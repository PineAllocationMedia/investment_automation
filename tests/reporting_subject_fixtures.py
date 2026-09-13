"""Fictional accounting subjects over the existing complete cross-form fixtures."""
from dataclasses import replace
import hashlib
from pathlib import Path
import tempfile

from economic_facts import reporting_subject as r
from economic_facts import share_basis as s
from economic_facts.sec_archive import SecArchive
from economic_facts.sec_eps_series import resolve_annual_diluted_eps
from tests import share_basis_fixtures as basis
from tests import security_identity_fixtures as identities
from tests.sec_eps_series_fixtures import annual_rows, request as series_request
from tests.sec_filing_fixtures import CIK, T2, raw, source

SUBJECT = "synthetic:subject:continuing-one"
SUCCESSOR = "synthetic:subject:successor-one"


def upstream(series=None, *, identity_claims=None, basis_documents=None):
    series = basis.series_fixture() if series is None else series
    identity, witness = basis.identity_fixture(series, claims=identity_claims)
    request = basis.request(series, identity)
    documents = ((basis.document(basis.snapshot(series, identity)),)
                 if basis_documents is None else basis_documents)
    evidence = basis.bundle(witness, *documents)
    qualification = s.qualify_share_basis(series, identity, request, evidence)
    return series, identity, qualification, r.ShareBasisQualificationWitness(request, evidence)


def signed_series(value, *, live=False):
    rows = annual_rows()
    for row in rows:
        row["val"] = 777
    # Literal JSON numbers preserve Decimal spelling, including negative zero.
    content = raw(source(rows)).replace(b'"val":777', b'"val":' + str(value).encode("ascii"))
    with tempfile.TemporaryDirectory() as temporary:
        archive = SecArchive(Path(temporary).resolve() / "archive")
        receipt = (archive._capture_live(content, cik=CIK, captured_at=T2) if live else
            archive.capture(content, cik=CIK, captured_at=T2, source_locator="fixture:subject"))
        return resolve_annual_diluted_eps(archive, series_request(receipt)).series


def request(series, identity, share_basis, **changes):
    return replace(r.ReportingSubjectRequest(r.REPORTING_SUBJECT_CONTRACT_VERSION,
        r.ReportingSubjectMode.CURRENT_SNAPSHOT, series.semantic_hash, series.evidence_hash,
        identity.semantic_hash, identity.evidence_hash, share_basis.semantic_hash, share_basis.evidence_hash), **changes)


def snapshot(series):
    return r.ReportingSubjectSnapshot(series.semantic_hash, series.evidence_hash,
        r.CoverageStatus.COMPLETE, (r.ReportingSubjectSpan(SUBJECT, identities.ISSUER,
        "2020-01-01", "2026-03-02", basis.references(series)),))


def document(claims, **changes):
    metadata = dict(authority=r.Authority.SYNTHETIC_TEST_ONLY,
        source_reference="synthetic:document:subject-one", source_version=r.SYNTHETIC_EVIDENCE_VERSION,
        source_locator="/claims", extraction_version=r.EXTRACTION_VERSION,
        published_at="2026-03-02T10:00:00Z", available_at="2026-03-02T11:00:00Z",
        captured_at=basis.CAPTURED, claims=claims)
    metadata.update(changes)
    raw = r._json(metadata)
    return r.SyntheticReportingSubjectEvidence(**metadata, source_bytes=raw,
        content_sha256=hashlib.sha256(raw).hexdigest())


def bundle(witness, *documents):
    return r.SyntheticReportingSubjectEvidenceBundle(r.SYNTHETIC_EVIDENCE_VERSION, witness, tuple(documents))


def transition(series, on="2022-01-01", previous_end="2021-12-31"):
    original = snapshot(series)
    before = tuple(ref for ref in basis.references(series) if ref.period_end < on)
    after = tuple(ref for ref in basis.references(series) if ref.period_start >= on)
    return replace(original, spans=(
        replace(original.spans[0], effective_end=previous_end, references=before),
        replace(original.spans[0], subject_anchor=SUCCESSOR, effective_start=on, references=after)))
