import unittest

from tests.helpers import full_strong_analysis, strong_benchmark, strong_market
from src.proof_score_engine import compute_proof_score


class ProofScoreTest(unittest.TestCase):
    def test_manual_confirmed_score_has_small_gap(self):
        analysis = full_strong_analysis("MSFT")
        manual = {
            **analysis,
            "manual_override_fields": [
                "roic_5y_avg",
                "net_margin_stable_or_expanding",
                "eps_growth_5y",
                "moat_clear",
                "eps_growth_estimated_3_5y",
                "sector_cagr_estimated",
                "fair_value",
                "valuation_vs_5y_avg_ok",
            ],
            "auto_estimated_fields": [],
        }
        result = compute_proof_score(
            manual,
            strong_market(),
            strong_benchmark(),
            analysis,
            {"data_reliability_level": "HIGH", "auto_estimate_dependency": "LOW", "automation_evidence_level": "CONFIRMED"},
        )

        self.assertGreaterEqual(result["score_confirmed_only"], 8)
        self.assertEqual(result["score_evidence_level"], "CONFIRMED")
        self.assertEqual(result["score_evidence_penalty"], 0)

    def test_estimate_heavy_score_is_flagged_without_blocking_analysis(self):
        analysis = full_strong_analysis("MSFT")
        auto_fields = [
            "roic_5y_avg",
            "net_margin_stable_or_expanding",
            "eps_growth_5y",
            "moat_clear",
            "eps_growth_estimated_3_5y",
            "sector_cagr_estimated",
            "fair_value",
            "valuation_vs_5y_avg_ok",
        ]
        manual = {**analysis, "input_data_mode": "AUTO_ESTIMATED", "auto_estimated_fields": auto_fields, "manual_override_fields": []}
        result = compute_proof_score(
            manual,
            strong_market(),
            strong_benchmark(),
            analysis,
            {"data_reliability_level": "MEDIUM", "auto_estimate_dependency": "HIGH", "automation_evidence_level": "WEAK"},
        )

        self.assertLess(result["score_confirmed_only"], result["score_with_estimates"])
        self.assertIn(result["score_evidence_level"], {"ESTIMATE_HEAVY", "INSUFFICIENT_CONFIRMED"})
        self.assertGreater(result["score_evidence_penalty"], 0)

    def test_strong_automation_gets_separate_label_not_manual_block(self):
        analysis = full_strong_analysis("MSFT")
        manual = {
            **analysis,
            "input_data_mode": "AUTO_ESTIMATED",
            "auto_estimated_fields": ["roic_5y_avg", "moat_clear", "fair_value"],
            "manual_override_fields": [],
        }
        result = compute_proof_score(
            manual,
            strong_market(),
            strong_benchmark(),
            analysis,
            {"data_reliability_level": "HIGH", "auto_estimate_dependency": "MEDIUM", "automation_evidence_level": "STRONG"},
        )

        self.assertEqual(result["score_evidence_level"], "AUTOMATED_STRONG")
        self.assertLessEqual(result["score_evidence_penalty"], 1.5)

    def test_sec_supported_auto_fields_count_as_confirmed_evidence(self):
        analysis = full_strong_analysis("MSFT")
        auto_fields = [
            "roic_5y_avg",
            "net_margin_stable_or_expanding",
            "eps_growth_5y",
            "moat_clear",
            "eps_growth_estimated_3_5y",
            "sector_cagr_estimated",
            "fair_value",
            "valuation_vs_5y_avg_ok",
        ]
        manual = {
            **analysis,
            "input_data_mode": "AUTO_ESTIMATED",
            "auto_estimated_fields": auto_fields,
            "manual_override_fields": [],
            "official_supported_manual_fields": [
                "roic_5y_avg",
                "net_margin_stable_or_expanding",
                "eps_growth_5y",
                "eps_growth_estimated_3_5y",
            ],
        }

        without_sec = compute_proof_score(
            {**manual, "official_supported_manual_fields": []},
            strong_market(),
            strong_benchmark(),
            analysis,
            {"data_reliability_level": "HIGH", "auto_estimate_dependency": "MEDIUM", "automation_evidence_level": "STRONG"},
        )
        with_sec = compute_proof_score(
            manual,
            strong_market(),
            strong_benchmark(),
            analysis,
            {"data_reliability_level": "HIGH", "auto_estimate_dependency": "LOW", "automation_evidence_level": "STRONG"},
        )

        self.assertGreater(with_sec["score_confirmed_only"], without_sec["score_confirmed_only"])
        self.assertLess(with_sec["score_estimate_gap"], without_sec["score_estimate_gap"])


if __name__ == "__main__":
    unittest.main()
