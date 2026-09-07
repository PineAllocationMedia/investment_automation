from unittest.mock import patch
import tempfile
import unittest
import copy
from pathlib import Path

from src.allocation_engine import allocate_capital
from src.baseline_identity import (
    VALIDATION_BASELINE_ID,
    baseline_observation_metadata,
    load_baseline_identity,
)
from src.critical_input_engine import (
    HARD_FAIL,
    audit_runtime_critical_inputs,
    audit_static_critical_inputs,
    critical_config_fingerprint,
)
from src.allocation_change_engine import save_allocation_snapshot
from src.decision_manifest_engine import (
    build_decision_manifest,
    git_commit_sha,
    write_decision_manifest,
    write_failed_run_audit,
)
from src.history_engine import save_current_snapshot
from src.model_version import MODEL_RULES_VERSION
from src.run_logging_engine import write_universe_snapshot
from src.report_generator import _baseline_report_metadata_lines, build_compact_markdown_report
from src.utils import load_json
from tests.helpers import full_strong_analysis
from src.validation_evidence import AUTO_TUNING_POLICY, VALIDATION_SCHEMA_VERSION


class BaselineIdentityTest(unittest.TestCase):
    def setUp(self):
        lineage = patch("src.model_identity.MODEL_LINEAGE", "V1")
        lineage.start()
        self.addCleanup(lineage.stop)

    def test_baseline_identity_and_frozen_versions_are_exact(self):
        root = Path(__file__).resolve().parents[1]
        identity = load_baseline_identity(root / "config" / "baseline.yaml")

        self.assertEqual(identity["baseline_id"], VALIDATION_BASELINE_ID)
        self.assertEqual(MODEL_RULES_VERSION, "2026-08-23-allocation-room-integrity-v7")
        self.assertEqual(VALIDATION_SCHEMA_VERSION, "2026-09-06-validation-identity-v4")
        self.assertEqual(AUTO_TUNING_POLICY, "PROPOSAL_ONLY")
        self.assertEqual(identity["approved_config_fingerprint"], critical_config_fingerprint(root))

    def test_baseline_start_is_not_retroactive_and_diagnostics_are_excluded(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "baseline.yaml"
            config.write_text(
                "baseline_id: VALIDATION_BASELINE_V1\n"
                "baseline_started_at: '2026-09-01T12:00:00'\n"
                "baseline_status: ACTIVE\n",
                encoding="utf-8",
            )
            before = baseline_observation_metadata(
                run_timestamp="2026-09-01T11:59:59",
                run_purpose="SCHEDULED_DECISION",
                config_path=config,
            )
            after = baseline_observation_metadata(
                run_timestamp="2026-09-01T12:00:01",
                run_purpose="SCHEDULED_DECISION",
                capital=500,
                config_path=config,
            )
            diagnostic = baseline_observation_metadata(
                run_timestamp="2026-09-01T12:00:01",
                run_purpose="DIAGNOSTIC",
                capital=500,
                config_path=config,
            )
            zero_capital = baseline_observation_metadata(
                run_timestamp="2026-09-01T12:00:01",
                run_purpose="SCHEDULED_DECISION",
                capital=0,
                config_path=config,
            )

        self.assertEqual(before["baseline_evidence_status"], "PRE_BASELINE_OBSERVATION")
        self.assertFalse(before["baseline_forward_eligible"])
        self.assertEqual(after["baseline_evidence_status"], "BASELINE_V1_FORWARD_OBSERVATION")
        self.assertTrue(after["baseline_forward_eligible"])
        self.assertEqual(diagnostic["baseline_evidence_status"], "BASELINE_NON_DECISION_OBSERVATION")
        self.assertFalse(diagnostic["baseline_forward_eligible"])
        self.assertEqual(zero_capital["baseline_evidence_status"], "BASELINE_ZERO_CAPITAL_OBSERVATION")
        self.assertFalse(zero_capital["baseline_forward_eligible"])

    def test_pending_deployment_does_not_fabricate_baseline_history(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "baseline.yaml"
            config.write_text(
                "baseline_id: VALIDATION_BASELINE_V1\nbaseline_started_at: ''\nbaseline_status: PENDING_APPROVED_DEPLOYMENT\n",
                encoding="utf-8",
            )
            metadata = baseline_observation_metadata(
                run_timestamp="2026-09-01T12:00:01",
                run_purpose="MANUAL_DECISION",
                config_path=config,
            )

        self.assertEqual(metadata["baseline_evidence_status"], "PRE_BASELINE_PENDING_APPROVED_DEPLOYMENT")
        self.assertFalse(metadata["baseline_forward_eligible"])

    def test_structured_snapshots_preserve_baseline_and_manifest_metadata(self):
        baseline = {
            "baseline_id": VALIDATION_BASELINE_ID,
            "baseline_started_at": "2026-09-01T12:00:00",
            "baseline_evidence_status": "BASELINE_V1_FORWARD_OBSERVATION",
            "baseline_forward_eligible": True,
        }
        with tempfile.TemporaryDirectory() as directory:
            reports = Path(directory)
            analyses = {"MSFT": {"ticker": "MSFT", "score_total": 9.0, "universe": "CORE_PORTFOLIO"}}
            save_current_snapshot(
                reports,
                "high-cagr",
                analyses,
                run_purpose="MANUAL_DECISION",
                baseline_metadata=baseline,
                manifest_reference="reports/decision_manifests/run-1.json",
                manifest_fingerprint="manifest",
            )
            save_allocation_snapshot(
                reports,
                {"allocations": [{"destination": "MSFT", "montant": 500}]},
                analysis_mode="high-cagr",
                run_purpose="MANUAL_DECISION",
                baseline_metadata=baseline,
                manifest_reference="reports/decision_manifests/run-1.json",
                manifest_fingerprint="manifest",
            )
            write_universe_snapshot(
                analyses,
                run_id="run-1",
                mode="high-cagr",
                model_rules_version=MODEL_RULES_VERSION,
                reports_dir=reports,
                run_purpose="MANUAL_DECISION",
                baseline_metadata=baseline,
                manifest_reference="reports/decision_manifests/run-1.json",
                manifest_fingerprint="manifest",
            )
            analysis_payload = load_json(reports / "latest_analysis_snapshot_high-cagr.json")
            allocation_payload = load_json(reports / "latest_allocation_snapshot_high-cagr.json")
            universe_payload = load_json(reports / "universe_snapshots" / "run-1.json")

        for payload in (analysis_payload, allocation_payload, universe_payload):
            self.assertEqual(payload["baseline_id"], VALIDATION_BASELINE_ID)
            self.assertTrue(payload["baseline_forward_eligible"])
            self.assertEqual(payload["manifest_fingerprint"], "manifest")

    def test_report_metadata_exposes_baseline_code_purpose_and_manifest(self):
        lines = _baseline_report_metadata_lines(
            {
                "baseline_identity": {
                    "baseline_id": VALIDATION_BASELINE_ID,
                    "baseline_evidence_status": "BASELINE_V1_FORWARD_OBSERVATION",
                    "validation_schema_version": VALIDATION_SCHEMA_VERSION,
                    "run_purpose": "MANUAL_DECISION",
                },
                "decision_manifest": {
                    "git_commit_sha": "c" * 40,
                    "manifest_reference": "reports/decision_manifests/run-1.json",
                    "manifest_fingerprint": "manifest",
                },
            }
        )

        rendered = "\n".join(lines)
        self.assertIn(VALIDATION_BASELINE_ID, rendered)
        self.assertIn(VALIDATION_SCHEMA_VERSION, rendered)
        self.assertIn("MANUAL_DECISION", rendered)
        self.assertIn("reports/decision_manifests/run-1.json", rendered)

    def test_compact_report_smoke_renders_baseline_metadata_from_local_fixture(self):
        analysis = full_strong_analysis("MSFT")
        analysis.update({"universe": "CORE_PORTFOLIO", "allocation_decision": "BUY", "final_position_action": "ADD"})
        allocation_result = {
            "allocations": [{"destination": "MSFT", "montant": 500, "pourcentage": 1.0, "bloc": "core"}],
            "mandatory_vfv_percent": 0,
            "average_score_ex_vfv": 9.0,
            "decision_quality": {"decision_quality_level": "HIGH", "decision_quality_score": 90},
            "baseline_identity": {
                "baseline_id": VALIDATION_BASELINE_ID,
                "baseline_evidence_status": "BASELINE_V1_FORWARD_OBSERVATION",
                "validation_schema_version": VALIDATION_SCHEMA_VERSION,
                "run_purpose": "MANUAL_DECISION",
            },
            "decision_manifest": {
                "git_commit_sha": "c" * 40,
                "manifest_reference": "reports/decision_manifests/run-1.json",
                "manifest_fingerprint": "manifest",
            },
        }

        markdown = build_compact_markdown_report(
            mode="high-cagr",
            capital=500,
            analyses={"MSFT": analysis},
            allocation_result=allocation_result,
            portfolio_risk={"total_portfolio_value": 10000, "alerts": []},
            tax_report=[],
            validation_warnings=[],
            watchlist_analyses={},
            market_analyses={},
            market_universe={},
            discovery_analyses={},
            discovery_universe={},
            proxy_calibration_summary=[],
            proxy_correction_audit_rows=[],
            allocation_change_rows=[],
            allocation_sensitivity={},
            validation_priority_rows=[],
            research_needed_rows=[],
            portfolio_change_rows=[],
            portfolio_change_history_rows=[],
            portfolio_change_summary_rows=[],
            account_performance_rows=[],
            account_chart_rows=[],
        )

        self.assertIn("# Rapport compact d'investissement", markdown)
        self.assertIn(VALIDATION_BASELINE_ID, markdown)
        self.assertIn("reports/decision_manifests/run-1.json", markdown)


class CriticalInputAuditTest(unittest.TestCase):
    def test_missing_portfolio_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._minimal_project(Path(directory), with_portfolio=False)
            audit = audit_static_critical_inputs(root, capital=500, run_purpose="MANUAL_DECISION")

        self.assertEqual(audit["status"], HARD_FAIL)
        self.assertTrue(any(row["code"] == "MISSING_PORTFOLIO" for row in audit["hard_failures"]))

    def test_noncritical_watchlist_problem_is_advisory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._minimal_project(Path(directory), with_portfolio=True)
            (root / "data" / "watchlist.csv").write_text(
                "ticker,notes,manual_priority\nMSFT,,IMPOSSIBLE\n",
                encoding="utf-8",
            )
            audit = audit_static_critical_inputs(root, capital=0, run_purpose="DIAGNOSTIC")

        self.assertFalse(audit["hard_failures"])
        self.assertTrue(audit["advisories"])

    def test_corrupt_critical_configuration_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._minimal_project(Path(directory), with_portfolio=True)
            (root / "config" / "rules.yaml").write_text("broken: [", encoding="utf-8")
            audit = audit_static_critical_inputs(root, capital=500, run_purpose="MANUAL_DECISION")

        self.assertTrue(any(row["code"] == "CORRUPT_CRITICAL_CONFIG" for row in audit["hard_failures"]))

    def test_unapproved_critical_configuration_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._minimal_project(Path(directory), with_portfolio=True)
            approved = critical_config_fingerprint(root)
            (root / "config" / "baseline.yaml").write_text(
                "baseline_id: VALIDATION_BASELINE_V1\n"
                "baseline_started_at: ''\n"
                "baseline_status: PENDING_APPROVED_DEPLOYMENT\n"
                f"approved_config_fingerprint: {approved}\n",
                encoding="utf-8",
            )
            initial = audit_static_critical_inputs(root, capital=500, run_purpose="MANUAL_DECISION")
            (root / "config" / "rules.yaml").write_text("changed: true\n", encoding="utf-8")
            drifted = audit_static_critical_inputs(root, capital=500, run_purpose="MANUAL_DECISION")

        self.assertFalse(any(row["code"] == "BASELINE_CONFIG_FINGERPRINT_MISMATCH" for row in initial["hard_failures"]))
        self.assertTrue(any(row["code"] == "BASELINE_CONFIG_FINGERPRINT_MISMATCH" for row in drifted["hard_failures"]))

    def test_invalid_capital_and_mode_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._minimal_project(Path(directory), with_portfolio=True)
            audit = audit_static_critical_inputs(
                root,
                capital="not-a-number",
                run_purpose="MANUAL_DECISION",
                mode="unsupported",
            )

        codes = {row["code"] for row in audit["hard_failures"]}
        self.assertIn("INVALID_CAPITAL", codes)
        self.assertIn("INVALID_ANALYSIS_MODE", codes)

    def test_missing_cost_basis_currency_fails_closed_but_explicit_mixed_lots_do_not(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._minimal_project(Path(directory), with_portfolio=True)
            (root / "data" / "portfolio.csv").write_text(
                "ticker,shares,average_cost,average_cost_currency,account_type\n"
                "MSFT,1,100,,TFSA\n"
                "AAPL,1,100,CAD,TFSA\n"
                "AAPL,1,90,USD,RRSP\n",
                encoding="utf-8",
            )
            audit = audit_static_critical_inputs(root, capital=500, run_purpose="MANUAL_DECISION")

        codes = {row["code"] for row in audit["hard_failures"]}
        self.assertIn("COST_BASIS_CURRENCY_MISSING", codes)
        self.assertNotIn("INCONSISTENT_TICKER_COST_BASIS_CURRENCIES", codes)

    def test_valid_explicit_mixed_currency_lots_pass_static_critical_input_audit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._minimal_project(Path(directory), with_portfolio=True)
            (root / "data" / "portfolio.csv").write_text(
                "ticker,shares,average_cost,average_cost_currency,account_type\n"
                "AAPL,2,396.94,CAD,TFSA1\n"
                "AAPL,0.2987,299.45,USD,TFSA2\n"
                "MSFT,4,652,CAD,TFSA1\n"
                "MSFT,0.1012,375.18,USD,TFSA2\n"
                "INTU,1,568.87,CAD,TFSA1\n"
                "INTU,0.1819,395.59,USD,TFSA2\n",
                encoding="utf-8",
            )
            audit = audit_static_critical_inputs(root, capital=225, run_purpose="SCHEDULED_DECISION")

        self.assertFalse(audit["hard_failures"], audit["hard_failures"])
        self.assertEqual(audit["status"], "PASS")

    def test_unsafe_value_basis_is_hard_but_manual_current_value_is_advisory(self):
        unsafe = audit_runtime_critical_inputs(
            portfolio_rows=[
                {
                    "ticker": "MSFT",
                    "shares": 2,
                    "current_value_cad": 200,
                    "portfolio_valuation_source": "acquisition_value_fallback",
                }
            ],
            market_data={"VFV.TO": {"current_price": 100}},
            capital=500,
            run_purpose="MANUAL_DECISION",
        )
        manual = audit_runtime_critical_inputs(
            portfolio_rows=[
                {
                    "ticker": "MSFT",
                    "shares": 2,
                    "current_value_cad": 200,
                    "portfolio_valuation_source": "manual_current_value_fallback",
                }
            ],
            market_data={"VFV.TO": {"current_price": 100}},
            capital=500,
            run_purpose="MANUAL_DECISION",
        )

        self.assertTrue(unsafe["hard_failures"])
        self.assertFalse(manual["hard_failures"])
        self.assertTrue(manual["advisories"])

    def test_failed_critical_run_is_auditable_but_not_forward_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._minimal_project(Path(directory), with_portfolio=False)
            reports = root / "reports"
            audit = {"status": "HARD_FAIL", "hard_failures": [{"code": "MISSING_PORTFOLIO"}]}
            payload = write_failed_run_audit(
                reports_dir=reports,
                project_root=root,
                run_id="failed-1",
                run_timestamp="2026-09-01T12:00:00",
                run_purpose="SCHEDULED_DECISION",
                mode="high-cagr",
                capital=500,
                input_audit=audit,
            )

            self.assertTrue((reports / "latest_failed_run_audit.json").exists())
            self.assertTrue((reports / "failed_run_audits" / "failed-1.json").exists())
        self.assertFalse(payload["genuine_forward_evidence"])
        self.assertFalse(payload["baseline"]["baseline_forward_eligible"])
        self.assertEqual(payload["allocations"], [])

    @staticmethod
    def _minimal_project(root: Path, *, with_portfolio: bool) -> Path:
        from src.critical_input_engine import REQUIRED_CONFIG_FILES

        config = root / "config"
        data = root / "data"
        config.mkdir(parents=True)
        data.mkdir(parents=True)
        for filename in REQUIRED_CONFIG_FILES:
            content = "{}\n"
            if filename == "baseline.yaml":
                content = "baseline_id: VALIDATION_BASELINE_V1\nbaseline_started_at: ''\nbaseline_status: PENDING_APPROVED_DEPLOYMENT\n"
            (config / filename).write_text(content, encoding="utf-8")
        if with_portfolio:
            (data / "portfolio.csv").write_text(
                "ticker,shares,average_cost,average_cost_currency,account_type\nMSFT,1,100,USD,TFSA\n",
                encoding="utf-8",
            )
        return root


class DecisionManifestTest(unittest.TestCase):
    def test_repository_git_sha_is_captured(self):
        root = Path(__file__).resolve().parents[1]

        captured = git_commit_sha(root)

        self.assertEqual(len(captured), 40)
        self.assertTrue(all(character in "0123456789abcdef" for character in captured))

    def test_successful_manifest_writes_immutable_run_and_latest_references(self):
        manifest = {
            "run_id": "run-1",
            "manifest_fingerprint": "manifest",
            "decision_output_fingerprint": "decision",
            "git_commit_sha": "a" * 40,
        }
        with tempfile.TemporaryDirectory() as directory:
            reports = Path(directory) / "reports"

            references = write_decision_manifest(reports, manifest)

            write_decision_manifest(reports, manifest)
            with self.assertRaises(FileExistsError):
                write_decision_manifest(reports, {**manifest, "manifest_fingerprint": "conflict"})

            immutable = load_json(reports / "decision_manifests" / "run-1.json")
            latest = load_json(reports / "latest_decision_manifest.json")
        self.assertEqual(immutable, manifest)
        self.assertEqual(latest, manifest)
        self.assertEqual(references["manifest_reference"], "reports/decision_manifests/run-1.json")

    def test_same_input_recommendation_is_deterministic(self):
        candidate = full_strong_analysis("MSFT")
        candidate.update(
            {
                "capital_allocation_score": 90,
                "add_eligibility_status": "ADD_ALLOWED",
                "data_reliability_level": "HIGH",
                "current_value": 10_000,
                "current_value_cad": 10_000,
                "portfolio_valuation_source": "shares_x_market_price_CAD",
                "shares": 1,
                "position_weight": 0.10,
            }
        )
        filler = full_strong_analysis("OLD")
        filler.update(
            {
                "current_value": 90_000,
                "current_value_cad": 90_000,
                "portfolio_valuation_source": "shares_x_market_price_CAD",
                "shares": 1,
                "position_weight": 0.90,
                "thesis_status": "WEAKENING",
                "liquidation_status": "YELLOW",
                "add_eligibility_status": "DO_NOT_ADD",
            }
        )
        inputs = {"MSFT": candidate, "OLD": filler}

        first = allocate_capital(500, copy.deepcopy(inputs), "high-cagr")
        second = allocate_capital(500, copy.deepcopy(inputs), "high-cagr")

        self.assertEqual(first, second)

    def test_same_semantic_inputs_have_same_decision_and_manifest_fingerprint(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._manifest_project(Path(directory))
            baseline = {
                "baseline_id": VALIDATION_BASELINE_ID,
                "baseline_started_at": "2026-09-01T00:00:00",
                "baseline_evidence_status": "BASELINE_V1_FORWARD_OBSERVATION",
                "baseline_forward_eligible": True,
                "run_purpose": "MANUAL_DECISION",
                "model_rules_version": MODEL_RULES_VERSION,
                "validation_schema_version": VALIDATION_SCHEMA_VERSION,
            }
            common = {
                "project_root": root,
                "run_purpose": "MANUAL_DECISION",
                "mode": "high-cagr",
                "capital": 500,
                "analyses_by_universe": {
                    "CORE_PORTFOLIO": {
                        "MSFT": {
                            "ticker": "MSFT",
                            "score_total": 9.0,
                            "allocation_decision": "BUY",
                            "generated_at": "ignored-a",
                        }
                    }
                },
                "allocation_result": {"allocations": [{"destination": "MSFT", "montant": 500, "bloc": "core"}]},
                "research_inputs": {"MSFT": {"fair_value": 500}},
                "market_data": {
                    "MSFT": {
                        "current_price": 450,
                        "fetched_at": "2026-09-01T10:00:00",
                        "cache_path": "/temporary/host-a/MSFT.json",
                    }
                },
                "benchmark_data": {"VFV.TO": {"current_price": 150}},
                "baseline_metadata": baseline,
                "git_sha": "a" * 40,
                "dependency_payload": {
                    "dependency_fingerprint": "dependency",
                    "dependency_lock_fingerprint": "lock",
                },
            }
            first = build_decision_manifest(run_id="run-1", run_timestamp="2026-09-01T12:00:00", **common)
            common["analyses_by_universe"]["CORE_PORTFOLIO"]["MSFT"]["generated_at"] = "ignored-b"
            common["market_data"]["MSFT"]["cache_path"] = "/different/temporary/host-b/MSFT.json"
            second = build_decision_manifest(run_id="run-2", run_timestamp="2026-09-01T12:05:00", **common)

        self.assertEqual(first["decision_output_fingerprint"], second["decision_output_fingerprint"])
        self.assertEqual(first["manifest_fingerprint"], second["manifest_fingerprint"])
        self.assertEqual(first["git_commit_sha"], "a" * 40)

    def test_relevant_input_change_changes_manifest_fingerprint(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._manifest_project(Path(directory))
            kwargs = {
                "project_root": root,
                "run_id": "run-1",
                "run_timestamp": "2026-09-01T12:00:00",
                "run_purpose": "MANUAL_DECISION",
                "mode": "high-cagr",
                "capital": 500,
                "analyses_by_universe": {},
                "allocation_result": {"allocations": []},
                "research_inputs": {},
                "market_data": {},
                "benchmark_data": {},
                "git_sha": "b" * 40,
                "dependency_payload": {
                    "dependency_fingerprint": "dependency",
                    "dependency_lock_fingerprint": "lock",
                },
            }
            first = build_decision_manifest(**kwargs)
            (root / "data" / "portfolio.csv").write_text(
                "ticker,shares,average_cost,average_cost_currency,account_type\nMSFT,2,100,USD,TFSA\n",
                encoding="utf-8",
            )
            second = build_decision_manifest(**kwargs)

        self.assertNotEqual(
            first["portfolio_input_fingerprints"]["combined_fingerprint"],
            second["portfolio_input_fingerprints"]["combined_fingerprint"],
        )
        self.assertNotEqual(first["manifest_fingerprint"], second["manifest_fingerprint"])

    def test_relevant_configuration_change_changes_config_fingerprint(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._manifest_project(Path(directory))
            kwargs = {
                "project_root": root,
                "run_id": "run-1",
                "run_timestamp": "2026-09-01T12:00:00",
                "run_purpose": "MANUAL_DECISION",
                "mode": "high-cagr",
                "capital": 500,
                "analyses_by_universe": {},
                "allocation_result": {"allocations": []},
                "research_inputs": {},
                "market_data": {},
                "benchmark_data": {},
                "git_sha": "b" * 40,
                "dependency_payload": {
                    "dependency_fingerprint": "dependency",
                    "dependency_lock_fingerprint": "lock",
                },
            }
            first = build_decision_manifest(**kwargs)
            (root / "config" / "rules.yaml").write_text("rules:\n  changed: true\n", encoding="utf-8")
            second = build_decision_manifest(**kwargs)

        self.assertNotEqual(
            first["config_fingerprints"]["combined_fingerprint"],
            second["config_fingerprints"]["combined_fingerprint"],
        )
        self.assertNotEqual(first["manifest_fingerprint"], second["manifest_fingerprint"])

    @staticmethod
    def _manifest_project(root: Path) -> Path:
        (root / "config").mkdir(parents=True)
        (root / "data").mkdir(parents=True)
        (root / "config" / "baseline.yaml").write_text(
            "baseline_id: VALIDATION_BASELINE_V1\nbaseline_started_at: ''\nbaseline_status: PENDING_APPROVED_DEPLOYMENT\n",
            encoding="utf-8",
        )
        (root / "config" / "rules.yaml").write_text("rules: {}\n", encoding="utf-8")
        (root / "data" / "portfolio.csv").write_text(
            "ticker,shares,average_cost,average_cost_currency,account_type\nMSFT,1,100,USD,TFSA\n",
            encoding="utf-8",
        )
        (root / "requirements.lock").write_text("PyYAML==6.0.3\n", encoding="utf-8")
        return root


if __name__ == "__main__":
    unittest.main()
