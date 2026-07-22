from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any

from .add_eligibility_engine import ADD_ALLOWED_STATUSES
from .asset_type_engine import is_etf_asset, is_etf_asset_analysis
from .manual_inputs import BOOL_COLUMNS, MANUAL_COLUMNS, NUMERIC_COLUMNS, empty_manual_row, parse_manual_row
from .utils import (
    BNCD_MORNINGSTAR_DIR,
    REPORTS_DIR,
    RESEARCH_REPORTS_DIR,
    normalize_ticker,
    read_csv_records,
    safe_bool,
    safe_float,
    write_csv_records,
)


RESEARCH_INDEX_COLUMNS = ["ticker", "provider", "report_date", "file_name", "notes"]
RESEARCH_NEEDED_COLUMNS = [
    "ticker",
    "ticker_display",
    "universe",
    "company_name",
    "data_quality",
    "ticker_validation_status",
    "ticker_coverage_status",
    "missing_critical_count",
    "auto_estimate_count",
    "priority",
    "need_type",
    "reason",
    "suggested_action",
    "suggested_file_name",
    "ticker_potential_score",
]
RESEARCH_STATUS_COLUMNS = [
    "file_name",
    "ticker_detected",
    "provider",
    "report_date",
    "readable",
    "text_characters",
    "text_quality_status",
    "text_quality_score",
    "extraction_method",
    "ocr_status",
    "extracted_fields",
    "field_count",
    "extraction_warnings",
    "status",
    "message",
]
SUPPORTED_REPORT_EXTENSIONS = {".pdf", ".txt", ".md"}
RESEARCH_HELPFUL_FIELDS = {
    "fair_value",
    "roic_5y_avg",
    "eps_growth_estimated_3_5y",
    "forward_pe_manual",
    "peg_manual",
    "moat_clear",
    "valuation_vs_5y_avg_ok",
    "balance_sheet_strong",
    "management_quality_good",
    "margin_or_profitability_under_pressure",
    "regulatory_risk_high",
    "geopolitical_risk_high",
    "single_product_dependency_high",
}
RESEARCH_PRIMARY_FIELDS = {
    "fair_value",
    "roic_5y_avg",
    "eps_growth_estimated_3_5y",
    "moat_clear",
    "valuation_vs_5y_avg_ok",
}
DESCRIPTIVE_RESEARCH_FIELDS = {
    "research_report_company_description",
    "research_report_company_description_source",
    "research_report_company_description_date",
    "research_report_company_description_source_rank",
    "research_report_company_description_source_type",
    "research_report_sector",
    "research_report_industry",
}
PRIORITY_RESEARCH_FIELDS = {"fair_value", "roic_5y_avg"}
MORNINGSTAR_RESEARCH_SOURCE_TYPES = {"MORNINGSTAR_ANALYST", "MORNINGSTAR_TEAR_SHEET"}
COMMON_NON_TICKER_FILENAME_TOKENS = {
    "ANALYSIS",
    "ANALYSE",
    "BNCD",
    "EQUITY",
    "MORNINGSTAR",
    "REPORT",
    "RESEARCH",
    "RAPPORT",
}


def create_research_report_scaffold() -> None:
    BNCD_MORNINGSTAR_DIR.mkdir(parents=True, exist_ok=True)
    readme_path = BNCD_MORNINGSTAR_DIR / "README.md"
    if not readme_path.exists():
        readme_path.write_text(
            "# Rapports BNCD / Morningstar\n\n"
            "Déposez ici les PDF que vous téléchargez depuis BNCD/Morningstar.\n\n"
            "Nom recommandé :\n\n"
            "```text\n"
            "CSU.TO_2026-04-15_BNCD_Morningstar.pdf\n"
            "WSP.TO_2026-04-15_BNCD_Morningstar.pdf\n"
            "BAM_2026-04-15_BNCD_Morningstar.pdf\n"
            "```\n\n"
            "L’agent essaie d’identifier le ticker dans le nom du fichier. "
            "Si le nom du fichier n’est pas clair, remplissez `data/research_reports/research_index.csv`.\n\n"
            "Les données extraites servent seulement à combler certains champs manquants. "
            "Elles doivent être validées manuellement.\n",
            encoding="utf-8",
        )
    index_path = RESEARCH_REPORTS_DIR / "research_index.csv"
    if not index_path.exists():
        write_csv_records(index_path, [], RESEARCH_INDEX_COLUMNS)


def load_research_report_inputs(
    report_dir: str | Path = BNCD_MORNINGSTAR_DIR,
    index_path: str | Path = RESEARCH_REPORTS_DIR / "research_index.csv",
    known_tickers: list[str] | None = None,
) -> dict[str, dict[str, Any]]:
    report_dir = Path(report_dir)
    index_path = Path(index_path)
    known = [normalize_ticker(ticker) for ticker in (known_tickers or []) if normalize_ticker(ticker)]
    indexed = _indexed_reports(index_path)
    rows_by_ticker: dict[str, list[dict[str, Any]]] = {}

    for path in sorted(report_dir.glob("*")):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_REPORT_EXTENSIONS:
            continue
        index_row = indexed.get(path.name, {})
        ticker = normalize_ticker(index_row.get("ticker")) or infer_ticker_from_filename(path.name, known)
        if not ticker:
            continue
        report = parse_research_report(path, ticker, index_row)
        rows_by_ticker.setdefault(ticker, []).append(report)

    merged: dict[str, dict[str, Any]] = {}
    for ticker, reports in rows_by_ticker.items():
        merged[ticker] = merge_research_rows(ticker, reports)
    return merged


def parse_research_report(path: str | Path, ticker: str, index_row: dict[str, Any] | None = None) -> dict[str, Any]:
    path = Path(path)
    index_row = index_row or {}
    extraction = extract_report_text_detailed(path)
    text = str(extraction.get("text") or "")
    error = str(extraction.get("error") or "")
    row = empty_manual_row(ticker)
    extracted_fields: list[str] = []
    extraction_notes: list[str] = []
    extraction_warnings: list[str] = list(extraction.get("warnings") or [])
    field_sources: dict[str, str] = {}
    field_confidence: dict[str, str] = {}
    source_rank, source_type = _classify_research_report_source(text)

    def set_field(field: str, value: Any, source: str = "") -> None:
        if field not in MANUAL_COLUMNS or field == "ticker":
            return
        if value is None or value == "":
            return
        row[field] = value
        extracted_fields.append(field)
        if source:
            field_sources[field] = source
            field_confidence[field] = research_field_confidence(field, source, extraction)
            extraction_notes.append(f"{field}: {source}")

    if text:
        moat_value, moat_source, moat_warnings = extract_morningstar_moat_clear(text)
        valuation_value, valuation_source, valuation_warnings = extract_morningstar_valuation_ok(text)
        extraction_warnings.extend(moat_warnings)
        extraction_warnings.extend(valuation_warnings)

        fair_value, fair_value_source, fair_value_warnings = _extract_fair_value_estimate(text)
        extraction_warnings.extend(fair_value_warnings)
        set_field("fair_value", fair_value, fair_value_source)
        roic_value = extract_percent_number(text, ROIC_PATTERNS)
        roic_source = "ROIC text pattern"
        if roic_value is not None and source_type not in {"MORNINGSTAR_ANALYST", "MORNINGSTAR_TEAR_SHEET"}:
            roic_source = "ROIC TTM courtier — définition divergente"
            extraction_warnings.append(
                "ROIC: source courtier non-Morningstar utilisée comme dernier recours; définition divergente du champ 5 ans."
            )
        set_field("roic_5y_avg", roic_value, roic_source)
        set_field("eps_growth_estimated_3_5y", extract_percent_number(text, EPS_GROWTH_PATTERNS), "EPS growth text pattern")
        forward_pe = extract_valuation_analysis_current_value(text, "Forward P/E")
        forward_pe_source = "forward PE text pattern"
        if forward_pe is None:
            forward_pe = extract_nbccm_forward_pe_estimate(text)
            if forward_pe is not None:
                forward_pe_source = "NBCCM estimates P/E 2026E"
        set_field(
            "forward_pe_manual",
            forward_pe if forward_pe is not None else extract_first_number(text, FORWARD_PE_PATTERNS),
            forward_pe_source,
        )
        set_field("peg_manual", extract_first_number(text, PEG_PATTERNS), "PEG text pattern")
        set_field("moat_clear", moat_value, moat_source)
        set_field("valuation_vs_5y_avg_ok", valuation_value, valuation_source)
        set_field(
            "margin_or_profitability_under_pressure",
            extract_bool_from_patterns(text, TRUE_MARGIN_PRESSURE_PATTERNS, FALSE_MARGIN_PRESSURE_PATTERNS),
            "margin pressure text pattern",
        )
        set_field("balance_sheet_strong", extract_bool_from_patterns(text, TRUE_BALANCE_PATTERNS, FALSE_BALANCE_PATTERNS), "balance sheet text pattern")
        set_field("management_quality_good", extract_bool_from_patterns(text, TRUE_MANAGEMENT_PATTERNS, FALSE_MANAGEMENT_PATTERNS), "management text pattern")
        set_field("regulatory_risk_high", extract_bool_from_patterns(text, TRUE_REGULATORY_PATTERNS, []), "regulatory risk text pattern")
        set_field("geopolitical_risk_high", extract_bool_from_patterns(text, TRUE_GEOPOLITICAL_PATTERNS, []), "geopolitical risk text pattern")
        set_field("single_product_dependency_high", extract_bool_from_patterns(text, TRUE_SINGLE_PRODUCT_PATTERNS, []), "single product text pattern")

    source_name = path.name
    provider = str(index_row.get("provider") or "BNCD/Morningstar").strip()
    report_date = str(index_row.get("report_date") or date_from_filename(path.name) or "").strip()
    descriptive_fields = _extract_descriptive_research_fields(text) if text else {}
    if descriptive_fields:
        parsed_report_date = _parse_research_report_date(report_date)
        if parsed_report_date and (date.today() - parsed_report_date).days > 730:
            extraction_warnings.append("Description: champ informationnel ignoré, rapport de plus de 24 mois.")
            descriptive_fields = {}
        elif not parsed_report_date:
            extraction_warnings.append(
                "Description: date de rapport inconnue; plafond 24 mois non appliqué à ce champ informationnel."
            )
    row["manual_confidence_level"] = "HIGH" if {"fair_value", "moat_clear"} <= set(extracted_fields) else "MEDIUM"
    row["notes"] = (
        f"Données extraites automatiquement du rapport local {source_name}. "
        "À valider manuellement; ne pas republier de longs extraits du rapport."
    )
    parsed = parse_manual_row(row)
    parsed["research_report_fields"] = sorted(set(extracted_fields))
    parsed["research_report_sources"] = [source_name]
    parsed["research_report_provider"] = provider
    parsed["research_report_dates"] = [report_date] if report_date else []
    parsed["research_report_source_rank"] = source_rank
    parsed["research_report_source_type"] = source_type
    parsed["research_report_status"] = "FOUND_FIELDS" if extracted_fields else "NO_FIELDS_EXTRACTED"
    parsed["research_report_error"] = error
    parsed["research_report_extraction_notes"] = sorted(set(extraction_notes))
    parsed["research_report_extraction_warnings"] = sorted(set(extraction_warnings))
    parsed["research_report_field_sources"] = field_sources
    parsed["research_report_field_confidence"] = field_confidence
    parsed["research_report_text_quality_status"] = extraction.get("text_quality_status")
    parsed["research_report_text_quality_score"] = extraction.get("text_quality_score")
    parsed["research_report_extraction_method"] = extraction.get("extraction_method")
    parsed["research_report_ocr_status"] = extraction.get("ocr_status")
    parsed["research_report_text_characters"] = extraction.get("text_characters")
    parsed["research_report_extraction_messages"] = extraction.get("messages", [])
    if descriptive_fields:
        parsed.update(descriptive_fields)
        parsed["research_report_company_description_source"] = source_name
        parsed["research_report_company_description_date"] = report_date
    return parsed


def merge_research_rows(ticker: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    merged = empty_manual_row(ticker)
    fields: list[str] = []
    sources: list[str] = []
    dates: list[str] = []
    errors: list[str] = []
    notes: list[str] = []
    warnings: list[str] = []
    field_sources: dict[str, str] = {}
    field_confidence: dict[str, str] = {}
    text_quality_statuses: list[str] = []
    extraction_methods: list[str] = []
    ocr_statuses: list[str] = []
    quality_scores: list[float] = []
    text_characters: list[float] = []
    extraction_messages: list[str] = []
    for row in sorted(rows, key=lambda item: _latest_date_text(item), reverse=True):
        row_fields = set(row.get("research_report_fields") or [])
        for field in row_fields:
            if field in PRIORITY_RESEARCH_FIELDS:
                continue
            value = row.get(field)
            if value is not None and value != "" and merged.get(field) in {None, ""}:
                merged[field] = value
                fields.append(field)
                source = (row.get("research_report_field_sources") or {}).get(field)
                if source:
                    field_sources[field] = source
                confidence = (row.get("research_report_field_confidence") or {}).get(field)
                if confidence:
                    field_confidence[field] = str(confidence)
        sources.extend(str(source) for source in row.get("research_report_sources") or [])
        dates.extend(str(report_date) for report_date in row.get("research_report_dates") or [] if report_date)
        notes.extend(str(note) for note in row.get("research_report_extraction_notes") or [])
        warnings.extend(str(warning) for warning in row.get("research_report_extraction_warnings") or [])
        if row_fields and row.get("research_report_text_quality_status"):
            text_quality_statuses.append(str(row.get("research_report_text_quality_status")))
        if row_fields and row.get("research_report_extraction_method"):
            extraction_methods.append(str(row.get("research_report_extraction_method")))
        if row_fields and row.get("research_report_ocr_status"):
            ocr_statuses.append(str(row.get("research_report_ocr_status")))
        if row_fields and safe_float(row.get("research_report_text_quality_score")) is not None:
            quality_scores.append(float(safe_float(row.get("research_report_text_quality_score")) or 0.0))
        if row_fields and safe_float(row.get("research_report_text_characters")) is not None:
            text_characters.append(float(safe_float(row.get("research_report_text_characters")) or 0.0))
        if row_fields:
            extraction_messages.extend(str(message) for message in row.get("research_report_extraction_messages") or [])
        if row.get("research_report_error"):
            errors.append(str(row.get("research_report_error")))

    priority_values, priority_warnings = _merge_priority_research_fields(rows)
    warnings.extend(priority_warnings)
    for field, selected in priority_values.items():
        value = selected.get("value")
        if value is None or value == "" or merged.get(field) not in {None, ""}:
            continue
        merged[field] = value
        fields.append(field)
        source = str(selected.get("source") or "")
        confidence = str(selected.get("confidence") or "")
        if source:
            field_sources[field] = source
        if confidence:
            field_confidence[field] = confidence

    merged["ticker"] = ticker
    non_low_confidence_fields = {
        field for field in set(fields) if str(field_confidence.get(field) or "MEDIUM").upper() != "LOW"
    }
    merged["manual_confidence_level"] = "HIGH" if len(non_low_confidence_fields) >= 4 else "MEDIUM"
    merged["notes"] = "Données enrichies par rapports BNCD/Morningstar locaux. À valider manuellement."
    parsed = parse_manual_row(merged)
    parsed["research_report_fields"] = sorted(set(fields))
    parsed["research_report_sources"] = sorted(set(sources))
    parsed["research_report_dates"] = sorted(set(dates), reverse=True)
    parsed["research_report_status"] = "FOUND_FIELDS" if fields else "NO_FIELDS_EXTRACTED"
    parsed["research_report_error"] = "; ".join(sorted(set(errors)))
    parsed["research_report_extraction_notes"] = sorted(set(notes))
    parsed["research_report_extraction_warnings"] = sorted(set(warnings))
    parsed["research_report_field_sources"] = field_sources
    parsed["research_report_field_confidence"] = field_confidence
    parsed["research_report_text_quality_status"] = _worst_text_quality_status(text_quality_statuses)
    parsed["research_report_text_quality_score"] = min(quality_scores) if quality_scores else None
    parsed["research_report_extraction_method"] = "; ".join(sorted(set(extraction_methods)))
    parsed["research_report_ocr_status"] = _worst_ocr_status(ocr_statuses)
    parsed["research_report_text_characters"] = int(max(text_characters)) if text_characters else None
    parsed["research_report_extraction_messages"] = sorted(set(extraction_messages))
    descriptive, descriptive_warnings = _merge_descriptive_research_fields(rows)
    parsed.update(descriptive)
    if descriptive_warnings:
        parsed["research_report_extraction_warnings"] = sorted(
            set(list(parsed.get("research_report_extraction_warnings") or []) + descriptive_warnings)
        )
    return parsed


def merge_research_with_automated(
    automated: dict[str, Any],
    research: dict[str, Any] | None,
) -> dict[str, Any]:
    if not research:
        return dict(automated)

    merged = dict(automated)
    fields = set(research.get("research_report_fields") or [])
    applied: list[str] = []
    for field in fields:
        if field == "ticker":
            continue
        value = research.get(field)
        if value is not None and value != "":
            merged[field] = value
            applied.append(field)

    merged["research_report_fields"] = sorted(set(applied))
    merged["research_report_sources"] = research.get("research_report_sources", [])
    merged["research_report_dates"] = research.get("research_report_dates", [])
    merged["research_report_status"] = research.get("research_report_status")
    merged["research_report_error"] = research.get("research_report_error", "")
    merged["research_report_extraction_notes"] = research.get("research_report_extraction_notes", [])
    merged["research_report_extraction_warnings"] = research.get("research_report_extraction_warnings", [])
    merged["research_report_field_sources"] = research.get("research_report_field_sources", {})
    merged["research_report_field_confidence"] = research.get("research_report_field_confidence", {})
    merged["research_report_text_quality_status"] = research.get("research_report_text_quality_status", "")
    merged["research_report_text_quality_score"] = research.get("research_report_text_quality_score")
    merged["research_report_extraction_method"] = research.get("research_report_extraction_method", "")
    merged["research_report_ocr_status"] = research.get("research_report_ocr_status", "")
    merged["research_report_text_characters"] = research.get("research_report_text_characters")
    merged["research_report_extraction_messages"] = research.get("research_report_extraction_messages", [])
    for key in DESCRIPTIVE_RESEARCH_FIELDS:
        value = research.get(key)
        if value is not None and value != "":
            merged[key] = value
    merged["auto_estimated_fields"] = [
        field for field in merged.get("auto_estimated_fields", []) if field not in set(applied)
    ]
    _remove_proxy_corrections_for_fields(merged, applied)
    for key in ("official_supported_manual_fields", "official_confirmed_manual_fields"):
        merged[key] = [field for field in merged.get(key, []) if field not in set(applied)]
    merged["input_data_mode"] = "AUTO_WITH_RESEARCH_REPORT" if applied else automated.get("input_data_mode", "AUTO_ESTIMATED")
    if applied:
        merged["manual_confidence_level"] = research.get("manual_confidence_level") or merged.get("manual_confidence_level")
        merged["notes"] = research.get("notes") or merged.get("notes", "")
    return merged


def _remove_proxy_corrections_for_fields(payload: dict[str, Any], confirmed_fields: list[str]) -> None:
    removed = set(confirmed_fields)
    if not removed:
        return
    corrections = [
        row for row in payload.get("proxy_corrections_applied", []) if str(row.get("field") or "") not in removed
    ]
    payload["proxy_corrections_applied"] = corrections
    payload["proxy_correction_fields"] = sorted({row.get("field") for row in corrections if row.get("field")})
    payload["proxy_correction_status"] = "ACTIVE" if corrections else "NONE"


def research_needed_rows_from_reports(reports_dir: str | Path = REPORTS_DIR) -> list[dict[str, Any]]:
    reports_dir = Path(reports_dir)
    gaps = read_csv_records(reports_dir / "latest_data_gaps.csv")
    auto_estimates = read_csv_records(reports_dir / "latest_auto_estimates.csv")
    metadata = _latest_metadata_by_ticker(reports_dir)
    known_tickers = sorted(metadata.keys())
    existing_reports = (
        load_research_report_inputs(
            BNCD_MORNINGSTAR_DIR,
            RESEARCH_REPORTS_DIR / "research_index.csv",
            known_tickers=known_tickers,
        )
        if reports_dir == REPORTS_DIR
        else {}
    )
    grouped: dict[str, dict[str, Any]] = {}

    for gap, is_auto_estimate in [(gap, False) for gap in gaps] + [(gap, True) for gap in auto_estimates]:
        ticker = normalize_ticker(gap.get("ticker"))
        if not ticker or ticker == "VFV.TO" or is_etf_asset(ticker):
            continue
        field = str(gap.get("data_field") or "")
        row = grouped.setdefault(
            ticker,
            {
                "ticker": ticker,
                "critical": 0,
                "auto": 0,
                "qualitative": False,
                "qualitative_target_status": "",
                "fields": [],
            },
        )
        if is_auto_estimate or field.startswith("AUTO_ESTIMATE"):
            row["auto"] += 1
        elif str(gap.get("importance") or "").upper() == "HIGH":
            row["critical"] += 1
        row["fields"].append(field)

    for qualitative in _qualitative_missing_rows_from_latest_report(reports_dir):
        ticker = normalize_ticker(qualitative.get("ticker"))
        if not ticker or ticker == "VFV.TO" or is_etf_asset(ticker):
            continue
        row = grouped.setdefault(
            ticker,
            {
                "ticker": ticker,
                "critical": 0,
                "auto": 0,
                "qualitative": False,
                "qualitative_target_status": "",
                "fields": [],
            },
        )
        row["qualitative"] = True
        row["qualitative_target_status"] = qualitative.get("target_status") or "QUALITATIVE"
        row["fields"].append("QUALITATIVE_MOAT_SOURCE")

    rows = []
    for ticker, values in grouped.items():
        meta = metadata.get(ticker, {})
        existing = existing_reports.get(ticker)
        critical = int(values["critical"])
        auto = int(values["auto"])
        qualitative_needed = bool(values.get("qualitative")) and not research_report_has_qualitative_source(existing)
        data_quality = str(meta.get("data_quality") or "").upper()
        validation_status = str(meta.get("ticker_validation_status") or "").upper()
        coverage_status = str(meta.get("ticker_coverage_status") or "").upper()
        if validation_status in {"ETF_OR_BENCHMARK", "ETF_OR_FUND"} or coverage_status in {"ETF_OR_BENCHMARK", "ETF_OR_FUND"}:
            continue
        reliability_level = str(meta.get("data_reliability_level") or "").upper()
        dependency = str(meta.get("auto_estimate_dependency") or "").upper()
        evidence = str(meta.get("automation_evidence_level") or "").upper()
        data_priority = ""
        if not research_report_has_usable_fields(existing):
            data_priority = research_need_priority(
                critical_count=critical,
                auto_count=auto,
                data_quality=data_quality,
                reliability_level=reliability_level,
                dependency=dependency,
                evidence=evidence,
                universe=str(meta.get("universe") or "UNKNOWN"),
                requires_validation=_truthy(meta.get("requires_manual_validation_for_large_allocation")),
            )
        if validation_status in {"NO_MARKET_DATA", "POSSIBLE_WRONG_TICKER"}:
            data_priority = "HIGH"
        qualitative_priority = _qualitative_priority(str(values.get("qualitative_target_status") or ""))
        priority = _highest_priority(data_priority, qualitative_priority if qualitative_needed else "")
        if not priority:
            continue
        reasons = []
        need_types = []
        if data_priority:
            need_types.append("DATA")
        if qualitative_needed:
            need_types.append("QUALITATIVE")
        if critical and data_priority:
            reasons.append(f"{critical} donnée(s) critique(s) manquante(s)")
        if auto and data_priority:
            reasons.append(f"{auto} estimation(s) automatique(s) utile(s) à valider")
        if data_quality and data_priority:
            reasons.append(f"qualité des données={data_quality}")
        if coverage_status and data_priority:
            reasons.append(f"couverture ticker={coverage_status}")
        if reliability_level and data_priority:
            reasons.append(f"fiabilité={reliability_level}")
        if dependency and data_priority:
            reasons.append(f"dépendance aux proxys={dependency}")
        if qualitative_needed:
            target_status = str(values.get("qualitative_target_status") or "titre admissible")
            reasons.append(f"source qualitative manquante pour {target_status}")
        suggested_action = _combined_research_suggested_action(data_priority, qualitative_needed, validation_status, coverage_status)
        rows.append(
            {
                "ticker": ticker,
                "ticker_display": meta.get("ticker_display") or ticker,
                "universe": meta.get("universe") or "UNKNOWN",
                "company_name": meta.get("company_name") or meta.get("company_name_found") or "",
                "data_quality": data_quality,
                "ticker_validation_status": validation_status,
                "ticker_coverage_status": coverage_status,
                "missing_critical_count": critical,
                "auto_estimate_count": auto,
                "priority": priority,
                "need_type": "+".join(need_types) or "UNKNOWN",
                "reason": "; ".join(reasons),
                "suggested_action": suggested_action,
                "suggested_file_name": "" if validation_status in {"NO_MARKET_DATA", "POSSIBLE_WRONG_TICKER"} else f"{ticker}_{date.today().isoformat()}_BNCD_Morningstar.pdf",
            }
        )

    priority_rank = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    return sorted(
        rows,
        key=lambda row: (
            priority_rank.get(str(row.get("priority")), 9),
            -(safe_float(row.get("missing_critical_count")) or 0),
            -(safe_float(row.get("auto_estimate_count")) or 0),
            str(row.get("ticker")),
        ),
    )


def research_needed_rows_from_analysis_rows(
    analysis_groups_by_universe: dict[str, dict[str, dict[str, Any]]],
    existing_reports: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    from .validation_priority_engine import ticker_validation_value_score

    existing_reports = existing_reports or {}
    rows: list[dict[str, Any]] = []
    for universe, analyses in analysis_groups_by_universe.items():
        for ticker, analysis in sorted(analyses.items()):
            ticker = normalize_ticker(ticker or analysis.get("ticker"))
            if not ticker or ticker == "VFV.TO" or is_etf_asset_analysis(analysis):
                continue
            existing = existing_reports.get(ticker)
            data_report_available = research_report_has_usable_fields(existing)
            qualitative_needed = _qualitative_report_needed_from_analysis(analysis, universe, existing)
            if data_report_available and not qualitative_needed:
                continue
            potential, _potential_reasons = ticker_validation_value_score(analysis, universe)

            manual_required = analysis.get("manual_required_criteria") or []
            auto_fields = set(analysis.get("auto_estimated_fields") or [])
            helpful_auto_fields = sorted(auto_fields & RESEARCH_HELPFUL_FIELDS)
            critical_count = len(manual_required)
            auto_count = len(helpful_auto_fields)
            data_quality = str(analysis.get("data_quality") or "").upper()
            validation_status = str(analysis.get("ticker_validation_status") or "").upper()
            coverage_status = str(analysis.get("ticker_coverage_status") or "").upper()
            reliability_level = str(analysis.get("data_reliability_level") or "").upper()
            dependency = str(analysis.get("auto_estimate_dependency") or "").upper()
            evidence = str(analysis.get("automation_evidence_level") or "").upper()
            data_priority = ""
            if not data_report_available:
                data_priority = research_need_priority(
                    critical_count=critical_count,
                    auto_count=auto_count,
                    data_quality=data_quality,
                    reliability_level=reliability_level,
                    dependency=dependency,
                    evidence=evidence,
                    universe=universe,
                    requires_validation=bool(analysis.get("requires_manual_validation_for_large_allocation")),
                )
            if validation_status in {"NO_MARKET_DATA", "POSSIBLE_WRONG_TICKER"}:
                data_priority = "HIGH"
            qualitative_priority = _qualitative_priority_from_analysis(analysis)
            priority = _highest_priority(data_priority, qualitative_priority if qualitative_needed else "")
            if not priority:
                continue

            reasons = []
            need_types = []
            if data_priority:
                need_types.append("DATA")
            if qualitative_needed:
                need_types.append("QUALITATIVE")
            if critical_count and data_priority:
                reasons.append(f"{critical_count} donnée(s) critique(s) manquante(s)")
            if helpful_auto_fields and data_priority:
                reasons.append("proxys clés à confirmer: " + ", ".join(helpful_auto_fields[:6]))
            if data_quality and data_priority:
                reasons.append(f"qualité des données={data_quality}")
            if coverage_status and data_priority:
                reasons.append(f"couverture ticker={coverage_status}")
            if reliability_level and data_priority:
                reasons.append(f"fiabilité={reliability_level}")
            if dependency and data_priority:
                reasons.append(f"dépendance aux proxys={dependency}")
            if qualitative_needed:
                reasons.append(_qualitative_reason_from_analysis(analysis))
            suggested_action = _combined_research_suggested_action(data_priority, qualitative_needed, validation_status, coverage_status)

            rows.append(
                {
                    "ticker": ticker,
                    "ticker_display": analysis.get("ticker_display") or ticker,
                    "universe": universe,
                    "company_name": analysis.get("company_name") or analysis.get("company_name_found") or "",
                    "data_quality": data_quality,
                    "ticker_validation_status": validation_status,
                    "ticker_coverage_status": coverage_status,
                    "missing_critical_count": critical_count,
                    "auto_estimate_count": auto_count,
                    "priority": priority,
                    "need_type": "+".join(need_types) or "UNKNOWN",
                    "reason": "; ".join(reasons),
                    "suggested_action": suggested_action,
                    "suggested_file_name": "" if validation_status in {"NO_MARKET_DATA", "POSSIBLE_WRONG_TICKER"} else f"{ticker}_{date.today().isoformat()}_BNCD_Morningstar.pdf",
                    "ticker_potential_score": round(potential, 2),
                }
            )

    priority_rank = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    return sorted(
        rows,
        key=lambda row: (
            -(safe_float(row.get("ticker_potential_score")) or 0.0),
            priority_rank.get(str(row.get("priority")), 9),
            0 if str(row.get("universe")) == "CORE_PORTFOLIO" else 1,
            -(safe_float(row.get("missing_critical_count")) or 0),
            -(safe_float(row.get("auto_estimate_count")) or 0),
            str(row.get("ticker")),
        ),
    )


def research_report_has_usable_fields(research: dict[str, Any] | None) -> bool:
    if not research:
        return False
    fields = set(research.get("research_report_fields") or [])
    helpful = fields & RESEARCH_HELPFUL_FIELDS
    primary = fields & RESEARCH_PRIMARY_FIELDS
    return len(helpful) >= 2 or bool(primary)


def research_report_has_qualitative_source(research: dict[str, Any] | None) -> bool:
    if not research:
        return False
    return bool(research.get("research_report_sources"))


def research_need_priority(
    critical_count: int,
    auto_count: int,
    data_quality: str,
    reliability_level: str,
    dependency: str,
    evidence: str,
    universe: str,
    requires_validation: bool,
) -> str:
    data_quality = data_quality.upper()
    reliability_level = reliability_level.upper()
    dependency = dependency.upper()
    evidence = evidence.upper()
    universe = universe.upper()

    if critical_count >= 3 or data_quality == "LOW" or reliability_level == "LOW":
        return "HIGH"
    if critical_count >= 1 and (dependency in {"HIGH", "MEDIUM"} or data_quality == "MEDIUM" or reliability_level == "MEDIUM"):
        return "MEDIUM"
    if dependency == "HIGH" and auto_count >= 4:
        return "MEDIUM"
    if requires_validation and universe == "CORE_PORTFOLIO" and dependency == "MEDIUM" and evidence not in {"STRONG", "CONFIRMED"}:
        return "LOW"
    return ""


def _qualitative_report_needed_from_analysis(
    analysis: dict[str, Any],
    universe: str,
    existing_research: dict[str, Any] | None,
) -> bool:
    if str(universe or "").upper() != "CORE_PORTFOLIO":
        return False
    if is_etf_asset_analysis(analysis) or normalize_ticker(analysis.get("ticker")) == "VFV.TO":
        return False
    if research_report_has_qualitative_source(existing_research):
        return False
    return analysis.get("add_eligibility_status") in ADD_ALLOWED_STATUSES or _looks_recommended_for_allocation(analysis)


def _looks_recommended_for_allocation(analysis: dict[str, Any]) -> bool:
    for field in ["allocation_decision", "final_position_action", "decision"]:
        text = str(analysis.get(field) or "").strip().upper()
        if not text:
            continue
        if any(blocked in text for blocked in ["DO_NOT_ADD", "DO NOT ADD", "NOT_ADD", "NO_ADD", "NE PAS RENFORCER"]):
            continue
        if text in {"BUY", "ADD", "BUY_ADD", "BUY / ADD", "BUY/ADD"}:
            return True
        if re.search(r"\b(BUY|ADD)\b", text):
            return True
    return False


def _qualitative_priority_from_analysis(analysis: dict[str, Any]) -> str:
    if _looks_recommended_for_allocation(analysis):
        return "HIGH"
    score = safe_float(analysis.get("capital_allocation_score")) or 0.0
    if score >= 80:
        return "HIGH"
    return "MEDIUM"


def _qualitative_priority(target_status: str) -> str:
    target = str(target_status or "").upper()
    if "RECOMMAND" in target or "RECOMMEND" in target:
        return "HIGH"
    return "MEDIUM"


def _qualitative_reason_from_analysis(analysis: dict[str, Any]) -> str:
    status = "titre recommandé" if _looks_recommended_for_allocation(analysis) else "titre éligible"
    score = safe_float(analysis.get("capital_allocation_score"))
    score_text = f" score allocation={score:.1f}" if score is not None else ""
    return f"source qualitative manquante pour {status}{score_text}"


def _highest_priority(*priorities: str) -> str:
    rank = {"HIGH": 3, "MEDIUM": 2, "LOW": 1, "": 0}
    clean = [priority for priority in priorities if priority]
    if not clean:
        return ""
    return max(clean, key=lambda priority: rank.get(priority, 0))


def _qualitative_missing_rows_from_latest_report(reports_dir: Path) -> list[dict[str, Any]]:
    rows = []
    for row in read_csv_records(reports_dir / "latest_qualitative_moat_report.csv"):
        if str(row.get("source_status") or "") != "SOURCE_MISSING":
            continue
        target_status = str(row.get("target_status") or "")
        if target_status not in {"RECOMMANDÉ", "ÉLIGIBLE_NON_RETENU", "RECOMMENDED", "ELIGIBLE_NOT_SELECTED"}:
            continue
        rows.append(row)
    return rows


def _research_suggested_action(validation_status: str, coverage_status: str) -> str:
    if validation_status in {"NO_MARKET_DATA", "POSSIBLE_WRONG_TICKER"}:
        return "Corriger ou confirmer le ticker Yahoo Finance avant de chercher un rapport."
    if coverage_status in {"LOW_FREE_DATA_COVERAGE", "NEEDS_BNCD_OR_MANUAL_CONFIRMATION"}:
        return "Chercher un rapport BNCD/Morningstar ou confirmer les champs clés manuellement."
    return "Rapport utile mais non urgent; prioriser seulement si la position devient candidate à allocation."


def _combined_research_suggested_action(
    data_priority: str,
    qualitative_needed: bool,
    validation_status: str,
    coverage_status: str,
) -> str:
    actions = []
    if data_priority:
        actions.append(_research_suggested_action(validation_status, coverage_status))
    if qualitative_needed:
        actions.append("Chercher un rapport analyste ou annuel pour activer le texte qualitatif sourcé: moat, rempart, résilience en crise et pouvoir de prix.")
    return " ".join(dict.fromkeys(actions))


def write_research_needed_csv(path: str | Path, rows: list[dict[str, Any]]) -> None:
    write_csv_records(path, rows, RESEARCH_NEEDED_COLUMNS)


def research_status_rows(
    report_dir: str | Path = BNCD_MORNINGSTAR_DIR,
    index_path: str | Path = RESEARCH_REPORTS_DIR / "research_index.csv",
    known_tickers: list[str] | None = None,
) -> list[dict[str, Any]]:
    report_dir = Path(report_dir)
    index_path = Path(index_path)
    known = [normalize_ticker(ticker) for ticker in (known_tickers or []) if normalize_ticker(ticker)]
    indexed = _indexed_reports(index_path)
    rows: list[dict[str, Any]] = []

    for path in sorted(report_dir.glob("*")):
        if not path.is_file() or path.name == "README.md":
            continue

        index_row = indexed.get(path.name, {})
        provider = str(index_row.get("provider") or "BNCD/Morningstar").strip()
        report_date = str(index_row.get("report_date") or date_from_filename(path.name) or "").strip()
        ticker = normalize_ticker(index_row.get("ticker")) or infer_ticker_from_filename(path.name, known)

        if path.suffix.lower() not in SUPPORTED_REPORT_EXTENSIONS:
            rows.append(
                {
                    "file_name": path.name,
                    "ticker_detected": ticker,
                    "provider": provider,
                    "report_date": report_date,
                    "readable": False,
                    "text_characters": 0,
                    "text_quality_status": "UNSUPPORTED",
                    "text_quality_score": 0,
                    "extraction_method": "NONE",
                    "ocr_status": "NOT_APPLICABLE",
                    "extracted_fields": "",
                    "field_count": 0,
                    "extraction_warnings": "",
                    "status": "IGNORED_UNSUPPORTED",
                    "message": "Type de fichier non supporté. Utilisez PDF, TXT ou MD.",
                }
            )
            continue

        extraction = extract_report_text_detailed(path)
        text = str(extraction.get("text") or "")
        error = str(extraction.get("error") or "")
        fields: list[str] = []
        warnings: list[str] = list(extraction.get("warnings") or [])
        if ticker and text:
            parsed = parse_research_report(path, ticker, index_row)
            fields = list(parsed.get("research_report_fields") or [])
            warnings.extend(str(warning) for warning in parsed.get("research_report_extraction_warnings") or [])

        if error:
            status = "READ_ERROR"
            message = error
        elif not ticker:
            status = "NO_TICKER_DETECTED"
            message = "Fichier visible, mais ticker non détecté. Renommez le fichier avec le ticker au début ou remplissez research_index.csv."
        elif not text:
            status = "NO_TEXT_EXTRACTED"
            message = "Fichier visible, mais aucun texte exploitable n’a été extrait."
        elif not fields:
            status = "READABLE_NO_FIELDS"
            message = "Fichier lisible, mais aucun champ utile n’a été détecté automatiquement."
        else:
            status = "READY"
            message = "Fichier lisible et champs utiles détectés."

        rows.append(
            {
                "file_name": path.name,
                "ticker_detected": ticker,
                "provider": provider,
                "report_date": report_date,
                "readable": bool(text) and not error,
                "text_characters": len(text),
                "text_quality_status": extraction.get("text_quality_status"),
                "text_quality_score": extraction.get("text_quality_score"),
                "extraction_method": extraction.get("extraction_method"),
                "ocr_status": extraction.get("ocr_status"),
                "extracted_fields": "; ".join(sorted(set(fields))),
                "field_count": len(set(fields)),
                "extraction_warnings": "; ".join(sorted(set(warnings))),
                "status": status,
                "message": message,
            }
        )

    return rows


def write_research_status_csv(path: str | Path, rows: list[dict[str, Any]]) -> None:
    write_csv_records(path, rows, RESEARCH_STATUS_COLUMNS)


def extract_report_text(path: Path) -> tuple[str, str]:
    extraction = extract_report_text_detailed(path)
    return str(extraction.get("text") or ""), str(extraction.get("error") or "")


def extract_report_text_detailed(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="latin-1")
        except OSError as exc:
            return _text_extraction_result("", str(exc), "TEXT", "UNREADABLE", 0.0, "NOT_APPLICABLE", [])
        quality = assess_extracted_text_quality(text, suffix)
        return _text_extraction_result(text, "", "TEXT", quality["status"], quality["score"], "NOT_APPLICABLE", quality["warnings"])
    if suffix != ".pdf":
        return _text_extraction_result(
            "",
            "Type de fichier non supporté.",
            "NONE",
            "UNSUPPORTED",
            0.0,
            "NOT_APPLICABLE",
            [],
        )

    attempts: list[dict[str, Any]] = []
    pypdf_text, pypdf_error = _extract_pdf_text_pypdf(path)
    pypdf_quality = assess_extracted_text_quality(pypdf_text, suffix)
    attempts.append(
        _text_extraction_result(
            pypdf_text,
            pypdf_error,
            "pypdf",
            pypdf_quality["status"],
            pypdf_quality["score"],
            "NOT_USED",
            pypdf_quality["warnings"],
        )
    )

    best = attempts[0]
    if best["text_quality_status"] != "TEXT_OK":
        fitz_text, fitz_error = _extract_pdf_text_pymupdf(path)
        fitz_quality = assess_extracted_text_quality(fitz_text, suffix)
        attempts.append(
            _text_extraction_result(
                fitz_text,
                fitz_error,
                "PyMuPDF",
                fitz_quality["status"],
                fitz_quality["score"],
                "NOT_USED",
                fitz_quality["warnings"],
            )
        )
        best = max(attempts, key=lambda item: (float(item.get("text_quality_score") or 0.0), len(str(item.get("text") or ""))))

    if best["text_quality_status"] != "TEXT_OK":
        ocr_text, ocr_error = _extract_pdf_text_ocr(path)
        if ocr_text:
            ocr_quality = assess_extracted_text_quality(ocr_text, suffix)
            ocr_result = _text_extraction_result(
                ocr_text,
                ocr_error,
                "OCR_TESSERACT",
                "OCR_USED" if ocr_quality["status"] == "TEXT_OK" else "LOW_TEXT_QUALITY",
                max(float(ocr_quality["score"] or 0.0) - 8.0, 0.0),
                "OCR_USED",
                list(ocr_quality["warnings"]) + ["OCR utilisé: valider les chiffres importants avant une grosse décision."],
            )
            attempts.append(ocr_result)
            best = max(attempts, key=lambda item: (float(item.get("text_quality_score") or 0.0), len(str(item.get("text") or ""))))
        elif len(str(best.get("text") or "")) < 400:
            best["ocr_status"] = "OCR_NEEDED"
            best["text_quality_status"] = "OCR_NEEDED"
            best["warnings"] = sorted(
                set(
                    list(best.get("warnings") or [])
                    + ["PDF possiblement scanné ou mal encodé: OCR requis pour une lecture fiable."]
                )
            )
            if ocr_error:
                best["messages"] = sorted(set(list(best.get("messages") or []) + [ocr_error]))

    if not best.get("text") and not best.get("error"):
        best["error"] = "; ".join(str(item.get("error")) for item in attempts if item.get("error"))
    best["messages"] = sorted(
        set(
            [str(item.get("error")) for item in attempts if item.get("error")]
            + [str(message) for item in attempts for message in item.get("messages", []) if message]
        )
    )
    return best


def _extract_pdf_text_pypdf(path: Path) -> tuple[str, str]:
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception:
        return "", "Le module pypdf n’est pas installé; lancez pip install -r requirements.txt."
    try:
        reader = PdfReader(str(path))
        pages = []
        for page in reader.pages:
            pages.append(page.extract_text() or "")
        return "\n".join(pages), ""
    except Exception as exc:
        return "", f"PDF non lisible automatiquement avec pypdf: {exc}"


def _extract_pdf_text_pymupdf(path: Path) -> tuple[str, str]:
    try:
        import fitz  # type: ignore
    except Exception:
        return "", "PyMuPDF non installé; fallback PDF secondaire ignoré."
    try:
        with fitz.open(str(path)) as doc:
            pages = [page.get_text("text") or "" for page in doc]
        return "\n".join(pages), ""
    except Exception as exc:
        return "", f"PDF non lisible automatiquement avec PyMuPDF: {exc}"


def _extract_pdf_text_ocr(path: Path, max_pages: int = 3) -> tuple[str, str]:
    try:
        import io

        import fitz  # type: ignore
        import pytesseract  # type: ignore
        from PIL import Image  # type: ignore
    except Exception:
        return "", "OCR non disponible localement; installez Tesseract/pytesseract seulement si vous devez lire des PDF scannés."
    try:
        pages: list[str] = []
        with fitz.open(str(path)) as doc:
            for page in list(doc)[:max_pages]:
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                image = Image.open(io.BytesIO(pix.tobytes("png")))
                pages.append(pytesseract.image_to_string(image) or "")
        return "\n".join(pages), ""
    except Exception as exc:
        return "", f"OCR non réussi: {exc}"


def assess_extracted_text_quality(text: str, suffix: str = "") -> dict[str, Any]:
    text = text or ""
    if suffix in {".txt", ".md"}:
        score = 100.0 if text.strip() else 0.0
        return {
            "status": "TEXT_OK" if text.strip() else "NO_TEXT_EXTRACTED",
            "score": score,
            "warnings": [] if text.strip() else ["Aucun texte exploitable extrait."],
        }

    chars = len(text.strip())
    words = len(re.findall(r"[A-Za-zÀ-ÿ0-9]{2,}", text))
    markers = sum(
        1
        for pattern in [
            r"\bmorningstar\b",
            r"\bfair value\b",
            r"\beconomic moat\b",
            r"\bprice\s*/\s*fve\b",
            r"\bforward\s+p/?e\b",
            r"\bpeg\b",
        ]
        if re.search(pattern, text, flags=re.IGNORECASE)
    )
    score = min(55.0, chars / 35.0) + min(30.0, words / 8.0) + min(15.0, markers * 4.0)
    score = round(min(100.0, score), 2)
    warnings = []
    if chars == 0:
        return {"status": "NO_TEXT_EXTRACTED", "score": 0.0, "warnings": ["Aucun texte exploitable extrait."]}
    if chars < 400:
        warnings.append("Texte extrait très court: PDF possiblement scanné, protégé ou mal encodé.")
    if markers == 0 and chars < 1500:
        warnings.append("Peu de repères Morningstar détectés dans le texte extrait.")
    status = "TEXT_OK" if score >= 60.0 and chars >= 400 else "LOW_TEXT_QUALITY"
    return {"status": status, "score": score, "warnings": warnings}


def _text_extraction_result(
    text: str,
    error: str,
    method: str,
    quality_status: str,
    quality_score: float,
    ocr_status: str,
    warnings: list[str],
) -> dict[str, Any]:
    return {
        "text": text or "",
        "error": error or "",
        "extraction_method": method,
        "text_quality_status": quality_status,
        "text_quality_score": round(float(quality_score or 0.0), 2),
        "text_characters": len(text or ""),
        "ocr_status": ocr_status,
        "warnings": sorted(set(warnings)),
        "messages": [error] if error else [],
    }


def infer_ticker_from_filename(file_name: str, known_tickers: list[str]) -> str:
    upper = file_name.upper()
    candidates = sorted(set(known_tickers), key=len, reverse=True)
    for ticker in candidates:
        if ticker and re.search(rf"(^|[^A-Z0-9]){re.escape(ticker)}([^A-Z0-9]|$)", upper):
            return ticker

    tickers_by_root: dict[str, list[str]] = {}
    for ticker in candidates:
        root = re.sub(r"\.[A-Z]{1,3}$", "", str(ticker or "").upper())
        if len(root) >= 2:
            tickers_by_root.setdefault(root, []).append(ticker)
    for root, tickers in sorted(tickers_by_root.items(), key=lambda item: len(item[0]), reverse=True):
        if not re.search(rf"(^|[^A-Z0-9]){re.escape(root)}([^A-Z0-9]|$)", upper):
            continue
        if len(set(tickers)) == 1:
            return tickers[0]
        return ""

    first_token = re.split(r"[\s_-]+", Path(file_name).stem.upper())[0]
    if first_token in COMMON_NON_TICKER_FILENAME_TOKENS:
        return ""
    if not re.fullmatch(r"[A-Z0-9.\-]{1,12}", first_token):
        return ""
    return normalize_ticker(first_token)


def date_from_filename(file_name: str) -> str:
    match = re.search(r"(20\d{2})[-_]?(\d{2})[-_]?(\d{2})", file_name)
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
    match = re.search(r"(\d{2})[-_](\d{2})[-_](20\d{2})", file_name)
    if match:
        return f"{match.group(3)}-{match.group(1)}-{match.group(2)}"
    return ""


def extract_first_number(text: str, patterns: list[str]) -> float | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return _safe_report_number(match.group(1))
    return None


def extract_percent_number(text: str, patterns: list[str]) -> float | None:
    return extract_first_number(text, patterns)


def extract_valuation_analysis_current_value(text: str, label: str) -> float | None:
    pattern = rf"^\s*{re.escape(label)}\s+{REPORT_NUMBER_CAPTURE}\*?(?:\s|$)"
    match = re.search(pattern, text or "", flags=re.IGNORECASE | re.MULTILINE)
    if not match:
        return None
    return _safe_report_number(match.group(1))


def extract_broker_target_price(text: str) -> float | None:
    value, _start = _extract_broker_target_price_candidate(text)
    return value


def extract_nbccm_forward_pe_estimate(text: str) -> float | None:
    section_match = re.search(
        r"\bNBCCM\s+ESTIMATES\s*&\s*VALUATION\b(?P<body>.*?)(?=\n\s*(?:Source:|All figures|Company Profile|IMPORTANT DISCLOSURES)\b|$)",
        text or "",
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not section_match:
        return None
    section = section_match.group("body")
    header = re.search(r"\bFiscal\s+Y/E\b(?P<header>[^\n]+(?:\n[^\n]+)?)", section, flags=re.IGNORECASE)
    labels_text = header.group("header") if header else section[:500]
    year_labels = re.findall(r"\b20\d{2}[AE]\b", labels_text, flags=re.IGNORECASE)
    if not year_labels:
        return None
    pe_match = re.search(r"^\s*P/E\s*\(x\)\s+(?P<values>[^\n]+)$", section, flags=re.IGNORECASE | re.MULTILINE)
    if not pe_match:
        return None
    values = [
        value
        for value in (_safe_report_number(match.group(1)) for match in re.finditer(REPORT_NUMBER_CAPTURE, pe_match.group("values")))
        if value is not None
    ]
    first_estimate_index = next(
        (index for index, label in enumerate(year_labels) if str(label).upper().endswith("E")),
        None,
    )
    if first_estimate_index is None or first_estimate_index >= len(values):
        return None
    return values[first_estimate_index]


def _extract_descriptive_research_fields(text: str) -> dict[str, Any]:
    source_rank, source_type = _classify_research_report_source(text)
    description = _extract_company_description(text, source_type)
    sector, industry = _extract_sector_industry(text, source_type)
    fields: dict[str, Any] = {}
    if description:
        fields["research_report_company_description"] = description
    if sector:
        fields["research_report_sector"] = sector
    if industry:
        fields["research_report_industry"] = industry
    if fields:
        fields["research_report_company_description_source_rank"] = source_rank
        fields["research_report_company_description_source_type"] = source_type
    return fields


def _classify_research_report_source(text: str) -> tuple[int, str]:
    lower = str(text or "").lower()
    if "morningstar equity analyst report" in lower and "business description" in lower and "economic moat" in lower:
        return 1, "MORNINGSTAR_ANALYST"
    if "investment detail report" in lower or ("morningstar" in lower and "business description" not in lower):
        return 2, "MORNINGSTAR_TEAR_SHEET"
    if "company profile" in lower or "nbccm" in lower or "national bank" in lower:
        return 3, "NATIONAL_BANK"
    return 4, "OTHER"


def _extract_company_description(text: str, source_type: str) -> str:
    text = str(text or "")
    if not text.strip():
        return ""
    if source_type == "MORNINGSTAR_ANALYST":
        return _extract_morningstar_analyst_description(text)
    if source_type == "MORNINGSTAR_TEAR_SHEET":
        return _extract_morningstar_tear_sheet_description(text)
    if source_type == "NATIONAL_BANK":
        return _extract_national_bank_description(text)
    return _extract_generic_company_description(text)


def _extract_morningstar_analyst_description(text: str) -> str:
    candidates: list[str] = []
    pattern = (
        r"\bBusiness Description\b\s*"
        r"(?P<body>.*?)"
        r"(?=\n\s*(?:Business Strategy|Business Strategy & Outlook|Bulls Say|Bears Say|Economic Moat|"
        r"Fair Value|Risk and Uncertainty|Capital Allocation|Analyst Notes?|Financials|ESG Risk|Appendix)\b)"
    )
    for match in re.finditer(pattern, text, flags=re.IGNORECASE | re.DOTALL):
        candidate = _clean_descriptive_text(match.group("body"))
        if len(candidate) >= 80:
            candidates.append(candidate)
    return max(candidates, key=len) if candidates else ""


def _extract_morningstar_tear_sheet_description(text: str) -> str:
    head = _truncate_before_disclaimer(str(text or ""))[:3000]
    if "\n" in head:
        head = head.split("\n", 1)[1]
    stop = re.search(
        r"\n\s*(?:Growth Rates|Fair Value Uncertainty|Valuation|Financials|Profitability|Stock Performance)\b",
        head,
        flags=re.IGNORECASE,
    )
    if stop:
        head = head[: stop.start()]
    head = re.sub(r"^\s*\d{1,2}[-/][A-Za-z]{3}[-/]\d{4}\s+", "", head)
    description = _clean_descriptive_text(head)
    return description if len(description) >= 80 else ""


def _extract_national_bank_description(text: str) -> str:
    pattern = (
        r"\bCOMPANY PROFILE\b\s*"
        r"(?P<body>.*?)"
        r"(?=\n\s*(?:Analyst|Associate|For required disclosures|Figure\s+\d|Source:|IMPORTANT DISCLOSURES)\b)"
    )
    match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    description = _clean_descriptive_text(match.group("body"))
    return description if len(description) >= 60 else ""


def _extract_generic_company_description(text: str) -> str:
    for pattern in [
        r"\bBusiness Description\b\s*(?P<body>.*?)(?=\n\s*[A-Z][A-Za-z &/]{4,40}\n)",
        r"\bCompany Profile\b\s*(?P<body>.*?)(?=\n\s*[A-Z][A-Za-z &/]{4,40}\n)",
    ]:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
        if match:
            description = _clean_descriptive_text(match.group("body"))
            if len(description) >= 80:
                return description
    return ""


def _extract_sector_industry(text: str, source_type: str) -> tuple[str, str]:
    sector = ""
    industry = ""

    table_match = re.search(
        r"\bSector\s+Industry\s*\n\s*(?P<line>[^\n]+)\n\s*Business Description\b",
        text,
        flags=re.IGNORECASE,
    )
    if table_match:
        sector, industry = _split_sector_industry_line(table_match.group("line"))

    if not industry:
        industry = _extract_labeled_industry(text)

    if not sector and source_type == "MORNINGSTAR_TEAR_SHEET":
        sector = _extract_tear_sheet_sector(text)

    if not sector and source_type == "NATIONAL_BANK":
        sector = _extract_national_bank_sector(text)

    return _clean_short_label(sector), _clean_short_label(industry)


def _split_sector_industry_line(line: str) -> tuple[str, str]:
    clean = _clean_short_label(re.sub(r"^[a-z]\s+", "", str(line or "").strip(), flags=re.IGNORECASE))
    for sector in sorted(KNOWN_REPORT_SECTORS, key=len, reverse=True):
        if clean.lower().startswith(sector.lower()):
            industry = _clean_short_label(clean[len(sector) :])
            return sector, industry
    return "", clean


def _extract_labeled_industry(text: str) -> str:
    patterns = [
        r"\bIndustry\s*:\s*(?!Rating\b)(?P<value>[^\n|]+)",
        r"\|\s*Industry\s*:\s*(?P<value>[^\n|]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            value = _clean_short_label(match.group("value"))
            if value and not value.lower().startswith("rating"):
                return value
    return ""


def _extract_tear_sheet_sector(text: str) -> str:
    match = re.search(
        r"\bFair Value\s+Uncertainty\s+Economic Moat\s+Sector\s+Style[^\n]*\n(?P<line>[^\n]+)",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return ""
    return _match_known_sector(match.group("line"))


def _extract_national_bank_sector(text: str) -> str:
    for line in str(text or "").splitlines()[:8]:
        sector = _match_known_sector(line)
        if sector:
            return sector
    return ""


def _match_known_sector(text: str) -> str:
    clean = _clean_short_label(text)
    for sector in sorted(KNOWN_REPORT_SECTORS, key=len, reverse=True):
        if re.search(rf"(^|[^A-Za-z]){re.escape(sector)}([^A-Za-z]|$)", clean, flags=re.IGNORECASE):
            return sector
    return ""


def _clean_descriptive_text(value: str) -> str:
    text = _truncate_before_disclaimer(value)
    text = text.replace("\u00a0", " ").replace("\xad", "")
    text = re.sub(r"-\s*\n\s*", "", text)
    text = re.sub(r"\s*\n\s*", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" -:;")
    text = re.sub(r"^(?:[;?\s]+)*(?:\d{1,2}[-/][A-Za-z]{3}[-/]\d{4})\s+", "", text)
    replacements = {
        r"\bthecompany\b": "the company",
        r"\bourview\b": "our view",
        r"\bwebelieve\b": "we believe",
        r"\bweexpect\b": "we expect",
        r"\bthebusiness\b": "the business",
    }
    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def _clean_short_label(value: str) -> str:
    text = str(value or "").replace("\u00a0", " ")
    text = re.sub(r"\s+", " ", text).strip(" -:;|")
    return text


def _truncate_before_disclaimer(text: str) -> str:
    stops = [
        "© Morningstar",
        "All Rights Reserved",
        "For required disclosures",
        "This report may not be reproduced",
        "Important Disclosure",
        "IMPORTANT DISCLOSURES",
    ]
    cut = len(text or "")
    for marker in stops:
        index = str(text or "").find(marker)
        if index >= 0:
            cut = min(cut, index)
    return str(text or "")[:cut]


def _merge_descriptive_research_fields(rows: list[dict[str, Any]]) -> tuple[dict[str, Any], list[str]]:
    candidates: list[dict[str, Any]] = []
    warnings: list[str] = []
    for row in rows:
        if not any(row.get(field) for field in DESCRIPTIVE_RESEARCH_FIELDS):
            continue
        source = _first_research_source(row)
        report_date = str(row.get("research_report_company_description_date") or _latest_date_text(row) or "").strip()
        parsed_date = _parse_research_report_date(report_date)
        if parsed_date and (date.today() - parsed_date).days > 730:
            warnings.append(f"Description: {source or 'rapport local'} ignoré, rapport de plus de 24 mois.")
            continue
        if not parsed_date:
            warnings.append(
                f"Description: date inconnue pour {source or 'rapport local'}; plafond 24 mois non appliqué."
            )
        candidates.append(
            {
                "row": row,
                "source": source,
                "date": report_date,
                "rank": int(safe_float(row.get("research_report_company_description_source_rank")) or 4),
                "source_type": str(row.get("research_report_company_description_source_type") or "OTHER"),
                "date_ordinal": parsed_date.toordinal() if parsed_date else 0,
            }
        )

    if not candidates:
        return {}, warnings

    candidates.sort(key=lambda item: (int(item["rank"]), -int(item["date_ordinal"])))
    output: dict[str, Any] = {}
    chosen_description_candidate = None
    for field in ["research_report_company_description", "research_report_sector", "research_report_industry"]:
        for candidate in candidates:
            value = candidate["row"].get(field)
            if value is not None and value != "":
                output[field] = value
                if field == "research_report_company_description":
                    chosen_description_candidate = candidate
                break

    source_candidate = chosen_description_candidate or candidates[0]
    if output:
        output["research_report_company_description_source"] = source_candidate["source"]
        output["research_report_company_description_date"] = source_candidate["date"]
        output["research_report_company_description_source_rank"] = source_candidate["rank"]
        output["research_report_company_description_source_type"] = source_candidate["source_type"]
    return output, warnings


def _first_research_source(row: dict[str, Any]) -> str:
    sources = row.get("research_report_sources") or []
    if isinstance(sources, list) and sources:
        return str(sources[0])
    return str(row.get("research_report_company_description_source") or "")


def _parse_research_report_date(value: str) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    match = re.search(r"(20\d{2})-(\d{2})-(\d{2})", text)
    if match:
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            return None
    return None


def _safe_report_number(value: Any) -> float | None:
    """Convert English-formatted report numbers without changing global safe_float()."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    text = text.replace("\u00a0", "").replace(" ", "")
    text = re.sub(r"^(?:CAD|USD|C\$|US\$|\$)", "", text, flags=re.IGNORECASE)
    text = re.sub(r"(?:CAD|USD)$", "", text, flags=re.IGNORECASE)
    if not re.fullmatch(REPORT_NUMBER_PATTERN, text):
        return None
    try:
        return float(text.replace(",", ""))
    except ValueError:
        return None


def _extract_broker_target_price_candidate(text: str) -> tuple[float | None, int]:
    text = str(text or "")
    anchored_patterns = [
        rf"\btarget\s+price\s+(?:of|to|at|is|=)?\s*(?:CAD|USD|C\$|US\$|\$)?\s*{REPORT_NUMBER_CAPTURE}",
        rf"\bprice\s+target\s+(?:of|to|at|is|=)?\s*(?:CAD|USD|C\$|US\$|\$)?\s*{REPORT_NUMBER_CAPTURE}",
    ]
    for pattern in anchored_patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue
        value = _safe_report_number(match.group(1))
        if value is not None:
            return value, match.start(1)

    header_match = re.search(
        r"\bSTOCK\s+RATING\s+TARGET\s+EST\s*\.?\s*TOTAL\s+RETURN\b(?P<body>.{0,450})",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not header_match:
        return None, -1
    currency_matches = list(
        re.finditer(rf"(?:CAD|USD|C\$|US\$|\$)\s*{REPORT_NUMBER_CAPTURE}", header_match.group("body"), flags=re.IGNORECASE)
    )
    if len(currency_matches) < 2:
        return None, -1
    target_match = currency_matches[1]
    value = _safe_report_number(target_match.group(1))
    if value is None:
        return None, -1
    return value, header_match.start("body") + target_match.start(1)


def _extract_fair_value_estimate(text: str) -> tuple[float | None, str, list[str]]:
    candidates: list[dict[str, Any]] = []
    for pattern in FAIR_VALUE_PATTERNS:
        for match in re.finditer(pattern, text or "", flags=re.IGNORECASE):
            value = _safe_report_number(match.group(1))
            if value is None:
                continue
            candidates.append(
                {
                    "value": value,
                    "start": match.start(1),
                    "score": _fair_value_candidate_score(text, match.start(), match.end()),
                }
            )
    target_value, target_start = _extract_broker_target_price_candidate(text)
    if target_value is not None:
        candidates.append(
            {
                "value": target_value,
                "start": target_start if target_start >= 0 else len(text or ""),
                "score": 1.0,
                "source": "cours cible 12 mois — courtier, définition divergente",
            }
        )
    if not candidates:
        return None, "", []

    candidates.sort(key=lambda item: (-float(item["score"]), int(item["start"])))
    best = candidates[0]
    warnings: list[str] = []
    source = str(best.get("source") or ("fair value header pattern" if float(best["score"]) >= 6.0 else "fair value text pattern"))
    if _is_divergent_research_source(source):
        warnings.append(
            "Fair value: cours cible courtier 12 mois détecté; définition divergente de la juste valeur intrinsèque."
        )
    if len(candidates) > 1 and float(best["score"]) < 6.0:
        warnings.append(
            "Juste valeur: plusieurs candidats détectés sans en-tête Morningstar clair; premier candidat utilisé avec prudence."
        )
    return float(best["value"]), source, warnings


def _merge_priority_research_fields(rows: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    selected: dict[str, dict[str, Any]] = {}
    warnings: list[str] = []
    for field in sorted(PRIORITY_RESEARCH_FIELDS):
        choice, field_warnings = _select_priority_research_field(field, rows)
        warnings.extend(field_warnings)
        if choice:
            selected[field] = choice
    return selected, warnings


def _select_priority_research_field(field: str, rows: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, list[str]]:
    candidates: list[dict[str, Any]] = []
    warnings: list[str] = []
    for row in rows:
        row_fields = set(row.get("research_report_fields") or [])
        if field not in row_fields:
            continue
        value = row.get(field)
        if value is None or value == "":
            continue
        source = str((row.get("research_report_field_sources") or {}).get(field) or "")
        source_type = _research_source_type_from_row(row)
        parsed_date = _parse_research_report_date(_latest_date_text(row))
        confidence = str((row.get("research_report_field_confidence") or {}).get(field) or "")
        divergent = _is_divergent_priority_candidate(field, source, source_type)
        if divergent:
            confidence = "LOW"
        candidates.append(
            {
                "value": value,
                "source": source,
                "confidence": confidence,
                "source_type": source_type,
                "source_rank": _research_source_rank_from_row(row),
                "date_text": _latest_date_text(row),
                "date_ordinal": parsed_date.toordinal() if parsed_date else 0,
                "divergent": divergent,
            }
        )

    if not candidates:
        return None, warnings

    if field == "fair_value":
        intrinsic_candidates = [candidate for candidate in candidates if not candidate["divergent"]]
        if intrinsic_candidates:
            chosen = sorted(
                intrinsic_candidates,
                key=lambda candidate: (-int(candidate["date_ordinal"]), int(candidate["source_rank"])),
            )[0]
            if any(candidate["divergent"] for candidate in candidates):
                warnings.append(
                    "Fair value: cours cible courtier détecté puis écarté au profit d'une juste valeur Morningstar/intrinsèque."
                )
            return chosen, warnings
        chosen = sorted(candidates, key=lambda candidate: (-int(candidate["date_ordinal"]), int(candidate["source_rank"])))[0]
        chosen["confidence"] = "LOW"
        warnings.append(
            "Fair value: cours cible courtier retenu en dernier recours faute de juste valeur Morningstar; définition divergente, confiance LOW."
        )
        return chosen, warnings

    if field == "roic_5y_avg":
        comparable_candidates = [candidate for candidate in candidates if not candidate["divergent"]]
        if comparable_candidates:
            chosen = sorted(
                comparable_candidates,
                key=lambda candidate: (int(candidate["source_rank"]), -int(candidate["date_ordinal"])),
            )[0]
            if any(candidate["divergent"] for candidate in candidates):
                warnings.append("ROIC: source courtier écartée au profit d'une source Morningstar comparable au champ 5 ans.")
            return chosen, warnings
        chosen = sorted(candidates, key=lambda candidate: (int(candidate["source_rank"]), -int(candidate["date_ordinal"])))[0]
        chosen["confidence"] = "LOW"
        warnings.append("ROIC: source non-Morningstar retenue en dernier recours; définition divergente, confiance LOW.")
        return chosen, warnings

    return sorted(candidates, key=lambda candidate: (-int(candidate["date_ordinal"]), int(candidate["source_rank"])))[0], warnings


def _research_source_type_from_row(row: dict[str, Any]) -> str:
    source_type = str(row.get("research_report_source_type") or row.get("research_report_company_description_source_type") or "")
    if source_type:
        return source_type
    return _classify_research_source_name(_first_research_source(row))[1]


def _research_source_rank_from_row(row: dict[str, Any]) -> int:
    rank = safe_float(row.get("research_report_source_rank"))
    if rank is None:
        rank = safe_float(row.get("research_report_company_description_source_rank"))
    if rank is not None:
        return int(rank)
    return _classify_research_source_name(_first_research_source(row))[0]


def _classify_research_source_name(source: str) -> tuple[int, str]:
    lower = str(source or "").lower()
    if "morningstar" in lower and "tear" in lower:
        return 2, "MORNINGSTAR_TEAR_SHEET"
    if "morningstar" in lower:
        return 1, "MORNINGSTAR_ANALYST"
    if "nbf" in lower or "national" in lower or "companyreport" in lower or "banque" in lower:
        return 3, "NATIONAL_BANK"
    return 4, "OTHER"


def _is_divergent_priority_candidate(field: str, source: str, source_type: str) -> bool:
    if _is_divergent_research_source(source):
        return True
    if field == "roic_5y_avg" and str(source_type or "") not in MORNINGSTAR_RESEARCH_SOURCE_TYPES:
        return True
    return False


def _is_divergent_research_source(source: str) -> bool:
    source_text = str(source or "").lower()
    return "définition divergente" in source_text or "definition divergent" in source_text or "cours cible" in source_text


def _fair_value_candidate_score(text: str, start: int, end: int) -> float:
    context = str(text or "")[max(0, start - 450) : min(len(text or ""), end + 450)].lower()
    score = 0.0
    if start < 8000:
        score += 2.0
    if re.search(r"\bprice\s*/\s*fve\b|\bprice\s*/\s*fair\s+value\b|\bprice\s+to\s+fair\s+value\b", context):
        score += 6.0
    if re.search(r"\bfair\s+value\s+uncertainty\s+economic\s+moat\s+sector\b", context):
        score += 6.0
    if re.search(r"\b(?:current\s+price|last\s+price|market\s+price)\b", context):
        score += 2.0
    if re.search(r"\b(?:archive|archived|analyst note|we (?:raise|lower|cut|increase|decrease)|previous|prior)\b", context):
        score -= 2.0
    return score


def extract_bool_from_patterns(text: str, true_patterns: list[str], false_patterns: list[str]) -> bool | None:
    for pattern in false_patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return False
    for pattern in true_patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return True
    return None


def research_field_confidence(field: str, source: str, extraction: dict[str, Any] | None = None) -> str:
    source_text = str(source or "").lower()
    confidence = "MEDIUM"

    if _is_divergent_research_source(source):
        confidence = "LOW"
    elif field in {"regulatory_risk_high", "geopolitical_risk_high", "single_product_dependency_high"}:
        confidence = "LOW"
    elif "morningstar economic moat" in source_text:
        confidence = "HIGH"
    elif "morningstar price/fve" in source_text:
        confidence = "HIGH"
    elif field in {"fair_value", "forward_pe_manual", "peg_manual", "roic_5y_avg", "eps_growth_estimated_3_5y"}:
        confidence = "MEDIUM"
    elif field in {
        "moat_clear",
        "valuation_vs_5y_avg_ok",
        "balance_sheet_strong",
        "management_quality_good",
        "margin_or_profitability_under_pressure",
    }:
        confidence = "MEDIUM"

    quality_status = str((extraction or {}).get("text_quality_status") or "").upper()
    if quality_status in {"LOW_TEXT_QUALITY", "OCR_USED"}:
        confidence = _downgrade_confidence(confidence)
    elif quality_status in {"OCR_NEEDED", "NO_TEXT_EXTRACTED", "UNREADABLE"}:
        confidence = "LOW"
    return confidence


def _downgrade_confidence(confidence: str) -> str:
    order = ["LOW", "MEDIUM", "HIGH"]
    try:
        index = order.index(str(confidence or "MEDIUM").upper())
    except ValueError:
        index = 1
    return order[max(0, index - 1)]


def extract_morningstar_moat_clear(text: str) -> tuple[bool | None, str, list[str]]:
    """Extract the company-level Morningstar moat without letting segment text override it."""
    warnings: list[str] = []
    structured = _extract_structured_morningstar_moat(text)
    has_generic_no_moat = _has_any_pattern(text, FALSE_MOAT_PATTERNS)

    if structured:
        rating = structured.lower().strip()
        if rating in {"wide", "narrow"}:
            if has_generic_no_moat:
                warnings.append(
                    "Moat: cote Morningstar globale Wide/Narrow priorisée; une mention 'no moat' ailleurs dans le rapport a été ignorée comme contexte non global."
                )
            return True, f"Morningstar Economic Moat={rating.upper()}", warnings
        if rating in {"none", "no moat"}:
            return False, "Morningstar Economic Moat=NONE", warnings

    true_found = _has_any_pattern(text, TRUE_MOAT_PATTERNS)
    company_false_found = _has_any_pattern(text, COMPANY_LEVEL_FALSE_MOAT_PATTERNS)
    generic_false_found = has_generic_no_moat

    if true_found and company_false_found:
        warnings.append("Moat: signaux contradictoires détectés; champ non utilisé automatiquement, validation manuelle recommandée.")
        return None, "", warnings
    if true_found:
        if generic_false_found:
            warnings.append(
                "Moat: mention positive détectée avec une mention générique 'no moat'; le signal positif est conservé, mais validation utile."
            )
        return True, "moat text pattern", warnings
    if company_false_found:
        return False, "company-level no moat text pattern", warnings
    if generic_false_found:
        warnings.append("Moat: mention 'no moat' détectée sans contexte entreprise clair; champ non utilisé automatiquement.")
    return None, "", warnings


def extract_morningstar_valuation_ok(text: str) -> tuple[bool | None, str, list[str]]:
    """Prefer Morningstar's numeric Price/FVE ratio over generic valuation wording."""
    warnings: list[str] = []
    price_fve = _extract_price_to_fair_value(text)
    if price_fve is not None:
        status = price_fve <= 1.30
        return status, f"Morningstar Price/FVE={price_fve:.2f}", warnings

    true_found = _has_any_pattern(text, TRUE_VALUATION_PATTERNS)
    false_found = _has_any_pattern(text, FALSE_VALUATION_PATTERNS)
    if true_found and false_found:
        warnings.append("Valorisation: signaux textuels contradictoires; champ non utilisé automatiquement.")
        return None, "", warnings
    if true_found:
        return True, "valuation text pattern", warnings
    if false_found:
        return False, "valuation text pattern", warnings
    return None, "", warnings


def _extract_structured_morningstar_moat(text: str) -> str:
    patterns = [
        r"\beconomic\s+moat\s*(?:tm|™)?\s*(?P<moat>wide|narrow|none|no\s+moat)\b",
        r"\bmoat\s*(?:rating)?\s*[:\-]?\s*(?P<moat>wide|narrow|none|no\s+moat)\b",
        rf"\bFair Value\s+Uncertainty\s+Economic Moat\s+Sector\s+Style[^\n\r]*\n\s*(?:CAD|USD|C\$|US\$|\$)?\s*{REPORT_NUMBER_CAPTURE}\s+\w+\s+(?P<moat>wide|narrow|none|no\s+moat)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return str(match.group("moat") if "moat" in match.groupdict() else match.group(1)).strip()
    return ""


def _extract_price_to_fair_value(text: str) -> float | None:
    patterns = [
        rf"\bprice\s*/\s*fve\s*[:\-]?\s*{REPORT_NUMBER_CAPTURE}\b",
        rf"\bprice\s*/\s*fair\s+value\s*[:\-]?\s*{REPORT_NUMBER_CAPTURE}\b",
        rf"\bprice\s+to\s+fair\s+value\s*[:\-]?\s*{REPORT_NUMBER_CAPTURE}\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue
        value = _safe_report_number(match.group(1))
        if value is None:
            continue
        if 10 < value <= 300:
            value = value / 100
        if value > 0:
            return value
    return None


def _has_any_pattern(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def _worst_text_quality_status(statuses: list[str]) -> str:
    if not statuses:
        return ""
    rank = {
        "TEXT_OK": 0,
        "OCR_USED": 1,
        "LOW_TEXT_QUALITY": 2,
        "OCR_NEEDED": 3,
        "NO_TEXT_EXTRACTED": 4,
        "UNREADABLE": 5,
        "UNSUPPORTED": 6,
    }
    clean = [str(status or "").upper() for status in statuses if str(status or "").strip()]
    if not clean:
        return ""
    return max(clean, key=lambda status: rank.get(status, 9))


def _worst_ocr_status(statuses: list[str]) -> str:
    if not statuses:
        return ""
    rank = {
        "NOT_APPLICABLE": 0,
        "NOT_USED": 1,
        "OCR_USED": 2,
        "OCR_NEEDED": 3,
    }
    clean = [str(status or "").upper() for status in statuses if str(status or "").strip()]
    if not clean:
        return ""
    return max(clean, key=lambda status: rank.get(status, 9))


def _indexed_reports(index_path: Path) -> dict[str, dict[str, Any]]:
    rows = {}
    for row in read_csv_records(index_path):
        file_name = str(row.get("file_name") or "").strip()
        if file_name:
            rows[file_name] = row
    return rows


def _latest_date_text(row: dict[str, Any]) -> str:
    dates = row.get("research_report_dates") or []
    if isinstance(dates, list) and dates:
        return str(dates[0])
    return ""


def _latest_metadata_by_ticker(reports_dir: Path) -> dict[str, dict[str, Any]]:
    metadata: dict[str, dict[str, Any]] = {}
    for path, universe in [
        (reports_dir / "latest_scores.csv", "CORE_PORTFOLIO"),
        (reports_dir / "latest_watchlist_report.csv", "WATCHLIST"),
        (reports_dir / "latest_market_candidates.csv", "MARKET_SCANNER"),
    ]:
        for row in read_csv_records(path):
            ticker = normalize_ticker(row.get("ticker"))
            if ticker:
                metadata[ticker] = {**row, "universe": universe}
    return metadata


def _truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "oui"}


REPORT_NUMBER_PATTERN = r"[+-]?(?:\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)"
REPORT_NUMBER_CAPTURE = rf"({REPORT_NUMBER_PATTERN})"
KNOWN_REPORT_SECTORS = [
    "Communication Services",
    "Consumer Discretionary",
    "Consumer Staples",
    "Consumer Cyclical",
    "Consumer Defensive",
    "Financial Services",
    "Information Technology",
    "Basic Materials",
    "Real Estate",
    "Technology",
    "Financials",
    "Healthcare",
    "Industrials",
    "Utilities",
    "Energy",
]
FAIR_VALUE_PATTERNS = [
    rf"(?:fair value estimate|fair value|juste valeur|valeur intrins[eè]que)[^\n\r0-9]{{0,80}}?(?:CAD|USD|C\$|US\$|\$)?\s*{REPORT_NUMBER_CAPTURE}",
    rf"\bFair Value\s+Uncertainty\s+Economic Moat\s+Sector\s+Style[^\n\r]*\n\s*(?:CAD|USD|C\$|US\$|\$)?\s*{REPORT_NUMBER_CAPTURE}",
]
ROIC_PATTERNS = [
    rf"(?:ROIC|return on invested capital|rendement du capital investi)[^\n\r%]{{0,80}}?{REPORT_NUMBER_CAPTURE}\s*%",
]
EPS_GROWTH_PATTERNS = [
    rf"(?:EPS|earnings|b[eé]n[eé]fice)[^\n\r%]{{0,80}}?(?:growth|croissance)[^\n\r%]{{0,80}}?{REPORT_NUMBER_CAPTURE}\s*%",
    rf"(?:growth|croissance)[^\n\r%]{{0,80}}?(?:EPS|earnings|b[eé]n[eé]fice)[^\n\r%]{{0,80}}?{REPORT_NUMBER_CAPTURE}\s*%",
]
FORWARD_PE_PATTERNS = [
    rf"(?:forward P/E|forward PE|P/E forward|PE forward|cours/b[eé]n[eé]fice pr[eé]visionnel)[^\n\r0-9]{{0,80}}?{REPORT_NUMBER_CAPTURE}",
]
PEG_PATTERNS = [
    rf"(?:PEG ratio|PEG)[^\n\r0-9]{{0,80}}?{REPORT_NUMBER_CAPTURE}",
]
TRUE_MOAT_PATTERNS = [r"\bwide moat\b", r"\bnarrow moat\b", r"\bmoat\s*:\s*(wide|narrow)\b", r"avantage concurrentiel"]
FALSE_MOAT_PATTERNS = [r"\bno moat\b", r"\bno economic moat\b", r"aucun avantage concurrentiel"]
COMPANY_LEVEL_FALSE_MOAT_PATTERNS = [
    r"\b(?:overall firm|company|firm|we assign|we rate|we view|analyst(?:s)? assign)[^\n\r.]{0,180}\b(?:no moat|no economic moat)\b",
    r"\b(?:no moat|no economic moat)\s+rating\s+(?:to|for)\s+(?:the\s+)?(?:overall firm|company|firm)\b",
    r"\b(?:company|firm)\s+(?:has|merits|receives|is assigned)[^\n\r.]{0,140}\b(?:no moat|no economic moat)\b",
]
TRUE_VALUATION_PATTERNS = [r"\bundervalued\b", r"below (?:our )?fair value", r"sous (?:sa |notre )?juste valeur", r"fairly valued"]
FALSE_VALUATION_PATTERNS = [r"\bovervalued\b", r"above (?:our )?fair value", r"au-dessus de (?:sa |notre )?juste valeur"]
TRUE_MARGIN_PRESSURE_PATTERNS = [r"margin pressure", r"margins? under pressure", r"pression sur les marges", r"rentabilit[eé] sous pression"]
FALSE_MARGIN_PRESSURE_PATTERNS = [r"stable margins?", r"margins? stable", r"marges? stables?", r"margin expansion", r"marges? en expansion"]
TRUE_BALANCE_PATTERNS = [r"strong balance sheet", r"sound balance sheet", r"bilan solide", r"low debt", r"faible endettement"]
FALSE_BALANCE_PATTERNS = [r"weak balance sheet", r"bilan faible", r"high debt", r"endettement [eé]lev[eé]"]
TRUE_MANAGEMENT_PATTERNS = [r"exemplary capital allocation", r"standard capital allocation", r"management quality", r"bonne qualit[eé] de gestion"]
FALSE_MANAGEMENT_PATTERNS = [r"poor capital allocation", r"poor management", r"mauvaise gestion"]
TRUE_REGULATORY_PATTERNS = [r"regulatory risk", r"risque r[eé]glementaire"]
TRUE_GEOPOLITICAL_PATTERNS = [r"geopolitical risk", r"risque g[eé]opolitique"]
TRUE_SINGLE_PRODUCT_PATTERNS = [r"single product", r"product concentration", r"d[eé]pendance.*produit"]
