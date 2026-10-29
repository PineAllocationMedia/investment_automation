"""Private valuation quote-to-evidence alignment; never a price certification.

The quote_source_ref already supplied to M2 may identify one existing M5
observation_id. No source retrieval, market-price discovery, FX conversion,
evidence upgrade, investment ranking, storage or trade happens here.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping


def _date(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label}: canonical date required")
    try:
        result = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{label}: canonical date required") from exc
    if result.isoformat() != value:
        raise ValueError(f"{label}: canonical date required")
    return value


def _number(value: Any, label: str) -> Decimal:
    if not isinstance(value, str):
        raise ValueError(f"{label}: decimal string required")
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"{label}: decimal string required") from exc
    if not number.is_finite() or number <= 0:
        raise ValueError(f"{label}: finite positive decimal required")
    return number


def trace_valuation_quote(
    *, valuation: Mapping[str, Any], source_annex: Mapping[str, Any] | None,
    ir_research_as_of: str,
) -> dict[str, Any]:
    """Bounded structural check of the original caller-supplied quotation.

    Unknown quote identifiers are not silently replaced by another source. A
    matched but mismatched numeric quote is an error, not a cherry-picked price.
    Source quality and original availability remain for human verification.
    """
    if not isinstance(valuation, Mapping):
        raise ValueError("QUOTE_VALUATION_MAPPING_REQUIRED")
    aid, as_of = valuation.get("analysis_id"), _date(valuation.get("analysis_as_of"), "quote.as_of")
    researched = _date(ir_research_as_of, "ir_research_as_of")
    quoted = _date(valuation.get("quoted_at"), "quote.quoted_at")
    ref = valuation.get("quote_source_ref")
    if (not isinstance(aid, str) or not aid.strip()
            or not isinstance(ref, str) or not ref.strip()
            or not isinstance(valuation.get("security_id"), str) or not valuation["security_id"].strip()
            or not isinstance(valuation.get("currency"), str) or not valuation["currency"].strip()
            or quoted > as_of or researched > as_of):
        raise ValueError("QUOTE_VALUATION_ID_DATE_OR_BASIS_MISMATCH")
    price = _number(valuation.get("price_per_share"), "price_per_share")
    common = {
        "status": "PRIVATE_QUOTE_SOURCE_TRACE_NOT_CERTIFIED",
        "analysis_id": aid, "analysis_as_of": as_of,
        "quote_reference_private": ref,
        "source_authentication": "NOT_PERFORMED",
        "original_market_price_verification": "NOT_ESTABLISHED",
        "market_price_or_fx_authority": "NONE",
        "writes": "NONE",
    }
    if source_annex is None:
        return {**common, "review_stage": "EVIDENCE_RESOLUTION",
                "reason_codes": ["SOURCE_ANNEX_NOT_SUPPLIED"],
                "matched_observation_id_private": None}
    if (not isinstance(source_annex, Mapping)
            or source_annex.get("status") != "PRIVATE_SOURCE_ANNEX_PREPARED_NOT_CERTIFIED"
            or source_annex.get("analysis_id") != aid
            or source_annex.get("analysis_as_of") != as_of
            or source_annex.get("source_authentication") != "NOT_PERFORMED_BY_CODE"
            or source_annex.get("source_rights_authority") != "NOT_GRANTED_BY_CODE"):
        raise ValueError("QUOTE_SOURCE_ANNEX_AUTHORITY_OR_MANDATE_MISMATCH")
    observations = source_annex.get("observations_private")
    if not isinstance(observations, list):
        raise ValueError("QUOTE_SOURCE_OBSERVATIONS_REQUIRED")
    matches = [x for x in observations if isinstance(x, Mapping) and x.get("observation_id") == ref]
    if len(matches) > 1:
        raise ValueError("QUOTE_DUPLICATE_SOURCE_OBSERVATION")
    if not matches:
        return {**common, "review_stage": "EVIDENCE_RESOLUTION",
                "reason_codes": ["QUOTE_OBSERVATION_NOT_LINKED"],
                "matched_observation_id_private": None}
    row = matches[0]
    # The quote's exact security, currency, measurement and timestamp are
    # essential: a GAAP EPS observation or a different listing is not a quote.
    if (row.get("instrument") != valuation["security_id"]
            or row.get("currency") != valuation["currency"].upper()
            or row.get("metric") != "MARKET_PRICE_PER_SHARE"
            or row.get("unit") != "PER_SHARE"
            or row.get("period_start") != quoted
            or row.get("period_end") != quoted):
        raise ValueError("QUOTE_IDENTITY_CURRENCY_UNIT_OR_DATE_MISMATCH")
    if row.get("value") is not None and _number(row["value"], "observation.price") != price:
        raise ValueError("QUOTE_PRICE_DISAGREES_WITH_LINKED_OBSERVATION")
    if _date(row.get("observed_at"), "quote.observed_at") > researched:
        raise ValueError("QUOTE_OBSERVATION_AFTER_IR_RESEARCH_AS_OF")
    raw_codes = row.get("reason_codes")
    if not isinstance(raw_codes, list) or any(not isinstance(code, str) or not code for code in raw_codes):
        raise ValueError("QUOTE_SOURCE_REASON_CODES_INVALID")
    reasons = list(raw_codes)
    if row.get("value") is None:
        reasons.append("QUOTE_OBSERVATION_VALUE_MISSING")
    if (row.get("claim_use_status") != "CALLER_REPORTED_ONLY"
            or row.get("rights_status") != "PERMITTED"
            or row.get("classification") != "SOURCE_FACT"
            or row.get("source_kind") not in {"ISSUER_OR_REGULATOR", "SECONDARY"}):
        reasons.append("QUOTE_SOURCE_NOT_STRUCTURALLY_USABLE")
    reasons = sorted(set(reasons))
    return {
        **common,
        "review_stage": "EVIDENCE_RESOLUTION" if reasons else "HUMAN_QUOTE_REVIEW_ONLY",
        "reason_codes": reasons,
        "matched_observation_id_private": ref,
    }
