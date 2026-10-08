"""Adversarial tests for explicit Stage-B non-available case handling."""
import ast
from dataclasses import FrozenInstanceError, fields, replace
import json
from pathlib import Path
import tempfile
import unittest

from economic_facts import cash_like_current_carry as cash_carry
from economic_facts import executable_entry_evidence as executable_entry
from economic_facts import vfv_current_evidence
from src import company_vfv_expected_return_comparator as comparator
from src import expected_return_pr5e_adapter as pr5e
from src import explicit_unsupported_case as explicit_case
from src import vfv_forward_er_policy
from src import vfv_forward_expected_return as vfv_er
from tests.test_cash_like_current_carry import qualify as qualify_cash
from tests.test_expected_return_pr5e_adapter import PR5EFixtureMixin
from tests.test_vfv_fx_hedge_evidence import standard_qualification
from tests.vfv_current_evidence_fixtures import publish_bundle, request_for


class ExplicitUnsupportedCaseTests(PR5EFixtureMixin, unittest.TestCase):
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
        request = vfv_er.VFVForwardERRequest(
            "VFV",
            vfv_er.VFV_FORWARD_ER_ANALYTICAL_BASIS,
            qualification.semantic_id,
            qualification.evidence_id,
            policy.policy_id,
            policy.content_hash,
        )
        cls.vfv = vfv_er.calculate_vfv_forward_expected_return(
            qualification, request)
        cls.hedge = standard_qualification()
        problem = comparator.identify_company_expected_return_problem(
            cls.company)
        comparison_request = comparator.CompanyVFVComparisonRequest(
            problem.semantic_id,
            problem.evidence_id,
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
        return explicit_case.project_explicit_unsupported_case(value)

    def non_available_inputs(self):
        return (
            replace(
                self.company,
                status=pr5e.PR5EStatus.UNAVAILABLE,
                reasons=(pr5e.PR5EReason.PR5D2_ROOTS_UNAVAILABLE,),
            ),
            replace(
                self.vfv,
                status=vfv_er.VFVForwardERStatus.UNSUPPORTED,
                reasons=(
                    vfv_er.VFVForwardERReason.
                    NON_VFV_INSTRUMENT_UNSUPPORTED,
                ),
            ),
            replace(
                self.comparison,
                status=comparator.CompanyVFVComparisonStatus.SOURCE_CONFLICT,
                reasons=(
                    comparator.CompanyVFVComparisonReason.
                    VFV_UPSTREAM_SOURCE_CONFLICT,
                ),
            ),
            cash_carry.qualify_cash_like_current_carry(None),
        )

    def test_accepts_exact_four_canonical_runtime_types_only(self):
        expected = (
            (replace(
                self.company,
                status=pr5e.PR5EStatus.UNAVAILABLE,
                reasons=(pr5e.PR5EReason.PR5D2_ROOTS_UNAVAILABLE,),
            ), explicit_case.StageBAnalysisKind.COMPANY_EXPECTED_RETURN),
            (replace(
                self.vfv,
                status=vfv_er.VFVForwardERStatus.UNAVAILABLE,
                reasons=(vfv_er.VFVForwardERReason.UPSTREAM_UNAVAILABLE,),
            ), explicit_case.StageBAnalysisKind.VFV_FORWARD_EXPECTED_RETURN),
            (replace(
                self.comparison,
                status=comparator.CompanyVFVComparisonStatus.UNAVAILABLE,
                reasons=(comparator.CompanyVFVComparisonReason.
                         COMPANY_UPSTREAM_UNAVAILABLE,),
            ), explicit_case.StageBAnalysisKind.
             COMPANY_VFV_EXPECTED_RETURN_COMPARATOR),
            (cash_carry.qualify_cash_like_current_carry(None),
             explicit_case.StageBAnalysisKind.CASH_LIKE_CURRENT_CARRY),
        )
        for value, kind in expected:
            with self.subTest(kind=kind):
                self.assertIs(self.project(value).analysis_kind, kind)

    def test_mappings_detached_diagnostics_ducks_and_wrong_objects_raise(self):
        class Duck:
            status = "UNAVAILABLE"
            reasons = ("DETACHED",)
            semantic_id = "a" * 64
            evidence_id = "b" * 64

        wrong = (
            {},
            {"status": "UNAVAILABLE"},
            self.company.construction.diagnostic,
            self.company.qualified_facts,
            self.company.upstream_pr5d2,
            self.hedge,
            Duck(),
            object(),
        )
        for value in wrong:
            with self.subTest(value_type=type(value)), self.assertRaises(
                    explicit_case.ExplicitUnsupportedCaseError):
                self.project(value)

    def test_all_four_available_inputs_return_exactly_none(self):
        for value in (self.company, self.vfv, self.comparison, self.cash):
            with self.subTest(value_type=type(value)):
                self.assertIsNone(self.project(value))

    def test_each_closed_status_and_native_reason_is_preserved(self):
        cases = (
            (
                pr5e.PR5EStatus.UNAVAILABLE,
                pr5e.PR5EReason.PR5D2_ROOTS_UNAVAILABLE,
                explicit_case.StageBCapabilityStatus.UNAVAILABLE,
            ),
            (
                pr5e.PR5EStatus.UNSUPPORTED,
                pr5e.PR5EReason.PR5D2_ROOTS_UNSUPPORTED,
                explicit_case.StageBCapabilityStatus.UNSUPPORTED,
            ),
            (
                pr5e.PR5EStatus.SOURCE_CONFLICT,
                pr5e.PR5EReason.PR5D2_SOURCE_CONFLICT,
                explicit_case.StageBCapabilityStatus.SOURCE_CONFLICT,
            ),
        )
        for status, reason, common_status in cases:
            company = replace(self.company, status=status, reasons=(reason,))
            with self.subTest(status=status):
                result = self.project(company)
                self.assertIs(result.capability_status, common_status)
                self.assertIs(result.upstream_status, status)
                self.assertEqual(result.upstream_reasons, (reason,))

    def test_closed_statuses_remain_distinct_for_every_analysis_kind(self):
        cases = (
            (
                self.company,
                (
                    pr5e.PR5EStatus.UNAVAILABLE,
                    pr5e.PR5EStatus.UNSUPPORTED,
                    pr5e.PR5EStatus.SOURCE_CONFLICT,
                ),
                pr5e.PR5EReason.PR5D2_ROOTS_UNAVAILABLE,
            ),
            (
                self.vfv,
                (
                    vfv_er.VFVForwardERStatus.UNAVAILABLE,
                    vfv_er.VFVForwardERStatus.UNSUPPORTED,
                    vfv_er.VFVForwardERStatus.SOURCE_CONFLICT,
                ),
                vfv_er.VFVForwardERReason.UPSTREAM_UNAVAILABLE,
            ),
            (
                self.comparison,
                (
                    comparator.CompanyVFVComparisonStatus.UNAVAILABLE,
                    comparator.CompanyVFVComparisonStatus.UNSUPPORTED,
                    comparator.CompanyVFVComparisonStatus.SOURCE_CONFLICT,
                ),
                comparator.CompanyVFVComparisonReason.
                NUMERICAL_SPREAD_UNAVAILABLE,
            ),
            (
                self.cash,
                (
                    cash_carry.CashLikeCurrentCarryStatus.UNAVAILABLE,
                    cash_carry.CashLikeCurrentCarryStatus.UNSUPPORTED,
                    cash_carry.CashLikeCurrentCarryStatus.SOURCE_CONFLICT,
                ),
                cash_carry.CashLikeCurrentCarryReason.RATE_UNAVAILABLE,
            ),
        )
        for value, statuses, reason in cases:
            results = tuple(
                self.project(replace(value, status=status, reasons=(reason,)))
                for status in statuses
            )
            with self.subTest(value_type=type(value)):
                self.assertEqual(
                    tuple(item.capability_status for item in results),
                    tuple(explicit_case.StageBCapabilityStatus),
                )
                self.assertEqual(len({item.semantic_id for item in results}), 3)

    def test_unknown_future_upstream_status_is_contract_error(self):
        for value in (self.company, self.vfv, self.comparison, self.cash):
            changed = replace(value, status="FUTURE_STATE")
            with self.subTest(value_type=type(value)), self.assertRaises(
                    explicit_case.ExplicitUnsupportedCaseError):
                self.project(changed)

    def test_case_surface_is_exact_and_has_no_confidence_or_reason_class(self):
        self.assertEqual(
            tuple(field.name for field in fields(
                explicit_case.StageBNonAvailableCase)),
            (
                "contract_version",
                "representation_version",
                "analysis_kind",
                "capability_status",
                "upstream_status",
                "upstream_reasons",
                "upstream_semantic_id",
                "upstream_evidence_id",
                "authority",
                "limitations",
            ),
        )
        result = self.project(self.non_available_inputs()[0])
        self.assertTrue(hasattr(result, "semantic_id"))
        self.assertTrue(hasattr(result, "evidence_id"))
        prohibited = {
            "confidence", "reason_class", "partial", "deferred", "error",
            "failed", "annualized_return", "scenario_returns",
            "scenario_spreads", "spread", "carry_rate", "rate",
            "execution_cost", "executable_net_er", "score", "probability",
        }
        self.assertFalse(
            prohibited & {field.name.casefold() for field in fields(result)})

    def test_no_partial_deferred_available_or_generic_failure_state_exists(self):
        self.assertEqual(
            {item.value for item in explicit_case.StageBCapabilityStatus},
            {"UNAVAILABLE", "UNSUPPORTED", "SOURCE_CONFLICT"},
        )
        for name in (
                "PARTIAL", "DEFERRED", "AVAILABLE", "LOW_CONFIDENCE",
                "ERROR", "FAILED"):
            self.assertFalse(hasattr(explicit_case.StageBCapabilityStatus, name))

    def test_executable_entry_and_its_preserved_facts_are_rejected(self):
        b1 = executable_entry.qualify_executable_entry_evidence(None)
        before = b1
        with self.assertRaises(explicit_case.ExplicitUnsupportedCaseError):
            self.project(b1)
        self.assertIs(b1, before)
        self.assertNotIn(
            "facts",
            {field.name for field in fields(explicit_case.StageBNonAvailableCase)},
        )

    def test_no_analytical_numbers_or_upstream_facts_are_serialized(self):
        prohibited_keys = {
            "fact", "facts", "scenarios", "scenario_spreads", "rate",
            "confidence", "source_payload", "evidence_hashes", "timestamps",
        }
        for value in self.non_available_inputs():
            result = self.project(value)
            payload = result.to_dict()["stage_b_non_available_case"]
            with self.subTest(kind=result.analysis_kind):
                self.assertTrue(prohibited_keys.isdisjoint(payload))

    def test_repeated_projection_and_serialization_are_deterministic(self):
        for value in self.non_available_inputs():
            first = self.project(value)
            second = self.project(value)
            with self.subTest(kind=first.analysis_kind):
                self.assertEqual(first, second)
                self.assertEqual(first.semantic_id, second.semantic_id)
                self.assertEqual(first.evidence_id, second.evidence_id)
                self.assertEqual(
                    json.dumps(first.to_dict(), sort_keys=True,
                               separators=(",", ":"), allow_nan=False),
                    json.dumps(second.to_dict(), sort_keys=True,
                               separators=(",", ":"), allow_nan=False),
                )

    def test_status_and_reason_changes_change_semantic_identity(self):
        unavailable = replace(
            self.vfv,
            status=vfv_er.VFVForwardERStatus.UNAVAILABLE,
            reasons=(vfv_er.VFVForwardERReason.UPSTREAM_UNAVAILABLE,),
        )
        unsupported = replace(
            unavailable,
            status=vfv_er.VFVForwardERStatus.UNSUPPORTED,
            reasons=(vfv_er.VFVForwardERReason.UPSTREAM_UNAVAILABLE,),
        )
        changed_reason = replace(
            unavailable,
            reasons=(vfv_er.VFVForwardERReason.REQUIRED_FACT_ABSENT,),
        )
        baseline = self.project(unavailable)
        self.assertNotEqual(
            baseline.semantic_id, self.project(unsupported).semantic_id)
        self.assertNotEqual(
            baseline.semantic_id, self.project(changed_reason).semantic_id)

    def test_evidence_only_recapture_preserves_semantics_changes_evidence(self):
        unavailable = replace(
            self.vfv,
            status=vfv_er.VFVForwardERStatus.UNAVAILABLE,
            reasons=(vfv_er.VFVForwardERReason.UPSTREAM_UNAVAILABLE,),
        )
        recaptured = replace(unavailable, upstream_evidence_id="f" * 64)
        self.assertEqual(unavailable.semantic_id, recaptured.semantic_id)
        self.assertNotEqual(unavailable.evidence_id, recaptured.evidence_id)
        first = self.project(unavailable)
        second = self.project(recaptured)
        self.assertEqual(first.semantic_id, second.semantic_id)
        self.assertNotEqual(first.evidence_id, second.evidence_id)

    def test_representative_non_available_identity_fixtures_are_pinned(self):
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
            status=vfv_er.VFVForwardERStatus.UNSUPPORTED,
            reasons=(
                vfv_er.VFVForwardERReason.NON_VFV_INSTRUMENT_UNSUPPORTED,
            ),
            upstream_evidence_id="e" * 64,
            fact_evidence=stable_vfv_evidence,
        )
        stable_comparison = replace(
            self.comparison,
            status=comparator.CompanyVFVComparisonStatus.SOURCE_CONFLICT,
            reasons=(
                comparator.CompanyVFVComparisonReason.
                VFV_UPSTREAM_SOURCE_CONFLICT,
            ),
            vfv_evidence_id=stable_vfv.evidence_id,
        )
        expected = {
            explicit_case.StageBAnalysisKind.COMPANY_EXPECTED_RETURN: (
                "6200b76daced34e0c53430f271afae0341cc37b2ce4ffd56886a1b4fcfeccc9a",
                "fa018b959e734d384112e4f99c5798bc690057ab8e93c2e2691402547f466962",
            ),
            explicit_case.StageBAnalysisKind.VFV_FORWARD_EXPECTED_RETURN: (
                "809fb6605983dcc73539d5253844d7614f6ca57804251196a4342f760d1d5048",
                "c465fa2929517002a62a9059627b308866d4cf2c15ae47cb224b69f4fc503eb3",
            ),
            explicit_case.StageBAnalysisKind.
            COMPANY_VFV_EXPECTED_RETURN_COMPARATOR: (
                "eaf7594d58ff0db0f836240e993bac71e96640a6b0c2cd233bb0d031f1a6c7d1",
                "db5bd19bdf94db07cc5a4fd7f6890849e1e7bf1649c55c52b40c6168d9b9f5e7",
            ),
            explicit_case.StageBAnalysisKind.CASH_LIKE_CURRENT_CARRY: (
                "6bcf0abe3b20acdedb9b513795ffb873d46c336f0a7b19147e165afa6d2c7eb8",
                "6f2ba5144db37630c0d87584f5ea5b1753f188359d5d1279b75b9759a3b82366",
            ),
        }
        company, _, _, cash = self.non_available_inputs()
        for value in (company, stable_vfv, stable_comparison, cash):
            result = self.project(value)
            with self.subTest(kind=result.analysis_kind):
                self.assertEqual(
                    (result.semantic_id, result.evidence_id),
                    expected[result.analysis_kind],
                )

    def test_authority_and_required_limitations_are_always_present(self):
        required = set(explicit_case.StageBNonAvailableCaseLimitation)
        self.assertEqual(len(required), 8)
        for value in self.non_available_inputs():
            result = self.project(value)
            with self.subTest(kind=result.analysis_kind):
                self.assertIs(
                    result.authority,
                    explicit_case.StageBNonAvailableCaseAuthority.
                    CAPABILITY_STATUS_EXPLANATION_ONLY,
                )
                self.assertEqual(set(result.limitations), required)

    def test_case_is_immutable_and_does_not_mutate_upstream(self):
        value = self.non_available_inputs()[0]
        before = value
        result = self.project(value)
        with self.assertRaises(FrozenInstanceError):
            result.capability_status = (
                explicit_case.StageBCapabilityStatus.UNSUPPORTED)
        self.assertEqual(value, before)

    def test_static_isolation_from_excluded_architectures(self):
        source = Path(explicit_case.__file__).read_text()
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
        imported_aliases = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            for alias in node.names
        }
        import_text = " ".join(imports | imported_aliases).casefold()
        self.assertIn("cash_like_current_carry", import_text)
        self.assertIn("expected_return_pr5e_adapter", import_text)
        self.assertIn("vfv_forward_expected_return", import_text)
        self.assertIn("company_vfv_expected_return_comparator", import_text)
        for prohibited in (
                "analysis_capabilities", "bounded_confidence_projection",
                "executable_entry_evidence", "confidence_range_engine",
                "recommendation", "sizing", "broker"):
            self.assertNotIn(prohibited, import_text)
        public_fields = " ".join(
            field.name for field in fields(
                explicit_case.StageBNonAvailableCase)).casefold()
        for prohibited in (
                "confidence", "recommendation", "allocation", "sizing",
                "broker", "execution", "b1", "b2"):
            self.assertNotIn(prohibited, public_fields)

    def test_module_has_no_network_filesystem_acquisition_or_runtime_clock(self):
        source = Path(explicit_case.__file__).read_text()
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
        self.assertTrue({
            "requests", "urllib", "httpx", "socket", "pathlib", "os",
            "subprocess", "datetime", "time",
        }.isdisjoint(imports))
        calls = {
            node.func.attr if isinstance(node.func, ast.Attribute)
            else node.func.id if isinstance(node.func, ast.Name) else ""
            for node in ast.walk(tree) if isinstance(node, ast.Call)
        }
        self.assertFalse({
            "open", "read_text", "read_bytes", "getenv", "now", "today",
            "utcnow", "urlopen", "__import__", "import_module",
        } & calls)


if __name__ == "__main__":
    unittest.main()
