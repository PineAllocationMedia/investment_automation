from __future__ import annotations

from typing import Any

from .utils import clamp, safe_float


SHAREHOLDER_DISCIPLINE_COLUMNS = [
    "universe",
    "ticker",
    "shareholder_discipline_status",
    "shareholder_discipline_score",
    "shareholder_discipline_adjustment",
    "shareholder_discipline_monitoring_status",
    "shares_outstanding",
    "diluted_average_shares",
    "share_count_growth_1y",
    "share_count_cagr_3y",
    "share_count_cagr_5y",
    "share_repurchases",
    "buyback_yield",
    "stock_based_compensation",
    "sbc_to_revenue",
    "fcf_per_share",
    "fcf_per_share_growth",
    "shareholder_discipline_reason",
]


def compute_shareholder_discipline(analysis: dict[str, Any]) -> dict[str, Any]:
    one_year = _ratio_decimal(analysis.get("share_count_growth_1y"))
    cagr_3y = _ratio_decimal(analysis.get("share_count_cagr_3y"))
    cagr_5y = _ratio_decimal(analysis.get("share_count_cagr_5y"))
    buyback_yield = _ratio_decimal(analysis.get("buyback_yield"))
    sbc_to_revenue = _ratio_decimal(analysis.get("sbc_to_revenue"))
    fcf_per_share_growth = _ratio_decimal(analysis.get("fcf_per_share_growth"))
    eps_est = _percent_to_decimal(analysis.get("eps_growth_estimated_3_5y"))
    fcf_status = str(analysis.get("cash_flow_quality_status") or "")

    dilution_rate = _primary_dilution_rate(one_year, cagr_3y, cagr_5y)
    available_count = sum(
        value is not None
        for value in [one_year, cagr_3y, cagr_5y, buyback_yield, sbc_to_revenue, fcf_per_share_growth]
    )

    if dilution_rate is None and available_count < 2:
        return _result(
            status="DILUTION_DATA_UNCERTAIN",
            score=55.0,
            adjustment=-0.5,
            monitoring="NORMAL",
            reason="Données insuffisantes pour juger la dilution; légère prudence, sans signal de vente.",
            analysis=analysis,
            dilution_rate=dilution_rate,
        )

    compensated = _dilution_compensated(fcf_per_share_growth, eps_est, fcf_status)
    components = {
        "share_count_trend": _share_count_points(dilution_rate),
        "fcf_per_share_growth": _fcf_per_share_points(fcf_per_share_growth),
        "buyback_quality": _buyback_points(buyback_yield, dilution_rate),
        "stock_based_compensation": _sbc_points(sbc_to_revenue),
        "growth_compensation": 10.0 if compensated else 4.0,
    }
    score = round(clamp(sum(components.values()), 0, 100), 2)
    status = _status_for(score, dilution_rate, sbc_to_revenue, compensated)
    adjustment = _adjustment_for(status, compensated)
    monitoring = "WATCH" if status == "HIGH_DILUTION_RISK" else "NORMAL"
    reason = _reason_for(status, dilution_rate, buyback_yield, sbc_to_revenue, fcf_per_share_growth, compensated)
    return _result(
        status=status,
        score=score,
        adjustment=adjustment,
        monitoring=monitoring,
        reason=reason,
        analysis=analysis,
        dilution_rate=dilution_rate,
        components=components,
    )


def shareholder_discipline_rows_for_csv(*analysis_groups: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for group in analysis_groups:
        for row in group.values():
            rows.append(
                {
                    "universe": row.get("universe"),
                    "ticker": row.get("ticker_display", row.get("ticker")),
                    "shareholder_discipline_status": row.get("shareholder_discipline_status"),
                    "shareholder_discipline_score": row.get("shareholder_discipline_score"),
                    "shareholder_discipline_adjustment": row.get("shareholder_discipline_adjustment"),
                    "shareholder_discipline_monitoring_status": row.get("shareholder_discipline_monitoring_status"),
                    "shares_outstanding": row.get("shares_outstanding"),
                    "diluted_average_shares": row.get("diluted_average_shares"),
                    "share_count_growth_1y": row.get("share_count_growth_1y"),
                    "share_count_cagr_3y": row.get("share_count_cagr_3y"),
                    "share_count_cagr_5y": row.get("share_count_cagr_5y"),
                    "share_repurchases": row.get("share_repurchases"),
                    "buyback_yield": row.get("buyback_yield"),
                    "stock_based_compensation": row.get("stock_based_compensation"),
                    "sbc_to_revenue": row.get("sbc_to_revenue"),
                    "fcf_per_share": row.get("fcf_per_share"),
                    "fcf_per_share_growth": row.get("fcf_per_share_growth"),
                    "shareholder_discipline_reason": row.get("shareholder_discipline_reason"),
                }
            )
    return rows


def _result(
    *,
    status: str,
    score: float,
    adjustment: float,
    monitoring: str,
    reason: str,
    analysis: dict[str, Any],
    dilution_rate: float | None,
    components: dict[str, float] | None = None,
) -> dict[str, Any]:
    return {
        "shareholder_discipline_status": status,
        "shareholder_discipline_score": round(score, 2),
        "shareholder_discipline_adjustment": round(adjustment, 2),
        "shareholder_discipline_monitoring_status": monitoring,
        "shareholder_discipline_reason": reason,
        "shareholder_discipline_components": components or {},
        "shareholder_discipline_primary_dilution_rate": dilution_rate,
        "shares_outstanding": analysis.get("shares_outstanding"),
        "diluted_average_shares": analysis.get("diluted_average_shares"),
        "share_count_growth_1y": analysis.get("share_count_growth_1y"),
        "share_count_cagr_3y": analysis.get("share_count_cagr_3y"),
        "share_count_cagr_5y": analysis.get("share_count_cagr_5y"),
        "share_repurchases": analysis.get("share_repurchases"),
        "buyback_yield": analysis.get("buyback_yield"),
        "stock_based_compensation": analysis.get("stock_based_compensation"),
        "sbc_to_revenue": analysis.get("sbc_to_revenue"),
        "fcf_per_share": analysis.get("fcf_per_share"),
        "fcf_per_share_growth": analysis.get("fcf_per_share_growth"),
    }


def _primary_dilution_rate(one_year: float | None, cagr_3y: float | None, cagr_5y: float | None) -> float | None:
    for value in [cagr_5y, cagr_3y, one_year]:
        if value is not None:
            return value
    return None


def _dilution_compensated(fcf_per_share_growth: float | None, eps_est: float | None, fcf_status: str) -> bool:
    if fcf_per_share_growth is not None and fcf_per_share_growth >= 0.08:
        return True
    if eps_est is not None and eps_est >= 0.15 and fcf_status in {"EXCELLENT_CASH_COMPOUNDER", "GOOD_CASH_GENERATOR"}:
        return True
    return False


def _share_count_points(dilution_rate: float | None) -> float:
    if dilution_rate is None:
        return 18.0
    if dilution_rate <= -0.01:
        return 35.0
    if dilution_rate <= 0.01:
        return 32.0
    if dilution_rate <= 0.03:
        return 25.0
    if dilution_rate <= 0.06:
        return 16.0
    if dilution_rate <= 0.10:
        return 8.0
    return 0.0


def _fcf_per_share_points(value: float | None) -> float:
    if value is None:
        return 10.0
    if value >= 0.15:
        return 20.0
    if value >= 0.06:
        return 16.0
    if value >= 0:
        return 10.0
    if value >= -0.10:
        return 5.0
    return 0.0


def _buyback_points(buyback_yield: float | None, dilution_rate: float | None) -> float:
    if buyback_yield is None:
        return 8.0
    if buyback_yield >= 0.03 and (dilution_rate is None or dilution_rate <= 0.01):
        return 15.0
    if buyback_yield >= 0.01:
        return 11.0
    if dilution_rate is not None and dilution_rate > 0.06:
        return 3.0
    return 8.0


def _sbc_points(value: float | None) -> float:
    if value is None:
        return 10.0
    if value <= 0.03:
        return 15.0
    if value <= 0.08:
        return 10.0
    if value <= 0.15:
        return 5.0
    return 0.0


def _status_for(score: float, dilution_rate: float | None, sbc_to_revenue: float | None, compensated: bool) -> str:
    high_dilution = dilution_rate is not None and dilution_rate > 0.08
    extreme_dilution = dilution_rate is not None and dilution_rate > 0.12
    high_sbc = sbc_to_revenue is not None and sbc_to_revenue > 0.15

    if (extreme_dilution or high_sbc) and not compensated:
        return "HIGH_DILUTION_RISK"
    if high_dilution and not compensated:
        return "DILUTION_WATCH" if score >= 48 else "HIGH_DILUTION_RISK"
    if score >= 82:
        return "SHAREHOLDER_FRIENDLY"
    if score >= 62:
        return "ACCEPTABLE_DILUTION"
    if score >= 45 or compensated:
        return "DILUTION_WATCH"
    return "HIGH_DILUTION_RISK"


def _adjustment_for(status: str, compensated: bool) -> float:
    if status == "SHAREHOLDER_FRIENDLY":
        return 3.0
    if status == "ACCEPTABLE_DILUTION":
        return 1.0
    if status == "DILUTION_WATCH":
        return -1.5 if compensated else -3.0
    if status == "HIGH_DILUTION_RISK":
        return -7.0
    return -0.5


def _reason_for(
    status: str,
    dilution_rate: float | None,
    buyback_yield: float | None,
    sbc_to_revenue: float | None,
    fcf_per_share_growth: float | None,
    compensated: bool,
) -> str:
    reason = f"Discipline actionnariale: {status}."
    if dilution_rate is not None:
        reason += f" Variation principale du nombre d’actions {dilution_rate:.1%}."
    if buyback_yield is not None:
        reason += f" Rachats/market cap {buyback_yield:.1%}."
    if sbc_to_revenue is not None:
        reason += f" SBC/revenus {sbc_to_revenue:.1%}."
    if fcf_per_share_growth is not None:
        reason += f" Croissance FCF/action {fcf_per_share_growth:.1%}."
    if compensated:
        reason += " La dilution détectée semble partiellement compensée par la croissance par action ou la qualité du cash-flow."
    if status == "HIGH_DILUTION_RISK":
        reason += " Signal de surveillance: le modèle limite le sizing, mais ne recommande pas de vente seulement pour la dilution."
    return reason


def _ratio_decimal(value: Any) -> float | None:
    number = safe_float(value)
    if number is None:
        return None
    if abs(number) > 5:
        return number / 100
    return number


def _percent_to_decimal(value: Any) -> float | None:
    number = safe_float(value)
    if number is None:
        return None
    if abs(number) <= 5:
        return number
    return number / 100
