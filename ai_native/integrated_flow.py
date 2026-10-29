"""Bounded manual-handoff assembler for the AI-native R1 construction release.

Consumes already-researched IR/PI capsules. Does not call Projects, browse,
authenticate sources, persist private records, or authorize portfolio action.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Mapping

from .new_capital_flow import prepare_new_capital_projection
from .research_memory import prepare_research_history
from .research_case_comparison import compare_supplied_cases
from .evidence_math import audit_calculation
from .source_fusion import assemble_source_fusion
from .fact_evidence_alignment import align_ir_facts_to_sources
from .pillar_trace import prepare_pillar_trace
from .mode_research_trace import prepare_mode_research_trace
from .mode_portfolio_trace import prepare_mode_portfolio_trace
from .opportunity_triage import prepare_opportunity_triage
from .macro_sector_context import prepare_macro_sector_context
from .valuation_scenarios import evaluate_valuation_scenarios
from .valuation_quote_trace import trace_valuation_quote
from .conditional_weighted_cashflows import calculate_weighted_cashflows
from .candidate_comparison import compare_candidates
from .fundamental_dossier import prepare_fundamental_dossier
from .reporting import render_report
from .strategy_authority import assess_r1_mode
from .strategy_return_parity import check_specialist_mode_echo

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
    probability_inputs: Mapping[str, Any] | None = None,
    candidate_comparison_inputs: Mapping[str, Any] | None = None,
    fundamental_inputs: Mapping[str, Any] | None = None,
    historical_comparison_inputs: Mapping[str, Any] | None = None,
    opportunity_triage_inputs: Mapping[str, Any] | None = None,
    macro_sector_inputs: Mapping[str, Any] | None = None,
    portfolio_room_review_private: Mapping[str, Any] | None = None,
    portfolio_observation_private: Mapping[str, Any] | None = None,
    exceptional_lifecycle_review_private: Mapping[str, Any] | None = None,
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
    mode_gate = assess_r1_mode(strategy)
    kind = _required_text(request, "kind")
    if kind not in {"DECISION", "FOLLOWUP"}:
        raise ValueError("kind must be DECISION or FOLLOWUP")
    ir_mode_echo = check_specialist_mode_echo(strategy, ir_capsule, specialist="IR")
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
    limits.append(mode_gate["limitation"])
    limits.append("IR mode echo: " + ir_mode_echo + "; no independent specialist authentication.")
    if ir_mode_echo == "NOT_ECHOED_MODE_NOT_VERIFIED":
        status = "CONDITIONAL"
    if mode_gate["policy_authority"] == "R1_POLICY_REQUIRES_CEO_APPROVAL":
        status = "CONDITIONAL"
    room = "NOT_EVALUATED"
    pi_date = None
    pi_mode_echo = None
    if pi_delta is not None:
        if not isinstance(pi_delta, Mapping):
            raise ValueError("pi_delta must be a mapping")
        pi_mode_echo = check_specialist_mode_echo(strategy, pi_delta, specialist="PI")
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
        limits.append("PI mode echo: " + pi_mode_echo + "; no independent specialist authentication.")
        if pi_mode_echo == "NOT_ECHOED_MODE_NOT_VERIFIED":
            status = "CONDITIONAL"
        if room != "ROOM_EVIDENCE_SUPPORTED":
            status = "CONDITIONAL"
    mode_portfolio_trace = (
        prepare_mode_portfolio_trace(
            request=request, pi_delta=pi_delta, observation=portfolio_observation_private
        ) if pi_delta is not None else None
    )
    if mode_portfolio_trace is not None:
        limits.append("Mode-specific PI answers cite caller-reported P records only; no account or strategy suitability certification.")
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

    contribution_bundle = None
    contribution = None
    costs = None
    funded_contribution = None
    if contribution_inputs is not None:
        if pi_delta is None:
            raise ValueError("Cannot calculate a contribution without a PI capsule")
        contribution_bundle = prepare_new_capital_projection(
            analysis_id=run_id, analysis_as_of=as_of, portfolio_as_of=pi_date,
            contribution_inputs=contribution_inputs, cost_inputs=cost_inputs,
        )
        contribution = contribution_bundle["gross_contribution_private"]
        costs = contribution_bundle["supplied_costs_private"]
        funded_contribution = contribution_bundle["funded_contribution_private"]
        limits.extend(contribution_bundle["limitations"])
        if contribution["status"] == "UNAVAILABLE" or cost_inputs is not None:
            status = "CONDITIONAL"
    elif cost_inputs is not None:
        raise ValueError("cost_inputs require an available PI gross contribution projection")

    facts = ir_capsule["facts"]
    if any(isinstance(f, Mapping) and f.get("status") in {"MISSING", "CONFLICTED"} for f in facts):
        status = "CONDITIONAL"

    # IR may carry its private evidence in the *same unchanged capsule* used by
    # manual CC -> PI -> CC transfers. Avoid duplicating sensitive source records
    # in a second CC-only argument. Legacy separate inputs remain supported.
    embedded_annex = "EVIDENCE_ANNEX" in ir_capsule
    if embedded_annex:
        if source_evidence_inputs is not None:
            raise ValueError("AMBIGUOUS_SOURCE_ANNEX: choose one authoritative packet")
        source_evidence_inputs = ir_capsule["EVIDENCE_ANNEX"]
        if not isinstance(source_evidence_inputs, Mapping):
            raise ValueError("IR_EVIDENCE_ANNEX_MAPPING_REQUIRED")

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
        # An embedded annex purports to belong to the original IR research.
        # A separately submitted CC review may instead contain legitimately
        # newer observations. Preserve those, but do not imply the earlier IR
        # could have known them or that the original facts were authenticated.
        post_ir_observation_ids = sorted(
            row["observation_id"] for row in source_annex["observations_private"]
            if row["observed_at"] > ir_cutoff.isoformat()
        )
        if embedded_annex and post_ir_observation_ids:
            raise ValueError("IR_SOURCE_OBSERVED_AFTER_RESEARCH_AS_OF")
        source_annex["ir_timeline_relation"] = (
            "POST_IR_CC_REVIEW_ONLY" if post_ir_observation_ids
            else "NO_POST_IR_OBSERVATIONS_REPORTED"
        )
        source_annex["post_ir_observation_ids_private"] = post_ir_observation_ids
        if post_ir_observation_ids:
            limits.append(
                "Some separately supplied CC source observations postdate "
                "the original IR research cutoff. They may inform a current "
                "human review but cannot retroactively substantiate what IR "
                "knew then; obtain an explicit updated IR analysis if needed."
            )
            status = "CONDITIONAL"
        limits.append("Supplied source observations were structurally reviewed only; original-source authenticity and usage rights were not independently certified. See private annex.")
        ir_fact_ids = {x["id"] for x in facts if isinstance(x, Mapping) and isinstance(x.get("id"), str)}
        supported_ids = {x["fact_id"] for x in source_annex["observations_private"]}
        if not supported_ids.issubset(ir_fact_ids):
            raise ValueError("SOURCE_ANNEX_UNKNOWN_IR_FACT_ID")
        source_annex["uncovered_ir_fact_ids"] = sorted(ir_fact_ids - supported_ids)
        fact_alignment = align_ir_facts_to_sources(
            analysis_id=run_id, analysis_as_of=as_of,
            ir_facts=facts, source_annex=source_annex,
            ir_research_as_of=ir_cutoff.isoformat())
        if fact_alignment["facts_needing_review"]:
            limits.append("Some IR fact evidence labels do not structurally align with supplied source observations; see private review flags. No evidence was upgraded or authenticated.")
            status = "CONDITIONAL"
        if (source_annex["unresolved_count"] or source_annex["uncovered_ir_fact_ids"] or
                source_annex["noncomparable_basis_groups"]):
            limits.append("Some research evidence is missing, disputed or noncomparable; see private source annex. No source was independently certified.")
            status = "CONDITIONAL"
    # One optional four-pillar view travels inside the original unchanged IR
    # capsule. A reported qualitative view is never an economic or source verdict.
    pillar_trace = prepare_pillar_trace(
        request=request, ir_capsule=ir_capsule, fact_alignment=fact_alignment)
    if pillar_trace is not None:
        limits.append("Four research-pillar views are caller-reported and not independently certified; Portfolio Room requires a separate PI review.")
        status = "CONDITIONAL"
    mode_research_trace = prepare_mode_research_trace(
        request=request, ir_capsule=ir_capsule, fact_alignment=fact_alignment)
    if mode_research_trace is not None:
        limits.append("Mode-specific IR question-to-fact links are caller-reported research, not verified policy or evidence. See private trace.")
        status = "CONDITIONAL"

    opportunity_triage = None
    if opportunity_triage_inputs is not None:
        if source_annex is None:
            raise ValueError("OPPORTUNITY_TRIAGE_REQUIRES_SOURCE_ANNEX")
        if not isinstance(opportunity_triage_inputs, Mapping):
            raise ValueError("OPPORTUNITY_TRIAGE_INPUT_MAPPING_REQUIRED")
        required = {"analysis_id", "analysis_as_of", "strategy_id",
                    "universe_scope", "universe_note", "candidates"}
        if set(opportunity_triage_inputs) != required:
            raise ValueError("OPPORTUNITY_TRIAGE_EXACT_SCHEMA_REQUIRED")
        if (opportunity_triage_inputs["analysis_id"] != run_id
                or opportunity_triage_inputs["analysis_as_of"] != as_of
                or opportunity_triage_inputs["strategy_id"] != strategy):
            raise ValueError("OPPORTUNITY_TRIAGE_MANDATE_MISMATCH")
        opportunity_triage = prepare_opportunity_triage(
            ir_facts=facts, source_annex=source_annex,
            ir_research_as_of=ir_cutoff.isoformat(), **opportunity_triage_inputs
        )
        limits.append("Research candidates were organized into private analyst follow-up queues only; no global screening, source certification, ranking or investability conclusion.")
        status = "CONDITIONAL"

    macro_sector_context = None
    if macro_sector_inputs is not None:
        if source_annex is None:
            raise ValueError("MACRO_SECTOR_REQUIRES_SOURCE_ANNEX")
        if (not isinstance(macro_sector_inputs, Mapping)
                or set(macro_sector_inputs) != {"analysis_id", "analysis_as_of", "strategy_id", "drivers"}):
            raise ValueError("MACRO_SECTOR_EXACT_SCHEMA_REQUIRED")
        if (macro_sector_inputs["analysis_id"] != run_id
                or macro_sector_inputs["analysis_as_of"] != as_of
                or macro_sector_inputs["strategy_id"] != strategy):
            raise ValueError("MACRO_SECTOR_MANDATE_MISMATCH")
        macro_sector_context = prepare_macro_sector_context(
            ir_facts=facts, source_annex=source_annex, **macro_sector_inputs)
        # Check only already validated links, not an unvalidated caller input.
        linked_ids = {
            oid for driver in macro_sector_context["drivers_private_in_supplied_order"]
            for oid in driver["source_observation_ids_private"]
        }
        if any(row["observed_at"] > ir_cutoff.isoformat()
               for row in source_annex["observations_private"]
               if row["observation_id"] in linked_ids):
            raise ValueError("MACRO_SECTOR_OBSERVATION_AFTER_IR_RESEARCH_AS_OF")
        limits.append("Macro/sector research context is caller-reported and source-linked only; causal magnitude, returns and timing are not inferred or authenticated.")
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
            original_ir_fact_ids=ir_ids,
            ir_research_as_of=ir_cutoff.isoformat(), **fundamental_inputs)
        limits.append("Fundamental metrics use caller-reported original-source observations only: organic growth, normalized owner cash, moat durability, Expected Return and source authenticity remain unverified. See private dossier.")
        status = "CONDITIONAL"

    valuation_scenarios = None
    valuation_quote_trace = None
    weighted_cashflows = None
    if probability_inputs is not None and valuation_inputs is None:
        raise ValueError("WEIGHTED_CASHFLOWS_REQUIRE_VALUATION_INPUTS")
    if valuation_inputs is not None:
        if not isinstance(valuation_inputs, Mapping):
            raise ValueError("valuation_inputs: mapping required")
        if valuation_inputs.get("analysis_id") != run_id or valuation_inputs.get("analysis_as_of") != as_of:
            raise ValueError("VALUATION_ANALYSIS_OR_DATE_MISMATCH")
        valuation_scenarios = evaluate_valuation_scenarios(**valuation_inputs)
        valuation_quote_trace = trace_valuation_quote(
            valuation=valuation_scenarios, source_annex=source_annex,
            ir_research_as_of=ir_cutoff.isoformat())
        if valuation_quote_trace["review_stage"] == "EVIDENCE_RESOLUTION":
            limits.append("The input quotation lacks a structurally supported, same-security/date/currency source link; resolve quote evidence before relying on scenario numbers.")
        else:
            limits.append("Input quotation is structurally linked to caller-reported evidence only; human source and rights review is still required.")
        limits.append("Valuation scenario arithmetic is conditional on source, security, currency and terminal assumptions; see private valuation annex. No probability-weighted Expected Return or VFV alpha certified.")
        if probability_inputs is not None:
            weighted_cashflows = calculate_weighted_cashflows(
                valuation_inputs=valuation_inputs,
                valuation_scenarios=valuation_scenarios,
                quote_trace=valuation_quote_trace,
                probability_inputs=probability_inputs)
            if weighted_cashflows["measure"] == "UNAVAILABLE":
                limits.append("Probability-weighted cash-flow arithmetic is unavailable until quotation evidence, basis and distribution assumptions are compatible.")
            else:
                limits.append("Weighted scenario cash flows are caller-assumed arithmetic, not calibrated or certified Expected Return; original price, probabilities and forward assumptions still need human review.")
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
        "strategy_policy_gate": mode_gate,
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

    if pillar_trace is not None:
        packet["pillar_trace_private"] = pillar_trace
    if mode_research_trace is not None:
        packet["mode_research_trace_private"] = mode_research_trace
    if mode_portfolio_trace is not None:
        packet["mode_portfolio_trace_private"] = mode_portfolio_trace
    if fact_alignment is not None:
        # Only the private report consumer sees structural source-use warnings.
        # The original IR capsule and its reported labels remain unchanged.
        packet["fact_source_alignment_private"] = fact_alignment
    if portfolio_room_review_private is not None:
        if pi_delta is None:
            raise ValueError("ROOM_REPORT_REQUIRES_PI_DELTA")
        packet["portfolio_room_review_private"] = portfolio_room_review_private
    if opportunity_triage is not None:
        # A private research queue is not a market screen or investment ranking.
        packet["opportunity_triage_private"] = opportunity_triage
    if macro_sector_context is not None:
        packet["macro_sector_context_private"] = macro_sector_context
    if candidate_comparison is not None:
        # Private scenario spreads never enter the institutional memory proposal.
        packet["candidate_comparison_private"] = candidate_comparison
    if fundamental_dossier is not None:
        # Only private report; the institutional memory proposal remains
        # the same non-sensitive schema without issuer financial details.
        packet["fundamental_dossier_private"] = fundamental_dossier
    if weighted_cashflows is not None:
        packet["weighted_cashflow_model_private"] = weighted_cashflows
    if valuation_quote_trace is not None:
        packet["valuation_quote_trace_private"] = valuation_quote_trace
    if valuation_scenarios is not None:
        # Private, arithmetic-only M2 packet: no probability model, net return,
        # source verification, Expected Return certification or VFV alpha.
        packet["valuation_scenarios_private"] = valuation_scenarios
    if contribution_bundle is not None:
        packet["new_contribution_summary_private"] = contribution_bundle["report_summary_private"]
    if historical_comparison is not None:
        packet["historical_research_comparison_private"] = historical_comparison
    if portfolio_observation_private is not None:
        packet["portfolio_observation_private"] = portfolio_observation_private
    if exceptional_lifecycle_review_private is not None:
        if pi_delta is None:
            raise ValueError("LIFECYCLE_REPORT_REQUIRES_PI_DELTA")
        packet["exceptional_lifecycle_review_private"] = exceptional_lifecycle_review_private
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
        "pillar_trace_private": pillar_trace,
        "mode_research_trace_private": mode_research_trace,
        "mode_portfolio_trace_private": mode_portfolio_trace,
        "opportunity_triage_private": opportunity_triage,
        "macro_sector_context_private": macro_sector_context,
        "valuation_scenarios_private": valuation_scenarios,
        "valuation_quote_trace_private": valuation_quote_trace,
        "weighted_cashflow_model_private": weighted_cashflows,
        "candidate_comparison_private": candidate_comparison,
        "fundamental_dossier_private": fundamental_dossier,
        "gross_contribution_private": contribution,
        "supplied_costs_private": costs,
        "funded_contribution_private": funded_contribution,
        "portfolio_room_status": room,
        "strategy_policy_gate": mode_gate,
        "specialist_mode_echo": {"IR": ir_mode_echo, "PI": pi_mode_echo},
        "exceptional_lifecycle_review_private": exceptional_lifecycle_review_private,
        "memory_proposal_nonprivate": memory,
        "private_research_history_proposal": private_history,
        "historical_research_comparison_private": historical_comparison,
        "github_memory_review_gate": github_review_gate,
        "handoff": "MANUAL_TRANSFER_NOT_PROJECT_AUTOMATION",
        "source_verification": "NOT_PERFORMED_BY_INTEGRATION",
    }
