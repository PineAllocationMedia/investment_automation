import unittest

from src.long_term_durability_engine import compute_long_term_durability
from src.sizing_engine import compute_capital_allocation_score
from tests.helpers import full_strong_analysis


class LongTermDurabilityTest(unittest.TestCase):
    def test_strong_compounder_gets_very_durable_status(self):
        analysis = full_strong_analysis("MSFT")
        analysis["cycle_bubble_risk_level"] = "LOW"
        analysis["data_reliability_level"] = "HIGH"
        analysis["data_reliability_score"] = 92
        analysis["auto_estimate_dependency"] = "LOW"
        analysis["trend_status"] = "STABLE"

        result = compute_long_term_durability(analysis)

        self.assertEqual(result["long_term_durability_status"], "VERY_DURABLE_COMPOUNDER")
        self.assertGreaterEqual(result["long_term_durability_score"], 82)

    def test_hot_cycle_growth_name_is_classified_as_fragile(self):
        analysis = full_strong_analysis("NVDA")
        analysis["cycle_bubble_risk_level"] = "EXTREME"
        analysis["high_cagr_potential_score"] = 92
        analysis["quality_but_too_expensive"] = True
        analysis["data_reliability_level"] = "HIGH"
        analysis["data_reliability_score"] = 90

        result = compute_long_term_durability(analysis)

        self.assertEqual(result["long_term_durability_status"], "HIGH_GROWTH_BUT_FRAGILE")
        self.assertIn("Risque de cycle/tendance EXTREME", result["long_term_durability_reason"])

    def test_cyclical_quality_business_is_not_treated_like_pure_compounder(self):
        analysis = full_strong_analysis("BAM")
        analysis["business_profile"] = "ALT_ASSET_MANAGER"
        analysis["cycle_bubble_risk_level"] = "MEDIUM"
        analysis["high_cagr_potential_score"] = 60
        analysis["data_reliability_level"] = "HIGH"
        analysis["data_reliability_score"] = 88

        result = compute_long_term_durability(analysis)

        self.assertEqual(result["long_term_durability_status"], "DURABLE_BUT_CYCLICAL")

    def test_uncertain_low_data_name_is_speculative_or_unproven(self):
        analysis = full_strong_analysis("NANO.TO")
        analysis["thesis_status"] = "UNCERTAIN"
        analysis["data_reliability_level"] = "LOW"
        analysis["score_missing_data_count"] = 5

        result = compute_long_term_durability(analysis)

        self.assertEqual(result["long_term_durability_status"], "SPECULATIVE_OR_UNPROVEN")

    def test_capital_score_penalizes_fragile_durability(self):
        analysis = full_strong_analysis("MSFT")
        analysis["cycle_bubble_risk_level"] = "LOW"
        base = compute_capital_allocation_score(analysis, {"concentration_by_sector": {}, "top3_weight": 0})
        analysis["long_term_durability_score"] = 68
        analysis["long_term_durability_status"] = "HIGH_GROWTH_BUT_FRAGILE"

        penalized = compute_capital_allocation_score(analysis, {"concentration_by_sector": {}, "top3_weight": 0})

        self.assertLess(penalized["capital_allocation_score"], base["capital_allocation_score"])
        self.assertIn("fragilité 15-30 ans", str(penalized["capital_allocation_components"]["penalties"]))


if __name__ == "__main__":
    unittest.main()
