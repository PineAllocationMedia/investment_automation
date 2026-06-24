from __future__ import annotations

from typing import Any

from .benchmark_relevance_engine import benchmark_relevance_level
from .manual_inputs import CATASTROPHIC_COLUMNS
from .utils import safe_float


def compute_thesis_status(
    manual: dict[str, Any],
    score: dict[str, Any],
    market: dict[str, Any],
    benchmark: dict[str, Any],
) -> dict[str, Any]:
    broken_reasons = [field for field in CATASTROPHIC_COLUMNS if manual.get(field) is True]
    if broken_reasons:
        return {
            "thesis_status": "BROKEN",
            "fundamental_thesis_status": "BROKEN",
            "market_watch_status": "NOT_RELEVANT",
            "valuation_watch_status": "NOT_RELEVANT",
            "thesis_reasons": [f"Signal catastrophique: {field}" for field in broken_reasons],
            "fundamental_thesis_reasons": [f"Signal catastrophique: {field}" for field in broken_reasons],
            "market_watch_reasons": [],
            "valuation_watch_reasons": [],
        }

    missing_count = int(score.get("score_missing_data_count") or 0)
    if missing_count > 5:
        return {
            "thesis_status": "UNCERTAIN",
            "fundamental_thesis_status": "UNCERTAIN",
            "market_watch_status": "UNCERTAIN",
            "valuation_watch_status": "UNCERTAIN",
            "thesis_reasons": ["Trop de données critiques manquent pour confirmer la thèse."],
            "fundamental_thesis_reasons": ["Trop de données critiques manquent pour confirmer la thèse."],
            "market_watch_reasons": [],
            "valuation_watch_reasons": [],
        }

    eps_est = safe_float(score.get("eps_growth_estimated_3_5y"))
    eps_hist = safe_float(score.get("eps_growth_5y"))
    peg = safe_float(score.get("peg"))
    price_to_fair_value = safe_float(score.get("price_to_fair_value"))
    sector_cagr = safe_float(score.get("sector_cagr_estimated"))
    weak_growth_threshold = safe_float(score.get("profile_weak_growth_threshold")) or 10.0
    sector_threshold = safe_float(score.get("profile_sector_cagr_threshold")) or 8.0
    peg_limit = safe_float(score.get("profile_peg_limit")) or 2.0
    benchmark_5y = safe_float(benchmark.get("benchmark_5y_cagr"))
    relevance = benchmark_relevance_level(benchmark)
    stock_return_1y = safe_float(market.get("stock_return_1y"))
    benchmark_return_1y = safe_float(benchmark.get("benchmark_return_1y"))
    underperformance = (
        stock_return_1y - benchmark_return_1y
        if stock_return_1y is not None and benchmark_return_1y is not None
        else None
    )

    fundamental_reasons: list[str] = []
    market_watch_reasons: list[str] = []
    valuation_watch_reasons: list[str] = []

    if eps_est is not None and eps_est <= 0 and _field_confirmed(manual, "eps_growth_estimated_3_5y"):
        fundamental_reasons.append("Croissance EPS estimée non positive confirmée.")
    elif eps_est is not None and 0 < eps_est < weak_growth_threshold:
        market_watch_reasons.append(f"Croissance EPS estimée positive mais sous le seuil du profil ({weak_growth_threshold:.0f} %).")
    if manual.get("moat_clear") is False and _field_confirmed(manual, "moat_clear"):
        fundamental_reasons.append("Moat affaibli ou absent confirmé.")
    if manual.get("margin_or_profitability_under_pressure") is True and _field_confirmed(manual, "margin_or_profitability_under_pressure"):
        fundamental_reasons.append("Marge ou rentabilité sous pression confirmée.")
    elif manual.get("margin_or_profitability_under_pressure") is True:
        market_watch_reasons.append("Marge ou rentabilité sous pression possible, mais non confirmée.")
    if manual.get("balance_sheet_strong") is False and _field_confirmed(manual, "balance_sheet_strong"):
        fundamental_reasons.append("Bilan financier affaibli confirmé.")
    elif manual.get("balance_sheet_strong") is False:
        market_watch_reasons.append("Bilan financier possiblement affaibli, mais non confirmé.")
    if manual.get("forward_pe_growth_acceptable") is False and _field_confirmed(manual, "forward_pe_growth_acceptable"):
        valuation_watch_reasons.append("Forward P/E non acceptable selon la croissance, confirmé.")
    elif manual.get("forward_pe_growth_acceptable") is False:
        valuation_watch_reasons.append("Forward P/E possiblement non acceptable, mais non confirmé.")
    if manual.get("valuation_vs_5y_avg_ok") is False:
        valuation_watch_reasons.append("Valorisation supérieure à la moyenne 5 ans.")

    if peg is not None and peg > peg_limit + 1.5:
        valuation_watch_reasons.append("PEG très élevé.")
    elif peg is not None and peg > peg_limit + 0.5 and (eps_est is None or eps_est < weak_growth_threshold):
        valuation_watch_reasons.append("PEG élevé sans croissance suffisante confirmée.")
    if price_to_fair_value is not None and price_to_fair_value > 1.40:
        valuation_watch_reasons.append("Prix / juste valeur > 1.40.")

    if sector_cagr is not None and sector_cagr < 0:
        if _field_confirmed(manual, "sector_cagr_estimated"):
            fundamental_reasons.append("Déclin structurel du secteur confirmé.")
        else:
            market_watch_reasons.append("Proxy sectoriel négatif, à valider.")
    elif sector_cagr is not None and sector_cagr < sector_threshold:
        market_watch_reasons.append(f"Croissance sectorielle estimée sous le seuil du profil ({sector_threshold:.0f} %).")
    if benchmark_5y is not None and benchmark_5y < 0.03:
        if relevance == "LOW":
            market_watch_reasons.append("ETF de comparaison faible sur 5 ans, mais pertinence faible; signal informatif.")
        else:
            market_watch_reasons.append(f"ETF de comparaison faible sur 5 ans (pertinence {relevance}).")
    if market.get("price_above_sma_200") is False:
        market_watch_reasons.append("Prix sous SMA 200.")
    underperformance_threshold = -0.35 if relevance == "LOW" else -0.20
    if underperformance is not None and underperformance <= underperformance_threshold and (
        (eps_est is not None and eps_est < weak_growth_threshold)
        or manual.get("margin_or_profitability_under_pressure") is True
        or manual.get("moat_clear") is False
    ):
        market_watch_reasons.append(f"Sous-performance notable avec signal fondamental faible ou à valider (pertinence {relevance}).")
    if manual.get("regulatory_risk_high") is True:
        market_watch_reasons.append("Risque réglementaire élevé.")
    if manual.get("geopolitical_risk_high") is True:
        market_watch_reasons.append("Risque géopolitique élevé.")
    if manual.get("single_product_dependency_high") is True:
        market_watch_reasons.append("Dépendance élevée à un seul produit.")

    growth_positive = (eps_est is not None and eps_est > 0) or (eps_hist is not None and eps_hist > 0)
    roic_not_destroyed = manual.get("catastrophic_roic_destroyed") is not True
    margin_not_majorly_deteriorating = not (
        manual.get("margin_or_profitability_under_pressure") is True
        and _field_confirmed(manual, "margin_or_profitability_under_pressure")
    )
    moat_present = manual.get("moat_clear") is True or manual.get("moat_clear") is None or not _field_confirmed(manual, "moat_clear")
    sector_not_declining = not (
        (sector_cagr is not None and sector_cagr < 0 and _field_confirmed(manual, "sector_cagr_estimated"))
    )

    market_watch_status = _watch_status(market_watch_reasons)
    valuation_watch_status = _valuation_status(valuation_watch_reasons)

    if fundamental_reasons:
        return _result(
            "WEAKENING",
            fundamental_reasons,
            market_watch_status,
            valuation_watch_status,
            market_watch_reasons,
            valuation_watch_reasons,
        )

    if growth_positive and roic_not_destroyed and margin_not_majorly_deteriorating and moat_present and sector_not_declining:
        reasons = ["Aucun signal fondamental majeur de cassure détecté."]
        if market_watch_reasons or valuation_watch_reasons:
            reasons.append("Alertes de marché/valorisation séparées de la thèse fondamentale.")
        return _result(
            "INTACT",
            reasons,
            market_watch_status,
            valuation_watch_status,
            market_watch_reasons,
            valuation_watch_reasons,
        )

    if missing_count > 3:
        return {
            "thesis_status": "UNCERTAIN",
            "fundamental_thesis_status": "UNCERTAIN",
            "market_watch_status": market_watch_status,
            "valuation_watch_status": valuation_watch_status,
            "thesis_reasons": ["La thèse peut être bonne, mais trop d’éléments restent non confirmés."],
            "fundamental_thesis_reasons": ["La thèse peut être bonne, mais trop d’éléments restent non confirmés."],
            "market_watch_reasons": market_watch_reasons,
            "valuation_watch_reasons": valuation_watch_reasons,
        }

    return _result(
        "WEAKENING",
        ["La croissance ou le moat ne sont pas assez confirmés."],
        market_watch_status,
        valuation_watch_status,
        market_watch_reasons,
        valuation_watch_reasons,
    )


def _result(
    thesis_status: str,
    thesis_reasons: list[str],
    market_watch_status: str,
    valuation_watch_status: str,
    market_watch_reasons: list[str],
    valuation_watch_reasons: list[str],
) -> dict[str, Any]:
    return {
        "thesis_status": thesis_status,
        "fundamental_thesis_status": thesis_status,
        "market_watch_status": market_watch_status,
        "valuation_watch_status": valuation_watch_status,
        "thesis_reasons": thesis_reasons,
        "fundamental_thesis_reasons": thesis_reasons,
        "market_watch_reasons": market_watch_reasons,
        "valuation_watch_reasons": valuation_watch_reasons,
    }


def _watch_status(reasons: list[str]) -> str:
    if not reasons:
        return "NORMAL"
    serious_terms = ("négatif", "sous SMA 200", "Sous-performance", "réglementaire", "géopolitique")
    serious_count = sum(1 for reason in reasons if any(term in reason for term in serious_terms))
    return "WEAK" if serious_count >= 2 else "WATCH"


def _valuation_status(reasons: list[str]) -> str:
    if not reasons:
        return "NORMAL"
    if any("1.40" in reason or "très élevé" in reason for reason in reasons):
        return "EXTREME"
    return "WATCH"


def _field_confirmed(manual: dict[str, Any], field: str) -> bool:
    manual_fields = _field_set(manual.get("manual_override_fields"))
    research_fields = _field_set(manual.get("research_report_fields"))
    auto_fields = _field_set(manual.get("auto_estimated_fields"))
    if field in manual_fields:
        return True
    if field in research_fields:
        return _research_field_confidence(manual, field) != "LOW"
    return field not in auto_fields


def _research_field_confidence(manual: dict[str, Any], field: str) -> str:
    values = manual.get("research_report_field_confidence") or {}
    if isinstance(values, dict):
        confidence = str(values.get(field) or "").strip().upper()
        return confidence or "MEDIUM"
    text = str(values or "")
    for part in text.replace(",", ";").split(";"):
        if ":" not in part:
            continue
        key, value = part.split(":", 1)
        if key.strip() == field:
            return str(value).strip().upper() or "MEDIUM"
    return "MEDIUM"


def _field_set(value: Any) -> set[str]:
    if not value:
        return set()
    if isinstance(value, str):
        return {part.strip() for part in value.replace(";", ",").split(",") if part.strip()}
    return {str(part).strip() for part in value if str(part).strip()}
