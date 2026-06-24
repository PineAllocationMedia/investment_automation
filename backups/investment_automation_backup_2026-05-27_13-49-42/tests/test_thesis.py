import unittest

from tests.helpers import strong_benchmark, strong_manual, strong_market
from src.thesis_engine import compute_thesis_status


class ThesisTest(unittest.TestCase):
    def test_catastrophic_signal_breaks_thesis(self):
        manual = strong_manual()
        manual["catastrophic_fraud"] = True
        thesis = compute_thesis_status(manual, {"score_missing_data_count": 0}, strong_market(), strong_benchmark())
        self.assertEqual(thesis["thesis_status"], "BROKEN")

    def test_too_many_missing_fields_makes_thesis_uncertain(self):
        thesis = compute_thesis_status(strong_manual(), {"score_missing_data_count": 6}, strong_market(), strong_benchmark())
        self.assertEqual(thesis["thesis_status"], "UNCERTAIN")

    def test_market_weakness_does_not_break_fundamental_thesis(self):
        manual = strong_manual()
        market = strong_market()
        market["price_above_sma_200"] = False
        market["stock_return_1y"] = -0.20
        benchmark = strong_benchmark()
        benchmark["benchmark_5y_cagr"] = 0.02
        score = {
            "score_missing_data_count": 0,
            "eps_growth_estimated_3_5y": 15,
            "eps_growth_5y": 18,
            "peg": 1.8,
            "sector_cagr_estimated": 2,
            "price_to_fair_value": 1.0,
        }

        thesis = compute_thesis_status(manual, score, market, benchmark)

        self.assertEqual(thesis["thesis_status"], "INTACT")
        self.assertEqual(thesis["fundamental_thesis_status"], "INTACT")
        self.assertIn(thesis["market_watch_status"], {"WATCH", "WEAK"})

    def test_negative_benchmark_is_market_watch_not_thesis_break(self):
        manual = strong_manual()
        benchmark = strong_benchmark()
        benchmark["benchmark_5y_cagr"] = -0.05
        score = {
            "score_missing_data_count": 0,
            "eps_growth_estimated_3_5y": 15,
            "eps_growth_5y": 18,
            "peg": 1.8,
            "sector_cagr_estimated": 7,
            "price_to_fair_value": 1.0,
        }

        thesis = compute_thesis_status(manual, score, strong_market(), benchmark)

        self.assertEqual(thesis["thesis_status"], "INTACT")
        self.assertIn("ETF", " ".join(thesis["market_watch_reasons"]))

    def test_low_relevance_benchmark_warning_is_informative(self):
        manual = strong_manual()
        benchmark = strong_benchmark()
        benchmark["benchmark_5y_cagr"] = -0.05
        benchmark["benchmark_relevance_level"] = "LOW"
        benchmark["benchmark_relevance_score"] = 0.25
        score = {
            "score_missing_data_count": 0,
            "eps_growth_estimated_3_5y": 15,
            "eps_growth_5y": 18,
            "peg": 1.8,
            "sector_cagr_estimated": 7,
            "price_to_fair_value": 1.0,
        }

        thesis = compute_thesis_status(manual, score, strong_market(), benchmark)

        self.assertEqual(thesis["thesis_status"], "INTACT")
        self.assertIn("pertinence faible", " ".join(thesis["market_watch_reasons"]))
        self.assertEqual(thesis["market_watch_status"], "WATCH")

    def test_confirmed_fundamental_damage_weakens_thesis(self):
        manual = strong_manual()
        manual["moat_clear"] = False
        manual["manual_override_fields"] = ["moat_clear"]
        score = {
            "score_missing_data_count": 0,
            "eps_growth_estimated_3_5y": 15,
            "eps_growth_5y": 18,
            "peg": 1.8,
            "sector_cagr_estimated": 8,
            "price_to_fair_value": 1.0,
        }

        thesis = compute_thesis_status(manual, score, strong_market(), strong_benchmark())

        self.assertEqual(thesis["thesis_status"], "WEAKENING")
        self.assertIn("Moat", " ".join(thesis["fundamental_thesis_reasons"]))


if __name__ == "__main__":
    unittest.main()
