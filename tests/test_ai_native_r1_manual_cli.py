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

if __name__ == "__main__":
    unittest.main()
