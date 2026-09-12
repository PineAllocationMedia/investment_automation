"""Closed issuer-only resolver mechanics; all source bytes are fictional."""
import ast
from dataclasses import FrozenInstanceError, asdict, replace
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

from economic_facts.sec_archive import SecArchive
from economic_facts.sec_diluted_eps import inspect_archive
from economic_facts.sec_eps_series import (AdmissionBlocker, CaptureAuthority, PeriodPolicy,
    ResolutionMode, ResolutionReason as R, ResolutionStatus as S, SERIES_CONTRACT_VERSION,
    SeriesResolutionError, SeriesResolutionRequest, resolve_annual_diluted_eps)
from tests.sec_eps_series_fixtures import annual_rows, capture, request
from tests.sec_filing_fixtures import CIK, T2, raw, row, source


class SecEPSSeriesTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.archive = SecArchive(Path(temporary.name).resolve() / "archive")

    def resolve(self, rows=None, *, payload=None, **changes):
        receipt = capture(self.archive, rows, payload=payload)
        return resolve_annual_diluted_eps(self.archive, request(receipt, **changes))

    def blocked(self, result, *reasons):
        self.assertIs(result.status, S.UNAVAILABLE)
        self.assertIsNone(result.series)
        self.assertTrue(set(reasons) <= set(result.reasons), result.reasons)
        self.assertEqual(result.reasons, tuple(sorted(set(result.reasons), key=lambda r: r.value)))

    def test_one_version_per_year(self):
        result = self.resolve()
        self.assertIs(result.status, S.RESOLVED_ISSUER_EVIDENCE)
        self.assertEqual(len(result.series.periods), 5)
        self.assertEqual([r.period_end for r in result.series.periods],
                         [f"{y}-12-31" for y in range(2020, 2025)])
        self.assertEqual([r.value for r in result.series.periods], list(map(Decimal, (2, 3, 4, 5, 6))))
        self.assertEqual(result.series.authority_as_of, T2)
        self.assertEqual(result.reasons, ())
        self.assertEqual(len(result.extraction.observations), 5)

    def test_exact_duplicates_preserve_occurrences_one_semantic_version(self):
        rows = annual_rows()
        result = self.resolve(rows + [dict(rows[-1]), dict(rows[-1])])
        final = result.series.periods[-1]
        self.assertEqual(len(final.supporting_observation_ids), 3)
        self.assertEqual(len(final.version_ids), 1)
        self.assertEqual(len(final.filing_versions[0].observation_ids), 3)
        self.assertEqual(len(result.extraction.observations), 7)

    def test_multiple_accessions_and_amendment_same_value(self):
        rows = annual_rows()
        for form in ("10-K", "10-K/A"):
            with self.subTest(form=form):
                changed = dict(rows[-1], form=form, filed="2025-04-01", accn="9999999999-25-000002")
                result = self.resolve(rows + [changed])
                self.assertEqual(len(result.series.periods[-1].version_ids), 2)
                self.assertEqual(len(result.series.periods[-1].supporting_observation_ids), 2)
                self.assertEqual(result.series.periods[-1].value, Decimal(6))

    def test_amendment_or_later_comparative_different_value_does_not_win(self):
        rows = annual_rows()
        for form in ("10-K", "10-K/A"):
            with self.subTest(form=form):
                changed = dict(rows[-1], form=form, val=7, fy=2025, filed="2026-02-01",
                               accn="9999999999-26-000003")
                result = self.resolve(rows + [changed])
                self.blocked(result, R.UNRESOLVED_VALUE_CONFLICT)
                self.assertEqual(len(result.period_decisions[-1].conflicting_observation_ids), 2)

    def test_later_comparative_same_value_retains_filing_year(self):
        rows = annual_rows()
        result = self.resolve(rows + [dict(rows[-1], fy=2025, filed="2026-02-01", accn="9999999999-26-000003")])
        self.assertEqual({v.reported_fy for v in result.series.periods[-1].filing_versions}, {2024, 2025})

    def test_same_accession_conflict_including_metadata_only_difference(self):
        rows = annual_rows()
        for extra in ({}, {"frame": "different-display-frame"}):
            with self.subTest(extra=extra):
                self.blocked(self.resolve(rows + [dict(rows[-1], val=7, **extra)]),
                             R.SAME_ACCESSION_VALUE_CONFLICT, R.UNRESOLVED_VALUE_CONFLICT)

    def test_same_accession_conflicting_filing_identity(self):
        rows = annual_rows()
        for extra in ({"filed": "2025-05-01"}, {"form": "10-K/A"}, {"fy": 2025}):
            with self.subTest(extra=extra):
                self.blocked(self.resolve(rows + [dict(rows[-1], **extra)]), R.INSUFFICIENT_FILING_IDENTITY)

    def test_missing_and_malformed_accession_even_beside_good_row(self):
        rows = annual_rows()
        for value, reason in ((None, R.MISSING_ACCESSION), ("", R.MISSING_ACCESSION),
                              ("1-25-1", R.INVALID_ACCESSION), ("0000000000-25-000001 ", R.INVALID_ACCESSION)):
            with self.subTest(value=value):
                self.blocked(self.resolve(rows + [dict(rows[-1], accn=value)]), reason)

    def test_multiple_units_never_converted(self):
        result = self.resolve(payload=source(units={"USD/shares": annual_rows(), "CAD/shares": [row()]}))
        self.blocked(result, R.UNIT_MISMATCH)
        self.blocked(self.resolve(expected_unit="CAD/shares"), R.UNIT_MISMATCH)

    def test_exact_concept_namespace_only(self):
        for namespace, concept in (("ifrs-full", "EarningsPerShareDiluted"),
                                    ("us-gaap", "EarningsPerShareBasic")):
            payload = source(annual_rows())
            fact = payload['facts']['us-gaap']['EarningsPerShareDiluted']
            payload['facts'] = {namespace: {concept: fact}}
            self.blocked(self.resolve(payload=payload), R.DILUTED_EPS_UNAVAILABLE)

    def test_unknown_context_is_not_automatic_agreement_or_conflict(self):
        rows = annual_rows()
        for value in (6, 7):
            result = self.resolve(rows + [dict(rows[-1], val=value, segment={"axis": "fictional"})])
            self.blocked(result, R.UNRESOLVED_CONTEXT)
            self.assertNotIn(R.UNRESOLVED_VALUE_CONFLICT, result.reasons)
            self.assertNotIn(R.SAME_ACCESSION_VALUE_CONFLICT, result.reasons)

    def test_cross_form_comparable_conflict_and_agreement(self):
        rows = annual_rows()
        for form in ("8-K", "10-Q", "10-Q/A"):
            with self.subTest(form=form):
                other = dict(rows[-1], form=form, fp="Q4", accn="9999999999-25-000002")
                result = self.resolve(rows + [other])
                self.assertIs(result.status, S.RESOLVED_ISSUER_EVIDENCE)
                self.assertEqual(len(result.series.periods[-1].filing_versions), 2)
                self.assertEqual(len(result.period_decisions[-1].excluded_observations), 1)
                self.blocked(self.resolve(rows + [dict(other, val=7)]), R.UNRESOLVED_VALUE_CONFLICT)

    def test_cross_form_unknown_context_does_not_manufacture_conflict(self):
        rows = annual_rows()
        result = self.resolve(rows + [dict(rows[-1], form="8-K", val=7, segment="unknown")])
        self.blocked(result, R.UNRESOLVED_CONTEXT)
        self.assertNotIn(R.UNRESOLVED_VALUE_CONFLICT, result.reasons)

    def test_cross_form_missing_period_identity_fails_closed(self):
        rows = annual_rows()
        other = dict(rows[-1], form='8-K', accn='9999999999-25-000009')
        del other['fp']; del other['fy']
        result = self.resolve(rows + [other])
        self.blocked(result, R.INSUFFICIENT_FILING_IDENTITY)
        self.assertNotIn(R.UNRESOLVED_VALUE_CONFLICT, result.reasons)

    def test_other_forms_cannot_supply_missing_annual_candidate(self):
        rows = annual_rows()
        rows[-1]['form'] = '8-K'
        self.blocked(self.resolve(rows), R.MISSING_ANNUAL_PERIOD, R.MISSING_REQUIRED_LATEST_PERIOD)

    def test_missing_year_no_older_substitution(self):
        rows = annual_rows()
        rows = [r for r in rows if r['end'] != '2022-12-31'] + [row(2019)]
        self.blocked(self.resolve(rows), R.MISSING_ANNUAL_PERIOD, R.NONCONSECUTIVE_PERIODS)

    def test_fewer_than_five_and_missing_latest(self):
        self.blocked(self.resolve(annual_rows()[:-1]), R.FEWER_THAN_FIVE_ANNUAL_PERIODS,
                     R.MISSING_REQUIRED_LATEST_PERIOD)

    def test_leap_years_and_february_month_end(self):
        self.assertEqual([p.inclusive_days for p in self.resolve().series.periods], [366, 365, 365, 365, 366])
        rows = [row(y, start=f'{y-1}-03-01', end=f'{y}-02-{29 if y in (2020, 2024) else 28}',
                    filed=f'{y}-04-01') for y in range(2020, 2025)]
        self.assertIs(self.resolve(rows, latest_required_fiscal_end='2024-02-29').status, S.RESOLVED_ISSUER_EVIDENCE)

    def test_week_calendars_stubs_and_transitions(self):
        for start, end in (('2024-01-01', '2024-12-29'), ('2023-12-25', '2024-12-29'),
                           ('2024-07-01', '2024-12-31'), ('2024-01-01', '2024-06-30')):
            rows = annual_rows()
            rows[-1].update(start=start, end=end)
            with self.subTest(start=start,end=end):
                self.blocked(self.resolve(rows), R.UNSUPPORTED_CALENDAR)

    def test_full_length_shift_and_overlap_are_not_supported(self):
        rows = annual_rows()
        rows[-1].update(start='2023-12-31', end='2024-12-30')
        self.blocked(self.resolve(rows), R.UNSUPPORTED_CALENDAR, R.CALENDAR_TRANSITION_UNRESOLVED)
        rows = annual_rows()
        self.blocked(self.resolve(rows + [row(2023, start='2023-07-01', end='2024-06-30')]),
                     R.CALENDAR_TRANSITION_UNRESOLVED)

    def test_quarter_rows_in_annual_filing_do_not_break_complete_years(self):
        rows = annual_rows()
        rows.append(row(2024, start='2024-10-01', end='2024-12-31'))
        result = self.resolve(rows)
        self.assertIs(result.status, S.RESOLVED_ISSUER_EVIDENCE)
        self.assertEqual(len(result.observation_exclusions), 1)
        self.assertIn(R.NON_ANNUAL_PERIOD, result.observation_exclusions[0].reasons)

    def test_nonpositive_values_preserved_every_required_position(self):
        for year in range(5):
            for value in (0, -2):
                rows = annual_rows(); rows[year]['val'] = value
                result = self.resolve(rows)
                self.assertIs(result.status, S.RESOLVED_ISSUER_EVIDENCE)
                self.assertEqual(result.series.periods[year].value, Decimal(value))
                self.assertIn(AdmissionBlocker.UPSTREAM_EVIDENCE_ONLY, result.series.downstream_admission_blockers)

    def test_missing_or_misleading_fy_and_optional_frame(self):
        for field, value in (('fy', None), ('fy', 2099), ('frame', None), ('frame', 'CY1900')):
            rows = annual_rows()
            for r in rows:
                if value is None: r.pop(field)
                else: r[field] = value
            result = self.resolve(rows)
            self.assertIs(result.status, S.RESOLVED_ISSUER_EVIDENCE)
            if field == 'fy' and value is None:
                self.assertEqual(result.series.periods[0].limitations, ('MISSING_FY',))

    def test_invalid_filed_and_capture_chronology(self):
        rows = annual_rows()
        for value in (None, 'bad', '2024-01-01', '2027-01-01'):
            bad = [*rows[:-1], dict(rows[-1], filed=value)]
            self.blocked(self.resolve(bad), R.INVALID_FILING_CHRONOLOGY)

    def test_later_annual_prevents_older_window_before_any_filters(self):
        for extra in ({'val':0}, {'val':-2}, {'val':None}, {'accn':None}, {'filed':None},
                      {'fp':None}, {'form':None}, {'start':None}, {'segment':'unknown'}):
            with self.subTest(extra=extra):
                later = row(2025, **extra)
                self.blocked(self.resolve(annual_rows()+[later]), R.LATER_ANNUAL_PERIOD_PRESENT)

    def test_later_conflicting_period_no_fallback(self):
        rows = annual_rows()+[row(2025), row(2025, 3, accn='0000000000-26-000009')]
        self.blocked(self.resolve(rows), R.LATER_ANNUAL_PERIOD_PRESENT)
        self.blocked(self.resolve(rows, latest_required_fiscal_end='2025-12-31'), R.UNRESOLVED_VALUE_CONFLICT)

    def test_later_nonpositive_period_resolves_when_required(self):
        for value in (0, -1):
            result = self.resolve(annual_rows()+[row(2025,value)], latest_required_fiscal_end='2025-12-31')
            self.assertEqual(result.series.periods[-1].value, Decimal(value))
            self.assertEqual(len(result.series.periods), 5)

    def test_unlocatable_annual_metadata_cannot_be_discarded(self):
        for missing in ('start', 'end'):
            rows = annual_rows()+[row(2025)]
            rows[-1].pop(missing)
            self.blocked(self.resolve(rows), R.INSUFFICIENT_FILING_IDENTITY)

    def test_row_reordering_semantic_stability_evidence_changes(self):
        rows = annual_rows()+[dict(annual_rows()[-1],accn='9999999999-25-000009')]
        first, second = self.resolve(rows), self.resolve(list(reversed(rows)))
        self.assertEqual(first.series.semantic_hash, second.series.semantic_hash)
        self.assertNotEqual(first.series.evidence_hash, second.series.evidence_hash)
        self.assertEqual([p.value for p in first.series.periods], [p.value for p in second.series.periods])
        def representative_semantic(result):
            identifier=result.series.periods[-1].representative_observation_id
            return next(o.semantic_id for o in result.extraction.observations if o.observation_id==identifier)
        self.assertEqual(representative_semantic(first),representative_semantic(second))

    def test_decimal_precision_and_context_independent_hashes(self):
        content=raw(source(annual_rows())).replace(b'"val":6', b'"val":6.123456789012345678901234567890123456789')
        receipt=self.archive.capture(content,cik=CIK,captured_at=T2,source_locator='fixture:precision')
        with localcontext() as ctx:
            ctx.prec=5
            first=resolve_annual_diluted_eps(self.archive,request(receipt))
        second=resolve_annual_diluted_eps(self.archive,request(receipt))
        self.assertEqual(first,second)
        self.assertEqual(first.series.periods[-1].value,Decimal('6.123456789012345678901234567890123456789'))
        equivalent=self.resolve([dict(r,val=float(r['val'])) for r in annual_rows()])
        self.assertEqual(self.resolve().series.semantic_hash,equivalent.series.semantic_hash)

    def test_semantic_hash_binds_values_intervals_and_issuer(self):
        first=self.resolve()
        rows=annual_rows(); rows[0]['val']=9
        self.assertNotEqual(first.series.semantic_hash,self.resolve(rows).series.semantic_hash)
        payload=source(annual_rows()); payload['cik']=1
        receipt=self.archive.capture(raw(payload),cik='0000000001',captured_at=T2,source_locator='fixture:other')
        other=resolve_annual_diluted_eps(self.archive,request(receipt,cik='0000000001'))
        self.assertNotEqual(first.series.semantic_hash,other.series.semantic_hash)

    def test_later_receipts_never_change_explicit_earlier_result(self):
        original=capture(self.archive)
        before=resolve_annual_diluted_eps(self.archive,request(original))
        rows=annual_rows(); rows[-1]['val']=99
        later=capture(self.archive,rows,captured_at='2026-04-01T12:00:00Z')
        self.assertEqual(before,resolve_annual_diluted_eps(self.archive,request(original)))
        self.assertNotEqual(before.series.semantic_hash,resolve_annual_diluted_eps(self.archive,request(later)).series.semantic_hash)

    def test_same_semantic_fact_recaptured_changes_only_evidence(self):
        first=capture(self.archive)
        later=capture(self.archive,captured_at='2026-04-01T12:00:00Z')
        a=resolve_annual_diluted_eps(self.archive,request(first)).series
        b=resolve_annual_diluted_eps(self.archive,request(later)).series
        self.assertEqual(a.semantic_hash,b.semantic_hash)
        self.assertNotEqual(a.evidence_hash,b.evidence_hash)

    def test_live_offline_authority_and_legacy_output_unchanged(self):
        for live in (False,True):
            receipt=capture(self.archive,live=live)
            legacy=inspect_archive(self.archive,cik=CIK,cutoff=T2)
            result=resolve_annual_diluted_eps(self.archive,request(receipt))
            blockers=result.series.downstream_admission_blockers
            self.assertEqual(AdmissionBlocker.OFFLINE_CAPTURE_NOT_AUTHENTICATED in blockers,not live)
            expected=CaptureAuthority.LIVE_LOCAL_CAPTURE if live else CaptureAuthority.OFFLINE_SUPPLIED_CAPTURE
            self.assertIs(result.source_authority.authority,expected)
            self.assertEqual(legacy,inspect_archive(self.archive,cik=CIK,cutoff=T2))
            self.assertIn('OFFLINE_CAPTURE_NOT_AUTHENTICATED',legacy.qualification_blockers)
            for blocker in (AdmissionBlocker.SPLIT_BASIS_NOT_ESTABLISHED,
                            AdmissionBlocker.SECURITY_SHARE_CLASS_AND_LISTING_NOT_ESTABLISHED,
                            AdmissionBlocker.PUBLICATION_AND_AVAILABILITY_NOT_ESTABLISHED):
                self.assertIn(blocker,blockers)

    def test_historical_rejected_without_reading_any_source(self):
        receipt=capture(self.archive)
        with patch.object(SecArchive,'read_receipt',side_effect=AssertionError('archive read')):
            result=resolve_annual_diluted_eps(self.archive,request(receipt,mode=ResolutionMode.HISTORICAL_AS_OF))
        self.blocked(result,R.HISTORICAL_CUTOFF_UNSUPPORTED)
        self.assertIsNone(result.extraction)
        self.assertIsNone(result.source_authority)

    def test_corrupt_object_or_receipt_fails_integrity(self):
        receipt=capture(self.archive)
        target=self.archive.root/'objects'/receipt.content_sha256
        target.chmod(0o600); target.write_bytes(b'corrupt')
        with self.assertRaises(SeriesResolutionError) as caught:
            resolve_annual_diluted_eps(self.archive,request(receipt))
        self.assertIs(caught.exception.reason,R.ARCHIVE_INTEGRITY_ERROR)

    def test_unknown_receipt_contract_rejected_without_reinterpretation(self):
        receipt=capture(self.archive)
        path=self.archive.root/'receipts'/(receipt.receipt_id+'.json')
        payload=json.loads(path.read_bytes())
        payload['acquisition_contract_version']='unknown-live-contract'
        path.chmod(0o600); path.write_text(json.dumps(payload))
        with self.assertRaises(SeriesResolutionError) as caught:
            resolve_annual_diluted_eps(self.archive,request(receipt))
        self.assertIs(caught.exception.reason,R.ARCHIVE_INTEGRITY_ERROR)

    def test_malformed_source_and_invalid_values_are_not_accepted(self):
        receipt=self.archive.capture(b'[]',cik=CIK,captured_at=T2,source_locator='fixture:bad')
        with self.assertRaises(SeriesResolutionError) as caught:
            resolve_annual_diluted_eps(self.archive,request(receipt))
        self.assertIs(caught.exception.reason,R.SOURCE_STRUCTURE_ERROR)
        for value in (None, True, '6'):
            rows=annual_rows(); rows[-1]['val']=value
            self.blocked(self.resolve(rows), R.INVALID_VALUE)

    def test_exclusion_inventory_and_evidence_hash_bind_unused_rows(self):
        baseline=self.resolve()
        result=self.resolve(annual_rows()+[row(2019)])
        self.assertEqual(baseline.series.semantic_hash,result.series.semantic_hash)
        self.assertNotEqual(baseline.series.evidence_hash,result.series.evidence_hash)
        admitted={i for d in result.period_decisions for i in d.admissible_observation_ids}
        excluded={x.observation_id for x in result.observation_exclusions}
        self.assertEqual(admitted | excluded, {o.observation_id for o in result.extraction.observations})
        self.assertFalse(admitted & excluded)

    def test_request_and_archive_subclasses_cannot_inject_observations(self):
        receipt=capture(self.archive)
        class ForeignArchive(SecArchive):
            pass
        class ForeignRequest(SeriesResolutionRequest):
            pass
        with self.assertRaises(SeriesResolutionError):
            resolve_annual_diluted_eps(ForeignArchive(self.archive.root),request(receipt))
        with self.assertRaises(SeriesResolutionError):
            resolve_annual_diluted_eps(self.archive,ForeignRequest(**asdict(request(receipt))))

    def test_forged_unstored_receipt_not_admitted(self):
        receipt=capture(self.archive)
        forged=replace(receipt,captured_at='2020-01-01T00:00:00Z')
        with self.assertRaises(SeriesResolutionError) as caught:
            resolve_annual_diluted_eps(self.archive,request(forged))
        self.assertIs(caught.exception.reason,R.ARCHIVE_INTEGRITY_ERROR)

    def test_closed_request_and_no_authority_override(self):
        receipt=capture(self.archive); req=request(receipt)
        for changes in ({'mode':'CURRENT_AS_REPORTED'},{'period_policy':'fake'},{'contract_version':'wrong'},
                        {'receipt_id':'../escape'},{'cik':True},{'latest_required_fiscal_end':'bad'}):
            with self.subTest(changes=changes),self.assertRaises(SeriesResolutionError):
                resolve_annual_diluted_eps(self.archive,replace(req,**changes))
        with self.assertRaises(SeriesResolutionError): resolve_annual_diluted_eps(self.archive,asdict(req))
        with self.assertRaises(TypeError): SeriesResolutionRequest(**asdict(req),as_of=T2)
        self.assertEqual(set(inspect.signature(resolve_annual_diluted_eps).parameters),{'archive','request'})
        with self.assertRaises(FrozenInstanceError): req.cik='0000000001'
        result=resolve_annual_diluted_eps(self.archive,req)
        with self.assertRaises(FrozenInstanceError): result.series.periods=()

    def test_cik_mismatch_and_missing_source_cik(self):
        receipt=capture(self.archive)
        with self.assertRaises(SeriesResolutionError) as caught:
            resolve_annual_diluted_eps(self.archive,request(receipt,cik='0000000001'))
        self.assertIs(caught.exception.reason,R.CIK_MISMATCH)
        payload=source(annual_rows()); del payload['cik']
        self.blocked(self.resolve(payload=payload),R.INSUFFICIENT_FILING_IDENTITY)

    def test_no_archive_writes_or_network(self):
        receipt=capture(self.archive)
        def inventory():
            return {str(p.relative_to(self.archive.root)):(p.read_bytes(),p.stat().st_mode,p.stat().st_mtime_ns)
                    for p in self.archive.root.rglob('*') if p.is_file()}
        before=inventory()
        with patch.object(SecArchive,'capture',side_effect=AssertionError('write')), \
             patch.object(SecArchive,'_publish',side_effect=AssertionError('write')), \
             patch.object(SecArchive,'captures_as_of',side_effect=AssertionError('implicit latest')), \
             patch.object(socket.socket,'connect',side_effect=AssertionError('network')), \
             patch.object(socket,'getaddrinfo',side_effect=AssertionError('network')):
            resolve_annual_diluted_eps(self.archive,request(receipt))
        self.assertEqual(before,inventory())

    def test_hash_seed_and_process_determinism_without_model_import(self):
        receipt=capture(self.archive)
        code='''import sys
from economic_facts.sec_archive import SecArchive
from economic_facts.sec_eps_series import resolve_annual_diluted_eps
from tests.sec_eps_series_fixtures import request
a=SecArchive(sys.argv[1]); r=a.read_receipt(sys.argv[2])
s=resolve_annual_diluted_eps(a,request(r)).series
assert not any(x == 'src' or x.startswith(('src.', 'pit_comparison')) for x in sys.modules)
assert 'economic_facts.sec_acquisition' not in sys.modules
print(s.semantic_hash, s.evidence_hash)
'''
        outputs=[]
        for seed in ('1','777'):
            outputs.append(subprocess.check_output([sys.executable,'-B','-c',code,str(self.archive.root),receipt.receipt_id],
                           env={**os.environ,'PYTHONHASHSEED':seed},text=True))
        self.assertEqual(outputs[0],outputs[1])

    def test_static_dependency_and_capability_boundary(self):
        root=Path(__file__).resolve().parents[1]
        tree=ast.parse((root/'economic_facts/sec_eps_series.py').read_text())
        allowed={'calendar','dataclasses','datetime','decimal','enum','json','re'}
        for node in ast.walk(tree):
            if isinstance(node,ast.Import): self.assertTrue(all(a.name in allowed for a in node.names))
            if isinstance(node,ast.ImportFrom):
                self.assertTrue(node.module in allowed or (node.level==1 and node.module in {'sec_archive','sec_diluted_eps'}))
            if isinstance(node,ast.Call):
                name=node.func.id if isinstance(node.func,ast.Name) else node.func.attr if isinstance(node.func,ast.Attribute) else ''
                self.assertNotIn(name,{'open','write','write_text','write_bytes','capture','_capture_live','_publish',
                                       'now','today','getenv','system','run','exec','eval','__import__'})
                if isinstance(node.func,ast.Name): self.assertNotEqual(name,'compile')
