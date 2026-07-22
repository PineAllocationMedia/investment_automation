import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from src.health_check_engine import walk_forward_health_rows
from src.source_health_engine import check_canadian_source_health
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

    def test_canadian_source_health_missing_cache_is_dead(self):
        with tempfile.TemporaryDirectory() as directory:
            health = check_canadian_source_health(Path(directory) / "missing_cache")

        self.assertEqual(health["canadian_source_health_status"], "DEAD")
        self.assertFalse(health["canadian_fallback_available"])

    def test_canadian_source_health_unavailable_recent_cache_is_dead(self):
        with tempfile.TemporaryDirectory() as directory:
            source_dir = Path(directory) / "canadian_sources"
            source_dir.mkdir()
            fetched_at = datetime.now().isoformat(timespec="seconds")
            (source_dir / "stockanalysis_tsx_TEST.json").write_text(
                '{"fetched_at": "%s", "parsed_payload": {"available": false}}' % fetched_at,
                encoding="utf-8",
            )

            health = check_canadian_source_health(Path(directory))

        self.assertEqual(health["canadian_source_health_status"], "DEAD")
        self.assertFalse(health["canadian_fallback_available"])
        self.assertEqual(health["sources"]["stockanalysis"]["attempted_files"], 1)

    def test_canadian_source_health_recent_available_source_is_healthy(self):
        with tempfile.TemporaryDirectory() as directory:
            source_dir = Path(directory) / "canadian_sources"
            source_dir.mkdir()
            fetched_at = datetime.now().isoformat(timespec="seconds")
            (source_dir / "tmx_tsx_TEST.json").write_text(
                '{"fetched_at": "%s", "parsed_payload": {"available": true}}' % fetched_at,
                encoding="utf-8",
            )

            health = check_canadian_source_health(Path(directory))

        self.assertEqual(health["canadian_source_health_status"], "HEALTHY")
        self.assertTrue(health["canadian_fallback_available"])

    def test_canadian_source_health_old_success_is_degraded_when_recent_attempt_exists(self):
        with tempfile.TemporaryDirectory() as directory:
            source_dir = Path(directory) / "canadian_sources"
            source_dir.mkdir()
            stale_success = (datetime.now() - timedelta(hours=96)).isoformat(timespec="seconds")
            recent_attempt = datetime.now().isoformat(timespec="seconds")
            (source_dir / "sedarplus_tsx_OLD.json").write_text(
                '{"fetched_at": "%s", "parsed_payload": {"available": true}}' % stale_success,
                encoding="utf-8",
            )
            (source_dir / "tmx_tsx_RECENT.json").write_text(
                '{"fetched_at": "%s", "parsed_payload": {"available": false}}' % recent_attempt,
                encoding="utf-8",
            )

            health = check_canadian_source_health(Path(directory))

        self.assertEqual(health["canadian_source_health_status"], "DEGRADED")
        self.assertTrue(health["canadian_fallback_available"])

    def test_canadian_source_health_too_old_success_with_recent_failures_is_dead(self):
        with tempfile.TemporaryDirectory() as directory:
            source_dir = Path(directory) / "canadian_sources"
            source_dir.mkdir()
            too_old_success = (datetime.now() - timedelta(hours=240)).isoformat(timespec="seconds")
            recent_attempt = datetime.now().isoformat(timespec="seconds")
            (source_dir / "stockanalysis_tsx_OLD.json").write_text(
                '{"fetched_at": "%s", "parsed_payload": {"available": true}}' % too_old_success,
                encoding="utf-8",
            )
            (source_dir / "tmx_tsx_RECENT.json").write_text(
                '{"fetched_at": "%s", "parsed_payload": {"available": false}}' % recent_attempt,
                encoding="utf-8",
            )

            health = check_canadian_source_health(Path(directory))

        self.assertEqual(health["canadian_source_health_status"], "DEAD")
        self.assertFalse(health["canadian_fallback_available"])


if __name__ == "__main__":
    unittest.main()
