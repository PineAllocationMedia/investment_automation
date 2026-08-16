from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from src.instrument_profile_engine import build_instrument_profile, build_instrument_profiles
from src.report_formatters import build_instrument_profile_section
from src.utils import today_iso


class InstrumentProfileEngineTest(unittest.TestCase):
    def test_stock_with_internal_complete_profile(self) -> None:
        row = build_instrument_profile(
            "MSFT",
            {
                "ticker": "MSFT",
                "long_name": "Microsoft Corporation",
                "business_summary": "Microsoft sells cloud, productivity and AI software to enterprises.",
                "sector_name": "Technology",
                "industry": "Software - Infrastructure",
                "expected_cagr_quality": "HIGH",
                "thesis_status": "INTACT",
                "official_data_sources": ["SEC EDGAR companyfacts"],
            },
            {"ticker": "MSFT", "amount": 100, "reason": "Bloc principal."},
            cache_dir=Path(tempfile.mkdtemp()),
        )

        self.assertEqual(row["instrument_type"], "stock")
        self.assertEqual(row["profile_status"], "COMPLETE")
        self.assertEqual(row["source_confidence"], "HIGH")
        self.assertIn("cloud", row["business_description"])
        self.assertIn("Bloc principal", row["portfolio_role"])

    def test_stock_watch_items_format_decimal_margins_as_percent(self) -> None:
        row = build_instrument_profile(
            "CLS.TO",
            {
                "ticker": "CLS.TO",
                "long_name": "Celestica Inc.",
                "business_summary": "Celestica provides supply chain solutions.",
                "sector_name": "Technology",
                "industry": "Electronic Components",
                "profit_margins": 0.07159,
            },
            {"ticker": "CLS.TO", "amount": 63},
            cache_dir=Path(tempfile.mkdtemp()),
        )

        self.assertIn("marges: 7.2 %", row["key_watch_items"])
        self.assertNotIn("marges: 0.07159", row["key_watch_items"])

    def test_stock_profile_prefers_research_report_description(self) -> None:
        row = build_instrument_profile(
            "CSU.TO",
            {
                "ticker": "CSU.TO",
                "long_name": "Constellation Software Inc.",
                "business_summary": "Yahoo fallback summary.",
                "sector_name": "Technology",
                "industry": "Software",
                "research_report_company_description": "Constellation acquires and manages vertical market software companies globally.",
                "research_report_sector": "Technology",
                "research_report_industry": "Software - Application",
                "research_report_company_description_source": "CSU.TO_2026-05-19_Morningstar_AnalystReport.pdf",
                "research_report_company_description_date": "2026-05-19",
                "research_report_company_description_source_rank": 1,
            },
            {"ticker": "CSU.TO", "amount": 100},
            cache_dir=Path(tempfile.mkdtemp()),
        )

        self.assertIn("vertical market software", row["business_description"])
        self.assertNotIn("Yahoo fallback", row["business_description"])
        self.assertEqual(row["industry"], "Software - Application")
        self.assertIn("CSU.TO_2026-05-19_Morningstar_AnalystReport.pdf", row["source"])

    def test_stock_with_external_complete_profile_when_key_available(self) -> None:
        mock_response = Mock(ok=True)
        mock_response.json.return_value = {
            "Name": "Example Corp",
            "Description": "Example Corp provides mission-critical software.",
            "Sector": "Technology",
            "Industry": "Software",
        }
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"ALPHA_VANTAGE_API_KEY": "demo"}), patch(
            "src.instrument_profile_engine.requests.get", return_value=mock_response
        ):
            row = build_instrument_profile("EXM", {"ticker": "EXM"}, {"ticker": "EXM", "amount": 50}, cache_dir=tmp)

        self.assertEqual(row["profile_status"], "COMPLETE")
        self.assertIn("Example Corp", row["name"])
        self.assertIn("mission-critical", row["business_description"])
        self.assertIn("Alpha Vantage", row["source"])

    def test_etf_with_top_holdings_available(self) -> None:
        row = build_instrument_profile(
            "VFV.TO",
            {
                "ticker": "VFV.TO",
                "quote_type": "ETF",
                "long_name": "Vanguard S&P 500 Index ETF",
                "top_holdings": [{"ticker": "AAPL"}, {"ticker": "MSFT"}],
            },
            {"ticker": "VFV.TO", "amount": 25, "reason": "Filet de sécurité."},
            cache_dir=Path(tempfile.mkdtemp()),
        )

        self.assertEqual(row["instrument_type"], "etf")
        self.assertIn("S&P 500", row["business_description"])
        self.assertIn("AAPL", row["top_holdings"])
        self.assertIn("MSFT", row["top_holdings"])

    def test_etf_without_holdings_stays_partial_or_complete_without_inventing_holdings(self) -> None:
        row = build_instrument_profile(
            "QQQ",
            {"ticker": "QQQ", "quote_type": "ETF", "long_name": "Invesco QQQ Trust"},
            {"ticker": "QQQ", "amount": 25},
            cache_dir=Path(tempfile.mkdtemp()),
        )

        self.assertEqual(row["instrument_type"], "etf")
        self.assertEqual(row["top_holdings"], "")
        self.assertIn(row["profile_status"], {"PARTIAL", "COMPLETE"})

    def test_unknown_ticker_returns_unconfirmed_fallback(self) -> None:
        row = build_instrument_profile("ZZZZ", {"ticker": "ZZZZ"}, {"ticker": "ZZZZ", "amount": 25}, cache_dir=Path(tempfile.mkdtemp()))

        self.assertEqual(row["instrument_type"], "unknown")
        self.assertEqual(row["profile_status"], "UNCONFIRMED")
        self.assertIn("Profil d’activité non confirmé", row["business_description"])

    def test_external_source_unavailable_does_not_crash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"ALPHA_VANTAGE_API_KEY": "demo"}), patch(
            "src.instrument_profile_engine.requests.get", side_effect=RuntimeError("network down")
        ):
            row = build_instrument_profile("EXM", {"ticker": "EXM"}, {"ticker": "EXM", "amount": 50}, cache_dir=tmp)

        self.assertEqual(row["profile_status"], "UNCONFIRMED")
        self.assertIn("Profil d’activité non confirmé", row["business_description"])

    def test_absent_api_key_does_not_call_external_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {}, clear=True), patch(
            "src.instrument_profile_engine.requests.get"
        ) as mocked_get:
            row = build_instrument_profile("EXM", {"ticker": "EXM"}, {"ticker": "EXM", "amount": 50}, cache_dir=tmp)

        mocked_get.assert_not_called()
        self.assertEqual(row["profile_status"], "UNCONFIRMED")

    def test_existing_cache_fills_missing_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache_path = Path(tmp) / "EXM.json"
            cache_path.write_text(
                json.dumps(
                    {
                        "ticker": "EXM",
                        "name": "Cached Example",
                        "instrument_type": "stock",
                        "business_description": "Cached company profile.",
                        "sector_or_category": "Technology",
                        "revenue_model_or_activity": "Cached revenue model.",
                        "portfolio_role": "Cached role.",
                        "key_watch_items": "Cached watch items.",
                        "source": "cache local",
                        "source_confidence": "MEDIUM",
                        "last_updated": today_iso(),
                    }
                ),
                encoding="utf-8",
            )

            row = build_instrument_profile("EXM", {"ticker": "EXM"}, {"ticker": "EXM", "amount": 50}, cache_dir=tmp)

        self.assertEqual(row["name"], "Cached Example")
        self.assertEqual(row["profile_status"], "COMPLETE")
        self.assertIn("cache local", row["source"])

    def test_conflicting_cached_sector_reduces_confidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache_path = Path(tmp) / "MSFT.json"
            cache_path.write_text(
                json.dumps(
                    {
                        "ticker": "MSFT",
                        "sector_or_category": "Energy",
                        "source": "cache local",
                        "source_confidence": "HIGH",
                        "last_updated": today_iso(),
                    }
                ),
                encoding="utf-8",
            )

            row = build_instrument_profile(
                "MSFT",
                {
                    "ticker": "MSFT",
                    "long_name": "Microsoft Corporation",
                    "business_summary": "Microsoft sells software.",
                    "sector_name": "Technology",
                    "industry": "Software",
                },
                {"ticker": "MSFT", "amount": 50},
                cache_dir=tmp,
            )

        self.assertEqual(row["source_confidence"], "MEDIUM")
        self.assertIn("valider", row["source"])

    def test_build_profiles_does_not_mutate_allocations(self) -> None:
        allocations = [{"ticker": "MSFT", "amount": 100, "reason": "Test"}]
        before = [dict(row) for row in allocations]

        rows = build_instrument_profiles(
            allocations,
            {"MSFT": {"ticker": "MSFT", "business_summary": "Microsoft sells software."}},
            cache_dir=Path(tempfile.mkdtemp()),
        )

        self.assertEqual(allocations, before)
        self.assertEqual(rows[0]["ticker"], "MSFT")

    def test_build_profiles_accepts_allocation_engine_schema(self) -> None:
        rows = build_instrument_profiles(
            [{"destination": "APH", "montant": 375, "raison": "Bloc principal."}],
            {
                "APH": {
                    "ticker": "APH",
                    "company_name_found": "Amphenol Corporation",
                    "business_summary": "Amphenol designs and manufactures connectors and interconnect systems.",
                    "sector_name": "Technology",
                    "industry": "Electronic Components",
                }
            },
            cache_dir=Path(tempfile.mkdtemp()),
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["ticker"], "APH")
        self.assertIn("connectors", rows[0]["business_description"])

    def test_formatter_builds_what_you_buy_section(self) -> None:
        markdown = build_instrument_profile_section(
            [
                {
                    "ticker": "MSFT",
                    "name": "Microsoft Corporation",
                    "instrument_type": "stock",
                    "business_description": "Microsoft sells software.",
                    "sector_or_category": "Technology",
                    "industry": "Software",
                    "revenue_model_or_activity": "Cloud and productivity software.",
                    "portfolio_role": "CAGR qualitatif HIGH.",
                    "key_watch_items": "marges; croissance",
                    "source": "résumé d’activité Yahoo/yfinance",
                    "source_confidence": "HIGH",
                    "profile_status": "COMPLETE",
                }
            ],
            compact=True,
        )

        self.assertIn("## Ce que vous achetez", markdown)
        self.assertIn("Microsoft Corporation (MSFT)", markdown)
        self.assertIn("informative seulement", markdown.lower())


if __name__ == "__main__":
    unittest.main()
