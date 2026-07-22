from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from .allocation_engine import allocate_capital
from .utils import read_csv_records, safe_float, write_csv_records


ALLOCATION_MODE_ORDER = ["balanced", "family-office", "rational-aggressive", "high-cagr"]

ALLOCATION_MODE_CONTRACT_COLUMNS = [
    "row_type",
    "mode",
    "status",
    "capital",
    "total_allocated",
    "max_single_allocation_pct",
    "fallback_allocation_pct",
    "defensive_reserve_pct",
    "ticker_count",
    "external_allocation_pct",
    "emerging_fragile_allocation_pct",
    "defensiveness_score",
    "expected_order_check",
    "interpretation",
    "audit_only",
]

EXTERNAL_UNIVERSES = {"WATCHLIST", "MARKET_SCANNER", "DISCOVERY_IDEAS"}


def build_allocation_mode_contract_audit(
    capital: float,
    analyses: dict[str, dict[str, Any]],
    *,
    defensive_etf_candidates_by_mode: dict[str, list[dict[str, Any]]] | None = None,
) -> list[dict[str, Any]]:
    """Run an audit-only comparison of allocation behavior across modes."""
    capital_float = safe_float(capital) or 0.0
    if capital_float <= 0:
        return [_neutral_row("NO_CAPITAL", "Capital d'audit nul ou invalide.")]
    if not analyses:
        return [_neutral_row("NO_ANALYSES", "Aucune analyse disponible pour comparer les contrats de modes.")]

    defensive_etf_candidates_by_mode = defensive_etf_candidates_by_mode or {}
    mode_rows: list[dict[str, Any]] = []
    summaries: dict[str, dict[str, Any]] = {}

    for mode in ALLOCATION_MODE_ORDER:
        mode_analyses = _deepcopy_analyses(analyses)
        defensive_candidates = _deepcopy_rows(defensive_etf_candidates_by_mode.get(mode, []))
        result = allocate_capital(
            capital_float,
            mode_analyses,
            mode,
            defensive_etf_candidates=defensive_candidates,
        )
        summary = _summarize_mode(mode, capital_float, result.get("allocations") or [], mode_analyses)
        summaries[mode] = summary
        mode_rows.append(_mode_row(summary))

    return [
        *mode_rows,
        _concentration_order_row(summaries),
        _defensiveness_order_row(summaries),
        _defensive_reserve_pattern_row(summaries),
        _high_cagr_safety_row(summaries),
        _emerging_satellite_row(summaries),
    ]


def build_allocation_mode_contract_audit_from_reports(
    reports_dir: str | Path,
    capital: float,
) -> list[dict[str, Any]]:
    reports_dir = Path(reports_dir)
    analyses = _load_analyses_from_scores(reports_dir / "latest_scores.csv")
    defensive_candidates = _load_defensive_candidates_by_mode(reports_dir / "latest_defensive_etf_fallback.csv")
    return build_allocation_mode_contract_audit(
        capital,
        analyses,
        defensive_etf_candidates_by_mode=defensive_candidates,
    )


def write_allocation_mode_contract_audit_csv(path: str | Path, rows: list[dict[str, Any]]) -> None:
    write_csv_records(path, rows, ALLOCATION_MODE_CONTRACT_COLUMNS)


def _summarize_mode(
    mode: str,
    capital: float,
    allocations: list[dict[str, Any]],
    analyses: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    total_allocated = round(sum(safe_float(row.get("montant")) or 0.0 for row in allocations), 2)
    max_single = 0.0
    fallback_total = 0.0
    defensive_total = 0.0
    external_total = 0.0
    emerging_fragile_total = 0.0
    funded_tickers: set[str] = set()

    for row in allocations:
        ticker = str(row.get("destination") or "").strip().upper()
        amount = safe_float(row.get("montant")) or 0.0
        if not ticker or amount <= 0:
            continue
        funded_tickers.add(ticker)
        analysis = analyses.get(ticker, {})
        is_fallback = _is_fallback_allocation(ticker, row, analysis)
        if not is_fallback:
            max_single = max(max_single, amount / capital if capital > 0 else 0.0)
        if is_fallback:
            fallback_total += amount
        if _is_defensive_reserve(row, analysis):
            defensive_total += amount
        if _is_external_candidate(analysis):
            external_total += amount
            if str(analysis.get("long_term_durability_status") or "") == "HIGH_GROWTH_BUT_FRAGILE":
                emerging_fragile_total += amount

    fallback_pct = fallback_total / capital if capital > 0 else 0.0
    defensive_pct = defensive_total / capital if capital > 0 else 0.0
    external_pct = external_total / capital if capital > 0 else 0.0
    emerging_pct = emerging_fragile_total / capital if capital > 0 else 0.0
    defensiveness_score = _defensiveness_score(
        fallback_pct=fallback_pct,
        defensive_pct=defensive_pct,
        max_single_pct=max_single,
        external_pct=external_pct,
        emerging_fragile_pct=emerging_pct,
    )
    return {
        "mode": mode,
        "capital": round(capital, 2),
        "total_allocated": total_allocated,
        "max_single_allocation_pct": round(max_single, 4),
        "fallback_allocation_pct": round(fallback_pct, 4),
        "defensive_reserve_pct": round(defensive_pct, 4),
        "ticker_count": len(funded_tickers),
        "external_allocation_pct": round(external_pct, 4),
        "emerging_fragile_allocation_pct": round(emerging_pct, 4),
        "defensiveness_score": round(defensiveness_score, 4),
    }


def _mode_row(summary: dict[str, Any]) -> dict[str, Any]:
    mode = str(summary.get("mode") or "")
    return {
        "row_type": "MODE_SUMMARY",
        "mode": mode,
        "status": "INFO",
        "capital": summary.get("capital", ""),
        "total_allocated": summary.get("total_allocated", ""),
        "max_single_allocation_pct": summary.get("max_single_allocation_pct", ""),
        "fallback_allocation_pct": summary.get("fallback_allocation_pct", ""),
        "defensive_reserve_pct": summary.get("defensive_reserve_pct", ""),
        "ticker_count": summary.get("ticker_count", ""),
        "external_allocation_pct": summary.get("external_allocation_pct", ""),
        "emerging_fragile_allocation_pct": summary.get("emerging_fragile_allocation_pct", ""),
        "defensiveness_score": summary.get("defensiveness_score", ""),
        "expected_order_check": "",
        "interpretation": _mode_interpretation(summary),
        "audit_only": "TRUE",
    }


def _concentration_order_row(summaries: dict[str, dict[str, Any]]) -> dict[str, Any]:
    values = [safe_float(summaries.get(mode, {}).get("max_single_allocation_pct")) or 0.0 for mode in ALLOCATION_MODE_ORDER]
    ok = _non_decreasing(values, tolerance=0.035)
    return _check_row(
        "CONCENTRATION_ORDER",
        "PASS" if ok else "REVIEW",
        "balanced <= family-office <= rational-aggressive <= high-cagr",
        (
            "L'ordre de concentration respecte le contrat des modes."
            if ok
            else "À vérifier: un mode plus prudent semble aussi concentré ou plus concentré qu'un mode plus offensif."
        ),
    )


def _defensiveness_order_row(summaries: dict[str, dict[str, Any]]) -> dict[str, Any]:
    values = [safe_float(summaries.get(mode, {}).get("defensiveness_score")) or 0.0 for mode in ALLOCATION_MODE_ORDER]
    ok = _non_increasing(values, tolerance=0.035)
    return _check_row(
        "DEFENSIVENESS_ORDER",
        "PASS" if ok else "REVIEW",
        "balanced >= family-office >= rational-aggressive >= high-cagr",
        (
            "L'ordre de défensivité respecte le contrat des modes."
            if ok
            else "À vérifier: un mode offensif semble plus défensif qu'un mode prudent, ou inversement."
        ),
    )


def _defensive_reserve_pattern_row(summaries: dict[str, dict[str, Any]]) -> dict[str, Any]:
    fallback_values = [
        safe_float(summaries.get(mode, {}).get("fallback_allocation_pct")) or 0.0
        for mode in ALLOCATION_MODE_ORDER
    ]
    high_defensive_reserve = safe_float(summaries.get("high-cagr", {}).get("defensive_reserve_pct")) or 0.0
    ok = _non_increasing(fallback_values, tolerance=0.05) and high_defensive_reserve <= 0.001
    return _check_row(
        "DEFENSIVE_RESERVE_PATTERN",
        "PASS" if ok else "REVIEW",
        "balanced/family/rational plus défensifs que high-cagr; high-cagr sans réserve défensive ETF",
        (
            "La réserve défensive/fallback respecte l'esprit des modes; high-cagr garde seulement son filet de sécurité."
            if ok
            else "À vérifier: la réserve défensive/fallback ne suit pas clairement l'ordre attendu des modes."
        ),
    )


def _high_cagr_safety_row(summaries: dict[str, dict[str, Any]]) -> dict[str, Any]:
    high = summaries.get("high-cagr", {})
    fallback_pct = safe_float(high.get("fallback_allocation_pct")) or 0.0
    ok = fallback_pct >= 0.049
    return _check_row(
        "HIGH_CAGR_SAFETY_NET",
        "PASS" if ok else "REVIEW",
        "high-cagr conserve un filet VFV/fallback minimal",
        (
            "Le filet de sécurité high-cagr est présent."
            if ok
            else "À vérifier: high-cagr ne montre pas de filet VFV/fallback dans cette simulation d'audit."
        ),
    )


def _emerging_satellite_row(summaries: dict[str, dict[str, Any]]) -> dict[str, Any]:
    high = summaries.get("high-cagr", {})
    emerging_pct = safe_float(high.get("emerging_fragile_allocation_pct")) or 0.0
    ok = emerging_pct <= 0.2255
    return _check_row(
        "EMERGING_SATELLITE_CAP",
        "PASS" if ok else "REVIEW",
        "satellites HIGH_GROWTH_BUT_FRAGILE <= 22.5% par run",
        (
            "Les satellites émergents restent dans le budget par run."
            if ok
            else "À vérifier: les satellites émergents dépassent le budget high-cagr prévu."
        ),
    )


def _check_row(row_type: str, status: str, expected_order_check: str, interpretation: str) -> dict[str, Any]:
    return {
        "row_type": row_type,
        "mode": "ALL",
        "status": status,
        "capital": "",
        "total_allocated": "",
        "max_single_allocation_pct": "",
        "fallback_allocation_pct": "",
        "defensive_reserve_pct": "",
        "ticker_count": "",
        "external_allocation_pct": "",
        "emerging_fragile_allocation_pct": "",
        "defensiveness_score": "",
        "expected_order_check": expected_order_check,
        "interpretation": interpretation,
        "audit_only": "TRUE",
    }


def _neutral_row(status: str, interpretation: str) -> dict[str, Any]:
    row = _check_row("NO_DATA", status, "", interpretation)
    row["mode"] = "ALL"
    return row


def _mode_interpretation(summary: dict[str, Any]) -> str:
    mode = str(summary.get("mode") or "")
    return (
        f"{mode}: plus gros bloc offensif {summary.get('max_single_allocation_pct')}, "
        f"fallback/ETF {summary.get('fallback_allocation_pct')}, "
        f"réserve défensive {summary.get('defensive_reserve_pct')}, "
        f"externes {summary.get('external_allocation_pct')}."
    )


def _defensiveness_score(
    *,
    fallback_pct: float,
    defensive_pct: float,
    max_single_pct: float,
    external_pct: float,
    emerging_fragile_pct: float,
) -> float:
    return (
        0.50 * fallback_pct
        + 0.35 * defensive_pct
        + 0.15 * max(0.0, 1.0 - max_single_pct)
        - 0.10 * external_pct
        - 0.15 * emerging_fragile_pct
    )


def _is_fallback_allocation(ticker: str, row: dict[str, Any], analysis: dict[str, Any]) -> bool:
    block = str(row.get("bloc") or "").upper()
    asset_type = str(analysis.get("asset_type") or "").upper()
    benchmark_role = str(analysis.get("benchmark_role") or "").upper()
    universe = str(analysis.get("universe") or "").upper()
    return (
        ticker in {"VFV.TO", "XUS.TO"}
        or "VFV" in block
        or "FALLBACK" in block
        or "BENCHMARK" in benchmark_role
        or "ETF" in asset_type
        or universe == "DEFENSIVE_ETF_FALLBACK"
    )


def _is_defensive_reserve(row: dict[str, Any], analysis: dict[str, Any]) -> bool:
    block = str(row.get("bloc") or "").upper()
    universe = str(analysis.get("universe") or "").upper()
    asset_type = str(analysis.get("asset_type") or "").upper()
    return "DEFENSIVE ETF" in block or universe == "DEFENSIVE_ETF_FALLBACK" or asset_type == "ETF_DEFENSIVE_FALLBACK"


def _is_external_candidate(analysis: dict[str, Any]) -> bool:
    return str(analysis.get("universe") or "").upper() in EXTERNAL_UNIVERSES


def _non_decreasing(values: list[float], *, tolerance: float) -> bool:
    return all(values[index] <= values[index + 1] + tolerance for index in range(len(values) - 1))


def _non_increasing(values: list[float], *, tolerance: float) -> bool:
    return all(values[index] + tolerance >= values[index + 1] for index in range(len(values) - 1))


def _load_analyses_from_scores(path: Path) -> dict[str, dict[str, Any]]:
    analyses: dict[str, dict[str, Any]] = {}
    for row in read_csv_records(path):
        normalized = _normalize_row(row)
        ticker = str(normalized.get("ticker") or "").strip().upper()
        if ticker:
            analyses[ticker] = normalized
    return analyses


def _load_defensive_candidates_by_mode(path: Path) -> dict[str, list[dict[str, Any]]]:
    output: dict[str, list[dict[str, Any]]] = {mode: [] for mode in ALLOCATION_MODE_ORDER}
    for row in read_csv_records(path):
        normalized = _normalize_row(row)
        mode = str(normalized.get("mode") or "").strip()
        if mode in output:
            output[mode].append(normalized)
    return output


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(row)
    for key, value in list(normalized.items()):
        if not isinstance(value, str):
            continue
        text = value.strip()
        lowered = text.lower()
        if lowered in {"true", "yes", "oui", "1"}:
            normalized[key] = True
        elif lowered in {"false", "no", "non", "0"}:
            normalized[key] = False
        else:
            normalized[key] = text
    return normalized


def _deepcopy_analyses(analyses: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {ticker: copy.deepcopy(row) for ticker, row in analyses.items()}


def _deepcopy_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [copy.deepcopy(row) for row in rows]
