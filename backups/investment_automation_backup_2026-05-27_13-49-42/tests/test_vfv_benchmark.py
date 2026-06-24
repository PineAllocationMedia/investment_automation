import unittest

from main import apply_etf_asset_role, apply_vfv_benchmark_role, enrich_exposure_map, enrich_sector_map
from src.asset_type_engine import etf_risk_exposure, etf_risk_sector
from src.ticker_resolver import apply_ticker_attention_flags


class VfvBenchmarkTest(unittest.TestCase):
    def test_vfv_is_marked_as_etf_benchmark_not_company(self):
        analysis = {"ticker": "VFV.TO", "long_name": "Vanguard S&P 500 Index ETF"}
        apply_vfv_benchmark_role(analysis)
        apply_ticker_attention_flags(analysis, {})

        self.assertTrue(analysis["benchmark_role"])
        self.assertEqual(analysis["asset_type"], "ETF_S_AND_P_500")
        self.assertEqual(analysis["asset_role"], "BENCHMARK_FALLBACK")
        self.assertEqual(analysis["score_total"], "BENCHMARK")
        self.assertEqual(analysis["company_name_found"], "ETF S&P 500 coté au Canada")
        self.assertFalse(analysis["ticker_needs_attention"])

    def test_non_vfv_etf_is_not_scored_like_a_company(self):
        analysis = {"ticker": "QQC.TO", "long_name": "Invesco NASDAQ 100 Index ETF CAD Units"}
        apply_etf_asset_role(analysis)
        apply_ticker_attention_flags(analysis, {})

        self.assertFalse(analysis["benchmark_role"])
        self.assertEqual(analysis["asset_type"], "ETF_NASDAQ_100")
        self.assertEqual(analysis["score_total"], "ETF")
        self.assertEqual(analysis["conviction_score"], "ETF")
        self.assertEqual(analysis["add_eligibility_status"], "ETF_HOLD_ONLY")
        self.assertEqual(analysis["ticker_validation_status"], "ETF_OR_FUND")
        self.assertEqual(analysis["manual_required_criteria"], [])
        self.assertFalse(analysis["ticker_needs_attention"])

    def test_etf_risk_classification_identifies_current_etfs(self):
        qqc_market = {"long_name": "Invesco NASDAQ 100 Index ETF CAD Units", "quote_type": "ETF", "currency": "CAD"}
        xus_market = {"long_name": "iShares Core S&P 500 Index ETF", "quote_type": "ETF", "currency": "CAD"}
        fbtc_market = {"long_name": "Fidelity Advantage Bitcoin ETF", "quote_type": None, "currency": None}

        self.assertEqual(etf_risk_sector("QQC.TO", qqc_market), "Nasdaq 100 ETF")
        self.assertEqual(etf_risk_exposure("QQC.TO", qqc_market)["region"], "United States")
        self.assertEqual(etf_risk_sector("XUS.TO", xus_market), "S&P 500 ETF")
        self.assertEqual(etf_risk_exposure("XUS.TO", xus_market)["currency"], "CAD")
        self.assertEqual(etf_risk_sector("FBTC.TO", fbtc_market), "Bitcoin / Crypto ETF")
        self.assertEqual(etf_risk_exposure("FBTC.TO", fbtc_market)["currency"], "CAD")
        self.assertIn("bitcoin", etf_risk_exposure("FBTC.TO", fbtc_market)["factor_exposure"])

    def test_enrichment_classifies_etfs_for_portfolio_risk(self):
        market_data = {
            "QQC.TO": {"long_name": "Invesco NASDAQ 100 Index ETF CAD Units", "quote_type": "ETF", "currency": "CAD"},
            "XUS.TO": {"long_name": "iShares Core S&P 500 Index ETF", "quote_type": "ETF", "currency": "CAD"},
            "FBTC.TO": {"long_name": None, "quote_type": None, "currency": None},
        }

        sectors = enrich_sector_map({}, market_data, ["QQC.TO", "XUS.TO", "FBTC.TO"])
        exposures = enrich_exposure_map({}, market_data, ["QQC.TO", "XUS.TO", "FBTC.TO"])

        self.assertEqual(sectors["QQC.TO"], "Nasdaq 100 ETF")
        self.assertEqual(sectors["XUS.TO"], "S&P 500 ETF")
        self.assertEqual(sectors["FBTC.TO"], "Bitcoin / Crypto ETF")
        self.assertEqual(exposures["QQC.TO"]["region"], "United States")
        self.assertIn("Nasdaq100", exposures["QQC.TO"]["factor_exposure"])
        self.assertEqual(exposures["XUS.TO"]["region"], "United States")
        self.assertIn("S&P500", exposures["XUS.TO"]["factor_exposure"])
        self.assertEqual(exposures["FBTC.TO"]["region"], "Global")
        self.assertIn("crypto", exposures["FBTC.TO"]["factor_exposure"])


if __name__ == "__main__":
    unittest.main()
