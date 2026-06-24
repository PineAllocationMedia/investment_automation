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
]
RESEARCH_STATUS_COLUMNS = [
    "file_name",
    "ticker_detected",
    "provider",
    "report_date",
    "readable",
    "text_characters",
    "extracted_fields",
    "field_count",
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
    text, error = extract_report_text(path)
    row = empty_manual_row(ticker)
    extracted_fields: list[str] = []

    def set_field(field: str, value: Any) -> None:
        if field not in MANUAL_COLUMNS or field == "ticker":
            return
        if value is None or value == "":
            return
        row[field] = value
        extracted_fields.append(field)

    if text:
        set_field("fair_value", extract_first_number(text, FAIR_VALUE_PATTERNS))
        set_field("roic_5y_avg", extract_percent_number(text, ROIC_PATTERNS))
        set_field("eps_growth_estimated_3_5y", extract_percent_number(text, EPS_GROWTH_PATTERNS))
        set_field("forward_pe_manual", extract_first_number(text, FORWARD_PE_PATTERNS))
        set_field("peg_manual", extract_first_number(text, PEG_PATTERNS))
        set_field("moat_clear", extract_bool_from_patterns(text, TRUE_MOAT_PATTERNS, FALSE_MOAT_PATTERNS))
        set_field("valuation_vs_5y_avg_ok", extract_bool_from_patterns(text, TRUE_VALUATION_PATTERNS, FALSE_VALUATION_PATTERNS))
        set_field(
            "margin_or_profitability_under_pressure",
            extract_bool_from_patterns(text, TRUE_MARGIN_PRESSURE_PATTERNS, FALSE_MARGIN_PRESSURE_PATTERNS),
        )
        set_field("balance_sheet_strong", extract_bool_from_patterns(text, TRUE_BALANCE_PATTERNS, FALSE_BALANCE_PATTERNS))
        set_field("management_quality_good", extract_bool_from_patterns(text, TRUE_MANAGEMENT_PATTERNS, FALSE_MANAGEMENT_PATTERNS))
        set_field("regulatory_risk_high", extract_bool_from_patterns(text, TRUE_REGULATORY_PATTERNS, []))
        set_field("geopolitical_risk_high", extract_bool_from_patterns(text, TRUE_GEOPOLITICAL_PATTERNS, []))
        set_field("single_product_dependency_high", extract_bool_from_patterns(text, TRUE_SINGLE_PRODUCT_PATTERNS, []))

    source_name = path.name
    provider = str(index_row.get("provider") or "BNCD/Morningstar").strip()
    report_date = str(index_row.get("report_date") or date_from_filename(path.name) or "").strip()
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
    parsed["research_report_status"] = "FOUND_FIELDS" if extracted_fields else "NO_FIELDS_EXTRACTED"
    parsed["research_report_error"] = error
    return parsed


def merge_research_rows(ticker: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    merged = empty_manual_row(ticker)
    fields: list[str] = []
    sources: list[str] = []
    dates: list[str] = []
    errors: list[str] = []
    for row in sorted(rows, key=lambda item: _latest_date_text(item), reverse=True):
        row_fields = set(row.get("research_report_fields") or [])
        for field in row_fields:
            value = row.get(field)
            if value is not None and value != "" and merged.get(field) in {None, ""}:
                merged[field] = value
                fields.append(field)
        sources.extend(str(source) for source in row.get("research_report_sources") or [])
        dates.extend(str(report_date) for report_date in row.get("research_report_dates") or [] if report_date)
        if row.get("research_report_error"):
            errors.append(str(row.get("research_report_error")))

    merged["ticker"] = ticker
    merged["manual_confidence_level"] = "HIGH" if len(set(fields)) >= 4 else "MEDIUM"
    merged["notes"] = "Données enrichies par rapports BNCD/Morningstar locaux. À valider manuellement."
    parsed = parse_manual_row(merged)
    parsed["research_report_fields"] = sorted(set(fields))
    parsed["research_report_sources"] = sorted(set(sources))
    parsed["research_report_dates"] = sorted(set(dates), reverse=True)
    parsed["research_report_status"] = "FOUND_FIELDS" if fields else "NO_FIELDS_EXTRACTED"
    parsed["research_report_error"] = "; ".join(sorted(set(errors)))
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
    merged["auto_estimated_fields"] = [
        field for field in merged.get("auto_estimated_fields", []) if field not in set(applied)
    ]
    for key in ("official_supported_manual_fields", "official_confirmed_manual_fields"):
        merged[key] = [field for field in merged.get(key, []) if field not in set(applied)]
    merged["input_data_mode"] = "AUTO_WITH_RESEARCH_REPORT" if applied else automated.get("input_data_mode", "AUTO_ESTIMATED")
    if applied:
        merged["manual_confidence_level"] = research.get("manual_confidence_level") or merged.get("manual_confidence_level")
        merged["notes"] = research.get("notes") or merged.get("notes", "")
    return merged


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
                }
            )

    priority_rank = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    return sorted(
        rows,
        key=lambda row: (
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
                    "extracted_fields": "",
                    "field_count": 0,
                    "status": "IGNORED_UNSUPPORTED",
                    "message": "Type de fichier non supporté. Utilisez PDF, TXT ou MD.",
                }
            )
            continue

        text, error = extract_report_text(path)
        fields: list[str] = []
        if ticker and text:
            parsed = parse_research_report(path, ticker, index_row)
            fields = list(parsed.get("research_report_fields") or [])

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
                "extracted_fields": "; ".join(sorted(set(fields))),
                "field_count": len(set(fields)),
                "status": status,
                "message": message,
            }
        )

    return rows


def write_research_status_csv(path: str | Path, rows: list[dict[str, Any]]) -> None:
    write_csv_records(path, rows, RESEARCH_STATUS_COLUMNS)


def extract_report_text(path: Path) -> tuple[str, str]:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        try:
            return path.read_text(encoding="utf-8"), ""
        except UnicodeDecodeError:
            return path.read_text(encoding="latin-1"), ""
        except OSError as exc:
            return "", str(exc)
    if suffix != ".pdf":
        return "", "Type de fichier non supporté."
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
        return "", f"PDF non lisible automatiquement: {exc}"


def infer_ticker_from_filename(file_name: str, known_tickers: list[str]) -> str:
    upper = file_name.upper()
    candidates = sorted(set(known_tickers), key=len, reverse=True)
    for ticker in candidates:
        if ticker and ticker in upper:
            return ticker
        no_suffix = ticker.replace(".TO", "").replace(".V", "")
        if len(no_suffix) >= 2 and re.search(rf"(^|[^A-Z0-9]){re.escape(no_suffix)}([^A-Z0-9]|$)", upper):
            return ticker
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
            return safe_float(match.group(1))
    return None


def extract_percent_number(text: str, patterns: list[str]) -> float | None:
    return extract_first_number(text, patterns)


def extract_bool_from_patterns(text: str, true_patterns: list[str], false_patterns: list[str]) -> bool | None:
    for pattern in false_patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return False
    for pattern in true_patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return True
    return None


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


FAIR_VALUE_PATTERNS = [
    r"(?:fair value estimate|fair value|juste valeur|valeur intrins[eè]que)[^\n\r$]{0,80}?(?:CAD|USD|C\$|US\$|\$)?\s*([0-9]+(?:[.,][0-9]+)?)",
]
ROIC_PATTERNS = [
    r"(?:ROIC|return on invested capital|rendement du capital investi)[^\n\r%]{0,80}?([0-9]+(?:[.,][0-9]+)?)\s*%",
]
EPS_GROWTH_PATTERNS = [
    r"(?:EPS|earnings|b[eé]n[eé]fice)[^\n\r%]{0,80}?(?:growth|croissance)[^\n\r%]{0,80}?([0-9]+(?:[.,][0-9]+)?)\s*%",
    r"(?:growth|croissance)[^\n\r%]{0,80}?(?:EPS|earnings|b[eé]n[eé]fice)[^\n\r%]{0,80}?([0-9]+(?:[.,][0-9]+)?)\s*%",
]
FORWARD_PE_PATTERNS = [
    r"(?:forward P/E|forward PE|P/E forward|PE forward|cours/b[eé]n[eé]fice pr[eé]visionnel)[^\n\r0-9]{0,80}?([0-9]+(?:[.,][0-9]+)?)",
]
PEG_PATTERNS = [
    r"(?:PEG ratio|PEG)[^\n\r0-9]{0,80}?([0-9]+(?:[.,][0-9]+)?)",
]
TRUE_MOAT_PATTERNS = [r"\bwide moat\b", r"\bnarrow moat\b", r"\bmoat\s*:\s*(wide|narrow)\b", r"avantage concurrentiel"]
FALSE_MOAT_PATTERNS = [r"\bno moat\b", r"\bno economic moat\b", r"aucun avantage concurrentiel"]
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
