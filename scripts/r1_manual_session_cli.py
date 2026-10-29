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
from ai_native.manual_review_queue import prepare_manual_review_queue
from ai_native.intake_review import prepare_intake_review
from ai_native.research_memory import prepare_explicit_followup_draft
from ai_native.method_handoff_bundle import (
    prepare_verified_method_handoff, render_manual_specialist_prompt,
)
from ai_native.private_case_integrity import seal_private_case, verify_private_case_envelope

MAX_INPUT_CHARACTERS = 5_000_000
OPTIONAL_FIELDS = frozenset({
    "ir_capsule", "pi_delta", "portfolio_context", "calculation_requests",
    "contribution_inputs", "cost_inputs", "memory_inputs",
    "observation_inputs", "work_blossom_inputs", "public_reference_inputs",
    "public_reference_table_inputs", "exposure_classifications", "room_assessment_inputs",
    "source_evidence_inputs", "valuation_inputs", "probability_inputs", "candidate_comparison_inputs",
    "fundamental_inputs", "historical_comparison_inputs", "opportunity_triage_inputs",
    "macro_sector_inputs", "work_portfolio_result", "specialist_result",
    "lifecycle_inputs", "lifecycle_current_evidence_inputs",
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
              if k not in {"request", "work_portfolio_result", "specialist_result"}}
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
    try:
        raw = instream.read(MAX_INPUT_CHARACTERS + 1)
        if len(raw) > MAX_INPUT_CHARACTERS:
            raise ValueError("INPUT_TOO_LARGE")
        payload = json.loads(raw, parse_constant=_no_nonfinite,
                             parse_float=_finite_json_float,
                             object_pairs_hook=_unique_pairs)
        if output == "intake-review":
            # Inspect only a request draft; never run a specialist or create
            # a session. No input values are copied to the review.
            intake = prepare_intake_review(payload)
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
        elif output == "resume-operator":
            resume_payload, result = _resume_manual_transfer(payload)
        elif output == "sealed-followup-operator":
            restored_payload, result = _reenter_sealed_followup(payload)
        elif (output == "guided-operator" and isinstance(payload, dict)
              and "private_case_envelope" in payload):
            # Reuse the SAME strict sealed-case re-entry plus verified-method
            # guided prompt path. The old case remains in CC-only continuation,
            # never in the receiving specialist's next handoff or prompt.
            guided_resuming = True
            guided_sealed_followup = True
            resume_payload, result = _reenter_sealed_followup(payload)
        elif (output == "guided-operator" and isinstance(payload, dict)
              and ("continuation_private" in payload
                   or ("specialist_result" in payload and "request" not in payload))):
            guided_resuming = True
            resume_payload, result = _resume_manual_transfer(payload)
        else:
            result = evaluate(payload)
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
    elif output in {"followup-draft", "sealed-followup-draft"}:
        # Explicitly PRIVATE. The returned request is intentionally invalid
        # for execution until the CEO fills new details and initiates it.
        outstream.write(json.dumps(draft, ensure_ascii=False, sort_keys=True,
                                   indent=2, allow_nan=False) + "\n")
    elif output == "status":
        outstream.write(json.dumps(_redacted_status(result),
                                   ensure_ascii=False, sort_keys=True) + "\n")
    elif output in {"operator-packet", "resume-operator", "sealed-followup-operator"}:
        # PRIVATE opt-in. Resume reuses exactly the original validated operator
        # packet contract after a separate, manually received specialist result.
        try:
            case_payload = (resume_payload if output == "resume-operator"
                            else restored_payload if output == "sealed-followup-operator"
                            else payload)
            packet = _private_operator_packet(case_payload, result)
            if output == "sealed-followup-operator":
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
    elif output == "guided-operator":
        # One explicitly PRIVATE packet from the existing operator and method
        # components. Assemble fully before emitting any sensitive output.
        try:
            actual_payload = resume_payload if guided_resuming else payload
            operator = _private_operator_packet(actual_payload, result)
            if guided_sealed_followup:
                operator["manual_copy_integrity"] = "SHA256_MATCHED_RETAINED_COPY_ONLY"
                operator["record_authenticity"] = "NOT_ESTABLISHED"
            continuation = operator["continuation_private"]
            prompt = None
            specialist = None
            if continuation is not None:
                bundle = prepare_verified_method_handoff(continuation)
                prompt = render_manual_specialist_prompt(bundle)
                specialist = next(iter(continuation["next_handoff"]))
            guided = {
                "status": "PRIVATE_GUIDED_OPERATOR_PACKET_NOT_SENT",
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
    elif output == "report":
        report = result["final_report_private"]
        if report is None:
            outstream.write("REPORT_NOT_AVAILABLE: " + result["status"] + "\n")
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
    parser.add_argument("--output", choices=("request-template", "intake-review", "status", "report", "handoffs", "next-handoff", "continuation", "operator-packet", "resume-operator", "guided-operator", "method-handoff", "specialist-prompt", "followup-draft", "sealed-followup-draft", "sealed-followup-operator", "private-case", "private-case-envelope", "review-queue"),
                        default="status",
                        help="request-template is an inert blank case and reads no stdin; intake-review reads a private request-only draft and returns field names/status without values; status is redacted; report, handoffs, next-handoff, continuation, operator-packet, resume-operator, guided-operator, method-handoff, specialist-prompt, followup-draft, sealed-followup-draft, sealed-followup-operator, private-case, private-case-envelope and review-queue require a private terminal")
    opts = parser.parse_args(argv)
    return run(output=opts.output, instream=instream or sys.stdin,
               outstream=outstream or sys.stdout, errstream=errstream or sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
