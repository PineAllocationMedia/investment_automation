"""Private six-mode PI question links to caller-reported dated portfolio rows.

A linked P_ID is neither a verified holding nor proof of portfolio suitability.
The same two questions from M1 are reused; no weights, trades or policies are
computed or authorized. Missing evidence is explicitly unresolved.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Mapping

from .strategy_research_brief import prepare_strategy_research_brief


def _date(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("MODE_PI_DATE_INVALID")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("MODE_PI_DATE_INVALID") from exc
    if parsed.isoformat() != value:
        raise ValueError("MODE_PI_DATE_INVALID")
    return value


def prepare_mode_portfolio_trace(
    *, request: Mapping[str, Any], pi_delta: Mapping[str, Any],
    observation: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Classify optional PI question replies against an already supplied P ledger."""
    if not isinstance(request, Mapping) or not isinstance(pi_delta, Mapping):
        raise ValueError("MODE_PI_REQUEST_AND_DELTA_REQUIRED")
    if "MODE_PORTFOLIO_RESPONSES" not in pi_delta:
        return None
    response = pi_delta["MODE_PORTFOLIO_RESPONSES"]
    if not isinstance(response, Mapping) or set(response) != {
        "analysis_id", "portfolio_as_of", "strategy_id", "answers"
    }:
        raise ValueError("MODE_PI_EXACT_SCHEMA_REQUIRED")
    aid, strategy = request.get("analysis_id"), request.get("strategy_id")
    if not isinstance(aid, str) or not aid.strip() or not isinstance(strategy, str) or not strategy.strip():
        raise ValueError("MODE_PI_REQUEST_CONTEXT_INVALID")
    cutoff = _date(request.get("as_of"))
    observed = _date(pi_delta.get("portfolio_as_of"))
    if (observed > cutoff or pi_delta.get("analysis_id") != aid
            or response.get("analysis_id") != aid
            or _date(response.get("portfolio_as_of")) != observed
            or not isinstance(response.get("strategy_id"), str)
            or response["strategy_id"].strip().lower() != strategy.strip().lower()):
        raise ValueError("MODE_PI_ID_DATE_OR_STRATEGY_MISMATCH")
    questions = prepare_strategy_research_brief(strategy)["pi_portfolio_questions"]

    positions: dict[str, Mapping[str, Any]] | None = None
    unresolved_scope = True
    if observation is not None:
        if (not isinstance(observation, Mapping)
                or observation.get("analysis_id") != aid
                or observation.get("analysis_as_of") != cutoff
                or observation.get("observed_on") != observed
                or observation.get("private_scope") is not True
                or observation.get("verification") != "CALLER_ASSERTED_NOT_INDEPENDENTLY_AUTHENTICATED"
                or observation.get("source_retrieval") != "NONE"
                or observation.get("decision_authority") != "CEO_ONLY"):
            raise ValueError("MODE_PI_P_LEDGER_AUTHORITY_OR_ID_MISMATCH")
        rows = observation.get("p_ledger_private")
        if not isinstance(rows, list) or not rows or len(rows) > 10000:
            raise ValueError("MODE_PI_P_LEDGER_ROWS_INVALID")
        positions = {}
        for row in rows:
            if not isinstance(row, Mapping):
                raise ValueError("MODE_PI_P_LEDGER_ROW_INVALID")
            pid = row.get("p_id")
            if not isinstance(pid, str) or not pid or pid in positions or pid == "P-CASH":
                raise ValueError("MODE_PI_P_LEDGER_DUPLICATE_OR_INVALID_ID")
            positions[pid] = row
        qualifiers = observation.get("missing_or_qualified")
        if not isinstance(qualifiers, list):
            raise ValueError("MODE_PI_P_LEDGER_QUALIFIERS_INVALID")
        unresolved_scope = bool(qualifiers) or observation.get("status") != "SCOPED_WEIGHTS_DERIVED_FROM_CALLER_VISIBLE_DATA"

    answers = response.get("answers")
    if not isinstance(answers, list) or len(answers) != len(questions):
        raise ValueError("MODE_PI_QUESTION_COUNT_MISMATCH")
    by_index: dict[int, dict[str, Any]] = {}
    for answer in answers:
        if not isinstance(answer, Mapping) or set(answer) != {
            "question_index", "status", "p_ids"
        }:
            raise ValueError("MODE_PI_ANSWER_SCHEMA_INVALID")
        index, status, ids = answer["question_index"], answer["status"], answer["p_ids"]
        if (type(index) is not int or index < 1 or index > len(questions) or index in by_index
                or status not in {"SPECIALIST_REPORTED", "UNKNOWN"}
                or not isinstance(ids, list) or len(ids) > 24
                or any(not isinstance(x, str) or not x or len(x) > 256 for x in ids)
                or len(set(ids)) != len(ids)
                or (status == "SPECIALIST_REPORTED") != bool(ids)):
            raise ValueError("MODE_PI_ANSWER_LINKS_INVALID")
        if positions is not None and set(ids) - positions.keys():
            raise ValueError("MODE_PI_UNKNOWN_P_ID")
        if status == "UNKNOWN":
            stage = "NOT_ASSESSED"
        elif positions is None or unresolved_scope or any(
            any(value != "VERIFIED_VISIBLE"
                for value in positions[pid].get("field_statuses", {}).values())
            or set(positions[pid].get("field_statuses", {}))
            != {"security_id", "market_value_base", "currency", "account_scope"}
            for pid in ids
        ):
            stage = "EVIDENCE_RESOLUTION"
        else:
            stage = "HUMAN_PORTFOLIO_REVIEW_ONLY"
        by_index[index] = {
            "question_index": index, "question_text": questions[index - 1],
            "reported_status": status, "review_stage": stage,
            "p_ids_private": list(ids),
        }
    return {
        "status": "PRIVATE_MODE_PI_TRACE_NOT_AUTHENTICATED",
        "analysis_id": aid, "analysis_as_of": cutoff,
        "portfolio_as_of": observed, "strategy_id": strategy,
        "questions_private": [by_index[i] for i in range(1, len(questions) + 1)],
        "observation_link_status": "CALLER_REPORTED_P_LEDGER" if positions is not None else "NO_P_LEDGER",
        "source_authentication": "NOT_PERFORMED",
        "method_load": "NOT_VERIFIED",
        "portfolio_room_authority": "NONE",
        "investment_or_trade_authority": "NONE", "storage": "NONE",
    }
