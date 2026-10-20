"""M1 real-geography + synthetic index-first map gate tests."""
import copy
import json
import math
import struct
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

from render_global_index_map import (
    GEO_GIT_BLOB_SHA, GEOMETRY, _fill, _return, git_blob_sha, load_geometry,
    render_global_map, validate_map_issue, run,
)
from render_macro_lens import InvalidIssue, payload_hash, release_allowed

EX=Path(__file__).resolve().parents[1]/'examples'/'m1_global_index_synthetic.json'


def fixture():
    return json.loads(EX.read_text(encoding='utf-8'))


class M1GlobalEquityIndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.geo=load_geometry()

    def test_public_domain_geo_snapshot_is_immutable(self):
        raw=GEOMETRY.read_bytes()
        self.assertEqual(git_blob_sha(raw),GEO_GIT_BLOB_SHA)
        self.assertEqual(len(self.geo['features']),177)
        self.assertEqual(self.geo['source_github_blob_sha'],
                         '1e6ab74c7042f97013be69ceec798be8e1aff27d')
        self.assertEqual(self.geo['license'],'Public domain')
        joined={f['id'] for f in self.geo['features']}
        self.assertTrue({'USA','CHN','JPN','BRA','RUS','CAN','IND'}.issubset(joined))

    def test_mutated_geometry_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            altered=Path(d)/'geo.json'
            altered.write_bytes(GEOMETRY.read_bytes().replace(
                b'Natural Earth',b'Changed Earth',1))
            with self.assertRaises(InvalidIssue):load_geometry(altered)

    def test_twenty_country_index_candidates_with_correct_missingness(self):
        p=fixture()
        accepted=validate_map_issue(p,self.geo)
        self.assertEqual(len(p['evidence']),20)
        self.assertEqual(len(accepted),18)
        self.assertEqual([r['rank'] for r in p['evidence']],list(range(1,21)))
        self.assertTrue(all(r['instrument_kind']=='INDEX' for r in accepted))
        self.assertTrue(all(r['benchmark_variant']=='PRICE_INDEX' for r in accepted))
        self.assertIn('S&P 500',p['evidence'][0]['instrument_name'])
        self.assertIn('DAX Price Index',p['evidence'][2]['instrument_name'])
        self.assertEqual(p['evidence'][10]['missing_status'],'INCOMPARABLE')
        self.assertTrue(all(r['signed_return_pct'] is None for r in
                            p['evidence'] if r['missing_status']!='ELIGIBLE'))

    def test_draft_map_bounded_real_shapes_and_visible_index_names(self):
        p=fixture()
        svg=render_global_map(p)
        root=ET.fromstring(svg)
        self.assertEqual((root.attrib['width'],root.attrib['height']),('1080','1350'))
        paths=root.findall('.//{http://www.w3.org/2000/svg}path')
        self.assertGreaterEqual(len(paths),170)
        for text in ('GLOBAL EQUITY MAP','LOCAL CURRENCY','LATEST COMPLETED SESSIONS',
                     '18/20 VALID INDICES','INDEX LEADERS &amp; LAGGARDS',
                     'TOPIX Price Index','S&amp;P/TSX Composite Price Index',
                     'NATURAL EARTH (PUBLIC DOMAIN)','DRAFT · SYNTHETIC',
                     'NOT INVESTMENT ADVICE'):
            self.assertIn(text,svg)
        self.assertNotIn('GDP GROWTH',svg)
        self.assertNotIn('TODAY ALL MARKETS',svg)

    def test_asynchronous_eligible_market_closes_are_allowed(self):
        p=fixture()
        self.assertNotEqual(p['evidence'][0]['observed_at'],
                            p['evidence'][1]['observed_at'])
        self.assertEqual(len(validate_map_issue(p,self.geo)),18)
        self.assertIn('NOT SYNCHRONIZED',render_global_map(p))

    def test_missing_holidays_do_not_become_zero(self):
        p=fixture()
        p['evidence'][0]['missing_status']='HOLIDAY'
        p['evidence'][0]['session_status']='HOLIDAY'
        with self.assertRaises(InvalidIssue):validate_map_issue(p,self.geo)
        zero=next(x for x in fixture()['evidence'] if x['economy_id']=='ESP')
        self.assertEqual(_return(zero),0)
        self.assertNotEqual(_fill(0),_fill(0.03))

    def test_computed_source_price_return_disagrees_fails(self):
        p=fixture();p['evidence'][0]['signed_return_pct']=-0.17
        with self.assertRaises(InvalidIssue):validate_map_issue(p,self.geo)

    def test_nonfinite_and_zero_prices_fail(self):
        for v in (float('inf'),math.nan,0,None):
            p=fixture();p['evidence'][2]['prior_close_price']=v
            with self.subTest(v=str(v)),self.assertRaises(InvalidIssue):
                validate_map_issue(p,self.geo)

    def test_incomplete_or_duplicate_gdp_universe_fails(self):
        p=fixture();p['evidence'].pop()
        with self.assertRaises(InvalidIssue):validate_map_issue(p,self.geo)
        p=fixture();p['evidence'][1]['rank']=1
        with self.assertRaises(InvalidIssue):validate_map_issue(p,self.geo)
        p=fixture();p['evidence'][0]['rank_nominal_gdp_usd']=1
        with self.assertRaises(InvalidIssue):validate_map_issue(p,self.geo)

    def test_wrong_country_join_or_new_polygon_fails(self):
        p=fixture();p['evidence'][1]['geometry_id']='USA'
        with self.assertRaises(InvalidIssue):validate_map_issue(p,self.geo)
        p=fixture();p['evidence'][1]['economy_id']='ZZZ'
        p['evidence'][1]['geometry_id']='ZZZ'
        with self.assertRaises(InvalidIssue):validate_map_issue(p,self.geo)

    def test_etf_total_return_or_fx_crossed_bases_fail(self):
        p=fixture();p['return_basis']='USD_ETF_TOTAL_RETURN'
        with self.assertRaises(InvalidIssue):validate_map_issue(p,self.geo)
        p=fixture();p['evidence'][4]['instrument_kind']='ETF'
        with self.assertRaises(InvalidIssue):validate_map_issue(p,self.geo)
        p=fixture();p['evidence'][2]['benchmark_variant']='TOTAL_RETURN_INDEX'
        with self.assertRaises(InvalidIssue):validate_map_issue(p,self.geo)
        p=fixture();p['evidence'][5]['return_currency']='USD'
        with self.assertRaises(InvalidIssue):validate_map_issue(p,self.geo)

    def test_proposed_registry_cannot_claim_verified_real_universe(self):
        p=fixture();p['rights_note']='REVIEWED_FOR_EXACT_USE'
        with self.assertRaises(InvalidIssue):validate_map_issue(p,self.geo)
        p=fixture();p['benchmark_registry_status']='INDEPENDENTLY_VERIFIED'
        with self.assertRaises(InvalidIssue):validate_map_issue(p,self.geo)

    def test_mismatched_period_or_future_quote_fails(self):
        p=fixture();p['evidence'][5]['close_session_date']='2026-10-19'
        with self.assertRaises(InvalidIssue):validate_map_issue(p,self.geo)
        p=fixture();p['evidence'][0]['retrieved_at']='2026-10-21T23:00:00Z'
        with self.assertRaises(InvalidIssue):validate_map_issue(p,self.geo)
        p=fixture();p['evidence'][2]['observed_at']='2026-10-12T16:00:00+02:00'
        with self.assertRaises(InvalidIssue):validate_map_issue(p,self.geo)

    def test_missing_status_with_nonmissing_price_fails(self):
        p=fixture();p['evidence'][9]['missing_status']='STALE'
        with self.assertRaises(InvalidIssue):validate_map_issue(p,self.geo)

    def test_no_synthetic_release_and_hash_bound_logo(self):
        p=fixture()
        with self.assertRaises(InvalidIssue):render_global_map(p,status='RELEASE')
        manifest={'input_sha256':payload_hash(p),'independent_audit':'PASS',
                  'ceo_approved':True,'auditor_reference':'synthetic-test',
                  'ceo_approval_reference':'synthetic-test'}
        with self.assertRaises(InvalidIssue):release_allowed(p,manifest)
        q=copy.deepcopy(p);q['caption']='Altered after audit'
        self.assertNotEqual(payload_hash(q),payload_hash(p))

    def test_rendered_390px_mobile_and_baselines(self):
        try:
            import fitz
        except ImportError:
            self.skipTest('PyMuPDF required for actual text glyph bounds')
        svg=render_global_map(fixture())
        page=fitz.open(stream=svg.encode(),filetype='svg')[0]
        pix=page.get_pixmap(matrix=fitz.Matrix(1,1),alpha=False)
        self.assertEqual((pix.width,pix.height),(1080,1350))
        mobile=page.get_pixmap(matrix=fitz.Matrix(390/1080,390/1080),alpha=False)
        self.assertEqual(mobile.width,390)
        self.assertGreaterEqual(mobile.height,487)
        spans=[sp for block in page.get_text('dict')['blocks']
               for line in block.get('lines',[]) for sp in line['spans']]
        for sp in spans:
            x0,y0,x1,y1=sp['bbox']
            self.assertGreaterEqual(x0,54,sp['text'])
            self.assertLessEqual(x1,1022,sp['text'])
            self.assertGreaterEqual(y0,42,sp['text'])
            self.assertLessEqual(y1,1340,sp['text'])
        leader=next(sp for sp in spans if sp['text']=='INDEX LEADERS & LAGGARDS')
        asof=next(sp for sp in spans if sp['text'].startswith('AS OF '))
        self.assertLess(leader['bbox'][3]+30,asof['bbox'][1])

    def test_cli_writes_after_validation_only(self):
        try:
            import fitz
        except ImportError:
            self.skipTest('Requires PyMuPDF')
        with tempfile.TemporaryDirectory() as tmp:
            svg=Path(tmp)/'demo.svg';png=Path(tmp)/'demo.png'
            self.assertEqual(run([str(EX),'--output',str(svg),'--png',str(png)]),0)
            self.assertEqual(struct.unpack('>II',png.read_bytes()[16:24]),(1080,1350))
            before=svg.read_bytes()
            f=fixture();f['evidence'][2]['instrument_kind']='ETF'
            bad=Path(tmp)/'bad.json';bad.write_text(json.dumps(f))
            self.assertEqual(run([str(bad),'--output',str(svg),'--png',str(png)]),2)
            self.assertEqual(svg.read_bytes(),before)


if __name__=='__main__':
    unittest.main()
