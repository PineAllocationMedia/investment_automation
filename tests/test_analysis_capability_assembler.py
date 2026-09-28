from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
import textwrap
import unittest

import analysis_capabilities
from analysis_capabilities import assembler
from analysis_capabilities import (
    ASSEMBLER_CONTRACT_VERSION,
    CAPABILITY_CONTRACT_VERSION,
    DEPENDENCY_CONTRACT_VERSION,
    AssemblyContractError,
    CapabilityAssessment,
    CapabilityDependency,
    CapabilityScope,
    CapabilityState,
    DependencyBinding,
    DependencyResolution,
    DependencyResolutionStatus,
    OutputAvailability,
    OutputAvailabilityStatus,
    OutputDependencyContract,
    assemble_output_availability,
)


ROOT = Path(__file__).resolve().parents[1]
SUBJECT_A = "1" * 64
SUBJECT_B = "2" * 64
SUBJECT_C = "3" * 64
SEMANTIC_A = "a" * 64
SEMANTIC_B = "b" * 64
RELATIONSHIP_A = "c" * 64
RELATIONSHIP_B = "d" * 64
EVIDENCE_A = "e" * 64
EVIDENCE_B = "f" * 64
EVIDENCE_C = "0" * 64


def scope(**changes):
    values = {
        "subject_kind": "ISSUER",
        "subject_identity": SUBJECT_A,
        "authority_boundary": "CURRENT_T1",
        "supporting_semantic_ids": (),
    }
    values.update(changes)
    return CapabilityScope(**values)


def dependency(**changes):
    values = {
        "dependency_id": "PRIMARY_FACTS",
        "capability_id": "FICTIONAL_FACT_HISTORY",
        "subject_kind": "ISSUER",
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


def binding(**changes):
    values = {
        "dependency_id": "PRIMARY_FACTS",
        "scope": scope(),
        "relationship_semantic_ids": (),
        "relationship_evidence_ids": (),
    }
    values.update(changes)
    return DependencyBinding(**values)


def assessment(state=CapabilityState.SUPPORTED, **changes):
    values = {
        "contract_version": CAPABILITY_CONTRACT_VERSION,
        "capability_id": "FICTIONAL_FACT_HISTORY",
        "scope": scope(),
        "state": state,
        "supporting_semantic_ids": (SEMANTIC_A,),
        "supporting_evidence_ids": (EVIDENCE_A,),
        "reason_codes": (),
        "limitation_codes": (),
    }
    if state is CapabilityState.PARTIAL:
        values.update(
            reason_codes=("BOUNDED_COVERAGE",),
            limitation_codes=("HISTORY_INCOMPLETE",),
        )
    elif state is not CapabilityState.SUPPORTED:
        values.update(reason_codes=("UPSTREAM_NOT_RESOLVED",))
    values.update(changes)
    return CapabilityAssessment(**values)


def assemble(**changes):
    values = {
        "dependency_contract": contract(),
        "output_scope": scope(),
        "bindings": (binding(),),
        "assessments": (assessment(),),
    }
    values.update(changes)
    return assemble_output_availability(**values)


class PartialAnalysisAssemblerTests(unittest.TestCase):
    def test_exact_public_api_and_closed_states(self):
        self.assertEqual(
            assembler.__all__,
            (
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
        for name in assembler.__all__:
            self.assertIs(getattr(analysis_capabilities, name), getattr(assembler, name))
        self.assertEqual(
            tuple(item.value for item in OutputAvailabilityStatus),
            ("AVAILABLE", "AVAILABLE_WITH_LIMITATIONS", "UNAVAILABLE"),
        )
        self.assertEqual(
            tuple(item.value for item in DependencyResolutionStatus),
            (
                "SATISFIED_SUPPORTED",
                "SATISFIED_PARTIAL",
                "UNSATISFIED_MISSING_BINDING",
                "UNSATISFIED_SUBJECT_KIND",
                "UNSATISFIED_BOUNDARY",
                "UNSATISFIED_RELATIONSHIP",
                "UNSATISFIED_MISSING_ASSESSMENT",
                "UNSATISFIED_AMBIGUOUS_ASSESSMENT",
                "UNSATISFIED_STATE",
            ),
        )

    def test_records_are_frozen_slotted_and_bind_version(self):
        result = assemble()
        resolution = result.dependency_resolutions[0]
        for item, field_name in (
            (binding(), "dependency_id"),
            (resolution, "status"),
            (result, "status"),
        ):
            self.assertFalse(hasattr(item, "__dict__"))
            with self.assertRaises(FrozenInstanceError):
                setattr(item, field_name, "OTHER")
        self.assertEqual(result.assembler_contract_version, ASSEMBLER_CONTRACT_VERSION)
        with self.assertRaises(AssemblyContractError):
            OutputAvailability(
                "future",
                contract().semantic_id,
                contract().output_id,
                scope(),
                OutputAvailabilityStatus.AVAILABLE,
                result.dependency_resolutions,
            )

    def test_exact_input_types_and_output_subject_kind_fail_closed(self):
        valid = assemble()
        class ScopeSubclass(CapabilityScope):
            pass

        class AssessmentSubclass(CapabilityAssessment):
            pass

        class BindingSubclass(DependencyBinding):
            pass

        invalid_requests = (
            {"dependency_contract": object()},
            {"output_scope": ScopeSubclass("ISSUER", SUBJECT_A, "CURRENT_T1")},
            {"bindings": [binding()]},
            {"bindings": (BindingSubclass("PRIMARY_FACTS", scope()),)},
            {"assessments": [assessment()]},
            {"assessments": (AssessmentSubclass(
                CAPABILITY_CONTRACT_VERSION,
                "FICTIONAL_FACT_HISTORY",
                scope(),
                CapabilityState.SUPPORTED,
                (SEMANTIC_A,),
                (EVIDENCE_A,),
            ),)},
        )
        for changes in invalid_requests:
            with self.subTest(changes=changes), self.assertRaises(AssemblyContractError):
                assemble(**changes)
        with self.assertRaises(AssemblyContractError):
            assemble(output_scope=scope(subject_kind="LISTING"))
        self.assertEqual(valid.status, OutputAvailabilityStatus.AVAILABLE)

    def test_binding_identity_grammar_and_canonical_collections(self):
        first = binding(
            relationship_semantic_ids=(RELATIONSHIP_B, RELATIONSHIP_A, RELATIONSHIP_B),
            relationship_evidence_ids=(EVIDENCE_B, EVIDENCE_A, EVIDENCE_B),
        )
        second = binding(
            relationship_semantic_ids=(RELATIONSHIP_A, RELATIONSHIP_B),
            relationship_evidence_ids=(EVIDENCE_A, EVIDENCE_B),
        )
        self.assertEqual(first, second)
        for changes in (
            {"dependency_id": "primary"},
            {"scope": {"subject_kind": "ISSUER"}},
            {"relationship_semantic_ids": [RELATIONSHIP_A]},
            {"relationship_semantic_ids": ("not-a-hash",)},
            {"relationship_evidence_ids": ("A" * 64,)},
        ):
            with self.subTest(changes=changes), self.assertRaises(AssemblyContractError):
                binding(**changes)

    def test_duplicate_and_unknown_bindings_are_malformed(self):
        with self.assertRaises(AssemblyContractError):
            assemble(bindings=(binding(), binding()))
        with self.assertRaises(AssemblyContractError):
            assemble(bindings=(binding(dependency_id="UNKNOWN_ROLE"),))

    def test_missing_binding_is_explainably_unavailable(self):
        result = assemble(bindings=())
        resolution = result.dependency_resolutions[0]
        self.assertEqual(result.status, OutputAvailabilityStatus.UNAVAILABLE)
        self.assertEqual(
            resolution.status,
            DependencyResolutionStatus.UNSATISFIED_MISSING_BINDING,
        )
        self.assertEqual(resolution.assembler_reason_codes, ("MISSING_DEPENDENCY_BINDING",))
        self.assertIn("MISSING_DEPENDENCY_BINDING", result.reason_codes)

    def test_subject_kind_mismatch_is_unavailable_without_identity_inference(self):
        bound_scope = scope(subject_kind="LISTING", subject_identity=SUBJECT_B)
        result = assemble(bindings=(binding(scope=bound_scope),))
        resolution = result.dependency_resolutions[0]
        self.assertEqual(result.status, OutputAvailabilityStatus.UNAVAILABLE)
        self.assertEqual(
            resolution.status,
            DependencyResolutionStatus.UNSATISFIED_SUBJECT_KIND,
        )
        self.assertEqual(resolution.assembler_reason_codes, ("SUBJECT_KIND_MISMATCH",))

    def test_same_scope_needs_no_relationship_but_cross_scope_needs_both_sides(self):
        self.assertEqual(assemble().status, OutputAvailabilityStatus.AVAILABLE)
        cross_scope = scope(subject_identity=SUBJECT_B)
        cross_assessment = assessment(scope=cross_scope)
        variants = (
            binding(scope=cross_scope),
            binding(
                scope=cross_scope,
                relationship_semantic_ids=(RELATIONSHIP_A,),
            ),
            binding(
                scope=cross_scope,
                relationship_evidence_ids=(EVIDENCE_B,),
            ),
        )
        for item in variants:
            with self.subTest(item=item):
                result = assemble(bindings=(item,), assessments=(cross_assessment,))
                self.assertEqual(result.status, OutputAvailabilityStatus.UNAVAILABLE)
                self.assertEqual(
                    result.dependency_resolutions[0].status,
                    DependencyResolutionStatus.UNSATISFIED_RELATIONSHIP,
                )
        valid_binding = binding(
            scope=cross_scope,
            relationship_semantic_ids=(RELATIONSHIP_A,),
            relationship_evidence_ids=(EVIDENCE_B,),
        )
        valid = assemble(bindings=(valid_binding,), assessments=(cross_assessment,))
        self.assertEqual(valid.status, OutputAvailabilityStatus.AVAILABLE)

    def test_exact_authority_boundary_equality_is_required_including_none(self):
        mismatches = (
            scope(subject_identity=SUBJECT_B, authority_boundary="CURRENT_T2"),
            scope(subject_identity=SUBJECT_B, authority_boundary=None),
        )
        for bound_scope in mismatches:
            with self.subTest(bound_scope=bound_scope):
                result = assemble(
                    bindings=(binding(
                        scope=bound_scope,
                        relationship_semantic_ids=(RELATIONSHIP_A,),
                        relationship_evidence_ids=(EVIDENCE_A,),
                    ),),
                    assessments=(assessment(scope=bound_scope),),
                )
                self.assertEqual(result.status, OutputAvailabilityStatus.UNAVAILABLE)
                self.assertEqual(
                    result.dependency_resolutions[0].status,
                    DependencyResolutionStatus.UNSATISFIED_BOUNDARY,
                )
                self.assertIn("AUTHORITY_BOUNDARY_MISMATCH", result.reason_codes)
        output = scope(authority_boundary=None)
        valid = assemble(
            output_scope=output,
            bindings=(binding(scope=output),),
            assessments=(assessment(scope=output),),
        )
        self.assertEqual(valid.status, OutputAvailabilityStatus.AVAILABLE)

    def test_matching_requires_exact_capability_and_exact_bound_scope(self):
        wrong_capability = assessment(capability_id="OTHER_CAPABILITY")
        wrong_scope = assessment(scope=scope(subject_identity=SUBJECT_B))
        for supplied in ((), (wrong_capability, wrong_scope)):
            with self.subTest(supplied=supplied):
                result = assemble(assessments=supplied)
                self.assertEqual(result.status, OutputAvailabilityStatus.UNAVAILABLE)
                self.assertEqual(
                    result.dependency_resolutions[0].status,
                    DependencyResolutionStatus.UNSATISFIED_MISSING_ASSESSMENT,
                )
                self.assertIn("CAPABILITY_ASSESSMENT_MISSING", result.reason_codes)

    def test_supported_and_explicitly_accepted_partial_satisfy(self):
        supported = assemble()
        self.assertEqual(supported.status, OutputAvailabilityStatus.AVAILABLE)
        self.assertEqual(
            supported.dependency_resolutions[0].status,
            DependencyResolutionStatus.SATISFIED_SUPPORTED,
        )
        partial_requirement = dependency(
            accepted_states=(CapabilityState.SUPPORTED, CapabilityState.PARTIAL)
        )
        partial = assemble(
            dependency_contract=contract(requirements=(partial_requirement,)),
            assessments=(assessment(CapabilityState.PARTIAL),),
        )
        self.assertEqual(
            partial.status,
            OutputAvailabilityStatus.AVAILABLE_WITH_LIMITATIONS,
        )
        self.assertEqual(
            partial.dependency_resolutions[0].status,
            DependencyResolutionStatus.SATISFIED_PARTIAL,
        )
        self.assertEqual(partial.reason_codes, ("BOUNDED_COVERAGE",))
        self.assertEqual(partial.limitation_codes, ("HISTORY_INCOMPLETE",))

    def test_unaccepted_states_never_satisfy_and_retain_upstream_context(self):
        states = (
            CapabilityState.PARTIAL,
            CapabilityState.UNSUPPORTED,
            CapabilityState.UNAVAILABLE,
            CapabilityState.REVIEW_REQUIRED,
            CapabilityState.CONFLICTED,
        )
        for state in states:
            item = assessment(state)
            with self.subTest(state=state):
                result = assemble(assessments=(item,))
                resolution = result.dependency_resolutions[0]
                self.assertEqual(result.status, OutputAvailabilityStatus.UNAVAILABLE)
                self.assertEqual(
                    resolution.status,
                    DependencyResolutionStatus.UNSATISFIED_STATE,
                )
                self.assertEqual(resolution.upstream_state, state)
                self.assertIn("UPSTREAM_NOT_RESOLVED" if state is not CapabilityState.PARTIAL else "BOUNDED_COVERAGE", result.reason_codes)
                self.assertIn("CAPABILITY_STATE_NOT_ACCEPTED", result.reason_codes)
                if state is CapabilityState.PARTIAL:
                    self.assertIn("HISTORY_INCOMPLETE", result.limitation_codes)

    def test_equivalent_recaptures_are_accepted_and_all_evidence_is_retained(self):
        first = assessment(supporting_evidence_ids=(EVIDENCE_A,))
        recapture = assessment(supporting_evidence_ids=(EVIDENCE_B,))
        result = assemble(assessments=(recapture, first))
        resolution = result.dependency_resolutions[0]
        self.assertEqual(result.status, OutputAvailabilityStatus.AVAILABLE)
        self.assertEqual(resolution.assessment_semantic_ids, (first.semantic_id,))
        self.assertEqual(
            resolution.assessment_evidence_ids,
            tuple(sorted((first.evidence_id, recapture.evidence_id))),
        )

    def test_semantically_different_matches_are_ambiguous_without_order_or_majority(self):
        first = assessment(supporting_semantic_ids=(SEMANTIC_A,))
        second = assessment(supporting_semantic_ids=(SEMANTIC_B,))
        results = (
            assemble(assessments=(first, second)),
            assemble(assessments=(second, first)),
            assemble(assessments=(first, first, second)),
        )
        for result in results:
            self.assertEqual(result.status, OutputAvailabilityStatus.UNAVAILABLE)
            self.assertEqual(
                result.dependency_resolutions[0].status,
                DependencyResolutionStatus.UNSATISFIED_AMBIGUOUS_ASSESSMENT,
            )
            self.assertIn("AMBIGUOUS_CAPABILITY_ASSESSMENT", result.reason_codes)
        self.assertEqual(len({item.semantic_id for item in results}), 1)
        self.assertEqual(len({item.evidence_id for item in results}), 1)

    def test_status_is_conjunctive_and_independent_assessments_are_not_modified(self):
        second_requirement = dependency(
            dependency_id="SECONDARY_FACTS",
            capability_id="SECOND_FICTIONAL_HISTORY",
        )
        item_contract = contract(requirements=(dependency(), second_requirement))
        primary_assessment = assessment()
        before = primary_assessment
        result = assemble(
            dependency_contract=item_contract,
            bindings=(binding(),),
            assessments=(primary_assessment,),
        )
        self.assertEqual(result.status, OutputAvailabilityStatus.UNAVAILABLE)
        self.assertEqual(primary_assessment, before)
        self.assertEqual(primary_assessment.state, CapabilityState.SUPPORTED)
        statuses = {
            item.dependency_id: item.status for item in result.dependency_resolutions
        }
        self.assertEqual(
            statuses["PRIMARY_FACTS"],
            DependencyResolutionStatus.SATISFIED_SUPPORTED,
        )
        self.assertEqual(
            statuses["SECONDARY_FACTS"],
            DependencyResolutionStatus.UNSATISFIED_MISSING_BINDING,
        )

    def test_supported_plus_accepted_partial_derives_available_with_limitations(self):
        partial_requirement = dependency(
            dependency_id="SECONDARY_FACTS",
            capability_id="SECOND_FICTIONAL_HISTORY",
            accepted_states=(CapabilityState.SUPPORTED, CapabilityState.PARTIAL),
        )
        item_contract = contract(requirements=(dependency(), partial_requirement))
        second_binding = binding(
            dependency_id="SECONDARY_FACTS",
            scope=scope(subject_identity=SUBJECT_B),
            relationship_semantic_ids=(RELATIONSHIP_A,),
            relationship_evidence_ids=(EVIDENCE_C,),
        )
        partial_assessment = assessment(
            CapabilityState.PARTIAL,
            capability_id="SECOND_FICTIONAL_HISTORY",
            scope=second_binding.scope,
            reason_codes=("Z_REASON", "A_REASON"),
            limitation_codes=("Z_LIMIT", "A_LIMIT"),
        )
        result = assemble(
            dependency_contract=item_contract,
            bindings=(binding(), second_binding),
            assessments=(assessment(), partial_assessment),
        )
        self.assertEqual(
            result.status,
            OutputAvailabilityStatus.AVAILABLE_WITH_LIMITATIONS,
        )
        self.assertEqual(result.reason_codes, ("A_REASON", "Z_REASON"))
        self.assertEqual(result.limitation_codes, ("A_LIMIT", "Z_LIMIT"))

    def test_semantic_and_evidence_identity_separate_recapture(self):
        first_assessment = assessment(supporting_evidence_ids=(EVIDENCE_A,))
        recaptured_assessment = assessment(supporting_evidence_ids=(EVIDENCE_B,))
        first = assemble(assessments=(first_assessment,))
        recaptured = assemble(assessments=(recaptured_assessment,))
        self.assertEqual(first.semantic_id, recaptured.semantic_id)
        self.assertNotEqual(first.evidence_id, recaptured.evidence_id)
        self.assertRegex(first.semantic_id, r"^[0-9a-f]{64}$")
        self.assertRegex(first.evidence_id, r"^[0-9a-f]{64}$")

    def test_relationship_evidence_changes_only_evidence_identity(self):
        cross_scope = scope(subject_identity=SUBJECT_B)
        first_binding = binding(
            scope=cross_scope,
            relationship_semantic_ids=(RELATIONSHIP_A,),
            relationship_evidence_ids=(EVIDENCE_A,),
        )
        recaptured_binding = binding(
            scope=cross_scope,
            relationship_semantic_ids=(RELATIONSHIP_A,),
            relationship_evidence_ids=(EVIDENCE_B,),
        )
        item_assessment = assessment(scope=cross_scope)
        first = assemble(bindings=(first_binding,), assessments=(item_assessment,))
        recaptured = assemble(
            bindings=(recaptured_binding,), assessments=(item_assessment,)
        )
        self.assertEqual(first.semantic_id, recaptured.semantic_id)
        self.assertNotEqual(first.evidence_id, recaptured.evidence_id)
        changed_semantic_binding = binding(
            scope=cross_scope,
            relationship_semantic_ids=(RELATIONSHIP_B,),
            relationship_evidence_ids=(EVIDENCE_A,),
        )
        changed_semantic = assemble(
            bindings=(changed_semantic_binding,), assessments=(item_assessment,)
        )
        self.assertNotEqual(first.semantic_id, changed_semantic.semantic_id)

    def test_scope_contract_and_dependency_state_changes_change_semantic_identity(self):
        base = assemble()
        other_output_scope = scope(subject_identity=SUBJECT_C)
        scoped = assemble(
            output_scope=other_output_scope,
            bindings=(binding(scope=other_output_scope),),
            assessments=(assessment(scope=other_output_scope),),
        )
        changed_contract = assemble(
            dependency_contract=contract(output_id="OTHER_FICTIONAL_OUTPUT")
        )
        partial_requirement = dependency(
            accepted_states=(CapabilityState.SUPPORTED, CapabilityState.PARTIAL)
        )
        changed_state = assemble(
            dependency_contract=contract(requirements=(partial_requirement,)),
            assessments=(assessment(CapabilityState.PARTIAL),),
        )
        for variant in (scoped, changed_contract, changed_state):
            with self.subTest(variant=variant):
                self.assertNotEqual(base.semantic_id, variant.semantic_id)

    def test_bindings_and_assessments_are_caller_order_independent(self):
        second_requirement = dependency(
            dependency_id="SECONDARY_FACTS",
            capability_id="SECOND_FICTIONAL_HISTORY",
        )
        item_contract = contract(requirements=(dependency(), second_requirement))
        second_scope = scope(subject_identity=SUBJECT_B)
        second_binding = binding(
            dependency_id="SECONDARY_FACTS",
            scope=second_scope,
            relationship_semantic_ids=(RELATIONSHIP_A,),
            relationship_evidence_ids=(EVIDENCE_B,),
        )
        second_assessment = assessment(
            capability_id="SECOND_FICTIONAL_HISTORY", scope=second_scope
        )
        first = assemble(
            dependency_contract=item_contract,
            bindings=(binding(), second_binding),
            assessments=(assessment(), second_assessment),
        )
        second = assemble(
            dependency_contract=item_contract,
            bindings=(second_binding, binding()),
            assessments=(second_assessment, assessment()),
        )
        self.assertEqual(first, second)
        self.assertEqual(first.semantic_id, second.semantic_id)
        self.assertEqual(first.evidence_id, second.evidence_id)

    def test_no_economic_value_score_authority_or_execution_surface(self):
        names = set()
        for record in (DependencyBinding, DependencyResolution, OutputAvailability):
            names.update(field.name for field in fields(record))
        for prohibited in (
            "value", "score", "weight", "percentage", "expected_return",
            "quality", "ranking", "recommendation", "allocation", "investable",
            "admitted", "opportunity_set_eligible", "buy", "sell",
            "execution_authority", "production_authority", "promotion_authority",
            "ticker", "cik", "name",
        ):
            self.assertNotIn(prohibited, names)
        parameters = inspect.signature(assemble_output_availability).parameters
        for prohibited in (
            "execute_if_available", "calculator", "analysis_fn", "resolver_callback"
        ):
            self.assertNotIn(prohibited, parameters)
        for prohibited in (
            "FULL_ANALYSIS_ELIGIBLE", "PARTIAL_ANALYSIS", "RESEARCH_CANDIDATE",
            "UNSUPPORTED_RESEARCH_PROFILE",
        ):
            self.assertFalse(hasattr(analysis_capabilities, prohibited))

    def test_module_is_pure_and_respects_source_neutral_boundaries(self):
        module_path = ROOT / "analysis_capabilities/assembler.py"
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
            {
                "__future__", "dataclasses", "enum", "hashlib", "json", "re",
                "contracts", "dependencies",
            },
        )
        for forbidden in (
            "economic_facts", "from src", "import src", "pit_comparison",
            "socket", "urllib", "requests", "pathlib", "open(", "getenv",
            "environ", "datetime", "time.", "subprocess", "provider",
        ):
            self.assertNotIn(forbidden, source)

    def test_identity_is_deterministic_across_python_hash_seeds(self):
        source = textwrap.dedent(
            f"""
            import json
            from analysis_capabilities import *
            output_scope = CapabilityScope('ISSUER', '{SUBJECT_A}', 'CURRENT_T1')
            requirement = CapabilityDependency(
                'PRIMARY_FACTS', 'FICTIONAL_FACT_HISTORY', 'ISSUER',
                (CapabilityState.PARTIAL, CapabilityState.SUPPORTED))
            contract = OutputDependencyContract(
                DEPENDENCY_CONTRACT_VERSION, 'FICTIONAL_ANALYTICAL_OUTPUT',
                'ISSUER', (requirement,))
            binding = DependencyBinding('PRIMARY_FACTS', output_scope)
            item = CapabilityAssessment(
                CAPABILITY_CONTRACT_VERSION, 'FICTIONAL_FACT_HISTORY', output_scope,
                CapabilityState.PARTIAL, ('{SEMANTIC_A}',), ('{EVIDENCE_A}',),
                ('Z_REASON', 'A_REASON'), ('Z_LIMIT', 'A_LIMIT'))
            result = assemble_output_availability(
                contract, output_scope, (binding,), (item,))
            print(json.dumps([result.semantic_id, result.evidence_id,
                              result.reason_codes, result.limitation_codes]))
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
