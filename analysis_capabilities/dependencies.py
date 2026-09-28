"""Pure declarations of analytical-output capability dependencies.

These records describe what one future analytical output requires.  They do not
match capability assessments, bind subjects, execute outputs, or grant analytical,
admission, recommendation, allocation, execution, or production authority.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re

from .contracts import CapabilityState


DEPENDENCY_CONTRACT_VERSION = "2026-09-28-output-dependency-contract-v1"

__all__ = (
    "DEPENDENCY_CONTRACT_VERSION",
    "CapabilityDependency",
    "DependencyContractError",
    "OutputDependencyContract",
)

_CODE = re.compile(r"[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*", re.ASCII)
_SEMANTIC_DOMAIN = b"pam:analysis-capability-output-dependency-contract:semantic:v1\0"


class DependencyContractError(ValueError):
    """Malformed or structurally unsupported output dependency contract."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise DependencyContractError(message)


def _code(value: object, label: str) -> str:
    _require(
        type(value) is str
        and len(value) <= 128
        and _CODE.fullmatch(value) is not None,
        f"{label}: canonical uppercase ASCII identifier required",
    )
    return value


def _canonical_accepted_states(values: object) -> tuple[CapabilityState, ...]:
    _require(type(values) is tuple, "accepted_states: tuple required")
    _require(bool(values), "accepted_states: nonempty tuple required")
    _require(
        all(type(value) is CapabilityState for value in values),
        "accepted_states: exact CapabilityState values required",
    )
    states = frozenset(values)
    _require(
        states in (
            frozenset((CapabilityState.SUPPORTED,)),
            frozenset((CapabilityState.SUPPORTED, CapabilityState.PARTIAL)),
        ),
        "accepted_states: only SUPPORTED or SUPPORTED plus PARTIAL permitted",
    )
    if CapabilityState.PARTIAL in states:
        return (CapabilityState.SUPPORTED, CapabilityState.PARTIAL)
    return (CapabilityState.SUPPORTED,)


def _digest(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(_SEMANTIC_DOMAIN + payload).hexdigest()


@dataclass(frozen=True, slots=True)
class CapabilityDependency:
    """One named dependency role within an analytical output contract."""

    dependency_id: str
    capability_id: str
    subject_kind: str
    accepted_states: tuple[CapabilityState, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "dependency_id", _code(self.dependency_id, "dependency_id")
        )
        object.__setattr__(
            self, "capability_id", _code(self.capability_id, "capability_id")
        )
        object.__setattr__(
            self, "subject_kind", _code(self.subject_kind, "subject_kind")
        )
        object.__setattr__(
            self,
            "accepted_states",
            _canonical_accepted_states(self.accepted_states),
        )


@dataclass(frozen=True, slots=True)
class OutputDependencyContract:
    """Versioned, conjunctive dependency declaration for one output.

    Construction does not make a contract authoritative.  Future consumers must
    rely only on separately reviewed and pinned contract identities or
    repository-owned declarations, never arbitrary caller-created instances.
    """

    contract_version: str
    output_id: str
    output_subject_kind: str
    requirements: tuple[CapabilityDependency, ...]

    def __post_init__(self) -> None:
        _require(
            type(self.contract_version) is str
            and self.contract_version == DEPENDENCY_CONTRACT_VERSION,
            "Unsupported dependency contract version",
        )
        object.__setattr__(self, "output_id", _code(self.output_id, "output_id"))
        object.__setattr__(
            self,
            "output_subject_kind",
            _code(self.output_subject_kind, "output_subject_kind"),
        )
        _require(type(self.requirements) is tuple, "requirements: tuple required")
        _require(bool(self.requirements), "requirements: nonempty tuple required")
        _require(
            all(type(item) is CapabilityDependency for item in self.requirements),
            "requirements: exact CapabilityDependency instances required",
        )
        dependency_ids = tuple(item.dependency_id for item in self.requirements)
        _require(
            len(dependency_ids) == len(set(dependency_ids)),
            "requirements: dependency_id values must be unique",
        )
        object.__setattr__(
            self,
            "requirements",
            tuple(sorted(self.requirements, key=lambda item: item.dependency_id)),
        )

    @property
    def semantic_id(self) -> str:
        """Deterministic identity of the complete canonical declaration."""
        return _digest(
            {
                "contract_version": self.contract_version,
                "output_id": self.output_id,
                "output_subject_kind": self.output_subject_kind,
                "requirements": [
                    {
                        "dependency_id": item.dependency_id,
                        "capability_id": item.capability_id,
                        "subject_kind": item.subject_kind,
                        "accepted_states": tuple(
                            state.value for state in item.accepted_states
                        ),
                    }
                    for item in self.requirements
                ],
            }
        )
