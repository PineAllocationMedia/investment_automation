"""Adversarial tests for bounded confidence propagation."""
import ast
from dataclasses import fields, replace
from pathlib import Path
import tempfile
import unittest

from economic_facts import cash_like_current_carry as cash_carry
from economic_facts import vfv_current_evidence
from src import bounded_confidence_projection as projection
from src import company_vfv_expected_return_comparator as comparator
from src import expected_return_engine
from src import expected_return_pr5e_adapter as pr5e
from src import vfv_forward_er_policy
from src import vfv_forward_expected_return as vfv_er
from tests.test_cash_like_current_carry import qualify as qualify_cash
from tests.test_expected_return_pr5e_adapter import PR5EFixtureMixin
from tests.test_vfv_fx_hedge_evidence import standard_qualification
from tests.vfv_current_evidence_fixtures import publish_bundle, request_for


class BoundedConfidenceProjectionTests(PR5EFixtureMixin, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        fixture = cls.built["fixture"]
        roots = cls.built["result"]
        admission_request = pr5e.PR5ERealExpectedReturnRequest(
            cls.built["request"], roots.semantic_id, roots.evidence_id)
        cls.company = pr5e.admit_real_expected_return_pr5e(
            fixture.current_archive,
            fixture.submissions_archive,
            fixture.filing_archive,
            fixture.sec_archive,
            fixture.nasdaq_archive,
            cls.builder.quote_archive,
            cls.builder.split_archive,
            admission_request,
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
        company_problem = comparator.identify_company_expected_return_problem(
            cls.company)
        comparison_request = comparator.CompanyVFVComparisonRequest(
            company_problem.semantic_id,
            company_problem.evidence_id,
            cls.vfv.semantic_id,
            cls.vfv.evidence_id,
            cls.hedge.semantic_id,
            cls.hedge.evidence_id,
        )
        cls.comparison = comparator.compare_company_vfv_expected_returns(
            cls.company, cls.vfv, cls.hedge, comparison_request)
        cls.cash = qualify_cash()

    @classmethod
    def tearDownClass(cls):
        cls.vfv_temporary.cleanup()
        super().tearDownClass()

    def project(self, value):
        return projection.project_bounded_confidence(value)

    def test_accepts_exact_closed_canonical_types_only(self):
        expected = (
            (self.company,
             projection.BoundedConfidenceAnalysisKind.COMPANY_EXPECTED_RETURN),
            (self.vfv,
             projection.BoundedConfidenceAnalysisKind.VFV_FORWARD_EXPECTED_RETURN),
            (self.comparison,
             projection.BoundedConfidenceAnalysisKind.
             COMPANY_VFV_EXPECTED_RETURN_COMPARATOR),
            (self.cash,
             projection.BoundedConfidenceAnalysisKind.CASH_LIKE_CURRENT_CARRY),
        )
        for value, kind in expected:
            with self.subTest(kind=kind):
                self.assertIs(self.project(value).analysis_kind, kind)

    def test_mappings_detached_diagnostics_and_wrong_surfaces_raise(self):
        wrong = (
            {},
            {"status": "AVAILABLE"},
            self.company.construction.diagnostic,
            self.company.qualified_facts,
            self.company.upstream_pr5d2,
            self.hedge,
        )
        for value in wrong:
            with self.subTest(value_type=type(value)), self.assertRaises(
                    projection.BoundedConfidenceProjectionError):
                self.project(value)

    def test_company_degraded_is_available_and_native_confidence_is_exact(self):
        diagnostic = self.company.construction.diagnostic
        self.assertEqual(diagnostic.status, "DEGRADED")
        result = self.project(self.company)
        self.assertIs(
            result.capability_status,
            projection.BoundedConfidenceCapabilityStatus.AVAILABLE,
        )
        self.assertIs(
            result.confidence_representation,
            projection.BoundedConfidenceRepresentation.NATIVE_CATEGORICAL,
        )
        self.assertIs(result.detail.component_confidence,
                      diagnostic.confidence)
        self.assertEqual(result.detail.overall_confidence,
                         diagnostic.overall_confidence)
        self.assertIs(result.detail.assessments,
                      self.company.construction.confidence)

    def test_company_assessments_are_propagated_without_recomputation(self):
        result = self.project(self.company)
        self.assertEqual(result.detail.assessments,
                         self.company.construction.confidence)
        self.assertEqual(
            tuple(item.category for item in result.detail.assessments),
            tuple(item.category
                  for item in self.company.construction.confidence),
        )
        self.assertEqual(
            result.detail.component_confidence,
            self.company.construction.diagnostic.confidence,
        )

    def test_company_closed_failure_statuses_map_without_confidence_detail(self):
        cases = (
            (pr5e.PR5EStatus.UNAVAILABLE,
             pr5e.PR5EReason.PR5D2_ROOTS_UNAVAILABLE,
             projection.BoundedConfidenceCapabilityStatus.UNAVAILABLE),
            (pr5e.PR5EStatus.UNSUPPORTED,
             pr5e.PR5EReason.PR5D2_ROOTS_UNSUPPORTED,
             projection.BoundedConfidenceCapabilityStatus.UNSUPPORTED),
            (pr5e.PR5EStatus.SOURCE_CONFLICT,
             pr5e.PR5EReason.PR5D2_SOURCE_CONFLICT,
             projection.BoundedConfidenceCapabilityStatus.SOURCE_CONFLICT),
        )
        for status, reason, expected in cases:
            company = replace(self.company, status=status, reasons=(reason,))
            with self.subTest(status=status):
                result = self.project(company)
                self.assertIs(result.capability_status, expected)
                self.assertIs(
                    result.confidence_representation,
                    projection.BoundedConfidenceRepresentation.NOT_APPLICABLE,
                )
                self.assertIsNone(result.detail)
                self.assertIs(result.upstream_status, status)
                self.assertEqual(result.upstream_reasons, (reason,))

    def test_impossible_admitted_company_shape_raises(self):
        impossible = (
            replace(self.company, construction=None),
            replace(
                self.company,
                construction=replace(
                    self.company.construction, status="UNAVAILABLE")),
            replace(
                self.company,
                construction=replace(
                    self.company.construction,
                    diagnostic=replace(
                        self.company.construction.diagnostic,
                        scenarios=(),
                    ),
                ),
            ),
        )
        for company in impossible:
            with self.subTest(company=company), self.assertRaises(
                    projection.BoundedConfidenceProjectionError):
                self.project(company)

    def test_available_vfv_preserves_exact_native_low_confidence(self):
        result = self.project(self.vfv)
        self.assertIs(
            result.capability_status,
            projection.BoundedConfidenceCapabilityStatus.AVAILABLE,
        )
        self.assertIs(result.detail, self.vfv.confidence)
        self.assertIs(
            result.detail.overall_vfv_er_confidence,
            vfv_er.VFVForwardERConfidenceLevel.LOW,
        )

    def test_nonavailable_vfv_uses_not_applicable_not_native_none(self):
        none = vfv_er.VFVForwardERConfidence(
            vfv_er.VFVForwardEREvidenceAuthority.NONE,
            vfv_er.VFVForwardERAssumptionDependence.NONE,
            vfv_er.VFVForwardERCurrencyBasisStatus.NONE,
            vfv_er.VFVForwardERConfidenceLevel.NONE,
        )
        for status in (
                vfv_er.VFVForwardERStatus.UNAVAILABLE,
                vfv_er.VFVForwardERStatus.UNSUPPORTED,
                vfv_er.VFVForwardERStatus.SOURCE_CONFLICT):
            value = replace(
                self.vfv, status=status, reasons=("CLOSED_REASON",),
                confidence=none)
            with self.subTest(status=status):
                result = self.project(value)
                self.assertIs(
                    result.confidence_representation,
                    projection.BoundedConfidenceRepresentation.NOT_APPLICABLE)
                self.assertIsNone(result.detail)
                self.assertEqual(result.upstream_reasons, ("CLOSED_REASON",))

    def test_available_comparator_preserves_exact_local_low(self):
        result = self.project(self.comparison)
        self.assertIs(
            result.capability_status,
            projection.BoundedConfidenceCapabilityStatus.AVAILABLE)
        self.assertIs(
            result.detail,
            comparator.CompanyVFVComparisonConfidence.LOW)
        self.assertIs(result.detail,
                      self.comparison.local_comparator_confidence)

    def test_nonavailable_comparator_has_no_confidence_detail(self):
        for status in (
                comparator.CompanyVFVComparisonStatus.UNAVAILABLE,
                comparator.CompanyVFVComparisonStatus.UNSUPPORTED,
                comparator.CompanyVFVComparisonStatus.SOURCE_CONFLICT):
            value = replace(
                self.comparison,
                status=status,
                reasons=(comparator.CompanyVFVComparisonReason.
                         NUMERICAL_SPREAD_UNAVAILABLE,),
                local_comparator_confidence=(
                    comparator.CompanyVFVComparisonConfidence.NONE),
            )
            with self.subTest(status=status):
                result = self.project(value)
                self.assertIs(
                    result.confidence_representation,
                    projection.BoundedConfidenceRepresentation.NOT_APPLICABLE)
                self.assertIsNone(result.detail)

    def test_available_cash_is_evidence_context_only_without_category(self):
        result = self.project(self.cash)
        self.assertIs(
            result.confidence_representation,
            projection.BoundedConfidenceRepresentation.EVIDENCE_CONTEXT_ONLY)
        self.assertIs(
            result.detail.authority_scope,
            self.cash.authority_scope)
        self.assertIs(result.detail.freshness,
                      self.cash.evidence.freshness)
        self.assertIs(result.detail.availability_semantics,
                      self.cash.evidence.availability_semantics)
        self.assertIs(result.detail.publication_semantics,
                      self.cash.evidence.publication_semantics)
        self.assertFalse(hasattr(result.detail, "category"))
        self.assertFalse(hasattr(result.detail, "rate"))

    def test_nonavailable_cash_is_not_applicable(self):
        unavailable = cash_carry.qualify_cash_like_current_carry(None)
        result = self.project(unavailable)
        self.assertIs(
            result.capability_status,
            projection.BoundedConfidenceCapabilityStatus.UNAVAILABLE)
        self.assertIs(
            result.confidence_representation,
            projection.BoundedConfidenceRepresentation.NOT_APPLICABLE)
        self.assertIsNone(result.detail)
        self.assertEqual(result.upstream_reasons, unavailable.reasons)

    def test_projection_has_no_analytical_numeric_output_surface(self):
        names = {field.name for field in fields(
            projection.BoundedConfidenceProjection)}
        detail_names = {
            field.name
            for detail_type in (
                projection.CompanyExpectedReturnConfidenceDetail,
                projection.CashLikeCurrentCarryEvidenceContext,
            )
            for field in fields(detail_type)
        }
        prohibited = {
            "annualized_return", "scenario_returns", "scenario_spreads",
            "spread", "cash_rate", "carry_rate", "execution_cost",
            "executable_net_er", "score", "probability", "confidence_band",
        }
        self.assertFalse(names & prohibited)
        self.assertFalse(detail_names & prohibited)
        for value in (self.company, self.vfv, self.comparison, self.cash):
            payload = self.project(value).to_dict()[
                "bounded_confidence_projection"]
            self.assertNotIn("scenarios", payload)
            self.assertNotIn("scenario_spreads", payload)
            self.assertNotIn("fact", payload)

    def test_projection_does_not_mutate_upstream_objects(self):
        values = (self.company, self.vfv, self.comparison, self.cash)
        identities = tuple(
            (value.admission_semantic_id, value.admission_evidence_id)
            if type(value) is pr5e.PR5EAdmissionResult
            else (value.semantic_id, value.evidence_id)
            for value in values
        )
        snapshots = tuple(values)
        for value in values:
            self.project(value)
        self.assertEqual(values, snapshots)
        self.assertEqual(
            identities,
            tuple(
                (value.admission_semantic_id, value.admission_evidence_id)
                if type(value) is pr5e.PR5EAdmissionResult
                else (value.semantic_id, value.evidence_id)
                for value in values
            ),
        )

    def test_repeated_input_is_deterministic(self):
        for value in (self.company, self.vfv, self.comparison, self.cash):
            with self.subTest(value_type=type(value)):
                first = self.project(value)
                second = self.project(value)
                self.assertEqual(first, second)
                self.assertEqual(first.semantic_id, second.semantic_id)
                self.assertEqual(first.evidence_id, second.evidence_id)

    def test_confidence_semantic_change_changes_projection_semantic_id(self):
        diagnostic = self.company.construction.diagnostic
        changed_components = replace(
            diagnostic.confidence, fundamental="MEDIUM")
        assessments = self.company.construction.confidence
        changed_assessment = replace(assessments[0], category="MEDIUM")
        changed_construction = replace(
            self.company.construction,
            confidence=(changed_assessment, *assessments[1:]),
            diagnostic=replace(
                diagnostic, confidence=changed_components),
        )
        changed_company = replace(
            self.company, construction=changed_construction)
        self.assertNotEqual(
            self.project(self.company).semantic_id,
            self.project(changed_company).semantic_id,
        )

    def test_evidence_only_recapture_preserves_semantics_changes_evidence(self):
        recaptured = replace(self.vfv, upstream_evidence_id="f" * 64)
        self.assertEqual(self.vfv.semantic_id, recaptured.semantic_id)
        self.assertNotEqual(self.vfv.evidence_id, recaptured.evidence_id)
        first = self.project(self.vfv)
        second = self.project(recaptured)
        self.assertEqual(first.semantic_id, second.semantic_id)
        self.assertNotEqual(first.evidence_id, second.evidence_id)

    def test_company_root_lineage_is_evidence_not_semantic_material(self):
        assessments = self.company.construction.confidence
        changed_assessment = replace(
            assessments[0], root_ids=(*assessments[0].root_ids,
                                      "recapture:lineage"))
        changed_company = replace(
            self.company,
            construction=replace(
                self.company.construction,
                confidence=(changed_assessment, *assessments[1:]),
            ),
        )
        first = self.project(self.company)
        second = self.project(changed_company)
        self.assertEqual(first.upstream_semantic_id,
                         second.upstream_semantic_id)
        self.assertEqual(first.upstream_evidence_id,
                         second.upstream_evidence_id)
        self.assertEqual(first.semantic_id, second.semantic_id)
        self.assertNotEqual(first.evidence_id, second.evidence_id)

    def test_positive_projection_identity_fixtures_are_pinned(self):
        stable_vfv_evidence = tuple(
            replace(
                item,
                artifact_receipt_id=f"{index + 1:064x}",
                content_sha256=f"{index + 101:064x}",
            )
            for index, item in enumerate(self.vfv.fact_evidence)
        )
        stable_vfv = replace(
            self.vfv,
            upstream_evidence_id="e" * 64,
            fact_evidence=stable_vfv_evidence,
        )
        stable_comparison = replace(
            self.comparison,
            vfv_evidence_id=stable_vfv.evidence_id,
        )
        expected = {
            projection.BoundedConfidenceAnalysisKind.COMPANY_EXPECTED_RETURN:
                (
                    "f461d62d1901b5ebf9765cd7cebc4b42259f9fefaf9868cda9d08b4349464968",
                    "6569c6d106d07727c0d7343dfd8d4a20c458c6445550d77028d085d837a1e0b0",
                ),
            projection.BoundedConfidenceAnalysisKind.VFV_FORWARD_EXPECTED_RETURN:
                (
                    "876a04374ba5b639cedc072c2be6db941c20dfa1c1de850570cd4506a6f456a0",
                    "2cd0967ab85e0ce5af5846f8ca06904180e444b1b7fee86ce59401a4c2f2b2a9",
                ),
            projection.BoundedConfidenceAnalysisKind.
            COMPANY_VFV_EXPECTED_RETURN_COMPARATOR:
                (
                    "f0a466ce2e58c29b47c9dbbd8d9b19e32515b37106313004cc7672966a2a5f3a",
                    "6f330ed765ca4a8baf37fdc8971350bb1f9a0e74c78fecfe05504d9681cadd67",
                ),
            projection.BoundedConfidenceAnalysisKind.CASH_LIKE_CURRENT_CARRY:
                (
                    "58f69cbf32882e39837479a9f798ecff5e439aad6acdd0bf546fd5fcec6ce505",
                    "da729b722c77a6343a3bac7279f423fccf18fdfc54e18ea8f982f98329b704d6",
                ),
        }
        for value in (
                self.company, stable_vfv, stable_comparison, self.cash):
            result = self.project(value)
            with self.subTest(kind=result.analysis_kind):
                self.assertEqual(
                    (result.semantic_id, result.evidence_id),
                    expected[result.analysis_kind],
                )

    def test_authority_and_required_limitations_are_always_present(self):
        values = (
            self.company,
            self.vfv,
            self.comparison,
            self.cash,
            cash_carry.qualify_cash_like_current_carry(None),
        )
        required = set(projection.BoundedConfidenceProjectionLimitation)
        for value in values:
            with self.subTest(value_type=type(value)):
                result = self.project(value)
                self.assertIs(
                    result.authority,
                    projection.BoundedConfidenceProjectionAuthority.
                    CONFIDENCE_PROJECTION_ONLY)
                self.assertEqual(set(result.limitations), required)

    def test_static_isolation_from_legacy_and_decision_surfaces(self):
        source = Path(projection.__file__).read_text()
        tree = ast.parse(source)
        imports = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        imports.update(
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        )
        lowered_imports = " ".join(imports).casefold()
        for prohibited in (
                "confidence_range_engine", "conviction", "sizing",
                "recommendation", "broker", "executable_entry"):
            self.assertNotIn(prohibited, lowered_imports)
        public_fields = " ".join(
            field.name for field in fields(
                projection.BoundedConfidenceProjection)).casefold()
        for prohibited in (
                "conviction", "sizing", "recommendation", "broker", "b2"):
            self.assertNotIn(prohibited, public_fields)

    def test_module_has_no_network_filesystem_or_runtime_clock_acquisition(self):
        source = Path(projection.__file__).read_text()
        tree = ast.parse(source)
        imports = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        imports.update(
            node.module.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        )
        self.assertTrue(
            {"requests", "urllib", "httpx", "socket", "pathlib"}.
            isdisjoint(imports))
        calls = {
            node.func.attr if isinstance(node.func, ast.Attribute)
            else node.func.id if isinstance(node.func, ast.Name) else ""
            for node in ast.walk(tree) if isinstance(node, ast.Call)
        }
        self.assertFalse({
            "open", "read_text", "read_bytes", "getenv", "now", "today",
            "utcnow", "urlopen",
        } & calls)


if __name__ == "__main__":
    unittest.main()
