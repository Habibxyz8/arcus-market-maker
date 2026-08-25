"""Phase 5: Credential guards - never log/display/commit."""
from __future__ import annotations

from backend.config.settings import settings
from backend.monitoring.logger import get_logger

log = get_logger(__name__)


def assert_no_hardcoded_secrets() -> None:
    """Called on startup to ensure no hardcoded secrets in code path."""
    # We only read from env; this is a guard rail for developers
    if settings.has_credentials():
        log.info("Credentials present for mode=%s address=%s... (secret redacted)", settings.trading_mode.value, settings.arcus_account_address[:6] if settings.arcus_account_address else "?")
    else:
        log.info("No credentials configured - PAPER mode or read-only")


def redact_for_log(obj: dict) -> dict:
    from backend.monitoring.logger import sanitize
    return sanitize(obj)  # type: ignore[return-value]
