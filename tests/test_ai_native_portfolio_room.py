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
    def test_unknown_portfolio_check_cannot_support_conditional_room(self):
        for check in ("CONCENTRATION", "CORRELATED_DRIVERS", "ALTERNATIVES",
                      "ACCOUNT_COSTS"):
            with self.subTest(check=check):
                inputs = self.inputs()
                inputs["portfolio_checks"][check]["status"] = "UNKNOWN"
                packet = self.runroom(room_inputs=inputs)
                self.assertEqual(packet["status"], "ROOM_UNAVAILABLE")
                self.assertIn(check + "_UNSUPPORTED_OR_UNKNOWN",
                              packet["missing_or_qualified"])
                self.assertEqual(packet["independent_evidence_check"], "NOT_PERFORMED")

    def test_unsourced_portfolio_check_cannot_support_conditional_room(self):
        for check in ("CONCENTRATION", "CORRELATED_DRIVERS", "ALTERNATIVES",
                      "ACCOUNT_COSTS"):
            with self.subTest(check=check):
                inputs = self.inputs()
                inputs["portfolio_checks"][check]["source_ref"] = None
                packet = self.runroom(room_inputs=inputs)
                self.assertEqual(packet["status"], "ROOM_UNAVAILABLE")
                self.assertIn(check + "_UNSUPPORTED_OR_UNKNOWN",
                              packet["missing_or_qualified"])

    def test_report_rejects_forged_conditional_room_when_check_unknown(self):
        from ai_native.reporting import render_report
        def report(room):
            return render_report({
                "kind":"DECISION", "analysis_id":"SYN-A", "as_of":"2026-10-28",
                "strategy":"SYN-EXPLORATORY", "method_version":"UNKNOWN_NOT_LOADED",
                "status":"CONDITIONAL", "objective":"Synthetic",
                "decision_line":"No trade", "summary":["SYN"], "facts":[],
                "countercase":"Unknown", "limitations":"Unverified",
                "next_action":"Review", "portfolio_room_review_private":room,
            })
        original = self.runroom()
        self.assertIn("ROOM_CONDITIONAL", report(original))
        for key, value in (("status", "UNKNOWN"), ("source_ref", None)):
            with self.subTest(key=key):
                forged = copy.deepcopy(original)
                forged["portfolio_checks_private"]["ACCOUNT_COSTS"][key] = value
                with self.assertRaisesRegex(ValueError, "CONDITIONAL_SUPPORT_MISSING"):
                    report(forged)
        forged = copy.deepcopy(original)
        forged["research_axes_private"]["CONFIDENCE"]["ir_fact_ids"] = []
        with self.assertRaisesRegex(ValueError, "CONDITIONAL_SUPPORT_MISSING"):
            report(forged)

    def test_historical_fund_room_cannot_be_forged_conditional(self):
        from ai_native.reporting import render_report
        c = {"P1":dict(security_id="ABC:TSX", kind="FUND",
            source_ref="SYN-OLD", rights_status="PERMITTED",
            as_of="2026-10-27", composition_complete_reported=True,
            constituents=[dict(economic_issuer_id="ABC",sector="TECH",
                               region="CANADA",fund_weight_pct="100")])}
        room = self.runroom(exposures=self.exposure(classifications=c))
        self.assertEqual(room["status"], "ROOM_UNAVAILABLE")
        forged = copy.deepcopy(room)
        forged["status"] = "ROOM_CONDITIONAL"
        # Force a bogus non-null known issuer bound to reach the distinct
        # historical-fund anti-promotion guard in the report renderer.
        forged["known_candidate_issuer_exposure_pct_private"] = "0.00"
        packet={"kind":"DECISION", "analysis_id":"SYN-A", "as_of":"2026-10-28",
                "strategy":"SYN-EXPLORATORY", "method_version":"UNKNOWN_NOT_LOADED",
                "status":"CONDITIONAL", "objective":"Synthetic",
                "decision_line":"No trade", "summary":["SYN"], "facts":[],
                "countercase":"Unknown", "limitations":"Not verified",
                "next_action":"Review", "portfolio_room_review_private":forged}
        with self.assertRaisesRegex(ValueError, "HISTORICAL_FUND_CANNOT_BE_CONDITIONAL"):
            render_report(packet)

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

    def test_old_etf_constituents_do_not_support_current_portfolio_room(self):
        from ai_native.reporting import render_report
        c={"P1":dict(
            security_id="ABC:TSX", kind="FUND", source_ref="PRIVATE_PRIOR_FUND_SOURCE",
            rights_status="PERMITTED", as_of="2026-10-27",
            composition_complete_reported=True,
            constituents=[dict(economic_issuer_id="ABC",sector="TECH",
                               region="CANADA",fund_weight_pct="100")])}
        exp=self.exposure(classifications=c)
        room=self.runroom(exposures=exp)
        self.assertEqual(room["status"],"ROOM_UNAVAILABLE")
        self.assertIsNone(room["known_candidate_issuer_exposure_pct_private"])
        self.assertIn("HISTORICAL_FUND_COMPOSITION_NOT_CURRENT",
                      room["missing_or_qualified"])
        packet={"kind":"DECISION", "analysis_id":"SYN-A", "as_of":"2026-10-28",
                "strategy":"SYN-EXPLORATORY", "method_version":"UNKNOWN_NOT_LOADED",
                "status":"CONDITIONAL", "objective":"Synthetic",
                "decision_line":"No trade", "summary":["SYN"], "facts":[],
                "countercase":"Unknown", "limitations":"Not verified",
                "next_action":"Review", "portfolio_room_review_private":room}
        report=render_report(packet)
        self.assertIn("Fund constituent evidence predates",report)
        self.assertIn("Known supplied candidate-issuer exposure: UNKNOWN",report)
        self.assertNotIn("PRIVATE_PRIOR_FUND_SOURCE",report)
        self.assertNotIn("90.00% of the scoped portfolio",report)

    def test_direct_issuer_lower_bound_survives_old_overlapping_fund_without_room_upgrade(self):
        from ai_native.reporting import render_report
        obs = prepare_observation_ledger(
            analysis_id="SYN-A", observed_on="2026-10-28",
            analysis_as_of="2026-10-28", captured_at="2026-10-28T10:00:00-04:00",
            source_type="PRIVATE_USER_TABLE", private_scope=True,
            source_access_confirmed_by_caller=True, account_scope="SYN-ACCOUNT",
            currency="CAD", scope_complete=True, cash_base="100.00",
            cash_visibility="VERIFIED_VISIBLE", same_currency_basis_confirmed_by_caller=True,
            positions=[
                dict(p_id="P1", security_id="ABC:TSX", market_value_base="300.00",
                     account_scope="SYN-ACCOUNT", currency="CAD",
                     field_statuses={key:"VERIFIED_VISIBLE" for key in
                                     ("security_id","market_value_base","currency","account_scope")}),
                dict(p_id="P2", security_id="FUND:TSX", market_value_base="600.00",
                     account_scope="SYN-ACCOUNT", currency="CAD",
                     field_statuses={key:"VERIFIED_VISIBLE" for key in
                                     ("security_id","market_value_base","currency","account_scope")}),
            ])
        classifications = {
            "P1":dict(security_id="ABC:TSX",kind="DIRECT_EQUITY",
                      source_ref="SYN-DIRECT-SOURCE",rights_status="PERMITTED",
                      as_of="2026-10-27",economic_issuer_id="ABC",
                      sector="TECH",region="CANADA"),
            "P2":dict(security_id="FUND:TSX",kind="FUND",
                      source_ref="PRIVATE_PRIOR_FUND_SOURCE",rights_status="PERMITTED",
                      as_of="2026-10-27",composition_complete_reported=True,
                      constituents=[dict(economic_issuer_id="ABC",sector="TECH",
                                         region="CANADA",fund_weight_pct="100")]),
        }
        exposure = self.exposure(obs, classifications=classifications)
        self.assertEqual(exposure["economic_issuer_pct_private"]["ABC"], "30.00")
        self.assertEqual(exposure["unclassified_or_unknown_fund_pct"], "60.00")
        self.assertEqual(exposure["historical_fund_scenario_private"][
            "economic_issuer_pct_of_current_scope_private"]["ABC"], "60.00")
        room = self.runroom(observation=obs, exposures=exposure)
        self.assertEqual(room["status"], "ROOM_UNAVAILABLE")
        self.assertEqual(room["known_candidate_issuer_exposure_pct_private"], "30.00")
        self.assertEqual(room["unclassified_lookthrough_pct_private"], "60.00")
        self.assertIn("HISTORICAL_FUND_COMPOSITION_NOT_CURRENT",room["missing_or_qualified"])
        self.assertIn("HISTORICAL_FUND_EXCLUDED_FROM_KNOWN_LOWER_BOUND",room["missing_or_qualified"])
        self.assertEqual(room["contribution_or_sale_proposal"], "NONE_NOT_AUTOMATED")
        packet={"kind":"DECISION", "analysis_id":"SYN-A", "as_of":"2026-10-28",
                "strategy":"SYN-EXPLORATORY", "method_version":"UNKNOWN_NOT_LOADED",
                "status":"CONDITIONAL", "objective":"Synthetic current scoped exposure",
                "decision_line":"No trade", "summary":["SYN"], "facts":[],
                "countercase":"Unknown", "limitations":"Not verified",
                "next_action":"Review", "portfolio_room_review_private":room}
        report = render_report(packet)
        self.assertIn("Known supplied candidate-issuer exposure: 30.00%",report)
        self.assertIn("Unclassified/unknown fund look-through: 60.00%",report)
        self.assertIn("excludes ALL prior-dated fund constituents",report)
        self.assertIn("Portfolio Room remain UNAVAILABLE",report)
        for private in ("PRIVATE_PRIOR_FUND_SOURCE","SYN-DIRECT-SOURCE",
                        "300.00","600.00"):
            self.assertNotIn(private, report)

    def test_historical_known_lower_bound_without_qualification_rejected(self):
        from ai_native.reporting import render_report
        obs = self.observation()
        # Existing no-current-issuer historical case stays UNKNOWN.
        classified = {"P1":dict(
            security_id="ABC:TSX", kind="FUND",
            source_ref="PRIVATE_PRIOR_FUND_SOURCE", rights_status="PERMITTED",
            as_of="2026-10-27", composition_complete_reported=True,
            constituents=[dict(economic_issuer_id="ABC",sector="TECH",
                               region="CANADA",fund_weight_pct="100")])}
        room = self.runroom(observation=obs, exposures=self.exposure(obs, classifications=classified))
        self.assertIsNone(room["known_candidate_issuer_exposure_pct_private"])
        forged = copy.deepcopy(room)
        forged["known_candidate_issuer_exposure_pct_private"] = "90.00"
        packet={"kind":"DECISION", "analysis_id":"SYN-A", "as_of":"2026-10-28",
                "strategy":"SYN-EXPLORATORY", "method_version":"UNKNOWN_NOT_LOADED",
                "status":"CONDITIONAL", "objective":"Synthetic",
                "decision_line":"No trade", "summary":["SYN"], "facts":[],
                "countercase":"Unknown", "limitations":"Not verified",
                "next_action":"Review", "portfolio_room_review_private":forged}
        with self.assertRaisesRegex(ValueError,"HISTORICAL_LOWER_BOUND_UNQUALIFIED"):
            render_report(packet)

    def test_real_portfolio_room_review_renders_only_conditional_exposure(self):
        from ai_native.reporting import render_report
        room=self.runroom()
        packet={"kind":"DECISION", "analysis_id":"SYN-A", "as_of":"2026-10-28",
                "strategy":"SYN-EXPLORATORY", "method_version":"UNKNOWN_NOT_LOADED",
                "status":"CONDITIONAL", "objective":"Synthetic capital room",
                "decision_line":"No trade", "summary":["Synthetic observation only"],
                "facts":[], "countercase":"Unknown drivers",
                "limitations":"Not authenticated", "next_action":"Review facts",
                "portfolio_room_review_private":room}
        text=render_report(packet)
        self.assertIn("90.00% of the scoped portfolio",text)
        self.assertIn("ROOM_CONDITIONAL",text)
        self.assertIn("No target allocation",text)
        self.assertNotIn("Room may merit more review",text)

if __name__=='__main__': unittest.main()
