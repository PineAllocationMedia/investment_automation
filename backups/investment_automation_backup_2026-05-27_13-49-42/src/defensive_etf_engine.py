from __future__ import annotations

from pathlib import Path
from typing import Any

from .utils import load_yaml, normalize_ticker, safe_float


DEFENSIVE_ETF_COLUMNS = [
    "ticker",
    "name",
    "source",
    "role",
    "category",
    "mode",
    "enabled_for_mode",
    "selected_for_allocation",
    "selector_status",
    "selector_rank",
    "selector_reason",
    "defensive_score",
    "current_price",
    "price_above_sma_200",
    "return_1y",
    "drawdown_from_12m_high",
    "status",
    "reason",
    "max_single_allocation_pct",
]

MODE_LIMITS = {
    "high-cagr": {"enabled": False, "max_total_pct": 0.0, "min_score": 1000},
    "rational-aggressive": {"enabled": True, "max_total_pct": 0.05, "min_score": 68},
    "family-office": {"enabled": True, "max_total_pct": 0.25, "min_score": 60},
    "balanced": {"enabled": True, "max_total_pct": 0.45, "min_score": 55},
}

SPECULATIVE_ETF_TERMS = {
    "LEVERAGED",
    "2X",
    "3X",
    "INVERSE",
    "DAILY BULL",
    "DAILY BEAR",
    "CALL OPTION",
    "COVERED CALL",
    "BITCOIN",
    "CRYPTO",
}

BASE_ROLE_SCORES = {
    "treasury_bill_cash_like": 78,
    "cash_like": 76,
    "short_term_canadian_bonds": 74,
    "broad_canadian_bonds": 70,
    "conservative_all_in_one": 68,
    "balanced_all_in_one": 64,
    "low_volatility_canada_equity": 63,
    "low_volatility_us_equity": 62,
    "broad_canada_equity": 58,
    "canadian_consumer_staples": 57,
}

BALANCED_ROLE_ADJUSTMENTS = {
    "treasury_bill_cash_like": -4,
    "cash_like": -6,
    "short_term_canadian_bonds": -2,
    "broad_canadian_bonds": -1,
    "conservative_all_in_one": 10,
    "balanced_all_in_one": 9,
    "low_volatility_canada_equity": 8,
    "low_volatility_us_equity": 7,
    "broad_canada_equity": 4,
    "canadian_consumer_staples": 5,
}


def load_defensive_etf_config(path: str | Path) -> dict[str, Any]:
    config = load_yaml(path)
    if not isinstance(config, dict):
        return {"defensive_etfs": [], "auto_universe": [], "selection_rules": {}}
    return {
        "defensive_etfs": _clean_rows(config.get("defensive_etfs", []), "CORE_ALLOWLIST"),
        "auto_universe": _clean_rows(config.get("auto_universe", []), "AUTO_SELECTOR_UNIVERSE"),
        "selection_rules": config.get("selection_rules", {}) if isinstance(config.get("selection_rules"), dict) else {},
    }


def defensive_fallback_enabled(mode: str) -> bool:
    return bool(MODE_LIMITS.get(str(mode or ""), {}).get("enabled"))


def defensive_mode_limit(mode: str) -> float:
    return safe_float(MODE_LIMITS.get(str(mode or ""), {}).get("max_total_pct")) or 0.0


def defensive_etf_tickers_for_mode(config: dict[str, Any], mode: str) -> list[str]:
    if not defensive_fallback_enabled(mode):
        return []
    tickers = []
    for row in _all_config_rows(config):
        if _is_allowed_for_mode(row, mode):
            tickers.append(normalize_ticker(row.get("ticker")))
    return sorted({ticker for ticker in tickers if ticker})


def build_defensive_etf_candidates(
    config: dict[str, Any],
    mode: str,
    market_data: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    enabled = defensive_fallback_enabled(mode)
    for item in _all_config_rows(config):
        ticker = normalize_ticker(item.get("ticker"))
        market = market_data.get(ticker, {})
        allowed = enabled and _is_allowed_for_mode(item, mode)
        row = {
            "ticker": ticker,
            "name": str(item.get("name") or ticker),
            "source": str(item.get("source") or ""),
            "role": str(item.get("role") or ""),
            "category": str(item.get("category") or ""),
            "mode": mode,
            "enabled_for_mode": allowed,
            "selected_for_allocation": False,
            "selector_status": "",
            "selector_rank": "",
            "selector_reason": "",
            "max_single_allocation_pct": _single_limit(item, mode),
            **_score_defensive_etf(item, market, mode, allowed),
        }
        rows.append(row)
    rows = _apply_auto_selection(rows, config, mode)
    rows.sort(
        key=lambda row: (
            bool(row.get("selected_for_allocation")),
            safe_float(row.get("defensive_score")) or 0.0,
        ),
        reverse=True,
    )
    return rows


def defensive_etf_analysis_map(candidates: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for row in candidates:
        if row.get("status") != "ELIGIBLE_DEFENSIVE_FALLBACK":
            continue
        ticker = normalize_ticker(row.get("ticker"))
        output[ticker] = {
            "ticker": ticker,
            "universe": "DEFENSIVE_ETF_FALLBACK",
            "asset_type": "ETF_DEFENSIVE_FALLBACK",
            "thesis_status": "ETF",
            "liquidation_status": "GREEN",
            "add_eligibility_status": "ADD_ALLOWED",
            "position_weight": 0.0,
            "data_reliability_level": "ETF",
            "defensive_score": row.get("defensive_score"),
            "capital_allocation_score": row.get("defensive_score"),
            "expected_cagr_quality": "DEFENSIVE_ETF",
            "opportunity_cost_status": "DEFENSIVE_FALLBACK",
            "allocation_decision": "DEFENSIVE_ETF_FALLBACK",
        }
    return output


def defensive_etf_rows_for_csv(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{column: row.get(column, "") for column in DEFENSIVE_ETF_COLUMNS} for row in candidates]


def defensive_fallback_summary(candidates: list[dict[str, Any]], mode: str) -> str:
    if not defensive_fallback_enabled(mode):
        return "Désactivé pour ce mode."
    selected = [row for row in candidates if row.get("selected_for_allocation") is True]
    if not selected:
        return "Activé, mais aucun ETF défensif admissible avec les données disponibles."
    top = selected[0]
    return f"Activé; sélection autonome: {top.get('ticker')} en tête ({len(selected)} ETF retenu(s))."


def _clean_rows(rows: Any, source: str) -> list[dict[str, Any]]:
    cleaned = []
    if not isinstance(rows, list):
        return cleaned
    for row in rows:
        if not isinstance(row, dict):
            continue
        ticker = normalize_ticker(row.get("ticker"))
        if not ticker:
            continue
        cleaned.append({**row, "ticker": ticker, "source": source})
    return cleaned


def _all_config_rows(config: dict[str, Any]) -> list[dict[str, Any]]:
    by_ticker: dict[str, dict[str, Any]] = {}
    for row in config.get("auto_universe", []):
        ticker = normalize_ticker(row.get("ticker"))
        if ticker:
            by_ticker[ticker] = dict(row)
    for row in config.get("defensive_etfs", []):
        ticker = normalize_ticker(row.get("ticker"))
        if ticker:
            by_ticker[ticker] = dict(row)
    return list(by_ticker.values())


def _apply_auto_selection(rows: list[dict[str, Any]], config: dict[str, Any], mode: str) -> list[dict[str, Any]]:
    if not defensive_fallback_enabled(mode):
        for row in rows:
            row["selected_for_allocation"] = False
            row["selector_status"] = "DISABLED_FOR_MODE"
            row["selector_reason"] = "Sélecteur automatique désactivé pour ce mode."
        return rows

    max_selected = _selection_limit(config, "max_selected_by_mode", mode, default={"balanced": 5, "family-office": 4, "rational-aggressive": 2}.get(mode, 0))
    max_per_category = _selection_limit(config, "max_per_category_by_mode", mode, default={"balanced": 2, "family-office": 1, "rational-aggressive": 1}.get(mode, 0))
    selected_count = 0
    category_counts: dict[str, int] = {}
    eligible = sorted(
        [row for row in rows if row.get("status") == "ELIGIBLE_DEFENSIVE_FALLBACK"],
        key=lambda row: safe_float(row.get("defensive_score")) or 0.0,
        reverse=True,
    )

    for index, row in enumerate(eligible, start=1):
        category = str(row.get("category") or "other")
        row["selector_rank"] = index
        if selected_count >= max_selected:
            row["selected_for_allocation"] = False
            row["selector_status"] = "RESERVE_MODE_LIMIT"
            row["selector_reason"] = "ETF admissible, mais non retenu car le mode a déjà assez d'ETF défensifs."
            continue
        if category_counts.get(category, 0) >= max_per_category:
            row["selected_for_allocation"] = False
            row["selector_status"] = "RESERVE_SAME_CATEGORY"
            row["selector_reason"] = "ETF admissible, mais un meilleur ETF de la même catégorie est déjà retenu."
            continue
        row["selected_for_allocation"] = True
        row["selector_status"] = "SELECTED_AUTO_FALLBACK"
        row["selector_reason"] = "Retenu automatiquement comme ETF défensif admissible pour ce mode."
        selected_count += 1
        category_counts[category] = category_counts.get(category, 0) + 1

    for row in rows:
        if row.get("selector_status"):
            continue
        if row.get("status") == "ELIGIBLE_DEFENSIVE_FALLBACK":
            row["selector_status"] = "RESERVE_NOT_SELECTED"
            row["selector_reason"] = "ETF admissible mais non retenu par le sélecteur automatique."
        else:
            row["selector_status"] = "NOT_ELIGIBLE"
            row["selector_reason"] = str(row.get("reason") or "ETF non admissible.")
    return rows


def _selection_limit(config: dict[str, Any], key: str, mode: str, default: int) -> int:
    rules = config.get("selection_rules") or {}
    values = rules.get(key) if isinstance(rules, dict) else {}
    if isinstance(values, dict):
        value = safe_float(values.get(mode))
        if value is not None:
            return max(0, int(value))
    return max(0, int(default))


def _score_defensive_etf(
    item: dict[str, Any],
    market: dict[str, Any],
    mode: str,
    allowed: bool,
) -> dict[str, Any]:
    ticker = normalize_ticker(item.get("ticker"))
    role = str(item.get("role") or "")
    name = str(market.get("long_name") or market.get("short_name") or item.get("name") or ticker)
    upper_name = name.upper()
    current_price = safe_float(market.get("current_price"))
    price_above_sma = market.get("price_above_sma_200")
    return_1y = safe_float(market.get("return_1y"))
    drawdown = safe_float(market.get("drawdown_from_12m_high"))

    if not allowed:
        return {
            "defensive_score": 0,
            "current_price": current_price,
            "price_above_sma_200": price_above_sma,
            "return_1y": return_1y,
            "drawdown_from_12m_high": drawdown,
            "status": "DISABLED_FOR_MODE",
            "reason": f"ETF défensif non autorisé en mode {mode}.",
        }
    if any(term in upper_name for term in SPECULATIVE_ETF_TERMS):
        return {
            "defensive_score": 0,
            "current_price": current_price,
            "price_above_sma_200": price_above_sma,
            "return_1y": return_1y,
            "drawdown_from_12m_high": drawdown,
            "status": "REJECTED_SPECULATIVE_ETF",
            "reason": "ETF rejeté: levier, inverse, crypto, options ou thématique spéculative détectée.",
        }
    if current_price is None or current_price <= 0:
        if mode in {"balanced", "family-office"}:
            score = max(0.0, _role_score(role, mode) - 8.0)
            minimum = safe_float(MODE_LIMITS.get(mode, {}).get("min_score")) or 1000.0
            status = "ELIGIBLE_DEFENSIVE_FALLBACK" if score >= minimum else "WATCH_ONLY"
            reason = (
                "Prix gratuit indisponible; ETF défensif pré-approuvé par configuration, "
                "utilisable comme stabilisateur limité à valider manuellement avant achat."
            )
            if status == "WATCH_ONLY":
                reason += " Score défensif insuffisant pour allocation automatique."
            return {
                "defensive_score": round(max(0.0, min(100.0, score)), 2),
                "current_price": current_price,
                "price_above_sma_200": price_above_sma,
                "return_1y": return_1y,
                "drawdown_from_12m_high": drawdown,
                "status": status,
                "reason": reason,
            }
        return {
            "defensive_score": 0,
            "current_price": current_price,
            "price_above_sma_200": price_above_sma,
            "return_1y": return_1y,
            "drawdown_from_12m_high": drawdown,
            "status": "INSUFFICIENT_MARKET_DATA",
            "reason": "Prix gratuit indisponible; l'ETF ne peut pas recevoir une allocation automatique.",
        }

    score = _role_score(role, mode)
    reasons = [f"Rôle défensif: {role or 'ETF diversifié'}."]
    if price_above_sma is True:
        score += 5
        reasons.append("Prix au-dessus de la SMA 200.")
    elif price_above_sma is False:
        score -= 6
        reasons.append("Prix sous SMA 200; utilisation possible seulement comme stabilisateur limité.")
    if return_1y is not None:
        if return_1y >= 0:
            score += 4
            reasons.append("Rendement 1 an non négatif.")
        elif return_1y <= -0.10:
            score -= 6
            reasons.append("Rendement 1 an faible; prudence.")
    if drawdown is not None and drawdown <= -0.20:
        score -= 6
        reasons.append("Drawdown important pour un ETF défensif.")
    if mode == "rational-aggressive":
        score -= 6
        reasons.append("Pénalité rational-aggressive: fallback très limité.")

    minimum = safe_float(MODE_LIMITS.get(mode, {}).get("min_score")) or 1000.0
    status = "ELIGIBLE_DEFENSIVE_FALLBACK" if score >= minimum else "WATCH_ONLY"
    if status == "WATCH_ONLY":
        reasons.append("Score défensif insuffisant pour allocation automatique.")
    return {
        "defensive_score": round(max(0.0, min(100.0, score)), 2),
        "current_price": current_price,
        "price_above_sma_200": price_above_sma,
        "return_1y": return_1y,
        "drawdown_from_12m_high": drawdown,
        "status": status,
        "reason": " ".join(reasons),
    }


def _is_allowed_for_mode(row: dict[str, Any], mode: str) -> bool:
    allowed_modes = row.get("allowed_modes") or []
    return str(mode or "") in {str(item) for item in allowed_modes}


def _role_score(role: str, mode: str) -> float:
    base = float(BASE_ROLE_SCORES.get(role, 50))
    if mode == "balanced":
        return base + float(BALANCED_ROLE_ADJUSTMENTS.get(role, 0))
    return base


def _single_limit(row: dict[str, Any], mode: str) -> float:
    limits = row.get("max_single_allocation_pct") or {}
    if isinstance(limits, dict):
        return safe_float(limits.get(mode)) or defensive_mode_limit(mode)
    return defensive_mode_limit(mode)
