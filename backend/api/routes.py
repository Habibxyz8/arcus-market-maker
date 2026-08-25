"""Phases 4-39: Unified routes + BotService singleton + paper volume/PnL/risk."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse

from backend.config.settings import settings
from backend.models.schemas import BotStatusResponse, HealthResponse, MarketSnapshot, StartRequest
from backend.monitoring.logger import BOT_STARTED, BOT_STOPPED, EMERGENCY_STOP, get_logger
from backend.services.trading_mode import describe_mode, require_not_emergency, validate_live_start
from backend.services.bot import BotService

log = get_logger(__name__)
router = APIRouter()

bot = BotService()
# keep legacy _state for backward compat but delegate to bot
_state: dict[str, object] = {"state": "STOPPED", "emergency": False}


def _sync_state() -> None:
    _state["state"] = bot.state
    _state["emergency"] = bot.emergency.active


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(trading_mode=settings.trading_mode.value, market=settings.market)


@router.get("/bot/status", response_model=BotStatusResponse)
async def bot_status() -> BotStatusResponse:
    _sync_state()
    return BotStatusResponse(
        state=bot.state,  # type: ignore[arg-type]
        trading_mode=settings.trading_mode.value,
        market=settings.market,
        emergency=bot.emergency.active,
    )


@router.get("/config/mode")
async def config_mode() -> JSONResponse:
    return JSONResponse(describe_mode())


@router.post("/bot/start")
async def bot_start(req: StartRequest) -> JSONResponse:
    require_not_emergency(bot.emergency.active)
    validate_live_start(req.confirm_live)
    if settings.trading_mode.value in ("LIVE", "TESTNET") and not settings.has_credentials():
        log.warning("Starting %s without credentials - trading will be blocked by risk engine", settings.trading_mode.value)
    try:
        await bot.start()
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))
    _sync_state()
    log.info("%s mode=%s market=%s", BOT_STARTED, settings.trading_mode.value, settings.market)
    return JSONResponse({"ok": True, "state": bot.state, "mode": settings.trading_mode.value})


@router.post("/bot/pause")
async def bot_pause() -> JSONResponse:
    require_not_emergency(bot.emergency.active)
    if bot.state != "RUNNING":
        raise HTTPException(status_code=409, detail="Not running")
    bot.state = "PAUSED"
    _sync_state()
    log.info("%s", BOT_STOPPED)
    return JSONResponse({"ok": True, "state": "PAUSED"})


@router.post("/bot/stop")
async def bot_stop() -> JSONResponse:
    await bot.stop()
    _sync_state()
    log.info("%s", BOT_STOPPED)
    return JSONResponse({"ok": True, "state": bot.state})


@router.post("/bot/emergency-stop")
async def bot_emergency() -> JSONResponse:
    await bot.emergency_stop("manual")
    _sync_state()
    log.warning("%s - all quotes should be cancelled", EMERGENCY_STOP)
    return JSONResponse({"ok": True, "state": bot.state})


@router.post("/bot/reset-emergency")
async def bot_reset_emergency() -> JSONResponse:
    bot.reset_emergency()
    _sync_state()
    return JSONResponse({"ok": True, "state": bot.state})


@router.get("/market/snapshot")
async def market_snapshot() -> JSONResponse:
    s = bot.status_dict()
    return JSONResponse({
        "market": s["market"],
        "bid": s["bid"],
        "ask": s["ask"],
        "mid": s["mid"],
        "spread": s["spread"],
        "spread_bps": s["spread_bps"],
        "stale": s["stale"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


@router.get("/analytics/status")
async def analytics_status() -> JSONResponse:
    return JSONResponse(bot.status_dict())


@router.get("/analytics/volume")
async def analytics_volume() -> JSONResponse:
    s = bot.status_dict()
    vol = s["volume"]
    target = 1_000_000
    return JSONResponse({
        "target": target,
        "current": vol,
        "remaining": max(0, target - vol),
        "progress_pct": (vol / target * 100) if target else 0,
        "daily": vol * 0.1,  # stub split
        "weekly": vol * 0.5,
        "monthly": vol,
        "session": vol,
        "fills": len(bot.paper.fills),
        "avg_fill": (vol / len(bot.paper.fills)) if bot.paper.fills else 0,
        "fill_rate": 0.3,
        "trading_mode": settings.trading_mode.value,
        # clearly separated
        "paper_volume": vol if settings.trading_mode.value == "PAPER" else 0,
        "testnet_volume": vol if settings.trading_mode.value == "TESTNET" else 0,
        "live_volume": vol if settings.trading_mode.value == "LIVE" else 0,
    })


@router.get("/analytics/pnl")
async def analytics_pnl() -> JSONResponse:
    s = bot.status_dict()
    return JSONResponse({
        "gross": s["realized_pnl"] + s["fees"],
        "fees": s["fees"],
        "funding": 0,
        "net": s["net_pnl"],
        "realized": s["realized_pnl"],
        "unrealized": s["unrealized_pnl"],
        "inventory_pnl": s["unrealized_pnl"],
        "volume": s["volume"],
        "per_1k": (s["net_pnl"] / s["volume"] * 1000) if s["volume"] else 0,
        "per_10k": (s["net_pnl"] / s["volume"] * 10000) if s["volume"] else 0,
        "per_100k": (s["net_pnl"] / s["volume"] * 100000) if s["volume"] else 0,
        "per_1m": (s["net_pnl"] / s["volume"] * 1000000) if s["volume"] else 0,
    })


@router.get("/analytics/risk")
async def analytics_risk() -> JSONResponse:
    s = bot.status_dict()
    return JSONResponse({
        "inventory_usage_pct": abs(s["inventory"]) / settings.max_inventory * 100 if settings.max_inventory else 0,
        "exposure_usage_pct": abs(s["exposure"]) / settings.max_exposure * 100 if settings.max_exposure else 0,
        "daily_loss_usage_pct": abs(bot.daily_loss) / settings.max_daily_loss * 100 if settings.max_daily_loss else 0,
        "open_order_usage_pct": s["open_orders"] / settings.max_open_orders * 100 if settings.max_open_orders else 0,
        "rate_limit_usage_pct": s["rate_usage_pct"],
        "stale": s["stale"],
        "dms_active": not settings.is_paper and bot.emergency.active is False,
        "overall": "OK" if not s["stale"] and not bot.emergency.active else "WARNING",
        "inventory": s["inventory"],
        "exposure": s["exposure"],
    })


@router.get("/orders")
async def list_orders() -> JSONResponse:
    orders = []
    for o in bot.paper.orders.values():
        orders.append({
            "order_id": o.order_id,
            "client_id": o.client_id,
            "market": o.market,
            "side": o.side,
            "price": o.price,
            "quantity": o.quantity,
            "filled_quantity": o.filled,
            "remaining": max(0, o.quantity - o.filled),
            "status": o.status,
            "created": o.created_ns,
            "updated": o.created_ns,
        })
    return JSONResponse({"orders": orders, "trading_mode": settings.trading_mode.value})


@router.get("/fills")
async def list_fills() -> JSONResponse:
    fills = []
    for f in bot.paper.fills[-100:]:
        fills.append({
            "fill_id": f.fill_id,
            "order_id": f.order_id,
            "market": f.market,
            "side": f.side,
            "price": f.price,
            "quantity": f.quantity,
            "notional": f.notional,
            "fee": f.fee,
            "timestamp": f.ts_ns,
        })
    return JSONResponse({"fills": fills, "trading_mode": settings.trading_mode.value})


@router.get("/config/settings")
async def get_settings() -> JSONResponse:
    # Safe expose (no secrets)
    return JSONResponse({
        "market": settings.market,
        "order_size": settings.order_size,
        "max_order_size": settings.max_order_size,
        "bid_spread_bps": settings.bid_spread_bps,
        "ask_spread_bps": settings.ask_spread_bps,
        "quote_refresh_interval_ms": settings.quote_refresh_interval_ms,
        "max_inventory": settings.max_inventory,
        "max_exposure": settings.max_exposure,
        "max_daily_loss": settings.max_daily_loss,
        "max_open_orders": settings.max_open_orders,
        "max_order_age_sec": settings.max_order_age_sec,
        "min_expected_profit": settings.min_expected_profit,
        "min_expected_edge_bps": settings.min_expected_edge_bps,
        "inventory_skew_factor": settings.inventory_skew_factor,
        "maker_fee_bps": settings.maker_fee_bps,
        "dead_mans_switch_timeout_sec": settings.dead_mans_switch_timeout_sec,
    })


@router.post("/config/settings")
async def update_settings(payload: dict[str, Any]) -> JSONResponse:
    # Allow updating mutable fields (no secrets, no TRADING_MODE via this endpoint)
    allowed = {"market","order_size","max_order_size","bid_spread_bps","ask_spread_bps","quote_refresh_interval_ms","max_inventory","max_exposure","max_daily_loss","max_open_orders","max_order_age_sec","min_expected_profit","min_expected_edge_bps","inventory_skew_factor","maker_fee_bps","dead_mans_switch_timeout_sec"}
    for k, v in payload.items():
        if k in allowed and hasattr(settings, k):
            setattr(settings, k, v)  # type: ignore[attr-defined]
    return JSONResponse({"ok": True, "settings": await get_settings()})  # type: ignore


# Dashboard WS - pushes status every 2s (Phase 39)
@router.websocket("/ws/dashboard")
async def ws_dashboard(ws: WebSocket) -> None:
    await ws.accept()
    try:
        while True:
            payload = bot.status_dict()
            payload["type"] = "status"
            payload["ts"] = datetime.now(timezone.utc).isoformat()
            await ws.send_text(json.dumps(payload, default=str))
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        pass
