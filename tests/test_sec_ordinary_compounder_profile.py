from dataclasses import replace
from decimal import Decimal
import inspect
import unittest

from economic_facts import sec_ordinary_compounder_profile as profile
from tests import test_sec_quote_eps_basis_bridge as bridge_tests
from tests.sec_current_security_eps_qualification_fixtures import (
    VALUES,
    companyfacts_rows,
    source_rows,
)
from tests.sec_five_year_eps_presentation_fixtures import five_year_table
from tests.sec_property4_temporal_fixtures import CIK
from tests.sec_submissions_fixtures import root as submissions_root


class OrdinaryCompounderProfileTests(unittest.TestCase):
    def setUp(self):
        self.bridge_fixture = bridge_tests.SecQuoteEPSBasisBridgeTests(methodName="runTest")
        self.bridge_fixture.setUp()
        self.addCleanup(self.bridge_fixture.doCleanups)

    def comparability_context(
        self,
        *,
        sic=3571,
        description="Electronic Computers",
        filings=None,
        current=None,
        metadata_changes=None,
    ):
        metadata_changes = {} if metadata_changes is None else metadata_changes
        parent = self.bridge_fixture.comparability.submissions_archive._capture_live(
            submissions_root(
                source_rows(), cik=CIK, sic=sic, sicDescription=description,
                **metadata_changes),
            cik=CIK,
            captured_at="2026-02-25T12:00:00Z",
        )
        comparability_request = self.bridge_fixture.comparability.build_request(
            parent=parent, filings=filings, current=current)
        pr5c = self.bridge_fixture.comparability.qualify_request(comparability_request)
        return comparability_request, pr5c

    def qualify(
        self,
        *,
        sic=3571,
        description="Electronic Computers",
        filings=None,
        current=None,
        metadata_changes=None,
        expected_comparability_semantic_id=None,
        expected_comparability_evidence_id=None,
    ):
        comparability_request, pr5c = self.comparability_context(
            sic=sic,
            description=description,
            filings=filings,
            current=current,
            metadata_changes=metadata_changes,
        )
        request = profile.SecOrdinaryCompounderProfileRequest(
            comparability_request,
            (
                pr5c.semantic_id
                if expected_comparability_semantic_id is None
                else expected_comparability_semantic_id
            ),
            (
                pr5c.evidence_id
                if expected_comparability_evidence_id is None
                else expected_comparability_evidence_id
            ),
        )
        return profile.qualify_sec_ordinary_compounder_profile(
            self.bridge_fixture.comparability.current_archive,
            self.bridge_fixture.comparability.submissions_archive,
            self.bridge_fixture.comparability.filing_archive,
            self.bridge_fixture.comparability.sec_archive,
            self.bridge_fixture.comparability.nasdaq_archive,
            request)

    def test_normal_operating_sic_establishes_methodology_profile(self):
        result = self.qualify()
        self.assertEqual(
            result.contract_version,
            "2026-10-07-sec-ordinary-compounder-method-profile-v2",
        )
        self.assertIs(result.status,
                      profile.OrdinaryCompounderProfileStatus.ORDINARY_COMPOUNDER_PROFILE_ESTABLISHED)
        self.assertEqual(result.profile, "ORDINARY_COMPOUNDER")
        self.assertEqual(len(result.decisions), len(profile.UnsupportedStructure))
        self.assertTrue(all(item.decision is profile.ProfileDecisionValue.EXCLUDED
                            for item in result.decisions))
        self.assertIn("NO_QUALITY_SCORE", result.limitations)
        self.assertEqual(
            result.expected_comparability_semantic_id,
            result.upstream_comparability.semantic_id,
        )
        self.assertEqual(
            result.expected_comparability_evidence_id,
            result.upstream_comparability.evidence_id,
        )
        self.assertNotIn(
            profile.ProfileReason.REPLAY_IDENTITY_MISMATCH,
            result.reasons,
        )

    def test_foreign_location_metadata_does_not_change_sic_structure_decisions(self):
        cases = ((3571, "Electronic Computers"),
                 (6021, "National Commercial Banks"),
                 (3571, "Real Estate Investment Trusts"))
        for sic, description in cases:
            baseline = self.qualify(sic=sic, description=description)
            for branch in ("mailing", "business"):
                for value in (None, "foreign", 7, -(2**63 - 1)):
                    with self.subTest(sic=sic, description=description, branch=branch, value=value):
                        result = self.qualify(
                            sic=sic, description=description,
                            metadata_changes={"addresses": {branch: {"isForeignLocation": value}}})
                        self.assertEqual(result.sic, baseline.sic)
                        self.assertEqual(result.sic_description, baseline.sic_description)
                        self.assertEqual(result.status, baseline.status)
                        self.assertEqual(result.reasons, baseline.reasons)
                        self.assertEqual(
                            [(item.profile, item.decision, item.reason) for item in result.decisions],
                            [(item.profile, item.decision, item.reason) for item in baseline.decisions])
                        self.assertEqual(result.contract_version, baseline.contract_version)
                        self.assertEqual(result.qualifier_version, baseline.qualifier_version)

    def test_replay_mismatch_is_authenticated_for_each_expected_identity(self):
        cases = (
            ("0" * 64, None),
            (None, "1" * 64),
            ("0" * 64, "1" * 64),
        )
        for expected_semantic, expected_evidence in cases:
            result = self.qualify(
                expected_comparability_semantic_id=expected_semantic,
                expected_comparability_evidence_id=expected_evidence,
            )
            with self.subTest(
                expected_semantic=expected_semantic,
                expected_evidence=expected_evidence,
            ):
                self.assertIs(
                    result.status,
                    profile.OrdinaryCompounderProfileStatus.SOURCE_CONFLICT,
                )
                self.assertEqual(
                    result.reasons,
                    (profile.ProfileReason.REPLAY_IDENTITY_MISMATCH,),
                )
                self.assertEqual(
                    result.expected_comparability_semantic_id,
                    (
                        result.upstream_comparability.semantic_id
                        if expected_semantic is None
                        else expected_semantic
                    ),
                )
                self.assertEqual(
                    result.expected_comparability_evidence_id,
                    (
                        result.upstream_comparability.evidence_id
                        if expected_evidence is None
                        else expected_evidence
                    ),
                )

    def test_expected_replay_identity_construction_is_exact_and_closed(self):
        comparability_request, pr5c = self.comparability_context()
        invalid_values = (None, 0, "A" * 64, "0" * 63)
        for field in (
            "expected_comparability_semantic_id",
            "expected_comparability_evidence_id",
        ):
            for invalid in invalid_values:
                values = {
                    "expected_comparability_semantic_id": pr5c.semantic_id,
                    "expected_comparability_evidence_id": pr5c.evidence_id,
                }
                values[field] = invalid
                with self.subTest(field=field, invalid=invalid), self.assertRaises(
                    profile.OrdinaryCompounderProfileError
                ):
                    profile.SecOrdinaryCompounderProfileRequest(
                        comparability_request,
                        values["expected_comparability_semantic_id"],
                        values["expected_comparability_evidence_id"],
                    )

        canonical = self.qualify()
        with self.assertRaises(profile.OrdinaryCompounderProfileError):
            replace(canonical, expected_comparability_semantic_id="A" * 64)

    def test_expected_replay_provenance_is_evidence_not_direct_semantics(self):
        no_mismatch = self.qualify()
        first = self.qualify(expected_comparability_semantic_id="0" * 64)
        second = self.qualify(expected_comparability_semantic_id="1" * 64)
        self.assertEqual(first.upstream_comparability, second.upstream_comparability)
        self.assertEqual(first.status, second.status)
        self.assertEqual(first.reasons, second.reasons)
        self.assertEqual(first.semantic_id, second.semantic_id)
        self.assertNotEqual(first.evidence_id, second.evidence_id)
        self.assertNotEqual(no_mismatch.semantic_id, first.semantic_id)

    def test_reviewed_special_structure_sic_families_are_unsupported(self):
        cases = (
            (6021, "National Commercial Banks", profile.UnsupportedStructure.BANK),
            (6331, "Fire Marine and Casualty Insurance", profile.UnsupportedStructure.INSURER),
            (6798, "Real Estate Investment Trusts", profile.UnsupportedStructure.REIT),
            (6282, "Investment Advice", profile.UnsupportedStructure.ASSET_MANAGER),
            (1040, "Gold and Silver Ores", profile.UnsupportedStructure.RESOURCES_MINING),
            (1311, "Crude Petroleum and Natural Gas", profile.UnsupportedStructure.ENERGY_CYCLICAL),
            (4612, "Crude Petroleum Pipelines", profile.UnsupportedStructure.PIPELINE),
            (4911, "Electric Services", profile.UnsupportedStructure.UTILITY_ACCOUNTING),
            (6719, "Offices of Holding Companies", profile.UnsupportedStructure.INVESTMENT_HOLDING),
        )
        for sic, description, expected_structure in cases:
            with self.subTest(sic=sic):
                result = self.qualify(sic=sic, description=description)
                self.assertIs(result.status,
                              profile.OrdinaryCompounderProfileStatus.PROFILE_UNSUPPORTED)
                decision = next(item for item in result.decisions
                                if item.profile is expected_structure)
                self.assertIs(decision.decision, profile.ProfileDecisionValue.NOT_EXCLUDED)

    def test_distinct_normal_operating_sic_families_are_supported(self):
        cases = (
            (2834, "Pharmaceutical Preparations"),
            (3571, "Electronic Computers"),
            (3711, "Motor Vehicles and Passenger Car Bodies"),
            (5812, "Eating Places"),
            (7372, "Prepackaged Software"),
            (8062, "General Medical and Surgical Hospitals"),
        )
        for sic, description in cases:
            with self.subTest(sic=sic):
                self.assertIs(
                    self.qualify(sic=sic, description=description).status,
                    profile.OrdinaryCompounderProfileStatus.
                    ORDINARY_COMPOUNDER_PROFILE_ESTABLISHED,
                )

    def test_loss_reporting_transition_mixed_and_missing_sic_fail_closed(self):
        rows = companyfacts_rows()
        for row in rows:
            if row["fy"] == 2024:
                row["val"] = -1
        values = dict(VALUES)
        values[2024] = Decimal("-1")
        negative = self.qualify(
            current=self.bridge_fixture.comparability.current(rows=rows),
            filings=self.bridge_fixture.comparability.filings(
                table=five_year_table(values=values),
                value_overrides={2024: Decimal("-1")}),
        )
        self.assertIs(negative.status,
                      profile.OrdinaryCompounderProfileStatus.PROFILE_UNSUPPORTED)
        loss = next(item for item in negative.decisions
                    if item.profile is profile.UnsupportedStructure.LOSS_MAKING)
        self.assertIs(loss.decision, profile.ProfileDecisionValue.NOT_EXCLUDED)

        transition = self.qualify(
            filings=self.bridge_fixture.comparability.filings(claims=(
                "Old Fiction was the predecessor, and New Fiction became the successor.",
            )))
        self.assertIs(transition.status,
                      profile.OrdinaryCompounderProfileStatus.PROFILE_UNAVAILABLE)
        self.assertIn(profile.ProfileReason.REPORTING_SUBJECT_STABILITY_NOT_ESTABLISHED,
                      transition.reasons)

        mixed = self.qualify(
            filings=self.bridge_fixture.comparability.filings(claims=(
                "These are combined financial statements.",
            )))
        self.assertIs(mixed.status,
                      profile.OrdinaryCompounderProfileStatus.PROFILE_UNAVAILABLE)
        self.assertIn(profile.ProfileReason.MIXED_STRUCTURE_UNRESOLVED, mixed.reasons)
        mixed_decision = next(item for item in mixed.decisions
                              if item.profile is profile.UnsupportedStructure.MIXED_CONGLOMERATE)
        self.assertIs(mixed_decision.decision, profile.ProfileDecisionValue.UNRESOLVED)

        missing = self.qualify(sic=None, description=None)
        self.assertIs(missing.status,
                      profile.OrdinaryCompounderProfileStatus.PROFILE_UNAVAILABLE)
        self.assertIn(profile.ProfileReason.SIC_MISSING_OR_INVALID, missing.reasons)

    def test_name_and_ticker_metadata_do_not_determine_profile_and_v1_is_unused(self):
        baseline = self.qualify()
        renamed = self.qualify(metadata_changes={
            "name": "Renamed Fictional Operating Issuer",
            "tickers": ["ZZZZ"],
        })
        self.assertIs(baseline.status,
                      profile.OrdinaryCompounderProfileStatus.
                      ORDINARY_COMPOUNDER_PROFILE_ESTABLISHED)
        self.assertIs(renamed.status,
                      profile.OrdinaryCompounderProfileStatus.
                      ORDINARY_COMPOUNDER_PROFILE_ESTABLISHED)
        source = inspect.getsource(profile)
        self.assertNotIn("business_profile_engine", source)
        self.assertNotIn("instrument_profile_engine", source)


if __name__ == "__main__":
    unittest.main()
