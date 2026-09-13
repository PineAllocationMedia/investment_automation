"""Fictional share denominations and notices; no external source acquisition."""
from dataclasses import replace
import hashlib
import json

from economic_facts import share_basis as s
from economic_facts import security_identity as i
from tests import security_identity_fixtures as identities
from tests.sec_eps_series_fixtures import annual_rows

SECURITY = identities.SECURITY
CLASS = identities.COMMON.class_id
BASELINE = "synthetic:basis:baseline"
CAPTURED = identities.CAPTURED


def series_fixture():
    rows = annual_rows()
    # Exercise every cross-form and duplicate occurrence at every period position.
    for n, row in enumerate(tuple(rows)):
        rows.append(dict(row))
        for k, form in enumerate(("8-K", "10-Q", "10-Q/A"), start=2):
            rows.append(dict(row, form=form, fp="Q4", accn=f"9999999999-{21+n:02d}-{k:06d}"))
    return identities.resolve_series_fixture(rows).series


def identity_fixture(series, captured_at=CAPTURED, claims=None):
    req = identities.request(series)
    evidence = identities.bundle(identities.document(
        identities.snapshot(series) if claims is None else claims, captured_at=captured_at))
    witness = s.IdentityQualificationWitness(req, evidence)
    return i.qualify_security_identity(series, req, evidence), witness


def request(series, identity, **changes):
    return replace(s.ShareBasisRequest(s.SHARE_BASIS_CONTRACT_VERSION, s.ShareBasisMode.CURRENT_SNAPSHOT,
        series.semantic_hash, series.evidence_hash, identity.semantic_hash, identity.evidence_hash), **changes)


def split(key="one", new=2, old=1, effective_at="2025-03-15", **changes):
    return replace(s.CorporateActionEvidence(f"synthetic:notice:{key}", f"synthetic:event:{key}",
        SECURITY, CLASS, s.CorporateActionKind.FORWARD_SPLIT if new > old else s.CorporateActionKind.REVERSE_SPLIT,
        s.EventLifecycle.EFFECTIVE, "2026-02-27T12:00:00Z", None, effective_at, s.Implementation.CONFIRMED,
        s.SplitRatio(new, old, s.RatioOrientation.NEW_UNITS_PER_OLD_UNITS), f"synthetic:basis:{key}",
        s.SecurityContinuation.SAME_SECURITY_AND_CLASS, s.ActionStructure.PURE_SPLIT,
        s.FractionalTreatment.NO_FRACTIONAL_SETTLEMENT, ()), **changes)


def references(series):
    return tuple(s.ObservationReference(p.period_start, p.period_end, v.semantic_id, o)
                 for p in series.periods for v in p.filing_versions for o in v.observation_ids)


def snapshot(series, identity, events=(), basis=None):
    target = basis or (events[-1].successor_basis_id if events else BASELINE)
    treatments = tuple(s.EventTreatmentEvidence(e.event_id, s.ReportedEventTreatment.INCORPORATED)
                       for e in events if e.lifecycle is s.EventLifecycle.EFFECTIVE)
    return s.ShareBasisSnapshot(series.semantic_hash, series.evidence_hash, identity.semantic_hash,
        identity.evidence_hash, s.BaselineBasisAnchor(BASELINE, SECURITY, CLASS, "2019-01-01"),
        s.CorporateActionCoverage(SECURITY, CLASS, "2019-01-01", "2026-03-02", s.CoverageStatus.COMPLETE,
                                 tuple(s.CorporateActionKind), (), tuple(sorted({e.event_id for e in events}))),
        events, tuple(s.ReportedEPSBasisEvidence((r,), SECURITY, CLASS, target, treatments)
                      for r in references(series)))


def document(claims, **changes):
    metadata = dict(authority=s.Authority.SYNTHETIC_TEST_ONLY, source_reference="synthetic:document:basis-one",
        source_version=s.SYNTHETIC_EVIDENCE_VERSION, source_locator="/claims", extraction_version=s.EXTRACTION_VERSION,
        published_at="2026-03-02T10:00:00Z", available_at="2026-03-02T11:00:00Z", captured_at=CAPTURED, claims=claims)
    metadata.update(changes)
    raw = json.dumps({k: identities.payload(v) for k, v in metadata.items()},
                    sort_keys=True, separators=(",", ":")).encode()
    return s.SyntheticSourceEvidence(**metadata, source_bytes=raw, content_sha256=hashlib.sha256(raw).hexdigest())


def bundle(witness, *documents):
    return s.SyntheticShareBasisEvidenceBundle(s.SYNTHETIC_EVIDENCE_VERSION, witness, tuple(documents))
