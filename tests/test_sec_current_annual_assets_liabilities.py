"""Adversarial tests for paired CURRENT annual assets and liabilities."""
import ast
from collections import UserDict
from dataclasses import FrozenInstanceError, fields, replace
from decimal import Decimal
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from economic_facts import sec_current_annual_assets_liabilities as qualifier
from economic_facts import sec_assets_liabilities as extraction
from economic_facts import sec_ordinary_compounder_profile as profile_module
from economic_facts.sec_archive import ArchiveError, SecArchive
from tests import test_sec_current_eps_comparability_qualification as comparability_tests
from tests import test_sec_ordinary_compounder_profile as profile_tests
from tests.sec_current_security_eps_qualification_fixtures import (
    VALUES,
    companyfacts_rows,
)
from tests.sec_filing_fixtures import raw
from tests.sec_five_year_eps_presentation_fixtures import five_year_table
from tests.sec_assets_liabilities_fixtures import (
    LATEST_ACCESSION,
    LIABILITIES_VALUE,
    ASSETS_VALUE,
    SECOND_ACCESSION,
    capture_profile,
    coherent_pair_payload,
    companyfacts_payload,
    conflicting_liabilities_payload,
    conflicting_assets_payload,
    duplicate_same_value_payload,
    financial_row,
    mismatched_period_payload,
    missing_liabilities_payload,
    missing_assets_payload,
    no_common_accession_payload,
    orphan_assets_conflict_payload,
    wrong_unit_payload,
)
from tests.sec_property4_temporal_boundary_fixtures import BOUNDARY_T1, BOUNDARY_T2
from tests.sec_property4_temporal_fixtures import CIK


class SecCurrentAnnualAssetsLiabilitiesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = comparability_tests.SecCurrentEPSComparabilityTests(
            methodName="runTest"
        )
        cls.fixture.setUp()
        cls.receipt, cls.available = capture_profile(cls.fixture)
        _, cls.unavailable = capture_profile(
            cls.fixture,
            sic=None,
            description=None,
        )
        _, cls.unsupported = capture_profile(
            cls.fixture,
            sic=6021,
            description="National Commercial Banks",
        )
        _, cls.semantic_replay_conflict = capture_profile(
            cls.fixture,
            expected_comparability_semantic_id="0" * 64,
        )
        _, cls.evidence_replay_conflict = capture_profile(
            cls.fixture,
            expected_comparability_evidence_id="0" * 64,
        )

    @classmethod
    def tearDownClass(cls):
        cls.fixture.doCleanups()

    def qualify(self, profile=None, archive=None):
        return qualifier.qualify_sec_current_annual_assets_liabilities(
            self.fixture.current_archive if archive is None else archive,
            self.available if profile is None else profile,
        )

    def profile_for(self, payload, *, reverse=False, captured_at=BOUNDARY_T1):
        return capture_profile(
            self.fixture,
            payload,
            reverse=reverse,
            captured_at=captured_at,
        )[1]

    @staticmethod
    def replace_decision(profile, structure, **changes):
        return replace(
            profile,
            decisions=tuple(
                replace(item, **changes) if item.profile is structure else item
                for item in profile.decisions
            ),
        )

    def extract(self, payload, *, content=None):
        with tempfile.TemporaryDirectory() as temporary:
            archive = SecArchive(Path(temporary).resolve() / "archive")
            receipt = archive._capture_live(
                raw(payload) if content is None else content,
                cik=CIK,
                captured_at=BOUNDARY_T1,
            )
            return extraction.extract_assets_liabilities(
                archive.read_object(receipt), receipt
            )

    def test_exact_public_input_types_only(self):
        class ArchiveSubclass(SecArchive):
            pass

        class ProfileSubclass(
            profile_module.OrdinaryCompounderMethodProfileQualification
        ):
            pass

        subclass = ProfileSubclass(*(
            getattr(self.available, field.name)
            for field in fields(self.available)
        ))
        with tempfile.TemporaryDirectory() as temporary:
            foreign_archive = ArchiveSubclass(Path(temporary) / "archive")
            cases = (
                ({}, self.available),
                (UserDict(), self.available),
                (foreign_archive, self.available),
                (self.fixture.current_archive, {}),
                (self.fixture.current_archive, UserDict()),
                (self.fixture.current_archive, subclass),
                (self.fixture.current_archive, self.available.upstream_comparability),
            )
            for archive, profile in cases:
                with self.subTest(types=(type(archive), type(profile))), \
                        self.assertRaises(
                            qualifier.CurrentAnnualAssetsLiabilitiesError
                        ):
                    qualifier.qualify_sec_current_annual_assets_liabilities(
                        archive, profile
                    )

    def test_coherent_pair_establishes_exact_decimal_facts_only(self):
        result = self.qualify()
        self.assertEqual(
            result.contract_version,
            "2026-10-08-current-annual-assets-liabilities-qualification-v1",
        )
        self.assertEqual(
            result.qualifier_version,
            "2026-10-08-paired-common-filing-exact-decimal-usd-instant-fact-qualification-v1",
        )
        self.assertEqual(
            result.evidence_kind,
            "CURRENT_ANNUAL_ASSETS_LIABILITIES_QUALIFICATION",
        )
        self.assertIs(
            result.status,
            qualifier.CurrentAnnualAssetsLiabilitiesStatus.
            PAIRED_ASSETS_LIABILITIES_ESTABLISHED,
        )
        self.assertEqual(result.period_end, "2024-12-31")
        self.assertNotIn("period_start", {field.name for field in fields(result)})
        self.assertEqual(result.accounting_namespace, "us-gaap")
        self.assertEqual(result.accounting_basis, "US_GAAP")
        self.assertEqual(result.assets_concept, "Assets")
        self.assertEqual(result.liabilities_concept, "Liabilities")
        self.assertEqual(result.unit, "USD")
        self.assertEqual(result.assets, Decimal(ASSETS_VALUE))
        self.assertEqual(result.liabilities, Decimal(LIABILITIES_VALUE))
        self.assertIs(type(result.assets), Decimal)
        self.assertIs(type(result.liabilities), Decimal)
        self.assertEqual(result.supporting_accessions, (LATEST_ACCESSION,))
        public_fields = set(result.to_dict()["current_annual_assets_liabilities"])
        for forbidden in (
            "ratio", "percentage", "debt", "leverage", "score", "grade",
            "threshold", "ranking", "recommendation", "allocation", "sizing",
        ):
            self.assertNotIn(forbidden, public_fields)

    def test_profile_capability_states_project_exactly_without_partial_values(self):
        cases = (
            (
                self.unavailable,
                qualifier.CurrentAnnualAssetsLiabilitiesStatus.
                EVIDENCE_UNAVAILABLE,
                qualifier.CurrentAnnualAssetsLiabilitiesReason.
                UPSTREAM_PROFILE_UNAVAILABLE,
            ),
            (
                self.unsupported,
                qualifier.CurrentAnnualAssetsLiabilitiesStatus.
                EVIDENCE_UNSUPPORTED,
                qualifier.CurrentAnnualAssetsLiabilitiesReason.
                UPSTREAM_PROFILE_UNSUPPORTED,
            ),
            (
                self.semantic_replay_conflict,
                qualifier.CurrentAnnualAssetsLiabilitiesStatus.SOURCE_CONFLICT,
                qualifier.CurrentAnnualAssetsLiabilitiesReason.
                UPSTREAM_SOURCE_CONFLICT,
            ),
            (
                self.evidence_replay_conflict,
                qualifier.CurrentAnnualAssetsLiabilitiesStatus.SOURCE_CONFLICT,
                qualifier.CurrentAnnualAssetsLiabilitiesReason.
                UPSTREAM_SOURCE_CONFLICT,
            ),
        )
        for profile, status, reason in cases:
            with self.subTest(status=status):
                result = self.qualify(profile)
                self.assertIs(result.status, status)
                self.assertEqual(result.reasons, (reason,))
                self.assertIsNone(result.assets)
                self.assertIsNone(result.liabilities)
                self.assertEqual(result.selected_assets_observation_ids, ())
                self.assertEqual(result.selected_liabilities_observation_ids, ())
                self.assertEqual(result.supporting_accessions, ())
                self.assertEqual(result.supporting_filings, ())

    def test_replay_provenance_is_authenticated_expected_vs_actual(self):
        comparability = self.available.upstream_comparability
        self.assertEqual(
            self.available.expected_comparability_semantic_id,
            comparability.semantic_id,
        )
        self.assertEqual(
            self.available.expected_comparability_evidence_id,
            comparability.evidence_id,
        )
        self.assertNotIn(
            profile_module.ProfileReason.REPLAY_IDENTITY_MISMATCH,
            self.available.reasons,
        )
        for profile in (
            self.semantic_replay_conflict,
            self.evidence_replay_conflict,
        ):
            with self.subTest(profile=profile):
                actual = profile.upstream_comparability
                self.assertTrue(
                    profile.expected_comparability_semantic_id
                    != actual.semantic_id
                    or profile.expected_comparability_evidence_id
                    != actual.evidence_id
                )
                self.assertIs(
                    profile.status,
                    profile_module.OrdinaryCompounderProfileStatus.SOURCE_CONFLICT,
                )
                self.assertIn(
                    profile_module.ProfileReason.REPLAY_IDENTITY_MISMATCH,
                    profile.reasons,
                )
                result = self.qualify(profile)
                self.assertIs(
                    result.status,
                    qualifier.CurrentAnnualAssetsLiabilitiesStatus.
                    SOURCE_CONFLICT,
                )
                self.assertEqual(
                    result.reasons,
                    (
                        qualifier.CurrentAnnualAssetsLiabilitiesReason.
                        UPSTREAM_SOURCE_CONFLICT,
                    ),
                )

    def test_fabricated_replay_conflict_and_expected_id_mutation_are_rejected(self):
        fabricated = replace(
            self.available,
            status=profile_module.OrdinaryCompounderProfileStatus.SOURCE_CONFLICT,
            profile=None,
            reasons=(profile_module.ProfileReason.REPLAY_IDENTITY_MISMATCH,),
        )
        mutations = (
            fabricated,
            replace(
                self.available,
                expected_comparability_semantic_id="0" * 64,
            ),
            replace(
                self.available,
                expected_comparability_evidence_id="0" * 64,
            ),
        )
        for profile in mutations:
            with self.subTest(profile=profile), self.assertRaises(
                qualifier.CurrentAnnualAssetsLiabilitiesError
            ):
                self.qualify(profile)

    def test_v1_profile_contract_is_rejected_without_migration(self):
        legacy = replace(
            self.available,
            contract_version=(
                "2026-09-29-sec-ordinary-compounder-method-profile-v1"
            ),
        )
        with self.assertRaises(
            qualifier.CurrentAnnualAssetsLiabilitiesError
        ):
            self.qualify(legacy)

    def test_factory_impossible_reconstructed_profile_states_are_rejected(self):
        impossible = (
            replace(
                self.available,
                status=profile_module.OrdinaryCompounderProfileStatus.PROFILE_UNAVAILABLE,
                profile=None,
                reasons=(),
            ),
            replace(
                self.available,
                status=profile_module.OrdinaryCompounderProfileStatus.PROFILE_UNSUPPORTED,
                profile=None,
                reasons=(profile_module.ProfileReason.SIC_MISSING_OR_INVALID,),
            ),
            replace(
                self.available,
                status=profile_module.OrdinaryCompounderProfileStatus.SOURCE_CONFLICT,
                profile=None,
                reasons=(profile_module.ProfileReason.UNSUPPORTED_SIC_PROFILE,),
            ),
            replace(
                self.available,
                status=profile_module.OrdinaryCompounderProfileStatus.PROFILE_UNAVAILABLE,
                profile=None,
                reasons=(
                    profile_module.ProfileReason.
                    POSITIVE_FIVE_PERIOD_ROUTE_NOT_ESTABLISHED,
                ),
            ),
            replace(self.available, status="FUTURE_STATE"),
            replace(self.available, source_cik="0000000001"),
        )
        for profile in impossible:
            with self.subTest(profile=profile), self.assertRaises(
                qualifier.CurrentAnnualAssetsLiabilitiesError
            ):
                self.qualify(profile)

    def test_unsupported_bank_profile_cannot_be_forged_into_established(self):
        bank = next(
            item for item in self.unsupported.decisions
            if item.profile is profile_module.UnsupportedStructure.BANK
        )
        self.assertIs(
            self.unsupported.status,
            profile_module.OrdinaryCompounderProfileStatus.PROFILE_UNSUPPORTED,
        )
        self.assertIs(bank.decision, profile_module.ProfileDecisionValue.NOT_EXCLUDED)
        self.assertIn(
            profile_module.ProfileReason.UNSUPPORTED_SIC_PROFILE,
            self.unsupported.reasons,
        )

        forged = self.replace_decision(
            self.unsupported,
            profile_module.UnsupportedStructure.BANK,
            decision=profile_module.ProfileDecisionValue.EXCLUDED,
            reason="SEC_SIC_PROFILE_EXCLUDED:6021:National Commercial Banks",
        )
        forged = replace(
            forged,
            status=(
                profile_module.OrdinaryCompounderProfileStatus.
                ORDINARY_COMPOUNDER_PROFILE_ESTABLISHED
            ),
            profile=profile_module.PROFILE,
            reasons=(),
        )
        with self.assertRaises(
            qualifier.CurrentAnnualAssetsLiabilitiesError
        ):
            self.qualify(forged)

    def test_profile_reasons_require_their_exact_factory_conditions(self):
        unavailable = profile_module.OrdinaryCompounderProfileStatus.PROFILE_UNAVAILABLE
        fabricated = (
            profile_module.ProfileReason.PR5C_NOT_ESTABLISHED,
            profile_module.ProfileReason.SIC_MISSING_OR_INVALID,
            profile_module.ProfileReason.SIC_DESCRIPTION_MISSING_OR_INVALID,
            profile_module.ProfileReason.
            REPORTING_SUBJECT_STABILITY_NOT_ESTABLISHED,
            profile_module.ProfileReason.MIXED_STRUCTURE_UNRESOLVED,
        )
        for reason in fabricated:
            forged = replace(
                self.available,
                status=unavailable,
                profile=None,
                reasons=(reason,),
            )
            with self.subTest(reason=reason), self.assertRaises(
                qualifier.CurrentAnnualAssetsLiabilitiesError
            ):
                self.qualify(forged)

    def test_unsupported_reason_requires_reachable_structural_decision(self):
        forged = replace(
            self.available,
            status=profile_module.OrdinaryCompounderProfileStatus.PROFILE_UNSUPPORTED,
            profile=None,
            reasons=(profile_module.ProfileReason.UNSUPPORTED_SIC_PROFILE,),
        )
        self.assertTrue(all(
            item.decision is profile_module.ProfileDecisionValue.EXCLUDED
            for item in forged.decisions
        ))
        with self.assertRaises(
            qualifier.CurrentAnnualAssetsLiabilitiesError
        ):
            self.qualify(forged)

    def test_structural_decision_semantics_and_support_are_factory_exact(self):
        cases = (
            self.replace_decision(
                self.available,
                profile_module.UnsupportedStructure.BANK,
                decision=profile_module.ProfileDecisionValue.NOT_EXCLUDED,
            ),
            self.replace_decision(
                self.available,
                profile_module.UnsupportedStructure.REIT,
                reason="SEC_SIC_PROFILE_MATCH:3571:Electronic Computers",
            ),
            self.replace_decision(
                self.available,
                profile_module.UnsupportedStructure.TURNAROUND,
                supporting_semantic_ids=("0" * 64,),
            ),
            self.replace_decision(
                self.available,
                profile_module.UnsupportedStructure.LOSS_MAKING,
                supporting_evidence_ids=("0" * 64,),
            ),
        )
        for profile in cases:
            with self.subTest(profile=profile), self.assertRaises(
                qualifier.CurrentAnnualAssetsLiabilitiesError
            ):
                self.qualify(profile)

    def test_genuine_turnaround_loss_reporting_and_mixed_states_are_preserved(self):
        factory = profile_tests.OrdinaryCompounderProfileTests(methodName="runTest")
        factory.setUp()
        self.addCleanup(factory.doCleanups)
        transition = factory.qualify(
            filings=factory.bridge_fixture.comparability.filings(claims=(
                "Old Fiction was the predecessor, and New Fiction became the successor.",
            )),
        )
        mixed = factory.qualify(
            filings=factory.bridge_fixture.comparability.filings(claims=(
                "These are combined financial statements.",
            )),
        )
        rows = companyfacts_rows()
        for row in rows:
            if row["fy"] == 2024:
                row["val"] = -1
        values = dict(VALUES)
        values[2024] = Decimal("-1")
        loss_making = factory.qualify(
            current=factory.bridge_fixture.comparability.current(rows=rows),
            filings=factory.bridge_fixture.comparability.filings(
                table=five_year_table(values=values),
                value_overrides={2024: Decimal("-1")},
            ),
        )
        archive = factory.bridge_fixture.comparability.current_archive
        cases = (
            (
                transition,
                profile_module.OrdinaryCompounderProfileStatus.PROFILE_UNAVAILABLE,
                profile_module.ProfileReason.
                REPORTING_SUBJECT_STABILITY_NOT_ESTABLISHED,
                qualifier.CurrentAnnualAssetsLiabilitiesStatus.
                EVIDENCE_UNAVAILABLE,
            ),
            (
                mixed,
                profile_module.OrdinaryCompounderProfileStatus.PROFILE_UNAVAILABLE,
                profile_module.ProfileReason.MIXED_STRUCTURE_UNRESOLVED,
                qualifier.CurrentAnnualAssetsLiabilitiesStatus.
                EVIDENCE_UNAVAILABLE,
            ),
            (
                loss_making,
                profile_module.OrdinaryCompounderProfileStatus.PROFILE_UNSUPPORTED,
                profile_module.ProfileReason.
                POSITIVE_FIVE_PERIOD_ROUTE_NOT_ESTABLISHED,
                qualifier.CurrentAnnualAssetsLiabilitiesStatus.
                EVIDENCE_UNSUPPORTED,
            ),
        )
        for profile, upstream_status, upstream_reason, local_status in cases:
            with self.subTest(upstream_status=upstream_status):
                self.assertIs(profile.status, upstream_status)
                self.assertIn(upstream_reason, profile.reasons)
                result = qualifier.qualify_sec_current_annual_assets_liabilities(
                    archive,
                    profile,
                )
                self.assertIs(result.status, local_status)
                self.assertIsNone(result.assets)
                self.assertIsNone(result.liabilities)

    def test_factory_out_of_range_integer_sic_projects_capability_state(self):
        _, profile = capture_profile(
            self.fixture,
            sic=10000,
            description="Out of Range Industry",
        )
        self.assertIs(
            profile.status,
            profile_module.OrdinaryCompounderProfileStatus.PROFILE_UNAVAILABLE,
        )
        self.assertIn(
            profile_module.ProfileReason.SIC_MISSING_OR_INVALID,
            profile.reasons,
        )
        self.assertEqual(profile.sic, 10000)
        self.assertEqual(len(profile.decisions), len(profile_module.UnsupportedStructure))

        result = self.qualify(profile)
        projected = {
            profile_module.OrdinaryCompounderProfileStatus.PROFILE_UNAVAILABLE: (
                qualifier.CurrentAnnualAssetsLiabilitiesStatus.
                EVIDENCE_UNAVAILABLE,
                qualifier.CurrentAnnualAssetsLiabilitiesReason.
                UPSTREAM_PROFILE_UNAVAILABLE,
            ),
            profile_module.OrdinaryCompounderProfileStatus.PROFILE_UNSUPPORTED: (
                qualifier.CurrentAnnualAssetsLiabilitiesStatus.
                EVIDENCE_UNSUPPORTED,
                qualifier.CurrentAnnualAssetsLiabilitiesReason.
                UPSTREAM_PROFILE_UNSUPPORTED,
            ),
            profile_module.OrdinaryCompounderProfileStatus.SOURCE_CONFLICT: (
                qualifier.CurrentAnnualAssetsLiabilitiesStatus.SOURCE_CONFLICT,
                qualifier.CurrentAnnualAssetsLiabilitiesReason.
                UPSTREAM_SOURCE_CONFLICT,
            ),
        }
        expected_status, expected_reason = projected[profile.status]
        self.assertIs(result.status, expected_status)
        self.assertEqual(result.reasons, (expected_reason,))
        self.assertIsNone(result.assets)
        self.assertIsNone(result.liabilities)
        self.assertEqual(result.selected_assets_observation_ids, ())
        self.assertEqual(result.selected_liabilities_observation_ids, ())
        self.assertEqual(result.supporting_accessions, ())
        self.assertEqual(result.supporting_filings, ())

        for invalid_sic in ("10000", 10000.0, True):
            with self.subTest(invalid_sic=invalid_sic), self.assertRaises(
                qualifier.CurrentAnnualAssetsLiabilitiesError
            ):
                self.qualify(replace(profile, sic=invalid_sic))

    def test_established_profile_and_period_chain_must_remain_canonical(self):
        periods = list(self.available.upstream_comparability.period_decisions)
        periods[2] = replace(
            periods[2],
            period_start=periods[1].period_start,
            period_end=periods[1].period_end,
        )
        cases = (
            replace(self.available, metadata_semantic_id=None),
            replace(self.available, sic_description=" Electronic Computers "),
            replace(self.available, sic=10000),
            replace(
                self.available,
                upstream_comparability=replace(
                    self.available.upstream_comparability,
                    period_decisions=tuple(periods),
                ),
            ),
        )
        for profile in cases:
            with self.subTest(profile=profile), self.assertRaises(
                qualifier.CurrentAnnualAssetsLiabilitiesError
            ):
                self.qualify(profile)

    def test_extraction_preserves_exact_source_row_and_capture_semantics(self):
        observation = next(
            item for item in self.extract(coherent_pair_payload()).observations
            if item.concept == extraction.ASSETS_CONCEPT
        )
        original = financial_row(ASSETS_VALUE)
        self.assertEqual(observation.source_cik, CIK)
        self.assertEqual(observation.namespace, "us-gaap")
        self.assertEqual(observation.unit, "USD")
        self.assertEqual(observation.value, Decimal(ASSETS_VALUE))
        self.assertIsNone(observation.start)
        for field, source_key in (
            ("end", "end"), ("fy", "fy"),
            ("fp", "fp"), ("form", "form"), ("filed", "filed"),
            ("accession", "accn"), ("frame", "frame"),
        ):
            self.assertEqual(getattr(observation, field), original[source_key])
        self.assertTrue(observation.source_object_hash)
        self.assertTrue(observation.capture_receipt_id)
        self.assertTrue(observation.source_locator)
        self.assertTrue(observation.semantic_locator)
        self.assertTrue(observation.row_json)
        self.assertIn("CURRENT_CAPTURE_REPLAY", observation.source_semantics)

    def test_malformed_companyfacts_structures_fail_closed(self):
        malformed = []
        facts_array = coherent_pair_payload()
        facts_array["facts"] = []
        malformed.append(facts_array)
        units_array = coherent_pair_payload()
        units_array["facts"]["us-gaap"][extraction.ASSETS_CONCEPT]["units"] = []
        malformed.append(units_array)
        rows_object = coherent_pair_payload()
        rows_object["facts"]["us-gaap"][extraction.ASSETS_CONCEPT]["units"][
            "USD"
        ] = {}
        malformed.append(rows_object)
        row_array = coherent_pair_payload()
        row_array["facts"]["us-gaap"][extraction.ASSETS_CONCEPT]["units"][
            "USD"
        ] = [[]]
        malformed.append(row_array)
        for payload in malformed:
            with self.subTest(payload=payload), self.assertRaises(ArchiveError):
                self.extract(payload)

    def test_state_and_reason_surfaces_are_closed(self):
        self.assertEqual(
            {item.value for item in qualifier.CurrentAnnualAssetsLiabilitiesStatus},
            {
                "PAIRED_ASSETS_LIABILITIES_ESTABLISHED",
                "EVIDENCE_UNAVAILABLE",
                "EVIDENCE_UNSUPPORTED",
                "SOURCE_CONFLICT",
            },
        )
        self.assertEqual(
            {item.value for item in qualifier.CurrentAnnualAssetsLiabilitiesReason},
            {
                "UPSTREAM_PROFILE_UNAVAILABLE",
                "UPSTREAM_PROFILE_UNSUPPORTED",
                "UPSTREAM_SOURCE_CONFLICT",
                "CANONICAL_ROUTE_IDENTITY_CONFLICT",
                "CAPTURE_REPLAY_CONFLICT",
                "SOURCE_CIK_CONFLICT",
                "ASSETS_UNAVAILABLE",
                "LIABILITIES_UNAVAILABLE",
                "EXACT_USD_UNIT_UNAVAILABLE",
                "FINITE_ASSETS_VALUE_UNAVAILABLE",
                "FINITE_LIABILITIES_VALUE_UNAVAILABLE",
                "EXACT_ANNUAL_TARGET_PERIOD_END_PRESENTATION_UNAVAILABLE",
                "NO_COMMON_ANNUAL_FILING_ACCESSION",
                "COMPETING_ASSETS_VALUES",
                "COMPETING_LIABILITIES_VALUES",
                "COMMON_FILING_METADATA_CONFLICT",
            },
        )

    def test_only_exact_concepts_namespace_and_usd_unit_are_admissible(self):
        substitutes = (
            ("assets_concept", "AssetsCurrent"),
            ("assets_concept", "AssetsNet"),
            ("assets_concept", "TangibleAssetsNet"),
            ("assets_concept", "InvestedCapital"),
            ("liabilities_concept", "LiabilitiesCurrent"),
            ("liabilities_concept", "StockholdersEquity"),
            ("liabilities_concept", "LongTermDebt"),
        )
        for key, concept in substitutes:
            result = self.qualify(self.profile_for(companyfacts_payload(**{key: concept})))
            with self.subTest(concept=concept):
                self.assertIs(
                    result.status,
                    qualifier.CurrentAnnualAssetsLiabilitiesStatus.
                    EVIDENCE_UNAVAILABLE,
                )
                self.assertIsNone(result.assets)
                self.assertIsNone(result.liabilities)
        issuer_extension = companyfacts_payload(
            namespace="fiction",
            assets_concept="FictionAssets",
            liabilities_concept="FictionLiabilities",
        )
        result = self.qualify(self.profile_for(issuer_extension))
        self.assertIs(
            result.status,
            qualifier.CurrentAnnualAssetsLiabilitiesStatus.EVIDENCE_UNAVAILABLE,
        )
        wrong_unit = self.qualify(self.profile_for(wrong_unit_payload()))
        self.assertEqual(
            wrong_unit.reasons,
            (qualifier.CurrentAnnualAssetsLiabilitiesReason.
             EXACT_USD_UNIT_UNAVAILABLE,),
        )
        missing_unit_payload = coherent_pair_payload()
        missing_unit_payload["facts"]["us-gaap"][
            extraction.ASSETS_CONCEPT
        ]["units"] = {}
        missing_unit = self.qualify(self.profile_for(missing_unit_payload))
        self.assertEqual(
            missing_unit.reasons,
            (qualifier.CurrentAnnualAssetsLiabilitiesReason.
             EXACT_USD_UNIT_UNAVAILABLE,),
        )

    def test_missing_concepts_are_unavailable_and_never_zero(self):
        cases = (
            (
                missing_assets_payload(),
                qualifier.CurrentAnnualAssetsLiabilitiesReason.
                ASSETS_UNAVAILABLE,
            ),
            (
                missing_liabilities_payload(),
                qualifier.CurrentAnnualAssetsLiabilitiesReason.
                LIABILITIES_UNAVAILABLE,
            ),
        )
        for payload, reason in cases:
            result = self.qualify(self.profile_for(payload))
            with self.subTest(reason=reason):
                self.assertIs(
                    result.status,
                    qualifier.CurrentAnnualAssetsLiabilitiesStatus.
                    EVIDENCE_UNAVAILABLE,
                )
                self.assertIn(reason, result.reasons)
                self.assertIsNone(result.assets)
                self.assertIsNone(result.liabilities)

        both = self.qualify(self.profile_for(companyfacts_payload(
            include_assets=False,
            include_liabilities=False,
        )))
        self.assertEqual(
            both.reasons,
            tuple(sorted(
                (
                    qualifier.CurrentAnnualAssetsLiabilitiesReason.
                    ASSETS_UNAVAILABLE,
                    qualifier.CurrentAnnualAssetsLiabilitiesReason.
                    LIABILITIES_UNAVAILABLE,
                ),
                key=lambda item: item.value,
            )),
        )

    def test_zero_and_negative_values_are_legitimate_exact_facts(self):
        cases = ((9, 5), (9, 0), (9, -4), (0, 2), (-5, 2), (-5, -6))
        for assets_value, liabilities_value in cases:
            payload = companyfacts_payload(
                assets_rows=[financial_row(assets_value)],
                liabilities_rows=[financial_row(liabilities_value)],
            )
            result = self.qualify(self.profile_for(payload))
            with self.subTest(values=(assets_value, liabilities_value)):
                self.assertIs(
                    result.status,
                    qualifier.CurrentAnnualAssetsLiabilitiesStatus.
                    PAIRED_ASSETS_LIABILITIES_ESTABLISHED,
                )
                self.assertEqual(result.assets, Decimal(assets_value))
                self.assertEqual(
                    result.liabilities, Decimal(liabilities_value)
                )

    def test_nonfinite_and_invalid_values_cannot_establish(self):
        cases = (
            (
                companyfacts_payload(
                    assets_rows=[financial_row("NaN")],
                    liabilities_rows=[financial_row(LIABILITIES_VALUE)],
                ),
                qualifier.CurrentAnnualAssetsLiabilitiesReason.
                FINITE_ASSETS_VALUE_UNAVAILABLE,
            ),
            (
                companyfacts_payload(
                    assets_rows=[financial_row(ASSETS_VALUE)],
                    liabilities_rows=[financial_row("Infinity")],
                ),
                qualifier.CurrentAnnualAssetsLiabilitiesReason.
                FINITE_LIABILITIES_VALUE_UNAVAILABLE,
            ),
        )
        for payload, reason in cases:
            with self.subTest(reason=reason):
                self.assertEqual(
                    self.qualify(self.profile_for(payload)).reasons,
                    (reason,),
                )
        nonfinite = raw(coherent_pair_payload()).replace(
            str(ASSETS_VALUE).encode(), b"NaN", 1
        )
        with self.assertRaises(ArchiveError):
            self.extract(coherent_pair_payload(), content=nonfinite)

    def test_exact_annual_target_end_and_presentation_are_required(self):
        payloads = (
            mismatched_period_payload(),
            companyfacts_payload(
                assets_rows=[financial_row(
                    ASSETS_VALUE, fp="Q4", form="10-Q"
                )],
                liabilities_rows=[financial_row(
                    LIABILITIES_VALUE, fp="Q4", form="10-Q"
                )],
            ),
            companyfacts_payload(
                assets_rows=[financial_row(
                    ASSETS_VALUE, start="2024-01-01"
                )],
                liabilities_rows=[financial_row(
                    LIABILITIES_VALUE, start="2024-01-01"
                )],
            ),
        )
        for payload in payloads:
            result = self.qualify(self.profile_for(payload))
            with self.subTest(payload=payload):
                self.assertIs(
                    result.status,
                    qualifier.CurrentAnnualAssetsLiabilitiesStatus.
                    EVIDENCE_UNAVAILABLE,
                )
                self.assertIn(
                    qualifier.CurrentAnnualAssetsLiabilitiesReason.
                    EXACT_ANNUAL_TARGET_PERIOD_END_PRESENTATION_UNAVAILABLE,
                    result.reasons,
                )

    def test_instant_facts_require_no_duration_start(self):
        established = self.qualify(self.profile_for(companyfacts_payload(
            assets_rows=[financial_row(ASSETS_VALUE, start=None)],
            liabilities_rows=[financial_row(LIABILITIES_VALUE, start=None)],
        )))
        self.assertIs(
            established.status,
            qualifier.CurrentAnnualAssetsLiabilitiesStatus.
            PAIRED_ASSETS_LIABILITIES_ESTABLISHED,
        )
        self.assertEqual(established.period_end, "2024-12-31")
        self.assertNotIn("period_start", established.to_dict()[
            "current_annual_assets_liabilities"
        ])

    def test_common_accession_required_and_orphan_does_not_poison_pair(self):
        unavailable = self.qualify(self.profile_for(no_common_accession_payload()))
        self.assertEqual(
            unavailable.reasons,
            (qualifier.CurrentAnnualAssetsLiabilitiesReason.
             NO_COMMON_ANNUAL_FILING_ACCESSION,),
        )
        established = self.qualify(
            self.profile_for(orphan_assets_conflict_payload())
        )
        self.assertIs(
            established.status,
            qualifier.CurrentAnnualAssetsLiabilitiesStatus.
            PAIRED_ASSETS_LIABILITIES_ESTABLISHED,
        )
        self.assertEqual(established.supporting_accessions, (LATEST_ACCESSION,))

    def test_multiple_coherent_common_accessions_are_deterministic(self):
        profile = self.profile_for(duplicate_same_value_payload())
        first = self.qualify(profile)
        second = self.qualify(profile)
        self.assertEqual(first, second)
        self.assertEqual(first.supporting_accessions,
                         (LATEST_ACCESSION, SECOND_ACCESSION))
        self.assertEqual(first.semantic_id, second.semantic_id)
        self.assertEqual(first.evidence_id, second.evidence_id)

    def test_competing_common_pair_values_are_source_conflicts(self):
        cases = (
            (
                conflicting_assets_payload(),
                qualifier.CurrentAnnualAssetsLiabilitiesReason.
                COMPETING_ASSETS_VALUES,
            ),
            (
                conflicting_liabilities_payload(),
                qualifier.CurrentAnnualAssetsLiabilitiesReason.
                COMPETING_LIABILITIES_VALUES,
            ),
        )
        for payload, reason in cases:
            result = self.qualify(self.profile_for(payload))
            with self.subTest(reason=reason):
                self.assertIs(
                    result.status,
                    qualifier.CurrentAnnualAssetsLiabilitiesStatus.
                    SOURCE_CONFLICT,
                )
                self.assertIn(reason, result.reasons)
                self.assertIsNone(result.assets)
                self.assertIsNone(result.liabilities)

        both = companyfacts_payload(
            assets_rows=[
                financial_row(100),
                financial_row(101, accession=SECOND_ACCESSION, filed="2025-02-02"),
            ],
            liabilities_rows=[
                financial_row(20),
                financial_row(21, accession=SECOND_ACCESSION, filed="2025-02-02"),
            ],
        )
        result = self.qualify(self.profile_for(both))
        self.assertEqual(
            set(result.reasons),
            {
                qualifier.CurrentAnnualAssetsLiabilitiesReason.
                COMPETING_ASSETS_VALUES,
                qualifier.CurrentAnnualAssetsLiabilitiesReason.
                COMPETING_LIABILITIES_VALUES,
            },
        )

    def test_common_accession_metadata_must_be_coherent_but_frame_may_differ(self):
        for field, replacement in (
            ("form", "10-K/A"),
            ("filed", "2025-02-02"),
            ("fy", 2025),
        ):
            assets = financial_row(ASSETS_VALUE)
            liabilities = financial_row(LIABILITIES_VALUE, **{field: replacement})
            result = self.qualify(self.profile_for(companyfacts_payload(
                assets_rows=[assets],
                liabilities_rows=[liabilities],
            )))
            with self.subTest(field=field):
                self.assertEqual(
                    result.reasons,
                    (qualifier.CurrentAnnualAssetsLiabilitiesReason.
                     COMMON_FILING_METADATA_CONFLICT,),
                )
        frame_difference = self.qualify(self.profile_for(companyfacts_payload(
            assets_rows=[financial_row(
                ASSETS_VALUE, frame="CY2024"
            )],
            liabilities_rows=[financial_row(
                LIABILITIES_VALUE, frame="CY2024Q4"
            )],
        )))
        self.assertIs(
            frame_difference.status,
            qualifier.CurrentAnnualAssetsLiabilitiesStatus.
            PAIRED_ASSETS_LIABILITIES_ESTABLISHED,
        )

    def test_route_receipt_object_and_source_cik_conflicts_fail_closed(self):
        route_mismatch = replace(
            self.available,
            upstream_comparability=replace(
                self.available.upstream_comparability,
                route_local_issuer_key="0" * 64,
            ),
        )
        with self.assertRaises(
            qualifier.CurrentAnnualAssetsLiabilitiesError
        ):
            self.qualify(route_mismatch)

        comparability = self.available.upstream_comparability
        security = comparability.upstream_security_eps
        bridge = security.upstream_registered_listing_bridge
        temporal = bridge.temporal_boundary
        current = temporal.current_evidence
        incoherent_request = replace(current.request, cik="0000000001")
        incoherent_current = replace(current, request=incoherent_request)
        incoherent_temporal = replace(temporal, current_evidence=incoherent_current)
        incoherent_bridge = replace(bridge, temporal_boundary=incoherent_temporal)
        incoherent_security = replace(
            security,
            upstream_registered_listing_bridge=incoherent_bridge,
        )
        incoherent_comparability = replace(
            comparability,
            upstream_security_eps=incoherent_security,
        )
        incoherent_profile = replace(
            self.available,
            upstream_comparability=incoherent_comparability,
        )
        route_conflict = self.qualify(incoherent_profile)
        self.assertEqual(
            route_conflict.reasons,
            (qualifier.CurrentAnnualAssetsLiabilitiesReason.
             CANONICAL_ROUTE_IDENTITY_CONFLICT,),
        )

        with tempfile.TemporaryDirectory() as temporary:
            foreign = SecArchive(Path(temporary).resolve() / "foreign")
            replay = self.qualify(archive=foreign)
        self.assertEqual(
            replay.reasons,
            (qualifier.CurrentAnnualAssetsLiabilitiesReason.
             CAPTURE_REPLAY_CONFLICT,),
        )
        mismatched_receipt = replace(
            self.receipt,
            captured_at="2025-03-02T12:00:00Z",
        )
        with patch.object(
            self.fixture.current_archive,
            "read_receipt",
            return_value=mismatched_receipt,
        ):
            receipt_conflict = self.qualify()
        self.assertEqual(
            receipt_conflict.reasons,
            (qualifier.CurrentAnnualAssetsLiabilitiesReason.
             CAPTURE_REPLAY_CONFLICT,),
        )
        with patch.object(
            self.fixture.current_archive,
            "read_object",
            side_effect=ArchiveError("corrupt object"),
        ):
            object_conflict = self.qualify()
        self.assertEqual(
            object_conflict.reasons,
            (qualifier.CurrentAnnualAssetsLiabilitiesReason.
             CAPTURE_REPLAY_CONFLICT,),
        )
        extracted = extraction.AssetsLiabilitiesExtraction(
            extraction.EXTRACTION_VERSION,
            "0000000001",
            self.receipt.receipt_id,
            self.receipt.content_sha256,
            self.receipt.captured_at,
            self.receipt.source_locator,
            (),
            (),
        )
        with patch.object(
            qualifier,
            "extract_assets_liabilities",
            return_value=extracted,
        ):
            cik_conflict = self.qualify()
        self.assertEqual(
            cik_conflict.reasons,
            (qualifier.CurrentAnnualAssetsLiabilitiesReason.
             SOURCE_CIK_CONFLICT,),
        )

    def test_selected_observation_partition_and_supporting_metadata_are_exact(self):
        result = self.qualify(self.profile_for(duplicate_same_value_payload()))
        assets_ids = result.selected_assets_observation_ids
        liabilities_ids = result.selected_liabilities_observation_ids
        self.assertEqual(assets_ids, tuple(sorted(set(assets_ids))))
        self.assertEqual(liabilities_ids, tuple(sorted(set(liabilities_ids))))
        self.assertFalse(set(assets_ids) & set(liabilities_ids))
        flattened_assets = tuple(sorted(
            item for filing in result.supporting_filings
            for item in filing.assets_observation_ids
        ))
        flattened_liabilities = tuple(sorted(
            item for filing in result.supporting_filings
            for item in filing.liabilities_observation_ids
        ))
        self.assertEqual(flattened_assets, assets_ids)
        self.assertEqual(flattened_liabilities, liabilities_ids)
        self.assertEqual(
            tuple(filing.accession for filing in result.supporting_filings),
            result.supporting_accessions,
        )
        for filing in result.supporting_filings:
            self.assertEqual(len(filing.forms), 1)
            self.assertEqual(len(filing.filed_dates), 1)
            self.assertEqual(len(filing.fiscal_years), 1)

    def test_source_evidence_order_and_decimal_lexical_forms_do_not_change_semantics(self):
        payload = duplicate_same_value_payload()
        normal = self.qualify(self.profile_for(payload))
        reordered = duplicate_same_value_payload()
        facts = reordered["facts"]["us-gaap"]
        for concept in (
            extraction.ASSETS_CONCEPT,
            extraction.LIABILITIES_CONCEPT,
        ):
            facts[concept]["units"]["USD"].reverse()
        reordered_result = self.qualify(self.profile_for(reordered))
        self.assertIs(normal.status, reordered_result.status)
        self.assertEqual(normal.reasons, reordered_result.reasons)
        self.assertEqual(
            normal.assets,
            reordered_result.assets,
        )
        self.assertEqual(normal.liabilities, reordered_result.liabilities)
        self.assertEqual(
            normal.supporting_accessions,
            reordered_result.supporting_accessions,
        )
        reversed_evidence = replace(
            normal,
            selected_assets_observation_ids=tuple(
                reversed(normal.selected_assets_observation_ids)
            ),
            selected_liabilities_observation_ids=tuple(
                reversed(normal.selected_liabilities_observation_ids)
            ),
        )
        self.assertEqual(normal.semantic_id, reversed_evidence.semantic_id)
        lexical = replace(
            normal,
            assets=Decimal("250000000.000"),
            liabilities=Decimal("2.00000000E+8"),
        )
        self.assertEqual(normal.semantic_id, lexical.semantic_id)

    def test_exact_base_ten_precision_is_never_binary_float(self):
        precise = "250000000.12345678901234567890123456789"
        content = raw(coherent_pair_payload()).replace(
            str(ASSETS_VALUE).encode(), precise.encode(), 1
        )
        extracted = self.extract(coherent_pair_payload(), content=content)
        observation = next(
            item for item in extracted.observations
            if item.concept == extraction.ASSETS_CONCEPT
        )
        self.assertEqual(observation.value, Decimal(precise))
        self.assertIs(type(observation.value), Decimal)

    def test_genuine_factory_recapture_preserves_semantics_and_changes_evidence(self):
        first = self.qualify()
        recapture_fixture = comparability_tests.SecCurrentEPSComparabilityTests(
            methodName="runTest"
        )
        recapture_fixture.setUp()
        self.addCleanup(recapture_fixture.doCleanups)
        _, recaptured_profile = capture_profile(
            recapture_fixture,
            reverse=True,
            captured_at=BOUNDARY_T1,
        )
        recaptured = qualifier.qualify_sec_current_annual_assets_liabilities(
            recapture_fixture.current_archive,
            recaptured_profile,
        )
        self.assertEqual(first.assets, recaptured.assets)
        self.assertEqual(first.liabilities, recaptured.liabilities)
        self.assertEqual(first.source_cik, recaptured.source_cik)
        self.assertEqual(first.period_end, recaptured.period_end)
        self.assertEqual(first.semantic_id, recaptured.semantic_id)
        self.assertNotEqual(first.evidence_id, recaptured.evidence_id)
        self.assertNotEqual(first.capture_receipt_id, recaptured.capture_receipt_id)
        self.assertNotEqual(first.source_object_hash, recaptured.source_object_hash)

    def test_later_current_capture_changes_route_evidence_not_semantics(self):
        first = self.qualify()
        later_fixture = comparability_tests.SecCurrentEPSComparabilityTests(
            methodName="runTest"
        )
        later_fixture.setUp()
        self.addCleanup(later_fixture.doCleanups)
        _, later_profile = capture_profile(
            later_fixture,
            captured_at=BOUNDARY_T2,
        )
        later = qualifier.qualify_sec_current_annual_assets_liabilities(
            later_fixture.current_archive,
            later_profile,
        )
        self.assertEqual(first.source_cik, later.source_cik)
        self.assertEqual(first.period_end, later.period_end)
        for field in (
            "accounting_namespace",
            "accounting_basis",
            "assets_concept",
            "liabilities_concept",
            "unit",
        ):
            self.assertEqual(getattr(first, field), getattr(later, field))
        self.assertEqual(first.assets, later.assets)
        self.assertEqual(first.liabilities, later.liabilities)
        self.assertNotEqual(first.captured_at, later.captured_at)
        self.assertNotEqual(first.capture_receipt_id, later.capture_receipt_id)
        self.assertNotEqual(
            first.upstream_profile_evidence_id,
            later.upstream_profile_evidence_id,
        )
        self.assertNotEqual(
            first.upstream_comparability_evidence_id,
            later.upstream_comparability_evidence_id,
        )
        self.assertNotEqual(first.route_local_issuer_key, later.route_local_issuer_key)
        self.assertNotEqual(first.route_local_security_key, later.route_local_security_key)
        self.assertEqual(first.semantic_id, later.semantic_id)
        self.assertNotEqual(first.evidence_id, later.evidence_id)
        self.assertEqual(later.route_local_issuer_key,
                         later_profile.upstream_comparability.route_local_issuer_key)
        self.assertEqual(later.route_local_security_key,
                         later_profile.upstream_comparability.route_local_security_key)

    def test_semantic_identity_binds_both_absolute_economic_values(self):
        first = self.qualify(self.profile_for(companyfacts_payload(
            assets_rows=[financial_row(100)],
            liabilities_rows=[financial_row(20)],
        )))
        proportionally_equal = self.qualify(self.profile_for(companyfacts_payload(
            assets_rows=[financial_row(200)],
            liabilities_rows=[financial_row(40)],
        )))
        self.assertNotEqual(first.semantic_id, proportionally_equal.semantic_id)
        changed = (
            replace(first, source_cik="0000000001"),
            replace(first, period_end="2023-12-31"),
            replace(first, assets=Decimal("101")),
            replace(first, liabilities=Decimal("21")),
        )
        for result in changed:
            with self.subTest(result=result):
                self.assertNotEqual(first.semantic_id, result.semantic_id)

    def test_route_context_state_is_stable_but_mixed_state_is_rejected(self):
        present = self.qualify()
        changed_keys = replace(
            present,
            route_local_issuer_key="0" * 64,
            route_local_security_key="1" * 64,
        )
        absent = replace(
            present,
            route_local_issuer_key=None,
            route_local_security_key=None,
        )
        mixed = replace(present, route_local_issuer_key=None)
        self.assertEqual(present.semantic_id, changed_keys.semantic_id)
        self.assertNotEqual(present.evidence_id, changed_keys.evidence_id)
        self.assertNotEqual(present.semantic_id, absent.semantic_id)
        with self.assertRaises(qualifier.CurrentAnnualAssetsLiabilitiesError):
            _ = mixed.semantic_id

    def test_result_serialization_identity_and_reasons_are_deterministic(self):
        result = self.qualify()
        self.assertEqual(result.semantic_id, result.semantic_id)
        self.assertEqual(result.evidence_id, result.evidence_id)
        self.assertEqual(result.to_dict(), result.to_dict())
        json.dumps(result.to_dict(), sort_keys=True)
        self.assertEqual(result.reasons, tuple(sorted(
            set(result.reasons), key=lambda item: item.value
        )))
        with self.assertRaises(FrozenInstanceError):
            result.assets = Decimal(1)
        with self.assertRaises(FrozenInstanceError):
            result.supporting_filings[0].accession = SECOND_ACCESSION

    def test_current_only_authority_and_closed_limitations_are_pinned(self):
        result = self.qualify()
        self.assertEqual(result.authority, "QUALITY_BALANCE_SHEET_EVIDENCE_ONLY")
        self.assertEqual(
            result.limitations,
            tuple(qualifier.CurrentAnnualAssetsLiabilitiesLimitation),
        )
        values = {item.value for item in result.limitations}
        self.assertEqual(values, {
            "ONLY_US_GAAP_ASSETS",
            "ONLY_US_GAAP_LIABILITIES",
            "NO_TAXONOMY_SUBSTITUTION",
            "NO_LIABILITIES_AS_INTEREST_BEARING_DEBT",
            "NO_ASSETS_AS_INVESTED_CAPITAL",
            "NO_LIABILITIES_ASSETS_RATIO",
            "NO_DEBT_ASSETS",
            "NO_DEBT_EQUITY",
            "NO_NET_DEBT",
            "NO_LEVERAGE_CONCLUSION",
            "NO_LIQUIDITY_OR_CURRENT_RATIO",
            "NO_WORKING_CAPITAL",
            "NO_SOLVENCY",
            "NO_BALANCE_SHEET_STRENGTH",
            "NO_ROA",
            "NO_ROE",
            "NO_ROIC",
            "NO_CAPITAL_ALLOCATION_CONCLUSION",
            "NO_TANGIBLE_BOOK_VALUE",
            "NO_LIQUIDATION_VALUE",
            "NO_HISTORICAL_BALANCE_SHEET_TREND",
            "NO_CROSS_ISSUER_COMPARABILITY",
            "NO_CROSS_SECTOR_COMPARABILITY",
            "NO_DURABILITY_OR_PERSISTENCE_CONCLUSION",
            "NO_CONFIDENCE_EFFECT",
            "NO_EXPECTED_RETURN_EFFECT",
            "NO_QUALITY_SCORE_GRADE_AGGREGATE_OR_WEIGHT",
            "NO_RECOMMENDATION_RANKING_ALLOCATION_OR_SIZING",
            "NO_EXECUTION_PRODUCTION_DEPLOYMENT_OR_V2_PROMOTION_AUTHORITY",
            "NO_HISTORICAL_AS_OF_OR_PIT_AUTHORITY",
        })

    def test_controlled_replay_has_no_network_or_provider_acquisition(self):
        with patch.object(
            socket.socket, "connect", side_effect=AssertionError("network")
        ), patch.object(
            socket, "getaddrinfo", side_effect=AssertionError("network")
        ):
            self.assertIs(
                self.qualify().status,
                qualifier.CurrentAnnualAssetsLiabilitiesStatus.
                PAIRED_ASSETS_LIABILITIES_ESTABLISHED,
            )

    def test_static_imports_and_dependency_boundaries_are_closed(self):
        allowed = {
            "dataclasses", "datetime", "decimal", "enum", "hashlib", "json", "re",
            "economic_facts",
            "economic_facts.sec_archive",
            "economic_facts.sec_current_eps_comparability_qualification",
            "economic_facts.sec_eps_series",
            "economic_facts.sec_assets_liabilities",
            "economic_facts.sec_ordinary_compounder_profile",
        }
        for module in (extraction, qualifier):
            source = Path(module.__file__).read_text()
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    self.assertTrue(all(alias.name in allowed for alias in node.names))
                elif isinstance(node, ast.ImportFrom):
                    name = node.module
                    if node.level:
                        name = "economic_facts." + (name or "")
                    self.assertIn(name.rstrip("."), allowed)
                elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    self.assertNotIn(node.func.id, {"eval", "exec", "__import__", "compile"})
            for token in (
                "requests", "urllib", "sec_acquisition", "expected_return_engine",
                "portfolio", "execution_instruction", "cash_conversion_ratio",
                "quality_score", "analysis_capabilities",
            ):
                self.assertNotIn(token, source)

    def test_model_rules_and_protected_fingerprints_remain_pinned(self):
        checkout = Path(__file__).resolve().parents[1]
        self.assertIn(
            'MODEL_RULES_VERSION = "2026-08-23-allocation-room-integrity-v7"',
            (checkout / "src" / "model_version.py").read_text(),
        )
        self.assertIn(
            "f1e73b27b80e41d96ff5e0fe990b482bad71b7220db0b5bd6a2f470d72786166",
            (checkout / "tests" / "test_pit_adapter_equivalence.py").read_text(),
        )
        self.assertIn(
            "f8457910665391e39c234274cae4c029802c681211eebc7dba986a63000876f1",
            (checkout / "tests" / "test_pit_comparison.py").read_text(),
        )


if __name__ == "__main__":
    unittest.main()
