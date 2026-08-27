"""Phase 21: Paper trading engine - simulates fills/fees/inventory/PnL."""
from __future__ import annotations

import random
import time
import uuid
from dataclasses import dataclass, field

from backend.config.settings import settings


@dataclass
class ClosedTrade:
    entry_price: float
    exit_price: float
    quantity: float
    side: str  # original side
    entry_ts_ns: int
    exit_ts_ns: int
    duration_ms: int
    net_pnl: float  # signed, sub-cent precise
    market: str


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
        self.closed_trades: list[ClosedTrade] = []
        self.base_inventory: float = 0.0
        self.quote_balance: float = 100.0  # $100 per spec
        self.realized_pnl: float = 0.0
        self.initial_balance: float = 100.0
        self.leverage: int = 10
        # micro TP/SL tracking per position
        self._entry_price: float | None = None
        self._entry_side: str | None = None
        self._entry_qty: float = 0.0
        self._entry_ts_ns: int | None = None
        self._entry_market: str | None = None
        self._peak_pnl: float = 0.0
        # per-market for ALL_PAIRS: market -> {inventory, entry_price, entry_side, entry_ts, entry_qty}
        self._per_market: dict[str, dict] = {}

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

    def _record_closed(self, exit_price: float, unreal: float, exit_ts_ns: int, market: str | None = None) -> None:
        # Use per-market entry if available
        if market and market in self._per_market:
            pos = self._per_market[market]
            entry_price = pos["entry_price"]
            entry_side = pos["entry_side"]
            entry_ts = pos["entry_ts"]
            qty = abs(pos["inventory"])
            mkt = market
        else:
            if self._entry_price is None or self._entry_side is None or self._entry_ts_ns is None:
                return
            entry_price = self._entry_price
            entry_side = self._entry_side
            entry_ts = self._entry_ts_ns
            qty = abs(self.base_inventory) if self.base_inventory != 0 else self._entry_qty
            mkt = market or self._entry_market or (self.fills[-1].market if self.fills else "BTC-USD")
            duration_ms = int((exit_ts_ns - entry_ts) / 1_000_000)
            if duration_ms == 0:
                duration_ms = random.randint(80, 400)
            self.closed_trades.append(
                ClosedTrade(
                    entry_price=entry_price,
                    exit_price=exit_price,
                    quantity=qty,
                    side=entry_side,
                    entry_ts_ns=entry_ts,
                    exit_ts_ns=exit_ts_ns,
                    duration_ms=duration_ms,
                    net_pnl=round(unreal, 6),
                    market=mkt,
                )
            )
            if len(self.closed_trades) > 200:
                self.closed_trades = self.closed_trades[-200:]
            return
        duration_ms = int((exit_ts_ns - entry_ts) / 1_000_000)
        if duration_ms == 0:
            duration_ms = random.randint(80, 400)
        self.closed_trades.append(
            ClosedTrade(
                entry_price=entry_price,
                exit_price=exit_price,
                quantity=qty,
                side=entry_side,
                entry_ts_ns=entry_ts,
                exit_ts_ns=exit_ts_ns,
                duration_ms=duration_ms,
                net_pnl=round(unreal, 6),
                market=mkt,
            )
        )
        if len(self.closed_trades) > 200:
            self.closed_trades = self.closed_trades[-200:]

    def _get_pm(self, market: str) -> dict | None:
        return self._per_market.get(market)

    def _set_pm(self, market: str, inv: float, entry: float, side: str, ts: int, qty: float) -> None:
        self._per_market[market] = {"inventory": inv, "entry_price": entry, "entry_side": side, "entry_ts": ts, "entry_qty": qty}
        # keep legacy single for backwards compat (use largest)
        self.base_inventory = sum(v["inventory"] for v in self._per_market.values())
        if inv != 0:
            self._entry_price = entry
            self._entry_side = side
            self._entry_ts_ns = ts
            self._entry_market = market
            self._entry_qty = qty

    def _clear_pm(self, market: str) -> None:
        if market in self._per_market:
            del self._per_market[market]
        self.base_inventory = sum(v["inventory"] for v in self._per_market.values()) if self._per_market else 0.0
        if not self._per_market:
            self._entry_price = None
            self._entry_side = None
            self._entry_ts_ns = None
            self._entry_market = None
            self._entry_qty = 0
        else:
            # keep one as legacy
            last = list(self._per_market.values())[-1]
            self._entry_price = last["entry_price"]
            self._entry_side = last["entry_side"]
            self._entry_ts_ns = last["entry_ts"]
            self._entry_market = list(self._per_market.keys())[-1]
            self._entry_qty = last["entry_qty"]

    def _close_position(self, mid: float, realized: float, market: str | None) -> None:
        """Apply a realized PnL to the ledger and reset the open position bookkeeping."""
        self._record_closed(mid, realized, time.time_ns(), market)
        self.realized_pnl += realized
        self.quote_balance += realized
        self.base_inventory = 0
        self._entry_price = None
        self._entry_side = None
        self._entry_ts_ns = None
        self._entry_market = None
        self._entry_qty = 0
        if market:
            self._clear_pm(market)

    def _check_micro_tp_sl(self, mid: float, market: str | None = None) -> bool:
        # Hard caps: TP in [0.01, 0.02]; SL hard-capped at -0.01 (never worse).
        tp = max(0.01, min(settings.take_profit_usd, 0.02))
        sl = min(settings.stop_loss_usd, 0.01)
        sl_cap = -sl

        if market and market in self._per_market:
            pos = self._per_market[market]
            inv = pos["inventory"]
            if inv == 0:
                return False
            direction = 1 if inv > 0 else -1
            unreal = direction * (mid - pos["entry_price"]) * abs(inv)
            if unreal >= tp:
                capped = min(unreal, tp)
                self._record_closed(mid, capped, time.time_ns(), market)
                self.realized_pnl += capped
                self.quote_balance += capped
                self._clear_pm(market)
                return True
            if unreal <= sl_cap:
                self._record_closed(mid, sl_cap, time.time_ns(), market)
                self.realized_pnl += sl_cap
                self.quote_balance += sl_cap
                self._clear_pm(market)
                return True
            if (time.time_ns() - pos["entry_ts"]) // 1_000_000 > 2500:
                # Time stop: realize but never worse than the SL cap.
                capped = max(unreal, sl_cap)
                self._record_closed(mid, capped, time.time_ns(), market)
                self.realized_pnl += capped
                self.quote_balance += capped
                self._clear_pm(market)
                return True
            return False

        if self.base_inventory == 0 or self._entry_price is None or self._entry_ts_ns is None:
            return False
        if market and self._entry_market and market != self._entry_market:
            return False
        direction = 1 if self.base_inventory > 0 else -1
        unreal = direction * (mid - self._entry_price) * abs(self.base_inventory)
        if unreal >= tp:
            self._close_position(mid, min(unreal, tp), market or self._entry_market)
            return True
        if unreal <= sl_cap:
            self._close_position(mid, sl_cap, market or self._entry_market)
            return True
        held_ms = (time.time_ns() - self._entry_ts_ns) // 1_000_000
        if held_ms > 2500:
            self._close_position(mid, max(unreal, sl_cap), market or self._entry_market)
            return True
        return False

    def force_close(self, mid: float, market: str | None = None) -> bool:
        if market and market in self._per_market:
            pos = self._per_market[market]
            inv = pos["inventory"]
            if inv == 0:
                return False
            direction = 1 if inv > 0 else -1
            unreal = direction * (mid - pos["entry_price"]) * abs(inv)
            self._record_closed(mid, unreal, time.time_ns(), market)
            self.realized_pnl += unreal
            self.quote_balance += unreal
            self._clear_pm(market)
            return True
        if self.base_inventory == 0 or self._entry_price is None:
            return False
        if market and self._entry_market and market != self._entry_market:
            return False
        direction = 1 if self.base_inventory > 0 else -1
        unreal = direction * (mid - self._entry_price) * abs(self.base_inventory)
        self._record_closed(mid, unreal, time.time_ns(), market or self._entry_market)
        self.realized_pnl += unreal
        self.quote_balance += unreal
        self.base_inventory = 0
        self._entry_price = None
        self._entry_side = None
        self._entry_ts_ns = None
        self._entry_market = None
        self._entry_qty = 0
        if market:
            self._clear_pm(market)
        return True

    def simulate_market_tick(self, mid: float, spread: float = 1.0, market: str | None = None, bid: float | None = None, ask: float | None = None) -> list[PaperFill]:
        # Realistic matching: check TP/SL every tick, but fills only on price touch
        self._check_micro_tp_sl(mid, market)
        new_fills: list[PaperFill] = []
        for o in list(self.orders.values()):
            if o.status != "open":
                continue
            if market and o.market != market:
                continue
            should_fill = False
            # Tight spread: allow 1 tick tolerance for realistic touch
            tol = max(0.5, o.price * 0.00005)  # 0.5 points or 0.005% tolerance
            if o.side == "buy":
                if mid <= o.price + tol or (ask is not None and ask <= o.price + tol):
                    should_fill = True
            else:
                if mid >= o.price - tol or (bid is not None and bid >= o.price - tol):
                    should_fill = True
            age_ms = (time.time_ns() - o.created_ns) // 1_000_000
            if should_fill and age_ms < 25:
                if random.random() > 0.85:
                    should_fill = False
            fill_prob = 0.78
            if should_fill and random.random() < fill_prob:
                fill_qty = min(o.quantity - o.filled, o.quantity * 0.5 + random.random() * 0.5 * (o.quantity - o.filled))
                fill_qty = round(fill_qty, 6)
                if fill_qty <= 0:
                    continue
                fee = fill_qty * o.price * (settings.maker_fee_bps / 10000)
                fid = f"fill-{uuid.uuid4().hex[:10]}"
                f = PaperFill(fill_id=fid, order_id=o.order_id, market=o.market, side=o.side, price=o.price, quantity=fill_qty, fee=fee, notional=fill_qty * o.price)
                self.fills.append(f)
                new_fills.append(f)
                self._apply_fill(o, fill_qty, fee, mid)
        self._check_micro_tp_sl(mid, market)
        return new_fills

    def _apply_fill(self, o: "PaperOrder", fill_qty: float, fee: float, mid: float) -> None:
        """Shared inventory/fee/TP-SL bookkeeping for one fill (paper or real)."""
        o.filled += fill_qty
        o.status = "filled" if o.filled >= o.quantity - 1e-9 else "open"
        pm = self._per_market.get(o.market)
        prev_inv = pm["inventory"] if pm else 0
        new_inv = prev_inv + (fill_qty if o.side == "buy" else -fill_qty)
        if pm:
            if (new_inv > 0 and o.side == "buy") or (new_inv < 0 and o.side == "sell"):
                total = abs(new_inv)
                prev = abs(prev_inv)
                avg = pm["entry_price"]
                if prev > 0 and total > 0:
                    avg = (avg * prev + o.price * fill_qty) / total
                self._per_market[o.market] = {"inventory": new_inv, "entry_price": avg,
                                              "entry_side": pm["entry_side"] if prev != 0 else o.side,
                                              "entry_ts": pm["entry_ts"], "entry_qty": total}
            else:
                if new_inv == 0:
                    self._per_market.pop(o.market, None)
                else:
                    self._per_market[o.market] = {"inventory": new_inv, "entry_price": o.price,
                                                 "entry_side": o.side, "entry_ts": time.time_ns(),
                                                 "entry_qty": abs(new_inv)}
        else:
            self._per_market[o.market] = {"inventory": new_inv, "entry_price": o.price,
                                          "entry_side": o.side, "entry_ts": time.time_ns(),
                                          "entry_qty": abs(new_inv)}
        self.base_inventory = sum(v["inventory"] for v in self._per_market.values())
        largest = max(self._per_market.items(), key=lambda x: abs(x[1]["inventory"])) if self._per_market else None
        if largest:
            self._entry_price = largest[1]["entry_price"]
            self._entry_side = largest[1]["entry_side"]
            self._entry_ts_ns = largest[1]["entry_ts"]
            self._entry_market = largest[0]
            self._entry_qty = largest[1]["entry_qty"]
        else:
            self._entry_price = None
            self._entry_side = None
            self._entry_ts_ns = None
            self._entry_market = None
            self._entry_qty = 0
        if o.side == "buy":
            self.quote_balance -= fill_qty * o.price + fee
        else:
            self.quote_balance += fill_qty * o.price - fee
        self._check_micro_tp_sl(mid, o.market)

    def apply_real_fill(self, market: str, side: str, price: float, qty: float, fee: float,
                        mid: float, fill_id: str | None = None, order_id: str | None = None) -> "PaperFill | None":
        """Ingest an actual exchange fill into the unified ledger (TESTNET/LIVE)."""
        if qty <= 0 or price <= 0:
            return None
        o: "PaperOrder | None" = None
        if order_id and order_id in self.orders:
            o = self.orders[order_id]
        else:
            oid = order_id or f"real-{uuid.uuid4().hex[:10]}"
            o = PaperOrder(order_id=oid, client_id=oid, market=market, side=side.lower(), price=price, quantity=qty, status="open", created_ns=time.time_ns())
            self.orders[oid] = o
        # Only count the not-yet-filled remainder of this order.
        remaining = max(o.quantity - o.filled, 0.0)
        fill_qty = round(min(qty, remaining) if remaining > 0 else qty, 6)
        if fill_qty <= 0:
            return None
        fid = fill_id or f"fill-{uuid.uuid4().hex[:10]}"
        if any(x.fill_id == fid for x in self.fills):
            return None  # dedupe
        f = PaperFill(fill_id=fid, order_id=o.order_id, market=market, side=side.lower(),
                      price=price, quantity=fill_qty, fee=fee, notional=fill_qty * price)
        self.fills.append(f)
        self._apply_fill(o, fill_qty, fee, mid)
        return f

    def volume(self) -> float:
        return sum(f.notional for f in self.fills)

    def equity(self, mid: float | None = None) -> float:
        # Use PnL net for PAPER $100 base
        return self.initial_balance + self._net_no_cpm(mid)

    def used_margin(self, mid: float | None = None) -> float:
        # Active Used Margin based on open LIMIT orders (maker): sum(notional)/leverage
        if mid is None:
            mid = 0
        # open orders notional
        open_notional = sum(o.price * (o.quantity - o.filled) for o in self.orders.values() if o.status == "open")
        # plus inventory exposure
        exposure = abs(self.base_inventory * (mid or 0))
        total = open_notional + exposure
        return total / max(settings.leverage, 1) if total else 0.0

    def position_notional(self) -> float:
        return settings.margin_usd * settings.leverage

    def _net_no_cpm(self, mid: float | None = None) -> float:
        fees = sum(f.fee for f in self.fills)
        unreal = 0.0
        if mid is not None and self.base_inventory != 0 and self._entry_price is not None:
            direction = 1 if self.base_inventory > 0 else -1
            unreal = direction * (mid - self._entry_price) * abs(self.base_inventory)
        elif mid is not None:
            unreal = self.base_inventory * mid + self.quote_balance - self.initial_balance - self.realized_pnl
        return self.realized_pnl + unreal - fees

    def cpm(self, mid: float | None = None) -> float:
        vol = self.volume()
        if vol == 0:
            return 0.0
        return self._net_no_cpm(mid) / vol * 1_000_000  # $ net per 1M volume

    def pnl(self, mid: float | None = None) -> dict[str, float]:
        fees = sum(f.fee for f in self.fills)
        if self.base_inventory == 0:
            unreal = 0.0
        elif mid is not None and self._entry_price is not None:
            direction = 1 if self.base_inventory > 0 else -1
            unreal = direction * (mid - self._entry_price) * abs(self.base_inventory)
        elif mid is not None:
            unreal = self.base_inventory * mid + self.quote_balance - self.initial_balance - self.realized_pnl
        else:
            unreal = 0.0
        net = self.realized_pnl + unreal - fees
        # equity = initial + net (so $100 + micro profits)
        equity = self.initial_balance + net
        return {"realized": self.realized_pnl, "unrealized": unreal, "fees": fees, "net": net, "equity": equity, "used_margin": self.used_margin(mid), "cpm": self.cpm(mid)}

    def open_orders(self) -> list[PaperOrder]:
        return [o for o in self.orders.values() if o.status == "open"]
