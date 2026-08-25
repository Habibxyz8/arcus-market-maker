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
        # Enforce pure maker: millisecond HFT, dynamic margin*leverage, micro TP/SL already in PaperEngine
        while self.state == "RUNNING":
            try:
                await self.limiter.acquire()
                snap = self.md.snapshot
                if snap.mid is None:
                    if settings.is_paper:
                        self.md._seed_mock()
                        snap = self.md.snapshot
                    else:
                        self.paper.cancel_all()
                        await asyncio.sleep(0.5)
                        continue
                # Sync dynamic margin/leverage: Position Notional = Margin * Leverage
                # Enforce Arcus max leverage per pair
                try:
                    from backend.strategy.market_limits import get_max_leverage_sync
                    max_lev = get_max_leverage_sync(snap.market)
                    if settings.leverage > max_lev:
                        settings.leverage = max_lev
                except Exception:
                    pass
                self.paper.leverage = settings.leverage
                self.paper.initial_balance = settings.account_balance
                # Derive notional from margin*leverage if margin set
                if settings.margin_usd > 0:
                    # Ensure margin $1-100+ and leverage respects pair limit
                    margin = max(1.0, min(settings.margin_usd, settings.account_balance))
                    # clamp leverage to pair max
                    try:
                        from backend.strategy.market_limits import get_max_leverage_sync as _gml
                        margin = max(1.0, min(margin, 1000))
                        max_lev2 = _gml(snap.market)
                        if settings.leverage > max_lev2:
                            settings.leverage = max_lev2
                    except Exception:
                        pass
                    notional = margin * settings.leverage
                    # keep order_size_usd in sync for UI
                    settings.order_size_usd = notional
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

    def set_market(self, market: str) -> None:
        self.md.set_market(market)
        settings.market = market

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
            "stale": snap.stale if not settings.is_paper else False,  # PAPER never stale to UI
            "inventory": self.paper.base_inventory,
            "exposure": self.paper.base_inventory * (snap.mid or 0),
            "open_orders": len(self.paper.open_orders()),
            "volume": self.paper.volume(),
            "realized_pnl": pnl["realized"],
            "unrealized_pnl": pnl["unrealized"],
            "fees": pnl["fees"],
            "net_pnl": pnl["net"],
            "equity": pnl["equity"],
            "used_margin": pnl["used_margin"],
            "cpm": pnl["cpm"],
            "account_balance": settings.account_balance,
            "leverage": settings.leverage,
            "order_size_usd": settings.order_size_usd,
            "take_profit_usd": settings.take_profit_usd,
            "stop_loss_usd": settings.stop_loss_usd,
            "preset": settings.strategy_preset,
            "rate_usage_pct": self.limiter.usage_pct(),
        }
