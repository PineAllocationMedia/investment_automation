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

**Optional private personalization:** the CEO can add `investor_profile_private={"summary":"Synthetic investor: concise reports", "preferences":{"communication_style":"compact"}}`, `mandate_preferences_private={"communication_style":"detailed for this request"}`, and `mandate_prompt_private="Compare the stated research alternatives"` to the same request. M1 transfers the exact optional user text in both private specialist handoffs and resolves *presentation/research preferences only*: explicit mandate wins over profile for matching keys. The resulting `mandate_context_private` has status, provenance, `financial_policy_override=NONE`, and `method_loading=NOT_PERFORMED`. It cannot change the selected strategy, horizon, risk constraints, permitted sources or account costs, and cannot establish loaded methods. The untrusted mandate prompt is not executed or treated as system policy. The CLI `--output status` stays redacted; `handoffs`, `next-handoff` and `continuation` remain PRIVATE. Tests: `python -B -m unittest -v tests.test_ai_native_mandate_context` (synthetic only, no Project invocation).

The M1 helper references R1 research/portfolio methods **by name only**: receiving Projects must genuinely retrieve and version-check them. Research source verification, private broker/Blossom access, governed historical storage and **complete-system evaluation remain outstanding**.

**Six-mode differentiated research-question seam (2026-10-29):** The existing manual M1 handoff assembles two *non-binding, fixed* qualitative questions for IR and two for PI when one of six R1 modes is explicitly selected. This is an actual mode-conditioned research task brief, **not** a strategy-policy engine, model method, asset eligibility check, trading signal or portfolio weight. High-CAGR's candidate method reference is now present only for `high-cagr`; for Balanced, Family-Office, Rational-Aggressive, Dividend Harvester and Adaptive Browne, the handoff links the respective proposal as `strategy_design_reference_not_loaded_or_approved`, while common source-fusion and valuation references remain suggestions rather than proof of loading. `EXPLORATORY` and unrecognized labels receive generic questions with no policy document; former `income`/`capital-preservation` *mode labels* remain invalid, although those remain mandate objectives. IR/PI questions and the explicit strategy-policy gate are carried through the same private, manually transferred packets, including the unchanged original IR payload when PI follows. No sources are retrieved, no Project invoked, and no existing V2 policy changed. Focused tests: `python -B -m unittest -v tests.test_ai_native_strategy_research_brief` (synthetic; real project use unverified).

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

## Work → M3 P-ledger → PI manual fallback

On a **CEO-initiated** portfolio mandate, Work is the preferred visual acquisition surface **if a private Blossom account page is actually supported and authorized**. Use the short read-only Work task and private packet fields in `portfolio/WORK_BLOSSOM_HANDOFF_R1.md`. The handoff is manual: collect the Work-reported structured observation in a private context, invoke `prepare_work_blossom_observation(private_packet)`, and pass `prepared["observation_inputs_private"]` to `complete_manual_session(..., observation_inputs=...)` only if non-null. PI still separately supplies a `PI_DELTA` and no cross-Project invocation is implied. Private full packet and any amounts must stay out of GitHub. Work's browser cannot be driven by this Python code, and actual Blossom account/screenshot access has not been tested. Incompatible site → `UNAVAILABLE` → dated screenshot fallback, not infinite retries or false positions.

## Optional M2 source provenance annex during M7a synthesis

The private session bridge now forwards `source_evidence_inputs` only for an IR route. Provide a same-ID and same-`analysis_as_of` dictionary of source observations according to `research/SOURCE_FUSION_R1.md`. `assemble_source_fusion` groups only same-definition/same-period values, keeps GAAP and adjusted concepts distinct, does not authenticate URLs, and records `UNAVAILABLE/CONFLICTED/INCOMPLETE` claim-use states without overwriting the caller's original IR facts. M7a returns `source_evidence_annex_private` separately from the short report. Uncovered IR fact IDs, unresolved observations and noncomparable bases result in a CONDITIONAL report with a private-annex caveat. No source query or GitHub archive write is performed.

**Still missing:** authentic source browsing and actual original-document checking in the authorized IR/Work context, full method loading, external rights qualification, historical PIT tests and full integrated acceptance. A synthetic component check cannot replace those actions.

## M2 scenario-return arithmetic in the private IR → CC report

If research supplies all actual `BEAR/BASE/BULL` exit price assumptions, exact security and quote date, native currency, explicit distributions-or-UNKNOWN, supporting assumption refs, horizon and basis confirmations, an IR route may call `complete_manual_session(..., valuation_inputs=...) `. The bridge passes these only for `CC_IR_CC` or `CC_IR_PI_CC`. M7a checks exact ANALYSIS_ID and request `as_of` and emits `valuation_scenarios_private`; the compact report remains `CONDITIONAL`. It cannot turn a scenario price CAGR into a probability-weighted Expected Return or assume zero dividends. See `research/VALUATION_R1.md`; no unvalidated benchmark alpha, fees, share dilution adjustment or policy admission is implied.

**Validation scope:** 26 local targeted Python tests for the pure helper (including explicit year-end cash flows, unknown vs zero distributions, scenario/basis/date errors and IRR root). This is not proof of authentic financial data, economic normalization or full real M7a integration regression.

## Optional M3 economic issuer/sector/region look-through

After obtaining a dated, complete private P-ledger, supply `exposure_classifications` to `complete_manual_session(..., observation_inputs=..., exposure_classifications=...)`. Only the P_IDs in the visible account scope may be classified. Direct equities use one economic issuer, sector, region and dated source reference; each FNB/Fund requires its **actual dated** constituent percentages and an explicit reported complete/partial flag. If fund composition is unavailable or rights are uncertain, provide no classification: the corresponding weight stays `UNKNOWN`; do not substitute the FNB provider brand as the underlying issuer. Existing `portfolio_exposure.aggregate_portfolio_exposures` returns `portfolio_exposures_private` without copying amounts into the Markdown report or GitHub memory. Known percentages are **observed-scope-only and caller-reported**; do not infer a household exposure, true revenue-region allocation, FX risk or Portfolio Room.

This is deterministic **exposure arithmetic**, not a second holdings read, a live ETF feed, a financial recommendation or a new V1/V2 diversification policy. Preserve class dates, source refs and rights status privately. The session remains manually routed to PI; partial look-through cannot support an elevated Portfolio Room assertion.

## Conditional Portfolio Room memorandum (M3)

For a CEO-initiated `CC_IR_PI_CC` route, first obtain the **original** IR capsule, a private dated `observation_inputs` packet and supported `exposure_classifications`. Only then optionally pass `room_assessment_inputs` containing selected strategy and same request date, scope/account/horizon, candidate issuer + security class, four original F-linked `QUALITY/DURABILITY/EXPECTED_RETURN/CONFIDENCE` conclusions, four documented `CONCENTRATION/CORRELATED_DRIVERS/ALTERNATIVES/ACCOUNT_COSTS` qualitative checks and a countercase/next verification. See `portfolio/OBSERVATION_AND_ROOM_R1.md` for the precise status boundary. The private `portfolio_room_review_private` packet remains available while waiting for the manually supplied PI_DELTA; the actual report renderer never silently presents this self-reported packet as independently verified. Never copy private values, accounts or F references into public repository evidence.

`ROOM_CONDITIONAL` is the maximum review status from this construction path, **never `ROOM_EVIDENCE_SUPPORTED`**, and it gives no automatic target, trade or policy admission. The helper cannot independently verify IR sources, fund facts, fees/FX/tax, brokerage accounts or personal holdings; genuine human financial decision remains separately required. Full M7a integration verification and 36-decision acceptance are still pending.

## M2 multi-candidate scenario comparison — private optional R1 annex

For a CEO-initiated **IR-containing** route, `complete_manual_session(..., candidate_comparison_inputs=...)` forwards a same-ANALYSIS_ID, cutoff and **strategy_id** 2–6 security comparison to existing M7a. The private annex `candidate_comparison_private` reuses M2 valuation arithmetic and identifies BEAR/BASE/BULL **scenario** percentage-point differences only where both securities have the same quote date, analysis horizon, account currency and return measure. Unknown dividends, incomplete share bases, foreign currency without modeled FX and differing IRR/price-only return measures prohibit a numerical spread.

A benchmark ETF like VFV is permitted only as a **REFERENCE_ETF scenario candidate**, not as a claim of independent forward benchmark Expected Return. Research status and Portfolio Room remain self-reported/conditional; the short report stays CONDITIONAL and never inherits an automatic ranking or new-contribution allocation. Keep the candidate price/IR/PI packets private; no public evidence archive or Media transfer. See `research/CANDIDATE_COMPARISON_R1.md`. Full actual-repo regression and authentic multi-company use remain untested during construction.

## M2 source-linked issuer operating economics

For `CC_IR_CC` or `CC_IR_PI_CC`, supply `source_evidence_inputs` (the existing M2 S/F observation contract) and optionally `fundamental_inputs` with the 2-period observation ID map, one economic issuer/security, comparability assertion, and three original-F-linked qualitative drivers. M7a constructs `fundamental_dossier_private` only **after** the original source annex; it refuses standalone financial figures, conflicting securities, incompatible accounting definitions, missing fact IDs, noncomparable fiscal periods and restricted input use. The executive report stays CONDITIONAL, while organic growth, normalized owner earnings, investment Quality/Durability conclusion and Expected Return are not auto-certified. Private research evidence must remain out of GitHub archives and PAM Media. Method: `research/FUNDAMENTAL_ECONOMICS_R1.md`.


## Optional supplied-prior research comparison (R1 M4)

For a **CEO-initiated** `FOLLOWUP` with real, explicitly same-subject current IR research, `assemble_manual_run(..., historical_comparison_inputs={"prior_case": <private RESEARCH_HISTORY_R1 case or None>, "subject_id": "SYN-ISSUER", "fact_links": [{"prior_fact_id": "P-F1", "current_fact_id": "C-F1"}]})` returns `historical_research_comparison_private`. Set `request.subject_id` to the same declared subject; request and IR analyses need distinct original/current IDs and defensible dates. The direct module does not retrieve a previous case, and the M1 session route remains an explicit manual transfer.

A prior-case pointer or matching text is **not** historical source proof; a linkage is an analyst-reported pair to be independently checked for economic concept, currency, basis, units, reporting period, source rights and source authenticity. The private annex shows statuses and text deltas without claiming real-world economic change. The short report says only that the comparison is structurally conditional. Neither original prior claims nor account content can be committed to ordinary GitHub memory. No scheduled monitoring is authorized. Synthetic helper tests are not whole-system acceptance.

## M5 supplied IR-to-source status reconciliation (private)

When `source_evidence_inputs` are supplied to `assemble_manual_run`, a second private result `fact_source_alignment_private` now performs deterministic structural alignment between IR fact IDs/statuses and source-observation IDs/use statuses. It blocks analysis/AS_OF mismatches, unknown fact IDs and duplicate observation IDs. Missing coverage, incomplete, conflicted or unavailable source observations flag review, especially when IR had labeled the claim `VERIFIED`. No label is upgraded; no source or rights are authenticated; a caller-reported 'clean' record remains uncertified. The report exposes only an unspecific qualification, never detailed IDs or source locators from this private annex. Running a case without source evidence creates no false claim of alignment. Synthetic local tests are not the full integrated-system assessment.

## Optional non-ranking M2 opportunity triage (PRIVATE)

A CEO-initiated `CC_IR_CC` or `CC_IR_PI_CC` route may now carry `opportunity_triage_inputs` containing `analysis_id`, `analysis_as_of`, `strategy_id`, `universe_scope`, `universe_note` and a 1–30 item `candidates` list. This is not a new automatically sourced company screener: the caller must supply the candidate names, factual IR references, questions and risks. Each candidate contains `candidate_id`, `economic_issuer`, `instrument`, `target_type`, `origin_scope`, `research_question`, `ir_fact_ids`, `open_questions` and `known_risks`. Require an explicit `source_evidence_inputs` alongside these research inputs; missing original source observations must be represented explicitly and keep a gap.

M7a validates ID/cutoff/strategy against the original request, source observations and IR capsule and then returns `opportunity_triage_private`. The source data, candidate names, original F IDs and unsatisfied questions never enter public/institutional GitHub memory. A candidate is only in `EVIDENCE_RESOLUTION` or `HUMAN_DEEP_DIVE` *research-work* stage, in original input order; there is no score, ranking, Expected Return or investability certification. A positive-looking source observation never overrides an unresolved/conflicted one.

Without source evidence or an IR-enabled route, reject triage; without live financial disclosures or human analysis, the result is a planning queue, not a discovery result or buying advice. See [M2 opportunity triage contract](../research/OPPORTUNITY_TRIAGE_R1.md). This does not implement Project-to-Project automation or the complete 36-decision acceptance.
