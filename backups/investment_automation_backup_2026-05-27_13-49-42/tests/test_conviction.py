import unittest

from tests.helpers import strong_benchmark, strong_manual, strong_market
from src.conviction_engine import compute_conviction_score
from src.scoring import compute_fundamental_score


class ConvictionTest(unittest.TestCase):
    def test_conviction_is_capped_at_100_for_exceptional_inputs(self):
        manual = strong_manual()
        market = strong_market()
        benchmark = strong_benchmark()
        score = compute_fundamental_score("MSFT", manual, market, benchmark)
        conviction = compute_conviction_score(manual, score, "INTACT", market, benchmark)
        self.assertEqual(conviction["conviction_score"], 100)
        self.assertEqual(conviction["conviction_category"], "VERY_HIGH")

    def test_low_relevance_benchmark_has_smaller_conviction_impact(self):
        manual = strong_manual()
        manual["management_quality_good"] = False
        manual["balance_sheet_strong"] = False
        manual["manual_confidence_level"] = "MEDIUM"
        market = strong_market()
        market["stock_return_1y"] = -0.05
        benchmark_high = strong_benchmark()
        benchmark_high["benchmark_5y_cagr"] = 0.0
        benchmark_high["benchmark_return_1y"] = 0.20
        benchmark_high["benchmark_relevance_level"] = "HIGH"
        benchmark_high["benchmark_relevance_score"] = 1.0
        benchmark_low = dict(benchmark_high)
        benchmark_low["benchmark_relevance_level"] = "LOW"
        benchmark_low["benchmark_relevance_score"] = 0.25
        score = compute_fundamental_score("AAPL", manual, market, benchmark_high)
        score["score_total"] = 7.5

        high_penalty = compute_conviction_score(manual, score, "INTACT", market, benchmark_high)
        low_penalty = compute_conviction_score(manual, score, "INTACT", market, benchmark_low)

        self.assertGreater(low_penalty["conviction_score"], high_penalty["conviction_score"])
        self.assertIn("pertinence LOW", " ".join(low_penalty["conviction_reasons"]))


if __name__ == "__main__":
    unittest.main()
