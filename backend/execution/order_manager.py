"""Phase 16-17: Order management + reconciliation, duplicate protection."""
from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from backend.monitoring.logger import get_logger

log = get_logger(__name__)


@dataclass
class OrderState:
    order_id: str
    client_id: str | None
    market: str
    side: str
    price: float
    quantity: float
    filled: float = 0.0
    status: str = "open"  # open/filled/canceled/rejected
    created_ns: int = field(default_factory=time.time_ns)
    updated_ns: int = field(default_factory=time.time_ns)


class OrderManager:
    def __init__(self) -> None:
        self.orders: dict[str, OrderState] = {}
        self._seen_client_ids: set[str] = set()
        self._lock = asyncio.Lock()

    async def track(self, o: OrderState) -> None:
        async with self._lock:
            if o.client_id and o.client_id in self._seen_client_ids and o.order_id not in self.orders:
                log.warning("Duplicate clientId %s blocked", o.client_id)
                raise ValueError(f"Duplicate clientId {o.client_id}")
            self.orders[o.order_id] = o
            if o.client_id:
                self._seen_client_ids.add(o.client_id)

    async def on_fill(self, order_id: str, fill_qty: float, is_full: bool = False) -> None:
        async with self._lock:
            o = self.orders.get(order_id)
            if not o:
                log.warning("Fill for unknown order %s", order_id)
                return
            o.filled += fill_qty
            o.status = "filled" if is_full or o.filled >= o.quantity else "partial"
            o.updated_ns = time.time_ns()

    async def on_cancel(self, order_id: str) -> None:
        async with self._lock:
            if order_id in self.orders:
                self.orders[order_id].status = "canceled"
                self.orders[order_id].updated_ns = time.time_ns()

    def open_orders(self) -> list[OrderState]:
        return [o for o in self.orders.values() if o.status == "open"]

    def is_stale(self, order_id: str, max_age_sec: int) -> bool:
        o = self.orders.get(order_id)
        if not o:
            return False
        age = (time.time_ns() - o.created_ns) / 1e9
        return age > max_age_sec and o.status == "open"

    def new_client_id(self) -> str:
        return f"am-{uuid.uuid4().hex[:12]}"
