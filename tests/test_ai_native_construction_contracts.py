"""R1 synthetic cross-component contracts, NOT comprehensive acceptance.

Real M1/M2/M3/M4 helper functions; M7a reporter is mocked only to assert
manual-call arguments. No live Projects, accounts, financial data or writes.
"""
import copy
import unittest
from unittest.mock import patch

from ai_native.portfolio_observation import prepare_observation_ledger
from ai_native.portfolio_exposure import aggregate_portfolio_exposures
from ai_native.source_fusion import assemble_source_fusion
from ai_native.valuation_scenarios import evaluate_valuation_scenarios
from ai_native.research_memory import prepare_research_history
from ai_native.session_bridge import complete_manual_session


class R1ConstructionContracts(unittest.TestCase):
    def request(self, research=True, portfolio=False):
        return dict(ceo_initiated=True, research_needed=research,
                    portfolio_needed=portfolio, analysis_id="SYN-X", as_of="2026-10-28",
                    kind="DECISION", objective="Synthetic comparison",
                    strategy_id="EXPLORATORY", method_version="R1",
                    ir_method_version="R1")

    def capsule(self):
        return dict(analysis_id="SYN-X", research_as_of="2026-10-27",
                    summary=["Conditional synthetic result"],
                    facts=[dict(id="F-1", claim="Synthetic information", status="INDICATIVE")],
                    limitations="No original source authentication",
                    countercase="Unobserved risks", decision_line="No trade",
                    next_action="Verify original sources")

    def observation(self, complete=True):
        return dict(analysis_id="SYN-X", observed_on="2026-10-28",
                    analysis_as_of="2026-10-28", captured_at="2026-10-28T10:00:00-04:00",
                    source_type="PRIVATE_USER_TABLE", private_scope=True,
                    source_access_confirmed_by_caller=True,
                    account_scope="SYN-SCOPE", currency="CAD", scope_complete=complete,
                    cash_base="100.00", cash_visibility="VERIFIED_VISIBLE",
                    same_currency_basis_confirmed_by_caller=True, positions=[
                        dict(p_id=p, security_id=t, market_value_base=v,
                             account_scope="SYN-SCOPE", currency="CAD",
                             field_statuses={k:"VERIFIED_VISIBLE" for k in
                                 ("security_id","market_value_base","currency","account_scope")})
                        for p,t,v in (("P1","ABC:TSX","300.00"),
                                      ("P2","FUND:TSX","600.00"))])

    def classes(self, fund_rights="PERMITTED"):
        return {
            "P1":dict(kind="DIRECT_EQUITY", security_id="ABC:TSX",source_ref="S1",
                      as_of="2026-10-27",rights_status="PERMITTED",
                      economic_issuer_id="ABC",sector="TECH",region="CANADA"),
            "P2":dict(kind="FUND",security_id="FUND:TSX",source_ref="S2",
                      as_of="2026-10-28",rights_status=fund_rights,
                      composition_complete_reported=False,constituents=[
                          dict(economic_issuer_id="ABC",sector="TECH",region="CANADA",
                               fund_weight_pct="25")])}

    def source(self):
        return dict(observation_id="OBS1",fact_id="F-1",source_id="SRC1",
                    economic_issuer="ABC",instrument="ABC:TSX",metric="REVENUE",
                    period_start="2025-01-01",period_end="2025-12-31",
                    currency="CAD",unit="MILLIONS",definition_basis="IFRS",
                    consolidation="GROUP",value="100",observed_at="2026-10-27",
                    published_at="2026-01-10",original_checked_at=None,
                    source_kind="SECONDARY",classification="SOURCE_FACT",
                    source_locator="https://example.org/synthetic",
                    rights_status="UNCERTAIN",verification_status="INDICATIVE")

    def valuation(self):
        rows={k:dict(valuation_method="OTHER_EXPLICIT",assumption_basis="PAM_ASSUMPTION",
                     rationale_ref="SYN-R",terminal_value_ref="SYN-V",
                     terminal_price_per_share=v,annual_distributions_per_share=None)
              for k,v in (("BEAR","81"),("BASE","121"),("BULL","144"))}
        return dict(analysis_id="SYN-X",analysis_as_of="2026-10-28",
                    security_id="ABC:TSX",currency="CAD",quoted_at="2026-10-27",
                    quote_source_ref="SYN-QUOTE",price_per_share="100",horizon_years=2,
                    security_basis_confirmed_by_caller=True,
                    currency_basis_confirmed_by_caller=True,scenarios=rows)

    def test_shared_identity_and_distinct_dates(self):
        p=prepare_observation_ledger(**self.observation())
        e=aggregate_portfolio_exposures(p,classifications_by_p_id=self.classes())
        f=assemble_source_fusion(analysis_id="SYN-X",analysis_as_of="2026-10-28",observations=[self.source()])
        v=evaluate_valuation_scenarios(**self.valuation())
        h=prepare_research_history(self.request(),self.capsule(),
                                   report_id="SYN-REPORT",instruction_version="R1",
                                   recorded_at="2026-10-28")
        self.assertTrue(all(x["analysis_id"]=="SYN-X" for x in
                            (p,e,f,v,h["private_research_history_proposal"])))
        self.assertEqual(f["observations_private"][0]["published_at"],"2026-01-10")
        self.assertEqual(v["quoted_at"],"2026-10-27")

    def test_partial_fund_exposure_is_lower_bound_not_room(self):
        p=prepare_observation_ledger(**self.observation())
        e=aggregate_portfolio_exposures(p,classifications_by_p_id=self.classes())
        self.assertEqual(e["economic_issuer_pct_private"],{"ABC":"45.00"})
        self.assertEqual(e["unclassified_or_unknown_fund_pct"],"45.00")
        self.assertFalse(e["economic_issuer_rank_coverage_reported_complete"])
        self.assertEqual(e["portfolio_room_status"],"ROOM_UNAVAILABLE")

    def test_fund_rights_uncertain_becomes_unknown(self):
        p=prepare_observation_ledger(**self.observation())
        e=aggregate_portfolio_exposures(p,classifications_by_p_id=self.classes("UNCERTAIN"))
        self.assertEqual(e["economic_issuer_pct_private"],{"ABC":"30.00"})
        self.assertEqual(e["unclassified_or_unknown_fund_pct"],"60.00")

    def test_incomplete_observation_cannot_create_exposures(self):
        p=prepare_observation_ledger(**self.observation(False))
        e=aggregate_portfolio_exposures(p,classifications_by_p_id=self.classes())
        self.assertEqual(e["status"],"UNAVAILABLE_INCOMPLETE_P_LEDGER")
        self.assertIsNone(e["economic_issuer_pct_private"])

    def test_uncertain_source_cannot_gain_verification(self):
        f=assemble_source_fusion(analysis_id="SYN-X",analysis_as_of="2026-10-28",
                                 observations=[self.source()])
        self.assertEqual(f["observations_private"][0]["claim_use_status"],"INCOMPLETE")
        self.assertEqual(f["source_authentication"],"NOT_PERFORMED_BY_CODE")

    def test_scenario_price_cagr_is_not_total_return_or_alpha(self):
        v=evaluate_valuation_scenarios(**self.valuation())
        self.assertEqual(v["scenarios_private"]["BASE"]["scenario_return_pct_annual"],"10.00")
        self.assertEqual(v["scenarios_private"]["BASE"]["return_measure"],
                         "PRICE_ONLY_CAGR_NOT_TOTAL_RETURN")
        self.assertIn("VFV_ER_UNAVAILABLE",v["benchmark_expected_return_status"])

    def test_private_history_gate_has_no_source_or_account_content(self):
        h=prepare_research_history(self.request(),self.capsule(),report_id="SYN-REPORT",
                                   instruction_version="R1",recorded_at="2026-10-28")
        self.assertFalse(h["github_review_gate"]["approved_for_publication"])
        self.assertNotIn("SYN-X",str(h["github_review_gate"]))
        self.assertEqual(h["private_research_history_proposal"]["archive_status"],
                         "PROPOSED_NOT_COMMITTED")

    def test_pi_pending_carries_scoped_private_exposures_without_report(self):
        x=complete_manual_session(self.request(False,True),
                                  observation_inputs=self.observation(),
                                  exposure_classifications=self.classes())
        self.assertEqual(x["status"],"AWAITING_MANUAL_PI_DELTA")
        self.assertEqual(x["portfolio_exposures_private"]["known_exposure_pct"],"45.00")
        self.assertIsNone(x["final_report_private"])
        self.assertEqual(x["project_invocation"],"NONE")

    def test_pi_supported_room_rejected_on_partial_fund(self):
        pi=dict(analysis_id="SYN-X",portfolio_as_of="2026-10-28",
                room_status="ROOM_EVIDENCE_SUPPORTED",summary="Synthetic",
                limitations="Unknown",next_action="Review")
        with self.assertRaisesRegex(ValueError,"ROOM_ASSERTION_UNSUPPORTED"):
            complete_manual_session(self.request(False,True),pi_delta=pi,
                                    observation_inputs=self.observation(),
                                    exposure_classifications=self.classes())

    def test_ir_to_pi_waits_for_original_capsule(self):
        pending=complete_manual_session(self.request(True,True))
        self.assertEqual(pending["status"],"AWAITING_MANUAL_IR_CAPSULE")
        ir=self.capsule()
        second=complete_manual_session(self.request(True,True),ir_capsule=ir)
        self.assertEqual(second["status"],"AWAITING_MANUAL_PI_DELTA")
        self.assertEqual(second["handoffs_private"]["pi_request_private"]["FORWARD_UNCHANGED"],ir)

    def test_source_and_scenario_forwarded_without_project_invocation(self):
        evidence=dict(analysis_id="SYN-X",analysis_as_of="2026-10-28",observations=[self.source()])
        valuation=self.valuation()
        with patch("ai_native.session_bridge.assemble_manual_run",
                   return_value={"markdown":"SYNTHETIC ONLY"}) as call:
            result=complete_manual_session(self.request(),ir_capsule=self.capsule(),
                                           source_evidence_inputs=evidence,valuation_inputs=valuation)
            self.assertEqual(call.call_args.kwargs["source_evidence_inputs"],evidence)
            self.assertEqual(call.call_args.kwargs["valuation_inputs"],valuation)
        self.assertEqual(result["method_load_verification"],"NOT_PERFORMED")
        self.assertEqual(result["project_invocation"],"NONE")

    def test_bypass_ir_or_observation_is_rejected(self):
        with self.assertRaisesRegex(ValueError,"VALUATION_REQUIRES_IR_CAPSULE"):
            complete_manual_session(self.request(False,True),valuation_inputs=self.valuation())
        with self.assertRaisesRegex(ValueError,"EXPOSURES_REQUIRE_PI_OBSERVATION"):
            complete_manual_session(self.request(False,True),exposure_classifications=self.classes())


if __name__=="__main__": unittest.main()
