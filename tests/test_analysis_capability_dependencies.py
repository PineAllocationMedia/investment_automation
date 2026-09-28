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
from analysis_capabilities import dependencies
from analysis_capabilities import (
    DEPENDENCY_CONTRACT_VERSION,
    CapabilityDependency,
    CapabilityState,
    DependencyContractError,
    OutputDependencyContract,
)


ROOT = Path(__file__).resolve().parents[1]


def dependency(**changes):
    values = {
        "dependency_id": "PRIMARY_EPS_HISTORY",
        "capability_id": "COMPARABLE_EPS_HISTORY",
        "subject_kind": "ROUTE_LOCAL_SECURITY",
        "accepted_states": (CapabilityState.SUPPORTED,),
    }
    values.update(changes)
    return CapabilityDependency(**values)


def contract(**changes):
    values = {
        "contract_version": DEPENDENCY_CONTRACT_VERSION,
        "output_id": "FICTIONAL_ANALYTICAL_OUTPUT",
        "output_subject_kind": "ISSUER",
        "requirements": (dependency(),),
    }
    values.update(changes)
    return OutputDependencyContract(**values)


class CapabilityDependencyTests(unittest.TestCase):
    def test_exact_public_dependency_api(self):
        self.assertEqual(
            dependencies.__all__,
            (
                "DEPENDENCY_CONTRACT_VERSION",
                "CapabilityDependency",
                "DependencyContractError",
                "OutputDependencyContract",
            ),
        )
        for name in dependencies.__all__:
            self.assertIs(getattr(analysis_capabilities, name), getattr(dependencies, name))

    def test_records_are_frozen_and_slotted_with_exact_fields(self):
        requirement = dependency()
        item = contract()
        self.assertEqual(
            tuple(field.name for field in fields(CapabilityDependency)),
            ("dependency_id", "capability_id", "subject_kind", "accepted_states"),
        )
        self.assertEqual(
            tuple(field.name for field in fields(OutputDependencyContract)),
            ("contract_version", "output_id", "output_subject_kind", "requirements"),
        )
        self.assertFalse(hasattr(requirement, "__dict__"))
        self.assertFalse(hasattr(item, "__dict__"))
        with self.assertRaises(FrozenInstanceError):
            requirement.capability_id = "REVENUE_HISTORY"
        with self.assertRaises(FrozenInstanceError):
            item.output_id = "OTHER_OUTPUT"

    def test_contract_version_fails_closed(self):
        for version in ("future", "", 1, None):
            with self.subTest(version=version), self.assertRaises(DependencyContractError):
                contract(contract_version=version)

    def test_codes_require_canonical_uppercase_ascii(self):
        dependency_fields = ("dependency_id", "capability_id", "subject_kind")
        output_fields = ("output_id", "output_subject_kind")
        invalid = ("lowercase", "HAS SPACE", "_LEADING", "TRAILING_", "ÉPS", "", 1)
        for field_name in dependency_fields:
            for value in invalid:
                with self.subTest(field=field_name, value=value):
                    with self.assertRaises(DependencyContractError):
                        dependency(**{field_name: value})
        for field_name in output_fields:
            for value in invalid:
                with self.subTest(field=field_name, value=value):
                    with self.assertRaises(DependencyContractError):
                        contract(**{field_name: value})

    def test_requirements_are_exact_nonempty_tuple_of_exact_dependencies(self):
        for value in ([], (), [dependency()], (object(),)):
            with self.subTest(value=value), self.assertRaises(DependencyContractError):
                contract(requirements=value)

        class DependencySubclass(CapabilityDependency):
            pass

        with self.assertRaises(DependencyContractError):
            contract(requirements=(DependencySubclass(
                "ROLE", "CAPABILITY", "ISSUER", (CapabilityState.SUPPORTED,)
            ),))

    def test_dependency_role_ids_are_unique(self):
        repeated = dependency()
        with self.assertRaises(DependencyContractError):
            contract(requirements=(repeated, repeated))

    def test_requirements_are_canonical_and_order_independent(self):
        first_requirement = dependency(dependency_id="Z_ROLE")
        second_requirement = dependency(
            dependency_id="A_ROLE",
            capability_id="CURRENT_QUOTE",
            subject_kind="LISTING",
        )
        first = contract(requirements=(first_requirement, second_requirement))
        second = contract(requirements=(second_requirement, first_requirement))
        self.assertEqual(first, second)
        self.assertEqual(first.semantic_id, second.semantic_id)
        self.assertEqual(
            tuple(item.dependency_id for item in first.requirements),
            ("A_ROLE", "Z_ROLE"),
        )

    def test_supported_only_and_supported_plus_partial_are_valid(self):
        supported = dependency(accepted_states=(CapabilityState.SUPPORTED,))
        partial = dependency(
            accepted_states=(CapabilityState.SUPPORTED, CapabilityState.PARTIAL)
        )
        reversed_partial = dependency(
            accepted_states=(CapabilityState.PARTIAL, CapabilityState.SUPPORTED)
        )
        duplicate_partial = dependency(
            accepted_states=(
                CapabilityState.PARTIAL,
                CapabilityState.SUPPORTED,
                CapabilityState.PARTIAL,
                CapabilityState.SUPPORTED,
            )
        )
        self.assertEqual(supported.accepted_states, (CapabilityState.SUPPORTED,))
        self.assertEqual(
            partial.accepted_states,
            (CapabilityState.SUPPORTED, CapabilityState.PARTIAL),
        )
        self.assertEqual(partial, reversed_partial)
        self.assertEqual(partial, duplicate_partial)

    def test_invalid_accepted_states_fail_closed(self):
        invalid = (
            (),
            (CapabilityState.PARTIAL,),
            (CapabilityState.UNSUPPORTED,),
            (CapabilityState.UNAVAILABLE,),
            (CapabilityState.REVIEW_REQUIRED,),
            (CapabilityState.CONFLICTED,),
            (CapabilityState.SUPPORTED, CapabilityState.UNAVAILABLE),
            ("SUPPORTED",),
            [CapabilityState.SUPPORTED],
        )
        for accepted_states in invalid:
            with self.subTest(accepted_states=accepted_states):
                with self.assertRaises(DependencyContractError):
                    dependency(accepted_states=accepted_states)

    def test_same_capability_may_serve_different_dependency_roles(self):
        item = contract(
            requirements=(
                dependency(dependency_id="PRIMARY_SECURITY_PRICE", capability_id="PRICE"),
                dependency(dependency_id="BENCHMARK_SECURITY_PRICE", capability_id="PRICE"),
            )
        )
        self.assertEqual(len(item.requirements), 2)

    def test_each_bound_semantic_dimension_changes_identity(self):
        base = contract()
        variants = (
            contract(output_id="OTHER_OUTPUT"),
            contract(output_subject_kind="PORTFOLIO"),
            contract(requirements=(dependency(capability_id="REVENUE_HISTORY"),)),
            contract(requirements=(dependency(dependency_id="REPORTING_SUBJECT"),)),
            contract(requirements=(dependency(subject_kind="REPORTING_SUBJECT"),)),
            contract(requirements=(dependency(accepted_states=(
                CapabilityState.SUPPORTED, CapabilityState.PARTIAL
            )),)),
        )
        self.assertRegex(base.semantic_id, r"^[0-9a-f]{64}$")
        for variant in variants:
            with self.subTest(variant=variant):
                self.assertNotEqual(base.semantic_id, variant.semantic_id)

    def test_identity_is_deterministic_across_python_hash_seeds(self):
        source = textwrap.dedent(
            """
            import json
            from analysis_capabilities import *
            first = CapabilityDependency(
                'Z_ROLE', 'PRICE', 'LISTING',
                (CapabilityState.PARTIAL, CapabilityState.SUPPORTED))
            second = CapabilityDependency(
                'A_ROLE', 'REVENUE_HISTORY', 'ISSUER',
                (CapabilityState.SUPPORTED,))
            item = OutputDependencyContract(
                DEPENDENCY_CONTRACT_VERSION,
                'FICTIONAL_OUTPUT',
                'ISSUER',
                (first, second))
            print(json.dumps([item.semantic_id,
                              [value.dependency_id for value in item.requirements],
                              [state.value for state in first.accepted_states]]))
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

    def test_no_evaluator_score_identity_shortcut_or_authority_surface_exists(self):
        field_names = {field.name for field in fields(CapabilityDependency)} | {
            field.name for field in fields(OutputDependencyContract)
        }
        for prohibited in (
            "weight", "priority", "score", "coverage_score", "minimum_score",
            "ticker", "name", "cik", "subject_identity", "authority_boundary",
            "admitted", "investable", "buy", "sell", "recommendation",
            "opportunity_set_eligible", "allocation_authority", "execution_authority",
            "production_authority", "promotion_authority", "evidence_id",
        ):
            self.assertNotIn(prohibited, field_names)
        for prohibited in (
            "is_satisfied", "requirements_satisfied", "evaluate_dependencies",
            "can_execute", "available", "ready", "admit",
        ):
            self.assertFalse(hasattr(dependencies, prohibited))

    def test_module_is_pure_and_respects_boundaries(self):
        module_path = ROOT / "analysis_capabilities/dependencies.py"
        source = module_path.read_text()
        tree = ast.parse(source)
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add((node.module or "").split(".")[0])
        self.assertLessEqual(
            imported,
            {"__future__", "dataclasses", "hashlib", "json", "re", "contracts"},
        )
        for forbidden in (
            "economic_facts", "from src", "import src", "socket", "urllib",
            "requests", "pathlib", "open(", "getenv", "environ", "datetime", "time.",
            "CapabilityAssessment",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
