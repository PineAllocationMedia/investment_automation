"""Offline SEC common-class and diluted-EPS source claims.

Extraction establishes none of Property 4A–4H or obligations 5–7.  In
particular, an XBRL class member is not a PAM security/class identity and an EPS
context is not proof of economic entitlement or applicability.
"""
from dataclasses import asdict, dataclass
from datetime import date
from enum import StrEnum
import re

from lxml import etree

from .sec_filing_archive import FilingReceipt, SecFilingArchive, canonical_json, digest
from .sec_primary_document import (
    PrimaryDocumentProvenance,
    UnsupportedPrimaryDocumentSource,
    read_primary_document,
)

EXTRACTION_CONTRACT_VERSION = "2026-09-26-sec-class-eps-source-claims-v1"
SUPPORTED_FORMS = frozenset(("10-K", "10-K/A", "10-Q", "10-Q/A"))
TAXONOMY_PROFILES = (
    ("http://xbrl.sec.gov/dei/2025", "http://fasb.org/us-gaap/2025"),
    ("http://xbrl.sec.gov/dei/2026", "http://fasb.org/us-gaap/2026"),
)
IX = "http://www.xbrl.org/2013/inlineXBRL"
XBRLI = "http://www.xbrl.org/2003/instance"
XBRLDI = "http://xbrl.org/2006/xbrldi"
XHTML = "http://www.w3.org/1999/xhtml"
XSI = "http://www.w3.org/2001/XMLSchema-instance"
CLASS_AXIS_LOCAL_NAME = "StatementClassOfStockAxis"
COMMON_SHARES_LOCAL_NAME = "EntityCommonStockSharesOutstanding"
DILUTED_EPS_LOCAL_NAME = "EarningsPerShareDiluted"
MAX_ELEMENTS = 250_000
MAX_CONTEXTS = 20_000
MAX_FACTS = 10_000
MAX_VALUE_LENGTH = 16_384
_TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_.-]{0,255}")
_DECIMAL_LEXICAL = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)")


class SecClassEPSRequestError(ValueError):
    """Invalid explicit filing-receipt selection."""


class UnsupportedSecClassEPSSource(ValueError):
    """Unsupported structure or representation; never partial success."""


class ExtractionStatus(StrEnum):
    CAPTURED_CLASS_EPS_SOURCE_CLAIMS = "CAPTURED_CLASS_EPS_SOURCE_CLAIMS"
    INCOMPLETE_CLASS_EPS_SOURCE_CLAIMS = "INCOMPLETE_CLASS_EPS_SOURCE_CLAIMS"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"
    NO_SUPPORTED_CLASS_EPS_SOURCE_CLAIMS = "NO_SUPPORTED_CLASS_EPS_SOURCE_CLAIMS"


class SourceFactKind(StrEnum):
    COMMON_STOCK_SHARES_OUTSTANDING = "COMMON_STOCK_SHARES_OUTSTANDING"
    DILUTED_EPS = "DILUTED_EPS"


class ClaimIssue(StrEnum):
    CONTRADICTORY_SOURCE_ASSERTIONS = "CONTRADICTORY_SOURCE_ASSERTIONS"
    CONTEXT_ENTITY_MISMATCH = "CONTEXT_ENTITY_MISMATCH"
    DIMENSIONED_AND_UNDIMENSIONED_EPS = "DIMENSIONED_AND_UNDIMENSIONED_EPS"
    MISSING_COMMON_STOCK_SOURCE_ASSERTION = "MISSING_COMMON_STOCK_SOURCE_ASSERTION"
    MISSING_DILUTED_EPS_SOURCE_ASSERTION = "MISSING_DILUTED_EPS_SOURCE_ASSERTION"


_CONFLICTS = frozenset((
    ClaimIssue.CONTRADICTORY_SOURCE_ASSERTIONS,
    ClaimIssue.CONTEXT_ENTITY_MISMATCH,
    ClaimIssue.DIMENSIONED_AND_UNDIMENSIONED_EPS,
))


def _require(condition, message):
    if not condition:
        raise UnsupportedSecClassEPSSource(message)


def _identity(domain, value):
    return digest(("pam:sec-class-eps-claims:" + domain + ":v1\0").encode("ascii")
                  + canonical_json(value))


@dataclass(frozen=True, slots=True)
class SecClassEPSExtractionRequest:
    filing_receipt_id: str

    def __post_init__(self):
        if (type(self.filing_receipt_id) is not str
                or re.fullmatch(r"[0-9a-f]{64}", self.filing_receipt_id) is None):
            raise SecClassEPSRequestError("Exact filing receipt ID required")


@dataclass(frozen=True, slots=True)
class SourceTaxonomyProfile:
    dei_namespace: str
    us_gaap_namespace: str


@dataclass(frozen=True, slots=True)
class SourceDimension:
    axis: str  # Expanded QName.
    member: str  # Expanded QName; custom members remain opaque.
    source_axis: str
    source_member: str


@dataclass(frozen=True, slots=True)
class SourcePeriod:
    kind: str  # INSTANT or DURATION.
    start_date: str | None
    end_date: str


@dataclass(frozen=True, slots=True)
class SourceContext:
    context_id: str
    element_ordinal: int
    entity_scheme: str
    entity_identifier: str
    period: SourcePeriod
    dimensions: tuple[SourceDimension, ...]

    def aspects(self):
        return (self.entity_scheme, self.entity_identifier, asdict(self.period),
                tuple(sorted((dimension.axis, dimension.member)
                             for dimension in self.dimensions)))

    @property
    def semantic_id(self):
        return _identity("context", self.aspects())

    def source_class_scope_id(self, document):
        """Filing-local context relationship, never a durable/economic class ID."""
        members = tuple((dimension.axis, dimension.member) for dimension in self.dimensions)
        if not members:
            return None
        return _identity("filing-local-class-scope", {
            "filing": (document.cik, document.accession, document.form),
            "members": members,
        })


@dataclass(frozen=True, slots=True)
class SourceRepresentation:
    unit_ref: str
    decimals: str | None
    precision: str | None


@dataclass(frozen=True, slots=True)
class ClassEPSFactOccurrence:
    primary_document_id: str
    element_ordinal: int
    source_line: int
    fact_kind: SourceFactKind
    concept_name: str  # Expanded QName.
    source_name: str  # Lexical QName.
    source_fact_id: str | None
    context_ref: str
    source_class_scope_id: str | None
    source_value: str  # Exact XML-decoded lexical value; never converted.
    representation: SourceRepresentation

    @property
    def occurrence_id(self):
        return _identity("fact-occurrence", asdict(self))


@dataclass(frozen=True, slots=True)
class SourceAssertion:
    source_value: str
    representation: SourceRepresentation


@dataclass(frozen=True, slots=True)
class ClassEPSSourceClaim:
    fact_kind: SourceFactKind
    concept_name: str
    context_semantic_id: str
    source_class_scope_id: str | None
    context_refs: tuple[str, ...]
    assertions: tuple[SourceAssertion, ...]
    occurrence_ids: tuple[str, ...]
    issues: tuple[ClaimIssue, ...]


@dataclass(frozen=True, slots=True)
class SecClassEPSExtractionAssessment:
    contract_version: str
    status: ExtractionStatus
    receipt: FilingReceipt
    primary_document: PrimaryDocumentProvenance
    taxonomy_profile: SourceTaxonomyProfile
    contexts: tuple[SourceContext, ...]
    occurrences: tuple[ClassEPSFactOccurrence, ...]
    claims: tuple[ClassEPSSourceClaim, ...]
    issues: tuple[ClaimIssue, ...]

    @property
    def semantic_id(self):
        context_ids = {context.context_id: context.semantic_id for context in self.contexts}
        facts = sorted(set((occurrence.fact_kind, occurrence.concept_name,
                            context_ids[occurrence.context_ref],
                            occurrence.source_class_scope_id, occurrence.source_value,
                            (occurrence.representation.unit_ref,
                             occurrence.representation.decimals,
                             occurrence.representation.precision))
                           for occurrence in self.occurrences), key=repr)
        return _identity("assessment-semantics", {
            "contract": self.contract_version,
            "status": self.status,
            "profile": asdict(self.taxonomy_profile),
            "filing": (self.primary_document.cik, self.primary_document.accession,
                       self.primary_document.form),
            "facts": facts,
            "claims": [(claim.fact_kind, claim.concept_name,
                        claim.context_semantic_id, claim.source_class_scope_id,
                        claim.issues) for claim in self.claims],
            "issues": self.issues,
        })

    @property
    def evidence_id(self):
        return _identity("assessment-evidence", {
            "semantic_id": self.semantic_id,
            "receipt": self.receipt.receipt_id,
            "document": asdict(self.primary_document),
            "contexts": [asdict(context) for context in self.contexts],
            "occurrences": [asdict(occurrence) for occurrence in self.occurrences],
            "claims": [asdict(claim) for claim in self.claims],
        })


class _NoExternalResources(etree.Resolver):
    def resolve(self, url, public_id, context):
        raise UnsupportedSecClassEPSSource("External XML resource forbidden")


def _qname(element, value):
    _require(type(value) is str and len(value) <= 512, "Missing or oversized QName")
    parts = value.split(":")
    _require(len(parts) in (1, 2) and all(_TOKEN.fullmatch(part) for part in parts),
             "Unsupported QName")
    namespace = element.nsmap.get(parts[0] if len(parts) == 2 else None)
    _require(bool(namespace), "Unbound QName")
    return "{" + namespace + "}" + parts[-1]


def _children(element):
    return [child for child in element if isinstance(child.tag, str)]


def _structural_whitespace(element):
    _require(not (element.text or "").strip()
             and all(not (child.tail or "").strip() for child in element),
             "Unexpected context mixed content")


def _leaf(element):
    _require(not _children(element), "Unexpected nested context value")
    return "".join(element.itertext())


def _source_date(value):
    _require(re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value) is not None,
             "Unsupported context date")
    try:
        date.fromisoformat(value)
    except ValueError:
        raise UnsupportedSecClassEPSSource("Invalid context date") from None
    return value


def _context(element, ordinal, class_axis):
    _require(set(element.attrib) == {"id"} and _TOKEN.fullmatch(element.get("id", "")),
             "Invalid context ID")
    children = _children(element)
    _require([child.tag for child in children] ==
             ["{" + XBRLI + "}entity", "{" + XBRLI + "}period"],
             "Unsupported context structure or scenario")
    entity, period = children
    for container in (element, entity, period):
        _structural_whitespace(container)
    entity_children = _children(entity)
    _require(not entity.attrib and len(entity_children) in (1, 2)
             and entity_children[0].tag == "{" + XBRLI + "}identifier",
             "Unsupported context entity")
    identifier = entity_children[0]
    scheme, identifier_value = identifier.get("scheme"), _leaf(identifier)
    _require(set(identifier.attrib) == {"scheme"}
             and scheme == "http://www.sec.gov/CIK"
             and re.fullmatch(r"[0-9]{10}", identifier_value) is not None,
             "Unsupported entity identifier")
    dimensions = []
    if len(entity_children) == 2:
        segment = entity_children[1]
        _require(segment.tag == "{" + XBRLI + "}segment" and not segment.attrib,
                 "Unsupported entity segment")
        _structural_whitespace(segment)
        _require(bool(_children(segment)), "Empty context segment unsupported")
        for member in _children(segment):
            _require(member.tag == "{" + XBRLDI + "}explicitMember"
                     and set(member.attrib) == {"dimension"},
                     "Only explicit dimensions supported")
            source_axis, source_member = member.get("dimension"), _leaf(member)
            axis, member_name = _qname(member, source_axis), _qname(member, source_member)
            _require(axis == class_axis, "Unsupported target-fact dimension")
            _require(not dimensions, "Duplicate class dimension")
            dimensions.append(SourceDimension(axis, member_name, source_axis, source_member))
    period_children = _children(period)
    _require(not period.attrib, "Unsupported context period attributes")
    if [child.tag for child in period_children] == ["{" + XBRLI + "}instant"]:
        instant = period_children[0]
        _require(not instant.attrib, "Unsupported instant attributes")
        source_period = SourcePeriod("INSTANT", None, _source_date(_leaf(instant)))
    else:
        _require([child.tag for child in period_children] ==
                 ["{" + XBRLI + "}startDate", "{" + XBRLI + "}endDate"],
                 "Only instant or duration contexts supported")
        _require(all(not child.attrib for child in period_children),
                 "Unsupported duration attributes")
        start, end = (_source_date(_leaf(child)) for child in period_children)
        _require(date.fromisoformat(start) <= date.fromisoformat(end),
                 "Reversed context period")
        source_period = SourcePeriod("DURATION", start, end)
    return SourceContext(element.get("id"), ordinal, scheme, identifier_value,
                         source_period, tuple(dimensions))


def _profile(namespaces):
    taxonomy_namespaces = {namespace for namespace in namespaces if namespace.startswith(
        ("http://xbrl.sec.gov/dei/", "http://fasb.org/us-gaap/"))}
    candidates = [profile for profile in TAXONOMY_PROFILES
                  if taxonomy_namespaces and taxonomy_namespaces <= set(profile)]
    _require(len(candidates) == 1, "Mixed or unreviewed taxonomy generations")
    return SourceTaxonomyProfile(*candidates[0])


def _parse_inline(payload, document):
    try:
        payload.decode("utf-8")
    except UnicodeError:
        raise UnsupportedSecClassEPSSource("Only UTF-8 primary documents supported") from None
    _require(b"<!DOCTYPE" not in payload.upper() and b"<!ENTITY" not in payload.upper(),
             "DTD/entity declarations unsupported")
    parser = etree.XMLParser(resolve_entities=False, load_dtd=False, no_network=True,
                             recover=False, huge_tree=False, remove_comments=False)
    parser.resolvers.add(_NoExternalResources())
    try:
        root = etree.fromstring(payload, parser)
    except (etree.XMLSyntaxError, ValueError):
        raise UnsupportedSecClassEPSSource("Malformed or unsupported XHTML/XML") from None
    _require(root.tag == "{" + XHTML + "}html", "Namespaced XHTML primary required")
    _require(root.getroottree().docinfo.encoding.upper().replace("-", "") == "UTF8",
             "Only UTF-8 XML supported")
    elements, namespaces, ids, contexts = [], set(), {}, {}
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
    profile = _profile(namespaces)
    class_axis = "{" + profile.us_gaap_namespace + "}" + CLASS_AXIS_LOCAL_NAME
    concepts = {
        "{" + profile.dei_namespace + "}" + COMMON_SHARES_LOCAL_NAME:
            SourceFactKind.COMMON_STOCK_SHARES_OUTSTANDING,
        "{" + profile.us_gaap_namespace + "}" + DILUTED_EPS_LOCAL_NAME:
            SourceFactKind.DILUTED_EPS,
    }
    headers = [element for element in elements if element.tag == "{" + IX + "}header"]
    resources = [element for element in elements if element.tag == "{" + IX + "}resources"]
    _require(len(headers) == len(resources) == 1 and resources[0].getparent() is headers[0],
             "Single Inline XBRL header/resources required")
    parsed_contexts, facts = {}, []
    target_local_names = {COMMON_SHARES_LOCAL_NAME, DILUTED_EPS_LOCAL_NAME}
    for ordinal, element in enumerate(elements):
        _require(element.tag not in concepts, "Non-Inline target fact unsupported")
        if not element.tag.startswith("{" + IX + "}") or element.get("name") is None:
            continue
        name = _qname(element, element.get("name"))
        local_name = name.rsplit("}", 1)[-1]
        if local_name not in target_local_names:
            continue
        _require(name in concepts, "Unreviewed target concept namespace")
        _require(element.tag == "{" + IX + "}nonFraction",
                 "Target numeric fact must be ix:nonFraction")
        allowed = {"name", "contextRef", "unitRef", "decimals", "precision", "id", "target"}
        _require(set(element.attrib) <= allowed
                 and "{" + XSI + "}nil" not in element.attrib
                 and not ({"decimals", "precision"} <= set(element.attrib)),
                 "Transformed, scaled, signed, nil, continued or ambiguous fact unsupported")
        unit_ref = element.get("unitRef")
        _require(type(unit_ref) is str and _TOKEN.fullmatch(unit_ref) is not None,
                 "Exact unitRef required")
        decimals, precision = element.get("decimals"), element.get("precision")
        _require((decimals is None or re.fullmatch(r"INF|[+-]?[0-9]{1,6}", decimals))
                 and (precision is None or re.fullmatch(r"INF|[1-9][0-9]{0,5}", precision)),
                 "Unsupported accuracy attribute")
        ref = element.get("contextRef")
        _require(ref in contexts, "Unknown fact contextRef")
        context_element, context_ordinal = contexts[ref]
        _require(context_element.getparent() is resources[0],
                 "Context must be in Inline resources")
        if ref not in parsed_contexts:
            parsed_contexts[ref] = _context(context_element, context_ordinal, class_axis)
        context = parsed_contexts[ref]
        expected_period = ("INSTANT" if concepts[name] is
                           SourceFactKind.COMMON_STOCK_SHARES_OUTSTANDING else "DURATION")
        _require(context.period.kind == expected_period,
                 "Target fact uses unsupported period type")
        _require(not _children(element), "Nested numeric representation unsupported")
        _require(not any(ancestor.tag in {"{" + IX + "}tuple", "{" + IX + "}nonFraction"}
                         for ancestor in element.iterancestors()),
                 "Unsupported target fact ancestor")
        value = "".join(element.itertext())
        _require(len(value) <= MAX_VALUE_LENGTH and _DECIMAL_LEXICAL.fullmatch(value) is not None,
                 "Unsupported numeric lexical representation")
        representation = SourceRepresentation(unit_ref, decimals, precision)
        scope_id = context.source_class_scope_id(document)
        facts.append(ClassEPSFactOccurrence(
            document.evidence_id, ordinal, element.sourceline, concepts[name], name,
            element.get("name"), element.get("id"), ref, scope_id, value, representation))
        _require(len(facts) <= MAX_FACTS, "Fact safety bound exceeded")
    return (profile,
            tuple(sorted(parsed_contexts.values(), key=lambda context: context.element_ordinal)),
            tuple(facts))


def _claims(contexts, facts, cik):
    by_ref = {context.context_id: context for context in contexts}
    groups = {}
    for fact in facts:
        context_id = by_ref[fact.context_ref].semantic_id
        groups.setdefault((fact.fact_kind, fact.concept_name, context_id,
                           fact.source_class_scope_id), []).append(fact)
    ambiguity_keys = {}
    for fact in facts:
        if fact.fact_kind is SourceFactKind.DILUTED_EPS:
            context = by_ref[fact.context_ref]
            key = (context.entity_scheme, context.entity_identifier,
                   context.period.start_date, context.period.end_date)
            ambiguity_keys.setdefault(key, set()).add(fact.source_class_scope_id is not None)
    records = []
    for key, occurrences in sorted(groups.items(), key=lambda item: repr(item[0])):
        kind, concept, context_id, scope_id = key
        context = by_ref[occurrences[0].context_ref]
        assertions = tuple(sorted({SourceAssertion(fact.source_value, fact.representation)
                                   for fact in occurrences}, key=repr))
        issues = set()
        if len(assertions) > 1:
            issues.add(ClaimIssue.CONTRADICTORY_SOURCE_ASSERTIONS)
        if context.entity_identifier != cik:
            issues.add(ClaimIssue.CONTEXT_ENTITY_MISMATCH)
        ambiguity_key = (context.entity_scheme, context.entity_identifier,
                         context.period.start_date, context.period.end_date)
        if (kind is SourceFactKind.DILUTED_EPS
                and ambiguity_keys[ambiguity_key] == {False, True}):
            issues.add(ClaimIssue.DIMENSIONED_AND_UNDIMENSIONED_EPS)
        records.append(ClassEPSSourceClaim(
            kind, concept, context_id, scope_id,
            tuple(sorted({fact.context_ref for fact in occurrences})), assertions,
            tuple(fact.occurrence_id for fact in occurrences), tuple(sorted(issues))))
    return tuple(records)


def extract_sec_class_eps_claims(
    archive: SecFilingArchive,
    request: SecClassEPSExtractionRequest,
) -> SecClassEPSExtractionAssessment:
    """Replay one explicit D2A receipt without network, writes, clocks, or authority."""
    if type(archive) is not SecFilingArchive or type(request) is not SecClassEPSExtractionRequest:
        raise SecClassEPSRequestError("Exact typed archive/request required")
    receipt = archive.read_receipt(request.filing_receipt_id)
    try:
        document, payload = read_primary_document(
            archive.read_object(receipt), receipt, supported_forms=SUPPORTED_FORMS)
    except UnsupportedPrimaryDocumentSource as exc:
        raise UnsupportedSecClassEPSSource(str(exc)) from None
    profile, contexts, facts = _parse_inline(payload, document)
    claims = _claims(contexts, facts, document.cik)
    issues = {issue for claim in claims for issue in claim.issues}
    kinds = {fact.fact_kind for fact in facts}
    if SourceFactKind.COMMON_STOCK_SHARES_OUTSTANDING not in kinds:
        issues.add(ClaimIssue.MISSING_COMMON_STOCK_SOURCE_ASSERTION)
    if SourceFactKind.DILUTED_EPS not in kinds:
        issues.add(ClaimIssue.MISSING_DILUTED_EPS_SOURCE_ASSERTION)
    ordered_issues = tuple(sorted(issues))
    if issues & _CONFLICTS:
        status = ExtractionStatus.SOURCE_CONFLICT
    elif facts and issues:
        status = ExtractionStatus.INCOMPLETE_CLASS_EPS_SOURCE_CLAIMS
    elif facts:
        status = ExtractionStatus.CAPTURED_CLASS_EPS_SOURCE_CLAIMS
    else:
        status = ExtractionStatus.NO_SUPPORTED_CLASS_EPS_SOURCE_CLAIMS
    return SecClassEPSExtractionAssessment(
        EXTRACTION_CONTRACT_VERSION, status, receipt, document, profile,
        contexts, facts, claims, ordered_issues)
