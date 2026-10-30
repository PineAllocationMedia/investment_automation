"""Portable PRIVATE M3 observation copy for a human-managed R1 archive.

SHA-256 is an UNKEYED accidental-change check: no authenticity, encryption,
storage, retention, broker verification or investment authority. Reuse the
existing strict M3 original observation validator; do not introduce new math.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import hmac
from typing import Any, Mapping

from .portfolio_observation import prepare_observation_ledger
from .private_case_integrity import _canonical, HEX_SHA256, ALGORITHM

SCHEMA = "PRIVATE_PORTFOLIO_SNAPSHOT_COPY_R1"
ENVELOPE_SCHEMA = "PRIVATE_PORTFOLIO_SNAPSHOT_ENVELOPE_R1"
INPUT_KEYS = frozenset({
    "analysis_id", "observed_on", "analysis_as_of", "captured_at",
    "source_type", "private_scope", "source_access_confirmed_by_caller",
    "account_scope", "currency", "scope_complete", "cash_base",
    "cash_visibility", "same_currency_basis_confirmed_by_caller", "positions",
})
RECORD_KEYS = frozenset({
    "schema_version", "status", "analysis_id", "analysis_as_of",
    "observed_on", "original_observation_inputs", "privacy",
    "source_authentication", "storage", "trading_authority",
})
ENVELOPE_KEYS = frozenset({
    "schema_version", "status", "algorithm", "private_snapshot_sha256",
    "private_snapshot", "confidentiality", "authenticity", "storage",
    "readiness", "project_invocation", "trading_authority",
})
PRIVATE_SOURCES = frozenset({
    "PRIVATE_USER_TABLE", "PRIVATE_SCREENSHOT_TRANSCRIPTION",
    "PRIVATE_EXPORT_TRANSCRIPTION", "AUTHORIZED_BLOSSOM_TRANSCRIPTION",
})


def _checked_observation(inputs: Any) -> dict[str, Any]:
    if (not isinstance(inputs, Mapping)
            or set(inputs) != INPUT_KEYS
            or inputs.get("private_scope") is not True
            or inputs.get("source_type") not in PRIVATE_SOURCES):
        raise ValueError("PRIVATE_PORTFOLIO_SNAPSHOT_INVALID")
    _canonical(inputs)  # Refuse non-JSON, nonfinite, or lossy object conversions.
    ledger = prepare_observation_ledger(**dict(inputs))
    if (ledger.get("private_scope") is not True
            or ledger.get("verification") !=
                "CALLER_ASSERTED_NOT_INDEPENDENTLY_AUTHENTICATED"):
        raise ValueError("PRIVATE_PORTFOLIO_SNAPSHOT_INVALID")
    return ledger


def seal_private_portfolio_snapshot(inputs: Mapping[str, Any]) -> dict[str, Any]:
    """Produce only an opt-in PRIVATE copy; never write it to disk or GitHub."""
    ledger = _checked_observation(inputs)
    record = {
        "schema_version": SCHEMA,
        "status": "CALLER_REPORTED_OBSERVATION_ONLY",
        "analysis_id": ledger["analysis_id"],
        "analysis_as_of": ledger["analysis_as_of"],
        "observed_on": ledger["observed_on"],
        "original_observation_inputs": deepcopy(dict(inputs)),
        "privacy": "PRIVATE_ONLY",
        "source_authentication": "NOT_PERFORMED",
        "storage": "NONE",
        "trading_authority": "NONE",
    }
    return {
        "schema_version": ENVELOPE_SCHEMA,
        "status": "PRIVATE_PORTFOLIO_COPY_NOT_STORED",
        "algorithm": ALGORITHM,
        "private_snapshot_sha256": hashlib.sha256(_canonical(record)).hexdigest(),
        "private_snapshot": record,
        "confidentiality": "NOT_PROVIDED_BY_CHECKSUM",
        "authenticity": "NOT_ESTABLISHED_UNKEYED_CHECKSUM",
        "storage": "NONE",
        "readiness": "NOT_EVALUATED",
        "project_invocation": "NONE",
        "trading_authority": "NONE",
    }


def verify_private_portfolio_snapshot(envelope: Mapping[str, Any]) -> dict[str, Any]:
    """Recover supplied snapshot only after checksum and M3 replay checks."""
    if (not isinstance(envelope, Mapping)
            or set(envelope) != ENVELOPE_KEYS
            or envelope.get("schema_version") != ENVELOPE_SCHEMA
            or envelope.get("status") != "PRIVATE_PORTFOLIO_COPY_NOT_STORED"
            or envelope.get("algorithm") != ALGORITHM
            or envelope.get("confidentiality") != "NOT_PROVIDED_BY_CHECKSUM"
            or envelope.get("authenticity") != "NOT_ESTABLISHED_UNKEYED_CHECKSUM"
            or envelope.get("storage") != "NONE"
            or envelope.get("readiness") != "NOT_EVALUATED"
            or envelope.get("project_invocation") != "NONE"
            or envelope.get("trading_authority") != "NONE"):
        raise ValueError("PRIVATE_PORTFOLIO_ENVELOPE_INVALID")
    digest = envelope.get("private_snapshot_sha256")
    record = envelope.get("private_snapshot")
    if (not isinstance(digest, str) or not HEX_SHA256.fullmatch(digest)
            or not isinstance(record, Mapping) or set(record) != RECORD_KEYS
            or record.get("schema_version") != SCHEMA
            or record.get("status") != "CALLER_REPORTED_OBSERVATION_ONLY"
            or record.get("privacy") != "PRIVATE_ONLY"
            or record.get("source_authentication") != "NOT_PERFORMED"
            or record.get("storage") != "NONE"
            or record.get("trading_authority") != "NONE"):
        raise ValueError("PRIVATE_PORTFOLIO_ENVELOPE_INVALID")
    if not hmac.compare_digest(
            hashlib.sha256(_canonical(record)).hexdigest(), digest):
        raise ValueError("PRIVATE_PORTFOLIO_SHA256_MISMATCH")
    original = record.get("original_observation_inputs")
    ledger = _checked_observation(original)
    if (record["analysis_id"] != ledger["analysis_id"]
            or record["analysis_as_of"] != ledger["analysis_as_of"]
            or record["observed_on"] != ledger["observed_on"]):
        raise ValueError("PRIVATE_PORTFOLIO_ENVELOPE_INVALID")
    return deepcopy(dict(original))
