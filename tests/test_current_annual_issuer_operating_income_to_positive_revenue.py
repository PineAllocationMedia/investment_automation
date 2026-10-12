"""Fictional replay/forgery regressions; no authentic issuer applicability claim."""
from copy import deepcopy
from dataclasses import asdict, fields, replace, FrozenInstanceError
from decimal import Decimal, localcontext
import json
from pathlib import Path
import pickle
import socket
import tempfile
import unittest
from unittest.mock import patch

from economic_facts import sec_current_annual_issuer_revenue_operating_income as q
from economic_facts import sec_current_annual_reported_fact_research_candidate as research
from economic_facts import sec_current_annual_revenue_operating_income as legacy_q
from economic_facts.sec_archive import ArchiveError, SecArchive
from src import current_annual_issuer_operating_income_to_positive_revenue as d
from src import current_annual_operating_income_to_positive_revenue as legacy_d
from tests.test_sec_current_annual_reported_fact_research_candidate import CIK, TIME, row, payload, OTHER

analyze = d.analyze_current_annual_issuer_operating_income_to_positive_revenue_v1
qualify = q.qualify_sec_current_annual_issuer_revenue_operating_income_v1


class IssuerDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.archive = SecArchive(self.root)

    def evidence(self, revenue='100', income='20', *, source=None, timestamp=TIME):
        if source is None:
            source = payload([row('REVENUE')], [row('INCOME')])
        raw = json.dumps(source, sort_keys=True).replace('"REVENUE"', revenue).replace('"INCOME"', income).encode()
        receipt = self.archive._capture_live(raw, cik=CIK, captured_at=timestamp)
        return qualify(self.archive, receipt.receipt_id)

    def bound_forge(self, original, **changes):
        # Deliberate bypass of frozen storage. Retain real binding so rejection
        # must come from independent replay, not just a missing capability.
        forged = replace(original)
        object.__setattr__(forged, '_archive_replay_binding', original._archive_replay_binding)
        for name, value in changes.items():
            object.__setattr__(forged, name, value)
        return forged

    def test_exact_signed_reduced_ratios_and_frozen_result(self):
        for revenue, income, expected in [('100','20',(1,5)), ('100','-20',(-1,5)),
                ('100','0',(0,1)), ('3','1',(1,3)), ('1e-100','-1',(-10**100,1)),
                ('123456789012345678901234567890.123','246913578024691357802469135780.246',(2,1))]:
            with self.subTest(revenue=revenue, income=income):
                result = analyze(self.evidence(revenue, income))
                self.assertIs(result.status, d.S.AVAILABLE)
                self.assertEqual(result.reasons, ())
                ratio = result.operating_income_to_revenue_ratio
                self.assertEqual((ratio.numerator, ratio.denominator), expected)
                with self.assertRaises(FrozenInstanceError):
                    result.source_cik = '0000000999'
                self.assertEqual(result.analysis_kind, legacy_d._ANALYSIS_KIND)

    def test_zero_negative_revenue_not_applicable(self):
        for revenue, reason in [('0', d.R.REVENUE_ZERO_DENOMINATOR),
                ('-0.0', d.R.REVENUE_ZERO_DENOMINATOR),
                ('-100', d.R.REVENUE_NEGATIVE_NOT_POSITIVE_DENOMINATOR)]:
            evidence = self.evidence(revenue)
            self.assertIs(evidence.status, q.S.PAIRED_ISSUER_REPORTED_FACTS_ESTABLISHED)
            result = analyze(evidence)
            self.assertIs(result.status, d.S.NOT_APPLICABLE)
            self.assertEqual(result.reasons, (reason,))
            self.assertIsNone(result.operating_income_to_revenue_ratio)

    def test_all_nonpositive_status_projections(self):
        cases = [(payload([], []), d.S.UNAVAILABLE, d.R.UPSTREAM_EVIDENCE_UNAVAILABLE),
                 (payload([row(start='2024-07-01')], [row(20)]), d.S.UNSUPPORTED,
                  d.R.UPSTREAM_EVIDENCE_UNSUPPORTED),
                 (payload([row(),row(999)], [row(20)]), d.S.SOURCE_CONFLICT,
                  d.R.UPSTREAM_SOURCE_CONFLICT)]
        for source, status, reason in cases:
            evidence = self.evidence(source=source)
            result = analyze(evidence)
            self.assertIs(result.status, status)
            self.assertEqual(result.reasons, (reason,))
            self.assertIsNone(result.operating_income_to_revenue_ratio)
            self.assertEqual(result.upstream_reasons, evidence.reasons)

    def test_replay_once_source_snapshot_not_untrusted_input(self):
        evidence = self.evidence()
        with patch.object(SecArchive, 'read_object', autospec=True,
                side_effect=SecArchive.read_object) as read, \
             patch.object(q, 'extract_revenue_operating_income',
                wraps=q.extract_revenue_operating_income) as extract, \
             patch.object(q, '_qualify_extraction', wraps=q._qualify_extraction) as adjudicate:
            result = analyze(evidence)
        self.assertEqual(read.call_count, 1)
        self.assertEqual(extract.call_count, 1)
        self.assertEqual(adjudicate.call_count, 1)
        self.assertEqual(result.upstream_qualification_evidence_id, evidence.evidence_id)

    def test_detached_replace_copy_pickle_and_dict_rejected(self):
        evidence = self.evidence()
        serialized = pickle.dumps(evidence)
        public = asdict(evidence)
        self.assertNotIn('_archive_replay_binding', public)
        self.assertNotIn(str(self.root).encode(), serialized)
        self.assertNotIn(str(self.root), repr(evidence))
        self.assertNotIn('archive', {f.name for f in fields(evidence)})
        for value in (replace(evidence), deepcopy(evidence), pickle.loads(serialized), public, None):
            with self.subTest(kind=type(value)):
                with self.assertRaises((ArchiveError, d.IssuerDiagnosticError)):
                    analyze(value)
        restored = qualify(self.archive, evidence.capture_receipt_id)
        self.assertEqual(analyze(restored), analyze(evidence))

    def test_forged_exact_type_with_recomputed_hashes_rejected(self):
        evidence = self.evidence()
        for changes in ({'revenue': Decimal(200)}, {'operating_income': Decimal(90)},
                {'source_cik': '0000000999'}, {'source_byte_length': evidence.source_byte_length + 1},
                {'extraction_inventory_id': '0'*64}, {'source_locator': 'false'},
                {'captured_at': '2025-08-02T00:00:00Z'}, {'observations': ()},
                {'adjudicated_filings': ()}, {'supporting_filings': ()},
                {'selected_revenue_observation_ids': ()}):
            forged = self.bound_forge(evidence, **changes)
            # IDs derive from altered fields: this is not a mere stale-hash test.
            self.assertEqual(len(forged.semantic_id), 64)
            self.assertEqual(len(forged.evidence_id), 64)
            with self.subTest(changes=changes), self.assertRaises((ArchiveError, d.IssuerDiagnosticError)):
                analyze(forged)

    def test_omitted_newer_adverse_inventory_cannot_be_promoted(self):
        source = payload([row(),row(200,start='2025-01-02',end='2025-12-31',filed='2026-02-01')], [row(20)])
        adverse = self.evidence(source=source,timestamp='2026-08-01T00:00:00Z')
        good = self.evidence()
        forged = self.bound_forge(good, capture_receipt_id=adverse.capture_receipt_id,
            source_object_hash=adverse.source_object_hash,
            captured_at=adverse.captured_at, source_byte_length=adverse.source_byte_length)
        object.__setattr__(forged, '_archive_replay_binding', adverse._archive_replay_binding)
        self.assertEqual(len(forged.evidence_id),64)
        with self.assertRaises((ArchiveError, d.IssuerDiagnosticError)):
            analyze(forged)

    def test_nested_mutations_and_permissive_equal_types_rejected(self):
        evidence = self.evidence()
        observation = evidence.observations[0]
        alterations = [replace(observation, value=Decimal(999)),
                      replace(observation, exclusion_reasons=('HIDDEN',)),
                      replace(observation, fy=True), replace(observation, value=100)]
        for altered in alterations:
            forged = self.bound_forge(evidence, observations=(altered,)+evidence.observations[1:])
            with self.assertRaises((ArchiveError, d.IssuerDiagnosticError)):
                analyze(forged)
        for field, value in [('status', evidence.status.value), ('reasons', []),
                ('source_byte_length', str(evidence.source_byte_length)),
                ('conflict_values', ((), [])), ('revenue', 100),
                ('revenue', Decimal('NaN'))]:
            with self.subTest(field=field), self.assertRaises((ArchiveError, d.IssuerDiagnosticError)):
                analyze(self.bound_forge(evidence, **{field:value}))

    def test_unknown_state_and_forged_nonpositive_result_rejected(self):
        good = self.evidence()
        for status, reasons in [('FUTURE_STATE', ()),
                (q.S.EVIDENCE_UNAVAILABLE, (q.R.REVENUE_UNAVAILABLE,)),
                (q.S.SOURCE_CONFLICT, (q.R.COMMON_FILING_METADATA_CONFLICT,))]:
            forged = self.bound_forge(good, status=status, reasons=reasons, revenue=None,
                operating_income=None, supporting_filings=(), selected_revenue_observation_ids=(),
                selected_operating_income_observation_ids=())
            with self.assertRaises((ArchiveError, d.IssuerDiagnosticError)):
                analyze(forged)

    def test_incompatible_contract_and_subclass_rejected(self):
        evidence = self.evidence()
        for name, value in [('contract_version','future'), ('authority','PROMOTED'),
                ('limitations',()), ('concepts',tuple(reversed(q.CONCEPTS))),
                ('unit','CAD'), ('qualification_version','future')]:
            with patch.object(type(evidence),name,value), self.assertRaises((ArchiveError, d.IssuerDiagnosticError)):
                analyze(evidence)
        class Foreign(type(evidence)):
            pass
        foreign = Foreign(**{f.name:getattr(evidence,f.name) for f in fields(evidence)})
        with self.assertRaises((ArchiveError, d.IssuerDiagnosticError)):
            analyze(foreign)

    def test_research_and_legacy_isolation_both_directions(self):
        evidence = self.evidence()
        candidate = research.evaluate_sec_current_annual_reported_fact_research_candidate(
            self.archive,evidence.capture_receipt_id)
        with self.assertRaises((ArchiveError, d.IssuerDiagnosticError)):
            analyze(candidate)
        # Exact legacy type is rejected before accessing any fields.
        legacy = object.__new__(legacy_q.CurrentAnnualRevenueOperatingIncomeQualification)
        with self.assertRaises((ArchiveError, d.IssuerDiagnosticError)):
            analyze(legacy)
        with self.assertRaises(legacy_d.CurrentAnnualOperatingIncomeToPositiveRevenueError):
            legacy_d.analyze_current_annual_operating_income_to_positive_revenue(evidence)
        self.assertEqual(candidate.authority,'CURRENT_CAPTURE_RESEARCH_CANDIDATE_ONLY')
        self.assertNotEqual(candidate.semantic_id,evidence.semantic_id)

    def test_corrupt_object_after_factory_fails_without_cached_acceptance(self):
        evidence = self.evidence()
        path=self.root/'objects'/evidence.source_object_hash
        raw=path.read_bytes(); path.chmod(0o600)
        for altered in (raw+b' ', b'x'+raw[1:]):
            path.write_bytes(altered)
            with self.assertRaises((ArchiveError, d.IssuerDiagnosticError)):
                analyze(evidence)
        path.write_bytes(raw)
        self.assertIs(analyze(evidence).status,d.S.AVAILABLE)

    def test_wrong_missing_corrupt_or_replaced_receipt(self):
        evidence = self.evidence()
        other = self.evidence('200')
        with self.assertRaises((ArchiveError, d.IssuerDiagnosticError)):
            analyze(self.bound_forge(evidence,capture_receipt_id=other.capture_receipt_id))
        forged = self.bound_forge(evidence)
        object.__setattr__(forged,'_archive_replay_binding',other._archive_replay_binding)
        with self.assertRaises((ArchiveError, d.IssuerDiagnosticError)):
            analyze(forged)
        path=self.root/'receipts'/(evidence.capture_receipt_id+'.json')
        raw=path.read_bytes(); path.chmod(0o600)
        replacement=(self.root/'receipts'/(other.capture_receipt_id+'.json')).read_bytes()
        for altered in (b'{}',replacement):
            path.write_bytes(altered)
            with self.assertRaises((ArchiveError, d.IssuerDiagnosticError)):
                analyze(evidence)
        path.unlink()
        with self.assertRaises((ArchiveError, d.IssuerDiagnosticError)):
            analyze(evidence)
        path.write_bytes(raw)
        self.assertIs(analyze(evidence).status,d.S.AVAILABLE)

    def test_missing_binding_and_archive_loss(self):
        evidence=self.evidence()
        for binding in (None,{},(self.archive,evidence.capture_receipt_id)):
            forged=self.bound_forge(evidence)
            object.__setattr__(forged,'_archive_replay_binding',binding)
            with self.assertRaises((ArchiveError, d.IssuerDiagnosticError)):
                analyze(forged)
        (self.root/'objects'/evidence.source_object_hash).unlink()
        with self.assertRaises((ArchiveError, d.IssuerDiagnosticError)):
            analyze(evidence)

    def test_unsafe_hardlink_and_symlink_at_consumption(self):
        import os
        evidence=self.evidence()
        path=self.root/'objects'/evidence.source_object_hash
        backup=self.root/'backup'
        os.link(path,backup)
        with self.assertRaises((ArchiveError, d.IssuerDiagnosticError)):
            analyze(evidence)
        backup.unlink()
        path.rename(backup); path.symlink_to(backup)
        with self.assertRaises((ArchiveError, d.IssuerDiagnosticError)):
            analyze(evidence)

    def test_recapture_semantics_evidence_and_independent_replay(self):
        a=self.evidence(); b=self.evidence(timestamp='2025-08-02T00:00:00Z')
        x,y=analyze(a),analyze(b)
        self.assertEqual(x.semantic_id,y.semantic_id)
        self.assertNotEqual(x.evidence_id,y.evidence_id)
        independent=qualify(SecArchive(self.root),a.capture_receipt_id)
        self.assertEqual(analyze(independent),x)
        self.assertEqual(analyze(independent).evidence_id,x.evidence_id)

    def test_equivalent_decimal_forms_and_different_economics(self):
        results=[analyze(self.evidence(r,i)) for r,i in [('100','20'),('100.00','20.0'),('1E2','2E1')]]
        self.assertEqual(len({v.semantic_id for v in results}),1)
        doubled=analyze(self.evidence('200','40'))
        self.assertEqual(doubled.operating_income_to_revenue_ratio,results[0].operating_income_to_revenue_ratio)
        self.assertNotEqual(doubled.semantic_id,results[0].semantic_id)

    def test_hostile_decimal_context_qualification_replay_and_identity(self):
        evidence=self.evidence('12345678901234567890.123456789','-9876543210987654321.987654321')
        normal=analyze(evidence)
        with localcontext() as ctx:
            ctx.prec=1; ctx.Emax=1; ctx.Emin=-1
            for signal in ctx.traps:
                ctx.traps[signal]=True
            replay=qualify(self.archive,evidence.capture_receipt_id)
            hostile=analyze(replay)
            self.assertEqual(hostile.semantic_id,normal.semantic_id)
            self.assertEqual(hostile.evidence_id,normal.evidence_id)
            self.assertEqual(hostile.operating_income_to_revenue_ratio,normal.operating_income_to_revenue_ratio)

    def test_read_only_no_callback_and_original_archive_instance_override(self):
        evidence=self.evidence()
        before={str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        # Caller instance methods must not be used as validation callbacks.
        self.archive.read_object=lambda *a: (_ for _ in ()).throw(AssertionError('override'))
        with patch.object(socket,'socket',side_effect=AssertionError('network')), \
             patch.object(SecArchive,'capture',side_effect=AssertionError('capture')), \
             patch.object(SecArchive,'_capture_live',side_effect=AssertionError('capture')):
            self.assertIs(analyze(evidence).status,d.S.AVAILABLE)
            self.assertEqual(qualify(self.archive,evidence.capture_receipt_id),evidence)
        after={str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before,after)

    def test_matching_public_reconstruction_requires_replay(self):
        evidence=self.evidence()
        reconstructed=self.bound_forge(evidence)
        self.assertEqual(analyze(reconstructed),analyze(evidence))
        with patch.object(SecArchive,'read_object',side_effect=ArchiveError('missing')):
            with self.assertRaises((ArchiveError, d.IssuerDiagnosticError)):
                analyze(reconstructed)


if __name__ == '__main__':
    unittest.main()
