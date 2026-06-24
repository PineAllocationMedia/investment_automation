import unittest
from datetime import datetime

from src.data_freshness_engine import (
    apply_market_freshness_to_reliability,
    compute_market_data_freshness,
    compute_overall_data_freshness,
)


class DataFreshnessTest(unittest.TestCase):
    def test_recent_market_data_is_fresh(self):
        freshness = compute_market_data_freshness(
            {"source": "yfinance", "fetched_at": "2026-05-06T08:00:00", "current_price": 100},
            now=datetime(2026, 5, 6, 12, 0, 0),
        )

        self.assertEqual(freshness["market_data_freshness_level"], "FRESH")
        self.assertFalse(freshness["market_data_requires_refresh"])
        self.assertEqual(freshness["market_data_freshness_penalty"], 0.0)

    def test_stale_cache_reduces_reliability_and_requires_refresh(self):
        freshness = compute_market_data_freshness(
            {
                "source": "stale_cache",
                "fetched_at": "2026-04-20T08:00:00",
                "current_price": 100,
                "stale_cache_warning": "Actualisation impossible",
            },
            now=datetime(2026, 5, 6, 12, 0, 0),
        )
        reliability = apply_market_freshness_to_reliability(
            {
                "data_reliability_score": 90,
                "data_reliability_level": "HIGH",
                "data_reliability_reasons": [],
                "requires_manual_validation_for_large_allocation": False,
                "research_report_freshness_level": "NO_REPORT",
            },
            freshness,
        )

        self.assertEqual(freshness["market_data_freshness_level"], "STALE")
        self.assertTrue(reliability["market_data_requires_refresh"])
        self.assertTrue(reliability["requires_manual_validation_for_large_allocation"])
        self.assertLess(reliability["data_reliability_score"], 90)
        self.assertEqual(reliability["overall_data_freshness_level"], "STALE_REFRESH_RECOMMENDED")

    def test_unavailable_price_is_critical(self):
        freshness = compute_market_data_freshness(
            {"source": "unavailable", "fetched_at": "2026-05-06T08:00:00", "current_price": None},
            now=datetime(2026, 5, 6, 12, 0, 0),
        )
        overall = compute_overall_data_freshness({**freshness, "research_report_freshness_level": "NO_REPORT"})

        self.assertEqual(freshness["market_data_freshness_level"], "UNAVAILABLE")
        self.assertTrue(freshness["market_data_requires_refresh"])
        self.assertEqual(overall["overall_data_freshness_level"], "CRITICAL_REFRESH_NEEDED")


if __name__ == "__main__":
    unittest.main()
