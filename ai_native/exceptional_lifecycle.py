"""Private, exceptional High-CAGR thesis-review packet; never a selling engine.

The CEO initiates an explicit IR+PI request. Only user/specialist supplied
research and scoped portfolio observation are examined. No market-data access,
source certification, thresholds, standing monitoring, orders or storage.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Mapping

EVENTS = frozenset({
    "VOLATILITY_ONLY", "TRANSIENT_INFORMATION_UNCERTAINTY",
    "FUNDAMENTAL_DETERIORATION", "STRUCTURAL_THESIS_BREAK",
    "CONCENTRATION_AND_OPPORTUNITY_COST",
})
VIEWS = frozenset({"HOLD", "PAUSE_ADDS", "REVIEW_TRIM", "REVIEW_EXIT", "UNRESOLVED"})
COST = frozenset({"UNKNOWN", "SUPPLIED_NOT_INDEPENDENTLY_CHECKED"})
FIELDS = frozenset({
    "analysis_id", "review_as_of", "strategy_id", "account_scope",
    "position_p_id", "security_id", "thesis_event", "analyst_reported_view",
    "original_ir_fact_ids", "current_evidence_refs", "fees_status",
    "fx_status", "tax_status", "original_thesis_private",
    "strongest_countercase_private", "next_human_check_private",
})


def _str(raw: Any, field: str, limit: int = 2000) -> str:
    if not isinstance(raw, str) or not raw.strip() or len(raw.strip()) > limit:
        raise ValueError("LIFECYCLE_INVALID_" + field.upper())
    return raw.strip()


def _date(raw: Any, field: str) -> str:
    value = _str(raw, field, 10)
    try:
        if date.fromisoformat(value).isoformat() != value:
            raise ValueError
    except ValueError as exc:
        raise ValueError("LIFECYCLE_DATE_INVALID") from exc
    return value


def prepare_exceptional_lifecycle_review(
    request: Mapping[str, Any], ir_capsule: Mapping[str, Any],
    pi_delta: Mapping[str, Any], observation: Mapping[str, Any],
    inputs: Mapping[str, Any],
) -> dict[str, Any]:
    """A private human-review record, not a sell, trim or allocation proposal."""
    if not all(isinstance(v, Mapping) for v in
               (request, ir_capsule, pi_delta, observation, inputs)):
        raise ValueError("LIFECYCLE_MAPPINGS_REQUIRED")
    if set(inputs) != FIELDS:
        raise ValueError("LIFECYCLE_EXACT_INPUT_SCHEMA_REQUIRED")
    if (request.get("ceo_initiated") is not True
            or request.get("research_needed") is not True
            or request.get("portfolio_needed") is not True
            or request.get("exceptional_lifecycle_review_requested") is not True):
        raise ValueError("LIFECYCLE_EXPLICIT_IR_PI_CEO_REQUEST_REQUIRED")
    strategy = _str(request.get("strategy_id"), "strategy_id", 32)
    # Existing High-CAGR scope only; this helper cannot invent preservation rules.
    if strategy not in {"high-cagr", "High-CAGR", "HIGH_CAGR"}:
        raise ValueError("LIFECYCLE_STRATEGY_POLICY_NOT_APPROVED")
    aid = _str(request.get("analysis_id"), "analysis_id", 90)
    cutoff = _date(request.get("as_of"), "as_of")
    if (inputs.get("analysis_id") != aid or inputs.get("strategy_id") != strategy
            or _date(inputs.get("review_as_of"), "review_as_of") != cutoff
            or ir_capsule.get("analysis_id") != aid or pi_delta.get("analysis_id") != aid
            or observation.get("analysis_id") != aid
            or observation.get("analysis_as_of") != cutoff):
        raise ValueError("LIFECYCLE_CASE_OR_STRATEGY_MISMATCH")
    observed = _date(observation.get("observed_on"), "observed_on")
    if (observed > cutoff or pi_delta.get("portfolio_as_of") != observed
            or observation.get("private_scope") is not True
            or observation.get("verification") != "CALLER_ASSERTED_NOT_INDEPENDENTLY_AUTHENTICATED"):
        raise ValueError("LIFECYCLE_OBSERVATION_AUTHORITY_OR_DATE_MISMATCH")
    account = _str(inputs.get("account_scope"), "account_scope", 160)
    if observation.get("account_scope") != account:
        raise ValueError("LIFECYCLE_ACCOUNT_SCOPE_MISMATCH")
    pid = _str(inputs.get("position_p_id"), "position_p_id", 80)
    security = _str(inputs.get("security_id"), "security_id", 100)
    positions = observation.get("p_ledger_private")
    if not isinstance(positions, list):
        raise ValueError("LIFECYCLE_POSITION_NOT_OBSERVED")
    matching = [row for row in positions if isinstance(row, Mapping) and row.get("p_id") == pid]
    if (len(matching) != 1 or matching[0].get("security_id") != security
            or matching[0].get("account_scope") != account):
        raise ValueError("LIFECYCLE_POSITION_NOT_OBSERVED")
    event = _str(inputs.get("thesis_event"), "thesis_event", 80)
    view = _str(inputs.get("analyst_reported_view"), "analyst_reported_view", 30)
    if event not in EVENTS or view not in VIEWS:
        raise ValueError("LIFECYCLE_UNSUPPORTED_EVENT_OR_VIEW")
    # Neither price drops nor transient uncertainty constitute a sell trigger.
    if (view in {"REVIEW_TRIM", "REVIEW_EXIT"}
            and event in {"VOLATILITY_ONLY", "TRANSIENT_INFORMATION_UNCERTAINTY"}):
        raise ValueError("LIFECYCLE_NO_PRICE_OR_UNCERTAINTY_ONLY_SELL_REVIEW")
    refs = inputs.get("original_ir_fact_ids")
    current = inputs.get("current_evidence_refs")
    if (not isinstance(refs, list) or not refs or len(refs) > 24
            or not isinstance(current, list) or len(current) > 24
            or any(not isinstance(x, str) or not x.strip() or len(x) > 90
                   for x in refs + current)
            or len(set(refs)) != len(refs)
            or len(set(current)) != len(current)):
        raise ValueError("LIFECYCLE_EVIDENCE_LINKS_INVALID")
    ir_facts = ir_capsule.get("facts")
    if not isinstance(ir_facts, list):
        raise ValueError("LIFECYCLE_ORIGINAL_IR_FACTS_REQUIRED")
    fact_status = {f["id"]: f.get("status") for f in ir_facts
                   if isinstance(f, Mapping) and isinstance(f.get("id"), str)}
    if set(refs) - set(fact_status):
        raise ValueError("LIFECYCLE_UNKNOWN_ORIGINAL_IR_FACT")
    for name in ("original_thesis_private", "strongest_countercase_private",
                 "next_human_check_private"):
        _str(inputs.get(name), name)
    for name in ("fees_status", "fx_status", "tax_status"):
        if inputs.get(name) not in COST:
            raise ValueError("LIFECYCLE_COST_BASIS_UNSUPPORTED")
    limitations = []
    if observation.get("known_scope_weights_pct") is None:
        limitations.append("PRIVATE_SCOPED_PORTFOLIO_INCOMPLETE")
    if any(fact_status[fid] in {"MISSING", "CONFLICTED"} for fid in refs):
        limitations.append("ORIGINAL_IR_FACTS_UNRESOLVED")
    if not current:
        limitations.append("NO_CURRENT_EVIDENCE_REFERENCES")
    for name in ("fees_status", "fx_status", "tax_status"):
        if inputs[name] == "UNKNOWN":
            limitations.append(name.upper() + "_UNKNOWN")
    if event in {"VOLATILITY_ONLY", "TRANSIENT_INFORMATION_UNCERTAINTY"}:
        limitations.append("NO_STRUCTURAL_SELL_THESIS_FROM_EVENT")
    # A supplied state is an analyst hypothesis, never model-generated action.
    return {
        "status": ("EVIDENCE_RESOLUTION_NO_ACTION" if limitations
                   else "HUMAN_THESIS_AND_COST_REVIEW_ONLY"),
        "analysis_id": aid, "analysis_as_of": cutoff, "strategy_id": strategy,
        "portfolio_observed_on": observed,
        "account_scope_private": account, "position_p_id_private": pid,
        "security_id_private": security,
        "thesis_event": event, "analyst_reported_view": view,
        "original_ir_fact_ids_private": list(refs),
        "current_evidence_refs_private": list(current),
        "original_thesis_private": inputs["original_thesis_private"],
        "strongest_countercase_private": inputs["strongest_countercase_private"],
        "next_human_check_private": inputs["next_human_check_private"],
        "missing_or_qualified": sorted(set(limitations)),
        "source_authentication": "NOT_PERFORMED",
        "account_and_cost_authentication": "NOT_PERFORMED",
        "portfolio_room_admission": "NONE",
        "allocation_or_sale_proposal": "NONE",
        "trade_authority": "NONE_CEO_ONLY",
        "public_memory_write": "NONE",
    }
