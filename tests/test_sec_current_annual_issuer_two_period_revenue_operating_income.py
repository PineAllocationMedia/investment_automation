"""Adversarial Contract A R3 mechanics with explicitly fictional evidence.

Covers canonical R3 predicates and the recovered independent-review T1–T20
configurations. No authentic applicability or investment authority is established.
"""
from copy import deepcopy
from dataclasses import FrozenInstanceError, asdict, fields, replace
from decimal import Decimal, localcontext, Inexact, Rounded, FloatOperation
import json
import pickle
import socket
from unittest.mock import patch

from economic_facts.sec_archive import ArchiveError, SecArchive
from economic_facts.sec_revenue_operating_income import CONCEPTS
from tests.sec_d1_two_period_fixtures import D1Fixture, comparative, prior, row, payload, ACC, OTHER, TIME, a


class ComparativeQualificationTests(D1Fixture):
    def failure(self, result, state, *reasons):
        self.assertIs(result.status, state)
        for reason in reasons:
            self.assertIn(reason, result.reasons)
        self.assertEqual(result.reasons, tuple(sorted(set(result.reasons), key=lambda r: r.value)))
        self.assertEqual((result.prior_revenue, result.prior_operating_income,
                          result.current_revenue, result.current_operating_income), (None,) * 4)
        self.assertEqual(result.selected_observation_ids, ((),) * 4)
        self.assertEqual(result.supporting_filings, ())
        self.assertFalse(any(o.disposition is a.D.SELECTED for o in result.observations))
        self.assertTrue(all(type(o.disposition) is a.D for o in result.observations))
        return result

    def test_established_four_cells_fiscal_vintage_and_full_provenance(self):
        q = self.evaluate(comparative(fy=2025))
        self.assertIs(q.status, a.S.COMPARATIVE_ISSUER_REPORTED_FACTS_ESTABLISHED)
        self.assertEqual((q.prior_revenue, q.prior_operating_income, q.current_revenue,
                          q.current_operating_income), tuple(map(Decimal, (80, 10, 100, 20))))
        self.assertEqual((q.prior_period_start, q.prior_period_end, q.current_period_start,
                          q.current_period_end), ('2023-01-01','2023-12-31','2024-01-01','2024-12-31'))
        self.assertEqual(len(q.supporting_filings), 1)
        self.assertTrue(all(q.supporting_filings[0].cell_observation_ids))
        self.assertEqual(q.selected_observation_ids, q.supporting_filings[0].cell_observation_ids)
        self.assertTrue(all(r.observation.row_json and r.observation.namespace == 'us-gaap'
                            and r.observation.source_object_hash == q.source_object_hash
                            for r in q.observations))
        self.assertEqual(q.temporal_mode, 'CURRENT_CAPTURE_BOUND_ONLY')
        self.assertNotIn('_archive_replay_binding', asdict(q))
        with self.assertRaises(FrozenInstanceError):
            q.prior_revenue = Decimal(9)
        self.assertEqual(a._verified_comparative_snapshot(q), q)

    def test_missing_current_concepts_without_prior_reasons(self):
        for index, reason in enumerate((a.R.CURRENT_REVENUE_UNAVAILABLE,
                                         a.R.CURRENT_OPERATING_INCOME_UNAVAILABLE)):
            source = comparative()
            source['facts']['us-gaap'][CONCEPTS[index]]['units']['USD'].pop()
            q = self.failure(self.evaluate(source), a.S.EVIDENCE_UNAVAILABLE, reason)
            self.assertFalse(any('PRIOR' in r.value or 'FOUR_CELL' in r.value for r in q.reasons))

    def test_disjoint_current_accessions_explicit_closed_transition(self):
        source = comparative()
        source['facts']['us-gaap'][CONCEPTS[1]]['units']['USD'][-1]['accn'] = OTHER
        q = self.failure(self.evaluate(source), a.S.EVIDENCE_UNAVAILABLE, a.R.NO_COMMON_CURRENT_ACCESSION)
        self.assertEqual(q.reasons, (a.R.NO_COMMON_CURRENT_ACCESSION,))
        self.assertIsNone(q.prior_period_start)
        self.assertIsNone(q.prior_period_end)

    def test_no_annual_and_only_known_quarter(self):
        for source in (payload([], []), payload([row(fp='Q4',form='10-Q',start=None)], [])):
            self.assertEqual(self.failure(self.evaluate(source), a.S.EVIDENCE_UNAVAILABLE,
                a.R.NO_APPARENT_ANNUAL_PERIOD).reasons, (a.R.NO_APPARENT_ANNUAL_PERIOD,))

    def test_newer_endpoint_without_pair_never_falls_back(self):
        source = comparative()
        source['facts']['us-gaap'][CONCEPTS[0]]['units']['USD'].append(
            row(start='2025-01-01',end='2025-12-31',filed='2026-02-01'))
        q = self.failure(self.evaluate(source,timestamp='2026-08-01T00:00:00Z'),
                         a.S.EVIDENCE_UNAVAILABLE,a.R.CURRENT_OPERATING_INCOME_UNAVAILABLE)
        self.assertEqual(q.current_period_end,'2025-12-31')
        self.assertIsNone(q.prior_period_start)

    def test_unlocatable_and_unknown_current_forbid_prior_reasons(self):
        for changes in ({'end':None}, {'end':'bad'}, {'start':None},
                        {'start':'2024-01-02'}, {'start':'2025-01-01'},
                        {'form':'10-K','fp':'Q4','start':None}):
            source = comparative()
            source['facts']['us-gaap'][CONCEPTS[0]]['units']['USD'].append(row(**changes))
            q = self.failure(self.evaluate(source),a.S.EVIDENCE_UNSUPPORTED)
            self.assertFalse(any(r.value.startswith('PRIOR_') or r.value.startswith('PERIODS_')
                                 or 'ADJACENT_PRIOR' in r.value for r in q.reasons))
            self.assertIsNone(q.prior_period_start)

    def test_annual_surveillance_unfavorable_form_fp_and_364_371_days(self):
        for changes in ({'form':'10-Q'}, {'fp':'Q4'}, {'start':'2024-01-03'},
                        {'start':'2023-12-27'}, {'fp':None,'fy':None,'start':None}):
            source = comparative()
            source['facts']['us-gaap'][CONCEPTS[0]]['units']['USD'].append(row(accn=OTHER,**changes))
            self.failure(self.evaluate(source),a.S.EVIDENCE_UNSUPPORTED)

    def test_unknown_newer_10k_vs_known_10q_quarter(self):
        for form, state in (('10-K',a.S.EVIDENCE_UNSUPPORTED),('10-Q',a.S.COMPARATIVE_ISSUER_REPORTED_FACTS_ESTABLISHED)):
            source=comparative()
            source['facts']['us-gaap'][CONCEPTS[0]]['units']['USD'].append(
                row(form=form,fp='Q4',start=None,end='2025-12-31',filed='2026-02-01'))
            self.assertIs(self.evaluate(source,timestamp='2026-08-01T00:00:00Z').status,state)

    def test_current_metadata_conflict_not_no_common(self):
        for changes in ({'fy':2025},{'form':'10-K/A'},{'filed':'2025-02-02'}):
            source=comparative()
            source['facts']['us-gaap'][CONCEPTS[1]]['units']['USD'][-1].update(changes)
            q=self.failure(self.evaluate(source),a.S.SOURCE_CONFLICT,a.R.COMMON_FILING_METADATA_CONFLICT)
            self.assertNotIn(a.R.NO_COMMON_CURRENT_ACCESSION,q.reasons)
            self.assertIsNone(q.prior_period_start)

    def test_no_prior_after_coherent_current_pair(self):
        q=self.failure(self.evaluate(payload()),a.S.EVIDENCE_UNAVAILABLE,a.R.ADJACENT_PRIOR_PERIOD_NOT_OBSERVED)
        self.assertEqual(q.reasons,(a.R.ADJACENT_PRIOR_PERIOD_NOT_OBSERVED,))

    def test_missing_prior_concepts_and_distributed_four_cells(self):
        for index, reason in enumerate((a.R.PRIOR_REVENUE_UNAVAILABLE,a.R.PRIOR_OPERATING_INCOME_UNAVAILABLE)):
            source=comparative()
            source['facts']['us-gaap'][CONCEPTS[index]]['units']['USD'].pop(0)
            self.failure(self.evaluate(source),a.S.EVIDENCE_UNAVAILABLE,reason)
        source=comparative()
        source['facts']['us-gaap'][CONCEPTS[1]]['units']['USD'][0]['accn']=OTHER
        self.failure(self.evaluate(source),a.S.EVIDENCE_UNAVAILABLE,a.R.NO_COMMON_FOUR_CELL_ACCESSION)
        source=payload([row(),prior(accn=OTHER,fy=2023)], [row(20),prior(10,accn=OTHER,fy=2023)])
        q=self.failure(self.evaluate(source),a.S.EVIDENCE_UNAVAILABLE,a.R.NO_COMMON_FOUR_CELL_ACCESSION)
        self.assertNotIn(a.R.ADJACENT_PRIOR_PERIOD_NOT_OBSERVED,q.reasons)

    def test_gap_overlap_and_prior_unsupported_duration(self):
        cases=[({'start':'2022-01-01','end':'2022-12-31'},a.R.PERIODS_NOT_IMMEDIATELY_ADJACENT),
               ({'start':'2023-02-01','end':'2024-01-31'},a.R.PERIODS_OVERLAP),
               ({'start':'2023-01-02','end':'2023-12-31'},a.R.PRIOR_ANNUAL_INTERVAL_UNSUPPORTED)]
        for changes,reason in cases:
            source=comparative()
            for c in CONCEPTS:
                source['facts']['us-gaap'][c]['units']['USD'][0].update(changes)
            self.failure(self.evaluate(source),a.S.EVIDENCE_UNSUPPORTED,reason)

    def test_older_same_filing_history_is_not_another_prior(self):
        source=comparative()
        for c in CONCEPTS:
            source['facts']['us-gaap'][c]['units']['USD'].append(prior(999,start='2022-01-01',end='2022-12-31'))
        q=self.evaluate(source)
        self.assertIs(q.status,a.S.COMPARATIVE_ISSUER_REPORTED_FACTS_ESTABLISHED)
        self.assertEqual(sum('OLDER_COMPARATIVE_HISTORY' in o.reasons for o in q.observations),2)
        self.assertEqual(sum(o.disposition is a.D.SELECTED for o in q.observations),4)

    def test_complete_prior_intervals_are_ambiguous_historical_only_is_excluded(self):
        for historical,state in ((False,a.S.EVIDENCE_UNSUPPORTED),(True,a.S.COMPARATIVE_ISSUER_REPORTED_FACTS_ESTABLISHED)):
            source=comparative()
            for index,c in enumerate(CONCEPTS):
                rows=source['facts']['us-gaap'][c]['units']['USD']
                rows.append(prior(80 if index==0 else 10,start='2022-12-31',accn=OTHER,fy=2023 if historical else 2024))
                if not historical:
                    rows.append(row(100 if index==0 else 20,accn=OTHER))
            q=self.evaluate(source)
            self.assertIs(q.status,state)
            if historical:
                refs=[o for o in q.observations if o.observation.accession==OTHER]
                self.assertTrue(all(o.disposition is a.D.NONSELECTED and o.exclusion_reasons ==
                    (a.X.EXCLUDED_DIFFERENT_FILING_VINTAGE_PRIOR_ONLY,) for o in refs))
            else:
                self.assertIn(a.R.PRIOR_ANNUAL_INTERVAL_AMBIGUOUS,q.reasons)
                self.assertIsNone(q.prior_period_start)

    def test_partial_current_equal_or_contradictory_before_after_amended(self):
        for index,c in enumerate(CONCEPTS):
            for filed,form in (('2025-01-31','10-K'),('2025-03-01','10-K/A')):
                for value,state in ((100 if index==0 else 20,a.S.COMPARATIVE_ISSUER_REPORTED_FACTS_ESTABLISHED),
                                    (999,a.S.SOURCE_CONFLICT)):
                    source=comparative()
                    source['facts']['us-gaap'][c]['units']['USD'].append(row(value,accn=OTHER,filed=filed,form=form))
                    q=self.evaluate(source)
                    self.assertIs(q.status,state)
                    ref=next(o for o in q.observations if o.observation.accession==OTHER)
                    if state is a.S.SOURCE_CONFLICT:
                        self.failure(q,state,(a.R.COMPETING_CURRENT_REVENUE_VALUES,
                                              a.R.COMPETING_CURRENT_OPERATING_INCOME_VALUES)[index])
                        self.assertIs(ref.disposition,a.D.COMPETING)
                        self.assertEqual(ref.exclusion_reasons,())
                    else:
                        self.assertIs(ref.disposition,a.D.NONSELECTED)
                        self.assertEqual(ref.exclusion_reasons,(a.X.EXCLUDED_CONSISTENT_PARTIAL_CURRENT,))
                        self.assertNotIn(ref.observation.observation_id,{x for g in q.selected_observation_ids for x in g})

    def test_partial_prior_equal_conflicting_and_alternative_context(self):
        for index,c in enumerate(CONCEPTS):
            for value,state in ((80 if index==0 else 10,a.S.COMPARATIVE_ISSUER_REPORTED_FACTS_ESTABLISHED),
                                (999,a.S.SOURCE_CONFLICT)):
                source=comparative()
                source['facts']['us-gaap'][c]['units']['USD'].extend([
                    row(100 if index==0 else 20,accn=OTHER),prior(value,accn=OTHER)])
                q=self.evaluate(source)
                self.assertIs(q.status,state)
                if state is a.S.SOURCE_CONFLICT:
                    self.assertIn((a.R.COMPETING_PRIOR_REVENUE_VALUES,a.R.COMPETING_PRIOR_OPERATING_INCOME_VALUES)[index],q.reasons)
        source=comparative()
        source['facts']['us-gaap'][CONCEPTS[0]]['units']['USD'].extend([row(accn=OTHER),prior(start='2022-12-31',accn=OTHER)])
        self.failure(self.evaluate(source),a.S.EVIDENCE_UNSUPPORTED,a.R.COMPARATIVE_CONTEXT_UNRESOLVED)

    def test_partial_unresolved_or_incompatible_is_never_silently_ignored(self):
        for changes,reason in (({'fy':None},a.R.COMPARATIVE_CONTEXT_UNRESOLVED),
                ({'accn':'bad'},a.R.COMPARATIVE_CONTEXT_UNRESOLVED),
                ({'filed':None},a.R.COMPARATIVE_CONTEXT_UNRESOLVED),
                ({'fp':'Q4'},a.R.UNSUPPORTED_FILING_CONTEXT),
                ({'segment':{}},a.R.UNSUPPORTED_UNIT_OR_ROW_CONTEXT)):
            source=comparative()
            source['facts']['us-gaap'][CONCEPTS[0]]['units']['USD'].append(row(accn=OTHER,**{k:v for k,v in changes.items() if k!='accn'}))
            if 'accn' in changes:
                source['facts']['us-gaap'][CONCEPTS[0]]['units']['USD'][-1]['accn']=changes['accn']
            self.failure(self.evaluate(source),a.S.EVIDENCE_UNSUPPORTED,reason)

    def test_units_row_extensions_and_values_are_not_guessed(self):
        for index in (0,1):
            for period_index in (0,1):
                for value in (None,True,'NaN','Infinity','123',{}):
                    source=comparative()
                    source['facts']['us-gaap'][CONCEPTS[index]]['units']['USD'][period_index]['val']=value
                    self.failure(self.evaluate(source),a.S.EVIDENCE_UNAVAILABLE,a.R.FINITE_VALUE_UNAVAILABLE)
        for unit in ('EUR','shares'):
            source=comparative()
            source['facts']['us-gaap'][CONCEPTS[0]]['units'][unit]=[row()]
            self.failure(self.evaluate(source),a.S.EVIDENCE_UNSUPPORTED,a.R.UNSUPPORTED_UNIT_OR_ROW_CONTEXT)

    def test_filing_chronology_and_cross_period_metadata_conflicts(self):
        for changes,reason in (({'filed':'2023-12-01'},a.R.INVALID_FILING_CHRONOLOGY),
                ({'filed':'2025-09-01'},a.R.INVALID_FILING_CHRONOLOGY),
                ({'fy':2023},a.R.COMMON_FILING_METADATA_CONFLICT),
                ({'form':'10-K/A'},a.R.COMMON_FILING_METADATA_CONFLICT)):
            source=comparative()
            source['facts']['us-gaap'][CONCEPTS[0]]['units']['USD'][0].update(changes)
            self.failure(self.evaluate(source),a.S.SOURCE_CONFLICT,reason)

    def test_complete_filings_consensus_not_latest_majority_or_amendment(self):
        for index in (0,1):
            for period_index in (0,1):
                source=comparative()
                for c in CONCEPTS:
                    rows=source['facts']['us-gaap'][c]['units']['USD']
                    rows.extend([dict(o,accn=OTHER,form='10-K/A',filed='2025-03-01') for o in deepcopy(rows)])
                changed=source['facts']['us-gaap'][CONCEPTS[index]]['units']['USD'][2+period_index]
                changed['val']=999
                reason=((a.R.COMPETING_PRIOR_REVENUE_VALUES,a.R.COMPETING_PRIOR_OPERATING_INCOME_VALUES),
                        (a.R.COMPETING_CURRENT_REVENUE_VALUES,a.R.COMPETING_CURRENT_OPERATING_INCOME_VALUES))[period_index][index]
                self.failure(self.evaluate(source),a.S.SOURCE_CONFLICT,reason)

    def test_numeric_encoding_order_duplicate_recapture_and_hostile_context_identities(self):
        q=self.evaluate()
        source=comparative()
        for c in CONCEPTS:
            rows=source['facts']['us-gaap'][c]['units']['USD']
            rows.reverse(); rows.append(deepcopy(rows[0]))
        duplicate=self.evaluate(source,timestamp='2025-08-02T00:00:00Z')
        self.assertEqual(q.semantic_id,duplicate.semantic_id)
        self.assertNotEqual(q.evidence_id,duplicate.evidence_id)
        raw=json.dumps(comparative()).encode().replace(b'"val": 100',b'"val": 100.0000')
        encoded=self.evaluate(raw=raw)
        self.assertEqual(q.semantic_id,encoded.semantic_id)
        with localcontext() as ctx:
            ctx.prec=1
            for signal in (Inexact,Rounded,FloatOperation): ctx.traps[signal]=True
            hostile=self.evaluate(raw=raw)
            self.assertEqual(hostile.semantic_id,q.semantic_id)
            self.assertEqual(hostile.evidence_id,encoded.evidence_id)
        source=comparative(r1=101)
        self.assertNotEqual(q.semantic_id,self.evaluate(source).semantic_id)

    def test_closed_enums_and_precedence(self):
        self.assertEqual(len(a.R),25)
        self.assertEqual({r.value for r in a.D},{'SELECTED','NONSELECTED','ORPHAN','UNSUPPORTED','COMPETING'})
        self.assertEqual(len(a.X),2)
        self.assertEqual(a._status((a.R.CURRENT_REVENUE_UNAVAILABLE,a.R.COMPARATIVE_CONTEXT_UNRESOLVED,
                                    a.R.COMPETING_CURRENT_REVENUE_VALUES)),a.S.SOURCE_CONFLICT)
        q=self.evaluate()
        for changes in ({'reasons':('FAKE',)}, {'selected_observation_ids':[]}, {'status':'SOURCE_CONFLICT'}):
            with self.assertRaises(a.ComparativeQualificationError): replace(q,**changes)
        ref=q.observations[0]
        with self.assertRaises(a.ComparativeQualificationError):
            replace(q,observations=(replace(ref,exclusion_reasons=(a.X.EXCLUDED_CONSISTENT_PARTIAL_CURRENT,)),)+q.observations[1:])

    def test_exact_input_live_offline_and_source_locator(self):
        for kwargs in ({'offline':True},{'locator':'https://example.com/companyfacts'}):
            with self.assertRaises(ArchiveError): self.evaluate(**kwargs)
        q=self.evaluate()
        for archive,rid in (({},q.capture_receipt_id),(self.archive,q.capture_receipt_id.upper()),(self.archive,'0'*64)):
            with self.assertRaises(ArchiveError): a.qualify_sec_current_annual_issuer_two_period_revenue_operating_income_v1(archive,rid)
        class ArchiveSubclass(SecArchive): pass
        with self.assertRaises(ArchiveError):
            a.qualify_sec_current_annual_issuer_two_period_revenue_operating_income_v1(ArchiveSubclass(self.root),q.capture_receipt_id)
        # Instance-overridden I/O is not a trusted source boundary.
        self.archive.read_receipt=lambda *_: None
        self.assertIs(self.evaluate().status,a.S.COMPARATIVE_ISSUER_REPORTED_FACTS_ESTABLISHED)

    def test_missing_mismatched_cik_and_malformed_source(self):
        for cik in (None,999):
            source=comparative()
            if cik is None: del source['cik']
            else: source['cik']=cik
            with self.assertRaises(ArchiveError): self.evaluate(source)
        for raw in (b'{}',b'{"cik":123,"cik":123}',b'NaN',b'invalid'):
            with self.assertRaises(ArchiveError): self.evaluate(raw=raw)

    def test_replay_rejects_detached_cloned_forged_subclass_and_every_changed_field(self):
        q=self.evaluate()
        for clone in (replace(q),deepcopy(q),pickle.loads(pickle.dumps(q))):
            with self.assertRaises(ArchiveError): a._verified_comparative_snapshot(clone)
        class Subclass(a.CurrentAnnualIssuerTwoPeriodRevenueOperatingIncomeQualificationV1): pass
        clone=object.__new__(Subclass)
        with self.assertRaises(ArchiveError): a._verified_comparative_snapshot(clone)
        for f in fields(q):
            forged=replace(q)
            object.__setattr__(forged,'_archive_replay_binding',q._archive_replay_binding)
            object.__setattr__(forged,f.name,'FORGED')
            with self.subTest(field=f.name),self.assertRaises(ArchiveError): a._verified_comparative_snapshot(forged)
        with patch.object(type(q),'contract_version','incompatible'):
            with self.assertRaises(ArchiveError): a._verified_comparative_snapshot(q)

    def test_replay_missing_replaced_corrupted_receipt_or_source(self):
        for kind in ('receipts','objects'):
            for corrupt in (False,True):
                q=self.evaluate(timestamp='2025-08-03T00:00:00Z' if corrupt else TIME)
                path=self.root/kind/(q.capture_receipt_id+'.json' if kind=='receipts' else q.source_object_hash)
                if corrupt:
                    path.chmod(0o600); path.write_bytes(b'CORRUPTED')
                else: path.unlink()
                with self.assertRaises(ArchiveError): a._verified_comparative_snapshot(q)
                # Restore only synthetic fixture publication for the next case.
                if path.exists(): path.unlink()

    def test_proven_older_partial_history_excluded_alternative_prior_start_unresolved(self):
        source=comparative()
        source['facts']['us-gaap'][CONCEPTS[0]]['units']['USD'].extend([
            row(accn=OTHER),prior(999,start='2022-01-01',end='2022-12-31',accn=OTHER)])
        q=self.evaluate(source)
        self.assertIs(q.status,a.S.COMPARATIVE_ISSUER_REPORTED_FACTS_ESTABLISHED)
        historical=next(r for r in q.observations if r.observation.end=='2022-12-31')
        self.assertIs(historical.disposition,a.D.NONSELECTED)
        self.assertIn('OUTSIDE_COMPARATIVE_INTERVAL',historical.reasons)
        source['facts']['us-gaap'][CONCEPTS[0]]['units']['USD'][-1].update(start='2022-12-31',end='2023-12-31')
        self.failure(self.evaluate(source),a.S.EVIDENCE_UNSUPPORTED,a.R.COMPARATIVE_CONTEXT_UNRESOLVED)

    def test_no_equal_partial_exclusion_without_coherent_four_cell_reference(self):
        source=payload([row(),row(accn=OTHER,filed='2025-01-31')],[row(20)])
        q=self.evaluate(source)
        self.assertIs(q.status,a.S.EVIDENCE_UNAVAILABLE)
        self.assertFalse(any(r.exclusion_reasons for r in q.observations))
        source=comparative()
        source['facts']['us-gaap'][CONCEPTS[0]]['units']['USD'].extend([prior(81),row(accn=OTHER)])
        q=self.evaluate(source)
        self.assertIs(q.status,a.S.SOURCE_CONFLICT)
        self.assertFalse(any(a.X.EXCLUDED_CONSISTENT_PARTIAL_CURRENT in r.exclusion_reasons for r in q.observations))

    def test_intrafiling_current_value_conflict_never_selects_prior(self):
        source=comparative()
        source['facts']['us-gaap'][CONCEPTS[0]]['units']['USD'].append(row(101))
        q=self.failure(self.evaluate(source),a.S.SOURCE_CONFLICT,a.R.COMPETING_CURRENT_REVENUE_VALUES)
        self.assertIsNone(q.prior_period_start)
        self.assertFalse(any(r.value.startswith('PRIOR_') for r in q.reasons))

    def test_only_reviewed_concepts_namespace_and_exact_unit(self):
        source=comparative()
        source['facts']['ifrs-full']=source['facts'].pop('us-gaap')
        self.failure(self.evaluate(source),a.S.EVIDENCE_UNAVAILABLE,a.R.NO_APPARENT_ANNUAL_PERIOD)
        source=comparative()
        source['facts']['us-gaap']['Revenues']=source['facts']['us-gaap'].pop(CONCEPTS[0])
        self.failure(self.evaluate(source),a.S.EVIDENCE_UNAVAILABLE,a.R.CURRENT_REVENUE_UNAVAILABLE)
        source=comparative()
        source['facts']['us-gaap'][CONCEPTS[0]]['units']['usd']=source['facts']['us-gaap'][CONCEPTS[0]]['units'].pop('USD')
        self.failure(self.evaluate(source),a.S.EVIDENCE_UNSUPPORTED,a.R.UNSUPPORTED_UNIT_OR_ROW_CONTEXT)

    def test_invalid_fiscal_year_and_accession_and_period_metadata(self):
        for changes in ({'fy':True},{'fy':'2024'},{'accn':None},{'filed':'bad'},
                        {'start':'2024-2-01'},{'end':'2024-02-30'}):
            source=comparative()
            source['facts']['us-gaap'][CONCEPTS[0]]['units']['USD'][-1].update(changes)
            self.failure(self.evaluate(source),a.S.EVIDENCE_UNSUPPORTED)

    def test_same_length_source_corruption_and_valid_receipt_replacement_rejected(self):
        q=self.evaluate()
        path=self.root/'objects'/q.source_object_hash
        raw=path.read_bytes()
        path.chmod(0o600); path.write_bytes(raw.replace(b'100',b'101'))
        self.assertEqual(path.stat().st_size,q.source_byte_length)
        with self.assertRaises(ArchiveError): a._verified_comparative_snapshot(q)
        path.write_bytes(raw)
        receipt=self.archive.read_receipt(q.capture_receipt_id)
        changed=replace(receipt,captured_at='2025-08-02T00:00:00Z')
        path=self.root/'receipts'/(q.capture_receipt_id+'.json')
        path.chmod(0o600); path.write_bytes(changed.to_bytes())
        with self.assertRaises(ArchiveError): a._verified_comparative_snapshot(q)

    def test_complete_support_partition_with_equal_multiple_filings_and_duplicates(self):
        source=comparative()
        for c in CONCEPTS:
            rows=source['facts']['us-gaap'][c]['units']['USD']
            rows.extend([dict(o,accn=OTHER,filed='2025-03-01',form='10-K/A') for o in deepcopy(rows)])
            rows.append(deepcopy(rows[0]))
        q=self.evaluate(source)
        self.assertIs(q.status,a.S.COMPARATIVE_ISSUER_REPORTED_FACTS_ESTABLISHED)
        self.assertEqual(len(q.supporting_filings),2)
        for f in q.supporting_filings:
            self.assertTrue(all(f.cell_observation_ids))
            for ids in f.cell_observation_ids:
                refs=[r for r in q.observations if r.observation.observation_id in ids]
                self.assertTrue(all(r.observation.accession==f.accession and r.disposition is a.D.SELECTED for r in refs))
        self.assertEqual({oid for group in q.selected_observation_ids for oid in group},
                         {r.observation.observation_id for r in q.observations if r.disposition is a.D.SELECTED})

    def test_read_only_no_network_no_new_capture(self):
        q=self.evaluate()
        before={str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        with (patch.object(socket,'socket',side_effect=AssertionError('network')),
              patch.object(SecArchive,'_capture',side_effect=AssertionError('write'))):
            replay=a._verified_comparative_snapshot(q)
        self.assertEqual(q,replay)
        after={str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before,after)


class IndependentReviewScenarioTests(D1Fixture):
    """Exact T1–T20 configurations recovered from the owner's review reference."""

    def test_t1_t2_earlier_revenue_and_later_amended_income_conflict(self):
        for concept,value,filed,form,reason in (
            (CONCEPTS[0],110,'2025-01-31','10-K',a.R.COMPETING_CURRENT_REVENUE_VALUES),
            (CONCEPTS[1],21,'2025-03-01','10-K/A',a.R.COMPETING_CURRENT_OPERATING_INCOME_VALUES)):
            source=comparative()
            source['facts']['us-gaap'][concept]['units']['USD'].append(row(value,accn=OTHER,filed=filed,form=form))
            q=self.evaluate(source)
            self.assertIs(q.status,a.S.SOURCE_CONFLICT)
            self.assertIn(reason,q.reasons)

    def test_t3_t15_consistent_partial_current_exclusion(self):
        source=comparative()
        source['facts']['us-gaap'][CONCEPTS[0]]['units']['USD'].append(row(accn=OTHER,filed='2025-01-31'))
        q=self.evaluate(source)
        self.assertIs(q.status,a.S.COMPARATIVE_ISSUER_REPORTED_FACTS_ESTABLISHED)
        ref=next(r for r in q.observations if r.observation.accession==OTHER)
        self.assertIs(ref.disposition,a.D.NONSELECTED)
        self.assertEqual(ref.exclusion_reasons,(a.X.EXCLUDED_CONSISTENT_PARTIAL_CURRENT,))

    def test_t4_missing_current_start_context_unresolved(self):
        source=comparative()
        source['facts']['us-gaap'][CONCEPTS[0]]['units']['USD'].append(row(accn=OTHER,start=None))
        q=self.evaluate(source)
        self.assertIs(q.status,a.S.EVIDENCE_UNSUPPORTED)
        self.assertIn(a.R.COMPARATIVE_CONTEXT_UNRESOLVED,q.reasons)
        self.assertFalse(any(r.value.startswith('PRIOR_') for r in q.reasons))

    def test_t5_t16_historical_only_alternative_prior_excluded(self):
        source=comparative()
        for c in CONCEPTS:
            source['facts']['us-gaap'][c]['units']['USD'].append(prior(999,accn=OTHER,fy=2023,start='2022-12-31'))
        q=self.evaluate(source)
        self.assertIs(q.status,a.S.COMPARATIVE_ISSUER_REPORTED_FACTS_ESTABLISHED)
        self.assertNotIn(a.R.PRIOR_ANNUAL_INTERVAL_AMBIGUOUS,q.reasons)
        self.assertTrue(all(r.disposition is a.D.NONSELECTED and r.exclusion_reasons ==
            (a.X.EXCLUDED_DIFFERENT_FILING_VINTAGE_PRIOR_ONLY,) for r in q.observations
            if r.observation.accession==OTHER))

    def test_t6_two_complete_prior_starts_ambiguous(self):
        source=comparative()
        for index,c in enumerate(CONCEPTS):
            source['facts']['us-gaap'][c]['units']['USD'].extend([
                prior(80 if index==0 else 10,accn=OTHER,start='2022-12-31'),
                row(100 if index==0 else 20,accn=OTHER)])
        q=self.evaluate(source)
        self.assertIs(q.status,a.S.EVIDENCE_UNSUPPORTED)
        self.assertIn(a.R.PRIOR_ANNUAL_INTERVAL_AMBIGUOUS,q.reasons)

    def test_t7_t8_gap_and_overlap_rejected(self):
        for start,end,reason in (('2022-01-01','2022-12-31',a.R.PERIODS_NOT_IMMEDIATELY_ADJACENT),
                                ('2023-02-01','2024-01-31',a.R.PERIODS_OVERLAP)):
            source=comparative()
            for c in CONCEPTS:
                source['facts']['us-gaap'][c]['units']['USD'][0].update(start=start,end=end)
            q=self.evaluate(source)
            self.assertIs(q.status,a.S.EVIDENCE_UNSUPPORTED)
            self.assertIn(reason,q.reasons)

    def test_t9_no_predecessor_unavailable(self):
        q=self.evaluate(payload())
        self.assertEqual(q.reasons,(a.R.ADJACENT_PRIOR_PERIOD_NOT_OBSERVED,))
        self.assertIs(q.status,a.S.EVIDENCE_UNAVAILABLE)

    def test_t10_four_cells_in_separate_filings_never_assembled(self):
        source=comparative()
        for c in CONCEPTS:
            source['facts']['us-gaap'][c]['units']['USD'][0].update(accn=OTHER,fy=2023)
        q=self.evaluate(source)
        self.assertEqual(q.reasons,(a.R.NO_COMMON_FOUR_CELL_ACCESSION,))
        self.assertIs(q.status,a.S.EVIDENCE_UNAVAILABLE)
        self.assertEqual(q.selected_observation_ids,((),)*4)

    def test_t11_partial_f_prior_value_conflict(self):
        source=comparative()
        source['facts']['us-gaap'][CONCEPTS[0]]['units']['USD'].extend([row(accn=OTHER),prior(81,accn=OTHER)])
        q=self.evaluate(source)
        self.assertIs(q.status,a.S.SOURCE_CONFLICT)
        self.assertIn(a.R.COMPETING_PRIOR_REVENUE_VALUES,q.reasons)

    def test_t12_current_interval_ambiguity_no_prior_reasons(self):
        source=comparative()
        source['facts']['us-gaap'][CONCEPTS[0]]['units']['USD'].append(row(start='2024-01-02',accn=OTHER))
        q=self.evaluate(source)
        self.assertEqual(q.reasons,(a.R.CURRENT_ANNUAL_INTERVAL_AMBIGUOUS,))
        self.assertIs(q.status,a.S.EVIDENCE_UNSUPPORTED)

    def test_t13_disjoint_current_accessions_no_prior_reasons(self):
        q=self.evaluate(payload([row()],[row(20,accn=OTHER)]))
        self.assertEqual(q.reasons,(a.R.NO_COMMON_CURRENT_ACCESSION,))
        self.assertIs(q.status,a.S.EVIDENCE_UNAVAILABLE)

    def test_t14_common_accession_filing_date_conflict(self):
        q=self.evaluate(payload([row()],[row(20,filed='2025-02-02')]))
        self.assertEqual(q.reasons,(a.R.COMMON_FILING_METADATA_CONFLICT,))
        self.assertIs(q.status,a.S.SOURCE_CONFLICT)

    def test_t17_incorrect_source_locator_and_t18_offline_rejected(self):
        for kwargs in ({'locator':'https://example.com/incorrect'},{'offline':True}):
            with self.assertRaises(ArchiveError): self.evaluate(**kwargs)

    def test_t19_exclusion_is_not_a_disposition(self):
        q=self.evaluate()
        ref=replace(q.observations[0],disposition='EXCLUDED_CONSISTENT_PARTIAL_CURRENT')
        with self.assertRaises(a.ComparativeQualificationError):
            replace(q,observations=(ref,)+q.observations[1:])

    def test_t20_isolated_identity_projection_and_forged_result_replay_rejection(self):
        # Isolated identity-function exercise; altered public projections are
        # NOT legitimate source qualifications and must fail native replay.
        source=comparative()
        source['facts']['us-gaap'][CONCEPTS[0]]['units']['USD'].append(row(accn=OTHER))
        q=self.evaluate(source)
        changed=replace(q,observations=tuple(replace(r,exclusion_reasons=()) if
            r.observation.accession==OTHER else r for r in q.observations))
        self.assertEqual(q.semantic_id,changed.semantic_id)
        self.assertNotEqual(q.evidence_id,changed.evidence_id)
        object.__setattr__(changed,'_archive_replay_binding',q._archive_replay_binding)
        with self.assertRaises(ArchiveError): a._verified_comparative_snapshot(changed)
