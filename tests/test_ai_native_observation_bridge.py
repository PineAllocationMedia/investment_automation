import copy
import unittest
from ai_native.session_bridge import complete_manual_session


class ObservationBridgeTests(unittest.TestCase):
    def req(self, **change):
        d = dict(ceo_initiated=True,research_needed=False,portfolio_needed=True,analysis_id="SYN-01",
                 as_of="2026-10-28",objective="Private conditional observation",kind="DECISION")
        d.update(change)
        return d

    def observation(self, **change):
        d = dict(analysis_id="SYN-01", observed_on="2026-10-28", analysis_as_of="2026-10-28",
                 captured_at="2026-10-28T10:00:00-04:00", source_type="PRIVATE_USER_TABLE",
                 private_scope=True, source_access_confirmed_by_caller=True, account_scope="SCOPE-A",
                 currency="CAD", scope_complete=True, cash_base="100.00",
                 cash_visibility="VERIFIED_VISIBLE", same_currency_basis_confirmed_by_caller=True,
                 positions=[dict(p_id="P-1",security_id="ABC:TSX",account_scope="SCOPE-A",
                                 currency="CAD",market_value_base="300.00",
                                 field_statuses={k:"VERIFIED_VISIBLE" for k in
                                     ("security_id","market_value_base","currency","account_scope")})])
        d.update(change)
        return d

    def pi(self, **change):
        d = dict(analysis_id="SYN-01",portfolio_as_of="2026-10-28",room_status="ROOM_CONDITIONAL",
                 summary="Only scoped observations available",limitations="Not broker verified",
                 next_action="Check account inclusion")
        d.update(change)
        return d

    def test_pi_pending_carries_private_p_ledger(self):
        result = complete_manual_session(self.req(),observation_inputs=self.observation())
        self.assertEqual(result["status"],"AWAITING_MANUAL_PI_DELTA")
        self.assertEqual(result["portfolio_observation_private"]["scope_total_base"],"400.00")
        self.assertIsNone(result["final_report_private"])

    def test_pi_report_does_not_promote_observation(self):
        result = complete_manual_session(self.req(),pi_delta=self.pi(),observation_inputs=self.observation())
        self.assertEqual(result["status"],"PI_ONLY_CONDITIONAL_REPORT_ASSEMBLED")
        self.assertIn("NOT authenticated",result["final_report_private"])
        self.assertEqual(result["portfolio_observation_private"]["portfolio_room_status"],"ROOM_UNAVAILABLE")

    def test_pi_late_capture_reports_effective_date_not_capture_as_holdings(self):
        output = complete_manual_session(
            self.req(as_of="2026-10-30"),
            pi_delta=self.pi(portfolio_as_of="2026-10-27"),
            observation_inputs=self.observation(
                observed_on="2026-10-27",
                analysis_as_of="2026-10-30",
                captured_at="2026-10-29T10:00:00-04:00"))
        self.assertEqual(output["status"],
                         "PI_ONLY_CONDITIONAL_REPORT_ASSEMBLED")
        report = output["final_report_private"]
        self.assertIn("Capture recorded on 2026-10-29", report)
        self.assertIn("effective position date 2026-10-27", report)
        self.assertIn("2 calendar day(s) between position date and capture",
                      report)
        self.assertIn("3 day(s) before analysis cutoff", report)
        self.assertIn("NOT independently authenticated", report)
        self.assertEqual(
            output["portfolio_observation_private"]["portfolio_room_status"],
            "ROOM_UNAVAILABLE")

    def test_pi_date_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError,"OBSERVATION_PI_DATE_MISMATCH"):
            complete_manual_session(self.req(),pi_delta=self.pi(portfolio_as_of="2026-10-27"),observation_inputs=self.observation())

    def test_observation_cutoff_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError,"OBSERVATION_ANALYSIS_CUTOFF_MISMATCH"):
            complete_manual_session(self.req(),observation_inputs=self.observation(analysis_as_of="2026-10-27"))

    def test_observation_not_allowed_in_research_route(self):
        with self.assertRaisesRegex(ValueError,"PORTFOLIO_OBSERVATION_REQUIRES_PI_ROUTE"):
            complete_manual_session(self.req(portfolio_needed=False,research_needed=True),observation_inputs=self.observation())

    def test_bad_visibility_cannot_support_room(self):
        with self.assertRaisesRegex(ValueError,"UNSUPPORTED_PORTFOLIO_ROOM_ASSERTION"):
            complete_manual_session(self.req(),pi_delta=self.pi(room_status="ROOM_EVIDENCE_SUPPORTED"),
                   observation_inputs=self.observation(scope_complete=False))

    def test_no_mutation_of_private_observation(self):
        o=self.observation();before=copy.deepcopy(o)
        complete_manual_session(self.req(),observation_inputs=o)
        self.assertEqual(o,before)

    def ir(self):
        return dict(analysis_id="SYN-01", research_as_of="2026-10-28",
                    summary=["Conditional synthetic research"], facts=[],
                    limitations="No authenticated original source",
                    countercase="Coverage might be incomplete",
                    decision_line="No executable conclusion",
                    next_action="Verify observations")

    def contribution(self, **patch):
        data = dict(positions_base={"ABC:TSX": "300.00"},
                    allocations_pct={"ABC:TSX": "100"},
                    contribution_base="100.00", currency="CAD", as_of="2026-10-28",
                    scope_complete=True, cash_accounted_for=True,
                    same_currency_basis_verified=True, instrument_identity_verified=True)
        data.update(patch)
        return data

    def test_incomplete_visible_scope_cannot_be_overridden_on_either_route(self):
        # The former guard existed only in PI-only; IR+PI silently projected.
        for research_needed in (False, True):
            with self.subTest(research_needed=research_needed):
                ir = self.ir() if research_needed else None
                pi = self.pi(forwarded_ir=copy.deepcopy(ir)) if ir else self.pi()
                with self.assertRaisesRegex(
                        ValueError, "PI_CONTRIBUTION_SCOPE_CONFLICTS_WITH_OBSERVATION"):
                    complete_manual_session(
                        self.req(research_needed=research_needed),
                        ir_capsule=ir, pi_delta=pi,
                        observation_inputs=self.observation(scope_complete=False),
                        contribution_inputs=self.contribution())

    def test_mismatched_currency_cannot_be_called_verified_on_either_route(self):
        for research_needed in (False, True):
            with self.subTest(research_needed=research_needed):
                ir = self.ir() if research_needed else None
                pi = self.pi(forwarded_ir=copy.deepcopy(ir)) if ir else self.pi()
                with self.assertRaisesRegex(
                        ValueError, "PI_CONTRIBUTION_CURRENCY_CONFLICTS_WITH_OBSERVATION"):
                    complete_manual_session(
                        self.req(research_needed=research_needed),
                        ir_capsule=ir, pi_delta=pi,
                        observation_inputs=self.observation(cash_base="0.00"),
                        contribution_inputs=self.contribution(currency="USD"))

    def test_matching_complete_capture_can_project_on_both_routes(self):
        for research_needed in (False, True):
            with self.subTest(research_needed=research_needed):
                ir = self.ir() if research_needed else None
                pi = self.pi(forwarded_ir=copy.deepcopy(ir)) if ir else self.pi()
                result = complete_manual_session(
                    self.req(research_needed=research_needed),
                    ir_capsule=ir, pi_delta=pi,
                    observation_inputs=self.observation(cash_base="0.00"),
                    contribution_inputs=self.contribution())
                self.assertEqual(
                    result["gross_contribution_private"]["status"],
                    "GROSS_PROJECTION_ONLY")
                self.assertEqual(result["project_invocation"], "NONE")
                self.assertEqual(result["storage"], "NONE")

    def test_observed_positions_derived_including_cash_on_both_manual_routes(self):
        for research_needed in (False, True):
            with self.subTest(research_needed=research_needed):
                ir = self.ir() if research_needed else None
                pi = self.pi(forwarded_ir=copy.deepcopy(ir)) if ir else self.pi()
                supplied = self.contribution()
                supplied.pop("positions_base")
                before = copy.deepcopy(supplied)
                out = complete_manual_session(
                    self.req(research_needed=research_needed),
                    ir_capsule=ir, pi_delta=pi,
                    observation_inputs=self.observation(),
                    contribution_inputs=supplied)
                gross = out["gross_contribution_private"]
                self.assertEqual(gross["status"], "GROSS_PROJECTION_ONLY")
                self.assertEqual(gross["current_total"], "400.00")
                self.assertEqual(gross["projected_total"], "500.00")
                self.assertEqual(gross["projected_positions"]["P-CASH"], "100.00")
                self.assertEqual(supplied, before)
                self.assertEqual(out["source_authentication"], "NOT_PERFORMED")
                self.assertIsNone(out["funded_contribution_private"])

    def test_retyped_positions_disagree_with_visible_ledger_both_routes(self):
        for research_needed in (False, True):
            ir = self.ir() if research_needed else None
            pi = self.pi(forwarded_ir=copy.deepcopy(ir)) if ir else self.pi()
            with self.subTest(research_needed=research_needed):
                with self.assertRaisesRegex(
                        ValueError, "PI_CONTRIBUTION_POSITIONS_CONFLICT_WITH_OBSERVATION"):
                    complete_manual_session(
                        self.req(research_needed=research_needed),
                        ir_capsule=ir, pi_delta=pi,
                        observation_inputs=self.observation(cash_base="0.00"),
                        contribution_inputs=self.contribution(
                            positions_base={"ABC:TSX": "301.00"}))

    def test_visible_nonzero_cash_cannot_disappear_from_supplied_basis(self):
        for research_needed in (False, True):
            ir = self.ir() if research_needed else None
            pi = self.pi(forwarded_ir=copy.deepcopy(ir)) if ir else self.pi()
            with self.subTest(research_needed=research_needed):
                with self.assertRaisesRegex(
                        ValueError, "PI_CONTRIBUTION_CASH_MISSING_FROM_SCOPED_BASIS"):
                    complete_manual_session(
                        self.req(research_needed=research_needed),
                        ir_capsule=ir, pi_delta=pi,
                        observation_inputs=self.observation(),
                        contribution_inputs=self.contribution())

    def test_supplied_full_cash_basis_and_duplicate_security_rows(self):
        rows = self.observation()["positions"]
        extra = copy.deepcopy(rows[0])
        extra["p_id"] = "P-2"
        extra["market_value_base"] = "200.00"
        rows.append(extra)
        supplied = self.contribution(
            positions_base={"ABC:TSX": "500.00", "P-CASH": "100.00"})
        out = complete_manual_session(
            self.req(), pi_delta=self.pi(),
            observation_inputs=self.observation(positions=rows),
            contribution_inputs=supplied)
        self.assertEqual(out["gross_contribution_private"]["current_total"], "600.00")
        self.assertEqual(out["gross_contribution_private"]["projected_total"], "700.00")
        self.assertEqual(out["gross_contribution_private"]["current_weights_pct"]["P-CASH"],
                         str(__import__("decimal").Decimal("100") * 100 / 600))

if __name__ == '__main__': unittest.main()
