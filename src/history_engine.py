from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from .model_version import MODEL_RULES_VERSION
from .validation_evidence import RunPurpose, normalize_run_purpose
from .utils import load_json, read_csv_records, safe_float, save_json, today_iso, write_csv_records


TREND_COLUMNS = [
    "ticker",
    "universe",
    "trend_status",
    "trend_severity",
    "history_reference_count",
    "history_reference_dates",
    "score_total_change",
    "conviction_score_change",
    "capital_allocation_score_change",
    "previous_thesis_status",
    "current_thesis_status",
    "previous_liquidation_status",
    "current_liquidation_status",
    "previous_allocation_decision",
    "previous_final_position_action",
    "trend_reasons",
]

SNAPSHOT_FIELDS = [
    "ticker",
    "universe",
    "score_total",
    "score_with_estimates",
    "score_confirmed_only",
    "score_estimate_gap",
    "score_evidence_level",
    "conviction_score",
    "capital_allocation_score",
    "expected_cagr_quality",
    "long_term_durability_score",
    "long_term_durability_status",
    "opportunity_cost_status",
    "thesis_status",
    "liquidation_status",
    "allocation_decision",
    "final_position_action",
    "add_eligibility_status",
    "add_eligibility_reason",
    "auto_estimate_dependency",
    "sell_decision",
    "winner_protection_status",
    "winner_protection_action",
    "personal_high_price",
    "drawdown_from_personal_high",
    "unrealized_gain_percent",
    "shares",
    "average_cost",
    "average_cost_cad",
    "acquisition_value",
    "acquisition_value_cad",
    "current_value",
    "current_value_cad",
    "quality_but_too_expensive",
    "valuation_severity",
    "valuation_severity_reason",
    "quality_expensive_reasons",
    "data_quality",
    "data_reliability_score",
    "data_reliability_level",
    "overall_data_freshness_level",
    "market_data_freshness_level",
    "research_report_text_quality_status",
    "research_report_text_quality_score",
    "research_report_extraction_method",
    "research_report_ocr_status",
    "research_report_field_confidence",
    "research_report_extraction_warnings",
    "cycle_bubble_risk_level",
    "current_price",
    "current_price_cad",
    "forward_pe",
    "peg",
    "profit_margins",
    "eps_growth_estimated_3_5y",
    "score_missing_data_count",
    "model_rules_version",
    "analysis_mode",
]

HISTORY_LOOKBACK_DATES = 4
HISTORY_NUMERIC_BASELINE_FIELDS = [
    "score_total",
    "score_confirmed_only",
    "score_estimate_gap",
    "conviction_score",
    "capital_allocation_score",
    "current_price",
    "forward_pe",
    "peg",
    "profit_margins",
    "eps_growth_estimated_3_5y",
    "score_missing_data_count",
]


def load_previous_snapshot(
    reports_dir: str | Path,
    current_model_rules_version: str | None = None,
    analysis_mode: str | None = None,
) -> dict[str, dict[str, Any]]:
    reports_dir = Path(reports_dir)
    history_dir = reports_dir / "history"
    historical_daily_snapshots = _distinct_daily_snapshots(
        history_dir,
        exclude_date=today_iso(),
        analysis_mode=analysis_mode,
    )
    if current_model_rules_version is not None:
        historical_daily_snapshots = [
            snapshot
            for snapshot in historical_daily_snapshots
            if snapshot.get("model_rules_version") == current_model_rules_version
        ]
    if historical_daily_snapshots:
        return _multi_date_baseline(historical_daily_snapshots[:HISTORY_LOOKBACK_DATES])

    latest_path = _latest_analysis_snapshot_path(reports_dir, analysis_mode)
    latest_snapshot = load_json(latest_path)
    rows = latest_snapshot.get("analyses") if isinstance(latest_snapshot, dict) else None
    latest_date = _payload_date(latest_snapshot, latest_path)
    latest_version = str(latest_snapshot.get("model_rules_version") or "") if isinstance(latest_snapshot, dict) else ""
    latest_version_ok = current_model_rules_version is None or latest_version == current_model_rules_version
    latest_mode_ok = analysis_mode is None or _payload_mode_matches(latest_snapshot, analysis_mode)
    if isinstance(rows, list) and rows and latest_date != today_iso() and latest_version_ok and latest_mode_ok:
        return _rows_by_ticker(rows)

    latest_scores = reports_dir / "latest_scores.csv"
    if analysis_mode is None and current_model_rules_version is None and latest_scores.exists() and not history_dir.exists():
        return _rows_by_ticker(read_csv_records(latest_scores))
    return {}


def apply_history_context(
    analyses: dict[str, dict[str, Any]],
    previous_snapshot: dict[str, dict[str, Any]],
) -> None:
    for ticker, analysis in analyses.items():
        previous = previous_snapshot.get(ticker)
        trend = compute_trend(analysis, previous)
        analysis.update(trend)
        if trend["trend_status"] == "DETERIORATING" and trend["trend_severity"] >= 2:
            _add_historical_warning(analysis, trend)


def compute_trend(current: dict[str, Any], previous: dict[str, Any] | None) -> dict[str, Any]:
    if not previous:
        return {
            "trend_status": "NEW",
            "trend_severity": 0,
            "trend_reasons": ["Aucune analyse precedente disponible."],
            "history_reference_count": 0,
            "history_reference_dates": [],
            "previous_score_total": None,
            "score_total_change": None,
            "previous_conviction_score": None,
            "conviction_score_change": None,
            "previous_capital_allocation_score": None,
            "capital_allocation_score_change": None,
            "previous_thesis_status": "",
            "previous_liquidation_status": "",
            "previous_expected_cagr_quality": "",
            "previous_data_reliability_level": "",
            "previous_data_quality": "",
            "previous_allocation_decision": "",
            "previous_final_position_action": "",
        }

    score_delta = _delta(current.get("score_total"), previous.get("score_total"))
    conviction_delta = _delta(current.get("conviction_score"), previous.get("conviction_score"))
    capital_score_delta = _delta(current.get("capital_allocation_score"), previous.get("capital_allocation_score"))
    missing_delta = _delta(current.get("score_missing_data_count"), previous.get("score_missing_data_count"))
    price_delta = _relative_delta(current.get("current_price"), previous.get("current_price"))
    previous_thesis = str(previous.get("thesis_status") or "")
    current_thesis = str(current.get("thesis_status") or "")
    previous_liquidation = str(previous.get("liquidation_status") or "")
    current_liquidation = str(current.get("liquidation_status") or "")
    previous_allocation = str(previous.get("allocation_decision") or "")
    previous_final_action = str(previous.get("final_position_action") or "")
    previous_quality = str(previous.get("expected_cagr_quality") or "")
    current_quality = str(current.get("expected_cagr_quality") or "")
    previous_data_quality = str(previous.get("data_quality") or "")
    current_data_quality = str(current.get("data_quality") or "")
    previous_data_reliability = str(previous.get("data_reliability_level") or "")
    reference_count = int(safe_float(previous.get("history_reference_count")) or 1)
    reference_dates = previous.get("history_reference_dates") or []
    if not isinstance(reference_dates, list):
        reference_dates = [str(reference_dates)]
    reference_note = _reference_note(reference_count, reference_dates)

    if current_data_quality == "LOW" and safe_float(current.get("current_price")) is None:
        return {
            "trend_status": "DATA_UNAVAILABLE",
            "trend_severity": 0,
            "trend_reasons": [
                "Données de marché indisponibles; ne pas interpréter comme une détérioration fondamentale.",
                reference_note,
            ],
            "history_reference_count": reference_count,
            "history_reference_dates": reference_dates,
            "previous_score_total": safe_float(previous.get("score_total")),
            "score_total_change": score_delta,
            "previous_conviction_score": safe_float(previous.get("conviction_score")),
            "conviction_score_change": conviction_delta,
            "previous_capital_allocation_score": safe_float(previous.get("capital_allocation_score")),
            "capital_allocation_score_change": capital_score_delta,
            "previous_thesis_status": previous_thesis,
            "previous_liquidation_status": previous_liquidation,
            "previous_expected_cagr_quality": previous_quality,
            "previous_data_reliability_level": previous_data_reliability,
            "previous_data_quality": previous_data_quality,
            "previous_allocation_decision": previous_allocation,
            "previous_final_position_action": previous_final_action,
        }

    deterioration: list[str] = []
    improvement: list[str] = []

    if score_delta is not None:
        if score_delta <= -1.0:
            deterioration.append(f"score_total en baisse de {score_delta:.2f}")
        elif score_delta >= 1.0:
            improvement.append(f"score_total en hausse de {score_delta:.2f}")
    if conviction_delta is not None:
        if conviction_delta <= -10:
            deterioration.append(f"conviction en baisse de {conviction_delta:.1f} points")
        elif conviction_delta >= 10:
            improvement.append(f"conviction en hausse de {conviction_delta:.1f} points")
    if _has_rank(current_thesis, THESIS_RANK) and _has_rank(previous_thesis, THESIS_RANK) and _rank(current_thesis, THESIS_RANK) < _rank(previous_thesis, THESIS_RANK):
        deterioration.append(f"these passee de {previous_thesis} a {current_thesis}")
    elif _has_rank(current_thesis, THESIS_RANK) and _has_rank(previous_thesis, THESIS_RANK) and _rank(current_thesis, THESIS_RANK) > _rank(previous_thesis, THESIS_RANK):
        improvement.append(f"these amelioree de {previous_thesis} a {current_thesis}")
    if _has_rank(current_liquidation, LIQUIDATION_RANK) and _has_rank(previous_liquidation, LIQUIDATION_RANK) and _rank(current_liquidation, LIQUIDATION_RANK) < _rank(previous_liquidation, LIQUIDATION_RANK):
        deterioration.append(f"liquidation passee de {previous_liquidation} a {current_liquidation}")
    elif _has_rank(current_liquidation, LIQUIDATION_RANK) and _has_rank(previous_liquidation, LIQUIDATION_RANK) and _rank(current_liquidation, LIQUIDATION_RANK) > _rank(previous_liquidation, LIQUIDATION_RANK):
        improvement.append(f"liquidation amelioree de {previous_liquidation} a {current_liquidation}")
    if _has_rank(current_quality, CAGR_RANK) and _has_rank(previous_quality, CAGR_RANK) and _rank(current_quality, CAGR_RANK) < _rank(previous_quality, CAGR_RANK):
        deterioration.append(f"qualite CAGR passee de {previous_quality} a {current_quality}")
    elif _has_rank(current_quality, CAGR_RANK) and _has_rank(previous_quality, CAGR_RANK) and _rank(current_quality, CAGR_RANK) > _rank(previous_quality, CAGR_RANK):
        improvement.append(f"qualite CAGR amelioree de {previous_quality} a {current_quality}")
    if missing_delta is not None and missing_delta >= 2:
        deterioration.append("plus de donnees critiques manquantes qu'avant")
    elif missing_delta is not None and missing_delta <= -2:
        improvement.append("moins de donnees critiques manquantes qu'avant")
    if price_delta is not None and price_delta <= -0.20 and current.get("price_above_sma_200") is False:
        deterioration.append("prix en forte baisse depuis la derniere analyse et sous SMA 200")
    if _has_rank(current_data_quality, DATA_QUALITY_RANK) and _has_rank(previous_data_quality, DATA_QUALITY_RANK) and _rank(current_data_quality, DATA_QUALITY_RANK) < _rank(previous_data_quality, DATA_QUALITY_RANK):
        deterioration.append(f"qualite des donnees passee de {previous_data_quality} a {current_data_quality}")
    elif _has_rank(current_data_quality, DATA_QUALITY_RANK) and _has_rank(previous_data_quality, DATA_QUALITY_RANK) and _rank(current_data_quality, DATA_QUALITY_RANK) > _rank(previous_data_quality, DATA_QUALITY_RANK):
        improvement.append(f"qualite des donnees amelioree de {previous_data_quality} a {current_data_quality}")

    status_deterioration = _status_deteriorated(previous_thesis, current_thesis, THESIS_RANK) or _status_deteriorated(
        previous_liquidation, current_liquidation, LIQUIDATION_RANK
    ) or _status_deteriorated(previous_quality, current_quality, CAGR_RANK)
    data_quality_worsened = _status_deteriorated(previous_data_quality, current_data_quality, DATA_QUALITY_RANK)
    score_conviction_material = (
        score_delta is not None
        and conviction_delta is not None
        and score_delta <= -1.5
        and conviction_delta <= -15
        and not data_quality_worsened
    )

    if len(deterioration) >= 2 and (status_deterioration or score_conviction_material):
        trend_status = "DETERIORATING"
        reasons = deterioration
        severity = len(deterioration)
    elif deterioration and data_quality_worsened and not status_deterioration:
        trend_status = "STABLE"
        reasons = ["Changement surtout lié à la qualité/fraîcheur des données; ne pas l’interpréter comme une détérioration fondamentale."]
        reasons.extend(deterioration)
        severity = 0
    elif len(improvement) >= 2 and current.get("thesis_status") == "INTACT":
        trend_status = "SOLIDIFYING"
        reasons = improvement
        severity = len(improvement)
    elif len(improvement) >= 1:
        trend_status = "DEVELOPING"
        reasons = improvement
        severity = len(improvement)
    else:
        trend_status = "STABLE"
        reasons = ["Pas de changement majeur par rapport a la reference historique."]
        severity = 0
    if reference_note not in reasons:
        reasons.append(reference_note)

    return {
        "trend_status": trend_status,
        "trend_severity": severity,
        "trend_reasons": reasons,
        "history_reference_count": reference_count,
        "history_reference_dates": reference_dates,
        "previous_score_total": safe_float(previous.get("score_total")),
        "score_total_change": score_delta,
        "previous_conviction_score": safe_float(previous.get("conviction_score")),
        "conviction_score_change": conviction_delta,
        "previous_capital_allocation_score": safe_float(previous.get("capital_allocation_score")),
        "capital_allocation_score_change": capital_score_delta,
        "previous_thesis_status": previous_thesis,
        "previous_liquidation_status": previous_liquidation,
        "previous_expected_cagr_quality": previous_quality,
        "previous_data_reliability_level": previous_data_reliability,
        "previous_data_quality": previous_data_quality,
        "previous_allocation_decision": previous_allocation,
        "previous_final_position_action": previous_final_action,
    }


def save_current_snapshot(
    reports_dir: str | Path,
    analysis_mode: str | dict[str, dict[str, Any]] | None = None,
    *analysis_groups: dict[str, dict[str, Any]],
    run_purpose: str = RunPurpose.UNKNOWN_LEGACY.value,
    baseline_metadata: dict[str, Any] | None = None,
    manifest_reference: str = "",
    manifest_fingerprint: str = "",
) -> None:
    reports_dir = Path(reports_dir)
    history_dir = reports_dir / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    if isinstance(analysis_mode, dict):
        groups = (analysis_mode, *analysis_groups)
        normalized_mode = None
    else:
        groups = analysis_groups
        normalized_mode = _normalize_mode(analysis_mode)
    rows = []
    for group in groups:
        for analysis in group.values():
            rows.append(_snapshot_row(analysis, normalized_mode))
    baseline = baseline_metadata or {}
    payload = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "analysis_date": today_iso(),
        "model_rules_version": MODEL_RULES_VERSION,
        "analysis_mode": normalized_mode,
        "run_purpose": normalize_run_purpose(run_purpose),
        "baseline_id": baseline.get("baseline_id", ""),
        "baseline_started_at": baseline.get("baseline_started_at", ""),
        "baseline_evidence_status": baseline.get("baseline_evidence_status", ""),
        "baseline_forward_eligible": baseline.get("baseline_forward_eligible", False),
        "manifest_reference": manifest_reference,
        "manifest_fingerprint": manifest_fingerprint,
        "analyses": rows,
    }
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    mode_prefix = f"{_mode_slug(normalized_mode)}_" if normalized_mode else ""
    save_json(history_dir / f"analysis_{mode_prefix}{stamp}.json", payload)
    save_json(reports_dir / "latest_analysis_snapshot.json", payload)
    if normalized_mode:
        save_json(_latest_analysis_snapshot_path(reports_dir, normalized_mode), payload)


def trend_rows_for_csv(*analysis_groups: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for group in analysis_groups:
        for analysis in sorted(group.values(), key=lambda row: (str(row.get("universe")), str(row.get("ticker")))):
            reasons = analysis.get("trend_reasons") or []
            if isinstance(reasons, list):
                reasons = "; ".join(str(item) for item in reasons)
            rows.append(
                {
                    "ticker": analysis.get("ticker"),
                    "universe": analysis.get("universe"),
                    "trend_status": analysis.get("trend_status"),
                    "trend_severity": analysis.get("trend_severity"),
                    "history_reference_count": analysis.get("history_reference_count"),
                    "history_reference_dates": _date_list_text(analysis.get("history_reference_dates")),
                    "score_total_change": analysis.get("score_total_change"),
                    "conviction_score_change": analysis.get("conviction_score_change"),
                    "capital_allocation_score_change": analysis.get("capital_allocation_score_change"),
                    "previous_thesis_status": analysis.get("previous_thesis_status"),
                    "current_thesis_status": analysis.get("thesis_status"),
                    "previous_liquidation_status": analysis.get("previous_liquidation_status"),
                    "current_liquidation_status": analysis.get("liquidation_status"),
                    "previous_allocation_decision": analysis.get("previous_allocation_decision"),
                    "previous_final_position_action": analysis.get("previous_final_position_action"),
                    "trend_reasons": reasons,
                }
            )
    return rows


def write_trend_csv(path: str | Path, *analysis_groups: dict[str, dict[str, Any]]) -> None:
    write_csv_records(path, trend_rows_for_csv(*analysis_groups), TREND_COLUMNS)


THESIS_RANK = {"BROKEN": 0, "WEAKENING": 1, "UNCERTAIN": 1, "INTACT": 3}
LIQUIDATION_RANK = {"RED": 0, "ORANGE": 1, "YELLOW": 2, "GREEN": 3}
CAGR_RANK = {"UNCERTAIN": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "VERY_HIGH": 4}
DATA_QUALITY_RANK = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}


def _distinct_daily_snapshots(
    history_dir: Path,
    exclude_date: str,
    analysis_mode: str | None = None,
) -> list[dict[str, Any]]:
    records = []
    for path in history_dir.glob("analysis_*.json"):
        loaded = load_json(path)
        rows = loaded.get("analyses") if isinstance(loaded, dict) else None
        if not isinstance(rows, list) or not rows:
            continue
        if analysis_mode is not None and not _payload_mode_matches(loaded, analysis_mode):
            continue
        snapshot_date = _payload_date(loaded, path)
        if not snapshot_date or snapshot_date == exclude_date:
            continue
        records.append(
            {
                "path": path,
                "analysis_date": snapshot_date,
                "created_at": str(loaded.get("created_at") or path.stem),
                "rows": rows,
                "model_rules_version": str(loaded.get("model_rules_version") or ""),
                "analysis_mode": _normalize_mode(loaded.get("analysis_mode")),
            }
        )

    records.sort(key=lambda row: (str(row.get("analysis_date")), str(row.get("created_at"))), reverse=True)
    by_date: dict[str, dict[str, Any]] = {}
    for record in records:
        snapshot_date = str(record.get("analysis_date") or "")
        if snapshot_date and snapshot_date not in by_date:
            by_date[snapshot_date] = record
    return list(by_date.values())


def _multi_date_baseline(snapshot_records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    rows_by_ticker: dict[str, list[dict[str, Any]]] = {}
    for record in snapshot_records:
        snapshot_date = str(record.get("analysis_date") or "")
        rows = record.get("rows") or []
        if not isinstance(rows, list):
            continue
        for row in rows:
            ticker = str(row.get("ticker") or "").strip().upper()
            if not ticker:
                continue
            enriched = dict(row)
            enriched["_snapshot_date"] = snapshot_date
            rows_by_ticker.setdefault(ticker, []).append(enriched)

    baseline: dict[str, dict[str, Any]] = {}
    for ticker, rows in rows_by_ticker.items():
        rows.sort(key=lambda row: str(row.get("_snapshot_date") or ""), reverse=True)
        latest_reference = dict(rows[0])
        reference_dates = sorted(
            {str(row.get("_snapshot_date")) for row in rows if row.get("_snapshot_date")},
            reverse=True,
        )
        for field in HISTORY_NUMERIC_BASELINE_FIELDS:
            average = _average_numeric(row.get(field) for row in rows)
            if average is not None:
                latest_reference[field] = average
        latest_reference["history_reference_count"] = len(reference_dates)
        latest_reference["history_reference_dates"] = reference_dates
        latest_reference["history_reference_mode"] = "DISTINCT_DAILY_AVERAGE"
        latest_reference["model_rules_version"] = str(rows[0].get("model_rules_version") or "")
        baseline[ticker] = latest_reference
    return baseline


def _rows_by_ticker(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        ticker = str(row.get("ticker") or "").strip().upper()
        if ticker:
            indexed[ticker] = row
    return indexed


def _snapshot_row(analysis: dict[str, Any], analysis_mode: str | None = None) -> dict[str, Any]:
    row = {field: analysis.get(field) for field in SNAPSHOT_FIELDS}
    row["model_rules_version"] = MODEL_RULES_VERSION
    row["analysis_mode"] = analysis_mode
    return row


def _latest_analysis_snapshot_path(reports_dir: Path, analysis_mode: str | None) -> Path:
    normalized_mode = _normalize_mode(analysis_mode)
    if not normalized_mode:
        return reports_dir / "latest_analysis_snapshot.json"
    return reports_dir / f"latest_analysis_snapshot_{_mode_slug(normalized_mode)}.json"


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


def _payload_date(payload: Any, path: Path) -> str:
    if isinstance(payload, dict):
        analysis_date = str(payload.get("analysis_date") or "").strip()
        if analysis_date:
            return analysis_date[:10]
        created_at = str(payload.get("created_at") or "").strip()
        if created_at:
            return created_at[:10]
    stem = path.stem
    if stem.startswith("analysis_") and len(stem) >= len("analysis_YYYYMMDD"):
        raw = stem.removeprefix("analysis_")[:8]
        if raw.isdigit():
            return f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"
    return ""


def _average_numeric(values: Any) -> float | None:
    numbers = [number for number in (safe_float(value) for value in values) if number is not None]
    if not numbers:
        return None
    return round(sum(numbers) / len(numbers), 4)


def _reference_note(reference_count: int, reference_dates: list[str]) -> str:
    if reference_count <= 0:
        return "Reference historique: aucune date precedente disponible."
    dates = ", ".join(reference_dates)
    return f"Reference historique: moyenne des {reference_count} derniere(s) date(s) distincte(s): {dates}."


def _date_list_text(values: Any) -> str:
    if not values:
        return ""
    if isinstance(values, list):
        return ", ".join(str(value) for value in values)
    return str(values)


def _delta(current: Any, previous: Any) -> float | None:
    current_value = safe_float(current)
    previous_value = safe_float(previous)
    if current_value is None or previous_value is None:
        return None
    return round(current_value - previous_value, 4)


def _relative_delta(current: Any, previous: Any) -> float | None:
    current_value = safe_float(current)
    previous_value = safe_float(previous)
    if current_value is None or previous_value is None or previous_value <= 0:
        return None
    return current_value / previous_value - 1


def _rank(value: str, ranks: dict[str, int]) -> int:
    return ranks.get(str(value or "").upper(), -1)


def _has_rank(value: str, ranks: dict[str, int]) -> bool:
    return str(value or "").upper() in ranks


def _status_deteriorated(previous: str, current: str, ranks: dict[str, int]) -> bool:
    return _has_rank(previous, ranks) and _has_rank(current, ranks) and _rank(current, ranks) < _rank(previous, ranks)


def _add_historical_warning(analysis: dict[str, Any], trend: dict[str, Any]) -> None:
    signal = "Deterioration detectee par comparaison avec les analyses precedentes."
    signals = analysis.get("signals_detected")
    if not isinstance(signals, list):
        signals = []
    if signal not in signals:
        signals.append(signal)
    analysis["signals_detected"] = signals
    reasons = analysis.get("liquidation_reasons")
    if not isinstance(reasons, list):
        reasons = []
    if signal not in reasons:
        reasons.append(signal)
    analysis["liquidation_reasons"] = reasons
    if analysis.get("liquidation_status") == "GREEN" and trend.get("trend_severity", 0) >= 3:
        analysis["liquidation_status"] = "YELLOW"
        analysis["sell_status"] = "YELLOW"
        analysis["fundamental_sell_status"] = "YELLOW"
        analysis["recommended_action"] = "WATCH"
        analysis["sell_decision"] = "WATCH"
        analysis["liquidation_decision"] = "WATCH"
        analysis["winner_accelerated"] = False
