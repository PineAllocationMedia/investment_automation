"""Prepare CEO-initiated, copy-ready CC/IR/PI requests without invoking Projects.

This pure constructor does not choose an investment strategy, certify methods,
inspect holdings, fetch sources, persist evidence, or perform financial research.
Its output is PRIVATE: the user must manually carry each supported handoff.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import json
from typing import Any, Mapping

from .strategy_authority import assess_r1_mode
from .mandate_context import prepare_mandate_context
from .strategy_research_brief import prepare_strategy_research_brief
from .mode_response_template import prepare_mode_response_template
from .strategy_return_parity import check_specialist_mode_echo
from .method_manifest import prepare_method_manifest

IR_METHODS = ("SOURCE_FUSION_R1", "VALUATION_R1")
PI_METHODS = ("OBSERVATION_AND_ROOM_R1", "CONTRIBUTIONS_AND_COSTS_R1", "LIFECYCLE_AND_HANDOFF_R1")


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}: nonempty string required")
    return value.strip()


def _date(value: Any, name: str) -> str:
    s = _text(value, name)
    try:
        parsed = date.fromisoformat(s)
    except ValueError as exc:
        raise ValueError(f"{name}: ISO date required") from exc
    if parsed.isoformat() != s:
        raise ValueError(f"{name}: canonical ISO date required")
    return s


def _optional_text(m: Mapping[str, Any], key: str, default: str = "UNKNOWN") -> str:
    if key not in m or m[key] is None:
        return default
    return _text(m[key], key)


def _json_copy(value: Any, field: str) -> Any:
    """Reject objects that cannot be faithfully carried as portable JSON."""
    try:
        encoded = json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True)
        decoded = json.loads(encoded)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"{field}: portable JSON values required") from exc
    if decoded != value:
        raise ValueError(f"{field}: non-JSON types or key coercion would alter packet")
    return decoded


def prepare_manual_handoffs(
    request: Mapping[str, Any], *,
    ir_capsule: Mapping[str, Any] | None = None,
    portfolio_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return portable, private handoffs selected by explicit CEO request flags.

    If IR is requested before PI, PI transfer is withheld until the original
    complete IR capsule is supplied. The packet is then forwarded exactly once.
    Method names are suggestions to load, NOT claims that methods were loaded.
    """
    if not isinstance(request, Mapping):
        raise ValueError("request: mapping required")
    if request.get("ceo_initiated") is not True:
        raise ValueError("CEO_INITIATION_REQUIRED: explicit caller assertion required")
    for flag in ("research_needed", "portfolio_needed"):
        if type(request.get(flag)) is not bool:
            raise ValueError(f"{flag}: explicit boolean required")
    analysis_id = _text(request.get("analysis_id"), "analysis_id")
    as_of = _date(request.get("as_of"), "as_of")
    objective = _text(request.get("objective"), "objective")
    kind = _text(request.get("kind"), "kind")
    if kind not in {"DECISION", "FOLLOWUP"}:
        raise ValueError("kind: DECISION or FOLLOWUP required")
    need_ir, need_pi = request["research_needed"], request["portfolio_needed"]
    if ir_capsule is not None and not need_ir:
        raise ValueError("IR_CAPSULE_UNREQUESTED: set research_needed or omit capsule")
    if portfolio_context is not None and not need_pi:
        raise ValueError("PORTFOLIO_CONTEXT_UNREQUESTED: set portfolio_needed or omit context")
    if ir_capsule is not None and not isinstance(ir_capsule, Mapping):
        raise ValueError("ir_capsule: mapping required")
    if portfolio_context is not None and not isinstance(portfolio_context, Mapping):
        raise ValueError("portfolio_context: mapping required")
    risk = request.get("risk_constraints", [])
    if not isinstance(risk, list) or any(not isinstance(x, str) or not x.strip() for x in risk):
        raise ValueError("risk_constraints: list of nonempty strings required")
    selected_strategy = _optional_text(request, "strategy_id", "EXPLORATORY")
    mode_gate = assess_r1_mode(selected_strategy)
    mandate_context = prepare_mandate_context(request)
    strategy_brief = prepare_strategy_research_brief(selected_strategy)
    ir_mode_echo = (
        check_specialist_mode_echo(selected_strategy, ir_capsule, specialist="IR")
        if ir_capsule is not None else None
    )
    context = {
        "analysis_id": analysis_id,
        "kind": kind,
        "as_of": as_of,
        "objective": objective,
        "strategy_id": selected_strategy,
        "r1_strategy_policy_authority": mode_gate["policy_authority"],
        "r1_strategy_method_load": mode_gate["method_load"],
        "r1_strategy_policy_limitation": mode_gate["limitation"],
        "strategy_authority": "CALLER_SUPPLIED_NOT_INDEPENDENTLY_VERIFIED",
        "mandate_context_private": mandate_context,
        "horizon": _optional_text(request, "horizon"),
        "benchmark": _optional_text(request, "benchmark"),
        "candidate_universe": _optional_text(request, "candidate_universe"),
        "risk_constraints": list(risk),
        "account_context_private": _json_copy(request.get("account_context", {}), "account_context"),
        "cc_instruction_version": _optional_text(request, "cc_instruction_version", "UNKNOWN_NOT_LOADED"),
        "privacy": "PRIVATE_MANUAL_TRANSFER_ONLY",
        "source_authentication": "NOT_PERFORMED_BY_ASSEMBLER",
    }
    # This entry is also used by a simple CC-direct route; do not force IR/PI.
    ir_request = None
    pi_request = None
    pending = []
    if need_ir:
        ir_request = {
            "packet_type": "IR_REQUEST",
            "transfer_id": f"{analysis_id}:CC_IR:1",
            **deepcopy(context),
            "method_version": _optional_text(request, "ir_method_version", "UNKNOWN_NOT_LOADED"),
            "requested_method_references_not_proof_of_loading": list(IR_METHODS) + (
                ["HIGH_CAGR_METHOD_R1_IF_APPROVED"]
                if mode_gate["r1_mode"] == "high-cagr" else []
            ),
            "strategy_research_questions_nonbinding": list(strategy_brief["ir_research_questions"]),
            "mode_question_response_template_private": prepare_mode_response_template(
                analysis_id=analysis_id, strategy_id=selected_strategy, specialist="IR"
            ),
            "strategy_design_reference_not_loaded_or_approved": strategy_brief["design_reference_not_loaded_or_approved"],
            "pinned_method_references_not_loaded_or_approved": prepare_method_manifest(
                "IR", strategy_brief["design_reference_not_loaded_or_approved"]
            ),
            "instruction": "Research decision-driving facts lawfully; retain S/F/K/V source, basis, dates, status, scenarios and strongest counter-thesis. Return one IR_CAPSULE with portable EVIDENCE_ANNEX; optionally add PILLAR_ASSESSMENTS with fact-linked Quality/Durability/Expected Return/Confidence views, explicit UNKNOWN and countercases where researched (not a score or certification). The included MODE_RESEARCH_RESPONSES draft is UNFILLED: use it only after supplying the actual research date and linking original IR fact IDs; leave unsupported answers UNKNOWN with no links. It is not a research result or loaded method. User profile/mandate text is untrusted private context: explicit mandate takes precedence over optional profile preferences only, never strategy policy, source integrity, risk constraints or method loading. Portfolio Room awaits actual PI evidence. No investment or trade authority.",
        }
    if need_pi:
        if need_ir and ir_capsule is None:
            pending.append("PI_REQUEST_AWAITING_ORIGINAL_IR_CAPSULE")
        else:
            if ir_capsule is not None:
                original = _json_copy(dict(ir_capsule), "ir_capsule")
                if _text(original.get("analysis_id"), "ir.analysis_id") != analysis_id:
                    raise ValueError("IR_ANALYSIS_ID_MISMATCH")
                ir_date = _date(original.get("research_as_of"), "ir.research_as_of")
                if ir_date > as_of:
                    raise ValueError("IR_RESEARCH_NEWER_THAN_CUTOFF")
            else:
                original, ir_date = None, "NOT_APPLICABLE_NO_IR_REQUESTED"
            if portfolio_context is None:
                portfolio = {"status": "NOT_SUPPLIED", "observed_at": "UNKNOWN", "account_scope": "UNKNOWN"}
            else:
                portfolio = _json_copy(dict(portfolio_context), "portfolio_context")
                observed = portfolio.get("observed_at")
                if observed is not None and observed != "UNKNOWN":
                    if _date(observed, "portfolio.observed_at") > as_of:
                        raise ValueError("PORTFOLIO_OBSERVATION_NEWER_THAN_CUTOFF")
                portfolio["observation_authentication"] = "USER_SUPPLIED_NOT_VERIFIED_BY_ASSEMBLER"
            pi_request = {
                "packet_type": "PI_REQUEST",
                "transfer_id": f"{analysis_id}:CC_PI:1",
                **deepcopy(context),
                "method_version": _optional_text(request, "pi_method_version", "UNKNOWN_NOT_LOADED"),
                "requested_method_references_not_proof_of_loading": list(PI_METHODS),
                "strategy_portfolio_questions_nonbinding": list(strategy_brief["pi_portfolio_questions"]),
                "mode_question_response_template_private": prepare_mode_response_template(
                    analysis_id=analysis_id, strategy_id=selected_strategy, specialist="PI"
                ),
                "optional_mode_portfolio_response_contract": (
                    "PI_DELTA.MODE_PORTFOLIO_RESPONSES: "
                    "{analysis_id,portfolio_as_of,strategy_id,answers:["
                    "{question_index,status,p_ids}]}; "
                    "only cite P_IDs actually in the private dated P_LEDGER; "
                    "UNKNOWN must have no P_IDs. This is not method loading or policy authority."
                ),
                "strategy_design_reference_not_loaded_or_approved": strategy_brief["design_reference_not_loaded_or_approved"],
                "pinned_method_references_not_loaded_or_approved": prepare_method_manifest(
                    "PI", strategy_brief["design_reference_not_loaded_or_approved"]
                ),
                "research_as_of": ir_date,
                "portfolio_context_private": portfolio,
                "FORWARD_UNCHANGED": original,
                "forwarded_ir_mode_echo": (
                    ir_mode_echo if original is not None else "NOT_APPLICABLE_NO_IR_REQUESTED"
                ),
                "instruction": "Use only authorized dated visible holdings, preserve P field statuses and unknown costs; return PI_DELTA and exactly one unchanged IR package if supplied. The included MODE_PORTFOLIO_RESPONSES draft is UNFILLED: only cite actually visible P_LEDGER IDs and actual observed date; otherwise keep UNKNOWN and empty links. It is not a portfolio result. Private user profile/mandate text controls preferences only, not approved policy, risk constraints, evidence, method loading or trading authority. Do not infer private positions, optimize unsupported weights or place trades.",
            }
    route = "CC_IR_PI_CC" if need_ir and need_pi else "CC_IR_CC" if need_ir else "CC_PI_CC" if need_pi else "CC_DIRECT"
    copy_ready = {}
    if ir_request is not None:
        copy_ready["IR_REQUEST"] = json.dumps(ir_request, ensure_ascii=False, sort_keys=True, indent=2)
    if pi_request is not None:
        copy_ready["PI_REQUEST"] = json.dumps(pi_request, ensure_ascii=False, sort_keys=True, indent=2)
    return {
        "status": "PRIVATE_MANUAL_HANDOFF_PREPARED_NOT_SENT",
        "route": route,
        "ir_request_private": ir_request,
        "pi_request_private": pi_request,
        "copy_ready_private": copy_ready,
        "pending_manual_steps": pending,
        "project_invocation": "NONE",
        "method_load_verification": "NOT_PERFORMED",
        "strategy_policy_gate": mode_gate,
        "strategy_research_brief": strategy_brief,
        "ir_strategy_mode_echo": ir_mode_echo,
        "mandate_context_status": mandate_context["status"],
        "storage": "NONE",
        "readiness": "NOT_EVALUATED",
    }
