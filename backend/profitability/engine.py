"""Phase 13-15: Profitability engine - expected P&L vs fees/funding/adverse selection."""
from __future__ import annotations

from dataclasses import dataclass

from backend.config.settings import settings


@dataclass
class ProfitabilityInput:
    fair_value: float
    bid_price: float
    ask_price: float
    bid_size: float
    ask_size: float
    spread_bps: float
    fill_prob: float = 0.3  # estimated maker fill probability
    expected_holding_sec: float = 60
    funding_rate: float = 0.0  # per hour
    volatility: float | None = None
    adverse_selection_bps: float = 1.0  # expected adverse move if filled


@dataclass
class ProfitabilityResult:
    gross_profit: float
    fees: float
    funding_cost: float
    inventory_cost: float
    adverse_selection_cost: float
    net_profit: float
    edge_bps: float
    fill_prob: float


def estimate(
    inp: ProfitabilityInput,
    inventory: float = 0.0,
) -> ProfitabilityResult:
    # gross = half spread captured per round trip (buy at bid, sell at ask)
    mid = inp.fair_value
    gross_per_unit = (inp.ask_price - inp.bid_price) / 2  # half spread
    # Expected gross accounts for fill prob on both sides ~ prob^2 for round trip, but we quote one side at a time
    gross = gross_per_unit * min(inp.bid_size, inp.ask_size) * inp.fill_prob
    # fees: maker fee bps on notional
    notional = (inp.bid_price * inp.bid_size + inp.ask_price * inp.ask_size) / 2
    fees = notional * (settings.maker_fee_bps / 10000) * inp.fill_prob
    # funding: inventory * fundingRate * holding time (hourly rate)
    funding_cost = abs(inventory) * mid * inp.funding_rate * (inp.expected_holding_sec / 3600)
    # inventory risk: vol * inventory
    inv_cost = 0.0
    if inp.volatility and inventory:
        inv_cost = abs(inventory) * mid * inp.volatility * 0.1 * (inp.expected_holding_sec / 3600)
    # adverse selection: expected price move against us after fill
    adv = (inp.adverse_selection_bps / 10000) * mid * min(inp.bid_size, inp.ask_size) * inp.fill_prob
    net = gross - fees - funding_cost - inv_cost - adv
    edge_bps = (net / notional * 10000) if notional else 0
    return ProfitabilityResult(
        gross_profit=gross,
        fees=fees,
        funding_cost=funding_cost,
        inventory_cost=inv_cost,
        adverse_selection_cost=adv,
        net_profit=net,
        edge_bps=edge_bps,
        fill_prob=inp.fill_prob,
    )


def check(inp: ProfitabilityInput, inventory: float = 0.0) -> str:
    """Phase 14: PROFITABLE/UNPROFITABLE/INSUFFICIENT_DATA/RISK_BLOCKED"""
    if inp.fair_value <= 0 or inp.bid_price <= 0 or inp.ask_price <= 0:
        return "INSUFFICIENT_DATA"
    if inp.spread_bps < 1:
        return "UNPROFITABLE"
    res = estimate(inp, inventory)
    if res.fill_prob < 0.05:
        return "UNPROFITABLE"
    if res.adverse_selection_cost > inp.fair_value * 0.001:
        # max adverse selection guard
        if res.adverse_selection_cost > 5:
            return "RISK_BLOCKED"
    if res.net_profit < settings.min_expected_profit:
        return "UNPROFITABLE"
    if res.edge_bps < settings.min_expected_edge_bps:
        return "UNPROFITABLE"
    return "PROFITABLE"
