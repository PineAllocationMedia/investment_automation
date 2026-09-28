"""Pure assembly of per-output analytical dependency availability.

The assembler matches one reviewed dependency declaration to explicit subject
bindings and existing capability assessments.  It never calculates an economic
output and grants no admission, recommendation, allocation, execution, or
production authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
import json
import re

from .contracts import CapabilityAssessment, CapabilityScope, CapabilityState
from .dependencies import CapabilityDependency, OutputDependencyContract


ASSEMBLER_CONTRACT_VERSION = "2026-09-28-partial-analysis-assembler-v1"

__all__ = (
    "ASSEMBLER_CONTRACT_VERSION",
    "AssemblyContractError",
    "OutputAvailabilityStatus",
    "DependencyBinding",
    "DependencyResolutionStatus",
    "DependencyResolution",
    "OutputAvailability",
    "assemble_output_availability",
)

_CODE = re.compile(r"[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*", re.ASCII)
_IDENTITY = re.compile(r"[0-9a-f]{64}", re.ASCII)
_SEMANTIC_DOMAIN = b"pam:partial-analysis-output-availability:semantic:v1\0"
_EVIDENCE_DOMAIN = b"pam:partial-analysis-output-availability:evidence:v1\0"


class AssemblyContractError(ValueError):
    """Malformed or structurally unsupported assembly request."""


class OutputAvailabilityStatus(StrEnum):
    """Closed output-level dependency-availability states."""

    AVAILABLE = "AVAILABLE"
    AVAILABLE_WITH_LIMITATIONS = "AVAILABLE_WITH_LIMITATIONS"
    UNAVAILABLE = "UNAVAILABLE"


class DependencyResolutionStatus(StrEnum):
    """Closed result vocabulary for one declared dependency role."""

    SATISFIED_SUPPORTED = "SATISFIED_SUPPORTED"
    SATISFIED_PARTIAL = "SATISFIED_PARTIAL"
    UNSATISFIED_MISSING_BINDING = "UNSATISFIED_MISSING_BINDING"
    UNSATISFIED_SUBJECT_KIND = "UNSATISFIED_SUBJECT_KIND"
    UNSATISFIED_BOUNDARY = "UNSATISFIED_BOUNDARY"
    UNSATISFIED_RELATIONSHIP = "UNSATISFIED_RELATIONSHIP"
    UNSATISFIED_MISSING_ASSESSMENT = "UNSATISFIED_MISSING_ASSESSMENT"
    UNSATISFIED_AMBIGUOUS_ASSESSMENT = "UNSATISFIED_AMBIGUOUS_ASSESSMENT"
    UNSATISFIED_STATE = "UNSATISFIED_STATE"


_SATISFIED_STATUSES = frozenset(
    (
        DependencyResolutionStatus.SATISFIED_SUPPORTED,
        DependencyResolutionStatus.SATISFIED_PARTIAL,
    )
)
_STATE_ORDER = {state: index for index, state in enumerate(CapabilityState)}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AssemblyContractError(message)


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
        f"{label}: lowercase SHA-256 semantic/evidence identity required",
    )
    return value


def _canonical_codes(values: object, label: str) -> tuple[str, ...]:
    _require(type(values) is tuple, f"{label}: tuple required")
    return tuple(sorted({_code(value, label) for value in values}))


def _canonical_identities(values: object, label: str) -> tuple[str, ...]:
    _require(type(values) is tuple, f"{label}: tuple required")
    return tuple(sorted({_identity(value, label) for value in values}))


def _canonical_states(values: object, label: str) -> tuple[CapabilityState, ...]:
    _require(type(values) is tuple, f"{label}: tuple required")
    _require(
        all(type(value) is CapabilityState for value in values),
        f"{label}: exact CapabilityState values required",
    )
    return tuple(sorted(set(values), key=_STATE_ORDER.__getitem__))


def _scope_payload(scope: CapabilityScope | None) -> object:
    if scope is None:
        return None
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
class DependencyBinding:
    """Explicit binding from one dependency role to one exact capability scope.

    Relationship identities are retained assertions from a separately reviewed
    upstream resolver.  This record does not interpret or authenticate them.
    """

    dependency_id: str
    scope: CapabilityScope
    relationship_semantic_ids: tuple[str, ...] = ()
    relationship_evidence_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "dependency_id", _code(self.dependency_id, "dependency_id")
        )
        _require(type(self.scope) is CapabilityScope, "Exact CapabilityScope required")
        object.__setattr__(
            self,
            "relationship_semantic_ids",
            _canonical_identities(
                self.relationship_semantic_ids, "relationship_semantic_ids"
            ),
        )
        object.__setattr__(
            self,
            "relationship_evidence_ids",
            _canonical_identities(
                self.relationship_evidence_ids, "relationship_evidence_ids"
            ),
        )


@dataclass(frozen=True, slots=True)
class DependencyResolution:
    """Immutable, provenance-preserving resolution of one dependency role."""

    dependency_id: str
    required_capability_id: str
    expected_subject_kind: str
    accepted_states: tuple[CapabilityState, ...]
    bound_scope: CapabilityScope | None
    status: DependencyResolutionStatus
    assessment_semantic_ids: tuple[str, ...] = ()
    assessment_evidence_ids: tuple[str, ...] = ()
    relationship_semantic_ids: tuple[str, ...] = ()
    relationship_evidence_ids: tuple[str, ...] = ()
    upstream_states: tuple[CapabilityState, ...] = ()
    upstream_reason_codes: tuple[str, ...] = ()
    upstream_limitation_codes: tuple[str, ...] = ()
    assembler_reason_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "dependency_id", _code(self.dependency_id, "dependency_id")
        )
        object.__setattr__(
            self,
            "required_capability_id",
            _code(self.required_capability_id, "required_capability_id"),
        )
        object.__setattr__(
            self,
            "expected_subject_kind",
            _code(self.expected_subject_kind, "expected_subject_kind"),
        )
        object.__setattr__(
            self,
            "accepted_states",
            _canonical_states(self.accepted_states, "accepted_states"),
        )
        _require(
            self.accepted_states
            in (
                (CapabilityState.SUPPORTED,),
                (CapabilityState.SUPPORTED, CapabilityState.PARTIAL),
            ),
            "accepted_states: only SUPPORTED or SUPPORTED plus PARTIAL permitted",
        )
        _require(
            self.bound_scope is None or type(self.bound_scope) is CapabilityScope,
            "bound_scope: exact CapabilityScope or None required",
        )
        _require(
            type(self.status) is DependencyResolutionStatus,
            "Exact DependencyResolutionStatus required",
        )
        for field_name in (
            "assessment_semantic_ids",
            "assessment_evidence_ids",
            "relationship_semantic_ids",
            "relationship_evidence_ids",
        ):
            object.__setattr__(
                self,
                field_name,
                _canonical_identities(getattr(self, field_name), field_name),
            )
        object.__setattr__(
            self,
            "upstream_states",
            _canonical_states(self.upstream_states, "upstream_states"),
        )
        for field_name in (
            "upstream_reason_codes",
            "upstream_limitation_codes",
            "assembler_reason_codes",
        ):
            object.__setattr__(
                self,
                field_name,
                _canonical_codes(getattr(self, field_name), field_name),
            )
        self._validate_status()

    def _validate_status(self) -> None:
        if self.status is DependencyResolutionStatus.SATISFIED_SUPPORTED:
            _require(
                self.bound_scope is not None,
                "SATISFIED_SUPPORTED requires a bound scope",
            )
            _require(
                self.upstream_states == (CapabilityState.SUPPORTED,),
                "SATISFIED_SUPPORTED requires exactly one SUPPORTED upstream state",
            )
            _require(
                bool(self.assessment_semantic_ids and self.assessment_evidence_ids),
                "SATISFIED_SUPPORTED requires retained assessment identities",
            )
            _require(
                not self.assembler_reason_codes,
                "SATISFIED_SUPPORTED cannot contain assembler failure reasons",
            )
            return
        if self.status is DependencyResolutionStatus.SATISFIED_PARTIAL:
            _require(
                CapabilityState.PARTIAL in self.accepted_states,
                "SATISFIED_PARTIAL requires PARTIAL to be explicitly accepted",
            )
            _require(
                self.bound_scope is not None,
                "SATISFIED_PARTIAL requires a bound scope",
            )
            _require(
                self.upstream_states == (CapabilityState.PARTIAL,),
                "SATISFIED_PARTIAL requires exactly one PARTIAL upstream state",
            )
            _require(
                bool(self.assessment_semantic_ids and self.assessment_evidence_ids),
                "SATISFIED_PARTIAL requires retained assessment identities",
            )
            _require(
                bool(self.upstream_reason_codes),
                "SATISFIED_PARTIAL requires upstream reasons",
            )
            _require(
                bool(self.upstream_limitation_codes),
                "SATISFIED_PARTIAL requires upstream limitations",
            )
            _require(
                not self.assembler_reason_codes,
                "SATISFIED_PARTIAL cannot contain assembler failure reasons",
            )
            return

        _require(
            bool(self.assembler_reason_codes),
            "Unsatisfied dependency resolution requires an assembler reason",
        )
        if self.status is DependencyResolutionStatus.UNSATISFIED_MISSING_BINDING:
            _require(
                self.bound_scope is None,
                "UNSATISFIED_MISSING_BINDING cannot contain a bound scope",
            )
            _require(
                not self.assessment_semantic_ids
                and not self.assessment_evidence_ids
                and not self.relationship_semantic_ids
                and not self.relationship_evidence_ids
                and not self.upstream_states,
                "UNSATISFIED_MISSING_BINDING cannot retain binding or assessment identities",
            )

    @property
    def upstream_state(self) -> CapabilityState | None:
        """Return the unique upstream state, or ``None`` for none/ambiguity."""
        if len(self.upstream_states) == 1:
            return self.upstream_states[0]
        return None


def _derive_output_status(
    resolutions: tuple[DependencyResolution, ...],
) -> OutputAvailabilityStatus:
    if any(item.status not in _SATISFIED_STATUSES for item in resolutions):
        return OutputAvailabilityStatus.UNAVAILABLE
    if any(
        item.status is DependencyResolutionStatus.SATISFIED_PARTIAL
        for item in resolutions
    ):
        return OutputAvailabilityStatus.AVAILABLE_WITH_LIMITATIONS
    return OutputAvailabilityStatus.AVAILABLE


@dataclass(frozen=True, slots=True)
class OutputAvailability:
    """Deterministic dependency availability for one future analytical output."""

    assembler_contract_version: str
    dependency_contract_semantic_id: str
    output_id: str
    output_scope: CapabilityScope
    status: OutputAvailabilityStatus
    dependency_resolutions: tuple[DependencyResolution, ...]
    reason_codes: tuple[str, ...] = ()
    limitation_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require(
            type(self.assembler_contract_version) is str
            and self.assembler_contract_version == ASSEMBLER_CONTRACT_VERSION,
            "Unsupported assembler contract version",
        )
        object.__setattr__(
            self,
            "dependency_contract_semantic_id",
            _identity(
                self.dependency_contract_semantic_id,
                "dependency_contract_semantic_id",
            ),
        )
        object.__setattr__(self, "output_id", _code(self.output_id, "output_id"))
        _require(
            type(self.output_scope) is CapabilityScope,
            "Exact output CapabilityScope required",
        )
        _require(
            type(self.status) is OutputAvailabilityStatus,
            "Exact OutputAvailabilityStatus required",
        )
        _require(
            type(self.dependency_resolutions) is tuple,
            "dependency_resolutions: tuple required",
        )
        _require(
            bool(self.dependency_resolutions)
            and all(
                type(item) is DependencyResolution
                for item in self.dependency_resolutions
            ),
            "dependency_resolutions: nonempty exact DependencyResolution tuple required",
        )
        dependency_ids = tuple(
            item.dependency_id for item in self.dependency_resolutions
        )
        _require(
            len(dependency_ids) == len(set(dependency_ids)),
            "dependency_resolutions: dependency_id values must be unique",
        )
        object.__setattr__(
            self,
            "dependency_resolutions",
            tuple(
                sorted(
                    self.dependency_resolutions,
                    key=lambda item: item.dependency_id,
                )
            ),
        )
        object.__setattr__(
            self, "reason_codes", _canonical_codes(self.reason_codes, "reason_codes")
        )
        object.__setattr__(
            self,
            "limitation_codes",
            _canonical_codes(self.limitation_codes, "limitation_codes"),
        )
        derived_status = _derive_output_status(self.dependency_resolutions)
        _require(
            self.status is derived_status,
            "Output availability status contradicts dependency resolutions",
        )
        if self.status is OutputAvailabilityStatus.AVAILABLE:
            _require(
                not self.reason_codes and not self.limitation_codes,
                "AVAILABLE cannot contain output-level reasons or limitations",
            )
        elif self.status is OutputAvailabilityStatus.AVAILABLE_WITH_LIMITATIONS:
            _require(
                bool(self.reason_codes),
                "AVAILABLE_WITH_LIMITATIONS requires output-level reasons",
            )
            _require(
                bool(self.limitation_codes),
                "AVAILABLE_WITH_LIMITATIONS requires output-level limitations",
            )
        else:
            _require(
                bool(self.reason_codes),
                "UNAVAILABLE requires output-level reasons",
            )

    def _resolution_payload(self, *, include_evidence: bool) -> list[dict[str, object]]:
        payload = []
        for resolution in self.dependency_resolutions:
            item: dict[str, object] = {
                "dependency_id": resolution.dependency_id,
                "required_capability_id": resolution.required_capability_id,
                "expected_subject_kind": resolution.expected_subject_kind,
                "accepted_states": tuple(
                    state.value for state in resolution.accepted_states
                ),
                "bound_scope": _scope_payload(resolution.bound_scope),
                "status": resolution.status.value,
                "assessment_semantic_ids": resolution.assessment_semantic_ids,
                "relationship_semantic_ids": resolution.relationship_semantic_ids,
                "upstream_states": tuple(
                    state.value for state in resolution.upstream_states
                ),
                "upstream_reason_codes": resolution.upstream_reason_codes,
                "upstream_limitation_codes": resolution.upstream_limitation_codes,
                "assembler_reason_codes": resolution.assembler_reason_codes,
            }
            if include_evidence:
                item["assessment_evidence_ids"] = resolution.assessment_evidence_ids
                item["relationship_evidence_ids"] = (
                    resolution.relationship_evidence_ids
                )
            payload.append(item)
        return payload

    @property
    def semantic_id(self) -> str:
        """Identity of availability meaning, excluding exact recapture IDs."""
        return _digest(
            _SEMANTIC_DOMAIN,
            {
                "assembler_contract_version": self.assembler_contract_version,
                "dependency_contract_semantic_id": (
                    self.dependency_contract_semantic_id
                ),
                "output_id": self.output_id,
                "output_scope": _scope_payload(self.output_scope),
                "status": self.status.value,
                "dependency_resolutions": self._resolution_payload(
                    include_evidence=False
                ),
                "reason_codes": self.reason_codes,
                "limitation_codes": self.limitation_codes,
            },
        )

    @property
    def evidence_id(self) -> str:
        """Identity additionally binding every retained exact evidence ID."""
        return _digest(
            _EVIDENCE_DOMAIN,
            {
                "semantic_id": self.semantic_id,
                "dependency_resolutions": self._resolution_payload(
                    include_evidence=True
                ),
            },
        )


def _resolution(
    requirement: CapabilityDependency,
    binding: DependencyBinding | None,
    status: DependencyResolutionStatus,
    *,
    assessments: tuple[CapabilityAssessment, ...] = (),
    assembler_reason: str | None = None,
) -> DependencyResolution:
    assessment_semantic_ids = tuple(item.semantic_id for item in assessments)
    assessment_evidence_ids = tuple(item.evidence_id for item in assessments)
    upstream_states = tuple(item.state for item in assessments)
    upstream_reason_codes = tuple(
        reason for item in assessments for reason in item.reason_codes
    )
    upstream_limitation_codes = tuple(
        limitation for item in assessments for limitation in item.limitation_codes
    )
    return DependencyResolution(
        dependency_id=requirement.dependency_id,
        required_capability_id=requirement.capability_id,
        expected_subject_kind=requirement.subject_kind,
        accepted_states=requirement.accepted_states,
        bound_scope=None if binding is None else binding.scope,
        status=status,
        assessment_semantic_ids=assessment_semantic_ids,
        assessment_evidence_ids=assessment_evidence_ids,
        relationship_semantic_ids=(
            () if binding is None else binding.relationship_semantic_ids
        ),
        relationship_evidence_ids=(
            () if binding is None else binding.relationship_evidence_ids
        ),
        upstream_states=upstream_states,
        upstream_reason_codes=upstream_reason_codes,
        upstream_limitation_codes=upstream_limitation_codes,
        assembler_reason_codes=(() if assembler_reason is None else (assembler_reason,)),
    )


def assemble_output_availability(
    dependency_contract: OutputDependencyContract,
    output_scope: CapabilityScope,
    bindings: tuple[DependencyBinding, ...],
    assessments: tuple[CapabilityAssessment, ...],
) -> OutputAvailability:
    """Resolve one output's dependencies without executing the output itself.

    The caller must supply repository-reviewed objects and relationship evidence
    through separately reviewed paths.  Structurally valid caller-created objects
    and SHA-256-looking strings are not self-authenticating production authority.
    """
    _require(
        type(dependency_contract) is OutputDependencyContract,
        "Exact OutputDependencyContract required",
    )
    _require(
        type(output_scope) is CapabilityScope,
        "Exact output CapabilityScope required",
    )
    _require(type(bindings) is tuple, "bindings: tuple required")
    _require(
        all(type(item) is DependencyBinding for item in bindings),
        "bindings: exact DependencyBinding instances required",
    )
    _require(type(assessments) is tuple, "assessments: tuple required")
    _require(
        all(type(item) is CapabilityAssessment for item in assessments),
        "assessments: exact CapabilityAssessment instances required",
    )
    _require(
        output_scope.subject_kind == dependency_contract.output_subject_kind,
        "output_scope subject_kind must equal dependency contract output_subject_kind",
    )

    requirement_ids = {
        requirement.dependency_id for requirement in dependency_contract.requirements
    }
    binding_ids = tuple(binding.dependency_id for binding in bindings)
    _require(
        len(binding_ids) == len(set(binding_ids)),
        "bindings: dependency_id values must be unique",
    )
    unknown_ids = sorted(set(binding_ids) - requirement_ids)
    _require(
        not unknown_ids,
        "bindings: dependency_id not declared by dependency contract",
    )
    bindings_by_id = {binding.dependency_id: binding for binding in bindings}

    resolutions = []
    for requirement in dependency_contract.requirements:
        binding = bindings_by_id.get(requirement.dependency_id)
        if binding is None:
            resolutions.append(
                _resolution(
                    requirement,
                    None,
                    DependencyResolutionStatus.UNSATISFIED_MISSING_BINDING,
                    assembler_reason="MISSING_DEPENDENCY_BINDING",
                )
            )
            continue
        if binding.scope.subject_kind != requirement.subject_kind:
            resolutions.append(
                _resolution(
                    requirement,
                    binding,
                    DependencyResolutionStatus.UNSATISFIED_SUBJECT_KIND,
                    assembler_reason="SUBJECT_KIND_MISMATCH",
                )
            )
            continue
        if binding.scope.authority_boundary != output_scope.authority_boundary:
            resolutions.append(
                _resolution(
                    requirement,
                    binding,
                    DependencyResolutionStatus.UNSATISFIED_BOUNDARY,
                    assembler_reason="AUTHORITY_BOUNDARY_MISMATCH",
                )
            )
            continue
        if binding.scope != output_scope and not (
            binding.relationship_semantic_ids
            and binding.relationship_evidence_ids
        ):
            resolutions.append(
                _resolution(
                    requirement,
                    binding,
                    DependencyResolutionStatus.UNSATISFIED_RELATIONSHIP,
                    assembler_reason="CROSS_SCOPE_RELATIONSHIP_NOT_ESTABLISHED",
                )
            )
            continue

        matches = tuple(
            assessment
            for assessment in assessments
            if assessment.capability_id == requirement.capability_id
            and assessment.scope == binding.scope
        )
        if not matches:
            resolutions.append(
                _resolution(
                    requirement,
                    binding,
                    DependencyResolutionStatus.UNSATISFIED_MISSING_ASSESSMENT,
                    assembler_reason="CAPABILITY_ASSESSMENT_MISSING",
                )
            )
            continue
        semantic_ids = {assessment.semantic_id for assessment in matches}
        if len(semantic_ids) != 1:
            resolutions.append(
                _resolution(
                    requirement,
                    binding,
                    DependencyResolutionStatus.UNSATISFIED_AMBIGUOUS_ASSESSMENT,
                    assessments=matches,
                    assembler_reason="AMBIGUOUS_CAPABILITY_ASSESSMENT",
                )
            )
            continue

        representative = matches[0]
        if representative.state not in requirement.accepted_states:
            resolutions.append(
                _resolution(
                    requirement,
                    binding,
                    DependencyResolutionStatus.UNSATISFIED_STATE,
                    assessments=matches,
                    assembler_reason="CAPABILITY_STATE_NOT_ACCEPTED",
                )
            )
            continue
        satisfied_status = (
            DependencyResolutionStatus.SATISFIED_PARTIAL
            if representative.state is CapabilityState.PARTIAL
            else DependencyResolutionStatus.SATISFIED_SUPPORTED
        )
        resolutions.append(
            _resolution(
                requirement,
                binding,
                satisfied_status,
                assessments=matches,
            )
        )

    resolution_tuple = tuple(resolutions)
    output_status = _derive_output_status(resolution_tuple)
    if output_status is OutputAvailabilityStatus.UNAVAILABLE:
        relevant = resolution_tuple
    elif output_status is OutputAvailabilityStatus.AVAILABLE_WITH_LIMITATIONS:
        relevant = tuple(
            item
            for item in resolution_tuple
            if item.status is DependencyResolutionStatus.SATISFIED_PARTIAL
        )
    else:
        relevant = ()

    reason_codes = tuple(
        code
        for item in relevant
        for code in item.assembler_reason_codes + item.upstream_reason_codes
    )
    limitation_codes = tuple(
        code for item in relevant for code in item.upstream_limitation_codes
    )
    return OutputAvailability(
        assembler_contract_version=ASSEMBLER_CONTRACT_VERSION,
        dependency_contract_semantic_id=dependency_contract.semantic_id,
        output_id=dependency_contract.output_id,
        output_scope=output_scope,
        status=output_status,
        dependency_resolutions=resolution_tuple,
        reason_codes=reason_codes,
        limitation_codes=limitation_codes,
    )
