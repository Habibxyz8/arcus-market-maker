"""Phase 9-12: Legit two-sided market maker, dynamic spread/size, inventory skew."""
from __future__ import annotations

from dataclasses import dataclass

from backend.config.settings import settings
from backend.market_data.engine import MarketSnapshot
from backend.strategy.fair_value import fair_value


@dataclass
class Quote:
    bid_price: float | None
    ask_price: float | None
    bid_size: float
    ask_size: float
    fair_value: float | None
    spread_bps: float


def _round_to_tick(price: float, tick: float = 0.1) -> float:
    import math
    # Use market tickSize; round to nearest tick
    return round(price / tick) * tick

# Pure maker: always ALO (Add Liquidity Only) => 0% taker fees
MAKER_TIF = 3  # ALO


def compute_quotes(
    snap: MarketSnapshot,
    base_inventory: float = 0.0,
    tick_size: float = 0.1,
    recent_vol: float | None = None,
) -> Quote | None:
    fv_res = fair_value(snap)
    fv = fv_res.fair_value
    # PAPER with synthetic mock: allow even if stale flag was just set (engine seeds mock)
    if fv is None:
        return None
    if snap.stale and not settings.is_paper:
        return None
    # Phase 10: dynamic spread
    base_bps = (settings.bid_spread_bps + settings.ask_spread_bps) / 2
    # Volatility widening
    if recent_vol and recent_vol > 0.02:
        base_bps *= 1.5
    if fv_res.imbalance is not None and abs(fv_res.imbalance) > 0.5:
        base_bps *= 1.2
    # Inventory skew (Phase 11)
    skew = base_inventory / max(settings.max_inventory, 1e-9) * settings.inventory_skew_factor
    # skew: long inventory -> ask more attractive (lower), bid less aggressive
    bid_bps = base_bps + skew * 10  # bps added to bid distance
    ask_bps = base_bps - skew * 10
    bid_bps = max(1, bid_bps)
    ask_bps = max(1, ask_bps)
    bid = _round_to_tick(fv * (1 - bid_bps / 10000), tick_size)
    ask = _round_to_tick(fv * (1 + ask_bps / 10000), tick_size)
    if bid is None or ask is None or bid >= ask:
        return None
    # Phase 12: adaptive size - USD-based with 10x leverage
    # User custom USD size; convert to qty via fv; presets adjust spread/refresh
    usd_size = settings.order_size_usd
    # clamp $1..$100 (balance) * leverage headroom
    usd_size = max(1.0, min(usd_size, settings.account_balance * settings.leverage * 0.7))
    base_size = usd_size / max(fv, 1.0) if fv else settings.order_size
    size = base_size
    if recent_vol and recent_vol > 0.03:
        size *= 0.5
    if fv_res.depth is not None and fv_res.depth < 1.0:
        size *= 0.7
    # Inventory cap
    if abs(base_inventory) >= settings.max_inventory:
        # Stop quoting on the side that would increase inventory
        if base_inventory > 0:
            size_bid = 0.0
            size_ask = min(size, settings.max_order_size)
        else:
            size_bid = min(size, settings.max_order_size)
            size_ask = 0.0
    else:
        size_bid = min(size, settings.max_order_size)
        size_ask = min(size, settings.max_order_size)
    # Apply inventory skew sizing
    if base_inventory > 0:
        size_bid *= 0.7
        size_ask *= 1.0
    elif base_inventory < 0:
        size_bid *= 1.0
        size_ask *= 0.7
    avg_bps = (bid_bps + ask_bps) / 2
    return Quote(bid_price=bid if size_bid > 0 else None, ask_price=ask if size_ask > 0 else None, bid_size=size_bid, ask_size=size_ask, fair_value=fv, spread_bps=avg_bps)
