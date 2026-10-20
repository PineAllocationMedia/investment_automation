#!/usr/bin/env python3
"""Offline M2 Sector Rotation research plate — source-bound layout only.

No market-data acquisition or publication authority. Synthetic examples are
for design/testing only, never market observations.
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
    W, H, BG, LIGHT, MUTED, TEAL, AMBER, PINE, IVORY, InvalidIssue,
    bounded, checked_logo, iso_dt, need, payload_hash, rect, rule, txt,
    valid_url, wrap, release_allowed,
)

DARK_PANEL = '#172C30'
DIVIDER = '#415A55'
NEUTRAL = '#D5D3C9'
SECTORS = (
    'Communication Services',
    'Consumer Discretionary',
    'Consumer Staples',
    'Energy',
    'Financials',
    'Health Care',
    'Industrials',
    'Information Technology',
    'Materials',
    'Real Estate',
    'Utilities',
)
ID_RE = re.compile(r'^SR-\d{8}-\d{2}$')


def _dt(value, name):
    return datetime.fromisoformat(iso_dt(value, name).replace('Z', '+00:00'))


def _width(value, size):
    def factor(c):
        if c in 'WM@#%&':
            return 1.0
        if c.isupper():
            return 0.78
        if c.islower() or c.isdigit():
            return 0.66
        return 0.34 if c.isspace() else 0.58
    return size * sum(factor(c) for c in value)


def checked_text(x, y, text, size, width, *, color=LIGHT, weight=600,
                 anchor='start'):
    need(_width(str(text), size) <= width,
         'M2 text exceeds safe column; shorten editorial copy accurately')
    return txt(x, y, text, size, color, weight, anchor)


def paragraph(x, y, value, *, name, chars, count, size, leading, width,
              color=LIGHT, weight=500):
    rows = wrap(value, chars, count, name)
    return [checked_text(x, y + i * leading, row, size, width,
                         color=color, weight=weight)
            for i, row in enumerate(rows)]


def _number(item, field, i):
    v = item.get(field)
    need(type(v) in (int, float) and math.isfinite(v) and v > 0,
         f'evidence[{i}].{field} requires a positive finite index level')
    return float(v)


def _returns(item):
    return ((item['close'] / item['lookback_close'] - 1.0) * 100.0,
            (item['close'] / item['prior_close'] - 1.0) * 100.0)


def validate_sector_rotation(p):
    need(isinstance(p, dict), 'M2 issue must be a JSON object')
    need(p.get('template') == 'M2' and p.get('schema_version') == '1.0',
         'M2 template/schema contract mismatch')
    need(p.get('account') == '@therealpam', 'Wrong Blossom account')
    need(isinstance(p.get('issue_id'), str) and ID_RE.fullmatch(p['issue_id']),
         'M2 issue_id must be SR-YYYYMMDD-NN')
    issue_at = _dt(p.get('issue_at'), 'issue_at')
    bounded(p.get('headline'), 'headline', 63)
    bounded(p.get('deck'), 'deck', 103)
    bounded(p.get('interpretation'), 'interpretation', 115)
    bounded(p.get('watch'), 'watch', 67)
    bounded(p.get('caption'), 'caption', 1200)
    need(p.get('universe') == 'US_LARGE_CAP_11_SECTORS',
         'Only explicitly mapped US large-cap 11-sector universe allowed')
    need(p.get('basis') == 'LOCAL_CURRENCY_INDEX_PRICE_RETURN',
         'Do not mix index/ETF, USD/local or total/price return bases')
    need(p.get('lookback_sessions') == 20,
         'Only source-backed 20 eligible trading sessions allowed')
    family = bounded(p.get('index_family'), 'index_family', 34)
    provider = bounded(p.get('source_title'), 'source_title', 28)
    currency = bounded(p.get('currency'), 'currency', 8)
    bounded(p.get('rights_note'), 'rights_note', 160)
    _ = family, provider, currency
    facts = p.get('evidence')
    need(isinstance(facts, list) and len(facts) == len(SECTORS),
         'M2 needs 11 complete sector index records, not a partial heatmap')
    observed, previous, lookback = set(), set(), set()
    sector_names, instrument_ids = set(), set()
    for i, f in enumerate(facts):
        need(isinstance(f, dict), 'M2 evidence must consist of objects')
        sector = bounded(f.get('sector'), f'evidence[{i}].sector', 31)
        need(sector in SECTORS and sector not in sector_names,
             f'evidence[{i}]: unsupported or duplicate sector')
        sector_names.add(sector)
        fid = bounded(f.get('claim_id'), f'evidence[{i}].claim_id', 30)
        need(fid not in instrument_ids, 'Duplicate M2 claim ID')
        instrument_ids.add(fid)
        bounded(f.get('index_id'), f'evidence[{i}].index_id', 25)
        bounded(f.get('verification_note'), f'evidence[{i}].verification_note', 160)
        need(f.get('classification') == 'FACT' and
             f.get('verification') == 'VERIFIED',
             'M2 source status is not eligible for research-plate rendering')
        valid_url(f.get('source_url'), f'evidence[{i}].source_url')
        need(f.get('index_family') == family and f.get('currency') == currency,
             'M2 sector index family or currency is inconsistent')
        if p.get('rights_note') == 'SYNTHETIC_LAYOUT_ONLY':
            need(urlparse(f['source_url']).hostname in ('example.org', 'example.com'),
                 'Synthetic evidence must use harmless example.org/com source URLs')
        _number(f, 'close', i)
        _number(f, 'prior_close', i)
        _number(f, 'lookback_close', i)
        current = _dt(f.get('observed_at'), f'evidence[{i}].observed_at')
        prev = _dt(f.get('prior_observed_at'), f'evidence[{i}].prior_observed_at')
        historic = _dt(f.get('lookback_observed_at'),
                       f'evidence[{i}].lookback_observed_at')
        retrieved = _dt(f.get('retrieved_at'), f'evidence[{i}].retrieved_at')
        need(historic < prev < current <= retrieved <= issue_at,
             'M2 observations/retrieval occur in the wrong order')
        need(issue_at - current <= timedelta(hours=96),
             'M2 observed sector index is stale')
        need(20 <= (current.date() - historic.date()).days <= 45,
             '20-session lookback lacks plausible calendar coverage')
        need(f.get('session_status') == 'COMPLETED',
             'Closed, halted or incomplete market cannot be treated as a return')
        observed.add(current)
        previous.add(prev)
        lookback.add(historic)
        a, b = _returns(f)
        need(abs(a) <= 70 and abs(b) <= 30,
             'Extreme price return needs independent treatment, not template normalization')
        need(abs(b) <= 100, 'M2 daily return outside bounded scope')
    need(sector_names == set(SECTORS),
         'M2 is missing at least one sector')
    need(len(observed) == len(previous) == len(lookback) == 1,
         'M2 mixed index-close sessions are not comparable; HOLD')
    need(next(iter(observed)).utcoffset() is not None,
         'M2 closing observation must include explicit offset')
    # 20 eligible sessions is source metadata, NOT something calendar span proves.
    # An independent auditor must verify source index taxonomy, exact twenty
    # trading-session count, corporate actions and distribution rights.
    ordered = sorted(facts, key=lambda f: (-_returns(f)[0], f['sector']))
    return ordered


def move_text(v):
    return '0.00%' if round(v, 2) == 0 else f'{v:+.2f}%'


def render_sector_rotation(p, logo_png=None, status='DRAFT'):
    need(status in ('DRAFT', 'RELEASE'), 'M2 render mode not allowed')
    ordered = validate_sector_rotation(p)
    if status == 'RELEASE':
        need(logo_png is not None, 'M2 RELEASE needs the approved logo')
        need(p.get('brand_logo_sha256') ==
             hashlib.sha256(logo_png).hexdigest(),
             'M2 exact approved brand hash required')
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
    out.extend([
        txt(169, 102, 'PAM', 29, LIGHT, 800),
        txt(267, 102, '/  SECTOR ROTATION', 23, MUTED, 600),
        txt(1012, 103, p['issue_id'], 20, TEAL, 600, anchor='end'),
        rule(68, 148, 1012, 148, DIVIDER, 2),
        txt(68, 188, 'EQUITY MARKETS  /  20-SESSION PRICE RETURN', 19, TEAL, 680),
    ])
    out.extend(paragraph(68, 253, p['headline'], name='headline',
                         chars=30, count=2, size=49, leading=59, width=944,
                         weight=800))
    out.extend(paragraph(68, 373, p['deck'], name='deck',
                         chars=65, count=2, size=23, leading=29, width=944,
                         color=MUTED))
    close = _dt(ordered[0]['observed_at'], 'observed_at')
    out.append(checked_text(68, 440, p['source_title']+' / '+p['currency']+
                            ' / '+close.strftime('%Y-%m-%d'),
                            19, 635, color=TEAL, weight=700))
    out.append(txt(1012, 440, '11 SECTORS / SAME INDEX FAMILY', 19, MUTED, 650, anchor='end'))
    out.append(rule(68, 457, 1012, 457, DIVIDER, 2))
    out.extend([
        txt(68, 488, 'RANK / SECTOR', 17, MUTED, 650),
        txt(620, 488, '20S PRICE MOVE  /  ZERO', 17, MUTED, 650, anchor='middle'),
        txt(921, 488, '20S %', 17, MUTED, 650, anchor='end'),
        txt(1012, 488, '1D %', 17, MUTED, 650, anchor='end'),
        rule(68, 502, 1012, 502, DIVIDER, 1),
        rule(620, 508, 620, 1064, DIVIDER, 2),
    ])
    returns = [_returns(f) for f in ordered]
    max_abs = max(abs(v[0]) for v in returns)
    scale = max(2, math.ceil(max_abs / 2.0) * 2.0)
    scale = float(scale)
    for i, (f, (long_move, day_move)) in enumerate(zip(ordered, returns)):
        y = 504 + i*49
        out.append(rect(68, y, 944, 48, DARK_PANEL if i % 2 == 0 else BG, 0))
        # Restore the zero axis across alternating fills, so negative/positive
        # bar direction is always anchored to the same value.
        out.append(rule(620, y, 620, y+47, DIVIDER, 1))
        out.append(rule(68, y+48, 1012, y+48, DIVIDER, 1))
        out.append(checked_text(75, y+31, f'{i+1:02d}', 19, 35,
                                color=MUTED, weight=550))
        out.append(checked_text(112, y+31, f['sector'], 20, 299,
                                weight=620))
        length = min(185, abs(long_move)/scale * 185)
        color = TEAL if long_move > 0 else AMBER if long_move < 0 else NEUTRAL
        if length > 0:
            out.append(rect(620 if long_move >= 0 else 620-length,
                            y+24, max(length, 1), 9, color, 0))
        out.append(checked_text(921, y+31, move_text(long_move), 23, 95,
                                weight=700, anchor='end'))
        out.append(checked_text(1012, y+31, move_text(day_move), 21, 90,
                                color=MUTED, weight=600, anchor='end'))
    out.append(txt(68, 1080, 'RANKED 20-SESSION PRICE RETURNS', 16, MUTED, 600))
    out.append(txt(1012, 1080, f'BAR SCALE:  ±{scale:.0f}%', 16, MUTED, 600, anchor='end'))
    positive = sum(v[0] > 0 for v in returns)
    spread = returns[0][0] - returns[-1][0]
    out.extend([
        rule(68, 1091, 1012, 1091, DIVIDER, 2),
        txt(68, 1121, f'BREADTH  {positive}/11 POSITIVE', 19, TEAL, 700),
        txt(1012, 1121, f'LEADER–LAGGARD SPREAD  {spread:.2f} pp',
            19, TEAL, 700, anchor='end'),
        txt(68, 1154, 'READING', 18, AMBER, 730),
    ])
    out.extend(paragraph(197, 1154, p['interpretation'], name='interpretation',
                         chars=53, count=2, size=21, leading=26, width=815))
    out.append(txt(68, 1228, 'WATCH', 18, AMBER, 740))
    out.extend(paragraph(171, 1228, p['watch'], name='watch',
                         chars=60, count=1, size=20, leading=25, width=841))
    out.append(rule(68, 1261, 1012, 1261, DIVIDER, 2))
    out.append(txt(68, 1284, 'FULL ORIGINAL INDEX SERIES / RIGHTS REVIEW IN EVIDENCE',
                   16, MUTED, 500))
    out.append(checked_text(68, 1321,
                            'AS OF '+_dt(p['issue_at'], 'issue_at').strftime('%Y-%m-%d %H:%M %z'),
                            18, 475, color=MUTED, weight=500))
    out.append(txt(1012, 1321, 'NOT INVESTMENT ADVICE', 19,
                   MUTED, 550, anchor='end'))
    if status != 'RELEASE':
        out.append(rect(732, 159, 280, 45, '#503D25', 10, AMBER))
        out.append(txt(872, 188, 'DRAFT · SYNTHETIC TEST' if
                       p.get('rights_note') == 'SYNTHETIC_LAYOUT_ONLY' else
                       'DRAFT · NOT AUDITED', 16, AMBER, 750, anchor='middle'))
    out.append('</svg>')
    svg = '\n'.join(out)+'\n'
    ET.fromstring(svg)
    return svg


def run(argv=None):
    ap = argparse.ArgumentParser(description='Offline source-bound M2 sector rotation designer')
    ap.add_argument('issue', type=Path)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--png', type=Path)
    ap.add_argument('--brand-logo', type=Path)
    ap.add_argument('--release-manifest', type=Path)
    args = ap.parse_args(argv)
    try:
        p = json.loads(args.issue.read_text(encoding='utf-8'))
        validate_sector_rotation(p)
        logo = checked_logo(args.brand_logo) if args.brand_logo else None
        if logo is not None:
            need(p.get('brand_logo_sha256') == hashlib.sha256(logo).hexdigest(),
                 'Brand logo not bound to issue input')
        status = 'DRAFT'
        if args.release_manifest:
            approval = json.loads(args.release_manifest.read_text(encoding='utf-8'))
            release_allowed(p, approval)
            need(p.get('rights_note') == 'REVIEWED_FOR_EXACT_USE',
                 'M2 data redistribution/attribution gate not recorded')
            need(logo is not None, 'Approved master PNG required for release')
            status = 'RELEASE'
        svg = render_sector_rotation(p, logo, status)
        raw_png = None
        if args.png:
            import fitz
            page = fitz.open(stream=svg.encode('utf-8'), filetype='svg')[0]
            pix = page.get_pixmap(matrix=fitz.Matrix(1, 1), alpha=False)
            need((pix.width, pix.height) == (W, H), 'Unexpected M2 PNG resolution')
            raw_png = pix.tobytes('png')
        args.output.parent.mkdir(parents=True, exist_ok=True)
        if raw_png is not None:
            args.png.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(svg, encoding='utf-8')
        if raw_png is not None:
            args.png.write_bytes(raw_png)
        print(json.dumps({'status':status, 'issue_id':p['issue_id'],
                          'input_sha256':payload_hash(p),
                          'svg':str(args.output),
                          'png':str(args.png) if args.png else None}))
        return 0
    except (OSError, ValueError, TypeError, KeyError, ImportError,
            ET.ParseError) as exc:
        print('HOLD:', exc, file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(run())
