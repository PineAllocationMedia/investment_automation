"""PR4D4D3B temporal common-stock source correspondence series tests."""
import ast
from dataclasses import FrozenInstanceError, fields, replace
import inspect
import os
from pathlib import Path
import socket
import tempfile
import time
import unittest
from unittest.mock import patch

from economic_facts import sec_current_common_stock_class_bridge as d4d3a
from economic_facts import sec_temporal_common_stock_source_series as series
from economic_facts.nasdaq_listed_archive import NasdaqListedArchive
from economic_facts.sec_archive import SecArchive
from economic_facts.sec_current_registered_listing_bridge import (
    SecCurrentRegisteredListingBridgeRequest,
)
from economic_facts.sec_filing_archive import SecFilingArchive
from economic_facts.sec_property4_temporal_boundary import (
    SecProperty4TemporalBoundaryRequest,
    SourceAcceptanceBoundaryEvidence,
    SourceEventBoundaryRelation,
)
from economic_facts.sec_section12_rights_source_claims import (
    SecSection12RightsSourceClaimsRequest,
    SecSection12RightsSourceTopic,
)
from economic_facts.sec_submissions_archive import SecSubmissionsArchive
from economic_facts.sec_ticker_exchange_archive import SecTickerExchangeArchive
from tests.sec_current_registered_listing_bridge_fixtures import (
    NASDAQ_CAPTURE,
    SEC_CAPTURE,
    nasdaq_snapshot,
    sec_snapshot,
)
from tests.sec_property4_temporal_boundary_fixtures import (
    BOUNDARY_T1,
    capture_current,
    current_request,
)
from tests.sec_property4_temporal_fixtures import CIK, FILENAME
from tests.sec_submissions_fixtures import root as submissions_root, row
from tests.sec_temporal_common_stock_source_series_fixtures import (
    ACCEPTANCE_1,
    ACCEPTANCE_2,
    ACCESSION_1,
    ACCESSION_2,
    CAPTURE_1,
    CAPTURE_2,
    temporal_class_submission,
)


def source_row(number, acceptance, **changes):
    return row(number, **{**{
        "accessionNumber": f"0000000001-26-{number:06d}",
        "acceptanceDateTime": acceptance,
        "primaryDocument": FILENAME,
    }, **changes})


class TemporalCommonStockSourceSeriesTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name).resolve()
        self._set_archives(self.base)

    def _set_archives(self, base):
        self.current_archive = SecArchive(base / "current")
        self.submissions_archive = SecSubmissionsArchive(base / "submissions")
        self.filing_archive = SecFilingArchive(base / "filings")
        self.sec_archive = SecTickerExchangeArchive(base / "sec-associations")
        self.nasdaq_archive = NasdaqListedArchive(base / "nasdaq")

    def current(self, *, boundary=BOUNDARY_T1, live=True):
        return current_request(capture_current(
            self.current_archive, boundary=boundary, live=live))

    def parent(self, *, rows=None):
        if rows is None:
            rows = (
                source_row(1, ACCEPTANCE_1),
                source_row(2, ACCEPTANCE_2),
            )
        return self.submissions_archive._capture_live(
            submissions_root(list(rows), cik=CIK),
            cik=CIK,
            captured_at="2026-02-20T12:00:00Z",
        )

    def filing(self, *, accession=ACCESSION_1, captured_at=CAPTURE_1,
               raw=None, **changes):
        payload = (temporal_class_submission(accession=accession, **changes)
                   if raw is None else raw)
        return self.filing_archive._capture_live(
            payload, cik=CIK, accession=accession, captured_at=captured_at)

    def sec(self):
        return self.sec_archive._capture_live(
            sec_snapshot(), captured_at=SEC_CAPTURE)

    def nasdaq(self):
        return self.nasdaq_archive._capture_live(
            nasdaq_snapshot(), captured_at=NASDAQ_CAPTURE)

    def request(self, current, parent, sec, nasdaq, filings, *, rights=None):
        temporal = SecProperty4TemporalBoundaryRequest(
            current,
            parent.receipt_id,
            (),
            tuple(receipt.receipt_id for receipt in filings),
        )
        current_bridge = SecCurrentRegisteredListingBridgeRequest(
            temporal, sec.receipt_id, nasdaq.receipt_id)
        rights = (tuple(SecSection12RightsSourceClaimsRequest(receipt.receipt_id)
                        for receipt in filings)
                  if rights is None else rights)
        return series.SecTemporalCommonStockSourceSeriesRequest(
            current_bridge, rights)

    def inputs(self, *, filings=None, rows=None, rights=None, live=True):
        if filings is None:
            filings = (
                self.filing(),
                self.filing(accession=ACCESSION_2, captured_at=CAPTURE_2),
            )
        return self.request(
            self.current(live=live), self.parent(rows=rows), self.sec(),
            self.nasdaq(), filings, rights=rights)

    def assess_request(self, request):
        return series.assess_sec_temporal_common_stock_source_series(
            self.current_archive,
            self.submissions_archive,
            self.filing_archive,
            self.sec_archive,
            self.nasdaq_archive,
            request,
        )

    def assess(self, **kwargs):
        return self.assess_request(self.inputs(**kwargs))

    def class_assessments(self, request):
        return tuple(d4d3a.assess_sec_current_common_stock_class_bridge(
            self.current_archive,
            self.submissions_archive,
            self.filing_archive,
            self.sec_archive,
            self.nasdaq_archive,
            d4d3a.SecCurrentCommonStockClassBridgeRequest(
                request.registered_listing_bridge_request, rights),
        ) for rights in sorted(request.rights_claims_requests,
                               key=lambda item: item.filing_receipt_id))

    def test_exact_public_api_request_shape_bounds_uniqueness_and_frozen_records(self):
        self.assertEqual(tuple(inspect.signature(
            series.assess_sec_temporal_common_stock_source_series).parameters), (
                "current_archive", "submissions_archive", "filing_archive",
                "ticker_exchange_archive", "nasdaq_listed_archive", "request"))
        self.assertEqual(tuple(field.name for field in fields(
            series.SecTemporalCommonStockSourceSeriesRequest)), (
                "registered_listing_bridge_request", "rights_claims_requests"))
        request = self.inputs()
        maximum = tuple(SecSection12RightsSourceClaimsRequest(f"{index:064x}")
                        for index in range(1, 33))
        accepted = series.SecTemporalCommonStockSourceSeriesRequest(
            request.registered_listing_bridge_request, maximum)
        self.assertEqual(len(accepted.rights_claims_requests), 32)
        too_many = maximum + (SecSection12RightsSourceClaimsRequest(f"{33:064x}"),)
        for invalid in (list(request.rights_claims_requests),
                        request.rights_claims_requests[:1],
                        too_many, (request.rights_claims_requests[0],) * 2):
            with self.subTest(length=len(invalid)), self.assertRaises(
                    series.SecTemporalCommonStockSourceSeriesRequestError):
                series.SecTemporalCommonStockSourceSeriesRequest(
                    request.registered_listing_bridge_request, invalid)
        for keyword in ("cik", "ticker", "accession", "title", "class_id",
                        "as_of", "continuity", "latest", "candidate", "clock"):
            with self.subTest(keyword=keyword), self.assertRaises(TypeError):
                series.SecTemporalCommonStockSourceSeriesRequest(
                    request.registered_listing_bridge_request,
                    request.rights_claims_requests,
                    **{keyword: "forbidden"},
                )
        result = self.assess_request(request)
        with self.assertRaises(FrozenInstanceError):
            result.status = "changed"
        with self.assertRaises(FrozenInstanceError):
            result.observations[0].accession = "changed"

    def test_each_public_argument_requires_its_exact_type(self):
        request = self.inputs()
        arguments = [
            self.current_archive, self.submissions_archive, self.filing_archive,
            self.sec_archive, self.nasdaq_archive, request,
        ]
        for index in range(len(arguments)):
            wrong = list(arguments)
            wrong[index] = object()
            with self.subTest(index=index), self.assertRaises(
                    series.SecTemporalCommonStockSourceSeriesRequestError):
                series.assess_sec_temporal_common_stock_source_series(*wrong)

    def test_positive_series_freshly_replays_common_d4c2_and_every_d4d3a(self):
        request = self.inputs()
        with patch.object(
                series, "assess_sec_current_registered_listing_bridge",
                wraps=series.assess_sec_current_registered_listing_bridge) as d4c2, \
             patch.object(
                series, "assess_sec_current_common_stock_class_bridge",
                wraps=series.assess_sec_current_common_stock_class_bridge) as bridges:
            result = self.assess_request(request)
        self.assertEqual((d4c2.call_count, bridges.call_count), (1, 2))
        self.assertEqual(result.status,
            series.TemporalCommonStockSourceSeriesStatus.
            CAPTURED_TEMPORAL_COMMON_STOCK_SOURCE_SERIES)
        self.assertEqual(result.current_authority_boundary, BOUNDARY_T1)
        self.assertEqual(result.distinct_accession_count, 2)
        self.assertEqual(tuple(item.accession for item in result.observations),
                         (ACCESSION_1, ACCESSION_2))
        self.assertEqual(tuple(item.source_acceptance_timestamp
                               for item in result.observations),
                         (ACCEPTANCE_1, ACCEPTANCE_2))
        for observation in result.observations:
            self.assertEqual((observation.source_cik, observation.source_symbol),
                             (CIK, "FICT"))
            self.assertEqual(observation.canonical_source_class_label,
                             "CLASS A COMMON STOCK")
            self.assertEqual(observation.exact_d3a_titles,
                             ("Class A Common Stock, $0.01 par value",))
            self.assertTrue(observation.passage_semantic_ids)
            self.assertEqual(observation.source_topics, (
                SecSection12RightsSourceTopic.DIVIDEND,
                SecSection12RightsSourceTopic.VOTING,
            ))

    def test_caller_permutation_does_not_change_output_or_identities(self):
        request = self.inputs()
        reverse = replace(request, rights_claims_requests=tuple(
            reversed(request.rights_claims_requests)))
        first = self.assess_request(request)
        second = self.assess_request(reverse)
        self.assertEqual((first.semantic_id, first.evidence_id),
                         (second.semantic_id, second.evidence_id))
        self.assertEqual(tuple(item.semantic_id for item in first.observations),
                         tuple(item.semantic_id for item in second.observations))

    def test_acceptance_timestamp_not_receipt_capture_orders_observations(self):
        first = self.filing(captured_at="2026-02-12T12:00:00Z")
        second = self.filing(accession=ACCESSION_2,
                             captured_at="2026-02-11T12:00:00Z")
        rows = (
            source_row(1, "2026-02-10T15:30:00.000Z"),
            source_row(2, "2026-02-09T15:30:00.000Z"),
        )
        result = self.assess(filings=(first, second), rows=rows)
        self.assertEqual(tuple(item.accession for item in result.observations),
                         (ACCESSION_2, ACCESSION_1))
        self.assertFalse(any("publication" in field.name.lower()
                             or "availability" in field.name.lower()
                             or "effective" in field.name.lower()
                             for field in fields(series.TemporalCommonStockSourceObservation)))

    def test_accession_tie_breaks_equal_acceptance_timestamps(self):
        rows = (source_row(2, ACCEPTANCE_1), source_row(1, ACCEPTANCE_1))
        result = self.assess(rows=rows)
        self.assertEqual(tuple(item.accession for item in result.observations),
                         (ACCESSION_1, ACCESSION_2))

    def test_same_accession_equivalent_recaptures_make_one_insufficient_observation(self):
        raw = temporal_class_submission()
        first = self.filing(raw=raw, captured_at=CAPTURE_1)
        second = self.filing(raw=raw, captured_at="2026-01-12T12:00:00Z")
        result = self.assess(
            filings=(first, second), rows=(source_row(1, ACCEPTANCE_1),))
        self.assertEqual(result.status,
            series.TemporalCommonStockSourceSeriesStatus.
            INSUFFICIENT_TEMPORAL_OBSERVATIONS)
        self.assertEqual(result.distinct_accession_count, 1)
        observation = result.observations[0]
        self.assertEqual(observation.filing_receipt_ids,
                         tuple(sorted((first.receipt_id, second.receipt_id))))
        self.assertEqual(len(observation.d4d3a_candidate_semantic_id), 64)
        self.assertEqual(len(observation.d4d3a_candidate_evidence_ids), 2)

    def test_equivalent_recapture_preserves_series_semantics_and_enriches_evidence(self):
        raw = temporal_class_submission()
        first = self.filing(raw=raw)
        recapture = self.filing(raw=raw, captured_at="2026-01-12T12:00:00Z")
        second = self.filing(accession=ACCESSION_2, captured_at=CAPTURE_2)
        common = self.inputs(filings=(first, second))
        richer = self.inputs(filings=(first, recapture, second))
        base_result = self.assess_request(common)
        richer_result = self.assess_request(richer)
        self.assertEqual(base_result.semantic_id, richer_result.semantic_id)
        self.assertNotEqual(base_result.evidence_id, richer_result.evidence_id)
        self.assertEqual(base_result.observations[0].semantic_id,
                         richer_result.observations[0].semantic_id)
        self.assertNotEqual(base_result.observations[0].evidence_id,
                            richer_result.observations[0].evidence_id)

    def test_source_stability_and_all_closed_variation_signals(self):
        first = self.filing()
        second = self.filing(
            accession=ACCESSION_2,
            captured_at=CAPTURE_2,
            title="Class A Common Stock, $0.001 par value",
            rights_blocks=(("h2", "Class A Common Stock"),
                           ("p", "Holders have voting rights.")),
        )
        result = self.assess(filings=(first, second))
        self.assertEqual(result.status,
            series.TemporalCommonStockSourceSeriesStatus.
            CAPTURED_TEMPORAL_COMMON_STOCK_SOURCE_SERIES)
        self.assertEqual(set(result.descriptive_signals), {
            series.TemporalCommonStockSourceSignal.CANONICAL_CLASS_LABEL_STABLE,
            series.TemporalCommonStockSourceSignal.EXACT_D3A_TITLE_VARIATION,
            series.TemporalCommonStockSourceSignal.D3A_TITLE_SUFFIX_VARIATION,
            series.TemporalCommonStockSourceSignal.EXACT_D4D2B_HEADING_VARIATION,
            series.TemporalCommonStockSourceSignal.RIGHTS_PASSAGE_SEMANTICS_VARIATION,
            series.TemporalCommonStockSourceSignal.RIGHTS_TOPIC_SET_VARIATION,
        })

    def test_stable_source_does_not_emit_variation_or_continuity_signal(self):
        result = self.assess()
        self.assertEqual(result.descriptive_signals, (
            series.TemporalCommonStockSourceSignal.CANONICAL_CLASS_LABEL_STABLE,))
        values = {item.value for item in series.TemporalCommonStockSourceSignal}
        for forbidden in ("SAME_CLASS", "CLASS_CONTINUITY_ESTABLISHED",
                          "NO_CORPORATE_ACTION", "TICKER_CONTINUITY_PROVED",
                          "RIGHTS_CONTINUITY_PROVED"):
            self.assertNotIn(forbidden, values)

    def test_one_failed_d4d3a_blocks_global_positive_and_unsupported_is_distinct(self):
        unsupported = self.filing(
            accession=ACCESSION_2,
            captured_at=CAPTURE_2,
            title="Class AA Common Stock",
            rights_blocks=(("h2", "CLASS A COMMON STOCK"),
                           ("p", "Voting rights.")),
        )
        result = self.assess(filings=(self.filing(), unsupported))
        self.assertEqual(result.status,
            series.TemporalCommonStockSourceSeriesStatus.UNSUPPORTED_TEMPORAL_PROFILE)
        self.assertIn(
            series.TemporalCommonStockSourceSeriesIssue.D4D3A_UNSUPPORTED_PROFILE,
            result.issues)
        self.assertEqual(result.distinct_accession_count, 1)

    def test_no_matching_class_candidate_is_incomplete_not_conflict(self):
        mismatch = self.filing(
            accession=ACCESSION_2,
            captured_at=CAPTURE_2,
            rights_blocks=(("h2", "COMMON STOCK"), ("p", "Voting rights.")),
        )
        result = self.assess(filings=(self.filing(), mismatch))
        self.assertEqual(result.status,
            series.TemporalCommonStockSourceSeriesStatus.INCOMPLETE_TEMPORAL_SOURCE_SERIES)
        self.assertIn(
            series.TemporalCommonStockSourceSeriesIssue.D4D3A_NO_CLASS_CANDIDATE,
            result.issues)

    def test_common_d4c2_unavailable_and_conflict_fail_closed(self):
        unavailable = self.assess(live=False)
        self.assertEqual(unavailable.status,
            series.TemporalCommonStockSourceSeriesStatus.
            UPSTREAM_CURRENT_BRIDGE_UNAVAILABLE)
        conflict_filing = self.filing(
            accession=ACCESSION_2, captured_at=CAPTURE_2, symbol="OTHER")
        conflict = self.assess(filings=(self.filing(), conflict_filing))
        self.assertEqual(conflict.status,
                         series.TemporalCommonStockSourceSeriesStatus.SOURCE_CONFLICT)
        self.assertIn(
            series.TemporalCommonStockSourceSeriesIssue.D4C2_SOURCE_CONFLICT,
            conflict.issues)

    def test_every_d4d3a_replay_must_match_common_d4c2_semantics_and_evidence(self):
        request = self.inputs()
        assessments = self.class_assessments(request)
        altered_bridge = replace(
            assessments[0].current_listing_bridge,
            contract_version=assessments[0].current_listing_bridge.contract_version + "-x",
        )
        altered = replace(assessments[0], current_listing_bridge=altered_bridge)
        with patch.object(series, "assess_sec_current_common_stock_class_bridge",
                          side_effect=(altered, assessments[1])):
            result = self.assess_request(request)
        self.assertEqual(result.status,
                         series.TemporalCommonStockSourceSeriesStatus.SOURCE_CONFLICT)
        self.assertIn(
            series.TemporalCommonStockSourceSeriesIssue.D4C2_REPLAY_DISAGREEMENT,
            result.issues)

    def _assessment_with_common(self, assessment, common):
        return replace(assessment, current_listing_bridge=common,
                       current_authority_boundary=common.current_authority_boundary)

    def test_missing_and_ambiguous_source_acceptance_chronology_fail_closed(self):
        for index, ambiguous in enumerate((False, True)):
            if index:
                self._set_archives(self.base / "ambiguous")
            request = self.inputs()
            assessments = self.class_assessments(request)
            common = assessments[0].current_listing_bridge
            filing = common.temporal_boundary.filings[0]
            events = (() if not ambiguous else (
                *filing.source_acceptance_events,
                SourceAcceptanceBoundaryEvidence(
                    "f" * 64, "2026-01-11T15:30:00.000Z",
                    SourceEventBoundaryRelation.ON_OR_BEFORE_CURRENT_BOUNDARY),
            ))
            changed_filing = replace(filing, source_acceptance_events=events)
            changed_boundary = replace(
                common.temporal_boundary,
                filings=(changed_filing, *common.temporal_boundary.filings[1:]),
            )
            changed_common = replace(common, temporal_boundary=changed_boundary)
            changed_assessments = tuple(
                self._assessment_with_common(item, changed_common)
                for item in assessments)
            expected = (series.TemporalCommonStockSourceSeriesIssue.
                        AMBIGUOUS_SOURCE_ACCEPTANCE_TIMESTAMP if ambiguous else
                        series.TemporalCommonStockSourceSeriesIssue.
                        MISSING_SOURCE_ACCEPTANCE_TIMESTAMP)
            with patch.object(series, "assess_sec_current_registered_listing_bridge",
                              return_value=changed_common), \
                 patch.object(series, "assess_sec_current_common_stock_class_bridge",
                              side_effect=changed_assessments):
                result = self.assess_request(request)
            with self.subTest(ambiguous=ambiguous):
                self.assertIn(expected, result.issues)
                self.assertEqual(result.status,
                    series.TemporalCommonStockSourceSeriesStatus.SOURCE_CONFLICT
                    if ambiguous else
                    series.TemporalCommonStockSourceSeriesStatus.
                    INCOMPLETE_TEMPORAL_SOURCE_SERIES)

    def test_selected_receipt_must_be_controlled_by_same_boundary(self):
        request = self.inputs()
        assessments = self.class_assessments(request)
        common = assessments[0].current_listing_bridge
        filing = common.temporal_boundary.filings[0]
        changed_filing = replace(filing, controlled_captures_by_boundary=())
        changed_boundary = replace(
            common.temporal_boundary,
            filings=(changed_filing, *common.temporal_boundary.filings[1:]),
        )
        changed_common = replace(common, temporal_boundary=changed_boundary)
        changed_assessments = tuple(
            self._assessment_with_common(item, changed_common) for item in assessments)
        with patch.object(series, "assess_sec_current_registered_listing_bridge",
                          return_value=changed_common), \
             patch.object(series, "assess_sec_current_common_stock_class_bridge",
                          side_effect=changed_assessments):
            result = self.assess_request(request)
        self.assertEqual(result.status,
            series.TemporalCommonStockSourceSeriesStatus.INCOMPLETE_TEMPORAL_SOURCE_SERIES)
        self.assertIn(
            series.TemporalCommonStockSourceSeriesIssue.
            SELECTED_RECEIPT_NOT_CONTROLLED_BY_BOUNDARY,
            result.issues)

    def test_same_accession_competing_semantics_is_conflict_without_winner(self):
        raw = temporal_class_submission()
        first = self.filing(raw=raw)
        second = self.filing(raw=raw, captured_at="2026-01-12T12:00:00Z")
        request = self.inputs(
            filings=(first, second), rows=(source_row(1, ACCEPTANCE_1),))
        assessments = self.class_assessments(request)
        altered_candidate = replace(
            assessments[1].candidates[0],
            exact_d3a_title="Class A Common Stock, $0.02 par value",
            exact_d3a_title_suffix=", $0.02 par value",
        )
        altered = replace(assessments[1], candidates=(altered_candidate,))
        with patch.object(series, "assess_sec_current_common_stock_class_bridge",
                          side_effect=(assessments[0], altered)):
            result = self.assess_request(request)
        self.assertEqual(result.status,
                         series.TemporalCommonStockSourceSeriesStatus.SOURCE_CONFLICT)
        observation = result.observations[0]
        self.assertIsNone(observation.d4d3a_candidate_semantic_id)
        self.assertEqual(len(observation.competing_d4d3a_candidate_semantic_ids), 2)
        self.assertEqual(set(observation.filing_receipt_ids),
                         {first.receipt_id, second.receipt_id})

    def test_identity_determinism_source_sensitivity_and_filesystem_invariance(self):
        first = self.assess()
        second = self.assess_request(self.inputs())
        self.assertEqual((first.semantic_id, first.evidence_id),
                         (second.semantic_id, second.evidence_id))

        self._set_archives(self.base / "changed")
        changed = self.assess(filings=(
            self.filing(),
            self.filing(accession=ACCESSION_2, captured_at=CAPTURE_2,
                        rights_blocks=(("h2", "CLASS A COMMON STOCK"),
                                       ("p", "Voting rights only."))),
        ))
        self.assertNotEqual(first.semantic_id, changed.semantic_id)

        self._set_archives(self.base / "other-root")
        other_path = self.assess()
        self.assertEqual((first.semantic_id, first.evidence_id),
                         (other_path.semantic_id, other_path.evidence_id))

    def test_no_network_writes_clock_directory_scan_or_latest_selection(self):
        request = self.inputs()
        roots = (self.current_archive.root, self.submissions_archive.root,
                 self.filing_archive.root, self.sec_archive.root,
                 self.nasdaq_archive.root)
        before = {(root, path.relative_to(root)): path.read_bytes()
                  for root in roots for path in root.rglob("*") if path.is_file()}
        with patch.object(socket, "create_connection", side_effect=AssertionError("network")), \
             patch.object(os, "listdir", side_effect=AssertionError("scan")), \
             patch.object(os, "scandir", side_effect=AssertionError("scan")), \
             patch.object(time, "time", side_effect=AssertionError("clock")), \
             patch.object(time, "monotonic", side_effect=AssertionError("clock")):
            result = self.assess_request(request)
        after = {(root, path.relative_to(root)): path.read_bytes()
                 for root in roots for path in root.rglob("*") if path.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(result.status,
            series.TemporalCommonStockSourceSeriesStatus.
            CAPTURED_TEMPORAL_COMMON_STOCK_SOURCE_SERIES)

    def test_no_durable_identity_ticker_permanence_or_rights_interpretation_fields(self):
        forbidden = {
            "class_id", "security_id", "economic_class_id", "durable_class_id",
            "continuity_id", "same_class", "ticker_permanent", "rights_effective",
            "no_corporate_action", "rights_continuity", "qualified", "admitted",
            "authority", "votes_per_share", "has_voting_rights", "par_value",
        }
        for record in (
                series.SecTemporalCommonStockSourceSeriesRequest,
                series.TemporalCommonStockSourceObservation,
                series.SecTemporalCommonStockSourceSeriesAssessment):
            self.assertFalse(forbidden & set(record.__dataclass_fields__))


class TemporalCommonStockSourceSeriesDependencyTests(unittest.TestCase):
    def test_exact_dependency_direction_and_no_forbidden_operations(self):
        root = Path(__file__).resolve().parents[1]
        module = root / "economic_facts/sec_temporal_common_stock_source_series.py"
        tree = ast.parse(module.read_text())
        allowed_standard = {"dataclasses", "datetime", "enum"}
        allowed_relative = {
            "nasdaq_listed_archive", "sec_archive",
            "sec_current_common_stock_class_bridge",
            "sec_current_registered_listing_bridge", "sec_filing_archive",
            "sec_property4_temporal_boundary",
            "sec_section12_rights_source_claims", "sec_submissions_archive",
            "sec_ticker_exchange_archive",
        }
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                self.assertTrue(all(alias.name in allowed_standard for alias in node.names))
            elif isinstance(node, ast.ImportFrom):
                imported.add(node.module or "")
                self.assertTrue((node.level == 1 and node.module in allowed_relative)
                                or (node.level == 0 and node.module in allowed_standard))
            elif isinstance(node, ast.Call):
                name = (node.func.id if isinstance(node.func, ast.Name) else
                        node.func.attr if isinstance(node.func, ast.Attribute) else "")
                self.assertNotIn(name, {
                    "open", "float", "eval", "exec", "__import__", "now", "today",
                    "listdir", "scandir", "max",
                })
        joined = " ".join(imported)
        for forbidden in ("security_identity", "source_authority", "expected_return",
                          "src", "pit_comparison", "model", "portfolio", "runtime",
                          "main"):
            self.assertNotIn(forbidden, joined)

    def test_no_reverse_model_runtime_v1_or_authority_consumer(self):
        root = Path(__file__).resolve().parents[1]
        module_name = "sec_temporal_common_stock_source_series"
        for path in [root / "main.py", *(root / "src").rglob("*.py"),
                     *(root / "pit_comparison").rglob("*.py"),
                     *(root / "scripts").rglob("*.py")]:
            self.assertNotIn(module_name, path.read_text(), str(path))

    def test_contract_documents_nonclaims_property4_validation_and_handoff(self):
        text = (Path(__file__).resolve().parents[1] / "docs" / "contracts" / "v2"
                / "expected_return" / "EXPECTED_RETURN_PR4D4D3B.md").read_text()
        for property_name in ("4A", "4B", "4C", "4D", "4E", "4F", "4G", "4H"):
            self.assertIn("| " + property_name + " |", text)
        for phrase in (
                "Obligations 5–7 remain unresolved",
                "Same ticker is not durable identity",
                "Stable observations are not gap-free continuity",
                "This PR has no corporate-action authority",
                "one exact T",
                "complete suite",
                "does not pre-authorize another implementation"):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
