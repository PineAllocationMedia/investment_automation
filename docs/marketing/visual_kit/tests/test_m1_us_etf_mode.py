"""M1 USD U.S. country ETF proxy mode: separateness, coverage and fail-closed tests.

All example market prices are fictional, NOT source-exchange data or permissions.
"""
import copy
import json
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

from m1_country_etf_mode import (
    ETF_BASIS, ETF_COMPARISON, ETF_CANDIDATES, NO_ETF_PROXY,
)
from render_global_index_map import (
    COUNTRIES, LAND, load_geometry, render_global_map, validate_map_issue,
)
from render_macro_lens import InvalidIssue

ROOT = Path(__file__).resolve().parents[1]
SYN = ROOT/'examples'/'m1_us_etf_synthetic.json'
INDEX = ROOT/'examples'/'m1_global_index_synthetic.json'


def fixture():
    return json.loads(SYN.read_text(encoding='utf-8'))


class M1UsdETFTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.geo=load_geometry()

    def test_28_registered_candidates_and_five_genuine_no_proxy_markets(self):
        self.assertEqual(len(COUNTRIES),30)
        self.assertEqual(len(ETF_CANDIDATES),28)
        self.assertEqual(NO_ETF_PROXY,{'EGY','DZA','RUS','KAZ','IRN'})
        self.assertEqual(ETF_CANDIDATES['USA']['ticker'],'VOO')
        self.assertEqual(ETF_CANDIDATES['JPN']['ticker'],'EWJ')
        self.assertEqual(ETF_CANDIDATES['CHN']['ticker'],'MCHI')
        self.assertEqual(ETF_CANDIDATES['IND']['ticker'],'INDA')
        self.assertEqual(ETF_CANDIDATES['DEU']['ticker'],'EWG')
        self.assertEqual(ETF_CANDIDATES['GBR']['ticker'],'EWU')
        self.assertEqual(ETF_CANDIDATES['VNM']['ticker'],'VNM')
        self.assertEqual(ETF_CANDIDATES['SAU']['ticker'],'KSA')
        self.assertTrue(all(x['issuer_url'].startswith('https://')
                            for x in ETF_CANDIDATES.values()))

    def test_same_us_close_25_mock_returns_validate(self):
        p=fixture()
        q=validate_map_issue(p,self.geo)
        self.assertEqual(p['return_basis'],ETF_BASIS)
        self.assertEqual(p['comparison_basis'],ETF_COMPARISON)
        self.assertEqual(len(q),25)
        self.assertEqual([e['economy_id'] for e in q],
                         [c for c in COUNTRIES if c not in NO_ETF_PROXY])
        self.assertTrue(all(e['listed_currency']=='USD' for e in q))
        self.assertEqual(len({e['observed_at'] for e in q}),1)
        self.assertTrue(all(e['close_session_date']=='2026-10-19' for e in q))
        self.assertTrue(all(e['verification']=='DEMO_ONLY' for e in q))

    def test_accurate_labels_no_false_local_index_or_today_claim(self):
        svg=render_global_map(fixture())
        ET.fromstring(svg)
        for token in ('MARKET ATLAS','USD PRICE MOVES','ONE COMPLETED U.S. SESSION',
                      'FX INCLUDED','ETF LEADERS &amp; LAGGARDS',
                      '25 MARKETS SHOWN','USD ETF PROXIES','DRAFT · SYNTHETIC'):
            self.assertIn(token,svg)
        for absent in ('LOCAL CURRENCY','INDEX LEADERS',
                       'NO VALID CLOSE','/30 VALID','DATA UNAVAILABLE'):
            self.assertNotIn(absent,svg)

    def test_no_proxy_countries_blend_with_unselected_land(self):
        root=ET.fromstring(render_global_map(fixture()))
        ns='{http://www.w3.org/2000/svg}'
        group=next(g for g in root.findall(ns+'g')
                   if g.attrib.get('clip-path')=='url(#mapView)')
        paths=group.findall(ns+'path')
        ids=[f['id'] for f in self.geo['features'] if f['id']!='ATA']
        byid=dict(zip(ids,paths))
        for missing in NO_ETF_PROXY:
            self.assertEqual(byid[missing].attrib['fill'],LAND)
            self.assertEqual(byid[missing].attrib['fill'],byid['NOR'].attrib['fill'])
        for shown in ('USA','CHN','IND','BRA','SAU','VNM'):
            self.assertNotEqual(byid[shown].attrib['fill'],LAND)

    def test_bad_ticker_mapping_substitution_or_broad_proxy_holds(self):
        for key,value in (('etf_ticker','EWJ'),
                          ('instrument_kind','INDEX'),
                          ('benchmark_variant','PRICE_INDEX'),
                          ('instrument_name','MSCI Europe ETF'),
                          ('proxy_scope','BROAD_EMERGING_MARKETS'),
                          ('return_currency','LOCAL'),
                          ('listed_currency','JPY'),
                          ('issuer_product_url','https://example.org/false')):
            p=fixture();p['evidence'][0][key]=value
            with self.subTest(key=key),self.assertRaises(InvalidIssue):
                validate_map_issue(p,self.geo)

    def test_no_egypt_delisted_or_russia_proxy_allowed(self):
        for code in ('EGY','RUS'):
            p=fixture()
            e=next(e for e in p['evidence'] if e['economy_id']==code)
            e.update(instrument_kind='ETF',missing_status='ELIGIBLE',
                     etf_ticker='EGPT' if code=='EGY' else 'RSX')
            with self.subTest(code=code),self.assertRaises(InvalidIssue):
                validate_map_issue(p,self.geo)

    def test_mixed_closes_or_incomplete_us_session_holds(self):
        for key,value in (
            ('close_session_date','2026-10-20'),
            ('observed_at','2026-10-20T16:00:00-04:00'),
            ('observed_at','2026-10-19T15:45:00-04:00'),
            ('prior_session_date','2026-10-15'),
            ('retrieved_at','2026-10-21T17:00:00Z'),
            ('session_status','INTRADAY'),
        ):
            p=fixture()
            p['evidence'][0][key]=value
            with self.subTest(key=key,value=value),self.assertRaises(InvalidIssue):
                validate_map_issue(p,self.geo)

    def test_nav_total_return_fx_and_unreviewed_distributions_hold(self):
        for field,value in (
            ('etf_price_basis','FUND_NAV'),
            ('etf_price_basis','DIVIDEND_ADJUSTED_TOTAL_RETURN'),
            ('corporate_action_review','NOT_CHECKED'),
            ('benchmark_variant','ETF_NAV'),
        ):
            p=fixture()
            p['evidence'][0][field]=value
            with self.subTest(field=field,value=value),self.assertRaises(InvalidIssue):
                validate_map_issue(p,self.geo)
        for key,value in (('etf_price_basis','FUND_NAV'),
                          ('fund_currency','EUR'),
                          ('comparison_basis','LATEST_COMPLETED_SESSIONS')):
            p=fixture();p[key]=value
            with self.subTest(key=key),self.assertRaises(InvalidIssue):
                validate_map_issue(p,self.geo)

    def test_no_synthetic_release_and_real_without_independent_review(self):
        p=fixture()
        with self.assertRaises(InvalidIssue):
            render_global_map(p,status='RELEASE')
        p['rights_note']='REVIEWED_FOR_EXACT_USE'
        with self.assertRaises(InvalidIssue):
            validate_map_issue(p,self.geo)
        p=fixture()
        p['evidence'][0]['original_price_source_url']='https://example.com/dummy'
        self.assertEqual(len(validate_map_issue(p,self.geo)),25)
        p['evidence'][0]['original_price_source_url']='https://real.exchange.example/mislabel'
        with self.assertRaises(InvalidIssue):
            validate_map_issue(p,self.geo)

    def test_index_mode_unchanged_and_25_still_valid(self):
        old=json.loads(INDEX.read_text(encoding='utf-8'))
        q=validate_map_issue(old,self.geo)
        self.assertEqual(len(q),25)
        self.assertEqual(q[0]['instrument_kind'],'INDEX')
        self.assertIn('MARKET ATLAS',render_global_map(old))


if __name__=='__main__':
    unittest.main()
