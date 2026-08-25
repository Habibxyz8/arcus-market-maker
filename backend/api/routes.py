"""Phase 39: Minimal FastAPI routes + WS for dashboard."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse

from backend.config.settings import settings
from backend.models.schemas import BotStatusResponse, HealthResponse, MarketSnapshot, StartRequest
from backend.monitoring.logger import BOT_STARTED, BOT_STOPPED, EMERGENCY_STOP, get_logger

log = get_logger(__name__)
router = APIRouter()

# In-memory bot state (proper state machine comes in Phases 19-20)
_state: dict[str, object] = {"state": "STOPPED", "emergency": False}


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(trading_mode=settings.trading_mode.value, market=settings.market)


@router.get("/bot/status", response_model=BotStatusResponse)
async def bot_status() -> BotStatusResponse:
    return BotStatusResponse(
        state=_state["state"],  # type: ignore[arg-type]
        trading_mode=settings.trading_mode.value,
        market=settings.market,
        emergency=bool(_state["emergency"]),
    )


@router.post("/bot/start")
async def bot_start(req: StartRequest) -> JSONResponse:
    if settings.is_live and not req.confirm_live:
        raise HTTPException(status_code=400, detail="LIVE mode requires confirm_live=true")
    if _state["emergency"]:
        raise HTTPException(status_code=409, detail="Emergency stop active - reset required")
    _state["state"] = "RUNNING"
    log.info("%s mode=%s market=%s", BOT_STARTED, settings.trading_mode.value, settings.market)
    return JSONResponse({"ok": True, "state": "RUNNING"})


@router.post("/bot/pause")
async def bot_pause() -> JSONResponse:
    if _state["state"] != "RUNNING":
        raise HTTPException(status_code=409, detail="Not running")
    _state["state"] = "PAUSED"
    log.info("%s", BOT_STOPPED)
    return JSONResponse({"ok": True, "state": "PAUSED"})


@router.post("/bot/stop")
async def bot_stop() -> JSONResponse:
    _state["state"] = "STOPPED"
    log.info("%s", BOT_STOPPED)
    return JSONResponse({"ok": True, "state": "STOPPED"})


@router.post("/bot/emergency-stop")
async def bot_emergency() -> JSONResponse:
    _state["state"] = "EMERGENCY"
    _state["emergency"] = True
    log.warning("%s - all quotes should be cancelled", EMERGENCY_STOP)
    return JSONResponse({"ok": True, "state": "EMERGENCY"})


@router.post("/bot/reset-emergency")
async def bot_reset_emergency() -> JSONResponse:
    _state["emergency"] = False
    _state["state"] = "STOPPED"
    return JSONResponse({"ok": True, "state": "STOPPED"})


@router.get("/market/snapshot", response_model=MarketSnapshot)
async def market_snapshot() -> MarketSnapshot:
    # Stub until Phase 7 engine live - returns empty but typed
    return MarketSnapshot(market=settings.market, stale=True)


# Dashboard WS - pushes status every 2s (Phase 39)
@router.websocket("/ws/dashboard")
async def ws_dashboard(ws: WebSocket) -> None:
    await ws.accept()
    try:
        while True:
            payload = {
                "type": "status",
                "ts": datetime.now(timezone.utc).isoformat(),
                "state": _state["state"],
                "emergency": _state["emergency"],
                "trading_mode": settings.trading_mode.value,
                "market": settings.market,
            }
            await ws.send_text(json.dumps(payload))
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        pass
