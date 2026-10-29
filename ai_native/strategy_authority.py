"""Non-authorizing R1 strategy-policy gate shared by CC handoffs and reports.

Six selected modes are design intent, not six CEO-approved financial policies.
This module never evaluates instruments, infers weights, verifies method loading,
or promotes existing V2 policies into a new R1 authority.
"""
from __future__ import annotations

R1_MODES = (
    "high-cagr",
    "balanced",
    "family-office",
    "rational-aggressive",
    "intelligent-dividend-harvester",
    "modern-adaptive-browne",
)
OBJECTIVES_NOT_MODES = frozenset({"capital-preservation", "income"})


def assess_r1_mode(strategy_id: str) -> dict[str, str]:
    """Classify supplied strategy ID, never trust a caller's policy assertion.

    Unknown labels remain exploratory for legacy/manual compatibility; they
    never become new R1 strategies. Former proposals passed as modes fail closed.
    """
    if not isinstance(strategy_id, str) or not strategy_id.strip():
        raise ValueError("R1_STRATEGY_ID_REQUIRED")
    mode = strategy_id.strip().lower()
    if mode in OBJECTIVES_NOT_MODES:
        raise ValueError("R1_OBJECTIVE_NOT_STRATEGY")
    if mode == "high-cagr":
        authority = "V2_HIGH_CAGR_EXISTING_SCOPE_ONLY"
        limitation = (
            "Existing High-CAGR V2 policy applies only within its approved scope; "
            "this R1 assembler does not verify or load that method."
        )
    elif mode in R1_MODES:
        authority = "R1_POLICY_REQUIRES_CEO_APPROVAL"
        limitation = (
            "This R1 mode has CEO-selected qualitative design only. Its "
            "investment policy, numeric limits, assets and methods require "
            "separate CEO approval and verified loading before mode-specific "
            "allocation, sales or decision-grade conclusions."
        )
    elif mode == "exploratory":
        authority = "EXPLORATORY_NO_STRATEGY_POLICY"
        limitation = (
            "Exploratory research has no mode-specific investment policy "
            "or decision-grade allocation authority."
        )
    else:
        authority = "UNRECOGNIZED_R1_MODE_NO_AUTHORITY"
        limitation = (
            "Unrecognized strategy label is not one of the six approved R1 "
            "design modes; no policy or investment authority can be inferred."
        )
    return {
        "r1_mode": mode if mode in R1_MODES else "NOT_SELECTED_OR_UNSUPPORTED",
        "policy_authority": authority,
        "method_load": "NOT_VERIFIED",
        "decision_grade": "NOT_ESTABLISHED",
        "limitation": limitation,
    }
