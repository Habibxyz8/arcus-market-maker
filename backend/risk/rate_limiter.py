"""Phase 18: Internal request scheduler / rate limit protection."""
from __future__ import annotations

import asyncio
import time
from collections import deque

from backend.monitoring.logger import RATE_LIMIT_WARNING, get_logger

log = get_logger(__name__)

MAX_RPS_PAPER = 50  # millisecond HFT in PAPER (limit orders, no rate hit)
MAX_RPS_LIVE = 8  # conservative for LIVE/TESTNET per Arcus rate-limits.md


class RateLimiter:
    def __init__(self, max_rps: int | None = None) -> None:
        if max_rps is None:
            from backend.config.settings import settings
            max_rps = MAX_RPS_PAPER if settings.is_paper else MAX_RPS_LIVE
        self.max_rps = max_rps
        self._times: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.time()
            # drop old
            while self._times and now - self._times[0] > 1.0:
                self._times.popleft()
            if len(self._times) >= self.max_rps:
                sleep = 1.0 - (now - self._times[0]) + 0.05
                log.warning(RATE_LIMIT_WARNING + " throttling %.2fs", sleep)
                await asyncio.sleep(max(0, sleep))
            self._times.append(time.time())

    def usage_pct(self) -> float:
        return len(self._times) / self.max_rps * 100
