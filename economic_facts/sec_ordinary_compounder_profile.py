"""SEC-backed qualification for PR4B1's ordinary-company methodology profile."""
from dataclasses import dataclass, fields, is_dataclass
from decimal import Decimal
from enum import Enum, StrEnum
import hashlib
import json
import re

from .nasdaq_listed_archive import NasdaqListedArchive
from .sec_archive import SecArchive
from .sec_current_eps_comparability_qualification import (
    ComparabilityOutcome,
    RealEPSComparabilityQualification,
    SecCurrentEPSComparabilityRequest,
    qualify_sec_current_eps_comparability,
)
from .sec_filing_archive import SecFilingArchive
from .sec_reporting_subject_source_claims import ReportingSubjectClaimKind
from .sec_submissions_archive import SecSubmissionsArchive
from .sec_ticker_exchange_archive import SecTickerExchangeArchive

CONTRACT_VERSION = "2026-10-07-sec-ordinary-compounder-method-profile-v2"
QUALIFIER_VERSION = "2026-09-29-closed-sec-sic-profile-exclusions-v1"
PROFILE = "ORDINARY_COMPOUNDER"
_HASH = re.compile(r"[0-9a-f]{64}")


class OrdinaryCompounderProfileError(ValueError):
    """Invalid closed request or unsupported identity projection."""


class OrdinaryCompounderProfileStatus(StrEnum):
    ORDINARY_COMPOUNDER_PROFILE_ESTABLISHED = "ORDINARY_COMPOUNDER_PROFILE_ESTABLISHED"
    PROFILE_UNAVAILABLE = "PROFILE_UNAVAILABLE"
    PROFILE_UNSUPPORTED = "PROFILE_UNSUPPORTED"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"


class ProfileDecisionValue(StrEnum):
    EXCLUDED = "EXCLUDED"
    NOT_EXCLUDED = "NOT_EXCLUDED"
    UNRESOLVED = "UNRESOLVED"


class UnsupportedStructure(StrEnum):
    BANK = "BANK"
    INSURER = "INSURER"
    REIT = "REIT"
    ASSET_MANAGER = "ASSET_MANAGER"
    RESOURCES_MINING = "RESOURCES_MINING"
    ENERGY_CYCLICAL = "ENERGY_CYCLICAL"
    PIPELINE = "PIPELINE"
    UTILITY_ACCOUNTING = "UTILITY_ACCOUNTING"
    INVESTMENT_HOLDING = "INVESTMENT_HOLDING"
    MIXED_CONGLOMERATE = "MIXED_CONGLOMERATE"
    TURNAROUND = "TURNAROUND"
    LOSS_MAKING = "LOSS_MAKING"


class ProfileReason(StrEnum):
    PR5C_NOT_ESTABLISHED = "PR5C_NOT_ESTABLISHED"
    REPLAY_IDENTITY_MISMATCH = "REPLAY_IDENTITY_MISMATCH"
    SIC_MISSING_OR_INVALID = "SIC_MISSING_OR_INVALID"
    SIC_DESCRIPTION_MISSING_OR_INVALID = "SIC_DESCRIPTION_MISSING_OR_INVALID"
    UNSUPPORTED_SIC_PROFILE = "UNSUPPORTED_SIC_PROFILE"
    POSITIVE_FIVE_PERIOD_ROUTE_NOT_ESTABLISHED = "POSITIVE_FIVE_PERIOD_ROUTE_NOT_ESTABLISHED"
    REPORTING_SUBJECT_STABILITY_NOT_ESTABLISHED = "REPORTING_SUBJECT_STABILITY_NOT_ESTABLISHED"
    MIXED_STRUCTURE_UNRESOLVED = "MIXED_STRUCTURE_UNRESOLVED"


LIMITATIONS = (
    "METHODOLOGY_APPLICABILITY_ONLY",
    "NO_QUALITY_SCORE",
    "NO_MANAGEMENT_QUALITY_CLAIM",
    "NO_GROWTH_FORECAST",
    "NO_RECOMMENDATION_OR_RANKING",
    "NO_FINAL_ECONOMIC_ADMISSION",
    "SEC_SIC_AND_CONTROLLED_EVIDENCE_PROFILE_ONLY",
)


@dataclass(frozen=True, slots=True)
class SecOrdinaryCompounderProfileRequest:
    comparability_request: SecCurrentEPSComparabilityRequest
    expected_comparability_semantic_id: str
    expected_comparability_evidence_id: str

    def __post_init__(self):
        if type(self.comparability_request) is not SecCurrentEPSComparabilityRequest:
            raise OrdinaryCompounderProfileError("Exact PR5C selector request required")
        for value in (self.expected_comparability_semantic_id,
                      self.expected_comparability_evidence_id):
            if type(value) is not str or _HASH.fullmatch(value) is None:
                raise OrdinaryCompounderProfileError("Exact PR5C replay identities required")


@dataclass(frozen=True, slots=True)
class MethodProfileDecision:
    profile: UnsupportedStructure
    decision: ProfileDecisionValue
    reason: str
    supporting_semantic_ids: tuple[str, ...]
    supporting_evidence_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class OrdinaryCompounderMethodProfileQualification:
    contract_version: str
    qualifier_version: str
    status: OrdinaryCompounderProfileStatus
    profile: str | None
    source_cik: str | None
    sic: int | None
    sic_description: str | None
    decisions: tuple[MethodProfileDecision, ...]
    reasons: tuple[ProfileReason, ...]
    limitations: tuple[str, ...]
    upstream_comparability: RealEPSComparabilityQualification
    metadata_semantic_id: str | None
    metadata_evidence_id: str | None
    expected_comparability_semantic_id: str
    expected_comparability_evidence_id: str

    def __post_init__(self):
        for value in (
            self.expected_comparability_semantic_id,
            self.expected_comparability_evidence_id,
        ):
            if type(value) is not str or _HASH.fullmatch(value) is None:
                raise OrdinaryCompounderProfileError(
                    "Exact expected PR5C replay identities required"
                )

    @property
    def semantic_id(self):
        return _identity("profile-semantics", {
            "contract": self.contract_version,
            "qualifier": self.qualifier_version,
            "status": self.status,
            "profile": self.profile,
            "source_cik": self.source_cik,
            "sic": self.sic,
            "sic_description": self.sic_description,
            "decisions": self.decisions,
            "reasons": self.reasons,
            "limitations": self.limitations,
            "comparability_semantic_id": self.upstream_comparability.semantic_id,
            "metadata_semantic_id": self.metadata_semantic_id,
        })

    @property
    def evidence_id(self):
        return _identity("profile-evidence", {
            "semantic_id": self.semantic_id,
            "comparability_evidence_id": self.upstream_comparability.evidence_id,
            "metadata_evidence_id": self.metadata_evidence_id,
            "expected_comparability_semantic_id": (
                self.expected_comparability_semantic_id
            ),
            "expected_comparability_evidence_id": (
                self.expected_comparability_evidence_id
            ),
        })


def _project(value):
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {field.name: _project(getattr(value, field.name)) for field in fields(value)}
    if type(value) is Decimal:
        return str(value)
    if type(value) in (tuple, list):
        return [_project(item) for item in value]
    if type(value) is dict:
        return {key: _project(item) for key, item in value.items()}
    if value is None or type(value) in (str, int, bool):
        return value
    raise OrdinaryCompounderProfileError("Unsupported identity value")


def _identity(domain, value):
    raw = json.dumps(_project((QUALIFIER_VERSION, domain, value)), sort_keys=True,
                     separators=(",", ":"), ensure_ascii=True,
                     allow_nan=False).encode("ascii")
    return hashlib.sha256(raw).hexdigest()


def _normalize(value):
    return " ".join(re.sub(r"[^A-Z0-9]+", " ", value.upper()).split())


def _sic_metadata(comparability):
    inventory = comparability.upstream_reporting_subject_source.submissions_inventory
    try:
        metadata = json.loads(inventory.metadata_json.decode("ascii"))
    except (UnicodeError, ValueError, TypeError):
        return None, None, None, None
    raw_sic = metadata.get("sic") if type(metadata) is dict else None
    raw_description = metadata.get("sicDescription") if type(metadata) is dict else None
    if type(raw_sic) is int and not isinstance(raw_sic, bool):
        sic = raw_sic
    elif type(raw_sic) is str and re.fullmatch(r"[0-9]{1,4}", raw_sic):
        sic = int(raw_sic)
    else:
        sic = None
    description = (raw_description.strip() if type(raw_description) is str
                   and raw_description.strip() == raw_description
                   and raw_description else None)
    metadata_semantic_id = _identity("submissions-root-sic-metadata", {
        "cik": inventory.parent.cik,
        "sic": sic,
        "sic_description": description,
    }) if sic is not None and description is not None else None
    metadata_evidence_id = _identity("submissions-root-sic-evidence", {
        "semantic_id": metadata_semantic_id,
        "inventory_evidence_id": inventory.evidence_id,
        "parent_receipt_id": inventory.parent.receipt_id,
        "metadata_sha256": hashlib.sha256(inventory.metadata_json).hexdigest(),
    }) if metadata_semantic_id is not None else None
    return sic, description, metadata_semantic_id, metadata_evidence_id


def _structural_flags(sic, description):
    text = _normalize(description)
    tokens = set(text.split())
    return {
        UnsupportedStructure.BANK: 6000 <= sic <= 6199 or "BANK" in tokens,
        UnsupportedStructure.INSURER: 6300 <= sic <= 6411 or bool(tokens & {"INSURANCE", "INSURER"}),
        UnsupportedStructure.REIT: sic == 6798 or "REIT" in tokens
            or "REAL ESTATE INVESTMENT TRUST" in text,
        UnsupportedStructure.ASSET_MANAGER: 6200 <= sic <= 6289
            or "ASSET MANAGEMENT" in text or "INVESTMENT ADVISER" in text,
        UnsupportedStructure.RESOURCES_MINING: 1000 <= sic <= 1499
            or bool(tokens & {"MINING", "MINERALS", "METALS"}),
        UnsupportedStructure.ENERGY_CYCLICAL: sic in {1311, 1321, 1381, 1382, 1389, 2911}
            or "OIL AND GAS" in text or "PETROLEUM REFINING" in text,
        UnsupportedStructure.PIPELINE: sic in {4612, 4613, 4922}
            or "PIPELINE" in tokens,
        UnsupportedStructure.UTILITY_ACCOUNTING: 4900 <= sic <= 4991
            or "REGULATED UTILITY" in text,
        UnsupportedStructure.INVESTMENT_HOLDING: sic in {6719, 6722, 6726, 6799}
            or "INVESTMENT HOLDING" in text or "HOLDING COMPANY" in text,
        UnsupportedStructure.MIXED_CONGLOMERATE: "CONGLOMERATE" in tokens
            or "DIVERSIFIED HOLDING" in text,
    }


def qualify_sec_ordinary_compounder_profile(
    current_archive: SecArchive,
    submissions_archive: SecSubmissionsArchive,
    filing_archive: SecFilingArchive,
    ticker_exchange_archive: SecTickerExchangeArchive,
    nasdaq_listed_archive: NasdaqListedArchive,
    request: SecOrdinaryCompounderProfileRequest,
) -> OrdinaryCompounderMethodProfileQualification:
    """Freshly replay PR5C and classify only the reviewed methodology profile."""
    if (type(current_archive) is not SecArchive
            or type(submissions_archive) is not SecSubmissionsArchive
            or type(filing_archive) is not SecFilingArchive
            or type(ticker_exchange_archive) is not SecTickerExchangeArchive
            or type(nasdaq_listed_archive) is not NasdaqListedArchive
            or type(request) is not SecOrdinaryCompounderProfileRequest):
        raise OrdinaryCompounderProfileError("Exact typed archives/request required")
    comparability = qualify_sec_current_eps_comparability(
        current_archive, submissions_archive, filing_archive,
        ticker_exchange_archive, nasdaq_listed_archive,
        request.comparability_request)
    reasons = set()
    if comparability.outcome is not ComparabilityOutcome.COMPARABLE_REAL_EPS_ESTABLISHED:
        reasons.add(ProfileReason.PR5C_NOT_ESTABLISHED)
    if (comparability.semantic_id != request.expected_comparability_semantic_id
            or comparability.evidence_id != request.expected_comparability_evidence_id):
        reasons.add(ProfileReason.REPLAY_IDENTITY_MISMATCH)
    sic, description, metadata_semantic_id, metadata_evidence_id = _sic_metadata(comparability)
    if sic is None or not 100 <= sic <= 9999:
        reasons.add(ProfileReason.SIC_MISSING_OR_INVALID)
    if description is None:
        reasons.add(ProfileReason.SIC_DESCRIPTION_MISSING_OR_INVALID)

    decisions = []
    if sic is not None and description is not None:
        support_semantics = tuple(value for value in (
            metadata_semantic_id,
            comparability.historical_reporting_subject.qualified_subject_identity,
            comparability.semantic_id,
        ) if value is not None)
        support_evidence = tuple(value for value in (
            metadata_evidence_id, comparability.evidence_id,
        ) if value is not None)
        flags = _structural_flags(sic, description)
        mixed_signal = any(
            claim.kind is ReportingSubjectClaimKind.COMBINED_FINANCIAL_STATEMENTS_REFERENCE
            for claim in comparability.upstream_reporting_subject_source.explicit_claims)
        for profile in tuple(UnsupportedStructure)[:10]:
            detected = flags[profile]
            unresolved_mixed = (
                profile is UnsupportedStructure.MIXED_CONGLOMERATE
                and mixed_signal and not detected)
            decisions.append(MethodProfileDecision(
                profile,
                (ProfileDecisionValue.NOT_EXCLUDED if detected else
                 ProfileDecisionValue.UNRESOLVED if unresolved_mixed else
                 ProfileDecisionValue.EXCLUDED),
                (f"SEC_SIC_PROFILE_MATCH:{sic}:{description}" if detected else
                 "COMBINED_FINANCIAL_STATEMENTS_REQUIRE_MIXED_STRUCTURE_RESOLUTION"
                 if unresolved_mixed else
                 f"SEC_SIC_PROFILE_EXCLUDED:{sic}:{description}"),
                support_semantics, support_evidence,
            ))
        positive = (len(comparability.period_decisions) == 5
                    and all(item.c3_value > 0 for item in comparability.period_decisions))
        subject_stable = (
            comparability.historical_reporting_subject.qualified_subject_identity is not None)
        decisions.extend((
            MethodProfileDecision(
                UnsupportedStructure.TURNAROUND,
                ProfileDecisionValue.EXCLUDED if positive and subject_stable
                else ProfileDecisionValue.UNRESOLVED,
                ("STABLE_POSITIVE_FIVE_PERIOD_REPORTING_SUBJECT_ROUTE" if positive and subject_stable
                 else "TURNAROUND_EXCLUSION_NOT_ESTABLISHED"),
                support_semantics, support_evidence,
            ),
            MethodProfileDecision(
                UnsupportedStructure.LOSS_MAKING,
                ProfileDecisionValue.EXCLUDED if positive else ProfileDecisionValue.NOT_EXCLUDED,
                ("ALL_FIVE_QUALIFIED_DILUTED_EPS_PERIODS_STRICTLY_POSITIVE" if positive
                 else "POSITIVE_FIVE_PERIOD_ROUTE_NOT_ESTABLISHED"),
                support_semantics, support_evidence,
            ),
        ))
        if not positive:
            reasons.add(ProfileReason.POSITIVE_FIVE_PERIOD_ROUTE_NOT_ESTABLISHED)
        if not subject_stable:
            reasons.add(ProfileReason.REPORTING_SUBJECT_STABILITY_NOT_ESTABLISHED)
        if any(item.profile is UnsupportedStructure.MIXED_CONGLOMERATE
               and item.decision is ProfileDecisionValue.UNRESOLVED for item in decisions):
            reasons.add(ProfileReason.MIXED_STRUCTURE_UNRESOLVED)

    if ProfileReason.REPLAY_IDENTITY_MISMATCH in reasons:
        status = OrdinaryCompounderProfileStatus.SOURCE_CONFLICT
    elif decisions and any(item.decision is ProfileDecisionValue.NOT_EXCLUDED
                           for item in decisions):
        reasons.add(ProfileReason.UNSUPPORTED_SIC_PROFILE)
        status = OrdinaryCompounderProfileStatus.PROFILE_UNSUPPORTED
    elif reasons or len(decisions) != len(UnsupportedStructure) or any(
            item.decision is not ProfileDecisionValue.EXCLUDED for item in decisions):
        status = OrdinaryCompounderProfileStatus.PROFILE_UNAVAILABLE
    else:
        status = OrdinaryCompounderProfileStatus.ORDINARY_COMPOUNDER_PROFILE_ESTABLISHED
    return OrdinaryCompounderMethodProfileQualification(
        CONTRACT_VERSION, QUALIFIER_VERSION, status,
        PROFILE if status is OrdinaryCompounderProfileStatus.ORDINARY_COMPOUNDER_PROFILE_ESTABLISHED
        else None,
        comparability.upstream_reporting_subject_source.source_cik,
        sic, description, tuple(decisions),
        tuple(sorted(reasons, key=lambda item: item.value)), LIMITATIONS,
        comparability, metadata_semantic_id, metadata_evidence_id,
        request.expected_comparability_semantic_id,
        request.expected_comparability_evidence_id,
    )
