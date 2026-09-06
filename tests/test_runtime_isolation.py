"""Subprocess regressions: the runtime profile is fixed before application imports."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest

from src.runtime_context import CODE_ROOT, RuntimeIsolationError, resolve_runtime

NO_NETWORK = '''
import sys
def deny_network(event, args):
    if event in {"socket.connect", "socket.getaddrinfo"}:
        raise AssertionError("Network is disabled in runtime isolation tests")
sys.addaudithook(deny_network)
'''

# In-memory unit fixture only: never call run_analysis or write observations.
EQUIVALENCE = '''
import json
from tests.helpers import full_strong_analysis
from src.allocation_engine import allocate_capital
from src.critical_input_engine import critical_config_fingerprint
from pathlib import Path
CODE_ROOT = Path.cwd()
from src.model_version import MODEL_RULES_VERSION
from src.baseline_identity import load_baseline_identity
rows = {ticker: full_strong_analysis(ticker) for ticker in ("MSFT", "INTU")}
rows["MSFT"].update(current_value=10000, current_value_cad=10000, shares=10, position_weight=1)
results = {mode: allocate_capital(1000, rows, mode) for mode in
           ("balanced", "family-office", "rational-aggressive", "high-cagr")}
print(json.dumps({"analyses": rows, "allocations": results,
                  "config": critical_config_fingerprint(CODE_ROOT),
                  "version": MODEL_RULES_VERSION,
                  "baseline": load_baseline_identity()}, sort_keys=True, default=str))
'''


class RuntimeIsolationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="v2-isolation-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.home = self.base / "original-home"
        self.home.mkdir()
        self.root = self.base / "runtime-a"
        self.env = {"HOME": str(self.home), "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                    "PYTHONDONTWRITEBYTECODE": "1", "LANG": "en_US.UTF-8",
                    "XDG_CACHE_HOME": str(self.home / "cache"),
                    "XDG_STATE_HOME": str(self.home / "state"),
                    "XDG_CONFIG_HOME": str(self.home / "config"), "TMPDIR": str(self.base)}

    def child(self, source, *, isolated=True, root=None, extra=None, success=True):
        env = {**self.env, **(extra or {})}
        if isolated:
            env["INVESTMENT_AUTOMATION_RUNTIME_ROOT"] = str(root or self.root)
        result = subprocess.run([sys.executable, "-B", "-c", NO_NETWORK + textwrap.dedent(source)],
                                cwd=CODE_ROOT, env=env, capture_output=True, text=True, timeout=90)
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_default_paths_and_explicit_v1_fixture_roots(self):
        self.child(r'''
            from pathlib import Path
            from src.runtime_context import RUNTIME, CODE_ROOT, state_root
            from src.utils import PROJECT_ROOT, CONFIG_DIR, DATA_DIR, REPORTS_DIR, CACHE_DIR
            from src.csv_schema_engine import csv_schema_specs
            from src.model_tuning import MODEL_TUNING_HISTORY_PATH, MODEL_TUNING_PATH
            assert not RUNTIME.restricted
            assert PROJECT_ROOT == CODE_ROOT == RUNTIME.root
            assert CONFIG_DIR == CODE_ROOT / "config"
            assert DATA_DIR == CODE_ROOT / "data"
            assert REPORTS_DIR == CODE_ROOT / "reports"
            assert CACHE_DIR == CODE_ROOT / "data/cached_market_data"
            assert MODEL_TUNING_PATH == CONFIG_DIR / "model_tuning.yaml"
            assert MODEL_TUNING_HISTORY_PATH == DATA_DIR / "model_tuning_history.csv"
            assert csv_schema_specs("fixture")[0].path == Path("fixture/data/portfolio.csv")
            assert state_root("fixture") == Path("fixture")
        ''', isolated=False)
        self.assertFalse(self.root.exists())

    def test_initialization_is_read_only_and_config_stays_in_code_tree(self):
        files = [p for name in ("src", "config", "scripts") for p in (CODE_ROOT / name).rglob("*")
                 if p.is_file() and "__pycache__" not in p.parts]
        before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
        self.child(r'''
            from src.utils import CONFIG_DIR, DATA_DIR, REPORTS_DIR, PROJECT_ROOT
            from src.runtime_context import RUNTIME
            from src.csv_schema_engine import csv_schema_specs
            from src.utils import load_yaml
            assert CONFIG_DIR == PROJECT_ROOT / "config"
            assert load_yaml(CONFIG_DIR / "rules.yaml")
            assert DATA_DIR == RUNTIME.root / "data"
            assert REPORTS_DIR == RUNTIME.root / "reports"
            assert all(s.path.is_relative_to(DATA_DIR) for s in csv_schema_specs(PROJECT_ROOT))
            assert not RUNTIME.root.exists()
        ''')
        self.assertFalse(self.root.exists())
        self.assertEqual(before, {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files})

    def test_root_overlap_in_both_directions_and_distinct_prefix(self):
        production = self.base / "production"
        for root in (production, production / "child", self.base):
            with self.subTest(root=root), self.assertRaises(RuntimeIsolationError):
                resolve_runtime({**self.env, "INVESTMENT_AUTOMATION_RUNTIME_ROOT": str(root),
                                 "INVESTMENT_AUTOMATION_FORBIDDEN_ROOTS": str(production)})
        good = resolve_runtime({**self.env, "INVESTMENT_AUTOMATION_RUNTIME_ROOT": str(self.base / "production-v2"),
                                "INVESTMENT_AUTOMATION_FORBIDDEN_ROOTS": str(production)})
        self.assertTrue(good.restricted)
        self.assertFalse(production.exists())

    def test_code_and_git_common_checkout_are_forbidden(self):
        for root in (CODE_ROOT, CODE_ROOT / "runtime", CODE_ROOT.parent):
            with self.subTest(root=root), self.assertRaises(RuntimeIsolationError):
                resolve_runtime({**self.env, "INVESTMENT_AUTOMATION_RUNTIME_ROOT": str(root)})
        context = resolve_runtime({**self.env, "INVESTMENT_AUTOMATION_RUNTIME_ROOT": str(self.root)})
        for forbidden in context.forbidden_roots:
            self.assertFalse(context.root.is_relative_to(forbidden))

    def test_drive_environment_and_file_config_are_rejected_before_writes(self):
        drive = self.base / "Drive"
        for key in ("INVESTMENT_AUTOMATION_INPUT_SOURCE", "INVESTMENT_AUTOMATION_PROJECT_ROOT",
                    "INVESTMENT_AUTOMATION_FORBIDDEN_ROOTS"):
            with self.subTest(key=key):
                self.child('import src', root=drive / "runtime", extra={key: f" {drive} " if key == "INVESTMENT_AUTOMATION_INPUT_SOURCE" else str(drive)}, success=False)
                self.assertFalse(drive.exists())
        config = self.home / ".config/investment_automation/input_sync.env"
        config.parent.mkdir(parents=True)
        config.write_text(f'INVESTMENT_AUTOMATION_INPUT_SOURCE="{drive}"\n')
        self.child('import src', root=drive / "runtime", success=False)
        self.assertFalse(drive.exists())

    def test_symlink_root_and_existing_nested_escape_fail_before_creation(self):
        production = self.base / "production"
        production.mkdir()
        link = self.base / "alias"
        link.symlink_to(production, target_is_directory=True)
        self.child('import src', root=link / "runtime",
                   extra={"INVESTMENT_AUTOMATION_FORBIDDEN_ROOTS": str(production)}, success=False)
        self.assertEqual(list(production.iterdir()), [])
        self.root.mkdir()
        (self.root / "data").symlink_to(production, target_is_directory=True)
        self.child('import src', success=False)
        self.assertFalse((self.root / "home").exists())
        self.assertEqual(list(production.iterdir()), [])

    def test_hardlinks_and_traversal_are_rejected(self):
        self.root.mkdir()
        source = self.base / "external.txt"
        source.write_text("preserve")
        os.link(source, self.root / "hardlink")
        self.child('import src', success=False)
        self.assertEqual(source.read_text(), "preserve")
        (self.root / "hardlink").unlink()
        self.child(r'''
            from src.runtime_context import RUNTIME, RuntimeIsolationError
            try:
                (RUNTIME.root / ".." / "escape").write_text("bad")
            except RuntimeIsolationError:
                pass
            else:
                raise AssertionError("traversal accepted")
        ''')
        self.assertFalse((self.base / "escape").exists())

    def test_normal_home_and_xdg_provider_cache_roots_are_forbidden(self):
        for root in (self.home / ".cache/py-yfinance", self.home / "Library/Caches/py-yfinance",
                     self.home / "cache/py-yfinance", self.home / "state/investment_automation"):
            with self.subTest(root=root), self.assertRaises(RuntimeIsolationError):
                resolve_runtime({**self.env, "INVESTMENT_AUTOMATION_RUNTIME_ROOT": str(root)})
        self.assertEqual(list(self.home.iterdir()), [])

    def test_cached_python_distribution_remains_read_only_code(self):
        self.child("from src.utils import DATA_DIR; import pandas",
                   extra={"XDG_CACHE_HOME": str(Path(sys.base_prefix).parent)})
        self.assertFalse(self.root.exists())

    def test_git_linked_checkout_protects_common_project(self):
        common = self.base / "v1" / ".git"
        linked = self.base / "v2"
        gitdir = common / "worktrees" / "v2"
        gitdir.mkdir(parents=True)
        linked.mkdir()
        (linked / ".git").write_text(f"gitdir: {gitdir}\n")
        (gitdir / "commondir").write_text("../..\n")
        (gitdir / "gitdir").write_text(str(linked / ".git"))
        with self.assertRaises(RuntimeIsolationError):
            resolve_runtime({**self.env, "INVESTMENT_AUTOMATION_RUNTIME_ROOT": str(common.parent / "runtime")},
                            code_root=linked)
        self.assertFalse((common.parent / "runtime").exists())

    def test_profile_default_unknown_relative_and_conflicting_options(self):
        context = resolve_runtime({**self.env, "INVESTMENT_AUTOMATION_RUNTIME_PROFILE": "v2-restricted"})
        self.assertEqual(context.root, self.home / ".local/state/investment_automation_v2")
        for extra in ({"INVESTMENT_AUTOMATION_RUNTIME_PROFILE": "typo"},
                      {"INVESTMENT_AUTOMATION_RUNTIME_ROOT": "relative"},
                      {"INVESTMENT_AUTOMATION_RUNTIME_ROOT": str(self.root),
                       "INVESTMENT_AUTOMATION_RUNTIME_PROFILE": "v1"}):
            with self.subTest(extra=extra), self.assertRaises(RuntimeIsolationError):
                resolve_runtime({**self.env, **extra})
        self.assertEqual(list(self.home.iterdir()), [])

    def test_native_pdf_paths_and_readers_use_the_runtime_boundary(self):
        self.child(f'''
            from pathlib import Path
            from src.runtime_context import RuntimeIsolationError, RUNTIME
            from src.research_reports import _extract_pdf_text_pymupdf, _extract_pdf_text_ocr
            for reader in (_extract_pdf_text_pymupdf, _extract_pdf_text_ocr):
                try:
                    reader(Path({str(self.home / "production.pdf")!r}))
                except RuntimeIsolationError:
                    pass
                else:
                    raise AssertionError("native PDF reader accepted an external path")
            from src.report_formatters import _triage_proxy_calibration_maintenance_state
            assert "absent" in _triage_proxy_calibration_maintenance_state()[0]
        ''')

    def test_home_xdg_credentials_and_yfinance_sqlite_are_separate(self):
        self.child(r'''
            import os
            from pathlib import Path
            from src.runtime_context import RUNTIME, configure_provider_cache
            RUNTIME.prepare()
            for key in ("HOME", "XDG_CACHE_HOME", "XDG_STATE_HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "TMPDIR"):
                assert Path(os.environ[key]).resolve().is_relative_to(RUNTIME.root)
            assert not any(k in os.environ for k in ("TELEGRAM_BOT_TOKEN", "ALPHA_VANTAGE_API_KEY",
                          "INVESTMENT_AUTOMATION_INPUT_SOURCE", "INVESTMENT_AUTOMATION_LOG_DIR",
                          "INVESTMENT_AUTOMATION_BASELINE_STARTED_AT"))
            import yfinance as yf
            configure_provider_cache(yf)
            from yfinance import cache
            for manager in (cache._TzDBManager, cache._CookieDBManager, cache._ISINDBManager):
                assert Path(manager.get_location()) == RUNTIME.root / "cache/yfinance"
            cache.get_tz_cache().store("UNIT_TEST", "UTC")
            assert cache.get_tz_cache().lookup("UNIT_TEST") == "UTC"
            assert list((RUNTIME.root / "cache/yfinance").glob("*.db"))
        ''', extra={"TELEGRAM_BOT_TOKEN": "unit-test-secret", "ALPHA_VANTAGE_API_KEY": "unit-test-key",
                    "INVESTMENT_AUTOMATION_BASELINE_STARTED_AT": "unit-test-invalid",
                    "INVESTMENT_AUTOMATION_LOG_DIR": str(self.home / "production-logs")})
        self.assertEqual(list(self.home.iterdir()), [])

    def test_all_mutable_families_and_real_writers(self):
        self.child(r'''
            from src.runtime_context import RUNTIME, CODE_ROOT
            from src.utils import *
            from src.data_fetcher import MarketDataFetcher
            from src.official_data_fetcher import OfficialDataFetcher
            from src.canadian_data_fetcher import CanadianDataFetcher
            from src.history_engine import save_current_snapshot
            from src.allocation_change_engine import save_allocation_snapshot
            from src.decision_manifest_engine import write_decision_manifest, write_failed_run_audit
            from src.run_logging_engine import write_universe_snapshot, append_run_log_history
            from src.ticker_memory_engine import update_ticker_memory
            from src.research_reports import create_research_report_scaffold
            from src.csv_schema_engine import repair_safe_csv_schemas
            from src.backup_engine import create_project_backup
            RUNTIME.prepare()
            ensure_directories()
            create_research_report_scaffold()
            for fetcher in (MarketDataFetcher(), OfficialDataFetcher(), CanadianDataFetcher()):
                assert fetcher.cache_dir.is_relative_to(CACHE_DIR)
            save_current_snapshot(REPORTS_DIR, "high-cagr", {}, run_purpose="DEVELOPMENT_TEST")
            save_allocation_snapshot(REPORTS_DIR, {"allocations": []}, "high-cagr", run_purpose="DEVELOPMENT_TEST")
            write_decision_manifest(REPORTS_DIR, {"run_id": "unit-test", "genuine_forward_evidence": False})
            write_failed_run_audit(reports_dir=REPORTS_DIR, project_root=CODE_ROOT, run_id="unit-test-failure",
                run_timestamp="2000-01-01T00:00:00", run_purpose="DIAGNOSTIC", mode="high-cagr", capital=0,
                input_audit={"hard_failures": []})
            write_universe_snapshot({}, "unit-test-universe", "high-cagr", "unit-test", REPORTS_DIR, run_purpose="DEVELOPMENT_TEST")
            append_run_log_history(DATA_DIR / "run_log_history.csv", [])
            update_ticker_memory(DATA_DIR / "ticker_memory.csv", [])
            write_text(DATA_DIR / "watchlist.csv", "ticker\nUNIT_TEST\n")
            repair_safe_csv_schemas(CODE_ROOT, skip_portfolio_repair=True)
            assert list((DATA_DIR / "repair_backups").rglob("watchlist.csv"))
            families = ["portfolio_state_snapshot.csv", "portfolio_change_history.csv", "portfolio_inferred_transactions.csv",
                "account_performance_history.csv", "proxy_calibration_history.csv", "proxy_correction_history.csv",
                "source_health_history.csv", "anomaly_history.csv", "discovery_universe_cache.csv", "model_tuning_history.csv"]
            for name in families:
                write_csv_records(DATA_DIR / name, [], ["unit_test"])
            for name in ("latest_report.md", "latest_walk_forward_report.md", "latest_backtest_report.md",
                         "latest_improvement_suggestions.md", "diagnostics/unit-test.md"):
                write_text(REPORTS_DIR / name, "UNIT TEST ONLY")
            for name in ("logs/test.log", "locks/test.lock", "state/input_backups/test.json",
                         "state/portfolio_sync_state.json", "data/cached_market_data/backtest_prices.csv"):
                write_text(RUNTIME.root / name, "UNIT TEST ONLY")
            backup = create_project_backup(CODE_ROOT)
            assert Path(backup["backup_path"]).is_relative_to(RUNTIME.root / "backups")
            assert (REPORTS_DIR / "decision_manifests/unit-test.json").exists()
            assert (REPORTS_DIR / "failed_run_audits/unit-test-failure.json").exists()
            assert (REPORTS_DIR / "universe_snapshots/unit-test-universe.json").exists()
            assert list((REPORTS_DIR / "history").glob("*.json"))
        ''')
        self.assertEqual(list(self.home.iterdir()), [])

    def test_explicit_output_overrides_and_external_mutable_reads_fail(self):
        external = self.base / "other-runtime"
        external.mkdir()
        (external / "input.csv").write_text("unit-test\n")
        self.child(f'''
            from pathlib import Path
            from src.runtime_context import RuntimeIsolationError
            from src.utils import write_text, read_csv_records
            from src.data_fetcher import MarketDataFetcher
            operations = [lambda: write_text(Path({str(external)!r}) / "out" / "file", "bad"),
                          lambda: MarketDataFetcher(cache_dir=Path({str(external)!r}) / "cache"),
                          lambda: read_csv_records(Path({str(external)!r}) / "input.csv")]
            for operation in operations:
                try:
                    operation()
                except RuntimeIsolationError:
                    pass
                else:
                    raise AssertionError("external path accepted")
        ''')
        self.assertEqual([p.name for p in external.iterdir()], ["input.csv"])

    def test_symlink_added_after_activation_is_rejected_at_io(self):
        external = self.base / "external"
        external.mkdir()
        source = NO_NETWORK + textwrap.dedent("""
            from src.runtime_context import RUNTIME, RuntimeIsolationError
            RUNTIME.prepare()
            print("READY", flush=True)
            input()
            try:
                (RUNTIME.root / "late-link" / "escaped.txt").write_text("bad")
            except RuntimeIsolationError:
                print("REJECTED", flush=True)
            else:
                raise AssertionError("late symlink escaped")
        """)
        child = subprocess.Popen([sys.executable, "-B", "-c", source], cwd=CODE_ROOT,
                                 env={**self.env, "INVESTMENT_AUTOMATION_RUNTIME_ROOT": str(self.root)},
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            self.assertEqual(child.stdout.readline().strip(), "READY")
            (self.root / "late-link").symlink_to(external, target_is_directory=True)
            out, err = child.communicate("continue\n", timeout=30)
            self.assertEqual(child.returncode, 0, err)
            self.assertIn("REJECTED", out)
        finally:
            if child.poll() is None:
                child.kill()
                child.communicate()
        self.assertEqual(list(external.iterdir()), [])

    def test_validation_and_health_probes_do_not_create_a_portfolio(self):
        self.child(r'''
            import main
            from src.runtime_context import RUNTIME, CODE_ROOT
            from src.health_check_engine import _writeability_rows
            from src.storage_observability_engine import build_storage_health_rows
            assert main.main(["validate-inputs"]) == 1
            assert not (RUNTIME.root / "data/portfolio.csv").exists()
            assert all(row["status"] == "PASS" for row in _writeability_rows(CODE_ROOT))
            assert build_storage_health_rows(CODE_ROOT)
        ''')

    def test_static_config_writes_are_rejected(self):
        self.child(r'''
            from src.runtime_context import RuntimeIsolationError
            from src.utils import CONFIG_DIR, write_yaml
            try:
                write_yaml(CONFIG_DIR / "must-not-exist.yaml", {})
            except RuntimeIsolationError:
                pass
            else:
                raise AssertionError("config write accepted")
        ''')
        self.assertFalse((CODE_ROOT / "config/must-not-exist.yaml").exists())

    def test_two_roots_do_not_share_mutable_files(self):
        code = '''
            from src.runtime_context import RUNTIME
            from src.utils import DATA_DIR, write_text
            assert not (DATA_DIR / "unique.txt").exists()
            write_text(DATA_DIR / "unique.txt", str(RUNTIME.root))
        '''
        other = self.base / "runtime-b"
        self.child(code)
        self.child(code, root=other)
        self.assertNotEqual((self.root / "data/unique.txt").read_text(), (other / "data/unique.txt").read_text())

    def test_unsafe_cli_commands_and_direct_analysis_fail_before_writes(self):
        for argv in (["init"], ["export-template"], ["sync-portfolio"], ["apply-safe-tuning"],
                     ["analyze", "--capital", "1"], ["analyze", "--run-purpose", "SCHEDULED_DECISION"],
                     ["analyze", "--run-purpose", "MANUAL_DECISION"]):
            with self.subTest(argv=argv):
                result = self.child(f'import main; main.main({argv!r})', success=False)
                self.assertRegex(result.stderr, "disabled in restricted V2|Restricted V2 permits")
                self.assertFalse(self.root.exists())
        self.child('import main; main.run_analysis(1)', success=False)
        self.assertFalse(self.root.exists())

    def test_operational_scripts_reject_import_and_shell_rejects_before_writes(self):
        names = ("sync_operational_inputs", "run_automatic_portfolio_sync", "install_systemd_automation",
                 "update_deployment_code", "request_telegram_analysis", "telegram_notify", "run_scheduled_maintenance")
        for name in names:
            with self.subTest(name=name):
                result = self.child(f'import scripts.{name}', success=False)
                self.assertIn("disabled in restricted V2", result.stderr)
                self.assertFalse(self.root.exists())
        result = subprocess.run(["bash", str(CODE_ROOT / "scripts/run_investment_analysis.sh")],
                                env={**self.env, "INVESTMENT_AUTOMATION_RUNTIME_ROOT": str(self.root)},
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 64)
        self.assertFalse(self.root.exists())
        self.assertEqual(list(self.home.iterdir()), [])

    def test_direct_cli_without_bytecode_flags_has_no_bootstrap_writes(self):
        env = {key: value for key, value in self.env.items() if key != "PYTHONDONTWRITEBYTECODE"}
        env["INVESTMENT_AUTOMATION_RUNTIME_ROOT"] = str(self.root)
        before = {str(p): p.stat().st_mtime_ns for folder in ("src", "scripts")
                  for p in (CODE_ROOT / folder).rglob("*.pyc")}
        for script, args, expected in (("main.py", ["runtime-info"], 0),
                                       ("scripts/install_systemd_automation.py", [], 1)):
            result = subprocess.run([sys.executable, str(CODE_ROOT / script), *args], env=env,
                                    cwd=CODE_ROOT, text=True, capture_output=True, timeout=90)
            self.assertEqual(result.returncode, expected, result.stderr)
        self.assertFalse(self.root.exists())
        after = {str(p): p.stat().st_mtime_ns for folder in ("src", "scripts")
                 for p in (CODE_ROOT / folder).rglob("*.pyc")}
        self.assertEqual(before, after)

    def test_subprocess_and_sqlite_escape_fail_closed(self):
        self.child(f'''
            import subprocess, sqlite3
            from src.runtime_context import RuntimeIsolationError
            for call in (lambda: subprocess.run(["touch", {str(self.base / 'escape')!r}]),
                         lambda: sqlite3.connect({str(self.base / 'escape.db')!r})):
                try:
                    call()
                except RuntimeIsolationError:
                    pass
                else:
                    raise AssertionError("unguarded operation accepted")
        ''')
        self.assertFalse((self.base / "escape").exists())
        self.assertFalse((self.base / "escape.db").exists())

    def test_equivalent_deterministic_recommendations_across_profiles(self):
        legacy = json.loads(self.child(EQUIVALENCE, isolated=False).stdout)
        isolated = json.loads(self.child(EQUIVALENCE).stdout)
        self.assertEqual(legacy, isolated)
        self.assertFalse(self.root.exists())

    def test_launcher_runtime_info_is_non_authoritative_and_read_only(self):
        result = subprocess.run([sys.executable, "-B", str(CODE_ROOT / "scripts/run_v2.py"),
                                 "--runtime-root", str(self.root), "runtime-info"],
                                env=self.env, cwd=CODE_ROOT, capture_output=True, text=True, timeout=90)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {"runtime_profile": "v2-restricted",
                         "runtime_root": str(self.root), "code_root": str(CODE_ROOT)})
        self.assertFalse(self.root.exists())


if __name__ == "__main__":
    unittest.main()
