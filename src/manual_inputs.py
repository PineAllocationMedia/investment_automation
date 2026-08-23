from __future__ import annotations

import configparser
import json
from datetime import date
from pathlib import Path
from typing import Any

from .evidence_provenance import (
    CALIBRATION_CONTEXT_FIELDS,
    HUMAN_MANUAL,
    PROXY_CALIBRATION_SYNC,
    calibration_field_freshness,
    field_set,
    values_equivalent,
)
from .utils import parse_confidence, read_csv_records, safe_bool, safe_float, write_csv_records, write_text, normalize_ticker


MANUAL_COLUMNS = [
    "ticker",
    "roic_5y_avg",
    "net_margin_stable_or_expanding",
    "eps_growth_5y",
    "moat_clear",
    "eps_growth_estimated_3_5y",
    "sector_cagr_estimated",
    "forward_pe_manual",
    "peg_manual",
    "fair_value",
    "current_price_manual",
    "valuation_vs_5y_avg_ok",
    "catastrophic_fraud",
    "catastrophic_moat_lost",
    "catastrophic_growth_broken",
    "catastrophic_roic_destroyed",
    "catastrophic_dangerous_debt",
    "catastrophic_obsolete_business",
    "catastrophic_destructive_management",
    "margin_or_profitability_under_pressure",
    "forward_pe_growth_acceptable",
    "management_quality_good",
    "balance_sheet_strong",
    "regulatory_risk_high",
    "geopolitical_risk_high",
    "single_product_dependency_high",
    "manual_confidence_level",
    "notes",
]

BOOL_COLUMNS = {
    "net_margin_stable_or_expanding",
    "moat_clear",
    "valuation_vs_5y_avg_ok",
    "catastrophic_fraud",
    "catastrophic_moat_lost",
    "catastrophic_growth_broken",
    "catastrophic_roic_destroyed",
    "catastrophic_dangerous_debt",
    "catastrophic_obsolete_business",
    "catastrophic_destructive_management",
    "margin_or_profitability_under_pressure",
    "forward_pe_growth_acceptable",
    "management_quality_good",
    "balance_sheet_strong",
    "regulatory_risk_high",
    "geopolitical_risk_high",
    "single_product_dependency_high",
}

NUMERIC_COLUMNS = {
    "roic_5y_avg",
    "eps_growth_5y",
    "eps_growth_estimated_3_5y",
    "sector_cagr_estimated",
    "forward_pe_manual",
    "peg_manual",
    "fair_value",
    "current_price_manual",
}

CATASTROPHIC_COLUMNS = [
    "catastrophic_fraud",
    "catastrophic_moat_lost",
    "catastrophic_growth_broken",
    "catastrophic_roic_destroyed",
    "catastrophic_dangerous_debt",
    "catastrophic_obsolete_business",
    "catastrophic_destructive_management",
]

FRIENDLY_ALIAS_COLUMNS = {
    "margin_stable_or_expanding": "net_margin_stable_or_expanding",
    "valuation_reasonable": "valuation_vs_5y_avg_ok",
}


def parse_manual_row(row: dict[str, Any]) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    for column in MANUAL_COLUMNS:
        value = row.get(column, "")
        if column == "ticker":
            parsed[column] = normalize_ticker(value)
        elif column in BOOL_COLUMNS:
            parsed[column] = safe_bool(value)
        elif column in NUMERIC_COLUMNS:
            parsed[column] = safe_float(value)
        elif column == "manual_confidence_level":
            parsed[column] = parse_confidence(value)
        else:
            parsed[column] = str(value or "").strip()
    return parsed


def load_manual_inputs(path: str | Path) -> dict[str, dict[str, Any]]:
    records = read_csv_records(path)
    inputs: dict[str, dict[str, Any]] = {}
    for row in records:
        parsed = parse_manual_row(row)
        ticker = parsed.get("ticker")
        if ticker:
            inputs[ticker] = parsed
    return inputs


def load_friendly_manual_inputs(
    path: str | Path,
    today: date | None = None,
) -> dict[str, dict[str, Any]]:
    path = Path(path)
    if not path.exists():
        return {}
    try:
        source_text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    legacy_generated_file = "# Source: data/proxy_calibration.csv" in source_text
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    try:
        parser.read_string(source_text)
    except configparser.Error:
        return {}
    inputs: dict[str, dict[str, Any]] = {}
    for section in parser.sections():
        ticker = normalize_ticker(section)
        row = empty_manual_row(ticker)
        provided_fields: list[str] = []
        for column in MANUAL_COLUMNS:
            if column == "ticker":
                continue
            value = parser.get(section, column, fallback="")
            row[column] = value
            if str(value or "").strip():
                if not (column == "manual_confidence_level" and str(value).strip().upper() == "MEDIUM"):
                    provided_fields.append(column)
        for alias, full_column in FRIENDLY_ALIAS_COLUMNS.items():
            alias_value = parser.get(section, alias, fallback="")
            if not str(row.get(full_column) or "").strip() and str(alias_value or "").strip():
                row[full_column] = alias_value
                provided_fields.append(full_column)
        thesis_health = parser.get(section, "thesis_health", fallback="")
        main_risks = parser.get(section, "main_risks", fallback="")
        apply_simple_thesis_health(row, thesis_health)
        apply_simple_risks(row, main_risks)
        parsed = parse_manual_row(row)
        if str(thesis_health or "").strip():
            provided_fields.extend(CATASTROPHIC_COLUMNS)
            provided_fields.append("margin_or_profitability_under_pressure")
        if str(main_risks or "").strip():
            provided_fields.extend(
                [
                    "regulatory_risk_high",
                    "geopolitical_risk_high",
                    "single_product_dependency_high",
                    "margin_or_profitability_under_pressure",
                ]
            )
        provided_field_set = set(provided_fields)
        declared_origin = parser.get(section, "input_origin", fallback="").strip().upper()
        calibration_fields = field_set(parser.get(section, "calibration_synced_fields", fallback=""))
        if not calibration_fields and (declared_origin == PROXY_CALIBRATION_SYNC or legacy_generated_file):
            calibration_fields = set(provided_field_set)
        calibration_fields &= provided_field_set

        explicit_manual_fields = field_set(parser.get(section, "manual_override_fields", fallback=""))
        snapshot_values = _load_snapshot_values(
            parser.get(section, "calibration_snapshot_values", fallback="")
        )
        changed_generated_fields = {
            field
            for field in calibration_fields
            if field in snapshot_values and not values_equivalent(parsed.get(field), snapshot_values.get(field))
        }
        manual_fields = (provided_field_set - calibration_fields) | explicit_manual_fields | changed_generated_fields
        manual_fields &= provided_field_set
        calibration_fields -= manual_fields

        source_date = parser.get(section, "calibration_source_date", fallback="").strip()
        source_name = parser.get(section, "calibration_source", fallback="").strip()
        freshness_by_field = {
            field: calibration_field_freshness(field, source_date, today=today)
            for field in sorted(calibration_fields)
            if field not in CALIBRATION_CONTEXT_FIELDS
        }
        parsed["manual_override_fields"] = sorted(manual_fields)
        parsed["calibration_synced_fields"] = sorted(calibration_fields)
        parsed["calibration_current_fields"] = sorted(
            field for field, metadata in freshness_by_field.items() if metadata["status"] == "CURRENT"
        )
        parsed["calibration_stale_fields"] = sorted(
            field for field, metadata in freshness_by_field.items() if metadata["status"] == "STALE"
        )
        parsed["calibration_unknown_date_fields"] = sorted(
            field for field, metadata in freshness_by_field.items() if metadata["status"] == "UNKNOWN_DATE"
        )
        parsed["calibration_field_freshness"] = freshness_by_field
        parsed["calibration_field_source_dates"] = {
            field: metadata.get("source_date") for field, metadata in freshness_by_field.items()
        }
        parsed["calibration_source"] = source_name
        parsed["calibration_source_date"] = source_date or None
        parsed["calibration_snapshot_values"] = {
            field: snapshot_values.get(field) for field in sorted(calibration_fields) if field in snapshot_values
        }
        parsed["field_provenance"] = {
            **{field: PROXY_CALIBRATION_SYNC for field in sorted(calibration_fields)},
            **{field: HUMAN_MANUAL for field in sorted(manual_fields)},
        }
        parsed["manual_input_present"] = bool(manual_fields)
        parsed["calibration_input_present"] = bool(calibration_fields)
        if parsed.get("ticker"):
            inputs[parsed["ticker"]] = parsed
    return inputs


def _load_snapshot_values(value: str) -> dict[str, Any]:
    text = str(value or "").strip()
    if not text:
        return {}
    try:
        loaded = json.loads(text)
    except (TypeError, ValueError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def merge_manual_inputs(
    detailed: dict[str, dict[str, Any]], simple: dict[str, dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    merged = {ticker: dict(values) for ticker, values in detailed.items()}
    for ticker, simple_values in simple.items():
        if ticker not in merged:
            merged[ticker] = simple_values
            continue
        for key, value in simple_values.items():
            if key == "ticker":
                continue
            if value is not None and value != "":
                merged[ticker][key] = value
    return merged


def simple_row_to_manual(row: dict[str, Any]) -> dict[str, Any]:
    manual = empty_manual_row(normalize_ticker(row.get("ticker")))
    simple_columns = [
        "ticker",
        "roic_5y_avg",
        "eps_growth_5y",
        "eps_growth_estimated_3_5y",
        "sector_cagr_estimated",
        "forward_pe_manual",
        "peg_manual",
        "fair_value",
        "current_price_manual",
        "moat_clear",
        "margin_stable_or_expanding",
        "valuation_reasonable",
        "forward_pe_growth_acceptable",
        "management_quality_good",
        "balance_sheet_strong",
        "thesis_health",
        "main_risks",
        "manual_confidence_level",
        "notes",
    ]
    for column in simple_columns:
        value = row.get(column, "")
        if column == "ticker":
            manual["ticker"] = normalize_ticker(value)
        elif column in NUMERIC_COLUMNS:
            manual[column] = safe_float(value)
        elif column in {"moat_clear", "forward_pe_growth_acceptable", "management_quality_good", "balance_sheet_strong"}:
            manual[column] = safe_bool(value)
        elif column in FRIENDLY_ALIAS_COLUMNS:
            manual[FRIENDLY_ALIAS_COLUMNS[column]] = safe_bool(value)
        elif column == "manual_confidence_level":
            manual[column] = parse_confidence(value)
        elif column == "thesis_health":
            apply_simple_thesis_health(manual, value)
        elif column == "main_risks":
            apply_simple_risks(manual, value)
        elif column == "notes":
            manual[column] = str(value or "").strip()
    return parse_manual_row(manual)


def apply_simple_thesis_health(manual: dict[str, Any], value: Any) -> None:
    text = str(value or "").strip().upper()
    if text == "BROKEN":
        manual["catastrophic_growth_broken"] = True
    elif text == "WEAKENING":
        manual["margin_or_profitability_under_pressure"] = True
    elif text == "INTACT":
        for field in CATASTROPHIC_COLUMNS:
            manual[field] = False


def apply_simple_risks(manual: dict[str, Any], value: Any) -> None:
    risks = {
        item.strip().lower().replace(" ", "_")
        for item in str(value or "").replace(";", ",").split(",")
        if item.strip()
    }
    risk_map = {
        "regulatory": "regulatory_risk_high",
        "reglementaire": "regulatory_risk_high",
        "réglementaire": "regulatory_risk_high",
        "geopolitical": "geopolitical_risk_high",
        "geopolitique": "geopolitical_risk_high",
        "géopolitique": "geopolitical_risk_high",
        "single_product": "single_product_dependency_high",
        "produit_unique": "single_product_dependency_high",
        "margin_pressure": "margin_or_profitability_under_pressure",
        "marge": "margin_or_profitability_under_pressure",
        "fraud": "catastrophic_fraud",
        "fraude": "catastrophic_fraud",
        "moat_lost": "catastrophic_moat_lost",
        "moat": "catastrophic_moat_lost",
        "growth_broken": "catastrophic_growth_broken",
        "croissance": "catastrophic_growth_broken",
        "roic_destroyed": "catastrophic_roic_destroyed",
        "roic": "catastrophic_roic_destroyed",
        "dangerous_debt": "catastrophic_dangerous_debt",
        "debt": "catastrophic_dangerous_debt",
        "dette": "catastrophic_dangerous_debt",
        "obsolete": "catastrophic_obsolete_business",
        "management": "catastrophic_destructive_management",
    }
    for risk in risks:
        mapped = risk_map.get(risk)
        if mapped:
            manual[mapped] = True


def empty_manual_row(ticker: str) -> dict[str, Any]:
    row = {column: "" for column in MANUAL_COLUMNS}
    row["ticker"] = ticker
    row["manual_confidence_level"] = "MEDIUM"
    return row


def create_manual_template(path: str | Path, tickers: list[str]) -> None:
    rows = [empty_manual_row(ticker) for ticker in tickers]
    write_csv_records(path, rows, MANUAL_COLUMNS)


def create_friendly_manual_template(path: str | Path, tickers: list[str]) -> None:
    lines = [
        "# Fichier 2 optionnel: corrections manuelles.",
        "# L'agent remplit maintenant les donnees automatiquement autant que possible.",
        "# Vous pouvez laisser ce fichier vide et utiliser seulement portfolio.csv,",
        "# account_locations.csv et market_universe.csv.",
        "#",
        "# Utilisez ce fichier seulement si vous voulez corriger ou confirmer une donnee.",
        "# Une section = une action. Exemple:",
        "#",
        "# [MSFT]",
        "# roic_5y_avg = 25",
        "# moat_clear = TRUE",
        "# manual_confidence_level = HIGH",
        "# notes = Donnees verifiees dans le rapport annuel.",
        "#",
        "# Vrai/faux acceptes: TRUE/FALSE, yes/no, oui/non, 1/0.",
        "# manual_confidence_level accepte: HIGH, MEDIUM, LOW.",
        "# Les champs catastrophic_* doivent rester FALSE sauf probleme majeur confirme.",
        "",
    ]
    write_text(path, "\n".join(lines))


def get_manual_value(inputs: dict[str, dict[str, Any]], ticker: str, field: str) -> Any:
    return inputs.get(normalize_ticker(ticker), {}).get(field)
