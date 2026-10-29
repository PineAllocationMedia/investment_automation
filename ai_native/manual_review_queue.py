"""R1 manual work queue, derived only from the existing validated session.

No research, ranking, source authentication, brokerage access, scheduling,
storage or Project invocation. Codes/actions deliberately exclude private values.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from .exceptional_lifecycle import EVENTS, VIEWS

FINAL = frozenset({
    "M7A_COMPONENT_ASSEMBLED_NOT_END_TO_END_ACCEPTANCE",
    "PI_ONLY_CONDITIONAL_REPORT_ASSEMBLED",
    "PUBLIC_REFERENCE_DESCRIPTIVE_REPORT_READY",
})
WAITING = frozenset({
    "AWAITING_MANUAL_IR_CAPSULE",
    "AWAITING_MANUAL_PI_DELTA",
    "AWAITING_MANUAL_PORTFOLIO_SCREENSHOT",
})
ROUTES = frozenset({"CC_DIRECT", "CC_IR_CC", "CC_PI_CC", "CC_IR_PI_CC"})
MAX_ITEMS = 14  # At most one additional dated-snapshot human review step.


LIFECYCLE_STATUSES = frozenset({
    "EVIDENCE_RESOLUTION_NO_ACTION", "HUMAN_THESIS_AND_COST_REVIEW_ONLY",
})
LIFECYCLE_LIMITS = frozenset({
    "PRIVATE_SCOPED_PORTFOLIO_INCOMPLETE", "ORIGINAL_IR_FACTS_UNRESOLVED",
    "NO_CURRENT_EVIDENCE_REFERENCES", "CURRENT_EVIDENCE_NOT_STRUCTURALLY_LINKED",
    "CURRENT_EVIDENCE_UNRESOLVED", "FEES_STATUS_UNKNOWN",
    "FX_STATUS_UNKNOWN", "TAX_STATUS_UNKNOWN",
    "NO_STRUCTURAL_SELL_THESIS_FROM_EVENT",
})


def _lifecycle_review_action(session: Mapping[str, Any],
                             integrated: Mapping[str, Any],
                             review: Mapping[str, Any]) -> tuple[str, str, str]:
    """At most one deterministic human task. Never surface private values."""
    memory = integrated.get("memory_proposal_nonprivate")
    if (not isinstance(memory, Mapping)
            or integrated.get("exceptional_lifecycle_review_private") != review
            or review.get("status") not in LIFECYCLE_STATUSES
            or review.get("analysis_id") != memory.get("analysis_id")
            or review.get("analysis_as_of") != memory.get("as_of")
            or review.get("strategy_id") not in {"high-cagr", "High-CAGR", "HIGH_CAGR"}
            or review.get("source_authentication") != "NOT_PERFORMED"
            or review.get("account_and_cost_authentication") != "NOT_PERFORMED"
            or review.get("portfolio_room_admission") != "NONE"
            or review.get("allocation_or_sale_proposal") != "NONE"
            or review.get("trade_authority") != "NONE_CEO_ONLY"
            or review.get("public_memory_write") != "NONE"
            or review.get("thesis_event") not in EVENTS
            or review.get("analyst_reported_view") not in VIEWS):
        raise ValueError("REVIEW_QUEUE_LIFECYCLE_AUTHORITY_INVALID")
    obs = session.get("portfolio_observation_private")
    if (not isinstance(obs, Mapping)
            or obs.get("analysis_id") != review["analysis_id"]
            or obs.get("analysis_as_of") != review["analysis_as_of"]
            or obs.get("observed_on") != review.get("portfolio_observed_on")
            or obs.get("account_scope") != review.get("account_scope_private")
            or obs.get("private_scope") is not True):
        raise ValueError("REVIEW_QUEUE_LIFECYCLE_OBSERVATION_MISMATCH")
    refs = review.get("original_ir_fact_ids_private")
    current = review.get("current_evidence_refs_private")
    limits = review.get("missing_or_qualified")
    if (not isinstance(refs, list) or not refs or len(refs) > 24
            or not isinstance(current, list) or len(current) > 24
            or any(not isinstance(x, str) or not x or len(x) > 90 for x in refs + current)
            or len(set(refs)) != len(refs) or len(set(current)) != len(current)
            or not isinstance(limits, list) or len(limits) > len(LIFECYCLE_LIMITS)
            or any(not isinstance(x, str) or x not in LIFECYCLE_LIMITS for x in limits)
            or len(set(limits)) != len(limits)
            or (review["status"] == "HUMAN_THESIS_AND_COST_REVIEW_ONLY") != (not limits)):
        raise ValueError("REVIEW_QUEUE_LIFECYCLE_LIMITATIONS_INVALID")
    if (review["thesis_event"] in {"VOLATILITY_ONLY", "TRANSIENT_INFORMATION_UNCERTAINTY"}
            and review["analyst_reported_view"] in {"REVIEW_TRIM", "REVIEW_EXIT"}):
        raise ValueError("REVIEW_QUEUE_LIFECYCLE_PRICE_ONLY_SELL_INVALID")
    missing = set(limits)
    annex = review.get("current_evidence_annex_private")
    if annex is None:
        if current and "CURRENT_EVIDENCE_NOT_STRUCTURALLY_LINKED" not in missing:
            raise ValueError("REVIEW_QUEUE_LIFECYCLE_CURRENT_EVIDENCE_UNSUPPORTED")
    else:
        if (not isinstance(annex, Mapping)
                or annex.get("status") != "PRIVATE_SOURCE_ANNEX_PREPARED_NOT_CERTIFIED"
                or annex.get("analysis_id") != review.get("analysis_id")
                or annex.get("analysis_as_of") != review.get("analysis_as_of")
                or annex.get("source_authentication") != "NOT_PERFORMED_BY_CODE"
                or annex.get("source_rights_authority") != "NOT_GRANTED_BY_CODE"
                or annex.get("trading_authority") != "NONE"
                or not isinstance(annex.get("observations_private"), list)):
            raise ValueError("REVIEW_QUEUE_LIFECYCLE_CURRENT_EVIDENCE_INVALID")
        observations = annex["observations_private"]
        if (len(observations) != len(current)
                or any(not isinstance(item, Mapping) for item in observations)
                or {item.get("observation_id") for item in observations} != set(current)
                or any(item.get("fact_id") not in refs for item in observations)):
            raise ValueError("REVIEW_QUEUE_LIFECYCLE_CURRENT_EVIDENCE_LINK_MISMATCH")
        unresolved = any(item.get("claim_use_status") != "CALLER_REPORTED_ONLY"
                         for item in observations)
        if (("CURRENT_EVIDENCE_UNRESOLVED" in missing) != unresolved
                or "CURRENT_EVIDENCE_NOT_STRUCTURALLY_LINKED" in missing
                or "NO_CURRENT_EVIDENCE_REFERENCES" in missing):
            raise ValueError("REVIEW_QUEUE_LIFECYCLE_CURRENT_EVIDENCE_STATUS_MISMATCH")
    if "ORIGINAL_IR_FACTS_UNRESOLVED" in missing:
        return ("RESOLVE_LIFECYCLE_IR_FACTS", "EVIDENCE_RESOLUTION",
                "Check the original IR-linked thesis facts and contradictions before interpreting any exceptional position view.")
    if missing & {"NO_CURRENT_EVIDENCE_REFERENCES",
                  "CURRENT_EVIDENCE_NOT_STRUCTURALLY_LINKED",
                  "CURRENT_EVIDENCE_UNRESOLVED"}:
        return ("FIND_LIFECYCLE_CURRENT_EVIDENCE", "EVIDENCE_RESOLUTION",
                "Link current thesis evidence to dated source observations, resolve source rights and conflicts; no portfolio trade can follow from unverified references.")
    if "PRIVATE_SCOPED_PORTFOLIO_INCOMPLETE" in missing:
        return ("RECONCILE_LIFECYCLE_HOLDINGS_SCOPE", "EVIDENCE_RESOLUTION",
                "Recheck the dated private position, account coverage and hidden holdings before assessing concentration or lifecycle choices.")
    if missing & {"FEES_STATUS_UNKNOWN", "FX_STATUS_UNKNOWN", "TAX_STATUS_UNKNOWN"}:
        return ("VERIFY_LIFECYCLE_TRANSACTION_COSTS", "EVIDENCE_RESOLUTION",
                "Verify relevant account fees, FX and tax-lot effects before discussing any exceptional trim or exit; do not trade.")
    if "NO_STRUCTURAL_SELL_THESIS_FROM_EVENT" in missing:
        return ("REVIEW_LIFECYCLE_NONSTRUCTURAL_EVENT", "HUMAN_VERIFICATION",
                "Volatility or temporary uncertainty alone does not establish a High-CAGR sell trigger; check the original thesis without recommending a sale.")
    return ("REVIEW_LIFECYCLE_THESIS_AND_COSTS", "HUMAN_VERIFICATION",
            "Independently review original and current thesis evidence, portfolio identity and account costs; specialist view is not trading approval.")


def _portfolio_exposure_review_action(
    exposure: Mapping[str, Any] | None, observation: Mapping[str, Any],
) -> tuple[str, str, str]:
    """Choose ONE non-sensitive human task from computed M3 exposure limits.

    Does not trust specialist prose or reclassify funds. M3's actual private
    computation must already exist, and only its bounded status flags are read.
    """
    original = ("CHECK_PORTFOLIO_ORIGINAL", "HUMAN_VERIFICATION",
                "Check dated source image/export, holdings and account scope before "
                "trusting caller-reported scoped portfolio weights.")
    if exposure is None:
        return original
    if not isinstance(exposure, Mapping):
        raise ValueError("REVIEW_QUEUE_EXPOSURE_INVALID")
    status = exposure.get("status")
    if status not in {
        "UNAVAILABLE_INCOMPLETE_P_LEDGER",
        "PARTIAL_KNOWN_EXPOSURE_LOWER_BOUNDS",
        "CALLER_REPORTED_SCOPED_EXPOSURES",
    }:
        raise ValueError("REVIEW_QUEUE_EXPOSURE_STATUS_INVALID")
    if status == "UNAVAILABLE_INCOMPLETE_P_LEDGER":
        # Structural loss of the P-ledger cannot silently be presented as a
        # valid exposure breakdown, even by a forged output packet.
        raise ValueError("REVIEW_QUEUE_EXPOSURE_LEDGER_MISMATCH")
    if (observation.get("private_scope") is not True
            or exposure.get("analysis_id") != observation.get("analysis_id")
            or exposure.get("observation_as_of") != observation.get("observed_on")
            or exposure.get("account_scope_private") != observation.get("account_scope")
            or exposure.get("currency") != observation.get("currency")
            or exposure.get("source_authentication") !=
                "CALLER_REPORTED_NOT_INDEPENDENTLY_VERIFIED"
            or exposure.get("coverage_scope") !=
                "EXPLICIT_LEDGER_SCOPE_ONLY_NOT_HOUSEHOLD_TOTAL"
            or exposure.get("portfolio_room_status") != "ROOM_UNAVAILABLE"
            or exposure.get("trading_authority") != "NONE"
            or exposure.get("writes") != "NONE"):
        raise ValueError("REVIEW_QUEUE_EXPOSURE_AUTHORITY_OR_SCOPE_MISMATCH")
    def pct(name: str) -> Decimal:
        raw = exposure.get(name)
        if not isinstance(raw, str) or len(raw) > 6:
            raise ValueError("REVIEW_QUEUE_EXPOSURE_PERCENT_INVALID")
        try:
            amount = Decimal(raw)
        except InvalidOperation as exc:
            raise ValueError("REVIEW_QUEUE_EXPOSURE_PERCENT_INVALID") from exc
        if (not amount.is_finite() or amount < 0 or amount > 100
                or amount != amount.quantize(Decimal("0.01"))):
            raise ValueError("REVIEW_QUEUE_EXPOSURE_PERCENT_INVALID")
        return amount
    known = pct("known_exposure_pct")
    unknown = pct("unclassified_or_unknown_fund_pct")
    cash = pct("cash_pct")
    if (abs(known + unknown + cash - Decimal("100")) > Decimal("0.02")
            or (unknown > 0) !=
               (status == "PARTIAL_KNOWN_EXPOSURE_LOWER_BOUNDS")):
        raise ValueError("REVIEW_QUEUE_EXPOSURE_PERCENT_OR_STATUS_MISMATCH")
    dated = exposure.get("fund_composition_date_alignment")
    if dated == "PRIOR_DATED_FUND_SNAPSHOTS":
        if (not unknown or exposure.get("economic_issuer_rank_coverage_reported_complete") is not False
                or not isinstance(exposure.get("historical_fund_scenario_private"), Mapping)
                or not isinstance(exposure.get("historical_fund_p_ids_private"), list)
                or not exposure["historical_fund_p_ids_private"]):
            raise ValueError("REVIEW_QUEUE_EXPOSURE_HISTORY_INVALID")
        return ("REFRESH_DATED_FUND_LOOKTHROUGH", "EVIDENCE_RESOLUTION",
                "Obtain rights-permitted ETF/fund constituent evidence dated to the "
                "observed portfolio scope; older compositions are illustrative, "
                "not current issuer/sector exposure. Recheck source and account coverage.")
    if dated != "NO_PRIOR_DATED_FUND_SNAPSHOTS_REPORTED" or (
            exposure.get("historical_fund_scenario_private") is not None):
        raise ValueError("REVIEW_QUEUE_EXPOSURE_FUND_DATE_INVALID")
    if unknown > 0:
        return ("RESOLVE_CURRENT_EXPOSURE_COVERAGE", "EVIDENCE_RESOLUTION",
                "Resolve missing, partial or rights-uncertain direct/fund "
                "classifications and fund constituents using dated permitted "
                "sources; confirm the actual account and cash scope.")
    return original


def _snapshot_review_action(
    session: Mapping[str, Any], comparison: Mapping[str, Any],
) -> tuple[str, str, str]:
    """One source-aware human task from existing PRIVATE dated snapshot results.

    Never transfer accounts, security IDs, position amounts, raw UI weights,
    dates, source refs or user-controlled text into the operator review queue.
    """
    if not isinstance(comparison, Mapping):
        raise ValueError("REVIEW_QUEUE_SNAPSHOT_PACKET_INVALID")
    if (session.get("route") not in {"CC_PI_CC", "CC_IR_PI_CC"}
            or session.get("status") not in FINAL):
        raise ValueError("REVIEW_QUEUE_SNAPSHOT_ROUTE_INVALID")
    observation = session.get("portfolio_observation_private")
    if (not isinstance(observation, Mapping)
            or observation.get("private_scope") is not True
            or comparison.get("analysis_id") != observation.get("analysis_id")
            or comparison.get("analysis_as_of") != observation.get("analysis_as_of")
            or comparison.get("current_observed_on") != observation.get("observed_on")
            or comparison.get("privacy") != "PRIVATE_ONLY"
            or comparison.get("source_authentication") != "NOT_PERFORMED"
            or comparison.get("performance_or_transaction_inference") != "NONE"
            or comparison.get("storage") != "NONE"
            or comparison.get("trading_authority") != "NONE"):
        raise ValueError("REVIEW_QUEUE_SNAPSHOT_AUTHORITY_OR_OBSERVATION_MISMATCH")
    integrated = session.get("integrated_private")
    if session.get("route") == "CC_IR_PI_CC":
        if (not isinstance(integrated, Mapping)
                or integrated.get("portfolio_snapshot_comparison_private") != comparison):
            raise ValueError("REVIEW_QUEUE_SNAPSHOT_INTEGRATED_PARITY_INVALID")
    elif integrated is not None:
        raise ValueError("REVIEW_QUEUE_SNAPSHOT_PI_ONLY_INTEGRATED_INVALID")
    prior_id = comparison.get("prior_analysis_id")
    if (not isinstance(prior_id, str) or not prior_id.strip()
            or prior_id == comparison.get("analysis_id")):
        raise ValueError("REVIEW_QUEUE_SNAPSHOT_PRIOR_ID_INVALID")
    try:
        before = date.fromisoformat(comparison["prior_observed_on"])
        after = date.fromisoformat(comparison["current_observed_on"])
        cutoff = date.fromisoformat(comparison["analysis_as_of"])
        if (before.isoformat() != comparison["prior_observed_on"]
                or after.isoformat() != comparison["current_observed_on"]
                or cutoff.isoformat() != comparison["analysis_as_of"]
                or not before < after <= cutoff):
            raise ValueError
    except (TypeError, KeyError, ValueError) as exc:
        raise ValueError("REVIEW_QUEUE_SNAPSHOT_DATES_INVALID") from exc

    status = comparison.get("status")
    reasons = comparison.get("reason_codes")
    rows = comparison.get("rows_private")
    if status == "UNAVAILABLE_INCOMPLETE_SNAPSHOT_SCOPE":
        if (not isinstance(reasons, list) or not reasons
                or len(reasons) != len(set(reasons))
                or any(code not in {"PRIOR_SCOPE_INCOMPLETE", "CURRENT_SCOPE_INCOMPLETE"}
                       for code in reasons)
                or rows is not None
                or any(comparison.get(field) is not None for field in (
                    "matched_instrument_count", "newly_visible_count",
                    "no_longer_visible_count",
                    "largest_absolute_security_weight_shift_pp",
                    "cash_weight_change_pp"))):
            raise ValueError("REVIEW_QUEUE_SNAPSHOT_UNAVAILABLE_SCHEMA_INVALID")
        return ("RECONCILE_DATED_SNAPSHOT_INPUTS", "EVIDENCE_RESOLUTION",
                "Reconcile BOTH original dated private holdings views, scope, "
                "security identities, visible cash, currency and source access. "
                "Do not infer missing values or historical transactions.")
    if (not isinstance(rows, list) or not 1 <= len(rows) <= 10000
            or type(comparison.get("matched_instrument_count")) is not int
            or comparison["matched_instrument_count"] < 0
            or type(comparison.get("newly_visible_count")) is not int
            or type(comparison.get("no_longer_visible_count")) is not int
            or comparison["newly_visible_count"] < 0
            or comparison["no_longer_visible_count"] < 0
            or sum(comparison[k] for k in (
                "matched_instrument_count", "newly_visible_count",
                "no_longer_visible_count")) != len(rows)):
        raise ValueError("REVIEW_QUEUE_SNAPSHOT_COMPARISON_SCHEMA_INVALID")
    if status == "OBSERVED_UI_WEIGHT_CHANGE_ONLY_NO_MONETARY_DENOMINATOR":
        if (reasons != ["MONETARY_DENOMINATOR_NOT_VERIFIED"]
                or comparison.get("cash_weight_change_pp") is not None
                or comparison["newly_visible_count"] != 0
                or comparison["no_longer_visible_count"] != 0
                or comparison["matched_instrument_count"] != len(rows)):
            raise ValueError("REVIEW_QUEUE_SNAPSHOT_UI_ONLY_AUTHORITY_INVALID")
        return ("VERIFY_SOURCE_DISPLAYED_HISTORY", "HUMAN_VERIFICATION",
                "Inspect both dated original private Blossom/screenshots: "
                "same account filter and visibly identical securities; check "
                "raw UI percentages without normalization. Cash, money basis, "
                "portfolio returns and transactions remain UNKNOWN.")
    if status == "DESCRIPTIVE_SCOPED_WEIGHT_CHANGE_NOT_RETURN":
        if (reasons != [] or comparison.get("cash_weight_change_pp") is None
                or observation.get("known_scope_weights_pct") is None):
            raise ValueError("REVIEW_QUEUE_SNAPSHOT_MONETARY_AUTHORITY_INVALID")
        return ("VERIFY_MONETARY_SNAPSHOT_HISTORY", "HUMAN_VERIFICATION",
                "Verify both original dated private holdings, same account and "
                "currency basis, cash and corporate actions. Scoped weight "
                "differences are not returns, capital flows, purchases or sales.")
    raise ValueError("REVIEW_QUEUE_SNAPSHOT_STATUS_INVALID")


def prepare_manual_review_queue(session: Mapping[str, Any]) -> dict[str, Any]:
    """Private human next-action queue; one code per distinct issue.

    Never copies source URLs, holdings, account names, amounts, fact IDs,
    security IDs, private report narratives, or arbitrary user-provided text.
    Not a readiness gate or evidence-upgrade mechanism.
    """
    if not isinstance(session, Mapping):
        raise ValueError("REVIEW_QUEUE_SESSION_REQUIRED")
    status = session.get("status")
    route = session.get("route")
    if route not in ROUTES or status not in FINAL | WAITING | {"CC_DIRECT_NO_SPECIALIST_REPORT_REQUIRED"}:
        raise ValueError("REVIEW_QUEUE_UNSUPPORTED_SESSION_STATUS")
    if (session.get("method_load_verification") != "NOT_PERFORMED"
            or session.get("source_authentication") != "NOT_PERFORMED"
            or session.get("project_invocation") != "NONE"
            or session.get("storage") != "NONE"
            or session.get("readiness") != "NOT_EVALUATED"):
        raise ValueError("REVIEW_QUEUE_AUTHORITY_MISMATCH")
    snapshot = session.get("portfolio_snapshot_comparison_private")
    if snapshot is not None and (
            status not in {"M7A_COMPONENT_ASSEMBLED_NOT_END_TO_END_ACCEPTANCE",
                           "PI_ONLY_CONDITIONAL_REPORT_ASSEMBLED"}
            or route not in {"CC_IR_PI_CC", "CC_PI_CC"}):
        raise ValueError("REVIEW_QUEUE_SNAPSHOT_ROUTE_INVALID")
    lifecycle = session.get("exceptional_lifecycle_review_private")
    if lifecycle is not None and (
            status != "M7A_COMPONENT_ASSEMBLED_NOT_END_TO_END_ACCEPTANCE"
            or route != "CC_IR_PI_CC" or not isinstance(lifecycle, Mapping)):
        raise ValueError("REVIEW_QUEUE_LIFECYCLE_ROUTE_INVALID")
    items: list[dict[str, str]] = []

    def add(code: str, stage: str, instruction: str) -> None:
        if not any(x["code"] == code for x in items):
            items.append({"code": code, "stage": stage, "human_action": instruction})

    if status == "CC_DIRECT_NO_SPECIALIST_REPORT_REQUIRED":
        if route != "CC_DIRECT":
            raise ValueError("REVIEW_QUEUE_DIRECT_ROUTE_MISMATCH")
        add("CC_DIRECT_REVIEW", "OPERATOR_REVIEW",
            "No specialist path was requested. Review whether the CEO's original mandate is fulfilled.")
    elif status == "PUBLIC_REFERENCE_DESCRIPTIVE_REPORT_READY":
        if route != "CC_DIRECT":
            raise ValueError("REVIEW_QUEUE_PUBLIC_REFERENCE_ROUTE_MISMATCH")
        add("VERIFY_REFERENCE_SCOPE", "HUMAN_VERIFICATION",
            "Check the original visible reference portfolio and actual account filter, publication/access rights, data date and currency before research conclusions.")
        add("REVIEW_REFERENCE_ONLY", "OPERATOR_REVIEW",
            "Use public portfolio rows only as a descriptive research reference; never treat them as the CEO's personal holdings, Portfolio Room or trade authority.")
    else:
        add("CONFIRM_METHOD_CONTEXT", "OPERATOR_REVIEW",
            "Confirm the relevant Project instructions, method version, mandate and strategy were actually loaded; not validated by the local runner.")
        if status == "AWAITING_MANUAL_IR_CAPSULE":
            if route not in {"CC_IR_CC", "CC_IR_PI_CC"}:
                raise ValueError("REVIEW_QUEUE_IR_ROUTE_MISMATCH")
            add("TRANSFER_IR_CAPSULE", "HANDOFF_REQUIRED",
                "Run the authorized IR request and paste the original unchanged IR_CAPSULE into the next explicit session.")
            if session.get("public_reference_private") is not None:
                add("VERIFY_REFERENCE_SCOPE", "HUMAN_VERIFICATION",
                    "Check the source-profile holdings scope and synchronization date; observed lines are research reference only.")
        elif status == "AWAITING_MANUAL_PI_DELTA":
            if route not in {"CC_IR_PI_CC", "CC_PI_CC"}:
                raise ValueError("REVIEW_QUEUE_PI_ROUTE_MISMATCH")
            add("TRANSFER_PI_DELTA", "HANDOFF_REQUIRED",
                "Obtain the dated authorized PI_DELTA; preserve an unchanged forwarded IR_CAPSULE when IR was requested.")
        elif status == "AWAITING_MANUAL_PORTFOLIO_SCREENSHOT":
            if route not in {"CC_IR_PI_CC", "CC_PI_CC"}:
                raise ValueError("REVIEW_QUEUE_SCREENSHOT_ROUTE_MISMATCH")
            capture = session.get("work_blossom_capture_private")
            if (not isinstance(capture, Mapping)
                    or capture.get("status") != "VISUAL_SOURCE_UNAVAILABLE_USE_SCREENSHOT_FALLBACK"
                    or capture.get("project_invocation") != "NONE"
                    or capture.get("transfer") != "MANUAL_ONLY"):
                raise ValueError("REVIEW_QUEUE_SCREENSHOT_SOURCE_INVALID")
            add("CAPTURE_AUTHORIZED_PORTFOLIO_SCREENSHOT", "HANDOFF_REQUIRED",
                "The private visual portfolio source was unavailable. Manually capture an authorized dated private screenshot or supply a private user transcript; return a new explicit PI packet.")
        else:
            if status == "M7A_COMPONENT_ASSEMBLED_NOT_END_TO_END_ACCEPTANCE":
                if route not in {"CC_IR_CC", "CC_IR_PI_CC"}:
                    raise ValueError("REVIEW_QUEUE_IR_COMPLETE_ROUTE_MISMATCH")
                integrated = session.get("integrated_private")
                if not isinstance(integrated, Mapping) or integrated.get("status") != "ASSEMBLED_COMPONENT_ONLY_NOT_END_TO_END_ACCEPTANCE":
                    raise ValueError("REVIEW_QUEUE_INTEGRATED_PACKET_REQUIRED")
                if integrated.get("source_evidence_annex_private") is None:
                    add("SOURCE_ANNEX_NOT_PRESENT", "EVIDENCE_RESOLUTION",
                        "Supply a dated, rights-scoped source annex with original IR fact links where decision-grade research is needed.")
                else:
                    add("VERIFY_ORIGINAL_SOURCES", "HUMAN_VERIFICATION",
                        "Check source provenance, dates, rights, accounting definitions and conflicting evidence against originals.")
                fact_alignment = integrated.get("fact_source_alignment_private")
                if fact_alignment is not None:
                    if (not isinstance(fact_alignment, Mapping)
                            or type(fact_alignment.get("facts_needing_review")) is not int
                            or fact_alignment["facts_needing_review"] < 0
                            or fact_alignment.get("status") != "PRIVATE_FACT_SOURCE_ALIGNMENT_NOT_CERTIFIED"):
                        raise ValueError("REVIEW_QUEUE_FACT_ALIGNMENT_INVALID")
                    if fact_alignment["facts_needing_review"]:
                        add("RECONCILE_IR_FACTS", "EVIDENCE_RESOLUTION",
                            "Resolve the IR facts with unlinked, incomplete, conflicted or unsupported source observations.")
                quote = integrated.get("valuation_quote_trace_private")
                if quote is not None:
                    if (not isinstance(quote, Mapping)
                            or quote.get("status") != "PRIVATE_QUOTE_SOURCE_TRACE_NOT_CERTIFIED"
                            or quote.get("source_authentication") != "NOT_PERFORMED"
                            or quote.get("original_market_price_verification") != "NOT_ESTABLISHED"
                            or quote.get("market_price_or_fx_authority") != "NONE"
                            or quote.get("review_stage") not in {"EVIDENCE_RESOLUTION", "HUMAN_QUOTE_REVIEW_ONLY"}):
                        raise ValueError("REVIEW_QUEUE_QUOTE_TRACE_INVALID")
                    if quote["review_stage"] == "EVIDENCE_RESOLUTION":
                        add("RESOLVE_VALUATION_QUOTE", "EVIDENCE_RESOLUTION",
                            "Resolve the supplied security, date, quote, native currency and source link before relying on the conditional scenario figures.")
                    else:
                        add("CHECK_ORIGINAL_QUOTE", "HUMAN_VERIFICATION",
                            "Independently inspect the original dated quotation, share class, venue, adjustments and source rights; the structural match was not certified.")
                if integrated.get("valuation_scenarios_private") is not None:
                    add("VALIDATE_VALUATION_ASSUMPTIONS", "HUMAN_VERIFICATION",
                        "Review BEAR/BASE/BULL terminal inputs, horizon, distributions and method assumptions; these are not probability-weighted Expected Return.")
                weighted = integrated.get("weighted_cashflow_model_private")
                if weighted is not None:
                    if (not isinstance(weighted, Mapping)
                            or weighted.get("status") not in {
                                "CONDITIONAL_CASHFLOW_MODEL_NOT_CERTIFIED",
                                "UNAVAILABLE_NEEDS_EVIDENCE_OR_COMPATIBLE_ASSUMPTIONS"}
                            or weighted.get("model_expected_return_authority") != "NOT_CERTIFIED"
                            or weighted.get("probability_calibration") != "NOT_PERFORMED"
                            or weighted.get("trading_authority") != "NONE"):
                        raise ValueError("REVIEW_QUEUE_WEIGHTED_MODEL_AUTHORITY_INVALID")
                    add("CHECK_SCENARIO_PROBABILITIES", "HUMAN_VERIFICATION",
                        "Review rationale, calibration and stress sensitivity of supplied BEAR/BASE/BULL probabilities; the modeled weighted result is not a certified Expected Return.")
                    if weighted.get("measure") == "UNAVAILABLE":
                        add("RESOLVE_WEIGHTED_CASHFLOW_INPUTS", "EVIDENCE_RESOLUTION",
                            "Resolve quote evidence, security/currency basis or mixed distribution knowledge before relying on weighted cash-flow arithmetic.")
                if integrated.get("candidate_comparison_private") is not None:
                    add("CHECK_COMPARISON_BASES", "HUMAN_VERIFICATION",
                        "Confirm security, FX, cost, period and measure comparability before interpreting arithmetic spreads; no investability ranking.")
                if integrated.get("historical_research_comparison_private") is not None:
                    add("CHECK_RESEARCH_CHANGES", "HUMAN_VERIFICATION",
                        "Verify linked past/current evidence and distinguish genuine thesis change from changed methods or sources.")
                if lifecycle is not None:
                    code, stage, action = _lifecycle_review_action(session, integrated, lifecycle)
                    add(code, stage, action)
            elif status == "PI_ONLY_CONDITIONAL_REPORT_ASSEMBLED":
                if route != "CC_PI_CC":
                    raise ValueError("REVIEW_QUEUE_PI_COMPLETE_ROUTE_MISMATCH")
            if route in {"CC_IR_PI_CC", "CC_PI_CC"}:
                observation = session.get("portfolio_observation_private")
                if observation is None:
                    add("VERIFY_DATED_PORTFOLIO", "EVIDENCE_RESOLUTION",
                        "Collect and authenticate dated authorized Blossom/screenshot holdings; do not infer hidden accounts, weights or cash.")
                else:
                    if not isinstance(observation, Mapping):
                        raise ValueError("REVIEW_QUEUE_PORTFOLIO_OBSERVATION_INVALID")
                    if observation.get("known_scope_weights_pct") is None:
                        add("RECONCILE_PORTFOLIO_SCOPE", "EVIDENCE_RESOLUTION",
                            "Resolve missing positions, cash, currencies and account scope before using portfolio weights or exposure claims.")
                    else:
                        code, stage, action = _portfolio_exposure_review_action(
                            session.get("portfolio_exposures_private"), observation)
                        add(code, stage, action)
                if snapshot is not None:
                    code, stage, action = _snapshot_review_action(session, snapshot)
                    add(code, stage, action)
                funded_from_ir = (isinstance(session.get("integrated_private"), Mapping)
                                  and session["integrated_private"].get("gross_contribution_private") is not None)
                funded_from_pi = session.get("gross_contribution_private") is not None
                if funded_from_ir or funded_from_pi:
                    add("RECHECK_ACCOUNT_COSTS", "HUMAN_VERIFICATION",
                        "Confirm account, commission, FX, tax and available funding before interpreting percentages of new contributions; never execute orders.")
            add("REVIEW_CONDITIONAL_REPORT", "OPERATOR_REVIEW",
                "Read the private conditional report and unresolved evidence; no ready gate, investment permission, automatic scheduling or trade is granted.")
    if len(items) > MAX_ITEMS:
        raise ValueError("REVIEW_QUEUE_TOO_MANY_ITEMS")
    return {
        "status": "MANUAL_REVIEW_QUEUE_NOT_ACCEPTANCE",
        "session_status": status,
        "route": route,
        "items": items,
        "item_count": len(items),
        "readiness": "NOT_EVALUATED",
        "source_authentication": "NOT_PERFORMED",
        "project_invocation": "NONE",
        "storage": "NONE",
        "trading_authority": "NONE",
    }
