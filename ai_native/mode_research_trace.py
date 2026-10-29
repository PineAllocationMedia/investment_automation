"""Private six-mode IR-question evidence links for the R1 manual research report.

The CEO-selected mode determines the fixed questions. Returned specialist
links are research-reported, not source authentication, policy approval or a
grading/portfolio allocation model. No external access or persistence.
"""
from __future__ import annotations

from datetime import date
import re
from typing import Any, Mapping

from .strategy_research_brief import prepare_strategy_research_brief

SAFE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,79}\\Z")
FACT_STATUSES = frozenset({"VERIFIED", "INDICATIVE", "MISSING", "CONFLICTED"})


def _date(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("MODE_RESEARCH_DATE_INVALID")
    try:
        d = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("MODE_RESEARCH_DATE_INVALID") from exc
    if value != d.isoformat():
        raise ValueError("MODE_RESEARCH_DATE_INVALID")
    return value


def prepare_mode_research_trace(
    *, request: Mapping[str, Any], ir_capsule: Mapping[str, Any],
    fact_alignment: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Link at most one specialist response to each predefined mode question.

    No answer is inferred from a fact or fabricated when IR omitted this field.
    Linked facts are descriptive; source-use alignment only permits human
    review, never certified support or financial-policy execution.
    """
    if "MODE_RESEARCH_RESPONSES" not in ir_capsule:
        return None
    response = ir_capsule["MODE_RESEARCH_RESPONSES"]
    if not isinstance(response, Mapping) or set(response) != {
        "analysis_id", "research_as_of", "strategy_id", "answers"
    }:
        raise ValueError("MODE_RESEARCH_EXACT_SCHEMA_REQUIRED")
    aid, strategy = request.get("analysis_id"), request.get("strategy_id")
    if not isinstance(aid, str) or not SAFE_ID.fullmatch(aid):
        raise ValueError("MODE_RESEARCH_ID_INVALID")
    if not isinstance(strategy, str) or not strategy.strip():
        raise ValueError("MODE_RESEARCH_STRATEGY_INVALID")
    cutoff, ir_date = _date(request.get("as_of")), _date(ir_capsule.get("research_as_of"))
    if (ir_capsule.get("analysis_id") != aid
            or response["analysis_id"] != aid
            or _date(response["research_as_of"]) != ir_date
            or ir_date > cutoff
            or not isinstance(response["strategy_id"], str)
            or response["strategy_id"].strip().lower() != strategy.strip().lower()):
        raise ValueError("MODE_RESEARCH_ID_DATE_OR_STRATEGY_MISMATCH")
    brief = prepare_strategy_research_brief(strategy)
    questions = brief["ir_research_questions"]
    facts = ir_capsule.get("facts")
    if not isinstance(facts, list):
        raise ValueError("MODE_RESEARCH_FACTS_REQUIRED")
    statuses = {}
    for fact in facts:
        if not isinstance(fact, Mapping):
            raise ValueError("MODE_RESEARCH_FACT_INVALID")
        fid = fact.get("id")
        if (not isinstance(fid, str) or not SAFE_ID.fullmatch(fid)
                or fid in statuses or fact.get("status") not in FACT_STATUSES):
            raise ValueError("MODE_RESEARCH_FACT_ID_OR_STATUS_INVALID")
        statuses[fid] = fact["status"]

    blocked = set(statuses)
    if fact_alignment is not None:
        if (not isinstance(fact_alignment, Mapping)
                or fact_alignment.get("status") != "PRIVATE_FACT_SOURCE_ALIGNMENT_NOT_CERTIFIED"
                or fact_alignment.get("analysis_id") != aid
                or fact_alignment.get("analysis_as_of") != cutoff
                or fact_alignment.get("source_authentication") != "NOT_PERFORMED"):
            raise ValueError("MODE_RESEARCH_ALIGNMENT_AUTHORITY_MISMATCH")
        rows = fact_alignment.get("facts_private")
        if not isinstance(rows, list) or len(rows) != len(statuses):
            raise ValueError("MODE_RESEARCH_ALIGNMENT_COVERAGE_INVALID")
        found = set()
        blocked = set()
        for row in rows:
            if not isinstance(row, Mapping):
                raise ValueError("MODE_RESEARCH_ALIGNMENT_ROW_INVALID")
            fid = row.get("fact_id_private")
            if (fid not in statuses or fid in found
                    or row.get("ir_reported_status") != statuses[fid]):
                raise ValueError("MODE_RESEARCH_ALIGNMENT_FACT_MISMATCH")
            found.add(fid)
            if (row.get("review_flags")
                    or row.get("alignment") != "CALLER_REPORTED_STRUCTURALLY_ALIGNED_ONLY"):
                blocked.add(fid)

    answers = response["answers"]
    if not isinstance(answers, list) or len(answers) != len(questions):
        raise ValueError("MODE_RESEARCH_QUESTION_COUNT_MISMATCH")
    by_index = {}
    for answer in answers:
        if not isinstance(answer, Mapping) or set(answer) != {
            "question_index", "status", "ir_fact_ids"
        }:
            raise ValueError("MODE_RESEARCH_ANSWER_SCHEMA_INVALID")
        index, status, ids = answer["question_index"], answer["status"], answer["ir_fact_ids"]
        if (type(index) is not int or not 1 <= index <= len(questions)
                or index in by_index or status not in {"SPECIALIST_REPORTED", "UNKNOWN"}
                or not isinstance(ids, list) or len(ids) > 12
                or any(not isinstance(fid, str) or not SAFE_ID.fullmatch(fid) for fid in ids)
                or len(set(ids)) != len(ids) or set(ids) - statuses.keys()
                or (status == "SPECIALIST_REPORTED") != bool(ids)):
            raise ValueError("MODE_RESEARCH_ANSWER_LINKS_INVALID")
        if status == "UNKNOWN":
            stage = "NOT_ASSESSED"
        elif any(fid in blocked or statuses[fid] in {"MISSING", "CONFLICTED"} for fid in ids):
            stage = "EVIDENCE_RESOLUTION"
        else:
            stage = "HUMAN_RESEARCH_REVIEW_ONLY"
        by_index[index] = {
            "question_index": index, "question_text": questions[index - 1],
            "reported_status": status, "review_stage": stage,
            "ir_fact_ids_private": list(ids),
        }
    return {
        "status": "PRIVATE_MODE_RESEARCH_TRACE_NOT_CERTIFIED",
        "analysis_id": aid, "analysis_as_of": cutoff, "strategy_id": strategy,
        "research_as_of": ir_date,
        "questions_private": [by_index[i] for i in range(1, len(questions) + 1)],
        "source_authentication": "NOT_PERFORMED",
        "method_load": "NOT_VERIFIED",
        "investment_or_trade_authority": "NONE",
        "storage": "NONE",
    }
