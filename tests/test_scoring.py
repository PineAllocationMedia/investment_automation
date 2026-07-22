import unittest

from tests.helpers import strong_benchmark, strong_manual, strong_market
from src.scoring import compute_fundamental_score


class ScoringTest(unittest.TestCase):
    def test_strong_company_scores_ten(self):
        score = compute_fundamental_score("MSFT", strong_manual(), strong_market(), strong_benchmark())
        self.assertEqual(score["score_total"], 10)
        self.assertEqual(score["score_missing_data_count"], 0)
        self.assertEqual(score["confidence_level"], "HIGH")

    def test_benchmark_uses_shorter_free_history_when_ten_year_is_missing(self):
        benchmark = {
            "benchmark_10y_cagr": None,
            "benchmark_5y_cagr": 0.08,
            "benchmark_usable_cagr": 0.08,
            "benchmark_usable_period": "5 ans",
            "benchmark_above_sma_200": True,
        }
        score = compute_fundamental_score("MSFT", strong_manual(), strong_market(), benchmark)
        self.assertEqual(score["criteria"]["C7"]["points"], 1.0)
        self.assertIn("5 ans", score["criteria"]["C7"]["detail"])
        self.assertNotIn("None", score["criteria"]["C7"]["detail"])

    def test_benchmark_detail_says_data_unavailable_when_no_history_exists(self):
        benchmark = {
            "benchmark_usable_cagr": None,
            "benchmark_usable_period": "Donnée pas dispo",
            "benchmark_above_sma_200": None,
        }
        score = compute_fundamental_score("MSFT", strong_manual(), strong_market(), benchmark)
        self.assertIsNone(score["criteria"]["C7"]["points"])
        self.assertIn("Donnée pas dispo", score["criteria"]["C7"]["detail"])

    def test_bank_profile_uses_adapted_thresholds(self):
        manual = strong_manual()
        manual["roic_5y_avg"] = 10
        manual["eps_growth_5y"] = 7
        manual["eps_growth_estimated_3_5y"] = 8
        manual["sector_cagr_estimated"] = 4
        manual["forward_pe_manual"] = 16
        manual["peg_manual"] = 2.4
        market = strong_market()
        market["forward_pe"] = None
        market["peg"] = None

        score = compute_fundamental_score("TD.TO", manual, market, strong_benchmark())

        self.assertEqual(score["business_profile"], "BANK")
        self.assertEqual(score["criteria"]["C1"]["points"], 0.4)
        self.assertEqual(score["criteria"]["C5"]["points"], 0.4571)
        self.assertEqual(score["criteria"]["C6"]["points"], 0.4)
        self.assertEqual(score["criteria"]["C8"]["points"], 1.0)

    def test_quantitative_criteria_use_continuous_magnitude_scoring(self):
        manual = strong_manual()
        manual["roic_5y_avg"] = 15
        manual["eps_growth_5y"] = 17.5
        manual["eps_growth_estimated_3_5y"] = 30
        manual["sector_cagr_estimated"] = 4

        score = compute_fundamental_score("MSFT", manual, strong_market(), strong_benchmark())

        self.assertEqual(score["criteria"]["C1"]["points"], 0.4)
        self.assertEqual(score["criteria"]["C3"]["points"], 0.7)
        self.assertEqual(score["criteria"]["C5"]["points"], 1.0)
        self.assertEqual(score["criteria"]["C6"]["points"], 0.0)
        self.assertIn("ratio=1.00×", score["criteria"]["C1"]["detail"])
        self.assertIn("ratio=1.75×", score["criteria"]["C3"]["detail"])


if __name__ == "__main__":
    unittest.main()
