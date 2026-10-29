"""Non-binding, differentiated R1 research questions for manual IR/PI handoffs.

Research questions are not investment policies, allocation rules, recommendations,
source certifications or evidence that a ChatGPT Project loaded a method.
"""
from __future__ import annotations

from .strategy_authority import R1_MODES, assess_r1_mode

# These are design-orientation questions, NOT policy instructions or target weights.
# In particular, do not transfer High-CAGR's VFV hurdle to other R1 modes.
_MODE_QUESTIONS = {
    "high-cagr": (
        (
            "What original evidence supports durable per-share compounding and its main permanent-loss countercase?",
            "Which normalized bear/base/bull assumptions could support a VFV opportunity-cost comparison without inventing expected alpha?",
        ),
        (
            "What observed concentration, shared exposures and new-contribution room exist relative to the approved High-CAGR scope?",
            "Is there actual thesis deterioration warranting exceptional review, rather than a price-driven automatic sale?",
        ),
        "HIGH_CAGR_METHOD_R1.md",
    ),
    "balanced": (
        (
            "How do the documented return drivers and risks differ across stocks, bonds, gold and other justified assets?",
            "What recession, inflation and concentration countercases challenge steady growth and resilience?",
        ),
        (
            "Which visible cross-asset exposures and overlapping risks limit diversification and resilience?",
            "What new-contribution options merit review before any rebalance, subject to unapproved R1 policy bands and costs?",
        ),
        "POLICY_PROPOSAL_BALANCED_R1.md",
    ),
    "family-office": (
        (
            "What evidence supports investment-portfolio durability across the family's stated horizon and financial obligations?",
            "Which tax, liquidity and reporting uncertainties could materially alter an investment-only comparison?",
        ),
        (
            "What account-level exposures and dated investment liquidity requirements are actually known versus missing?",
            "How might new contributions fit family investment constraints and known costs, without inferring household assets or cash policy?",
        ),
        "POLICY_PROPOSAL_FAMILY_OFFICE_R1.md",
    ),
    "rational-aggressive": (
        (
            "How do normalized economics, valuation asymmetry and downside scenarios withstand the strongest counter-thesis?",
            "What source and confidence gaps undermine the case for an unusually attractive net long-run return?",
        ),
        (
            "What observed shared exposures and concentration could amplify permanent loss rather than just volatility?",
            "Which evidence and costs would be necessary before any high-conviction new-contribution proposal under approved bounds?",
        ),
        "POLICY_PROPOSAL_RATIONAL_AGGRESSIVE_R1.md",
    ),
    "intelligent-dividend-harvester": (
        (
            "Do original cash-flow, payout, balance-sheet and reinvestment records support sustainable growing distributions?",
            "What valuation, dilution and payout-cut countercases challenge yield and dividend growth?",
        ),
        (
            "Which visible holdings and confirmed distributions match the user's stated cash needs and account scope?",
            "How do known taxes, FX costs, reinvestment constraints and gaps affect conditional new-contribution research?",
        ),
        "POLICY_PROPOSAL_INTELLIGENT_DIVIDEND_HARVESTER_R1.md",
    ),
    "modern-adaptive-browne": (
        (
            "What evidence supports or weakens growth, deflation, inflation and short-duration liquidity hedge functions?",
            "How might joint stock-bond losses, duration, currency and gold risks defeat diversification without forecasting regimes?",
        ),
        (
            "What actually observed holdings cover each economic hedge function, with look-through and FX uncertainties?",
            "Which stress and liquidity gaps need review before any policy-gated sleeve weights, reserve or rebalancing?",
        ),
        "POLICY_PROPOSAL_MODERN_ADAPTIVE_BROWNE_R1.md",
    ),
}

_GENERIC_IR = (
    "Which source-qualified Quality, Durability, Expected Return and Confidence facts are supported or unknown?",
)
_GENERIC_PI = (
    "Which holdings, costs and Portfolio Room conclusions are actually supported by dated visible evidence?",
)


def prepare_strategy_research_brief(strategy_id: str) -> dict[str, object]:
    """Return fixed questions and authority limits, never an approved strategy."""
    gate = assess_r1_mode(strategy_id)
    mode = gate["r1_mode"]
    if mode in R1_MODES:
        ir_questions, pi_questions, document = _MODE_QUESTIONS[mode]
        reference = "docs/ai_native/integrated_build/research/" + document
    else:
        ir_questions, pi_questions, reference = _GENERIC_IR, _GENERIC_PI, None
    return {
        "status": "NON_BINDING_RESEARCH_QUESTIONS_ONLY",
        "r1_mode": mode,
        "policy_authority": gate["policy_authority"],
        "method_load": "NOT_VERIFIED",
        "design_reference_not_loaded_or_approved": reference,
        "ir_research_questions": list(ir_questions),
        "pi_portfolio_questions": list(pi_questions),
        "decision_grade_authority": "NONE",
        "allocation_or_sale_authority": "NONE",
        "source_authentication": "NOT_PERFORMED",
    }
