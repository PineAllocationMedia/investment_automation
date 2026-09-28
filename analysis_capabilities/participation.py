"""Pure classification of one subject's descriptive research participation.

The classifier consumes one reviewed research-profile contract, one explicit
profile-support capability assessment, and independently assembled analytical-
output availabilities.  It performs no economic calculation and grants no
admission, recommendation, allocation, execution, or production authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
import json
import re

from .assembler import OutputAvailability, OutputAvailabilityStatus
from .contracts import CapabilityAssessment, CapabilityScope, CapabilityState


RESEARCH_PARTICIPATION_CONTRACT_VERSION = "2026-09-28-research-participation-v1"

__all__ = (
    "RESEARCH_PARTICIPATION_CONTRACT_VERSION",
    "ResearchParticipationContractError",
    "ResearchParticipationState",
    "ResearchOutputRequirement",
    "ResearchParticipationContract",
    "ResearchParticipation",
    "classify_research_participation",
)

_CODE = re.compile(r"[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*", re.ASCII)
_IDENTITY = re.compile(r"[0-9a-f]{64}", re.ASCII)
_CONTRACT_SEMANTIC_DOMAIN = b"pam:research-participation-contract:semantic:v1\0"
_SEMANTIC_DOMAIN = b"pam:research-participation:semantic:v1\0"
_EVIDENCE_DOMAIN = b"pam:research-participation:evidence:v1\0"


class ResearchParticipationContractError(ValueError):
    """Malformed or structurally unsupported participation request."""


class ResearchParticipationState(StrEnum):
    """Closed descriptive states with no economic or ranking order."""

    FULL_ANALYSIS_ELIGIBLE = "FULL_ANALYSIS_ELIGIBLE"
    PARTIAL_ANALYSIS = "PARTIAL_ANALYSIS"
    RESEARCH_CANDIDATE = "RESEARCH_CANDIDATE"
    UNSUPPORTED_RESEARCH_PROFILE = "UNSUPPORTED_RESEARCH_PROFILE"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ResearchParticipationContractError(message)


def _code(value: object, label: str) -> str:
    _require(
        type(value) is str
        and len(value) <= 128
        and _CODE.fullmatch(value) is not None,
        f"{label}: canonical uppercase ASCII identifier required",
    )
    return value


def _identity(value: object, label: str) -> str:
    _require(
        type(value) is str and _IDENTITY.fullmatch(value) is not None,
        f"{label}: lowercase SHA-256 semantic identity required",
    )
    return value


def _scope_payload(scope: CapabilityScope) -> dict[str, object]:
    return {
        "subject_kind": scope.subject_kind,
        "subject_identity": scope.subject_identity,
        "authority_boundary": scope.authority_boundary,
        "supporting_semantic_ids": scope.supporting_semantic_ids,
    }


def _digest(domain: bytes, value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(domain + payload).hexdigest()


@dataclass(frozen=True, slots=True)
class ResearchOutputRequirement:
    """One exact output and its reviewed dependency-contract semantics."""

    output_id: str
    dependency_contract_semantic_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "output_id", _code(self.output_id, "output_id"))
        object.__setattr__(
            self,
            "dependency_contract_semantic_id",
            _identity(
                self.dependency_contract_semantic_id,
                "dependency_contract_semantic_id",
            ),
        )


@dataclass(frozen=True, slots=True)
class ResearchParticipationContract:
    """Reviewed declaration of one complete analytical research profile."""

    contract_version: str
    profile_id: str
    subject_kind: str
    profile_support_capability_id: str
    output_requirements: tuple[ResearchOutputRequirement, ...]

    def __post_init__(self) -> None:
        _require(
            type(self.contract_version) is str
            and self.contract_version == RESEARCH_PARTICIPATION_CONTRACT_VERSION,
            "Unsupported research participation contract version",
        )
        object.__setattr__(self, "profile_id", _code(self.profile_id, "profile_id"))
        object.__setattr__(
            self, "subject_kind", _code(self.subject_kind, "subject_kind")
        )
        object.__setattr__(
            self,
            "profile_support_capability_id",
            _code(
                self.profile_support_capability_id,
                "profile_support_capability_id",
            ),
        )
        _require(
            type(self.output_requirements) is tuple,
            "output_requirements: tuple required",
        )
        _require(
            bool(self.output_requirements)
            and all(
                type(item) is ResearchOutputRequirement
                for item in self.output_requirements
            ),
            "output_requirements: nonempty exact ResearchOutputRequirement tuple required",
        )
        output_ids = tuple(item.output_id for item in self.output_requirements)
        _require(
            len(output_ids) == len(set(output_ids)),
            "output_requirements: output_id values must be unique",
        )
        object.__setattr__(
            self,
            "output_requirements",
            tuple(sorted(self.output_requirements, key=lambda item: item.output_id)),
        )

    @property
    def semantic_id(self) -> str:
        """Deterministic identity of the complete reviewed methodology."""
        return _digest(
            _CONTRACT_SEMANTIC_DOMAIN,
            {
                "contract_version": self.contract_version,
                "profile_id": self.profile_id,
                "subject_kind": self.subject_kind,
                "profile_support_capability_id": (
                    self.profile_support_capability_id
                ),
                "output_requirements": [
                    {
                        "output_id": item.output_id,
                        "dependency_contract_semantic_id": (
                            item.dependency_contract_semantic_id
                        ),
                    }
                    for item in self.output_requirements
                ],
            },
        )


def _validate_inputs(
    contract: object,
    subject_scope: object,
    profile_support_assessment: object,
    output_availabilities: object,
) -> tuple[OutputAvailability, ...]:
    _require(
        type(contract) is ResearchParticipationContract,
        "Exact ResearchParticipationContract required",
    )
    _require(type(subject_scope) is CapabilityScope, "Exact CapabilityScope required")
    _require(
        type(profile_support_assessment) is CapabilityAssessment,
        "Exact CapabilityAssessment required",
    )
    _require(
        type(output_availabilities) is tuple,
        "output_availabilities: tuple required",
    )
    _require(
        all(type(item) is OutputAvailability for item in output_availabilities),
        "output_availabilities: exact OutputAvailability instances required",
    )
    _require(
        subject_scope.subject_kind == contract.subject_kind,
        "subject_scope subject_kind must equal contract subject_kind",
    )
    _require(
        profile_support_assessment.capability_id
        == contract.profile_support_capability_id,
        "profile-support capability must equal contract capability",
    )
    _require(
        profile_support_assessment.scope == subject_scope,
        "profile-support assessment scope must equal subject_scope",
    )

    requirements = {item.output_id: item for item in contract.output_requirements}
    output_ids = tuple(item.output_id for item in output_availabilities)
    _require(
        len(output_ids) == len(set(output_ids)),
        "output_availabilities: output_id values must be unique",
    )
    for output in output_availabilities:
        _require(
            output.output_scope == subject_scope,
            "every output availability scope must equal subject_scope",
        )
        _require(
            output.output_id in requirements,
            "output availability is not declared by participation contract",
        )
        _require(
            output.dependency_contract_semantic_id
            == requirements[output.output_id].dependency_contract_semantic_id,
            "output dependency-contract semantic identity does not match contract",
        )
    return tuple(sorted(output_availabilities, key=lambda item: item.output_id))


@dataclass(frozen=True, slots=True)
class ResearchParticipation:
    """Immutable inputs whose participation result is always derived."""

    classifier_contract_version: str
    contract: ResearchParticipationContract
    subject_scope: CapabilityScope
    profile_support_assessment: CapabilityAssessment
    output_availabilities: tuple[OutputAvailability, ...]

    def __post_init__(self) -> None:
        _require(
            type(self.classifier_contract_version) is str
            and self.classifier_contract_version
            == RESEARCH_PARTICIPATION_CONTRACT_VERSION,
            "Unsupported research participation classifier version",
        )
        canonical_outputs = _validate_inputs(
            self.contract,
            self.subject_scope,
            self.profile_support_assessment,
            self.output_availabilities,
        )
        object.__setattr__(self, "output_availabilities", canonical_outputs)

    @property
    def state(self) -> ResearchParticipationState:
        """Derive descriptive participation with explicit unsupported precedence."""
        if self.profile_support_assessment.state is CapabilityState.UNSUPPORTED:
            return ResearchParticipationState.UNSUPPORTED_RESEARCH_PROFILE

        by_id = {item.output_id: item for item in self.output_availabilities}
        all_fully_available = all(
            requirement.output_id in by_id
            and by_id[requirement.output_id].status
            is OutputAvailabilityStatus.AVAILABLE
            for requirement in self.contract.output_requirements
        )
        if (
            self.profile_support_assessment.state is CapabilityState.SUPPORTED
            and all_fully_available
        ):
            return ResearchParticipationState.FULL_ANALYSIS_ELIGIBLE

        if any(
            item.status
            in (
                OutputAvailabilityStatus.AVAILABLE,
                OutputAvailabilityStatus.AVAILABLE_WITH_LIMITATIONS,
            )
            for item in self.output_availabilities
        ):
            return ResearchParticipationState.PARTIAL_ANALYSIS
        return ResearchParticipationState.RESEARCH_CANDIDATE

    @property
    def reason_codes(self) -> tuple[str, ...]:
        """Deterministic result-level reasons without economic criticism."""
        if self.state is ResearchParticipationState.FULL_ANALYSIS_ELIGIBLE:
            return ()
        if self.state is ResearchParticipationState.UNSUPPORTED_RESEARCH_PROFILE:
            return tuple(
                sorted(
                    {
                        "RESEARCH_PROFILE_UNSUPPORTED",
                        *self.profile_support_assessment.reason_codes,
                    }
                )
            )

        reasons = set()
        if self.state is ResearchParticipationState.PARTIAL_ANALYSIS:
            reasons.add("COMPLETE_RESEARCH_PROFILE_NOT_SATISFIED")
        else:
            reasons.add("NO_MEANINGFUL_ANALYTICAL_OUTPUT_AVAILABLE")
        if self.profile_support_assessment.state is not CapabilityState.SUPPORTED:
            reasons.update(self.profile_support_assessment.reason_codes)
        supplied_ids = {item.output_id for item in self.output_availabilities}
        if any(
            item.output_id not in supplied_ids
            for item in self.contract.output_requirements
        ):
            reasons.add("REQUIRED_OUTPUT_MISSING")
        for output in self.output_availabilities:
            if output.status is not OutputAvailabilityStatus.AVAILABLE:
                reasons.update(output.reason_codes)
        return tuple(sorted(reasons))

    @property
    def limitation_codes(self) -> tuple[str, ...]:
        """Preserve relevant upstream limitations without inventing absence limits."""
        if self.state is ResearchParticipationState.FULL_ANALYSIS_ELIGIBLE:
            return ()
        limitations = set(self.profile_support_assessment.limitation_codes)
        for output in self.output_availabilities:
            if output.status is not OutputAvailabilityStatus.AVAILABLE:
                limitations.update(output.limitation_codes)
        return tuple(sorted(limitations))

    def _output_payload(self, *, include_evidence: bool) -> list[dict[str, str]]:
        payload = []
        for output in self.output_availabilities:
            item = {
                "output_id": output.output_id,
                "semantic_id": output.semantic_id,
            }
            if include_evidence:
                item["evidence_id"] = output.evidence_id
            payload.append(item)
        return payload

    @property
    def semantic_id(self) -> str:
        """Identity of participation meaning, excluding exact recapture IDs."""
        return _digest(
            _SEMANTIC_DOMAIN,
            {
                "classifier_contract_version": self.classifier_contract_version,
                "participation_contract_semantic_id": self.contract.semantic_id,
                "subject_scope": _scope_payload(self.subject_scope),
                "profile_support_assessment_semantic_id": (
                    self.profile_support_assessment.semantic_id
                ),
                "state": self.state.value,
                "output_availabilities": self._output_payload(
                    include_evidence=False
                ),
                "reason_codes": self.reason_codes,
                "limitation_codes": self.limitation_codes,
            },
        )

    @property
    def evidence_id(self) -> str:
        """Identity additionally binding all exact upstream evidence captures."""
        return _digest(
            _EVIDENCE_DOMAIN,
            {
                "semantic_id": self.semantic_id,
                "profile_support_assessment_evidence_id": (
                    self.profile_support_assessment.evidence_id
                ),
                "output_availabilities": self._output_payload(
                    include_evidence=True
                ),
            },
        )


def classify_research_participation(
    contract: ResearchParticipationContract,
    subject_scope: CapabilityScope,
    profile_support_assessment: CapabilityAssessment,
    output_availabilities: tuple[OutputAvailability, ...],
) -> ResearchParticipation:
    """Classify one subject without calculating economics or granting authority."""
    return ResearchParticipation(
        classifier_contract_version=RESEARCH_PARTICIPATION_CONTRACT_VERSION,
        contract=contract,
        subject_scope=subject_scope,
        profile_support_assessment=profile_support_assessment,
        output_availabilities=output_availabilities,
    )
