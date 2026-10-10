"""Fictional native-capture regressions for the bounded two-foundation ratio."""
import ast
from collections import UserDict
from copy import deepcopy
from dataclasses import FrozenInstanceError, fields, replace
from decimal import Decimal, localcontext
from fractions import Fraction
import json
from pathlib import Path
import socket
import time
import unittest
from unittest.mock import patch

from economic_facts import sec_current_annual_revenue_operating_income as income
from economic_facts import sec_current_annual_opening_closing_assets as assets
from economic_facts import sec_ordinary_compounder_profile as profiles
from src import current_annual_operating_income_to_positive_two_point_average_assets as diagnostic
from tests import test_sec_current_eps_comparability_qualification as comparability_tests
from tests.sec_revenue_operating_income_fixtures import (
    capture_profile, companyfacts_payload, financial_row, LATEST_ACCESSION, SECOND_ACCESSION,
)
from tests.test_sec_current_annual_opening_closing_assets import payload_for
from tests.sec_assets_liabilities_fixtures import financial_row as asset_row
from tests.sec_property4_temporal_boundary_fixtures import BOUNDARY_T1, BOUNDARY_T2

Status = diagnostic.CurrentAnnualOperatingIncomeToPositiveTwoPointAverageAssetsStatus
Reason = diagnostic.CurrentAnnualOperatingIncomeToPositiveTwoPointAverageAssetsReason
Error = diagnostic.CurrentAnnualOperatingIncomeToPositiveTwoPointAverageAssetsError
Ratio = diagnostic.OperatingIncomeToTwoPointAverageAssetsRatio
analyze = diagnostic.analyze_current_annual_operating_income_to_positive_two_point_average_assets


def exact_json(value):
    """Fixture encoder preserves finite Decimal tokens without float conversion."""
    if type(value) is Decimal:
        if not value.is_finite():
            raise ValueError("Finite fixture Decimal required")
        return str(value)
    if type(value) is dict:
        return "{" + ",".join(json.dumps(k) + ":" + exact_json(v) for k, v in value.items()) + "}"
    if type(value) is list:
        return "[" + ",".join(exact_json(v) for v in value) + "]"
    return json.dumps(value)


def combined_payload(*, i=20, opening=100, closing=300, revenue=250, **kwargs):
    result = payload_for(opening=opening, closing=closing)
    paired = companyfacts_payload(revenue_rows=[financial_row(revenue)],
                                  operating_income_rows=[financial_row(i)], **kwargs)
    result["facts"]["us-gaap"].update(paired["facts"]["us-gaap"])
    return result


class TwoPointAverageAssetsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = comparability_tests.SecCurrentEPSComparabilityTests(methodName="runTest")
        cls.fixture.setUp()
        cls.pairs = {}
        for state, kwargs in (
            ("established", {}),
            ("unavailable", {"sic": None, "description": None}),
            ("unsupported", {"sic": 6021, "description": "National Commercial Banks"}),
            ("conflict", {"expected_comparability_semantic_id": "0" * 64}),
        ):
            cls.pairs[state] = cls.make_pair(combined_payload(), **kwargs)
        cls.left, cls.right = cls.pairs["established"]

    @classmethod
    def tearDownClass(cls):
        cls.fixture.doCleanups()

    @classmethod
    def make_pair(cls, payload=None, **kwargs):
        payload = combined_payload() if payload is None else payload
        # All identity regressions use real native captures and upstream factories.
        with patch("tests.sec_revenue_operating_income_fixtures.raw",
                   side_effect=lambda value, **_: exact_json(value).encode("utf-8")):
            _, profile = capture_profile(cls.fixture, payload, **kwargs)
        archive = cls.fixture.current_archive
        return (income.qualify_sec_current_annual_revenue_operating_income(archive, profile),
                assets.qualify_sec_current_annual_opening_closing_assets(archive, profile))

    def test_exact_positive_ratio_and_public_context(self):
        result = analyze(self.left, self.right)
        self.assertEqual(result.status, Status.AVAILABLE)
        self.assertEqual(result.reasons, ())
        self.assertEqual(result.operating_income_to_two_point_average_assets_ratio, Ratio(1, 10))
        self.assertEqual((result.period_start, result.period_end, result.opening_balance_date,
                          result.closing_balance_date),
                         ("2024-01-01", "2024-12-31", "2023-12-31", "2024-12-31"))
        self.assertEqual(result.common_supporting_accessions, (LATEST_ACCESSION,))
        self.assertEqual(result.upstream_revenue_operating_income_qualification_semantic_id, self.left.semantic_id)
        self.assertEqual(result.upstream_opening_closing_assets_qualification_evidence_id, self.right.evidence_id)

    def test_closed_versions_statuses_reasons_authority_and_limitations(self):
        result = analyze(self.left, self.right)
        self.assertEqual(diagnostic.CONTRACT_VERSION, "2026-10-10-current-annual-operating-income-to-positive-two-point-average-assets-diagnostic-v1")
        self.assertEqual(diagnostic.METHODOLOGY_VERSION, "2026-10-10-exact-rational-operating-income-per-positive-two-point-average-assets-v1")
        self.assertEqual(result.analysis_kind.value, "CURRENT_ANNUAL_OPERATING_INCOME_TO_POSITIVE_TWO_POINT_AVERAGE_ASSETS")
        self.assertEqual(result.authority.value, "QUALITY_CURRENT_ANNUAL_OPERATING_INCOME_TO_POSITIVE_TWO_POINT_AVERAGE_ASSETS_DIAGNOSTIC_ONLY")
        self.assertEqual(len(Status), 5)
        self.assertEqual(len(Reason), 12)
        self.assertEqual(result.limitations, tuple(diagnostic.CurrentAnnualOperatingIncomeToPositiveTwoPointAverageAssetsLimitation))
        contract = Path("docs/contracts/v2/quality/CURRENT_ANNUAL_OPERATING_INCOME_TO_POSITIVE_TWO_POINT_AVERAGE_ASSETS_DIAGNOSTIC.md")
        # The isolated runner copies code/config/tests, not docs; contract QA runs separately.
        if contract.exists():
            text = contract.read_text()
            for item in (*Status, *Reason, *result.limitations):
                self.assertIn(item.value, text)

    def test_public_result_has_no_amount_or_average_fact(self):
        result = analyze(self.left, self.right)
        payload = next(iter(result.to_dict().values()))
        for forbidden in ("revenue", "operating_income", "opening_assets", "closing_assets",
                          "two_point_average_assets", "average_assets", "_analytical_fingerprint"):
            self.assertNotIn(forbidden, payload)
            self.assertNotIn(forbidden, {f.name for f in fields(result)})
        self.assertEqual(payload["operating_income_to_two_point_average_assets_ratio"], {"numerator": 1, "denominator": 10})
        json.dumps(result.to_dict(), allow_nan=False)

    def test_result_and_ratio_are_immutable(self):
        result = analyze(self.left, self.right)
        with self.assertRaises(FrozenInstanceError):
            result.status = Status.UNAVAILABLE
        with self.assertRaises(FrozenInstanceError):
            result.operating_income_to_two_point_average_assets_ratio.numerator = 9

    def test_reconstructed_result_without_private_fingerprints_fails(self):
        result = replace(analyze(self.left, self.right))
        with self.assertRaises(Error):
            _ = result.semantic_id
        with self.assertRaises(Error):
            _ = result.evidence_id

    def test_exact_native_input_types(self):
        for bad in (None, {}, UserDict(), self.left.to_dict(), self.right,
                    self.left.revenue, object()):
            with self.subTest(bad=type(bad)), self.assertRaises(Error):
                analyze(bad, self.right)
        for bad in (None, {}, UserDict(), self.right.to_dict(), self.left, object()):
            with self.subTest(bad=type(bad)), self.assertRaises(Error):
                analyze(self.left, bad)

    def test_subclasses_are_rejected(self):
        for original, other, first in ((self.left, self.right, True), (self.right, self.left, False)):
            subclass = type("Substitute", (type(original),), {})
            bad = subclass(**{f.name: getattr(original, f.name) for f in fields(original)})
            with self.assertRaises(Error):
                analyze(bad, other) if first else analyze(other, bad)

    def test_duck_types_and_detached_facts_rejected(self):
        from types import SimpleNamespace
        for q, first in ((self.left, True), (self.right, False)):
            bad = SimpleNamespace(**{f.name: getattr(q, f.name) for f in fields(q)})
            with self.assertRaises(Error):
                analyze(bad, self.right) if first else analyze(self.left, bad)
        with self.assertRaises(Error):
            analyze(self.left, self.right.selected_opening_observations[0])

    def test_exact_two_positional_arguments_only(self):
        with self.assertRaises(TypeError):
            analyze(revenue_operating_income=self.left, opening_closing_assets=self.right)
        for kwargs in ({"period_start": "2024-01-01"}, {"amount": 0}, {"accession": LATEST_ACCESSION}, {"qualified": True}):
            with self.assertRaises(TypeError):
                analyze(self.left, self.right, **kwargs)
        with self.assertRaises(TypeError):
            analyze(self.left)
        with self.assertRaises(TypeError):
            analyze(self.left, self.right, 3)

    def test_pinned_contract_mutations_rejected(self):
        for q, first in ((self.left, True), (self.right, False)):
            changes = {"contract_version": "future", "qualifier_version": "future", "evidence_kind": "OTHER",
                       "authority": "QUALITY_SCORE", "limitations": (), "accounting_namespace": "ifrs",
                       "accounting_basis": "IFRS", "unit": "EUR"}
            changes.update({"revenue_concept": "SalesRevenueNet", "operating_income_concept": "ProfitLoss"}
                           if first else {"concept": "Liabilities"})
            for field, value in changes.items():
                with self.subTest(first=first, field=field), self.assertRaises(Error):
                    bad = replace(q, **{field: value})
                    analyze(bad, self.right) if first else analyze(self.left, bad)

    def test_future_upstream_versions_cannot_silently_expand_diagnostic(self):
        for q, module, first in ((self.left, income, True), (self.right, assets, False)):
            for name, field in (("CONTRACT_VERSION", "contract_version"),
                                ("QUALIFIER_VERSION", "qualifier_version")):
                with patch.object(module, name, "future"):
                    with self.assertRaises(Error):
                        bad = replace(q, **{field: "future"})
                        analyze(bad, self.right) if first else analyze(self.left, bad)

    def test_non_native_closed_enum_strings_rejected(self):
        for q, first in ((self.left, True), (self.right, False)):
            for changes in ({"status": q.status.value}, {"limitations": tuple(v.value for v in q.limitations)},
                            {"upstream_profile_status": q.upstream_profile_status.value}):
                with self.subTest(changes=changes), self.assertRaises(Error):
                    bad = replace(q, **changes)
                    analyze(bad, self.right) if first else analyze(self.left, bad)

    def test_unknown_and_wrong_reason_families_rejected(self):
        for q, first, reason_type in ((self.left, True, income.CurrentAnnualRevenueOperatingIncomeReason),
                                      (self.right, False, assets.CurrentAnnualOpeningClosingAssetsReason)):
            for reasons in (("UNKNOWN",), (reason_type.UPSTREAM_PROFILE_UNAVAILABLE,), [],
                            (reason_type.UPSTREAM_SOURCE_CONFLICT,) * 2):
                with self.subTest(first=first, reasons=reasons), self.assertRaises(Error):
                    bad = replace(q, reasons=reasons)
                    analyze(bad, self.right) if first else analyze(self.left, bad)

    def test_all_native_status_pairs_preserve_blockers_and_precedence(self):
        priority = {"established": -1, "unavailable": 0, "unsupported": 1, "conflict": 2}
        statuses = {"unavailable": Status.UNAVAILABLE, "unsupported": Status.UNSUPPORTED, "conflict": Status.SOURCE_CONFLICT}
        suffix = {"unavailable": "EVIDENCE_UNAVAILABLE", "unsupported": "EVIDENCE_UNSUPPORTED", "conflict": "SOURCE_CONFLICT"}
        for left_state, left_pair in self.pairs.items():
            for right_state, right_pair in self.pairs.items():
                with self.subTest(left=left_state, right=right_state):
                    result = analyze(left_pair[0], right_pair[1])
                    if left_state == right_state == "established":
                        self.assertEqual(result.status, Status.AVAILABLE)
                        continue
                    winner = max((left_state, right_state), key=priority.__getitem__)
                    self.assertEqual(result.status, statuses[winner])
                    expected = []
                    for state, prefix in ((left_state, "UPSTREAM_REVENUE_OPERATING_INCOME_"),
                                          (right_state, "UPSTREAM_OPENING_CLOSING_ASSETS_")):
                        if state != "established":
                            expected.append(Reason(prefix + suffix[state]))
                    self.assertEqual(result.reasons, tuple(sorted(expected, key=lambda r: r.value)))
                    self.assertIsNone(result.operating_income_to_two_point_average_assets_ratio)
                    self.assertEqual(result.upstream_revenue_operating_income_reasons, left_pair[0].reasons)
                    self.assertEqual(result.upstream_opening_closing_assets_reasons, right_pair[1].reasons)

    def test_blocked_objects_cannot_carry_partial_amounts_or_provenance(self):
        left, right = self.pairs["unavailable"]
        changes_left = ({"operating_income": Decimal(0)}, {"revenue": Decimal(0)},
                        {"selected_revenue_observation_ids": ("0" * 64,)}, {"supporting_filings": self.left.supporting_filings})
        changes_right = ({"opening_assets": Decimal(0)}, {"closing_assets": Decimal(0)},
                         {"selected_opening_observations": self.right.selected_opening_observations},
                         {"selected_closing_observations": self.right.selected_closing_observations},
                         {"supporting_accessions": (LATEST_ACCESSION,)})
        for change in changes_left:
            with self.assertRaises(Error):
                analyze(replace(left, **change), self.right)
        for change in changes_right:
            with self.assertRaises(Error):
                analyze(self.left, replace(right, **change))

    def test_factory_impossible_profile_projection_rejected(self):
        for q, first in ((self.left, True), (self.right, False)):
            bad = replace(q, upstream_profile_status=profiles.OrdinaryCompounderProfileStatus.PROFILE_UNSUPPORTED,
                          upstream_profile_reasons=(profiles.ProfileReason.UNSUPPORTED_SIC_PROFILE,))
            with self.assertRaises(Error):
                analyze(bad, self.right) if first else analyze(self.left, bad)

    def test_malformed_identity_route_and_capture_context_rejected(self):
        for q, first in ((self.left, True), (self.right, False)):
            changes = {"source_cik": "123", "upstream_profile_semantic_id": "bad",
                       "upstream_comparability_semantic_id": "bad", "upstream_profile_evidence_id": "bad",
                       "upstream_comparability_evidence_id": "bad", "route_local_issuer_key": None,
                       "route_local_security_key": "bad", "capture_receipt_id": "bad", "source_object_hash": "bad",
                       "captured_at": "2026-02-25", "capture_source_locator": " ", "period_start": "bad",
                       "period_end": "2023-01-01"}
            for field, value in changes.items():
                with self.subTest(first=first, field=field), self.assertRaises(Error):
                    bad = replace(q, **{field: value})
                    analyze(bad, self.right) if first else analyze(self.left, bad)

    def test_wrong_issuer_is_contract_error(self):
        with self.assertRaises(Error):
            analyze(replace(self.left, source_cik="0000000099"), self.right)

    def test_wrong_annual_start_and_end_are_contract_errors(self):
        for change in ({"period_start": "2024-02-01"}, {"period_end": "2024-11-30"}):
            with self.assertRaises(Error):
                analyze(replace(self.left, **change), self.right)

    def test_wrong_balance_dates_are_contract_errors(self):
        for change in ({"opening_balance_date": "2024-01-01"}, {"closing_balance_date": "2023-12-31"},
                       {"opening_balance_date": None}, {"closing_balance_date": None}):
            with self.assertRaises(Error):
                analyze(self.left, replace(self.right, **change))

    def test_nonfinite_missing_or_inexact_amounts_rejected(self):
        for q, first, names in ((self.left, True, ("revenue", "operating_income")),
                                (self.right, False, ("opening_assets", "closing_assets"))):
            for name in names:
                for amount in (None, 1, 1.0, Decimal("NaN"), Decimal("Infinity")):
                    with self.subTest(first=first, name=name, amount=str(amount)), self.assertRaises(Error):
                        bad = replace(q, **{name: amount})
                        analyze(bad, self.right) if first else analyze(self.left, bad)

    def test_selected_partition_mutations_rejected(self):
        for q, first, field in ((self.left, True, "selected_operating_income_observation_ids"),
                                (self.right, False, "selected_opening_assets_observation_ids")):
            for ids in ((), ["0" * 64], ("0" * 64,), getattr(q, field) * 2):
                with self.assertRaises(Error):
                    bad = replace(q, **{field: ids})
                    analyze(bad, self.right) if first else analyze(self.left, bad)

    def test_supporting_filing_metadata_and_partitions_rejected(self):
        for q, first in ((self.left, True), (self.right, False)):
            filing = q.supporting_filings[0]
            for change in ({"forms": ("10-Q",)}, {"filed_dates": ("bad",)}, {"fiscal_years": (True,)},
                           {"accession": "bad"}, {"forms": ["10-K"]}):
                with self.assertRaises(Error):
                    bad = replace(q, supporting_filings=(replace(filing, **change),))
                    analyze(bad, self.right) if first else analyze(self.left, bad)
            with self.assertRaises(Error):
                bad = replace(q, supporting_accessions=(SECOND_ACCESSION,))
                analyze(bad, self.right) if first else analyze(self.left, bad)

    def test_selected_assets_observation_provenance_is_validated(self):
        row = self.right.selected_opening_observations[0]
        changes = {"value": Decimal(999), "source_cik": "0000000099", "concept": "Liabilities", "end": "2023-12-30",
                   "start": "2023-01-01", "fp": "Q4", "fy": True, "form": "10-Q", "filed": "2025-03-01",
                   "source_object_hash": "0" * 64, "capture_receipt_id": "0" * 64, "captured_at": BOUNDARY_T2,
                   "extraction_version": "future", "source_locator": "bad", "semantic_locator": "bad",
                   "row_json": "{}", "source_semantics": (), "metadata_limitations": ("MISSING_VALUE",)}
        for field, value in changes.items():
            with self.subTest(field=field), self.assertRaises(Error):
                analyze(self.left, replace(self.right, selected_opening_observations=(replace(row, **{field: value}),)))
        for rows in ([], (), ({},)):
            with self.assertRaises(Error):
                analyze(self.left, replace(self.right, selected_closing_observations=rows))

    def test_native_local_unavailability_is_preserved(self):
        left, right = self.make_pair(combined_payload(include_operating_income=False))
        result = analyze(left, right)
        self.assertEqual(result.status, Status.UNAVAILABLE)
        self.assertEqual(result.upstream_revenue_operating_income_reasons, left.reasons)
        payload = combined_payload()
        del payload["facts"]["us-gaap"]["Assets"]
        left, right = self.make_pair(payload)
        self.assertEqual(analyze(left, right).reasons, (Reason.UPSTREAM_OPENING_CLOSING_ASSETS_EVIDENCE_UNAVAILABLE,))

    def test_native_local_conflict_is_preserved(self):
        payload = combined_payload()
        payload["facts"]["us-gaap"]["OperatingIncomeLoss"]["units"]["USD"].append(financial_row(21, accession=SECOND_ACCESSION))
        payload["facts"]["us-gaap"]["RevenueFromContractWithCustomerExcludingAssessedTax"]["units"]["USD"].append(financial_row(250, accession=SECOND_ACCESSION))
        left, right = self.make_pair(payload)
        self.assertEqual(analyze(left, right).reasons, (Reason.UPSTREAM_REVENUE_OPERATING_INCOME_SOURCE_CONFLICT,))

    def test_independent_authentic_captures_are_accepted(self):
        left, _ = self.make_pair(combined_payload(), captured_at=BOUNDARY_T1)
        _, right = self.make_pair(combined_payload(revenue=251), captured_at=BOUNDARY_T2)
        self.assertNotEqual(left.capture_receipt_id, right.capture_receipt_id)
        self.assertNotEqual(left.source_object_hash, right.source_object_hash)
        self.assertNotEqual(left.upstream_profile_semantic_id, right.upstream_profile_semantic_id)
        self.assertNotEqual(left.route_local_security_key, right.route_local_security_key)
        self.assertEqual(analyze(left, right).status, Status.AVAILABLE)

    def test_no_common_selected_accession(self):
        payload = combined_payload()
        for row in payload["facts"]["us-gaap"]["Assets"]["units"]["USD"]:
            row["accn"] = SECOND_ACCESSION
        _, right = self.make_pair(payload)
        result = analyze(self.left, right)
        self.assertEqual(result.status, Status.UNAVAILABLE)
        self.assertEqual(result.reasons, (Reason.NO_COMMON_SUPPORTING_ANNUAL_FILING_ACCESSION,))
        self.assertEqual(result.common_supporting_accessions, ())
        self.assertIsNone(result.operating_income_to_two_point_average_assets_ratio)

    def extra_filing_payload(self, *, second_metadata=None, only_income=False, only_assets=False):
        payload = combined_payload()
        for concept in ("Assets", "OperatingIncomeLoss", "RevenueFromContractWithCustomerExcludingAssessedTax"):
            if only_income and concept == "Assets" or only_assets and concept != "Assets":
                continue
            rows = payload["facts"]["us-gaap"][concept]["units"]["USD"]
            for row in deepcopy(rows):
                row["accn"] = SECOND_ACCESSION
                row["filed"] = "2025-02-02"
                if second_metadata:
                    row.update(second_metadata)
                rows.append(row)
        return payload

    def test_multiple_common_accessions(self):
        result = analyze(*self.make_pair(self.extra_filing_payload()))
        self.assertEqual(result.status, Status.AVAILABLE)
        self.assertEqual(result.common_supporting_accessions, (LATEST_ACCESSION, SECOND_ACCESSION))

    def test_every_common_filing_is_checked(self):
        left, _ = self.make_pair(self.extra_filing_payload())
        _, right = self.make_pair(self.extra_filing_payload(second_metadata={"filed": "2025-03-01"}))
        result = analyze(left, right)
        self.assertEqual(result.status, Status.SOURCE_CONFLICT)
        self.assertEqual(result.reasons, (Reason.COMMON_SUPPORTING_FILING_METADATA_CONFLICT,))
        self.assertEqual(len(result.common_supporting_accessions), 2)

    def test_form_filed_date_and_fiscal_year_conflicts(self):
        for metadata in ({"form": "10-K/A"}, {"filed": "2025-03-01"}, {"fy": 2025}):
            payload = combined_payload()
            for row in payload["facts"]["us-gaap"]["Assets"]["units"]["USD"]:
                row.update(metadata)
            _, right = self.make_pair(payload)
            result = analyze(self.left, right)
            self.assertEqual(result.status, Status.SOURCE_CONFLICT)
            self.assertEqual(result.reasons, (Reason.COMMON_SUPPORTING_FILING_METADATA_CONFLICT,))

    def test_nonshared_extra_filings_do_not_poison_join(self):
        for payload in (self.extra_filing_payload(only_income=True), self.extra_filing_payload(only_assets=True)):
            result = analyze(*self.make_pair(payload))
            self.assertEqual(result.status, Status.AVAILABLE)
            self.assertEqual(result.common_supporting_accessions, (LATEST_ACCESSION,))

    def test_join_precedes_nonpositive_endpoint_classification(self):
        payload = combined_payload(opening=0, closing=-1)
        for row in payload["facts"]["us-gaap"]["Assets"]["units"]["USD"]:
            row["accn"] = SECOND_ACCESSION
        _, right = self.make_pair(payload)
        self.assertEqual(analyze(self.left, right).status, Status.UNAVAILABLE)
        payload = combined_payload(opening=0, closing=-1)
        for row in payload["facts"]["us-gaap"]["Assets"]["units"]["USD"]:
            row["filed"] = "2025-03-01"
        _, right = self.make_pair(payload)
        self.assertEqual(analyze(self.left, right).status, Status.SOURCE_CONFLICT)

    def test_signed_and_zero_operating_income(self):
        for value, expected in ((20, Ratio(1, 10)), (0, Ratio(0, 1)), (-20, Ratio(-1, 10))):
            result = analyze(*self.make_pair(combined_payload(i=value)))
            self.assertEqual(result.status, Status.AVAILABLE)
            self.assertEqual(result.operating_income_to_two_point_average_assets_ratio, expected)

    def test_each_nonpositive_endpoint(self):
        for opening, closing, reason in (
            (0, 300, Reason.OPENING_ASSETS_ZERO_ENDPOINT),
            (-1, 300, Reason.OPENING_ASSETS_NEGATIVE_NOT_POSITIVE_ENDPOINT),
            (100, 0, Reason.CLOSING_ASSETS_ZERO_ENDPOINT),
            (100, -1, Reason.CLOSING_ASSETS_NEGATIVE_NOT_POSITIVE_ENDPOINT),
        ):
            result = analyze(*self.make_pair(combined_payload(opening=opening, closing=closing)))
            self.assertEqual((result.status, result.reasons), (Status.NOT_APPLICABLE, (reason,)))
            self.assertIsNone(result.operating_income_to_two_point_average_assets_ratio)

    def test_all_double_endpoint_failures_are_retained(self):
        for opening in (0, -1):
            for closing in (0, -1):
                result = analyze(*self.make_pair(combined_payload(opening=opening, closing=closing)))
                expected = (Reason.OPENING_ASSETS_ZERO_ENDPOINT if opening == 0 else Reason.OPENING_ASSETS_NEGATIVE_NOT_POSITIVE_ENDPOINT,
                            Reason.CLOSING_ASSETS_ZERO_ENDPOINT if closing == 0 else Reason.CLOSING_ASSETS_NEGATIVE_NOT_POSITIVE_ENDPOINT)
                self.assertEqual(result.reasons, tuple(sorted(expected, key=lambda r: r.value)))
                self.assertEqual(result.status, Status.NOT_APPLICABLE)
                self.assertIsNone(result.operating_income_to_two_point_average_assets_ratio)

    def test_exact_high_precision_and_low_ambient_context(self):
        values = (Decimal("-20.123456789012345678901234567890123456789"),
                  Decimal("100.000000000000000000000000000000000000001"),
                  Decimal("300.222222222222222222222222222222222222222"))
        pair = self.make_pair(combined_payload(i=values[0], opening=values[1], closing=values[2]))
        expected = 2 * Fraction(values[0]) / (Fraction(values[1]) + Fraction(values[2]))
        with localcontext() as context:
            context.prec = 2
            result = analyze(*pair)
        ratio = result.operating_income_to_two_point_average_assets_ratio
        self.assertEqual((ratio.numerator, ratio.denominator), (expected.numerator, expected.denominator))
        self.assertEqual(result.semantic_id, analyze(*pair).semantic_id)

    def test_rational_reduction_positive_denominator_and_zero(self):
        for n, d, expected in ((6, 12, (1, 2)), (6, -12, (-1, 2)), (-6, -12, (1, 2)), (0, -99, (0, 1))):
            ratio = Ratio(n, d)
            self.assertEqual((ratio.numerator, ratio.denominator), expected)
        for n, d in ((True, 1), (1, False), (1.0, 2), (1, 0), (Decimal(1), 2)):
            with self.assertRaises(Error):
                Ratio(n, d)

    def test_equivalent_decimal_representations(self):
        a = analyze(*self.make_pair(combined_payload(i=Decimal("20.00"), opening=Decimal("100.0"), closing=Decimal("3E2"))))
        b = analyze(self.left, self.right)
        self.assertEqual(a.operating_income_to_two_point_average_assets_ratio, b.operating_income_to_two_point_average_assets_ratio)
        self.assertEqual(a.semantic_id, b.semantic_id)

    def test_scaled_operands_same_ratio_different_semantics(self):
        a = analyze(self.left, self.right)
        b = analyze(*self.make_pair(combined_payload(i=40, opening=200, closing=600)))
        self.assertEqual(a.operating_income_to_two_point_average_assets_ratio, b.operating_income_to_two_point_average_assets_ratio)
        self.assertNotEqual(a.semantic_id, b.semantic_id)

    def test_each_genuine_operand_change_changes_semantics(self):
        base = analyze(self.left, self.right)
        for change in ({"i": 21}, {"opening": 101}, {"closing": 301}):
            changed = analyze(*self.make_pair(combined_payload(**change)))
            self.assertNotEqual(base.semantic_id, changed.semantic_id)

    def test_nonapplicable_semantics_still_bind_all_three_operands(self):
        base = analyze(*self.make_pair(combined_payload(opening=0)))
        for change in ({"i": 21, "opening": 0}, {"opening": 0, "closing": 301}, {"opening": -1}):
            changed = analyze(*self.make_pair(combined_payload(**change)))
            self.assertNotEqual(base.semantic_id, changed.semantic_id)
            self.assertEqual(changed.status, Status.NOT_APPLICABLE)

    def test_authentic_recapture_preserves_semantics_changes_evidence(self):
        before = self.make_pair(combined_payload(), captured_at=BOUNDARY_T1)
        after = self.make_pair(combined_payload(), captured_at=BOUNDARY_T2)
        for a, b in zip(before, after):
            self.assertNotEqual(a.capture_receipt_id, b.capture_receipt_id)
            self.assertNotEqual(a.evidence_id, b.evidence_id)
        a, b = analyze(*before), analyze(*after)
        self.assertEqual(a.semantic_id, b.semantic_id)
        self.assertNotEqual(a.evidence_id, b.evidence_id)

    def test_authentic_revenue_only_change_preserves_semantics_changes_evidence(self):
        before = self.make_pair(combined_payload(revenue=250))
        after = self.make_pair(combined_payload(revenue=251))
        self.assertNotEqual(before[0].semantic_id, after[0].semantic_id)
        self.assertNotEqual(before[0].source_object_hash, after[0].source_object_hash)
        a, b = analyze(*before), analyze(*after)
        self.assertEqual(a.semantic_id, b.semantic_id)
        self.assertNotEqual(a.evidence_id, b.evidence_id)

    def test_revenue_zero_or_negative_is_not_an_operand(self):
        for revenue in (0, -1):
            result = analyze(*self.make_pair(combined_payload(revenue=revenue)))
            self.assertEqual(result.status, Status.AVAILABLE)
            self.assertEqual(result.semantic_id, analyze(self.left, self.right).semantic_id)

    def test_reordered_source_rows_preserve_economic_identity(self):
        payload = self.extra_filing_payload()
        a = analyze(*self.make_pair(payload))
        for node in payload["facts"]["us-gaap"].values():
            for rows in node.get("units", {}).values():
                rows.reverse()
        b = analyze(*self.make_pair(payload))
        self.assertEqual(a.semantic_id, b.semantic_id)
        self.assertNotEqual(a.evidence_id, b.evidence_id)

    def test_filing_provenance_does_not_contaminate_semantic_identity(self):
        a = analyze(self.left, self.right)
        b = analyze(*self.make_pair(self.extra_filing_payload()))
        self.assertEqual(a.semantic_id, b.semantic_id)
        self.assertNotEqual(a.evidence_id, b.evidence_id)

    def test_no_io_clock_extraction_replay_or_requalification(self):
        with patch.object(socket, "socket", side_effect=AssertionError("network")), \
             patch.object(time, "time", side_effect=AssertionError("clock")), \
             patch("builtins.open", side_effect=AssertionError("file IO")), \
             patch.object(income, "qualify_sec_current_annual_revenue_operating_income", side_effect=AssertionError("requalification")), \
             patch.object(assets, "qualify_sec_current_annual_opening_closing_assets", side_effect=AssertionError("requalification")), \
             patch.object(assets, "extract_assets_liabilities", side_effect=AssertionError("extraction")), \
             patch.object(assets, "assess_sec_current_evidence", side_effect=AssertionError("replay")):
            self.assertEqual(analyze(self.left, self.right).status, Status.AVAILABLE)

    def test_impossible_blocker_families_raise_contract_error(self):
        for q, first, reason_type in (
            (self.pairs["unavailable"][0], True, income.CurrentAnnualRevenueOperatingIncomeReason),
            (self.pairs["unavailable"][1], False, assets.CurrentAnnualOpeningClosingAssetsReason),
        ):
            for reasons in ((reason_type.COMMON_FILING_METADATA_CONFLICT,),
                            (reason_type.UPSTREAM_PROFILE_UNSUPPORTED,),
                            (reason_type.UPSTREAM_PROFILE_UNAVAILABLE, reason_type.EXACT_USD_UNIT_UNAVAILABLE)):
                with self.assertRaises(Error):
                    bad = replace(q, reasons=reasons)
                    analyze(bad, self.right) if first else analyze(self.left, bad)

    def test_established_missing_entire_capture_context_is_rejected(self):
        for q, first in ((self.left, True), (self.right, False)):
            bad = replace(q, capture_receipt_id=None, source_object_hash=None,
                          captured_at=None, capture_source_locator=None)
            with self.assertRaises(Error):
                analyze(bad, self.right) if first else analyze(self.left, bad)

    def test_assets_local_competing_values_project_native_conflict(self):
        payload = self.extra_filing_payload()
        payload["facts"]["us-gaap"]["Assets"]["units"]["USD"][-1]["val"] = 301
        pair = self.make_pair(payload)
        result = analyze(*pair)
        self.assertEqual(result.status, Status.SOURCE_CONFLICT)
        self.assertEqual(result.reasons, (Reason.UPSTREAM_OPENING_CLOSING_ASSETS_SOURCE_CONFLICT,))
        self.assertEqual(result.upstream_opening_closing_assets_reasons,
                         (assets.CurrentAnnualOpeningClosingAssetsReason.COMPETING_CLOSING_ASSETS_VALUES,))

    def test_genuine_wrong_units_and_missing_instant_keep_native_reasons(self):
        payload = combined_payload()
        node = payload["facts"]["us-gaap"]["Assets"]["units"]
        node["shares"] = node.pop("USD")
        pair = self.make_pair(payload)
        self.assertEqual(analyze(*pair).status, Status.UNAVAILABLE)
        self.assertEqual(pair[1].reasons, (assets.CurrentAnnualOpeningClosingAssetsReason.EXACT_USD_UNIT_UNAVAILABLE,))
        payload = combined_payload()
        payload["facts"]["us-gaap"]["Assets"]["units"]["USD"].pop(0)
        pair = self.make_pair(payload)
        self.assertEqual(analyze(*pair).status, Status.UNAVAILABLE)
        self.assertIn(assets.CurrentAnnualOpeningClosingAssetsReason.OPENING_ASSETS_UNAVAILABLE, pair[1].reasons)

    def test_boundary_unavailable_cannot_claim_a_present_opening_date(self):
        bad = replace(self.right,
            status=assets.CurrentAnnualOpeningClosingAssetsStatus.EVIDENCE_UNAVAILABLE,
            reasons=(assets.CurrentAnnualOpeningClosingAssetsReason.CANONICAL_OPENING_BALANCE_DATE_UNAVAILABLE,),
            opening_assets=None, closing_assets=None, selected_opening_assets_observation_ids=(),
            selected_closing_assets_observation_ids=(), selected_opening_observations=(),
            selected_closing_observations=(), supporting_accessions=(), supporting_filings=())
        with self.assertRaises(Error):
            analyze(self.left, bad)
        # Defensive projection only: current factory admits adjacent annual chains.
        result = analyze(self.left, replace(bad, opening_balance_date=None))
        self.assertEqual(result.status, Status.UNAVAILABLE)

    def test_duplicate_or_nonfinite_selected_row_json_rejected(self):
        row = self.right.selected_opening_observations[0]
        for text in ('{"val":100,"val":100}', '{"val":NaN}'):
            with self.assertRaises(Error):
                analyze(self.left, replace(self.right, selected_opening_observations=(replace(row, row_json=text),)))

    def test_independent_one_foundation_recapture_binds_evidence(self):
        later = self.make_pair(combined_payload(), captured_at=BOUNDARY_T2)
        original = analyze(self.left, self.right)
        for pair in ((later[0], self.right), (self.left, later[1])):
            result = analyze(*pair)
            self.assertEqual(result.semantic_id, original.semantic_id)
            self.assertNotEqual(result.evidence_id, original.evidence_id)

    def test_decimal_rounding_traps_do_not_affect_integer_arithmetic(self):
        from decimal import Inexact, Rounded
        pair = self.make_pair(combined_payload(i=Decimal("20.000000000001"),
                                              opening=Decimal("100.000000000003"),
                                              closing=Decimal("300.000000000007")))
        expected = analyze(*pair)
        with localcontext() as context:
            context.prec = 1
            context.traps[Inexact] = True
            context.traps[Rounded] = True
            actual = analyze(*pair)
            self.assertEqual(actual.semantic_id, expected.semantic_id)
            self.assertEqual(actual.evidence_id, expected.evidence_id)
            self.assertEqual(actual.operating_income_to_two_point_average_assets_ratio,
                             expected.operating_income_to_two_point_average_assets_ratio)

    def test_source_has_no_division_float_provider_or_upstream_factory_import(self):
        tree = ast.parse(Path(diagnostic.__file__).read_text())
        for node in ast.walk(tree):
            self.assertFalse(isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div))
            self.assertFalse(isinstance(node, ast.Constant) and type(node.value) is float)
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [n.name for n in node.names] if isinstance(node, ast.Import) else [node.module or ""]
                self.assertFalse(any(name.startswith(("economic_facts", "requests", "urllib", "yfinance")) for name in names))


if __name__ == "__main__":
    unittest.main()
