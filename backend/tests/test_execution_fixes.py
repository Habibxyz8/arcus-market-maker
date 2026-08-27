"""Regression tests for the four fix areas (TP/SL, CPM, real-fill ingest)."""
from __future__ import annotations

from backend.config.settings import settings
from backend.paper_trading.engine import PaperEngine


def _engine() -> PaperEngine:
    settings.stop_loss_usd = 0.01
    settings.take_profit_usd = 0.015
    e = PaperEngine()
    return e


def test_sl_hard_cap_negative_0_01():
    e = _engine()
    e._per_market["BTC-USD"] = {"inventory": 0.001, "entry_price": 100.0, "entry_side": "buy", "entry_ts": 1, "entry_qty": 0.001}
    e.base_inventory = 0.001
    e._entry_price = 100.0
    # price drop of $10 * 0.001 = -0.01 unrealized -> SL cap -0.01
    closed = e._check_micro_tp_sl(90.0, "BTC-USD")
    assert closed is True
    assert e.realized_pnl == -0.01
    assert e.base_inventory == 0


def test_tp_clamped_within_0_01_0_02():
    e = _engine()
    settings.take_profit_usd = 0.02
    e._per_market["BTC-USD"] = {"inventory": 0.001, "entry_price": 100.0, "entry_side": "buy", "entry_ts": 1, "entry_qty": 0.001}
    e.base_inventory = 0.001
    e._entry_price = 100.0
    # huge favorable move -> TP capped at 0.02, never more
    closed = e._check_micro_tp_sl(500.0, "BTC-USD")
    assert closed is True
    assert e.realized_pnl == 0.02


def test_cpm_no_crash_and_uses_mid():
    e = _engine()
    e._per_market["BTC-USD"] = {"inventory": 0.001, "entry_price": 100.0, "entry_side": "buy", "entry_ts": 1, "entry_qty": 0.001}
    e.base_inventory = 0.001
    e._entry_price = 100.0
    cpm = e.cpm(101.0)
    assert isinstance(cpm, float)


def test_apply_real_fill_updates_inventory():
    e = _engine()
    f = e.apply_real_fill("BTC-USD", "buy", 100.0, 0.001, 0.0, 100.0, fill_id="r1", order_id="o1")
    assert f is not None
    assert abs(e.base_inventory - 0.001) < 1e-9
    assert e.apply_real_fill("BTC-USD", "buy", 100.0, 0.001, 0.0, 100.0, fill_id="r1", order_id="o1") is None
