from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from src.portfolio_change_tracker import PORTFOLIO_CHANGE_COLUMNS, PORTFOLIO_STATE_COLUMNS


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "scripts" / "run_automatic_portfolio_sync.py"
SPEC = importlib.util.spec_from_file_location("run_automatic_portfolio_sync", MODULE_PATH)
automatic_sync = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(automatic_sync)


VALID_PORTFOLIO = "ticker,shares,average_cost,average_cost_currency,account_type\nAAPL,2,100,USD,TFSA1\n"


class _Result:
    def __init__(self, returncode: int = 0):
        self.returncode = returncode


class AutomaticPortfolioSyncTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.source_root = self._make_source("source")
        self.project = self._make_project()
        self.state_file = self.root / "state" / "portfolio_sync_state.json"
        self.runner = Mock(return_value=_Result())

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def _make_source(self, name: str, content: str = VALID_PORTFOLIO) -> Path:
        source_root = self.root / name
        (source_root / "data").mkdir(parents=True)
        (source_root / "data" / "portfolio.csv").write_text(content, encoding="utf-8")
        return source_root

    def _make_project(self) -> Path:
        project = self.root / "project"
        python = project / ".venv" / "bin" / "python"
        python.parent.mkdir(parents=True)
        python.write_text("#!/bin/sh\n", encoding="utf-8")
        python.chmod(0o700)
        (project / "main.py").write_text("", encoding="utf-8")
        (project / "data").mkdir()
        return project

    @property
    def source_file(self) -> Path:
        return (self.source_root / "data" / "portfolio.csv").resolve()

    @property
    def destination(self) -> Path:
        return self.project / "data" / "portfolio.csv"

    def _hash(self, path: Path | None = None) -> str:
        return hashlib.sha256((path or self.source_file).read_bytes()).hexdigest()

    def _marker_payload(self, *, source: Path | None = None, source_hash: str | None = None) -> dict[str, object]:
        source = (source or self.source_file).resolve()
        return {
            "schema_version": 1,
            "processed_source_sha256": source_hash or self._hash(source),
            "processed_at": "2026-08-23T18:00:00Z",
            "source_path": str(source),
        }

    def _write_marker(self, **kwargs: object) -> dict[str, object]:
        payload = self._marker_payload(**kwargs)
        automatic_sync._write_marker(self.state_file, payload)
        return payload

    def _process(self, **overrides: object):
        arguments = {
            "explicit_source": self.source_root,
            "config_path": self.root / "missing.env",
            "project_root": self.project,
            "state_file": self.state_file,
            "settle_delay_seconds": 0,
            "environ": {},
            "sleeper": Mock(),
            "command_runner": self.runner,
            "now_utc": lambda: datetime(2026, 8, 23, 18, 30, tzinfo=timezone.utc),
        }
        arguments.update(overrides)
        return automatic_sync.process_portfolio_sync(**arguments)

    def _write_tracking_header(self, name: str, columns: list[str], row: list[str] | None = None) -> None:
        text = ",".join(columns) + "\n"
        if row is not None:
            text += ",".join(row + [""] * (len(columns) - len(row))) + "\n"
        (self.project / "data" / name).write_text(text, encoding="utf-8")

    def _stage_files(self) -> list[Path]:
        return list((self.project / "data").glob(".portfolio.csv.stage.*.tmp"))

    def test_processed_source_unchanged_is_true_no_op(self):
        self._write_marker()
        self.destination.write_bytes(self.source_file.read_bytes())
        (self.project / ".venv" / "bin" / "python").unlink()
        (self.project / "main.py").unlink()
        validator = Mock(side_effect=AssertionError("validation must not run"))
        integrity = Mock(side_effect=AssertionError("integrity must not run"))
        marker_writer = Mock(side_effect=AssertionError("marker write must not run"))

        with patch.object(automatic_sync, "validate_portfolio_file", validator), patch.object(
            automatic_sync, "_validate_tracking_integrity", integrity
        ):
            result = self._process(marker_writer=marker_writer)

        self.assertFalse(result.processed)
        self.runner.assert_not_called()
        marker_writer.assert_not_called()
        self.assertEqual(self.destination.read_bytes(), self.source_file.read_bytes())
        self.assertEqual(self._stage_files(), [])

    def test_marker_and_source_match_but_local_differs_reconciles(self):
        self._write_marker()
        self.destination.write_text(VALID_PORTFOLIO.replace("AAPL,2", "AAPL,3"), encoding="utf-8")

        result = self._process()

        self.assertTrue(result.processed)
        self.assertEqual(self.destination.read_bytes(), self.source_file.read_bytes())
        self.runner.assert_called_once()

    def test_marker_and_source_match_but_local_missing_reconciles(self):
        self._write_marker()

        result = self._process()

        self.assertTrue(result.processed)
        self.assertEqual(self.destination.read_bytes(), self.source_file.read_bytes())
        self.runner.assert_called_once()

    def test_marker_and_source_match_but_local_destination_symlink_fails_closed(self):
        self._write_marker()
        target = self.project / "elsewhere.csv"
        target.write_text(VALID_PORTFOLIO, encoding="utf-8")
        self.destination.symlink_to(target)

        with self.assertRaisesRegex(automatic_sync.AutomaticPortfolioSyncError, "symbolique"):
            self._process()

        self.runner.assert_not_called()

    def test_changed_valid_source_runs_exact_command_once_and_advances_marker(self):
        self._write_marker(source_hash="0" * 64)

        result = self._process()

        self.assertTrue(result.processed)
        self.assertEqual(self.destination.read_bytes(), self.source_file.read_bytes())
        self.runner.assert_called_once_with(
            [str(self.project.resolve() / ".venv" / "bin" / "python"), "main.py", "sync-portfolio"],
            cwd=self.project.resolve(),
            check=False,
        )
        marker = json.loads(self.state_file.read_text(encoding="utf-8"))
        self.assertEqual(marker["processed_source_sha256"], self._hash())
        self.assertEqual(marker["source_path"], str(self.source_file))
        self.assertEqual(marker["processed_at"], "2026-08-23T18:30:00Z")

    def test_repeated_identical_processed_source_does_not_sync_twice(self):
        self._process()
        self._process()

        self.runner.assert_called_once()

    def test_missing_marker_processes_even_when_local_bytes_match(self):
        self.destination.write_bytes(self.source_file.read_bytes())

        result = self._process()

        self.assertTrue(result.processed)
        self.runner.assert_called_once()
        self.assertTrue(self.state_file.is_file())

    def test_invalid_source_preserves_live_portfolio(self):
        self.destination.write_text("old usable portfolio", encoding="utf-8")
        self.source_file.write_text("ticker,shares\nAAPL,-2\n", encoding="utf-8")

        with self.assertRaisesRegex(automatic_sync.AutomaticPortfolioSyncError, "portfolio invalide"):
            self._process()

        self.assertEqual(self.destination.read_text(encoding="utf-8"), "old usable portfolio")
        self.runner.assert_not_called()
        self.assertFalse(self.state_file.exists())
        self.assertEqual(self._stage_files(), [])

    def test_valid_header_only_portfolio_remains_permitted(self):
        self.source_file.write_text("ticker,shares,average_cost,average_cost_currency,account_type\n", encoding="utf-8")

        result = self._process()

        self.assertTrue(result.processed)
        self.assertEqual(self.destination.read_bytes(), self.source_file.read_bytes())
        self.runner.assert_called_once()

    def test_source_unconfigured_and_missing_fail_safely(self):
        with self.assertRaisesRegex(automatic_sync.AutomaticPortfolioSyncError, "non configurée"):
            self._process(explicit_source=None)

        missing = self.root / "missing-source"
        with self.assertRaisesRegex(automatic_sync.AutomaticPortfolioSyncError, "introuvable"):
            self._process(explicit_source=missing)

        self.runner.assert_not_called()
        self.assertFalse(self.destination.exists())

    def test_source_symlink_is_refused(self):
        real_source = self.source_file
        moved = real_source.with_name("portfolio-real.csv")
        real_source.replace(moved)
        real_source.symlink_to(moved)

        with self.assertRaisesRegex(automatic_sync.AutomaticPortfolioSyncError, "symbolique"):
            self._process()

        self.runner.assert_not_called()

    def test_source_mutation_during_staging_preserves_live_and_marker(self):
        self.destination.write_text("old", encoding="utf-8")
        old_marker = self._write_marker(source_hash="0" * 64)

        def mutate(_: float) -> None:
            self.source_file.write_text(VALID_PORTFOLIO.replace("AAPL,2", "AAPL,3"), encoding="utf-8")

        with self.assertRaisesRegex(automatic_sync.AutomaticPortfolioSyncError, "modifiée"):
            self._process(settle_delay_seconds=1, sleeper=mutate)

        self.assertEqual(self.destination.read_text(encoding="utf-8"), "old")
        self.assertEqual(json.loads(self.state_file.read_text(encoding="utf-8")), old_marker)
        self.assertEqual(self._stage_files(), [])

    def test_sync_failure_leaves_marker_unchanged_and_retry_succeeds(self):
        old_marker = self._write_marker(source_hash="0" * 64)
        self.runner.side_effect = [_Result(7), _Result(0)]

        with self.assertRaisesRegex(automatic_sync.AutomaticPortfolioSyncError, "statut 7"):
            self._process()

        self.assertEqual(json.loads(self.state_file.read_text(encoding="utf-8")), old_marker)
        retry = self._process()
        self.assertTrue(retry.processed)
        self.assertEqual(self.runner.call_count, 2)
        self.assertEqual(json.loads(self.state_file.read_text())["processed_source_sha256"], self._hash())

    def test_failed_promoted_b_then_source_reverts_to_processed_a_reconciles_a(self):
        source_a = self.source_file.read_bytes()
        self._process()
        marker_a = json.loads(self.state_file.read_text(encoding="utf-8"))

        self.source_file.write_text(VALID_PORTFOLIO.replace("AAPL,2", "AAPL,3"), encoding="utf-8")
        self.runner.return_value = _Result(9)
        with self.assertRaisesRegex(automatic_sync.AutomaticPortfolioSyncError, "statut 9"):
            self._process()
        self.assertNotEqual(self.destination.read_bytes(), source_a)
        self.assertEqual(json.loads(self.state_file.read_text(encoding="utf-8")), marker_a)

        self.source_file.write_bytes(source_a)
        self.runner.return_value = _Result(0)
        recovered = self._process()

        self.assertTrue(recovered.processed)
        self.assertEqual(self.destination.read_bytes(), source_a)
        self.assertEqual(self.runner.call_count, 3)

    def test_marker_failure_after_success_leaves_old_marker_and_retry_is_safe(self):
        old_marker = self._write_marker(source_hash="0" * 64)
        failing_writer = Mock(side_effect=OSError("disk full"))

        with self.assertRaisesRegex(OSError, "disk full"):
            self._process(marker_writer=failing_writer)

        self.assertEqual(json.loads(self.state_file.read_text(encoding="utf-8")), old_marker)
        retry = self._process()
        self.assertTrue(retry.processed)
        self.assertEqual(self.runner.call_count, 2)

    def test_marker_atomicity_preserves_old_json_when_replace_fails(self):
        old_marker = self._write_marker(source_hash="0" * 64)
        replacement = self._marker_payload()

        with patch.object(automatic_sync.os, "replace", side_effect=OSError("replace failed")):
            with self.assertRaisesRegex(OSError, "replace failed"):
                automatic_sync._write_marker(self.state_file, replacement)

        self.assertEqual(json.loads(self.state_file.read_text(encoding="utf-8")), old_marker)
        self.assertEqual(list(self.state_file.parent.glob(f".{self.state_file.name}.*.tmp")), [])

    def test_post_replace_marker_directory_fsync_failure_leaves_complete_new_marker_visible(self):
        real_fsync_directory = automatic_sync._fsync_directory

        def fail_state_directory(path: Path) -> None:
            if path == self.state_file.parent:
                raise OSError("state directory fsync failed")
            real_fsync_directory(path)

        with patch.object(automatic_sync, "_fsync_directory", side_effect=fail_state_directory):
            with self.assertRaisesRegex(automatic_sync.AutomaticPortfolioSyncError, "marqueur remplacé"):
                self._process()

        marker = json.loads(self.state_file.read_text(encoding="utf-8"))
        self.assertEqual(marker["processed_source_sha256"], self._hash())
        self.assertEqual(marker["source_path"], str(self.source_file))
        self.assertEqual(list(self.state_file.parent.glob(f".{self.state_file.name}.*.tmp")), [])
        self.runner.assert_called_once()

        retry = self._process()
        self.assertFalse(retry.processed)
        self.runner.assert_called_once()

    def test_corrupt_or_invalid_marker_fails_closed(self):
        invalid_payloads = [
            "{broken",
            json.dumps({"schema_version": 2}),
            json.dumps({**self._marker_payload(), "processed_source_sha256": "BAD"}),
            json.dumps({**self._marker_payload(), "processed_at": 123}),
            json.dumps({**self._marker_payload(), "source_path": 123}),
        ]
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                self.state_file.parent.mkdir(parents=True, exist_ok=True)
                self.state_file.write_text(payload, encoding="utf-8")
                with self.assertRaises(automatic_sync.AutomaticPortfolioSyncError):
                    self._process()
                self.runner.assert_not_called()

    def test_history_records_with_snapshot_file_missing_fails_closed(self):
        self.destination.write_text("old", encoding="utf-8")
        self._write_tracking_header("portfolio_change_history.csv", PORTFOLIO_CHANGE_COLUMNS, ["2026-08-22", "AAPL"])

        with self.assertRaisesRegex(automatic_sync.AutomaticPortfolioSyncError, "tous deux présents"):
            self._process()

        self.assertEqual(self.destination.read_text(encoding="utf-8"), "old")
        self.runner.assert_not_called()

    def test_header_only_snapshot_with_existing_history_is_allowed(self):
        self._write_tracking_header("portfolio_state_snapshot.csv", PORTFOLIO_STATE_COLUMNS)
        self._write_tracking_header("portfolio_change_history.csv", PORTFOLIO_CHANGE_COLUMNS, ["2026-08-22", "AAPL"])

        result = self._process()

        self.assertTrue(result.processed)
        self.runner.assert_called_once()

    def test_both_structurally_valid_header_only_tracking_files_are_allowed(self):
        self._write_tracking_header("portfolio_state_snapshot.csv", PORTFOLIO_STATE_COLUMNS)
        self._write_tracking_header("portfolio_change_history.csv", PORTFOLIO_CHANGE_COLUMNS)

        self.assertTrue(self._process().processed)

    def test_snapshot_positions_without_authoritative_history_fails_closed(self):
        self._write_tracking_header("portfolio_state_snapshot.csv", PORTFOLIO_STATE_COLUMNS, ["2026-08-22", "AAPL"])
        self._write_tracking_header("portfolio_change_history.csv", PORTFOLIO_CHANGE_COLUMNS)

        with self.assertRaisesRegex(automatic_sync.AutomaticPortfolioSyncError, "sans enregistrements"):
            self._process()

        self.runner.assert_not_called()

    def test_structurally_corrupt_snapshot_or_history_fails_closed(self):
        cases = (
            ("portfolio_state_snapshot.csv", PORTFOLIO_CHANGE_COLUMNS, "portfolio_change_history.csv", PORTFOLIO_CHANGE_COLUMNS),
            ("portfolio_state_snapshot.csv", PORTFOLIO_STATE_COLUMNS, "portfolio_change_history.csv", ["bad"]),
        )
        for snapshot_name, snapshot_columns, history_name, history_columns in cases:
            with self.subTest(history_columns=history_columns):
                for path in (self.project / "data").glob("portfolio_*history.csv"):
                    path.unlink()
                (self.project / "data" / "portfolio_state_snapshot.csv").unlink(missing_ok=True)
                self._write_tracking_header(snapshot_name, list(snapshot_columns))
                self._write_tracking_header(history_name, list(history_columns))
                with self.assertRaisesRegex(automatic_sync.AutomaticPortfolioSyncError, "schéma incomplet"):
                    self._process()
                self.runner.assert_not_called()

    def test_tracking_nonblank_rows_with_missing_cells_fail_closed(self):
        cases = ("portfolio_state_snapshot.csv", "portfolio_change_history.csv")
        for malformed_name in cases:
            with self.subTest(malformed_name=malformed_name):
                self._write_tracking_header("portfolio_state_snapshot.csv", PORTFOLIO_STATE_COLUMNS)
                self._write_tracking_header("portfolio_change_history.csv", PORTFOLIO_CHANGE_COLUMNS)
                with (self.project / "data" / malformed_name).open("a", encoding="utf-8") as handle:
                    handle.write("2026-08-22,AAPL\n")
                with self.assertRaisesRegex(automatic_sync.AutomaticPortfolioSyncError, "largeur de ligne invalide"):
                    self._process()
                self.runner.assert_not_called()

    def test_tracking_required_header_with_surrounding_whitespace_fails_closed(self):
        invalid_snapshot_columns = [" ticker " if column == "ticker" else column for column in PORTFOLIO_STATE_COLUMNS]
        self._write_tracking_header("portfolio_state_snapshot.csv", invalid_snapshot_columns)
        self._write_tracking_header("portfolio_change_history.csv", PORTFOLIO_CHANGE_COLUMNS)

        with self.assertRaisesRegex(automatic_sync.AutomaticPortfolioSyncError, "schéma incomplet"):
            self._process()

        self.runner.assert_not_called()

    def test_no_change_does_not_require_pdf_or_proxy_paths_or_command(self):
        self._write_marker()
        self.destination.write_bytes(self.source_file.read_bytes())
        self.assertFalse((self.source_root / "data" / "research_reports").exists())
        self.assertFalse((self.source_root / "data" / "proxy_calibration.csv").exists())

        result = self._process()

        self.assertFalse(result.processed)
        self.runner.assert_not_called()

    def test_staged_utf8_duplicate_header_and_overflow_fail_closed(self):
        invalid_bytes = (
            b"",
            b'ticker,shares\n"AAPL,2\n',
            b"ticker,shares\nAAPL,\xff\n",
            b"ticker,ticker\nAAPL,AAPL\n",
            b"ticker,shares\nAAPL,2,overflow\n",
        )
        for payload in invalid_bytes:
            with self.subTest(payload=payload):
                self.source_file.write_bytes(payload)
                self.destination.write_text("old", encoding="utf-8")
                with self.assertRaises(automatic_sync.AutomaticPortfolioSyncError):
                    self._process()
                self.assertEqual(self.destination.read_text(encoding="utf-8"), "old")
                self.assertEqual(self._stage_files(), [])
                self.runner.assert_not_called()

    def test_staged_nonblank_row_with_missing_trailing_cells_fails_closed(self):
        self.destination.write_text("old", encoding="utf-8")
        self.source_file.write_text(
            "ticker,shares,average_cost,average_cost_currency,account_type\nAAPL,2,100,USD\n",
            encoding="utf-8",
        )

        with self.assertRaisesRegex(automatic_sync.AutomaticPortfolioSyncError, "largeur de ligne invalide"):
            self._process()

        self.assertEqual(self.destination.read_text(encoding="utf-8"), "old")
        self.runner.assert_not_called()
        self.assertEqual(self._stage_files(), [])

    def test_validation_exception_fails_closed(self):
        self.destination.write_text("old", encoding="utf-8")
        with patch.object(automatic_sync, "validate_portfolio_file", side_effect=RuntimeError("validator boom")):
            with self.assertRaisesRegex(automatic_sync.AutomaticPortfolioSyncError, "validation portfolio impossible"):
                self._process()

        self.assertEqual(self.destination.read_text(encoding="utf-8"), "old")
        self.runner.assert_not_called()

    def test_destination_symlink_is_refused(self):
        target = self.project / "elsewhere.csv"
        target.write_text("old", encoding="utf-8")
        self.destination.symlink_to(target)

        with self.assertRaisesRegex(automatic_sync.AutomaticPortfolioSyncError, "symbolique"):
            self._process()

        self.assertEqual(target.read_text(encoding="utf-8"), "old")
        self.runner.assert_not_called()

    def test_promotion_failure_preserves_live_portfolio_marker_and_cleans_stage(self):
        self.destination.write_text("old", encoding="utf-8")
        old_marker = self._write_marker(source_hash="0" * 64)

        with patch.object(automatic_sync.os, "replace", side_effect=OSError("promotion failed")):
            with self.assertRaisesRegex(OSError, "promotion failed"):
                self._process()

        self.assertEqual(self.destination.read_text(encoding="utf-8"), "old")
        self.assertEqual(json.loads(self.state_file.read_text(encoding="utf-8")), old_marker)
        self.assertEqual(self._stage_files(), [])
        self.runner.assert_not_called()

    def test_destination_directory_fsync_failure_skips_sync_and_retry_reconciles(self):
        old_marker = self._write_marker(source_hash="0" * 64)
        real_fsync_directory = automatic_sync._fsync_directory

        def fail_data_directory(path: Path) -> None:
            if path == self.project.resolve() / "data":
                raise OSError("data directory fsync failed")
            real_fsync_directory(path)

        with patch.object(automatic_sync, "_fsync_directory", side_effect=fail_data_directory):
            with self.assertRaisesRegex(OSError, "data directory fsync failed"):
                self._process()

        self.assertEqual(self.destination.read_bytes(), self.source_file.read_bytes())
        self.assertEqual(json.loads(self.state_file.read_text(encoding="utf-8")), old_marker)
        self.runner.assert_not_called()

        retry = self._process()
        self.assertTrue(retry.processed)
        self.runner.assert_called_once()

    def test_formatting_only_source_change_causes_one_reconciliation(self):
        self._process()
        self.source_file.write_text(VALID_PORTFOLIO + "\n", encoding="utf-8")

        changed = self._process()
        unchanged = self._process()

        self.assertTrue(changed.processed)
        self.assertFalse(unchanged.processed)
        self.assertEqual(self.runner.call_count, 2)

    def test_same_hash_with_changed_canonical_source_path_reconciles_and_updates_path(self):
        original_source = self.source_file
        self._write_marker(source=original_source)
        second_root = self._make_source("second-source", original_source.read_text(encoding="utf-8"))
        second_source = (second_root / "data" / "portfolio.csv").resolve()

        result = self._process(explicit_source=second_root)

        self.assertTrue(result.processed)
        self.runner.assert_called_once()
        marker = json.loads(self.state_file.read_text(encoding="utf-8"))
        self.assertEqual(marker["processed_source_sha256"], self._hash(second_source))
        self.assertEqual(marker["source_path"], str(second_source))

    def test_missing_command_environment_fails_before_live_promotion(self):
        self.destination.write_text("old", encoding="utf-8")
        python = self.project / ".venv" / "bin" / "python"
        main_file = self.project / "main.py"

        for missing in (python, main_file):
            with self.subTest(missing=missing):
                original = missing.read_bytes()
                mode = missing.stat().st_mode
                missing.unlink()
                with self.assertRaises(automatic_sync.AutomaticPortfolioSyncError):
                    self._process()
                self.assertEqual(self.destination.read_text(encoding="utf-8"), "old")
                missing.parent.mkdir(parents=True, exist_ok=True)
                missing.write_bytes(original)
                os.chmod(missing, mode)

        self.runner.assert_not_called()

    def test_stage_files_are_cleaned_after_promotion_and_validation_failures(self):
        self._process()
        self.assertEqual(self._stage_files(), [])

        self.source_file.write_text("ticker,shares\nAAPL,-1\n", encoding="utf-8")
        with self.assertRaises(automatic_sync.AutomaticPortfolioSyncError):
            self._process()
        self.assertEqual(self._stage_files(), [])


if __name__ == "__main__":
    unittest.main()
