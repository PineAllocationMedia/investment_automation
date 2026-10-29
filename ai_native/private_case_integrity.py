"""On-demand checksums for manually saved PRIVATE R1 research case copies.

SHA-256 detects accidental changes relative to a retained checksum, NOT
authenticity, confidentiality, approved storage, archival durability or
source verification. No disk writes, external services or automatic research.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import hmac
import json
import re
from typing import Any, Mapping

SCHEMA = "PRIVATE_CASE_TRANSFER_INTEGRITY_R1"
ALGORITHM = "SHA256_CANONICAL_JSON_R1"
HEX_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
ENVELOPE_KEYS = frozenset({
    "schema_version", "status", "algorithm",
    "private_case_sha256", "private_case",
    "confidentiality", "authenticity", "storage",
    "readiness", "project_invocation", "trading_authority",
})


def _canonical(record: Mapping[str, Any]) -> bytes:
    if not isinstance(record, Mapping):
        raise ValueError("PRIVATE_CASE_RECORD_INVALID")
    try:
        source = dict(record)
        encoded = json.dumps(source, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":"), allow_nan=False)
        roundtrip = json.loads(encoded)
    except (ValueError, TypeError, OverflowError, RecursionError) as exc:
        raise ValueError("PRIVATE_CASE_RECORD_INVALID") from exc
    if roundtrip != source or not isinstance(roundtrip, dict):
        raise ValueError("PRIVATE_CASE_RECORD_INVALID")
    return encoded.encode("utf-8")


def _case_scope(case: Mapping[str, Any]) -> None:
    # Only actual existing R1 private research-case *proposals* can be sealed.
    # This is a structural gate, not evidence or personal-record validation.
    if (case.get("schema_version") != "RESEARCH_HISTORY_R1"
            or case.get("record_type") != "PRIVATE_RESEARCH_CASE_PROPOSAL"
            or case.get("privacy_tier") != "PRIVATE_PENDING_REVIEW"
            or case.get("archive_status") != "PROPOSED_NOT_COMMITTED"
            or case.get("source_authentication") !=
            "NOT_PERFORMED_BY_MEMORY_HELPER"
            or case.get("cross_record_uniqueness") !=
            "NOT_CHECKED_NO_ARCHIVE_READ"
            or not isinstance(case.get("original_request"), Mapping)
            or not isinstance(case.get("original_ir_capsule"), Mapping)):
        raise ValueError("PRIVATE_CASE_RECORD_INVALID")


def seal_private_case(case: Mapping[str, Any]) -> dict[str, Any]:
    """Produce PRIVATE portable case + unkeyed accidental-change checksum."""
    _case_scope(case)
    digest = hashlib.sha256(_canonical(case)).hexdigest()
    return {
        "schema_version": SCHEMA,
        "status": "PRIVATE_CASE_COPY_NOT_STORED",
        "algorithm": ALGORITHM,
        "private_case_sha256": digest,
        "private_case": deepcopy(dict(case)),
        "confidentiality": "NOT_PROVIDED_BY_CHECKSUM",
        "authenticity": "NOT_ESTABLISHED_UNKEYED_CHECKSUM",
        "storage": "NONE",
        "readiness": "NOT_EVALUATED",
        "project_invocation": "NONE",
        "trading_authority": "NONE",
    }


def verify_private_case_envelope(envelope: Mapping[str, Any]) -> dict[str, Any]:
    """Recover a checked private case in memory; callers control its use."""
    if (not isinstance(envelope, Mapping)
            or set(envelope) != ENVELOPE_KEYS
            or envelope.get("schema_version") != SCHEMA
            or envelope.get("status") != "PRIVATE_CASE_COPY_NOT_STORED"
            or envelope.get("algorithm") != ALGORITHM
            or envelope.get("confidentiality") != "NOT_PROVIDED_BY_CHECKSUM"
            or envelope.get("authenticity") !=
            "NOT_ESTABLISHED_UNKEYED_CHECKSUM"
            or envelope.get("storage") != "NONE"
            or envelope.get("readiness") != "NOT_EVALUATED"
            or envelope.get("project_invocation") != "NONE"
            or envelope.get("trading_authority") != "NONE"):
        raise ValueError("PRIVATE_CASE_ENVELOPE_INVALID")
    digest = envelope.get("private_case_sha256")
    if not isinstance(digest, str) or not HEX_SHA256.fullmatch(digest):
        raise ValueError("PRIVATE_CASE_ENVELOPE_INVALID")
    record = envelope.get("private_case")
    if not isinstance(record, Mapping):
        raise ValueError("PRIVATE_CASE_ENVELOPE_INVALID")
    _case_scope(record)
    actual = hashlib.sha256(_canonical(record)).hexdigest()
    if not hmac.compare_digest(actual, digest):
        raise ValueError("PRIVATE_CASE_SHA256_MISMATCH")
    return deepcopy(dict(record))
