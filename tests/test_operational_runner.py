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
    def _project(
        self,
        root: Path,
        *,
        validation_status: int = 0,
        sync_status: int = 0,
        analysis_status: int = 0,
        walk_forward_status: int = 0,
        report_state: str = "present",
    ) -> dict[str, str]:
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
                    if (({analysis_status} != 0)); then
                        exit {analysis_status}
                    fi
                    mode=""
                    previous=""
                    for argument in "$@"; do
                        if [[ "$previous" == "--mode" ]]; then
                            mode="$argument"
                            break
                        fi
                        previous="$argument"
                    done
                    mkdir -p reports
                    report="reports/latest_report_compact_${{mode//-/_}}.md"
                    if [[ "{report_state}" == "present" ]]; then
                        printf 'SCORE_STABILITY_STABLE\\n' >"$report"
                    elif [[ "{report_state}" == "empty" ]]; then
                        : >"$report"
                    fi
                fi
                if [[ "$2" == "walk-forward-backtest" ]]; then
                    exit {walk_forward_status}
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

    def _run(
        self, env: dict[str, str], *arguments: str
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(RUNNER), *arguments],
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
            self.assertEqual(
                calls,
                [
                    "main.py validate-inputs",
                    "main.py analyze --capital 0 --mode high-cagr",
                    "main.py walk-forward-backtest --mode high-cagr",
                ],
            )
            self.assertIn("Score stability: SCORE_STABILITY_STABLE", result.stdout)
            self.assertEqual(len(list((root / "logs").glob("analysis_*.log"))), 1)

    def test_walk_forward_uses_current_mode_without_refresh(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            env = self._project(root)

            result = self._run(
                env, "--mode", "balanced", "--refresh-market-data"
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            calls = (root / "calls.txt").read_text(encoding="utf-8").splitlines()
            self.assertEqual(
                calls,
                [
                    "main.py validate-inputs",
                    "main.py analyze --capital 0 --mode balanced --refresh-market-data",
                    "main.py walk-forward-backtest --mode balanced",
                ],
            )

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

    def test_analysis_failure_stops_before_walk_forward(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            env = self._project(root, analysis_status=7)

            result = self._run(env)

            self.assertEqual(result.returncode, 7)
            calls = (root / "calls.txt").read_text(encoding="utf-8").splitlines()
            self.assertEqual(
                calls,
                [
                    "main.py validate-inputs",
                    "main.py analyze --capital 0 --mode high-cagr",
                ],
            )

    def test_missing_or_empty_report_stops_before_walk_forward(self):
        for report_state in ("missing", "empty"):
            with (
                self.subTest(report_state=report_state),
                tempfile.TemporaryDirectory() as directory,
            ):
                root = Path(directory)
                env = self._project(root, report_state=report_state)

                result = self._run(env)

                self.assertEqual(result.returncode, 3)
                calls = (root / "calls.txt").read_text(encoding="utf-8").splitlines()
                self.assertEqual(
                    calls,
                    [
                        "main.py validate-inputs",
                        "main.py analyze --capital 0 --mode high-cagr",
                    ],
                )

    def test_walk_forward_failure_does_not_fail_successful_analysis(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            env = self._project(root, walk_forward_status=6)
            compact_html_report = (
                root / "reports" / "latest_report_compact_high_cagr.html"
            )
            compact_html_report.write_text("<p>report</p>\n", encoding="utf-8")
            notifications = root / "notifications.txt"
            notifier = root / "telegram_capture.py"
            notifier.write_text(
                textwrap.dedent(
                    """\
                    import os
                    import sys

                    path = os.environ["INVESTMENT_AUTOMATION_TEST_NOTIFICATIONS"]
                    with open(path, "a", encoding="utf-8") as handle:
                        handle.write(" ".join(sys.argv[1:]) + "\\n")
                    """
                ),
                encoding="utf-8",
            )
            env["INVESTMENT_AUTOMATION_TELEGRAM_NOTIFIER"] = str(notifier)
            env["INVESTMENT_AUTOMATION_TEST_NOTIFICATIONS"] = str(notifications)

            result = self._run(env)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("walk-forward echoue avec le statut 6", result.stdout)
            final_notification = notifications.read_text(encoding="utf-8").splitlines()[-1]
            self.assertIn("SUCCÈS analyse high-cagr", final_notification)
            self.assertIn("walk-forward échoué (statut 6)", final_notification)
            self.assertIn(f"--document {compact_html_report}", final_notification)

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
