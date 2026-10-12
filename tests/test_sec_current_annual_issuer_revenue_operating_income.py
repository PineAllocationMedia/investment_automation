"""Fictional adversarial fixtures; synthetic mechanics, never issuer authority."""
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from decimal import Decimal, localcontext
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from economic_facts.sec_archive import ArchiveError, SecArchive, endpoint_for
from economic_facts import sec_current_annual_issuer_revenue_operating_income as m
from economic_facts.sec_revenue_operating_income import CONCEPTS
from src import current_annual_operating_income_to_positive_revenue as native

from tests.test_sec_current_annual_reported_fact_research_candidate import (
    CIK, ACC, OTHER, TIME, row, payload,
)


class IssuerQualificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.physical_root = Path(self.temp.name).resolve(strict=True)
        self.archive = SecArchive(self.physical_root)

    def capture(self, source=None, *, timestamp=TIME, offline=False, raw=None):
        if raw is None:
            raw = json.dumps(payload() if source is None else source, sort_keys=True).encode()
        if offline:
            return self.archive.capture(raw, cik=CIK, captured_at=timestamp,
                                        source_locator=endpoint_for(CIK))
        return self.archive._capture_live(raw, cik=CIK, captured_at=timestamp)

    def evaluate(self, source=None, **kwargs):
        receipt = self.capture(source, **kwargs)
        return m.qualify_sec_current_annual_issuer_revenue_operating_income_v1(self.archive, receipt.receipt_id)

    def assert_failure(self, result, state, reason):
        self.assertIs(result.status, state)
        self.assertIn(reason, result.reasons)
        self.assertIsNone(result.revenue)
        self.assertIsNone(result.operating_income)
        self.assertEqual(result.supporting_filings, ())
        self.assertEqual(result.selected_revenue_observation_ids, ())
        self.assertEqual(result.selected_operating_income_observation_ids, ())
        self.assertFalse(any(o.disposition == 'SELECTED' for o in result.observations))
        self.assertTrue(result.observations or reason is m.R.NO_APPARENT_ANNUAL_PERIOD)
        self.assertEqual(result.reasons, tuple(sorted(set(result.reasons), key=lambda r: r.value)))

    def test_coherent_exact_decimals_fiscal_vintage_frame_and_immutable(self):
        source=payload([row(-100, fy=2025, frame='CY2024')], [row(0, fy=2025)])
        result=self.evaluate(source)
        self.assertIs(result.status, m.S.PAIRED_ISSUER_REPORTED_FACTS_ESTABLISHED)
        self.assertEqual((result.revenue, result.operating_income), (Decimal('-100'), Decimal('0')))
        self.assertEqual((result.period_start, result.period_end), ('2024-01-01','2024-12-31'))
        self.assertEqual(result.supporting_filings[0].fiscal_year,2025)
        self.assertEqual({o.disposition for o in result.observations},{'SELECTED'})
        self.assertTrue(all(o.source_locator.startswith('/facts/us-gaap/') for o in result.observations))
        self.assertEqual(result.authority,'CURRENT_ISSUER_REPORTED_PROFITABILITY_EVIDENCE_ONLY')
        with self.assertRaises(FrozenInstanceError):
            result.revenue=Decimal(1)
        with self.assertRaises(m.IssuerQualificationError):
            replace(result,status=m.S.EVIDENCE_UNAVAILABLE)
        with self.assertRaises(m.IssuerQualificationError):
            replace(result, reasons=(m.R.REVENUE_UNAVAILABLE,), status=m.S.EVIDENCE_UNAVAILABLE)

    def test_365_day_and_decimal_context_independent_identity(self):
        raw=json.dumps(payload([row(start='2023-01-01',end='2023-12-31')],
                               [row(20,start='2023-01-01',end='2023-12-31')])).encode()
        raw=raw.replace(b'"val": 100',b'"val": 12345678901234567890.123456789')
        result=self.evaluate(raw=raw)
        self.assertIs(result.status,m.S.PAIRED_ISSUER_REPORTED_FACTS_ESTABLISHED)
        self.assertEqual(result.revenue,Decimal('12345678901234567890.123456789'))
        with localcontext() as ctx:
            ctx.prec=2
            semantic,evidence=result.semantic_id,result.evidence_id
        self.assertEqual(semantic,result.semantic_id)
        self.assertEqual(evidence,result.evidence_id)

    def test_missing_each_concept(self):
        for c,reason in zip(CONCEPTS,(m.R.REVENUE_UNAVAILABLE,m.R.OPERATING_INCOME_UNAVAILABLE)):
            with self.subTest(concept=c):
                source=payload(); del source['facts']['us-gaap'][c]
                self.assert_failure(self.evaluate(source),m.S.EVIDENCE_UNAVAILABLE,reason)

    def test_no_annual_inventory(self):
        self.assert_failure(self.evaluate(payload([],[])),m.S.EVIDENCE_UNAVAILABLE,m.R.NO_APPARENT_ANNUAL_PERIOD)

    def test_no_common_accession(self):
        result=self.evaluate(payload([row()], [row(20,accn=OTHER)]))
        self.assert_failure(result,m.S.EVIDENCE_UNAVAILABLE,m.R.NO_COMMON_ANNUAL_ACCESSION)
        self.assertEqual({o.disposition for o in result.observations},{'ORPHAN'})

    def test_all_common_accessions_consensus_not_majority_or_latest(self):
        for c,reason in zip(CONCEPTS,(m.R.COMPETING_REVENUE_VALUES,m.R.COMPETING_OPERATING_INCOME_VALUES)):
            source=payload([row(),row(accn=OTHER)], [row(20),row(20,accn=OTHER)])
            source['facts']['us-gaap'][c]['units']['USD'][1]['val']=999
            result=self.evaluate(source)
            self.assert_failure(result,m.S.SOURCE_CONFLICT,reason)
            self.assertEqual(len(result.adjudicated_filings),2)
            self.assertTrue(any(o.disposition=='COMPETING' for o in result.observations))

    def test_duplicate_equal_values_and_frame_difference(self):
        result=self.evaluate(payload([row(),row(frame='CY2024')],[row(20)]))
        self.assertIs(result.status,m.S.PAIRED_ISSUER_REPORTED_FACTS_ESTABLISHED)
        self.assertEqual(len(result.supporting_filings[0].revenue_observation_ids),2)

    def test_common_metadata_conflicts(self):
        for changes in ({'form':'10-K/A'},{'filed':'2025-02-02'},{'fy':2025}):
            with self.subTest(changes=changes):
                self.assert_failure(self.evaluate(payload([row()], [row(20,**changes)])),
                    m.S.SOURCE_CONFLICT,m.R.COMMON_FILING_METADATA_CONFLICT)

    def test_orphan_retained_without_manufactured_conflict(self):
        result=self.evaluate(payload([row(),row(999,accn=OTHER)],[row(20)]))
        self.assertIs(result.status,m.S.PAIRED_ISSUER_REPORTED_FACTS_ESTABLISHED)
        orphan=next(o for o in result.observations if o.accession==OTHER)
        self.assertEqual(orphan.value,Decimal(999))
        self.assertEqual(orphan.disposition,'ORPHAN')
        self.assertIn('NO_PAIRED_CONCEPT_IN_ACCESSION',orphan.exclusion_reasons)

    def test_newer_missing_concept_no_fallback(self):
        result=self.evaluate(payload([row(),row(200,start='2025-01-01',end='2025-12-31',filed='2026-02-01')],
                                    [row(20)]),timestamp='2026-08-01T00:00:00Z')
        self.assert_failure(result,m.S.EVIDENCE_UNAVAILABLE,m.R.OPERATING_INCOME_UNAVAILABLE)
        self.assertEqual(result.period_end,'2025-12-31')

    def test_unlocatable_apparent_endpoint_blocks_old_pair(self):
        for end in (None,'bogus','2025-2-01'):
            with self.subTest(end=end):
                source=payload([row(),row(end=end)], [row(20)])
                self.assert_failure(self.evaluate(source),m.S.EVIDENCE_UNSUPPORTED,m.R.ANNUAL_ENDPOINT_UNLOCATABLE)

    def test_incomplete_metadata_annual_surveillance(self):
        result=self.evaluate(payload([row(),row(fp=None,start=None,end=None)], [row(20)]))
        self.assert_failure(result,m.S.EVIDENCE_UNSUPPORTED,m.R.ANNUAL_ENDPOINT_UNLOCATABLE)

    def test_52_53_week_transition_and_reversed_intervals(self):
        for start,end in [('2024-01-03','2024-12-31'),('2023-12-27','2024-12-31'),
                          ('2024-07-01','2024-12-31'),('2025-01-01','2024-12-31')]:
            with self.subTest(start=start):
                self.assert_failure(self.evaluate(payload([row(start=start,end=end)],[row(20,start=start,end=end)])),
                    m.S.EVIDENCE_UNSUPPORTED,m.R.ANNUAL_INTERVAL_UNSUPPORTED)

    def test_newer_unsupported_annual_no_old_fallback(self):
        result=self.evaluate(payload([row(),row(start='2025-01-02',end='2025-12-31',filed='2026-02-01')],
                                    [row(20)]),timestamp='2026-08-01T00:00:00Z')
        self.assert_failure(result,m.S.EVIDENCE_UNSUPPORTED,m.R.ANNUAL_INTERVAL_UNSUPPORTED)
        self.assertEqual(result.period_end,'2025-12-31')

    def test_ambiguous_annual_start(self):
        result=self.evaluate(payload([row(),row(start='2024-01-02')], [row(20)]))
        self.assert_failure(result,m.S.EVIDENCE_UNSUPPORTED,m.R.ANNUAL_INTERVAL_AMBIGUOUS)
        self.assertIsNone(result.period_start)

    def test_known_quarter_not_annual_candidate(self):
        source=payload([row(),row(fp='Q4',form='10-Q',start='2025-04-01',end='2025-06-30')], [row(20)])
        result=self.evaluate(source)
        self.assertIs(result.status,m.S.PAIRED_ISSUER_REPORTED_FACTS_ESTABLISHED)
        self.assertEqual(result.period_end,'2024-12-31')
        self.assertTrue(any('CLEARLY_NONANNUAL' in o.exclusion_reasons for o in result.observations))

    def test_a1_newer_annual_filing_missing_fiscal_metadata_blocks_fallback(self):
        # FICTIONAL: valid dates, 359 inclusive days, but no fiscal FP/FY.
        newer=row(200,start='2025-01-07',end='2025-12-31',
                  filed='2026-02-01',fp=None,fy=None)
        del newer['fp']
        del newer['fy']
        result=self.evaluate(payload([row(),newer],[row(20)]),
                             timestamp='2026-08-01T00:00:00Z')
        self.assert_failure(result,m.S.EVIDENCE_UNSUPPORTED,m.R.ANNUAL_INTERVAL_UNSUPPORTED)
        self.assertEqual(result.period_end,'2025-12-31')
        self.assertIsNone(result.period_start)
        observed=next(o for o in result.observations if o.end=='2025-12-31')
        self.assertEqual(observed.disposition,'UNSUPPORTED')
        self.assertIn('ANNUAL_INTERVAL_UNSUPPORTED',observed.exclusion_reasons)
        self.assertTrue(observed.observation_id)
        self.assertTrue(observed.source_locator.startswith('/facts/us-gaap/'))
        self.assertFalse(any(o.disposition=='SELECTED' for o in result.observations))

    def test_a2_explicit_quarter_missing_start_does_not_select_annual_endpoint(self):
        # FICTIONAL: integer FY is filing metadata, not annual-period proof.
        newer=row(200,form='10-Q',fp='Q4',fy=2025,start=None,
                  end='2025-12-31',filed='2026-02-01')
        del newer['start']
        result=self.evaluate(payload([row(),newer],[row(20)]),
                             timestamp='2026-08-01T00:00:00Z')
        self.assertIs(result.status,m.S.PAIRED_ISSUER_REPORTED_FACTS_ESTABLISHED)
        self.assertEqual(result.reasons,())
        self.assertEqual(result.period_end,'2024-12-31')
        self.assertEqual((result.revenue,result.operating_income),(Decimal(100),Decimal(20)))
        observed=next(o for o in result.observations if o.end=='2025-12-31')
        self.assertEqual(observed.disposition,'NONSELECTED')
        self.assertIn('CLEARLY_NONANNUAL',observed.exclusion_reasons)
        self.assertEqual((observed.form,observed.fp,observed.fy),('10-Q','Q4',2025))
        self.assertTrue(observed.observation_id)
        self.assertTrue(observed.source_locator.startswith('/facts/us-gaap/'))

    def test_annual_form_quarter_fp_missing_start_blocks_older_fallback(self):
        # FICTIONAL: annual form contradicts a clearly quarterly interpretation.
        newer=row(200,form='10-K',fp='Q4',fy=2025,start=None,
                  end='2025-12-31',filed='2026-02-01')
        result=self.evaluate(payload([row(),newer],[row(20)]),
                             timestamp='2026-08-01T00:00:00Z')
        self.assert_failure(result,m.S.EVIDENCE_UNSUPPORTED,m.R.ANNUAL_INTERVAL_UNSUPPORTED)
        self.assertEqual(result.period_end,'2025-12-31')
        self.assertIsNone(result.period_start)
        observed=next(o for o in result.observations if o.end=='2025-12-31')
        self.assertEqual(observed.disposition,'UNSUPPORTED')
        self.assertNotIn('CLEARLY_NONANNUAL',observed.exclusion_reasons)
        self.assertIn('POTENTIALLY_COMPARABLE_CONTEXT_UNRESOLVED',observed.exclusion_reasons)
        self.assertEqual((observed.form,observed.fp,observed.fy),('10-K','Q4',2025))
        self.assertTrue(observed.observation_id)
        self.assertTrue(observed.source_locator.startswith('/facts/us-gaap/'))
        self.assertFalse(any(o.disposition=='SELECTED' for o in result.observations))

    def test_duration_surveillance_despite_quarter_context(self):
        result=self.evaluate(payload([row(),row(fp='Q4',form='10-Q',start='2025-01-01',
                            end='2025-12-31',filed='2026-02-01')],[row(20)]),timestamp='2026-08-01T00:00:00Z')
        self.assert_failure(result,m.S.EVIDENCE_UNSUPPORTED,m.R.UNSUPPORTED_FILING_CONTEXT)
        self.assertEqual(result.period_end,'2025-12-31')

    def test_non_usd_surveillance_and_no_positive_substitution(self):
        source=payload()
        source['facts']['us-gaap'][CONCEPTS[0]]['units']['CAD']=[row(start='2025-01-01',end='2025-12-31',filed='2026-02-01')]
        result=self.evaluate(source,timestamp='2026-08-01T00:00:00Z')
        self.assert_failure(result,m.S.EVIDENCE_UNSUPPORTED,m.R.UNSUPPORTED_UNIT_OR_ROW_CONTEXT)
        self.assertEqual(result.period_end,'2025-12-31')
        self.assertTrue(any(o.unit=='CAD' for o in result.observations))

    def test_invalid_row_metadata_and_unknown_extensions(self):
        for changes in ({'accn':'invalid'},{'filed':None},{'fy':True},{'start':'invalid'},
                        {'frame':7},{'segment':'FICTIONAL UNKNOWN CONTEXT'}):
            with self.subTest(changes=changes):
                result=self.evaluate(payload([row(**changes)],[row(20)]))
                self.assertIs(result.status,m.S.EVIDENCE_UNSUPPORTED)
                self.assertIsNone(result.revenue)
                self.assertIsNone(result.operating_income)
                self.assertTrue(result.reasons)

    def test_missing_and_invalid_values(self):
        for value in (None,True,'100'):
            result=self.evaluate(payload([row(value)],[row(20)]))
            self.assert_failure(result,m.S.EVIDENCE_UNAVAILABLE,m.R.FINITE_VALUE_UNAVAILABLE)

    def test_chronology_conflict_precedence(self):
        for filed in ('2024-12-30','2025-09-01'):
            result=self.evaluate(payload([row(filed=filed,form='10-Q')],[row(20)]))
            self.assert_failure(result,m.S.SOURCE_CONFLICT,m.R.INVALID_FILING_CHRONOLOGY)
            self.assertIn(m.R.UNSUPPORTED_FILING_CONTEXT,result.reasons)

    def test_invalid_public_inputs_and_extra_selectors(self):
        receipt=self.capture()
        class ForeignArchive(SecArchive):
            pass
        for archive,rid in ((None,receipt.receipt_id),(ForeignArchive(self.temp.name),receipt.receipt_id),
                            (self.archive,None),(self.archive,receipt),(self.archive,'A'*64),
                            (self.archive,'0'*63),(self.archive,123)):
            with self.subTest(rid=repr(rid)):
                with self.assertRaises(m.IssuerQualificationError):
                    m.qualify_sec_current_annual_issuer_revenue_operating_income_v1(archive,rid)
        with self.assertRaises(TypeError):
            m.qualify_sec_current_annual_issuer_revenue_operating_income_v1(self.archive,receipt.receipt_id,period='2024')

    def test_offline_receipt_rejected(self):
        with self.assertRaises(m.IssuerQualificationError):
            self.evaluate(offline=True)

    def test_missing_receipt_membership_and_corrupt_original_bytes(self):
        with self.assertRaises(ArchiveError):
            m.qualify_sec_current_annual_issuer_revenue_operating_income_v1(self.archive,'0'*64)
        receipt=self.capture()
        obj=self.physical_root/'objects'/receipt.content_sha256
        obj.chmod(0o600)  # Deliberate fictional corruption; production remains read-only.
        original=obj.read_bytes()
        for corrupt in (original+b' ',b'x'+original[1:]):
            obj.write_bytes(corrupt)
            with self.assertRaises(ArchiveError):
                m.qualify_sec_current_annual_issuer_revenue_operating_income_v1(self.archive,receipt.receipt_id)
        obj.write_bytes(original)
        receipt_file=self.physical_root/'receipts'/(receipt.receipt_id+'.json')
        receipt_file.chmod(0o600)
        receipt_file.write_bytes(b'{}')
        with self.assertRaises(ArchiveError):
            m.qualify_sec_current_annual_issuer_revenue_operating_income_v1(self.archive,receipt.receipt_id)

    def test_source_cik_mismatch_and_malformed_source(self):
        for source in ({'cik':999,'facts':{}},{'facts':{}}, {'cik':True},
                       {'cik':123,'facts':[]}, {'cik':123,'facts':{'us-gaap':{CONCEPTS[0]:{'units':{'USD':[7]}}}}}):
            with self.subTest(source=source):
                with self.assertRaises(ArchiveError):
                    self.evaluate(source)
        for raw in (b'not json',b'{"cik":123,"cik":123}',b'{"cik":123,"val":NaN}'):
            with self.assertRaises(ArchiveError):
                self.evaluate(raw=raw)

    def test_noncanonical_live_source_locator(self):
        from economic_facts.sec_archive import LIVE_ACQUISITION_CONTRACT_VERSION
        receipt=self.archive._capture(json.dumps(payload()).encode(),cik=CIK,captured_at=TIME,
            source_locator='FICTIONAL:wrong-locator',acquisition_contract_version=LIVE_ACQUISITION_CONTRACT_VERSION)
        with self.assertRaises(m.IssuerQualificationError):
            m.qualify_sec_current_annual_issuer_revenue_operating_income_v1(self.archive,receipt.receipt_id)

    def test_recapture_same_object_distinct_receipt_identity(self):
        a=self.evaluate()
        b=self.evaluate(timestamp='2025-08-02T00:00:00Z')
        self.assertEqual(a.source_object_hash,b.source_object_hash)
        self.assertEqual(a.semantic_id,b.semantic_id)
        self.assertNotEqual(a.evidence_id,b.evidence_id)
        self.assertNotEqual(a.extraction_inventory_id,b.extraction_inventory_id)

    def test_source_permutations_do_not_change_state_semantics_or_reason_order(self):
        source=payload([row(),row(999,accn=OTHER)], [row(20),row(21,accn=OTHER)])
        a=self.evaluate(source)
        reverse=deepcopy(source)
        for c in CONCEPTS:
            reverse['facts']['us-gaap'][c]['units']['USD'].reverse()
        b=self.evaluate(reverse)
        self.assertEqual(a.status,b.status)
        self.assertEqual(a.reasons,b.reasons)
        self.assertEqual(a.semantic_id,b.semantic_id)
        self.assertNotEqual(a.evidence_id,b.evidence_id)

    def test_changed_values_period_status_conflict_affect_identity(self):
        a=self.evaluate()
        variants=[payload([row(101)],[row(20)]),
            payload([row(start='2023-01-01',end='2023-12-31')],[row(20,start='2023-01-01',end='2023-12-31')]),
            payload([row()],[]),payload([row(),row(200)],[row(20)])]
        ids={a.semantic_id}
        for source in variants:
            ids.add(self.evaluate(source).semantic_id)
        self.assertEqual(len(ids),5)
        x=self.evaluate(payload([row(),row(200)],[row(20)]))
        y=self.evaluate(payload([row(),row(201)],[row(20)]))
        self.assertNotEqual(x.semantic_id,y.semantic_id)

    def test_irrelevant_inventory_changes_only_evidence(self):
        a=self.evaluate()
        b=self.evaluate(payload([row(),row(999,fp='Q1',form='10-Q',start='2024-01-01',end='2024-03-31')],[row(20)]))
        self.assertEqual(a.semantic_id,b.semantic_id)
        self.assertNotEqual(a.evidence_id,b.evidence_id)
        self.assertNotEqual(a.extraction_inventory_id,b.extraction_inventory_id)

    def test_native_quality_exact_type_rejection_even_forged_identity(self):
        result=self.evaluate()
        with self.assertRaises(native.CurrentAnnualOperatingIncomeToPositiveRevenueError):
            native.analyze_current_annual_operating_income_to_positive_revenue(result)
        with self.assertRaises(native.CurrentAnnualOperatingIncomeToPositiveRevenueError):
            native.analyze_current_annual_operating_income_to_positive_revenue(replace(result,source_cik='0000000999'))

    def test_incidental_archive_path_not_identity(self):
        source=json.dumps(payload(),sort_keys=True).encode()
        receipt=self.capture(raw=source)
        a=m.qualify_sec_current_annual_issuer_revenue_operating_income_v1(self.archive,receipt.receipt_id)
        other=SecArchive(self.physical_root/'another-physical-root')
        other_receipt=other._capture_live(source,cik=CIK,captured_at=TIME)
        b=m.qualify_sec_current_annual_issuer_revenue_operating_income_v1(other,other_receipt.receipt_id)
        self.assertEqual(a,b)
        self.assertEqual(a.semantic_id,b.semantic_id)
        self.assertEqual(a.evidence_id,b.evidence_id)

    def test_mutable_reconstructed_inventory_rejected(self):
        result=self.evaluate()
        with self.assertRaises(m.IssuerQualificationError):
            replace(result,observations=list(result.observations))
        altered=replace(result.observations[0],exclusion_reasons=[])
        with self.assertRaises(m.IssuerQualificationError):
            replace(result,observations=(altered,)+result.observations[1:])

    def test_native_module_has_no_research_promotion_or_network(self):
        import ast
        tree=ast.parse(Path(m.__file__).read_text())
        allowed={'dataclasses','datetime','decimal','enum','json','re','typing',
                 'sec_archive','sec_revenue_operating_income'}
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):
                self.assertTrue(all(item.name in allowed for item in node.names))
            elif isinstance(node,ast.ImportFrom):
                self.assertIn(node.module,allowed)

    def test_symlink_archive_and_object_rejected(self):
        receipt=self.capture()
        alias=self.physical_root/'unsafe-alias'
        alias.symlink_to(self.physical_root, target_is_directory=True)
        with self.assertRaises(ArchiveError):
            m.qualify_sec_current_annual_issuer_revenue_operating_income_v1(SecArchive(alias),receipt.receipt_id)
        obj=self.physical_root/'objects'/receipt.content_sha256
        saved=self.physical_root/'saved-object'
        obj.rename(saved)
        obj.symlink_to(saved)
        with self.assertRaises(ArchiveError):
            m.qualify_sec_current_annual_issuer_revenue_operating_income_v1(self.archive,receipt.receipt_id)

    def test_network_free_archive_unchanged_no_new_files(self):
        receipt=self.capture()
        before={str(p.relative_to(self.temp.name)):p.read_bytes() for p in Path(self.temp.name).rglob('*') if p.is_file()}
        with patch.object(socket,'socket',side_effect=AssertionError('Network forbidden')), \
             patch.object(SecArchive,'_capture_live',side_effect=AssertionError('Capture forbidden')), \
             patch.object(SecArchive,'capture',side_effect=AssertionError('Capture forbidden')):
            result=m.qualify_sec_current_annual_issuer_revenue_operating_income_v1(self.archive,receipt.receipt_id)
        after={str(p.relative_to(self.temp.name)):p.read_bytes() for p in Path(self.temp.name).rglob('*') if p.is_file()}
        self.assertEqual(before,after)
        self.assertIs(result.status,m.S.PAIRED_ISSUER_REPORTED_FACTS_ESTABLISHED)
        self.assertNotIn('row_json',repr(result))

    def test_multiple_agreeing_accessions_preserve_all_selected_support(self):
        result = self.evaluate(payload([row(), row(accn=OTHER)],
                                       [row(20), row(20, accn=OTHER)]))
        self.assertIs(result.status, m.S.PAIRED_ISSUER_REPORTED_FACTS_ESTABLISHED)
        self.assertEqual(tuple(f.accession for f in result.supporting_filings), (ACC, OTHER))
        self.assertEqual(len(result.selected_revenue_observation_ids), 2)
        self.assertEqual(len(result.selected_operating_income_observation_ids), 2)
        for filing in result.supporting_filings:
            self.assertTrue(filing.revenue_observation_ids)
            self.assertTrue(filing.operating_income_observation_ids)

    def test_alternative_concept_cannot_substitute(self):
        source = payload()
        facts = source['facts']['us-gaap']
        facts['SalesRevenueNet'] = facts.pop(CONCEPTS[0])
        self.assert_failure(self.evaluate(source), m.S.EVIDENCE_UNAVAILABLE,
                            m.R.REVENUE_UNAVAILABLE)

    def test_original_decimal_representative_is_selected_source_value(self):
        raw = json.dumps(payload([row(), row(accn=OTHER)],
                                 [row(20), row(20, accn=OTHER)])).encode()
        raw = raw.replace(b'"val": 100', b'"val": 100.00', 1)
        result = self.evaluate(raw=raw)
        chosen = min((o for o in result.observations
                      if o.observation_id in result.selected_revenue_observation_ids),
                     key=lambda o: o.observation_id)
        self.assertEqual(result.revenue.as_tuple(), chosen.value.as_tuple())
        self.assertEqual({o.value.as_tuple().exponent for o in result.observations
                          if o.concept == CONCEPTS[0]}, {0, -2})

    def test_receipt_hash_length_cik_and_contract_tampering(self):
        receipt = self.capture()
        path = self.physical_root / 'receipts' / (receipt.receipt_id + '.json')
        original = path.read_bytes()
        path.chmod(0o600)
        for key, value in [('content_sha256', '0'*64), ('byte_length', receipt.byte_length+1),
                           ('cik', '0000000999'), ('acquisition_contract_version', 'future')]:
            altered = json.loads(original)
            altered[key] = value
            path.write_text(json.dumps(altered))
            with self.subTest(field=key), self.assertRaises(ArchiveError):
                m.qualify_sec_current_annual_issuer_revenue_operating_income_v1(
                    self.archive, receipt.receipt_id)
        path.write_bytes(original)


if __name__ == '__main__':
    unittest.main()
