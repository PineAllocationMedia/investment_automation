"""PR5B narrow CURRENT security/EPS qualification tests."""
import ast
from dataclasses import FrozenInstanceError, fields, replace
from decimal import Decimal
import inspect
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from economic_facts import sec_current_security_eps_qualification as qualification
from economic_facts.nasdaq_listed_archive import NasdaqListedArchive
from economic_facts.sec_archive import SecArchive
from economic_facts.sec_current_registered_listing_bridge import (
    SecCurrentRegisteredListingBridgeRequest,
)
from economic_facts.sec_filing_archive import SecFilingArchive
from economic_facts.sec_eps_series import AdmissionBlocker
from economic_facts.sec_property4_temporal_boundary import (
    SecProperty4TemporalBoundaryRequest,
)
from economic_facts.sec_section12_rights_source_claims import (
    SecSection12RightsSourceClaimsRequest,
)
from economic_facts.sec_submissions_archive import SecSubmissionsArchive
from economic_facts.sec_temporal_common_stock_source_series import (
    SecTemporalCommonStockSourceSeriesRequest,
    assess_sec_temporal_common_stock_source_series,
)
from economic_facts.sec_ticker_exchange_archive import SecTickerExchangeArchive
from tests.sec_current_registered_listing_bridge_fixtures import (
    NASDAQ_CAPTURE,
    SEC_CAPTURE,
    nasdaq_snapshot,
    sec_snapshot,
)
from tests.sec_current_security_eps_qualification_fixtures import (
    DISTRIBUTION_SENTENCE,
    LIQUIDATION_SENTENCE,
    NO_PREFERENCE_SENTENCE,
    VALUES,
    VOTING_SENTENCE,
    accession,
    companyfacts_rows,
    qualification_submission,
    source_rows,
    with_competing_common_security,
    with_mixed_dimensioned_eps,
)
from tests.sec_property4_temporal_boundary_fixtures import (
    BOUNDARY_T1,
    capture_current,
    current_request,
)
from tests.sec_property4_temporal_fixtures import CIK
from tests.sec_submissions_fixtures import root as submissions_root


class CurrentSecurityEPSQualificationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        base = Path(temporary.name).resolve()
        self.current_archive = SecArchive(base / "current")
        self.submissions_archive = SecSubmissionsArchive(base / "submissions")
        self.filing_archive = SecFilingArchive(base / "filings")
        self.sec_archive = SecTickerExchangeArchive(base / "sec-associations")
        self.nasdaq_archive = NasdaqListedArchive(base / "nasdaq")

    def current(self, *, rows=None, boundary=BOUNDARY_T1, live=True):
        receipt = capture_current(
            self.current_archive,
            boundary=boundary,
            live=live,
            rows=companyfacts_rows() if rows is None else rows,
        )
        return current_request(receipt)

    def parent(self, *, rows=None):
        return self.submissions_archive._capture_live(
            submissions_root(source_rows() if rows is None else rows, cik=CIK),
            cik=CIK,
            captured_at="2026-02-25T12:00:00Z",
        )

    def filing(self, year, *, amendment=False, captured_at=None, raw=None, **changes):
        if captured_at is None:
            second = year - 2020 + (10 if amendment else 0)
            captured_at = f"2026-02-20T12:00:{second:02d}Z"
        payload = (qualification_submission(year, amendment=amendment, **changes)
                   if raw is None else raw)
        return self.filing_archive._capture_live(
            payload,
            cik=CIK,
            accession=accession(year, amendment=amendment),
            captured_at=captured_at,
        )

    def filings(self, **per_filing_changes):
        values = tuple(self.filing(year, **per_filing_changes) for year in VALUES)
        return values + (self.filing(2022, amendment=True, **per_filing_changes),)

    def sec(self, *, captured_at=SEC_CAPTURE, **changes):
        return self.sec_archive._capture_live(
            sec_snapshot(**changes), captured_at=captured_at)

    def nasdaq(self, *, captured_at=NASDAQ_CAPTURE, **changes):
        return self.nasdaq_archive._capture_live(
            nasdaq_snapshot(**changes), captured_at=captured_at)

    def request(self, current, parent, sec, nasdaq, filings, *, rights=None):
        temporal = SecProperty4TemporalBoundaryRequest(
            current,
            parent.receipt_id,
            (),
            tuple(item.receipt_id for item in filings),
        )
        listing = SecCurrentRegisteredListingBridgeRequest(
            temporal, sec.receipt_id, nasdaq.receipt_id)
        if rights is None:
            rights = tuple(SecSection12RightsSourceClaimsRequest(item.receipt_id)
                           for item in filings)
        source_series = SecTemporalCommonStockSourceSeriesRequest(listing, rights)
        return qualification.SecCurrentSecurityEPSQualificationRequest(source_series)

    def inputs(self, *, current=None, parent=None, filings=None, sec=None,
               nasdaq=None, rights=None):
        current = self.current() if current is None else current
        parent = self.parent() if parent is None else parent
        filings = self.filings() if filings is None else filings
        sec = self.sec() if sec is None else sec
        nasdaq = self.nasdaq() if nasdaq is None else nasdaq
        return self.request(current, parent, sec, nasdaq, filings, rights=rights)

    def qualify_request(self, request):
        return qualification.qualify_sec_current_security_eps(
            self.current_archive,
            self.submissions_archive,
            self.filing_archive,
            self.sec_archive,
            self.nasdaq_archive,
            request,
        )

    def qualify(self, **kwargs):
        return self.qualify_request(self.inputs(**kwargs))

    def test_positive_narrow_route_qualifies_every_retained_version(self):
        result = self.qualify()
        self.assertEqual(
            result.status,
            qualification.QualificationStatus.
            CURRENT_SECURITY_EPS_QUALIFICATION_ESTABLISHED,
        )
        self.assertEqual(result.current_authority_boundary, BOUNDARY_T1)
        self.assertIsNotNone(result.route_local_issuer_key)
        self.assertIsNotNone(result.route_local_security_key)
        self.assertEqual(
            result.qualified_admission_blockers,
            (AdmissionBlocker.SECURITY_SHARE_CLASS_AND_LISTING_NOT_ESTABLISHED,),
        )
        self.assertEqual(result.issues, ())
        self.assertEqual(result.participation.status,
                         qualification.ComponentStatus.QUALIFICATION_ESTABLISHED)
        self.assertEqual(result.relevant_class_coverage.status,
                         qualification.ComponentStatus.QUALIFICATION_ESTABLISHED)
        self.assertEqual(result.direct_listing.status,
                         qualification.ComponentStatus.QUALIFICATION_ESTABLISHED)
        self.assertEqual(len(result.eps_applicability_decisions), 6)
        self.assertTrue(all(
            item.status is qualification.ComponentStatus.QUALIFICATION_ESTABLISHED
            for item in result.eps_applicability_decisions))
        self.assertEqual(
            {item.c3_value for item in result.eps_applicability_decisions},
            {Decimal(value) for value in VALUES.values()},
        )
        self.assertEqual(
            sum(item.accession == accession(2022) for item in result.eps_applicability_decisions),
            1,
        )
        self.assertEqual(
            sum(item.accession == accession(2022, amendment=True)
                for item in result.eps_applicability_decisions),
            1,
        )
        self.assertEqual(result.participation.canonical_source_class_label,
                         "CLASS A COMMON STOCK")
        self.assertEqual(result.direct_listing.source_symbol, "FICT")
        self.assertRegex(result.semantic_id, r"^[0-9a-f]{64}$")
        self.assertRegex(result.evidence_id, r"^[0-9a-f]{64}$")

    def test_public_request_is_closed_and_fresh_replay_is_mandatory(self):
        self.assertEqual(tuple(inspect.signature(
            qualification.qualify_sec_current_security_eps).parameters), (
                "current_archive", "submissions_archive", "filing_archive",
                "ticker_exchange_archive", "nasdaq_listed_archive", "request"))
        self.assertEqual(tuple(field.name for field in fields(
            qualification.SecCurrentSecurityEPSQualificationRequest)),
            ("temporal_source_series_request",))
        request = self.inputs()
        for keyword in (
            "qualified", "ordinary_common", "single_class", "eps_applicable",
            "continuity", "listing_valid", "security_id", "class_id",
            "economic_identity", "assessment",
        ):
            with self.subTest(keyword=keyword), self.assertRaises(TypeError):
                qualification.SecCurrentSecurityEPSQualificationRequest(
                    request.temporal_source_series_request,
                    **{keyword: True},
                )
        with patch.object(
            qualification,
            "assess_sec_temporal_common_stock_source_series",
            wraps=qualification.assess_sec_temporal_common_stock_source_series,
        ) as replay:
            result = self.qualify_request(request)
        self.assertEqual(replay.call_count, 1)
        self.assertEqual(result.status,
                         qualification.QualificationStatus.
                         CURRENT_SECURITY_EPS_QUALIFICATION_ESTABLISHED)

    def test_records_are_frozen_and_explicitly_not_admission(self):
        result = self.qualify()
        with self.assertRaises(FrozenInstanceError):
            result.status = "changed"
        with self.assertRaises(FrozenInstanceError):
            result.eps_applicability_decisions[0].status = "changed"
        self.assertIn(qualification.QualificationLimitation.NO_FINAL_ADMISSION,
                      result.limitations)
        self.assertIn(qualification.QualificationLimitation.
                      NO_SHARE_BASIS_QUALIFICATION, result.limitations)
        self.assertIn(qualification.QualificationLimitation.
                      NO_REPORTING_SUBJECT_QUALIFICATION, result.limitations)
        self.assertIn(qualification.QualificationLimitation.NO_QUOTE_CURRENCY_OR_UNIT,
                      result.limitations)
        self.assertIn(qualification.QualificationLimitation.NO_PRICE,
                      result.limitations)
        self.assertIn(qualification.QualificationLimitation.NO_EXPECTED_RETURN,
                      result.limitations)
        self.assertIn(qualification.QualificationLimitation.NO_GLOBAL_DURABLE_ID,
                      result.limitations)
        self.assertFalse(any("ADMISSION" in status.value for status in (
            result.status, result.participation.status,
            result.relevant_class_coverage.status, result.direct_listing.status)))

    def test_missing_or_generic_rights_text_cannot_establish_participation(self):
        for blocks in (
            (("h2", "CLASS A COMMON STOCK"),),
            (("h2", "CLASS A COMMON STOCK"),
             ("p", "Holders have ordinary voting and dividend rights.")),
        ):
            with self.subTest(blocks=blocks):
                filings = self.filings(rights_blocks=blocks)
                result = self.qualify(filings=filings)
                self.assertNotEqual(
                    result.status,
                    qualification.QualificationStatus.
                    CURRENT_SECURITY_EPS_QUALIFICATION_ESTABLISHED,
                )
                self.assertIn(
                    qualification.QualificationIssue.
                    UNSUPPORTED_ORDINARY_COMMON_PARTICIPATION,
                    result.issues,
                )

    def test_unknown_rights_passage_is_ambiguous_not_interpreted_from_topic(self):
        blocks = (
            ("h2", "CLASS A COMMON STOCK"),
            ("p", DISTRIBUTION_SENTENCE),
            ("p", LIQUIDATION_SENTENCE),
            ("p", "The common stock may be convertible in circumstances described elsewhere."),
        )
        result = self.qualify(filings=self.filings(rights_blocks=blocks))
        self.assertEqual(result.status, qualification.QualificationStatus.SOURCE_CONFLICT)
        self.assertIn(
            qualification.QualificationIssue.
            AMBIGUOUS_ORDINARY_COMMON_PARTICIPATION,
            result.issues,
        )

    def test_negative_conversion_redemption_language_is_supported_only_exactly(self):
        blocks = (
            ("h2", "CLASS A COMMON STOCK"),
            ("p", DISTRIBUTION_SENTENCE),
            ("p", LIQUIDATION_SENTENCE),
            ("p", VOTING_SENTENCE),
            ("p", NO_PREFERENCE_SENTENCE),
        )
        result = self.qualify(filings=self.filings(rights_blocks=blocks))
        self.assertEqual(
            result.status,
            qualification.QualificationStatus.
            CURRENT_SECURITY_EPS_QUALIFICATION_ESTABLISHED,
        )

    def test_competing_registered_common_class_fails_closed(self):
        filings = list(self.filings())
        raw = qualification_submission(2024)
        filings[4] = self.filing(
            2024, raw=with_competing_common_security(raw, 2024))
        result = self.qualify(filings=tuple(filings))
        self.assertEqual(result.status, qualification.QualificationStatus.SOURCE_CONFLICT)
        self.assertIn(
            qualification.QualificationIssue.OBSERVED_COMPETING_RELEVANT_COMMON_CLASS,
            result.issues,
        )

    def test_class_specific_eps_context_blocks_applicability(self):
        filings = list(self.filings())
        filings[4] = self.filing(2024, dimensioned_eps=True)
        result = self.qualify(filings=tuple(filings))
        self.assertIn(
            qualification.QualificationIssue.DIMENSIONED_EPS_CLASS_AMBIGUITY,
            result.issues,
        )
        self.assertIn(
            qualification.QualificationIssue.EPS_APPLICABILITY_NOT_ESTABLISHED,
            result.issues,
        )

    def test_mixed_dimensioned_and_undimensioned_eps_is_source_conflict(self):
        filings = list(self.filings())
        raw = with_mixed_dimensioned_eps(
            qualification_submission(2024), 2024, VALUES[2024])
        filings[4] = self.filing(2024, raw=raw)
        result = self.qualify(filings=tuple(filings))
        self.assertEqual(result.status, qualification.QualificationStatus.SOURCE_CONFLICT)
        self.assertIn(
            qualification.QualificationIssue.
            MIXED_DIMENSIONED_UNDIMENSIONED_SOURCE_CONFLICT,
            result.issues,
        )

    def test_retained_version_period_and_value_mismatches_are_distinct(self):
        period_filings = list(self.filings())
        raw = qualification_submission(2024).replace(
            b"2024-01-01", b"2019-01-01").replace(
            b"2024-12-31", b"2019-12-31")
        period_filings[4] = self.filing(2024, raw=raw)
        period_result = self.qualify(filings=tuple(period_filings))
        self.assertIn(
            qualification.QualificationIssue.RETAINED_C3_VERSION_PERIOD_MISMATCH,
            period_result.issues,
        )

        value_filings = list(self.filings())
        value_filings[4] = self.filing(2024, value="999.00")
        value_result = self.qualify(filings=tuple(value_filings))
        self.assertEqual(value_result.status,
                         qualification.QualificationStatus.SOURCE_CONFLICT)
        self.assertIn(
            qualification.QualificationIssue.RETAINED_C3_VERSION_VALUE_MISMATCH,
            value_result.issues,
        )

    def test_omitted_retained_version_is_not_covered_by_other_versions(self):
        filings = self.filings()
        rights = tuple(SecSection12RightsSourceClaimsRequest(item.receipt_id)
                       for item in filings[:-1])
        result = self.qualify(filings=filings, rights=rights)
        self.assertIn(
            qualification.QualificationIssue.RETAINED_C3_VERSION_NOT_CONTROLLED,
            result.issues,
        )
        self.assertNotEqual(
            result.status,
            qualification.QualificationStatus.
            CURRENT_SECURITY_EPS_QUALIFICATION_ESTABLISHED,
        )

    def test_post_boundary_evidence_cannot_repair_missing_version(self):
        filings = list(self.filings())
        filings[4] = self.filing(2024, captured_at="2026-04-01T12:00:00Z")
        result = self.qualify(filings=tuple(filings))
        self.assertIn(
            qualification.QualificationIssue.EVIDENCE_AFTER_CURRENT_BOUNDARY,
            result.issues,
        )
        self.assertIn(
            qualification.QualificationIssue.RETAINED_C3_VERSION_NOT_CONTROLLED,
            result.issues,
        )

    def test_unsupported_taxonomy_and_instrument_profiles_fail_closed(self):
        taxonomy_filings = list(self.filings())
        raw = qualification_submission(2024).replace(
            b"http://xbrl.sec.gov/dei/2025",
            b"http://xbrl.sec.gov/dei/2099",
        ).replace(
            b"http://fasb.org/us-gaap/2025",
            b"http://fasb.org/us-gaap/2099",
        )
        taxonomy_filings[4] = self.filing(2024, raw=raw)
        taxonomy_result = self.qualify(filings=tuple(taxonomy_filings))
        self.assertIn(
            qualification.QualificationIssue.UNSUPPORTED_SOURCE_TAXONOMY_PROFILE,
            taxonomy_result.issues,
        )

        instrument_result = self.qualify(
            filings=self.filings(title="American Depositary Shares"))
        self.assertIn(
            qualification.QualificationIssue.UNSUPPORTED_INSTRUMENT_PROFILE,
            instrument_result.issues,
        )

    def test_wrong_context_cik_is_a_source_conflict(self):
        filings = list(self.filings())
        raw = qualification_submission(2024).replace(
            b">0000000123</xbrli:identifier>",
            b">0000000999</xbrli:identifier>",
        )
        filings[4] = self.filing(2024, raw=raw)
        result = self.qualify(filings=tuple(filings))
        self.assertEqual(result.status, qualification.QualificationStatus.SOURCE_CONFLICT)
        self.assertIn(qualification.QualificationIssue.ISSUER_CIK_DISAGREEMENT,
                      result.issues)

    def test_d4c2_ambiguity_is_preserved(self):
        from tests.nasdaq_listed_fixtures import row as nasdaq_row
        ambiguous = self.nasdaq_archive._capture_live(
            nasdaq_snapshot(rows=[nasdaq_row("FICT"), nasdaq_row("FICT")]),
            captured_at=NASDAQ_CAPTURE,
        )
        result = self.qualify(nasdaq=ambiguous)
        self.assertEqual(result.status, qualification.QualificationStatus.SOURCE_CONFLICT)
        self.assertIn(qualification.QualificationIssue.D4C2_CONFLICT_OR_AMBIGUITY,
                      result.issues)

    def test_conflicting_d3a_relationship_is_not_cherry_picked(self):
        filings = list(self.filings())
        raw = qualification_submission(2024).replace(
            b'</body>',
            b'<ix:nonNumeric name="dei:TradingSymbol" contextRef="registered">'
            b'OTHER</ix:nonNumeric></body>',
        )
        filings[4] = self.filing(2024, raw=raw)
        result = self.qualify(filings=tuple(filings))
        self.assertEqual(result.status, qualification.QualificationStatus.SOURCE_CONFLICT)
        self.assertIn(
            qualification.QualificationIssue.D4C2_CONFLICT_OR_AMBIGUITY,
            result.issues,
        )
        self.assertEqual(result.qualified_admission_blockers, ())

    def test_matching_ticker_without_matching_cik_cannot_qualify(self):
        result = self.qualify(sec=self.sec(cik=124, symbol="FICT"))
        self.assertNotEqual(
            result.status,
            qualification.QualificationStatus.
            CURRENT_SECURITY_EPS_QUALIFICATION_ESTABLISHED,
        )
        self.assertIsNone(result.route_local_issuer_key)
        self.assertIsNone(result.route_local_security_key)
        self.assertEqual(result.qualified_admission_blockers, ())

    def test_duplicate_conflict_cannot_be_voted_away(self):
        filings = list(self.filings())
        conflicting = self.filing(2024, value="999.00",
                                  captured_at="2026-02-21T12:00:00Z")
        filings.append(conflicting)
        result = self.qualify(filings=tuple(filings))
        self.assertEqual(result.status, qualification.QualificationStatus.SOURCE_CONFLICT)
        self.assertIn(qualification.QualificationIssue.D4D3A_D4D3B_SOURCE_CONFLICT,
                      result.issues)

    def test_caller_permutation_cannot_change_identities(self):
        current, parent, filings, sec, nasdaq = (
            self.current(), self.parent(), self.filings(), self.sec(), self.nasdaq())
        request_a = self.request(current, parent, sec, nasdaq, filings)
        rights = tuple(reversed(
            request_a.temporal_source_series_request.rights_claims_requests))
        request_b = self.request(
            current, parent, sec, nasdaq, tuple(reversed(filings)), rights=rights)
        first = self.qualify_request(request_a)
        second = self.qualify_request(request_b)
        self.assertEqual((first.semantic_id, first.evidence_id),
                         (second.semantic_id, second.evidence_id))

    def test_offline_current_capture_and_unresolved_c3_are_unavailable(self):
        offline = self.qualify(current=self.current(live=False))
        self.assertEqual(
            offline.status,
            qualification.QualificationStatus.UPSTREAM_CURRENT_AUTHORITY_UNAVAILABLE,
        )
        self.assertIn(qualification.QualificationIssue.CURRENT_AUTHORITY_UNAVAILABLE,
                      offline.issues)

        unresolved_rows = companyfacts_rows()[:-2]
        unresolved = self.qualify(current=self.current(rows=unresolved_rows))
        self.assertIn(qualification.QualificationIssue.C3_SERIES_UNAVAILABLE,
                      unresolved.issues)

    def test_exact_public_arguments_require_exact_types(self):
        request = self.inputs()
        arguments = [
            self.current_archive, self.submissions_archive, self.filing_archive,
            self.sec_archive, self.nasdaq_archive, request,
        ]
        for index in range(len(arguments)):
            wrong = list(arguments)
            wrong[index] = object()
            with self.subTest(index=index), self.assertRaises(
                    qualification.SecCurrentSecurityEPSQualificationRequestError):
                qualification.qualify_sec_current_security_eps(*wrong)

    def test_affirmative_all_class_coverage_is_required(self):
        filings = list(self.filings())
        filings[4] = self.filing(2024, dimensioned_shares=True)
        result = self.qualify(filings=tuple(filings))
        self.assertIn(
            qualification.QualificationIssue.
            RELEVANT_COMMON_CLASS_COVERAGE_NOT_ESTABLISHED,
            result.issues,
        )
        self.assertNotEqual(
            result.relevant_class_coverage.status,
            qualification.ComponentStatus.QUALIFICATION_ESTABLISHED,
        )

    def test_missing_eps_source_correspondence_is_not_inferred(self):
        filings = list(self.filings())
        filings[4] = self.filing(2024, include_eps=False)
        result = self.qualify(filings=tuple(filings))
        self.assertIn(
            qualification.QualificationIssue.MISSING_EPS_SOURCE_CORRESPONDENCE,
            result.issues,
        )
        self.assertIn(
            qualification.QualificationIssue.EPS_APPLICABILITY_NOT_ESTABLISHED,
            result.issues,
        )

    def test_duplicate_matching_rights_scopes_are_ambiguous(self):
        blocks = (
            ("h2", "CLASS A COMMON STOCK"),
            ("p", DISTRIBUTION_SENTENCE),
            ("p", LIQUIDATION_SENTENCE),
            ("h2", "CLASS A COMMON STOCK"),
            ("p", DISTRIBUTION_SENTENCE),
            ("p", LIQUIDATION_SENTENCE),
        )
        result = self.qualify(filings=self.filings(rights_blocks=blocks))
        self.assertEqual(result.status, qualification.QualificationStatus.SOURCE_CONFLICT)
        self.assertIn(
            qualification.QualificationIssue.D4D3A_D4D3B_SOURCE_CONFLICT,
            result.issues,
        )

    def test_duplicate_companyfacts_observation_remains_individually_bound(self):
        rows = companyfacts_rows()
        rows.append(dict(rows[4]))
        result = self.qualify(current=self.current(rows=rows))
        self.assertEqual(
            result.status,
            qualification.QualificationStatus.
            CURRENT_SECURITY_EPS_QUALIFICATION_ESTABLISHED,
        )
        decision = next(item for item in result.eps_applicability_decisions
                        if item.accession == accession(2024))
        self.assertEqual(len(decision.c3_observation_ids), 2)

    def test_equivalent_recapture_preserves_semantics_and_enriches_evidence(self):
        current, parent, filings, sec, nasdaq = (
            self.current(), self.parent(), self.filings(), self.sec(), self.nasdaq())
        baseline = self.qualify_request(
            self.request(current, parent, sec, nasdaq, filings))
        recapture = self.filing(
            2024,
            raw=qualification_submission(2024),
            captured_at="2026-02-22T12:00:00Z",
        )
        enriched_filings = filings + (recapture,)
        enriched = self.qualify_request(
            self.request(current, parent, sec, nasdaq, enriched_filings))
        self.assertEqual(
            enriched.status,
            qualification.QualificationStatus.
            CURRENT_SECURITY_EPS_QUALIFICATION_ESTABLISHED,
        )
        self.assertEqual(baseline.semantic_id, enriched.semantic_id)
        self.assertNotEqual(baseline.evidence_id, enriched.evidence_id)

    def test_boundary_disagreement_is_explicitly_blocked(self):
        request = self.inputs()
        upstream = assess_sec_temporal_common_stock_source_series(
            self.current_archive,
            self.submissions_archive,
            self.filing_archive,
            self.sec_archive,
            self.nasdaq_archive,
            request.temporal_source_series_request,
        )
        altered = replace(
            upstream,
            current_authority_boundary="2026-02-28T12:00:00Z",
        )
        with patch.object(
            qualification,
            "assess_sec_temporal_common_stock_source_series",
            return_value=altered,
        ):
            result = self.qualify_request(request)
        self.assertIn(qualification.QualificationIssue.CURRENT_BOUNDARY_MISMATCH,
                      result.issues)
        self.assertEqual(result.status,
                         qualification.QualificationStatus.QUALIFICATION_BLOCKED)

    def test_static_dependency_and_authority_boundary(self):
        root = Path(__file__).resolve().parents[1]
        module = root / "economic_facts/sec_current_security_eps_qualification.py"
        tree = ast.parse(module.read_text())
        permitted_local = {
            "current_authority", "nasdaq_listed_archive", "sec_archive",
            "sec_class_eps_claims", "sec_current_common_stock_class_bridge",
            "sec_current_registered_listing_bridge", "sec_eps_series",
            "sec_filing_archive", "sec_property4_temporal_boundary",
            "sec_registered_securities", "sec_submissions_archive",
            "sec_temporal_common_stock_source_series", "sec_ticker_exchange_archive",
        }
        permitted_standard = {"dataclasses", "decimal", "enum", "re"}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                self.assertTrue(
                    (node.level == 1 and node.module in permitted_local)
                    or (node.level == 0 and node.module in permitted_standard),
                    node.module,
                )
            elif isinstance(node, ast.Import):
                self.assertTrue(all(item.name in permitted_standard for item in node.names))
            elif isinstance(node, ast.Call):
                name = (node.func.id if isinstance(node.func, ast.Name) else
                        node.func.attr if isinstance(node.func, ast.Attribute) else "")
                self.assertNotIn(name, {
                    "open", "write", "write_text", "write_bytes", "now", "today",
                    "getenv", "system", "run", "eval", "exec", "__import__",
                })
        source = module.read_text()
        for forbidden in (
            "QualifiedFacts", "calculate_expected_return", "security_identity",
            "share_basis", "reporting_subject", "MODEL_RULES_VERSION", "src.",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
