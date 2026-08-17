import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNNER = PROJECT_ROOT / "scripts" / "run_investment_analysis.sh"


class OperationalRunnerTest(unittest.TestCase):
    def _project(self, root: Path, *, validation_status: int = 0, sync_status: int = 0) -> dict[str, str]:
        (root / ".venv" / "bin").mkdir(parents=True)
        (root / "reports").mkdir()
        (root / "main.py").write_text("# test fixture\n", encoding="utf-8")
        fake_python = root / ".venv" / "bin" / "python"
        fake_python.write_text(
            textwrap.dedent(
                f"""\
                #!/usr/bin/env bash
                echo "$*" >>"$INVESTMENT_AUTOMATION_TEST_CALLS"
                if [[ "$1" == *"sync_operational_inputs.py" ]]; then
                    exit {sync_status}
                fi
                if [[ "$2" == "validate-inputs" ]]; then
                    exit {validation_status}
                fi
                if [[ "$2" == "analyze" ]]; then
                    mkdir -p reports
                    printf 'SCORE_STABILITY_STABLE\\n' >reports/latest_report_compact_high_cagr.md
                fi
                """
            ),
            encoding="utf-8",
        )
        fake_python.chmod(0o755)
        calls = root / "calls.txt"
        return {
            **os.environ,
            "INVESTMENT_AUTOMATION_PROJECT_ROOT": str(root),
            "INVESTMENT_AUTOMATION_LOG_DIR": str(root / "logs"),
            "INVESTMENT_AUTOMATION_LOCK_DIR": str(root / "state" / "analyze.lock"),
            "INVESTMENT_AUTOMATION_TEST_CALLS": str(calls),
            "INVESTMENT_AUTOMATION_TELEGRAM_CONFIG": str(root / "telegram-disabled.env"),
            "INVESTMENT_AUTOMATION_TELEGRAM_PYTHON": sys.executable,
        }

    def _run(self, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(RUNNER)],
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )

    def test_success_validates_then_generates_report_and_log(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            env = self._project(root)

            result = self._run(env)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            calls = (root / "calls.txt").read_text(encoding="utf-8").splitlines()
            self.assertEqual(calls[0], "main.py validate-inputs")
            self.assertIn("main.py analyze --capital 0 --mode high-cagr", calls[1])
            self.assertIn("Score stability: SCORE_STABILITY_STABLE", result.stdout)
            self.assertEqual(len(list((root / "logs").glob("analysis_*.log"))), 1)

    def test_telegram_failure_does_not_fail_successful_analysis(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            env = self._project(root)
            notifier = root / "telegram_failure.py"
            notifier.write_text("raise SystemExit(9)\n", encoding="utf-8")
            env["INVESTMENT_AUTOMATION_TELEGRAM_NOTIFIER"] = str(notifier)

            result = self._run(env)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("notification Telegram non livrée", result.stdout)

    def test_live_lock_prevents_a_second_run(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            env = self._project(root)
            lock_dir = Path(env["INVESTMENT_AUTOMATION_LOCK_DIR"])
            lock_dir.mkdir(parents=True)
            (lock_dir / "pid").write_text(str(os.getpid()), encoding="utf-8")

            result = self._run(env)

            self.assertEqual(result.returncode, 75)
            self.assertIn("Analyse deja en cours", result.stderr)
            self.assertFalse((root / "calls.txt").exists())

    def test_validation_failure_stops_before_analysis(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            env = self._project(root, validation_status=9)

            result = self._run(env)

            self.assertEqual(result.returncode, 2)
            calls = (root / "calls.txt").read_text(encoding="utf-8").splitlines()
            self.assertEqual(calls, ["main.py validate-inputs"])
            self.assertIn("Analyse annulee", result.stdout)

    def test_configured_input_sync_runs_before_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            env = self._project(root)
            config = root / "input_sync.env"
            config.write_text("INVESTMENT_AUTOMATION_INPUT_SOURCE=/drive\n", encoding="utf-8")
            env["INVESTMENT_AUTOMATION_INPUT_SYNC_CONFIG"] = str(config)

            result = self._run(env)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            calls = (root / "calls.txt").read_text(encoding="utf-8").splitlines()
            self.assertIn("sync_operational_inputs.py", calls[0])
            self.assertEqual(calls[1], "main.py validate-inputs")
            self.assertIn("main.py analyze", calls[2])

    def test_input_sync_failure_stops_before_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            env = self._project(root, sync_status=8)
            config = root / "input_sync.env"
            config.write_text("INVESTMENT_AUTOMATION_INPUT_SOURCE=/drive\n", encoding="utf-8")
            env["INVESTMENT_AUTOMATION_INPUT_SYNC_CONFIG"] = str(config)

            result = self._run(env)

            self.assertEqual(result.returncode, 4)
            calls = (root / "calls.txt").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(calls), 1)
            self.assertIn("sync_operational_inputs.py", calls[0])


if __name__ == "__main__":
    unittest.main()
