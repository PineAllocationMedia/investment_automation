import unittest
from datetime import date, timedelta

from src.market_regime_engine import (
    compute_market_regime,
    compute_market_regime_adjustment,
    compute_sector_euphoria,
    compute_sector_euphoria_adjustment,
)


def payload(
    ticker: str,
    *,
    start: float = 100,
    end: float = 110,
    above_sma: bool = True,
    drawdown: float = -0.02,
    current_price: float | None = None,
) -> dict:
    days = 150
    first = date(2025, 1, 1)
    history = {}
    for index in range(days):
        value = start + (end - start) * index / (days - 1)
        history[(first + timedelta(days=index)).isoformat()] = value
    return {
        "ticker": ticker,
        "current_price": current_price if current_price is not None else end,
        "total_return_price_history": history,
        "adjusted_stock_return_1y": end / start - 1,
        "stock_return_1y": end / start - 1,
        "price_above_sma_200": above_sma,
        "drawdown_from_12m_high": drawdown,
    }


class MarketRegimeEngineTest(unittest.TestCase):
    def test_detects_bubble_risk_from_tech_and_semiconductor_leadership(self):
        data = {
            "SPY": payload("SPY", start=100, end=108, above_sma=True),
            "VFV.TO": payload("VFV.TO", start=100, end=108, above_sma=True),
            "QQQ": payload("QQQ", start=100, end=135, above_sma=True),
            "XLK": payload("XLK", start=100, end=130, above_sma=True),
            "SOXX": payload("SOXX", start=100, end=155, above_sma=True),
            "IWM": payload("IWM", start=100, end=108, above_sma=True),
            "TLT": payload("TLT", start=100, end=100),
            "^VIX": payload("^VIX", start=17, end=16, current_price=16),
            "^TNX": payload("^TNX", start=42, end=43),
            "XLP": payload("XLP", start=100, end=104),
            "XLU": payload("XLU", start=100, end=103),
            "XLV": payload("XLV", start=100, end=105),
            "XLF": payload("XLF", start=100, end=106),
            "XLI": payload("XLI", start=100, end=107),
            "UUP": payload("UUP", start=100, end=101),
        }

        regime = compute_market_regime(data)

        self.assertEqual(regime["market_regime_status"], "BUBBLE_RISK")
        self.assertIn("tech/IA/semi", " ".join(regime["market_regime_reasons"]))

    def test_high_cagr_macro_penalty_is_capped_and_reduced_for_exceptional_compounder(self):
        regime = {"market_regime_status": "BUBBLE_RISK", "market_regime_score": 74}
        analysis = {
            "ticker": "MSFT",
            "cycle_risk_profile": "TECH_AI_GROWTH_THEME",
            "benchmark_ticker": "IGV",
            "factor_exposure": ["technology", "AI", "growth"],
            "quality_but_too_expensive": True,
            "thesis_status": "INTACT",
            "expected_cagr_quality": "VERY_HIGH",
            "opportunity_cost_status": "CLEARLY_BETTER_THAN_VFV",
            "conviction_score": 90,
        }

        result = compute_market_regime_adjustment(analysis, regime, mode="high-cagr")

        self.assertGreaterEqual(result["market_regime_allocation_adjustment"], -4.0)
        self.assertLess(result["market_regime_allocation_adjustment"], 0)
        self.assertIn("pénalité macro réduite", result["market_regime_reason"])

    def test_balanced_mode_allows_stronger_macro_penalty_than_high_cagr(self):
        regime = {"market_regime_status": "RECESSION_RISK", "market_regime_score": 68}
        analysis = {
            "ticker": "CAT",
            "cycle_risk_profile": "INDUSTRIAL_CYCLE",
            "sector": "Industrial Machinery",
            "factor_exposure": ["industrial"],
            "beta": 1.4,
            "thesis_status": "INTACT",
            "expected_cagr_quality": "MEDIUM",
        }

        high_cagr = compute_market_regime_adjustment(analysis, regime, mode="high-cagr")
        balanced = compute_market_regime_adjustment(analysis, regime, mode="balanced")

        self.assertLess(balanced["market_regime_allocation_adjustment"], high_cagr["market_regime_allocation_adjustment"])

    def test_bubble_penalty_is_granular_by_real_exposure(self):
        regime = {"market_regime_status": "BUBBLE_RISK", "market_regime_score": 79}
        direct_semi_hot = {
            "ticker": "LRCX",
            "cycle_risk_profile": "SEMI_CAPEX_CYCLE",
            "sector": "Semiconductor Manufacturing Equipment",
            "benchmark_ticker": "SOXX",
            "factor_exposure": ["semiconductors", "AI"],
            "quality_but_too_expensive": True,
            "cycle_bubble_risk_level": "EXTREME",
            "beta": 1.6,
        }
        broad_quality_tech = {
            "ticker": "MSFT",
            "cycle_risk_profile": "TECH_AI_GROWTH_THEME",
            "sector": "Cloud Computing",
            "benchmark_ticker": "IGV",
            "factor_exposure": ["technology", "cloud", "AI"],
            "balance_sheet_strong": True,
            "quality_drawdown_status": "QUALITY_DRAWDOWN_OPPORTUNITY",
        }
        defensive_quality = {
            "ticker": "LLY",
            "sector": "Pharmaceutical",
            "benchmark_ticker": "XLV",
            "factor_exposure": ["healthcare", "pharma"],
            "balance_sheet_strong": True,
        }

        direct = compute_market_regime_adjustment(direct_semi_hot, regime, mode="high-cagr")
        broad = compute_market_regime_adjustment(broad_quality_tech, regime, mode="high-cagr")
        defensive = compute_market_regime_adjustment(defensive_quality, regime, mode="high-cagr")

        self.assertLess(direct["market_regime_allocation_adjustment"], broad["market_regime_allocation_adjustment"])
        self.assertLess(broad["market_regime_allocation_adjustment"], defensive["market_regime_allocation_adjustment"])
        self.assertGreater(direct["market_regime_exposure_intensity"], broad["market_regime_exposure_intensity"])
        self.assertGreater(broad["market_regime_exposure_intensity"], defensive["market_regime_exposure_intensity"])

    def test_infrastructure_factor_alone_does_not_create_ai_bubble_exposure(self):
        regime = {"market_regime_status": "BUBBLE_RISK", "market_regime_score": 79}
        analysis = {
            "ticker": "WSP.TO",
            "cycle_risk_profile": "TECH_AI_GROWTH_THEME",
            "sector": "Engineering & Construction",
            "benchmark_ticker": "XLI",
            "factor_exposure": ["engineering", "infrastructure", "industrial"],
            "balance_sheet_strong": True,
        }

        result = compute_market_regime_adjustment(analysis, regime, mode="high-cagr")

        self.assertEqual(result["market_regime_exposure_intensity"], 0)
        self.assertNotIn("tech_ai_semi", result["market_regime_exposure"])

    def test_detects_non_tech_sector_euphoria(self):
        data = {
            "SPY": payload("SPY", start=100, end=108, above_sma=True),
            "XLE": payload("XLE", start=100, end=150, above_sma=True),
        }
        metrics = {"broad_6m": 0.08, "broad_1y": 0.08}
        config = {
            "sector_euphoria": {
                "enabled": True,
                "activation_score": 55,
                "max_reported_sectors": 5,
                "sectors": {"energy": "XLE"},
                "mode_impact": {"high-cagr": {"max_penalty": 2.5, "max_bonus": 0.5, "multiplier": 0.60}},
            }
        }

        result = compute_sector_euphoria(data, metrics, config)

        self.assertEqual(result["sector_euphoria_status"], "ACTIVE")
        self.assertEqual(result["dominant_euphoric_sectors"][0]["sector"], "energy")

    def test_sector_euphoria_adjusts_only_directly_exposed_titles(self):
        regime = {
            "sector_euphoria": {
                "sector_euphoria_status": "ACTIVE",
                "sector_euphoria_score": 80,
                "dominant_euphoric_sectors": [
                    {"sector": "energy", "ticker": "XLE", "sector_euphoria_score": 80}
                ],
                "config": {
                    "mode_impact": {
                        "high-cagr": {"max_penalty": 2.5, "max_bonus": 0.5, "multiplier": 0.60}
                    }
                },
            }
        }
        energy_stock = {
            "ticker": "CNQ.TO",
            "sector": "Energy",
            "benchmark_ticker": "XLE",
            "factor_exposure": ["energy"],
            "quality_but_too_expensive": True,
        }
        software_stock = {
            "ticker": "MSFT",
            "sector": "Cloud Computing",
            "benchmark_ticker": "IGV",
            "factor_exposure": ["technology", "cloud"],
        }

        energy = compute_sector_euphoria_adjustment(energy_stock, regime, mode="high-cagr")
        software = compute_sector_euphoria_adjustment(software_stock, regime, mode="high-cagr")

        self.assertLess(energy["sector_euphoria_allocation_adjustment"], 0)
        self.assertEqual(software["sector_euphoria_allocation_adjustment"], 0)
        self.assertGreater(energy["sector_euphoria_exposure_intensity"], software["sector_euphoria_exposure_intensity"])


if __name__ == "__main__":
    unittest.main()
