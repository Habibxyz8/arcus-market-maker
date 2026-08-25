"""Phase 36: Structured logs, no secrets."""
from __future__ import annotations

import logging
import re
from typing import Any

_SENSITIVE = re.compile(r"(api[_-]?secret|api[_-]?key|signature|mnemonic|private[_-]?key)", re.I)

_formatter = logging.Formatter(
    fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)


def get_logger(name: str) -> logging.Logger:
    lg = logging.getLogger(name)
    if not lg.handlers:
        h = logging.StreamHandler()
        h.setFormatter(_formatter)
        lg.addHandler(h)
        lg.setLevel(logging.INFO)
        lg.propagate = False
    return lg


def sanitize(obj: Any) -> Any:
    """Redact secrets recursively."""
    if isinstance(obj, dict):
        return {k: ("***REDACTED***" if _SENSITIVE.search(k) else sanitize(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize(x) for x in obj]
    if isinstance(obj, str) and _SENSITIVE.search(obj):
        return "***REDACTED***"
    return obj


# Canonical event names per Phase 36
BOT_STARTED = "BOT_STARTED"
BOT_STOPPED = "BOT_STOPPED"
ORDER_PLACED = "ORDER_PLACED"
ORDER_MODIFIED = "ORDER_MODIFIED"
ORDER_CANCELLED = "ORDER_CANCELLED"
ORDER_FILLED = "ORDER_FILLED"
PARTIAL_FILL = "PARTIAL_FILL"
RISK_BLOCKED_ORDER = "RISK_BLOCKED_ORDER"
PROFITABILITY_BLOCKED_ORDER = "PROFITABILITY_BLOCKED_ORDER"
MARKET_DATA_STALE = "MARKET_DATA_STALE"
RATE_LIMIT_WARNING = "RATE_LIMIT_WARNING"
EMERGENCY_STOP = "EMERGENCY_STOP"
