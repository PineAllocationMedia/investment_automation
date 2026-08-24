import unittest

from tests.helpers import full_strong_analysis
from src.add_eligibility_engine import compute_add_eligibility_status
from src.allocation_engine import allocate_capital
from src.quality_drawdown_engine import compute_quality_drawdown_opportunity
from src.sizing_engine import compute_capital_allocation_score


class QualityDrawdownTest(unittest.TestCase):
    def test_strong_business_drawdown_becomes_opportunity_not_falling_knife(self):
        analysis = full_strong_analysis("INTU")
        analysis.update(
            {
                "drawdown_from_12m_high": -0.28,
                "drawdown_from_8m_high": -0.22,
                "price_above_sma_200": False,
                "stock_return_1y": -0.12,
                "benchmark_return_1y": 0.08,
                "long_term_durability_score": 88,
                "cash_flow_quality_score": 92,
                "data_reliability_score": 86,
                "news_context_headlines": ["Intuit shares fall after earnings despite resilient cash flow"],
                "news_context_sources": ["Yahoo Finance"],
            }
        )

        result = compute_quality_drawdown_opportunity(analysis)

        self.assertEqual(result["quality_drawdown_status"], "QUALITY_DRAWDOWN_OPPORTUNITY")
        self.assertGreater(result["quality_drawdown_allocation_adjustment"], 0)
        self.assertEqual(result["news_context_status"], "TEMPORARY_MARKET_REACTION")

    def test_fundamental_news_blocks_drawdown_opportunity(self):
        analysis = full_strong_analysis("TEST")
        analysis.update(
            {
                "drawdown_from_12m_high": -0.35,
                "price_above_sma_200": False,
                "long_term_durability_score": 90,
                "cash_flow_quality_score": 90,
                "data_reliability_score": 90,
                "news_context_headlines": ["Company cuts guidance as margin pressure and weak demand worsen"],
                "news_context_sources": ["Reuters"],
            }
        )

        result = compute_quality_drawdown_opportunity(analysis)

        self.assertEqual(result["quality_drawdown_status"], "PRICE_WEAKNESS_WITH_FUNDAMENTAL_RISK")
        self.assertLess(result["quality_drawdown_allocation_adjustment"], 0)

    def test_quality_drawdown_can_allow_limited_add_despite_watch(self):
        analysis = full_strong_analysis("INTU")
        analysis["expected_cagr_quality"] = "MEDIUM"
        analysis["monitoring_status"] = "WATCH"
        analysis["technical_or_valuation_signals"] = ["Alerte technique: prix sous SMA 200."]
        analysis["quality_drawdown_status"] = "QUALITY_DRAWDOWN_OPPORTUNITY"
        analysis["quality_drawdown_score"] = 84
        analysis["conviction_score"] = 86

        result = compute_add_eligibility_status(analysis)

        self.assertEqual(result["add_eligibility_status"], "ADD_ALLOWED_SMALL")

    def test_high_cagr_allocation_can_include_quality_drawdown_medium_cagr_limited(self):
        analysis = full_strong_analysis("INTU")
        analysis.update(
            {
                "expected_cagr_quality": "MEDIUM",
                "opportunity_cost_status": "SIMILAR_TO_VFV",
                "monitoring_status": "WATCH",
                "add_eligibility_status": "ADD_ALLOWED_SMALL",
                "quality_drawdown_status": "QUALITY_DRAWDOWN_OPPORTUNITY",
                "quality_drawdown_score": 84,
                "quality_drawdown_allocation_adjustment": 5,
                "conviction_score": 86,
                "business_quality_score": 88,
                "long_term_durability_score": 88,
                "data_reliability_level": "HIGH",
                "capital_allocation_score": 74,
                "current_value": 50,
                "position_weight": 0.05,
            }
        )

        result = allocate_capital(500, {"INTU": analysis}, "high-cagr")
        intu_total = sum(row["montant"] for row in result["allocations"] if row["destination"] == "INTU")

        self.assertGreater(intu_total, 0)
        self.assertLessEqual(intu_total, 250)

    def test_sizing_uses_quality_drawdown_adjustment(self):
        analysis = full_strong_analysis("INTU")
        base = compute_capital_allocation_score(analysis, {"concentration_by_sector": {}, "top3_weight": 0})
        analysis["quality_drawdown_allocation_adjustment"] = 5
        analysis["quality_drawdown_allocation_exception_passed"] = True
        improved = compute_capital_allocation_score(analysis, {"concentration_by_sector": {}, "top3_weight": 0})

        self.assertGreater(improved["capital_allocation_score"], base["capital_allocation_score"])


if __name__ == "__main__":
    unittest.main()
