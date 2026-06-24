import unittest

from src.hidden_cluster_engine import (
    apply_hidden_cluster_guardrails,
    compute_hidden_cluster_context,
    compute_hidden_cluster_exposures,
)
from src.sizing_engine import compute_capital_allocation_score
from tests.helpers import full_strong_analysis


def cluster_member(ticker: str, weight: float) -> dict:
    row = full_strong_analysis(ticker)
    row.update(
        {
            "position_weight": weight,
            "current_value": weight * 100_000,
            "sector": "Semiconductors" if ticker in {"NVDA", "AVGO", "ASML"} else "Cloud Computing",
            "factor_exposure": ["technology", "AI", "semiconductors", "cloud"],
            "data_reliability_level": "HIGH",
            "business_quality_score": 90,
        }
    )
    return row


class HiddenClusterEngineTest(unittest.TestCase):
    def test_hidden_cluster_exposure_detects_ai_semi_cloud_cluster(self):
        analyses = {
            "NVDA": cluster_member("NVDA", 0.22),
            "AVGO": cluster_member("AVGO", 0.18),
            "MSFT": cluster_member("MSFT", 0.15),
            "ASML": cluster_member("ASML", 0.10),
            "VFV.TO": {"ticker": "VFV.TO", "position_weight": 0.35, "benchmark_role": True},
        }

        exposures = compute_hidden_cluster_exposures(analyses)

        self.assertGreaterEqual(exposures["AI_SEMI_CLOUD_INFRA"], 0.60)

    def test_high_cagr_cluster_adjustment_is_capped_and_exception_reduces_it(self):
        exposures = {"AI_SEMI_CLOUD_INFRA": 0.65}
        ordinary = cluster_member("GOOGL", 0.0)
        ordinary["data_reliability_level"] = "MEDIUM"
        exceptional = cluster_member("GOOGL", 0.0)
        exceptional.update(
            {
                "data_reliability_level": "HIGH",
                "business_quality_score": 92,
                "conviction_score": 90,
                "expected_cagr_quality": "VERY_HIGH",
                "opportunity_cost_status": "CLEARLY_BETTER_THAN_VFV",
                "quality_but_too_expensive": False,
            }
        )

        ordinary_context = compute_hidden_cluster_context(ordinary, exposures, mode="high-cagr")
        exceptional_context = compute_hidden_cluster_context(exceptional, exposures, mode="high-cagr")

        self.assertEqual(ordinary_context["hidden_cluster_risk_level"], "EXTREME")
        self.assertEqual(ordinary_context["hidden_cluster_adjustment"], -3.0)
        self.assertLess(exceptional_context["hidden_cluster_adjustment"], 0)
        self.assertGreater(exceptional_context["hidden_cluster_adjustment"], ordinary_context["hidden_cluster_adjustment"])
        self.assertTrue(exceptional_context["hidden_cluster_exception_applied"])

    def test_sizing_applies_hidden_cluster_adjustment_without_changing_fundamental_score(self):
        analysis = cluster_member("MSFT", 0.0)
        base = compute_capital_allocation_score(analysis, {"concentration_by_sector": {}, "top3_weight": 0})
        analysis["hidden_cluster_adjustment"] = -2.5
        adjusted = compute_capital_allocation_score(analysis, {"concentration_by_sector": {}, "top3_weight": 0})

        self.assertAlmostEqual(
            adjusted["capital_allocation_score"],
            base["capital_allocation_score"] - 2.5,
            places=2,
        )
        self.assertEqual(analysis["score_total"], analysis["score_total"])
        self.assertEqual(adjusted["capital_allocation_components"]["hidden_cluster_adjustment"], -2.5)

    def test_apply_guardrail_updates_portfolio_risk_alerts(self):
        analyses = {
            "NVDA": cluster_member("NVDA", 0.25),
            "AVGO": cluster_member("AVGO", 0.20),
            "MSFT": cluster_member("MSFT", 0.15),
            "COST": cluster_member("COST", 0.05),
        }
        portfolio_risk = {"alerts": []}

        apply_hidden_cluster_guardrails(analyses, {}, {}, {}, portfolio_risk, mode="high-cagr")

        self.assertIn("hidden_cluster_exposure", portfolio_risk)
        self.assertTrue(any(alert["risk_type"] == "cluster_caché" for alert in portfolio_risk["alerts"]))
        self.assertIn(analyses["NVDA"]["hidden_cluster_risk_level"], {"HIGH", "EXTREME"})


if __name__ == "__main__":
    unittest.main()

