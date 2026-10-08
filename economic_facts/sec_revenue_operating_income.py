"""Lossless SEC Companyfacts extraction for annual revenue and operating income.

This module extracts only source observations for the two reviewed concepts. It
does not select a period, reconcile filings, calculate operating margin, or grant
analytical authority.
"""
from dataclasses import dataclass
from decimal import Decimal
import json
import re

from .sec_archive import (
    ArchiveError,
    CaptureReceipt,
    digest,
    reject_constant,
    require,
    unique_pairs,
)


EXTRACTION_VERSION = (
    "2026-10-07-sec-revenue-operating-income-extraction-v1"
)
NAMESPACE = "us-gaap"
REVENUE_CONCEPT = "RevenueFromContractWithCustomerExcludingAssessedTax"
OPERATING_INCOME_CONCEPT = "OperatingIncomeLoss"
CONCEPTS = (REVENUE_CONCEPT, OPERATING_INCOME_CONCEPT)
REVIEWED_UNIT = "USD"


def _semantic_json(value):
    """Canonical JSON with exact base-ten numeric handling."""
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


def _identity(domain, value):
    return digest((domain + "\0" + _semantic_json(value)).encode("ascii"))


def _pointer_token(value):
    return value.replace("~", "~0").replace("/", "~1")


@dataclass(frozen=True, slots=True)
class RevenueOperatingIncomeObservation:
    observation_id: str
    semantic_id: str
    source_cik: str | None
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
    source_semantics: tuple[str, ...]
    metadata_limitations: tuple[str, ...]
    accounting_basis: str = "US_GAAP"


@dataclass(frozen=True, slots=True)
class RevenueOperatingIncomeExtraction:
    extraction_version: str
    source_cik: str | None
    capture_receipt_id: str
    source_object_hash: str
    captured_at: str
    source_locator: str
    observations: tuple[RevenueOperatingIncomeObservation, ...]
    issues: tuple[str, ...]


def _metadata(row):
    limitations = []
    values = {}
    for key in ("start", "end", "fp", "form", "filed", "accn", "frame"):
        value = row.get(key)
        if value is not None and (type(value) is not str or not value.strip()):
            limitations.append("INVALID_" + key.upper())
            value = None
        if value is None and key != "frame":
            limitations.append("MISSING_" + key.upper())
        values[key] = value
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
        if not value.is_finite():
            limitations.append("NONFINITE_VALUE")
            value = None
    return values, fy, value, limitations


def extract_revenue_operating_income(raw, receipt):
    """Extract only the reviewed US-GAAP revenue and operating-income concepts."""
    require(type(receipt) is CaptureReceipt, "Typed receipt required")
    require(type(raw) is bytes, "Exact source bytes required")
    require(
        digest(raw) == receipt.content_sha256 and len(raw) == receipt.byte_length,
        "Source bytes do not match receipt",
    )
    try:
        source = json.loads(
            raw,
            parse_float=Decimal,
            object_pairs_hook=unique_pairs,
            parse_constant=reject_constant,
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ArchiveError("Invalid SEC-style JSON") from exc
    require(type(source) is dict, "Source JSON object required")

    raw_cik = source.get("cik")
    issues = []
    source_cik = None
    if raw_cik is None:
        issues.append("MISSING_SOURCE_CIK")
    else:
        require(
            (type(raw_cik) is int and 0 <= raw_cik <= 9999999999)
            or (type(raw_cik) is str and re.fullmatch(r"[0-9]{1,10}", raw_cik)),
            "Invalid source CIK",
        )
        source_cik = str(raw_cik).zfill(10)

    missing_issues = (
        "REVENUE_UNAVAILABLE",
        "OPERATING_INCOME_UNAVAILABLE",
    )
    facts = source.get("facts")
    if facts is None:
        return RevenueOperatingIncomeExtraction(
            EXTRACTION_VERSION,
            source_cik,
            receipt.receipt_id,
            receipt.content_sha256,
            receipt.captured_at,
            receipt.source_locator,
            (),
            tuple(sorted(issues + list(missing_issues))),
        )
    require(type(facts) is dict, "Malformed Companyfacts facts structure")
    namespace = facts.get(NAMESPACE)
    if namespace is None:
        return RevenueOperatingIncomeExtraction(
            EXTRACTION_VERSION,
            source_cik,
            receipt.receipt_id,
            receipt.content_sha256,
            receipt.captured_at,
            receipt.source_locator,
            (),
            tuple(sorted(issues + list(missing_issues))),
        )
    require(type(namespace) is dict, "Malformed US-GAAP facts structure")

    observations = []
    for concept in CONCEPTS:
        concept_node = namespace.get(concept)
        if concept_node is None:
            issues.append(
                "REVENUE_UNAVAILABLE"
                if concept == REVENUE_CONCEPT
                else "OPERATING_INCOME_UNAVAILABLE"
            )
            continue
        require(type(concept_node) is dict, "Malformed reviewed concept structure")
        require("units" in concept_node, "Malformed reviewed concept units structure")
        units = concept_node["units"]
        require(type(units) is dict, "Malformed reviewed concept units structure")
        if REVIEWED_UNIT not in units:
            issues.append(
                "REVENUE_EXACT_USD_UNIT_UNAVAILABLE"
                if concept == REVENUE_CONCEPT
                else "OPERATING_INCOME_EXACT_USD_UNIT_UNAVAILABLE"
            )
        base_pointer = f"/facts/{NAMESPACE}/{concept}/units"
        for unit in sorted(units):
            require(type(unit) is str, "Companyfacts unit name must be text")
            rows = units[unit]
            require(type(rows) is list, "Companyfacts unit rows must be an array")
            for index, raw_row in enumerate(rows):
                require(type(raw_row) is dict, "Companyfacts fact row must be an object")
                metadata, fy, value, limitations = _metadata(raw_row)
                if unit != REVIEWED_UNIT:
                    limitations.append("UNIT_NOT_REVIEWED_USD")
                if source_cik is None:
                    limitations.append("MISSING_SOURCE_CIK")
                row_json = _semantic_json(raw_row)
                semantic_id = _identity(
                    "revenue-operating-income-observation-semantics",
                    {
                        "source_cik": source_cik,
                        "namespace": NAMESPACE,
                        "concept": concept,
                        "unit": unit,
                        "row": raw_row,
                    },
                )
                pointer = base_pointer + "/" + _pointer_token(unit) + "/" + str(index)
                semantic_locator = (
                    base_pointer + "/" + _pointer_token(unit) + "/sha256:" + semantic_id
                )
                observation_id = _identity(
                    "revenue-operating-income-observation-evidence",
                    {
                        "semantic_id": semantic_id,
                        "source_object_hash": receipt.content_sha256,
                        "capture_receipt_id": receipt.receipt_id,
                        "source_locator": pointer,
                        "extraction_version": EXTRACTION_VERSION,
                    },
                )
                observations.append(RevenueOperatingIncomeObservation(
                    observation_id,
                    semantic_id,
                    source_cik,
                    NAMESPACE,
                    concept,
                    unit,
                    value,
                    metadata["start"],
                    metadata["end"],
                    fy,
                    metadata["fp"],
                    metadata["form"],
                    metadata["filed"],
                    metadata["accn"],
                    metadata["frame"],
                    receipt.content_sha256,
                    receipt.receipt_id,
                    receipt.captured_at,
                    EXTRACTION_VERSION,
                    pointer,
                    semantic_locator,
                    row_json,
                    ("SEC_COMPANYFACTS_PRESENTATION", "CURRENT_CAPTURE_REPLAY"),
                    tuple(sorted(set(limitations))),
                ))

    return RevenueOperatingIncomeExtraction(
        EXTRACTION_VERSION,
        source_cik,
        receipt.receipt_id,
        receipt.content_sha256,
        receipt.captured_at,
        receipt.source_locator,
        tuple(sorted(
            observations,
            key=lambda item: (item.concept, item.semantic_id, item.source_locator),
        )),
        tuple(sorted(set(issues))),
    )
