#!/usr/bin/env python3
"""PAM E1 Company Lens — deterministic historical-filing research plate.

No SEC download, source authentication, security recommendation, issuer
affiliation or publication action. Numeric display is checked against submitted
source levels; original evidence is still independently audited by a human.
"""
import argparse
import base64
import hashlib
import json
import math
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from xml.etree import ElementTree as ET

from render_macro_lens import (
    W, H, BG, LIGHT, MUTED, TEAL, AMBER, PINE, IVORY, InvalidIssue,
    APPROVED_LOGO_SHA256, bounded, checked_logo, iso_dt, need, payload_hash,
    rect, rule, txt, valid_url, release_allowed, wrap,
    assert_clean_artwork,
)

DIVIDER = '#405A53'
ROW_SHADE = '#172C30'
FILING_TYPES = ('10-K', '10-Q', '8-K')
BASIS = ('GAAP', 'NON_GAAP', 'OPERATING')
ID_RE = re.compile(r'^CL-\d{8}-\d{2}$')
TICKER_RE = re.compile(r'^[A-Z][A-Z0-9.-]{0,8}$')
DISPLAY_RE = re.compile(r'^[+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{1,4})?$')


def as_date(value, name):
    return datetime.fromisoformat(iso_dt(value, name).replace('Z', '+00:00'))


def width_approx(value, size):
    def w(c):
        if c in 'WM@#%&':
            return 1.0
        if c.isupper():
            return 0.78
        if c.islower() or c.isdigit():
            return 0.66
        return 0.34 if c.isspace() else 0.58
    return size * sum(w(c) for c in value)


def safe_text(x, y, value, size, available, *, color=LIGHT, weight=550,
              anchor='start'):
    need(width_approx(str(value), size) <= available,
         'E1 text exceeds allocated readable column; shorten rather than clip')
    return txt(x, y, value, size, color, weight, anchor)


def lines(x, y, text, *, chars, count, size, leading, available, name,
          color=LIGHT, weight=500):
    rows = wrap(text, chars, count, name)
    return [safe_text(x, y + i*leading, row, size, available,
                      color=color, weight=weight) for i, row in enumerate(rows)]


def _real_sec_url(url):
    parsed = urlparse(url)
    return (parsed.scheme == 'https' and parsed.hostname == 'www.sec.gov' and
            parsed.path.startswith('/Archives/edgar/data/') and
            not parsed.username and not parsed.password)


def validate_company_lens(p):
    need(isinstance(p, dict), 'E1 payload must be an object')
    need(p.get('schema_version') == '1.0' and p.get('template') == 'E1',
         'E1 schema/template mismatch')
    need(p.get('account') == '@therealpam', 'Wrong Blossom account')
    need(isinstance(p.get('issue_id'), str) and ID_RE.fullmatch(p['issue_id']),
         'E1 issue_id format must be CL-YYYYMMDD-NN')
    issue_at = as_date(p.get('issue_at'), 'issue_at')
    bounded(p.get('company_name'), 'company_name', 35)
    ticker = bounded(p.get('ticker'), 'ticker', 9)
    need(TICKER_RE.fullmatch(ticker), 'Ticker format invalid')
    cik = bounded(p.get('cik'), 'cik', 10)
    need(re.fullmatch(r'\d{10}', cik), 'CIK must be a padded ten-digit string')
    bounded(p.get('event'), 'event', 71)
    bounded(p.get('headline'), 'headline', 66)
    bounded(p.get('deck'), 'deck', 111)
    bounded(p.get('countercase'), 'countercase', 105)
    bounded(p.get('watch'), 'watch', 67)
    bounded(p.get('caption'), 'caption', 1200)
    fiscal = bounded(p.get('fiscal_period'), 'fiscal_period', 23)
    currency = bounded(p.get('reporting_currency'), 'reporting_currency', 3)
    need(re.fullmatch(r'[A-Z]{3}', currency), 'Reporting currency must be ISO-like')
    need(p.get('document_type') in FILING_TYPES,
         'E1 requires an issuer 10-K/10-Q/8-K filing')
    need(p.get('figure_policy') == 'EXACT_REPORTED_HISTORICAL',
         'E1 does not portray forward guidance as historical reported metrics')
    primary = valid_url(p.get('primary_filing_url'), 'primary_filing_url')
    filed = as_date(p.get('filed_at'), 'filed_at')
    need(filed <= issue_at, 'Filing occurred after issue cutoff')
    status = p.get('rights_note')
    need(status in ('SYNTHETIC_LAYOUT_ONLY', 'REVIEWED_FOR_EXACT_USE'),
         'M2/E1 source rights must be explicitly scoped')
    if status == 'SYNTHETIC_LAYOUT_ONLY':
        need(urlparse(primary).hostname in ('example.org', 'example.com'),
             'Synthetic filing URL must be an example domain')
    else:
        need(_real_sec_url(primary), 'Real E1 requires an original SEC EDGAR archive URL')
        need(cik != '0000000000', 'Real E1 requires the valid padded issuer CIK')
    facts = p.get('evidence')
    need(isinstance(facts, list) and len(facts) == 3,
         'E1 requires exactly three filing-backed historical facts')
    seen = set()
    for i, f in enumerate(facts):
        prefix = f'evidence[{i}]'
        need(isinstance(f, dict), f'{prefix} is not an object')
        claim = bounded(f.get('claim_id'), prefix+'.claim_id', 30)
        need(claim not in seen, 'Duplicate E1 claim ID')
        seen.add(claim)
        bounded(f.get('metric'), prefix+'.metric', 29)
        display = bounded(f.get('display'), prefix+'.display', 16)
        need(DISPLAY_RE.fullmatch(display) is not None,
             f'{prefix}: value display must be a plain numeric level')
        raw = f.get('numeric_value')
        need(type(raw) in (int, float) and math.isfinite(raw),
             f'{prefix}: numeric_value must be a finite number')
        precision = len(display.split('.', 1)[1]) if '.' in display else 0
        need(abs(float(display.replace(',', ''))-raw) <=
             0.5 * 10**(-precision) + 1e-8,
             f'{prefix}: visible figure must match its reported numeric_value')
        bounded(f.get('unit'), prefix+'.unit', 21)
        need(f.get('basis') in BASIS,
             f'{prefix}: identify GAAP / NON_GAAP / OPERATING basis')
        need(f.get('fact_kind') == 'REPORTED_HISTORICAL',
             f'{prefix}: projections/outlooks not interchangeable with historical results')
        need(f.get('fiscal_period') == fiscal,
             f'{prefix}: incompatible fiscal periods; explain separately instead')
        bounded(f.get('meaning'), prefix+'.meaning', 84)
        bounded(f.get('source_section'), prefix+'.source_section', 45)
        bounded(f.get('verification_note'), prefix+'.verification_note', 160)
        src = valid_url(f.get('source_url'), prefix+'.source_url')
        need(src == primary, f'{prefix}: this pilot anchors all three facts to one filing')
        need(f.get('verification') == 'VERIFIED' and
             f.get('classification') == 'FACT',
             f'{prefix} needs independently auditable verified FACT')
        retrieved = as_date(f.get('retrieved_at'), prefix+'.retrieved_at')
        need(filed <= retrieved <= issue_at,
             f'{prefix} retrieved prior to filing or after brief issue cutoff')
    return facts


def draw_company_lens(p, logo_png=None, status='DRAFT'):
    need(status in ('DRAFT', 'RELEASE'), 'E1 mode must be DRAFT or RELEASE')
    facts = validate_company_lens(p)
    if status == 'RELEASE':
        need(p.get('rights_note') == 'REVIEWED_FOR_EXACT_USE',
             'E1 release cannot use synthetic/unreviewed facts')
        need(logo_png is not None and
             hashlib.sha256(logo_png).hexdigest() == APPROVED_LOGO_SHA256 and
             p.get('brand_logo_sha256') == APPROVED_LOGO_SHA256,
             'E1 RELEASE requires exact hash-bound CEO-approved pine PNG')
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
        rect(0, 0, W, H, BG, 0),
        '<defs><clipPath id="sealClip"><circle cx="110" cy="98" r="38"/></clipPath></defs>',
        f'<circle cx="110" cy="98" r="39" fill="{IVORY}"/>',
    ]
    if logo_png:
        enc = base64.b64encode(logo_png).decode('ascii')
        out.append('<image x="72" y="60" width="76" height="76" '
                   'preserveAspectRatio="xMidYMid slice" clip-path="url(#sealClip)" '
                   'href="data:image/png;base64,' + enc + '"/>')
    else:
        out.append(txt(110, 112, 'P', 39, PINE, 800, anchor='middle'))
    demo = p.get('rights_note') == 'SYNTHETIC_LAYOUT_ONLY'
    out.extend([
        txt(169, 102, 'PAM', 29, LIGHT, 800),
        txt(267, 102, '/  COMPANY LENS', 23, MUTED, 600),
        # No internal issue identifier printed on the image.

        rule(68, 149, 1012, 149, DIVIDER, 2),
        safe_text(68, 193, p['company_name'], 25, 760, weight=700),
        safe_text(1012, 193, p['ticker'] + ('  /  DEMO ISSUER' if demo else '  /  SEC FILER'), 19, 348,
                  color=TEAL, weight=600, anchor='end'),
    ])
    out.extend(lines(68, 266, p['headline'], chars=30, count=2,
                     size=49, leading=57, available=944, name='headline',
                     weight=800))
    out.extend(lines(68, 378, p['deck'], chars=62, count=2,
                     size=23, leading=29, available=944, name='deck',
                     color=MUTED))
    out.append(rule(68, 432, 1012, 432, DIVIDER, 2))
    out.append(safe_text(68, 462, p['document_type']+' / '+p['fiscal_period']+
                         ' / '+p['reporting_currency'], 19, 530,
                         color=TEAL, weight=700))
    out.append(safe_text(1012, 462,
                         ('DEMO DATE ' if demo else 'FILED ')+as_date(p['filed_at'], 'filed_at').strftime('%Y-%m-%d'),
                         19, 268, color=MUTED, weight=550, anchor='end'))
    out.append(safe_text(68, 496, p['event'], 22, 922,
                         weight=550))
    out.append(rule(68, 521, 1012, 521, DIVIDER, 2))
    out.append(txt(68, 547, 'THREE REPORTED FACTS', 19, TEAL, 700))
    out.append(txt(1012, 547, 'BASIS / PERIOD / FILING REFERENCE', 17,
                   MUTED, 600, anchor='end'))
    for i, f in enumerate(facts):
        y = 555 + i*167
        out.append(rect(68, y, 944, 166, ROW_SHADE if i % 2 == 0 else BG, 0))
        out.append(rule(68, y+165, 1012, y+165, DIVIDER, 1))
        out.append(txt(84, y+26, f'{i+1:02d}', 18, TEAL, 750))
        out.append(safe_text(133, y+26, f['metric'], 22, 530, weight=690))
        out.append(safe_text(1012, y+59, f['display'], 39, 272,
                             weight=780, anchor='end'))
        out.append(safe_text(1012, y+83, f['unit'], 18, 270,
                             color=MUTED, anchor='end'))
        out.append(safe_text(84, y+65,
                             f['basis']+'  /  '+f['fiscal_period'], 19, 520,
                             color=MUTED, weight=570))
        out.append(safe_text(84, y+94,
                             ('DEMO SOURCE  /  ' if demo else 'SEC FILING  /  ')+f['source_section'], 18, 555,
                             color=MUTED))
        out.append(txt(84, y+122, 'EDITORIAL READING', 16, TEAL, 650))
        out.extend(lines(270, y+122, f['meaning'], chars=52, count=2,
                         size=20, leading=25, available=737,
                         name=f'evidence[{i}].meaning', color=LIGHT))
    out.append(txt(68, 1090, 'COUNTER-CASE', 18, AMBER, 750))
    out.extend(lines(239, 1090, p['countercase'], chars=52, count=2,
                     size=21, leading=29, available=773, name='countercase'))
    out.append(txt(68, 1191, 'WHAT TO MONITOR', 18, AMBER, 740))
    out.extend(lines(285, 1191, p['watch'], chars=48, count=2,
                     size=20, leading=26, available=727, name='watch'))
    out.append(rule(68, 1254, 1012, 1254, DIVIDER, 2))
    out.append(txt(68, 1280, ('FICTIONAL FILING / SOURCE-FREE LAYOUT TEST' if demo else
                              'ORIGINAL SEC SOURCE + LOCATORS IN EVIDENCE RECORD'), 18,
                   MUTED, 500))
    out.append(safe_text(68, 1320,
                         'AS OF '+as_date(p['issue_at'], 'issue_at').strftime('%Y-%m-%d %H:%M %z'),
                         18, 508, color=MUTED))
    out.append(txt(1012, 1320, 'NOT INVESTMENT ADVICE', 19,
                   MUTED, 550, anchor='end'))
    # Genuine-filing previews are visually clean, but still unaudited drafts.
    # Their authorization status is kept in the separate exact-file record.
    if status != 'RELEASE' and demo:
        out.append(rect(720, 205, 292, 46, '#503D25', 10, AMBER))
        out.append(txt(866, 235, 'DRAFT · SYNTHETIC TEST',
                       16, AMBER, 730, anchor='middle'))
    out.append('</svg>')
    svg = '\n'.join(out) + '\n'
    ET.fromstring(svg)
    if not demo:
        assert_clean_artwork(svg)
    return svg


def run(argv=None):
    ap = argparse.ArgumentParser(description='Offline E1 filing-evidence Company Lens renderer')
    ap.add_argument('issue', type=Path)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--png', type=Path)
    ap.add_argument('--brand-logo', type=Path)
    ap.add_argument('--release-manifest', type=Path)
    args = ap.parse_args(argv)
    try:
        p = json.loads(args.issue.read_text(encoding='utf-8'))
        validate_company_lens(p)
        logo = checked_logo(args.brand_logo) if args.brand_logo else None
        if logo is not None:
            need(p.get('brand_logo_sha256') ==
                 hashlib.sha256(logo).hexdigest(),
                 'E1 supplied logo does not match issue hash')
        status = 'DRAFT'
        if args.release_manifest:
            approval = json.loads(args.release_manifest.read_text(encoding='utf-8'))
            release_allowed(p, approval)
            need(p.get('rights_note') == 'REVIEWED_FOR_EXACT_USE',
                 'Source rights review required for E1 publication')
            need(logo is not None, 'Approved pine master required for release')
            status = 'RELEASE'
        svg = draw_company_lens(p, logo, status)
        png = None
        if args.png:
            import fitz
            page = fitz.open(stream=svg.encode('utf-8'), filetype='svg')[0]
            pix = page.get_pixmap(matrix=fitz.Matrix(1, 1), alpha=False)
            need((pix.width, pix.height) == (W, H),
                 'Unexpected E1 PNG dimensions')
            png = pix.tobytes('png')
        args.output.parent.mkdir(parents=True, exist_ok=True)
        if png:
            args.png.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(svg, encoding='utf-8')
        if png:
            args.png.write_bytes(png)
        print(json.dumps({'status':status, 'issue_id':p['issue_id'],
                          'input_sha256':payload_hash(p),
                          'svg':str(args.output),
                          'png':str(args.png) if png else None}))
        return 0
    except (OSError, KeyError, ValueError, TypeError, ImportError,
            ET.ParseError) as exc:
        print(f'HOLD: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(run())
