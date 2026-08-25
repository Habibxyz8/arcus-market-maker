"""Phase 4: Trading mode guards - single source of truth."""
from __future__ import annotations

from fastapi import HTTPException

from backend.config.settings import TradingMode, settings
from backend.monitoring.logger import get_logger

log = get_logger(__name__)


def require_not_emergency(emergency: bool) -> None:
    if emergency:
        raise HTTPException(status_code=409, detail="Emergency stop active - POST /api/bot/reset-emergency first")


def validate_live_start(confirm_live: bool) -> None:
    """Phase 4: LIVE must never auto-start; requires explicit confirmation."""
    if settings.trading_mode == TradingMode.LIVE and not confirm_live:
        log.warning("BLOCKED LIVE start without confirm_live=true")
        raise HTTPException(
            status_code=400,
            detail="LIVE mode requires confirm_live=true and explicit user confirmation",
        )


def describe_mode() -> dict[str, str | bool]:
    """Safe to expose to frontend (no secrets)."""
    return {
        "mode": settings.trading_mode.value,
        "is_paper": settings.trading_mode == TradingMode.PAPER,
        "is_testnet": settings.trading_mode == TradingMode.TESTNET,
        "is_live": settings.trading_mode == TradingMode.LIVE,
        "rest_url": settings.active_rest_url,
        "ws_url": settings.active_ws_url,
        "market": settings.market,
        "has_credentials": settings.has_credentials(),
    }
