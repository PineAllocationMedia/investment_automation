import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.research_reports import (
    date_from_filename,
    load_research_report_inputs,
    merge_research_with_automated,
    parse_research_report,
    research_needed_rows_from_analysis_rows,
    research_needed_rows_from_reports,
    research_report_has_usable_fields,
    research_status_rows,
    write_research_needed_csv,
)
from src.utils import write_csv_records


class ResearchReportsTest(unittest.TestCase):
    def test_parse_text_report_extracts_useful_fields(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "CSU.TO_2026-04-15_BNCD_Morningstar.txt"
            path.write_text(
                "Morningstar fair value estimate CAD 5200. Wide moat. "
                "Strong balance sheet. EPS growth 13%. Forward P/E 31. PEG 1.8. "
                "Stable margins.",
                encoding="utf-8",
            )

            parsed = parse_research_report(path, "CSU.TO")

        self.assertEqual(parsed["fair_value"], 5200)
        self.assertTrue(parsed["moat_clear"])
        self.assertTrue(parsed["balance_sheet_strong"])
        self.assertFalse(parsed["margin_or_profitability_under_pressure"])
        self.assertEqual(parsed["eps_growth_estimated_3_5y"], 13)
        self.assertEqual(parsed["forward_pe_manual"], 31)
        self.assertEqual(parsed["peg_manual"], 1.8)
        self.assertIn("fair_value", parsed["research_report_fields"])

    def test_research_overrides_automatic_estimates_but_keeps_metadata(self):
        automated = {
            "ticker": "CSU.TO",
            "fair_value": 4000,
            "moat_clear": None,
            "auto_estimated_fields": ["fair_value", "moat_clear"],
            "input_data_mode": "AUTO_ESTIMATED",
        }
        research = {
            "ticker": "CSU.TO",
            "fair_value": 5200,
            "moat_clear": True,
            "research_report_fields": ["fair_value", "moat_clear"],
            "research_report_sources": ["CSU.TO_2026-04-15_BNCD_Morningstar.pdf"],
            "research_report_status": "FOUND_FIELDS",
        }

        merged = merge_research_with_automated(automated, research)

        self.assertEqual(merged["fair_value"], 5200)
        self.assertTrue(merged["moat_clear"])
        self.assertEqual(merged["auto_estimated_fields"], [])
        self.assertEqual(merged["input_data_mode"], "AUTO_WITH_RESEARCH_REPORT")

    def test_load_research_report_inputs_infers_ticker_from_filename(self):
        with TemporaryDirectory() as folder:
            report_dir = Path(folder) / "bncd_morningstar"
            report_dir.mkdir()
            index_path = Path(folder) / "research_index.csv"
            write_csv_records(index_path, [], ["ticker", "provider", "report_date", "file_name", "notes"])
            (report_dir / "WSP.TO_2026-04-15_BNCD_Morningstar.txt").write_text(
                "Fair value 300. Narrow moat. Sound balance sheet.",
                encoding="utf-8",
            )

            loaded = load_research_report_inputs(report_dir, index_path, known_tickers=["WSP.TO"])

        self.assertIn("WSP.TO", loaded)
        self.assertEqual(loaded["WSP.TO"]["fair_value"], 300)
        self.assertIn("WSP.TO_2026-04-15_BNCD_Morningstar.txt", loaded["WSP.TO"]["research_report_sources"])

    def test_date_from_filename_accepts_year_first_and_month_first(self):
        self.assertEqual(date_from_filename("CSU.TO_2026-04-15_BNCD_Morningstar.pdf"), "2026-04-15")
        self.assertEqual(date_from_filename("AAPL_MORNINGSTAR_DATA_TEAR_SHEET_04-29-2026.pdf"), "2026-04-29")

    def test_research_needed_rows_prioritize_critical_gaps(self):
        with TemporaryDirectory() as folder:
            reports_dir = Path(folder)
            write_csv_records(
                reports_dir / "latest_scores.csv",
                [{"ticker": "CSU.TO", "ticker_display": "CSU.TO", "company_name_found": "Constellation", "data_quality": "LOW"}],
                ["ticker", "ticker_display", "company_name_found", "data_quality"],
            )
            write_csv_records(
                reports_dir / "latest_data_gaps.csv",
                [
                    {"ticker": "CSU.TO", "data_field": "C1: roic_5y_avg", "importance": "HIGH", "impact": ""},
                    {"ticker": "CSU.TO", "data_field": "C4: moat_clear", "importance": "HIGH", "impact": ""},
                    {"ticker": "CSU.TO", "data_field": "AUTO_ESTIMATE: fair_value", "importance": "MEDIUM", "impact": ""},
                ],
                ["ticker", "data_field", "importance", "impact"],
            )

            rows = research_needed_rows_from_reports(reports_dir)

        self.assertEqual(rows[0]["ticker"], "CSU.TO")
        self.assertEqual(rows[0]["priority"], "HIGH")
        self.assertIn("BNCD_Morningstar.pdf", rows[0]["suggested_file_name"])

    def test_research_needed_includes_watchlist_and_market_scanner(self):
        with TemporaryDirectory() as folder:
            reports_dir = Path(folder)
            write_csv_records(
                reports_dir / "latest_watchlist_report.csv",
                [{"ticker": "COST", "ticker_display": "COST", "data_quality": "MEDIUM"}],
                ["ticker", "ticker_display", "data_quality"],
            )
            write_csv_records(
                reports_dir / "latest_market_candidates.csv",
                [{"ticker": "BLX.TO", "ticker_display": "BLX.TO", "company_name": "Boralex Inc.", "data_quality": "LOW"}],
                ["ticker", "ticker_display", "company_name", "data_quality"],
            )
            write_csv_records(
                reports_dir / "latest_data_gaps.csv",
                [
                    {"ticker": "COST", "data_field": "C4: moat_clear", "importance": "HIGH", "impact": ""},
                    {"ticker": "BLX.TO", "data_field": "C1: roic_5y_avg", "importance": "HIGH", "impact": ""},
                ],
                ["ticker", "data_field", "importance", "impact"],
            )

            rows = research_needed_rows_from_reports(reports_dir)

        rows_by_ticker = {row["ticker"]: row for row in rows}
        self.assertEqual(rows_by_ticker["COST"]["universe"], "WATCHLIST")
        self.assertEqual(rows_by_ticker["BLX.TO"]["universe"], "MARKET_SCANNER")

    def test_research_needed_from_analysis_skips_existing_useful_report(self):
        analyses = {
            "CORE_PORTFOLIO": {
                "CSU.TO": {
                    "ticker": "CSU.TO",
                    "ticker_display": "CSU.TO",
                    "data_quality": "LOW",
                    "data_reliability_level": "LOW",
                    "auto_estimate_dependency": "HIGH",
                    "automation_evidence_level": "WEAK",
                    "manual_required_criteria": ["C1: roic_5y_avg", "C4: moat_clear"],
                    "auto_estimated_fields": ["fair_value", "moat_clear", "roic_5y_avg"],
                }
            }
        }
        existing = {"CSU.TO": {"research_report_fields": ["fair_value", "moat_clear"], "research_report_sources": ["CSU.pdf"]}}

        rows = research_needed_rows_from_analysis_rows(analyses, existing)

        self.assertEqual(rows, [])

    def test_research_needed_from_analysis_keeps_true_high_need_without_report(self):
        analyses = {
            "CORE_PORTFOLIO": {
                "NANO.TO": {
                    "ticker": "NANO.TO",
                    "ticker_display": "NANO.TO",
                    "data_quality": "LOW",
                    "data_reliability_level": "LOW",
                    "auto_estimate_dependency": "HIGH",
                    "automation_evidence_level": "WEAK",
                    "manual_required_criteria": ["C1: roic_5y_avg", "C4: moat_clear", "C10: fair_value"],
                    "auto_estimated_fields": ["fair_value", "moat_clear", "roic_5y_avg"],
                }
            }
        }

        rows = research_needed_rows_from_analysis_rows(analyses, {})

        self.assertEqual(rows[0]["ticker"], "NANO.TO")
        self.assertEqual(rows[0]["priority"], "HIGH")

    def test_research_needed_includes_eligible_core_without_qualitative_source(self):
        analyses = {
            "CORE_PORTFOLIO": {
                "GOOGL": {
                    "ticker": "GOOGL",
                    "ticker_display": "GOOGL",
                    "data_quality": "HIGH",
                    "data_reliability_level": "HIGH",
                    "auto_estimate_dependency": "LOW",
                    "automation_evidence_level": "STRONG",
                    "manual_required_criteria": [],
                    "auto_estimated_fields": [],
                    "add_eligibility_status": "ADD_ALLOWED",
                    "capital_allocation_score": 82,
                }
            }
        }

        rows = research_needed_rows_from_analysis_rows(analyses, {})

        self.assertEqual(rows[0]["ticker"], "GOOGL")
        self.assertEqual(rows[0]["need_type"], "QUALITATIVE")
        self.assertEqual(rows[0]["priority"], "HIGH")
        self.assertIn("source qualitative manquante", rows[0]["reason"])

    def test_research_needed_does_not_treat_do_not_add_as_recommended(self):
        analyses = {
            "CORE_PORTFOLIO": {
                "NANO.TO": {
                    "ticker": "NANO.TO",
                    "ticker_display": "NANO.TO",
                    "data_quality": "LOW",
                    "data_reliability_level": "LOW",
                    "auto_estimate_dependency": "HIGH",
                    "automation_evidence_level": "WEAK",
                    "manual_required_criteria": ["C1: roic_5y_avg"],
                    "auto_estimated_fields": ["roic_5y_avg"],
                    "add_eligibility_status": "DO_NOT_ADD",
                    "allocation_decision": "DO_NOT_ADD",
                    "capital_allocation_score": 0,
                }
            }
        }

        rows = research_needed_rows_from_analysis_rows(analyses, {})

        self.assertEqual(rows[0]["need_type"], "DATA")
        self.assertNotIn("QUALITATIVE", rows[0]["need_type"])
        self.assertNotIn("titre recommandé", rows[0]["reason"])

    def test_research_needed_skips_qualitative_need_when_report_source_exists(self):
        analyses = {
            "CORE_PORTFOLIO": {
                "GOOGL": {
                    "ticker": "GOOGL",
                    "ticker_display": "GOOGL",
                    "data_quality": "HIGH",
                    "data_reliability_level": "HIGH",
                    "auto_estimate_dependency": "LOW",
                    "automation_evidence_level": "STRONG",
                    "manual_required_criteria": [],
                    "auto_estimated_fields": [],
                    "add_eligibility_status": "ADD_ALLOWED",
                    "capital_allocation_score": 82,
                }
            }
        }
        existing = {"GOOGL": {"research_report_sources": ["GOOGL_2026-05-13_Morningstar.pdf"]}}

        rows = research_needed_rows_from_analysis_rows(analyses, existing)

        self.assertEqual(rows, [])

    def test_research_needed_skips_etf_assets(self):
        analyses = {
            "CORE_PORTFOLIO": {
                "XUS.TO": {
                    "ticker": "XUS.TO",
                    "asset_type": "ETF_S_AND_P_500",
                    "data_quality": "LOW",
                    "data_reliability_level": "LOW",
                    "manual_required_criteria": ["C1: roic_5y_avg"],
                    "auto_estimated_fields": ["roic_5y_avg"],
                    "add_eligibility_status": "ETF_HOLD_ONLY",
                }
            }
        }

        rows = research_needed_rows_from_analysis_rows(analyses, {})

        self.assertEqual(rows, [])

    def test_research_needed_from_reports_includes_missing_qualitative_report(self):
        with TemporaryDirectory() as folder:
            reports_dir = Path(folder)
            write_csv_records(
                reports_dir / "latest_qualitative_moat_report.csv",
                [
                    {
                        "ticker": "META",
                        "ticker_display": "META",
                        "target_status": "RECOMMANDÉ",
                        "source_status": "SOURCE_MISSING",
                    }
                ],
                ["ticker", "ticker_display", "target_status", "source_status"],
            )

            rows = research_needed_rows_from_reports(reports_dir)

        self.assertEqual(rows[0]["ticker"], "META")
        self.assertEqual(rows[0]["need_type"], "QUALITATIVE")
        self.assertEqual(rows[0]["priority"], "HIGH")

    def test_research_report_has_usable_fields_requires_helpful_extraction(self):
        self.assertTrue(research_report_has_usable_fields({"research_report_fields": ["fair_value"]}))
        self.assertFalse(research_report_has_usable_fields({"research_report_fields": ["regulatory_risk_high"]}))

    def test_research_status_reports_visible_readable_files(self):
        with TemporaryDirectory() as folder:
            report_dir = Path(folder) / "bncd_morningstar"
            report_dir.mkdir()
            index_path = Path(folder) / "research_index.csv"
            write_csv_records(index_path, [], ["ticker", "provider", "report_date", "file_name", "notes"])
            (report_dir / "CSU.TO_2026-04-15_BNCD_Morningstar.txt").write_text(
                "Morningstar fair value estimate CAD 5200. Wide moat.",
                encoding="utf-8",
            )

            rows = research_status_rows(report_dir, index_path, known_tickers=["CSU.TO"])

        self.assertEqual(rows[0]["file_name"], "CSU.TO_2026-04-15_BNCD_Morningstar.txt")
        self.assertEqual(rows[0]["ticker_detected"], "CSU.TO")
        self.assertTrue(rows[0]["readable"])
        self.assertEqual(rows[0]["status"], "READY")
        self.assertIn("fair_value", rows[0]["extracted_fields"])

    def test_research_status_flags_unknown_original_filename(self):
        with TemporaryDirectory() as folder:
            report_dir = Path(folder) / "bncd_morningstar"
            report_dir.mkdir()
            index_path = Path(folder) / "research_index.csv"
            write_csv_records(index_path, [], ["ticker", "provider", "report_date", "file_name", "notes"])
            (report_dir / "Morningstar Equity Report.txt").write_text(
                "Morningstar fair value estimate CAD 200. Wide moat.",
                encoding="utf-8",
            )

            rows = research_status_rows(report_dir, index_path, known_tickers=["CSU.TO"])

        self.assertEqual(rows[0]["ticker_detected"], "")
        self.assertEqual(rows[0]["status"], "NO_TICKER_DETECTED")


if __name__ == "__main__":
    unittest.main()
