"""Offline manual research presentation; structural validation admits no evidence."""
from dataclasses import dataclass, fields
from datetime import date
from enum import Enum
from html import escape
from typing import ClassVar
import unicodedata

CONTRACT_VERSION = '2026-10-26-qualitative-durability-research-note-v1'
AUTHORITY = 'MANUAL_RESEARCH_ONLY'
EVIDENCE_STATUS = 'NOT_NATIVE_EVIDENCE_ADMISSION'
TEMPORAL_MODE = 'CURRENT_CAPTURE_BOUND_ONLY'
LIMITATIONS = (
    'All content and review metadata are operator supplied, not independently verified here.',
    'A citation, URL, accession, path or digest does not establish source authenticity or admission.',
    'Operator review does not verify native SEC provenance, source rights or economic truth.',
    'Issuer statements, interpretations and possible mechanisms are not proof of a moat or persistence.',
    'No scoring, company classification, investment admission, allocation or execution authority.',
    'No PIT, HISTORICAL_AS_OF, production, deployment or V2 promotion authority.',
    'Private research presentation only; no publication or redistribution rights are established.',
)
MISSING = 'NOT PROVIDED'


class ResearchNoteError(ValueError):
    """Malformed presentation data, not an evidence-qualification verdict."""


class ManualReviewStatus(str, Enum):
    UNREVIEWED = 'UNREVIEWED'
    OPERATOR_REVIEWED = 'OPERATOR_REVIEWED'


def _text(value):
    if value is not None and (type(value) is not str or not value.strip()
            or len(value) > 10_000
            or any(unicodedata.category(c).startswith('C') and c not in '\n\t' for c in value)):
        raise ResearchNoteError('Use bounded text or explicit None; control characters are unsupported')


def _texts(values):
    if type(values) is not tuple or len(values) > 20:
        raise ResearchNoteError('At most twenty immutable text entries required')
    for value in values:
        if value is None:
            raise ResearchNoteError('Use an empty tuple for missing list information')
        _text(value)


def _optional_date(value):
    _text(value)
    if value is not None:
        try:
            if date.fromisoformat(value).isoformat() != value:
                raise ValueError
        except ValueError:
            raise ResearchNoteError('Exact YYYY-MM-DD date or None required') from None


@dataclass(frozen=True, slots=True, kw_only=True)
class ManualSourceReferenceV1:
    """Opaque operator references; no dereferencing, hashing or source verification."""
    document_title: str | None = None
    document_reference: str | None = None
    document_date: str | None = None
    source_type: str | None = None
    locator: str | None = None
    section_location: str | None = None
    operator_supplied_digest: str | None = None

    def __post_init__(self):
        for field in fields(self):
            _text(getattr(self, field.name))
        _optional_date(self.document_date)


@dataclass(frozen=True, slots=True, kw_only=True)
class QualitativeResearchItemV1:
    source: ManualSourceReferenceV1 | None = None
    statement_attribution: str | None = None
    issuer_statement: str | None = None
    source_grounded_observation: str | None = None
    research_interpretation: str | None = None
    possible_economic_mechanism: str | None = None
    competing_explanations_or_vulnerabilities: tuple[str, ...] = ()
    supporting_context: tuple[str, ...] = ()
    contrary_context: tuple[str, ...] = ()
    missing_corroboration: tuple[str, ...] = ()
    uncertainties: tuple[str, ...] = ()
    possible_falsification_evidence: tuple[str, ...] = ()

    def __post_init__(self):
        if self.source is not None:
            if type(self.source) is not ManualSourceReferenceV1:
                raise ResearchNoteError('Exact manual source reference or None required')
            self.source.__post_init__()
        for value in (self.statement_attribution, self.issuer_statement,
                      self.source_grounded_observation, self.research_interpretation,
                      self.possible_economic_mechanism):
            _text(value)
        for values in (self.competing_explanations_or_vulnerabilities,
                       self.supporting_context, self.contrary_context,
                       self.missing_corroboration, self.uncertainties,
                       self.possible_falsification_evidence):
            _texts(values)


@dataclass(frozen=True, slots=True, kw_only=True)
class QualitativeDurabilityResearchNoteV1:
    issuer_name: str | None = None
    issuer_reference: str | None = None
    review_status: ManualReviewStatus = ManualReviewStatus.UNREVIEWED
    reviewed_by: str | None = None
    reviewed_on: str | None = None
    items: tuple[QualitativeResearchItemV1, ...] = ()
    provenance_limitations: tuple[str, ...] = ()
    research_conclusion: str | None = None
    contract_version: ClassVar[str] = CONTRACT_VERSION
    authority: ClassVar[str] = AUTHORITY
    evidence_status: ClassVar[str] = EVIDENCE_STATUS
    temporal_mode: ClassVar[str] = TEMPORAL_MODE

    def __post_init__(self):
        for value in (self.issuer_name, self.issuer_reference, self.reviewed_by,
                      self.research_conclusion):
            _text(value)
        _optional_date(self.reviewed_on)
        if type(self.review_status) is not ManualReviewStatus:
            raise ResearchNoteError('Exact closed manual review status required')
        reviewed = self.review_status is ManualReviewStatus.OPERATOR_REVIEWED
        if reviewed != (self.reviewed_by is not None and self.reviewed_on is not None):
            raise ResearchNoteError('Operator-reviewed notes require both reviewer and review date')
        if not reviewed and (self.reviewed_by is not None or self.reviewed_on is not None):
            raise ResearchNoteError('Unreviewed notes cannot claim review metadata')
        if type(self.items) is not tuple or len(self.items) > 20:
            raise ResearchNoteError('At most twenty immutable native research items required')
        for item in self.items:
            if type(item) is not QualitativeResearchItemV1:
                raise ResearchNoteError('Exact research item required')
            item.__post_init__()
        _texts(self.provenance_limitations)


def _value(value):
    return escape(MISSING if value is None else value, quote=True)


def _row(label, value):
    return '<dt>' + escape(label) + '</dt><dd>' + _value(value) + '</dd>'


def _list(label, values):
    content = ''.join('<li>' + _value(v) + '</li>' for v in values) if values else '<li>' + MISSING + '</li>'
    return '<h3>' + escape(label) + '</h3><ul>' + content + '</ul>'


def render_qualitative_durability_research_note_v1(note):
    """Return inert standalone HTML; never read/write files, fetch URLs or qualify facts."""
    if type(note) is not QualitativeDurabilityResearchNoteV1:
        raise ResearchNoteError('Exact manual research note required')
    try:
        note.__post_init__()  # Structural validation only; authenticate no source.
    except (AttributeError, TypeError):
        raise ResearchNoteError('Incomplete or malformed manual research note') from None
    parts = [
        '<!doctype html><html lang="en"><head><meta charset="utf-8">',
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        '<title>Manual qualitative Durability research note</title>',
        '<style>body{max-width:64rem;margin:2rem auto;padding:0 1rem;font:1rem/1.5 system-ui;color:#172331;background:#fff}dt{font-weight:600}dd{margin:0 0 1rem;white-space:pre-wrap;overflow-wrap:anywhere}li{white-space:pre-wrap;overflow-wrap:anywhere}section{border-top:1px solid #aaa;margin-top:2rem}header{border-bottom:2px solid #172331}</style>',
        '</head><body><header><h1>Qualitative Durability research note</h1>',
        '<p>' + AUTHORITY + ' / ' + EVIDENCE_STATUS + '</p>',
        '<p>' + TEMPORAL_MODE + '</p>',
        '<p>Non-scored manual research; source grounding is not independently verified.</p></header>',
        '<dl>' + _row('Contract version', CONTRACT_VERSION),
        _row('Issuer name (operator supplied)', note.issuer_name),
        _row('Issuer reference (operator supplied)', note.issuer_reference),
        _row('Manual review status (operator supplied)', note.review_status.value),
        _row('Reviewed by (operator supplied)', note.reviewed_by),
        _row('Reviewed on (operator supplied)', note.reviewed_on) + '</dl>',
        _list('Fixed authority and evidence limitations', LIMITATIONS),
        _list('Operator-supplied provenance limitations', note.provenance_limitations),
    ]
    if not note.items:
        parts.append('<p>Research items: ' + MISSING + '</p>')
    for index, item in enumerate(note.items, 1):
        parts.append('<section><h2>Research item ' + str(index) + '</h2><dl>')
        source = item.source or ManualSourceReferenceV1()
        for label, value in (
            ('Document title (operator supplied)', source.document_title),
            ('Document reference (operator supplied)', source.document_reference),
            ('Document date (operator supplied)', source.document_date),
            ('Source type (operator supplied)', source.source_type),
            ('Source locator (opaque; not opened or verified)', source.locator),
            ('Section location (operator supplied; not inferred)', source.section_location),
            ('Digest (operator supplied; not recomputed or verified)', source.operator_supplied_digest),
            ('Statement attribution (operator supplied)', item.statement_attribution),
            ('Issuer statement (operator supplied; source grounding unverified)', item.issuer_statement),
            ('Operator-supplied source-grounded observation (not verified here)', item.source_grounded_observation),
            ('Research interpretation (operator supplied)', item.research_interpretation),
            ('Possible economic mechanism (hypothesis only)', item.possible_economic_mechanism),
        ):
            parts.append(_row(label, value))
        parts.extend(('</dl>',
            _list('Material competing explanations or vulnerabilities', item.competing_explanations_or_vulnerabilities),
            _list('Supporting context (not automatically independent corroboration)', item.supporting_context),
            _list('Contrary context', item.contrary_context),
            _list('Missing corroboration', item.missing_corroboration),
            _list('Uncertainties', item.uncertainties),
            _list('Possible falsification evidence', item.possible_falsification_evidence), '</section>'))
    parts.append('<dl>' + _row('Manual research conclusion (operator supplied; not automated)',
                              note.research_conclusion) + '</dl>')
    return ''.join(parts) + '</body></html>'
