from __future__ import annotations

from typing import Any

from .utils import clamp, safe_float


CASH_FLOW_QUALITY_COLUMNS = [
    "universe",
    "ticker",
    "business_profile",
    "cash_flow_quality_status",
    "cash_flow_quality_score",
    "cash_flow_quality_adjustment",
    "operating_cash_flow",
    "capital_expenditures",
    "free_cash_flow",
    "free_cash_flow_margin",
    "free_cash_flow_growth",
    "fcf_conversion",
    "net_debt_to_fcf",
    "cash_flow_metrics_available_count",
    "cash_flow_quality_reason",
]

NON_PRIMARY_CASH_FLOW_PROFILES = {
    "BANK",
    "INSURANCE",
    "REIT",
    "UTILITY",
    "PIPELINE",
    "ALT_ASSET_MANAGER",
    "ASSET_MANAGER",
}


def compute_cash_flow_quality(analysis: dict[str, Any]) -> dict[str, Any]:
    """Evaluate whether reported earnings are backed by durable free cash flow.

    This is a sizing and risk layer, not a replacement for the fundamental score.
    Some sectors have cash-flow statements that are not comparable to normal
    operating businesses, so they are labeled instead of penalized mechanically.
    """

    profile = str(analysis.get("business_profile") or "").upper()
    operating_cash_flow = safe_float(analysis.get("operating_cash_flow"))
    capex = safe_float(analysis.get("capital_expenditures"))
    free_cash_flow = safe_float(analysis.get("free_cash_flow"))
    revenue = safe_float(analysis.get("total_revenue"))
    net_income = safe_float(analysis.get("net_income"))
    total_debt = safe_float(analysis.get("total_debt"))
    total_cash = safe_float(analysis.get("total_cash"))

    if free_cash_flow is None and operating_cash_flow is not None and capex is not None:
        free_cash_flow = operating_cash_flow - abs(capex)

    fcf_margin = _ratio_or_existing(analysis.get("free_cash_flow_margin"), free_cash_flow, revenue)
    fcf_conversion = _ratio_or_existing(analysis.get("fcf_conversion"), free_cash_flow, net_income)
    fcf_growth = _ratio_decimal(analysis.get("free_cash_flow_growth"))
    net_debt_to_fcf = safe_float(analysis.get("net_debt_to_fcf"))
    if net_debt_to_fcf is None and total_debt is not None and total_cash is not None and free_cash_flow is not None and free_cash_flow > 0:
        net_debt_to_fcf = (total_debt - total_cash) / free_cash_flow

    available_count = sum(
        value is not None
        for value in [operating_cash_flow, capex, free_cash_flow, fcf_margin, fcf_conversion, fcf_growth, net_debt_to_fcf]
    )

    if profile in NON_PRIMARY_CASH_FLOW_PROFILES:
        reason = (
            "Cash-flow classique non prioritaire pour ce profil d'affaires; le modèle privilégie bilan, "
            "capital, dette, régulation et qualité des actifs plutôt qu'une pénalité FCF mécanique."
        )
        return _result(
            status="CASH_FLOW_MODEL_NOT_PRIMARY",
            score=60.0,
            adjustment=0.0,
            reason=reason,
            operating_cash_flow=operating_cash_flow,
            capex=capex,
            free_cash_flow=free_cash_flow,
            fcf_margin=fcf_margin,
            fcf_growth=fcf_growth,
            fcf_conversion=fcf_conversion,
            net_debt_to_fcf=net_debt_to_fcf,
            available_count=available_count,
        )

    if available_count < 3 or free_cash_flow is None:
        return _result(
            status="CASH_FLOW_UNCERTAIN",
            score=55.0,
            adjustment=-1.0,
            reason="Données cash-flow insuffisantes: légère prudence, sans bloquer une bonne entreprise autrement solide.",
            operating_cash_flow=operating_cash_flow,
            capex=capex,
            free_cash_flow=free_cash_flow,
            fcf_margin=fcf_margin,
            fcf_growth=fcf_growth,
            fcf_conversion=fcf_conversion,
            net_debt_to_fcf=net_debt_to_fcf,
            available_count=available_count,
        )

    components = {
        "fcf_margin": _fcf_margin_points(fcf_margin),
        "fcf_conversion": _fcf_conversion_points(fcf_conversion, free_cash_flow, net_income),
        "balance_sheet_fcf": _net_debt_to_fcf_points(net_debt_to_fcf),
        "fcf_trend": _fcf_growth_points(fcf_growth),
        "cash_generation": _cash_generation_points(operating_cash_flow, free_cash_flow),
    }
    score = round(clamp(sum(components.values()), 0, 100), 2)
    status = _status_for_score(score, free_cash_flow, fcf_margin, fcf_conversion, net_debt_to_fcf)
    adjustment = _adjustment_for_status(status)
    reason = _reason_for_status(status, components, fcf_margin, fcf_conversion, net_debt_to_fcf, fcf_growth)

    return _result(
        status=status,
        score=score,
        adjustment=adjustment,
        reason=reason,
        operating_cash_flow=operating_cash_flow,
        capex=capex,
        free_cash_flow=free_cash_flow,
        fcf_margin=fcf_margin,
        fcf_growth=fcf_growth,
        fcf_conversion=fcf_conversion,
        net_debt_to_fcf=net_debt_to_fcf,
        available_count=available_count,
        components=components,
    )


def cash_flow_rows_for_csv(*analysis_groups: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for group in analysis_groups:
        for row in group.values():
            rows.append(
                {
                    "universe": row.get("universe"),
                    "ticker": row.get("ticker_display", row.get("ticker")),
                    "business_profile": row.get("business_profile"),
                    "cash_flow_quality_status": row.get("cash_flow_quality_status"),
                    "cash_flow_quality_score": row.get("cash_flow_quality_score"),
                    "cash_flow_quality_adjustment": row.get("cash_flow_quality_adjustment"),
                    "operating_cash_flow": row.get("operating_cash_flow"),
                    "capital_expenditures": row.get("capital_expenditures"),
                    "free_cash_flow": row.get("free_cash_flow"),
                    "free_cash_flow_margin": row.get("free_cash_flow_margin"),
                    "free_cash_flow_growth": row.get("free_cash_flow_growth"),
                    "fcf_conversion": row.get("fcf_conversion"),
                    "net_debt_to_fcf": row.get("net_debt_to_fcf"),
                    "cash_flow_metrics_available_count": row.get("cash_flow_metrics_available_count"),
                    "cash_flow_quality_reason": row.get("cash_flow_quality_reason"),
                }
            )
    return rows


def _result(
    *,
    status: str,
    score: float,
    adjustment: float,
    reason: str,
    operating_cash_flow: float | None,
    capex: float | None,
    free_cash_flow: float | None,
    fcf_margin: float | None,
    fcf_growth: float | None,
    fcf_conversion: float | None,
    net_debt_to_fcf: float | None,
    available_count: int,
    components: dict[str, float] | None = None,
) -> dict[str, Any]:
    return {
        "cash_flow_quality_status": status,
        "cash_flow_quality_score": round(score, 2),
        "cash_flow_quality_adjustment": round(adjustment, 2),
        "cash_flow_quality_reason": reason,
        "cash_flow_quality_components": components or {},
        "operating_cash_flow": operating_cash_flow,
        "capital_expenditures": capex,
        "free_cash_flow": free_cash_flow,
        "free_cash_flow_margin": fcf_margin,
        "free_cash_flow_growth": fcf_growth,
        "fcf_conversion": fcf_conversion,
        "net_debt_to_fcf": net_debt_to_fcf,
        "cash_flow_metrics_available_count": available_count,
    }


def _ratio_or_existing(existing: Any, numerator: float | None, denominator: float | None) -> float | None:
    current = _ratio_decimal(existing)
    if current is not None:
        return current
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def _ratio_decimal(value: Any) -> float | None:
    number = safe_float(value)
    if number is None:
        return None
    if abs(number) > 5:
        return number / 100
    return number


def _fcf_margin_points(value: float | None) -> float:
    if value is None:
        return 12.0
    if value >= 0.20:
        return 25.0
    if value >= 0.12:
        return 21.0
    if value >= 0.06:
        return 15.0
    if value >= 0:
        return 8.0
    return 0.0


def _fcf_conversion_points(value: float | None, free_cash_flow: float | None, net_income: float | None) -> float:
    if value is None:
        if free_cash_flow is not None and free_cash_flow > 0 and net_income is not None and net_income <= 0:
            return 12.0
        return 12.0
    if value >= 1.0:
        return 25.0
    if value >= 0.80:
        return 22.0
    if value >= 0.50:
        return 15.0
    if value >= 0.20:
        return 8.0
    return 2.0


def _net_debt_to_fcf_points(value: float | None) -> float:
    if value is None:
        return 10.0
    if value <= 0:
        return 20.0
    if value <= 2.0:
        return 18.0
    if value <= 4.0:
        return 13.0
    if value <= 6.0:
        return 8.0
    return 2.0


def _fcf_growth_points(value: float | None) -> float:
    if value is None:
        return 8.0
    if value >= 0.15:
        return 15.0
    if value >= 0.03:
        return 12.0
    if value >= -0.05:
        return 9.0
    if value >= -0.20:
        return 4.0
    return 1.0


def _cash_generation_points(operating_cash_flow: float | None, free_cash_flow: float | None) -> float:
    if free_cash_flow is not None and free_cash_flow > 0 and (operating_cash_flow is None or operating_cash_flow > 0):
        return 15.0
    if free_cash_flow is not None and free_cash_flow > 0:
        return 10.0
    if operating_cash_flow is not None and operating_cash_flow < 0:
        return 2.0
    if free_cash_flow is not None and free_cash_flow < 0:
        return 1.0
    return 6.0


def _status_for_score(
    score: float,
    free_cash_flow: float | None,
    fcf_margin: float | None,
    fcf_conversion: float | None,
    net_debt_to_fcf: float | None,
) -> str:
    if free_cash_flow is not None and free_cash_flow < 0:
        return "CASH_FLOW_STRESS" if score < 45 else "WEAK_CASH_CONVERSION"
    if net_debt_to_fcf is not None and net_debt_to_fcf > 6 and score < 60:
        return "WEAK_CASH_CONVERSION"
    if score >= 85 and (fcf_margin is None or fcf_margin >= 0.12) and (fcf_conversion is None or fcf_conversion >= 0.80):
        return "EXCELLENT_CASH_COMPOUNDER"
    if score >= 72:
        return "GOOD_CASH_GENERATOR"
    if score >= 55:
        return "ACCEPTABLE_BUT_MONITOR"
    if score >= 40:
        return "WEAK_CASH_CONVERSION"
    return "CASH_FLOW_STRESS"


def _adjustment_for_status(status: str) -> float:
    return {
        "EXCELLENT_CASH_COMPOUNDER": 4.0,
        "GOOD_CASH_GENERATOR": 2.0,
        "ACCEPTABLE_BUT_MONITOR": 0.0,
        "WEAK_CASH_CONVERSION": -4.0,
        "CASH_FLOW_STRESS": -8.0,
        "CASH_FLOW_UNCERTAIN": -1.0,
        "CASH_FLOW_MODEL_NOT_PRIMARY": 0.0,
    }.get(status, 0.0)


def _reason_for_status(
    status: str,
    components: dict[str, float],
    fcf_margin: float | None,
    fcf_conversion: float | None,
    net_debt_to_fcf: float | None,
    fcf_growth: float | None,
) -> str:
    reason = f"Statut cash-flow: {status}."
    if fcf_margin is not None:
        reason += f" Marge FCF {fcf_margin:.1%}."
    if fcf_conversion is not None:
        reason += f" Conversion FCF/bénéfice {fcf_conversion:.2f}x."
    if net_debt_to_fcf is not None:
        reason += f" Dette nette/FCF {net_debt_to_fcf:.2f}x."
    if fcf_growth is not None:
        reason += f" Croissance FCF récente {fcf_growth:.1%}."
    if status in {"WEAK_CASH_CONVERSION", "CASH_FLOW_STRESS"}:
        reason += " Prudence: les profits ou la croissance semblent moins bien convertis en cash durable."
    elif status in {"EXCELLENT_CASH_COMPOUNDER", "GOOD_CASH_GENERATOR"}:
        reason += " Les profits semblent mieux appuyés par du cash réinvestissable."
    elif components:
        reason += " Profil acceptable, mais sans avantage cash-flow majeur."
    return reason
