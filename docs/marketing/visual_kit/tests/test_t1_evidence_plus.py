import copy
import json
import sys
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0,str(Path(__file__).resolve().parent))
from t1_evidence_plus import validate_t1_plus,draw_t1_plus,used_evidence

class InvalidIssue(ValueError):
    pass

def need(condition, message):
    if not condition:
        raise InvalidIssue(message)

def bounded(value, name, limit):
    need(isinstance(value,str) and len(value)<=limit and value, f'bad {name}')


def case():
    base={'verification':'VERIFIED','classification':'FACT','source_title':'DEMO ONLY','source_url':'https://example.org/demos','verification_note':'synthetic example', 'retrieved_at':'2026-10-19T16:00:00-04:00'}
    def ev(cid,label,display,unit,period,observed,value=None):
        d=dict(base,claim_id=cid,label=label,display=display,unit=unit,period=period,observed_at=observed)
        if value is not None: d['numeric_value']=value
        return d
    e=[ev('S','Synthetic price', '+4%', '% m/m SA', '2026-09','2026-09-30T00:00:00Z',4),
       ev('A','Broad synthetic', '+0.7%', '% m/m SA','2026-09','2026-09-30T00:00:00Z'),
       ev('B','Core synthetic', '+0.3%', '% m/m SA','2026-09','2026-09-30T00:00:00Z'),
       ev('JUL','Synthetic price','-2%','% m/m SA','2026-07','2026-07-31T00:00:00Z',-2),
       ev('AUG','Synthetic price','+3%','% m/m SA','2026-08','2026-08-31T00:00:00Z',3)]
    return ({'t1_variant':'EVIDENCE_PLUS', 'support_fact_ids':['A','B'],
        'mini_chart':{'kind':'bar','title':'SYNTHETIC MONTHLY OBSERVATIONS','fact_ids':['JUL','AUG','S']},
        'mechanism':['First stage','Second stage','Third stage'],'blind_spot':'Short insight',
        'tripwire':'Future source update'}, e)

class PlusTests(unittest.TestCase):
    def test_with_two_support_and_chart(self):
        p,e=case(); used=validate_t1_plus(p,[e[0]],e,need,bounded)
        self.assertEqual(set(used), {'A','B','JUL','AUG','S'})
        out=[]; draw_t1_plus(out,p,e[0],e,need)
        svg='<svg xmlns="http://www.w3.org/2000/svg">'+''.join(out)+'</svg>'
        ET.fromstring(svg)
        for val in ('+4%','-2%','+3%','ZERO-BASED','03 / HOW IT TRAVELS'):
            self.assertIn(val,svg)
        self.assertIn('2026-09',str(used_evidence(p,[e[0]],e)))

    def test_without_chart(self):
        p,e=case();p.pop('mini_chart')
        self.assertEqual(validate_t1_plus(p,[e[0]],e,need,bounded),['A','B'])
        out=[];draw_t1_plus(out,p,e[0],e,need)
        self.assertNotIn('ZERO-BASED',''.join(out))

    def test_no_support_with_chart(self):
        p,e=case();p['support_fact_ids']=[]
        validate_t1_plus(p,[e[0]],e,need,bounded)
        out=[];draw_t1_plus(out,p,e[0],e,need)
        self.assertIn('SOURCE-BACKED TREND',''.join(out))

    def test_classic_unchanged(self):
        p,e=case();p['t1_variant']='CLASSIC';p.pop('support_fact_ids');p.pop('mini_chart')
        self.assertEqual(validate_t1_plus(p,[e[0]],e,need,bounded),[])

    def test_classic_silent_extra_rejected(self):
        p,e=case();p['t1_variant']='CLASSIC'
        with self.assertRaises(InvalidIssue): validate_t1_plus(p,[e[0]],e,need,bounded)

    def test_wrong_period_rejected(self):
        p,e=case();e[1]['period']='2026-08'
        with self.assertRaises(InvalidIssue): validate_t1_plus(p,[e[0]],e,need,bounded)

    def test_wrong_timestamp_rejected(self):
        p,e=case();e[1]['observed_at']='2026-08-31T00:00:00Z'
        with self.assertRaises(InvalidIssue):validate_t1_plus(p,[e[0]],e,need,bounded)

    def test_missing_chart_fact_rejected(self):
        p,e=case();p['mini_chart']['fact_ids'][0]='NO-SOURCE'
        with self.assertRaises(InvalidIssue):validate_t1_plus(p,[e[0]],e,need,bounded)

    def test_mixed_metrics_rejected(self):
        p,e=case();e[3]['label']='Different metric'
        with self.assertRaises(InvalidIssue):validate_t1_plus(p,[e[0]],e,need,bounded)

    def test_month_gap_rejected(self):
        p,e=case();e[3]['period']='2026-06'
        with self.assertRaises(InvalidIssue):validate_t1_plus(p,[e[0]],e,need,bounded)

    def test_numeric_value_must_match_display(self):
        p,e=case();e[3]['numeric_value']=-0.2
        with self.assertRaises(InvalidIssue):validate_t1_plus(p,[e[0]],e,need,bounded)

    def test_nonfinite_rejected(self):
        p,e=case();e[3]['numeric_value']=float('nan')
        with self.assertRaises(InvalidIssue):validate_t1_plus(p,[e[0]],e,need,bounded)

    def test_negative_bars_anchored_at_zero(self):
        p,e=case();validate_t1_plus(p,[e[0]],e,need,bounded)
        out=[];draw_t1_plus(out,p,e[0],e,need)
        self.assertIn('ZERO-BASED',''.join(out))

    def test_no_evidence_rejected(self):
        p,e=case();p['support_fact_ids']=[];p.pop('mini_chart')
        with self.assertRaises(InvalidIssue):validate_t1_plus(p,[e[0]],e,need,bounded)

    def test_bad_chart_kind_rejected(self):
        p,e=case();p['mini_chart']['kind']='freehand'
        with self.assertRaises(InvalidIssue):validate_t1_plus(p,[e[0]],e,need,bounded)

    def test_injected_raw_chart_values_rejected(self):
        p,e=case();p['mini_chart']['values']=[1,2,3]
        with self.assertRaises(InvalidIssue):validate_t1_plus(p,[e[0]],e,need,bounded)

class IntegrationTests(unittest.TestCase):
    def test_evidence_plus_full_svg_and_sources(self):
        from render_macro_lens import render
        fixture=json.loads((Path(__file__).parent.parent/'examples'/'t1_evidence_plus_synthetic.json').read_text())
        svg=render(fixture)
        ET.fromstring(svg)
        self.assertIn('ZERO-BASED',svg)
        self.assertIn('DRAFT',svg)
        self.assertIn('THE VERIFIED SIGNAL',svg)

    def test_incomplete_evidence_halts_full_renderer(self):
        from render_macro_lens import render,InvalidIssue
        fixture=json.loads((Path(__file__).parent.parent/'examples'/'t1_evidence_plus_synthetic.json').read_text())
        fixture['evidence'][3]['numeric_value']=123
        with self.assertRaises(InvalidIssue): render(fixture)

    def test_evidence_plus_release_demo_halts(self):
        from render_macro_lens import release_allowed,payload_hash,InvalidIssue
        fixture=json.loads((Path(__file__).parent.parent/'examples'/'t1_evidence_plus_synthetic.json').read_text())
        approval={'input_sha256':payload_hash(fixture),'independent_audit':'PASS', 'ceo_approved':True,
           'auditor_reference':'TEST ONLY','ceo_approval_reference':'TEST ONLY'}
        with self.assertRaises(InvalidIssue): release_allowed(fixture,approval)

if __name__=='__main__': unittest.main()