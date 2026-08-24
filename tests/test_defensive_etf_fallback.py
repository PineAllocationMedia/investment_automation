import unittest

from src.allocation_engine import allocate_capital
from src.defensive_etf_engine import (
    build_defensive_etf_candidates,
    defensive_etf_analysis_map,
    defensive_etf_tickers_for_mode,
)
from src.validators import validate_allocation_rules
from tests.helpers import full_strong_analysis


CONFIG = {
    "defensive_etfs": [
        {
            "ticker": "XSB.TO",
            "name": "iShares Core Canadian Short Term Bond Index ETF",
            "role": "short_term_canadian_bonds",
            "category": "short_bonds",
            "allowed_modes": ["balanced", "family-office", "rational-aggressive"],
            "max_single_allocation_pct": {
                "balanced": 0.20,
                "family-office": 0.08,
                "rational-aggressive": 0.03,
            },
        },
        {
            "ticker": "ZLU.TO",
            "name": "BMO Low Volatility US Equity ETF",
            "role": "low_volatility_us_equity",
            "category": "low_vol_equity",
            "allowed_modes": ["balanced", "family-office", "rational-aggressive"],
            "max_single_allocation_pct": {
                "balanced": 0.20,
                "family-office": 0.08,
                "rational-aggressive": 0.03,
            },
        },
    ]
}

MARKET_DATA = {
    "XSB.TO": {
        "current_price": 28,
        "price_above_sma_200": True,
        "return_1y": 0.03,
        "drawdown_from_12m_high": -0.02,
        "long_name": "iShares Core Canadian Short Term Bond Index ETF",
    },
    "ZLU.TO": {
        "current_price": 50,
        "price_above_sma_200": True,
        "return_1y": 0.05,
        "drawdown_from_12m_high": -0.04,
        "long_name": "BMO Low Volatility US Equity ETF",
    },
}


class DefensiveEtfFallbackTest(unittest.TestCase):
    def test_auto_universe_is_included_without_manual_promotion(self):
        config = {
            "defensive_etfs": [],
            "auto_universe": [
                {
                    "ticker": "CBIL.TO",
                    "name": "Global X 0-3 Month T-Bill ETF",
                    "role": "treasury_bill_cash_like",
                    "category": "cash_like",
                    "allowed_modes": ["balanced", "family-office", "rational-aggressive"],
                }
            ],
        }

        self.assertEqual(defensive_etf_tickers_for_mode(config, "high-cagr"), [])
        self.assertEqual(defensive_etf_tickers_for_mode(config, "balanced"), ["CBIL.TO"])

    def test_auto_selector_keeps_best_etf_per_category_for_family_office(self):
        config = {
            "defensive_etfs": [],
            "auto_universe": [
                {
                    "ticker": "XSB.TO",
                    "name": "iShares Core Canadian Short Term Bond Index ETF",
                    "role": "short_term_canadian_bonds",
                    "category": "short_bonds",
                    "allowed_modes": ["family-office"],
                },
                {
                    "ticker": "VSB.TO",
                    "name": "Vanguard Canadian Short-Term Bond Index ETF",
                    "role": "short_term_canadian_bonds",
                    "category": "short_bonds",
                    "allowed_modes": ["family-office"],
                },
            ],
        }
        market_data = {
            "XSB.TO": {**MARKET_DATA["XSB.TO"], "price_above_sma_200": True},
            "VSB.TO": {**MARKET_DATA["XSB.TO"], "price_above_sma_200": False},
        }

        candidates = build_defensive_etf_candidates(config, "family-office", market_data)
        selected = [row["ticker"] for row in candidates if row.get("selected_for_allocation") is True]
        reserve = [row for row in candidates if row.get("selector_status") == "RESERVE_SAME_CATEGORY"]

        self.assertEqual(selected, ["XSB.TO"])
        self.assertEqual([row["ticker"] for row in reserve], ["VSB.TO"])

    def test_defensive_etf_reads_live_market_return_fields(self):
        market_data = {"XSB.TO": {**MARKET_DATA["XSB.TO"]}}
        market_data["XSB.TO"].pop("return_1y")
        market_data["XSB.TO"]["stock_return_1y"] = 0.07

        candidates = build_defensive_etf_candidates(CONFIG, "balanced", market_data)
        xsb = next(row for row in candidates if row["ticker"] == "XSB.TO")

        self.assertEqual(xsb["return_1y"], 0.07)

    def test_high_cagr_never_uses_defensive_etf_fallback(self):
        weak = full_strong_analysis("MSFT")
        weak["thesis_status"] = "UNCERTAIN"
        weak["add_eligibility_status"] = "DO_NOT_ADD"
        defensive = build_defensive_etf_candidates(CONFIG, "high-cagr", MARKET_DATA)

        result = allocate_capital(1000, {"MSFT": weak}, "high-cagr", defensive_etf_candidates=defensive)

        self.assertTrue(all(row["destination"] != "XSB.TO" for row in result["allocations"]))
        self.assertTrue(all(row["destination"] != "ZLU.TO" for row in result["allocations"]))

    def test_rational_aggressive_uses_only_tiny_defensive_fallback(self):
        weak = full_strong_analysis("MSFT")
        weak["thesis_status"] = "UNCERTAIN"
        weak["add_eligibility_status"] = "DO_NOT_ADD"
        defensive = build_defensive_etf_candidates(CONFIG, "rational-aggressive", MARKET_DATA)

        result = allocate_capital(1000, {"MSFT": weak}, "rational-aggressive", defensive_etf_candidates=defensive)
        defensive_total = sum(
            row["montant"] for row in result["allocations"] if row["destination"] in {"XSB.TO", "ZLU.TO"}
        )

        self.assertGreater(defensive_total, 0)
        self.assertLessEqual(defensive_total, 50)
        self.assertAlmostEqual(sum(row["montant"] for row in result["allocations"]), 1000)

    def test_balanced_can_use_defensive_fallback_before_vfv(self):
        weak = full_strong_analysis("MSFT")
        weak["thesis_status"] = "UNCERTAIN"
        weak["add_eligibility_status"] = "DO_NOT_ADD"
        defensive = build_defensive_etf_candidates(CONFIG, "balanced", MARKET_DATA)

        result = allocate_capital(1000, {"MSFT": weak}, "balanced", defensive_etf_candidates=defensive)
        defensive_total = sum(
            row["montant"] for row in result["allocations"] if row["destination"] in {"XSB.TO", "ZLU.TO"}
        )

        self.assertGreater(defensive_total, 0)
        self.assertLessEqual(defensive_total, 450)
        self.assertTrue(any(row["destination"] == "VFV.TO" for row in result["allocations"]))

    def test_balanced_uses_defensive_reserve_even_when_core_is_eligible(self):
        strong = full_strong_analysis("MSFT")
        strong["score_total"] = 8.8
        strong["capital_allocation_score"] = 90
        strong["expected_cagr_quality"] = "VERY_HIGH"
        strong["conviction_score"] = 92
        strong["business_quality_score"] = 95
        strong["long_term_durability_status"] = "VERY_DURABLE_COMPOUNDER"
        strong["opportunity_cost_status"] = "CLEARLY_BETTER_THAN_VFV"
        strong["current_value"] = 0
        strong["position_weight"] = 0
        defensive = build_defensive_etf_candidates(CONFIG, "balanced", MARKET_DATA)

        result = allocate_capital(1000, {"MSFT": strong}, "balanced", defensive_etf_candidates=defensive)
        defensive_total = sum(
            row["montant"] for row in result["allocations"] if row["destination"] in {"XSB.TO", "ZLU.TO"}
        )
        core_total = sum(row["montant"] for row in result["allocations"] if row["destination"] == "MSFT")

        self.assertGreaterEqual(defensive_total, 400)
        self.assertGreater(core_total, 0)
        self.assertAlmostEqual(sum(row["montant"] for row in result["allocations"]), 1000)

    def test_balanced_defensive_sleeve_keeps_inflation_aware_growth_exposure(self):
        config = {
            "selection_rules": {
                "max_selected_by_mode": {"balanced": 5},
                "max_per_category_by_mode": {"balanced": 2},
            },
            "auto_universe": [
                {
                    "ticker": "CBIL.TO",
                    "name": "Global X 0-3 Month T-Bill ETF",
                    "role": "treasury_bill_cash_like",
                    "category": "cash_like",
                    "allowed_modes": ["balanced"],
                    "max_single_allocation_pct": {"balanced": 0.15},
                },
                {
                    "ticker": "CASH.TO",
                    "name": "Global X High Interest Savings ETF",
                    "role": "cash_like",
                    "category": "cash_like",
                    "allowed_modes": ["balanced"],
                    "max_single_allocation_pct": {"balanced": 0.15},
                },
                {
                    "ticker": "VSB.TO",
                    "name": "Vanguard Canadian Short-Term Bond Index ETF",
                    "role": "short_term_canadian_bonds",
                    "category": "short_bonds",
                    "allowed_modes": ["balanced"],
                    "max_single_allocation_pct": {"balanced": 0.20},
                },
                {
                    "ticker": "VCNS.TO",
                    "name": "Vanguard Conservative ETF Portfolio",
                    "role": "conservative_all_in_one",
                    "category": "conservative_all_in_one",
                    "allowed_modes": ["balanced"],
                    "max_single_allocation_pct": {"balanced": 0.25},
                },
                {
                    "ticker": "XBAL.TO",
                    "name": "iShares Core Balanced ETF Portfolio",
                    "role": "balanced_all_in_one",
                    "category": "balanced_all_in_one",
                    "allowed_modes": ["balanced"],
                    "max_single_allocation_pct": {"balanced": 0.20},
                },
            ],
        }
        weak = full_strong_analysis("MSFT")
        weak["thesis_status"] = "UNCERTAIN"
        weak["add_eligibility_status"] = "DO_NOT_ADD"
        defensive = build_defensive_etf_candidates(config, "balanced", {})

        result = allocate_capital(1000, {"MSFT": weak}, "balanced", defensive_etf_candidates=defensive)
        destinations = {row["destination"] for row in result["allocations"]}

        self.assertTrue({"VCNS.TO", "XBAL.TO"} & destinations)

    def test_balanced_can_use_preapproved_defensive_etf_when_market_price_is_missing(self):
        config = {
            "defensive_etfs": [
                {
                    "ticker": "XSB.TO",
                    "name": "iShares Core Canadian Short Term Bond Index ETF",
                    "role": "short_term_canadian_bonds",
                    "category": "short_bonds",
                    "allowed_modes": ["balanced"],
                    "max_single_allocation_pct": {"balanced": 0.20},
                }
            ]
        }
        weak = full_strong_analysis("MSFT")
        weak["thesis_status"] = "UNCERTAIN"
        weak["add_eligibility_status"] = "DO_NOT_ADD"
        defensive = build_defensive_etf_candidates(config, "balanced", {})

        result = allocate_capital(1000, {"MSFT": weak}, "balanced", defensive_etf_candidates=defensive)

        self.assertTrue(any(row["destination"] == "XSB.TO" for row in result["allocations"]))

    def test_high_cagr_ignores_defensive_reserve_even_with_defensive_candidates(self):
        strong = full_strong_analysis("MSFT")
        strong["score_total"] = 8.8
        strong["capital_allocation_score"] = 90
        defensive = build_defensive_etf_candidates(CONFIG, "high-cagr", MARKET_DATA)

        result = allocate_capital(1000, {"MSFT": strong}, "high-cagr", defensive_etf_candidates=defensive)

        self.assertTrue(all(row["destination"] not in {"XSB.TO", "ZLU.TO"} for row in result["allocations"]))

    def test_validator_allows_defensive_etf_fallback_allocations(self):
        analyses = defensive_etf_analysis_map(build_defensive_etf_candidates(CONFIG, "balanced", MARKET_DATA))
        allocations = [{"destination": "XSB.TO", "montant": 100}]

        self.assertEqual(validate_allocation_rules(allocations, analyses), [])


if __name__ == "__main__":
    unittest.main()
