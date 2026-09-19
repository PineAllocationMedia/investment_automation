"""Fictional controlled archives only; LIVE fixtures are not real observations."""
import ast
from dataclasses import FrozenInstanceError, asdict, replace
from datetime import datetime, timezone
from decimal import Decimal, localcontext
import inspect
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from economic_facts import current_authority as c
from economic_facts import sec_current_evidence as a
from economic_facts import source_authority as s
from economic_facts.sec_archive import SecArchive, ArchiveError
from economic_facts.sec_eps_series import (AdmissionBlocker, CaptureAuthority, ResolutionMode,
    ResolutionStatus, ResolutionReason, resolve_annual_diluted_eps)
from tests.sec_eps_series_fixtures import annual_rows, capture, request
from tests.sec_filing_fixtures import CIK, T2, raw, source


class SecCurrentEvidenceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.archive = SecArchive(self.root / "archive")

    def assess(self, rows=None, *, live=True, **changes):
        receipt = capture(self.archive, rows, live=live, **changes)
        return a.assess_sec_current_evidence(self.archive, request(receipt))

    def test_live_evidence_established_not_economic_admission(self):
        result = self.assess()
        neutral = result.current_authority
        self.assertIs(neutral.status, c.AssessmentStatus.EVIDENCE_ESTABLISHED)
        self.assertEqual(len(neutral.established_claims), 3)
        self.assertEqual(len(neutral.unresolved_obligations), 4)
        self.assertEqual(len(result.resolution.series.downstream_admission_blockers), 6)
        self.assertNotIn(AdmissionBlocker.OFFLINE_CAPTURE_NOT_AUTHENTICATED,
                         result.resolution.series.downstream_admission_blockers)
        self.assertNotIn("ADMITTED", json.dumps(s._project(result)))

    def test_offline_identical_values_never_acquire_live_authority(self):
        offline, live = self.assess(live=False), self.assess()
        self.assertEqual(offline.resolution.series.semantic_hash, live.resolution.series.semantic_hash)
        neutral = offline.current_authority
        self.assertIs(neutral.status, c.AssessmentStatus.UNAVAILABLE)
        self.assertEqual(neutral.reasons, (c.AuthorityReason.UNSUPPORTED_ACQUISITION_AUTHORITY,))
        self.assertEqual(neutral.established_claims, ())
        self.assertIsNone(neutral.current_authority_boundary)
        self.assertIsNone(neutral.observed_available_by)
        self.assertEqual(len(neutral.upstream_blockers), 7)
        self.assertIsNotNone(offline.resolution.series)

    def test_unchanged_resolver_called_once_and_original_result_retained(self):
        receipt = capture(self.archive, live=True)
        req = request(receipt)
        replay = resolve_annual_diluted_eps(self.archive, req)
        with patch.object(a, "resolve_annual_diluted_eps", return_value=replay) as resolver:
            result = a.assess_sec_current_evidence(self.archive, req)
        resolver.assert_called_once_with(self.archive, req)
        self.assertIs(result.resolution, replay)
        self.assertIs(result.request, req)

    def test_stored_receipt_and_object_actually_read(self):
        receipt = capture(self.archive, live=True)
        original = SecArchive.read_object
        read = []
        def observe(archive, stored):
            read.append(stored.receipt_id)
            return original(archive, stored)
        with patch.object(SecArchive, "read_object", observe):
            result = a.assess_sec_current_evidence(self.archive, request(receipt))
        self.assertGreaterEqual(len(read), 1)
        self.assertEqual(set(read), {receipt.receipt_id})
        self.assertEqual(result.receipt, receipt)

    def test_missing_receipt_is_integrity_error(self):
        receipt = capture(self.archive, live=True)
        with self.assertRaises(c.CurrentAuthorityError) as caught:
            a.assess_sec_current_evidence(self.archive, request(receipt, receipt_id="f" * 64))
        self.assertIs(caught.exception.reason, c.AuthorityErrorReason.ARCHIVE_INTEGRITY_FAILURE)

    def test_object_corruption_is_integrity_error(self):
        receipt = capture(self.archive, live=True)
        path = self.archive.root / "objects" / receipt.content_sha256
        path.chmod(0o600)
        path.write_bytes(b"corrupt")
        with self.assertRaises(c.CurrentAuthorityError) as caught:
            a.assess_sec_current_evidence(self.archive, request(receipt))
        self.assertIs(caught.exception.reason, c.AuthorityErrorReason.ARCHIVE_INTEGRITY_FAILURE)

    def test_receipt_corruption_is_integrity_error(self):
        receipt = capture(self.archive, live=True)
        path = self.archive.root / "receipts" / (receipt.receipt_id + ".json")
        value = json.loads(path.read_bytes())
        value["captured_at"] = "1999-01-01T00:00:00Z"
        path.chmod(0o600)
        path.write_text(json.dumps(value))
        with self.assertRaises(c.CurrentAuthorityError) as caught:
            a.assess_sec_current_evidence(self.archive, request(receipt))
        self.assertIs(caught.exception.reason, c.AuthorityErrorReason.ARCHIVE_INTEGRITY_FAILURE)

    def test_unknown_acquisition_receipt_is_not_missing_evidence(self):
        receipt = capture(self.archive, live=True)
        path = self.archive.root / "receipts" / (receipt.receipt_id + ".json")
        value = json.loads(path.read_bytes())
        value["acquisition_contract_version"] = "REAL"
        path.chmod(0o600)
        path.write_text(json.dumps(value))
        with self.assertRaises(c.CurrentAuthorityError) as caught:
            a.assess_sec_current_evidence(self.archive, request(receipt))
        self.assertIs(caught.exception.reason, c.AuthorityErrorReason.ARCHIVE_INTEGRITY_FAILURE)

    def test_wrong_cik_is_route_error(self):
        receipt = capture(self.archive, live=True)
        with self.assertRaises(c.CurrentAuthorityError) as caught:
            a.assess_sec_current_evidence(self.archive, request(receipt, cik="0000000001"))
        self.assertIs(caught.exception.reason, c.AuthorityErrorReason.ROUTE_CONTRACT_MISMATCH)

    def test_malformed_source_is_structure_error(self):
        receipt = self.archive._capture_live(b"not json", cik=CIK, captured_at=T2)
        with self.assertRaises(c.CurrentAuthorityError) as caught:
            a.assess_sec_current_evidence(self.archive, request(receipt))
        self.assertIs(caught.exception.reason, c.AuthorityErrorReason.SOURCE_STRUCTURE_FAILURE)

    def test_resolution_unavailable_retains_full_failure_diagnostics(self):
        result = self.assess(annual_rows()[:-1])
        self.assertIs(result.resolution.status, ResolutionStatus.UNAVAILABLE)
        self.assertIsNone(result.resolution.series)
        self.assertTrue(result.resolution.period_decisions)
        self.assertTrue(result.resolution.reasons)
        self.assertIs(result.current_authority.status, c.AssessmentStatus.UNAVAILABLE)
        self.assertEqual(result.current_authority.reasons, (c.AuthorityReason.RESOLUTION_UNAVAILABLE,))
        self.assertEqual(result.current_authority.established_claims, ())
        self.assertEqual(result.current_authority.upstream_blockers,
                         tuple(b.value for b in result.resolution.source_authority.limitations))

    def test_offline_unresolved_preserves_both_failure_reasons(self):
        result = self.assess([], live=False)
        self.assertEqual(set(result.current_authority.reasons), {
            c.AuthorityReason.RESOLUTION_UNAVAILABLE, c.AuthorityReason.UNSUPPORTED_ACQUISITION_AUTHORITY})

    def test_boundary_equals_verified_capture_exactly(self):
        result = self.assess(captured_at="2026-03-01T12:00:00.000001Z")
        neutral = result.current_authority
        self.assertEqual(neutral.current_authority_boundary, result.receipt.captured_at)
        self.assertEqual(neutral.observed_available_by, result.resolution.series.authority_as_of)
        self.assertIs(neutral.publication, s.PublicationSemantics.UNKNOWN)

    def test_internal_boundary_mismatch_is_contract_error(self):
        receipt = capture(self.archive, live=True)
        req = request(receipt)
        result = resolve_annual_diluted_eps(self.archive, req)
        for changed in (replace(result, series=replace(result.series, authority_as_of="2026-03-01T12:00:00.000001Z")),
                        replace(result, source_authority=replace(result.source_authority, captured_at="2026-03-02T12:00:00Z"))):
            with self.subTest(result=changed.source_authority.captured_at), \
                 patch.object(a, "resolve_annual_diluted_eps", return_value=changed), \
                 self.assertRaises(c.CurrentAuthorityError) as caught:
                a.assess_sec_current_evidence(self.archive, req)
            self.assertIs(caught.exception.reason, c.AuthorityErrorReason.AUTHORITY_BOUNDARY_MISMATCH)

    def test_historical_mode_no_archive_reads_or_partial_authority(self):
        receipt = capture(self.archive, live=True)
        with patch.object(SecArchive, "read_receipt", side_effect=AssertionError("archive read")):
            result = a.assess_sec_current_evidence(self.archive, request(receipt, mode=ResolutionMode.HISTORICAL_AS_OF))
        self.assertIsNone(result.receipt)
        self.assertIsNone(result.current_authority.current_authority_boundary)
        self.assertEqual(result.current_authority.established_claims, ())
        self.assertEqual(result.current_authority.reasons, (c.AuthorityReason.HISTORICAL_MODE_UNSUPPORTED,))

    def test_filing_dates_never_become_publication(self):
        rows = [dict(row, filed="2026-02-01") for row in annual_rows()]
        result = self.assess(rows)
        self.assertIs(result.current_authority.publication, s.PublicationSemantics.UNKNOWN)
        self.assertEqual(result.current_authority.observed_available_by, T2)
        self.assertTrue(all(v.filed == "2026-02-01" for p in result.resolution.series.periods for v in p.filing_versions))

    def test_real_c2_code_with_fake_transport_headers_never_become_publication(self):
        # Real acquisition CODE, fictional transport/body/clock. No live provider.
        from economic_facts import sec_acquisition as acquisition
        from tests.test_sec_acquisition import Response, FakeClock, USER_AGENT
        clock = FakeClock()
        response = Response(body=raw(source(annual_rows())), headers={
            "Content-Type": "application/json", "Date": "Fri, 01 Jan 1999 00:00:00 GMT",
            "Last-Modified": "Fri, 01 Jan 1999 00:00:00 GMT"})
        with patch.object(acquisition, "_open_response", return_value=response), \
             patch.object(acquisition, "_state_directory", return_value=self.root / "gate"), \
             patch.object(acquisition, "_utc_now", return_value=datetime(2026, 3, 1, 12, tzinfo=timezone.utc)), \
             patch.object(acquisition.time, "sleep", clock.sleep), \
             patch.object(acquisition.time, "monotonic", clock.monotonic), \
             patch.dict(os.environ, {acquisition.USER_AGENT_ENV: USER_AGENT}), \
             patch.object(socket, "socket", side_effect=AssertionError("network")):
            capture_result = acquisition.acquire_companyfacts(cik=CIK, archive_root=self.archive.root)
            receipt = self.archive.read_receipt(capture_result.archive_receipt_id)
            result = a.assess_sec_current_evidence(self.archive, request(receipt))
        self.assertIs(result.current_authority.publication, s.PublicationSemantics.UNKNOWN)
        self.assertEqual(result.current_authority.observed_available_by, T2)
        self.assertNotIn("1999", json.dumps(s._project(result.current_authority)))

    def test_five_decimals_and_complete_cross_form_lineage_preserved(self):
        rows = annual_rows()
        for form in ("8-K", "10-Q", "10-Q/A"):
            for row in annual_rows():
                rows.append(dict(row, form=form, accn=f"0000000000-25-{100 + len(rows):06d}"))
        rows.append(dict(rows[0]))
        receipt = capture(self.archive, rows, live=True)
        replay = resolve_annual_diluted_eps(self.archive, request(receipt))
        with patch.object(a, "resolve_annual_diluted_eps", return_value=replay):
            result = a.assess_sec_current_evidence(self.archive, request(receipt))
        self.assertIs(result.resolution, replay)
        for before, after in zip(replay.series.periods, result.resolution.series.periods):
            self.assertIs(before.value, after.value)
            self.assertIs(type(after.value), Decimal)
            self.assertEqual(len(after.version_ids), 4)
            self.assertLess(len(after.supporting_observation_ids), sum(len(v.observation_ids) for v in after.filing_versions))
        self.assertEqual(result.current_authority.upstream_semantic_hash, replay.series.semantic_hash)
        self.assertEqual(result.current_authority.upstream_evidence_hash, replay.series.evidence_hash)

    def test_precision_sign_and_decimal_context_preserved(self):
        for value in ("6.123456789012345678901234567890123456789", "-6", "0", "-0.00"):
            content = raw(source(annual_rows())).replace(b'"val":6', b'"val":' + value.encode())
            receipt = self.archive._capture_live(content, cik=CIK, captured_at=T2)
            with localcontext() as context:
                context.prec = 2
                for signal in context.traps:
                    context.traps[signal] = True
                result = a.assess_sec_current_evidence(self.archive, request(receipt))
            self.assertEqual(result.resolution.series.periods[-1].value, Decimal(value))
            self.assertEqual(result, a.assess_sec_current_evidence(self.archive, request(receipt)))
            self.assertEqual(next(o.value for o in result.resolution.extraction.observations
                                  if o.end == "2024-12-31").as_tuple(), Decimal(value).as_tuple())

    def test_excluded_observations_and_conflicts_not_hidden(self):
        rows = annual_rows() + [dict(annual_rows()[0], start="2020-01-01", end="2020-03-31", form="10-Q")]
        result = self.assess(rows)
        self.assertTrue(result.resolution.observation_exclusions)
        conflict = self.assess(annual_rows() + [dict(annual_rows()[0], val=999)])
        self.assertIsNone(conflict.resolution.series)
        self.assertIn(ResolutionReason.UNRESOLVED_VALUE_CONFLICT, conflict.resolution.reasons)

    def test_blockers_preserved_exactly_live_and_offline(self):
        for live in (True, False):
            result = self.assess(live=live)
            self.assertEqual(result.current_authority.upstream_blockers,
                             tuple(b.value for b in result.resolution.series.downstream_admission_blockers))
            for blocker in (AdmissionBlocker.UPSTREAM_EVIDENCE_ONLY, AdmissionBlocker.SNAPSHOT_COVERAGE_ONLY,
                            AdmissionBlocker.PUBLICATION_AND_AVAILABILITY_NOT_ESTABLISHED):
                self.assertIn(blocker, result.resolution.series.downstream_admission_blockers)

    def test_public_signature_no_extra_authority_input(self):
        self.assertEqual(tuple(inspect.signature(a.assess_sec_current_evidence).parameters), ("archive", "request"))
        receipt = capture(self.archive, live=True)
        for keyword in ("as_of", "boundary", "published_at", "authority", "profile", "callback", "raw",
                        "url", "transport", "clock", "series"):
            with self.subTest(keyword=keyword), self.assertRaises(TypeError):
                a.assess_sec_current_evidence(self.archive, request(receipt), **{keyword: "REAL"})

    def test_fabricated_series_hash_profile_and_reports_cannot_enter(self):
        result = self.assess()
        for value in (result.resolution.series, result.resolution, result.current_authority, result,
                      "a" * 64, "REAL", asdict(result.request), s.get_source_route(s.SEC_COMPANYFACTS_LIVE_CURRENT_V1)):
            with self.subTest(kind=type(value)), self.assertRaises(c.CurrentAuthorityError):
                a.assess_sec_current_evidence(self.archive, value)

    def test_successful_synthetic_c4_c5_c6_cannot_supply_real_claims(self):
        from tests import reporting_subject_fixtures as f
        from economic_facts import reporting_subject as r
        series, identity, basis, witness = f.upstream()
        subject = r.qualify_reporting_subject(series, identity, basis, f.request(series, identity, basis),
                                              f.bundle(witness, f.document(f.snapshot(series))))
        self.assertIs(subject.outcome, r.ComparabilityOutcome.COMPARABLE_WITHIN_SYNTHETIC_SCOPE)
        for value in (identity, basis, subject):
            with self.subTest(kind=type(value)), self.assertRaises(c.CurrentAuthorityError):
                a.assess_sec_current_evidence(self.archive, value)

    def test_invalid_request_and_subclasses_fail_before_archive_read(self):
        receipt = capture(self.archive, live=True)
        req = request(receipt)
        class ForeignArchive(SecArchive):
            pass
        for archive, value in ((ForeignArchive(self.archive.root), req), (self.archive, asdict(req)),
                               (self.archive, replace(req, mode="CURRENT_AS_REPORTED"))):
            with patch.object(SecArchive, "read_receipt", side_effect=AssertionError("read")), \
                 self.assertRaises(c.CurrentAuthorityError):
                a.assess_sec_current_evidence(archive, value)

    def test_route_contract_drift_fails_closed(self):
        receipt = capture(self.archive, live=True)
        with patch.object(a, "EXTRACTION_VERSION", "future"), self.assertRaises(c.CurrentAuthorityError) as caught:
            a.assess_sec_current_evidence(self.archive, request(receipt))
        self.assertIs(caught.exception.reason, c.AuthorityErrorReason.ROUTE_CONTRACT_MISMATCH)

    def test_acquisition_identity_mismatch_rejected(self):
        receipt = capture(self.archive, live=True)
        req = request(receipt)
        result = resolve_annual_diluted_eps(self.archive, req)
        changed = replace(result, source_authority=replace(result.source_authority,
                                                          authority=CaptureAuthority.OFFLINE_SUPPLIED_CAPTURE))
        with patch.object(a, "resolve_annual_diluted_eps", return_value=changed), self.assertRaises(c.CurrentAuthorityError):
            a.assess_sec_current_evidence(self.archive, req)

    def test_live_locator_must_match_exact_canonical_route(self):
        from economic_facts.sec_archive import LIVE_ACQUISITION_CONTRACT_VERSION
        receipt = self.archive._capture(raw(source(annual_rows())), cik=CIK, captured_at=T2,
            source_locator="https://fictional.invalid/supplied", acquisition_contract_version=LIVE_ACQUISITION_CONTRACT_VERSION)
        with self.assertRaises(c.CurrentAuthorityError) as caught:
            a.assess_sec_current_evidence(self.archive, request(receipt))
        self.assertIs(caught.exception.reason, c.AuthorityErrorReason.ROUTE_CONTRACT_MISMATCH)

    def test_offline_canonical_url_does_not_change_route_authority(self):
        from economic_facts.sec_archive import endpoint_for
        receipt = self.archive.capture(raw(source(annual_rows())), cik=CIK, captured_at=T2,
                                       source_locator=endpoint_for(CIK))
        result = a.assess_sec_current_evidence(self.archive, request(receipt))
        self.assertEqual(result.current_authority.established_claims, ())
        self.assertIn(c.AuthorityReason.UNSUPPORTED_ACQUISITION_AUTHORITY, result.current_authority.reasons)

    def test_unstored_self_consistent_receipt_does_not_grant_authority(self):
        receipt = capture(self.archive, live=True)
        detached = replace(receipt, captured_at="2026-03-02T12:00:00Z")
        with self.assertRaises(c.CurrentAuthorityError) as caught:
            a.assess_sec_current_evidence(self.archive, request(detached))
        self.assertIs(caught.exception.reason, c.AuthorityErrorReason.ARCHIVE_INTEGRITY_FAILURE)

    def test_second_read_failure_is_integrity_error(self):
        receipt = capture(self.archive, live=True)
        req = request(receipt)
        result = resolve_annual_diluted_eps(self.archive, req)
        with patch.object(a, "resolve_annual_diluted_eps", return_value=result), \
             patch.object(SecArchive, "read_receipt", side_effect=ArchiveError("fixture")), \
             self.assertRaises(c.CurrentAuthorityError) as caught:
            a.assess_sec_current_evidence(self.archive, req)
        self.assertIs(caught.exception.reason, c.AuthorityErrorReason.ARCHIVE_INTEGRITY_FAILURE)

    def test_programming_errors_not_disguised_as_unavailability(self):
        receipt = capture(self.archive, live=True)
        with patch.object(a, "resolve_annual_diluted_eps", side_effect=RuntimeError("fixture bug")), \
             self.assertRaises(RuntimeError):
            a.assess_sec_current_evidence(self.archive, request(receipt))

    def test_reordered_source_same_semantics_different_evidence(self):
        first = self.assess()
        second = self.assess(list(reversed(annual_rows())))
        self.assertEqual(first.semantic_hash, second.semantic_hash)
        self.assertEqual(first.current_authority.semantic_hash, second.current_authority.semantic_hash)
        self.assertNotEqual(first.evidence_hash, second.evidence_hash)

    def test_reformatted_bytes_change_evidence_only(self):
        first = self.assess()
        body = json.dumps(source(annual_rows()), indent=2).encode()
        receipt = self.archive._capture_live(body, cik=CIK, captured_at=T2)
        second = a.assess_sec_current_evidence(self.archive, request(receipt))
        self.assertEqual(first.semantic_hash, second.semantic_hash)
        self.assertNotEqual(first.evidence_hash, second.evidence_hash)

    def test_changed_values_change_semantics(self):
        first = self.assess()
        rows = annual_rows()
        rows[-1]["val"] = 77
        self.assertNotEqual(first.semantic_hash, self.assess(rows).semantic_hash)

    def test_recapture_does_not_extend_existing_assessment(self):
        first = self.assess()
        later = self.assess(captured_at="2026-03-01T12:00:00.000001Z")
        self.assertEqual(first.resolution.series.semantic_hash, later.resolution.series.semantic_hash)
        self.assertNotEqual(first.semantic_hash, later.semantic_hash)
        self.assertEqual(first, a.assess_sec_current_evidence(self.archive, first.request))

    def test_different_unavailable_reasons_change_wrapper_semantics(self):
        missing = self.assess([])
        conflict = self.assess(annual_rows() + [dict(annual_rows()[0], val=999)])
        self.assertNotEqual(missing.semantic_hash, conflict.semantic_hash)

    def test_archive_unchanged_and_no_network_no_writes(self):
        receipt = capture(self.archive, live=True)
        def inventory():
            return {str(p.relative_to(self.archive.root)): (p.read_bytes(), p.stat().st_mode, p.stat().st_mtime_ns)
                    for p in self.archive.root.rglob("*") if p.is_file()}
        before = inventory()
        with patch.object(socket, "socket", side_effect=AssertionError("network")), \
             patch.object(SecArchive, "_publish", side_effect=AssertionError("write")):
            a.assess_sec_current_evidence(self.archive, request(receipt))
        self.assertEqual(before, inventory())

    def test_no_provider_model_or_synthetic_imports_and_no_float_calls(self):
        standard = {"dataclasses", "datetime", "decimal", "enum", "hashlib", "json", "re"}
        for module, allowed in ((s, set()), (c, {"source_authority"}),
                (a, {"source_authority", "current_authority", "sec_archive", "sec_diluted_eps", "sec_eps_series"})):
            tree = ast.parse(inspect.getsource(module))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    self.assertTrue(all(alias.name in standard for alias in node.names))
                if isinstance(node, ast.ImportFrom):
                    self.assertIn(node.module, allowed if node.level else standard)
                if isinstance(node, ast.Call):
                    name = node.func.id if isinstance(node.func, ast.Name) else node.func.attr if isinstance(node.func, ast.Attribute) else ""
                    self.assertNotIn(name, {"float", "normalize", "quantize", "open", "now", "today", "getenv",
                                           "write_text", "write_bytes", "capture", "_capture_live", "run", "eval", "exec"})

    def test_fresh_process_determinism_and_no_host_path_identity(self):
        receipt = capture(self.archive, live=True)
        code = '''
import json, sys
from economic_facts.sec_archive import SecArchive
from economic_facts.sec_eps_series import SeriesResolutionRequest, ResolutionMode, PeriodPolicy, SERIES_CONTRACT_VERSION
from economic_facts.sec_current_evidence import assess_sec_current_evidence
from economic_facts.source_authority import _project
archive=SecArchive(sys.argv[1])
request=SeriesResolutionRequest(SERIES_CONTRACT_VERSION,ResolutionMode.CURRENT_AS_REPORTED,sys.argv[2],
    "0000000000","2024-12-31","USD/shares",PeriodPolicy.FIXED_MONTH_END_365_366)
result=assess_sec_current_evidence(archive,request)
assert not any(k == "src" or k.startswith("src.") or k == "economic_facts.sec_acquisition" for k in sys.modules)
print(json.dumps(_project(result),sort_keys=True))
'''
        values = []
        for seed in ("1", "42"):
            result = subprocess.run([sys.executable, "-B", "-c", code, str(self.archive.root), receipt.receipt_id],
                env={**os.environ, "PYTHONHASHSEED": seed}, capture_output=True, text=True, check=True, timeout=20)
            values.append(result.stdout)
        self.assertEqual(*values)
        self.assertNotIn(str(self.archive.root), values[0])
        other = SecArchive(self.root / "other")
        other_receipt = capture(other, live=True)
        self.assertEqual(a.assess_sec_current_evidence(self.archive, request(receipt)),
                         a.assess_sec_current_evidence(other, request(other_receipt)))

    def test_output_frozen(self):
        result = self.assess()
        with self.assertRaises(FrozenInstanceError):
            result.resolution = None
        with self.assertRaises(FrozenInstanceError):
            result.current_authority.observed_available_by = T2


if __name__ == "__main__":
    unittest.main()
