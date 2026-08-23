from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "scripts" / "install_systemd_automation.py"
SPEC = importlib.util.spec_from_file_location("install_systemd_automation", MODULE_PATH)
systemd_automation = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(systemd_automation)


class SystemdAutomationTest(unittest.TestCase):
    def test_analysis_timer_uses_confirmed_schedule_and_catch_up(self):
        rendered = systemd_automation.render_units(PROJECT_ROOT)
        timer = rendered["investment-automation-analysis.timer"]
        service = rendered["investment-automation-analysis.service"]
        self.assertIn("OnCalendar=*-*-01,15 16:45:00 America/Toronto", timer)
        self.assertIn("Persistent=true", timer)
        self.assertIn("--timeout-seconds 43200", service)
        self.assertIn("--refresh-market-data", service)
        self.assertIn("INVESTMENT_AUTOMATION_REQUIRE_PORTFOLIO_SYNC=1", service)
        self.assertNotIn("@PROJECT_ROOT@", service)

    def test_maintenance_timer_is_weekly_and_persistent(self):
        rendered = systemd_automation.render_units(PROJECT_ROOT)
        timer = rendered["investment-automation-maintenance.timer"]
        service = rendered["investment-automation-maintenance.service"]
        self.assertIn("OnCalendar=Sun *-*-* 09:00:00 America/Toronto", timer)
        self.assertIn("Persistent=true", timer)
        self.assertIn("run_scheduled_maintenance.py --mode high-cagr --repair-safe", service)
        self.assertIn("--require-portfolio-sync", service)
        self.assertIn("/usr/bin/flock --exclusive --verbose", service)
        self.assertNotIn("--nonblock", service)

    def test_portfolio_timer_and_service_are_hourly_persistent_and_narrow(self):
        rendered = systemd_automation.render_units(PROJECT_ROOT)
        timer = rendered["investment-automation-portfolio-sync.timer"]
        service = rendered["investment-automation-portfolio-sync.service"]
        self.assertIn("OnCalendar=*-*-* *:15:00 America/Toronto", timer)
        self.assertIn("Persistent=true", timer)
        self.assertIn("AccuracySec=1min", timer)
        self.assertNotIn("RandomizedDelaySec", timer)
        self.assertIn("run_automatic_portfolio_sync.py", service)
        self.assertIn("operations.lock", service)
        self.assertIn("--exclusive --nonblock --conflict-exit-code=75 --verbose", service)
        self.assertIn("SuccessExitStatus=75", service)
        self.assertIn("TimeoutStartSec=1h", service)
        self.assertLess(service.index("/usr/bin/flock"), service.index("run_automatic_portfolio_sync.py"))
        self.assertEqual(service.count("ExecStart="), 1)
        self.assertNotIn("sync_operational_inputs.py", service)
        self.assertNotIn("--refresh-market-data", service)
        self.assertNotIn("telegram", service.casefold())

    def test_no_scheduled_service_updates_git_automatically(self):
        rendered = systemd_automation.render_units(PROJECT_ROOT)
        for name in (
            "investment-automation-analysis.service",
            "investment-automation-maintenance.service",
            "investment-automation-portfolio-sync.service",
        ):
            with self.subTest(name=name):
                service = rendered[name]
                self.assertNotIn("update_deployment_code.py", service)
                self.assertNotIn("git pull", service)

    def test_all_automatic_operations_use_same_operations_lock(self):
        rendered = systemd_automation.render_units(PROJECT_ROOT)
        maintenance = rendered["investment-automation-maintenance.service"]
        portfolio = rendered["investment-automation-portfolio-sync.service"]
        runner = (PROJECT_ROOT / "scripts" / "run_investment_analysis.sh").read_text(encoding="utf-8")
        self.assertIn(".local/state/investment_automation/operations.lock", maintenance)
        self.assertIn(".local/state/investment_automation/operations.lock", portfolio)
        self.assertIn(".local/state/investment_automation/operations.lock", runner)
        self.assertNotIn("analyze.lock", runner)
        self.assertNotIn("/pid", runner)

    def test_install_writes_only_expected_units_and_activates_timers(self):
        runner = Mock()
        with tempfile.TemporaryDirectory() as temp_dir:
            unit_dir = Path(temp_dir)
            systemd_automation.install_units(
                project_root=PROJECT_ROOT,
                unit_dir=unit_dir,
                start_timers=True,
                command_runner=runner,
            )
            self.assertEqual(sorted(path.name for path in unit_dir.iterdir()), sorted(systemd_automation.UNIT_NAMES))
        self.assertEqual(runner.call_count, 2)
        runner.assert_any_call(["systemctl", "--user", "daemon-reload"], check=True)
        runner.assert_any_call(
            ["systemctl", "--user", "enable", "--now", *systemd_automation.HISTORICAL_TIMER_NAMES],
            check=True,
        )
        self.assertFalse(
            any(systemd_automation.PORTFOLIO_TIMER_NAME in call.args[0] for call in runner.call_args_list)
        )

    def test_explicit_opt_in_enables_portfolio_timer(self):
        runner = Mock()
        with tempfile.TemporaryDirectory() as temp_dir:
            systemd_automation.install_units(
                project_root=PROJECT_ROOT,
                unit_dir=Path(temp_dir),
                start_timers=True,
                enable_portfolio_sync=True,
                command_runner=runner,
            )
        runner.assert_any_call(
            ["systemctl", "--user", "enable", "--now", systemd_automation.PORTFOLIO_TIMER_NAME],
            check=True,
        )

    def test_no_start_issues_no_enable_or_start_actions(self):
        runner = Mock()
        with tempfile.TemporaryDirectory() as temp_dir:
            systemd_automation.install_units(
                project_root=PROJECT_ROOT,
                unit_dir=Path(temp_dir),
                start_timers=False,
                enable_portfolio_sync=True,
                command_runner=runner,
            )
        runner.assert_called_once_with(["systemctl", "--user", "daemon-reload"], check=True)

    def test_reinstall_without_opt_in_preserves_an_already_enabled_portfolio_timer(self):
        runner = Mock()
        with tempfile.TemporaryDirectory() as temp_dir:
            unit_dir = Path(temp_dir)
            systemd_automation.install_units(
                project_root=PROJECT_ROOT,
                unit_dir=unit_dir,
                start_timers=True,
                enable_portfolio_sync=True,
                command_runner=runner,
            )
            first_render = {
                name: (unit_dir / name).read_text(encoding="utf-8")
                for name in systemd_automation.UNIT_NAMES
            }
            runner.reset_mock()

            systemd_automation.install_units(
                project_root=PROJECT_ROOT,
                unit_dir=unit_dir,
                start_timers=True,
                enable_portfolio_sync=False,
                command_runner=runner,
            )

            second_render = {
                name: (unit_dir / name).read_text(encoding="utf-8")
                for name in systemd_automation.UNIT_NAMES
            }

        self.assertEqual(first_render, second_render)
        self.assertFalse(any("disable" in call.args[0] for call in runner.call_args_list))
        self.assertFalse(
            any(systemd_automation.PORTFOLIO_TIMER_NAME in call.args[0] for call in runner.call_args_list)
        )

    def test_repeated_rendering_is_identical_and_manages_exactly_six_units(self):
        first = systemd_automation.render_units(PROJECT_ROOT)
        second = systemd_automation.render_units(PROJECT_ROOT)
        self.assertEqual(first, second)
        self.assertEqual(set(first), set(systemd_automation.UNIT_NAMES))
        self.assertEqual(len(first), 6)


if __name__ == "__main__":
    unittest.main()
