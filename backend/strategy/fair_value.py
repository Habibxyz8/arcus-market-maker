"""Phase 8: Fair value engine - modular, testable."""
from __future__ import annotations

from dataclasses import dataclass

from backend.market_data.engine import MarketSnapshot


@dataclass
class FairValueResult:
    mid: float | None
    microprice: float | None
    imbalance: float | None  # -1..1 (bid heavy positive)
    fair_value: float | None
    volatility: float | None
    spread: float | None
    depth: float | None


def mid_price(snap: MarketSnapshot) -> float | None:
    if snap.bid is not None and snap.ask is not None:
        return (snap.bid + snap.ask) / 2
    return snap.mid


def microprice(snap: MarketSnapshot) -> float | None:
    """(ask* bidSize + bid* askSize)/ (bidSize+askSize) when L2 exists."""
    if snap.bids and snap.asks:
        bid_sz = snap.bids[0].size if snap.bids[0].size else 0
        ask_sz = snap.asks[0].size if snap.asks[0].size else 0
        tot = bid_sz + ask_sz
        if tot > 0 and snap.bid and snap.ask:
            return (snap.ask * bid_sz + snap.bid * ask_sz) / tot
    return mid_price(snap)


def order_book_imbalance(snap: MarketSnapshot) -> float | None:
    if snap.bids and snap.asks:
        bids = sum(l.size for l in snap.bids[:5])
        asks = sum(l.size for l in snap.asks[:5])
        tot = bids + asks
        if tot > 0:
            return (bids - asks) / tot
    return None


def fair_value(snap: MarketSnapshot, recent_trades: list[float] | None = None) -> FairValueResult:
    mid = mid_price(snap)
    micro = microprice(snap)
    imb = order_book_imbalance(snap)
    # Blend microprice when imbalance is informative
    fv: float | None = mid
    if micro is not None and imb is not None and abs(imb) > 0.2:
        # Weighted: 70% micro, 30% mid when imbalance strong
        assert micro is not None and mid is not None
        fv = 0.7 * micro + 0.3 * mid
    elif micro is not None:
        fv = micro
    # volatility stub (real: std of returns)
    vol = None
    if recent_trades and len(recent_trades) >= 2 and fv:
        import math
        rets = [(recent_trades[i] - recent_trades[i - 1]) / recent_trades[i - 1] for i in range(1, len(recent_trades)) if recent_trades[i - 1]]
        if rets:
            mean = sum(rets) / len(rets)
            var = sum((r - mean) ** 2 for r in rets) / len(rets)
            vol = math.sqrt(var) * math.sqrt(86400)  # annualized-ish
    depth = None
    if snap.bids and snap.asks:
        depth = sum(l.size for l in snap.bids[:3]) + sum(l.size for l in snap.asks[:3])
    return FairValueResult(mid=mid, microprice=micro, imbalance=imb, fair_value=fv, volatility=vol, spread=snap.spread, depth=depth)
