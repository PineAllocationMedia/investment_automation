from __future__ import annotations

from pathlib import Path
from typing import Any

from .canadian_data_fetcher import SEDARPLUS_SOURCE_NAME, STOCKANALYSIS_SOURCE_NAME, TMX_SOURCE_NAME, canadian_ticker_metadata
from .source_conflict_engine import summarize_conflict_profile
from .utils import clamp, read_csv_records, safe_float, today_iso, write_csv_records


SOURCE_HEALTH_COLUMNS = [
    "source",
    "status",
    "health_score",
    "coverage_rate",
    "freshness_rate",
    "availability_rate",
    "avg_latency_ms",
    "affected_ticker_count",
    "affected_tickers",
    "conflict_count",
    "critical_gap_count",
    "confirmed_field_rate",
    "partial_coverage_count",
    "critical_stale_count",
    "audit_signal",
    "ticker_count",
    "trend",
    "action",
    "notes",
]

SOURCE_HEALTH_HISTORY_COLUMNS = ["date", "mode", *SOURCE_HEALTH_COLUMNS]

BAD_MARKET_LEVELS = {"UNAVAILABLE", "VERY_STALE", "STALE", "UNKNOWN_DATE"}
GOOD_MARKET_LEVELS = {"FRESH", "AGING", "STALE_CACHE"}
CORE_AUTO_TUNING_SOURCES = {"Yahoo/yfinance market data"}
CANADIAN_SOURCE_CACHE_PREFIXES = {
    "stockanalysis_": "stockanalysis",
    "tmx_": "tmx",
    "sedarplus_": "sedarplus",
}
CANADIAN_SOURCE_RECENT_FILE_HOURS = 168
CANADIAN_SOURCE_HEALTHY_SUCCESS_RATE = 50.0
CANADIAN_SOURCE_HEALTHY_SUCCESS_HOURS = 72


def check_canadian_source_health(cache_dir: str | Path) -> dict[str, Any]:
    source_dir = Path(cache_dir)
    if source_dir.name != "canadian_sources":
        source_dir = source_dir / "canadian_sources"
    stats = {
        key: {
            "attempted_files": 0,
            "available_files": 0,
            "success_rate_percent": 0.0,
            "latest_fetch_at": "",
            "latest_success_fetched_at": "",
            "latest_success_age_hours": "",
        }
        for key in CANADIAN_SOURCE_CACHE_PREFIXES.values()
    }
    try:
        if not source_dir.exists():
            return _canadian_source_health_result("DEAD", False, stats, str(source_dir), False)

        recent_file_exists = False
        for path in source_dir.glob("*.json"):
            source = _canadian_source_from_cache_name(path.name)
            if not source:
                continue
            payload = _read_json_silently(path)
            fetched_at = _canadian_cache_fetched_at(payload)
            fetched_age = _age_hours_from_iso(fetched_at)
            if fetched_age is not None and fetched_age < CANADIAN_SOURCE_RECENT_FILE_HOURS:
                recent_file_exists = True
            available = _canadian_cache_available(payload)
            row = stats[source]
            row["attempted_files"] += 1
            if _is_more_recent_fetch(fetched_at, str(row.get("latest_fetch_at") or "")):
                row["latest_fetch_at"] = fetched_at
            if available:
                row["available_files"] += 1
                if fetched_age is not None:
                    current_success_age = safe_float(row.get("latest_success_age_hours"))
                    if current_success_age is None or fetched_age < current_success_age:
                        row["latest_success_age_hours"] = round(fetched_age, 2)
                        row["latest_success_fetched_at"] = fetched_at

        for row in stats.values():
            attempted = int(safe_float(row.get("attempted_files")) or 0)
            available = int(safe_float(row.get("available_files")) or 0)
            row["success_rate_percent"] = round((available / attempted) * 100, 1) if attempted else 0.0

        if not recent_file_exists:
            return _canadian_source_health_result("DEAD", False, stats, str(source_dir), recent_file_exists)
        healthy = any(_canadian_source_is_healthy(row) for row in stats.values())
        if healthy:
            return _canadian_source_health_result("HEALTHY", True, stats, str(source_dir), recent_file_exists)
        any_recent_success = any(_canadian_source_has_recent_success(row) for row in stats.values())
        if any_recent_success:
            return _canadian_source_health_result("DEGRADED", True, stats, str(source_dir), recent_file_exists)
        return _canadian_source_health_result("DEAD", False, stats, str(source_dir), recent_file_exists)
    except Exception:
        return _canadian_source_health_result("DEAD", False, stats, str(source_dir), False)


def build_source_health_rows(
    analysis_groups: dict[str, dict[str, dict[str, Any]]],
    *,
    mode: str,
    history_rows: list[dict[str, Any]] | None = None,
    date: str | None = None,
) -> list[dict[str, Any]]:
    rows = _flatten(analysis_groups)
    history_rows = history_rows or []
    date = date or today_iso()
    output = [
        _market_data_health(rows),
        _official_data_health(rows),
        _canadian_source_health(rows, SEDARPLUS_SOURCE_NAME),
        _canadian_source_health(rows, TMX_SOURCE_NAME),
        _canadian_source_health(rows, STOCKANALYSIS_SOURCE_NAME),
        _research_report_health(rows),
        _news_context_health(rows),
        _auto_proxy_health(rows),
    ]
    previous_by_source = _latest_history_by_source(history_rows, mode, before_date=date)
    for row in output:
        previous = previous_by_source.get(str(row.get("source") or ""))
        row["trend"] = _trend_text(row, previous)
    return output


def update_source_health_history(
    path: str | Path,
    rows: list[dict[str, Any]],
    *,
    mode: str,
    date: str | None = None,
    max_rows: int = 750,
) -> list[dict[str, Any]]:
    path = Path(path)
    date = date or today_iso()
    existing = read_csv_records(path)
    cleaned = [
        row
        for row in existing
        if not (row.get("date") == date and row.get("mode") == mode and row.get("source") in {item.get("source") for item in rows})
    ]
    additions = [{**row, "date": date, "mode": mode} for row in rows]
    combined = [*cleaned, *additions][-max_rows:]
    write_csv_records(path, combined, SOURCE_HEALTH_HISTORY_COLUMNS)
    return combined


def source_health_summary(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "Aucune donnée de santé des sources disponible."
    worst = sorted(rows, key=lambda row: safe_float(row.get("health_score")) or 0.0)[0]
    degraded = [row for row in rows if str(row.get("status")) in {"WATCH", "DEGRADED", "CRITICAL"}]
    if not degraded:
        return "Sources OK: aucune dégradation importante détectée."
    return (
        f"{len(degraded)} source(s) à surveiller; point le plus faible: "
        f"{worst.get('source')} ({worst.get('status')}, {worst.get('health_score')}/100)."
    )


def compact_source_health_rows(rows: list[dict[str, Any]], limit: int = 6) -> list[dict[str, Any]]:
    sorted_rows = sorted(rows, key=lambda row: safe_float(row.get("health_score")) or 0.0)
    return [
        {
            "source": row.get("source"),
            "statut": row.get("status"),
            "score": row.get("health_score"),
            "tendance": row.get("trend"),
            "action": row.get("action"),
        }
        for row in sorted_rows[:limit]
    ]


def source_health_audit_context(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "source_health_status": "UNKNOWN",
            "source_health_score": 60.0,
            "source_health_weakest_source": "N/D",
            "source_health_auto_tuning_gate": "REVIEW_ONLY",
            "source_health_interpretation": "Aucun rapport de santé des sources disponible; l’audit reste utilisable mais ne devrait pas auto-ajuster agressivement.",
            "source_health_degraded_sources": "",
        }

    sorted_rows = sorted(rows, key=lambda row: safe_float(row.get("health_score")) or 0.0)
    weakest = sorted_rows[0]
    weakest_score = round(safe_float(weakest.get("health_score")) or 0.0, 1)
    critical = [row for row in rows if str(row.get("status") or "").upper() == "CRITICAL"]
    degraded = [row for row in rows if str(row.get("status") or "").upper() in {"WATCH", "DEGRADED", "CRITICAL"}]
    core_critical = [
        row
        for row in critical
        if str(row.get("source") or "") in CORE_AUTO_TUNING_SOURCES
        and (safe_float(row.get("health_score")) or 0.0) < 50
    ]

    if core_critical or len(critical) >= 2:
        status = "CRITICAL_BLOCK"
        gate = "BLOCK"
        interpretation = (
            "Une source centrale est critique; l’audit peut informer, mais l’application automatique de tuning est bloquée "
            "jusqu’à rafraîchissement ou validation."
        )
    elif critical or any(str(row.get("status") or "").upper() == "DEGRADED" for row in degraded):
        status = "WATCH_SOURCE_QUALITY"
        gate = "PASS_WITH_CAUTION"
        interpretation = (
            "Certaines sources ou proxys sont faibles; l’audit peut continuer, mais les conclusions doivent être lues avec prudence."
        )
    elif degraded:
        status = "WATCH"
        gate = "PASS"
        interpretation = "Quelques sources sont à surveiller, sans bloquer l’audit ni le tuning prudent."
    else:
        status = "OK"
        gate = "PASS"
        interpretation = "Les sources semblent suffisamment saines pour soutenir l’audit."

    return {
        "source_health_status": status,
        "source_health_score": weakest_score,
        "source_health_weakest_source": weakest.get("source") or "N/D",
        "source_health_auto_tuning_gate": gate,
        "source_health_interpretation": interpretation,
        "source_health_degraded_sources": ", ".join(str(row.get("source") or "") for row in degraded[:8]),
        "source_health_partial_coverage_count": sum(int(safe_float(row.get("partial_coverage_count")) or 0) for row in rows),
        "source_health_critical_stale_count": sum(int(safe_float(row.get("critical_stale_count")) or 0) for row in rows),
        "source_health_audit_signal": "; ".join(
            str(row.get("audit_signal") or "")
            for row in rows
            if str(row.get("audit_signal") or "").upper() not in {"", "OK"}
        )[:500],
    }


def source_health_allows_auto_tuning(context: dict[str, Any]) -> bool:
    return str(context.get("source_health_auto_tuning_gate") or "") != "BLOCK"


def _flatten(analysis_groups: dict[str, dict[str, dict[str, Any]]]) -> list[dict[str, Any]]:
    rows = []
    for universe, analyses in analysis_groups.items():
        for row in analyses.values():
            rows.append({**row, "source_health_universe": universe})
    return rows


def _market_data_health(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    bad = []
    fresh = 0
    for row in rows:
        level = str(row.get("market_data_freshness_level") or "").upper()
        has_market_value = _has_market_value(row) or level in GOOD_MARKET_LEVELS
        if level in GOOD_MARKET_LEVELS and has_market_value:
            fresh += 1
        requires_refresh = bool(row.get("market_data_requires_refresh")) and level not in GOOD_MARKET_LEVELS
        if level in BAD_MARKET_LEVELS or requires_refresh or not has_market_value:
            bad.append(_ticker(row))
    coverage_rate = _ratio(total - len(bad), total)
    freshness_rate = _ratio(fresh, total)
    score = 100 * coverage_rate - 25 * _ratio(len(bad), total)
    partial_count = _partial_coverage_count(rows)
    critical_stale = _critical_stale_tickers(rows)
    audit_signal = _audit_signal(partial_count=partial_count, critical_stale_count=len(critical_stale), conflicts=0)
    return _row(
        "Yahoo/yfinance market data",
        score,
        coverage_rate,
        freshness_rate,
        affected=bad,
        action="Relancer avec --refresh-market-data si plusieurs tickers sont vieux ou indisponibles.",
        notes="Prix, historique, SMA, drawdown et métriques de marché.",
        ticker_count=total,
        confirmed_field_rate=_average_confirmed_field_rate(rows),
        partial_coverage_count=partial_count,
        critical_stale_count=len(critical_stale),
        audit_signal=audit_signal,
    )


def _official_data_health(rows: list[dict[str, Any]]) -> dict[str, Any]:
    eligible = [row for row in rows if _looks_sec_eligible(row)]
    confirmed = [row for row in eligible if _has_official_evidence(row)]
    raw_conflicts = sum(int(safe_float(row.get("official_data_conflict_count")) or 0) for row in rows)
    weighted_by_ticker = [_weighted_conflict_score(row) for row in rows]
    weighted_conflicts = sum(weighted_by_ticker)
    material_tickers = sum(1 for value in weighted_by_ticker if value >= 1.5)
    average_weighted_conflict = weighted_conflicts / max(1, len(weighted_by_ticker))
    affected = [_ticker(row) for row in eligible if not _has_official_evidence(row)]
    coverage_rate = _ratio(len(confirmed), len(eligible))
    score = 100 * coverage_rate - min(25, material_tickers * 0.75 + average_weighted_conflict * 3)
    partial_count = _partial_coverage_count(eligible)
    audit_signal = _audit_signal(partial_count=partial_count, critical_stale_count=0, conflicts=material_tickers)
    return _row(
        "SEC/official fundamentals",
        score,
        coverage_rate,
        coverage_rate,
        affected=affected,
        conflicts=material_tickers,
        action="Surveiller surtout les titres US importants sans confirmation officielle ou avec conflits matériels.",
        notes=(
            "Confirme certains champs fondamentaux quand disponible; "
            f"conflits bruts={raw_conflicts}, tickers matériels={material_tickers}, "
            f"score pondéré moyen={average_weighted_conflict:.2f}."
        ),
        ticker_count=len(eligible),
        confirmed_field_rate=_average_confirmed_field_rate(eligible),
        partial_coverage_count=partial_count,
        audit_signal=audit_signal,
    )


def _canadian_source_health(rows: list[dict[str, Any]], source_name: str) -> dict[str, Any]:
    eligible = [row for row in rows if _looks_canadian_eligible(row)]
    attempts: list[dict[str, Any]] = []
    affected: list[str] = []
    latencies: list[float] = []
    conflicts = 0
    for row in eligible:
        entries = row.get("canadian_source_health") or []
        if isinstance(entries, dict):
            entries = [entries]
        if not isinstance(entries, list):
            entries = []
        row_attempts = [entry for entry in entries if isinstance(entry, dict) and str(entry.get("source") or "") == source_name]
        attempts.extend(row_attempts)
        if any(not entry.get("available") for entry in row_attempts):
            affected.append(_ticker(row))
        for entry in row_attempts:
            latency = safe_float(entry.get("latency_ms"))
            if latency is not None:
                latencies.append(latency)
        conflict_text = " | ".join(str(item) for item in row.get("canadian_data_conflicts") or [])
        if source_name in conflict_text:
            conflicts += 1

    if not eligible:
        return _row(
            source_name,
            100,
            1.0,
            1.0,
            availability_rate=1.0,
            avg_latency_ms="",
            action="Aucune action canadienne à vérifier.",
            notes="Source canadienne disponible dans la hiérarchie, non sollicitée ici.",
            ticker_count=0,
        )
    if not attempts:
        return _row(
            source_name,
            90,
            1.0,
            1.0,
            availability_rate=1.0,
            avg_latency_ms="",
            action="Rien à faire: yfinance semble suffisant ou la source canadienne n'a pas été nécessaire.",
            notes="Source canadienne en réserve; elle est surtout utilisée quand les données canadiennes sont incomplètes.",
            ticker_count=len(eligible),
        )

    available_count = sum(1 for entry in attempts if entry.get("available"))
    availability_rate = _ratio(available_count, len(attempts))
    avg_latency_ms = round(sum(latencies) / len(latencies), 1) if latencies else ""
    score = max(70, 100 * availability_rate - min(15, conflicts * 3))
    partial_count = _partial_coverage_count(eligible)
    audit_signal = _audit_signal(partial_count=partial_count, critical_stale_count=0, conflicts=conflicts)
    return _row(
        source_name,
        score,
        availability_rate,
        availability_rate,
        availability_rate=availability_rate,
        avg_latency_ms=avg_latency_ms,
        affected=affected,
        conflicts=conflicts,
        action="Surveiller si plusieurs titres canadiens importants restent non couverts; StockAnalysis demeure le filet de secours.",
        notes="Source canadienne gratuite ajoutée sous yfinance et au-dessus du fallback final lorsque disponible.",
        ticker_count=len(eligible),
        confirmed_field_rate=_average_confirmed_field_rate(eligible),
        partial_coverage_count=partial_count,
        audit_signal=audit_signal,
    )


def _research_report_health(rows: list[dict[str, Any]]) -> dict[str, Any]:
    with_report = [row for row in rows if row.get("research_report_sources")]
    stale = [
        _ticker(row)
        for row in with_report
        if str(row.get("research_report_freshness_level") or "").upper() in {"STALE", "VERY_STALE", "UNKNOWN_DATE"}
        or row.get("research_report_requires_fresh_validation")
    ]
    coverage_rate = _ratio(len(with_report), len(rows))
    freshness_rate = _ratio(len(with_report) - len(stale), len(with_report))
    score = 85 + 15 * freshness_rate - 20 * _ratio(len(stale), max(1, len(with_report)))
    if not with_report:
        score = 82
    partial_count = _partial_coverage_count(rows)
    audit_signal = _audit_signal(partial_count=partial_count, critical_stale_count=len(stale), conflicts=0)
    return _row(
        "Local BNCD/Morningstar reports",
        score,
        coverage_rate,
        freshness_rate,
        affected=stale,
        action="Chercher un rapport seulement pour les titres importants ou recommandés qui manquent de preuves.",
        notes="Source locale utile pour combler les angles morts; optionnelle pour les titres déjà bien couverts.",
        ticker_count=len(rows),
        confirmed_field_rate=_average_confirmed_field_rate(with_report),
        partial_coverage_count=partial_count,
        critical_stale_count=len(stale),
        audit_signal=audit_signal,
    )


def _news_context_health(rows: list[dict[str, Any]]) -> dict[str, Any]:
    triggered = [row for row in rows if row.get("news_context_triggered") or row.get("news_context_status")]
    checked = [row for row in triggered if row.get("news_context_checked_at") or row.get("news_context_headlines")]
    affected = [_ticker(row) for row in triggered if row not in checked]
    coverage_rate = _ratio(len(checked), len(triggered))
    score = 92 if not triggered else 100 * coverage_rate
    return _row(
        "Free news context",
        score,
        coverage_rate if triggered else 1.0,
        coverage_rate if triggered else 1.0,
        affected=affected,
        action="Utiliser les nouvelles comme contexte seulement; valider manuellement si un mouvement de prix semble étrange.",
        notes="Aide à comprendre les grosses baisses ou risques récents, sans remplacer les fondamentaux.",
        ticker_count=len(triggered),
        confirmed_field_rate=1.0,
        audit_signal=_audit_signal(partial_count=0, critical_stale_count=0, conflicts=0),
    )


def _auto_proxy_health(rows: list[dict[str, Any]]) -> dict[str, Any]:
    high_dependency = [
        _ticker(row)
        for row in rows
        if str(row.get("auto_estimate_dependency") or "").upper() == "HIGH"
        or str(row.get("score_evidence_level") or "").upper() in {"ESTIMATE_HEAVY", "INSUFFICIENT_CONFIRMED"}
    ]
    critical_gaps = sum(int(safe_float(row.get("score_missing_data_count")) or 0) for row in rows)
    coverage_rate = _ratio(len(rows) - len(high_dependency), len(rows))
    score = 100 * coverage_rate - min(25, critical_gaps * 0.5)
    partial_count = _partial_coverage_count(rows)
    audit_signal = _audit_signal(partial_count=partial_count, critical_stale_count=0, conflicts=0)
    return _row(
        "Automatic proxy estimates",
        score,
        coverage_rate,
        coverage_rate,
        affected=high_dependency,
        gaps=critical_gaps,
        action="Remplir le fichier de calibration ou ajouter un rapport local pour les titres importants dépendants des proxys.",
        notes="Surveille le risque qu’un score confiant repose trop sur des estimations.",
        ticker_count=len(rows),
        confirmed_field_rate=_average_confirmed_field_rate(rows),
        partial_coverage_count=partial_count,
        audit_signal=audit_signal,
    )


def _row(
    source: str,
    score: float,
    coverage_rate: float,
    freshness_rate: float,
    *,
    affected: list[str] | None = None,
    conflicts: int = 0,
    gaps: int = 0,
    action: str,
    notes: str,
    ticker_count: int,
    availability_rate: float | None = None,
    avg_latency_ms: float | str | None = None,
    confirmed_field_rate: float | None = None,
    partial_coverage_count: int = 0,
    critical_stale_count: int = 0,
    audit_signal: str = "OK",
) -> dict[str, Any]:
    affected = sorted({ticker for ticker in (affected or []) if ticker})
    health_score = round(clamp(score, 0, 100), 1)
    audit_signal = audit_signal or "OK"
    return {
        "source": source,
        "status": _status(health_score),
        "health_score": health_score,
        "coverage_rate": round(coverage_rate, 4),
        "freshness_rate": round(freshness_rate, 4),
        "availability_rate": round(availability_rate if availability_rate is not None else coverage_rate, 4),
        "avg_latency_ms": avg_latency_ms if avg_latency_ms is not None else "",
        "affected_ticker_count": len(affected),
        "affected_tickers": ", ".join(affected[:20]),
        "conflict_count": conflicts,
        "critical_gap_count": gaps,
        "confirmed_field_rate": round(confirmed_field_rate if confirmed_field_rate is not None else coverage_rate, 4),
        "partial_coverage_count": partial_coverage_count,
        "critical_stale_count": critical_stale_count,
        "audit_signal": audit_signal,
        "ticker_count": ticker_count,
        "trend": "NEW",
        "action": _action_with_audit(action, audit_signal),
        "notes": notes,
    }


def _latest_history_by_source(rows: list[dict[str, Any]], mode: str, *, before_date: str) -> dict[str, dict[str, Any]]:
    filtered = [row for row in rows if row.get("mode") == mode and str(row.get("date") or "") < before_date]
    filtered.sort(key=lambda row: str(row.get("date") or ""))
    latest: dict[str, dict[str, Any]] = {}
    for row in filtered:
        latest[str(row.get("source") or "")] = row
    return latest


def _trend_text(row: dict[str, Any], previous: dict[str, Any] | None) -> str:
    if not previous:
        return "NEW"
    current = safe_float(row.get("health_score")) or 0.0
    old = safe_float(previous.get("health_score")) or 0.0
    delta = current - old
    if delta <= -8:
        return f"DETERIORATING ({delta:.1f})"
    if delta >= 8:
        return f"IMPROVING (+{delta:.1f})"
    return "STABLE"


def _status(score: float) -> str:
    if score >= 85:
        return "OK"
    if score >= 70:
        return "WATCH"
    if score >= 50:
        return "DEGRADED"
    return "CRITICAL"


def _average_confirmed_field_rate(rows: list[dict[str, Any]]) -> float:
    values = [
        safe_float(row.get("critical_data_confirmed_field_rate"))
        for row in rows
        if safe_float(row.get("critical_data_confirmed_field_rate")) is not None
    ]
    if not values:
        return 0.0
    return round(sum(float(value) for value in values) / len(values), 4)


def _partial_coverage_count(rows: list[dict[str, Any]]) -> int:
    count = 0
    for row in rows:
        status = str(row.get("data_quality_partial_coverage_status") or "").upper()
        partial_flag = str(row.get("data_quality_partial_coverage_flag") or "").strip().lower() in {"true", "1", "yes", "oui"}
        fill_rate = safe_float(row.get("data_fill_rate"))
        if partial_flag or status in {"AUTO_PROXY_HEAVY_COVERAGE", "THIN_COVERAGE"}:
            count += 1
        elif fill_rate is not None and fill_rate < 0.70:
            count += 1
    return count


def _critical_stale_tickers(rows: list[dict[str, Any]]) -> list[str]:
    stale_levels = {"VERY_STALE", "UNAVAILABLE", "CRITICAL_REFRESH_NEEDED"}
    output = []
    for row in rows:
        critical_level = str(row.get("critical_data_freshness_level") or row.get("overall_data_freshness_level") or "").upper()
        freshness_score = safe_float(row.get("critical_data_freshness_score"))
        age_hours = safe_float(row.get("market_data_age_hours"))
        if critical_level in stale_levels or (critical_level == "STALE" and age_hours is not None and age_hours > 168):
            output.append(_ticker(row))
        elif freshness_score is not None and freshness_score < 70:
            output.append(_ticker(row))
    return sorted({ticker for ticker in output if ticker})


def _audit_signal(*, partial_count: int, critical_stale_count: int, conflicts: int) -> str:
    parts = []
    if partial_count:
        parts.append(f"PARTIAL_COVERAGE:{partial_count}")
    if critical_stale_count:
        parts.append(f"CRITICAL_STALE:{critical_stale_count}")
    if conflicts:
        parts.append(f"SOURCE_CONFLICTS:{conflicts}")
    return " | ".join(parts) if parts else "OK"


def _action_with_audit(action: str, audit_signal: str) -> str:
    if not audit_signal or audit_signal == "OK":
        return action
    return f"{action} Audit data quality: {audit_signal}."


def _canadian_source_health_result(
    status: str,
    fallback_available: bool,
    sources: dict[str, dict[str, Any]],
    cache_dir: str,
    recent_file_exists: bool,
) -> dict[str, Any]:
    return {
        "canadian_source_health_status": status,
        "canadian_fallback_available": bool(fallback_available),
        "cache_dir": cache_dir,
        "recent_file_exists": bool(recent_file_exists),
        "sources": sources,
    }


def _canadian_source_from_cache_name(name: str) -> str:
    for prefix, source in CANADIAN_SOURCE_CACHE_PREFIXES.items():
        if name.startswith(prefix):
            return source
    return ""


def _canadian_source_is_healthy(row: dict[str, Any]) -> bool:
    success_rate = safe_float(row.get("success_rate_percent")) or 0.0
    success_age = safe_float(row.get("latest_success_age_hours"))
    return (
        success_rate > CANADIAN_SOURCE_HEALTHY_SUCCESS_RATE
        and success_age is not None
        and success_age < CANADIAN_SOURCE_HEALTHY_SUCCESS_HOURS
    )


def _canadian_source_has_recent_success(row: dict[str, Any]) -> bool:
    success_age = safe_float(row.get("latest_success_age_hours"))
    return success_age is not None and success_age < CANADIAN_SOURCE_RECENT_FILE_HOURS


def _read_json_silently(path: Path) -> dict[str, Any]:
    try:
        json = __import__("json")
        return dict(json.loads(path.read_text(encoding="utf-8")))
    except Exception:
        return {}


def _canadian_cache_fetched_at(payload: dict[str, Any]) -> str:
    parsed = payload.get("parsed_payload") if isinstance(payload.get("parsed_payload"), dict) else {}
    return str(payload.get("fetched_at") or parsed.get("fetched_at") or "").strip()


def _canadian_cache_available(payload: dict[str, Any]) -> bool:
    parsed = payload.get("parsed_payload") if isinstance(payload.get("parsed_payload"), dict) else {}
    value = payload.get("available")
    if value is None:
        value = parsed.get("available")
    return str(value).strip().lower() in {"true", "1", "yes", "oui"}


def _age_hours_from_iso(value: str) -> float | None:
    if not value:
        return None
    try:
        datetime_module = __import__("datetime", fromlist=["datetime"])
        datetime_cls = datetime_module.datetime
        parsed = datetime_cls.fromisoformat(str(value).replace("Z", "+00:00"))
        now = datetime_cls.now(parsed.tzinfo) if parsed.tzinfo else datetime_cls.now()
        return max(0.0, (now - parsed).total_seconds() / 3600)
    except Exception:
        return None


def _is_more_recent_fetch(candidate: str, current: str) -> bool:
    candidate_age = _age_hours_from_iso(candidate)
    if candidate_age is None:
        return False
    current_age = _age_hours_from_iso(current)
    return current_age is None or candidate_age < current_age


def _ratio(numerator: int | float, denominator: int | float) -> float:
    denominator = float(denominator or 0)
    if denominator <= 0:
        return 1.0
    return clamp(float(numerator) / denominator, 0.0, 1.0)


def _ticker(row: dict[str, Any]) -> str:
    return str(row.get("ticker_display") or row.get("ticker") or "").strip()


def _has_market_value(row: dict[str, Any]) -> bool:
    for field in ("current_price", "current_price_cad", "price", "last_price", "regular_market_price"):
        if safe_float(row.get(field)) is not None:
            return True
    return False


def _looks_sec_eligible(row: dict[str, Any]) -> bool:
    if _looks_canadian_eligible(row):
        return False
    ticker = _ticker(row)
    if row.get("sec_edgar_cik") or row.get("official_data_sources"):
        return True
    if "." in ticker and not ticker.endswith(".US"):
        return False
    return str(row.get("currency") or row.get("quote_currency") or "").upper() == "USD" or str(row.get("region") or "").lower() == "united states"


def _looks_canadian_eligible(row: dict[str, Any]) -> bool:
    ticker = _ticker(row)
    if canadian_ticker_metadata(ticker):
        return True
    country = str(row.get("country") or "").strip().lower()
    currency = str(row.get("currency") or row.get("quote_currency") or "").strip().upper()
    return country == "canada" and currency == "CAD"


def _has_official_evidence(row: dict[str, Any]) -> bool:
    if row.get("official_supported_fields") or row.get("official_confirmed_fields"):
        return True
    level = str(row.get("official_evidence_level") or "").upper()
    return level in {"SUPPORTED", "CONFIRMED", "STRONG"}


def _weighted_conflict_score(row: dict[str, Any]) -> float:
    explicit = safe_float(row.get("official_weighted_conflict_score"))
    if explicit is not None:
        return explicit
    conflicts = row.get("official_data_conflicts") or []
    if isinstance(conflicts, str):
        values = [part.strip() for part in conflicts.replace("|", ";").split(";") if part.strip()]
    else:
        values = [str(item).strip() for item in conflicts if str(item).strip()]
    return float(summarize_conflict_profile(values).get("weighted_conflict_score") or 0.0)
