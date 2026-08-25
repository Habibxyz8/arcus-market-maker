"""Phase 3: FastAPI entry with async lifespan, CORS, typed errors."""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import router
from backend.config.settings import settings
from backend.database.db import init_db
from backend.monitoring.logger import get_logger

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[no-untyped-def]
    log.info("Starting backend mode=%s market=%s", settings.trading_mode.value, settings.market)
    try:
        await init_db()
        log.info("DB initialized at %s", settings.database_url.split("://")[0] + "://...")
    except Exception as e:  # noqa: BLE001
        log.error("DB init failed: %s", e)
    yield
    log.info("Shutting down backend")


app = FastAPI(title="Arcus Market Maker", version="0.3.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": "arcus-market-maker", "mode": settings.trading_mode.value}
