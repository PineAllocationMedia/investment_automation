"""Privacy-minimal, non-authorizing preflight for a CEO-filled R1 request draft.

This deliberately inspects only a {request} envelope. The existing M1 manual
handoff constructor remains the structural authority after a draft is filled.
No source, browser, method loading, Projects, archive, or portfolio operations.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Mapping

from .request_assembly import prepare_manual_handoffs
from .strategy_authority import assess_r1_mode

TEXT_FIELDS = ("analysis_id", "as_of", "kind", "objective", "strategy_id")
ROUTE_FLAGS = ("research_needed", "portfolio_needed")
ACCOUNT_FIELDS = ("type", "broker", "tax", "commission", "fx_cost")


def _is_canonical_date(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def _unknown(value: Any) -> bool:
    return not isinstance(value, str) or not value.strip() or value.strip().upper() in {
        "UNKNOWN", "NOT_SUPPLIED", "UNKNOWN_NOT_LOADED",
    }


def prepare_intake_review(envelope: Any) -> dict[str, Any]:
    """Return static field names and authority flags, *never* request values.

    An incomplete draft is not an error: it remains inert until the CEO
    explicitly initiates and an unchanged M1 validator accepts the request.
    """
    if not isinstance(envelope, Mapping) or set(envelope) != {"request"}:
        raise ValueError("INTAKE_REVIEW_ENVELOPE_INVALID")
    request = envelope["request"]
    if not isinstance(request, Mapping):
        raise ValueError("INTAKE_REVIEW_ENVELOPE_INVALID")

    required: list[str] = []
    for field in TEXT_FIELDS:
        if not isinstance(request.get(field), str) or not request[field].strip():
            required.append("request." + field)
    if request.get("ceo_initiated") is not True:
        required.append("request.ceo_initiated")
    for flag in ROUTE_FLAGS:
        if type(request.get(flag)) is not bool:
            required.append("request." + flag)
    if isinstance(request.get("kind"), str) and request["kind"].strip():
        if request["kind"] not in {"DECISION", "FOLLOWUP"}:
            required.append("request.kind")
    if isinstance(request.get("as_of"), str) and request["as_of"].strip():
        if not _is_canonical_date(request["as_of"]):
            required.append("request.as_of")

    policy = "NOT_SELECTED"
    strategy = request.get("strategy_id")
    if isinstance(strategy, str) and strategy.strip():
        try:
            policy = assess_r1_mode(strategy)["policy_authority"]
        except ValueError:
            required.append("request.strategy_id")

    advisory: list[str] = []
    if _unknown(request.get("horizon")):
        advisory.append("CONFIRM_HORIZON")
    if _unknown(request.get("candidate_universe")):
        advisory.append("CONFIRM_UNIVERSE")
    risk = request.get("risk_constraints")
    if not isinstance(risk, list) or not risk:
        advisory.append("CONFIRM_RISK_CONSTRAINTS")
    account = request.get("account_context")
    if not isinstance(account, Mapping):
        advisory.append("CONFIRM_ACCOUNT_CONTEXT")
    else:
        for field in ACCOUNT_FIELDS:
            if _unknown(account.get(field)):
                advisory.append("CONFIRM_ACCOUNT_" + field.upper())
    if request.get("kind") == "FOLLOWUP" and _unknown(request.get("prior_analysis_id")):
        advisory.append("CHECK_FOLLOWUP_BASELINE")
    if policy in {"R1_POLICY_REQUIRES_CEO_APPROVAL", "UNRECOGNIZED_R1_MODE_NO_AUTHORITY"}:
        advisory.append("MODE_POLICY_NOT_APPROVED_OR_RECOGNIZED")
    # Method authenticity/Project loading is NEVER inferred from JSON fields.
    advisory.append("VERIFY_PROJECT_METHOD_LOAD_MANUALLY")

    route = None
    if not required:
        # Reuse the single M1 gate rather than duplicating its schema.
        # Deliberately withhold raw exception detail, which may contain
        # user-supplied private material, before displaying a review.
        try:
            route = prepare_manual_handoffs(request)["route"]
        except (ValueError, TypeError, KeyError, RecursionError):
            required.append("REQUEST_CONTRACT_REVIEW_REQUIRED")
    complete = not required
    return {
        "status": ("INTAKE_STRUCTURALLY_READY_NOT_SENT" if complete
                   else "INTAKE_INCOMPLETE_NOT_SENT"),
        "missing_or_invalid_fields": sorted(set(required)),
        "human_review_codes": sorted(set(advisory)),
        "route_if_valid": route,
        "strategy_policy_authority": policy,
        "ceo_initiation": ("CALLER_ASSERTED_NOT_AUTHENTICATED"
                           if request.get("ceo_initiated") is True
                           else "NOT_ASSERTED"),
        "next_manual_step": ("REVIEW_AND_RUN_GUIDED_OPERATOR_ONLY_IF_CEO_REQUESTED"
                             if complete else "COMPLETE_PRIVATE_REQUEST_DRAFT"),
        "method_load_verification": "NOT_PERFORMED",
        "source_authentication": "NOT_PERFORMED",
        "project_invocation": "NONE",
        "storage": "NONE",
        "trading_authority": "NONE",
        "readiness": "NOT_EVALUATED",
    }
