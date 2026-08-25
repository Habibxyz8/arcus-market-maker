"""Pydantic schemas - typed API contracts."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    trading_mode: str
    market: str
    version: str = "0.3.0"


class BotStatusResponse(BaseModel):
    state: Literal["STOPPED", "RUNNING", "PAUSED", "EMERGENCY"] = "STOPPED"
    trading_mode: str
    market: str
    emergency: bool = False


class MarketSnapshot(BaseModel):
    market: str
    bid: float | None = None
    ask: float | None = None
    mid: float | None = None
    spread: float | None = None
    spread_bps: float | None = None
    timestamp: datetime | None = None
    sequence: int | None = None
    stale: bool = False


class OrderOut(BaseModel):
    order_id: str
    market: str
    side: Literal["buy", "sell"]
    price: float
    quantity: float
    filled_quantity: float = 0
    remaining_quantity: float = 0
    status: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class FillOut(BaseModel):
    fill_id: str
    order_id: str
    market: str
    side: Literal["buy", "sell"]
    price: float
    quantity: float
    notional: float
    fee: float = 0
    timestamp: datetime | None = None


class StartRequest(BaseModel):
    confirm_live: bool = Field(default=False, description="Must be true to start LIVE")
