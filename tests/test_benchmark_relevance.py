import unittest

from src.benchmark_relevance_engine import compute_benchmark_relevance, enrich_benchmark_map, infer_benchmark_from_context
from src.scoring import compute_fundamental_score
from tests.helpers import strong_benchmark, strong_manual, strong_market


class BenchmarkRelevanceTest(unittest.TestCase):
    def test_auto_enriches_known_unmapped_tickers(self):
        benchmark_map, sources = enrich_benchmark_map({"MSFT": "IGV"}, ["MSFT", "AAPL", "META", "UNKNOWN"])

        self.assertEqual(benchmark_map["MSFT"], "IGV")
        self.assertEqual(sources["MSFT"], "CONFIGURED")
        self.assertEqual(benchmark_map["AAPL"], "XLK")
        self.assertEqual(sources["AAPL"], "AUTO_INFERRED")
        self.assertEqual(benchmark_map["META"], "XLC")
        self.assertEqual(sources["META"], "AUTO_INFERRED")
        self.assertNotIn("UNKNOWN", benchmark_map)
        self.assertEqual(sources["UNKNOWN"], "BROAD_MARKET_FALLBACK")

    def test_auto_enriches_more_precise_market_universe_benchmarks(self):
        benchmark_map, sources = enrich_benchmark_map({}, ["BLK", "NEE", "WDC", "CCO.TO", "PGR"])

        self.assertEqual(benchmark_map["BLK"], "KCE")
        self.assertEqual(benchmark_map["NEE"], "XLU")
        self.assertEqual(benchmark_map["WDC"], "XLK")
        self.assertEqual(benchmark_map["CCO.TO"], "URA")
        self.assertEqual(benchmark_map["PGR"], "KIE")
        self.assertEqual(sources["BLK"], "AUTO_INFERRED")

    def test_vfv_is_low_relevance_sector_proxy(self):
        result = compute_benchmark_relevance(
            ticker="AAPL",
            benchmark_ticker="VFV.TO",
            sector="Technology",
            exposure={"factor_exposure": ["technology"]},
            benchmark_source="BROAD_MARKET_FALLBACK",
        )

        self.assertEqual(result["benchmark_relevance_level"], "LOW")
        self.assertLess(result["benchmark_relevance_score"], 0.5)

    def test_specialized_etf_can_be_high_relevance(self):
        result = compute_benchmark_relevance(
            ticker="AVGO",
            benchmark_ticker="SOXX",
            sector="Semiconductors",
            exposure={"factor_exposure": ["semiconductors", "AI"]},
            benchmark_source="CONFIGURED",
        )

        self.assertEqual(result["benchmark_relevance_level"], "HIGH")

    def test_new_specialized_benchmarks_have_useful_relevance(self):
        result = compute_benchmark_relevance(
            ticker="NEE",
            benchmark_ticker="XLU",
            sector="Utilities",
            exposure={"factor_exposure": ["utility", "power"]},
            benchmark_source="AUTO_INFERRED",
        )

        self.assertEqual(result["benchmark_relevance_level"], "HIGH")

    def test_context_inference_finds_benchmark_for_new_communication_platform(self):
        benchmark, reason = infer_benchmark_from_context(
            "NEWCO",
            sector="Communication Services",
            exposure={"factor_exposure": ["advertising", "platform"]},
            market={"industry": "Internet Content & Information"},
        )

        self.assertEqual(benchmark, "XLC")
        self.assertIn("contexte", reason)

    def test_context_inferred_benchmark_gets_high_relevance_when_terms_match(self):
        result = compute_benchmark_relevance(
            ticker="NEWCO",
            benchmark_ticker="XLC",
            sector="Communication Services",
            exposure={"factor_exposure": ["advertising", "platform"]},
            market={"industry": "Internet Content & Information"},
            benchmark_source="AUTO_CONTEXT_INFERRED",
        )

        self.assertEqual(result["benchmark_relevance_level"], "HIGH")

    def test_low_relevance_benchmark_does_not_fail_criterion_7_harshly(self):
        benchmark = strong_benchmark()
        benchmark.update(
            {
                "benchmark_usable_cagr": -0.02,
                "benchmark_5y_cagr": -0.02,
                "benchmark_above_sma_200": False,
                "benchmark_relevance_level": "LOW",
                "benchmark_relevance_score": 0.25,
            }
        )

        score = compute_fundamental_score("AAPL", strong_manual(), strong_market(), benchmark)

        self.assertEqual(score["criteria"]["C7"]["points"], 0.25)
        self.assertIn("pertinence benchmark=LOW", score["criteria"]["C7"]["detail"])


if __name__ == "__main__":
    unittest.main()
