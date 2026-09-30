"""Route-local join of PR5D0B nonpayer evidence to the successful PR5B/PR5C route."""
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
from .sec_current_security_eps_qualification import ComponentStatus
from .sec_filing_archive import SecFilingArchive
from .sec_submissions_archive import SecSubmissionsArchive
from .sec_ticker_exchange_archive import SecTickerExchangeArchive
from .sec_verified_nonpayer import (
    VerifiedNonpayerRequest,
    VerifiedNonpayerSourceResult,
    VerifiedNonpayerStatus,
    resolve_sec_verified_nonpayer,
)

CONTRACT_VERSION = "2026-09-29-sec-current-route-local-verified-nonpayer-v1"
QUALIFIER_VERSION = "2026-09-29-pr5b-pr5c-companyfacts-nonpayer-join-v1"
_HASH = re.compile(r"[0-9a-f]{64}")


class CurrentVerifiedNonpayerError(ValueError):
    """Invalid typed selector or identity projection."""


class RouteLocalVerifiedNonpayerStatus(StrEnum):
    VERIFIED_NONPAYER_ESTABLISHED = "VERIFIED_NONPAYER_ESTABLISHED"
    NONPAYER_UNAVAILABLE = "NONPAYER_UNAVAILABLE"
    NONPAYER_UNSUPPORTED = "NONPAYER_UNSUPPORTED"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"


class RouteLocalNonpayerReason(StrEnum):
    PR5C_NOT_ESTABLISHED = "PR5C_NOT_ESTABLISHED"
    REPLAY_IDENTITY_MISMATCH = "REPLAY_IDENTITY_MISMATCH"
    NONPAYER_SOURCE_NOT_ESTABLISHED = "NONPAYER_SOURCE_NOT_ESTABLISHED"
    FOREIGN_CIK = "FOREIGN_CIK"
    WRONG_LATEST_FISCAL_PERIOD = "WRONG_LATEST_FISCAL_PERIOD"
    UNIT_MISMATCH = "UNIT_MISMATCH"
    DIFFERENT_COMPANYFACTS_RECEIPT = "DIFFERENT_COMPANYFACTS_RECEIPT"
    POST_AUTHORITY_BOUNDARY_CAPTURE = "POST_AUTHORITY_BOUNDARY_CAPTURE"
    RELEVANT_CLASS_NOT_UNIQUELY_ESTABLISHED = "RELEVANT_CLASS_NOT_UNIQUELY_ESTABLISHED"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"


LIMITATIONS = (
    "ROUTE_LOCAL_JOIN_ONLY",
    "NO_GENERAL_MULTI_CLASS_DIVIDEND_ALLOCATION",
    "PAYER_ROUTE_NOT_SUPPORTED",
    "NO_PR4B1_VERIFIED_NONPAYER_ROOT",
    "NO_FINAL_ECONOMIC_ADMISSION",
    "PR5E_FINAL_ADMISSION_REQUIRED",
)


@dataclass(frozen=True, slots=True)
class SecCurrentVerifiedNonpayerRequest:
    comparability_request: SecCurrentEPSComparabilityRequest
    expected_comparability_semantic_id: str
    expected_comparability_evidence_id: str
    nonpayer_request: VerifiedNonpayerRequest
    expected_nonpayer_semantic_id: str
    expected_nonpayer_evidence_id: str

    def __post_init__(self):
        if (type(self.comparability_request) is not SecCurrentEPSComparabilityRequest
                or type(self.nonpayer_request) is not VerifiedNonpayerRequest):
            raise CurrentVerifiedNonpayerError("Exact typed replay selectors required")
        for value in (self.expected_comparability_semantic_id,
                      self.expected_comparability_evidence_id,
                      self.expected_nonpayer_semantic_id,
                      self.expected_nonpayer_evidence_id):
            if type(value) is not str or _HASH.fullmatch(value) is None:
                raise CurrentVerifiedNonpayerError("Exact replay identities required")


@dataclass(frozen=True, slots=True)
class RouteLocalVerifiedNonpayerQualification:
    contract_version: str
    qualifier_version: str
    status: RouteLocalVerifiedNonpayerStatus
    reasons: tuple[RouteLocalNonpayerReason, ...]
    route_local_issuer_key: str | None
    route_local_security_key: str | None
    canonical_source_class_label: str | None
    period_start: str | None
    period_end: str | None
    unit: str | None
    upstream_comparability: RealEPSComparabilityQualification
    upstream_nonpayer_source: VerifiedNonpayerSourceResult
    limitations: tuple[str, ...]

    @property
    def semantic_id(self):
        return _identity("nonpayer-join-semantics", {
            "contract": self.contract_version,
            "qualifier": self.qualifier_version,
            "status": self.status,
            "reasons": self.reasons,
            "issuer_key": self.route_local_issuer_key,
            "security_key": self.route_local_security_key,
            "class_label": self.canonical_source_class_label,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "unit": self.unit,
            "comparability_semantic_id": self.upstream_comparability.semantic_id,
            "nonpayer_semantic_id": self.upstream_nonpayer_source.semantic_hash,
            "limitations": self.limitations,
        })

    @property
    def evidence_id(self):
        return _identity("nonpayer-join-evidence", {
            "semantic_id": self.semantic_id,
            "comparability_evidence_id": self.upstream_comparability.evidence_id,
            "nonpayer_evidence_id": self.upstream_nonpayer_source.evidence_hash,
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
    raise CurrentVerifiedNonpayerError("Unsupported identity value")


def _identity(domain, value):
    raw = json.dumps(_project((QUALIFIER_VERSION, domain, value)), sort_keys=True,
                     separators=(",", ":"), ensure_ascii=True,
                     allow_nan=False).encode("ascii")
    return hashlib.sha256(raw).hexdigest()


def qualify_sec_current_verified_nonpayer(
    current_archive: SecArchive,
    submissions_archive: SecSubmissionsArchive,
    filing_archive: SecFilingArchive,
    ticker_exchange_archive: SecTickerExchangeArchive,
    nasdaq_listed_archive: NasdaqListedArchive,
    request: SecCurrentVerifiedNonpayerRequest,
) -> RouteLocalVerifiedNonpayerQualification:
    """Freshly replay both source graphs and permit only the exact successful join."""
    if (type(current_archive) is not SecArchive
            or type(submissions_archive) is not SecSubmissionsArchive
            or type(filing_archive) is not SecFilingArchive
            or type(ticker_exchange_archive) is not SecTickerExchangeArchive
            or type(nasdaq_listed_archive) is not NasdaqListedArchive
            or type(request) is not SecCurrentVerifiedNonpayerRequest):
        raise CurrentVerifiedNonpayerError("Exact typed archives/request required")
    comparability = qualify_sec_current_eps_comparability(
        current_archive, submissions_archive, filing_archive,
        ticker_exchange_archive, nasdaq_listed_archive,
        request.comparability_request)
    nonpayer = resolve_sec_verified_nonpayer(current_archive, request.nonpayer_request)
    reasons = set()
    if comparability.outcome is not ComparabilityOutcome.COMPARABLE_REAL_EPS_ESTABLISHED:
        reasons.add(RouteLocalNonpayerReason.PR5C_NOT_ESTABLISHED)
    if (comparability.semantic_id != request.expected_comparability_semantic_id
            or comparability.evidence_id != request.expected_comparability_evidence_id
            or nonpayer.semantic_hash != request.expected_nonpayer_semantic_id
            or nonpayer.evidence_hash != request.expected_nonpayer_evidence_id):
        reasons.add(RouteLocalNonpayerReason.REPLAY_IDENTITY_MISMATCH)
    security = comparability.upstream_security_eps
    current_evidence = (security.upstream_registered_listing_bridge.temporal_boundary
                        .current_evidence)
    current_receipt = current_evidence.receipt
    source_cik = current_evidence.request.cik
    latest_period = (comparability.period_decisions[-1].period_end
                     if len(comparability.period_decisions) == 5 else None)
    if request.nonpayer_request.cik != source_cik:
        reasons.add(RouteLocalNonpayerReason.FOREIGN_CIK)
    if request.nonpayer_request.latest_required_fiscal_end != latest_period:
        reasons.add(RouteLocalNonpayerReason.WRONG_LATEST_FISCAL_PERIOD)
    if request.nonpayer_request.expected_unit != "USD/shares":
        reasons.add(RouteLocalNonpayerReason.UNIT_MISMATCH)
    if current_receipt is None or request.nonpayer_request.receipt_id != current_receipt.receipt_id:
        reasons.add(RouteLocalNonpayerReason.DIFFERENT_COMPANYFACTS_RECEIPT)
    if nonpayer.captured_at > (security.current_authority_boundary or ""):
        reasons.add(RouteLocalNonpayerReason.POST_AUTHORITY_BOUNDARY_CAPTURE)
    if (security.relevant_class_coverage.status
            is not ComponentStatus.QUALIFICATION_ESTABLISHED
            or security.participation.status
            is not ComponentStatus.QUALIFICATION_ESTABLISHED
            or security.participation.canonical_source_class_label is None):
        reasons.add(RouteLocalNonpayerReason.RELEVANT_CLASS_NOT_UNIQUELY_ESTABLISHED)
    if nonpayer.status is not VerifiedNonpayerStatus.VERIFIED_NONPAYER_SOURCE_ESTABLISHED:
        reasons.add(RouteLocalNonpayerReason.NONPAYER_SOURCE_NOT_ESTABLISHED)
        if nonpayer.status is VerifiedNonpayerStatus.SOURCE_CONFLICT:
            reasons.add(RouteLocalNonpayerReason.SOURCE_CONFLICT)

    if reasons & {RouteLocalNonpayerReason.REPLAY_IDENTITY_MISMATCH,
                  RouteLocalNonpayerReason.SOURCE_CONFLICT}:
        status = RouteLocalVerifiedNonpayerStatus.SOURCE_CONFLICT
    elif reasons & {RouteLocalNonpayerReason.UNIT_MISMATCH,
                    RouteLocalNonpayerReason.RELEVANT_CLASS_NOT_UNIQUELY_ESTABLISHED}:
        status = RouteLocalVerifiedNonpayerStatus.NONPAYER_UNSUPPORTED
    elif reasons:
        status = RouteLocalVerifiedNonpayerStatus.NONPAYER_UNAVAILABLE
    else:
        status = RouteLocalVerifiedNonpayerStatus.VERIFIED_NONPAYER_ESTABLISHED
    positive = status is RouteLocalVerifiedNonpayerStatus.VERIFIED_NONPAYER_ESTABLISHED
    return RouteLocalVerifiedNonpayerQualification(
        CONTRACT_VERSION, QUALIFIER_VERSION, status,
        tuple(sorted(reasons, key=lambda item: item.value)),
        security.route_local_issuer_key if positive else None,
        security.route_local_security_key if positive else None,
        security.participation.canonical_source_class_label if positive else None,
        nonpayer.period_start if positive else None,
        nonpayer.period_end if positive else None,
        request.nonpayer_request.expected_unit if positive else None,
        comparability, nonpayer, LIMITATIONS,
    )
