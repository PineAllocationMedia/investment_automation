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

GEOMETRY = Path(__file__).parent/'assets'/'m1_natural_earth_50m_v5_1_1.json'
# Pin the 177 original country IDs mapped to the genuine public-domain
# Natural Earth 1:50m polygons; geometry upgraded for Arctic/coastal fidelity.
# The background land and eligible colored countries share each same path.
GEO_GIT_BLOB_SHA = '9f298a1bac5923c787a8e2aaf937221da04c4a58'
UPSTREAM_NE_BLOB_SHA = '9d99f26dc470fcdbd08b062c813005acbdf73ccb'
GEO_VERSION = 'NATURAL_EARTH_50M_V5.1.1_PAM_V2'
BASIS = 'DOMESTIC_INDEX_LOCAL_PRICE_RETURN'
ETF_BASIS = 'US_LISTED_COUNTRY_ETF_USD_MARKET_PRICE_RETURN'
ISSUE_RE = re.compile(r'^GM-\d{8}-\d{2}$')
ECONOMY_RE = re.compile(r'^[A-Z]{3}$')
COUNTRIES = (
    'USA','JPN','CHN','IND','DEU','GBR','CAN','AUS','TWN','KOR',
    'BRA','FRA','CHE','MEX','ESP','ITA','NLD','SGP','ZAF','TUR',
    'SAU','EGY','DZA','IDN','VNM','RUS','KAZ','IRN','POL','SWE',
)
# The pinned map-country set has no Singapore polygon, even at 50m; the
# location below is a geographic point, not a fabricated sovereign boundary.
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
    need(geo.get('schema') == 'pam.m1.ne50.geometry.v1' and
         geo.get('source_github_blob_sha') == UPSTREAM_NE_BLOB_SHA and
         geo.get('license') == 'Public domain',
         'M1 geometry provenance or license record has drifted')
    features=geo.get('features')
    need(isinstance(features,list) and len(features)==177,
         'Market Atlas expects 177 pinned Natural Earth 50m country features')
    ids=set()
    for i,f in enumerate(features):
        fid=f.get('id')
        need(isinstance(fid,str) and fid not in ids and
             ECONOMY_RE.fullmatch(fid) is not None,
             f'M1 duplicate/invalid geometry ID at feature {i}')
        ids.add(fid)
        need(f.get('type') in ('Polygon','MultiPolygon'),
             'M1 unsupported country geometry type')
    # The 50m master preserves island groups absent at 110m; never
    # substitute a coarser or different shape for highlighted countries.
    can=next(f for f in features if f['id']=='CAN')
    need(can['type']=='MultiPolygon' and len(can['coordinates'])>=100,
         'Market Atlas geographic fidelity regression: Canadian Arctic polygons lost')
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
    need(len(valid)>=1,
         'Market Atlas requires one genuine qualified return; never fabricate data')
    return valid


def _project(pt, map_top=462, map_height=388):
    x,y=pt
    return (72+(x+180)/360*936, map_top+(81-y)/141*map_height)


def _paths(f, map_top=462, map_height=388):
    parts=[f['coordinates']] if f['type']=='Polygon' else f['coordinates']
    lines=[]
    for poly in parts:
        for ring in poly:
            if len(ring)<4:
                continue
            coords=[_project(c,map_top,map_height) for c in ring]
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



def _render_market_atlas_reference(p, geo, eligible, logo_png, status):
    """CEO's October 20 reference plate. Fixed geometry; only session data change.

    This renders the same 1080 x 1350 composition every day: masthead, single
    headline, session comparison, map, diverging legend, 3+3 league panels,
    breadth/spread and source footer. No alternative design selection.
    """
    dark = BG
    ocean = '#12282C'
    land = '#294344'
    panel = '#173033'
    border = '#36585A'
    soft = '#B5C8C4'
    green = '#78C99D'
    red = '#E67C7A'
    def color(v):
        if v == 0:
            return ZERO
        ratio = min(1.0, abs(v) / scale)**0.68
        light, strong = (('#B2C8BA', '#59B989') if v > 0
                         else ('#C3B1A9', '#C97878'))
        return _hexmix(light, strong, ratio)
    def stat(v):
        return f'{v:+.2f}%' if round(v, 2) else '0.00%'

    ranked = sorted(eligible, key=lambda e: (-_return(e), e['economy_id']))
    # One shared observed scale: exact values, not a misleading fixed +/-2%.
    scale = max(1.0, math.ceil(max(abs(_return(e)) for e in ranked)*10-1e-9)/10)
    selected = {e['economy_id']: e for e in eligible}
    winners_count = min(3, (len(ranked)+1)//2)
    losers_count = min(3, len(ranked)//2)
    leaders = ranked[:winners_count]
    laggards = list(reversed(ranked[-losers_count:])) if losers_count else []
    higher = sum(_return(e)>0 for e in eligible)
    lower = sum(_return(e)<0 for e in eligible)
    unchanged = len(eligible)-higher-lower
    spread = _return(ranked[0])-_return(ranked[-1])
    current = datetime.fromisoformat(p['session_date']).strftime('%b %d, %Y').upper()
    previous = datetime.fromisoformat(p['prior_session_date']).strftime('%b %d, %Y').upper()
    source_names = sorted({e['source_title'] for e in eligible})
    source_label = (source_names[0] if len(source_names)==1
                    else 'MULTIPLE DATED SOURCES')
    # Avoid unreadable source strings without silently changing factual values.
    source_line = ('PRICES: '+source_label.upper()+
                   '  /  U.S. ETF USD EXCHANGE CLOSE')
    if len(source_line)>108:
        source_line = 'PRICES: MULTIPLE DATED SOURCES / U.S. ETF USD EXCHANGE CLOSE'

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
        rect(0,0,W,H,dark,0),
        '<defs><clipPath id="atlasMap"><rect x="68" y="372" width="944" height="429"/></clipPath>'
        '<clipPath id="atlasSeal"><circle cx="113" cy="101" r="49"/></clipPath></defs>',
        f'<circle cx="113" cy="101" r="49" fill="{IVORY}"/>',
    ]
    if logo_png:
        img = base64.b64encode(logo_png).decode('ascii')
        out.append('<image x="64" y="52" width="98" height="98" '
                   'preserveAspectRatio="xMidYMid slice" clip-path="url(#atlasSeal)" '
                   'href="data:image/png;base64,'+img+'"/>')
    else:
        out.append(txt(113,113,'P',43,PINE,800,anchor='middle'))
    out.extend([
        txt(175,99,'PAM / MARKET ATLAS',30,LIGHT,760),
        txt(178,123,'GLOBAL EQUITY ETF PRICE MONITOR',14,TEAL,650),
        rule(68,160,1012,160,border,1),
        txt(68,240,'The world in one U.S. session',49,LIGHT,800),
        txt(68,279,'U.S.-LISTED COUNTRY ETFs  /  USD PRICE MOVES',17,TEAL,680),
        txt(68,324,current+'  vs.  '+previous,22,LIGHT,660),
        txt(1012,322,'REGULAR U.S. CLOSE',13,soft,520,anchor='end'),
        rect(68,372,944,429,ocean,0),
    ])
    # Pale grid behind the authentic 50m polygons, exactly as in the CEO image.
    for x in (225,540,698,855):
        out.append(rule(x,372,x,801,'#254247',0.6))
    for y in (535,626,716):
        out.append(rule(68,y,1012,y,'#254247',0.6))
    out.append('<g clip-path="url(#atlasMap)">')
    for f in geo['features']:
        if f['id']=='ATA':
            continue
        d = _paths(f, 376, 419)
        if not d:
            continue
        e = selected.get(f['id'])
        fill = color(_return(e)) if e is not None else land
        ink = '#6F9589' if e is not None else '#29474A'
        out.append('<path d="'+d+'" fill="'+fill+
                   '" fill-rule="evenodd" stroke="'+ink+
                   '" stroke-width=".72"/>')
    sg = selected.get('SGP')
    if sg is not None:
        sx,sy = _project(SGP_POINT, 376, 419)
        out.append(f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="5" '
                   f'fill="{color(_return(sg))}" stroke="{LIGHT}" stroke-width="1.4"/>')
        out.append(txt(sx+10,sy-8,'SG',14,LIGHT,700))
    out.extend([
        '</g>',
        txt(68,835,'ONE COMPLETED U.S. SESSION  /  FX INCLUDED',15,soft,540),
        txt(1012,835,f'{len(eligible)} MARKETS SHOWN',15,TEAL,700,anchor='end'),
        txt(68,875,f'-{scale:g}%',15,soft,540),
        txt(1012,875,f'+{scale:g}%',15,soft,540,anchor='end'),
    ])
    # Each displayed map color is generated from the same function as this key.
    for i in range(110):
        v=scale*(2*(i+.5)/110-1)
        out.append(rect(116+i*848/110,871,848/110+.2,16,color(v),0))
    out.extend([
        txt(540,906,'0.0%  /  NEUTRAL',14,soft,550,anchor='middle'),
        rect(68,924,19,17,land,0),
        txt(95,937,'NOT PLOTTED',14,soft,560),
        txt(540,937,'RETURN SCALE IS SYMMETRIC',14,soft,560,anchor='middle'),
        txt(1012,937,'SINGAPORE SHOWN AS SG POINT' if sg else
            'COUNTRY ETF PRICE RETURNS',13,soft,540,anchor='end'),
        rule(68,957,1012,957,border,1),
    ])
    for x, items, heading in (
        (68,leaders,'TOP 3 / FRONTRUNNERS'),
        (554,laggards,'BOTTOM 3 / LAGGARDS'),
    ):
        out.extend([rect(x,982,458,237,panel,4),
                    txt(x+21,1019,heading,20,LIGHT,740),
                    rule(x+20,1035,x+438,1035,border,1)])
        for i in range(3):
            row_y=1074+i*52
            if i:
                out.append(rule(x+20,row_y-31,x+438,row_y-31,border,1))
            if i >= len(items):
                out.append(txt(x+21,row_y,'—',19,soft,540))
                continue
            item=items[i]
            value=_return(item)
            out.extend([
                txt(x+21,row_y,item['economy_name'].upper(),17,LIGHT,690),
                txt(x+236,row_y,item['etf_ticker'],16,soft,580),
                txt(x+434,row_y,stat(value),20,green if value>=0 else red,770,
                    anchor='end'),
            ])
    breadth=f'{higher} HIGHER  /  {lower} LOWER'
    if unchanged:
        breadth+=f'  /  {unchanged} FLAT'
    out.extend([
        txt(68,1254,breadth,16,TEAL,670),
        txt(1012,1254,f'{spread:.2f} pp  LEADER-LAGGARD SPREAD',
            16,LIGHT,650,anchor='end'),
        rule(68,1274,1012,1274,border,1),
        txt(68,1296,source_line,12,soft,500),
        txt(68,1318,p['prior_session_date']+' — '+p['session_date']+
            '  /  COUNTRY ETF PROXIES, NOT DOMESTIC INDEX RETURNS',
            12,'#819D9D',500),
        txt(1012,1334,'NOT INVESTMENT ADVICE',13,soft,540,anchor='end'),
    ])
    if status=='DRAFT' and p['rights_note']=='SYNTHETIC_LAYOUT_ONLY':
        out.extend([rect(750,305,262,36,'#503D25',5),
                    txt(881,329,'SYNTHETIC EXAMPLE',15,AMBER,750,anchor='middle')])
    out.append('</svg>')
    svg='\n'.join(out)+'\n'
    ET.fromstring(svg)
    return svg


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
    need(status in ('DRAFT','REVIEW_CANDIDATE','RELEASE'), 'M1 mode invalid')
    geo=load_geometry(geometry_path)
    elig=validate_map_issue(p,geo)
    # Fail only on an actual format deviation, never on an arbitrary number
    # of real observations. The recurring Market Atlas header must not drift.
    if p.get('map_product')=='MARKET_ATLAS_V1':
        need(p.get('headline')=='The world in one U.S. session',
             'Market Atlas V1 fixed headline cannot vary across days')
    etf_mode=p.get('return_basis')==ETF_BASIS
    if status=='REVIEW_CANDIDATE':
        need(p.get('rights_note')=='RESEARCH_PREVIEW' and
             p.get('scan_status')=='RESEARCH_PREVIEW' and
             p.get('return_basis')==ETF_BASIS and
             p.get('artifact_intent')=='EXACT_ARTIFACT_AWAITING_PROMPT3',
             'M1 review candidate only for source-linked real USD ETF facts')
        need(logo_png is not None and
             hashlib.sha256(logo_png).hexdigest()==APPROVED_LOGO_SHA256 and
             p.get('brand_logo_sha256')==APPROVED_LOGO_SHA256,
             'M1 review candidate requires exact CEO-approved pine logo')
    if status=='RELEASE':
        need(p['rights_note'] in ('REVIEWED_FOR_EXACT_USE','PUBLIC_FACTS_QA_PASSED') and
             p['universe_review']=='COVERAGE_VALIDATED' and
             p['benchmark_registry_status']=='INDEPENDENTLY_VERIFIED',
             'M1 RELEASE requires reviewed 30-country/index/geography/data rights')
        need(logo_png is not None and
             hashlib.sha256(logo_png).hexdigest()==APPROVED_LOGO_SHA256 and
             p.get('brand_logo_sha256')==APPROVED_LOGO_SHA256,
             'M1 RELEASE exact approved brand master required')
    # CEO reference image is the single stable Market Atlas visual contract.
    # All other M1 modes retain the existing renderer unchanged.
    if p.get('map_product')=='MARKET_ATLAS_V1' and etf_mode:
        return _render_market_atlas_reference(p, geo, elig, logo_png, status)
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
        txt(267,102,'/  MARKET ATLAS',22,MUTED,600),
        # The GM-YYYYMMDD-NN identifier lives in the issue JSON/manifest,
        # never in the public-facing Market Atlas image.
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
        # Land and colored performances MUST be the same Natural Earth 50m
        # polygon. MultiPolygon Arctic archipelagos/island countries remain
        # intact, with one shared projection/clipping and no overlay mismatch.
        # Antarctica is outside this mobile crop, so exclude it entirely.
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
    # Singapore has no polygon in the pinned 50m country-ID subset. Plot its
    # locator ONLY when its own price return is qualified; otherwise omit it.
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
    out.append(txt(68,947,'ETF LEADERS & LAGGARDS' if etf_mode else
                   'INDEX LEADERS & LAGGARDS',19,TEAL,750))
    out.append(txt(1012,947,'COUNTRY / USD ETF / 1 U.S. SESSION' if etf_mode else
                   'COUNTRY / INDEX / 1 SESSION',17,MUTED,600,anchor='end'))
    ranked=sorted(elig,key=lambda e:(-_return(e),e['economy_id']))
    # MARKET ATLAS V1: permanent 3+3 panel geometry across daily sessions.
    # When data is exceptionally sparse, empty rows are blank rather than
    # inventing a market, moving boxes or blocking the entire artifact.
    winners_count=min(3,(len(ranked)+1)//2)
    losers_count=min(3,len(ranked)//2)
    leaders=ranked[:winners_count]
    laggards=list(reversed(ranked[-losers_count:])) if losers_count else []
    need(not ({e['economy_id'] for e in leaders} &
              {e['economy_id'] for e in laggards}),
         'Market Atlas ranking panels must never duplicate a market')
    for x,items,label,ink in (
            (68,leaders,'TOP 3 FRONTRUNNERS',TEAL),
            (554,laggards,'BOTTOM 3 LAGGARDS',AMBER)):
        out.append(txt(x+10,977,label,16,ink,760))
        for i in range(3):
            row_y=986+i*54
            if i%2==0:
                out.append(rect(x,row_y,458,53,'#182E33',0))
            out.append(rule(x,row_y+52,x+458,row_y+52,GRID,1))
            if i>=len(items):
                out.append(put(x+12,row_y+34,f'{i+1}.  —',21,313,weight=660,color=MUTED))
                continue
            e=items[i]
            if etf_mode:
                desc=f"{i+1}.  {e['economy_id']} / {e['etf_ticker']}"
            else:
                prefix=f"{i+1}.  {e['economy_id']} / "
                desc=prefix+e['instrument_name']
                if _text_width(desc,21)>313:
                    words=e['instrument_name'].split()
                    while words and _text_width(prefix+' '.join(words)+'…',21)>313:
                        words.pop()
                    need(words,'Market Atlas domestic index label cannot fit')
                    desc=prefix+' '.join(words)+'…'
            out.append(put(x+12,row_y+34,desc,21,313,weight=660))
            result=_return(e)
            out.append(put(x+446,row_y+34,
                           f'{result:+.2f}%' if round(result,2) else '0.00%',
                           23,120,anchor='end',weight=750))
    out.append(txt(68,1185,'THE READING',18,TEAL,750))
    out.extend(paragraph(225,1185,p['interpretation'],name='interpretation',
                         chars=54,max_lines=2,size=21,leading=27,width=787))
    out.append(rule(68,1254,1012,1254,GRID,2))
    geography_note=(('GEO: NATURAL EARTH / SG POINT / USD ETF PROXIES' if sg is not None
                    else 'GEO: NATURAL EARTH / USD ETF PROXIES') if etf_mode else
                    ('GEO: NATURAL EARTH / SG POINT / INDEX EVIDENCE' if sg is not None
                     else 'GEO: NATURAL EARTH / INDEX EVIDENCE'))
    out.append(txt(68,1280,geography_note,18,MUTED,500))
    # The session dates remain in the visible deck. Internal render cutoff
    # UTC stays in the source-linked issue/manifest, not the image footer.
    out.append(txt(1012,1320,'NOT INVESTMENT ADVICE',19,MUTED,550,anchor='end'))
    # Synthetic fixtures alone display a watermark. Genuine source-linked
    # Market Atlas maps, including research-state views, are always clean on
    # the image. Audit/CEO state lives in the separate SHA-bound manifest.
    if status=='DRAFT' and p['rights_note']=='SYNTHETIC_LAYOUT_ONLY':
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
