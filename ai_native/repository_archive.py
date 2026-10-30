"""Only plan opaque single-repository R1 case locators, never archive user data.

No GitHub write, encryption, source verification, privacy review or storage.
"""
from __future__ import annotations

from datetime import date
import hashlib
import hmac
import re
from typing import Any, Mapping

ID = re.compile(r"R1-[A-Z0-9]{12,24}\Z")
KINDS = frozenset({"ISSUER", "FUND", "STRATEGY", "PORTFOLIO",
                   "MULTIPORTFOLIO", "FOLLOWUP"})
MODES = frozenset({"high-cagr", "balanced", "family-office",
                   "rational-aggressive", "intelligent-dividend-harvester",
                   "modern-adaptive-browne", "EXPLORATORY"})
KEYS = frozenset({"archive_id", "case_kind", "as_of", "strategy_id",
                  "parent_archive_id"})


def _opaque(value: Any) -> str:
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise ValueError("ARCHIVE_OPAQUE_ID_REQUIRED")
    return value


def prepare_archive_locator(proposal: Mapping[str, Any]) -> dict[str, Any]:
    """Make only minimal path proposals; a human must independently review IDs."""
    if not isinstance(proposal, Mapping) or set(proposal) != KEYS:
        raise ValueError("ARCHIVE_METADATA_ONLY_REQUIRED")
    ident = _opaque(proposal["archive_id"])
    parent = proposal["parent_archive_id"]
    if parent is not None and _opaque(parent) == ident:
        raise ValueError("ARCHIVE_SELF_PARENT_INVALID")
    kind, strategy = proposal["case_kind"], proposal["strategy_id"]
    if (not isinstance(kind, str) or not isinstance(strategy, str)
            or kind not in KINDS or strategy not in MODES):
        raise ValueError("ARCHIVE_SCOPE_INVALID")
    as_of = proposal["as_of"]
    if not isinstance(as_of, str):
        raise ValueError("ARCHIVE_DATE_INVALID")
    try:
        day = date.fromisoformat(as_of)
    except ValueError as exc:
        raise ValueError("ARCHIVE_DATE_INVALID") from exc
    if day.isoformat() != as_of:
        raise ValueError("ARCHIVE_DATE_INVALID")
    return {
        "status": "ARCHIVE_NOT_SAVED",
        "archive_id_candidate": ident,
        "case_kind": kind,
        "strategy_id": strategy,
        "as_of": as_of,
        "parent_archive_id_candidate": parent,
        "research_path_candidate": f"archives/r1/research/{ident}/report.md",
        "manifest_path_candidate": f"archives/r1/cases/{ident}/manifest.json",
        "encrypted_path_candidate": f"archives/r1/protected/{ident}.age",
        "privacy_rights_review": "REQUIRED_BY_HUMAN",
        "encryption": "NOT_VERIFIED",
        "source_authentication": "NOT_PERFORMED",
        "repo_write": "NONE",
        "previous_case_read": "NOT_VERIFIED",
        "private_payload": "NONE",
        "repo_uniqueness": "NOT_CHECKED",
    }

# Git stores archive reports as SHA-1 objects in this repository. This local
# content comparison is NOT source authenticity, authorization, privacy review,
# evidence verification, or confirmation that the file is on merged V2.
MANIFEST_KEYS = frozenset({
    "schema_version", "archive_id", "case_kind", "as_of", "strategy_id",
    "report_path", "report_git_blob_sha", "record_class",
    "source_authentication", "review_claim",
})
GIT_BLOB_SHA = re.compile(r"[0-9a-f]{40}\Z")
RECORD_CLASSES = frozenset({"SYNTHETIC_EXAMPLE", "REVIEWED_RESEARCH"})


def verify_retrieved_research_report(
    manifest: Mapping[str, Any], report_text: str, *,
    retrieved_path: str, retrieved_blob_sha: str,
) -> dict[str, Any]:
    """Check a GitHub-fetched research report against its opaque manifest.

    A caller must *actually* fetch the manifest and report using authorized
    GitHub access, verify merged branch/commit and human rights/privacy review.
    This function does not store/archive, certify sources or return report text.
    Do NOT supply sensitive Tier-III plaintext.
    """
    if not isinstance(manifest, Mapping) or set(manifest) != MANIFEST_KEYS:
        raise ValueError("RESEARCH_ARCHIVE_MANIFEST_INVALID")
    if manifest["schema_version"] != "RESEARCH_ARCHIVE_MANIFEST_R1":
        raise ValueError("RESEARCH_ARCHIVE_MANIFEST_INVALID")
    planned = prepare_archive_locator({
        "archive_id": manifest["archive_id"],
        "case_kind": manifest["case_kind"],
        "as_of": manifest["as_of"],
        "strategy_id": manifest["strategy_id"],
        "parent_archive_id": None,
    })
    expected_path = planned["research_path_candidate"]
    if (manifest["report_path"] != expected_path
            or retrieved_path != expected_path):
        raise ValueError("RESEARCH_ARCHIVE_PATH_MISMATCH")
    if (not isinstance(manifest["record_class"], str)
            or manifest["record_class"] not in RECORD_CLASSES
            or manifest["source_authentication"] != "NOT_CERTIFIED_BY_ARCHIVE"
            or not isinstance(manifest["review_claim"], str)
            or manifest["review_claim"] not in {
                "SYNTHETIC_NOT_REVIEWED",
                "HUMAN_REVIEW_REPORTED_NOT_VERIFIED",
            }):
        raise ValueError("RESEARCH_ARCHIVE_AUTHORITY_INVALID")
    if (manifest["record_class"] == "SYNTHETIC_EXAMPLE") != (
            manifest["review_claim"] == "SYNTHETIC_NOT_REVIEWED"):
        raise ValueError("RESEARCH_ARCHIVE_AUTHORITY_INVALID")
    if (not isinstance(report_text, str) or not report_text
            or not isinstance(retrieved_blob_sha, str)
            or not GIT_BLOB_SHA.fullmatch(retrieved_blob_sha)
            or not isinstance(manifest["report_git_blob_sha"], str)
            or not GIT_BLOB_SHA.fullmatch(manifest["report_git_blob_sha"])):
        raise ValueError("RESEARCH_ARCHIVE_REPORT_INVALID")
    encoded = report_text.encode("utf-8")
    calculated = hashlib.sha1(
        b"blob " + str(len(encoded)).encode("ascii") + b"\x00" + encoded
    ).hexdigest()
    if (not hmac.compare_digest(calculated, retrieved_blob_sha)
            or not hmac.compare_digest(
                calculated, manifest["report_git_blob_sha"])):
        raise ValueError("RESEARCH_ARCHIVE_BLOB_MISMATCH")
    return {
        "status": "GITHUB_REPORT_CONTENT_CHECKED_NOT_SOURCE_VERIFIED",
        "archive_id": manifest["archive_id"],
        "report_path": expected_path,
        "blob_sha": calculated,
        "record_class": manifest["record_class"],
        "source_authentication": "NOT_PERFORMED",
        "rights_privacy_review": "NOT_VERIFIED_BY_CODE",
        "canonical_merge_and_read_access": "REQUIRES_EXTERNAL_GITHUB_EVIDENCE",
        "historical_baseline": (
            "SYNTHETIC_NOT_ELIGIBLE"
            if manifest["record_class"] == "SYNTHETIC_EXAMPLE"
            else "NOT_ESTABLISHED_BY_CODE"
        ),
        "repo_write": "NONE",
        "sensitive_record_access": "NONE",
    }
