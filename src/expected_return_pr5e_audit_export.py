"""Bounded PR5E identity/provenance export; offline, externally anchored verifier.

This module deliberately does not replay financial sources or analytical rules.
The verifier uses only the standard library and the versioned wire contract.
"""
from __future__ import annotations

from dataclasses import fields, is_dataclass
import hashlib
import json
import re

SCHEMA_VERSION = "2026-10-11-pr5e-audit-export-v1"
NATIVE_CONTRACT = "2026-09-30-pr5e-final-real-expected-return-admission-v1"
NATIVE_ADAPTER = "2026-09-30-pr5e-real-pr4b1-adapter-v1"
UPSTREAM_CONTRACT = "2026-09-29-pr5d2-real-expected-return-roots-v1"
UPSTREAM_ASSEMBLER = "2026-09-29-pr5d2-fresh-replay-bundle-v1"
COVERAGE = "PR5E_IDENTITY_STATUS_AND_PROVENANCE_PROJECTION_ONLY"
BOUNDARIES = (
    "NO_SOURCE_AUTHENTICATION_OR_REPLAY",
    "NO_FULL_NATIVE_RESULT_INTEGRITY_CLAIM",
    "NO_FINANCIAL_HISTORICAL_PIT_SHADOW_OR_PRODUCTION_AUTHORITY",
    "NO_RECOMMENDATION_ALLOCATION_EXECUTION_OR_V2_PROMOTION",
)
STATUSES = {"REAL_EXPECTED_RETURN_ADMITTED", "UNAVAILABLE", "UNSUPPORTED", "SOURCE_CONFLICT"}
REASONS = {
    "PR5D2_ROOTS_UNAVAILABLE", "PR5D2_ROOTS_UNSUPPORTED", "PR5D2_SOURCE_CONFLICT",
    "PR5D2_REPLAY_IDENTITY_MISMATCH", "PR5D2_SUCCESS_SHAPE_MISMATCH",
    "APPROVED_POLICY_IDENTITY_MISMATCH", "PRICE_BINARY64_REPRESENTATION_UNAVAILABLE",
    "EPS_BINARY64_REPRESENTATION_UNAVAILABLE", "PR4B1_CONSTRUCTOR_UNAVAILABLE",
}
NATIVE_LIMITATIONS = (
    "FINAL_ADMISSION_FOR_BOUNDED_SUPPORTED_ROUTE_ONLY", "DIAGNOSTIC_CHALLENGER_ONLY",
    "NO_PRODUCTION_OR_V1_AUTHORITY", "NO_HISTORICAL_AS_OF_OR_PIT_AUTHORITY",
    "PUBLICATION_TIME_UNKNOWN", "CAPTURE_BOUND_AVAILABILITY_ONLY", "PAYER_ROUTE_UNSUPPORTED",
    "ROUTE_LOCAL_SECURITY_IDENTITY_ONLY", "NO_UNIVERSAL_CORPORATE_ACTION_COMPLETENESS_CLAIM",
    "NO_RECOMMENDATION_ALLOCATION_OR_EXECUTION_AUTHORITY",
)
REFERENCE_FIELDS = frozenset({
    "receipt_id", "content_sha256", "source_object_hash", "table_sha256",
    "source_reference", "source_document_hash", "source_locator",
    "response_structure_locator", "filing_receipt_id", "accession",
    "document_filename", "captured_at", "filing_captured_at",
})
_HASH = re.compile(r"[0-9a-f]{64}")
MAX_BYTES = 4 * 1024 * 1024


class AuditExportError(ValueError):
    """Malformed, unsupported or integrity-invalid bounded audit artifact."""


def _require(condition, message):
    if not condition:
        raise AuditExportError(message)


def _hash(value):
    _require(type(value) is str and _HASH.fullmatch(value) is not None, "Invalid SHA-256")


def _canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def _digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, "Duplicate JSON key")
        result[key] = value
    return result


def _unsupported_number(value):
    raise AuditExportError("Numbers are outside this projection")


def _load(raw):
    _require(type(raw) is bytes and 0 < len(raw) <= MAX_BYTES, "Bounded exact bytes required")
    value = json.loads(raw.decode("ascii"), object_pairs_hook=_pairs,
                       parse_int=_unsupported_number, parse_float=_unsupported_number,
                       parse_constant=_unsupported_number)
    _require(_canonical(value) == raw, "Noncanonical serialization")
    return value


def _keys(value, names):
    _require(type(value) is dict and set(value) == set(names), "Invalid object fields")


def _strings(value):
    _require(type(value) is list and all(type(item) is str for item in value), "String array required")


def _validate_payload(p):
    _keys(p, ("contract_version", "adapter_version", "status", "reasons",
              "pr5d2_semantic_id", "pr5d2_evidence_id", "admission_semantic_id",
              "admission_evidence_id", "admitted_share_basis_identity", "analytical_as_of",
              "limitations", "upstream", "evidence_references"))
    _require(p["contract_version"] == NATIVE_CONTRACT and p["adapter_version"] == NATIVE_ADAPTER,
             "Unsupported native version")
    _require(type(p["status"]) is str and p["status"] in STATUSES, "Unsupported admission status")
    _strings(p["reasons"])
    _require(p["reasons"] == sorted(set(p["reasons"])) and set(p["reasons"]) <= REASONS,
             "Unsupported admission reasons")
    admitted = p["status"] == "REAL_EXPECTED_RETURN_ADMITTED"
    _require(bool(p["reasons"]) != admitted, "Admission status/reasons mismatch")
    allowed_reasons = {
        "REAL_EXPECTED_RETURN_ADMITTED": set(),
        "UNAVAILABLE": {"PR5D2_ROOTS_UNAVAILABLE", "PRICE_BINARY64_REPRESENTATION_UNAVAILABLE",
                        "EPS_BINARY64_REPRESENTATION_UNAVAILABLE", "PR4B1_CONSTRUCTOR_UNAVAILABLE"},
        "UNSUPPORTED": {"PR5D2_ROOTS_UNSUPPORTED"},
        "SOURCE_CONFLICT": {"PR5D2_SOURCE_CONFLICT", "PR5D2_REPLAY_IDENTITY_MISMATCH",
                            "PR5D2_SUCCESS_SHAPE_MISMATCH", "APPROVED_POLICY_IDENTITY_MISMATCH"},
    }
    _require(set(p["reasons"]) <= allowed_reasons[p["status"]], "Status/reason mismatch")
    _require(p["limitations"] == list(NATIVE_LIMITATIONS), "Native boundaries mismatch")
    for name in ("pr5d2_semantic_id", "pr5d2_evidence_id", "admission_semantic_id", "admission_evidence_id"):
        _hash(p[name])
    if p["admitted_share_basis_identity"] is not None:
        _hash(p["admitted_share_basis_identity"])
    as_of = p["analytical_as_of"]
    if as_of is not None:
        from datetime import datetime, timezone
        _require(type(as_of) is str, "Invalid analytical as-of")
        parsed = datetime.fromisoformat(as_of)
        _require(parsed.tzinfo is not None and parsed.astimezone(timezone.utc).isoformat() == as_of,
                 "Canonical UTC analytical as-of required")
    _require((as_of is None) == (p["admitted_share_basis_identity"] is None), "Basis/as-of mismatch")
    _require(not admitted or as_of is not None, "Missing admitted basis/as-of")
    u = p["upstream"]
    _keys(u, ("contract_version", "assembler_version", "semantic_id", "evidence_id",
              "upstream_semantic_ids", "upstream_evidence_ids"))
    _require(u["contract_version"] == UPSTREAM_CONTRACT and u["assembler_version"] == UPSTREAM_ASSEMBLER,
             "Unsupported upstream version")
    _require(u["semantic_id"] == p["pr5d2_semantic_id"] and u["evidence_id"] == p["pr5d2_evidence_id"],
             "Upstream identity mismatch")
    for name in ("upstream_semantic_ids", "upstream_evidence_ids"):
        _strings(u[name])
        for identity in u[name]:
            _hash(identity)
    refs = p["evidence_references"]
    _require(type(refs) is list, "Reference array required")
    paths = []
    for ref in refs:
        _keys(ref, ("path", "value"))
        _require(type(ref["path"]) is str and type(ref["value"]) is str, "Invalid reference")
        path = ref["path"]
        _require(re.fullmatch(r"(?:upstream_pr5d2|qualified_facts)(?:/[a-zA-Z_][a-zA-Z_0-9]*|/[0-9]+)+", path)
                 is not None and path.rsplit("/", 1)[-1] in REFERENCE_FIELDS, "Invalid reference path")
        if path.rsplit("/", 1)[-1] in {
            "content_sha256", "source_object_hash", "table_sha256", "source_document_hash",
        }:
            _hash(ref["value"])
        paths.append(path)
    _require(paths == sorted(set(paths)), "Duplicate or unordered references")


def _references(value, path):
    """Retain named string references, never source bytes or economic values."""
    if is_dataclass(value) and not isinstance(value, type):
        for field in fields(value):
            child = getattr(value, field.name)
            child_path = path + "/" + field.name
            if field.name in REFERENCE_FIELDS and type(child) is str:
                yield {"path": child_path, "value": child}
            else:
                yield from _references(child, child_path)
    elif type(value) is tuple:
        for index, child in enumerate(value):
            yield from _references(child, path + "/" + str(index))


def export_pr5e_audit(result) -> bytes:
    """Export one exact native result without source reads, writes or analysis."""
    from . import expected_return_pr5e_adapter as native
    from .expected_return_pr5d_bundle import PR5D2RealExpectedReturnRoots
    _require(type(result) is native.PR5EAdmissionResult, "Exact native PR5E result required")
    _require(type(result.status) is native.PR5EStatus and type(result.reasons) is tuple
             and all(type(reason) is native.PR5EReason for reason in result.reasons), "Native enums required")
    if result.status is native.PR5EStatus.REAL_EXPECTED_RETURN_ADMITTED:
        _require(type(result.qualified_facts) is native.assumptions.QualifiedFacts
                 and type(result.construction) is native.assumptions.ConstructionResult
                 and result.construction.status == "BUILT" and result.construction.diagnostic is not None,
                 "Missing admitted native content")
    u = result.upstream_pr5d2
    _require(type(u) is PR5D2RealExpectedReturnRoots, "Exact native upstream required")
    # Authenticate internal native identities using the existing native identity contract.
    rebuilt = native._result(result.status, result.reasons, u,
                             share_basis=result.admitted_share_basis_identity,
                             as_of=result.analytical_as_of, qualified_facts=result.qualified_facts,
                             construction=result.construction)
    _require(result == rebuilt, "Inconsistent native result")
    p = {name: getattr(result, name) for name in (
        "contract_version", "adapter_version", "pr5d2_semantic_id", "pr5d2_evidence_id",
        "admission_semantic_id", "admission_evidence_id", "admitted_share_basis_identity", "analytical_as_of")}
    p.update(status=result.status.value, reasons=[item.value for item in result.reasons],
             limitations=list(result.limitations), upstream={
                 "contract_version": u.contract_version, "assembler_version": u.assembler_version,
                 "semantic_id": u.semantic_id, "evidence_id": u.evidence_id,
                 "upstream_semantic_ids": list(u.upstream_semantic_ids),
                 "upstream_evidence_ids": list(u.upstream_evidence_ids)},
             evidence_references=sorted(
                 [*_references(u, "upstream_pr5d2"),
                  *_references(result.qualified_facts, "qualified_facts")], key=lambda item: item["path"]))
    _validate_payload(p)
    artifact = _canonical({"manifest": {
        "schema_version": SCHEMA_VERSION, "coverage": COVERAGE,
        "boundaries": list(BOUNDARIES), "payload_sha256": _digest(_canonical(p))}, "payload": p})
    # Apply exactly the same acceptance boundary to exporter output.
    verify_pr5e_audit(artifact, _digest(artifact))
    return artifact


def verify_pr5e_audit(artifact: bytes, expected_artifact_digest: str) -> str:
    """Return the anchored artifact digest, or raise; no source-authenticity claim.

    expected_artifact_digest MUST come from a separately trusted channel.
    """
    try:
        _hash(expected_artifact_digest)
        a = _load(artifact)
        _keys(a, ("manifest", "payload"))
        m = a["manifest"]
        _keys(m, ("schema_version", "coverage", "boundaries", "payload_sha256"))
        _require(m["schema_version"] == SCHEMA_VERSION and m["coverage"] == COVERAGE,
                 "Unsupported manifest version/coverage")
        _require(m["boundaries"] == list(BOUNDARIES), "Authority boundaries mismatch")
        _hash(m["payload_sha256"])
        _validate_payload(a["payload"])
        _require(_digest(_canonical(a["payload"])) == m["payload_sha256"], "Payload digest mismatch")
        digest = _digest(artifact)
        _require(digest == expected_artifact_digest, "External artifact digest mismatch")
        return digest
    except (ValueError, TypeError, KeyError, OverflowError, RecursionError, UnicodeError) as exc:
        raise AuditExportError("Audit artifact verification failed: " + str(exc)) from exc
