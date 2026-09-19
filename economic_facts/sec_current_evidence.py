"""Controlled stored SEC capture -> unchanged C3 replay -> CURRENT authority.

There is no acquisition import or live network operation. The caller must own a
controlled archive populated by reviewed local code; uploaded/self-authored LIVE
receipts are not trusted. Local code/clock/archive compromise is outside C2's
threat model. A hash or a frozen report alone is never an authority credential.
"""
from dataclasses import dataclass

from .sec_archive import (ACQUISITION_CONTRACT_VERSION, LIVE_ACQUISITION_CONTRACT_VERSION,
                          RECEIPT_SCHEMA_VERSION, ArchiveError, CaptureReceipt, SecArchive,
                          endpoint_for)
from .sec_diluted_eps import EXTRACTION_VERSION
from .sec_eps_series import (CaptureAuthority, ResolutionMode, ResolutionReason,
    ResolutionStatus, SERIES_CONTRACT_VERSION, SERIES_RESOLVER_VERSION,
    SeriesResolutionError, SeriesResolutionRequest, SeriesResolutionResult,
    resolve_annual_diluted_eps)
from .source_authority import (AuthorityProperty as P, SEC_COMPANYFACTS_LIVE_CURRENT_V1,
                               get_source_route, _hash)
from .current_authority import (AuthorityErrorReason as E, AuthorityReason as R,
    CurrentAuthorityAssessment, CurrentAuthorityError, _build_assessment, _require)

SEC_CURRENT_EVIDENCE_VERSION = "2026-09-19-sec-current-evidence-verifier-v1"


@dataclass(frozen=True, slots=True)
class SecCurrentEvidenceAssessment:
    contract_version: str
    request: SeriesResolutionRequest
    receipt: CaptureReceipt | None
    resolution: SeriesResolutionResult
    current_authority: CurrentAuthorityAssessment
    semantic_hash: str
    evidence_hash: str


def assess_sec_current_evidence(archive: SecArchive,
                                request: SeriesResolutionRequest) -> SecCurrentEvidenceAssessment:
    """Only original C3 requests and controlled archives, never supplied series.

    C3 owns request validation, stored receipt/object reads, extraction and all
    resolution. A second read checks exact receipt/object linkage; it does not
    duplicate the resolver or mint new capture authority. Unknown/corrupt input
    raises; offline, historical or unresolved evidence remains unavailable.
    """
    _require(type(archive) is SecArchive and type(request) is SeriesResolutionRequest)
    profile = get_source_route(SEC_COMPANYFACTS_LIVE_CURRENT_V1)
    _require((profile.verifier_id, profile.required_acquisition_contract,
              profile.required_capture_contract, profile.required_extraction_contract,
              profile.required_resolution_contract, profile.required_resolver_version) == (
        SEC_CURRENT_EVIDENCE_VERSION, LIVE_ACQUISITION_CONTRACT_VERSION,
        RECEIPT_SCHEMA_VERSION, EXTRACTION_VERSION, SERIES_CONTRACT_VERSION,
        SERIES_RESOLVER_VERSION), E.ROUTE_CONTRACT_MISMATCH)
    try:
        resolution = resolve_annual_diluted_eps(archive, request)
    except SeriesResolutionError as exc:
        category = {ResolutionReason.ARCHIVE_INTEGRITY_ERROR: E.ARCHIVE_INTEGRITY_FAILURE,
                    ResolutionReason.SOURCE_STRUCTURE_ERROR: E.SOURCE_STRUCTURE_FAILURE,
                    ResolutionReason.CIK_MISMATCH: E.ROUTE_CONTRACT_MISMATCH}.get(exc.reason, E.INVALID_CONTRACT)
        raise CurrentAuthorityError(category) from None
    _require(type(resolution) is SeriesResolutionResult)
    receipt, reasons, blockers, hashes, boundary = None, [], (), (), None
    series = resolution.series
    if request.mode is ResolutionMode.HISTORICAL_AS_OF:
        _require(resolution.status is ResolutionStatus.UNAVAILABLE and series is None
                 and resolution.source_authority is None and resolution.extraction is None
                 and resolution.reasons == (ResolutionReason.HISTORICAL_CUTOFF_UNSUPPORTED,),
                 E.ROUTE_CONTRACT_MISMATCH)
        reasons.append(R.HISTORICAL_MODE_UNSUPPORTED)
    else:
        try:
            receipt = archive.read_receipt(request.receipt_id)
            archive.read_object(receipt)
        except (ArchiveError, OSError):
            raise CurrentAuthorityError(E.ARCHIVE_INTEGRITY_FAILURE) from None
        capture = resolution.source_authority
        _require(capture is not None and resolution.extraction is not None, E.ROUTE_CONTRACT_MISMATCH)
        _require((receipt.cik, receipt.endpoint, receipt.receipt_id, receipt.schema_version) ==
                 (request.cik, endpoint_for(request.cik), request.receipt_id, profile.required_capture_contract),
                 E.ROUTE_CONTRACT_MISMATCH)
        _require((capture.receipt_id, capture.object_hash, capture.acquisition_contract) ==
                 (receipt.receipt_id, receipt.content_sha256, receipt.acquisition_contract_version),
                 E.ROUTE_CONTRACT_MISMATCH)
        _require(capture.captured_at == receipt.captured_at, E.AUTHORITY_BOUNDARY_MISMATCH)
        _require(resolution.extraction.receipt_id == receipt.receipt_id
                 and resolution.extraction.extraction_version == profile.required_extraction_contract,
                 E.ROUTE_CONTRACT_MISMATCH)
        live = receipt.acquisition_contract_version == profile.required_acquisition_contract
        expected = CaptureAuthority.LIVE_LOCAL_CAPTURE if live else CaptureAuthority.OFFLINE_SUPPLIED_CAPTURE
        _require(capture.authority is expected and (live or
                 receipt.acquisition_contract_version == ACQUISITION_CONTRACT_VERSION), E.ROUTE_CONTRACT_MISMATCH)
        if live:
            _require(receipt.source_locator == receipt.endpoint, E.ROUTE_CONTRACT_MISMATCH)
        else:
            reasons.append(R.UNSUPPORTED_ACQUISITION_AUTHORITY)
        hashes = (receipt.content_sha256,)
        blockers = tuple(b.value for b in capture.limitations)
        if resolution.status is ResolutionStatus.UNAVAILABLE:
            _require(series is None and bool(resolution.reasons), E.ROUTE_CONTRACT_MISMATCH)
            reasons.append(R.RESOLUTION_UNAVAILABLE)
        else:
            _require(resolution.status is ResolutionStatus.RESOLVED_ISSUER_EVIDENCE
                     and series is not None and not resolution.reasons, E.ROUTE_CONTRACT_MISMATCH)
            _require((series.contract_version, series.resolver_version, series.capture_authority,
                      series.receipt_ids, series.object_hashes, series.mode) == (
                profile.required_resolution_contract, profile.required_resolver_version, capture,
                (receipt.receipt_id,), hashes, ResolutionMode.CURRENT_AS_REPORTED), E.ROUTE_CONTRACT_MISMATCH)
            _require(series.authority_as_of == receipt.captured_at, E.AUTHORITY_BOUNDARY_MISMATCH)
            _require(series.downstream_admission_blockers == capture.limitations, E.ROUTE_CONTRACT_MISMATCH)
            blockers = tuple(b.value for b in series.downstream_admission_blockers)
            if live:
                boundary = series.authority_as_of
    # Bind the entire returned C3 result, including unresolved/excluded evidence.
    # This digest is a replay-envelope hash, never an original document hash.
    replay_hash = _hash("sec-current-replayed-evidence", (SEC_CURRENT_EVIDENCE_VERSION,
                        request, receipt, resolution))
    neutral = _build_assessment(route_id=profile.route_id, boundary=boundary,
        reasons=tuple(reasons), verified_properties=() if reasons else (
            P.SOURCE_ACQUISITION_PROVENANCE, P.CURRENT_OBSERVED_AVAILABILITY, P.CURRENT_SNAPSHOT_SCOPE),
        upstream_blockers=blockers, source_hashes=hashes,
        upstream_semantic_hash=series.semantic_hash if series else None,
        upstream_evidence_hash=series.evidence_hash if series else None,
        verified_evidence_hash=replay_hash)
    semantic_hash = _hash("sec-current-assessment-semantics", (SEC_CURRENT_EVIDENCE_VERSION,
        neutral.semantic_hash, request.cik, request.mode, request.latest_required_fiscal_end,
        request.expected_unit, request.period_policy, resolution.status, resolution.reasons))
    evidence_hash = _hash("sec-current-assessment-evidence", (SEC_CURRENT_EVIDENCE_VERSION,
        semantic_hash, neutral.evidence_hash, replay_hash))
    return SecCurrentEvidenceAssessment(SEC_CURRENT_EVIDENCE_VERSION, request, receipt,
                                        resolution, neutral, semantic_hash, evidence_hash)
