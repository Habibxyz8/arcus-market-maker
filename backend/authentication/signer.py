"""Phase 5: Official Arcus Ed25519 signing - Scheme 1 (typed payload) + Scheme 2 (legacy).

Never logs secrets. Uses cryptography Ed25519. Source: https://docs.arcus.xyz/api-reference/authentication.md
"""
from __future__ import annotations

import json
import time
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from backend.monitoring.logger import get_logger

log = get_logger(__name__)

# Operation enums per docs
OP_PLACE = 1
OP_CANCEL = 2
OP_MODIFY = 3
OP_PLACE_UNTRIGGERED = 4  # TPSL


def _load_private_key(hex_secret: str) -> Ed25519PrivateKey:
    """Secret is 64-hex (32 bytes) or 128-hex seed handling."""
    s = hex_secret.strip().lower().replace("0x", "")
    if len(s) == 64:
        raw = bytes.fromhex(s)
        return Ed25519PrivateKey.from_private_bytes(raw)
    if len(s) == 128:
        # Some exports give 64-byte private+public concatenated; take first 32
        raw = bytes.fromhex(s[:64])
        return Ed25519PrivateKey.from_private_bytes(raw)
    raise ValueError(f"ARCUS_API_SECRET must be 64 hex chars (32 bytes), got {len(s)}")


def sign_bytes(private_hex: str, msg: bytes) -> str:
    """Ed25519 sign raw bytes -> 128 hex lowercase."""
    key = _load_private_key(private_hex)
    return key.sign(msg).hex()


def canonical_json(obj: dict[str, Any]) -> str:
    return json.dumps(obj, separators=(",", ":"), sort_keys=True)


def _ticks(price: str | float | int, tick_size: str) -> int:
    from decimal import Decimal, InvalidOperation

    try:
        n = Decimal(str(price)) / Decimal(str(tick_size))
    except InvalidOperation as e:
        raise ValueError(f"Invalid price/tickSize: {e}") from e
    if n != n.to_integral_value():
        raise ValueError(f"{price} is not a multiple of tickSize {tick_size}")
    return int(n)


def _quantums(qty: str | float | int, step_size: str) -> int:
    from decimal import Decimal, InvalidOperation

    try:
        n = Decimal(str(qty)) / Decimal(str(step_size))
    except InvalidOperation as e:
        raise ValueError(f"Invalid qty/stepSize: {e}") from e
    if n != n.to_integral_value():
        raise ValueError(f"{qty} is not a multiple of stepSize {step_size}")
    return int(n)


def build_place_payload(
    *,
    address: str,
    account_index: int,
    client_id: str | None,
    timestamp_ns: int,
    good_til_time_ns: int,
    market_id: int,
    price: str | float,
    quantity: str | float,
    tick_size: str,
    step_size: str,
    side: int,  # 0 buy, 1 sell
    tif: int,  # 0 GTT,1 FOK,2 IOC,3 ALO
    reduce_only: int = 0,
    op: int = OP_PLACE,
) -> str:
    """Returns canonical JSON string to sign for placeOrder (Scheme 1)."""
    p = _ticks(price, tick_size)
    q = _quantums(quantity, step_size)
    ad = address.lower()
    obj: dict[str, Any] = {
        "ad": ad,
        "ai": account_index,
        "ct": timestamp_ns,
        "g": good_til_time_ns,
        "m": market_id,
        "op": op,
        "p": p,
        "q": q,
        "r": reduce_only,
        "s": side,
        "t": tif,
        "v": 1,
    }
    if client_id:
        obj["c"] = client_id.lower()
    # key-sorted compact
    return canonical_json(obj)


def build_cancel_payload(
    *,
    address: str,
    account_index: int,
    timestamp_ns: int,
    market_id: int,
    order_id: str | None = None,
    client_id: str | None = None,
) -> str:
    if not order_id and not client_id:
        raise ValueError("cancel requires orderId or clientId")
    if order_id and client_id:
        raise ValueError("cancel requires exactly one of orderId or clientId")
    obj: dict[str, Any] = {"ad": address.lower(), "ai": account_index, "ct": timestamp_ns, "m": market_id, "op": OP_CANCEL, "v": 1}
    if order_id:
        obj["id"] = order_id
    if client_id:
        obj["c"] = client_id.lower()
    return canonical_json(obj)


def build_modify_payload(
    *,
    address: str,
    account_index: int,
    timestamp_ns: int,
    good_til_time_ns: int,
    market_id: int,
    order_id: str,
    client_id: str | None,
    price: str | float,
    quantity: str | float,
    tick_size: str,
    step_size: str,
    side: int,
    tif: int,
    reduce_only: int = 0,
) -> str:
    p = _ticks(price, tick_size)
    q = _quantums(quantity, step_size)
    obj: dict[str, Any] = {
        "ad": address.lower(),
        "ai": account_index,
        "ct": timestamp_ns,
        "g": good_til_time_ns,
        "id": order_id,
        "m": market_id,
        "op": OP_MODIFY,
        "p": p,
        "q": q,
        "r": reduce_only,
        "s": side,
        "t": tif,
        "v": 1,
    }
    if client_id:
        obj["c"] = client_id.lower()
    return canonical_json(obj)


def sign_scheme1(private_hex: str, canonical_payload: str) -> str:
    """Scheme 1: ed25519(canonical_payload) - payload IS the message."""
    return sign_bytes(private_hex, canonical_payload.encode())


def sign_scheme2(private_hex: str, timestamp_ns: int, action: str, body: dict[str, Any]) -> str:
    """Scheme 2: ed25519(timestamp + action + canonical_json(body)) - for cancelAll, setLeverage, WS auth."""
    msg = f"{timestamp_ns}{action}{canonical_json(body)}".encode()
    return sign_bytes(private_hex, msg)


def now_ns() -> int:
    return time.time_ns()


def good_til_future_ns(months_ahead: int = 1) -> int:
    """GoodTilTime must be >=1 month ahead; default +40 days in ns."""
    return (int(time.time()) + 40 * 86400) * 1_000_000_000  # ns, caller converts to µs*1000 as needed per docs


# Never expose secrets in repr
__all__ = [
    "sign_scheme1",
    "sign_scheme2",
    "build_place_payload",
    "build_cancel_payload",
    "build_modify_payload",
    "canonical_json",
]
