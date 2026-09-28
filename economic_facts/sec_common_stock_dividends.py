"""Lossless extraction of two reviewed SEC common-stock dividend concepts.

This module preserves Companyfacts source claims. It does not qualify a payer,
nonpayer, selected security/class, share basis, or Expected Return input.
"""
from dataclasses import dataclass
from decimal import Decimal
import hashlib
import json
import re

from .sec_archive import (ArchiveError, CaptureReceipt, digest, reject_constant,
                          require, unique_pairs)

EXTRACTION_VERSION = "2026-09-28-sec-common-stock-dividends-extraction-v1"
NAMESPACE = "us-gaap"
DECLARED_CONCEPT = "CommonStockDividendsPerShareDeclared"
PAID_CONCEPT = "CommonStockDividendsPerShareCashPaid"
CONCEPTS = (DECLARED_CONCEPT, PAID_CONCEPT)
_BASE_POINTER = "/facts/us-gaap"


def _semantic_json(value):
    """Canonical JSON with exact base-ten numbers and stable mapping order."""
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
    return "{" + ",".join(
        json.dumps(key, ensure_ascii=True) + ":" + _semantic_json(value[key])
        for key in sorted(value)
    ) + "}"


def _identity(value):
    return hashlib.sha256(_semantic_json(value).encode("ascii")).hexdigest()


def _pointer_token(value):
    return value.replace("~", "~0").replace("/", "~1")


@dataclass(frozen=True, slots=True)
class CommonStockDividendObservation:
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
    accession: str | None
    frame: str | None
    source_object_hash: str
    capture_receipt_id: str
    captured_at: str
    extraction_version: str
    source_locator: str
    semantic_locator: str
    row_json: str
    metadata_limitations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CommonStockDividendExtraction:
    extraction_version: str
    receipt_id: str
    observations: tuple[CommonStockDividendObservation, ...]
    issues: tuple[str, ...]


def extract_common_stock_dividends(raw, receipt):
    """Extract all rows for exactly the two reviewed standard concepts."""
    require(type(receipt) is CaptureReceipt, "Typed receipt required")
    require(type(raw) is bytes and digest(raw) == receipt.content_sha256
            and len(raw) == receipt.byte_length, "Source bytes do not match receipt")
    try:
        source = json.loads(raw, parse_float=Decimal, object_pairs_hook=unique_pairs,
                            parse_constant=reject_constant)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ArchiveError("Invalid SEC-style JSON") from exc
    require(type(source) is dict, "Source JSON object required")

    issues = []
    source_issues = []
    source_cik = source.get("cik")
    if source_cik is None:
        source_issues.append("MISSING_SOURCE_CIK")
        issues.append("MISSING_SOURCE_CIK")
    else:
        require((type(source_cik) is int and 0 <= source_cik <= 9999999999)
                or (type(source_cik) is str and re.fullmatch(r"[0-9]{1,10}", source_cik)),
                "Invalid source CIK")
        require(str(source_cik).zfill(10) == receipt.cik, "Source/receipt CIK mismatch")

    facts = source.get("facts")
    if facts is None:
        facts = {}
    require(type(facts) is dict, "Malformed Companyfacts facts structure")
    namespace = facts.get(NAMESPACE)
    if namespace is None:
        namespace = {}
    require(type(namespace) is dict, "Malformed Companyfacts namespace structure")

    observations = []
    for concept in CONCEPTS:
        concept_observation_count = len(observations)
        concept_node = namespace.get(concept)
        if concept_node is None:
            issues.append(concept + "_UNAVAILABLE")
            continue
        require(type(concept_node) is dict, "Malformed dividend concept structure")
        units = concept_node.get("units")
        require(type(units) is dict, "Malformed dividend units structure")
        if not units:
            issues.append(concept + "_UNAVAILABLE")
        for unit in sorted(units):
            rows = units[unit]
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
                                         "concept": concept, "unit": unit, "row": raw_row})
                base = _BASE_POINTER + "/" + concept + "/units/" + _pointer_token(unit)
                pointer = base + "/" + str(index)
                semantic_locator = base + "/sha256:" + semantic_id
                observation_id = _identity({
                    "source_object_hash": receipt.content_sha256,
                    "capture_receipt_id": receipt.receipt_id,
                    "semantic_id": semantic_id,
                    "source_locator": pointer,
                    "extraction_version": EXTRACTION_VERSION,
                })
                observations.append(CommonStockDividendObservation(
                    observation_id, semantic_id, receipt.cik, NAMESPACE, concept, unit,
                    value, metadata["start"], metadata["end"], fy, metadata["fp"],
                    metadata["form"], metadata["filed"], metadata["accn"],
                    metadata["frame"], receipt.content_sha256, receipt.receipt_id,
                    receipt.captured_at, EXTRACTION_VERSION, pointer, semantic_locator,
                    row_json, tuple(sorted(set(limitations))),
                ))
        if len(observations) == concept_observation_count:
            issues.append(concept + "_UNAVAILABLE")

    return CommonStockDividendExtraction(
        EXTRACTION_VERSION,
        receipt.receipt_id,
        tuple(sorted(observations,
                     key=lambda row: (row.concept, row.semantic_id, row.source_locator))),
        tuple(sorted(set(issues))),
    )
