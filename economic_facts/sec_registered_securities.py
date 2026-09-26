"""Offline SEC 12(b) source claims; NONE of Property 4A–4H or obligations 5–7.

No economic classification, identity qualification, completeness, chronology or
admission follows from extraction. Only one explicitly selected D2A receipt is
read. A future consumer must independently review and verify the source evidence.
"""
from dataclasses import asdict, dataclass
from datetime import date
from enum import StrEnum
import re

from lxml import etree

from .sec_filing_archive import FilingReceipt, SecFilingArchive, canonical_json, digest

EXTRACTION_CONTRACT_VERSION = "2026-09-22-sec-registered-security-claims-v1"
SUPPORTED_FORMS = frozenset(("10-K", "10-K/A", "10-Q", "10-Q/A"))
DEI = "http://xbrl.sec.gov/dei/2025"
GAAP = "http://fasb.org/us-gaap/2025"
TAXONOMY_PROFILES = (
    (DEI, GAAP),
    ("http://xbrl.sec.gov/dei/2026", "http://fasb.org/us-gaap/2026"),
)
IX = "http://www.xbrl.org/2013/inlineXBRL"
XBRLI = "http://www.xbrl.org/2003/instance"
XBRLDI = "http://xbrl.org/2006/xbrldi"
XHTML = "http://www.w3.org/1999/xhtml"
XML = "http://www.w3.org/XML/1998/namespace"
CLASS_AXES = frozenset("{" + gaap + "}StatementClassOfStockAxis" for _, gaap in TAXONOMY_PROFILES)
EXCHANGE_AXES = frozenset("{" + dei + "}EntityListingsExchangeAxis" for dei, _ in TAXONOMY_PROFILES)
FACT_NAMES = ("Security12bTitle", "TradingSymbol", "NoTradingSymbolFlag", "SecurityExchangeName")
FACT_QNAMES = frozenset("{" + dei + "}" + name for dei, _ in TAXONOMY_PROFILES for name in FACT_NAMES)
MAX_ELEMENTS = 250_000
MAX_CONTEXTS = 20_000
MAX_FACTS = 10_000
MAX_VALUE_LENGTH = 16_384
_TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_.-]{0,255}")


class RegisteredSecurityRequestError(ValueError):
    """Invalid explicit filing receipt selection."""


class UnsupportedRegisteredSecuritySource(ValueError):
    """Unsupported structure/semantics or safety bound; never partial success."""


class ExtractionStatus(StrEnum):
    CAPTURED_REGISTERED_SECURITY_CLAIMS = "CAPTURED_REGISTERED_SECURITY_CLAIMS"
    INCOMPLETE_REGISTERED_SECURITY_CLAIMS = "INCOMPLETE_REGISTERED_SECURITY_CLAIMS"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"
    NO_SUPPORTED_REGISTERED_SECURITY_CLAIMS = "NO_SUPPORTED_REGISTERED_SECURITY_CLAIMS"


class ClaimIssue(StrEnum):
    CONTRADICTORY_FACTS = "CONTRADICTORY_FACTS"
    SYMBOL_AND_NO_SYMBOL = "SYMBOL_AND_NO_SYMBOL"
    MISSING_TITLE = "MISSING_TITLE"
    MISSING_SYMBOL_ASSERTION = "MISSING_SYMBOL_ASSERTION"
    MISSING_EXCHANGE = "MISSING_EXCHANGE"
    CONTEXT_ENTITY_MISMATCH = "CONTEXT_ENTITY_MISMATCH"
    INCONSISTENT_SECURITY_TITLE = "INCONSISTENT_SECURITY_TITLE"
    AMBIGUOUS_DIMENSION_SCOPE = "AMBIGUOUS_DIMENSION_SCOPE"


_CONFLICTS = frozenset((ClaimIssue.CONTRADICTORY_FACTS, ClaimIssue.SYMBOL_AND_NO_SYMBOL,
                        ClaimIssue.CONTEXT_ENTITY_MISMATCH, ClaimIssue.INCONSISTENT_SECURITY_TITLE,
                        ClaimIssue.AMBIGUOUS_DIMENSION_SCOPE))


def _require(condition, message):
    if not condition:
        raise UnsupportedRegisteredSecuritySource(message)


def _identity(domain, value):
    return digest(("pam:sec-registered-securities:" + domain + ":v1\0").encode("ascii")
                  + canonical_json(value))


@dataclass(frozen=True, slots=True)
class SecRegisteredSecurityExtractionRequest:
    filing_receipt_id: str

    def __post_init__(self):
        if type(self.filing_receipt_id) is not str or not re.fullmatch(r"[0-9a-f]{64}", self.filing_receipt_id):
            raise RegisteredSecurityRequestError("Exact filing receipt ID required")


@dataclass(frozen=True, slots=True)
class PrimaryDocumentProvenance:
    receipt_id: str
    cik: str
    accession: str
    form: str
    endpoint: str
    document_ordinal: int
    sequence: str
    filename: str
    byte_start: int
    byte_length: int
    content_sha256: str

    @property
    def evidence_id(self):
        return _identity("primary-document", asdict(self))


@dataclass(frozen=True, slots=True)
class SourceDimension:
    axis: str  # Expanded QName, not a PAM economic anchor.
    member: str
    source_axis: str
    source_member: str


@dataclass(frozen=True, slots=True)
class SourceContext:
    context_id: str
    element_ordinal: int
    entity_scheme: str
    entity_identifier: str
    start_date: str
    end_date: str
    dimensions: tuple[SourceDimension, ...]

    def aspects(self, *, without_exchange=False):
        return (self.entity_scheme, self.entity_identifier, self.start_date, self.end_date,
                tuple(sorted((d.axis, d.member) for d in self.dimensions
                             if not without_exchange or d.axis not in EXCHANGE_AXES)))

    @property
    def semantic_id(self):
        return _identity("context", self.aspects())

    @property
    def source_security_scope_id(self):
        # This is a filing-context relationship, NOT an economic security ID.
        return _identity("source-security-scope", self.aspects(without_exchange=True))


@dataclass(frozen=True, slots=True)
class RegisteredSecurityFactOccurrence:
    primary_document_id: str
    element_ordinal: int  # Zero-based preorder of all XML elements in the primary.
    source_line: int
    fact_name: str  # Expanded QName; lexical spelling also retained.
    source_name: str
    source_fact_id: str | None
    context_ref: str
    source_value: str  # Exact XML-decoded descendant text; no whitespace normalization.
    language: str | None

    @property
    def occurrence_id(self):
        return _identity("fact-occurrence", asdict(self))


@dataclass(frozen=True, slots=True)
class RegisteredSecurityContextClaims:
    """All assertions sharing exact supported XBRL aspects; conflicts keep all values."""
    context_semantic_id: str
    source_security_scope_id: str
    context_refs: tuple[str, ...]
    titles: tuple[str, ...]
    trading_symbols: tuple[str, ...]
    no_trading_symbol_flags: tuple[str, ...]
    exchange_names: tuple[str, ...]
    occurrence_ids: tuple[str, ...]
    issues: tuple[ClaimIssue, ...]


@dataclass(frozen=True, slots=True)
class SecRegisteredSecurityExtractionAssessment:
    contract_version: str
    status: ExtractionStatus
    receipt: FilingReceipt
    primary_document: PrimaryDocumentProvenance
    contexts: tuple[SourceContext, ...]  # Referenced contexts only, source order.
    occurrences: tuple[RegisteredSecurityFactOccurrence, ...]  # Every duplicate retained.
    claims: tuple[RegisteredSecurityContextClaims, ...]  # Canonical context-semantic order.

    @property
    def semantic_id(self):
        context_ids = {c.context_id: c.semantic_id for c in self.contexts}
        facts = sorted(set((context_ids[f.context_ref], f.fact_name, f.source_value, f.language or "")
                           for f in self.occurrences))
        relationships = [(c.context_semantic_id, c.source_security_scope_id, c.issues) for c in self.claims]
        return _identity("assessment-semantics", {
            "contract": self.contract_version, "status": self.status,
            "filing": (self.primary_document.cik, self.primary_document.accession, self.primary_document.form),
            "facts": facts, "relationships": relationships,
        })

    @property
    def evidence_id(self):
        return _identity("assessment-evidence", {
            "semantic_id": self.semantic_id, "receipt": self.receipt.receipt_id,
            "document": asdict(self.primary_document), "contexts": [asdict(c) for c in self.contexts],
            "occurrences": [asdict(f) for f in self.occurrences], "claims": [asdict(c) for c in self.claims],
        })


def _single_field(lines, prefix, pattern):
    values = [line[len(prefix):].strip() for line in lines if line.startswith(prefix)]
    _require(len(values) == 1 and re.fullmatch(pattern, values[0]), "Unsupported filing envelope field")
    return values[0]


def _primary_document(raw, receipt):
    """Read D2A's modern envelope without importing acquisition or altering bytes.

    Deliberately source-local: no document framework and no external resolution.
    D2A has already preflighted trusted captures; replay also verifies selectors,
    parties, counts and all DOCUMENT/TEXT boundaries, including ignored exhibits.
    """
    end = raw.find(b"</SEC-HEADER>", 0, 256 * 1024)
    _require(end >= 0, "Unsupported filing header")
    try:
        header = raw[:end].decode("ascii").replace("\r\n", "\n")
    except UnicodeError:
        raise UnsupportedRegisteredSecuritySource("Unsupported filing header encoding") from None
    lines = [line.rstrip(" \t") for line in header.split("\n")]
    _require(len(lines) > 3 and all(c in "\n\t" or 32 <= ord(c) <= 126 for c in header),
             "Incomplete or unsupported filing header")
    for line, tag, suffix in ((lines[0], "SEC-DOCUMENT", "txt"), (lines[1], "SEC-HEADER", r"hdr\.sgml")):
        _require(re.fullmatch("<" + tag + ">" + re.escape(receipt.accession) + r"\."
                             + suffix + r" : [0-9]{8}", line), "Filing accession mismatch")
    top = [line for line in lines[2:] if line and not line[0].isspace()]
    top_patterns = (
        r"<ACCEPTANCE-DATETIME>[0-9]{14}", r"FILER:",
        r"ACCESSION NUMBER:[ \t]+[0-9]{10}-[0-9]{2}-[0-9]{6}",
        r"CONFORMED SUBMISSION TYPE:[ \t]+[A-Z0-9/-]+",
        r"PUBLIC DOCUMENT COUNT:[ \t]+[0-9]{1,4}",
        r"(?:CONFORMED PERIOD OF REPORT|FILED AS OF DATE|DATE AS OF CHANGE|EFFECTIVENESS DATE):[ \t]+[0-9]{8}",
        r"ITEM INFORMATION:[ \t]+[^<>]+",
    )
    _require(all(any(re.fullmatch(pattern, line) for pattern in top_patterns) for line in top),
             "Unsupported filing header context")
    _require(sum(line.startswith("<ACCEPTANCE-DATETIME>") for line in lines) == 1,
             "Ambiguous acceptance metadata")
    _require(not any("<" in line or ">" in line for line in lines[2:]
                     if not line.startswith("<ACCEPTANCE-DATETIME>")), "Unexpected header markup")
    _require([line for line in top if line.endswith(":")] == ["FILER:"], "Unsupported filing parties")
    index = lines.index("FILER:")
    _require(all(not line or not line[0].isspace() for line in lines[2:index])
             and all(not line or line.startswith("\t") for line in lines[index + 1:]), "Unsupported filer block")
    filer_lines = [line for line in lines[index + 1:] if line]
    section_indices = [i for i, line in enumerate(filer_lines) if not line.startswith("\t\t")]
    filer = [line.strip() for line in filer_lines]
    _require(all(filer[i] in {"COMPANY DATA:", "FILING VALUES:", "BUSINESS ADDRESS:",
                             "MAIL ADDRESS:", "FORMER COMPANY:"} for i in section_indices),
             "Unsupported filer section")
    _require(filer.count("COMPANY DATA:") == filer.count("FILING VALUES:") == 1, "Ambiguous filer sections")
    cik = _single_field(filer, "CENTRAL INDEX KEY:", r"[0-9]{10}")
    company_start = filer.index("COMPANY DATA:")
    company_end = next((i for i in section_indices if i > company_start), len(filer))
    _require(_single_field(filer[company_start + 1:company_end], "CENTRAL INDEX KEY:", r"[0-9]{10}") == cik,
             "CIK outside company data")
    _require(cik == receipt.cik, "Filing CIK mismatch")
    _require(_single_field(top, "ACCESSION NUMBER:", r"[0-9]{10}-[0-9]{2}-[0-9]{6}") == receipt.accession,
             "Filing accession mismatch")
    form = _single_field(top, "CONFORMED SUBMISSION TYPE:", r"[A-Z0-9/-]+")
    _require(form in SUPPORTED_FORMS and _single_field(filer, "FORM TYPE:", r"[A-Z0-9/-]+") == form,
             "Unsupported semantic extraction form")
    filing_start = filer.index("FILING VALUES:")
    filing_end = next((i for i in section_indices if i > filing_start), len(filer))
    _require(_single_field(filer[filing_start + 1:filing_end], "FORM TYPE:", r"[A-Z0-9/-]+") == form,
             "Form outside filing values")
    count = int(_single_field(top, "PUBLIC DOCUMENT COUNT:", r"[0-9]{1,4}"))
    _require(1 <= count <= 1000, "Unsupported document count")
    tail_start = end + len(b"</SEC-HEADER>")
    markers = []
    for marker in re.finditer(rb"(?m)^</?(?:DOCUMENT|TEXT|SEC-DOCUMENT)>\r?$", raw[tail_start:]):
        markers.append(marker)
        _require(len(markers) <= 4 * count + 1, "Excess document delimiters")
    _require(len(markers) == 4 * count + 1, "Unbalanced document envelope")
    _require(markers[-1][0].rstrip(b"\r") == b"</SEC-DOCUMENT>"
             and not raw[tail_start + markers[-1].end():].strip(), "Invalid filing terminator")
    cursor, sequences, filenames, types, primary = tail_start, set(), set(), [], None
    for ordinal in range(count):
        a, b, c, d = markers[ordinal * 4:ordinal * 4 + 4]
        _require([m[0].rstrip(b"\r") for m in (a, b, c, d)] ==
                 [b"<DOCUMENT>", b"<TEXT>", b"</TEXT>", b"</DOCUMENT>"], "Invalid document delimiters")
        _require(not raw[cursor:tail_start + a.start()].strip(), "Unexpected envelope content")
        try:
            fields = raw[tail_start + a.end():tail_start + b.start()].decode("ascii").strip("\r\n").splitlines()
        except UnicodeError:
            raise UnsupportedRegisteredSecuritySource("Unsupported document metadata") from None
        _require(len(fields) in (3, 4) and all(fields[i].startswith(tag) for i, tag in
                 enumerate(("<TYPE>", "<SEQUENCE>", "<FILENAME>")))
                 and (len(fields) == 3 or fields[3].startswith("<DESCRIPTION>")), "Unsupported document metadata")
        kind = _single_field(fields, "<TYPE>", r"[A-Za-z0-9._/-]+")
        sequence = _single_field(fields, "<SEQUENCE>", r"[1-9][0-9]{0,5}")
        filename = _single_field(fields, "<FILENAME>", r"[A-Za-z0-9][A-Za-z0-9_.-]*")
        _require(sequence not in sequences and filename not in filenames, "Duplicate document identity")
        sequences.add(sequence)
        filenames.add(filename)
        types.append(kind)
        start = tail_start + b.end() + 1  # Exclude the TEXT delimiter's newline.
        stop = tail_start + c.start()
        _require(raw[start - 1:start] == b"\n", "Missing TEXT newline")
        # Exclude exactly the closing delimiter's preceding newline, not payload whitespace.
        stop -= 2 if raw[stop - 2:stop] == b"\r\n" else 1
        payload = raw[start:stop]
        _require(bool(payload.strip()), "Empty primary or exhibit document")
        _require(re.search(rb"(?m)^</?(?:SEC-DOCUMENT|SEC-HEADER|DOCUMENT|TEXT)>[^\n]*$", payload) is None,
                 "Reserved delimiter inside document")
        _require(not raw[tail_start + c.end():tail_start + d.start()].strip(), "Unexpected TEXT suffix")
        if ordinal == 0:
            primary = (PrimaryDocumentProvenance(receipt.receipt_id, cik, receipt.accession, form,
                       receipt.endpoint, ordinal, sequence, filename, start, len(payload), digest(payload)), payload)
        cursor = tail_start + d.end()
    _require(not raw[cursor:tail_start + markers[-1].start()].strip()
             and types[0] == form and types.count(form) == 1, "Ambiguous primary document")
    return primary


class _NoExternalResources(etree.Resolver):
    def resolve(self, url, public_id, context):
        raise UnsupportedRegisteredSecuritySource("External XML resource forbidden")


def _qname(element, value):
    _require(type(value) is str and len(value) <= 512, "Missing or oversized QName")
    parts = value.split(":")
    _require(len(parts) in (1, 2) and all(_TOKEN.fullmatch(part) for part in parts), "Unsupported QName")
    namespace = element.nsmap.get(parts[0] if len(parts) == 2 else None)
    _require(bool(namespace), "Unbound QName")
    return "{" + namespace + "}" + parts[-1]


def _children(element):
    return [child for child in element if isinstance(child.tag, str)]


def _structural_whitespace(element):
    _require(not (element.text or "").strip() and all(not (c.tail or "").strip() for c in element),
             "Unexpected context mixed content")


def _leaf(element):
    _require(not _children(element), "Unexpected nested context value")
    # Comment/PI tails are still source text; ignoring them could hide a conflict.
    return "".join(element.itertext())


def _context(element, ordinal):
    _require(set(element.attrib) == {"id"} and _TOKEN.fullmatch(element.get("id", "")), "Invalid context ID")
    children = _children(element)
    _require([c.tag for c in children] == ["{" + XBRLI + "}entity", "{" + XBRLI + "}period"],
             "Unsupported context structure or scenario")
    entity, period = children
    for container in (element, entity, period):
        _structural_whitespace(container)
    children = _children(entity)
    _require(not entity.attrib and len(children) in (1, 2)
             and children[0].tag == "{" + XBRLI + "}identifier", "Unsupported context entity")
    identifier = children[0]
    scheme, value = identifier.get("scheme"), _leaf(identifier)
    _require(set(identifier.attrib) == {"scheme"} and scheme == "http://www.sec.gov/CIK"
             and re.fullmatch(r"[0-9]{10}", value), "Unsupported entity identifier")
    dimensions = []
    if len(children) == 2:
        segment = children[1]
        _require(segment.tag == "{" + XBRLI + "}segment" and not segment.attrib, "Unsupported entity segment")
        _structural_whitespace(segment)
        _require(bool(_children(segment)), "Empty context segment unsupported")
        for member in _children(segment):
            _require(member.tag == "{" + XBRLDI + "}explicitMember" and set(member.attrib) == {"dimension"},
                     "Only explicit dimensions supported")
            source_axis, source_member = member.get("dimension"), _leaf(member)
            axis, member_name = _qname(member, source_axis), _qname(member, source_member)
            _require(axis in CLASS_AXES | EXCHANGE_AXES, "Unsupported registered-security axis")
            _require(axis not in {d.axis for d in dimensions}, "Duplicate context dimension")
            dimensions.append(SourceDimension(axis, member_name, source_axis, source_member))
    dates = _children(period)
    _require(not period.attrib and [c.tag for c in dates] ==
             ["{" + XBRLI + "}startDate", "{" + XBRLI + "}endDate"], "Only duration contexts supported")
    values = tuple(_leaf(c) for c in dates)
    _require(all(not c.attrib for c in dates) and
             all(re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", v) for v in values), "Unsupported context dates")
    try:
        _require(date.fromisoformat(values[0]) <= date.fromisoformat(values[1]), "Reversed context period")
    except ValueError:
        raise UnsupportedRegisteredSecuritySource("Invalid context dates") from None
    return SourceContext(element.get("id"), ordinal, scheme, value, *values, tuple(dimensions))


def _parse_inline(payload, document):
    try:
        payload.decode("utf-8")  # No fallback decoding or lossy replacement.
    except UnicodeError:
        raise UnsupportedRegisteredSecuritySource("Only UTF-8 primary documents supported") from None
    _require(b"<!DOCTYPE" not in payload.upper() and b"<!ENTITY" not in payload.upper(), "DTD/entity declarations unsupported")
    parser = etree.XMLParser(resolve_entities=False, load_dtd=False, no_network=True,
                             recover=False, huge_tree=False, remove_comments=False)
    parser.resolvers.add(_NoExternalResources())
    try:
        root = etree.fromstring(payload, parser)
    except (etree.XMLSyntaxError, ValueError):
        raise UnsupportedRegisteredSecuritySource("Malformed or unsupported XHTML/XML") from None
    _require(root.tag == "{" + XHTML + "}html", "Namespaced XHTML primary required")
    _require(root.getroottree().docinfo.encoding.upper().replace("-", "") == "UTF8", "Only UTF-8 XML supported")
    elements = []
    namespaces = set()
    ids, contexts = {}, {}
    for element in root.iter():
        if not isinstance(element.tag, str):
            continue
        ordinal = len(elements)
        elements.append(element)
        _require(len(elements) <= MAX_ELEMENTS, "Element safety bound exceeded")
        namespaces.update(element.nsmap.values())
        source_id = element.get("id")
        if source_id is not None:
            _require(source_id not in ids, "Duplicate XML ID")
            ids[source_id] = element
        if element.tag == "{" + XBRLI + "}context":
            _require(source_id is not None, "Missing context ID")
            contexts[source_id] = (element, ordinal)
            _require(len(contexts) <= MAX_CONTEXTS, "Context safety bound exceeded")
        if element.tag.startswith("{" + IX + "}"):
            _require(element.get("target", "") == "", "Multiple Inline XBRL targets unsupported")
    # Family prefixes identify declarations to check, never acceptable years.
    # Every DEI/GAAP declaration (including nested/unused ones) must fit ONE
    # literal reviewed pair. An unused companion namespace need not be declared.
    taxonomy_namespaces = {ns for ns in namespaces if ns.startswith(
        ("http://xbrl.sec.gov/dei/", "http://fasb.org/us-gaap/"))}
    _require(any(taxonomy_namespaces <= set(profile) for profile in TAXONOMY_PROFILES),
             "Mixed or unreviewed taxonomy generations")
    headers = [e for e in elements if e.tag == "{" + IX + "}header"]
    resources = [e for e in elements if e.tag == "{" + IX + "}resources"]
    _require(len(headers) == len(resources) == 1 and resources[0].getparent() is headers[0],
             "Single Inline XBRL header/resources required")
    parsed_contexts, facts = {}, []
    for ordinal, element in enumerate(elements):
        _require(element.tag not in FACT_QNAMES,
                 "Non-Inline registered-security fact unsupported")
        if not element.tag.startswith("{" + IX + "}") or element.get("name") is None:
            continue
        name = _qname(element, element.get("name"))
        local = name.rsplit("}", 1)[-1]
        if local not in FACT_NAMES:
            continue
        _require(name in FACT_QNAMES, "Unreviewed registered-security concept namespace")
        _require(element.tag == "{" + IX + "}nonNumeric", "Registered-security fact must be nonNumeric")
        allowed = {"name", "contextRef", "id", "escape", "target", "{" + XML + "}lang"}
        _require(set(element.attrib) <= allowed and element.get("escape", "false") in {"false", "0"},
                 "Transformed, nil, continued, escaped or tuple facts unsupported")
        ref = element.get("contextRef")
        _require(ref in contexts, "Unknown fact contextRef")
        context_element, context_ordinal = contexts[ref]
        _require(context_element.getparent() is resources[0], "Context must be in Inline resources")
        if ref not in parsed_contexts:
            parsed_contexts[ref] = _context(context_element, context_ordinal)
        _require(all(e.tag.startswith("{" + XHTML + "}") and e.tag not in
                     {"{" + XHTML + "}script", "{" + XHTML + "}style"}
                     for e in element.iterdescendants() if isinstance(e.tag, str)),
                 "Nested Inline facts, exclusions or foreign value markup unsupported")
        _require(not any(e.tag in {"{" + IX + "}tuple", "{" + IX + "}nonNumeric",
                                   "{" + XHTML + "}script", "{" + XHTML + "}style"}
                         for e in element.iterancestors()), "Unsupported fact ancestor")
        value = "".join(element.itertext())
        _require(bool(value.strip()) and len(value) <= MAX_VALUE_LENGTH, "Empty or oversized fact value")
        if local == "NoTradingSymbolFlag":
            _require(value in {"true", "1"}, "Only literal true no-symbol assertions supported")
        language = next((e.get("{" + XML + "}lang") for e in (element, *element.iterancestors())
                         if e.get("{" + XML + "}lang") is not None), None)
        facts.append(RegisteredSecurityFactOccurrence(document.evidence_id, ordinal, element.sourceline,
                     name, element.get("name"), element.get("id"), ref, value, language))
        _require(len(facts) <= MAX_FACTS, "Fact safety bound exceeded")
    return tuple(sorted(parsed_contexts.values(), key=lambda c: c.element_ordinal)), tuple(facts)


def _claims(contexts, facts, cik):
    by_ref = {c.context_id: c for c in contexts}
    context_ids = {c.context_id: c.semantic_id for c in contexts}
    scope_ids = {c.context_id: c.source_security_scope_id for c in contexts}
    scope_titles, scope_exchange_flags, period_class_flags = {}, {}, {}
    for context in contexts:
        scope_exchange_flags.setdefault(scope_ids[context.context_id], set()).add(
            any(d.axis in EXCHANGE_AXES for d in context.dimensions))
        period_class_flags.setdefault(context.aspects()[:4], set()).add(
            any(d.axis in CLASS_AXES for d in context.dimensions))
    groups = {}
    for fact in facts:
        groups.setdefault(context_ids[fact.context_ref], []).append(fact)
        if fact.fact_name.rsplit("}", 1)[-1] == "Security12bTitle":
            scope_titles.setdefault(scope_ids[fact.context_ref], set()).add(fact.source_value)
    records = []
    for context_id, occurrences in sorted(groups.items()):
        context = by_ref[occurrences[0].context_ref]
        # Namespaces were verified as a single reviewed profile before grouping.
        values = [tuple(sorted({f.source_value for f in occurrences if f.fact_name.rsplit("}", 1)[-1] == name}))
                  for name in FACT_NAMES]
        title, symbols, flags, exchanges = values
        issues = set()
        if any(len(v) > 1 for v in values):
            issues.add(ClaimIssue.CONTRADICTORY_FACTS)
        if symbols and flags:
            issues.add(ClaimIssue.SYMBOL_AND_NO_SYMBOL)
        if not title:
            issues.add(ClaimIssue.MISSING_TITLE)
        if not symbols and not flags:
            issues.add(ClaimIssue.MISSING_SYMBOL_ASSERTION)
        if not exchanges:
            issues.add(ClaimIssue.MISSING_EXCHANGE)
        if context.entity_identifier != cik:
            issues.add(ClaimIssue.CONTEXT_ENTITY_MISMATCH)
        # Explicit exchange-axis relationships only; titles never create joins.
        scope_id = scope_ids[context.context_id]
        if len(scope_titles.get(scope_id, ())) > 1:
            issues.add(ClaimIssue.INCONSISTENT_SECURITY_TITLE)
        if scope_exchange_flags[scope_id] == {False, True}:
            issues.add(ClaimIssue.AMBIGUOUS_DIMENSION_SCOPE)
        if period_class_flags[context.aspects()[:4]] == {False, True}:
            issues.add(ClaimIssue.AMBIGUOUS_DIMENSION_SCOPE)
        records.append(RegisteredSecurityContextClaims(context_id, scope_id,
                       tuple(sorted({f.context_ref for f in occurrences})), *values,
                       tuple(f.occurrence_id for f in occurrences), tuple(sorted(issues))))
    return tuple(records)


def extract_sec_registered_security_claims(
    archive: SecFilingArchive,
    request: SecRegisteredSecurityExtractionRequest,
) -> SecRegisteredSecurityExtractionAssessment:
    """Read verified bytes for ONE explicit receipt; no other I/O, clocks or authority.

    Storage errors propagate as FilingArchiveError. Unsupported source structure
    raises UnsupportedRegisteredSecuritySource. Contradictions/incomplete pairings
    retain every fact and report a non-success status without selecting winners.
    """
    if type(archive) is not SecFilingArchive or type(request) is not SecRegisteredSecurityExtractionRequest:
        raise RegisteredSecurityRequestError("Exact typed archive/request required")
    receipt = archive.read_receipt(request.filing_receipt_id)
    document, payload = _primary_document(archive.read_object(receipt), receipt)
    contexts, facts = _parse_inline(payload, document)
    claims = _claims(contexts, facts, document.cik)
    issues = {issue for claim in claims for issue in claim.issues}
    if issues & _CONFLICTS:
        status = ExtractionStatus.SOURCE_CONFLICT
    elif issues:
        status = ExtractionStatus.INCOMPLETE_REGISTERED_SECURITY_CLAIMS
    elif claims:
        status = ExtractionStatus.CAPTURED_REGISTERED_SECURITY_CLAIMS
    else:
        status = ExtractionStatus.NO_SUPPORTED_REGISTERED_SECURITY_CLAIMS
    return SecRegisteredSecurityExtractionAssessment(EXTRACTION_CONTRACT_VERSION, status, receipt,
                                                      document, contexts, facts, claims)
