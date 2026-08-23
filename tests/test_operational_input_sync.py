from __future__ import annotations

from datetime import datetime
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "scripts" / "sync_operational_inputs.py"
SPEC = importlib.util.spec_from_file_location("sync_operational_inputs", MODULE_PATH)
input_sync = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(input_sync)


class _Result:
    def __init__(self, returncode: int = 0):
        self.returncode = returncode


class OperationalInputSyncTest(unittest.TestCase):
    def _source(self, root: Path) -> Path:
        source = root / "drive"
        (source / "data" / "research_reports" / "bncd_morningstar").mkdir(parents=True)
        (source / "data" / "portfolio.csv").write_text("ticker,shares\nAPH,2\n", encoding="utf-8")
        (source / "data" / "proxy_calibration.csv").write_text("ticker,source_date\nAPH,\n", encoding="utf-8")
        (source / "data" / "research_reports" / "bncd_morningstar" / "APH_report.pdf").write_bytes(
            b"%PDF-1.7\ntest"
        )
        return source

    def _project(self, root: Path) -> Path:
        project = root / "project"
        (project / ".venv" / "bin").mkdir(parents=True)
        (project / ".venv" / "bin" / "python").write_text("", encoding="utf-8")
        (project / "main.py").write_text("", encoding="utf-8")
        return project

    def test_sync_copies_whitelist_and_runs_manual_sync(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._source(root)
            project = self._project(root)
            runner = Mock(return_value=_Result())

            result = input_sync.sync_inputs(
                source_root=source,
                project_root=project,
                backup_root=root / "backups",
                command_runner=runner,
            )

            self.assertEqual(len(result.copied), 3)
            self.assertIsNone(result.backup_directory)
            self.assertEqual((project / "data" / "portfolio.csv").read_text(), "ticker,shares\nAPH,2\n")
            self.assertTrue(
                (project / "data" / "research_reports" / "bncd_morningstar" / "APH_report.pdf").is_file()
            )
            runner.assert_called_once_with(
                [str(project / ".venv" / "bin" / "python"), "main.py", "sync-manual-inputs"],
                cwd=project,
                check=False,
            )

    def test_overwrite_creates_backup_and_missing_source_pdf_does_not_delete_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._source(root)
            project = self._project(root)
            destination_data = project / "data"
            destination_reports = destination_data / "research_reports" / "bncd_morningstar"
            destination_reports.mkdir(parents=True)
            (destination_data / "portfolio.csv").write_text("old portfolio", encoding="utf-8")
            (destination_data / "proxy_calibration.csv").write_text(
                (source / "data" / "proxy_calibration.csv").read_text(), encoding="utf-8"
            )
            retained_pdf = destination_reports / "older_report.pdf"
            retained_pdf.write_bytes(b"%PDF-1.4\nolder")

            result = input_sync.sync_inputs(
                source_root=source,
                project_root=project,
                backup_root=root / "backups",
                now=datetime(2026, 8, 16, 18, 30),
            )

            self.assertEqual(
                (result.backup_directory / "data" / "portfolio.csv").read_text(encoding="utf-8"),
                "old portfolio",
            )
            self.assertTrue(retained_pdf.is_file())
            self.assertFalse(result.proxy_calibration_changed)

    def test_unchanged_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._source(root)
            project = self._project(root)
            runner = Mock(return_value=_Result())
            input_sync.sync_inputs(
                source_root=source, project_root=project, backup_root=root / "backups", command_runner=runner
            )
            runner.reset_mock()

            result = input_sync.sync_inputs(
                source_root=source, project_root=project, backup_root=root / "backups", command_runner=runner
            )

            self.assertEqual(result.copied, ())
            self.assertEqual(len(result.unchanged), 3)
            self.assertIsNone(result.backup_directory)
            runner.assert_not_called()

    def test_skip_portfolio_syncs_proxy_and_pdfs_without_reading_portfolio(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._source(root)
            project = self._project(root)
            (source / "data" / "portfolio.csv").unlink()
            local_portfolio = project / "data" / "portfolio.csv"
            local_portfolio.parent.mkdir(parents=True)
            local_portfolio.write_text("local portfolio must remain untouched\n", encoding="utf-8")
            runner = Mock(return_value=_Result())

            result = input_sync.sync_inputs(
                source_root=source,
                project_root=project,
                backup_root=root / "backups",
                skip_portfolio=True,
                command_runner=runner,
            )

            self.assertEqual(
                result.copied,
                (
                    Path("data/proxy_calibration.csv"),
                    Path("data/research_reports/bncd_morningstar/APH_report.pdf"),
                ),
            )
            self.assertEqual(local_portfolio.read_text(encoding="utf-8"), "local portfolio must remain untouched\n")
            self.assertTrue((project / "data" / "proxy_calibration.csv").is_file())
            self.assertTrue(
                (project / "data" / "research_reports" / "bncd_morningstar" / "APH_report.pdf").is_file()
            )
            runner.assert_called_once()

    def test_invalid_pdf_fails_before_any_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._source(root)
            project = self._project(root)
            report = source / "data" / "research_reports" / "bncd_morningstar" / "APH_report.pdf"
            report.write_text("not a pdf", encoding="utf-8")

            with self.assertRaises(input_sync.InputSyncError):
                input_sync.sync_inputs(source_root=source, project_root=project, backup_root=root / "backups")

            self.assertFalse((project / "data" / "portfolio.csv").exists())

    def test_manual_sync_failure_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._source(root)
            project = self._project(root)

            with self.assertRaisesRegex(input_sync.InputSyncError, "sync-manual-inputs"):
                input_sync.sync_inputs(
                    source_root=source,
                    project_root=project,
                    backup_root=root / "backups",
                    command_runner=Mock(return_value=_Result(9)),
                )

    def test_symbolic_source_file_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._source(root)
            project = self._project(root)
            portfolio = source / "data" / "portfolio.csv"
            real_file = source / "portfolio-real.csv"
            portfolio.replace(real_file)
            portfolio.symlink_to(real_file)

            with self.assertRaises(input_sync.InputSyncError):
                input_sync.sync_inputs(source_root=source, project_root=project, backup_root=root / "backups")

    def test_configuration_prefers_explicit_then_environment_then_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "input_sync.env"
            config.write_text("INVESTMENT_AUTOMATION_INPUT_SOURCE=/from/config\n", encoding="utf-8")
            self.assertEqual(
                input_sync.configured_source(
                    explicit_source=Path("/explicit"), config_path=config, environ={"INVESTMENT_AUTOMATION_INPUT_SOURCE": "/env"}
                ),
                Path("/explicit"),
            )
            self.assertEqual(
                input_sync.configured_source(
                    explicit_source=None, config_path=config, environ={"INVESTMENT_AUTOMATION_INPUT_SOURCE": "/env"}
                ),
                Path("/env"),
            )
            self.assertEqual(
                input_sync.configured_source(explicit_source=None, config_path=config, environ={}),
                Path("/from/config"),
            )


if __name__ == "__main__":
    unittest.main()
