from __future__ import annotations

from src.cagr_quality_engine import compute_expected_cagr_quality, compute_quality_but_too_expensive
from src.conviction_engine import compute_conviction_score
from src.liquidation_engine import compute_liquidation_status
from src.opportunity_cost_engine import compute_opportunity_cost_status
from src.scoring import compute_fundamental_score
from src.sizing_engine import compute_winner_accelerated
from src.thesis_engine import compute_thesis_status


def strong_manual() -> dict:
    return {
        "roic_5y_avg": 38,
        "net_margin_stable_or_expanding": True,
        "eps_growth_5y": 25,
        "moat_clear": True,
        "eps_growth_estimated_3_5y": 30,
        "sector_cagr_estimated": 20,
        "forward_pe_manual": 28,
        "peg_manual": 1.6,
        "fair_value": 100,
        "current_price_manual": 105,
        "valuation_vs_5y_avg_ok": True,
        "catastrophic_fraud": False,
        "catastrophic_moat_lost": False,
        "catastrophic_growth_broken": False,
        "catastrophic_roic_destroyed": False,
        "catastrophic_dangerous_debt": False,
        "catastrophic_obsolete_business": False,
        "catastrophic_destructive_management": False,
        "margin_or_profitability_under_pressure": False,
        "forward_pe_growth_acceptable": True,
        "management_quality_good": True,
        "balance_sheet_strong": True,
        "regulatory_risk_high": False,
        "geopolitical_risk_high": False,
        "single_product_dependency_high": False,
        "manual_confidence_level": "HIGH",
        "notes": "",
    }


def strong_market() -> dict:
    return {
        "current_price": 105,
        "forward_pe": 28,
        "peg": 1.6,
        "sma_200": 95,
        "price_above_sma_200": True,
        "stock_return_1y": 0.22,
        "drawdown_from_12m_high": -0.18,
        "drawdown_from_8m_high": -0.12,
        "dividend_yield": 0.0,
    }


def strong_benchmark() -> dict:
    return {
        "benchmark_ticker": "IGV",
        "benchmark_10y_cagr": 0.09,
        "benchmark_5y_cagr": 0.08,
        "benchmark_usable_cagr": 0.09,
        "benchmark_usable_period": "10 ans",
        "benchmark_usable_field": "cagr_10y",
        "benchmark_above_sma_200": True,
        "benchmark_return_1y": 0.10,
    }


def full_strong_analysis(ticker: str = "MSFT") -> dict:
    manual = strong_manual()
    market = strong_market()
    benchmark = strong_benchmark()
    score = compute_fundamental_score(ticker, manual, market, benchmark)
    thesis = compute_thesis_status(manual, score, market, benchmark)
    liquidation = compute_liquidation_status(manual, score, thesis["thesis_status"], market, benchmark)
    conviction = compute_conviction_score(manual, score, thesis["thesis_status"], market, benchmark)
    cagr = compute_expected_cagr_quality(manual, score, conviction["conviction_score"], thesis["thesis_status"])
    expensive = compute_quality_but_too_expensive(manual, score)
    opportunity = compute_opportunity_cost_status(
        manual,
        score,
        conviction["conviction_score"],
        cagr["expected_cagr_quality"],
        thesis["thesis_status"],
        liquidation["liquidation_status"],
        expensive["quality_but_too_expensive"],
    )
    analysis = {
        "ticker": ticker,
        **manual,
        **market,
        **benchmark,
        **score,
        **thesis,
        **liquidation,
        **conviction,
        **cagr,
        **expensive,
        **opportunity,
        "position_weight": 0.10,
        "sector": "Cloud Computing",
        "catastrophic_flags": [],
    }
    analysis.update(compute_winner_accelerated(analysis))
    return analysis
