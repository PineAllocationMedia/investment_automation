"""Synthetic and real local-doc parity checks for user-initiated method handoffs.

The CLI never writes files. Only explicit test fixtures create temporary data.
No network, Project calls, credentials, trades or live financial source access.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path
import tempfile
import unittest

from ai_native.method_handoff_bundle import prepare_verified_method_handoff
from ai_native.method_manifest import DOCUMENT_BLOBS, prepare_method_manifest
from ai_native.request_assembly import prepare_manual_handoffs


ROOT = Path(__file__).resolve().parents[1]


def _next(strategy="balanced", *, specialist="IR"):
    request = {
        "ceo_initiated": True, "analysis_id": "SYN-METHOD",
        "as_of": "2026-10-29", "kind": "DECISION",
        "objective": "Read-only synthetic research", "strategy_id": strategy,
        "research_needed": specialist == "IR",
        "portfolio_needed": specialist == "PI",
    }
    prepared = prepare_manual_handoffs(request)
    label = specialist + "_REQUEST"
    return {
        "status": "PRIVATE_MANUAL_CONTINUATION_NOT_SENT",
        "next_handoff": {label: prepared["ir_request_private"] if specialist == "IR"
                         else prepared["pi_request_private"]},
        "resume_input": {"request": deepcopy(request),
                         "specialist_result": None},
        "readiness": "NOT_EVALUATED", "storage": "NONE",
        "project_invocation": "NONE", "trading_authority": "NONE",
    }


class PinnedMethodHandoffTests(unittest.TestCase):
    def test_all_pins_match_current_local_repository_content(self):
        # Catch stale fingerprints after any new contribution/method edit.
        for path, expected in DOCUMENT_BLOBS.items():
            with self.subTest(path=path):
                content = (ROOT / path).read_bytes()
                header = b"blob " + str(len(content)).encode("ascii") + b"\x00"
                self.assertEqual(hashlib.sha1(header + content).hexdigest(), expected)

    def test_ir_and_pi_bundle_carry_actual_pinned_text_no_loading(self):
        for specialist, count in (("IR", 3), ("PI", 4)):
            with self.subTest(specialist=specialist):
                previous = _next(specialist=specialist)
                saved = deepcopy(previous)
                result = prepare_verified_method_handoff(previous)
                self.assertEqual(result["status"],
                                 "PRIVATE_METHOD_HANDOFF_PREPARED_NOT_SENT")
                self.assertEqual(len(result["document_contents_private"]), count)
                self.assertEqual(result["continuation_private"], previous)
                self.assertEqual(previous, saved)
                self.assertTrue(all(x["local_git_blob_check"] ==
                                    "MATCHED_EXPECTED_SHA_ONLY" for x in
                                    result["document_contents_private"]))
                self.assertEqual(result["project_method_load_verification"],
                                 "NOT_PERFORMED")
                self.assertEqual(result["strategy_policy_approval"],
                                 "NOT_GRANTED_BY_ASSEMBLER")
                self.assertEqual(result["project_invocation"], "NONE")

    def test_unapproved_mode_proposal_not_mislabeled_as_policy(self):
        out = prepare_verified_method_handoff(_next("modern-adaptive-browne"))
        design = [x for x in out["document_contents_private"]
                  if x["reference_role"] != "COMMON_CANDIDATE_METHOD"]
        self.assertEqual(len(design), 1)
        self.assertEqual(design[0]["reference_role"],
                         "UNAPPROVED_R1_STRATEGY_POLICY_PROPOSAL")
        high = prepare_verified_method_handoff(_next("high-cagr"))
        self.assertIn("EXISTING_HIGH_CAGR_V2_SCOPE_REFERENCE",
                      [x["reference_role"] for x in
                       high["document_contents_private"]])
        explore = prepare_verified_method_handoff(_next("EXPLORATORY"))
        self.assertEqual(len(explore["document_contents_private"]), 2)

    def test_tampered_manifest_cannot_select_arbitrary_local_file(self):
        previous = _next()
        previous["next_handoff"]["IR_REQUEST"][
            "pinned_method_references_not_loaded_or_approved"]["documents"][0][
                "path"] = "../../PRIVATE_DATA.txt"
        with self.assertRaisesRegex(ValueError, "METHOD_HANDOFF_MANIFEST_MISMATCH"):
            prepare_verified_method_handoff(previous)

    def test_stale_local_document_refused_without_partial_bundle(self):
        path = "docs/ai_native/integrated_build/research/SOURCE_FUSION_R1.md"
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("Synthetic unauthorized modification", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "METHOD_HANDOFF_LOCAL_BLOB_MISMATCH"):
                prepare_verified_method_handoff(
                    _next(), repository_root=Path(tmp))

    def test_missing_local_docs_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "METHOD_HANDOFF_LOCAL_METHOD_UNAVAILABLE"):
                prepare_verified_method_handoff(_next(), repository_root=Path(tmp))



    def test_copy_paste_prompt_exposes_only_specialist_packet_not_cc_resume(self):
        from ai_native.method_handoff_bundle import render_manual_specialist_prompt
        for specialist in ("IR", "PI"):
            with self.subTest(specialist=specialist):
                pending = _next("balanced", specialist=specialist)
                pending["resume_input"]["private_cc_only_secret"] = (
                    "CC_RESUME_SECRET_NOT_FOR_SPECIALIST")
                bundle = prepare_verified_method_handoff(pending)
                before = deepcopy(bundle)
                prompt = render_manual_specialist_prompt(bundle)
                self.assertIn("REQUEST_JSON (" + specialist + "_REQUEST)", prompt)
                self.assertIn("CONTENT_BEGIN", prompt)
                self.assertIn("CONTENT_END", prompt)
                self.assertIn("UNAPPROVED_R1_STRATEGY_POLICY_PROPOSAL", prompt)
                self.assertNotIn("CC_RESUME_SECRET_NOT_FOR_SPECIALIST", prompt)
                self.assertNotIn('"resume_input"', prompt)
                self.assertNotIn('"specialist_result"', prompt)
                self.assertEqual(bundle, before)

    def test_copy_paste_prompt_never_alters_original_forwarded_ir(self):
        from ai_native.method_handoff_bundle import render_manual_specialist_prompt
        pending = _next("high-cagr", specialist="PI")
        forwarded = {"analysis_id": "SYN-METHOD", "facts": [
            {"id": "F1", "claim": "Original synthetic evidence"}]}
        pending["next_handoff"]["PI_REQUEST"]["FORWARD_UNCHANGED"] = (
            deepcopy(forwarded))
        result = prepare_verified_method_handoff(pending)
        prompt = render_manual_specialist_prompt(result)
        self.assertIn('"FORWARD_UNCHANGED"', prompt)
        self.assertIn('"Original synthetic evidence"', prompt)
        self.assertIn("unchanged in every field", prompt)
        self.assertIn("EXISTING_HIGH_CAGR_V2_SCOPE_REFERENCE", prompt)
        self.assertEqual(
            result["continuation_private"]["next_handoff"]["PI_REQUEST"]
            ["FORWARD_UNCHANGED"], forwarded)

    def test_prompt_does_not_claim_ir_exists_on_pi_only_route(self):
        from ai_native.method_handoff_bundle import render_manual_specialist_prompt
        output = render_manual_specialist_prompt(
            prepare_verified_method_handoff(_next("EXPLORATORY", specialist="PI")))
        self.assertIn("Do not invent a prior IR_CAPSULE", output)
        self.assertNotIn('"FORWARD_UNCHANGED"; the latter', output)
        self.assertNotIn("UNAPPROVED_R1_STRATEGY_POLICY_PROPOSAL", output)

    def test_prompt_rejects_modified_method_content_or_fake_authority(self):
        from ai_native.method_handoff_bundle import render_manual_specialist_prompt
        original = prepare_verified_method_handoff(_next("balanced"))
        with self.assertRaisesRegex(ValueError, "DOCUMENT_BLOB_MISMATCH"):
            tampered = deepcopy(original)
            tampered["document_contents_private"][0]["content"] += (
                "\nFAKE FINANCIAL POLICY")
            render_manual_specialist_prompt(tampered)
        forged = deepcopy(original)
        forged["project_method_load_verification"] = "PROVED_LOADED"
        with self.assertRaisesRegex(ValueError, "SPECIALIST_PROMPT_BUNDLE_INVALID"):
            render_manual_specialist_prompt(forged)

if __name__ == "__main__":
    unittest.main()
