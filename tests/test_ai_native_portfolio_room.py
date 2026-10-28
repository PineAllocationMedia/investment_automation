import copy
import unittest
from ai_native.portfolio_observation import prepare_observation_ledger
from ai_native.portfolio_exposure import aggregate_portfolio_exposures
from ai_native.portfolio_room import prepare_portfolio_room_review

class RoomTests(unittest.TestCase):
    def request(self):
        return dict(ceo_initiated=True, research_needed=True, portfolio_needed=True,
                    analysis_id="SYN-A",as_of="2026-10-28",strategy_id="SYN-EXPLORATORY",
                    kind="DECISION",objective="Conditional synthetic capital room")
    def ir(self):
        return dict(analysis_id="SYN-A",research_as_of="2026-10-27",
                    facts=[dict(id=f"F{i}",status="INDICATIVE",claim="synthetic") for i in range(1,5)],
                    summary=["Synthetic"], limitations="unverified", countercase="unknown",
                    decision_line="no trade",next_action="check")
    def observation(self,complete=True):
        return prepare_observation_ledger(analysis_id="SYN-A",observed_on="2026-10-28",
            analysis_as_of="2026-10-28",captured_at="2026-10-28T10:00:00-04:00",
            source_type="PRIVATE_USER_TABLE",private_scope=True,
            source_access_confirmed_by_caller=True,account_scope="SYN-ACCOUNT",currency="CAD",
            scope_complete=complete,cash_base="100.00",cash_visibility="VERIFIED_VISIBLE",
            same_currency_basis_confirmed_by_caller=True,positions=[dict(p_id="P1",
             security_id="ABC:TSX",market_value_base="900.00",account_scope="SYN-ACCOUNT",
             currency="CAD",field_statuses={k:"VERIFIED_VISIBLE" for k in
             ("security_id","market_value_base","currency","account_scope")})])
    def exposure(self, obs=None, classifications=None):
        return aggregate_portfolio_exposures(obs if obs is not None else self.observation(),
          classifications_by_p_id=classifications if classifications is not None else {
          "P1":dict(security_id="ABC:TSX",kind="DIRECT_EQUITY",source_ref="SYN-ETF",
             rights_status="PERMITTED",as_of="2026-10-27",economic_issuer_id="ABC",
             sector="TECH",region="CANADA")})
    def inputs(self):
        return dict(review_as_of="2026-10-28",strategy_id="SYN-EXPLORATORY",
         capital_source="NEW_CONTRIBUTION",account_scope="SYN-ACCOUNT",account_type="TFSA",
         candidate_economic_issuer_id="ABC",candidate_security_id="ABC:TSX",horizon_years=5,
         research_axes={k:dict(status="SPECIALIST_REPORTED",rationale="Only researcher-reported data",
                             ir_fact_ids=[f"F{i}"]) for i,k in enumerate(
                            ("QUALITY","DURABILITY","EXPECTED_RETURN","CONFIDENCE"),start=1)},
         portfolio_checks={k:dict(status="SPECIALIST_REPORTED",finding="conditional",
                                  source_ref="SYN-REVIEW") for k in
                           ("CONCENTRATION","CORRELATED_DRIVERS","ALTERNATIVES","ACCOUNT_COSTS")},
         analyst_view="Room may merit more review",strongest_countercase="Compounding can fail",
         next_verification="Independent issuer filing")
    def runroom(self, **kwargs):
        data=dict(request=self.request(),ir_capsule=self.ir(),observation=self.observation(),room_inputs=self.inputs())
        data["exposures"]=self.exposure(data["observation"])
        data.update(kwargs)
        return prepare_portfolio_room_review(**data)
    def test_conditional_even_with_all_research_reported(self):
        x=self.runroom()
        self.assertEqual(x["status"],"ROOM_CONDITIONAL")
        self.assertEqual(x["known_candidate_issuer_exposure_pct_private"],"90.00")
        self.assertEqual(x["trade_authority"],"NONE_CEO_ONLY")
    def test_never_evidence_supported(self):
        x=self.runroom();self.assertNotEqual(x["status"],"ROOM_EVIDENCE_SUPPORTED")
        self.assertEqual(x["independent_evidence_check"],"NOT_PERFORMED")
    def test_an_unknown_axis_unavailable(self):
        p=self.inputs();p["research_axes"]["EXPECTED_RETURN"]["status"]="UNKNOWN"
        x=self.runroom(room_inputs=p)
        self.assertEqual(x["status"],"ROOM_UNAVAILABLE")
    def test_empty_research_refs_do_not_qualify(self):
        p=self.inputs();p["research_axes"]["CONFIDENCE"]["ir_fact_ids"]=[]
        self.assertEqual(self.runroom(room_inputs=p)["status"],"ROOM_UNAVAILABLE")
    def test_contradicted_ir_fact_blocks_room(self):
        ir=self.ir();ir["facts"][0]["status"]="CONFLICTED"
        x=self.runroom(ir_capsule=ir)
        self.assertEqual(x["status"],"ROOM_UNAVAILABLE")
        self.assertIn("QUALITY_ORIGINAL_IR_FACT_UNRESOLVED",x["missing_or_qualified"])
    def test_research_fact_id_forgery_rejected(self):
        p=self.inputs();p["research_axes"]["QUALITY"]["ir_fact_ids"]=["NONEXISTENT"]
        with self.assertRaisesRegex(ValueError,"UNKNOWN_IR_FACT"):
            self.runroom(room_inputs=p)
    def test_partial_fund_is_qualified_not_assumed_zero(self):
        obs=self.observation()
        ex=self.exposure(obs,classifications={})
        x=self.runroom(observation=obs,exposures=ex)
        self.assertEqual(x["known_candidate_issuer_exposure_pct_private"],"0")
        self.assertEqual(x["unclassified_lookthrough_pct_private"],"90.00")
        self.assertIn("LOOKTHROUGH_PARTIAL",x["missing_or_qualified"])
    def test_incomplete_observation_unavailable(self):
        o=self.observation(complete=False);e=self.exposure(o)
        x=self.runroom(observation=o,exposures=e)
        self.assertEqual(x["status"],"ROOM_UNAVAILABLE")
    def test_wrong_strategy_rejected(self):
        p=self.inputs();p["strategy_id"]="HIGH_CAGR"
        with self.assertRaisesRegex(ValueError,"STRATEGY_MISMATCH"):
            self.runroom(room_inputs=p)
    def test_wrong_id_rejected(self):
        ir=self.ir();ir["analysis_id"]="ANOTHER"
        with self.assertRaisesRegex(ValueError,"ANALYSIS_ID_MISMATCH"):
            self.runroom(ir_capsule=ir)
    def test_future_IR_cutoff_rejected(self):
        ir=self.ir();ir["research_as_of"]="2026-10-29"
        with self.assertRaisesRegex(ValueError,"IR_AFTER"):
            self.runroom(ir_capsule=ir)
    def test_wrong_portfolio_date_rejected(self):
        e=self.exposure();e["observation_as_of"]="2026-10-27"
        with self.assertRaisesRegex(ValueError,"OBSERVATION_DATE_MISMATCH"):
            self.runroom(exposures=e)
    def test_account_scope_mismatch_rejected(self):
        p=self.inputs();p["account_scope"]="NOT-THIS-ACCOUNT"
        with self.assertRaisesRegex(ValueError,"ACCOUNT_SCOPE_MISMATCH"):
            self.runroom(room_inputs=p)
    def test_missing_account_type_does_not_auto_assume(self):
        p=self.inputs();p["account_type"]="UNKNOWN"
        x=self.runroom(room_inputs=p)
        self.assertEqual(x["status"],"ROOM_UNAVAILABLE")
    def test_exceptional_lifecycle_separate_review_required(self):
        p=self.inputs();p["capital_source"]="EXCEPTIONAL_LIFECYCLE_REVIEW"
        x=self.runroom(room_inputs=p)
        self.assertIn("EXCEPTIONAL_ACTION_REQUIRES_SEPARATE_THESIS_AND_COST_REVIEW",x["missing_or_qualified"])
    def test_no_implicit_sale_or_weights(self):
        x=self.runroom()
        self.assertEqual(x["contribution_or_sale_proposal"],"NONE_NOT_AUTOMATED")
        self.assertNotIn("target_weight_pct",x)
    def test_no_mutation(self):
        raw=dict(request=self.request(),ir_capsule=self.ir(),observation=self.observation(),room_inputs=self.inputs())
        raw["exposures"]=self.exposure(raw["observation"])
        orig=copy.deepcopy(raw)
        prepare_portfolio_room_review(**raw)
        self.assertEqual(raw,orig)
    def test_missing_checks_rejected(self):
        p=self.inputs();del p["portfolio_checks"]["ACCOUNT_COSTS"]
        with self.assertRaisesRegex(ValueError,"EXACT_FOUR_PORTFOLIO_CHECKS"):
            self.runroom(room_inputs=p)
    def test_invalid_horizon_rejected(self):
        for n in (0,60,2.5,True,"3"):
            with self.subTest(horizon=n):
                p=self.inputs();p["horizon_years"]=n
                with self.assertRaisesRegex(ValueError,"HORIZON_INVALID"):
                    self.runroom(room_inputs=p)
    def test_no_evidenced_claim_status_accepted_from_input(self):
        p=self.inputs();p["research_axes"]["QUALITY"]["status"]="BROKER_VERIFIED"
        with self.assertRaisesRegex(ValueError,"CANNOT_DECLARE_INDEPENDENT"):
            self.runroom(room_inputs=p)
    def test_other_IR_facts_are_not_implicitly_approved(self):
        ir=self.ir();ir["facts"].append(dict(id="OTHER",status="MISSING"))
        x=self.runroom(ir_capsule=ir)
        self.assertEqual(x["status"],"ROOM_CONDITIONAL")
        self.assertEqual(x["independent_evidence_check"],"NOT_PERFORMED")

if __name__=='__main__': unittest.main()
