"""Fetch Arcus pair limits: max leverage per market from GET /v1/markets."""
from __future__ import annotations

import asyncio
import time
from typing import Any

from backend.arcus.client import ArcusClient
from backend.monitoring.logger import get_logger

log = get_logger(__name__)

# Cache: symbol -> {max_leverage, tickSize, stepSize, initialMarginFraction}
_cache: dict[str, dict[str, Any]] = {}
_cache_ts: float = 0
TTL = 300  # 5m

DEFAULTS = {
    "BTC-USD": {"max_leverage": 20, "tickSize": "0.1", "stepSize": "0.0001", "initialMarginFraction": "0.05"},
    "ETH-USD": {"max_leverage": 15, "tickSize": "0.01", "stepSize": "0.001", "initialMarginFraction": "0.066"},
    "SOL-USD": {"max_leverage": 10, "tickSize": "0.01", "stepSize": "0.01", "initialMarginFraction": "0.1"},
    "NVDA-USD": {"max_leverage": 5, "tickSize": "0.01", "stepSize": "0.1", "initialMarginFraction": "0.2"},
    "TSLA-USD": {"max_leverage": 5, "tickSize": "0.01", "stepSize": "0.1", "initialMarginFraction": "0.2"},
    "AAPL-USD": {"max_leverage": 5, "tickSize": "0.01", "stepSize": "0.1", "initialMarginFraction": "0.2"},
}


async def fetch_limits(force: bool = False) -> dict[str, dict[str, Any]]:
    global _cache, _cache_ts
    if not force and _cache and time.time() - _cache_ts < TTL:
        return _cache
    client = ArcusClient()
    try:
        data = await client.get_markets()
        markets = data.get("markets", []) if isinstance(data, dict) else []
        new: dict[str, dict[str, Any]] = {}
        for m in markets:
            sym = m.get("marketDisplayName") or m.get("market") or ""
            if not sym:
                continue
            imf = m.get("initialMarginFraction") or "0.1"
            try:
                lev = int(round(1 / float(imf))) if float(imf) > 0 else 10
            except Exception:
                lev = 10
            lev = max(1, min(lev, 50))
            new[sym] = {
                "max_leverage": lev,
                "tickSize": m.get("tickSize", "0.1"),
                "stepSize": m.get("stepSize", "0.01"),
                "initialMarginFraction": imf,
            }
        if new:
            _cache = new
            _cache_ts = time.time()
            log.info("Fetched %d market limits", len(new))
        else:
            _cache = DEFAULTS.copy()
    except Exception as e:
        log.warning("fetch_limits failed %s, using defaults", type(e).__name__)
        if not _cache:
            _cache = DEFAULTS.copy()
    finally:
        await client.close()
    return _cache


def get_max_leverage_sync(market: str) -> int:
    if market in _cache:
        return int(_cache[market].get("max_leverage", 10))
    return int(DEFAULTS.get(market, {}).get("max_leverage", 10))


def get_tick_step(market: str) -> tuple[str, str]:
    if market in _cache and "tickSize" in _cache[market]:
        return _cache[market]["tickSize"], _cache[market]["stepSize"]
    d = DEFAULTS.get(market, {})
    return d.get("tickSize", "0.1"), d.get("stepSize", "0.01")
