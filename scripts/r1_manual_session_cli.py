"""Explicit, local, private JSON-over-stdin adapter for the existing R1 session.

Use from repository root: python -m scripts.r1_manual_session_cli --output status
No files are created, no processes scheduled, no Projects invoked, no trade made.
The caller must provide genuine, authorized inputs and review all conclusions.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from typing import Any, TextIO

from ai_native.session_bridge import complete_manual_session
from ai_native.manual_review_queue import prepare_manual_review_queue

MAX_INPUT_CHARACTERS = 5_000_000
OPTIONAL_FIELDS = frozenset({
    "ir_capsule", "pi_delta", "portfolio_context", "calculation_requests",
    "contribution_inputs", "cost_inputs", "memory_inputs",
    "observation_inputs", "work_blossom_inputs", "public_reference_inputs",
    "public_reference_table_inputs", "exposure_classifications", "room_assessment_inputs",
    "source_evidence_inputs", "valuation_inputs", "probability_inputs", "candidate_comparison_inputs",
    "fundamental_inputs", "historical_comparison_inputs", "opportunity_triage_inputs",
    "macro_sector_inputs", "work_portfolio_result",
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
})


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
              if k not in {"request", "work_portfolio_result"}}
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
    return complete_manual_session(payload["request"], **fields)


def run(*, output: str, instream: TextIO, outstream: TextIO,
        errstream: TextIO) -> int:
    """Read one bounded JSON payload from stdin, send results to stdout only."""
    try:
        raw = instream.read(MAX_INPUT_CHARACTERS + 1)
        if len(raw) > MAX_INPUT_CHARACTERS:
            raise ValueError("INPUT_TOO_LARGE")
        payload = json.loads(raw, parse_constant=_no_nonfinite,
                             parse_float=_finite_json_float,
                             object_pairs_hook=_unique_pairs)
        result = evaluate(payload)
    except (ValueError, TypeError, KeyError, RecursionError) as exc:
        errstream.write("R1_INPUT_REJECTED: " + _code(exc) + "\n")
        return 2
    except Exception:
        # Preserve user confidentiality even if a component has an unexpected
        # exception with financial information in its message.
        errstream.write("R1_PROCESSING_ERROR: details suppressed; inspect locally.\n")
        return 3

    if output == "status":
        result_status = result["status"]
        outstream.write(json.dumps({
            "status": result_status,
            "route": result["route"],
            "readiness": result["readiness"],
            "project_invocation": result["project_invocation"],
            "storage": result["storage"],
            "source_authentication": result["source_authentication"],
            "next_manual_action": NEXT_ACTIONS.get(result_status, "Review the private packet manually."),
        }, ensure_ascii=False, sort_keys=True) + "\n")
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
    elif output == "private-case":
        # Explicit output is a private PROPOSAL, not a committed archive.
        # Caller decides how to protect it outside GitHub.
        integrated = result.get("integrated_private")
        if not isinstance(integrated, dict):
            outstream.write("PRIVATE_CASE_NOT_AVAILABLE: " + result["status"] + "\n")
        else:
            record = integrated.get("private_research_history_proposal")
            gate = integrated.get("github_memory_review_gate")
            if record is None:
                outstream.write("PRIVATE_CASE_NOT_PREPARED: explicit memory_inputs required.\n")
            elif (not isinstance(record, dict) or not isinstance(gate, dict)
                  or record.get("schema_version") != "RESEARCH_HISTORY_R1"
                  or record.get("privacy_tier") != "PRIVATE_PENDING_REVIEW"
                  or record.get("archive_status") != "PROPOSED_NOT_COMMITTED"
                  or gate.get("approved_for_publication") is not False
                  or gate.get("status") != "WITHHELD_PENDING_HUMAN_PRIVACY_AND_RIGHTS_REVIEW"):
                outstream.write("PRIVATE_CASE_NOT_AVAILABLE: review gate or private status invalid.\n")
            else:
                outstream.write(json.dumps(record, ensure_ascii=False,
                                           sort_keys=True, indent=2, allow_nan=False) + "\n")

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
    parser.add_argument("--output", choices=("status", "report", "handoffs", "next-handoff", "private-case", "review-queue"),
                        default="status",
                        help="status is redacted; report, handoffs, next-handoff, private-case and review-queue require a private terminal")
    opts = parser.parse_args(argv)
    return run(output=opts.output, instream=instream or sys.stdin,
               outstream=outstream or sys.stdout, errstream=errstream or sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
