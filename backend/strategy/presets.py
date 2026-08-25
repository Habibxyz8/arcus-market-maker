"""Presets: Guru, Apex, Alpha v2 + custom. Each maps to spread/skew/refresh/TP/SL."""
from __future__ import annotations

PRESETS: dict[str, dict] = {
    "guru": {
        "bid_spread_bps": 6, "ask_spread_bps": 6,
        "quote_refresh_interval_ms": 400,
        "inventory_skew_factor": 0.4,
        "take_profit_usd": 0.015, "stop_loss_usd": 0.009,
        "leverage": 10, "desc": "Tightest, fastest — micro-scalp",
    },
    "apex": {
        "bid_spread_bps": 10, "ask_spread_bps": 10,
        "quote_refresh_interval_ms": 600,
        "inventory_skew_factor": 0.5,
        "take_profit_usd": 0.02, "stop_loss_usd": 0.008,
        "leverage": 10, "desc": "Balanced 1-2c target",
    },
    "alpha_v2": {
        "bid_spread_bps": 14, "ask_spread_bps": 14,
        "quote_refresh_interval_ms": 800,
        "inventory_skew_factor": 0.6,
        "take_profit_usd": 0.02, "stop_loss_usd": 0.007,
        "leverage": 10, "desc": "Wider, safer, sub-cent SL",
    },
    "custom": {
        "bid_spread_bps": 10, "ask_spread_bps": 10,
        "quote_refresh_interval_ms": 500,
        "inventory_skew_factor": 0.5,
        "take_profit_usd": 0.015, "stop_loss_usd": 0.009,
        "leverage": 10, "desc": "User-tuned",
    },
}

def apply_preset(name: str, settings_obj) -> None:  # type: ignore[no-untyped-def]
    p = PRESETS.get(name.lower(), PRESETS["guru"])
    for k in ("bid_spread_bps","ask_spread_bps","quote_refresh_interval_ms","inventory_skew_factor","take_profit_usd","stop_loss_usd","leverage"):
        if hasattr(settings_obj, k):
            setattr(settings_obj, k, p[k])
    settings_obj.strategy_preset = name.lower()
