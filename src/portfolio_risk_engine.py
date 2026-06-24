from __future__ import annotations

from collections import defaultdict
from typing import Any

from .utils import safe_float


TECH_AI_SEMI_FACTORS = {"technology", "cloud", "AI", "semiconductors", "infrastructure", "software", "vertical_markets"}


def compute_portfolio_risk(
    portfolio_rows: list[dict[str, Any]],
    sectors: dict[str, str],
    exposures: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    total_value = sum(safe_float(row.get("current_value")) or 0.0 for row in portfolio_rows)
    positions = []
    for row in portfolio_rows:
        ticker = row["ticker"]
        value = safe_float(row.get("current_value")) or 0.0
        weight = value / total_value if total_value > 0 else 0.0
        exposure = exposures.get(ticker, {})
        positions.append(
            {
                "ticker": ticker,
                "current_value": value,
                "weight": weight,
                "sector": sectors.get(ticker, "Unknown"),
                "region": exposure.get("region", "Unknown"),
                "currency": exposure.get("currency", "Unknown"),
                "factor_exposure": exposure.get("factor_exposure", []),
            }
        )

    by_sector = _aggregate_weights(positions, "sector")
    by_region = _aggregate_weights(positions, "region")
    by_currency = _aggregate_weights(positions, "currency")
    by_factor = defaultdict(float)
    for position in positions:
        factors = position.get("factor_exposure") or []
        for factor in factors:
            by_factor[str(factor)] += position["weight"]

    sorted_positions = sorted(positions, key=lambda row: row["weight"], reverse=True)
    top3_weight = sum(row["weight"] for row in sorted_positions[:3])
    top5_weight = sum(row["weight"] for row in sorted_positions[:5])
    effective_positions = 1 / sum(row["weight"] ** 2 for row in positions) if positions and total_value > 0 else 0.0
    tech_ai_semi_weight = sum(
        position["weight"]
        for position in positions
        if any(factor in TECH_AI_SEMI_FACTORS for factor in position.get("factor_exposure", []))
    )

    alerts: list[dict[str, Any]] = []
    for position in sorted_positions:
        if position["weight"] > 0.40:
            alerts.append(_alert("action", position["ticker"], position["weight"], "concentration extrême"))
        elif position["weight"] > 0.30:
            alerts.append(_alert("action", position["ticker"], position["weight"], "concentration élevée"))

    for sector, weight in by_sector.items():
        if weight > 0.55:
            alerts.append(_alert("secteur", sector, weight, "risque sectoriel extrême"))
        elif weight > 0.40:
            alerts.append(_alert("secteur", sector, weight, "risque sectoriel élevé"))

    usd_weight = by_currency.get("USD", 0.0)
    if usd_weight > 0.90:
        alerts.append(_alert("devise", "USD", usd_weight, "exposition USD extrême"))
    elif usd_weight > 0.75:
        alerts.append(_alert("devise", "USD", usd_weight, "forte exposition USD"))

    if top3_weight > 0.75:
        alerts.append(_alert("top3", "Top 3 positions", top3_weight, "concentration extrême"))
    elif top3_weight > 0.60:
        alerts.append(_alert("top3", "Top 3 positions", top3_weight, "portefeuille très concentré"))

    for factor, weight in by_factor.items():
        if weight > 0.40:
            alerts.append(_alert("facteur", factor, weight, "corrélation cachée possible"))

    if tech_ai_semi_weight > 0.40:
        alerts.append(_alert("facteur", "tech/IA/semi-conducteurs", tech_ai_semi_weight, "exposition thématique élevée"))

    return {
        "total_portfolio_value": total_value,
        "positions": positions,
        "concentration_by_action": {row["ticker"]: row["weight"] for row in positions},
        "concentration_by_sector": dict(sorted(by_sector.items(), key=lambda item: item[1], reverse=True)),
        "concentration_by_region": dict(sorted(by_region.items(), key=lambda item: item[1], reverse=True)),
        "concentration_by_currency": dict(sorted(by_currency.items(), key=lambda item: item[1], reverse=True)),
        "factor_exposure": dict(sorted(by_factor.items(), key=lambda item: item[1], reverse=True)),
        "effective_positions": effective_positions,
        "top3_weight": top3_weight,
        "top5_weight": top5_weight,
        "tech_ai_semi_weight": tech_ai_semi_weight,
        "usd_weight": by_currency.get("USD", 0.0),
        "cad_weight": by_currency.get("CAD", 0.0),
        "eur_weight": by_currency.get("EUR", 0.0),
        "alerts": alerts,
        "primary_risk": alerts[0]["alert"] if alerts else "Aucun risque dominant extrême détecté avec les données disponibles.",
    }


def _aggregate_weights(positions: list[dict[str, Any]], key: str) -> dict[str, float]:
    totals: defaultdict[str, float] = defaultdict(float)
    for position in positions:
        weight = safe_float(position.get("weight")) or 0.0
        if weight <= 0:
            continue
        totals[str(position.get(key) or "Unknown")] += weight
    return dict(totals)


def _alert(risk_type: str, name: str, weight: float, alert: str) -> dict[str, Any]:
    return {"risk_type": risk_type, "name": name, "weight": weight, "alert": alert}


def risk_rows_for_csv(risk_report: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for alert in risk_report.get("alerts", []):
        rows.append(alert)
    if not rows:
        rows.append({"risk_type": "global", "name": "portfolio", "weight": "", "alert": "Aucune alerte majeure."})
    return rows
