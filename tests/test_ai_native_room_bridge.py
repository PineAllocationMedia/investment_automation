import unittest
from unittest.mock import patch
import test_ai_native_portfolio_room as room_fixture
from ai_native.session_bridge import complete_manual_session

class RoomBridgeTests(unittest.TestCase):
    def setUp(self):
        self.fx=room_fixture.RoomTests()
    def req(self):return self.fx.request()
    def extra(self):
        obs=self.fx.observation()
        return dict(ir_capsule=self.fx.ir(),observation_inputs={
            "analysis_id":"SYN-A","observed_on":"2026-10-28","analysis_as_of":"2026-10-28",
            "captured_at":"2026-10-28T10:00:00-04:00","source_type":"PRIVATE_USER_TABLE",
            "private_scope":True,"source_access_confirmed_by_caller":True,
            "account_scope":"SYN-ACCOUNT","currency":"CAD","scope_complete":True,
            "cash_base":"100.00","cash_visibility":"VERIFIED_VISIBLE",
            "same_currency_basis_confirmed_by_caller":True,
            "positions":[{"p_id":"P1","security_id":"ABC:TSX","market_value_base":"900.00",
              "account_scope":"SYN-ACCOUNT","currency":"CAD",
              "field_statuses":{x:"VERIFIED_VISIBLE" for x in
              ("security_id","market_value_base","currency","account_scope")}}]},
            exposure_classifications={"P1":dict(kind="DIRECT_EQUITY",security_id="ABC:TSX",
             source_ref="S1",rights_status="PERMITTED",as_of="2026-10-27",
             economic_issuer_id="ABC",sector="TECH",region="CANADA")},
            room_assessment_inputs=self.fx.inputs())
    def test_private_room_prepared_while_waiting_for_pi(self):
        result=complete_manual_session(self.req(),**self.extra())
        self.assertEqual(result["status"],"AWAITING_MANUAL_PI_DELTA")
        self.assertEqual(result["portfolio_room_review_private"]["status"],"ROOM_CONDITIONAL")
        self.assertIsNone(result["final_report_private"])
    def test_pi_only_cannot_prepare_room_from_missing_ir(self):
        r=self.req();r["research_needed"]=False
        with self.assertRaisesRegex(ValueError,"ROOM_REQUIRES_IR_AND_PI_ROUTE"):
            complete_manual_session(r,room_assessment_inputs=self.fx.inputs())
    def test_room_cannot_be_prepared_without_P_ledger(self):
        with self.assertRaisesRegex(ValueError,"ROOM_REQUIRES_SCOPED_OBSERVATION_AND_EXPOSURES"):
            complete_manual_session(self.req(),ir_capsule=self.fx.ir(),room_assessment_inputs=self.fx.inputs())
    def test_room_pending_does_not_run_on_missing_ir(self):
        x=self.extra();x["ir_capsule"]=None
        out=complete_manual_session(self.req(),**x)
        self.assertEqual(out["status"],"AWAITING_MANUAL_IR_CAPSULE")
        self.assertIsNone(out["portfolio_room_review_private"])
    def test_supported_room_is_not_promoted(self):
        x=self.extra();x["pi_delta"]=dict(analysis_id="SYN-A",portfolio_as_of="2026-10-28",
         forwarded_ir=x["ir_capsule"],room_status="ROOM_EVIDENCE_SUPPORTED",summary="synthetic",
         limitations="unknown",next_action="review")
        with self.assertRaisesRegex(ValueError,"ROOM_SUPPORTED_NOT_CERTIFIED"):
            complete_manual_session(self.req(),**x)
    def test_normal_PI_return_preserves_private_review(self):
        x=self.extra();x["pi_delta"]=dict(analysis_id="SYN-A",portfolio_as_of="2026-10-28",
         forwarded_ir=x["ir_capsule"],room_status="ROOM_CONDITIONAL",summary="synthetic",
         limitations="unknown",next_action="review")
        with patch("ai_native.session_bridge.assemble_manual_run",return_value={"markdown":"SYNTHETIC REPORT"}):
            result=complete_manual_session(self.req(),**x)
        self.assertEqual(result["portfolio_room_review_private"]["status"],"ROOM_CONDITIONAL")
        self.assertEqual(result["final_report_private"],"SYNTHETIC REPORT")
        self.assertNotIn("90.00",result["final_report_private"])

if __name__=='__main__':unittest.main()
