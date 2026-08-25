from backend.market_data.engine import MarketSnapshot, OrderBookLevel
from backend.strategy.fair_value import fair_value, microprice, order_book_imbalance
from backend.strategy.market_maker import compute_quotes
from backend.profitability.engine import ProfitabilityInput, check, estimate
from backend.risk.engine import check_all


def test_mid_micro_imbalance():
    snap = MarketSnapshot(market="BTC-PERP", market_id=1, bid=100, ask=102, mid=101, spread=2, stale=False, bids=[OrderBookLevel(100,10)], asks=[OrderBookLevel(102,5)])
    assert microprice(snap) == (102*10 + 100*5)/15
    assert order_book_imbalance(snap) > 0
    fv = fair_value(snap)
    assert fv.fair_value is not None


def test_quotes_inventory_skew():
    snap = MarketSnapshot(market="BTC-PERP", market_id=1, bid=100, ask=102, mid=101, spread=2, stale=False)
    q1 = compute_quotes(snap, base_inventory=0)
    q2 = compute_quotes(snap, base_inventory=0.04)
    assert q1 and q2
    # long inventory widens bid distance
    assert q2.bid_price <= q1.bid_price  # type: ignore


def test_profitability_filter():
    inp = ProfitabilityInput(fair_value=100, bid_price=99, ask_price=101, bid_size=0.01, ask_size=0.01, spread_bps=20, fill_prob=0.3)
    res = estimate(inp)
    assert res.net_profit != 0
    assert check(inp) in ("PROFITABLE","UNPROFITABLE","RISK_BLOCKED","INSUFFICIENT_DATA")


def test_risk_blocks_stale():
    snap = MarketSnapshot(market="BTC-PERP", market_id=1, stale=True)
    rc = check_all(snap, 0.01, "buy", 0, 0, 0, 0)
    assert not rc.passed
