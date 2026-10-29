# PI R1 — Exceptional lifecycle review and loss-aware handoff
**Status:** candidate; no live execution, no routine buy/sell signals.

## Lifecycle under V2 High-CAGR principles
Separate five situations: (a) ordinary volatility/drawdown, (b) transient information uncertainty, (c) fundamental deterioration with possible recovery, (d) structural thesis break/permanent impairment, (e) concentration and account-specific capital destination. Price decline, scary macro headlines or elevated valuation alone are **not** sell triggers. In High-CAGR, trimming/selling is exceptional, thesis-driven, after-cost, and always decided by the CEO. Do not impose this policy on a different strategy without its approved specific rules.

A requested exceptional review needs: original IR Quality/Durability thesis and source date; current evidence and source conflict; present class/position/weight scope; same economic issuer via multiple wrappers; alternatives/opportunity cost; actual known fees, FX, taxes, account restrictions and lot data when material. Output HOLD/PAUSE_ADDS/REVIEW_TRIM/REVIEW_EXIT/UNRESOLVED as **qualitative research states**, not executable orders or automatic thresholds. Missing data never imply sell.

## Exact PI_DELTA (copy-ready handoff)
- Header: ANALYSIS_ID, TRANSFER_ID, incoming research method/instruction versions, IR_AS_OF, PI_CAPTURE_AS_OF, strategy and account scope.
- P ledger: VERIFIED_VISIBLE / UNCERTAIN / NOT_VISIBLE with sources and each field's confidence.
- ROOM: ROOM_EVIDENCE_SUPPORTED / ROOM_CONDITIONAL / ROOM_UNAVAILABLE with denominator, concentration and known overlap.
- CONTRIBUTION: user/analyst proposed %; rationale; gross arithmetic if all checks satisfied; costs/account/FX uncertainties; 100% reconciliation, conditional benchmark / temporary reserve path.
- LIFECYCLE: factual thesis change, strongest opposing case, no-sell default or exceptional review context.
- GAPS/NEXT_ACTION: one decisive user verification or source check; scope limitation; status.

Wrap the exact incoming IR_CAPSULE and decisive EVIDENCE_ANNEX in a **single FORWARD_UNCHANGED block**. PI_DELTA is appended separately, never overwrites F/K/V/S original identifiers, never invents an independent check or copies a whole inaccessible project archive. If material research or original-source locators are missing, say PACKET_INCOMPLETE, restrict impacted conclusions, and preserve defensible unrelated insights. The human carries packet PI→CC; no autonomous project transport is assumed.

## Memory / privacy / authority
The public institutional record may contain only de-identified methodology lessons and permitted source pointers, after appropriate review. Holdings, amounts, screenshots, accounts, tax lots, contribution decisions and private Broker/Blossom history stay in private storage. Never send them to Media. This module permits no broker transactions, rebalancing automation, merge, production or gate promotion.

## CEO-initiated private R1 qualitative lifecycle seam (M3 → M4)

For an **explicit High-CAGR exceptional review only**, the CEO request must include
`research_needed=true`, `portfolio_needed=true`, `ceo_initiated=true`,
`exceptional_lifecycle_review_requested=true`, plus a valid original `ir_capsule`,
dated private `observation_inputs` (or authorized Work `work_blossom_inputs`),
and completed `pi_delta` with its unchanged original IR. A completed PI return **without** the separately requested lifecycle review fails closed rather than quietly omitting the CEO's mandate; pending PI still remains pending.
Pass `lifecycle_inputs` as a **separate private analyst-supplied mapping**:
`analysis_id`, `review_as_of`, `strategy_id`, `account_scope`,
`position_p_id`, `security_id`, `thesis_event`, `analyst_reported_view`,
`original_ir_fact_ids`, `current_evidence_refs`, `fees_status`,
`fx_status`, `tax_status`, `original_thesis_private`,
`strongest_countercase_private`, `next_human_check_private`.
The exact schema is enforced in `ai_native/exceptional_lifecycle.py`; this is
not a new strategy policy. The strategy must be `high-cagr`, `High-CAGR` or `HIGH_CAGR`
matching the explicit mandate. The position must exist in the dated, private,
matching-account M3 ledger; referenced IR fact IDs must occur in the original IR.
Current evidence references, thesis, countercase and verified transaction costs
remain human responsibilities. Missing inputs remain qualified; source rights,
PIT, account/cost/tax verification and any share-class or lot details are NOT
certified. Volatility or transient uncertainty alone may never yield a
`REVIEW_TRIM` or `REVIEW_EXIT` hypothesis.

The final **private CC** report displays only the high-level thesis-event
category, *analyst-reported* hypothesis, original-IR/current-evidence link
counts, observed date, and unresolved-qualification count. It never copies
the position ID, account, security, weights, values, original thesis or
private countercase into the concise section or non-private GitHub-memory
proposal. The complete private review remains under
`exceptional_lifecycle_review_private`; `trade_authority=NONE_CEO_ONLY`
and `allocation_or_sale_proposal=NONE` even when all fields are supplied.
No routine selling, price-only signal, automation, Project invocation or
portfolio decision is created. The helper is **construction only**; synthetic
tests authored `tests.test_ai_native_exceptional_lifecycle`, runtime NOT_RUN
in connector-only environment, no real holdings/thesis acceptance.

## Conditional lifecycle → Command Center manual review queue

On a **completed, explicitly CEO-requested** High-CAGR IR→PI→CC session,
`python -m scripts.r1_manual_session_cli --output review-queue` now
emits **at most one lifecycle-specific, fixed-code human next action**
from the already prepared private `exceptional_lifecycle_review_private`.
The queue prioritizes unresolved original IR facts, missing dated current
evidence, incomplete scope, unknown fee/FX/tax effects, or a price-only/
transient uncertainty event; an otherwise complete-looking caller-reported
record still requires independent thesis and cost review. The queue
checks case/date/account alignment, original private ledger, unchanged
component record and non-escalated source/trading authority.
The default `--output status` remains redacted; the queue never copies
identifiers, account/sale amounts, the original thesis, countercase,
private locators or analyst narrative.

No lifecycle-specific task is offered before the requested PI result or
without a lifecycle review. A task is an operator instruction only:
`readiness=NOT_EVALUATED`, `trading_authority=NONE`, zero storage,
zero Project invocation, no sales signal. The finite queue cap is now
13 rather than 12 to allow one exceptional task without replacing
the existing research/portfolio checks. Synthetic tests authored in
`tests.test_ai_native_exceptional_lifecycle` and
`tests.test_ai_native_manual_review_queue`; runtime NOT_RUN in the
GitHub-only session, not authentic R1 acceptance.

## Distinct dated current-source annex for exceptional thesis evidence

An optional **private** `lifecycle_current_evidence_inputs` now carries the
already established M5 source-fusion envelope
`{analysis_id, analysis_as_of, observations}` alongside the explicit
`lifecycle_inputs` in the same CEO-requested IR+PI session. Each current
source observation uses the existing S/F fields and dates, is linked by
`observation_id` to one `current_evidence_refs` entry, and is tied by
`fact_id` to one of the original IR thesis facts selected for the review.
Case IDs, analysis cutoff, unique observation IDs, and exact reference
coverage must match. The current annex contains at most **24** dated
observations, one for each explicitly referenced ID; unmatched, duplicate
or unrequested observations are rejected. The separate current annex is **not** silently added to
or substituted for the untouched original IR `EVIDENCE_ANNEX`; a genuinely
later current observation may be evaluated against its own analysis cutoff,
never disguised as available at the original IR research date.

Without the annex, mere strings under `current_evidence_refs` produce
`CURRENT_EVIDENCE_NOT_STRUCTURALLY_LINKED`. Source-fusion flags for
uncertain rights, future observations, missing values and conflicts produce
`CURRENT_EVIDENCE_UNRESOLVED`. Either keeps the review in
`EVIDENCE_RESOLUTION_NO_ACTION` and directs the fixed-code CC queue to
`FIND_LIFECYCLE_CURRENT_EVIDENCE` before any claimed human-ready thesis
assessment. A structurally consistent annex is still
`CALLER_REPORTED_ONLY`; it does **not** certify authenticity, rights,
source timeliness, updated thesis economics, tax costs or sell justification.
The full evidence trace stays in `current_evidence_annex_private`; the
CC report shows only whether a structural link was supplied, not URLs,
identifiers or confidential details. No new data purchases, browser use,
unattended review, model policy or transaction authority.

Synthetic focused regression scenarios are authored in
`tests.test_ai_native_exceptional_lifecycle`. Python tests and authentic
portfolio/source acceptance remain `NOT_RUN` in connector-only development.
