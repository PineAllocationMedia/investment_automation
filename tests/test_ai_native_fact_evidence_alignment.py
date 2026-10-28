import copy
import unittest

from ai_native.fact_evidence_alignment import align_ir_facts_to_sources


class AlignmentTests(unittest.TestCase):
    def data(self, *, ir_status="VERIFIED", use="CALLER_REPORTED_ONLY"):
        facts = [{"id": "F1", "status": ir_status, "claim": "Synthetic figure"}]
        annex = {"status": "PRIVATE_SOURCE_ANNEX_PREPARED_NOT_CERTIFIED",
                 "analysis_id": "SYN-1", "analysis_as_of": "2026-10-28",
                 "source_authentication": "NOT_PERFORMED_BY_CODE",
                 "observations_private": [{"fact_id": "F1", "observation_id": "O1",
                                           "claim_use_status": use}]}
        return dict(analysis_id="SYN-1", analysis_as_of="2026-10-28", ir_facts=facts,
                    source_annex=annex)

    def test_good_reported_evidence_never_proves_verified(self):
        d = align_ir_facts_to_sources(**self.data())
        self.assertEqual(d["facts_needing_review"], 0)
        self.assertEqual(d["evidence_upgrade"], "NONE")
        self.assertEqual(d["decision_grade_status"], "NOT_ESTABLISHED")
        self.assertEqual(d["facts_private"][0]["alignment"], "CALLER_REPORTED_STRUCTURALLY_ALIGNED_ONLY")

    def test_missing_fact_source_flags_verified_label(self):
        d = self.data(); d["source_annex"]["observations_private"] = []
        out = align_ir_facts_to_sources(**d)
        self.assertEqual(out["facts_needing_review"], 1)
        self.assertIn("IR_VERIFIED_LABEL_NOT_SUPPORTED_BY_SUPPLIED_ANNEX", out["facts_private"][0]["review_flags"])

    def test_indicative_no_source_stays_unverified(self):
        d = self.data(ir_status="INDICATIVE"); d["source_annex"]["observations_private"] = []
        out = align_ir_facts_to_sources(**d)
        self.assertEqual(out["facts_private"][0]["ir_reported_status"], "INDICATIVE")
        self.assertEqual(out["facts_needing_review"], 1)
        self.assertNotIn("IR_VERIFIED_LABEL_NOT_SUPPORTED_BY_SUPPLIED_ANNEX", out["facts_private"][0]["review_flags"])

    def test_one_unavailable_overrides_other_positive_observation(self):
        d = self.data()
        d["source_annex"]["observations_private"].append(dict(fact_id="F1", observation_id="O2", claim_use_status="UNAVAILABLE"))
        flags = align_ir_facts_to_sources(**d)["facts_private"][0]["review_flags"]
        self.assertIn("SOURCE_UNAVAILABLE", flags)
        self.assertIn("IR_VERIFIED_LABEL_NOT_SUPPORTED_BY_SUPPLIED_ANNEX", flags)

    def test_conflicted_observation_blocks_clean_alignment(self):
        out = align_ir_facts_to_sources(**self.data(use="CONFLICTED"))
        self.assertIn("SOURCE_CONFLICTED", out["facts_private"][0]["review_flags"])

    def test_incomplete_observation_blocks_clean_alignment(self):
        out = align_ir_facts_to_sources(**self.data(use="INCOMPLETE"))
        self.assertIn("SOURCE_INCOMPLETE", out["facts_private"][0]["review_flags"])

    def test_missing_ir_status_remains_unresolved_even_positive_source(self):
        out = align_ir_facts_to_sources(**self.data(ir_status="MISSING"))
        self.assertIn("IR_FACT_REPORTED_UNRESOLVED", out["facts_private"][0]["review_flags"])

    def test_mismatched_analysis_blocked(self):
        d = self.data(); d["source_annex"]["analysis_id"] = "WRONG"
        with self.assertRaisesRegex(ValueError,"ANNEX_ID_DATE_OR_AUTHORITY_MISMATCH"):
            align_ir_facts_to_sources(**d)

    def test_mismatched_date_blocked(self):
        d = self.data(); d["source_annex"]["analysis_as_of"] = "2026-10-27"
        with self.assertRaisesRegex(ValueError,"ANNEX_ID_DATE_OR_AUTHORITY_MISMATCH"):
            align_ir_facts_to_sources(**d)

    def test_fake_source_authentication_blocked(self):
        d = self.data(); d["source_annex"]["source_authentication"] = "CERTIFIED"
        with self.assertRaisesRegex(ValueError,"ANNEX_ID_DATE_OR_AUTHORITY_MISMATCH"):
            align_ir_facts_to_sources(**d)

    def test_unknown_ir_fact_id_blocked(self):
        d = self.data(); d["source_annex"]["observations_private"][0]["fact_id"] = "F2"
        with self.assertRaisesRegex(ValueError,"SOURCE_ANNEX_UNKNOWN_IR_FACT_ID"):
            align_ir_facts_to_sources(**d)

    def test_duplicate_ir_fact_id_blocked(self):
        d = self.data(); d["ir_facts"].append(dict(id="F1",status="VERIFIED"))
        with self.assertRaisesRegex(ValueError,"DUPLICATE_IR_FACT_ID"):
            align_ir_facts_to_sources(**d)

    def test_duplicate_observation_id_blocked(self):
        d = self.data(); d["source_annex"]["observations_private"].append(dict(fact_id="F1",observation_id="O1",claim_use_status="CALLER_REPORTED_ONLY"))
        with self.assertRaisesRegex(ValueError,"DUPLICATE_OR_INVALID_OBSERVATION_ID"):
            align_ir_facts_to_sources(**d)

    def test_invalid_status_blocks(self):
        d = self.data(ir_status="CERTIFIED")
        with self.assertRaisesRegex(ValueError,"INVALID_IR_FACT_STATUS"):
            align_ir_facts_to_sources(**d)

    def test_empty_ir_and_annex_are_transparent(self):
        d = self.data(); d["ir_facts"]=[]; d["source_annex"]["observations_private"]=[]
        out = align_ir_facts_to_sources(**d)
        self.assertEqual((out["fact_count"],out["source_observation_count"],out["facts_needing_review"]),(0,0,0))

    def test_no_mutation(self):
        d = self.data(); before=copy.deepcopy(d)
        align_ir_facts_to_sources(**d)
        self.assertEqual(d,before)

    def test_no_private_claim_or_source_url_copied_to_flags(self):
        d=self.data()
        d["ir_facts"][0]["claim"]="PRIVATE ACCOUNT DATA"
        d["source_annex"]["observations_private"][0]["source_locator"]="https://example.invalid/private"
        out=align_ir_facts_to_sources(**d)
        self.assertNotIn("PRIVATE ACCOUNT DATA",str(out))
        self.assertNotIn("https://",str(out))


if __name__ == "__main__":
    unittest.main()
