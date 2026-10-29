"""Synthetic scenario-specific NEW-contribution cost checks. Not live broker quotes."""
from __future__ import annotations

from copy import deepcopy
import unittest

from ai_native.new_capital_flow import prepare_new_capital_projection
from ai_native.session_bridge import complete_manual_session
from ai_native.reporting import render_report
from tests.test_ai_native_session_bridge import SessionBridgeTests
from tests.test_ai_native_reporting import ReportingTests


class AlternativeSuppliedCostsTests(unittest.TestCase):
    def setUp(self):
        self.fx = SessionBridgeTests()

    def plan(self):
        x = self.fx.new_contribution_inputs()
        x["alternative_allocations_pct"] = [
            {"ABC:TSX":"100"}, {"P-CASH":"100"}]
        return x

    @staticmethod
    def quote(dest, fee, funding="FROM_CONTRIBUTION"):
        charges = {kind:{"amount_base":"0.00","source_ref":"SYN-ALT-SOURCE"}
                   for kind in ("commission", "bid_ask_spread", "fx_conversion",
                                "purchase_tax", "other_fees")}
        charges["commission"]["amount_base"] = fee
        return {"charges_by_destination":{dest:charges},
                "cost_currency":"CAD","cost_quote_as_of":"2026-10-28",
                "analysis_as_of":"2026-10-28","funding":funding}

    def costs(self):
        x = self.fx.new_cost_inputs()
        x["alternative_cost_inputs"] = [
            self.quote("ABC:TSX", "10.00"),
            self.quote("P-CASH", "0.00")]
        return x

    def project(self, plan=None, costs=None):
        return prepare_new_capital_projection(
            analysis_id="CASE-A",analysis_as_of="2026-10-28",
            portfolio_as_of="2026-10-28",
            contribution_inputs=self.plan() if plan is None else plan,
            cost_inputs=self.costs() if costs is None else costs)

    def test_distinct_quotes_and_cost_sensitivity_do_not_change_baseline(self):
        plan, costs = self.plan(), self.costs()
        oldplan, oldcosts = deepcopy(plan), deepcopy(costs)
        out = self.project(plan, costs)
        self.assertEqual(plan, oldplan)
        self.assertEqual(costs, oldcosts)
        self.assertEqual(out["funded_contribution_private"]["one_time_supplied_cost_share_pct"], "0.5000")
        variants = out["report_summary_private"]["conditional_alternative_costs_private"]
        self.assertEqual(variants["status"], "SEPARATELY_QUOTED_CONDITIONAL_ALTERNATIVES")
        self.assertEqual([r["one_time_supplied_cost_share_pct"] for r in variants["scenarios"]],
                         ["1.0000", "0.0000"])
        self.assertEqual(variants["scenarios"][0]["conditional_funded_after_scoped_cash_pct"], "0.00")
        self.assertEqual(variants["scenarios"][1]["conditional_funded_after_scoped_cash_pct"], "50.00")
        self.assertEqual(out["alternative_cost_details_private"][0][
            "supplied_costs_private"]["total_supplied_costs_base"], "10.00")
        self.assertEqual(out["alternative_cost_details_private"][1][
            "supplied_costs_private"]["total_supplied_costs_base"], "0.00")
        self.assertEqual(out["execution_status"], "UNAVAILABLE_NOT_EXECUTION_CERTIFIED")

    def test_private_pi_only_cc_report_shows_bounded_percentages_not_quotes(self):
        out = complete_manual_session(
            self.fx.request(research_needed=False, portfolio_needed=True),
            pi_delta=self.fx.pi(), contribution_inputs=self.plan(),
            cost_inputs=self.costs())
        report = out["final_report_private"]
        self.assertIn("Alternative 1 with its OWN supplied fixed costs", report)
        self.assertIn("one-time purchase-cost share 1.0000%", report)
        self.assertIn("Alternative 2 with its OWN supplied fixed costs", report)
        self.assertIn("scoped cash 50.00%", report)
        for secret in ("SYN-ALT-SOURCE", "10.00", "1000.00", "995.00"):
            self.assertNotIn(secret, report)
        self.assertEqual(out["storage"], "NONE")

    def test_incomplete_separately_quoted_alt_stays_unavailable(self):
        x = self.costs()
        del x["alternative_cost_inputs"][0]["charges_by_destination"]["ABC:TSX"]["purchase_tax"]
        out = self.project(costs=x)
        a, b = out["report_summary_private"]["conditional_alternative_costs_private"]["scenarios"]
        self.assertEqual(a["cost_status"], "INCOMPLETE_COST_INPUTS")
        self.assertEqual(a["funded_status"], "UNAVAILABLE_COST_INPUTS")
        self.assertIsNone(a["one_time_supplied_cost_share_pct"])
        self.assertEqual(b["one_time_supplied_cost_share_pct"], "0.0000")

    def test_count_destination_and_quote_date_mismatch_fail_closed(self):
        for bad in ([], [self.quote("ABC:TSX","10.00")],
                    "not-a-list", [{"stray":"object"}, {}]):
            with self.subTest(value=bad):
                c = self.costs()
                c["alternative_cost_inputs"] = bad
                with self.assertRaises(ValueError):
                    self.project(costs=c)
        c = self.costs()
        c["alternative_cost_inputs"][1] = self.quote("ABC:TSX","0.00")
        with self.assertRaisesRegex(ValueError, "DESTINATION_MISMATCH"):
            self.project(costs=c)
        c = self.costs()
        c["alternative_cost_inputs"][0]["analysis_as_of"] = "2026-10-27"
        with self.assertRaisesRegex(ValueError,"ALTERNATIVE_COST_QUOTE_SCHEMA_OR_DATE"):
            self.project(costs=c)

    def test_gross_alternatives_without_new_quotes_keep_original_contract(self):
        c = self.fx.new_cost_inputs()
        out = self.project(costs=c)
        self.assertIsNone(out["report_summary_private"]["conditional_alternative_costs_private"])
        self.assertIsNone(out["alternative_cost_details_private"])
        self.assertEqual(out["report_summary_private"]["gross_alternatives_private"][
            "status"], "GROSS_ALTERNATIVES_ONLY_NOT_NET")

    def test_report_cannot_claim_forged_net_quote_or_extra_cash(self):
        summary = self.project()["report_summary_private"]
        for key, val in (
            ("authority", "BROKER_CERTIFIED"),
            ("status", "NET_EXPECTED_RETURN"),
        ):
            with self.subTest(key=key):
                bad = deepcopy(summary)
                bad["conditional_alternative_costs_private"][key] = val
                with self.assertRaisesRegex(ValueError,"CONTRIBUTION_REPORT_ALT_COST"):
                    render_report(ReportingTests().packet(
                        analysis_id="CASE-A", new_contribution_summary_private=bad))
        for key, val in (
            ("scenario_index", 2),
            ("one_time_supplied_cost_share_pct", "NaN"),
            ("conditional_funded_after_scoped_cash_pct", "101.00"),
            ("cost_status", "EXECUTION_CERTIFIED"),
        ):
            with self.subTest(key=key):
                bad = deepcopy(summary)
                bad["conditional_alternative_costs_private"]["scenarios"][0][key] = val
                with self.assertRaisesRegex(ValueError,"CONTRIBUTION_REPORT_ALT_COST"):
                    render_report(ReportingTests().packet(
                        analysis_id="CASE-A", new_contribution_summary_private=bad))

    def test_incomplete_scope_never_produces_alternative_cost_figures(self):
        out = self.project(plan={**self.plan(), "scope_complete":False})
        summary = out["report_summary_private"]
        self.assertEqual(summary["gross_status"], "UNAVAILABLE")
        self.assertIsNone(summary["gross_alternatives_private"])
        self.assertIsNone(summary["conditional_alternative_costs_private"])


if __name__ == "__main__":
    unittest.main()
