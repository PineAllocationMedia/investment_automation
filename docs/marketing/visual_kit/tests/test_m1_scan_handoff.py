"""Offline M1 data intake tests: MOCK reviewer attestations are not actual rights."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from m1_scan_handoff import assess, main, scaffold
from render_global_index_map import COUNTRIES, validate_map_issue, load_geometry
from render_macro_lens import InvalidIssue


CUTOFF = '2026-10-20T23:00:00Z'
META = {
    'issue_id': 'GM-20261020-02',
    'headline': 'Qualified market snapshot',
    'deck': 'Latest completed local index sessions, not synchronized',
    'interpretation': 'Local market indices are not national GDP growth',
    'caption': 'MOCK TEST: fabricated source and rights attestations. NOT FOR PUBLICATION.',
}


def excluded_packet():
    p = scaffold(CUTOFF)
    p['preparer_reference'] = 'MOCK-RESEARCHER'
    p['independent_auditor_reference'] = 'MOCK-AUDITOR'
    for r in p['rows']:
        r.update({
            'decision': 'EXCLUDED',
            'research_notes': 'No independently qualified source or rights in test',
            'exclusion_status': 'MISSING',
        })
    return p


def mock_eligible(p, code):
    r = next(x for x in p['rows'] if x['economy_id'] == code)
    r.update({
        'decision': 'QUALIFIED',
        'exclusion_status': None,
        'research_notes': 'MOCK ONLY: no authentic market price or license',
        'qualified_quote': {
            'index_name': r['index_candidate'],
            'publisher': 'MOCK EXCHANGE',
            'source_title': 'MOCK INDEX CLOSE',
            'capture_reference': 'MOCK-IMMUTABLE-CAPTURE',
            'benchmark_definition': 'MOCK price-index variant, not authenticated',
            'rights_review_reference': 'MOCK-RIGHTS-REVIEW',
            'independent_fact_review_reference': 'MOCK-FACT-AUDIT',
            'source_capture_sha256': 'a' * 64,
            'rights_scope': 'PUBLIC_BLOSSOM_INDEX_RETURN_GRAPHIC',
            'rights_decision': 'APPROVED_FOR_EXACT_USE',
            'fact_decision': 'INDEPENDENTLY_CHECKED',
            'original_price_source_url': 'https://source.example.net/mock-index',
            'rights_evidence_url': 'https://rights.example.net/mock-terms',
            'currency': r['currency_candidate'],
            'benchmark_variant': 'PRICE_INDEX',
            'return_currency': 'LOCAL',
            'session_status': 'COMPLETED',
            'prior_close': 1000,
            'current_close': 1001,
            'prior_observed_at': '2026-10-19T15:00:00Z',
            'observed_at': '2026-10-20T15:00:00Z',
            'retrieved_at': '2026-10-20T21:00:00Z',
        }
    })


class M1ResearchHandoffTests(unittest.TestCase):
    def test_scaffold_is_thirty_unresearched_without_fabricated_prices(self):
        p = scaffold(CUTOFF)
        self.assertEqual(tuple(r['economy_id'] for r in p['rows']), COUNTRIES)
        self.assertEqual(len(p['rows']), 30)
        self.assertTrue(all(r['decision']=='UNRESEARCHED'
                            and r['qualified_quote'] is None
                            for r in p['rows']))
        self.assertEqual(p['rows'][20]['economy_id'],'SAU')
        self.assertEqual(p['rows'][21]['economy_id'],'EGY')
        self.assertEqual(p['rows'][22]['economy_id'],'DZA')
        r,issue = assess(p,issue_metadata=META)
        self.assertEqual(r['count_unresearched'],30)
        self.assertEqual(r['status'],'HOLD')
        self.assertIsNone(issue)

    def test_missing_swapped_or_duplicate_market_fails(self):
        for transform in ('pop','swap','duplicate'):
            p=scaffold(CUTOFF)
            if transform=='pop':p['rows'].pop()
            if transform=='swap':p['rows'][0],p['rows'][1]=p['rows'][1],p['rows'][0]
            if transform=='duplicate':p['rows'][10]['economy_id']='USA'
            with self.subTest(transform=transform),self.assertRaises(InvalidIssue):
                assess(p)

    def test_excluded_countries_are_retained_in_scan_but_not_displayed(self):
        p=excluded_packet()
        r,issue=assess(p,issue_metadata=META)
        self.assertEqual(r['count_excluded'],30)
        self.assertEqual(r['count_qualified'],0)
        self.assertEqual(r['displayed_market_codes'],[])
        self.assertIsNone(issue)
        self.assertEqual(r['status'],'HOLD')

    def test_four_mock_attested_markets_generate_only_draft_candidate(self):
        p=excluded_packet()
        for code in ('USA','JPN','SAU','EGY'):
            mock_eligible(p,code)
        r,issue=assess(p,issue_metadata=META)
        self.assertEqual(r['status'],'CANDIDATE_READY_REQUIRES_EXTERNAL_AUDIT')
        self.assertEqual(r['count_qualified'],4)
        self.assertEqual(r['count_excluded'],26)
        self.assertIn('HUMAN_ASSERTIONS_ONLY',r['rights_and_source_truth'])
        self.assertEqual(len(validate_map_issue(issue,load_geometry())),4)
        self.assertEqual(issue['evidence'][22]['missing_status'],'MISSING')
        self.assertIsNone(issue['evidence'][22]['signed_return_pct'])
        self.assertIsNone(issue['evidence'][22]['original_price_source_url'])
        self.assertEqual(issue['evidence'][20]['missing_status'],'ELIGIBLE')
        self.assertEqual(issue['scan_status'],'COMPLETE_AUDITED')
        self.assertIn('MOCK TEST',issue['caption'])

    def test_missing_rights_scope_source_capture_and_independent_review_hold(self):
        for key,val in (
            ('rights_decision','NOT_REVIEWED'),
            ('rights_scope','INTERNAL_ONLY'),
            ('source_capture_sha256','bad-hash'),
            ('original_price_source_url','https://example.org/fake'),
            ('rights_evidence_url','http://rights.example.net'),
            ('independent_fact_review_reference','MOCK-RESEARCHER'),
        ):
            p=excluded_packet()
            for code in ('USA','JPN','SAU','EGY'):
                mock_eligible(p,code)
            q=p['rows'][0]['qualified_quote']
            q[key]=val
            with self.subTest(field=key),self.assertRaises(InvalidIssue):
                assess(p,issue_metadata=META)

    def test_provisional_quote_or_future_retrieval_fails(self):
        for key,value in (('session_status','INTRADAY'),
                          ('retrieved_at','2026-10-21T12:00:00Z'),
                          ('benchmark_variant','TOTAL_RETURN_INDEX'),
                          ('current_close',None)):
            p=excluded_packet()
            for code in ('USA','JPN','SAU','EGY'):mock_eligible(p,code)
            p['rows'][0]['qualified_quote'][key]=value
            with self.subTest(field=key),self.assertRaises(InvalidIssue):
                assess(p,issue_metadata=META)

    def test_three_attested_countries_not_enough(self):
        p=excluded_packet()
        for code in ('USA','JPN','EGY'):mock_eligible(p,code)
        r,issue=assess(p,issue_metadata=META)
        self.assertEqual(r['status'],'HOLD')
        self.assertIsNone(issue)
        self.assertIn('At least four', ' '.join(r['blockers']))

    def test_auditor_cannot_be_preparer(self):
        p=excluded_packet()
        p['independent_auditor_reference']='MOCK-RESEARCHER'
        for code in ('USA','JPN','SAU','EGY'):mock_eligible(p,code)
        with self.assertRaises(InvalidIssue):assess(p,issue_metadata=META)

    def test_cli_creates_diagnostic_not_real_issue(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            inp=root/'packet.json';out=root/'report.json'
            self.assertEqual(main(['init','--cutoff-utc',CUTOFF,
                                   '--out',str(inp)]),0)
            raw=json.loads(inp.read_text())
            self.assertEqual(len(raw['rows']),30)
            self.assertNotIn('signed_return_pct',str(raw))
            self.assertEqual(main(['assess',str(inp),'--report',str(out)]),2)
            result=json.loads(out.read_text())
            self.assertEqual(result['status'],'HOLD')


if __name__=='__main__':
    unittest.main()
