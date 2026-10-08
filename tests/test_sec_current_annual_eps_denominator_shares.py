"""Adversarial tests for paired CURRENT annual EPS denominator shares."""
import ast
from collections import UserDict
from dataclasses import FrozenInstanceError, fields, replace
from decimal import Decimal
from enum import StrEnum
import inspect
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from economic_facts import sec_current_annual_eps_denominator_shares as qualifier
from economic_facts import sec_eps_denominator_shares as extraction
from economic_facts import sec_ordinary_compounder_profile as profile_module
from economic_facts.sec_archive import ArchiveError, SecArchive
from tests import test_sec_current_eps_comparability_qualification as comparability_tests
from tests.sec_eps_denominator_shares_fixtures import (
    BASIC_VALUE,
    DILUTED_VALUE,
    basic_missing_payload,
    capture_profile,
    coherent_pair_payload,
    companyfacts_payload,
    conflicting_values_payload,
    denominator_row,
    diluted_below_basic_payload,
    diluted_missing_payload,
    duplicate_same_value_payload,
    mismatched_period_payload,
    no_common_accession_payload,
    orphan_basic_conflict_payload,
    quarterly_payload,
    wrong_unit_payload,
)
from tests.sec_filing_fixtures import raw
from tests.sec_property4_temporal_boundary_fixtures import BOUNDARY_T1
from tests.sec_property4_temporal_fixtures import CIK


class SecCurrentAnnualEPSDenominatorSharesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = comparability_tests.SecCurrentEPSComparabilityTests(
            methodName="runTest"
        )
        cls.fixture.setUp()
        cls.receipt, cls.available = capture_profile(cls.fixture)
        _, cls.unavailable = capture_profile(cls.fixture, sic=None, description=None)
        _, cls.unsupported = capture_profile(
            cls.fixture,
            sic=6021,
            description="National Commercial Banks",
        )
        _, cls.source_conflict = capture_profile(
            cls.fixture,
            expected_comparability_semantic_id="0" * 64,
        )

    @classmethod
    def tearDownClass(cls):
        cls.fixture.doCleanups()

    def qualify(self, profile=None, archive=None):
        return qualifier.qualify_sec_current_annual_eps_denominator_shares(
            self.fixture.current_archive if archive is None else archive,
            self.available if profile is None else profile,
        )

    def profile_for(self, payload, *, reverse=False):
        return capture_profile(self.fixture, payload, reverse=reverse)[1]

    def extract(self, payload):
        with tempfile.TemporaryDirectory() as temporary:
            archive = SecArchive(Path(temporary).resolve() / "archive")
            receipt = archive._capture_live(
                raw(payload), cik=CIK, captured_at=BOUNDARY_T1
            )
            return extraction.extract_eps_denominator_shares(
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
                (self.fixture.current_archive,
                 self.available.upstream_comparability),
            )
            for archive, profile in cases:
                with self.subTest(types=(type(archive), type(profile))), \
                        self.assertRaises(
                            qualifier.CurrentAnnualEPSDenominatorSharesError):
                    qualifier.qualify_sec_current_annual_eps_denominator_shares(
                        archive, profile
                    )

    def test_coherent_canonical_pair_establishes_exact_decimal_facts(self):
        result = self.qualify()
        self.assertIs(
            result.status,
            qualifier.CurrentAnnualEPSDenominatorSharesStatus.
            PAIRED_EPS_DENOMINATOR_SHARES_ESTABLISHED,
        )
        self.assertEqual(result.period_start, "2024-01-01")
        self.assertEqual(result.period_end, "2024-12-31")
        self.assertEqual(result.basic_weighted_average_shares,
                         Decimal(BASIC_VALUE))
        self.assertEqual(result.diluted_weighted_average_shares,
                         Decimal(DILUTED_VALUE))
        self.assertIs(type(result.basic_weighted_average_shares), Decimal)
        self.assertIs(type(result.diluted_weighted_average_shares), Decimal)
        self.assertEqual(result.supporting_accessions,
                         ("0000000000-25-000001",))

    def test_profile_capability_states_map_exactly(self):
        cases = (
            (
                self.unavailable,
                qualifier.CurrentAnnualEPSDenominatorSharesStatus.
                EVIDENCE_UNAVAILABLE,
            ),
            (
                self.unsupported,
                qualifier.CurrentAnnualEPSDenominatorSharesStatus.
                EVIDENCE_UNSUPPORTED,
            ),
            (
                self.source_conflict,
                qualifier.CurrentAnnualEPSDenominatorSharesStatus.SOURCE_CONFLICT,
            ),
        )
        for profile, status in cases:
            with self.subTest(status=status):
                result = self.qualify(profile)
                self.assertIs(result.status, status)
                self.assertIsNone(result.basic_weighted_average_shares)
                self.assertIsNone(result.diluted_weighted_average_shares)

    def test_genuine_replay_conflict_is_authenticated_and_projected(self):
        self.assertIs(
            self.source_conflict.status,
            profile_module.OrdinaryCompounderProfileStatus.SOURCE_CONFLICT,
        )
        self.assertEqual(
            self.source_conflict.reasons,
            (profile_module.ProfileReason.REPLAY_IDENTITY_MISMATCH,),
        )
        self.assertNotEqual(
            self.source_conflict.expected_comparability_semantic_id,
            self.source_conflict.upstream_comparability.semantic_id,
        )
        self.assertEqual(
            self.source_conflict.expected_comparability_evidence_id,
            self.source_conflict.upstream_comparability.evidence_id,
        )
        result = self.qualify(self.source_conflict)
        self.assertIs(
            result.status,
            qualifier.CurrentAnnualEPSDenominatorSharesStatus.SOURCE_CONFLICT,
        )

    def test_fabricated_replay_conflict_is_rejected(self):
        fabricated = replace(
            self.available,
            status=profile_module.OrdinaryCompounderProfileStatus.SOURCE_CONFLICT,
            profile=None,
            reasons=(profile_module.ProfileReason.REPLAY_IDENTITY_MISMATCH,),
        )
        self.assertEqual(
            fabricated.expected_comparability_semantic_id,
            fabricated.upstream_comparability.semantic_id,
        )
        self.assertEqual(
            fabricated.expected_comparability_evidence_id,
            fabricated.upstream_comparability.evidence_id,
        )
        with self.assertRaises(
            qualifier.CurrentAnnualEPSDenominatorSharesError
        ):
            self.qualify(fabricated)

    def test_expected_replay_mutation_without_state_update_is_rejected(self):
        mutated = replace(
            self.available,
            expected_comparability_evidence_id="0" * 64,
        )
        with self.assertRaises(
            qualifier.CurrentAnnualEPSDenominatorSharesError
        ):
            self.qualify(mutated)

    def test_v1_profile_contract_is_rejected(self):
        old = replace(
            self.available,
            contract_version=(
                "2026-09-29-sec-ordinary-compounder-method-profile-v1"
            ),
        )
        with self.assertRaises(
            qualifier.CurrentAnnualEPSDenominatorSharesError
        ):
            self.qualify(old)

    def test_unknown_future_profile_state_fails_programming_contract(self):
        with self.assertRaises(
            qualifier.CurrentAnnualEPSDenominatorSharesError
        ):
            self.qualify(replace(self.available, status="FUTURE_STATE"))

    def test_reconstructed_established_profile_requires_canonical_metadata(self):
        cases = (
            replace(self.available, sic=None),
            replace(self.available, sic=True),
            replace(self.available, sic_description=""),
            replace(self.available, sic_description=" Electronic Computers "),
            replace(self.available, metadata_semantic_id=None),
            replace(self.available, metadata_semantic_id="bad"),
            replace(self.available, metadata_evidence_id=None),
            replace(self.available, metadata_evidence_id="bad"),
        )
        for reconstructed in cases:
            with self.subTest(reconstructed=reconstructed), self.assertRaises(
                qualifier.CurrentAnnualEPSDenominatorSharesError
            ):
                self.qualify(reconstructed)

    def test_foreign_equal_string_enums_cannot_masquerade_as_profile_decisions(self):
        class ForeignUnsupportedStructure(StrEnum):
            BANK = "BANK"

        decisions = list(self.available.decisions)
        decisions[0] = replace(
            decisions[0], profile=ForeignUnsupportedStructure.BANK
        )
        reconstructed = replace(self.available, decisions=tuple(decisions))
        with self.assertRaises(
            qualifier.CurrentAnnualEPSDenominatorSharesError
        ):
            self.qualify(reconstructed)

    def test_established_periods_require_distinct_strict_chronology(self):
        periods = list(self.available.upstream_comparability.period_decisions)
        duplicate = periods.copy()
        duplicate[2] = replace(
            duplicate[2],
            period_start=duplicate[1].period_start,
            period_end=duplicate[1].period_end,
        )
        non_strict = periods.copy()
        non_strict[1], non_strict[2] = non_strict[2], non_strict[1]
        for malformed in (duplicate, non_strict):
            reconstructed = replace(
                self.available,
                upstream_comparability=replace(
                    self.available.upstream_comparability,
                    period_decisions=tuple(malformed),
                ),
            )
            with self.subTest(malformed=malformed), self.assertRaises(
                qualifier.CurrentAnnualEPSDenominatorSharesError
            ):
                self.qualify(reconstructed)

    def test_only_exact_reviewed_namespace_and_concepts_are_extracted(self):
        substitutes = (
            "WeightedAverageNumberOfSharesOutstanding",
            "EntityCommonStockSharesOutstanding",
            "CommonStocksIncludingAdditionalPaidInCapital",
        )
        for concept in substitutes:
            payload = coherent_pair_payload()
            facts = payload["facts"]["us-gaap"]
            facts[concept] = facts.pop(extraction.BASIC_CONCEPT)
            with self.subTest(concept=concept):
                result = self.extract(payload)
                self.assertEqual(
                    {item.concept for item in result.observations},
                    {extraction.DILUTED_CONCEPT},
                )
        issuer_extension = self.extract(
            companyfacts_payload(
                include_basic=True,
                issuer_extension_basic=True,
            )
        )
        self.assertEqual(
            {item.concept for item in issuer_extension.observations},
            {extraction.DILUTED_CONCEPT},
        )
        foreign_namespace = coherent_pair_payload()
        foreign_namespace["facts"]["ifrs-full"] = (
            foreign_namespace["facts"].pop("us-gaap")
        )
        self.assertEqual(self.extract(foreign_namespace).observations, ())

    def test_extraction_preserves_source_and_provenance_fields(self):
        original = denominator_row(BASIC_VALUE)
        observation = next(
            item for item in self.extract(coherent_pair_payload()).observations
            if item.concept == extraction.BASIC_CONCEPT
        )
        self.assertEqual(observation.source_cik, CIK)
        self.assertEqual(observation.namespace, "us-gaap")
        self.assertEqual(observation.unit, "shares")
        self.assertEqual(observation.value, Decimal(BASIC_VALUE))
        for field, source_key in (
            ("start", "start"), ("end", "end"), ("fy", "fy"),
            ("fp", "fp"), ("form", "form"), ("filed", "filed"),
            ("accession", "accn"), ("frame", "frame"),
        ):
            self.assertEqual(getattr(observation, field), original[source_key])
        self.assertTrue(observation.source_object_hash)
        self.assertTrue(observation.capture_receipt_id)
        self.assertTrue(observation.source_locator)
        self.assertTrue(observation.semantic_locator)
        self.assertIn("CURRENT_CAPTURE_REPLAY", observation.source_semantics)

    def test_exact_base_ten_precision_is_never_binary_float(self):
        precise = "100000000.12345678901234567890123456789"
        payload = companyfacts_payload(
            basic_rows=[denominator_row(1)],
            diluted_rows=[denominator_row(DILUTED_VALUE)],
        )
        content = raw(payload).replace(b'"val":1,',
                                       ('"val":' + precise + ',').encode(), 1)
        with tempfile.TemporaryDirectory() as temporary:
            archive = SecArchive(Path(temporary).resolve() / "archive")
            receipt = archive._capture_live(
                content, cik=CIK, captured_at=BOUNDARY_T1
            )
            result = extraction.extract_eps_denominator_shares(
                archive.read_object(receipt), receipt
            )
        basic = next(item for item in result.observations
                     if item.concept == extraction.BASIC_CONCEPT)
        self.assertEqual(basic.value, Decimal(precise))
        self.assertIs(type(basic.value), Decimal)

    def test_malformed_source_structures_fail_closed(self):
        malformed = []
        facts_scalar = coherent_pair_payload()
        facts_scalar["facts"] = []
        malformed.append(facts_scalar)
        concept_scalar = coherent_pair_payload()
        concept_scalar["facts"]["us-gaap"][extraction.BASIC_CONCEPT] = []
        malformed.append(concept_scalar)
        units_scalar = coherent_pair_payload()
        units_scalar["facts"]["us-gaap"][extraction.BASIC_CONCEPT]["units"] = []
        malformed.append(units_scalar)
        row_scalar = coherent_pair_payload()
        row_scalar["facts"]["us-gaap"][extraction.BASIC_CONCEPT]["units"]["shares"] = [None]
        malformed.append(row_scalar)
        for payload in malformed:
            with self.subTest(payload=payload), self.assertRaises(ArchiveError):
                self.extract(payload)

    def test_missing_basic_or_diluted_is_unavailable_not_zero(self):
        for payload, reason in (
            (
                basic_missing_payload(),
                qualifier.CurrentAnnualEPSDenominatorSharesReason.
                BASIC_DENOMINATOR_SHARES_UNAVAILABLE,
            ),
            (
                diluted_missing_payload(),
                qualifier.CurrentAnnualEPSDenominatorSharesReason.
                DILUTED_DENOMINATOR_SHARES_UNAVAILABLE,
            ),
        ):
            with self.subTest(reason=reason):
                result = self.qualify(self.profile_for(payload))
                self.assertIs(
                    result.status,
                    qualifier.CurrentAnnualEPSDenominatorSharesStatus.
                    EVIDENCE_UNAVAILABLE,
                )
                self.assertIn(reason, result.reasons)
                self.assertIsNone(result.basic_weighted_average_shares)
                self.assertIsNone(result.diluted_weighted_average_shares)

    def test_unit_must_be_exactly_shares(self):
        result = self.qualify(self.profile_for(wrong_unit_payload()))
        self.assertIs(
            result.status,
            qualifier.CurrentAnnualEPSDenominatorSharesStatus.EVIDENCE_UNAVAILABLE,
        )
        self.assertIn(
            qualifier.CurrentAnnualEPSDenominatorSharesReason.
            EXACT_SHARES_UNIT_UNAVAILABLE,
            result.reasons,
        )

    def test_values_must_be_finite_positive_decimals(self):
        for concept, value in (
            ("basic", 0), ("basic", -1),
            ("diluted", 0), ("diluted", -1),
        ):
            basic = BASIC_VALUE if concept != "basic" else value
            diluted = DILUTED_VALUE if concept != "diluted" else value
            payload = companyfacts_payload(
                basic_rows=[denominator_row(basic)],
                diluted_rows=[denominator_row(diluted)],
            )
            with self.subTest(concept=concept, value=value):
                result = self.qualify(self.profile_for(payload))
                self.assertIs(
                    result.status,
                    qualifier.CurrentAnnualEPSDenominatorSharesStatus.
                    EVIDENCE_UNAVAILABLE,
                )
                self.assertIsNone(result.basic_weighted_average_shares)
                self.assertIsNone(result.diluted_weighted_average_shares)

    def test_quarterly_and_mismatched_period_rows_cannot_establish(self):
        for payload in (quarterly_payload(), mismatched_period_payload()):
            result = self.qualify(self.profile_for(payload))
            with self.subTest(payload=payload):
                self.assertIs(
                    result.status,
                    qualifier.CurrentAnnualEPSDenominatorSharesStatus.
                    EVIDENCE_UNAVAILABLE,
                )
                self.assertIn(
                    qualifier.CurrentAnnualEPSDenominatorSharesReason.
                    EXACT_ANNUAL_PERIOD_PRESENTATION_UNAVAILABLE,
                    result.reasons,
                )

    def test_no_common_annual_filing_accession_is_unavailable(self):
        result = self.qualify(self.profile_for(no_common_accession_payload()))
        self.assertIs(
            result.status,
            qualifier.CurrentAnnualEPSDenominatorSharesStatus.EVIDENCE_UNAVAILABLE,
        )
        self.assertEqual(
            result.reasons,
            (qualifier.CurrentAnnualEPSDenominatorSharesReason.
             NO_COMMON_ANNUAL_FILING_ACCESSION,),
        )

    def test_same_value_duplicate_presentations_are_deterministic(self):
        profile = self.profile_for(duplicate_same_value_payload())
        first = self.qualify(profile)
        second = self.qualify(profile)
        self.assertIs(
            first.status,
            qualifier.CurrentAnnualEPSDenominatorSharesStatus.
            PAIRED_EPS_DENOMINATOR_SHARES_ESTABLISHED,
        )
        self.assertEqual(len(first.supporting_accessions), 2)
        self.assertEqual(first, second)
        self.assertEqual(first.semantic_id, second.semantic_id)
        self.assertEqual(first.evidence_id, second.evidence_id)

    def test_competing_values_are_source_conflict(self):
        result = self.qualify(self.profile_for(conflicting_values_payload()))
        self.assertIs(
            result.status,
            qualifier.CurrentAnnualEPSDenominatorSharesStatus.SOURCE_CONFLICT,
        )
        self.assertIn(
            qualifier.CurrentAnnualEPSDenominatorSharesReason.
            COMPETING_BASIC_DENOMINATOR_VALUES,
            result.reasons,
        )
        self.assertIsNone(result.basic_weighted_average_shares)
        self.assertIsNone(result.diluted_weighted_average_shares)

    def test_orphan_single_concept_conflict_does_not_poison_coherent_pair(self):
        result = self.qualify(self.profile_for(orphan_basic_conflict_payload()))
        self.assertIs(
            result.status,
            qualifier.CurrentAnnualEPSDenominatorSharesStatus.
            PAIRED_EPS_DENOMINATOR_SHARES_ESTABLISHED,
        )
        self.assertEqual(result.basic_weighted_average_shares,
                         Decimal(BASIC_VALUE))
        self.assertEqual(result.diluted_weighted_average_shares,
                         Decimal(DILUTED_VALUE))
        self.assertEqual(result.supporting_accessions,
                         ("0000000000-25-000001",))
        self.assertEqual(len(result.supporting_filings), 1)
        self.assertTrue(all(
            "000099" not in item.accession
            for item in result.supporting_filings
        ))

    def test_common_accession_requires_coherent_intrinsic_filing_metadata(self):
        cases = (
            ({"form": "10-K/A"}, "form"),
            ({"filed": "2025-02-02"}, "filed"),
            ({"fy": 2025}, "fy"),
        )
        for changes, field in cases:
            payload = companyfacts_payload(
                basic_rows=[denominator_row(BASIC_VALUE)],
                diluted_rows=[denominator_row(DILUTED_VALUE, **changes)],
            )
            result = self.qualify(self.profile_for(payload))
            with self.subTest(field=field):
                self.assertIs(
                    result.status,
                    qualifier.CurrentAnnualEPSDenominatorSharesStatus.
                    SOURCE_CONFLICT,
                )
                self.assertEqual(
                    result.reasons,
                    (qualifier.CurrentAnnualEPSDenominatorSharesReason.
                     COMMON_FILING_METADATA_CONFLICT,),
                )

    def test_frame_variation_is_not_a_filing_metadata_conflict(self):
        payload = companyfacts_payload(
            basic_rows=[denominator_row(BASIC_VALUE, frame="CY2024")],
            diluted_rows=[denominator_row(DILUTED_VALUE, frame=None)],
        )
        self.assertIs(
            self.qualify(self.profile_for(payload)).status,
            qualifier.CurrentAnnualEPSDenominatorSharesStatus.
            PAIRED_EPS_DENOMINATOR_SHARES_ESTABLISHED,
        )

    def test_diluted_below_basic_is_accounting_source_conflict(self):
        result = self.qualify(self.profile_for(diluted_below_basic_payload()))
        self.assertIs(
            result.status,
            qualifier.CurrentAnnualEPSDenominatorSharesStatus.SOURCE_CONFLICT,
        )
        self.assertEqual(
            result.reasons,
            (qualifier.CurrentAnnualEPSDenominatorSharesReason.
             DILUTED_SHARES_BELOW_BASIC_SHARES,),
        )

    def test_foreign_cik_and_foreign_archive_fail_closed(self):
        foreign_profile = replace(self.available, source_cik="0000000001")
        with self.assertRaises(
            qualifier.CurrentAnnualEPSDenominatorSharesError
        ):
            self.qualify(foreign_profile)
        with tempfile.TemporaryDirectory() as temporary:
            foreign_archive = SecArchive(Path(temporary).resolve() / "archive")
            detached = self.qualify(archive=foreign_archive)
        self.assertIs(
            detached.status,
            qualifier.CurrentAnnualEPSDenominatorSharesStatus.SOURCE_CONFLICT,
        )
        self.assertIn(
            qualifier.CurrentAnnualEPSDenominatorSharesReason.
            CAPTURE_REPLAY_CONFLICT,
            detached.reasons,
        )

    def test_source_cik_mismatch_is_rejected_by_extraction(self):
        payload = coherent_pair_payload()
        payload["cik"] = 1
        with tempfile.TemporaryDirectory() as temporary:
            archive = SecArchive(Path(temporary).resolve() / "archive")
            receipt = archive._capture_live(
                raw(payload), cik=CIK, captured_at=BOUNDARY_T1
            )
            with self.assertRaises(ArchiveError):
                extraction.extract_eps_denominator_shares(
                    archive.read_object(receipt), receipt
                )

    def test_public_output_has_no_dilution_diagnostic_or_policy_fields(self):
        names = {field.name for field in fields(
            qualifier.CurrentAnnualEPSDenominatorSharesQualification
        )}
        prohibited = {
            "diluted_minus_basic", "difference", "spread", "ratio",
            "percentage", "basis_points", "dilution_rate", "score", "grade",
            "rank", "quality", "confidence", "recommendation", "allocation",
            "sizing", "expected_return", "durability",
        }
        self.assertTrue(names.isdisjoint(prohibited))

    def test_nonestablished_states_never_expose_partial_or_zero_facts(self):
        profiles = (
            self.unavailable,
            self.unsupported,
            self.source_conflict,
            self.profile_for(basic_missing_payload()),
            self.profile_for(diluted_missing_payload()),
            self.profile_for(conflicting_values_payload()),
        )
        for profile in profiles:
            result = self.qualify(profile)
            with self.subTest(status=result.status):
                self.assertIsNone(result.basic_weighted_average_shares)
                self.assertIsNone(result.diluted_weighted_average_shares)
                self.assertEqual(result.selected_basic_observation_ids, ())
                self.assertEqual(result.selected_diluted_observation_ids, ())
                self.assertEqual(result.supporting_accessions, ())
                self.assertEqual(result.supporting_filings, ())

    def test_value_period_status_and_reason_changes_change_semantic_identity(self):
        baseline = self.qualify()
        changed_value = self.qualify(self.profile_for(companyfacts_payload(
            basic_rows=[denominator_row(BASIC_VALUE + 10)],
            diluted_rows=[denominator_row(DILUTED_VALUE + 10)],
        )))
        changed_period = replace(baseline, period_end="2025-12-31")
        unavailable = self.qualify(self.unavailable)
        reason_changed = replace(
            unavailable,
            reasons=(qualifier.CurrentAnnualEPSDenominatorSharesReason.
                     EXACT_ANNUAL_PERIOD_PRESENTATION_UNAVAILABLE,),
        )
        self.assertNotEqual(baseline.semantic_id, changed_value.semantic_id)
        self.assertNotEqual(baseline.semantic_id, changed_period.semantic_id)
        self.assertNotEqual(baseline.semantic_id, unavailable.semantic_id)
        self.assertNotEqual(unavailable.semantic_id, reason_changed.semantic_id)

    def test_equivalent_decimal_values_have_one_semantic_representation(self):
        baseline = self.qualify()
        variants = tuple(
            replace(
                baseline,
                basic_weighted_average_shares=value,
                diluted_weighted_average_shares=value,
            )
            for value in (
                Decimal("100"), Decimal("100.0"), Decimal("100.00"),
                Decimal("1E+2"),
            )
        )
        self.assertEqual(
            {item.semantic_id for item in variants},
            {variants[0].semantic_id},
        )
        self.assertEqual(
            qualifier._canonical(Decimal("100")),
            qualifier._canonical(Decimal("100.00")),
        )
        self.assertEqual(
            qualifier._canonical(Decimal("100")),
            qualifier._canonical(Decimal("1E+2")),
        )
        self.assertEqual(
            qualifier._canonical(Decimal("0")),
            qualifier._canonical(Decimal("-0.000")),
        )
        changed = replace(
            variants[0],
            basic_weighted_average_shares=Decimal("100.01"),
            diluted_weighted_average_shares=Decimal("100.01"),
        )
        self.assertNotEqual(variants[0].semantic_id, changed.semantic_id)

    def test_reversed_equivalent_source_evidence_order_preserves_semantic_id(self):
        profile = self.profile_for(companyfacts_payload(
            basic_rows=[
                denominator_row(BASIC_VALUE),
                denominator_row(BASIC_VALUE),
            ],
            diluted_rows=[
                denominator_row(DILUTED_VALUE),
                denominator_row(DILUTED_VALUE),
            ],
        ))
        result = self.qualify(profile)
        reversed_evidence = replace(
            result,
            selected_basic_observation_ids=tuple(
                reversed(result.selected_basic_observation_ids)
            ),
            selected_diluted_observation_ids=tuple(
                reversed(result.selected_diluted_observation_ids)
            ),
        )
        self.assertEqual(result.semantic_id, reversed_evidence.semantic_id)

    def test_evidence_only_recapture_preserves_semantics_and_changes_evidence(self):
        first = self.qualify()
        recaptured = replace(
            first,
            upstream_profile_evidence_id="f" * 64,
            upstream_comparability_evidence_id="e" * 64,
            capture_receipt_id="d" * 64,
            source_object_hash="c" * 64,
            selected_basic_observation_ids=("b" * 64,),
            selected_diluted_observation_ids=("a" * 64,),
        )
        self.assertEqual(first.semantic_id, recaptured.semantic_id)
        self.assertNotEqual(first.evidence_id, recaptured.evidence_id)

    def test_result_and_supporting_provenance_are_immutable(self):
        result = self.qualify()
        with self.assertRaises(FrozenInstanceError):
            result.status = (
                qualifier.CurrentAnnualEPSDenominatorSharesStatus.
                EVIDENCE_UNAVAILABLE
            )
        with self.assertRaises(FrozenInstanceError):
            result.supporting_filings[0].accession = "changed"

    def test_repeated_serialization_and_identity_are_deterministic(self):
        result = self.qualify()
        first = json.dumps(result.to_dict(), sort_keys=True, separators=(",", ":"))
        second = json.dumps(result.to_dict(), sort_keys=True, separators=(",", ":"))
        self.assertEqual(first, second)
        self.assertEqual(result.semantic_id, result.semantic_id)
        self.assertEqual(result.evidence_id, result.evidence_id)

    def test_current_only_authority_and_evidence_limitations_are_pinned(self):
        result = self.qualify()
        self.assertEqual(
            result.authority,
            "QUALITY_DILUTION_EPS_DENOMINATOR_EVIDENCE_ONLY",
        )
        self.assertEqual(
            result.limitations,
            tuple(qualifier.CurrentAnnualEPSDenominatorSharesLimitation),
        )
        values = tuple(item.value for item in result.limitations)
        self.assertIn("NO_HISTORICAL_AS_OF_OR_PIT_AUTHORITY", values)
        self.assertIn("NO_DILUTION_QUALITY_CONCLUSION", values)
        self.assertIn("NO_SBC_CAUSAL_ATTRIBUTION", values)
        self.assertIn("NO_PERIOD_END_SHARES_OUTSTANDING_CLAIM", values)
        self.assertIn("NO_EXPECTED_RETURN_EFFECT", values)
        self.assertIn("NO_CONFIDENCE_CONCLUSION", values)

    def test_controlled_archive_replay_has_no_network_or_provider_acquisition(self):
        with patch.object(
            socket.socket, "connect", side_effect=AssertionError("network")
        ), patch.object(
            socket, "getaddrinfo", side_effect=AssertionError("network")
        ):
            self.assertIs(
                self.qualify().status,
                qualifier.CurrentAnnualEPSDenominatorSharesStatus.
                PAIRED_EPS_DENOMINATOR_SHARES_ESTABLISHED,
            )

    def test_static_imports_and_dependency_boundaries_are_closed(self):
        allowed = {
            "dataclasses", "datetime", "decimal", "enum", "hashlib", "json",
            "re",
            "economic_facts",
            "economic_facts.sec_archive",
            "economic_facts.sec_current_eps_comparability_qualification",
            "economic_facts.sec_eps_denominator_shares",
            "economic_facts.sec_eps_series",
            "economic_facts.sec_ordinary_compounder_profile",
        }
        for module in (extraction, qualifier):
            source = Path(module.__file__).read_text()
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    self.assertTrue(all(alias.name in allowed
                                        for alias in node.names))
                elif isinstance(node, ast.ImportFrom):
                    name = node.module
                    if node.level:
                        name = "economic_facts." + (name or "")
                    self.assertIn(name.rstrip("."), allowed)
                elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    self.assertNotIn(node.func.id,
                                     {"eval", "exec", "__import__", "compile"})
            for token in (
                "analysis_capabilities", "expected_return_engine",
                "vfv_forward_expected_return", "bounded_confidence_projection",
                "portfolio", "execution_instruction", "cagr_quality_engine",
                "cash_flow_quality_engine", "decision_quality_engine",
                "quality_drawdown_engine", "shareholder_return_engine",
                "shareholder_discipline_engine", "safe_float", "clamp",
                "requests", "urllib", "sec_acquisition",
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

    def test_representative_identities_are_pinned(self):
        cases = (
            self.qualify(),
            self.qualify(self.unavailable),
            self.qualify(self.unsupported),
            self.qualify(self.source_conflict),
        )
        expected = (
            (
                "b947644797cea4252f420d059107b113a5da6bec4efd6b7abde44986c2409096",
                "5a507cfbb0771260f8b8d5368d488d2859bc2202ada6c27d0b8fe3984e8580f6",
            ),
            (
                "0bce0315a396ebb7a85f1decb15176ef8ec4f06fea0cf8dccba27db009e4ba3d",
                "65b4985b7464d4fd3f070b4d8e0d8ada144f48ff7154172f1ece07421a582fd7",
            ),
            (
                "af71b35679077f8b30e06a22ca961bfcfc5fa5e62ce1af5215442151e22d08db",
                "3add0704659e03b82e244884bcee85c385746f09054d79e70eaf9e1571a96c84",
            ),
            (
                "e19661d711b2a67321054d9f0056fa71645ef67f0e0bc3a91b511431b1aba2ff",
                "2be72640253d93524b100880fa670fe65723d37aa9c358b4a4278d14f0a9f096",
            ),
        )
        for result, (semantic_id, evidence_id) in zip(cases, expected, strict=True):
            with self.subTest(status=result.status):
                self.assertEqual(result.semantic_id, semantic_id)
                self.assertEqual(result.evidence_id, evidence_id)


if __name__ == "__main__":
    unittest.main()
