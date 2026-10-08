"""Adversarial tests for the bounded Stage-C EPS-consistency diagnostic."""
import ast
import builtins
from collections import UserDict
from dataclasses import FrozenInstanceError, dataclass, fields, replace
from decimal import Decimal
from enum import Enum
import json
import os
from pathlib import Path
import socket
import time
import unittest
from unittest.mock import patch

from economic_facts import sec_current_eps_comparability_qualification as comparability
from economic_facts import sec_ordinary_compounder_profile as profile_module
from src import five_period_eps_consistency as consistency
from tests.test_sec_ordinary_compounder_profile import (
    OrdinaryCompounderProfileTests,
)


class FivePeriodEPSConsistencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile_fixture = OrdinaryCompounderProfileTests(
            methodName="runTest"
        )
        cls.profile_fixture.setUp()
        cls.available = cls.profile_fixture.qualify()
        cls.unavailable = cls.profile_fixture.qualify(
            sic=None, description=None
        )
        cls.unsupported = cls.profile_fixture.qualify(
            sic=6021, description="National Commercial Banks"
        )
        cls.source_conflict = cls.profile_fixture.qualify(
            expected_comparability_semantic_id="0" * 64,
        )

    @classmethod
    def tearDownClass(cls):
        cls.profile_fixture.doCleanups()

    def analyze(self, value=None):
        return consistency.analyze_five_period_eps_consistency(
            self.available if value is None else value
        )

    def with_values(self, *values):
        periods = tuple(
            replace(period, c3_value=value, presented_value=value)
            for period, value in zip(
                self.available.upstream_comparability.period_decisions,
                values,
                strict=True,
            )
        )
        upstream = replace(
            self.available.upstream_comparability,
            period_decisions=periods,
        )
        return replace(self.available, upstream_comparability=upstream)

    def test_exact_runtime_input_type_only(self):
        class Subclass(
            profile_module.OrdinaryCompounderMethodProfileQualification
        ):
            pass

        valid = self.analyze()
        self.assertIs(
            valid.status,
            consistency.FivePeriodEPSConsistencyStatus.AVAILABLE,
        )
        for value in (
                {},
                UserDict(),
                Subclass(*(
                    getattr(self.available, field.name)
                    for field in fields(self.available)
                )),
                self.available.upstream_comparability,
                self.available.upstream_comparability.period_decisions,
                object(),
        ):
            with self.subTest(value_type=type(value)), self.assertRaises(
                    consistency.FivePeriodEPSConsistencyError):
                self.analyze(value)

    def test_valid_established_profile_produces_four_available_intervals(self):
        result = self.analyze()
        self.assertIs(
            result.analysis_kind,
            consistency.FivePeriodEPSConsistencyAnalysisKind.
            FIVE_PERIOD_DILUTED_EPS_DIRECTIONAL_CONSISTENCY,
        )
        self.assertIs(
            result.status,
            consistency.FivePeriodEPSConsistencyStatus.AVAILABLE,
        )
        self.assertEqual(len(result.intervals), 4)
        self.assertEqual(
            result.increase_count
            + result.unchanged_count
            + result.decrease_count,
            4,
        )

    def test_all_increasing_trace_is_four_zero_zero(self):
        result = self.analyze()
        self.assertEqual(
            (result.increase_count, result.unchanged_count,
             result.decrease_count),
            (4, 0, 0),
        )
        self.assertTrue(all(
            item.direction is consistency.FivePeriodEPSDirection.INCREASED
            for item in result.intervals
        ))

    def test_mixed_trace_uses_exact_decimal_signs(self):
        result = self.analyze(self.with_values(
            Decimal("2.000"),
            Decimal("3.250"),
            Decimal("3.250"),
            Decimal("1.125"),
            Decimal("4.125"),
        ))
        self.assertEqual(
            tuple(item.direction for item in result.intervals),
            (
                consistency.FivePeriodEPSDirection.INCREASED,
                consistency.FivePeriodEPSDirection.UNCHANGED,
                consistency.FivePeriodEPSDirection.DECREASED,
                consistency.FivePeriodEPSDirection.INCREASED,
            ),
        )
        self.assertEqual(
            tuple(item.delta_diluted_eps for item in result.intervals),
            (
                Decimal("1.250"),
                Decimal("0.000"),
                Decimal("-2.125"),
                Decimal("3.000"),
            ),
        )
        self.assertEqual(
            (result.increase_count, result.unchanged_count,
             result.decrease_count),
            (2, 1, 1),
        )

    def test_decimal_values_never_pass_through_binary_float(self):
        result = self.analyze(self.with_values(
            Decimal("0.1"), Decimal("0.2"), Decimal("0.3"),
            Decimal("0.4"), Decimal("0.5"),
        ))
        self.assertEqual(
            tuple(item.delta_diluted_eps for item in result.intervals),
            (Decimal("0.1"),) * 4,
        )
        self.assertTrue(all(
            type(value) is Decimal
            for item in result.intervals
            for value in (
                item.prior_diluted_eps,
                item.current_diluted_eps,
                item.delta_diluted_eps,
            )
        ))

    def test_profile_capability_states_map_exactly_and_remain_distinct(self):
        cases = (
            (
                self.unavailable,
                consistency.FivePeriodEPSConsistencyStatus.UNAVAILABLE,
            ),
            (
                self.unsupported,
                consistency.FivePeriodEPSConsistencyStatus.UNSUPPORTED,
            ),
            (
                self.source_conflict,
                consistency.FivePeriodEPSConsistencyStatus.SOURCE_CONFLICT,
            ),
        )
        for upstream, expected in cases:
            with self.subTest(status=upstream.status):
                result = self.analyze(upstream)
                self.assertIs(result.status, expected)
                self.assertIs(result.upstream_profile_status, upstream.status)
                self.assertIs(result.upstream_profile_reasons,
                              upstream.reasons)

    def test_excluded_loss_and_turnaround_profiles_never_become_available(self):
        for structure in profile_module.UnsupportedStructure:
            excluded = replace(
                self.unsupported,
                decisions=tuple(
                    replace(
                        item,
                        decision=(
                            profile_module.ProfileDecisionValue.NOT_EXCLUDED
                            if item.profile is structure
                            else item.decision
                        ),
                    )
                    for item in self.unsupported.decisions
                ),
            )
            with self.subTest(structure=structure):
                self.assertIs(
                    self.analyze(excluded).status,
                    consistency.FivePeriodEPSConsistencyStatus.UNSUPPORTED,
                )

    def test_unknown_future_profile_state_fails_contract(self):
        with self.assertRaises(consistency.FivePeriodEPSConsistencyError):
            self.analyze(replace(self.available, status="FUTURE_STATE"))

    def test_contradictory_established_profile_fails_programming_contract(self):
        cases = (
            replace(
                self.available,
                reasons=(profile_module.ProfileReason.PR5C_NOT_ESTABLISHED,),
            ),
            replace(self.available, profile=None),
            replace(
                self.available,
                upstream_comparability=replace(
                    self.available.upstream_comparability,
                    outcome=comparability.ComparabilityOutcome.
                    COMPARABILITY_UNAVAILABLE,
                ),
            ),
            replace(
                self.available,
                decisions=self.available.decisions[:-1],
            ),
        )
        for value in cases:
            with self.subTest(value=value), self.assertRaises(
                    consistency.FivePeriodEPSConsistencyError):
                self.analyze(value)

    def test_wrong_period_count_and_non_exact_match_fail_closed(self):
        upstream = self.available.upstream_comparability
        wrong_count = replace(
            self.available,
            upstream_comparability=replace(
                upstream, period_decisions=upstream.period_decisions[:-1]
            ),
        )
        non_exact_periods = list(upstream.period_decisions)
        non_exact_periods[2] = replace(
            non_exact_periods[2],
            outcome=comparability.PeriodOutcome.PRESENTATION_VALUE_MISMATCH,
            reasons=(
                comparability.ComparabilityReason.
                PRESENTED_EPS_VALUE_MISMATCH,
            ),
        )
        non_exact = replace(
            self.available,
            upstream_comparability=replace(
                upstream, period_decisions=tuple(non_exact_periods)
            ),
        )
        for value in (wrong_count, non_exact):
            with self.subTest(value=value), self.assertRaises(
                    consistency.FivePeriodEPSConsistencyError):
                self.analyze(value)

    def test_foreign_dataclass_period_cannot_masquerade_as_canonical(self):
        @dataclass(frozen=True)
        class ForeignPeriodDecision:
            period_end: str
            outcome: object
            reasons: tuple
            c3_value: Decimal
            presented_value: Decimal

        periods = list(self.available.upstream_comparability.period_decisions)
        canonical = periods[2]
        periods[2] = ForeignPeriodDecision(
            canonical.period_end,
            canonical.outcome,
            canonical.reasons,
            canonical.c3_value,
            canonical.presented_value,
        )
        value = replace(
            self.available,
            upstream_comparability=replace(
                self.available.upstream_comparability,
                period_decisions=tuple(periods),
            ),
        )
        with self.assertRaises(consistency.FivePeriodEPSConsistencyError):
            self.analyze(value)

    def test_foreign_exact_match_enum_cannot_masquerade_as_canonical(self):
        class ForeignPeriodOutcome(Enum):
            EXACT_MATCH = "EXACT_MATCH"

        periods = list(self.available.upstream_comparability.period_decisions)
        periods[2] = replace(
            periods[2], outcome=ForeignPeriodOutcome.EXACT_MATCH
        )
        value = replace(
            self.available,
            upstream_comparability=replace(
                self.available.upstream_comparability,
                period_decisions=tuple(periods),
            ),
        )
        with self.assertRaises(consistency.FivePeriodEPSConsistencyError):
            self.analyze(value)

    def test_malformed_nonfinite_float_and_missing_eps_fail_closed(self):
        for malformed in (
                None,
                0.0,
                Decimal("NaN"),
                Decimal("Infinity"),
                Decimal("-Infinity"),
        ):
            periods = list(
                self.available.upstream_comparability.period_decisions
            )
            periods[2] = replace(
                periods[2],
                c3_value=malformed,
                presented_value=malformed,
            )
            value = replace(
                self.available,
                upstream_comparability=replace(
                    self.available.upstream_comparability,
                    period_decisions=tuple(periods),
                ),
            )
            with self.subTest(malformed=malformed), self.assertRaises(
                    consistency.FivePeriodEPSConsistencyError):
                self.analyze(value)

    def test_profile_comparability_route_identity_mismatch_fails(self):
        value = replace(
            self.available,
            upstream_comparability=replace(
                self.available.upstream_comparability,
                route_local_issuer_key="a" * 64,
            ),
        )
        with self.assertRaises(consistency.FivePeriodEPSConsistencyError):
            self.analyze(value)

    def test_period_endpoints_must_be_strictly_ordered_and_distinct(self):
        periods = list(self.available.upstream_comparability.period_decisions)
        cases = []
        duplicate = periods.copy()
        duplicate[2] = replace(
            duplicate[2], period_end=duplicate[1].period_end
        )
        cases.append(duplicate)
        reversed_periods = periods.copy()
        reversed_periods[1], reversed_periods[2] = (
            reversed_periods[2], reversed_periods[1]
        )
        cases.append(reversed_periods)
        for malformed in cases:
            value = replace(
                self.available,
                upstream_comparability=replace(
                    self.available.upstream_comparability,
                    period_decisions=tuple(malformed),
                ),
            )
            with self.subTest(endpoints=[p.period_end for p in malformed]), \
                    self.assertRaises(
                        consistency.FivePeriodEPSConsistencyError):
                self.analyze(value)

    def test_result_and_intervals_are_immutable(self):
        result = self.analyze()
        with self.assertRaises(FrozenInstanceError):
            result.status = consistency.FivePeriodEPSConsistencyStatus.UNAVAILABLE
        with self.assertRaises(FrozenInstanceError):
            result.intervals[0].direction = (
                consistency.FivePeriodEPSDirection.DECREASED
            )

    def test_repeated_serialization_and_identity_are_deterministic(self):
        result = self.analyze(self.with_values(
            Decimal("2.000"), Decimal("3.250"), Decimal("3.250"),
            Decimal("1.125"), Decimal("4.125"),
        ))
        first = json.dumps(
            result.to_dict(), sort_keys=True, separators=(",", ":")
        )
        second = json.dumps(
            result.to_dict(), sort_keys=True, separators=(",", ":")
        )
        self.assertEqual(first, second)
        self.assertEqual(result.semantic_id, result.semantic_id)
        self.assertEqual(result.evidence_id, result.evidence_id)

    def test_eps_and_direction_changes_change_semantic_identity(self):
        baseline = self.analyze()
        eps_changed = self.analyze(self.with_values(
            Decimal("2"), Decimal("3"), Decimal("4.1"),
            Decimal("5"), Decimal("6"),
        ))
        direction_changed = self.analyze(self.with_values(
            Decimal("2"), Decimal("3"), Decimal("2.5"),
            Decimal("5"), Decimal("6"),
        ))
        self.assertNotEqual(baseline.semantic_id, eps_changed.semantic_id)
        self.assertNotEqual(baseline.semantic_id, direction_changed.semantic_id)
        self.assertNotEqual(
            tuple(item.direction for item in baseline.intervals),
            tuple(item.direction for item in direction_changed.intervals),
        )

    def test_status_and_native_reason_changes_change_semantic_identity(self):
        unavailable = self.analyze(self.unavailable)
        unsupported = self.analyze(self.unsupported)
        reason_changed_upstream = replace(
            self.unavailable,
            reasons=(
                profile_module.ProfileReason.
                POSITIVE_FIVE_PERIOD_ROUTE_NOT_ESTABLISHED,
            ),
        )
        reason_changed = self.analyze(reason_changed_upstream)
        self.assertNotEqual(unavailable.semantic_id, unsupported.semantic_id)
        self.assertNotEqual(unavailable.semantic_id, reason_changed.semantic_id)

    def test_evidence_only_recapture_preserves_semantics_and_changes_evidence(self):
        baseline = self.analyze()
        recaptured_profile = replace(
            self.available,
            metadata_evidence_id="f" * 64,
        )
        recaptured = self.analyze(recaptured_profile)
        self.assertEqual(
            baseline.upstream_profile_semantic_id,
            recaptured.upstream_profile_semantic_id,
        )
        self.assertNotEqual(
            baseline.upstream_profile_evidence_id,
            recaptured.upstream_profile_evidence_id,
        )
        self.assertEqual(baseline.semantic_id, recaptured.semantic_id)
        self.assertNotEqual(baseline.evidence_id, recaptured.evidence_id)

    def test_representative_identities_are_pinned(self):
        mixed = self.analyze(self.with_values(
            Decimal("2.000"), Decimal("3.250"), Decimal("3.250"),
            Decimal("1.125"), Decimal("4.125"),
        ))
        cases = (
            (
                mixed,
                "af768e8390d2f64f02e9111bc198724aa77b27a8ceb36dda4a4b5bd928d59533",
                "24f5a8163c22e421f2b152b131ee610c1029d28225f1d857ef6fa029963e6403",
            ),
            (
                self.analyze(self.unavailable),
                "92c5b14781d3468594dcc5783913f57bc94c85a582ac1673900a5092d09e64aa",
                "d41a1e07642fdbeb00d18eba3a1df3d9ca8669532014e2fd6a812418c38edd3f",
            ),
            (
                self.analyze(self.unsupported),
                "430c01a2b390ab8f4c7c7d1421ab08672b23f3fe04246e6732f3a7d9541d5bca",
                "e0671aaf3aa1cdb6d712abf7947c2a755fab2c3f9ef9b7a18304320cf7bc3ead",
            ),
            (
                self.analyze(self.source_conflict),
                "7ea98f9b64826c2a8d0c58b4e2cf374245421acfd031b3715dbd463c506fcc2c",
                "43f60e21457b4b54698a29a052c9c527c19fa3d6de651e6fb29d690cd2496274",
            ),
        )
        for result, semantic_id, evidence_id in cases:
            with self.subTest(status=result.status):
                self.assertEqual(result.semantic_id, semantic_id)
                self.assertEqual(result.evidence_id, evidence_id)

    def test_public_result_fields_are_exact_and_exclude_policy_surfaces(self):
        self.assertEqual(
            tuple(field.name for field in fields(
                consistency.FivePeriodEPSInterval
            )),
            (
                "prior_period_end", "current_period_end",
                "prior_diluted_eps", "current_diluted_eps",
                "delta_diluted_eps", "direction",
            ),
        )
        self.assertEqual(
            tuple(field.name for field in fields(
                consistency.FivePeriodEPSConsistencyResult
            )),
            (
                "contract_version", "methodology_version", "analysis_kind",
                "status", "upstream_profile_status",
                "upstream_profile_reasons", "route_local_issuer_key",
                "route_local_security_key", "upstream_profile_semantic_id",
                "upstream_profile_evidence_id",
                "upstream_comparability_semantic_id",
                "upstream_comparability_evidence_id", "intervals",
                "increase_count", "unchanged_count", "decrease_count",
                "authority", "limitations",
            ),
        )
        prohibited = {
            "score", "grade", "rank", "confidence", "recommendation",
            "allocation", "sizing", "expected_return", "durability",
            "moat", "cagr", "percentage_growth",
        }
        self.assertTrue(prohibited.isdisjoint(
            field.name
            for field in fields(consistency.FivePeriodEPSConsistencyResult)
        ))

    def test_nonavailable_result_has_no_partial_trace_or_zero_counts(self):
        for value in (
                self.unavailable, self.unsupported, self.source_conflict):
            result = self.analyze(value)
            with self.subTest(status=result.status):
                self.assertEqual(result.intervals, ())
                self.assertIsNone(result.increase_count)
                self.assertIsNone(result.unchanged_count)
                self.assertIsNone(result.decrease_count)

    def test_authority_and_closed_limitations_are_exact(self):
        result = self.analyze()
        self.assertIs(
            result.authority,
            consistency.FivePeriodEPSConsistencyAuthority.
            QUALITY_EPS_CONSISTENCY_DIAGNOSTIC_ONLY,
        )
        self.assertEqual(
            result.limitations,
            tuple(consistency.FivePeriodEPSConsistencyLimitation),
        )
        self.assertEqual(
            tuple(item.value for item in result.limitations),
            (
                "NO_COMPOSITE_QUALITY_SCORE",
                "NO_CROSS_SECTOR_COMPARABILITY",
                "NO_PROFIT_MARGIN_OR_ROIC_CLAIM",
                "NO_CASH_CONVERSION_OR_BALANCE_SHEET_CLAIM",
                "NO_CAPITAL_ALLOCATION_DILUTION_OR_MOAT_CLAIM",
                "NO_DURABILITY_OR_FORWARD_PERSISTENCE_CLAIM",
                "NO_EXPECTED_RETURN_ADJUSTMENT",
                "NO_CONFIDENCE_SUBSTITUTION",
                "NO_RECOMMENDATION_RANKING_ALLOCATION_OR_SIZING",
                "NO_EXECUTION_PRODUCTION_OR_V2_PROMOTION_AUTHORITY",
                "NO_HISTORICAL_AS_OF_OR_PIT_AUTHORITY",
            ),
        )

    def test_runtime_is_read_only_without_network_filesystem_env_or_clock(self):
        with patch.object(
                socket.socket, "connect",
                side_effect=AssertionError("network")), \
                patch.object(
                    socket, "getaddrinfo",
                    side_effect=AssertionError("network")), \
                patch.object(
                    builtins, "open",
                    side_effect=AssertionError("filesystem")), \
                patch.object(
                    os, "getenv",
                    side_effect=AssertionError("environment")), \
                patch.object(
                    time, "time",
                    side_effect=AssertionError("clock")):
            self.assertIs(
                self.analyze().status,
                consistency.FivePeriodEPSConsistencyStatus.AVAILABLE,
            )

    def test_static_imports_are_narrow_and_prohibited_layers_are_absent(self):
        path = Path(consistency.__file__)
        source = path.read_text()
        tree = ast.parse(source)
        allowed_imports = {
            "__future__",
            "dataclasses",
            "decimal",
            "enum",
            "hashlib",
            "json",
            "economic_facts.sec_current_eps_comparability_qualification",
            "economic_facts.sec_ordinary_compounder_profile",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                self.assertTrue(all(
                    alias.name in allowed_imports for alias in node.names
                ))
            elif isinstance(node, ast.ImportFrom):
                self.assertIn(node.module, allowed_imports)
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                self.assertNotIn(
                    node.func.id,
                    {"eval", "exec", "__import__", "compile"},
                )
        prohibited_tokens = (
            "expected_return_pr5e_adapter",
            "expected_return_engine",
            "vfv_forward_expected_return",
            "company_vfv_expected_return_comparator",
            "cash_like_current_carry",
            "bounded_confidence_projection",
            "analysis_capabilities",
            "pit_comparison",
            "broker",
            "execution_instruction",
            "cagr_quality_engine",
            "cash_flow_quality_engine",
            "decision_quality_engine",
            "quality_drawdown_engine",
            "shareholder_return_engine",
            "shareholder_discipline_engine",
            "safe_float",
            "clamp",
        )
        for token in prohibited_tokens:
            self.assertNotIn(token, source)

    def test_reverse_dependency_exception_is_one_exact_path(self):
        guard = (
            Path(__file__).resolve().parent / "test_sec_fact_archive.py"
        ).read_text()
        tree = ast.parse(guard)
        exact = "five_period_eps_consistency.py"
        constants = tuple(
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and type(node.value) is str
            and exact in node.value
        )
        self.assertEqual(constants, (exact,))
        self.assertNotIn("glob(\"five_period", guard)
        self.assertNotIn("src/*", guard)

    def test_model_rules_and_protected_fingerprints_remain_pinned(self):
        checkout = Path(__file__).resolve().parents[1]
        model_source = (checkout / "src" / "model_version.py").read_text()
        pit_source = (
            checkout / "tests" / "test_pit_adapter_equivalence.py"
        ).read_text()
        determinism_source = (
            checkout / "tests" / "test_pit_comparison.py"
        ).read_text()
        self.assertIn(
            'MODEL_RULES_VERSION = "2026-08-23-allocation-room-integrity-v7"',
            model_source,
        )
        self.assertIn(
            "f1e73b27b80e41d96ff5e0fe990b482bad71b7220db0b5bd6a2f470d72786166",
            pit_source,
        )
        self.assertIn(
            "f8457910665391e39c234274cae4c029802c681211eebc7dba986a63000876f1",
            determinism_source,
        )


if __name__ == "__main__":
    unittest.main()
