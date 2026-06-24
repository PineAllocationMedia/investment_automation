from __future__ import annotations

from typing import Any

from .add_eligibility_engine import ADD_ALLOWED_STATUSES
from .defensive_etf_engine import defensive_mode_limit
from .drift_engine import can_add_by_drift
from .external_etf_engine import external_etf_is_eligible, is_external_etf_allocation_candidate
from .model_tuning import tuning_value
from .utils import clamp, safe_float


SATELLITE_WEIGHT_THRESHOLD = 0.02
WATCH_ALLOCATION_BUDGETS = {
    "balanced": 0.00,
    "family-office": 0.25,
    "rational-aggressive": 0.35,
    "high-cagr": 0.50,
}
CYCLE_SENSITIVE_LEVELS = {"HIGH", "EXTREME"}
CYCLE_ALLOCATION_BUDGETS = {
    "balanced": 0.00,
    "family-office": 0.22,
    "rational-aggressive": 0.30,
    "high-cagr": 0.45,
}
CYCLE_INDIVIDUAL_CAPS = {
    "balanced": {"HIGH": 0.00, "EXTREME": 0.00},
    "family-office": {"HIGH": 0.12, "EXTREME": 0.04},
    "rational-aggressive": {"HIGH": 0.18, "EXTREME": 0.06},
    "high-cagr": {"HIGH": 0.30, "EXTREME": 0.10},
}
HOT_GROWTH_THEME_TERMS = {
    "technology",
    "software",
    "semiconductor",
    "semiconductors",
    "cloud",
    "ai",
    "artificial intelligence",
    "communication",
    "advertising",
    "interactive",
    "internet",
    "platform",
    "app",
}
QUALITY_DIVERSIFIER_SCORE_WINDOW = {
    "balanced": 3.0,
    "family-office": 6.0,
    "rational-aggressive": 8.0,
    "high-cagr": 10.0,
}
DEFENSIVE_RESERVE_PCT = {
    "balanced": 0.45,
    "family-office": 0.20,
    "rational-aggressive": 0.05,
    "high-cagr": 0.0,
}
MODE_MIN_CAPITAL_SCORE = {
    "balanced": 78,
    "family-office": 65,
    "rational-aggressive": 60,
    "high-cagr": 50,
}
EXTERNAL_ALLOCATION_UNIVERSES = {"WATCHLIST", "MARKET_SCANNER", "DISCOVERY_IDEAS"}
EXTERNAL_ALLOCATION_BUDGETS = {
    "balanced": 0.12,
    "family-office": 0.25,
    "rational-aggressive": 0.35,
    "high-cagr": 0.0,
}
EXTERNAL_INDIVIDUAL_CAPS = {
    "balanced": 0.08,
    "family-office": 0.16,
    "rational-aggressive": 0.22,
    "high-cagr": 0.0,
}


def _defensive_reserve_pct(mode: str) -> float:
    base = DEFENSIVE_RESERVE_PCT.get(mode, 0.0)
    adjustment = tuning_value(mode, "defensive_reserve_adjustment", 0.0)
    max_pct = 0.70 if mode == "balanced" else 0.40 if mode == "family-office" else 0.10 if mode == "rational-aggressive" else 0.0
    return round(clamp(base + adjustment, 0.0, max_pct), 4)


def _minimum_capital_score(mode: str) -> float:
    base = MODE_MIN_CAPITAL_SCORE.get(mode, 55)
    adjustment = tuning_value(mode, "min_capital_score_adjustment", 0.0)
    return round(clamp(base + adjustment, 40.0, 90.0), 4)


def mandatory_vfv_percent(average_score_ex_vfv: float | None, mode: str = "rational-aggressive") -> float:
    if mode == "high-cagr":
        if average_score_ex_vfv is None:
            return _tuned_vfv_percent(0.15, mode)
        if average_score_ex_vfv >= 8.5:
            return _tuned_vfv_percent(0.00, mode)
        if average_score_ex_vfv >= 8.0:
            return _tuned_vfv_percent(0.05, mode)
        if average_score_ex_vfv >= 7.5:
            return _tuned_vfv_percent(0.10, mode)
        if average_score_ex_vfv >= 7.0:
            return _tuned_vfv_percent(0.15, mode)
        return _tuned_vfv_percent(0.20, mode)
    if mode == "balanced":
        if average_score_ex_vfv is None:
            return _tuned_vfv_percent(0.35, mode)
        if average_score_ex_vfv >= 8.5:
            return _tuned_vfv_percent(0.20, mode)
        if average_score_ex_vfv >= 8.0:
            return _tuned_vfv_percent(0.25, mode)
        if average_score_ex_vfv >= 7.5:
            return _tuned_vfv_percent(0.30, mode)
        if average_score_ex_vfv >= 7.0:
            return _tuned_vfv_percent(0.35, mode)
        return _tuned_vfv_percent(0.40, mode)
    if mode == "family-office":
        if average_score_ex_vfv is None:
            return _tuned_vfv_percent(0.30, mode)
        if average_score_ex_vfv >= 8.5:
            return _tuned_vfv_percent(0.12, mode)
        if average_score_ex_vfv >= 8.0:
            return _tuned_vfv_percent(0.15, mode)
        if average_score_ex_vfv >= 7.5:
            return _tuned_vfv_percent(0.20, mode)
        if average_score_ex_vfv >= 7.0:
            return _tuned_vfv_percent(0.25, mode)
        return _tuned_vfv_percent(0.30, mode)
    if average_score_ex_vfv is None:
        return _tuned_vfv_percent(0.25, mode)
    if average_score_ex_vfv >= 8.5:
        return _tuned_vfv_percent(0.05, mode)
    if average_score_ex_vfv >= 8.0:
        return _tuned_vfv_percent(0.10, mode)
    if average_score_ex_vfv >= 7.5:
        return _tuned_vfv_percent(0.15, mode)
    if average_score_ex_vfv >= 7.0:
        return _tuned_vfv_percent(0.20, mode)
    return _tuned_vfv_percent(0.25, mode)


def _tuned_vfv_percent(base: float, mode: str) -> float:
    adjustment = tuning_value(mode, "vfv_adjustment", 0.0)
    max_pct = 0.55 if mode == "balanced" else 0.40 if mode == "family-office" else 0.35
    return round(clamp(base + adjustment, 0.0, max_pct), 4)


def compute_average_score_ex_vfv(analyses: dict[str, dict[str, Any]]) -> float | None:
    weighted_scores: list[tuple[float, float]] = []
    fallback_scores: list[float] = []
    for ticker, row in analyses.items():
        if ticker == "VFV.TO":
            continue
        score = safe_float(row.get("score_total"))
        if score is None:
            continue
        weight = safe_float(row.get("position_weight")) or 0.0
        if 0 < weight < SATELLITE_WEIGHT_THRESHOLD:
            row["average_score_excluded_reason"] = "Petite position satellite/speculative sous 2 % du portefeuille."
            continue
        if weight > 0:
            weighted_scores.append((score, weight))
        else:
            row["average_score_excluded_reason"] = (
                "Position candidate à 0 $: considérée pour les cotisations, mais exclue de la moyenne des positions détenues."
            )
            fallback_scores.append(score)

    if weighted_scores:
        total_weight = sum(weight for _, weight in weighted_scores)
        if total_weight > 0:
            return sum(score * weight for score, weight in weighted_scores) / total_weight
    if not fallback_scores:
        return None
    return sum(fallback_scores) / len(fallback_scores)


def allocate_capital(
    capital: float,
    analyses: dict[str, dict[str, Any]],
    mode: str,
    defensive_etf_candidates: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    capital = safe_float(capital) or 0.0
    defensive_etf_candidates = defensive_etf_candidates or []
    average_score = compute_average_score_ex_vfv(analyses)
    vfv_pct = mandatory_vfv_percent(average_score, mode)
    allocations: list[dict[str, Any]] = []

    if capital <= 0:
        return {
            "average_score_ex_vfv": average_score,
            "mandatory_vfv_percent": vfv_pct,
            "allocations": [],
            "allocation_log": ["Capital analysé = 0 $, aucune nouvelle allocation à produire."],
        }

    mandatory_vfv_amount = round(capital * vfv_pct, 2)
    if mandatory_vfv_amount > 0:
        allocations.append(
            _allocation_row(
                "VFV.TO",
                mandatory_vfv_amount,
                capital,
                "Allocation VFV obligatoire",
                100,
                "Filet de sécurité S&P 500 selon moyenne des scores.",
                "allocation VFV obligatoire",
                "HIGH",
            )
        )

    remaining = round(capital - mandatory_vfv_amount, 2)
    candidates = [row for row in analyses.values() if row.get("ticker") != "VFV.TO" and _eligible(row, mode)]
    candidates = sorted(candidates, key=_candidate_sort_key, reverse=True)
    allocation_log = [f"Allocation VFV obligatoire: {vfv_pct:.0%}."]

    if remaining <= 0:
        return {
            "average_score_ex_vfv": average_score,
            "mandatory_vfv_percent": vfv_pct,
            "allocations": allocations,
            "allocation_log": allocation_log,
        }

    defensive_reserve_target = round(capital * _defensive_reserve_pct(mode), 2)
    defensive_used_total = 0.0
    if defensive_reserve_target > 0:
        defensive_rows, defensive_used_total = _defensive_fallback_rows(
            amount_to_allocate=min(remaining, defensive_reserve_target),
            total_capital=capital,
            mode=mode,
            defensive_etf_candidates=defensive_etf_candidates,
            reason="Réserve défensive de mode: protège une partie de la cotisation avant les actions individuelles.",
        )
        if defensive_rows:
            allocations.extend(defensive_rows)
            remaining = round(remaining - defensive_used_total, 2)
            allocation_log.append(
                f"Réserve défensive {mode}: {defensive_used_total:.2f} $ / {defensive_reserve_target:.2f} $."
            )

    if remaining <= 0:
        return _finalize_allocations(capital, allocations, average_score, vfv_pct, allocation_log)

    if not candidates:
        defensive_rows, defensive_used = _defensive_fallback_rows(
            amount_to_allocate=remaining,
            total_capital=capital,
            mode=mode,
            defensive_etf_candidates=defensive_etf_candidates,
            already_allocated=defensive_used_total,
            reason="Aucune action core admissible; stabilisateur défensif limité avant redirection VFV.",
        )
        if defensive_rows:
            allocations.extend(defensive_rows)
            remaining = round(remaining - defensive_used, 2)
            allocation_log.append(f"Defensive ETF fallback: {defensive_used:.2f} $ utilisés avant VFV.")
        if remaining > 0.01:
            allocations.append(
                _allocation_row(
                    "VFV.TO",
                    remaining,
                    capital,
                    "Redirection VFV",
                    100,
                    "Aucune action n’est clairement admissible au nouveau capital.",
                    "cash rule",
                    "HIGH",
                )
            )
            allocation_log.append("Aucune action admissible: capital restant redirigé vers VFV.TO.")
        return _finalize_allocations(capital, allocations, average_score, vfv_pct, allocation_log)

    optimized_allocations, optimizer_log = _optimize_monthly_contribution(
        capital=capital,
        remaining=remaining,
        analyses=analyses,
        candidates=candidates,
        mode=mode,
        defensive_etf_candidates=defensive_etf_candidates,
        defensive_already_allocated=defensive_used_total,
    )
    allocations.extend(optimized_allocations)
    allocation_log.extend(optimizer_log)
    return _finalize_allocations(capital, allocations, average_score, vfv_pct, allocation_log)


def _legacy_no_candidate_vfv_redirect(
    capital: float,
    remaining: float,
    allocations: list[dict[str, Any]],
    average_score: float | None,
    vfv_pct: float,
    allocation_log: list[str],
) -> dict[str, Any]:
    if remaining > 0.01:
        allocations.append(
            _allocation_row(
                "VFV.TO",
                remaining,
                capital,
                "Redirection VFV",
                100,
                "Aucune action n’est clairement admissible au nouveau capital.",
                "cash rule",
                "HIGH",
            )
        )
        allocation_log.append("Aucune action admissible: capital restant redirigé vers VFV.TO.")
    return _finalize_allocations(capital, allocations, average_score, vfv_pct, allocation_log)


def _eligible(analysis: dict[str, Any], mode: str) -> bool:
    if is_external_etf_allocation_candidate(analysis):
        return external_etf_is_eligible(analysis, mode)
    universe = str(analysis.get("universe") or "CORE_PORTFOLIO")
    if universe in EXTERNAL_ALLOCATION_UNIVERSES and not _external_candidate_allowed(analysis, mode):
        return False
    if analysis.get("ticker_validation_status") in {"NO_MARKET_DATA", "POSSIBLE_WRONG_TICKER"}:
        return False
    if analysis.get("thesis_status") != "INTACT":
        return False
    add_status = analysis.get("add_eligibility_status")
    if add_status:
        if add_status not in ADD_ALLOWED_STATUSES:
            return False
    elif analysis.get("liquidation_status") != "GREEN":
        return False
    if analysis.get("trend_status") == "DETERIORATING" and (safe_float(analysis.get("trend_severity")) or 0.0) >= 2:
        return False
    if analysis.get("data_reliability_level") == "LOW":
        return False
    if not can_add_by_drift(analysis):
        return False
    capital_score = safe_float(analysis.get("capital_allocation_score")) or 0.0
    minimum_score = _minimum_capital_score(mode)
    if capital_score < minimum_score:
        return False
    if mode == "balanced":
        if _is_watch_limited(analysis):
            return False
        if analysis.get("quality_drawdown_status") == "QUALITY_DRAWDOWN_OPPORTUNITY":
            return False
        if analysis.get("expected_cagr_quality") not in {"HIGH", "VERY_HIGH"}:
            return False
        if analysis.get("opportunity_cost_status") != "CLEARLY_BETTER_THAN_VFV":
            return False
        if analysis.get("cycle_bubble_risk_level") in {"HIGH", "EXTREME"}:
            return False
        if analysis.get("long_term_durability_status") not in {"VERY_DURABLE_COMPOUNDER"}:
            return False
        if (safe_float(analysis.get("business_quality_score")) or 0.0) < 85:
            return False
        if (safe_float(analysis.get("conviction_score")) or 0.0) < 85:
            return False
    business_quality = safe_float(analysis.get("business_quality_score"))
    high_cagr_potential = safe_float(analysis.get("high_cagr_potential_score"))
    if business_quality is not None and business_quality < 65:
        return False
    if mode == "high-cagr" and high_cagr_potential is not None and high_cagr_potential < 70:
        return False
    if _is_starter_core_candidate(analysis):
        if analysis.get("expected_cagr_quality") not in {"HIGH", "VERY_HIGH"}:
            return False
        reliability_level = str(analysis.get("data_reliability_level") or "")
        if reliability_level in {"LOW", "MEDIUM"}:
            return False
        if analysis.get("opportunity_cost_status") != "CLEARLY_BETTER_THAN_VFV":
            return False
        if capital_score < (55 if mode == "high-cagr" else 60):
            return False
    if analysis.get("opportunity_cost_status") == "WORSE_THAN_VFV":
        return False
    if analysis.get("quality_but_too_expensive") is True:
        exception = (
            (safe_float(analysis.get("conviction_score")) or 0.0) >= 85
            and analysis.get("expected_cagr_quality") == "VERY_HIGH"
        )
        if mode == "balanced" or not exception:
            return False
    if mode in {"rational-aggressive", "family-office"} and capital_score >= 70:
        if analysis.get("expected_cagr_quality") not in {"HIGH", "VERY_HIGH"} and not _quality_drawdown_allocation_exception(
            analysis, mode
        ):
            return False
    if mode == "high-cagr" and capital_score >= 60:
        if analysis.get("expected_cagr_quality") not in {"HIGH", "VERY_HIGH"} and not _quality_drawdown_allocation_exception(
            analysis, mode
        ):
            return False
    if analysis.get("cycle_bubble_risk_level") == "EXTREME" and capital_score < 65:
        return False
    if analysis.get("long_term_durability_status") == "SPECULATIVE_OR_UNPROVEN":
        return False
    return True


def _external_candidate_allowed(analysis: dict[str, Any], mode: str) -> bool:
    if mode == "high-cagr":
        return False
    universe = str(analysis.get("universe") or "")
    if universe not in EXTERNAL_ALLOCATION_UNIVERSES:
        return True
    if analysis.get("ticker_validation_status") in {"NO_MARKET_DATA", "POSSIBLE_WRONG_TICKER"}:
        return False
    if analysis.get("thesis_status") != "INTACT" or analysis.get("liquidation_status") != "GREEN":
        return False
    if analysis.get("add_eligibility_status") not in ADD_ALLOWED_STATUSES:
        return False
    if analysis.get("opportunity_cost_status") != "CLEARLY_BETTER_THAN_VFV":
        return False
    if analysis.get("expected_cagr_quality") not in {"HIGH", "VERY_HIGH"}:
        return False
    if analysis.get("quality_but_too_expensive") is True:
        return False
    if str(analysis.get("data_reliability_level") or "") == "LOW" or str(analysis.get("data_quality") or "") == "LOW":
        return False
    if str(analysis.get("external_superiority") or "") in {
        "NOT_COMPARABLE_TO_CORE_LEADERS",
        "NOT_FULLY_ALIGNED_WITH_HIGH_CAGR_CORE",
    }:
        return False

    capital_score = safe_float(analysis.get("capital_allocation_score")) or 0.0
    score_total = safe_float(analysis.get("score_total")) or 0.0
    conviction = safe_float(analysis.get("conviction_score")) or 0.0
    business_quality = safe_float(analysis.get("business_quality_score")) or 0.0
    durability = str(analysis.get("long_term_durability_status") or "")
    cycle_level = str(analysis.get("cycle_bubble_risk_level") or "LOW")

    if mode == "balanced":
        if capital_score < 82 or score_total < 8.5 or conviction < 85 or business_quality < 85:
            return False
        if durability != "VERY_DURABLE_COMPOUNDER":
            return False
        if cycle_level in {"HIGH", "EXTREME"}:
            return False
        if _external_status(analysis) not in {"HIGH_PRIORITY_WATCH", "MANUAL_REVIEW_TOP_CANDIDATE", "ADD_TO_MARKET_UNIVERSE_REVIEW"}:
            return False
        return True

    if mode == "family-office":
        if capital_score < 72 or score_total < 8.0 or conviction < 78 or business_quality < 78:
            return False
        if _external_status(analysis) in {
            "TOO_EXPENSIVE",
            "REJECTED",
            "AVOID_FOR_NOW",
            "INSUFFICIENT_DATA",
            "NOT_ALIGNED_NOW",
        }:
            return False
        if cycle_level == "EXTREME" and capital_score < 88:
            return False
        return True

    if mode == "rational-aggressive":
        if capital_score < 70 or score_total < 8.0 or conviction < 75 or business_quality < 75:
            return False
        if _external_status(analysis) in {
            "TOO_EXPENSIVE",
            "REJECTED",
            "AVOID_FOR_NOW",
            "INSUFFICIENT_DATA",
            "NOT_ALIGNED_NOW",
        }:
            return False
        if cycle_level == "EXTREME" and capital_score < 85:
            return False
        return True

    return False


def _external_status(analysis: dict[str, Any]) -> str:
    for key in ("watchlist_status", "candidate_status", "discovery_status", "promotion_status"):
        value = str(analysis.get(key) or "")
        if value:
            return value
    return ""


def _is_external_candidate(candidate: dict[str, Any]) -> bool:
    return str(candidate.get("universe") or "") in EXTERNAL_ALLOCATION_UNIVERSES


def _candidate_sort_key(analysis: dict[str, Any]) -> tuple[float, float, float, float]:
    winner = 1.0 if analysis.get("winner_accelerated") else 0.0
    score = safe_float(analysis.get("capital_allocation_score")) or 0.0
    conviction = safe_float(analysis.get("conviction_score")) or 0.0
    drawdown_bonus = abs(min(safe_float(analysis.get("drawdown_from_12m_high")) or 0.0, 0.0))
    return (winner, score, conviction, drawdown_bonus)


def _optimize_monthly_contribution(
    capital: float,
    remaining: float,
    analyses: dict[str, dict[str, Any]],
    candidates: list[dict[str, Any]],
    mode: str,
    defensive_etf_candidates: list[dict[str, Any]] | None = None,
    defensive_already_allocated: float = 0.0,
) -> tuple[list[dict[str, Any]], list[str]]:
    allocations_by_ticker: dict[str, float] = {}
    remaining_to_allocate = round(remaining, 2)
    current_total = _current_portfolio_value(analyses)
    chunk = _monthly_chunk_size(capital, mode)
    log = ["Optimisation mensuelle: simulation des poids après contribution."]
    candidate_lookup = {str(row.get("ticker")): row for row in candidates}

    while remaining_to_allocate > 0.01:
        best_candidate = None
        best_score = -1_000_000.0
        best_room = 0.0

        for candidate in candidates:
            room = _available_monthly_room(candidate, allocations_by_ticker, candidate_lookup, current_total, capital, mode)
            if room <= 0.01:
                continue
            score = _marginal_monthly_score(candidate, allocations_by_ticker, candidate_lookup, current_total, capital, mode)
            if score > best_score:
                best_candidate = candidate
                best_score = score
                best_room = room

        if best_candidate is None:
            break

        ticker = best_candidate["ticker"]
        amount = round(min(chunk, remaining_to_allocate, best_room), 2)
        if amount <= 0:
            break
        allocations_by_ticker[ticker] = round(allocations_by_ticker.get(ticker, 0.0) + amount, 2)
        remaining_to_allocate = round(remaining_to_allocate - amount, 2)

    if remaining_to_allocate > 0.01 and mode == "high-cagr":
        overflow_candidates = _high_cagr_overflow_candidates(analyses, candidates)
        redirection_room = _high_cagr_vfv_redirection_room(capital, remaining, overflow_candidates)
        deployable_overflow = round(max(0.0, remaining_to_allocate - redirection_room), 2)
        if deployable_overflow > 0.01:
            deployed = _deploy_high_cagr_overflow(
                amount_to_deploy=deployable_overflow,
                allocations_by_ticker=allocations_by_ticker,
                current_total=current_total,
                capital=capital,
                candidates=overflow_candidates,
                chunk=chunk,
            )
            if deployed > 0:
                remaining_to_allocate = round(remaining_to_allocate - deployed, 2)
                log.append(
                    "Redirection VFV plafonnée en mode high-CAGR: surplus réalloué aux titres admissibles avec thèse intacte."
                )

    rows = []
    all_lookup = {**candidate_lookup, **{str(row.get("ticker")): row for row in analyses.values()}}
    watch_budget = _watch_allocation_budget(capital, mode)
    watch_allocated = _watch_allocated_total(allocations_by_ticker, all_lookup)
    if watch_allocated > 0:
        log.append(
            f"Budget titres sous surveillance: {watch_allocated:.2f} $ / {watch_budget:.2f} $ "
            "(évite qu'une cotisation entière soit aspirée par des titres encore à valider)."
        )
    if _cycle_budget_should_apply(candidate_lookup, mode):
        cycle_budget = _cycle_allocation_budget(capital, mode)
        cycle_allocated = _cycle_allocated_total(allocations_by_ticker, all_lookup)
        log.append(
            f"Budget cycle/bulle/tendance: {cycle_allocated:.2f} $ / {cycle_budget:.2f} $ "
            "(préserve le haut CAGR, mais évite qu'une cotisation soit trop dépendante d'un thème chaud)."
        )
    external_allocated = _external_allocated_total(allocations_by_ticker, all_lookup)
    if external_allocated > 0:
        log.append(
            f"Budget nouvelles positions externes: {external_allocated:.2f} $ / {_external_allocation_budget(capital, mode):.2f} $ "
            "(évite qu'une idée externe remplace trop vite le Core Portfolio)."
        )
    for ticker, amount in sorted(
        allocations_by_ticker.items(),
        key=lambda item: safe_float(analyses.get(item[0], {}).get("capital_allocation_score")) or 0.0,
        reverse=True,
    ):
        candidate = analyses[ticker]
        rows.append(
            _allocation_row(
                ticker,
                amount,
                capital,
                _optimizer_block_name(mode, candidate),
                candidate.get("capital_allocation_score"),
                _optimizer_reason(candidate),
                _optimizer_rule(candidate, mode),
                _allocation_confidence(candidate),
            )
        )

    if remaining_to_allocate > 0.01:
        defensive_rows, defensive_used = _defensive_fallback_rows(
            amount_to_allocate=remaining_to_allocate,
            total_capital=capital,
            mode=mode,
            defensive_etf_candidates=defensive_etf_candidates or [],
            already_allocated=defensive_already_allocated,
            reason="Solde non plaçable dans les actions core sans dépasser les garde-fous; stabilisateur défensif limité.",
        )
        if defensive_rows:
            rows.extend(defensive_rows)
            remaining_to_allocate = round(remaining_to_allocate - defensive_used, 2)
            log.append(f"Defensive ETF fallback: {defensive_used:.2f} $ utilisés avant redirection VFV.")
    if remaining_to_allocate > 0.01:
        rows.append(
            _allocation_row(
                "VFV.TO",
                remaining_to_allocate,
                capital,
                "Redirection VFV",
                100,
                "Solde non plaçable sans violer les plafonds de concentration ou de qualité.",
                "optimisation mensuelle + cash rule",
                "HIGH",
            )
        )
    return rows, log


def _high_cagr_overflow_candidates(
    analyses: dict[str, dict[str, Any]],
    primary_candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_ticker = {row["ticker"]: row for row in primary_candidates}
    for row in analyses.values():
        ticker = row.get("ticker")
        if not ticker or ticker == "VFV.TO":
            continue
        if ticker in by_ticker:
            continue
        if _high_cagr_overflow_eligible(row):
            by_ticker[ticker] = row
    return sorted(by_ticker.values(), key=_candidate_sort_key, reverse=True)


def _high_cagr_overflow_eligible(candidate: dict[str, Any]) -> bool:
    if _is_external_candidate(candidate):
        return False
    if candidate.get("thesis_status") != "INTACT":
        return False
    if candidate.get("add_eligibility_status") not in ADD_ALLOWED_STATUSES:
        return False
    if candidate.get("liquidation_status") in {"ORANGE", "RED"}:
        return False
    if candidate.get("data_reliability_level") == "LOW":
        return False
    if not can_add_by_drift(candidate):
        return False
    if candidate.get("expected_cagr_quality") not in {"HIGH", "VERY_HIGH"}:
        return False
    if candidate.get("opportunity_cost_status") != "CLEARLY_BETTER_THAN_VFV":
        return False
    if candidate.get("quality_but_too_expensive") is True:
        return False
    if candidate.get("long_term_durability_status") == "SPECULATIVE_OR_UNPROVEN":
        return False
    capital_score = safe_float(candidate.get("capital_allocation_score")) or 0.0
    business_quality = safe_float(candidate.get("business_quality_score"))
    high_cagr_potential = safe_float(candidate.get("high_cagr_potential_score"))
    if capital_score < 40:
        return False
    if business_quality is not None and business_quality < 75:
        return False
    if high_cagr_potential is not None and high_cagr_potential < 70:
        return False
    return True


def _high_cagr_vfv_redirection_room(
    capital: float,
    remaining_after_mandatory_vfv: float,
    overflow_candidates: list[dict[str, Any]],
) -> float:
    robust_count = len([candidate for candidate in overflow_candidates if _high_cagr_overflow_eligible(candidate)])
    excellent_count = len(
        [
            candidate
            for candidate in overflow_candidates
            if _high_cagr_overflow_eligible(candidate)
            and (safe_float(candidate.get("capital_allocation_score")) or 0.0) >= 60
        ]
    )
    mandatory_vfv_amount = max(0.0, capital - remaining_after_mandatory_vfv)
    if excellent_count >= 3 or robust_count >= 5:
        max_total_vfv = capital * 0.20
    elif robust_count >= 3:
        max_total_vfv = capital * 0.25
    elif robust_count == 2:
        max_total_vfv = capital * 0.35
    else:
        return capital
    return round(max(0.0, max_total_vfv - mandatory_vfv_amount), 2)


def _deploy_high_cagr_overflow(
    amount_to_deploy: float,
    allocations_by_ticker: dict[str, float],
    current_total: float,
    capital: float,
    candidates: list[dict[str, Any]],
    chunk: float,
) -> float:
    remaining = round(amount_to_deploy, 2)
    deployed = 0.0
    while remaining > 0.01:
        best_candidate = None
        best_score = -1_000_000.0
        best_room = 0.0
        candidate_lookup = {str(row.get("ticker")): row for row in candidates}
        for candidate in candidates:
            room = _high_cagr_overflow_room(candidate, allocations_by_ticker, candidate_lookup, current_total, capital)
            if room <= 0.01:
                continue
            score = _high_cagr_overflow_score(candidate, allocations_by_ticker, candidate_lookup)
            if score > best_score:
                best_candidate = candidate
                best_score = score
                best_room = room
        if best_candidate is None:
            break
        amount = round(min(chunk, remaining, best_room), 2)
        if amount <= 0:
            break
        ticker = best_candidate["ticker"]
        allocations_by_ticker[ticker] = round(allocations_by_ticker.get(ticker, 0.0) + amount, 2)
        best_candidate["_high_cagr_overflow_used"] = True
        remaining = round(remaining - amount, 2)
        deployed = round(deployed + amount, 2)
    return deployed


def _high_cagr_overflow_room(
    candidate: dict[str, Any],
    allocations_by_ticker: dict[str, float],
    candidate_lookup: dict[str, dict[str, Any]],
    current_total: float,
    capital: float,
) -> float:
    already_allocated = allocations_by_ticker.get(candidate["ticker"], 0.0)
    amount_basis = capital
    score = safe_float(candidate.get("capital_allocation_score")) or 0.0
    if score >= 70:
        fraction = 0.45
    elif score >= 60:
        fraction = 0.35
    elif score >= 50:
        fraction = 0.28
    else:
        fraction = 0.18
    if candidate.get("add_eligibility_status") == "ADD_ALLOWED_SMALL":
        fraction = min(fraction, 0.30)
        if _is_starter_core_candidate(candidate) and score < 70:
            fraction = min(fraction, 0.25)
    if candidate.get("cycle_bubble_risk_level") == "EXTREME":
        fraction = min(fraction, 0.18)
    elif candidate.get("cycle_bubble_risk_level") == "HIGH":
        fraction = min(fraction, 0.22)
    if _has_poor_free_data_coverage(candidate):
        fraction = min(fraction, 0.12)
    monthly_cap = amount_basis * fraction
    denominator = current_total + capital if current_total + capital > 0 else capital
    current_weight = (_candidate_current_value(candidate, current_total) + already_allocated) / denominator if denominator > 0 else 0.0
    if current_weight > 0.34:
        return 0.0
    room = round(max(0.0, monthly_cap - already_allocated), 2)
    return round(
        min(
            room,
            _watch_budget_room(candidate, allocations_by_ticker, candidate_lookup, capital, "high-cagr"),
            _cycle_budget_room(candidate, allocations_by_ticker, candidate_lookup, capital, "high-cagr"),
        ),
        2,
    )


def _high_cagr_overflow_score(
    candidate: dict[str, Any],
    allocations_by_ticker: dict[str, float],
    candidate_lookup: dict[str, dict[str, Any]],
) -> float:
    score = safe_float(candidate.get("capital_allocation_score")) or 0.0
    conviction = safe_float(candidate.get("conviction_score")) or 0.0
    stability = safe_float(candidate.get("allocation_stability_adjustment")) or 0.0
    already_allocated = allocations_by_ticker.get(candidate["ticker"], 0.0)
    quality_bonus = 8.0 if candidate.get("expected_cagr_quality") == "VERY_HIGH" else 4.0
    cycle_penalty = (safe_float(candidate.get("cycle_bubble_penalty")) or 0.0) * 0.35
    diversifier_bonus = _quality_diversifier_bonus(candidate, allocations_by_ticker, candidate_lookup, "high-cagr")
    allocation_drag = already_allocated * 0.04
    return score + quality_bonus + (conviction * 0.05) + stability + diversifier_bonus - cycle_penalty - allocation_drag


def _candidate_cap(candidate: dict[str, Any], mode: str, amount_basis: float) -> float:
    score = safe_float(candidate.get("capital_allocation_score")) or 0.0
    if mode == "balanced":
        fraction = 0.12 if score >= 90 else 0.10 if score >= 80 else 0.06
    elif mode == "high-cagr":
        fraction = 0.70 if score >= 90 else 0.60 if score >= 80 else 0.50 if score >= 70 else 0.30 if score >= 60 else 0.20
    elif mode == "family-office":
        fraction = 0.32 if score >= 90 else 0.26 if score >= 80 else 0.18 if score >= 70 else 0.10
    elif mode == "rational-aggressive":
        fraction = 0.40 if score >= 90 else 0.32 if score >= 80 else 0.24 if score >= 70 else 0.12
    else:
        fraction = 0.60 if score >= 90 else 0.45 if score >= 80 else 0.35 if score >= 70 else 0.15
    if candidate.get("drift_status") == "HIGH_CONVICTION_ADD_ALLOWED":
        fraction = min(fraction, 0.35 if mode == "high-cagr" else 0.25)
    if candidate.get("add_eligibility_status") == "ADD_ALLOWED_SMALL":
        if _is_starter_core_candidate(candidate):
            if mode == "high-cagr":
                starter_fraction = 0.45 if score >= 85 else 0.35 if score >= 70 else 0.30 if score >= 60 else 0.20
                fraction = min(max(fraction, starter_fraction), 0.35 if score < 85 else 0.45)
            else:
                fraction = min(fraction, 0.25)
        else:
            fraction = min(fraction, 0.25 if mode == "high-cagr" else 0.15)
    if _has_poor_free_data_coverage(candidate):
        fraction = min(fraction, 0.12 if mode == "high-cagr" else 0.08)
    if _is_external_candidate(candidate):
        fraction = min(fraction, _external_individual_cap_fraction(mode))
    fraction *= _cycle_allocation_multiplier(candidate)
    fraction += tuning_value(mode, "single_stock_cap_adjustment", 0.0)
    max_fraction = 0.75 if mode == "high-cagr" else 0.45 if mode == "rational-aggressive" else 0.35 if mode == "family-office" else 0.18
    fraction = clamp(fraction, 0.0, max_fraction)
    return round(amount_basis * fraction, 2)


def _current_portfolio_value(analyses: dict[str, dict[str, Any]]) -> float:
    total = sum(safe_float(row.get("current_value")) or 0.0 for row in analyses.values())
    if total > 0:
        return total
    return 100_000.0


def _candidate_current_value(candidate: dict[str, Any], current_total: float) -> float:
    value = safe_float(candidate.get("current_value"))
    if value is not None:
        return value
    return (safe_float(candidate.get("position_weight")) or 0.0) * current_total


def _monthly_chunk_size(capital: float, mode: str) -> float:
    fraction = 0.05 if mode == "high-cagr" else 0.04
    return round(max(10.0, min(50.0, capital * fraction)), 2)


def _target_post_contribution_weight(candidate: dict[str, Any], mode: str) -> float:
    quality = str(candidate.get("expected_cagr_quality"))
    conviction = safe_float(candidate.get("conviction_score")) or 0.0
    capital_score = safe_float(candidate.get("capital_allocation_score")) or 0.0

    if mode == "balanced":
        base = 0.10 if quality == "VERY_HIGH" else 0.08 if quality == "HIGH" else 0.04
    elif mode == "high-cagr":
        base = 0.30 if quality == "VERY_HIGH" and conviction >= 85 else 0.25 if quality in {"HIGH", "VERY_HIGH"} else 0.15
    elif mode == "family-office":
        base = 0.22 if quality == "VERY_HIGH" and conviction >= 85 else 0.18 if quality in {"HIGH", "VERY_HIGH"} else 0.10
    elif mode == "rational-aggressive":
        base = 0.26 if quality == "VERY_HIGH" and conviction >= 85 else 0.22 if quality in {"HIGH", "VERY_HIGH"} else 0.12
    else:
        base = 0.25 if quality == "VERY_HIGH" and conviction >= 85 else 0.22 if quality in {"HIGH", "VERY_HIGH"} else 0.12

    if capital_score >= 90:
        base += 0.03
    elif capital_score < 70:
        base -= 0.03

    base *= _cycle_allocation_multiplier(candidate)
    base += tuning_value(mode, "target_weight_adjustment", 0.0)

    if _is_external_candidate(candidate):
        if mode == "balanced":
            external_target = 0.07 if capital_score >= 90 and conviction >= 90 else 0.05
        elif mode == "family-office":
            external_target = 0.14 if capital_score >= 90 and conviction >= 85 else 0.10
        elif mode == "rational-aggressive":
            external_target = 0.18 if capital_score >= 90 and conviction >= 85 else 0.14
        else:
            external_target = 0.0
        if candidate.get("add_eligibility_status") == "ADD_ALLOWED_SMALL":
            external_target *= 0.65
        return min(base, external_target)

    if candidate.get("add_eligibility_status") == "ADD_ALLOWED_SMALL":
        if _is_quality_diversifier_candidate(candidate, mode):
            return min(base, 0.15 if mode == "high-cagr" else 0.10)
        return min(base, 0.12 if mode == "high-cagr" else 0.08)
    if candidate.get("drift_status") == "HIGH_CONVICTION_ADD_ALLOWED":
        if mode == "balanced":
            drift_cap = 0.12
        elif mode == "high-cagr":
            drift_cap = 0.35
        elif mode == "family-office":
            drift_cap = 0.25
        elif mode == "rational-aggressive":
            drift_cap = 0.30
        else:
            drift_cap = 0.32
        return min(max(base, safe_float(candidate.get("position_weight")) or 0.0), drift_cap)
    if mode == "balanced":
        return min(base, 0.12)
    if mode == "family-office":
        return min(base, 0.25)
    if mode == "rational-aggressive":
        return min(base, 0.30)
    return min(base, 0.30)


def _available_monthly_room(
    candidate: dict[str, Any],
    allocations_by_ticker: dict[str, float],
    candidate_lookup: dict[str, dict[str, Any]],
    current_total: float,
    capital: float,
    mode: str,
) -> float:
    ticker = candidate["ticker"]
    already_allocated = allocations_by_ticker.get(ticker, 0.0)
    denominator = current_total + capital if current_total + capital > 0 else capital
    current_value = _candidate_current_value(candidate, current_total)
    target_weight = _target_post_contribution_weight(candidate, mode)
    room_to_target = max(0.0, target_weight * denominator - current_value - already_allocated)
    room_by_monthly_cap = max(0.0, _candidate_cap(candidate, mode, capital) - already_allocated)
    room_by_watch_budget = _watch_budget_room(candidate, allocations_by_ticker, candidate_lookup, capital, mode)
    room_by_cycle_budget = _cycle_budget_room(candidate, allocations_by_ticker, candidate_lookup, capital, mode)
    room_by_external_budget = _external_budget_room(candidate, allocations_by_ticker, candidate_lookup, capital, mode)
    return round(
        min(room_to_target, room_by_monthly_cap, room_by_watch_budget, room_by_cycle_budget, room_by_external_budget),
        2,
    )


def _marginal_monthly_score(
    candidate: dict[str, Any],
    allocations_by_ticker: dict[str, float],
    candidate_lookup: dict[str, dict[str, Any]],
    current_total: float,
    capital: float,
    mode: str,
) -> float:
    ticker = candidate["ticker"]
    current_value = _candidate_current_value(candidate, current_total)
    allocated = allocations_by_ticker.get(ticker, 0.0)
    denominator = current_total + capital if current_total + capital > 0 else capital
    post_weight = (current_value + allocated) / denominator if denominator > 0 else 0.0
    target_weight = _target_post_contribution_weight(candidate, mode)
    capital_score = safe_float(candidate.get("capital_allocation_score")) or 0.0
    drawdown = safe_float(candidate.get("drawdown_from_12m_high")) or 0.0

    quality_bonus = {"VERY_HIGH": 6.0, "HIGH": 3.0, "MEDIUM": 0.0}.get(str(candidate.get("expected_cagr_quality")), -4.0)
    opportunity_bonus = 4.0 if candidate.get("opportunity_cost_status") == "CLEARLY_BETTER_THAN_VFV" else 0.0
    durability_adjustment = {
        "VERY_DURABLE_COMPOUNDER": 3.0,
        "DURABLE_BUT_CYCLICAL": 0.5,
        "HIGH_GROWTH_BUT_FRAGILE": -2.0,
        "SPECULATIVE_OR_UNPROVEN": -8.0,
    }.get(str(candidate.get("long_term_durability_status") or ""), 0.0)
    under_target_bonus = max(0.0, (target_weight - post_weight) / target_weight) * 4.0 if target_weight > 0 else 0.0
    drawdown_bonus = min(abs(min(drawdown, 0.0)) * 10.0, 3.0)
    concentration_drag = max(0.0, post_weight - target_weight * 0.85) * (90.0 if mode == "high-cagr" else 120.0)
    cycle_drag = (safe_float(candidate.get("cycle_bubble_penalty")) or 0.0) * 0.65
    stability_adjustment = safe_float(candidate.get("allocation_stability_adjustment")) or 0.0
    diversifier_bonus = _quality_diversifier_bonus(candidate, allocations_by_ticker, candidate_lookup, mode)

    return (
        capital_score
        + quality_bonus
        + opportunity_bonus
        + durability_adjustment
        + under_target_bonus
        + drawdown_bonus
        + stability_adjustment
        + diversifier_bonus
        - concentration_drag
        - cycle_drag
    )


def _optimizer_block_name(mode: str, candidate: dict[str, Any] | None = None) -> str:
    if candidate and is_external_etf_allocation_candidate(candidate):
        return "ETF externe"
    if candidate and str(candidate.get("universe") or "") in EXTERNAL_ALLOCATION_UNIVERSES:
        return "Nouvelle position externe"
    return "Optimisation mensuelle high-CAGR" if mode == "high-cagr" else "Optimisation mensuelle"


def _optimizer_reason(candidate: dict[str, Any]) -> str:
    if is_external_etf_allocation_candidate(candidate):
        return (
            "ETF externe retenu par ce mode: il est évalué selon son rôle de portefeuille, sa tendance, "
            "son drawdown, son risque de concentration et son adéquation au profil du mode, pas comme une entreprise individuelle."
        )
    if str(candidate.get("universe") or "") in EXTERNAL_ALLOCATION_UNIVERSES:
        return (
            "Nouvelle position externe retenue par ce mode: le titre provient de la surveillance externe, "
            "passe les garde-fous de qualité, thèse, données, valorisation et avantage face à VFV, sans devoir être promu manuellement."
        )
    if candidate.get("_high_cagr_overflow_used"):
        return (
            "Allocation high-CAGR: VFV reste le filet de sécurité, mais le surplus est réalloué "
            "vers un titre admissible avec thèse intacte et avantage clair face à VFV."
        )
    if candidate.get("quality_drawdown_status") == "QUALITY_DRAWDOWN_OPPORTUNITY":
        return (
            "Quality drawdown: le titre a chuté, mais la thèse, la vente GREEN, la durabilité et le cash-flow "
            "restent assez solides; l'allocation est permise de façon limitée pour éviter de manquer un winner temporairement puni."
        )
    cycle_level = str(candidate.get("cycle_bubble_risk_level") or "")
    if cycle_level in {"HIGH", "EXTREME"}:
        return (
            "Allocation réduite: entreprise de qualité possible, mais thème/cycle déjà chaud ou cyclique; "
            "le sizing limite le risque de payer une tendance."
        )
    if (safe_float(candidate.get("_quality_diversifier_bonus")) or 0.0) > 0:
        return (
            "Allocation retenue aussi pour son rôle de diversificateur de qualité: le titre garde un profil "
            "haut CAGR, tout en réduisant la dépendance de la cotisation aux thèmes déjà chauds."
        )
    if (safe_float(candidate.get("allocation_stability_adjustment")) or 0.0) > 0:
        return (
            "Allocation retenue après amortisseur mensuel: le titre reste bien classé et la continuité évite "
            "un changement causé seulement par du bruit de marché."
        )
    if _has_poor_free_data_coverage(candidate):
        return (
            "Allocation limitée: le ticker semble valide, mais les données gratuites couvrent mal les fondamentaux; "
            "une validation BNCD/Morningstar ou manuelle est requise avant une grosse allocation."
        )
    if candidate.get("add_eligibility_status") == "ADD_ALLOWED_SMALL" and _is_starter_core_candidate(candidate):
        return (
            "Allocation de démarrage: titre core à 0 $, qualité et thèse suffisantes, mais sizing limité "
            "par la surveillance technique/valorisation."
        )
    if candidate.get("add_eligibility_status") == "ADD_ALLOWED_SMALL":
        return (
            "Allocation limitée: qualité et thèse suffisantes, mais la position reste en surveillance "
            "technique/valorisation."
        )
    return (
        "Meilleur gain marginal après simulation de la contribution: qualité, thèse intacte, "
        "avantage vs VFV et concentration post-achat acceptables."
    )


def _optimizer_rule(candidate: dict[str, Any], mode: str) -> str:
    if is_external_etf_allocation_candidate(candidate):
        return f"allocation ETF externe ({mode}) + score ETF par mode + plafond de nouvelle position"
    if str(candidate.get("universe") or "") in EXTERNAL_ALLOCATION_UNIVERSES:
        return f"allocation externe automatique ({mode}) + filtres stricts + validation manuelle avant achat réel"
    if candidate.get("_high_cagr_overflow_used"):
        return "optimisation mensuelle high-CAGR + plafonnement redirection VFV"
    if candidate.get("quality_drawdown_status") == "QUALITY_DRAWDOWN_OPPORTUNITY":
        return "optimisation mensuelle + quality drawdown opportunity + garde-fous fondamentaux"
    if candidate.get("cycle_bubble_risk_level") in {"HIGH", "EXTREME"}:
        return "optimisation mensuelle + garde-fou cycle/bulle/tendance"
    if (safe_float(candidate.get("_quality_diversifier_bonus")) or 0.0) > 0:
        return "optimisation mensuelle + diversificateur de qualité"
    if (safe_float(candidate.get("allocation_stability_adjustment")) or 0.0) > 0:
        return "optimisation mensuelle + stabilité modérée"
    if _has_poor_free_data_coverage(candidate):
        return "optimisation mensuelle + garde-fou couverture gratuite"
    if candidate.get("winner_accelerated"):
        return "optimisation mensuelle + Winner accéléré + drift rule"
    if candidate.get("add_eligibility_status") == "ADD_ALLOWED_SMALL" and _is_starter_core_candidate(candidate):
        return "optimisation mensuelle high-CAGR + position de démarrage + achat limité en zone jaune"
    if candidate.get("add_eligibility_status") == "ADD_ALLOWED_SMALL":
        return "optimisation mensuelle + achat limité en zone jaune"
    if mode == "high-cagr":
        return "optimisation mensuelle high-CAGR + plafonds de concentration"
    return "optimisation mensuelle + plafonds de concentration"


def _defensive_fallback_rows(
    amount_to_allocate: float,
    total_capital: float,
    mode: str,
    defensive_etf_candidates: list[dict[str, Any]],
    reason: str,
    already_allocated: float = 0.0,
) -> tuple[list[dict[str, Any]], float]:
    if mode == "high-cagr":
        return [], 0.0
    max_total = round(max(0.0, total_capital * defensive_mode_limit(mode) - already_allocated), 2)
    if max_total <= 0 or amount_to_allocate <= 0:
        return [], 0.0
    eligible = [
        row
        for row in defensive_etf_candidates
        if row.get("enabled_for_mode") is True
        and row.get("status") == "ELIGIBLE_DEFENSIVE_FALLBACK"
        and row.get("selected_for_allocation") is True
    ]
    if not eligible:
        return [], 0.0

    remaining = round(min(amount_to_allocate, max_total), 2)
    rows = []
    for candidate in sorted(eligible, key=lambda row: safe_float(row.get("defensive_score")) or 0.0, reverse=True):
        if remaining <= 0.01:
            break
        ticker = str(candidate.get("ticker") or "").strip().upper()
        if not ticker:
            continue
        single_limit = total_capital * (safe_float(candidate.get("max_single_allocation_pct")) or defensive_mode_limit(mode))
        amount = round(min(remaining, single_limit), 2)
        if amount <= 0.01:
            continue
        rows.append(
            _allocation_row(
                ticker,
                amount,
                total_capital,
                "Defensive ETF fallback",
                candidate.get("defensive_score"),
                f"{reason} {candidate.get('reason')}",
                f"defensive ETF fallback ({mode}) + plafond par mode",
                "MEDIUM" if mode == "rational-aggressive" else "HIGH",
            )
        )
        remaining = round(remaining - amount, 2)

    used = round(sum(safe_float(row.get("montant")) or 0.0 for row in rows), 2)
    return rows, used


def _allocation_row(
    destination: str,
    amount: float,
    total_capital: float,
    block: str,
    capital_allocation_score: Any,
    reason: str,
    rule: str,
    confidence: str,
) -> dict[str, Any]:
    return {
        "destination": destination,
        "montant": round(amount, 2),
        "pourcentage": amount / total_capital if total_capital > 0 else 0.0,
        "bloc": block,
        "capital_allocation_score": capital_allocation_score,
        "raison": reason,
        "règle appliquée": rule,
        "niveau de confiance": confidence,
    }


def _allocation_reason(candidate: dict[str, Any]) -> str:
    if candidate.get("winner_accelerated"):
        return "Winner accéléré avec thèse intacte et avantage clair face à VFV."
    score = safe_float(candidate.get("capital_allocation_score")) or 0.0
    if score >= 80:
        return "Très bon capital_allocation_score avec garde-fous respectés."
    if score >= 70:
        return "Allocation normale permise par le score et la thèse."
    return "Allocation réduite seulement; score acceptable mais pas dominant."


def _rule_for_candidate(candidate: dict[str, Any]) -> str:
    if candidate.get("winner_accelerated"):
        return "Winner accéléré + drift rule"
    if candidate.get("opportunity_cost_status") == "CLEARLY_BETTER_THAN_VFV":
        return "meilleur score vs VFV + sizing"
    return "allocation limitée + cash rule"


def _allocation_confidence(candidate: dict[str, Any]) -> str:
    confidence = str(candidate.get("confidence_level") or "MEDIUM").upper()
    reliability = str(candidate.get("data_reliability_level") or confidence).upper()
    if candidate.get("requires_manual_validation_for_large_allocation"):
        reliability = "MEDIUM" if reliability == "HIGH" else reliability
    ranks = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
    labels = {0: "LOW", 1: "MEDIUM", 2: "HIGH"}
    return labels[min(ranks.get(confidence, 1), ranks.get(reliability, 1))]


def _is_starter_core_candidate(candidate: dict[str, Any]) -> bool:
    shares = safe_float(candidate.get("shares"))
    return (
        candidate.get("universe", "CORE_PORTFOLIO") == "CORE_PORTFOLIO"
        and (shares is None or shares <= 0)
        and (safe_float(candidate.get("current_value")) or 0.0) <= 0
        and (safe_float(candidate.get("position_weight")) or 0.0) <= 0
    )


def _is_watch_limited(candidate: dict[str, Any]) -> bool:
    return str(candidate.get("monitoring_status") or "NORMAL") in {"WATCH", "MANUAL_REVIEW"}


def _quality_drawdown_allocation_exception(analysis: dict[str, Any], mode: str) -> bool:
    if str(analysis.get("quality_drawdown_status") or "") != "QUALITY_DRAWDOWN_OPPORTUNITY":
        return False
    if mode not in {"high-cagr", "rational-aggressive", "family-office"}:
        return False
    if str(analysis.get("expected_cagr_quality") or "") not in {"MEDIUM", "HIGH", "VERY_HIGH"}:
        return False
    if str(analysis.get("opportunity_cost_status") or "") == "WORSE_THAN_VFV":
        return False
    if str(analysis.get("news_context_status") or "") in {
        "FUNDAMENTAL_DETERIORATION_REPORTED",
        "REGULATORY_OR_LEGAL_RISK_REPORTED",
    }:
        return False
    if analysis.get("quality_but_too_expensive") is True:
        return False
    threshold = 78.0 + tuning_value(mode, "quality_drawdown_score_adjustment", 0.0)
    if (safe_float(analysis.get("quality_drawdown_score")) or 0.0) < threshold:
        return False
    if (safe_float(analysis.get("conviction_score")) or 0.0) < 80:
        return False
    if (safe_float(analysis.get("business_quality_score")) or 0.0) < 75:
        return False
    if (safe_float(analysis.get("long_term_durability_score")) or 0.0) < 75:
        return False
    return True


def _watch_allocation_budget(capital: float, mode: str) -> float:
    fraction = WATCH_ALLOCATION_BUDGETS.get(mode, WATCH_ALLOCATION_BUDGETS["rational-aggressive"])
    return round(max(0.0, capital * fraction), 2)


def _watch_allocated_total(
    allocations_by_ticker: dict[str, float],
    candidate_lookup: dict[str, dict[str, Any]],
) -> float:
    total = 0.0
    for ticker, amount in allocations_by_ticker.items():
        candidate = candidate_lookup.get(ticker)
        if candidate and _is_watch_limited(candidate):
            total += safe_float(amount) or 0.0
    return round(total, 2)


def _watch_budget_room(
    candidate: dict[str, Any],
    allocations_by_ticker: dict[str, float],
    candidate_lookup: dict[str, dict[str, Any]],
    capital: float,
    mode: str,
) -> float:
    if not _is_watch_limited(candidate):
        return capital
    budget = _watch_allocation_budget(capital, mode)
    used = _watch_allocated_total(allocations_by_ticker, candidate_lookup)
    return round(max(0.0, budget - used), 2)


def _external_allocation_budget(capital: float, mode: str) -> float:
    fraction = EXTERNAL_ALLOCATION_BUDGETS.get(mode, 0.0)
    return round(max(0.0, capital * fraction), 2)


def _external_individual_cap_fraction(mode: str) -> float:
    return EXTERNAL_INDIVIDUAL_CAPS.get(mode, 0.0)


def _external_allocated_total(
    allocations_by_ticker: dict[str, float],
    candidate_lookup: dict[str, dict[str, Any]],
) -> float:
    total = 0.0
    for ticker, amount in allocations_by_ticker.items():
        candidate = candidate_lookup.get(ticker)
        if candidate and _is_external_candidate(candidate):
            total += safe_float(amount) or 0.0
    return round(total, 2)


def _external_budget_room(
    candidate: dict[str, Any],
    allocations_by_ticker: dict[str, float],
    candidate_lookup: dict[str, dict[str, Any]],
    capital: float,
    mode: str,
) -> float:
    if not _is_external_candidate(candidate):
        return capital
    already_allocated = allocations_by_ticker.get(candidate["ticker"], 0.0)
    total_room = _external_allocation_budget(capital, mode) - _external_allocated_total(allocations_by_ticker, candidate_lookup)
    individual_room = capital * _external_individual_cap_fraction(mode) - already_allocated
    return round(max(0.0, min(total_room, individual_room)), 2)


def _cycle_risk_level(candidate: dict[str, Any]) -> str:
    return str(candidate.get("cycle_bubble_risk_level") or "").upper()


def _cycle_allocation_budget(capital: float, mode: str) -> float:
    fraction = CYCLE_ALLOCATION_BUDGETS.get(mode, CYCLE_ALLOCATION_BUDGETS["rational-aggressive"])
    fraction += tuning_value(mode, "cycle_budget_adjustment", 0.0)
    max_fraction = 0.55 if mode == "high-cagr" else 0.40 if mode == "rational-aggressive" else 0.30 if mode == "family-office" else 0.12
    fraction = clamp(fraction, 0.0, max_fraction)
    return round(max(0.0, capital * fraction), 2)


def _cycle_individual_cap_fraction(candidate: dict[str, Any], mode: str) -> float:
    level = _cycle_risk_level(candidate)
    caps = CYCLE_INDIVIDUAL_CAPS.get(mode, CYCLE_INDIVIDUAL_CAPS["rational-aggressive"])
    base = caps.get(level, 1.0)
    if level not in CYCLE_SENSITIVE_LEVELS:
        return base
    return round(clamp(base + tuning_value(mode, "cycle_individual_cap_adjustment", 0.0), 0.0, 0.35), 4)


def _cycle_allocated_total(
    allocations_by_ticker: dict[str, float],
    candidate_lookup: dict[str, dict[str, Any]],
) -> float:
    total = 0.0
    for ticker, amount in allocations_by_ticker.items():
        candidate = candidate_lookup.get(ticker)
        if candidate and _cycle_risk_level(candidate) in CYCLE_SENSITIVE_LEVELS:
            total += safe_float(amount) or 0.0
    return round(total, 2)


def _cycle_budget_should_apply(candidate_lookup: dict[str, dict[str, Any]], mode: str) -> bool:
    has_cycle_sensitive_candidate = any(
        _cycle_risk_level(candidate) in CYCLE_SENSITIVE_LEVELS for candidate in candidate_lookup.values()
    )
    if not has_cycle_sensitive_candidate:
        return False
    return any(_is_cycle_diversifying_candidate(candidate, mode) for candidate in candidate_lookup.values())


def _is_cycle_diversifying_candidate(candidate: dict[str, Any], mode: str) -> bool:
    if _cycle_risk_level(candidate) in CYCLE_SENSITIVE_LEVELS:
        return False
    score = safe_float(candidate.get("capital_allocation_score")) or 0.0
    minimum_score = 55 if mode == "high-cagr" else 60
    if score < minimum_score:
        return False
    if candidate.get("expected_cagr_quality") not in {"HIGH", "VERY_HIGH"}:
        return False
    if candidate.get("thesis_status") != "INTACT":
        return False
    if candidate.get("liquidation_status") not in {"GREEN", "YELLOW"}:
        return False
    if candidate.get("opportunity_cost_status") == "WORSE_THAN_VFV":
        return False
    if _has_poor_free_data_coverage(candidate):
        return False
    return True


def _cycle_budget_room(
    candidate: dict[str, Any],
    allocations_by_ticker: dict[str, float],
    candidate_lookup: dict[str, dict[str, Any]],
    capital: float,
    mode: str,
) -> float:
    if _cycle_risk_level(candidate) not in CYCLE_SENSITIVE_LEVELS:
        return capital
    if not _cycle_budget_should_apply(candidate_lookup, mode):
        return capital

    already_allocated = allocations_by_ticker.get(candidate["ticker"], 0.0)
    total_room = _cycle_allocation_budget(capital, mode) - _cycle_allocated_total(allocations_by_ticker, candidate_lookup)
    individual_room = (capital * _cycle_individual_cap_fraction(candidate, mode)) - already_allocated
    return round(max(0.0, min(total_room, individual_room)), 2)


def _quality_diversifier_bonus(
    candidate: dict[str, Any],
    allocations_by_ticker: dict[str, float],
    candidate_lookup: dict[str, dict[str, Any]],
    mode: str,
) -> float:
    if not _is_quality_diversifier_candidate(candidate, mode):
        return 0.0
    if not _is_close_to_best_candidate(candidate, candidate_lookup, mode):
        return 0.0

    allocated_total = sum(safe_float(amount) or 0.0 for amount in allocations_by_ticker.values())
    cycle_allocated = _cycle_allocated_total(allocations_by_ticker, candidate_lookup)
    has_cycle_pressure = any(
        _cycle_risk_level(row) in CYCLE_SENSITIVE_LEVELS for row in candidate_lookup.values() if row is not candidate
    )

    bonus = 0.0
    if has_cycle_pressure:
        bonus += 1.0
    if allocated_total > 0 and cycle_allocated / allocated_total >= 0.35:
        bonus += 2.0
    if allocated_total > 0 and _candidate_adds_underrepresented_sector(candidate, allocations_by_ticker, candidate_lookup):
        bonus += 1.0
    if _is_hot_growth_theme(candidate):
        bonus *= 0.50

    max_bonus = 5.0 if mode == "high-cagr" else 3.5
    bonus = round(min(max_bonus, bonus), 2)
    if bonus > 0:
        previous_bonus = safe_float(candidate.get("_quality_diversifier_bonus")) or 0.0
        candidate["_quality_diversifier_bonus"] = max(previous_bonus, bonus)
    return bonus


def _is_quality_diversifier_candidate(candidate: dict[str, Any], mode: str) -> bool:
    if _cycle_risk_level(candidate) in CYCLE_SENSITIVE_LEVELS:
        return False
    score_total = safe_float(candidate.get("score_total")) or 0.0
    conviction = safe_float(candidate.get("conviction_score")) or 0.0
    capital_score = safe_float(candidate.get("capital_allocation_score")) or 0.0
    minimum_capital_score = 70.0 if mode == "high-cagr" else 72.0
    if score_total < 8.0 or conviction < 85 or capital_score < minimum_capital_score:
        return False
    if candidate.get("expected_cagr_quality") not in {"HIGH", "VERY_HIGH"}:
        return False
    if candidate.get("thesis_status") != "INTACT":
        return False
    if candidate.get("liquidation_status") != "GREEN":
        return False
    if candidate.get("opportunity_cost_status") != "CLEARLY_BETTER_THAN_VFV":
        return False
    if candidate.get("quality_but_too_expensive") is True:
        return False
    if candidate.get("data_reliability_level") == "LOW":
        return False
    if not _has_known_diversifier_context(candidate):
        return False
    if _is_hot_growth_theme(candidate):
        return False
    durability = str(candidate.get("long_term_durability_status") or "")
    business_quality = safe_float(candidate.get("business_quality_score"))
    return durability == "VERY_DURABLE_COMPOUNDER" or (business_quality is not None and business_quality >= 85)


def _is_close_to_best_candidate(
    candidate: dict[str, Any],
    candidate_lookup: dict[str, dict[str, Any]],
    mode: str,
) -> bool:
    candidate_score = safe_float(candidate.get("capital_allocation_score")) or 0.0
    eligible_scores = [
        safe_float(row.get("capital_allocation_score")) or 0.0
        for row in candidate_lookup.values()
        if row.get("ticker") != "VFV.TO"
    ]
    if not eligible_scores:
        return False
    best_score = max(eligible_scores)
    window = QUALITY_DIVERSIFIER_SCORE_WINDOW.get(mode, QUALITY_DIVERSIFIER_SCORE_WINDOW["rational-aggressive"])
    return best_score - candidate_score <= window


def _candidate_adds_underrepresented_sector(
    candidate: dict[str, Any],
    allocations_by_ticker: dict[str, float],
    candidate_lookup: dict[str, dict[str, Any]],
) -> bool:
    candidate_sector = _sector_key(candidate)
    if not candidate_sector:
        return False
    sector_allocations: dict[str, float] = {}
    total = 0.0
    for ticker, amount in allocations_by_ticker.items():
        other = candidate_lookup.get(ticker)
        if not other:
            continue
        sector = _sector_key(other)
        amount_float = safe_float(amount) or 0.0
        total += amount_float
        if sector:
            sector_allocations[sector] = sector_allocations.get(sector, 0.0) + amount_float
    if total <= 0:
        return False
    return sector_allocations.get(candidate_sector, 0.0) / total < 0.20


def _sector_key(candidate: dict[str, Any]) -> str:
    sector = str(candidate.get("sector") or "").strip().lower()
    return "" if sector in {"", "unknown", "none"} else sector


def _has_known_diversifier_context(candidate: dict[str, Any]) -> bool:
    if _sector_key(candidate):
        return True
    factors = candidate.get("factor_exposure") or []
    if isinstance(factors, str):
        return bool(factors.strip())
    return any(str(item).strip() for item in factors)


def _is_hot_growth_theme(candidate: dict[str, Any]) -> bool:
    sector = str(candidate.get("sector") or "")
    factors = candidate.get("factor_exposure") or []
    if isinstance(factors, str):
        factors_text = factors
    else:
        factors_text = " ".join(str(item) for item in factors)
    text = f"{sector} {factors_text}".lower()
    return any(term in text for term in HOT_GROWTH_THEME_TERMS)


def _has_poor_free_data_coverage(candidate: dict[str, Any]) -> bool:
    validation = str(candidate.get("ticker_validation_status") or "")
    if validation in {"NO_MARKET_DATA", "POSSIBLE_WRONG_TICKER"}:
        return False
    coverage_class = str(candidate.get("free_data_coverage_class") or "")
    coverage_status = str(candidate.get("ticker_coverage_status") or "")
    if coverage_class != "VALID_TICKER_POOR_FREE_COVERAGE" and coverage_status not in {
        "LOW_FREE_DATA_COVERAGE",
        "NEEDS_BNCD_OR_MANUAL_CONFIRMATION",
    }:
        return False
    confirmed_fields = len(candidate.get("manual_override_fields") or []) + len(candidate.get("research_report_fields") or [])
    return confirmed_fields < 3


def _cycle_allocation_multiplier(candidate: dict[str, Any]) -> float:
    multiplier = safe_float(candidate.get("cycle_bubble_allocation_multiplier"))
    if multiplier is None:
        return 1.0
    return max(0.20, min(multiplier, 1.0))


def _finalize_allocations(
    capital: float,
    allocations: list[dict[str, Any]],
    average_score: float | None,
    vfv_pct: float,
    allocation_log: list[str],
) -> dict[str, Any]:
    total = round(sum(safe_float(row.get("montant")) or 0.0 for row in allocations), 2)
    difference = round(capital - total, 2)
    if abs(difference) > 0.01:
        allocations.append(
            _allocation_row(
                "VFV.TO",
                difference,
                capital,
                "Ajustement final",
                100,
                "Ajustement d’arrondi pour totaliser 100 % du capital disponible.",
                "cash rule",
                "HIGH",
            )
        )
    allocations = _consolidate_allocations(allocations, capital)
    return {
        "average_score_ex_vfv": average_score,
        "mandatory_vfv_percent": vfv_pct,
        "allocations": allocations,
        "allocation_log": allocation_log,
    }


def _consolidate_allocations(allocations: list[dict[str, Any]], capital: float) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for row in allocations:
        ticker = str(row.get("destination") or "")
        amount = safe_float(row.get("montant")) or 0.0
        if not ticker or amount <= 0:
            continue
        if ticker not in grouped:
            grouped[ticker] = {
                **row,
                "montant": 0.0,
                "_reasons": [],
                "_rules": [],
                "_blocks": [],
            }
            order.append(ticker)
        grouped[ticker]["montant"] += amount
        for source, target in [
            ("raison", "_reasons"),
            ("règle appliquée", "_rules"),
            ("bloc", "_blocks"),
        ]:
            value = str(row.get(source) or "").strip()
            if value and value not in grouped[ticker][target]:
                grouped[ticker][target].append(value)

    rows = []
    for ticker in order:
        row = grouped[ticker]
        amount = round(safe_float(row.get("montant")) or 0.0, 2)
        row["montant"] = amount
        row["pourcentage"] = amount / capital if capital > 0 else 0.0
        row["raison"] = " | ".join(row.pop("_reasons"))
        row["règle appliquée"] = " | ".join(row.pop("_rules"))
        row["bloc"] = " | ".join(row.pop("_blocks"))
        rows.append(row)
    return rows
