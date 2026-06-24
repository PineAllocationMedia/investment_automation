import unittest

from src.double_counting_engine import compute_double_counting_context
from src.sizing_engine import compute_capital_allocation_score
from tests.helpers import full_strong_analysis


class DoubleCountingTest(unittest.TestCase):
    def test_hot_growth_theme_gets_moderate_dampener(self):
        analysis = full_strong_analysis("NVDA")
        analysis.update(
            {
                "score_total": 9.4,
                "conviction_score": 95,
                "expected_cagr_quality": "VERY_HIGH",
                "eps_growth_5y": 35,
                "eps_growth_estimated_3_5y": 22,
                "sector_cagr_estimated": 14,
                "high_cagr_potential_score": 94,
                "market_growth_thesis_score": 92,
                "sector": "Semiconductors",
                "factor_exposure": ["AI", "semiconductors", "data center", "technology"],
                "price_above_sma_200": True,
                "benchmark_above_sma_200": True,
                "stock_return_1y": 0.75,
                "benchmark_return_1y": 0.25,
                "cycle_bubble_risk_level": "HIGH",
                "business_quality_score": 74,
                "cash_flow_quality_score": 55,
                "long_term_durability_score": 65,
            }
        )

        result = compute_double_counting_context(analysis, mode="high-cagr")

        self.assertIn(result["double_counting_risk_level"], {"HIGH", "EXTREME"})
        self.assertLess(result["double_counting_adjustment"], 0)
        self.assertGreaterEqual(result["double_counting_adjustment"], -3.0)

    def test_confirmed_quality_reduces_not_removes_dampener(self):
        weak_quality = full_strong_analysis("NVDA")
        strong_quality = full_strong_analysis("NVDA")
        common = {
            "score_total": 9.4,
            "conviction_score": 95,
            "expected_cagr_quality": "VERY_HIGH",
            "eps_growth_5y": 35,
            "eps_growth_estimated_3_5y": 22,
            "sector_cagr_estimated": 14,
            "high_cagr_potential_score": 94,
            "market_growth_thesis_score": 92,
            "sector": "Semiconductors",
            "factor_exposure": ["AI", "semiconductors", "data center", "technology"],
            "price_above_sma_200": True,
            "benchmark_above_sma_200": True,
            "stock_return_1y": 0.75,
            "benchmark_return_1y": 0.25,
        }
        weak_quality.update({**common, "business_quality_score": 70, "cash_flow_quality_score": 50, "long_term_durability_score": 60})
        strong_quality.update(
            {
                **common,
                "business_quality_score": 95,
                "cash_flow_quality_score": 90,
                "long_term_durability_score": 90,
                "shareholder_discipline_score": 85,
                "price_to_fair_value": 1.05,
                "peg": 1.6,
            }
        )

        weak_result = compute_double_counting_context(weak_quality, mode="high-cagr")
        strong_result = compute_double_counting_context(strong_quality, mode="high-cagr")

        self.assertLess(strong_result["double_counting_adjustment"], 0)
        self.assertGreater(strong_result["double_counting_adjustment"], weak_result["double_counting_adjustment"])

    def test_sizing_applies_double_counting_adjustment_without_changing_fundamental_score(self):
        analysis = full_strong_analysis("MSFT")
        base = compute_capital_allocation_score(analysis, {"concentration_by_sector": {}, "top3_weight": 0})
        adjusted = compute_capital_allocation_score(
            {**analysis, "double_counting_adjustment": -2.25},
            {"concentration_by_sector": {}, "top3_weight": 0},
        )

        self.assertAlmostEqual(base["capital_allocation_score"] - adjusted["capital_allocation_score"], 2.25)
        self.assertEqual(analysis["score_total"], full_strong_analysis("MSFT")["score_total"])
        self.assertEqual(adjusted["capital_allocation_components"]["double_counting_adjustment"], -2.25)


if __name__ == "__main__":
    unittest.main()
