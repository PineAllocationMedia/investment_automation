"""Conservative arithmetic over supplied financial fact records.

Does not fetch/authenticate evidence, perform historical PIT qualification,
normalize owner earnings, value shares, or authorize investments.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Mapping, Any

SUPPORTED = {
    "OPERATING_MARGIN": ("OPERATING_INCOME", "REVENUE"),
    "REVENUE_GROWTH_YOY": ("REVENUE", "REVENUE"),
    "CFO_LESS_PPE": ("CFO", "PPE_CASH_OUTFLOW"),
}
EVIDENCE_LABELS = frozenset({"VERIFIED", "INDICATIVE", "CONFLICTED", "MISSING"})
RIGHTS = frozenset({"PERMITTED", "UNCERTAIN", "RESTRICTED"})
REQUIRED = (
    "id", "economic_issuer", "metric", "value", "currency", "unit",
    "accounting_basis", "consolidation", "period_start", "period_end",
    "observed_at", "source_url", "rights_status", "verification_status",
)


def _date(value: Any, field: str) -> date:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field}: ISO date required")
    try:
        d = date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field}: invalid ISO date") from exc
    if d.isoformat() != value:
        raise ValueError(f"{field}: YYYY-MM-DD required")
    return d


def _number(value: Any, field: str) -> Decimal:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field}: explicit decimal string required")
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"{field}: invalid decimal") from exc
    if not number.is_finite():
        raise ValueError(f"{field}: nonfinite decimal")
    return number


def _read(fact: Mapping[str, Any], as_of: date) -> tuple[Decimal, date, date, list[str]]:
    if not isinstance(fact, Mapping):
        raise ValueError("fact: mapping required")
    for key in REQUIRED:
        if key not in fact or fact[key] is None or (isinstance(fact[key], str) and not fact[key].strip()):
            raise ValueError(f"fact: missing {key}")
    for key in REQUIRED:
        if key != "value" and not isinstance(fact[key], str):
            raise ValueError(f"{key}: string required")
    start = _date(fact["period_start"], "period_start")
    end = _date(fact["period_end"], "period_end")
    observed = _date(fact["observed_at"], "observed_at")
    if start > end:
        raise ValueError("financial period reversed")
    if fact["verification_status"] not in EVIDENCE_LABELS:
        raise ValueError("invalid verification_status")
    if fact["rights_status"] not in RIGHTS:
        raise ValueError("invalid rights_status")
    reasons = []
    if observed > as_of:
        reasons.append("OBSERVATION_AFTER_ANALYSIS_CUTOFF")
    if end > as_of:
        reasons.append("FINANCIAL_PERIOD_END_AFTER_ANALYSIS_CUTOFF")
    if fact["rights_status"] == "RESTRICTED":
        reasons.append("RESTRICTED_SOURCE_USE")
    if fact["verification_status"] in {"CONFLICTED", "MISSING"}:
        reasons.append("UNRESOLVED_SOURCE_FACT")
    if not fact["source_url"].startswith("https://"):
        reasons.append("SOURCE_LOCATOR_NOT_HTTPS")
    return _number(fact["value"], "value"), start, end, reasons


def _unavailable(operation: str, fact_ids: list[str], reasons: list[str]) -> dict:
    return {
        "status": "UNAVAILABLE", "operation": operation,
        "fact_ids": fact_ids, "reason_codes": sorted(set(reasons)),
        "source_verification": "NOT_PERFORMED",
        "temporal_authority": "CURRENT_OBSERVATION_ONLY",
    }


def audit_calculation(
    operation: str, left: Mapping[str, Any], right: Mapping[str, Any], *, as_of: str
) -> dict:
    """Perform one supported arithmetic check, without evidence certification.

    A FORMALLY_CALCULATED result means supplied numeric inputs are structurally
    compatible; it never makes an issuer fact VERIFIED or a scenario decision-grade.
    """
    if operation not in SUPPORTED:
        raise ValueError("unsupported financial operation")
    cutoff = _date(as_of, "as_of")
    lv, ls, le, reasons = _read(left, cutoff)
    rv, rs, re, other = _read(right, cutoff)
    reasons.extend(other)
    fact_ids = [left["id"], right["id"]]
    if left["id"] == right["id"]:
        reasons.append("DUPLICATE_FACT_ID")
    left_metric, right_metric = SUPPORTED[operation]
    if (left["metric"], right["metric"]) != (left_metric, right_metric):
        reasons.append("METRIC_MISMATCH")
    for key, reason in (
        ("economic_issuer", "ISSUER_MISMATCH"),
        ("currency", "CURRENCY_MISMATCH"),
        ("unit", "UNIT_MISMATCH"),
        ("accounting_basis", "ACCOUNTING_BASIS_MISMATCH"),
        ("consolidation", "CONSOLIDATION_SCOPE_MISMATCH"),
    ):
        if left[key] != right[key]:
            reasons.append(reason)
    if operation == "REVENUE_GROWTH_YOY":
        len_l, len_r = (le - ls).days + 1, (re - rs).days + 1
        if ls != re + timedelta(days=1):
            reasons.append("NONADJACENT_PERIODS")
        if not (360 <= len_l <= 371 and 360 <= len_r <= 371) or abs(len_l - len_r) > 2:
            reasons.append("INCOMPARABLE_FISCAL_PERIOD_LENGTH")
        if rv <= 0 or lv < 0:
            reasons.append("INVALID_REVENUE_DENOMINATOR")
    else:
        if ls != rs or le != re:
            reasons.append("PERIOD_MISMATCH")
        if operation == "OPERATING_MARGIN" and rv <= 0:
            reasons.append("INVALID_REVENUE_DENOMINATOR")
        if operation == "CFO_LESS_PPE" and rv < 0:
            reasons.append("PPE_OUTFLOW_MAGNITUDE_EXPECTED")
    if reasons:
        return _unavailable(operation, fact_ids, reasons)
    if operation == "OPERATING_MARGIN":
        result = lv / rv * Decimal("100")
        metric = "OPERATING_MARGIN_PERCENT"
        unit = "PERCENT"
    elif operation == "REVENUE_GROWTH_YOY":
        result = (lv / rv - Decimal("1")) * Decimal("100")
        metric = "REVENUE_GROWTH_YOY_PERCENT"
        unit = "PERCENT"
    else:
        result = lv - rv
        metric = "CFO_MINUS_PPE_PROXY_NOT_NORMALIZED_FCF"
        unit = f"{left['unit']} {left['currency']}"
    out = {
        "status": "FORMALLY_CALCULATED", "operation": operation, "metric": metric,
        "value": str(result.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        "unit": unit, "fact_ids": fact_ids,
        "input_evidence_labels": [left["verification_status"], right["verification_status"]],
        "source_rights_statuses": [left["rights_status"], right["rights_status"]],
        "source_verification": "NOT_PERFORMED",
        "temporal_authority": "CURRENT_OBSERVATION_ONLY",
        "decision_grade": False,
    }
    if "UNCERTAIN" in out["source_rights_statuses"]:
        out["permission_caveat"] = "SOURCE_USE_UNCERTAIN_REVIEW_REQUIRED"
    return out
