"""M1 USD country ETF intake, with MOCK source and rights attestations only."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from m1_scan_handoff import (
    scaffold, assess, main, ETF_RESEARCH_MODE,
)
from m1_country_etf_mode import ETF_CANDIDATES, NO_ETF_PROXY
from render_global_index_map import load_geometry, validate_map_issue, render_global_map
from render_macro_lens import InvalidIssue

ROOT=Path(__file__).resolve().parents[1]
CUT='2026-10-20T23:00:00Z'
MOCK_SOURCE='tests/test_m1_etf_research_intake.py'
MOCK_RIGHTS='M1_DAILY_SCAN_HANDOFF.md'
META={'issue_id':'GM-20261020-08',
      'headline':'Country ETF prices in USD',
      'deck':'Fictitious one-session USD ETF closes for contract tests',
      'interpretation':'MOCK ETF returns are not domestic index performance',
      'caption':'MOCK TEST ONLY: no real prices or permissions. NOT FOR PUBLICATION.'}


def research_packet():
    p=scaffold(CUT,research_mode=ETF_RESEARCH_MODE)
    p['preparer_reference']='MOCK-PREPARER'
    p['independent_auditor_reference']='MOCK-AUDITOR'
    for row in p['rows']:
        row.update(decision='EXCLUDED',
                   exclusion_status='MISSING',
                   research_notes='MOCK: missing independently licensed fund quote')
        row['etf_discovery'] = {
            'state': ('CANDIDATE_VERIFIED' if
                      row['etf_ticker_candidate'] else 'NO_ELIGIBLE_ETF_FOUND'),
            'checked_at_utc': '2026-10-20T14:03:00Z',
            'source_urls': ['https://www.ishares.com/us/products/etf-investments'
                            if row['etf_ticker_candidate'] else
                            'https://www.sec.gov/edgar/search/'],
            'notes': 'MOCK discovery declaration: not evidence of actual search',
        }
    return p


def accept_mock(p,code):
    fund=ETF_CANDIDATES[code]
    row=next(r for r in p['rows'] if r['economy_id']==code)
    row.update(decision='QUALIFIED', exclusion_status=None,
               research_notes='MOCK ONLY, not a real licensed quote',
               qualified_quote={
                  'index_name':fund['name'],
                  'etf_ticker':fund['ticker'],
                  'publisher':fund['issuer'],
                  'source_title':'MOCK U.S. ETF close',
                  'capture_reference':'MOCK CAPTURE',
                  'benchmark_definition':'MOCK U.S. listed single-country unhedged fund',
                  'rights_review_reference':'MOCK RIGHTS AUDITOR',
                  'independent_fact_review_reference':'MOCK FACTS AUDITOR',
                  'rights_scope':'PUBLIC_BLOSSOM_ETF_USD_GRAPHIC',
                  'rights_decision':'APPROVED_FOR_EXACT_USE',
                  'fact_decision':'INDEPENDENTLY_CHECKED',
                  'benchmark_variant':'ETF_EXCHANGE_PRICE',
                  'return_currency':'USD','currency':'USD',
                  'etf_price_basis':'UNADJUSTED_US_EXCHANGE_CLOSE',
                  'corporate_action_review':'NO_MATERIAL_SPLIT_OR_EX_DISTRIBUTION',
                  'proxy_scope':'SINGLE_COUNTRY_UNHEDGED',
                  'original_price_source_url':'https://source.example.net/test-etf',
                  'rights_evidence_url':'https://rights.example.net/test-etf',
                  'source_capture_path':MOCK_SOURCE,
                  'source_capture_sha256':hashlib.sha256(
                      (ROOT/MOCK_SOURCE).read_bytes()).hexdigest(),
                  'rights_capture_path':MOCK_RIGHTS,
                  'rights_capture_sha256':hashlib.sha256(
                      (ROOT/MOCK_RIGHTS).read_bytes()).hexdigest(),
                  'prior_close':100.00,
                  'current_close':100.22,
                  'prior_observed_at':'2026-10-16T16:00:00-04:00',
                  'observed_at':'2026-10-19T16:00:00-04:00',
                  'retrieved_at':'2026-10-20T14:03:00Z',
                  'close_session_date':'2026-10-19',
                  'prior_session_date':'2026-10-16',
                  'session_status':'COMPLETED',
               })


class ETFResearchIntakeTests(unittest.TestCase):
    def test_initial_research_has_30_null_quotes_and_25_candidate_etfs(self):
        p=scaffold(CUT,research_mode=ETF_RESEARCH_MODE)
        self.assertEqual(len(p['rows']),30)
        self.assertEqual(sum(r['etf_ticker_candidate'] is not None
                             for r in p['rows']),25)
        self.assertEqual({r['economy_id'] for r in p['rows']
                          if r['etf_ticker_candidate'] is None},NO_ETF_PROXY)
        self.assertTrue(all(r['decision']=='UNRESEARCHED' and
                            r['qualified_quote'] is None
                            for r in p['rows']))
        res,issue=assess(p,issue_metadata=META)
        self.assertEqual(res['status'],'HOLD')
        self.assertEqual(res['count_unresearched'],30)
        self.assertIsNone(issue)

    def test_missing_discovery_check_blocks_exclusion_even_with_all_rows(self):
        p=research_packet()
        p['rows'][21]['etf_discovery']['state']='NOT_SEARCHED'
        with self.assertRaises(InvalidIssue):
            assess(p,issue_metadata=META)
        p=research_packet()
        p['rows'][0]['etf_discovery']['source_urls']=[]
        with self.assertRaises(InvalidIssue):
            assess(p,issue_metadata=META)
        p=research_packet()
        p['rows'][0]['etf_discovery']['checked_at_utc']='2026-10-21T14:03:00Z'
        with self.assertRaises(InvalidIssue):
            assess(p,issue_metadata=META)

    def test_new_etf_discovery_requires_registry_review_never_auto_substitutes(self):
        p=research_packet()
        p['rows'][21]['etf_discovery'].update(
            state='NEW_ETF_REVIEW_REQUIRED',
            notes='MOCK newly discovered fund; no authorized registry identity',
            source_urls=['https://www.sec.gov/edgar/search/'])
        result,issue=assess(p,issue_metadata=META)
        self.assertEqual(result['status'],'HOLD')
        self.assertIsNone(issue)
        p['rows'][21]['decision']='QUALIFIED'
        with self.assertRaises(InvalidIssue):
            assess(p,issue_metadata=META)

    def test_four_mock_qualified_us_funds_may_only_become_draft_candidate(self):
        p=research_packet()
        for code in ('USA','JPN','IND','SAU'):accept_mock(p,code)
        res,issue=assess(p,issue_metadata=META,evidence_root=ROOT)
        self.assertEqual(res['research_mode'],ETF_RESEARCH_MODE)
        self.assertEqual(res['status'],'CANDIDATE_READY_REQUIRES_EXTERNAL_AUDIT')
        self.assertEqual(len(validate_map_issue(issue,load_geometry())),4)
        self.assertEqual(issue['evidence'][0]['etf_ticker'],'VOO')
        self.assertEqual(issue['evidence'][1]['etf_ticker'],'EWJ')
        self.assertEqual(issue['evidence'][20]['etf_ticker'],'KSA')
        self.assertEqual(issue['evidence'][21]['etf_ticker'],None)
        self.assertEqual(issue['evidence'][21]['missing_status'],'MISSING')
        svg=render_global_map(issue)
        self.assertIn('GLOBAL ETF MAP',svg)
        self.assertIn('4 MARKETS SHOWN',svg)
        self.assertNotIn('COUNTRY INDEX RETURNS',svg)
        self.assertIn('MOCK TEST',issue['caption'])

    def test_wrong_etf_ticker_and_index_proxy_cannot_pass_intake(self):
        p=research_packet()
        for code in ('USA','JPN','IND','SAU'):accept_mock(p,code)
        p['rows'][1]['qualified_quote']['etf_ticker']='MCHI'
        with self.assertRaises(InvalidIssue):
            assess(p,issue_metadata=META,evidence_root=ROOT)
        p=research_packet()
        for code in ('USA','JPN','IND','SAU'):accept_mock(p,code)
        p['rows'][21]['decision']='QUALIFIED'
        p['rows'][21]['qualified_quote']=p['rows'][0]['qualified_quote']
        with self.assertRaises(InvalidIssue):
            assess(p,issue_metadata=META,evidence_root=ROOT)

    def test_wrong_rights_or_missing_actual_captures_hold(self):
        for key,v in (
             ('rights_scope','PUBLIC_BLOSSOM_INDEX_RETURN_GRAPHIC'),
             ('rights_decision','UNKNOWN'),
             ('source_capture_path','missing-source.bin'),
             ('rights_capture_sha256','0'*64),
             ('etf_price_basis','DIVIDEND_ADJUSTED_NAV'),
             ('corporate_action_review','UNREVIEWED'),
             ('proxy_scope','EMERGING_MARKETS_MULTI_COUNTRY'),
             ('currency','JPY'),
             ('observed_at','2026-10-20T13:00:00-04:00'),
        ):
            p=research_packet()
            for code in ('USA','JPN','IND','SAU'):accept_mock(p,code)
            p['rows'][0]['qualified_quote'][key]=v
            with self.subTest(key=key),self.assertRaises(InvalidIssue):
                assess(p,issue_metadata=META,evidence_root=ROOT)

    def test_session_mismatch_blocks_before_render(self):
        p=research_packet()
        for code in ('USA','JPN','IND','SAU'):accept_mock(p,code)
        p['rows'][1]['qualified_quote'].update(
             observed_at='2026-10-20T16:00:00-04:00',
             close_session_date='2026-10-20',
             retrieved_at='2026-10-20T21:00:00Z')
        with self.assertRaises(InvalidIssue):
            assess(p,issue_metadata=META,evidence_root=ROOT)

    def test_default_subject_routing_etf_and_explicit_index_override(self):
        from m1_scan_handoff import route_subject, LOCAL_RESEARCH_MODE
        self.assertEqual(route_subject('World map scan of today\'s market moves'),
                         ETF_RESEARCH_MODE)
        self.assertEqual(route_subject('Full world map daily scan'),
                         ETF_RESEARCH_MODE)
        self.assertEqual(route_subject('National stock index daily map'),
                         LOCAL_RESEARCH_MODE)
        self.assertEqual(route_subject("World map today's market moves",
                         explicit_mode='index'),LOCAL_RESEARCH_MODE)
        self.assertEqual(route_subject('Country map domestic index moves'),
                         LOCAL_RESEARCH_MODE)

    def test_cli_usd_etf_mode_returns_hold_without_real_quote(self):
        with tempfile.TemporaryDirectory() as tmp:
            a=Path(tmp)/'packet.json';b=Path(tmp)/'report.json'
            self.assertEqual(main(['init','--cutoff-utc',CUT,'--mode','usd-etf',
                                   '--out',str(a)]),0)
            p=json.loads(a.read_text())
            self.assertEqual(p['research_mode'],ETF_RESEARCH_MODE)
            self.assertNotIn('prior_close',a.read_text())
            self.assertEqual(main(['assess',str(a),'--report',str(b)]),2)
            self.assertEqual(json.loads(b.read_text())['count_unresearched'],30)


if __name__=='__main__':
    unittest.main()
