import unittest

from src.company_dossier_engine import build_company_dossier, build_company_dossier_rows


class CompanyDossierEngineTest(unittest.TestCase):
    def test_dossier_combines_local_report_yfinance_sec_and_news(self):
        analysis = {
            "ticker": "MSFT",
            "company_name_found": "Microsoft Corporation",
            "sector_name": "Technology",
            "industry": "Software - Infrastructure",
            "business_summary": "Microsoft develops cloud, software, artificial intelligence and productivity products for enterprise customers.",
            "official_data_sources": ["SEC EDGAR companyfacts"],
            "news_context_sources": ["Reuters"],
            "market_growth_thesis_sources": ["public industry sources"],
            "data_source_notes": ["yfinance info"],
            "management_quality_good": True,
            "balance_sheet_strong": True,
            "free_cash_flow_margin": 0.31,
            "shareholder_discipline_status": "DISCIPLINED",
            "market_growth_thesis_status": "STRUCTURAL_TAILWIND",
            "market_growth_thesis_score": 82,
            "capital_allocation_score": 91,
            "conviction_score": 88,
            "expected_cagr_quality": "VERY_HIGH",
            "thesis_status": "INTACT",
            "opportunity_cost_status": "CLEARLY_BETTER_THAN_VFV",
        }
        qualitative = {
            "ticker": "MSFT",
            "source_status": "LOCAL_RESEARCH_REPORT",
            "sources": "MSFT_2026_report.pdf",
            "competitive_advantage_themes": "coûts de changement, écosystème",
            "crisis_protection_themes": "revenus récurrents, bilan solide",
            "pricing_power_themes": "pouvoir de prix",
        }

        row = build_company_dossier(analysis, qualitative, target_status="RECOMMANDÉ", allocation_amount=250)

        self.assertEqual(row["source_quality"], "FULL_SOURCE_BACKED")
        self.assertIn("rapports locaux", row["sources_used"])
        self.assertIn("SEC EDGAR", row["sources_used"])
        self.assertIn("coûts de changement", row["competitive_advantage"])
        self.assertIn("pouvoir de prix", row["pricing_power"])
        self.assertIn("score allocation 91.0/100", row["portfolio_fit"])

    def test_dossier_uses_automated_sources_without_inventing_local_report(self):
        analysis = {
            "ticker": "GOOGL",
            "company_name_found": "Alphabet Inc.",
            "sector_name": "Communication Services",
            "industry": "Internet Content & Information",
            "business_summary": "Alphabet offers search, advertising, cloud, data and artificial intelligence products.",
            "data_source_notes": ["yfinance info"],
            "moat_clear": True,
        }

        row = build_company_dossier(analysis)

        self.assertEqual(row["source_quality"], "BASIC_AUTOMATED")
        self.assertIn("rapport local", row["missing_sources"])
        self.assertIn("recherche", row["business_model"])
        self.assertIn("indices de moat", row["competitive_advantage"])

    def test_full_source_backed_cannot_hide_ftv_like_auto_estimated_allocation_fields(self):
        analysis = {
            "ticker": "FTV",
            "company_name_found": "Fortive Corporation",
            "business_summary": "Fortive provides essential industrial technology and software.",
            "official_data_sources": ["SEC EDGAR companyfacts"],
            "data_source_notes": ["yfinance info"],
            "research_report_fields": ["fair_value", "moat_clear"],
            "auto_estimated_fields": [
                "eps_growth_estimated_3_5y",
                "roic_5y_avg",
                "peg_manual",
                "valuation_vs_5y_avg_ok",
                "balance_sheet_strong",
                "margin_or_profitability_under_pressure",
            ],
        }
        qualitative = {
            "source_status": "LOCAL_RESEARCH_REPORT",
            "sources": "FTV_MORNINGSTAR_DATA_TEAR_SHEET_08-22-2026.pdf",
        }

        row = build_company_dossier(analysis, qualitative, target_status="RECOMMANDÉ", allocation_amount=56.25)

        self.assertEqual(row["source_quality"], "PARTIAL_SOURCE_BACKED")
        self.assertIn("champs d'allocation encore estimés automatiquement", row["missing_sources"])
        self.assertIn("eps_growth_estimated_3_5y", row["missing_sources"])
        self.assertIn("roic_5y_avg", row["missing_sources"])

    def test_rows_include_recommended_and_eligible_core_positions_only(self):
        rows = build_company_dossier_rows(
            {
                "MSFT": {"ticker": "MSFT", "add_eligibility_status": "ADD_ALLOWED", "business_summary": "Cloud software."},
                "AAPL": {"ticker": "AAPL", "add_eligibility_status": "DO_NOT_ADD", "business_summary": "Consumer devices."},
                "META": {"ticker": "META", "business_summary": "Advertising platform."},
            },
            [{"ticker": "META", "amount": 100}],
            [],
        )

        tickers = [row["ticker"] for row in rows]
        self.assertIn("MSFT", tickers)
        self.assertIn("META", tickers)
        self.assertNotIn("AAPL", tickers)
        self.assertEqual(rows[0]["target_status"], "RECOMMANDÉ")


if __name__ == "__main__":
    unittest.main()
