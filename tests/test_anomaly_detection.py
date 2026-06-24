import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.anomaly_detection_engine import (
    detect_analysis_anomalies,
    update_anomaly_history,
)
from src.utils import read_csv_records


class AnomalyDetectionEngineTest(unittest.TestCase):
    def test_detects_allocated_score_and_conviction_drop(self):
        rows = detect_analysis_anomalies(
            mode="high-cagr",
            analyses={
                "MSFT": {
                    "ticker": "MSFT",
                    "universe": "CORE_PORTFOLIO",
                    "score_total": 7.1,
                    "previous_score_total": 9.0,
                    "score_total_change": -1.9,
                    "conviction_score": 62,
                    "previous_conviction_score": 85,
                    "conviction_score_change": -23,
                    "capital_allocation_score": 61,
                    "previous_capital_allocation_score": 86,
                    "capital_allocation_score_change": -25,
                    "thesis_status": "INTACT",
                    "previous_thesis_status": "INTACT",
                    "liquidation_status": "GREEN",
                    "previous_liquidation_status": "GREEN",
                }
            },
            allocation_result={"allocations": [{"ticker": "MSFT", "amount": 250, "percentage": 0.5}]},
        )

        anomaly_types = {row["anomaly_type"] for row in rows}
        self.assertIn("SCORE_DROP", anomaly_types)
        self.assertIn("CONVICTION_DROP", anomaly_types)
        self.assertTrue(any(row["requires_improvement_audit"] for row in rows))

    def test_fallback_market_data_is_warning_not_auto_audit(self):
        rows = detect_analysis_anomalies(
            mode="high-cagr",
            analyses={
                "APP": {
                    "ticker": "APP",
                    "universe": "CORE_PORTFOLIO",
                    "market_data_fetch_status": "FALLBACK_STALE_CACHE",
                    "market_data_fallback_level": "STALE_CACHE",
                    "market_data_freshness_level": "STALE_CACHE",
                }
            },
            allocation_result={"allocations": [{"ticker": "APP", "amount": 200, "percentage": 0.4}]},
        )

        row = next(row for row in rows if row["anomaly_type"] == "MARKET_DATA_FALLBACK_USED")
        self.assertEqual(row["severity"], "MEDIUM")
        self.assertFalse(row["requires_improvement_audit"])

    def test_validation_load_is_flagged_for_allocated_tickers(self):
        rows = detect_analysis_anomalies(
            mode="high-cagr",
            analyses={"MSFT": {"ticker": "MSFT", "universe": "CORE_PORTFOLIO"}},
            allocation_result={"allocations": [{"ticker": "MSFT", "amount": 100, "percentage": 0.2}]},
            validation_priority_rows=[
                {"ticker": "MSFT", "priority": "TRES_HAUTE", "field": "fair_value"},
                {"ticker": "MSFT", "priority": "HAUTE", "field": "roic_5y_avg"},
            ],
        )

        self.assertIn("ALLOCATED_TICKERS_NEED_VALIDATION", {row["anomaly_type"] for row in rows})

    def test_no_major_anomaly_returns_info_row(self):
        rows = detect_analysis_anomalies(
            mode="balanced",
            analyses={"VFV.TO": {"ticker": "VFV.TO", "universe": "CORE_PORTFOLIO"}},
            allocation_result={"allocations": [{"ticker": "VFV.TO", "amount": 100, "percentage": 1.0}]},
        )

        self.assertEqual(rows[0]["anomaly_type"], "NO_MAJOR_ANOMALY")
        self.assertEqual(rows[0]["severity"], "INFO")

    def test_anomaly_history_is_idempotent_by_date_and_mode(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "anomaly_history.csv"
            first = [{"date": "2026-06-01", "mode": "high-cagr", "scope": "GLOBAL", "ticker": "", "anomaly_type": "OLD"}]
            second = [{"date": "2026-06-01", "mode": "high-cagr", "scope": "GLOBAL", "ticker": "", "anomaly_type": "NEW"}]

            update_anomaly_history(path, first, mode="high-cagr", date="2026-06-01")
            update_anomaly_history(path, second, mode="high-cagr", date="2026-06-01")

            history = read_csv_records(path)
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0]["anomaly_type"], "NEW")


if __name__ == "__main__":
    unittest.main()
