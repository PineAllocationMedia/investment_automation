"""Synthetic private on-demand portfolio snapshot follow-ups; no market-return attribution."""
from __future__ import annotations

from copy import deepcopy
import unittest

from ai_native.portfolio_observation import prepare_observation_ledger
from ai_native.portfolio_snapshot_comparison import compare_private_portfolio_snapshots
from ai_native.session_bridge import complete_manual_session
from ai_native.reporting import render_report
from tests.test_ai_native_session_bridge import SessionBridgeTests
from tests.test_ai_native_portfolio_observation import ObservationTests
from tests.test_ai_native_reporting import ReportingTests


class PrivatePortfolioSnapshotFollowupTests(unittest.TestCase):
    def setUp(self):
        self.fx = SessionBridgeTests()
        self.obs = ObservationTests()

    def previous(self, **patch):
        old = self.obs.kwargs(
            analysis_id="PRIOR-CASE", observed_on="2026-10-27",
            analysis_as_of="2026-10-27",
            captured_at="2026-10-27T10:00:00-04:00",
            cash_base="200.00")
        old["positions"][0]["market_value_base"] = "200.00"
        old.update(patch)
        return old

    def current(self, **patch):
        now = self.obs.kwargs(
            analysis_id="CASE-A", analysis_as_of="2026-10-28")
        now.update(patch)
        return now

    def compare(self, old=None, now=None):
        return compare_private_portfolio_snapshots(
            analysis_id="CASE-A", analysis_as_of="2026-10-28",
            prior_analysis_id="PRIOR-CASE",
            current_observation=prepare_observation_ledger(
                **(self.current() if now is None else now)),
            prior_observation_inputs=self.previous() if old is None else old)

    def request(self, research_needed=False):
        return self.fx.request(
            research_needed=research_needed, portfolio_needed=True,
            kind="FOLLOWUP", prior_analysis_id="PRIOR-CASE")

    def test_exact_synthetic_weight_and_cash_changes_are_not_returns(self):
        x = self.compare()
        self.assertEqual(x["status"], "DESCRIPTIVE_SCOPED_WEIGHT_CHANGE_NOT_RETURN")
        self.assertEqual(x["matched_instrument_count"], 1)
        self.assertEqual(x["newly_visible_count"], 0)
        self.assertEqual(x["no_longer_visible_count"], 0)
        self.assertEqual(x["largest_absolute_security_weight_shift_pp"], "25.00")
        self.assertEqual(x["cash_weight_change_pp"], "-25.00")
        self.assertEqual(x["rows_private"][0]["security_id_private"], "ABC:TSX")
        self.assertEqual(x["rows_private"][0]["weight_change_pp"], "25.00")
        self.assertEqual(x["performance_or_transaction_inference"], "NONE")

    def test_appeared_and_disappeared_lines_not_interpreted_as_trades(self):
        curr = self.current()
        curr["positions"][0]["security_id"] = "NEW:TSX"
        x = self.compare(now=curr)
        self.assertEqual(x["newly_visible_count"], 1)
        self.assertEqual(x["no_longer_visible_count"], 1)
        self.assertEqual(x["matched_instrument_count"], 0)
        self.assertEqual(x["largest_absolute_security_weight_shift_pp"], "75.00")

    def test_incomplete_source_scope_blocks_all_numeric_deltas(self):
        for old, now, codes in (
            (self.previous(scope_complete=False), self.current(), ["PRIOR_SCOPE_INCOMPLETE"]),
            (self.previous(), self.current(cash_visibility="NOT_VISIBLE"),
             ["CURRENT_SCOPE_INCOMPLETE"]),
            (self.previous(scope_complete=False), self.current(scope_complete=False),
             ["PRIOR_SCOPE_INCOMPLETE", "CURRENT_SCOPE_INCOMPLETE"]),
        ):
            with self.subTest(codes=codes):
                x = self.compare(old=old, now=now)
                self.assertEqual(x["status"], "UNAVAILABLE_INCOMPLETE_SNAPSHOT_SCOPE")
                self.assertEqual(x["reason_codes"], codes)
                self.assertIsNone(x["rows_private"])
                self.assertIsNone(x["cash_weight_change_pp"])

    def test_prior_date_account_currency_identity_or_cutoff_mismatch_rejected(self):
        for prior, error in (
            (self.previous(observed_on="2026-10-28",analysis_as_of="2026-10-28",
                           captured_at="2026-10-28T10:00:00-04:00"), "DATES_NOT_STRICTLY_ORDERED"),
            (self.previous(account_scope="WRONG"), "ACCOUNT_OR_CURRENCY_BASIS_CHANGED"),
            (self.previous(currency="USD"), "ACCOUNT_OR_CURRENCY_BASIS_CHANGED"),
            (self.previous(analysis_id="FORGED"), "PRIOR_ID_OR_SCOPE_INVALID"),
            (self.previous(private_scope=False), "PRIOR_ID_OR_SCOPE_INVALID"),
            (self.previous(analysis_as_of="2026-10-29"), "ORIGINAL_CUTOFF_OR_CURRENCY_UNKNOWN"),
        ):
            with self.subTest(error=error), self.assertRaisesRegex(ValueError, error):
                self.compare(old=prior)

    def test_pi_only_followup_keeps_private_ids_out_of_short_cc_report(self):
        old, now = self.previous(), self.current()
        saved_old, saved_now = deepcopy(old), deepcopy(now)
        out = complete_manual_session(
            self.request(), pi_delta=self.fx.pi(), observation_inputs=now,
            prior_portfolio_observation_inputs=old)
        self.assertEqual(old, saved_old)
        self.assertEqual(now, saved_now)
        self.assertEqual(out["status"], "PI_ONLY_CONDITIONAL_REPORT_ASSEMBLED")
        report = out["final_report_private"]
        self.assertIn("Observed 2026-10-27 vs 2026-10-28", report)
        self.assertIn("Largest absolute security-line weight shift: 25.00", report)
        self.assertIn("scoped cash weight change: -25.00", report)
        self.assertNotIn("ABC:TSX", report)
        self.assertNotIn("SCOPE-A", report)
        self.assertNotIn("200.00", report)
        self.assertEqual(out["portfolio_snapshot_comparison_private"]["matched_instrument_count"], 1)
        self.assertEqual(out["storage"], "NONE")

    def test_ir_pi_followup_carries_same_private_annex_without_memory_leak(self):
        ir = self.fx.ir()
        out = complete_manual_session(
            self.request(research_needed=True), ir_capsule=ir,
            pi_delta=self.fx.pi(forwarded_ir=deepcopy(ir)),
            observation_inputs=self.current(),
            prior_portfolio_observation_inputs=self.previous())
        self.assertEqual(out["status"], "M7A_COMPONENT_ASSEMBLED_NOT_END_TO_END_ACCEPTANCE")
        self.assertEqual(out["integrated_private"]["portfolio_snapshot_comparison_private"],
                         out["portfolio_snapshot_comparison_private"])
        self.assertIn("25.00 percentage points", out["final_report_private"])
        self.assertNotIn("ABC:TSX", out["final_report_private"])
        memory = str(out["integrated_private"]["memory_proposal_nonprivate"])
        self.assertNotIn("SCOPE-A", memory)
        self.assertNotIn("portfolio_snapshot_comparison_private", memory)

    def test_explicit_followup_and_current_private_pi_required(self):
        requests = [
            self.fx.request(research_needed=False,portfolio_needed=True),
            self.fx.request(research_needed=True,portfolio_needed=False,
                            kind="FOLLOWUP",prior_analysis_id="PRIOR-CASE"),
        ]
        for request in requests:
            with self.subTest(request=request), self.assertRaisesRegex(ValueError,
                                                                       "EXPLICIT_PI_FOLLOWUP"):
                complete_manual_session(
                    request, prior_portfolio_observation_inputs=self.previous())
        with self.assertRaisesRegex(ValueError,"REQUIRES_CURRENT_PRIVATE_OBSERVATION"):
            complete_manual_session(
                self.request(), pi_delta=self.fx.pi(),
                prior_portfolio_observation_inputs=self.previous())

    def test_report_refuses_forged_confidentiality_status_and_percentages(self):
        current = prepare_observation_ledger(**self.current())
        packet = ReportingTests().packet(
            analysis_id="CASE-A",kind="FOLLOWUP", prior_analysis_id="PRIOR-CASE",
            changes=[],portfolio_observation_private=current,
            portfolio_snapshot_comparison_private=self.compare())
        self.assertIn("snapshot comparison", render_report(packet))
        for key, value in (
            ("privacy", "PUBLIC"),
            ("largest_absolute_security_weight_shift_pp", "101.00"),
            ("cash_weight_change_pp", "NaN"),
            ("matched_instrument_count", 8),
            ("status", "CERTIFIED_RETURN"),
        ):
            with self.subTest(key=key):
                forged = deepcopy(packet)
                forged["portfolio_snapshot_comparison_private"][key] = value
                with self.assertRaisesRegex(ValueError, "SNAPSHOT_REPORT_"):
                    render_report(forged)
        packet["kind"] = "DECISION"
        with self.assertRaisesRegex(ValueError, "SNAPSHOT_REPORT_ID_OR_AUTHORITY_INVALID"):
            render_report(packet)


if __name__ == "__main__":
    unittest.main()
