"""Bounded manual-handoff assembler for the AI-native R1 construction release.

Consumes already-researched IR/PI capsules. Does not call Projects, browse,
authenticate sources, persist private records, or authorize portfolio action.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Mapping

from .contribution_math import project_gross_contribution
from .known_costs import tally_supplied_costs
from .research_memory import prepare_research_history
from .evidence_math import audit_calculation
from .reporting import render_report

ROOM_STATUSES = frozenset({"ROOM_EVIDENCE_SUPPORTED", "ROOM_CONDITIONAL", "ROOM_UNAVAILABLE"})


def _required_text(record: Mapping[str, Any], key: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key}: nonempty string required")
    return value.strip()


def _date(value: str, key: str) -> date:
    try:
        result = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{key}: ISO date required") from exc
    if result.isoformat() != value:
        raise ValueError(f"{key}: canonical ISO date required")
    return result


def assemble_manual_run(
    request: Mapping[str, Any],
    ir_capsule: Mapping[str, Any],
    *,
    pi_delta: Mapping[str, Any] | None = None,
    calculation_requests: list[Mapping[str, Any]] | None = None,
    contribution_inputs: Mapping[str, Any] | None = None,
    cost_inputs: Mapping[str, Any] | None = None,
    memory_inputs: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble a PRIVATE report without claiming live Project connectivity.

    IR/PI content remains user/specialist-supplied; validations preserve status
    and check consistency only. No side effects or archival writes occur.
    """
    if not isinstance(request, Mapping) or not isinstance(ir_capsule, Mapping):
        raise ValueError("request and ir_capsule must be mappings")
    run_id = _required_text(request, "analysis_id")
    as_of = _required_text(request, "as_of")
    cutoff = _date(as_of, "as_of")
    objective = _required_text(request, "objective")
    strategy = _required_text(request, "strategy_id")
    method = _required_text(request, "method_version")
    kind = _required_text(request, "kind")
    if kind not in {"DECISION", "FOLLOWUP"}:
        raise ValueError("kind must be DECISION or FOLLOWUP")
    if _required_text(ir_capsule, "analysis_id") != run_id:
        raise ValueError("IR analysis_id mismatch")
    ir_cutoff = _date(_required_text(ir_capsule, "research_as_of"), "research_as_of")
    if ir_cutoff > cutoff:
        raise ValueError("IR research is newer than request cutoff")
    if not isinstance(ir_capsule.get("summary"), list):
        raise ValueError("IR summary list required")
    if not isinstance(ir_capsule.get("facts"), list):
        raise ValueError("IR facts list required")
    if not 1 <= len(ir_capsule["summary"]) <= 5:
        raise ValueError("IR summary must contain one to five points")
    for item in ir_capsule["summary"]:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("IR summary contains empty item")
    summary = [item.strip() for item in ir_capsule["summary"]]
    limits = [_required_text(ir_capsule, "limitations")]
    status = "EXPLORATORY"
    room = "NOT_EVALUATED"
    pi_date = None
    if pi_delta is not None:
        if not isinstance(pi_delta, Mapping):
            raise ValueError("pi_delta must be a mapping")
        if _required_text(pi_delta, "analysis_id") != run_id:
            raise ValueError("PI analysis_id mismatch")
        if pi_delta.get("forwarded_ir") != ir_capsule:
            raise ValueError("PACKET_INCOMPLETE: PI must forward identical IR capsule")
        pi_date = _required_text(pi_delta, "portfolio_as_of")
        if _date(pi_date, "portfolio_as_of") > cutoff:
            raise ValueError("Portfolio observation is newer than request cutoff")
        room = _required_text(pi_delta, "room_status")
        if room not in ROOM_STATUSES:
            raise ValueError("invalid Portfolio Room status")
        summary.append("Portfolio: " + _required_text(pi_delta, "summary"))
        limits.append(_required_text(pi_delta, "limitations"))
        if room != "ROOM_EVIDENCE_SUPPORTED":
            status = "CONDITIONAL"
    if method == "UNKNOWN_NOT_LOADED":
        limits.append("Specialized method was not loaded; research remains exploratory.")
        status = "CONDITIONAL"

    checks: list[dict[str, Any]] = []
    for item in calculation_requests or []:
        if not isinstance(item, Mapping):
            raise ValueError("calculation request must be a mapping")
        checks.append(audit_calculation(
            _required_text(item, "operation"), item.get("left"), item.get("right"), as_of=as_of
        ))
    if any(item["status"] == "UNAVAILABLE" for item in checks):
        limits.append("One or more requested financial calculations are unavailable; see private calculation annex.")
        status = "CONDITIONAL"

    contribution = None
    if contribution_inputs is not None:
        if pi_delta is None:
            raise ValueError("Cannot calculate a contribution without a PI capsule")
        if not isinstance(contribution_inputs, Mapping):
            raise ValueError("contribution_inputs must be a mapping")
        if contribution_inputs.get("as_of") != pi_date:
            raise ValueError("Contribution input must use exact PI portfolio observation date")
        contribution = project_gross_contribution(**contribution_inputs)
        if contribution["status"] == "UNAVAILABLE":
            limits.append("Gross contribution projection unavailable: required scope flags were not established.")
            status = "CONDITIONAL"
        else:
            limits.append("Gross contribution math only; real account costs, taxes, FX and execution not assessed.")

    costs = None
    if cost_inputs is not None:
        if contribution is None:
            raise ValueError("cost_inputs require an available PI gross contribution projection")
        if not isinstance(cost_inputs, Mapping):
            raise ValueError("cost_inputs must be a mapping")
        if cost_inputs.get("analysis_as_of") != as_of:
            raise ValueError("cost_inputs analysis cutoff must match request as_of")
        costs = tally_supplied_costs(gross_projection=contribution, **cost_inputs)
        if costs["status"] != "SUPPLIED_COST_TALLY_ONLY":
            limits.append("After-cost analysis unavailable: incomplete or infeasible supplied purchase costs.")
        else:
            limits.append("Supplied-cost tally only; quotes, taxes and net execution not certified.")
            if costs.get("gross_allocation_funding_conflict"):
                limits.append("Gross allocation uses the full contribution; deducting fees from that same contribution needs a revised plan.")
        status = "CONDITIONAL"

    facts = ir_capsule["facts"]
    if any(isinstance(f, Mapping) and f.get("status") in {"MISSING", "CONFLICTED"} for f in facts):
        status = "CONDITIONAL"
    packet: dict[str, Any] = {
        "kind": kind,
        "analysis_id": run_id,
        "as_of": as_of,
        "strategy": strategy,
        "method_version": method,
        "status": status,
        "objective": objective,
        "decision_line": _required_text(ir_capsule, "decision_line"),
        "summary": summary,
        "facts": facts,
        "countercase": _required_text(ir_capsule, "countercase"),
        "limitations": " ".join(limits),
        "next_action": _required_text(ir_capsule, "next_action"),
    }
    if kind == "FOLLOWUP":
        packet["changes"] = ir_capsule.get("changes", [])
        if "prior_analysis_id" in request:
            packet["prior_analysis_id"] = request["prior_analysis_id"]
        if "period_start" in request or "period_end" in request:
            packet["period_start"] = request.get("period_start")
            packet["period_end"] = request.get("period_end")

    markdown = render_report(packet)
    # Memory proposal excludes portfolio data, issuer narrative and full claims.
    memory = {
        "analysis_id": run_id,
        "as_of": as_of,
        "method_version": method,
        "fact_ids": [x["id"] for x in facts],
        "archive_status": "PROPOSED_NOT_COMMITTED",
        "privacy_review": "REQUIRED_BEFORE_ANY_WRITE",
        "source_authentication": "NOT_PERFORMED_BY_INTEGRATION",
    }
    private_history = None
    github_review_gate = None
    if memory_inputs is not None:
        if not isinstance(memory_inputs, Mapping):
            raise ValueError("memory_inputs: mapping required")
        prepared = prepare_research_history(request, ir_capsule, **memory_inputs)
        private_history = prepared["private_research_history_proposal"]
        github_review_gate = prepared["github_review_gate"]

    return {
        "status": "ASSEMBLED_COMPONENT_ONLY_NOT_END_TO_END_ACCEPTANCE",
        "markdown": markdown,
        "calculation_checks": checks,
        "gross_contribution_private": contribution,
        "supplied_costs_private": costs,
        "portfolio_room_status": room,
        "memory_proposal_nonprivate": memory,
        "private_research_history_proposal": private_history,
        "github_memory_review_gate": github_review_gate,
        "handoff": "MANUAL_TRANSFER_NOT_PROJECT_AUTOMATION",
        "source_verification": "NOT_PERFORMED_BY_INTEGRATION",
    }
