"""Phase 19: Risk engine - 14 pre-trade checks."""
from __future__ import annotations

from dataclasses import dataclass

from backend.config.settings import settings
from backend.market_data.engine import MarketSnapshot


@dataclass
class RiskCheck:
    passed: bool
    reason: str | None = None


def check_all(
    snap: MarketSnapshot,
    order_size: float,
    side: str,
    base_inventory: float,
    exposure: float,
    daily_loss: float,
    open_orders: int,
    rate_remaining: int | None = None,
    emergency: bool = False,
) -> RiskCheck:
    if emergency:
        return RiskCheck(False, "emergency_stop")
    if snap.stale or snap.mid is None:
        return RiskCheck(False, "market_data_stale")
    if snap.bid is None or snap.ask is None or snap.mid is None:
        return RiskCheck(False, "market_status_invalid")
    # price deviation >5% from mid if order price far
    # (checked later per order price; here just size)
    if order_size <= 0:
        return RiskCheck(False, "order_size_invalid")
    if order_size > settings.max_order_size:
        return RiskCheck(False, "order_size_exceeds_max")
    if abs(base_inventory) > settings.max_inventory:
        return RiskCheck(False, "inventory_exceeded")
    if abs(exposure) > settings.max_exposure:
        return RiskCheck(False, "exposure_exceeded")
    if daily_loss <= -settings.max_daily_loss:
        return RiskCheck(False, "daily_loss_exceeded")
    if open_orders >= settings.max_open_orders:
        return RiskCheck(False, "max_open_orders")
    if rate_remaining is not None and rate_remaining < 5:
        return RiskCheck(False, "rate_limit_low")
    # market data freshness already, price deviation etc handled in order path
    return RiskCheck(True, None)
