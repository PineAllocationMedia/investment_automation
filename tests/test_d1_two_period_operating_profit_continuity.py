"""Contract B adversarial synthetic mechanics; no authentic SEC execution."""
from copy import deepcopy
from dataclasses import asdict, replace
from decimal import Decimal, localcontext, Inexact, Rounded, FloatOperation
import json
import pickle
import socket
from unittest.mock import patch

from economic_facts.sec_archive import ArchiveError, SecArchive
from economic_facts.sec_revenue_operating_income import CONCEPTS
from economic_facts import sec_current_annual_issuer_revenue_operating_income as legacy
from src import d1_two_period_operating_profit_continuity as b
from tests.sec_d1_two_period_fixtures import D1Fixture, comparative, row, payload, OTHER, a


class D1DiagnosticTests(D1Fixture):
    def analyze(self, source=None, **kwargs):
        return b.analyze_d1_two_period_operating_profit_continuity_v1(self.evaluate(source, **kwargs))

    def fraction(self, ratio, numerator, denominator):
        self.assertEqual((ratio.numerator, ratio.denominator),(numerator,denominator))

    def test_exact_ratios_difference_direction_and_bound_provenance(self):
        q=self.evaluate()
        d=b.analyze_d1_two_period_operating_profit_continuity_v1(q)
        self.assertIs(d.status,b.S.AVAILABLE)
        self.assertEqual(d.reasons,())
        self.fraction(d.prior_operating_income_to_revenue_ratio,1,8)
        self.fraction(d.current_operating_income_to_revenue_ratio,1,5)
        self.fraction(d.ratio_difference,3,40)
        self.assertIs(d.ratio_direction,b.RatioDirection.INCREASED)
        self.assertIs(d.operating_income_sign_continuity,b.OperatingIncomeContinuity.POSITIVE_IN_BOTH_PERIODS)
        self.assertEqual(d.upstream_qualification_semantic_id,q.semantic_id)
        self.assertEqual(d.upstream_qualification_evidence_id,q.evidence_id)
        self.assertEqual((d.prior_revenue,d.prior_operating_income,d.current_revenue,d.current_operating_income),
                         (q.prior_revenue,q.prior_operating_income,q.current_revenue,q.current_operating_income))
        self.assertEqual(d.temporal_mode,'CURRENT_CAPTURE_BOUND_ONLY')
        self.assertFalse(any(k in asdict(d) for k in ('observations','score','recommendation','allocation','confidence')))

    def test_supplied_microsoft_arithmetic_oracle_only_on_fictional_fixture(self):
        # Deliberately fictional issuer and synthetic rows: oracle arithmetic
        # validation only, NEVER an executed Microsoft source qualification.
        d=self.analyze(comparative(281724000000,128528000000,331839000000,155237000000))
        self.fraction(d.prior_operating_income_to_revenue_ratio,32132,70431)
        self.fraction(d.current_operating_income_to_revenue_ratio,155237,331839)
        self.fraction(d.ratio_difference,90282133,7790584203)
        self.assertIs(d.ratio_direction,b.RatioDirection.INCREASED)

    def test_zero_and_negative_revenue_each_and_both_no_partial_ratios(self):
        for r0 in (0,-100,100):
            for r1 in (0,-200,200):
                if r0>0 and r1>0: continue
                d=self.analyze(comparative(r0,-1,r1,0))
                self.assertIs(d.status,b.S.NOT_APPLICABLE)
                expected=[]
                if r0<=0:
                    expected.append(b.R.PRIOR_REVENUE_ZERO_DENOMINATOR if r0==0 else b.R.PRIOR_REVENUE_NEGATIVE_NOT_POSITIVE_DENOMINATOR)
                if r1<=0:
                    expected.append(b.R.CURRENT_REVENUE_ZERO_DENOMINATOR if r1==0 else b.R.CURRENT_REVENUE_NEGATIVE_NOT_POSITIVE_DENOMINATOR)
                self.assertEqual(d.reasons,tuple(sorted(expected,key=lambda r:r.value)))
                self.assertEqual((d.prior_operating_income_to_revenue_ratio,
                    d.current_operating_income_to_revenue_ratio,d.ratio_difference,d.ratio_direction),(None,)*4)
                self.assertIs(d.prior_operating_income_sign,b.OperatingIncomeSign.NEGATIVE)
                self.assertIs(d.current_operating_income_sign,b.OperatingIncomeSign.ZERO)
                self.assertIs(d.operating_income_sign_continuity,b.OperatingIncomeContinuity.POSITIVE_IN_NEITHER_PERIOD)

    def test_all_nine_sign_pairs_and_continuity_without_inferred_quality(self):
        signs={-1:b.OperatingIncomeSign.NEGATIVE,0:b.OperatingIncomeSign.ZERO,1:b.OperatingIncomeSign.POSITIVE}
        expected={(True,True):b.OperatingIncomeContinuity.POSITIVE_IN_BOTH_PERIODS,
                  (True,False):b.OperatingIncomeContinuity.POSITIVE_ONLY_IN_PRIOR_PERIOD,
                  (False,True):b.OperatingIncomeContinuity.POSITIVE_ONLY_IN_CURRENT_PERIOD,
                  (False,False):b.OperatingIncomeContinuity.POSITIVE_IN_NEITHER_PERIOD}
        for o0 in signs:
            for o1 in signs:
                d=self.analyze(comparative(o0=o0,o1=o1))
                self.assertIs(d.prior_operating_income_sign,signs[o0])
                self.assertIs(d.current_operating_income_sign,signs[o1])
                self.assertIs(d.operating_income_sign_continuity,expected[o0>0,o1>0])

    def test_increased_decreased_unchanged_signed_ratios_and_canonical_zero(self):
        for o0,o1,direction,num,den in ((20,20,b.RatioDirection.UNCHANGED,0,1),
            (20,10,b.RatioDirection.DECREASED,-1,10),(-20,-10,b.RatioDirection.INCREASED,1,10),
            (0,0,b.RatioDirection.UNCHANGED,0,1)):
            d=self.analyze(comparative(100,o0,100,o1))
            self.assertIs(d.ratio_direction,direction)
            self.fraction(d.ratio_difference,num,den)
            self.assertGreater(d.prior_operating_income_to_revenue_ratio.denominator,0)

    def test_exact_fractional_decimal_and_hostile_context(self):
        raw=json.dumps(comparative()).encode()
        for old,new in ((b'"val": 80',b'"val": 3.000'),(b'"val": 100',b'"val": 0.75'),
                        (b'"val": 10',b'"val": -0.125'),(b'"val": 20',b'"val": 0.125')):
            raw=raw.replace(old,new)
        d=self.analyze(raw=raw)
        with localcontext() as ctx:
            ctx.prec=1
            for signal in (Inexact,Rounded,FloatOperation): ctx.traps[signal]=True
            hostile=self.analyze(raw=raw)
            self.assertEqual((hostile.semantic_id,hostile.evidence_id),(d.semantic_id,d.evidence_id))
            self.fraction(hostile.prior_operating_income_to_revenue_ratio,-1,24)
            self.fraction(hostile.current_operating_income_to_revenue_ratio,1,6)
            self.fraction(hostile.ratio_difference,5,24)

    def test_nonestablished_upstream_mapping_no_facts_signs_periods_ratios(self):
        sources=[(payload(),b.S.UNAVAILABLE,b.R.UPSTREAM_EVIDENCE_UNAVAILABLE),
                 (comparative(fp='Q4'),b.S.UNSUPPORTED,b.R.UPSTREAM_EVIDENCE_UNSUPPORTED)]
        conflict=comparative()
        conflict['facts']['us-gaap'][CONCEPTS[0]]['units']['USD'].append(row(999,accn=OTHER))
        sources.append((conflict,b.S.SOURCE_CONFLICT,b.R.UPSTREAM_SOURCE_CONFLICT))
        for source,state,reason in sources:
            q=self.evaluate(source)
            d=b.analyze_d1_two_period_operating_profit_continuity_v1(q)
            self.assertIs(d.status,state)
            self.assertEqual(d.reasons,(reason,))
            self.assertEqual(d.upstream_status,q.status)
            self.assertEqual(d.upstream_reasons,q.reasons)
            for key in ('prior_period_start','prior_period_end','current_period_start','current_period_end',
                'prior_revenue','prior_operating_income','current_revenue','current_operating_income',
                'prior_operating_income_sign','current_operating_income_sign','operating_income_sign_continuity',
                'prior_operating_income_to_revenue_ratio','current_operating_income_to_revenue_ratio',
                'ratio_difference','ratio_direction'):
                self.assertIsNone(getattr(d,key))

    def test_replay_before_status_or_arithmetic_for_every_upstream_state(self):
        for source in (comparative(),payload(),comparative(fp='Q4'),comparative(filed='2025-09-01')):
            q=self.evaluate(source)
            path=self.root/'objects'/q.source_object_hash
            path.unlink()
            with self.assertRaises(ArchiveError): b.analyze_d1_two_period_operating_profit_continuity_v1(q)

    def test_rejects_legacy_dictionary_none_subclasses_and_detached(self):
        q=self.evaluate()
        rid=q.capture_receipt_id
        single=legacy.qualify_sec_current_annual_issuer_revenue_operating_income_v1(self.archive,rid)
        for wrong in (single,{},None,True,asdict(q)):
            with self.assertRaises(b.D1DiagnosticError): b.analyze_d1_two_period_operating_profit_continuity_v1(wrong)
        class Subclass(a.CurrentAnnualIssuerTwoPeriodRevenueOperatingIncomeQualificationV1): pass
        with self.assertRaises(b.D1DiagnosticError): b.analyze_d1_two_period_operating_profit_continuity_v1(object.__new__(Subclass))
        for wrong in (replace(q),deepcopy(q),pickle.loads(pickle.dumps(q))):
            with self.assertRaises(ArchiveError): b.analyze_d1_two_period_operating_profit_continuity_v1(wrong)

    def test_self_consistent_forged_values_and_invalid_binding_rejected(self):
        q=self.evaluate()
        forged=replace(q,current_revenue=Decimal(999))
        object.__setattr__(forged,'_archive_replay_binding',q._archive_replay_binding)
        self.assertNotEqual(forged.semantic_id,q.semantic_id)
        with self.assertRaises(ArchiveError): b.analyze_d1_two_period_operating_profit_continuity_v1(forged)
        forged=replace(q)
        object.__setattr__(forged,'_archive_replay_binding',replace(q._archive_replay_binding,receipt_id='0'*64))
        with self.assertRaises(ArchiveError): b.analyze_d1_two_period_operating_profit_continuity_v1(forged)

    def test_replay_uses_recomputed_values_once(self):
        q=self.evaluate()
        with patch.object(a,'_qualify_extraction',wraps=a._qualify_extraction) as replay:
            b.analyze_d1_two_period_operating_profit_continuity_v1(q)
        self.assertEqual(replay.call_count,1)

    def test_identity_semantics_recapture_equal_ratios_different_facts(self):
        d=self.analyze()
        recaptured=self.analyze(timestamp='2025-08-02T00:00:00Z')
        self.assertEqual(d.semantic_id,recaptured.semantic_id)
        self.assertNotEqual(d.evidence_id,recaptured.evidence_id)
        scaled=self.analyze(comparative(160,20,200,40))
        self.assertEqual(d.ratio_difference,scaled.ratio_difference)
        self.assertNotEqual(d.semantic_id,scaled.semantic_id)
        self.assertNotEqual(d.evidence_id,scaled.evidence_id)
        source=comparative()
        for c in CONCEPTS:
            rows=source['facts']['us-gaap'][c]['units']['USD']
            rows.reverse(); rows.append(deepcopy(rows[0]))
        duplicate=self.analyze(source)
        self.assertEqual(d.semantic_id,duplicate.semantic_id)
        self.assertNotEqual(d.evidence_id,duplicate.evidence_id)

    def test_no_side_effects_network_capture_or_pipeline_calls(self):
        q=self.evaluate()
        before={str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        with (patch.object(socket,'socket',side_effect=AssertionError('network')),
              patch.object(SecArchive,'_capture',side_effect=AssertionError('capture'))):
            d=b.analyze_d1_two_period_operating_profit_continuity_v1(q)
        self.assertIs(d.status,b.S.AVAILABLE)
        self.assertEqual(before,{str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()})
        self.assertEqual({s.value for s in b.S},{'AVAILABLE','NOT_APPLICABLE','UNAVAILABLE','UNSUPPORTED','SOURCE_CONFLICT'})
        self.assertEqual(len(b.R),7)
