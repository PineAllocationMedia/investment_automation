import copy
import unittest
from ai_native.research_case_comparison import compare_supplied_cases

class Tests(unittest.TestCase):
    def sample(self):
        old_request = dict(analysis_id='OLD',subject_id='ISSUER-1',as_of='2026-01-01',
                           method_version='IR-R1',strategy_id='EXPLORATORY')
        old_ir = dict(analysis_id='OLD',research_as_of='2025-12-31',facts=[
            dict(id='F-OLD',claim='Margin estimate A',status='INDICATIVE'),
            dict(id='F-OLD2',claim='Debt figure B',status='MISSING')])
        prior = dict(schema_version='RESEARCH_HISTORY_R1',analysis_id='OLD',
                     as_of='2026-01-01',recorded_at='2026-01-02',
                     method_version='IR-R1',strategy_id='EXPLORATORY',
                     original_request=old_request,original_ir_capsule=old_ir)
        req = dict(kind='FOLLOWUP',analysis_id='NEW',subject_id='ISSUER-1',
                   prior_analysis_id='OLD',as_of='2026-10-28',
                   method_version='IR-R1',strategy_id='EXPLORATORY')
        ir = dict(analysis_id='NEW',research_as_of='2026-10-27',facts=[
            dict(id='F-NEW',claim='Margin estimate B',status='CONFLICTED'),
            dict(id='F-NEW2',claim='Debt figure B',status='MISSING')])
        return dict(request=req,ir_capsule=ir,prior_case=prior,subject_id='ISSUER-1',
                    fact_links=[dict(prior_fact_id='F-OLD',current_fact_id='F-NEW'),
                                dict(prior_fact_id='F-OLD2',current_fact_id='F-NEW2')])
    def test_explicit_link_only_is_structural(self):
        d=compare_supplied_cases(**self.sample())
        self.assertEqual(d['status'],'STRUCTURAL_REVIEW_PREPARED')
        self.assertEqual(d['economic_change_status'],'NOT_EVALUATED')
        self.assertEqual(d['review_items_private'][0]['prior_evidence_status'],'INDICATIVE')
        self.assertEqual(d['review_items_private'][0]['current_evidence_status'],'CONFLICTED')
        self.assertEqual(d['review_items_private'][0]['text_check'],'TEXT_DIFF_NOT_CERTIFIED_ECONOMIC_CHANGE')
        self.assertEqual(d['review_items_private'][1]['text_check'],'TEXT_SAME_NOT_EVIDENCE_OF_NO_CHANGE')
    def test_no_prior_never_invents_baseline(self):
        a=self.sample();a['prior_case']=None;a['fact_links']=[]
        self.assertEqual(compare_supplied_cases(**a)['status'],'BASELINE_NOT_AVAILABLE')
    def test_no_prior_with_links_blocks(self):
        a=self.sample();a['prior_case']=None
        with self.assertRaisesRegex(ValueError,'FACT_LINKS_WITHOUT_BASELINE'):compare_supplied_cases(**a)
    def test_no_links_means_no_comparison(self):
        a=self.sample();a['fact_links']=[]
        self.assertEqual(compare_supplied_cases(**a)['status'],'NO_FACT_LINKS_SUPPLIED')
    def test_non_followup_blocks(self):
        a=self.sample();a['request']['kind']='DECISION'
        with self.assertRaisesRegex(ValueError,'FOLLOWUP_REQUIRED'):compare_supplied_cases(**a)
    def test_subject_mismatch_blocks(self):
        a=self.sample();a['prior_case']['original_request']['subject_id']='OTHER'
        with self.assertRaisesRegex(ValueError,'PRIOR_SUBJECT_MISMATCH'):compare_supplied_cases(**a)
    def test_future_prior_blocks(self):
        a=self.sample();a['prior_case']['recorded_at']='2026-11-01'
        with self.assertRaisesRegex(ValueError,'PRIOR_FUTURE'):compare_supplied_cases(**a)
    def test_prior_id_mismatch_blocks(self):
        a=self.sample();a['prior_case']['original_ir_capsule']['analysis_id']='DIFFERENT'
        with self.assertRaisesRegex(ValueError,'PRIOR_ANALYSIS_ID_INCONSISTENT'):compare_supplied_cases(**a)
    def test_fact_id_mismatch_blocks(self):
        a=self.sample();a['fact_links'][0]['prior_fact_id']='MISSING-ID'
        with self.assertRaisesRegex(ValueError,'FACT_LINK_UNKNOWN'):compare_supplied_cases(**a)
    def test_duplicate_links_blocks(self):
        a=self.sample();a['fact_links'].append(dict(prior_fact_id='F-OLD',current_fact_id='F-NEW2'))
        with self.assertRaisesRegex(ValueError,'DUPLICATE_FACT_LINK'):compare_supplied_cases(**a)
    def test_unrecognized_evidence_status_blocks(self):
        a=self.sample();a['prior_case']['original_ir_capsule']['facts'][0]['status']='SOURCE_AUTHENTIC'
        with self.assertRaisesRegex(ValueError,'UNSUPPORTED_EVIDENCE_STATUS'):compare_supplied_cases(**a)
    def test_changed_strategy_is_not_silently_comparable(self):
        a=self.sample();a['request']['strategy_id']='high-cagr'
        self.assertTrue(compare_supplied_cases(**a)['strategy_changed'])
    def test_no_mutation(self):
        a=self.sample();before=copy.deepcopy(a);compare_supplied_cases(**a)
        self.assertEqual(a,before)

if __name__=='__main__':unittest.main()
