import tempfile
import unittest
from pathlib import Path

from src.source_health_engine import (
    SOURCE_HEALTH_HISTORY_COLUMNS,
    build_source_health_rows,
    update_source_health_history,
)
from src.utils import read_csv_records


class SourceHealthEngineTest(unittest.TestCase):
    def test_flags_degraded_market_data_without_changing_analysis(self):
        rows = build_source_health_rows(
            {
                "CORE_PORTFOLIO": {
                    "MSFT": {
                        "ticker": "MSFT",
                        "current_price": 100,
                        "market_data_freshness_level": "FRESH",
                        "market_data_requires_refresh": False,
                        "quote_currency": "USD",
                        "official_supported_fields": ["revenue_growth"],
                    },
                    "BAD": {
                        "ticker": "BAD",
                        "current_price": None,
                        "market_data_freshness_level": "UNAVAILABLE",
                        "market_data_requires_refresh": True,
                        "quote_currency": "USD",
                        "auto_estimate_dependency": "HIGH",
                    },
                }
            },
            mode="high-cagr",
        )

        market = next(row for row in rows if row["source"] == "Yahoo/yfinance market data")
        proxies = next(row for row in rows if row["source"] == "Automatic proxy estimates")
        self.assertEqual(market["affected_ticker_count"], 1)
        self.assertIn("BAD", market["affected_tickers"])
        self.assertLess(market["health_score"], 85)
        self.assertIn(proxies["status"], {"WATCH", "DEGRADED", "CRITICAL"})

    def test_history_is_mode_and_date_aware(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "source_health_history.csv"
            rows = [
                {
                    "source": "Yahoo/yfinance market data",
                    "status": "OK",
                    "health_score": 90,
                    "coverage_rate": 1,
                    "freshness_rate": 1,
                    "affected_ticker_count": 0,
                    "affected_tickers": "",
                    "conflict_count": 0,
                    "critical_gap_count": 0,
                    "ticker_count": 1,
                    "trend": "NEW",
                    "action": "ok",
                    "notes": "ok",
                }
            ]
            update_source_health_history(path, rows, mode="high-cagr", date="2026-05-01")
            update_source_health_history(path, [{**rows[0], "health_score": 80}], mode="balanced", date="2026-05-01")
            update_source_health_history(path, [{**rows[0], "health_score": 95}], mode="high-cagr", date="2026-05-01")

            history = read_csv_records(path)
            self.assertEqual(len(history), 2)
            self.assertEqual(set(history[0].keys()), set(SOURCE_HEALTH_HISTORY_COLUMNS))
            high_cagr = [row for row in history if row["mode"] == "high-cagr"][0]
            balanced = [row for row in history if row["mode"] == "balanced"][0]
            self.assertEqual(high_cagr["health_score"], "95")
            self.assertEqual(balanced["health_score"], "80")


if __name__ == "__main__":
    unittest.main()
