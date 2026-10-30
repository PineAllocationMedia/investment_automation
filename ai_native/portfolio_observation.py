"""Private scoped portfolio observation ledger from *supplied transcriptions*.

No image parsing, Blossom access, brokerage authentication, market data or trades.
Field-level statuses describe what the caller claims was visible, NOT verified
broker truth. A derived weight is never itself evidence of Portfolio Room.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_DOWN
import re
from typing import Any, Mapping

VISIBILITY = frozenset({"VERIFIED_VISIBLE", "UNCERTAIN", "NOT_VISIBLE"})
SOURCES = frozenset({"PRIVATE_SCREENSHOT_TRANSCRIPTION", "PRIVATE_EXPORT_TRANSCRIPTION",
                     "PRIVATE_USER_TABLE", "AUTHORIZED_BLOSSOM_TRANSCRIPTION",
                     "PUBLIC_BLOSSOM_REFERENCE"})
REQUIRED_FIELD_STATUSES = ("security_id", "market_value_base", "currency", "account_scope")
CENTS = Decimal("0.01")
HUNDRED = Decimal("100")
# These literal source placeholders do not name a real account or security,
# even when a caller reports their field status as VERIFIED_VISIBLE.
IDENTITY_PLACEHOLDERS = frozenset({
    "UNKNOWN", "NOT_VISIBLE", "NOT_SUPPLIED", "N/A", "TBD", "UNCERTAIN",
})


def identity_is_placeholder(value: Any) -> bool:
    return isinstance(value, str) and value.strip().upper() in IDENTITY_PLACEHOLDERS


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field}: nonempty string required")
    return value.strip()


def _date(value: Any, field: str) -> date:
    text = _text(value, field)
    try:
        d = date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{field}: ISO date required") from exc
    if d.isoformat() != text:
        raise ValueError(f"{field}: canonical ISO date required")
    return d


def _money(value: Any, field: str) -> Decimal:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field}: explicit decimal string required")
    try:
        d = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"{field}: invalid decimal") from exc
    if not d.is_finite() or d < 0 or d != d.quantize(CENTS):
        raise ValueError(f"{field}: finite nonnegative amount with <=2 decimals")
    return d


def _visibility(raw: Any, field: str) -> str:
    value = _text(raw, field)
    if value not in VISIBILITY:
        raise ValueError(f"{field}: invalid visibility status")
    return value


def _displayed_pct(raw: Any, field: str) -> Decimal:
    """Exact UI percentage, kept separate from amount-derived portfolio weights."""
    if (not isinstance(raw, str) or not re.fullmatch(
            r"(?:0|[1-9][0-9]{0,2})(?:\.[0-9]{1,2})?", raw)):
        raise ValueError(f"{field}: display percentage must be a decimal string with <=2 places")
    try:
        amount = Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError(f"{field}: invalid display percentage") from exc
    if not amount.is_finite() or not 0 <= amount <= 100:
        raise ValueError(f"{field}: percentage outside 0..100")
    return amount


def prepare_observation_ledger(
    *,
    analysis_id: str,
    observed_on: str,
    analysis_as_of: str,
    captured_at: str,
    source_type: str,
    private_scope: bool,
    source_access_confirmed_by_caller: bool,
    account_scope: str,
    currency: str,
    scope_complete: bool,
    cash_base: str | None,
    cash_visibility: str,
    same_currency_basis_confirmed_by_caller: bool,
    positions: list[Mapping[str, Any]],
) -> dict[str, Any]:
    """Create PRIVATE P-ledger, with weights only for an explicitly complete scope.

    The caller's visibility/coverage assertions are NOT independently checked.
    An UNKNOWN capture timestamp cannot support computed weights.
    """
    aid = _text(analysis_id, "analysis_id")
    observed = _date(observed_on, "observed_on")
    cutoff = _date(analysis_as_of, "analysis_as_of")
    if observed > cutoff:
        raise ValueError("OBSERVATION_NEWER_THAN_ANALYSIS_CUTOFF")
    src = _text(source_type, "source_type")
    if src not in SOURCES:
        raise ValueError("unsupported source_type")
    for label, val in (("private_scope", private_scope),
                       ("source_access_confirmed_by_caller", source_access_confirmed_by_caller),
                       ("scope_complete", scope_complete),
                       ("same_currency_basis_confirmed_by_caller", same_currency_basis_confirmed_by_caller)):
        if type(val) is not bool:
            raise ValueError(f"{label}: explicit boolean required")
    if (src == "PUBLIC_BLOSSOM_REFERENCE") == private_scope:
        raise ValueError("PUBLIC_PRIVATE_SOURCE_SCOPE_MISMATCH")
    if src == "AUTHORIZED_BLOSSOM_TRANSCRIPTION" and not source_access_confirmed_by_caller:
        raise ValueError("BLOSSOM_ACCESS_NOT_CONFIRMED")
    account = _text(account_scope, "account_scope")
    curr = _text(currency, "currency").upper()
    # User-provided missing-value tokens must NEVER become cash-denominated
    # portfolio weights just because they happen to be three ASCII letters.
    # Preserve the observational record but canonicalize these sentinels to
    # UNKNOWN; same-currency caller assertions cannot override this boundary.
    if curr in {"UNK", "XXX", "XTS", "TBD"}:
        curr = "UNKNOWN"
    if curr != "UNKNOWN" and (
            len(curr) != 3 or not curr.isascii() or not curr.isalpha()):
        raise ValueError("currency: three-letter account currency or UNKNOWN required")
    reasons: list[str] = []
    if private_scope and identity_is_placeholder(account):
        reasons.append("ACCOUNT_SCOPE_UNIDENTIFIED")
    if curr == "UNKNOWN":
        reasons.append("ACCOUNT_CURRENCY_UNKNOWN")
    if captured_at == "UNKNOWN":
        reasons.append("CAPTURE_TIME_UNKNOWN")
    else:
        try:
            stamp = datetime.fromisoformat(_text(captured_at, "captured_at"))
            if stamp.utcoffset() is None:
                raise ValueError("captured_at: timezone-aware ISO datetime required")
            # A screenshot captured later may show a prior-dated portfolio
            # snapshot. Admit its *observed-on* state without silently
            # upgrading it to the capture date or analysis cutoff.
            if not observed <= stamp.date() <= cutoff:
                raise ValueError("CAPTURE_DATE_OUTSIDE_OBSERVATION_AND_CUTOFF")
        except ValueError as exc:
            if str(exc) == "CAPTURE_DATE_OUTSIDE_OBSERVATION_AND_CUTOFF":
                raise
            raise ValueError("captured_at: timezone-aware ISO datetime required") from exc
    if not source_access_confirmed_by_caller:
        reasons.append("SOURCE_ACCESS_NOT_CONFIRMED_BY_CALLER")
    if not scope_complete:
        reasons.append("SCOPED_HOLDINGS_INCOMPLETE")
    if not same_currency_basis_confirmed_by_caller:
        reasons.append("COMMON_CURRENCY_BASIS_UNCONFIRMED")
    if not private_scope:
        reasons.append("PUBLIC_REFERENCE_NOT_PRIVATE_PORTFOLIO")
    cash_status = _visibility(cash_visibility, "cash_visibility")
    cash = _money(cash_base, "cash_base") if cash_base is not None else None
    if cash_status != "VERIFIED_VISIBLE" or cash is None:
        reasons.append("CASH_NOT_VISIBLE_OR_UNQUANTIFIED")
    if not isinstance(positions, list) or not positions:
        raise ValueError("positions: nonempty list of supplied P records required")

    p_records = []
    display_values: list[Decimal] = []
    seen: set[str] = set()
    values: dict[str, Decimal] = {}
    for idx, raw in enumerate(positions):
        if not isinstance(raw, Mapping):
            raise ValueError(f"positions[{idx}]: mapping required")
        p_id = _text(raw.get("p_id"), f"positions[{idx}].p_id")
        if p_id in seen or p_id == "P-CASH":
            raise ValueError("DUPLICATE_OR_RESERVED_P_ID")
        seen.add(p_id)
        field_statuses = raw.get("field_statuses")
        if not isinstance(field_statuses, Mapping):
            raise ValueError(f"positions[{idx}].field_statuses: mapping required")
        statuses = {key: _visibility(field_statuses.get(key, "NOT_VISIBLE"), f"{p_id}.{key}")
                    for key in REQUIRED_FIELD_STATUSES}
        security = raw.get("security_id")
        if security is not None:
            security = _text(security, f"{p_id}.security_id")
        if identity_is_placeholder(security):
            reasons.append(f"{p_id}:SECURITY_ID_UNIDENTIFIED")
        row_currency = raw.get("currency")
        if row_currency is not None:
            row_currency = _text(row_currency, f"{p_id}.currency").upper()
        row_account = raw.get("account_scope")
        if row_account is not None:
            row_account = _text(row_account, f"{p_id}.account_scope")
        if identity_is_placeholder(row_account):
            reasons.append(f"{p_id}:ACCOUNT_SCOPE_UNIDENTIFIED")
        val_raw = raw.get("market_value_base")
        val = _money(val_raw, f"{p_id}.market_value_base") if val_raw is not None else None
        display_status = _visibility(raw.get("displayed_weight_visibility", "NOT_VISIBLE"),
                                     f"{p_id}.displayed_weight_visibility")
        raw_display = raw.get("displayed_weight_pct")
        if (display_status == "VERIFIED_VISIBLE") != (raw_display is not None):
            raise ValueError("DISPLAYED_WEIGHT_VISIBILITY_VALUE_MISMATCH")
        displayed = (_displayed_pct(raw_display, f"{p_id}.displayed_weight_pct")
                     if raw_display is not None else None)
        if displayed is not None:
            display_values.append(displayed)
        if (val is None or security is None or identity_is_placeholder(security)
                or identity_is_placeholder(row_account)
                or (private_scope and identity_is_placeholder(account))
                or row_currency != curr or row_account != account
                or any(v != "VERIFIED_VISIBLE" for v in statuses.values())):
            reasons.append(f"{p_id}:FIELD_NOT_COMPARABLE_OR_NOT_VISIBLE")
        else:
            values[p_id] = val
        p_records.append({"p_id": p_id, "security_id": security,
                          "account_scope": row_account, "currency": row_currency,
                          "market_value_base": f"{val:.2f}" if val is not None else None,
                          "displayed_weight_pct_private": (
                              f"{displayed:.2f}" if displayed is not None else None),
                          "displayed_weight_visibility": display_status,
                          "field_statuses": statuses,
                          "provenance": "CALLER_REPORTED_VISIBILITY_NOT_BROKER_VERIFIED"})
    response: dict[str, Any] = {
        "status": "OBSERVATION_LEDGER_ONLY", "analysis_id": aid,
        "observed_on": observed_on, "analysis_as_of": analysis_as_of,
        "captured_at": captured_at, "source_type": src, "account_scope": account,
        "currency": curr, "private_scope": private_scope,
        "p_ledger_private": p_records,
        "cash_record_private": {"p_id": "P-CASH", "amount_base": f"{cash:.2f}" if cash is not None else None,
                                "visibility": cash_status},
        "known_scope_weights_pct": None,
        "scope_total_base": None,
        "displayed_weight_summary_private": (
            {"visible_count": len(display_values),
             "position_row_count": len(positions),
             "displayed_weight_sum_pct": (
                 f"{sum(display_values, Decimal('0')):.2f}"
                 if len(display_values) == len(positions) else None),
             "normalization": "NONE_DISPLAYED_VALUES_UNCHANGED",
             "denominator_verification": "NOT_PERFORMED"}
            if display_values else None),
        "portfolio_room_status": "ROOM_UNAVAILABLE",
        "verification": "CALLER_ASSERTED_NOT_INDEPENDENTLY_AUTHENTICATED",
        "missing_or_qualified": sorted(set(reasons)),
        "writes": "NONE", "source_retrieval": "NONE", "blossom_access": "NONE",
        "decision_authority": "CEO_ONLY",
    }
    if not reasons and len(values) == len(positions) and cash is not None:
        total = sum(values.values(), cash)
        if total <= 0:
            response["missing_or_qualified"] = ["ZERO_SCOPED_DENOMINATOR"]
        else:
            all_values = dict(values)
            all_values["P-CASH"] = cash
            # Hundredths of a percentage point reconcile to exactly 100.00.
            ideals = {key: v * Decimal("10000") / total for key, v in all_values.items()}
            units = {key: int(x.to_integral_value(rounding=ROUND_DOWN)) for key, x in ideals.items()}
            left = 10000 - sum(units.values())
            for key in sorted(units, key=lambda k: (-(ideals[k] - units[k]), k))[:left]:
                units[key] += 1
            response["status"] = "SCOPED_WEIGHTS_DERIVED_FROM_CALLER_VISIBLE_DATA"
            response["known_scope_weights_pct"] = {k: f"{Decimal(units[k]) / HUNDRED:.2f}"
                                                    for k in sorted(units)}
            response["scope_total_base"] = f"{total:.2f}"
    return response
