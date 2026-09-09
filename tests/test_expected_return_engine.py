"""Synthetic economic identities and contract checks; no operational inputs."""
import ast
import copy
from dataclasses import FrozenInstanceError, fields, replace
import json
import math
from pathlib import Path
import unittest
from unittest.mock import patch

from src import expected_return_engine as er


STAMP = "2026-09-08T12:00:00Z"
BASIS = "SYNTHETIC_COMMON_SHARE_SPLIT_BASIS"


def request_fixture(*, price=100.0, eps=10.0, growth=(0.0,) * 7,
                    dividends=(0.0,) * 7, terminal_pe=10.0):
    """An explicitly qualified fictitious company, with no provider acquisition."""
    evidence = (
        er.Evidence("price", "current_price", price, "CURRENCY_PER_SHARE", "MARKET_PROVIDER",
            "synthetic:price", "fixture-v1", STAMP, STAMP, STAMP, "CURRENT", "HIGH",
            currency="USD", share_basis=BASIS),
        er.Evidence("eps", "normalized_diluted_eps", eps, "CURRENCY_PER_SHARE", "OFFICIAL_CURRENT_DATA",
            "synthetic:normalized-eps", "fixture-v1", STAMP, STAMP, STAMP, "CURRENT", "HIGH",
            currency="USD", share_basis=BASIS, period_start="2025-01-01", period_end="2025-12-31",
            accounting_basis=er.SUPPORTED_METRIC),
    )
    assumptions, scenarios = [], []
    for name in er.SCENARIOS:
        for component, value in (("growth", growth), ("distributions", dividends), ("terminal_valuation", terminal_pe)):
            assumptions.append(er.Assumption(f"{name}-{component}", component, name,
                "Explicit synthetic assumption; no forecast accuracy claim.", er.EXPECTED_RETURN_METHODOLOGY_VERSION,
                supporting_evidence_ids=("eps",), value=value))
        scenarios.append(er.Scenario(name, eps, growth, dividends, terminal_pe, "USD", BASIS,
            er.References(evidence_ids=("eps",)),
            er.References(assumption_ids=(f"{name}-growth",)),
            er.References(assumption_ids=(f"{name}-distributions",)),
            er.References(assumption_ids=(f"{name}-terminal_valuation",))))
    return er.ExpectedReturnRequest(er.EXPECTED_RETURN_SCHEMA_VERSION,
        er.EXPECTED_RETURN_METHODOLOGY_VERSION, STAMP, er.SUPPORTED_PROFILE, er.SUPPORTED_METRIC,
        "USD", BASIS, 7, price, "price", tuple(scenarios),
        er.ConfidenceComponents("HIGH", "HIGH", "HIGH", "HIGH"), evidence, tuple(assumptions))


def alter_scenario(request, name="base", **changes):
    """Change both the economic value and its explicitly recorded assumption."""
    scenarios = tuple(replace(s, **changes) if s.name == name else s for s in request.scenarios)
    mapping = {"growth_rates": "growth", "dividends_per_share": "distributions", "terminal_pe": "terminal_valuation"}
    assumptions = []
    for assumption in request.assumptions:
        for field, component in mapping.items():
            if field in changes and assumption.scenario == name and assumption.component == component:
                assumption = replace(assumption, value=changes[field])
        assumptions.append(assumption)
    return replace(request, scenarios=scenarios, assumptions=tuple(assumptions))


def returns(request):
    return tuple(s.annualized_return for s in er.calculate_expected_return(request).scenarios)


class ExpectedReturnMathematicsTests(unittest.TestCase):
    def test_flat_eps_unchanged_multiple_zero_dividends(self):
        self.assertAlmostEqual(returns(request_fixture())[1], 0.0, delta=2e-14)

    def test_ten_percent_growth_identity(self):
        result = er.calculate_expected_return(request_fixture(growth=(0.1,) * 7))
        self.assertAlmostEqual(result.scenarios[1].annualized_return, 0.1, delta=2e-14)
        self.assertAlmostEqual(result.scenarios[1].terminal_eps_per_share, 10 * 1.1**7)

    def test_multiple_contraction(self):
        value = returns(request_fixture(terminal_pe=5))[1]
        self.assertLess(value, 0)
        self.assertAlmostEqual(value, 0.5**(1 / 7) - 1, delta=2e-14)

    def test_multiple_expansion(self):
        value = returns(request_fixture(terminal_pe=20))[1]
        self.assertGreater(value, 0)
        self.assertAlmostEqual(value, 2**(1 / 7) - 1, delta=2e-14)

    def test_no_dividend_irr_matches_independent_terminal_cagr(self):
        for growth, pe in (((-.2, .1, .03, .04, .05, .06, .07), 13), ((.4,) * 7, 25), ((-.4,) * 7, 2)):
            with self.subTest(growth=growth, pe=pe):
                fixture = request_fixture(growth=growth, terminal_pe=pe)
                expected = (10 * math.prod(1 + g for g in growth) * pe / 100)**(1 / 7) - 1
                self.assertAlmostEqual(returns(fixture)[1], expected, delta=2e-14)

    def test_precomputed_nonzero_dividend_fixture(self):
        # Price 100, seven annual cash dividends of 8 and terminal price 100:
        # the geometric annuity identity gives an IRR of exactly 8%.
        fixture = request_fixture(dividends=(8.0,) * 7)
        self.assertAlmostEqual(returns(fixture)[1], .08, delta=2e-14)

    def test_independent_npv_substitution_for_varying_dividends(self):
        fixture = request_fixture(growth=(.07, .09, .04, -.01, .03, .02, .02),
                                  dividends=(0., 1., 2., 1., 3., 4., 5.), terminal_pe=14)
        r = returns(fixture)[1]
        terminal = 10 * math.prod(1 + g for g in fixture.scenarios[1].growth_rates) * 14
        pv = sum(d / (1 + r)**year for year, d in enumerate(fixture.scenarios[1].dividends_per_share, 1))
        pv += terminal / (1 + r)**7
        self.assertAlmostEqual(pv, 100, delta=1e-10)

    def test_dividends_increase_return(self):
        self.assertGreater(returns(request_fixture(dividends=(2.,) * 7))[1], returns(request_fixture())[1])

    def test_higher_purchase_price_lowers_return(self):
        self.assertLess(returns(request_fixture(price=120))[1], returns(request_fixture(price=100))[1])

    def test_higher_terminal_multiple_raises_return(self):
        self.assertGreater(returns(request_fixture(terminal_pe=12))[1], returns(request_fixture(terminal_pe=10))[1])

    def test_higher_growth_raises_return(self):
        self.assertGreater(returns(request_fixture(growth=(.05,) * 7))[1], returns(request_fixture(growth=(.03,) * 7))[1])

    def test_larger_dividends_raise_return(self):
        self.assertGreater(returns(request_fixture(dividends=(3.,) * 7))[1], returns(request_fixture(dividends=(2.,) * 7))[1])

    def test_currency_rescaling_preserves_return(self):
        original = request_fixture(growth=(.04,) * 7, dividends=(2.,) * 7)
        scaled = request_fixture(price=150, eps=15, growth=(.04,) * 7, dividends=(3.,) * 7)
        scaled = replace(scaled, currency="CAD",
            scenarios=tuple(replace(s, currency="CAD") for s in scaled.scenarios),
            evidence=tuple(replace(e, currency="CAD") for e in scaled.evidence))
        self.assertAlmostEqual(returns(original)[1], returns(scaled)[1], delta=2e-14)

    def test_extreme_negative_return_is_above_minus_one(self):
        result = returns(request_fixture(growth=(-.9,) * 7, terminal_pe=.001))[1]
        self.assertGreater(result, -1)
        self.assertLess(result, -.95)

    def test_valid_small_and_large_currency_scales(self):
        for scale in (1e-200, 1e200):
            with self.subTest(scale=scale):
                r = returns(request_fixture(price=100*scale, eps=10*scale, dividends=(8*scale,) * 7))[1]
                self.assertAlmostEqual(r, .08, delta=1e-12)

    def test_nonconvergence_raises_numerical_error(self):
        with patch.object(er, "_MAX_ITERATIONS", 0):
            with self.assertRaisesRegex(er.ExpectedReturnNumericalError, "did not converge"):
                er.calculate_expected_return(request_fixture())

    def test_numerical_overflow_and_underflow_raise(self):
        for fixture in (request_fixture(eps=1e300, growth=(1e100,) * 7),
                        request_fixture(eps=1e-300, growth=(-.999999,) * 7),
                        request_fixture(eps=1e300, terminal_pe=1e100)):
            with self.subTest(fixture=fixture.scenarios[0]):
                with self.assertRaises(er.ExpectedReturnNumericalError):
                    er.calculate_expected_return(fixture)

    def test_unrepresentable_negative_root_raises(self):
        with self.assertRaises(er.ExpectedReturnNumericalError):
            er.calculate_expected_return(request_fixture(price=1e300, eps=1e-100))


class ExpectedReturnContractTests(unittest.TestCase):
    def test_identity_and_nested_json_output(self):
        result = er.calculate_expected_return(request_fixture())
        self.assertEqual(er.EXPECTED_RETURN_METHODOLOGY_VERSION, "2026-09-08-normalized-eps-cashflow-irr-v1")
        self.assertEqual(er.EXPECTED_RETURN_SCHEMA_VERSION, "2026-09-08-expected-return-diagnostic-v1")
        self.assertEqual(result.authority, "DIAGNOSTIC_ONLY")
        self.assertEqual(result.status, "AVAILABLE")
        self.assertEqual(result.horizon_years, 7)
        self.assertEqual(result.return_basis, "NOMINAL_PRETAX_EQUITY_CASHFLOW_IRR")
        self.assertEqual(result.fx_basis, "CONSTANT_FX")
        payload = result.to_dict()
        self.assertEqual(set(payload), {"expected_return_diagnostic"})
        self.assertEqual(tuple(payload["expected_return_diagnostic"]["scenarios"]), er.SCENARIOS)
        json.dumps(payload, allow_nan=False)

    def test_wrong_versions_rejected(self):
        for key in ("schema_version", "methodology_version"):
            with self.subTest(key=key), self.assertRaises(er.ExpectedReturnError):
                er.calculate_expected_return(replace(request_fixture(), **{key: "unknown"}))

    def test_horizon_exactly_seven_integer(self):
        for value in (5, 10, 7.0, True, "7", None):
            with self.subTest(value=value), self.assertRaises(er.ExpectedReturnError):
                er.calculate_expected_return(replace(request_fixture(), horizon_years=value))

    def test_unsupported_profiles_and_metric_unavailable(self):
        for profile in ("BANK", "INSURANCE", "REIT", "ASSET_MANAGER", "ALT_ASSET_MANAGER", "UTILITY",
                        "PIPELINE", "RESOURCES", "ENERGY_CYCLICAL", "TURNAROUND", "LOSS_MAKING", "UNKNOWN"):
            with self.subTest(profile=profile):
                result = er.calculate_expected_return(replace(request_fixture(), profile=profile))
                self.assertEqual(result.status, "UNAVAILABLE")
                self.assertIn("UNSUPPORTED_PROFILE:" + profile, result.unavailable_reasons)
                self.assertTrue(all(s.annualized_return is None for s in result.scenarios))
        self.assertEqual(er.calculate_expected_return(replace(request_fixture(), metric="FCF_PER_SHARE")).status, "UNAVAILABLE")

    def test_malformed_profile_rejected(self):
        for value in (None, 1, {}, "", "ordinary compounder", " BANK"):
            with self.subTest(value=value), self.assertRaises(er.ExpectedReturnError):
                er.calculate_expected_return(replace(request_fixture(), profile=value))

    def test_positive_price_eps_and_multiple_required(self):
        for value in (0, -1, True, "10"):
            with self.subTest(value=value):
                for key in ("current_price", "starting_eps_per_share", "terminal_pe"):
                    with self.subTest(key=key), self.assertRaises(er.ExpectedReturnError):
                        fixture = request_fixture()
                        fixture = replace(fixture, current_price=value) if key == "current_price" else alter_scenario(fixture, **{key: value})
                        er.calculate_expected_return(fixture)

    def test_missing_economics_unavailable(self):
        fixture = request_fixture()
        variants = [replace(fixture, current_price=None), replace(fixture, current_price_evidence_id=None),
                    alter_scenario(fixture, starting_eps_per_share=None), alter_scenario(fixture, growth_rates=None),
                    alter_scenario(fixture, dividends_per_share=None), alter_scenario(fixture, terminal_pe=None)]
        # Missing assumption values need no malformed assumption object.
        variants = [replace(v, assumptions=tuple(replace(a, rule="Explicit path unavailable") if a.value is None else a for a in v.assumptions)) for v in variants]
        for variant in variants:
            with self.subTest(variant=variant):
                result = er.calculate_expected_return(variant)
                self.assertEqual(result.status, "UNAVAILABLE")
                self.assertTrue(result.unavailable_reasons)

    def test_wrong_schedule_lengths_or_mutable_arrays_rejected(self):
        for field in ("growth_rates", "dividends_per_share"):
            for value in ((0.,) * 6, (0.,) * 8, [], [0.] * 7, "0000000"):
                with self.subTest(field=field, value=value), self.assertRaises(er.ExpectedReturnError):
                    er.calculate_expected_return(alter_scenario(request_fixture(), **{field: value}))

    def test_growth_and_dividend_domains(self):
        for field, value in (("growth_rates", (-1.,) * 7), ("growth_rates", (-2.,) * 7),
                             ("dividends_per_share", (-1.,) * 7)):
            with self.subTest(field=field, value=value), self.assertRaises(er.ExpectedReturnError):
                er.calculate_expected_return(alter_scenario(request_fixture(), **{field: value}))

    def test_nonfinite_and_boolean_values_rejected_everywhere(self):
        for value in (float("nan"), float("inf"), float("-inf"), True):
            for field in ("starting_eps_per_share", "terminal_pe", "growth_rates", "dividends_per_share"):
                with self.subTest(value=value, field=field), self.assertRaises(er.ExpectedReturnError):
                    er.calculate_expected_return(alter_scenario(request_fixture(), **{field: (value,) * 7 if field.endswith("rates") or field == "dividends_per_share" else value}))
            with self.assertRaises(er.ExpectedReturnError):
                er.calculate_expected_return(replace(request_fixture(), current_price=value))
            fixture = request_fixture()
            with self.assertRaises(er.ExpectedReturnError):
                er.calculate_expected_return(replace(fixture, evidence=(replace(fixture.evidence[0], value=value), fixture.evidence[1])))

    def test_malformed_timestamps_and_dates(self):
        for value in ("2026-09-08", "2026-09-08T12:00:00", "2026-02-30T00:00:00Z", "nonsense", 5):
            with self.subTest(value=value), self.assertRaises(er.ExpectedReturnError):
                er.calculate_expected_return(replace(request_fixture(), as_of=value))
        fixture = request_fixture()
        for changes in ({"period_end": "2026-02-30"}, {"period_start": "2026-01-01", "period_end": "2025-01-01"}):
            with self.subTest(changes=changes), self.assertRaises(er.ExpectedReturnError):
                er.calculate_expected_return(replace(fixture, evidence=(fixture.evidence[0], replace(fixture.evidence[1], **changes))))

    def test_future_availability_publication_capture_rejected(self):
        fixture = request_fixture()
        for field in ("available_at", "published_at", "captured_at"):
            with self.subTest(field=field), self.assertRaises(er.ExpectedReturnError):
                record = replace(fixture.evidence[1], **{field: "2026-09-09T12:00:00Z"})
                er.calculate_expected_return(replace(fixture, evidence=(fixture.evidence[0], record)))

    def test_future_forecast_target_allowed(self):
        fixture = request_fixture()
        forecast = replace(fixture.evidence[1], id="forward", field="forward_eps", period_start="2027-01-01", period_end="2027-12-31")
        modified = replace(fixture, evidence=fixture.evidence + (forecast,),
            assumptions=tuple(replace(a, supporting_evidence_ids=("forward",)) if a.component == "growth" else a for a in fixture.assumptions))
        self.assertEqual(returns(modified), returns(fixture))

    def test_duplicate_ids_and_dangling_links_rejected(self):
        fixture = request_fixture()
        variants = [replace(fixture, evidence=fixture.evidence + (fixture.evidence[0],)),
                    replace(fixture, assumptions=fixture.assumptions + (fixture.assumptions[0],)),
                    replace(fixture, current_price_evidence_id="missing"),
                    alter_scenario(fixture, growth_refs=er.References(assumption_ids=("missing",))),
                    alter_scenario(fixture, fundamental_refs=er.References(evidence_ids=("missing",))),
                    replace(fixture, assumptions=(replace(fixture.assumptions[0], supporting_evidence_ids=("missing",)),) + fixture.assumptions[1:]),
                    replace(fixture, evidence=(replace(fixture.evidence[0], parent_evidence_ids=("missing",)), fixture.evidence[1]))]
        for variant in variants:
            with self.subTest(variant=variant), self.assertRaises(er.ExpectedReturnError):
                er.calculate_expected_return(variant)

    def test_cyclic_provenance_rejected(self):
        fixture = request_fixture()
        cyclic = (replace(fixture.evidence[0], parent_evidence_ids=("eps",)), replace(fixture.evidence[1], parent_evidence_ids=("price",)))
        with self.assertRaisesRegex(er.ExpectedReturnError, "Cyclic"):
            er.calculate_expected_return(replace(fixture, evidence=cyclic))

    def test_wrong_reference_semantics_rejected(self):
        fixture = request_fixture()
        for variant in (alter_scenario(fixture, terminal_refs=er.References(assumption_ids=("bear-terminal_valuation",))),
                        alter_scenario(fixture, fundamental_refs=er.References(evidence_ids=("price",))),
                        replace(fixture, evidence=(replace(fixture.evidence[0], value=101), fixture.evidence[1])),
                        replace(fixture, assumptions=(replace(fixture.assumptions[0], value=(.5,) * 7),) + fixture.assumptions[1:])):
            with self.subTest(variant=variant), self.assertRaises(er.ExpectedReturnError):
                er.calculate_expected_return(variant)

    def test_missing_provenance_or_terminal_assumption_unavailable(self):
        for field in ("fundamental_refs", "growth_refs", "distribution_refs", "terminal_refs"):
            with self.subTest(field=field):
                result = er.calculate_expected_return(alter_scenario(request_fixture(), **{field: er.References()}))
                self.assertEqual(result.status, "UNAVAILABLE")

    def test_currency_share_and_accounting_basis_validation(self):
        fixture = request_fixture()
        for changes in ({"currency": "CAD"}, {"share_basis": "different"}, {"currency": "usd"}):
            with self.subTest(changes=changes), self.assertRaises(er.ExpectedReturnError):
                er.calculate_expected_return(alter_scenario(fixture, **changes))
        for changes in ({"accounting_basis": "BASIC_EPS"}, {"currency": "CAD"}, {"unit": "PERCENT"}):
            with self.subTest(changes=changes), self.assertRaises(er.ExpectedReturnError):
                er.calculate_expected_return(replace(fixture, evidence=(fixture.evidence[0], replace(fixture.evidence[1], **changes))))

    def test_malformed_scenario_records_rejected(self):
        fixture = request_fixture()
        for value in (fixture.scenarios[:2], (fixture.scenarios[0],) * 3, list(fixture.scenarios), ({},) * 3):
            with self.subTest(value=value), self.assertRaises(er.ExpectedReturnError):
                er.calculate_expected_return(replace(fixture, scenarios=value))

    def test_normal_order_and_crossed_returns_never_relabelled(self):
        fixture = alter_scenario(request_fixture(), "bear", terminal_pe=8)
        fixture = alter_scenario(fixture, "bull", terminal_pe=12)
        result = er.calculate_expected_return(fixture)
        self.assertEqual(tuple(s.name for s in result.scenarios), er.SCENARIOS)
        self.assertLess(result.scenarios[0].annualized_return, result.scenarios[1].annualized_return)
        crossed = alter_scenario(fixture, "bear", terminal_pe=30)
        with self.assertRaisesRegex(er.ExpectedReturnError, "returns cross"):
            er.calculate_expected_return(crossed)

    def test_confidence_changes_status_never_calculated_return(self):
        fixture = request_fixture(growth=(.1,) * 7)
        for level in ("MEDIUM", "LOW"):
            for component in er.COMPONENTS:
                with self.subTest(level=level, component=component):
                    modified = replace(fixture, confidence=replace(fixture.confidence, **{component: level}))
                    result = er.calculate_expected_return(modified)
                    self.assertEqual(result.status, "DEGRADED")
                    self.assertEqual(result.overall_confidence, level)
                    self.assertEqual(returns(modified), returns(fixture))

    def test_none_confidence_withholds_all_returns(self):
        for component in er.COMPONENTS:
            fixture = request_fixture()
            result = er.calculate_expected_return(replace(fixture, confidence=replace(fixture.confidence, **{component: "NONE"})))
            self.assertEqual(result.status, "UNAVAILABLE")
            self.assertEqual(result.overall_confidence, "NONE")
            self.assertTrue(all(s.annualized_return is None for s in result.scenarios))

    def test_invalid_confidence_rejected(self):
        for value in (80, "VERY_HIGH", None, []):
            with self.subTest(value=value), self.assertRaises(er.ExpectedReturnError):
                fixture = request_fixture()
                er.calculate_expected_return(replace(fixture, confidence=replace(fixture.confidence, growth=value)))

    def test_evidence_confidence_is_a_ceiling_not_return_haircut(self):
        fixture = request_fixture(growth=(.08,) * 7)
        changed = replace(fixture, evidence=(fixture.evidence[0], replace(fixture.evidence[1], reliability_status="LOW")))
        result = er.calculate_expected_return(changed)
        self.assertEqual(result.overall_confidence, "LOW")
        self.assertEqual(returns(changed), returns(fixture))

    def test_stale_unknown_and_unreliable_evidence(self):
        fixture = request_fixture()
        for changes, status in (({"freshness_status": "STALE"}, "DEGRADED"),
                                ({"freshness_status": "UNKNOWN"}, "UNAVAILABLE"),
                                ({"reliability_status": "NONE"}, "UNAVAILABLE")):
            changed = replace(fixture, evidence=(fixture.evidence[0], replace(fixture.evidence[1], **changes)))
            self.assertEqual(er.calculate_expected_return(changed).status, status)

    def test_non_economic_metadata_changes_do_not_change_return(self):
        fixture = request_fixture(growth=(.05,) * 7)
        modified = replace(fixture, evidence=tuple(replace(e, source_reference="synthetic:alternate", source_version="v2") for e in fixture.evidence),
                           assumptions=tuple(replace(a, rationale="Another explicit rationale.") for a in fixture.assumptions))
        self.assertEqual(returns(modified), returns(fixture))

    def test_immutability_success_unavailable_failure(self):
        for fixture in (request_fixture(), replace(request_fixture(), profile="BANK"),
                        alter_scenario(request_fixture(), terminal_pe=-1)):
            before = copy.deepcopy(fixture)
            try:
                er.calculate_expected_return(fixture)
            except er.ExpectedReturnError:
                pass
            self.assertEqual(fixture, before)
            with self.assertRaises(FrozenInstanceError):
                fixture.current_price = 123
            with self.assertRaises(FrozenInstanceError):
                fixture.evidence[0].value = 123

    def test_serialization_does_not_expose_mutable_state(self):
        result = er.calculate_expected_return(request_fixture())
        before = result.to_dict()
        output = result.to_dict()
        output["expected_return_diagnostic"]["scenarios"]["base"]["growth_rates"][0] = 9
        self.assertEqual(result.to_dict(), before)

    def test_repetition_and_input_order_are_deterministic(self):
        fixture = request_fixture()
        # Reverse record order, scenario order and reference insertion order.
        evidence = fixture.evidence + (replace(fixture.evidence[1], id="eps-copy"),)
        fixture = replace(fixture, evidence=evidence,
            assumptions=tuple(replace(a, supporting_evidence_ids=("eps", "eps-copy")) for a in fixture.assumptions))
        modified = replace(fixture, evidence=tuple(reversed(fixture.evidence)), scenarios=tuple(reversed(fixture.scenarios)),
            assumptions=tuple(replace(a, supporting_evidence_ids=tuple(reversed(a.supporting_evidence_ids))) for a in reversed(fixture.assumptions)))
        expected = er.calculate_expected_return(fixture)
        self.assertEqual(er.calculate_expected_return(modified), expected)
        self.assertEqual(er.calculate_expected_return(fixture).to_dict(), expected.to_dict())
        self.assertEqual(json.dumps(expected.to_dict()), json.dumps(er.calculate_expected_return(modified).to_dict()))

    def test_equivalent_timestamp_offsets_canonicalized(self):
        fixture = request_fixture()
        changed = replace(fixture, as_of="2026-09-08T08:00:00-04:00", evidence=tuple(replace(e,
            published_at="2026-09-08T08:00:00-04:00", available_at="2026-09-08T08:00:00-04:00",
            captured_at="2026-09-08T08:00:00-04:00") for e in fixture.evidence))
        self.assertEqual(er.calculate_expected_return(changed), er.calculate_expected_return(fixture))

    def test_strict_api_excludes_v1_and_additive_yield_fields(self):
        prohibited = {"expected_cagr_quality", "score_total", "conviction_score", "capital_allocation_score",
            "stock_cagr_3y", "stock_cagr_5y", "stock_cagr_10y", "sector_cagr_estimated", "peg_manual",
            "fair_value", "price_to_fair_value", "valuation_severity", "opportunity_cost_status",
            "long_term_durability_score", "allocations", "buyback_yield", "shareholder_yield", "dilution",
            "quality_multiplier", "durability_multiplier", "conviction_multiplier", "fair_value_upside"}
        for model in (er.ExpectedReturnRequest, er.Scenario):
            self.assertFalse(prohibited & {f.name for f in fields(model)})
        for key in prohibited:
            with self.subTest(key=key), self.assertRaises(TypeError):
                replace(request_fixture(), **{key: 100})
        with self.assertRaises(er.ExpectedReturnError):
            er.calculate_expected_return({"score_total": 10})

    def test_module_has_no_operational_imports_or_calls(self):
        # Source inspection only: no portfolio, research or runtime state is read.
        tree = ast.parse(Path(er.__file__).read_text())
        imports = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        imports.update(alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names)
        self.assertEqual(imports, {"__future__", "dataclasses", "datetime", "math", "re"})
        forbidden_calls = {"now", "today", "open", "read_text", "getenv", "environ", "random"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id if isinstance(node.func, ast.Name) else ""
                self.assertNotIn(name, forbidden_calls)

    def test_no_existing_investment_path_imports_new_module(self):
        root = Path(er.__file__).resolve().parents[1]
        for path in (root / "main.py", *sorted((root / "src").glob("*.py")),
                     *sorted((root / "pit_comparison").glob("*.py"))):
            if path.name == "expected_return_engine.py":
                continue
            self.assertNotIn("expected_return_engine", path.read_text(), str(path))

    def test_per_share_growth_has_no_second_dilution_adjustment(self):
        # Corporate earnings +21%, share count +10% => per-share EPS +10%.
        per_share_growth = 1.21 / 1.10 - 1
        self.assertAlmostEqual(returns(request_fixture(growth=(per_share_growth,) * 7))[1], .1, delta=2e-14)

    def test_rule_based_assumptions_are_retained_not_executed(self):
        fixture = request_fixture()
        assumptions = tuple(replace(a, value=None, rule="Qualified seven-year zero-growth schedule") if a.component == "growth" else a for a in fixture.assumptions)
        changed = replace(fixture, assumptions=assumptions)
        self.assertEqual(returns(changed), returns(fixture))
        self.assertIn("Qualified seven-year zero-growth schedule", repr(er.calculate_expected_return(changed).assumptions))

    def test_assumption_without_value_or_rule_is_malformed(self):
        fixture = request_fixture()
        with self.assertRaises(er.ExpectedReturnError):
            er.calculate_expected_return(replace(fixture, assumptions=(replace(fixture.assumptions[0], value=None),) + fixture.assumptions[1:]))

    def test_fundamental_assumption_requires_supporting_evidence(self):
        fixture = request_fixture()
        assumption = er.Assumption("base-normalization", "fundamental", "base", "Normalization", "fixture-v1", value=10.)
        changed = alter_scenario(fixture, fundamental_refs=er.References(assumption_ids=(assumption.id,)))
        changed = replace(changed, assumptions=changed.assumptions + (assumption,))
        self.assertEqual(er.calculate_expected_return(changed).status, "UNAVAILABLE")
        changed = replace(changed, assumptions=tuple(replace(a, supporting_evidence_ids=("eps",)) if a.id == assumption.id else a for a in changed.assumptions))
        self.assertEqual(er.calculate_expected_return(changed).status, "AVAILABLE")

    def test_evidence_cannot_replace_terminal_assumption(self):
        fixture = request_fixture()
        terminal = replace(fixture.evidence[1], id="terminal", field="terminal_pe", value=10., unit="MULTIPLE")
        changed = alter_scenario(fixture, terminal_refs=er.References(evidence_ids=(terminal.id,)))
        result = er.calculate_expected_return(replace(changed, evidence=changed.evidence + (terminal,)))
        self.assertEqual(result.status, "UNAVAILABLE")
        self.assertIn("MISSING_ASSUMPTION:base:terminal_valuation", result.unavailable_reasons)

    def test_noncanonical_timestamp_offset_rejected(self):
        with self.assertRaises(er.ExpectedReturnError):
            er.calculate_expected_return(replace(request_fixture(), as_of="2026-09-08T12:00:00+00:99"))

    def test_out_of_range_integer_is_contract_error(self):
        with self.assertRaises(er.ExpectedReturnError):
            er.calculate_expected_return(replace(request_fixture(), current_price=10**400))
        with self.assertRaises(er.ExpectedReturnNumericalError):
            er.calculate_expected_return(request_fixture(eps=10**300, growth=(10**300,) * 7))

    def test_unused_evidence_cannot_smuggle_mutability_or_nonfinite_values(self):
        fixture = request_fixture()
        for value in ([1, 2], {"x": 3}, (float("nan"),)):
            with self.subTest(value=value), self.assertRaises(er.ExpectedReturnError):
                extra = replace(fixture.evidence[1], id="extra", value=value)
                er.calculate_expected_return(replace(fixture, evidence=fixture.evidence + (extra,)))

    def test_validation_precedes_economic_unavailability(self):
        fixture = replace(request_fixture(), profile="BANK")
        with self.assertRaises(er.ExpectedReturnError):
            er.calculate_expected_return(replace(fixture, current_price=float("nan")))


class ExpectedReturnMaterialEvidenceTests(unittest.TestCase):
    def supported_by(self, field, component="growth", **metadata):
        fixture = request_fixture(growth=(.1,) * 7)
        record = replace(fixture.evidence[1], id="support", field=field, value=.12,
                         unit="DECIMAL_FRACTION", source_kind="MARKET_PROVIDER", **metadata)
        return replace(fixture, evidence=fixture.evidence + (record,),
            assumptions=tuple(replace(a, supporting_evidence_ids=(record.id,))
                              if a.component == component else a for a in fixture.assumptions))

    def assert_prohibited(self, fixture, field):
        before = copy.deepcopy(fixture)
        with self.assertRaisesRegex(er.ExpectedReturnError, "prohibited material Expected Return evidence") as raised:
            er.calculate_expected_return(fixture)
        self.assertIn(repr(field), str(raised.exception))
        self.assertEqual(fixture, before)

    def test_stock_cagr_cannot_qualify_growth(self):
        self.assert_prohibited(self.supported_by("stock_cagr_5y"), "stock_cagr_5y")

    def test_stock_cagr_cannot_qualify_through_derived_child(self):
        fixture = self.supported_by("stock_cagr_5y")
        child = replace(fixture.evidence[-1], id="child", field="per_share_eps_growth",
                        source_kind="DERIVED", parent_evidence_ids=("support",))
        grandchild = replace(child, id="grandchild", parent_evidence_ids=("child",))
        fixture = replace(fixture, evidence=fixture.evidence + (child, grandchild),
            assumptions=tuple(replace(a, supporting_evidence_ids=("grandchild",))
                              if a.component == "growth" else a for a in fixture.assumptions))
        self.assert_prohibited(fixture, "stock_cagr_5y")

    def test_v1_score_cannot_qualify_growth(self):
        self.assert_prohibited(self.supported_by("score_total"), "score_total")

    def test_v1_valuation_cannot_qualify_terminal_valuation(self):
        for field in ("peg_manual", "fair_value", "price_to_fair_value"):
            with self.subTest(field=field):
                self.assert_prohibited(self.supported_by(field, "terminal_valuation"), field)

    def test_existing_cagr_category_cannot_qualify_any_component(self):
        for component in er.COMPONENTS:
            with self.subTest(component=component):
                fixture = self.supported_by("expected_cagr_quality", component)
                if component == "fundamental":
                    assumption = er.Assumption("normalization", component, "base", "Synthetic normalization",
                        "fixture-v1", supporting_evidence_ids=("support",), value=10.)
                    fixture = alter_scenario(fixture, fundamental_refs=er.References(assumption_ids=(assumption.id,)))
                    fixture = replace(fixture, assumptions=fixture.assumptions + (assumption,))
                self.assert_prohibited(fixture, "expected_cagr_quality")

    def test_v1_fields_cannot_enter_material_evidence_graph(self):
        # Independent contract examples complement the strict typed-API test.
        fields_to_reject = {
            "stock_cagr_3y", "stock_cagr_5y", "stock_cagr_10y", "cagr_5y", "cagr_10y",
            "adjusted_stock_cagr_3y", "adjusted_stock_cagr_5y", "adjusted_stock_cagr_10y",
            "adjusted_cagr_5y", "adjusted_cagr_10y", "stock_return_1y", "adjusted_stock_return_1y",
            "sector_cagr_estimated", "benchmark_3y_cagr", "benchmark_5y_cagr", "benchmark_10y_cagr",
            "benchmark_usable_cagr", "benchmark_1y_return", "benchmark_return_1y",
            "expected_cagr_quality", "expected_cagr_quality_raw", "expected_cagr_quality_score",
            "score_total", "score_total_normalized", "conviction_score", "opportunity_cost_status",
            "opportunity_cost_score", "long_term_durability_score", "business_quality_score",
            "high_cagr_potential_score", "quality_cagr_intersection", "peg", "peg_manual", "fair_value",
            "price_to_fair_value", "valuation_severity", "valuation_score", "quality_but_too_expensive",
            "capital_allocation_score", "capital_allocation_score_low", "capital_allocation_score_high",
            "capital_allocation_components", "capital_allocation_confidence_range", "capital_allocation_confidence_label",
            "allocations", "allocation_weight", "montant", "pourcentage", "post_purchase_position_weight",
            "reliability_allocation_cap_percent", "reliability_allocation_cap_amount",
        }
        self.assertEqual(er.PROHIBITED_EXPECTED_RETURN_EVIDENCE_FIELDS, fields_to_reject)
        for field in sorted(fields_to_reject):
            with self.subTest(field=field):
                self.assert_prohibited(self.supported_by(field), field)

    def test_unreferenced_prohibited_evidence_does_not_affect_economics(self):
        fixture = request_fixture(growth=(.1,) * 7)
        expected = er.calculate_expected_return(fixture)
        for field in sorted(er.PROHIBITED_EXPECTED_RETURN_EVIDENCE_FIELDS):
            for reliability, freshness in (("HIGH", "CURRENT"), ("NONE", "UNKNOWN")):
                with self.subTest(field=field, reliability=reliability):
                    extra = replace(fixture.evidence[1], id="unreferenced", field=field,
                                    reliability_status=reliability, freshness_status=freshness)
                    unused = er.Assumption("unused", "growth", "base", "Descriptive only", "fixture-v1",
                                           supporting_evidence_ids=(extra.id,), value=(.2,) * 7)
                    result = er.calculate_expected_return(replace(fixture, evidence=fixture.evidence + (extra,),
                                                                  assumptions=fixture.assumptions + (unused,)))
                    self.assertEqual(result.scenarios, expected.scenarios)
                    self.assertEqual(result.confidence, expected.confidence)
                    self.assertEqual(result.overall_confidence, expected.overall_confidence)
                    self.assertEqual(result.status, expected.status)
                    self.assertEqual(result.warnings, expected.warnings)
                    self.assertEqual(result.unavailable_reasons, expected.unavailable_reasons)
                    self.assertIn(extra.id, {e.id for e in result.evidence})

    def test_legitimate_operating_evidence_still_qualifies_assumptions(self):
        fixture = request_fixture(growth=(.1,) * 7)
        expected = er.calculate_expected_return(fixture)
        examples = (
            ("revenue_growth", .12, "DECIMAL_FRACTION"),
            ("normalized_diluted_eps", (8., 9., 10.), "CURRENCY_PER_SHARE"),
            ("shares_outstanding", 1000000., "SHARES"),
            ("share_count_cagr_5y", .02, "DECIMAL_FRACTION"),
            ("dilution", .02, "DECIMAL_FRACTION"),
            ("dividends_per_share", 1., "CURRENCY_PER_SHARE"),
            ("net_margin", .2, "DECIMAL_FRACTION"),
            ("cash_flow", 1000000., "CURRENCY"),
            ("forward_eps", 11., "CURRENCY_PER_SHARE"),
            ("roe", .15, "DECIMAL_FRACTION"), ("roa", .08, "DECIMAL_FRACTION"),
        )
        for field, value, unit in examples:
            with self.subTest(field=field):
                record = replace(fixture.evidence[1], id="operating", field=field, value=value, unit=unit)
                changed = replace(fixture, evidence=fixture.evidence + (record,),
                    assumptions=tuple(replace(a, supporting_evidence_ids=(record.id,)) for a in fixture.assumptions))
                result = er.calculate_expected_return(changed)
                self.assertEqual(result.scenarios, expected.scenarios)
                self.assertEqual(result.confidence, expected.confidence)
                self.assertEqual(result.status, "AVAILABLE")

    def test_current_purchase_price_remains_valid(self):
        fixture = request_fixture()
        self.assertEqual(fixture.evidence[0].field, "current_price")
        result = er.calculate_expected_return(fixture)
        self.assertEqual(result.status, "AVAILABLE")
        self.assertEqual(result.current_price_evidence_id, "price")
        self.assertEqual(result.current_price, 100.)

    def test_purchase_price_prohibited_ancestor_is_rejected(self):
        fixture = self.supported_by("stock_cagr_5y")
        fixture = replace(fixture, assumptions=request_fixture(growth=(.1,) * 7).assumptions,
            evidence=(replace(fixture.evidence[0], parent_evidence_ids=("support",)),) + fixture.evidence[1:])
        self.assert_prohibited(fixture, "stock_cagr_5y")

    def test_direct_component_evidence_prohibited_ancestor_is_rejected(self):
        for component in er.COMPONENTS:
            with self.subTest(component=component):
                fixture = request_fixture()
                parent = replace(fixture.evidence[1], id="parent", field="score_total")
                # A correctly named direct record cannot launder a forbidden parent.
                mapping = {
                    "fundamental": ("fundamental_refs", "normalized_diluted_eps", 10., "CURRENCY_PER_SHARE"),
                    "growth": ("growth_refs", "per_share_eps_growth", (0.,) * 7, "DECIMAL_FRACTION"),
                    "distributions": ("distribution_refs", "dividends_per_share", (0.,) * 7, "CURRENCY_PER_SHARE"),
                    "terminal_valuation": ("terminal_refs", "terminal_pe", 10., "MULTIPLE"),
                }
                ref_field, field, value, unit = mapping[component]
                child = replace(fixture.evidence[1], id="direct", field=field, value=value, unit=unit,
                                source_kind="DERIVED", parent_evidence_ids=(parent.id,))
                old_refs = getattr(fixture.scenarios[1], ref_field)
                fixture = alter_scenario(fixture, **{ref_field: replace(old_refs, evidence_ids=(child.id,))})
                self.assert_prohibited(replace(fixture, evidence=fixture.evidence + (parent, child)), "score_total")

    def test_prohibited_evidence_rejected_regardless_of_source_or_confidence(self):
        for source in sorted(er.SOURCE_KINDS):
            for level in er.CONFIDENCE_ORDER:
                with self.subTest(source=source, level=level):
                    fixture = self.supported_by("score_total")
                    fixture = replace(fixture, confidence=replace(fixture.confidence, growth=level),
                        evidence=fixture.evidence[:-1] + (replace(fixture.evidence[-1], source_kind=source,
                            reliability_status=level, freshness_status="UNKNOWN" if level == "NONE" else "CURRENT"),))
                    self.assert_prohibited(fixture, "score_total")

    def test_prohibited_evidence_not_hidden_by_economic_unavailability(self):
        fixture = replace(self.supported_by("stock_cagr_5y"), profile="BANK", current_price=None)
        self.assert_prohibited(fixture, "stock_cagr_5y")

    def test_prohibited_field_case_aliases_rejected(self):
        for field in ("STOCK_CAGR_5Y", "Score_Total", "PEG_MANUAL"):
            with self.subTest(field=field):
                self.assert_prohibited(self.supported_by(field), field)

    def test_prohibited_error_is_deterministic_across_provenance_order(self):
        fixture = self.supported_by("stock_cagr_5y")
        other = replace(fixture.evidence[-1], id="other", field="score_total")
        fixture = replace(fixture, evidence=fixture.evidence + (other,),
            assumptions=tuple(replace(a, supporting_evidence_ids=("support", "other"))
                              if a.component == "growth" else a for a in fixture.assumptions))
        reversed_fixture = replace(fixture, evidence=tuple(reversed(fixture.evidence)),
            scenarios=tuple(reversed(fixture.scenarios)),
            assumptions=tuple(replace(a, supporting_evidence_ids=tuple(reversed(a.supporting_evidence_ids)))
                              for a in reversed(fixture.assumptions)))
        messages = []
        for variant in (fixture, reversed_fixture):
            with self.assertRaises(er.ExpectedReturnError) as raised:
                er.calculate_expected_return(variant)
            messages.append(str(raised.exception))
        self.assertEqual(messages[0], messages[1])


if __name__ == "__main__":
    unittest.main()
