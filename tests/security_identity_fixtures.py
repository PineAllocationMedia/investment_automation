"""Invented identity documents only; no real issuers, symbols or security IDs."""
from dataclasses import fields, is_dataclass, replace
from enum import Enum
import hashlib
import json
from pathlib import Path
import tempfile

from economic_facts import security_identity as i
from economic_facts.sec_archive import SecArchive
from economic_facts.sec_eps_series import resolve_annual_diluted_eps
from tests.sec_eps_series_fixtures import annual_rows, capture, request as series_request

ISSUER = "synthetic:issuer:fixture-one"
SECURITY = "synthetic:security:ordinary-one"
LISTING = "synthetic:listing:direct-one"
CAPTURED = "2026-03-02T12:00:00Z"
INTERVAL = i.EffectiveInterval("2020-01-01", "2027-12-31")
COMMON = i.CommonClass("fixture-common", "Fixture Ordinary Common", "Fixture Residual Common",
                       i.Participation.ORDINARY_RESIDUAL_COMMON)


def series_fixture(multiple_versions=False):
    rows = annual_rows()
    if multiple_versions:
        rows.append(dict(rows[-1], accn="0000000000-26-000002", filed="2026-02-01", fy=2025))
        rows.append(dict(rows[0]))
    return resolve_series_fixture(rows).series


def resolve_series_fixture(rows):
    with tempfile.TemporaryDirectory() as temporary:
        archive = SecArchive(Path(temporary).resolve() / "archive")
        receipt = capture(archive, rows)
        return resolve_annual_diluted_eps(archive, series_request(receipt))


def snapshot(series):
    return i.IdentitySnapshot(
        i.IssuerClaim(ISSUER, series.cik, "Fictional Identity Fixture", INTERVAL),
        (i.SecurityClaim(SECURITY, ISSUER, i.InstrumentType.ORDINARY_COMMON_EQUITY, COMMON, INTERVAL, ()),),
        i.CommonClassInventory(ISSUER, INTERVAL, i.InventoryCoverage.COMPLETE_WITHIN_INTERVAL, (COMMON,)),
        (i.ListingClaim(LISTING, SECURITY, "MIC:XNYS", "FICTIONAL_ONE", "USD",
                       i.QuoteUnit.MAJOR_CURRENCY_UNIT, i.ListingKind.DIRECT, INTERVAL),),
        i.ListingInventory(SECURITY, INTERVAL, i.InventoryCoverage.COMPLETE_WITHIN_INTERVAL, (LISTING,)),
        (),
        tuple(i.EPSApplicabilityClaim(series.semantic_hash, series.evidence_hash,
              i.EffectiveInterval(p.period_start, p.period_end), SECURITY, COMMON.class_id,
              p.version_ids, p.supporting_observation_ids) for p in series.periods),
        i.Continuity.UNCHANGED_SECURITY)


def payload(value):
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {f.name: payload(getattr(value, f.name)) for f in fields(value)}
    if type(value) is tuple:
        return [payload(v) for v in value]
    return value


def document(claims, **changes):
    raw = json.dumps({"schema_version": i.SYNTHETIC_EVIDENCE_VERSION, "claims": payload(claims)},
                     sort_keys=True, separators=(",", ":")).encode()
    source = i.SyntheticSourceEvidence(i.Authority.SYNTHETIC_TEST_ONLY, "synthetic:document:identity-one",
        i.SYNTHETIC_EVIDENCE_VERSION, "/claims", i.EXTRACTION_VERSION,
        "2026-03-02T10:00:00Z", "2026-03-02T11:00:00Z", CAPTURED,
        raw, hashlib.sha256(raw).hexdigest(), claims)
    return replace(source, **changes)


def bundle(*documents):
    return i.SyntheticIdentityEvidenceBundle(i.SYNTHETIC_EVIDENCE_VERSION, tuple(documents))


def request(series, **changes):
    value = i.SecurityIdentityRequest(i.IDENTITY_CONTRACT_VERSION, i.IdentityMode.CURRENT_SNAPSHOT,
                                      series.semantic_hash, series.evidence_hash, SECURITY, LISTING)
    return replace(value, **changes)


def rename(claims):
    previous = replace(claims.listings[0], interval=i.EffectiveInterval("2020-01-01", "2026-02-28"))
    current = replace(claims.listings[0], symbol="FICTIONAL_RENAMED",
                      interval=i.EffectiveInterval("2026-03-01", "2027-12-31"))
    continuity = i.SymbolContinuity(LISTING, SECURITY, previous.venue, previous.symbol,
                                    current.symbol, current.interval.start)
    return replace(claims, listings=(previous, current), symbol_continuities=(continuity,))
