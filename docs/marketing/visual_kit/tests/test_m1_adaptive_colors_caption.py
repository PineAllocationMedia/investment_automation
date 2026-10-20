"""M1 adaptive scale/legend and real-price editorial caption regression tests.

All observations below are synthetic test values, not actual session prices.
"""
import copy
import csv
import json
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

from m1_etf_daily import COLUMNS, build, init_csv, race_recap_caption, records
from render_global_index_map import (
    LAND, ZERO, _daily_scale, _fill, _return, load_geometry, render_global_map,
)

ROOT=Path(__file__).resolve().parents[1]
ETF=ROOT/'examples'/'m1_us_etf_synthetic.json'
INDEX=ROOT/'examples'/'m1_global_index_synthetic.json'


def brightness(hex_color):
    return sum(int(hex_color[i:i+2],16)*coef
               for i,coef in ((1,0.2126),(3,0.7152),(5,0.0722)))


def geo_shapes(p):
    svg=render_global_map(p)
    root=ET.fromstring(svg)
    ns='{http://www.w3.org/2000/svg}'
    grp=next(g for g in root.findall(ns+'g')
             if g.attrib.get('clip-path')=='url(#mapView)')
    features=load_geometry()['features']
    country_shapes=grp.findall(ns+'path')
    codes=[f['id'] for f in features if f['id']!='ATA' and f['geom_type'] in ('Polygon','MultiPolygon')]
    return svg,dict(zip(codes,country_shapes))


class M1AdaptiveColorsAndCaptionTests(unittest.TestCase):
    def test_nice_daily_endpoints_use_actual_range(self):
        for moves,cap in (
            ([.02,.35,-.16],1.0),([-.99,.42],1.0),
            ([1.7,-.3],2.0),([4.08,-3.32],5.0),
            ([7.2,-1.7],10.0),([12,-5],20.0),
            ([0,0,0,0],1.0)
        ):
            with self.subTest(moves=moves):
                self.assertEqual(_daily_scale(moves),cap)
                self.assertGreaterEqual(cap,max(map(abs,moves)))

    def test_exact_zero_is_covered_not_land_gray(self):
        self.assertNotEqual(_fill(0,1),LAND)
        self.assertEqual(_fill(0,1),ZERO)
        for v in (-.00001,-.02,.00001,.02):
            with self.subTest(v=v):
                self.assertNotEqual(_fill(v,1),LAND)
                self.assertNotEqual(_fill(v,1),ZERO)

    def test_both_color_signs_strictly_darkening_with_magnitude(self):
        for cap in (1,2,5,10):
            for sign in (-1,1):
                values=[sign*cap*k/25 for k in range(1,26)]
                colors=[_fill(v,cap) for v in values]
                luminosities=list(map(brightness,colors))
                self.assertEqual(len(set(colors)),len(colors))
                self.assertTrue(all(a>b for a,b in
                                    zip(luminosities,luminosities[1:])),
                                f'Color luminance not monotonic: {cap} {sign}')
                self.assertNotIn(LAND,colors)

    def test_dynamic_legend_discloses_session_scale_and_unplotted_land(self):
        for path in (ETF,INDEX):
            p=json.loads(path.read_text(encoding='utf-8'))
            eligible=[e for e in p['evidence'] if e['missing_status']=='ELIGIBLE']
            # force same distinct session range in either M1 mode
            for i,e in enumerate(eligible):
                pct=4.1 if i==0 else -3.3 if i==1 else .1
                e['close_price']=e['prior_close_price']*(1+pct/100)
                e['signed_return_pct']=pct
            # Synthetic test fixtures may enforce observed values within
            # a small arithmetic tolerance; use the recomputed real ratio.
            for e in eligible:
                e['signed_return_pct']=_return(e)
            svg=render_global_map(p)
            self.assertIn('-5%',svg)
            self.assertIn('+5%',svg)
            self.assertIn('NOT PLOTTED',svg)
            self.assertIn('0.00%',svg)
            self.assertEqual(svg.count('height="13"'),2)  # exact 0 / unplotted
            self.assertEqual(svg.count('fill="'+LAND+'"')>0,True)

    def test_covered_color_can_never_merge_into_land(self):
        p=json.loads(ETF.read_text(encoding='utf-8'))
        eligible=[e for e in p['evidence'] if e['missing_status']=='ELIGIBLE']
        for e in eligible:
            e['close_price']=e['prior_close_price']*(1+0.00005/100)
            e['signed_return_pct']=_return(e)
        eligible[0]['close_price']=eligible[0]['prior_close_price']
        eligible[0]['signed_return_pct']=0
        svg,shapes=geo_shapes(p)
        for code in ('NOR','RUS','EGY','IRN','KAZ','DZA'):
            self.assertEqual(shapes[code].attrib['fill'],LAND)
        for e in eligible:
            if e['economy_id']=='SGP':
                continue
            color=shapes[e['economy_id']].attrib['fill']
            self.assertNotEqual(color,LAND)
            self.assertNotEqual(color,'#294047')
            self.assertEqual(shapes[e['economy_id']].attrib['stroke-width'],'1.05')

    def test_caption_grounded_horse_race_direction_and_spread(self):
        facts=[
            dict(economy_name='South Korea',etf_ticker='EWY',
                 economy_id='KOR',signed_return_pct=4.08,
                 source_title='Exchange publication'),
            dict(economy_name='Indonesia',etf_ticker='EIDO',
                 economy_id='IDN',signed_return_pct=-3.32,
                 source_title='Exchange publication'),
            dict(economy_name='Japan',etf_ticker='EWJ',
                 economy_id='JPN',signed_return_pct=.12,
                 source_title='Exchange publication'),
            dict(economy_name='China',etf_ticker='MCHI',
                 economy_id='CHN',signed_return_pct=-.64,
                 source_title='Exchange publication'),
        ]
        cap=race_recap_caption(facts,'2026-10-19','2026-10-16')
        for phrase in ('7.40 percentage points','South Korea (EWY)',
                       'Indonesia (EIDO)','+4.08%','-3.32%',
                       '2 higher, 2 lower','U.S.-listed country ETFs',
                       'FX','2026-10-19','Exchange publication'):
            self.assertIn(phrase,cap)
        for forbidden in ('beat the market because','GDP rose','buy now'):
            self.assertNotIn(forbidden,cap)

    def test_all_red_caption_does_not_invent_a_positive_winner(self):
        original=[dict(economy_name=f'Market {i}',etf_ticker=f'ET{i}',
                       economy_id=f'M{i}',signed_return_pct=-.1-i*.1,
                       source_title='Sample price source') for i in range(4)]
        cap=race_recap_caption(original,'2026-10-19','2026-10-16')
        self.assertIn('Everyone finished in the red',cap)
        self.assertIn('0 higher, 4 lower',cap)
        self.assertIn('-0.10%',cap)

    def test_actual_csv_draft_caption_from_prices_not_names(self):
        with tempfile.TemporaryDirectory() as td:
            file=Path(td)/'quotes.csv'
            init_csv(file)
            rows=records(file)
            for row in rows:
                if row['ticker']:
                    move={'KOR':4.08,'IDN':-3.32}.get(row['country'],.1)
                    row.update(prior_close='100',close=str(100*(1+move/100)),
                               source_url='https://www.ishares.com/us/products/etf-investments',
                               prior_source_url='https://www.ishares.com/us/products/etf-investments',
                               source_name='Synthetic test price citation',
                               corporate_action_status='NO_KNOWN_EVENT',
                               source_use_status='REVIEW_PENDING')
            with file.open('w',newline='',encoding='utf-8') as fh:
                writer=csv.DictWriter(fh,fieldnames=COLUMNS)
                writer.writeheader();writer.writerows(rows)
            p,report=build(file,'2026-10-19','2026-10-16',
                           '2026-10-20T18:30:00Z',issue_id='GM-20261020-09')
            self.assertEqual(report['caption_draft'],p['caption'])
            self.assertIn('South Korea',p['caption'])
            self.assertIn('Indonesia',p['caption'])
            self.assertIn('7.40 percentage points',p['caption'])
            self.assertEqual(p['caption_review_state'],'DRAFT_AWAITING_PROMPT3')


if __name__=='__main__':
    unittest.main()
