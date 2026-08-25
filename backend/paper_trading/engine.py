"""Phase 21: Paper trading engine - simulates fills/fees/inventory/PnL."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from backend.config.settings import settings


@dataclass
class PaperOrder:
    order_id: str
    client_id: str
    market: str
    side: str  # buy/sell
    price: float
    quantity: float
    filled: float = 0.0
    status: str = "open"
    created_ns: int = field(default_factory=time.time_ns)


@dataclass
class PaperFill:
    fill_id: str
    order_id: str
    market: str
    side: str
    price: float
    quantity: float
    fee: float
    notional: float
    ts_ns: int = field(default_factory=time.time_ns)


class PaperEngine:
    def __init__(self) -> None:
        self.orders: dict[str, PaperOrder] = {}
        self.fills: list[PaperFill] = []
        self.base_inventory: float = 0.0
        self.quote_balance: float = 10000.0  # starting paper USD
        self.realized_pnl: float = 0.0

    def place(self, market: str, side: str, price: float, quantity: float, client_id: str | None = None) -> PaperOrder:
        oid = f"paper-{uuid.uuid4().hex[:10]}"
        cid = client_id or f"paper-c-{uuid.uuid4().hex[:8]}"
        o = PaperOrder(order_id=oid, client_id=cid, market=market, side=side.lower(), price=price, quantity=quantity)
        self.orders[oid] = o
        return o

    def cancel(self, order_id: str) -> bool:
        o = self.orders.get(order_id)
        if not o or o.status != "open":
            return False
        o.status = "canceled"
        return True

    def cancel_all(self) -> int:
        n = 0
        for o in self.orders.values():
            if o.status == "open":
                o.status = "canceled"
                n += 1
        return n

    def simulate_market_tick(self, mid: float, spread: float = 1.0) -> list[PaperFill]:
        """Simple maker fill simulation: if mid moves through our price, fill partially."""
        new_fills: list[PaperFill] = []
        for o in list(self.orders.values()):
            if o.status != "open":
                continue
            # Fill if our limit is marketable: buy if ask <= mid? simplified: mid touches price
            should_fill = False
            if o.side == "buy" and mid <= o.price:
                should_fill = True
            if o.side == "sell" and mid >= o.price:
                should_fill = True
            # Randomize a bit: only 30% of touch = fill to avoid fake volume
            import random
            if should_fill and random.random() < 0.3:
                fill_qty = min(o.quantity - o.filled, o.quantity * 0.5 + random.random() * 0.5 * (o.quantity - o.filled))
                fill_qty = round(fill_qty, 6)
                if fill_qty <= 0:
                    continue
                fee = fill_qty * o.price * (settings.maker_fee_bps / 10000)
                fid = f"fill-{uuid.uuid4().hex[:10]}"
                f = PaperFill(fill_id=fid, order_id=o.order_id, market=o.market, side=o.side, price=o.price, quantity=fill_qty, fee=fee, notional=fill_qty * o.price)
                self.fills.append(f)
                new_fills.append(f)
                o.filled += fill_qty
                if o.filled >= o.quantity - 1e-9:
                    o.status = "filled"
                else:
                    o.status = "partial"  # partial then still open for more
                    o.status = "open"  # keep open for simulation
                # inventory
                if o.side == "buy":
                    self.base_inventory += fill_qty
                    self.quote_balance -= fill_qty * o.price + fee
                else:
                    self.base_inventory -= fill_qty
                    self.quote_balance += fill_qty * o.price - fee
        return new_fills

    def volume(self) -> float:
        return sum(f.notional for f in self.fills)

    def pnl(self, mid: float | None = None) -> dict[str, float]:
        fees = sum(f.fee for f in self.fills)
        # unrealized: inventory * mid vs avg entry (simplified: inventory * mid + quote_balance - 10000)
        unreal = 0.0
        if mid is not None:
            unreal = self.base_inventory * mid + self.quote_balance - 10000
        return {"realized": self.realized_pnl, "unrealized": unreal, "fees": fees, "net": self.realized_pnl + unreal - fees}

    def open_orders(self) -> list[PaperOrder]:
        return [o for o in self.orders.values() if o.status == "open"]
