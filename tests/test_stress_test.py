import unittest
from pathlib import Path

from src.stress_test_engine import compute_stress_tests


class StressTestTest(unittest.TestCase):
    def test_bear_market_loss_is_calculated(self):
        rows = [{"ticker": "MSFT", "current_value": 1000}, {"ticker": "VFV.TO", "current_value": 1000}]
        results = compute_stress_tests(rows, {}, {})
        bear = results[0]
        self.assertEqual(bear["scenario"], "Bear market normal")
        self.assertAlmostEqual(bear["estimated_loss_dollars"], 450)

    def test_sequential_scenarios_are_deterministic_and_multi_phase(self):
        rows = [
            {
                "ticker": "MSFT",
                "current_value": 1000,
                "thesis_status": "INTACT",
                "long_term_durability_status": "VERY_DURABLE_COMPOUNDER",
            },
            {"ticker": "BAM", "current_value": 500, "cycle_bubble_risk_level": "HIGH"},
            {"ticker": "VFV.TO", "current_value": 500, "asset_type": "ETF_EQUITY"},
        ]
        exposures = {
            "MSFT": {"factor_exposure": ["technology", "cloud", "growth"]},
            "BAM": {"factor_exposure": ["financials", "rates_sensitive"]},
            "VFV.TO": {"factor_exposure": ["broad_market"]},
        }
        sectors = {"MSFT": "Cloud Computing", "BAM": "Alternative Asset Management", "VFV.TO": "S&P 500 ETF"}

        first = compute_stress_tests(rows, exposures, sectors)
        second = compute_stress_tests(rows, exposures, sectors)

        self.assertEqual(first, second)
        sequential = [row for row in first if row.get("scenario_type") == "sequential_stylized"]
        self.assertGreaterEqual(len(sequential), 4)
        self.assertTrue(all(len(row.get("phase_path", [])) > 1 for row in sequential))
        self.assertTrue(all(row.get("diagnostic_only") is True for row in sequential))

    def test_missing_metadata_does_not_crash_sequential_stress(self):
        rows = [{"ticker": "UNKNOWN.TO", "current_value": 1000}]
        results = compute_stress_tests(rows, {}, {})
        sequential = [row for row in results if row.get("scenario_type") == "sequential_stylized"]

        self.assertTrue(sequential)
        self.assertTrue(all(row.get("scenario_quality") in {"LOW", "MEDIUM", "HIGH"} for row in sequential))
        self.assertTrue(all(row.get("estimated_loss_dollars") >= 0 for row in sequential))

    def test_sequential_stress_does_not_emit_allocation_override(self):
        rows = [{"ticker": "MSFT", "current_value": 1000}]
        results = compute_stress_tests(rows, {}, {})
        forbidden_keys = {"allocation_override", "sell_signal_override", "raise_cash", "block_recommendation"}

        for scenario in results:
            self.assertFalse(forbidden_keys & set(scenario.keys()))

    def test_stress_engine_does_not_introduce_statistical_optimizer_terms(self):
        source = (Path(__file__).resolve().parents[1] / "src" / "stress_test_engine.py").read_text()
        forbidden_terms = [
            "covariance",
            "correlation matrix",
            "pca",
            "eigen",
            "ledoit",
            "mean-variance",
        ]

        for term in forbidden_terms:
            self.assertNotIn(term, source.lower())


if __name__ == "__main__":
    unittest.main()
