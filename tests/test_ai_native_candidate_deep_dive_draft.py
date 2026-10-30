"""R1 synthetic original triage -> CEO-selected inert IR deep dive.

No external discovery, original-source verification, policy approval, ranking,
automatic research, portfolio access, storage, or trading.
"""
from __future__ import annotations

from copy import deepcopy
from io import StringIO
import json
import unittest

from ai_native.opportunity_triage import (
    prepare_opportunity_triage, prepare_selected_candidate_draft,
)
from scripts.r1_manual_session_cli import main
from tests.test_ai_native_session_bridge import SessionBridgeTests
from tests.test_ai_native_opportunity_triage import OpportunityTriageTests
from tests.test_ai_native_source_fusion import SourceFusionTests


class CandidateDeepDiveDraftTests(unittest.TestCase):
    def setUp(self):
        self.fx = SessionBridgeTests()
        self.t = OpportunityTriageTests()
        self.s = SourceFusionTests()

    def cli(self, payload, output="candidate-deep-dive-draft"):
        inp = StringIO(json.dumps(payload, ensure_ascii=False))
        out, err = StringIO(), StringIO()
        rc = main(["--output", output], instream=inp,
                  outstream=out, errstream=err)
        return rc, out.getvalue(), err.getvalue()

    def session(self, *, observations=True):
        triage = self.t.setup_case()
        row = self.s.sample(
            economic_issuer="SYN-CO", instrument="SYN:NYSE",
            value="777.00", source_locator="https://example.org/SECRET_SOURCE")
        return {
            "request": self.fx.request(strategy_id="high-cagr"),
            "ir_capsule": self.fx.ir(facts=[
                {"id": "F1", "status": "INDICATIVE",
                 "claim": "SECRET_OLD_IR_CLAIM_NOT_NEW_EVIDENCE"}]),
            "source_evidence_inputs": {
                "analysis_id": "CASE-A", "analysis_as_of": "2026-10-28",
                "observations": [row] if observations else [],
            },
            "opportunity_triage_inputs": {
                "analysis_id": "CASE-A", "analysis_as_of": "2026-10-28",
                "strategy_id": "high-cagr",
                "universe_scope": triage["universe_scope"],
                "universe_note": triage["universe_note"],
                "candidates": deepcopy(triage["candidates"]),
            },
        }

    def test_genuine_manual_session_yields_selected_candidate_not_automated_research(self):
        session = self.session()
        prior = deepcopy(session)
        rc, text, err = self.cli(
            {"session": session, "candidate_id": "C1"})
        self.assertEqual((rc, err), (0, ""))
        draft = json.loads(text)
        self.assertEqual(draft["status"],
                         "PRIVATE_CANDIDATE_DEEP_DIVE_DRAFT_REQUIRES_NEW_CEO_MANDATE")
        selected = draft["selected_candidate_private"]
        self.assertEqual(selected["candidate_id"], "C1")
        self.assertEqual(selected["prior_analysis_id"], "CASE-A")
        self.assertEqual(selected["economic_issuer"], "SYN-CO")
        self.assertEqual(selected["instrument"], "SYN:NYSE")
        self.assertEqual(selected["prior_ir_fact_ids"], ["F1"])
        self.assertEqual(selected["prior_observation_ids"], ["O1"])
        self.assertEqual(selected["prior_research_work_stage"],
                         "HUMAN_DEEP_DIVE")
        req = draft["input_template"]["request"]
        self.assertIs(req["ceo_initiated"], False)
        self.assertIsNone(req["analysis_id"])
        self.assertIsNone(req["as_of"])
        self.assertIsNone(req["objective"])
        self.assertEqual(req["kind"], "DECISION")
        self.assertIs(req["research_needed"], True)
        self.assertIs(req["portfolio_needed"], False)
        self.assertEqual(req["strategy_id"], "high-cagr")
        self.assertEqual(req["candidate_universe"], "SYN-CO | SYN:NYSE")
        self.assertEqual(req["ir_method_version"], "UNKNOWN_NOT_LOADED")
        self.assertEqual(draft["prior_context_transfer"],
                         "PREFILLED_REQUIRES_CEO_REVIEW")
        self.assertIn("What drives durability?",
                      req["mandate_prompt_private"])
        self.assertIn("Check customer churn",
                      req["mandate_prompt_private"])
        self.assertIn("UNTRUSTED PRIOR TRIAGE CONTEXT",
                      req["mandate_prompt_private"])
        self.assertIn("not verified evidence",
                      req["mandate_prompt_private"])
        self.assertLessEqual(len(req["mandate_prompt_private"]), 3000)
        self.assertNotIn("historical_comparison_inputs", draft["input_template"])
        self.assertNotIn("prior_analysis_id", req)
        self.assertEqual(draft["ranking_or_buy_recommendation"], "NONE")
        self.assertEqual(draft["trading_authority"], "NONE")
        self.assertEqual(draft["project_invocation"], "NONE")
        self.assertEqual(draft["storage"], "NONE")
        self.assertNotIn("SECRET_OLD_IR_CLAIM_NOT_NEW_EVIDENCE", text)
        self.assertNotIn("777.00", text)
        self.assertNotIn("SECRET_SOURCE", text)
        self.assertEqual(session, prior)
        rc, output, err = self.cli(draft["input_template"], "next-handoff")
        self.assertEqual((rc, output), (2, ""))
        self.assertIn("CEO_INITIATION_REQUIRED", err)

    def test_new_explicit_ceo_request_transmits_question_into_real_m1_ir_handoff(self):
        code, raw, err = self.cli({
            "session": self.session(), "candidate_id": "C1"})
        self.assertEqual((code, err), (0, ""))
        draft = json.loads(raw)
        new_request = deepcopy(draft["input_template"]["request"])
        new_request.update({
            "ceo_initiated": True,
            "analysis_id": "CASE-NEW-DEEP-DIVE",
            "as_of": "2026-10-29",
            "objective": "Independently investigate a chosen candidate",
            "horizon": "5 years",
            "risk_constraints": ["No authenticated source claims assumed"],
        })
        code, body, err = self.cli({"request": new_request}, "next-handoff")
        self.assertEqual((code, err), (0, ""))
        handoff = json.loads(body)["IR_REQUEST"]
        self.assertEqual(
            handoff["mandate_context_private"]["mandate_prompt_private"],
            new_request["mandate_prompt_private"])
        self.assertEqual(handoff["candidate_universe"], "SYN-CO | SYN:NYSE")
        self.assertIn("Check customer churn",
                      handoff["mandate_context_private"]["mandate_prompt_private"])
        self.assertIn("NOT_VERIFIED",
                      handoff["r1_strategy_method_load"])
        self.assertNotIn("SECRET_OLD_IR_CLAIM", body)
        self.assertNotIn("SECRET_SOURCE", body)
        self.assertNotIn("777.00", body)
        self.assertNotIn("FORWARD_UNCHANGED", handoff)

        # The ordinary method-checked guided route consumes the SAME request.
        code, body, err = self.cli({"request": new_request}, "guided-operator")
        self.assertEqual((code, err), (0, ""))
        guided = json.loads(body)
        self.assertEqual(guided["specialist_step"], "IR_REQUEST")
        self.assertEqual(guided["copy_to_specialist"], "specialist_prompt_private")
        self.assertIn("Check customer churn",
                      guided["specialist_prompt_private"])
        self.assertIn("UNTRUSTED PRIOR TRIAGE CONTEXT",
                      guided["specialist_prompt_private"])
        self.assertNotIn("SECRET_SOURCE",
                         guided["specialist_prompt_private"])
        self.assertEqual(guided["project_invocation"], "NONE")
        self.assertEqual(guided["method_load_verification"], "NOT_PERFORMED")

    def test_overlong_prior_questions_are_not_silently_truncated_into_ir(self):
        data = self.t.setup_case()
        data["candidates"][0]["open_questions"] = [
            "Original 1 " + "Q" * 3600,
        ]
        old = prepare_opportunity_triage(**data)
        draft = prepare_selected_candidate_draft(old, "C1")
        self.assertEqual(draft["prior_context_transfer"],
                         "NOT_COPIED_TOO_LONG_MANUAL_REVIEW_REQUIRED")
        self.assertIsNone(draft["input_template"]["request"]["mandate_prompt_private"])
        self.assertEqual(
            draft["selected_candidate_private"]["open_questions"],
            data["candidates"][0]["open_questions"])
        self.assertIn(
            "Review/edit the proposed mandate_prompt_private",
            draft["human_checks"][0])

    def test_candidate_with_missing_sources_is_evidence_work_not_ranked(self):
        rc, text, err = self.cli({
            "session": self.session(observations=False), "candidate_id": "C1"})
        self.assertEqual((rc, err), (0, ""))
        item = json.loads(text)["selected_candidate_private"]
        self.assertEqual(item["prior_research_work_stage"],
                         "EVIDENCE_RESOLUTION")
        self.assertIn("NO_SOURCE_OBSERVATION",
                      item["prior_evidence_issue_codes"])

    def test_pure_helper_requires_selected_id_and_never_ranks(self):
        data = self.t.setup_case()
        prepared = prepare_opportunity_triage(**data)
        untouched = deepcopy(prepared)
        draft = prepare_selected_candidate_draft(prepared, "C1")
        self.assertEqual(draft["selected_candidate_private"]["candidate_id"], "C1")
        self.assertEqual(prepared, untouched)
        self.assertNotIn("SENSITIVE", str(draft))
        self.assertNotIn("500.00", str(draft))
        for bad in ("UNKNOWN", "c1", ""):
            with self.subTest(candidate=bad), self.assertRaises(ValueError):
                prepare_selected_candidate_draft(prepared, bad)

    def test_cli_rejects_missing_triage_and_forged_complete_output(self):
        basic = {"request": self.fx.request(), "ir_capsule": self.fx.ir()}
        rc, text, err = self.cli({"session": basic, "candidate_id": "C1"})
        self.assertEqual((rc, text), (2, ""))
        self.assertIn("CANDIDATE_DRAFT_TRIAGE_UNAVAILABLE", err)
        rc, text, err = self.cli({
            "candidate_id": "C1",
            "triage": prepare_opportunity_triage(**self.t.setup_case()),
        })
        self.assertEqual((rc, text), (2, ""))
        self.assertIn("CANDIDATE_DRAFT_INPUT_INVALID", err)
        incomplete = self.session()
        incomplete.pop("ir_capsule")
        rc, text, err = self.cli(
            {"session": incomplete, "candidate_id": "C1"})
        self.assertEqual((rc, text), (2, ""))
        self.assertIn("CANDIDATE_DRAFT_TRIAGE_UNAVAILABLE", err)

    def test_no_candidate_other_than_exact_original_id(self):
        for candidate in ("C0", "SYN:NYSE", "C1 ", "SECRET_IR_MARKER"):
            with self.subTest(candidate=candidate):
                rc, text, err = self.cli(
                    {"session": self.session(), "candidate_id": candidate})
                self.assertEqual((rc, text), (2, ""))
                self.assertIn("CANDIDATE_DRAFT_CANDIDATE_NOT_FOUND", err)
                self.assertNotIn("SECRET_OLD_IR_CLAIM", err)


if __name__ == "__main__":
    unittest.main()
