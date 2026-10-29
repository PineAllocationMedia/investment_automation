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

    def test_original_check_cannot_precede_publication_and_remain_usable(self):
        # All dates are before analysis cutoff and the check is before the
        # later observation, but it cannot have verified an unpublished filing.
        observed=self.sample(
            original_checked_at="2026-02-09", published_at="2026-02-10")
        out=self.run_fusion([observed])
        item=out["observations_private"][0]
        self.assertEqual(item["claim_use_status"], "UNAVAILABLE")
        self.assertIn("ORIGINAL_CHECK_BEFORE_PUBLICATION", item["reason_codes"])
        self.assertEqual(out["source_authentication"], "NOT_PERFORMED_BY_CODE")

    def test_completed_source_fact_cannot_be_observed_before_period_end(self):
        # An annual actual 2025 EPS fact is unavailable in October 2025 even
        # if metadata falsely claims that its filing and check were earlier.
        observed=self.sample(
            observed_at="2025-10-01", published_at="2025-08-01",
            original_checked_at="2025-09-01")
        result=self.run_fusion([observed])
        item=result["observations_private"][0]
        self.assertIn("FINANCIAL_PERIOD_END_AFTER_OBSERVATION",
                      item["reason_codes"])
        self.assertEqual(item["claim_use_status"], "UNAVAILABLE")
        self.assertEqual(result["unresolved_count"], 1)

    def test_future_period_estimate_not_mislabeled_completed_source_fact(self):
        # A reported third-party FY forecast may legitimately predate the
        # period end, though it is not a certified source fact.
        estimate=self.sample(
            observed_at="2025-10-01", published_at="2025-08-01",
            original_checked_at=None, source_kind="SECONDARY",
            classification="THIRD_PARTY_ESTIMATE",
            verification_status="INDICATIVE")
        item=self.run_fusion([estimate])["observations_private"][0]
        self.assertNotIn("FINANCIAL_PERIOD_END_AFTER_OBSERVATION",
                         item["reason_codes"])
        self.assertEqual(item["claim_use_status"], "CALLER_REPORTED_ONLY")
        self.assertEqual(item["independent_source_authentication"], "NOT_PERFORMED")

    def test_malformed_https_locator_qualifies_single_source_not_whole_case(self):
        malformed=self.sample(source_locator="https://[invalid-host")
        good=self.sample(observation_id="O2", source_id="S2")
        out=self.run_fusion([malformed, good])
        bad_item=out["observations_private"][0]
        self.assertIn("RECOVERABLE_HTTPS_SOURCE_NOT_SUPPLIED",
                      bad_item["reason_codes"])
        self.assertEqual(bad_item["claim_use_status"], "INCOMPLETE")
        self.assertEqual(out["observations_private"][1]["claim_use_status"],
                         "CALLER_REPORTED_ONLY")

    def test_completed_fact_published_before_period_end_is_unavailable(self):
        # A superficially clean FY actual still cannot have been published
        # in October while its reporting period finishes in December.
        result = self.run_fusion([self.sample(
            published_at="2025-10-01", observed_at="2026-10-28",
            original_checked_at="2026-10-28")])
        item = result["observations_private"][0]
        self.assertIn("COMPLETED_FACT_PUBLISHED_BEFORE_PERIOD_END",
                      item["reason_codes"])
        self.assertEqual(item["claim_use_status"], "UNAVAILABLE")
        self.assertEqual(result["unresolved_count"], 1)
        self.assertEqual(result["pit_authority"], "NOT_ESTABLISHED_BY_DATES_ALONE")

    def test_completed_fact_checked_before_period_end_without_publication(self):
        # Unknown publication does not excuse an impossible check date.
        item = self.run_fusion([self.sample(
            published_at=None, original_checked_at="2025-11-30")])[
                "observations_private"][0]
        self.assertIn("COMPLETED_FACT_CHECKED_BEFORE_PERIOD_END",
                      item["reason_codes"])
        self.assertEqual(item["claim_use_status"], "UNAVAILABLE")

    def test_early_estimate_remains_research_only_not_historical_fact(self):
        item = self.run_fusion([self.sample(
            classification="THIRD_PARTY_ESTIMATE", source_kind="SECONDARY",
            verification_status="INDICATIVE", original_checked_at=None,
            published_at="2025-10-01")])["observations_private"][0]
        self.assertNotIn("COMPLETED_FACT_PUBLISHED_BEFORE_PERIOD_END",
                         item["reason_codes"])
        self.assertNotIn("COMPLETED_FACT_CHECKED_BEFORE_PERIOD_END",
                         item["reason_codes"])
        self.assertEqual(item["claim_use_status"], "CALLER_REPORTED_ONLY")
        self.assertEqual(item["independent_source_authentication"], "NOT_PERFORMED")

    def test_early_publication_isolated_from_independent_valid_observation(self):
        bad = self.sample(published_at="2025-10-01")
        good = self.sample(observation_id="O2", source_id="S2")
        result = self.run_fusion([bad, good])
        self.assertEqual(result["conflict_observation_id_groups"], [])
        self.assertEqual([item["claim_use_status"] for item in
                          result["observations_private"]],
                         ["UNAVAILABLE", "CALLER_REPORTED_ONLY"])
        self.assertEqual(result["unresolved_count"], 1)

    def test_observation_on_period_end_not_rejected_by_new_guard(self):
        row=self.sample(
            observed_at="2025-12-31", published_at="2025-12-31",
            original_checked_at="2025-12-31")
        item=self.run_fusion([row])["observations_private"][0]
        self.assertNotIn("FINANCIAL_PERIOD_END_AFTER_OBSERVATION",
                         item["reason_codes"])
        self.assertNotIn("ORIGINAL_CHECK_BEFORE_PUBLICATION",
                         item["reason_codes"])
        self.assertNotIn("COMPLETED_FACT_PUBLISHED_BEFORE_PERIOD_END",
                         item["reason_codes"])
        self.assertNotIn("COMPLETED_FACT_CHECKED_BEFORE_PERIOD_END",
                         item["reason_codes"])
        self.assertEqual(item["claim_use_status"], "CALLER_REPORTED_ONLY")

if __name__ == '__main__':unittest.main()
