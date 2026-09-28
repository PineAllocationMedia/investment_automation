"""Pure contracts for dimensional V2 analytical capability coverage.

These records describe only whether one exact analytical capability is supported
within one exact scope.  They do not resolve economic evidence and grant no
analytical, admission, recommendation, allocation, execution, or production
authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
import json
import re


CAPABILITY_CONTRACT_VERSION = "2026-09-28-capability-assessment-foundation-v1"

__all__ = (
    "CAPABILITY_CONTRACT_VERSION",
    "CapabilityAssessment",
    "CapabilityContractError",
    "CapabilityScope",
    "CapabilityState",
)

_CODE = re.compile(r"[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*", re.ASCII)
_IDENTITY = re.compile(r"[0-9a-f]{64}", re.ASCII)
_BOUNDARY = re.compile(r"[A-Za-z0-9][A-Za-z0-9:._+/-]{0,255}", re.ASCII)
_SEMANTIC_DOMAIN = b"pam:analysis-capability-assessment:semantic:v1\0"
_EVIDENCE_DOMAIN = b"pam:analysis-capability-assessment:evidence:v1\0"


class CapabilityContractError(ValueError):
    """Malformed or structurally unsupported capability contract."""


class CapabilityState(StrEnum):
    """Closed dimensional states with no ranking or economic ordering."""

    SUPPORTED = "SUPPORTED"
    PARTIAL = "PARTIAL"
    UNSUPPORTED = "UNSUPPORTED"
    UNAVAILABLE = "UNAVAILABLE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    CONFLICTED = "CONFLICTED"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise CapabilityContractError(message)


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
class CapabilityScope:
    """Exact upstream-reviewed subject and optional explicit authority boundary.

    ``subject_identity`` is an upstream semantic identity, never a ticker,
    display name, CIK, or identity inferred by this contract.
    """

    subject_kind: str
    subject_identity: str
    authority_boundary: str | None = None
    supporting_semantic_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "subject_kind", _code(self.subject_kind, "subject_kind"))
        object.__setattr__(
            self,
            "subject_identity",
            _identity(self.subject_identity, "subject_identity"),
        )
        if self.authority_boundary is not None:
            _require(
                type(self.authority_boundary) is str
                and _BOUNDARY.fullmatch(self.authority_boundary) is not None,
                "authority_boundary: explicit canonical boundary required",
            )
        object.__setattr__(
            self,
            "supporting_semantic_ids",
            _canonical_identities(
                self.supporting_semantic_ids, "scope supporting_semantic_ids"
            ),
        )


@dataclass(frozen=True, slots=True)
class CapabilityAssessment:
    """Immutable representation of one dimensional capability assessment."""

    contract_version: str
    capability_id: str
    scope: CapabilityScope
    state: CapabilityState
    supporting_semantic_ids: tuple[str, ...] = ()
    supporting_evidence_ids: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()
    limitation_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require(
            self.contract_version == CAPABILITY_CONTRACT_VERSION,
            "Unsupported capability contract version",
        )
        object.__setattr__(
            self, "capability_id", _code(self.capability_id, "capability_id")
        )
        _require(type(self.scope) is CapabilityScope, "Exact CapabilityScope required")
        _require(type(self.state) is CapabilityState, "Exact CapabilityState required")
        object.__setattr__(
            self,
            "supporting_semantic_ids",
            _canonical_identities(
                self.supporting_semantic_ids, "supporting_semantic_ids"
            ),
        )
        object.__setattr__(
            self,
            "supporting_evidence_ids",
            _canonical_identities(
                self.supporting_evidence_ids, "supporting_evidence_ids"
            ),
        )
        object.__setattr__(
            self,
            "reason_codes",
            _canonical_codes(self.reason_codes, "reason_codes"),
        )
        object.__setattr__(
            self,
            "limitation_codes",
            _canonical_codes(self.limitation_codes, "limitation_codes"),
        )
        self._validate_state()

    def _validate_state(self) -> None:
        has_support = bool(
            self.supporting_semantic_ids and self.supporting_evidence_ids
        )
        if self.state is CapabilityState.SUPPORTED:
            _require(has_support, "SUPPORTED requires retained semantic and evidence support")
        elif self.state is CapabilityState.PARTIAL:
            _require(has_support, "PARTIAL requires retained semantic and evidence support")
            _require(bool(self.reason_codes), "PARTIAL requires explicit reason_codes")
            _require(
                bool(self.limitation_codes),
                "PARTIAL requires explicit limitation_codes",
            )
        elif self.state in (CapabilityState.UNSUPPORTED, CapabilityState.UNAVAILABLE):
            _require(bool(self.reason_codes), f"{self.state.value} requires reason_codes")
        elif self.state in (
            CapabilityState.REVIEW_REQUIRED,
            CapabilityState.CONFLICTED,
        ):
            _require(has_support, f"{self.state.value} requires retained evidence")
            _require(bool(self.reason_codes), f"{self.state.value} requires reason_codes")

    @property
    def semantic_id(self) -> str:
        """Identity of meaning, excluding exact evidence recapture identities."""
        return _digest(
            _SEMANTIC_DOMAIN,
            {
                "contract_version": self.contract_version,
                "capability_id": self.capability_id,
                "scope": {
                    "subject_kind": self.scope.subject_kind,
                    "subject_identity": self.scope.subject_identity,
                    "authority_boundary": self.scope.authority_boundary,
                    "supporting_semantic_ids": self.scope.supporting_semantic_ids,
                },
                "state": self.state.value,
                "supporting_semantic_ids": self.supporting_semantic_ids,
                "reason_codes": self.reason_codes,
                "limitation_codes": self.limitation_codes,
            },
        )

    @property
    def evidence_id(self) -> str:
        """Identity of the semantics plus the exact retained evidence capture."""
        return _digest(
            _EVIDENCE_DOMAIN,
            {
                "semantic_id": self.semantic_id,
                "supporting_evidence_ids": self.supporting_evidence_ids,
            },
        )
