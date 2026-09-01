import tempfile
import unittest
from pathlib import Path

from src.allocation_engine import _available_monthly_room, allocate_capital, apply_deep_averaging_down_context
from src.critical_input_engine import _cost_basis_consistency_issues
from src.portfolio_loader import add_position_weights, enrich_portfolio_with_market_data, load_portfolio, merge_portfolio_rows
from src.ticker_resolver import resolve_portfolio_lot_rows, resolve_portfolio_rows
from src.utils import write_csv_records
from tests.helpers import full_strong_analysis


PRODUCTION_STYLE_ROWS = [
    {"ticker": "AAPL", "shares": 2, "average_cost": 396.94, "average_cost_currency": "CAD", "account_type": "TFSA1"},
    {"ticker": "AAPL", "shares": 0.2987, "average_cost": 299.45, "average_cost_currency": "USD", "account_type": "TFSA2"},
    {"ticker": "MSFT", "shares": 4, "average_cost": 652, "average_cost_currency": "CAD", "account_type": "TFSA1"},
    {"ticker": "MSFT", "shares": 0.1012, "average_cost": 375.18, "average_cost_currency": "USD", "account_type": "TFSA2"},
    {"ticker": "INTU", "shares": 1, "average_cost": 568.87, "average_cost_currency": "CAD", "account_type": "TFSA1"},
    {"ticker": "INTU", "shares": 0.1819, "average_cost": 395.59, "average_cost_currency": "USD", "account_type": "TFSA2"},
]


class MixedCostBasisCurrencyTest(unittest.TestCase):
    def test_exact_production_style_aapl_msft_intu_rows_are_valid_explicit_mixed_lots(self):
        issues = self._cost_basis_issues(PRODUCTION_STYLE_ROWS)

        self.assertFalse(
            [row for row in issues if row["code"] == "INCONSISTENT_TICKER_COST_BASIS_CURRENCIES"],
            issues,
        )
        self.assertFalse([row for row in issues if row["classification"] == "HARD_FAIL"], issues)

    def test_missing_currency_on_cost_bearing_row_still_fails_closed(self):
        issues = self._cost_basis_issues(
            [{"ticker": "AAPL", "shares": 1, "average_cost": 100, "average_cost_currency": "", "account_type": "TFSA1"}]
        )

        self.assertIn("COST_BASIS_CURRENCY_MISSING", {row["code"] for row in issues})

    def test_unsupported_currency_on_cost_bearing_row_fails_closed(self):
        issues = self._cost_basis_issues(
            [{"ticker": "AAPL", "shares": 1, "average_cost": 100, "average_cost_currency": "EUR", "account_type": "TFSA1"}]
        )

        self.assertIn("COST_BASIS_CURRENCY_UNSUPPORTED", {row["code"] for row in issues})

    def test_explicit_cad_field_cannot_contradict_generic_currency(self):
        issues = self._cost_basis_issues(
            [
                {
                    "ticker": "AAPL",
                    "shares": 1,
                    "average_cost_cad": 100,
                    "average_cost_currency": "USD",
                    "account_type": "TFSA1",
                }
            ]
        )

        self.assertIn("CONTRADICTORY_COST_BASIS_CURRENCY", {row["code"] for row in issues})

    def test_malformed_cost_basis_value_fails_closed(self):
        issues = self._cost_basis_issues(
            [{"ticker": "AAPL", "shares": 1, "average_cost": "not-a-number", "average_cost_currency": "CAD", "account_type": "TFSA1"}]
        )

        self.assertIn("COST_BASIS_VALUE_INVALID", {row["code"] for row in issues})

    def test_mixed_lots_preserve_accounts_without_summing_raw_costs(self):
        rows = self._load_rows(PRODUCTION_STYLE_ROWS[:2])
        metadata = {}
        aggregate = resolve_portfolio_rows(rows, {}, metadata, "fixture")[0]
        lots = resolve_portfolio_lot_rows(rows, {}, metadata, "fixture")

        self.assertAlmostEqual(aggregate["shares"], 2.2987)
        self.assertIsNone(aggregate["average_cost"])
        self.assertIsNone(aggregate["acquisition_value"])
        self.assertIsNone(aggregate["acquisition_value_cad"])
        self.assertEqual(aggregate["cost_basis_aggregation_status"], "MIXED_CURRENCY_UNNORMALIZED")
        self.assertEqual(aggregate["cost_basis_currencies"], ["CAD", "USD"])
        self.assertEqual([row["account_type"] for row in lots], ["TFSA1", "TFSA2"])
        self.assertEqual([row["average_cost_currency"] for row in lots], ["CAD", "USD"])
        self.assertEqual([row["acquisition_value"] for row in lots], [793.88, 89.45])

        loader_aggregate = merge_portfolio_rows(rows)[0]
        self.assertIsNone(loader_aggregate["acquisition_value"])
        self.assertEqual(loader_aggregate["cost_basis_aggregation_status"], "MIXED_CURRENCY_UNNORMALIZED")
        self.assertEqual(loader_aggregate["cost_basis_currencies"], ["CAD", "USD"])

    def test_mixed_cost_unavailable_does_not_impair_cad_current_value_or_weight(self):
        aapl = resolve_portfolio_rows(self._load_rows(PRODUCTION_STYLE_ROWS[:2]), {}, {}, "fixture")[0]
        vfv = resolve_portfolio_rows(
            self._load_rows(
                [{"ticker": "VFV.TO", "shares": 2, "average_cost": 100, "average_cost_currency": "CAD", "account_type": "FHSA"}]
            ),
            {},
            {},
            "fixture",
        )[0]
        enriched = enrich_portfolio_with_market_data(
            [aapl, vfv],
            {
                "AAPL": {"current_price": 100, "currency": "USD"},
                "VFV.TO": {"current_price": 100, "currency": "CAD"},
            },
            {"CAD": 1.0, "USD": 1.35},
        )
        weighted, total = add_position_weights(enriched)
        by_ticker = {row["ticker"]: row for row in weighted}

        self.assertEqual(by_ticker["AAPL"]["current_value_cad"], 310.32)
        self.assertEqual(total, 510.32)
        self.assertAlmostEqual(by_ticker["AAPL"]["position_weight"], 310.32 / 510.32)
        self.assertIsNone(by_ticker["AAPL"]["acquisition_value_cad"])

    def test_mixed_cost_basis_is_unknown_and_conservatively_non_addable_under_p3(self):
        aggregate = resolve_portfolio_rows(self._load_rows(PRODUCTION_STYLE_ROWS[:2]), {}, {}, "fixture")[0]
        enriched = enrich_portfolio_with_market_data(
            [aggregate],
            {"AAPL": {"current_price": 100, "currency": "USD"}},
            {"CAD": 1.0, "USD": 1.35},
        )[0]
        analysis = self._owned_analysis("AAPL")
        analysis.update(enriched)
        analysis["position_weight"] = 0.10

        apply_deep_averaging_down_context({"AAPL": analysis}, mode="high-cagr")

        self.assertEqual(analysis["deep_averaging_down_status"], "UNKNOWN")
        self.assertIsNone(analysis["combined_position_return"])
        self.assertTrue(analysis["deep_averaging_down_blocked"])
        self.assertEqual(self._available_room(analysis), 0)
        self.assertIn("mixed CAD/USD", analysis["deep_averaging_down_reason"])

    def test_generic_unknown_cost_basis_behavior_is_not_broadened(self):
        analysis = self._owned_analysis("AAPL")
        analysis.update({"shares": 2, "current_value": 300, "current_value_cad": 300, "acquisition_value_cad": None})

        apply_deep_averaging_down_context({"AAPL": analysis}, mode="high-cagr")

        self.assertEqual(analysis["deep_averaging_down_status"], "UNKNOWN")
        self.assertFalse(analysis["deep_averaging_down_blocked"])

    def test_mixed_owned_ticker_is_skipped_while_unrelated_candidate_can_receive_allocation(self):
        mixed = self._owned_analysis("AAPL")
        mixed.update(
            {
                "shares": 10,
                "current_value": 10_000,
                "current_value_cad": 10_000,
                "acquisition_value_cad": None,
                "position_weight": 0.10,
                "cost_basis_aggregation_status": "MIXED_CURRENCY_UNNORMALIZED",
                "cost_basis_currencies": ["CAD", "USD"],
                "capital_allocation_score": 99,
            }
        )
        unrelated = self._owned_analysis("AVGO")
        unrelated.update({"shares": 0, "current_value": 0, "current_value_cad": 0, "position_weight": 0, "capital_allocation_score": 95})
        filler = self._owned_analysis("OLD")
        filler.update(
            {
                "shares": 1,
                "current_value": 90_000,
                "current_value_cad": 90_000,
                "position_weight": 0.90,
                "thesis_status": "WEAKENING",
                "liquidation_status": "YELLOW",
                "add_eligibility_status": "DO_NOT_ADD",
            }
        )

        result = allocate_capital(1_000, {"AAPL": mixed, "AVGO": unrelated, "OLD": filler}, "high-cagr")
        amounts = {
            ticker: sum(row["montant"] for row in result["allocations"] if row["destination"] == ticker)
            for ticker in ("AAPL", "AVGO")
        }

        self.assertEqual(amounts["AAPL"], 0)
        self.assertGreater(amounts["AVGO"], 0)
        self.assertEqual(sum(row["montant"] for row in result["allocations"]), 1_000)

    def test_same_currency_multiple_accounts_retains_combined_return_behavior(self):
        rows = self._load_rows(
            [
                {"ticker": "MSFT", "shares": 3, "acquisition_value": 400, "average_cost_currency": "CAD", "account_type": "TFSA1"},
                {"ticker": "MSFT", "shares": 2, "acquisition_value": 200, "average_cost_currency": "CAD", "account_type": "TFSA2"},
            ]
        )
        aggregate = resolve_portfolio_rows(rows, {}, {}, "fixture")[0]
        enriched = enrich_portfolio_with_market_data(
            [aggregate],
            {"MSFT": {"current_price": 100, "currency": "CAD"}},
            {"CAD": 1.0},
        )[0]
        analysis = self._owned_analysis("MSFT")
        analysis.update(enriched)
        analysis["position_weight"] = 0.10

        apply_deep_averaging_down_context({"MSFT": analysis}, mode="high-cagr")

        self.assertEqual(analysis["acquisition_value_cad"], 600)
        self.assertAlmostEqual(analysis["combined_position_return"], -1 / 6)
        self.assertFalse(analysis["deep_averaging_down_blocked"])

    def test_zero_share_row_does_not_create_a_mixed_economic_cost_basis(self):
        rows = self._load_rows(
            [
                {"ticker": "MSFT", "shares": 2, "average_cost": 100, "average_cost_currency": "USD", "account_type": "TFSA1"},
                {"ticker": "MSFT", "shares": 0, "average_cost": 150, "average_cost_currency": "CAD", "account_type": "TFSA2"},
            ]
        )

        aggregate = resolve_portfolio_rows(rows, {}, {}, "fixture")[0]

        self.assertEqual(aggregate["cost_basis_aggregation_status"], "SINGLE_CURRENCY")
        self.assertEqual(aggregate["cost_basis_currencies"], ["USD"])
        self.assertEqual(aggregate["acquisition_value"], 200)
        self.assertEqual(aggregate["average_cost_currency"], "USD")

    @staticmethod
    def _owned_analysis(ticker):
        analysis = full_strong_analysis(ticker)
        analysis.update(
            {
                "ticker": ticker,
                "quality_drawdown_status": "QUALITY_DRAWDOWN_OPPORTUNITY",
                "quality_drawdown_score": 88,
                "news_context_status": "TEMPORARY_MARKET_REACTION",
                "data_reliability_level": "HIGH",
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
        return _available_monthly_room(analysis, {}, {analysis["ticker"]: analysis}, 10_000, 1_000, "high-cagr")

    @staticmethod
    def _load_rows(rows):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "portfolio.csv"
            columns = sorted({key for row in rows for key in row})
            write_csv_records(path, rows, columns)
            return load_portfolio(path)

    @staticmethod
    def _cost_basis_issues(rows):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "portfolio.csv"
            columns = sorted({key for row in rows for key in row})
            write_csv_records(path, rows, columns)
            return _cost_basis_consistency_issues(path)


if __name__ == "__main__":
    unittest.main()
