"""Private IR four-pillar evidence handoff; no economic grading or source certification."""
from __future__ import annotations

from datetime import date
import re
from typing import Any, Mapping

PILLARS = ("QUALITY", "DURABILITY", "EXPECTED_RETURN", "CONFIDENCE")
STATES = frozenset({"SPECIALIST_REPORTED", "UNKNOWN"})
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,79}\Z")


def _id(value: Any, field: str) -> str:
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise ValueError(f"{field}: safe opaque ID required")
    return value


def _date(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field}: canonical date required")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field}: canonical date required") from exc
    if parsed.isoformat() != value:
        raise ValueError(f"{field}: canonical date required")
    return value


def prepare_pillar_trace(*, request: Mapping[str, Any], ir_capsule: Mapping[str, Any],
                         fact_alignment: Mapping[str, Any] | None = None) -> dict[str, Any] | None:
    """Assemble optional caller-supplied IR views without creating a score.

    Four research pillars belong to IR; Portfolio Room remains a separate,
    PI-observation-dependent assessment. All rationales remain PRIVATE.
    """
    if not isinstance(request, Mapping) or not isinstance(ir_capsule, Mapping):
        raise ValueError("PILLAR_REQUEST_AND_IR_REQUIRED")
    if "PILLAR_ASSESSMENTS" not in ir_capsule:
        return None
    supplied = ir_capsule["PILLAR_ASSESSMENTS"]
    if not isinstance(supplied, Mapping) or set(supplied) != {
        "analysis_id", "research_as_of", "strategy_id", "pillars"
    }:
        raise ValueError("PILLAR_EXACT_SCHEMA_REQUIRED")
    aid = _id(request.get("analysis_id"), "analysis_id")
    cutoff = _date(request.get("as_of"), "as_of")
    ir_date = _date(ir_capsule.get("research_as_of"), "ir.research_as_of")
    strategy = request.get("strategy_id")
    if (supplied["analysis_id"] != aid or ir_capsule.get("analysis_id") != aid
            or _date(supplied["research_as_of"], "pillar.research_as_of") != ir_date
            or ir_date > cutoff or not isinstance(strategy, str) or not strategy.strip()
            or supplied["strategy_id"] != strategy):
        raise ValueError("PILLAR_ID_DATE_OR_STRATEGY_MISMATCH")
    facts = ir_capsule.get("facts")
    if not isinstance(facts, list):
        raise ValueError("PILLAR_IR_FACT_LIST_REQUIRED")
    fact_statuses: dict[str, str] = {}
    for row in facts:
        if not isinstance(row, Mapping):
            raise ValueError("PILLAR_IR_FACT_INVALID")
        fid = _id(row.get("id"), "fact.id")
        if fid in fact_statuses or row.get("status") not in {"VERIFIED", "INDICATIVE", "MISSING", "CONFLICTED"}:
            raise ValueError("PILLAR_IR_FACT_DUPLICATE_OR_BAD_STATUS")
        fact_statuses[fid] = row["status"]
    blocked_ids: set[str] = set()
    if fact_alignment is not None:
        if (not isinstance(fact_alignment, Mapping)
                or fact_alignment.get("analysis_id") != aid
                or fact_alignment.get("analysis_as_of") != cutoff
                or fact_alignment.get("status") != "PRIVATE_FACT_SOURCE_ALIGNMENT_NOT_CERTIFIED"
                or fact_alignment.get("source_authentication") != "NOT_PERFORMED"):
            raise ValueError("PILLAR_ALIGNMENT_AUTHORITY_MISMATCH")
        rows = fact_alignment.get("facts_private")
        if not isinstance(rows, list) or len(rows) != len(fact_statuses):
            raise ValueError("PILLAR_ALIGNMENT_COVERAGE_MISMATCH")
        seen: set[str] = set()
        for row in rows:
            if not isinstance(row, Mapping):
                raise ValueError("PILLAR_ALIGNMENT_ROW_INVALID")
            fid = row.get("fact_id_private")
            if fid not in fact_statuses or fid in seen or row.get("ir_reported_status") != fact_statuses[fid]:
                raise ValueError("PILLAR_ALIGNMENT_FACT_MISMATCH")
            seen.add(fid)
            if row.get("review_flags") or row.get("alignment") != "CALLER_REPORTED_STRUCTURALLY_ALIGNED_ONLY":
                blocked_ids.add(fid)
    axes = supplied["pillars"]
    if not isinstance(axes, Mapping) or set(axes) != set(PILLARS):
        raise ValueError("PILLAR_EXACT_FOUR_AXES_REQUIRED")
    output = {}
    for name in PILLARS:
        item = axes[name]
        if not isinstance(item, Mapping) or set(item) != {
            "status", "ir_fact_ids", "rationale_private", "countercase_private"
        } or item.get("status") not in STATES:
            raise ValueError(f"PILLAR_{name}_INVALID")
        refs = item["ir_fact_ids"]
        if (not isinstance(refs, list) or len(refs) > 24
                or any(not isinstance(x, str) or not ID.fullmatch(x) for x in refs)
                or len(set(refs)) != len(refs) or set(refs) - fact_statuses.keys()):
            raise ValueError(f"PILLAR_{name}_FACT_LINKS_INVALID")
        for field in ("rationale_private", "countercase_private"):
            value = item[field]
            if not isinstance(value, str) or not 1 <= len(value.strip()) <= 2000:
                raise ValueError(f"PILLAR_{name}_{field}_REQUIRED")
        state = item["status"]
        if state == "SPECIALIST_REPORTED" and not refs:
            raise ValueError(f"PILLAR_{name}_REPORTED_WITHOUT_FACTS")
        if state == "UNKNOWN":
            stage = "NOT_ASSESSED"
        elif fact_alignment is None or any(fid in blocked_ids or fact_statuses[fid] in {"MISSING", "CONFLICTED"} for fid in refs):
            stage = "EVIDENCE_RESOLUTION"
        else:
            stage = "HUMAN_RESEARCH_REVIEW_ONLY"
        output[name] = {
            "reported_status": state, "review_stage": stage,
            "ir_fact_ids_private": list(refs),
            "rationale_private": item["rationale_private"],
            "countercase_private": item["countercase_private"],
        }
    return {
        "status": "PRIVATE_FOUR_PILLAR_IR_TRACE_NOT_CERTIFIED",
        "analysis_id": aid, "analysis_as_of": cutoff, "strategy_id": strategy,
        "research_as_of": ir_date, "pillars_private": output,
        "source_authentication": "NOT_PERFORMED",
        "expected_return_certification": "NOT_ESTABLISHED",
        "portfolio_room": "SEPARATE_PI_EVIDENCE_REQUIRED",
        "investment_or_trade_authority": "NONE", "storage": "NONE",
    }
