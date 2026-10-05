"""Adversarial tests for the bounded annual denominator-dilution diagnostic."""
import ast
import builtins
from collections import UserDict
from dataclasses import FrozenInstanceError, dataclass, fields, replace
from decimal import Decimal, localcontext
from enum import StrEnum
import json
from pathlib import Path
import socket
import time
import unittest
from unittest.mock import patch

from economic_facts import sec_current_annual_eps_denominator_shares as upstream
from economic_facts import sec_ordinary_compounder_profile as profile_module
from src import current_annual_eps_denominator_dilution as dilution
from tests import test_sec_current_eps_comparability_qualification as comparability_tests
from tests.sec_eps_denominator_shares_fixtures import capture_profile


class CurrentAnnualEPSDenominatorDilutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = comparability_tests.SecCurrentEPSComparabilityTests(
            methodName="runTest"
        )
        cls.fixture.setUp()
        _, cls.available_profile = capture_profile(cls.fixture)
        _, unavailable_profile = capture_profile(
            cls.fixture, sic=None, description=None
        )
        _, unsupported_profile = capture_profile(
            cls.fixture, sic=6021, description="National Commercial Banks"
        )
        source_conflict_profile = replace(
            cls.available_profile,
            status=profile_module.OrdinaryCompounderProfileStatus.SOURCE_CONFLICT,
            reasons=(profile_module.ProfileReason.REPLAY_IDENTITY_MISMATCH,),
        )
        cls.available = cls.qualify(cls.available_profile)
        cls.unavailable = cls.qualify(unavailable_profile)
        cls.unsupported = cls.qualify(unsupported_profile)
        cls.source_conflict = cls.qualify(source_conflict_profile)

    @classmethod
    def tearDownClass(cls):
        cls.fixture.doCleanups()

    @classmethod
    def qualify(cls, profile):
        return upstream.qualify_sec_current_annual_eps_denominator_shares(
            cls.fixture.current_archive, profile
        )

    def analyze(self, value=None):
        return dilution.analyze_current_annual_eps_denominator_dilution(
            self.available if value is None else value
        )

    def with_values(self, basic, diluted):
        return replace(
            self.available,
            basic_weighted_average_shares=Decimal(basic),
            diluted_weighted_average_shares=Decimal(diluted),
        )

    def test_exact_runtime_input_type_only(self):
        class Subclass(
            upstream.CurrentAnnualEPSDenominatorSharesQualification
        ):
            pass

        subclass = Subclass(*(
            getattr(self.available, field.name)
            for field in fields(self.available)
        ))

        @dataclass(frozen=True)
        class ForeignQualification:
            status: object

        for value in (
                {}, UserDict(), subclass,
                ForeignQualification(self.available.status),
                self.available_profile, object(),
        ):
            with self.subTest(value_type=type(value)), self.assertRaises(
                    dilution.CurrentAnnualEPSDenominatorDilutionError):
                self.analyze(value)

    def test_coherent_established_evidence_is_available(self):
        result = self.analyze()
        self.assertIs(
            result.analysis_kind,
            dilution.CurrentAnnualEPSDenominatorDilutionAnalysisKind.
            CURRENT_ANNUAL_EPS_DENOMINATOR_DILUTION,
        )
        self.assertIs(
            result.status,
            dilution.CurrentAnnualEPSDenominatorDilutionStatus.AVAILABLE,
        )
        self.assertIs(result.upstream_status, self.available.status)
        self.assertIs(result.upstream_reasons, self.available.reasons)
        self.assertEqual(result.period_start, self.available.period_start)
        self.assertEqual(result.period_end, self.available.period_end)
        self.assertEqual(
            result.incremental_denominator_ratio,
            dilution.EPSDenominatorDilutionRatio(1, 20),
        )

    def test_zero_ratio_is_exactly_zero_over_one_and_remains_available(self):
        result = self.analyze(self.with_values("100", "100.000"))
        self.assertIs(
            result.status,
            dilution.CurrentAnnualEPSDenominatorDilutionStatus.AVAILABLE,
        )
        self.assertEqual(
            result.incremental_denominator_ratio,
            dilution.EPSDenominatorDilutionRatio(0, 1),
        )

    def test_positive_ratios_are_exact_reduced_and_unlabelled(self):
        cases = (
            ("1000000", "1000001", (1, 1000000)),
            ("100", "175", (3, 4)),
            ("3", "4", (1, 3)),
        )
        for basic, diluted_shares, expected in cases:
            with self.subTest(values=(basic, diluted_shares)):
                result = self.analyze(self.with_values(basic, diluted_shares))
                ratio = result.incremental_denominator_ratio
                self.assertEqual(
                    (ratio.numerator, ratio.denominator), expected
                )
                self.assertFalse(any(
                    token in field.name
                    for field in fields(type(result))
                    for token in ("label", "grade", "score", "threshold")
                ))

    def test_equivalent_decimal_representations_preserve_ratio_semantics(self):
        cases = (
            self.with_values("3", "4"),
            self.with_values("3.0", "4.00"),
            self.with_values("3E+0", "0.4E+1"),
        )
        results = tuple(self.analyze(item) for item in cases)
        self.assertEqual(
            {item.incremental_denominator_ratio for item in results},
            {dilution.EPSDenominatorDilutionRatio(1, 3)},
        )
        self.assertEqual(len({item.semantic_id for item in results}), 1)

    def test_ratio_is_independent_of_decimal_context_and_never_uses_float(self):
        with localcontext() as context, patch.object(
            builtins, "float", side_effect=AssertionError("float forbidden")
        ):
            context.prec = 1
            result = self.analyze(self.with_values("3", "4"))
        self.assertEqual(
            result.incremental_denominator_ratio,
            dilution.EPSDenominatorDilutionRatio(1, 3),
        )

    def test_capability_states_map_exactly_without_partial_ratio(self):
        cases = (
            (
                self.unavailable,
                dilution.CurrentAnnualEPSDenominatorDilutionStatus.UNAVAILABLE,
            ),
            (
                self.unsupported,
                dilution.CurrentAnnualEPSDenominatorDilutionStatus.UNSUPPORTED,
            ),
            (
                self.source_conflict,
                dilution.CurrentAnnualEPSDenominatorDilutionStatus.
                SOURCE_CONFLICT,
            ),
        )
        for value, expected in cases:
            with self.subTest(status=value.status):
                result = self.analyze(value)
                self.assertIs(result.status, expected)
                self.assertIs(result.upstream_status, value.status)
                self.assertIs(result.upstream_reasons, value.reasons)
                self.assertIsNone(result.incremental_denominator_ratio)

    def test_unknown_future_upstream_state_is_programming_error(self):
        with self.assertRaises(
            dilution.CurrentAnnualEPSDenominatorDilutionError
        ):
            self.analyze(replace(self.available, status="FUTURE_STATE"))

    def test_established_values_must_be_exact_finite_positive_decimals(self):
        malformed = (
            (None, Decimal("4")),
            (0, Decimal("4")),
            (Decimal("0"), Decimal("4")),
            (Decimal("-1"), Decimal("4")),
            (Decimal("NaN"), Decimal("4")),
            (Decimal("Infinity"), Decimal("4")),
            (Decimal("3"), None),
            (Decimal("3"), 4.0),
            (Decimal("3"), Decimal("0")),
            (Decimal("3"), Decimal("-1")),
            (Decimal("3"), Decimal("NaN")),
            (Decimal("3"), Decimal("Infinity")),
            (Decimal("4"), Decimal("3")),
        )
        for basic, diluted_shares in malformed:
            with self.subTest(values=(basic, diluted_shares)), self.assertRaises(
                    dilution.CurrentAnnualEPSDenominatorDilutionError):
                self.analyze(replace(
                    self.available,
                    basic_weighted_average_shares=basic,
                    diluted_weighted_average_shares=diluted_shares,
                ))

    def test_established_contract_authority_and_limitations_are_closed(self):
        cases = (
            replace(self.available, contract_version="wrong"),
            replace(self.available, qualifier_version="wrong"),
            replace(self.available, evidence_kind="wrong"),
            replace(self.available, accounting_namespace="ifrs-full"),
            replace(self.available, accounting_basis="IFRS"),
            replace(self.available, basic_concept="wrong"),
            replace(self.available, diluted_concept="wrong"),
            replace(self.available, unit="USD"),
            replace(self.available, authority="wrong"),
            replace(self.available, limitations=self.available.limitations[:-1]),
        )
        for value in cases:
            with self.subTest(value=value), self.assertRaises(
                    dilution.CurrentAnnualEPSDenominatorDilutionError):
                self.analyze(value)

    def test_established_native_state_and_reasons_must_be_canonical(self):
        class ForeignReason(StrEnum):
            VALUE = "VALUE"

        cases = (
            replace(
                self.available,
                reasons=(
                    upstream.CurrentAnnualEPSDenominatorSharesReason.
                    SOURCE_CIK_CONFLICT,
                ),
            ),
            replace(self.available, reasons=(ForeignReason.VALUE,)),
            replace(
                self.available,
                upstream_profile_status="ESTABLISHED",
            ),
            replace(
                self.available,
                upstream_profile_reasons=(
                    profile_module.ProfileReason.REPLAY_IDENTITY_MISMATCH,
                ),
            ),
        )
        for value in cases:
            with self.subTest(value=value), self.assertRaises(
                    dilution.CurrentAnnualEPSDenominatorDilutionError):
                self.analyze(value)

    def test_established_route_cik_period_and_ids_must_be_valid(self):
        cases = (
            replace(self.available, route_local_issuer_key=None),
            replace(self.available, route_local_issuer_key="bad"),
            replace(self.available, route_local_security_key=None),
            replace(self.available, route_local_security_key="g" * 64),
            replace(self.available, source_cik=None),
            replace(self.available, source_cik="123"),
            replace(self.available, period_start=None),
            replace(self.available, period_start="2024-13-01"),
            replace(self.available, period_start="2025-01-01"),
            replace(self.available, upstream_profile_semantic_id="bad"),
            replace(self.available, upstream_comparability_semantic_id="bad"),
            replace(self.available, upstream_profile_evidence_id="bad"),
            replace(self.available, upstream_comparability_evidence_id="bad"),
        )
        for value in cases:
            with self.subTest(value=value), self.assertRaises(
                    dilution.CurrentAnnualEPSDenominatorDilutionError):
                self.analyze(value)

    def test_established_provenance_must_be_coherent_and_nonempty(self):
        filing = self.available.supporting_filings[0]
        cases = (
            replace(self.available, capture_receipt_id=None),
            replace(self.available, source_object_hash=None),
            replace(self.available, captured_at=None),
            replace(self.available, captured_at="not-a-timestamp"),
            replace(self.available, captured_at="2026-10-04T12:00:00"),
            replace(self.available, capture_source_locator=None),
            replace(self.available, capture_source_locator=" locator "),
            replace(self.available, selected_basic_observation_ids=()),
            replace(self.available, selected_diluted_observation_ids=()),
            replace(self.available, supporting_accessions=()),
            replace(self.available, supporting_filings=()),
            replace(
                self.available,
                supporting_filings=(replace(filing, accession="bad"),),
            ),
            replace(
                self.available,
                supporting_filings=(
                    replace(filing, basic_observation_ids=("a" * 64,)),
                ),
            ),
        )
        for value in cases:
            with self.subTest(value=value), self.assertRaises(
                    dilution.CurrentAnnualEPSDenominatorDilutionError):
                self.analyze(value)

    def test_established_supporting_provenance_is_an_exact_partition(self):
        filing = self.available.supporting_filings[0]
        second_accession = "0000000000-25-000002"
        second_filing = replace(filing, accession=second_accession)
        extra_id = "0" * 64
        basic_with_extra = tuple(sorted(
            self.available.selected_basic_observation_ids + (extra_id,)
        ))
        filing_basic_with_extra = tuple(sorted(
            filing.basic_observation_ids + (extra_id,)
        ))
        cross_concept_filing = replace(
            filing,
            diluted_observation_ids=filing.basic_observation_ids,
        )
        cases = (
            replace(
                self.available,
                supporting_filings=(replace(
                    filing, forms=("10-K", "10-K/A")
                ),),
            ),
            replace(
                self.available,
                supporting_filings=(replace(
                    filing, filed_dates=("2025-02-01", "2025-02-02")
                ),),
            ),
            replace(
                self.available,
                supporting_accessions=(filing.accession, second_accession),
                supporting_filings=(filing, second_filing),
            ),
            replace(
                self.available,
                supporting_accessions=(filing.accession, second_accession),
                supporting_filings=(filing, second_filing),
            ),
            replace(
                self.available,
                selected_diluted_observation_ids=(
                    self.available.selected_basic_observation_ids
                ),
                supporting_filings=(cross_concept_filing,),
            ),
            replace(
                self.available,
                supporting_filings=(replace(
                    filing, basic_observation_ids=filing_basic_with_extra
                ),),
            ),
            replace(
                self.available,
                selected_basic_observation_ids=basic_with_extra,
            ),
        )
        labels = (
            "two forms",
            "two filed dates",
            "basic ID reused across accessions",
            "diluted ID reused across accessions",
            "basic/diluted concept overlap",
            "extra filing-level basic ID",
            "missing filing-level basic ID",
        )
        for label, value in zip(labels, cases, strict=True):
            if label == "basic ID reused across accessions":
                value = replace(
                    value,
                    supporting_filings=(
                        filing,
                        replace(second_filing, diluted_observation_ids=(
                            "1" * 64,
                        )),
                    ),
                    selected_diluted_observation_ids=tuple(sorted(
                        filing.diluted_observation_ids + ("1" * 64,)
                    )),
                )
            elif label == "diluted ID reused across accessions":
                value = replace(
                    value,
                    supporting_filings=(
                        filing,
                        replace(second_filing, basic_observation_ids=(
                            "2" * 64,
                        )),
                    ),
                    selected_basic_observation_ids=tuple(sorted(
                        filing.basic_observation_ids + ("2" * 64,)
                    )),
                )
            with self.subTest(case=label), self.assertRaises(
                    dilution.CurrentAnnualEPSDenominatorDilutionError):
                self.analyze(value)

    def test_non_available_status_reason_and_profile_paths_are_canonical(self):
        denominator_reason = upstream.CurrentAnnualEPSDenominatorSharesReason
        denominator_status = upstream.CurrentAnnualEPSDenominatorSharesStatus
        profile_status = profile_module.OrdinaryCompounderProfileStatus
        profile_reason = profile_module.ProfileReason
        cases = (
            replace(
                self.unavailable,
                reasons=(denominator_reason.UPSTREAM_PROFILE_UNSUPPORTED,),
                upstream_profile_status=profile_status.PROFILE_UNSUPPORTED,
                upstream_profile_reasons=(
                    profile_reason.UNSUPPORTED_SIC_PROFILE,
                ),
            ),
            replace(
                self.unavailable,
                reasons=(denominator_reason.SOURCE_CIK_CONFLICT,),
                upstream_profile_status=(
                    profile_status.ORDINARY_COMPOUNDER_PROFILE_ESTABLISHED
                ),
                upstream_profile_reasons=(),
            ),
            replace(
                self.unsupported,
                reasons=(
                    denominator_reason.BASIC_DENOMINATOR_SHARES_UNAVAILABLE,
                ),
            ),
            replace(
                self.source_conflict,
                reasons=(denominator_reason.NO_COMMON_ANNUAL_FILING_ACCESSION,),
            ),
            replace(
                self.unavailable,
                upstream_profile_status=profile_status.PROFILE_UNSUPPORTED,
                upstream_profile_reasons=(
                    profile_reason.UNSUPPORTED_SIC_PROFILE,
                ),
            ),
            replace(
                self.unsupported,
                upstream_profile_status=profile_status.PROFILE_UNAVAILABLE,
                upstream_profile_reasons=(
                    profile_reason.SIC_MISSING_OR_INVALID,
                ),
            ),
            replace(
                self.source_conflict,
                upstream_profile_status=(
                    profile_status.ORDINARY_COMPOUNDER_PROFILE_ESTABLISHED
                ),
                upstream_profile_reasons=(),
            ),
            replace(
                self.unavailable,
                reasons=(
                    denominator_reason.BASIC_DENOMINATOR_SHARES_UNAVAILABLE,
                ),
            ),
            replace(
                self.source_conflict,
                reasons=(denominator_reason.SOURCE_CIK_CONFLICT,),
            ),
            replace(
                self.unavailable,
                reasons=(
                    denominator_reason.BASIC_DENOMINATOR_SHARES_UNAVAILABLE,
                ),
                upstream_profile_status=(
                    profile_status.ORDINARY_COMPOUNDER_PROFILE_ESTABLISHED
                ),
                upstream_profile_reasons=(
                    profile_reason.SIC_MISSING_OR_INVALID,
                ),
            ),
            replace(
                self.source_conflict,
                reasons=(denominator_reason.SOURCE_CIK_CONFLICT,),
                upstream_profile_status=(
                    profile_status.ORDINARY_COMPOUNDER_PROFILE_ESTABLISHED
                ),
                upstream_profile_reasons=(
                    profile_reason.REPLAY_IDENTITY_MISMATCH,
                ),
            ),
        )
        labels = (
            "unavailable with unsupported reason",
            "unavailable with conflict reason",
            "unsupported with unavailable reason",
            "conflict with unavailable reason",
            "profile-unavailable reason with unsupported profile",
            "profile-unsupported reason with unavailable profile",
            "profile-conflict reason with established profile",
            "local unavailable with non-established profile",
            "local conflict with non-established profile",
            "local unavailable with native profile reasons",
            "local conflict with native profile reasons",
        )
        for label, value in zip(labels, cases, strict=True):
            with self.subTest(case=label), self.assertRaises(
                    dilution.CurrentAnnualEPSDenominatorDilutionError):
                self.analyze(value)

        multi_reason_conflict = replace(
            self.source_conflict,
            status=denominator_status.SOURCE_CONFLICT,
            reasons=(
                denominator_reason.COMPETING_BASIC_DENOMINATOR_VALUES,
                denominator_reason.COMPETING_DILUTED_DENOMINATOR_VALUES,
            ),
            upstream_profile_status=(
                profile_status.ORDINARY_COMPOUNDER_PROFILE_ESTABLISHED
            ),
            upstream_profile_reasons=(),
        )
        result = self.analyze(multi_reason_conflict)
        self.assertIs(
            result.status,
            dilution.CurrentAnnualEPSDenominatorDilutionStatus.SOURCE_CONFLICT,
        )
        self.assertIsNone(result.incremental_denominator_ratio)

    def test_non_established_states_cannot_smuggle_numeric_or_partial_output(self):
        cases = (
            replace(
                self.unavailable,
                basic_weighted_average_shares=Decimal("100"),
            ),
            replace(self.unsupported, reasons=()),
            replace(
                self.source_conflict,
                selected_basic_observation_ids=("a" * 64,),
            ),
        )
        for value in cases:
            with self.subTest(value=value), self.assertRaises(
                    dilution.CurrentAnnualEPSDenominatorDilutionError):
                self.analyze(value)

    def test_ratio_constructor_requires_canonical_reduced_pair(self):
        valid = (
            dilution.EPSDenominatorDilutionRatio(0, 17),
            dilution.EPSDenominatorDilutionRatio(2, 6),
            dilution.EPSDenominatorDilutionRatio(9, 12),
        )
        self.assertEqual(
            tuple((item.numerator, item.denominator) for item in valid),
            ((0, 1), (1, 3), (3, 4)),
        )
        for numerator, denominator in (
                (-1, 3), (1, 0), (1, -3),
                (True, 1), (1, True), (1.0, 2), (1, 2.0),
        ):
            with self.subTest(pair=(numerator, denominator)), self.assertRaises(
                    dilution.CurrentAnnualEPSDenominatorDilutionError):
                dilution.EPSDenominatorDilutionRatio(numerator, denominator)

    def test_result_and_ratio_are_immutable(self):
        result = self.analyze(self.with_values("3", "4"))
        with self.assertRaises(FrozenInstanceError):
            result.status = (
                dilution.CurrentAnnualEPSDenominatorDilutionStatus.UNAVAILABLE
            )
        with self.assertRaises(FrozenInstanceError):
            result.incremental_denominator_ratio.numerator = 2

    def test_serialization_and_identity_are_deterministic(self):
        result = self.analyze(self.with_values("3", "4"))
        first = json.dumps(
            result.to_dict(), sort_keys=True, separators=(",", ":")
        )
        second = json.dumps(
            result.to_dict(), sort_keys=True, separators=(",", ":")
        )
        self.assertEqual(first, second)
        self.assertEqual(result.semantic_id, result.semantic_id)
        self.assertEqual(result.evidence_id, result.evidence_id)

    def test_semantic_identity_changes_with_economic_ratio(self):
        baseline = self.analyze(self.with_values("100", "101"))
        changed = self.analyze(self.with_values("100", "102"))
        self.assertNotEqual(baseline.semantic_id, changed.semantic_id)
        self.assertNotEqual(baseline.evidence_id, changed.evidence_id)

    def test_evidence_only_recapture_preserves_semantics_changes_evidence(self):
        baseline = self.analyze()
        recaptured = replace(
            self.available,
            capture_receipt_id="a" * 64,
            source_object_hash="b" * 64,
            captured_at="2026-10-04T12:00:00+00:00",
            capture_source_locator="https://example.invalid/recapture",
        )
        changed = self.analyze(recaptured)
        self.assertEqual(
            baseline.upstream_denominator_qualification_semantic_id,
            changed.upstream_denominator_qualification_semantic_id,
        )
        self.assertNotEqual(
            baseline.upstream_denominator_qualification_evidence_id,
            changed.upstream_denominator_qualification_evidence_id,
        )
        self.assertEqual(baseline.semantic_id, changed.semantic_id)
        self.assertNotEqual(baseline.evidence_id, changed.evidence_id)

    def test_public_result_and_ratio_surfaces_are_exactly_bounded(self):
        self.assertEqual(
            tuple(field.name for field in fields(
                dilution.EPSDenominatorDilutionRatio
            )),
            ("numerator", "denominator"),
        )
        self.assertEqual(
            tuple(field.name for field in fields(
                dilution.CurrentAnnualEPSDenominatorDilutionResult
            )),
            (
                "contract_version", "methodology_version", "analysis_kind",
                "status", "upstream_status", "upstream_reasons",
                "route_local_issuer_key", "route_local_security_key",
                "source_cik", "period_start", "period_end",
                "upstream_denominator_qualification_semantic_id",
                "upstream_denominator_qualification_evidence_id",
                "incremental_denominator_ratio", "authority", "limitations",
            ),
        )
        prohibited = {
            "absolute_difference", "percentage", "basis_points", "score",
            "grade", "rank", "threshold", "confidence", "recommendation",
            "allocation", "sizing", "basic_weighted_average_shares",
            "diluted_weighted_average_shares",
        }
        self.assertTrue(prohibited.isdisjoint(
            field.name for field in fields(
                dilution.CurrentAnnualEPSDenominatorDilutionResult
            )
        ))

    def test_authority_and_limitations_are_pinned(self):
        result = self.analyze()
        self.assertIs(
            result.authority,
            dilution.CurrentAnnualEPSDenominatorDilutionAuthority.
            QUALITY_DILUTION_EPS_DENOMINATOR_DIAGNOSTIC_ONLY,
        )
        self.assertEqual(
            result.limitations,
            tuple(dilution.CurrentAnnualEPSDenominatorDilutionLimitation),
        )
        self.assertEqual(len(result.limitations), 18)

    def test_runtime_has_no_acquisition_clock_or_filesystem_dependency(self):
        with patch.object(socket, "socket", side_effect=AssertionError), \
                patch.object(time, "time", side_effect=AssertionError), \
                patch.object(builtins, "open", side_effect=AssertionError):
            self.assertIsNotNone(
                self.analyze().incremental_denominator_ratio
            )

    def test_static_dependency_boundary_and_cross_pillar_isolation(self):
        source = Path(dilution.__file__).read_text()
        tree = ast.parse(source)
        allowed = {
            "__future__", "dataclasses", "datetime", "decimal", "enum",
            "math", "hashlib", "json", "re", "sys",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                self.assertTrue(all(alias.name in allowed
                                    for alias in node.names))
            elif isinstance(node, ast.ImportFrom):
                self.assertIn(node.module, allowed)
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                self.assertNotIn(
                    node.func.id, {"eval", "exec", "__import__", "compile"}
                )
        for token in (
            "five_period_eps_consistency", "expected_return_engine",
            "vfv_forward_expected_return", "bounded_confidence_projection",
            "portfolio_engine", "portfolio_room", "execution_instruction",
            "QualityScore",
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
            self.analyze(self.with_values("100", "101")),
            self.analyze(self.with_values("100", "100")),
            self.analyze(self.unavailable),
            self.analyze(self.unsupported),
            self.analyze(self.source_conflict),
        )
        expected = (
            (
                "da39895afa5a8089725a0a04d0ea957d2e3705bc77567c7aef5ebd4ca186b150",
                "808dd6acfe7d9a70313379a16b3b9ef5951df45db229fce71260e023a846f7de",
            ),
            (
                "cfb847259ac5452ccb87719fd1e43e0f9b5a5f4d35fd8e521db3a01936d0e2c1",
                "0686bc67ccaf8fe8635042f7902fdb2d12f18978b1e375713e2aabb4bf47c561",
            ),
            (
                "79c133752e23e7b9bcae37245339710757a48009dd03c6ad3abb207503cd2ccf",
                "8612a6faca0d1d36139fc70c4152757293e097cafa0e4e1ed54954a840e8d135",
            ),
            (
                "02f733b0252da5ced461b6d6489e2713915406ffb352653e642c5c649fb44a7a",
                "b93b7a1fc5c9e750c2001cd6d80169485f81e572271301fb823f01dd5ea7b1dd",
            ),
            (
                "a58aab452f7ca6bd37048750a33876ea9e0110c1cf32b3e18f5aa99d9355c086",
                "5b8e6f94826f10f31742eac1166a9c815d2985731218ab6e638ec57c1e1b5b1c",
            ),
        )
        for result, (semantic_id, evidence_id) in zip(
                cases, expected, strict=True):
            with self.subTest(status=result.status):
                self.assertEqual(result.semantic_id, semantic_id)
                self.assertEqual(result.evidence_id, evidence_id)


if __name__ == "__main__":
    unittest.main()
