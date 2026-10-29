"""Synthetic-only profile-reference route checks. No Blossom browsing or real account data."""
from __future__ import annotations

import copy
from io import StringIO
import json
import unittest

from ai_native.public_portfolio_reference import (
    prepare_public_portfolio_reference, render_public_portfolio_reference,
)
from ai_native.session_bridge import complete_manual_session
from ai_native.manual_review_queue import prepare_manual_review_queue
from scripts.r1_manual_session_cli import main


class PublicReferenceTests(unittest.TestCase):
    def req(self, research=False, portfolio=False):
        return {"ceo_initiated": True, "research_needed": research,
                "portfolio_needed": portfolio, "analysis_id": "SYN-REF-1",
                "as_of": "2026-10-29", "objective": "Synthetic profile study",
                "kind": "DECISION", "strategy_id": "EXPLORATORY"}

    def ir(self):
        return {"analysis_id": "SYN-REF-1", "research_as_of": "2026-10-29",
                "summary": ["No authenticated original source"],
                "facts": [{"id": "F1", "status": "INDICATIVE",
                           "claim": "Synthetic context only"}],
                "limitations": "Original evidence not independently checked",
                "countercase": "Potentially stale profile",
                "decision_line": "No decision or allocation supported",
                "next_action": "Verify original composition evidence"}

    def data(self):
        positions = [
            {"security_id": name, "weight_pct": weight,
             "value": None, "currency": None, "visibility": "VISIBLE"}
            for name, weight in [
                ("SYN-A", "40.1"), ("SYN-B", "30.1"),
                ("SYN-C", "20.1"), ("SYN-D", "10.0")]
        ]
        return {"status": "PUBLIC_REFERENCE_ONLY",
                "analysis_id": "SYN-REF-1", "analysis_as_of": "2026-10-29",
                "observation_as_of": "UNKNOWN", "captured_at": "UNKNOWN",
                "visibility_context": "SIGNED_IN_VISIBILITY_ONLY",
                "visible_scope": "SYN_ACCOUNT_MUST_NOT_LEAK_IN_REPORT",
                "account_ownership": "NOT_ASSUMED_USER",
                "positions_visible": positions,
                "coverage": {"all_rows_visible": True,
                             "other_group_expanded_or_absent": True,
                             "cash_visible": False, "weights_comparable": True,
                             "account_filter_visible": False, "sync_date_visible": False},
                "displayed_weight_sum_pct": "100.30",
                "unknowns": ["SYNTHETIC_UNOBSERVED_ACCOUNT_FILTER"]}

    def test_displayed_sum_not_renormalized_no_private_upgrade(self):
        packet=self.data()
        original=copy.deepcopy(packet)
        x=prepare_public_portfolio_reference(packet,analysis_id="SYN-REF-1",
                                             analysis_as_of="2026-10-29")
        self.assertEqual(packet,original)
        self.assertEqual(x["displayed_weight_sum_pct"],"100.30")
        self.assertEqual(x["top_five_displayed_points"],"100.30")
        self.assertEqual(x["position_count"],4)
        self.assertEqual(x["private_holdings_import"],"NONE")
        self.assertEqual(x["portfolio_room_status"],"NOT_APPLICABLE_PUBLIC_REFERENCE")
        self.assertEqual(x["source_authentication"],"NOT_PERFORMED")
        out=render_public_portfolio_reference(x)
        self.assertIn("100.30% (NOT renormalized)",out)
        self.assertIn("SYN-A",out)
        self.assertNotIn("SYN_ACCOUNT_MUST_NOT_LEAK_IN_REPORT",out)
        self.assertNotIn("SYNTHETIC_UNOBSERVED_ACCOUNT_FILTER",out)

    def test_cc_direct_delivers_reference_report_without_pi(self):
        result=complete_manual_session(self.req(),public_reference_inputs=self.data())
        self.assertEqual(result["status"],"PUBLIC_REFERENCE_DESCRIPTIVE_REPORT_READY")
        self.assertEqual(result["route"],"CC_DIRECT")
        self.assertIn("SYN-A",result["final_report_private"])
        self.assertIsNone(result["portfolio_observation_private"])
        self.assertIsNone(result["gross_contribution_private"])
        self.assertIsNone(result["integrated_private"])
        self.assertEqual(result["project_invocation"],"NONE")
        self.assertEqual(result["storage"],"NONE")
        self.assertEqual(result["readiness"],"NOT_EVALUATED")
        queue=prepare_manual_review_queue(result)
        self.assertIn("VERIFY_REFERENCE_SCOPE",[i["code"] for i in queue["items"]])
        self.assertNotIn("SYN-A",str(queue))
        self.assertNotIn("SYN_ACCOUNT_MUST_NOT_LEAK_IN_REPORT",str(queue))

    def test_ir_handoff_carries_reference_without_inventing_ir(self):
        result=complete_manual_session(self.req(research=True),
                                       public_reference_inputs=self.data())
        self.assertEqual(result["status"],"AWAITING_MANUAL_IR_CAPSULE")
        self.assertIsNone(result["integrated_private"])
        handoff=json.loads(result["handoffs_private"]["copy_ready_private"]["IR_REQUEST"])
        context=handoff["public_reference_context"]
        self.assertEqual(context["status"],"CALLER_REPORTED_REFERENCE_NOT_SOURCE_AUTHENTICATED")
        self.assertEqual(context["positions_visible"][0]["security_id"],"SYN-A")
        self.assertEqual(context["positions_visible"][0]["displayed_weight_pct"],"40.1")
        self.assertNotIn("SYN_ACCOUNT_MUST_NOT_LEAK_IN_REPORT",str(handoff))
        self.assertEqual(result["handoffs_private"]["pi_request_private"],None)
        queue=prepare_manual_review_queue(result)
        self.assertIn("TRANSFER_IR_CAPSULE",[x["code"] for x in queue["items"]])
        self.assertIn("VERIFY_REFERENCE_SCOPE",[x["code"] for x in queue["items"]])

    def test_ir_completed_keeps_reference_separate_from_model_and_memory(self):
        ir=self.ir()
        original=copy.deepcopy(ir)
        result=complete_manual_session(self.req(research=True),
                                       ir_capsule=ir,
                                       public_reference_inputs=self.data())
        self.assertEqual(ir,original)
        self.assertEqual(result["status"],"M7A_COMPONENT_ASSEMBLED_NOT_END_TO_END_ACCEPTANCE")
        self.assertIn("Blossom Portfolio — observed profile reference",result["final_report_private"])
        self.assertIn("SYN-A",result["final_report_private"])
        self.assertEqual(result["integrated_private"]["public_reference_private"]["position_count"],4)
        self.assertEqual(result["integrated_private"]["memory_proposal_nonprivate"]["archive_status"],
                         "PROPOSED_NOT_COMMITTED")
        self.assertNotIn("SYN-A",str(result["integrated_private"]["memory_proposal_nonprivate"]))
        self.assertIsNone(result["portfolio_observation_private"])
        self.assertEqual(result["project_invocation"],"NONE")

    def test_public_cannot_run_pi_portfolio_room_or_private_adapter(self):
        for research in (True,False):
            with self.subTest(research=research),self.assertRaisesRegex(ValueError,
                    "PUBLIC_REFERENCE_ONLY_CC_OR_IR_ROUTE"):
                complete_manual_session(self.req(research=research,portfolio=True),
                                        public_reference_inputs=self.data())
        with self.assertRaisesRegex(ValueError,"PUBLIC_REFERENCE_CANNOT_BECOME_PRIVATE_PORTFOLIO"):
            complete_manual_session(self.req(),
                public_reference_inputs=self.data(), work_blossom_inputs={})

    def test_source_scope_and_provenance_authority(self):
        for key,value,error in (
            ("status","PRIVATE_PORTFOLIO","PUBLIC_REFERENCE_MUST_NOT_CLAIM_PRIVATE_OWNERSHIP"),
            ("account_ownership","CEO_PRIVATE","PUBLIC_REFERENCE_MUST_NOT_CLAIM_PRIVATE_OWNERSHIP"),
            ("analysis_id","OTHER","PUBLIC_REFERENCE_ID_OR_CUTOFF_MISMATCH"),
            ("analysis_as_of","2026-10-28","PUBLIC_REFERENCE_ID_OR_CUTOFF_MISMATCH"),
            ("observation_as_of","2026-10-30","PUBLIC_REFERENCE_AFTER_ANALYSIS_CUTOFF"),
            ("visibility_context","OWNER_AUTHENTICATED","PUBLIC_REFERENCE_VISIBILITY_MODE_UNSUPPORTED"),
        ):
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,error):
                v=self.data();v[key]=value
                prepare_public_portfolio_reference(v,analysis_id="SYN-REF-1",
                                                   analysis_as_of="2026-10-29")

    def test_weights_precision_and_missing_basis_never_guessed(self):
        for amount in ("-1","100.1","1.234","NaN","Infinity"):
            with self.subTest(amount=amount),self.assertRaises(ValueError):
                v=self.data();v["positions_visible"][0]["weight_pct"]=amount
                prepare_public_portfolio_reference(v,analysis_id="SYN-REF-1",
                                                   analysis_as_of="2026-10-29")
        v=self.data()
        v["positions_visible"][0]["weight_pct"]=None
        v["displayed_weight_sum_pct"]=None
        v["coverage"]["weights_comparable"]=False
        out=prepare_public_portfolio_reference(v,analysis_id="SYN-REF-1",
                                               analysis_as_of="2026-10-29")
        self.assertIsNone(out["displayed_weight_sum_pct"])
        self.assertIn("ONE_OR_MORE_WEIGHTS_NOT_VISIBLE",out["missing_or_qualified"])

    def test_claimed_total_mismatch_and_duplicate_security_fail(self):
        v=self.data();v["displayed_weight_sum_pct"]="100.00"
        with self.assertRaisesRegex(ValueError,"PUBLIC_REFERENCE_DISPLAY_SUM_MISMATCH"):
            prepare_public_portfolio_reference(v,analysis_id="SYN-REF-1",
                                               analysis_as_of="2026-10-29")
        v=self.data();v["positions_visible"][1]["security_id"]="SYN-A"
        with self.assertRaisesRegex(ValueError,"PUBLIC_REFERENCE_DUPLICATE_OR_INVALID_SECURITY"):
            prepare_public_portfolio_reference(v,analysis_id="SYN-REF-1",
                                               analysis_as_of="2026-10-29")

    def test_nonboolean_coverage_and_unexpected_fields_fail(self):
        v=self.data();v["coverage"]["all_rows_visible"]="True"
        with self.assertRaisesRegex(ValueError,"PUBLIC_REFERENCE_COVERAGE_FLAGS_REQUIRED"):
            prepare_public_portfolio_reference(v,analysis_id="SYN-REF-1",
                                               analysis_as_of="2026-10-29")
        v=self.data();v["private_account_number"]="PRIVATE_MUST_NOT_FORWARD"
        with self.assertRaisesRegex(ValueError,"PUBLIC_REFERENCE_EXACT_SCHEMA_REQUIRED"):
            prepare_public_portfolio_reference(v,analysis_id="SYN-REF-1",
                                               analysis_as_of="2026-10-29")

    def test_timestamp_must_be_offset_aware_and_match_visible_date(self):
        v=self.data()
        v["observation_as_of"]="2026-10-29"
        v["captured_at"]="2026-10-29T00:21:00-04:00"
        self.assertEqual(prepare_public_portfolio_reference(
            v,analysis_id="SYN-REF-1",analysis_as_of="2026-10-29")["observation_as_of"],
                         "2026-10-29")
        for stamp in ("2026-10-29T00:21:00","2026-10-28T23:21:00-04:00"):
            with self.subTest(stamp=stamp), self.assertRaisesRegex(ValueError,
                            "PUBLIC_REFERENCE_CAPTURE_TIME_INCONSISTENT"):
                v["captured_at"]=stamp
                prepare_public_portfolio_reference(
                    v,analysis_id="SYN-REF-1",analysis_as_of="2026-10-29")

    def test_cli_status_redaction_and_explicit_report(self):
        payload={"request":self.req(),"public_reference_inputs":self.data()}
        stdout,stderr=StringIO(),StringIO()
        result=main(["--output","status"],instream=StringIO(json.dumps(payload)),
                    outstream=stdout,errstream=stderr)
        self.assertEqual(result,0)
        self.assertEqual(stderr.getvalue(),"")
        self.assertNotIn("SYN-A",stdout.getvalue())
        self.assertEqual(json.loads(stdout.getvalue())["status"],
                         "PUBLIC_REFERENCE_DESCRIPTIVE_REPORT_READY")
        stdout,stderr=StringIO(),StringIO()
        code=main(["--output","report"],instream=StringIO(json.dumps(payload)),
                  outstream=stdout,errstream=stderr)
        self.assertEqual(code,0)
        self.assertIn("SYN-A",stdout.getvalue())
        self.assertNotIn("SYN_ACCOUNT_MUST_NOT_LEAK_IN_REPORT",stdout.getvalue())

    def test_future_browser_capture_and_unsafe_case_identity_fail(self):
        v=self.data()
        v["captured_at"]="2026-10-30T00:21:00-04:00"
        with self.assertRaisesRegex(ValueError,"PUBLIC_REFERENCE_CAPTURE_TIME_INCONSISTENT"):
            prepare_public_portfolio_reference(v,analysis_id="SYN-REF-1",
                                               analysis_as_of="2026-10-29")
        v=self.data()
        v["analysis_id"]="SYN-MARKDOWN<script>"
        with self.assertRaisesRegex(ValueError,"PUBLIC_REFERENCE_CASE_ID_UNSAFE"):
            prepare_public_portfolio_reference(v,analysis_id="SYN-MARKDOWN<script>",
                                               analysis_as_of="2026-10-29")

    def test_cli_rejects_untrusted_schema_without_echo(self):
        payload={"request":self.req(),"public_reference_inputs":self.data()}
        payload["public_reference_inputs"]["positions_visible"][0]["security_id"]="SYN|SECRET"
        stdout,stderr=StringIO(),StringIO()
        code=main(["--output","status"],instream=StringIO(json.dumps(payload)),
                  outstream=stdout,errstream=stderr)
        self.assertEqual(code,2)
        self.assertNotIn("SYN|SECRET",stdout.getvalue()+stderr.getvalue())


if __name__=="__main__":
    unittest.main()
