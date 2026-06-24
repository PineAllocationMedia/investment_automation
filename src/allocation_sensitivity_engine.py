from __future__ import annotations

from copy import deepcopy
from typing import Any

from .allocation_engine import allocate_capital
from .utils import clamp, safe_float, write_csv_records


SENSITIVITY_SCENARIOS = {
    "PRUDENT_LONG_TERME": "Hypothèses un peu plus prudentes sur valorisation, cycle, thème chaud et durabilité.",
    "DONNEES_PLUS_STRICTES": "Hypothèses plus strictes quand le score dépend fortement d’estimations automatiques.",
}

ALLOCATION_SENSITIVITY_COLUMNS = [
    "ticker",
    "base_amount",
    "prudent_amount",
    "strict_data_amount",
    "min_amount",
    "max_amount",
    "max_change_amount",
    "max_change_percent",
    "robustness_note",
]

ALLOCATION_SENSITIVITY_SUMMARY_COLUMNS = [
    "robustness_status",
    "robustness_score",
    "top_pick_status",
    "base_top_pick",
    "prudent_top_pick",
    "strict_data_top_pick",
    "vfv_base_percent",
    "vfv_prudent_percent",
    "vfv_strict_data_percent",
    "largest_sensitive_ticker",
    "largest_change_amount",
    "largest_change_percent",
    "summary",
    "interpretation",
]


def compute_allocation_sensitivity(
    capital: float,
    mode: str,
    analyses: dict[str, dict[str, Any]],
    base_allocation_result: dict[str, Any],
) -> dict[str, Any]:
    """Run a small robustness check around the final allocation.

    This is intentionally moderate and explanatory. It does not replace the
    main allocation. It only answers: would the recommendation still look
    reasonable if the uncertain inputs were a bit less favorable?
    """

    capital = safe_float(capital) or 0.0
    base_amounts = _allocation_amounts(base_allocation_result.get("allocations", []))
    if capital <= 0:
        return _empty_result("Capital analysé à 0 $: aucune sensibilité d’allocation à tester.")

    scenario_results: dict[str, dict[str, Any]] = {}
    scenario_amounts: dict[str, dict[str, float]] = {}
    for scenario in SENSITIVITY_SCENARIOS:
        scenario_analyses = _scenario_analyses(analyses, scenario)
        result = allocate_capital(capital, scenario_analyses, mode)
        scenario_results[scenario] = result
        scenario_amounts[scenario] = _allocation_amounts(result.get("allocations", []))

    rows = _build_rows(capital, base_amounts, scenario_amounts)
    summary = _build_summary(capital, base_amounts, scenario_amounts, rows)
    return {
        "summary": summary,
        "rows": rows,
        "scenario_results": scenario_results,
    }


def write_allocation_sensitivity_csv(path: str, rows: list[dict[str, Any]]) -> None:
    output = rows or [
        {
            "ticker": "",
            "base_amount": "",
            "prudent_amount": "",
            "strict_data_amount": "",
            "min_amount": "",
            "max_amount": "",
            "max_change_amount": "",
            "max_change_percent": "",
            "robustness_note": "Aucune sensibilité disponible.",
        }
    ]
    write_csv_records(path, output, ALLOCATION_SENSITIVITY_COLUMNS)


def write_allocation_sensitivity_summary_csv(path: str, summary: dict[str, Any]) -> None:
    write_csv_records(path, [summary or _empty_summary("Aucune sensibilité disponible.")], ALLOCATION_SENSITIVITY_SUMMARY_COLUMNS)


def sensitivity_penalty(sensitivity: dict[str, Any] | None) -> tuple[float, str, list[str]]:
    if not sensitivity:
        return 0.0, "NOT_AVAILABLE", ["Analyse de sensibilité non disponible."]
    summary = sensitivity.get("summary") or {}
    status = str(summary.get("robustness_status") or "NOT_AVAILABLE")
    if status == "HIGHLY_SENSITIVE":
        return 8.0, status, [str(summary.get("summary") or "Allocation sensible aux hypothèses prudentes.")]
    if status == "MODERATELY_SENSITIVE":
        return 3.0, status, [str(summary.get("summary") or "Allocation modérément sensible aux hypothèses prudentes.")]
    if status == "ROBUST":
        return 0.0, status, [str(summary.get("summary") or "Allocation robuste dans les tests prudents.")]
    return 0.0, status, [str(summary.get("summary") or "Sensibilité non concluante.")]


def sensitivity_summary_rows_for_report(sensitivity: dict[str, Any] | None) -> list[dict[str, Any]]:
    summary = (sensitivity or {}).get("summary") or _empty_summary("Aucune sensibilité disponible.")
    return [dict(summary)]


def sensitivity_rows_for_report(sensitivity: dict[str, Any] | None, limit: int = 8) -> list[dict[str, Any]]:
    rows = list((sensitivity or {}).get("rows") or [])
    rows.sort(key=lambda row: safe_float(row.get("max_change_amount")) or 0.0, reverse=True)
    return rows[:limit]


def _scenario_analyses(analyses: dict[str, dict[str, Any]], scenario: str) -> dict[str, dict[str, Any]]:
    scenario_rows = deepcopy(analyses)
    strength = 0.45 if scenario == "PRUDENT_LONG_TERME" else 0.65
    for ticker, row in scenario_rows.items():
        if ticker == "VFV.TO" or row.get("benchmark_role") is True:
            continue
        adjustment = _scenario_penalty(row, strength)
        score = safe_float(row.get("capital_allocation_score")) or 0.0
        conviction = safe_float(row.get("conviction_score")) or 0.0
        row["capital_allocation_score"] = round(clamp(score - adjustment, 0.0, 100.0), 4)
        row["conviction_score"] = round(clamp(conviction - adjustment * 0.25, 0.0, 100.0), 4)
        row["sensitivity_adjustment"] = round(-adjustment, 4)
        row["sensitivity_scenario"] = scenario
    return scenario_rows


def _scenario_penalty(row: dict[str, Any], strength: float) -> float:
    penalty = 0.0
    cycle = str(row.get("cycle_bubble_risk_level") or "")
    durability = str(row.get("long_term_durability_status") or "")
    evidence = str(row.get("score_evidence_level") or "")
    reliability = str(row.get("data_reliability_level") or "")
    monitoring = str(row.get("monitoring_status") or "")
    valuation_watch = str(row.get("valuation_watch_status") or "")

    if row.get("quality_but_too_expensive") is True:
        penalty += 10.0
    if cycle == "EXTREME":
        penalty += 14.0
    elif cycle == "HIGH":
        penalty += 8.0
    elif cycle == "MEDIUM":
        penalty += 3.0
    if durability == "HIGH_GROWTH_BUT_FRAGILE":
        penalty += 7.0
    elif durability == "DURABLE_BUT_CYCLICAL":
        penalty += 4.0
    elif durability == "SPECULATIVE_OR_UNPROVEN":
        penalty += 18.0
    if evidence == "INSUFFICIENT_CONFIRMED":
        penalty += 12.0
    elif evidence == "ESTIMATE_HEAVY":
        penalty += 8.0
    elif evidence == "AUTOMATED_STRONG":
        penalty += 2.5
    if reliability == "LOW":
        penalty += 15.0
    elif reliability == "MEDIUM":
        penalty += 5.0
    if monitoring in {"WATCH", "MANUAL_REVIEW"}:
        penalty += 5.0
    if valuation_watch in {"WATCH", "EXPENSIVE", "EXTREME"}:
        penalty += 5.0
    if row.get("requires_manual_validation_for_large_allocation") is True:
        penalty += 5.0
    return min(18.0, penalty * strength)


def _allocation_amounts(allocations: list[dict[str, Any]]) -> dict[str, float]:
    amounts: dict[str, float] = {}
    for row in allocations:
        ticker = str(row.get("destination", row.get("ticker")) or "")
        amount = safe_float(row.get("montant", row.get("amount"))) or 0.0
        if not ticker:
            continue
        amounts[ticker] = round(amounts.get(ticker, 0.0) + amount, 2)
    return amounts


def _build_rows(
    capital: float,
    base_amounts: dict[str, float],
    scenario_amounts: dict[str, dict[str, float]],
) -> list[dict[str, Any]]:
    tickers = set(base_amounts)
    for amounts in scenario_amounts.values():
        tickers.update(amounts)
    rows = []
    for ticker in sorted(tickers):
        base = base_amounts.get(ticker, 0.0)
        prudent = scenario_amounts.get("PRUDENT_LONG_TERME", {}).get(ticker, 0.0)
        strict = scenario_amounts.get("DONNEES_PLUS_STRICTES", {}).get(ticker, 0.0)
        values = [base, prudent, strict]
        max_change = max(abs(prudent - base), abs(strict - base))
        max_change_pct = max_change / capital if capital > 0 else 0.0
        rows.append(
            {
                "ticker": ticker,
                "base_amount": round(base, 2),
                "prudent_amount": round(prudent, 2),
                "strict_data_amount": round(strict, 2),
                "min_amount": round(min(values), 2),
                "max_amount": round(max(values), 2),
                "max_change_amount": round(max_change, 2),
                "max_change_percent": round(max_change_pct, 4),
                "robustness_note": _row_note(max_change_pct),
            }
        )
    return rows


def _build_summary(
    capital: float,
    base_amounts: dict[str, float],
    scenario_amounts: dict[str, dict[str, float]],
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    top_base = _top_non_vfv(base_amounts)
    top_prudent = _top_non_vfv(scenario_amounts.get("PRUDENT_LONG_TERME", {}))
    top_strict = _top_non_vfv(scenario_amounts.get("DONNEES_PLUS_STRICTES", {}))
    top_flips = sum(1 for top in [top_prudent, top_strict] if top and top_base and top != top_base)
    worst_reallocation = max((_reallocation_percent(capital, base_amounts, amounts) for amounts in scenario_amounts.values()), default=0.0)
    vfv_values = [
        base_amounts.get("VFV.TO", 0.0) / capital if capital > 0 else 0.0,
        scenario_amounts.get("PRUDENT_LONG_TERME", {}).get("VFV.TO", 0.0) / capital if capital > 0 else 0.0,
        scenario_amounts.get("DONNEES_PLUS_STRICTES", {}).get("VFV.TO", 0.0) / capital if capital > 0 else 0.0,
    ]
    vfv_range = max(vfv_values) - min(vfv_values)
    largest = max(rows, key=lambda row: safe_float(row.get("max_change_amount")) or 0.0, default={})
    score = round(clamp(100.0 - worst_reallocation * 90.0 - vfv_range * 40.0 - top_flips * 6.0, 0.0, 100.0), 2)
    status = "ROBUST" if score >= 80 else "MODERATELY_SENSITIVE" if score >= 65 else "HIGHLY_SENSITIVE"
    return {
        "robustness_status": status,
        "robustness_score": score,
        "top_pick_status": "STABLE" if top_flips == 0 else "CHANGE_UNDER_STRESS",
        "base_top_pick": top_base or "",
        "prudent_top_pick": top_prudent or "",
        "strict_data_top_pick": top_strict or "",
        "vfv_base_percent": round(vfv_values[0], 4),
        "vfv_prudent_percent": round(vfv_values[1], 4),
        "vfv_strict_data_percent": round(vfv_values[2], 4),
        "largest_sensitive_ticker": largest.get("ticker", ""),
        "largest_change_amount": largest.get("max_change_amount", 0.0),
        "largest_change_percent": largest.get("max_change_percent", 0.0),
        "summary": _summary_text(status, top_flips, worst_reallocation, vfv_range),
        "interpretation": (
            "La recommandation principale reste celle de l’allocation de cotisation. "
            "Cette couche sert seulement à signaler si elle dépend trop d’hypothèses optimistes."
        ),
    }


def _reallocation_percent(capital: float, base: dict[str, float], scenario: dict[str, float]) -> float:
    if capital <= 0:
        return 0.0
    tickers = set(base) | set(scenario)
    moved = sum(abs(base.get(ticker, 0.0) - scenario.get(ticker, 0.0)) for ticker in tickers) / 2.0
    return moved / capital


def _top_non_vfv(amounts: dict[str, float]) -> str:
    rows = [(amount, ticker) for ticker, amount in amounts.items() if ticker != "VFV.TO" and amount > 0]
    if not rows:
        return ""
    amount, ticker = max(rows)
    return ticker


def _row_note(max_change_pct: float) -> str:
    if max_change_pct <= 0.08:
        return "Stable dans les tests prudents."
    if max_change_pct <= 0.18:
        return "Sensible mais encore raisonnable; surveiller les données clés."
    return "Très sensible; valider les hypothèses avant une grosse cotisation."


def _summary_text(status: str, top_flips: int, worst_reallocation: float, vfv_range: float) -> str:
    if status == "ROBUST":
        return "L’allocation reste assez stable sous hypothèses prudentes."
    if status == "MODERATELY_SENSITIVE":
        return (
            f"L’allocation bouge modérément sous hypothèses prudentes "
            f"(réallocation max {worst_reallocation:.0%}, variation VFV {vfv_range:.0%})."
        )
    flip_text = " et le meilleur choix change" if top_flips else ""
    return (
        f"L’allocation est sensible aux hypothèses prudentes{flip_text}; "
        "valider les données prioritaires avant d’augmenter fortement la cotisation."
    )


def _empty_result(message: str) -> dict[str, Any]:
    return {"summary": _empty_summary(message), "rows": [], "scenario_results": {}}


def _empty_summary(message: str) -> dict[str, Any]:
    return {
        "robustness_status": "NOT_AVAILABLE",
        "robustness_score": "",
        "top_pick_status": "",
        "base_top_pick": "",
        "prudent_top_pick": "",
        "strict_data_top_pick": "",
        "vfv_base_percent": "",
        "vfv_prudent_percent": "",
        "vfv_strict_data_percent": "",
        "largest_sensitive_ticker": "",
        "largest_change_amount": "",
        "largest_change_percent": "",
        "summary": message,
        "interpretation": "Aucune conclusion de robustesse à tirer.",
    }
