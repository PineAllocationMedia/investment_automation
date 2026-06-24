import unittest

from tests.helpers import full_strong_analysis
from main import apply_external_superiority_gate
from src.market_scanner import classify_market_candidate, compute_valuation_status, market_prefilter


class MarketScannerTest(unittest.TestCase):
    def test_top_candidate_requires_manual_review_status(self):
        analysis = full_strong_analysis("NVDA")
        analysis["market_cap"] = 1_000_000_000_000
        analysis["profit_margins"] = 0.25
        analysis["data_quality"] = "HIGH"
        result = classify_market_candidate(analysis)
        self.assertEqual(result["candidate_status"], "MANUAL_REVIEW_TOP_CANDIDATE")
        self.assertIn("manuellement", result["candidate_reason"])

    def test_rejected_when_prefilter_fails(self):
        analysis = full_strong_analysis("SMALL")
        analysis["market_cap"] = 1_000_000_000
        analysis["profit_margins"] = -0.05
        passed, reason = market_prefilter(analysis)
        self.assertFalse(passed)
        self.assertIn("marges", reason)

    def test_low_relevance_benchmark_requires_larger_underperformance_to_fail_prefilter(self):
        analysis = full_strong_analysis("AAPL")
        analysis["price_above_sma_200"] = False
        analysis["stock_return_1y"] = -0.05
        analysis["benchmark_return_1y"] = 0.20
        analysis["benchmark_relevance_level"] = "LOW"
        analysis["benchmark_relevance_score"] = 0.25

        passed, reason = market_prefilter(analysis)

        self.assertTrue(passed)
        self.assertNotIn("sous-performance", reason)

    def test_valuation_status_detects_extreme_expense(self):
        analysis = full_strong_analysis("NVDA")
        analysis["peg"] = 4.5
        self.assertEqual(compute_valuation_status(analysis), "EXTREMELY_EXPENSIVE")

    def test_external_top_candidate_is_demoted_if_not_superior_to_core(self):
        core = full_strong_analysis("MSFT")
        external = full_strong_analysis("NVDA")
        core["score_total"] = 9.5
        core["conviction_score"] = 95
        core["business_quality_score"] = 95
        core["high_cagr_potential_score"] = 95
        core["quality_cagr_intersection"] = 95
        external["business_quality_score"] = 85
        external["high_cagr_potential_score"] = 82
        external["quality_cagr_intersection"] = 82
        external["watchlist_status"] = "HIGH_PRIORITY_WATCH"
        external["watchlist_reason"] = "Strong."
        apply_external_superiority_gate(external, {"MSFT": core})
        self.assertEqual(external["watchlist_status"], "INTERESTING_BUT_WAIT")


if __name__ == "__main__":
    unittest.main()
