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
        self.state: str = "STOPPED"
        self._quote_task: asyncio.Task | None = None
        self.daily_loss: float = 0.0
        self.execution_status: str = "IDLE"
        self.active_markets: list[str] = []

    async def start(self) -> None:
        if self.emergency.active:
            raise RuntimeError("Emergency active")
        if self.state == "RUNNING":
            return
        if settings.market == "ALL_PAIRS":
            try:
                from backend.strategy.market_limits import fetch_limits
                limits = await fetch_limits()
                self.active_markets = sorted(limits.keys())
                log.info("ALL_PAIRS mode: %d markets", len(self.active_markets))
            except Exception:
                self.active_markets = settings.supported_markets.split(",")
            await self.md.start()
            for m in self.active_markets:
                try:
                    self.md.get_snapshot_for(m)
                except Exception:
                    pass
        else:
            self.active_markets = [settings.market]
            await self.md.start()
        self.state = "RUNNING"
        self.execution_status = "STARTING"
        self._quote_task = asyncio.create_task(self._quote_loop())
        log.info("BOT_RUNNING mode=%s market=%s", settings.trading_mode.value, settings.market)

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
        log.info("QUOTE LOOP START")
        last_closed_len = len(self.paper.closed_trades)
        try:
            self._set_status("RUNNING - PLACING ORDERS")
        except Exception as e:
            log.error("set_status failed %s", e)
        rr_idx = 0
        while self.state == "RUNNING":
            try:
                log.info("QUOTE LOOP TICK")
                await self.limiter.acquire()
                log.info("QUOTE LOOP ACQUIRED")
                # Single or ALL_PAIRS round-robin (one market per tick for clean settlement)
                if settings.market == "ALL_PAIRS":
                    if not self.active_markets:
                        try:
                            from backend.strategy.market_limits import _cache
                            self.active_markets = sorted(_cache.keys())[:12] if _cache else settings.supported_markets.split(",")[:5]
                        except Exception:
                            self.active_markets = settings.supported_markets.split(",")[:5]
                    market = self.active_markets[rr_idx % len(self.active_markets)]
                    rr_idx += 1
                    markets = [market]
                else:
                    markets = [self.md.snapshot.market]
                for market in markets:
                    try:
                        snap = self.md.get_snapshot_for(market) if settings.market == "ALL_PAIRS" else self.md.snapshot
                    except Exception:
                        snap = self.md.snapshot
                    if snap.mid is None:
                        if settings.is_paper:
                            self.md._seed_mock()
                            snap = self.md.get_snapshot_for(market) if settings.market == "ALL_PAIRS" else self.md.snapshot
                        else:
                            self.paper.cancel_all()
                            self._set_status("STALE - CANCELLED")
                            await asyncio.sleep(0.05)
                            continue
                    if snap.mid is not None:
                        closed = self.paper._check_micro_tp_sl(snap.mid, market)
                        if closed:
                            self._set_status(f"RE-OPENING CYCLE {market}")
                            last_closed_len = len(self.paper.closed_trades)
                        else:
                            if len([o for o in self.paper.open_orders() if o.market==market]) == 0:
                                self._set_status(f"PLACING ORDER {market} BID {snap.bid:.2f}" if snap.bid else f"PLACING {market}")
                            else:
                                self._set_status(f"EVALUATING {market} TP {settings.take_profit_usd:.3f} SL {settings.stop_loss_usd:.3f}")
                    # Sync margin/leverage per market
                    try:
                        from backend.strategy.market_limits import get_max_leverage_sync
                        max_lev = get_max_leverage_sync(market)
                        if settings.leverage > max_lev:
                            settings.leverage = max_lev
                    except Exception:
                        pass
                    self.paper.leverage = settings.leverage
                    self.paper.initial_balance = settings.account_balance
                    if settings.margin_usd > 0:
                        margin = max(1.0, min(settings.margin_usd, settings.account_balance))
                        settings.order_size_usd = margin * settings.leverage
                    # Cancel stale for this market before risk
                    pre_open = len([o for o in self.paper.open_orders() if o.market == market])
                    if pre_open >= 2:
                        for o in list(self.paper.orders.values()):
                            if o.market == market and o.status == "open":
                                o.status = "canceled"
                    rc = check_all(snap, settings.order_size, "buy", self.paper.base_inventory, exposure=self.paper.base_inventory * (snap.mid or 0), daily_loss=self.daily_loss, open_orders=len(self.paper.open_orders()), rate_remaining=None, emergency=self.emergency.active)
                    if not rc.passed and self.paper.base_inventory == 0:
                        await asyncio.sleep(0.03)
                        continue
                    q = compute_quotes(snap, base_inventory=self.paper.base_inventory)
                    if not q:
                        if snap.mid and self.paper.base_inventory != 0:
                            self.paper.simulate_market_tick(snap.mid, snap.spread or 1, market)
                        await asyncio.sleep(0.02)
                        continue
                    if q.bid_price and q.ask_price:
                        inp = ProfitabilityInput(fair_value=q.fair_value or snap.mid or 0, bid_price=q.bid_price, ask_price=q.ask_price, bid_size=q.bid_size, ask_size=q.ask_size, spread_bps=q.spread_bps)
                        if settings.trading_mode.value != "PAPER" and check(inp, self.paper.base_inventory) != "PROFITABLE":
                            await asyncio.sleep(0.05)
                            continue
                    self._set_status(f"PLACING ORDER {market} BID {q.bid_price:.2f} ASK {q.ask_price:.2f}" if q.bid_price and q.ask_price else f"PLACING {market}")
                    for o in list(self.paper.orders.values()):
                        if o.market == market and o.status == "open":
                            o.status = "canceled"
                    if q.bid_price and q.bid_size > 0:
                        self.paper.place(market, "buy", q.bid_price, q.bid_size)
                    if q.ask_price and q.ask_size > 0:
                        self.paper.place(market, "sell", q.ask_price, q.ask_size)
                    if snap.mid:
                        before_closed = len(self.paper.closed_trades)
                        fills = self.paper.simulate_market_tick(snap.mid, snap.spread or 1, market)
                        if fills:
                            self._set_status(f"ORDER FILLED {market} {fills[0].side.upper()} {fills[0].quantity:.6f}")
                        after_closed = len(self.paper.closed_trades)
                        if after_closed > before_closed:
                            self._set_status(f"RE-OPENING CYCLE {market} PnL {self.paper.closed_trades[-1].net_pnl:+.3f}")
                            last_closed_len = after_closed
                            await asyncio.sleep(0.015)
                            continue
                    if len(self.paper.closed_trades) > last_closed_len:
                        last_closed_len = len(self.paper.closed_trades)
                        await asyncio.sleep(0.015)
                        continue
                await asyncio.sleep(settings.quote_refresh_interval_ms / 1000)
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error("quote loop error %s", type(e).__name__)
                await asyncio.sleep(0.5)

    def _set_status(self, msg: str) -> None:
        self.execution_status = msg
        try:
            log.info("EXEC %s", msg)
        except Exception:
            pass

    def set_market(self, market: str) -> None:
        self.md.set_market(market)
        settings.market = market
        if market == "ALL_PAIRS":
            try:
                from backend.strategy.market_limits import _cache
                if _cache:
                    self.active_markets = sorted(_cache.keys())
                else:
                    self.active_markets = settings.supported_markets.split(",")
                if len(self.active_markets) < 5:
                    self.active_markets = settings.supported_markets.split(",")
            except Exception:
                self.active_markets = settings.supported_markets.split(",")
        else:
            self.active_markets = [market]

    def status_dict(self) -> dict[str, Any]:
        snap = self.md.snapshot
        if settings.market == "ALL_PAIRS" and self.active_markets:
            mids = []
            for m in self.active_markets[:5]:
                try:
                    s = self.md.get_snapshot_for(m)
                    if s.mid:
                        mids.append(s.mid)
                except Exception:
                    pass
            if mids:
                snap.mid = sum(mids) / len(mids)
        pnl = self.paper.pnl(snap.mid)
        return {
            "state": self.state,
            "emergency": self.emergency.active,
            "execution_status": self.execution_status,
            "active_markets": self.active_markets,
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
