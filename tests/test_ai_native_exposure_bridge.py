import copy
import unittest
from ai_native.session_bridge import complete_manual_session

class ExposureBridgeTests(unittest.TestCase):
    def request(self):
        return dict(ceo_initiated=True,research_needed=False,portfolio_needed=True,
                    analysis_id="SYN-01",as_of="2026-10-28",objective="Analyze exposures",
                    kind="DECISION")
    def observed(self):
        return dict(analysis_id="SYN-01",observed_on="2026-10-28",analysis_as_of="2026-10-28",
                    captured_at="2026-10-28T10:00:00-04:00",source_type="PRIVATE_USER_TABLE",
                    private_scope=True,source_access_confirmed_by_caller=True,
                    account_scope="ACC-SYN",currency="CAD",scope_complete=True,
                    cash_base="100.00",cash_visibility="VERIFIED_VISIBLE",
                    same_currency_basis_confirmed_by_caller=True,
                    positions=[dict(p_id="P1",security_id="ABC:TSX",account_scope="ACC-SYN",
                                    currency="CAD",market_value_base="900.00",
                                    field_statuses={k:"VERIFIED_VISIBLE" for k in
                                    ("security_id","market_value_base","currency","account_scope")})])
    def classes(self):
        return {"P1":dict(kind="DIRECT_EQUITY",security_id="ABC:TSX",source_ref="S1",
                          as_of="2026-10-28",rights_status="PERMITTED",
                          economic_issuer_id="ABC",sector="TECH",region="CANADA")}
    def pi(self,**kw):
        d=dict(analysis_id="SYN-01",portfolio_as_of="2026-10-28",room_status="ROOM_UNAVAILABLE",
               summary="Synthetic visible data", limitations="Unverified",next_action="Check more sources")
        d.update(kw)
        return d
    def test_pi_pending_keeps_private_exposures(self):
        x=complete_manual_session(self.request(),observation_inputs=self.observed(), exposure_classifications=self.classes())
        self.assertEqual(x["status"],"AWAITING_MANUAL_PI_DELTA")
        self.assertEqual(x["portfolio_exposures_private"]["economic_issuer_pct_private"],{"ABC":"90.00"})
        self.assertIsNone(x["final_report_private"])
    def test_no_exposure_without_observation(self):
        with self.assertRaisesRegex(ValueError,"EXPOSURES_REQUIRE_PI_OBSERVATION"):
            complete_manual_session(self.request(),exposure_classifications=self.classes())
    def test_partial_fund_does_not_authorize_room(self):
        with self.assertRaisesRegex(ValueError,"ROOM_ASSERTION_UNSUPPORTED"):
            complete_manual_session(self.request(),observation_inputs=self.observed(),exposure_classifications={},
                                    pi_delta=self.pi(room_status="ROOM_EVIDENCE_SUPPORTED"))
    def test_private_data_not_in_short_report(self):
        x=complete_manual_session(self.request(),observation_inputs=self.observed(),
            exposure_classifications=self.classes(),pi_delta=self.pi())
        self.assertEqual(x["status"],"PI_ONLY_CONDITIONAL_REPORT_ASSEMBLED")
        self.assertNotIn("90.00",x["final_report_private"])
    def test_original_classifications_unchanged(self):
        d=self.classes();original=copy.deepcopy(d)
        complete_manual_session(self.request(),observation_inputs=self.observed(),exposure_classifications=d)
        self.assertEqual(original,d)

if __name__=='__main__':unittest.main()
