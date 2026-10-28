"""Private, source-linked operating economics dossier; indicative, not verified facts."""
from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Mapping

METRICS = frozenset({"REVENUE", "OPERATING_INCOME", "CFO", "CASH_CAPEX", "DILUTED_AVG_SHARES"})
AXES = ("COMPETITIVE_POSITION", "REINVESTMENT", "PERMANENT_LOSS")
CENT = Decimal("0.01")


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label}: nonempty string required")
    return value.strip()


def _percent(n: Decimal, d: Decimal) -> str:
    return str((n / d * Decimal(100)).quantize(CENT, rounding=ROUND_HALF_UP))


def prepare_fundamental_dossier(
    *, analysis_id: str, analysis_as_of: str, economic_issuer: str,
    instrument: str, source_annex: Mapping[str, Any],
    period_pairs: Mapping[str, list[str]],
    annual_periods_comparable_reported: bool,
    qualitative_axes: Mapping[str, Mapping[str, Any]],
    original_ir_fact_ids: list[str],
) -> dict[str, Any]:
    """Extract only compatible reported observations, preserving unsupported gaps.

    Identifies supplied original observations and analyst interpretations; it does
    NOT fetch sources, certify facts, normalize earnings or assign investment rank.
    """
    aid = _string(analysis_id, "analysis_id")
    issuer = _string(economic_issuer, "economic_issuer")
    security = _string(instrument, "instrument")
    cutoff = date.fromisoformat(_string(analysis_as_of, "analysis_as_of"))
    if not isinstance(source_annex, Mapping) or source_annex.get("analysis_id") != aid or source_annex.get("analysis_as_of") != analysis_as_of:
        raise ValueError("SOURCE_ANNEX_ID_OR_DATE_MISMATCH")
    if type(annual_periods_comparable_reported) is not bool:
        raise ValueError("EXPLICIT_PERIOD_COMPARABILITY_REQUIRED")
    if not isinstance(original_ir_fact_ids, list) or not original_ir_fact_ids or any(not isinstance(x, str) or not x for x in original_ir_fact_ids):
        raise ValueError("ORIGINAL_IR_FACT_IDS_REQUIRED")
    fact_ids = set(original_ir_fact_ids)
    if len(fact_ids) != len(original_ir_fact_ids):
        raise ValueError("DUPLICATE_IR_FACT_ID")
    observations = source_annex.get("observations_private")
    if not isinstance(observations, list):
        raise ValueError("SOURCE_OBSERVATIONS_REQUIRED")
    indexed = {}
    for o in observations:
        if not isinstance(o, Mapping):
            raise ValueError("SOURCE_OBSERVATION_INVALID")
        oid = _string(o.get("observation_id"), "observation_id")
        if oid in indexed:
            raise ValueError("DUPLICATE_SOURCE_OBSERVATION_ID")
        indexed[oid] = o
    if not isinstance(period_pairs, Mapping) or not period_pairs or set(period_pairs) - METRICS:
        raise ValueError("PERIOD_PAIR_METRIC_UNSUPPORTED")
    if not isinstance(qualitative_axes, Mapping) or set(qualitative_axes) != set(AXES):
        raise ValueError("EXACT_THREE_QUALITATIVE_AXES_REQUIRED")
    qualitative = {}
    warnings = []
    for axis in AXES:
        raw = qualitative_axes[axis]
        if not isinstance(raw, Mapping):
            raise ValueError("QUALITATIVE_AXIS_INVALID")
        state = _string(raw.get("status"), f"{axis}.status")
        if state not in {"SPECIALIST_REPORTED", "UNKNOWN"}:
            raise ValueError("NO_AUTOMATIC_QUALITATIVE_CERTIFICATION")
        refs = raw.get("ir_fact_ids")
        if not isinstance(refs, list) or any(not isinstance(x, str) for x in refs) or not set(refs).issubset(fact_ids):
            raise ValueError("UNKNOWN_OR_INVALID_IR_FACT_REFERENCE")
        rationale = _string(raw.get("rationale"), f"{axis}.rationale")
        challenge = _string(raw.get("countercase"), f"{axis}.countercase")
        if state == "UNKNOWN" or not refs:
            warnings.append(f"{axis}_NOT_EVIDENCED")
        qualitative[axis] = {"status": state, "rationale": rationale,
                             "countercase": challenge, "ir_fact_ids": list(refs)}
    paired: dict[str, dict[str, Any]] = {}
    for metric, ids in period_pairs.items():
        if not isinstance(ids, list) or len(ids) != 2 or len(set(ids)) != 2 or any(not isinstance(x, str) for x in ids):
            raise ValueError("TWO_DISTINCT_OBSERVATIONS_REQUIRED")
        if any(oid not in indexed for oid in ids):
            raise ValueError("UNKNOWN_SOURCE_OBSERVATION_ID")
        rows = [indexed[oid] for oid in ids]
        for row in rows:
            if row.get("fact_id") not in fact_ids:
                raise ValueError("SOURCE_FACT_NOT_IN_ORIGINAL_IR")
            if row.get("metric") != metric or row.get("economic_issuer") != issuer or row.get("instrument") != security:
                raise ValueError("METRIC_OR_SECURITY_IDENTITY_MISMATCH")
        earlier, later = (date.fromisoformat(row["period_start"]) for row in rows)
        ends = [date.fromisoformat(row["period_end"]) for row in rows]
        if not (earlier <= ends[0] < later <= ends[1] <= cutoff):
            raise ValueError("FISCAL_PERIODS_NOT_SEQUENTIAL")
        # Only annual periods; different fiscal lengths remain explicit uncertainty.
        lengths = [(end - start).days + 1 for end, start in zip(ends, (earlier, later))]
        reasons = []
        if not annual_periods_comparable_reported:
            reasons.append("ANNUAL_COMPARABILITY_UNCONFIRMED")
        if min(lengths) < 350 or max(lengths) > 378 or abs(lengths[0] - lengths[1]) > 7:
            reasons.append("PERIOD_LENGTH_NOT_COMPARABLE")
        if rows[0].get("definition_basis") != rows[1].get("definition_basis"):
            reasons.append("ACCOUNTING_BASIS_MISMATCH")
        for field in ("currency", "unit", "consolidation"):
            if rows[0].get(field) != rows[1].get(field):
                reasons.append(f"{field.upper()}_MISMATCH")
        if any(row.get("claim_use_status") != "CALLER_REPORTED_ONLY" or
               row.get("source_kind") != "ISSUER_OR_REGULATOR" or
               row.get("classification") != "SOURCE_FACT" or
               row.get("rights_status") != "PERMITTED" for row in rows):
            reasons.append("SOURCE_NOT_USABLE_FOR_DESCRIPTIVE_ARITHMETIC")
        try:
            values = [Decimal(row["value"]) for row in rows]
            if not all(v.is_finite() for v in values):
                reasons.append("INVALID_NUMERIC_VALUE")
        except (ValueError, TypeError, ArithmeticError):
            values = None
            reasons.append("INVALID_NUMERIC_VALUE")
        if metric == "CASH_CAPEX" and values is not None and any(v < 0 for v in values):
            reasons.append("CAPEX_SIGN_CONVENTION_UNCONFIRMED")
        if metric == "DILUTED_AVG_SHARES" and values is not None and any(v <= 0 for v in values):
            reasons.append("DILUTED_SHARES_NONPOSITIVE")
        paired[metric] = {"observation_ids": list(ids), "fact_ids": [r["fact_id"] for r in rows],
                          "period_ends": [d.isoformat() for d in ends],
                          "currency": rows[0].get("currency"), "unit": rows[0].get("unit"),
                          "definition_basis": rows[0].get("definition_basis"),
                          "values": [str(v) for v in values] if values is not None and not reasons else None,
                          "status": "INDICATIVE_COMPARABLE" if not reasons else "UNAVAILABLE",
                          "reason_codes": sorted(set(reasons))}
        warnings += [f"{metric}:{r}" for r in reasons]
    derived = {}
    def value(name: str) -> list[Decimal] | None:
        p = paired.get(name)
        return [Decimal(v) for v in p["values"]] if p and p["values"] is not None else None
    rev, op, cfo, capex, shares = (value(name) for name in
        ("REVENUE", "OPERATING_INCOME", "CFO", "CASH_CAPEX", "DILUTED_AVG_SHARES"))
    if rev is not None and rev[0] > 0:
        derived["reported_revenue_change_pct"] = _percent(rev[1] - rev[0], rev[0])
    else:
        warnings.append("REVENUE_GROWTH_UNAVAILABLE")
    if rev is not None and op is not None and all(r > 0 for r in rev) and paired["REVENUE"]["period_ends"] == paired["OPERATING_INCOME"]["period_ends"] and paired["REVENUE"]["currency"] == paired["OPERATING_INCOME"]["currency"] and paired["REVENUE"]["unit"] == paired["OPERATING_INCOME"]["unit"]:
        derived["reported_operating_margin_pct"] = [_percent(o, r) for o, r in zip(op, rev)]
    else:
        warnings.append("OPERATING_MARGIN_UNAVAILABLE_OR_NONCOMPARABLE")
    if cfo is not None and capex is not None and paired["CFO"]["period_ends"] == paired["CASH_CAPEX"]["period_ends"] and paired["CFO"]["currency"] == paired["CASH_CAPEX"]["currency"] and paired["CFO"]["unit"] == paired["CASH_CAPEX"]["unit"]:
        derived["cfo_less_cash_capex_descriptive"] = [str(x - y) for x, y in zip(cfo, capex)]
        derived["cfo_less_capex_label"] = "NOT_NORMALIZED_OWNER_EARNINGS"
    else:
        warnings.append("CFO_LESS_CAPEX_UNAVAILABLE_OR_NONCOMPARABLE")
    if shares is not None and shares[0] > 0:
        derived["diluted_share_count_change_pct"] = _percent(shares[1] - shares[0], shares[0])
    else:
        warnings.append("DILUTION_CHANGE_UNAVAILABLE")
    return {"status": "INDICATIVE_FUNDAMENTAL_DOSSIER_NOT_CERTIFIED", "analysis_id": aid,
            "analysis_as_of": analysis_as_of, "economic_issuer": issuer, "instrument": security,
            "metric_pairs_private": paired, "descriptive_metrics_private": derived,
            "qualitative_axes_private": qualitative, "limitations": sorted(set(warnings)),
            "organic_growth_status": "UNKNOWN_ACQUISITIONS_AND_MIX_NOT_EVALUATED",
            "normalized_owner_earnings_status": "NOT_ESTABLISHED",
            "quality_or_durability_verdict": "NOT_AUTOMATICALLY_ESTABLISHED",
            "expected_return_or_trade": "NOT_ESTABLISHED",
            "evidence_authority": "CALLER_REPORTED_ONLY_NOT_ORIGINAL_AUTHENTICATED",
            "writes": "NONE"}
