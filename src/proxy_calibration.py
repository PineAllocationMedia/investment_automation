from __future__ import annotations

from pathlib import Path
from typing import Any

from .utils import normalize_ticker, read_csv_records, safe_bool, safe_float, today_iso, write_csv_records


PROXY_CALIBRATION_LEGACY_COLUMNS = [
    "ticker",
    "company_name",
    "field",
    "true_value",
    "value_type",
    "where_to_find",
    "source",
    "source_date",
    "confidence",
    "notes",
]

PROXY_CALIBRATION_FIELD_TO_FRIENDLY_COLUMN = {
    "roic_5y_avg": "roic_5y_avg_true",
    "net_margin_stable_or_expanding": "net_margin_stable_or_expanding_true",
    "eps_growth_5y": "eps_growth_5y_true",
    "eps_growth_estimated_3_5y": "eps_growth_estimated_3_5y_true",
    "sector_cagr_estimated": "sector_cagr_estimated_true",
    "forward_pe_manual": "forward_pe_true",
    "peg_manual": "peg_true",
    "fair_value": "fair_value_true",
    "valuation_vs_5y_avg_ok": "valuation_vs_5y_avg_ok_true",
    "moat_clear": "moat_clear_true",
    "forward_pe_growth_acceptable": "forward_pe_growth_acceptable_true",
    "management_quality_good": "management_quality_good_true",
    "balance_sheet_strong": "balance_sheet_strong_true",
    "margin_or_profitability_under_pressure": "margin_or_profitability_under_pressure_true",
}

PROXY_CALIBRATION_FRIENDLY_COLUMNS = [
    "ticker",
    "company_name",
    *PROXY_CALIBRATION_FIELD_TO_FRIENDLY_COLUMN.values(),
    "source",
    "source_date",
    "confidence",
    "notes",
]

PROXY_CALIBRATION_COLUMNS = PROXY_CALIBRATION_FRIENDLY_COLUMNS

PROXY_CALIBRATION_REPORT_COLUMNS = [
    "ticker",
    "company_name",
    "field",
    "true_value",
    "proxy_value",
    "difference",
    "relative_difference",
    "comparison_status",
    "recalibration_hint",
    "proxy_source",
    "source",
    "source_date",
    "confidence",
    "notes",
]

PROXY_CALIBRATION_SUMMARY_COLUMNS = [
    "field",
    "filled_examples",
    "usable_examples",
    "match_count",
    "close_count",
    "review_count",
    "missing_proxy_count",
    "invalid_count",
    "average_difference",
    "average_relative_difference",
    "bias_direction",
    "reliability_status",
    "recommended_action",
]

PROXY_CALIBRATION_HISTORY_COLUMNS = [
    "first_seen_date",
    "last_seen_date",
    "last_run_id",
    "last_mode",
    "ticker",
    "company_name",
    "field",
    "proxy_value",
    "true_value",
    "difference",
    "relative_difference",
    "error_pct",
    "comparison_status",
    "source",
    "source_date",
    "confidence",
    "observation_count",
    "evidence_key",
    "proxy_source",
    "notes",
]

PROXY_CALIBRATION_GUIDE_COLUMNS = [
    "column_to_fill",
    "meaning",
    "format",
    "where_to_find",
]

PROXY_CALIBRATION_FIELDS = [
    {
        "field": "roic_5y_avg",
        "value_type": "percent",
        "where_to_find": "ROIC ou ROE moyen 5 ans dans Morningstar ou rapports annuels. Ecrire 18 pour 18%.",
    },
    {
        "field": "net_margin_stable_or_expanding",
        "value_type": "boolean",
        "where_to_find": "Marge nette 5 ans. TRUE si stable ou en expansion. FALSE sinon.",
    },
    {
        "field": "eps_growth_5y",
        "value_type": "percent",
        "where_to_find": "Croissance EPS dilué 5 ans. Ecrire 12 pour 12%.",
    },
    {
        "field": "eps_growth_estimated_3_5y",
        "value_type": "percent",
        "where_to_find": "Croissance EPS estimée 3 à 5 ans. Ecrire 14 pour 14%.",
    },
    {
        "field": "sector_cagr_estimated",
        "value_type": "percent",
        "where_to_find": "Croissance attendue du secteur ou marché adressable. Ecrire 8 pour 8%.",
    },
    {
        "field": "forward_pe_manual",
        "value_type": "number",
        "where_to_find": "Forward PE dans BNCD Morningstar Yahoo Finance ou autre source gratuite.",
    },
    {
        "field": "peg_manual",
        "value_type": "number",
        "where_to_find": "PEG ratio dans BNCD Morningstar Yahoo Finance ou autre source gratuite.",
    },
    {
        "field": "fair_value",
        "value_type": "price",
        "where_to_find": "Fair value ou juste valeur Morningstar si disponible.",
    },
    {
        "field": "valuation_vs_5y_avg_ok",
        "value_type": "boolean",
        "where_to_find": "TRUE si la valorisation n’est pas trop au-dessus de sa moyenne 5 ans.",
    },
    {
        "field": "moat_clear",
        "value_type": "boolean",
        "where_to_find": "TRUE si Morningstar ou votre analyse confirme un avantage compétitif durable.",
    },
    {
        "field": "forward_pe_growth_acceptable",
        "value_type": "boolean",
        "where_to_find": "TRUE si le PE est raisonnable par rapport à la croissance attendue.",
    },
    {
        "field": "management_quality_good",
        "value_type": "boolean",
        "where_to_find": "TRUE si exécution et allocation du capital semblent bonnes.",
    },
    {
        "field": "balance_sheet_strong",
        "value_type": "boolean",
        "where_to_find": "TRUE si bilan solide dette raisonnable et liquidité suffisante.",
    },
    {
        "field": "margin_or_profitability_under_pressure",
        "value_type": "boolean",
        "where_to_find": "TRUE si marges ou rentabilité sous pression importante.",
    },
]

PROXY_CALIBRATION_FIELD_NAMES = [row["field"] for row in PROXY_CALIBRATION_FIELDS]

DEFAULT_PROXY_CALIBRATION_TICKERS = [
    {"ticker": "MSFT", "company_name": "Microsoft Corporation"},
    {"ticker": "MA", "company_name": "Mastercard Incorporated"},
    {"ticker": "AAPL", "company_name": "Apple Inc."},
    {"ticker": "GOOGL", "company_name": "Alphabet Inc."},
    {"ticker": "AVGO", "company_name": "Broadcom Inc."},
    {"ticker": "INTU", "company_name": "Intuit Inc."},
    {"ticker": "COST", "company_name": "Costco Wholesale Corporation"},
    {"ticker": "NVDA", "company_name": "NVIDIA Corporation"},
    {"ticker": "CSU.TO", "company_name": "Constellation Software Inc."},
    {"ticker": "WSP.TO", "company_name": "WSP Global Inc."},
    {"ticker": "", "company_name": ""},
    {"ticker": "", "company_name": ""},
    {"ticker": "", "company_name": ""},
    {"ticker": "", "company_name": ""},
    {"ticker": "", "company_name": ""},
]

BOOLEAN_FIELDS = {
    "net_margin_stable_or_expanding",
    "valuation_vs_5y_avg_ok",
    "moat_clear",
    "forward_pe_growth_acceptable",
    "management_quality_good",
    "balance_sheet_strong",
    "margin_or_profitability_under_pressure",
}

PERCENT_POINT_FIELDS = {
    "roic_5y_avg",
    "eps_growth_5y",
    "eps_growth_estimated_3_5y",
    "sector_cagr_estimated",
}

MISSING_TRUE_VALUE_MARKERS = {"", "X", "N/A", "NA", "N.D.", "ND", "N/D", "NON DISPONIBLE", "PAS DISPONIBLE"}


def create_proxy_calibration_template(
    path: str | Path,
    tickers: list[dict[str, Any]] | None = None,
) -> None:
    rows: list[dict[str, Any]] = []
    for ticker_row in tickers or DEFAULT_PROXY_CALIBRATION_TICKERS:
        ticker = normalize_ticker(ticker_row.get("ticker"))
        company_name = str(ticker_row.get("company_name") or "").strip()
        rows.append(
            {
                "ticker": ticker,
                "company_name": company_name,
                "source": "",
                "source_date": "",
                "confidence": "HIGH" if ticker else "",
                "notes": "",
            }
        )
    write_csv_records(path, rows, PROXY_CALIBRATION_COLUMNS)


def create_proxy_calibration_field_guide(path: str | Path) -> None:
    rows = []
    for field_row in PROXY_CALIBRATION_FIELDS:
        field = field_row["field"]
        rows.append(
            {
                "column_to_fill": PROXY_CALIBRATION_FIELD_TO_FRIENDLY_COLUMN[field],
                "meaning": field,
                "format": _friendly_format_for_field(field),
                "where_to_find": field_row["where_to_find"],
            }
        )
    rows.extend(
        [
            {
                "column_to_fill": "source",
                "meaning": "Source utilisée pour vos vraies données",
                "format": "texte",
                "where_to_find": "Exemple: Morningstar, BNCD, rapport annuel, TIKR gratuit, macrotrends, etc.",
            },
            {
                "column_to_fill": "source_date",
                "meaning": "Date ou période de la source",
                "format": "YYYY-MM-DD ou année",
                "where_to_find": "Date du rapport ou période des données.",
            },
            {
                "column_to_fill": "confidence",
                "meaning": "Votre confiance dans les vraies données entrées",
                "format": "HIGH / MEDIUM / LOW",
                "where_to_find": "Utiliser HIGH si la source est fiable et récente.",
            },
            {
                "column_to_fill": "notes",
                "meaning": "Commentaire optionnel",
                "format": "texte court",
                "where_to_find": "Expliquer une nuance si nécessaire.",
            },
        ]
    )
    write_csv_records(path, rows, PROXY_CALIBRATION_GUIDE_COLUMNS)


def create_proxy_calibration_history(path: str | Path) -> None:
    write_csv_records(path, [], PROXY_CALIBRATION_HISTORY_COLUMNS)


def load_proxy_calibration_inputs(path: str | Path) -> list[dict[str, Any]]:
    path = Path(path)
    if not path.exists():
        return []
    records = read_csv_records(path)
    if not records:
        return []
    if "field" not in records[0]:
        return _load_friendly_proxy_calibration_inputs(records)
    return _load_legacy_proxy_calibration_inputs(records)


def _load_legacy_proxy_calibration_inputs(records: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in records:
        ticker = normalize_ticker(row.get("ticker"))
        field = str(row.get("field") or "").strip()
        if not ticker or not field:
            continue
        rows.append(
            {
                "ticker": ticker,
                "company_name": str(row.get("company_name") or "").strip(),
                "field": field,
                "true_value": _clean_true_value(row.get("true_value")),
                "value_type": str(row.get("value_type") or "").strip(),
                "where_to_find": str(row.get("where_to_find") or "").strip(),
                "source": str(row.get("source") or "").strip(),
                "source_date": str(row.get("source_date") or "").strip(),
                "confidence": str(row.get("confidence") or "").strip().upper() or "MEDIUM",
                "notes": str(row.get("notes") or "").strip(),
            }
        )
    return rows


def _load_friendly_proxy_calibration_inputs(records: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in records:
        ticker = normalize_ticker(row.get("ticker"))
        if not ticker:
            continue
        company_name = str(row.get("company_name") or "").strip()
        source = str(row.get("source") or "").strip()
        source_date = str(row.get("source_date") or "").strip()
        confidence = str(row.get("confidence") or "").strip().upper() or "MEDIUM"
        notes = str(row.get("notes") or "").strip()
        for field, column in PROXY_CALIBRATION_FIELD_TO_FRIENDLY_COLUMN.items():
            value = _clean_true_value(row.get(column))
            rows.append(
                {
                    "ticker": ticker,
                    "company_name": company_name,
                    "field": field,
                    "true_value": value,
                    "value_type": _value_type_for_field(field),
                    "where_to_find": _where_to_find_for_field(field),
                    "source": source,
                    "source_date": source_date,
                    "confidence": confidence,
                    "notes": notes,
                }
            )
    return rows


def clear_proxy_calibration_values(path: str | Path) -> int:
    """Clear user-entered truth data while keeping the calibration template shape."""

    path = Path(path)
    if not path.exists():
        return 0
    rows = read_csv_records(path)
    if not rows:
        return 0
    if "field" in rows[0]:
        return _clear_legacy_proxy_calibration_values(path, rows)
    return _clear_friendly_proxy_calibration_values(path, rows)


def _clear_legacy_proxy_calibration_values(path: Path, rows: list[dict[str, str]]) -> int:
    cleared = 0
    cleaned_rows = []
    for row in rows:
        had_user_value = any(str(row.get(column) or "").strip() for column in ["true_value", "source", "source_date", "notes"])
        if had_user_value:
            cleared += 1
        cleaned = dict(row)
        cleaned["true_value"] = ""
        cleaned["source"] = ""
        cleaned["source_date"] = ""
        cleaned["notes"] = ""
        cleaned_rows.append(cleaned)
    write_csv_records(path, cleaned_rows, PROXY_CALIBRATION_LEGACY_COLUMNS)
    return cleared


def _clear_friendly_proxy_calibration_values(path: Path, rows: list[dict[str, str]]) -> int:
    cleared = 0
    cleaned_rows = []
    true_columns = set(PROXY_CALIBRATION_FIELD_TO_FRIENDLY_COLUMN.values())
    for row in rows:
        had_user_value = any(str(row.get(column) or "").strip() for column in [*true_columns, "source", "source_date", "notes"])
        if had_user_value:
            cleared += 1
        cleaned = dict(row)
        for column in true_columns:
            cleaned[column] = ""
        cleaned["source"] = ""
        cleaned["source_date"] = ""
        cleaned["notes"] = ""
        cleaned_rows.append(cleaned)
    write_csv_records(path, cleaned_rows, PROXY_CALIBRATION_COLUMNS)
    return cleared


def build_proxy_calibration_report(
    analysis_groups: list[dict[str, dict[str, Any]]],
    calibration_inputs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    analyses: dict[str, dict[str, Any]] = {}
    for group in analysis_groups:
        analyses.update(group)

    rows: list[dict[str, Any]] = []
    for calibration in calibration_inputs:
        ticker = calibration["ticker"]
        field = calibration["field"]
        analysis = analyses.get(ticker)
        if not analysis:
            rows.append(_missing_analysis_row(calibration))
            continue
        rows.append(_comparison_row(calibration, analysis))
    return rows


def build_proxy_calibration_summary(report_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in report_rows:
        field = str(row.get("field") or "").strip()
        if not field:
            continue
        grouped.setdefault(field, []).append(row)

    summary_rows = []
    for field_row in PROXY_CALIBRATION_FIELDS:
        field = field_row["field"]
        rows = grouped.get(field, [])
        filled = [row for row in rows if str(row.get("true_value") or "").strip()]
        statuses = [str(row.get("comparison_status") or "") for row in filled]
        usable = [
            row
            for row in filled
            if row.get("comparison_status") in {"MATCH", "CLOSE", "REVIEW_PROXY"}
        ]
        differences = [safe_float(row.get("difference")) for row in usable]
        differences = [value for value in differences if value is not None]
        relatives = [safe_float(row.get("relative_difference")) for row in usable]
        relatives = [value for value in relatives if value is not None]
        avg_difference = _average(differences)
        avg_relative = _average(relatives)
        summary_rows.append(
            {
                "field": field,
                "filled_examples": len(filled),
                "usable_examples": len(usable),
                "match_count": statuses.count("MATCH"),
                "close_count": statuses.count("CLOSE"),
                "review_count": statuses.count("REVIEW_PROXY"),
                "missing_proxy_count": statuses.count("PROXY_MISSING"),
                "invalid_count": statuses.count("INVALID_TRUE_VALUE") + statuses.count("PROXY_UNUSABLE"),
                "average_difference": round(avg_difference, 4) if avg_difference is not None else "",
                "average_relative_difference": round(avg_relative, 4) if avg_relative is not None else "",
                "bias_direction": _bias_direction(field, avg_difference),
                "reliability_status": _summary_reliability_status(filled, usable, statuses, avg_relative),
                "recommended_action": _summary_recommended_action(field, filled, usable, statuses, avg_difference, avg_relative),
            }
        )
    return summary_rows


def update_proxy_calibration_history(
    path: str | Path,
    report_rows: list[dict[str, Any]],
    *,
    run_id: str = "",
    mode: str = "",
    snapshot_date: str | None = None,
) -> list[dict[str, Any]]:
    """Persist usable proxy calibration evidence without duplicating repeated runs.

    The user-facing calibration CSV is a work file. This history is the durable
    evidence store that future bias detection can use. Re-running the same
    analysis with the same true value/source updates the row instead of counting
    it as a fresh independent example.
    """

    path = Path(path)
    snapshot_date = (snapshot_date or today_iso())[:10]
    existing = read_csv_records(path)
    by_key = {str(row.get("evidence_key") or ""): dict(row) for row in existing if str(row.get("evidence_key") or "")}

    for evidence in build_proxy_calibration_history_rows(
        report_rows,
        run_id=run_id,
        mode=mode,
        snapshot_date=snapshot_date,
    ):
        key = str(evidence.get("evidence_key") or "")
        if not key:
            continue
        previous = by_key.get(key)
        if previous:
            evidence["first_seen_date"] = previous.get("first_seen_date") or evidence["first_seen_date"]
            evidence["observation_count"] = int(safe_float(previous.get("observation_count")) or 1) + 1
        by_key[key] = evidence

    rows = sorted(
        by_key.values(),
        key=lambda row: (
            str(row.get("field") or ""),
            str(row.get("ticker") or ""),
            str(row.get("source_date") or ""),
            str(row.get("true_value") or ""),
        ),
    )
    write_csv_records(path, rows, PROXY_CALIBRATION_HISTORY_COLUMNS)
    return rows


def build_proxy_calibration_history_rows(
    report_rows: list[dict[str, Any]],
    *,
    run_id: str = "",
    mode: str = "",
    snapshot_date: str | None = None,
) -> list[dict[str, Any]]:
    snapshot_date = (snapshot_date or today_iso())[:10]
    rows = []
    for row in report_rows:
        history_row = _history_row_from_report_row(row, run_id=run_id, mode=mode, snapshot_date=snapshot_date)
        if history_row:
            rows.append(history_row)
    return rows


def _missing_analysis_row(calibration: dict[str, Any]) -> dict[str, Any]:
    return {
        "ticker": calibration.get("ticker"),
        "company_name": calibration.get("company_name"),
        "field": calibration.get("field"),
        "true_value": calibration.get("true_value"),
        "proxy_value": "",
        "difference": "",
        "relative_difference": "",
        "comparison_status": "TICKER_NOT_ANALYZED",
        "recalibration_hint": "Ajouter ce ticker au portfolio ou au market_universe pour que l’agent puisse calculer le proxy.",
        "proxy_source": "",
        "source": calibration.get("source"),
        "source_date": calibration.get("source_date"),
        "confidence": calibration.get("confidence"),
        "notes": calibration.get("notes"),
    }


def _history_row_from_report_row(
    row: dict[str, Any],
    *,
    run_id: str,
    mode: str,
    snapshot_date: str,
) -> dict[str, Any] | None:
    status = str(row.get("comparison_status") or "").strip()
    if status not in {"MATCH", "CLOSE", "REVIEW_PROXY"}:
        return None
    ticker = normalize_ticker(row.get("ticker"))
    field = str(row.get("field") or "").strip()
    true_value = str(row.get("true_value") or "").strip()
    proxy_value = str(row.get("proxy_value") or "").strip()
    if not ticker or not field or not true_value or not proxy_value:
        return None
    confidence = str(row.get("confidence") or "").strip().upper() or "MEDIUM"
    source = str(row.get("source") or "").strip()
    source_date = str(row.get("source_date") or "").strip()
    difference = safe_float(row.get("difference"))
    relative = safe_float(row.get("relative_difference"))
    evidence_key = _proxy_evidence_key(ticker, field, true_value, source, source_date)
    return {
        "first_seen_date": snapshot_date,
        "last_seen_date": snapshot_date,
        "last_run_id": run_id,
        "last_mode": mode,
        "ticker": ticker,
        "company_name": str(row.get("company_name") or "").strip(),
        "field": field,
        "proxy_value": proxy_value,
        "true_value": true_value,
        "difference": round(difference, 6) if difference is not None else "",
        "relative_difference": round(relative, 6) if relative is not None else "",
        "error_pct": round(relative * 100, 4) if relative is not None else "",
        "comparison_status": status,
        "source": source,
        "source_date": source_date,
        "confidence": confidence,
        "observation_count": 1,
        "evidence_key": evidence_key,
        "proxy_source": str(row.get("proxy_source") or "").strip(),
        "notes": str(row.get("notes") or "").strip(),
    }


def _proxy_evidence_key(ticker: str, field: str, true_value: str, source: str, source_date: str) -> str:
    parts = [
        normalize_ticker(ticker),
        field.strip(),
        _canonical_evidence_value(true_value),
        source.strip().upper(),
        source_date.strip(),
    ]
    return "|".join(parts)


def _canonical_evidence_value(value: Any) -> str:
    number = safe_float(value)
    if number is not None:
        return f"{number:.6f}"
    return str(value or "").strip().upper()


def _comparison_row(calibration: dict[str, Any], analysis: dict[str, Any]) -> dict[str, Any]:
    field = calibration["field"]
    true_text = _clean_true_value(calibration.get("true_value"))
    proxy_values = analysis.get("raw_auto_proxy_values") or {}
    proxy_value = proxy_values.get(field)
    if proxy_value is None and field in {"forward_pe_manual", "peg_manual"}:
        proxy_value = proxy_values.get(field.replace("_manual", ""))
    proxy_source = _proxy_source_for_field(analysis, field)

    if not true_text:
        status = "WAITING_FOR_TRUE_VALUE"
        difference = ""
        relative = ""
        hint = "Remplir true_value pour comparer la vraie donnée au proxy automatique."
    elif proxy_value is None or proxy_value == "":
        status = "PROXY_MISSING"
        difference = ""
        relative = ""
        hint = "Le modèle n’a pas réussi à estimer ce champ automatiquement. Une source manuelle reste utile."
    elif field in BOOLEAN_FIELDS:
        status, difference, relative, hint = _compare_boolean(true_text, proxy_value)
    else:
        status, difference, relative, hint = _compare_numeric(field, true_text, proxy_value)

    return {
        "ticker": calibration.get("ticker"),
        "company_name": calibration.get("company_name") or analysis.get("company_name_found", ""),
        "field": field,
        "true_value": true_text,
        "proxy_value": _display_value(proxy_value),
        "difference": difference,
        "relative_difference": relative,
        "comparison_status": status,
        "recalibration_hint": hint,
        "proxy_source": proxy_source,
        "source": calibration.get("source"),
        "source_date": calibration.get("source_date"),
        "confidence": calibration.get("confidence"),
        "notes": calibration.get("notes"),
    }


def _compare_boolean(true_text: str, proxy_value: Any) -> tuple[str, str, str, str]:
    true_bool = safe_bool(true_text)
    proxy_bool = safe_bool(proxy_value)
    if true_bool is None:
        return (
            "INVALID_TRUE_VALUE",
            "",
            "",
            "Utiliser TRUE ou FALSE pour ce champ.",
        )
    if proxy_bool is None:
        return (
            "PROXY_UNUSABLE",
            "",
            "",
            "Le proxy automatique n’est pas lisible comme TRUE/FALSE.",
        )
    if true_bool == proxy_bool:
        return (
            "MATCH",
            "0",
            "0",
            "Le proxy donne la même conclusion que la vraie donnée.",
        )
    return (
        "REVIEW_PROXY",
        "opposé",
        "",
        "Le proxy donne la conclusion inverse. Ce champ mérite une recalibration ou une validation manuelle prioritaire.",
    )


def _compare_numeric(field: str, true_text: str, proxy_value: Any) -> tuple[str, str, str, str]:
    true_number = safe_float(true_text)
    proxy_number = safe_float(proxy_value)
    if true_number is None:
        return (
            "INVALID_TRUE_VALUE",
            "",
            "",
            "Utiliser un nombre simple. Exemple: 18 pour 18%.",
        )
    if proxy_number is None:
        return (
            "PROXY_UNUSABLE",
            "",
            "",
            "Le proxy automatique n’est pas lisible comme nombre.",
        )

    difference = proxy_number - true_number
    relative = difference / abs(true_number) if true_number else None
    status = _numeric_status(field, abs(difference), abs(relative) if relative is not None else None)
    if status == "MATCH":
        hint = "Le proxy est assez proche pour ce champ."
    elif status == "CLOSE":
        hint = "Le proxy est utilisable mais imparfait. Surveiller si plusieurs titres montrent le même biais."
    else:
        hint = "Écart important. Ce champ pourrait nécessiter une meilleure source ou une recalibration du proxy."
    return status, round(difference, 4), round(relative, 4) if relative is not None else "", hint


def _numeric_status(field: str, abs_difference: float, abs_relative: float | None) -> str:
    if field in PERCENT_POINT_FIELDS:
        if abs_difference <= 2.5:
            return "MATCH"
        if abs_difference <= 5.0:
            return "CLOSE"
        return "REVIEW_PROXY"

    if abs_relative is not None:
        if abs_relative <= 0.15:
            return "MATCH"
        if abs_relative <= 0.25:
            return "CLOSE"
        return "REVIEW_PROXY"

    if abs_difference <= 1.0:
        return "MATCH"
    if abs_difference <= 2.0:
        return "CLOSE"
    return "REVIEW_PROXY"


def _average(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _bias_direction(field: str, avg_difference: float | None) -> str:
    if avg_difference is None or field in BOOLEAN_FIELDS:
        return "NON_NUMERIC_OR_NOT_ENOUGH_DATA"
    threshold = 2.5 if field in PERCENT_POINT_FIELDS else 0.10
    if avg_difference > threshold:
        return "PROXY_TOO_HIGH"
    if avg_difference < -threshold:
        return "PROXY_TOO_LOW"
    return "NO_CLEAR_BIAS"


def _summary_reliability_status(
    filled: list[dict[str, Any]],
    usable: list[dict[str, Any]],
    statuses: list[str],
    avg_relative: float | None,
) -> str:
    if not filled:
        return "WAITING_FOR_EXAMPLES"
    if len(usable) < 3:
        return "NEED_MORE_EXAMPLES"
    review_rate = statuses.count("REVIEW_PROXY") / len(filled)
    good_rate = (statuses.count("MATCH") + statuses.count("CLOSE")) / len(filled)
    if review_rate >= 0.40:
        return "RECALIBRATION_CANDIDATE"
    if avg_relative is not None and abs(avg_relative) >= 0.25:
        return "RECALIBRATION_CANDIDATE"
    if good_rate >= 0.80:
        return "PROXY_ACCEPTABLE"
    return "MONITOR_MORE_EXAMPLES"


def _summary_recommended_action(
    field: str,
    filled: list[dict[str, Any]],
    usable: list[dict[str, Any]],
    statuses: list[str],
    avg_difference: float | None,
    avg_relative: float | None,
) -> str:
    if not filled:
        return "Remplir plusieurs exemples pour auditer ce proxy."
    if len(usable) < 3:
        return "Ajouter au moins 3 exemples utilisables avant de modifier la formule."
    status = _summary_reliability_status(filled, usable, statuses, avg_relative)
    if status == "PROXY_ACCEPTABLE":
        return "Garder la formule actuelle; le proxy semble assez fiable sur cet échantillon."
    if status == "RECALIBRATION_CANDIDATE":
        direction = _bias_direction(field, avg_difference)
        if field in BOOLEAN_FIELDS:
            return "Revoir les règles TRUE/FALSE; plusieurs conclusions semblent inversées ou fragiles."
        if direction == "PROXY_TOO_HIGH":
            return "Candidat à recalibrer: le proxy semble surestimer cette donnée de façon répétée."
        if direction == "PROXY_TOO_LOW":
            return "Candidat à recalibrer: le proxy semble sous-estimer cette donnée de façon répétée."
        return "Candidat à recalibrer: les erreurs sont importantes même sans biais simple."
    return "Continuer à accumuler quelques exemples avant de changer la formule."


def _proxy_source_for_field(analysis: dict[str, Any], field: str) -> str:
    notes = analysis.get("raw_auto_proxy_source_notes") or analysis.get("auto_source_notes") or []
    for note in notes:
        text = str(note)
        if text.startswith(f"{field}:"):
            return text
        if field in {"forward_pe_manual", "peg_manual"} and text.startswith(f"{field.replace('_manual', '')}:"):
            return text
    return "Proxy automatique interne si disponible."


def _display_value(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 4)
    return value


def _clean_true_value(value: Any) -> str:
    text = str(value or "").strip()
    if text.upper() in MISSING_TRUE_VALUE_MARKERS:
        return ""
    return text


def _value_type_for_field(field: str) -> str:
    for row in PROXY_CALIBRATION_FIELDS:
        if row["field"] == field:
            return str(row.get("value_type") or "")
    return ""


def _where_to_find_for_field(field: str) -> str:
    for row in PROXY_CALIBRATION_FIELDS:
        if row["field"] == field:
            return str(row.get("where_to_find") or "")
    return ""


def _friendly_format_for_field(field: str) -> str:
    if field in BOOLEAN_FIELDS:
        return "TRUE ou FALSE"
    if field in PERCENT_POINT_FIELDS:
        return "nombre en pourcentage; écrire 18 pour 18%"
    if field in {"forward_pe_manual", "peg_manual"}:
        return "nombre simple"
    if field == "fair_value":
        return "prix ou juste valeur par action"
    return "nombre simple"
