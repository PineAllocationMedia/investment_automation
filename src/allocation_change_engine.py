from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from .model_version import MODEL_RULES_VERSION
from .utils import load_json, read_csv_records, safe_float, save_json, today_iso, write_csv_records


ALLOCATION_CHANGE_COLUMNS = [
    "ticker",
    "previous_amount",
    "current_amount",
    "change_amount",
    "previous_percentage",
    "current_percentage",
    "change_status",
    "main_explanation",
    "decision_impact",
    "reference_dates",
]

ALLOCATION_HISTORY_LOOKBACK_DATES = 4


def load_previous_allocation_baseline(
    reports_dir: str | Path,
    current_model_rules_version: str | None = None,
    analysis_mode: str | None = None,
) -> dict[str, dict[str, Any]]:
    reports_dir = Path(reports_dir)
    history_dir = reports_dir / "history"
    history_files_exist = any(history_dir.glob("allocation_*.json")) if history_dir.exists() else False
    records = _distinct_daily_allocation_snapshots(
        history_dir,
        exclude_date=today_iso(),
        analysis_mode=analysis_mode,
    )
    if current_model_rules_version is not None:
        records = [
            record for record in records if record.get("model_rules_version") == current_model_rules_version
        ]
    if records:
        return _allocation_baseline(records[:ALLOCATION_HISTORY_LOOKBACK_DATES])
    if history_files_exist:
        return {}

    latest_path = _latest_allocation_snapshot_path(reports_dir, analysis_mode)
    latest = load_json(latest_path)
    latest_version = str(latest.get("model_rules_version") or "") if isinstance(latest, dict) else ""
    latest_version_ok = current_model_rules_version is None or latest_version == current_model_rules_version
    latest_mode_ok = analysis_mode is None or _payload_mode_matches(latest, analysis_mode)
    if (
        isinstance(latest, dict)
        and str(latest.get("analysis_date") or "")[:10] != today_iso()
        and latest_version_ok
        and latest_mode_ok
    ):
        rows = latest.get("allocations") or []
        if isinstance(rows, list):
            return _allocation_baseline([{"analysis_date": str(latest.get("analysis_date") or ""), "rows": rows}])

    latest_csv = reports_dir / "latest_allocations.csv"
    if analysis_mode is None and current_model_rules_version is None and latest_csv.exists():
        rows = read_csv_records(latest_csv)
        return _allocation_baseline([{"analysis_date": "latest_csv", "rows": rows}])
    return {}


def build_allocation_change_rows(
    allocations: list[dict[str, Any]],
    analyses: dict[str, dict[str, Any]],
    previous_baseline: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    current_rows = _current_allocation_map(allocations)
    tickers = sorted(set(current_rows) | set(previous_baseline), key=lambda ticker: (ticker == "VFV.TO", ticker))
    if not tickers:
        return [
            {
                "ticker": "",
                "previous_amount": "",
                "current_amount": "",
                "change_amount": "",
                "previous_percentage": "",
                "current_percentage": "",
                "change_status": "NO_ALLOCATION_TO_COMPARE",
                "main_explanation": "Aucune cotisation active à comparer.",
                "decision_impact": "Explication seulement; ne modifie pas l’allocation.",
                "reference_dates": "",
            }
        ]

    rows = []
    for ticker in tickers:
        current = current_rows.get(ticker, {})
        previous = previous_baseline.get(ticker, {})
        current_amount = safe_float(current.get("amount")) or 0.0
        previous_amount = safe_float(previous.get("amount")) or 0.0
        current_percentage = safe_float(current.get("percentage")) or 0.0
        previous_percentage = safe_float(previous.get("percentage")) or 0.0
        delta = round(current_amount - previous_amount, 2)
        rows.append(
            {
                "ticker": ticker,
                "previous_amount": round(previous_amount, 2),
                "current_amount": round(current_amount, 2),
                "change_amount": delta,
                "previous_percentage": round(previous_percentage, 4),
                "current_percentage": round(current_percentage, 4),
                "change_status": _change_status(current_amount, previous_amount, delta),
                "main_explanation": _change_explanation(ticker, delta, current, previous, analyses.get(ticker, {})),
                "decision_impact": "Explication seulement; ne modifie pas le choix des titres ni les montants.",
                "reference_dates": _reference_dates(previous),
            }
        )
    return rows


def write_allocation_change_csv(path: str | Path, rows: list[dict[str, Any]]) -> None:
    write_csv_records(path, rows, ALLOCATION_CHANGE_COLUMNS)


def save_allocation_snapshot(
    reports_dir: str | Path,
    allocation_result: dict[str, Any],
    analysis_mode: str | None = None,
) -> None:
    reports_dir = Path(reports_dir)
    history_dir = reports_dir / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    normalized_mode = _normalize_mode(analysis_mode)
    rows = _snapshot_rows(allocation_result.get("allocations") or [])
    payload = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "analysis_date": today_iso(),
        "model_rules_version": MODEL_RULES_VERSION,
        "analysis_mode": normalized_mode,
        "allocations": rows,
        "average_score_ex_vfv": allocation_result.get("average_score_ex_vfv"),
        "mandatory_vfv_percent": allocation_result.get("mandatory_vfv_percent"),
        "decision_quality": allocation_result.get("decision_quality", {}),
    }
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    mode_prefix = f"{_mode_slug(normalized_mode)}_" if normalized_mode else ""
    save_json(history_dir / f"allocation_{mode_prefix}{stamp}.json", payload)
    save_json(reports_dir / "latest_allocation_snapshot.json", payload)
    if normalized_mode:
        save_json(_latest_allocation_snapshot_path(reports_dir, normalized_mode), payload)


def _current_allocation_map(allocations: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for row in allocations:
        ticker = str(row.get("destination") or row.get("ticker") or "").strip().upper()
        if not ticker:
            continue
        rows[ticker] = {
            "ticker": ticker,
            "amount": safe_float(row.get("montant", row.get("amount"))) or 0.0,
            "percentage": safe_float(row.get("pourcentage", row.get("percentage"))) or 0.0,
            "reason": row.get("raison", row.get("reason", "")),
            "allocation_type": row.get("bloc", row.get("allocation_type", "")),
        }
    return rows


def _snapshot_rows(allocations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return list(_current_allocation_map(allocations).values())


def _distinct_daily_allocation_snapshots(
    history_dir: Path,
    exclude_date: str,
    analysis_mode: str | None = None,
) -> list[dict[str, Any]]:
    records = []
    for path in history_dir.glob("allocation_*.json"):
        payload = load_json(path)
        rows = payload.get("allocations") if isinstance(payload, dict) else None
        if not isinstance(rows, list) or not rows:
            continue
        if analysis_mode is not None and not _payload_mode_matches(payload, analysis_mode):
            continue
        analysis_date = str(payload.get("analysis_date") or payload.get("created_at") or "")[:10]
        if not analysis_date or analysis_date == exclude_date:
            continue
        records.append(
            {
                "analysis_date": analysis_date,
                "created_at": str(payload.get("created_at") or path.stem),
                "model_rules_version": str(payload.get("model_rules_version") or ""),
                "analysis_mode": _normalize_mode(payload.get("analysis_mode")),
                "rows": rows,
            }
        )
    records.sort(key=lambda row: (str(row.get("analysis_date")), str(row.get("created_at"))), reverse=True)
    by_date: dict[str, dict[str, Any]] = {}
    for record in records:
        date_key = str(record.get("analysis_date") or "")
        if date_key and date_key not in by_date:
            by_date[date_key] = record
    return list(by_date.values())


def _allocation_baseline(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        date_key = str(record.get("analysis_date") or "")
        for row in record.get("rows") or []:
            ticker = str(row.get("ticker") or row.get("destination") or "").strip().upper()
            if not ticker:
                continue
            enriched = dict(row)
            enriched["_analysis_date"] = date_key
            grouped.setdefault(ticker, []).append(enriched)

    baseline: dict[str, dict[str, Any]] = {}
    for ticker, rows in grouped.items():
        dates = sorted({str(row.get("_analysis_date") or "") for row in rows if row.get("_analysis_date")}, reverse=True)
        amount = _average(row.get("amount", row.get("montant")) for row in rows)
        percentage = _average(row.get("percentage", row.get("pourcentage")) for row in rows)
        latest_reason = str(rows[0].get("reason") or rows[0].get("raison") or "")
        baseline[ticker] = {
            "ticker": ticker,
            "amount": amount or 0.0,
            "percentage": percentage or 0.0,
            "reason": latest_reason,
            "reference_dates": dates,
        }
    return baseline


def _change_status(current_amount: float, previous_amount: float, delta: float) -> str:
    threshold = max(5.0, (current_amount + previous_amount) * 0.05)
    if previous_amount <= 0 and current_amount > 0:
        return "NEW_OR_RETURNED"
    if previous_amount > 0 and current_amount <= 0:
        return "REMOVED_OR_REDIRECTED"
    if abs(delta) <= threshold:
        return "STABLE"
    return "INCREASED" if delta > 0 else "DECREASED"


def _change_explanation(
    ticker: str,
    delta: float,
    current: dict[str, Any],
    previous: dict[str, Any],
    analysis: dict[str, Any],
) -> str:
    if not previous:
        return "Aucune référence historique d’allocation distincte; la ligne sert de point de départ."
    if ticker == "VFV.TO":
        return str(current.get("reason") or "VFV varie selon l’allocation obligatoire et les redirections imposées par les garde-fous.")

    reasons: list[str] = []
    cap_delta = safe_float(analysis.get("capital_allocation_score_change"))
    score_delta = safe_float(analysis.get("score_total_change"))
    conviction_delta = safe_float(analysis.get("conviction_score_change"))
    monitoring = str(analysis.get("monitoring_status") or "NORMAL")
    cycle = str(analysis.get("cycle_bubble_risk_level") or "")
    evidence = str(analysis.get("score_evidence_level") or "")
    allocation_status = str(analysis.get("allocation_stability_status") or "")

    if cap_delta is not None and abs(cap_delta) >= 3:
        reasons.append(f"capital_allocation_score {'hausse' if cap_delta > 0 else 'baisse'} de {cap_delta:.1f}")
    if score_delta is not None and abs(score_delta) >= 0.5:
        reasons.append(f"score fondamental {'hausse' if score_delta > 0 else 'baisse'} de {score_delta:.1f}")
    if conviction_delta is not None and abs(conviction_delta) >= 5:
        reasons.append(f"conviction {'hausse' if conviction_delta > 0 else 'baisse'} de {conviction_delta:.0f} pts")
    if monitoring not in {"", "NORMAL", "BENCHMARK"}:
        reasons.append(f"statut {monitoring}: sizing volontairement limité")
    if cycle in {"HIGH", "EXTREME"}:
        reasons.append(f"risque cycle/bulle {cycle}: allocation plafonnée")
    if evidence in {"ESTIMATE_HEAVY", "INSUFFICIENT_CONFIRMED"}:
        reasons.append(f"preuves du score {evidence}: validation utile avant grosse allocation")
    if allocation_status:
        reasons.append(f"stabilité mensuelle: {allocation_status}")
    if not reasons and current.get("reason"):
        reasons.append(str(current.get("reason")))
    if not reasons:
        reasons.append("variation causée par la simulation marginale et les plafonds de concentration.")

    prefix = "Allocation augmentée" if delta > 0 else "Allocation réduite" if delta < 0 else "Allocation stable"
    return f"{prefix}: " + "; ".join(reasons[:4]) + "."


def _reference_dates(row: dict[str, Any]) -> str:
    dates = row.get("reference_dates") or []
    if isinstance(dates, list):
        return ", ".join(str(date) for date in dates)
    return str(dates)


def _average(values: Any) -> float | None:
    numbers = [number for number in (safe_float(value) for value in values) if number is not None]
    if not numbers:
        return None
    return round(sum(numbers) / len(numbers), 4)


def _latest_allocation_snapshot_path(reports_dir: Path, analysis_mode: str | None) -> Path:
    normalized_mode = _normalize_mode(analysis_mode)
    if not normalized_mode:
        return reports_dir / "latest_allocation_snapshot.json"
    return reports_dir / f"latest_allocation_snapshot_{_mode_slug(normalized_mode)}.json"


def _payload_mode_matches(payload: Any, analysis_mode: str | None) -> bool:
    expected = _normalize_mode(analysis_mode)
    if expected is None:
        return True
    if not isinstance(payload, dict):
        return False
    return _normalize_mode(payload.get("analysis_mode")) == expected


def _normalize_mode(value: Any) -> str | None:
    text = str(value or "").strip().lower()
    return text or None


def _mode_slug(value: Any) -> str:
    text = _normalize_mode(value) or "unknown"
    return "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in text)
