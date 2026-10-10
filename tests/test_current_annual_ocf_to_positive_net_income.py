"""Adversarial tests for the bounded annual OCF/net-income diagnostic."""
import ast
import builtins
from collections import UserDict
from dataclasses import FrozenInstanceError, dataclass, fields, replace
from decimal import Decimal, localcontext
from enum import StrEnum
import json
from pathlib import Path
import socket
import tempfile
import time
import unittest
from unittest.mock import patch

from economic_facts import (
    sec_current_annual_operating_cash_flow_net_income as upstream,
)
from economic_facts import sec_operating_cash_flow_net_income as extraction
from economic_facts import sec_ordinary_compounder_profile as profile_module
from economic_facts.sec_archive import ArchiveError, SecArchive
from src import current_annual_ocf_to_positive_net_income as diagnostic
from tests import (
    test_sec_current_eps_comparability_qualification as comparability_tests,
)
from tests.sec_current_security_eps_qualification_fixtures import source_rows
from tests.sec_current_registered_listing_bridge_fixtures import sec_snapshot
from tests.sec_filing_fixtures import raw
from tests.sec_operating_cash_flow_net_income_fixtures import (
    LATEST_ACCESSION,
    NET_INCOME_VALUE,
    OPERATING_CASH_FLOW_VALUE,
    SECOND_ACCESSION,
    capture_profile,
    coherent_pair_payload,
    companyfacts_payload,
    conflicting_operating_cash_flow_payload,
    financial_row,
    missing_operating_cash_flow_payload,
    missing_net_income_payload,
    conflicting_net_income_payload,
    no_common_accession_payload,
)
from tests.sec_property4_temporal_boundary_fixtures import (
    BOUNDARY_T1,
    BOUNDARY_T2,
    current_request,
)
from tests.sec_property4_temporal_fixtures import CIK
from tests.sec_submissions_fixtures import root as submissions_root


class CurrentAnnualOCFToPositiveNetIncomeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = comparability_tests.SecCurrentEPSComparabilityTests(
            methodName="runTest"
        )
        cls.fixture.setUp()
        cls.receipt, available_profile = capture_profile(cls.fixture)
        _, unavailable_profile = capture_profile(
            cls.fixture, sic=None, description=None
        )
        _, unsupported_profile = capture_profile(
            cls.fixture,
            sic=6021,
            description="National Commercial Banks",
        )
        source_conflict_profile = cls.factory_source_conflict_profile()
        cls.available_profile = available_profile
        cls.available = cls.qualify(available_profile)
        cls.unavailable = cls.qualify(unavailable_profile)
        cls.unsupported = cls.qualify(unsupported_profile)
        cls.source_conflict = cls.qualify(source_conflict_profile)

    @classmethod
    def tearDownClass(cls):
        cls.fixture.doCleanups()

    @classmethod
    def qualify(cls, profile, archive=None):
        return upstream.qualify_sec_current_annual_operating_cash_flow_net_income(
            cls.fixture.current_archive if archive is None else archive,
            profile,
        )

    @classmethod
    def factory_source_conflict_profile(cls):
        receipt = cls.fixture.current_archive._capture_live(
            raw(coherent_pair_payload()),
            cik=CIK,
            captured_at=BOUNDARY_T1,
        )
        current = current_request(receipt)
        parent = cls.fixture.submissions_archive._capture_live(
            submissions_root(
                source_rows(),
                cik=CIK,
                sic=3571,
                sicDescription="Electronic Computers",
            ),
            cik=CIK,
            captured_at="2026-02-25T12:00:00Z",
        )
        request = cls.fixture.build_request(parent=parent, current=current)
        comparability = cls.fixture.qualify_request(request)
        profile_request = profile_module.SecOrdinaryCompounderProfileRequest(
            request,
            "0" * 64,
            comparability.evidence_id,
        )
        return profile_module.qualify_sec_ordinary_compounder_profile(
            cls.fixture.current_archive,
            cls.fixture.submissions_archive,
            cls.fixture.filing_archive,
            cls.fixture.sec_archive,
            cls.fixture.nasdaq_archive,
            profile_request,
        )

    @classmethod
    def qualification_for_payload(cls, payload):
        _, profile = capture_profile(cls.fixture, payload)
        return cls.qualify(profile)

    def analyze(self, value=None):
        return diagnostic.analyze_current_annual_ocf_to_positive_net_income(
            self.available if value is None else value
        )

    def with_values(self, operating_cash_flow, net_income):
        return replace(
            self.available,
            operating_cash_flow=Decimal(operating_cash_flow),
            net_income=Decimal(net_income),
        )

    def test_exact_runtime_input_type_only(self):
        class Subclass(
            upstream.CurrentAnnualOperatingCashFlowNetIncomeQualification
        ):
            pass

        subclass = Subclass(*(
            getattr(self.available, field.name)
            for field in fields(self.available)
        ))

        @dataclass(frozen=True)
        class ForeignQualification:
            status: object

        for value in (
            {},
            UserDict(),
            subclass,
            ForeignQualification(self.available.status),
            self.available_profile,
            object(),
        ):
            with self.subTest(value_type=type(value)), self.assertRaises(
                diagnostic.CurrentAnnualOCFToPositiveNetIncomeError
            ):
                self.analyze(value)

    def test_positive_net_income_cases_are_exact_signed_ratios(self):
        cases = (
            ("100", "80", (5, 4)),
            ("80", "100", (4, 5)),
            ("0", "100", (0, 1)),
            ("-20", "100", (-1, 5)),
            ("100", "0.0001", (1000000, 1)),
        )
        for operating_cash_flow, net_income, expected in cases:
            with self.subTest(values=(operating_cash_flow, net_income)):
                result = self.analyze(
                    self.with_values(operating_cash_flow, net_income)
                )
                self.assertIs(
                    result.status,
                    diagnostic.CurrentAnnualOCFToPositiveNetIncomeStatus.AVAILABLE,
                )
                self.assertEqual(result.reasons, ())
                ratio = result.operating_cash_flow_to_net_income_ratio
                self.assertEqual((ratio.numerator, ratio.denominator), expected)

    def test_non_positive_net_income_is_not_applicable(self):
        cases = (
            (
                "100",
                "0",
                diagnostic.CurrentAnnualOCFToPositiveNetIncomeReason.
                NET_INCOME_ZERO_DENOMINATOR,
            ),
            (
                "100",
                "-20",
                diagnostic.CurrentAnnualOCFToPositiveNetIncomeReason.
                NET_INCOME_NEGATIVE_NOT_POSITIVE_EARNINGS,
            ),
            (
                "-100",
                "-20",
                diagnostic.CurrentAnnualOCFToPositiveNetIncomeReason.
                NET_INCOME_NEGATIVE_NOT_POSITIVE_EARNINGS,
            ),
            (
                "0",
                "0",
                diagnostic.CurrentAnnualOCFToPositiveNetIncomeReason.
                NET_INCOME_ZERO_DENOMINATOR,
            ),
        )
        for operating_cash_flow, net_income, reason in cases:
            with self.subTest(values=(operating_cash_flow, net_income)):
                result = self.analyze(
                    self.with_values(operating_cash_flow, net_income)
                )
                self.assertIs(
                    result.status,
                    diagnostic.CurrentAnnualOCFToPositiveNetIncomeStatus.
                    NOT_APPLICABLE,
                )
                self.assertEqual(result.reasons, (reason,))
                self.assertIsNone(
                    result.operating_cash_flow_to_net_income_ratio
                )

    def test_ratio_is_immutable_reduced_and_normalizes_sign_and_zero(self):
        ratio = diagnostic.OperatingCashFlowToNetIncomeRatio(20, -100)
        self.assertEqual(ratio, diagnostic.OperatingCashFlowToNetIncomeRatio(-1, 5))
        self.assertEqual(
            diagnostic.OperatingCashFlowToNetIncomeRatio(0, -100),
            diagnostic.OperatingCashFlowToNetIncomeRatio(0, 1),
        )
        for numerator, denominator in ((True, 1), (1, False), (1.0, 2), (1, 0)):
            with self.subTest(values=(numerator, denominator)), self.assertRaises(
                diagnostic.CurrentAnnualOCFToPositiveNetIncomeError
            ):
                diagnostic.OperatingCashFlowToNetIncomeRatio(
                    numerator, denominator
                )
        with self.assertRaises(FrozenInstanceError):
            ratio.numerator = 3

    def test_equivalent_decimal_forms_have_identical_ratio_semantics(self):
        results = tuple(
            self.analyze(self.with_values(operating_cash_flow, net_income))
            for operating_cash_flow, net_income in (
                ("100", "80"),
                ("100.0", "80.00"),
                ("1E+2", "8E+1"),
            )
        )
        self.assertEqual(
            {result.operating_cash_flow_to_net_income_ratio for result in results},
            {diagnostic.OperatingCashFlowToNetIncomeRatio(5, 4)},
        )
        self.assertEqual({result.semantic_id for result in results}, {
            results[0].semantic_id
        })

    def test_decimal_context_and_float_are_irrelevant(self):
        with localcontext() as context, patch.object(
            builtins, "float", side_effect=AssertionError("float forbidden")
        ):
            context.prec = 1
            result = self.analyze(self.with_values("1", "3"))
        self.assertEqual(
            result.operating_cash_flow_to_net_income_ratio,
            diagnostic.OperatingCashFlowToNetIncomeRatio(1, 3),
        )

    def test_capability_states_map_exactly_without_partial_ratio(self):
        cases = (
            (
                self.unavailable,
                diagnostic.CurrentAnnualOCFToPositiveNetIncomeStatus.UNAVAILABLE,
                diagnostic.CurrentAnnualOCFToPositiveNetIncomeReason.
                UPSTREAM_EVIDENCE_UNAVAILABLE,
            ),
            (
                self.unsupported,
                diagnostic.CurrentAnnualOCFToPositiveNetIncomeStatus.UNSUPPORTED,
                diagnostic.CurrentAnnualOCFToPositiveNetIncomeReason.
                UPSTREAM_EVIDENCE_UNSUPPORTED,
            ),
            (
                self.source_conflict,
                diagnostic.CurrentAnnualOCFToPositiveNetIncomeStatus.
                SOURCE_CONFLICT,
                diagnostic.CurrentAnnualOCFToPositiveNetIncomeReason.
                UPSTREAM_SOURCE_CONFLICT,
            ),
        )
        for value, expected_status, expected_reason in cases:
            with self.subTest(status=value.status):
                result = self.analyze(value)
                self.assertIs(result.status, expected_status)
                self.assertEqual(result.reasons, (expected_reason,))
                self.assertIs(result.upstream_status, value.status)
                self.assertIs(result.upstream_reasons, value.reasons)
                self.assertIsNone(
                    result.operating_cash_flow_to_net_income_ratio
                )

    def test_all_factory_reachable_preliminary_unavailable_families_are_accepted(
        self,
    ):
        reason = upstream.CurrentAnnualOperatingCashFlowNetIncomeReason
        operating_paths = {
            None: None,
            "missing": reason.OPERATING_CASH_FLOW_UNAVAILABLE,
            "unit": reason.EXACT_USD_UNIT_UNAVAILABLE,
            "finite": reason.FINITE_OPERATING_CASH_FLOW_VALUE_UNAVAILABLE,
            "period": reason.EXACT_ANNUAL_PERIOD_PRESENTATION_UNAVAILABLE,
        }
        income_paths = {
            None: None,
            "missing": reason.NET_INCOME_UNAVAILABLE,
            "unit": reason.EXACT_USD_UNIT_UNAVAILABLE,
            "finite": reason.FINITE_NET_INCOME_VALUE_UNAVAILABLE,
            "period": reason.EXACT_ANNUAL_PERIOD_PRESENTATION_UNAVAILABLE,
        }

        def payload_for(operating_path, income_path):
            changes = {}
            if operating_path == "missing":
                changes["include_operating_cash_flow"] = False
            elif operating_path == "unit":
                changes["operating_cash_flow_unit"] = "shares"
            elif operating_path == "finite":
                changes["operating_cash_flow_rows"] = [financial_row("NaN")]
            elif operating_path == "period":
                changes["operating_cash_flow_rows"] = [financial_row(
                    OPERATING_CASH_FLOW_VALUE,
                    start="2023-01-01",
                    end="2023-12-31",
                )]
            if income_path == "missing":
                changes["include_net_income"] = False
            elif income_path == "unit":
                changes["net_income_unit"] = "shares"
            elif income_path == "finite":
                changes["net_income_rows"] = [financial_row("NaN")]
            elif income_path == "period":
                changes["net_income_rows"] = [financial_row(
                    NET_INCOME_VALUE,
                    start="2023-01-01",
                    end="2023-12-31",
                )]
            return companyfacts_payload(**changes)

        for operating_path, operating_reason in operating_paths.items():
            for income_path, income_reason in income_paths.items():
                if operating_path is None and income_path is None:
                    continue
                with self.subTest(
                    operating_path=operating_path,
                    income_path=income_path,
                ):
                    qualification = self.qualification_for_payload(
                        payload_for(operating_path, income_path)
                    )
                    expected = tuple(sorted(
                        {
                            item
                            for item in (operating_reason, income_reason)
                            if item is not None
                        },
                        key=lambda item: item.value,
                    ))
                    self.assertEqual(qualification.reasons, expected)
                    result = self.analyze(qualification)
                    self.assertIs(
                        result.status,
                        diagnostic.CurrentAnnualOCFToPositiveNetIncomeStatus.
                        UNAVAILABLE,
                    )
                    self.assertIs(result.upstream_reasons, qualification.reasons)

    def test_factory_reachable_late_unavailable_and_conflict_families_are_accepted(
        self,
    ):
        second_operating = financial_row(
            OPERATING_CASH_FLOW_VALUE + 1,
            accession=SECOND_ACCESSION,
            filed="2025-02-02",
        )
        second_income = financial_row(
            NET_INCOME_VALUE + 1,
            accession=SECOND_ACCESSION,
            filed="2025-02-02",
        )
        both_competing = companyfacts_payload(
            operating_cash_flow_rows=[
                financial_row(OPERATING_CASH_FLOW_VALUE),
                second_operating,
            ],
            net_income_rows=[
                financial_row(NET_INCOME_VALUE),
                second_income,
            ],
        )
        metadata_conflict = companyfacts_payload(
            operating_cash_flow_rows=[financial_row(
                OPERATING_CASH_FLOW_VALUE
            )],
            net_income_rows=[financial_row(
                NET_INCOME_VALUE,
                filed="2025-02-02",
            )],
        )
        cases = (
            no_common_accession_payload(),
            metadata_conflict,
            conflicting_operating_cash_flow_payload(),
            conflicting_net_income_payload(),
            both_competing,
        )
        for payload in cases:
            qualification = self.qualification_for_payload(payload)
            with self.subTest(reasons=qualification.reasons):
                result = self.analyze(qualification)
                expected = (
                    diagnostic.CurrentAnnualOCFToPositiveNetIncomeStatus.
                    UNAVAILABLE
                    if qualification.status is
                    upstream.CurrentAnnualOperatingCashFlowNetIncomeStatus.
                    EVIDENCE_UNAVAILABLE
                    else diagnostic.CurrentAnnualOCFToPositiveNetIncomeStatus.
                    SOURCE_CONFLICT
                )
                self.assertIs(result.status, expected)
                self.assertIs(result.upstream_reasons, qualification.reasons)

    def test_factory_reachable_route_replay_and_source_cik_conflicts_are_accepted(
        self,
    ):
        comparability = self.available_profile.upstream_comparability
        security = comparability.upstream_security_eps
        bridge = security.upstream_registered_listing_bridge
        temporal = bridge.temporal_boundary
        current = temporal.current_evidence
        incoherent_request = replace(current.request, cik="0000000001")
        incoherent_current = replace(current, request=incoherent_request)
        incoherent_temporal = replace(
            temporal, current_evidence=incoherent_current
        )
        incoherent_bridge = replace(
            bridge, temporal_boundary=incoherent_temporal
        )
        incoherent_security = replace(
            security,
            upstream_registered_listing_bridge=incoherent_bridge,
        )
        route_conflict = self.qualify(replace(
            self.available_profile,
            upstream_comparability=replace(
                comparability,
                upstream_security_eps=incoherent_security,
            ),
        ))

        with tempfile.TemporaryDirectory() as temporary:
            foreign_archive = SecArchive(
                Path(temporary).resolve() / "foreign"
            )
            replay_conflict = self.qualify(
                self.available_profile, archive=foreign_archive
            )

        extracted = extraction.OperatingCashFlowNetIncomeExtraction(
            extraction.EXTRACTION_VERSION,
            "0000000001",
            self.receipt.receipt_id,
            self.receipt.content_sha256,
            self.receipt.captured_at,
            self.receipt.source_locator,
            (),
            (),
        )
        with patch.object(
            upstream,
            "extract_operating_cash_flow_net_income",
            return_value=extracted,
        ):
            source_cik_conflict = self.qualify(self.available_profile)

        for qualification in (
            route_conflict,
            replay_conflict,
            source_cik_conflict,
        ):
            with self.subTest(reasons=qualification.reasons):
                self.assertIs(
                    self.analyze(qualification).status,
                    diagnostic.CurrentAnnualOCFToPositiveNetIncomeStatus.
                    SOURCE_CONFLICT,
                )

    def test_factory_reachable_mapped_profile_families_are_accepted(self):
        cases = (self.unavailable, self.unsupported, self.source_conflict)
        for qualification in cases:
            with self.subTest(status=qualification.status):
                self.assertIsNotNone(self.analyze(qualification))

        before_route_fixture = (
            comparability_tests.SecCurrentEPSComparabilityTests(
                methodName="runTest"
            )
        )
        before_route_fixture.setUp()
        self.addCleanup(before_route_fixture.doCleanups)
        with patch.object(
            comparability_tests,
            "sec_snapshot",
            return_value=sec_snapshot(cik=124),
        ):
            _, before_route_profile = capture_profile(before_route_fixture)
        before_route = (
            upstream.qualify_sec_current_annual_operating_cash_flow_net_income(
                before_route_fixture.current_archive,
                before_route_profile,
            )
        )
        self.assertIs(
            before_route.status,
            upstream.CurrentAnnualOperatingCashFlowNetIncomeStatus.
            EVIDENCE_UNAVAILABLE,
        )
        self.assertIsNone(before_route.route_local_issuer_key)
        self.assertIsNone(before_route.route_local_security_key)
        self.assertIsNotNone(self.analyze(before_route))

    def test_factory_reachable_out_of_range_sic_is_accepted(self):
        _, profile = capture_profile(
            self.fixture,
            sic=10000,
            description="Out of Range Industry",
        )
        qualification = self.qualify(profile)
        result = self.analyze(qualification)
        self.assertIs(
            result.status,
            diagnostic.CurrentAnnualOCFToPositiveNetIncomeStatus.UNAVAILABLE,
        )
        self.assertEqual(
            result.reasons,
            (
                diagnostic.CurrentAnnualOCFToPositiveNetIncomeReason.
                UPSTREAM_EVIDENCE_UNAVAILABLE,
            ),
        )

    def test_established_values_must_be_exact_finite_decimals(self):
        malformed = (
            (None, Decimal("1")),
            (0, Decimal("1")),
            (0.0, Decimal("1")),
            (Decimal("NaN"), Decimal("1")),
            (Decimal("Infinity"), Decimal("1")),
            (Decimal("1"), None),
            (Decimal("1"), 1),
            (Decimal("1"), 1.0),
            (Decimal("1"), Decimal("NaN")),
            (Decimal("1"), Decimal("-Infinity")),
        )
        for operating_cash_flow, net_income in malformed:
            with self.subTest(values=(operating_cash_flow, net_income)), \
                    self.assertRaises(
                        diagnostic.CurrentAnnualOCFToPositiveNetIncomeError
                    ):
                self.analyze(replace(
                    self.available,
                    operating_cash_flow=operating_cash_flow,
                    net_income=net_income,
                ))

    def test_upstream_contract_authority_and_limitations_are_closed(self):
        cases = (
            replace(self.available, contract_version="wrong"),
            replace(self.available, qualifier_version="wrong"),
            replace(self.available, evidence_kind="wrong"),
            replace(self.available, accounting_namespace="ifrs-full"),
            replace(self.available, accounting_basis="IFRS"),
            replace(self.available, operating_cash_flow_concept="wrong"),
            replace(self.available, net_income_concept="ProfitLoss"),
            replace(self.available, unit="shares"),
            replace(self.available, authority="wrong"),
            replace(self.available, limitations=self.available.limitations[:-1]),
        )
        for value in cases:
            with self.subTest(value=value), self.assertRaises(
                diagnostic.CurrentAnnualOCFToPositiveNetIncomeError
            ):
                self.analyze(value)

    def test_established_native_state_and_reasons_must_be_canonical(self):
        class ForeignReason(StrEnum):
            VALUE = "VALUE"

        cases = (
            replace(
                self.available,
                reasons=(
                    upstream.CurrentAnnualOperatingCashFlowNetIncomeReason.
                    SOURCE_CIK_CONFLICT,
                ),
            ),
            replace(self.available, reasons=(ForeignReason.VALUE,)),
            replace(self.available, upstream_profile_status="ESTABLISHED"),
            replace(
                self.available,
                upstream_profile_reasons=(
                    profile_module.ProfileReason.REPLAY_IDENTITY_MISMATCH,
                ),
            ),
            replace(self.available, status="FUTURE_STATE"),
        )
        for value in cases:
            with self.subTest(value=value), self.assertRaises(
                diagnostic.CurrentAnnualOCFToPositiveNetIncomeError
            ):
                self.analyze(value)

    def test_established_route_period_and_identity_context_must_be_valid(self):
        cases = (
            replace(self.available, route_local_issuer_key=None),
            replace(self.available, route_local_issuer_key="bad"),
            replace(self.available, route_local_security_key=None),
            replace(self.available, route_local_security_key="g" * 64),
            replace(self.available, source_cik=None),
            replace(self.available, source_cik="123"),
            replace(self.available, period_start=None),
            replace(self.available, period_start="2024-13-01"),
            replace(self.available, period_start="2025-01-01"),
            replace(self.available, upstream_profile_semantic_id="bad"),
            replace(self.available, upstream_comparability_semantic_id="bad"),
            replace(self.available, upstream_profile_evidence_id="bad"),
            replace(self.available, upstream_comparability_evidence_id="bad"),
        )
        for value in cases:
            with self.subTest(value=value), self.assertRaises(
                diagnostic.CurrentAnnualOCFToPositiveNetIncomeError
            ):
                self.analyze(value)

    def test_established_provenance_must_be_coherent_and_nonempty(self):
        filing = self.available.supporting_filings[0]
        cases = (
            replace(self.available, capture_receipt_id=None),
            replace(self.available, source_object_hash=None),
            replace(self.available, captured_at=None),
            replace(self.available, captured_at="not-a-timestamp"),
            replace(self.available, captured_at="2026-10-05T12:00:00"),
            replace(self.available, capture_source_locator=None),
            replace(self.available, capture_source_locator=" locator "),
            replace(
                self.available,
                selected_operating_cash_flow_observation_ids=(),
            ),
            replace(self.available, selected_net_income_observation_ids=()),
            replace(self.available, supporting_accessions=()),
            replace(self.available, supporting_filings=()),
            replace(
                self.available,
                supporting_filings=(replace(filing, accession="bad"),),
            ),
            replace(
                self.available,
                supporting_filings=(replace(
                    filing,
                    operating_cash_flow_observation_ids=("a" * 64,),
                    net_income_observation_ids=("a" * 64,),
                ),),
            ),
        )
        for value in cases:
            with self.subTest(value=value), self.assertRaises(
                diagnostic.CurrentAnnualOCFToPositiveNetIncomeError
            ):
                self.analyze(value)

    def test_established_supporting_provenance_is_exact_partition(self):
        filing = self.available.supporting_filings[0]
        extra_id = "0" * 64
        cases = (
            replace(
                self.available,
                supporting_filings=(replace(
                    filing, forms=("10-K", "10-K/A")
                ),),
            ),
            replace(
                self.available,
                supporting_filings=(replace(
                    filing, filed_dates=("2025-02-01", "2025-02-02")
                ),),
            ),
            replace(
                self.available,
                supporting_filings=(replace(
                    filing, fiscal_years=(2024, 2025)
                ),),
            ),
            replace(
                self.available,
                selected_operating_cash_flow_observation_ids=tuple(sorted(
                    self.available.selected_operating_cash_flow_observation_ids
                    + (extra_id,)
                )),
            ),
            replace(
                self.available,
                supporting_filings=(replace(
                    filing,
                    net_income_observation_ids=(
                        filing.operating_cash_flow_observation_ids[0],
                    ),
                ),),
            ),
        )
        for value in cases:
            with self.subTest(value=value), self.assertRaises(
                diagnostic.CurrentAnnualOCFToPositiveNetIncomeError
            ):
                self.analyze(value)

    def test_non_established_upstream_objects_cannot_carry_partial_evidence(self):
        reason = upstream.CurrentAnnualOperatingCashFlowNetIncomeReason
        status = upstream.CurrentAnnualOperatingCashFlowNetIncomeStatus
        profile_status = profile_module.OrdinaryCompounderProfileStatus
        cases = (
            replace(self.unavailable, operating_cash_flow=Decimal("1")),
            replace(self.unavailable, net_income=Decimal("1")),
            replace(
                self.unavailable,
                selected_net_income_observation_ids=("a" * 64,),
            ),
            replace(self.unavailable, reasons=()),
            replace(
                self.unavailable,
                status=status.EVIDENCE_UNSUPPORTED,
                reasons=(reason.UPSTREAM_PROFILE_UNAVAILABLE,),
            ),
            replace(
                self.unavailable,
                status=status.SOURCE_CONFLICT,
                reasons=(reason.UPSTREAM_SOURCE_CONFLICT,),
                upstream_profile_status=profile_status.PROFILE_UNAVAILABLE,
            ),
        )
        for value in cases:
            with self.subTest(value=value), self.assertRaises(
                diagnostic.CurrentAnnualOCFToPositiveNetIncomeError
            ):
                self.analyze(value)

    def test_impossible_non_established_reason_combinations_are_rejected(self):
        reason = upstream.CurrentAnnualOperatingCashFlowNetIncomeReason
        unavailable = self.qualification_for_payload(
            missing_net_income_payload()
        )
        conflict = self.qualification_for_payload(
            conflicting_net_income_payload()
        )
        cases = (
            replace(
                unavailable,
                reasons=tuple(sorted(
                    (
                        reason.NET_INCOME_UNAVAILABLE,
                        reason.NO_COMMON_ANNUAL_FILING_ACCESSION,
                    ),
                    key=lambda item: item.value,
                )),
            ),
            replace(
                unavailable,
                reasons=tuple(sorted(
                    (
                        reason.UPSTREAM_PROFILE_UNAVAILABLE,
                        reason.NET_INCOME_UNAVAILABLE,
                    ),
                    key=lambda item: item.value,
                )),
            ),
            replace(
                conflict,
                reasons=tuple(sorted(
                    (
                        reason.CAPTURE_REPLAY_CONFLICT,
                        reason.SOURCE_CIK_CONFLICT,
                    ),
                    key=lambda item: item.value,
                )),
            ),
            replace(
                conflict,
                reasons=tuple(sorted(
                    (
                        reason.COMMON_FILING_METADATA_CONFLICT,
                        reason.COMPETING_NET_INCOME_VALUES,
                    ),
                    key=lambda item: item.value,
                )),
            ),
        )
        for value in cases:
            with self.subTest(reasons=value.reasons), self.assertRaises(
                diagnostic.CurrentAnnualOCFToPositiveNetIncomeError
            ):
                self.analyze(value)

    def test_non_established_state_specific_context_is_enforced(self):
        local_unavailable = self.qualification_for_payload(
            missing_operating_cash_flow_payload()
        )
        local_conflict = self.qualification_for_payload(
            conflicting_operating_cash_flow_payload()
        )
        cases = (
            replace(
                local_unavailable,
                route_local_issuer_key=None,
                route_local_security_key=None,
            ),
            replace(
                local_unavailable,
                period_start=None,
                period_end=None,
            ),
            replace(
                local_unavailable,
                capture_receipt_id=None,
                source_object_hash=None,
                captured_at=None,
                capture_source_locator=None,
            ),
            replace(
                local_conflict,
                route_local_issuer_key=None,
                route_local_security_key=None,
            ),
            replace(
                local_conflict,
                period_start=None,
                period_end=None,
            ),
            replace(
                local_conflict,
                capture_receipt_id=None,
                source_object_hash=None,
                captured_at=None,
                capture_source_locator=None,
            ),
        )
        for value in cases:
            with self.subTest(reasons=value.reasons), self.assertRaises(
                diagnostic.CurrentAnnualOCFToPositiveNetIncomeError
            ):
                self.analyze(value)

    def test_partial_receipt_derived_provenance_is_always_rejected(self):
        cases = (
            replace(self.unavailable, capture_receipt_id=None),
            replace(self.unavailable, source_object_hash=None),
            replace(self.unavailable, captured_at=None),
            replace(self.unavailable, capture_source_locator=None),
        )
        for value in cases:
            with self.subTest(value=value), self.assertRaises(
                diagnostic.CurrentAnnualOCFToPositiveNetIncomeError
            ):
                self.analyze(value)

    def test_noncanonical_but_parseable_dates_and_timestamps_are_rejected(self):
        filing = self.available.supporting_filings[0]
        cases = (
            replace(
                self.available,
                captured_at="2025-03-01T12:00:00+00:00",
            ),
            replace(
                self.available,
                captured_at="2025-03-01T12:00:00.1Z",
            ),
            replace(self.available, period_start="20240101"),
            replace(
                self.available,
                supporting_filings=(replace(
                    filing,
                    filed_dates=("20250201",),
                ),),
            ),
        )
        for value in cases:
            with self.subTest(value=value), self.assertRaises(
                diagnostic.CurrentAnnualOCFToPositiveNetIncomeError
            ):
                self.analyze(value)

    def test_public_result_surface_is_exact_and_omits_raw_facts(self):
        result = self.analyze()
        expected_fields = {
            "contract_version",
            "methodology_version",
            "analysis_kind",
            "status",
            "reasons",
            "upstream_status",
            "upstream_reasons",
            "route_local_issuer_key",
            "route_local_security_key",
            "source_cik",
            "period_start",
            "period_end",
            "upstream_qualification_semantic_id",
            "upstream_qualification_evidence_id",
            "operating_cash_flow_to_net_income_ratio",
            "authority",
            "limitations",
        }
        self.assertEqual(
            {field.name for field in fields(type(result))}, expected_fields
        )
        self.assertFalse(hasattr(result, "operating_cash_flow"))
        self.assertFalse(hasattr(result, "net_income"))
        for forbidden in (
            "percentage",
            "score",
            "label",
            "grade",
            "threshold",
            "rank",
            "confidence",
            "recommendation",
        ):
            self.assertFalse(hasattr(result, forbidden))
        payload = result.to_dict()["current_annual_ocf_to_positive_net_income"]
        self.assertNotIn("operating_cash_flow", payload)
        self.assertNotIn("net_income", payload)

    def test_genuine_factory_recapture_preserves_analytical_semantics_only(
        self,
    ):
        first = self.analyze()
        recapture_fixture = (
            comparability_tests.SecCurrentEPSComparabilityTests(
                methodName="runTest"
            )
        )
        recapture_fixture.setUp()
        self.addCleanup(recapture_fixture.doCleanups)
        _, recaptured_profile = capture_profile(
            recapture_fixture,
            reverse=True,
            captured_at=BOUNDARY_T1,
        )
        factory_recaptured_upstream = (
            upstream.qualify_sec_current_annual_operating_cash_flow_net_income(
                recapture_fixture.current_archive,
                recaptured_profile,
            )
        )
        self.assertEqual(
            self.available.operating_cash_flow,
            factory_recaptured_upstream.operating_cash_flow,
        )
        self.assertEqual(
            self.available.net_income,
            factory_recaptured_upstream.net_income,
        )
        self.assertEqual(
            self.available.period_start,
            factory_recaptured_upstream.period_start,
        )
        self.assertEqual(
            self.available.period_end,
            factory_recaptured_upstream.period_end,
        )
        self.assertEqual(
            self.available.route_local_issuer_key,
            factory_recaptured_upstream.route_local_issuer_key,
        )
        self.assertEqual(
            self.available.route_local_security_key,
            factory_recaptured_upstream.route_local_security_key,
        )
        self.assertNotEqual(
            self.available.capture_receipt_id,
            factory_recaptured_upstream.capture_receipt_id,
        )
        self.assertNotEqual(
            self.available.source_object_hash,
            factory_recaptured_upstream.source_object_hash,
        )
        # OCF contract v2 keeps economic semantics stable across native recapture.
        self.assertEqual(
            self.available.semantic_id,
            factory_recaptured_upstream.semantic_id,
        )
        self.assertNotEqual(
            self.available.evidence_id,
            factory_recaptured_upstream.evidence_id,
        )
        recaptured = self.analyze(factory_recaptured_upstream)
        self.assertEqual(
            first.upstream_qualification_semantic_id,
            self.available.semantic_id,
        )
        self.assertEqual(
            first.upstream_qualification_evidence_id,
            self.available.evidence_id,
        )
        self.assertEqual(
            recaptured.upstream_qualification_semantic_id,
            factory_recaptured_upstream.semantic_id,
        )
        self.assertEqual(
            recaptured.upstream_qualification_evidence_id,
            factory_recaptured_upstream.evidence_id,
        )
        self.assertEqual(
            first.upstream_qualification_semantic_id,
            recaptured.upstream_qualification_semantic_id,
        )
        self.assertEqual(first.semantic_id, recaptured.semantic_id)
        self.assertNotEqual(first.evidence_id, recaptured.evidence_id)

    def test_later_current_boundary_factory_recapture_preserves_semantics(
        self,
    ):
        first = self.analyze()
        later_fixture = (
            comparability_tests.SecCurrentEPSComparabilityTests(
                methodName="runTest"
            )
        )
        later_fixture.setUp()
        self.addCleanup(later_fixture.doCleanups)
        _, later_profile = capture_profile(
            later_fixture,
            captured_at=BOUNDARY_T2,
        )
        later_upstream = (
            upstream.qualify_sec_current_annual_operating_cash_flow_net_income(
                later_fixture.current_archive,
                later_profile,
            )
        )
        for field_name in (
            "source_cik",
            "period_start",
            "period_end",
            "accounting_namespace",
            "accounting_basis",
            "operating_cash_flow_concept",
            "net_income_concept",
            "unit",
            "operating_cash_flow",
            "net_income",
        ):
            with self.subTest(field_name=field_name):
                self.assertEqual(
                    getattr(self.available, field_name),
                    getattr(later_upstream, field_name),
                )
        self.assertNotEqual(
            self.available.route_local_issuer_key,
            later_upstream.route_local_issuer_key,
        )
        self.assertNotEqual(
            self.available.route_local_security_key,
            later_upstream.route_local_security_key,
        )
        self.assertNotEqual(
            self.available.capture_receipt_id,
            later_upstream.capture_receipt_id,
        )
        self.assertNotEqual(
            self.available.captured_at,
            later_upstream.captured_at,
        )
        # OCF contract v2 excludes the changed capture-bound route keys.
        self.assertEqual(
            self.available.semantic_id,
            later_upstream.semantic_id,
        )
        self.assertNotEqual(
            self.available.evidence_id,
            later_upstream.evidence_id,
        )

        later = self.analyze(later_upstream)
        self.assertEqual(
            first.route_local_issuer_key,
            self.available.route_local_issuer_key,
        )
        self.assertEqual(
            first.route_local_security_key,
            self.available.route_local_security_key,
        )
        self.assertEqual(
            later.route_local_issuer_key,
            later_upstream.route_local_issuer_key,
        )
        self.assertEqual(
            later.route_local_security_key,
            later_upstream.route_local_security_key,
        )
        self.assertEqual(
            later.upstream_qualification_semantic_id,
            later_upstream.semantic_id,
        )
        self.assertEqual(
            later.upstream_qualification_evidence_id,
            later_upstream.evidence_id,
        )
        self.assertEqual(first.semantic_id, later.semantic_id)
        self.assertNotEqual(first.evidence_id, later.evidence_id)

    def test_same_ratio_different_economics_changes_analytical_semantics(self):
        first = self.analyze(self.with_values("100", "80"))
        same_ratio_different_economics = self.analyze(
            self.with_values("200", "160")
        )
        self.assertEqual(
            first.operating_cash_flow_to_net_income_ratio,
            same_ratio_different_economics.
            operating_cash_flow_to_net_income_ratio,
        )
        self.assertNotEqual(
            first.upstream_qualification_semantic_id,
            same_ratio_different_economics.
            upstream_qualification_semantic_id,
        )
        self.assertNotEqual(
            first.semantic_id, same_ratio_different_economics.semantic_id
        )

    def test_analytical_semantics_bind_each_material_economic_context(self):
        first = self.analyze(self.with_values("100", "80"))
        cases = (
            self.with_values("101", "80"),
            self.with_values("100", "81"),
            replace(
                self.with_values("100", "80"),
                period_start="2023-01-01",
                period_end="2023-12-31",
            ),
            replace(
                self.with_values("100", "80"),
                source_cik="0000000001",
            ),
        )
        for qualification in cases:
            with self.subTest(qualification=qualification):
                self.assertNotEqual(
                    first.semantic_id,
                    self.analyze(qualification).semantic_id,
                )

    def test_route_presence_not_opaque_route_values_drives_semantics(self):
        present = self.analyze(self.unavailable)
        changed_keys = self.analyze(replace(
            self.unavailable,
            route_local_issuer_key="0" * 64,
            route_local_security_key="1" * 64,
        ))
        absent = self.analyze(replace(
            self.unavailable,
            route_local_issuer_key=None,
            route_local_security_key=None,
        ))
        self.assertEqual(present.semantic_id, changed_keys.semantic_id)
        self.assertNotEqual(present.semantic_id, absent.semantic_id)
        self.assertEqual(changed_keys.route_local_issuer_key, "0" * 64)
        self.assertEqual(changed_keys.route_local_security_key, "1" * 64)

    def test_not_applicable_semantics_bind_exact_economic_inputs(self):
        cases = (
            (("100", "0"), ("200", "0")),
            (("100", "-20"), ("100", "-40")),
        )
        for left_values, right_values in cases:
            with self.subTest(left=left_values, right=right_values):
                left = self.analyze(self.with_values(*left_values))
                right = self.analyze(self.with_values(*right_values))
                self.assertIs(
                    left.status,
                    diagnostic.CurrentAnnualOCFToPositiveNetIncomeStatus.
                    NOT_APPLICABLE,
                )
                self.assertIs(
                    right.status,
                    diagnostic.CurrentAnnualOCFToPositiveNetIncomeStatus.
                    NOT_APPLICABLE,
                )
                self.assertNotEqual(left.semantic_id, right.semantic_id)

    def test_result_serialization_and_immutability_are_deterministic(self):
        result = self.analyze()
        self.assertEqual(result.semantic_id, result.semantic_id)
        self.assertEqual(result.evidence_id, result.evidence_id)
        self.assertEqual(result.to_dict(), result.to_dict())
        json.dumps(result.to_dict(), sort_keys=True)
        with self.assertRaises(FrozenInstanceError):
            result.status = (
                diagnostic.CurrentAnnualOCFToPositiveNetIncomeStatus.UNAVAILABLE
            )
        with self.assertRaises(FrozenInstanceError):
            result.operating_cash_flow_to_net_income_ratio.numerator = 2

    def test_authority_reasons_and_limitations_are_closed(self):
        result = self.analyze()
        self.assertIs(
            result.analysis_kind,
            diagnostic.CurrentAnnualOCFToPositiveNetIncomeAnalysisKind.
            CURRENT_ANNUAL_OCF_TO_POSITIVE_NET_INCOME,
        )
        self.assertEqual(
            result.authority.value,
            "QUALITY_CURRENT_ANNUAL_OCF_NET_INCOME_RELATIONSHIP_"
            "DIAGNOSTIC_ONLY",
        )
        self.assertEqual(
            result.limitations,
            tuple(diagnostic.CurrentAnnualOCFToPositiveNetIncomeLimitation),
        )
        self.assertEqual(len(result.limitations), 19)
        self.assertEqual(
            set(diagnostic.CurrentAnnualOCFToPositiveNetIncomeReason),
            {
                diagnostic.CurrentAnnualOCFToPositiveNetIncomeReason.
                UPSTREAM_EVIDENCE_UNAVAILABLE,
                diagnostic.CurrentAnnualOCFToPositiveNetIncomeReason.
                UPSTREAM_EVIDENCE_UNSUPPORTED,
                diagnostic.CurrentAnnualOCFToPositiveNetIncomeReason.
                UPSTREAM_SOURCE_CONFLICT,
                diagnostic.CurrentAnnualOCFToPositiveNetIncomeReason.
                NET_INCOME_ZERO_DENOMINATOR,
                diagnostic.CurrentAnnualOCFToPositiveNetIncomeReason.
                NET_INCOME_NEGATIVE_NOT_POSITIVE_EARNINGS,
            },
        )

    def test_analysis_has_no_acquisition_network_or_clock_dependency(self):
        with patch.object(
            socket.socket, "connect", side_effect=AssertionError("network")
        ), patch.object(
            socket, "getaddrinfo", side_effect=AssertionError("network")
        ), patch.object(
            time, "time", side_effect=AssertionError("clock")
        ), patch.object(
            upstream,
            "qualify_sec_current_annual_operating_cash_flow_net_income",
            side_effect=AssertionError("requalification"),
        ):
            self.assertIs(
                self.analyze().status,
                diagnostic.CurrentAnnualOCFToPositiveNetIncomeStatus.AVAILABLE,
            )

    def test_static_imports_and_dependency_boundaries_are_closed(self):
        allowed = {
            "dataclasses",
            "datetime",
            "decimal",
            "enum",
            "math",
            "hashlib",
            "json",
            "re",
            "sys",
        }
        source = Path(diagnostic.__file__).read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                self.assertTrue(
                    all(alias.name in allowed for alias in node.names)
                )
            elif isinstance(node, ast.ImportFrom):
                self.assertIn(node.module, allowed | {"__future__"})
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                self.assertNotIn(
                    node.func.id,
                    {"eval", "exec", "__import__", "compile", "float"},
                )
        for token in (
            "requests",
            "urllib",
            "expected_return_engine",
            "durability",
            "confidence_engine",
            "portfolio",
            "quality_score",
            "FivePeriodEPSConsistencyResult",
            "CurrentAnnualEPSDenominatorDilutionResult",
        ):
            self.assertNotIn(token, source)

    def test_model_rules_and_protected_fingerprints_remain_pinned(self):
        checkout = Path(__file__).resolve().parents[1]
        self.assertIn(
            'MODEL_RULES_VERSION = "2026-08-23-allocation-room-integrity-v7"',
            (checkout / "src" / "model_version.py").read_text(),
        )
        self.assertIn(
            "f1e73b27b80e41d96ff5e0fe990b482bad71b7220db0b5bd6a2f470d72786166",
            (checkout / "tests" / "test_pit_adapter_equivalence.py").read_text(),
        )
        self.assertIn(
            "f8457910665391e39c234274cae4c029802c681211eebc7dba986a63000876f1",
            (checkout / "tests" / "test_pit_comparison.py").read_text(),
        )


if __name__ == "__main__":
    unittest.main()
