"""Read-only private presentation of native financial context and manual research."""
from decimal import Decimal
from enum import Enum
from html import escape

from economic_facts import sec_current_annual_issuer_two_period_revenue_operating_income as native
from economic_facts.sec_archive import ArchiveError
from src import d1_two_period_operating_profit_continuity as d1
from src import d2_two_period_reported_trajectory as d2
from src import qualitative_durability_research_note as manual

CONTRACT_VERSION = '2026-10-26-unified-private-durability-research-sheet-v1'
AUTHORITY = 'PRIVATE_RESEARCH_PRESENTATION_ONLY'
ASSOCIATION_LIMITATION = (
    'Any supplied qualitative artifact is operator-selected. Its association with the financial issuer '
    'is operator-supplied, not independently authenticated. Matching issuer names, references '
    'or review metadata do not establish a verified financial-to-narrative join.'
)
LIMITATIONS = (
    'D1 and D2 describe reported financial observations, not economic persistence.',
    'Manual narrative research and native financial evidence have separate authority and identities.',
    'Same-issuer statements are not independent economic corroboration.',
    'No inference that a proposed qualitative mechanism caused D1/D2 financial changes.',
    'No generated conclusion, moat verdict, score, investment advice, admission or portfolio action.',
    'No PIT, HISTORICAL_AS_OF, publication rights, production or V2 promotion authority.',
    'Stage D remains INCOMPLETE; V1 remains frozen operational authority and V2 a challenger.',
)
_CONTEXT_FIELDS = (
    'source_cik', 'prior_period_start', 'prior_period_end',
    'current_period_start', 'current_period_end', 'prior_revenue',
    'prior_operating_income', 'current_revenue', 'current_operating_income',
)


class ResearchSheetIntegrityError(ValueError):
    """Financial diagnostics cannot be paired as verified common evidence."""


def _display(value):
    if value is None:
        return manual.MISSING
    if isinstance(value, Enum):
        value = value.value
    elif type(value) is Decimal:
        value = str(value)  # Exact Decimal text, including any exponent; no arithmetic.
    return escape(str(value), quote=True)


def _row(label, value):
    return '<dt>' + escape(label) + '</dt><dd>' + _display(value) + '</dd>'


def _reasons(values):
    return '<ul>' + (''.join('<li>' + _display(v) + '</li>' for v in values)
                     if values else '<li>NONE</li>') + '</ul>'


def _ratio(value):
    return None if value is None else str(value.numerator) + ' / ' + str(value.denominator)


def _verified_financial_context(qualification):
    if type(qualification) is not native.CurrentAnnualIssuerTwoPeriodRevenueOperatingIncomeQualificationV1:
        raise ResearchSheetIntegrityError('Exact bound native Contract A qualification required')
    snapshot = native._verified_comparative_snapshot(qualification)
    first = d1.analyze_d1_two_period_operating_profit_continuity_v1(snapshot)
    second = d2.analyze_d2_two_period_reported_trajectory_v1(snapshot)
    if (type(first) is not d1.D1TwoPeriodOperatingProfitContinuityResultV1
            or type(second) is not d2.D2TwoPeriodReportedTrajectoryResultV1):
        raise ResearchSheetIntegrityError('Exact native analytical results required')
    established = snapshot.status is native.S.COMPARATIVE_ISSUER_REPORTED_FACTS_ESTABLISHED
    for result in (first, second):
        if (result.upstream_qualification_evidence_id != snapshot.evidence_id
                or result.upstream_qualification_semantic_id != snapshot.semantic_id
                or result.upstream_status is not snapshot.status
                or result.upstream_reasons != snapshot.reasons):
            raise ResearchSheetIntegrityError('Native analytical provenance mismatch')
        for field in _CONTEXT_FIELDS:
            expected = getattr(snapshot, field)
            if not established and field.endswith(('_start', '_end')):
                expected = None
            if not native._same_public_value(getattr(result, field), expected):
                raise ResearchSheetIntegrityError('Native reporting context mismatch')
        for field in ('accounting_basis', 'namespace', 'concepts', 'unit', 'temporal_mode'):
            if getattr(result, field) != getattr(snapshot, field):
                raise ResearchSheetIntegrityError('Native accounting context mismatch')
    if first.status.value != second.status.value:
        raise ResearchSheetIntegrityError('Native analytical availability mismatch')
    return snapshot, first, second


def _financial_fragment(qualification):
    try:
        snapshot, first, second = _verified_financial_context(qualification)
    except (ArchiveError, d1.D1DiagnosticError, d2.D2DiagnosticError,
            ResearchSheetIntegrityError, OSError):
        # Do not expose caller-controlled IDs, values, paths or raw exception text.
        return ('<p class="integrity">INTEGRITY_FAILURE</p><p>Financial evidence could not '
                'be verified or paired. No financial values or diagnostic outputs are displayed. '
                'This is an integrity failure, not UNAVAILABLE and not a business judgment.</p>')
    parts = ['<dl>', _row('Native Contract A status', snapshot.status),
        _row('Source CIK', snapshot.source_cik), _row('Reporting basis', snapshot.accounting_basis),
        _row('Namespace', snapshot.namespace), _row('Unit', snapshot.unit),
        _row('Reported concepts', ' / '.join(snapshot.concepts)),
        _row('Temporal mode', snapshot.temporal_mode),
        _row('Verified bound capture date (UTC)', snapshot.captured_at),
        '</dl><details><summary>Native Contract A provenance references</summary><dl>',
        _row('Native Contract A semantic identity', snapshot.semantic_id),
        _row('Native Contract A evidence identity', snapshot.evidence_id),
        _row('Native capture receipt reference', snapshot.capture_receipt_id),
        _row('Verified source-object SHA-256', snapshot.source_object_hash),
        _row('Source endpoint (inert reference)', snapshot.endpoint),
        _row('Common supporting filing references', ' / '.join(f.accession for f in snapshot.supporting_filings) or None),
        '</dl></details><h3>Native qualification reasons</h3>', _reasons(snapshot.reasons)]
    if snapshot.status is native.S.COMPARATIVE_ISSUER_REPORTED_FACTS_ESTABLISHED:
        parts.append('<p>Exact reported USD values use Decimal text; exponent notation, if present, is exact.</p>'
                     '<table><caption>Common verified annual financial presentation</caption>'
                     '<thead><tr><th scope="col">Field</th><th scope="col">Prior</th><th scope="col">Current</th></tr></thead><tbody>')
        for label, prior, current in (
            ('Annual start', snapshot.prior_period_start, snapshot.current_period_start),
            ('Annual end', snapshot.prior_period_end, snapshot.current_period_end),
            ('Revenue (exact USD)', snapshot.prior_revenue, snapshot.current_revenue),
            ('Operating Income (exact USD)', snapshot.prior_operating_income, snapshot.current_operating_income),
        ):
            parts.append('<tr><th scope="row">' + escape(label) + '</th><td>' + _display(prior)
                         + '</td><td>' + _display(current) + '</td></tr>')
        parts.append('</tbody></table>')
    else:
        parts.append('<p>No comparative financial facts or periods are established for display.</p>')
    for label, result in (('D1 reported operating-profit comparison', first),
                          ('D2 reported financial trajectory', second)):
        parts.extend(('<h3>' + label + '</h3><dl>', _row('Analytical status', result.status),
            _row('Diagnostic authority', result.authority),
            '</dl><details><summary>Analytical identities and native binding</summary><dl>',
            _row('Analytical semantic identity', result.semantic_id),
            _row('Analytical evidence identity', result.evidence_id),
            _row('Bound native Contract A evidence identity', result.upstream_qualification_evidence_id),
            '</dl></details><h4>Analytical reasons</h4>',
            _reasons(result.reasons), '<h4>Upstream reasons</h4>', _reasons(result.upstream_reasons)))
        if result is first:
            values = (
                ('Prior Operating Income sign', first.prior_operating_income_sign),
                ('Current Operating Income sign', first.current_operating_income_sign),
                ('Operating Income sign continuity', first.operating_income_sign_continuity),
                ('Prior Operating Income / Revenue (exact rational)', _ratio(first.prior_operating_income_to_revenue_ratio)),
                ('Current Operating Income / Revenue (exact rational)', _ratio(first.current_operating_income_to_revenue_ratio)),
                ('Ratio difference (exact rational)', _ratio(first.ratio_difference)),
                ('Ratio direction', first.ratio_direction),
            )
        else:
            values = (
                ('Revenue direction', second.revenue_direction),
                ('Operating Income direction', second.operating_income_direction),
                ('Relative Revenue change (exact rational)', _ratio(second.revenue_relative_change)),
            )
        parts.append('<dl>' + ''.join(_row(key, value) for key, value in values) + '</dl>')
        parts.extend(('<details><summary>Diagnostic limitations</summary>', _reasons(result.limitations), '</details>'))
    parts.extend(('<details><summary>Native qualification limitations</summary>', _reasons(snapshot.limitations), '</details>'))
    return ''.join(parts)


def render_unified_durability_research_sheet_v1(qualification, note=None):
    """Replay retained financial evidence and return private inert HTML; no writes/network."""
    note = manual.QualitativeDurabilityResearchNoteV1() if note is None else note
    qualitative = manual.render_qualitative_durability_research_note_fragment_v1(
        note, include_conclusion=False)
    financial = _financial_fragment(qualification)
    return ''.join((
        '<!doctype html><html lang="en"><head><meta charset="utf-8">',
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        '<title>Private Durability research sheet</title>',
        '<style>body{max-width:68rem;margin:2rem auto;padding:0 1rem;font:1rem/1.5 system-ui;color:#172331;background:#fff}section{border-top:1px solid #aaa;margin-top:2rem}dt,th{font-weight:600}dd{margin:0 0 1rem;white-space:pre-wrap;overflow-wrap:anywhere}li,td{overflow-wrap:anywhere}table{border-collapse:collapse;width:100%}td,th{border:1px solid #aaa;padding:.5rem;text-align:left}#qualitative h1{font-size:1.25rem}.integrity{font-weight:bold;color:#8b2020}</style>',
        '</head><body><h1>Private Durability research sheet</h1>',
        '<p>What was reported? What economic hypotheses merit investigation? What remains unproven?</p>',
        '<dl>', _row('Sheet contract version', CONTRACT_VERSION), _row('Sheet authority', AUTHORITY), '</dl>',
        '<section id="financial"><h2>A. Reported annual financial context</h2>', financial, '</section>',
        '<section id="qualitative"><h2>B. Manual qualitative research</h2><p>',
        escape(ASSOCIATION_LIMITATION), '</p>', qualitative, '</section>',
        '<section id="synthesis"><h2>C. Research synthesis</h2><dl>',
        _row('Operator-authored research conclusion (not generated or authenticated)', note.research_conclusion),
        '</dl><p>Established financial observations, manual hypotheses and unresolved limitations '
        'remain separate. No causal explanation or persistence verdict is generated.</p>',
        _reasons(LIMITATIONS), '</section></body></html>',
    ))
