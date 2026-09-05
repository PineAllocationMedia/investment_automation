import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.allocation_engine import apply_deep_averaging_down_context
from src.company_dossier_engine import build_company_dossier
from src.portfolio_loader import enrich_portfolio_with_market_data, load_portfolio, merge_portfolio_rows
from src.report_generator import generate_reports
from src.sell_validation_checklist_engine import sell_validation_checklist_rows
from src.ticker_resolver import resolve_portfolio_lot_rows, resolve_portfolio_rows
from src.utils import read_csv_records, write_csv_records
from src.winner_protection_engine import apply_winner_protection, compute_winner_protection
from tests.helpers import full_strong_analysis


MISSING_REASON = "Coût d’acquisition absent; remplir average_cost et average_cost_currency pour activer la protection."
MIXED_REASON = (
    "Coût d’acquisition disponible par lot/compte, mais coût historique agrégé indisponible : "
    "devises mixtes et absence de conversion fiable aux taux de change historiques."
)
COST_FIELDS = ("average_cost", "average_cost_cad", "acquisition_value", "acquisition_value_cad")


class MixedCostBasisReportingTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def lot_rows(self, currencies=("CAD", "USD"), missing=False):
        rows = [
            {"ticker": "INTU", "shares": 1, "average_cost": "" if missing else 568.87,
             "average_cost_currency": currencies[0], "account_type": "TFSA1"},
            {"ticker": "INTU", "shares": 0.1819, "average_cost": "" if missing else 395.59,
             "average_cost_currency": currencies[1], "account_type": "TFSA2"},
        ]
        path = self.root / "unit-lots.csv"
        write_csv_records(path, rows, list(rows[0]))
        return load_portfolio(path)

    def analysis(self, currencies=("CAD", "USD"), missing=False, fx=1.35):
        aggregate = resolve_portfolio_rows(self.lot_rows(currencies, missing), {}, {}, "unit-fixture")[0]
        enriched = enrich_portfolio_with_market_data(
            [aggregate], {"INTU": {"current_price": 400, "currency": "USD"}}, {"CAD": 1, "USD": fx},
        )[0]
        analysis = full_strong_analysis("INTU")
        analysis.update(enriched)
        analysis["current_price"] = 400
        return analysis

    def assert_mixed_reason(self, text):
        self.assertIn(MIXED_REASON, text)
        self.assertNotIn("Coût d’acquisition absent", text)
        self.assertNotIn("remplir average_cost", text)

    def test_single_currency_cost_retains_existing_gain_and_protection(self):
        for currency in ("CAD", "USD"):
            with self.subTest(currency=currency):
                analysis = self.analysis((currency, currency))
                original = copy.deepcopy(analysis)
                result = compute_winner_protection(analysis)
                self.assertEqual(analysis, original)
                self.assertEqual(analysis["cost_basis_aggregation_status"], "SINGLE_CURRENCY")
                self.assertEqual(result["winner_protection_status"], "NOT_A_WINNER")
                self.assertEqual(result["winner_protection_action"], "HOLD")
                self.assertAlmostEqual(
                    result["unrealized_gain_percent"],
                    analysis["current_value_cad"] / analysis["acquisition_value_cad"] - 1,
                )
                self.assertNotIn("absent", result["winner_protection_reason"])
                self.assertNotIn("devises mixtes", result["winner_protection_reason"])

    def test_truly_missing_cost_retains_missing_message_even_with_different_account_currencies(self):
        analysis = self.analysis(missing=True)
        self.assertEqual(analysis["cost_basis_aggregation_status"], "UNAVAILABLE")
        self.assertEqual(analysis["cost_basis_currencies"], [])
        result = compute_winner_protection(analysis)
        self.assertEqual(result["winner_protection_reason"], MISSING_REASON)
        self.assertEqual(result["winner_protection_status"], "NO_COST_DATA")
        self.assertEqual(result["winner_protection_action"], "HOLD")

    def test_mixed_lots_keep_costs_but_neither_aggregator_sums_or_converts_history(self):
        for currencies in (("CAD", "USD"), ("USD", "CAD")):
            with self.subTest(currencies=currencies):
                rows = self.lot_rows(currencies)
                original = copy.deepcopy(rows)
                lots = resolve_portfolio_lot_rows(rows, {}, {}, "unit-fixture")
                self.assertEqual(lots, original)
                self.assertEqual([lot["average_cost"] for lot in lots], [568.87, 395.59])
                self.assertEqual([lot["acquisition_value"] for lot in lots], [568.87, 71.96])
                aggregates = (
                    merge_portfolio_rows(rows)[0],
                    resolve_portfolio_rows(rows, {}, {}, "unit-fixture")[0],
                )
                for aggregate in aggregates:
                    for fx in (1.0, 1.35, 2.0):
                        analysis = enrich_portfolio_with_market_data(
                            [aggregate], {"INTU": {"current_price": 400, "currency": "USD"}},
                            {"CAD": 1, "USD": fx},
                        )[0]
                        result = compute_winner_protection(analysis)
                        self.assertEqual(analysis["cost_basis_aggregation_status"], "MIXED_CURRENCY_UNNORMALIZED")
                        self.assertEqual(analysis["cost_basis_currencies"], ["CAD", "USD"])
                        self.assertEqual(analysis["current_value_cad"], round(1.1819 * 400 * fx, 2))
                        for field in COST_FIELDS:
                            self.assertIsNone(analysis[field], field)
                            self.assertIsNone(result[field], field)
                        self.assertIsNone(result["unrealized_gain_percent"])
                        self.assertIsNone(result["unrealized_gain_amount"])
                        self.assert_mixed_reason(result["winner_protection_reason"])
                self.assertEqual(rows, original)

    def test_only_reason_changes_and_p3_and_sell_overlay_stay_conservative(self):
        mixed = self.analysis()
        missing = {**mixed, "cost_basis_aggregation_status": "UNAVAILABLE", "cost_basis_currencies": []}
        mixed_result = compute_winner_protection(mixed)
        missing_result = compute_winner_protection(missing)
        self.assert_mixed_reason(mixed_result.pop("winner_protection_reason"))
        self.assertEqual(missing_result.pop("winner_protection_reason"), MISSING_REASON)
        self.assertEqual(mixed_result, missing_result)
        self.assertEqual(mixed_result["winner_protection_status"], "NO_COST_DATA")
        self.assertEqual(mixed_result["winner_protection_action"], "HOLD")

        # Existing independent sell signals must neither be created nor suppressed.
        for decision in ("HOLD", "REVIEW_TRIM_25"):
            row = {**mixed, "sell_decision": decision, "recommended_action": decision}
            expected = {**row, **compute_winner_protection(row)}
            apply_winner_protection({"INTU": row})
            self.assertEqual(row, expected)
            apply_deep_averaging_down_context({"INTU": row}, mode="high-cagr")
            self.assertEqual(row["deep_averaging_down_status"], "UNKNOWN")
            self.assertTrue(row["deep_averaging_down_blocked"])
            self.assertIsNone(row["combined_position_return"])

    def test_no_position_does_not_acquire_mixed_cost_warning(self):
        analysis = self.analysis()
        analysis.update(shares=0, current_value=0, current_value_cad=0)
        result = compute_winner_protection(analysis)
        self.assertEqual(result["winner_protection_status"], "NO_POSITION")
        self.assertNotIn("devises mixtes", result["winner_protection_reason"])

    def test_zero_capital_reports_and_validation_exports_share_correct_reason(self):
        for kind in ("single", "missing", "mixed"):
            with self.subTest(kind=kind):
                row = self.analysis(("CAD", "CAD") if kind == "single" else ("CAD", "USD"), missing=kind == "missing")
                # A pre-existing review signal exercises the shared sell/thesis narrative.
                row.update(sell_decision="REVIEW_TRIM_25", recommended_action="REVIEW_TRIM_25",
                           sell_status="ORANGE", liquidation_status="ORANGE", mechanical_sell_signal="TRIM_25")
                apply_winner_protection({"INTU": row})
                reason = row["winner_protection_reason"]
                reports = self.root / kind / "reports"
                reports.mkdir(parents=True)
                # Synthetic archival sentinel only; never read or rewrite operational history.
                historical = reports / "decision_manifests" / "fixture-2026-09-01.json"
                historical.parent.mkdir()
                historical.write_text(json.dumps({
                    "run_id": "fixture-2026-09-01", "baseline_status": "BASELINE_V1_FORWARD_OBSERVATION",
                    "winner_protection_reason": MISSING_REASON,
                }), encoding="utf-8")
                archived_report = reports / "history" / "fixture-2026-09-01.md"
                archived_report.parent.mkdir()
                archived_report.write_text(MISSING_REASON, encoding="utf-8")
                sentinels = {path: path.read_bytes() for path in (historical, archived_report)}
                analyses, allocation = {"INTU": row}, {"allocations": []}
                original = copy.deepcopy((analyses, allocation))
                with patch("src.report_generator.DATA_DIR", self.root / kind / "data"):
                    generate_reports(reports, "high-cagr", 0, analyses, allocation, {}, [], [], [], [])
                self.assertEqual((analyses, allocation), original)
                for name in ("latest_report", "latest_report_compact"):
                    for suffix in (".md", ".html", "_high_cagr.md", "_high_cagr.html"):
                        text = (reports / f"{name}{suffix}").read_text(encoding="utf-8")
                        self.assertIn(reason, text)
                        if kind == "mixed":
                            self.assert_mixed_reason(text)
                        elif kind == "missing":
                            self.assertIn(MISSING_REASON, text)
                        else:
                            self.assertNotIn("Coût d’acquisition absent", text)
                for name, field in (("latest_scores", "winner_protection_reason"),
                                    ("latest_winner_protection_report", "winner_protection_reason"),
                                    ("latest_sell_validation_checklist", "winner_protection_check")):
                    for suffix in (".csv", "_high_cagr.csv"):
                        exported = read_csv_records(reports / f"{name}{suffix}")[0]
                        if kind == "single" and field == "winner_protection_check":
                            self.assertEqual(exported[field], "Aucune vente winner active.")
                        else:
                            self.assertIn(reason, exported[field])
                for path, before in sentinels.items():
                    self.assertEqual(path.read_bytes(), before)

    def test_dossier_and_validation_decisions_do_not_depend_on_reason_wording(self):
        row = self.analysis()
        row.update(sell_status="ORANGE", sell_decision="REVIEW_TRIM_25")
        apply_winner_protection({"INTU": row})
        legacy = {**row, "winner_protection_reason": MISSING_REASON}
        self.assertEqual(build_company_dossier(row), build_company_dossier(legacy))
        current_check = sell_validation_checklist_rows({"INTU": row})[0]
        legacy_check = sell_validation_checklist_rows({"INTU": legacy})[0]
        self.assert_mixed_reason(current_check.pop("winner_protection_check"))
        self.assertIn(MISSING_REASON, legacy_check.pop("winner_protection_check"))
        self.assertEqual(current_check, legacy_check)


if __name__ == "__main__":
    unittest.main()
