"""Practical M1 ETF market-price path — MOCK prices, no real-data claim."""
import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from m1_country_etf_mode import ETF_CANDIDATES
from m1_etf_daily import build, init_csv, records, review, main, COLUMNS
from render_global_index_map import (
    load_geometry, validate_map_issue, render_global_map,
    m1_release_allowed,
)
from render_macro_lens import InvalidIssue, payload_hash


class M1PracticalETFTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.csv=self.root/'mock.csv'
        init_csv(self.csv)
        self.rows=records(self.csv)
        # Fictional prices used only for tests. We never claim these prices
        # actually appear at the linked issuer pages.
        for i,row in enumerate(self.rows):
            if row['ticker']:
                row.update(
                    prior_close=str(100.0+i),
                    close=str(round((100+i)*(1+(i%7-3)*.003),4)),
                    source_url='https://www.ishares.com/us/products/etf-investments',
                    prior_source_url='https://www.ishares.com/us/products/etf-investments',
                    source_name='MOCK issuer source structure',
                    corporate_action_status='NO_KNOWN_EVENT',
                    source_use_status='REVIEW_PENDING',
                    notes='FICTITIOUS PRICE PAIR; TEST ONLY')
        self.save()

    def save(self):
        with self.csv.open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=COLUMNS)
            w.writeheader();w.writerows(self.rows)

    def make(self):
        return build(self.csv,'2026-10-19','2026-10-16',
                     '2026-10-20T18:30:00Z',issue_id='GM-20261020-09',
                     headline='Global ETFs in USD')

    def test_30_country_csv_has_no_fake_prices(self):
        p=self.root/'initial.csv'
        self.assertEqual(init_csv(p),30)
        data=records(p)
        self.assertEqual(len(data),30)
        self.assertTrue(all(not e['close'] and not e['prior_close'] for e in data))
        self.assertEqual(sum(bool(e['ticker']) for e in data),25)

    def test_25_mock_us_close_pairs_produce_real_data_draft_contract(self):
        p,report=self.make()
        eligible=validate_map_issue(p,load_geometry())
        self.assertEqual(len(eligible),25)
        self.assertEqual(report['count_shown'],25)
        self.assertEqual(len(report['omitted']),5)
        self.assertEqual(p['rights_note'],'RESEARCH_PREVIEW')
        self.assertEqual(p['session_date'],'2026-10-19')
        svg=render_global_map(p)
        self.assertIn('GLOBAL ETF MAP',svg)
        self.assertIn('DRAFT · REAL DATA',svg)
        self.assertIn('25 MARKETS SHOWN',svg)
        self.assertIn('USD PRICE MOVES',svg)
        self.assertNotIn('COUNTRY INDEX RETURNS',svg)
        with self.assertRaises(InvalidIssue):
            render_global_map(p,status='RELEASE')

    def test_partial_coverage_still_produces_map_when_four_supported(self):
        for i,row in enumerate(self.rows):
            if row['ticker'] and i>5:
                for k in COLUMNS[2:]:
                    row[k]=''
        self.save()
        p,report=self.make()
        self.assertEqual(report['count_shown'],6)
        self.assertEqual(len(report['omitted']),24)
        self.assertIn('6 MARKETS SHOWN',render_global_map(p))

    def test_current_us_market_close_not_yet_complete(self):
        with self.assertRaises(InvalidIssue):
            build(self.csv,'2026-10-20','2026-10-19',
                  '2026-10-20T19:45:00Z',issue_id='GM-20261020-09')

    def test_reject_weekends_stale_dates_and_bad_registry_mapping(self):
        with self.assertRaises(InvalidIssue):
            build(self.csv,'2026-10-19','2026-10-18',
                  '2026-10-20T18:30:00Z',issue_id='GM-20261020-09')
        with self.assertRaises(InvalidIssue):
            build(self.csv,'2026-09-15','2026-09-14',
                  '2026-10-20T18:30:00Z',issue_id='GM-20261020-09')
        self.rows[0]['ticker']='EWJ';self.save()
        with self.assertRaises(InvalidIssue):
            self.make()

    def test_missing_half_price_or_fake_or_restricted_sources_fail(self):
        for k,value in (
            ('close',''),('source_url','https://example.org/fake'),
            ('source_url','http://not-secure.test'),
            ('source_name',''),('source_use_status','RESTRICTED'),
            ('corporate_action_status','SPLIT_CONFIRMED'),
            ('prior_close','0'),('prior_close','nan'),
        ):
            old=self.rows[0][k]
            self.rows[0][k]=value;self.save()
            with self.subTest(k=k,value=value),self.assertRaises(InvalidIssue):
                self.make()
            self.rows[0][k]=old

    def test_inaccurate_return_value_or_mixed_session_fails(self):
        p,_=self.make()
        p['evidence'][0]['signed_return_pct']=800
        with self.assertRaises(InvalidIssue):
            validate_map_issue(p,load_geometry())
        p,_=self.make()
        p['evidence'][1]['close_session_date']='2026-10-20'
        with self.assertRaises(InvalidIssue):
            validate_map_issue(p,load_geometry())
        p,_=self.make()
        p['evidence'][1]['observed_at']='2026-10-19T16:00:00-05:00'
        with self.assertRaises(InvalidIssue):
            validate_map_issue(p,load_geometry())

    def test_review_missing_pass_never_removes_watermark(self):
        p,_=self.make()
        q={'issue_sha256':payload_hash(p),'fact_verdict':'PASS',
           'corporate_actions_verdict':'PASS','source_use_verdict':'UNKNOWN',
           'visual_verdict':'PASS','auditor_reference':'INDEPENDENT AUDIT',
           'source_use_review_reference':'INDEPENDENT TERMS'}
        with self.assertRaises(InvalidIssue):
            review(p,q)
        q['source_use_verdict']='NO_KNOWN_RESTRICTION'
        promoted=review(p,q)
        self.assertEqual(promoted['rights_note'],'PUBLIC_FACTS_QA_PASSED')
        self.assertEqual(len(validate_map_issue(promoted,load_geometry())),25)
        with self.assertRaises(InvalidIssue):
            m1_release_allowed(promoted,{'input_sha256':payload_hash(promoted),
                                         'independent_audit':'PASS',
                                         'ceo_approved':False,
                                         'auditor_reference':'INDEPENDENT AUDIT',
                                         'ceo_approval_reference':'OWNER'})

    def test_full_cli_build_writes_native_and_mobile_drafts(self):
        issue=self.root/'m1.json';svg=self.root/'m1.svg'
        png=self.root/'m1.png';mobile=self.root/'mobile.png'
        args=['build',str(self.csv),'--session-date','2026-10-19',
              '--prior-date','2026-10-16','--cutoff-utc','2026-10-20T18:30:00Z',
              '--issue-id','GM-20261020-09','--headline','Global ETFs in USD',
              '--out-issue',str(issue),'--svg',str(svg),
              '--png',str(png),'--mobile-png',str(mobile)]
        self.assertEqual(main(args),0)
        self.assertTrue(all(x.is_file() and x.stat().st_size>500
                            for x in (issue,svg,png,mobile)))
        self.assertIn('DRAFT · REAL DATA',svg.read_text())
        import struct
        self.assertEqual(struct.unpack('>II',png.read_bytes()[16:24]),
                         (1080,1350))
        self.assertEqual(struct.unpack('>II',mobile.read_bytes()[16:24])[0],390)


if __name__=='__main__':
    unittest.main()
