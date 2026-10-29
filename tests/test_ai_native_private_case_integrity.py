"""Focused R1 private-case copy integrity; no files, network or services."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import unittest

from ai_native.private_case_integrity import (
    seal_private_case, verify_private_case_envelope)
from ai_native.research_memory import prepare_research_history


class PrivateCaseIntegrityTests(unittest.TestCase):
    def record(self):
        req = {"ceo_initiated": True, "analysis_id": "CASE-A",
               "as_of": "2026-10-28", "kind": "DECISION",
               "strategy_id": "EXPLORATORY", "method_version": "R1-SYN",
               "subject_id": "SYN-ISSUER", "research_needed": True,
               "portfolio_needed": False,
               "account_context": {"token": "PRIVATE_SYNTHETIC"}}
        ir = {"analysis_id": "CASE-A", "research_as_of": "2026-10-28",
              "facts": [{"id": "F1", "status": "INDICATIVE",
                          "claim": "Private synthetic observation"}]}
        return prepare_research_history(
            req, ir, report_id="REP-A",
            instruction_version="R1-SYN",
            recorded_at="2026-10-28")["private_research_history_proposal"]

    def test_recovered_case_equal_without_mutation(self):
        initial = self.record()
        original = deepcopy(initial)
        envelope = seal_private_case(initial)
        self.assertEqual(verify_private_case_envelope(envelope), original)
        self.assertEqual(initial, original)
        self.assertEqual(len(envelope["private_case_sha256"]), 64)
        self.assertEqual(envelope["storage"], "NONE")
        self.assertEqual(envelope["confidentiality"],
                         "NOT_PROVIDED_BY_CHECKSUM")

    def test_equivalent_json_key_order_does_not_change_checksum(self):
        case = self.record()
        swapped = dict(reversed(list(case.items())))
        self.assertEqual(seal_private_case(case)["private_case_sha256"],
                         seal_private_case(swapped)["private_case_sha256"])

    def test_changed_nested_fact_refused(self):
        envelope = seal_private_case(self.record())
        envelope["private_case"]["original_ir_capsule"]["facts"][0][
            "claim"] = "Tampered"
        with self.assertRaisesRegex(ValueError, "PRIVATE_CASE_SHA256_MISMATCH"):
            verify_private_case_envelope(envelope)

    def test_modified_checksum_or_metadata_refused(self):
        sealed = seal_private_case(self.record())
        changes = (("private_case_sha256", "0" * 64),
                   ("schema_version", "PUBLIC"),
                   ("authenticity", "VERIFIED"),
                   ("storage", "GITHUB"))
        for field, value in changes:
            with self.subTest(field=field):
                mutated = deepcopy(sealed)
                mutated[field] = value
                with self.assertRaises(ValueError):
                    verify_private_case_envelope(mutated)

    def test_extra_field_refused_and_unkeyed_digest_does_not_certify_source(self):
        sealed = seal_private_case(self.record())
        sealed["extra_authority"] = "BROKER_VERIFIED"
        with self.assertRaisesRegex(ValueError, "PRIVATE_CASE_ENVELOPE_INVALID"):
            verify_private_case_envelope(sealed)
        self.assertNotIn("BROKER_VERIFIED", seal_private_case(self.record()).values())

    def test_nonportable_json_or_wrong_record_type_refused(self):
        case = self.record()
        case["original_ir_capsule"]["facts"][0]["claim"] = float("nan")
        with self.assertRaisesRegex(ValueError, "PRIVATE_CASE_RECORD_INVALID"):
            seal_private_case(case)
        case = self.record()
        case["archive_status"] = "COMMITTED"
        with self.assertRaisesRegex(ValueError, "PRIVATE_CASE_RECORD_INVALID"):
            seal_private_case(case)


if __name__ == "__main__":
    unittest.main()
