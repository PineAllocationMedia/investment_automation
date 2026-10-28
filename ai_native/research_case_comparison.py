"""Compare two *supplied* private research cases without claiming economic change.

No source retrieval, historical archive access, scheduling, writes or investment action.
Text/status comparisons are structural review prompts, never source verification.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Mapping
import re

_IDENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,79}\Z")
_STATUSES = frozenset({"VERIFIED", "INDICATIVE", "CONFLICTED", "MISSING"})


def _id(raw: Any, name: str) -> str:
    if not isinstance(raw, str) or not _IDENT.fullmatch(raw):
        raise ValueError(f"{name}: opaque identifier required")
    return raw


def _date(raw: Any, name: str) -> str:
    if not isinstance(raw, str):
        raise ValueError(f"{name}: ISO date required")
    try:
        d = date.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(f"{name}: invalid ISO date") from exc
    if d.isoformat() != raw:
        raise ValueError(f"{name}: canonical ISO date required")
    return raw


def _facts(raw: Any, name: str) -> dict[str, Mapping[str, Any]]:
    if not isinstance(raw, list):
        raise ValueError(f"{name}: fact list required")
    found = {}
    for i, fact in enumerate(raw):
        if not isinstance(fact, Mapping):
            raise ValueError(f"{name}[{i}]: mapping required")
        ident = _id(fact.get("id"), f"{name}[{i}].id")
        if ident in found:
            raise ValueError("DUPLICATE_FACT_ID")
        if fact.get("status") not in _STATUSES:
            raise ValueError("UNSUPPORTED_EVIDENCE_STATUS")
        if not isinstance(fact.get("claim"), str) or not fact["claim"].strip():
            raise ValueError("FACT_CLAIM_REQUIRED")
        found[ident] = fact
    return found


def compare_supplied_cases(*, request: Mapping[str, Any], ir_capsule: Mapping[str, Any],
                           prior_case: Mapping[str, Any] | None,
                           subject_id: str, fact_links: list[Mapping[str, str]]) -> dict[str, Any]:
    """Return a private, reviewer-only comparison of explicit fact-ID pairings.

    The caller asserts related economic concepts; this function does not certify
    metric equivalence, periods, values, source rights or that any thesis changed.
    """
    if not isinstance(request, Mapping) or not isinstance(ir_capsule, Mapping):
        raise ValueError("REQUEST_AND_IR_REQUIRED")
    if request.get("kind") != "FOLLOWUP":
        raise ValueError("CEO_REQUESTED_FOLLOWUP_REQUIRED")
    subject = _id(subject_id, "subject_id")
    if request.get("subject_id") != subject:
        raise ValueError("CURRENT_SUBJECT_MISMATCH_OR_MISSING")
    current_id = _id(request.get("analysis_id"), "analysis_id")
    if _id(ir_capsule.get("analysis_id"), "ir.analysis_id") != current_id:
        raise ValueError("IR_ANALYSIS_ID_MISMATCH")
    current_as_of = _date(request.get("as_of"), "request.as_of")
    if _date(ir_capsule.get("research_as_of"), "ir.research_as_of") > current_as_of:
        raise ValueError("CURRENT_RESEARCH_AFTER_CUTOFF")
    if not isinstance(fact_links, list):
        raise ValueError("FACT_LINKS_LIST_REQUIRED")
    current_facts = _facts(ir_capsule.get("facts"), "current.facts")
    if prior_case is None:
        if fact_links:
            raise ValueError("FACT_LINKS_WITHOUT_BASELINE")
        return {"status": "BASELINE_NOT_AVAILABLE", "subject_id_private": subject,
                "review_items_private": [], "source_authentication": "NOT_PERFORMED",
                "privacy": "PRIVATE_ONLY", "economic_change_status": "NOT_EVALUATED"}
    if not isinstance(prior_case, Mapping) or prior_case.get("schema_version") != "RESEARCH_HISTORY_R1":
        raise ValueError("PRIOR_PRIVATE_CASE_SCHEMA_REQUIRED")
    prior_req = prior_case.get("original_request")
    prior_ir = prior_case.get("original_ir_capsule")
    if not isinstance(prior_req, Mapping) or not isinstance(prior_ir, Mapping):
        raise ValueError("PRIOR_ORIGINAL_PACKETS_REQUIRED")
    if prior_req.get("subject_id") != subject:
        raise ValueError("PRIOR_SUBJECT_MISMATCH_OR_MISSING")
    prior_id = _id(prior_case.get("analysis_id"), "prior.analysis_id")
    if prior_id == current_id:
        raise ValueError("SAME_ANALYSIS_CANNOT_BE_PRIOR")
    if (prior_req.get("analysis_id") != prior_id
            or prior_ir.get("analysis_id") != prior_id):
        raise ValueError("PRIOR_ANALYSIS_ID_INCONSISTENT")
    if request.get("prior_analysis_id") not in (None, prior_id):
        raise ValueError("REQUESTED_PRIOR_ANALYSIS_ID_MISMATCH")
    if _date(prior_req.get("as_of"), "prior.request.as_of") != _date(prior_case.get("as_of"), "prior.as_of"):
        raise ValueError("PRIOR_DATE_INCONSISTENT")
    prior_recorded = _date(prior_case.get("recorded_at"), "prior.recorded_at")
    if (_date(prior_ir.get("research_as_of"), "prior.ir.research_as_of") > prior_case["as_of"]
            or not (prior_case["as_of"] <= prior_recorded <= current_as_of)):
        raise ValueError("PRIOR_FUTURE_OR_TEMPORALLY_INCONSISTENT")
    if (prior_req.get("method_version") != prior_case.get("method_version")
            or prior_req.get("strategy_id") != prior_case.get("strategy_id")):
        raise ValueError("PRIOR_METHOD_STRATEGY_INCONSISTENT")
    old_facts = _facts(prior_ir.get("facts"), "prior.facts")
    seen_prior, seen_current, items = set(), set(), []
    for i, link in enumerate(fact_links):
        if not isinstance(link, Mapping) or set(link) != {"prior_fact_id", "current_fact_id"}:
            raise ValueError("FACT_LINK_EXACT_SCHEMA_REQUIRED")
        old = _id(link["prior_fact_id"], f"fact_links[{i}].prior_fact_id")
        new = _id(link["current_fact_id"], f"fact_links[{i}].current_fact_id")
        if old not in old_facts or new not in current_facts:
            raise ValueError("FACT_LINK_UNKNOWN_ID")
        if old in seen_prior or new in seen_current:
            raise ValueError("DUPLICATE_FACT_LINK")
        seen_prior.add(old)
        seen_current.add(new)
        before, after = old_facts[old], current_facts[new]
        items.append({"prior_fact_id": old, "current_fact_id": new,
                      "prior_claim_private": before["claim"], "current_claim_private": after["claim"],
                      "prior_evidence_status": before["status"],
                      "current_evidence_status": after["status"],
                      "text_check": ("TEXT_SAME_NOT_EVIDENCE_OF_NO_CHANGE" if before["claim"] == after["claim"]
                                     else "TEXT_DIFF_NOT_CERTIFIED_ECONOMIC_CHANGE")})
    strategy_changed = prior_case["strategy_id"] != request.get("strategy_id")
    method_changed = prior_case["method_version"] != request.get("method_version")
    return {"status": "STRUCTURAL_REVIEW_PREPARED" if items else "NO_FACT_LINKS_SUPPLIED",
            "subject_id_private": subject, "prior_analysis_id_private": prior_id,
            "current_analysis_id_private": current_id, "prior_as_of": prior_case["as_of"],
            "current_as_of": current_as_of, "strategy_changed": strategy_changed,
            "method_changed": method_changed, "review_items_private": items,
            "comparability": "ANALYST_MUST_VERIFY_IDENTITY_METRIC_UNITS_PERIODS_AND_RIGHTS",
            "baseline_authentication": "CALLER_SUPPLIED_RECORD_STRUCTURALLY_CHECKED_ONLY",
            "source_authentication": "NOT_PERFORMED", "economic_change_status": "NOT_EVALUATED",
            "privacy": "PRIVATE_ONLY"}
