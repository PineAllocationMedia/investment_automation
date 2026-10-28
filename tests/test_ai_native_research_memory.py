import copy
import unittest

from ai_native.research_memory import prepare_research_history


class ResearchHistoryTests(unittest.TestCase):
    def sample(self, **kw):
        req = {"analysis_id": "SYN-01", "as_of": "2026-10-28", "kind": "DECISION",
               "strategy_id": "high-cagr", "method_version": "R1_METHOD"}
        ir = {"analysis_id": "SYN-01", "research_as_of": "2026-10-27",
              "facts": [{"id": "F01", "status": "INDICATIVE", "claim": "DO NOT PUBLISH",
                         "source_url": "https://example.com/private-input"}],
              "countercase": "Private user narrative"}
        args = {"request": req, "ir_capsule": ir, "report_id": "REP-01",
                "instruction_version": "R1", "recorded_at": "2026-10-28"}
        args.update(kw)
        return args

    def test_private_record_retains_original_ir_and_dates(self):
        a = self.sample()
        out = prepare_research_history(**a)
        private = out["private_research_history_proposal"]
        self.assertEqual(private["original_ir_capsule"], a["ir_capsule"])
        self.assertEqual(private["research_as_of"], "2026-10-27")
        self.assertEqual(private["archive_status"], "PROPOSED_NOT_COMMITTED")
        self.assertEqual(private["evidence_status_counts"]["INDICATIVE"], 1)

    def test_public_review_gate_does_not_leak_research_or_ids(self):
        a = self.sample()
        out = prepare_research_history(**a)
        public = str(out["github_review_gate"])
        for forbidden in ("SYN-01", "REP-01", "F01", "DO NOT PUBLISH", "Private user", "https://"):
            self.assertNotIn(forbidden, public)
        self.assertFalse(out["github_review_gate"]["approved_for_publication"])

    def test_not_alias_or_mutate_source(self):
        a = self.sample()
        before = copy.deepcopy(a)
        out = prepare_research_history(**a)
        self.assertEqual(a, before)
        out["private_research_history_proposal"]["original_ir_capsule"]["facts"][0]["claim"] = "changed"
        self.assertEqual(a, before)

    def test_missing_method_faithfully_kept(self):
        a = self.sample()
        a["request"]["method_version"] = "UNKNOWN_NOT_LOADED"
        out = prepare_research_history(**a)
        self.assertEqual(out["private_research_history_proposal"]["method_version"], "UNKNOWN_NOT_LOADED")

    def test_id_mismatch_blocks(self):
        a = self.sample(); a["ir_capsule"]["analysis_id"] = "OTHER"
        with self.assertRaisesRegex(ValueError, "PACKET_INCOMPLETE"):
            prepare_research_history(**a)

    def test_future_research_blocks(self):
        a = self.sample(); a["ir_capsule"]["research_as_of"] = "2026-10-29"
        with self.assertRaisesRegex(ValueError, "TEMPORAL_MISMATCH"):
            prepare_research_history(**a)

    def test_recorded_before_analysis_blocks(self):
        a = self.sample(); a["recorded_at"] = "2026-10-20"
        with self.assertRaisesRegex(ValueError, "TEMPORAL_MISMATCH"):
            prepare_research_history(**a)

    def test_duplicate_fact_ids_block(self):
        a = self.sample(); a["ir_capsule"]["facts"].append({"id": "F01", "status": "MISSING"})
        with self.assertRaisesRegex(ValueError, "DUPLICATE_FACT_ID"):
            prepare_research_history(**a)

    def test_unknown_evidence_status_blocks(self):
        a = self.sample(); a["ir_capsule"]["facts"][0]["status"] = "CERTIFIED"
        with self.assertRaisesRegex(ValueError, "UNSUPPORTED_EVIDENCE_STATUS"):
            prepare_research_history(**a)

    def test_unavailable_prior_is_not_invented(self):
        a = self.sample(parent_report_id="REP-OLDER")
        out = prepare_research_history(**a)
        self.assertEqual(out["private_research_history_proposal"]["baseline_status"],
                         "BASELINE_REFERENCE_NOT_VERIFIED")

    def test_accessible_prior_identity_and_date_only(self):
        a = self.sample(parent_report_id="REP-OLDER", accessible_parent={"report_id": "REP-OLDER", "as_of": "2026-01-01"})
        out = prepare_research_history(**a)
        self.assertEqual(out["private_research_history_proposal"]["baseline_status"],
                         "ACCESSIBLE_PARENT_ID_AND_DATE_CHECKED_ONLY")

    def test_inaccessible_parent_mismatch_blocks(self):
        a = self.sample(parent_report_id="REP-OLDER", accessible_parent={"report_id": "DIFFERENT", "as_of": "2026-01-01"})
        with self.assertRaisesRegex(ValueError, "PARENT_ID_MISMATCH"):
            prepare_research_history(**a)

    def test_future_parent_blocks(self):
        a = self.sample(parent_report_id="REP-OLDER", accessible_parent={"report_id": "REP-OLDER", "as_of": "2026-11-01"})
        with self.assertRaisesRegex(ValueError, "PARENT_IS_NEWER"):
            prepare_research_history(**a)

    def test_self_parent_blocks(self):
        a = self.sample(parent_report_id="REP-01")
        with self.assertRaisesRegex(ValueError, "APPEND_ONLY_VIOLATION"):
            prepare_research_history(**a)

    def test_parent_requires_id(self):
        a = self.sample(accessible_parent={"report_id": "REP-OLDER", "as_of": "2026-01-01"})
        with self.assertRaisesRegex(ValueError, "requires a parent_report_id"):
            prepare_research_history(**a)

    def test_invalid_identifier_cannot_be_an_account_name(self):
        a = self.sample(report_id="Account 123")
        with self.assertRaisesRegex(ValueError, "opaque nonblank"):
            prepare_research_history(**a)


if __name__ == '__main__':
    unittest.main()
