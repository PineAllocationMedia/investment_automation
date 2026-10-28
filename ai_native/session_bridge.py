"""Bridge M1 manual handoffs to M7a reporting with no Project invocation.

All output is PRIVATE. This only routes caller-provided packets and retains
unknowns; no source authentication, brokerage access, archiving or trades.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from typing import Any, Mapping

from .request_assembly import prepare_manual_handoffs
from .integrated_flow import assemble_manual_run
from .reporting import render_report
from .portfolio_observation import prepare_observation_ledger

ROOM_STATUSES = frozenset({"ROOM_EVIDENCE_SUPPORTED", "ROOM_CONDITIONAL", "ROOM_UNAVAILABLE"})


def _required(obj: Mapping[str, Any], key: str) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key}: nonempty string required")
    return value.strip()


def _date(value: str, name: str) -> str:
    try:
        d = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{name}: invalid date") from exc
    if d.isoformat() != value:
        raise ValueError(f"{name}: canonical YYYY-MM-DD required")
    return value


def complete_manual_session(
    request: Mapping[str, Any],
    *,
    ir_capsule: Mapping[str, Any] | None = None,
    pi_delta: Mapping[str, Any] | None = None,
    portfolio_context: Mapping[str, Any] | None = None,
    calculation_requests: list[Mapping[str, Any]] | None = None,
    contribution_inputs: Mapping[str, Any] | None = None,
    cost_inputs: Mapping[str, Any] | None = None,
    memory_inputs: Mapping[str, Any] | None = None,
    observation_inputs: Mapping[str, Any] | None = None,
    source_evidence_inputs: Mapping[str, Any] | None = None,
    valuation_inputs: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """One CEO-initiated manual session, possibly awaiting a human transfer.

    IR route uses M7a unchanged; PI-only route renders a CONDITIONAL report
    because no original issuer research is supplied. No local or remote writes.
    """
    handoffs = prepare_manual_handoffs(request, ir_capsule=ir_capsule, portfolio_context=portfolio_context)
    route = handoffs["route"]
    if pi_delta is not None and not request["portfolio_needed"]:
        raise ValueError("PI_DELTA_UNREQUESTED")
    if (contribution_inputs is not None or cost_inputs is not None) and route != "CC_IR_PI_CC":
        raise ValueError("PORTFOLIO_ARITHMETIC_REQUIRES_IR_PI_M7A_ROUTE")
    if memory_inputs is not None and route not in {"CC_IR_CC", "CC_IR_PI_CC"}:
        raise ValueError("MEMORY_PACKET_REQUIRES_IR_CAPSULE")
    if calculation_requests is not None and route not in {"CC_IR_CC", "CC_IR_PI_CC"}:
        raise ValueError("FINANCIAL_CHECKS_REQUIRE_IR_CAPSULE")
    if source_evidence_inputs is not None and route not in {"CC_IR_CC", "CC_IR_PI_CC"}:
        raise ValueError("SOURCE_ANNEX_REQUIRES_IR_CAPSULE")
    if valuation_inputs is not None and route not in {"CC_IR_CC", "CC_IR_PI_CC"}:
        raise ValueError("VALUATION_REQUIRES_IR_CAPSULE")

    observation = None
    if observation_inputs is not None:
        if route not in {"CC_PI_CC", "CC_IR_PI_CC"}:
            raise ValueError("PORTFOLIO_OBSERVATION_REQUIRES_PI_ROUTE")
        if not isinstance(observation_inputs, Mapping):
            raise ValueError("observation_inputs: mapping required")
        if observation_inputs.get("analysis_id") != request.get("analysis_id"):
            raise ValueError("OBSERVATION_ANALYSIS_ID_MISMATCH")
        if observation_inputs.get("analysis_as_of") != request.get("as_of"):
            raise ValueError("OBSERVATION_ANALYSIS_CUTOFF_MISMATCH")
        observation = prepare_observation_ledger(**observation_inputs)
        if pi_delta is not None and observation["observed_on"] != pi_delta.get("portfolio_as_of"):
            raise ValueError("OBSERVATION_PI_DATE_MISMATCH")
        if (pi_delta is not None and pi_delta.get("room_status") == "ROOM_EVIDENCE_SUPPORTED"
                and observation["known_scope_weights_pct"] is None):
            raise ValueError("UNSUPPORTED_PORTFOLIO_ROOM_ASSERTION: incomplete observation")

    private = {"status": "MANUAL_SESSION_PENDING", "route": route,
               "handoffs_private": handoffs, "final_report_private": None,
               "integrated_private": None, "pi_delta_private": None,
               "portfolio_observation_private": observation,
               "method_load_verification": "NOT_PERFORMED", "project_invocation": "NONE",
               "source_authentication": "NOT_PERFORMED", "storage": "NONE",
               "readiness": "NOT_EVALUATED"}

    if route == "CC_DIRECT":
        private["status"] = "CC_DIRECT_NO_SPECIALIST_REPORT_REQUIRED"
        return private
    if route in {"CC_IR_CC", "CC_IR_PI_CC"} and ir_capsule is None:
        private["status"] = "AWAITING_MANUAL_IR_CAPSULE"
        return private
    if route in {"CC_IR_PI_CC", "CC_PI_CC"} and pi_delta is None:
        private["status"] = "AWAITING_MANUAL_PI_DELTA"
        return private

    if route == "CC_PI_CC":
        if not isinstance(pi_delta, Mapping):
            raise ValueError("pi_delta: mapping required")
        if _required(pi_delta, "analysis_id") != _required(request, "analysis_id"):
            raise ValueError("PI_ANALYSIS_ID_MISMATCH")
        cutoff = _date(_required(request, "as_of"), "request.as_of")
        pi_observed_on = _date(_required(pi_delta, "portfolio_as_of"), "portfolio_as_of")
        if pi_observed_on > cutoff:
            raise ValueError("PI_OBSERVATION_NEWER_THAN_CUTOFF")
        room = _required(pi_delta, "room_status")
        if room not in ROOM_STATUSES:
            raise ValueError("INVALID_ROOM_STATUS")
        # No PI-only issuer facts, inherited research, optimized weights or
        # source-certified holdings can be silently created by this bridge.
        packet = {
            "kind": _required(request, "kind"),
            "analysis_id": _required(request, "analysis_id"),
            "as_of": cutoff,
            "strategy": handoffs["pi_request_private"]["strategy_id"],
            "method_version": handoffs["pi_request_private"]["method_version"],
            "status": "CONDITIONAL",
            "objective": _required(request, "objective"),
            "decision_line": "Portfolio-only interpretation; no independently verified investment or trading recommendation.",
            "summary": ["PI-reported, not independently verified: " + _required(pi_delta, "summary")],
            "facts": [],
            "countercase": "Invisible accounts, cash, currency or stale holdings may change this conclusion.",
            "limitations": ("PI-reported Portfolio Room: " + room + "; portfolio observed as of " + pi_observed_on +
                            ". Source and account coverage NOT authenticated by this assembler. " +
                            _required(pi_delta, "limitations")),
            "next_action": _required(pi_delta, "next_action"),
        }
        if packet["kind"] == "FOLLOWUP":
            packet["changes"] = []
            for key in ("prior_analysis_id", "period_start", "period_end"):
                if key in request:
                    packet[key] = request[key]
        private["final_report_private"] = render_report(packet)
        private["pi_delta_private"] = deepcopy(dict(pi_delta))
        private["status"] = "PI_ONLY_CONDITIONAL_REPORT_ASSEMBLED"
        return private

    base_request = {
        "analysis_id": _required(request, "analysis_id"),
        "as_of": _date(_required(request, "as_of"), "request.as_of"),
        "objective": _required(request, "objective"),
        "strategy_id": handoffs["ir_request_private"]["strategy_id"],
        "method_version": handoffs["ir_request_private"]["method_version"],
        "kind": _required(request, "kind"),
    }
    for optional in ("prior_analysis_id", "period_start", "period_end"):
        if optional in request:
            base_request[optional] = request[optional]
    integrated = assemble_manual_run(
        base_request, ir_capsule, pi_delta=pi_delta,
        calculation_requests=calculation_requests,
        contribution_inputs=contribution_inputs,
        cost_inputs=cost_inputs,
        memory_inputs=memory_inputs,
        source_evidence_inputs=source_evidence_inputs,
        valuation_inputs=valuation_inputs,
    )
    private["integrated_private"] = integrated
    private["final_report_private"] = integrated["markdown"]
    private["pi_delta_private"] = deepcopy(dict(pi_delta)) if pi_delta is not None else None
    private["status"] = "M7A_COMPONENT_ASSEMBLED_NOT_END_TO_END_ACCEPTANCE"
    return private
