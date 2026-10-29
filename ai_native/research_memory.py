"""In-memory, private research-history assembly with no repository or disk writes.

Research content and source locators stay in the private return value. The only
repository-facing proposal is a content-free review gate; it is NOT approval.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import re
from typing import Any, Mapping

EVIDENCE_STATUSES = frozenset({"VERIFIED", "INDICATIVE", "CONFLICTED", "MISSING"})
IDENTITY = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,79}\Z")


def _id(value: Any, field: str) -> str:
    if not isinstance(value, str) or not IDENTITY.fullmatch(value):
        raise ValueError(f"{field}: opaque nonblank identifier required (max 80 safe characters)")
    return value


def _date(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field}: ISO date required")
    try:
        d = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field}: invalid ISO date") from exc
    if d.isoformat() != value:
        raise ValueError(f"{field}: canonical YYYY-MM-DD required")
    return value


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field}: nonempty value required")
    return value.strip()


def prepare_research_history(
    request: Mapping[str, Any],
    ir_capsule: Mapping[str, Any],
    *,
    report_id: str,
    instruction_version: str,
    recorded_at: str,
    parent_report_id: str | None = None,
    accessible_parent: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return PRIVATE append-only case proposal + content-free governance gate.

    No actual archive, source validation or automatic GitHub write occurs. A
    parent pointer alone is never treated as an accessible historical baseline.
    """
    if not isinstance(request, Mapping) or not isinstance(ir_capsule, Mapping):
        raise ValueError("request and ir_capsule must be mappings")
    analysis_id = _id(request.get("analysis_id"), "analysis_id")
    current_id = _id(report_id, "report_id")
    if _id(ir_capsule.get("analysis_id"), "ir.analysis_id") != analysis_id:
        raise ValueError("PACKET_INCOMPLETE: IR analysis ID differs")
    as_of = _date(request.get("as_of"), "request.as_of")
    ir_as_of = _date(ir_capsule.get("research_as_of"), "ir.research_as_of")
    recorded = _date(recorded_at, "recorded_at")
    if ir_as_of > as_of or as_of > recorded:
        raise ValueError("TEMPORAL_MISMATCH: research, as-of, and record dates are incompatible")
    kind = _text(request.get("kind"), "kind")
    if kind not in {"DECISION", "FOLLOWUP"}:
        raise ValueError("kind: DECISION or FOLLOWUP required")
    strategy = _text(request.get("strategy_id"), "strategy_id")
    method = _text(request.get("method_version"), "method_version")
    instr = _text(instruction_version, "instruction_version")
    prior_id = _id(parent_report_id, "parent_report_id") if parent_report_id is not None else None
    if prior_id == current_id:
        raise ValueError("APPEND_ONLY_VIOLATION: report cannot reference itself")
    if accessible_parent is not None and prior_id is None:
        raise ValueError("accessible_parent requires a parent_report_id")
    parent_status = "BASELINE_NOT_AVAILABLE"
    if prior_id is not None:
        parent_status = "BASELINE_REFERENCE_NOT_VERIFIED"
        if accessible_parent is not None:
            if not isinstance(accessible_parent, Mapping):
                raise ValueError("accessible_parent: mapping required")
            if _id(accessible_parent.get("report_id"), "parent.report_id") != prior_id:
                raise ValueError("PARENT_ID_MISMATCH")
            earlier = _date(accessible_parent.get("as_of"), "parent.as_of")
            if earlier > as_of:
                raise ValueError("PARENT_IS_NEWER_THAN_CURRENT")
            parent_status = "ACCESSIBLE_PARENT_ID_AND_DATE_CHECKED_ONLY"
    facts = ir_capsule.get("facts")
    if not isinstance(facts, list):
        raise ValueError("ir.facts: list required")
    fact_ids: list[str] = []
    counts = {key: 0 for key in sorted(EVIDENCE_STATUSES)}
    for i, fact in enumerate(facts):
        if not isinstance(fact, Mapping):
            raise ValueError(f"ir.facts[{i}]: mapping required")
        fact_id = _id(fact.get("id"), f"ir.facts[{i}].id")
        if fact_id in fact_ids:
            raise ValueError("DUPLICATE_FACT_ID")
        status = _text(fact.get("status"), f"ir.facts[{i}].status")
        if status not in EVIDENCE_STATUSES:
            raise ValueError("UNSUPPORTED_EVIDENCE_STATUS")
        counts[status] += 1
        fact_ids.append(fact_id)
    private_record = {
        "schema_version": "RESEARCH_HISTORY_R1",
        "record_type": "PRIVATE_RESEARCH_CASE_PROPOSAL",
        "archive_status": "PROPOSED_NOT_COMMITTED",
        "privacy_tier": "PRIVATE_PENDING_REVIEW",
        "report_id": current_id,
        "parent_report_id": prior_id,
        "baseline_status": parent_status,
        "analysis_id": analysis_id,
        "recorded_at": recorded,
        "as_of": as_of,
        "research_as_of": ir_as_of,
        "kind": kind,
        "strategy_id": strategy,
        "instruction_version": instr,
        "method_version": method,
        "fact_ids": fact_ids,
        "evidence_status_counts": counts,
        "source_authentication": "NOT_PERFORMED_BY_MEMORY_HELPER",
        "cross_record_uniqueness": "NOT_CHECKED_NO_ARCHIVE_READ",
        "original_request": deepcopy(dict(request)),
        "original_ir_capsule": deepcopy(dict(ir_capsule)),
    }
    # Deliberately NO user-supplied text, IDs, source URLs or content here.
    github_review_gate = {
        "schema_version": "RESEARCH_MEMORY_GITHUB_REVIEW_R1",
        "status": "WITHHELD_PENDING_HUMAN_PRIVACY_AND_RIGHTS_REVIEW",
        "approved_for_publication": False,
        "archive_status": "PROPOSED_NOT_COMMITTED",
        "record_locator_included": False,
        "contains_research_content": False,
        "private_record_reviewer_required": True,
    }
    return {"private_research_history_proposal": private_record,
            "github_review_gate": github_review_gate}


def prepare_explicit_followup_draft(prior_case: Mapping[str, Any]) -> dict[str, Any]:
    """Prepare a PRIVATE inert follow-up envelope from a supplied case proposal.

    This is not research, an archival read, a new CEO instruction, a calendar
    reminder, source authentication or a request to a ChatGPT Project. The CEO
    must explicitly set the next mandate, date and analysis ID and review the
    inherited strategy/method before an ordinary manual session can begin.
    """
    if not isinstance(prior_case, Mapping):
        raise ValueError("FOLLOWUP_PRIVATE_CASE_REQUIRED")
    if (prior_case.get("schema_version") != "RESEARCH_HISTORY_R1"
            or prior_case.get("record_type") != "PRIVATE_RESEARCH_CASE_PROPOSAL"
            or prior_case.get("privacy_tier") != "PRIVATE_PENDING_REVIEW"
            or prior_case.get("archive_status") != "PROPOSED_NOT_COMMITTED"
            or prior_case.get("source_authentication") != "NOT_PERFORMED_BY_MEMORY_HELPER"
            or prior_case.get("cross_record_uniqueness") != "NOT_CHECKED_NO_ARCHIVE_READ"):
        raise ValueError("FOLLOWUP_PRIOR_CASE_AUTHORITY_INVALID")
    prior_id = _id(prior_case.get("analysis_id"), "prior.analysis_id")
    _id(prior_case.get("report_id"), "prior.report_id")
    prior_as_of = _date(prior_case.get("as_of"), "prior.as_of")
    recorded = _date(prior_case.get("recorded_at"), "prior.recorded_at")
    ir_as_of = _date(prior_case.get("research_as_of"), "prior.research_as_of")
    if not (ir_as_of <= prior_as_of <= recorded):
        raise ValueError("FOLLOWUP_PRIOR_DATES_INCONSISTENT")
    req, ir = prior_case.get("original_request"), prior_case.get("original_ir_capsule")
    if not isinstance(req, Mapping) or not isinstance(ir, Mapping):
        raise ValueError("FOLLOWUP_PRIOR_ORIGINAL_PACKETS_REQUIRED")
    subject = _id(req.get("subject_id"), "prior.subject_id")
    strategy = _text(prior_case.get("strategy_id"), "prior.strategy_id")
    method = _text(prior_case.get("method_version"), "prior.method_version")
    if (req.get("ceo_initiated") is not True
            or req.get("research_needed") is not True
            or req.get("analysis_id") != prior_id
            or ir.get("analysis_id") != prior_id
            or req.get("as_of") != prior_as_of
            or ir.get("research_as_of") != ir_as_of
            or req.get("strategy_id") != strategy
            or req.get("method_version") != method
            or req.get("kind") != prior_case.get("kind")
            or req.get("kind") not in {"DECISION", "FOLLOWUP"}):
        raise ValueError("FOLLOWUP_PRIOR_PACKETS_INCONSISTENT")
    facts = ir.get("facts")
    if not isinstance(facts, list):
        raise ValueError("FOLLOWUP_PRIOR_FACTS_REQUIRED")
    ids: list[str] = []
    counts = {status: 0 for status in sorted(EVIDENCE_STATUSES)}
    for i, raw in enumerate(facts):
        if not isinstance(raw, Mapping):
            raise ValueError("FOLLOWUP_PRIOR_FACT_INVALID")
        fid = _id(raw.get("id"), f"prior.facts[{i}].id")
        reported = raw.get("status")
        if fid in ids or reported not in EVIDENCE_STATUSES:
            raise ValueError("FOLLOWUP_PRIOR_FACT_INVALID")
        ids.append(fid)
        counts[reported] += 1
    if (prior_case.get("fact_ids") != ids
            or prior_case.get("evidence_status_counts") != counts):
        raise ValueError("FOLLOWUP_PRIOR_FACT_SUMMARY_MISMATCH")

    # This is intentionally NOT executable until the CEO explicitly fills and
    # approves the new request. No stale portfolio, account/fees, evidence
    # rights, risk constraints or current assertions are inherited.
    draft_request = {
        "ceo_initiated": False,
        "analysis_id": None,
        "as_of": None,
        "kind": "FOLLOWUP",
        "objective": None,
        "research_needed": True,
        "portfolio_needed": False,
        "subject_id": subject,
        "prior_analysis_id": prior_id,
        "period_start": prior_as_of,
        "strategy_id": strategy,
        "method_version": method,
        "risk_constraints": [],
    }
    return {
        "status": "PRIVATE_FOLLOWUP_DRAFT_REQUIRES_CEO_INITIATION",
        "input_template": {
            "request": draft_request,
            "historical_comparison_inputs": {
                "prior_case": deepcopy(dict(prior_case)),
                "subject_id": subject,
                "fact_links": [],
            },
        },
        "human_checks": [
            "Explicitly authorize a NEW CEO-initiated request; enter its distinct analysis ID, current cutoff date and objective.",
            "Confirm subject/economic identity, strategy, current method version, risk constraints and original evidence/rights before research.",
            "Select any fresh portfolio analysis explicitly; do not reuse prior account balances, holdings, costs or position weights.",
            "After NEW IR evidence arrives, link old/current fact IDs manually; no factual, source, methodology or economic change is certified.",
        ],
        "readiness": "NOT_EVALUATED",
        "source_authentication": "NOT_PERFORMED",
        "project_invocation": "NONE",
        "storage": "NONE",
        "trading_authority": "NONE",
    }
