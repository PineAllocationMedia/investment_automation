"""Deterministic SEC Property-4 temporal source-evidence dossier.

This module organizes exact D2B, D2A, D3A, and D3B evidence.  It grants no
economic identity, completeness, continuity, CURRENT authority, or admission.
Source acceptance time, filing/report dates, and PAM capture time remain distinct;
none is publication time or first public availability.
"""
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import StrEnum
import re

from .sec_class_eps_claims import (
    ExtractionStatus as ClassEPSExtractionStatus,
    SecClassEPSExtractionAssessment,
    SecClassEPSExtractionRequest,
    UnsupportedSecClassEPSSource,
    extract_sec_class_eps_claims,
)
from .sec_filing_archive import FilingReceipt, SecFilingArchive, canonical_json, digest
from .sec_primary_document import (
    PrimaryDocumentProvenance,
    UnsupportedPrimaryDocumentSource,
    read_primary_document,
)
from .sec_registered_securities import (
    ExtractionStatus as RegisteredSecurityExtractionStatus,
    SecRegisteredSecurityExtractionAssessment,
    SecRegisteredSecurityExtractionRequest,
    UnsupportedRegisteredSecuritySource,
    extract_sec_registered_security_claims,
)
from .sec_submissions_archive import (
    MAX_REFERENCES,
    SecSubmissionsArchive,
    SubmissionsArchiveError,
    validate_receipt_id,
)
from .sec_submissions_inventory import (
    FilingOccurrence,
    SecSubmissionsInventoryAssessment,
    SecSubmissionsInventoryRequest,
    replay_sec_submissions_inventory,
)

DOSSIER_CONTRACT_VERSION = "2026-09-26-sec-property4-temporal-dossier-v1"
RELEVANT_FORMS = frozenset(("10-K", "10-K/A", "10-Q", "10-Q/A"))
MAX_FILING_RECEIPTS = 1_000
_RECEIPT_ID = re.compile(r"[0-9a-f]{64}")


class SecProperty4TemporalDossierRequestError(ValueError):
    """Invalid explicit evidence selection; distinct from archive corruption."""


class DossierStatus(StrEnum):
    CAPTURED_TEMPORAL_EVIDENCE_DOSSIER = "CAPTURED_TEMPORAL_EVIDENCE_DOSSIER"
    INCOMPLETE_TEMPORAL_EVIDENCE_DOSSIER = "INCOMPLETE_TEMPORAL_EVIDENCE_DOSSIER"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"
    NO_RELEVANT_PERIODIC_FILINGS = "NO_RELEVANT_PERIODIC_FILINGS"


class DossierIssue(StrEnum):
    D2B_RELEVANT_INVENTORY_CONFLICT = "D2B_RELEVANT_INVENTORY_CONFLICT"
    D2B_RANGE_CONFLICT = "D2B_RANGE_CONFLICT"
    D2B_REFERENCE_CLOSURE_INCOMPLETE = "D2B_REFERENCE_CLOSURE_INCOMPLETE"
    MISSING_D2A_CAPTURE = "MISSING_D2A_CAPTURE"
    D2B_D2A_FORM_MISMATCH = "D2B_D2A_FORM_MISMATCH"
    D2B_D2A_PRIMARY_DOCUMENT_MISMATCH = "D2B_D2A_PRIMARY_DOCUMENT_MISMATCH"
    DIFFERING_D2A_CAPTURE_BYTES = "DIFFERING_D2A_CAPTURE_BYTES"
    D3A_UNSUPPORTED_SOURCE = "D3A_UNSUPPORTED_SOURCE"
    D3A_INCOMPLETE = "D3A_INCOMPLETE"
    D3A_SOURCE_CONFLICT = "D3A_SOURCE_CONFLICT"
    D3A_NO_SUPPORTED_CLAIMS = "D3A_NO_SUPPORTED_CLAIMS"
    D3B_UNSUPPORTED_SOURCE = "D3B_UNSUPPORTED_SOURCE"
    D3B_INCOMPLETE = "D3B_INCOMPLETE"
    D3B_SOURCE_CONFLICT = "D3B_SOURCE_CONFLICT"
    D3B_NO_SUPPORTED_CLAIMS = "D3B_NO_SUPPORTED_CLAIMS"


_CONFLICT_ISSUES = frozenset((
    DossierIssue.D2B_RELEVANT_INVENTORY_CONFLICT,
    DossierIssue.D2B_RANGE_CONFLICT,
    DossierIssue.D2B_D2A_FORM_MISMATCH,
    DossierIssue.D2B_D2A_PRIMARY_DOCUMENT_MISMATCH,
    DossierIssue.DIFFERING_D2A_CAPTURE_BYTES,
    DossierIssue.D3A_SOURCE_CONFLICT,
    DossierIssue.D3B_SOURCE_CONFLICT,
))


def _identity(domain, value):
    return digest(("pam:sec-property4-temporal-dossier:" + domain + ":v1\0").encode("ascii")
                  + canonical_json(value))


def _validate_selector(value):
    if type(value) is not str or _RECEIPT_ID.fullmatch(value) is None:
        raise SecProperty4TemporalDossierRequestError("Exact receipt ID required")


@dataclass(frozen=True, slots=True)
class SecProperty4TemporalDossierRequest:
    parent_submissions_receipt_id: str
    child_submissions_receipt_ids: tuple[str, ...] = ()
    filing_receipt_ids: tuple[str, ...] = ()

    def __post_init__(self):
        try:
            validate_receipt_id(self.parent_submissions_receipt_id)
        except SubmissionsArchiveError:
            raise SecProperty4TemporalDossierRequestError("Exact parent receipt ID required") from None
        for values, limit, label in (
            (self.child_submissions_receipt_ids, MAX_REFERENCES, "child"),
            (self.filing_receipt_ids, MAX_FILING_RECEIPTS, "filing"),
        ):
            if type(values) is not tuple or len(values) > limit:
                raise SecProperty4TemporalDossierRequestError(
                    "Bounded tuple of " + label + " receipt IDs required")
            for value in values:
                _validate_selector(value)
            if len(set(values)) != len(values):
                raise SecProperty4TemporalDossierRequestError(
                    "Duplicate " + label + " receipt ID")


@dataclass(frozen=True, slots=True)
class FilingCaptureEvidence:
    """One exact D2A capture and its independently replayed extraction rails."""

    receipt: FilingReceipt
    primary_document: PrimaryDocumentProvenance | None
    registered_security_claims: SecRegisteredSecurityExtractionAssessment | None
    class_eps_claims: SecClassEPSExtractionAssessment | None
    issues: tuple[DossierIssue, ...]

    @property
    def semantic_id(self):
        return _identity("filing-capture-semantics", {
            "d3a": (None if self.registered_security_claims is None
                    else self.registered_security_claims.semantic_id),
            "d3b": None if self.class_eps_claims is None else self.class_eps_claims.semantic_id,
            "primary": (None if self.primary_document is None else
                        (self.primary_document.cik, self.primary_document.accession,
                         self.primary_document.form, self.primary_document.filename)),
            "issues": self.issues,
        })

    @property
    def evidence_id(self):
        return _identity("filing-capture-evidence", {
            "semantic_id": self.semantic_id,
            "receipt": asdict(self.receipt),
            "receipt_id": self.receipt.receipt_id,
            "primary": None if self.primary_document is None else asdict(self.primary_document),
            "d3a": (None if self.registered_security_claims is None
                    else self.registered_security_claims.evidence_id),
            "d3b": None if self.class_eps_claims is None else self.class_eps_claims.evidence_id,
        })


@dataclass(frozen=True, slots=True)
class TemporalFilingEvidence:
    """One accession-level bundle; source-local scopes remain filing-local."""

    accession: str
    inventory_occurrences: tuple[FilingOccurrence, ...]
    captures: tuple[FilingCaptureEvidence, ...]
    issues: tuple[DossierIssue, ...]

    @property
    def semantic_id(self):
        # Equal-byte recaptures collapse semantically while every receipt remains
        # visible in evidence identity. D2B duplicate multiplicity is preserved.
        return _identity("temporal-filing-semantics", {
            "accession": self.accession,
            "occurrences": [row.semantic_id for row in self.inventory_occurrences],
            "capture_semantics": sorted({capture.semantic_id for capture in self.captures}),
            "issues": self.issues,
        })

    @property
    def evidence_id(self):
        return _identity("temporal-filing-evidence", {
            "semantic_id": self.semantic_id,
            "occurrences": [row.occurrence_id for row in self.inventory_occurrences],
            "captures": [capture.evidence_id for capture in self.captures],
        })


@dataclass(frozen=True, slots=True)
class SecProperty4TemporalDossier:
    contract_version: str
    status: DossierStatus
    source_cik: str
    inventory: SecSubmissionsInventoryAssessment
    filings: tuple[TemporalFilingEvidence, ...]
    issues: tuple[DossierIssue, ...]

    @property
    def semantic_id(self):
        return _identity("dossier-semantics", {
            "contract": self.contract_version,
            "status": self.status,
            "source_cik": self.source_cik,
            "inventory_semantic_id": self.inventory.semantic_id,
            "filings": [filing.semantic_id for filing in self.filings],
            "issues": self.issues,
        })

    @property
    def evidence_id(self):
        return _identity("dossier-evidence", {
            "semantic_id": self.semantic_id,
            "inventory_evidence_id": self.inventory.evidence_id,
            "filings": [filing.evidence_id for filing in self.filings],
        })


def _occurrence_key(occurrence):
    fields = dict(occurrence.fields)
    acceptance = datetime.fromisoformat(fields["acceptanceDateTime"].replace("Z", "+00:00"))
    return (acceptance, fields["filingDate"], fields["accessionNumber"],
            occurrence.occurrence_id)


def _assessment_document(capture):
    documents = ([capture.primary_document] if capture.primary_document is not None else [])
    documents.extend(assessment.primary_document for assessment in
                 (capture.registered_security_claims, capture.class_eps_claims)
                 if assessment is not None)
    if documents and any(document != documents[0] for document in documents[1:]):
        raise RuntimeError("D3A/D3B primary-document replay disagreement")
    return documents[0] if documents else None


def _extract_capture(filing_archive, receipt):
    issues = set()
    try:
        primary_document, _ = read_primary_document(
            filing_archive.read_object(receipt), receipt, supported_forms=RELEVANT_FORMS)
    except UnsupportedPrimaryDocumentSource:
        primary_document = None
    try:
        d3a = extract_sec_registered_security_claims(
            filing_archive, SecRegisteredSecurityExtractionRequest(receipt.receipt_id))
    except UnsupportedRegisteredSecuritySource:
        d3a = None
        issues.add(DossierIssue.D3A_UNSUPPORTED_SOURCE)
    if d3a is not None:
        issues.add({
            RegisteredSecurityExtractionStatus.INCOMPLETE_REGISTERED_SECURITY_CLAIMS:
                DossierIssue.D3A_INCOMPLETE,
            RegisteredSecurityExtractionStatus.SOURCE_CONFLICT:
                DossierIssue.D3A_SOURCE_CONFLICT,
            RegisteredSecurityExtractionStatus.NO_SUPPORTED_REGISTERED_SECURITY_CLAIMS:
                DossierIssue.D3A_NO_SUPPORTED_CLAIMS,
        }.get(d3a.status))
    try:
        d3b = extract_sec_class_eps_claims(
            filing_archive, SecClassEPSExtractionRequest(receipt.receipt_id))
    except UnsupportedSecClassEPSSource:
        d3b = None
        issues.add(DossierIssue.D3B_UNSUPPORTED_SOURCE)
    if d3b is not None:
        issues.add({
            ClassEPSExtractionStatus.INCOMPLETE_CLASS_EPS_SOURCE_CLAIMS:
                DossierIssue.D3B_INCOMPLETE,
            ClassEPSExtractionStatus.SOURCE_CONFLICT:
                DossierIssue.D3B_SOURCE_CONFLICT,
            ClassEPSExtractionStatus.NO_SUPPORTED_CLASS_EPS_SOURCE_CLAIMS:
                DossierIssue.D3B_NO_SUPPORTED_CLAIMS,
        }.get(d3b.status))
    issues.discard(None)
    return FilingCaptureEvidence(receipt, primary_document, d3a, d3b, tuple(sorted(issues)))


def _entry(accession, occurrences, captures, inventory_conflict):
    issues = {issue for capture in captures for issue in capture.issues}
    if inventory_conflict:
        issues.add(DossierIssue.D2B_RELEVANT_INVENTORY_CONFLICT)
    if not captures:
        issues.add(DossierIssue.MISSING_D2A_CAPTURE)
    if len({capture.receipt.content_sha256 for capture in captures}) > 1:
        issues.add(DossierIssue.DIFFERING_D2A_CAPTURE_BYTES)
    for capture in captures:
        document = _assessment_document(capture)
        if document is None:
            continue
        for occurrence in occurrences:
            fields = dict(occurrence.fields)
            if fields["form"] != document.form:
                issues.add(DossierIssue.D2B_D2A_FORM_MISMATCH)
            if fields["primaryDocument"] != document.filename:
                issues.add(DossierIssue.D2B_D2A_PRIMARY_DOCUMENT_MISMATCH)
    return TemporalFilingEvidence(
        accession,
        tuple(sorted(occurrences, key=_occurrence_key)),
        tuple(sorted(captures, key=lambda capture: capture.receipt.receipt_id)),
        tuple(sorted(issues)),
    )


def build_sec_property4_temporal_dossier(
    submissions_archive: SecSubmissionsArchive,
    filing_archive: SecFilingArchive,
    request: SecProperty4TemporalDossierRequest,
) -> SecProperty4TemporalDossier:
    """Replay exact selected evidence without acquisition, discovery, or clocks.

    CAPTURED means only that the explicitly replayed D2B reference set's relevant
    periodic occurrences have nonconflicting selected capture/extraction evidence.
    It is not complete filing history, continuity, coverage through D1 T, or
    economic admission.
    """
    if (type(submissions_archive) is not SecSubmissionsArchive
            or type(filing_archive) is not SecFilingArchive
            or type(request) is not SecProperty4TemporalDossierRequest):
        raise SecProperty4TemporalDossierRequestError("Exact typed archives/request required")
    inventory = replay_sec_submissions_inventory(
        submissions_archive,
        SecSubmissionsInventoryRequest(
            request.parent_submissions_receipt_id,
            tuple(sorted(request.child_submissions_receipt_ids)),
        ),
    )
    by_accession = {}
    for occurrence in inventory.occurrences:
        accession = dict(occurrence.fields)["accessionNumber"]
        by_accession.setdefault(accession, []).append(occurrence)
    relevant_accessions = {
        accession for accession, occurrences in by_accession.items()
        if any(dict(occurrence.fields)["form"] in RELEVANT_FORMS for occurrence in occurrences)
    }
    selected = {accession: [] for accession in relevant_accessions}
    for receipt_id in sorted(request.filing_receipt_ids):
        receipt = filing_archive.read_receipt(receipt_id)
        if receipt.cik != inventory.parent.cik:
            raise SecProperty4TemporalDossierRequestError("Filing receipt CIK does not match parent")
        if receipt.accession not in by_accession:
            raise SecProperty4TemporalDossierRequestError("Filing receipt accession absent from inventory")
        if receipt.accession not in relevant_accessions:
            raise SecProperty4TemporalDossierRequestError("Filing receipt is outside relevant form universe")
        selected[receipt.accession].append(_extract_capture(filing_archive, receipt))
    entries = [
        _entry(accession, by_accession[accession], selected[accession],
               accession in inventory.conflicting_accessions)
        for accession in relevant_accessions
    ]
    entries.sort(key=lambda entry: (
        tuple(_occurrence_key(occurrence) for occurrence in entry.inventory_occurrences),
        entry.accession,
    ))
    issues = {issue for entry in entries for issue in entry.issues}
    if inventory.range_conflicts:
        issues.add(DossierIssue.D2B_RANGE_CONFLICT)
    if inventory.missing_history_filenames:
        issues.add(DossierIssue.D2B_REFERENCE_CLOSURE_INCOMPLETE)
    ordered_issues = tuple(sorted(issues))
    if issues & _CONFLICT_ISSUES:
        status = DossierStatus.SOURCE_CONFLICT
    elif issues:
        status = DossierStatus.INCOMPLETE_TEMPORAL_EVIDENCE_DOSSIER
    elif not entries:
        status = DossierStatus.NO_RELEVANT_PERIODIC_FILINGS
    else:
        status = DossierStatus.CAPTURED_TEMPORAL_EVIDENCE_DOSSIER
    return SecProperty4TemporalDossier(
        DOSSIER_CONTRACT_VERSION, status, inventory.parent.cik, inventory,
        tuple(entries), ordered_issues,
    )
