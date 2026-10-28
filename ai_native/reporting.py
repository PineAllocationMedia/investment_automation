"""Read-only, evidence-preserving R1 report rendering.

No source retrieval, source verification, storage, scheduling, or trades.
All input statuses are caller-provided and preserved, never upgraded.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

EVIDENCE_STATUSES = frozenset({"VERIFIED", "INDICATIVE", "CONFLICTED", "MISSING"})
REPORT_STATUSES = frozenset({"EXPLORATORY", "CONDITIONAL", "COMPONENT_SUPPORTED"})


def _string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field}: nonempty string required")
    return value.strip()


def _iso_date(value: Any, field: str) -> str:
    text = _string(value, field)
    try:
        if date.fromisoformat(text).isoformat() != text:
            raise ValueError
    except ValueError as exc:
        raise ValueError(f"{field}: ISO date YYYY-MM-DD required") from exc
    return text


def _facts(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        raise ValueError("facts: list required")
    identifiers: set[str] = set()
    for i, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise ValueError(f"facts[{i}]: record required")
        ref = _string(item.get("id"), f"facts[{i}].id")
        if ref in identifiers:
            raise ValueError(f"facts[{i}]: duplicate evidence ID")
        identifiers.add(ref)
        _string(item.get("claim"), f"facts[{i}].claim")
        status = _string(item.get("status"), f"facts[{i}].status")
        if status not in EVIDENCE_STATUSES:
            raise ValueError(f"facts[{i}]: invalid evidence status")
        if status == "VERIFIED":
            url = _string(item.get("source_url"), f"facts[{i}].source_url")
            if not url.startswith("https://"):
                raise ValueError(f"facts[{i}]: verified claim needs HTTPS source URL")
            _string(item.get("period"), f"facts[{i}].period")
            _string(item.get("checked_by"), f"facts[{i}].checked_by")
            _iso_date(item.get("checked_at"), f"facts[{i}].checked_at")
    return value


def _source_review(packet: Mapping[str, Any], analysis_id: str, as_of: str,
                   facts: list[Mapping[str, Any]]) -> tuple[dict[str, list[str]], int] | None:
    """Validate private structural-review handoff, never certify research facts."""
    review = packet.get("fact_source_alignment_private")
    if review is None:
        return None
    if not isinstance(review, Mapping) or (
        review.get("status") != "PRIVATE_FACT_SOURCE_ALIGNMENT_NOT_CERTIFIED"
        or review.get("analysis_id") != analysis_id
        or review.get("analysis_as_of") != as_of
        or review.get("source_authentication") != "NOT_PERFORMED"
        or review.get("evidence_upgrade") != "NONE"
        or review.get("decision_grade_status") != "NOT_ESTABLISHED"
    ):
        raise ValueError("REPORT_SOURCE_REVIEW_AUTHORITY_OR_ID_MISMATCH")
    expected = {f["id"]: f["status"] for f in facts}
    rows = review.get("facts_private")
    if not isinstance(rows, list):
        raise ValueError("REPORT_SOURCE_REVIEW_FACTS_REQUIRED")
    by_id: dict[str, list[str]] = {}
    for entry in rows:
        if not isinstance(entry, Mapping):
            raise ValueError("REPORT_SOURCE_REVIEW_ENTRY_INVALID")
        fid = entry.get("fact_id_private")
        if fid not in expected or fid in by_id or entry.get("ir_reported_status") != expected[fid]:
            raise ValueError("REPORT_SOURCE_REVIEW_FACT_MISMATCH")
        flags = entry.get("review_flags")
        if not isinstance(flags, list) or any(
            not isinstance(f, str) or not f or not all(c.isascii() and (c.isupper() or c.isdigit() or c == "_") for c in f)
            for f in flags
        ):
            raise ValueError("REPORT_SOURCE_REVIEW_FLAGS_INVALID")
        alignment = "REVIEW_REQUIRED" if flags else "CALLER_REPORTED_STRUCTURALLY_ALIGNED_ONLY"
        if entry.get("alignment") != alignment:
            raise ValueError("REPORT_SOURCE_REVIEW_ALIGNMENT_MISMATCH")
        by_id[fid] = flags
    count = sum(bool(x) for x in by_id.values())
    if set(by_id) != set(expected) or review.get("facts_needing_review") != count:
        raise ValueError("REPORT_SOURCE_REVIEW_COVERAGE_MISMATCH")
    return by_id, count



def _new_contribution_lines(packet: Mapping[str, Any], analysis_id: str,
                            as_of: str) -> list[str]:
    """Show only supplied NEW-capital percentages, never private positions.

    The gross/funded statuses are computed by the existing M3 helpers. This
    renderer cannot independently validate brokerage economics or holdings.
    """
    summary = packet.get("new_contribution_summary_private")
    if summary is None:
        return []
    if not isinstance(summary, Mapping) or (
        summary.get("analysis_id") != analysis_id
        or summary.get("source_authentication") != "NOT_PERFORMED"
    ):
        raise ValueError("CONTRIBUTION_REPORT_ID_OR_AUTHORITY_MISMATCH")
    observed_at = _iso_date(summary.get("portfolio_as_of"), "portfolio_as_of")
    if observed_at > as_of:
        raise ValueError("CONTRIBUTION_REPORT_OBSERVATION_AFTER_CUTOFF")
    gross = summary.get("gross_status")
    costs = summary.get("cost_status")
    funded = summary.get("funded_status")
    if gross not in {"GROSS_PROJECTION_ONLY", "UNAVAILABLE"} or not isinstance(costs, str) or not isinstance(funded, str):
        raise ValueError("CONTRIBUTION_REPORT_INVALID_STATUS")
    lines = ["", "## New contributions — private, caller-supplied plan"]
    if gross != "GROSS_PROJECTION_ONLY":
        if summary.get("allocations_pct") is not None:
            raise ValueError("CONTRIBUTION_REPORT_UNSUPPORTED_PERCENTAGES")
        lines.append("Gross contribution projection UNAVAILABLE: portfolio scope, cash, currency or identity inputs are not established.")
    else:
        allocations = summary.get("allocations_pct")
        if not isinstance(allocations, Mapping) or not allocations:
            raise ValueError("CONTRIBUTION_REPORT_ALLOCATIONS_REQUIRED")
        exact = {}
        for instrument, raw in allocations.items():
            if (not isinstance(instrument, str) or not instrument.strip()
                    or len(instrument) > 80 or any(ord(c) < 32 for c in instrument)
                    or not isinstance(raw, str)):
                raise ValueError("CONTRIBUTION_REPORT_INVALID_ALLOCATION")
            try:
                pct = Decimal(raw)
            except InvalidOperation as exc:
                raise ValueError("CONTRIBUTION_REPORT_INVALID_ALLOCATION") from exc
            if not pct.is_finite() or pct < 0 or pct > 100:
                raise ValueError("CONTRIBUTION_REPORT_INVALID_ALLOCATION")
            exact[instrument] = pct
        if sum(exact.values()) != 100:
            raise ValueError("CONTRIBUTION_REPORT_PERCENTAGES_NOT_100")
        lines.append("Percentages of **NEW contribution only** (user/analyst supplied, gross of costs; not portfolio target weights):")
        ordered = sorted(exact, key=lambda key: (-exact[key], key))
        for instrument in ordered[:8]:
            safe = instrument.replace("\\", "\\\\").replace("`", "\\`").replace("<", "&lt;").replace(">", "&gt;")
            lines.append(f"- `{safe}`: {format(exact[instrument], 'g')}% of new capital")
        if len(ordered) > 8:
            lines.append(f"- {len(ordered) - 8} other destinations in private M3 annex.")
    if costs == "NOT_SUPPLIED" and funded == "NOT_ASSESSED":
        lines.append("Costs/funding NOT ASSESSED: gross plan only; no executable allocation.")
    elif (costs == "SUPPLIED_COST_TALLY_ONLY"
          and funded == "CONDITIONAL_SUPPLIED_COST_BUDGET_RECONCILED"
          and gross == "GROSS_PROJECTION_ONLY"):
        lines.append("Cost-funded budget CONDITIONALLY RECONCILED using caller-supplied fixed fees; percentages are unchanged, but net amounts and funding differ. Requote size-dependent costs and verify account taxes/FX before any decision.")
    elif (costs in {"NOT_SUPPLIED", "INCOMPLETE_COST_INPUTS", "UNAVAILABLE_GROSS_PROJECTION",
                     "UNAVAILABLE_COSTS_EXCEED_CONTRIBUTION", "SUPPLIED_COST_TALLY_ONLY"}
          and (funded == "NOT_ASSESSED" or funded.startswith("UNAVAILABLE_"))):
        lines.append("After-cost funded allocation UNAVAILABLE: charges, funding or scope are incomplete or inconsistent. Do not treat the gross percentages as an executable plan.")
    else:
        raise ValueError("CONTRIBUTION_REPORT_COST_FUNDING_STATUS_MISMATCH")
    lines.append("PI observations and allocations are caller-supplied; no holdings authentication, source certification, price, trade or investment recommendation.")
    return lines


def _valuation_lines(packet: Mapping[str, Any], analysis_id: str,
                     as_of: str) -> list[str]:
    """Show the existing M2 scenario measures without inventing Expected Return."""
    result = packet.get("valuation_scenarios_private")
    if result is None:
        return []
    if not isinstance(result, Mapping) or (
        result.get("analysis_id") != analysis_id
        or result.get("analysis_as_of") != as_of
        or result.get("source_authentication") != "NOT_PERFORMED"
        or result.get("trade_or_portfolio_authority") != "NONE"
        or result.get("expected_return_status") != "NOT_ESTABLISHED_NO_PROBABILITIES_OR_ASSUMPTION_CERTIFICATION"
        or result.get("benchmark_expected_return_status") != "VFV_ER_UNAVAILABLE_UNLESS_SEPARATELY_EVIDENCED"
        or result.get("calculation_scope") != "CURRENT_SUPPLIED_INPUTS_ONLY_NO_PIT"
    ):
        raise ValueError("VALUATION_REPORT_ID_OR_AUTHORITY_MISMATCH")
    status = result.get("status")
    if status not in {"CONDITIONAL_SCENARIO_ARITHMETIC_ONLY", "UNAVAILABLE_INCOMPATIBLE_BASIS"}:
        raise ValueError("VALUATION_REPORT_STATUS_INVALID")
    _iso_date(result.get("quoted_at"), "valuation.quoted_at")
    if result["quoted_at"] > as_of:
        raise ValueError("VALUATION_REPORT_FUTURE_QUOTE")
    currency, horizon = result.get("currency"), result.get("horizon_years")
    if (not isinstance(currency, str) or len(currency) != 3 or not currency.isascii()
            or not currency.isalpha() or currency != currency.upper()
            or type(horizon) is not int or not 1 <= horizon <= 30):
        raise ValueError("VALUATION_REPORT_BASIS_INVALID")
    scenarios = result.get("scenarios_private")
    if not isinstance(scenarios, Mapping) or set(scenarios) != {"BEAR", "BASE", "BULL"}:
        raise ValueError("VALUATION_REPORT_SCENARIO_SET_INVALID")
    lines = ["", "## Valuation scenarios — conditional, private",
             f"Caller-supplied {horizon}-year scenario arithmetic in {currency}; issuer value assumptions and quotation remain unverified."]
    for name in ("BEAR", "BASE", "BULL"):
        row = scenarios[name]
        if not isinstance(row, Mapping) or row.get("assumption_validation") != "NOT_PERFORMED":
            raise ValueError("VALUATION_REPORT_ASSUMPTIONS_NOT_CERTIFIED")
        measure, value = row.get("return_measure"), row.get("scenario_return_pct_annual")
        if measure not in {"PRICE_ONLY_CAGR_NOT_TOTAL_RETURN",
                           "YEAR_END_CASHFLOW_IRR_CONDITIONAL", "UNAVAILABLE"}:
            raise ValueError("VALUATION_REPORT_MEASURE_INVALID")
        if status == "UNAVAILABLE_INCOMPATIBLE_BASIS":
            if measure != "UNAVAILABLE" or value is not None:
                raise ValueError("VALUATION_REPORT_INVALID_UNAVAILABLE")
        elif measure == "UNAVAILABLE":
            raise ValueError("VALUATION_REPORT_INVALID_AVAILABLE")
        reasons = row.get("reason_codes")
        if not isinstance(reasons, list) or any(
            not isinstance(v, str) or not v or len(v) > 100 or
            any(c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_" for c in v)
            for v in reasons
        ):
            raise ValueError("VALUATION_REPORT_REASON_CODES_INVALID")
        if measure == "UNAVAILABLE":
            if not any(v in reasons for v in (
                "SECURITY_SHARE_CLASS_OR_CORPORATE_ACTION_BASIS_UNCONFIRMED",
                "CURRENCY_OR_FX_BASIS_UNCONFIRMED",
            )):
                raise ValueError("VALUATION_REPORT_UNAVAILABLE_REASON_MISSING")
            lines.append(f"- **{name}: UNAVAILABLE** — security/share-class or currency basis unconfirmed.")
            continue
        if measure == "PRICE_ONLY_CAGR_NOT_TOTAL_RETURN":
            if (row.get("annual_distributions_status") != "UNKNOWN"
                    or "DISTRIBUTIONS_UNKNOWN_PRICE_RETURN_ONLY" not in reasons):
                raise ValueError("VALUATION_REPORT_DISTRIBUTION_BASIS_MISMATCH")
        else:
            if (row.get("annual_distributions_status") != "EXPLICITLY_SUPPLIED"
                    or "DISTRIBUTIONS_UNKNOWN_PRICE_RETURN_ONLY" in reasons):
                raise ValueError("VALUATION_REPORT_DISTRIBUTION_BASIS_MISMATCH")
        if not isinstance(value, str) or len(value) > 40:
            raise ValueError("VALUATION_REPORT_RETURN_INVALID")
        try:
            annual = Decimal(value)
        except InvalidOperation as exc:
            raise ValueError("VALUATION_REPORT_RETURN_INVALID") from exc
        if not annual.is_finite() or annual < -100 or annual > Decimal("1000000000"):
            raise ValueError("VALUATION_REPORT_RETURN_INVALID")
        formatted = format(annual, "f")
        if measure == "PRICE_ONLY_CAGR_NOT_TOTAL_RETURN":
            label = "price-only CAGR; distributions UNKNOWN, not total return"
        else:
            label = "conditional year-end cash-flow IRR on explicitly supplied distributions"
        lines.append(f"- **{name}: {formatted}% annualized** — {label}.")
    lines.append("These are alternative scenario calculations, not probabilities, not probability-weighted Expected Return, not FX-adjusted account performance and not forecast alpha versus VFV. No investment or trade authority.")
    return lines


def _fundamental_lines(packet: Mapping[str, Any], analysis_id: str,
                       as_of: str) -> list[str]:
    """Display M2 descriptive issuer economics, not verified Quality or ER."""
    dossier = packet.get("fundamental_dossier_private")
    if dossier is None:
        return []
    if not isinstance(dossier, Mapping) or (
        dossier.get("status") != "INDICATIVE_FUNDAMENTAL_DOSSIER_NOT_CERTIFIED"
        or dossier.get("analysis_id") != analysis_id
        or dossier.get("analysis_as_of") != as_of
        or dossier.get("evidence_authority") != "CALLER_REPORTED_ONLY_NOT_ORIGINAL_AUTHENTICATED"
        or dossier.get("normalized_owner_earnings_status") != "NOT_ESTABLISHED"
        or dossier.get("quality_or_durability_verdict") != "NOT_AUTOMATICALLY_ESTABLISHED"
        or dossier.get("expected_return_or_trade") != "NOT_ESTABLISHED"
        or dossier.get("organic_growth_status") != "UNKNOWN_ACQUISITIONS_AND_MIX_NOT_EVALUATED"
        or dossier.get("writes") != "NONE"
    ):
        raise ValueError("FUNDAMENTAL_REPORT_ID_OR_AUTHORITY_MISMATCH")

    pairs = dossier.get("metric_pairs_private")
    metrics = dossier.get("descriptive_metrics_private")
    axes = dossier.get("qualitative_axes_private")
    limits = dossier.get("limitations")
    if not isinstance(pairs, Mapping) or not isinstance(metrics, Mapping) or not isinstance(limits, list):
        raise ValueError("FUNDAMENTAL_REPORT_INVALID_STRUCTURE")
    allowed_metrics = {"reported_revenue_change_pct", "reported_operating_margin_pct",
                       "cfo_less_cash_capex_descriptive", "cfo_less_capex_label",
                       "diluted_share_count_change_pct"}
    if set(metrics) - allowed_metrics:
        raise ValueError("FUNDAMENTAL_REPORT_UNKNOWN_METRIC")
    if not isinstance(axes, Mapping) or set(axes) != {
        "COMPETITIVE_POSITION", "REINVESTMENT", "PERMANENT_LOSS"
    }:
        raise ValueError("FUNDAMENTAL_REPORT_QUALITATIVE_AXES_REQUIRED")
    for name, pair in pairs.items():
        if name not in {"REVENUE", "OPERATING_INCOME", "CFO", "CASH_CAPEX", "DILUTED_AVG_SHARES"}:
            raise ValueError("FUNDAMENTAL_REPORT_UNKNOWN_SOURCE_METRIC")
        if not isinstance(pair, Mapping) or pair.get("status") not in {
            "INDICATIVE_COMPARABLE", "UNAVAILABLE"
        }:
            raise ValueError("FUNDAMENTAL_REPORT_PAIR_STATUS_INVALID")
    def supported(*names: str) -> bool:
        return all(name in pairs and pairs[name].get("status") == "INDICATIVE_COMPARABLE"
                   for name in names)
    def decimal(value: Any) -> str:
        if not isinstance(value, str) or not 1 <= len(value) <= 50:
            raise ValueError("FUNDAMENTAL_REPORT_NUMBER_INVALID")
        try:
            number = Decimal(value)
        except InvalidOperation as exc:
            raise ValueError("FUNDAMENTAL_REPORT_NUMBER_INVALID") from exc
        if not number.is_finite() or (number and number.copy_abs().adjusted() > 15):
            raise ValueError("FUNDAMENTAL_REPORT_NUMBER_INVALID")
        return format(number, "f")
    def two_numbers(key: str) -> tuple[str, str]:
        values = metrics[key]
        if not isinstance(values, list) or len(values) != 2:
            raise ValueError("FUNDAMENTAL_REPORT_PERIOD_VALUES_INVALID")
        return decimal(values[0]), decimal(values[1])

    lines = ["", "## Fundamental economics — indicative, private",
             "Caller-reported issuer observations only; comparability checks are structural, not original-source authentication."]
    if "reported_revenue_change_pct" in metrics:
        if not supported("REVENUE"):
            raise ValueError("FUNDAMENTAL_REPORT_UNSUPPORTED_DERIVATION")
        lines.append("- Reported revenue change (two supplied annual periods): " +
                     decimal(metrics["reported_revenue_change_pct"]) + "%; not confirmed organic growth.")
    else:
        lines.append("- Reported revenue growth: UNAVAILABLE or noncomparable.")
    if "reported_operating_margin_pct" in metrics:
        if not supported("REVENUE", "OPERATING_INCOME"):
            raise ValueError("FUNDAMENTAL_REPORT_UNSUPPORTED_DERIVATION")
        before, after = two_numbers("reported_operating_margin_pct")
        lines.append(f"- Reported operating margin, prior → later period: {before}% → {after}%.")
    else:
        lines.append("- Reported operating margin: UNAVAILABLE or noncomparable.")
    if "cfo_less_cash_capex_descriptive" in metrics:
        if not supported("CFO", "CASH_CAPEX") or metrics.get("cfo_less_capex_label") != "NOT_NORMALIZED_OWNER_EARNINGS":
            raise ValueError("FUNDAMENTAL_REPORT_UNSUPPORTED_CASHFLOW")
        left, right = pairs["CFO"], pairs["CASH_CAPEX"]
        if any(left.get(k) != right.get(k) for k in ("period_ends", "currency", "unit")):
            raise ValueError("FUNDAMENTAL_REPORT_CASHFLOW_BASIS_MISMATCH")
        curr, unit = left.get("currency"), left.get("unit")
        if any(not isinstance(v, str) or not 1 <= len(v) <= 20 or
               any(c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_/" for c in v)
               for v in (curr, unit)):
            raise ValueError("FUNDAMENTAL_REPORT_CASHFLOW_UNIT_INVALID")
        before, after = two_numbers("cfo_less_cash_capex_descriptive")
        lines.append(f"- CFO less cash capex (prior → later): {before} → {after} {unit} ({curr}); "
                     "**not normalized owner earnings**.")
    elif "cfo_less_capex_label" in metrics:
        raise ValueError("FUNDAMENTAL_REPORT_ORPHAN_CASHFLOW_LABEL")
    else:
        lines.append("- CFO less cash capex: UNAVAILABLE or noncomparable.")
    if "diluted_share_count_change_pct" in metrics:
        if not supported("DILUTED_AVG_SHARES"):
            raise ValueError("FUNDAMENTAL_REPORT_UNSUPPORTED_DERIVATION")
        lines.append("- Diluted average-share count change: " +
                     decimal(metrics["diluted_share_count_change_pct"]) + "% (not a share-price return).")
    else:
        lines.append("- Diluted share count change: UNAVAILABLE.")
    for axis in ("COMPETITIVE_POSITION", "REINVESTMENT", "PERMANENT_LOSS"):
        row = axes[axis]
        if not isinstance(row, Mapping) or row.get("status") not in {"SPECIALIST_REPORTED", "UNKNOWN"}:
            raise ValueError("FUNDAMENTAL_REPORT_INVALID_QUALITATIVE_STATUS")
        ids = row.get("ir_fact_ids")
        if not isinstance(ids, list) or any(not isinstance(x, str) or not x for x in ids):
            raise ValueError("FUNDAMENTAL_REPORT_INVALID_QUALITATIVE_LINKS")
        evidence = "linked IR facts" if ids else "no linked IR facts"
        lines.append(f"- {axis.replace('_', ' ').title()}: {row['status']} ({evidence}); no independent verdict.")
    if any(not isinstance(s, str) or not s or len(s) > 140
           or any(c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_:_" for c in s)
           for s in limits):
        raise ValueError("FUNDAMENTAL_REPORT_LIMITATIONS_INVALID")
    if limits:
        lines.append(f"- {len(limits)} comparability/evidence limitation(s) remain; see private dossier.")
    lines.append("Quality, durability, organic growth, normalized owner earnings and Expected Return remain NOT ESTABLISHED. No investment ranking, source certification or trade authority.")
    return lines

def render_report(packet: Mapping[str, Any]) -> str:
    """Render a concise markdown research report or user-requested follow-up.

    The presence of evidence metadata does not independently validate a claim.
    Portfolio-sensitive packets must remain in the user's private environment.
    """
    if not isinstance(packet, Mapping):
        raise ValueError("packet: mapping required")
    kind = _string(packet.get("kind"), "kind")
    if kind not in {"DECISION", "FOLLOWUP"}:
        raise ValueError("kind: DECISION or FOLLOWUP required")
    analysis_id = _string(packet.get("analysis_id"), "analysis_id")
    as_of = _iso_date(packet.get("as_of"), "as_of")
    strategy = _string(packet.get("strategy"), "strategy")
    method_version = _string(packet.get("method_version"), "method_version")
    status = _string(packet.get("status"), "status")
    if status not in REPORT_STATUSES:
        raise ValueError("unsupported report status")
    objective = _string(packet.get("objective"), "objective")
    decision_line = _string(packet.get("decision_line"), "decision_line")
    next_action = _string(packet.get("next_action"), "next_action")
    if not isinstance(packet.get("summary"), list) or not (1 <= len(packet["summary"]) <= 6):
        raise ValueError("summary: 1 to 6 points required")
    for i, item in enumerate(packet["summary"]):
        _string(item, f"summary[{i}]")
    facts = _facts(packet.get("facts"))
    source_review = _source_review(packet, analysis_id, as_of, facts)
    lines = [
        f"# {'User-requested reassessment' if kind == 'FOLLOWUP' else 'Investment decision research'} — {analysis_id}",
        f"**As of:** {as_of} | **Strategy:** {strategy} | **Method:** {method_version} | **Status:** {status}",
        f"**Question:** {objective}",
        "", "## Decision line", decision_line, "", "## Key findings",
    ]
    lines += [f"- {item.strip()}" for item in packet["summary"]]
    lines += [
        "", "**Source assurance:** IR evidence statuses are research-reported, not "
        "independently authenticated by this report (including rights and historical availability)."
    ]
    if source_review is not None:
        _, flagged_count = source_review
        lines.append(
            f"**Source reconciliation:** {flagged_count}/{len(facts)} facts require "
            "human source-use review based on supplied observations; no status was upgraded."
        )
    lines += ["", "## Supporting observations"]
    if facts:
        for item in facts:
            ref = item["id"].strip()
            evidence_status = item["status"].strip()
            locator = item.get("source_url") or "SOURCE_NOT_SUPPLIED"
            period = item.get("period") or "PERIOD_UNKNOWN"
            lines.append(f"- [{ref} / {evidence_status}] {item['claim'].strip()} (period: {period}; source: {locator})")
            if source_review is not None and source_review[0][ref]:
                flags = ", ".join(source_review[0][ref])
                lines.append(f"  - **Source review required:** {flags}. IR-reported label is not independently corroborated.")
    else:
        lines.append("No underlying fact records supplied; no factual verification is asserted.")
    lines += _fundamental_lines(packet, analysis_id, as_of)
    lines += _valuation_lines(packet, analysis_id, as_of)
    lines += _new_contribution_lines(packet, analysis_id, as_of)
    if kind == "FOLLOWUP":
        previous_id = packet.get("prior_analysis_id")
        if previous_id is None:
            prior_line = "BASELINE_NOT_AVAILABLE: no previous analysis was provided."
        else:
            prior_line = f"Prior analysis: {_string(previous_id, 'prior_analysis_id')}"
        start_raw, end_raw = packet.get("period_start"), packet.get("period_end")
        if (start_raw is None) != (end_raw is None):
            raise ValueError("follow-up comparison dates must be supplied together")
        if start_raw is None:
            window_label = "no fixed reporting window"
        else:
            start = _iso_date(start_raw, "period_start")
            end = _iso_date(end_raw, "period_end")
            if start > end or end > as_of:
                raise ValueError("follow-up period must be ordered and end by as_of")
            window_label = f"{start} to {end}"
        changes = packet.get("changes")
        if not isinstance(changes, list):
            raise ValueError("changes: list required, possibly empty")
        lines += ["", f"## Requested comparison ({window_label})", prior_line]
        if not changes:
            lines.append("No changes entered in this packet; this is NOT proof that no market or thesis events occurred.")
        else:
            for i, change in enumerate(changes):
                if not isinstance(change, Mapping):
                    raise ValueError(f"changes[{i}]: record required")
                subject = _string(change.get("subject"), f"changes[{i}].subject")
                finding = _string(change.get("finding"), f"changes[{i}].finding")
                cstatus = _string(change.get("status"), f"changes[{i}].status")
                if cstatus not in EVIDENCE_STATUSES:
                    raise ValueError(f"changes[{i}]: invalid status")
                lines.append(f"- **{subject}** [{cstatus}]: {finding}")
    lines += [
        "", "## Strongest countercase / limitation",
        _string(packet.get("countercase"), "countercase"),
        "", "## Evidence and portfolio boundaries",
        _string(packet.get("limitations"), "limitations"),
        "", "## Next human action", next_action,
        "", "_Rendered from supplied data only. No source checks, monitoring, archival or investment execution performed by this formatter._",
    ]
    return "\n".join(lines) + "\n"
