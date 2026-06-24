import unittest

from src.market_growth_thesis_engine import compute_market_growth_thesis, market_growth_thesis_rows_for_csv
from src.sizing_engine import compute_capital_allocation_score
from tests.helpers import full_strong_analysis


class MarketGrowthThesisTest(unittest.TestCase):
    def test_structural_tailwind_gets_small_positive_adjustment(self):
        analysis = full_strong_analysis("MSFT")
        analysis.update(
            {
                "sector": "Cloud Computing",
                "factor_exposure": ["AI", "cloud", "software"],
                "revenue_growth": 0.14,
                "cycle_bubble_risk_level": "LOW",
                "data_reliability_score": 88,
                "data_reliability_level": "HIGH",
                "official_confirmed_fields": ["revenue_growth"],
            }
        )

        result = compute_market_growth_thesis(analysis)

        self.assertEqual(result["market_growth_thesis_status"], "STRUCTURAL_TAILWIND")
        self.assertGreaterEqual(result["market_growth_thesis_score"], 75)
        self.assertGreater(result["market_growth_thesis_adjustment"], 0)
        self.assertLessEqual(result["market_growth_thesis_adjustment"], 3)

    def test_hot_market_is_not_allowed_to_become_unbounded_bonus(self):
        analysis = full_strong_analysis("NVDA")
        analysis.update(
            {
                "sector": "Semiconductors",
                "factor_exposure": ["AI", "semiconductors", "infrastructure"],
                "revenue_growth": 0.45,
                "cycle_bubble_risk_level": "EXTREME",
                "quality_but_too_expensive": True,
                "data_reliability_score": 90,
                "data_reliability_level": "HIGH",
            }
        )

        result = compute_market_growth_thesis(analysis)

        self.assertIn(result["market_growth_thesis_status"], {"HYPE_RISK", "ATTRACTIVE_BUT_CYCLICAL"})
        self.assertLessEqual(result["market_growth_thesis_adjustment"], 0)

    def test_mature_low_growth_market_is_penalized_moderately(self):
        analysis = full_strong_analysis("MATURE")
        analysis.update(
            {
                "sector": "Traditional Financials",
                "business_profile": "BANK",
                "factor_exposure": ["financials", "credit"],
                "sector_cagr_estimated": 2,
                "benchmark_10y_cagr": 0.025,
                "benchmark_5y_cagr": 0.02,
                "revenue_growth": 0.01,
                "cycle_bubble_risk_level": "MEDIUM",
                "data_reliability_score": 72,
            }
        )

        result = compute_market_growth_thesis(analysis)

        self.assertEqual(result["market_growth_thesis_status"], "MATURE_OR_LOW_GROWTH")
        self.assertLessEqual(result["market_growth_thesis_adjustment"], 0)

    def test_infrastructure_alone_does_not_trigger_semiconductor_theme(self):
        analysis = full_strong_analysis("WSP.TO")
        analysis.update(
            {
                "sector": "Engineering & Construction",
                "factor_exposure": ["engineering", "infrastructure", "industrial"],
                "benchmark_ticker": "XLI",
            }
        )

        result = compute_market_growth_thesis(analysis)

        self.assertIn("ELECTRIFICATION_AUTOMATION", result["market_growth_thesis_themes"])
        self.assertNotIn("SEMICONDUCTORS", result["market_growth_thesis_themes"])

    def test_data_infrastructure_alone_does_not_trigger_electrification_theme(self):
        analysis = full_strong_analysis("AVGO")
        analysis.update(
            {
                "sector": "Semiconductors",
                "factor_exposure": ["semiconductors", "AI", "infrastructure"],
                "benchmark_ticker": "SOXX",
            }
        )

        result = compute_market_growth_thesis(analysis)

        self.assertIn("SEMICONDUCTORS", result["market_growth_thesis_themes"])
        self.assertNotIn("ELECTRIFICATION_AUTOMATION", result["market_growth_thesis_themes"])

    def test_sizing_uses_market_growth_adjustment_without_dominating_score(self):
        analysis = full_strong_analysis("MSFT")
        base = compute_capital_allocation_score(analysis, {"concentration_by_sector": {}, "top3_weight": 0})
        analysis.update(compute_market_growth_thesis({**analysis, "factor_exposure": ["AI", "cloud"], "revenue_growth": 0.15}))
        improved = compute_capital_allocation_score(analysis, {"concentration_by_sector": {}, "top3_weight": 0})

        self.assertGreater(improved["capital_allocation_score"], base["capital_allocation_score"])
        self.assertLessEqual(
            improved["capital_allocation_score"] - base["capital_allocation_score"],
            6,
        )

    def test_rows_include_multiple_universes(self):
        core = {"MSFT": {"ticker": "MSFT", **compute_market_growth_thesis(full_strong_analysis("MSFT"))}}
        market = {"GOOGL": {"ticker": "GOOGL", **compute_market_growth_thesis(full_strong_analysis("GOOGL"))}}

        rows = market_growth_thesis_rows_for_csv(core, market_analyses=market)

        universes = {row["universe"] for row in rows}
        self.assertIn("CORE_PORTFOLIO", universes)
        self.assertIn("MARKET_UNIVERSE", universes)


if __name__ == "__main__":
    unittest.main()
