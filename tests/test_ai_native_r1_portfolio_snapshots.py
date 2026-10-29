"""Synthetic private on-demand portfolio snapshot follow-ups; no market-return attribution."""
from __future__ import annotations

from copy import deepcopy
from io import StringIO
import json
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

    def test_missing_currency_in_prior_or_current_never_produces_monetary_change(self):
        for prior_currency, current_currency in (
            ("XXX", "CAD"), ("UNK", "UNK"), ("CAD", "XXX"),
        ):
            with self.subTest(currencies=(prior_currency, current_currency)):
                old = self.previous(currency=prior_currency)
                old["positions"][0]["currency"] = prior_currency
                now = self.current(currency=current_currency)
                now["positions"][0]["currency"] = current_currency
                out = self.compare(old=old, now=now)
                self.assertEqual(out["status"], "UNAVAILABLE_INCOMPLETE_SNAPSHOT_SCOPE")
                self.assertIsNone(out["rows_private"])
                self.assertIsNone(out["cash_weight_change_pp"])
                self.assertIsNone(out["largest_absolute_security_weight_shift_pp"])

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

    def test_private_cli_report_and_redacted_status_remain_user_initiated(self):
        from scripts.r1_manual_session_cli import main
        payload = {
            "request": self.request(),
            "pi_delta": self.fx.pi(),
            "observation_inputs": self.current(),
            "prior_portfolio_observation_inputs": self.previous(),
        }
        original = deepcopy(payload)
        output, error = StringIO(), StringIO()
        code = main(["--output", "report"], instream=StringIO(json.dumps(payload)),
                    outstream=output, errstream=error)
        self.assertEqual((code, error.getvalue()), (0, ""))
        self.assertIn("Largest absolute security-line weight shift: 25.00",
                      output.getvalue())
        self.assertNotIn("ABC:TSX", output.getvalue())
        self.assertNotIn("SCOPE-A", output.getvalue())
        self.assertEqual(payload, original)
        output, error = StringIO(), StringIO()
        code = main(["--output", "status"], instream=StringIO(json.dumps(payload)),
                    outstream=output, errstream=error)
        self.assertEqual((code, error.getvalue()), (0, ""))
        status = json.loads(output.getvalue())
        self.assertEqual(status["status"], "PI_ONLY_CONDITIONAL_REPORT_ASSEMBLED")
        self.assertNotIn("portfolio_snapshot_comparison_private", output.getvalue())
        self.assertNotIn("ABC:TSX", output.getvalue())
        self.assertEqual(status["readiness"], "NOT_EVALUATED")

    def percentage_only(self, old_value="80.00", new_value="75.00"):
        """Both screenshots have the same visible title, but no cash or amounts."""
        prior, current = self.previous(), self.current()
        for args, pct in ((prior, old_value), (current, new_value)):
            args["currency"] = "UNKNOWN"
            args["cash_base"] = None
            args["cash_visibility"] = "NOT_VISIBLE"
            args["same_currency_basis_confirmed_by_caller"] = False
            row = args["positions"][0]
            row["currency"] = None
            row["market_value_base"] = None
            row["displayed_weight_pct"] = pct
            row["displayed_weight_visibility"] = "VERIFIED_VISIBLE"
            row["field_statuses"]["market_value_base"] = "NOT_VISIBLE"
            row["field_statuses"]["currency"] = "NOT_VISIBLE"
        return prior, current

    def test_ui_only_unknown_named_account_is_not_a_comparable_account(self):
        old, current = self.percentage_only()
        for source in (old, current):
            source["account_scope"] = "UNKNOWN"
            source["positions"][0]["account_scope"] = "UNKNOWN"
        out = self.compare(old=old, now=current)
        self.assertEqual(out["status"], "UNAVAILABLE_INCOMPLETE_SNAPSHOT_SCOPE")
        self.assertIsNone(out["rows_private"])
        self.assertIsNone(out["largest_absolute_security_weight_shift_pp"])
        self.assertIsNone(out["cash_weight_change_pp"])

    def test_ui_only_placeholder_security_does_not_become_same_title(self):
        for placeholder in ("UNKNOWN", "NOT_VISIBLE", "TBD"):
            with self.subTest(placeholder=placeholder):
                old, current = self.percentage_only()
                for source in (old, current):
                    source["positions"][0]["security_id"] = placeholder
                out = self.compare(old=old, now=current)
                self.assertEqual(out["status"], "UNAVAILABLE_INCOMPLETE_SNAPSHOT_SCOPE")
                self.assertIsNone(out["rows_private"])

    def test_unknown_currency_ui_only_comparison_is_reachable_not_monetary(self):
        # The source transcript may have raw source weights but NO currency,
        # cash, FX, account-base denominator or original purchase records.
        old, current = self.percentage_only("50.05", "50.25")
        before = deepcopy((old, current))
        prior_p = prepare_observation_ledger(**old)
        current_p = prepare_observation_ledger(**current)
        self.assertEqual(prior_p["currency"], "UNKNOWN")
        self.assertEqual(current_p["currency"], "UNKNOWN")
        self.assertIsNone(prior_p["known_scope_weights_pct"])
        self.assertIsNone(current_p["known_scope_weights_pct"])
        result = self.compare(old=old, now=current)
        self.assertEqual(result["status"],
                         "OBSERVED_UI_WEIGHT_CHANGE_ONLY_NO_MONETARY_DENOMINATOR")
        self.assertEqual(result["largest_absolute_security_weight_shift_pp"], "0.20")
        self.assertEqual(result["rows_private"][0]["weight_change_pp"], "0.20")
        self.assertIsNone(result["cash_weight_change_pp"])
        self.assertEqual((old, current), before)

    def test_different_known_account_currencies_not_ui_comparable(self):
        old, current = self.percentage_only()
        old["currency"] = "USD"
        current["currency"] = "CAD"
        # Both displayed values exist; the known-basis contradiction still
        # blocks even the weaker, UI-only history comparison.
        with self.assertRaisesRegex(
                ValueError, "SNAPSHOT_ACCOUNT_OR_CURRENCY_BASIS_CHANGED"):
            self.compare(old=old, now=current)

    def test_unknown_currency_ui_view_never_bypasses_named_account_scope(self):
        old, current = self.percentage_only()
        current["account_scope"] = "ANOTHER-ACCOUNT"
        with self.assertRaisesRegex(
                ValueError, "SNAPSHOT_ACCOUNT_OR_CURRENCY_BASIS_CHANGED"):
            self.compare(old=old, now=current)

    def test_separately_supplied_unknown_currency_with_no_ui_stays_unavailable(self):
        old, current = self.previous(currency="UNK"), self.current(currency="XXX")
        old["positions"][0]["currency"] = "UNK"
        current["positions"][0]["currency"] = "XXX"
        x = self.compare(old=old, now=current)
        self.assertEqual(x["status"], "UNAVAILABLE_INCOMPLETE_SNAPSHOT_SCOPE")
        self.assertIsNone(x["rows_private"])
        self.assertEqual(x["reason_codes"],
                         ["PRIOR_SCOPE_INCOMPLETE", "CURRENT_SCOPE_INCOMPLETE"])
        self.assertIsNone(x["cash_weight_change_pp"])

    def test_percentage_only_source_ui_deltas_without_cash_or_money(self):
        old, current = self.percentage_only("80.00", "75.00")
        original = deepcopy((old, current))
        result = self.compare(old=old, now=current)
        self.assertEqual((old, current), original)
        self.assertEqual(result["status"],
                         "OBSERVED_UI_WEIGHT_CHANGE_ONLY_NO_MONETARY_DENOMINATOR")
        self.assertEqual(result["matched_instrument_count"], 1)
        self.assertEqual(result["largest_absolute_security_weight_shift_pp"], "5.00")
        self.assertEqual(result["rows_private"][0]["weight_change_pp"], "-5.00")
        self.assertEqual(result["reason_codes"], ["MONETARY_DENOMINATOR_NOT_VERIFIED"])
        self.assertIsNone(result["cash_weight_change_pp"])
        self.assertEqual(result["performance_or_transaction_inference"], "NONE")

    def test_percent_only_unmatched_securities_do_not_get_inferred_zero_weights(self):
        old, current = self.percentage_only()
        current["positions"][0]["security_id"] = "DIFFERENT:TSX"
        out = self.compare(old=old, now=current)
        self.assertEqual(out["status"], "UNAVAILABLE_INCOMPLETE_SNAPSHOT_SCOPE")
        self.assertIsNone(out["rows_private"])
        self.assertIsNone(out["largest_absolute_security_weight_shift_pp"])

    def test_percent_only_missing_identity_visibility_or_unconfirmed_scope_blocks(self):
        for change in ("hidden_title", "hidden_scope", "incomplete_scope",
                       "unconfirmed_access", "missing_display", "unknown_capture"):
            with self.subTest(change=change):
                old, current = self.percentage_only()
                row = current["positions"][0]
                if change == "hidden_title":
                    row["field_statuses"]["security_id"] = "UNCERTAIN"
                elif change == "hidden_scope":
                    row["field_statuses"]["account_scope"] = "NOT_VISIBLE"
                elif change == "incomplete_scope":
                    current["scope_complete"] = False
                elif change == "unconfirmed_access":
                    current["source_access_confirmed_by_caller"] = False
                elif change == "missing_display":
                    row["displayed_weight_pct"] = None
                    row["displayed_weight_visibility"] = "NOT_VISIBLE"
                else:
                    current["captured_at"] = "UNKNOWN"
                out = self.compare(old=old, now=current)
                self.assertEqual(out["status"], "UNAVAILABLE_INCOMPLETE_SNAPSHOT_SCOPE")
                self.assertIsNone(out["rows_private"])

    def test_pi_only_private_report_shows_ui_change_without_monetary_claims(self):
        old, current = self.percentage_only("50.05", "50.25")
        out = complete_manual_session(
            self.request(), pi_delta=self.fx.pi(),
            observation_inputs=current, prior_portfolio_observation_inputs=old)
        self.assertEqual(out["portfolio_snapshot_comparison_private"]["status"],
                         "OBSERVED_UI_WEIGHT_CHANGE_ONLY_NO_MONETARY_DENOMINATOR")
        report = out["final_report_private"]
        self.assertIn("largest raw UI difference 0.20 percentage points", report)
        self.assertIn("Monetary account denominator and cash weight are UNKNOWN", report)
        self.assertNotIn("ABC:TSX", report)
        self.assertNotIn("SCOPE-A", report)
        self.assertNotIn("scoped cash weight change", report)
        self.assertEqual(out["readiness"], "NOT_EVALUATED")

    def test_raw_ui_totals_above_hundred_are_not_normalized(self):
        old, current = self.percentage_only("50.05", "50.25")
        for args, second_pct in ((old, "50.25"), (current, "50.05")):
            row = deepcopy(args["positions"][0])
            row["p_id"] = "P-2"
            row["security_id"] = "OTHER:TSX"
            row["displayed_weight_pct"] = second_pct
            args["positions"].append(row)
        out = self.compare(old=old, now=current)
        self.assertEqual(out["status"],
                         "OBSERVED_UI_WEIGHT_CHANGE_ONLY_NO_MONETARY_DENOMINATOR")
        self.assertEqual(out["matched_instrument_count"], 2)
        self.assertEqual(out["largest_absolute_security_weight_shift_pp"], "0.20")
        self.assertEqual(
            prepare_observation_ledger(**current)["displayed_weight_summary_private"][
                "displayed_weight_sum_pct"], "100.30")
        self.assertEqual(out["cash_weight_change_pp"], None)

    def test_old_ui_only_current_monetary_basis_still_uses_source_ui(self):
        old, current = self.percentage_only("80.00", "75.00")
        # The newer statement independently supplies the actual account
        # currency, all amounts/cash and source-visible UI percentages.
        current["currency"] = "CAD"
        current["cash_base"] = "100.00"
        current["cash_visibility"] = "VERIFIED_VISIBLE"
        current["same_currency_basis_confirmed_by_caller"] = True
        row = current["positions"][0]
        row["currency"] = "CAD"
        row["market_value_base"] = "300.00"
        row["field_statuses"]["currency"] = "VERIFIED_VISIBLE"
        row["field_statuses"]["market_value_base"] = "VERIFIED_VISIBLE"
        obs = prepare_observation_ledger(**current)
        self.assertIsNotNone(obs["known_scope_weights_pct"])
        out = self.compare(old=old, now=current)
        self.assertEqual(out["status"],
                         "OBSERVED_UI_WEIGHT_CHANGE_ONLY_NO_MONETARY_DENOMINATOR")
        self.assertIsNone(out["cash_weight_change_pp"])
        self.assertEqual(out["largest_absolute_security_weight_shift_pp"], "5.00")
        packet = ReportingTests().packet(
            analysis_id="CASE-A", kind="FOLLOWUP", prior_analysis_id="PRIOR-CASE",
            changes=[], portfolio_observation_private=obs,
            portfolio_snapshot_comparison_private=out)
        report = render_report(packet)
        self.assertIn("largest raw UI difference 5.00 percentage points", report)
        self.assertNotIn("scoped cash weight change", report)

    def test_ir_pi_followup_preserves_ui_only_status_and_private_annex(self):
        old, current = self.percentage_only()
        ir = self.fx.ir()
        out = complete_manual_session(
            self.request(research_needed=True), ir_capsule=ir,
            pi_delta=self.fx.pi(forwarded_ir=deepcopy(ir)),
            observation_inputs=current, prior_portfolio_observation_inputs=old)
        self.assertEqual(out["integrated_private"]["portfolio_snapshot_comparison_private"],
                         out["portfolio_snapshot_comparison_private"])
        self.assertIn("largest raw UI difference", out["final_report_private"])
        self.assertNotIn("ABC:TSX", out["final_report_private"])
        self.assertNotIn("portfolio_snapshot_comparison_private",
                         str(out["integrated_private"]["memory_proposal_nonprivate"]))

    def test_report_cannot_upgrade_ui_only_to_cash_return_or_forged_current_pct(self):
        old, current = self.percentage_only()
        obs = prepare_observation_ledger(**current)
        snap = self.compare(old=old, now=current)
        packet = ReportingTests().packet(
            analysis_id="CASE-A", kind="FOLLOWUP", prior_analysis_id="PRIOR-CASE",
            changes=[], portfolio_observation_private=obs,
            portfolio_snapshot_comparison_private=snap)
        self.assertIn("largest raw UI difference", render_report(packet))
        for field, value in (
            ("cash_weight_change_pp", "-5.00"),
            ("status", "DESCRIPTIVE_SCOPED_WEIGHT_CHANGE_NOT_RETURN"),
            ("matched_instrument_count", 3),
        ):
            with self.subTest(field=field):
                bad = deepcopy(packet)
                bad["portfolio_snapshot_comparison_private"][field] = value
                with self.assertRaisesRegex(ValueError, "SNAPSHOT_REPORT_"):
                    render_report(bad)
        bad = deepcopy(packet)
        bad["portfolio_snapshot_comparison_private"]["rows_private"][0][
            "current_weight_pct"] = "99.00"
        bad["portfolio_snapshot_comparison_private"]["rows_private"][0][
            "weight_change_pp"] = "19.00"
        bad["portfolio_snapshot_comparison_private"][
            "largest_absolute_security_weight_shift_pp"] = "19.00"
        with self.assertRaisesRegex(ValueError, "SNAPSHOT_REPORT_UI_VISIBLE_PARITY_INVALID"):
            render_report(bad)

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
