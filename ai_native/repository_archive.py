"""Only plan opaque single-repository R1 case locators, never archive user data.

No GitHub write, encryption, source verification, privacy review or storage.
"""
from __future__ import annotations

from datetime import date
import re
from typing import Any, Mapping

ID = re.compile(r"R1-[A-Z0-9]{12,24}\\Z")
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
    if kind not in KINDS or strategy not in MODES:
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
