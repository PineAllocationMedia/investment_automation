import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.run_logging_engine import (
    append_run_log_history,
    build_analysis_run_log,
    build_health_check_run_log,
    build_walk_forward_run_log,
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
            source_health_rows=[
                {
                    "source": "Yahoo/yfinance market data",
                    "status": "DEGRADED",
                    "health_score": 55,
                    "audit_signal": "PARTIAL_COVERAGE:2",
                }
            ],
            source_conflict_rows=[{"ticker": "AAPL", "universe": "CORE_PORTFOLIO", "severity": "REVIEW", "metric": "profit_margins"}],
            ticker_memory_rows=[{"ticker": "XYZ", "ticker_memory_status": "NEEDS_TICKER_REVIEW"}],
        )

        events = {row["event"] for row in extended}
        self.assertIn("SOURCE_HEALTH_WARNINGS", events)
        self.assertIn("SOURCE_CONFLICTS", events)
        self.assertIn("TICKER_MEMORY_REVIEW", events)
        source_row = next(row for row in extended if row["event"] == "SOURCE_HEALTH_WARNINGS")
        self.assertIn("PARTIAL_COVERAGE", source_row["details"])

    def test_analysis_log_counts_french_high_validation_priorities(self):
        rows = build_analysis_run_log(
            run_id="run-fr-priority",
            mode="high-cagr",
            capital=0,
            refresh_market_data=False,
            validation_priority_rows=[
                {"ticker": "RHM.NE", "priority": "TRES_HAUTE", "field": "fair_value"},
                {"ticker": "CLS.TO", "priority": "HAUTE", "field": "fair_value"},
                {"ticker": "AAPL", "priority": "MOYENNE", "field": "peg_manual"},
            ],
            allocation_result={"allocations": []},
        )

        priority_row = next(row for row in rows if row["event"] == "HIGH_PRIORITY_VALIDATION")
        self.assertIn("2 validation(s)", priority_row["message"])

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

    def test_walk_forward_log_flags_weak_regime_without_error(self):
        rows = build_walk_forward_run_log(
            run_id="walk-1",
            mode="high-cagr",
            refresh_market_data=False,
            result={
                "coverage": {"status": "READY_FOR_WALK_FORWARD_SIMULATION"},
                "summary": {
                    "status": "READY_FOR_WALK_FORWARD_REVIEW",
                    "usable_walk_forward_periods": 6,
                    "simulated_periods": 6,
                    "price_return_basis": "ADJUSTED_CLOSE_TOTAL_RETURN_PROXY",
                    "regime_coverage_status": "HAS_WEAK_REGIME",
                    "weak_regimes": "VFV_WEAK",
                },
                "regime_rows": [
                    {
                        "market_regime": "VFV_WEAK",
                        "regime_status": "WEAK",
                        "period_count": 2,
                        "compounded_excess_return_vs_vfv": -0.08,
                    }
                ],
            },
        )

        events = {row["event"] for row in rows}
        self.assertIn("WALK_FORWARD_SUMMARY", events)
        self.assertIn("WALK_FORWARD_REGIME_CHECK", events)
        self.assertTrue(any(row["level"] == "WARN" for row in rows))
        self.assertFalse(any(row["level"] == "ERROR" for row in rows))


if __name__ == "__main__":
    unittest.main()
