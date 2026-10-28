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

    def test_pi_only_arithmetic_requires_ir_m7a_route(self):
        with self.assertRaisesRegex(ValueError,"PORTFOLIO_ARITHMETIC_REQUIRES_IR_PI_M7A_ROUTE"):
            complete_manual_session(self.request(research_needed=False,portfolio_needed=True),
                                    pi_delta=self.pi(),contribution_inputs={})

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

if __name__ == "__main__": unittest.main()
