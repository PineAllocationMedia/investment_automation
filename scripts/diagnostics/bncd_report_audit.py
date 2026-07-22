from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data_reliability_engine import (  # noqa: E402
    apply_reliability_cagr_cap,
    apply_reliability_confidence_cap,
    apply_reliability_conviction_cap,
    apply_reliability_opportunity_cap,
    compute_data_reliability,
)
from src.research_reports import (  # noqa: E402
    EPS_GROWTH_PATTERNS,
    FAIR_VALUE_PATTERNS,
    FORWARD_PE_PATTERNS,
    PEG_PATTERNS,
    ROIC_PATTERNS,
    extract_morningstar_moat_clear,
    extract_morningstar_valuation_ok,
    extract_report_text_detailed,
    infer_ticker_from_filename,
    merge_research_with_automated,
    parse_research_report,
    research_needed_rows_from_analysis_rows,
    research_report_has_usable_fields,
)
from src.research_reports import (  # noqa: E402
    _extract_price_to_fair_value,
    _extract_structured_morningstar_moat,
    _has_any_pattern,
)
from src.scoring import compute_fundamental_score  # noqa: E402
from src.utils import BNCD_MORNINGSTAR_DIR, REPORTS_DIR, read_csv_records, safe_float  # noqa: E402
from src.validation_priority_engine import build_validation_priority_rows  # noqa: E402


TARGET_FILES = [
    BNCD_MORNINGSTAR_DIR / "CSU.TO_2026-05-19_Morningstar_AnalystReport.pdf",
    BNCD_MORNINGSTAR_DIR / "CSU.TO_2026-05-17_Morningstar_TearSheet.pdf",
    BNCD_MORNINGSTAR_DIR / "CSU.TO_2026-05-13_NBF_CompanyReport.pdf",
]

NUMERIC_FIELD_PATTERNS = {
    "fair_value": FAIR_VALUE_PATTERNS,
    "roic_5y_avg": ROIC_PATTERNS,
    "eps_growth_estimated_3_5y": EPS_GROWTH_PATTERNS,
    "forward_pe_manual": FORWARD_PE_PATTERNS,
    "peg_manual": PEG_PATTERNS,
}

HELPFUL_FIELDS = [
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
]


class MarkdownLog:
    def __init__(self) -> None:
        self.lines: list[str] = []

    def add(self, text: str = "") -> None:
        self.lines.append(str(text))

    def heading(self, level: int, text: str) -> None:
        self.add(f"{'#' * level} {text}")
        self.add()

    def bullet(self, text: str) -> None:
        self.add(f"- {text}")

    def code(self, payload: Any, language: str = "text") -> None:
        self.add(f"```{language}")
        if isinstance(payload, str):
            self.add(payload)
        else:
            self.add(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
        self.add("```")
        self.add()

    def emit(self, text: str = "") -> None:
        print(text)
        self.add(text)

    def emit_payload(self, label: str, payload: Any) -> None:
        line = f"{label}: {json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)}"
        print(line)
        self.add(line)


def _run_text(command: list[str]) -> str:
    try:
        result = subprocess.run(command, cwd=PROJECT_ROOT, text=True, capture_output=True, check=False)
        return (result.stdout or result.stderr or "").strip()
    except Exception as exc:  # noqa: BLE001
        return f"UNAVAILABLE: {type(exc).__name__}: {exc}"


def _word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-zÀ-ÿ0-9]{2,}", text or ""))


def _marker_count(text: str) -> int:
    patterns = [
        r"\bmorningstar\b",
        r"\bfair value\b",
        r"\beconomic moat\b",
        r"\bprice\s*/\s*fve\b",
        r"\bforward\s+p/?e\b",
        r"\bpeg\b",
    ]
    return sum(1 for pattern in patterns if re.search(pattern, text or "", flags=re.IGNORECASE))


def _first_match_context(text: str, patterns: list[str], window: int = 50) -> dict[str, Any]:
    for pattern in patterns:
        match = re.search(pattern, text or "", flags=re.IGNORECASE)
        if not match:
            continue
        start = max(0, match.start(1) - window)
        end = min(len(text), match.end(1) + window)
        return {
            "pattern": pattern,
            "raw_match": match.group(1),
            "context": re.sub(r"\s+", " ", text[start:end]).strip(),
        }
    return {"pattern": "", "raw_match": "", "context": ""}


def _as_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    return [str(part).strip() for part in value if str(part).strip()]


def _parse_serialized_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(part) for part in value]
    text = str(value).strip()
    if not text:
        return []
    try:
        parsed = json.loads(text.replace("'", '"'))
        if isinstance(parsed, list):
            return [str(part) for part in parsed]
    except Exception:
        pass
    return [part.strip().strip("[]'\"") for part in text.split(",") if part.strip().strip("[]'\"")]


def _latest_score_row(ticker: str) -> dict[str, str] | None:
    path = REPORTS_DIR / "latest_scores.csv"
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if str(row.get("ticker") or "").upper() == ticker.upper():
                return row
    return None


def _synthetic_automated_payload() -> dict[str, Any]:
    return {
        "ticker": "CSU.TO",
        "roic_5y_avg": 28.0,
        "net_margin_stable_or_expanding": True,
        "eps_growth_5y": 16.0,
        "moat_clear": True,
        "eps_growth_estimated_3_5y": 14.5,
        "sector_cagr_estimated": 9.0,
        "fair_value": 3200.0,
        "valuation_vs_5y_avg_ok": True,
        "forward_pe_growth_acceptable": True,
        "management_quality_good": True,
        "balance_sheet_strong": True,
        "margin_or_profitability_under_pressure": False,
        "forward_pe_manual": 38.0,
        "peg_manual": 2.6,
        "manual_confidence_level": "MEDIUM",
        "input_data_mode": "AUTO_ESTIMATED",
        "auto_source_quality": "MEDIUM",
        "auto_estimated_fields": [
            "roic_5y_avg",
            "eps_growth_estimated_3_5y",
            "fair_value",
            "moat_clear",
            "peg_manual",
            "forward_pe_manual",
            "valuation_vs_5y_avg_ok",
        ],
        "proxy_corrections_applied": [
            {"field": "roic_5y_avg", "factor": 1.08},
            {"field": "eps_growth_estimated_3_5y", "factor": 0.96},
        ],
        "proxy_correction_fields": ["roic_5y_avg", "eps_growth_estimated_3_5y"],
        "proxy_correction_status": "ACTIVE",
    }


def _automated_payload_for_csu(log: MarkdownLog) -> tuple[dict[str, Any], str]:
    row = _latest_score_row("CSU.TO")
    if not row:
        log.bullet("Payload automatisé CSU.TO: latest_scores.csv absent ou sans CSU.TO; payload synthétique utilisé.")
        return _synthetic_automated_payload(), "SYNTHETIC_REPRESENTATIVE"

    payload = _synthetic_automated_payload()
    for field in HELPFUL_FIELDS:
        if field in row and row.get(field) not in {"", None}:
            payload[field] = row.get(field)
    payload["auto_estimated_fields"] = _parse_serialized_list(row.get("auto_estimated_fields")) or payload["auto_estimated_fields"]
    payload["manual_confidence_level"] = row.get("manual_confidence_level") or payload["manual_confidence_level"]
    payload["input_data_mode"] = row.get("input_data_mode") or payload["input_data_mode"]
    payload["auto_source_quality"] = row.get("auto_source_quality") or payload["auto_source_quality"]
    payload["proxy_correction_fields"] = _parse_serialized_list(row.get("proxy_correction_fields"))
    payload["proxy_corrections_applied"] = _parse_serialized_list(row.get("proxy_corrections_applied"))
    payload["proxy_correction_status"] = row.get("proxy_correction_status") or "UNKNOWN"
    log.bullet(
        "Payload automatisé CSU.TO: construit depuis latest_scores.csv quand possible, "
        "avec fallback synthétique pour les champs manuels non exportés."
    )
    return payload, "LATEST_SCORES_PLUS_SYNTHETIC_COMPLETION"


def _score_for_payload(payload: dict[str, Any]) -> dict[str, Any]:
    market = {
        "ticker": "CSU.TO",
        "market_cap": 85000000000,
        "profit_margins": 0.11,
        "operating_margins": 0.16,
        "forward_pe": safe_float(payload.get("forward_pe_manual")) or 38.0,
        "trailing_pe": 68.0,
        "peg": safe_float(payload.get("peg_manual")) or 2.6,
        "sector": "Technology",
        "industry": "Software - Application",
    }
    benchmark = {
        "benchmark_usable_cagr": 10.0,
        "benchmark_relevance_level": "HIGH",
    }
    return compute_fundamental_score("CSU.TO", payload, market, benchmark)


def _cap_probe(manual: dict[str, Any], score: dict[str, Any], reliability: dict[str, Any]) -> dict[str, Any]:
    confidence_after = apply_reliability_confidence_cap(manual, reliability)
    conviction_before = {
        "conviction_score": 92.0,
        "conviction_category": "VERY_HIGH",
        "conviction_reasons": ["synthetic high conviction before cap"],
    }
    conviction_after = apply_reliability_conviction_cap(conviction_before, reliability)
    cagr_before = {
        "expected_cagr_quality": "VERY_HIGH",
        "expected_cagr_reason": "synthetic CAGR quality before cap.",
    }
    cagr_after = apply_reliability_cagr_cap(cagr_before, reliability)
    opportunity_before = {
        "opportunity_cost_status": "CLEARLY_BETTER_THAN_VFV",
        "opportunity_cost_reason": "synthetic opportunity before cap.",
    }
    opportunity_after = apply_reliability_opportunity_cap(
        opportunity_before,
        reliability,
        thesis_status="INTACT",
        liquidation_status="GREEN",
        add_eligibility_status="ADD_ALLOWED",
    )
    return {
        "manual_confidence_before": manual.get("manual_confidence_level"),
        "manual_confidence_after": confidence_after.get("manual_confidence_level"),
        "confidence_cap": confidence_after.get("data_reliability_confidence_cap"),
        "conviction_before": conviction_before,
        "conviction_after": conviction_after,
        "cagr_before": cagr_before,
        "cagr_after": cagr_after,
        "opportunity_before": opportunity_before,
        "opportunity_after": opportunity_after,
    }


def _analysis_rows_for_prioritization() -> dict[str, dict[str, dict[str, Any]]]:
    return {
        "CORE_PORTFOLIO": {
            "HEAVY.TO": {
                "ticker": "HEAVY.TO",
                "ticker_display": "HEAVY.TO",
                "company_name": "Estimate Heavy Held Inc.",
                "current_value": 25000,
                "manual_required_criteria": ["fair_value", "moat_clear", "roic_5y_avg"],
                "auto_estimated_fields": ["fair_value", "eps_growth_estimated_3_5y", "peg_manual", "moat_clear"],
                "data_quality": "LOW",
                "ticker_validation_status": "VALID",
                "ticker_coverage_status": "PARTIAL",
                "data_reliability_level": "LOW",
                "auto_estimate_dependency": "HIGH",
                "automation_evidence_level": "WEAK",
                "score_evidence_level": "ESTIMATE_HEAVY",
                "capital_allocation_score": 82,
                "allocation_decision": "BUY / ADD",
                "final_position_action": "BUY / ADD",
                "thesis_status": "INTACT",
                "requires_manual_validation_for_large_allocation": True,
            }
        },
        "MARKET_SCANNER": {
            "BLOCK.TO": {
                "ticker": "BLOCK.TO",
                "ticker_display": "BLOCK.TO",
                "company_name": "Blocked High Score Candidate",
                "manual_required_criteria": ["fair_value", "roic_5y_avg"],
                "auto_estimated_fields": ["fair_value", "eps_growth_estimated_3_5y", "roic_5y_avg", "moat_clear"],
                "data_quality": "LOW",
                "ticker_validation_status": "VALID",
                "ticker_coverage_status": "PARTIAL",
                "data_reliability_level": "LOW",
                "auto_estimate_dependency": "HIGH",
                "automation_evidence_level": "WEAK",
                "score_evidence_level": "ESTIMATE_HEAVY",
                "capital_allocation_score": 91,
                "allocation_decision": "ELIGIBLE_BUT_NOT_SELECTED",
                "promotion_status": "WAIT_FOR_BETTER_DATA_OR_PRICE",
                "blocking_reason_category": "DATA_INSUFFICIENT",
                "thesis_status": "INTACT",
                "requires_manual_validation_for_large_allocation": True,
            },
            "FREE.TO": {
                "ticker": "FREE.TO",
                "ticker_display": "FREE.TO",
                "company_name": "Free Data Complete Candidate",
                "manual_required_criteria": [],
                "auto_estimated_fields": [],
                "data_quality": "HIGH",
                "ticker_validation_status": "VALID",
                "ticker_coverage_status": "FULL",
                "data_reliability_level": "HIGH",
                "auto_estimate_dependency": "LOW",
                "automation_evidence_level": "STRONG",
                "score_evidence_level": "AUTOMATED_STRONG",
                "capital_allocation_score": 88,
                "allocation_decision": "ELIGIBLE_BUT_NOT_SELECTED",
                "promotion_status": "PROMOTE_TO_CORE_REVIEW",
                "thesis_status": "INTACT",
                "requires_manual_validation_for_large_allocation": False,
            },
        },
    }


def section_a(log: MarkdownLog) -> list[dict[str, Any]]:
    log.heading(2, "A. Fidélité d'extraction")
    parsed_reports: list[dict[str, Any]] = []
    for path in TARGET_FILES:
        log.heading(3, path.name)
        if not path.exists():
            log.emit(f"ABSENT: {path}")
            continue
        extraction = extract_report_text_detailed(path)
        text = str(extraction.get("text") or "")
        extraction_summary = {
            "extraction_method": extraction.get("extraction_method"),
            "text_characters": extraction.get("text_characters"),
            "word_count": _word_count(text),
            "marker_count": _marker_count(text),
            "text_quality_score": extraction.get("text_quality_score"),
            "text_quality_status": extraction.get("text_quality_status"),
            "ocr_status": extraction.get("ocr_status"),
            "warnings": extraction.get("warnings"),
            "messages": extraction.get("messages"),
        }
        log.emit_payload("extraction_summary", extraction_summary)
        parsed = parse_research_report(path, "CSU.TO", {})
        parsed_reports.append(parsed)
        log.emit_payload(
            "parsed_core_status",
            {
                "research_report_status": parsed.get("research_report_status"),
                "manual_confidence_level": parsed.get("manual_confidence_level"),
                "research_report_has_usable_fields": research_report_has_usable_fields(parsed),
                "research_report_fields": parsed.get("research_report_fields"),
                "research_report_field_confidence": parsed.get("research_report_field_confidence"),
                "research_report_extraction_warnings": parsed.get("research_report_extraction_warnings"),
            },
        )
        final_values = {field: parsed.get(field) for field in HELPFUL_FIELDS}
        log.emit_payload("final_field_values", final_values)
        for field, patterns in NUMERIC_FIELD_PATTERNS.items():
            match_info = _first_match_context(text, patterns)
            match_info["parsed_value"] = parsed.get(field)
            log.emit_payload(f"numeric_match_{field}", match_info)
        structured_moat = _extract_structured_morningstar_moat(text)
        moat_value, moat_source, moat_warnings = extract_morningstar_moat_clear(text)
        moat_diag = {
            "structured_morningstar_moat": structured_moat,
            "structured_match_used": bool(structured_moat),
            "parsed_value": parsed.get("moat_clear"),
            "extractor_value": moat_value,
            "extractor_source": moat_source,
            "warnings": moat_warnings,
            "has_narrow_moat": bool(re.search(r"\bnarrow moat\b", text, flags=re.IGNORECASE)),
            "has_no_moat": bool(re.search(r"\bno moat\b|\bno economic moat\b", text, flags=re.IGNORECASE)),
        }
        log.emit_payload("moat_diagnostic", moat_diag)
        valuation_value, valuation_source, valuation_warnings = extract_morningstar_valuation_ok(text)
        valuation_diag = {
            "price_to_fair_value": _extract_price_to_fair_value(text),
            "valuation_source": valuation_source,
            "valuation_value": valuation_value,
            "parsed_value": parsed.get("valuation_vs_5y_avg_ok"),
            "warnings": valuation_warnings,
        }
        log.emit_payload("valuation_diagnostic", valuation_diag)
    safe_float_diag = {
        'safe_float("3,600")': safe_float("3,600"),
        'safe_float("3,600.00")': safe_float("3,600.00"),
        'safe_float("1,234.56")': safe_float("1,234.56"),
    }
    log.emit_payload("safe_float_bug_probe", safe_float_diag)
    return parsed_reports


def section_b(log: MarkdownLog) -> None:
    log.heading(2, "B. Inférence de ticker")
    known = ["CSU.TO", "RHM.NE", "TOI.V", "RHM.DE"]
    names = [
        "CSU.TO_2026-05-19_Morningstar_AnalystReport.pdf",
        "CSU_2026-05-19_Morningstar_AnalystReport.pdf",
        "RHM.NE_2026-05-19_Morningstar_AnalystReport.pdf",
        "RHM_2026-05-19_Morningstar_AnalystReport.pdf",
        "TOI.V_2026-05-19_Morningstar_AnalystReport.pdf",
        "RHM.DE_2026-05-19_Morningstar_AnalystReport.pdf",
    ]
    rows = [{"file_name": name, "inferred": infer_ticker_from_filename(name, known)} for name in names]
    log.emit_payload("ticker_inference_rows", rows)


def section_c_d(log: MarkdownLog, parsed_reports: list[dict[str, Any]]) -> None:
    log.heading(2, "C. Fusion")
    automated, source = _automated_payload_for_csu(log)
    log.emit_payload(
        "automated_payload_source",
        {
            "source": source,
            "input_data_mode": automated.get("input_data_mode"),
            "auto_estimated_fields": automated.get("auto_estimated_fields"),
            "proxy_correction_fields": automated.get("proxy_correction_fields"),
            "note": "Synthétique si le pipeline non-mutant complet n'est pas disponible; évite de relancer analyze.",
        },
    )
    automated_score = _score_for_payload(automated)
    automated_reliability = compute_data_reliability(automated, automated_score)
    log.heading(2, "D. Impact fiabilité")
    log.emit_payload(
        "before_research_reliability",
        {
            "score_total": automated_score.get("score_total"),
            "score_missing_data_count": automated_score.get("score_missing_data_count"),
            "data_reliability_score": automated_reliability.get("data_reliability_score"),
            "data_reliability_level": automated_reliability.get("data_reliability_level"),
            "auto_estimate_dependency": automated_reliability.get("auto_estimate_dependency"),
            "automation_evidence_level": automated_reliability.get("automation_evidence_level"),
            "caps": _cap_probe(automated, automated_score, automated_reliability),
        },
    )
    for research in parsed_reports:
        sources = research.get("research_report_sources") or ["UNKNOWN"]
        label = str(sources[0])
        log.heading(3, label)
        merged = merge_research_with_automated(automated, research)
        removed_auto = sorted(set(_as_list(automated.get("auto_estimated_fields"))) - set(_as_list(merged.get("auto_estimated_fields"))))
        removed_proxy = sorted(set(_as_list(automated.get("proxy_correction_fields"))) - set(_as_list(merged.get("proxy_correction_fields"))))
        log.emit_payload(
            "merge_result",
            {
                "research_fields": research.get("research_report_fields"),
                "applied_fields": merged.get("research_report_fields"),
                "input_data_mode": merged.get("input_data_mode"),
                "removed_auto_estimated_fields": removed_auto,
                "removed_proxy_correction_fields": removed_proxy,
                "manual_confidence_level": merged.get("manual_confidence_level"),
            },
        )
        merged_score = _score_for_payload(merged)
        merged_reliability = compute_data_reliability(merged, merged_score)
        log.emit_payload(
            "after_research_reliability",
            {
                "score_total": merged_score.get("score_total"),
                "score_missing_data_count": merged_score.get("score_missing_data_count"),
                "data_reliability_score": merged_reliability.get("data_reliability_score"),
                "data_reliability_level": merged_reliability.get("data_reliability_level"),
                "auto_estimate_dependency": merged_reliability.get("auto_estimate_dependency"),
                "automation_evidence_level": merged_reliability.get("automation_evidence_level"),
                "delta_reliability_score": round(
                    float(merged_reliability.get("data_reliability_score") or 0)
                    - float(automated_reliability.get("data_reliability_score") or 0),
                    2,
                ),
                "caps": _cap_probe(merged, merged_score, merged_reliability),
            },
        )


def section_e(log: MarkdownLog) -> None:
    log.heading(2, "E. Priorisation")
    analysis_groups = _analysis_rows_for_prioritization()
    needed_rows = research_needed_rows_from_analysis_rows(analysis_groups, existing_reports={})
    validation_rows = build_validation_priority_rows(analysis_groups, existing_reports={})
    log.emit_payload("research_needed_rows_from_analysis_rows", needed_rows)
    log.emit_payload("build_validation_priority_rows", validation_rows)
    free_needed = [row for row in needed_rows if row.get("ticker") == "FREE.TO"]
    free_validation = [row for row in validation_rows if row.get("ticker") == "FREE.TO"]
    log.emit_payload(
        "case_iii_free_data_complete_effect",
        {
            "research_needed_triggered": bool(free_needed),
            "validation_priority_triggered": bool(free_validation),
            "interpretation": (
                "Le candidat externe complet ne déclenche pas de demande BNCD si aucune donnée manuelle "
                "requise/proxy utile n'est présente dans les inputs synthétiques."
            ),
        },
    )


def section_f(log: MarkdownLog) -> None:
    log.heading(2, "F. Inventaire / architecture")
    inventory = {
        "research_reports.py": [
            "load_research_report_inputs(report_dir, index_path, known_tickers) -> dict[ticker, merged research manual row]",
            "parse_research_report(path, ticker, index_row) -> manual-like dict with research_report_* metadata",
            "extract_report_text_detailed(path) -> text extraction dict with method/quality/OCR status",
            "merge_research_rows(ticker, rows) -> merged multi-report research row",
            "merge_research_with_automated(automated, research) -> automated manual payload enriched by report fields",
            "research_needed_rows_from_reports(reports_dir) -> CSV/report-driven research-needed rows",
            "research_needed_rows_from_analysis_rows(analysis_groups_by_universe, existing_reports) -> analysis-driven research-needed rows",
            "research_status_rows(report_dir, index_path, known_tickers) -> readability/extraction inventory",
            "infer_ticker_from_filename(file_name, known_tickers) -> ticker guess from file name",
        ],
        "validation_priority_engine.py": [
            "build_validation_priority_rows(analysis_groups_by_universe, existing_reports, limit) -> field-level validation priorities",
            "write_validation_priority_csv(path, rows) -> reports/latest_validation_priority.csv writer",
            "validation_priority_rows_for_report(rows, limit) -> compact/full report subset",
        ],
        "data_reliability_engine.py": [
            "compute_data_reliability(manual, score) -> reliability score/level/dependency/caps metadata",
            "apply_reliability_confidence_cap(manual, reliability) -> caps manual_confidence_level",
            "apply_reliability_conviction_cap(conviction, reliability) -> caps conviction_score",
            "apply_reliability_cagr_cap(cagr, reliability) -> caps expected_cagr_quality",
            "apply_reliability_opportunity_cap(opportunity, reliability, thesis, liquidation, add) -> caps opportunity_cost_status",
        ],
        "main.py contact points": [
            "run_analysis() loads research_inputs via load_research_report_inputs() before build_position_analyses()",
            "build_position_analyses() calls merge_research_with_automated() before manual overrides and scoring",
            "build_position_analyses() calls compute_data_reliability() and reliability caps after scoring",
            "run_analysis() writes latest_research_needed.csv and latest_validation_priority.csv",
            "research-needed command builds rows through build_research_needed_rows_from_current_inputs()",
            "research-status command uses research_status_rows()",
        ],
        "CSV outputs": [
            "reports/latest_research_needed.csv",
            "reports/latest_research_status.csv",
            "reports/latest_validation_priority.csv",
            "reports/latest_scores.csv includes research_report_* and reliability columns",
        ],
        "call graph": [
            "main.run_analysis -> load_research_report_inputs -> parse_research_report -> extract_report_text_detailed",
            "main.build_position_analyses -> build_automated_manual_inputs -> merge_research_with_automated -> merge_automated_with_manual_overrides -> compute_fundamental_score -> compute_data_reliability -> reliability caps",
            "main.run_analysis -> research_needed_rows_from_analysis_rows -> write latest_research_needed.csv",
            "main.run_analysis -> build_validation_priority_rows -> write latest_validation_priority.csv -> report compact/full consumption",
        ],
    }
    log.emit_payload("architecture_inventory", inventory)


def final_findings(log: MarkdownLog, parsed_reports: list[dict[str, Any]]) -> None:
    log.heading(2, "RÉSUMÉ EXÉCUTIF")
    usable_count = sum(1 for row in parsed_reports if research_report_has_usable_fields(row))
    fields_by_file = {
        str((row.get("research_report_sources") or ["UNKNOWN"])[0]): row.get("research_report_fields")
        for row in parsed_reports
    }
    summary = [
        f"{len(parsed_reports)} rapport(s) CSU.TO parsé(s), {usable_count} avec champs utilisables selon research_report_has_usable_fields().",
        "Le diagnostic utilise les signatures réelles lues dans le code: parse_research_report(path, ticker, index_row), extract_report_text_detailed(path), merge_research_with_automated(automated, research), compute_data_reliability(manual, score), research_needed_rows_from_analysis_rows(analysis_groups_by_universe, existing_reports), build_validation_priority_rows(analysis_groups_by_universe, existing_reports, limit).",
        "Aucun moteur src/ n'a été modifié par ce script; les observations servent de base à une refonte ultérieure.",
    ]
    for item in summary:
        log.emit(item)
    log.emit_payload("fields_by_file", fields_by_file)
    log.heading(2, "LISTE PRIORISÉE des bugs / fragilités / lacunes trouvés")
    findings = [
        {
            "priority": "P1",
            "finding": "safe_float avec séparateurs de milliers doit être vérifié: les résultats imprimés dans A montrent si '3,600' devient 3.6 ou 3600.",
            "impact": "Peut fausser la juste valeur extraite si le format PDF utilise une virgule de milliers.",
        },
        {
            "priority": "P1",
            "finding": "Les regex numériques extraient seulement le premier match et ne conservent pas nativement le contexte brut.",
            "impact": "Risque de capturer un mauvais chiffre si le rapport contient plusieurs fair values, P/E ou taux de croissance autour du même libellé.",
        },
        {
            "priority": "P2",
            "finding": "infer_ticker_from_filename retire explicitement .TO et .V, mais pas .NE/.DE pour les noms sans suffixe.",
            "impact": "Un fichier 'RHM_...' peut inférer RHM au lieu de RHM.NE/RHM.DE selon known_tickers.",
        },
        {
            "priority": "P2",
            "finding": "research_needed_rows_from_analysis_rows et build_validation_priority_rows priorisent différemment: l'un raisonne par ticker, l'autre par champ.",
            "impact": "Les deux listes peuvent donner un ordre divergent pour la même situation de données.",
        },
        {
            "priority": "P3",
            "finding": "La fidélité du moat dépend fortement des libellés Morningstar structurés; les mentions génériques 'no moat' sont gérées mais restent fragiles.",
            "impact": "Besoin futur d'une extraction plus structurée par zone/table plutôt que regex globale.",
        },
    ]
    for finding in findings:
        log.emit_payload("finding", finding)


def main() -> int:
    diagnostics_dir = REPORTS_DIR / "diagnostics"
    diagnostics_dir.mkdir(parents=True, exist_ok=True)
    output_path = diagnostics_dir / f"bncd_report_subsystem_audit_{date.today().isoformat()}.md"

    log = MarkdownLog()
    log.heading(1, f"BNCD/Morningstar Research Report Subsystem Audit — {date.today().isoformat()}")
    log.emit_payload(
        "baseline_metadata",
        {
            "git_head": _run_text(["git", "rev-parse", "HEAD"]),
            "project_root": str(PROJECT_ROOT),
            "target_files": [str(path) for path in TARGET_FILES],
            "note": "Diagnostic autonome hors src/. Ne modifie aucun moteur.",
        },
    )
    parsed_reports = section_a(log)
    section_b(log)
    section_c_d(log, parsed_reports)
    section_e(log)
    section_f(log)
    final_findings(log, parsed_reports)

    output_path.write_text("\n".join(log.lines) + "\n", encoding="utf-8")
    print(f"\nREPORT_WRITTEN: {output_path}")
    print("\nRESUME_EXECUTIF:")
    for line in log.lines[-30:]:
        if line.startswith("finding:") or line.startswith("fields_by_file:"):
            print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
