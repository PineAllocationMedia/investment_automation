import tempfile
import unittest
from pathlib import Path

from src.health_check_engine import walk_forward_health_rows
from src.utils import write_csv_records


class HealthCheckEngineTest(unittest.TestCase):
    def test_walk_forward_not_ready_is_info_not_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reports = root / "reports"
            reports.mkdir()
            write_csv_records(
                reports / "latest_walk_forward_summary.csv",
                [
                    {
                        "status": "NO_USABLE_PERIODS",
                        "usable_walk_forward_periods": 0,
                        "simulated_periods": 0,
                        "price_return_basis": "NOT_RUN_NO_USABLE_PERIODS",
                    }
                ],
                ["status", "usable_walk_forward_periods", "simulated_periods", "price_return_basis"],
            )
            write_csv_records(
                reports / "latest_walk_forward_coverage.csv",
                [{"usable_walk_forward_periods": 0}],
                ["usable_walk_forward_periods"],
            )
            write_csv_records(reports / "latest_walk_forward_periods.csv", [], ["status"])
            (reports / "latest_walk_forward_report.md").write_text("test", encoding="utf-8")

            rows = walk_forward_health_rows(root)
            walk = [row for row in rows if row["check"] == "walk_forward"]

        self.assertEqual(walk[0]["status"], "INFO")
        self.assertIn("trop jeune", walk[0]["details"])

    def test_partial_walk_forward_outputs_warn(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reports = root / "reports"
            reports.mkdir()
            write_csv_records(
                reports / "latest_walk_forward_summary.csv",
                [{"status": "PRELIMINARY_WALK_FORWARD"}],
                ["status"],
            )

            rows = walk_forward_health_rows(root)
            walk = [row for row in rows if row["check"] == "walk_forward"]

        self.assertEqual(walk[0]["status"], "WARN")
        self.assertIn("partielles", walk[0]["details"])


if __name__ == "__main__":
    unittest.main()
