from dataclasses import FrozenInstanceError, fields, replace
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_EVEN, ROUND_UP, localcontext
import ast
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from economic_facts import vfv_current_evidence as evidence
from src import expected_return_engine as company_er
from src import vfv_forward_er_policy as policy_module
from src import vfv_forward_expected_return as vfv_er
from tests.test_expected_return_engine import request_fixture
from tests.vfv_current_evidence_fixtures import publish_bundle, request_for


EXPECTED_POLICY_HASH = (
    "31dbebd0545c233c4913dad1915dfd2eb23d91481019fec078b245541ef0e645"
)


class VFVForwardExpectedReturnTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name).resolve() / "vfv"
        archive, product, etf, factsheet = publish_bundle(root)
        self.qualification = evidence.qualify_vfv_current_evidence(
            archive, request_for(archive, product, etf, factsheet))
        self.assertIs(
            self.qualification.status,
            evidence.VFVCurrentEvidenceStatus.AVAILABLE,
        )

    def request(self, qualification=None, **changes):
        qualification = qualification or self.qualification
        policy = policy_module.get_approved_vfv_forward_er_policy()
        values = {
            "instrument": "VFV",
            "analytical_basis": vfv_er.VFV_FORWARD_ER_ANALYTICAL_BASIS,
            "expected_upstream_semantic_id": qualification.semantic_id,
            "expected_upstream_evidence_id": qualification.evidence_id,
            "expected_policy_id": policy.policy_id,
            "expected_policy_hash": policy.content_hash,
        }
        values.update(changes)
        return vfv_er.VFVForwardERRequest(**values)

    def calculate(self, qualification=None, **request_changes):
        qualification = qualification or self.qualification
        return vfv_er.calculate_vfv_forward_expected_return(
            qualification, self.request(qualification, **request_changes))

    def with_facts(self, *, price=None, pe=None, yield_percent=None,
                   management_fee=None, mer=None, ter=None):
        qualification = self.qualification
        market = qualification.market_observation
        valuation = qualification.trailing_valuation
        distributions = qualification.distributions
        expenses = qualification.expenses
        if price is not None:
            market = replace(market, market_price=Decimal(price))
        if pe is not None:
            valuation = replace(valuation, weighted_pe=Decimal(pe))
        if yield_percent is not None:
            distributions = replace(
                distributions,
                trailing_distribution_yield=Decimal(yield_percent),
            )
        expense_changes = {}
        if management_fee is not None:
            expense_changes["management_fee"] = Decimal(management_fee)
        if mer is not None:
            expense_changes["mer"] = Decimal(mer)
        if ter is not None:
            expense_changes["ter"] = Decimal(ter)
        if expense_changes:
            expenses = replace(expenses, **expense_changes)
        return replace(
            qualification,
            market_observation=market,
            trailing_valuation=valuation,
            distributions=distributions,
            expenses=expenses,
        )

    def test_fixed_policy_identity_hash_and_exact_scenarios(self):
        policy = policy_module.get_approved_vfv_forward_er_policy()
        self.assertEqual(policy.policy_id,
                         "PAM_VFV_FORWARD_ER_POLICY_2026_10_01_V1")
        self.assertEqual(policy.methodology_id,
                         "2026-10-01-vfv-normalized-unit-cashflow-irr-v1")
        self.assertEqual(policy.content_hash, EXPECTED_POLICY_HASH)
        self.assertEqual(policy.horizon_years, 7)
        self.assertEqual(
            tuple((item.name, item.fundamental_growth,
                   item.terminal_weighted_pe) for item in policy.scenarios),
            (("bear", Decimal("0.00"), Decimal("12")),
             ("base", Decimal("0.03"), Decimal("16")),
             ("bull", Decimal("0.05"), Decimal("20"))),
        )
        json.loads(policy.canonical_json)
        with self.assertRaises(FrozenInstanceError):
            policy.horizon_years = 8

    def test_policy_content_change_changes_hash(self):
        policy = policy_module.get_approved_vfv_forward_er_policy()
        changed = replace(
            policy,
            scenarios=(replace(policy.scenarios[0], fundamental_growth=Decimal("0.01")),
                       *policy.scenarios[1:]),
        )
        self.assertNotEqual(changed.content_hash, policy.content_hash)

    def test_request_has_pins_but_no_caller_scenario_numbers_or_approval_boolean(self):
        names = {field.name for field in fields(vfv_er.VFVForwardERRequest)}
        self.assertEqual(names, {
            "instrument", "analytical_basis", "expected_upstream_semantic_id",
            "expected_upstream_evidence_id", "expected_policy_id",
            "expected_policy_hash",
        })
        for prohibited in ("growth", "terminal_pe", "scenario_values",
                           "horizon_years", "approved", "qualified"):
            with self.subTest(prohibited=prohibited), self.assertRaises(TypeError):
                vfv_er.VFVForwardERRequest(**{
                    **{field.name: getattr(self.request(), field.name)
                       for field in fields(vfv_er.VFVForwardERRequest)},
                    prohibited: True,
                })

    def test_positive_result_exact_semantics_and_lineage(self):
        result = self.calculate()
        self.assertIs(result.status, vfv_er.VFVForwardERStatus.AVAILABLE)
        self.assertEqual(result.reasons, ())
        self.assertEqual(result.return_basis,
                         "NOMINAL_PRE_HOLDER_TAX_UNIT_HOLDER_CASHFLOW_IRR")
        self.assertEqual(result.fx_basis,
                         "CONSTANT_TRANSLATION_NO_FX_CONTRIBUTION_MODELED")
        self.assertEqual(result.policy_hash, EXPECTED_POLICY_HASH)
        self.assertEqual(result.upstream_semantic_id,
                         self.qualification.semantic_id)
        self.assertEqual(result.upstream_evidence_id,
                         self.qualification.evidence_id)
        self.assertEqual(tuple(row.name for row in result.scenarios),
                         ("bear", "base", "bull"))
        self.assertTrue(all(row.result_semantics ==
                            "VFV_INSTRUMENT_ER_NET_OF_WRAPPER_EXPENSES_PRE_EXECUTION"
                            for row in result.scenarios))
        self.assertIsNone(result.underlying_benchmark_economic_er)
        self.assertIsNone(result.vfv_executable_net_er)
        payload = result.to_dict()["vfv_forward_expected_return"]
        self.assertEqual(payload["semantic_id"], result.semantic_id)
        self.assertEqual(payload["evidence_id"], result.evidence_id)
        json.dumps({"vfv_forward_expected_return": payload}, allow_nan=False)

    def test_market_price_is_required_context_but_not_inverted_into_earnings(self):
        original = self.calculate()
        changed_qualification = self.with_facts(price="386.2400")
        changed = self.calculate(changed_qualification)
        self.assertEqual(
            tuple(row.annualized_return for row in original.scenarios),
            tuple(row.annualized_return for row in changed.scenarios),
        )
        self.assertNotEqual(original.semantic_id, changed.semantic_id)
        names = {field.name for field in fields(vfv_er.VFVForwardERFactualInputs)}
        self.assertFalse({"earnings", "eps", "earnings_per_unit"} & names)
        source = Path(vfv_er.__file__).read_text()
        self.assertNotIn("market_price /", source)
        self.assertNotIn("current_market_price /", source)

    def test_trailing_pe_is_m0_and_normalized_v0_is_one(self):
        result = self.calculate()
        self.assertEqual(result.factual_inputs.trailing_weighted_fund_portfolio_pe,
                         Decimal("25.2"))
        self.assertTrue(all(row.normalized_initial_unit_value == Decimal("1")
                            for row in result.scenarios))
        expected = ((Decimal("1") + Decimal("0.03"))
                    * result.wrapper_expense_factor) ** 7
        expected *= Decimal("16") / Decimal("25.2")
        self.assertEqual(result.scenarios[1].terminal_normalized_unit_value,
                         expected)

    def test_exact_distribution_path_and_no_latest_quarter_annualization(self):
        result = self.calculate()
        base = result.scenarios[1]
        y0 = Decimal("0.84") / Decimal(100)
        compounded = (Decimal(1) + Decimal("0.03")) \
            * result.wrapper_expense_factor
        expected = tuple(
            y0 if year == 1 else y0 * compounded ** (year - 1)
            for year in range(1, 8)
        )
        self.assertEqual(base.annual_distributions, expected)
        changed_event = replace(
            self.qualification.distributions.latest_event,
            total_distribution_per_unit=Decimal("99"),
            cash_distribution_per_unit=Decimal("99"),
        )
        changed_distribution = replace(
            self.qualification.distributions, latest_event=changed_event)
        changed_qualification = replace(
            self.qualification, distributions=changed_distribution)
        changed = self.calculate(changed_qualification)
        self.assertEqual(
            tuple(row.annual_distributions for row in result.scenarios),
            tuple(row.annual_distributions for row in changed.scenarios),
        )

    def test_exact_wrapper_factor_and_management_fee_not_double_counted(self):
        result = self.calculate()
        self.assertEqual(
            result.wrapper_expense_factor,
            (Decimal(1) - Decimal("0.08") / 100)
            * (Decimal(1) - Decimal("0.00") / 100),
        )
        changed = self.calculate(self.with_facts(management_fee="75"))
        self.assertEqual(
            tuple(row.annualized_return for row in result.scenarios),
            tuple(row.annualized_return for row in changed.scenarios),
        )
        self.assertEqual(changed.factual_inputs.management_fee_percent,
                         Decimal("75"))
        self.assertEqual(changed.factual_inputs.mer_percent, Decimal("0.08"))
        self.assertEqual(changed.factual_inputs.ter_percent, Decimal("0.00"))

    def test_hand_check_zero_growth_unchanged_valuation_zero_expenses(self):
        qualification = self.with_facts(pe="12", yield_percent="0", mer="0", ter="0")
        bear = self.calculate(qualification).scenarios[0]
        self.assertEqual(bear.terminal_normalized_unit_value, Decimal("1"))
        self.assertAlmostEqual(bear.annualized_return, 0.0, delta=1e-14)

    def test_hand_check_positive_growth_and_valuation_contraction_expansion(self):
        positive = self.calculate(
            self.with_facts(pe="20", yield_percent="0", mer="0", ter="0"))
        self.assertAlmostEqual(positive.scenarios[2].annualized_return,
                               0.05, delta=2e-14)
        contraction = self.calculate(
            self.with_facts(pe="24", yield_percent="0", mer="0", ter="0"))
        self.assertAlmostEqual(
            contraction.scenarios[0].annualized_return,
            (12 / 24) ** (1 / 7) - 1,
            delta=2e-14,
        )
        expansion = self.calculate(
            self.with_facts(pe="10", yield_percent="0", mer="0", ter="0"))
        self.assertAlmostEqual(
            expansion.scenarios[2].annualized_return,
            1.05 * (20 / 10) ** (1 / 7) - 1,
            delta=2e-14,
        )

    def test_hand_check_nonzero_yield_and_nonzero_expenses(self):
        distribution = self.calculate(
            self.with_facts(pe="12", yield_percent="1", mer="0", ter="0"))
        self.assertAlmostEqual(distribution.scenarios[0].annualized_return,
                               0.01, delta=2e-14)
        expenses = self.calculate(
            self.with_facts(pe="12", yield_percent="0", mer="1", ter="2"))
        self.assertAlmostEqual(expenses.scenarios[0].annualized_return,
                               0.99 * 0.98 - 1, delta=2e-14)

    def test_combined_fixture_satisfies_cashflow_equation(self):
        result = self.calculate(
            self.with_facts(pe="18", yield_percent="1.2", mer="0.25", ter="0.10"))
        scenario = result.scenarios[1]
        gross = 1 + scenario.annualized_return
        present = math.fsum(
            float(value) / gross ** year
            for year, value in enumerate(scenario.annual_distributions, 1)
        ) + float(scenario.terminal_normalized_unit_value) / gross ** 7
        self.assertAlmostEqual(present, 1.0, delta=1e-10)

    def test_low_confidence_does_not_haircut_return(self):
        result = self.calculate()
        self.assertIs(result.confidence.overall_vfv_er_confidence,
                      vfv_er.VFVForwardERConfidenceLevel.LOW)
        scenario = result.scenarios[1]
        direct = vfv_er.solve_annual_cashflow_irr(
            1.0,
            tuple(float(value) for value in scenario.annual_distributions),
            float(scenario.terminal_normalized_unit_value),
        )
        self.assertEqual(scenario.annualized_return, direct)

    def test_currency_and_fx_are_policy_only_without_hedge_or_exposure_claim(self):
        result = self.calculate()
        self.assertIs(
            result.confidence.currency_basis_status,
            vfv_er.VFVForwardERCurrencyBasisStatus.
            CONSTANT_TRANSLATION_POLICY_ONLY_NO_FX_AUTHORITY,
        )
        limitations = {item.value for item in result.limitations}
        self.assertIn("NO_UNDERLYING_EXPOSURE_CURRENCY_AUTHORITY", limitations)
        self.assertIn("NO_CURRENCY_HEDGE_STATUS_AUTHORITY", limitations)
        self.assertIn("NO_FX_COMPARABILITY_AUTHORITY", limitations)
        self.assertIn(
            "ZERO_FX_CONTRIBUTION_IS_STANDALONE_ANALYTICAL_POLICY_ONLY",
            limitations,
        )

    def test_policy_mismatch_withholds_numeric_result_and_confidence(self):
        for change, reason in (
            ({"expected_policy_id": "NOT_APPROVED"},
             vfv_er.VFVForwardERReason.APPROVED_POLICY_ID_MISMATCH),
            ({"expected_policy_hash": "0" * 64},
             vfv_er.VFVForwardERReason.APPROVED_POLICY_HASH_MISMATCH),
        ):
            with self.subTest(change=change):
                result = self.calculate(**change)
                self.assertIs(result.status, vfv_er.VFVForwardERStatus.UNAVAILABLE)
                self.assertIn(reason.value, result.reasons)
                self.assertEqual(result.scenarios, ())
                self.assertIs(result.confidence.overall_vfv_er_confidence,
                              vfv_er.VFVForwardERConfidenceLevel.NONE)

    def test_missing_fact_and_unusable_expense_semantics_fail_closed(self):
        missing = replace(self.qualification, trailing_valuation=None)
        result = self.calculate(missing)
        self.assertIs(result.status, vfv_er.VFVForwardERStatus.UNAVAILABLE)
        self.assertEqual(result.scenarios, ())
        self.assertIn(vfv_er.VFVForwardERReason.REQUIRED_FACT_ABSENT.value,
                      result.reasons)
        bad_expense = replace(
            self.qualification,
            expenses=replace(self.qualification.expenses, mer_annualized=False),
        )
        result = self.calculate(bad_expense)
        self.assertIs(result.status, vfv_er.VFVForwardERStatus.UNAVAILABLE)
        self.assertIn(
            vfv_er.VFVForwardERReason.
            REQUIRED_EXPENSE_SEMANTICS_UNAVAILABLE.value,
            result.reasons,
        )

    def test_upstream_closed_statuses_propagate_without_bear_reinterpretation(self):
        cases = (
            (evidence.VFVCurrentEvidenceStatus.UNAVAILABLE,
             vfv_er.VFVForwardERStatus.UNAVAILABLE,
             evidence.VFVCurrentEvidenceReason.PRICE_UNAVAILABLE),
            (evidence.VFVCurrentEvidenceStatus.UNSUPPORTED,
             vfv_er.VFVForwardERStatus.UNSUPPORTED,
             evidence.VFVCurrentEvidenceReason.SOURCE_STRUCTURE_UNSUPPORTED),
            (evidence.VFVCurrentEvidenceStatus.SOURCE_CONFLICT,
             vfv_er.VFVForwardERStatus.SOURCE_CONFLICT,
             evidence.VFVCurrentEvidenceReason.IDENTITY_MISMATCH),
        )
        for upstream, expected, reason in cases:
            with self.subTest(upstream=upstream):
                qualification = replace(
                    self.qualification, status=upstream, reasons=(reason,))
                result = self.calculate(qualification)
                self.assertIs(result.status, expected)
                self.assertEqual(result.scenarios, ())
                self.assertIn("UPSTREAM:" + reason.value, result.reasons)

    def test_non_vfv_and_unsupported_basis_are_unsupported(self):
        for change, reason in (
            ({"instrument": "OTHER_ETF"},
             vfv_er.VFVForwardERReason.NON_VFV_INSTRUMENT_UNSUPPORTED),
            ({"analytical_basis": "PRICE_OVER_WEIGHTED_PE"},
             vfv_er.VFVForwardERReason.ANALYTICAL_BASIS_UNSUPPORTED),
        ):
            result = self.calculate(**change)
            self.assertIs(result.status, vfv_er.VFVForwardERStatus.UNSUPPORTED)
            self.assertIn(reason.value, result.reasons)
            self.assertEqual(result.scenarios, ())

    def test_source_identity_mismatch_is_source_conflict(self):
        result = self.calculate(expected_upstream_evidence_id="0" * 64)
        self.assertIs(result.status, vfv_er.VFVForwardERStatus.SOURCE_CONFLICT)
        self.assertEqual(result.scenarios, ())

    def test_numerical_failure_closes_cleanly(self):
        with patch.object(
                vfv_er, "solve_annual_cashflow_irr",
                side_effect=vfv_er.AnnualCashFlowIRRError("forced")):
            result = self.calculate()
        self.assertIs(result.status, vfv_er.VFVForwardERStatus.UNAVAILABLE)
        self.assertEqual(result.scenarios, ())
        self.assertIn(
            vfv_er.VFVForwardERReason.NUMERICAL_REPRESENTATION_UNAVAILABLE.value,
            result.reasons,
        )

    def test_deterministic_output_and_changed_evidence_identity(self):
        first = self.calculate()
        second = self.calculate()
        self.assertEqual(first, second)
        self.assertEqual(first.semantic_id, second.semantic_id)
        self.assertEqual(first.evidence_id, second.evidence_id)
        changed_record = replace(
            self.qualification.fact_evidence[0], content_sha256="f" * 64)
        changed_qualification = replace(
            self.qualification,
            fact_evidence=(changed_record, *self.qualification.fact_evidence[1:]),
        )
        changed = self.calculate(changed_qualification)
        self.assertEqual(first.semantic_id, changed.semantic_id)
        self.assertNotEqual(first.evidence_id, changed.evidence_id)

    def test_ambient_decimal_context_cannot_change_results_or_identities(self):
        contexts = (
            (6, ROUND_DOWN),
            (28, ROUND_HALF_EVEN),
            (50, ROUND_UP),
        )
        results = []
        for precision, rounding in contexts:
            with self.subTest(precision=precision, rounding=rounding):
                with localcontext() as ambient:
                    ambient.prec = precision
                    ambient.rounding = rounding
                    results.append(self.calculate())

        def analytical_output(result):
            return (
                result.wrapper_expense_factor,
                tuple(tuple(row.annual_distributions)
                      for row in result.scenarios),
                tuple(row.terminal_normalized_unit_value
                      for row in result.scenarios),
                result.semantic_id,
                result.evidence_id,
            )

        expected = analytical_output(results[1])
        self.assertTrue(all(analytical_output(result) == expected
                            for result in results))

        # Pin the pre-correction ordinary/default-context economics exactly.
        default_result = results[1]
        self.assertEqual(default_result.wrapper_expense_factor,
                         Decimal("0.999200"))
        self.assertEqual(
            tuple(row.terminal_normalized_unit_value
                  for row in default_result.scenarios),
            (
                Decimal("0.4735302009972995812165706118"),
                Decimal("0.7765098915946192893485703644"),
                Decimal("1.110507576606332093324562719"),
            ),
        )
        for actual, reference in zip(
                (row.annualized_return for row in default_result.scenarios),
                (-0.08954559947688687,
                 -0.025226689275521054,
                 0.02437022559796578)):
            self.assertTrue(math.isclose(
                actual, reference, rel_tol=0.0, abs_tol=2e-14))

    def test_identity_versions_root_problem_not_binary64_realization(self):
        self.assertEqual(
            vfv_er.VFV_FORWARD_ER_IDENTITY_VERSION,
            "2026-10-01-vfv-forward-er-root-problem-identity-v2",
        )
        original = self.calculate()
        original_scenario = original.scenarios[2]
        changed_return = math.nextafter(
            original_scenario.annualized_return, math.inf)
        variant = replace(
            original,
            scenarios=(*original.scenarios[:2], replace(
                original_scenario, annualized_return=changed_return)),
        )
        self.assertNotEqual(original.scenarios[2].annualized_return,
                            variant.scenarios[2].annualized_return)
        self.assertEqual(original.semantic_id, variant.semantic_id)
        self.assertEqual(original.evidence_id, variant.evidence_id)
        original_json = original.to_dict()["vfv_forward_expected_return"]
        variant_json = variant.to_dict()["vfv_forward_expected_return"]
        self.assertNotEqual(original_json["scenarios"][2]["annualized_return"],
                            variant_json["scenarios"][2]["annualized_return"])

    def test_identity_v2_pins_and_deterministic_inputs_remain_material(self):
        original = self.calculate()
        baseline = original.semantic_id
        scenario = original.scenarios[1]
        changed_scenarios = (
            replace(original.scenarios[0],
                    fundamental_growth=Decimal("0.01")),
            replace(scenario, terminal_weighted_pe=Decimal("17")),
            replace(original.scenarios[2], annual_distributions=(
                Decimal("0.009"),
                *original.scenarios[2].annual_distributions[1:])),
        )
        variants = (
            replace(original, scenarios=(changed_scenarios[0],
                                         *original.scenarios[1:])),
            replace(original, scenarios=(original.scenarios[0],
                                         changed_scenarios[1],
                                         original.scenarios[2])),
            replace(original, scenarios=(*original.scenarios[:2],
                                         changed_scenarios[2])),
            replace(original, wrapper_expense_factor=Decimal("0.999201")),
            replace(original, scenarios=(original.scenarios[0], replace(
                scenario,
                terminal_normalized_unit_value=(
                    scenario.terminal_normalized_unit_value
                    + Decimal("0.0000000000000000000000000001"))),
                original.scenarios[2])),
            replace(original, policy_hash="0" * 64),
            replace(original, methodology_id="changed-methodology"),
            replace(original, factual_inputs=replace(
                original.factual_inputs,
                current_market_price=Decimal("193.1201"))),
        )
        self.assertTrue(all(item.semantic_id != baseline for item in variants))
        with patch.object(
                vfv_er, "VFV_FORWARD_ER_IDENTITY_VERSION",
                "changed-identity-version"):
            self.assertNotEqual(original.semantic_id, baseline)

        # Stabilize test-only provenance tokens so both exact v2 IDs are pinned.
        stable_evidence = tuple(
            replace(item,
                    artifact_receipt_id=f"{index + 1:064x}",
                    content_sha256=f"{index + 101:064x}")
            for index, item in enumerate(original.fact_evidence)
        )
        identity_fixture = replace(
            original,
            upstream_evidence_id="e" * 64,
            fact_evidence=stable_evidence,
        )
        self.assertEqual(
            identity_fixture.semantic_id,
            "5a000b8246e09918222383d9a16d45360d37989f28ba2268e0a4e7f950ca6ce5",
        )
        self.assertEqual(
            identity_fixture.evidence_id,
            "b1015f9d17d69f9f753043252470be0e7fb6011f64d9e04b055abf31a190fde1",
        )

    def test_pr4a_numerical_result_is_unchanged_through_shared_solver(self):
        diagnostic = company_er.calculate_expected_return(request_fixture())
        for scenario in diagnostic.scenarios:
            if scenario.annualized_return is None:
                continue
            direct = vfv_er.solve_annual_cashflow_irr(
                diagnostic.current_price,
                scenario.dividends_per_share,
                scenario.terminal_price,
                max_iterations=company_er._MAX_ITERATIONS,
                root_tolerance=company_er._ROOT_TOLERANCE,
                residual_tolerance=company_er._RESIDUAL_TOLERANCE,
            )
            self.assertEqual(scenario.annualized_return, direct)

    def test_no_company_comparator_runtime_consumer_or_operational_io(self):
        source = Path(vfv_er.__file__).read_text()
        tree = ast.parse(source)
        calls = {
            node.func.attr if isinstance(node.func, ast.Attribute)
            else node.func.id if isinstance(node.func, ast.Name) else ""
            for node in ast.walk(tree) if isinstance(node, ast.Call)
        }
        self.assertFalse({"open", "read_text", "getenv", "now", "today"} & calls)
        self.assertNotIn("company", {field.name for field in
                                     fields(vfv_er.VFVForwardERRequest)})
        root = Path(vfv_er.__file__).resolve().parents[1]
        adapter = Path(vfv_er.__file__).resolve()
        allowed = {
            adapter,
            Path(policy_module.__file__).resolve(),
            adapter.with_name(
                "company_vfv_expected_return_comparator.py").resolve(),
            adapter.with_name(
                "bounded_confidence_projection.py").resolve(),
        }
        for path in (root / "main.py", *sorted((root / "src").glob("*.py")),
                     *sorted((root / "pit_comparison").glob("*.py"))):
            if path.resolve() in allowed:
                continue
            self.assertNotIn("vfv_forward_expected_return", path.read_text(),
                             str(path))


if __name__ == "__main__":
    unittest.main()
