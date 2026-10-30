"""Explicit, local, private JSON-over-stdin adapter for the existing R1 session.

Use from repository root: python -m scripts.r1_manual_session_cli --output status
No files are created, no processes scheduled, no Projects invoked, no trade made.
The caller must provide genuine, authorized inputs and review all conclusions.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import date
import re
import json
import math
import sys
from typing import Any, TextIO

from ai_native.session_bridge import complete_manual_session
from ai_native.pamalised_report import render_pamalised_html
from ai_native.pamalised_pdf import render_pamalised_pdf
from ai_native.manual_review_queue import prepare_manual_review_queue
from ai_native.intake_review import prepare_intake_review
from ai_native.opportunity_triage import prepare_selected_candidate_draft
from ai_native.research_memory import prepare_explicit_followup_draft
from ai_native.method_handoff_bundle import (
    prepare_verified_method_handoff, render_manual_specialist_prompt,
)
from ai_native.private_case_integrity import seal_private_case, verify_private_case_envelope
from ai_native.portfolio_snapshot_transfer import (
    seal_private_portfolio_snapshot, verify_private_portfolio_snapshot,
)
from ai_native.portfolio_observation import prepare_observation_ledger
from ai_native.work_blossom_adapter import prepare_work_blossom_observation

MAX_INPUT_CHARACTERS = 5_000_000
OPTIONAL_FIELDS = frozenset({
    "ir_capsule", "pi_delta", "portfolio_context", "calculation_requests",
    "method_return_receipts",
    "human_effort_inputs",
    "contribution_inputs", "cost_inputs", "scenario_weight_inputs", "memory_inputs",
    "observation_inputs", "prior_portfolio_observation_inputs",
    "work_blossom_inputs", "public_reference_inputs",
    "public_reference_table_inputs", "public_scope_attestation_inputs",
    "exposure_classifications", "room_assessment_inputs",
    "source_evidence_inputs", "valuation_inputs", "probability_inputs", "candidate_comparison_inputs",
    "fundamental_inputs", "historical_comparison_inputs", "opportunity_triage_inputs",
    "macro_sector_inputs", "work_portfolio_result", "specialist_result",
    "lifecycle_inputs", "lifecycle_current_evidence_inputs",
    "prior_private_portfolio_envelope",
})
PERMITTED_FIELDS = OPTIONAL_FIELDS | {"request"}
NEXT_ACTIONS = {
    "AWAITING_MANUAL_IR_CAPSULE": "Transfer the IR_REQUEST yourself; supply the original IR capsule in the next explicit run.",
    "AWAITING_MANUAL_PI_DELTA": "Transfer the PI_REQUEST yourself; supply the PI delta in the next explicit run.",
    "AWAITING_MANUAL_PORTFOLIO_SCREENSHOT": "Private visual portfolio source was reported unavailable. Use an authorized dated screenshot transcript in a new explicit session; no holdings are inferred.",
    "PI_ONLY_CONDITIONAL_REPORT_ASSEMBLED": "Review the private conditional report; no account or trade authorization.",
    "M7A_COMPONENT_ASSEMBLED_NOT_END_TO_END_ACCEPTANCE": "Review the private research report; end-to-end acceptance was NOT performed.",
    "CC_DIRECT_NO_SPECIALIST_REPORT_REQUIRED": "No specialist report requested; no automatic Project work.",
    "PUBLIC_REFERENCE_DESCRIPTIVE_REPORT_READY": "Review the caller-reported Blossom profile reference; not the CEO's private portfolio or a certified research conclusion.",
}
SAFE_ERROR_CODES = frozenset({
    "DUPLICATE_JSON_FIELD", "NONFINITE_JSON_NUMBER",
    "TOP_LEVEL_OBJECT_REQUIRED", "UNKNOWN_OR_MISSING_SESSION_FIELD",
    "INPUT_TOO_LARGE", "CEO_INITIATION_REQUIRED",
    "WORK_PORTFOLIO_RESULT_INVALID", "WORK_PORTFOLIO_RESULT_AMBIGUOUS",
    "SPECIALIST_RESULT_INVALID", "SPECIALIST_RESULT_AMBIGUOUS",
    "SPECIALIST_ORIGINAL_IR_REQUIRED", "SPECIALIST_FORWARDED_IR_MISMATCH",
    "SPECIALIST_UNEXPECTED_FORWARDED_IR",
    "FOLLOWUP_PRIOR_CASE_ENVELOPE_REQUIRED",
    "PRIVATE_CASE_ENVELOPE_REQUIRED",
    "PRIVATE_CASE_ENVELOPE_INVALID", "PRIVATE_CASE_SHA256_MISMATCH",
    "PRIVATE_CASE_RECORD_INVALID",
    "MANUAL_RESUME_ENVELOPE_INVALID",
    "MANUAL_RESUME_CONTINUATION_MISMATCH",
    "MANUAL_RESUME_STAGE_MISMATCH",
    "SEALED_FOLLOWUP_INPUT_INVALID",
    "SEALED_FOLLOWUP_EXPLICIT_MANDATE_REQUIRED",
    "SEALED_FOLLOWUP_PRIOR_ID_OR_SUBJECT_MISMATCH",
    "SEALED_FOLLOWUP_DATE_INVALID",
    "SEALED_FOLLOWUP_FACT_LINKS_INVALID",
    "PRIVATE_PORTFOLIO_ENVELOPE_INVALID",
    "PRIVATE_PORTFOLIO_SHA256_MISMATCH",
    "PRIVATE_PORTFOLIO_SNAPSHOT_INVALID",
    "PRIVATE_PORTFOLIO_FOLLOWUP_REQUIRED",
    "PRIVATE_PORTFOLIO_BASELINE_ID_MISMATCH",
    "PRIVATE_PORTFOLIO_SOURCE_AMBIGUOUS",
    "PORTFOLIO_FOLLOWUP_EXPLICIT_MANDATE_REQUIRED",
    "PORTFOLIO_FOLLOWUP_AMBIGUOUS_PRIOR_SOURCE",
    "PORTFOLIO_FOLLOWUP_CURRENT_OBSERVATION_REQUIRED",
    "INTEGRATED_PRIOR_CLOSEOUT_INVALID",
    "INTEGRATED_PRIOR_CASE_ID_OR_DATE_MISMATCH",
    "INTEGRATED_FOLLOWUP_CURRENT_PORTFOLIO_REQUIRED",
    "INTEGRATED_FOLLOWUP_PORTFOLIO_ROUTE_REQUIRED",
    "INTEGRATED_FOLLOWUP_PRIOR_SOURCE_AMBIGUOUS",
    "GUIDED_PRIVATE_CLOSEOUT_IR_PI_REQUIRED",
    "GUIDED_PRIVATE_CLOSEOUT_MEMORY_REQUIRED",
    "GUIDED_PRIVATE_CLOSEOUT_MEMORY_METADATA_INVALID",
    "GUIDED_PRIVATE_CLOSEOUT_CURRENT_OBSERVATION_REQUIRED",
    "GUIDED_RESEARCH_CLOSEOUT_IR_ONLY_REQUIRED",
    "GUIDED_PORTFOLIO_CLOSEOUT_PI_ONLY_REQUIRED",
    "GUIDED_PRIVATE_ROUTE_REQUEST_INVALID",
    "GUIDED_PRIVATE_ROUTE_SPECIALIST_REQUIRED",
    "SCREENSHOT_REENTRY_INPUT_INVALID",
    "SCREENSHOT_REENTRY_NOT_PENDING",
    "SCREENSHOT_REENTRY_SOURCE_INVALID",
    "SCREENSHOT_REENTRY_CASE_MISMATCH",
    "CANDIDATE_DRAFT_INPUT_INVALID",
    "CANDIDATE_DRAFT_TRIAGE_UNAVAILABLE",
    "CANDIDATE_DRAFT_CANDIDATE_NOT_FOUND",
})


def _inert_new_case_template() -> dict[str, Any]:
    """One private, intentionally non-executable CC intake skeleton.

    Never infer a date, strategy, fees, user initiation or specialist route.
    The existing R1 request validator remains the only admission path once
    the human fills this draft and explicitly starts a new session.
    """
    return {
        "request": {
            "ceo_initiated": False,
            "analysis_id": "",
            "as_of": "",
            "kind": "",
            "objective": "",
            "strategy_id": "",
            "horizon": "UNKNOWN",
            "risk_constraints": [],
            "candidate_universe": "UNKNOWN",
            "research_needed": None,
            "portfolio_needed": None,
            "account_context": {
                "type": "UNKNOWN",
                "broker": "UNKNOWN",
                "tax": "UNKNOWN",
                "commission": "UNKNOWN",
                "fx_cost": "UNKNOWN",
            },
            "method_version": "UNKNOWN_NOT_LOADED",
        }
    }


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("DUPLICATE_JSON_FIELD")
        result[key] = value
    return result


def _no_nonfinite(raw: str) -> None:
    raise ValueError("NONFINITE_JSON_NUMBER")


def _finite_json_float(raw: str) -> float:
    """Python JSON can silently turn 1e999 into infinity; reject that too."""
    number = float(raw)
    if not math.isfinite(number):
        raise ValueError("NONFINITE_JSON_NUMBER")
    return number


def _code(error: BaseException) -> str:
    # Never print arbitrary exception text: it may contain private data.
    candidate = str(error).split(":", 1)[0]
    return candidate if candidate in SAFE_ERROR_CODES else "INPUT_CONTRACT_REJECTED"


def evaluate(payload: Any) -> dict[str, Any]:
    """Pure dispatch to existing handoff/session code; no duplicate finance logic."""
    if not isinstance(payload, dict):
        raise ValueError("TOP_LEVEL_OBJECT_REQUIRED")
    if "request" not in payload or set(payload) - PERMITTED_FIELDS:
        raise ValueError("UNKNOWN_OR_MISSING_SESSION_FIELD")
    # PI-1 R1.4 Work returns exactly one of two JSON envelopes. Accept the
    # already pasted JSON object without asking a person to rename the field;
    # downstream public/private, mandate, date and provenance guards remain
    # authoritative. No browser access, source inference or project invocation.
    fields = {k: v for k, v in payload.items()
              if k not in {"request", "work_portfolio_result", "specialist_result",
                           "prior_private_portfolio_envelope"}}
    if "prior_private_portfolio_envelope" in payload:
        request = payload.get("request")
        if (not isinstance(request, dict)
                or request.get("ceo_initiated") is not True
                or request.get("kind") != "FOLLOWUP"
                or request.get("portfolio_needed") is not True):
            raise ValueError("PRIVATE_PORTFOLIO_FOLLOWUP_REQUIRED")
        if "prior_portfolio_observation_inputs" in fields:
            raise ValueError("PRIVATE_PORTFOLIO_SOURCE_AMBIGUOUS")
        prior = verify_private_portfolio_snapshot(
            payload["prior_private_portfolio_envelope"])
        if prior["analysis_id"] != request.get("prior_analysis_id"):
            raise ValueError("PRIVATE_PORTFOLIO_BASELINE_ID_MISMATCH")
        fields["prior_portfolio_observation_inputs"] = prior
    if "work_portfolio_result" in payload:
        wrapped = payload["work_portfolio_result"]
        branches = {
            "public_portfolio_reference": "public_reference_inputs",
            "work_blossom_inputs": "work_blossom_inputs",
        }
        if not isinstance(wrapped, dict) or len(wrapped) != 1:
            raise ValueError("WORK_PORTFOLIO_RESULT_INVALID")
        key = next(iter(wrapped))
        if key not in branches or not isinstance(wrapped[key], dict):
            raise ValueError("WORK_PORTFOLIO_RESULT_INVALID")
        if fields.keys() & {
            "work_blossom_inputs", "public_reference_inputs",
            "public_reference_table_inputs", "observation_inputs",
        }:
            raise ValueError("WORK_PORTFOLIO_RESULT_AMBIGUOUS")
        fields[branches[key]] = wrapped[key]
    if "specialist_result" in payload:
        # The Projects cannot invoke each other. A person supplies exactly
        # one original specialist-return envelope per explicit CLI call.
        # Never infer an earlier IR capsule from PI's forwarded copy.
        result = payload["specialist_result"]
        if not isinstance(result, dict):
            raise ValueError("SPECIALIST_RESULT_INVALID")
        keys = set(result)
        if keys == {"IR_CAPSULE"}:
            if not isinstance(result["IR_CAPSULE"], dict):
                raise ValueError("SPECIALIST_RESULT_INVALID")
            if "ir_capsule" in fields:
                raise ValueError("SPECIALIST_RESULT_AMBIGUOUS")
            fields["ir_capsule"] = result["IR_CAPSULE"]
        elif keys in ({"PI_DELTA"}, {"PI_DELTA", "FORWARD_UNCHANGED"}):
            if not isinstance(result["PI_DELTA"], dict):
                raise ValueError("SPECIALIST_RESULT_INVALID")
            if "pi_delta" in fields:
                raise ValueError("SPECIALIST_RESULT_AMBIGUOUS")
            delta = deepcopy(result["PI_DELTA"])
            if "FORWARD_UNCHANGED" in result:
                forwarded = result["FORWARD_UNCHANGED"]
                if not isinstance(forwarded, dict):
                    raise ValueError("SPECIALIST_RESULT_INVALID")
                request = payload["request"]
                if (not isinstance(request, dict)
                        or request.get("research_needed") is not True):
                    raise ValueError("SPECIALIST_UNEXPECTED_FORWARDED_IR")
                # The CEO must retain/re-supply the independently received
                # original IR. PI's copy alone cannot establish integrity.
                original_ir = fields.get("ir_capsule")
                if not isinstance(original_ir, dict):
                    raise ValueError("SPECIALIST_ORIGINAL_IR_REQUIRED")
                if forwarded != original_ir:
                    raise ValueError("SPECIALIST_FORWARDED_IR_MISMATCH")
                if ("forwarded_ir" in delta
                        and delta["forwarded_ir"] != original_ir):
                    raise ValueError("SPECIALIST_FORWARDED_IR_MISMATCH")
                # Reuse the already enforced canonical PI_DELTA schema.
                delta["forwarded_ir"] = deepcopy(original_ir)
            fields["pi_delta"] = delta
        else:
            raise ValueError("SPECIALIST_RESULT_INVALID")
    return complete_manual_session(payload["request"], **fields)


def _prepare_manual_continuation(payload: dict[str, Any],
                                 result: dict[str, Any]) -> dict[str, Any] | None:
    """Private, one-step manual continuation; no disk state or Project calls.

    Prepare an input envelope the operator can explicitly use again. IR must
    remain the *independently received* original, never reconstructed from PI.
    """
    required = {
        "AWAITING_MANUAL_IR_CAPSULE": ("IR_REQUEST", "IR_CAPSULE"),
        "AWAITING_MANUAL_PI_DELTA": ("PI_REQUEST", "PI_DELTA"),
    }.get(result["status"])
    if required is None:
        return None
    label, expected = required
    packet = result["handoffs_private"]["copy_ready_private"].get(label)
    if not isinstance(packet, str):
        raise ValueError("CONTINUATION_HANDOFF_MISSING")
    handoff = json.loads(packet, parse_constant=_no_nonfinite,
                         parse_float=_finite_json_float,
                         object_pairs_hook=_unique_pairs)
    resume = deepcopy(payload)
    if "specialist_result" in resume:
        prior = resume.pop("specialist_result")
        if (label != "PI_REQUEST" or not isinstance(prior, dict)
                or set(prior) != {"IR_CAPSULE"}
                or not isinstance(prior["IR_CAPSULE"], dict)
                or "ir_capsule" in resume):
            raise ValueError("CONTINUATION_PRIOR_SPECIALIST_INVALID")
        resume["ir_capsule"] = deepcopy(prior["IR_CAPSULE"])

    # A validated Work capture has a canonical PRIVATE observation mapping.
    # Carry that consumed mapping, NOT the original raw HTML/browser token or
    # other unconsumed Work metadata, into the next explicit user input.
    capture = result.get("work_blossom_capture_private")
    if capture is not None:
        if "work_blossom_inputs" in resume:
            raw_work = resume.pop("work_blossom_inputs")
        else:
            wrapped = resume.pop("work_portfolio_result", None)
            raw_work = wrapped.get("work_blossom_inputs") if isinstance(wrapped, dict) else None
        if not isinstance(raw_work, dict):
            raise ValueError("CONTINUATION_WORK_CAPTURE_INVALID")
        if capture.get("status") == "PRIVATE_OBSERVATION_PACKET_PREPARED_NOT_SENT":
            observation = capture.get("observation_inputs_private")
            if not isinstance(observation, dict) or "observation_inputs" in resume:
                raise ValueError("CONTINUATION_WORK_CAPTURE_INVALID")
            resume["observation_inputs"] = deepcopy(observation)
        elif capture.get("status") == "VISUAL_SOURCE_UNAVAILABLE_USE_SCREENSHOT_FALLBACK":
            # IR can still be requested before the screenshot; keep only
            # the minimal unavailable-state marker, never the inaccessible view.
            resume["work_blossom_inputs"] = {
                "capture_mode": raw_work.get("capture_mode"),
                "view_status": "UNAVAILABLE",
                "analysis_id": payload["request"]["analysis_id"],
                "analysis_as_of": payload["request"]["as_of"],
            }
        else:
            raise ValueError("CONTINUATION_WORK_CAPTURE_INVALID")

    # JSON null is deliberately not a valid specialist return. The user must
    # replace it with the original full IR_CAPSULE / PI_DELTA JSON envelope.
    resume["specialist_result"] = None
    return {
        "status": "PRIVATE_MANUAL_CONTINUATION_NOT_SENT",
        "next_handoff": {label: handoff},
        "resume_input": resume,
        "replace_null_with": expected,
        "readiness": "NOT_EVALUATED",
        "storage": "NONE",
        "project_invocation": "NONE",
        "trading_authority": "NONE",
    }


def _redacted_status(session: dict[str, Any]) -> dict[str, Any]:
    """Reuse the default status schema; no private fields."""
    status = session["status"]
    return {
        "status": status, "route": session["route"],
        "readiness": session["readiness"],
        "project_invocation": session["project_invocation"],
        "storage": session["storage"],
        "source_authentication": session["source_authentication"],
        "next_manual_action": NEXT_ACTIONS.get(
            status, "Review the private packet manually."),
    }


def _private_operator_packet(payload: dict[str, Any],
                             session: dict[str, Any]) -> dict[str, Any]:
    """Explicit PRIVATE composition of the existing manual session outputs."""
    continuation = _prepare_manual_continuation(payload, session)
    report = session["final_report_private"]
    if report is not None and not isinstance(report, str):
        raise ValueError("OPERATOR_PACKET_REPORT_INVALID")
    if continuation is not None and report is not None:
        raise ValueError("OPERATOR_PACKET_FINAL_PENDING_CONFLICT")
    return {
        "status": "PRIVATE_OPERATOR_PACKET_NOT_SENT",
        "session": _redacted_status(session),
        "continuation_private": continuation,
        "report_private": report,
        "review_queue": prepare_manual_review_queue(session),
        "readiness": "NOT_EVALUATED",
        "source_authentication": "NOT_PERFORMED",
        "project_invocation": "NONE",
        "storage": "NONE",
        "trading_authority": "NONE",
    }


def _eligible_private_case(result: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
    """Existing private-case export gate reused by both explicit outputs."""
    integrated = result.get("integrated_private")
    if not isinstance(integrated, dict):
        return None, "PRIVATE_CASE_NOT_AVAILABLE: " + result["status"]
    record = integrated.get("private_research_history_proposal")
    gate = integrated.get("github_memory_review_gate")
    if record is None:
        return None, "PRIVATE_CASE_NOT_PREPARED: explicit memory_inputs required."
    if (not isinstance(record, dict) or not isinstance(gate, dict)
            or record.get("schema_version") != "RESEARCH_HISTORY_R1"
            or record.get("privacy_tier") != "PRIVATE_PENDING_REVIEW"
            or record.get("archive_status") != "PROPOSED_NOT_COMMITTED"
            or gate.get("approved_for_publication") is not False
            or gate.get("status") !=
            "WITHHELD_PENDING_HUMAN_PRIVACY_AND_RIGHTS_REVIEW"):
        return None, "PRIVATE_CASE_NOT_AVAILABLE: review gate or private status invalid."
    return record, ""


def _private_research_closeout(payload: dict[str, Any],
                               session: dict[str, Any]) -> dict[str, Any]:
    """Opt-in final CC report + independently reusable PRIVATE case copy.

    No disk/archive write. Reuse the same checked report, review queue and
    existing case-sealing contracts; never invent PI-only research memory.
    """
    if session.get("status") != "M7A_COMPONENT_ASSEMBLED_NOT_END_TO_END_ACCEPTANCE":
        raise ValueError("PRIVATE_CLOSEOUT_FINAL_RESEARCH_REQUIRED")
    if not isinstance(payload.get("memory_inputs"), dict):
        raise ValueError("PRIVATE_CLOSEOUT_MEMORY_INPUTS_REQUIRED")
    record, error = _eligible_private_case(session)
    if record is None:
        raise ValueError("PRIVATE_CLOSEOUT_CASE_UNAVAILABLE")
    operator = _private_operator_packet(payload, session)
    if (operator["continuation_private"] is not None
            or not isinstance(operator["report_private"], str)
            or not operator["report_private"].strip()):
        raise ValueError("PRIVATE_CLOSEOUT_REPORT_UNAVAILABLE")
    return {
        "status": "PRIVATE_RESEARCH_CLOSEOUT_COPY_NOT_STORED",
        "operator_packet_private": operator,
        "private_case_envelope": seal_private_case(record),
        "next_manual_step": "HUMAN_REVIEW_THEN_SAVE_ONLY_IN_APPROVED_PRIVATE_ARCHIVE",
        "archive_integrity": "UNKEYED_SHA256_COPY_CHECK_ONLY_NOT_AUTHENTICITY",
        "archive_protection": "NOT_ESTABLISHED",
        "method_load_verification": "NOT_PERFORMED",
        "source_authentication": "NOT_PERFORMED",
        "project_invocation": "NONE",
        "storage": "NONE",
        "readiness": "NOT_EVALUATED",
        "trading_authority": "NONE",
    }


def _sealed_current_private_portfolio(payload: dict[str, Any],
                                      session: dict[str, Any]) -> dict[str, Any]:
    """Export only the current, checked M3 observation from a completed PI path.

    Strictly reuse the original Work sanitation, M3 validation and SHA-256
    export; never include a browser token or authenticate a private source.
    """
    if (session.get("status") not in {
            "PI_ONLY_CONDITIONAL_REPORT_ASSEMBLED",
            "M7A_COMPONENT_ASSEMBLED_NOT_END_TO_END_ACCEPTANCE"}
            or not isinstance(session.get("pi_delta_private"), dict)):
        raise ValueError("PRIVATE_PORTFOLIO_SNAPSHOT_INVALID")
    original = payload.get("observation_inputs")
    capture = session.get("work_blossom_capture_private")
    if capture is not None:
        if (original is not None or capture.get("status") !=
                "PRIVATE_OBSERVATION_PACKET_PREPARED_NOT_SENT"):
            raise ValueError("PRIVATE_PORTFOLIO_SNAPSHOT_INVALID")
        original = capture.get("observation_inputs_private")
    if (not isinstance(original, dict)
            or prepare_observation_ledger(**original) !=
                session.get("portfolio_observation_private")):
        raise ValueError("PRIVATE_PORTFOLIO_SNAPSHOT_INVALID")
    return seal_private_portfolio_snapshot(original)


def _private_portfolio_closeout(
    payload: dict[str, Any], session: dict[str, Any],
) -> dict[str, Any]:
    """Explicit PI-only result + original private M3 copy, never research."""
    if (session.get("route") != "CC_PI_CC"
            or session.get("status") != "PI_ONLY_CONDITIONAL_REPORT_ASSEMBLED"):
        raise ValueError("GUIDED_PORTFOLIO_CLOSEOUT_PI_ONLY_REQUIRED")
    portfolio = _sealed_current_private_portfolio(payload, session)
    operator = _private_operator_packet(payload, session)
    if (operator["continuation_private"] is not None
            or not isinstance(operator["report_private"], str)
            or not operator["report_private"].strip()):
        raise ValueError("PRIVATE_PORTFOLIO_CLOSEOUT_REPORT_UNAVAILABLE")
    return {
        "status": "PRIVATE_PORTFOLIO_CLOSEOUT_COPY_NOT_STORED",
        "operator_packet_private": operator,
        "private_portfolio_snapshot_envelope": portfolio,
        "next_manual_step": "HUMAN_REVIEW_THEN_SAVE_ONLY_IN_APPROVED_PRIVATE_ARCHIVE",
        "archive_integrity": "UNKEYED_SHA256_COPY_CHECK_ONLY_NOT_AUTHENTICITY",
        "archive_protection": "NOT_ESTABLISHED",
        "source_authentication": "NOT_PERFORMED",
        "project_invocation": "NONE",
        "storage": "NONE",
        "readiness": "NOT_EVALUATED",
        "trading_authority": "NONE",
    }


def _private_integrated_closeout(payload: dict[str, Any],
                                 session: dict[str, Any]) -> dict[str, Any]:
    """One deliberately opted-in private CC/IR/PI closing packet.

    The existing research and portfolio copies remain independent, portable,
    and unencrypted. Never create a PI research case or invent portfolio data.
    """
    research = _private_research_closeout(payload, session)
    portfolio = _sealed_current_private_portfolio(payload, session)
    original_research = research["private_case_envelope"]["private_case"]
    original_portfolio = portfolio["private_snapshot"]
    if (original_research.get("analysis_id") != original_portfolio.get("analysis_id")
            or original_research.get("as_of") != original_portfolio.get("analysis_as_of")):
        raise ValueError("PRIVATE_INTEGRATED_CLOSEOUT_CASE_MISMATCH")
    return {
        **research,
        "status": "PRIVATE_INTEGRATED_CLOSEOUT_COPY_NOT_STORED",
        "private_portfolio_snapshot_envelope": portfolio,
        "archive_scope": "COMPACT_RESEARCH_CASE_AND_ORIGINAL_M3_OBSERVATION_ONLY",
        "portfolio_source_authentication": "NOT_PERFORMED",
    }


def _checked_integrated_prior(raw: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    """Recheck BOTH retained PRIVATE copies, not a self-declared archive status.

    Only original research and M3 observations are restored; the prior report
    does not become new evidence or an instruction in the fresh mandate.
    """
    if (not isinstance(raw, dict)
            or raw.get("status") != "PRIVATE_INTEGRATED_CLOSEOUT_COPY_NOT_STORED"
            or raw.get("archive_scope") !=
                "COMPACT_RESEARCH_CASE_AND_ORIGINAL_M3_OBSERVATION_ONLY"
            or raw.get("archive_protection") != "NOT_ESTABLISHED"
            or raw.get("archive_integrity") !=
                "UNKEYED_SHA256_COPY_CHECK_ONLY_NOT_AUTHENTICITY"
            or raw.get("source_authentication") != "NOT_PERFORMED"
            or raw.get("portfolio_source_authentication") != "NOT_PERFORMED"
            or raw.get("method_load_verification") != "NOT_PERFORMED"
            or raw.get("storage") != "NONE"
            or raw.get("readiness") != "NOT_EVALUATED"
            or raw.get("project_invocation") != "NONE"
            or raw.get("trading_authority") != "NONE"):
        raise ValueError("INTEGRATED_PRIOR_CLOSEOUT_INVALID")
    case = verify_private_case_envelope(raw.get("private_case_envelope"))
    portfolio = verify_private_portfolio_snapshot(
        raw.get("private_portfolio_snapshot_envelope"))
    if (case["analysis_id"] != portfolio["analysis_id"]
            or case["as_of"] != portfolio["analysis_as_of"]):
        raise ValueError("INTEGRATED_PRIOR_CASE_ID_OR_DATE_MISMATCH")
    return case, portfolio


def _portfolio_followup_draft(raw: Any) -> dict[str, Any]:
    """Explicit inert NEW PI-only mandate from ONE previously saved M3 copy.

    The old source is verified for accidental alteration only. Retain its
    original holdings strictly in CC-only input, never the fresh request or
    receiving PI prompt; the next current observation must be newly supplied.
    """
    original = verify_private_portfolio_snapshot(raw)
    previous_analysis = original["analysis_id"]
    previous_cutoff = original["analysis_as_of"]
    return {
        "status": "PRIVATE_PORTFOLIO_FOLLOWUP_DRAFT_REQUIRES_CEO_INITIATION",
        "input_template": {
            "request": {
                "ceo_initiated": False,
                "analysis_id": None,
                "as_of": None,
                "kind": "FOLLOWUP",
                "prior_analysis_id": previous_analysis,
                "objective": None,
                "research_needed": False,
                "portfolio_needed": True,
                # A private M3 snapshot does NOT contain an approved strategy,
                # investment horizon, current account costs or CEO intention.
                "strategy_id": "EXPLORATORY",
                "horizon": "UNKNOWN",
                "risk_constraints": [],
                "candidate_universe": "UNKNOWN",
                "account_context": {
                    "type": "UNKNOWN", "broker": "UNKNOWN",
                    "tax": "UNKNOWN", "commission": "UNKNOWN",
                    "fx_cost": "UNKNOWN",
                },
                "pi_method_version": "UNKNOWN_NOT_LOADED",
            },
            "prior_private_portfolio_envelope": deepcopy(raw),
        },
        "prior_observation_reference_private": {
            "analysis_id": previous_analysis,
            "analysis_as_of": previous_cutoff,
            "observed_on": original["observed_on"],
            "copy_integrity": "UNKEYED_SHA256_MATCHED_RETAINED_COPY_ONLY",
            "account_or_positions_in_new_request": "NONE",
        },
        "next_manual_step": "CEO_REVIEW_FILL_NEW_REQUEST_AND_SUPPLY_FRESH_DATED_PRIVATE_OBSERVATION",
        "human_checks": [
            "Human must supply a distinct NEW analysis ID, later current observation date and analysis cutoff, objective and explicit CEO initiation.",
            "Reconfirm selected strategy, horizon, risk constraints, named account scope, broker, taxes, commissions and FX costs; none are inherited from old M3 holdings.",
            "Reconfirm authorized read-only current portfolio view or dated screenshot, including coverage, account/currency/cash fields and rights.",
            "Run intake-review on a request-only copy if useful; run guided-portfolio-closeout only with a NEW original observation and actual CEO authorization.",
            "Existing M3 comparison refuses mismatched account, currency, dates and unsupported weight/performance inference; do not infer transfers, capital flows or investment returns.",
        ],
        "previous_record_authenticity": "NOT_ESTABLISHED_UNKEYED_CHECKSUM",
        "current_portfolio_observation": "NOT_SUPPLIED",
        "source_authentication": "NOT_PERFORMED",
        "method_load_verification": "NOT_PERFORMED",
        "project_invocation": "NONE",
        "storage": "NONE",
        "readiness": "NOT_EVALUATED",
        "trading_authority": "NONE",
    }


def _reenter_portfolio_followup(
    payload: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """One new CEO PI mandate with a human-retained prior M3 snapshot.

    Reuse the existing sealed-source, M3 comparison and operator contracts;
    no historical holdings are inferred as current or forwarded to PI.
    """
    if (not isinstance(payload, dict)
            or set(payload) != {
                "private_portfolio_snapshot_envelope", "session"}
            or not isinstance(payload["session"], dict)):
        raise ValueError("PORTFOLIO_FOLLOWUP_EXPLICIT_MANDATE_REQUIRED")
    # Verifies accidental-copy integrity and reconstructs the old original
    # source via M3; this does NOT authenticate a broker or the archive.
    historical = _portfolio_followup_draft(
        payload["private_portfolio_snapshot_envelope"])
    old = historical["prior_observation_reference_private"]
    current = deepcopy(payload["session"])
    request = current.get("request")
    if (not isinstance(request, dict)
            or request.get("ceo_initiated") is not True
            or request.get("kind") != "FOLLOWUP"
            or request.get("research_needed") is not False
            or request.get("portfolio_needed") is not True
            or request.get("prior_analysis_id") != old["analysis_id"]
            or request.get("analysis_id") == old["analysis_id"]
            or not isinstance(request.get("as_of"), str)
            or request["as_of"] <= old["analysis_as_of"]):
        raise ValueError("PORTFOLIO_FOLLOWUP_EXPLICIT_MANDATE_REQUIRED")
    if ("prior_private_portfolio_envelope" in current
            or "prior_portfolio_observation_inputs" in current):
        raise ValueError("PORTFOLIO_FOLLOWUP_AMBIGUOUS_PRIOR_SOURCE")
    if not any(key in current for key in (
            "observation_inputs", "work_blossom_inputs",
            "work_portfolio_result")):
        raise ValueError("PORTFOLIO_FOLLOWUP_CURRENT_OBSERVATION_REQUIRED")
    current["prior_private_portfolio_envelope"] = deepcopy(
        payload["private_portfolio_snapshot_envelope"])
    # Previous positions are retained ONLY inside CC-owned private state.
    # Existing M1, Work/M3, snapshot comparison and handoff gates apply.
    return current, evaluate(current)


def _integrated_followup_draft(raw: Any) -> dict[str, Any]:
    """Inert research draft with separately retained optional PI baseline.

    A new portfolio mandate and a NEW dated private observation must be
    independently supplied before comparing historical portfolio weights.
    """
    case, _ = _checked_integrated_prior(raw)
    draft = prepare_explicit_followup_draft(case)
    draft["private_portfolio_baseline_for_explicit_use"] = deepcopy(
        raw["private_portfolio_snapshot_envelope"])
    draft["portfolio_followup"] = "OPT_IN_ONLY_REQUIRES_NEW_DATED_PRIVATE_OBSERVATION"
    draft["human_checks"].append(
        "For a new PI follow-up, explicitly set portfolio_needed=true and "
        "provide a NEW dated private observation, then supply "
        "private_portfolio_baseline_for_explicit_use as "
        "prior_private_portfolio_envelope in the private session. "
        "Do not silently carry old holdings into the new mandate.")
    return draft


def _integrated_followup_operator(payload: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    """Reuse M4 sealed research and M3 prior snapshot in one NEW user request.

    This is a one-time, manual step; it cannot retrieve, schedule or invoke.
    It requires a fresh independent current P-ledger before any comparison.
    """
    if (not isinstance(payload, dict)
            or set(payload) != {"prior_integrated_closeout", "session", "fact_links"}
            or not isinstance(payload["session"], dict)):
        raise ValueError("INTEGRATED_PRIOR_CLOSEOUT_INVALID")
    _checked_integrated_prior(payload["prior_integrated_closeout"])
    session = deepcopy(payload["session"])
    request = session.get("request")
    if (not isinstance(request, dict)
            or request.get("portfolio_needed") is not True):
        raise ValueError("INTEGRATED_FOLLOWUP_PORTFOLIO_ROUTE_REQUIRED")
    if "prior_private_portfolio_envelope" in session or (
            "prior_portfolio_observation_inputs" in session):
        raise ValueError("INTEGRATED_FOLLOWUP_PRIOR_SOURCE_AMBIGUOUS")
    if not any(key in session for key in (
            "observation_inputs", "work_blossom_inputs", "work_portfolio_result")):
        raise ValueError("INTEGRATED_FOLLOWUP_CURRENT_PORTFOLIO_REQUIRED")
    # The prior observation is a CC-only comparison input, NOT forwarded to
    # IR/PI as current holdings or a true account-state assertion.
    session["prior_private_portfolio_envelope"] = deepcopy(
        payload["prior_integrated_closeout"]["private_portfolio_snapshot_envelope"])
    recovered = {
        "private_case_envelope": deepcopy(
            payload["prior_integrated_closeout"]["private_case_envelope"]),
        "session": session,
        "fact_links": deepcopy(payload["fact_links"]),
    }
    return _reenter_sealed_followup(recovered)


def _check_guided_research_archive_memory(payload: dict[str, Any]) -> None:
    """Reuse the exact archive memory metadata gate on IR-only and IR+PI.

    An immutable saved CC continuation cannot acquire missing memory inputs
    after an IR return. Refuse a non-completable archival route up front.
    """
    request = payload.get("request")
    if not isinstance(request, dict):
        raise ValueError("GUIDED_PRIVATE_CLOSEOUT_MEMORY_METADATA_INVALID")
    memory = payload.get("memory_inputs")
    if not isinstance(memory, dict):
        raise ValueError("GUIDED_PRIVATE_CLOSEOUT_MEMORY_REQUIRED")
    if set(memory) - {
            "report_id", "instruction_version", "recorded_at",
            "parent_report_id", "accessible_parent"}:
        raise ValueError("GUIDED_PRIVATE_CLOSEOUT_MEMORY_METADATA_INVALID")
    parent = memory.get("accessible_parent")
    if (parent is not None and (
            not isinstance(parent, dict)
            or not isinstance(memory.get("parent_report_id"), str)
            or parent.get("report_id") != memory.get("parent_report_id"))):
        raise ValueError("GUIDED_PRIVATE_CLOSEOUT_MEMORY_METADATA_INVALID")
    report_id = memory.get("report_id")
    instruction_version = memory.get("instruction_version")
    recorded_at = memory.get("recorded_at")
    parent_id = memory.get("parent_report_id")
    if (not isinstance(report_id, str)
            or not _FOLLOWUP_SAFE_ID.fullmatch(report_id)
            or not isinstance(instruction_version, str)
            or not instruction_version.strip()
            or not isinstance(recorded_at, str)
            or (parent_id is not None and (
                not isinstance(parent_id, str)
                or not _FOLLOWUP_SAFE_ID.fullmatch(parent_id)
                or parent_id == report_id))):
        raise ValueError("GUIDED_PRIVATE_CLOSEOUT_MEMORY_METADATA_INVALID")
    try:
        recorded = date.fromisoformat(recorded_at)
        if (recorded.isoformat() != recorded_at
                or recorded_at < request["as_of"]):
            raise ValueError
    except (ValueError, TypeError, KeyError) as exc:
        raise ValueError("GUIDED_PRIVATE_CLOSEOUT_MEMORY_METADATA_INVALID") from exc


def _check_guided_current_m3_observation(
    payload: dict[str, Any], session: dict[str, Any],
) -> None:
    """Shared original dated M3 admission for opt-in PI archive routes."""
    request = payload.get("request")
    if not isinstance(request, dict):
        raise ValueError("GUIDED_PRIVATE_CLOSEOUT_CURRENT_OBSERVATION_REQUIRED")
    ledger = session.get("portfolio_observation_private")
    if not isinstance(ledger, dict) or ledger.get("private_scope") is not True:
        raise ValueError("GUIDED_PRIVATE_CLOSEOUT_CURRENT_OBSERVATION_REQUIRED")
    raw = payload.get("observation_inputs")
    capture = session.get("work_blossom_capture_private")
    if capture is not None:
        if (raw is not None
                or capture.get("status") !=
                    "PRIVATE_OBSERVATION_PACKET_PREPARED_NOT_SENT"):
            raise ValueError("GUIDED_PRIVATE_CLOSEOUT_CURRENT_OBSERVATION_REQUIRED")
        raw = capture.get("observation_inputs_private")
    if not isinstance(raw, dict):
        raise ValueError("GUIDED_PRIVATE_CLOSEOUT_CURRENT_OBSERVATION_REQUIRED")
    try:
        checked = seal_private_portfolio_snapshot(raw)
        if (checked["private_snapshot"]["analysis_id"] != request["analysis_id"]
                or checked["private_snapshot"]["analysis_as_of"] != request["as_of"]
                or prepare_observation_ledger(**raw) != ledger):
            raise ValueError
    except (ValueError, KeyError, TypeError) as exc:
        raise ValueError("GUIDED_PRIVATE_CLOSEOUT_CURRENT_OBSERVATION_REQUIRED") from exc


def _preflight_guided_portfolio_closeout(
    payload: dict[str, Any], session: dict[str, Any],
) -> None:
    """PI-only private copies are possible only with a current original M3."""
    request = payload.get("request")
    if (not isinstance(request, dict)
            or request.get("research_needed") is not False
            or request.get("portfolio_needed") is not True
            or session.get("route") != "CC_PI_CC"
            or "memory_inputs" in payload):
        raise ValueError("GUIDED_PORTFOLIO_CLOSEOUT_PI_ONLY_REQUIRED")
    _check_guided_current_m3_observation(payload, session)


def _preflight_guided_research_closeout(
    payload: dict[str, Any], session: dict[str, Any],
) -> None:
    """Fail closed on IR-only archive prerequisites before any specialist work."""
    request = payload.get("request")
    if (not isinstance(request, dict)
            or request.get("research_needed") is not True
            or request.get("portfolio_needed") is not False
            or session.get("route") != "CC_IR_CC"):
        raise ValueError("GUIDED_RESEARCH_CLOSEOUT_IR_ONLY_REQUIRED")
    _check_guided_research_archive_memory(payload)


def _preflight_guided_private_closeout(
    payload: dict[str, Any], session: dict[str, Any],
) -> None:
    """Reject a non-completable guided archive BEFORE human IR/PI work begins.

    A saved manual continuation must be replayed unchanged: the operator cannot
    safely add absent M3 observations or memory metadata at a later specialist
    return. Use the original M3 seal for source eligibility and original
    memory contract's essential fields, without inventing an IR record.
    This is an admission check, not source authentication or final acceptance.
    """
    request = payload.get("request")
    if (not isinstance(request, dict)
            or request.get("research_needed") is not True
            or request.get("portfolio_needed") is not True
            or session.get("route") != "CC_IR_PI_CC"):
        raise ValueError("GUIDED_PRIVATE_CLOSEOUT_IR_PI_REQUIRED")
    _check_guided_research_archive_memory(payload)
    _check_guided_current_m3_observation(payload, session)


def _screenshot_retry_template(
    payload: dict[str, Any], session: dict[str, Any],
) -> dict[str, Any] | None:
    """Provide the exact private retry context after Work is unavailable.

    The retry is inert until the CEO supplies a NEW dated screenshot source.
    No unavailable browser fields other than the four checked routing markers
    are copied. This is CC-only state, never an IR/PI transfer.
    """
    if session.get("status") != "AWAITING_MANUAL_PORTFOLIO_SCREENSHOT":
        return None
    prior = payload.get("work_blossom_inputs")
    if prior is None:
        wrapper = payload.get("work_portfolio_result")
        prior = (wrapper.get("work_blossom_inputs")
                 if isinstance(wrapper, dict) else None)
    request = payload.get("request")
    if (not isinstance(prior, dict)
            or not isinstance(request, dict)
            or prior.get("capture_mode") != "WORK_BROWSER"
            or prior.get("view_status") != "UNAVAILABLE"
            or prior.get("analysis_id") != request.get("analysis_id")
            or prior.get("analysis_as_of") != request.get("as_of")):
        raise ValueError("SCREENSHOT_REENTRY_INPUT_INVALID")
    pending = deepcopy(payload)
    pending.pop("work_portfolio_result", None)
    pending.pop("work_blossom_inputs", None)
    pending["work_blossom_inputs"] = {
        key: prior[key] for key in (
            "capture_mode", "view_status", "analysis_id", "analysis_as_of")
    }
    if evaluate(pending)["status"] != session["status"]:
        raise ValueError("SCREENSHOT_REENTRY_NOT_PENDING")
    return {"pending_session": pending, "screenshot_work_inputs": None}


def _reenter_manual_screenshot(
    envelope: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Resume a previously stalled CC PI session with a NEW manual screenshot.

    Require the exact sanitized unavailable-Work marker from a prior local
    continuation, and replay it before replacing it. A new screenshot is
    caller-supplied and never a claim of signed-in Work/browser access.
    No original IR, previous holdings, financial policy or CEO authorization
    is overwritten by the replacement.
    """
    if (not isinstance(envelope, dict)
            or set(envelope) != {"pending_session", "screenshot_work_inputs"}
            or not isinstance(envelope["pending_session"], dict)
            or not isinstance(envelope["screenshot_work_inputs"], dict)):
        raise ValueError("SCREENSHOT_REENTRY_INPUT_INVALID")
    pending = deepcopy(envelope["pending_session"])
    source = pending.get("work_blossom_inputs")
    request = pending.get("request")
    if (not isinstance(source, dict)
            or not isinstance(request, dict)
            or set(source) != {
                "capture_mode", "view_status", "analysis_id", "analysis_as_of"
            }
            or source["capture_mode"] != "WORK_BROWSER"
            or source["view_status"] != "UNAVAILABLE"
            or source["analysis_id"] != request.get("analysis_id")
            or source["analysis_as_of"] != request.get("as_of")
            or "work_portfolio_result" in pending
            or "observation_inputs" in pending):
        raise ValueError("SCREENSHOT_REENTRY_INPUT_INVALID")
    # Only a previously checked, actually stalled PI path is eligible. IR
    # must have returned independently on the research+portfolio route.
    before = evaluate(pending)
    if before["status"] != "AWAITING_MANUAL_PORTFOLIO_SCREENSHOT":
        raise ValueError("SCREENSHOT_REENTRY_NOT_PENDING")
    screenshot = envelope["screenshot_work_inputs"]
    if (screenshot.get("capture_mode") != "USER_SCREENSHOT"
            or screenshot.get("view_status") != "VISIBLE"
            or "raw_html" in screenshot
            or "browser_hostname" in screenshot
            or "work_reported_signed_in" in screenshot):
        raise ValueError("SCREENSHOT_REENTRY_SOURCE_INVALID")
    if (screenshot.get("analysis_id") != request["analysis_id"]
            or screenshot.get("analysis_as_of") != request["as_of"]):
        raise ValueError("SCREENSHOT_REENTRY_CASE_MISMATCH")
    captured = prepare_work_blossom_observation(screenshot)
    if captured.get("status") != "PRIVATE_OBSERVATION_PACKET_PREPARED_NOT_SENT":
        raise ValueError("SCREENSHOT_REENTRY_SOURCE_INVALID")
    # Never carry screenshot pixels, browser tokens, URLs or the unavailable
    # Work marker into the new PI request, resume input or private report.
    del pending["work_blossom_inputs"]
    pending["observation_inputs"] = deepcopy(
        captured["observation_inputs_private"])
    after = evaluate(pending)
    if after["status"] != "AWAITING_MANUAL_PI_DELTA":
        raise ValueError("SCREENSHOT_REENTRY_NOT_PENDING")
    return pending, after


def _resume_manual_transfer(envelope: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    """Rejoin independently supplied specialist JSON with the saved CC step.

    Never trust a carried continuation as authority: deterministically replay
    its pre-return case and require identical next handoff before proceeding.
    Returns one next validated session, not a Project call or archive write.
    """
    if (not isinstance(envelope, dict)
            or set(envelope) != {"continuation_private", "specialist_result"}):
        raise ValueError("MANUAL_RESUME_ENVELOPE_INVALID")
    continuation = envelope["continuation_private"]
    returned = envelope["specialist_result"]
    if (not isinstance(continuation, dict)
            or set(continuation) != {
                "status", "next_handoff", "resume_input", "replace_null_with",
                "readiness", "storage", "project_invocation", "trading_authority",
            }
            or continuation.get("status") != "PRIVATE_MANUAL_CONTINUATION_NOT_SENT"
            or continuation.get("readiness") != "NOT_EVALUATED"
            or continuation.get("storage") != "NONE"
            or continuation.get("project_invocation") != "NONE"
            or continuation.get("trading_authority") != "NONE"):
        raise ValueError("MANUAL_RESUME_ENVELOPE_INVALID")
    resume = continuation.get("resume_input")
    handoff = continuation.get("next_handoff")
    if (not isinstance(resume, dict)
            or resume.get("specialist_result", "MISSING") is not None
            or not isinstance(handoff, dict)
            or len(handoff) != 1
            or not isinstance(returned, dict)):
        raise ValueError("MANUAL_RESUME_ENVELOPE_INVALID")
    stage = continuation.get("replace_null_with")
    label = "IR_REQUEST" if stage == "IR_CAPSULE" else (
        "PI_REQUEST" if stage == "PI_DELTA" else None)
    if label is None or set(handoff) != {label}:
        raise ValueError("MANUAL_RESUME_STAGE_MISMATCH")

    # Re-evaluate the original unsatisfied step before accepting new evidence.
    # This prevents a forged, stale or internally inconsistent handoff from
    # being reused as a different case or a silently skipped IR/PI stage.
    before = deepcopy(resume)
    del before["specialist_result"]
    replay = evaluate(before)
    actual = _prepare_manual_continuation(before, replay)
    if actual != continuation:
        raise ValueError("MANUAL_RESUME_CONTINUATION_MISMATCH")

    if stage == "IR_CAPSULE":
        allowed = {"IR_CAPSULE"}
    elif before["request"].get("research_needed") is True:
        allowed = {"PI_DELTA", "FORWARD_UNCHANGED"}
    else:
        allowed = {"PI_DELTA"}
    if set(returned) != allowed:
        raise ValueError("MANUAL_RESUME_STAGE_MISMATCH")
    current = deepcopy(resume)
    current["specialist_result"] = deepcopy(returned)
    return current, evaluate(current)



_FOLLOWUP_SAFE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,79}\Z")


def _reenter_sealed_followup(envelope: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    """Explicitly recover a checksum-matched case for a NEW CEO follow-up.

    Restored history is used only as a supplied private comparison baseline;
    no prior request, account context, holdings, costs, or IR conclusion is
    promoted into the fresh mandate. The checksum is not authentication.
    """
    if (not isinstance(envelope, dict)
            or set(envelope) != {"private_case_envelope", "session", "fact_links"}
            or not isinstance(envelope["session"], dict)):
        raise ValueError("SEALED_FOLLOWUP_INPUT_INVALID")
    case = verify_private_case_envelope(envelope["private_case_envelope"])
    # Reuse the independently checked original-request/fact/date contract.
    draft = prepare_explicit_followup_draft(case)
    inherited = draft["input_template"]["request"]
    current = deepcopy(envelope["session"])
    req = current.get("request")
    if not isinstance(req, dict):
        raise ValueError("SEALED_FOLLOWUP_INPUT_INVALID")
    if (req.get("ceo_initiated") is not True
            or req.get("research_needed") is not True
            or req.get("kind") != "FOLLOWUP"):
        raise ValueError("SEALED_FOLLOWUP_EXPLICIT_MANDATE_REQUIRED")
    new_id = req.get("analysis_id")
    if (req.get("subject_id") != inherited["subject_id"]
            or req.get("prior_analysis_id") != inherited["prior_analysis_id"]
            or not isinstance(new_id, str)
            or new_id == inherited["prior_analysis_id"]):
        raise ValueError("SEALED_FOLLOWUP_PRIOR_ID_OR_SUBJECT_MISMATCH")
    raw_date = req.get("as_of")
    try:
        current_date = date.fromisoformat(raw_date)
        if (not isinstance(raw_date, str) or current_date.isoformat() != raw_date
                or raw_date < case["recorded_at"]):
            raise ValueError
    except (ValueError, TypeError) as exc:
        raise ValueError("SEALED_FOLLOWUP_DATE_INVALID") from exc
    links = envelope["fact_links"]
    if (not isinstance(links, list) or len(links) > 100
            or any(not isinstance(link, dict)
                   or set(link) != {"prior_fact_id", "current_fact_id"}
                   or any(not isinstance(link[key], str)
                          or not _FOLLOWUP_SAFE_ID.fullmatch(link[key])
                          for key in ("prior_fact_id", "current_fact_id"))
                   for link in links)):
        raise ValueError("SEALED_FOLLOWUP_FACT_LINKS_INVALID")
    if "historical_comparison_inputs" in current:
        raise ValueError("SEALED_FOLLOWUP_INPUT_INVALID")
    current["historical_comparison_inputs"] = {
        "prior_case": case, "subject_id": inherited["subject_id"],
        "fact_links": deepcopy(links)}
    # Existing session bridge and source/IR/PI checks remain authoritative,
    # including when the new IR capsule is still pending.
    return current, evaluate(current)


def _selected_guided_private_route(payload: Any) -> str:
    """Select ONE already-implemented private closeout from the real mandate.

    This is routing only, never authorization. Nested saved CC continuations
    belong to the same existing user request; refuse conflicting sources,
    ambiguous envelopes and direct/no-specialist sessions.
    """
    if not isinstance(payload, dict):
        raise ValueError("GUIDED_PRIVATE_ROUTE_REQUEST_INVALID")
    sources: list[Any] = []
    if "request" in payload:
        sources.append(payload["request"])
    if "session" in payload:
        nested = payload["session"]
        sources.append(nested.get("request") if isinstance(nested, dict) else None)
    if "pending_session" in payload:
        nested = payload["pending_session"]
        sources.append(nested.get("request") if isinstance(nested, dict) else None)
    if "continuation_private" in payload:
        continuation = payload["continuation_private"]
        resume = (continuation.get("resume_input")
                  if isinstance(continuation, dict) else None)
        sources.append(resume.get("request") if isinstance(resume, dict) else None)
    if len(sources) != 1 or not isinstance(sources[0], dict):
        raise ValueError("GUIDED_PRIVATE_ROUTE_REQUEST_INVALID")
    mandate = sources[0]
    ir = mandate.get("research_needed")
    pi = mandate.get("portfolio_needed")
    if type(ir) is not bool or type(pi) is not bool:
        raise ValueError("GUIDED_PRIVATE_ROUTE_REQUEST_INVALID")
    if ir and pi:
        return "guided-integrated-closeout"
    if ir:
        return "guided-research-closeout"
    if pi:
        return "guided-portfolio-closeout"
    raise ValueError("GUIDED_PRIVATE_ROUTE_SPECIALIST_REQUIRED")


def run(*, output: str, instream: TextIO, outstream: TextIO,
        errstream: TextIO) -> int:
    """Read one bounded JSON payload from stdin, send results to stdout only."""
    if output == "request-template":
        # No stdin is read: this is an inert, non-secret starting point.
        outstream.write(json.dumps(_inert_new_case_template(), ensure_ascii=False,
                                   sort_keys=True, indent=2, allow_nan=False) + "\n")
        return 0
    guided_resuming = False
    guided_sealed_followup = False
    guided_integrated_followup = False
    try:
        raw = instream.read(MAX_INPUT_CHARACTERS + 1)
        if len(raw) > MAX_INPUT_CHARACTERS:
            raise ValueError("INPUT_TOO_LARGE")
        payload = json.loads(raw, parse_constant=_no_nonfinite,
                             parse_float=_finite_json_float,
                             object_pairs_hook=_unique_pairs)
        if output == "guided-private-closeout":
            # The only new UX selector is a strict, private, no-action
            # dispatch to the THREE unchanged existing closeout engines.
            # Every downstream CEO/source/method check remains mandatory.
            output = _selected_guided_private_route(payload)
        if output == "intake-review":
            # Inspect only a request draft; never run a specialist or create
            # a session. No input values are copied to the review.
            intake = prepare_intake_review(payload)
            result = None
        elif output == "candidate-deep-dive-draft":
            # Re-evaluate the real prior CEO/IR case, including M2 original
            # facts, provenance and candidate triage. Never accept an isolated
            # triage JSON as a claimed original or initiate research on behalf
            # of the CEO. Only the chosen candidate enters the PRIVATE draft.
            if (not isinstance(payload, dict)
                    or set(payload) != {"session", "candidate_id"}
                    or not isinstance(payload["session"], dict)
                    or not isinstance(payload["candidate_id"], str)):
                raise ValueError("CANDIDATE_DRAFT_INPUT_INVALID")
            prior = evaluate(payload["session"])
            integrated = prior.get("integrated_private")
            if (prior.get("status") !=
                    "M7A_COMPONENT_ASSEMBLED_NOT_END_TO_END_ACCEPTANCE"
                    or not isinstance(integrated, dict)
                    or not isinstance(integrated.get("opportunity_triage_private"), dict)):
                raise ValueError("CANDIDATE_DRAFT_TRIAGE_UNAVAILABLE")
            draft = prepare_selected_candidate_draft(
                integrated["opportunity_triage_private"], payload["candidate_id"])
            result = None
        elif output == "followup-draft":
            # Unchanged support for unwrapped historical PRIVATE cases.
            if not isinstance(payload, dict) or set(payload) != {"prior_private_case"}:
                raise ValueError("FOLLOWUP_PRIOR_CASE_ENVELOPE_REQUIRED")
            draft = prepare_explicit_followup_draft(payload["prior_private_case"])
            result = None
        elif output == "sealed-followup-draft":
            if not isinstance(payload, dict) or set(payload) != {"private_case_envelope"}:
                raise ValueError("PRIVATE_CASE_ENVELOPE_REQUIRED")
            recovered = verify_private_case_envelope(payload["private_case_envelope"])
            draft = prepare_explicit_followup_draft(recovered)
            # Checksum is accidental-change detection, not authenticated history.
            draft["manual_copy_integrity"] = "SHA256_MATCHED_RETAINED_COPY_ONLY"
            draft["record_authenticity"] = "NOT_ESTABLISHED"
            result = None
        elif output == "portfolio-followup-draft":
            # One human-retained original M3 envelope only; never an
            # inferred portfolio account, current holding or CEO mandate.
            if (not isinstance(payload, dict)
                    or set(payload) != {"private_portfolio_snapshot_envelope"}):
                raise ValueError("PRIVATE_PORTFOLIO_ENVELOPE_INVALID")
            draft = _portfolio_followup_draft(
                payload["private_portfolio_snapshot_envelope"])
            result = None
        elif output == "integrated-followup-draft":
            if (not isinstance(payload, dict)
                    or set(payload) != {"prior_integrated_closeout"}):
                raise ValueError("INTEGRATED_PRIOR_CLOSEOUT_INVALID")
            draft = _integrated_followup_draft(payload["prior_integrated_closeout"])
            result = None
        elif output == "integrated-followup-operator":
            restored_payload, result = _integrated_followup_operator(payload)
        elif output == "resume-operator":
            resume_payload, result = _resume_manual_transfer(payload)
        elif (output in {"private-closeout", "private-integrated-closeout"}
              and isinstance(payload, dict)
              and "continuation_private" in payload):
            # The same independently checked PI/IR resume path; never use
            # PI's forwarded copy as a substitute for original IR.
            resume_payload, result = _resume_manual_transfer(payload)
        elif output == "sealed-followup-operator":
            restored_payload, result = _reenter_sealed_followup(payload)
        elif (output == "guided-portfolio-closeout"
              and isinstance(payload, dict)
              and "private_portfolio_snapshot_envelope" in payload):
            # Explicit new CEO PI-only follow-up from a checked old M3 copy.
            # No manual previous-envelope retyping into the new session.
            guided_resuming = True
            guided_sealed_followup = True
            resume_payload, result = _reenter_portfolio_followup(payload)
        elif (output in {"guided-operator", "guided-integrated-closeout", "guided-portfolio-closeout"} and isinstance(payload, dict)
              and "pending_session" in payload):
            # One explicit human-entered visual fallback. The validated
            # source is an already transcribed dated screenshot, not a
            # reopened Work browser or an inferred account state.
            guided_resuming = True
            resume_payload, result = _reenter_manual_screenshot(payload)
        elif (output in {"guided-operator", "guided-integrated-closeout"} and isinstance(payload, dict)
              and "prior_integrated_closeout" in payload):
            # Start a NEW CEO-initiated IR+PI follow-up directly from the
            # opt-in historical two-envelope re-entry. The existing guided
            # operator then checks the real next IR/PI method content before
            # rendering the one copy-ready specialist prompt. Prior holdings
            # and original research remain in CC-only resume_input, not prompt.
            guided_resuming = True
            guided_sealed_followup = True
            guided_integrated_followup = True
            resume_payload, result = _integrated_followup_operator(payload)
        elif (output in {"guided-operator", "guided-integrated-closeout", "guided-research-closeout"} and isinstance(payload, dict)
              and "private_case_envelope" in payload):
            # Reuse the SAME strict sealed-case re-entry plus verified-method
            # guided prompt path. The old case remains in CC-only continuation,
            # never in the receiving specialist's next handoff or prompt.
            guided_resuming = True
            guided_sealed_followup = True
            resume_payload, result = _reenter_sealed_followup(payload)
        elif (output in {"guided-operator", "guided-integrated-closeout", "guided-research-closeout", "guided-portfolio-closeout"} and isinstance(payload, dict)
              and ("continuation_private" in payload
                   or ("specialist_result" in payload and "request" not in payload))):
            guided_resuming = True
            resume_payload, result = _resume_manual_transfer(payload)
        else:
            result = evaluate(payload)
        if output == "guided-portfolio-closeout":
            _preflight_guided_portfolio_closeout(
                resume_payload if guided_resuming else payload, result)
        if output == "guided-research-closeout":
            _preflight_guided_research_closeout(
                resume_payload if guided_resuming else payload, result)
        if output == "guided-integrated-closeout":
            # Check the COMPLETE and replayable private session before the
            # first costly human transfer. No partial prompt/record on failure.
            _preflight_guided_private_closeout(
                resume_payload if guided_resuming else payload, result)
    except (ValueError, TypeError, KeyError, RecursionError) as exc:
        errstream.write("R1_INPUT_REJECTED: " + _code(exc) + "\n")
        return 2
    except Exception:
        # Preserve user confidentiality even if a component has an unexpected
        # exception with financial information in its message.
        errstream.write("R1_PROCESSING_ERROR: details suppressed; inspect locally.\n")
        return 3

    if output == "intake-review":
        outstream.write(json.dumps(intake, ensure_ascii=False, sort_keys=True,
                                   indent=2, allow_nan=False) + "\n")
    elif output in {"followup-draft", "sealed-followup-draft", "integrated-followup-draft",
                   "portfolio-followup-draft", "candidate-deep-dive-draft"}:
        # Explicitly PRIVATE. The returned request is intentionally invalid
        # for execution until the CEO fills new details and initiates it.
        outstream.write(json.dumps(draft, ensure_ascii=False, sort_keys=True,
                                   indent=2, allow_nan=False) + "\n")
    elif output == "status":
        outstream.write(json.dumps(_redacted_status(result),
                                   ensure_ascii=False, sort_keys=True) + "\n")
    elif output == "private-portfolio-snapshot":
        # PRIVATE: existing M3 copy contract, now shared with full closeout.
        try:
            envelope = _sealed_current_private_portfolio(payload, result)
            encoded = json.dumps(envelope, ensure_ascii=False, sort_keys=True,
                                 indent=2, allow_nan=False)
            if len(encoded) > MAX_INPUT_CHARACTERS:
                raise ValueError("PRIVATE_PORTFOLIO_OUTPUT_TOO_LARGE")
            outstream.write(encoded + "\n")
        except (ValueError, TypeError, KeyError, RecursionError):
            errstream.write("R1_PROCESSING_ERROR: private portfolio snapshot unavailable; "
                            "complete current PI and original private observation required.\n")
            return 3
    elif output in {"private-closeout", "private-integrated-closeout"}:
        # The new combined mode MUST be expressly selected; the old research
        # closeout never silently adds holdings. Both have no storage.
        try:
            closeout_payload = (resume_payload if
                                "continuation_private" in payload else payload)
            closeout = (_private_integrated_closeout(closeout_payload, result)
                        if output == "private-integrated-closeout" else
                        _private_research_closeout(closeout_payload, result))
            encoded = json.dumps(closeout, ensure_ascii=False, sort_keys=True,
                                 indent=2, allow_nan=False)
            if len(encoded) > MAX_INPUT_CHARACTERS:
                raise ValueError("PRIVATE_CLOSEOUT_OUTPUT_TOO_LARGE")
            outstream.write(encoded + "\n")
        except (ValueError, TypeError, KeyError, RecursionError):
            if output == "private-closeout":
                # Backward-compatible privacy-safe error for existing clients.
                errstream.write("R1_PROCESSING_ERROR: private research closeout unavailable; "
                                "complete original IR and explicit memory_inputs required.\n")
            else:
                errstream.write("R1_PROCESSING_ERROR: private integrated closeout unavailable; "
                                "complete IR, dated PI observation and explicit "
                                "memory_inputs required.\n")
            return 3
    elif output in {"operator-packet", "resume-operator", "sealed-followup-operator",
                   "integrated-followup-operator"}:
        # PRIVATE opt-in. Resume reuses exactly the original validated operator
        # packet contract after a separate, manually received specialist result.
        try:
            case_payload = (resume_payload if output == "resume-operator"
                            else restored_payload if output in {
                                "sealed-followup-operator", "integrated-followup-operator"}
                            else payload)
            packet = _private_operator_packet(case_payload, result)
            if output in {"sealed-followup-operator", "integrated-followup-operator"}:
                packet["manual_copy_integrity"] = "SHA256_MATCHED_RETAINED_COPY_ONLY"
                packet["record_authenticity"] = "NOT_ESTABLISHED"
            encoded = json.dumps(packet, ensure_ascii=False, sort_keys=True,
                                 indent=2, allow_nan=False)
            if len(encoded) > MAX_INPUT_CHARACTERS:
                raise ValueError("OPERATOR_PACKET_TOO_LARGE")
            outstream.write(encoded + "\n")
        except (ValueError, TypeError, KeyError, RecursionError):
            errstream.write("R1_PROCESSING_ERROR: private operator packet unavailable.\n")
            return 3
    elif output in {"guided-operator", "guided-integrated-closeout", "guided-research-closeout", "guided-portfolio-closeout"}:
        # One explicitly PRIVATE packet from the existing operator and method
        # components. Assemble fully before emitting any sensitive output.
        try:
            actual_payload = resume_payload if guided_resuming else payload
            operator = _private_operator_packet(actual_payload, result)
            if guided_sealed_followup:
                operator["manual_copy_integrity"] = (
                    "TWO_UNKEYED_SHA256_COPIES_MATCHED_RETAINED_ONLY"
                    if guided_integrated_followup else
                    "SHA256_MATCHED_RETAINED_COPY_ONLY"
                )
                operator["record_authenticity"] = "NOT_ESTABLISHED"
            continuation = operator["continuation_private"]
            prompt = None
            specialist = None
            if continuation is not None:
                bundle = prepare_verified_method_handoff(continuation)
                prompt = render_manual_specialist_prompt(bundle)
                specialist = next(iter(continuation["next_handoff"]))
            screenshot_retry = _screenshot_retry_template(actual_payload, result)
            guided = {
                "status": "PRIVATE_GUIDED_OPERATOR_PACKET_NOT_SENT",
                "screenshot_reentry_input_private": screenshot_retry,
                "operator_packet_private": operator,
                "specialist_prompt_private": prompt,
                "specialist_step": specialist,
                "copy_to_specialist": (
                    "specialist_prompt_private" if prompt is not None else "NONE"
                ),
                "cc_continuation_must_remain_private": True,
                "project_invocation": "NONE",
                "storage": "NONE",
                "readiness": "NOT_EVALUATED",
                "trading_authority": "NONE",
                "method_load_verification": "NOT_PERFORMED",
                "source_authentication": "NOT_PERFORMED",
            }
            if output == "guided-portfolio-closeout":
                # The PI-only path carries a single M3 copy and conditional
                # CC report with the original private scoped observation,
                # never an IR case, forced research or automatic archive.
                final_portfolio = (
                    _private_portfolio_closeout(actual_payload, result)
                    if continuation is None else None
                )
                guided = {
                    "status": (
                        "PRIVATE_GUIDED_PORTFOLIO_CLOSEOUT_COPY_NOT_STORED"
                        if final_portfolio is not None else
                        "PRIVATE_GUIDED_PORTFOLIO_CLOSEOUT_PENDING_MANUAL_PI"
                    ),
                    "guided_operator_private": guided,
                    "private_portfolio_closeout": final_portfolio,
                    "next_manual_step": (
                        "HUMAN_REVIEW_THEN_SAVE_ONLY_IN_APPROVED_PRIVATE_ARCHIVE"
                        if final_portfolio is not None else
                        "COPY_ONLY_PI_PROMPT_AND_KEEP_CC_RESUME_PRIVATE"
                    ),
                    "archive_protection": "NOT_ESTABLISHED",
                    "source_authentication": "NOT_PERFORMED",
                    "project_invocation": "NONE",
                    "storage": "NONE",
                    "readiness": "NOT_EVALUATED",
                    "trading_authority": "NONE",
                }
            if output == "guided-research-closeout":
                # Keep IR-only research and manual archiving in one explicit
                # user-selected private route; same archive as private-closeout.
                # Final copy stays null during IR handoff.
                final_research = (
                    _private_research_closeout(actual_payload, result)
                    if continuation is None else None
                )
                guided = {
                    "status": (
                        "PRIVATE_GUIDED_RESEARCH_CLOSEOUT_COPY_NOT_STORED"
                        if final_research is not None else
                        "PRIVATE_GUIDED_RESEARCH_CLOSEOUT_PENDING_MANUAL_IR"
                    ),
                    "guided_operator_private": guided,
                    "private_research_closeout": final_research,
                    "next_manual_step": (
                        "HUMAN_REVIEW_THEN_SAVE_ONLY_IN_APPROVED_PRIVATE_ARCHIVE"
                        if final_research is not None else
                        "COPY_ONLY_IR_PROMPT_AND_KEEP_CC_RESUME_PRIVATE"
                    ),
                    "archive_protection": "NOT_ESTABLISHED",
                    "source_authentication": "NOT_PERFORMED",
                    "project_invocation": "NONE",
                    "storage": "NONE",
                    "readiness": "NOT_EVALUATED",
                    "trading_authority": "NONE",
                }
            if output == "guided-integrated-closeout":
                # One *explicit* private surface from initial manual IR/PI
                # prompts to final report and both original archive copies.
                # Do not export anything until the full IR+PI route completes.
                # Missing explicit memory/M3 inputs fail closed on completion.
                # The old guided-operator output never silently includes
                # holdings or the two plaintext archive records.
                final_copy = (
                    _private_integrated_closeout(actual_payload, result)
                    if continuation is None else None
                )
                guided = {
                    "status": (
                        "PRIVATE_GUIDED_INTEGRATED_CLOSEOUT_COPY_NOT_STORED"
                        if final_copy is not None else
                        "PRIVATE_GUIDED_INTEGRATED_CLOSEOUT_PENDING_MANUAL_HANDOFF"
                    ),
                    "guided_operator_private": guided,
                    "private_integrated_closeout": final_copy,
                    "next_manual_step": (
                        "HUMAN_REVIEW_THEN_SAVE_ONLY_IN_APPROVED_PRIVATE_ARCHIVE"
                        if final_copy is not None else
                        "COPY_ONLY_SPECIALIST_PROMPT_AND_KEEP_CC_RESUME_PRIVATE"
                    ),
                    "archive_protection": "NOT_ESTABLISHED",
                    "source_authentication": "NOT_PERFORMED",
                    "project_invocation": "NONE",
                    "storage": "NONE",
                    "readiness": "NOT_EVALUATED",
                    "trading_authority": "NONE",
                }
            encoded = json.dumps(guided, ensure_ascii=False, sort_keys=True,
                                 indent=2, allow_nan=False)
            if len(encoded) > MAX_INPUT_CHARACTERS:
                raise ValueError("GUIDED_OPERATOR_OUTPUT_TOO_LARGE")
            outstream.write(encoded + "\n")
        except (ValueError, TypeError, KeyError, RecursionError, OSError):
            errstream.write(
                "R1_PROCESSING_ERROR: private guided operator packet unavailable; "
                "check input and pinned local methods.\n"
            )
            return 3
    elif output in {"method-handoff", "specialist-prompt"}:
        # Both modes validate exactly the same real next handoff and locally
        # pinned method texts; specialist-prompt omits CC-only resume context.
        try:
            continuation = _prepare_manual_continuation(payload, result)
            if continuation is None:
                label = ("SPECIALIST_PROMPT_NOT_AVAILABLE" if
                         output == "specialist-prompt" else
                         "METHOD_HANDOFF_NOT_AVAILABLE")
                outstream.write(label + ": " + result["status"] + "\n")
            else:
                bundle = prepare_verified_method_handoff(continuation)
                if output == "specialist-prompt":
                    encoded = render_manual_specialist_prompt(bundle)
                else:
                    encoded = json.dumps(bundle, ensure_ascii=False, sort_keys=True,
                                         indent=2, allow_nan=False) + "\n"
                if len(encoded) > MAX_INPUT_CHARACTERS:
                    raise ValueError("METHOD_HANDOFF_OUTPUT_TOO_LARGE")
                outstream.write(encoded)
        except (ValueError, TypeError, KeyError, RecursionError, OSError):
            errstream.write("R1_PROCESSING_ERROR: private method handoff unavailable; " +
                            "check local method files and pinned versions.\n")
            return 3
    elif output in {"report", "executive-report", "pamalised-html", "pamalised-pdf"}:
        report = (result["executive_report_private"]
                  if output in {"executive-report", "pamalised-html", "pamalised-pdf"}
                  else result["final_report_private"])
        if report is None:
            outstream.write("REPORT_NOT_AVAILABLE: " + result["status"] + "\n")
        elif output in {"pamalised-html", "pamalised-pdf"}:
            # PRIVATE and in-memory only. The original validated executive/detail
            # pair is mandatory; no filesystem write, external asset or PDF claim.
            try:
                match = re.search(
                    r"(?m)^\*\*Statut :\*\* (EXPLORATORY|CONDITIONAL|COMPONENT_SUPPORTED)\b",
                    report)
                if match is None or not isinstance(payload, dict):
                    raise ValueError("PAMALISED_REPORT_STATUS_UNAVAILABLE")
                request = payload["request"]
                body = render_pamalised_html(
                    executive_report=report,
                    detailed_report=result["final_report_private"],
                    analysis_id=request["analysis_id"],
                    as_of=request["as_of"],
                    strategy=request["strategy_id"],
                    report_status=match.group(1),
                )
                if output == "pamalised-html":
                    outstream.write(body)
                else:
                    pdf = render_pamalised_pdf(
                        executive_report=report,
                        detailed_report=result["final_report_private"],
                        analysis_id=request["analysis_id"],
                        as_of=request["as_of"],
                        strategy=request["strategy_id"],
                        report_status=match.group(1),
                        request=request,
                        ir_capsule=payload.get("ir_capsule"),
                        pi_delta=payload.get("pi_delta"),
                        new_contribution_summary_private=(
                            result.get("integrated_private", {}) or {}
                        ).get("new_contribution_summary_private"),
                    )
                    sink = getattr(outstream, "buffer", None)
                    if sink is None:
                        raise ValueError("PAMALISED_BINARY_STDOUT_REQUIRED")
                    sink.write(pdf)
            except (ValueError, TypeError, KeyError, RecursionError, RuntimeError):
                errstream.write(
                    "R1_PROCESSING_ERROR: private PAMalised report unavailable.\n")
                return 3
        else:
            outstream.write(report + ("\n" if not report.endswith("\n") else ""))
    elif output == "review-queue":
        # Deterministic privacy-minimal human tasks, not source certification.
        outstream.write(json.dumps(prepare_manual_review_queue(result),
                                   ensure_ascii=False, sort_keys=True,
                                   indent=2, allow_nan=False) + "\n")
    elif output in {"private-case", "private-case-envelope"}:
        # User-selected PRIVATE copy only, never a write to disk or GitHub.
        record, error = _eligible_private_case(result)
        if record is None:
            outstream.write(error + "\n")
        elif output == "private-case":
            outstream.write(json.dumps(record, ensure_ascii=False,
                                       sort_keys=True, indent=2, allow_nan=False) + "\n")
        else:
            try:
                envelope = seal_private_case(record)
                encoded = json.dumps(envelope, ensure_ascii=False, sort_keys=True,
                                     indent=2, allow_nan=False)
                if len(encoded) > MAX_INPUT_CHARACTERS:
                    raise ValueError("PRIVATE_CASE_ENVELOPE_TOO_LARGE")
                outstream.write(encoded + "\n")
            except (ValueError, TypeError, KeyError, RecursionError):
                errstream.write("R1_PROCESSING_ERROR: private case integrity package unavailable.\n")
                return 3

    elif output == "continuation":
        # Explicitly PRIVATE: a single portable next handoff together with
        # re-entry context. No automatic memory, persistent state or call.
        try:
            bundle = _prepare_manual_continuation(payload, result)
            if bundle is None:
                outstream.write("CONTINUATION_NOT_AVAILABLE: " + result["status"] + "\n")
            else:
                encoded_resume = json.dumps(bundle["resume_input"], ensure_ascii=False,
                                            sort_keys=True, allow_nan=False)
                if len(encoded_resume) > MAX_INPUT_CHARACTERS:
                    raise ValueError("CONTINUATION_INPUT_TOO_LARGE")
                outstream.write(json.dumps(bundle, ensure_ascii=False, sort_keys=True,
                                           indent=2, allow_nan=False) + "\n")
        except (ValueError, TypeError, KeyError, RecursionError):
            errstream.write("R1_PROCESSING_ERROR: private continuation unavailable.\n")
            return 3
    elif output == "next-handoff":
        # Only the actionable next transfer. In particular, never offer PI
        # before IR, or when an unavailable visual source requires a screenshot.
        label = {
            "AWAITING_MANUAL_IR_CAPSULE": "IR_REQUEST",
            "AWAITING_MANUAL_PI_DELTA": "PI_REQUEST",
        }.get(result["status"])
        if label is None:
            outstream.write("NEXT_HANDOFF_NOT_AVAILABLE: " + result["status"] + "\n")
        else:
            raw_packet = result["handoffs_private"]["copy_ready_private"].get(label)
            if not isinstance(raw_packet, str):
                errstream.write("R1_PROCESSING_ERROR: next handoff packet unavailable.\n")
                return 3
            outstream.write(json.dumps({
                label: json.loads(raw_packet, parse_constant=_no_nonfinite,
                                  parse_float=_finite_json_float,
                                  object_pairs_hook=_unique_pairs)
            }, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n")
    elif output == "handoffs":
        handoffs = result["handoffs_private"]["copy_ready_private"]
        # These packets may include private research/account context and are
        # displayed only when specifically requested, never saved automatically.
        outstream.write(json.dumps({
            label: json.loads(value, parse_constant=_no_nonfinite,
                              parse_float=_finite_json_float,
                              object_pairs_hook=_unique_pairs)
            for label, value in handoffs.items()
        }, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    else:
        raise ValueError("OUTPUT_MODE_UNSUPPORTED")
    return 0


def main(argv: list[str] | None = None, *, instream: TextIO | None = None,
         outstream: TextIO | None = None,
         errstream: TextIO | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", choices=("request-template", "intake-review", "status", "report", "executive-report", "pamalised-html", "pamalised-pdf", "handoffs", "next-handoff", "continuation", "operator-packet", "resume-operator", "guided-operator", "guided-integrated-closeout", "guided-research-closeout", "guided-portfolio-closeout", "guided-private-closeout", "candidate-deep-dive-draft", "method-handoff", "specialist-prompt", "followup-draft", "sealed-followup-draft", "sealed-followup-operator", "integrated-followup-draft", "portfolio-followup-draft", "integrated-followup-operator", "private-case", "private-case-envelope", "private-closeout", "private-integrated-closeout", "private-portfolio-snapshot", "review-queue"),
                        default="status",
                        help="request-template is an inert blank case and reads no stdin; intake-review reads a private request-only draft and returns field names/status without values; status is redacted; report, executive-report, pamalised-html, pamalised-pdf (binary stdout), handoffs, next-handoff, continuation, operator-packet, resume-operator, guided-operator, guided-integrated-closeout, guided-research-closeout, guided-portfolio-closeout, guided-private-closeout, candidate-deep-dive-draft, method-handoff, specialist-prompt, followup-draft, sealed-followup-draft, sealed-followup-operator, integrated-followup-draft, portfolio-followup-draft, integrated-followup-operator, private-case, private-case-envelope, private-closeout, private-integrated-closeout, private-portfolio-snapshot and review-queue require a private terminal")
    opts = parser.parse_args(argv)
    return run(output=opts.output, instream=instream or sys.stdin,
               outstream=outstream or sys.stdout, errstream=errstream or sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
