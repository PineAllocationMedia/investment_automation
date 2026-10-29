"""Synthetic R1 private visible-percentage handoff; never a market-value inference."""
from __future__ import annotations

from copy import deepcopy
import unittest

from ai_native.portfolio_observation import prepare_observation_ledger
from ai_native.work_blossom_adapter import prepare_work_blossom_observation
from ai_native.session_bridge import complete_manual_session
from ai_native.reporting import render_report
from tests.test_ai_native_work_blossom_session_bridge import BlossomSessionBridgeTests
from tests.test_ai_native_reporting import ReportingTests


class PrivateVisiblePercentageTests(unittest.TestCase):
    def setUp(self):
        self.fx = BlossomSessionBridgeTests()

    def percent_only(self):
        source = self.fx.report(currency="UNKNOWN", cash_base=None,
                                cash_visibility="NOT_VISIBLE")
        source["coverage_evidence"]["same_currency_basis_visible"] = False
        source["positions"][0].update({
            "market_value_base": None,
            "currency": None,
            "displayed_weight_pct": "100.30",
            "displayed_weight_visibility": "VERIFIED_VISIBLE",
            "field_statuses": {
                "security_id": "VERIFIED_VISIBLE",
                "market_value_base": "NOT_VISIBLE",
                "currency": "NOT_VISIBLE",
                "account_scope": "VERIFIED_VISIBLE",
            },
        })
        return source

    def test_percent_only_work_handoff_keeps_sum_unmodified_and_blocks_portfolio_math(self):
        source = self.percent_only()
        before = deepcopy(source)
        capture = prepare_work_blossom_observation(source)
        self.assertEqual(source, before)
        ledger = capture["p_ledger_private"]
        self.assertEqual(ledger["status"], "OBSERVATION_LEDGER_ONLY")
        self.assertEqual(ledger["currency"], "UNKNOWN")
        self.assertIsNone(ledger["scope_total_base"])
        self.assertIsNone(ledger["known_scope_weights_pct"])
        self.assertIn("ACCOUNT_CURRENCY_UNKNOWN", ledger["missing_or_qualified"])
        self.assertIn("CASH_NOT_VISIBLE_OR_UNQUANTIFIED", ledger["missing_or_qualified"])
        self.assertEqual(ledger["displayed_weight_summary_private"]["displayed_weight_sum_pct"], "100.30")
        self.assertEqual(ledger["p_ledger_private"][0]["displayed_weight_pct_private"], "100.30")
        self.assertEqual(ledger["portfolio_room_status"], "ROOM_UNAVAILABLE")

    def test_pi_only_cc_report_shows_only_aggregate_not_private_security_or_account(self):
        source = self.percent_only()
        out = complete_manual_session(
            self.fx.pi_only(), pi_delta=self.fx.fx.pi(),
            work_blossom_inputs=source)
        report = out["final_report_private"]
        self.assertIn("raw displayed total 100.30%", report)
        self.assertIn("No rounding reconciliation or normalization", report)
        self.assertIn("INCOMPLETE_NO_DERIVED_WEIGHTS", report)
        self.assertNotIn("SYNTHETIC-HOLDING:TSX", report)
        self.assertNotIn("SYNTHETIC_ACCOUNT_SECRET", report)
        self.assertIsNone(out["portfolio_observation_private"]["scope_total_base"])
        self.assertEqual(out["readiness"], "NOT_EVALUATED")

    def test_incomplete_display_rows_do_not_claim_portfolio_total(self):
        source = self.percent_only()
        second = deepcopy(source["positions"][0])
        second["p_id"] = "P2"
        second["displayed_weight_pct"] = None
        second["displayed_weight_visibility"] = "NOT_VISIBLE"
        source["positions"].append(second)
        capture = prepare_work_blossom_observation(source)
        summary = capture["p_ledger_private"]["displayed_weight_summary_private"]
        self.assertEqual(summary["visible_count"], 1)
        self.assertEqual(summary["position_row_count"], 2)
        self.assertIsNone(summary["displayed_weight_sum_pct"])

    def test_reported_pct_never_overwrites_dollar_derived_weights(self):
        source = self.fx.report()
        source["positions"][0]["displayed_weight_pct"] = "79.50"
        source["positions"][0]["displayed_weight_visibility"] = "VERIFIED_VISIBLE"
        ledger = prepare_work_blossom_observation(source)["p_ledger_private"]
        self.assertEqual(ledger["status"], "SCOPED_WEIGHTS_DERIVED_FROM_CALLER_VISIBLE_DATA")
        self.assertEqual(ledger["known_scope_weights_pct"]["P1"], "80.00")
        self.assertEqual(ledger["displayed_weight_summary_private"]["displayed_weight_sum_pct"], "79.50")
        self.assertEqual(ledger["scope_total_base"], "100.00")

    def test_invalid_display_values_and_visibility_rejected(self):
        for bad in ("NaN", "-1", "101", "100.001", "1e2", "3.141", "1,5", 30, ""):
            with self.subTest(value=bad):
                source = self.percent_only()
                source["positions"][0]["displayed_weight_pct"] = bad
                with self.assertRaises(ValueError):
                    prepare_work_blossom_observation(source)
        source = self.percent_only()
        source["positions"][0]["displayed_weight_visibility"] = "NOT_VISIBLE"
        with self.assertRaisesRegex(ValueError, "VISIBILITY_VALUE_MISMATCH"):
            prepare_work_blossom_observation(source)

    def test_forged_displayed_total_is_rejected_before_reporting(self):
        source = self.percent_only()
        ledger = prepare_work_blossom_observation(source)["p_ledger_private"]
        forged = deepcopy(ledger)
        forged["displayed_weight_summary_private"]["displayed_weight_sum_pct"] = "100.00"
        packet = ReportingTests().packet(
            analysis_id="CASE-A", portfolio_observation_private=forged)
        with self.assertRaisesRegex(ValueError, "REPORT_DISPLAYED_WEIGHT_SUM_INVALID"):
            render_report(packet)


if __name__ == "__main__":
    unittest.main()
