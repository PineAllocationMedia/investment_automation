from __future__ import annotations

import configparser
import csv
import json
from datetime import date
from pathlib import Path
from typing import Any

from .evidence_provenance import (
    CALIBRATION_CONTEXT_FIELDS,
    CALIBRATION_FIELD_MAX_AGE_DAYS,
    HUMAN_MANUAL,
    PROXY_CALIBRATION_SYNC,
    calibration_field_freshness,
)
from .manual_inputs import MANUAL_COLUMNS, load_friendly_manual_inputs


MISSING = {"", "x", "X", "N/A", "NA", "N/D", "ND", "LOW-MEDIUM"}

CALIBRATION_COLUMN_MAP = {
    "roic_5y_avg_true": "roic_5y_avg",
    "net_margin_stable_or_expanding_true": "net_margin_stable_or_expanding",
    "eps_growth_5y_true": "eps_growth_5y",
    "eps_growth_estimated_3_5y_true": "eps_growth_estimated_3_5y",
    "sector_cagr_estimated_true": "sector_cagr_estimated",
    "forward_pe_true": "forward_pe_manual",
    "peg_true": "peg_manual",
    "fair_value_true": "fair_value",
    "valuation_vs_5y_avg_ok_true": "valuation_vs_5y_avg_ok",
    "moat_clear_true": "moat_clear",
    "forward_pe_growth_acceptable_true": "forward_pe_growth_acceptable",
    "management_quality_good_true": "management_quality_good",
    "balance_sheet_strong_true": "balance_sheet_strong",
    "margin_or_profitability_under_pressure_true": "margin_or_profitability_under_pressure",
    "confidence": "manual_confidence_level",
    "notes": "notes",
}


def sync_proxy_calibration_to_friendly(
    proxy_path: str | Path,
    friendly_path: str | Path,
    log_path: str | Path,
    today: date | None = None,
) -> dict[str, Any]:
    proxy_path = Path(proxy_path)
    friendly_path = Path(friendly_path)
    log_path = Path(log_path)
    today = today or date.today()

    with open(proxy_path, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    existing_inputs = load_friendly_manual_inputs(friendly_path, today=today)
    config = configparser.ConfigParser(interpolation=None)
    config.optionxform = str

    sections_written = 0
    skipped_no_data = 0
    stale_tickers: set[str] = set()
    warning_tickers: set[str] = set()
    no_date_tickers: set[str] = set()
    stale_fields: dict[str, list[str]] = {}
    current_fields: dict[str, list[str]] = {}
    unknown_date_fields: dict[str, list[str]] = {}
    proxy_tickers: set[str] = set()

    for row in rows:
        ticker = str(row.get("ticker", "") or "").strip().upper()
        if not ticker:
            continue
        proxy_tickers.add(ticker)
        source_date = str(row.get("source_date", "") or "").strip()
        source_name = str(row.get("source", "") or "").strip()
        generated_values = _generated_values(row)
        human_values = _human_values(existing_inputs.get(ticker))

        if not generated_values and not human_values:
            skipped_no_data += 1
            continue

        fields = {field: _format_config_value(value) for field, value in generated_values.items()}
        fields.update({field: _format_config_value(value) for field, value in human_values.items()})

        generated_fields = sorted(generated_values)
        human_fields = sorted(human_values)
        if generated_fields:
            fields["input_origin"] = PROXY_CALIBRATION_SYNC
            fields["calibration_source"] = source_name
            fields["calibration_source_date"] = source_date
            fields["calibration_synced_fields"] = ",".join(generated_fields)
            fields["calibration_snapshot_values"] = json.dumps(
                generated_values,
                ensure_ascii=True,
                separators=(",", ":"),
            )
        elif human_fields:
            fields["input_origin"] = HUMAN_MANUAL
        if human_fields:
            fields["manual_override_fields"] = ",".join(human_fields)

        config[ticker] = fields
        sections_written += 1

        ticker_stale: list[str] = []
        ticker_current: list[str] = []
        ticker_unknown: list[str] = []
        for field in generated_fields:
            if field in CALIBRATION_CONTEXT_FIELDS:
                continue
            freshness = calibration_field_freshness(field, source_date, today=today)
            if freshness["status"] == "STALE":
                ticker_stale.append(field)
            elif freshness["status"] == "UNKNOWN_DATE":
                ticker_unknown.append(field)
            else:
                ticker_current.append(field)
                remaining = int(freshness["max_age_days"]) - int(freshness["age_days"])
                if remaining <= 15:
                    warning_tickers.add(ticker)
        if ticker_stale:
            stale_tickers.add(ticker)
            stale_fields[ticker] = sorted(ticker_stale)
        if ticker_current:
            current_fields[ticker] = sorted(ticker_current)
        if ticker_unknown:
            no_date_tickers.add(ticker)
            unknown_date_fields[ticker] = sorted(ticker_unknown)

    for ticker, existing in sorted(existing_inputs.items()):
        if ticker in proxy_tickers or ticker in config:
            continue
        human_values = _human_values(existing)
        if not human_values:
            continue
        fields = {field: _format_config_value(value) for field, value in human_values.items()}
        fields["input_origin"] = HUMAN_MANUAL
        fields["manual_override_fields"] = ",".join(sorted(human_values))
        config[ticker] = fields
        sections_written += 1

    header = "\n".join(
        [
            "# Genere automatiquement par: python3 main.py sync-manual-inputs",
            "# Source: data/proxy_calibration.csv",
            "# Les metadonnees conservent la provenance et la fraicheur par champ.",
            "# Les observations de calibration perimees restent visibles mais ne sont pas autoritaires.",
            "# Les modifications utilisateur sont preservees comme HUMAN_MANUAL lors des synchronisations suivantes.",
            "# Ne pas modifier les cles input_origin/calibration_* manuellement.",
            "",
        ]
    )
    friendly_path.parent.mkdir(parents=True, exist_ok=True)
    with open(friendly_path, "w", encoding="utf-8") as handle:
        handle.write(header + "\n")
        config.write(handle)

    sync_log = {
        "sync_date": today.isoformat(),
        "sections_written": sections_written,
        "skipped_no_data": skipped_no_data,
        "stale_tickers": sorted(stale_tickers),
        "warning_tickers": sorted(warning_tickers),
        "no_date_tickers": sorted(no_date_tickers),
        "stale_fields": stale_fields,
        "current_fields": current_fields,
        "unknown_date_fields": unknown_date_fields,
        "freshness_policy_days": CALIBRATION_FIELD_MAX_AGE_DAYS,
        "provenance_policy": f"{PROXY_CALIBRATION_SYNC} is not {HUMAN_MANUAL}",
    }
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as handle:
        json.dump(sync_log, handle, indent=2, ensure_ascii=False)
    return sync_log


def _generated_values(row: dict[str, Any]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for csv_column, manual_field in CALIBRATION_COLUMN_MAP.items():
        raw = str(row.get(csv_column, "") or "").strip()
        if raw in MISSING:
            continue
        values[manual_field] = raw
    return values


def _human_values(existing: dict[str, Any] | None) -> dict[str, Any]:
    if not existing:
        return {}
    values: dict[str, Any] = {}
    for field in existing.get("manual_override_fields") or []:
        if field not in MANUAL_COLUMNS or field == "ticker":
            continue
        value = existing.get(field)
        if value is not None and value != "":
            values[field] = value
    return values


def _format_config_value(value: Any) -> str:
    if value is True:
        return "TRUE"
    if value is False:
        return "FALSE"
    return str(value)
