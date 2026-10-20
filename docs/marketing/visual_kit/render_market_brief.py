#!/usr/bin/env python3
"""PAM M4 Cross-Asset Market Brief — deterministic, source-bound layout only.

Separate from Macro Lens; no data downloads, chart interpolation, publishing
authority or independent source verification. M4 candidate is a controlled pilot.
"""
import argparse
import base64
import json
import math
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from xml.etree import ElementTree as ET

from render_macro_lens import (
    W, H, BG, LIGHT, MUTED, TEAL, AMBER, PINE, IVORY,
    InvalidIssue, APPROVED_LOGO_SHA256, bounded, checked_logo,
    iso_dt, need, payload_hash, rect, rule, txt, valid_url,
    release_allowed, wrap,
)

NOTE_BG = '#152A2D'
SEPARATOR = '#405751'
SECTIONS = ('EQUITIES', 'RATES', 'FX', 'COMMODITIES')
ID_RE = re.compile(r'^MB-\d{8}-\d{2}$')
VALUE_RE = re.compile(r'^([+-]?\d+(?:,\d{3})*(?:\.\d{1,4})?)$')
CHANGE_RE = re.compile(r'^([+-]?\d+(?:\.\d{1,2})?)\s*(%|bp)$')


def _dt(value, name):
    return datetime.fromisoformat(iso_dt(value, name).replace('Z', '+00:00'))


def _width(text, size):
    """Conservative glyph-span estimate; final PNG still requires inspection."""
    factor = lambda c: (1.0 if c in 'WM@#%&' else
                        0.79 if c.isupper() else
                        0.66 if c.islower() or c.isdigit() else
                        0.36 if c.isspace() else 0.59)
    return size * sum(factor(c) for c in text)


def _text_checked(x, y, value, size, limit, *, color=LIGHT, weight=600, anchor='start'):
    need(_width(value, size) <= limit,
         'M4 text exceeds its available column; shorten copy without altering facts')
    return txt(x, y, value, size, color, weight, anchor)


def _paragraph(x, y, value, *, chars, max_lines, size, lead, width, name,
               color=LIGHT, weight=500):
    rows = wrap(value, chars, max_lines, name)
    return [_text_checked(x, y + i * lead, line, size, width,
                          color=color, weight=weight) for i, line in enumerate(rows)]


def validate_market_brief(p):
    need(isinstance(p, dict), 'M4 issue must be a JSON object')
    need(p.get('schema_version') == '1.0', 'Unsupported M4 schema')
    need(p.get('template') == 'M4', 'Only template M4 is supported by this renderer')
    need(p.get('account') == '@therealpam', 'Only @therealpam supported')
    need(isinstance(p.get('issue_id'), str) and ID_RE.fullmatch(p['issue_id']),
         'M4 issue_id must be MB-YYYYMMDD-NN')
    issue_dt = _dt(p.get('issue_at'), 'issue_at')
    bounded(p.get('headline'), 'headline', 62)
    bounded(p.get('deck'), 'deck', 108)
    bounded(p.get('interpretation'), 'interpretation', 105)
    bounded(p.get('watch'), 'watch', 78)
    bounded(p.get('caption'), 'caption', 1200)
    need(p.get('comparison_basis') == 'LATEST_COMPLETED_REGULAR_SESSIONS',
         'M4 accepts only the latest eligible completed regular market sessions')
    need(p.get('return_policy') == 'PRICE_RETURN_AND_YIELD_BP_DISTINCT',
         'M4 requires distinct price-return and yield-movement conventions')
    facts = p.get('evidence')
    need(isinstance(facts, list) and len(facts) in (4, 5),
         'M4 requires four or five independently sourced market rows')
    groups = [f.get('asset_group') for f in facts if isinstance(f, dict)]
    need(len(groups) == len(facts), 'Each M4 evidence row must be an object')
    need((groups == list(SECTIONS) if len(facts) == 4 else
          groups == ['EQUITIES', 'EQUITIES', 'RATES', 'FX', 'COMMODITIES']),
         'M4 requires one row per group and optional second equity row in order')
    used = set()
    for i, f in enumerate(facts):
        prefix = f'evidence[{i}]'
        cid = bounded(f.get('claim_id'), prefix+'.claim_id', 30)
        need(cid not in used, 'Duplicate M4 claim ID')
        used.add(cid)
        bounded(f.get('label'), prefix+'.label', 27)
        bounded(f.get('instrument_id'), prefix+'.instrument_id', 18)
        bounded(f.get('venue'), prefix+'.venue', 30)
        bounded(f.get('price_currency'), prefix+'.price_currency', 18)
        bounded(f.get('source_title'), prefix+'.source_title', 24)
        bounded(f.get('verification_note'), prefix+'.verification_note', 160)
        valid_url(f.get('source_url'), prefix+'.source_url')
        need(f.get('verification') == 'VERIFIED' and
             f.get('classification') == 'FACT',
             f'{prefix} requires independently auditable human-verified FACT')
        # Every observation is a local completed session. Separate exact UTC/offset
        # timestamps permit mixed time zones without implying synchronized closes.
        period = bounded(f.get('period'), prefix+'.period', 10)
        prior_period = bounded(f.get('prior_period'), prefix+'.prior_period', 10)
        need(re.fullmatch(r'\d{4}-\d{2}-\d{2}', period) is not None and
             re.fullmatch(r'\d{4}-\d{2}-\d{2}', prior_period) is not None,
             'M4 session dates must use YYYY-MM-DD')
        current = _dt(f.get('observed_at'), prefix+'.observed_at')
        previous = _dt(f.get('prior_observed_at'), prefix+'.prior_observed_at')
        retrieved = _dt(f.get('retrieved_at'), prefix+'.retrieved_at')
        need(previous < current <= retrieved <= issue_dt,
             f'{prefix} dates out of order or acquired after brief cutoff')
        # Explicit freshness limit for a daily market note (weekends/holidays are
        # not treated as 0% returns). A stale market must cause HOLD or omission.
        need(issue_dt - current <= timedelta(hours=96),
             f'{prefix} market observation too stale for M4')
        need(prior_period < period, 'M4 previous session must precede current')
        need(current.date().isoformat() == period and
             previous.date().isoformat() == prior_period,
             'M4 period must match the specified local session timestamps')
        expected_measure = ('YIELD_MOVE_BP' if groups[i] == 'RATES'
                            else 'PRICE_RETURN_PCT')
        need(f.get('change_kind') == expected_measure,
             f'{prefix} incompatible change measurement for {groups[i]}')
        need(f.get('session_status') == 'COMPLETED',
             f'{prefix} halted, provisional or unavailable close cannot be plotted')
        level_unit = bounded(f.get('unit'), prefix+'.unit', 16)
        need(level_unit.strip() != 'bp' or groups[i] == 'RATES',
             'Do not display a price index level as basis points')
        display = bounded(f.get('display'), prefix+'.display', 15)
        m = VALUE_RE.fullmatch(display)
        need(m is not None, 'M4 level display must be a plain numeric value')
        def numeric(key):
            v = f.get(key)
            need(type(v) in (int, float) and math.isfinite(v),
                 f'{prefix}.{key} must be a finite number')
            return float(v)
        last = numeric('numeric_value')
        prior = numeric('previous_numeric_value')
        need(last >= 0 or groups[i] == 'RATES',
             'Non-rate market prices/index levels cannot be negative')
        need(prior > 0 or groups[i] == 'RATES',
             'Previous price/index value must be positive')
        # Parse displayed level rather than trusting a friendly looking label.
        digits = len(display.split('.', 1)[1]) if '.' in display else 0
        displayed_level = float(display.replace(',', ''))
        need(abs(displayed_level - last) <= 0.5 * (10 ** -digits) + 1e-8,
             f'{prefix} displayed level disagrees with numeric_value')
        actual = ((last - prior) * 100.0 if groups[i] == 'RATES'
                  else (last / prior - 1.0) * 100.0)
        number = numeric('numeric_change')
        need(abs(actual - number) <= 0.005,
             f'{prefix} change does not match observation pair')
        change = bounded(f.get('change_display'), prefix+'.change_display', 12)
        match = CHANGE_RE.fullmatch(change)
        need(match is not None, f'{prefix} change display malformed')
        expected_unit = 'bp' if groups[i] == 'RATES' else '%'
        need(match.group(2) == expected_unit, f'{prefix} percentage and bp are not interchangeable')
        shown = float(match.group(1))
        precision = len(match.group(1).split('.', 1)[1]) if '.' in match.group(1) else 0
        need(abs(actual - shown) <= 0.5 * (10 ** -precision) + 1e-7,
             f'{prefix} displayed change disagrees with source observations')
        need(abs(actual) < 1000, 'Unusually large move requires outside review; M4 HOLD')
        # Distinguish sign and zero at the precision actually shown.
        need((actual < 0 and shown <= 0) or (actual > 0 and shown >= 0) or actual == 0,
             'M4 displayed direction is inconsistent with source')
    return facts


def _masthead(p, logo_png):
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
           rect(0, 0, W, H, BG, 0),
           '<defs><clipPath id="pamSealClip"><circle cx="110" cy="99" r="38"/></clipPath></defs>',
           f'<circle cx="110" cy="99" r="39" fill="{IVORY}"/>']
    if logo_png:
        encoded = base64.b64encode(logo_png).decode('ascii')
        out.append('<image x="72" y="61" width="76" height="76" preserveAspectRatio="xMidYMid slice" '
                   'clip-path="url(#pamSealClip)" href="data:image/png;base64,'+encoded+'"/>')
    else:
        out.append(txt(110, 111, 'P', 40, PINE, 800, anchor='middle'))
    out.extend([
        txt(169, 102, 'PAM', 29, LIGHT, 800),
        txt(267, 102, '/  MARKET BRIEF', 23, MUTED, 600),
        txt(1012, 103, p['issue_id'], 20, TEAL, 600, anchor='end'),
        rule(68, 150, 1012, 150, SEPARATOR, 2),
        txt(68, 188, p['issue_at'][:10]+'   /   @therealpam', 19, MUTED, 600),
    ])
    return out


def draw_market_brief(p, logo_png=None, status='DRAFT'):
    need(status != 'RELEASE' or logo_png is not None,
         'M4 release requires the exact approved logo bytes')
    facts = validate_market_brief(p)
    out = _masthead(p, logo_png)
    out.extend(_paragraph(68, 260, p['headline'], chars=29, max_lines=2, size=52,
                          lead=62, width=944, name='headline', weight=800))
    out.extend(_paragraph(68, 379, p['deck'], chars=65, max_lines=2, size=24,
                          lead=34, width=944, name='deck', color=MUTED))
    out.extend([
        txt(68, 444, 'LATEST COMPLETED SESSIONS  /  CROSS-ASSET', 20, TEAL, 700),
        txt(1012, 444, 'PRICE %  ·  YIELDS bp', 18, MUTED, 650, anchor='end'),
        rule(68, 465, 1012, 465, SEPARATOR, 2),
    ])
    # Keep all five rows comfortably sized; avoid different-width horizontal bars
    # whose magnitude could misleadingly compare basis points with percentages.
    step = 102 if len(facts) == 5 else 124
    for i, f in enumerate(facts):
        y = 469 + i * step
        out.append(rect(68, y, 944, step - 3,
                        NOTE_BG if i % 2 == 0 else BG, 0))
        out.append(rule(68, y + step - 2, 1012, y + step - 2, SEPARATOR, 1))
        out.append(_text_checked(86, y+23, f['asset_group'], 18, 400,
                                 color=TEAL, weight=800))
        out.append(_text_checked(86, y+58, f['label'], 29, 450, weight=650))
        out.append(_text_checked(86, y+83, f['source_title']+' · '+f['period'],
                                 20, 475, color=MUTED, weight=500))
        out.append(_text_checked(774, y+54, f['display'], 30, 180,
                                 weight=720, anchor='end'))
        out.append(_text_checked(774, y+83, f['unit'], 19, 185,
                                 color=MUTED, weight=500, anchor='end'))
        out.append(_text_checked(1012, y+54, f['change_display'], 31, 182,
                                 weight=750, anchor='end'))
        out.append(txt(1012, y+83, 'vs previous close', 18, MUTED, 450, anchor='end'))
    out.append(txt(68, 1037, 'THE READING', 19, TEAL, 750))
    out.extend(_paragraph(68, 1073, p['interpretation'], chars=73, max_lines=2,
                          size=24, lead=31, width=944, name='interpretation'))
    out.append(txt(68, 1152, 'WATCH', 19, AMBER, 750))
    out.extend(_paragraph(179, 1152, p['watch'], chars=66, max_lines=1,
                          size=23, lead=30, width=828, name='watch'))
    out.append(rule(68, 1201, 1012, 1201, SEPARATOR, 2))
    out.append(txt(68, 1243, 'SOURCES PER ROW  /  ORIGINAL LINKS IN EVIDENCE PACKET',
                   23, MUTED, 500))
    out.append(txt(68, 1313, 'AS OF '+p['issue_at'][:16]+p['issue_at'][19:],
                   27, MUTED, 500))
    out.append(txt(1012, 1313, 'NOT INVESTMENT ADVICE', 27, MUTED, 500, anchor='end'))
    if status != 'RELEASE':
        out.append(rect(710, 151, 302, 53, '#503D25', 12, AMBER))
        out.append(txt(861, 185, 'DRAFT · NOT AUDITED', 18, AMBER, 750, anchor='middle'))
    out.append('</svg>')
    result = '\n'.join(out) + '\n'
    ET.fromstring(result)  # Verify XML validity before release/output.
    return result


def run(argv=None):
    parser = argparse.ArgumentParser(description='Offline M4 market-brief renderer; no market-data feeds')
    parser.add_argument('issue', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--png', type=Path)
    parser.add_argument('--brand-logo', type=Path)
    parser.add_argument('--release-manifest', type=Path)
    args = parser.parse_args(argv)
    try:
        p = json.loads(args.issue.read_text(encoding='utf-8'))
        validate_market_brief(p)
        logo = checked_logo(args.brand_logo) if args.brand_logo else None
        if logo:
            import hashlib
            need(p.get('brand_logo_sha256') == hashlib.sha256(logo).hexdigest(),
                 'Issue brand_logo_sha256 must match supplied logo bytes')
        status = 'DRAFT'
        if args.release_manifest:
            approval = json.loads(args.release_manifest.read_text(encoding='utf-8'))
            release_allowed(p, approval)
            need(logo is not None, 'M4 release requires the approved logo')
            status = 'RELEASE'
        svg = draw_market_brief(p, logo, status)
        png = None
        if args.png:
            import fitz
            page = fitz.open(stream=svg.encode('utf-8'), filetype='svg')[0]
            pix = page.get_pixmap(matrix=fitz.Matrix(1, 1), alpha=False)
            need((pix.width, pix.height) == (1080, 1350),
                 'Rendered M4 PNG dimensions invalid')
            png = pix.tobytes('png')
        args.output.parent.mkdir(parents=True, exist_ok=True)
        if png is not None:
            args.png.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(svg, encoding='utf-8')
        if png is not None:
            args.png.write_bytes(png)
        print(json.dumps({'status': status, 'issue_id': p['issue_id'],
                          'input_sha256': payload_hash(p),
                          'svg': str(args.output),
                          'png': str(args.png) if png else None}))
        return 0
    except (OSError, ValueError, TypeError, KeyError, ImportError, ET.ParseError) as exc:
        print(f'HOLD: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(run())
