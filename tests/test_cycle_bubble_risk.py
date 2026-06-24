import unittest

from src.cycle_bubble_risk_engine import compute_cycle_bubble_risk
from tests.helpers import full_strong_analysis


class CycleBubbleRiskTest(unittest.TestCase):
    def test_hot_semiconductor_cycle_is_flagged_high(self):
        analysis = full_strong_analysis("LRCX")
        analysis["benchmark_ticker"] = "SOXX"
        analysis["factor_exposure"] = ["semiconductors", "AI", "technology"]
        analysis["stock_return_1y"] = 0.55
        analysis["benchmark_return_1y"] = 0.38
        analysis["drawdown_from_12m_high"] = -0.02
        analysis["benchmark_relevance_level"] = "HIGH"

        result = compute_cycle_bubble_risk(analysis, {"tech_ai_semi_weight": 0.45, "concentration_by_sector": {}})

        self.assertIn(result["cycle_bubble_risk_level"], {"HIGH", "EXTREME"})
        self.assertLess(result["cycle_bubble_allocation_multiplier"], 1.0)
        self.assertGreater(result["cycle_bubble_penalty"], 0)

    def test_quality_business_without_heat_stays_low_or_medium(self):
        analysis = full_strong_analysis("MSFT")
        analysis["factor_exposure"] = ["software"]
        analysis["stock_return_1y"] = 0.08
        analysis["benchmark_return_1y"] = 0.07
        analysis["drawdown_from_12m_high"] = -0.22
        analysis["benchmark_relevance_level"] = "MEDIUM"

        result = compute_cycle_bubble_risk(analysis, {"tech_ai_semi_weight": 0.20, "concentration_by_sector": {}})

        self.assertIn(result["cycle_bubble_risk_level"], {"LOW", "MEDIUM"})

    def test_possible_peak_earnings_adds_full_cycle_warning(self):
        analysis = full_strong_analysis("WDC")
        analysis["sector"] = "Technology"
        analysis["factor_exposure"] = ["technology", "hardware"]
        analysis["stock_return_1y"] = 0.55
        analysis["drawdown_from_12m_high"] = -0.02
        analysis["forward_pe"] = 26
        analysis["trailing_pe"] = 28
        analysis["profit_margins"] = 0.55
        analysis["revenue_growth"] = 0.45
        analysis["earnings_growth"] = 4.8
        analysis["eps_growth_estimated_3_5y"] = 24

        result = compute_cycle_bubble_risk(analysis, {"tech_ai_semi_weight": 0.20, "concentration_by_sector": {}})

        self.assertEqual(result["cycle_normalized_status"], "POSSIBLE_PEAK_EARNINGS")
        self.assertGreater(result["cycle_normalized_earnings_risk_score"], 20)
        self.assertIn(result["cycle_bubble_risk_level"], {"HIGH", "EXTREME"})


if __name__ == "__main__":
    unittest.main()
