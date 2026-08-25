"""Phase 4: PAPER/TESTNET/LIVE guards."""
import pytest
from httpx import AsyncClient, ASGITransport

from backend.config.settings import TradingMode, Settings
from backend.main import app


@pytest.mark.asyncio
async def test_default_is_paper(monkeypatch) -> None:
    # Settings defaults to PAPER without env
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.trading_mode == TradingMode.PAPER
    assert s.is_paper
    assert not s.is_live


@pytest.mark.asyncio
async def test_health_exposes_mode() -> None:
    t = ASGITransport(app=app)
    async with AsyncClient(transport=t, base_url="http://test") as ac:
        r = await ac.get("/api/health")
        assert r.status_code == 200
        assert r.json()["trading_mode"] in ("PAPER", "TESTNET", "LIVE")


@pytest.mark.asyncio
async def test_config_mode_no_secrets() -> None:
    t = ASGITransport(app=app)
    async with AsyncClient(transport=t, base_url="http://test") as ac:
        r = await ac.get("/api/config/mode")
        assert r.status_code == 200
        j = r.json()
        assert "mode" in j
        assert "has_credentials" in j
        # never leak secret
        assert "arcus_api_secret" not in str(j).lower()
        assert "ARCUS_API_SECRET" not in str(j)


@pytest.mark.asyncio
async def test_live_requires_confirm(monkeypatch) -> None:
    # Simulate LIVE without actually changing global env - patch settings directly
    from backend.config import settings as st_mod

    orig = st_mod.settings.trading_mode
    try:
        st_mod.settings.trading_mode = TradingMode.LIVE  # type: ignore[assignment]
        t = ASGITransport(app=app)
        async with AsyncClient(transport=t, base_url="http://test") as ac:
            r = await ac.post("/api/bot/start", json={"confirm_live": False})
            assert r.status_code == 400
            assert "confirm_live" in r.json()["detail"].lower()
            r2 = await ac.post("/api/bot/start", json={"confirm_live": True})
            assert r2.status_code == 200
            # cleanup state
            await ac.post("/api/bot/stop", json={})
    finally:
        st_mod.settings.trading_mode = orig  # type: ignore[assignment]
        # ensure stopped
        t2 = ASGITransport(app=app)
        async with AsyncClient(transport=t2, base_url="http://test") as ac:
            await ac.post("/api/bot/stop")


@pytest.mark.asyncio
async def test_emergency_blocks_start() -> None:
    t = ASGITransport(app=app)
    async with AsyncClient(transport=t, base_url="http://test") as ac:
        await ac.post("/api/bot/emergency-stop")
        r = await ac.post("/api/bot/start", json={"confirm_live": True})
        assert r.status_code == 409
        await ac.post("/api/bot/reset-emergency")
        r2 = await ac.get("/api/bot/status")
        assert r2.json()["emergency"] is False
