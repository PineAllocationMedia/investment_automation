import unittest

from tests.helpers import full_strong_analysis
from src.allocation_engine import allocate_capital, compute_average_score_ex_vfv, mandatory_vfv_percent
from src.sizing_engine import compute_capital_allocation_score


class AllocationTest(unittest.TestCase):
    def test_mandatory_vfv_percentage(self):
        self.assertEqual(mandatory_vfv_percent(8.2), 0.10)
        self.assertEqual(mandatory_vfv_percent(8.2, "balanced"), 0.25)
        self.assertEqual(mandatory_vfv_percent(8.2, "family-office"), 0.15)
        self.assertEqual(mandatory_vfv_percent(6.9), 0.25)
        self.assertEqual(mandatory_vfv_percent(8.2, "high-cagr"), 0.05)
        self.assertEqual(mandatory_vfv_percent(8.6, "high-cagr"), 0.05)

    def test_cash_rule_redirects_to_vfv_when_no_action_eligible(self):
        weak = full_strong_analysis("MSFT")
        weak["thesis_status"] = "UNCERTAIN"
        weak["liquidation_status"] = "YELLOW"
        weak["capital_allocation_score"] = 90
        result = allocate_capital(1000, {"MSFT": weak, "VFV.TO": {"ticker": "VFV.TO", "score_total": 0}}, "family-office")
        self.assertAlmostEqual(sum(row["montant"] for row in result["allocations"]), 1000)
        self.assertTrue(all(row["destination"] == "VFV.TO" for row in result["allocations"]))

    def test_orange_or_red_never_receive_allocation(self):
        for status in ["ORANGE", "RED"]:
            candidate = full_strong_analysis("MSFT")
            candidate["liquidation_status"] = status
            candidate["add_eligibility_status"] = "DO_NOT_ADD"
            candidate["capital_allocation_score"] = 95
            result = allocate_capital(1000, {"MSFT": candidate}, "family-office")
            self.assertTrue(all(row["destination"] != "MSFT" for row in result["allocations"]))

    def test_yellow_technical_can_receive_limited_allocation(self):
        candidate = full_strong_analysis("MSFT")
        candidate["liquidation_status"] = "YELLOW"
        candidate["add_eligibility_status"] = "ADD_ALLOWED_SMALL"
        candidate["add_eligibility_size"] = "LIMITED"
        candidate["confirmed_fundamental_sell_signals"] = []
        candidate["technical_or_valuation_signals"] = ["Prix sous SMA 200."]
        candidate["expected_cagr_quality"] = "HIGH"
        candidate["conviction_score"] = 90
        candidate["data_reliability_level"] = "HIGH"
        candidate["capital_allocation_score"] = 75

        result = allocate_capital(1000, {"MSFT": candidate}, "high-cagr")
        msft_total = sum(row["montant"] for row in result["allocations"] if row["destination"] == "MSFT")

        self.assertGreater(msft_total, 0)
        self.assertLessEqual(msft_total, 250)

    def test_zero_value_core_candidates_get_starter_allocation_before_large_vfv_redirect(self):
        existing = full_strong_analysis("MSFT")
        existing["score_total"] = 8.2
        existing["thesis_status"] = "WEAKENING"
        existing["liquidation_status"] = "YELLOW"
        existing["add_eligibility_status"] = "DO_NOT_ADD"
        existing["capital_allocation_score"] = 0
        existing["current_value"] = 10_000
        existing["position_weight"] = 1.0

        first = full_strong_analysis("INTU")
        second = full_strong_analysis("ASML")
        for candidate in [first, second]:
            candidate["current_value"] = 0
            candidate["position_weight"] = 0
            candidate["liquidation_status"] = "YELLOW"
            candidate["add_eligibility_status"] = "ADD_ALLOWED_SMALL"
            candidate["add_eligibility_size"] = "LIMITED"
            candidate["expected_cagr_quality"] = "HIGH"
            candidate["conviction_score"] = 90
            candidate["data_reliability_level"] = "HIGH"
            candidate["capital_allocation_score"] = 75

        result = allocate_capital(500, {"MSFT": existing, "INTU": first, "ASML": second}, "high-cagr")
        vfv_total = sum(row["montant"] for row in result["allocations"] if row["destination"] == "VFV.TO")
        starter_total = sum(row["montant"] for row in result["allocations"] if row["destination"] in {"INTU", "ASML"})

        self.assertLessEqual(vfv_total, 150)
        self.assertGreaterEqual(starter_total, 350)

    def test_low_reliability_estimates_do_not_receive_allocation(self):
        candidate = full_strong_analysis("MSFT")
        candidate["capital_allocation_score"] = 95
        candidate["data_reliability_level"] = "LOW"
        result = allocate_capital(1000, {"MSFT": candidate}, "family-office")
        self.assertTrue(all(row["destination"] != "MSFT" for row in result["allocations"]))

    def test_high_cagr_still_excludes_external_candidates_without_promotion(self):
        core = full_strong_analysis("MSFT")
        external = full_strong_analysis("NVDA")
        external["universe"] = "WATCHLIST"
        core["capital_allocation_score"] = 75
        external["capital_allocation_score"] = 99
        result = allocate_capital(1000, {"MSFT": core, "NVDA": external}, "high-cagr")
        self.assertTrue(all(row["destination"] != "NVDA" for row in result["allocations"]))

    def test_high_cagr_still_excludes_external_candidates_even_if_promotion_ready(self):
        core = full_strong_analysis("MSFT")
        external = full_strong_analysis("NVDA")
        external.update(
            {
                "universe": "WATCHLIST",
                "watchlist_status": "HIGH_PRIORITY_WATCH",
                "promotion_status": "PROMOTE_TO_CORE_REVIEW",
                "external_superiority": "COMPARABLE_TO_CORE_LEADERS",
                "add_eligibility_status": "ADD_ALLOWED",
                "capital_allocation_score": 99,
                "current_value": 0,
                "position_weight": 0,
            }
        )
        core["capital_allocation_score"] = 75

        result = allocate_capital(1000, {"MSFT": core, "NVDA": external}, "high-cagr")

        self.assertTrue(all(row["destination"] != "NVDA" for row in result["allocations"]))

    def test_non_high_cagr_modes_can_allocate_to_strict_external_candidates(self):
        core = full_strong_analysis("MSFT")
        external = full_strong_analysis("NVDA")
        external.update(
            {
                "universe": "WATCHLIST",
                "watchlist_status": "HIGH_PRIORITY_WATCH",
                "add_eligibility_status": "ADD_ALLOWED",
                "data_quality": "HIGH",
                "data_reliability_level": "HIGH",
                "external_superiority": "COMPARABLE_TO_CORE_LEADERS",
                "business_quality_score": 92,
                "long_term_durability_status": "VERY_DURABLE_COMPOUNDER",
                "capital_allocation_score": 96,
                "current_value": 0,
                "position_weight": 0,
            }
        )
        core["capital_allocation_score"] = 75

        result = allocate_capital(1000, {"MSFT": core, "NVDA": external}, "family-office")
        external_total = sum(row["montant"] for row in result["allocations"] if row["destination"] == "NVDA")

        self.assertGreater(external_total, 0)
        self.assertLessEqual(external_total, 160)

    def test_non_high_cagr_modes_can_allocate_to_external_etfs_with_etf_rules(self):
        etf = {
            "ticker": "XBAL.TO",
            "universe": "MARKET_SCANNER",
            "asset_type": "ETF_BALANCED_ALLOCATION",
            "external_etf_allocation_status": "ELIGIBLE_EXTERNAL_ETF_ALLOCATION",
            "capital_allocation_score": 86,
            "current_value": 0,
            "position_weight": 0,
            "current_price": 28,
            "add_eligibility_status": "ADD_ALLOWED",
            "expected_cagr_quality": "MEDIUM",
            "opportunity_cost_status": "ETF_COMPLEMENTS_VFV",
            "liquidation_status": "GREEN",
            "thesis_status": "ETF",
            "data_reliability_level": "ETF",
        }

        result = allocate_capital(1000, {"XBAL.TO": etf}, "balanced")
        etf_total = sum(row["montant"] for row in result["allocations"] if row["destination"] == "XBAL.TO")

        self.assertGreater(etf_total, 0)
        self.assertLessEqual(etf_total, 80)

    def test_high_cagr_still_excludes_external_etfs(self):
        etf = {
            "ticker": "QQQ",
            "universe": "MARKET_SCANNER",
            "asset_type": "ETF_NASDAQ_100",
            "external_etf_allocation_status": "ELIGIBLE_EXTERNAL_ETF_ALLOCATION",
            "capital_allocation_score": 95,
            "current_value": 0,
            "position_weight": 0,
            "current_price": 500,
            "add_eligibility_status": "ADD_ALLOWED",
            "expected_cagr_quality": "HIGH",
            "opportunity_cost_status": "ETF_COMPLEMENTS_VFV",
            "liquidation_status": "GREEN",
            "thesis_status": "ETF",
            "data_reliability_level": "ETF",
        }

        result = allocate_capital(1000, {"QQQ": etf}, "high-cagr")

        self.assertTrue(all(row["destination"] != "QQQ" for row in result["allocations"]))

    def test_dynamic_sizing_allocates_to_strong_candidate(self):
        strong = full_strong_analysis("MSFT")
        strong.update(compute_capital_allocation_score(strong, {"concentration_by_sector": {}, "top3_weight": 0}))
        result = allocate_capital(1000, {"MSFT": strong, "VFV.TO": {"ticker": "VFV.TO", "score_total": 8}}, "family-office")
        self.assertTrue(any(row["destination"] == "MSFT" for row in result["allocations"]))

    def test_high_cagr_mode_reduces_vfv_and_allows_larger_core_allocation(self):
        strong = full_strong_analysis("MSFT")
        strong["score_total"] = 8.6
        strong["capital_allocation_score"] = 90
        result = allocate_capital(1000, {"MSFT": strong, "VFV.TO": {"ticker": "VFV.TO", "score_total": 8}}, "high-cagr")
        vfv_total = sum(row["montant"] for row in result["allocations"] if row["destination"] == "VFV.TO")
        msft_total = sum(row["montant"] for row in result["allocations"] if row["destination"] == "MSFT")
        self.assertEqual(result["mandatory_vfv_percent"], 0.05)
        self.assertGreaterEqual(msft_total, 700)
        self.assertLessEqual(vfv_total, 300)

    def test_high_cycle_risk_reduces_monthly_allocation_size(self):
        normal = full_strong_analysis("LRCX")
        hot_cycle = full_strong_analysis("LRCX")
        for candidate in [normal, hot_cycle]:
            candidate["score_total"] = 9.0
            candidate["capital_allocation_score"] = 75
            candidate["expected_cagr_quality"] = "HIGH"
            candidate["conviction_score"] = 90
            candidate["current_value"] = 0
            candidate["position_weight"] = 0
        hot_cycle["cycle_bubble_risk_level"] = "HIGH"
        hot_cycle["cycle_bubble_penalty"] = 12
        hot_cycle["cycle_bubble_allocation_multiplier"] = 0.65

        normal_result = allocate_capital(1000, {"LRCX": normal}, "high-cagr")
        hot_result = allocate_capital(1000, {"LRCX": hot_cycle}, "high-cagr")
        normal_amount = sum(row["montant"] for row in normal_result["allocations"] if row["destination"] == "LRCX")
        hot_amount = sum(row["montant"] for row in hot_result["allocations"] if row["destination"] == "LRCX")

        self.assertLess(hot_amount, normal_amount)

    def test_non_high_cagr_modes_use_distinct_single_stock_caps(self):
        strong = full_strong_analysis("MSFT")
        strong["score_total"] = 9.0
        strong["capital_allocation_score"] = 90
        strong["expected_cagr_quality"] = "VERY_HIGH"
        strong["conviction_score"] = 92
        strong["business_quality_score"] = 95
        strong["long_term_durability_status"] = "VERY_DURABLE_COMPOUNDER"
        analyses = {"MSFT": strong}

        balanced = allocate_capital(1000, analyses, "balanced")
        family = allocate_capital(1000, analyses, "family-office")
        rational = allocate_capital(1000, analyses, "rational-aggressive")
        high = allocate_capital(1000, analyses, "high-cagr")

        amounts = {
            "balanced": sum(row["montant"] for row in balanced["allocations"] if row["destination"] == "MSFT"),
            "family": sum(row["montant"] for row in family["allocations"] if row["destination"] == "MSFT"),
            "rational": sum(row["montant"] for row in rational["allocations"] if row["destination"] == "MSFT"),
            "high": sum(row["montant"] for row in high["allocations"] if row["destination"] == "MSFT"),
        }

        self.assertLessEqual(amounts["balanced"], amounts["family"])
        self.assertLessEqual(amounts["family"], amounts["rational"])
        self.assertLessEqual(amounts["rational"], amounts["high"])

    def test_balanced_excludes_watch_and_quality_drawdown_names(self):
        watched = full_strong_analysis("APP")
        watched["monitoring_status"] = "WATCH"
        watched["quality_drawdown_status"] = "QUALITY_DRAWDOWN_OPPORTUNITY"
        watched["capital_allocation_score"] = 95
        watched["expected_cagr_quality"] = "VERY_HIGH"
        watched["opportunity_cost_status"] = "CLEARLY_BETTER_THAN_VFV"
        watched["business_quality_score"] = 95
        watched["long_term_durability_status"] = "VERY_DURABLE_COMPOUNDER"

        result = allocate_capital(1000, {"APP": watched}, "balanced")

        self.assertTrue(all(row["destination"] != "APP" for row in result["allocations"]))

    def test_cycle_budget_caps_hot_theme_when_quality_alternatives_exist(self):
        candidates = {}
        for ticker, level, score in [
            ("GOOGL", "HIGH", 96),
            ("LRCX", "EXTREME", 94),
            ("MSFT", "LOW", 86),
            ("MA", "LOW", 84),
        ]:
            candidate = full_strong_analysis(ticker)
            candidate["score_total"] = 9.0
            candidate["capital_allocation_score"] = score
            candidate["expected_cagr_quality"] = "VERY_HIGH"
            candidate["conviction_score"] = 94
            candidate["current_value"] = 0
            candidate["position_weight"] = 0
            candidate["cycle_bubble_risk_level"] = level
            candidate["cycle_bubble_penalty"] = 14 if level == "EXTREME" else 8 if level == "HIGH" else 0
            candidate["cycle_bubble_allocation_multiplier"] = 0.65 if level == "EXTREME" else 0.85 if level == "HIGH" else 1.0
            candidates[ticker] = candidate

        result = allocate_capital(1000, candidates, "high-cagr")
        by_ticker = {row["destination"]: row["montant"] for row in result["allocations"]}
        cycle_total = by_ticker.get("GOOGL", 0) + by_ticker.get("LRCX", 0)
        lower_cycle_total = by_ticker.get("MSFT", 0) + by_ticker.get("MA", 0)

        self.assertLessEqual(by_ticker.get("GOOGL", 0), 300)
        self.assertLessEqual(by_ticker.get("LRCX", 0), 100)
        self.assertLessEqual(cycle_total, 450)
        self.assertGreater(lower_cycle_total, 0)
        self.assertAlmostEqual(sum(row["montant"] for row in result["allocations"]), 1000)

    def test_quality_diversifier_can_receive_allocation_when_close_to_hot_theme(self):
        hot_theme = full_strong_analysis("GOOGL")
        diversifier = full_strong_analysis("LLY")
        large_noneligible_holding = full_strong_analysis("OLD")

        hot_theme["score_total"] = 9.5
        hot_theme["capital_allocation_score"] = 84
        hot_theme["expected_cagr_quality"] = "HIGH"
        hot_theme["conviction_score"] = 90
        hot_theme["current_value"] = 0
        hot_theme["position_weight"] = 0
        hot_theme["sector"] = "Cloud Computing"
        hot_theme["factor_exposure"] = ["technology", "AI", "cloud"]
        hot_theme["cycle_bubble_risk_level"] = "HIGH"
        hot_theme["cycle_bubble_penalty"] = 8
        hot_theme["cycle_bubble_allocation_multiplier"] = 0.75

        diversifier["score_total"] = 8.5
        diversifier["capital_allocation_score"] = 80
        diversifier["expected_cagr_quality"] = "HIGH"
        diversifier["conviction_score"] = 90
        diversifier["current_value"] = 1400
        diversifier["position_weight"] = 0.14
        diversifier["sector"] = "Pharmaceutical"
        diversifier["factor_exposure"] = ["healthcare", "pharma", "innovation"]
        diversifier["cycle_bubble_risk_level"] = "LOW"
        diversifier["cycle_bubble_penalty"] = 0
        diversifier["cycle_bubble_allocation_multiplier"] = 1.0
        diversifier["long_term_durability_status"] = "VERY_DURABLE_COMPOUNDER"
        diversifier["add_eligibility_status"] = "ADD_ALLOWED_SMALL"

        large_noneligible_holding["score_total"] = 8.0
        large_noneligible_holding["current_value"] = 8600
        large_noneligible_holding["position_weight"] = 0.86
        large_noneligible_holding["thesis_status"] = "WEAKENING"
        large_noneligible_holding["liquidation_status"] = "YELLOW"
        large_noneligible_holding["add_eligibility_status"] = "DO_NOT_ADD"

        result = allocate_capital(
            1000,
            {"GOOGL": hot_theme, "LLY": diversifier, "OLD": large_noneligible_holding},
            "high-cagr",
        )
        lly_total = sum(row["montant"] for row in result["allocations"] if row["destination"] == "LLY")

        self.assertGreater(lly_total, 0)
        self.assertTrue(any("diversificateur de qualité" in row["raison"] for row in result["allocations"] if row["destination"] == "LLY"))

    def test_quality_diversifier_bonus_does_not_rescue_weaker_candidate(self):
        hot_theme = full_strong_analysis("GOOGL")
        weak_diversifier = full_strong_analysis("LLY")
        large_noneligible_holding = full_strong_analysis("OLD")

        hot_theme["capital_allocation_score"] = 90
        hot_theme["current_value"] = 0
        hot_theme["position_weight"] = 0
        hot_theme["cycle_bubble_risk_level"] = "HIGH"
        hot_theme["cycle_bubble_penalty"] = 8
        hot_theme["cycle_bubble_allocation_multiplier"] = 0.75

        weak_diversifier["score_total"] = 7.2
        weak_diversifier["capital_allocation_score"] = 66
        weak_diversifier["expected_cagr_quality"] = "MEDIUM"
        weak_diversifier["current_value"] = 1400
        weak_diversifier["position_weight"] = 0.14
        weak_diversifier["sector"] = "Pharmaceutical"
        weak_diversifier["factor_exposure"] = ["healthcare", "pharma"]
        weak_diversifier["cycle_bubble_risk_level"] = "LOW"
        weak_diversifier["add_eligibility_status"] = "ADD_ALLOWED_SMALL"

        large_noneligible_holding["current_value"] = 8600
        large_noneligible_holding["position_weight"] = 0.86
        large_noneligible_holding["thesis_status"] = "WEAKENING"
        large_noneligible_holding["liquidation_status"] = "YELLOW"
        large_noneligible_holding["add_eligibility_status"] = "DO_NOT_ADD"

        result = allocate_capital(
            1000,
            {"GOOGL": hot_theme, "LLY": weak_diversifier, "OLD": large_noneligible_holding},
            "high-cagr",
        )
        lly_total = sum(row["montant"] for row in result["allocations"] if row["destination"] == "LLY")

        self.assertEqual(lly_total, 0)

    def test_monthly_optimizer_prefers_underweight_quality_position(self):
        overweight = full_strong_analysis("MSFT")
        underweight = full_strong_analysis("AVGO")
        for candidate in [overweight, underweight]:
            candidate["score_total"] = 9.0
            candidate["capital_allocation_score"] = 90
            candidate["expected_cagr_quality"] = "VERY_HIGH"
            candidate["conviction_score"] = 95
        overweight["current_value"] = 40_000
        overweight["position_weight"] = 0.80
        underweight["current_value"] = 10_000
        underweight["position_weight"] = 0.20

        result = allocate_capital(1000, {"MSFT": overweight, "AVGO": underweight}, "high-cagr")
        msft_total = sum(row["montant"] for row in result["allocations"] if row["destination"] == "MSFT")
        avgo_total = sum(row["montant"] for row in result["allocations"] if row["destination"] == "AVGO")

        self.assertEqual(msft_total, 0)
        self.assertGreater(avgo_total, 0)

    def test_high_cagr_caps_vfv_redirection_when_multiple_quality_candidates_exist(self):
        candidates = {}
        for ticker in ["MSFT", "GOOGL", "INTU"]:
            candidate = full_strong_analysis(ticker)
            candidate["score_total"] = 8.0
            candidate["capital_allocation_score"] = 55
            candidate["business_quality_score"] = 90
            candidate["high_cagr_potential_score"] = 82
            candidate["expected_cagr_quality"] = "HIGH"
            candidate["opportunity_cost_status"] = "CLEARLY_BETTER_THAN_VFV"
            candidate["thesis_status"] = "INTACT"
            candidate["liquidation_status"] = "YELLOW"
            candidate["add_eligibility_status"] = "ADD_ALLOWED_SMALL"
            candidate["data_reliability_level"] = "HIGH"
            candidate["current_value"] = 3000
            candidate["position_weight"] = 0.30
            candidate["cycle_bubble_risk_level"] = "LOW"
            candidate["cycle_bubble_penalty"] = 0
            candidate["cycle_bubble_allocation_multiplier"] = 1.0
            candidates[ticker] = candidate

        result = allocate_capital(1000, candidates, "high-cagr")
        vfv_total = sum(row["montant"] for row in result["allocations"] if row["destination"] == "VFV.TO")
        core_total = sum(row["montant"] for row in result["allocations"] if row["destination"] != "VFV.TO")

        self.assertLessEqual(vfv_total, 250)
        self.assertGreaterEqual(core_total, 750)

    def test_high_cagr_caps_total_watch_allocations(self):
        candidates = {}
        for ticker in ["META", "LLY", "INTU"]:
            candidate = full_strong_analysis(ticker)
            candidate["score_total"] = 9.0
            candidate["capital_allocation_score"] = 92
            candidate["expected_cagr_quality"] = "VERY_HIGH"
            candidate["conviction_score"] = 95
            candidate["monitoring_status"] = "WATCH"
            candidate["current_value"] = 0
            candidate["position_weight"] = 0
            candidates[ticker] = candidate

        normal = full_strong_analysis("GOOGL")
        normal["score_total"] = 8.8
        normal["capital_allocation_score"] = 82
        normal["expected_cagr_quality"] = "VERY_HIGH"
        normal["conviction_score"] = 92
        normal["current_value"] = 0
        normal["position_weight"] = 0
        candidates["GOOGL"] = normal

        result = allocate_capital(1000, candidates, "high-cagr")
        watch_total = sum(row["montant"] for row in result["allocations"] if row["destination"] in {"META", "LLY", "INTU"})

        self.assertLessEqual(watch_total, 600)
        self.assertAlmostEqual(sum(row["montant"] for row in result["allocations"]), 1000)

    def test_valid_poor_free_data_coverage_gets_limited_allocation(self):
        candidate = full_strong_analysis("CSU.TO")
        candidate["score_total"] = 9.0
        candidate["capital_allocation_score"] = 92
        candidate["expected_cagr_quality"] = "VERY_HIGH"
        candidate["conviction_score"] = 95
        candidate["data_reliability_level"] = "HIGH"
        candidate["ticker_validation_status"] = "OK"
        candidate["ticker_coverage_status"] = "NEEDS_BNCD_OR_MANUAL_CONFIRMATION"
        candidate["free_data_coverage_class"] = "VALID_TICKER_POOR_FREE_COVERAGE"
        candidate["manual_override_fields"] = []
        candidate["research_report_fields"] = []
        candidate["current_value"] = 0
        candidate["position_weight"] = 0

        result = allocate_capital(1000, {"CSU.TO": candidate}, "high-cagr")
        csu_total = sum(row["montant"] for row in result["allocations"] if row["destination"] == "CSU.TO")

        self.assertGreater(csu_total, 0)
        self.assertLessEqual(csu_total, 120)

    def test_high_cagr_allows_limited_exceptional_expensive_add(self):
        candidate = full_strong_analysis("GOOGL")
        candidate.update(
            {
                "score_total": 8.8,
                "conviction_score": 95,
                "expected_cagr_quality": "VERY_HIGH",
                "opportunity_cost_status": "SIMILAR_TO_VFV",
                "quality_but_too_expensive": True,
                "valuation_severity": "EXPENSIVE_BUT_EXCEPTIONAL",
                "capital_allocation_score": 62,
                "business_quality_score": 90,
                "high_cagr_potential_score": 82,
                "data_reliability_level": "HIGH",
                "add_eligibility_status": "ADD_ALLOWED",
                "liquidation_status": "GREEN",
                "thesis_status": "INTACT",
                "current_value": 100,
                "position_weight": 0.01,
                "shares": 1,
            }
        )

        result = allocate_capital(1000, {"GOOGL": candidate}, "high-cagr")
        googl_total = sum(row["montant"] for row in result["allocations"] if row["destination"] == "GOOGL")

        self.assertGreater(googl_total, 0)
        self.assertLessEqual(googl_total, 220)

    def test_high_cagr_blocks_extreme_expensive_add(self):
        candidate = full_strong_analysis("GOOGL")
        candidate.update(
            {
                "score_total": 9.2,
                "conviction_score": 98,
                "expected_cagr_quality": "VERY_HIGH",
                "opportunity_cost_status": "WORSE_THAN_VFV",
                "quality_but_too_expensive": True,
                "valuation_severity": "EXTREMELY_EXPENSIVE",
                "capital_allocation_score": 90,
                "business_quality_score": 95,
                "high_cagr_potential_score": 90,
                "data_reliability_level": "HIGH",
                "add_eligibility_status": "ADD_ALLOWED",
                "liquidation_status": "GREEN",
                "thesis_status": "INTACT",
                "current_value": 100,
                "position_weight": 0.01,
                "shares": 1,
            }
        )

        result = allocate_capital(1000, {"GOOGL": candidate}, "high-cagr")

        self.assertTrue(all(row["destination"] != "GOOGL" for row in result["allocations"]))

    def test_reliability_cap_limits_large_high_cagr_allocation_without_blocking(self):
        candidate = full_strong_analysis("INTU")
        candidate["score_total"] = 9.0
        candidate["capital_allocation_score"] = 95
        candidate["expected_cagr_quality"] = "VERY_HIGH"
        candidate["conviction_score"] = 94
        candidate["business_quality_score"] = 92
        candidate["current_value"] = 0
        candidate["position_weight"] = 0
        candidate["shares"] = 1
        candidate["data_reliability_level"] = "MEDIUM"
        candidate["score_confidence_label"] = "WIDE"
        candidate["conviction_confidence_label"] = "NORMAL"
        candidate["capital_allocation_confidence_label"] = "WIDE"

        result = allocate_capital(1000, {"INTU": candidate}, "high-cagr")
        intu_rows = [row for row in result["allocations"] if row["destination"] == "INTU"]
        intu_total = sum(row["montant"] for row in intu_rows)

        self.assertGreater(intu_total, 0)
        self.assertLessEqual(intu_total, 400)
        self.assertTrue(any(row.get("reliability_cap_applied") is True for row in intu_rows))

    def test_exceptional_confirmed_candidate_keeps_high_cagr_room_despite_medium_reliability(self):
        candidate = full_strong_analysis("MSFT")
        candidate["score_total"] = 9.2
        candidate["capital_allocation_score"] = 96
        candidate["expected_cagr_quality"] = "VERY_HIGH"
        candidate["conviction_score"] = 95
        candidate["business_quality_score"] = 95
        candidate["current_value"] = 0
        candidate["position_weight"] = 0
        candidate["shares"] = 1
        candidate["data_reliability_level"] = "MEDIUM"
        candidate["score_confidence_label"] = "NORMAL"
        candidate["conviction_confidence_label"] = "NORMAL"
        candidate["capital_allocation_confidence_label"] = "NORMAL"
        candidate["score_evidence_level"] = "MOSTLY_CONFIRMED"

        result = allocate_capital(1000, {"MSFT": candidate}, "high-cagr")
        msft_total = sum(row["montant"] for row in result["allocations"] if row["destination"] == "MSFT")

        self.assertGreaterEqual(msft_total, 500)
        self.assertLessEqual(msft_total, 600)

    def test_moderate_stability_reduces_noise_when_candidates_are_close(self):
        previous_pick = full_strong_analysis("MSFT")
        close_challenger = full_strong_analysis("AVGO")
        for candidate in [previous_pick, close_challenger]:
            candidate["score_total"] = 8.8
            candidate["expected_cagr_quality"] = "VERY_HIGH"
            candidate["conviction_score"] = 92
            candidate["current_value"] = 0
            candidate["position_weight"] = 0
            candidate["cycle_bubble_risk_level"] = "LOW"
            candidate["cycle_bubble_penalty"] = 0
            candidate["cycle_bubble_allocation_multiplier"] = 1.0
        previous_pick["capital_allocation_score"] = 85
        previous_pick["allocation_stability_adjustment"] = 3
        close_challenger["capital_allocation_score"] = 86
        close_challenger["allocation_stability_adjustment"] = 0

        result = allocate_capital(1000, {"MSFT": previous_pick, "AVGO": close_challenger}, "high-cagr")
        msft_total = sum(row["montant"] for row in result["allocations"] if row["destination"] == "MSFT")
        avgo_total = sum(row["montant"] for row in result["allocations"] if row["destination"] == "AVGO")

        self.assertGreaterEqual(msft_total, avgo_total)

    def test_moderate_stability_does_not_block_a_clear_new_leader(self):
        previous_pick = full_strong_analysis("MSFT")
        clear_leader = full_strong_analysis("AVGO")
        for candidate in [previous_pick, clear_leader]:
            candidate["score_total"] = 8.8
            candidate["expected_cagr_quality"] = "VERY_HIGH"
            candidate["conviction_score"] = 92
            candidate["current_value"] = 0
            candidate["position_weight"] = 0
            candidate["cycle_bubble_risk_level"] = "LOW"
            candidate["cycle_bubble_penalty"] = 0
            candidate["cycle_bubble_allocation_multiplier"] = 1.0
        previous_pick["capital_allocation_score"] = 82
        previous_pick["allocation_stability_adjustment"] = 3
        clear_leader["capital_allocation_score"] = 95
        clear_leader["allocation_stability_adjustment"] = 0

        result = allocate_capital(1000, {"MSFT": previous_pick, "AVGO": clear_leader}, "high-cagr")
        msft_total = sum(row["montant"] for row in result["allocations"] if row["destination"] == "MSFT")
        avgo_total = sum(row["montant"] for row in result["allocations"] if row["destination"] == "AVGO")

        self.assertGreater(avgo_total, msft_total)

    def test_high_cagr_single_name_guardrail_slows_large_position_without_blocking(self):
        concentrated = full_strong_analysis("MSFT")
        filler = full_strong_analysis("OLD")
        concentrated.update(
            {
                "score_total": 9.2,
                "capital_allocation_score": 96,
                "expected_cagr_quality": "VERY_HIGH",
                "conviction_score": 95,
                "business_quality_score": 95,
                "current_value": 24_000,
                "position_weight": 0.24,
                "score_evidence_level": "MOSTLY_CONFIRMED",
                "data_reliability_level": "HIGH",
            }
        )
        filler.update(
            {
                "current_value": 76_000,
                "position_weight": 0.76,
                "thesis_status": "WEAKENING",
                "liquidation_status": "YELLOW",
                "add_eligibility_status": "DO_NOT_ADD",
            }
        )

        result = allocate_capital(1000, {"MSFT": concentrated, "OLD": filler}, "high-cagr")
        msft_rows = [row for row in result["allocations"] if row["destination"] == "MSFT"]
        msft_total = sum(row["montant"] for row in msft_rows)

        self.assertGreater(msft_total, 0)
        self.assertLessEqual(msft_total, 400)
        self.assertTrue(any(row.get("single_name_concentration_guardrail_applied") is True for row in msft_rows))

    def test_high_cagr_single_name_guardrail_does_not_limit_under_watch_zone(self):
        candidate = full_strong_analysis("MSFT")
        filler = full_strong_analysis("OLD")
        candidate.update(
            {
                "score_total": 9.2,
                "capital_allocation_score": 96,
                "expected_cagr_quality": "VERY_HIGH",
                "conviction_score": 95,
                "business_quality_score": 95,
                "current_value": 17_000,
                "position_weight": 0.17,
                "score_evidence_level": "MOSTLY_CONFIRMED",
                "data_reliability_level": "HIGH",
            }
        )
        filler.update(
            {
                "current_value": 83_000,
                "position_weight": 0.83,
                "thesis_status": "WEAKENING",
                "liquidation_status": "YELLOW",
                "add_eligibility_status": "DO_NOT_ADD",
            }
        )

        result = allocate_capital(1000, {"MSFT": candidate, "OLD": filler}, "high-cagr")
        msft_rows = [row for row in result["allocations"] if row["destination"] == "MSFT"]
        msft_total = sum(row["montant"] for row in msft_rows)

        self.assertGreaterEqual(msft_total, 600)
        self.assertTrue(all(row.get("single_name_concentration_status") in {None, "", "NONE"} for row in msft_rows))

    def test_high_cagr_single_name_guardrail_prefers_less_concentrated_peer_when_close(self):
        concentrated = full_strong_analysis("MSFT")
        underweight = full_strong_analysis("AVGO")
        filler = full_strong_analysis("OLD")
        for candidate, current_value, weight in [(concentrated, 24_000, 0.24), (underweight, 10_000, 0.10)]:
            candidate.update(
                {
                    "score_total": 9.2,
                    "capital_allocation_score": 94,
                    "expected_cagr_quality": "VERY_HIGH",
                    "conviction_score": 95,
                    "business_quality_score": 95,
                    "current_value": current_value,
                    "position_weight": weight,
                    "score_evidence_level": "MOSTLY_CONFIRMED",
                    "data_reliability_level": "HIGH",
                }
            )
        filler.update(
            {
                "current_value": 66_000,
                "position_weight": 0.66,
                "thesis_status": "WEAKENING",
                "liquidation_status": "YELLOW",
                "add_eligibility_status": "DO_NOT_ADD",
            }
        )

        result = allocate_capital(1000, {"MSFT": concentrated, "AVGO": underweight, "OLD": filler}, "high-cagr")
        msft_total = sum(row["montant"] for row in result["allocations"] if row["destination"] == "MSFT")
        avgo_total = sum(row["montant"] for row in result["allocations"] if row["destination"] == "AVGO")

        self.assertGreater(avgo_total, msft_total)
        self.assertGreater(msft_total, 0)

    def test_average_score_is_weighted_and_excludes_tiny_satellites(self):
        core = {"ticker": "MSFT", "score_total": 8.0, "position_weight": 0.60}
        second = {"ticker": "AVGO", "score_total": 9.0, "position_weight": 0.30}
        tiny = {"ticker": "TMC", "score_total": 1.0, "position_weight": 0.01}
        result = compute_average_score_ex_vfv({"MSFT": core, "AVGO": second, "TMC": tiny})
        self.assertAlmostEqual(result, (8.0 * 0.60 + 9.0 * 0.30) / 0.90)
        self.assertIn("satellite", tiny["average_score_excluded_reason"])


if __name__ == "__main__":
    unittest.main()
