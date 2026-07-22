from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from .data_fetcher import DEFAULT_CIRCUIT_BREAKER_COOLDOWN_SECONDS
from .utils import CACHE_DIR, safe_float, save_json


CACHE_HEALTH_COLUMNS = [
    "category",
    "status",
    "severity",
    "count",
    "cleaned_count",
    "details",
    "suggested_action",
]

LAST_KNOWN_GOOD_DIR_NAME = "last_known_good"
QUARANTINE_DIR_NAME = "quarantine"
TEMP_FILE_MAX_AGE_HOURS = 24
CORRUPT_JSON_QUARANTINE_AGE_HOURS = 24
UNAVAILABLE_CACHE_MAX_AGE_HOURS = 168
OLD_DIRECT_CACHE_WARN_HOURS = 720
STALE_LAST_KNOWN_GOOD_WARN_HOURS = 24 * 180


def reset_expired_market_circuit_breakers(
    cache_dir: str | Path = CACHE_DIR,
    *,
    cooldown_seconds: int = DEFAULT_CIRCUIT_BREAKER_COOLDOWN_SECONDS,
) -> dict[str, Any]:
    """Reset expired persisted market circuit-breaker flags without deleting price cache."""
    cache_dir = Path(cache_dir)
    if not cache_dir.exists():
        return _row(
            "market_circuit_breaker_reset",
            "INFO",
            "LOW",
            0,
            0,
            "Cache marché absent; aucun circuit breaker persistant à remettre à zéro.",
            "Aucune action.",
        )

    now = datetime.now()
    candidates = 0
    reset_count = 0
    still_cooling_down = 0
    missing_timestamp = 0
    for path in sorted(cache_dir.glob("*.json")):
        if not path.is_file() or path.name.endswith(".meta.json"):
            continue
        payload = _load_json_payload(path)
        if payload is None or not _has_open_circuit_marker(payload):
            continue
        candidates += 1
        last_failure_at = _parse_iso_datetime(
            payload.get("market_data_fetch_attempted_at") or payload.get("fetched_at")
        )
        if last_failure_at is None:
            missing_timestamp += 1
            continue
        age_seconds = max(0.0, (now - last_failure_at).total_seconds())
        if age_seconds < cooldown_seconds:
            still_cooling_down += 1
            continue
        _reset_circuit_breaker_payload(payload, now)
        save_json(path, payload)
        reset_count += 1

    details = (
        f"{reset_count} circuit(s) Yahoo Finance expiré(s) remis à zéro; "
        f"{still_cooling_down} encore en cooldown; {missing_timestamp} sans timestamp exploitable."
    )
    return _row(
        "market_circuit_breaker_reset",
        "PASS" if reset_count else "INFO",
        "LOW",
        candidates,
        reset_count,
        details,
        "Aucune action." if not still_cooling_down else "Relancer plus tard si des circuits sont encore en cooldown.",
    )


def run_cache_maintenance(cache_dir: str | Path = CACHE_DIR, *, repair_safe: bool = False) -> list[dict[str, Any]]:
    """Inspect and lightly repair the market-data cache.

    The cleanup is intentionally conservative. It removes temporary files and
    unusable stale artifacts, but it preserves any cache file that can still act
    as a fallback unless a safer last-known-good copy already exists.
    """

    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    lkg_dir = cache_dir / LAST_KNOWN_GOOD_DIR_NAME
    lkg_dir.mkdir(parents=True, exist_ok=True)
    quarantine_dir = cache_dir / QUARANTINE_DIR_NAME

    root_json_files = sorted(
        path
        for path in cache_dir.glob("*.json")
        if path.is_file() and not path.name.endswith(".meta.json")
    )
    auxiliary_json_files = sorted(path for path in cache_dir.glob("*.json") if path.is_file() and path.name.endswith(".meta.json"))
    lkg_files = sorted(path for path in lkg_dir.glob("*.json") if path.is_file())
    temp_files = sorted(_iter_temp_files(cache_dir))

    direct_usable: list[Path] = []
    legacy_fallback: list[Path] = []
    unavailable: list[Path] = []
    corrupt: list[Path] = []
    old_direct: list[Path] = []
    backfilled_lkg = 0
    backfilled_lkg_from_direct = 0
    backfilled_lkg_from_legacy = 0
    cleaned_temp = 0
    cleaned_unavailable = 0
    cleaned_legacy = 0
    quarantined_corrupt = 0

    for path in root_json_files:
        payload = _load_json_payload(path)
        if payload is None:
            corrupt.append(path)
            if repair_safe and _age_hours(path) >= CORRUPT_JSON_QUARANTINE_AGE_HOURS:
                _quarantine_file(path, quarantine_dir)
                quarantined_corrupt += 1
            continue
        source = str(payload.get("source") or "").strip()
        has_price = safe_float(payload.get("current_price")) is not None
        if _is_direct_usable(payload):
            direct_usable.append(path)
            if _age_hours(path) >= OLD_DIRECT_CACHE_WARN_HOURS:
                old_direct.append(path)
            if repair_safe and not _last_known_good_path(lkg_dir, path).exists():
                _save_last_known_good_from_cache(lkg_dir, path, payload)
                backfilled_lkg += 1
                backfilled_lkg_from_direct += 1
            continue
        if source in {"stale_cache", "last_known_good"} and has_price:
            legacy_fallback.append(path)
            lkg_path = _last_known_good_path(lkg_dir, path)
            if repair_safe and not lkg_path.exists():
                _save_last_known_good_from_cache(lkg_dir, path, payload)
                backfilled_lkg += 1
                backfilled_lkg_from_legacy += 1
            if repair_safe and lkg_path.exists():
                _safe_unlink(path)
                cleaned_legacy += 1
            continue
        if source in {"", "empty", "unavailable"} or not has_price:
            unavailable.append(path)
            if repair_safe and _age_hours(path) >= UNAVAILABLE_CACHE_MAX_AGE_HOURS:
                _safe_unlink(path)
                cleaned_unavailable += 1

    for path in temp_files:
        if repair_safe and _age_hours(path) >= TEMP_FILE_MAX_AGE_HOURS:
            _safe_unlink(path)
            cleaned_temp += 1

    final_root_json_files = sorted(
        path
        for path in cache_dir.glob("*.json")
        if path.is_file() and not path.name.endswith(".meta.json")
    )
    final_auxiliary_json_files = sorted(path for path in cache_dir.glob("*.json") if path.is_file() and path.name.endswith(".meta.json"))
    final_lkg_files = sorted(path for path in lkg_dir.glob("*.json") if path.is_file())
    remaining_corrupt = max(0, len(corrupt) - quarantined_corrupt)
    remaining_unavailable = max(0, len(unavailable) - cleaned_unavailable)
    remaining_legacy = max(0, len(legacy_fallback) - cleaned_legacy)
    remaining_temp = max(0, len(temp_files) - cleaned_temp)
    stale_lkg = [path for path in final_lkg_files if _age_hours(path) >= STALE_LAST_KNOWN_GOOD_WARN_HOURS]
    rows = [
        _row(
            "summary",
            _summary_status(remaining_corrupt, remaining_unavailable, remaining_legacy, len(old_direct)),
            _summary_severity(remaining_corrupt, remaining_unavailable, remaining_legacy, len(old_direct)),
            len(final_root_json_files) + len(final_auxiliary_json_files) + len(final_lkg_files),
            cleaned_temp + cleaned_unavailable + cleaned_legacy + quarantined_corrupt + backfilled_lkg,
            (
                f"{len(final_root_json_files)} cache(s) marché, {len(final_lkg_files)} dernière(s) bonne(s) donnée(s), "
                f"{len(final_auxiliary_json_files)} cache(s) auxiliaire(s)."
            ),
            "Aucune action."
            if not (remaining_corrupt or remaining_unavailable or remaining_legacy or old_direct)
            else "Lire reports/latest_cache_health.csv.",
        ),
        _row(
            "direct_market_cache",
            "PASS" if direct_usable else "INFO",
            "LOW",
            len(direct_usable),
            backfilled_lkg_from_direct,
            f"{len(direct_usable)} cache(s) direct(s) utilisable(s); {backfilled_lkg_from_direct} last-known-good créé(s) depuis cache direct.",
            "Aucune action.",
        ),
        _row(
            "last_known_good",
            "WARN" if stale_lkg else ("PASS" if final_lkg_files else "INFO"),
            "MEDIUM" if stale_lkg else "LOW",
            len(final_lkg_files),
            0,
            f"{len(final_lkg_files)} fichier(s) last-known-good; {len(stale_lkg)} très ancien(s).",
            "Rafraîchir les données si plusieurs last-known-good deviennent très anciens." if stale_lkg else "Aucune action.",
        ),
        _row(
            "temporary_files",
            "WARN" if remaining_temp else "PASS",
            "LOW",
            len(temp_files),
            cleaned_temp,
            f"{len(temp_files)} fichier(s) temporaire(s) détecté(s); {cleaned_temp} supprimé(s).",
            "Relancer health-check --repair-safe si des temporaires persistent." if remaining_temp else "Aucune action.",
        ),
        _row(
            "corrupt_json",
            "WARN" if remaining_corrupt else "PASS",
            "MEDIUM" if remaining_corrupt else "LOW",
            len(corrupt),
            quarantined_corrupt,
            f"{len(corrupt)} cache(s) JSON illisible(s); {quarantined_corrupt} mis en quarantaine.",
            "Aucune action si la quarantaine a réussi; sinon relancer --refresh-market-data." if remaining_corrupt else "Aucune action.",
        ),
        _row(
            "unavailable_cache",
            "WARN" if remaining_unavailable else "PASS",
            "LOW" if not remaining_unavailable else "MEDIUM",
            len(unavailable),
            cleaned_unavailable,
            f"{len(unavailable)} cache(s) sans prix utilisable; {cleaned_unavailable} supprimé(s).",
            "Normal pour certains tickers mal couverts; vérifier seulement si un titre important est touché." if remaining_unavailable else "Aucune action.",
        ),
        _row(
            "legacy_fallback_cache",
            "WARN" if remaining_legacy else "PASS",
            "LOW" if not remaining_legacy else "MEDIUM",
            len(legacy_fallback),
            cleaned_legacy,
            (
                f"{len(legacy_fallback)} ancien(s) cache(s) fallback; "
                f"{backfilled_lkg_from_legacy} copié(s) en last-known-good; {cleaned_legacy} supprimé(s)."
            ),
            "Ces fichiers n’empêchent plus un refresh live, mais le nettoyage réduit le bruit." if remaining_legacy else "Aucune action.",
        ),
        _row(
            "old_direct_cache",
            "WARN" if old_direct else "PASS",
            "LOW" if not old_direct else "MEDIUM",
            len(old_direct),
            0,
            f"{len(old_direct)} cache(s) direct(s) datent de plus de {OLD_DIRECT_CACHE_WARN_HOURS / 24:.0f} jours.",
            "Utiliser --refresh-market-data si une décision importante dépend de ces titres." if old_direct else "Aucune action.",
        ),
    ]
    return rows


def cache_health_summary(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "Cache non vérifié."
    summary = next((row for row in rows if row.get("category") == "summary"), rows[0])
    status = str(summary.get("status") or "INFO")
    details = str(summary.get("details") or "")
    cleaned = safe_float(summary.get("cleaned_count")) or 0
    suffix = f" {int(cleaned)} réparation(s)/nettoyage(s) safe." if cleaned else ""
    return f"{status}: {details}{suffix}"


def _row(
    category: str,
    status: str,
    severity: str,
    count: int,
    cleaned_count: int,
    details: str,
    suggested_action: str,
) -> dict[str, Any]:
    return {
        "category": category,
        "status": status,
        "severity": severity,
        "count": count,
        "cleaned_count": cleaned_count,
        "details": details,
        "suggested_action": suggested_action,
    }


def _summary_status(corrupt_count: int, unavailable_count: int, legacy_fallback_count: int, old_direct_count: int) -> str:
    if corrupt_count:
        return "WARN"
    if unavailable_count >= 10 or legacy_fallback_count >= 10 or old_direct_count:
        return "WARN"
    return "PASS"


def _summary_severity(corrupt_count: int, unavailable_count: int, legacy_fallback_count: int, old_direct_count: int) -> str:
    if corrupt_count:
        return "MEDIUM"
    if unavailable_count >= 10 or legacy_fallback_count >= 10 or old_direct_count:
        return "LOW"
    return "LOW"


def _iter_temp_files(cache_dir: Path) -> list[Path]:
    if not cache_dir.exists():
        return []
    return [
        path
        for path in cache_dir.rglob("*")
        if path.is_file() and (path.suffix == ".tmp" or (path.name.startswith(".") and ".tmp" in path.name))
    ]


def _load_json_payload(path: Path) -> dict[str, Any] | None:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return loaded if isinstance(loaded, dict) else None


def _has_open_circuit_marker(payload: dict[str, Any]) -> bool:
    flags = {str(flag) for flag in (payload.get("market_data_warning_flags") or [])}
    return bool(payload.get("market_data_circuit_breaker_open")) or "CIRCUIT_OPEN" in flags


def _reset_circuit_breaker_payload(payload: dict[str, Any], now: datetime) -> None:
    payload["market_data_circuit_breaker_open"] = False
    payload["market_data_warning_flags"] = [
        flag for flag in (payload.get("market_data_warning_flags") or []) if str(flag) != "CIRCUIT_OPEN"
    ]
    payload["failure_count"] = 0
    payload["market_data_failure_count"] = 0
    payload["market_data_circuit_breaker_reset_at"] = now.isoformat(timespec="seconds")
    last_error = str(payload.get("market_data_last_error") or "")
    if "Coupe-circuit" in last_error or "circuit" in last_error.lower():
        payload["market_data_last_error"] = ""


def _parse_iso_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def _is_direct_usable(payload: dict[str, Any]) -> bool:
    source = str(payload.get("source") or "").strip()
    if source in {"", "empty", "unavailable", "stale_cache", "last_known_good"}:
        return False
    return safe_float(payload.get("current_price")) is not None


def _last_known_good_path(lkg_dir: Path, root_cache_path: Path) -> Path:
    return lkg_dir / root_cache_path.name


def _save_last_known_good_from_cache(lkg_dir: Path, root_cache_path: Path, payload: dict[str, Any]) -> None:
    saved = dict(payload)
    saved["last_known_good_at"] = payload.get("fetched_at") or _modified_iso(root_cache_path)
    saved["last_known_good_source"] = payload.get("source")
    save_json(_last_known_good_path(lkg_dir, root_cache_path), saved)


def _age_hours(path: Path) -> float:
    try:
        return max(0.0, (datetime.now().timestamp() - path.stat().st_mtime) / 3600)
    except OSError:
        return 0.0


def _modified_iso(path: Path) -> str:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")
    except OSError:
        return datetime.now().isoformat(timespec="seconds")


def _safe_unlink(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        return
    except OSError:
        return


def _quarantine_file(path: Path, quarantine_dir: Path) -> None:
    quarantine_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = quarantine_dir / f"{path.name}.{stamp}.corrupt"
    try:
        os.replace(path, target)
    except OSError:
        return
