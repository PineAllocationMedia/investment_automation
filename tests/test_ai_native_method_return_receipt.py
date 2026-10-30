"""F4 synthetic return-receipt checks and real pinned-doc byte parity.

Does not contact ChatGPT Projects, prove live method loading, run market
research, amend Project Settings, handle private holdings or authorize policy.
"""
from copy import deepcopy
import hashlib
from pathlib import Path
import unittest

from ai_native.method_manifest import DOCUMENT_BLOBS, prepare_method_manifest
from ai_native.method_return_receipt import (
    evaluate_returned_method_text, render_returned_method_receipt,
)
from ai_native.strategy_research_brief import prepare_strategy_research_brief
from ai_native.session_bridge import complete_manual_session
from scripts.r1_manual_session_cli import evaluate
from tests.test_ai_native_session_bridge import SessionBridgeTests


ROOT = Path(__file__).resolve().parents[1]


def _case(strategy="balanced", specialist="IR", retrieval="PROJECT_GITHUB_RETRIEVAL_REPORTED"):
    mode_path = prepare_strategy_research_brief(strategy)[
        "design_reference_not_loaded_or_approved"
    ]
    manifest = prepare_method_manifest(specialist, mode_path)
    docs = [
        {"path": item["path"], "content": (ROOT / item["path"]).read_text(encoding="utf-8")}
        for item in manifest["documents"]
    ]
    return {
        "analysis_id": "CASE-A", "analysis_as_of": "2026-10-28",
        "strategy_id": strategy, "specialist": specialist,
        "reported_retrieval": retrieval, "documents": docs,
    }


class MethodReturnReceiptTests(unittest.TestCase):
    def setUp(self):
        self.fx = SessionBridgeTests()

    def request(self, strategy="balanced", **patch):
        return self.fx.request(strategy_id=strategy, **patch)

    def test_all_pins_match_current_repository_bytes(self):
        for path, expected in DOCUMENT_BLOBS.items():
            with self.subTest(path=path):
                data = (ROOT / path).read_bytes()
                blob = hashlib.sha1(
                    b"blob " + str(len(data)).encode("ascii") + b"\x00" + data
                ).hexdigest()
                self.assertEqual(blob, expected)

    def test_ir_and_pi_exact_returned_content_is_not_loading_proof(self):
        for specialist in ("IR", "PI"):
            for mode in ("high-cagr", "balanced", "intelligent-dividend-harvester",
                         "modern-adaptive-browne", "EXPLORATORY"):
                with self.subTest(specialist=specialist, mode=mode):
                    request = self.request(mode)
                    receipt = _case(mode, specialist)
                    copy = deepcopy(receipt)
                    out = evaluate_returned_method_text(
                        request=request, specialist=specialist, receipt=receipt)
                    self.assertEqual(receipt, copy)
                    self.assertEqual(out["content_result"],
                                     "RETURNED_TEXT_MATCHES_PINNED_GIT_BLOBS_ONLY")
                    self.assertEqual(out["actual_project_method_read_or_application"],
                                     "NOT_INDEPENDENTLY_VERIFIED")
                    self.assertEqual(out["actual_project_settings"], "NOT_INSPECTED")
                    self.assertEqual(out["investment_policy_authority"], "NOT_GRANTED")
                    self.assertEqual(out["portfolio_or_trade_authority"], "NONE")
                    self.assertNotIn("content", out)
                    for raw in receipt["documents"]:
                        self.assertNotIn(raw["content"][:200], str(out))

    def test_one_stale_pi_method_blocks_both_f4_and_stale_pins(self):
        request = self.request("balanced")
        receipt = _case("balanced", "PI")
        receipt["documents"][0]["content"] += "\nINJECTED_INVALID_METHOD\n"
        out = evaluate_returned_method_text(
            request=request, specialist="PI", receipt=receipt)
        self.assertEqual(out["content_result"], "STALE_OR_CHANGED_METHOD_TEXT_BLOCKED")
        self.assertEqual(len(out["mismatched_or_missing_reference_paths"]), 1)
        self.assertNotIn("INJECTED_INVALID_METHOD", str(out))
        self.assertIn("STALE_OR_CHANGED_METHOD_TEXT_BLOCKED",
                      render_returned_method_receipt(out))

    def test_missing_and_no_access_can_not_pass(self):
        req = self.request()
        missing = _case()
        missing["documents"].pop()
        out = evaluate_returned_method_text(
            request=req, specialist="IR", receipt=missing)
        self.assertEqual(out["content_result"], "INCOMPLETE_METHOD_TEXT_BLOCKED")
        absent = _case()
        absent["reported_retrieval"] = "NOT_RETRIEVED"
        absent["documents"] = []
        out = evaluate_returned_method_text(
            request=req, specialist="IR", receipt=absent)
        self.assertEqual(out["content_result"], "METHOD_NOT_RETRIEVED_OR_LOADED")
        self.assertEqual(out["actual_project_method_read_or_application"],
                         "NOT_INDEPENDENTLY_VERIFIED")

    def test_path_mode_date_and_specialist_mismatch_fail_closed(self):
        req = self.request()
        original = _case()
        for variant in ("mode", "path", "date", "specialist", "claimed_no_retrieval"):
            receipt = deepcopy(original)
            if variant == "mode":
                receipt["strategy_id"] = "high-cagr"
            elif variant == "path":
                receipt["documents"][0]["path"] = (
                    "docs/ai_native/integrated_build/research/HIGH_CAGR_METHOD_R1.md")
            elif variant == "date":
                receipt["analysis_as_of"] = "2026-10-27"
            elif variant == "specialist":
                receipt["specialist"] = "PI"
            else:
                receipt["reported_retrieval"] = "NOT_RETRIEVED"
            with self.subTest(variant=variant), self.assertRaises(ValueError):
                evaluate_returned_method_text(
                    request=req, specialist="IR", receipt=receipt)

    def test_cc_ir_and_pi_routes_preserve_report_and_private_memory(self):
        req = self.request("balanced")
        ir = self.fx.ir()
        receipts = {"IR": _case("balanced", "IR")}
        before = deepcopy(receipts)
        output = complete_manual_session(
            req, ir_capsule=ir, method_return_receipts=receipts)
        self.assertEqual(receipts, before)
        self.assertEqual(output["status"],
                         "M7A_COMPONENT_ASSEMBLED_NOT_END_TO_END_ACCEPTANCE")
        self.assertEqual(output["method_return_receipts_private"]["IR"]["content_result"],
                         "RETURNED_TEXT_MATCHES_PINNED_GIT_BLOBS_ONLY")
        self.assertIn("F4 — Méthodes IR", output["final_report_private"])
        self.assertIn("F4 — Méthodes IR", output["executive_report_private"])
        self.assertNotIn("F4_SPECIALIST_RETURNED_METHOD",
                         str(output["integrated_private"]["memory_proposal_nonprivate"]))
        self.assertNotIn("METHOD_PATH:", output["final_report_private"])
        self.assertEqual(output["storage"], "NONE")
        self.assertEqual(evaluate({"request": req, "ir_capsule": ir,
                                   "method_return_receipts": receipts})[
            "method_return_receipts_private"]["IR"]["content_result"],
            "RETURNED_TEXT_MATCHES_PINNED_GIT_BLOBS_ONLY")

        pi_req = self.request("balanced", research_needed=False, portfolio_needed=True)
        pi = self.fx.pi()
        pi_out = complete_manual_session(
            pi_req, pi_delta=pi,
            method_return_receipts={"PI": _case("balanced", "PI")})
        self.assertEqual(pi_out["status"], "PI_ONLY_CONDITIONAL_REPORT_ASSEMBLED")
        self.assertIn("F4 — Méthodes PI", pi_out["final_report_private"])
        self.assertIn("F4 — Méthodes PI", pi_out["executive_report_private"])

    def test_missing_real_specialist_packet_rejects_receipt(self):
        for req, receipt in (
            (self.request(), {"IR": _case()}),
            (self.request("balanced", research_needed=False, portfolio_needed=True),
             {"PI": _case("balanced", "PI")}),
            (self.request(), {"PI": _case("balanced", "PI")}),
        ):
            with self.assertRaisesRegex(
                    ValueError, "METHOD_RECEIPT_REQUIRES_ACTUAL_SPECIALIST_PACKET"):
                complete_manual_session(req, method_return_receipts=receipt)

    def test_renderer_refuses_false_loading_authority(self):
        view = evaluate_returned_method_text(
            request=self.request(), specialist="IR", receipt=_case())
        changed = deepcopy(view)
        changed["actual_project_method_read_or_application"] = "LOADED_VERIFIED"
        with self.assertRaisesRegex(ValueError, "METHOD_RECEIPT_REPORT_AUTHORITY_INVALID"):
            render_returned_method_receipt(changed)


if __name__ == "__main__":
    unittest.main()
