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

if __name__ == '__main__': unittest.main()
