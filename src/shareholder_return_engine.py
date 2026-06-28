from __future__ import annotations

from typing import Any

from .utils import clamp, safe_float


def compute_shareholder_return_quality(analysis: dict[str, Any]) -> dict[str, Any]:
    adjusted_yield = analysis.get("after_tax_yield_adjusted")
    adjusted_number = safe_float(adjusted_yield)
    gross_number = safe_float(analysis.get("dividend_yield"))
    if adjusted_number is None or (gross_number is not None and gross_number > 0 and adjusted_number == 0):
        adjusted_yield = analysis.get("dividend_yield")
    dividend_yield = _yield_percent(adjusted_yield)
    gross_dividend_yield = _yield_percent(analysis.get("dividend_yield"))
    tax_note = str(analysis.get("tax_adjustment_note") or "").strip()
    payout_ratio = _ratio_decimal(analysis.get("payout_ratio"))
    debt_to_equity = _debt_to_equity_percent(analysis.get("debt_to_equity"))
    growth = _best_growth_percent(analysis)
    roic = safe_float(analysis.get("roic_5y_avg"))
    margins_ok = analysis.get("net_margin_stable_or_expanding") is True
    balance_ok = analysis.get("balance_sheet_strong") is True
    moat_ok = analysis.get("moat_clear") is True
    thesis_ok = analysis.get("thesis_status") == "INTACT"
    liquidation_ok = analysis.get("liquidation_status") == "GREEN"

    payout_ok = payout_ratio is None or payout_ratio <= 0.65
    payout_stretched = payout_ratio is not None and payout_ratio > 0.80
    debt_stretched = debt_to_equity is not None and debt_to_equity > 120
    debt_dangerous = debt_to_equity is not None and debt_to_equity > 180
    quality_backstop = (roic is not None and roic >= 15) or moat_ok or (margins_ok and balance_ok)
    growth_value = growth if growth is not None else 0.0

    if dividend_yield is None or dividend_yield <= 0:
        if growth_value >= 10 and quality_backstop:
            score = 78.0
            profile = "REINVESTMENT_COMPOUNDER"
            adjustment = 0.5
            reason = "Aucun dividende significatif: le rendement total dépend surtout du réinvestissement interne et de la croissance."
        else:
            score = 60.0
            profile = "NO_DIVIDEND_OR_UNKNOWN"
            adjustment = 0.0
            reason = "Dividende absent ou inconnu; aucun bonus ni pénalité mécanique."
    elif dividend_yield <= 1.5:
        score = 84.0 if growth_value >= 8 and quality_backstop else 68.0
        profile = "LOW_YIELD_GROWTH_COMPOUNDER"
        adjustment = 1.5 if score >= 80 else 0.5
        reason = "Faible dividende réinvesti: compatible avec un profil haut CAGR si la croissance et la qualité restent fortes."
    elif dividend_yield <= 3.5:
        if growth_value >= 6 and payout_ok and not debt_stretched and quality_backstop:
            score = 90.0
            profile = "BALANCED_TOTAL_RETURN_COMPOUNDER"
            adjustment = 2.5
            reason = "Dividende modéré et réinvestissable avec croissance/qualité suffisantes: bon profil de rendement total."
        else:
            score = 65.0
            profile = "DIVIDEND_NEEDS_GROWTH_CONFIRMATION"
            adjustment = 0.0
            reason = "Dividende utile, mais croissance, payout ou bilan à confirmer avant de le valoriser."
    elif dividend_yield <= 5.0:
        if growth_value >= 5 and payout_ok and not debt_stretched and quality_backstop:
            score = 72.0
            profile = "HIGHER_YIELD_TOTAL_RETURN_REVIEW"
            adjustment = 0.5
            reason = "Dividende assez élevé: acceptable seulement avec croissance, payout et bilan encore solides."
        else:
            score = 45.0
            profile = "HIGH_YIELD_QUALITY_RISK"
            adjustment = -2.5
            reason = "Dividende élevé avec qualité ou croissance insuffisamment robuste: risque de rendement total plus faible."
    else:
        if growth_value >= 5 and payout_ok and not debt_dangerous and quality_backstop:
            score = 55.0
            profile = "HIGH_YIELD_MANUAL_REVIEW"
            adjustment = -1.0
            reason = "Très haut dividende: exige une validation manuelle même si les fondamentaux semblent acceptables."
        else:
            score = 25.0
            profile = "YIELD_TRAP_RISK"
            adjustment = -7.0
            reason = "Très haut dividende sans preuves suffisantes de durabilité: risque de piège à rendement."

    if payout_stretched:
        score -= 12.0
        adjustment -= 2.0
        reason += " Payout possiblement trop élevé."
    if debt_dangerous:
        score -= 10.0
        adjustment -= 2.0
        reason += " Dette élevée par rapport aux fonds propres."
    if not thesis_ok or not liquidation_ok:
        adjustment = min(adjustment, 0.0)
        reason += " Aucun bonus positif si la thèse ou le statut de liquidation n’est pas pleinement vert."
    if analysis.get("quality_but_too_expensive") is True:
        adjustment = min(adjustment, 0.5)
        reason += " Valorisation exigeante: le rendement total ne justifie pas un gros bonus."
    if tax_note and gross_dividend_yield is not None:
        reason += f" Rendement utilisé: after-tax est. (approx.) {dividend_yield or 0:.2f}% vs brut {gross_dividend_yield:.2f}%. {tax_note}"

    return {
        "shareholder_return_quality_score": round(clamp(score, 0, 100), 2),
        "shareholder_return_profile": profile,
        "shareholder_return_adjustment": round(clamp(adjustment, -8, 3), 2),
        "shareholder_return_reason": reason,
    }


def _yield_percent(value: Any) -> float | None:
    dividend_yield = safe_float(value)
    if dividend_yield is None:
        return None
    if dividend_yield <= 0:
        return 0.0
    if dividend_yield <= 0.20:
        return dividend_yield * 100
    return dividend_yield


def _ratio_decimal(value: Any) -> float | None:
    ratio = safe_float(value)
    if ratio is None:
        return None
    return ratio / 100 if ratio > 3 else ratio


def _debt_to_equity_percent(value: Any) -> float | None:
    debt_to_equity = safe_float(value)
    if debt_to_equity is None:
        return None
    return debt_to_equity * 100 if debt_to_equity <= 5 else debt_to_equity


def _best_growth_percent(analysis: dict[str, Any]) -> float | None:
    values = [
        safe_float(analysis.get("eps_growth_estimated_3_5y")),
        safe_float(analysis.get("eps_growth_5y")),
        _growth_percent(analysis.get("earnings_growth")),
        _growth_percent(analysis.get("revenue_growth")),
    ]
    present = [value for value in values if value is not None]
    return max(present) if present else None


def _growth_percent(value: Any) -> float | None:
    growth = safe_float(value)
    if growth is None:
        return None
    return growth * 100 if abs(growth) <= 5 else growth
