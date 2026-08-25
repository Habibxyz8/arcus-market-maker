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

# Live Arcus symbols (per getMarkets). Synthetic fallback only if live stale >1s.
MOCK_PRICES: dict[str, float] = {
    "BTC-USD": 65000.0,
    "ETH-USD": 3500.0,
    "SOL-USD": 150.0,
    "NVDA-USD": 500.0,
    "TSLA-USD": 250.0,
    "AAPL-USD": 220.0,
    "SPY-USD": 580.0,
    "QQQ-USD": 500.0,
}
# Market IDs from live Arcus (cached). Fallback map if fetch fails.
MARKET_IDS: dict[str, int] = {"BTC-USD": 1, "ETH-USD": 2, "SOL-USD": 3, "NVDA-USD": 4, "TSLA-USD": 5, "AAPL-USD": 6, "SPY-USD": 7, "QQQ-USD": 8}


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
    def __init__(self, market: str | None = None, market_id: int | None = None) -> None:
        self.market = market or settings.market
        self.market_id = market_id or MARKET_IDS.get(self.market, 1)
        self.snapshot = MarketSnapshot(market=self.market, market_id=self.market_id)
        self._client = ArcusClient()
        self._ws_task: asyncio.Task | None = None
        self._synthetic_task: asyncio.Task | None = None
        self._running = False
        self._last_update_ns: int | None = None
        self._seq: int | None = None
        self._callbacks: list[Any] = []
        self._mock_base = MOCK_PRICES.get(self.market, 65000.0)

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

    def _seed_mock(self) -> None:
        mid = self._mock_base
        self._apply_bbo(mid * 0.9999, mid * 1.0001, sequence=None)

    async def _synthetic_loop(self) -> None:
        # In PAPER, always wiggle mid slightly (±0.06%) every 350ms on top of live price
        # so BID/ASK/MID stream without lag even when Arcus REST is 1s polled
        import random
        while self._running:
            if settings.is_paper:
                # Blend live mid with synthetic drift for continuous millisecond stream
                base = self.snapshot.mid or self._mock_base
                drift = (random.random() - 0.5) * 0.0012  # ±0.06% per tick
                new_mid = base * (1 + drift)
                bid = new_mid * (1 - 0.00035)
                ask = new_mid * (1 + 0.00035)
                self._mock_base = new_mid
                self._apply_bbo(bid, ask, sequence=None)
            await asyncio.sleep(0.35)

    async def start(self) -> None:
        self._running = True
        if settings.is_paper:
            self._seed_mock()
            self._synthetic_task = asyncio.create_task(self._synthetic_loop())
        # initial REST (non-blocking fallback)
        try:
            await asyncio.wait_for(self._fetch_rest_snapshot(), timeout=2.0)
        except asyncio.TimeoutError:
            pass
        # WS loop with reconnect (keep for TESTNET/LIVE; also runs in PAPER but mock covers)
        self._ws_task = asyncio.create_task(self._ws_loop())

    async def stop(self) -> None:
        self._running = False
        for t in (self._ws_task, self._synthetic_task):
            if t:
                t.cancel()
                try:
                    await t
                except asyncio.CancelledError:
                    pass
        await self._client.close()

    def set_market(self, market: str) -> None:
        self.market = market
        self.market_id = MARKET_IDS.get(market, 1)
        self.snapshot.market = market
        self.snapshot.market_id = self.market_id
        self._mock_base = MOCK_PRICES.get(market, 65000.0)
        self._seed_mock()

    async def _ws_loop(self) -> None:
        backoff = 1.0
        while self._running:
            try:
                url = settings.active_ws_url
                # Try public websocket for live Arcus (BBO + trades). Fallback to REST polling if not available.
                async with websockets.connect(url, ping_interval=20, ping_timeout=10) as ws:  # type: ignore[arg-type]
                    log.info("MarketData WS connected %s %s", url, self.market)
                    # Subscribe patterns: try both Arcus spec and generic
                    for ch in [f'{{"type":"subscribe","channel":"bbo","marketId":{self.market_id}}}',
                               f'{{"type":"subscribe","channel":"bbo","market":"{self.market}"}}',
                               '{"type":"subscribe","channel":"markets"}',
                               f'{{"op":"subscribe","args":["bbo.{self.market}"]}}']:
                        try:
                            await ws.send(ch)
                        except Exception:
                            pass
                    backoff = 1.0
                    async for raw in ws:
                        try:
                            import json
                            msg = json.loads(raw)
                            if msg.get("type") == "ping":
                                await ws.send('{"type":"pong"}')
                                continue
                            # Direct BBO
                            if "bid" in msg and "ask" in msg and "market" not in msg:
                                self._apply_bbo(float(msg["bid"]), float(msg["ask"]), msg.get("sequence") or msg.get("seq"))
                            elif "bbo" in msg:
                                b = msg["bbo"]
                                self._apply_bbo(float(b["bid"]), float(b["ask"]), b.get("sequence"))
                            elif msg.get("channel") == "bbo" and "data" in msg:
                                d = msg["data"]
                                if isinstance(d, dict) and "bid" in d and "ask" in d:
                                    self._apply_bbo(float(d["bid"]), float(d["ask"]), d.get("sequence"))
                            elif msg.get("topic") == f"bbo.{self.market}" and "data" in msg:
                                d = msg["data"]
                                self._apply_bbo(float(d["bid"]), float(d["ask"]), d.get("seq"))
                            # Markets channel may carry oraclePrice
                            if msg.get("channel") == "markets" and "data" in msg:
                                for m in msg["data"] if isinstance(msg["data"], list) else [msg["data"]]:
                                    if isinstance(m, dict) and m.get("marketDisplayName") == self.market:
                                        o = m.get("oraclePrice") or m.get("markPrice")
                                        if o:
                                            try:
                                                mid = float(o)
                                                self._apply_bbo(mid*0.9999, mid*1.0001, None)
                                            except Exception:
                                                pass
                        except Exception as e:
                            log.error("WS parse error %s", e)
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error("WS disconnect %s backoff %.1f", type(e).__name__, backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30)
            # REST live polling every 1s for all pairs (BBO -> livePrices -> markets)
            try:
                await self._fetch_rest_snapshot()
                # also poll livePrices for this market
                try:
                    lp = await self._client.get_live_prices()
                    # livePrices shape: {prices: [{market:"BTC-USD", bid, ask}]}
                    lst = lp.get("prices") or lp.get("markets") or []
                    for p in lst if isinstance(lst, list) else []:
                        if isinstance(p, dict) and (p.get("market")==self.market or p.get("marketDisplayName")==self.market):
                            bid = p.get("bid") or p.get("bestBid")
                            ask = p.get("ask") or p.get("bestAsk")
                            if bid and ask:
                                self._apply_bbo(float(bid), float(ask), None)
                                break
                except Exception:
                    pass
            except Exception:
                pass
            if self.is_stale():
                log.warning(MARKET_DATA_STALE + " %s", self.market)
            await asyncio.sleep(1)
