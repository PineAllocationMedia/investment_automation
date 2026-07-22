import copy
import unittest

from src.allocation_engine import allocate_capital
from src.allocation_mode_contract_engine import build_allocation_mode_contract_audit
from tests.helpers import full_strong_analysis


def _contract_candidate(
    ticker: str,
    score: float,
    *,
    durability: str = "VERY_DURABLE_COMPOUNDER",
    universe: str = "CORE_PORTFOLIO",
) -> dict:
    row = full_strong_analysis(ticker)
    row.update(
        {
            "score_total": 9.0,
            "conviction_score": 92,
            "capital_allocation_score": score,
            "business_quality_score": 92,
            "expected_cagr_quality": "VERY_HIGH",
            "opportunity_cost_status": "CLEARLY_BETTER_THAN_VFV",
            "thesis_status": "INTACT",
            "liquidation_status": "GREEN",
            "add_eligibility_status": "ADD_ALLOWED",
            "data_reliability_level": "HIGH",
            "data_quality": "HIGH",
            "current_value": 0,
            "position_weight": 0,
            "long_term_durability_status": durability,
            "cycle_bubble_risk_level": "LOW",
            "quality_but_too_expensive": False,
            "universe": universe,
            "watchlist_status": "HIGH_PRIORITY_WATCH",
            "external_superiority": "COMPARABLE_TO_CORE_LEADERS",
        }
    )
    if universe != "CORE_PORTFOLIO":
        row["research_report_fields"] = ["moat_clear"]
        row["external_validation_status"] = "VALIDATED_DATA_PRESENT"
    if durability == "HIGH_GROWTH_BUT_FRAGILE":
        row["conviction_score"] = 88
    return row


def _contract_universe() -> dict:
    return {
        "MSFT": _contract_candidate("MSFT", 96),
        "COST": _contract_candidate("COST", 86),
        "LLY": _contract_candidate("LLY", 80),
        "APP": _contract_candidate(
            "APP",
            94,
            durability="HIGH_GROWTH_BUT_FRAGILE",
            universe="WATCHLIST",
        ),
        "VFV.TO": {
            "ticker": "VFV.TO",
            "score_total": 0,
            "benchmark_role": "BENCHMARK",
            "asset_type": "ETF_BENCHMARK",
            "universe": "CORE_PORTFOLIO",
        },
    }


def _defensive_candidates_by_mode() -> dict:
    return {
        "balanced": [_defensive_candidate("balanced", 0.45)],
        "family-office": [_defensive_candidate("family-office", 0.25)],
        "rational-aggressive": [_defensive_candidate("rational-aggressive", 0.05)],
        "high-cagr": [],
    }


def _defensive_candidate(mode: str, cap: float) -> dict:
    return {
        "ticker": "CBIL.TO",
        "mode": mode,
        "enabled_for_mode": True,
        "selected_for_allocation": True,
        "status": "ELIGIBLE_DEFENSIVE_FALLBACK",
        "defensive_score": 75,
        "max_single_allocation_pct": cap,
        "reason": "Test ETF défensif.",
    }


def _mode_row(rows: list[dict], mode: str) -> dict:
    return next(row for row in rows if row.get("row_type") == "MODE_SUMMARY" and row.get("mode") == mode)


def _check_row(rows: list[dict], row_type: str) -> dict:
    return next(row for row in rows if row.get("row_type") == row_type)


class AllocationModeContractAuditTest(unittest.TestCase):
    def test_high_cagr_allows_more_offensive_concentration_than_balanced(self):
        rows = build_allocation_mode_contract_audit(
            1000,
            _contract_universe(),
            defensive_etf_candidates_by_mode=_defensive_candidates_by_mode(),
        )

        balanced = _mode_row(rows, "balanced")
        high = _mode_row(rows, "high-cagr")

        self.assertGreater(
            high["max_single_allocation_pct"],
            balanced["max_single_allocation_pct"],
        )
        self.assertEqual(_check_row(rows, "CONCENTRATION_ORDER")["status"], "PASS")

    def test_balanced_does_not_look_like_high_cagr(self):
        rows = build_allocation_mode_contract_audit(
            1000,
            _contract_universe(),
            defensive_etf_candidates_by_mode=_defensive_candidates_by_mode(),
        )

        balanced = _mode_row(rows, "balanced")
        high = _mode_row(rows, "high-cagr")

        self.assertGreater(balanced["defensive_reserve_pct"], high["defensive_reserve_pct"])
        self.assertGreater(balanced["defensiveness_score"], high["defensiveness_score"])
        self.assertEqual(_check_row(rows, "DEFENSIVENESS_ORDER")["status"], "PASS")

    def test_high_cagr_keeps_vfv_safety_net(self):
        rows = build_allocation_mode_contract_audit(
            1000,
            _contract_universe(),
            defensive_etf_candidates_by_mode=_defensive_candidates_by_mode(),
        )
        high = _mode_row(rows, "high-cagr")

        self.assertGreaterEqual(high["fallback_allocation_pct"], 0.05)
        self.assertEqual(_check_row(rows, "HIGH_CAGR_SAFETY_NET")["status"], "PASS")

    def test_emerging_satellites_stay_capped(self):
        rows = build_allocation_mode_contract_audit(
            1000,
            _contract_universe(),
            defensive_etf_candidates_by_mode=_defensive_candidates_by_mode(),
        )
        high = _mode_row(rows, "high-cagr")

        self.assertLessEqual(high["emerging_fragile_allocation_pct"], 0.2255)
        self.assertEqual(_check_row(rows, "EMERGING_SATELLITE_CAP")["status"], "PASS")

    def test_audit_does_not_modify_active_allocation_or_input(self):
        analyses = _contract_universe()
        before_analyses = copy.deepcopy(analyses)
        active_before = allocate_capital(
            1000,
            copy.deepcopy(analyses),
            "high-cagr",
            defensive_etf_candidates=[],
        )["allocations"]

        build_allocation_mode_contract_audit(
            1000,
            analyses,
            defensive_etf_candidates_by_mode=_defensive_candidates_by_mode(),
        )

        active_after = allocate_capital(
            1000,
            copy.deepcopy(analyses),
            "high-cagr",
            defensive_etf_candidates=[],
        )["allocations"]
        self.assertEqual(analyses, before_analyses)
        self.assertEqual(active_before, active_after)


if __name__ == "__main__":
    unittest.main()
