"""Private, evidence-qualified Portfolio Room review; never investment admission.

It interprets only caller-supplied mandate, original IR capsule and observed
portfolio information. No numeric allocation thresholds, market data, source
authentication, brokerage operations, storage or policy selection.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

RESEARCH_AXES = ("QUALITY", "DURABILITY", "EXPECTED_RETURN", "CONFIDENCE")
PORTFOLIO_CHECKS = ("CONCENTRATION", "CORRELATED_DRIVERS", "ALTERNATIVES", "ACCOUNT_COSTS")
REPORTED = frozenset({"SPECIALIST_REPORTED", "UNKNOWN"})
CAPITAL_SOURCES = frozenset({"NEW_CONTRIBUTION", "EXCEPTIONAL_LIFECYCLE_REVIEW"})


def _str(raw: Any, name: str) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError(f"{name}: nonempty string required")
    return raw.strip()


def _date(raw: Any, name: str) -> str:
    value = _str(raw, name)
    try:
        parsed = date.fromisoformat(value)
    except ValueError as err:
        raise ValueError(f"{name}: YYYY-MM-DD required") from err
    if parsed.isoformat() != value:
        raise ValueError(f"{name}: canonical YYYY-MM-DD required")
    return value


def _pct(raw: Any, name: str) -> Decimal:
    if not isinstance(raw, str):
        raise ValueError(f"{name}: exact string percent required")
    try:
        value = Decimal(raw)
    except InvalidOperation as err:
        raise ValueError(f"{name}: decimal percent required") from err
    if not value.is_finite() or not (0 <= value <= 100):
        raise ValueError(f"{name}: percent outside 0..100")
    return value


def prepare_portfolio_room_review(
    request: Mapping[str, Any],
    ir_capsule: Mapping[str, Any],
    observation: Mapping[str, Any],
    exposures: Mapping[str, Any],
    room_inputs: Mapping[str, Any],
) -> dict[str, Any]:
    """Prepare qualitative PI memo for human decision, never auto-certify ROOM.

    All arguments and the output are PRIVATE. Evidence references are carried,
    not independently fetched/validated. The caller's assessment doesn't gain
    objective verification from this function.
    """
    if not all(isinstance(x, Mapping) for x in
               (request, ir_capsule, observation, exposures, room_inputs)):
        raise ValueError("ROOM_INPUTS_MUST_BE_MAPPINGS")
    aid = _str(request.get("analysis_id"), "request.analysis_id")
    cutoff = _date(request.get("as_of"), "request.as_of")
    strategy = _str(request.get("strategy_id"), "request.strategy_id")
    if not request.get("research_needed") or not request.get("portfolio_needed"):
        raise ValueError("ROOM_REQUIRES_EXPLICIT_IR_AND_PI_MANDATE")
    for label, obj in (("IR", ir_capsule), ("P", observation)):
        if _str(obj.get("analysis_id"), f"{label}.analysis_id") != aid:
            raise ValueError("ROOM_ANALYSIS_ID_MISMATCH")
    exposure_unavailable = exposures.get("status") == "UNAVAILABLE_INCOMPLETE_P_LEDGER"
    if not exposure_unavailable and _str(exposures.get("analysis_id"), "EXPOSURE.analysis_id") != aid:
        raise ValueError("ROOM_ANALYSIS_ID_MISMATCH")
    if _date(ir_capsule.get("research_as_of"), "IR.research_as_of") > cutoff:
        raise ValueError("ROOM_IR_AFTER_ANALYSIS_CUTOFF")
    observed = _date(observation.get("observed_on"), "P.observed_on")
    if observed > cutoff or (not exposure_unavailable and
                            _date(exposures.get("observation_as_of"), "EXPOSURE.observation_as_of") != observed):
        raise ValueError("ROOM_OBSERVATION_DATE_MISMATCH")
    if _date(room_inputs.get("review_as_of"), "review_as_of") != cutoff:
        raise ValueError("ROOM_REVIEW_AS_OF_MISMATCH")
    if _str(room_inputs.get("strategy_id"), "room.strategy_id") != strategy:
        raise ValueError("ROOM_STRATEGY_MISMATCH")
    source = _str(room_inputs.get("capital_source"), "capital_source")
    if source not in CAPITAL_SOURCES:
        raise ValueError("ROOM_CAPITAL_SOURCE_UNSUPPORTED")
    if _str(room_inputs.get("account_scope"), "account_scope") != observation.get("account_scope"):
        raise ValueError("ROOM_ACCOUNT_SCOPE_MISMATCH")
    if not exposure_unavailable and _str(exposures.get("account_scope_private"), "exposure.account_scope") != observation.get("account_scope"):
        raise ValueError("ROOM_EXPOSURE_SCOPE_MISMATCH")
    issuer = _str(room_inputs.get("candidate_economic_issuer_id"), "candidate_economic_issuer_id")
    security = _str(room_inputs.get("candidate_security_id"), "candidate_security_id")
    horizon = room_inputs.get("horizon_years")
    if type(horizon) is not int or horizon < 1 or horizon > 50:
        raise ValueError("ROOM_HORIZON_INVALID")
    account_type = _str(room_inputs.get("account_type"), "account_type")
    if account_type == "UNKNOWN":
        missing = ["ACCOUNT_TYPE_UNKNOWN"]
    else:
        missing = []
    axis_data: dict[str, Any] = {}
    original_facts = {f.get("id"): f for f in ir_capsule.get("facts", [])
                      if isinstance(f, Mapping) and isinstance(f.get("id"), str)}
    fact_ids = set(original_facts)
    axes = room_inputs.get("research_axes")
    if not isinstance(axes, Mapping) or set(axes) != set(RESEARCH_AXES):
        raise ValueError("ROOM_REQUIRES_EXACT_FOUR_RESEARCH_AXES")
    for axis in RESEARCH_AXES:
        item = axes[axis]
        if not isinstance(item, Mapping):
            raise ValueError(f"ROOM_{axis}_MUST_BE_MAPPING")
        status = _str(item.get("status"), f"{axis}.status")
        if status not in REPORTED:
            raise ValueError("ROOM_AXES_CANNOT_DECLARE_INDEPENDENT_CERTIFICATION")
        rationale = _str(item.get("rationale"), f"{axis}.rationale")
        refs = item.get("ir_fact_ids")
        if not isinstance(refs, list) or any(not isinstance(x, str) for x in refs):
            raise ValueError(f"ROOM_{axis}_FACT_REFS_INVALID")
        if set(refs) - fact_ids:
            raise ValueError("ROOM_UNKNOWN_IR_FACT_REFERENCE")
        if status == "UNKNOWN" or not refs:
            missing.append(axis + "_UNSUPPORTED_OR_UNKNOWN")
        if any(original_facts[x].get("status") in {"MISSING", "CONFLICTED"} for x in refs):
            missing.append(axis + "_ORIGINAL_IR_FACT_UNRESOLVED")
        axis_data[axis] = {"status": status, "rationale": rationale, "ir_fact_ids": list(refs)}
    checks = room_inputs.get("portfolio_checks")
    if not isinstance(checks, Mapping) or set(checks) != set(PORTFOLIO_CHECKS):
        raise ValueError("ROOM_REQUIRES_EXACT_FOUR_PORTFOLIO_CHECKS")
    check_data = {}
    for name in PORTFOLIO_CHECKS:
        item = checks[name]
        if not isinstance(item, Mapping):
            raise ValueError(f"ROOM_{name}_MUST_BE_MAPPING")
        status = _str(item.get("status"), f"{name}.status")
        if status not in REPORTED:
            raise ValueError("ROOM_CHECKS_CANNOT_DECLARE_INDEPENDENT_CERTIFICATION")
        finding = _str(item.get("finding"), f"{name}.finding")
        evidence_ref = item.get("source_ref")
        if evidence_ref is not None:
            evidence_ref = _str(evidence_ref, f"{name}.source_ref")
        if status == "UNKNOWN" or evidence_ref is None:
            missing.append(name + "_UNSUPPORTED_OR_UNKNOWN")
        check_data[name] = {"status": status, "finding": finding, "source_ref": evidence_ref}
    known_pct = None
    lower = exposures.get("economic_issuer_pct_private")
    unknown_pct = None
    if observation.get("status") != "SCOPED_WEIGHTS_DERIVED_FROM_CALLER_VISIBLE_DATA":
        missing.append("P_LEDGER_INCOMPLETE")
    if exposures.get("status") not in {"CALLER_REPORTED_SCOPED_EXPOSURES", "PARTIAL_KNOWN_EXPOSURE_LOWER_BOUNDS"}:
        missing.append("EXPOSURES_UNAVAILABLE")
    historical_fund = exposures.get("fund_composition_date_alignment") == "PRIOR_DATED_FUND_SNAPSHOTS"
    if historical_fund:
        # Private annex retains historical issuer arithmetic, but a prior
        # fund snapshot is not a CURRENT issuer exposure lower bound.
        missing.append("HISTORICAL_FUND_COMPOSITION_NOT_CURRENT")
        missing.append("KNOWN_ISSUER_EXPOSURE_UNAVAILABLE")
    elif isinstance(lower, Mapping):
        known_pct = str(_pct(lower.get(issuer, "0"), "known issuer exposure"))
    else:
        missing.append("KNOWN_ISSUER_EXPOSURE_UNAVAILABLE")
    try:
        unknown_pct = str(_pct(exposures.get("unclassified_or_unknown_fund_pct"), "unknown exposure"))
        if Decimal(unknown_pct) > 0:
            missing.append("LOOKTHROUGH_PARTIAL")
    except ValueError:
        missing.append("UNKNOWN_LOOKTHROUGH_UNAVAILABLE")
    recommendation = _str(room_inputs.get("analyst_view"), "analyst_view")
    countercase = _str(room_inputs.get("strongest_countercase"), "strongest_countercase")
    next_check = _str(room_inputs.get("next_verification"), "next_verification")
    if source == "EXCEPTIONAL_LIFECYCLE_REVIEW":
        missing.append("EXCEPTIONAL_ACTION_REQUIRES_SEPARATE_THESIS_AND_COST_REVIEW")
    # Financial input statuses are caller-reported; a complete-looking packet
    # cannot certify a supported allocation or an order.
    review_status = "ROOM_CONDITIONAL" if (
        observation.get("status") == "SCOPED_WEIGHTS_DERIVED_FROM_CALLER_VISIBLE_DATA"
        and known_pct is not None and unknown_pct is not None
        and account_type != "UNKNOWN"
        and all(axis_data[k]["status"] == "SPECIALIST_REPORTED" and axis_data[k]["ir_fact_ids"]
                and not any(original_facts[x].get("status") in {"MISSING", "CONFLICTED"}
                            for x in axis_data[k]["ir_fact_ids"]) for k in RESEARCH_AXES)
    ) else "ROOM_UNAVAILABLE"
    return {
        "status": review_status,
        "analysis_id": aid, "as_of": cutoff,
        "observed_on": observed, "strategy_id": strategy,
        "account_scope_private": observation.get("account_scope"),
        "account_type_private": account_type, "horizon_years": horizon,
        "candidate_security_id": security, "candidate_economic_issuer_id": issuer,
        "known_candidate_issuer_exposure_pct_private": known_pct,
        "unclassified_lookthrough_pct_private": unknown_pct,
        "research_axes_private": deepcopy(axis_data),
        "portfolio_checks_private": deepcopy(check_data),
        "analyst_view_private": recommendation,
        "strongest_countercase_private": countercase,
        "next_verification_private": next_check,
        "missing_or_qualified": sorted(set(missing)),
        "portfolio_room_authority": "QUALITATIVE_SPECIALIST_REPORTED_ONLY",
        "independent_evidence_check": "NOT_PERFORMED",
        "contribution_or_sale_proposal": "NONE_NOT_AUTOMATED",
        "trade_authority": "NONE_CEO_ONLY",
        "public_memory_write": "NONE",
    }
