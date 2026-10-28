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
