import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.run_logging_engine import (
    append_run_log_history,
    build_analysis_run_log,
    build_health_check_run_log,
    extend_report_run_log,
    run_log_summary,
)
from src.utils import read_csv_records


class RunLoggingEngineTest(unittest.TestCase):
    def test_analysis_log_flags_data_cache_and_anomaly_warnings(self):
        rows = build_analysis_run_log(
            run_id="run-1",
            mode="high-cagr",
            capital=500,
            refresh_market_data=True,
            universe_counts={"core": 4, "market": 10},
            cache_health_rows=[
                {
                    "category": "summary",
                    "status": "WARN",
                    "cleaned_count": 2,
                    "details": "cache fragile",
                }
            ],
            data_gaps=[{"ticker": "MSFT", "data_field": "sma_200", "importance": "HIGH"}],
            validation_priority_rows=[{"ticker": "MSFT", "priority": "HIGH", "data_field": "ROIC"}],
            anomaly_rows=[
                {
                    "ticker": "MSFT",
                    "scope": "CORE_PORTFOLIO",
                    "anomaly_type": "SCORE_DROP",
                    "severity": "MEDIUM",
                }
            ],
            allocation_result={"allocations": [{"ticker": "MSFT", "amount": 500}], "mandatory_vfv_percent": 0.1},
            portfolio_risk={"alerts": [{"risk_type": "secteur", "name": "Tech", "weight": 0.5, "alert": "élevé"}]},
        )

        events = {row["event"] for row in rows}
        self.assertIn("CACHE_HEALTH", events)
        self.assertIn("HIGH_IMPORTANCE_DATA_GAPS", events)
        self.assertIn("HIGH_PRIORITY_VALIDATION", events)
        self.assertIn("POST_ANALYSIS_ANOMALIES", events)
        self.assertIn("PORTFOLIO_RISK_ALERTS", events)
        self.assertIn("avertissement", run_log_summary(rows).lower())

    def test_report_log_extension_adds_source_and_ticker_warnings(self):
        rows = build_analysis_run_log(
            run_id="run-2",
            mode="balanced",
            capital=100,
            refresh_market_data=False,
            allocation_result={"allocations": []},
        )

        extended = extend_report_run_log(
            rows,
            source_health_rows=[{"source": "Yahoo/yfinance market data", "status": "DEGRADED", "health_score": 55}],
            source_conflict_rows=[{"ticker": "AAPL", "universe": "CORE_PORTFOLIO", "severity": "REVIEW", "metric": "profit_margins"}],
            ticker_memory_rows=[{"ticker": "XYZ", "ticker_memory_status": "NEEDS_TICKER_REVIEW"}],
        )

        events = {row["event"] for row in extended}
        self.assertIn("SOURCE_HEALTH_WARNINGS", events)
        self.assertIn("SOURCE_CONFLICTS", events)
        self.assertIn("TICKER_MEMORY_REVIEW", events)

    def test_history_append_is_idempotent_by_run_id(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "run_log_history.csv"
            first = build_health_check_run_log(
                run_id="health-1",
                repair_safe=False,
                health_rows=[{"check": "csv", "status": "PASS"}],
            )
            second = build_health_check_run_log(
                run_id="health-1",
                repair_safe=True,
                health_rows=[{"check": "csv", "status": "WARN"}],
            )

            append_run_log_history(path, first)
            append_run_log_history(path, second)
            saved = read_csv_records(path)

            self.assertEqual({row["run_id"] for row in saved}, {"health-1"})
            self.assertTrue(any(row["level"] == "WARN" for row in saved))


if __name__ == "__main__":
    unittest.main()
