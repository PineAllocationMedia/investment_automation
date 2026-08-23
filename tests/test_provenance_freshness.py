import csv
import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

from src.auto_fundamentals import merge_automated_with_manual_overrides
from src.evidence_provenance import field_is_confirmed
from src.manual_input_sync import sync_proxy_calibration_to_friendly
from src.manual_inputs import load_friendly_manual_inputs
from src.thesis_engine import compute_thesis_status
from tests.helpers import strong_benchmark, strong_manual, strong_market


TODAY = date(2026, 8, 23)
PROXY_COLUMNS = [
    "ticker",
    "company_name",
    "roic_5y_avg_true",
    "net_margin_stable_or_expanding_true",
    "eps_growth_5y_true",
    "eps_growth_estimated_3_5y_true",
    "sector_cagr_estimated_true",
    "forward_pe_true",
    "peg_true",
    "fair_value_true",
    "valuation_vs_5y_avg_ok_true",
    "moat_clear_true",
    "forward_pe_growth_acceptable_true",
    "management_quality_good_true",
    "balance_sheet_strong_true",
    "margin_or_profitability_under_pressure_true",
    "source",
    "source_date",
    "confidence",
    "notes",
]


class ProvenanceFreshnessTest(unittest.TestCase):
    def test_explicit_human_negative_override_remains_confirmed(self):
        manual = strong_manual()
        manual["balance_sheet_strong"] = False
        manual["manual_override_fields"] = ["balance_sheet_strong"]

        self.assertTrue(field_is_confirmed(manual, "balance_sheet_strong"))
        self.assertEqual(self._thesis(manual)["thesis_status"], "WEAKENING")

    def test_high_confidence_research_negative_remains_confirmed(self):
        manual = strong_manual()
        manual["balance_sheet_strong"] = False
        manual["research_report_fields"] = ["balance_sheet_strong"]
        manual["research_report_field_confidence"] = {"balance_sheet_strong": "HIGH"}

        self.assertTrue(field_is_confirmed(manual, "balance_sheet_strong"))
        self.assertEqual(self._thesis(manual)["thesis_status"], "WEAKENING")

    def test_official_current_negative_remains_confirmed(self):
        manual = strong_manual()
        manual["balance_sheet_strong"] = False
        manual["auto_estimated_fields"] = ["balance_sheet_strong"]
        manual["official_confirmed_manual_fields"] = ["balance_sheet_strong"]

        self.assertTrue(field_is_confirmed(manual, "balance_sheet_strong"))
        self.assertEqual(self._thesis(manual)["thesis_status"], "WEAKENING")

    def test_auto_estimated_negative_is_not_confirmed(self):
        manual = strong_manual()
        manual["balance_sheet_strong"] = False
        manual["auto_estimated_fields"] = ["balance_sheet_strong"]

        self.assertFalse(field_is_confirmed(manual, "balance_sheet_strong"))
        self.assertEqual(self._thesis(manual)["thesis_status"], "INTACT")

    def test_proxy_calibration_negative_is_not_human_or_confirmed(self):
        with TemporaryDirectory() as folder:
            loaded = self._sync_and_load(Path(folder), source_date="2026-08-01")
            merged = merge_automated_with_manual_overrides(self._automated_balance(True), loaded)

        self.assertNotIn("balance_sheet_strong", merged["manual_override_fields"])
        self.assertIn("balance_sheet_strong", merged["calibration_applied_fields"])
        self.assertFalse(field_is_confirmed(merged, "balance_sheet_strong"))

    def test_stale_calibration_false_cannot_force_weakening(self):
        with TemporaryDirectory() as folder:
            loaded = self._sync_and_load(Path(folder), source_date="2025-01-01")
            merged = merge_automated_with_manual_overrides(self._automated_balance(True), loaded)

        self.assertTrue(merged["balance_sheet_strong"])
        self.assertIn("balance_sheet_strong", merged["calibration_stale_fields"])
        self.assertNotIn("balance_sheet_strong", merged["calibration_applied_fields"])
        self.assertEqual(self._thesis(merged)["thesis_status"], "INTACT")

    def test_current_strong_evidence_and_stale_false_exposes_conflict(self):
        with TemporaryDirectory() as folder:
            loaded = self._sync_and_load(Path(folder), source_date="2025-01-01")
            automated = self._automated_balance(True)
            automated["official_confirmed_manual_fields"] = ["balance_sheet_strong"]
            merged = merge_automated_with_manual_overrides(automated, loaded)

        self.assertTrue(merged["fundamental_evidence_conflict"])
        self.assertIn("balance_sheet_strong", merged["fundamental_evidence_conflict_fields"])
        self.assertIn("Conflit de preuves", " ".join(self._thesis(merged)["market_watch_reasons"]))

    def test_real_current_deterioration_still_weakens(self):
        manual = strong_manual()
        manual["balance_sheet_strong"] = False
        manual["official_confirmed_manual_fields"] = ["balance_sheet_strong"]

        thesis = self._thesis(manual)

        self.assertEqual(thesis["thesis_status"], "WEAKENING")
        self.assertIn("Bilan financier affaibli confirmé", " ".join(thesis["fundamental_thesis_reasons"]))

    def test_catastrophic_conditions_remain_broken(self):
        manual = strong_manual()
        manual["catastrophic_fraud"] = True

        self.assertEqual(self._thesis(manual)["thesis_status"], "BROKEN")

    def test_valuation_only_problem_does_not_weaken_fundamental_thesis(self):
        manual = strong_manual()
        manual["forward_pe_growth_acceptable"] = False
        manual["manual_override_fields"] = ["forward_pe_growth_acceptable"]

        thesis = self._thesis(manual)

        self.assertEqual(thesis["thesis_status"], "INTACT")
        self.assertEqual(thesis["valuation_watch_status"], "WATCH")

    def test_generated_manual_file_retains_calibration_provenance(self):
        with TemporaryDirectory() as folder:
            loaded = self._sync_and_load(Path(folder), source_date="2026-08-01")

        self.assertEqual(loaded["field_provenance"]["balance_sheet_strong"], "PROXY_CALIBRATION_SYNC")
        self.assertIn("balance_sheet_strong", loaded["calibration_synced_fields"])
        self.assertNotIn("balance_sheet_strong", loaded["manual_override_fields"])

    def test_genuine_user_edit_through_generated_file_is_preserved(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            loaded = self._sync_and_load(root, source_date="2026-08-01")
            self.assertFalse(loaded["balance_sheet_strong"])
            friendly = root / "manual_inputs_friendly.txt"
            friendly.write_text(
                friendly.read_text(encoding="utf-8").replace(
                    "balance_sheet_strong = FALSE",
                    "balance_sheet_strong = TRUE",
                ),
                encoding="utf-8",
            )
            edited = load_friendly_manual_inputs(friendly, today=TODAY)["VRT"]
            self.assertIn("balance_sheet_strong", edited["manual_override_fields"])
            sync_proxy_calibration_to_friendly(
                root / "proxy_calibration.csv",
                friendly,
                root / "sync_log.json",
                today=TODAY,
            )
            resynced = load_friendly_manual_inputs(friendly, today=TODAY)["VRT"]

        self.assertTrue(resynced["balance_sheet_strong"])
        self.assertIn("balance_sheet_strong", resynced["manual_override_fields"])
        self.assertTrue(field_is_confirmed(resynced, "balance_sheet_strong"))

    def test_fresh_research_outranks_stale_calibration(self):
        with TemporaryDirectory() as folder:
            loaded = self._sync_and_load(Path(folder), source_date="2025-01-01")
            automated = self._automated_balance(True)
            automated["research_report_fields"] = ["balance_sheet_strong"]
            automated["research_report_field_confidence"] = {"balance_sheet_strong": "HIGH"}
            merged = merge_automated_with_manual_overrides(automated, loaded)

        self.assertTrue(merged["balance_sheet_strong"])
        self.assertEqual(merged["field_provenance"]["balance_sheet_strong"], "RESEARCH_REPORT")
        self.assertTrue(field_is_confirmed(merged, "balance_sheet_strong"))

    def test_vrt_regression_fixture_old_false_is_context_not_weakening(self):
        with TemporaryDirectory() as folder:
            loaded = self._sync_and_load(Path(folder), source_date="2025-01-01")
            merged = merge_automated_with_manual_overrides(self._automated_balance(True), loaded)
            thesis = self._thesis(merged)

        evidence = merged["field_evidence_sources"]["balance_sheet_strong"][0]
        self.assertEqual(evidence["provenance"], "PROXY_CALIBRATION_SYNC")
        self.assertEqual(evidence["freshness"], "STALE")
        self.assertFalse(evidence["currently_authoritative"])
        self.assertTrue(merged["fundamental_evidence_conflict"])
        self.assertEqual(thesis["thesis_status"], "INTACT")

    def _sync_and_load(self, root: Path, source_date: str) -> dict:
        proxy = root / "proxy_calibration.csv"
        with open(proxy, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=PROXY_COLUMNS)
            writer.writeheader()
            writer.writerow(
                {
                    "ticker": "VRT",
                    "company_name": "Vertiv Holdings",
                    "balance_sheet_strong_true": "FALSE",
                    "management_quality_good_true": "TRUE",
                    "margin_or_profitability_under_pressure_true": "FALSE",
                    "source": "VRT calibration fixture",
                    "source_date": source_date,
                    "confidence": "HIGH",
                    "notes": "Historical calibration observation",
                }
            )
        friendly = root / "manual_inputs_friendly.txt"
        sync_proxy_calibration_to_friendly(proxy, friendly, root / "sync_log.json", today=TODAY)
        return load_friendly_manual_inputs(friendly, today=TODAY)["VRT"]

    @staticmethod
    def _automated_balance(value: bool) -> dict:
        automated = strong_manual()
        automated["ticker"] = "VRT"
        automated["balance_sheet_strong"] = value
        automated["auto_estimated_fields"] = [
            "eps_growth_5y",
            "eps_growth_estimated_3_5y",
            "sector_cagr_estimated",
            "moat_clear",
            "management_quality_good",
            "margin_or_profitability_under_pressure",
            "balance_sheet_strong",
        ]
        automated["research_report_fields"] = []
        automated["official_supported_manual_fields"] = []
        automated["official_confirmed_manual_fields"] = []
        automated["input_data_mode"] = "AUTO_ESTIMATED"
        automated["auto_source_quality"] = "HIGH"
        return automated

    @staticmethod
    def _thesis(manual: dict) -> dict:
        score = {
            "score_missing_data_count": 0,
            "eps_growth_estimated_3_5y": 30,
            "eps_growth_5y": 25,
            "peg": 1.6,
            "sector_cagr_estimated": 20,
            "price_to_fair_value": 1.0,
            "profile_weak_growth_threshold": 10,
            "profile_sector_cagr_threshold": 8,
            "profile_peg_limit": 2,
        }
        return compute_thesis_status(manual, score, strong_market(), strong_benchmark())


if __name__ == "__main__":
    unittest.main()
