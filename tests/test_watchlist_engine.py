import unittest

from tests.helpers import full_strong_analysis
from src.watchlist_engine import classify_watchlist_analysis


class WatchlistEngineTest(unittest.TestCase):
    def test_high_priority_watch_for_exceptional_candidate(self):
        analysis = full_strong_analysis("NVDA")
        result = classify_watchlist_analysis(analysis)
        self.assertEqual(result["watchlist_status"], "HIGH_PRIORITY_WATCH")

    def test_insufficient_data_when_missing_data_is_high(self):
        analysis = full_strong_analysis("NVDA")
        analysis["score_missing_data_count"] = 8
        result = classify_watchlist_analysis(analysis)
        self.assertEqual(result["watchlist_status"], "INSUFFICIENT_DATA")

    def test_too_expensive_when_quality_is_expensive(self):
        analysis = full_strong_analysis("NVDA")
        analysis["quality_but_too_expensive"] = True
        analysis["peg"] = 3.5
        result = classify_watchlist_analysis(analysis)
        self.assertEqual(result["watchlist_status"], "TOO_EXPENSIVE")


if __name__ == "__main__":
    unittest.main()
