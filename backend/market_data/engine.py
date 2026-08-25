"""Phase 7: Market data engine - WS + REST fallback, stale detection, sequence handling."""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import httpx
import websockets

from backend.arcus.client import ArcusClient
from backend.config.settings import settings
from backend.monitoring.logger import MARKET_DATA_STALE, get_logger

log = get_logger(__name__)

STALE_SEC = 5.0


@dataclass
class OrderBookLevel:
    price: float
    size: float


@dataclass
class MarketSnapshot:
    market: str
    market_id: int
    bid: float | None = None
    ask: float | None = None
    mid: float | None = None
    spread: float | None = None
    spread_bps: float | None = None
    bids: list[OrderBookLevel] = field(default_factory=list)
    asks: list[OrderBookLevel] = field(default_factory=list)
    last_price: float | None = None
    timestamp: datetime | None = None
    sequence: int | None = None
    stale: bool = True
    server_ts: int | None = None


class MarketDataEngine:
    def __init__(self, market: str | None = None, market_id: int = 1) -> None:
        self.market = market or settings.market
        self.market_id = market_id
        self.snapshot = MarketSnapshot(market=self.market, market_id=market_id)
        self._client = ArcusClient()
        self._ws_task: asyncio.Task | None = None
        self._running = False
        self._last_update_ns: int | None = None
        self._seq: int | None = None
        self._callbacks: list[Any] = []

    def on_update(self, cb):  # type: ignore[no-untyped-def]
        self._callbacks.append(cb)

    async def _fetch_rest_snapshot(self) -> None:
        try:
            # Prefer BBO, fallback to markets oraclePrice
            try:
                bbo = await self._client.get_bbo(self.market_id)
                # bbo shape varies; try to parse bid/ask
                bid = float(bbo.get("bid") or bbo.get("bestBid") or 0) or None
                ask = float(bbo.get("ask") or bbo.get("bestAsk") or 0) or None
                if bid and ask:
                    self._apply_bbo(bid, ask, sequence=None)
                    return
            except Exception:
                pass
            mkts = await self._client.get_markets(self.market)
            m = (mkts.get("markets") or [])[0] if isinstance(mkts, dict) else None
            if m:
                oracle = float(m.get("oraclePrice") or m.get("markPrice") or 0) or None
                if oracle:
                    # synth spread 2 bps around oracle when no BBO
                    self._apply_bbo(oracle * 0.9999, oracle * 1.0001, sequence=None)
        except Exception as e:
            log.error("REST fallback failed %s", type(e).__name__)

    def _apply_bbo(self, bid: float, ask: float, sequence: int | None) -> None:
        now = datetime.now(timezone.utc)
        mid = (bid + ask) / 2
        spread = ask - bid
        spread_bps = (spread / mid * 10000) if mid else None
        # sequence handling
        if sequence is not None:
            if self._seq is not None and sequence <= self._seq:
                log.warning("Stale sequence %s <= %s", sequence, self._seq)
                return
            self._seq = sequence
        self.snapshot.bid = bid
        self.snapshot.ask = ask
        self.snapshot.mid = mid
        self.snapshot.spread = spread
        self.snapshot.spread_bps = spread_bps
        self.snapshot.timestamp = now
        self.snapshot.sequence = sequence
        self.snapshot.stale = False
        self.snapshot.server_ts = int(time.time() * 1000)
        self._last_update_ns = time.time_ns()
        for cb in self._callbacks:
            try:
                cb(self.snapshot)
            except Exception:
                pass

    def is_stale(self) -> bool:
        if self._last_update_ns is None:
            return True
        return (time.time_ns() - self._last_update_ns) / 1e9 > STALE_SEC

    async def start(self) -> None:
        self._running = True
        # initial REST
        await self._fetch_rest_snapshot()
        # WS loop with reconnect
        self._ws_task = asyncio.create_task(self._ws_loop())

    async def stop(self) -> None:
        self._running = False
        if self._ws_task:
            self._ws_task.cancel()
            try:
                await self._ws_task
            except asyncio.CancelledError:
                pass
        await self._client.close()

    async def _ws_loop(self) -> None:
        backoff = 1.0
        while self._running:
            try:
                url = settings.active_ws_url
                # Arcus WS expects no auth for market data; we just subscribe
                async with websockets.connect(url, ping_interval=20, ping_timeout=10) as ws:  # type: ignore[arg-type]
                    log.info("MarketData WS connected %s", url)
                    # Subscribe to BBO/markets per docs - best effort
                    await ws.send(f'{{"type":"subscribe","channel":"bbo","marketId":{self.market_id}}}')
                    await ws.send(f'{{"type":"subscribe","channel":"markets"}}')
                    backoff = 1.0
                    async for raw in ws:
                        try:
                            import json
                            msg = json.loads(raw)
                            # Heartbeat
                            if msg.get("type") == "ping":
                                await ws.send('{"type":"pong"}')
                                continue
                            # Try parse BBO
                            if "bid" in msg and "ask" in msg:
                                bid = float(msg["bid"])
                                ask = float(msg["ask"])
                                seq = msg.get("sequence") or msg.get("seq")
                                self._apply_bbo(bid, ask, seq)
                            elif "bbo" in msg:
                                b = msg["bbo"]
                                self._apply_bbo(float(b["bid"]), float(b["ask"]), b.get("sequence"))
                        except Exception as e:
                            log.error("WS parse error %s", e)
                        # stale check
                        if self.is_stale():
                            log.warning(MARKET_DATA_STALE + " no update %.1fs", STALE_SEC)
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error("WS disconnect %s backoff %.1f", type(e).__name__, backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30)
            # periodic REST fallback
            await self._fetch_rest_snapshot()
            if self.is_stale():
                log.warning(MARKET_DATA_STALE)
            await asyncio.sleep(1)
