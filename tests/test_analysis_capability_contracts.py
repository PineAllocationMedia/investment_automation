from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields
import json
import os
from pathlib import Path
import subprocess
import sys
import textwrap
import unittest

import analysis_capabilities
from analysis_capabilities import contracts
from analysis_capabilities import (
    CAPABILITY_CONTRACT_VERSION,
    CapabilityAssessment,
    CapabilityContractError,
    CapabilityScope,
    CapabilityState,
)


ROOT = Path(__file__).resolve().parents[1]
SUBJECT_A = "1" * 64
SUBJECT_B = "2" * 64
SEMANTIC_A = "a" * 64
SEMANTIC_B = "b" * 64
EVIDENCE_A = "c" * 64
EVIDENCE_B = "d" * 64


def scope(**changes):
    values = {
        "subject_kind": "ROUTE_LOCAL_SECURITY",
        "subject_identity": SUBJECT_A,
        "authority_boundary": "2026-09-28T12:00:00Z",
        "supporting_semantic_ids": (SEMANTIC_B, SEMANTIC_A),
    }
    values.update(changes)
    return CapabilityScope(**values)


def assessment(state=CapabilityState.SUPPORTED, **changes):
    values = {
        "contract_version": CAPABILITY_CONTRACT_VERSION,
        "capability_id": "COMPARABLE_EPS_HISTORY",
        "scope": scope(),
        "state": state,
        "supporting_semantic_ids": (SEMANTIC_B, SEMANTIC_A),
        "supporting_evidence_ids": (EVIDENCE_B, EVIDENCE_A),
        "reason_codes": (),
        "limitation_codes": (),
    }
    values.update(changes)
    return CapabilityAssessment(**values)


class CapabilityContractTests(unittest.TestCase):
    def test_exact_closed_capability_states(self):
        self.assertEqual(
            tuple(state.value for state in CapabilityState),
            (
                "SUPPORTED",
                "PARTIAL",
                "UNSUPPORTED",
                "UNAVAILABLE",
                "REVIEW_REQUIRED",
                "CONFLICTED",
            ),
        )
        self.assertEqual(len(CapabilityState.__members__), 6)

    def test_public_api_is_minimal_and_excludes_participation_states(self):
        self.assertEqual(
            analysis_capabilities.__all__,
            (
                "CAPABILITY_CONTRACT_VERSION",
                "CapabilityAssessment",
                "CapabilityContractError",
                "CapabilityScope",
                "CapabilityState",
                "DEPENDENCY_CONTRACT_VERSION",
                "CapabilityDependency",
                "DependencyContractError",
                "OutputDependencyContract",
                "ASSEMBLER_CONTRACT_VERSION",
                "AssemblyContractError",
                "OutputAvailabilityStatus",
                "DependencyBinding",
                "DependencyResolutionStatus",
                "DependencyResolution",
                "OutputAvailability",
                "assemble_output_availability",
            ),
        )
        self.assertEqual(
            contracts.__all__,
            (
                "CAPABILITY_CONTRACT_VERSION",
                "CapabilityAssessment",
                "CapabilityContractError",
                "CapabilityScope",
                "CapabilityState",
            ),
        )
        for prohibited in (
            "FULL_ANALYSIS_ELIGIBLE",
            "PARTIAL_ANALYSIS",
            "RESEARCH_CANDIDATE",
            "UNSUPPORTED_RESEARCH_PROFILE",
        ):
            self.assertFalse(hasattr(analysis_capabilities, prohibited))

    def test_records_are_frozen_and_slotted(self):
        item = assessment()
        self.assertFalse(hasattr(item, "__dict__"))
        self.assertFalse(hasattr(item.scope, "__dict__"))
        with self.assertRaises(FrozenInstanceError):
            item.capability_id = "REVENUE_HISTORY"
        with self.assertRaises(FrozenInstanceError):
            item.scope.subject_kind = "ISSUER"

    def test_supported_requires_positive_semantic_and_evidence_support(self):
        for changes in (
            {"supporting_semantic_ids": ()},
            {"supporting_evidence_ids": ()},
            {"supporting_semantic_ids": (), "supporting_evidence_ids": ()},
        ):
            with self.subTest(changes=changes), self.assertRaises(CapabilityContractError):
                assessment(**changes)

    def test_partial_requires_support_reasons_and_limitations(self):
        valid = assessment(
            CapabilityState.PARTIAL,
            reason_codes=("SOURCE_DATA_MISSING",),
            limitation_codes=("SHARE_BASIS_NOT_ESTABLISHED",),
        )
        self.assertEqual(valid.state, CapabilityState.PARTIAL)
        for changes in (
            {"supporting_semantic_ids": ()},
            {"supporting_evidence_ids": ()},
            {"reason_codes": ()},
            {"limitation_codes": ()},
        ):
            values = {
                "reason_codes": ("SOURCE_DATA_MISSING",),
                "limitation_codes": ("SHARE_BASIS_NOT_ESTABLISHED",),
                **changes,
            }
            with self.subTest(changes=changes), self.assertRaises(CapabilityContractError):
                assessment(CapabilityState.PARTIAL, **values)

    def test_negative_and_unresolved_state_invariants(self):
        for state in (CapabilityState.UNSUPPORTED, CapabilityState.UNAVAILABLE):
            with self.subTest(state=state):
                with self.assertRaises(CapabilityContractError):
                    assessment(state, supporting_semantic_ids=(), supporting_evidence_ids=())
                item = assessment(
                    state,
                    supporting_semantic_ids=(),
                    supporting_evidence_ids=(),
                    reason_codes=("SOURCE_DATA_MISSING",),
                )
                self.assertEqual(item.supporting_evidence_ids, ())
        for state in (CapabilityState.REVIEW_REQUIRED, CapabilityState.CONFLICTED):
            with self.subTest(state=state):
                with self.assertRaises(CapabilityContractError):
                    assessment(state, reason_codes=())
                with self.assertRaises(CapabilityContractError):
                    assessment(
                        state,
                        supporting_semantic_ids=(),
                        supporting_evidence_ids=(),
                        reason_codes=("SOURCE_CONFLICT",),
                    )
                self.assertEqual(
                    assessment(state, reason_codes=("SOURCE_CONFLICT",)).state,
                    state,
                )

    def test_contract_version_capability_id_and_exact_types_fail_closed(self):
        with self.assertRaises(CapabilityContractError):
            assessment(contract_version="future")
        for value in ("comparable_eps", "COMPARABLE EPS", "_EPS", "ÉPS", "", 1):
            with self.subTest(value=value), self.assertRaises(CapabilityContractError):
                assessment(capability_id=value)
        with self.assertRaises(CapabilityContractError):
            assessment(state="SUPPORTED")
        with self.assertRaises(CapabilityContractError):
            assessment(scope={"subject_identity": SUBJECT_A})

    def test_scope_requires_explicit_upstream_identity_not_ticker_or_name(self):
        for changes in (
            {"subject_kind": "route_local_security"},
            {"subject_identity": "MSFT"},
            {"subject_identity": "0000789019"},
            {"subject_identity": "Microsoft Corporation"},
            {"authority_boundary": " inferred now "},
            {"supporting_semantic_ids": [SEMANTIC_A]},
        ):
            with self.subTest(changes=changes), self.assertRaises(CapabilityContractError):
                scope(**changes)

    def test_collections_are_unique_sorted_and_order_independent(self):
        first = assessment(
            supporting_semantic_ids=(SEMANTIC_B, SEMANTIC_A, SEMANTIC_B),
            supporting_evidence_ids=(EVIDENCE_B, EVIDENCE_A, EVIDENCE_B),
            reason_codes=("Z_REASON", "A_REASON", "Z_REASON"),
            limitation_codes=("Z_LIMIT", "A_LIMIT", "Z_LIMIT"),
        )
        second = assessment(
            supporting_semantic_ids=(SEMANTIC_A, SEMANTIC_B),
            supporting_evidence_ids=(EVIDENCE_A, EVIDENCE_B),
            reason_codes=("A_REASON", "Z_REASON"),
            limitation_codes=("A_LIMIT", "Z_LIMIT"),
        )
        self.assertEqual(first, second)
        self.assertEqual(first.semantic_id, second.semantic_id)
        self.assertEqual(first.evidence_id, second.evidence_id)
        self.assertEqual(first.scope.supporting_semantic_ids, (SEMANTIC_A, SEMANTIC_B))
        with self.assertRaises(CapabilityContractError):
            assessment(reason_codes=("natural language",))

    def test_semantic_identity_excludes_exact_evidence_identity(self):
        first = assessment(supporting_evidence_ids=(EVIDENCE_A,))
        recapture = assessment(supporting_evidence_ids=(EVIDENCE_B,))
        self.assertEqual(first.semantic_id, recapture.semantic_id)
        self.assertNotEqual(first.evidence_id, recapture.evidence_id)
        self.assertRegex(first.semantic_id, r"^[0-9a-f]{64}$")
        self.assertRegex(first.evidence_id, r"^[0-9a-f]{64}$")

    def test_semantic_changes_change_semantic_and_evidence_identity(self):
        base = assessment()
        variants = (
            assessment(scope=scope(subject_identity=SUBJECT_B)),
            assessment(CapabilityState.REVIEW_REQUIRED, reason_codes=("MANUAL_REVIEW",)),
            assessment(reason_codes=("POSITIVE_SOURCE_AGREEMENT",)),
            assessment(limitation_codes=("NO_GLOBAL_IDENTITY",)),
            assessment(scope=scope(authority_boundary="CURRENT_T1")),
        )
        for variant in variants:
            with self.subTest(variant=variant):
                self.assertNotEqual(base.semantic_id, variant.semantic_id)
                self.assertNotEqual(base.evidence_id, variant.evidence_id)

        unavailable = assessment(
            CapabilityState.UNAVAILABLE,
            supporting_semantic_ids=(),
            supporting_evidence_ids=(),
            reason_codes=("SOURCE_DATA_MISSING",),
        )
        unsupported = assessment(
            CapabilityState.UNSUPPORTED,
            supporting_semantic_ids=(),
            supporting_evidence_ids=(),
            reason_codes=("SOURCE_DATA_MISSING",),
        )
        self.assertNotEqual(unavailable.semantic_id, unsupported.semantic_id)

    def test_no_score_ticker_or_investment_authority_field_exists(self):
        names = {field.name for field in fields(CapabilityScope)} | {
            field.name for field in fields(CapabilityAssessment)
        }
        for prohibited in (
            "ticker",
            "coverage_score",
            "capability_percentage",
            "research_completeness_score",
            "global_supported_fraction",
            "admitted",
            "investable",
            "opportunity_set_eligible",
            "buy",
            "sell",
            "allocation_authority",
            "production_authority",
        ):
            self.assertNotIn(prohibited, names)

    def test_contract_module_has_pure_stdlib_dependency_boundary(self):
        module_path = ROOT / "analysis_capabilities/contracts.py"
        tree = ast.parse(module_path.read_text())
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add((node.module or "").split(".")[0])
        self.assertLessEqual(imported, {"__future__", "dataclasses", "enum", "hashlib", "json", "re"})
        source = module_path.read_text()
        for forbidden in (
            "socket",
            "urllib",
            "requests",
            "pathlib",
            "open(",
            "getenv",
            "environ",
            "datetime",
            "time.",
        ):
            self.assertNotIn(forbidden, source)

    def test_identity_is_deterministic_across_python_hash_seeds(self):
        source = textwrap.dedent(
            f"""
            import json
            from analysis_capabilities import *
            scope = CapabilityScope('ROUTE_LOCAL_SECURITY', '{SUBJECT_A}',
                                    'CURRENT_T1', ('{SEMANTIC_B}', '{SEMANTIC_A}'))
            item = CapabilityAssessment(CAPABILITY_CONTRACT_VERSION,
                                        'COMPARABLE_EPS_HISTORY', scope,
                                        CapabilityState.PARTIAL,
                                        ('{SEMANTIC_B}', '{SEMANTIC_A}'),
                                        ('{EVIDENCE_B}', '{EVIDENCE_A}'),
                                        ('Z_REASON', 'A_REASON'),
                                        ('Z_LIMIT', 'A_LIMIT'))
            print(json.dumps([item.semantic_id, item.evidence_id]))
            """
        )
        outputs = []
        for seed in ("1", "97"):
            env = {
                "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                "PYTHONHASHSEED": seed,
                "PYTHONDONTWRITEBYTECODE": "1",
            }
            result = subprocess.run(
                [sys.executable, "-B", "-c", source],
                cwd=ROOT,
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )
            outputs.append(json.loads(result.stdout))
        self.assertEqual(outputs[0], outputs[1])


if __name__ == "__main__":
    unittest.main()
