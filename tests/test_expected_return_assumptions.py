"""Synthetic constructor mechanics, fail-closed boundary and investment isolation."""
import ast
from dataclasses import FrozenInstanceError, asdict, dataclass, fields, replace
import json
import math
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from src import expected_return_assumptions as a
from src import expected_return_engine as er
from src import expected_return_policy as p
from tests.expected_return_assumption_fixtures import (
    AS_OF, BASIS, HISTORY_CASES, IDENTITY_CASES, change_provenance, change_root, facts, identity, policies, without,
)


def build(fixture=None, **overrides):
    supplied = policies(payer=bool(fixture and any(type(r) is a.OrdinaryAnnualDividend for r in fixture.roots)))
    supplied.update(overrides)
    return a.construct_expected_return(fixture or facts(), **supplied)


def node(result, transform):
    return next(n for n in result.lineage if n.transformation_id == transform)


def returns(result):
    return tuple(s.annualized_return for s in result.diagnostic.scenarios)


@dataclass(frozen=True)
class ForeignDerived:
    """Adversarial unsupported transport; not a constructor input type."""
    label: str
    origin: str
    parents: tuple
    available_at: str = AS_OF


class ConstructorTests(unittest.TestCase):
    def unavailable(self, result, reason):
        self.assertEqual(result.status, "UNAVAILABLE")
        self.assertIn(reason, result.reasons)
        self.assertIsNone(result.request)
        self.assertIsNone(result.diagnostic)

    def test_valid_build_calls_exact_pr4a_once(self):
        with patch.object(er, "calculate_expected_return", wraps=er.calculate_expected_return) as calculator:
            result = build()
        self.assertEqual(result.status, "BUILT")
        calculator.assert_called_once_with(result.request)
        self.assertIs(type(result.request), er.ExpectedReturnRequest)
        self.assertEqual(result.diagnostic, er.calculate_expected_return(result.request))
        self.assertEqual(result.diagnostic.authority, "DIAGNOSTIC_ONLY")
        self.assertEqual(result.diagnostic.return_basis, "NOMINAL_PRETAX_EQUITY_CASHFLOW_IRR")
        self.assertEqual(result.diagnostic.status, "DEGRADED")

    def test_median_latest_three_not_mean_or_latest(self):
        result = build(facts(eps=(1., 2., 9., 3., 5.)))
        self.assertEqual(result.request.scenarios[0].starting_eps_per_share, 5.)
        self.assertEqual(node(result, "MEDIAN_LATEST_THREE_DILUTED_EPS_V1").root_ids,
                         ("eps-2023", "eps-2024", "eps-2025"))

    def test_negative_latest_required_year_not_replaced_by_older_positive(self):
        fixture = facts(eps=(1., 1.1, 1.2, 1.3, -1., 2.))
        result = build(fixture)
        self.unavailable(result, "NONPOSITIVE_REQUIRED_EPS")
        self.assertEqual(len(result.input_roots), len(fixture.roots))

    def test_each_required_nonpositive_year_unavailable(self):
        for year in range(2021, 2026):
            for value in (0., -1.):
                with self.subTest(year=year, value=value):
                    self.unavailable(build(change_root(facts(), f"eps-{year}", value=value)), "NONPOSITIVE_REQUIRED_EPS")

    def test_missing_middle_not_replaced_by_older_year(self):
        fixture = without(facts(eps=(1., 1.1, 1.2, 1.3, 1.4, 1.5)), "eps-2023")
        self.unavailable(build(fixture), "MISSING_CONSECUTIVE_EPS_PERIOD")

    def test_missing_latest_year_not_silently_stale(self):
        self.unavailable(build(without(facts(eps=(1., 1.1, 1.2, 1.3, 1.4, 1.5)), "eps-2025")), "MISSING_EPS_SEQUENCE")

    def test_missing_five_year_history_unavailable(self):
        self.unavailable(build(facts(eps=(2., 3., 4.))), "MISSING_EPS_SEQUENCE")

    def test_duplicate_period_revision_rejected_regardless_of_input_order(self):
        fixture = facts()
        revision = replace(fixture.roots[0], identity=identity("revision", a.AdapterIdentity.SYNTHETIC_REPORTED_DILUTED_EPS_V1), value=7.)
        for roots in (fixture.roots + (revision,), (revision,) + fixture.roots):
            with self.subTest(roots=roots[0].identity.observation_id), self.assertRaisesRegex(p.ConstructorContractError, "Duplicate fiscal period"):
                build(replace(fixture, roots=roots))

    def test_split_currency_security_accounting_mismatches_rejected(self):
        fixture = facts()
        eps = fixture.roots[0]
        changes = (
            dict(basis=replace(BASIS, share_basis="UNRECONCILED_SPLIT")),
            dict(basis=replace(BASIS, currency="USD")),
            dict(accounting_basis="US_GAAP"),
            dict(identity=replace(eps.identity, security_id="DIFFERENT_FICTIONAL_ENTITY")),
            dict(identity=replace(eps.identity, share_class="B")),
        )
        for change in changes:
            with self.subTest(change=change), self.assertRaises(p.ConstructorContractError):
                build(change_root(fixture, "eps-2021", **change))

    def test_reordered_roots_and_exclusions_identical(self):
        fixture = facts()
        profile = next(r for r in fixture.roots if type(r) is a.ProfileQualification)
        reordered = change_root(fixture, "profile", excluded_structures=tuple(reversed(profile.excluded_structures)))
        reordered = replace(reordered, roots=tuple(reversed(reordered.roots)))
        self.assertEqual(build(fixture), build(reordered))
        self.assertEqual(json.dumps(asdict(build(fixture)), default=lambda x: x.value, sort_keys=True),
                         json.dumps(asdict(build(reordered)), default=lambda x: x.value, sort_keys=True))

    def test_equivalent_timestamp_offsets_have_same_semantic_output(self):
        fixture = replace(facts(), as_of="2026-06-30T14:00:00-04:00")
        fixture = change_provenance(fixture, "price", published_at="2026-06-30T08:00:00-04:00",
                                   available_at="2026-06-30T08:00:00-04:00", captured_at="2026-06-30T08:00:00-04:00")
        self.assertEqual(build(fixture), build())

    def test_all_observations_retained_even_older_unused(self):
        result = build(facts(eps=(-7., 1., 2., 3., 4., 5.)))
        self.assertEqual(result.status, "BUILT")
        self.assertIn("eps-2020", [r.identity.observation_id for r in result.input_roots])
        self.assertIn("eps-2020", [r.id for r in result.request.evidence])
        self.assertNotIn("eps-2020", dict(result.component_root_ids)["growth"])

    def test_interval_log_ratio_independent_oracle(self):
        result = build(facts(eps=(1., 2., 3., 6., 9.)))
        intervals = [n for n in result.lineage if n.transformation_id == "ANNUAL_DILUTED_EPS_LOG_RATIO_V1"]
        values = {n.root_ids: n.value for n in intervals}
        for index, expected in enumerate((math.log(2), math.log(1.5), math.log(2), math.log(1.5)), 2021):
            self.assertAlmostEqual(values[(f"eps-{index}", f"eps-{index + 1}")], expected, places=14)

    def test_historical_min_median_max_independent_oracle(self):
        result = build(facts(eps=(1., 2., 6., 24., 120.)))
        for label, expected in (("BEAR", math.log(2)), ("BASE", (math.log(3) + math.log(4)) / 2), ("BULL", math.log(5))):
            anchor = node(result, "HISTORICAL_LOG_" + label + "_V1")
            self.assertAlmostEqual(anchor.value, expected, places=14)
            self.assertEqual(anchor.root_ids, tuple(f"eps-{year}" for year in range(2021, 2026)))
            self.assertEqual(len(anchor.parents), 4)

    def test_exact_fade_and_exp_conversion(self):
        fixture = facts(eps=(1., 2., 4., 8., 16.))
        supplied = policies(mature=(.0, .0, .0))
        result = a.construct_expected_return(fixture, **supplied)
        expected = (1., 1., 2 ** .75 - 1, 2 ** .5 - 1, 2 ** .25 - 1, 0., 0.)
        for scenario in result.request.scenarios:
            faded = node(result, "LOG_GROWTH_FADE_7Y_V1:" + scenario.name)
            self.assertEqual(len(faded.policy_hashes), 1)
            for actual, weight in zip(faded.value, (1., 1., .75, .5, .25, 0., 0.)):
                self.assertAlmostEqual(actual, weight * math.log(2), places=14)
            for actual, want in zip(scenario.growth_rates, expected):
                self.assertAlmostEqual(actual, want, places=14)

    def test_scenario_ordering_for_all_paths_and_returns(self):
        result = build(facts(payer=True))
        for field in ("growth_rates", "dividends_per_share"):
            paths = [getattr(s, field) for s in result.request.scenarios]
            for year in range(7):
                self.assertLessEqual(paths[0][year], paths[1][year])
                self.assertLessEqual(paths[1][year], paths[2][year])
        self.assertEqual(returns(result), tuple(sorted(returns(result))))

    def test_growth_independent_of_observed_price(self):
        low, high = build(facts(price=2.)), build(facts(price=2000.))
        for left, right in zip(low.request.scenarios, high.request.scenarios):
            self.assertEqual(left.growth_rates, right.growth_rates)
            self.assertEqual(left.terminal_pe, right.terminal_pe)
            self.assertEqual(left.dividends_per_share, right.dividends_per_share)
        self.assertGreater(returns(low)[1], returns(high)[1])

    def test_synthetic_history_cases_fade_context_not_auto_perpetuated(self):
        for name, history in HISTORY_CASES:
            with self.subTest(name=name):
                result = build(facts(eps=history))
                self.assertEqual(result.status, "BUILT")
                for index, expected in enumerate((.01, .03, .05)):
                    self.assertAlmostEqual(result.request.scenarios[index].growth_rates[-1], expected)
                    self.assertAlmostEqual(result.request.scenarios[index].growth_rates[-2], expected)

    def test_payer_period_aligned_payout_uses_reported_not_normalized_eps(self):
        result = build(facts(eps=(1., 2., 3., 4., 6.), payer=True))
        # D_ref=.9, EPS_ref=6 => .15; starting median=4, NOT denominator=4.
        self.assertEqual(node(result, "CONSTANT_MATCHED_ORDINARY_PAYOUT_V1").value, .15)
        for scenario in result.request.scenarios:
            projected = 4.
            for growth, dividend in zip(scenario.growth_rates, scenario.dividends_per_share):
                projected *= 1 + growth
                self.assertAlmostEqual(dividend, .15 * projected)
        self.assertEqual(node(result, "CONSTANT_MATCHED_ORDINARY_PAYOUT_V1").root_ids, ("dividend", "eps-2025"))

    def test_payout_above_earnings_is_economic_unavailability(self):
        fixture = change_root(facts(eps=(2.,) * 5, payer=True), "dividend", value=3.)
        self.unavailable(build(fixture), "PAYOUT_EXCEEDS_EARNINGS")

    def test_exactly_full_payout_remains_supported(self):
        fixture = change_root(facts(eps=(2.,) * 5, payer=True), "dividend", value=2.)
        result = build(fixture)
        self.assertEqual(result.status, "BUILT")
        self.assertEqual(node(result, "CONSTANT_MATCHED_ORDINARY_PAYOUT_V1").value, 1.)
        self.assertIsNotNone(result.diagnostic)
        for scenario in result.request.scenarios:
            projected = 2.
            for growth, dividend in zip(scenario.growth_rates, scenario.dividends_per_share):
                projected *= 1 + growth
                self.assertEqual(dividend, projected)

    def test_payout_immediately_above_one_has_no_tolerance_or_clamping(self):
        dividend = math.nextafter(2., math.inf)
        self.assertEqual(dividend / 2., math.nextafter(1., math.inf))
        fixture = change_root(facts(eps=(2.,) * 5, payer=True), "dividend", value=dividend)
        with patch.object(er, "calculate_expected_return", wraps=er.calculate_expected_return) as calculator:
            result = build(fixture)
        self.unavailable(result, "PAYOUT_EXCEEDS_EARNINGS")
        calculator.assert_not_called()
        self.assertEqual(next(r.value for r in result.input_roots if type(r) is a.OrdinaryAnnualDividend), dividend)
        self.assertFalse(any(n.transformation_id.startswith(("CONSTANT_MATCHED_ORDINARY_PAYOUT", "DIVIDEND_SCHEDULE"))
                             for n in result.lineage))

    def test_normal_payer_cash_flows_and_pre_correction_returns_unchanged(self):
        result = build(facts(payer=True))
        self.assertEqual(result.status, "BUILT")
        self.assertEqual(node(result, "CONSTANT_MATCHED_ORDINARY_PAYOUT_V1").value, .3)
        # Existing fixture: matched dividend .9 / reported EPS 3 = .3;
        # the latest-three median used to project EPS remains 2.7.
        for scenario in result.request.scenarios:
            projected = 2.7
            for growth, dividend in zip(scenario.growth_rates, scenario.dividends_per_share):
                projected *= 1 + growth
                self.assertEqual(dividend, .3 * projected)
        # Captured at a3645a4; only libm/IRR comparison uses numerical tolerance.
        for actual, expected in zip(returns(result), (.019342232275808047, .08157136351772037, .1405980658758347)):
            self.assertAlmostEqual(actual, expected, delta=2e-14)

    def test_nonpayer_cash_flows_and_pre_correction_returns_unchanged(self):
        result = build(facts())
        self.assertEqual(result.status, "BUILT")
        self.assertEqual(node(result, "CONTINUED_VERIFIED_NONPAYER_V1").value, 0.)
        for scenario in result.request.scenarios:
            self.assertEqual(scenario.dividends_per_share, (0.,) * 7)
        for actual, expected in zip(returns(result), (-.003467440923891662, .06089762040432094, .12115309470015583)):
            self.assertAlmostEqual(actual, expected, delta=2e-14)

    def test_nonpayer_requires_continued_policy_and_constructs_zeros(self):
        result = build()
        for scenario in result.request.scenarios:
            self.assertEqual(scenario.dividends_per_share, (0.,) * 7)
        self.unavailable(build(distribution_policy=None), "MISSING_DISTRIBUTION_POLICY")
        self.unavailable(build(distribution_policy=policies(payer=True)["distribution_policy"]), "INAPPLICABLE_DISTRIBUTION_POLICY")

    def test_payer_requires_explicit_applicable_policy(self):
        self.unavailable(build(facts(payer=True), distribution_policy=None), "MISSING_DISTRIBUTION_POLICY")
        self.unavailable(build(facts(payer=True), distribution_policy=policies()["distribution_policy"]), "INAPPLICABLE_DISTRIBUTION_POLICY")

    def test_unknown_dividend_status_is_not_zero(self):
        self.unavailable(build(without(facts(), "nonpayer")), "MISSING_DIVIDEND_STATUS")
        self.unavailable(build(change_root(facts(payer=True), "dividend", value=0.)), "MISSING_DIVIDEND_STATUS")

    def test_special_dividend_not_recurring(self):
        with self.assertRaisesRegex(p.ConstructorContractError, "exclude specials"):
            build(change_root(facts(payer=True), "dividend", special_dividends_excluded=False))
        # The sole accepted dividend root explicitly carries ordinary amounts.
        self.assertTrue(next(r for r in facts(payer=True).roots if type(r) is a.OrdinaryAnnualDividend).special_dividends_excluded)
        self.assertNotIn("special_dividend", {f.name for f in fields(a.OrdinaryAnnualDividend)})

    def test_dividend_and_nonpayer_mismatched_period_unavailable(self):
        for payer, identifier in ((True, "dividend"), (False, "nonpayer")):
            self.unavailable(build(change_root(facts(payer=payer), identifier,
                period=a.AnnualPeriod("2024-01-01", "2024-12-31"))), "DIVIDEND_EPS_PERIOD_MISMATCH")

    def test_conflicting_dividend_status_contract_error(self):
        fixture = facts()
        with self.assertRaisesRegex(p.ConstructorContractError, "Contradictory payer"):
            build(replace(fixture, roots=fixture.roots + (facts(payer=True).roots[-1],)))

    def test_per_share_identities_have_no_second_buyback_or_dilution_term(self):
        for name, earnings_factor, shares_factor in IDENTITY_CASES:
            with self.subTest(name=name):
                per_share_factor = earnings_factor / shares_factor
                history = tuple(2 * per_share_factor ** year for year in range(5))
                supplied = policies(mature=(per_share_factor - 1,) * 3, terminal=(10.,) * 3)
                # starting median is fourth observation; price=10*normalized EPS, no dividends.
                result = a.construct_expected_return(facts(eps=history, price=10 * history[3]), **supplied)
                for scenario in result.request.scenarios:
                    for growth in scenario.growth_rates:
                        self.assertAlmostEqual(1 + growth, earnings_factor / shares_factor, places=14)
                for actual in returns(result):
                    self.assertAlmostEqual(actual, per_share_factor - 1, delta=2e-14)

    def test_no_optional_share_history_or_analyst_inputs_needed(self):
        result = build()
        self.assertEqual(result.status, "BUILT")
        self.assertEqual({type(r) for r in result.input_roots},
                         {a.ReportedDilutedEPS, a.ObservedPrice, a.VerifiedNonpayer, a.ProfileQualification})
        for forbidden in ("buyback_yield", "shareholder_yield", "forward_eps", "analyst_estimate", "market_cap", "dividend_yield"):
            self.assertNotIn(forbidden, {f.name for f in fields(a.QualifiedFacts)})

    def test_terminal_multiples_are_exact_explicit_policy(self):
        result = build()
        self.assertEqual(tuple(s.terminal_pe for s in result.request.scenarios), (12., 16., 20.))
        for n in result.lineage:
            if n.transformation_id.startswith("INDEPENDENT_TERMINAL_PE"):
                self.assertEqual(n.root_ids, ("profile",))

    def test_terminal_contraction_and_expansion_math(self):
        for price, positive in ((100., False), (10., True)):
            result = a.construct_expected_return(facts(eps=(2.,) * 5, price=price),
                **policies(mature=(0.,) * 3, terminal=(10.,) * 3))
            expected = (20 / price) ** (1 / 7) - 1
            for actual in returns(result):
                self.assertAlmostEqual(actual, expected, delta=2e-14)
                self.assertEqual(actual > 0, positive)

    def test_high_current_multiple_does_not_select_terminal_policy(self):
        result = build(facts(price=10000.))
        self.assertEqual(tuple(s.terminal_pe for s in result.request.scenarios), (12., 16., 20.))
        self.assertLess(returns(result)[2], 0.)

    def test_descriptive_facts_do_not_override_mathematical_returns(self):
        excellent = change_root(facts(price=10000.), "profile", rationale="Fictional excellent descriptive business context")
        mediocre = change_root(facts(price=1.), "profile", rationale="Fictional mediocre descriptive business context")
        self.assertLess(returns(build(excellent))[2], 0.)
        self.assertGreater(returns(build(mediocre))[0], 0.)
        same_price = change_root(mediocre, "price", value=10000.)
        self.assertEqual(returns(build(excellent)), returns(build(same_price)))

    def test_missing_policies_no_production_defaults(self):
        result = a.construct_expected_return(facts())
        for reason in ("MISSING_MATURE_GROWTH_POLICY", "MISSING_TERMINAL_VALUATION_POLICY", "MISSING_DISTRIBUTION_POLICY"):
            self.unavailable(result, reason)
        self.unavailable(build(mature_policy=None), "MISSING_MATURE_GROWTH_POLICY")
        self.unavailable(build(terminal_policy=None), "MISSING_TERMINAL_VALUATION_POLICY")

    def test_inapplicable_policy_unavailable(self):
        for key, reason in (("mature_policy", "MISSING_MATURE_GROWTH_POLICY"), ("terminal_policy", "MISSING_TERMINAL_VALUATION_POLICY"),
                            ("distribution_policy", "MISSING_DISTRIBUTION_POLICY")):
            original = policies()[key]
            for change in (dict(currency="USD"), dict(accounting_basis="US_GAAP"), dict(valid_through="2026-01-31")):
                with self.subTest(key=key, change=change):
                    self.unavailable(build(**{key: replace(original, applicability=replace(original.applicability, **change))}), reason)

    def test_policy_order_and_invalid_values_are_contract_errors(self):
        for key, field in (("mature_policy", "log_growth"), ("terminal_policy", "terminal_pe")):
            for values in (p.ScenarioValues(3., 1., 4.), p.ScenarioValues(1., math.nan, 3.), p.ScenarioValues(1., 2., math.inf)):
                with self.subTest(key=key, values=values), self.assertRaises(p.ConstructorContractError):
                    build(**{key: replace(policies()[key], **{field: values})})
        with self.assertRaises(p.ConstructorContractError):
            build(terminal_policy=replace(policies()["terminal_policy"], terminal_pe=p.ScenarioValues(-1., 2., 3.)))

    def test_policy_hash_covers_semantics_and_is_content_based(self):
        for original in policies().values():
            self.assertEqual(original.policy_hash, replace(original).policy_hash)
            for change in (dict(policy_id=original.policy_id + "-change"), dict(rationale="Different rationale"),
                           dict(assumption_id=original.assumption_id + "-change"),
                           dict(applicability=replace(original.applicability, valid_through="2027-12-31"))):
                self.assertNotEqual(original.policy_hash, replace(original, **change).policy_hash)
        original = policies()["terminal_policy"]
        self.assertNotEqual(original.policy_hash, replace(original, terminal_pe=replace(original.terminal_pe, bull=21.)).policy_hash)
        original = policies()["mature_policy"]
        self.assertNotEqual(original.policy_hash, replace(original, log_growth=replace(original.log_growth, bull=.2)).policy_hash)
        original = policies()["distribution_policy"]
        self.assertNotEqual(original.policy_hash, replace(original, rule=p.DistributionRule.CONSTANT_MATCHED_ORDINARY_PAYOUT).policy_hash)
        with patch.object(p, "HISTORICAL_FADE_WEIGHTS", (1., 1., .8, .5, .2, 0., 0.)):
            changed_hash = policies()["mature_policy"].policy_hash
        self.assertNotEqual(changed_hash, policies()["mature_policy"].policy_hash)

    def test_hash_ignores_dict_record_construction_order(self):
        original = policies()["terminal_policy"]
        parameters = {f.name: getattr(original, f.name) for f in reversed(fields(original))}
        self.assertEqual(original.policy_hash, p.TerminalValuationPolicy(**parameters).policy_hash)
        self.assertEqual(p.canonical_hash({"a": 1, "b": {"c": 2, "d": 3}}),
                         p.canonical_hash({"b": {"d": 3., "c": 2.}, "a": 1.}))

    def test_profile_gate_all_unsupported_and_unknown(self):
        for profile in a.Profile:
            if profile is a.Profile.ORDINARY_COMPOUNDER:
                continue
            with self.subTest(profile=profile):
                fixture = change_root(facts(), "profile", profile=profile, excluded_structures=())
                self.unavailable(build(fixture), "UNSUPPORTED_OR_MISSING_PROFILE")

    def test_positive_eps_without_qualification_not_admitted(self):
        self.unavailable(build(without(facts(), "profile")), "UNSUPPORTED_OR_MISSING_PROFILE")
        self.unavailable(build(change_root(facts(), "profile", excluded_structures=())), "AMBIGUOUS_PROFILE")

    def test_no_ticker_or_market_cap_gate(self):
        fixture = facts()
        fixture = replace(fixture, security_id="TINY_FICTIONAL_ISSUER", roots=tuple(
            replace(r, identity=replace(r.identity, security_id="TINY_FICTIONAL_ISSUER")) for r in fixture.roots))
        self.assertEqual(returns(build(fixture)), returns(build()))

    def test_chronology_failures_for_every_stage(self):
        cases = (
            dict(available_at="2027-01-01T00:00:00Z"),
            dict(captured_at="2027-01-01T00:00:00Z"),
            dict(published_at="2026-03-01T00:00:00Z"),
            dict(captured_at="2020-01-01T00:00:00Z"),
            dict(available_at="2020-01-01T00:00:00Z"),
        )
        for change in cases:
            with self.subTest(change=change), self.assertRaises(p.ConstructorContractError):
                build(change_provenance(facts(), "eps-2025", **change))

    def test_derived_nodes_never_predate_parents(self):
        result = build(facts(payer=True))
        by_id = {r.identity.observation_id: r.identity.provenance for r in result.input_roots}
        by_id.update({n.id: n for n in result.lineage})
        for child in result.lineage:
            for parent_id in child.parents:
                parent = by_id[parent_id]
                self.assertLessEqual(a._timestamp(parent.available_at), a._timestamp(child.available_at))
                self.assertLessEqual(a._timestamp(parent.captured_at), a._timestamp(child.captured_at))
            self.assertLessEqual(a._timestamp(child.captured_at), a._timestamp(AS_OF))

    def test_caller_derived_parent_later_than_child_rejected_at_boundary(self):
        parent = ForeignDerived("parent", "SYNTHETIC_REPORTED_DILUTED_EPS_V1", (), "2027-01-01T00:00:00Z")
        child = ForeignDerived("normalized_eps_growth", "DERIVED", (parent,))
        with self.assertRaisesRegex(p.ConstructorContractError, "caller-supplied transformation"):
            build(replace(facts(), roots=facts().roots + (child,)))

    def test_cyclic_caller_lineage_rejected_at_boundary(self):
        first = ForeignDerived("first", "DERIVED", ("second",))
        second = ForeignDerived("second", "DERIVED", ("first",))
        with self.assertRaisesRegex(p.ConstructorContractError, "caller-supplied transformation"):
            build(replace(facts(), roots=facts().roots + (first, second)))

    def test_prohibited_origins_cannot_be_renamed_into_derived_roots(self):
        prohibited = ("STOCK_PRICE_RETURN", "BENCHMARK_RETURN", "SECTOR_CAGR", "BETA", "SMA", "DRAWDOWN",
            "eps_growth_5y", "eps_growth_estimated_3_5y", "forward_eps_growth_direct", "PEG", "FAIR_VALUE",
            "PRICE_FAIR_VALUE", "VALUATION_SCORE", "SCORE", "CONVICTION", "DURABILITY_SCORE", "expected_cagr_quality",
            "OPPORTUNITY_COST", "RELIABILITY_ALLOCATION_CAP", "SIZING", "ALLOCATION", "PROXY_CALIBRATION")
        for origin in prohibited:
            root = ForeignDerived("innocuous", origin, ())
            renamed = ForeignDerived("normalized_eps_growth", "DERIVED", (ForeignDerived("middle", "DERIVED", (root,)),))
            with self.subTest(origin=origin), self.assertRaises(p.ConstructorContractError):
                build(replace(facts(), roots=facts().roots + (renamed,)))
            with self.subTest(adapter=origin), self.assertRaisesRegex(p.ConstructorContractError, "adapter mismatch"):
                build(change_provenance(facts(), "eps-2025", extractor_id=origin))

    def test_price_adapter_cannot_be_labelled_eps(self):
        with self.assertRaisesRegex(p.ConstructorContractError, "adapter mismatch"):
            build(change_provenance(facts(), "eps-2025", extractor_id=a.AdapterIdentity.SYNTHETIC_OBSERVED_PRICE_V1))

    def test_duplicate_ids_and_economic_wrappers_rejected(self):
        fixture = facts()
        for duplicate in (fixture.roots[0], replace(fixture.roots[0], identity=replace(fixture.roots[0].identity, observation_id="wrapper"))):
            with self.assertRaisesRegex(p.ConstructorContractError, "Duplicate"):
                build(replace(fixture, roots=fixture.roots + (duplicate,)))

    def test_shared_evidence_exposed_not_counted_twice(self):
        result = build()
        components = dict(result.component_root_ids)
        self.assertEqual(set(components["fundamental"]) & set(components["growth"]), {"eps-2023", "eps-2024", "eps-2025"})
        self.assertTrue({"eps-2023", "eps-2024", "eps-2025"} <= set(result.shared_evidence_roots))
        self.assertEqual(len(result.shared_evidence_roots), len(set(result.shared_evidence_roots)))

    def test_lineage_hash_binds_locator_and_document_hash(self):
        baseline = build()
        for change in (dict(source_locator="changed-table-row"), dict(source_document_hash="a" * 64)):
            result = build(change_provenance(facts(), "eps-2025", **change))
            self.assertNotEqual(baseline.lineage_hash, result.lineage_hash)
            self.assertNotEqual(node(baseline, "MEDIAN_LATEST_THREE_DILUTED_EPS_V1").id,
                                node(result, "MEDIAN_LATEST_THREE_DILUTED_EPS_V1").id)
            self.assertEqual(returns(baseline), returns(result))

    def test_stable_transformation_ids_and_transitive_root_closure(self):
        result = build(facts(payer=True))
        by_id = {n.id: n for n in result.lineage}
        root_ids = {r.identity.observation_id for r in result.input_roots}
        def roots_of(identifier, active=frozenset()):
            self.assertNotIn(identifier, active)
            if identifier in root_ids:
                return {identifier}
            return set().union(*(roots_of(parent, active | {identifier}) for parent in by_id[identifier].parents))
        for n in result.lineage:
            self.assertIn("V1", n.transformation_id)
            self.assertEqual(set(n.root_ids), roots_of(n.id))
        self.assertEqual(result.lineage, build(facts(payer=True)).lineage)

    def test_confidence_exact_mapping_and_forecast_ceilings(self):
        result = build()
        self.assertEqual(result.request.confidence, er.ConfidenceComponents("HIGH", "LOW", "LOW", "LOW"))
        for assessment in result.confidence:
            self.assertEqual(assessment.category, min((assessment.source_authority, assessment.freshness,
                assessment.completeness, assessment.consistency, assessment.assumption_dependence), key=er.CONFIDENCE_ORDER.index))
        self.assertEqual(result.diagnostic.confidence, result.request.confidence)

    def test_weak_evidence_changes_confidence_not_returns_or_cash_flows(self):
        for payer in (False, True):
            strong, weak = build(facts(payer=payer)), build(facts(payer=payer, weak=True))
            self.assertEqual(returns(strong), returns(weak))
            for left, right in zip(strong.request.scenarios, weak.request.scenarios):
                self.assertEqual(left.growth_rates, right.growth_rates)
                self.assertEqual(left.dividends_per_share, right.dividends_per_share)
                self.assertEqual(left.terminal_pe, right.terminal_pe)
            self.assertEqual(weak.request.confidence.fundamental, "LOW")
            self.assertEqual(weak.diagnostic.confidence, weak.request.confidence)

    def test_freshness_thresholds_are_deterministic(self):
        for observed, expected in (("2026-06-23", "HIGH"), ("2026-06-22", "MEDIUM"), ("2026-05-31", "MEDIUM"), ("2026-05-30", "LOW")):
            result = build(change_root(facts(), "price", observed_on=observed))
            self.assertEqual(result.request.confidence.fundamental, expected)
            self.assertEqual(result.diagnostic.confidence.fundamental, expected)
            self.assertEqual(returns(result), returns(build()))

    def test_completeness_and_consistency_fail_closed_not_averaged(self):
        self.unavailable(build(without(facts(), "eps-2024")), "MISSING_EPS_SEQUENCE")
        with self.assertRaises(p.ConstructorContractError):
            build(change_root(facts(), "eps-2024", basis=replace(BASIS, share_basis="CONFLICT")))
        self.assertNotIn("confidence_score", {f.name for f in fields(a.ConfidenceAssessment)})

    def test_extreme_growth_not_clipped(self):
        original = policies()["mature_policy"]
        result = build(mature_policy=replace(original, log_growth=p.ScenarioValues(1000., 1001., 1002.)))
        self.unavailable(result, "UNREPRESENTABLE_GROWTH_PATH")
        result = build(mature_policy=replace(original, log_growth=p.ScenarioValues(-1002., -1001., -1000.)))
        self.unavailable(result, "UNREPRESENTABLE_GROWTH_PATH")

    def test_payer_underflow_is_unavailable_not_silent_zero(self):
        tiny = float.fromhex("0x0.0000000000001p-1022")
        fixture = change_root(facts(eps=(1e100,) * 5, payer=True), "dividend", value=tiny)
        self.unavailable(build(fixture), "UNREPRESENTABLE_PAYOUT")
        fixture = change_root(facts(eps=(1., .5, .25, .125, .0625), payer=True), "dividend", value=tiny)
        self.unavailable(build(fixture), "UNREPRESENTABLE_DIVIDEND_PATH")

    def test_terminal_overflow_translates_only_pr4a_numerical_error(self):
        policy = replace(policies()["terminal_policy"], terminal_pe=p.ScenarioValues(1e308, 1e308, 1e308))
        self.unavailable(build(terminal_policy=policy), "UNREPRESENTABLE_PR4A_CALCULATION")
        with patch.object(er, "calculate_expected_return", side_effect=er.ExpectedReturnError("synthetic contract bug")):
            with self.assertRaisesRegex(er.ExpectedReturnError, "synthetic contract bug"):
                build()

    def test_programming_bugs_not_swallowed_as_unavailable(self):
        with patch.object(er, "calculate_expected_return", side_effect=RuntimeError("synthetic bug")):
            with self.assertRaisesRegex(RuntimeError, "synthetic bug"):
                build()

    def test_closed_immutable_contract_no_dict_or_pr4a_evidence(self):
        with self.assertRaises(p.ConstructorContractError):
            a.construct_expected_return(asdict(facts()))
        with self.assertRaises(p.ConstructorContractError):
            build(replace(facts(), roots=list(facts().roots)))
        with self.assertRaises(p.ConstructorContractError):
            build(replace(facts(), roots=(build().request.evidence[0],)))
        with self.assertRaises(FrozenInstanceError):
            facts().as_of = "changed"
        with self.assertRaises(FrozenInstanceError):
            policies()["mature_policy"].rationale = "changed"
        with self.assertRaises(FrozenInstanceError):
            build().lineage_hash = "changed"

    def test_malformed_scalar_and_identity_contracts(self):
        for value in (True, math.nan, math.inf, "3", 10 ** 1000):
            with self.subTest(value=repr(value)[:30]), self.assertRaises(p.ConstructorContractError):
                build(change_root(facts(), "eps-2025", value=value))
        for change in (dict(source_document_hash="fake"), dict(source_locator=""), dict(extractor_version="2"),
                       dict(source_kind="OFFICIAL_CURRENT_DATA"), dict(published_at="2026-01-01")):
            with self.subTest(change=change), self.assertRaises(p.ConstructorContractError):
                build(change_provenance(facts(), "eps-2025", **change))

    def test_impossible_period_and_future_observation_rejected(self):
        for period in (a.AnnualPeriod("2025-01-01", "2025-06-30"), a.AnnualPeriod("2026-01-01", "2026-12-31")):
            with self.assertRaises(p.ConstructorContractError):
                build(change_root(facts(), "eps-2025", period=period))
        with self.assertRaises(p.ConstructorContractError):
            build(change_root(facts(), "price", observed_on="2027-01-01"))

    def test_hash_seed_and_locale_independent_semantic_serialization(self):
        # Child only loads pure modules through a synthetic src package, avoiding
        # src.__init__'s legacy runtime activation entirely.
        code = '''import sys, types, json
from pathlib import Path
from dataclasses import asdict
package = types.ModuleType("src")
package.__path__ = [str(Path.cwd() / "src")]
sys.modules["src"] = package
from tests.expected_return_assumption_fixtures import facts, policies
from src.expected_return_assumptions import construct_expected_return
result = construct_expected_return(facts(), **policies())
print(json.dumps(asdict(result), sort_keys=True, default=lambda x: x.value, separators=(",", ":")))
'''
        outputs = []
        for seed, locale in (("1", "C"), ("987", "en_US.UTF-8")):
            proc = subprocess.run([sys.executable, "-B", "-c", code], cwd=Path(a.__file__).resolve().parents[1],
                env={"PYTHONHASHSEED": seed, "LANG": locale, "TZ": "UTC" if seed == "1" else "Pacific/Auckland"},
                check=True, capture_output=True, text=True)
            outputs.append(proc.stdout)
        self.assertEqual(*outputs)


class IsolationTests(unittest.TestCase):
    def test_exact_static_dependency_allowlists_and_forbidden_calls(self):
        allowed = {
            a: {"__future__", "dataclasses", "datetime", "enum", "math", "re", "statistics", "expected_return_policy", None},
            p: {"__future__", "dataclasses", "datetime", "enum", "hashlib", "json", "math"},
        }
        forbidden = {"now", "today", "open", "read_text", "read_bytes", "write_text", "getenv", "environ",
                     "random", "eval", "exec", "__import__", "import_module", "compile"}
        for module, expected in allowed.items():
            tree = ast.parse(Path(module.__file__).read_text())
            imports = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
            imports.update(alias.name for n in ast.walk(tree) if isinstance(n, ast.Import) for alias in n.names)
            self.assertEqual(imports, expected)
            for n in ast.walk(tree):
                if isinstance(n, ast.ImportFrom) and n.module is None:
                    self.assertEqual([(alias.name, alias.asname) for alias in n.names], [("expected_return_engine", "er")])
                    self.assertEqual(n.level, 1)
                if isinstance(n, ast.Call):
                    name = n.func.attr if isinstance(n.func, ast.Attribute) else n.func.id if isinstance(n.func, ast.Name) else ""
                    self.assertNotIn(name, forbidden)
        self.assertNotIn("expected_return_engine", Path(p.__file__).read_text())

    def test_no_existing_investment_or_pit_consumer(self):
        root = Path(a.__file__).resolve().parents[1]
        for path in (root / "main.py", *sorted((root / "src").rglob("*.py")), *sorted((root / "pit_comparison").rglob("*.py"))):
            if path in (Path(a.__file__), Path(p.__file__)):
                continue
            source = path.read_text()
            self.assertNotIn("expected_return_assumptions", source, str(path))
            self.assertNotIn("expected_return_policy", source, str(path))

    def test_rules_and_calculator_versions_unchanged(self):
        root = Path(a.__file__).resolve().parents[1]
        self.assertIn('MODEL_RULES_VERSION = "2026-08-23-allocation-room-integrity-v7"', (root / "src/model_version.py").read_text())
        self.assertEqual(er.EXPECTED_RETURN_METHODOLOGY_VERSION, "2026-09-08-normalized-eps-cashflow-irr-v1")
        self.assertNotEqual(a.EXPECTED_RETURN_CONSTRUCTOR_VERSION, a.EXPECTED_RETURN_FACTS_CONTRACT_VERSION)
        self.assertNotEqual(p.EXPECTED_RETURN_TERMINAL_POLICY_SCHEMA_VERSION, p.EXPECTED_RETURN_ASSUMPTION_POLICY_SCHEMA_VERSION)


if __name__ == "__main__":
    unittest.main()
