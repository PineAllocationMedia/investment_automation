import tempfile
import unittest
from pathlib import Path

from tests.helpers import full_strong_analysis
from main import expand_exclusions_with_alias_inputs
from src.discovery_engine import (
    actionable_discovery_rows,
    build_discovery_maintenance_rows,
    build_discovery_idea_rows,
    classify_discovery_idea,
    classify_discovery_maintenance,
    load_auto_discovery_universe,
    load_discovery_universe,
)


class DiscoveryEngineTest(unittest.TestCase):
    def test_strict_external_idea_can_be_suggested_for_market_universe_review(self):
        analysis = full_strong_analysis("WM")
        analysis["market_cap"] = 80_000_000_000
        analysis["profit_margins"] = 0.15
        analysis["data_quality"] = "HIGH"
        analysis["data_reliability_level"] = "HIGH"
        analysis["cycle_bubble_risk_level"] = "LOW"

        result = classify_discovery_idea(analysis)

        self.assertEqual(result["discovery_status"], "ADD_TO_MARKET_UNIVERSE_REVIEW")
        self.assertIn("market_universe", result["discovery_suggested_action"])

    def test_expensive_quality_is_not_suggested_as_priority_addition(self):
        analysis = full_strong_analysis("PANW")
        analysis["market_cap"] = 120_000_000_000
        analysis["profit_margins"] = 0.20
        analysis["data_quality"] = "HIGH"
        analysis["peg"] = 3.5
        analysis["quality_but_too_expensive"] = True

        result = classify_discovery_idea(analysis)

        self.assertEqual(result["discovery_status"], "TOO_EXPENSIVE")

    def test_discovery_universe_excludes_existing_portfolio_or_market_names(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "market_scanner.yaml"
            path.write_text("discovery_universe:\n  - WM\n  - MSFT\n", encoding="utf-8")

            universe = load_discovery_universe(path, {"MSFT"})

        self.assertIn("WM", universe)
        self.assertNotIn("MSFT", universe)

    def test_actionable_rows_only_keep_strict_suggestions(self):
        suggested = {"ticker": "WM", "discovery_status": "ADD_TO_MARKET_UNIVERSE_REVIEW"}
        waiting = {"ticker": "MSI", "discovery_status": "STRONG_BUT_WAIT"}

        rows = actionable_discovery_rows([suggested, waiting])

        self.assertEqual(rows, [suggested])

    def test_report_rows_can_hide_non_interesting_rejections(self):
        strong = full_strong_analysis("WM")
        strong.update(classify_discovery_idea(strong))
        weak = full_strong_analysis("LOW")
        weak["score_total"] = 5
        weak["conviction_score"] = 40
        weak.update(classify_discovery_idea(weak))

        rows = build_discovery_idea_rows(
            {"WM": strong, "LOW": weak},
            {"WM": {"company_name": "Waste Management Inc."}, "LOW": {"company_name": "Weak Co."}},
            report_only=True,
        )

        self.assertTrue(all(row["discovery_status"] != "NOT_ALIGNED_NOW" for row in rows))

    def test_auto_discovery_uses_cache_and_excludes_existing_tickers(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "market_scanner.yaml"
            cache_path = Path(tmpdir) / "discovery_universe_cache.csv"
            config_path.write_text(
                "auto_discovery:\n"
                "  enabled: true\n"
                "  cache_max_age_hours: 999\n"
                "discovery_universe:\n"
                "  - WM\n",
                encoding="utf-8",
            )
            cache_path.write_text(
                "ticker,company_name,source,priority,last_seen\n"
                "MSFT,Microsoft Corporation,test,5,2026-01-01\n"
                "CTAS,Cintas Corporation,test,4,2026-01-01\n",
                encoding="utf-8",
            )

            universe = load_auto_discovery_universe(config_path, cache_path, {"MSFT"}, refresh=False)
            cache_after = cache_path.read_text(encoding="utf-8")

        self.assertIn("WM", universe)
        self.assertIn("CTAS", universe)
        self.assertNotIn("MSFT", universe)
        self.assertNotIn("MSFT,Microsoft Corporation", cache_after)
        self.assertIn("CTAS,Cintas Corporation", cache_after)

    def test_alias_inputs_are_excluded_when_canonical_ticker_is_already_known(self):
        expanded = expand_exclusions_with_alias_inputs(
            {"GOOGL"},
            {"GOOG": {"resolved_ticker": "GOOGL"}},
        )

        self.assertIn("GOOGL", expanded)
        self.assertIn("GOOG", expanded)

    def test_news_red_flag_quarantines_discovery_candidate(self):
        analysis = full_strong_analysis("TEST")
        analysis["news_red_flags"] = ["Company files for bankruptcy protection"]
        analysis["data_quality"] = "HIGH"

        status, reason, action = classify_discovery_maintenance(analysis)

        self.assertEqual(status, "QUARANTINE")
        self.assertIn("Nouvelles", reason)
        self.assertIn("validation", action)

    def test_maintenance_rows_identify_top_idea(self):
        analysis = full_strong_analysis("WM")
        analysis.update(classify_discovery_idea(analysis))
        rows = build_discovery_maintenance_rows({"WM": analysis}, {"WM": {"company_name": "Waste Management Inc."}})

        self.assertEqual(rows[0]["maintenance_status"], "ACTIVE_TOP_IDEA")


if __name__ == "__main__":
    unittest.main()
