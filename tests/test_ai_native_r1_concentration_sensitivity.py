"""New-contribution *security-line* concentration sensitivity, synthetic-only.

Existing deterministic M3 contribution/funded calculations are the only source
of figures. No portfolio policy, economic issuer look-through, market-price
projection, brokerage verification or trading action is supplied.
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


class R1ConcentrationSensitivityTests(unittest.TestCase):
    def setUp(self):
        self.fx = SessionBridgeTests()

    def projection(self, contribution=None, costs=None):
        return prepare_new_capital_projection(
            analysis_id="CASE-A", analysis_as_of="2026-10-28",
            portfolio_as_of="2026-10-28",
            contribution_inputs=(
                self.fx.new_contribution_inputs() if contribution is None
                else contribution),
            cost_inputs=costs)

    def test_reuses_gross_weights_and_never_invents_net_scenario(self):
        inputs = self.fx.new_contribution_inputs()
        before = deepcopy(inputs)
        result = self.projection(inputs)
        self.assertEqual(inputs, before)
        sensitivity = result["report_summary_private"][
            "largest_security_line_sensitivity_private"]
        self.assertEqual(sensitivity["status"],"GROSS_ONLY_SCOPED_SENSITIVITY")
        self.assertEqual(sensitivity["before_largest_non_cash_security_pct"],"60.00")
        self.assertEqual(sensitivity["gross_after_largest_non_cash_security_pct"],"50.00")
        self.assertIsNone(sensitivity[
            "conditional_funded_after_largest_non_cash_security_pct"])
        self.assertEqual(result["execution_status"],"UNAVAILABLE_NOT_EXECUTION_CERTIFIED")

    def test_cost_funding_affects_only_conditional_post_scenario(self):
        inputs = self.fx.new_contribution_inputs()
        for funding in ("FROM_CONTRIBUTION","EXTERNAL_CASH"):
            with self.subTest(funding=funding):
                result = self.projection(inputs, self.fx.new_cost_inputs(funding))
                sensitivity = result["report_summary_private"][
                    "largest_security_line_sensitivity_private"]
                self.assertEqual(sensitivity["status"],
                                 "GROSS_AND_CONDITIONAL_FUNDED_SCOPED_SENSITIVITY")
                self.assertEqual(sensitivity[
                    "before_largest_non_cash_security_pct"],"60.00")
                self.assertEqual(sensitivity[
                    "gross_after_largest_non_cash_security_pct"],"50.00")
                self.assertEqual(sensitivity[
                    "conditional_funded_after_largest_non_cash_security_pct"],
                    "50.03" if funding == "FROM_CONTRIBUTION" else "50.00")
                self.assertEqual(result["funded_contribution_private"][
                    "execution_status"],"UNAVAILABLE_NOT_EXECUTION_CERTIFIED")

    def test_unknown_funding_does_not_gain_conditional_concentration(self):
        result = self.projection(costs=self.fx.new_cost_inputs("UNKNOWN"))
        self.assertEqual(result["funded_contribution_private"]["status"],
                         "UNAVAILABLE_FUNDING_UNKNOWN")
        sensitivity = result["report_summary_private"][
            "largest_security_line_sensitivity_private"]
        self.assertEqual(sensitivity["status"],"GROSS_ONLY_SCOPED_SENSITIVITY")
        self.assertIsNone(sensitivity[
            "conditional_funded_after_largest_non_cash_security_pct"])

    def test_unavailable_scope_and_cash_only_do_not_fabricate_security(self):
        result = self.projection(self.fx.new_contribution_inputs(scope_complete=False))
        self.assertIsNone(result["report_summary_private"][
            "largest_security_line_sensitivity_private"])
        cash_only = self.fx.new_contribution_inputs(
            positions_base={"P-CASH":"1000.00"},
            allocations_pct={"P-CASH":"100"})
        result = self.projection(cash_only)
        sensitivity = result["report_summary_private"][
            "largest_security_line_sensitivity_private"]
        self.assertIsNone(sensitivity["before_largest_non_cash_security_pct"])
        self.assertIsNone(sensitivity["gross_after_largest_non_cash_security_pct"])

    def test_pi_only_report_uses_aggregate_sensitivity_without_raw_holdings(self):
        result = complete_manual_session(
            self.fx.request(research_needed=False,portfolio_needed=True),
            pi_delta=self.fx.pi(), contribution_inputs=self.fx.new_contribution_inputs(),
            cost_inputs=self.fx.new_cost_inputs())
        report = result["final_report_private"]
        self.assertIn("Largest single non-cash security line",report)
        self.assertIn("before 60.00%",report)
        self.assertIn("GROSS new-capital scenario 50.00%",report)
        self.assertIn("largest non-cash security line 50.03%",report)
        self.assertIn("not economic-issuer look-through",report)
        self.assertNotIn("400.00",report)
        self.assertNotIn("995.00",report)
        self.assertEqual(result["storage"],"NONE")

    def test_full_ir_pi_cc_report_reuses_the_same_existing_m3_math(self):
        case = RealManualConstructionSmoke().case()
        old = deepcopy(case)
        result = complete_manual_session(**case)
        self.assertEqual(case,old)
        report = result["final_report_private"]
        self.assertIn("before 60.00%",report)
        self.assertIn("GROSS new-capital scenario 50.00%",report)
        self.assertIn("largest non-cash security line 50.03%",report)
        self.assertNotIn("SYN-COST",report)
        self.assertNotIn("1000.00",report)
        self.assertNotIn("largest_security_line_sensitivity_private",
                         str(result["integrated_private"]["memory_proposal_nonprivate"]))
        self.assertEqual(result["readiness"],"NOT_EVALUATED")

    def test_report_rejects_forged_status_percent_and_funded_authority(self):
        base = self.projection()["report_summary_private"]
        for changes in (
            {"status":"INVESTABLE"},
            {"authority":"BROKER_APPROVED"},
            {"before_largest_non_cash_security_pct":"NaN"},
            {"gross_after_largest_non_cash_security_pct":"150.00"},
            {"gross_after_largest_non_cash_security_pct":"50.000"},
            {"conditional_funded_after_largest_non_cash_security_pct":"50.03"},
        ):
            with self.subTest(changes=changes):
                forged = deepcopy(base)
                forged["largest_security_line_sensitivity_private"].update(changes)
                with self.assertRaisesRegex(ValueError,"CONTRIBUTION_REPORT_CONCENTRATION"):
                    render_report(ReportingTests().packet(
                        analysis_id="CASE-A",new_contribution_summary_private=forged))

    def test_report_rejects_unavailable_gross_with_concentration(self):
        summary = deepcopy(self.projection()["report_summary_private"])
        summary["gross_status"]="UNAVAILABLE"
        summary["allocations_pct"]=None
        with self.assertRaisesRegex(ValueError,"CONTRIBUTION_REPORT_CONCENTRATION"):
            render_report(ReportingTests().packet(
                analysis_id="CASE-A",new_contribution_summary_private=summary))


if __name__=="__main__":
    unittest.main()
