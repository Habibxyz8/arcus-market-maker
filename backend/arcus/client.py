"""Phase 6: Official Arcus REST client - only documented endpoints, never guess auth."""
from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

from backend.authentication.signer import (
    build_cancel_payload,
    build_modify_payload,
    build_place_payload,
    canonical_json,
    sign_scheme1,
    sign_scheme2,
)
from backend.config.settings import settings
from backend.monitoring.logger import get_logger, sanitize

log = get_logger(__name__)

# Official paths per docs
PATHS = {
    "markets": "/v1/markets",
    "l2": "/v1/l2OrderbookSnapshot",
    "bbo": "/v1/bbo",
    "live_prices": "/v1/livePrices",
    "open_orders": "/v1/openOrders",
    "order_history": "/v1/orderHistory",
    "fills": "/v1/fills",
    "positions": "/v1/positions",
    "account": "/v1/account",
    "account_stats": "/v1/accountStats",
    "rate_limit": "/v1/currentRateLimitUsage",
    "place_order": "/v1/placeOrder",
    "batch_place": "/v1/batchPlaceOrders",
    "cancel_order": "/v1/cancelOrder",
    "batch_cancel": "/v1/batchCancelOrders",
    "cancel_all": "/v1/cancelAllOrders",
    "modify_order": "/v1/modifyOrder",
    "batch_modify": "/v1/batchModifyOrders",
    "dms": "/v1/scheduleCancelAllDeadMansSwitch",
    "set_leverage": "/v1/setLeverage",
}


class ArcusClient:
    """Async httpx client with Ed25519 signing per docs. No secrets logged."""

    def __init__(self, timeout: float = 10.0) -> None:
        self._client = httpx.AsyncClient(timeout=timeout, headers={"Content-Type": "application/json"})
        self._lock = asyncio.Lock()
        # Rate limit tracking (Phase 18)
        self.rate_remaining: int | None = None
        self.rate_retry_after_ms: int | None = None

    @property
    def base(self) -> str:
        return settings.active_rest_url.rstrip("/")

    def _auth_headers(self, signature: str, timestamp_ns: int) -> dict[str, str]:
        return {
            "X-API-Key": settings.arcus_api_key,
            "X-Timestamp": str(timestamp_ns),
            "X-Signature": signature,
        }

    async def _get(self, path: str, params: dict[str, Any] | None = None, signed: bool = False) -> Any:
        url = self.base + path
        headers: dict[str, str] = {}
        if signed and settings.has_credentials():
            # Read endpoints require only X-API-Key per docs, but we send it
            headers["X-API-Key"] = settings.arcus_api_key
        try:
            r = await self._client.get(url, params=params, headers=headers)
            self._capture_rate(r.headers)
            if r.status_code == 429:
                log.warning("RATE_LIMIT_WARNING %s %s", path, sanitize(r.json() if r.content else {}))
            r.raise_for_status()
            return r.json() if r.content else {}
        except httpx.HTTPStatusError as e:
            log.error("Arcus GET %s failed %s %s", path, e.response.status_code, sanitize({"body": str(e.response.text)[:500]}))
            raise
        except Exception as e:
            log.error("Arcus GET %s network error %s", path, type(e).__name__)
            raise

    async def _post(self, path: str, body: dict[str, Any], signed_payload: str | None, timestamp_ns: int | None) -> Any:
        url = self.base + path
        headers: dict[str, str] = {}
        if signed_payload is not None and timestamp_ns is not None:
            # Scheme 1: signature is over canonical payload, headers carry it
            headers = self._auth_headers(signed_payload, timestamp_ns)
        elif timestamp_ns is not None and signed_payload is not None:
            headers = self._auth_headers(signed_payload, timestamp_ns)
        # For POST with Scheme2, caller provides signature
        try:
            r = await self._client.post(url, json=body, headers=headers)
            self._capture_rate(r.headers)
            if r.status_code == 429:
                log.warning("RATE_LIMIT_WARNING POST %s", path)
            # 202 is success for async orders per docs
            if r.status_code not in (200, 201, 202):
                r.raise_for_status()
            return r.json() if r.content else {}
        except httpx.HTTPStatusError as e:
            log.error("Arcus POST %s failed %s", path, e.response.status_code)
            raise

    def _capture_rate(self, headers: httpx.Headers) -> None:
        # Arcus returns Retry-After; also track per docs rate-limits.md
        if "retry-after" in headers:
            try:
                self.rate_retry_after_ms = int(headers["retry-after"]) * 1000
            except Exception:
                pass
        # Some deployments return X-RateLimit-Remaining
        for k in ("x-ratelimit-remaining", "x-rate-limit-remaining"):
            if k in headers:
                try:
                    self.rate_remaining = int(headers[k])
                except Exception:
                    pass

    # --- Public reads (no sig needed, but send API key if present) ---

    async def get_markets(self, market: str | None = None) -> Any:
        params = {"market": market} if market else None
        return await self._get(PATHS["markets"], params=params, signed=False)

    async def get_l2(self, market_id: int) -> Any:
        return await self._get(PATHS["l2"], params={"marketId": market_id}, signed=False)

    async def get_bbo(self, market_id: int) -> Any:
        return await self._get(PATHS["bbo"], params={"marketId": market_id}, signed=False)

    async def get_live_prices(self) -> Any:
        return await self._get(PATHS["live_prices"], signed=False)

    async def get_open_orders(self) -> Any:
        return await self._get(PATHS["open_orders"], params={"address": settings.arcus_account_address}, signed=True)

    async def get_order_history(self) -> Any:
        return await self._get(PATHS["order_history"], params={"address": settings.arcus_account_address}, signed=True)

    async def get_fills(self) -> Any:
        return await self._get(PATHS["fills"], params={"address": settings.arcus_account_address}, signed=True)

    async def get_positions(self) -> Any:
        return await self._get(PATHS["positions"], params={"address": settings.arcus_account_address}, signed=True)

    async def get_account(self) -> Any:
        return await self._get(PATHS["account"], params={"address": settings.arcus_account_address}, signed=True)

    async def get_account_stats(self) -> Any:
        return await self._get(PATHS["account_stats"], params={"address": settings.arcus_account_address}, signed=True)

    async def get_rate_limit(self) -> Any:
        return await self._get(PATHS["rate_limit"], params={"address": settings.arcus_account_address}, signed=True)

    # --- Trading (signed) ---

    async def place_order(
        self,
        market_id: int,
        side: str,  # BUY/SELL
        order_type: str,  # LIMIT/MARKET
        quantity: str,
        price: str,
        time_in_force: str = "GTT",
        good_til_time: str | None = None,
        client_id: str | None = None,
        tick_size: str = "0.1",
        step_size: str = "0.001",
        reduce_only: bool = False,
    ) -> Any:
        if not settings.has_credentials():
            raise RuntimeError("No credentials for placeOrder")
        ts = time.time_ns()
        # goodTilTime per docs: µs string, must be >=1 month ahead; body uses µs, payload uses ns (µs*1000)
        if good_til_time is None:
            good_til_time = str(int(time.time() * 1_000_000) + 40 * 86400 * 1_000_000)
        g_ns = int(good_til_time) * 1000
        side_i = 0 if side.upper() == "BUY" else 1
        tif_map = {"GTT": 0, "FOK": 1, "IOC": 2, "ALO": 3}
        tif = tif_map.get(time_in_force.upper(), 0)
        payload = build_place_payload(
            address=settings.arcus_account_address,
            account_index=settings.arcus_account_index,
            client_id=client_id,
            timestamp_ns=ts,
            good_til_time_ns=g_ns,
            market_id=market_id,
            price=price,
            quantity=quantity,
            tick_size=tick_size,
            step_size=step_size,
            side=side_i,
            tif=tif,
            reduce_only=1 if reduce_only else 0,
        )
        sig = sign_scheme1(settings.arcus_api_secret, payload)
        body: dict[str, Any] = {
            "address": settings.arcus_account_address,
            "accountIndex": settings.arcus_account_index,
            "marketId": market_id,
            "orderSide": side.upper(),
            "orderType": order_type.upper(),
            "quantity": quantity,
            "price": price,
            "timeInForce": time_in_force.upper(),
            "goodTilTime": good_til_time,
            "timestamp": ts,
        }
        if client_id:
            body["clientId"] = client_id
        return await self._post(PATHS["place_order"], body, sig, ts)

    async def cancel_order(self, market_id: int, order_id: str | None = None, client_id: str | None = None) -> Any:
        if not settings.has_credentials():
            raise RuntimeError("No credentials for cancelOrder")
        ts = time.time_ns()
        payload = build_cancel_payload(
            address=settings.arcus_account_address,
            account_index=settings.arcus_account_index,
            timestamp_ns=ts,
            market_id=market_id,
            order_id=order_id,
            client_id=client_id,
        )
        sig = sign_scheme1(settings.arcus_api_secret, payload)
        body: dict[str, Any] = {
            "address": settings.arcus_account_address,
            "accountIndex": settings.arcus_account_index,
            "marketId": market_id,
            "timestamp": ts,
        }
        if order_id:
            body["kind"] = "orderId"
            body["orderId"] = order_id
        else:
            body["kind"] = "clientId"
            body["clientId"] = client_id
        return await self._post(PATHS["cancel_order"], body, sig, ts)

    async def cancel_all(self) -> Any:
        if not settings.has_credentials():
            raise RuntimeError("No credentials for cancelAll")
        ts = time.time_ns()
        body: dict[str, Any] = {"address": settings.arcus_account_address, "accountIndex": settings.arcus_account_index}
        sig = sign_scheme2(settings.arcus_api_secret, ts, "cancelAllOrders", body)
        return await self._post(PATHS["cancel_all"], body, sig, ts)

    async def modify_order(
        self,
        market_id: int,
        order_id: str,
        price: str,
        quantity: str,
        tick_size: str = "0.1",
        step_size: str = "0.001",
        side: str = "BUY",
        time_in_force: str = "GTT",
        good_til_time: str | None = None,
        client_id: str | None = None,
        reduce_only: bool = False,
    ) -> Any:
        if not settings.has_credentials():
            raise RuntimeError("No credentials for modifyOrder")
        ts = time.time_ns()
        if good_til_time is None:
            good_til_time = str(int(time.time() * 1_000_000) + 40 * 86400 * 1_000_000)
        g_ns = int(good_til_time) * 1000
        side_i = 0 if side.upper() == "BUY" else 1
        tif_map = {"GTT": 0, "FOK": 1, "IOC": 2, "ALO": 3}
        tif = tif_map.get(time_in_force.upper(), 0)
        payload = build_modify_payload(
            address=settings.arcus_account_address,
            account_index=settings.arcus_account_index,
            timestamp_ns=ts,
            good_til_time_ns=g_ns,
            market_id=market_id,
            order_id=order_id,
            client_id=client_id,
            price=price,
            quantity=quantity,
            tick_size=tick_size,
            step_size=step_size,
            side=side_i,
            tif=tif,
            reduce_only=1 if reduce_only else 0,
        )
        sig = sign_scheme1(settings.arcus_api_secret, payload)
        body: dict[str, Any] = {
            "address": settings.arcus_account_address,
            "accountIndex": settings.arcus_account_index,
            "marketId": market_id,
            "orderId": order_id,
            "price": price,
            "quantity": quantity,
            "timeInForce": time_in_force.upper(),
            "goodTilTime": good_til_time,
            "timestamp": ts,
        }
        if client_id:
            body["clientId"] = client_id
        return await self._post(PATHS["modify_order"], body, sig, ts)

    async def batch_place_orders(self, orders: list[dict[str, Any]], tick_size: str = "0.1", step_size: str = "0.001") -> Any:
        if not settings.has_credentials():
            raise RuntimeError("No credentials for batchPlace")
        ts = time.time_ns()
        signed_orders: list[dict[str, Any]] = []
        for o in orders:
            g_ns = int(o["goodTilTime"]) * 1000
            side_i = 0 if o["orderSide"].upper() == "BUY" else 1
            tif_map = {"GTT": 0, "FOK": 1, "IOC": 2, "ALO": 3}
            tif = tif_map.get(o.get("timeInForce", "GTT").upper(), 0)
            payload = build_place_payload(
                address=settings.arcus_account_address,
                account_index=settings.arcus_account_index,
                client_id=o.get("clientId"),
                timestamp_ns=ts,
                good_til_time_ns=g_ns,
                market_id=o["marketId"],
                price=o["price"],
                quantity=o["quantity"],
                tick_size=tick_size,
                step_size=step_size,
                side=side_i,
                tif=tif,
                reduce_only=1 if o.get("reduceOnly") else 0,
            )
            sig = sign_scheme1(settings.arcus_api_secret, payload)
            copy = dict(o)
            copy["address"] = settings.arcus_account_address
            copy["accountIndex"] = settings.arcus_account_index
            copy["timestamp"] = ts
            copy["signature"] = sig
            signed_orders.append(copy)
        # X-Signature must be present per docs: set to any element's sig
        any_sig = signed_orders[0]["signature"] if signed_orders else ""
        url = self.base + PATHS["batch_place"]
        headers = self._auth_headers(any_sig, ts)
        r = await self._client.post(url, json={"orders": signed_orders}, headers=headers)
        r.raise_for_status()
        return r.json() if r.content else {}

    async def schedule_dms(self, timeout_sec: int) -> Any:
        if not settings.has_credentials():
            raise RuntimeError("No credentials for DMS")
        ts = time.time_ns()
        body: dict[str, Any] = {"address": settings.arcus_account_address, "accountIndex": settings.arcus_account_index, "timeout": timeout_sec}
        sig = sign_scheme2(settings.arcus_api_secret, ts, "scheduleCancelAllDeadMansSwitch", body)
        return await self._post(PATHS["dms"], body, sig, ts)

    async def set_leverage(self, market_id: int, leverage: float) -> Any:
        if not settings.has_credentials():
            raise RuntimeError("No credentials for setLeverage")
        ts = time.time_ns()
        body: dict[str, Any] = {"address": settings.arcus_account_address, "accountIndex": settings.arcus_account_index, "marketId": market_id, "leverage": str(leverage)}
        sig = sign_scheme2(settings.arcus_api_secret, ts, "setLeverage", body)
        return await self._post(PATHS["set_leverage"], body, sig, ts)

    async def close(self) -> None:
        await self._client.aclose()
