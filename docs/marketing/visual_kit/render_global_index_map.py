#!/usr/bin/env python3
"""PAM M1 index-first global equity choropleth. Offline research graphic ONLY.

Synthetic fixture uses proposed, unverified benchmark names and fake prices.
Production requires audited CEO-selected country coverage and 30 index decisions,
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
    valid_url, payload_hash, checked_logo, rect, rule, txt, wrap,
)

GEOMETRY = Path(__file__).parent/'assets'/'m1_natural_earth_110m_v5_1_1.json'
# Pin the exact rounded 177-feature public-domain Natural Earth snapshot.
GEO_GIT_BLOB_SHA = '8300299de7b831db1b50d0501924cad1f5b067e1'
UPSTREAM_NE_BLOB_SHA = '1e6ab74c7042f97013be69ceec798be8e1aff27d'
GEO_VERSION = 'NATURAL_EARTH_110M_V5.1.1_PAM_V1'
BASIS = 'DOMESTIC_INDEX_LOCAL_PRICE_RETURN'
ETF_BASIS = 'US_LISTED_COUNTRY_ETF_USD_MARKET_PRICE_RETURN'
ISSUE_RE = re.compile(r'^GM-\d{8}-\d{2}$')
ECONOMY_RE = re.compile(r'^[A-Z]{3}$')
COUNTRIES = (
    'USA','JPN','CHN','IND','DEU','GBR','CAN','AUS','TWN','KOR',
    'BRA','FRA','CHE','MEX','ESP','ITA','NLD','SGP','ZAF','TUR',
    'SAU','EGY','DZA','IDN','VNM','RUS','KAZ','IRN','POL','SWE',
)
# Natural Earth 110m omits microstate-scale Singapore. This is a geographic
# locator, not a fabricated polygon or an assertion about legal borders.
SGP_POINT = (103.8198, 1.3521)
MISSING = {'HOLIDAY','CLOSED','STALE','MISSING','INCOMPARABLE'}
# Fixed endpoints, adaptive daily scale. All channels darken with |return|,
# making the fill mathematically monotonic within each sign.
NEG_LIGHT, NEG_DARK = '#F5D4CE', '#982F37'
POS_LIGHT, POS_DARK = '#C9E9D3', '#246B49'
ZERO = '#F0E8D6'  # eligible, exactly unchanged; never ordinary land
PALETTE_NEG = (NEG_DARK, NEG_LIGHT)  # legacy named endpoints, NOT fixed bins
PALETTE_POS = (POS_LIGHT, POS_DARK)
PALETTE_GAMMA = 0.85
PALETTE_MIN_STRENGTH = 0.06
# Non-eligible selections use the same neutral land fill as unselected countries.
# No 'missing data' color is displayed on the public graphic.
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
    # Explicitly separate domestic local-index returns from USD country-ETF
    # proxy prices. The ETF mode has its own mutually exclusive input contract.
    if isinstance(p,dict) and p.get('return_basis')==ETF_BASIS:
        from m1_country_etf_mode import validate_country_etf_issue
        return validate_country_etf_issue(p,geo)
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
    need(p.get('selection_basis')=='CEO_SELECTED_30_COUNTRIES',
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
    need(p.get('scan_status') in ('SYNTHETIC_NOT_RUN','COMPLETE_AUDITED'),
         'M1 requires an explicit full-universe daily scan disposition')
    if p['rights_note']=='SYNTHETIC_LAYOUT_ONLY':
        need(p['universe_review']=='CEO_SELECTED_UNVERIFIED' and
             p['benchmark_registry_status']=='CANDIDATES_UNVERIFIED' and
             p['scan_status']=='SYNTHETIC_NOT_RUN',
             'Demo issue must be explicitly marked as unverified')
    else:
        need(p['universe_review']=='COVERAGE_VALIDATED' and
             p['benchmark_registry_status']=='INDEPENDENTLY_VERIFIED' and
             p['scan_status']=='COMPLETE_AUDITED',
             'Real M1 requires independent country, index and rights review')
    entries=p.get('evidence')
    need(isinstance(entries,list) and len(entries)==len(COUNTRIES),
         'M1 map requires exactly 30 CEO-selected country decisions')
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
        # A real excluded market may have *no* usable original quotation URL.
        # Never fabricate a source simply to satisfy the input schema; the full
        # attempted-source and rejection record belongs in the audit packet.
        source=e.get('original_price_source_url')
        if status=='ELIGIBLE' or source is not None:
            valid_url(source,n+'.original_price_source_url')
            if p['rights_note']=='SYNTHETIC_LAYOUT_ONLY':
                need(urlparse(source).hostname in ('example.org','example.com'),
                     'Synthetic M1 prices must use safe demo URL')
            else:
                need(urlparse(source).hostname not in ('example.org','example.com'),
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
         'M1 selection order must cover all 30 requested countries')
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


def _daily_scale(returns):
    """Symmetric, zero-centered, readable daily range, never clipping facts.

    Minimum ±1 percentage point avoids magnifying very quiet sessions.
    Nice step endpoints are chosen from 1,2,5×powers of ten.
    """
    moves=list(returns)
    need(moves and all(type(x) in (float,int) and math.isfinite(x)
                       for x in moves), 'M1 color scale needs real finite returns')
    observed=max(abs(v) for v in moves)
    target=max(1.0,observed)
    order=10.0**math.floor(math.log10(target))
    for factor in (1,2,5,10):
        cap=factor*order
        if cap>=target-1e-12:
            return cap
    return 10*order


def _hexmix(light,dark,t):
    need(0<=t<=1, 'M1 color interpolation out of range')
    a=tuple(int(light[i:i+2],16) for i in (1,3,5))
    b=tuple(int(dark[i:i+2],16) for i in (1,3,5))
    return '#'+''.join(f'{round(a[i]+(b[i]-a[i])*t):02X}' for i in range(3))


def _fill(v,scale=2.0):
    """Return color intensity increases strictly with |percent move|.

    Tiny observed moves remain colored, and 0% is explicitly not the
    NOT PLOTTED land fill. The cap is printed on the actual map legend.
    """
    need(type(v) in (float,int) and math.isfinite(v) and scale>0,
         'M1 fill needs finite market percent and positive daily scale')
    if v==0:
        return ZERO
    ratio=min(1.0,abs(v)/scale)
    strength=PALETTE_MIN_STRENGTH+(1-PALETTE_MIN_STRENGTH)*ratio**PALETTE_GAMMA
    return _hexmix(*(POS_LIGHT,POS_DARK) if v>0 else (NEG_LIGHT,NEG_DARK),
                   strength)


def _tick(v):
    if v==0:
        return '0%'
    return f'{v:+g}%'


def m1_release_allowed(p, approval):
    """M1-specific SHA-bound approval. Never assume that public facts need a
    per-ticker data licence; require Prompt 3 factual and actual-source-use
    review, plus CEO approval of this exact issue and image.
    """
    need(isinstance(approval,dict) and
         approval.get('input_sha256')==payload_hash(p),
         'M1 release approval missing/stale issue SHA256')
    need(approval.get('independent_audit')=='PASS' and
         approval.get('ceo_approved') is True,
         'M1 independent Prompt 3 PASS and separate CEO post approval required')
    for k in ('auditor_reference','ceo_approval_reference'):
        bounded(approval.get(k),k,140)
    need(p.get('rights_note') in ('REVIEWED_FOR_EXACT_USE','PUBLIC_FACTS_QA_PASSED'),
         'M1 preview/synthetic cannot be directly published')
    need(p.get('brand_logo_sha256')==APPROVED_LOGO_SHA256,
         'M1 exact approved pine-logo hash required')
    if p.get('rights_note')=='PUBLIC_FACTS_QA_PASSED':
        need(p.get('publication_source_use_state')=='NO_KNOWN_RESTRICTION' and
             p.get('fact_audit_reference') and p.get('source_use_review_reference'),
             'M1 public-facts release needs completed factual/terms review')
    # These are signed-off external claims; code cannot impersonate a human auditor.


def render_global_map(p, logo_png=None, status='DRAFT', geometry_path=GEOMETRY):
    need(status in ('DRAFT','RELEASE'), 'M1 mode invalid')
    geo=load_geometry(geometry_path)
    elig=validate_map_issue(p,geo)
    etf_mode=p.get('return_basis')==ETF_BASIS
    if status=='RELEASE':
        need(p['rights_note'] in ('REVIEWED_FOR_EXACT_USE','PUBLIC_FACTS_QA_PASSED') and
             p['universe_review']=='COVERAGE_VALIDATED' and
             p['benchmark_registry_status']=='INDEPENDENTLY_VERIFIED',
             'M1 RELEASE requires reviewed 30-country/index/geography/data rights')
        need(logo_png is not None and
             hashlib.sha256(logo_png).hexdigest()==APPROVED_LOGO_SHA256 and
             p.get('brand_logo_sha256')==APPROVED_LOGO_SHA256,
             'M1 RELEASE exact approved brand master required')
    # Only qualified entries have a visible market overlay. Keep all thirty
    # checked outcomes in the private evidence packet, including exclusions.
    eligible_byid={e['economy_id']:e for e in elig}
    scale=_daily_scale(_return(e) for e in elig)
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
        txt(267,102,'/  GLOBAL ETF MAP' if etf_mode else '/  GLOBAL EQUITY MAP',22,MUTED,600),
        txt(1012,103,p['issue_id'],20,TEAL,600,anchor='end'),
        rule(68,147,1012,147,GRID,2),
        txt(68,183,'US-LISTED COUNTRY ETFs  /  USD PRICE MOVES' if etf_mode else
            'COUNTRY INDEX RETURNS  /  LOCAL CURRENCY',19,TEAL,700),
    ])
    out.extend(paragraph(68,249,p['headline'],name='headline',chars=31,
                         max_lines=2,size=49,leading=59,width=944,weight=800))
    out.extend(paragraph(68,373,p['deck'],name='deck',chars=58,max_lines=2,
                         size=23,leading=29,width=944,color=MUTED))
    out.append(txt(68,433,'ONE COMPLETED U.S. SESSION / FX INCLUDED' if etf_mode else
                   'LATEST COMPLETED SESSIONS / NOT SYNCHRONIZED',
                   19,TEAL,680))
    out.append(txt(1012,433,f'{len(elig)} MARKETS SHOWN',
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
        e=eligible_byid.get(f['id'])
        color=_fill(_return(e),scale) if e is not None else LAND
        # A narrow pale border keeps even very light selected countries
        # distinguishable from dark, unplotted land at mobile feed size.
        border='#A8BFB5' if e is not None else GRID
        width='1.05' if e is not None else '.7'
        out.append('<path d="'+d+'" fill="'+color+
                   '" fill-rule="evenodd" stroke="'+border+
                   '" stroke-width="'+width+'"/>')
    # Singapore is absent from 110m polygons. Plot its labeled locator ONLY
    # when its own index return is qualified; otherwise leave no marker.
    sg=eligible_byid.get('SGP')
    if sg is not None:
        sx,sy=_project(SGP_POINT)
        out.append(f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="6" '
                   f'fill="{_fill(_return(sg),scale)}" stroke="{LIGHT}" stroke-width="2"/>')
        out.append(txt(sx+9,sy-8,'SG',15,LIGHT,750))
    out.append('</g>')
    # Source-of-truth legend: sample the same continuous color function used
    # for every country, with exact session-dependent tick values.
    bar_x,bar_w,samples=68,684,76
    for i in range(samples):
        value=scale*(2*(i+0.5)/samples-1)
        out.append(rect(bar_x+i*bar_w/samples,867,
                        bar_w/samples+0.05,13,_fill(value,scale),0))
    for i,v in enumerate((-scale,-scale/2,0,scale/2,scale)):
        x=bar_x+i*bar_w/4
        anchor='start' if i==0 else 'end' if i==4 else 'middle'
        out.append(txt(x,898,_tick(v),14,MUTED,600,anchor=anchor))
    # Zero is a separate covered state. Missing countries use the SAME land
    # fill as unselected countries, but the legend explicitly explains it.
    out.append(rect(770,867,21,13,ZERO,0))
    out.append(txt(798,879,'EXACT 0.00%',12,MUTED,600))
    out.append('<rect x="900" y="867" width="21" height="13" '
               f'fill="{LAND}" stroke="{LIGHT}" stroke-width="1"/>')
    out.append(txt(927,879,'NOT PLOTTED',12,MUTED,650))
    out.append(rule(68,919,1012,919,GRID,2))
    out.append(txt(68,947,'TOP 3 FRONTRUNNERS / TOP 3 LAGGARDS',19,TEAL,750))
    # Four/five qualified markets can appear in both top/bottom 3.
    # Preserve the 4-market research-preview threshold without inventing extra
    # markets or hiding the overlap from readers.
    small_universe=len(elig)<6
    scope=('RANKINGS OVERLAP / '+str(len(elig))+' SHOWN' if small_universe else
           'USD COUNTRY ETFs / 1 U.S. SESSION' if etf_mode else
           'COUNTRY INDICES / COMPLETED SESSIONS')
    out.append(txt(1012,947,scope,14,MUTED,600,anchor='end'))
    # Always show 3 ranked frontrunners and 3 ranked laggards, with stable
    # alphabetical country tie-breaking in each direction.
    frontrunners=sorted(elig,key=lambda e:(-_return(e),e['economy_id']))[:3]
    laggards=sorted(elig,key=lambda e:(_return(e),e['economy_id']))[:3]
    featured=frontrunners+laggards
    labels_prefix=[f'FRONT #{i}' for i in range(1,4)]+[
                   f'LAGGARD #{i}' for i in range(1,4)]
    row_height=34
    for i,(e,prefix) in enumerate(zip(featured,labels_prefix)):
        y=955+i*row_height
        if i%2==0:
            out.append(rect(68,y,944,row_height,'#182E33',0))
        out.append(rule(68,y+row_height-1,1012,y+row_height-1,GRID,1))
        out.append(put(82,y+24,prefix,16,128,color=TEAL if i<3 else AMBER))
        desc=(e['economy_id']+'  /  '+e['etf_ticker']+'  /  '+
              e['instrument_name'].replace('iShares ','').replace('Vanguard ','').replace('VanEck ','').replace(' ETF','')
              if etf_mode else e['economy_id']+'  /  '+e['instrument_name'])
        out.append(put(226,y+24,desc,19,612,weight=600))
        result=_return(e)
        out.append(put(1012,y+24,f'{result:+.2f}%' if round(result,2) else '0.00%',
                       21,145,anchor='end',weight=750))
    out.append(txt(68,1185,'THE READING',18,TEAL,750))
    out.extend(paragraph(225,1185,p['interpretation'],name='interpretation',
                         chars=54,max_lines=2,size=21,leading=27,width=787))
    out.append(rule(68,1254,1012,1254,GRID,2))
    geography_note=(('GEO: NATURAL EARTH / SG POINT / USD ETF PROXIES' if sg is not None
                    else 'GEO: NATURAL EARTH / USD ETF PROXIES') if etf_mode else
                    ('GEO: NATURAL EARTH / SG POINT / INDEX EVIDENCE' if sg is not None
                     else 'GEO: NATURAL EARTH / INDEX EVIDENCE'))
    out.append(txt(68,1280,geography_note,18,MUTED,500))
    out.append(put(68,1320,'AS OF '+_dt(p['cutoff_utc'],'cutoff_utc').strftime('%Y-%m-%d %H:%M UTC'),
                   20,500,color=MUTED))
    out.append(txt(1012,1320,'NOT INVESTMENT ADVICE',19,MUTED,550,anchor='end'))
    if status!='RELEASE':
        out.append(rect(720,202,292,48,'#503D25',10,AMBER))
        out.append(txt(866,233,'DRAFT · SYNTHETIC' if
                       p['rights_note']=='SYNTHETIC_LAYOUT_ONLY'
                       else 'DRAFT · REAL DATA' if
                       p['rights_note']=='RESEARCH_PREVIEW'
                       else 'DRAFT · PENDING POST APPROVAL',
                       17,AMBER,750,anchor='middle'))
    out.append('</svg>')
    svg='\n'.join(out)+'\n'
    ET.fromstring(svg)
    return svg


def run(argv=None):
    ap=argparse.ArgumentParser(description='PAM M1 local-index or USD country-ETF map: audited offline renderer')
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
            m1_release_allowed(p,approval)
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
