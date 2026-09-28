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
from analysis_capabilities import participation
from analysis_capabilities import (
    ASSEMBLER_CONTRACT_VERSION,
    CAPABILITY_CONTRACT_VERSION,
    DEPENDENCY_CONTRACT_VERSION,
    RESEARCH_PARTICIPATION_CONTRACT_VERSION,
    CapabilityAssessment,
    CapabilityDependency,
    CapabilityScope,
    CapabilityState,
    DependencyBinding,
    OutputAvailability,
    OutputAvailabilityStatus,
    OutputDependencyContract,
    ResearchOutputRequirement,
    ResearchParticipation,
    ResearchParticipationContract,
    ResearchParticipationContractError,
    ResearchParticipationState,
    assemble_output_availability,
    classify_research_participation,
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
        "subject_kind": "RESEARCH_SUBJECT",
        "subject_identity": SUBJECT_A,
        "authority_boundary": "CURRENT_T1",
        "supporting_semantic_ids": (),
    }
    values.update(changes)
    return CapabilityScope(**values)


def profile_assessment(state=CapabilityState.SUPPORTED, **changes):
    values = {
        "contract_version": CAPABILITY_CONTRACT_VERSION,
        "capability_id": "FICTIONAL_PROFILE_SUPPORT",
        "scope": scope(),
        "state": state,
        "supporting_semantic_ids": (SEMANTIC_A,),
        "supporting_evidence_ids": (EVIDENCE_A,),
        "reason_codes": (),
        "limitation_codes": (),
    }
    if state is CapabilityState.PARTIAL:
        values.update(
            reason_codes=("PROFILE_PARTIAL",),
            limitation_codes=("PROFILE_LIMITED",),
        )
    elif state is not CapabilityState.SUPPORTED:
        values.update(reason_codes=("PROFILE_NOT_RESOLVED",))
        if state in (CapabilityState.UNSUPPORTED, CapabilityState.UNAVAILABLE):
            values.update(
                supporting_semantic_ids=(), supporting_evidence_ids=()
            )
    values.update(changes)
    return CapabilityAssessment(**values)


def output_contract(output_id):
    dependency = CapabilityDependency(
        dependency_id="FICTIONAL_INPUT",
        capability_id=f"{output_id}_CAPABILITY",
        subject_kind="RESEARCH_SUBJECT",
        accepted_states=(CapabilityState.SUPPORTED, CapabilityState.PARTIAL),
    )
    return OutputDependencyContract(
        contract_version=DEPENDENCY_CONTRACT_VERSION,
        output_id=output_id,
        output_subject_kind="RESEARCH_SUBJECT",
        requirements=(dependency,),
    )


def availability(output_id, status=OutputAvailabilityStatus.AVAILABLE, **changes):
    item_scope = changes.pop("output_scope", scope())
    dependency_contract = changes.pop(
        "dependency_contract", output_contract(output_id)
    )
    binding = DependencyBinding("FICTIONAL_INPUT", item_scope)
    assessment_values = {
        "contract_version": CAPABILITY_CONTRACT_VERSION,
        "capability_id": f"{output_id}_CAPABILITY",
        "scope": item_scope,
        "state": CapabilityState.SUPPORTED,
        "supporting_semantic_ids": (SEMANTIC_A,),
        "supporting_evidence_ids": (
            changes.pop("supporting_evidence_id", EVIDENCE_A),
        ),
    }
    if status is OutputAvailabilityStatus.AVAILABLE_WITH_LIMITATIONS:
        assessment_values.update(
            state=CapabilityState.PARTIAL,
            reason_codes=("OUTPUT_PARTIAL",),
            limitation_codes=("OUTPUT_LIMITED",),
        )
        assessments = (CapabilityAssessment(**assessment_values),)
    elif status is OutputAvailabilityStatus.UNAVAILABLE:
        assessments = ()
    else:
        assessments = (CapabilityAssessment(**assessment_values),)
    result = assemble_output_availability(
        dependency_contract,
        item_scope,
        (binding,),
        assessments,
    )
    if changes:
        raise AssertionError(f"unused availability changes: {changes}")
    return result


def requirement(output_id):
    return ResearchOutputRequirement(output_id, output_contract(output_id).semantic_id)


def contract(**changes):
    values = {
        "contract_version": RESEARCH_PARTICIPATION_CONTRACT_VERSION,
        "profile_id": "FICTIONAL_RESEARCH_PROFILE",
        "subject_kind": "RESEARCH_SUBJECT",
        "profile_support_capability_id": "FICTIONAL_PROFILE_SUPPORT",
        "output_requirements": (
            requirement("FICTIONAL_ALPHA"),
            requirement("FICTIONAL_BETA"),
        ),
    }
    values.update(changes)
    return ResearchParticipationContract(**values)


def classify(**changes):
    values = {
        "contract": contract(),
        "subject_scope": scope(),
        "profile_support_assessment": profile_assessment(),
        "output_availabilities": (
            availability("FICTIONAL_ALPHA"),
            availability("FICTIONAL_BETA"),
        ),
    }
    values.update(changes)
    return classify_research_participation(**values)


class ResearchParticipationTests(unittest.TestCase):
    def test_exact_public_api_and_four_closed_states(self):
        self.assertEqual(
            participation.__all__,
            (
                "RESEARCH_PARTICIPATION_CONTRACT_VERSION",
                "ResearchParticipationContractError",
                "ResearchParticipationState",
                "ResearchOutputRequirement",
                "ResearchParticipationContract",
                "ResearchParticipation",
                "classify_research_participation",
            ),
        )
        for name in participation.__all__:
            self.assertIs(
                getattr(analysis_capabilities, name), getattr(participation, name)
            )
        self.assertEqual(
            tuple(state.value for state in ResearchParticipationState),
            (
                "FULL_ANALYSIS_ELIGIBLE",
                "PARTIAL_ANALYSIS",
                "RESEARCH_CANDIDATE",
                "UNSUPPORTED_RESEARCH_PROFILE",
            ),
        )

    def test_enum_declaration_order_is_not_used_as_a_ranking(self):
        source = (ROOT / "analysis_capabilities/participation.py").read_text()
        self.assertNotIn("_STATE_ORDER", source)
        self.assertNotIn("min(", inspect.getsource(ResearchParticipation.state.fget))
        self.assertNotIn("max(", inspect.getsource(ResearchParticipation.state.fget))

    def test_records_are_frozen_slotted_and_have_exact_fields(self):
        output_requirement = requirement("FICTIONAL_ALPHA")
        profile_contract = contract()
        result = classify()
        self.assertEqual(
            tuple(field.name for field in fields(ResearchOutputRequirement)),
            ("output_id", "dependency_contract_semantic_id"),
        )
        self.assertEqual(
            tuple(field.name for field in fields(ResearchParticipationContract)),
            (
                "contract_version",
                "profile_id",
                "subject_kind",
                "profile_support_capability_id",
                "output_requirements",
            ),
        )
        self.assertEqual(
            tuple(field.name for field in fields(ResearchParticipation)),
            (
                "classifier_contract_version",
                "contract",
                "subject_scope",
                "profile_support_assessment",
                "output_availabilities",
            ),
        )
        for item, name in (
            (output_requirement, "output_id"),
            (profile_contract, "profile_id"),
            (result, "subject_scope"),
        ):
            self.assertFalse(hasattr(item, "__dict__"))
            with self.assertRaises(FrozenInstanceError):
                setattr(item, name, "OTHER")

    def test_contract_version_and_canonical_codes_fail_closed(self):
        for version in ("future", "", 1, None):
            with self.subTest(version=version), self.assertRaises(
                ResearchParticipationContractError
            ):
                contract(contract_version=version)
        for field_name in (
            "profile_id",
            "subject_kind",
            "profile_support_capability_id",
        ):
            for value in ("lowercase", "HAS SPACE", "_LEADING", "ÉPS", "", 1):
                with self.subTest(field=field_name, value=value), self.assertRaises(
                    ResearchParticipationContractError
                ):
                    contract(**{field_name: value})
        with self.assertRaises(ResearchParticipationContractError):
            ResearchOutputRequirement("lowercase", SEMANTIC_A)
        with self.assertRaises(ResearchParticipationContractError):
            ResearchOutputRequirement("FICTIONAL_ALPHA", "A" * 64)

    def test_output_requirements_are_exact_nonempty_unique_and_sorted(self):
        for value in ([], (), [requirement("FICTIONAL_ALPHA")], (object(),)):
            with self.subTest(value=value), self.assertRaises(
                ResearchParticipationContractError
            ):
                contract(output_requirements=value)
        duplicate = requirement("FICTIONAL_ALPHA")
        with self.assertRaises(ResearchParticipationContractError):
            contract(output_requirements=(duplicate, duplicate))
        first = contract(
            output_requirements=(
                requirement("FICTIONAL_BETA"),
                requirement("FICTIONAL_ALPHA"),
            )
        )
        second = contract(
            output_requirements=(
                requirement("FICTIONAL_ALPHA"),
                requirement("FICTIONAL_BETA"),
            )
        )
        self.assertEqual(first, second)
        self.assertEqual(first.semantic_id, second.semantic_id)
        self.assertEqual(
            tuple(item.output_id for item in first.output_requirements),
            ("FICTIONAL_ALPHA", "FICTIONAL_BETA"),
        )

    def test_contract_semantic_identity_binds_every_declared_dimension(self):
        base = contract()
        variants = (
            contract(profile_id="OTHER_PROFILE"),
            contract(subject_kind="OTHER_SUBJECT"),
            contract(profile_support_capability_id="OTHER_PROFILE_SUPPORT"),
            contract(output_requirements=(requirement("FICTIONAL_ALPHA"),)),
            contract(output_requirements=(
                ResearchOutputRequirement("FICTIONAL_ALPHA", SEMANTIC_B),
                requirement("FICTIONAL_BETA"),
            )),
        )
        self.assertRegex(base.semantic_id, r"^[0-9a-f]{64}$")
        for variant in variants:
            with self.subTest(variant=variant):
                self.assertNotEqual(base.semantic_id, variant.semantic_id)

    def test_exact_classifier_input_types_fail_closed(self):
        invalid = (
            {"contract": object()},
            {"subject_scope": object()},
            {"profile_support_assessment": object()},
            {"output_availabilities": []},
            {"output_availabilities": (object(),)},
        )
        for changes in invalid:
            with self.subTest(changes=changes), self.assertRaises(
                ResearchParticipationContractError
            ):
                classify(**changes)
        with self.assertRaises(ResearchParticipationContractError):
            ResearchParticipation(
                "future", contract(), scope(), profile_assessment(), ()
            )

    def test_subject_profile_support_and_output_scopes_must_match_exactly(self):
        with self.assertRaises(ResearchParticipationContractError):
            classify(subject_scope=scope(subject_kind="OTHER_SUBJECT"))
        with self.assertRaises(ResearchParticipationContractError):
            classify(
                profile_support_assessment=profile_assessment(
                    capability_id="OTHER_PROFILE_SUPPORT"
                )
            )
        with self.assertRaises(ResearchParticipationContractError):
            classify(
                profile_support_assessment=profile_assessment(
                    scope=scope(subject_identity=SUBJECT_B)
                )
            )
        with self.assertRaises(ResearchParticipationContractError):
            classify(
                output_availabilities=(
                    availability(
                        "FICTIONAL_ALPHA",
                        output_scope=scope(subject_identity=SUBJECT_B),
                    ),
                )
            )

    def test_unknown_wrong_contract_and_duplicate_outputs_are_malformed(self):
        with self.assertRaises(ResearchParticipationContractError):
            classify(output_availabilities=(availability("FICTIONAL_UNKNOWN"),))
        wrong_contract = OutputDependencyContract(
            DEPENDENCY_CONTRACT_VERSION,
            "FICTIONAL_ALPHA",
            "RESEARCH_SUBJECT",
            (CapabilityDependency(
                "FICTIONAL_INPUT",
                "FICTIONAL_ALPHA_CAPABILITY",
                "RESEARCH_SUBJECT",
                (CapabilityState.SUPPORTED,),
            ),),
        )
        with self.assertRaises(ResearchParticipationContractError):
            classify(output_availabilities=(availability(
                "FICTIONAL_ALPHA", dependency_contract=wrong_contract
            ),))
        alpha = availability("FICTIONAL_ALPHA")
        with self.assertRaises(ResearchParticipationContractError):
            classify(output_availabilities=(alpha, alpha))

    def test_missing_required_output_is_not_malformed_and_is_explicit(self):
        result = classify(output_availabilities=(availability("FICTIONAL_ALPHA"),))
        self.assertEqual(result.state, ResearchParticipationState.PARTIAL_ANALYSIS)
        self.assertIn("REQUIRED_OUTPUT_MISSING", result.reason_codes)

    def test_only_explicit_unsupported_profile_yields_unsupported(self):
        states = tuple(CapabilityState)
        for state in states:
            result = classify(
                profile_support_assessment=profile_assessment(state),
                output_availabilities=(),
            )
            expected = (
                ResearchParticipationState.UNSUPPORTED_RESEARCH_PROFILE
                if state is CapabilityState.UNSUPPORTED
                else ResearchParticipationState.RESEARCH_CANDIDATE
            )
            with self.subTest(state=state):
                self.assertEqual(result.state, expected)
        unsupported = classify(
            profile_support_assessment=profile_assessment(CapabilityState.UNSUPPORTED),
            output_availabilities=(availability("FICTIONAL_ALPHA"),),
        )
        self.assertEqual(
            unsupported.state,
            ResearchParticipationState.UNSUPPORTED_RESEARCH_PROFILE,
        )
        self.assertEqual(len(unsupported.output_availabilities), 1)
        self.assertIn("RESEARCH_PROFILE_UNSUPPORTED", unsupported.reason_codes)

    def test_retained_output_object_is_not_modified(self):
        output = availability("FICTIONAL_ALPHA")
        before = output
        result = classify(output_availabilities=(output,))
        self.assertIs(result.output_availabilities[0], output)
        self.assertEqual(output, before)
        self.assertEqual(output.status, OutputAvailabilityStatus.AVAILABLE)

    def test_no_meaningful_output_yields_research_candidate(self):
        variants = (
            (profile_assessment(), ()),
            (profile_assessment(), (
                availability("FICTIONAL_ALPHA", OutputAvailabilityStatus.UNAVAILABLE),
                availability("FICTIONAL_BETA", OutputAvailabilityStatus.UNAVAILABLE),
            )),
            (profile_assessment(CapabilityState.UNAVAILABLE), ()),
            (profile_assessment(CapabilityState.REVIEW_REQUIRED), ()),
            (profile_assessment(CapabilityState.CONFLICTED), ()),
        )
        for profile_support, outputs in variants:
            with self.subTest(state=profile_support.state, outputs=len(outputs)):
                result = classify(
                    profile_support_assessment=profile_support,
                    output_availabilities=outputs,
                )
                self.assertEqual(
                    result.state, ResearchParticipationState.RESEARCH_CANDIDATE
                )
                self.assertIn(
                    "NO_MEANINGFUL_ANALYTICAL_OUTPUT_AVAILABLE",
                    result.reason_codes,
                )

    def test_any_meaningful_output_short_of_full_yields_partial(self):
        variants = (
            (availability("FICTIONAL_ALPHA"),),
            (availability(
                "FICTIONAL_ALPHA",
                OutputAvailabilityStatus.AVAILABLE_WITH_LIMITATIONS,
            ),),
            (
                availability("FICTIONAL_ALPHA"),
                availability("FICTIONAL_BETA", OutputAvailabilityStatus.UNAVAILABLE),
            ),
        )
        for outputs in variants:
            with self.subTest(statuses=tuple(item.status for item in outputs)):
                result = classify(output_availabilities=outputs)
                self.assertEqual(
                    result.state, ResearchParticipationState.PARTIAL_ANALYSIS
                )
                self.assertIn(
                    "COMPLETE_RESEARCH_PROFILE_NOT_SATISFIED",
                    result.reason_codes,
                )

    def test_full_requires_supported_profile_and_every_output_fully_available(self):
        full = classify()
        self.assertEqual(
            full.state, ResearchParticipationState.FULL_ANALYSIS_ELIGIBLE
        )
        self.assertEqual(full.reason_codes, ())
        self.assertEqual(full.limitation_codes, ())
        prevented = (
            {
                "output_availabilities": (
                    availability(
                        "FICTIONAL_ALPHA",
                        OutputAvailabilityStatus.AVAILABLE_WITH_LIMITATIONS,
                    ),
                    availability("FICTIONAL_BETA"),
                )
            },
            {"output_availabilities": (availability("FICTIONAL_ALPHA"),)},
            {"profile_support_assessment": profile_assessment(CapabilityState.PARTIAL)},
            {"profile_support_assessment": profile_assessment(CapabilityState.UNAVAILABLE)},
            {"profile_support_assessment": profile_assessment(CapabilityState.REVIEW_REQUIRED)},
            {"profile_support_assessment": profile_assessment(CapabilityState.CONFLICTED)},
        )
        for changes in prevented:
            with self.subTest(changes=changes):
                self.assertIsNot(
                    classify(**changes).state,
                    ResearchParticipationState.FULL_ANALYSIS_ELIGIBLE,
                )

    def test_reasons_and_limitations_propagate_deterministically(self):
        limited = availability(
            "FICTIONAL_ALPHA",
            OutputAvailabilityStatus.AVAILABLE_WITH_LIMITATIONS,
        )
        unavailable = availability(
            "FICTIONAL_BETA", OutputAvailabilityStatus.UNAVAILABLE
        )
        result = classify(
            profile_support_assessment=profile_assessment(CapabilityState.PARTIAL),
            output_availabilities=(unavailable, limited),
        )
        self.assertEqual(result.state, ResearchParticipationState.PARTIAL_ANALYSIS)
        self.assertIn("PROFILE_PARTIAL", result.reason_codes)
        self.assertIn("OUTPUT_PARTIAL", result.reason_codes)
        self.assertIn("CAPABILITY_ASSESSMENT_MISSING", result.reason_codes)
        self.assertIn("PROFILE_LIMITED", result.limitation_codes)
        self.assertIn("OUTPUT_LIMITED", result.limitation_codes)
        self.assertEqual(result.reason_codes, tuple(sorted(set(result.reason_codes))))
        self.assertEqual(
            result.limitation_codes, tuple(sorted(set(result.limitation_codes)))
        )

    def test_caller_order_does_not_change_result_or_identities(self):
        alpha = availability("FICTIONAL_ALPHA")
        beta = availability(
            "FICTIONAL_BETA", OutputAvailabilityStatus.AVAILABLE_WITH_LIMITATIONS
        )
        first = classify(output_availabilities=(beta, alpha))
        second = classify(output_availabilities=(alpha, beta))
        self.assertEqual(first, second)
        self.assertEqual(first.semantic_id, second.semantic_id)
        self.assertEqual(first.evidence_id, second.evidence_id)
        self.assertEqual(
            tuple(item.output_id for item in first.output_availabilities),
            ("FICTIONAL_ALPHA", "FICTIONAL_BETA"),
        )

    def test_profile_support_recapture_changes_only_evidence_identity(self):
        first = classify(profile_support_assessment=profile_assessment(
            supporting_evidence_ids=(EVIDENCE_A,)
        ))
        recapture = classify(profile_support_assessment=profile_assessment(
            supporting_evidence_ids=(EVIDENCE_B,)
        ))
        self.assertEqual(first.semantic_id, recapture.semantic_id)
        self.assertNotEqual(first.evidence_id, recapture.evidence_id)

    def test_output_recapture_changes_only_evidence_identity(self):
        first = classify(output_availabilities=(
            availability("FICTIONAL_ALPHA", supporting_evidence_id=EVIDENCE_A),
            availability("FICTIONAL_BETA"),
        ))
        recapture = classify(output_availabilities=(
            availability("FICTIONAL_ALPHA", supporting_evidence_id=EVIDENCE_B),
            availability("FICTIONAL_BETA"),
        ))
        self.assertEqual(first.semantic_id, recapture.semantic_id)
        self.assertNotEqual(first.evidence_id, recapture.evidence_id)

    def test_contract_output_and_profile_semantic_changes_change_result_semantic_id(self):
        base = classify()
        changed_contract = classify(contract=contract(profile_id="OTHER_PROFILE"))
        changed_output = classify(output_availabilities=(
            availability("FICTIONAL_ALPHA", OutputAvailabilityStatus.UNAVAILABLE),
            availability("FICTIONAL_BETA"),
        ))
        changed_profile = classify(
            profile_support_assessment=profile_assessment(
                CapabilityState.PARTIAL,
                reason_codes=("OTHER_PROFILE_REASON",),
                limitation_codes=("OTHER_PROFILE_LIMIT",),
            )
        )
        for variant in (changed_contract, changed_output, changed_profile):
            with self.subTest(variant=variant):
                self.assertNotEqual(base.semantic_id, variant.semantic_id)

    def test_no_score_rank_investment_recommendation_or_authority_surface(self):
        names = set()
        for record in (
            ResearchOutputRequirement,
            ResearchParticipationContract,
            ResearchParticipation,
        ):
            names.update(field.name for field in fields(record))
        for prohibited in (
            "weight", "score", "percentage", "threshold", "rank", "ranking",
            "admitted", "investable", "opportunity_set_eligible", "buy", "sell",
            "hold", "recommendation", "target_weight", "allocation", "execution",
            "production_authority", "promotion_authority", "ticker", "provider",
        ):
            self.assertNotIn(prohibited, names)
        parameters = inspect.signature(classify_research_participation).parameters
        for prohibited in ("supported", "qualified", "score", "weight"):
            self.assertNotIn(prohibited, parameters)

    def test_module_is_pure_source_neutral_and_has_no_production_profile(self):
        module_path = ROOT / "analysis_capabilities/participation.py"
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
                "assembler", "contracts",
            },
        )
        for forbidden in (
            "economic_facts", "from src", "import src", "pit_comparison",
            "from main", "import main",
            "socket", "urllib", "requests", "pathlib", "open(", "getenv",
            "environ", "datetime", "time.", "subprocess", "provider",
            "DEFAULT_RESEARCH_PROFILE", "ORDINARY_COMPOUNDER_RESEARCH_PROFILE",
            "PRODUCTION_PROFILE", "V2_COMPLETE_PROFILE",
        ):
            self.assertNotIn(forbidden, source)
        for prohibited in (
            "Confidence", "OpportunitySet", "opportunity_set_eligible",
            "DEFAULT_RESEARCH_PROFILE", "PRODUCTION_PROFILE",
        ):
            self.assertFalse(hasattr(analysis_capabilities, prohibited))

    def test_identity_is_deterministic_across_python_hash_seeds(self):
        source = textwrap.dedent(
            f"""
            import json
            from analysis_capabilities import *
            scope = CapabilityScope('RESEARCH_SUBJECT', '{SUBJECT_A}', 'CURRENT_T1')
            profile = CapabilityAssessment(
                CAPABILITY_CONTRACT_VERSION, 'FICTIONAL_PROFILE_SUPPORT', scope,
                CapabilityState.SUPPORTED, ('{SEMANTIC_A}',), ('{EVIDENCE_A}',))
            dep = CapabilityDependency(
                'FICTIONAL_INPUT', 'FICTIONAL_ALPHA_CAPABILITY',
                'RESEARCH_SUBJECT', (CapabilityState.SUPPORTED,))
            output_contract = OutputDependencyContract(
                DEPENDENCY_CONTRACT_VERSION, 'FICTIONAL_ALPHA',
                'RESEARCH_SUBJECT', (dep,))
            output_assessment = CapabilityAssessment(
                CAPABILITY_CONTRACT_VERSION, 'FICTIONAL_ALPHA_CAPABILITY', scope,
                CapabilityState.SUPPORTED, ('{SEMANTIC_B}',), ('{EVIDENCE_B}',))
            output = assemble_output_availability(
                output_contract, scope, (DependencyBinding('FICTIONAL_INPUT', scope),),
                (output_assessment,))
            requirement = ResearchOutputRequirement(
                'FICTIONAL_ALPHA', output_contract.semantic_id)
            contract = ResearchParticipationContract(
                RESEARCH_PARTICIPATION_CONTRACT_VERSION,
                'FICTIONAL_RESEARCH_PROFILE', 'RESEARCH_SUBJECT',
                'FICTIONAL_PROFILE_SUPPORT', (requirement,))
            result = classify_research_participation(
                contract, scope, profile, (output,))
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
