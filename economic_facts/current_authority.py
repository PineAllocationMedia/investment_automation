"""Source-neutral CURRENT authority reports, never economic admission tokens.

Records and hashes are inspectable outputs, not unforgeable capabilities. No
public verifier accepts them as evidence. Route adapters must reconstruct claims
from controlled captures. A future gate must verify original evidence again.
"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import re

from .source_authority import (AuthorityProperty, ClaimGrant, PublicationSemantics,
                               get_source_route, permitted_claim, _hash)

CURRENT_AUTHORITY_VERSION = "2026-09-19-current-authority-assessment-v1"


class AssessmentStatus(Enum):
    EVIDENCE_ESTABLISHED = "EVIDENCE_ESTABLISHED"
    UNAVAILABLE = "UNAVAILABLE"


class AuthorityReason(Enum):
    UNSUPPORTED_ACQUISITION_AUTHORITY = "UNSUPPORTED_ACQUISITION_AUTHORITY"
    RESOLUTION_UNAVAILABLE = "RESOLUTION_UNAVAILABLE"
    HISTORICAL_MODE_UNSUPPORTED = "HISTORICAL_MODE_UNSUPPORTED"


class AuthorityLimitation(Enum):
    EXACT_PUBLICATION_UNKNOWN = "EXACT_PUBLICATION_UNKNOWN"
    NO_HISTORICAL_AS_OF_AUTHORITY = "NO_HISTORICAL_AS_OF_AUTHORITY"
    NO_ECONOMIC_ADMISSION = "NO_ECONOMIC_ADMISSION"
    CONTROLLED_LOCAL_TRUST_ONLY = "CONTROLLED_LOCAL_TRUST_ONLY"
    NO_FRESHNESS_BEYOND_CAPTURE = "NO_FRESHNESS_BEYOND_CAPTURE"


class AuthorityErrorReason(Enum):
    INVALID_CONTRACT = "INVALID_CONTRACT"
    ARCHIVE_INTEGRITY_FAILURE = "ARCHIVE_INTEGRITY_FAILURE"
    SOURCE_STRUCTURE_FAILURE = "SOURCE_STRUCTURE_FAILURE"
    ROUTE_CONTRACT_MISMATCH = "ROUTE_CONTRACT_MISMATCH"
    AUTHORITY_BOUNDARY_MISMATCH = "AUTHORITY_BOUNDARY_MISMATCH"


class CurrentAuthorityError(ValueError):
    def __init__(self, reason):
        self.reason = reason
        super().__init__(reason.value)


@dataclass(frozen=True, slots=True)
class EstablishedClaim:
    grant: ClaimGrant
    source_hashes: tuple[str, ...]
    evidence_hash: str


@dataclass(frozen=True, slots=True)
class CurrentAuthorityAssessment:
    contract_version: str
    route_id: str
    route_profile_version: str
    route_profile_hash: str
    status: AssessmentStatus
    reasons: tuple[AuthorityReason, ...]
    current_authority_boundary: str | None
    observed_available_by: str | None
    publication: PublicationSemantics
    established_claims: tuple[EstablishedClaim, ...]
    satisfied_obligations: tuple[AuthorityProperty, ...]
    unresolved_obligations: tuple[AuthorityProperty, ...]
    limitations: tuple[AuthorityLimitation, ...]
    upstream_blockers: tuple[str, ...]
    source_hashes: tuple[str, ...]
    upstream_semantic_hash: str | None
    upstream_evidence_hash: str | None
    semantic_hash: str
    evidence_hash: str


def _require(condition, reason=AuthorityErrorReason.INVALID_CONTRACT):
    if not condition:
        raise CurrentAuthorityError(reason)


def _digest(value):
    _require(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None)


def _time(value):
    _require(type(value) is str and re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{6})?Z", value) is not None)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise CurrentAuthorityError(AuthorityErrorReason.INVALID_CONTRACT) from None
    _require(parsed.isoformat().replace("+00:00", "Z") == value)
    return parsed


def _build_assessment(*, route_id, boundary, reasons, verified_properties, upstream_blockers, source_hashes,
                      upstream_semantic_hash, upstream_evidence_hash, verified_evidence_hash):
    """Private report assembly AFTER route verification; never an evidence API.

    Future contributing captures must be <= boundary AND establish coverage
    through it. Computation time cannot advance it or create historical knowledge.
    """
    profile = get_source_route(route_id)
    _require(type(reasons) is tuple and all(type(r) is AuthorityReason for r in reasons))
    reasons = tuple(sorted(set(reasons), key=lambda r: r.value))
    _require(type(verified_properties) is tuple
             and all(type(p) is AuthorityProperty for p in verified_properties))
    _require(AuthorityProperty.FINAL_ECONOMIC_ADMISSION not in verified_properties)
    _require(type(upstream_blockers) is tuple and all(type(b) is str and b and b == b.strip()
                                                    for b in upstream_blockers))
    _require(type(source_hashes) is tuple)
    for value in source_hashes:
        _digest(value)
    source_hashes = tuple(sorted(set(source_hashes)))
    _digest(verified_evidence_hash)
    for value in (upstream_semantic_hash, upstream_evidence_hash):
        if value is not None:
            _digest(value)
    if not reasons:
        _time(boundary)
        _require(bool(verified_properties) and bool(source_hashes) and upstream_semantic_hash is not None
                 and upstream_evidence_hash is not None)
    else:
        _require(boundary is None, AuthorityErrorReason.AUTHORITY_BOUNDARY_MISMATCH)
        _require(not verified_properties)
    satisfied = tuple(sorted(set(verified_properties), key=lambda p: p.value))
    # The route can never qualify the remaining four economic obligations.
    unresolved = tuple(sorted(set(AuthorityProperty) - set(satisfied), key=lambda p: p.value))
    claims = tuple(EstablishedClaim(permitted_claim(route_id, p), source_hashes,
                                    verified_evidence_hash) for p in satisfied)
    limitations = tuple(sorted(AuthorityLimitation, key=lambda p: p.value))
    status = AssessmentStatus.UNAVAILABLE if reasons else AssessmentStatus.EVIDENCE_ESTABLISHED
    semantic = (CURRENT_AUTHORITY_VERSION, profile.factual_hash, status, reasons, boundary,
                PublicationSemantics.UNKNOWN, satisfied, unresolved, limitations,
                tuple(sorted(set(upstream_blockers))), upstream_semantic_hash)
    semantic_hash = _hash("current-authority-semantics", semantic)
    evidence_hash = _hash("current-authority-evidence", (CURRENT_AUTHORITY_VERSION,
        semantic_hash, profile.profile_hash, claims, source_hashes, upstream_blockers,
        upstream_evidence_hash, verified_evidence_hash))
    return CurrentAuthorityAssessment(CURRENT_AUTHORITY_VERSION, profile.route_id,
        profile.profile_version, profile.profile_hash, status, reasons, boundary, boundary,
        PublicationSemantics.UNKNOWN, claims, satisfied, unresolved, limitations,
        upstream_blockers, source_hashes, upstream_semantic_hash, upstream_evidence_hash,
        semantic_hash, evidence_hash)
