#!/usr/bin/env python3
"""PAM M1 index-first global equity choropleth. Offline research graphic ONLY.

Synthetic fixture uses proposed, unverified benchmark names and fake prices.
Production requires audited CEO-selected country coverage and 27 index decisions,
original source/rights review, immutable public-domain Natural Earth polygons,
independent exact-asset audit, and separate CEO publication authorization.
"""
import argparse
import base64
import hashlib
import json
import math
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse
from xml.etree import ElementTree as ET

from render_macro_lens import (
    W, H, BG, LIGHT, MUTED, TEAL, AMBER, PINE, IVORY,
    InvalidIssue, APPROVED_LOGO_SHA256, need, bounded, iso_dt,
    valid_url, payload_hash, checked_logo, release_allowed, rect, rule, txt, wrap,
)

GEOMETRY = Path(__file__).parent/'assets'/'m1_natural_earth_110m_v5_1_1.json'
# Pin the exact rounded 177-feature public-domain Natural Earth snapshot.
GEO_GIT_BLOB_SHA = '8300299de7b831db1b50d0501924cad1f5b067e1'
UPSTREAM_NE_BLOB_SHA = '1e6ab74c7042f97013be69ceec798be8e1aff27d'
GEO_VERSION = 'NATURAL_EARTH_110M_V5.1.1_PAM_V1'
BASIS = 'DOMESTIC_INDEX_LOCAL_PRICE_RETURN'
ISSUE_RE = re.compile(r'^GM-\d{8}-\d{2}$')
ECONOMY_RE = re.compile(r'^[A-Z]{3}$')
COUNTRIES = (
    'USA','JPN','CHN','IND','DEU','GBR','CAN','AUS','TWN','KOR',
    'BRA','FRA','CHE','MEX','ESP','ITA','NLD','SGP','ZAF','TUR',
    'IDN','VNM','RUS','KAZ','IRN','POL','SWE',
)
# Natural Earth 110m omits microstate-scale Singapore. This is a geographic
# locator, not a fabricated polygon or an assertion about legal borders.
SGP_POINT = (103.8198, 1.3521)
MISSING = {'HOLIDAY','CLOSED','STALE','MISSING','INCOMPARABLE'}
PALETTE_NEG = ('#985F59','#B67D73','#CB9D90','#DFC5B9')
PALETTE_POS = ('#CAD9C5','#A8C8B5','#79AE91','#4C886D')
ZERO = '#CED0C8'
NO_DATA = '#707D7D'
LAND = '#294047'
OCEAN = '#142D35'
GRID = '#405B58'


def _dt(value, name):
    return datetime.fromisoformat(iso_dt(value, name).replace('Z', '+00:00'))


def _text_width(value, size):
    return sum(1 if c in 'WM@#%&' else .79 if c.isupper()
               else .66 if c.islower() or c.isdigit() else
               .34 if c.isspace() else .58 for c in value)*size


def put(x, y, text, size, max_width, *, anchor='start', color=LIGHT, weight=600):
    need(_text_width(str(text), size) <= max_width,
         'M1 text beyond safe column; shorten label without changing benchmark identity')
    return txt(x, y, text, size, color, weight, anchor)


def paragraph(x, y, value, *, name, chars, max_lines, size, leading, width,
              color=LIGHT, weight=500):
    return [put(x,y+i*leading,line,size,width,color=color,weight=weight)
            for i,line in enumerate(wrap(value,chars,max_lines,name))]


def git_blob_sha(raw):
    return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()


def load_geometry(path=GEOMETRY):
    raw=Path(path).read_bytes()
    need(git_blob_sha(raw) == GEO_GIT_BLOB_SHA,
         'M1 Natural Earth geometry bytes/hash changed; quarantine asset')
    geo=json.loads(raw)
    need(geo.get('schema') == 'pam.m1.ne110.geometry.v1' and
         geo.get('source_github_blob_sha') == UPSTREAM_NE_BLOB_SHA and
         geo.get('license') == 'Public domain',
         'M1 geometry provenance or license record has drifted')
    features=geo.get('features')
    need(isinstance(features,list) and len(features)==177,
         'M1 expected 177 Natural Earth country features')
    ids=set()
    for i,f in enumerate(features):
        fid=f.get('id')
        need(isinstance(fid,str) and fid not in ids and
             ECONOMY_RE.fullmatch(fid) is not None,
             f'M1 duplicate/invalid geometry ID at feature {i}')
        ids.add(fid)
        need(f.get('type') in ('Polygon','MultiPolygon'),
             'M1 unsupported country geometry type')
    return geo


def _one_number(f, key, name):
    v=f.get(key)
    need(type(v) in (float,int) and math.isfinite(v) and v>0,
         f'{name}.{key} must be finite and positive')
    return float(v)


def _return(f):
    return (f['close_price']/f['prior_close_price']-1.0)*100.0


def validate_map_issue(p, geo):
    need(isinstance(p,dict), 'M1 issue is not JSON object')
    need(p.get('schema_version')=='1.0' and p.get('template')=='M1',
         'M1 template and version required')
    need(p.get('account')=='@therealpam', 'M1 account must be @therealpam')
    need(isinstance(p.get('issue_id'),str) and ISSUE_RE.fullmatch(p['issue_id']),
         'M1 issue ID must use GM-YYYYMMDD-NN')
    cutoff=_dt(p.get('cutoff_utc'),'cutoff_utc')
    need(cutoff.utcoffset().total_seconds()==0,
         'Global map cutoff_utc must be expressed in UTC')
    for key,n in [('headline',62),('deck',111),('interpretation',97),
                  ('caption',1200),('universe_version',57),
                  ('method_version',45)]:
        bounded(p.get(key),key,n)
    need(p.get('selection_basis')=='CEO_SELECTED_27_COUNTRIES',
         'M1 uses the CEO-selected country list, not GDP ranks')
    need(p.get('geometry_version')==GEO_VERSION and
         p.get('geometry_source_github_blob_sha')==UPSTREAM_NE_BLOB_SHA,
         'M1 geometry join pinned source mismatch')
    need(p.get('return_basis')==BASIS,
         'M1 local-currency INDEX price return; no ETF or FX conversions')
    need(p.get('comparison_basis')=='LATEST_COMPLETED_SESSIONS',
         'M1 cross-time-zone markets cannot be described as synchronized')
    need(p.get('rights_note') in ('SYNTHETIC_LAYOUT_ONLY','REVIEWED_FOR_EXACT_USE'),
         'M1 precise data rights status required')
    need(p.get('universe_review') in ('CEO_SELECTED_UNVERIFIED','COVERAGE_VALIDATED'),
         'M1 country coverage review status missing')
    need(p.get('benchmark_registry_status') in
         ('CANDIDATES_UNVERIFIED','INDEPENDENTLY_VERIFIED'),
         'Benchmark registry verification status required')
    if p['rights_note']=='SYNTHETIC_LAYOUT_ONLY':
        need(p['universe_review']=='CEO_SELECTED_UNVERIFIED' and
             p['benchmark_registry_status']=='CANDIDATES_UNVERIFIED',
             'Demo issue must be explicitly marked as unverified')
    else:
        need(p['universe_review']=='COVERAGE_VALIDATED' and
             p['benchmark_registry_status']=='INDEPENDENTLY_VERIFIED',
             'Real M1 requires independent country, index and rights review')
    entries=p.get('evidence')
    need(isinstance(entries,list) and len(entries)==len(COUNTRIES),
         'M1 map requires exactly 27 CEO-selected country decisions')
    world={f['id'] for f in geo['features']}
    orders=set()
    ids=set()
    valid=[]
    for i,e in enumerate(entries):
        n=f'evidence[{i}]'
        need(isinstance(e,dict),f'{n} must be an object')
        order=e.get('selection_order')
        need(type(order)==int and 1 <= order <= len(COUNTRIES) and
             order not in orders, f'{n} duplicate or invalid selection order')
        orders.add(order)
        code=bounded(e.get('economy_id'),n+'.economy_id',3)
        need(code==COUNTRIES[order-1] and code not in ids,
             f'{n} wrong or duplicate CEO-selected country')
        ids.add(code)
        if code=='SGP':
            need(e.get('geometry_id')=='SGP_POINT',
                 'M1 Singapore must use audited locator, not nonexistent polygon')
        else:
            need(code in world and e.get('geometry_id')==code,
                 f'{n} missing or incorrect Natural Earth geometry join')
        bounded(e.get('economy_name'),n+'.economy_name',36)
        need('rank' not in e and 'rank_nominal_gdp_usd' not in e and
             'gdp_observation_year' not in e,
             'M1 country order must not masquerade as a GDP ranking')
        bounded(e.get('instrument_name'),n+'.instrument_name',43)
        bounded(e.get('instrument_provider'),n+'.instrument_provider',37)
        bounded(e.get('benchmark_definition'),n+'.benchmark_definition',120)
        bounded(e.get('country_exposure_note'),n+'.country_exposure_note',100)
        bounded(e.get('source_title'),n+'.source_title',50)
        bounded(e.get('rights_note'),n+'.rights_note',160)
        bounded(e.get('verification_note'),n+'.verification_note',160)
        need(e.get('instrument_kind') in ('INDEX','UNAVAILABLE'),
             f'{n} ETF proxy is excluded from domestic-index M1 mode')
        need(e.get('benchmark_variant') in ('PRICE_INDEX','UNCONFIRMED','NO_PROXY'),
             f'{n} index basis/status missing')
        need(e.get('return_currency')=='LOCAL',
             'M1 maps local benchmark price returns, not common USD returns')
        ccy=bounded(e.get('listed_currency'),n+'.listed_currency',3)
        need(re.fullmatch(r'[A-Z]{3}',ccy),
             f'{n} index currency invalid')
        need(e.get('verification') == ('DEMO_ONLY' if
             p['rights_note']=='SYNTHETIC_LAYOUT_ONLY' else 'VERIFIED'),
             f'{n} claimed independent source status unsupported')
        status=e.get('missing_status')
        need(status=='ELIGIBLE' or status in MISSING,
             f'{n} explicit missing-status required')
        valid_url(e.get('original_price_source_url'),n+'.original_price_source_url')
        if p['rights_note']=='SYNTHETIC_LAYOUT_ONLY':
            need(urlparse(e['original_price_source_url']).hostname in
                 ('example.org','example.com'),
                 'Synthetic M1 prices must use safe demo URL')
        else:
            need(urlparse(e['original_price_source_url']).hostname not in
                 ('example.org','example.com'),
                 'Real M1 index price original source cannot be a demo')
        if status=='ELIGIBLE':
            need(e.get('instrument_kind')=='INDEX' and
                 e.get('benchmark_variant')=='PRICE_INDEX',
                 'M1 eligible country requires reviewed price-index basis')
            _one_number(e,'close_price',n)
            _one_number(e,'prior_close_price',n)
            need(e.get('session_status')=='COMPLETED',
                 'M1 index close cannot be holiday/provisional')
            current=_dt(e.get('observed_at'),n+'.observed_at')
            previous=_dt(e.get('prior_observed_at'),n+'.prior_observed_at')
            retrieved=_dt(e.get('retrieved_at'),n+'.retrieved_at')
            need(previous<current<=retrieved<=cutoff,
                 'M1 observed/previous/retrieved clocks violate cutoff')
            need(cutoff-current<=timedelta(hours=96),
                 f'{n} stale index close must be marked STALE, not plotted')
            need(current.date().isoformat()==e.get('close_session_date') and
                 previous.date().isoformat()==e.get('prior_session_date'),
                 'M1 local session dates do not match close timestamp offsets')
            delta=_return(e)
            need(abs(delta)<=20,
                 'Unusually large index move requires separate manual review/HOLD')
            value=e.get('signed_return_pct')
            need(type(value) in (float,int) and math.isfinite(value)
                 and abs(delta-value)<=0.005,
                 'M1 return mismatches original index close pair')
            valid.append(e)
        else:
            need(e.get('close_price') is None and
                 e.get('prior_close_price') is None and
                 e.get('signed_return_pct') is None,
                 'M1 missing/holiday cannot be fabricated as 0% return')
            need(e.get('session_status') != 'COMPLETED',
                 'M1 noneligible status contradictory to completed market')
    need(orders==set(range(1,len(COUNTRIES)+1)),
         'M1 selection order must cover all 27 requested countries')
    need(len(valid)>=4,
         'M1 insufficient valid market coverage to justify a world graphic')
    return valid


def _project(pt):
    x,y=pt
    return (72+(x+180)/360*936, 462+(81-y)/141*388)


def _paths(f):
    parts=[f['coordinates']] if f['type']=='Polygon' else f['coordinates']
    lines=[]
    for poly in parts:
        for ring in poly:
            if len(ring)<4:
                continue
            coords=[_project(c) for c in ring]
            # Split any date-line jump instead of drawing a false line across Earth.
            seg=[]
            for k,(x,y) in enumerate(coords):
                if seg and abs(x-seg[-1][0])>480:
                    if len(seg)>=3:
                        lines.append('M '+' L '.join(f'{a:.1f},{b:.1f}' for a,b in seg)+' Z')
                    seg=[]
                seg.append((x,y))
            if len(seg)>=3:
                lines.append('M '+' L '.join(f'{a:.1f},{b:.1f}' for a,b in seg)+' Z')
    return ' '.join(lines)


def _fill(v):
    if abs(v)<1e-10:
        return ZERO
    a=abs(v)
    i=0 if a<0.5 else 1 if a<1 else 2 if a<2 else 3
    return PALETTE_POS[i] if v>0 else PALETTE_NEG[3-i]


def render_global_map(p, logo_png=None, status='DRAFT', geometry_path=GEOMETRY):
    need(status in ('DRAFT','RELEASE'), 'M1 mode invalid')
    geo=load_geometry(geometry_path)
    elig=validate_map_issue(p,geo)
    if status=='RELEASE':
        need(p['rights_note']=='REVIEWED_FOR_EXACT_USE' and
             p['universe_review']=='COVERAGE_VALIDATED' and
             p['benchmark_registry_status']=='INDEPENDENTLY_VERIFIED',
             'M1 RELEASE requires reviewed 27-country/index/geography/data rights')
        need(logo_png is not None and
             hashlib.sha256(logo_png).hexdigest()==APPROVED_LOGO_SHA256 and
             p.get('brand_logo_sha256')==APPROVED_LOGO_SHA256,
             'M1 RELEASE exact approved brand master required')
    byid={e['economy_id']:e for e in p['evidence']}
    out=[
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
        rect(0,0,W,H,BG,0),
        '<defs><clipPath id="mapView"><rect x="68" y="454" width="944" height="395"/></clipPath>'
        '<clipPath id="sealClip"><circle cx="110" cy="97" r="38"/></clipPath></defs>',
        f'<circle cx="110" cy="97" r="39" fill="{IVORY}"/>',
    ]
    if logo_png:
        enc=base64.b64encode(logo_png).decode('ascii')
        out.append('<image x="72" y="59" width="76" height="76" '
                   'preserveAspectRatio="xMidYMid slice" clip-path="url(#sealClip)" '
                   'href="data:image/png;base64,'+enc+'"/>')
    else:
        out.append(txt(110,111,'P',39,PINE,800,anchor='middle'))
    out.extend([
        txt(169,102,'PAM',29,LIGHT,800),
        txt(267,102,'/  GLOBAL EQUITY MAP',22,MUTED,600),
        txt(1012,103,p['issue_id'],20,TEAL,600,anchor='end'),
        rule(68,147,1012,147,GRID,2),
        txt(68,183,'COUNTRY INDEX RETURNS  /  LOCAL CURRENCY',19,TEAL,700),
    ])
    out.extend(paragraph(68,249,p['headline'],name='headline',chars=31,
                         max_lines=2,size=49,leading=59,width=944,weight=800))
    out.extend(paragraph(68,373,p['deck'],name='deck',chars=58,max_lines=2,
                         size=23,leading=29,width=944,color=MUTED))
    out.append(txt(68,433,'LATEST COMPLETED SESSIONS / NOT SYNCHRONIZED',
                   19,TEAL,680))
    out.append(txt(1012,433,f'{len(elig)}/{len(COUNTRIES)} VALID INDICES',
                   20,LIGHT,720,anchor='end'))
    out.append(rect(68,454,944,395,OCEAN,0))
    out.append('<g clip-path="url(#mapView)">')
    for f in geo['features']:
        # This fixed mobile crop ends around 60°S. Exclude Antarctica entirely:
        # PyMuPDF's SVG clip-path handling can otherwise leak polar geometry
        # beneath the legend, which is unacceptable even in a synthetic proof.
        if f['id']=='ATA':
            continue
        d=_paths(f)
        if not d:
            continue
        e=byid.get(f['id'])
        if e is None:
            color=LAND
        elif e['missing_status']=='ELIGIBLE':
            color=_fill(_return(e))
        else:
            color=NO_DATA
        out.append('<path d="'+d+'" fill="'+color+
                   '" fill-rule="evenodd" stroke="'+GRID+'" stroke-width=".7"/>')
    # Singapore is not present in 110m polygons: always plot its point and
    # return-colored locator, then identify the representation in the footer.
    sg=byid['SGP']
    sx,sy=_project(SGP_POINT)
    sg_color=_fill(_return(sg)) if sg['missing_status']=='ELIGIBLE' else NO_DATA
    out.append(f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="6" fill="{sg_color}" '
               f'stroke="{LIGHT}" stroke-width="2"/>')
    out.append(txt(sx+9,sy-8,'SG',15,LIGHT,750))
    out.append('</g>')
    # Legend values are local-index return percentages, not GDP figures.
    labels=('<-2','-2..-1','-1..-.5','-.5..0',
            '0..+.5','+.5..+1','+1..+2','>+2')
    palette=PALETTE_NEG+PALETTE_POS
    for i,color in enumerate(palette):
        x=68+i*91
        out.append(rect(x,867,88,12,color,0))
        out.append(txt(x+44,899,labels[i],14,MUTED,550,anchor='middle'))
    out.append(rect(823,867,22,12,NO_DATA,0))
    out.append(txt(854,879,'NO VALID CLOSE',17,MUTED,600))
    # True unchanged index close is a distinct neutral swatch, not a missing quote.
    out.append(rect(823,895,22,12,ZERO,0))
    out.append(txt(854,907,'EXACT 0.00%',17,MUTED,600))
    out.append(rule(68,919,1012,919,GRID,2))
    out.append(txt(68,947,'INDEX LEADERS & LAGGARDS',19,TEAL,750))
    out.append(txt(1012,947,'COUNTRY / INDEX / 1 SESSION',17,MUTED,600,anchor='end'))
    ranked=sorted(elig,key=lambda e:(-_return(e),e['economy_id']))
    featured=ranked[:2]+list(reversed(ranked[-2:]))
    labels_prefix=['LEADER','LEADER','LAGGARD','LAGGARD']
    for i,(e,prefix) in enumerate(zip(featured,labels_prefix)):
        y=955+i*49
        if i%2==0:
            out.append(rect(68,y,944,49,'#182E33',0))
        out.append(rule(68,y+48,1012,y+48,GRID,1))
        out.append(put(82,y+31,prefix,17,120,color=TEAL if i<2 else AMBER))
        desc=e['economy_id']+'  /  '+e['instrument_name']
        out.append(put(226,y+31,desc,21,612,weight=600))
        result=_return(e)
        out.append(put(1012,y+31,f'{result:+.2f}%' if round(result,2) else '0.00%',
                       24,145,anchor='end',weight=750))
    out.append(txt(68,1185,'THE READING',18,TEAL,750))
    out.extend(paragraph(225,1185,p['interpretation'],name='interpretation',
                         chars=54,max_lines=2,size=21,leading=27,width=787))
    out.append(rule(68,1254,1012,1254,GRID,2))
    out.append(txt(68,1280,'GEO: NATURAL EARTH (PUBLIC DOMAIN) / SG POINT / INDEX EVIDENCE',
                   18,MUTED,500))
    out.append(put(68,1320,'AS OF '+_dt(p['cutoff_utc'],'cutoff_utc').strftime('%Y-%m-%d %H:%M UTC'),
                   20,500,color=MUTED))
    out.append(txt(1012,1320,'NOT INVESTMENT ADVICE',19,MUTED,550,anchor='end'))
    if status!='RELEASE':
        out.append(rect(720,202,292,48,'#503D25',10,AMBER))
        out.append(txt(866,233,'DRAFT · SYNTHETIC' if
                       p['rights_note']=='SYNTHETIC_LAYOUT_ONLY'
                       else 'DRAFT · NOT AUDITED',
                       17,AMBER,750,anchor='middle'))
    out.append('</svg>')
    svg='\n'.join(out)+'\n'
    ET.fromstring(svg)
    return svg


def run(argv=None):
    ap=argparse.ArgumentParser(description='PAM M1 audited-index world map: offline draft renderer')
    ap.add_argument('issue',type=Path)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--png',type=Path)
    ap.add_argument('--brand-logo',type=Path)
    ap.add_argument('--release-manifest',type=Path)
    args=ap.parse_args(argv)
    try:
        p=json.loads(args.issue.read_text(encoding='utf-8'))
        geo=load_geometry()
        validate_map_issue(p,geo)
        logo=checked_logo(args.brand_logo) if args.brand_logo else None
        if logo is not None:
            need(hashlib.sha256(logo).hexdigest()==p.get('brand_logo_sha256'),
                 'M1 supplied logo is not issue-hash-bound')
        status='DRAFT'
        if args.release_manifest:
            approval=json.loads(args.release_manifest.read_text(encoding='utf-8'))
            release_allowed(p,approval)
            need(logo is not None,'M1 RELEASE requires approved pine logo bytes')
            status='RELEASE'
        svg=render_global_map(p,logo,status)
        png=None
        if args.png:
            import fitz
            page=fitz.open(stream=svg.encode(),filetype='svg')[0]
            pix=page.get_pixmap(matrix=fitz.Matrix(1,1),alpha=False)
            need((pix.width,pix.height)==(W,H),
                 'M1 rendered PNG dimensions unexpectedly changed')
            png=pix.tobytes('png')
        args.output.parent.mkdir(parents=True,exist_ok=True)
        if png is not None:
            args.png.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(svg,encoding='utf-8')
        if png is not None:
            args.png.write_bytes(png)
        print(json.dumps({'status':status,'issue_id':p['issue_id'],
                          'input_sha256':payload_hash(p),'svg':str(args.output),
                          'png':str(args.png) if png else None}))
        return 0
    except (OSError,KeyError,ValueError,TypeError,ImportError,ET.ParseError) as exc:
        print('HOLD:',exc,file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(run())
