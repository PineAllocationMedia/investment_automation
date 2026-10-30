"""Bounded read-only Blossom profile reference, NEVER a private portfolio ledger.

Accepts an explicit human-carried structured Work observation. This module does
not browse, authenticate sources, infer ownership, construct ETF look-through,
measure correlations, allocate capital, store anything or trade.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import re
from typing import Any, Mapping

HOST_VISIBILITY = frozenset({"SIGNED_IN_VISIBILITY_ONLY", "ANONYMOUS_PUBLIC_CONFIRMED", "UNKNOWN"})
COVERAGE_KEYS = frozenset({
    "all_rows_visible", "other_group_expanded_or_absent", "cash_visible",
    "weights_comparable", "account_filter_visible", "sync_date_visible",
})
FIELDS = frozenset({
    "status", "analysis_id", "analysis_as_of", "observation_as_of", "captured_at",
    "visibility_context", "visible_scope", "account_ownership", "positions_visible",
    "coverage", "displayed_weight_sum_pct", "unknowns",
})
ROW_FIELDS = frozenset({"security_id", "weight_pct", "value", "currency", "visibility"})
TABLE_FIELDS = (FIELDS - {"positions_visible", "displayed_weight_sum_pct"}) | {"positions_table"}
TABLE_HEADER_LEFT = frozenset({"position affichée", "position", "security", "holding"})
TABLE_HEADER_RIGHT = frozenset({"poids affiché", "poids", "weight", "displayed weight"})

TICKER = re.compile(r"[A-Za-z0-9][A-Za-z0-9.:-]{0,31}\Z")
CASE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,89}\Z")


def _text(v: Any, label: str, limit: int = 120) -> str:
    if not isinstance(v, str) or not v.strip() or len(v.strip()) > limit:
        raise ValueError(f"{label}: nonempty bounded text required")
    if any(ord(ch) < 32 for ch in v):
        raise ValueError(f"{label}: control character rejected")
    return v.strip()


def _date(v: Any, label: str, *, unknown: bool = False) -> str:
    if unknown and v == "UNKNOWN":
        return v
    value = _text(v, label, 10)
    try:
        d = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{label}: ISO date required") from exc
    if d.isoformat() != value:
        raise ValueError(f"{label}: canonical date required")
    return value


def _capture_day(raw: Any, observed_on: str, cutoff: str) -> str:
    """Separate real screenshot capture date from the holdings' effective date.

    This checks reported metadata only. A later capture cannot update holdings
    or turn a visible public profile into owned private positions.
    """
    if raw == "UNKNOWN":
        return "UNKNOWN"
    timestamp = _text(raw, "captured_at", 40)
    try:
        moment = datetime.fromisoformat(timestamp)
        if moment.utcoffset() is None:
            raise ValueError
        captured_on = moment.date().isoformat()
        if captured_on > cutoff or (
                observed_on != "UNKNOWN" and captured_on < observed_on):
            raise ValueError
    except ValueError as exc:
        raise ValueError("PUBLIC_REFERENCE_CAPTURE_TIME_INCONSISTENT") from exc
    return captured_on


def _decimal(v: Any, label: str, *, upper: Decimal | None = None) -> Decimal:
    if not isinstance(v, str) or not v.strip():
        raise ValueError(f"{label}: exact decimal string required")
    try:
        d = Decimal(v)
    except InvalidOperation as exc:
        raise ValueError(f"{label}: invalid decimal") from exc
    if (not d.is_finite() or d < 0 or d.as_tuple().exponent < -2
            or (upper is not None and d > upper) or d.adjusted() > 14):
        raise ValueError(f"{label}: unsupported amount or precision")
    return d


def prepare_public_portfolio_reference(
    packet: Mapping[str, Any], *, analysis_id: str, analysis_as_of: str
) -> dict[str, Any]:
    """Structural public-reference parsing, not a source/ownership validation."""
    if not isinstance(packet, Mapping) or set(packet) != FIELDS:
        raise ValueError("PUBLIC_REFERENCE_EXACT_SCHEMA_REQUIRED")
    aid = _text(analysis_id, "request.analysis_id", 90)
    if not CASE_ID.fullmatch(aid):
        raise ValueError("PUBLIC_REFERENCE_CASE_ID_UNSAFE")
    cutoff = _date(analysis_as_of, "request.as_of")
    if (packet["status"] != "PUBLIC_REFERENCE_ONLY"
            or packet["account_ownership"] != "NOT_ASSUMED_USER"):
        raise ValueError("PUBLIC_REFERENCE_MUST_NOT_CLAIM_PRIVATE_OWNERSHIP")
    if packet["analysis_id"] != aid or packet["analysis_as_of"] != cutoff:
        raise ValueError("PUBLIC_REFERENCE_ID_OR_CUTOFF_MISMATCH")
    visible_on = _date(packet["observation_as_of"], "observation_as_of", unknown=True)
    if visible_on != "UNKNOWN" and visible_on > cutoff:
        raise ValueError("PUBLIC_REFERENCE_AFTER_ANALYSIS_CUTOFF")
    captured = packet["captured_at"]
    _capture_day(captured, visible_on, cutoff)
    visible_mode = packet["visibility_context"]
    if visible_mode not in HOST_VISIBILITY:
        raise ValueError("PUBLIC_REFERENCE_VISIBILITY_MODE_UNSUPPORTED")
    # Read scope only to validate length; raw account description is NOT
    # propagated to reports, IR handoffs or institutional memory.
    _text(packet["visible_scope"], "visible_scope", 160)
    coverage = packet["coverage"]
    if (not isinstance(coverage, Mapping) or set(coverage) != COVERAGE_KEYS
            or any(type(v) is not bool for v in coverage.values())):
        raise ValueError("PUBLIC_REFERENCE_COVERAGE_FLAGS_REQUIRED")
    raw = packet["positions_visible"]
    if not isinstance(raw, list) or not 1 <= len(raw) <= 60:
        raise ValueError("PUBLIC_REFERENCE_NONEMPTY_BOUNDED_POSITIONS_REQUIRED")
    seen: set[str] = set()
    positions: list[dict[str, str | None]] = []
    total = Decimal("0")
    complete_weights = True
    for idx, row in enumerate(raw):
        if not isinstance(row, Mapping) or set(row) != ROW_FIELDS:
            raise ValueError("PUBLIC_REFERENCE_POSITION_SCHEMA_INVALID")
        ticker = _text(row["security_id"], f"positions[{idx}].security_id", 32)
        if not TICKER.fullmatch(ticker) or ticker in seen:
            raise ValueError("PUBLIC_REFERENCE_DUPLICATE_OR_INVALID_SECURITY")
        seen.add(ticker)
        if row["visibility"] not in {"VISIBLE", "UNCERTAIN"}:
            raise ValueError("PUBLIC_REFERENCE_VISIBILITY_FIELD_INVALID")
        weight = row["weight_pct"]
        if weight is None:
            complete_weights = False
        else:
            value = _decimal(weight, f"{ticker}.weight_pct", upper=Decimal("100"))
            total += value
        # No account base currency, market value or cost inference is permitted.
        if row["value"] is not None:
            _decimal(row["value"], f"{ticker}.value")
        if row["currency"] is not None:
            curr = _text(row["currency"], f"{ticker}.currency", 3)
            if len(curr) != 3 or not curr.isalpha() or curr != curr.upper():
                raise ValueError("PUBLIC_REFERENCE_CURRENCY_INVALID")
        positions.append({"security_id": ticker, "weight_pct": weight,
                          "visibility": row["visibility"]})
    if not complete_weights and coverage["weights_comparable"]:
        raise ValueError("PUBLIC_REFERENCE_WEIGHTS_MISSING_BUT_COMPARABLE")
    supplied_sum = packet["displayed_weight_sum_pct"]
    if supplied_sum is not None:
        if not complete_weights or _decimal(supplied_sum, "displayed_weight_sum_pct") != total:
            raise ValueError("PUBLIC_REFERENCE_DISPLAY_SUM_MISMATCH")
    unknowns = packet["unknowns"]
    if (not isinstance(unknowns, list) or len(unknowns) > 12
            or any(not isinstance(x, str) or not x.strip() or len(x) > 160 for x in unknowns)):
        raise ValueError("PUBLIC_REFERENCE_BOUNDED_UNKNOWN_LIST_REQUIRED")
    reasons = []
    if visible_mode != "ANONYMOUS_PUBLIC_CONFIRMED":
        reasons.append("ANONYMOUS_ACCESS_NOT_ESTABLISHED")
    for name in sorted(COVERAGE_KEYS):
        if not coverage[name]:
            reasons.append(name.upper() + "_NOT_CONFIRMED")
    if visible_on == "UNKNOWN":
        reasons.append("OBSERVATION_DATE_UNKNOWN")
    if not complete_weights:
        reasons.append("ONE_OR_MORE_WEIGHTS_NOT_VISIBLE")
    # These are relative to reported display ONLY, never private portfolio
    # weights. Unverified ETF holdings are not looked through or allocated.
    ordered = sorted(
        (p for p in positions if p["weight_pct"] is not None),
        key=lambda p: (-Decimal(p["weight_pct"]), p["security_id"]))
    top5 = sum((Decimal(p["weight_pct"]) for p in ordered[:5]), Decimal("0"))
    return {
        "status": "PUBLIC_REFERENCE_DESCRIPTIVE_ONLY", "analysis_id": aid,
        "analysis_as_of": cutoff, "observation_as_of": visible_on,
        "captured_at": captured,
        "visibility_context": visible_mode, "position_count": len(positions),
        "positions_private": positions, "displayed_weight_sum_pct": (
            f"{total:.2f}" if complete_weights else None),
        "top_five_displayed_points": (f"{top5:.2f}" if ordered else None),
        "top_five_security_ids": [p["security_id"] for p in ordered[:5]],
        "coverage": dict(coverage), "missing_or_qualified": reasons,
        "additional_unknown_count": len(unknowns),
        "source_authentication": "NOT_PERFORMED",
        "ownership_authority": "NOT_ESTABLISHED",
        "portfolio_room_status": "NOT_APPLICABLE_PUBLIC_REFERENCE",
        "private_holdings_import": "NONE", "allocation_authority": "NONE",
        "trading_authority": "NONE", "source_access": "CALLER_REPORTED",
        "project_invocation": "NONE", "storage": "NONE",
    }


def prepare_public_reference_from_work_table(
    packet: Mapping[str, Any], *, analysis_id: str, analysis_as_of: str
) -> dict[str, Any]:
    """Convert ONLY a two-column Work Markdown table to the existing reference.

    No natural-language extraction, ownership guessing, portfolio optimization
    or replacement of the existing strict public-reference validator.
    """
    if not isinstance(packet, Mapping) or set(packet) != TABLE_FIELDS:
        raise ValueError("PUBLIC_REFERENCE_TABLE_EXACT_SCHEMA_REQUIRED")
    raw = packet["positions_table"]
    if not isinstance(raw, str) or len(raw) > 20000:
        raise ValueError("PUBLIC_REFERENCE_TABLE_BOUNDED_TEXT_REQUIRED")
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    if not 3 <= len(lines) <= 62:
        raise ValueError("PUBLIC_REFERENCE_TABLE_ROW_COUNT_INVALID")

    def split_line(line: str) -> tuple[str, str]:
        if not line.startswith("|") or not line.endswith("|"):
            raise ValueError("PUBLIC_REFERENCE_TABLE_TWO_COLUMNS_REQUIRED")
        cells = [x.strip() for x in line[1:-1].split("|")]
        if len(cells) != 2 or not all(cells):
            raise ValueError("PUBLIC_REFERENCE_TABLE_TWO_COLUMNS_REQUIRED")
        return cells[0], cells[1]

    left, right = split_line(lines[0])
    if left.lower() not in TABLE_HEADER_LEFT or right.lower() not in TABLE_HEADER_RIGHT:
        raise ValueError("PUBLIC_REFERENCE_TABLE_HEADER_UNRECOGNIZED")
    sep_left, sep_right = split_line(lines[1])
    if (not re.fullmatch(r":?-{3,}:?", sep_left)
            or not re.fullmatch(r":?-{3,}:?", sep_right)):
        raise ValueError("PUBLIC_REFERENCE_TABLE_SEPARATOR_REQUIRED")
    positions: list[dict[str, str | None]] = []
    weight_sum = Decimal("0")
    complete = True
    for index, line in enumerate(lines[2:]):
        security, raw_weight = split_line(line)
        # A descriptive label after the ticker is permitted but discarded.
        # The ticker is the ONLY source identity retained downstream.
        match = re.fullmatch(
            r"([A-Za-z0-9][A-Za-z0-9.:-]{0,31})(?:\s+[—–-]\s+[^|]{1,120})?",
            security,
        )
        if match is None:
            raise ValueError("PUBLIC_REFERENCE_TABLE_SECURITY_ID_INVALID")
        ticker = match.group(1)
        if raw_weight in {"UNKNOWN", "NOT_VISIBLE", "—", "-"}:
            weight = None
            complete = False
        else:
            number = re.fullmatch(r"(\d+(?:[.,]\d{1,2})?)\s*%", raw_weight)
            if number is None:
                raise ValueError("PUBLIC_REFERENCE_TABLE_WEIGHT_FORMAT_INVALID")
            weight = number.group(1).replace(",", ".")
            weight_sum += _decimal(
                weight, f"work_table[{index}].weight_pct", upper=Decimal("100"))
        positions.append({
            "security_id": ticker, "weight_pct": weight,
            "value": None, "currency": None, "visibility": (
                "VISIBLE" if weight is not None else "UNCERTAIN"),
        })
    strict = {key: value for key, value in packet.items() if key != "positions_table"}
    strict["positions_visible"] = positions
    strict["displayed_weight_sum_pct"] = (
        f"{weight_sum:.2f}" if complete else None)
    # This existing validator enforces all remaining identity/date/coverage/
    # ownership/public-private protections on the converted packet.
    return prepare_public_portfolio_reference(
        strict, analysis_id=analysis_id, analysis_as_of=analysis_as_of)


def render_public_portfolio_reference(result: Mapping[str, Any]) -> str:
    """Private human-readable report of *reported display*, no holdings claim."""
    if (result.get("status") != "PUBLIC_REFERENCE_DESCRIPTIVE_ONLY"
            or result.get("private_holdings_import") != "NONE"
            or result.get("allocation_authority") != "NONE"
            or result.get("source_authentication") != "NOT_PERFORMED"):
        raise ValueError("PUBLIC_REFERENCE_REPORT_AUTHORITY_INVALID")
    observation_day = _date(result.get("observation_as_of"), "observation_as_of",
                            unknown=True)
    cutoff = _date(result.get("analysis_as_of"), "analysis_as_of")
    if observation_day != "UNKNOWN" and observation_day > cutoff:
        raise ValueError("PUBLIC_REFERENCE_AFTER_ANALYSIS_CUTOFF")
    capture_day = _capture_day(result.get("captured_at"), observation_day, cutoff)
    capture_label = (
        "Capture timestamp UNKNOWN; observation date " + observation_day + "."
        if capture_day == "UNKNOWN" else
        "Capture recorded on " + capture_day +
        "; effective displayed holdings date " + observation_day +
        ("; " + str((date.fromisoformat(capture_day) -
                       date.fromisoformat(observation_day)).days) +
         " calendar day(s) after the underlying observation."
         if observation_day != "UNKNOWN" else
         "; capture time does NOT establish a holdings sync date.")
    )
    rows = [
        "## Blossom Portfolio — observed profile reference only",
        f"Analysis: {result['analysis_id']} / {result['analysis_as_of']}; "
        f"observation: {result['observation_as_of']}; "
        f"visible positions reported: {result['position_count']}.",
        capture_label,
        "Reference classification only, not evidence of the CEO's private holdings, "
        "anonymous site access, actual account denominator or broker-verified positions.",
        "",
        "| Observed security | Displayed weight | Visibility |",
        "| --- | ---: | --- |",
    ]
    for p in result["positions_private"]:
        rows.append(f"| {p['security_id']} | "
                    f"{p['weight_pct'] + '%' if p['weight_pct'] is not None else 'UNKNOWN'}"
                    f" | {p['visibility']} |")
    rows += [
        "",
        "Sum of reported displayed line weights: "
        + (result["displayed_weight_sum_pct"] + "% (NOT renormalized)."
           if result["displayed_weight_sum_pct"] is not None else "UNKNOWN; rows incomplete."),
        "Top five visible line weights: "
        + (result["top_five_displayed_points"] + " percentage points (display-only)."
           if result["top_five_displayed_points"] is not None else "UNKNOWN."),
        "Observation limitations: " + ", ".join(result["missing_or_qualified"] or ["none reported"])
        + f"; {result['additional_unknown_count']} additional caller-reported unknown(s).",
        "No fund look-through, measured correlation, source/rights verification, "
        "Portfolio Room, personalized contribution allocation, certified Expected Return or trade.",
        "Next human check: verify displayed account scope, holdings synchronization "
        "date and source/ETF composition before treating apparent overlap as measured exposure.",
    ]
    return "\n".join(rows)
