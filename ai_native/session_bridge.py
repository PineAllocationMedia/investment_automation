"""Bridge M1 manual handoffs to M7a reporting with no Project invocation.

All output is PRIVATE. This only routes caller-provided packets and retains
unknowns; no source authentication, brokerage access, archiving or trades.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import json
from typing import Any, Mapping

from .request_assembly import prepare_manual_handoffs
from .integrated_flow import assemble_manual_run
from .reporting import render_report
from .portfolio_observation import prepare_observation_ledger
from .work_blossom_adapter import prepare_work_blossom_observation
from .public_portfolio_reference import (
    prepare_public_portfolio_reference, render_public_portfolio_reference,
)
from .portfolio_exposure import aggregate_portfolio_exposures
from .portfolio_room import prepare_portfolio_room_review
from .new_capital_flow import prepare_new_capital_projection

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
    work_blossom_inputs: Mapping[str, Any] | None = None,
    public_reference_inputs: Mapping[str, Any] | None = None,
    exposure_classifications: Mapping[str, Any] | None = None,
    room_assessment_inputs: Mapping[str, Any] | None = None,
    source_evidence_inputs: Mapping[str, Any] | None = None,
    valuation_inputs: Mapping[str, Any] | None = None,
    probability_inputs: Mapping[str, Any] | None = None,
    candidate_comparison_inputs: Mapping[str, Any] | None = None,
    fundamental_inputs: Mapping[str, Any] | None = None,
    historical_comparison_inputs: Mapping[str, Any] | None = None,
    opportunity_triage_inputs: Mapping[str, Any] | None = None,
    macro_sector_inputs: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """One CEO-initiated manual session, possibly awaiting a human transfer.

    IR route uses M7a unchanged; PI-only route renders a CONDITIONAL report
    because no original issuer research is supplied. No local or remote writes.
    """
    handoffs = prepare_manual_handoffs(request, ir_capsule=ir_capsule, portfolio_context=portfolio_context)
    route = handoffs["route"]
    if pi_delta is not None and not request["portfolio_needed"]:
        raise ValueError("PI_DELTA_UNREQUESTED")
    if (contribution_inputs is not None or cost_inputs is not None) and route not in {"CC_PI_CC", "CC_IR_PI_CC"}:
        raise ValueError("PORTFOLIO_ARITHMETIC_REQUIRES_PI_ROUTE")
    if cost_inputs is not None and contribution_inputs is None:
        raise ValueError("COST_INPUTS_REQUIRE_CONTRIBUTION_INPUTS")
    if memory_inputs is not None and route not in {"CC_IR_CC", "CC_IR_PI_CC"}:
        raise ValueError("MEMORY_PACKET_REQUIRES_IR_CAPSULE")
    if calculation_requests is not None and route not in {"CC_IR_CC", "CC_IR_PI_CC"}:
        raise ValueError("FINANCIAL_CHECKS_REQUIRE_IR_CAPSULE")
    if source_evidence_inputs is not None and route not in {"CC_IR_CC", "CC_IR_PI_CC"}:
        raise ValueError("SOURCE_ANNEX_REQUIRES_IR_CAPSULE")
    if probability_inputs is not None and (route not in {"CC_IR_CC", "CC_IR_PI_CC"} or valuation_inputs is None):
        raise ValueError("PROBABILITY_CASHFLOWS_REQUIRE_IR_VALUATION")
    if valuation_inputs is not None and route not in {"CC_IR_CC", "CC_IR_PI_CC"}:
        raise ValueError("VALUATION_REQUIRES_IR_CAPSULE")
    if candidate_comparison_inputs is not None and route not in {"CC_IR_CC", "CC_IR_PI_CC"}:
        raise ValueError("CANDIDATE_COMPARISON_REQUIRES_IR_CAPSULE")
    if fundamental_inputs is not None and route not in {"CC_IR_CC", "CC_IR_PI_CC"}:
        raise ValueError("FUNDAMENTAL_REQUIRES_IR_CAPSULE")
    if historical_comparison_inputs is not None and route not in {"CC_IR_CC", "CC_IR_PI_CC"}:
        raise ValueError("HISTORICAL_COMPARISON_REQUIRES_IR_ROUTE")
    if opportunity_triage_inputs is not None and route not in {"CC_IR_CC", "CC_IR_PI_CC"}:
        raise ValueError("OPPORTUNITY_TRIAGE_REQUIRES_IR_ROUTE")
    if macro_sector_inputs is not None and route not in {"CC_IR_CC", "CC_IR_PI_CC"}:
        raise ValueError("MACRO_SECTOR_REQUIRES_IR_ROUTE")

    if room_assessment_inputs is not None and route != "CC_IR_PI_CC":
        raise ValueError("PORTFOLIO_ROOM_REQUIRES_IR_AND_PI_ROUTE")

    # Publicly observed profile holdings are RESEARCH REFERENCE only, not PI,
    # never M3 private P-ledger or Portfolio Room. Work output is separately
    # transferred by the CEO; no web access, automatic research or ownership
    # authority. Do not let any PI inputs silently mix into this route.
    public_reference = None
    public_reference_report = None
    if public_reference_inputs is not None:
        if route not in {"CC_DIRECT", "CC_IR_CC"}:
            raise ValueError("PUBLIC_REFERENCE_ONLY_CC_OR_IR_ROUTE")
        if (pi_delta is not None or observation_inputs is not None
                or work_blossom_inputs is not None
                or portfolio_context is not None or contribution_inputs is not None
                or cost_inputs is not None or exposure_classifications is not None
                or room_assessment_inputs is not None):
            raise ValueError("PUBLIC_REFERENCE_CANNOT_BECOME_PRIVATE_PORTFOLIO")
        public_reference = prepare_public_portfolio_reference(
            public_reference_inputs,
            analysis_id=_required(request, "analysis_id"),
            analysis_as_of=_date(_required(request, "as_of"), "request.as_of"),
        )
        public_reference_report = render_public_portfolio_reference(public_reference)
        if route == "CC_IR_CC":
            # Portable manual IR request only; never self-invoke a Project.
            # Keep the source values marked as a reference, not IR-verified.
            ir_request = handoffs["ir_request_private"]
            ir_request["public_reference_context"] = {
                "status": "CALLER_REPORTED_REFERENCE_NOT_SOURCE_AUTHENTICATED",
                "analysis_id": public_reference["analysis_id"],
                "analysis_as_of": public_reference["analysis_as_of"],
                "observation_as_of": public_reference["observation_as_of"],
                "visibility_context": public_reference["visibility_context"],
                "positions_visible": [
                    {"security_id": row["security_id"],
                     "displayed_weight_pct": row["weight_pct"]}
                    for row in public_reference["positions_private"]
                ],
                "limits": list(public_reference["missing_or_qualified"]),
                "task": ("Research only the explicit visible securities and "
                         "investigate apparent overlaps with actual dated source "
                         "evidence; do not assume these are the CEO's holdings, "
                         "certify public accessibility, recommend trades or infer "
                         "complete fund composition."),
            }
            handoffs["copy_ready_private"]["IR_REQUEST"] = json.dumps(
                ir_request, ensure_ascii=False, sort_keys=True, indent=2,
                allow_nan=False,
            )

    # Existing Work/screenshot adapter is a user-controlled MANUAL source,
    # not a way to invoke Work or infer that the real Blossom view was seen.
    visual_capture = None
    if work_blossom_inputs is not None:
        if route not in {"CC_PI_CC", "CC_IR_PI_CC"}:
            raise ValueError("WORK_BLOSSOM_REQUIRES_PI_ROUTE")
        if observation_inputs is not None:
            raise ValueError("AMBIGUOUS_PORTFOLIO_OBSERVATION_INPUTS")
        if not isinstance(work_blossom_inputs, Mapping):
            raise ValueError("WORK_BLOSSOM_INPUT_MAPPING_REQUIRED")
        # The adapter intentionally short-circuits inaccessible views. Enforce
        # analysis identity *before* it can return the fallback status.
        if (work_blossom_inputs.get("analysis_id") != request.get("analysis_id")
                or work_blossom_inputs.get("analysis_as_of") != request.get("as_of")):
            raise ValueError("WORK_BLOSSOM_ANALYSIS_ID_OR_DATE_MISMATCH")
        visual_capture = prepare_work_blossom_observation(work_blossom_inputs)
        if visual_capture["status"] == "PRIVATE_OBSERVATION_PACKET_PREPARED_NOT_SENT":
            observation_inputs = visual_capture["observation_inputs_private"]
        elif visual_capture["status"] != "VISUAL_SOURCE_UNAVAILABLE_USE_SCREENSHOT_FALLBACK":
            raise ValueError("WORK_BLOSSOM_ADAPTER_STATUS_INVALID")

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
        if visual_capture is not None and observation != visual_capture["p_ledger_private"]:
            raise ValueError("WORK_BLOSSOM_LEDGER_PARITY_MISMATCH")
        if pi_delta is not None and observation["observed_on"] != pi_delta.get("portfolio_as_of"):
            raise ValueError("OBSERVATION_PI_DATE_MISMATCH")
        if (pi_delta is not None and pi_delta.get("room_status") == "ROOM_EVIDENCE_SUPPORTED"
                and observation["known_scope_weights_pct"] is None):
            raise ValueError("UNSUPPORTED_PORTFOLIO_ROOM_ASSERTION: incomplete observation")

    exposures = None
    if exposure_classifications is not None:
        if observation is None:
            raise ValueError("EXPOSURES_REQUIRE_PI_OBSERVATION")
        exposures = aggregate_portfolio_exposures(
            observation, classifications_by_p_id=exposure_classifications
        )
        if (pi_delta is not None and pi_delta.get("room_status") == "ROOM_EVIDENCE_SUPPORTED"
                and exposures["status"] != "CALLER_REPORTED_SCOPED_EXPOSURES"):
            raise ValueError("ROOM_ASSERTION_UNSUPPORTED_BY_PARTIAL_LOOKTHROUGH")

    private = {"status": "MANUAL_SESSION_PENDING", "route": route,
               "handoffs_private": handoffs, "final_report_private": None,
               "integrated_private": None, "pi_delta_private": None,
               "portfolio_observation_private": observation,
               "work_blossom_capture_private": visual_capture,
               "public_reference_private": public_reference,
               "public_reference_report_private": public_reference_report,
               "portfolio_exposures_private": exposures,
               "portfolio_room_review_private": None,
               "gross_contribution_private": None,
               "supplied_costs_private": None,
               "funded_contribution_private": None,
               "method_load_verification": "NOT_PERFORMED", "project_invocation": "NONE",
               "source_authentication": "NOT_PERFORMED", "storage": "NONE",
               "readiness": "NOT_EVALUATED"}

    if route == "CC_DIRECT":
        if public_reference is not None:
            private["status"] = "PUBLIC_REFERENCE_DESCRIPTIVE_REPORT_READY"
            private["final_report_private"] = public_reference_report
        else:
            private["status"] = "CC_DIRECT_NO_SPECIALIST_REPORT_REQUIRED"
        return private
    if route in {"CC_IR_CC", "CC_IR_PI_CC"} and ir_capsule is None:
        private["status"] = "AWAITING_MANUAL_IR_CAPSULE"
        return private
    if (visual_capture is not None
            and visual_capture["status"] == "VISUAL_SOURCE_UNAVAILABLE_USE_SCREENSHOT_FALLBACK"):
        # The inaccessible Work view cannot justify portfolio claims, even
        # when a PI_DELTA was independently typed into the same request.
        if pi_delta is not None:
            raise ValueError("WORK_BLOSSOM_UNAVAILABLE_CONFLICTS_WITH_PI_DELTA")
        private["status"] = "AWAITING_MANUAL_PORTFOLIO_SCREENSHOT"
        return private
    if room_assessment_inputs is not None:
        if observation is None or exposures is None:
            raise ValueError("PORTFOLIO_ROOM_REQUIRES_SCOPED_OBSERVATION_AND_EXPOSURES")
        if not isinstance(room_assessment_inputs, Mapping):
            raise ValueError("room_assessment_inputs: mapping required")
        room_review = prepare_portfolio_room_review(
            request, ir_capsule, observation, exposures, room_assessment_inputs
        )
        private["portfolio_room_review_private"] = room_review
        if (pi_delta is not None and pi_delta.get("room_status") == "ROOM_EVIDENCE_SUPPORTED"):
            raise ValueError("ROOM_SUPPORTED_NOT_CERTIFIED_BY_REPORTED_REVIEW")

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
        if contribution_inputs is not None:
            if (observation is not None
                    and observation.get("known_scope_weights_pct") is None
                    and contribution_inputs.get("scope_complete") is True):
                raise ValueError("PI_CONTRIBUTION_SCOPE_CONFLICTS_WITH_OBSERVATION")
            bundle = prepare_new_capital_projection(
                analysis_id=packet["analysis_id"], analysis_as_of=cutoff,
                portfolio_as_of=pi_observed_on,
                contribution_inputs=contribution_inputs, cost_inputs=cost_inputs,
            )
            packet["new_contribution_summary_private"] = bundle["report_summary_private"]
            packet["limitations"] += " " + " ".join(bundle["limitations"])
            private["gross_contribution_private"] = bundle["gross_contribution_private"]
            private["supplied_costs_private"] = bundle["supplied_costs_private"]
            private["funded_contribution_private"] = bundle["funded_contribution_private"]
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
    for optional in ("prior_analysis_id", "period_start", "period_end", "subject_id"):
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
        probability_inputs=probability_inputs,
        candidate_comparison_inputs=candidate_comparison_inputs,
        fundamental_inputs=fundamental_inputs,
        historical_comparison_inputs=historical_comparison_inputs,
        opportunity_triage_inputs=opportunity_triage_inputs,
        macro_sector_inputs=macro_sector_inputs,
        portfolio_room_review_private=private["portfolio_room_review_private"],
    )
    private["integrated_private"] = integrated
    if public_reference is not None:
        # Public profile observation remains separate from the IR model's
        # facts/pillars and the unchanged private institutional memory proposal.
        integrated["public_reference_private"] = public_reference
        integrated["public_reference_report_private"] = public_reference_report
        integrated["markdown"] += "\n\n" + public_reference_report
    private["final_report_private"] = integrated["markdown"]
    private["pi_delta_private"] = deepcopy(dict(pi_delta)) if pi_delta is not None else None
    private["status"] = "M7A_COMPONENT_ASSEMBLED_NOT_END_TO_END_ACCEPTANCE"
    return private
