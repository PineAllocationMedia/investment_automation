"""Lossless-in-context diluted EPS extraction and conservative archive inspection.

US-GAAP namespace is candidate accounting evidence only. No listing, share class,
split basis, publication time, availability time, or forecast root is asserted.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import json
import re

from .sec_archive import (ArchiveError, CaptureReceipt, CaptureView, SecArchive,
                          digest, reject_constant, require, unique_pairs)

EXTRACTION_VERSION = "2026-09-10-sec-diluted-eps-extraction-v1"
INSPECTION_VERSION = "2026-09-10-sec-diluted-eps-inspection-v1"
NAMESPACE = "us-gaap"
CONCEPT = "EarningsPerShareDiluted"
_BASE_POINTER = "/facts/us-gaap/EarningsPerShareDiluted/units"
QUALIFICATION_BLOCKERS = (
    "OFFLINE_CAPTURE_NOT_AUTHENTICATED",
    "PUBLICATION_AND_AVAILABILITY_NOT_ESTABLISHED",
    "SECURITY_SHARE_CLASS_AND_LISTING_NOT_ESTABLISHED",
    "SPLIT_BASIS_NOT_ESTABLISHED",
    "COMPARABLE_SERIES_NOT_RESOLVED",
    "UPSTREAM_EVIDENCE_ONLY",
)


def _semantic_json(value):
    """Canonical mapping order and exact base-ten numbers, without float loss."""
    if value is None or type(value) in (str, bool):
        return json.dumps(value, ensure_ascii=True)
    if type(value) in (int, Decimal):
        number = Decimal(value)
        require(number.is_finite(), "Finite source number required")
        sign, digits, exponent = number.as_tuple()
        if not any(digits):
            return "0"
        digits = list(digits)
        while digits[-1] == 0:
            digits.pop()
            exponent += 1
        coefficient = ("-" if sign else "") + "".join(map(str, digits))
        return coefficient + ("e" + str(exponent) if exponent else "")
    if type(value) is list:
        return "[" + ",".join(_semantic_json(item) for item in value) + "]"
    require(type(value) is dict, "Unsupported JSON value")
    return "{" + ",".join(json.dumps(key, ensure_ascii=True) + ":" + _semantic_json(value[key])
                           for key in sorted(value)) + "}"


def _identity(value):
    return digest(_semantic_json(value).encode("ascii"))


def _pointer_token(value):
    return value.replace("~", "~0").replace("/", "~1")


@dataclass(frozen=True, slots=True)
class DilutedEPSObservation:
    observation_id: str
    semantic_id: str
    cik: str
    namespace: str
    concept: str
    unit: str
    value: Decimal | None
    start: str | None
    end: str | None
    fy: int | None
    fp: str | None
    form: str | None
    filed: str | None
    accn: str | None
    frame: str | None
    source_object_hash: str
    capture_receipt_id: str
    captured_at: str
    extraction_version: str
    source_locator: str
    semantic_locator: str
    row_json: str
    metadata_limitations: tuple[str, ...]
    candidate_accounting_basis: str = "US_GAAP"


@dataclass(frozen=True, slots=True)
class Extraction:
    extraction_version: str
    receipt_id: str
    observations: tuple[DilutedEPSObservation, ...]
    issues: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CandidateAssessment:
    observation_id: str
    annual_form_candidate: bool
    inclusive_duration_days: int | None
    supported_annual_period: bool
    positive_eps: bool
    status: str
    reasons: tuple[str, ...]
    qualification_blockers: tuple[str, ...] = QUALIFICATION_BLOCKERS


@dataclass(frozen=True, slots=True)
class Ambiguity:
    kind: str
    start: str
    end: str
    observation_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ArchiveInspection:
    inspection_version: str
    capture_view: CaptureView
    extractions: tuple[Extraction, ...]
    assessments: tuple[CandidateAssessment, ...]
    ambiguities: tuple[Ambiguity, ...]
    status: str
    qualification_blockers: tuple[str, ...] = QUALIFICATION_BLOCKERS


def extract_diluted_eps(raw, receipt):
    require(type(receipt) is CaptureReceipt, "Typed receipt required")
    require(digest(raw) == receipt.content_sha256 and len(raw) == receipt.byte_length,
            "Source bytes do not match receipt")
    try:
        source = json.loads(raw, parse_float=Decimal, object_pairs_hook=unique_pairs,
                            parse_constant=reject_constant)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ArchiveError("Invalid SEC-style JSON") from exc
    require(type(source) is dict, "Source JSON object required")
    source_cik = source.get("cik")
    source_issues = []
    if source_cik is None:
        source_issues.append("MISSING_SOURCE_CIK")
    else:
        require((type(source_cik) is int and 0 <= source_cik <= 9999999999)
                or (type(source_cik) is str and re.fullmatch(r"[0-9]{1,10}", source_cik)),
                "Invalid source CIK")
        require(str(source_cik).zfill(10) == receipt.cik, "Source/receipt CIK mismatch")

    node = source
    for key in ("facts", NAMESPACE, CONCEPT, "units"):
        if key not in node:
            return Extraction(EXTRACTION_VERSION, receipt.receipt_id, (),
                              tuple(sorted(source_issues + ["DILUTED_EPS_UNAVAILABLE"])))
        node = node[key]
        require(type(node) is dict, "Malformed diluted EPS source structure")
    observations = []
    for unit in sorted(node):
        rows = node[unit]
        require(type(rows) is list, "SEC unit rows must be an array")
        for index, raw_row in enumerate(rows):
            limitations = list(source_issues)
            row = raw_row if type(raw_row) is dict else {}
            if type(raw_row) is not dict:
                limitations.append("MALFORMED_ROW")
            metadata = {}
            for key in ("start", "end", "fp", "form", "filed", "accn", "frame"):
                value = row.get(key)
                if value is not None and (type(value) is not str or not value.strip()):
                    limitations.append("INVALID_" + key.upper())
                    value = None
                if value is None and key != "frame":
                    limitations.append("MISSING_" + key.upper())
                metadata[key] = value
            fy = row.get("fy")
            if type(fy) is not int:
                limitations.append("MISSING_FY" if fy is None else "INVALID_FY")
                fy = None
            value = row.get("val")
            if type(value) not in (int, Decimal):
                limitations.append("MISSING_VALUE" if value is None else "INVALID_VALUE")
                value = None
            else:
                value = Decimal(value)
            if re.fullmatch(r"[A-Z]{3}/shares", unit) is None:
                limitations.append("UNSUPPORTED_OR_MISSING_UNIT")
            row_json = _semantic_json(raw_row)
            semantic_id = _identity({"cik": receipt.cik, "namespace": NAMESPACE,
                                     "concept": CONCEPT, "unit": unit, "row": raw_row})
            pointer = _BASE_POINTER + "/" + _pointer_token(unit) + "/" + str(index)
            semantic_locator = _BASE_POINTER + "/" + _pointer_token(unit) + "/sha256:" + semantic_id
            observation_id = _identity({"source_object_hash": receipt.content_sha256,
                                        "capture_receipt_id": receipt.receipt_id,
                                        "semantic_id": semantic_id, "source_locator": pointer,
                                        "extraction_version": EXTRACTION_VERSION})
            observations.append(DilutedEPSObservation(
                observation_id, semantic_id, receipt.cik, NAMESPACE, CONCEPT, unit, value,
                metadata["start"], metadata["end"], fy, metadata["fp"], metadata["form"],
                metadata["filed"], metadata["accn"], metadata["frame"], receipt.content_sha256,
                receipt.receipt_id, receipt.captured_at, EXTRACTION_VERSION, pointer,
                semantic_locator, row_json, tuple(sorted(set(limitations)))))
    issues = source_issues + ([] if observations else ["DILUTED_EPS_UNAVAILABLE"])
    return Extraction(EXTRACTION_VERSION, receipt.receipt_id,
                      tuple(sorted(observations, key=lambda r: (r.semantic_id, r.source_locator))),
                      tuple(sorted(issues)))


def _date(value):
    if value is None:
        return None
    try:
        result = date.fromisoformat(value)
        return result if result.isoformat() == value else None
    except ValueError:
        return None


def assess_candidate(observation):
    require(type(observation) is DilutedEPSObservation, "Extracted observation required")
    reasons = list(observation.metadata_limitations)
    annual = observation.form in ("10-K", "10-K/A") and observation.fp == "FY"
    if not annual:
        reasons.append("NOT_ANNUAL_FORM_CANDIDATE")
    start, end, filed = (_date(v) for v in (observation.start, observation.end, observation.filed))
    for name, original, parsed in (("START", observation.start, start), ("END", observation.end, end),
                                   ("FILED", observation.filed, filed)):
        if original is not None and parsed is None:
            reasons.append("INVALID_" + name)
    duration = (end - start).days + 1 if start is not None and end is not None else None
    supported = duration in (365, 366)
    if duration is not None and not supported:
        reasons.append("UNSUPPORTED_BY_CURRENT_PR4B1_PERIOD_CONTRACT")
    if start and end and start > end:
        reasons.append("REVERSED_PERIOD")
    if end and filed and end > filed:
        reasons.append("PERIOD_END_AFTER_FILED_DATE")
    if filed and filed > date.fromisoformat(observation.captured_at[:10]):
        reasons.append("FILED_DATE_AFTER_CAPTURE_UTC_DATE")
    positive = observation.value is not None and observation.value > 0
    if observation.value is not None and not positive:
        reasons.append("NOT_USABLE_BY_CURRENT_POSITIVE_EPS_ROUTE")
    return CandidateAssessment(observation.observation_id, annual, duration, supported, positive,
                               "ANNUAL_DILUTED_EPS_CANDIDATE" if not reasons else "LIMITED_SOURCE_OBSERVATION",
                               tuple(sorted(set(reasons))))


def _ambiguities(observations):
    periods = {}
    for observation in observations:
        if _date(observation.start) and _date(observation.end):
            periods.setdefault((observation.start, observation.end), []).append(observation)
    result = []
    for (start, end), rows in sorted(periods.items()):
        kinds = set()
        if len({r.unit for r in rows}) > 1:
            kinds.add("MULTIPLE_UNITS_UNRESOLVED")
        if len({r.accn for r in rows}) > 1:
            kinds.add("MULTIPLE_FILING_VERSIONS_UNRESOLVED")
        if len({r.semantic_id for r in rows}) > 1:
            kinds.add("MULTIPLE_PERIOD_OBSERVATIONS_UNRESOLVED")
        by_claim = {}
        by_unit = {}
        for row in rows:
            by_unit.setdefault(row.unit, set()).add(row.value)
            # Entire preserved context (including unknown extension dimensions),
            # excluding only value, defines the claimed source-fact identity.
            context = json.loads(row.row_json, parse_float=Decimal)
            if row.accn and type(context) is dict:
                context.pop("val", None)
                claim = _identity({"unit": row.unit, "context": context})
                by_claim.setdefault(claim, set()).add(row.value)
        if any(len(values) > 1 for values in by_unit.values()):
            kinds.add("COMPETING_PERIOD_VALUES_UNRESOLVED")
        if any(len(values) > 1 for values in by_claim.values()):
            kinds.add("SEMANTIC_IDENTITY_COLLISION")
        ids = tuple(sorted(r.observation_id for r in rows))
        result.extend(Ambiguity(kind, start, end, ids) for kind in sorted(kinds))
    return tuple(result)


def inspect_archive(archive, *, cik, cutoff):
    require(type(archive) is SecArchive, "SecArchive required")
    view = archive.captures_as_of(cik=cik, cutoff=cutoff)
    extractions = tuple(extract_diluted_eps(archive.read_object(receipt), receipt) for receipt in view.receipts)
    observations = tuple(row for extraction in extractions for row in extraction.observations)
    assessments = tuple(assess_candidate(row) for row in observations)
    ambiguities = _ambiguities(observations)
    status = "UNAVAILABLE" if not observations else "AMBIGUOUS" if ambiguities else "UPSTREAM_EVIDENCE_ONLY"
    return ArchiveInspection(INSPECTION_VERSION, view, extractions, assessments, ambiguities, status)
