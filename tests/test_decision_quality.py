import unittest

from src.decision_quality_engine import (
    annotate_allocations_with_decision_quality,
    compute_decision_quality,
    decision_quality_rows_for_csv,
)
from tests.helpers import full_strong_analysis


class DecisionQualityTest(unittest.TestCase):
    def test_high_quality_decision_when_core_allocations_are_robust(self):
        msft = full_strong_analysis("MSFT")
        msft.update(
            {
                "capital_allocation_score": 90,
                "add_eligibility_status": "ADD_ALLOWED",
                "data_reliability_level": "HIGH",
                "auto_estimate_dependency": "LOW",
                "ticker_validation_status": "OK",
                "ticker_coverage_status": "OK",
                "cycle_bubble_risk_level": "LOW",
                "allocation_stability_status": "SUPPORT_CONTINUITY",
            }
        )
        result = compute_decision_quality(
            {"MSFT": msft, "VFV.TO": {"ticker": "VFV.TO"}},
            {
                "mandatory_vfv_percent": 0.10,
                "allocations": [
                    {"destination": "VFV.TO", "montant": 100},
                    {"destination": "MSFT", "montant": 900},
                ],
            },
            {"alerts": []},
            [],
        )

        self.assertEqual(result["decision_quality_level"], "HIGH")
        self.assertGreaterEqual(result["decision_quality_score"], 82)
        self.assertEqual(result["allocated_core_count"], 1)

    def test_large_vfv_redirection_reduces_decision_quality(self):
        result = compute_decision_quality(
            {"VFV.TO": {"ticker": "VFV.TO"}},
            {
                "mandatory_vfv_percent": 0.10,
                "allocations": [{"destination": "VFV.TO", "montant": 1000}],
            },
            {"alerts": []},
            [],
        )

        self.assertIn(result["decision_quality_level"], {"LOW", "MANUAL_REVIEW_REQUIRED"})
        self.assertGreaterEqual(result["vfv_redirection_percent"], 0.8)
        self.assertTrue(result["why_not_high"])

    def test_wrong_ticker_allocation_requires_manual_review(self):
        cco = full_strong_analysis("CCO")
        cco.update(
            {
                "capital_allocation_score": 90,
                "add_eligibility_status": "ADD_ALLOWED",
                "data_reliability_level": "HIGH",
                "ticker_validation_status": "POSSIBLE_WRONG_TICKER",
                "ticker_coverage_status": "POSSIBLE_WRONG_TICKER",
            }
        )

        result = compute_decision_quality(
            {"CCO": cco},
            {"mandatory_vfv_percent": 0.0, "allocations": [{"destination": "CCO", "montant": 500}]},
            {"alerts": []},
            [],
        )

        self.assertEqual(result["decision_quality_level"], "MANUAL_REVIEW_REQUIRED")

    def test_decision_quality_can_be_written_to_allocations_and_csv_row(self):
        allocation_result = {
            "decision_quality": {
                "decision_quality_level": "MEDIUM",
                "decision_quality_score": 70,
                "summary": "Utilisable avec surveillance.",
            },
            "allocations": [{"destination": "MSFT", "montant": 500}],
        }

        annotate_allocations_with_decision_quality(allocation_result)
        rows = decision_quality_rows_for_csv(allocation_result["decision_quality"])

        self.assertEqual(allocation_result["allocations"][0]["decision_quality"], "MEDIUM")
        self.assertEqual(rows[0]["decision_quality_level"], "MEDIUM")

    def test_high_cagr_profile_accepts_quality_risk_more_than_standard_profile(self):
        googl = full_strong_analysis("GOOGL")
        googl.update(
            {
                "capital_allocation_score": 78,
                "add_eligibility_status": "ADD_ALLOWED",
                "data_reliability_level": "HIGH",
                "auto_estimate_dependency": "LOW",
                "ticker_validation_status": "OK",
                "ticker_coverage_status": "OK",
                "cycle_bubble_risk_level": "HIGH",
                "monitoring_status": "WATCH",
                "allocation_stability_status": "ALLOW_NEW_LEADER",
            }
        )
        allocation_result = {
            "mandatory_vfv_percent": 0.10,
            "allocations": [
                {"destination": "VFV.TO", "montant": 400},
                {"destination": "GOOGL", "montant": 600},
            ],
        }
        portfolio_risk = {
            "alerts": [
                {"alert": "forte exposition USD"},
                {"alert": "portefeuille très concentré"},
            ]
        }

        standard = compute_decision_quality({"GOOGL": googl}, allocation_result, portfolio_risk, [], mode="family-office")
        high_cagr = compute_decision_quality({"GOOGL": googl}, allocation_result, portfolio_risk, [], mode="high-cagr")

        self.assertGreater(high_cagr["decision_quality_score"], standard["decision_quality_score"])
        self.assertEqual(high_cagr["profile_calibration"], "HIGH_CAGR_LONG_TERM")
        self.assertNotEqual(high_cagr["decision_quality_level"], "HIGH")
        self.assertIn("Il manque", high_cagr["why_not_high"][0])


if __name__ == "__main__":
    unittest.main()
