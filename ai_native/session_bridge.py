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
from .strategy_return_parity import check_specialist_mode_echo
from .mode_portfolio_trace import prepare_mode_portfolio_trace
from .integrated_flow import assemble_manual_run
from .reporting import render_report
from .executive_report import render_executive_report
from .portfolio_observation import prepare_observation_ledger
from .portfolio_snapshot_comparison import compare_private_portfolio_snapshots
from .work_blossom_adapter import prepare_work_blossom_observation
from .public_portfolio_reference import (
    prepare_public_portfolio_reference, prepare_public_reference_from_work_table,
    render_public_portfolio_reference,
)
from .attested_visible_concentration import (
    prepare_attested_visible_concentration, render_attested_visible_concentration,
)
from .portfolio_exposure import aggregate_portfolio_exposures
from .portfolio_room import prepare_portfolio_room_review
from .new_capital_flow import prepare_new_capital_projection
from .contribution_observation import reconcile_observed_contribution_basis
from .exceptional_lifecycle import prepare_exceptional_lifecycle_review
from .high_cagr_destination_path import (
    prepare_high_cagr_destination_review, render_high_cagr_destination_review,
)
from .research_admission_evidence_map import (
    prepare_research_admission_evidence_map,
    render_research_admission_evidence_map,
)
from .scenario_session_integration import (
    prepare_scoped_scenario_review, render_scoped_scenario_lines,
)
from .method_return_receipt import (
    evaluate_returned_method_text, render_returned_method_receipt,
)

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
    scenario_weight_inputs: Mapping[str, Any] | None = None,
    memory_inputs: Mapping[str, Any] | None = None,
    method_return_receipts: Mapping[str, Any] | None = None,
    observation_inputs: Mapping[str, Any] | None = None,
    prior_portfolio_observation_inputs: Mapping[str, Any] | None = None,
    work_blossom_inputs: Mapping[str, Any] | None = None,
    public_reference_inputs: Mapping[str, Any] | None = None,
    public_reference_table_inputs: Mapping[str, Any] | None = None,
    public_scope_attestation_inputs: Mapping[str, Any] | None = None,
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
    lifecycle_inputs: Mapping[str, Any] | None = None,
    lifecycle_current_evidence_inputs: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """One CEO-initiated manual session, possibly awaiting a human transfer.

    IR route uses M7a unchanged; PI-only route renders a CONDITIONAL report
    because no original issuer research is supplied. No local or remote writes.
    """
    handoffs = prepare_manual_handoffs(request, ir_capsule=ir_capsule, portfolio_context=portfolio_context)
    route = handoffs["route"]
    if pi_delta is not None and not request["portfolio_needed"]:
        raise ValueError("PI_DELTA_UNREQUESTED")
    if method_return_receipts is not None:
        if (not isinstance(method_return_receipts, Mapping)
                or not method_return_receipts
                or set(method_return_receipts) - {"IR", "PI"}):
            raise ValueError("METHOD_RECEIPTS_ROLES_INVALID")
        if (("IR" in method_return_receipts
             and (route not in {"CC_IR_CC", "CC_IR_PI_CC"} or ir_capsule is None))
                or ("PI" in method_return_receipts
                    and (route not in {"CC_PI_CC", "CC_IR_PI_CC"} or pi_delta is None))):
            raise ValueError("METHOD_RECEIPT_REQUIRES_ACTUAL_SPECIALIST_PACKET")
    pi_mode_echo = None
    if pi_delta is not None:
        strategy_id = (
            handoffs["ir_request_private"]["strategy_id"]
            if handoffs["ir_request_private"] is not None
            else handoffs["pi_request_private"]["strategy_id"]
        )
        pi_mode_echo = check_specialist_mode_echo(strategy_id, pi_delta, specialist="PI")
    if (contribution_inputs is not None or cost_inputs is not None) and route not in {"CC_PI_CC", "CC_IR_PI_CC"}:
        raise ValueError("PORTFOLIO_ARITHMETIC_REQUIRES_PI_ROUTE")
    if cost_inputs is not None and contribution_inputs is None:
        raise ValueError("COST_INPUTS_REQUIRE_CONTRIBUTION_INPUTS")
    if scenario_weight_inputs is not None and (
            route not in {"CC_PI_CC", "CC_IR_PI_CC"} or pi_delta is None):
        raise ValueError("SCENARIO_REVIEW_REQUIRES_COMPLETED_PI_ROUTE")
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

    if lifecycle_inputs is not None and (route != "CC_IR_PI_CC" or pi_delta is None):
        raise ValueError("LIFECYCLE_REQUIRES_COMPLETED_IR_PI_ROUTE")
    if lifecycle_current_evidence_inputs is not None and lifecycle_inputs is None:
        raise ValueError("LIFECYCLE_CURRENT_EVIDENCE_REQUIRES_REVIEW")
    if (request.get("exceptional_lifecycle_review_requested") is True
            and pi_delta is not None and lifecycle_inputs is None):
        raise ValueError("LIFECYCLE_REQUESTED_REVIEW_NOT_SUPPLIED")
    if room_assessment_inputs is not None and route != "CC_IR_PI_CC":
        raise ValueError("PORTFOLIO_ROOM_REQUIRES_IR_AND_PI_ROUTE")
    if prior_portfolio_observation_inputs is not None:
        if route not in {"CC_PI_CC", "CC_IR_PI_CC"} or request.get("kind") != "FOLLOWUP":
            raise ValueError("SNAPSHOT_COMPARISON_REQUIRES_EXPLICIT_PI_FOLLOWUP")
        if not isinstance(request.get("prior_analysis_id"), str):
            raise ValueError("SNAPSHOT_COMPARISON_PRIOR_ANALYSIS_REQUIRED")

    # Publicly observed profile holdings are RESEARCH REFERENCE only, not PI,
    # never M3 private P-ledger or Portfolio Room. Work output is separately
    # transferred by the CEO; no web access, automatic research or ownership
    # authority. Do not let any PI inputs silently mix into this route.
    public_reference = None
    public_reference_report = None
    public_scope_review = None
    if (public_scope_attestation_inputs is not None
            and public_reference_inputs is None
            and public_reference_table_inputs is None):
        raise ValueError("ATTESTED_VIEW_REQUIRES_PUBLIC_REFERENCE")
    if public_reference_inputs is not None and public_reference_table_inputs is not None:
        raise ValueError("PUBLIC_REFERENCE_AMBIGUOUS_SOURCE_FORMAT")
    if public_reference_inputs is not None or public_reference_table_inputs is not None:
        if route not in {"CC_DIRECT", "CC_IR_CC"}:
            raise ValueError("PUBLIC_REFERENCE_ONLY_CC_OR_IR_ROUTE")
        if (pi_delta is not None or observation_inputs is not None
                or work_blossom_inputs is not None
                or portfolio_context is not None or contribution_inputs is not None
                or cost_inputs is not None or exposure_classifications is not None
                or room_assessment_inputs is not None
                or prior_portfolio_observation_inputs is not None):
            raise ValueError("PUBLIC_REFERENCE_CANNOT_BECOME_PRIVATE_PORTFOLIO")
        case_identity = {
            "analysis_id": _required(request, "analysis_id"),
            "analysis_as_of": _date(_required(request, "as_of"), "request.as_of"),
        }
        if public_reference_table_inputs is not None:
            public_reference = prepare_public_reference_from_work_table(
                public_reference_table_inputs, **case_identity)
        else:
            public_reference = prepare_public_portfolio_reference(
                public_reference_inputs, **case_identity)
        public_reference_report = render_public_portfolio_reference(public_reference)
        if public_scope_attestation_inputs is not None:
            public_scope_review = prepare_attested_visible_concentration(
                public_reference, public_scope_attestation_inputs)
            public_reference_report += "\n\n" + render_attested_visible_concentration(
                public_scope_review)
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

    scenario_review = None
    if scenario_weight_inputs is not None:
        scenario_review = prepare_scoped_scenario_review(
            request=request, pi_delta=pi_delta, observation=observation,
            scenario_weight_inputs=scenario_weight_inputs,
        )

    snapshot_comparison = None
    if prior_portfolio_observation_inputs is not None:
        if observation is None:
            raise ValueError("SNAPSHOT_COMPARISON_REQUIRES_CURRENT_PRIVATE_OBSERVATION")
        snapshot_comparison = compare_private_portfolio_snapshots(
            analysis_id=_required(request, "analysis_id"),
            analysis_as_of=_date(_required(request, "as_of"), "request.as_of"),
            prior_analysis_id=_required(request, "prior_analysis_id"),
            current_observation=observation,
            prior_observation_inputs=prior_portfolio_observation_inputs,
        )

    # Reuse the actual dated PRIVATE P-ledger as the complete new-capital
    # denominator when requested; reject independently retyped values that
    # disagree, including omitted visible cash. Both manual routes share it.
    # The ledger remains caller-reported, never account/source authenticated.
    if observation is not None and contribution_inputs is not None:
        contribution_inputs = reconcile_observed_contribution_basis(
            observation, contribution_inputs
        )

    exposures = None
    if exposure_classifications is not None:
        if observation is None:
            raise ValueError("EXPOSURES_REQUIRE_PI_OBSERVATION")
        exposures = aggregate_portfolio_exposures(
            observation, classifications_by_p_id=exposure_classifications
        )
        if (pi_delta is not None and pi_delta.get("room_status") == "ROOM_EVIDENCE_SUPPORTED"
                and (exposures["status"] != "CALLER_REPORTED_SCOPED_EXPOSURES"
                     or exposures.get("fund_composition_date_alignment") ==
                        "PRIOR_DATED_FUND_SNAPSHOTS")):
            raise ValueError("ROOM_ASSERTION_UNSUPPORTED_BY_PARTIAL_LOOKTHROUGH")

    # Carry the already-validated PRIVATE P-ledger in the existing manual PI
    # handoff. Previously the Work adapter produced a local ledger but the
    # copy-ready PI_REQUEST omitted it, requiring an unaudited second transcription.
    # Never turn an observed public profile into a private account packet.
    if observation is not None:
        if observation.get("private_scope") is not True:
            raise ValueError("PUBLIC_OBSERVATION_CANNOT_BECOME_PRIVATE_PI")
        if portfolio_context is not None:
            for context_field, observation_field in (
                ("observed_at", "observed_on"),
                ("account_scope", "account_scope"),
            ):
                stated = portfolio_context.get(context_field)
                if stated not in (None, "UNKNOWN", observation[observation_field]):
                    raise ValueError("PI_CONTEXT_CONFLICTS_WITH_OBSERVED_P_LEDGER")
        pi_request = handoffs["pi_request_private"]
        if pi_request is not None:
            pi_request["P_LEDGER_FOR_REVIEW_PRIVATE"] = deepcopy(observation)
            pi_request["P_LEDGER_HANDOFF_AUTHORITY"] = (
                "CALLER_REPORTED_PRIVATE_OBSERVATION_MANUAL_REVIEW_ONLY"
            )
            if contribution_inputs is not None:
                # Reuse the SAME CC gross/cost/funding calculation that the
                # final report will recompute after real PI returns. Previously
                # PI received the dated P-ledger but never saw the requested
                # NEW-cash percentage scenario it was expected to review.
                # Expose only the existing bounded, amount-free summary to
                # the authorized PI Project, not raw private costs, balances,
                # share counts, quotes, or a policy-generated allocation.
                pre_pi = prepare_new_capital_projection(
                    analysis_id=_required(request, "analysis_id"),
                    analysis_as_of=_date(_required(request, "as_of"), "request.as_of"),
                    portfolio_as_of=observation["observed_on"],
                    contribution_inputs=contribution_inputs,
                    cost_inputs=cost_inputs,
                )
                if (pre_pi.get("execution_status") !=
                        "UNAVAILABLE_NOT_EXECUTION_CERTIFIED"
                        or pre_pi.get("storage") != "NONE"):
                    raise ValueError("PI_CONTRIBUTION_PREVIEW_AUTHORITY_INVALID")
                pi_request["NEW_CAPITAL_FOR_REVIEW_PRIVATE"] = {
                    "status": "CALLER_SUPPLIED_SCENARIO_NOT_ALLOCATION_POLICY",
                    "analysis_id": _required(request, "analysis_id"),
                    "portfolio_observed_on": observation["observed_on"],
                    "new_capital_summary_private": deepcopy(
                        pre_pi["report_summary_private"]),
                    "limitations": list(pre_pi["limitations"]),
                    "source_authentication": "NOT_PERFORMED",
                    "policy_or_trade_authority": "NONE",
                    "next_action": (
                        "Review the caller-supplied percentages against dated "
                        "holdings, account limitations and known/UNKNOWN costs; "
                        "return PI_DELTA, not an order or endorsed allocation."
                    ),
                }
            handoffs["copy_ready_private"]["PI_REQUEST"] = json.dumps(
                pi_request, ensure_ascii=False, sort_keys=True,
                indent=2, allow_nan=False,
            )

    private = {"status": "MANUAL_SESSION_PENDING", "route": route,
               "handoffs_private": handoffs, "final_report_private": None,
               "executive_report_private": None,
               "integrated_private": None, "pi_delta_private": None,
               "portfolio_observation_private": observation,
               "portfolio_snapshot_comparison_private": snapshot_comparison,
               "work_blossom_capture_private": visual_capture,
               "public_reference_private": public_reference,
               "public_reference_report_private": public_reference_report,
               "public_scope_attested_concentration_private": public_scope_review,
               "portfolio_exposures_private": exposures,
               "portfolio_room_review_private": None,
               "exceptional_lifecycle_review_private": None,
               "gross_contribution_private": None,
               "supplied_costs_private": None,
               "funded_contribution_private": None,
               "alternative_cost_details_private": None,
               "scenario_weight_sensitivity_private": scenario_review,
               "method_load_verification": "NOT_PERFORMED", "project_invocation": "NONE",
               "source_authentication": "NOT_PERFORMED", "storage": "NONE",
               "readiness": "NOT_EVALUATED",
               "mode_portfolio_trace_private": None,
               "specialist_mode_echo": {
                   "IR": handoffs["ir_strategy_mode_echo"], "PI": pi_mode_echo,
               }}

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

    # F4 checks the returned method TEXT, not merely a specialist SHA claim.
    # No raw method bytes are included in output, memory, or reports.
    method_review = None
    method_report = None
    if method_return_receipts is not None:
        method_review = {
            role: evaluate_returned_method_text(
                request=request, specialist=role, receipt=receipt)
            for role, receipt in method_return_receipts.items()
        }
        private["method_return_receipts_private"] = method_review
        method_report = "\n\n".join(
            render_returned_method_receipt(method_review[role])
            for role in ("IR", "PI") if role in method_review
        )

    # Test #3 F1: visible company research alone cannot justify skipping VFV.
    # Report all three original High-CAGR branches without promoting evidence
    # or choosing an investment. All other mode reports stay unchanged.
    capital_path = None
    if (route in {"CC_IR_PI_CC", "CC_PI_CC"}
            and request.get("strategy_id") == "high-cagr"):
        capital_path = prepare_high_cagr_destination_review(
            request=request, ir_capsule=ir_capsule, pi_delta=pi_delta)
        private["high_cagr_destination_review_private"] = capital_path

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
        mode_portfolio_trace = prepare_mode_portfolio_trace(
            request=request, pi_delta=pi_delta, observation=observation
        )
        private["mode_portfolio_trace_private"] = mode_portfolio_trace
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
                            _required(pi_delta, "limitations") +
                            " PI mode echo: " + pi_mode_echo +
                            "; no independent specialist authentication."),
            "next_action": _required(pi_delta, "next_action"),
        }
        if contribution_inputs is not None:
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
            private["alternative_cost_details_private"] = bundle["alternative_cost_details_private"]
        if snapshot_comparison is not None:
            packet["portfolio_snapshot_comparison_private"] = snapshot_comparison
            packet["limitations"] += (
                " Prior/current portfolio snapshots are caller-reported; "
                "weight shifts cannot establish security returns, capital "
                "flows, transactions or household-wide exposure.")
        if packet["kind"] == "FOLLOWUP":
            packet["changes"] = []
            for key in ("prior_analysis_id", "period_start", "period_end"):
                if key in request:
                    packet[key] = request[key]
        if observation is not None:
            packet["portfolio_observation_private"] = observation
        if exposures is not None:
            packet["portfolio_exposures_private"] = exposures
        if mode_portfolio_trace is not None:
            packet["mode_portfolio_trace_private"] = mode_portfolio_trace
            packet["limitations"] += " PI mode questions are specialist-reported and not independently authenticated."
        private["final_report_private"] = render_report(packet)
        if method_report is not None:
            private["final_report_private"] += "\n\n" + method_report
        if capital_path is not None:
            private["final_report_private"] += "\n\n" + render_high_cagr_destination_review(capital_path)
        if scenario_review is not None:
            private["final_report_private"] += "\n\n" + render_scoped_scenario_lines(scenario_review)
        private["executive_report_private"] = render_executive_report(
            packet, detailed_report=private["final_report_private"],
            portfolio_room_status=room)
        private["pi_delta_private"] = deepcopy(dict(pi_delta))
        private["status"] = "PI_ONLY_CONDITIONAL_REPORT_ASSEMBLED"
        return private

    if lifecycle_inputs is not None:
        if observation is None:
            raise ValueError("LIFECYCLE_REQUIRES_PRIVATE_DATED_OBSERVATION")
        private["exceptional_lifecycle_review_private"] = prepare_exceptional_lifecycle_review(
            request, ir_capsule, pi_delta, observation, lifecycle_inputs,
            current_evidence_inputs=lifecycle_current_evidence_inputs,
        )

    base_request = {
        # Preserve the two previously validated CEO/IR route attestations in
        # the compact private research-history proposal. Without these, the
        # later on-demand follow-up validator rejects this same exported case.
        # Do NOT carry prior private account/holdings/fees into history.
        "ceo_initiated": True,
        "research_needed": True,
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
        portfolio_observation_private=observation,
        portfolio_snapshot_comparison_private=snapshot_comparison,
        portfolio_exposures_private=exposures,
        exceptional_lifecycle_review_private=private["exceptional_lifecycle_review_private"],
    )
    private["integrated_private"] = integrated
    # PI-only and IR+PI expose the same strictly private deterministic M3
    # outputs; the short CC report still omits actual balances and costs.
    private["gross_contribution_private"] = integrated.get("gross_contribution_private")
    private["supplied_costs_private"] = integrated.get("supplied_costs_private")
    private["funded_contribution_private"] = integrated.get("funded_contribution_private")
    private["alternative_cost_details_private"] = integrated.get("alternative_cost_details_private")
    # Old IR-only or IR+PI returns with no optional question answers are
    # supported. A specialist-supplied answer, however, may not vanish from
    # M7a even if an intermediate key exists with a null or unrelated value.
    if "MODE_RESEARCH_RESPONSES" in ir_capsule:
        ir_trace = integrated.get("mode_research_trace_private")
        if (not isinstance(ir_trace, Mapping)
                or ir_trace.get("status") != "PRIVATE_MODE_RESEARCH_TRACE_NOT_CERTIFIED"
                or ir_trace.get("analysis_id") != base_request["analysis_id"]
                or ir_trace.get("analysis_as_of") != base_request["as_of"]
                or ir_trace.get("research_as_of") != ir_capsule.get("research_as_of")
                or ir_trace.get("strategy_id") != base_request["strategy_id"]
                or not isinstance(ir_trace.get("questions_private"), list)
                or not ir_trace["questions_private"]):
            raise ValueError("MODE_IR_TRACE_NOT_RETURNED_BY_INTEGRATION")
    if pi_delta is not None and "MODE_PORTFOLIO_RESPONSES" in pi_delta:
        pi_trace = integrated.get("mode_portfolio_trace_private")
        if (not isinstance(pi_trace, Mapping)
                or pi_trace.get("status") != "PRIVATE_MODE_PI_TRACE_NOT_AUTHENTICATED"
                or pi_trace.get("analysis_id") != base_request["analysis_id"]
                or pi_trace.get("analysis_as_of") != base_request["as_of"]
                or pi_trace.get("portfolio_as_of") != pi_delta.get("portfolio_as_of")
                or pi_trace.get("strategy_id") != base_request["strategy_id"]
                or not isinstance(pi_trace.get("questions_private"), list)
                or not pi_trace["questions_private"]):
            raise ValueError("MODE_PI_TRACE_NOT_RETURNED_BY_INTEGRATION")
    private["mode_portfolio_trace_private"] = integrated.get("mode_portfolio_trace_private")
    if method_report is not None:
        integrated["method_return_receipts_private"] = method_review
        integrated["markdown"] += "\n\n" + method_report
        integrated["executive_markdown"] += "\n\n" + method_report
    # Third CEO test F3: read the ALREADY assembled source, economics,
    # valuation, mode and PI stages. Never promote research to admission.
    admission_review = prepare_research_admission_evidence_map(
        request=base_request, ir_capsule=ir_capsule, integrated=integrated)
    admission_lines = render_research_admission_evidence_map(admission_review)
    private["research_admission_evidence_map_private"] = admission_review
    integrated["research_admission_evidence_map_private"] = admission_review
    integrated["markdown"] += "\n\n" + admission_lines
    integrated["executive_markdown"] += "\n\n" + admission_lines
    if public_reference is not None:
        # Public profile observation remains separate from the IR model's
        # facts/pillars and the unchanged private institutional memory proposal.
        integrated["public_reference_private"] = public_reference
        integrated["public_reference_report_private"] = public_reference_report
        integrated["markdown"] += "\n\n" + public_reference_report
    if capital_path is not None:
        capital_lines = render_high_cagr_destination_review(capital_path)
        integrated["high_cagr_destination_review_private"] = capital_path
        integrated["markdown"] += "\n\n" + capital_lines
        integrated["executive_markdown"] += "\n\n" + capital_lines
    if scenario_review is not None:
        scenario_lines = render_scoped_scenario_lines(scenario_review)
        integrated["scenario_weight_sensitivity_private"] = scenario_review
        integrated["markdown"] += "\n\n" + scenario_lines
        # Append once after the original executive+annex rendering. This
        # keeps the original investment summary and its validity intact.
        integrated["executive_markdown"] += "\n\n" + scenario_lines
    private["final_report_private"] = integrated["markdown"]
    private["executive_report_private"] = integrated["executive_markdown"]
    private["pi_delta_private"] = deepcopy(dict(pi_delta)) if pi_delta is not None else None
    private["status"] = "M7A_COMPONENT_ASSEMBLED_NOT_END_TO_END_ACCEPTANCE"
    return private
