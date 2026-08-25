"""Phase 5: Signer correctness + never-log guards."""
import json
import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519

from backend.authentication.signer import (
    build_cancel_payload,
    build_place_payload,
    canonical_json,
    sign_scheme1,
    sign_scheme2,
)


def test_canonical_sorted() -> None:
    assert canonical_json({"b": 1, "a": 2}) == '{"a":2,"b":1}'


def test_build_place_payload_keys_sorted() -> None:
    p = build_place_payload(
        address="0xABC", account_index=0, client_id=None,
        timestamp_ns=123, good_til_time_ns=456, market_id=1,
        price="100.5", quantity="0.01", tick_size="0.1", step_size="0.001",
        side=0, tif=0
    )
    obj = json.loads(p)
    assert list(obj.keys()) == sorted(obj.keys())
    assert obj["ad"] == "0xabc"
    assert obj["op"] == 1
    assert "c" not in obj
    # With client id, lowercased and present
    p2 = build_place_payload(
        address="0xABC", account_index=0, client_id="MyID",
        timestamp_ns=123, good_til_time_ns=456, market_id=1,
        price="100.5", quantity="0.01", tick_size="0.1", step_size="0.001",
        side=0, tif=0
    )
    assert json.loads(p2)["c"] == "myid"


def test_build_cancel_requires_one() -> None:
    with pytest.raises(ValueError):
        build_cancel_payload(address="0xabc", account_index=0, timestamp_ns=1, market_id=1)
    with pytest.raises(ValueError):
        build_cancel_payload(address="0xabc", account_index=0, timestamp_ns=1, market_id=1, order_id="a", client_id="b")


def test_sign_scheme1_verifies() -> None:
    priv = ed25519.Ed25519PrivateKey.generate()
    hex_priv = priv.private_bytes_raw().hex()
    pub = priv.public_key()
    payload = '{"ad":"0xabc","ai":0,"ct":1,"g":2,"m":1,"op":1,"p":1,"q":1,"r":0,"s":0,"t":0,"v":1}'
    sig_hex = sign_scheme1(hex_priv, payload)
    pub.verify(bytes.fromhex(sig_hex), payload.encode())


def test_sign_scheme2_verifies() -> None:
    priv = ed25519.Ed25519PrivateKey.generate()
    hex_priv = priv.private_bytes_raw().hex()
    pub = priv.public_key()
    body = {"marketId": 1}
    ts = 1234567890000000000
    sig = sign_scheme2(hex_priv, ts, "cancelAllOrders", body)
    expected_msg = f"{ts}cancelAllOrders{canonical_json(body)}".encode()
    pub.verify(bytes.fromhex(sig), expected_msg)
