import copy
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from scripts.run_scheduled_maintenance import due_audit_commands
from src.audit_signal_engine import compute_full_audit_signal, compute_model_audit_signal
from src.decision_quality_engine import compute_decision_quality
from src.mode_artifacts import mode_artifact_path
from src.report_formatters import build_compact_model_health_section, build_triage_header
from src.report_generator import generate_reports
from src.walk_forward_signal_engine import compute_walk_forward_signal


class CompactOperationalGuidanceTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.reports = self.root / "reports"
        self.reports.mkdir()

    def write_artifact(self, filename, mode, text, age_days=0):
        path = mode_artifact_path(self.reports / filename, mode)
        path.write_text(text, encoding="utf-8")
        timestamp = time.time() - age_days * 86400
        os.utime(path, (timestamp, timestamp))

    def assert_no_manual_operation(self, text, *, check_advice=True):
        for command in ("walk-forward-backtest", "full-audit", "model-audit"):
            self.assertNotIn(command, text)
        if check_advice:
            for advice in ("Lancer :", "Relancer", "Continuer à", "Commande :", "Prochaine exécution"):
                self.assertNotIn(advice.casefold(), text.casefold())

    def triage(self, mode, signal):
        with patch(
            "src.report_formatters._triage_proxy_calibration_maintenance_state",
            return_value=("Calibration à jour.", []),
        ):
            return build_triage_header(
                mode=mode, allocation_result={"allocations": []}, sell_rows=[],
                validation_priority_rows=[], anomaly_rows=[], analyses={},
                watchlist_analyses={}, market_analyses={}, discovery_analyses={},
                walk_forward_status=signal,
            )

    def test_walk_forward_artifact_states_are_information_not_manual_actions(self):
        for mode in ("high-cagr", "balanced", "family-office", "rational-aggressive"):
            for state, periods, age in (
                ("ABSENT", None, 0), ("DORMANT", 0, 0), ("DORMANT", 3, 0),
                ("EARLY", 6, 0), ("HEALTHY", 8, 0), ("STALE", 8, 22),
            ):
                with self.subTest(mode=mode, state=state, periods=periods):
                    if periods is not None:
                        self.write_artifact(
                            "latest_walk_forward_inventory.csv", mode,
                            f"mode,usable_for_walk_forward\n{mode},True\n", age,
                        )
                        self.write_artifact(
                            "latest_walk_forward_summary.csv", mode,
                            f"mode,simulated_periods,regime_count\n{mode},{periods},1\n",
                        )
                    signal = compute_walk_forward_signal(self.reports, mode)
                    original = copy.deepcopy(signal)
                    self.assertEqual(signal["status"], f"WALK_FORWARD_{state}")
                    health = build_compact_model_health_section(walk_forward_status=signal)
                    self.assertIn(signal["status"], health)
                    if state in {"DORMANT", "EARLY", "HEALTHY"}:
                        self.assertIn(f"{periods} période", health)
                    self.assertIn("après la génération du rapport", health)
                    self.assertIn("pas le résultat de cette étape", health)
                    self.assertIn("ne garantit pas de nouvelles périodes simulables", health)
                    self.assert_no_manual_operation(health)
                    triage = self.triage(mode, signal)
                    self.assertNotIn("ACTIONS SYSTÈME", triage)
                    self.assert_no_manual_operation(triage)
                    self.assertEqual(signal, original)

    def test_due_audits_still_belong_to_maintenance(self):
        for mode in ("high-cagr", "balanced"):
            for full_age, model_age, expected in (
                (None, None, "full-audit"), (62, 32, "full-audit"),
                (0, 32, "model-audit"), (0, 0, None),
            ):
                with self.subTest(mode=mode, full_age=full_age, model_age=model_age):
                    for name, age in (("latest_full_audit_summary.csv", full_age),
                                      ("latest_model_audit.csv", model_age)):
                        if age is not None:
                            self.write_artifact(
                                name, mode, "section,metric,status,value\nRésumé,Santé,OK,90\n", age,
                            )
                    commands, full, model = due_audit_commands(reports_dir=self.reports, mode=mode)
                    originals = copy.deepcopy((full, model))
                    self.assertEqual([command[1] for command in commands], [expected] if expected else [])
                    health = build_compact_model_health_section(full_audit_status=full, model_audit_status=model)
                    self.assertIn(full["status"], health)
                    self.assertIn(model["status"], health)
                    self.assertIn("maintenance planifiée", health)
                    self.assertIn("ou sinon l’audit de stabilité dû", health)
                    self.assertIn("après réussite des contrôles préalables et du health-check", health)
                    self.assertIn("En cas de blocage ou d’échec", health)
                    self.assert_no_manual_operation(health)
                    self.assertEqual((full, model), originals)

    def test_unreadable_signals_do_not_reintroduce_cli_instructions(self):
        with patch.object(Path, "stat", side_effect=PermissionError("fixture unreadable")):
            walk = compute_walk_forward_signal(self.reports, "high-cagr")
            full = compute_full_audit_signal(self.reports, "high-cagr")
            model = compute_model_audit_signal(self.reports, "high-cagr")
        health = build_compact_model_health_section(
            walk_forward_status=walk, full_audit_status=full, model_audit_status=model,
        )
        self.assertIn("WALK_FORWARD_ABSENT", health)
        self.assertIn("FULL_AUDIT_ABSENT", health)
        self.assertIn("MODEL_AUDIT_ABSENT", health)
        self.assertIn("illisible", health)
        self.assert_no_manual_operation(health)

    def test_zero_capital_delivered_reports_hide_sentinel_confidence_without_changing_data(self):
        mode = "high-cagr"
        self.write_artifact("latest_walk_forward_inventory.csv", mode, "mode\nhigh-cagr\n")
        self.write_artifact("latest_walk_forward_summary.csv", mode, "simulated_periods,regime_count\n0,0\n")
        self.write_artifact("latest_full_audit_summary.csv", mode, "status,value\nOK,90\n", 62)
        allocation = {"allocations": []}
        quality = compute_decision_quality({}, allocation, {}, mode=mode)
        allocation["decision_quality"] = quality
        original = copy.deepcopy(allocation)
        signals = {
            "walk_forward_signal": compute_walk_forward_signal(self.reports, mode),
            "full_audit_signal": compute_full_audit_signal(self.reports, mode),
            "model_audit_signal": compute_model_audit_signal(self.reports, mode),
        }
        with patch("src.report_generator.DATA_DIR", self.root / "data"):
            generate_reports(self.reports, mode, 0, {}, allocation, {}, [], [], [], [], **signals)
        for suffix in (".md", ".html", "_high_cagr.md", "_high_cagr.html"):
            with self.subTest(suffix=suffix):
                text = (self.reports / f"latest_report_compact{suffix}").read_text(encoding="utf-8")
                self.assertIn("WALK_FORWARD_DORMANT", text)
                self.assertIn("FULL_AUDIT_STALE", text)
                self.assertIn("Confiance   : N/A", text)
                self.assertIn("Robustesse : N/A", text)
                self.assertIn("ne mesure pas la certitude", text)
                self.assertNotIn("HIGH (100", text)
                # Other report sections retain legitimate human data-maintenance advice.
                self.assert_no_manual_operation(text, check_advice=False)
        self.assertEqual(allocation, original)
        self.assertEqual(quality["decision_quality_score"], 100.0)
        self.assertEqual(quality["decision_quality_level"], "HIGH")

    def test_missing_quality_and_sensitivity_alone_do_not_imply_zero_capital(self):
        missing = build_compact_model_health_section()
        self.assertIn("Confiance   : N/D", missing)
        # Synthetic display fixture only; no positive-capital analysis is executed.
        applicable = build_compact_model_health_section(decision_quality={
            "decision_quality_level": "MEDIUM", "decision_quality_score": 70,
            "data_quality_status": "ROBUST", "sensitivity_status": "NOT_APPLICABLE",
        })
        self.assertIn("Confiance   : MEDIUM (70/100)", applicable)


if __name__ == "__main__":
    unittest.main()
