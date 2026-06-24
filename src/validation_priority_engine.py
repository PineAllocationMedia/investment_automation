from __future__ import annotations

from typing import Any

from .asset_type_engine import is_etf_asset_analysis
from .research_reports import RESEARCH_HELPFUL_FIELDS, research_report_has_usable_fields
from .utils import normalize_ticker, safe_float, write_csv_records


VALIDATION_PRIORITY_COLUMNS = [
    "priority_rank",
    "priority",
    "ticker",
    "universe",
    "company_name",
    "field",
    "field_label",
    "priority_score",
    "reason",
    "decision_impact",
    "suggested_action",
    "bncd_report_needed",
]


FIELD_LABELS = {
    "roic_5y_avg": "ROIC moyen 5 ans",
    "net_margin_stable_or_expanding": "Marge nette stable ou en expansion",
    "eps_growth_5y": "Croissance EPS 5 ans",
    "moat_clear": "Moat / avantage compétitif",
    "eps_growth_estimated_3_5y": "Croissance EPS estimée 3-5 ans",
    "sector_cagr_estimated": "Croissance estimée du secteur",
    "forward_pe_manual": "Forward P/E",
    "peg_manual": "PEG",
    "fair_value": "Juste valeur",
    "valuation_vs_5y_avg_ok": "Valorisation vs moyenne 5 ans",
    "forward_pe_growth_acceptable": "P/E acceptable selon la croissance",
    "management_quality_good": "Qualité du management",
    "balance_sheet_strong": "Solidité du bilan",
    "margin_or_profitability_under_pressure": "Marge ou rentabilité sous pression",
    "regulatory_risk_high": "Risque réglementaire",
    "geopolitical_risk_high": "Risque géopolitique",
    "single_product_dependency_high": "Dépendance à un produit",
}

FIELD_WEIGHTS = {
    "fair_value": 42,
    "eps_growth_estimated_3_5y": 40,
    "roic_5y_avg": 38,
    "moat_clear": 36,
    "peg_manual": 34,
    "forward_pe_manual": 32,
    "valuation_vs_5y_avg_ok": 30,
    "net_margin_stable_or_expanding": 26,
    "eps_growth_5y": 26,
    "sector_cagr_estimated": 24,
    "balance_sheet_strong": 22,
    "management_quality_good": 20,
    "forward_pe_growth_acceptable": 20,
    "margin_or_profitability_under_pressure": 20,
    "regulatory_risk_high": 14,
    "geopolitical_risk_high": 14,
    "single_product_dependency_high": 14,
}


def build_validation_priority_rows(
    analysis_groups_by_universe: dict[str, dict[str, dict[str, Any]]],
    existing_reports: dict[str, dict[str, Any]] | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Rank missing or estimated fields by their likely impact on decisions."""

    existing_reports = existing_reports or {}
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for universe, analyses in analysis_groups_by_universe.items():
        for raw_ticker, analysis in sorted(analyses.items()):
            ticker = normalize_ticker(raw_ticker or analysis.get("ticker"))
            if not ticker or ticker == "VFV.TO" or is_etf_asset_analysis(analysis):
                continue
            fields = _candidate_fields(analysis)
            for field, source in fields:
                key = (ticker, field)
                if key in seen:
                    continue
                seen.add(key)
                score, reason_parts = _priority_score(field, source, universe, analysis)
                if score < 35:
                    continue
                priority = _priority_label(score)
                has_report = research_report_has_usable_fields(existing_reports.get(ticker))
                rows.append(
                    {
                        "priority_rank": 0,
                        "priority": priority,
                        "ticker": analysis.get("ticker_display") or ticker,
                        "universe": universe,
                        "company_name": analysis.get("company_name") or analysis.get("company_name_found") or "",
                        "field": field,
                        "field_label": FIELD_LABELS.get(field, field),
                        "priority_score": round(score, 2),
                        "reason": "; ".join(reason_parts),
                        "decision_impact": _decision_impact(field, analysis),
                        "suggested_action": _suggested_action(field, source, analysis, has_report),
                        "bncd_report_needed": _bncd_needed(field, source, analysis, has_report),
                    }
                )

    rows.sort(key=lambda row: (-(safe_float(row.get("priority_score")) or 0.0), str(row.get("ticker")), str(row.get("field"))))
    for index, row in enumerate(rows, start=1):
        row["priority_rank"] = index
    return rows[:limit] if limit else rows


def write_validation_priority_csv(path: str, rows: list[dict[str, Any]]) -> None:
    output = rows or [
        {
            "priority_rank": "",
            "priority": "AUCUNE_PRIORITE_MAJEURE",
            "ticker": "",
            "universe": "",
            "company_name": "",
            "field": "",
            "field_label": "",
            "priority_score": "",
            "reason": "Aucune donnée manquante ou estimation automatique ne semble pouvoir changer fortement la décision.",
            "decision_impact": "",
            "suggested_action": "Ne rien chercher en priorité pour l’instant.",
            "bncd_report_needed": False,
        }
    ]
    write_csv_records(path, output, VALIDATION_PRIORITY_COLUMNS)


def validation_priority_rows_for_report(rows: list[dict[str, Any]], limit: int = 12) -> list[dict[str, Any]]:
    if not rows:
        return [
            {
                "priority_rank": "",
                "priority": "AUCUNE_PRIORITE_MAJEURE",
                "ticker": "",
                "field_label": "",
                "decision_impact": "Aucune donnée à valider en priorité.",
                "suggested_action": "Ne rien chercher en priorité pour l’instant.",
                "bncd_report_needed": False,
            }
        ]
    return rows[:limit]


def _candidate_fields(analysis: dict[str, Any]) -> list[tuple[str, str]]:
    fields: list[tuple[str, str]] = []
    for field in analysis.get("manual_required_criteria") or []:
        normalized = str(field).strip()
        if normalized:
            fields.append((normalized, "MISSING"))
    for field in analysis.get("auto_estimated_fields") or []:
        normalized = str(field).strip()
        if normalized in RESEARCH_HELPFUL_FIELDS:
            fields.append((normalized, "AUTO_ESTIMATE"))
    if analysis.get("score_evidence_level") in {"ESTIMATE_HEAVY", "INSUFFICIENT_CONFIRMED"}:
        for field in _estimated_score_fields(analysis):
            fields.append((field, "SCORE_PROOF"))
    return fields


def _estimated_score_fields(analysis: dict[str, Any]) -> list[str]:
    estimated = set(analysis.get("auto_estimated_fields") or [])
    preferred = [
        "fair_value",
        "eps_growth_estimated_3_5y",
        "roic_5y_avg",
        "moat_clear",
        "peg_manual",
        "forward_pe_manual",
        "valuation_vs_5y_avg_ok",
    ]
    return [field for field in preferred if field in estimated]


def _priority_score(field: str, source: str, universe: str, analysis: dict[str, Any]) -> tuple[float, list[str]]:
    score = float(FIELD_WEIGHTS.get(field, 10))
    reasons = [f"donnée {source.lower()}"]
    universe_upper = universe.upper()
    if universe_upper == "CORE_PORTFOLIO":
        score += 22
        reasons.append("position core")
    elif universe_upper == "WATCHLIST":
        score += 8
        reasons.append("watchlist")
    elif universe_upper == "MARKET_SCANNER":
        score += 6
        reasons.append("market universe")

    allocation_decision = str(analysis.get("allocation_decision") or "")
    final_action = str(analysis.get("final_position_action") or "")
    cap_score = safe_float(analysis.get("capital_allocation_score")) or 0.0
    if allocation_decision in {"BUY / ADD", "ADD_WITH_MONITORING"} or final_action in {"BUY / ADD", "ADD_WITH_MONITORING"}:
        score += 28
        reasons.append("influence une allocation actuelle")
    elif allocation_decision == "ELIGIBLE_BUT_NOT_SELECTED" or cap_score >= 55:
        score += 14
        reasons.append("peut changer une future cotisation")
    elif str(analysis.get("promotion_status") or "") == "PROMOTE_TO_CORE_REVIEW":
        score += 12
        reasons.append("peut influencer une promotion externe")

    evidence = str(analysis.get("score_evidence_level") or "")
    if evidence in {"ESTIMATE_HEAVY", "INSUFFICIENT_CONFIRMED"}:
        score += 16
        reasons.append("score très dépendant d’estimations")
    elif evidence == "AUTOMATED_STRONG":
        score += 5
        reasons.append("score surtout automatisé")

    dependency = str(analysis.get("auto_estimate_dependency") or "")
    if dependency == "HIGH":
        score += 10
        reasons.append("forte dépendance aux proxys")
    elif dependency == "MEDIUM":
        score += 5
        reasons.append("dépendance moyenne aux proxys")

    if source == "MISSING":
        score += 8
    elif source == "SCORE_PROOF":
        score += 5

    if analysis.get("ticker_validation_status") in {"NO_MARKET_DATA", "POSSIBLE_WRONG_TICKER"}:
        score += 18
        reasons.append("ticker à corriger avant interprétation")
    if analysis.get("thesis_status") not in {"INTACT", ""} and universe_upper != "CORE_PORTFOLIO":
        score -= 12
        reasons.append("moins urgent car thèse non intacte")
    return max(0.0, score), reasons


def _priority_label(score: float) -> str:
    if score >= 90:
        return "TRES_HAUTE"
    if score >= 70:
        return "HAUTE"
    if score >= 50:
        return "MOYENNE"
    return "FAIBLE"


def _decision_impact(field: str, analysis: dict[str, Any]) -> str:
    if field in {"fair_value", "peg_manual", "forward_pe_manual", "valuation_vs_5y_avg_ok"}:
        return "Peut changer le statut de valorisation, le score d’allocation et la part VFV."
    if field in {"eps_growth_estimated_3_5y", "roic_5y_avg", "moat_clear"}:
        return "Peut changer la qualité fondamentale, la thèse, la conviction et l’admissibilité à l’achat."
    if field in {"margin_or_profitability_under_pressure", "balance_sheet_strong"}:
        return "Peut changer les signaux de surveillance ou de vente."
    if analysis.get("allocation_decision") in {"BUY / ADD", "ADD_WITH_MONITORING"}:
        return "Peut modifier une allocation recommandée actuellement."
    return "Peut améliorer la confiance, mais impact probablement moins direct."


def _suggested_action(field: str, source: str, analysis: dict[str, Any], has_report: bool) -> str:
    if analysis.get("ticker_validation_status") in {"NO_MARKET_DATA", "POSSIBLE_WRONG_TICKER"}:
        return "Corriger ou confirmer le ticker Yahoo Finance avant de chercher d’autres données."
    if has_report:
        return "Un rapport local existe déjà; compléter manuellement seulement si cette donnée reste absente."
    if _bncd_needed(field, source, analysis, has_report):
        return "Chercher un rapport BNCD/Morningstar ou confirmer cette donnée avec une source gratuite fiable."
    return "Valider seulement si le titre devient une allocation importante."


def _bncd_needed(field: str, source: str, analysis: dict[str, Any], has_report: bool) -> bool:
    if has_report:
        return False
    if field not in RESEARCH_HELPFUL_FIELDS:
        return False
    if analysis.get("ticker_validation_status") in {"NO_MARKET_DATA", "POSSIBLE_WRONG_TICKER"}:
        return False
    if source == "MISSING":
        return True
    current_allocation = analysis.get("allocation_decision") in {"BUY / ADD", "ADD_WITH_MONITORING"} or analysis.get(
        "final_position_action"
    ) in {"BUY / ADD", "ADD_WITH_MONITORING"}
    if current_allocation and field in {"fair_value", "eps_growth_estimated_3_5y", "roic_5y_avg", "moat_clear"}:
        return True
    if analysis.get("requires_manual_validation_for_large_allocation") is True:
        return True
    priority_dependency = str(analysis.get("auto_estimate_dependency") or "")
    return priority_dependency == "HIGH" and field in {"fair_value", "eps_growth_estimated_3_5y", "roic_5y_avg", "moat_clear"}
