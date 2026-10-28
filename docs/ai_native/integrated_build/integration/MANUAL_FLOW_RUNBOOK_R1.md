# Integrated R1 — Manual CC → IR → PI → CC assembly

**Status:** runnable **local packet-composition component**, not a deployed Project integration. **Invocation:** only after an explicit CEO research/reassessment request. There is **no weekly cadence**, background analysis, scheduled monitoring or autonomous Project-to-Project call.

## What is actually connected
`assemble_manual_run(request, ir_capsule, pi_delta=None, calculation_requests=None, contribution_inputs=None)` is a pure function in `ai_native/integrated_flow.py`.
- **M2** IR supplies original research conclusions, observed fact records, countercase, limitations and evidence statuses; this function does not generate or verify them.
- **M5** optional arithmetic requests invoke `ai_native.evidence_math.audit_calculation`, keeping `source_verification=NOT_PERFORMED`. Incompatible source facts remain unavailable, not normalized by force.
- **M3** optional, **private** PI input must carry the same `analysis_id`, dated portfolio observation and a structurally identical `forwarded_ir`; optional contribution plan calls the existing `project_gross_contribution` only on certified complete same-currency scoped inputs. Outputs remain gross and conditional.
- **M4** renders a short Markdown report and returns a noncommitted, privacy-review-required memory proposal. It does not store data.
- **M1** still requires separately installed CC/IR/PI Project settings and manual user transfers. A merged GitHub method is not a loaded Project method.

## Call shape
```python
from ai_native.integrated_flow import assemble_manual_run

request = {
    "analysis_id": "SYN-001", "as_of": "2026-10-28",
    "kind": "DECISION", "objective": "Compare synthetic businesses",
    "strategy_id": "high-cagr", "method_version": "UNKNOWN_NOT_LOADED",
}
ir = {
    "analysis_id": "SYN-001", "research_as_of": "2026-10-27",
    "decision_line": "Insufficient evidence for a price-aware decision.",
    "summary": ["A synthetic economic question remains unresolved."],
    "facts": [{"id": "F-SYN-1", "claim": "Synthetic candidate margin", "status": "INDICATIVE"}],
    "countercase": "The reported basis may be unsuitable.",
    "limitations": "No verified valuation or portfolio holdings.",
    "next_action": "Retrieve an original issuer filing.",
}
result = assemble_manual_run(request, ir)
print(result["markdown"])
# status: ASSEMBLED_COMPONENT_ONLY_NOT_END_TO_END_ACCEPTANCE
```

This synthetic example deliberately contains **no source fact certified as VERIFIED**. All real issuer source locators must be checked by IR independently; a website string does not grant provenance or source-use rights.

## Conditional PI path
Human takes the complete IR capsule to PI alongside only authorized private input; PI must return an unchanged original capsule in `pi_delta["forwarded_ir"]`, a matching analysis ID, `portfolio_as_of`, `room_status` and `summary` / `limitations`. The adapter rejects mutated or missing original IR. Contribution arithmetic requires a real, already scoped and currency-normalized dated account and proposed 100%-summing percentages. The adapter never suggests the percentages or proves the caller's coverage assertions.

Private `gross_contribution_private`, PI summaries and the final Markdown **may contain user financial data**; keep them in the private execution environment. The public GitHub memory proposal contains only a bare case ID, method version and fact IDs, and still requires review for identifying metadata and source rights **before any write**.

## User-requested follow-up
`request["kind"]="FOLLOWUP"` compares only when a previous accessible analysis is supplied/referenced with integrity. `prior_analysis_id` is optional; an absent prior record gives `BASELINE_NOT_AVAILABLE`, not invented before/after metrics. Optional `period_start`/`period_end` describe the CEO-specified study window, **not a recurring review schedule**. The current implementation does not itself retrieve or compare historical reports; IR must do the analytical comparison first.

## Trust and readiness boundaries
- Report evidence labels remain caller-supplied; M4 requires metadata for a `VERIFIED` label but cannot authenticate the actual source. M5 can validate arithmetic, not financial truth or historical PIT.
- A field called `forwarded_ir` is checked for identical structured content, not cryptographic origin or source authenticity.
- No implicit source ingestion, auto scheduling, account API or brokerage trade.
- No source-rights exception, repo write or data disclosure to Media.
- Actual cross-Project UX, method loading, real portfolio visibility, 36-decision coverage and readiness gates are **outstanding**.

**Next:** intentionally install/adopt three Project setting candidates with CEO approval, make the agreed methods genuinely accessible, then evaluate the *whole* system once assembled. The separate authorized M6 inventory/preservation scope remains open; no Mac/PC/Chromebook action is granted by this function.

## Optional bounded known-costs tally (M3 continuation)

`assemble_manual_run(..., cost_inputs=None)` now accepts a separately supplied, **private** purchase cost ledger only when `pi_delta` and `contribution_inputs` yield a gross projection. Example cost-input shape (all values synthetic and no real fee schedule implied):

```python
cost_inputs = {
    "cost_currency": "CAD", "cost_quote_as_of": "2026-10-28",
    "analysis_as_of": "2026-10-28", "funding": "FROM_CONTRIBUTION",
    "charges_by_destination": {
        "ABC:TSX": {
            "commission": {"amount_base": "5.00", "source_ref": "S-SYN-1"},
            "bid_ask_spread": {"amount_base": "0.00", "source_ref": "S-SYN-2"},
            "fx_conversion": {"amount_base": "0.00", "source_ref": "S-SYN-2"},
            "purchase_tax": {"amount_base": "0.00", "source_ref": "S-SYN-2"},
            "other_fees": {"amount_base": "0.00", "source_ref": "S-SYN-2"},
        },
        # Repeat all five explicitly evidenced entries for every positive gross destination.
    },
}
```

These `source_ref` strings are **fictional test locators**, not proof of zero fees or verified brokerage economics. `cost_inputs.analysis_as_of` must match `request.as_of`. Actual omission or unknown costs yields conditional/incomplete status, never a zero. Outputs `supplied_costs_private` and `gross_contribution_private` stay in private execution only. Cost records are not added to the GitHub memory proposal. Neither the cost tally nor the gross contribution is an executable order, after-tax return, or a complete net-weight projection.

## Optional private research-history proposal (M4 continuation)

A human-supplied `memory_inputs` object may be passed to `assemble_manual_run` *after* the private IR capsule exists, for example:

```python
memory_inputs = {
    "report_id": "R-SYN-001",
    "instruction_version": "R1",
    "recorded_at": "2026-10-28",
    "parent_report_id": None,  # optional; prior case is NOT fetched automatically
}
# result = assemble_manual_run(request, ir, memory_inputs=memory_inputs)
# Keep result["private_research_history_proposal"] in a private, authorized context.
# result["github_memory_review_gate"] always refuses publication pending human review.
```

No file is written, no remote research is retrieved, no portfolio payload is copied into any GitHub-ready output, and the helper does not claim knowledge of previously archived reports. The optional `accessible_parent` merely checks supplied ID/date; it is not a storage or authenticity check. Never paste the private proposal into repository docs or PR descriptions.

## M1 dynamic manual request assembly (construction-time component)

`ai_native.request_assembly.prepare_manual_handoffs` converts **explicit CEO-initiated** request fields into *private human-copyable* request objects. It does **not** interpret the CEO's financial objective using an AI model, access ChatGPT Project settings, load GitHub methods automatically, communicate between Projects, or initiate trades/schedules. The CEO/CC must select `research_needed` and `portfolio_needed` and confirm relevant investment strategy before using any investment policy.

```python
from ai_native.request_assembly import prepare_manual_handoffs

request = {
    "ceo_initiated": True,  # caller assertion, NOT independent CEO authentication
    "analysis_id": "SYN-REQUEST-001", "as_of": "2026-10-28",
    "kind": "DECISION", "objective": "Research a synthetic issuer",
    "research_needed": True, "portfolio_needed": True,
    "strategy_id": "EXPLORATORY",  # no implicit High-CAGR or VFV mandate
}
prepared = prepare_manual_handoffs(request)
# Human copies prepared["copy_ready_private"]["IR_REQUEST"] to IR.
# PI_REQUEST is NOT created yet: pending original IR capsule.
original_ir = {
    "analysis_id": "SYN-REQUEST-001", "research_as_of": "2026-10-28",
    "evidence_annex": {"S": [], "F": [], "K": [], "V": []},
    "facts": [],  # synthetic structural illustration, NOT real-source research
}
follow_on = prepare_manual_handoffs(request, ir_capsule=original_ir)
# Human copies follow_on["copy_ready_private"]["PI_REQUEST"] to PI.
# It has ONE unchanged original_ir under FORWARD_UNCHANGED.
```

The copy-ready strings are **private**: do not put actual holdings, account information or source-restricted content in GitHub, PRs, public tools or PAM Media. `portfolio_context`, if supplied by an authorized human, must carry an actually dated and scoped observation; this helper labels it USER_SUPPLIED_NOT_VERIFIED_BY_ASSEMBLER. A missing portfolio view is NOT_SUPPLIED, not a zero position. The caller must manually deliver and verify the actual Project response; the returned transfer IDs and JSON are not proof of communication. Existing `ai_native.integrated_flow.assemble_manual_run` remains the later *already-researched* packet assembler, not an automatic part of this preliminary request-construction function.

The M1 helper references R1 research/portfolio methods **by name only**: receiving Projects must genuinely retrieve and version-check them. Research source verification, private broker/Blossom access, governed historical storage and **complete-system evaluation remain outstanding**.

## M1 → M7a unified manual session bridge (construction addition)

`ai_native.session_bridge.complete_manual_session(request, *, ir_capsule=None, pi_delta=None, portfolio_context=None, calculation_requests=None, contribution_inputs=None, cost_inputs=None, memory_inputs=None)` composes **existing** `request_assembly.prepare_manual_handoffs` and `integrated_flow.assemble_manual_run` rather than manually duplicating the request envelope for a final report. Inputs remain PRIVATE and user-carried. It never calls ChatGPT Projects or verifies sources or account access.

- `CC_DIRECT`: returns `CC_DIRECT_NO_SPECIALIST_REPORT_REQUIRED` and no fabricated research report; CC handles simple supported work directly.
- `CC_IR_CC`: first returns a copy-ready IR_REQUEST with `AWAITING_MANUAL_IR_CAPSULE`; once the CEO manually supplies the original IR capsule, constructs the M7a private report using the same request ID, date, supplied strategy and actual/UNKNOWN IR method version.
- `CC_IR_PI_CC`: stops at IR, then produces a single PI_REQUEST containing the original `FORWARD_UNCHANGED` IR package, and finally delegates to the existing M7a report only when the original PI_DELTA arrives. M7a checks the forwarded IR capsule and date/identity compatibility. Optional gross contributions, supplied-cost totals, arithmetic requests and memory proposals remain subject to **existing M7a prerequisites**, do not run before PI.
- `CC_PI_CC`: waits for the manually supplied PI_DELTA; after validating same ANALYSIS_ID, dated observation not after the request cutoff, and known room status, produces a **conditional PI-reported summary only**, no issuer facts, net allocation, authenticated holdings or independent trade conclusion. PI-only capital arithmetic and memory persistence are **not** implemented by this bridge.

All statuses remain `*_PENDING`, `PI_ONLY_CONDITIONAL_REPORT_ASSEMBLED` or `M7A_COMPONENT_ASSEMBLED_NOT_END_TO_END_ACCEPTANCE`. `final_report_private`, `integrated_private`, `pi_delta_private` and `handoffs_private` must never be copied into public GitHub or PAM Media. The function has no storage, scheduler, Project API, source authentication or production authority. A prior Report ID does not load historical evidence. The `copy_ready_private` payload is manually pasted only into an authorized receiving Project.

**Validation scope:** 18 new targeted local seam tests with a *test double* standing in for the M7a integration/reporter interface, not a complete-repo regression. Static scope and exact tested Git blobs should be checked before review. The comprehensive integrated acceptance is still intentionally deferred until all 36 design decisions have real components or CEO-accepted fallbacks.

## M3 private P-ledger input in the unified session bridge

The optional `complete_manual_session(..., observation_inputs=...)` accepts a private dictionary using `prepare_observation_ledger`'s keyword contract **only for routes including PI**. It is useful while waiting for a human-supplied PI_DELTA and preserves the normalized observation as `portfolio_observation_private` without printing account values into the report or public memory. The `analysis_id`, `analysis_as_of` and any subsequently supplied PI `portfolio_as_of` must match; otherwise the bridge refuses the comparison. The bridge also rejects an incoming `ROOM_EVIDENCE_SUPPORTED` assertion when the optional P-ledger cannot establish complete scoped weights. Such numerical weights do not, on their own, justify `ROOM_EVIDENCE_SUPPORTED` even when calculable; PI still owns the substantive room argument.

Inputs are structured user transcriptions, **not** automated screenshot processing or verified Blossom navigation. `source_access_confirmed_by_caller=true` is a caller assertion, not an independent capability check. For an incomplete/cropped public/private view or unknown cash/FX, retain the `P` records and `ROOM_UNAVAILABLE`, never assume missing values are zero. Keep all actual P records, account names, timestamps and holdings private; GitHub examples/tests contain synthetic identifiers only.

**Construction-only checks:** 19 helper tests + 7 added bridge tests + 18 existing local bridge tests pass with M7a/reporting stubs. Full repository regression, genuine screenshot parsing, authorized live Blossom access, cross-Project manual usage and final system-wide acceptance remain untested.
