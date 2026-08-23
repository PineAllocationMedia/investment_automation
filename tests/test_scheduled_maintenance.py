from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "scripts" / "run_scheduled_maintenance.py"
SPEC = importlib.util.spec_from_file_location("run_scheduled_maintenance", MODULE_PATH)
scheduled_maintenance = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(scheduled_maintenance)


class _Result:
    def __init__(self, returncode: int = 0):
        self.returncode = returncode


class ScheduledMaintenanceTest(unittest.TestCase):
    def test_full_audit_due_supersedes_model_audit(self):
        commands, _, _ = scheduled_maintenance.due_audit_commands(
            reports_dir=Path("reports"), mode="high-cagr",
            full_signal_reader=lambda *_: {"status": "FULL_AUDIT_STALE"},
            model_signal_reader=lambda *_: {"status": "MODEL_AUDIT_STALE"},
        )
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0][1], "full-audit")
        self.assertIn("--refresh-market-data", commands[0])

    def test_model_audit_runs_when_full_audit_is_healthy(self):
        commands, _, _ = scheduled_maintenance.due_audit_commands(
            reports_dir=Path("reports"), mode="high-cagr",
            full_signal_reader=lambda *_: {"status": "FULL_AUDIT_HEALTHY"},
            model_signal_reader=lambda *_: {"status": "MODEL_AUDIT_ABSENT"},
        )
        self.assertEqual(commands, [["main.py", "model-audit", "--period", "12m", "--mode", "high-cagr"]])

    def test_no_heavy_audit_when_both_signals_are_healthy(self):
        commands, _, _ = scheduled_maintenance.due_audit_commands(
            reports_dir=Path("reports"), mode="high-cagr",
            full_signal_reader=lambda *_: {"status": "FULL_AUDIT_HEALTHY"},
            model_signal_reader=lambda *_: {"status": "MODEL_AUDIT_HEALTHY"},
        )
        self.assertEqual(commands, [])

    def test_health_check_failure_stops_before_audits(self):
        runner = Mock(return_value=_Result(1))
        planner = Mock()
        notifier = Mock()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / ".venv" / "bin").mkdir(parents=True)
            status = scheduled_maintenance.run_maintenance(
                project_root=root, mode="high-cagr", repair_safe=True,
                config_path=root / "telegram.env", command_runner=runner,
                audit_planner=planner, notifier=notifier,
            )
        self.assertEqual(status, 1)
        planner.assert_not_called()
        self.assertEqual(runner.call_count, 1)
        self.assertIn("health-check", runner.call_args.args[0])
        self.assertIn("--repair-safe", runner.call_args.args[0])
        self.assertIn("--skip-portfolio-repair", runner.call_args.args[0])
        notifier.assert_called_once()

    def test_healthy_maintenance_without_due_audit_only_runs_health_check(self):
        runner = Mock(return_value=_Result(0))
        notifier = Mock()
        planner = Mock(return_value=([], {"status": "FULL_AUDIT_HEALTHY"}, {"status": "MODEL_AUDIT_HEALTHY"}))
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / ".venv" / "bin").mkdir(parents=True)
            status = scheduled_maintenance.run_maintenance(
                project_root=root, mode="high-cagr", repair_safe=False,
                config_path=root / "telegram.env", command_runner=runner,
                audit_planner=planner, notifier=notifier,
            )
        self.assertEqual(status, 0)
        self.assertEqual(runner.call_count, 1)
        self.assertNotIn("--repair-safe", runner.call_args.args[0])
        notifier.assert_called_once()

    def test_due_model_audit_runs_after_health_check_and_sends_report(self):
        runner = Mock(side_effect=[_Result(0), _Result(0)])
        notifier = Mock()
        planner = Mock(return_value=(
            [["main.py", "model-audit", "--period", "12m", "--mode", "high-cagr"]],
            {"status": "FULL_AUDIT_HEALTHY"},
            {"status": "MODEL_AUDIT_STALE"},
        ))
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / ".venv" / "bin").mkdir(parents=True)
            status = scheduled_maintenance.run_maintenance(
                project_root=root, mode="high-cagr", repair_safe=True,
                config_path=root / "telegram.env", command_runner=runner,
                audit_planner=planner, notifier=notifier,
            )

        self.assertEqual(status, 0)
        self.assertEqual(runner.call_count, 2)
        self.assertEqual(
            runner.call_args_list[1].args[0],
            [
                str(root / ".venv" / "bin" / "python"),
                "main.py", "model-audit", "--period", "12m", "--mode", "high-cagr",
            ],
        )
        self.assertEqual(notifier.call_args.args[2], root / "reports" / "latest_model_audit.html")

    def test_configured_sync_runs_before_health_check(self):
        runner = Mock(side_effect=[_Result(0), _Result(0), _Result(0)])
        notifier = Mock()
        planner = Mock(return_value=([], {"status": "FULL_AUDIT_HEALTHY"}, {"status": "MODEL_AUDIT_HEALTHY"}))
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / ".venv" / "bin").mkdir(parents=True)
            config = root / "input_sync.env"
            config.write_text("INVESTMENT_AUTOMATION_INPUT_SOURCE=/drive\n", encoding="utf-8")
            status = scheduled_maintenance.run_maintenance(
                project_root=root,
                mode="high-cagr",
                repair_safe=False,
                config_path=root / "telegram.env",
                input_sync_config_path=config,
                command_runner=runner,
                audit_planner=planner,
                notifier=notifier,
            )

        self.assertEqual(status, 0)
        self.assertIn("run_automatic_portfolio_sync.py", runner.call_args_list[0].args[0][1])
        self.assertIn("sync_operational_inputs.py", runner.call_args_list[1].args[0][1])
        self.assertIn("--skip-portfolio", runner.call_args_list[1].args[0])
        self.assertIn("health-check", runner.call_args_list[2].args[0])

    def test_sync_failure_stops_maintenance(self):
        runner = Mock(side_effect=[_Result(0), _Result(6)])
        notifier = Mock()
        planner = Mock()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / ".venv" / "bin").mkdir(parents=True)
            config = root / "input_sync.env"
            config.write_text("INVESTMENT_AUTOMATION_INPUT_SOURCE=/drive\n", encoding="utf-8")
            with patch.dict("os.environ", {}, clear=True):
                status = scheduled_maintenance.run_maintenance(
                    project_root=root,
                    mode="high-cagr",
                    repair_safe=True,
                    config_path=root / "telegram.env",
                    input_sync_config_path=config,
                    command_runner=runner,
                    audit_planner=planner,
                    notifier=notifier,
                )

        self.assertEqual(status, 6)
        self.assertEqual(runner.call_count, 2)
        self.assertIn("run_automatic_portfolio_sync.py", runner.call_args_list[0].args[0][1])
        self.assertIn("sync_operational_inputs.py", runner.call_args_list[1].args[0][1])
        planner.assert_not_called()
        notifier.assert_called_once()

    def test_reconciliation_failure_stops_before_sync_health_and_audits(self):
        runner = Mock(return_value=_Result(7))
        notifier = Mock()
        planner = Mock()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / ".venv" / "bin").mkdir(parents=True)
            config = root / "input_sync.env"
            config.write_text("INVESTMENT_AUTOMATION_INPUT_SOURCE=/drive\n", encoding="utf-8")

            status = scheduled_maintenance.run_maintenance(
                project_root=root,
                mode="high-cagr",
                repair_safe=True,
                config_path=root / "telegram.env",
                require_portfolio_sync=True,
                input_sync_config_path=config,
                command_runner=runner,
                audit_planner=planner,
                notifier=notifier,
            )

        self.assertEqual(status, 7)
        self.assertEqual(runner.call_count, 1)
        self.assertIn("run_automatic_portfolio_sync.py", runner.call_args.args[0][1])
        planner.assert_not_called()
        notifier.assert_called_once()

    def test_strict_maintenance_without_source_fails_closed(self):
        runner = Mock()
        notifier = Mock()
        planner = Mock()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / ".venv" / "bin").mkdir(parents=True)
            status = scheduled_maintenance.run_maintenance(
                project_root=root,
                mode="high-cagr",
                repair_safe=True,
                config_path=root / "telegram.env",
                require_portfolio_sync=True,
                input_sync_config_path=root / "missing.env",
                command_runner=runner,
                audit_planner=planner,
                notifier=notifier,
            )

        self.assertEqual(status, 5)
        runner.assert_not_called()
        planner.assert_not_called()
        notifier.assert_called_once()


if __name__ == "__main__":
    unittest.main()
