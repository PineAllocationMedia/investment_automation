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
        self.assertIn("ExecStartPre=", service)
        self.assertIn("update_deployment_code.py", service)
        self.assertNotIn("@PROJECT_ROOT@", service)

    def test_maintenance_timer_is_weekly_and_persistent(self):
        rendered = systemd_automation.render_units(PROJECT_ROOT)
        timer = rendered["investment-automation-maintenance.timer"]
        service = rendered["investment-automation-maintenance.service"]
        self.assertIn("OnCalendar=Sun *-*-* 09:00:00 America/Toronto", timer)
        self.assertIn("Persistent=true", timer)
        self.assertIn("run_scheduled_maintenance.py --mode high-cagr --repair-safe", service)
        self.assertIn("update_deployment_code.py", service)

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
            ["systemctl", "--user", "enable", "--now", *systemd_automation.TIMER_NAMES], check=True
        )


if __name__ == "__main__":
    unittest.main()
