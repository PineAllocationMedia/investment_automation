"""Cash share of the same private scoped portfolio before/new cash scenarios.

All fixtures synthetic. The cash line stays in the same denominator as the
largest-security-line metric; no liquidity-access or reserve policy is claimed.
"""
from __future__ import annotations
from copy import deepcopy
import unittest

from ai_native.new_capital_flow import prepare_new_capital_projection
from ai_native.reporting import render_report
from ai_native.session_bridge import complete_manual_session
from tests.test_ai_native_session_bridge import SessionBridgeTests
from tests.test_ai_native_r1_integrated_smoke import RealManualConstructionSmoke
from tests.test_ai_native_reporting import ReportingTests


class R1CashSensitivityTests(unittest.TestCase):
    def setUp(self):
        self.fx=SessionBridgeTests()

    def projection(self, inputs=None, costs=None):
        return prepare_new_capital_projection(
            analysis_id="CASE-A", analysis_as_of="2026-10-28",
            portfolio_as_of="2026-10-28",
            contribution_inputs=inputs or self.fx.new_contribution_inputs(),
            cost_inputs=costs)

    def cash(self, result):
        return result["report_summary_private"][
            "largest_security_line_sensitivity_private"]

    def test_no_existing_cash_is_zero_only_for_complete_gross_scope(self):
        inputs=self.fx.new_contribution_inputs()
        old=deepcopy(inputs)
        sensitivity=self.cash(self.projection(inputs))
        self.assertEqual(inputs,old)
        self.assertEqual(sensitivity["before_scoped_cash_pct"],"0.00")
        self.assertEqual(sensitivity["gross_after_scoped_cash_pct"],"0.00")
        self.assertIsNone(sensitivity["conditional_funded_after_scoped_cash_pct"])

    def test_cash_only_then_new_security_shows_descriptive_dilution(self):
        inputs=self.fx.new_contribution_inputs(
            positions_base={"P-CASH":"1000.00"},
            allocations_pct={"ABC:TSX":"100"})
        sensitivity=self.cash(self.projection(inputs))
        self.assertEqual(sensitivity["before_scoped_cash_pct"],"100.00")
        self.assertEqual(sensitivity["gross_after_scoped_cash_pct"],"50.00")
        self.assertIsNone(sensitivity["before_largest_non_cash_security_pct"])
        self.assertEqual(sensitivity["gross_after_largest_non_cash_security_pct"],"50.00")

    def test_all_cash_before_and_after_remains_cash_not_a_security(self):
        inputs=self.fx.new_contribution_inputs(
            positions_base={"P-CASH":"1000.00"},
            allocations_pct={"P-CASH":"100"})
        sensitivity=self.cash(self.projection(inputs))
        self.assertEqual(sensitivity["before_scoped_cash_pct"],"100.00")
        self.assertEqual(sensitivity["gross_after_scoped_cash_pct"],"100.00")
        self.assertIsNone(sensitivity["gross_after_largest_non_cash_security_pct"])

    def test_funded_cash_is_separately_conditional_for_both_cost_sources(self):
        case=RealManualConstructionSmoke().case()
        for funding in ("FROM_CONTRIBUTION","EXTERNAL_CASH"):
            with self.subTest(funding=funding):
                cost={**case["cost_inputs"],"funding":funding}
                p=prepare_new_capital_projection(
                    analysis_id="SYN-X",analysis_as_of="2026-10-28",
                    portfolio_as_of="2026-10-28",
                    contribution_inputs=case["contribution_inputs"],cost_inputs=cost)
                sensitivity=self.cash(p)
                self.assertEqual(sensitivity["before_scoped_cash_pct"],"10.00")
                self.assertEqual(sensitivity["gross_after_scoped_cash_pct"],"5.00")
                self.assertEqual(sensitivity["conditional_funded_after_scoped_cash_pct"],
                                 "5.01" if funding=="FROM_CONTRIBUTION" else "5.00")

    def test_unknown_funding_never_supplies_conditional_cash_share(self):
        result=self.projection(costs=self.fx.new_cost_inputs("UNKNOWN"))
        sensitivity=self.cash(result)
        self.assertIsNone(sensitivity["conditional_funded_after_scoped_cash_pct"])
        self.assertEqual(sensitivity["status"],"GROSS_ONLY_SCOPED_SENSITIVITY")
        self.assertEqual(result["funded_contribution_private"]["status"],
                         "UNAVAILABLE_FUNDING_UNKNOWN")

    def test_actual_ir_pi_cc_report_shows_only_aggregates(self):
        case=RealManualConstructionSmoke().case()
        original=deepcopy(case)
        result=complete_manual_session(**case)
        self.assertEqual(case,original)
        report=result["final_report_private"]
        self.assertIn("Cash within the SAME caller-confirmed portfolio scope",report)
        self.assertIn("before 10.00%",report)
        self.assertIn("GROSS hypothetical contribution 5.00%",report)
        self.assertIn("scoped cash 5.01%",report)
        self.assertIn("not a strategy reserve target",report)
        for sensitive in ("1000.00","300.00","SYN-SCOPE","SYN-COST"):
            self.assertNotIn(sensitive,report)
        self.assertEqual(result["project_invocation"],"NONE")
        self.assertEqual(result["storage"],"NONE")

    def test_pi_only_report_shows_zero_cash_but_no_execution(self):
        result=complete_manual_session(
            self.fx.request(research_needed=False,portfolio_needed=True),
            pi_delta=self.fx.pi(), contribution_inputs=self.fx.new_contribution_inputs())
        report=result["final_report_private"]
        self.assertIn("before 0.00%",report)
        self.assertIn("GROSS hypothetical contribution 0.00%",report)
        self.assertNotIn("Under the separate conditional fixed-supplied-cost funded scenario: scoped cash",report)
        self.assertEqual(result["readiness"],"NOT_EVALUATED")

    def test_report_rejects_forged_cash_percent_or_unfunded_net(self):
        summary=self.projection()["report_summary_private"]
        for change in (
            {"before_scoped_cash_pct":"NaN"},
            {"gross_after_scoped_cash_pct":"101.00"},
            {"gross_after_scoped_cash_pct":"0.123"},
            {"before_scoped_cash_pct":None},
            {"conditional_funded_after_scoped_cash_pct":"0.00"},
        ):
            with self.subTest(change=change):
                item=deepcopy(summary)
                item["largest_security_line_sensitivity_private"].update(change)
                with self.assertRaisesRegex(ValueError,"CONTRIBUTION_REPORT_CONCENTRATION"):
                    render_report(ReportingTests().packet(
                        analysis_id="CASE-A",new_contribution_summary_private=item))

    def test_missing_cash_metadata_refused_for_funded_scenario(self):
        summary=self.projection(costs=self.fx.new_cost_inputs())[
            "report_summary_private"]
        bad=deepcopy(summary)
        bad["largest_security_line_sensitivity_private"][
            "conditional_funded_after_scoped_cash_pct"]=None
        with self.assertRaisesRegex(ValueError,"CONTRIBUTION_REPORT_CONCENTRATION"):
            render_report(ReportingTests().packet(
                analysis_id="CASE-A",new_contribution_summary_private=bad))


if __name__=="__main__":
    unittest.main()
