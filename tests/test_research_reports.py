import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from src.data_reliability_engine import compute_data_reliability
from src.evidence_provenance import field_is_confirmed
from src.research_reports import (
    FAIR_VALUE_PATTERNS,
    _safe_report_number,
    date_from_filename,
    extract_broker_target_price,
    extract_first_number,
    extract_nbccm_forward_pe_estimate,
    extract_report_text_detailed,
    extract_valuation_analysis_current_value,
    infer_ticker_from_filename,
    load_research_report_inputs,
    merge_research_rows,
    merge_research_with_automated,
    parse_research_report,
    research_needed_rows_from_analysis_rows,
    research_needed_rows_from_reports,
    research_report_has_usable_fields,
    research_status_rows,
    write_research_needed_csv,
)
from src.scoring import compute_fundamental_score
from src.utils import write_csv_records
from tests.helpers import strong_benchmark, strong_market


class ResearchReportsTest(unittest.TestCase):
    def test_report_number_parser_uses_english_thousand_separators(self):
        cases = {
            "3,600": 3600.0,
            "3,600.00": 3600.0,
            "1,234.56": 1234.56,
            "15.0": 15.0,
            "23": 23.0,
            "not-a-number": None,
        }

        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(_safe_report_number(raw), expected)

    def test_report_number_patterns_capture_full_grouped_number(self):
        value = extract_first_number("Fair Value Estimate 3,600.00 CAD", FAIR_VALUE_PATTERNS)

        self.assertEqual(value, 3600.0)

    def test_parse_report_prefers_header_fair_value_over_historical_values(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "CSU.TO_2026-05-19_Morningstar_AnalystReport.txt"
            path.write_text(
                "Analyst note archive: we lower our fair value estimate to 5,230.00 after results. "
                "Historical update: fair value estimate 4,170.00 after currency moves. "
                + (" " * 600)
                + "Market Price 2,612.34 CAD 15 May 2026 "
                "Fair Value Estimate 3,600.00 CAD 13 Mar 2026 Price/FVE 0.73. "
                "Economic MoatTM Narrow.",
                encoding="utf-8",
            )

            parsed = parse_research_report(path, "CSU.TO")

        self.assertEqual(parsed["fair_value"], 3600.0)
        self.assertTrue(parsed["moat_clear"])

    def test_morningstar_tear_sheet_extracts_fair_value_moat_and_forward_pe(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "CSU.TO_2026-05-17_Morningstar_TearSheet.txt"
            path.write_text(
                "Investment Detail Report | Release date 04-03-2026 | Currency: USD | Industry: Software - Application\n"
                "Profitability Analysis\n"
                "Grade: C Current 5 Yr Avg Ind Mkt\n"
                "Return on Equity % 16.1 29.0 14.9 15.5\n"
                "Return on Assets % 3.5 5.9 8.4 5.5\n"
                "Valuation Analysis\n"
                "Current 5 Yr Avg Ind Mkt\n"
                "Price/Earnings 72.7 93.1 39.1 18.8\n"
                "Forward P/E 15.0 — — —\n"
                "Price/Sales 3.2 6.7 6.0 —\n"
                "Fair Value Uncertainty Economic Moat Sector Style Market Cap (Mil) Sales (Mil) Last Close\n"
                "$3,600.00 Medium Narrow Technology Large Core 51,734 11,623 2,441.27\n",
                encoding="utf-8",
            )

            parsed = parse_research_report(path, "CSU.TO")

        self.assertEqual(parsed["fair_value"], 3600.0)
        self.assertTrue(parsed["moat_clear"])
        self.assertEqual(parsed["forward_pe_manual"], 15.0)
        self.assertNotIn("roic_5y_avg", parsed["research_report_fields"])
        self.assertTrue(research_report_has_usable_fields(parsed))

    def test_valuation_analysis_uses_current_column_not_industry_or_market(self):
        text = (
            "Valuation Analysis\n"
            "Current 5 Yr Avg Ind Mkt\n"
            "Price/Earnings 72.7 93.1 39.1 18.8\n"
            "Forward P/E 15.0 — — —\n"
        )

        self.assertEqual(extract_valuation_analysis_current_value(text, "Price/Earnings"), 72.7)
        self.assertEqual(extract_valuation_analysis_current_value(text, "Forward P/E"), 15.0)

    def test_broker_target_price_is_anchored_to_target_not_current_price(self):
        text = (
            "CSU (TSX) STOCK RATING TARGET EST . TOTAL RETURN\n"
            "C$2,422.40 Sector Perform\n"
            "(Unchanged)\n"
            "C$3,400.00\n"
            "(Unchanged)\n"
            "40.5%\n"
        )

        self.assertEqual(extract_broker_target_price(text), 3400.0)

    def test_broker_target_prefers_structured_header_and_matching_currency(self):
        text = (
            "STOCK RATING TARGET EST. TOTAL RETURN\n"
            "C$3,008.60 Outperform US$2,190.00 C$3,700.00 23.1%\n"
            "A valuation table later contains Target Price 1.39."
        )

        self.assertEqual(extract_broker_target_price(text), 3700.0)

    def test_implausible_fair_value_guard_rejects_corrupted_report_value(self):
        from main import _reject_implausible_fair_value

        manual = {
            "ticker": "CSU.TO",
            "fair_value": 3.6,
            "research_report_fields": ["fair_value", "moat_clear"],
            "research_report_extraction_warnings": ["existing warning"],
        }
        market = {"current_price": 2780.49}

        _reject_implausible_fair_value(manual, market)

        self.assertNotIn("fair_value", manual)
        self.assertEqual(manual["research_report_fields"], ["moat_clear"])
        self.assertIn("existing warning", manual["research_report_extraction_warnings"])
        warning = manual["research_report_extraction_warnings"][-1]
        self.assertIn("Fair value rejetée", warning)
        self.assertIn("CSU.TO", warning)
        self.assertIn("champ retiré avant scoring", warning)

    def test_implausible_fair_value_guard_preserves_plausible_report_value(self):
        from main import _reject_implausible_fair_value

        manual = {
            "ticker": "CSU.TO",
            "fair_value": 3600.0,
            "research_report_fields": ["fair_value"],
            "research_report_extraction_warnings": [],
        }
        market = {"current_price": 2780.49}

        _reject_implausible_fair_value(manual, market)

        self.assertEqual(manual["fair_value"], 3600.0)
        self.assertEqual(manual["research_report_fields"], ["fair_value"])
        self.assertEqual(manual["research_report_extraction_warnings"], [])

    def test_implausible_fair_value_guard_preserves_manual_override(self):
        from main import _reject_implausible_fair_value

        manual = {
            "ticker": "CSU.TO",
            "fair_value": 3.6,
            "manual_override_fields": ["fair_value"],
            "research_report_fields": ["fair_value"],
            "research_report_extraction_warnings": [],
        }
        market = {"current_price": 2780.49}

        _reject_implausible_fair_value(manual, market)

        self.assertEqual(manual["fair_value"], 3.6)
        self.assertEqual(manual["research_report_fields"], ["fair_value"])
        self.assertEqual(manual["research_report_extraction_warnings"], [])

    def test_nbccm_forward_pe_uses_first_estimate_year_not_actual_year(self):
        text = (
            "NBCCM ESTIMATES & VALUATION\n"
            "Fiscal Y/E December 2025A 2026E 2027E\n"
            "Revenue 10,000 11,000 12,000\n"
            "P/E (x) 19.3 15.2 12.6\n"
            "Source: NBF\n"
        )

        self.assertEqual(extract_nbccm_forward_pe_estimate(text), 15.2)

    def test_nbf_report_separates_target_and_current_roic_from_canonical_fields(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "ONLY.TO_2026-05-13_NBF_CompanyReport.txt"
            path.write_text(
                "National Bank Financial Markets company report. NBCCM. "
                "STOCK RATING TARGET EST . TOTAL RETURN\n"
                "C$2,422.40 Sector Perform\n"
                "(Unchanged)\n"
                "C$3,400.00\n"
                "(Unchanged)\n"
                "40.5%\n"
                "NBCCM ESTIMATES & VALUATION\n"
                "Fiscal Y/E December 2025A 2026E 2027E\n"
                "P/E (x) 19.3 15.2 12.6\n"
                "ROIC 23.0%\n"
                "Regulatory risk. Strong balance sheet.\n",
                encoding="utf-8",
            )

            parsed = parse_research_report(path, "ONLY.TO")

        self.assertIsNone(parsed["fair_value"])
        self.assertEqual(parsed["broker_target_price_12m"], 3400.0)
        self.assertEqual(parsed["forward_pe_manual"], 15.2)
        self.assertIsNone(parsed["roic_5y_avg"])
        self.assertEqual(parsed["roic_current"], 23.0)
        self.assertTrue(parsed["balance_sheet_strong"])
        self.assertIsNone(parsed["regulatory_risk_high"])
        self.assertNotIn("fair_value", parsed["research_report_fields"])
        self.assertNotIn("roic_5y_avg", parsed["research_report_fields"])
        self.assertIn("broker_target_price_12m", parsed["research_report_advisory_fields"])
        self.assertIn("roic_current", parsed["research_report_advisory_fields"])
        self.assertEqual(
            parsed["research_report_field_files"]["broker_target_price_12m"],
            "ONLY.TO_2026-05-13_NBF_CompanyReport.txt",
        )
        self.assertEqual(parsed["research_report_field_source_types"]["broker_target_price_12m"], "NATIONAL_BANK")
        self.assertEqual(parsed["research_report_field_report_dates"]["broker_target_price_12m"], "2026-05-13")

    def test_merge_research_rows_discards_broker_target_when_morningstar_fair_value_exists(self):
        rows = [
            {
                "ticker": "CSU.TO",
                "fair_value": 3400.0,
                "research_report_fields": ["fair_value"],
                "research_report_sources": ["CSU.TO_2026-05-13_NBF_CompanyReport.txt"],
                "research_report_dates": ["2026-05-13"],
                "research_report_source_rank": 3,
                "research_report_source_type": "NATIONAL_BANK",
                "research_report_field_sources": {
                    "fair_value": "cours cible 12 mois — courtier, définition divergente"
                },
                "research_report_field_confidence": {"fair_value": "LOW"},
            },
            {
                "ticker": "CSU.TO",
                "fair_value": 3600.0,
                "research_report_fields": ["fair_value"],
                "research_report_sources": ["CSU.TO_2026-05-19_Morningstar_AnalystReport.txt"],
                "research_report_dates": ["2026-05-19"],
                "research_report_source_rank": 1,
                "research_report_source_type": "MORNINGSTAR_ANALYST",
                "research_report_field_sources": {"fair_value": "fair value header pattern"},
                "research_report_field_confidence": {"fair_value": "MEDIUM"},
            },
        ]

        merged = merge_research_rows("CSU.TO", rows)

        self.assertEqual(merged["fair_value"], 3600.0)
        self.assertEqual(merged["research_report_field_confidence"]["fair_value"], "MEDIUM")
        self.assertTrue(
            any("écarté" in warning for warning in merged.get("research_report_extraction_warnings") or [])
        )

    def test_merge_research_rows_keeps_broker_target_advisory_when_no_intrinsic_value(self):
        rows = [
            {
                "ticker": "ONLY.TO",
                "broker_target_price_12m": 3400.0,
                "research_report_fields": [],
                "research_report_extracted_fields": ["broker_target_price_12m"],
                "research_report_advisory_fields": ["broker_target_price_12m"],
                "research_report_sources": ["ONLY.TO_2026-05-13_NBF_CompanyReport.txt"],
                "research_report_dates": ["2026-05-13"],
                "research_report_source_rank": 3,
                "research_report_source_type": "NATIONAL_BANK",
                "research_report_field_sources": {
                    "broker_target_price_12m": "broker target price 12m pattern"
                },
                "research_report_field_confidence": {"broker_target_price_12m": "MEDIUM"},
                "research_report_field_reasons": {
                    "broker_target_price_12m": "BROKER_TARGET_NOT_INTRINSIC_FAIR_VALUE"
                },
            }
        ]

        merged = merge_research_rows("ONLY.TO", rows)

        self.assertIsNone(merged["fair_value"])
        self.assertEqual(merged["broker_target_price_12m"], 3400.0)
        self.assertEqual(merged["research_report_fields"], [])
        self.assertIn("broker_target_price_12m", merged["research_report_advisory_fields"])
        self.assertEqual(merged["manual_confidence_level"], "MEDIUM")

    def test_parse_report_extracts_descriptive_fields_without_confirming_them(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "CSU.TO_2026-05-19_Morningstar_AnalystReport.txt"
            path.write_text(
                "Morningstar Equity Analyst Report. Economic Moat section. "
                "Sector Industry\n"
                "a Technology Software - Application\n"
                "Business Description\n"
                "Constellation Software is an acquirer, manager, and developer of vertical market software businesses globally. "
                "Its decentralized model lets business-unit managers optimize returns on invested capital and revenue growth.\n"
                "Business Strategy & Outlook\n"
                "The company compounds through disciplined acquisitions.",
                encoding="utf-8",
            )

            parsed = parse_research_report(path, "CSU.TO")

        self.assertIn("vertical market software", parsed["research_report_company_description"])
        self.assertEqual(parsed["research_report_sector"], "Technology")
        self.assertEqual(parsed["research_report_industry"], "Software - Application")
        self.assertEqual(parsed["research_report_fields"], [])
        self.assertFalse(research_report_has_usable_fields(parsed))

    def test_description_only_report_does_not_raise_data_reliability(self):
        automated = {
            "ticker": "CSU.TO",
            "input_data_mode": "AUTO_ESTIMATED",
            "auto_estimated_fields": ["fair_value", "moat_clear", "eps_growth_estimated_3_5y"],
            "auto_source_quality": "MEDIUM",
        }
        score = {"score_missing_data_count": 2}
        before = compute_data_reliability(automated, score)
        research = {
            "ticker": "CSU.TO",
            "research_report_company_description": "Constellation Software acquires and manages vertical market software businesses.",
            "research_report_sector": "Technology",
            "research_report_industry": "Software - Application",
            "research_report_fields": [],
            "research_report_sources": ["CSU.TO_2026-05-19_Morningstar_AnalystReport.txt"],
            "research_report_dates": ["2026-05-19"],
            "research_report_status": "NO_FIELDS_EXTRACTED",
        }

        merged = merge_research_with_automated(automated, research)
        after = compute_data_reliability(merged, score)

        self.assertEqual(merged["research_report_fields"], [])
        self.assertEqual(merged["input_data_mode"], "AUTO_ESTIMATED")
        self.assertEqual(before["data_reliability_score"], after["data_reliability_score"])
        self.assertFalse(research_report_has_usable_fields(merged))

    def test_old_descriptive_report_is_ignored(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "CSU.TO_2000-01-01_Morningstar_AnalystReport.txt"
            path.write_text(
                "Morningstar Equity Analyst Report. Economic Moat section. "
                "Business Description\n"
                "Constellation Software is an acquirer and developer of vertical market software businesses globally. "
                "This old profile should not be retained for current reporting.\n"
                "Business Strategy & Outlook\n",
                encoding="utf-8",
            )

            parsed = parse_research_report(path, "CSU.TO")

        self.assertNotIn("research_report_company_description", parsed)
        self.assertTrue(
            any("plus de 24 mois" in warning for warning in parsed.get("research_report_extraction_warnings") or [])
        )

    def test_descriptive_merge_prefers_source_hierarchy_before_recency(self):
        rows = [
            {
                "ticker": "CSU.TO",
                "research_report_company_description": "NBF company profile description.",
                "research_report_sources": ["CSU.TO_2026-06-01_NBF_CompanyReport.txt"],
                "research_report_dates": ["2026-06-01"],
                "research_report_company_description_date": "2026-06-01",
                "research_report_company_description_source_rank": 3,
                "research_report_company_description_source_type": "NATIONAL_BANK",
                "research_report_fields": [],
            },
            {
                "ticker": "CSU.TO",
                "research_report_company_description": "Morningstar analyst business description.",
                "research_report_sources": ["CSU.TO_2026-05-01_Morningstar_AnalystReport.txt"],
                "research_report_dates": ["2026-05-01"],
                "research_report_company_description_date": "2026-05-01",
                "research_report_company_description_source_rank": 1,
                "research_report_company_description_source_type": "MORNINGSTAR_ANALYST",
                "research_report_fields": [],
            },
        ]

        merged = merge_research_rows("CSU.TO", rows)

        self.assertEqual(merged["research_report_company_description"], "Morningstar analyst business description.")
        self.assertEqual(merged["research_report_company_description_source"], "CSU.TO_2026-05-01_Morningstar_AnalystReport.txt")
        self.assertEqual(merged["research_report_company_description_source_rank"], 1)

    def test_non_descriptive_fields_keep_chronological_merge_rule(self):
        rows = [
            {
                "ticker": "CSU.TO",
                "fair_value": 1000,
                "research_report_fields": ["fair_value"],
                "research_report_sources": ["CSU.TO_2026-05-01_Morningstar_AnalystReport.txt"],
                "research_report_dates": ["2026-05-01"],
                "research_report_field_sources": {"fair_value": "older fair value"},
                "research_report_field_confidence": {"fair_value": "MEDIUM"},
                "research_report_company_description": "Better source description.",
                "research_report_company_description_date": "2026-05-01",
                "research_report_company_description_source_rank": 1,
            },
            {
                "ticker": "CSU.TO",
                "fair_value": 2000,
                "research_report_fields": ["fair_value"],
                "research_report_sources": ["CSU.TO_2026-06-01_NBF_CompanyReport.txt"],
                "research_report_dates": ["2026-06-01"],
                "research_report_field_sources": {"fair_value": "newer fair value"},
                "research_report_field_confidence": {"fair_value": "MEDIUM"},
                "research_report_company_description": "Newer but lower-ranked description.",
                "research_report_company_description_date": "2026-06-01",
                "research_report_company_description_source_rank": 3,
            },
        ]

        merged = merge_research_rows("CSU.TO", rows)

        self.assertEqual(merged["fair_value"], 2000)
        self.assertEqual(merged["research_report_company_description"], "Better source description.")

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

    def test_structured_morningstar_wide_moat_overrides_segment_no_moat(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "META_2026-04-30_BNCD_Morningstar.txt"
            path.write_text(
                "Morningstar Equity Research. Economic MoatTM Wide. Fair Value Estimate 850. "
                "Price/FVE 0.79. Reality Labs business merits a no moat rating.",
                encoding="utf-8",
            )

            parsed = parse_research_report(path, "META")

        self.assertTrue(parsed["moat_clear"])
        self.assertEqual(parsed["price_to_fair_value"], 0.79)
        self.assertIsNone(parsed["valuation_vs_5y_avg_ok"])
        self.assertIn("moat_clear", parsed["research_report_fields"])
        self.assertNotIn("valuation_vs_5y_avg_ok", parsed["research_report_fields"])
        self.assertIn("price_to_fair_value", parsed["research_report_advisory_fields"])
        self.assertTrue(parsed["research_report_extraction_warnings"])

    def test_structured_morningstar_no_moat_can_flag_false(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "XYZ_2026-04-30_BNCD_Morningstar.txt"
            path.write_text("Morningstar Equity Research. Economic MoatTM None. Price/FVE 0.90.", encoding="utf-8")

            parsed = parse_research_report(path, "XYZ")

        self.assertFalse(parsed["moat_clear"])
        self.assertEqual(parsed["price_to_fair_value"], 0.90)
        self.assertIsNone(parsed["valuation_vs_5y_avg_ok"])

    def test_unstructured_conflicting_moat_is_not_used_as_false(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "ABC_2026-04-30_BNCD_Morningstar.txt"
            path.write_text(
                "The company has a wide moat, but one segment also mentions a no moat rating.",
                encoding="utf-8",
            )

            parsed = parse_research_report(path, "ABC")

        self.assertIsNone(parsed["moat_clear"])
        self.assertNotIn("moat_clear", parsed["research_report_fields"])
        self.assertTrue(parsed["research_report_extraction_warnings"])

    def test_price_fve_remains_informational_and_does_not_populate_historical_valuation(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "DEF_2026-04-30_BNCD_Morningstar.txt"
            path.write_text(
                "Morningstar Equity Research. Price/FVE 0.85. A methodology note explains cases above our fair value.",
                encoding="utf-8",
            )

            parsed = parse_research_report(path, "DEF")

        self.assertEqual(parsed["price_to_fair_value"], 0.85)
        self.assertIsNone(parsed["valuation_vs_5y_avg_ok"])
        self.assertNotIn("valuation_vs_5y_avg_ok", parsed["research_report_fields"])
        self.assertIn("price_to_fair_value", parsed["research_report_advisory_fields"])

    def test_research_report_records_field_level_confidence(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "META_2026-04-30_BNCD_Morningstar.txt"
            path.write_text(
                "Morningstar Equity Research. Economic MoatTM Wide. Price/FVE 0.79. Regulatory risk.",
                encoding="utf-8",
            )

            parsed = parse_research_report(path, "META")

        confidence = parsed["research_report_field_confidence"]
        self.assertEqual(confidence["moat_clear"], "HIGH")
        self.assertEqual(confidence["price_to_fair_value"], "HIGH")
        self.assertNotIn("regulatory_risk_high", confidence)

    def test_pdf_text_extraction_uses_pymupdf_when_pypdf_quality_is_low(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "META_2026-04-30_BNCD_Morningstar.pdf"
            path.write_bytes(b"%PDF placeholder")
            good_text = (
                "Morningstar Equity Research. Economic MoatTM Wide. Fair Value Estimate 850. Price/FVE 0.79. "
                * 40
            )

            with patch("src.research_reports._extract_pdf_text_pypdf", return_value=("tiny", "")), patch(
                "src.research_reports._extract_pdf_text_pymupdf", return_value=(good_text, "")
            ), patch("src.research_reports._extract_pdf_text_ocr", return_value=("", "OCR unavailable")):
                extraction = extract_report_text_detailed(path)

        self.assertEqual(extraction["extraction_method"], "PyMuPDF")
        self.assertEqual(extraction["text_quality_status"], "TEXT_OK")
        self.assertGreater(extraction["text_quality_score"], 60)

    def test_pdf_text_extraction_flags_ocr_needed_when_text_is_too_short(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "SCAN_2026-04-30_BNCD_Morningstar.pdf"
            path.write_bytes(b"%PDF placeholder")

            with patch("src.research_reports._extract_pdf_text_pypdf", return_value=("", "")), patch(
                "src.research_reports._extract_pdf_text_pymupdf", return_value=("", "")
            ), patch("src.research_reports._extract_pdf_text_ocr", return_value=("", "OCR unavailable")):
                extraction = extract_report_text_detailed(path)

        self.assertEqual(extraction["text_quality_status"], "OCR_NEEDED")
        self.assertEqual(extraction["ocr_status"], "OCR_NEEDED")
        self.assertTrue(extraction["warnings"])

    def test_ocr_quality_downgrade_keeps_ambiguous_field_advisory(self):
        extraction = {
            "text": "Morningstar Equity Research. Fair Value Estimate 3,600.00.",
            "error": "",
            "extraction_method": "OCR_TESSERACT",
            "text_quality_status": "OCR_USED",
            "text_quality_score": 65.0,
            "ocr_status": "OCR_USED",
            "text_characters": 60,
            "warnings": [],
            "messages": [],
        }
        with TemporaryDirectory() as folder:
            path = Path(folder) / "OCR_2026-08-01_Morningstar_AnalystReport.pdf"
            path.write_bytes(b"%PDF placeholder")
            with patch("src.research_reports.extract_report_text_detailed", return_value=extraction):
                parsed = parse_research_report(path, "OCR")

        self.assertEqual(parsed["fair_value"], 3600.0)
        self.assertEqual(parsed["research_report_field_confidence"]["fair_value"], "LOW")
        self.assertNotIn("fair_value", parsed["research_report_fields"])
        self.assertIn("fair_value", parsed["research_report_advisory_fields"])

    def test_research_overrides_automatic_estimates_but_keeps_metadata(self):
        automated = {
            "ticker": "CSU.TO",
            "fair_value": 4000,
            "moat_clear": None,
            "auto_estimated_fields": ["fair_value", "moat_clear"],
            "input_data_mode": "AUTO_ESTIMATED",
            "proxy_corrections_applied": [
                {"field": "fair_value", "factor": 1.10},
                {"field": "roic_5y_avg", "factor": 1.08},
            ],
            "proxy_correction_fields": ["fair_value", "roic_5y_avg"],
            "proxy_correction_status": "ACTIVE",
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
        self.assertEqual(merged["proxy_correction_fields"], ["roic_5y_avg"])
        self.assertEqual(merged["proxy_correction_status"], "ACTIVE")
        self.assertEqual(merged["input_data_mode"], "AUTO_WITH_RESEARCH_REPORT")

    def test_low_confidence_research_is_retained_for_audit_without_replacing_proxy(self):
        automated = {
            "ticker": "LOW.TO",
            "fair_value": 4000.0,
            "auto_estimated_fields": ["fair_value"],
            "input_data_mode": "AUTO_ESTIMATED",
            "auto_source_quality": "MEDIUM",
            "proxy_corrections_applied": [{"field": "fair_value", "factor": 1.1}],
            "proxy_correction_fields": ["fair_value"],
            "proxy_correction_status": "ACTIVE",
        }
        research = {
            "ticker": "LOW.TO",
            "fair_value": 5200.0,
            "research_report_fields": ["fair_value"],
            "research_report_extracted_fields": ["fair_value"],
            "research_report_field_confidence": {"fair_value": "LOW"},
            "research_report_sources": ["LOW.TO_2026-08-01_OCR.pdf"],
            "research_report_dates": ["2026-08-01"],
        }

        merged = merge_research_with_automated(automated, research)
        reliability = compute_data_reliability(merged, {"score_missing_data_count": 0})

        self.assertEqual(merged["fair_value"], 4000.0)
        self.assertEqual(merged["research_report_fields"], [])
        self.assertIn("fair_value", merged["research_report_extracted_fields"])
        self.assertIn("fair_value", merged["research_report_advisory_fields"])
        self.assertIn("fair_value", merged["auto_estimated_fields"])
        self.assertIn("fair_value", merged["proxy_correction_fields"])
        self.assertFalse(field_is_confirmed(merged, "fair_value"))
        self.assertNotIn("fair_value", reliability["confirmed_critical_fields"])

    def test_medium_confidence_applies_without_higher_authority(self):
        automated = {
            "ticker": "MED.TO",
            "fair_value": 4000.0,
            "auto_estimated_fields": ["fair_value"],
            "input_data_mode": "AUTO_ESTIMATED",
        }
        research = {
            "fair_value": 5200.0,
            "research_report_fields": ["fair_value"],
            "research_report_field_confidence": {"fair_value": "MEDIUM"},
        }

        merged = merge_research_with_automated(automated, research)

        self.assertEqual(merged["fair_value"], 5200.0)
        self.assertEqual(merged["research_report_fields"], ["fair_value"])
        self.assertEqual(merged["field_provenance"]["fair_value"], "RESEARCH_REPORT")

    def test_medium_confidence_does_not_override_official_evidence(self):
        automated = {
            "ticker": "MED.TO",
            "fair_value": 4000.0,
            "auto_estimated_fields": ["fair_value"],
            "official_confirmed_manual_fields": ["fair_value"],
            "input_data_mode": "AUTO_ESTIMATED",
        }
        research = {
            "fair_value": 5200.0,
            "research_report_fields": ["fair_value"],
            "research_report_extracted_fields": ["fair_value"],
            "research_report_field_confidence": {"fair_value": "MEDIUM"},
        }

        merged = merge_research_with_automated(automated, research)

        self.assertEqual(merged["fair_value"], 4000.0)
        self.assertEqual(merged["research_report_fields"], [])
        self.assertIn("fair_value", merged["research_report_advisory_fields"])
        self.assertEqual(
            merged["research_report_field_reasons"]["fair_value"],
            "HIGHER_AUTHORITY_OFFICIAL_EVIDENCE",
        )

    def test_high_confidence_research_applies_with_research_provenance(self):
        automated = {
            "ticker": "HIGH.TO",
            "moat_clear": None,
            "auto_estimated_fields": ["moat_clear"],
            "input_data_mode": "AUTO_ESTIMATED",
        }
        research = {
            "moat_clear": True,
            "research_report_fields": ["moat_clear"],
            "research_report_extracted_fields": ["moat_clear"],
            "research_report_field_confidence": {"moat_clear": "HIGH"},
        }

        merged = merge_research_with_automated(automated, research)

        self.assertTrue(merged["moat_clear"])
        self.assertEqual(merged["field_provenance"]["moat_clear"], "RESEARCH_REPORT")
        self.assertNotIn("moat_clear", merged.get("manual_override_fields", []))
        self.assertTrue(field_is_confirmed(merged, "moat_clear"))

    def test_roic_periods_do_not_masquerade_as_five_year_average(self):
        cases = {
            "average adjusted ROIC of 10.3% over the trailing decade": ("roic_10y_avg", 10.3),
            "ROIC 23%": ("roic_current", 23.0),
        }
        for text, (field, expected) in cases.items():
            with self.subTest(text=text), TemporaryDirectory() as folder:
                path = Path(folder) / "ROIC_2026-08-01_NBF_CompanyReport.txt"
                path.write_text(f"National Bank Financial Markets. {text}", encoding="utf-8")
                parsed = parse_research_report(path, "ROIC")
            self.assertIsNone(parsed["roic_5y_avg"])
            self.assertEqual(parsed[field], expected)
            self.assertIn(field, parsed["research_report_advisory_fields"])

    def test_explicit_five_year_roic_populates_canonical_field(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "ROIC_2026-08-01_Morningstar_AnalystReport.txt"
            path.write_text("Morningstar. Average adjusted ROIC 18.2% over the trailing 5 years.", encoding="utf-8")
            parsed = parse_research_report(path, "ROIC")

        self.assertEqual(parsed["roic_5y_avg"], 18.2)
        self.assertIn("roic_5y_avg", parsed["research_report_fields"])

    def test_multiple_roic_periods_use_nearest_percentage_for_each_period(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "ROIC_2026-08-01_Morningstar_AnalystReport.txt"
            path.write_text(
                "Morningstar. ROIC averaged 7.5% over the 10 years ended in 2025, "
                "and around 10% over the five years ended on the same date.",
                encoding="utf-8",
            )
            parsed = parse_research_report(path, "ROIC")

        self.assertEqual(parsed["roic_5y_avg"], 10.0)
        self.assertEqual(parsed["roic_10y_avg"], 7.5)
        self.assertIn("roic_5y_avg", parsed["research_report_fields"])
        self.assertIn("roic_10y_avg", parsed["research_report_advisory_fields"])

    def test_qualitative_reversal_does_not_create_high_risk_boolean(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "RISK_2026-08-01_Morningstar_AnalystReport.txt"
            path.write_text("Morningstar. Regulatory risk has declined materially.", encoding="utf-8")
            parsed = parse_research_report(path, "RISK")

        self.assertIsNone(parsed["regulatory_risk_high"])
        self.assertNotIn("regulatory_risk_high", parsed["research_report_extracted_fields"])

    def test_explicit_historical_valuation_is_distinct_from_price_fve(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "VALUE_2026-08-01_Morningstar_AnalystReport.txt"
            path.write_text(
                "Morningstar. Current valuation is below its historical 5-year average. Price/FVE 0.73.",
                encoding="utf-8",
            )
            parsed = parse_research_report(path, "VALUE")

        self.assertTrue(parsed["valuation_vs_5y_avg_ok"])
        self.assertEqual(parsed["price_to_fair_value"], 0.73)
        self.assertIn("valuation_vs_5y_avg_ok", parsed["research_report_fields"])
        self.assertIn("price_to_fair_value", parsed["research_report_advisory_fields"])

    def test_price_fve_only_does_not_double_count_c9_and_c10(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "VALUE_2026-08-01_Morningstar_AnalystReport.txt"
            path.write_text(
                "Morningstar Equity Research. Fair Value Estimate 3,600.00. Price/FVE 0.73.",
                encoding="utf-8",
            )
            parsed = parse_research_report(path, "VALUE")
        merged = merge_research_with_automated({"ticker": "VALUE", "auto_estimated_fields": []}, parsed)
        market = strong_market()
        market["current_price"] = 2700.0
        score = compute_fundamental_score("VALUE", merged, market, strong_benchmark())

        self.assertIsNone(score["criteria"]["C9"]["points"])
        self.assertIsNotNone(score["criteria"]["C10"]["points"])

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

    def test_ticker_inference_does_not_match_short_ticker_inside_words(self):
        with TemporaryDirectory() as folder:
            report_dir = Path(folder) / "bncd_morningstar"
            report_dir.mkdir()
            index_path = Path(folder) / "research_index.csv"
            write_csv_records(index_path, [], ["ticker", "provider", "report_date", "file_name", "notes"])
            (report_dir / "ABNB_MORNINGSTAR_STOCK_ANALYST_REPORT_05-20-2026.txt").write_text(
                "Fair Value Estimate 180. Economic MoatTM Narrow. Price/FVE 0.92.",
                encoding="utf-8",
            )

            loaded = load_research_report_inputs(report_dir, index_path, known_tickers=["C", "ABNB"])

        self.assertIn("ABNB", loaded)
        self.assertNotIn("C", loaded)

    def test_ticker_inference_strips_exchange_suffixes_when_unambiguous(self):
        self.assertEqual(infer_ticker_from_filename("RHM_2026-05-19_Morningstar.pdf", ["RHM.NE"]), "RHM.NE")
        self.assertEqual(infer_ticker_from_filename("RHM_2026-05-19_Morningstar.pdf", ["RHM.DE"]), "RHM.DE")
        self.assertEqual(infer_ticker_from_filename("CSU_2026-05-19_Morningstar.pdf", ["CSU.TO"]), "CSU.TO")
        self.assertEqual(infer_ticker_from_filename("TOI.V_2026-05-19_Morningstar.pdf", ["TOI.V"]), "TOI.V")

    def test_ticker_inference_returns_empty_for_ambiguous_suffixless_root(self):
        self.assertEqual(infer_ticker_from_filename("RHM_2026-05-19_Morningstar.pdf", ["RHM.NE", "RHM.DE"]), "")

    def test_ticker_inference_exact_match_wins_even_when_root_is_ambiguous(self):
        self.assertEqual(infer_ticker_from_filename("RHM.NE_2026-05-19_Morningstar.pdf", ["RHM.NE", "RHM.DE"]), "RHM.NE")

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

    def test_research_needed_includes_external_candidate_with_existing_data_report(self):
        analyses = {
            "MARKET_SCANNER": {
                "AMAT": {
                    "ticker": "AMAT",
                    "ticker_display": "AMAT",
                    "data_quality": "HIGH",
                    "data_reliability_level": "HIGH",
                    "auto_estimate_dependency": "LOW",
                    "automation_evidence_level": "STRONG",
                    "manual_required_criteria": [],
                    "auto_estimated_fields": [],
                    "add_eligibility_status": "ADD_ALLOWED",
                    "allocation_status": "ELIGIBLE_BUT_NOT_SELECTED",
                    "capital_allocation_score": 88,
                }
            }
        }
        existing = {"AMAT": {"research_report_fields": ["fair_value"], "research_report_sources": ["AMAT.pdf"]}}

        rows = research_needed_rows_from_analysis_rows(analyses, existing)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["ticker"], "AMAT")
        self.assertEqual(rows[0]["priority"], "HIGH")
        self.assertIn("EXTERNAL_CANDIDATE", rows[0]["need_type"])
        self.assertIn("GOV-EXTERNAL-VALIDATION-GATE", rows[0]["reason"])

    def test_research_needed_external_candidate_requires_add_allowed_status(self):
        analyses = {
            "DISCOVERY_IDEAS": {
                "DELL": {
                    "ticker": "DELL",
                    "ticker_display": "DELL",
                    "data_quality": "HIGH",
                    "data_reliability_level": "HIGH",
                    "auto_estimate_dependency": "LOW",
                    "automation_evidence_level": "STRONG",
                    "manual_required_criteria": [],
                    "auto_estimated_fields": [],
                    "add_eligibility_status": "RESEARCH_REPORT_REQUIRED_BEFORE_ADD",
                    "allocation_status": "ELIGIBLE_BUT_NOT_SELECTED",
                    "capital_allocation_score": 88,
                }
            }
        }
        existing = {"DELL": {"research_report_fields": ["fair_value"], "research_report_sources": ["DELL.pdf"]}}

        rows = research_needed_rows_from_analysis_rows(analyses, existing)

        self.assertEqual(rows, [])

    def test_research_needed_external_candidate_requires_eligible_but_not_selected(self):
        analyses = {
            "DISCOVERY_IDEAS": {
                "TER": {
                    "ticker": "TER",
                    "ticker_display": "TER",
                    "data_quality": "HIGH",
                    "data_reliability_level": "HIGH",
                    "auto_estimate_dependency": "LOW",
                    "automation_evidence_level": "STRONG",
                    "manual_required_criteria": [],
                    "auto_estimated_fields": [],
                    "add_eligibility_status": "ADD_ALLOWED",
                    "allocation_status": "NO_NEW_ALLOCATION",
                    "capital_allocation_score": 88,
                }
            }
        }
        existing = {"TER": {"research_report_fields": ["fair_value"], "research_report_sources": ["TER.pdf"]}}

        rows = research_needed_rows_from_analysis_rows(analyses, existing)

        self.assertEqual(rows, [])

    def test_research_needed_external_candidate_does_not_apply_to_core(self):
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
                    "allocation_status": "ELIGIBLE_BUT_NOT_SELECTED",
                    "capital_allocation_score": 88,
                }
            }
        }
        existing = {"GOOGL": {"research_report_fields": ["fair_value"], "research_report_sources": ["GOOGL.pdf"]}}

        rows = research_needed_rows_from_analysis_rows(analyses, existing)

        self.assertEqual(rows, [])

    def test_research_needed_combines_data_and_external_candidate_needs(self):
        analyses = {
            "MARKET_SCANNER": {
                "ADI": {
                    "ticker": "ADI",
                    "ticker_display": "ADI",
                    "data_quality": "LOW",
                    "data_reliability_level": "LOW",
                    "auto_estimate_dependency": "HIGH",
                    "automation_evidence_level": "WEAK",
                    "manual_required_criteria": ["C1: roic_5y_avg", "C4: moat_clear", "C10: fair_value"],
                    "auto_estimated_fields": ["fair_value", "moat_clear", "roic_5y_avg"],
                    "add_eligibility_status": "ADD_ALLOWED_SMALL",
                    "allocation_status": "ELIGIBLE_BUT_NOT_SELECTED",
                    "capital_allocation_score": 88,
                }
            }
        }

        rows = research_needed_rows_from_analysis_rows(analyses, {})

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["ticker"], "ADI")
        self.assertEqual(rows[0]["priority"], "HIGH")
        self.assertIn("DATA", rows[0]["need_type"])
        self.assertIn("EXTERNAL_CANDIDATE", rows[0]["need_type"])

    def test_research_needed_limit_caps_pure_external_candidates_only(self):
        def external_candidate(
            ticker: str,
            *,
            data_quality: str = "HIGH",
            data_reliability_level: str = "HIGH",
            auto_estimate_dependency: str = "LOW",
            automation_evidence_level: str = "STRONG",
            score_evidence_level: str = "AUTOMATED_STRONG",
            manual_required_criteria: list[str] | None = None,
            auto_estimated_fields: list[str] | None = None,
        ) -> dict[str, object]:
            return {
                "ticker": ticker,
                "ticker_display": ticker,
                "data_quality": data_quality,
                "data_reliability_level": data_reliability_level,
                "auto_estimate_dependency": auto_estimate_dependency,
                "automation_evidence_level": automation_evidence_level,
                "score_evidence_level": score_evidence_level,
                "manual_required_criteria": manual_required_criteria or [],
                "auto_estimated_fields": auto_estimated_fields or [],
                "add_eligibility_status": "ADD_ALLOWED",
                "allocation_status": "ELIGIBLE_BUT_NOT_SELECTED",
                "allocation_decision": "ELIGIBLE_BUT_NOT_SELECTED",
                "capital_allocation_score": 88,
            }

        analyses = {
            "WATCHLIST": {
                "WTOP": external_candidate("WTOP"),
            },
            "MARKET_SCANNER": {
                "MMID": external_candidate("MMID"),
                "MIXD": external_candidate(
                    "MIXD",
                    data_quality="LOW",
                    data_reliability_level="LOW",
                    auto_estimate_dependency="HIGH",
                    automation_evidence_level="WEAK",
                    score_evidence_level="ESTIMATE_HEAVY",
                    manual_required_criteria=["C1: roic_5y_avg", "C4: moat_clear", "C10: fair_value"],
                    auto_estimated_fields=["fair_value", "moat_clear", "roic_5y_avg"],
                ),
            },
            "DISCOVERY_IDEAS": {
                "DLOW": external_candidate("DLOW"),
            },
        }

        capped_rows = research_needed_rows_from_analysis_rows(analyses, {}, limit=2)
        uncapped_rows = research_needed_rows_from_analysis_rows(analyses, {})

        pure_external_rows = [row for row in capped_rows if row["need_type"] == "EXTERNAL_CANDIDATE"]
        self.assertEqual(len(pure_external_rows), 2)
        self.assertIn("MIXD", {row["ticker"] for row in capped_rows if row["need_type"] == "DATA+EXTERNAL_CANDIDATE"})
        self.assertEqual(len(uncapped_rows), 4)

        pure_tickers = {row["ticker"] for row in pure_external_rows}
        self.assertEqual(pure_tickers, {"WTOP", "MMID"})
        self.assertNotIn("DLOW", pure_tickers)

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
        self.assertEqual(rows[0]["text_quality_status"], "TEXT_OK")
        self.assertEqual(rows[0]["extraction_method"], "TEXT")

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
