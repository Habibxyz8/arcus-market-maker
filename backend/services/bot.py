"""Orchestrator tying market data + fair value + quoting + risk + paper trading."""
from __future__ import annotations

import asyncio
from typing import Any

from backend.config.settings import settings
from backend.market_data.engine import MarketDataEngine
from backend.paper_trading.engine import PaperEngine
from backend.profitability.engine import ProfitabilityInput, check, estimate
from backend.risk.emergency import EmergencyManager
from backend.risk.engine import check_all
from backend.risk.rate_limiter import RateLimiter
from backend.strategy.market_maker import compute_quotes
from backend.monitoring.logger import get_logger

log = get_logger(__name__)


class BotService:
    def __init__(self) -> None:
        self.md = MarketDataEngine()
        self.paper = PaperEngine()
        self.emergency = EmergencyManager()
        self.limiter = RateLimiter()
        self.state: str = "STOPPED"  # STOPPED/RUNNING/PAUSED/EMERGENCY
        self._quote_task: asyncio.Task | None = None
        self.daily_loss: float = 0.0

    async def start(self) -> None:
        if self.emergency.active:
            raise RuntimeError("Emergency active")
        if self.state == "RUNNING":
            return
        await self.md.start()
        self.state = "RUNNING"
        self._quote_task = asyncio.create_task(self._quote_loop())
        log.info("BOT_RUNNING mode=%s", settings.trading_mode.value)

    async def stop(self) -> None:
        self.state = "STOPPED"
        if self._quote_task:
            self._quote_task.cancel()
            try:
                await self._quote_task
            except asyncio.CancelledError:
                pass
        await self.md.stop()
        log.info("BOT_STOPPED")

    async def emergency_stop(self, reason: str = "manual") -> None:
        self.emergency.trigger(reason)
        self.state = "EMERGENCY"
        self.paper.cancel_all()
        if self._quote_task:
            self._quote_task.cancel()
        log.warning("EMERGENCY_STOP quotes cancelled")

    def reset_emergency(self) -> None:
        self.emergency.reset()
        self.state = "STOPPED"

    async def _quote_loop(self) -> None:
        while self.state == "RUNNING":
            try:
                await self.limiter.acquire()
                snap = self.md.snapshot
                if snap.stale or snap.mid is None:
                    # Phase 7: stale -> cancel quotes
                    self.paper.cancel_all()
                    await asyncio.sleep(1)
                    continue
                # risk
                rc = check_all(snap, settings.order_size, "buy", self.paper.base_inventory, exposure=self.paper.base_inventory * (snap.mid or 0), daily_loss=self.daily_loss, open_orders=len(self.paper.open_orders()), rate_remaining=None, emergency=self.emergency.active)
                if not rc.passed:
                    await asyncio.sleep(0.5)
                    continue
                # quotes
                q = compute_quotes(snap, base_inventory=self.paper.base_inventory)
                if not q:
                    await asyncio.sleep(0.5)
                    continue
                # profitability filter (Phase 14)
                if q.bid_price and q.ask_price:
                    inp = ProfitabilityInput(fair_value=q.fair_value or snap.mid or 0, bid_price=q.bid_price, ask_price=q.ask_price, bid_size=q.bid_size, ask_size=q.ask_size, spread_bps=q.spread_bps)
                    if settings.trading_mode.value == "PAPER":
                        # In paper allow experimental but still compute
                        pass
                    else:
                        if check(inp, self.paper.base_inventory) != "PROFITABLE":
                            await asyncio.sleep(0.5)
                            continue
                # place paper orders (cancel old, place new)
                self.paper.cancel_all()
                if q.bid_price and q.bid_size > 0:
                    self.paper.place(snap.market, "buy", q.bid_price, q.bid_size)
                if q.ask_price and q.ask_size > 0:
                    self.paper.place(snap.market, "sell", q.ask_price, q.ask_size)
                # simulate fills
                if snap.mid:
                    self.paper.simulate_market_tick(snap.mid, snap.spread or 1)
                await asyncio.sleep(settings.quote_refresh_interval_ms / 1000)
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error("quote loop error %s", type(e).__name__)
                await asyncio.sleep(1)

    def status_dict(self) -> dict[str, Any]:
        snap = self.md.snapshot
        pnl = self.paper.pnl(snap.mid)
        return {
            "state": self.state,
            "emergency": self.emergency.active,
            "trading_mode": settings.trading_mode.value,
            "market": snap.market,
            "bid": snap.bid,
            "ask": snap.ask,
            "mid": snap.mid,
            "spread": snap.spread,
            "spread_bps": snap.spread_bps,
            "stale": snap.stale,
            "inventory": self.paper.base_inventory,
            "exposure": self.paper.base_inventory * (snap.mid or 0),
            "open_orders": len(self.paper.open_orders()),
            "volume": self.paper.volume(),
            "realized_pnl": pnl["realized"],
            "unrealized_pnl": pnl["unrealized"],
            "fees": pnl["fees"],
            "net_pnl": pnl["net"],
            "rate_usage_pct": self.limiter.usage_pct(),
        }
