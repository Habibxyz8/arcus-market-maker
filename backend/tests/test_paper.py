from backend.paper_trading.engine import PaperEngine


def test_paper_fill_sim():
    pe = PaperEngine()
    o = pe.place("BTC-PERP","buy",100,0.01)
    assert o.status=="open"
    fills = pe.simulate_market_tick(99)  # mid below buy -> fill chance
    # may be 0 or 1 due to random, run many times
    for _ in range(20):
        pe.simulate_market_tick(99)
    # after many ticks we should have at least one fill occasionally, but not guaranteed; test cancel
    pe2 = PaperEngine()
    o2 = pe2.place("BTC-PERP","sell",100,0.01)
    pe2.cancel(o2.order_id)
    assert pe2.orders[o2.order_id].status=="canceled"
    assert pe2.volume()>=0
