from __future__ import annotations

import unittest

from src.allocation_engine import allocate_capital
from src.allocation_sensitivity_engine import compute_allocation_sensitivity
from tests.helpers import full_strong_analysis


def candidate(ticker: str, score: float, evidence: str = "CONFIRMED") -> dict:
    row = full_strong_analysis(ticker)
    row.update(
        {
            "ticker": ticker,
            "universe": "CORE_PORTFOLIO",
            "capital_allocation_score": score,
            "conviction_score": 90,
            "score_evidence_level": evidence,
            "data_reliability_level": "HIGH" if evidence == "CONFIRMED" else "MEDIUM",
            "auto_estimate_dependency": "LOW" if evidence == "CONFIRMED" else "HIGH",
            "long_term_durability_status": "VERY_DURABLE_COMPOUNDER",
            "cycle_bubble_risk_level": "LOW",
            "monitoring_status": "NORMAL",
            "current_value": 0,
            "position_weight": 0,
        }
    )
    return row


class AllocationSensitivityTests(unittest.TestCase):
    def test_robust_allocation_keeps_simple_verdict(self):
        analyses = {
            "MSFT": candidate("MSFT", 92, "CONFIRMED"),
            "VFV.TO": {"ticker": "VFV.TO", "benchmark_role": True, "score_total": 8.0},
        }
        base = allocate_capital(500, analyses, "high-cagr")

        sensitivity = compute_allocation_sensitivity(500, "high-cagr", analyses, base)

        self.assertIn(sensitivity["summary"]["robustness_status"], {"ROBUST", "MODERATELY_SENSITIVE"})
        self.assertTrue(sensitivity["rows"])
        self.assertEqual(sensitivity["summary"]["base_top_pick"], "MSFT")

    def test_estimate_heavy_winner_is_reduced_under_strict_data(self):
        analyses = {
            "AAPL": candidate("AAPL", 88, "ESTIMATE_HEAVY"),
            "MSFT": candidate("MSFT", 75, "CONFIRMED"),
            "VFV.TO": {"ticker": "VFV.TO", "benchmark_role": True, "score_total": 8.0},
        }
        analyses["AAPL"]["data_reliability_level"] = "HIGH"
        base = allocate_capital(500, analyses, "high-cagr")

        sensitivity = compute_allocation_sensitivity(500, "high-cagr", analyses, base)
        aapl_row = next(row for row in sensitivity["rows"] if row["ticker"] == "AAPL")

        self.assertLessEqual(aapl_row["strict_data_amount"], aapl_row["base_amount"])
        self.assertGreaterEqual(aapl_row["max_change_percent"], 0)


if __name__ == "__main__":
    unittest.main()
