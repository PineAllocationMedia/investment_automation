import unittest

from src.auto_fundamentals import (
    build_automated_manual_inputs,
    compute_forward_eps_growth,
    merge_automated_with_manual_overrides,
)


class AutoFundamentalsTest(unittest.TestCase):
    def test_builds_automated_manual_inputs_from_market_data(self):
        market = {
            "current_price": 100,
            "forward_pe": 25,
            "peg": 1.8,
            "profit_margins": 0.22,
            "operating_margins": 0.28,
            "return_on_equity": 0.31,
            "revenue_growth": 0.12,
            "earnings_growth": 0.16,
            "stock_cagr_5y": 0.15,
            "market_cap": 250_000_000_000,
            "debt_to_equity": 35,
            "sma_200": 90,
        }
        benchmark = {"benchmark_10y_cagr": 0.09}

        manual = build_automated_manual_inputs("MSFT", market, benchmark)

        self.assertEqual(manual["ticker"], "MSFT")
        self.assertGreaterEqual(manual["roic_5y_avg"], 15)
        self.assertTrue(manual["moat_clear"])
        self.assertTrue(manual["valuation_vs_5y_avg_ok"])
        self.assertIn("fair_value", manual["auto_estimated_fields"])

    def test_forward_eps_growth_uses_analyst_count_confidence(self):
        high = compute_forward_eps_growth(6.0, 5.0, 12)
        low = compute_forward_eps_growth(6.0, 5.0, 2)
        none = compute_forward_eps_growth(6.0, 5.0, 0)

        self.assertAlmostEqual(high["forward_eps_growth_direct"], 0.20)
        self.assertEqual(high["forward_eps_growth_confidence"], "HIGH")
        self.assertEqual(low["forward_eps_growth_confidence"], "LOW")
        self.assertIsNone(none["forward_eps_growth_direct"])
        self.assertEqual(none["forward_eps_growth_confidence"], "NONE")

    def test_forward_eps_growth_blends_with_existing_proxy_without_replacing_long_term_anchor(self):
        manual = build_automated_manual_inputs(
            "MSFT",
            {
                "current_price": 100,
                "forward_pe": 25,
                "trailing_pe": 28,
                "forward_eps": 6.0,
                "trailing_eps": 5.0,
                "number_of_analyst_opinions": 12,
                "profit_margins": 0.22,
                "return_on_assets": 0.15,
                "revenue_growth": 0.10,
                "earnings_growth": 0.12,
                "stock_cagr_5y": 0.12,
                "market_cap": 2_000_000_000_000,
                "sma_200": 90,
            },
            {"benchmark_10y_cagr": 0.08},
        )

        self.assertEqual(manual["forward_eps_growth_confidence"], "HIGH")
        self.assertEqual(manual["data_source_forward"], "yfinance_forward_eps")
        self.assertGreater(manual["eps_growth_estimated_3_5y"], 10)
        self.assertLess(manual["eps_growth_estimated_3_5y"], 20)

    def test_etf_is_excluded_from_forward_eps_growth_logic(self):
        manual = build_automated_manual_inputs(
            "VFV.TO",
            {
                "quote_type": "ETF",
                "forward_eps": 6.0,
                "trailing_eps": 5.0,
                "number_of_analyst_opinions": 12,
                "stock_cagr_5y": 0.10,
                "current_price": 100,
                "sma_200": 95,
            },
            {"benchmark_10y_cagr": 0.08},
        )

        self.assertEqual(manual["forward_eps_growth_confidence"], "NONE")
        self.assertEqual(manual["data_source_forward"], "proxy")

    def test_negative_quarterly_growth_flags_early_deterioration_without_margin_pressure(self):
        manual = build_automated_manual_inputs(
            "MSFT",
            {
                "current_price": 100,
                "forward_pe": 25,
                "profit_margins": 0.22,
                "return_on_assets": 0.15,
                "revenue_growth": 0.10,
                "earnings_growth": 0.12,
                "earnings_quarterly_growth": -0.05,
                "stock_cagr_5y": 0.12,
                "market_cap": 2_000_000_000_000,
                "sma_200": 90,
            },
            {"benchmark_10y_cagr": 0.08},
        )

        self.assertTrue(manual["early_deterioration_signal"])
        self.assertFalse(manual["margin_or_profitability_under_pressure"])

    def test_manual_override_wins_over_automatic_estimate(self):
        automated = build_automated_manual_inputs(
            "MSFT",
            {
                "current_price": 100,
                "forward_pe": 25,
                "profit_margins": 0.20,
                "return_on_equity": 0.30,
                "stock_cagr_5y": 0.12,
                "market_cap": 200_000_000_000,
                "sma_200": 90,
            },
            {"benchmark_10y_cagr": 0.08},
        )
        manual_override = {
            "ticker": "MSFT",
            "moat_clear": False,
            "manual_override_fields": ["moat_clear"],
        }

        merged = merge_automated_with_manual_overrides(automated, manual_override)

        self.assertFalse(merged["moat_clear"])
        self.assertIn("moat_clear", merged["manual_override_fields"])
        self.assertNotIn("moat_clear", merged["auto_estimated_fields"])

    def test_manual_override_removes_proxy_correction_trace_for_confirmed_field(self):
        automated = build_automated_manual_inputs(
            "MSFT",
            {
                "current_price": 100,
                "forward_pe": 25,
                "profit_margins": 0.20,
                "return_on_assets": 0.15,
                "market_cap": 200_000_000_000,
                "sma_200": 90,
            },
            {"benchmark_10y_cagr": 0.08},
            proxy_corrections={
                "active_corrections": {
                    "roic_5y_avg": {
                        "factor": 1.10,
                        "confidence": "HIGH",
                        "sample_count": 8,
                    }
                }
            },
        )
        manual_override = {
            "ticker": "MSFT",
            "roic_5y_avg": 22,
            "manual_override_fields": ["roic_5y_avg"],
        }

        merged = merge_automated_with_manual_overrides(automated, manual_override)

        self.assertEqual(merged["roic_5y_avg"], 22)
        self.assertNotIn("roic_5y_avg", merged["proxy_correction_fields"])
        self.assertEqual(merged["proxy_correction_status"], "NONE")

    def test_sec_official_fields_support_related_automatic_proxies(self):
        manual = build_automated_manual_inputs(
            "MSFT",
            {
                "current_price": 100,
                "forward_pe": 25,
                "profit_margins": 0.22,
                "return_on_assets": 0.18,
                "revenue_growth": 0.12,
                "earnings_growth": 0.16,
                "market_cap": 2_000_000_000_000,
                "debt_to_equity": 35,
                "official_data_sources": ["SEC EDGAR companyfacts"],
                "official_fundamental_fields": ["return_on_assets", "revenue_growth", "total_debt"],
                "official_confirmed_fields": ["profit_margins"],
                "official_data_conflicts": ["earnings_growth: yfinance=0.16, SEC=0.10, ecart=38%"],
            },
            {"benchmark_10y_cagr": 0.08},
        )

        self.assertIn("roic_5y_avg", manual["official_supported_manual_fields"])
        self.assertIn("eps_growth_5y", manual["official_supported_manual_fields"])
        self.assertIn("balance_sheet_strong", manual["official_supported_manual_fields"])
        self.assertIn("net_margin_stable_or_expanding", manual["official_confirmed_manual_fields"])
        self.assertEqual(manual["official_conflict_count"], 1)

    def test_recalibrated_roic_uses_roa_anchor_when_available(self):
        manual = build_automated_manual_inputs(
            "GOOGL",
            {
                "current_price": 100,
                "forward_pe": 25,
                "profit_margins": 0.38,
                "return_on_equity": 0.39,
                "return_on_assets": 0.146,
                "revenue_growth": 0.22,
                "earnings_growth": 0.82,
                "market_cap": 2_000_000_000_000,
                "sma_200": 90,
            },
            {"benchmark_10y_cagr": 0.08},
        )

        self.assertLess(manual["roic_5y_avg"], 35)
        self.assertGreater(manual["roic_5y_avg"], 20)

    def test_active_proxy_correction_is_visible_and_bounded_to_auto_field(self):
        base_market = {
            "current_price": 100,
            "forward_pe": 25,
            "profit_margins": 0.38,
            "return_on_assets": 0.146,
            "revenue_growth": 0.22,
            "earnings_growth": 0.40,
            "market_cap": 2_000_000_000_000,
            "sma_200": 90,
        }
        baseline = build_automated_manual_inputs("GOOGL", base_market, {"benchmark_10y_cagr": 0.08})
        corrected = build_automated_manual_inputs(
            "GOOGL",
            base_market,
            {"benchmark_10y_cagr": 0.08},
            proxy_corrections={
                "active_corrections": {
                    "roic_5y_avg": {
                        "factor": 1.10,
                        "confidence": "HIGH",
                        "sample_count": 8,
                        "last_updated": "2026-06-25",
                    }
                }
            },
        )

        self.assertAlmostEqual(corrected["roic_5y_avg"], round(baseline["roic_5y_avg"] * 1.10, 3))
        self.assertEqual(corrected["proxy_correction_status"], "ACTIVE")
        self.assertIn("roic_5y_avg", corrected["proxy_correction_fields"])
        self.assertTrue(any("correction proxy active" in note for note in corrected["auto_source_notes"]))

    def test_recalibrated_future_growth_caps_recent_earnings_spike(self):
        manual = build_automated_manual_inputs(
            "GOOGL",
            {
                "current_price": 100,
                "forward_pe": 25,
                "profit_margins": 0.38,
                "return_on_assets": 0.146,
                "revenue_growth": 0.22,
                "earnings_growth": 0.82,
                "sector_name": "Communication Services",
                "market_cap": 2_000_000_000_000,
                "sma_200": 90,
            },
            {"benchmark_10y_cagr": 0.08},
        )

        self.assertLessEqual(manual["eps_growth_estimated_3_5y"], 20)

    def test_recalibrated_fair_value_is_not_unbounded_by_growth_proxy(self):
        manual = build_automated_manual_inputs(
            "NVDA",
            {
                "current_price": 200,
                "forward_pe": 17.5,
                "peg": 0.63,
                "profit_margins": 0.55,
                "return_on_assets": 0.51,
                "revenue_growth": 0.73,
                "earnings_growth": 0.95,
                "sector_name": "Technology",
                "industry": "Semiconductors",
                "market_cap": 5_000_000_000_000,
                "sma_200": 150,
            },
            {"benchmark_10y_cagr": 0.10},
        )

        self.assertLessEqual(manual["fair_value"], 270)

    def test_recalibrated_peg_neutralizes_extreme_yfinance_value_for_quality_industrial(self):
        manual = build_automated_manual_inputs(
            "WSP.TO",
            {
                "current_price": 229.59,
                "forward_pe": 17.43,
                "peg": 16.44,
                "profit_margins": 0.0527,
                "operating_margins": 0.103,
                "return_on_assets": 0.0538,
                "return_on_equity": 0.1065,
                "revenue_growth": 0.041,
                "earnings_growth": 0.528,
                "stock_cagr_5y": 0.122,
                "market_cap": 30_000_000_000,
                "debt_to_equity": 50,
                "sector_name": "Industrials",
                "industry": "Engineering & Construction",
                "sma_200": 200,
            },
            {"benchmark_10y_cagr": 0.08},
        )

        self.assertLess(manual["peg_manual"], 3)
        self.assertGreaterEqual(manual["fair_value"], 290)
        self.assertTrue(manual["valuation_vs_5y_avg_ok"])
        self.assertTrue(manual["moat_clear"])
        self.assertTrue(manual["management_quality_good"])

    def test_asset_light_network_can_have_strong_balance_sheet_despite_high_debt_to_equity(self):
        manual = build_automated_manual_inputs(
            "MA",
            {
                "current_price": 500,
                "forward_pe": 22,
                "peg": 1.6,
                "profit_margins": 0.45,
                "operating_margins": 0.60,
                "return_on_assets": 0.25,
                "return_on_equity": 2.3,
                "revenue_growth": 0.15,
                "earnings_growth": 0.20,
                "stock_cagr_5y": 0.05,
                "market_cap": 440_000_000_000,
                "total_debt": 19_000_000_000,
                "debt_to_equity": 282,
                "sma_200": 450,
            },
            {"benchmark_10y_cagr": 0.08},
        )

        self.assertTrue(manual["balance_sheet_strong"])

    def test_low_margin_scale_retailer_can_have_stable_margins_and_moat(self):
        manual = build_automated_manual_inputs(
            "COST",
            {
                "current_price": 1000,
                "forward_pe": 45,
                "peg": 5.1,
                "profit_margins": 0.029,
                "operating_margins": 0.036,
                "return_on_assets": 0.087,
                "return_on_equity": 0.296,
                "revenue_growth": 0.215,
                "earnings_growth": 0.455,
                "stock_cagr_5y": 0.22,
                "market_cap": 450_000_000_000,
                "sector_name": "Consumer Defensive",
                "industry": "Discount Stores",
                "debt_to_equity": 60,
                "sma_200": 900,
            },
            {"benchmark_10y_cagr": 0.08},
        )

        self.assertTrue(manual["net_margin_stable_or_expanding"])
        self.assertTrue(manual["moat_clear"])
        self.assertTrue(manual["management_quality_good"])
        self.assertFalse(manual["margin_or_profitability_under_pressure"])

    def test_high_growth_pharma_uses_conservative_historical_growth_and_balance_sheet(self):
        manual = build_automated_manual_inputs(
            "LLY",
            {
                "current_price": 988.87,
                "forward_pe": 22.596,
                "trailing_pe": 35.104,
                "peg": 1.39,
                "profit_margins": 0.3499,
                "operating_margins": 0.4939,
                "return_on_assets": 0.2074,
                "return_on_equity": 1.0746,
                "revenue_growth": 0.555,
                "earnings_growth": 1.699,
                "stock_cagr_5y": 0.4025,
                "market_cap": 881_000_000_000,
                "debt_to_equity": 139,
                "total_debt": 43_370_000_000,
                "total_cash": 5_282_000_000,
                "sector_name": "Healthcare",
                "industry": "Drug Manufacturers - General",
                "sma_200": 900,
            },
            {"benchmark_10y_cagr": 0.08},
        )

        self.assertLess(manual["eps_growth_5y"], 40)
        self.assertLess(manual["roic_5y_avg"], 35)
        self.assertLess(manual["fair_value"], 1100)
        self.assertTrue(manual["balance_sheet_strong"])

    def test_asset_manager_with_negative_recent_earnings_uses_more_conservative_growth(self):
        manual = build_automated_manual_inputs(
            "BAM",
            {
                "current_price": 48.43,
                "forward_pe": 22.12,
                "trailing_pe": 31.45,
                "peg": 1.36,
                "profit_margins": 0.5159,
                "operating_margins": 0.6793,
                "return_on_assets": 0.1215,
                "return_on_equity": 0.2231,
                "revenue_growth": 0.311,
                "earnings_growth": -0.207,
                "stock_cagr_3y": 0.1313,
                "market_cap": 79_000_000_000,
                "debt_to_equity": 28.5,
                "sector_name": "Financial Services",
                "industry": "Asset Management",
                "sma_200": 50,
            },
            {"benchmark_10y_cagr": 0.08},
        )

        self.assertLessEqual(manual["eps_growth_estimated_3_5y"], 16)
        self.assertGreaterEqual(manual["peg_manual"], 1.6)


if __name__ == "__main__":
    unittest.main()
