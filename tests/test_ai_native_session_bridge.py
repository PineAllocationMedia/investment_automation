import copy
import unittest
from ai_native.session_bridge import complete_manual_session

class SessionBridgeTests(unittest.TestCase):
    def request(self, **patch):
        out = {"ceo_initiated":True,"research_needed":True,"portfolio_needed":False,
               "analysis_id":"CASE-A","as_of":"2026-10-28","objective":"Compare synthetic issuers",
               "kind":"DECISION","strategy_id":"EXPLORATORY"}
        out.update(patch)
        return out

    def ir(self, **patch):
        out = {"analysis_id":"CASE-A", "research_as_of":"2026-10-28", "summary":["Unverified"],
               "facts":[{"id":"F1","status":"INDICATIVE","claim":"Synthetic"}],
               "limitations":"Source not authenticated", "countercase":"Revenue unknown",
               "decision_line":"No executable conclusion", "next_action":"Check original filings"}
        out.update(patch)
        return out

    def pi(self, **patch):
        out = {"analysis_id":"CASE-A","portfolio_as_of":"2026-10-28", "room_status":"ROOM_UNAVAILABLE",
               "summary":"Insufficient positions", "limitations":"Cash unknown", "next_action":"Supply dated view"}
        out.update(patch)
        return out

    def test_direct_returns_no_specialist_no_report(self):
        out=complete_manual_session(self.request(research_needed=False))
        self.assertEqual(out["status"], "CC_DIRECT_NO_SPECIALIST_REPORT_REQUIRED")
        self.assertIsNone(out["final_report_private"])

    def test_missing_ceo_mandate_rejected(self):
        with self.assertRaisesRegex(ValueError,"CEO_INITIATION_REQUIRED"):
            complete_manual_session(self.request(ceo_initiated=False))

    def test_research_only_handoff_pending(self):
        out=complete_manual_session(self.request())
        self.assertEqual(out["status"],"AWAITING_MANUAL_IR_CAPSULE")
        self.assertIn("IR_REQUEST",out["handoffs_private"]["copy_ready_private"])

    def test_ir_report_uses_prepared_context_and_method_version(self):
        out=complete_manual_session(self.request(ir_method_version="REAL_METHOD_R1"),ir_capsule=self.ir())
        self.assertEqual(out["status"],"M7A_COMPONENT_ASSEMBLED_NOT_END_TO_END_ACCEPTANCE")
        self.assertIn("REAL_METHOD_R1",out["integrated_private"]["markdown"])

    def test_missing_method_is_not_invented(self):
        out=complete_manual_session(self.request(),ir_capsule=self.ir())
        self.assertIn("UNKNOWN_NOT_LOADED",out["integrated_private"]["markdown"])

    def test_ir_then_pi_requires_ir_first(self):
        out=complete_manual_session(self.request(portfolio_needed=True))
        self.assertEqual(out["status"],"AWAITING_MANUAL_IR_CAPSULE")

    def test_ir_then_pi_waits_for_pi_and_carries_exact_ir(self):
        capsule=self.ir()
        out=complete_manual_session(self.request(portfolio_needed=True),ir_capsule=capsule)
        self.assertEqual(out["status"],"AWAITING_MANUAL_PI_DELTA")
        self.assertEqual(out["handoffs_private"]["pi_request_private"]["FORWARD_UNCHANGED"],capsule)

    def test_ir_pi_finalization_does_not_mutate_sources(self):
        capsule=self.ir()
        pi=self.pi(forwarded_ir=copy.deepcopy(capsule))
        before=copy.deepcopy((capsule,pi))
        out=complete_manual_session(self.request(portfolio_needed=True),ir_capsule=capsule,pi_delta=pi)
        self.assertEqual(out["status"],"M7A_COMPONENT_ASSEMBLED_NOT_END_TO_END_ACCEPTANCE")
        self.assertEqual((capsule,pi),before)

    def test_forwarded_ir_mutation_rejected(self):
        with self.assertRaisesRegex(ValueError,"PACKET_INCOMPLETE"):
            complete_manual_session(self.request(portfolio_needed=True),ir_capsule=self.ir(),
                                    pi_delta=self.pi(forwarded_ir={"altered":True}))

    def test_pi_only_pending(self):
        out=complete_manual_session(self.request(research_needed=False,portfolio_needed=True))
        self.assertEqual(out["status"],"AWAITING_MANUAL_PI_DELTA")
        self.assertNotIn("IR_REQUEST",out["handoffs_private"]["copy_ready_private"])

    def test_pi_only_conditional_no_issuer_facts(self):
        out=complete_manual_session(self.request(research_needed=False,portfolio_needed=True),pi_delta=self.pi())
        self.assertEqual(out["status"],"PI_ONLY_CONDITIONAL_REPORT_ASSEMBLED")
        self.assertIn("Cash unknown",out["final_report_private"])
        self.assertIsNone(out["integrated_private"])

    def test_pi_only_asof_future_blocked(self):
        with self.assertRaisesRegex(ValueError,"NEWER_THAN_CUTOFF"):
            complete_manual_session(self.request(research_needed=False,portfolio_needed=True),
                                    pi_delta=self.pi(portfolio_as_of="2026-10-29"))

    def test_pi_only_identity_blocked(self):
        with self.assertRaisesRegex(ValueError,"PI_ANALYSIS_ID_MISMATCH"):
            complete_manual_session(self.request(research_needed=False,portfolio_needed=True),
                                    pi_delta=self.pi(analysis_id="WRONG"))

    def test_unrequested_pi_blocked(self):
        with self.assertRaisesRegex(ValueError,"PI_DELTA_UNREQUESTED"):
            complete_manual_session(self.request(),pi_delta=self.pi())

    def test_arithmetic_requires_a_pi_route_and_cost_requires_contribution(self):
        with self.assertRaisesRegex(ValueError, "PORTFOLIO_ARITHMETIC_REQUIRES_PI_ROUTE"):
            complete_manual_session(self.request(), contribution_inputs={})
        with self.assertRaisesRegex(ValueError, "COST_INPUTS_REQUIRE_CONTRIBUTION_INPUTS"):
            complete_manual_session(self.request(research_needed=False, portfolio_needed=True),
                                    pi_delta=self.pi(), cost_inputs={})

    def test_memory_without_ir_blocked(self):
        with self.assertRaisesRegex(ValueError,"MEMORY_PACKET_REQUIRES_IR_CAPSULE"):
            complete_manual_session(self.request(research_needed=False,portfolio_needed=True),memory_inputs={})

    def test_unrequested_portfolio_context_blocked(self):
        with self.assertRaisesRegex(ValueError,"PORTFOLIO_CONTEXT_UNREQUESTED"):
            complete_manual_session(self.request(),portfolio_context={})

    def test_no_automatic_actions(self):
        out=complete_manual_session(self.request())
        self.assertEqual(out["project_invocation"],"NONE")
        self.assertEqual(out["storage"],"NONE")
        self.assertEqual(out["readiness"],"NOT_EVALUATED")

    def test_ir_only_minimal_assembler_double_has_no_pi_trace(self):
        from unittest.mock import patch
        with patch("ai_native.session_bridge.assemble_manual_run",
                   return_value={"markdown": "SYN MINIMAL REPORT"}):
            out = complete_manual_session(self.request(), ir_capsule=self.ir())
        self.assertEqual(out["status"], "M7A_COMPONENT_ASSEMBLED_NOT_END_TO_END_ACCEPTANCE")
        self.assertIsNone(out["mode_portfolio_trace_private"])
        self.assertEqual(out["final_report_private"], "SYN MINIMAL REPORT")

    def test_combined_legacy_return_without_mode_answers_stays_compatible(self):
        from unittest.mock import patch
        ir = self.ir()
        delta = self.pi(forwarded_ir=copy.deepcopy(ir))
        with patch("ai_native.session_bridge.assemble_manual_run",
                   return_value={"markdown": "SYN COMBINED REPORT"}):
            out = complete_manual_session(
                self.request(portfolio_needed=True), ir_capsule=ir, pi_delta=delta)
        self.assertIsNone(out["mode_portfolio_trace_private"])
        self.assertEqual(delta["forwarded_ir"], ir)
        self.assertEqual(out["final_report_private"], "SYN COMBINED REPORT")

    def test_pi_response_is_not_silently_lost_in_minimal_integration(self):
        from unittest.mock import patch
        ir = self.ir()
        delta = self.pi(forwarded_ir=copy.deepcopy(ir),
                        MODE_PORTFOLIO_RESPONSES={"synthetic": "supplied"})
        with patch("ai_native.session_bridge.assemble_manual_run",
                   return_value={"markdown": "SYN LOST RESULT"}):
            with self.assertRaisesRegex(
                    ValueError, "MODE_PI_TRACE_NOT_RETURNED_BY_INTEGRATION"):
                complete_manual_session(
                    self.request(portfolio_needed=True), ir_capsule=ir,
                    pi_delta=delta)

    def test_actual_ir_pi_mode_trace_survives_original_capsule(self):
        ir = self.ir()
        original = copy.deepcopy(ir)
        answers = [{"question_index": k, "status": "UNKNOWN", "p_ids": []}
                   for k in (1, 2)]
        delta = self.pi(
            forwarded_ir=copy.deepcopy(ir), strategy_id="balanced",
            MODE_PORTFOLIO_RESPONSES={
                "analysis_id": "CASE-A", "portfolio_as_of": "2026-10-28",
                "strategy_id": "balanced", "answers": answers})
        out = complete_manual_session(
            self.request(portfolio_needed=True, strategy_id="balanced"),
            ir_capsule=ir, pi_delta=delta)
        trace = out["mode_portfolio_trace_private"]
        self.assertEqual(trace, out["integrated_private"]["mode_portfolio_trace_private"])
        self.assertEqual(trace["status"], "PRIVATE_MODE_PI_TRACE_NOT_AUTHENTICATED")
        self.assertEqual(trace["observation_link_status"], "NO_P_LEDGER")
        self.assertEqual([row["review_stage"] for row in trace["questions_private"]],
                         ["NOT_ASSESSED", "NOT_ASSESSED"])
        self.assertIn("Mode-specific PI research", out["final_report_private"])
        self.assertEqual(ir, original)
        self.assertEqual(out["project_invocation"], "NONE")
        self.assertEqual(out["storage"], "NONE")


    def test_private_history_comparison_handoff_preserves_subject(self):
        from unittest.mock import patch
        payload = {"prior_case":None, "subject_id":"SYN-ISSUER", "fact_links":[]}
        req = self.request(kind="FOLLOWUP", subject_id="SYN-ISSUER",
                           prior_analysis_id="SYN-OLD")
        with patch("ai_native.session_bridge.assemble_manual_run",
                   return_value={"markdown":"SYNTHETIC REPORT"}) as call:
            out = complete_manual_session(req, ir_capsule=self.ir(),
                                          historical_comparison_inputs=payload)
        self.assertEqual(call.call_args.args[0]["subject_id"], "SYN-ISSUER")
        self.assertEqual(call.call_args.kwargs["historical_comparison_inputs"], payload)
        self.assertEqual(out["project_invocation"], "NONE")
        self.assertEqual(out["storage"], "NONE")


    def test_opportunity_research_packet_forwards_only_to_ir_flow(self):
        from unittest.mock import patch
        payload = {"analysis_id":"CASE-A", "analysis_as_of":"2026-10-28",
                   "strategy_id":"EXPLORATORY", "universe_scope":"WATCHLIST",
                   "universe_note":"Synthetic only", "candidates":[]}
        with patch("ai_native.session_bridge.assemble_manual_run",
                   return_value={"markdown":"SYNTHETIC REPORT"}) as called:
            out = complete_manual_session(self.request(), ir_capsule=self.ir(),
                                          opportunity_triage_inputs=payload)
        self.assertEqual(called.call_args.kwargs["opportunity_triage_inputs"], payload)
        self.assertEqual(out["project_invocation"], "NONE")
        self.assertEqual(out["storage"], "NONE")

    def test_opportunity_research_not_accepted_without_ir_route(self):
        with self.assertRaisesRegex(ValueError, "OPPORTUNITY_TRIAGE_REQUIRES_IR_ROUTE"):
            complete_manual_session(self.request(research_needed=False,portfolio_needed=True),
                                    pi_delta=self.pi(),opportunity_triage_inputs={})




    def test_ir_evidence_annex_roundtrip_through_pi_stays_private_and_unchanged(self):
        evidence = {"analysis_id":"CASE-A", "analysis_as_of":"2026-10-28",
                    "observations":[]}
        capsule = self.ir(EVIDENCE_ANNEX=evidence)
        before = copy.deepcopy(capsule)
        pi = self.pi(forwarded_ir=copy.deepcopy(capsule))
        out = complete_manual_session(
            self.request(portfolio_needed=True), ir_capsule=capsule, pi_delta=pi)
        self.assertEqual(capsule, before)
        self.assertEqual(out["handoffs_private"]["pi_request_private"]["FORWARD_UNCHANGED"], before)
        self.assertEqual(out["integrated_private"]["source_evidence_annex_private"]["observation_count"], 0)
        self.assertEqual(out["integrated_private"]["fact_source_alignment_private"]["facts_needing_review"], 1)
        self.assertEqual(out["project_invocation"], "NONE")
        self.assertEqual(out["storage"], "NONE")


    def test_source_review_visible_in_session_report_not_only_private_annex(self):
        capsule = self.ir(EVIDENCE_ANNEX={
            "analysis_id":"CASE-A", "analysis_as_of":"2026-10-28",
            "observations":[]})
        output = complete_manual_session(self.request(), ir_capsule=capsule)
        self.assertIn("NO_OBSERVATION_FOR_IR_FACT", output["final_report_private"])
        self.assertIn("Source reconciliation:", output["final_report_private"])
        self.assertEqual(output["integrated_private"]["fact_source_alignment_private"]["facts_needing_review"], 1)
        self.assertEqual(output["storage"], "NONE")


    def new_contribution_inputs(self, **patch):
        out = {"positions_base":{"ABC:TSX":"400.00","VFV:TSX":"600.00"},
               "allocations_pct":{"ABC:TSX":"60","VFV:TSX":"40"},
               "contribution_base":"1000.00","currency":"CAD","as_of":"2026-10-28",
               "scope_complete":True,"cash_accounted_for":True,
               "same_currency_basis_verified":True,"instrument_identity_verified":True}
        out.update(patch)
        return out

    def new_cost_inputs(self, funding="FROM_CONTRIBUTION"):
        kinds = ("commission","bid_ask_spread","fx_conversion","purchase_tax","other_fees")
        costs = {key:{k:{"amount_base":"0.00","source_ref":"SYN-ZERO"} for k in kinds}
                 for key in ("ABC:TSX","VFV:TSX")}
        costs["ABC:TSX"]["commission"] = {"amount_base":"5.00","source_ref":"SYN-FEE"}
        return {"charges_by_destination":costs,"cost_currency":"CAD",
                "cost_quote_as_of":"2026-10-28","analysis_as_of":"2026-10-28",
                "funding":funding}

    def test_pi_only_new_contribution_without_fake_ir(self):
        request = self.request(research_needed=False, portfolio_needed=True)
        source = self.new_contribution_inputs()
        before = copy.deepcopy(source)
        out = complete_manual_session(request, pi_delta=self.pi(), contribution_inputs=source)
        self.assertEqual(source, before)
        self.assertIsNone(out["integrated_private"])
        self.assertEqual(out["status"], "PI_ONLY_CONDITIONAL_REPORT_ASSEMBLED")
        self.assertEqual(out["gross_contribution_private"]["status"], "GROSS_PROJECTION_ONLY")
        self.assertIn("60% of new capital", out["final_report_private"])
        self.assertIn("Costs/funding NOT ASSESSED", out["final_report_private"])
        self.assertNotIn("400.00", out["final_report_private"])
        self.assertNotIn("1000.00", out["final_report_private"])
        self.assertNotIn("IR_REQUEST", out["handoffs_private"]["copy_ready_private"])
        self.assertEqual(out["storage"], "NONE")
        self.assertEqual(out["project_invocation"], "NONE")

    def test_pi_only_fixed_cost_funding_remains_conditional(self):
        out = complete_manual_session(
            self.request(research_needed=False, portfolio_needed=True),
            pi_delta=self.pi(), contribution_inputs=self.new_contribution_inputs(),
            cost_inputs=self.new_cost_inputs(),
        )
        self.assertEqual(out["funded_contribution_private"]["conditional_purchase_budget_base"], "995.00")
        self.assertIn("CONDITIONALLY RECONCILED", out["final_report_private"])
        self.assertNotIn("995.00", out["final_report_private"])
        self.assertEqual(out["funded_contribution_private"]["execution_status"],
                         "UNAVAILABLE_NOT_EXECUTION_CERTIFIED")

    def test_pi_only_unknown_funding_cannot_claim_net_projection(self):
        out = complete_manual_session(
            self.request(research_needed=False, portfolio_needed=True),
            pi_delta=self.pi(), contribution_inputs=self.new_contribution_inputs(),
            cost_inputs=self.new_cost_inputs(funding="UNKNOWN"),
        )
        self.assertEqual(out["funded_contribution_private"]["status"], "UNAVAILABLE_FUNDING_UNKNOWN")
        self.assertIn("After-cost funded allocation UNAVAILABLE", out["final_report_private"])

    def test_pi_only_unavailable_scope_displays_no_allocation(self):
        out = complete_manual_session(
            self.request(research_needed=False, portfolio_needed=True),
            pi_delta=self.pi(), contribution_inputs=self.new_contribution_inputs(scope_complete=False),
        )
        self.assertEqual(out["gross_contribution_private"]["status"], "UNAVAILABLE")
        self.assertIn("Gross contribution projection UNAVAILABLE", out["final_report_private"])
        self.assertNotIn("60% of new capital", out["final_report_private"])

    def test_pi_only_date_mismatch_and_no_pi_are_guarded(self):
        req = self.request(research_needed=False, portfolio_needed=True)
        pending = complete_manual_session(req, contribution_inputs=self.new_contribution_inputs())
        self.assertEqual(pending["status"], "AWAITING_MANUAL_PI_DELTA")
        self.assertIsNone(pending["gross_contribution_private"])
        with self.assertRaisesRegex(ValueError, "exact PI portfolio observation date"):
            complete_manual_session(req, pi_delta=self.pi(),
                contribution_inputs=self.new_contribution_inputs(as_of="2026-10-27"))
        with self.assertRaisesRegex(ValueError, "analysis cutoff"):
            complete_manual_session(req, pi_delta=self.pi(),
                contribution_inputs=self.new_contribution_inputs(),
                cost_inputs={**self.new_cost_inputs(), "analysis_as_of":"2026-10-27"})

    def test_pi_only_cannot_upgrade_incomplete_observation_scope(self):
        from unittest.mock import patch
        request = self.request(research_needed=False, portfolio_needed=True)
        with patch("ai_native.session_bridge.prepare_observation_ledger",
                   return_value={"observed_on":"2026-10-28","known_scope_weights_pct":None,
                                  "private_scope":True}):
            with self.assertRaisesRegex(ValueError, "PI_CONTRIBUTION_SCOPE_CONFLICTS_WITH_OBSERVATION"):
                complete_manual_session(
                    request, pi_delta=self.pi(), observation_inputs={
                        "analysis_id":"CASE-A", "analysis_as_of":"2026-10-28"},
                    contribution_inputs=self.new_contribution_inputs())


    def test_valuation_scenarios_pass_through_manual_ir_route_without_upgrade(self):
        from unittest.mock import patch
        args = {"analysis_id":"CASE-A", "analysis_as_of":"2026-10-28"}
        with patch("ai_native.session_bridge.assemble_manual_run",
                   return_value={"markdown":"SYN REPORT"}) as call:
            out = complete_manual_session(self.request(), ir_capsule=self.ir(),
                                          valuation_inputs=args)
        self.assertEqual(call.call_args.kwargs["valuation_inputs"], args)
        self.assertEqual(out["storage"], "NONE")
        self.assertEqual(out["project_invocation"], "NONE")


    def test_portfolio_room_review_reaches_final_report_on_ir_pi_route(self):
        from unittest.mock import patch
        req = self.request(portfolio_needed=True)
        original = self.ir()
        pi = self.pi(forwarded_ir=copy.deepcopy(original))
        reviewed = {
            "analysis_id":"CASE-A", "as_of":"2026-10-28", "observed_on":"2026-10-28",
            "status":"ROOM_UNAVAILABLE",
            "research_axes_private":{k:{"status":"UNKNOWN","ir_fact_ids":[]}
                for k in ("QUALITY","DURABILITY","EXPECTED_RETURN","CONFIDENCE")},
            "portfolio_checks_private":{k:{"status":"UNKNOWN","source_ref":None}
                for k in ("CONCENTRATION","CORRELATED_DRIVERS","ALTERNATIVES","ACCOUNT_COSTS")},
            "known_candidate_issuer_exposure_pct_private":None,
            "unclassified_lookthrough_pct_private":None,
            "missing_or_qualified":["ACCOUNT_TYPE_UNKNOWN"],
            "portfolio_room_authority":"QUALITATIVE_SPECIALIST_REPORTED_ONLY",
            "independent_evidence_check":"NOT_PERFORMED",
            "contribution_or_sale_proposal":"NONE_NOT_AUTOMATED",
            "trade_authority":"NONE_CEO_ONLY","public_memory_write":"NONE",
        }
        with patch("ai_native.session_bridge.prepare_observation_ledger",
                   return_value={"observed_on":"2026-10-28", "known_scope_weights_pct":None}), \
             patch("ai_native.session_bridge.aggregate_portfolio_exposures",
                   return_value={"status":"UNAVAILABLE_INCOMPLETE_P_LEDGER"}), \
             patch("ai_native.session_bridge.prepare_portfolio_room_review",
                   return_value=reviewed):
            result=complete_manual_session(
                req, ir_capsule=original, pi_delta=pi,
                observation_inputs={"analysis_id":"CASE-A","analysis_as_of":"2026-10-28"},
                exposure_classifications={},
                room_assessment_inputs={"synthetic":"inputs"},
            )
        self.assertIn("Portfolio Room — caller-reported", result["final_report_private"])
        self.assertIn("ROOM_UNAVAILABLE", result["final_report_private"])
        self.assertEqual(result["integrated_private"]["memory_proposal_nonprivate"]["archive_status"],
                         "PROPOSED_NOT_COMMITTED")
        self.assertNotIn("ACCOUNT_TYPE_UNKNOWN", str(result["integrated_private"]["memory_proposal_nonprivate"]))
        self.assertEqual(result["portfolio_room_review_private"], reviewed)

    def test_portfolio_room_no_pi_stays_pending(self):
        from unittest.mock import patch
        with patch("ai_native.session_bridge.prepare_observation_ledger",
                   return_value={"observed_on":"2026-10-28"}), \
             patch("ai_native.session_bridge.aggregate_portfolio_exposures",
                   return_value={"status":"UNAVAILABLE_INCOMPLETE_P_LEDGER"}), \
             patch("ai_native.session_bridge.prepare_portfolio_room_review",
                   return_value={"analysis_id":"CASE-A"}):
            output = complete_manual_session(
                self.request(portfolio_needed=True), ir_capsule=self.ir(),
                observation_inputs={"analysis_id":"CASE-A","analysis_as_of":"2026-10-28"},
                exposure_classifications={}, room_assessment_inputs={"synthetic":"inputs"},
            )
        self.assertEqual(output["status"], "AWAITING_MANUAL_PI_DELTA")
        self.assertIsNone(output["final_report_private"])

if __name__ == "__main__": unittest.main()
