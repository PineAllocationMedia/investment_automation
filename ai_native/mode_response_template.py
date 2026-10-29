"""Inert, fill-in response templates for manual R1 six-mode IR/PI transfers.

These are deliberately invalid as delivered specialist results: the actual
research/portfolio observation date is unknown and must be supplied by the
specialist. No facts, P_IDs, method-load proof or policy can be inferred.
"""
from __future__ import annotations

from typing import Any

from .strategy_research_brief import prepare_strategy_research_brief


def prepare_mode_response_template(
    *, analysis_id: str, strategy_id: str, specialist: str,
) -> dict[str, Any]:
    """Build a private draft matching the optional existing report contract.

    A draft is not an IR_CAPSULE, PI_DELTA or validated response. `None` is a
    deliberate non-date: copying it unchanged into a real specialist result
    must fail the later canonical-date checks, never backdate an observation.
    """
    if not isinstance(analysis_id, str) or not analysis_id.strip():
        raise ValueError("MODE_RESPONSE_TEMPLATE_ANALYSIS_ID_REQUIRED")
    if specialist not in {"IR", "PI"}:
        raise ValueError("MODE_RESPONSE_TEMPLATE_SPECIALIST_INVALID")
    brief = prepare_strategy_research_brief(strategy_id)
    ir = specialist == "IR"
    questions = brief["ir_research_questions" if ir else "pi_portfolio_questions"]
    date_field = "research_as_of" if ir else "portfolio_as_of"
    link_field = "ir_fact_ids" if ir else "p_ids"
    target = "IR_CAPSULE.MODE_RESEARCH_RESPONSES" if ir else "PI_DELTA.MODE_PORTFOLIO_RESPONSES"
    return {
        "status": "PRIVATE_UNFILLED_TEMPLATE_NOT_SPECIALIST_RESULT",
        "target_field": target,
        "template_private": {
            "analysis_id": analysis_id,
            date_field: None,
            "strategy_id": strategy_id,
            "answers": [
                {"question_index": i, "status": "UNKNOWN", link_field: []}
                for i in range(1, len(questions) + 1)
            ],
        },
        "instructions": (
            "Fill the real specialist date and use only original IR fact IDs"
            if ir else
            "Fill the real dated portfolio observation and use only actual private P_LEDGER IDs"
        ) + "; keep UNKNOWN and [] when unsupported; never invent evidence, "
            "load a method, grant policy authority or trade. Remove the outer "
            "template wrapper and return only the completed nested optional "
            "field inside the original specialist response.",
        "method_load": "NOT_VERIFIED",
        "policy_authorization_by_template": "NONE",
        "source_authentication": "NOT_PERFORMED",
        "storage": "NONE",
    }
