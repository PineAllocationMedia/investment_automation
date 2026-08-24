import tempfile
import unittest
from collections import namedtuple
from pathlib import Path

from src.storage_observability_engine import build_storage_health_rows


class StorageObservabilityTest(unittest.TestCase):
    def test_disk_warning_is_deterministic_and_non_mutating(self):
        Usage = namedtuple("Usage", "total used free")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data" / "cached_market_data").mkdir(parents=True)
            (root / "reports" / "history").mkdir(parents=True)
            rows = build_storage_health_rows(
                root,
                raw_log_dir=root / "logs",
                disk_usage_provider=lambda _path: Usage(1000, 960, 40),
                thresholds={
                    "free_warn": 100,
                    "free_critical": 50,
                    "free_warn_percent": 10,
                    "free_critical_percent": 5,
                },
            )

        free = next(row for row in rows if row["check"] == "storage:free_space")
        self.assertEqual(free["status"], "WARN")
        self.assertEqual(free["severity"], "HIGH")

    def test_structured_history_is_measured_separately_from_raw_logs(self):
        Usage = namedtuple("Usage", "total used free")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data").mkdir(parents=True)
            (root / "data" / "run_log_history.csv").write_text("history" * 20, encoding="utf-8")
            logs = root / "logs"
            logs.mkdir()
            (logs / "analysis_high-cagr_1.log").write_text("raw", encoding="utf-8")
            rows = build_storage_health_rows(
                root,
                raw_log_dir=logs,
                disk_usage_provider=lambda _path: Usage(10_000, 1_000, 9_000),
                thresholds={
                    "free_warn": 100,
                    "free_critical": 50,
                    "free_warn_percent": 10,
                    "free_critical_percent": 5,
                },
            )

        raw = next(row for row in rows if row["check"] == "storage:raw_logs")
        structured = next(row for row in rows if row["check"] == "storage:structured_history")
        self.assertIn("1 file(s)", raw["details"])
        self.assertIn("1 file(s)", structured["details"])

    def test_production_script_retains_approximately_one_hundred_logs_only(self):
        root = Path(__file__).resolve().parents[1]
        script = (root / "scripts" / "run_investment_analysis.sh").read_text(encoding="utf-8")

        self.assertIn("PRODUCTION_LOG_RETENTION_COUNT:-100", script)
        self.assertIn("analysis_*.log", script)
        self.assertNotIn("run_log_history.csv", script)
        self.assertNotIn("account_performance_history.csv", script)


if __name__ == "__main__":
    unittest.main()
