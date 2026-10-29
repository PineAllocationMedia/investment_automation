"""R1 bounded gross-only alternative new-contribution comparisons.

All scenario inputs are synthetic and caller supplied; no prices, net alternatives,
strategy allocation policy, sources, trades, brokerage data or persistent writes.
"""
from __future__ import annotations

from copy import deepcopy
import unittest

from ai_native.new_capital_flow import prepare_new_capital_projection
from ai_native.reporting import render_report
from ai_native.session_bridge import complete_manual_session
from tests.test_ai_native_session_bridge import SessionBridgeTests
from tests.test_ai_native_reporting import ReportingTests


class GrossAlternativeContributionTests(unittest.TestCase):
    def setUp(self):
        self.fx = SessionBridgeTests()

    def plan(self, **patch):
        data = self.fx.new_contribution_inputs()
        data["alternative_allocations_pct"] = [
            {"ABC:TSX": "100"}, {"P-CASH": "100"},
        ]
        data.update(patch)
        return data

    def project(self, plan=None, costs=None):
        return prepare_new_capital_projection(
            analysis_id="CASE-A", analysis_as_of="2026-10-28",
            portfolio_as_of="2026-10-28",
            contribution_inputs=self.plan() if plan is None else plan,
            cost_inputs=costs,
        )

    def test_two_alternatives_use_same_scope_without_recommending(self):
        plan = self.plan()
        original = deepcopy(plan)
        result = self.project(plan)
        self.assertEqual(plan, original)
        alt = result["report_summary_private"]["gross_alternatives_private"]
        self.assertEqual(alt["status"], "GROSS_ALTERNATIVES_ONLY_NOT_NET")
        self.assertEqual(alt["scenarios"][0][
            "gross_after_largest_non_cash_security_pct"], "70.00")
        self.assertEqual(alt["scenarios"][0]["gross_after_scoped_cash_pct"], "0.00")
        self.assertEqual(alt["scenarios"][1][
            "gross_after_largest_non_cash_security_pct"], "30.00")
        self.assertEqual(alt["scenarios"][1]["gross_after_scoped_cash_pct"], "50.00")
        self.assertNotIn("allocations_base", str(alt))
        self.assertNotIn("contribution", str(alt))
        self.assertEqual(result["execution_status"], "UNAVAILABLE_NOT_EXECUTION_CERTIFIED")

    def test_baseline_costs_do_not_become_alternative_net_quotes(self):
        result = self.project(costs=self.fx.new_cost_inputs())
        self.assertEqual(result["funded_contribution_private"]["status"],
                         "CONDITIONAL_SUPPLIED_COST_BUDGET_RECONCILED")
        alt = result["report_summary_private"]["gross_alternatives_private"]
        self.assertEqual(alt["status"], "GROSS_ALTERNATIVES_ONLY_NOT_NET")
        self.assertNotIn("funding", alt)
        self.assertNotIn("cost", str(alt).lower())

    def test_pi_only_manual_report_includes_alternatives_not_balances(self):
        out = complete_manual_session(
            self.fx.request(research_needed=False, portfolio_needed=True),
            pi_delta=self.fx.pi(), contribution_inputs=self.plan(),
        )
        report = out["final_report_private"]
        self.assertIn("Alternative 1: largest non-cash security line 70.00%", report)
        self.assertIn("Alternative 2: largest non-cash security line 30.00%; scoped cash 50.00%", report)
        self.assertIn("GROSS only", report)
        self.assertNotIn("1400.00", report)
        self.assertNotIn("1000.00", report)
        self.assertEqual(out["storage"], "NONE")

    def test_full_ir_pi_cc_path_shows_same_alternatives(self):
        out = complete_manual_session(
            self.fx.request(research_needed=True, portfolio_needed=True),
            ir_capsule=self.fx.ir(),
            pi_delta=self.fx.pi(forwarded_ir=self.fx.ir()),
            contribution_inputs=self.plan(),
        )
        self.assertIn("Alternative 2", out["final_report_private"])
        self.assertEqual(out["integrated_private"]["status"],
                         "ASSEMBLED_COMPONENT_ONLY_NOT_END_TO_END_ACCEPTANCE")
        self.assertNotIn("gross_alternatives_private",
                         str(out["integrated_private"]["memory_proposal_nonprivate"]))

    def test_invalid_count_or_allocation_fails_closed(self):
        for value in ([], [dict(ABC="100")] * 4, "100",
                      [{"ABC:TSX": "80"}], [{"ABC:TSX": "NaN"}]):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.project(self.plan(alternative_allocations_pct=value))

    def test_unknown_account_currency_blocks_gross_alternatives_and_reports_safe_gaps(self):
        from tests.test_ai_native_reporting import ReportingTests
        plan = self.plan(currency="UNKNOWN")
        bundle = self.project(plan)
        gross = bundle["gross_contribution_private"]
        summary = bundle["report_summary_private"]
        self.assertEqual(gross["status"], "UNAVAILABLE")
        self.assertEqual(gross["reason_codes"], ["ACCOUNT_CURRENCY_UNKNOWN"])
        self.assertIsNone(summary["allocations_pct"])
        self.assertIsNone(summary["gross_alternatives_private"])
        self.assertEqual(summary["gross_unavailable_reason_codes"],
                         ["ACCOUNT_CURRENCY_UNKNOWN"])
        report = render_report(ReportingTests().packet(
            analysis_id="CASE-A", new_contribution_summary_private=summary))
        self.assertIn("Identify the genuine three-letter account-base currency", report)
        self.assertIn("ACCOUNT_CURRENCY_UNKNOWN", report)
        self.assertNotIn("1000.00", report)
        self.assertNotIn("400.00", report)
        self.assertNotIn("60% of new capital", report)

    def test_actual_pi_only_manual_session_reports_unknown_currency_and_no_alternatives(self):
        out = complete_manual_session(
            self.fx.request(research_needed=False, portfolio_needed=True),
            pi_delta=self.fx.pi(), contribution_inputs=self.plan(currency="UNKNOWN"))
        self.assertEqual(out["status"], "PI_ONLY_CONDITIONAL_REPORT_ASSEMBLED")
        self.assertEqual(out["gross_contribution_private"]["status"], "UNAVAILABLE")
        self.assertIn("ACCOUNT_CURRENCY_UNKNOWN", out["final_report_private"])
        self.assertIn("Identify the genuine three-letter account-base currency",
                      out["final_report_private"])
        self.assertNotIn("Alternative 1:", out["final_report_private"])
        self.assertNotIn("1000.00", out["final_report_private"])
        self.assertEqual(out["storage"], "NONE")

    def test_gross_missing_reasons_reject_untrusted_or_repeated_strings(self):
        from tests.test_ai_native_reporting import ReportingTests
        summary = self.project(self.plan(currency="UNKNOWN"))["report_summary_private"]
        for invalid in (["BUY_ABC_NOW"], ["ACCOUNT_CURRENCY_UNKNOWN",
                                         "ACCOUNT_CURRENCY_UNKNOWN"],
                        [], ["ACCOUNT_CURRENCY_UNKNOWN", 17]):
            with self.subTest(invalid=invalid):
                changed = deepcopy(summary)
                changed["gross_unavailable_reason_codes"] = invalid
                with self.assertRaisesRegex(ValueError,
                                            "CONTRIBUTION_REPORT_UNAVAILABLE_REASONS_INVALID"):
                    render_report(ReportingTests().packet(
                        analysis_id="CASE-A",
                        new_contribution_summary_private=changed))

    def test_gross_projection_refuses_forged_missing_reason_codes(self):
        from tests.test_ai_native_reporting import ReportingTests
        summary = self.project()["report_summary_private"]
        summary["gross_unavailable_reason_codes"] = ["ACCOUNT_CURRENCY_UNKNOWN"]
        with self.assertRaisesRegex(ValueError, "CONTRIBUTION_REPORT_GROSS_REASONS_CONFLICT"):
            render_report(ReportingTests().packet(
                analysis_id="CASE-A", new_contribution_summary_private=summary))

    def test_missing_scope_never_reports_alternative_numbers(self):
        summary = self.project(self.plan(scope_complete=False))["report_summary_private"]
        self.assertEqual(summary["gross_status"], "UNAVAILABLE")
        self.assertIsNone(summary["gross_alternatives_private"])

    def test_report_rejects_forged_percent_authority_and_index(self):
        summary = self.project()["report_summary_private"]
        changes = (
            ("authority", "BROKER_APPROVED"),
            ("status", "NET_BEST_CHOICE"),
        )
        for key, value in changes:
            with self.subTest(key=key):
                packet = deepcopy(summary)
                packet["gross_alternatives_private"][key] = value
                with self.assertRaisesRegex(ValueError,"CONTRIBUTION_REPORT_ALTERNATIVES"):
                    render_report(ReportingTests().packet(
                        analysis_id="CASE-A", new_contribution_summary_private=packet))
        for key, value in (
            ("scenario_index", 2),
            ("gross_after_scoped_cash_pct", "NaN"),
            ("gross_after_scoped_cash_pct", "101.00"),
            ("gross_after_largest_non_cash_security_pct", "30.001"),
        ):
            with self.subTest(key=key):
                packet = deepcopy(summary)
                packet["gross_alternatives_private"]["scenarios"][0][key] = value
                with self.assertRaisesRegex(ValueError,"CONTRIBUTION_REPORT_ALTERNATIVES"):
                    render_report(ReportingTests().packet(
                        analysis_id="CASE-A", new_contribution_summary_private=packet))


if __name__ == "__main__":
    unittest.main()
