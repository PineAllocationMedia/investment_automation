#!/usr/bin/env python3
"""Offline PAM Macro Lens SVG/PNG renderer. Layout only, never a market-data verifier.

Real-data previews have clean artwork; audit/CEO status remains separate and
SHA-bound. Synthetic examples retain conspicuous markings. No network access.
"""
import argparse
import base64
import hashlib
import json
import math
import re
import sys
import struct
from t1_evidence_plus import validate_t1_plus, draw_t1_plus, used_evidence
from artwork_status_guard import assert_clean_artwork, synthetic_issue
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from xml.sax.saxutils import escape

W, H = 1080, 1350
# Blossom profile identity: warm ivory seal, forest-green pine-cone illustration.
# Preserve subdued dark editorial canvas; eliminate the old neon/teal brand badge.
BG, PANEL, LIGHT = '#11242A', '#1A3233', '#F4F0E6'
MUTED, TEAL, AMBER = '#BDC8BE', '#A6CBB1', '#E6C592'
PINE, IVORY = '#284936', '#F4F0E6'
# Exact CEO-approved RECONSTRUCTED v0.1 master; do not treat as historical original.
# Source of asset metadata: visual_kit/assets/PAM_MACRO_LENS_LOGO_RECONSTRUCTED_v0.1.json
APPROVED_LOGO_SHA256 = 'a352aa5dc6b9c5f1a142a36747eb4361a2d22cbc628805ee9a4e28da51ca9c75'
FONT = 'DejaVu Sans, Liberation Sans, Arial, sans-serif'
ID_RE = re.compile(r'^ML-\d{8}-\d{2}$')
SAFE_TOKEN = re.compile(r'^[A-Za-z0-9._:/+()%,&!?—–−= #\-]+$')

class InvalidIssue(ValueError):
    pass


def need(cond, msg):
    if not cond:
        raise InvalidIssue(msg)


def bounded(value, name, max_len, required=True):
    need(isinstance(value, str), f'{name} must be text')
    value = value.strip()
    need(not required or value, f'{name} is required')
    need(len(value) <= max_len, f'{name} exceeds {max_len} characters')
    need(not any(ord(c) < 32 for c in value), f'{name} contains control characters')
    need(not any(c in value for c in '\u2028\u2029'), f'{name} contains unexpected line separators')
    return value


def iso_dt(value, name):
    val = bounded(value, name, 40)
    try:
        parsed = datetime.fromisoformat(val.replace('Z', '+00:00'))
    except ValueError as exc:
        raise InvalidIssue(f'{name} must be ISO-8601') from exc
    need(parsed.tzinfo is not None and parsed.utcoffset() is not None,
         f'{name} must include explicit UTC offset')
    return val


def valid_url(value, name):
    val = bounded(value, name, 500)
    x = urlparse(val)
    need(x.scheme == 'https' and bool(x.netloc) and not x.username and not x.password,
         f'{name} must be an HTTPS source URL with no credentials')
    return val


def validate(payload):
    need(isinstance(payload, dict), 'Root must be a JSON object')
    need(payload.get('schema_version') == '1.0', 'Unsupported schema_version')
    typ = payload.get('template')
    need(typ in ('T1', 'T2', 'T3'), 'template must be T1, T2 or T3')
    need(ID_RE.fullmatch(payload.get('issue_id', '')) is not None, 'Bad issue ID')
    bounded(payload.get('headline'), 'headline', 63)
    bounded(payload.get('deck'), 'deck', 108)
    bounded(payload.get('caption'), 'caption', 1200)  # Stored for exact input-hash approval, not drawn
    bounded(payload.get('blind_spot'), 'blind_spot', 128)
    bounded(payload.get('tripwire'), 'tripwire', 110)
    iso_dt(payload.get('issue_at'), 'issue_at')
    need(payload.get('account') == '@therealpam', 'Only @therealpam is supported')
    evidence = payload.get('evidence')
    need(isinstance(evidence, list) and len(evidence) >= (2 if typ in ('T2', 'T3') else 1),
         f'{typ} requires enough evidence records')
    ids = set()
    for i, f in enumerate(evidence):
        need(isinstance(f, dict), 'Each evidence record must be an object')
        cid = bounded(f.get('claim_id'), f'evidence[{i}].claim_id', 30)
        need(cid not in ids, 'Duplicate claim_id')
        ids.add(cid)
        for key, n in [('label', 34), ('display', 24), ('unit', 24), ('period', 34),
                       ('source_title', 75), ('verification_note', 160)]:
            bounded(f.get(key), f'evidence[{i}].{key}', n)
        iso_dt(f.get('observed_at'), f'evidence[{i}].observed_at')
        iso_dt(f.get('retrieved_at'), f'evidence[{i}].retrieved_at')
        valid_url(f.get('source_url'), f'evidence[{i}].source_url')
        need(f.get('verification') == 'VERIFIED', f'evidence[{i}] must be verified in the fact sheet')
        need(f.get('classification') == 'FACT', f'evidence[{i}] must be classified FACT')
    used = payload.get('fact_ids')
    need(isinstance(used, list) and len(used) == (1 if typ == 'T1' else 2),
         f'{typ} requires its expected fact IDs')
    need(len(used) == len(set(used)) and all(x in ids for x in used), 'Invalid fact_ids')
    chosen = [next(f for f in evidence if f['claim_id'] == x) for x in used]
    cap = {'T1': 13, 'T2': 11, 'T3': 12}[typ]
    need(all(len(f['display']) <= cap for f in chosen),
         f'{typ} display value too wide for its data panel; use a truthful shorter representation')
    if typ == 'T1':
        steps = payload.get('mechanism')
        need(isinstance(steps, list) and len(steps) == 3, 'T1 requires three mechanism stages')
        for i, step in enumerate(steps):
            bounded(step, f'mechanism[{i}]', 39)
        layout = payload.get('t1_layout', 'CLASSIC')
        need(layout in ('CLASSIC', 'RESEARCH_NOTE'), 'Unsupported T1 layout')
        need(layout == 'CLASSIC' or payload.get('t1_variant', 'CLASSIC') == 'CLASSIC',
             'Research-note layout currently supports T1 Classic only')
        validate_t1_plus(payload, chosen, evidence, need, bounded)
    else:
        need(not any(x in payload for x in ('t1_layout', 't1_variant', 'support_fact_ids', 'mini_chart')),
             'Evidence+ fields are only supported for T1')
        bounded(payload.get('interpretation'), 'interpretation', 130)
    if typ == 'T2':
        # Comparing readings from different sessions can mislead even when both are true.
        need(chosen[0]['period'] == chosen[1]['period'], 'T2 periods must align')
        need(chosen[0]['observed_at'] == chosen[1]['observed_at'], 'T2 observed_at must align')
    if typ == 'T3':
        need(chosen[0]['label'] == chosen[1]['label'], 'T3 needs the same historical metric label')
        need(chosen[0]['unit'] == chosen[1]['unit'], 'T3 historical units differ')
        need(chosen[0]['period'] != chosen[1]['period'], 'T3 needs two distinct periods')
        need(chosen[0]['observed_at'] != chosen[1]['observed_at'], 'T3 observations must differ')
    # This is structural validation, not external verification.
    return chosen


def wrap(value, max_chars, max_lines, name):
    words = value.strip().split()
    lines, line = [], ''
    for word in words:
        need(len(word) <= max_chars, f'{name} has an overlong word')
        if line and len(line) + len(word) + 1 > max_chars:
            lines.append(line)
            line = word
        else:
            line = f'{line} {word}'.strip()
    if line:
        lines.append(line)
    need(len(lines) <= max_lines, f'{name} would overflow layout; shorten copy')
    return lines


def txt(x, y, val, size=31, color=LIGHT, weight=500, anchor='start', extra=''):
    return (f'<text x="{x}" y="{y}" text-anchor="{anchor}" fill="{color}" '
            f'font-size="{size}" font-weight="{weight}" font-family="{FONT}" {extra}>'
            f'{escape(str(val))}</text>')


def multiline(x, y, value, chars, max_lines, size=33, color=LIGHT, weight=500,
              lead=47, name='text'):
    lines = wrap(value, chars, max_lines, name)
    return ''.join(txt(x, y + i*lead, line, size, color, weight) for i, line in enumerate(lines))


def rect(x, y, w, h, fill=PANEL, radius=22, stroke=None):
    border = f' stroke="{stroke}" stroke-width="2"' if stroke else ''
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}"{border}/>'


def rule(x1, y1, x2, y2, stroke=TEAL, sw=3):
    return f'<path d="M {x1} {y1} L {x2} {y2}" stroke="{stroke}" stroke-width="{sw}" fill="none"/>'


def arrow(x, y, length=70):
    return rule(x, y, x, y + length) + f'<path d="M{x-10} {y+length-11} L{x} {y+length} L{x+10} {y+length-11}" fill="none" stroke="{TEAL}" stroke-width="3"/>'


def checked_logo(path):
    """Load clean square PNG bytes; release further restricts to CEO-approved asset hash."""
    raw = Path(path).read_bytes()
    need(len(raw) <= 2_000_000 and len(raw) >= 24,
         'Brand logo PNG must be between 24 bytes and 2MB')
    need(raw[:8] == b'\x89PNG\r\n\x1a\n' and raw[12:16] == b'IHDR',
         'Brand logo must be a real PNG')
    width, height = struct.unpack('>II', raw[16:24])
    need(width == height and 128 <= width <= 2048,
         'Brand logo must be square (at least 128×128, at most 2048×2048)')
    return raw


def common(p, typ, logo_png=None):
    # Real user-provided logo, if supplied, is embedded as image bytes in self-contained SVG.
    # Fallback is a typographic draft seal, never a fake pine-cone imitation.
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
           rect(0, 0, W, H, BG, 0),
           '<defs><clipPath id="pamSealClip"><circle cx="110" cy="99" r="38"/></clipPath></defs>',
           '<circle cx="110" cy="99" r="39" fill="'+IVORY+'"/>']
    if logo_png is not None:
        encoded = base64.b64encode(logo_png).decode('ascii')
        out.append('<image x="72" y="61" width="76" height="76" preserveAspectRatio="xMidYMid slice" '
                   'clip-path="url(#pamSealClip)" href="data:image/png;base64,'+encoded+'"/>')
    else:
        out.append(txt(110, 111, 'P', 40, PINE, 800, anchor='middle'))
    out.extend([txt(169, 103, 'PAM', 29, LIGHT, 800),
           txt(263, 102, '/  THE MACRO LENS', 21, MUTED, 600),
           # Tracking issue IDs and renderer family codes are private metadata.
           rule(68, 153, 1012, 153, '#3B554F', 2),
           txt(68, 195, p['issue_at'][:10]+'  /  @therealpam', 19, MUTED, 600),
           multiline(68, 276, p['headline'], 27, 2, 54, LIGHT, 800, 65, 'headline'),
           multiline(68, 403, p['deck'], 57, 2, 24, MUTED, 400, 37, 'deck')])
    return out


def footer(out, p, sources, asof, status):
    if p['template'] == 'T1':
        # T1 mobile legibility: source attribution and observation time must
        # remain readable when the 1080px graphic is scaled to a 390px feed.
        # Two lines accommodate long provenance without truncating it.
        source_lines = wrap('SOURCES: '+sources, 42, 2, 'T1 source attribution')
        # Failing closed on exceptionally wide glyphs matters: character count
        # alone does not guarantee visual fit. This is a conservative estimate,
        # not an SVG font-metrics engine. Final PNG must still be inspected.
        def estimated_line_px(line):
            return 32 * sum(
                1.0 if c in 'MW@#%&' else
                0.78 if c.isupper() else
                0.64 if c.isalnum() else
                0.37 if c.isspace() else 0.56 for c in line)
        need(all(estimated_line_px(line) <= 900 for line in source_lines),
             'T1 source attribution may exceed safe footer width; use concise source titles')
        # Evidence+ WATCH ends at y=1162 (Classic ends at y=1110).
        # Reserving extra height for wrapped attribution avoids row collisions.
        two_lines = len(source_lines) == 2
        separator_y = 1172 if two_lines else 1210
        first_y = 1218 if two_lines else 1255
        bottom_y = 1320 if two_lines else 1315
        out.append(rule(68, separator_y, 1012, separator_y, '#3B554F', 2))
        for i, source_line in enumerate(source_lines):
            out.append(txt(68, first_y + i*50, source_line, 32, MUTED, 600))
        out.extend([
            txt(68, bottom_y, 'AS OF '+asof, 29, MUTED, 500),
            txt(1012, bottom_y, 'NOT INVESTMENT ADVICE', 29, MUTED, 500, anchor='end')
        ])
    else:
        # Preserve existing T2/T3 rendering unchanged.
        out.extend([rule(68, 1224, 1012, 1224, '#3B554F', 2),
                    txt(68, 1262, 'SOURCES: '+sources, 15, MUTED, 500),
                    txt(68, 1287, 'AS OF '+asof+'  ·  NOT INVESTMENT ADVICE', 15, MUTED, 500)])
    if status != 'RELEASE' and synthetic_issue(p):
        out.append(rect(710, 151, 302, 53, '#503D25', 12, AMBER))
        out.append(txt(861, 185, 'DRAFT · SYNTHETIC TEST', 18, AMBER, 750, anchor='middle'))
    return out

def t1(out, p, f):
    out.append(rect(68, 481, 944, 156, '#204039'))
    out.append(txt(97, 520, '01  /  THE VERIFIED SIGNAL', 21, TEAL, 800))
    out.append(txt(97, 587, f['display'], 49, LIGHT, 800))
    out.append(txt(470, 580, f['label'], 27, LIGHT, 600))
    out.append(txt(470, 610, f['unit']+' · '+f['period'], 19, MUTED, 500))
    out.append(txt(68, 692, '02  /  HOW IT TRAVELS', 21, TEAL, 800))
    for i, step in enumerate(p['mechanism']):
        x = 68 + i * 325
        out.append(rect(x, 730, 295, 119, PANEL, 17))
        out.append(multiline(x+20, 781, step, 19, 2, 26, LIGHT, 650, 36, f'mechanism[{i}]'))
        if i < 2:
            out.append(rule(x+299, 787, x+319, 787, TEAL, 3))
    out.append(txt(68, 909, '03  /  THE BLIND SPOT', 20, TEAL, 800))
    out.append(multiline(68, 954, p['blind_spot'], 64, 2, 25, LIGHT, 500, 36, 'blind_spot'))
    out.append(rect(68, 1050, 944, 60, '#32433D', 10))
    out.append(multiline(89, 1088, 'WATCH: '+p['tripwire'], 91, 1, 19, AMBER, 600, 23, 'tripwire'))



def t1_research_note(out, p, f):
    """Opt-in sober T1 Classic layout. Facts/release manifest remain unchanged.

    The three explanatory stages are a ruled editorial grid, not floating
    classroom cards. An over-wide item fails closed instead of being clipped.
    """
    def estimated_width(value, size):
        def weight(ch):
            if ch in 'WM@#%&':
                return 1.0
            if ch.isupper():
                return 0.78
            if ch.islower() or ch.isdigit():
                return 0.59
            return 0.33 if ch.isspace() else 0.53
        return size * sum(weight(c) for c in value)

    def lines(x, y, value, *, chars, cap, size, leading, name,
              color=LIGHT, weight=500, width=None):
        rows = wrap(value, chars, cap, name)
        max_width = (1012 - x - 5) if width is None else width
        need(all(estimated_width(row, size) <= max_width for row in rows),
             f'{name} exceeds research-note safe line width; shorten')
        return [txt(x, y + i*leading, row, size, color, weight)
                for i, row in enumerate(rows)]

    out.extend([
        rule(68, 464, 1012, 464, '#46615A', 2),
        txt(68, 504, 'MARKET OBSERVATION', 20, TEAL, 750),
        txt(1012, 504, 'PRIMARY SERIES / '+f['period'].upper(),
            18, MUTED, 600, anchor='end')
    ])
    length = len(f['display'])
    signal_size = 66 if length <= 5 else 51 if length <= 8 else 39 if length <= 11 else 31
    need(estimated_width(f['display'], signal_size) <= 435,
         'Signal too wide for research-note signal area')
    out.append(txt(68, 594, f['display'], signal_size, LIGHT, 750))
    out.extend(lines(528, 535, f['label'], chars=27, cap=2, size=28, leading=38,
                     name='signal.label', weight=700))
    out.extend(lines(528, 614, f['unit'], chars=24, cap=1, size=21, leading=25,
                     name='signal.unit', color=MUTED))
    out.extend(lines(528, 651, f['period'], chars=34, cap=1, size=20, leading=25,
                     name='signal.period', color=MUTED))
    out.append(rule(68, 679, 1012, 679, '#46615A', 2))
    out.append(txt(68, 720, 'TRANSMISSION / POSSIBLE CHANNELS', 20, TEAL, 750))
    for i, step in enumerate(p['mechanism']):
        x = 68 + i*325
        out.append(txt(x, 756, f'{i+1:02}', 19, MUTED, 500))
        out.extend(lines(x, 807, step, chars=19, cap=2, size=27, leading=37,
                         name=f'mechanism[{i}]', weight=600,
                         width=(282 if i < 2 else 289)))
        if i < 2:
            out.append(rule(x+298, 751, x+298, 857, '#46615A', 2))
    out.append(rule(68, 886, 1012, 886, '#46615A', 2))
    out.append(txt(68, 928, 'SECOND-ORDER CONSIDERATION', 20, TEAL, 750))
    out.extend(lines(68, 973, p['blind_spot'], chars=64, cap=2, size=26,
                     leading=34, name='blind_spot'))
    out.append(rule(68, 1040, 1012, 1040, '#46615A', 2))
    out.append(txt(68, 1080, 'WHAT WOULD CHANGE THE VIEW?', 21, AMBER, 700))
    out.extend(lines(68, 1123, p['tripwire'], chars=60, cap=2, size=25,
                     leading=32, name='tripwire'))


def t2(out, p, a, b):
    out.append(txt(68, 488, '01  /  TWO SIGNALS', 21, TEAL, 800))
    for x, f, code in [(68,a,'A'),(555,b,'B')]:
        out.append(rect(x, 515, 457, 292, PANEL))
        out.append(txt(x+26, 558, code+'  /  '+f['label'].upper(), 20, TEAL, 700))
        out.append(txt(x+26, 646, f['display'], 58, LIGHT, 850))
        out.append(txt(x+26, 692, f['unit'], 23, LIGHT, 550))
        out.append(txt(x+26, 760, f['period'], 20, MUTED, 500))
    out.append(txt(68, 872, '02  /  WHY BOTH CAN BE TRUE', 21, TEAL, 800))
    out.append(multiline(68, 925, p['interpretation'], 63, 2, 28, LIGHT, 550, 41, 'interpretation'))
    out.append(txt(68, 1022, 'THE BLIND SPOT', 19, TEAL, 750))
    out.append(multiline(68, 1062, p['blind_spot'], 70, 2, 23, LIGHT, 500, 35, 'blind_spot'))
    out.append(multiline(68, 1172, 'WATCH: '+p['tripwire'], 86, 1, 18, AMBER, 650, 25, 'tripwire'))


def t3(out, p, a, b):
    out.append(txt(68, 488, '01  /  SAME METRIC, DIFFERENT PERIOD', 21, TEAL, 800))
    out.append(rect(68, 516, 944, 295, PANEL))
    out.append(txt(95, 560, a['label'].upper()+' / '+a['unit'], 22, MUTED, 600))
    for x, f, label in [(96,a,'THEN'),(611,b,'NOW')]:
        out.append(txt(x, 624, label+'  •  '+f['period'], 21, TEAL, 750))
        out.append(txt(x, 717, f['display'], (70 if len(f['display']) <= 6 else 48 if len(f['display']) <= 12 else 31), LIGHT, 850))
    out.append(rule(506, 612, 506, 767, '#3A4B59', 3))
    out.append(txt(68, 875, '02  /  WHAT MIGHT HAVE CHANGED', 21, TEAL, 800))
    out.append(multiline(68, 931, p['interpretation'], 63, 2, 27, LIGHT, 550, 39, 'interpretation'))
    out.append(txt(68, 1022, 'THE BLIND SPOT', 19, TEAL, 800))
    out.append(multiline(68, 1062, p['blind_spot'], 70, 2, 23, LIGHT, 500, 35, 'blind_spot'))
    out.append(multiline(68, 1172, 'WATCH: '+p['tripwire'], 86, 1, 18, AMBER, 650, 25, 'tripwire'))


def render(payload, status='DRAFT', logo_png=None):
    need(status != 'RELEASE' or logo_png is not None, 'Release rendering requires exact brand logo asset')
    chosen = validate(payload)
    typ = payload['template']
    out = common(payload, typ, logo_png)
    if typ == 'T1':
        if payload.get('t1_variant') == 'EVIDENCE_PLUS':
            draw_t1_plus(out, payload, chosen[0], payload['evidence'], need)
        elif payload.get('t1_layout') == 'RESEARCH_NOTE':
            t1_research_note(out, payload, chosen[0])
        else:
            t1(out, payload, chosen[0])
    elif typ == 'T2': t2(out, payload, *chosen)
    else: t3(out, payload, *chosen)
    # The footer must cover all data visibly represented, not just the hero metric.
    related = (used_evidence(payload, chosen, payload['evidence'])
               if typ == 'T1' and payload.get('t1_variant') == 'EVIDENCE_PLUS' else chosen)
    sources = ', '.join(dict.fromkeys(f['source_title'] for f in related))
    need(len(sources) <= 60, 'Source byline too long; use short precise publisher titles')
    times = [datetime.fromisoformat(f['observed_at'].replace('Z', '+00:00')) for f in related]
    asof = max(times).strftime('%Y-%m-%d %H:%M %z')
    footer(out, payload, sources, asof, status)
    out.append('</svg>')
    svg = '\n'.join(out)+'\n'
    if not synthetic_issue(payload):
        assert_clean_artwork(svg)
    return svg


def payload_hash(payload):
    return hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode('utf-8')).hexdigest()


def release_allowed(payload, approval):
    need(isinstance(approval,dict), 'approval must be object')
    need(approval.get('input_sha256') == payload_hash(payload), 'Approval is stale: input SHA256 mismatch')
    need(not any('synthetic' in f['verification_note'].lower() or urlparse(f['source_url']).hostname in ('example.org','example.com') for f in payload['evidence']), 'Synthetic/demo evidence can never be released')
    need(approval.get('independent_audit') == 'PASS', 'Independent audit PASS required')
    need(approval.get('ceo_approved') is True, 'Explicit CEO approval required')
    bounded(approval.get('auditor_reference'),'auditor_reference',140)
    bounded(approval.get('ceo_approval_reference'),'ceo_approval_reference',140)
    need(payload.get('brand_logo_sha256') == APPROVED_LOGO_SHA256,
         'Release requires SHA256 of exact CEO-approved reconstructed pine logo v0.1')
    # This checks an external record; it cannot authenticate the human reviewer or verify source URLs.


def run(argv=None):
    ap=argparse.ArgumentParser(description='Offline PAM Macro Lens design renderer; no market-data retrieval')
    ap.add_argument('issue',type=Path)
    ap.add_argument('--output',type=Path,required=True,help='Path to output SVG')
    ap.add_argument('--png',type=Path,help='Optional output PNG (existing PyMuPDF package required)')
    ap.add_argument('--release-manifest',type=Path,help='Separate pre-approved, SHA-bound external audit and CEO authorization')
    ap.add_argument('--brand-logo',type=Path,help='Exact CEO-approved reconstructed v0.1 pine PNG; see Visual Kit asset register')
    args=ap.parse_args(argv)
    try:
        data=json.loads(args.issue.read_text(encoding='utf-8'))
        status='DRAFT'
        if args.release_manifest:
            approval=json.loads(args.release_manifest.read_text(encoding='utf-8'))
            release_allowed(data,approval)
            status='RELEASE'
        logo_png = checked_logo(args.brand_logo) if args.brand_logo else None
        if logo_png is not None:
            need(data.get('brand_logo_sha256') == hashlib.sha256(logo_png).hexdigest(),
                 'Brand logo SHA256 missing or mismatched: asset is not bound to approved issue')
        if status == 'RELEASE':
            need(logo_png is not None, 'Cannot release without exact CEO-approved pine logo PNG')
        svg=render(data,status,logo_png)
        # Generate BOTH outputs before writing either to disk.
        png=None
        if args.png:
            import fitz  # PyMuPDF is in repository requirements.txt; no new package needed.
            doc=fitz.open(stream=svg.encode('utf-8'),filetype='svg')
            page=doc[0]; pix=page.get_pixmap(matrix=fitz.Matrix(1,1),alpha=False)
            need((pix.width,pix.height)==(W,H),'PNG output dimensions unexpected')
            png=pix.tobytes('png')
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(svg,encoding='utf-8')
        if png is not None:
            args.png.parent.mkdir(parents=True,exist_ok=True)
            args.png.write_bytes(png)
        print(json.dumps({'status':status,'issue_id':data['issue_id'],'input_sha256':payload_hash(data),
                          'svg':str(args.output),'png':str(args.png) if args.png else None}))
    except (OSError,ValueError,KeyError,TypeError,ImportError) as exc:
        print(f'HOLD: {exc}',file=sys.stderr)
        return 2
    return 0

if __name__=='__main__':
    raise SystemExit(run())