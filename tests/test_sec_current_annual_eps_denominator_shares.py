"""Adversarial tests for paired CURRENT annual EPS denominator shares."""
import ast
from collections import UserDict
from dataclasses import FrozenInstanceError, fields, replace
from decimal import Decimal
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
        cls.source_conflict = replace(
            cls.available,
            status=profile_module.OrdinaryCompounderProfileStatus.SOURCE_CONFLICT,
            reasons=(profile_module.ProfileReason.REPLAY_IDENTITY_MISMATCH,),
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

    def test_unknown_future_profile_state_fails_programming_contract(self):
        with self.assertRaises(
            qualifier.CurrentAnnualEPSDenominatorSharesError
        ):
            self.qualify(replace(self.available, status="FUTURE_STATE"))

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
        result = self.qualify(foreign_profile)
        self.assertIs(
            result.status,
            qualifier.CurrentAnnualEPSDenominatorSharesStatus.SOURCE_CONFLICT,
        )
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
                "c2cbcf83d214d9f060f15063c376f9923a0ca0a2e8ee4f23cd8926f2a325d8e3",
                "79719e4b56414f065dee4b60f7fa5fc254813e22a8271b49c3fb605fae98a109",
            ),
            (
                "874f435abcf60a1af1f0192f629376c15e42d98403897a0837e0a7cca8f679cf",
                "b62335d6f3d276c20fa45c465bd7c9ce2916952ae8ad7fb03834894451492f46",
            ),
            (
                "b63119f0c685335955b889fc5c6661575ca5583fabe11fb9096d6727d5853317",
                "52a2972efe563340fefe7c83d235fa30e8dacb5fd3c160b07cc03959a3f043e0",
            ),
            (
                "53d14bcb38640d1e6527145e6c3eeeb27e3b761eb1855f09e7dc3d5bb0c75dc4",
                "3ab67fc302a06d7e6c8eae18e0a940777a584c49f83f0c061d884647c7a06d63",
            ),
        )
        for result, (semantic_id, evidence_id) in zip(cases, expected, strict=True):
            with self.subTest(status=result.status):
                self.assertEqual(result.semantic_id, semantic_id)
                self.assertEqual(result.evidence_id, evidence_id)


if __name__ == "__main__":
    unittest.main()
