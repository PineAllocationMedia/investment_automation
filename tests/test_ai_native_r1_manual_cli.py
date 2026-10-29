"""Synthetic-only contract tests for the explicit local R1 stdin CLI.

No service, no file I/O, no real credentials, no external requests, no trades.
"""
from __future__ import annotations

from copy import deepcopy
from io import StringIO
import json
import unittest

from scripts.r1_manual_session_cli import main
from tests.test_ai_native_session_bridge import SessionBridgeTests


class ManualCLIContractTests(unittest.TestCase):
    def setUp(self):
        self.fx = SessionBridgeTests()

    def invoke(self, payload, output="status", *, raw=False):
        data = payload if raw else json.dumps(payload, ensure_ascii=False)
        stdin, stdout, stderr = StringIO(data), StringIO(), StringIO()
        code = main(["--output", output], instream=stdin,
                    outstream=stdout, errstream=stderr)
        return code, stdout.getvalue(), stderr.getvalue()


    def test_single_ir_capsule_envelope_routes_to_final_private_cc_report(self):
        req = self.fx.request()
        ir = self.fx.ir()
        payload = {"request": req, "specialist_result": {"IR_CAPSULE": ir}}
        before = deepcopy(payload)
        code, report, error = self.invoke(payload, "report")
        self.assertEqual((code, error), (0, ""))
        self.assertIn("Investment decision research", report)
        self.assertEqual(
            report,
            self.invoke({"request": req, "ir_capsule": ir}, "report")[1],
        )
        self.assertEqual(payload, before)
        code, status, error = self.invoke(payload)
        self.assertEqual((code, error), (0, ""))
        self.assertEqual(json.loads(status)["readiness"], "NOT_EVALUATED")
        self.assertNotIn("Synthetic", status)

    def test_original_ir_envelope_unblocks_only_next_pi_transfer(self):
        request = self.fx.request(portfolio_needed=True)
        ir = self.fx.ir()
        code, output, error = self.invoke(
            {"request": request, "specialist_result": {"IR_CAPSULE": ir}},
            output="next-handoff",
        )
        self.assertEqual((code, error), (0, ""))
        self.assertEqual(set(json.loads(output)), {"PI_REQUEST"})
        self.assertEqual(json.loads(output)["PI_REQUEST"]["FORWARD_UNCHANGED"], ir)

    def test_pi_return_envelope_matches_original_ir_and_builds_integrated_report(self):
        req, ir = self.fx.request(portfolio_needed=True), self.fx.ir()
        pi = self.fx.pi()
        payload = {"request": req, "ir_capsule": ir,
                   "specialist_result": {"PI_DELTA": pi, "FORWARD_UNCHANGED": deepcopy(ir)}}
        snapshot = deepcopy(payload)
        code, report, error = self.invoke(payload, "report")
        self.assertEqual((code, error), (0, ""))
        expected = self.invoke({"request": req, "ir_capsule": ir,
                                "pi_delta": self.fx.pi(forwarded_ir=deepcopy(ir))},
                               "report")
        self.assertEqual((expected[0], expected[2]), (0, ""))
        self.assertEqual(report, expected[1])
        self.assertEqual(payload, snapshot)
        code, status, error = self.invoke(payload)
        self.assertEqual((code, error), (0, ""))
        self.assertEqual(json.loads(status)["status"],
                         "M7A_COMPONENT_ASSEMBLED_NOT_END_TO_END_ACCEPTANCE")

    def test_pi_only_return_envelope_requires_no_invented_research(self):
        req = self.fx.request(research_needed=False, portfolio_needed=True)
        pi = self.fx.pi()
        payload = {"request": req, "specialist_result": {"PI_DELTA": pi}}
        code, report, error = self.invoke(payload, "report")
        self.assertEqual((code, error), (0, ""))
        self.assertIn("Portfolio-only interpretation", report)
        self.assertNotIn("Investment decision research", report)
        self.assertEqual(
            report,
            self.invoke({"request": req, "pi_delta": pi}, "report")[1],
        )

    def test_pi_forwarded_ir_requires_original_independent_capsule(self):
        req, ir = self.fx.request(portfolio_needed=True), self.fx.ir()
        pi = self.fx.pi()
        for original in (None, {"analysis_id": "CASE-A", "altered": True}):
            with self.subTest(original=original):
                payload = {"request": req, "specialist_result": {
                    "PI_DELTA": pi, "FORWARD_UNCHANGED": ir}}
                if original is not None:
                    payload["ir_capsule"] = original
                code, output, error = self.invoke(payload, "report")
                self.assertEqual(code, 2)
                self.assertEqual(output, "")
                self.assertIn(
                    "SPECIALIST_ORIGINAL_IR_REQUIRED" if original is None
                    else "SPECIALIST_FORWARDED_IR_MISMATCH", error,
                )
        pi_changed = self.fx.pi(forwarded_ir={"altered": True})
        code, output, error = self.invoke(
            {"request": req, "ir_capsule": ir, "specialist_result": {
                "PI_DELTA": pi_changed, "FORWARD_UNCHANGED": ir}}, "report")
        self.assertEqual(code, 2)
        self.assertEqual(output, "")
        self.assertIn("SPECIALIST_FORWARDED_IR_MISMATCH", error)

    def test_specialist_envelope_rejects_malformed_and_duplicate_sources(self):
        req = self.fx.request()
        ir = self.fx.ir()
        for wrapped in (None, {}, {"IR_CAPSULE": ir, "PI_DELTA": self.fx.pi()},
                        {"IR_CAPSULE": "not-an-object"}, {"BAD_KEY": ir},
                        {"PI_DELTA": []}, {"PI_DELTA": {}, "FORWARD_UNCHANGED": None}):
            with self.subTest(wrapped=type(wrapped).__name__):
                code, output, error = self.invoke(
                    {"request": req, "specialist_result": wrapped}, "status")
                self.assertEqual(code, 2)
                self.assertEqual(output, "")
                self.assertIn("SPECIALIST_RESULT_INVALID", error)
        for wrapped, direct in (
            ({"IR_CAPSULE": ir}, {"ir_capsule": ir}),
            ({"PI_DELTA": self.fx.pi()}, {"pi_delta": self.fx.pi()}),
        ):
            with self.subTest(keys=tuple(wrapped)):
                code, output, error = self.invoke(
                    {"request": self.fx.request(portfolio_needed=True),
                     "specialist_result": wrapped, **direct}, "status")
                self.assertEqual(code, 2)
                self.assertEqual(output, "")
                self.assertIn("SPECIALIST_RESULT_AMBIGUOUS", error)

    def test_specialist_envelope_rejects_unrequested_route_and_pi_only_forward(self):
        ir = self.fx.ir()
        pi = self.fx.pi()
        cases = (
            {"request": self.fx.request(research_needed=False, portfolio_needed=True),
             "specialist_result": {"IR_CAPSULE": ir}},
            {"request": self.fx.request(),
             "specialist_result": {"PI_DELTA": pi}},
            {"request": self.fx.request(research_needed=False, portfolio_needed=True),
             "specialist_result": {"PI_DELTA": pi,
                                   "FORWARD_UNCHANGED": ir}},
        )
        for payload in cases:
            with self.subTest(keys=tuple(payload["specialist_result"])):
                code, output, error = self.invoke(payload)
                self.assertEqual(code, 2)
                self.assertEqual(output, "")
                self.assertIn("R1_INPUT_REJECTED", error)
        code, output, error = self.invoke(
            {"request": self.fx.request(portfolio_needed=True),
             "ir_capsule": ir,
             "specialist_result": {"PI_DELTA": pi}}, "report")
        # A PI-only fragment cannot silently synthesize FORWARD_UNCHANGED
        # for an IR+PI request.
        self.assertEqual(code, 2)
        self.assertEqual(output, "")

    def test_default_status_redacts_handoffs_and_private_details(self):
        request = self.fx.request()
        code, output, error = self.invoke({"request":request})
        self.assertEqual(code, 0)
        self.assertEqual(error, "")
        result=json.loads(output)
        self.assertEqual(result["status"],"AWAITING_MANUAL_IR_CAPSULE")
        self.assertEqual(result["route"],"CC_IR_CC")
        self.assertEqual(result["project_invocation"],"NONE")
        self.assertEqual(result["storage"],"NONE")
        self.assertEqual(result["readiness"],"NOT_EVALUATED")
        self.assertNotIn("PRIVATE-ACCOUNT",output)
        self.assertNotIn("\"packet_type\"",output)
        self.assertNotIn("FORWARD_UNCHANGED",output)

    def test_explicit_handoffs_preserve_manual_ir_packet(self):
        request=self.fx.request()
        code, output, error=self.invoke({"request":request},output="handoffs")
        self.assertEqual((code,error),(0,""))
        result=json.loads(output)
        self.assertEqual(result["IR_REQUEST"]["analysis_id"],"CASE-A")
        self.assertEqual(result["IR_REQUEST"]["packet_type"],"IR_REQUEST")
        self.assertNotIn("PI_REQUEST",result)

    def test_explicit_ir_report_is_private_conditional_not_accepted(self):
        packet={"request":self.fx.request(),"ir_capsule":self.fx.ir()}
        saved=deepcopy(packet)
        code, status, error=self.invoke(packet)
        self.assertEqual((code,error),(0,""))
        self.assertEqual(json.loads(status)["readiness"],"NOT_EVALUATED")
        code, report, error=self.invoke(packet,output="report")
        self.assertEqual((code,error),(0,""))
        self.assertIn("Investment decision research",report)
        self.assertIn("not independently authenticated",report)
        self.assertEqual(packet,saved)

    def test_missing_pi_stays_pending_and_handoff_preserves_original_ir(self):
        packet={"request":self.fx.request(portfolio_needed=True),"ir_capsule":self.fx.ir()}
        code, report, err=self.invoke(packet,output="report")
        self.assertEqual((code,err),(0,""))
        self.assertIn("REPORT_NOT_AVAILABLE: AWAITING_MANUAL_PI_DELTA",report)
        code, handoffs, err=self.invoke(packet,output="handoffs")
        self.assertEqual((code,err),(0,""))
        record=json.loads(handoffs)
        self.assertEqual(record["PI_REQUEST"]["FORWARD_UNCHANGED"],packet["ir_capsule"])

    def test_rejects_duplicate_json_keys_and_nonfinite_number(self):
        for raw in ('{"request":{},"request":{}}',
                    '{"request":{"ceo_initiated":NaN}}'):
            code, output, err=self.invoke(raw,raw=True)
            self.assertEqual(code,2)
            self.assertEqual(output,"")
            self.assertIn("R1_INPUT_REJECTED:",err)

    def test_unknown_session_keys_and_missing_request_fail_closed(self):
        for payload in ({}, {"request":self.fx.request(),"execute_trade":True}):
            code,output,error=self.invoke(payload)
            self.assertEqual(code,2)
            self.assertEqual(output,"")
            self.assertIn("UNKNOWN_OR_MISSING_SESSION_FIELD",error)

    def test_invalid_ceo_mandate_not_accidentally_executed(self):
        req=self.fx.request(ceo_initiated=False)
        code,output,error=self.invoke({"request":req},output="report")
        self.assertEqual(code,2)
        self.assertEqual(output,"")
        self.assertIn("R1_INPUT_REJECTED",error)

    def test_large_input_is_rejected_without_echoing_secrets(self):
        raw='{"PRIVATE_SECRET":"'+'X'*5_000_001+'"}'
        code,output,error=self.invoke(raw,raw=True)
        self.assertEqual(code,2)
        self.assertEqual(output,"")
        self.assertIn("INPUT_TOO_LARGE",error)
        self.assertNotIn("PRIVATE_SECRET",error)



    def test_exponent_overflow_rejected_before_any_session_execution(self):
        for literal in ("1e999", "-1e999", "9.99e9999"):
            with self.subTest(literal=literal):
                raw='{"request":{"ceo_initiated":true,"risk_constraints":[' + literal + ']}}'
                code, output, error=self.invoke(raw, raw=True)
                self.assertEqual(code,2)
                self.assertEqual(output,"")
                self.assertIn("NONFINITE_JSON_NUMBER",error)
                self.assertNotIn("1e999",error)

    def test_finite_decimal_json_does_not_trigger_nonfinite_guard(self):
        # The financial method itself may reject a non-string numeric amount;
        # distinguish that contract failure from overflowing the JSON decoder.
        raw='{"request":{"ceo_initiated":true,"research_needed":true,"portfolio_needed":false,' + \
            '"analysis_id":"SYN","as_of":"2026-10-28","kind":"DECISION",' + \
            '"objective":"Human review","risk_constraints":[1.5]}}'
        code, output, error=self.invoke(raw, raw=True)
        self.assertEqual(code,2)
        self.assertEqual(output,"")
        self.assertNotIn("NONFINITE_JSON_NUMBER",error)

    def test_private_input_validation_error_has_no_raw_user_string(self):
        code,output,error=self.invoke({"request":{
            "ceo_initiated":False,"objective":"CONFIDENTIAL_ACCOUNT_123",
            "analysis_id":"SYN","as_of":"2026-10-28","kind":"DECISION",
            "research_needed":True,"portfolio_needed":False}})
        self.assertEqual(code,2)
        self.assertEqual(output,"")
        self.assertNotIn("CONFIDENTIAL_ACCOUNT_123",error)


    def test_private_case_export_is_user_requested_and_followup_compatible(self):
        from ai_native.research_case_comparison import compare_supplied_cases
        prior_request=self.fx.request(subject_id="SYN-ISSUER")
        ir=self.fx.ir()
        payload={"request":prior_request, "ir_capsule":ir,
                 "memory_inputs":{"report_id":"REPORT-A","instruction_version":"R1-SYN",
                                  "recorded_at":"2026-10-28"}}
        original=deepcopy(payload)
        code,output,error=self.invoke(payload,output="private-case")
        self.assertEqual((code,error),(0,""))
        saved=json.loads(output)
        self.assertEqual(saved["schema_version"],"RESEARCH_HISTORY_R1")
        self.assertEqual(saved["archive_status"],"PROPOSED_NOT_COMMITTED")
        self.assertEqual(saved["privacy_tier"],"PRIVATE_PENDING_REVIEW")
        self.assertEqual(saved["original_ir_capsule"],ir)
        self.assertEqual(saved["original_request"]["subject_id"],"SYN-ISSUER")
        self.assertEqual(payload,original)
        current={"kind":"FOLLOWUP","analysis_id":"CASE-B","subject_id":"SYN-ISSUER",
                 "as_of":"2026-10-29","method_version":"UNKNOWN_NOT_LOADED",
                 "strategy_id":"EXPLORATORY","prior_analysis_id":"CASE-A"}
        current_ir={"analysis_id":"CASE-B","research_as_of":"2026-10-29",
                    "facts":[{"id":"F2","claim":"New synthetic research claim",
                              "status":"INDICATIVE"}]}
        review=compare_supplied_cases(
            request=current,ir_capsule=current_ir,prior_case=saved,
            subject_id="SYN-ISSUER",
            fact_links=[{"prior_fact_id":"F1","current_fact_id":"F2"}])
        self.assertEqual(review["status"],"STRUCTURAL_REVIEW_PREPARED")
        self.assertEqual(review["economic_change_status"],"NOT_EVALUATED")

    def test_private_case_export_requires_explicit_memory_inputs(self):
        payload={"request":self.fx.request(),"ir_capsule":self.fx.ir()}
        code,output,error=self.invoke(payload,output="private-case")
        self.assertEqual((code,error),(0,""))
        self.assertEqual(output,"PRIVATE_CASE_NOT_PREPARED: explicit memory_inputs required.\n")
        self.assertNotIn("Synthetic",output)

    def test_private_case_export_is_unavailable_during_missing_ir_handoff(self):
        code,output,error=self.invoke({"request":self.fx.request()},output="private-case")
        self.assertEqual((code,error),(0,""))
        self.assertIn("PRIVATE_CASE_NOT_AVAILABLE: AWAITING_MANUAL_IR_CAPSULE",output)
        self.assertNotIn("original_ir_capsule",output)

    def test_private_case_export_never_changes_default_redacted_status(self):
        payload={"request":self.fx.request(subject_id="SYN-ISSUER"),
                 "ir_capsule":self.fx.ir(),
                 "memory_inputs":{"report_id":"REPORT-A","instruction_version":"R1-SYN",
                                  "recorded_at":"2026-10-28"}}
        code,output,error=self.invoke(payload)
        self.assertEqual((code,error),(0,""))
        self.assertNotIn("SYN-ISSUER",output)
        self.assertNotIn("REPORT-A",output)
        self.assertNotIn("original_request",output)
        self.assertEqual(json.loads(output)["storage"],"NONE")


    def test_macro_sector_input_allowed_but_never_direct_without_ir_source_annex(self):
        payload={"request":self.fx.request(),"ir_capsule":self.fx.ir(),
                 "macro_sector_inputs":{"analysis_id":"CASE-A",
                                        "analysis_as_of":"2026-10-28",
                                        "strategy_id":"EXPLORATORY","drivers":[]}}
        code,output,error=self.invoke(payload,output="report")
        self.assertEqual(code,2)
        self.assertEqual(output,"")
        self.assertIn("R1_INPUT_REJECTED",error)
        # The failure must be from the missing source annex, not a rejected
        # unknown top-level CLI key. Source content is never echoed on error.
        self.assertNotIn("UNKNOWN_OR_MISSING_SESSION_FIELD",error)


    def test_next_handoff_selects_only_the_current_manual_transfer(self):
        cases = (
            ({"request": self.fx.request()}, "IR_REQUEST"),
            ({"request": self.fx.request(portfolio_needed=True)}, "IR_REQUEST"),
            ({"request": self.fx.request(portfolio_needed=True),
              "ir_capsule": self.fx.ir()}, "PI_REQUEST"),
            ({"request": self.fx.request(research_needed=False, portfolio_needed=True)},
             "PI_REQUEST"),
        )
        for payload, expected_label in cases:
            with self.subTest(expected=expected_label, research=payload["request"]["research_needed"]):
                original = deepcopy(payload)
                code, output, error = self.invoke(payload, output="next-handoff")
                self.assertEqual((code, error), (0, ""))
                selected = json.loads(output)
                self.assertEqual(set(selected), {expected_label})
                self.assertEqual(selected[expected_label]["packet_type"], expected_label)
                code, all_output, error = self.invoke(payload, output="handoffs")
                self.assertEqual((code, error), (0, ""))
                self.assertEqual(selected[expected_label],
                                 json.loads(all_output)[expected_label])
                self.assertEqual(payload, original)
        self.assertEqual(
            json.loads(self.invoke(cases[2][0], "next-handoff")[1])["PI_REQUEST"]["FORWARD_UNCHANGED"],
            cases[2][0]["ir_capsule"],
        )

    def test_next_handoff_never_repeats_after_terminal_report_or_direct(self):
        completed_ir = {"request": self.fx.request(), "ir_capsule": self.fx.ir()}
        completed_pi = {
            "request": self.fx.request(research_needed=False, portfolio_needed=True),
            "pi_delta": self.fx.pi(),
        }
        no_specialist = {"request": self.fx.request(research_needed=False)}
        for payload in (completed_ir, completed_pi, no_specialist):
            with self.subTest(route=payload["request"]):
                code, text, error = self.invoke(payload, output="next-handoff")
                self.assertEqual((code, error), (0, ""))
                self.assertTrue(text.startswith("NEXT_HANDOFF_NOT_AVAILABLE: "))
                self.assertNotIn("IR_REQUEST", text)
                self.assertNotIn("PI_REQUEST", text)

    def test_next_handoff_is_explicit_private_mode_not_default_status(self):
        payload = {"request": self.fx.request(portfolio_needed=True,
                                               account_context={"account": "PRIVATE_SALT"})}
        code, status, error = self.invoke(payload)
        self.assertEqual((code, error), (0, ""))
        self.assertNotIn("PRIVATE_SALT", status)
        code, next_packet, error = self.invoke(payload, output="next-handoff")
        self.assertEqual((code, error), (0, ""))
        self.assertIn("PRIVATE_SALT", next_packet)
        self.assertEqual(set(json.loads(next_packet)), {"IR_REQUEST"})

if __name__ == "__main__":
    unittest.main()
