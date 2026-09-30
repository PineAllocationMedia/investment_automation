"""PR5E final-admission replay, real-fact adaptation, and isolation tests."""
import ast
from dataclasses import FrozenInstanceError, replace
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
import unittest
from unittest.mock import patch

from src import expected_return_assumptions as assumptions
from src import expected_return_pr5d_bundle as pr5d2
from src import expected_return_pr5e_adapter as pr5e
from tests.test_expected_return_pr5d_bundle import ExpectedReturnPR5D2BundleTests


class PR5EFixtureMixin:
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.builder = ExpectedReturnPR5D2BundleTests(methodName="runTest")
        cls.builder.setUp()
        cls.built = cls.builder._build_complete_bundle()

    @classmethod
    def tearDownClass(cls):
        cls.builder.doCleanups()
        super().tearDownClass()

    def request_for(self, roots=None):
        roots = self.built["result"] if roots is None else roots
        return pr5e.PR5ERealExpectedReturnRequest(
            self.built["request"], roots.semantic_id, roots.evidence_id)

    def call(self, request=None):
        fixture = self.built["fixture"]
        return pr5e.admit_real_expected_return_pr5e(
            fixture.current_archive, fixture.submissions_archive,
            fixture.filing_archive, fixture.sec_archive, fixture.nasdaq_archive,
            self.builder.quote_archive, self.builder.split_archive,
            self.request_for() if request is None else request,
        )


class PR5EAdmissionTests(PR5EFixtureMixin, unittest.TestCase):
    def test_fresh_replay_admits_exact_real_nonpayer_fact_set(self):
        with patch.object(pr5e, "assemble_expected_return_pr5d_bundle",
                          wraps=pr5d2.assemble_expected_return_pr5d_bundle) as replay:
            result = self.call()
        replay.assert_called_once()
        self.assertIs(result.status, pr5e.PR5EStatus.REAL_EXPECTED_RETURN_ADMITTED)
        self.assertEqual(result.reasons, ())
        self.assertEqual(result.qualified_facts.security_id,
                         result.upstream_pr5d2.route_local_security_key)
        self.assertEqual(result.qualified_facts.share_class,
                         result.upstream_pr5d2.canonical_selected_common_class)
        roots = result.qualified_facts.roots
        self.assertEqual(sum(type(item) is assumptions.ObservedPrice for item in roots), 1)
        self.assertEqual(sum(type(item) is assumptions.ReportedDilutedEPS for item in roots), 5)
        self.assertEqual(sum(type(item) is assumptions.VerifiedNonpayer for item in roots), 1)
        self.assertEqual(sum(type(item) is assumptions.ProfileQualification for item in roots), 1)
        self.assertFalse(any(type(item) is assumptions.OrdinaryAnnualDividend for item in roots))
        self.assertEqual(result.construction.status, "BUILT")
        self.assertEqual(result.construction.diagnostic.authority, "DIAGNOSTIC_ONLY")

    def test_route_identity_basis_price_and_period_economics_are_preserved(self):
        result = self.call()
        roots = result.qualified_facts.roots
        price = next(item for item in roots if type(item) is assumptions.ObservedPrice)
        eps = tuple(item for item in roots if type(item) is assumptions.ReportedDilutedEPS)
        self.assertEqual(price.value, float(Decimal("123.4500")))
        self.assertEqual(price.observed_on, "2026-09-29")
        self.assertEqual(price.basis.currency, "USD")
        self.assertEqual(price.basis.share_basis,
                         result.admitted_share_basis_identity)
        self.assertEqual(
            tuple((item.period.start, item.period.end, item.value) for item in eps),
            tuple((decision.period_start, decision.period_end,
                   float(Fraction(decision.c3_value)))
                  for decision in result.upstream_pr5d2.period_decisions),
        )
        self.assertEqual(result.qualified_facts.latest_required_fiscal_end,
                         result.upstream_pr5d2.nonpayer_period_end)

    def test_real_provenance_is_publication_unknown_and_capture_bound(self):
        result = self.call()
        for root in result.qualified_facts.roots:
            provenance = root.identity.provenance
            self.assertIs(type(provenance), assumptions.RealProvenance)
            self.assertIsNone(provenance.published_at)
            self.assertIs(provenance.publication_semantics,
                          assumptions.PublicationSemantics.UNKNOWN)
            self.assertIs(provenance.availability_semantics,
                          assumptions.AvailabilitySemantics.CAPTURE_BOUND)
            self.assertEqual(provenance.available_at, provenance.captured_at)
            self.assertTrue(provenance.extractor_id.value.startswith("PR5E_REAL_"))
            self.assertFalse(provenance.extractor_id.value.startswith("SYNTHETIC_"))
        for evidence in result.construction.request.evidence:
            self.assertIsNone(evidence.published_at)
            self.assertEqual(evidence.freshness_status, "CAPTURE_BOUND")
            self.assertEqual(evidence.publication_semantics, "UNKNOWN")
            self.assertEqual(evidence.availability_semantics, "CAPTURE_BOUND")
        self.assertEqual(result.construction.request.confidence.fundamental, "LOW")
        self.assertTrue(all(item.category == "LOW" for item in result.construction.confidence))

    def test_as_of_is_deterministic_maximum_required_capture_without_clock(self):
        first = self.call()
        second = self.call()
        self.assertEqual(first.analytical_as_of, "2026-10-01T12:00:00+00:00")
        self.assertEqual(first, second)
        self.assertEqual(first.admission_semantic_id, second.admission_semantic_id)
        self.assertEqual(first.admission_evidence_id, second.admission_evidence_id)

    def test_admitted_share_basis_identity_is_deterministic_and_evidence_bound(self):
        baseline = self.call()
        self.assertEqual(baseline.admitted_share_basis_identity,
                         self.call().admitted_share_basis_identity)
        changed = replace(self.built["result"], basis_multiplier_numerator=2)
        with patch.object(pr5e, "assemble_expected_return_pr5d_bundle",
                          return_value=changed):
            variant = self.call(self.request_for(changed))
        self.assertNotEqual(variant.admitted_share_basis_identity,
                            baseline.admitted_share_basis_identity)
        expected = tuple(float(Fraction(item.c3_value) * Fraction(2, 1))
                         for item in changed.period_decisions)
        actual = tuple(item.value for item in variant.qualified_facts.roots
                       if type(item) is assumptions.ReportedDilutedEPS)
        self.assertEqual(actual, expected)

    def test_exact_decimal_fraction_bridge_precedes_single_float_boundary(self):
        value = Decimal("0.1000000000000000000000000001")
        self.assertEqual(pr5e._adapt_eps(value, 2, 3),
                         float(Fraction(value) * Fraction(2, 3)))
        tree = ast.parse(Path(pr5e.__file__).read_text())
        function = next(node for node in tree.body
                        if isinstance(node, ast.FunctionDef)
                        and node.name == "_adapt_eps")
        float_calls = [node for node in ast.walk(function)
                       if isinstance(node, ast.Call)
                       and isinstance(node.func, ast.Name)
                       and node.func.id == "float"]
        self.assertEqual(len(float_calls), 1)

    def test_all_closed_statuses_and_identity_conflict_precedence(self):
        cases = (
            (pr5d2.PR5D2BundleStatus.PR5D_ROOTS_UNAVAILABLE,
             pr5e.PR5EStatus.UNAVAILABLE, pr5e.PR5EReason.PR5D2_ROOTS_UNAVAILABLE),
            (pr5d2.PR5D2BundleStatus.PR5D_ROOTS_UNSUPPORTED,
             pr5e.PR5EStatus.UNSUPPORTED, pr5e.PR5EReason.PR5D2_ROOTS_UNSUPPORTED),
            (pr5d2.PR5D2BundleStatus.SOURCE_CONFLICT,
             pr5e.PR5EStatus.SOURCE_CONFLICT, pr5e.PR5EReason.PR5D2_SOURCE_CONFLICT),
        )
        for upstream_status, expected_status, reason in cases:
            changed = replace(self.built["result"], status=upstream_status)
            with self.subTest(upstream_status=upstream_status), patch.object(
                    pr5e, "assemble_expected_return_pr5d_bundle",
                    return_value=changed):
                result = self.call(self.request_for(changed))
                self.assertIs(result.status, expected_status)
                self.assertIn(reason, result.reasons)
                self.assertIsNone(result.qualified_facts)
        mismatch = pr5e.PR5ERealExpectedReturnRequest(
            self.built["request"], "0" * 64, "1" * 64)
        result = self.call(mismatch)
        self.assertIs(result.status, pr5e.PR5EStatus.SOURCE_CONFLICT)
        self.assertIn(pr5e.PR5EReason.PR5D2_REPLAY_IDENTITY_MISMATCH,
                      result.reasons)

    def test_policy_is_reconstructed_verified_and_constructor_receives_nonpayer_roles(self):
        approved = pr5e.get_owner_approved_policy_proposal().proposal
        with patch.object(assumptions, "construct_expected_return",
                          wraps=assumptions.construct_expected_return) as constructor:
            result = self.call()
        self.assertIs(result.status, pr5e.PR5EStatus.REAL_EXPECTED_RETURN_ADMITTED)
        constructor.assert_called_once()
        kwargs = constructor.call_args.kwargs
        self.assertEqual(kwargs["mature_policy"], approved.mature_policy)
        self.assertEqual(kwargs["terminal_policy"], approved.terminal_policy)
        self.assertEqual(kwargs["distribution_policy"],
                         approved.nonpayer_distribution_policy)
        changed = replace(self.built["result"], approved_proposal_hash="0" * 64)
        with patch.object(pr5e, "assemble_expected_return_pr5d_bundle",
                          return_value=changed):
            conflict = self.call(self.request_for(changed))
        self.assertIs(conflict.status, pr5e.PR5EStatus.SOURCE_CONFLICT)
        self.assertIn(pr5e.PR5EReason.APPROVED_POLICY_IDENTITY_MISMATCH,
                      conflict.reasons)

    def test_payer_and_broader_authority_remain_explicitly_unsupported(self):
        result = self.call()
        self.assertIn("PAYER_ROUTE_UNSUPPORTED", result.limitations)
        self.assertIn("NO_HISTORICAL_AS_OF_OR_PIT_AUTHORITY", result.limitations)
        self.assertIn("ROUTE_LOCAL_SECURITY_IDENTITY_ONLY", result.limitations)
        self.assertIn("NO_UNIVERSAL_CORPORATE_ACTION_COMPLETENESS_CLAIM",
                      result.limitations)
        self.assertNotIn("HISTORICAL_AS_OF", result.construction.diagnostic.authority)
        with self.assertRaises(FrozenInstanceError):
            result.status = pr5e.PR5EStatus.UNAVAILABLE


class PR5EIsolationTests(unittest.TestCase):
    def test_adapter_has_no_clock_or_direct_calculator_and_no_authority_shortcuts(self):
        tree = ast.parse(Path(pr5e.__file__).read_text())
        calls = {node.func.attr if isinstance(node.func, ast.Attribute)
                 else node.func.id if isinstance(node.func, ast.Name) else ""
                 for node in ast.walk(tree) if isinstance(node, ast.Call)}
        self.assertFalse({"now", "today", "calculate_expected_return"} & calls)
        public = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                      and node.name == "admit_real_expected_return_pr5e")
        arguments = {item.arg for item in (*public.args.posonlyargs,
                                           *public.args.args,
                                           *public.args.kwonlyargs)}
        self.assertFalse({"as_of", "qualified", "same_basis", "pr5d2_result"}
                         & arguments)

    def test_no_v1_runtime_portfolio_or_production_consumer_imports_pr5e(self):
        root = Path(pr5e.__file__).resolve().parents[1]
        allowed = Path(pr5e.__file__).resolve()
        for path in (root / "main.py", *sorted((root / "src").glob("*.py")),
                     *sorted((root / "pit_comparison").glob("*.py"))):
            if path.resolve() == allowed:
                continue
            self.assertNotIn("expected_return_pr5e_adapter", path.read_text(), str(path))

    def test_real_extension_does_not_change_synthetic_contract_shape(self):
        self.assertEqual(
            tuple(field.name for field in assumptions.Provenance.__dataclass_fields__.values()),
            ("source_kind", "source_reference", "source_version",
             "source_document_hash", "source_locator", "published_at",
             "available_at", "captured_at", "extractor_id",
             "extractor_version"),
        )


if __name__ == "__main__":
    unittest.main()
