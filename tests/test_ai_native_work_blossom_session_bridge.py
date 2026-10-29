"""Synthetic Work/Blossom-to-M3-to-CC integration tests; no live browser or portfolio."""
from __future__ import annotations

from copy import deepcopy
from io import StringIO
import json
import unittest

from ai_native.session_bridge import complete_manual_session
from ai_native.manual_review_queue import prepare_manual_review_queue
from scripts.r1_manual_session_cli import main
from tests.test_ai_native_session_bridge import SessionBridgeTests


class BlossomSessionBridgeTests(unittest.TestCase):
    def setUp(self):
        self.fx = SessionBridgeTests()

    def report(self, mode="WORK_BROWSER", **changes):
        data = {
            "capture_mode": mode,
            "view_status": "VISIBLE",
            "user_authorized_read_only": True,
            "private_portfolio_view": True,
            "browser_hostname": "www.blossomsocial.com",
            "work_reported_signed_in": True,
            "source_access_reported": True,
            "analysis_id": "CASE-A",
            "analysis_as_of": "2026-10-28",
            "observed_on": "2026-10-28",
            "captured_at": "2026-10-28T09:45:00-04:00",
            "account_scope": "SYNTHETIC_ACCOUNT_SECRET",
            "currency": "CAD",
            "cash_base": "20.00",
            "cash_visibility": "VERIFIED_VISIBLE",
            "coverage_evidence": {name: True for name in (
                "account_filter_visible", "all_rows_visible",
                "other_group_expanded_or_absent", "cash_checked",
                "same_currency_basis_visible",
            )},
            "positions": [
                {
                    "p_id": "P1",
                    "security_id": "SYNTHETIC-HOLDING:TSX",
                    "market_value_base": "80.00",
                    "currency": "CAD",
                    "account_scope": "SYNTHETIC_ACCOUNT_SECRET",
                    "field_statuses": {name: "VERIFIED_VISIBLE" for name in (
                        "security_id", "market_value_base",
                        "currency", "account_scope",
                    )},
                }
            ],
            "raw_html": "TOKEN_THAT_MUST_NOT_PASS",
        }
        if mode == "USER_SCREENSHOT":
            data["browser_hostname"] = None
            data["work_reported_signed_in"] = False
        data.update(changes)
        return data

    def pi_only(self):
        return self.fx.request(research_needed=False, portfolio_needed=True)

    def cli(self, data, output="status"):
        stdin=StringIO(json.dumps(data))
        stdout,stderr=StringIO(),StringIO()
        code=main(["--output",output],instream=stdin,
                  outstream=stdout,errstream=stderr)
        return code,stdout.getvalue(),stderr.getvalue()


    def test_pi1_wrapped_private_work_packet_reaches_original_pi_ledger(self):
        source = self.report()
        payload = {"request": self.pi_only(),
                   "work_portfolio_result": {"work_blossom_inputs": source}}
        before = deepcopy(payload)
        code, output, error = self.cli(payload, "next-handoff")
        self.assertEqual((code, error), (0, ""))
        packet = json.loads(output)
        self.assertEqual(set(packet), {"PI_REQUEST"})
        original = complete_manual_session(
            self.pi_only(), work_blossom_inputs=source)
        self.assertEqual(packet["PI_REQUEST"],
                         original["handoffs_private"]["pi_request_private"])
        self.assertEqual(
            packet["PI_REQUEST"]["P_LEDGER_FOR_REVIEW_PRIVATE"]["known_scope_weights_pct"]["P1"],
            "80.00",
        )
        self.assertNotIn("TOKEN_THAT_MUST_NOT_PASS", output)
        self.assertEqual(payload, before)
        code, redacted, error = self.cli(payload, "status")
        self.assertEqual((code, error), (0, ""))
        self.assertNotIn("SYNTHETIC_ACCOUNT_SECRET", redacted)
        self.assertNotIn("SYNTHETIC-HOLDING", redacted)

    def test_pi1_wrapped_private_work_stays_ir_first(self):
        payload = {"request": self.fx.request(portfolio_needed=True),
                   "work_portfolio_result": {"work_blossom_inputs": self.report()}}
        code, handoff, error = self.cli(payload, "next-handoff")
        self.assertEqual((code, error), (0, ""))
        self.assertEqual(set(json.loads(handoff)), {"IR_REQUEST"})
        self.assertNotIn("P_LEDGER_FOR_REVIEW_PRIVATE", handoff)
        self.assertNotIn("SYNTHETIC_ACCOUNT_SECRET", handoff)

    def test_pi1_wrapped_private_unavailable_does_not_invent_holdings(self):
        unavailable = {
            "capture_mode": "WORK_BROWSER", "view_status": "UNAVAILABLE",
            "analysis_id": "CASE-A", "analysis_as_of": "2026-10-28",
        }
        payload = {"request": self.pi_only(),
                   "work_portfolio_result": {"work_blossom_inputs": unavailable}}
        code, output, error = self.cli(payload, "status")
        self.assertEqual((code, error), (0, ""))
        self.assertEqual(json.loads(output)["status"],
                         "AWAITING_MANUAL_PORTFOLIO_SCREENSHOT")
        code, next_handoff, error = self.cli(payload, "next-handoff")
        self.assertEqual((code, error), (0, ""))
        self.assertIn("NEXT_HANDOFF_NOT_AVAILABLE", next_handoff)
        self.assertNotIn("PI_REQUEST", next_handoff)

    def test_pi1_wrapper_rejects_ambiguous_and_malformed_shapes_without_leaks(self):
        source = self.report()
        for wrapper in (
            {},
            {"work_blossom_inputs": source, "public_portfolio_reference": {}},
            {"work_blossom_inputs": "not-a-mapping"},
            {"unexpected_key": source},
        ):
            with self.subTest(wrapper=list(wrapper)):
                code, output, error = self.cli(
                    {"request": self.pi_only(), "work_portfolio_result": wrapper})
                self.assertEqual(code, 2)
                self.assertEqual(output, "")
                self.assertIn("WORK_PORTFOLIO_RESULT_INVALID", error)
                self.assertNotIn("SYNTHETIC_ACCOUNT_SECRET", error)
        for conflicting in (
            {"work_blossom_inputs": source},
            {"observation_inputs": {"analysis_id": "CASE-A"}},
            {"public_reference_inputs": {}},
            {"public_reference_table_inputs": {}},
        ):
            with self.subTest(conflicting=list(conflicting)):
                code, output, error = self.cli({
                    "request": self.pi_only(),
                    "work_portfolio_result": {"work_blossom_inputs": source},
                    **conflicting,
                })
                self.assertEqual(code, 2)
                self.assertEqual(output, "")
                self.assertIn("WORK_PORTFOLIO_RESULT_AMBIGUOUS", error)
                self.assertNotIn("SYNTHETIC_ACCOUNT_SECRET", error)

    def test_pi1_wrapped_private_work_rejects_identity_and_non_pi_routes(self):
        source = self.report(analysis_id="WRONG")
        cases = (
            {"request": self.pi_only(), "work_portfolio_result": {
                "work_blossom_inputs": source}},
            {"request": self.fx.request(), "work_portfolio_result": {
                "work_blossom_inputs": self.report()}},
        )
        for payload in cases:
            with self.subTest(route=payload["request"]["portfolio_needed"]):
                code, output, error = self.cli(payload, "next-handoff")
                self.assertEqual(code, 2)
                self.assertEqual(output, "")
                self.assertIn("R1_INPUT_REJECTED", error)
                self.assertNotIn("SYNTHETIC_ACCOUNT_SECRET", error)

    def test_authorized_work_view_reaches_pi_only_report_without_ir(self):
        req, pi, packet=self.pi_only(), self.fx.pi(), self.report()
        copy=deepcopy((req,pi,packet))
        result=complete_manual_session(req,pi_delta=pi,
                                       work_blossom_inputs=packet)
        self.assertEqual((req,pi,packet),copy)
        self.assertEqual(result["status"],"PI_ONLY_CONDITIONAL_REPORT_ASSEMBLED")
        self.assertEqual(result["work_blossom_capture_private"]["transfer"],"MANUAL_ONLY")
        self.assertEqual(result["portfolio_observation_private"]["status"],
                         "SCOPED_WEIGHTS_DERIVED_FROM_CALLER_VISIBLE_DATA")
        self.assertEqual(result["portfolio_observation_private"]["known_scope_weights_pct"]["P1"],"80.00")
        self.assertIn("not independently verified", result["final_report_private"])
        self.assertEqual(result["readiness"],"NOT_EVALUATED")
        self.assertEqual(result["project_invocation"],"NONE")
        self.assertEqual(result["storage"],"NONE")

    def test_authorized_screenshot_without_work_signin_claim(self):
        result=complete_manual_session(
            self.pi_only(),pi_delta=self.fx.pi(),
            work_blossom_inputs=self.report(mode="USER_SCREENSHOT"))
        self.assertEqual(result["work_blossom_capture_private"]["observation_inputs_private"]["source_type"],
                         "PRIVATE_SCREENSHOT_TRANSCRIPTION")
        self.assertEqual(result["work_blossom_capture_private"]["work_compatibility"],
                         "NOT_INDEPENDENTLY_TESTED_BY_ADAPTER")

    def test_ir_plus_pi_preserves_exact_original_capsule(self):
        req=self.fx.request(portfolio_needed=True)
        ir=self.fx.ir()
        pi=self.fx.pi(forwarded_ir=deepcopy(ir))
        before=deepcopy((req,ir,pi))
        result=complete_manual_session(
            req,ir_capsule=ir,pi_delta=pi,work_blossom_inputs=self.report())
        self.assertEqual((req,ir,pi),before)
        self.assertEqual(result["status"],"M7A_COMPONENT_ASSEMBLED_NOT_END_TO_END_ACCEPTANCE")
        self.assertEqual(result["handoffs_private"]["pi_request_private"]["FORWARD_UNCHANGED"],ir)
        self.assertEqual(result["portfolio_observation_private"]["known_scope_weights_pct"]["P1"],"80.00")
        self.assertEqual(result["integrated_private"]["handoff"],"MANUAL_TRANSFER_NOT_PROJECT_AUTOMATION")
        self.assertEqual(result["readiness"],"NOT_EVALUATED")

    def test_visible_capture_without_pi_delta_stays_pending(self):
        result=complete_manual_session(self.pi_only(),
                                       work_blossom_inputs=self.report())
        self.assertEqual(result["status"],"AWAITING_MANUAL_PI_DELTA")
        self.assertIsNone(result["final_report_private"])
        self.assertIsNotNone(result["portfolio_observation_private"])

    def test_missing_ir_first_even_if_work_view_unavailable(self):
        req=self.fx.request(portfolio_needed=True)
        packet=self.report(view_status="UNAVAILABLE")
        result=complete_manual_session(req,work_blossom_inputs=packet)
        self.assertEqual(result["status"],"AWAITING_MANUAL_IR_CAPSULE")

    def test_unavailable_work_returns_fallback_without_private_rows(self):
        packet=self.report(view_status="UNAVAILABLE")
        packet["positions"]=[{"SECRET_CAPTURE":"DO_NOT_FORWARD"}]
        out=complete_manual_session(self.pi_only(),work_blossom_inputs=packet)
        self.assertEqual(out["status"],"AWAITING_MANUAL_PORTFOLIO_SCREENSHOT")
        self.assertIsNone(out["final_report_private"])
        self.assertIsNone(out["portfolio_observation_private"])
        self.assertNotIn("DO_NOT_FORWARD",str(out))
        queue=prepare_manual_review_queue(out)
        self.assertIn("CAPTURE_AUTHORIZED_PORTFOLIO_SCREENSHOT",
                      [x["code"] for x in queue["items"]])
        self.assertEqual(queue["trading_authority"],"NONE")

    def test_unavailable_work_conflicts_with_supplied_pi_delta(self):
        with self.assertRaisesRegex(ValueError,"WORK_BLOSSOM_UNAVAILABLE_CONFLICTS_WITH_PI_DELTA"):
            complete_manual_session(self.pi_only(),pi_delta=self.fx.pi(),
                                    work_blossom_inputs=self.report(view_status="UNAVAILABLE"))

    def test_two_observation_sources_are_not_silently_merged(self):
        with self.assertRaisesRegex(ValueError,"AMBIGUOUS_PORTFOLIO_OBSERVATION_INPUTS"):
            complete_manual_session(self.pi_only(),work_blossom_inputs=self.report(),
                                    observation_inputs={"analysis_id":"CASE-A"})

    def test_no_pi_route_cannot_supply_visual_private_source(self):
        for request in (
            self.fx.request(), self.fx.request(research_needed=False, portfolio_needed=False)
        ):
            with self.subTest(request=request), self.assertRaisesRegex(ValueError,"WORK_BLOSSOM_REQUIRES_PI_ROUTE"):
                complete_manual_session(request,work_blossom_inputs=self.report())

    def test_cross_run_identity_and_date_rejected_including_unavailable(self):
        for mode in ("VISIBLE","UNAVAILABLE"):
            for patched in ({"analysis_id":"OTHER"}, {"analysis_as_of":"2026-10-27"}):
                with self.subTest(mode=mode,patched=patched), self.assertRaisesRegex(ValueError,"WORK_BLOSSOM_ANALYSIS_ID_OR_DATE_MISMATCH"):
                    complete_manual_session(self.pi_only(),work_blossom_inputs=self.report(view_status=mode,**patched))

    def test_unauthorized_public_or_fake_work_host_rejected(self):
        for patched in (
            {"user_authorized_read_only":False},
            {"private_portfolio_view":False},
            {"work_reported_signed_in":False},
            {"browser_hostname":"blossomsocial.com.attack.example"},
        ):
            with self.subTest(patched=patched),self.assertRaises(ValueError):
                complete_manual_session(self.pi_only(),work_blossom_inputs=self.report(**patched))

    def test_incomplete_coverage_cannot_upgrade_weights_or_room(self):
        x=self.report()
        x["coverage_evidence"]["other_group_expanded_or_absent"]=False
        result=complete_manual_session(self.pi_only(),pi_delta=self.fx.pi(),
                                       work_blossom_inputs=x)
        self.assertIsNone(result["portfolio_observation_private"]["known_scope_weights_pct"])
        self.assertEqual(result["portfolio_observation_private"]["portfolio_room_status"],
                         "ROOM_UNAVAILABLE")
        queue=prepare_manual_review_queue(result)
        self.assertIn("RECONCILE_PORTFOLIO_SCOPE",
                      [a["code"] for a in queue["items"]])
        self.assertNotIn("SYNTHETIC_ACCOUNT_SECRET",json.dumps(queue))

    def test_pi_date_mismatch_rejected_even_with_valid_work_packet(self):
        with self.assertRaisesRegex(ValueError,"OBSERVATION_PI_DATE_MISMATCH"):
            complete_manual_session(self.pi_only(),pi_delta=self.fx.pi(portfolio_as_of="2026-10-27"),
                                    work_blossom_inputs=self.report())

    def test_cli_work_and_fallback_source_are_private_and_explicit(self):
        data={"request":self.pi_only(),
              "pi_delta":self.fx.pi(),
              "work_blossom_inputs":self.report()}
        code, status, error=self.cli(data)
        self.assertEqual((code,error),(0,""))
        self.assertEqual(json.loads(status)["readiness"],"NOT_EVALUATED")
        self.assertNotIn("SYNTHETIC_ACCOUNT_SECRET",status)
        code, report, error=self.cli(data,"report")
        self.assertEqual((code,error),(0,""))
        self.assertIn("Portfolio-only interpretation",report)
        self.assertNotIn("SYNTHETIC_ACCOUNT_SECRET",report)
        fallback={"request":self.pi_only(),
                  "work_blossom_inputs":self.report(view_status="UNAVAILABLE")}
        code, pending, error=self.cli(fallback)
        self.assertEqual((code,error),(0,""))
        self.assertEqual(json.loads(pending)["status"],"AWAITING_MANUAL_PORTFOLIO_SCREENSHOT")
        code, queue, error=self.cli(fallback,"review-queue")
        self.assertEqual((code,error),(0,""))
        self.assertIn("CAPTURE_AUTHORIZED_PORTFOLIO_SCREENSHOT",queue)
        self.assertNotIn("SYNTHETIC_ACCOUNT_SECRET",queue)

    def test_visible_private_ledger_is_in_copy_ready_pi_request(self):
        captured = self.report()
        out = complete_manual_session(self.pi_only(), work_blossom_inputs=captured)
        self.assertEqual(out["status"], "AWAITING_MANUAL_PI_DELTA")
        pi_request = out["handoffs_private"]["pi_request_private"]
        original = out["portfolio_observation_private"]
        self.assertEqual(pi_request["P_LEDGER_FOR_REVIEW_PRIVATE"], original)
        self.assertEqual(
            pi_request["P_LEDGER_HANDOFF_AUTHORITY"],
            "CALLER_REPORTED_PRIVATE_OBSERVATION_MANUAL_REVIEW_ONLY",
        )
        self.assertEqual(
            json.loads(out["handoffs_private"]["copy_ready_private"]["PI_REQUEST"]),
            pi_request,
        )
        self.assertNotIn("TOKEN_THAT_MUST_NOT_PASS", json.dumps(pi_request))
        self.assertEqual(original["known_scope_weights_pct"]["P1"], "80.00")
        self.assertEqual(out["project_invocation"], "NONE")

    def test_partial_visual_ledger_is_forwarded_without_upgrading_scope(self):
        partial = self.report()
        partial["coverage_evidence"]["cash_checked"] = False
        out = complete_manual_session(self.pi_only(), work_blossom_inputs=partial)
        forwarded = out["handoffs_private"]["pi_request_private"]["P_LEDGER_FOR_REVIEW_PRIVATE"]
        self.assertIsNone(forwarded["known_scope_weights_pct"])
        self.assertEqual(forwarded["portfolio_room_status"], "ROOM_UNAVAILABLE")
        self.assertIn("SCOPED_HOLDINGS_INCOMPLETE", forwarded["missing_or_qualified"])

    def test_ir_plus_pi_handoff_carries_both_unmodified_ir_and_visual_ledger(self):
        req = self.fx.request(portfolio_needed=True)
        original_ir = self.fx.ir()
        out = complete_manual_session(
            req, ir_capsule=original_ir, work_blossom_inputs=self.report())
        pi_request = out["handoffs_private"]["pi_request_private"]
        self.assertEqual(pi_request["FORWARD_UNCHANGED"], original_ir)
        self.assertEqual(
            pi_request["P_LEDGER_FOR_REVIEW_PRIVATE"],
            out["portfolio_observation_private"],
        )

    def test_conflicting_account_context_blocks_visual_pi_handoff(self):
        with self.assertRaisesRegex(ValueError, "PI_CONTEXT_CONFLICTS_WITH_OBSERVED_P_LEDGER"):
            complete_manual_session(
                self.pi_only(), work_blossom_inputs=self.report(),
                portfolio_context={"observed_at": "2026-10-28", "account_scope": "OTHER_SCOPE"},
            )

    def test_public_observation_cannot_enter_private_pi_handoff(self):
        from ai_native.work_blossom_adapter import prepare_work_blossom_observation

        observed = prepare_work_blossom_observation(self.report())["observation_inputs_private"]
        observed["source_type"] = "PUBLIC_BLOSSOM_REFERENCE"
        observed["private_scope"] = False
        with self.assertRaisesRegex(ValueError, "PUBLIC_OBSERVATION_CANNOT_BECOME_PRIVATE_PI"):
            complete_manual_session(self.pi_only(), observation_inputs=observed)

    def test_pi_handoff_without_visual_ledger_has_no_implied_observation(self):
        out = complete_manual_session(self.pi_only())
        pi_request = out["handoffs_private"]["pi_request_private"]
        self.assertNotIn("P_LEDGER_FOR_REVIEW_PRIVATE", pi_request)
        self.assertNotIn("P_LEDGER_HANDOFF_AUTHORITY", pi_request)


    def test_next_handoff_private_ledger_selects_only_pi_not_raw_work_data(self):
        ir = self.fx.ir()
        original_work = self.report()
        data = {"request": self.fx.request(portfolio_needed=True),
                "ir_capsule": ir, "work_blossom_inputs": original_work}
        before = deepcopy(data)
        code, output, error = self.cli(data, output="next-handoff")
        self.assertEqual((code, error), (0, ""))
        packet = json.loads(output)
        self.assertEqual(set(packet), {"PI_REQUEST"})
        self.assertEqual(packet["PI_REQUEST"]["FORWARD_UNCHANGED"], ir)
        ledger = packet["PI_REQUEST"]["P_LEDGER_FOR_REVIEW_PRIVATE"]
        self.assertEqual(ledger["known_scope_weights_pct"]["P1"], "80.00")
        self.assertNotIn("TOKEN_THAT_MUST_NOT_PASS", output)
        self.assertEqual(data, before)

    def test_next_handoff_ir_first_keeps_private_work_ledger_out_of_ir(self):
        payload = {"request": self.fx.request(portfolio_needed=True),
                   "work_blossom_inputs": self.report()}
        code, output, error = self.cli(payload, output="next-handoff")
        self.assertEqual((code, error), (0, ""))
        self.assertEqual(set(json.loads(output)), {"IR_REQUEST"})
        self.assertNotIn("P_LEDGER_FOR_REVIEW_PRIVATE", output)
        self.assertNotIn("SYNTHETIC_ACCOUNT_SECRET", output)

    def test_next_handoff_requires_screenshot_before_pi_transfer(self):
        payload = {"request": self.pi_only(),
                   "work_blossom_inputs": self.report(view_status="UNAVAILABLE")}
        code, output, error = self.cli(payload, output="next-handoff")
        self.assertEqual((code, error), (0, ""))
        self.assertEqual(
            output, "NEXT_HANDOFF_NOT_AVAILABLE: AWAITING_MANUAL_PORTFOLIO_SCREENSHOT\n"
        )
        self.assertNotIn("PI_REQUEST", output)
        code, queue, error = self.cli(payload, output="review-queue")
        self.assertEqual((code, error), (0, ""))
        self.assertIn("CAPTURE_AUTHORIZED_PORTFOLIO_SCREENSHOT", queue)


    def test_scoped_visual_ledger_coverage_reaches_pi_only_final_report(self):
        result = complete_manual_session(
            self.pi_only(), pi_delta=self.fx.pi(),
            work_blossom_inputs=self.report())
        report = result["final_report_private"]
        self.assertIn("Private portfolio observation — coverage and provenance", report)
        self.assertIn("Observed as of 2026-10-28; 1 caller-reported position row(s)", report)
        self.assertIn("CALLER_REPORTED_SCOPED_DENOMINATOR_ONLY", report)
        self.assertIn("not independently authenticated", report.lower())
        for private_value in ("SYNTHETIC_ACCOUNT_SECRET", "SYNTHETIC-HOLDING", "80.00",
                              "20.00", "TOKEN_THAT_MUST_NOT_PASS"):
            self.assertNotIn(private_value, report)
        self.assertEqual(result["portfolio_observation_private"]["known_scope_weights_pct"]["P1"], "80.00")
        self.assertEqual(result["readiness"], "NOT_EVALUATED")

    def test_ir_pi_final_report_includes_original_private_ledger_limits(self):
        ir = self.fx.ir()
        result = complete_manual_session(
            self.fx.request(portfolio_needed=True),
            ir_capsule=ir, pi_delta=self.fx.pi(forwarded_ir=deepcopy(ir)),
            work_blossom_inputs=self.report())
        self.assertEqual(result["status"], "M7A_COMPONENT_ASSEMBLED_NOT_END_TO_END_ACCEPTANCE")
        report = result["final_report_private"]
        self.assertEqual(report.count("Private portfolio observation — coverage and provenance"), 1)
        self.assertIn("CALLER_REPORTED_SCOPED_DENOMINATOR_ONLY", report)
        self.assertNotIn("SYNTHETIC_ACCOUNT_SECRET", report)
        self.assertNotIn("SYNTHETIC-HOLDING", report)
        self.assertNotIn("80.00", report)
        self.assertEqual(result["handoffs_private"]["pi_request_private"]["FORWARD_UNCHANGED"], ir)
        self.assertEqual(result["project_invocation"], "NONE")

    def test_incomplete_observation_is_explicit_not_reweighted(self):
        partial = self.report()
        partial["coverage_evidence"]["cash_checked"] = False
        result = complete_manual_session(
            self.pi_only(), pi_delta=self.fx.pi(), work_blossom_inputs=partial)
        report = result["final_report_private"]
        self.assertIn("INCOMPLETE_NO_DERIVED_WEIGHTS", report)
        self.assertIn("unresolved qualification(s)", report)
        self.assertNotIn("CALLER_REPORTED_SCOPED_DENOMINATOR_ONLY", report)
        self.assertIsNone(result["portfolio_observation_private"]["known_scope_weights_pct"])

    def test_no_observation_never_adds_observation_section(self):
        result = complete_manual_session(self.pi_only(), pi_delta=self.fx.pi())
        self.assertNotIn("Private portfolio observation", result["final_report_private"])

    def test_report_rejects_tampered_private_observation_authority_or_weights(self):
        from ai_native.reporting import render_report
        base = complete_manual_session(
            self.pi_only(), work_blossom_inputs=self.report())["portfolio_observation_private"]
        packet = {
            "kind": "DECISION", "analysis_id": "CASE-A",
            "as_of": "2026-10-28", "strategy": "EXPLORATORY",
            "method_version": "UNKNOWN_NOT_LOADED", "status": "CONDITIONAL",
            "objective": "Synthetic", "decision_line": "No action",
            "summary": ["Unverified"], "facts": [],
            "countercase": "Incomplete", "limitations": "Unknown", "next_action": "Review",
        }
        for changed in (
            {"verification": "INDEPENDENTLY_VERIFIED"},
            {"private_scope": False},
            {"portfolio_room_status": "ROOM_EVIDENCE_SUPPORTED"},
            {"analysis_id": "WRONG"},
            {"known_scope_weights_pct": {"P1": "50.00", "P-CASH": "50.00"}},
        ):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                tampered = deepcopy(base)
                tampered.update(changed)
                render_report({**packet, "portfolio_observation_private": tampered})

    def test_existing_pi_path_without_visual_packet_unchanged(self):
        result=complete_manual_session(self.pi_only(),pi_delta=self.fx.pi())
        self.assertEqual(result["status"],"PI_ONLY_CONDITIONAL_REPORT_ASSEMBLED")
        self.assertIsNone(result["work_blossom_capture_private"])


if __name__=="__main__":
    unittest.main()
