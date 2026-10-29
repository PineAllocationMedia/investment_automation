"""Source-neutral provenance and conflict ledger for supplied Investment Research facts.

No browser, source authentication, financial model or storage. Inputs/outputs
may contain private research; never publish the output to ordinary GitHub.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping
from urllib.parse import urlsplit

RIGHTS = frozenset({"PERMITTED", "UNCERTAIN", "RESTRICTED"})
STATUSES = frozenset({"VERIFIED", "INDICATIVE", "CONFLICTED", "MISSING"})
KINDS = frozenset({"ISSUER_OR_REGULATOR", "SECONDARY", "USER_SUPPLIED", "ASSUMPTION"})
CLASSES = frozenset({"SOURCE_FACT", "THIRD_PARTY_ESTIMATE", "PAM_ASSUMPTION"})
KEYS = ("economic_issuer", "instrument", "metric", "period_start", "period_end",
        "currency", "unit", "definition_basis", "consolidation")


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field}: nonempty text required")
    return value.strip()


def _date(value: Any, field: str) -> date:
    try:
        s = _text(value, field)
        d = date.fromisoformat(s)
    except ValueError as exc:
        raise ValueError(f"{field}: invalid ISO date") from exc
    if d.isoformat() != s:
        raise ValueError(f"{field}: canonical YYYY-MM-DD required")
    return d


def _choice(value: Any, choices: frozenset[str], field: str) -> str:
    s = _text(value, field)
    if s not in choices:
        raise ValueError(f"{field}: unsupported status")
    return s


def _value(value: Any) -> Decimal | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError("value: explicit decimal string or null required")
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("value: invalid decimal") from exc
    if not number.is_finite():
        raise ValueError("value: finite decimal required")
    return number


def _https_locator(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parts = urlsplit(value)
        return (parts.scheme == "https" and bool(parts.hostname)
                and not parts.username and not parts.password)
    except ValueError:
        # Invalid URL syntax qualifies the observation, rather than rejecting
        # the entire multi-source research case.
        return False


def assemble_source_fusion(
    *, analysis_id: str, analysis_as_of: str,
    observations: list[Mapping[str, Any]],
) -> dict[str, Any]:
    """Assemble S/F records and source disagreements, without choosing a winner.

    Each observation has a unique observation_id and a fact_id from the original
    IR capsule. The return value is PRIVATE and is never decision-grade proof.
    """
    aid = _text(analysis_id, "analysis_id")
    cutoff = _date(analysis_as_of, "analysis_as_of")
    if not isinstance(observations, list):
        raise ValueError("observations: list required")
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for i, raw in enumerate(observations):
        if not isinstance(raw, Mapping):
            raise ValueError(f"observations[{i}]: mapping required")
        oid = _text(raw.get("observation_id"), "observation_id")
        if oid in seen:
            raise ValueError("DUPLICATE_OBSERVATION_ID")
        seen.add(oid)
        fact_id = _text(raw.get("fact_id"), "fact_id")
        source_id = _text(raw.get("source_id"), "source_id")
        fields = {name: _text(raw.get(name), name) for name in KEYS}
        start, end = _date(fields["period_start"], "period_start"), _date(fields["period_end"], "period_end")
        if end < start:
            raise ValueError("REVERSED_FINANCIAL_PERIOD")
        seen_date = _date(raw.get("observed_at"), "observed_at")
        published = raw.get("published_at")
        pub_date = _date(published, "published_at") if published is not None else None
        checked = raw.get("original_checked_at")
        checked_date = _date(checked, "original_checked_at") if checked is not None else None
        kind = _choice(raw.get("source_kind"), KINDS, "source_kind")
        rights = _choice(raw.get("rights_status"), RIGHTS, "rights_status")
        label = _choice(raw.get("verification_status"), STATUSES, "verification_status")
        classification = _choice(raw.get("classification"), CLASSES, "classification")
        number = _value(raw.get("value"))
        reasons = []
        if start > cutoff or end > cutoff:
            reasons.append("FINANCIAL_PERIOD_AFTER_CUTOFF")
        # A completed issuer SOURCE_FACT cannot have been observed before
        # the reported period ended. Forecasts and analyst assumptions are
        # different classes and must not be silently reclassified as facts.
        if classification == "SOURCE_FACT" and end > seen_date:
            reasons.append("FINANCIAL_PERIOD_END_AFTER_OBSERVATION")
        if seen_date > cutoff:
            reasons.append("OBSERVED_AFTER_CUTOFF")
        if pub_date is not None and pub_date > cutoff:
            reasons.append("PUBLISHED_AFTER_CUTOFF")
        if pub_date is None:
            reasons.append("PUBLICATION_DATE_NOT_ESTABLISHED")
        if pub_date is not None and pub_date > seen_date:
            reasons.append("PUBLICATION_AFTER_OBSERVATION")
        if checked_date is not None and checked_date > seen_date:
            reasons.append("CHECK_AFTER_OBSERVATION")
        if checked_date is not None and pub_date is not None and checked_date < pub_date:
            reasons.append("ORIGINAL_CHECK_BEFORE_PUBLICATION")
        if checked_date is not None and checked_date > cutoff:
            reasons.append("ORIGINAL_CHECK_AFTER_CUTOFF")
        if rights == "RESTRICTED":
            reasons.append("RESTRICTED_SOURCE_USE")
        if rights == "UNCERTAIN":
            reasons.append("SOURCE_RIGHTS_UNCERTAIN")
        if label in {"MISSING", "CONFLICTED"}:
            reasons.append("REPORTED_FACT_UNRESOLVED")
        if number is None:
            reasons.append("VALUE_NOT_SUPPLIED")
        if classification == "PAM_ASSUMPTION" and kind != "ASSUMPTION":
            reasons.append("ASSUMPTION_SOURCE_TYPE_MISMATCH")
        if classification == "THIRD_PARTY_ESTIMATE" and kind == "ISSUER_OR_REGULATOR":
            reasons.append("ESTIMATE_SOURCE_TYPE_REVIEW")
        if (label == "VERIFIED" and (kind != "ISSUER_OR_REGULATOR" or
                                     classification != "SOURCE_FACT" or checked_date is None)):
            reasons.append("VERIFIED_REQUIRES_REPORTED_ORIGINAL_CHECK")
        locator = raw.get("source_locator")
        if kind in {"ISSUER_OR_REGULATOR", "SECONDARY"} and not _https_locator(locator):
            reasons.append("RECOVERABLE_HTTPS_SOURCE_NOT_SUPPLIED")
        if kind in {"ASSUMPTION", "USER_SUPPLIED"} and locator is not None and not isinstance(locator, str):
            raise ValueError("source_locator: string or null required")
        items.append({"observation_id": oid, "fact_id": fact_id, "source_id": source_id,
                      **fields, "value": str(number) if number is not None else None,
                      "source_kind": kind, "rights_status": rights,
                      "classification": classification,
                      "reported_verification_status": label,
                      "source_locator": locator if isinstance(locator, str) else None,
                      "observed_at": seen_date.isoformat(),
                      "published_at": pub_date.isoformat() if pub_date is not None else None,
                      "original_checked_at": checked_date.isoformat() if checked_date is not None else None,
                      "reason_codes": sorted(set(reasons)),
                      "independent_source_authentication": "NOT_PERFORMED"})
    groups: dict[tuple[str, ...], list[dict[str, Any]]] = {}
    for item in items:
        groups.setdefault(tuple(item[key] for key in KEYS), []).append(item)
    conflicts = []
    for group in groups.values():
        numbers = {Decimal(x["value"]) for x in group if x["value"] is not None}
        # Canonical decimal values make 10 and 10.00 equivalent.
        if len(numbers) > 1:
            ids = sorted(x["observation_id"] for x in group)
            conflicts.append(ids)
            for item in group:
                item["reason_codes"] = sorted(set(item["reason_codes"] + ["SAME_BASIS_VALUE_CONFLICT"]))
    # Changed accounting definitions are noncomparable, NOT a source conflict.
    scopes: dict[tuple[str, ...], list[dict[str, Any]]] = {}
    for item in items:
        scoped_key = tuple(item[x] for x in KEYS if x != "definition_basis")
        scopes.setdefault(scoped_key, []).append(item)
    noncomparables = [sorted(x["observation_id"] for x in group)
                      for group in scopes.values() if len({x["definition_basis"] for x in group}) > 1]
    for item in items:
        codes = item["reason_codes"]
        item["claim_use_status"] = ("UNAVAILABLE" if any(x in codes for x in (
            "RESTRICTED_SOURCE_USE", "FINANCIAL_PERIOD_AFTER_CUTOFF",
            "OBSERVED_AFTER_CUTOFF", "PUBLISHED_AFTER_CUTOFF", "ORIGINAL_CHECK_AFTER_CUTOFF",
            "PUBLICATION_AFTER_OBSERVATION", "CHECK_AFTER_OBSERVATION",
            "ORIGINAL_CHECK_BEFORE_PUBLICATION",
            "FINANCIAL_PERIOD_END_AFTER_OBSERVATION"))
            else "CONFLICTED" if "SAME_BASIS_VALUE_CONFLICT" in codes else
            "INCOMPLETE" if codes or item["reported_verification_status"] in {"MISSING", "CONFLICTED"}
            else "CALLER_REPORTED_ONLY")
    result = {
        "status": "PRIVATE_SOURCE_ANNEX_PREPARED_NOT_CERTIFIED",
        "analysis_id": aid, "analysis_as_of": analysis_as_of,
        "observations_private": items,
        "conflict_observation_id_groups": sorted(conflicts),
        "noncomparable_basis_groups": sorted(noncomparables),
        "observation_count": len(items),
        "unresolved_count": sum(x["claim_use_status"] != "CALLER_REPORTED_ONLY" for x in items),
        "source_authentication": "NOT_PERFORMED_BY_CODE",
        "pit_authority": "NOT_ESTABLISHED_BY_DATES_ALONE",
        "source_rights_authority": "NOT_GRANTED_BY_CODE",
        "public_memory_write": "NONE", "trading_authority": "NONE",
    }
    return result
