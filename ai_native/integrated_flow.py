"""Bounded manual-handoff assembler for the AI-native R1 construction release.

Consumes already-researched IR/PI capsules. Does not call Projects, browse,
authenticate sources, persist private records, or authorize portfolio action.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Mapping

from .contribution_math import project_gross_contribution
from .known_costs import tally_supplied_costs
from .funded_costs_reconciliation import reconcile_funded_contribution
from .research_memory import prepare_research_history
from .research_case_comparison import compare_supplied_cases
from .evidence_math import audit_calculation
from .source_fusion import assemble_source_fusion
from .fact_evidence_alignment import align_ir_facts_to_sources
from .valuation_scenarios import evaluate_valuation_scenarios
from .candidate_comparison import compare_candidates
from .fundamental_dossier import prepare_fundamental_dossier
from .reporting import render_report

ROOM_STATUSES = frozenset({"ROOM_EVIDENCE_SUPPORTED", "ROOM_CONDITIONAL", "ROOM_UNAVAILABLE"})


def _required_text(record: Mapping[str, Any], key: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key}: nonempty string required")
    return value.strip()


def _date(value: str, key: str) -> date:
    try:
        result = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{key}: ISO date required") from exc
    if result.isoformat() != value:
        raise ValueError(f"{key}: canonical ISO date required")
    return result


def assemble_manual_run(
    request: Mapping[str, Any],
    ir_capsule: Mapping[str, Any],
    *,
    pi_delta: Mapping[str, Any] | None = None,
    calculation_requests: list[Mapping[str, Any]] | None = None,
    contribution_inputs: Mapping[str, Any] | None = None,
    cost_inputs: Mapping[str, Any] | None = None,
    memory_inputs: Mapping[str, Any] | None = None,
    source_evidence_inputs: Mapping[str, Any] | None = None,
    valuation_inputs: Mapping[str, Any] | None = None,
    candidate_comparison_inputs: Mapping[str, Any] | None = None,
    fundamental_inputs: Mapping[str, Any] | None = None,
    historical_comparison_inputs: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble a PRIVATE report without claiming live Project connectivity.

    IR/PI content remains user/specialist-supplied; validations preserve status
    and check consistency only. No side effects or archival writes occur.
    """
    if not isinstance(request, Mapping) or not isinstance(ir_capsule, Mapping):
        raise ValueError("request and ir_capsule must be mappings")
    run_id = _required_text(request, "analysis_id")
    as_of = _required_text(request, "as_of")
    cutoff = _date(as_of, "as_of")
    objective = _required_text(request, "objective")
    strategy = _required_text(request, "strategy_id")
    method = _required_text(request, "method_version")
    kind = _required_text(request, "kind")
    if kind not in {"DECISION", "FOLLOWUP"}:
        raise ValueError("kind must be DECISION or FOLLOWUP")
    if _required_text(ir_capsule, "analysis_id") != run_id:
        raise ValueError("IR analysis_id mismatch")
    ir_cutoff = _date(_required_text(ir_capsule, "research_as_of"), "research_as_of")
    if ir_cutoff > cutoff:
        raise ValueError("IR research is newer than request cutoff")
    if not isinstance(ir_capsule.get("summary"), list):
        raise ValueError("IR summary list required")
    if not isinstance(ir_capsule.get("facts"), list):
        raise ValueError("IR facts list required")
    if not 1 <= len(ir_capsule["summary"]) <= 5:
        raise ValueError("IR summary must contain one to five points")
    for item in ir_capsule["summary"]:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("IR summary contains empty item")
    summary = [item.strip() for item in ir_capsule["summary"]]
    limits = [_required_text(ir_capsule, "limitations")]
    status = "EXPLORATORY"
    room = "NOT_EVALUATED"
    pi_date = None
    if pi_delta is not None:
        if not isinstance(pi_delta, Mapping):
            raise ValueError("pi_delta must be a mapping")
        if _required_text(pi_delta, "analysis_id") != run_id:
            raise ValueError("PI analysis_id mismatch")
        if pi_delta.get("forwarded_ir") != ir_capsule:
            raise ValueError("PACKET_INCOMPLETE: PI must forward identical IR capsule")
        pi_date = _required_text(pi_delta, "portfolio_as_of")
        if _date(pi_date, "portfolio_as_of") > cutoff:
            raise ValueError("Portfolio observation is newer than request cutoff")
        room = _required_text(pi_delta, "room_status")
        if room not in ROOM_STATUSES:
            raise ValueError("invalid Portfolio Room status")
        summary.append("Portfolio: " + _required_text(pi_delta, "summary"))
        limits.append(_required_text(pi_delta, "limitations"))
        if room != "ROOM_EVIDENCE_SUPPORTED":
            status = "CONDITIONAL"
    if method == "UNKNOWN_NOT_LOADED":
        limits.append("Specialized method was not loaded; research remains exploratory.")
        status = "CONDITIONAL"

    checks: list[dict[str, Any]] = []
    for item in calculation_requests or []:
        if not isinstance(item, Mapping):
            raise ValueError("calculation request must be a mapping")
        checks.append(audit_calculation(
            _required_text(item, "operation"), item.get("left"), item.get("right"), as_of=as_of
        ))
    if any(item["status"] == "UNAVAILABLE" for item in checks):
        limits.append("One or more requested financial calculations are unavailable; see private calculation annex.")
        status = "CONDITIONAL"

    contribution = None
    if contribution_inputs is not None:
        if pi_delta is None:
            raise ValueError("Cannot calculate a contribution without a PI capsule")
        if not isinstance(contribution_inputs, Mapping):
            raise ValueError("contribution_inputs must be a mapping")
        if contribution_inputs.get("as_of") != pi_date:
            raise ValueError("Contribution input must use exact PI portfolio observation date")
        contribution = project_gross_contribution(**contribution_inputs)
        if contribution["status"] == "UNAVAILABLE":
            limits.append("Gross contribution projection unavailable: required scope flags were not established.")
            status = "CONDITIONAL"
        else:
            limits.append("Gross contribution math only; real account costs, taxes, FX and execution not assessed.")

    costs = None
    funded_contribution = None
    if cost_inputs is not None:
        if contribution is None:
            raise ValueError("cost_inputs require an available PI gross contribution projection")
        if not isinstance(cost_inputs, Mapping):
            raise ValueError("cost_inputs must be a mapping")
        if cost_inputs.get("analysis_as_of") != as_of:
            raise ValueError("cost_inputs analysis cutoff must match request as_of")
        costs = tally_supplied_costs(gross_projection=contribution, **cost_inputs)
        if costs["status"] != "SUPPLIED_COST_TALLY_ONLY":
            limits.append("After-cost analysis unavailable: incomplete or infeasible supplied purchase costs.")
        else:
            limits.append("Supplied-cost tally only; quotes, taxes and net execution not certified.")
            if costs.get("gross_allocation_funding_conflict"):
                limits.append("Gross allocation uses the full contribution; deducting fees from that same contribution needs a revised plan.")
        funded_contribution = reconcile_funded_contribution(
            contribution_inputs=contribution_inputs, gross_projection=contribution,
            cost_tally=costs)
        if funded_contribution["status"] == "CONDITIONAL_SUPPLIED_COST_BUDGET_RECONCILED":
            limits.append("Conditional new-capital budget reconciled to stated costs; order-size-dependent fees and real execution must be rechecked. See private annex.")
        else:
            limits.append("Funded new-capital budget unavailable; missing or incompatible cost/funding data. Gross projection remains separately labeled.")
        status = "CONDITIONAL"

    facts = ir_capsule["facts"]
    if any(isinstance(f, Mapping) and f.get("status") in {"MISSING", "CONFLICTED"} for f in facts):
        status = "CONDITIONAL"

    source_annex = None
    fact_alignment = None
    if source_evidence_inputs is not None:
        if not isinstance(source_evidence_inputs, Mapping):
            raise ValueError("source_evidence_inputs: mapping required")
        if set(source_evidence_inputs) != {"analysis_id", "analysis_as_of", "observations"}:
            raise ValueError("source_evidence_inputs: exact private schema required")
        if source_evidence_inputs["analysis_id"] != run_id or source_evidence_inputs["analysis_as_of"] != as_of:
            raise ValueError("SOURCE_ANNEX_ANALYSIS_OR_DATE_MISMATCH")
        source_annex = assemble_source_fusion(**source_evidence_inputs)
        ir_fact_ids = {x["id"] for x in facts if isinstance(x, Mapping) and isinstance(x.get("id"), str)}
        supported_ids = {x["fact_id"] for x in source_annex["observations_private"]}
        if not supported_ids.issubset(ir_fact_ids):
            raise ValueError("SOURCE_ANNEX_UNKNOWN_IR_FACT_ID")
        source_annex["uncovered_ir_fact_ids"] = sorted(ir_fact_ids - supported_ids)
        fact_alignment = align_ir_facts_to_sources(
            analysis_id=run_id, analysis_as_of=as_of,
            ir_facts=facts, source_annex=source_annex)
        if fact_alignment["facts_needing_review"]:
            limits.append("Some IR fact evidence labels do not structurally align with supplied source observations; see private review flags. No evidence was upgraded or authenticated.")
            status = "CONDITIONAL"
        if (source_annex["unresolved_count"] or source_annex["uncovered_ir_fact_ids"] or
                source_annex["noncomparable_basis_groups"]):
            limits.append("Some research evidence is missing, disputed or noncomparable; see private source annex. No source was independently certified.")
            status = "CONDITIONAL"
    fundamental_dossier = None
    if fundamental_inputs is not None:
        if source_annex is None:
            raise ValueError("FUNDAMENTAL_REQUIRES_SOURCE_ANNEX")
        if not isinstance(fundamental_inputs, Mapping):
            raise ValueError("fundamental_inputs: mapping required")
        required = {"economic_issuer", "instrument", "period_pairs",
                    "annual_periods_comparable_reported", "qualitative_axes"}
        if set(fundamental_inputs) != required:
            raise ValueError("FUNDAMENTAL_INPUT_SCHEMA_MISMATCH")
        ir_ids = [x["id"] for x in facts
                  if isinstance(x, Mapping) and isinstance(x.get("id"), str)]
        fundamental_dossier = prepare_fundamental_dossier(
            analysis_id=run_id, analysis_as_of=as_of, source_annex=source_annex,
            original_ir_fact_ids=ir_ids, **fundamental_inputs)
        limits.append("Fundamental metrics use caller-reported original-source observations only: organic growth, normalized owner cash, moat durability, Expected Return and source authenticity remain unverified. See private dossier.")
        status = "CONDITIONAL"

    valuation_scenarios = None
    if valuation_inputs is not None:
        if not isinstance(valuation_inputs, Mapping):
            raise ValueError("valuation_inputs: mapping required")
        if valuation_inputs.get("analysis_id") != run_id or valuation_inputs.get("analysis_as_of") != as_of:
            raise ValueError("VALUATION_ANALYSIS_OR_DATE_MISMATCH")
        valuation_scenarios = evaluate_valuation_scenarios(**valuation_inputs)
        limits.append("Valuation scenario arithmetic is conditional on source, security, currency and terminal assumptions; see private valuation annex. No probability-weighted Expected Return or VFV alpha certified.")
        status = "CONDITIONAL"


    candidate_comparison = None
    if candidate_comparison_inputs is not None:
        if not isinstance(candidate_comparison_inputs, Mapping):
            raise ValueError("candidate_comparison_inputs: mapping required")
        if set(candidate_comparison_inputs) != {"analysis_id", "analysis_as_of", "strategy_id", "account_currency", "candidates"}:
            raise ValueError("CANDIDATE_COMPARISON_EXACT_SCHEMA_REQUIRED")
        if (candidate_comparison_inputs["analysis_id"] != run_id
                or candidate_comparison_inputs["analysis_as_of"] != as_of
                or candidate_comparison_inputs["strategy_id"] != strategy):
            raise ValueError("CANDIDATE_COMPARISON_MANDATE_MISMATCH")
        candidate_comparison = compare_candidates(**candidate_comparison_inputs)
        limits.append("Candidate comparison contains scenario-to-scenario arithmetic only; no authenticated source, FX-based account return, probability-weighted Expected Return, VFV forward alpha, ranking or trade authority. See private annex.")
        status = "CONDITIONAL"

    historical_comparison = None
    if historical_comparison_inputs is not None:
        if kind != "FOLLOWUP":
            raise ValueError("HISTORICAL_COMPARISON_REQUIRES_FOLLOWUP")
        if (not isinstance(historical_comparison_inputs, Mapping)
                or set(historical_comparison_inputs) != {"prior_case", "subject_id", "fact_links"}):
            raise ValueError("HISTORICAL_COMPARISON_EXACT_SCHEMA_REQUIRED")
        historical_comparison = compare_supplied_cases(
            request=request, ir_capsule=ir_capsule, **historical_comparison_inputs
        )
        if historical_comparison["status"] == "STRUCTURAL_REVIEW_PREPARED":
            limits.append("Prior and current caller-supplied research compared structurally in private annex; no independently certified economic or thesis change.")
        else:
            limits.append("Historical research comparison unavailable or has no explicitly linked facts; not evidence of no change.")
        status = "CONDITIONAL"

    packet: dict[str, Any] = {
        "kind": kind,
        "analysis_id": run_id,
        "as_of": as_of,
        "strategy": strategy,
        "method_version": method,
        "status": status,
        "objective": objective,
        "decision_line": _required_text(ir_capsule, "decision_line"),
        "summary": summary,
        "facts": facts,
        "countercase": _required_text(ir_capsule, "countercase"),
        "limitations": " ".join(limits),
        "next_action": _required_text(ir_capsule, "next_action"),
    }
    if kind == "FOLLOWUP":
        packet["changes"] = ir_capsule.get("changes", [])
        if "prior_analysis_id" in request:
            packet["prior_analysis_id"] = request["prior_analysis_id"]
        if "period_start" in request or "period_end" in request:
            packet["period_start"] = request.get("period_start")
            packet["period_end"] = request.get("period_end")

    markdown = render_report(packet)
    # Memory proposal excludes portfolio data, issuer narrative and full claims.
    memory = {
        "analysis_id": run_id,
        "as_of": as_of,
        "method_version": method,
        "fact_ids": [x["id"] for x in facts],
        "archive_status": "PROPOSED_NOT_COMMITTED",
        "privacy_review": "REQUIRED_BEFORE_ANY_WRITE",
        "source_authentication": "NOT_PERFORMED_BY_INTEGRATION",
    }
    private_history = None
    github_review_gate = None
    if memory_inputs is not None:
        if not isinstance(memory_inputs, Mapping):
            raise ValueError("memory_inputs: mapping required")
        prepared = prepare_research_history(request, ir_capsule, **memory_inputs)
        private_history = prepared["private_research_history_proposal"]
        github_review_gate = prepared["github_review_gate"]

    return {
        "status": "ASSEMBLED_COMPONENT_ONLY_NOT_END_TO_END_ACCEPTANCE",
        "markdown": markdown,
        "calculation_checks": checks,
        "source_evidence_annex_private": source_annex,
        "fact_source_alignment_private": fact_alignment,
        "valuation_scenarios_private": valuation_scenarios,
        "candidate_comparison_private": candidate_comparison,
        "fundamental_dossier_private": fundamental_dossier,
        "gross_contribution_private": contribution,
        "supplied_costs_private": costs,
        "funded_contribution_private": funded_contribution,
        "portfolio_room_status": room,
        "memory_proposal_nonprivate": memory,
        "private_research_history_proposal": private_history,
        "historical_research_comparison_private": historical_comparison,
        "github_memory_review_gate": github_review_gate,
        "handoff": "MANUAL_TRANSFER_NOT_PROJECT_AUTOMATION",
        "source_verification": "NOT_PERFORMED_BY_INTEGRATION",
    }
