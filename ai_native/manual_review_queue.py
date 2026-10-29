"""R1 manual work queue, derived only from the existing validated session.

No research, ranking, source authentication, brokerage access, scheduling,
storage or Project invocation. Codes/actions deliberately exclude private values.
"""
from __future__ import annotations

from typing import Any, Mapping

FINAL = frozenset({
    "M7A_COMPONENT_ASSEMBLED_NOT_END_TO_END_ACCEPTANCE",
    "PI_ONLY_CONDITIONAL_REPORT_ASSEMBLED",
})
WAITING = frozenset({
    "AWAITING_MANUAL_IR_CAPSULE",
    "AWAITING_MANUAL_PI_DELTA",
})
ROUTES = frozenset({"CC_DIRECT", "CC_IR_CC", "CC_PI_CC", "CC_IR_PI_CC"})
MAX_ITEMS = 12


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
    items: list[dict[str, str]] = []

    def add(code: str, stage: str, instruction: str) -> None:
        if not any(x["code"] == code for x in items):
            items.append({"code": code, "stage": stage, "human_action": instruction})

    if status == "CC_DIRECT_NO_SPECIALIST_REPORT_REQUIRED":
        if route != "CC_DIRECT":
            raise ValueError("REVIEW_QUEUE_DIRECT_ROUTE_MISMATCH")
        add("CC_DIRECT_REVIEW", "OPERATOR_REVIEW",
            "No specialist path was requested. Review whether the CEO's original mandate is fulfilled.")
    else:
        add("CONFIRM_METHOD_CONTEXT", "OPERATOR_REVIEW",
            "Confirm the relevant Project instructions, method version, mandate and strategy were actually loaded; not validated by the local runner.")
        if status == "AWAITING_MANUAL_IR_CAPSULE":
            if route not in {"CC_IR_CC", "CC_IR_PI_CC"}:
                raise ValueError("REVIEW_QUEUE_IR_ROUTE_MISMATCH")
            add("TRANSFER_IR_CAPSULE", "HANDOFF_REQUIRED",
                "Run the authorized IR request and paste the original unchanged IR_CAPSULE into the next explicit session.")
        elif status == "AWAITING_MANUAL_PI_DELTA":
            if route not in {"CC_IR_PI_CC", "CC_PI_CC"}:
                raise ValueError("REVIEW_QUEUE_PI_ROUTE_MISMATCH")
            add("TRANSFER_PI_DELTA", "HANDOFF_REQUIRED",
                "Obtain the dated authorized PI_DELTA; preserve an unchanged forwarded IR_CAPSULE when IR was requested.")
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
                        add("CHECK_PORTFOLIO_ORIGINAL", "HUMAN_VERIFICATION",
                            "Check dated source image/export, holdings and account scope before trusting caller-reported portfolio weights.")
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
