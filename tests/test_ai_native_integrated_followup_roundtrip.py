"""Synthetic integrated private history → new CEO follow-up through IR and PI.

No actual private positions, Project invocation, storage, investment-policy
approval or source authentication; uses real existing M1/M3/M4/M7a helpers.
"""
from __future__ import annotations

from copy import deepcopy
from io import StringIO
import json
import unittest

from ai_native.private_case_integrity import seal_private_case
from ai_native.portfolio_snapshot_transfer import seal_private_portfolio_snapshot
from scripts.r1_manual_session_cli import main
from tests.test_ai_native_session_bridge import SessionBridgeTests
from tests.test_ai_native_portfolio_observation import ObservationTests


class IntegratedHistoricalRoundTripTests(unittest.TestCase):
    def setUp(self):
        self.fx = SessionBridgeTests()
        self.ob = ObservationTests()

    def cli(self, payload, mode):
        inp = StringIO(json.dumps(payload, ensure_ascii=False))
        out, err = StringIO(), StringIO()
        rc = main(["--output", mode], instream=inp,
                  outstream=out, errstream=err)
        return rc, out.getvalue(), err.getvalue()

    def old(self):
        ir = self.fx.ir()
        ir["facts"][0]["claim"] = "OLD_RESEARCH_NOT_FOR_NEW_SPECIALIST"
        prior = {
            "request": self.fx.request(
                subject_id="SYN-ISSUER", portfolio_needed=True,
                account_context={"token": "PRIVATE_ACCOUNT_NOT_IN_RESEARCH_MEMORY"}),
            "ir_capsule": ir,
            "pi_delta": self.fx.pi(forwarded_ir=deepcopy(ir)),
            "observation_inputs": self.ob.kwargs(
                analysis_id="CASE-A", analysis_as_of="2026-10-28"),
            "memory_inputs": {
                "report_id": "R-OLD", "instruction_version": "R1-SYN",
                "recorded_at": "2026-10-28",
            },
        }
        rc, out, err = self.cli(prior, "private-integrated-closeout")
        self.assertEqual((rc, err), (0, ""))
        return json.loads(out)

    def current(self):
        observation = self.ob.kwargs(
            analysis_id="CASE-B", analysis_as_of="2026-10-29",
            observed_on="2026-10-29",
            captured_at="2026-10-29T10:00:00-04:00")
        return {
            "request": self.fx.request(
                analysis_id="CASE-B", as_of="2026-10-29",
                kind="FOLLOWUP", objective="New user-requested comparison",
                portfolio_needed=True, research_needed=True,
                subject_id="SYN-ISSUER", prior_analysis_id="CASE-A"),
            "observation_inputs": observation,
        }

    def test_exported_old_research_history_now_retains_only_route_provenance(self):
        old = self.old()
        case = old["private_case_envelope"]["private_case"]
        source = case["original_request"]
        self.assertIs(source["ceo_initiated"], True)
        self.assertIs(source["research_needed"], True)
        self.assertEqual(source["analysis_id"], "CASE-A")
        self.assertEqual(source["subject_id"], "SYN-ISSUER")
        self.assertNotIn("account_context", source)
        self.assertNotIn("portfolio_needed", source)
        self.assertNotIn("PRIVATE_ACCOUNT_NOT_IN_RESEARCH_MEMORY",
                         json.dumps(old["private_case_envelope"]))

    def test_integrated_followup_draft_is_inert_with_separate_portfolio_source(self):
        old = self.old()
        unchanged = deepcopy(old)
        rc, out, err = self.cli(
            {"prior_integrated_closeout": old}, "integrated-followup-draft")
        self.assertEqual((rc, err), (0, ""))
        draft = json.loads(out)
        self.assertEqual(draft["status"],
                         "PRIVATE_FOLLOWUP_DRAFT_REQUIRES_CEO_INITIATION")
        req = draft["input_template"]["request"]
        self.assertIs(req["ceo_initiated"], False)
        self.assertIsNone(req["analysis_id"])
        self.assertIsNone(req["as_of"])
        self.assertIsNone(req["objective"])
        self.assertIs(req["portfolio_needed"], False)
        self.assertNotIn("account_context", req)
        self.assertNotIn("positions", req)
        self.assertNotIn("prior_private_portfolio_envelope",
                         draft["input_template"])
        self.assertEqual(
            draft["private_portfolio_baseline_for_explicit_use"],
            old["private_portfolio_snapshot_envelope"])
        self.assertIn("new dated private observation",
                      " ".join(draft["human_checks"]).lower())
        self.assertEqual(old, unchanged)
        rc, result, err = self.cli(draft["input_template"], "next-handoff")
        self.assertEqual((rc, result), (2, ""))
        self.assertIn("CEO_INITIATION_REQUIRED", err)

    def test_one_fresh_mandate_roundtrips_old_ir_and_pi_through_manual_transfer(self):
        old = self.old()
        session = self.current()
        before = deepcopy(session)
        wrapper = {
            "prior_integrated_closeout": old,
            "session": session,
            "fact_links": [{"prior_fact_id":"F1", "current_fact_id":"F2"}],
        }
        rc, out, err = self.cli(wrapper, "integrated-followup-operator")
        self.assertEqual((rc, err), (0, ""))
        operator = json.loads(out)
        self.assertEqual(operator["session"]["status"], "AWAITING_MANUAL_IR_CAPSULE")
        self.assertEqual(operator["manual_copy_integrity"],
                         "SHA256_MATCHED_RETAINED_COPY_ONLY")
        ir_handoff = operator["continuation_private"]["next_handoff"]["IR_REQUEST"]
        self.assertNotIn("OLD_RESEARCH_NOT_FOR_NEW_SPECIALIST",
                         json.dumps(ir_handoff))
        self.assertNotIn("PRIVATE_ACCOUNT_NOT_IN_RESEARCH_MEMORY",
                         json.dumps(ir_handoff))
        self.assertIn("prior_private_portfolio_envelope",
                      operator["continuation_private"]["resume_input"])
        self.assertNotIn("prior_private_portfolio_envelope", json.dumps(ir_handoff))
        self.assertEqual(session, before)

        fresh_ir = self.fx.ir(
            analysis_id="CASE-B", research_as_of="2026-10-29",
            facts=[{"id":"F2", "status":"INDICATIVE",
                    "claim":"New synthetic observation"}])
        second = {
            "continuation_private": operator["continuation_private"],
            "specialist_result": {"IR_CAPSULE": fresh_ir},
        }
        rc, out, err = self.cli(second, "resume-operator")
        self.assertEqual((rc, err), (0, ""))
        pending_pi = json.loads(out)
        self.assertEqual(pending_pi["session"]["status"], "AWAITING_MANUAL_PI_DELTA")
        pi_handoff = pending_pi["continuation_private"]["next_handoff"]["PI_REQUEST"]
        self.assertEqual(pi_handoff["FORWARD_UNCHANGED"], fresh_ir)
        self.assertNotIn("OLD_RESEARCH_NOT_FOR_NEW_SPECIALIST",
                         json.dumps(pi_handoff))
        final = {
            "continuation_private": pending_pi["continuation_private"],
            "specialist_result": {
                "PI_DELTA": self.fx.pi(
                    analysis_id="CASE-B", portfolio_as_of="2026-10-29"),
                "FORWARD_UNCHANGED": deepcopy(fresh_ir),
            },
        }
        rc, out, err = self.cli(final, "resume-operator")
        self.assertEqual((rc, err), (0, ""))
        finished = json.loads(out)
        self.assertIsNone(finished["continuation_private"])
        report = finished["report_private"]
        self.assertIn("Prior/current research", report)
        self.assertIn("On-demand private portfolio snapshot comparison", report)
        self.assertIn("not independently authenticated", report.lower())
        self.assertNotIn("PRIVATE_ACCOUNT_NOT_IN_RESEARCH_MEMORY", report)
        self.assertEqual(finished["session"]["status"],
                         "M7A_COMPONENT_ASSEMBLED_NOT_END_TO_END_ACCEPTANCE")
        self.assertEqual(finished["storage"], "NONE")
        self.assertEqual(finished["trading_authority"], "NONE")

    def test_modified_private_source_and_cross_case_mix_fail_closed(self):
        old = self.old()
        bad = deepcopy(old)
        bad["private_portfolio_snapshot_envelope"]["private_snapshot"][
            "original_observation_inputs"]["positions"][0][
            "market_value_base"] = "CONFIDENTIAL_MUTATION"
        rc, output, err = self.cli({"prior_integrated_closeout": bad},
                                   "integrated-followup-draft")
        self.assertEqual((rc, output), (2, ""))
        self.assertIn("PRIVATE_PORTFOLIO_SHA256_MISMATCH", err)
        self.assertNotIn("CONFIDENTIAL_MUTATION", err)

        changed = deepcopy(old)
        changed["private_case_envelope"]["private_case"][
            "original_ir_capsule"]["facts"][0]["claim"] = "PRIVATE_CHANGED"
        rc, output, err = self.cli({"prior_integrated_closeout": changed},
                                   "integrated-followup-draft")
        self.assertEqual((rc, output), (2, ""))
        self.assertIn("PRIVATE_CASE_SHA256_MISMATCH", err)

        other = deepcopy(old)
        other_inputs = self.ob.kwargs(
            analysis_id="WRONG-PRIOR", analysis_as_of="2026-10-28")
        other["private_portfolio_snapshot_envelope"] = (
            seal_private_portfolio_snapshot(other_inputs))
        rc, output, err = self.cli({"prior_integrated_closeout": other},
                                   "integrated-followup-draft")
        self.assertEqual((rc, output), (2, ""))
        self.assertIn("INTEGRATED_PRIOR_CASE_ID_OR_DATE_MISMATCH", err)

    def test_existing_old_broken_memory_cannot_invent_ceo_provenance(self):
        old = self.old()
        stale = deepcopy(old)
        case = stale["private_case_envelope"]["private_case"]
        case["original_request"].pop("ceo_initiated")
        case["original_request"].pop("research_needed")
        stale["private_case_envelope"] = seal_private_case(case)
        rc, out, err = self.cli({"prior_integrated_closeout": stale},
                                "integrated-followup-draft")
        self.assertEqual((rc, out), (2, ""))
        self.assertIn("R1_INPUT_REJECTED", err)
        self.assertNotIn("PRIVATE_ACCOUNT_NOT_IN_RESEARCH_MEMORY", err)

    def test_missing_current_source_wrong_route_and_implicit_ceo_return_rejected(self):
        old = self.old()
        for variant, error in (
            ({"session": {"request": self.current()["request"]},
              "fact_links": []}, "INTEGRATED_FOLLOWUP_CURRENT_PORTFOLIO_REQUIRED"),
            ({"session": {**self.current(),
                          "request": {**self.current()["request"],
                                      "portfolio_needed": False}},
              "fact_links": []}, "INTEGRATED_FOLLOWUP_PORTFOLIO_ROUTE_REQUIRED"),
            ({"session": {**self.current(),
                          "request": {**self.current()["request"],
                                      "ceo_initiated": False}},
              "fact_links": []}, "SEALED_FOLLOWUP_EXPLICIT_MANDATE_REQUIRED"),
            ({"session": {**self.current(),
                          "prior_private_portfolio_envelope":
                              old["private_portfolio_snapshot_envelope"]},
              "fact_links": []}, "INTEGRATED_FOLLOWUP_PRIOR_SOURCE_AMBIGUOUS"),
        ):
            with self.subTest(error=error):
                packet = {"prior_integrated_closeout": old, **variant}
                rc, out, err = self.cli(packet, "integrated-followup-operator")
                self.assertEqual((rc, out), (2, ""))
                self.assertIn(error, err)


    def test_one_guided_mode_reuses_original_integrated_followup_and_pinned_prompts(self):
        """One entered request, two explicitly pasted specialist prompts, then report."""
        old = self.old()
        session = self.current()
        original_session = deepcopy(session)
        wrapper = {
            "prior_integrated_closeout": old,
            "session": session,
            "fact_links": [{"prior_fact_id": "F1", "current_fact_id": "F2"}],
        }
        rc, body, err = self.cli(wrapper, "guided-operator")
        self.assertEqual((rc, err), (0, ""))
        first = json.loads(body)
        self.assertEqual(first["specialist_step"], "IR_REQUEST")
        self.assertEqual(first["copy_to_specialist"], "specialist_prompt_private")
        self.assertIn("Recipient: Investment Research (IR)",
                      first["specialist_prompt_private"])
        self.assertIn("METHOD_PATH:", first["specialist_prompt_private"])
        self.assertIn("CONTENT_BEGIN", first["specialist_prompt_private"])
        self.assertNotIn("OLD_RESEARCH_NOT_FOR_NEW_SPECIALIST",
                         first["specialist_prompt_private"])
        self.assertNotIn("SCOPE-A", first["specialist_prompt_private"])
        self.assertNotIn('"resume_input"', first["specialist_prompt_private"])
        operator = first["operator_packet_private"]
        self.assertEqual(
            operator["manual_copy_integrity"],
            "TWO_UNKEYED_SHA256_COPIES_MATCHED_RETAINED_ONLY")
        self.assertEqual(operator["record_authenticity"], "NOT_ESTABLISHED")
        self.assertIn("prior_private_portfolio_envelope",
                      operator["continuation_private"]["resume_input"])
        self.assertNotIn("prior_private_portfolio_envelope",
                         json.dumps(operator["continuation_private"]["next_handoff"]))
        self.assertEqual(session, original_session)

        fresh_ir = self.fx.ir(
            analysis_id="CASE-B", research_as_of="2026-10-29",
            facts=[{"id":"F2", "status":"INDICATIVE",
                    "claim":"New synthetic observation"}])
        second = {
            "continuation_private": operator["continuation_private"],
            "specialist_result": {"IR_CAPSULE": fresh_ir},
        }
        rc, body, err = self.cli(second, "guided-operator")
        self.assertEqual((rc, err), (0, ""))
        pi = json.loads(body)
        self.assertEqual(pi["specialist_step"], "PI_REQUEST")
        self.assertIn("Recipient: Portfolio Intelligence (PI)",
                      pi["specialist_prompt_private"])
        self.assertIn("METHOD_PATH:", pi["specialist_prompt_private"])
        self.assertNotIn("OLD_RESEARCH_NOT_FOR_NEW_SPECIALIST",
                         pi["specialist_prompt_private"])
        self.assertEqual(
            pi["operator_packet_private"]["continuation_private"][
                "next_handoff"]["PI_REQUEST"]["FORWARD_UNCHANGED"],
            fresh_ir)

        returned = {
            "continuation_private":
                pi["operator_packet_private"]["continuation_private"],
            "specialist_result": {
                "PI_DELTA": self.fx.pi(
                    analysis_id="CASE-B", portfolio_as_of="2026-10-29"),
                "FORWARD_UNCHANGED": deepcopy(fresh_ir),
            },
        }
        rc, body, err = self.cli(returned, "guided-operator")
        self.assertEqual((rc, err), (0, ""))
        complete = json.loads(body)
        self.assertIsNone(complete["specialist_step"])
        self.assertIsNone(complete["specialist_prompt_private"])
        self.assertEqual(complete["copy_to_specialist"], "NONE")
        self.assertIsNone(
            complete["operator_packet_private"]["continuation_private"])
        report = complete["operator_packet_private"]["report_private"]
        self.assertIn("Prior/current research", report)
        self.assertIn("On-demand private portfolio snapshot comparison", report)
        self.assertNotIn("OLD_RESEARCH_NOT_FOR_NEW_SPECIALIST", report)
        self.assertNotIn("SCOPE-A", report)
        self.assertEqual(complete["trading_authority"], "NONE")
        self.assertEqual(complete["project_invocation"], "NONE")
        self.assertEqual(complete["method_load_verification"], "NOT_PERFORMED")

    def test_guided_integrated_followup_rejects_tamper_and_implicit_ceo(self):
        old = self.old()
        session = self.current()
        modified = deepcopy(old)
        modified["private_case_envelope"]["private_case"][
            "original_ir_capsule"]["facts"][0]["claim"] = "SYNTHETIC_PRIVATE_TAMPER"
        bad = {
            "prior_integrated_closeout": modified, "session": session,
            "fact_links": [],
        }
        rc, out, err = self.cli(bad, "guided-operator")
        self.assertEqual((rc, out), (2, ""))
        self.assertIn("PRIVATE_CASE_SHA256_MISMATCH", err)
        self.assertNotIn("SYNTHETIC_PRIVATE_TAMPER", err)
        no_ceo = {
            "prior_integrated_closeout": old,
            "session": {**session, "request": {
                **session["request"], "ceo_initiated": False}},
            "fact_links": [],
        }
        rc, out, err = self.cli(no_ceo, "guided-operator")
        self.assertEqual((rc, out), (2, ""))
        self.assertIn("SEALED_FOLLOWUP_EXPLICIT_MANDATE_REQUIRED", err)

    def test_guided_integrated_followup_can_change_mode_without_policy_approval(self):
        old = self.old()
        session = self.current()
        session["request"]["strategy_id"] = "balanced"
        payload = {
            "prior_integrated_closeout": old,
            "session": session,
            "fact_links": [],
        }
        rc, body, err = self.cli(payload, "guided-operator")
        self.assertEqual((rc, err), (0, ""))
        first = json.loads(body)
        prompt = first["specialist_prompt_private"]
        self.assertIn("Recipient: Investment Research (IR)", prompt)
        self.assertIn("POLICY_PROPOSAL_BALANCED_R1.md", prompt)
        self.assertIn("not Project-loading proof", prompt)
        self.assertIn("other five R1 mode designs remain unapproved", prompt)
        self.assertEqual(first["trading_authority"], "NONE")
        self.assertEqual(first["method_load_verification"], "NOT_PERFORMED")


if __name__ == "__main__":
    unittest.main()
