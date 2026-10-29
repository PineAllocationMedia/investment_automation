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



    def test_private_followup_draft_consumes_saved_case_not_active_request(self):
        prior_payload = {
            "request": self.fx.request(subject_id="SYN-ISSUER"),
            "ir_capsule": self.fx.ir(),
            "memory_inputs": {
                "report_id": "REPORT-A", "instruction_version": "R1-SYN",
                "recorded_at": "2026-10-28",
            },
        }
        code, private_json, error = self.invoke(prior_payload, "private-case")
        self.assertEqual((code, error), (0, ""))
        prior = json.loads(private_json)
        original = deepcopy(prior)
        code, output, error = self.invoke(
            {"prior_private_case": prior}, "followup-draft")
        self.assertEqual((code, error), (0, ""))
        self.assertEqual(prior, original)
        draft = json.loads(output)
        self.assertEqual(draft["status"],
                         "PRIVATE_FOLLOWUP_DRAFT_REQUIRES_CEO_INITIATION")
        self.assertEqual(draft["storage"], "NONE")
        self.assertEqual(draft["readiness"], "NOT_EVALUATED")
        self.assertEqual(draft["project_invocation"], "NONE")
        request = draft["input_template"]["request"]
        self.assertIs(request["ceo_initiated"], False)
        self.assertIsNone(request["analysis_id"])
        self.assertIsNone(request["as_of"])
        self.assertIsNone(request["objective"])
        self.assertEqual(request["kind"], "FOLLOWUP")
        self.assertEqual(request["prior_analysis_id"], "CASE-A")
        self.assertEqual(request["subject_id"], "SYN-ISSUER")
        self.assertFalse(request["portfolio_needed"])
        self.assertEqual(request["risk_constraints"], [])
        comparison = draft["input_template"]["historical_comparison_inputs"]
        self.assertEqual(comparison["prior_case"], prior)
        self.assertEqual(comparison["subject_id"], "SYN-ISSUER")
        self.assertEqual(comparison["fact_links"], [])
        self.assertNotIn("account_context", request)
        self.assertNotIn("PRIVATE_ACCOUNT_TOKEN", request)

        # An inert draft must fail before any Project handoff.
        code, no_transfer, error = self.invoke(draft["input_template"],
                                                "next-handoff")
        self.assertEqual(code, 2)
        self.assertEqual(no_transfer, "")
        self.assertIn("R1_INPUT_REJECTED", error)

        # The CEO may explicitly create a distinct request, no automatic job.
        request.update(ceo_initiated=True, analysis_id="CASE-B",
                       as_of="2026-10-29", objective="On-demand updated research")
        code, next_transfer, error = self.invoke(
            draft["input_template"], "next-handoff")
        self.assertEqual((code, error), (0, ""))
        self.assertEqual(set(json.loads(next_transfer)), {"IR_REQUEST"})
        self.assertNotIn("PRIVATE_ACCOUNT_TOKEN", next_transfer)

    def test_followup_draft_private_case_scope_and_no_default_leaks(self):
        prior_payload = {
            "request": self.fx.request(subject_id="SYN-ISSUER",
                                       account_context={"token": "PRIVATE_ACCOUNT_TOKEN"}),
            "ir_capsule": self.fx.ir(),
            "memory_inputs": {
                "report_id": "REPORT-A", "instruction_version": "R1-SYN",
                "recorded_at": "2026-10-28",
            },
        }
        code, private_json, error = self.invoke(prior_payload, "private-case")
        self.assertEqual((code, error), (0, ""))
        saved = json.loads(private_json)
        code, safe_status, error = self.invoke(prior_payload, "status")
        self.assertEqual((code, error), (0, ""))
        self.assertNotIn("PRIVATE_ACCOUNT_TOKEN", safe_status)
        self.assertNotIn("prior_private_case", safe_status)
        code, output, error = self.invoke(
            {"prior_private_case": saved}, "followup-draft")
        self.assertEqual((code, error), (0, ""))
        self.assertIn("PRIVATE_ACCOUNT_TOKEN", output)
        self.assertNotIn("PRIVATE_ACCOUNT_TOKEN",
                         json.dumps(json.loads(output)["input_template"]["request"]))
        self.assertEqual(json.loads(output)["trading_authority"], "NONE")
        code, invalid_output, error = self.invoke(
            {"prior_private_case": saved}, "status")
        self.assertEqual(code, 2)
        self.assertEqual(invalid_output, "")
        self.assertNotIn("PRIVATE_ACCOUNT_TOKEN", error)

    def test_followup_draft_rejects_tampered_private_history_and_ambiguous_inputs(self):
        prior_payload = {
            "request": self.fx.request(subject_id="SYN-ISSUER"),
            "ir_capsule": self.fx.ir(),
            "memory_inputs": {
                "report_id": "REPORT-A", "instruction_version": "R1-SYN",
                "recorded_at": "2026-10-28",
            },
        }
        code, private_json, error = self.invoke(prior_payload, "private-case")
        self.assertEqual((code, error), (0, ""))
        original = json.loads(private_json)
        for field, bad in (
            ("privacy_tier", "PUBLIC"),
            ("archive_status", "COMMITTED"),
            ("source_authentication", "VERIFIED"),
            ("recorded_at", "2026-10-27"),
            ("analysis_id", "OTHER"),
            ("fact_ids", ["FORGED-FACT"]),
        ):
            with self.subTest(field=field):
                changed = deepcopy(original)
                changed[field] = bad
                code, out, error = self.invoke(
                    {"prior_private_case": changed}, "followup-draft")
                self.assertEqual(code, 2)
                self.assertEqual(out, "")
                self.assertNotIn("SYN-ISSUER", error)
        changed = deepcopy(original)
        changed["original_request"].pop("subject_id")
        code, out, error = self.invoke(
            {"prior_private_case": changed}, "followup-draft")
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        code, out, error = self.invoke(
            {"prior_private_case": original, "request": original["original_request"]},
            "followup-draft")
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("FOLLOWUP_PRIOR_CASE_ENVELOPE_REQUIRED", error)

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



    def test_private_continuation_round_trip_ir_then_pi_without_retyping(self):
        req = self.fx.request(portfolio_needed=True, account_context={"account": "PRIVATE_ACCOUNT_TOKEN"})
        original = {"request": req}
        snapshot = deepcopy(original)
        code, output, err = self.invoke(original, "continuation")
        self.assertEqual((code, err), (0, ""))
        first = json.loads(output)
        self.assertEqual(first["status"], "PRIVATE_MANUAL_CONTINUATION_NOT_SENT")
        self.assertEqual(first["replace_null_with"], "IR_CAPSULE")
        self.assertEqual(set(first["next_handoff"]), {"IR_REQUEST"})
        self.assertEqual(first["next_handoff"]["IR_REQUEST"]["packet_type"], "IR_REQUEST")
        self.assertEqual(first["resume_input"]["specialist_result"], None)
        self.assertEqual(first["resume_input"]["request"], req)
        self.assertEqual(original, snapshot)
        self.assertEqual(first["readiness"], "NOT_EVALUATED")
        self.assertEqual(first["storage"], "NONE")

        code, bad, err = self.invoke(first["resume_input"], "status")
        self.assertEqual(code, 2)
        self.assertEqual(bad, "")
        ir = self.fx.ir()
        second_input = first["resume_input"]
        second_input["specialist_result"] = {"IR_CAPSULE": deepcopy(ir)}
        code, output, err = self.invoke(second_input, "continuation")
        self.assertEqual((code, err), (0, ""))
        second = json.loads(output)
        self.assertEqual(second["replace_null_with"], "PI_DELTA")
        self.assertEqual(set(second["next_handoff"]), {"PI_REQUEST"})
        self.assertEqual(second["next_handoff"]["PI_REQUEST"]["FORWARD_UNCHANGED"], ir)
        self.assertEqual(second["resume_input"]["ir_capsule"], ir)
        self.assertIsNone(second["resume_input"]["specialist_result"])
        self.assertNotIn("pi_delta", second["resume_input"])
        self.assertEqual(second_input["specialist_result"], {"IR_CAPSULE": ir})

        final = second["resume_input"]
        final["specialist_result"] = {
            "PI_DELTA": self.fx.pi(),
            "FORWARD_UNCHANGED": deepcopy(ir),
        }
        code, report, err = self.invoke(final, "report")
        self.assertEqual((code, err), (0, ""))
        code, expected, err = self.invoke(
            {"request": req, "ir_capsule": ir,
             "pi_delta": self.fx.pi(forwarded_ir=deepcopy(ir))}, "report")
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(report, expected)
        code, final_state, err = self.invoke(final, "continuation")
        self.assertEqual((code, err), (0, ""))
        self.assertIn("CONTINUATION_NOT_AVAILABLE", final_state)

    def test_private_pi_only_continuation_does_not_invent_ir(self):
        req = self.fx.request(research_needed=False, portfolio_needed=True)
        initial = {"request": req}
        code, output, err = self.invoke(initial, "continuation")
        self.assertEqual((code, err), (0, ""))
        step = json.loads(output)
        self.assertEqual(step["replace_null_with"], "PI_DELTA")
        self.assertEqual(set(step["next_handoff"]), {"PI_REQUEST"})
        self.assertNotIn("ir_capsule", step["resume_input"])
        final = step["resume_input"]
        final["specialist_result"] = {"PI_DELTA": self.fx.pi()}
        code, report, err = self.invoke(final, "report")
        self.assertEqual((code, err), (0, ""))
        self.assertIn("Portfolio-only interpretation", report)

    def test_private_continuation_is_not_created_for_finished_or_direct(self):
        for payload in (
            {"request": self.fx.request(research_needed=False)},
            {"request": self.fx.request(), "ir_capsule": self.fx.ir()},
            {"request": self.fx.request(research_needed=False, portfolio_needed=True),
             "pi_delta": self.fx.pi()},
        ):
            with self.subTest(route=payload["request"]):
                code, output, err = self.invoke(payload, "continuation")
                self.assertEqual((code, err), (0, ""))
                self.assertTrue(output.startswith("CONTINUATION_NOT_AVAILABLE: "))
                self.assertNotIn("resume_input", output)

    def test_default_status_never_prints_private_continuation(self):
        req = self.fx.request(portfolio_needed=True,
                              account_context={"account": "PRIVATE_ACCOUNT_TOKEN"})
        payload = {"request": req}
        code, out, err = self.invoke(payload)
        self.assertEqual((code, err), (0, ""))
        self.assertNotIn("PRIVATE_ACCOUNT_TOKEN", out)
        self.assertNotIn("resume_input", out)
        code, out, err = self.invoke(payload, "continuation")
        self.assertEqual((code, err), (0, ""))
        self.assertIn("PRIVATE_ACCOUNT_TOKEN", out)
        self.assertEqual(json.loads(out)["project_invocation"], "NONE")

    def test_private_continuation_preserves_ir_original_in_resumed_pi_comparison(self):
        request = self.fx.request(portfolio_needed=True)
        ir = self.fx.ir()
        code, text, error = self.invoke(
            {"request": request, "specialist_result": {"IR_CAPSULE": ir}},
            "continuation",
        )
        self.assertEqual((code, error), (0, ""))
        resume = json.loads(text)["resume_input"]
        resume["specialist_result"] = {
            "PI_DELTA": self.fx.pi(),
            "FORWARD_UNCHANGED": {"analysis_id": ir["analysis_id"], "fake": True},
        }
        code, report, error = self.invoke(resume, "report")
        self.assertEqual(code, 2)
        self.assertEqual(report, "")
        self.assertIn("SPECIALIST_FORWARDED_IR_MISMATCH", error)

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


    def test_operator_packet_pending_matches_status_review_and_continuation(self):
        payload = {"request": self.fx.request(
            portfolio_needed=True, account_context={"account": "PRIVATE_ACCOUNT"})}
        before = deepcopy(payload)
        code, output, err = self.invoke(payload, "operator-packet")
        self.assertEqual((code, err), (0, ""))
        item = json.loads(output)
        self.assertEqual(item["status"], "PRIVATE_OPERATOR_PACKET_NOT_SENT")
        self.assertIsNone(item["report_private"])
        self.assertEqual(item["session"], json.loads(self.invoke(payload, "status")[1]))
        self.assertEqual(item["review_queue"],
                         json.loads(self.invoke(payload, "review-queue")[1]))
        self.assertEqual(item["continuation_private"],
                         json.loads(self.invoke(payload, "continuation")[1]))
        self.assertEqual(set(item["continuation_private"]["next_handoff"]),
                         {"IR_REQUEST"})
        self.assertNotIn("PRIVATE_ACCOUNT", self.invoke(payload, "status")[1])
        self.assertIn("PRIVATE_ACCOUNT", output)
        self.assertEqual(payload, before)

    def test_operator_packet_round_trip_ir_pi_to_final_conditional_report(self):
        request = self.fx.request(portfolio_needed=True)
        first = json.loads(self.invoke({"request": request}, "operator-packet")[1])
        ir = self.fx.ir()
        second_input = first["continuation_private"]["resume_input"]
        second_input["specialist_result"] = {"IR_CAPSULE": deepcopy(ir)}
        second = json.loads(self.invoke(second_input, "operator-packet")[1])
        self.assertEqual(set(second["continuation_private"]["next_handoff"]),
                         {"PI_REQUEST"})
        self.assertEqual(second["continuation_private"]["next_handoff"]
                         ["PI_REQUEST"]["FORWARD_UNCHANGED"], ir)
        last = second["continuation_private"]["resume_input"]
        last["specialist_result"] = {
            "PI_DELTA": self.fx.pi(), "FORWARD_UNCHANGED": deepcopy(ir)}
        before = deepcopy(last)
        code, output, err = self.invoke(last, "operator-packet")
        self.assertEqual((code, err), (0, ""))
        item = json.loads(output)
        self.assertIsNone(item["continuation_private"])
        self.assertEqual(item["report_private"],
                         self.invoke(last, "report")[1])
        self.assertEqual(item["review_queue"],
                         json.loads(self.invoke(last, "review-queue")[1]))
        self.assertEqual(item["readiness"], "NOT_EVALUATED")
        self.assertEqual(item["project_invocation"], "NONE")
        self.assertEqual(last, before)

    def test_operator_packet_pi_only_and_direct_do_not_invent_issuer_research(self):
        payload = {"request": self.fx.request(
            research_needed=False, portfolio_needed=True), "pi_delta": self.fx.pi()}
        code, output, err = self.invoke(payload, "operator-packet")
        self.assertEqual((code, err), (0, ""))
        item = json.loads(output)
        self.assertIsNone(item["continuation_private"])
        self.assertIn("Portfolio-only interpretation", item["report_private"])
        payload = {"request": self.fx.request(research_needed=False)}
        code, output, err = self.invoke(payload, "operator-packet")
        self.assertEqual((code, err), (0, ""))
        item = json.loads(output)
        self.assertIsNone(item["report_private"])
        self.assertIsNone(item["continuation_private"])
        self.assertEqual(item["review_queue"]["items"][0]["code"],
                         "CC_DIRECT_REVIEW")

    def test_operator_packet_unavailable_work_never_emits_pi_or_raw_html(self):
        payload = {"request": self.fx.request(
            research_needed=False, portfolio_needed=True),
            "work_portfolio_result": {"work_blossom_inputs": {
                "capture_mode": "WORK_BROWSER", "view_status": "UNAVAILABLE",
                "analysis_id": "CASE-A", "analysis_as_of": "2026-10-28",
                "raw_html": "PRIVATE_WORK_TOKEN"}}}
        code, output, err = self.invoke(payload, "operator-packet")
        self.assertEqual((code, err), (0, ""))
        item = json.loads(output)
        self.assertEqual(item["session"]["status"],
                         "AWAITING_MANUAL_PORTFOLIO_SCREENSHOT")
        self.assertIsNone(item["continuation_private"])
        self.assertIsNone(item["report_private"])
        self.assertIn("CAPTURE_AUTHORIZED_PORTFOLIO_SCREENSHOT",
                      [v["code"] for v in item["review_queue"]["items"]])
        self.assertNotIn("PRIVATE_WORK_TOKEN", output)
        self.assertNotIn("PI_REQUEST", output)


    def test_method_handoff_ir_then_pi_reuses_current_real_manual_transfer(self):
        req = self.fx.request(portfolio_needed=True, strategy_id="balanced")
        initial = {"request": req}
        snapshot = deepcopy(initial)
        code, output, error = self.invoke(initial, "method-handoff")
        self.assertEqual((code, error), (0, ""))
        first = json.loads(output)
        self.assertEqual(first["status"], "PRIVATE_METHOD_HANDOFF_PREPARED_NOT_SENT")
        self.assertEqual(first["local_content_integrity"],
                         "GIT_BLOBS_MATCH_PINNED_REFERENCE")
        self.assertEqual(first["project_method_load_verification"], "NOT_PERFORMED")
        self.assertEqual(len(first["document_contents_private"]), 3)
        self.assertTrue(all(item["content"] for item in
                            first["document_contents_private"]))
        self.assertEqual(first["continuation_private"],
                         json.loads(self.invoke(initial, "continuation")[1]))
        self.assertEqual(initial, snapshot)

        ir = self.fx.ir()
        second_input = first["continuation_private"]["resume_input"]
        second_input["specialist_result"] = {"IR_CAPSULE": deepcopy(ir)}
        code, output, error = self.invoke(second_input, "method-handoff")
        self.assertEqual((code, error), (0, ""))
        second = json.loads(output)
        self.assertEqual(len(second["document_contents_private"]), 4)
        self.assertEqual(
            second["continuation_private"]["next_handoff"]["PI_REQUEST"]
            ["FORWARD_UNCHANGED"], ir)
        self.assertEqual(second["project_invocation"], "NONE")
        self.assertEqual(second["trading_authority"], "NONE")

    def test_method_handoff_unavailable_work_or_finished_never_loads_files(self):
        unavailable = {"request": self.fx.request(
            research_needed=False, portfolio_needed=True),
            "work_portfolio_result": {"work_blossom_inputs": {
                "capture_mode": "WORK_BROWSER", "view_status": "UNAVAILABLE",
                "analysis_id": "CASE-A", "analysis_as_of": "2026-10-28",
                "raw_html": "SECRET_CAPTURE"}}}
        code, output, error = self.invoke(unavailable, "method-handoff")
        self.assertEqual((code, error), (0, ""))
        self.assertEqual(output, "METHOD_HANDOFF_NOT_AVAILABLE: " +
                         "AWAITING_MANUAL_PORTFOLIO_SCREENSHOT\n")
        self.assertNotIn("SECRET_CAPTURE", output)
        finished = {"request": self.fx.request(),
                    "ir_capsule": self.fx.ir()}
        code, output, error = self.invoke(finished, "method-handoff")
        self.assertEqual((code, error), (0, ""))
        self.assertIn("METHOD_HANDOFF_NOT_AVAILABLE", output)
        self.assertNotIn("document_contents_private", output)
        self.assertEqual(self.invoke(finished, "status")[0], 0)


    def test_private_case_envelope_round_trip_to_inert_followup(self):
        payload = {
            "request": self.fx.request(subject_id="SYN-ISSUER",
                                       account_context={"token": "PRIVATE_ACCOUNT_TOKEN"}),
            "ir_capsule": self.fx.ir(),
            "memory_inputs": {"report_id": "REPORT-A",
                              "instruction_version": "R1-SYN",
                              "recorded_at": "2026-10-28"},
        }
        before = deepcopy(payload)
        code, out, err = self.invoke(payload, "private-case-envelope")
        self.assertEqual((code, err), (0, ""))
        envelope = json.loads(out)
        prior = json.loads(self.invoke(payload, "private-case")[1])
        self.assertEqual(envelope["private_case"], prior)
        self.assertEqual(envelope["confidentiality"], "NOT_PROVIDED_BY_CHECKSUM")
        self.assertEqual(envelope["authenticity"],
                         "NOT_ESTABLISHED_UNKEYED_CHECKSUM")
        self.assertEqual(envelope["storage"], "NONE")
        self.assertIn("PRIVATE_ACCOUNT_TOKEN", out)
        self.assertNotIn("PRIVATE_ACCOUNT_TOKEN", self.invoke(payload, "status")[1])
        code, restored, err = self.invoke(
            {"private_case_envelope": envelope}, "sealed-followup-draft")
        self.assertEqual((code, err), (0, ""))
        followup = json.loads(restored)
        regular = json.loads(self.invoke(
            {"prior_private_case": prior}, "followup-draft")[1])
        self.assertEqual(followup["input_template"], regular["input_template"])
        self.assertEqual(followup["status"],
                         "PRIVATE_FOLLOWUP_DRAFT_REQUIRES_CEO_INITIATION")
        self.assertEqual(followup["record_authenticity"], "NOT_ESTABLISHED")
        self.assertIs(followup["input_template"]["request"]["ceo_initiated"], False)
        self.assertEqual(payload, before)

    def test_modified_sealed_record_rejected_without_private_value_disclosure(self):
        payload = {
            "request": self.fx.request(subject_id="SYN-ISSUER"),
            "ir_capsule": self.fx.ir(),
            "memory_inputs": {"report_id": "REPORT-A",
                              "instruction_version": "R1-SYN",
                              "recorded_at": "2026-10-28"},
        }
        envelope = json.loads(self.invoke(payload, "private-case-envelope")[1])
        original = deepcopy(envelope)
        envelope["private_case"]["original_ir_capsule"]["facts"][0]["claim"] = (
            "VERY_SECRET_NEW_CLAIM")
        code, out, err = self.invoke(
            {"private_case_envelope": envelope}, "sealed-followup-draft")
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("PRIVATE_CASE_SHA256_MISMATCH", err)
        self.assertNotIn("VERY_SECRET_NEW_CLAIM", err)
        self.assertNotIn("VERY_SECRET_NEW_CLAIM", out)
        self.assertNotIn("PRIVATE_ACCOUNT", err)
        self.assertNotIn("VERY_SECRET_NEW_CLAIM", str(original))

    def test_sealed_followup_requires_only_one_expected_private_envelope(self):
        payload = {
            "request": self.fx.request(subject_id="SYN-ISSUER"),
            "ir_capsule": self.fx.ir(),
            "memory_inputs": {"report_id": "REPORT-A",
                              "instruction_version": "R1-SYN",
                              "recorded_at": "2026-10-28"},
        }
        envelope = json.loads(self.invoke(payload, "private-case-envelope")[1])
        for invalid in ({}, {"private_case_envelope": envelope,
                              "request": payload["request"]}):
            with self.subTest(fields=list(invalid)):
                code, out, err = self.invoke(invalid, "sealed-followup-draft")
                self.assertEqual(code, 2)
                self.assertEqual(out, "")
                self.assertIn("PRIVATE_CASE_ENVELOPE_REQUIRED", err)
        code, out, err = self.invoke({"private_case_envelope": envelope}, "status")
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertNotIn("original_ir_capsule", err)


    def test_specialist_prompt_ir_pi_route_only_manual_ready_text(self):
        input_packet = {"request": self.fx.request(
            portfolio_needed=True, strategy_id="balanced",
            account_context={"label": "PRIVATE_ACCOUNT_SENTINEL"})}
        snapshot = deepcopy(input_packet)
        code, output, error = self.invoke(input_packet, "specialist-prompt")
        self.assertEqual((code, error), (0, ""))
        self.assertIn("Recipient: Investment Research (IR)", output)
        self.assertIn("REQUEST_JSON (IR_REQUEST)", output)
        self.assertIn("METHOD_PATH:", output)
        self.assertNotIn("resume_input", output)
        self.assertNotIn("specialist_result", output)
        self.assertIn("PRIVATE_ACCOUNT_SENTINEL", output)
        self.assertEqual(input_packet, snapshot)
        code, status, error = self.invoke(input_packet, "status")
        self.assertEqual((code, error), (0, ""))
        self.assertNotIn("PRIVATE_ACCOUNT_SENTINEL", status)
        second = {**input_packet, "ir_capsule": self.fx.ir()}
        code, output, error = self.invoke(second, "specialist-prompt")
        self.assertEqual((code, error), (0, ""))
        self.assertIn("Recipient: Portfolio Intelligence (PI)", output)
        self.assertIn("REQUEST_JSON (PI_REQUEST)", output)
        self.assertIn('"FORWARD_UNCHANGED"', output)
        self.assertIn("unchanged in every field", output)

    def test_specialist_prompt_does_not_manufacture_completed_or_unavailable_step(self):
        for payload in (
            {"request": self.fx.request(research_needed=False)},
            {"request": self.fx.request(), "ir_capsule": self.fx.ir()},
            {"request": self.fx.request(research_needed=False, portfolio_needed=True),
             "work_portfolio_result": {"work_blossom_inputs": {
                 "capture_mode": "WORK_BROWSER", "view_status": "UNAVAILABLE",
                 "analysis_id": "CASE-A", "analysis_as_of": "2026-10-28",
                 "raw_html": "SECRET_BROWSER_TOKEN"}}},
        ):
            with self.subTest(request=payload["request"]):
                code, out, error = self.invoke(payload, "specialist-prompt")
                self.assertEqual((code, error), (0, ""))
                self.assertIn("SPECIALIST_PROMPT_NOT_AVAILABLE:", out)
                self.assertNotIn("SECRET_BROWSER_TOKEN", out)
                self.assertNotIn("METHOD_PATH:", out)


    def test_resume_operator_ir_pi_round_trip_without_editing_resume_json(self):
        initial = {"request": self.fx.request(
            portfolio_needed=True, strategy_id="balanced",
            account_context={"account": "PRIVATE_CC_SENTINEL"})}
        before = deepcopy(initial)
        first = json.loads(self.invoke(initial, "operator-packet")[1])
        ir = self.fx.ir()
        input_ir = {"continuation_private": first["continuation_private"],
                    "specialist_result": {"IR_CAPSULE": deepcopy(ir)}}
        saved = deepcopy(input_ir)
        code, body, err = self.invoke(input_ir, "resume-operator")
        self.assertEqual((code, err), (0, ""))
        second = json.loads(body)
        self.assertEqual(second["session"]["status"], "AWAITING_MANUAL_PI_DELTA")
        self.assertEqual(set(second["continuation_private"]["next_handoff"]),
                         {"PI_REQUEST"})
        self.assertEqual(second["continuation_private"]["next_handoff"]
                         ["PI_REQUEST"]["FORWARD_UNCHANGED"], ir)
        self.assertEqual(input_ir, saved)
        input_pi = {
            "continuation_private": second["continuation_private"],
            "specialist_result": {
                "PI_DELTA": self.fx.pi(),
                "FORWARD_UNCHANGED": deepcopy(ir),
            },
        }
        code, body, err = self.invoke(input_pi, "resume-operator")
        self.assertEqual((code, err), (0, ""))
        final = json.loads(body)
        self.assertIsNone(final["continuation_private"])
        self.assertEqual(final["session"]["status"],
                         "M7A_COMPONENT_ASSEMBLED_NOT_END_TO_END_ACCEPTANCE")
        expected = deepcopy(second["continuation_private"]["resume_input"])
        expected["specialist_result"] = deepcopy(input_pi["specialist_result"])
        self.assertEqual(final["report_private"], self.invoke(expected, "report")[1])
        self.assertNotIn("PRIVATE_CC_SENTINEL", self.invoke(initial, "status")[1])
        self.assertEqual(initial, before)

    def test_resume_operator_pi_only_never_invents_original_ir(self):
        request = self.fx.request(research_needed=False, portfolio_needed=True)
        first = json.loads(self.invoke({"request": request}, "operator-packet")[1])
        code, body, err = self.invoke({
            "continuation_private": first["continuation_private"],
            "specialist_result": {"PI_DELTA": self.fx.pi()},
        }, "resume-operator")
        self.assertEqual((code, err), (0, ""))
        result = json.loads(body)
        self.assertIsNone(result["continuation_private"])
        self.assertEqual(result["session"]["route"], "CC_PI_CC")
        self.assertIn("Portfolio-only interpretation", result["report_private"])

    def test_resume_operator_stale_or_tampered_continuation_fails_closed(self):
        first = json.loads(self.invoke({"request": self.fx.request()},
                                       "operator-packet")[1])
        step = first["continuation_private"]
        variants = [
            ("next_handoff", lambda c: c["next_handoff"]["IR_REQUEST"].update(
                analysis_id="FORGED_ID")),
            ("resume_input", lambda c: c["resume_input"]["request"].update(
                objective="CONFIDENTIAL_CHANGED_OBJECTIVE")),
            ("replace_null_with", lambda c: c.update(replace_null_with="PI_DELTA")),
        ]
        for name, change in variants:
            with self.subTest(which=name):
                modified = deepcopy(step)
                change(modified)
                code, body, err = self.invoke({
                    "continuation_private": modified,
                    "specialist_result": {"IR_CAPSULE": self.fx.ir()},
                }, "resume-operator")
                self.assertEqual(code, 2)
                self.assertEqual(body, "")
                self.assertNotIn("CONFIDENTIAL_CHANGED_OBJECTIVE", err)
                self.assertNotIn("FORGED_ID", err)

    def test_resume_operator_requires_correct_specialist_and_original_ir(self):
        first = json.loads(self.invoke({
            "request": self.fx.request(portfolio_needed=True)},
            "operator-packet")[1])
        code, body, err = self.invoke({
            "continuation_private": first["continuation_private"],
            "specialist_result": {"PI_DELTA": self.fx.pi()},
        }, "resume-operator")
        self.assertEqual(code, 2)
        self.assertEqual(body, "")
        self.assertIn("MANUAL_RESUME_STAGE_MISMATCH", err)

        ir = self.fx.ir()
        second = json.loads(self.invoke({
            "request": self.fx.request(portfolio_needed=True),
            "ir_capsule": ir,
        }, "operator-packet")[1])
        cont = second["continuation_private"]
        code, body, err = self.invoke({
            "continuation_private": cont,
            "specialist_result": {"PI_DELTA": self.fx.pi()},
        }, "resume-operator")
        self.assertEqual(code, 2)
        self.assertIn("MANUAL_RESUME_STAGE_MISMATCH", err)
        bad = {"PI_DELTA": self.fx.pi(),
               "FORWARD_UNCHANGED": {"analysis_id": ir["analysis_id"],
                                     "PRIVATE_SECRET": "BAD_COPY"}}
        code, body, err = self.invoke({
            "continuation_private": cont, "specialist_result": bad,
        }, "resume-operator")
        self.assertEqual(code, 2)
        self.assertEqual(body, "")
        self.assertIn("SPECIALIST_FORWARDED_IR_MISMATCH", err)
        self.assertNotIn("PRIVATE_SECRET", err)

    def test_resume_operator_refuses_completed_direct_and_screenshot_fallback(self):
        inputs = (
            {"request": self.fx.request(research_needed=False)},
            {"request": self.fx.request(), "ir_capsule": self.fx.ir()},
            {"request": self.fx.request(research_needed=False,
                                        portfolio_needed=True),
             "work_portfolio_result": {"work_blossom_inputs": {
                 "capture_mode": "WORK_BROWSER", "view_status": "UNAVAILABLE",
                 "analysis_id": "CASE-A", "analysis_as_of": "2026-10-28",
                 "raw_html": "PRIVATE_BLOSSOM_TOKEN"}}},
        )
        for initial in inputs:
            with self.subTest(route=initial["request"]):
                first = json.loads(self.invoke(initial, "operator-packet")[1])
                self.assertIsNone(first["continuation_private"])
                code, body, err = self.invoke({
                    "continuation_private": first["continuation_private"],
                    "specialist_result": {"IR_CAPSULE": self.fx.ir()},
                }, "resume-operator")
                self.assertEqual(code, 2)
                self.assertEqual(body, "")
                self.assertIn("MANUAL_RESUME_ENVELOPE_INVALID", err)
                self.assertNotIn("PRIVATE_BLOSSOM_TOKEN", err)


    def test_guided_initial_and_return_roundtrip_to_final_cc(self):
        initial = {"request": self.fx.request(
            portfolio_needed=True, strategy_id="balanced",
            account_context={"account": "PRIVATE_GUIDED_SENTINEL"})}
        snap = deepcopy(initial)
        code, text, err = self.invoke(initial, "guided-operator")
        self.assertEqual((code, err), (0, ""))
        first = json.loads(text)
        self.assertEqual(first["specialist_step"], "IR_REQUEST")
        self.assertEqual(first["specialist_prompt_private"],
                         self.invoke(initial, "specialist-prompt")[1])
        self.assertEqual(first["operator_packet_private"],
                         json.loads(self.invoke(initial, "operator-packet")[1]))
        self.assertNotIn('"resume_input"', first["specialist_prompt_private"])
        self.assertEqual(initial, snap)
        ir = self.fx.ir()
        ir_reply = {"continuation_private": first["operator_packet_private"][
            "continuation_private"], "specialist_result": {"IR_CAPSULE": deepcopy(ir)}}
        code, text, err = self.invoke(ir_reply, "guided-operator")
        self.assertEqual((code, err), (0, ""))
        second = json.loads(text)
        self.assertEqual(second["specialist_step"], "PI_REQUEST")
        self.assertIn("Recipient: Portfolio Intelligence (PI)",
                      second["specialist_prompt_private"])
        self.assertEqual(second["operator_packet_private"]["continuation_private"]
                         ["next_handoff"]["PI_REQUEST"]["FORWARD_UNCHANGED"], ir)
        pi_reply = {"continuation_private": second["operator_packet_private"][
            "continuation_private"],
            "specialist_result": {"PI_DELTA": self.fx.pi(),
                                  "FORWARD_UNCHANGED": deepcopy(ir)}}
        code, text, err = self.invoke(pi_reply, "guided-operator")
        self.assertEqual((code, err), (0, ""))
        final = json.loads(text)
        self.assertIsNone(final["specialist_prompt_private"])
        self.assertIsNone(final["specialist_step"])
        self.assertEqual(final["copy_to_specialist"], "NONE")
        self.assertIsNone(final["operator_packet_private"]["continuation_private"])
        self.assertEqual(final["operator_packet_private"],
                         json.loads(self.invoke(pi_reply, "resume-operator")[1]))
        self.assertEqual(final["project_invocation"], "NONE")
        self.assertEqual(final["storage"], "NONE")
        self.assertEqual(final["method_load_verification"], "NOT_PERFORMED")
        self.assertNotIn("PRIVATE_GUIDED_SENTINEL", self.invoke(initial, "status")[1])

    def test_guided_pi_only_and_direct_require_no_invented_ir(self):
        pi_only = {"request": self.fx.request(
            research_needed=False, portfolio_needed=True)}
        code, text, err = self.invoke(pi_only, "guided-operator")
        self.assertEqual((code, err), (0, ""))
        first = json.loads(text)
        self.assertEqual(first["specialist_step"], "PI_REQUEST")
        self.assertIn("Do not invent a prior IR_CAPSULE",
                      first["specialist_prompt_private"])
        inp = {"continuation_private": first["operator_packet_private"][
            "continuation_private"], "specialist_result": {"PI_DELTA": self.fx.pi()}}
        code, text, err = self.invoke(inp, "guided-operator")
        self.assertEqual((code, err), (0, ""))
        second = json.loads(text)
        self.assertIsNone(second["specialist_prompt_private"])
        self.assertIn("Portfolio-only interpretation",
                      second["operator_packet_private"]["report_private"])
        direct = {"request": self.fx.request(research_needed=False)}
        code, text, err = self.invoke(direct, "guided-operator")
        self.assertEqual((code, err), (0, ""))
        self.assertIsNone(json.loads(text)["specialist_prompt_private"])

    def test_guided_unavailable_browser_has_no_pi_or_raw_capture(self):
        payload = {"request": self.fx.request(
            research_needed=False, portfolio_needed=True),
            "work_portfolio_result": {"work_blossom_inputs": {
                "capture_mode": "WORK_BROWSER", "view_status": "UNAVAILABLE",
                "analysis_id": "CASE-A", "analysis_as_of": "2026-10-28",
                "raw_html": "PRIVATE_RAW_CAPTURE_SENTINEL"}}}
        code, text, err = self.invoke(payload, "guided-operator")
        self.assertEqual((code, err), (0, ""))
        item = json.loads(text)
        self.assertIsNone(item["specialist_prompt_private"])
        self.assertIsNone(item["operator_packet_private"]["continuation_private"])
        self.assertEqual(item["operator_packet_private"]["session"]["status"],
                         "AWAITING_MANUAL_PORTFOLIO_SCREENSHOT")
        self.assertNotIn("PRIVATE_RAW_CAPTURE_SENTINEL", text)
        self.assertNotIn("PI_REQUEST", text)

    def test_guided_rejects_changed_or_wrong_specialist_step_without_leak(self):
        first = json.loads(self.invoke({"request": self.fx.request()},
                                       "guided-operator")[1])
        continuation = first["operator_packet_private"]["continuation_private"]
        fake = deepcopy(continuation)
        fake["next_handoff"]["IR_REQUEST"]["strategy_id"] = "high-cagr"
        for bad in (
            {"continuation_private": fake,
             "specialist_result": {"IR_CAPSULE": self.fx.ir()}},
            {"continuation_private": continuation,
             "specialist_result": {"PI_DELTA": self.fx.pi()}},
            {"continuation_private": continuation,
             "specialist_result": {"IR_CAPSULE": self.fx.ir()},
             "private_extra": "SECRET_NO_PRINT"},
        ):
            with self.subTest(bad=tuple(bad)):
                code, out, err = self.invoke(bad, "guided-operator")
                self.assertEqual(code, 2)
                self.assertEqual(out, "")
                self.assertNotIn("SECRET_NO_PRINT", err)

    def test_guided_six_strategy_modes_preserve_single_existing_prompt(self):
        for strategy in (
            "high-cagr", "balanced", "family-office",
            "rational-aggressive", "intelligent-dividend-harvester",
            "modern-adaptive-browne",
        ):
            with self.subTest(strategy=strategy):
                initial = {"request": self.fx.request(strategy_id=strategy)}
                code, out, err = self.invoke(initial, "guided-operator")
                self.assertEqual((code, err), (0, ""))
                item = json.loads(out)
                self.assertEqual(item["specialist_step"], "IR_REQUEST")
                self.assertEqual(item["specialist_prompt_private"],
                                 self.invoke(initial, "specialist-prompt")[1])
                self.assertIn("PINNED_METHOD_TEXTS", item["specialist_prompt_private"])
if __name__ == "__main__":
    unittest.main()
