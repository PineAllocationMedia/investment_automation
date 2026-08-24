import unittest

from src.allocation_engine import (
    DEEP_AVERAGING_DOWN_THRESHOLD,
    _available_monthly_room,
    _marginal_monthly_score,
    apply_deep_averaging_down_context,
)
from src.portfolio_loader import enrich_portfolio_with_market_data
from src.sizing_engine import compute_capital_allocation_score
from src.ticker_resolver import resolve_portfolio_rows
from tests.helpers import full_strong_analysis


class DeepAveragingDownSafeguardTest(unittest.TestCase):
    def test_combined_cost_basis_and_current_value_are_aggregated_across_accounts(self):
        analysis = self._analysis_from_lots(
            [
                self._lot("TFSA1", shares=3, acquisition_value=400),
                self._lot("TFSA2", shares=2, acquisition_value=200),
            ],
            current_price_cad=100,
        )

        self.assertEqual(analysis["shares"], 5)
        self.assertEqual(analysis["current_value_cad"], 500)
        self.assertEqual(analysis["acquisition_value_cad"], 600)
        self.assertAlmostEqual(analysis["combined_position_return"], -1 / 6)
        self.assertEqual(analysis["deep_averaging_down_status"], "ABOVE_DEEP_THRESHOLD")

    def test_below_deep_threshold_does_not_activate_special_block(self):
        analysis = self._owned_analysis(current_value=850, acquisition_value=1000, reliability="MEDIUM")

        apply_deep_averaging_down_context({"MSFT": analysis}, mode="high-cagr")

        self.assertAlmostEqual(analysis["combined_position_return"], -0.15)
        self.assertFalse(analysis["deep_averaging_down_blocked"])
        self.assertGreater(self._available_room(analysis), 0)
        self.assertEqual(analysis["sell_decision"], "HOLD")

    def test_exact_minus_twenty_percent_is_inside_the_blocking_threshold(self):
        analysis = self._owned_analysis(current_value=800, acquisition_value=1000, reliability="MEDIUM")

        apply_deep_averaging_down_context({"MSFT": analysis}, mode="high-cagr")

        self.assertAlmostEqual(analysis["combined_position_return"], -0.20)
        self.assertTrue(analysis["deep_averaging_down_blocked"])
        self.assertEqual(self._available_room(analysis), 0)

    def test_deep_drawdown_with_strong_clean_evidence_keeps_normal_room_and_bonus(self):
        analysis = self._owned_analysis(current_value=750, acquisition_value=1000)

        apply_deep_averaging_down_context({"MSFT": analysis}, mode="high-cagr")
        scored = compute_capital_allocation_score(analysis, {"concentration_by_sector": {}, "top3_weight": 0})
        analysis.update(scored)

        self.assertTrue(analysis["quality_drawdown_allocation_exception_passed"])
        self.assertFalse(analysis["deep_averaging_down_blocked"])
        self.assertGreater(self._available_room(analysis), 0)
        self.assertGreater(analysis["quality_drawdown_allocation_adjustment"], 0)
        self.assertGreater(
            _marginal_monthly_score(analysis, {}, {"MSFT": analysis}, 10_000, 1_000, "high-cagr"),
            analysis["capital_allocation_score"],
        )

    def test_deep_drawdown_with_weak_reliability_blocks_room_and_positive_rewards(self):
        analysis = self._owned_analysis(current_value=750, acquisition_value=1000, reliability="MEDIUM")

        apply_deep_averaging_down_context({"MSFT": analysis}, mode="high-cagr")
        scored = compute_capital_allocation_score(analysis, {"concentration_by_sector": {}, "top3_weight": 0})
        analysis.update(scored)

        self.assertFalse(analysis["quality_drawdown_allocation_exception_passed"])
        self.assertTrue(analysis["deep_averaging_down_blocked"])
        self.assertEqual(self._available_room(analysis), 0)
        self.assertEqual(analysis["quality_drawdown_allocation_adjustment"], 0)
        self.assertIn("reliability=MEDIUM", analysis["deep_averaging_down_reason"])
        self.assertEqual(analysis["sell_decision"], "HOLD")

    def test_deep_drawdown_with_material_conflict_is_auditable_and_does_not_sell(self):
        analysis = self._owned_analysis(current_value=750, acquisition_value=1000)
        analysis["official_conflict_profile"] = "MATERIAL_REVIEW"

        apply_deep_averaging_down_context({"MSFT": analysis}, mode="high-cagr")
        self.assertTrue(analysis["quality_drawdown_material_conflict"])
        self.assertTrue(analysis["deep_averaging_down_blocked"])
        self.assertIn("MATERIAL_REVIEW", analysis["deep_averaging_down_reason"])
        self.assertEqual(analysis["sell_decision"], "HOLD")

    def test_minor_technical_conflict_does_not_block_strong_evidence(self):
        analysis = self._owned_analysis(current_value=750, acquisition_value=1000)
        analysis["official_conflict_profile"] = "TECHNICAL_OR_PERIOD_DIFFERENCE"

        apply_deep_averaging_down_context({"MSFT": analysis}, mode="high-cagr")

        self.assertFalse(analysis["quality_drawdown_material_conflict"])
        self.assertTrue(analysis["quality_drawdown_allocation_exception_passed"])
        self.assertFalse(analysis["deep_averaging_down_blocked"])

    def test_evidence_recovery_is_stateless(self):
        analysis = self._owned_analysis(current_value=750, acquisition_value=1000)
        analysis["fundamental_evidence_conflict"] = True
        apply_deep_averaging_down_context({"MSFT": analysis}, mode="high-cagr")
        self.assertTrue(analysis["deep_averaging_down_blocked"])

        analysis["fundamental_evidence_conflict"] = False
        apply_deep_averaging_down_context({"MSFT": analysis}, mode="high-cagr")

        self.assertFalse(analysis["deep_averaging_down_blocked"])
        self.assertTrue(analysis["quality_drawdown_allocation_exception_passed"])

    def test_new_candidate_is_not_subject_to_averaging_down_rule(self):
        analysis = self._owned_analysis(current_value=0, acquisition_value=0)
        analysis.update({"shares": 0, "current_value": 0, "current_value_cad": 0, "position_weight": 0})

        apply_deep_averaging_down_context({"MSFT": analysis}, mode="high-cagr")

        self.assertEqual(analysis["deep_averaging_down_status"], "NOT_OWNED")
        self.assertIsNone(analysis["combined_position_return"])
        self.assertFalse(analysis["deep_averaging_down_blocked"])

    def test_missing_cost_basis_is_unknown_without_fabricated_return(self):
        analysis = self._owned_analysis(current_value=750, acquisition_value=1000)
        analysis["acquisition_value_cad"] = None

        apply_deep_averaging_down_context({"MSFT": analysis}, mode="high-cagr")

        self.assertEqual(analysis["deep_averaging_down_status"], "UNKNOWN")
        self.assertIsNone(analysis["combined_position_return"])
        self.assertFalse(analysis["deep_averaging_down_blocked"])
        self.assertIn("no combined return was fabricated", analysis["deep_averaging_down_reason"])

    def test_acquisition_value_market_fallback_is_not_treated_as_a_valid_return(self):
        analysis = self._owned_analysis(current_value=750, acquisition_value=1000)
        analysis["portfolio_valuation_source"] = "acquisition_value_fallback"

        apply_deep_averaging_down_context({"MSFT": analysis}, mode="high-cagr")

        self.assertEqual(analysis["deep_averaging_down_status"], "UNKNOWN")
        self.assertIsNone(analysis["combined_position_return"])
        self.assertFalse(analysis["deep_averaging_down_blocked"])

    def test_zero_or_malformed_cost_basis_is_unknown(self):
        for acquisition_value in (0, -100, "not-a-number"):
            with self.subTest(acquisition_value=acquisition_value):
                analysis = self._owned_analysis(current_value=750, acquisition_value=1000)
                analysis["acquisition_value_cad"] = acquisition_value

                apply_deep_averaging_down_context({"MSFT": analysis}, mode="high-cagr")

                self.assertEqual(analysis["deep_averaging_down_status"], "UNKNOWN")
                self.assertIsNone(analysis["combined_position_return"])
                self.assertFalse(analysis["deep_averaging_down_blocked"])

    def test_combined_position_governs_when_accounts_cross_threshold_in_opposite_directions(self):
        above = self._analysis_from_lots(
            [
                self._lot("TFSA1", shares=1, acquisition_value=150),
                self._lot("TFSA2", shares=9, acquisition_value=850),
            ],
            current_price_cad=90,
        )
        deep = self._analysis_from_lots(
            [
                self._lot("TFSA1", shares=1, acquisition_value=50),
                self._lot("TFSA2", shares=9, acquisition_value=1200),
            ],
            current_price_cad=90,
            reliability="MEDIUM",
        )

        self.assertAlmostEqual(above["combined_position_return"], -0.10)
        self.assertFalse(above["deep_averaging_down_blocked"])
        self.assertAlmostEqual(deep["combined_position_return"], -0.28)
        self.assertTrue(deep["deep_averaging_down_blocked"])

    def test_threshold_is_exactly_one_explicit_minus_twenty_percent_policy(self):
        self.assertEqual(DEEP_AVERAGING_DOWN_THRESHOLD, -0.20)

    def _analysis_from_lots(self, lots, *, current_price_cad, reliability="HIGH"):
        resolved = resolve_portfolio_rows(lots, {}, {}, "fixture")
        enriched = enrich_portfolio_with_market_data(
            resolved,
            {"MSFT": {"current_price": current_price_cad, "currency": "CAD"}},
            {"CAD": 1.0},
        )[0]
        analysis = self._owned_analysis(
            current_value=enriched["current_value_cad"],
            acquisition_value=enriched["acquisition_value_cad"],
            reliability=reliability,
        )
        analysis.update(enriched)
        analysis["position_weight"] = 0.10
        apply_deep_averaging_down_context({"MSFT": analysis}, mode="high-cagr")
        return analysis

    @staticmethod
    def _lot(account_type, *, shares, acquisition_value):
        return {
            "ticker": "MSFT",
            "account_type": account_type,
            "shares": shares,
            "acquisition_value": acquisition_value,
            "average_cost_currency": "CAD",
        }

    @staticmethod
    def _owned_analysis(*, current_value, acquisition_value, reliability="HIGH"):
        analysis = full_strong_analysis("MSFT")
        analysis.update(
            {
                "shares": 10,
                "current_value": current_value,
                "current_value_cad": current_value,
                "acquisition_value_cad": acquisition_value,
                "current_value_currency": "CAD",
                "acquisition_value_currency": "CAD",
                "position_weight": 0.10,
                "quality_drawdown_status": "QUALITY_DRAWDOWN_OPPORTUNITY",
                "quality_drawdown_score": 88,
                "quality_drawdown_allocation_adjustment": 5,
                "news_context_status": "TEMPORARY_MARKET_REACTION",
                "data_reliability_level": reliability,
                "requires_manual_validation_for_large_allocation": False,
                "business_quality_score": 88,
                "long_term_durability_score": 88,
                "long_term_durability_status": "VERY_DURABLE_COMPOUNDER",
                "high_cagr_potential_score": 88,
                "capital_allocation_score": 85,
                "add_eligibility_status": "ADD_ALLOWED",
                "sell_decision": "HOLD",
                "recommended_action": "HOLD",
            }
        )
        return analysis

    @staticmethod
    def _available_room(analysis):
        return _available_monthly_room(analysis, {}, {"MSFT": analysis}, 10_000, 1_000, "high-cagr")


if __name__ == "__main__":
    unittest.main()
