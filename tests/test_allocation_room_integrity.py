import copy
import unittest

from src.allocation_engine import (
    HIGH_CAGR_EMERGING_SATELLITE_BUDGET,
    HIGH_CAGR_EMERGING_SATELLITE_TARGET_WEIGHT,
    PORTFOLIO_VALUE_BASIS_EMPTY,
    PORTFOLIO_VALUE_BASIS_MISSING,
    PORTFOLIO_VALUE_BASIS_VALID,
    _available_monthly_room,
    _current_portfolio_value,
    _deploy_high_cagr_overflow,
    _high_cagr_overflow_room,
    _portfolio_value_basis_status,
    allocate_capital,
)
from src.portfolio_loader import enrich_portfolio_with_market_data
from tests.helpers import full_strong_analysis


def _candidate(
    ticker: str,
    score: float = 95,
    *,
    universe: str = "CORE_PORTFOLIO",
    durability: str = "VERY_DURABLE_COMPOUNDER",
) -> dict:
    row = full_strong_analysis(ticker)
    row.update(
        {
            "score_total": 9.2,
            "capital_allocation_score": score,
            "conviction_score": 95,
            "business_quality_score": 95,
            "high_cagr_potential_score": 95,
            "expected_cagr_quality": "VERY_HIGH",
            "opportunity_cost_status": "CLEARLY_BETTER_THAN_VFV",
            "thesis_status": "INTACT",
            "liquidation_status": "GREEN",
            "add_eligibility_status": "ADD_ALLOWED",
            "data_reliability_level": "HIGH",
            "data_quality": "HIGH",
            "quality_but_too_expensive": False,
            "long_term_durability_status": durability,
            "cycle_bubble_risk_level": "LOW",
            "universe": universe,
            "current_value": 0,
            "position_weight": 0,
        }
    )
    if universe != "CORE_PORTFOLIO":
        row["research_report_fields"] = ["moat_clear"]
        row["watchlist_status"] = "HIGH_PRIORITY_WATCH"
        row["external_superiority"] = "COMPARABLE_TO_CORE_LEADERS"
    return row


def _satellite(ticker: str, score: float = 95) -> dict:
    return _candidate(
        ticker,
        score,
        universe="WATCHLIST",
        durability="HIGH_GROWTH_BUT_FRAGILE",
    )


def _amount(result: dict, *tickers: str) -> float:
    return round(
        sum(row["montant"] for row in result["allocations"] if row["destination"] in tickers),
        2,
    )


class AllocationRoomIntegrityTest(unittest.TestCase):
    def test_acquisition_value_fallback_is_not_a_valid_percentage_basis(self):
        fallback = self._acquisition_value_fallback_row()

        self.assertEqual(fallback["current_value"], 1000.0)
        self.assertEqual(fallback["portfolio_valuation_source"], "acquisition_value_fallback")
        self.assertEqual(
            _portfolio_value_basis_status({"OLD": fallback}, _current_portfolio_value({"OLD": fallback})),
            PORTFOLIO_VALUE_BASIS_MISSING,
        )

    def test_acquisition_value_fallback_closes_percentage_stock_room(self):
        fallback = self._acquisition_value_fallback_row()
        candidate = _candidate("NEW")
        analyses = {"OLD": fallback, "NEW": candidate}
        total = _current_portfolio_value(analyses)
        status = _portfolio_value_basis_status(analyses, total)

        room = _available_monthly_room(
            candidate,
            {},
            {"NEW": candidate},
            total,
            1000,
            "high-cagr",
            status,
        )

        self.assertEqual(room, 0.0)
        self.assertEqual(candidate["limiting_room_reason"], "POST_PURCHASE_ROOM_UNAVAILABLE_MISSING_PORTFOLIO_VALUE")

    def test_acquisition_value_fallback_sends_blocked_capital_to_vfv(self):
        fallback = self._acquisition_value_fallback_row()
        candidate = _candidate("NEW")

        result = allocate_capital(1000, {"OLD": fallback, "NEW": candidate}, "high-cagr")

        self.assertEqual(_amount(result, "NEW"), 0.0)
        self.assertEqual(_amount(result, "VFV.TO"), 1000.0)

    def test_explicit_current_market_value_sources_remain_valid(self):
        for source in (
            "shares_x_market_price_CAD",
            "shares_x_market_price_fx_to_CAD",
            "manual_current_value_fallback",
            "manual_current_value_legacy",
            "",
        ):
            with self.subTest(source=source or "absent"):
                row = {
                    "ticker": "VALID",
                    "shares": 10,
                    "current_value": 1500.0,
                    "current_value_cad": 1500.0,
                    "position_weight": 1.0,
                }
                if source:
                    row["portfolio_valuation_source"] = source
                self.assertEqual(
                    _portfolio_value_basis_status({"VALID": row}, 1500),
                    PORTFOLIO_VALUE_BASIS_VALID,
                )

    def test_loader_market_and_manual_current_value_sources_remain_valid(self):
        cases = [
            (
                [{"ticker": "CSU.TO", "shares": 10, "average_cost": 100, "average_cost_currency": "CAD"}],
                {"CSU.TO": {"current_price": 150, "currency": "CAD"}},
                {"CAD": 1.0},
                "shares_x_market_price_CAD",
            ),
            (
                [{"ticker": "MSFT", "shares": 10, "average_cost": 100, "average_cost_currency": "USD"}],
                {"MSFT": {"current_price": 150, "currency": "USD"}},
                {"CAD": 1.0, "USD": 1.35},
                "shares_x_market_price_fx_to_CAD",
            ),
            (
                [{"ticker": "MSFT", "shares": 10, "current_value": 1800, "average_cost": 100}],
                {"MSFT": {"current_price": None, "currency": "USD"}},
                {"CAD": 1.0},
                "manual_current_value_fallback",
            ),
        ]
        for rows, market, fx, expected_source in cases:
            with self.subTest(source=expected_source):
                enriched = enrich_portfolio_with_market_data(rows, market, fx)[0]
                self.assertEqual(enriched["portfolio_valuation_source"], expected_source)
                self.assertEqual(
                    _portfolio_value_basis_status({enriched["ticker"]: enriched}, enriched["current_value"]),
                    PORTFOLIO_VALUE_BASIS_VALID,
                )

    def test_mixed_market_and_acquisition_fallback_portfolio_fails_closed(self):
        valued = {
            "ticker": "VALUED",
            "shares": 10,
            "current_value": 9000,
            "current_value_cad": 9000,
            "position_weight": 0.90,
            "portfolio_valuation_source": "shares_x_market_price_CAD",
        }
        fallback = self._acquisition_value_fallback_row()
        fallback["position_weight"] = 0.10
        analyses = {"VALUED": valued, "OLD": fallback}

        self.assertEqual(
            _portfolio_value_basis_status(analyses, _current_portfolio_value(analyses)),
            PORTFOLIO_VALUE_BASIS_MISSING,
        )

    def test_empty_overflow_above_existing_34_percent_guard_has_zero_room(self):
        candidate = _candidate("EMPTY")

        room = _high_cagr_overflow_room(
            candidate,
            {"EMPTY": 350.0},
            {"EMPTY": candidate},
            0,
            1000,
            PORTFOLIO_VALUE_BASIS_EMPTY,
        )

        self.assertEqual(room, 0.0)

    def test_empty_overflow_below_existing_34_percent_guard_retains_room(self):
        candidate = _candidate("EMPTY")

        room = _high_cagr_overflow_room(
            candidate,
            {"EMPTY": 330.0},
            {"EMPTY": candidate},
            0,
            1000,
            PORTFOLIO_VALUE_BASIS_EMPTY,
        )

        self.assertEqual(room, 120.0)

    def test_two_satellite_p4a_reproduction_is_now_capped_at_225(self):
        analyses = {"SAT1": _satellite("SAT1", 96), "SAT2": _satellite("SAT2", 95)}

        result = allocate_capital(1000, analyses, "high-cagr")

        self.assertEqual(_amount(result, "SAT1", "SAT2"), 225.0)
        satellite_rows = [row for row in result["allocations"] if row["destination"].startswith("SAT")]
        self.assertTrue(satellite_rows)
        self.assertTrue(
            all(row["limiting_room_reason"] == "EMERGING_SATELLITE_RUN_BUDGET_EXHAUSTED" for row in satellite_rows)
        )

    def test_three_satellites_share_one_run_budget(self):
        analyses = {ticker: _satellite(ticker, score) for ticker, score in [("S1", 97), ("S2", 96), ("S3", 95)]}

        result = allocate_capital(1000, analyses, "high-cagr")

        self.assertEqual(_amount(result, "S1", "S2", "S3"), 225.0)

    def test_normal_phase_allocation_counts_against_overflow_budget(self):
        first = _satellite("S1", 96)
        second = _satellite("S2", 95)
        lookup = {"S1": first, "S2": second}
        allocations = {"S1": 150.0, "S2": 50.0}

        room = _high_cagr_overflow_room(
            second,
            allocations,
            lookup,
            0,
            1000,
            PORTFOLIO_VALUE_BASIS_EMPTY,
        )

        self.assertEqual(room, 25.0)
        self.assertEqual(second["satellite_allocated_this_run"], 200.0)
        self.assertEqual(second["satellite_remaining_run_room"], 25.0)

    def test_exhausted_and_cent_boundaries_never_overshoot(self):
        candidates = {ticker: _satellite(ticker) for ticker in ("S1", "S2", "S3")}
        candidate = candidates["S3"]
        for allocated, expected in [(224.99, 0.01), (225.0, 0.0), (225.01, 0.0)]:
            allocations = {"S1": 150.0, "S2": round(allocated - 150.0, 2)}
            room = _high_cagr_overflow_room(
                candidate,
                allocations,
                candidates,
                0,
                1000,
                PORTFOLIO_VALUE_BASIS_EMPTY,
            )
            self.assertEqual(room, expected)

    def test_final_partial_overflow_chunk_uses_only_remaining_25(self):
        candidates = [_satellite("S1", 97), _satellite("S2", 96), _satellite("S3", 95)]
        lookup = {row["ticker"]: row for row in candidates}
        allocations = {"S1": 150.0, "S2": 50.0}

        deployed = _deploy_high_cagr_overflow(
            50.0,
            allocations,
            0,
            1000,
            candidates,
            50.0,
            PORTFOLIO_VALUE_BASIS_EMPTY,
        )

        self.assertEqual(deployed, 25.0)
        self.assertEqual(sum(allocations.values()), 225.0)
        self.assertEqual(lookup["S1"]["satellite_run_budget"], 225.0)

    def test_existing_15_percent_target_is_identical_in_normal_and_overflow(self):
        satellite = _satellite("SAT")
        satellite.update({"current_value": 1490.0, "current_value_cad": 1490.0, "position_weight": 1490 / 9000})
        lookup = {"SAT": satellite}

        normal_room = _available_monthly_room(
            satellite,
            {},
            lookup,
            9000,
            1000,
            "high-cagr",
            PORTFOLIO_VALUE_BASIS_VALID,
        )
        overflow_room = _high_cagr_overflow_room(
            satellite,
            {},
            lookup,
            9000,
            1000,
            PORTFOLIO_VALUE_BASIS_VALID,
        )

        self.assertEqual(HIGH_CAGR_EMERGING_SATELLITE_TARGET_WEIGHT, 0.15)
        self.assertEqual(normal_room, 10.0)
        self.assertEqual(overflow_room, 10.0)

    def test_legitimate_core_winner_overflow_remains_available(self):
        analyses = {}
        for ticker, score in [("CORE1", 96), ("CORE2", 95), ("CORE3", 94)]:
            row = _candidate(ticker, score)
            row.update(
                {
                    "current_value": 30200.0,
                    "current_value_cad": 30200.0,
                    "position_weight": 30200 / 90600,
                    "shares": 10,
                    "winner_accelerated": ticker != "CORE3",
                }
            )
            analyses[ticker] = row

        result = allocate_capital(1000, analyses, "high-cagr")

        self.assertGreater(_amount(result, "CORE1", "CORE2"), 0)
        self.assertTrue(analyses["CORE1"].get("_high_cagr_overflow_used"))
        self.assertTrue(analyses["CORE2"].get("_high_cagr_overflow_used"))

    def test_generic_durable_external_overflow_does_not_inherit_satellite_budget(self):
        durable = _candidate("EXT", universe="WATCHLIST")
        satellite = _satellite("SAT")
        lookup = {"EXT": durable, "SAT": satellite}

        room = _high_cagr_overflow_room(
            durable,
            {"SAT": 225.0},
            lookup,
            0,
            1000,
            PORTFOLIO_VALUE_BASIS_EMPTY,
        )

        self.assertGreater(room, 225.0)
        self.assertNotIn("satellite_run_budget", durable)

    def test_p3_block_has_zero_room_in_normal_and_overflow(self):
        candidate = _candidate("BLOCKED")
        candidate["deep_averaging_down_blocked"] = True
        lookup = {"BLOCKED": candidate}

        normal = _available_monthly_room(candidate, {}, lookup, 10000, 1000, "high-cagr")
        overflow = _high_cagr_overflow_room(candidate, {}, lookup, 10000, 1000)

        self.assertEqual(normal, 0.0)
        self.assertEqual(overflow, 0.0)
        self.assertEqual(candidate["limiting_room_reason"], "DEEP_AVERAGING_DOWN_BLOCKED")

    def test_reliability_cap_remains_authoritative_in_both_paths(self):
        candidate = _candidate("CAUTION")
        candidate.update(
            {
                "score_confidence_label": "WIDE",
                "conviction_confidence_label": "WIDE",
                "capital_allocation_confidence_label": "WIDE",
            }
        )
        lookup = {"CAUTION": candidate}

        normal = _available_monthly_room(
            candidate,
            {},
            lookup,
            0,
            1000,
            "high-cagr",
            PORTFOLIO_VALUE_BASIS_EMPTY,
        )
        overflow = _high_cagr_overflow_room(
            candidate,
            {},
            lookup,
            0,
            1000,
            PORTFOLIO_VALUE_BASIS_EMPTY,
        )

        self.assertLessEqual(normal, 400.0)
        self.assertLessEqual(overflow, 400.0)

    def test_watch_and_cycle_budgets_remain_authoritative_in_overflow(self):
        watched = _candidate("WATCHED")
        watched["monitoring_status"] = "WATCH"
        hot = _candidate("HOT")
        hot["cycle_bubble_risk_level"] = "HIGH"
        diversifier = _candidate("DIVERSIFIER", 90)
        lookup = {row["ticker"]: row for row in [watched, hot, diversifier]}

        watch_room = _high_cagr_overflow_room(
            watched,
            {"WATCHED": 500.0},
            lookup,
            10000,
            1000,
            PORTFOLIO_VALUE_BASIS_VALID,
        )
        cycle_room = _high_cagr_overflow_room(
            hot,
            {"HOT": 450.0},
            lookup,
            10000,
            1000,
            PORTFOLIO_VALUE_BASIS_VALID,
        )

        self.assertEqual(watch_room, 0.0)
        self.assertEqual(cycle_room, 0.0)

    def test_genuine_empty_portfolio_uses_post_contribution_basis_not_100k(self):
        candidate = _candidate("EMPTY")
        analyses = {"EMPTY": candidate}

        result = allocate_capital(1000, analyses, "high-cagr")

        self.assertEqual(_current_portfolio_value(analyses), 0.0)
        self.assertEqual(_portfolio_value_basis_status(analyses, 0), PORTFOLIO_VALUE_BASIS_EMPTY)
        self.assertEqual(_amount(result, "EMPTY"), 300.0)
        row = next(row for row in result["allocations"] if row["destination"] == "EMPTY")
        self.assertEqual(row["portfolio_value_basis_status"], PORTFOLIO_VALUE_BASIS_EMPTY)

    def test_owned_missing_value_basis_gets_no_percentage_room_and_falls_back(self):
        candidate = _candidate("MISSING")
        candidate.update({"shares": 10, "current_value": 0, "current_value_cad": 0, "position_weight": 0.10})
        analyses = {"MISSING": candidate}

        result = allocate_capital(1000, analyses, "high-cagr")

        self.assertEqual(_portfolio_value_basis_status(analyses, 0), PORTFOLIO_VALUE_BASIS_MISSING)
        self.assertEqual(_amount(result, "MISSING"), 0.0)
        self.assertEqual(_amount(result, "VFV.TO"), 1000.0)
        self.assertEqual(candidate["limiting_room_reason"], "POST_PURCHASE_ROOM_UNAVAILABLE_MISSING_PORTFOLIO_VALUE")

    def test_partial_owned_portfolio_value_basis_is_also_conservative(self):
        valued = _candidate("VALUED")
        valued.update({"shares": 10, "current_value": 9000, "current_value_cad": 9000, "position_weight": 0.90})
        missing = _candidate("MISSING")
        missing.update({"shares": 10, "current_value": 0, "current_value_cad": 0, "position_weight": 0.10})
        analyses = {"VALUED": valued, "MISSING": missing}

        result = allocate_capital(1000, analyses, "high-cagr")

        self.assertEqual(_portfolio_value_basis_status(analyses, 9000), PORTFOLIO_VALUE_BASIS_MISSING)
        self.assertEqual(_amount(result, "VALUED", "MISSING"), 0.0)
        self.assertEqual(_amount(result, "VFV.TO"), 1000.0)

    def test_valid_current_value_basis_is_unchanged_and_uses_cad_fallback(self):
        candidate = _candidate("VALID")
        candidate.update({"current_value": 0, "current_value_cad": 10000.0, "position_weight": 1.0, "shares": 10})

        self.assertEqual(_current_portfolio_value({"VALID": candidate}), 10000.0)
        self.assertEqual(
            _portfolio_value_basis_status({"VALID": candidate}, 10000),
            PORTFOLIO_VALUE_BASIS_VALID,
        )

    def test_scores_conviction_cagr_and_sell_state_are_not_modified(self):
        analyses = {"S1": _satellite("S1", 96), "S2": _satellite("S2", 95)}
        protected = {
            ticker: {
                key: row.get(key)
                for key in (
                    "business_quality_score",
                    "score_total",
                    "capital_allocation_score",
                    "conviction_score",
                    "expected_cagr_quality",
                    "liquidation_status",
                    "thesis_status",
                )
            }
            for ticker, row in analyses.items()
        }

        result = allocate_capital(1000, analyses, "high-cagr")

        self.assertTrue(all(row["montant"] >= 0 for row in result["allocations"]))
        for ticker, expected in protected.items():
            self.assertEqual({key: analyses[ticker].get(key) for key in expected}, expected)

    def test_zero_capital_and_determinism_contracts_remain(self):
        analyses = {"S1": _satellite("S1", 96), "S2": _satellite("S2", 95)}

        zero = allocate_capital(0, copy.deepcopy(analyses), "high-cagr")
        first = allocate_capital(1000, copy.deepcopy(analyses), "high-cagr")
        second = allocate_capital(1000, copy.deepcopy(analyses), "high-cagr")

        self.assertEqual(zero["allocations"], [])
        self.assertEqual(first, second)
        self.assertEqual(HIGH_CAGR_EMERGING_SATELLITE_BUDGET, 0.225)

    @staticmethod
    def _acquisition_value_fallback_row() -> dict:
        row = enrich_portfolio_with_market_data(
            [{"ticker": "OLD", "shares": 10, "average_cost": 100, "average_cost_currency": "CAD"}],
            {"OLD": {"current_price": None, "currency": "CAD"}},
            {"CAD": 1.0},
        )[0]
        row.update(
            {
                "position_weight": 1.0,
                "thesis_status": "WEAKENING",
                "liquidation_status": "YELLOW",
                "add_eligibility_status": "DO_NOT_ADD",
            }
        )
        return row


if __name__ == "__main__":
    unittest.main()
