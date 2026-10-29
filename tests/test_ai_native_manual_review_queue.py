"""Synthetic operator-workflow tests: one finite review queue, never a readiness claim."""
from __future__ import annotations

from copy import deepcopy
from io import StringIO
import json
import unittest

from ai_native.manual_review_queue import prepare_manual_review_queue
from scripts.r1_manual_session_cli import main
from tests.test_ai_native_session_bridge import SessionBridgeTests


class ManualReviewQueueTests(unittest.TestCase):
    def setUp(self):
        self.fx = SessionBridgeTests()

    def shell(self, status, route="CC_IR_PI_CC", **extra):
        return dict(
            status=status, route=route,
            method_load_verification="NOT_PERFORMED",
            source_authentication="NOT_PERFORMED", project_invocation="NONE",
            storage="NONE", readiness="NOT_EVALUATED", **extra)

    def queue(self, status, route="CC_IR_PI_CC", **extra):
        return prepare_manual_review_queue(self.shell(status, route, **extra))

    @staticmethod
    def codes(out):
        return [row["code"] for row in out["items"]]

    def test_ir_pending_only_requests_manual_ir(self):
        out = self.queue("AWAITING_MANUAL_IR_CAPSULE", "CC_IR_PI_CC")
        self.assertEqual(self.codes(out), ["CONFIRM_METHOD_CONTEXT", "TRANSFER_IR_CAPSULE"])
        self.assertEqual(out["readiness"], "NOT_EVALUATED")
        self.assertEqual(out["trading_authority"], "NONE")

    def test_pi_pending_only_requests_manual_pi_not_both(self):
        out = self.queue("AWAITING_MANUAL_PI_DELTA")
        self.assertEqual(self.codes(out), ["CONFIRM_METHOD_CONTEXT", "TRANSFER_PI_DELTA"])

    def test_ir_only_never_asks_for_portfolio_data(self):
        integrated = dict(status="ASSEMBLED_COMPONENT_ONLY_NOT_END_TO_END_ACCEPTANCE",
                          source_evidence_annex_private=None, valuation_quote_trace_private=None)
        out = self.queue("M7A_COMPONENT_ASSEMBLED_NOT_END_TO_END_ACCEPTANCE",
                         "CC_IR_CC", integrated_private=integrated)
        self.assertIn("SOURCE_ANNEX_NOT_PRESENT", self.codes(out))
        self.assertNotIn("VERIFY_DATED_PORTFOLIO", self.codes(out))
        self.assertIn("REVIEW_CONDITIONAL_REPORT", self.codes(out))

    def test_source_fact_and_quote_evidence_remain_human_actions(self):
        integrated = {
            "status":"ASSEMBLED_COMPONENT_ONLY_NOT_END_TO_END_ACCEPTANCE",
            "source_evidence_annex_private":{
                "status":"PRIVATE_SOURCE_ANNEX_PREPARED_NOT_CERTIFIED",
                "observations_private":[{"source_locator":"PRIVATE_ACCOUNT_TOKEN_SECRET"}]},
            "fact_source_alignment_private":{
                "status":"PRIVATE_FACT_SOURCE_ALIGNMENT_NOT_CERTIFIED",
                "facts_needing_review":2},
            "valuation_quote_trace_private":{
                "status":"PRIVATE_QUOTE_SOURCE_TRACE_NOT_CERTIFIED",
                "source_authentication":"NOT_PERFORMED",
                "original_market_price_verification":"NOT_ESTABLISHED",
                "market_price_or_fx_authority":"NONE",
                "review_stage":"EVIDENCE_RESOLUTION",
                "quote_reference_private":"PRIVATE_ACCOUNT_TOKEN_SECRET",
            },
            "valuation_scenarios_private":{"private_price":"12345.67",
                                            "terminal_value_ref":"PRIVATE_ACCOUNT_TOKEN_SECRET"},
        }
        out = self.queue("M7A_COMPONENT_ASSEMBLED_NOT_END_TO_END_ACCEPTANCE",
                         "CC_IR_CC", integrated_private=integrated)
        self.assertEqual(self.codes(out), [
            "CONFIRM_METHOD_CONTEXT", "VERIFY_ORIGINAL_SOURCES",
            "RECONCILE_IR_FACTS", "RESOLVE_VALUATION_QUOTE",
            "VALIDATE_VALUATION_ASSUMPTIONS", "REVIEW_CONDITIONAL_REPORT"])
        self.assertNotIn("PRIVATE_ACCOUNT_TOKEN_SECRET", json.dumps(out))
        self.assertNotIn("12345.67", json.dumps(out))
        self.assertEqual(out["source_authentication"], "NOT_PERFORMED")

    def test_matched_quote_does_not_hide_original_source_review(self):
        integrated = {
            "status":"ASSEMBLED_COMPONENT_ONLY_NOT_END_TO_END_ACCEPTANCE",
            "source_evidence_annex_private":{},
            "valuation_quote_trace_private":{
                "status":"PRIVATE_QUOTE_SOURCE_TRACE_NOT_CERTIFIED",
                "source_authentication":"NOT_PERFORMED",
                "original_market_price_verification":"NOT_ESTABLISHED",
                "market_price_or_fx_authority":"NONE",
                "review_stage":"HUMAN_QUOTE_REVIEW_ONLY",
            },
        }
        codes = self.codes(self.queue("M7A_COMPONENT_ASSEMBLED_NOT_END_TO_END_ACCEPTANCE",
                                      "CC_IR_CC", integrated_private=integrated))
        self.assertIn("CHECK_ORIGINAL_QUOTE", codes)
        self.assertIn("VERIFY_ORIGINAL_SOURCES", codes)
        self.assertNotIn("RESOLVE_VALUATION_QUOTE", codes)

    def test_portfolio_without_dated_observation_requires_transcription(self):
        out = self.queue("PI_ONLY_CONDITIONAL_REPORT_ASSEMBLED", "CC_PI_CC",
                         portfolio_observation_private=None)
        self.assertIn("VERIFY_DATED_PORTFOLIO", self.codes(out))
        self.assertNotIn("SOURCE_ANNEX_NOT_PRESENT", self.codes(out))

    def test_incomplete_portfolio_cannot_be_called_verified(self):
        out = self.queue("PI_ONLY_CONDITIONAL_REPORT_ASSEMBLED", "CC_PI_CC",
                         portfolio_observation_private={
                             "known_scope_weights_pct":None,
                             "account_scope":"PRIVATE_ACCOUNT_TOKEN_SECRET"})
        self.assertIn("RECONCILE_PORTFOLIO_SCOPE", self.codes(out))
        self.assertNotIn("PRIVATE_ACCOUNT_TOKEN_SECRET",json.dumps(out))

    def test_complete_caller_reported_weights_still_manual_check(self):
        out = self.queue("PI_ONLY_CONDITIONAL_REPORT_ASSEMBLED", "CC_PI_CC",
                         portfolio_observation_private={
                             "known_scope_weights_pct":"100.00",
                             "account_scope":"PRIVATE_ACCOUNT_TOKEN_SECRET"})
        self.assertIn("CHECK_PORTFOLIO_ORIGINAL", self.codes(out))
        self.assertNotIn("RECONCILE_PORTFOLIO_SCOPE", self.codes(out))

    def test_account_costs_not_omitted_for_new_capital(self):
        out = self.queue("PI_ONLY_CONDITIONAL_REPORT_ASSEMBLED", "CC_PI_CC",
                         gross_contribution_private={"gross_amount":"1500",
                                                     "private_security":"SECRET"})
        self.assertIn("RECHECK_ACCOUNT_COSTS", self.codes(out))
        self.assertNotIn("1500", json.dumps(out))

    def test_followup_comparison_always_requests_human_review(self):
        integrated = dict(
            status="ASSEMBLED_COMPONENT_ONLY_NOT_END_TO_END_ACCEPTANCE",
            historical_research_comparison_private={"status":"STRUCTURAL_REVIEW_PREPARED"})
        codes = self.codes(self.queue("M7A_COMPONENT_ASSEMBLED_NOT_END_TO_END_ACCEPTANCE",
                                      "CC_IR_CC", integrated_private=integrated))
        self.assertIn("CHECK_RESEARCH_CHANGES", codes)

    def test_no_unrequested_specialist_starts_work(self):
        out = self.queue("CC_DIRECT_NO_SPECIALIST_REPORT_REQUIRED", "CC_DIRECT")
        self.assertEqual(self.codes(out), ["CC_DIRECT_REVIEW"])

    def test_forged_authority_and_inconsistent_routes_rejected(self):
        for field, value in (
            ("source_authentication", "CERTIFIED"),
            ("method_load_verification", "VERIFIED"),
            ("storage", "COMMITTED"),
            ("readiness", "RESEARCH_READY"),
            ("project_invocation", "AUTO_RUN"),
        ):
            with self.subTest(field=field), self.assertRaises(ValueError):
                obj=self.shell("AWAITING_MANUAL_IR_CAPSULE", "CC_IR_CC")
                obj[field] = value
                prepare_manual_review_queue(obj)
        for status, route in (
            ("AWAITING_MANUAL_PI_DELTA", "CC_IR_CC"),
            ("AWAITING_MANUAL_IR_CAPSULE", "CC_PI_CC"),
            ("PI_ONLY_CONDITIONAL_REPORT_ASSEMBLED", "CC_IR_CC"),
            ("M7A_COMPONENT_ASSEMBLED_NOT_END_TO_END_ACCEPTANCE", "CC_PI_CC"),
        ):
            with self.subTest(status=status,route=route), self.assertRaises(ValueError):
                prepare_manual_review_queue(self.shell(status,route))

    def test_lifecycle_review_is_rejected_on_waiting_or_pi_only_route(self):
        for status, route in (
            ("AWAITING_MANUAL_PI_DELTA", "CC_IR_PI_CC"),
            ("PI_ONLY_CONDITIONAL_REPORT_ASSEMBLED", "CC_PI_CC"),
            ("M7A_COMPONENT_ASSEMBLED_NOT_END_TO_END_ACCEPTANCE", "CC_IR_CC"),
        ):
            with self.subTest(route=route, status=status):
                packet = self.shell(
                    status, route,
                    exceptional_lifecycle_review_private={"PRIVATE_SECRET": "RAW_POSITION"},
                )
                with self.assertRaisesRegex(ValueError, "REVIEW_QUEUE_LIFECYCLE_ROUTE_INVALID"):
                    prepare_manual_review_queue(packet)

    def test_session_inputs_unmodified_and_output_bounded(self):
        raw=self.shell("M7A_COMPONENT_ASSEMBLED_NOT_END_TO_END_ACCEPTANCE",
                       integrated_private=dict(
                           status="ASSEMBLED_COMPONENT_ONLY_NOT_END_TO_END_ACCEPTANCE",
                           source_evidence_annex_private={},
                           fact_source_alignment_private={
                               "status":"PRIVATE_FACT_SOURCE_ALIGNMENT_NOT_CERTIFIED",
                               "facts_needing_review":0},
                           valuation_quote_trace_private=None,
                           candidate_comparison_private={},
                           historical_research_comparison_private={}),
                       portfolio_observation_private=None)
        saved=deepcopy(raw)
        out=prepare_manual_review_queue(raw)
        self.assertEqual(raw,saved)
        self.assertLessEqual(out["item_count"],13)
        self.assertEqual(out["item_count"],len(out["items"]))
        self.assertEqual(len(self.codes(out)),len(set(self.codes(out))))

    def cli(self, payload, output="review-queue"):
        stdin=StringIO(json.dumps(payload))
        stdout,stderr=StringIO(),StringIO()
        result=main(["--output",output],
                    instream=stdin,outstream=stdout,errstream=stderr)
        return result,stdout.getvalue(),stderr.getvalue()

    def test_actual_manual_ir_handoff_cli_returns_queue_not_credentials(self):
        request=self.fx.request()
        request["objective"]="PRIVATE_ACCOUNT_TOKEN_SECRET"
        payload={"request":request}
        original=deepcopy(payload)
        code, output, err = self.cli(payload)
        self.assertEqual((code,err),(0,""))
        data=json.loads(output)
        self.assertIn("TRANSFER_IR_CAPSULE",self.codes(data))
        self.assertNotIn("PRIVATE_ACCOUNT_TOKEN_SECRET",output)
        self.assertEqual(payload,original)

    def test_actual_completed_ir_cli_queue_and_default_status_distinct(self):
        payload={"request":self.fx.request(),"ir_capsule":self.fx.ir()}
        code, output, err=self.cli(payload)
        self.assertEqual((code,err),(0,""))
        data=json.loads(output)
        self.assertEqual(data["status"],"MANUAL_REVIEW_QUEUE_NOT_ACCEPTANCE")
        self.assertIn("SOURCE_ANNEX_NOT_PRESENT",self.codes(data))
        code, default_output, err=self.cli(payload,"status")
        self.assertEqual((code,err),(0,""))
        self.assertNotIn("items",json.loads(default_output))
        self.assertEqual(json.loads(default_output)["readiness"],"NOT_EVALUATED")

    def test_missing_pi_real_session_does_not_construct_fake_report(self):
        payload={"request":self.fx.request(portfolio_needed=True),
                 "ir_capsule":self.fx.ir()}
        code, output, err=self.cli(payload)
        self.assertEqual((code,err),(0,""))
        data=json.loads(output)
        self.assertIn("TRANSFER_PI_DELTA",self.codes(data))
        self.assertNotIn("REVIEW_CONDITIONAL_REPORT",self.codes(data))

    def test_unknown_currency_ui_only_is_actionable_via_real_operator_queue(self):
        from ai_native.session_bridge import complete_manual_session
        from tests.test_ai_native_r1_portfolio_snapshots import (
            PrivatePortfolioSnapshotFollowupTests,
        )
        fx = PrivatePortfolioSnapshotFollowupTests()
        fx.setUp()
        old, current = fx.percentage_only("50.05", "50.25")
        session = complete_manual_session(
            fx.request(), pi_delta=fx.fx.pi(),
            observation_inputs=current, prior_portfolio_observation_inputs=old)
        result = prepare_manual_review_queue(session)
        self.assertIn("VERIFY_SOURCE_DISPLAYED_HISTORY", self.codes(result))
        self.assertNotIn("VERIFY_MONETARY_SNAPSHOT_HISTORY", self.codes(result))
        self.assertNotIn("50.25", json.dumps(result))
        self.assertNotIn("ABC:TSX", json.dumps(result))
        self.assertEqual(result["trading_authority"], "NONE")
        self.assertEqual(result["readiness"], "NOT_EVALUATED")

    def test_actual_pi_only_snapshot_queue_selects_source_specific_verification(self):
        from tests.test_ai_native_r1_portfolio_snapshots import (
            PrivatePortfolioSnapshotFollowupTests,
        )
        from ai_native.session_bridge import complete_manual_session
        fx = PrivatePortfolioSnapshotFollowupTests()
        fx.setUp()
        for case, expected in (
            ("monetary", "VERIFY_MONETARY_SNAPSHOT_HISTORY"),
            ("ui", "VERIFY_SOURCE_DISPLAYED_HISTORY"),
            ("incomplete", "RECONCILE_DATED_SNAPSHOT_INPUTS"),
        ):
            with self.subTest(case=case):
                if case == "ui":
                    old, now = fx.percentage_only("50.05", "50.25")
                else:
                    old, now = fx.previous(), fx.current()
                    if case == "incomplete":
                        old["scope_complete"] = False
                result = complete_manual_session(
                    fx.request(), pi_delta=fx.fx.pi(),
                    observation_inputs=now,
                    prior_portfolio_observation_inputs=old)
                original = deepcopy(result)
                queue = prepare_manual_review_queue(result)
                self.assertEqual(result, original)
                self.assertIn(expected, self.codes(queue))
                self.assertEqual(queue["item_count"], len(queue["items"]))
                self.assertLessEqual(queue["item_count"], 14)
                self.assertNotIn("ABC:TSX", json.dumps(queue))
                self.assertNotIn("SCOPE-A", json.dumps(queue))
                self.assertNotIn("50.25", json.dumps(queue))
                self.assertEqual(queue["readiness"], "NOT_EVALUATED")
                self.assertEqual(queue["project_invocation"], "NONE")

    def test_actual_ir_pi_snapshot_queue_preserves_integrated_parity(self):
        from tests.test_ai_native_r1_portfolio_snapshots import (
            PrivatePortfolioSnapshotFollowupTests,
        )
        from ai_native.session_bridge import complete_manual_session
        fx = PrivatePortfolioSnapshotFollowupTests()
        fx.setUp()
        ir = fx.fx.ir()
        old, now = fx.percentage_only()
        session = complete_manual_session(
            fx.request(research_needed=True), ir_capsule=ir,
            pi_delta=fx.fx.pi(forwarded_ir=deepcopy(ir)),
            observation_inputs=now, prior_portfolio_observation_inputs=old)
        queue = prepare_manual_review_queue(session)
        self.assertIn("VERIFY_SOURCE_DISPLAYED_HISTORY", self.codes(queue))
        self.assertNotIn("ABC:TSX", json.dumps(queue))
        forged = deepcopy(session)
        # Independent mutated top-level value; preserve the integrated copy.
        # A plain deepcopy(session) retains aliasing of the two references.
        forged["portfolio_snapshot_comparison_private"] = deepcopy(
            forged["portfolio_snapshot_comparison_private"])
        forged["portfolio_snapshot_comparison_private"]["privacy"] = "PUBLIC"
        with self.assertRaisesRegex(ValueError, "SNAPSHOT_INTEGRATED_PARITY_INVALID"):
            prepare_manual_review_queue(forged)

    def test_actual_cli_snapshot_review_queue_redacts_details(self):
        from tests.test_ai_native_r1_portfolio_snapshots import (
            PrivatePortfolioSnapshotFollowupTests,
        )
        fx = PrivatePortfolioSnapshotFollowupTests()
        fx.setUp()
        old, now = fx.percentage_only()
        source = {
            "request": fx.request(), "pi_delta": fx.fx.pi(),
            "observation_inputs": now,
            "prior_portfolio_observation_inputs": old,
        }
        original = deepcopy(source)
        status, output, error = self.cli(source)
        self.assertEqual((status,error), (0,""))
        self.assertIn("VERIFY_SOURCE_DISPLAYED_HISTORY", self.codes(json.loads(output)))
        self.assertNotIn("ABC:TSX", output)
        self.assertNotIn("SCOPE-A", output)
        self.assertNotIn("PRIOR-CASE", output)
        self.assertEqual(source, original)
        status, standard, error = self.cli(source, "status")
        self.assertEqual((status,error), (0,""))
        self.assertNotIn("VERIFY_SOURCE_DISPLAYED_HISTORY", standard)

    def test_forged_snapshot_state_never_becomes_trusted_review(self):
        from tests.test_ai_native_r1_portfolio_snapshots import (
            PrivatePortfolioSnapshotFollowupTests,
        )
        from ai_native.session_bridge import complete_manual_session
        fx = PrivatePortfolioSnapshotFollowupTests()
        fx.setUp()
        old, now = fx.percentage_only()
        session = complete_manual_session(
            fx.request(), pi_delta=fx.fx.pi(), observation_inputs=now,
            prior_portfolio_observation_inputs=old)
        for field, value, reason in (
            ("privacy", "PUBLIC", "AUTHORITY_OR_OBSERVATION"),
            ("status", "BROKER_VERIFIED", "STATUS_INVALID"),
            ("cash_weight_change_pp", "25.00", "UI_ONLY_AUTHORITY"),
            ("reason_codes", [], "UI_ONLY_AUTHORITY"),
            ("analysis_id", "MISMATCH", "AUTHORITY_OR_OBSERVATION"),
        ):
            with self.subTest(field=field):
                forged = deepcopy(session)
                forged["portfolio_snapshot_comparison_private"][field] = value
                with self.assertRaisesRegex(ValueError, "REVIEW_QUEUE_SNAPSHOT_"):
                    prepare_manual_review_queue(forged)

    def test_pending_six_mode_policy_is_visible_before_specialist_research(self):
        from ai_native.strategy_authority import R1_MODES
        from ai_native.session_bridge import complete_manual_session
        for mode in R1_MODES:
            with self.subTest(mode=mode):
                request = self.fx.request(
                    strategy_id=mode, portfolio_needed=True)
                session = complete_manual_session(request)
                self.assertEqual(session["status"], "AWAITING_MANUAL_IR_CAPSULE")
                self.assertIsNone(session["handoffs_private"]["pi_request_private"])
                queue = prepare_manual_review_queue(session)
                names = self.codes(queue)
                expected = ("CONFIRM_APPROVED_HIGH_CAGR_SCOPE"
                            if mode == "high-cagr"
                            else "RESOLVE_SELECTED_R1_MODE_POLICY")
                self.assertIn(expected, names)
                self.assertIn("TRANSFER_IR_CAPSULE", names)
                self.assertNotIn("TRANSFER_PI_DELTA", names)
                self.assertNotIn("RESOLVE_MODE_QUESTION_EVIDENCE", names)
                self.assertNotIn("VERIFY_MODE_QUESTION_ORIGINALS", names)
                self.assertEqual(queue["readiness"], "NOT_EVALUATED")
                self.assertEqual(queue["project_invocation"], "NONE")
                self.assertEqual(queue["trading_authority"], "NONE")
                self.assertLessEqual(queue["item_count"], 16)
                self.assertNotIn(mode, json.dumps(queue))

    def test_pending_pi_after_ir_preserves_original_and_warns_about_unapproved_mode(self):
        from ai_native.session_bridge import complete_manual_session
        original = self.fx.ir()
        request = self.fx.request(
            strategy_id="balanced", portfolio_needed=True)
        result = complete_manual_session(request, ir_capsule=original)
        self.assertEqual(result["status"], "AWAITING_MANUAL_PI_DELTA")
        self.assertEqual(
            result["handoffs_private"]["pi_request_private"]["FORWARD_UNCHANGED"],
            original)
        queue = prepare_manual_review_queue(result)
        self.assertIn("RESOLVE_SELECTED_R1_MODE_POLICY", self.codes(queue))
        self.assertIn("TRANSFER_PI_DELTA", self.codes(queue))
        self.assertNotIn("TRANSFER_IR_CAPSULE", self.codes(queue))
        self.assertNotIn("RESOLVE_MODE_QUESTION_EVIDENCE", self.codes(queue))
        self.assertNotIn("F1", json.dumps(queue))
        self.assertNotIn("CASE-A", json.dumps(queue))

    def test_pi_only_pending_mode_policy_warning_without_ir_invention(self):
        from ai_native.session_bridge import complete_manual_session
        request = self.fx.request(
            strategy_id="modern-adaptive-browne",
            research_needed=False, portfolio_needed=True)
        pending = complete_manual_session(request)
        self.assertEqual(pending["status"], "AWAITING_MANUAL_PI_DELTA")
        queue = prepare_manual_review_queue(pending)
        self.assertIn("RESOLVE_SELECTED_R1_MODE_POLICY", self.codes(queue))
        self.assertIn("TRANSFER_PI_DELTA", self.codes(queue))
        self.assertNotIn("TRANSFER_IR_CAPSULE", self.codes(queue))
        self.assertNotIn("VERIFY_MODE_QUESTION_ORIGINALS", self.codes(queue))
        self.assertEqual(queue["storage"], "NONE")

    def test_pending_exploratory_never_claims_six_mode_policy(self):
        from ai_native.session_bridge import complete_manual_session
        pending = complete_manual_session(self.fx.request())
        queue = prepare_manual_review_queue(pending)
        self.assertIn("NO_APPROVED_R1_MODE_POLICY", self.codes(queue))
        self.assertNotIn("RESOLVE_SELECTED_R1_MODE_POLICY", self.codes(queue))
        self.assertNotIn("CONFIRM_APPROVED_HIGH_CAGR_SCOPE", self.codes(queue))
        self.assertEqual(queue["readiness"], "NOT_EVALUATED")

    def test_pending_forged_policy_and_unexpected_pi_handoff_fail_closed(self):
        from ai_native.session_bridge import complete_manual_session
        session = complete_manual_session(self.fx.request(
            strategy_id="intelligent-dividend-harvester",
            portfolio_needed=True))
        for mutation in ("policy", "pi_sent_too_early", "strategy"):
            with self.subTest(mutation=mutation):
                fake = deepcopy(session)
                if mutation == "policy":
                    fake["handoffs_private"]["strategy_policy_gate"][
                        "policy_authority"] = "CEO_APPROVED"
                elif mutation == "pi_sent_too_early":
                    fake["handoffs_private"]["pi_request_private"] = {
                        "packet_type": "PI_REQUEST"}
                else:
                    fake["handoffs_private"]["ir_request_private"][
                        "strategy_id"] = "high-cagr"
                with self.assertRaisesRegex(ValueError, "REVIEW_QUEUE_MODE_"):
                    prepare_manual_review_queue(fake)

    def test_cli_pending_policy_review_only_when_privately_requested(self):
        payload = {"request": self.fx.request(
            strategy_id="family-office", portfolio_needed=True)}
        original = deepcopy(payload)
        code, output, error = self.cli(payload)
        self.assertEqual((code, error), (0, ""))
        queue = json.loads(output)
        self.assertIn("RESOLVE_SELECTED_R1_MODE_POLICY", self.codes(queue))
        self.assertIn("TRANSFER_IR_CAPSULE", self.codes(queue))
        self.assertNotIn("family-office", output)
        self.assertNotIn("CASE-A", output)
        self.assertEqual(payload, original)
        code, standard, error = self.cli(payload, "status")
        self.assertEqual((code, error), (0, ""))
        self.assertNotIn("RESOLVE_SELECTED_R1_MODE_POLICY", standard)
        self.assertIn("AWAITING_MANUAL_IR_CAPSULE", standard)

    def test_selected_six_modes_reach_explicit_review_without_policy_upgrade(self):
        from ai_native.strategy_authority import R1_MODES
        from ai_native.session_bridge import complete_manual_session
        for mode in R1_MODES:
            with self.subTest(mode=mode):
                request = self.fx.request(
                    strategy_id=mode, research_needed=False, portfolio_needed=True)
                session = complete_manual_session(request, pi_delta=self.fx.pi())
                result = prepare_manual_review_queue(session)
                code = ("CONFIRM_APPROVED_HIGH_CAGR_SCOPE"
                        if mode == "high-cagr"
                        else "RESOLVE_SELECTED_R1_MODE_POLICY")
                self.assertIn(code, self.codes(result))
                self.assertNotIn("RESEARCH_READY", json.dumps(result))
                self.assertEqual(result["readiness"], "NOT_EVALUATED")
                self.assertEqual(result["trading_authority"], "NONE")
                self.assertLessEqual(result["item_count"], 16)

    def test_ir_pi_mode_questions_drive_actual_evidence_human_step(self):
        from ai_native.session_bridge import complete_manual_session
        request = self.fx.request(
            strategy_id="balanced", portfolio_needed=True)
        ir = self.fx.ir(MODE_RESEARCH_RESPONSES={
            "analysis_id": "CASE-A", "research_as_of": "2026-10-28",
            "strategy_id": "balanced", "answers": [
                {"question_index": 1, "status": "SPECIALIST_REPORTED",
                 "ir_fact_ids": ["F1"]},
                {"question_index": 2, "status": "UNKNOWN",
                 "ir_fact_ids": []},
            ]})
        pi = self.fx.pi(
            forwarded_ir=deepcopy(ir),
            MODE_PORTFOLIO_RESPONSES={
                "analysis_id": "CASE-A", "portfolio_as_of": "2026-10-28",
                "strategy_id": "balanced", "answers": [
                    {"question_index": 1, "status": "UNKNOWN", "p_ids": []},
                    {"question_index": 2, "status": "UNKNOWN", "p_ids": []},
                ],
            })
        session = complete_manual_session(
            request, ir_capsule=ir, pi_delta=pi)
        before = deepcopy(session)
        result = prepare_manual_review_queue(session)
        self.assertEqual(session, before)
        self.assertIn("RESOLVE_MODE_QUESTION_EVIDENCE", self.codes(result))
        self.assertIn("RESOLVE_SELECTED_R1_MODE_POLICY", self.codes(result))
        self.assertEqual(self.codes(result).count("RESOLVE_MODE_QUESTION_EVIDENCE"), 1)
        self.assertNotIn("CASE-A", json.dumps(result))
        self.assertNotIn("F1", json.dumps(result))
        self.assertNotIn("balanced", json.dumps(result))
        self.assertEqual(result["project_invocation"], "NONE")

    def test_forged_handoff_or_mode_trace_does_not_create_authority(self):
        from ai_native.session_bridge import complete_manual_session
        request = self.fx.request(
            strategy_id="modern-adaptive-browne",
            research_needed=False, portfolio_needed=True)
        session = complete_manual_session(request, pi_delta=self.fx.pi())
        for mutation in ("policy", "strategy", "method"):
            with self.subTest(mutation=mutation):
                forged = deepcopy(session)
                x = forged["handoffs_private"]
                if mutation == "policy":
                    x["strategy_policy_gate"]["policy_authority"] = "CEO_APPROVED"
                elif mutation == "strategy":
                    x["pi_request_private"]["strategy_id"] = "high-cagr"
                else:
                    x["pi_request_private"]["r1_strategy_method_load"] = "VERIFIED"
                with self.assertRaisesRegex(ValueError, "REVIEW_QUEUE_MODE_"):
                    prepare_manual_review_queue(forged)

    def test_actual_cli_six_mode_policy_gate_is_redacted_and_not_approved(self):
        payload = {
            "request": self.fx.request(
                strategy_id="intelligent-dividend-harvester",
                research_needed=False, portfolio_needed=True),
            "pi_delta": self.fx.pi(),
        }
        original = deepcopy(payload)
        code, output, error = self.cli(payload)
        self.assertEqual((code, error), (0, ""))
        queue = json.loads(output)
        self.assertIn("RESOLVE_SELECTED_R1_MODE_POLICY", self.codes(queue))
        self.assertNotIn("intelligent-dividend-harvester", output)
        self.assertEqual(queue["source_authentication"], "NOT_PERFORMED")
        self.assertEqual(payload, original)
        code, status, error = self.cli(payload, "status")
        self.assertEqual((code, error), (0, ""))
        self.assertNotIn("RESOLVE_SELECTED_R1_MODE_POLICY", status)

    def test_no_archive_or_automatic_research_even_with_checklist(self):
        payload={"request":self.fx.request()}
        code, output, err=self.cli(payload)
        self.assertEqual((code,err),(0,""))
        data=json.loads(output)
        self.assertEqual(data["storage"],"NONE")
        self.assertEqual(data["project_invocation"],"NONE")
        self.assertEqual(data["trading_authority"],"NONE")


if __name__ == "__main__":
    unittest.main()
