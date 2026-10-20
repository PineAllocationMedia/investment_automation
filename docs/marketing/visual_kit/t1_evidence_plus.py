"""Optional, evidence-linked T1 Evidence+ panel for PAM Macro Lens.

No network requests; numbers are drawn exclusively from VERIFIED fact records.
Structural validation DOES NOT authenticate the original source. Independent audit
of the exact graphic and caption, followed by CEO approval, remains mandatory.
"""
from datetime import datetime
from math import isfinite, ceil, log10
import calendar
import re
from xml.sax.saxutils import escape

BG = '#11242A'
PANEL = '#1A3233'
LIGHT = '#F4F0E6'
MUTED = '#BDC8BE'
SAGE = '#A6CBB1'
AMBER = '#E6C592'
FONT = 'DejaVu Sans, Liberation Sans, Arial, sans-serif'
MONTH_RE = re.compile(r'^\d{4}-(0[1-9]|1[0-2])$')
NUMBER_RE = re.compile(r'^[+\-]?(?:\d+(?:,\d{3})*)(?:\.\d{1,3})?%?$')


def _text(x, y, s, size=22, color=LIGHT, weight=500, anchor='start'):
    return (f'<text x="{x}" y="{y}" text-anchor="{anchor}" fill="{color}" '
            f'font-size="{size}" font-weight="{weight}" font-family="{FONT}">'
            f'{escape(str(s))}</text>')


def _rect(x, y, width, height, fill=PANEL, radius=16):
    return f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="{radius}" fill="{fill}"/>'


def _line(x1, y1, x2, y2, color=SAGE, stroke=2):
    return f'<path d="M {x1} {y1} L {x2} {y2}" stroke="{color}" stroke-width="{stroke}" fill="none"/>'


def _wrap(value, chars, lines, title, need):
    current = ''
    out = []
    for word in value.split():
        need(len(word) <= chars, f'{title} contains an overlong word')
        candidate = (current + ' ' + word).strip()
        if len(candidate) > chars and current:
            out.append(current)
            current = word
        else:
            current = candidate
    if current:
        out.append(current)
    need(len(out) <= lines, f'{title} would overflow T1 Evidence+; shorten text')
    return out


def _paragraph(x, y, value, *, chars, lines, title, need, size=23, leading=31, color=LIGHT, weight=500):
    return [_text(x, y + i * leading, line, size, color, weight)
            for i, line in enumerate(_wrap(value, chars, lines, title, need))]


def _source(evidence, claim_id):
    return next((f for f in evidence if f['claim_id'] == claim_id), None)


def _month_index(value):
    return int(value[:4])*12 + int(value[5:])


def _month_short(value):
    return f'{calendar.month_abbr[int(value[5:])]} {value[2:4]}'


def _format_tick(value):
    return f'{value:g}'


def validate_t1_plus(p, chosen, evidence, need, bounded):
    """Return all used fact IDs, fail closed on malformed and misleading displays."""
    variant = p.get('t1_variant', 'CLASSIC')
    need(variant in ('CLASSIC', 'EVIDENCE_PLUS'), 'Unknown T1 variant')
    if variant == 'CLASSIC':
        need(not p.get('support_fact_ids') and not p.get('mini_chart'),
             'Classic T1 cannot silently ignore additional indicators or charts')
        return []

    support_ids = p.get('support_fact_ids', [])
    need(isinstance(support_ids, list) and 0 <= len(support_ids) <= 2,
         'Evidence+ supports 0–2 context indicators')
    need(len(set(support_ids)) == len(support_ids), 'Duplicate supporting fact')
    need(all(isinstance(x, str) for x in support_ids), 'Supporting IDs must be strings')
    primary = chosen[0]
    need(primary['claim_id'] not in support_ids, 'Primary signal must not be duplicated as supporting indicator')
    for cid in support_ids:
        f = _source(evidence, cid)
        need(f is not None, f'Supporting fact {cid} lacks source evidence')
        need(f['period'] == primary['period'],
             'Supporting indicators must use the exact primary reference period')
        need(f['observed_at'] == primary['observed_at'],
             'Supporting indicators must use the exact primary observation timestamp')
        bounded(f['label'], 'support label', 25)
        bounded(f['display'], 'support display', 12)
        bounded(f['unit'], 'support unit', 24)
        need(len(f['label']) <= 24, 'Supporting indicator label will overflow')
    chart = p.get('mini_chart')
    need(chart is not None or len(support_ids) > 0, 'Evidence+ needs at least one supported indicator or chart')
    if chart is None:
        return support_ids

    need(isinstance(chart, dict), 'mini_chart must be structured object')
    need(set(chart.keys()) == {'kind', 'title', 'fact_ids'},
         'mini_chart must contain only kind, title and fact_ids; do not inject raw chart values')
    need(chart['kind'] == 'bar', 'Only anchored-zero bar chart is supported')
    bounded(chart['title'], 'mini_chart.title', 31)
    ids = chart['fact_ids']
    need(isinstance(ids, list) and 3 <= len(ids) <= 4,
         'Chart must cite 3–4 consecutive monthly observations')
    need(len(set(ids)) == len(ids) and all(isinstance(x, str) for x in ids),
         'Chart fact IDs must be unique strings')
    facts = [_source(evidence, cid) for cid in ids]
    need(all(f is not None for f in facts), 'Chart references unregistered fact IDs')
    first = facts[0]
    need(len(first['label']) <= 34 and len(first['unit']) <= 24, 'Chart metadata too long')
    need(all(f['label'] == first['label'] and f['unit'] == first['unit'] for f in facts),
         'Chart observations must represent the same metric and units')
    months = [f['period'] for f in facts]
    need(all(MONTH_RE.fullmatch(month) for month in months),
         'Chart period must use an explicit YYYY-MM observation label')
    need(all(_month_index(months[i + 1]) == _month_index(months[i]) + 1
             for i in range(len(months) - 1)),
         'Chart observations must be consecutive chronological months (no omitted intervals)')
    values = []
    for f in facts:
        v = f.get('numeric_value')
        need(type(v) in (float, int) and isfinite(v) and -1000 <= v <= 1000,
             'Chart numeric_value must be finite sourced value; booleans/strings prohibited')
        display = f['display']
        need(NUMBER_RE.fullmatch(display) is not None, 'Chart display must represent one exact numeric value')
        try:
            displayed = float(display.replace('%', '').replace(',', ''))
        except ValueError:
            need(False, 'Chart display numeric value invalid')
        need(abs(displayed - float(v)) <= 0.0005,
             'Chart numeric_value differs from evidence display')
        values.append(float(v))
    need(any(v != 0 for v in values), 'Flat all-zero chart is not meaningful; omit it')
    need(all(f['source_url'].startswith('https://') for f in facts), 'Chart facts require source URLs')
    return list(dict.fromkeys(support_ids + ids))


def used_evidence(p, chosen, evidence):
    """Used facts are bounded to verified evidence IDs by validate_t1_plus."""
    ids = [chosen[0]['claim_id']] + p.get('support_fact_ids', [])
    if p.get('mini_chart'):
        ids += p['mini_chart']['fact_ids']
    return [f for f in evidence if f['claim_id'] in ids]


def _bar_chart(out, chart, facts):
    # Proven values from evidence objects only; zero anchor always included.
    vals = [float(f['numeric_value']) for f in facts]
    lo, hi = min(0.0, *vals), max(0.0, *vals)
    if lo == hi:
        raise ValueError('Invalid chart scale')
    pad = (hi - lo) * 0.14
    bot, top = lo - pad if lo < 0 else 0.0, hi + pad if hi > 0 else 0.0
    if lo >= 0:
        top = hi * 1.25
    if hi <= 0:
        bot = lo * 1.25
    # Round chart extremes outward to human-readable tick values; never crop zero.
    peak = max(abs(top), abs(bot))
    base = 10 ** int(log10(peak)) if peak >= 1 else 10 ** (int(log10(peak)) - 1)
    step_tick = base if base <= peak/2 else base/2
    if top > 0: top = ceil(top / step_tick) * step_tick
    if bot < 0: bot = -ceil(abs(bot) / step_tick) * step_tick
    need_height = top - bot
    chart_top, chart_bottom = 712, 754
    y = lambda value: chart_bottom - (value - bot) / need_height * (chart_bottom - chart_top)
    zero = y(0)
    out.append(_line(505, round(zero, 2), 990, round(zero, 2), MUTED, 2))
    out.append(_text(492, 712, _format_tick(top), 13, MUTED, 500, 'end'))
    out.append(_text(492, 758, _format_tick(bot), 13, MUTED, 500, 'end'))
    count = len(vals)
    step = 458.0 / count
    for i, (fact, value) in enumerate(zip(facts, vals)):
        x = 523 + step * (i + 0.5)
        yval = y(value)
        bar_y = min(zero, yval)
        bar_h = abs(yval - zero)
        out.append(_rect(round(x - 18, 2), round(bar_y, 2), 36, round(max(bar_h, 0.5), 2), SAGE if value >= 0 else AMBER, 2))
        out.append(_text(round(x, 2), 783, _month_short(fact['period']), 14, MUTED, 500, 'middle'))
        # Every point is explicitly labeled; align below title and above month labels.
        label_y = max(706, yval - 3) if value >= 0 else min(768, yval + 16)
        out.append(_text(round(x, 2), round(label_y, 2), fact['display'], 14, LIGHT, 600, 'middle'))
    out.append(_text(989, 695, 'ZERO-BASED · '+facts[0]['unit'], 13, MUTED, 600, 'end'))


def draw_t1_plus(out, p, primary, evidence, need):
    """Renderer for 1080x1350 T1 with compact, optional evidence panels.

    No market fact is drawn unless selected from pre-validated evidence.
    """
    related = used_evidence(p, [primary], evidence)
    facts_by_id = {f['claim_id']: f for f in related}
    out.append(_rect(68, 461, 944, 131, '#204039', 20))
    out.append(_text(97, 497, '01 / THE VERIFIED SIGNAL', 20, SAGE, 800))
    out.append(_text(97, 562, primary['display'], 48, LIGHT, 800))
    out.append(_text(438, 547, primary['label'], 26, LIGHT, 650))
    out.append(_text(438, 573, primary['unit']+' · '+primary['period'], 18, MUTED, 500))
    out.append(_text(68, 622, '02 / THE EVIDENCE', 19, SAGE, 800))
    chart = p.get('mini_chart')
    supports = [facts_by_id[cid] for cid in p.get('support_fact_ids', [])]
    if chart:
        # Context indicators at left; chart at right, with a zero-based scale.
        if supports:
            if len(supports) == 1:
                rectangles = [(68, 644, 368, 150)]
            else:
                rectangles = [(68, 644, 368, 70), (68, 721, 368, 73)]
            for f, (x, yy, w, h) in zip(supports, rectangles):
                out.append(_rect(x, yy, w, h))
                if len(supports) == 1:
                    out.append(_text(x + 18, yy + 33, f['label'], 21, MUTED, 600))
                    out.append(_text(x + 18, yy + 82, f['display'], 40, LIGHT, 750))
                    out.append(_text(x + 18, yy + 110, f['unit'], 17, MUTED))
                else:
                    out.append(_text(x + 13, yy + 24, f['label'], 18, MUTED, 600))
                    out.append(_text(x + 13, yy + 52, f['display']+' '+f['unit'].removeprefix('%').strip(), 22, LIGHT, 750))
        else:
            # Chart gets extra horizontal room when no supporting indicators.
            out.append(_rect(68, 644, 368, 150))
            out.append(_text(86, 681, 'SOURCE-BACKED TREND', 20, SAGE, 700))
            out.extend(_paragraph(86, 718, 'Each bar represents a recorded monthly observation.',
                                  chars=29, lines=2, title='chart explanation', need=need, size=18, leading=26, color=MUTED))
        out.append(_rect(451, 644, 561, 150))
        out.append(_text(471, 671, chart['title'], 17, LIGHT, 700))
        # Zero-anchored bars within the compact chart panel.
        # Keep data and axis annotations inside safe area.
        chartfacts = [facts_by_id[cid] for cid in chart['fact_ids']]
        _bar_chart(out, chart, chartfacts)
    else:
        count = len(supports)
        w = (944 - 20 * (count - 1)) // count
        for i, f in enumerate(supports):
            xx = 68 + i * (w + 20)
            out.append(_rect(xx, 644, w, 150))
            out.append(_text(xx + 20, 684, f['label'], 23, MUTED, 600))
            out.append(_text(xx + 20, 733, f['display'], 42, LIGHT, 750))
            out.append(_text(xx + 20, 762, f['unit'], 18, MUTED))
    out.append(_text(68, 819, '03 / HOW IT TRAVELS', 19, SAGE, 800))
    for i, step in enumerate(p['mechanism']):
        x = 68 + i * 325
        out.append(_rect(x, 840, 295, 121))
        out.extend(_paragraph(x+17, 891, step, chars=19, lines=2,
                              title=f'mechanism[{i}]', need=need, size=25, leading=35, weight=650))
        if i < 2:
            out.append(_line(x+299, 896, x+319, 896, SAGE, 3))
    out.append(_text(68, 1003, '04 / THE BLIND SPOT', 19, SAGE, 800))
    out.extend(_paragraph(68, 1044, p['blind_spot'], chars=65, lines=2,
                          title='blind_spot', need=need, size=23, leading=33))
    # Leave a nonoverlapping, 2-line source attribution area in the T1 footer.
    out.append(_rect(68, 1096, 944, 66, '#32433D', 10))
    out.extend(_paragraph(89, 1137, 'WATCH: '+p['tripwire'], chars=93, lines=1,
                          title='tripwire', need=need, size=18, color=AMBER, weight=600))