"""Phase 20: Emergency stop + dead man's switch."""
from __future__ import annotations

import asyncio
from typing import Any

from backend.arcus.client import ArcusClient
from backend.config.settings import settings
from backend.monitoring.logger import EMERGENCY_STOP, get_logger

log = get_logger(__name__)


class EmergencyManager:
    def __init__(self) -> None:
        self.active = False
        self._dms_task: asyncio.Task | None = None

    def trigger(self, reason: str) -> None:
        self.active = True
        log.warning("%s reason=%s", EMERGENCY_STOP, reason)

    def reset(self) -> None:
        self.active = False
        log.info("Emergency reset")

    async def start_dms(self, client: ArcusClient) -> None:
        if settings.is_paper:
            return
        async def loop() -> None:
            while not self.active:
                try:
                    await client.schedule_dms(settings.dead_mans_switch_timeout_sec)
                    log.info("DMS refreshed %ss", settings.dead_mans_switch_timeout_sec)
                except Exception as e:
                    log.error("DMS failed %s", type(e).__name__)
                await asyncio.sleep(settings.dead_mans_switch_timeout_sec // 2 or 5)
        self._dms_task = asyncio.create_task(loop())

    async def stop_dms(self) -> None:
        if self._dms_task:
            self._dms_task.cancel()
            try:
                await self._dms_task
            except asyncio.CancelledError:
                pass
