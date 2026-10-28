import copy
import unittest
from ai_native.source_fusion import assemble_source_fusion

class SourceFusionTests(unittest.TestCase):
    def sample(self, **changes):
        row=dict(observation_id="O1", fact_id="F1",source_id="S1",economic_issuer="GEN",
                 instrument="GEN:NYSE",metric="EPS",period_start="2025-01-01",period_end="2025-12-31",
                 currency="USD",unit="PER_SHARE",definition_basis="US_GAAP",consolidation="GROUP",
                 value="0.36",observed_at="2026-10-28",published_at="2026-02-10",
                 original_checked_at="2026-10-28",source_kind="ISSUER_OR_REGULATOR",
                 classification="SOURCE_FACT",source_locator="https://example.org/report",
                 rights_status="PERMITTED",verification_status="VERIFIED")
        row.update(changes)
        return row
    def run_fusion(self, rows=None, asof="2026-10-28"):
        return assemble_source_fusion(analysis_id="A1",analysis_as_of=asof,observations=rows if rows is not None else [self.sample()])
    def test_reported_verified_is_not_independently_certified(self):
        o=self.run_fusion()
        x=o["observations_private"][0]
        self.assertEqual(x["claim_use_status"],"CALLER_REPORTED_ONLY")
        self.assertEqual(x["independent_source_authentication"],"NOT_PERFORMED")
        self.assertEqual(o["pit_authority"],"NOT_ESTABLISHED_BY_DATES_ALONE")
    def test_conflicting_same_basis_values_preserved(self):
        r=self.sample(observation_id="O2",source_id="S2",value="0.71")
        o=self.run_fusion([self.sample(),r])
        self.assertEqual(o["conflict_observation_id_groups"],[["O1","O2"]])
        self.assertTrue(all(x["claim_use_status"]=="CONFLICTED" for x in o["observations_private"]))
    def test_equivalent_decimals_not_conflicted(self):
        o=self.run_fusion([self.sample(value="1"),self.sample(observation_id="O2",value="1.00")])
        self.assertEqual(o["conflict_observation_id_groups"],[])
    def test_adjusted_vs_gaap_not_silently_mixed(self):
        r=self.sample(observation_id="O2",definition_basis="ISSUER_ADJUSTED",value="0.71")
        o=self.run_fusion([self.sample(),r])
        self.assertEqual(o["conflict_observation_id_groups"],[])
        self.assertEqual(o["noncomparable_basis_groups"],[["O1","O2"]])
    def test_distinct_periods_not_conflicted(self):
        r=self.sample(observation_id="O2",period_start="2024-01-01",period_end="2024-12-31",value="0.71")
        self.assertEqual(self.run_fusion([self.sample(),r])["conflict_observation_id_groups"],[])
    def test_missing_value_keeps_fact(self):
        o=self.run_fusion([self.sample(value=None,verification_status="MISSING")])
        self.assertEqual(o["observations_private"][0]["claim_use_status"],"INCOMPLETE")
        self.assertEqual(o["observation_count"],1)
    def test_secondary_verified_claim_is_qualified(self):
        o=self.run_fusion([self.sample(source_kind="SECONDARY")])
        self.assertIn("VERIFIED_REQUIRES_REPORTED_ORIGINAL_CHECK",o["observations_private"][0]["reason_codes"])
    def test_no_original_check_qualifies_verified(self):
        o=self.run_fusion([self.sample(original_checked_at=None)])
        self.assertEqual(o["observations_private"][0]["claim_use_status"],"INCOMPLETE")
    def test_future_observation_and_publication_unavailable(self):
        o=self.run_fusion([self.sample(observed_at="2026-11-01",published_at="2026-11-02")])
        self.assertEqual(o["observations_private"][0]["claim_use_status"],"UNAVAILABLE")
    def test_unknown_publication_is_not_pit_proof(self):
        o=self.run_fusion([self.sample(published_at=None)])
        self.assertIn("PUBLICATION_DATE_NOT_ESTABLISHED",o["observations_private"][0]["reason_codes"])
    def test_restricted_source_cannot_be_used(self):
        o=self.run_fusion([self.sample(rights_status="RESTRICTED")])
        self.assertEqual(o["observations_private"][0]["claim_use_status"],"UNAVAILABLE")
    def test_uncertain_rights_cannot_be_implicitly_granted(self):
        o=self.run_fusion([self.sample(rights_status="UNCERTAIN")])
        self.assertEqual(o["observations_private"][0]["claim_use_status"],"INCOMPLETE")
    def test_invalid_money_is_rejected(self):
        for bad in ("NaN","Infinity","bad",1.4,"",True):
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                self.run_fusion([self.sample(value=bad)])
    def test_reversed_period_rejected(self):
        with self.assertRaisesRegex(ValueError,"REVERSED"):
            self.run_fusion([self.sample(period_start="2026-01-01",period_end="2025-12-31")])
    def test_duplicate_observation_id_rejected(self):
        with self.assertRaisesRegex(ValueError,"DUPLICATE"):
            self.run_fusion([self.sample(),self.sample()])
    def test_incomplete_source_locator_is_not_validated(self):
        o=self.run_fusion([self.sample(source_locator="http://bad.example.org/")])
        self.assertIn("RECOVERABLE_HTTPS_SOURCE_NOT_SUPPLIED",o["observations_private"][0]["reason_codes"])
    def test_user_scenario_is_never_source_fact(self):
        o=self.run_fusion([self.sample(source_kind="ASSUMPTION",classification="PAM_ASSUMPTION",source_locator=None,verification_status="INDICATIVE")])
        self.assertEqual(o["observations_private"][0]["source_kind"],"ASSUMPTION")
    def test_source_chronology_inconsistent_is_unavailable(self):
        o=self.run_fusion([self.sample(published_at="2026-11-02",observed_at="2026-10-28")],asof="2026-11-10")
        self.assertIn("PUBLICATION_AFTER_OBSERVATION",o["observations_private"][0]["reason_codes"])
        self.assertEqual(o["observations_private"][0]["claim_use_status"],"UNAVAILABLE")
    def test_original_check_after_observation_is_unavailable(self):
        o=self.run_fusion([self.sample(original_checked_at="2026-10-29")],asof="2026-11-10")
        self.assertIn("CHECK_AFTER_OBSERVATION",o["observations_private"][0]["reason_codes"])
    def test_preserves_inputs_without_extra_content(self):
        row=self.sample(raw_filings="Sensitive proprietary quote")
        before=copy.deepcopy(row)
        o=self.run_fusion([row])
        self.assertEqual(row,before)
        self.assertNotIn("Sensitive proprietary quote",str(o))
    def test_empty_list_is_transparent(self):
        o=self.run_fusion([])
        self.assertEqual((o["observation_count"],o["unresolved_count"]),(0,0))
        self.assertEqual(o["source_authentication"],"NOT_PERFORMED_BY_CODE")

if __name__ == '__main__':unittest.main()
