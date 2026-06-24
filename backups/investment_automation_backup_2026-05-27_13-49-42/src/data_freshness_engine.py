from __future__ import annotations

from datetime import datetime
from typing import Any

from .utils import clamp, safe_float


FRESHNESS_RANK = {
    "FRESH": 0,
    "NO_REPORT": 0,
    "RECENT": 0,
    "AGING": 1,
    "UNKNOWN_DATE": 2,
    "STALE_CACHE": 2,
    "STALE": 3,
    "VERY_STALE": 4,
    "UNAVAILABLE": 4,
}


def compute_market_data_freshness(payload: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now()
    source = str(payload.get("source") or "unknown").strip() or "unknown"
    fetched_at = str(payload.get("fetched_at") or "").strip()
    fetched_datetime = _parse_datetime(fetched_at)
    age_hours = None
    if fetched_datetime is not None:
        age_hours = max(0.0, (now - fetched_datetime.replace(tzinfo=None)).total_seconds() / 3600)
    has_price = safe_float(payload.get("current_price")) is not None
    stale_warning = str(payload.get("stale_cache_warning") or "").strip()

    if source in {"unavailable", "empty"} or not has_price:
        return _market_result(
            level="UNAVAILABLE",
            source=source,
            fetched_at=fetched_at or None,
            age_hours=age_hours,
            penalty=25.0,
            requires_refresh=True,
            reason="Prix actuel indisponible: l’analyse continue, mais cette ligne doit être validée avant décision importante.",
            stale_warning=stale_warning,
        )
    if source == "stale_cache":
        if age_hours is not None and age_hours > 720:
            return _market_result(
                "VERY_STALE",
                source,
                fetched_at,
                age_hours,
                22.0,
                True,
                "Cache de marché très ancien: relancer avec --refresh-market-data et valider le ticker.",
                stale_warning,
            )
        if age_hours is not None and age_hours > 168:
            return _market_result(
                "STALE",
                source,
                fetched_at,
                age_hours,
                14.0,
                True,
                "Cache de marché ancien: relancer avec --refresh-market-data avant grosse allocation.",
                stale_warning,
            )
        return _market_result(
            "STALE_CACHE",
            source,
            fetched_at,
            age_hours,
            3.0,
            True,
            "Données de marché servies depuis un cache non rafraîchi: prudence avant décision importante.",
            stale_warning,
        )
    if age_hours is None:
        return _market_result(
            "UNKNOWN_DATE",
            source,
            None,
            None,
            6.0,
            True,
            "Date de récupération du prix inconnue: fraîcheur à valider avant grosse allocation.",
            stale_warning,
        )
    if age_hours <= 36:
        return _market_result(
            "FRESH",
            source,
            fetched_at,
            age_hours,
            0.0,
            False,
            "Données de marché récentes.",
            stale_warning,
        )
    if age_hours <= 168:
        return _market_result(
            "AGING",
            source,
            fetched_at,
            age_hours,
            3.0,
            False,
            "Données de marché un peu vieillissantes, mais encore utilisables pour une analyse long terme.",
            stale_warning,
        )
    if age_hours <= 720:
        return _market_result(
            "STALE",
            source,
            fetched_at,
            age_hours,
            7.0,
            True,
            "Données de marché vieilles de plus d’une semaine: rafraîchissement recommandé.",
            stale_warning,
        )
    return _market_result(
        "VERY_STALE",
        source,
        fetched_at,
        age_hours,
        20.0,
        True,
        "Données de marché vieilles de plus d’un mois: validation fraîche requise.",
        stale_warning,
    )


def apply_market_freshness_to_reliability(
    reliability: dict[str, Any],
    market_freshness: dict[str, Any],
) -> dict[str, Any]:
    adjusted = dict(reliability)
    penalty = safe_float(market_freshness.get("market_data_freshness_penalty")) or 0.0
    current_score = safe_float(adjusted.get("data_reliability_score")) or 0.0
    if penalty:
        new_score = round(clamp(current_score - penalty, 0, 100), 2)
        adjusted["data_reliability_score"] = new_score
        adjusted["data_reliability_level"] = _reliability_level(new_score)
        reasons = list(adjusted.get("data_reliability_reasons") or [])
        reasons.append(str(market_freshness.get("market_data_freshness_reason")))
        adjusted["data_reliability_reasons"] = reasons

    if market_freshness.get("market_data_requires_refresh"):
        adjusted["requires_manual_validation_for_large_allocation"] = True

    adjusted.update(market_freshness)
    adjusted.update(compute_overall_data_freshness(adjusted))
    return adjusted


def compute_overall_data_freshness(analysis_or_reliability: dict[str, Any]) -> dict[str, Any]:
    market_level = str(analysis_or_reliability.get("market_data_freshness_level") or "UNKNOWN_DATE")
    research_level = str(analysis_or_reliability.get("research_report_freshness_level") or "NO_REPORT")
    worst_rank = max(FRESHNESS_RANK.get(market_level, 2), FRESHNESS_RANK.get(research_level, 0))
    requires_refresh = bool(
        analysis_or_reliability.get("market_data_requires_refresh")
        or analysis_or_reliability.get("research_report_requires_fresh_validation")
    )

    if worst_rank >= 4:
        level = "CRITICAL_REFRESH_NEEDED"
        action = "Rafraîchir les données ou valider manuellement avant décision importante."
    elif worst_rank == 3:
        level = "STALE_REFRESH_RECOMMENDED"
        action = "Relancer avec --refresh-market-data ou valider la source avant grosse allocation."
    elif worst_rank == 2 or requires_refresh:
        level = "WATCH_FRESHNESS"
        action = "Analyse utilisable, mais fraîcheur à vérifier avant grosse allocation."
    elif worst_rank == 1:
        level = "OK_BUT_AGING"
        action = "Analyse utilisable; rafraîchissement utile si la décision est importante."
    else:
        level = "FRESH_ENOUGH"
        action = "Fraîcheur suffisante pour une analyse mécanique."

    return {
        "overall_data_freshness_level": level,
        "data_freshness_action": action,
    }


def _market_result(
    level: str,
    source: str,
    fetched_at: str | None,
    age_hours: float | None,
    penalty: float,
    requires_refresh: bool,
    reason: str,
    stale_warning: str,
) -> dict[str, Any]:
    return {
        "market_data_source": source,
        "market_data_fetched_at": fetched_at,
        "market_data_age_hours": round(age_hours, 2) if age_hours is not None else None,
        "market_data_age_days": round(age_hours / 24, 2) if age_hours is not None else None,
        "market_data_freshness_level": level,
        "market_data_freshness_penalty": penalty,
        "market_data_requires_refresh": requires_refresh,
        "market_data_freshness_reason": reason,
        "market_data_stale_cache_warning": stale_warning,
    }


def _parse_datetime(value: str) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    for candidate in (text, text.replace("Z", "+00:00")):
        try:
            return datetime.fromisoformat(candidate)
        except ValueError:
            continue
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text[:19], fmt)
        except ValueError:
            continue
    return None


def _reliability_level(score: float) -> str:
    if score >= 80:
        return "HIGH"
    if score >= 60:
        return "MEDIUM"
    return "LOW"
