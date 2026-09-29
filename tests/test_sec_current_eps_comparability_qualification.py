"""PR5C comparable-real-EPS qualification tests using controlled SEC-shaped bytes."""
from dataclasses import fields, replace
from decimal import Decimal
from pathlib import Path
import inspect
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from economic_facts import sec_current_eps_comparability_qualification as comparability
from economic_facts import sec_five_year_eps_presentation as presentation
from economic_facts import sec_reporting_subject_source_claims as subject_source
from economic_facts import sec_share_basis_source_claims as basis_source
from economic_facts import sec_current_security_eps_qualification as security_qualification
from economic_facts.nasdaq_listed_archive import NasdaqListedArchive
from economic_facts.sec_archive import SecArchive
from economic_facts.sec_current_registered_listing_bridge import (
    SecCurrentRegisteredListingBridgeRequest,
)
from economic_facts.sec_filing_archive import SecFilingArchive
from economic_facts.sec_property4_temporal_boundary import SecProperty4TemporalBoundaryRequest
from economic_facts.sec_section12_rights_source_claims import (
    SecSection12RightsSourceClaimsRequest,
)
from economic_facts.sec_submissions_archive import SecSubmissionsArchive
from economic_facts.sec_temporal_common_stock_source_series import (
    SecTemporalCommonStockSourceSeriesRequest,
)
from economic_facts.sec_ticker_exchange_archive import SecTickerExchangeArchive
from tests.sec_current_registered_listing_bridge_fixtures import (
    NASDAQ_CAPTURE,
    SEC_CAPTURE,
    nasdaq_snapshot,
    sec_snapshot,
)
from tests.sec_current_security_eps_qualification_fixtures import (
    VALUES,
    accession,
    companyfacts_rows,
    qualification_submission,
    source_rows,
)
from tests.sec_five_year_eps_presentation_fixtures import (
    five_year_table,
    inject_before_body,
)
from tests.sec_filing_document_inventory_fixtures import (
    embedded_document,
    filing_inventory,
)
from tests.sec_property4_temporal_boundary_fixtures import (
    BOUNDARY_T1,
    capture_current,
    current_request,
)
from tests.sec_property4_temporal_fixtures import CIK
from tests.sec_submissions_fixtures import root as submissions_root


SPLIT_WITH_RETROSPECTIVE = (
    "A 2-for-1 stock split of our Class A Common Stock became effective on "
    "January 15, 2024. Earnings per share and per share amounts for all periods "
    "presented were retrospectively adjusted to reflect the stock split."
)


class SecCurrentEPSComparabilityTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        base = Path(temporary.name).resolve()
        self.current_archive = SecArchive(base / "current")
        self.submissions_archive = SecSubmissionsArchive(base / "submissions")
        self.filing_archive = SecFilingArchive(base / "filings")
        self.sec_archive = SecTickerExchangeArchive(base / "sec-associations")
        self.nasdaq_archive = NasdaqListedArchive(base / "nasdaq")

    def current(self, *, rows=None):
        receipt = capture_current(
            self.current_archive, boundary=BOUNDARY_T1, live=True,
            rows=companyfacts_rows() if rows is None else rows)
        return current_request(receipt)

    def parent(self):
        return self.submissions_archive._capture_live(
            submissions_root(source_rows(), cik=CIK), cik=CIK,
            captured_at="2026-02-25T12:00:00Z")

    def filing(self, year, *, amendment=False, html=(), raw=None,
               captured_at=None, value=None):
        if captured_at is None:
            second = year - 2020 + (10 if amendment else 0)
            captured_at = f"2026-02-20T12:00:{second:02d}Z"
        if raw is None:
            raw = qualification_submission(
                year, amendment=amendment,
                value=VALUES[year] if value is None else value)
            # The PR5B fixture exposes visible Inline XBRL facts directly
            # beneath ``body``.  The PR5C0A/PR5C0B source grammars require
            # visible prose to live in a supported block, so make that block
            # explicit while retaining identical filing bytes for every
            # replayed layer.  Presentation HTML is appended outside it.
            raw = raw.replace(b"<body>", b"<body><div>", 1)
            raw = raw.replace(b"</body>", b"</div></body>", 1)
            if html:
                raw = inject_before_body(raw, *html)
        return self.filing_archive._capture_live(
            raw, cik=CIK, accession=accession(year, amendment=amendment),
            captured_at=captured_at)

    def filings(self, *, table=None, claims=(), value_overrides=None):
        if table is None:
            table = five_year_table()
        value_overrides = {} if value_overrides is None else value_overrides
        filings = []
        for year in VALUES:
            html = ()
            if year == 2024:
                html = tuple(f"<p>{claim}</p>" for claim in claims) + (table,)
            filings.append(self.filing(year, html=html,
                                       value=value_overrides.get(year)))
        filings.append(self.filing(2022, amendment=True,
                                   value=value_overrides.get(2022)))
        return tuple(filings)

    def security_request(self, current, parent, filings):
        temporal = SecProperty4TemporalBoundaryRequest(
            current, parent.receipt_id, (), tuple(item.receipt_id for item in filings))
        listing = SecCurrentRegisteredListingBridgeRequest(
            temporal,
            self.sec_archive._capture_live(
                sec_snapshot(), captured_at=SEC_CAPTURE).receipt_id,
            self.nasdaq_archive._capture_live(
                nasdaq_snapshot(), captured_at=NASDAQ_CAPTURE).receipt_id,
        )
        rights = tuple(SecSection12RightsSourceClaimsRequest(item.receipt_id)
                       for item in filings)
        return security_qualification.SecCurrentSecurityEPSQualificationRequest(
            SecTemporalCommonStockSourceSeriesRequest(listing, rights))

    def build_request(self, *, filings=None, current=None, parent=None,
                      subject_filing_ids=None, basis_filing_ids=None,
                      presentation_receipt=None):
        filings = self.filings() if filings is None else filings
        parent = self.parent() if parent is None else parent
        current = self.current() if current is None else current
        security_request = self.security_request(current, parent, filings)
        security = security_qualification.qualify_sec_current_security_eps(
            self.current_archive, self.submissions_archive, self.filing_archive,
            self.sec_archive, self.nasdaq_archive, security_request)
        series = (security.upstream_registered_listing_bridge.temporal_boundary
                  .current_evidence.resolution.series)
        subject_request = subject_source.SecReportingSubjectSourceRequest(
            parent.receipt_id, (),
            tuple(item.receipt_id for item in filings)
            if subject_filing_ids is None else tuple(subject_filing_ids))
        basis_request = basis_source.SecShareBasisSourceRequest(
            parent.receipt_id, (),
            tuple(item.receipt_id for item in filings)
            if basis_filing_ids is None else tuple(basis_filing_ids))
        subject = subject_source.build_sec_reporting_subject_source_foundation(
            self.submissions_archive, self.filing_archive, subject_request)
        basis = basis_source.build_sec_share_basis_source_foundation(
            self.submissions_archive, self.filing_archive, basis_request)
        if presentation_receipt is None:
            presentation_receipt = filings[4]
        presentation_request = presentation.SecFiveYearEPSPresentationRequest(
            presentation_receipt.receipt_id)
        extracted = presentation.extract_sec_five_year_eps_presentation(
            self.filing_archive, presentation_request)
        request = comparability.SecCurrentEPSComparabilityRequest(
            security_request, security.semantic_id, security.evidence_id,
            series.semantic_hash, series.evidence_hash,
            subject_request, subject.semantic_id, subject.evidence_id,
            basis_request, basis.semantic_id, basis.evidence_id,
            presentation_request, extracted.semantic_id, extracted.evidence_id)
        return request

    def qualify_request(self, request):
        return comparability.qualify_sec_current_eps_comparability(
            self.current_archive, self.submissions_archive, self.filing_archive,
            self.sec_archive, self.nasdaq_archive, request)

    def qualify(self, **kwargs):
        return self.qualify_request(self.build_request(**kwargs))

    def test_positive_single_presentation_establishes_both_historical_dimensions(self):
        result = self.qualify()
        self.assertEqual(result.outcome,
                         comparability.ComparabilityOutcome.COMPARABLE_REAL_EPS_ESTABLISHED)
        self.assertEqual(result.historical_share_basis.outcome,
                         comparability.DimensionOutcome.ESTABLISHED)
        self.assertEqual(result.historical_reporting_subject.outcome,
                         comparability.DimensionOutcome.ESTABLISHED)
        self.assertIsNotNone(result.historical_share_basis.qualified_basis_identity)
        self.assertIsNotNone(
            result.historical_reporting_subject.qualified_subject_identity)
        self.assertEqual(len(result.period_decisions), 5)
        self.assertTrue(all(item.outcome is comparability.PeriodOutcome.EXACT_MATCH
                            for item in result.period_decisions))
        for decision, expected in zip(result.period_decisions, VALUES.values()):
            self.assertIs(decision.c3_value,
                          result.upstream_security_eps.upstream_registered_listing_bridge
                          .temporal_boundary.current_evidence.resolution.series.periods[
                              result.period_decisions.index(decision)].value)
            self.assertEqual(decision.c3_value, Decimal(expected))
            self.assertTrue(decision.filing_versions)
        self.assertIn(
            comparability.ComparabilityLimitation.CURRENT_QUOTE_BASIS_NOT_ESTABLISHED,
            result.limitations)
        prohibited = {"current_price", "quote", "bid", "ask", "market_price",
                      "quote_currency", "price_timestamp"}
        self.assertTrue(prohibited.isdisjoint(
            field.name for field in fields(type(result))))

    def test_split_adjusted_positive_route_preserves_c3_decimals_without_arithmetic(self):
        result = self.qualify(filings=self.filings(claims=(SPLIT_WITH_RETROSPECTIVE,)))
        self.assertEqual(result.outcome,
                         comparability.ComparabilityOutcome.COMPARABLE_REAL_EPS_ESTABLISHED)
        self.assertTrue(result.historical_share_basis.retrospective_claim_semantic_ids)
        series = (result.upstream_security_eps.upstream_registered_listing_bridge
                  .temporal_boundary.current_evidence.resolution.series)
        for decision, period in zip(result.period_decisions, series.periods):
            self.assertIs(decision.c3_value, period.value)
            self.assertEqual(decision.presented_value, period.value)

    def test_period_coverage_value_row_and_exactness_fail_closed(self):
        variants = (
            (five_year_table(years=(2024, 2023, 2022, 2021)),
             comparability.ComparabilityOutcome.COMPARABILITY_UNSUPPORTED),
            (five_year_table(heading="Years Ended June 30"),
             comparability.ComparabilityOutcome.COMPARABILITY_UNAVAILABLE),
            (five_year_table(values={2020: 2, 2021: 3, 2022: Decimal("4.01"),
                                     2023: 5, 2024: 6}),
             comparability.ComparabilityOutcome.SOURCE_CONFLICT),
            (five_year_table(row_label="Basic earnings per share"),
             comparability.ComparabilityOutcome.COMPARABILITY_UNSUPPORTED),
            (five_year_table(row_label="Adjusted diluted earnings per share"),
             comparability.ComparabilityOutcome.COMPARABILITY_UNSUPPORTED),
        )
        for table, expected in variants:
            with self.subTest(expected=expected, table=table):
                self.assertEqual(self.qualify(filings=self.filings(table=table)).outcome,
                                 expected)

    def test_rounded_presentation_cannot_replace_exact_c3_decimal(self):
        rows = companyfacts_rows()
        for row in rows:
            if row["fy"] == 2022:
                row["val"] = 4.004
        filings = self.filings(
            table=five_year_table(),
            value_overrides={2022: Decimal("4.004")},
        )
        result = self.qualify(filings=filings, current=self.current(rows=rows))
        self.assertEqual(result.outcome,
                         comparability.ComparabilityOutcome.SOURCE_CONFLICT)
        decision = next(item for item in result.period_decisions
                        if item.period_end == "2022-12-31")
        self.assertEqual(decision.c3_value, Decimal("4.004"))
        self.assertEqual(decision.presented_value, Decimal("4"))
        self.assertEqual(decision.outcome,
                         comparability.PeriodOutcome.PRESENTATION_VALUE_MISMATCH)

    def test_split_requires_exact_terms_class_link_and_all_periods_adjustment(self):
        passages = (
            "A 2-for-1 stock split of our Class A Common Stock became effective on "
            "January 15, 2024.",
            "A 2-for-1 stock split of our Class A Common Stock became effective on "
            "January 15, 2024. Earnings per share were retrospectively adjusted.",
            "A 2-for-1 stock split of our Class A Common Stock became effective on "
            "January 15, 2024. Earnings per share for the year ended 2023 were "
            "retrospectively adjusted.",
            "The board considered a 2-for-1 stock split of our Class A Common Stock.",
            "A stock split of our Common Stock was implemented.",
            "A 2-for-1 stock split of our Class B Common Stock became effective on "
            "January 15, 2024. Earnings per share for all periods presented were "
            "retrospectively adjusted.",
        )
        for passage in passages:
            with self.subTest(passage=passage):
                result = self.qualify(filings=self.filings(claims=(passage,)))
                self.assertNotEqual(
                    result.outcome,
                    comparability.ComparabilityOutcome.COMPARABLE_REAL_EPS_ESTABLISHED)

    def test_unsupported_basis_transformations_and_multiple_classes_block(self):
        passages = (
            "Class A Common Stock was converted into Class B Common Stock.",
            "The recapitalization affected the Class A Common Stock share basis.",
            "The merger exchange converted the Class A Common Stock.",
            "The spin-off affected the Class A Common Stock per-share presentation.",
            "The Class A Common Stock redenomination became effective on January 15, 2024.",
            "The share consolidation of Class A Common Stock was implemented.",
            "The basis-affecting restructuring of Class A Common Stock was completed.",
            "A 2-for-1 stock split of Class A Common Stock and Class B Common Stock "
            "became effective on January 15, 2024.",
        )
        for passage in passages:
            with self.subTest(passage=passage):
                result = self.qualify(filings=self.filings(claims=(passage,)))
                self.assertNotEqual(
                    result.outcome,
                    comparability.ComparabilityOutcome.COMPARABLE_REAL_EPS_ESTABLISHED)

    def test_conflicting_split_terms_have_no_latest_or_majority_winner(self):
        passages = (
            "The 2-for-1 and 3-for-1 stock split of our Class A Common Stock "
            "became effective on January 15, 2024.",
            "The 2-for-1 stock split of our Class A Common Stock became effective "
            "on January 15, 2024 and effective on January 16, 2024.",
        )
        for passage in passages:
            with self.subTest(passage=passage):
                result = self.qualify(filings=self.filings(claims=(passage,)))
                self.assertEqual(result.outcome,
                                 comparability.ComparabilityOutcome.SOURCE_CONFLICT)

    def test_reporting_subject_transition_vocabulary_blocks(self):
        passages = (
            "Old Fiction was the predecessor, and New Fiction became the successor.",
            "Old Fiction was determined to be the accounting acquirer and the continuing reporting entity.",
            "The transaction was a reverse acquisition.",
            "The transaction was a reverse recapitalization.",
            "Predecessor period",
            "Successor period",
            "These are carve-out financial statements.",
            "These are combined financial statements.",
            "The restructuring affected the financial statements.",
        )
        for passage in passages:
            with self.subTest(passage=passage):
                result = self.qualify(filings=self.filings(claims=(passage,)))
                self.assertEqual(result.outcome,
                                 comparability.ComparabilityOutcome.COMPARABILITY_UNSUPPORTED)

    def test_incomplete_source_sets_and_different_byte_recapture_fail_closed(self):
        filings = self.filings()
        incomplete = self.qualify(
            filings=filings,
            subject_filing_ids=tuple(item.receipt_id for item in filings[:-1]))
        self.assertEqual(incomplete.outcome,
                         comparability.ComparabilityOutcome.COMPARABILITY_UNAVAILABLE)

        changed = self.filing(
            2024, html=("<p>Different semantic recapture.</p>", five_year_table()),
            captured_at="2026-02-21T12:00:04Z")
        conflict = self.qualify(
            filings=filings,
            basis_filing_ids=tuple(item.receipt_id for item in filings) +
            (changed.receipt_id,))
        self.assertEqual(conflict.outcome,
                         comparability.ComparabilityOutcome.SOURCE_CONFLICT)

        original_ids = tuple(item.receipt_id for item in filings)
        replaced = self.qualify(
            filings=filings,
            basis_filing_ids=original_ids[:4] + (changed.receipt_id,) + original_ids[5:])
        self.assertEqual(replaced.outcome,
                         comparability.ComparabilityOutcome.SOURCE_CONFLICT)
        self.assertIn(
            comparability.ComparabilityReason.SOURCE_GRAPH_FOREIGN_TO_PR5B_ROUTE,
            replaced.reasons)

    def test_equivalent_recapture_and_caller_order_do_not_change_semantics(self):
        filings = self.filings()
        base = self.qualify(filings=filings)
        duplicate = self.filing(
            2024, raw=self.filing_archive.read_object(filings[4]),
            captured_at="2026-02-21T12:00:04Z")
        enriched = self.qualify(
            filings=filings,
            subject_filing_ids=tuple(reversed(tuple(item.receipt_id for item in filings))) +
            (duplicate.receipt_id,),
            basis_filing_ids=tuple(reversed(tuple(item.receipt_id for item in filings))) +
            (duplicate.receipt_id,))
        self.assertEqual(base.semantic_id, enriched.semantic_id)
        self.assertNotEqual(base.evidence_id, enriched.evidence_id)

    def test_replay_is_pure_and_does_not_read_clock_network_or_directories(self):
        request = self.build_request()
        roots = (
            self.current_archive.root,
            self.submissions_archive.root,
            self.filing_archive.root,
            self.sec_archive.root,
            self.nasdaq_archive.root,
        )
        before = tuple({path.relative_to(root): path.read_bytes()
                        for path in root.rglob("*") if path.is_file()}
                       for root in roots)
        with patch("urllib.request.urlopen",
                   side_effect=AssertionError("network forbidden")), \
             patch("os.listdir", side_effect=AssertionError("scan forbidden")), \
             patch("os.scandir", side_effect=AssertionError("scan forbidden")), \
             patch("time.time", side_effect=AssertionError("clock forbidden")), \
             patch("time.monotonic", side_effect=AssertionError("clock forbidden")):
            result = self.qualify_request(request)
        after = tuple({path.relative_to(root): path.read_bytes()
                       for path in root.rglob("*") if path.is_file()}
                      for root in roots)
        self.assertEqual(result.outcome,
                         comparability.ComparabilityOutcome.COMPARABLE_REAL_EPS_ESTABLISHED)
        self.assertEqual(before, after)

    def test_hash_seed_determinism_for_positive_and_blocked_outcomes(self):
        code = """
from tests.test_sec_current_eps_comparability_qualification import SecCurrentEPSComparabilityTests
from tests.sec_five_year_eps_presentation_fixtures import five_year_table
case = SecCurrentEPSComparabilityTests(methodName='runTest')
case.setUp()
try:
    positive = case.qualify()
    blocked = case.qualify(filings=case.filings(
        table=five_year_table(years=(2024, 2023, 2022, 2021))))
    print(positive.semantic_id, positive.outcome.value)
    print(blocked.semantic_id, blocked.outcome.value)
finally:
    case.doCleanups()
"""
        outputs = []
        for seed in ("1", "777"):
            outputs.append(subprocess.check_output(
                [sys.executable, "-B", "-c", code],
                cwd=Path(__file__).resolve().parents[1],
                env={**os.environ, "PYTHONHASHSEED": seed},
                text=True,
            ))
        self.assertEqual(outputs[0], outputs[1])

    def test_foreign_presentation_and_current_boundary_extension_conflict_or_block(self):
        filings = self.filings()
        foreign_cik = "0000000999"
        foreign_accession = "0000000999-25-000001"
        foreign_raw = filing_inventory(
            cik=foreign_cik,
            accession=foreign_accession,
            documents=(embedded_document(
                document_type="10-K",
                sequence="1",
                filename="foreign-fictional.htm",
                payload=("<html><body>" + five_year_table()
                         + "</body></html>").encode("utf-8"),
            ),),
        )
        foreign = self.filing_archive._capture_live(
            foreign_raw, cik=foreign_cik, accession=foreign_accession,
            captured_at="2026-02-20T12:00:04Z")
        result = self.qualify(filings=filings, presentation_receipt=foreign)
        self.assertEqual(result.outcome,
                         comparability.ComparabilityOutcome.SOURCE_CONFLICT)

        outside_route_accession = "0000000123-25-999999"
        outside_route_raw = filing_inventory(
            cik=CIK,
            accession=outside_route_accession,
            documents=(embedded_document(
                document_type="10-K",
                sequence="1",
                filename="outside-route-fictional.htm",
                payload=("<html><body>" + five_year_table()
                         + "</body></html>").encode("utf-8"),
            ),),
        )
        outside_route = self.filing_archive._capture_live(
            outside_route_raw, cik=CIK, accession=outside_route_accession,
            captured_at="2026-02-20T12:00:04Z")
        result = self.qualify(filings=filings, presentation_receipt=outside_route)
        self.assertEqual(result.outcome,
                         comparability.ComparabilityOutcome.SOURCE_CONFLICT)
        self.assertIn(
            comparability.ComparabilityReason.PRESENTATION_FOREIGN_TO_PR5B_ROUTE,
            result.reasons)

        later = self.filing(
            2024, raw=self.filing_archive.read_object(filings[4]),
            captured_at="2027-02-20T12:00:04Z")
        result = self.qualify(filings=filings, presentation_receipt=later)
        self.assertEqual(result.outcome,
                         comparability.ComparabilityOutcome.COMPARABILITY_UNAVAILABLE)

    def test_forged_expected_upstream_and_c3_identities_are_rejected(self):
        request = self.build_request()
        expected_identity_fields = tuple(
            field.name for field in fields(request)
            if field.name.startswith("expected_")
        )
        for field_name in expected_identity_fields:
            with self.subTest(field_name=field_name):
                forged = replace(request, **{field_name: "0" * 64})
                with self.assertRaises(comparability.SecCurrentEPSComparabilityError):
                    self.qualify_request(forged)

    def test_request_has_no_prebuilt_result_assertion_or_quote_fields(self):
        names = tuple(field.name for field in fields(
            comparability.SecCurrentEPSComparabilityRequest))
        self.assertNotIn("security_eps_result", names)
        self.assertNotIn("reporting_subject_assessment", names)
        self.assertNotIn("share_basis_assessment", names)
        for keyword in ("qualified", "current_price", "quote", "same_basis",
                        "security_eps_result", "source_assessment"):
            with self.subTest(keyword=keyword), self.assertRaises(TypeError):
                comparability.SecCurrentEPSComparabilityRequest(**{keyword: True})
        self.assertEqual(tuple(inspect.signature(
            comparability.qualify_sec_current_eps_comparability).parameters), (
                "current_archive", "submissions_archive", "filing_archive",
                "ticker_exchange_archive", "nasdaq_listed_archive", "request"))


if __name__ == "__main__":
    unittest.main()
