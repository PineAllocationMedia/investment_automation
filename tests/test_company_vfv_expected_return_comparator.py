"""Bounded PR5E-company versus VFV Expected Return comparator tests."""
import ast
from dataclasses import fields, replace
from decimal import Decimal
import json
import math
from pathlib import Path
import tempfile
import unittest

from economic_facts import vfv_current_evidence
from economic_facts import vfv_fx_hedge_evidence as fx_evidence
from src import company_vfv_expected_return_comparator as comparator
from src import expected_return_assumptions as assumptions
from src import expected_return_pr5e_adapter as pr5e
from src import vfv_forward_er_policy
from src import vfv_forward_expected_return as vfv_er
from tests.test_expected_return_pr5e_adapter import PR5EFixtureMixin
from tests.test_vfv_fx_hedge_evidence import standard_qualification, standard_record
from tests.vfv_current_evidence_fixtures import publish_bundle, request_for


class CompanyVFVComparatorTests(PR5EFixtureMixin, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        fixture = cls.built["fixture"]
        roots = cls.built["result"]
        request = pr5e.PR5ERealExpectedReturnRequest(
            cls.built["request"], roots.semantic_id, roots.evidence_id)
        cls.company = pr5e.admit_real_expected_return_pr5e(
            fixture.current_archive, fixture.submissions_archive,
            fixture.filing_archive, fixture.sec_archive,
            fixture.nasdaq_archive, cls.builder.quote_archive,
            cls.builder.split_archive, request,
        )
        cls.vfv_temporary = tempfile.TemporaryDirectory()
        root = Path(cls.vfv_temporary.name).resolve() / "vfv"
        archive, product, etf, factsheet = publish_bundle(root)
        qualification = vfv_current_evidence.qualify_vfv_current_evidence(
            archive, request_for(archive, product, etf, factsheet))
        policy = vfv_forward_er_policy.get_approved_vfv_forward_er_policy()
        vfv_request = vfv_er.VFVForwardERRequest(
            "VFV",
            vfv_er.VFV_FORWARD_ER_ANALYTICAL_BASIS,
            qualification.semantic_id,
            qualification.evidence_id,
            policy.policy_id,
            policy.content_hash,
        )
        cls.vfv = vfv_er.calculate_vfv_forward_expected_return(
            qualification, vfv_request)
        cls.hedge = standard_qualification()

    @classmethod
    def tearDownClass(cls):
        cls.vfv_temporary.cleanup()
        super().tearDownClass()

    def request_for(self, company=None, vfv=None, hedge=None, **changes):
        company = self.company if company is None else company
        vfv = self.vfv if vfv is None else vfv
        hedge = self.hedge if hedge is None else hedge
        company_problem = (
            comparator.identify_company_expected_return_problem(company))
        values = {
            "expected_company_problem_semantic_id": (
                company_problem.semantic_id),
            "expected_company_problem_evidence_id": (
                company_problem.evidence_id),
            "expected_vfv_semantic_id": vfv.semantic_id,
            "expected_vfv_evidence_id": vfv.evidence_id,
            "expected_vfv_fx_hedge_semantic_id": hedge.semantic_id,
            "expected_vfv_fx_hedge_evidence_id": hedge.evidence_id,
        }
        values.update(changes)
        return comparator.CompanyVFVComparisonRequest(**values)

    def readmit(self, *, roots=None, construction=None):
        company = self.company
        return pr5e._result(
            company.status,
            company.reasons,
            company.upstream_pr5d2 if roots is None else roots,
            share_basis=company.admitted_share_basis_identity,
            as_of=company.analytical_as_of,
            qualified_facts=company.qualified_facts,
            construction=(company.construction if construction is None
                          else construction),
        )

    def provenance_only_company_variant(self):
        roots = self.company.upstream_pr5d2
        bridge = roots.basis_bridge
        quote = bridge.upstream_quote
        extraction = quote.quote_extraction
        receipt = replace(
            extraction.receipt, captured_at="2026-09-29T18:00:00Z")
        recaptured_extraction = replace(extraction, receipt=receipt)
        recaptured_quote = replace(
            quote,
            captured_at=receipt.captured_at,
            quote_extraction=recaptured_extraction,
        )
        self.assertEqual(quote.semantic_id, recaptured_quote.semantic_id)
        self.assertNotEqual(quote.evidence_id, recaptured_quote.evidence_id)
        recaptured_bridge = replace(
            bridge,
            quote_evidence_id=recaptured_quote.evidence_id,
            upstream_quote=recaptured_quote,
        )
        self.assertEqual(bridge.semantic_id, recaptured_bridge.semantic_id)
        self.assertNotEqual(bridge.evidence_id, recaptured_bridge.evidence_id)
        upstream_evidence_ids = tuple(sorted({
            recaptured_bridge.evidence_id,
            recaptured_bridge.upstream_comparability.evidence_id,
            recaptured_bridge.upstream_quote.evidence_id,
            recaptured_bridge.recent_share_basis_source.evidence_id,
            recaptured_bridge.yahoo_split_history.evidence_id,
            roots.nonpayer.evidence_id,
            roots.nonpayer.upstream_nonpayer_source.evidence_hash,
            roots.profile.evidence_id,
        }))
        recaptured_roots = replace(
            roots,
            upstream_evidence_ids=upstream_evidence_ids,
            basis_bridge=recaptured_bridge,
        )
        self.assertEqual(roots.semantic_id, recaptured_roots.semantic_id)
        self.assertNotEqual(roots.evidence_id, recaptured_roots.evidence_id)
        return self.readmit(roots=recaptured_roots)

    def compare(self, company=None, vfv=None, hedge=None, request=None):
        company = self.company if company is None else company
        vfv = self.vfv if vfv is None else vfv
        hedge = self.hedge if hedge is None else hedge
        return comparator.compare_company_vfv_expected_returns(
            company, vfv, hedge,
            self.request_for(company, vfv, hedge) if request is None else request,
        )

    def with_company_diagnostic(self, **changes):
        diagnostic = replace(
            self.company.construction.diagnostic, **changes)
        construction = replace(
            self.company.construction, diagnostic=diagnostic)
        return replace(self.company, construction=construction)

    def test_positive_bounded_current_route_comparison(self):
        result = self.compare()
        self.assertIs(
            result.status, comparator.CompanyVFVComparisonStatus.AVAILABLE)
        self.assertEqual(result.reasons, ())
        self.assertEqual(
            result.comparison_basis_identity,
            "2026-10-01-company-vfv-constant-fx-comparison-v1",
        )
        self.assertEqual(
            result.comparison_basis_version,
            "2026-10-01-company-vfv-constant-fx-comparison-v1",
        )
        self.assertEqual(
            result.comparison_semantics,
            "SAME_LABEL_DETERMINISTIC_SCENARIO_SPREADS",
        )
        self.assertEqual(
            result.company_problem_identity_version,
            "2026-10-01-company-vfv-problem-identity-v2",
        )
        self.assertEqual(result.company_basis.quote_currency, "USD")
        self.assertEqual(result.company_basis.quote_unit, "CURRENCY_PER_SHARE")
        self.assertEqual(result.company_basis.accounting_basis, "US_GAAP")
        self.assertEqual(result.company_basis.profile, "ORDINARY_COMPOUNDER")
        self.assertEqual(result.company_basis.distribution_state,
                         "VERIFIED_NONPAYER")
        self.assertEqual(result.vfv_basis.listed_currency, "CAD")
        self.assertEqual(
            result.vfv_fx_hedge_basis.economic_exposure_currency, "USD")
        json.dumps(result.to_dict(), allow_nan=False)

    def test_bear_base_bull_same_label_spreads_and_exact_arithmetic_only(self):
        result = self.compare()
        self.assertEqual(
            tuple(item.label for item in result.scenario_spreads),
            ("bear", "base", "bull"),
        )
        company_rows = self.company.construction.diagnostic.scenarios
        for spread, company_row, vfv_row in zip(
                result.scenario_spreads, company_rows, self.vfv.scenarios):
            self.assertEqual(spread.company_annualized_return,
                             company_row.annualized_return)
            self.assertEqual(spread.vfv_annualized_return,
                             vfv_row.annualized_return)
            self.assertEqual(
                spread.spread,
                company_row.annualized_return - vfv_row.annualized_return,
            )
            self.assertEqual(
                spread.semantics,
                comparator.SAME_LABEL_SPREAD_SEMANTICS,
            )
        payload = result.to_dict()["company_vfv_expected_return_comparison"]
        self.assertEqual(len(payload["scenario_spreads"]), 3)
        self.assertNotIn("cross_label_spreads", payload)

    def test_result_has_no_winner_rank_recommendation_or_allocation_fields(self):
        names = {field.name for field in fields(
            comparator.CompanyVFVComparisonResult)}
        prohibited = {
            "winner", "rank", "score", "recommendation", "allocation",
            "target_weight", "position_size", "execution_instruction",
            "expected_probability_of_outperformance",
        }
        self.assertFalse(names & prohibited)
        payload = json.dumps(self.compare().to_dict()).casefold()
        self.assertNotIn('"winner"', payload)
        self.assertNotIn('"recommendation"', payload)
        self.assertNotIn('"allocation"', payload)

    def test_request_pins_only_exact_upstream_identities(self):
        names = {field.name for field in fields(
            comparator.CompanyVFVComparisonRequest)}
        self.assertEqual(names, {
            "expected_company_problem_semantic_id",
            "expected_company_problem_evidence_id",
            "expected_vfv_semantic_id",
            "expected_vfv_evidence_id",
            "expected_vfv_fx_hedge_semantic_id",
            "expected_vfv_fx_hedge_evidence_id",
        })
        for prohibited in (
                "growth", "terminal_multiple", "fx_forecast", "hedge_ratio",
                "scenario_weights", "recommendation_threshold",
                "winner_threshold", "allocation_threshold"):
            with self.subTest(prohibited=prohibited), self.assertRaises(TypeError):
                comparator.CompanyVFVComparisonRequest(**{
                    **{field.name: getattr(self.request_for(), field.name)
                       for field in fields(
                           comparator.CompanyVFVComparisonRequest)},
                    prohibited: 1,
                })

    def test_only_current_pr5e_usd_route_is_supported(self):
        changed_roots = replace(
            self.company.upstream_pr5d2,
            quote_currency="CAD",
            quote_unit="CAD_PER_SHARE",
        )
        changed = replace(self.company, upstream_pr5d2=changed_roots)
        result = self.compare(company=changed)
        self.assertIs(
            result.status, comparator.CompanyVFVComparisonStatus.UNSUPPORTED)
        self.assertIn(
            comparator.CompanyVFVComparisonReason.
            COMPANY_CURRENCY_BASIS_INCOMPATIBLE,
            result.reasons,
        )
        self.assertEqual(result.scenario_spreads, ())

    def test_unsupported_company_profile_payer_and_accounting_routes_close(self):
        no_nonpayer = replace(
            self.company.qualified_facts,
            roots=tuple(item for item in self.company.qualified_facts.roots
                        if type(item) is not assumptions.VerifiedNonpayer),
        )
        cases = (
            self.with_company_diagnostic(profile="BANK"),
            replace(self.company, qualified_facts=no_nonpayer),
            replace(self.company, upstream_pr5d2=replace(
                self.company.upstream_pr5d2, accounting_basis="IFRS")),
        )
        for changed in cases:
            with self.subTest(changed=changed):
                result = self.compare(company=changed)
                self.assertIs(
                    result.status,
                    comparator.CompanyVFVComparisonStatus.UNSUPPORTED,
                )
                self.assertEqual(result.scenario_spreads, ())

    def test_wrong_company_return_fx_basis_and_horizon_close(self):
        cases = (
            (self.with_company_diagnostic(return_basis="OTHER"),
             comparator.CompanyVFVComparisonReason.
             COMPANY_RETURN_BASIS_INCOMPATIBLE),
            (self.with_company_diagnostic(fx_basis="FX_FORECAST"),
             comparator.CompanyVFVComparisonReason.
             COMPANY_FX_BASIS_INCOMPATIBLE),
            (self.with_company_diagnostic(horizon_years=8),
             comparator.CompanyVFVComparisonReason.
             COMPANY_HORIZON_INCOMPATIBLE),
        )
        for changed, reason in cases:
            with self.subTest(reason=reason):
                result = self.compare(company=changed)
                self.assertIs(
                    result.status,
                    comparator.CompanyVFVComparisonStatus.UNSUPPORTED,
                )
                self.assertIn(reason, result.reasons)

    def test_company_upstream_failures_and_policy_mismatch_close(self):
        status_cases = (
            (pr5e.PR5EStatus.UNAVAILABLE,
             comparator.CompanyVFVComparisonStatus.UNAVAILABLE),
            (pr5e.PR5EStatus.UNSUPPORTED,
             comparator.CompanyVFVComparisonStatus.UNSUPPORTED),
            (pr5e.PR5EStatus.SOURCE_CONFLICT,
             comparator.CompanyVFVComparisonStatus.SOURCE_CONFLICT),
        )
        for company_status, expected in status_cases:
            changed = replace(self.company, status=company_status)
            with self.subTest(company_status=company_status):
                result = self.compare(company=changed)
                self.assertIs(result.status, expected)
                self.assertEqual(result.scenario_spreads, ())
        changed = replace(
            self.company,
            construction=replace(
                self.company.construction,
                policy_hashes=(("mature_growth", "0" * 64),),
            ),
        )
        result = self.compare(company=changed)
        self.assertIs(
            result.status, comparator.CompanyVFVComparisonStatus.UNSUPPORTED)
        self.assertIn(
            comparator.CompanyVFVComparisonReason.
            COMPANY_POLICY_IDENTITY_MISMATCH,
            result.reasons,
        )

    def test_unavailable_or_wrong_vfv_policy_methodology_basis_horizon_close(self):
        variants = (
            (replace(self.vfv, status=vfv_er.VFVForwardERStatus.UNAVAILABLE),
             comparator.CompanyVFVComparisonStatus.UNAVAILABLE),
            (replace(self.vfv, policy_hash="0" * 64),
             comparator.CompanyVFVComparisonStatus.UNSUPPORTED),
            (replace(self.vfv, methodology_id="OTHER"),
             comparator.CompanyVFVComparisonStatus.UNSUPPORTED),
            (replace(self.vfv, return_basis="OTHER"),
             comparator.CompanyVFVComparisonStatus.UNSUPPORTED),
            (replace(self.vfv, fx_basis="OTHER"),
             comparator.CompanyVFVComparisonStatus.UNSUPPORTED),
            (replace(self.vfv, horizon_years=8),
             comparator.CompanyVFVComparisonStatus.UNSUPPORTED),
        )
        for changed, status in variants:
            with self.subTest(changed=changed):
                result = self.compare(vfv=changed)
                self.assertIs(result.status, status)
                self.assertEqual(result.scenario_spreads, ())

    def test_missing_unsupported_and_conflicted_fx_evidence_close(self):
        missing = fx_evidence.qualify_vfv_fx_hedge_evidence(())
        unsupported = fx_evidence.qualify_vfv_fx_hedge_evidence((
            standard_record(economic_exposure_currency="EUR"),))
        conflict = fx_evidence.qualify_vfv_fx_hedge_evidence((
            standard_record(),
            standard_record(
                content_sha256="3" * 64,
                capture_id="4" * 64,
                economic_exposure_currency="EUR"),
        ))
        cases = (
            (missing, comparator.CompanyVFVComparisonStatus.UNAVAILABLE),
            (unsupported, comparator.CompanyVFVComparisonStatus.UNSUPPORTED),
            (conflict, comparator.CompanyVFVComparisonStatus.SOURCE_CONFLICT),
        )
        for hedge, status in cases:
            with self.subTest(status=status):
                result = self.compare(hedge=hedge)
                self.assertIs(result.status, status)
                self.assertEqual(result.scenario_spreads, ())

    def test_each_semantic_or_evidence_identity_mismatch_is_source_conflict(self):
        request = self.request_for()
        for field in fields(request):
            changed = replace(request, **{field.name: "0" * 64})
            with self.subTest(field=field.name):
                result = self.compare(request=changed)
                self.assertIs(
                    result.status,
                    comparator.CompanyVFVComparisonStatus.SOURCE_CONFLICT,
                )
                self.assertEqual(result.scenario_spreads, ())

    def test_incomplete_scenarios_and_missing_numeric_spread_close(self):
        incomplete = self.with_company_diagnostic(
            scenarios=self.company.construction.diagnostic.scenarios[:2])
        numeric = self.with_company_diagnostic(scenarios=(
            replace(
                self.company.construction.diagnostic.scenarios[0],
                annualized_return=None),
            *self.company.construction.diagnostic.scenarios[1:],
        ))
        result = self.compare(company=incomplete)
        self.assertIs(
            result.status, comparator.CompanyVFVComparisonStatus.UNAVAILABLE)
        self.assertIn(
            comparator.CompanyVFVComparisonReason.SCENARIO_LABELS_INCOMPLETE,
            result.reasons,
        )
        result = self.compare(company=numeric)
        self.assertIs(
            result.status, comparator.CompanyVFVComparisonStatus.UNAVAILABLE)
        self.assertIn(
            comparator.CompanyVFVComparisonReason.NUMERICAL_SPREAD_UNAVAILABLE,
            result.reasons,
        )

    def test_confidence_is_minimum_low_without_er_or_spread_haircut(self):
        result = self.compare()
        self.assertIs(
            result.local_comparator_confidence,
            comparator.CompanyVFVComparisonConfidence.LOW,
        )
        self.assertLessEqual(
            ("NONE", "LOW").index(result.local_comparator_confidence.value), 1)
        for output, company_row, vfv_row in zip(
                result.scenario_spreads,
                self.company.construction.diagnostic.scenarios,
                self.vfv.scenarios):
            self.assertEqual(output.company_annualized_return,
                             company_row.annualized_return)
            self.assertEqual(output.vfv_annualized_return,
                             vfv_row.annualized_return)
            self.assertEqual(output.spread,
                             company_row.annualized_return
                             - vfv_row.annualized_return)

    def test_required_dated_fx_and_authority_limitations_are_retained(self):
        result = self.compare()
        limitations = {item.value for item in result.limitations}
        self.assertEqual(
            limitations,
            {item.value for item in comparator.CompanyVFVComparisonLimitation},
        )
        self.assertIn("NO_REALIZED_CAD_RETURN_CLAIM", limitations)
        self.assertIn("NO_FX_FORECAST", limitations)
        self.assertIn(
            "VFV_HEDGE_STATE_DATE_BOUND_NOT_PERMANENT", limitations)
        self.assertIn("NO_RECOMMENDATION_OR_ALLOCATION_AUTHORITY",
                      limitations)
        self.assertEqual(
            result.vfv_fx_hedge_basis.measurement_date, "2026-06-30")
        self.assertIs(
            result.vfv_fx_hedge_basis.authority_scope,
            fx_evidence.VFVFXHedgeAuthorityScope.
            CURRENT_CAPTURE_BOUND_DATE_BOUND,
        )
        self.assertEqual(result.company_limitations, self.company.limitations)
        self.assertEqual(result.vfv_limitations, self.vfv.limitations)
        self.assertEqual(result.vfv_inherited_limitations,
                         self.vfv.inherited_limitations)

    def test_cross_environment_admission_lineage_is_trace_only(self):
        first = self.compare()
        variant_construction = replace(
            self.company.construction, lineage_hash="f" * 64)
        variant_company = self.readmit(construction=variant_construction)
        variant = self.compare(company=variant_company)
        self.assertNotEqual(
            self.company.admission_semantic_id,
            variant_company.admission_semantic_id,
        )
        self.assertNotEqual(
            self.company.admission_evidence_id,
            variant_company.admission_evidence_id,
        )
        self.assertEqual(
            first.company_problem_semantic_id,
            variant.company_problem_semantic_id,
        )
        self.assertEqual(
            first.company_problem_evidence_id,
            variant.company_problem_evidence_id,
        )
        self.assertEqual(first.semantic_id, variant.semantic_id)
        self.assertEqual(first.evidence_id, variant.evidence_id)

    def test_company_provenance_only_change_changes_evidence_not_semantics(self):
        first = self.compare()
        recaptured_company = self.provenance_only_company_variant()
        changed = self.compare(company=recaptured_company)
        self.assertEqual(
            first.company_problem_semantic_id,
            changed.company_problem_semantic_id,
        )
        self.assertNotEqual(
            first.company_problem_evidence_id,
            changed.company_problem_evidence_id,
        )
        self.assertEqual(first.semantic_id, changed.semantic_id)
        self.assertNotEqual(first.evidence_id, changed.evidence_id)

    def test_material_company_problem_change_changes_semantic_identity(self):
        first = self.compare()
        changed_roots = replace(
            self.company.upstream_pr5d2,
            quote_price=self.company.upstream_pr5d2.quote_price
            + Decimal("1.0000"),
        )
        self.assertNotEqual(
            self.company.upstream_pr5d2.semantic_id,
            changed_roots.semantic_id,
        )
        changed = self.compare(company=self.readmit(roots=changed_roots))
        self.assertNotEqual(
            first.company_problem_semantic_id,
            changed.company_problem_semantic_id,
        )
        self.assertNotEqual(first.semantic_id, changed.semantic_id)

    def test_deterministic_identity_pins_and_fx_identity_preservation(self):
        first = self.compare()
        repeated = self.compare()
        self.assertEqual(first.semantic_id, repeated.semantic_id)
        self.assertEqual(first.evidence_id, repeated.evidence_id)
        self.assertEqual(
            first.company_problem_semantic_id,
            "3f2837d650371ae66b4b08e2fdb268eb8782c1430e284b22d12974081173ccf2",
        )
        self.assertEqual(
            first.company_problem_evidence_id,
            "e037fa8049805ace18f00d8e3835920b8cfe4804d24522c68e633232f451d8e7",
        )
        self.assertEqual(
            first.semantic_id,
            "156fd61f3256c3e4d125720e4cc30d473efb0737ddab22654dfa328d1dc91ef0",
        )
        stable_vfv_evidence = tuple(
            replace(
                item,
                artifact_receipt_id=f"{index + 1:064x}",
                content_sha256=f"{index + 101:064x}",
            )
            for index, item in enumerate(self.vfv.fact_evidence)
        )
        identity_vfv = replace(
            self.vfv,
            upstream_evidence_id="e" * 64,
            fact_evidence=stable_vfv_evidence,
        )
        identity_fixture = self.compare(vfv=identity_vfv)
        self.assertEqual(first.semantic_id, identity_fixture.semantic_id)
        self.assertEqual(
            identity_vfv.evidence_id,
            "b1015f9d17d69f9f753043252470be0e7fb6011f64d9e04b055abf31a190fde1",
        )
        self.assertEqual(
            identity_fixture.evidence_id,
            "a84d48db3e5831ca42ec5db69ba3700f300c632a0d824b7ed23826b3e338e0a1",
        )
        self.assertEqual(
            self.hedge.semantic_id,
            "1b16a3cab764f39fc3e74911dd813664616cedd984f55868729d45ae02724482",
        )
        self.assertEqual(
            self.hedge.evidence_id,
            "5d3badf3f403e96ca71904aa7ff23e4aa8a5790be742cabae7c8c951a65c280b",
        )
        recaptured = standard_qualification(
            content_sha256="3" * 64,
            capture_id="4" * 64,
            captured_at="2026-10-01T10:00:00-04:00",
            reviewed_at="2026-10-01T11:00:00-04:00",
        )
        changed = self.compare(hedge=recaptured)
        self.assertEqual(first.semantic_id, changed.semantic_id)
        self.assertNotEqual(first.evidence_id, changed.evidence_id)

    def test_one_ulp_spread_perturbation_does_not_change_identity(self):
        result = self.compare()
        original = result.scenario_spreads[1]
        perturbed = replace(
            result,
            scenario_spreads=(
                result.scenario_spreads[0],
                replace(original, spread=math.nextafter(
                    original.spread, math.inf)),
                result.scenario_spreads[2],
            ),
        )
        self.assertNotEqual(
            result.scenario_spreads[1].spread,
            perturbed.scenario_spreads[1].spread,
        )
        self.assertEqual(result.semantic_id, perturbed.semantic_id)
        self.assertEqual(result.evidence_id, perturbed.evidence_id)
        original_payload = result.to_dict()[
            "company_vfv_expected_return_comparison"]
        perturbed_payload = perturbed.to_dict()[
            "company_vfv_expected_return_comparison"]
        self.assertNotEqual(
            original_payload["scenario_spreads"][1]["spread"],
            perturbed_payload["scenario_spreads"][1]["spread"],
        )

    def test_no_runtime_io_and_no_production_consumer_imports_comparator(self):
        source = Path(comparator.__file__).read_text()
        tree = ast.parse(source)
        calls = {
            node.func.attr if isinstance(node.func, ast.Attribute)
            else node.func.id if isinstance(node.func, ast.Name) else ""
            for node in ast.walk(tree) if isinstance(node, ast.Call)
        }
        self.assertFalse({
            "open", "read_text", "getenv", "now", "today", "urlopen",
        } & calls)
        root = Path(comparator.__file__).resolve().parents[1]
        allowed = Path(comparator.__file__).resolve()
        for path in (
                root / "main.py", *sorted((root / "src").glob("*.py")),
                *sorted((root / "pit_comparison").glob("*.py"))):
            if path.resolve() == allowed:
                continue
            self.assertNotIn(
                "company_vfv_expected_return_comparator", path.read_text(),
                str(path),
            )


if __name__ == "__main__":
    unittest.main()
