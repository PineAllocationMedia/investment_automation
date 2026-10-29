"""Synthetic R1 specialist handoff template integration; never acceptance."""
import copy
import json
import unittest

from ai_native.mode_response_template import prepare_mode_response_template
from ai_native.request_assembly import prepare_manual_handoffs
from ai_native.strategy_authority import R1_MODES
from ai_native.strategy_research_brief import prepare_strategy_research_brief
from ai_native.mode_research_trace import prepare_mode_research_trace
from ai_native.mode_portfolio_trace import prepare_mode_portfolio_trace


class ModeResponseTemplateTests(unittest.TestCase):
    def request(self, mode="balanced", **changes):
        request = dict(ceo_initiated=True, analysis_id="SYN-TEMPLATE",
                       as_of="2026-10-29", kind="DECISION",
                       objective="Synthetic non-advisory research only",
                       strategy_id=mode, research_needed=True, portfolio_needed=True)
        request.update(changes)
        return request

    def ir(self):
        return dict(analysis_id="SYN-TEMPLATE", research_as_of="2026-10-29",
                    summary=["Synthetic; no conclusion"], facts=[])

    def test_six_mode_ir_and_pi_templates_in_real_manual_packets(self):
        for mode in R1_MODES:
            with self.subTest(mode=mode):
                request = self.request(mode)
                early = prepare_manual_handoffs(request)
                late = prepare_manual_handoffs(request, ir_capsule=self.ir())
                for role, packet, target, date_key, link_key, question_key in (
                    ("IR", early["ir_request_private"],
                     "IR_CAPSULE.MODE_RESEARCH_RESPONSES", "research_as_of",
                     "ir_fact_ids", "ir_research_questions"),
                    ("PI", late["pi_request_private"],
                     "PI_DELTA.MODE_PORTFOLIO_RESPONSES", "portfolio_as_of",
                     "p_ids", "pi_portfolio_questions"),
                ):
                    scaffold = packet["mode_question_response_template_private"]
                    self.assertEqual(scaffold["target_field"], target)
                    self.assertEqual(scaffold["status"], "PRIVATE_UNFILLED_TEMPLATE_NOT_SPECIALIST_RESULT")
                    self.assertEqual(scaffold["policy_authorization_by_template"], "NONE")
                    self.assertEqual(scaffold["method_load"], "NOT_VERIFIED")
                    body = scaffold["template_private"]
                    self.assertIsNone(body[date_key])
                    self.assertEqual(body["analysis_id"], request["analysis_id"])
                    self.assertEqual(body["strategy_id"], request["strategy_id"])
                    self.assertEqual(len(body["answers"]),
                                     len(prepare_strategy_research_brief(mode)[question_key]))
                    self.assertEqual([a["question_index"] for a in body["answers"]],
                                     list(range(1, len(body["answers"]) + 1)))
                    self.assertTrue(all(a["status"] == "UNKNOWN" and a[link_key] == []
                                        for a in body["answers"]))
                self.assertEqual(late["pi_request_private"]["FORWARD_UNCHANGED"], self.ir())

    def test_unfilled_ir_template_is_rejected_as_supposed_research(self):
        draft = prepare_mode_response_template(
            analysis_id="SYN-TEMPLATE", strategy_id="balanced",
            specialist="IR")["template_private"]
        capsule = dict(self.ir(), MODE_RESEARCH_RESPONSES=draft)
        with self.assertRaisesRegex(ValueError, "MODE_RESEARCH_DATE_INVALID"):
            prepare_mode_research_trace(request=self.request(), ir_capsule=capsule)

    def test_unfilled_pi_template_is_rejected_as_supposed_portfolio(self):
        draft = prepare_mode_response_template(
            analysis_id="SYN-TEMPLATE", strategy_id="balanced",
            specialist="PI")["template_private"]
        delta = dict(analysis_id="SYN-TEMPLATE", portfolio_as_of="2026-10-29",
                     MODE_PORTFOLIO_RESPONSES=draft)
        with self.assertRaisesRegex(ValueError, "MODE_PI_DATE_INVALID"):
            prepare_mode_portfolio_trace(request=self.request(), pi_delta=delta)

    def test_copy_ready_json_keeps_unknowns_without_mutating_request(self):
        request = self.request()
        old = copy.deepcopy(request)
        out = prepare_manual_handoffs(request)
        packet = json.loads(out["copy_ready_private"]["IR_REQUEST"])
        template = packet["mode_question_response_template_private"]["template_private"]
        self.assertIsNone(template["research_as_of"])
        self.assertEqual(template["answers"][0]["ir_fact_ids"], [])
        self.assertEqual(request, old)

    def test_pi_only_has_no_invented_ir_evidence(self):
        out = prepare_manual_handoffs(self.request(research_needed=False))
        self.assertEqual(out["route"], "CC_PI_CC")
        self.assertIsNone(out["ir_request_private"])
        packet = out["pi_request_private"]
        self.assertIsNone(packet["FORWARD_UNCHANGED"])
        self.assertEqual(packet["mode_question_response_template_private"]["target_field"],
                         "PI_DELTA.MODE_PORTFOLIO_RESPONSES")
        self.assertNotIn("ir_fact_ids", json.dumps(packet["mode_question_response_template_private"]))


if __name__ == "__main__":
    unittest.main()
