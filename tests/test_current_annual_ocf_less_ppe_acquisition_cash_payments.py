"""Adversarial tests for exact CURRENT annual OCF less PP&E cash payments."""
import ast
from collections import UserDict
from dataclasses import FrozenInstanceError, dataclass, fields, replace
from decimal import Decimal, localcontext
from pathlib import Path
import socket
import unittest
from unittest.mock import patch

from economic_facts import (
    sec_current_annual_operating_cash_flow_net_income as ocf_upstream,
)
from economic_facts import (
    sec_current_annual_ppe_acquisition_cash_payments as ppe_upstream,
)
from economic_facts import sec_ordinary_compounder_profile as profile_module
from src import current_annual_ocf_less_ppe_acquisition_cash_payments as diagnostic
from tests import (
    test_sec_current_eps_comparability_qualification as comparability_tests,
)
from tests import sec_operating_cash_flow_net_income_fixtures as ocf_fixtures
from tests import sec_ppe_acquisition_cash_payments_fixtures as ppe_fixtures
from tests.sec_current_security_eps_qualification_fixtures import source_rows
from tests.sec_filing_fixtures import raw
from tests.sec_property4_temporal_boundary_fixtures import (
    BOUNDARY_T1,
    BOUNDARY_T2,
    current_request,
)
from tests.sec_property4_temporal_fixtures import CIK
from tests.sec_submissions_fixtures import root as submissions_root


class CurrentAnnualOCFLessPPEAcquisitionCashPaymentsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = cls.new_fixture()
        _, ocf_profile = ocf_fixtures.capture_profile(cls.fixture)
        _, ppe_profile = ppe_fixtures.capture_profile(cls.fixture)
        cls.ocf_available = cls.qualify_ocf(cls.fixture, ocf_profile)
        cls.ppe_available = cls.qualify_ppe(cls.fixture, ppe_profile)

        _, unavailable_profile = ocf_fixtures.capture_profile(
            cls.fixture, sic=None, description=None
        )
        cls.ocf_unavailable = cls.qualify_ocf(
            cls.fixture, unavailable_profile
        )
        cls.ppe_unavailable = cls.qualify_ppe(
            cls.fixture, unavailable_profile
        )
        _, unsupported_profile = ocf_fixtures.capture_profile(
            cls.fixture, sic=6021, description="National Commercial Banks"
        )
        cls.ocf_unsupported = cls.qualify_ocf(
            cls.fixture, unsupported_profile
        )
        cls.ppe_unsupported = cls.qualify_ppe(
            cls.fixture, unsupported_profile
        )
        source_conflict_profile = cls.factory_source_conflict_profile(cls.fixture)
        cls.ocf_conflict = cls.qualify_ocf(
            cls.fixture, source_conflict_profile
        )
        cls.ppe_conflict = cls.qualify_ppe(
            cls.fixture, source_conflict_profile
        )

    @classmethod
    def tearDownClass(cls):
        cls.fixture.doCleanups()

    @staticmethod
    def new_fixture():
        fixture = comparability_tests.SecCurrentEPSComparabilityTests(
            methodName="runTest"
        )
        fixture.setUp()
        return fixture

    @staticmethod
    def qualify_ocf(fixture, profile):
        return (
            ocf_upstream.
            qualify_sec_current_annual_operating_cash_flow_net_income(
                fixture.current_archive, profile
            )
        )

    @staticmethod
    def qualify_ppe(fixture, profile):
        return (
            ppe_upstream.
            qualify_sec_current_annual_ppe_acquisition_cash_payments(
                fixture.current_archive, profile
            )
        )

    @classmethod
    def factory_source_conflict_profile(cls, fixture):
        receipt = fixture.current_archive._capture_live(
            raw(ocf_fixtures.coherent_pair_payload()),
            cik=CIK,
            captured_at=BOUNDARY_T1,
        )
        current = current_request(receipt)
        parent = fixture.submissions_archive._capture_live(
            submissions_root(
                source_rows(),
                cik=CIK,
                sic=3571,
                sicDescription="Electronic Computers",
            ),
            cik=CIK,
            captured_at="2026-02-25T12:00:00Z",
        )
        request = fixture.build_request(parent=parent, current=current)
        comparability = fixture.qualify_request(request)
        profile_request = profile_module.SecOrdinaryCompounderProfileRequest(
            request, "0" * 64, comparability.evidence_id
        )
        return profile_module.qualify_sec_ordinary_compounder_profile(
            fixture.current_archive,
            fixture.submissions_archive,
            fixture.filing_archive,
            fixture.sec_archive,
            fixture.nasdaq_archive,
            profile_request,
        )

    def analyze(self, ocf=None, ppe=None):
        return (
            diagnostic.
            analyze_current_annual_ocf_less_ppe_acquisition_cash_payments(
                self.ocf_available if ocf is None else ocf,
                self.ppe_available if ppe is None else ppe,
            )
        )

    def with_values(self, ocf, ppe, *, net_income="200"):
        return (
            replace(
                self.ocf_available,
                operating_cash_flow=Decimal(ocf),
                net_income=Decimal(net_income),
            ),
            replace(
                self.ppe_available,
                ppe_acquisition_cash_payments=Decimal(ppe),
            ),
        )

    def test_exact_two_input_runtime_types_only(self):
        class OCFSubclass(
            ocf_upstream.CurrentAnnualOperatingCashFlowNetIncomeQualification
        ):
            pass

        subclass = OCFSubclass(*(
            getattr(self.ocf_available, field.name)
            for field in fields(self.ocf_available)
        ))

        @dataclass(frozen=True)
        class Foreign:
            status: object

        invalid_pairs = (
            ({}, self.ppe_available),
            (UserDict(), self.ppe_available),
            (subclass, self.ppe_available),
            (Foreign(self.ocf_available.status), self.ppe_available),
            (self.ocf_available, {}),
            (self.ocf_available, UserDict()),
            (self.ocf_available, self.ocf_available),
        )
        for ocf, ppe in invalid_pairs:
            with self.subTest(types=(type(ocf), type(ppe))), self.assertRaises(
                diagnostic.CurrentAnnualOCFLessPPEAcquisitionCashPaymentsError
            ):
                self.analyze(ocf, ppe)

    def test_contract_versions_kinds_authorities_and_limitations_are_pinned(self):
        mutations = (
            ("contract_version", "wrong"),
            ("qualifier_version", "wrong"),
            ("evidence_kind", "wrong"),
            ("authority", "wrong"),
            ("limitations", ()),
        )
        for name, value in mutations:
            with self.subTest(input="ocf", field=name), self.assertRaises(
                diagnostic.CurrentAnnualOCFLessPPEAcquisitionCashPaymentsError
            ):
                self.analyze(replace(self.ocf_available, **{name: value}), None)
            with self.subTest(input="ppe", field=name), self.assertRaises(
                diagnostic.CurrentAnnualOCFLessPPEAcquisitionCashPaymentsError
            ):
                self.analyze(None, replace(self.ppe_available, **{name: value}))

    def test_closed_native_states_reasons_and_impossible_shapes_are_rejected(self):
        malformed = (
            replace(self.ocf_available, reasons=("unknown",)),
            replace(
                self.ocf_unavailable,
                reasons=(),
            ),
            replace(
                self.ocf_unavailable,
                operating_cash_flow=Decimal("1"),
            ),
            replace(
                self.ocf_available,
                selected_operating_cash_flow_observation_ids=(),
            ),
        )
        for value in malformed:
            with self.subTest(value=value), self.assertRaises(
                diagnostic.CurrentAnnualOCFLessPPEAcquisitionCashPaymentsError
            ):
                self.analyze(value, None)
        malformed_ppe = (
            replace(self.ppe_available, reasons=("unknown",)),
            replace(self.ppe_unavailable, reasons=()),
            replace(
                self.ppe_unavailable,
                ppe_acquisition_cash_payments=Decimal("1"),
            ),
            replace(self.ppe_available, selected_observation_ids=()),
        )
        for value in malformed_ppe:
            with self.subTest(value=value), self.assertRaises(
                diagnostic.CurrentAnnualOCFLessPPEAcquisitionCashPaymentsError
            ):
                self.analyze(None, value)

    def test_all_four_states_and_no_partial_numeric_output(self):
        cases = (
            (
                self.ocf_available,
                self.ppe_available,
                diagnostic.CurrentAnnualOCFLessPPEAcquisitionCashPaymentsStatus.
                AVAILABLE,
            ),
            (
                self.ocf_unavailable,
                self.ppe_available,
                diagnostic.CurrentAnnualOCFLessPPEAcquisitionCashPaymentsStatus.
                UNAVAILABLE,
            ),
            (
                self.ocf_available,
                self.ppe_unsupported,
                diagnostic.CurrentAnnualOCFLessPPEAcquisitionCashPaymentsStatus.
                UNSUPPORTED,
            ),
            (
                self.ocf_conflict,
                self.ppe_available,
                diagnostic.CurrentAnnualOCFLessPPEAcquisitionCashPaymentsStatus.
                SOURCE_CONFLICT,
            ),
        )
        for ocf, ppe, expected in cases:
            with self.subTest(expected=expected):
                result = self.analyze(ocf, ppe)
                self.assertIs(result.status, expected)
                numerics = (
                    result.operating_cash_flow,
                    result.ppe_acquisition_cash_payments,
                    result.ocf_less_ppe_acquisition_cash_payments,
                )
                if expected is diagnostic.CurrentAnnualOCFLessPPEAcquisitionCashPaymentsStatus.AVAILABLE:
                    self.assertTrue(all(value is not None for value in numerics))
                else:
                    self.assertEqual(numerics, (None, None, None))

    def test_each_input_failure_and_mixed_precedence_preserve_distinct_reasons(self):
        reason = diagnostic.CurrentAnnualOCFLessPPEAcquisitionCashPaymentsReason
        status = diagnostic.CurrentAnnualOCFLessPPEAcquisitionCashPaymentsStatus
        cases = (
            (self.ocf_unavailable, self.ppe_available, status.UNAVAILABLE,
             (reason.UPSTREAM_OCF_EVIDENCE_UNAVAILABLE,)),
            (self.ocf_available, self.ppe_unavailable, status.UNAVAILABLE,
             (reason.UPSTREAM_PPE_EVIDENCE_UNAVAILABLE,)),
            (self.ocf_unavailable, self.ppe_unavailable, status.UNAVAILABLE,
             tuple(sorted((reason.UPSTREAM_OCF_EVIDENCE_UNAVAILABLE,
                           reason.UPSTREAM_PPE_EVIDENCE_UNAVAILABLE),
                          key=lambda item: item.value))),
            (self.ocf_unsupported, self.ppe_unavailable, status.UNSUPPORTED,
             tuple(sorted((reason.UPSTREAM_OCF_EVIDENCE_UNSUPPORTED,
                           reason.UPSTREAM_PPE_EVIDENCE_UNAVAILABLE),
                          key=lambda item: item.value))),
            (self.ocf_unsupported, self.ppe_conflict, status.SOURCE_CONFLICT,
             tuple(sorted((reason.UPSTREAM_OCF_EVIDENCE_UNSUPPORTED,
                           reason.UPSTREAM_PPE_SOURCE_CONFLICT),
                          key=lambda item: item.value))),
        )
        for ocf, ppe, expected_status, expected_reasons in cases:
            with self.subTest(status=expected_status, reasons=expected_reasons):
                result = self.analyze(ocf, ppe)
                self.assertIs(result.status, expected_status)
                self.assertEqual(result.reasons, expected_reasons)
                self.assertIs(result.upstream_ocf_status, ocf.status)
                self.assertEqual(result.upstream_ocf_reasons, ocf.reasons)
                self.assertIs(result.upstream_ppe_status, ppe.status)
                self.assertEqual(result.upstream_ppe_reasons, ppe.reasons)

    def test_cross_foundation_issuer_period_and_accounting_semantics_are_exact(self):
        ppe_mutations = (
            ("source_cik", "0000000001"),
            ("period_start", "2023-01-01"),
            ("period_end", "2025-12-31"),
            ("accounting_namespace", "ifrs-full"),
            ("accounting_basis", "IFRS"),
            ("unit", "EUR"),
            ("concept", "OtherConcept"),
        )
        for name, value in ppe_mutations:
            with self.subTest(field=name), self.assertRaises(
                diagnostic.CurrentAnnualOCFLessPPEAcquisitionCashPaymentsError
            ):
                self.analyze(None, replace(self.ppe_available, **{name: value}))
        with self.assertRaises(
            diagnostic.CurrentAnnualOCFLessPPEAcquisitionCashPaymentsError
        ):
            self.analyze(
                replace(
                    self.ocf_available,
                    operating_cash_flow_concept="OtherConcept",
                ),
                None,
            )

    def test_common_accession_is_required(self):
        payload = ppe_fixtures.companyfacts_payload(rows=[
            ppe_fixtures.financial_row(
                ppe_fixtures.PPE_ACQUISITION_CASH_PAYMENTS_VALUE,
                accession=ppe_fixtures.SECOND_ACCESSION,
                filed="2025-02-02",
            )
        ])
        _, profile = ppe_fixtures.capture_profile(self.fixture, payload)
        result = self.analyze(None, self.qualify_ppe(self.fixture, profile))
        self.assertIs(
            result.status,
            diagnostic.CurrentAnnualOCFLessPPEAcquisitionCashPaymentsStatus.
            UNAVAILABLE,
        )
        self.assertEqual(result.reasons, (
            diagnostic.CurrentAnnualOCFLessPPEAcquisitionCashPaymentsReason.
            NO_COMMON_SUPPORTING_ANNUAL_FILING_ACCESSION,
        ))
        self.assertEqual(result.common_supporting_accessions, ())

    def test_common_accession_metadata_conflict_is_source_conflict(self):
        for metadata in (
            {"form": "10-K/A"},
            {"filed": "2025-02-02"},
            {"fy": 2025},
        ):
            with self.subTest(metadata=metadata):
                payload = ppe_fixtures.companyfacts_payload(rows=[
                    ppe_fixtures.financial_row(
                        ppe_fixtures.PPE_ACQUISITION_CASH_PAYMENTS_VALUE,
                        **metadata,
                    )
                ])
                _, profile = ppe_fixtures.capture_profile(self.fixture, payload)
                result = self.analyze(
                    None, self.qualify_ppe(self.fixture, profile)
                )
                self.assertIs(
                    result.status,
                    diagnostic.
                    CurrentAnnualOCFLessPPEAcquisitionCashPaymentsStatus.
                    SOURCE_CONFLICT,
                )
                self.assertEqual(result.reasons, (
                    diagnostic.
                    CurrentAnnualOCFLessPPEAcquisitionCashPaymentsReason.
                    COMMON_SUPPORTING_FILING_METADATA_CONFLICT,
                ))
                self.assertEqual(
                    result.common_supporting_accessions,
                    (ocf_fixtures.LATEST_ACCESSION,),
                )

    def test_exact_signed_subtraction_cases_and_canonical_zero(self):
        cases = (
            ("100", "30", Decimal("70")),
            ("100", "0", Decimal("100")),
            ("100", "-30", Decimal("130")),
            ("-100", "30", Decimal("-130")),
            ("0", "30", Decimal("-30")),
            ("30", "30", Decimal(0)),
        )
        for ocf, ppe, expected in cases:
            with self.subTest(ocf=ocf, ppe=ppe):
                result = self.analyze(*self.with_values(ocf, ppe))
                self.assertEqual(
                    result.ocf_less_ppe_acquisition_cash_payments, expected
                )
                if expected == 0:
                    self.assertEqual(
                        result.ocf_less_ppe_acquisition_cash_payments.as_tuple(),
                        Decimal(0).as_tuple(),
                    )

    def test_high_precision_subtraction_ignores_ambient_decimal_context(self):
        ocf = "12345678901234567890.123456789012345678901"
        ppe = "0.000000000000000000009"
        with localcontext() as context:
            context.prec = 3
            result = self.analyze(*self.with_values(ocf, ppe))
        self.assertEqual(
            result.ocf_less_ppe_acquisition_cash_payments,
            Decimal("12345678901234567890.123456789012345678892"),
        )

    def test_equivalent_decimal_forms_have_identical_semantics(self):
        results = tuple(
            self.analyze(*self.with_values(ocf, ppe))
            for ocf, ppe in (("100", "30"), ("100.0", "30.00"), ("1E2", "3E1"))
        )
        self.assertEqual({item.semantic_id for item in results}, {
            results[0].semantic_id
        })

    def test_economic_operand_changes_change_semantic_identity(self):
        baseline = self.analyze(*self.with_values("100", "30"))
        changed_ocf = self.analyze(*self.with_values("101", "30"))
        changed_ppe = self.analyze(*self.with_values("100", "31"))
        self.assertEqual(
            len({baseline.semantic_id, changed_ocf.semantic_id, changed_ppe.semantic_id}),
            3,
        )

    def test_net_income_only_change_does_not_change_semantic_identity(self):
        payload = ocf_fixtures.companyfacts_payload(net_income_rows=[
            ocf_fixtures.financial_row(999_000_000)
        ])
        _, profile = ocf_fixtures.capture_profile(
            self.fixture,
            payload,
            reverse=True,
            captured_at=BOUNDARY_T2,
        )
        changed_ocf = self.qualify_ocf(self.fixture, profile)
        self.assertEqual(
            self.ocf_available.operating_cash_flow,
            changed_ocf.operating_cash_flow,
        )
        self.assertNotEqual(self.ocf_available.net_income, changed_ocf.net_income)
        baseline = self.analyze()
        changed = self.analyze(changed_ocf, None)
        self.assertEqual(baseline.semantic_id, changed.semantic_id)
        self.assertNotEqual(baseline.evidence_id, changed.evidence_id)

    def test_authentic_independent_recapture_preserves_semantics_not_evidence(self):
        second_fixture = self.new_fixture()
        self.addCleanup(second_fixture.doCleanups)
        _, ocf_profile = ocf_fixtures.capture_profile(
            second_fixture, reverse=True, captured_at=BOUNDARY_T2
        )
        _, ppe_profile = ppe_fixtures.capture_profile(
            second_fixture, reverse=True, captured_at=BOUNDARY_T2
        )
        ocf = self.qualify_ocf(second_fixture, ocf_profile)
        ppe = self.qualify_ppe(second_fixture, ppe_profile)
        recaptured = self.analyze(ocf, ppe)
        baseline = self.analyze()
        self.assertNotEqual(
            self.ocf_available.upstream_profile_semantic_id,
            ocf.upstream_profile_semantic_id,
        )
        # OCF contract v2 preserves economic semantics under genuine recapture.
        self.assertEqual(self.ocf_available.semantic_id, ocf.semantic_id)
        self.assertNotEqual(self.ocf_available.evidence_id, ocf.evidence_id)
        self.assertNotEqual(
            self.ocf_available.capture_receipt_id, ocf.capture_receipt_id
        )
        self.assertNotEqual(ocf.capture_receipt_id, ppe.capture_receipt_id)
        self.assertEqual(baseline.semantic_id, recaptured.semantic_id)
        self.assertNotEqual(baseline.evidence_id, recaptured.evidence_id)
        self.assertEqual(
            baseline.ocf_less_ppe_acquisition_cash_payments,
            recaptured.ocf_less_ppe_acquisition_cash_payments,
        )

    def test_reordered_source_evidence_is_deterministic(self):
        second_fixture = self.new_fixture()
        self.addCleanup(second_fixture.doCleanups)
        _, ocf_profile = ocf_fixtures.capture_profile(
            second_fixture, reverse=True
        )
        _, ppe_profile = ppe_fixtures.capture_profile(
            second_fixture, reverse=True
        )
        reordered = self.analyze(
            self.qualify_ocf(second_fixture, ocf_profile),
            self.qualify_ppe(second_fixture, ppe_profile),
        )
        self.assertEqual(self.analyze().semantic_id, reordered.semantic_id)

    def test_result_is_immutable_deterministic_and_serializable(self):
        first = self.analyze()
        second = self.analyze()
        self.assertEqual(first, second)
        self.assertEqual(first.semantic_id, second.semantic_id)
        self.assertEqual(first.evidence_id, second.evidence_id)
        payload = first.to_dict()[
            "current_annual_ocf_less_ppe_acquisition_cash_payments"
        ]
        self.assertEqual(payload["semantic_id"], first.semantic_id)
        self.assertEqual(payload["evidence_id"], first.evidence_id)
        with self.assertRaises(FrozenInstanceError):
            first.status = "changed"

    def test_no_acquisition_network_or_unexpected_provider_dependency(self):
        source = Path(diagnostic.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        } | {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module is not None
        }
        self.assertFalse(any(
            name.startswith(("requests", "urllib", "httpx", "yfinance"))
            for name in imports
        ))
        with patch.object(
            socket,
            "create_connection",
            side_effect=AssertionError("network forbidden"),
        ):
            self.assertIs(
                self.analyze().status,
                diagnostic.CurrentAnnualOCFLessPPEAcquisitionCashPaymentsStatus.
                AVAILABLE,
            )

    def test_result_has_no_universal_fcf_owner_earnings_or_score_surface(self):
        field_names = {field.name for field in fields(
            diagnostic.CurrentAnnualOCFLessPPEAcquisitionCashPaymentsResult
        )}
        self.assertEqual(field_names, {
            "contract_version",
            "methodology_version",
            "analysis_kind",
            "status",
            "reasons",
            "upstream_ocf_status",
            "upstream_ocf_reasons",
            "upstream_ppe_status",
            "upstream_ppe_reasons",
            "source_cik",
            "period_start",
            "period_end",
            "accounting_namespace",
            "accounting_basis",
            "unit",
            "operating_cash_flow_concept",
            "ppe_acquisition_cash_payments_concept",
            "operating_cash_flow",
            "ppe_acquisition_cash_payments",
            "ocf_less_ppe_acquisition_cash_payments",
            "upstream_ocf_qualification_semantic_id",
            "upstream_ocf_qualification_evidence_id",
            "upstream_ppe_qualification_semantic_id",
            "upstream_ppe_qualification_evidence_id",
            "common_supporting_accessions",
            "authority",
            "limitations",
        })
        forbidden = {
            "free_cash_flow",
            "owner_earnings",
            "quality_score",
            "quality_grade",
            "net_income",
        }
        self.assertTrue(field_names.isdisjoint(forbidden))
        self.assertEqual(
            diagnostic.CONTRACT_VERSION,
            "2026-10-09-current-annual-ocf-less-ppe-acquisition-cash-payments-"
            "diagnostic-v1",
        )
        self.assertEqual(
            diagnostic.METHODOLOGY_VERSION,
            "2026-10-09-exact-base-ten-ocf-minus-ppe-cash-payments-v1",
        )

    def test_model_rules_and_protected_fingerprints_remain_pinned(self):
        checkout = Path(__file__).resolve().parents[1]
        self.assertIn(
            'MODEL_RULES_VERSION = "2026-08-23-allocation-room-integrity-v7"',
            (checkout / "src" / "model_version.py").read_text(),
        )
        self.assertIn(
            "f1e73b27b80e41d96ff5e0fe990b482bad71b7220db0b5bd6a2f470d72786166",
            (
                checkout / "tests" / "test_pit_adapter_equivalence.py"
            ).read_text(),
        )
        self.assertIn(
            "f8457910665391e39c234274cae4c029802c681211eebc7dba986a63000876f1",
            (checkout / "tests" / "test_pit_comparison.py").read_text(),
        )


if __name__ == "__main__":
    unittest.main()
