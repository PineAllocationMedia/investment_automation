"""PR5E final admission for the one bounded real Expected Return route.

The public function accepts only controlled archives and closed replay selectors.
It freshly reconstructs PR5D2, creates real-capable PR4B1 facts, and delegates all
assumption construction and calculation to the existing PR4B1 -> PR4A path.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum, StrEnum
from fractions import Fraction
import hashlib
import json
import math
import re

from . import expected_return_assumptions as assumptions
from .expected_return_approved_policy_v1 import get_owner_approved_policy_proposal
from .expected_return_pr5d_bundle import (
    PR5D2BundleStatus,
    PR5D2RealExpectedReturnRoots,
    PR5D2RealExpectedReturnRootsRequest,
    assemble_expected_return_pr5d_bundle,
)

CONTRACT_VERSION = "2026-09-30-pr5e-final-real-expected-return-admission-v1"
ADAPTER_VERSION = "2026-09-30-pr5e-real-pr4b1-adapter-v1"
_HASH = re.compile(r"[0-9a-f]{64}")


class PR5EAdapterError(ValueError):
    """Malformed closed PR5E request or impossible admitted representation."""


class _Binary64Unavailable(ValueError):
    """A positive exact source value cannot cross the PR5E binary64 boundary."""


class PR5EStatus(StrEnum):
    REAL_EXPECTED_RETURN_ADMITTED = "REAL_EXPECTED_RETURN_ADMITTED"
    UNAVAILABLE = "UNAVAILABLE"
    UNSUPPORTED = "UNSUPPORTED"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"


class PR5EReason(StrEnum):
    PR5D2_ROOTS_UNAVAILABLE = "PR5D2_ROOTS_UNAVAILABLE"
    PR5D2_ROOTS_UNSUPPORTED = "PR5D2_ROOTS_UNSUPPORTED"
    PR5D2_SOURCE_CONFLICT = "PR5D2_SOURCE_CONFLICT"
    PR5D2_REPLAY_IDENTITY_MISMATCH = "PR5D2_REPLAY_IDENTITY_MISMATCH"
    PR5D2_SUCCESS_SHAPE_MISMATCH = "PR5D2_SUCCESS_SHAPE_MISMATCH"
    APPROVED_POLICY_IDENTITY_MISMATCH = "APPROVED_POLICY_IDENTITY_MISMATCH"
    PRICE_BINARY64_REPRESENTATION_UNAVAILABLE = "PRICE_BINARY64_REPRESENTATION_UNAVAILABLE"
    EPS_BINARY64_REPRESENTATION_UNAVAILABLE = "EPS_BINARY64_REPRESENTATION_UNAVAILABLE"
    PR4B1_CONSTRUCTOR_UNAVAILABLE = "PR4B1_CONSTRUCTOR_UNAVAILABLE"


LIMITATIONS = (
    "FINAL_ADMISSION_FOR_BOUNDED_SUPPORTED_ROUTE_ONLY",
    "DIAGNOSTIC_CHALLENGER_ONLY",
    "NO_PRODUCTION_OR_V1_AUTHORITY",
    "NO_HISTORICAL_AS_OF_OR_PIT_AUTHORITY",
    "PUBLICATION_TIME_UNKNOWN",
    "CAPTURE_BOUND_AVAILABILITY_ONLY",
    "PAYER_ROUTE_UNSUPPORTED",
    "ROUTE_LOCAL_SECURITY_IDENTITY_ONLY",
    "NO_UNIVERSAL_CORPORATE_ACTION_COMPLETENESS_CLAIM",
    "NO_RECOMMENDATION_ALLOCATION_OR_EXECUTION_AUTHORITY",
)


@dataclass(frozen=True, slots=True)
class PR5ERealExpectedReturnRequest:
    pr5d2_request: PR5D2RealExpectedReturnRootsRequest
    expected_pr5d2_semantic_id: str
    expected_pr5d2_evidence_id: str

    def __post_init__(self):
        if type(self.pr5d2_request) is not PR5D2RealExpectedReturnRootsRequest:
            raise PR5EAdapterError("Exact PR5D2 replay request required")
        for value in (self.expected_pr5d2_semantic_id,
                      self.expected_pr5d2_evidence_id):
            if type(value) is not str or _HASH.fullmatch(value) is None:
                raise PR5EAdapterError("Exact PR5D2 semantic/evidence identities required")


@dataclass(frozen=True, slots=True)
class PR5EAdmissionResult:
    contract_version: str
    adapter_version: str
    status: PR5EStatus
    reasons: tuple[PR5EReason, ...]
    pr5d2_semantic_id: str
    pr5d2_evidence_id: str
    admitted_share_basis_identity: str | None
    analytical_as_of: str | None
    qualified_facts: assumptions.QualifiedFacts | None
    construction: assumptions.ConstructionResult | None
    admission_semantic_id: str
    admission_evidence_id: str
    limitations: tuple[str, ...]
    upstream_pr5d2: PR5D2RealExpectedReturnRoots


def _project(value):
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {field.name: _project(getattr(value, field.name)) for field in fields(value)}
    if type(value) is Decimal:
        sign, digits, exponent = value.as_tuple()
        return {"decimal_tuple": [sign, list(digits), exponent]}
    if type(value) is float:
        if not math.isfinite(value):
            raise PR5EAdapterError("Nonfinite identity value")
        return {"binary64_hex": value.hex()}
    if type(value) in (tuple, list):
        return [_project(item) for item in value]
    if type(value) is dict:
        return {key: _project(item) for key, item in value.items()}
    if value is None or type(value) in (str, int, bool):
        return value
    raise PR5EAdapterError("Unsupported PR5E identity value")


def _identity(domain, value):
    raw = json.dumps(_project((ADAPTER_VERSION, domain, value)), sort_keys=True,
                     separators=(",", ":"), ensure_ascii=True,
                     allow_nan=False).encode("ascii")
    return hashlib.sha256(raw).hexdigest()


def _timestamp(value):
    if type(value) is not str:
        raise PR5EAdapterError("Exact capture timestamp required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError
        return parsed.astimezone(timezone.utc)
    except (ValueError, OverflowError) as exc:
        raise PR5EAdapterError("Invalid capture timestamp") from exc


def _capture_times(value, *, field_name=None, seen=None):
    """Collect stored evidence captures only; never consult a runtime clock."""
    if seen is None:
        seen = set()
    if field_name in {"captured_at", "filing_captured_at"} and type(value) is str:
        return (_timestamp(value),)
    identifier = id(value)
    if is_dataclass(value):
        if identifier in seen:
            return ()
        seen.add(identifier)
        return tuple(item for field in fields(value)
                     for item in _capture_times(getattr(value, field.name),
                                                field_name=field.name, seen=seen))
    if type(value) in (tuple, list):
        return tuple(item for child in value
                     for item in _capture_times(child, seen=seen))
    if type(value) is dict:
        return tuple(item for child in value.values()
                     for item in _capture_times(child, seen=seen))
    return ()


def _real_provenance(*, source_kind, source_reference, source_version,
                     source_document_hash, source_locator, captured_at,
                     extractor_id):
    return assumptions.RealProvenance(
        source_kind, source_reference, source_version, source_document_hash,
        source_locator, None, captured_at, captured_at, extractor_id, "1",
        assumptions.PublicationSemantics.UNKNOWN,
        assumptions.AvailabilitySemantics.CAPTURE_BOUND,
    )


def _observation_id(kind, value):
    return "pr5e:" + kind + ":" + _identity("observation:" + kind, value)


def _adapt_eps(value, numerator, denominator):
    """Exact Decimal -> rational -> exact bridge -> one binary64 conversion."""
    if type(value) is not Decimal or type(numerator) is not int or type(denominator) is not int:
        raise PR5EAdapterError("Exact Decimal and integral bridge terms required")
    if numerator <= 0 or denominator <= 0:
        raise PR5EAdapterError("Positive bridge multiplier required")
    try:
        converted = float(Fraction(value) * Fraction(numerator, denominator))
    except (OverflowError, ValueError) as exc:
        raise _Binary64Unavailable from exc
    if not math.isfinite(converted) or converted <= 0:
        raise _Binary64Unavailable
    return converted


def _adapt_price(value):
    """Convert the exact admitted price once and require positive finite binary64."""
    if type(value) is not Decimal:
        raise PR5EAdapterError("Exact Decimal price required")
    try:
        converted = float(value)
    except (OverflowError, ValueError) as exc:
        raise _Binary64Unavailable from exc
    if not math.isfinite(converted) or converted <= 0:
        raise _Binary64Unavailable
    return converted


def _share_basis_identity(roots):
    bridge = roots.basis_bridge
    return _identity("admitted-share-basis", {
        "contract_version": CONTRACT_VERSION,
        "adapter_version": ADAPTER_VERSION,
        "route_local_security_key": roots.route_local_security_key,
        "canonical_selected_common_class": roots.canonical_selected_common_class,
        "historical_qualified_basis_identity": roots.historical_qualified_basis_identity,
        "basis_bridge_semantic_id": bridge.semantic_id,
        "basis_bridge_evidence_id": bridge.evidence_id,
        "quote_semantic_id": bridge.quote_semantic_id,
        "quote_evidence_id": bridge.quote_evidence_id,
        "bridge_multiplier": (roots.basis_multiplier_numerator,
                              roots.basis_multiplier_denominator),
        "route_inventory_semantic_id": bridge.route_inventory_semantic_id,
        "route_inventory_evidence_id": bridge.route_inventory_evidence_id,
        "recent_share_basis_semantic_id": bridge.recent_share_basis_source.semantic_id,
        "recent_share_basis_evidence_id": bridge.recent_share_basis_source.evidence_id,
        "yahoo_split_history_semantic_id": bridge.yahoo_split_history_semantic_id,
        "yahoo_split_history_evidence_id": bridge.yahoo_split_history_evidence_id,
        "reconciled_corporate_actions": roots.reconciled_corporate_actions,
    })


def _result(status, reasons, roots, *, share_basis=None, as_of=None,
            qualified_facts=None, construction=None):
    reason_tuple = tuple(sorted(set(reasons), key=lambda item: item.value))
    semantic = _identity("admission-semantics", {
        "contract": CONTRACT_VERSION,
        "adapter": ADAPTER_VERSION,
        "status": status,
        "reasons": reason_tuple,
        "pr5d2_semantic_id": roots.semantic_id,
        "share_basis": share_basis,
        "as_of": as_of,
        "fact_ids": (() if qualified_facts is None else tuple(
            item.identity.observation_id for item in qualified_facts.roots)),
        "constructor_status": None if construction is None else construction.status,
        "constructor_lineage": None if construction is None else construction.lineage_hash,
        "limitations": LIMITATIONS,
    })
    evidence = _identity("admission-evidence", {
        "semantic_id": semantic,
        "pr5d2_evidence_id": roots.evidence_id,
        "fact_provenance": (() if qualified_facts is None else tuple(
            item.identity.provenance for item in qualified_facts.roots)),
    })
    return PR5EAdmissionResult(
        CONTRACT_VERSION, ADAPTER_VERSION, status, reason_tuple,
        roots.semantic_id, roots.evidence_id, share_basis, as_of,
        qualified_facts, construction, semantic, evidence, LIMITATIONS, roots,
    )


def admit_real_expected_return_pr5e(
    current_archive: object,
    submissions_archive: object,
    filing_archive: object,
    ticker_exchange_archive: object,
    nasdaq_listed_archive: object,
    quote_archive: object,
    split_history_archive: object,
    request: PR5ERealExpectedReturnRequest,
) -> PR5EAdmissionResult:
    """Freshly replay PR5D2 and admit only its exact supported nonpayer route."""
    if type(request) is not PR5ERealExpectedReturnRequest:
        raise PR5EAdapterError("Exact typed PR5E request required")
    roots = assemble_expected_return_pr5d_bundle(
        current_archive, submissions_archive, filing_archive,
        ticker_exchange_archive, nasdaq_listed_archive, quote_archive,
        split_history_archive, request.pr5d2_request,
    )
    if (roots.semantic_id != request.expected_pr5d2_semantic_id
            or roots.evidence_id != request.expected_pr5d2_evidence_id):
        return _result(PR5EStatus.SOURCE_CONFLICT,
                       (PR5EReason.PR5D2_REPLAY_IDENTITY_MISMATCH,), roots)
    if roots.status is PR5D2BundleStatus.SOURCE_CONFLICT:
        return _result(PR5EStatus.SOURCE_CONFLICT,
                       (PR5EReason.PR5D2_SOURCE_CONFLICT,), roots)
    if roots.status is PR5D2BundleStatus.PR5D_ROOTS_UNSUPPORTED:
        return _result(PR5EStatus.UNSUPPORTED,
                       (PR5EReason.PR5D2_ROOTS_UNSUPPORTED,), roots)
    if roots.status is PR5D2BundleStatus.PR5D_ROOTS_UNAVAILABLE:
        return _result(PR5EStatus.UNAVAILABLE,
                       (PR5EReason.PR5D2_ROOTS_UNAVAILABLE,), roots)

    bridge = roots.basis_bridge
    quote = bridge.upstream_quote
    presentation = bridge.upstream_comparability.presentation
    nonpayer_source = roots.nonpayer.upstream_nonpayer_source
    profile_inventory = (roots.profile.upstream_comparability
                         .upstream_reporting_subject_source.submissions_inventory)
    required = (
        roots.route_local_security_key, roots.canonical_selected_common_class,
        roots.historical_qualified_basis_identity, roots.quote_price,
        roots.quote_timestamp, roots.quote_currency, roots.quote_unit,
        roots.accounting_basis, roots.basis_multiplier_numerator,
        roots.basis_multiplier_denominator, roots.nonpayer_period_start,
        roots.nonpayer_period_end, roots.nonpayer_status_identity,
        roots.ordinary_compounder_profile_identity, presentation.table_sha256,
    )
    if (any(value is None for value in required)
            or len(roots.period_decisions) != 5
            or roots.quote_currency != "USD"
            or roots.quote_unit != "CURRENCY_PER_SHARE"
            or roots.accounting_basis != "US_GAAP"
            or roots.profile.profile != "ORDINARY_COMPOUNDER"
            or roots.nonpayer_period_end != roots.period_decisions[-1].period_end):
        return _result(PR5EStatus.SOURCE_CONFLICT,
                       (PR5EReason.PR5D2_SUCCESS_SHAPE_MISMATCH,), roots)

    policy = get_owner_approved_policy_proposal()
    proposal = policy.proposal
    if (policy.proposal_hash != roots.approved_proposal_hash
            or proposal.proposal_id != roots.approved_policy_version
            or proposal.mature_policy.policy_hash != roots.mature_policy_hash
            or proposal.terminal_policy.policy_hash != roots.terminal_policy_hash
            or proposal.nonpayer_distribution_policy.policy_hash
            != roots.selected_nonpayer_distribution_policy_hash):
        return _result(PR5EStatus.SOURCE_CONFLICT,
                       (PR5EReason.APPROVED_POLICY_IDENTITY_MISMATCH,), roots)

    captures = _capture_times(roots)
    if not captures:
        return _result(PR5EStatus.SOURCE_CONFLICT,
                       (PR5EReason.PR5D2_SUCCESS_SHAPE_MISMATCH,), roots)
    as_of = max(captures).isoformat()
    share_basis_id = _share_basis_identity(roots)
    basis = assumptions.ShareBasis(roots.quote_currency, share_basis_id)
    security_id = roots.route_local_security_key
    share_class = roots.canonical_selected_common_class

    try:
        price_value = _adapt_price(roots.quote_price)
    except _Binary64Unavailable:
        return _result(PR5EStatus.UNAVAILABLE,
                       (PR5EReason.PRICE_BINARY64_REPRESENTATION_UNAVAILABLE,),
                       roots, share_basis=share_basis_id, as_of=as_of)
    quote_receipt = quote.quote_extraction.receipt
    price_identity = assumptions.Identity(
        _observation_id("price", (quote.semantic_id, quote.evidence_id,
                                  roots.quote_price, share_basis_id)),
        security_id, share_class,
        _real_provenance(
            source_kind=assumptions.SourceKind.YAHOO_MARKET_PROVIDER,
            source_reference="YAHOO_FINANCE_CHART_CURRENT_QUOTE_V1:" + quote_receipt.receipt_id,
            source_version=quote.contract_version,
            source_document_hash=quote_receipt.content_sha256,
            source_locator=quote.quote_extraction.response_structure_locator,
            captured_at=quote.captured_at,
            extractor_id=assumptions.AdapterIdentity.PR5E_REAL_OBSERVED_PRICE_V1,
        ),
    )
    price = assumptions.ObservedPrice(
        price_identity, price_value, basis,
        _timestamp(roots.quote_timestamp).date().isoformat(),
    )

    eps_roots = []
    for decision in roots.period_decisions:
        try:
            eps_value = _adapt_eps(
                decision.c3_value, roots.basis_multiplier_numerator,
                roots.basis_multiplier_denominator,
            )
        except _Binary64Unavailable:
            return _result(PR5EStatus.UNAVAILABLE,
                           (PR5EReason.EPS_BINARY64_REPRESENTATION_UNAVAILABLE,),
                           roots, share_basis=share_basis_id, as_of=as_of)
        observation_id = _observation_id("reported-diluted-eps", (
            bridge.upstream_comparability.semantic_id,
            bridge.upstream_comparability.evidence_id,
            decision, share_basis_id,
        ))
        locator = (f"filing:{presentation.accession};document:{presentation.document_filename};"
                   f"table:{presentation.table_sha256};period:{decision.period_end}")
        identity = assumptions.Identity(
            observation_id, security_id, share_class,
            _real_provenance(
                source_kind=assumptions.SourceKind.SEC_CURRENT,
                source_reference="SEC_FIVE_YEAR_DILUTED_EPS_PRESENTATION:" + presentation.filing_receipt_id,
                source_version=bridge.upstream_comparability.contract_version,
                source_document_hash=presentation.table_sha256,
                source_locator=locator,
                captured_at=presentation.filing_captured_at,
                extractor_id=assumptions.AdapterIdentity.PR5E_REAL_REPORTED_DILUTED_EPS_V1,
            ),
        )
        eps_roots.append(assumptions.ReportedDilutedEPS(
            identity, eps_value,
            basis,
            assumptions.AnnualPeriod(decision.period_start, decision.period_end),
            roots.accounting_basis,
        ))

    nonpayer_identity = assumptions.Identity(
        _observation_id("verified-nonpayer", (
            roots.nonpayer_status_identity, roots.nonpayer.evidence_id,
            roots.nonpayer_period_start, roots.nonpayer_period_end,
            share_basis_id,
        )),
        security_id, share_class,
        _real_provenance(
            source_kind=assumptions.SourceKind.SEC_CURRENT,
            source_reference="SEC_COMPANYFACTS_VERIFIED_NONPAYER:" + nonpayer_source.receipt_id,
            source_version=nonpayer_source.contract_version,
            source_document_hash=nonpayer_source.source_object_hash,
            source_locator="/facts/us-gaap/{CommonStockDividendsPerShareDeclared,CommonStockDividendsPerShareCashPaid}",
            captured_at=nonpayer_source.captured_at,
            extractor_id=assumptions.AdapterIdentity.PR5E_REAL_VERIFIED_NONPAYER_V1,
        ),
    )
    nonpayer = assumptions.VerifiedNonpayer(
        nonpayer_identity,
        assumptions.AnnualPeriod(roots.nonpayer_period_start,
                                 roots.nonpayer_period_end),
    )

    profile_parent = profile_inventory.parent
    profile_identity = assumptions.Identity(
        _observation_id("profile", (
            roots.ordinary_compounder_profile_identity,
            roots.profile.evidence_id, roots.profile.decisions,
            share_basis_id,
        )),
        security_id, share_class,
        _real_provenance(
            source_kind=assumptions.SourceKind.SEC_CURRENT,
            source_reference="SEC_SUBMISSIONS_ORDINARY_COMPOUNDER:" + profile_parent.receipt_id,
            source_version=roots.profile.contract_version,
            source_document_hash=profile_parent.content_sha256,
            source_locator="/sic;/sicDescription",
            captured_at=profile_parent.captured_at,
            extractor_id=assumptions.AdapterIdentity.PR5E_REAL_PROFILE_QUALIFICATION_V1,
        ),
    )
    profile = assumptions.ProfileQualification(
        profile_identity, assumptions.Profile.ORDINARY_COMPOUNDER,
        assumptions.UNSUPPORTED_STRUCTURES,
        "PR5D2 ORDINARY_COMPOUNDER methodology applicability only; no Quality, Durability, ranking, recommendation, or management claim",
    )
    facts = assumptions.QualifiedFacts(
        assumptions.EXPECTED_RETURN_REAL_FACTS_CONTRACT_VERSION,
        as_of, security_id, share_class, basis, roots.accounting_basis,
        roots.period_decisions[-1].period_end,
        (price, *eps_roots, nonpayer, profile),
    )
    construction = assumptions.construct_expected_return(
        facts,
        mature_policy=proposal.mature_policy,
        terminal_policy=proposal.terminal_policy,
        distribution_policy=proposal.nonpayer_distribution_policy,
    )
    if construction.status != "BUILT" or construction.diagnostic is None:
        return _result(PR5EStatus.UNAVAILABLE,
                       (PR5EReason.PR4B1_CONSTRUCTOR_UNAVAILABLE,), roots,
                       share_basis=share_basis_id, as_of=as_of,
                       qualified_facts=facts, construction=construction)
    return _result(PR5EStatus.REAL_EXPECTED_RETURN_ADMITTED, (), roots,
                   share_basis=share_basis_id, as_of=as_of,
                   qualified_facts=facts, construction=construction)
