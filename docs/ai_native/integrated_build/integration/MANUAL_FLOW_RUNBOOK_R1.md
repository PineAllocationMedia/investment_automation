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

**Mode-echo parity on manual specialist returns (2026-10-29):** If an explicitly CEO-initiated IR_CAPSULE or PI_DELTA voluntarily includes `strategy_id`, it must match the requested `strategy_id` (case-insensitive label match); a contradiction or invalid echo is rejected rather than reused across High-CAGR/Balanced/etc. The same guard is applied in M1 forwarding, standalone M7a and the PI-only session route. Legacy capsules with no `strategy_id` still work but receive `NOT_ECHOED_MODE_NOT_VERIFIED` and CONDITIONAL report limitations, never an invented confirmed mode. Matched echoes are explicitly `MATCHED_SELF_REPORTED_NOT_AUTHENTICATED`, **not** evidence of Project identity, method loading, CEO approval, factual correctness or sourced investment policy. Optional specialist echo never overrides the request; original IR remains unchanged within PI forwarding. Tests: `python -B -m unittest -v tests.test_ai_native_strategy_return_parity` (synthetic; no live Project handoff).

**Unfilled IR/PI mode-response drafts:** Each copy-ready specialist request now carries `mode_question_response_template_private`, containing an inert draft of `IR_CAPSULE.MODE_RESEARCH_RESPONSES` or `PI_DELTA.MODE_PORTFOLIO_RESPONSES`. The actual `research_as_of` / `portfolio_as_of` is deliberately `null` until the receiving specialist observes and supplies it; every question is `UNKNOWN` with zero original-fact/P-ledger links. The specialist must fill the actual date, link only existing original IR fact IDs or actual dated PRIVATE P_IDs, keep unsupported answers UNKNOWN, and return only the completed **inner** field inside the original unchanged IR_CAPSULE or PI_DELTA. These templates **fail validation if copied back untouched**; they cannot manufacture sources, holdings, method loading, strategy policy or approvals. The private handoff remains manual and user-initiated. New repo integration tests are authored but NOT_RUN; a bounded pure-template check is separate from actual Project acceptance.

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

## Inert on-demand new-case template (2026-10-29)

From a trusted checkout run `python -B -m scripts.r1_manual_session_cli --output request-template` **without stdin**. This emits exactly one portable JSON object with a `request` skeleton for the existing CC route. It intentionally has `ceo_initiated=false`, no date/ID/objective/selected strategy, and `research_needed=null` / `portfolio_needed=null`. All fee, FX, broker and tax facts remain `UNKNOWN`; no personal/portfolio/source data are read, generated, stored, or sent.

In a **private** terminal, the human supplies a new analysis ID, current as-of date, explicit decision or follow-up kind, objective, selected strategy, scope and risk constraints, **both** actual route booleans, and known account/cost facts; set `ceo_initiated=true` **only for a genuinely CEO-requested case**. For a historical follow-up include its valid `subject_id` and `prior_analysis_id` and use the existing sealed/manual comparison path when applicable. Then feed the completed JSON to the existing `--output guided-operator` (or `status` for a redacted preflight). The original request/session gate rejects an unedited template. This is a UX helper, not strategy-policy approval, a source, Project invocation, authentication, archive, weekly schedule or acceptance evidence. Use `python -B -m unittest -v tests.test_ai_native_r1_start_template tests.test_ai_native_r1_manual_cli` from an authentic checkout to verify it.

## Explicit private operator packet for one manual session (2026-10-29)

`python -m scripts.r1_manual_session_cli --output operator-packet` accepts the **same CEO-initiated JSON on stdin** as the existing CLI. This optional PRIVATE-only output returns the existing redacted `session` status, existing `review_queue`, and either the existing ready-to-copy `continuation_private` or the already-generated conditional `report_private` (never both). The continuation preserves the independently supplied original IR package for PI parity, keeps `specialist_result=null` until a human supplies a real specialist return and never sends a Project message. When a Work view is unavailable, the review queue requests the authorized screenshot fallback and there is no imaginary PI result or handoff.

This replaces multiple separate CLI invocations for one already validated manual case without introducing a new financial method, automatic cross-Project invocation, scheduling, record storage, source authentication, readiness or trading authority. Default `--output status` stays redacted; the explicitly requested operator packet can contain sensitive account, source or research content and belongs only in an authorized private terminal—not GitHub, logs or PAM Media. Output size and error text are bounded; `private-case` remains a separate expressly requested manual archive proposal. Synthetic round-trip, pi-only, direct, unavailable-Work and parity tests are authored, not accepted live Project evidence.

## Pinned GitHub method references in real manual specialist handoffs (2026-10-29)

When the CEO initiates an IR and/or PI request, the existing M1 `IR_REQUEST` / `PI_REQUEST` JSON now includes a `pinned_method_references_not_loaded_or_approved` manifest. The manifest carries **existing method file paths and Git blob IDs**, anchored to a verified historical V2 commit; a receiving human/Project can use these exact repository identities to locate and independently compare the intended materials. Two core IR references (`SOURCE_FUSION_R1`, `VALUATION_R1`), three core PI references (`OBSERVATION_AND_ROOM_R1`, `CONTRIBUTIONS_AND_COSTS_R1`, `LIFECYCLE_AND_HANDOFF_R1`) and the single user-selected six-mode design reference are included only in the relevant specialist route; exploratory work has no strategy-policy design file.

A SHA pin proves only the identity of the version present in GitHub at the recorded reference commit, **not** that a ChatGPT Project retrieved, saw, loaded, followed or executed the method. Every entry retains `loading_status=NOT_VERIFIED_BY_ASSEMBLER`, and the session's method-load verification remains `NOT_PERFORMED`. For High-CAGR, the reference is limited to its existing V2 scope. All other five mode documents remain **unapproved policy proposals**, not allocation/selling/band/asset/benchmark authority; no numeric policy is introduced. No arbitrary path, remote URL, source rights, method authority or Project capability is trusted from caller text. When a source file changes, the pins require explicit reviewed synchronization; the immutable historical reference is not automatically updated.

The unchanged original IR capsule is forwarded to PI exactly as before, and the existing PRIVATE operator packet transports the newly pinned handoffs. No file contents, portfolio data or private case are written to GitHub by this helper. No autonomous Project invocation, method fetch or source authenticity test is added. Actual receiving-Project document loading and agreement with these pinned blobs remains a manual **unverified capability**, to be assessed at the single integrated acceptance.

## Offline Git-verified complete method handoff (2026-10-29 construction)

After the user initiates an IR/PI mandate, run `python -m scripts.r1_manual_session_cli --output method-handoff` with the **same private JSON input** as the R1 operator packet. Unlike the lightweight method pointers added earlier, this optional read-only mode composes the **exact next IR_REQUEST or PI_REQUEST and re-entry continuation** with the full *existing* IR/PI method document text for that selected route. A human can copy the private handoff to the authorized receiving Project; no automatic chat/Project call, data source access, file write or record archive occurs.

The helper `ai_native.method_handoff_bundle.prepare_verified_method_handoff` only reads the fixed, repository-relative paths already whitelisted by `method_manifest.py`; it rejects any manifest mismatch, missing file, disallowed path, oversized file, or **local Git blob mismatch** before returning *any* partial bundle. The Git SHA check is deterministic on raw UTF-8 bytes (`blob <size>\\0<bytes>`), not evidence of independent document-content accuracy, method approval, Project reading or execution. A stale pin detected in the merged PR #330 manifest for `portfolio/CONTRIBUTIONS_AND_COSTS_R1.md` is refreshed here to the exact current canonical blob, with all 11 pinned documents checked. Future edits to pinned method documents intentionally block the method handoff until an explicit reviewed pin refresh; the regular default redacted `status` continues to work.

`method-handoff` is **PRIVATE**, potentially containing the user's mandate/account, the unchanged original IR capsule, and complete internal method text. Use only in a protected operator terminal or an authorized receiving Project, never GitHub, PAM Media or public logs. IR remains first on combined IR+PI requests; an unavailable Work portfolio view yields a screenshot fallback, **not** a false PI method/portfolio transfer; terminal routes have no further method handoff. The five non-High-CAGR mode documents retain `UNAPPROVED_R1_STRATEGY_POLICY_PROPOSAL`, while High-CAGR remains confined to the existing V2 scope. New tests verify all pinned local documents, IR/PI full-content bundles, tampered file and manifest rejection, and the manual CLI; live Project method loading, approved six-mode policies and comprehensive R1 acceptance remain **NOT_RUN / UNVERIFIED**.

## Explicit manual private-case copy integrity and inert follow-up (2026-10-29)

`python -m scripts.r1_manual_session_cli --output private-case-envelope` takes the same **already completed CEO-initiated private session and explicit `memory_inputs`** as `--output private-case`. It returns a strictly PRIVATE JSON envelope holding the same `RESEARCH_HISTORY_R1` proposal and a reproducible `SHA256_CANONICAL_JSON_R1` checksum of its canonical JSON bytes. The operator can choose a **separately approved private protected destination** and save the whole JSON manually; this command NEVER chooses a location, writes a file, schedules work, uploads to GitHub, stores account values or asserts that any actual archive exists.

For a future **explicitly user-requested** research follow-up, re-supply the private JSON as `{"private_case_envelope": <the saved private envelope>}` over stdin to `--output sealed-followup-draft`. The CLI first rejects malformed, changed or wrong-class envelopes and checks the retained SHA-256. Only then does it reuse `prepare_explicit_followup_draft` to produce the same **inert template** as `--output followup-draft`: `ceo_initiated=false`, no current date/ID/objective, no inherited holdings/costs. The CEO must review, provide current evidence and explicitly initiate any next request. The original `--output private-case` / `--output followup-draft` remain compatible and unchanged for unwrapped cases.

**Security precision:** SHA-256 is an **unkeyed accidental-corruption check**, not encryption, access control, secure storage, timestamping, provenance certification, tamper-resistant authentication or proof the record truly belongs to the user. Someone who modifies a record can recompute its hash. The entire envelope contains potentially sensitive original account/research details; keep it in a separately protected private location chosen by the CEO, NEVER in GitHub, logs, Media or public messages. No external data, payments, cryptographic keys or device inventory are involved. A stored-copy/restore exercise and independent security review remain unverified; synthetic round-trip, corruption and privacy tests are authored but do not constitute end-to-end acceptance.

## Copy-ready specialist prompt with verified source texts — R1 manual UX (2026-10-29)

The explicit, private CLI command `python -m scripts.r1_manual_session_cli --output specialist-prompt` accepts the **same CEO-initiated private JSON** as `--output method-handoff`. It reuses the *existing* next `IR_REQUEST` or `PI_REQUEST` and its full locally Git-blob-verified method texts, then produces **one plain-text prompt ready for the human to copy into the authorized IR or PI Project**. No separate specialist-specific request construction, source lookup or policy engine is introduced. The previous `method-handoff` JSON remains unchanged.

The ready-to-paste text contains only the **current receiving specialist's** request JSON, method paths, exact Git blob identities, content and a clear request for the standard IR_CAPSULE / PI_DELTA return JSON. If PI receives the original IR, the return contract requires `FORWARD_UNCHANGED` exactly as received; a PI-only case must not invent research. **Crucially, the full CC-only `resume_input` and operator continuation are NOT included in the specialist text**, reducing accidental disclosure of private CC-only metadata. On return, the operator continues using their separately retained `operator-packet` / `continuation` to supply the actual specialist envelope for the final CC report. The tool never sends anything to the Project, does not verify an actual method load, and does not bypass the live project's instructions.

The renderer rechecks the exact pinned manifest and raw Git blob hash of every method document before constructing the prompt. A tampered source, wrong specialist, unsupported mode or mismatched claim fails closed without printing partial research or secrets. Sensitive account/mandate fields **required by the intended specialist request** may still be present in its JSON: copy only to an authorized PRIVATE Project, never to GitHub, PAM Media or a public chat. Five R1 strategy-policy documents remain **unapproved proposals** and must not silently govern investment allocations; High-CAGR remains V2 scope-only. No automatic Projects, trading, archive or recurring research; genuine two-Project receiving behavior and user effort remain unverified pending actual use. Focused synthetic code-level and CLI tests are authored, not equivalent to authentic acceptance.

## Copy-back of specialist JSON without editing the CC re-entry packet (2026-10-29)

After an explicit `--output operator-packet` request, keep the returned `continuation_private` **in a protected private context**. Send only the separate `--output specialist-prompt` text to the authorized IR/PI Project. Once that Project returns its actual, original JSON object (`{"IR_CAPSULE": {...}}`, or `{"PI_DELTA": {...}, "FORWARD_UNCHANGED": <unchanged original IR capsule>}`), the operator can run `--output resume-operator` with the private input envelope `{"continuation_private": <the saved continuation>, "specialist_result": <the original specialist return>}`. There is **no need to edit the nested `resume_input.specialist_result=null` placeholder by hand**.

The adapter re-evaluates the exact unsatisfied request from the saved CC continuation, regenerates its current IR/PI handoff, and demands full equality with the provided continuation before incorporating the new specialist return. It verifies stage order, rejects PI replies at an IR stage, requires the original independent IR to be faithfully forwarded by PI, and uses the existing `evaluate`, `complete_manual_session` and `_private_operator_packet` methods for all checks and the resulting next handoff/report. If IR is complete but PI is still needed, the result contains the next **PI** continuation; after actual PI return, it contains the existing conditional CC report. A PI-only flow has no invented IR; terminal/direct/screenshot-fallback routes cannot be resumed as fictitious Project responses. The default `status` stays redacted.

This is **one user-initiated manual reply ingestion**, not automatic ChatGPT Project-to-Project invocation, live Project identity verification, source authentication, financial-policy approval, scheduled research or private data storage. Continuations, specialist results, and `resume-operator` output are PRIVATE; never paste a CC continuation or private account context into GitHub, public chats or PAM Media. Equality with a reproducible continuation protects against accidental stage/case mistakes, **not malicious re-authoring of both a continuation and its contents**. A real two-Project round trip and human-time measurement remain unverified. Synthetic CLI tests are authored; R1 integrated acceptance remains pending.

## Repair of stale source-fusion method pin and no-private-input local preflight (2026-10-29)

The merged PR #335 changed the candidate method file `research/SOURCE_FUSION_R1.md` to describe the source chronology checks, **without updating its SHA in `ai_native/method_manifest.py`**. All manual IR requests via `--output method-handoff` or `--output specialist-prompt` consequently reject a current checkout with `METHOD_HANDOFF_LOCAL_BLOB_MISMATCH`; rejecting is correct, but causes a real workflow interruption. This change explicitly refreshes that pin to the exact verified Git blob `c1d1400015c29cc9426e34e9a6edf7e79354f9e1` at the reviewed canonical V2 parent commit. All **11** pinned documents must match that repository snapshot; this is a reference correction, not new policy or method acceptance.

Before sending a sensitive research request, an operator may now execute `python -B -m scripts.r1_method_preflight` in an authorized local repository checkout. The output is a **read-only, content-free** JSON report with only fixed repository-relative method paths, expected Git hashes, `MATCHED_EXPECTED_GIT_BLOB` or `BLOCKED` and a short reason code; exit `0` means all current on-disk bytes match their pins, exit `3` means at least one method is missing or does not match. It accepts no CEO mandate or account data, makes no external requests and neither loads ChatGPT Projects nor changes files. A blocked result requires an explicit reviewed pin update or a clean authorized checkout, **not** bypassing the SHA check or relabelling an unapproved R1 policy proposal as approved.

This preflight checks **only local immutable-looking source-file identities**, not actual method reading by a ChatGPT Project, source truth, market data licensing, portfolio authenticity, comprehensive financial-function tests or production readiness. The existing strict fail-closed IR/PI transfers remain unchanged. Local-source code tests are authored and require an actual Python run; GitHub Actions has been failing early without job steps, so no CI success is inferred.

## R1 six-strategy method and mandate binding on actual IR/PI copy transfers (2026-10-29)

An exact matching Git SHA is necessary but not sufficient for a correct specialist transfer: a real, internally consistent `HIGH_CAGR_METHOD_R1.md` blob must **not** accompany a `balanced` research request merely because its document exists in the repository. Both `prepare_verified_method_handoff` and the final `render_manual_specialist_prompt` now re-derive the selected method document, qualitative IR/PI question list and reported policy authority **from the saved original CC request's `strategy_id`**, using the existing `prepare_strategy_research_brief` and `prepare_method_manifest`. They require exact agreement with the current `IR_REQUEST` or `PI_REQUEST`, including request analysis ID, date, kind and objective, instead of trusting the packet's choice of strategy document.

This guards against accidentally combining another strategy's method, unapproved policy claims or High-CAGR-specific questions with the original mandate, including a **coordinated but self-consistent path+SHA substitution**. A failure blocks the entire private handoff or text render without printing the mandate or method content. Exploratory legacy requests without an explicit `strategy_id` still default to unapproved exploratory research, as before. The method remains **not loaded** in the actual Project; the five non-High-CAGR proposals remain **unapproved**, and High-CAGR retains only its pre-existing scoped V2 policy. This is a stateless, local consistency check, **not** authenticated CEO identity, approval, market/source verification, live transfer or trade authority. Six-mode-by-specialist tests and adversarial cross-policy tests are authored, not a completed authentic Project acceptance.

## One-call private guided R1 operator, initial + specialist re-entry (2026-10-29)

Run `python -B -m scripts.r1_manual_session_cli --output guided-operator` with an explicit private user-initiated R1 request. This **combines the existing** `operator-packet` and `specialist-prompt` into a **single PRIVATE JSON response** with `operator_packet_private`, `specialist_prompt_private`, `specialist_step` and `copy_to_specialist`. It uses the exact current IR or PI transfer and Git-verified method texts; no additional investment methods or policy are added. The human must paste **ONLY the string in `specialist_prompt_private`** into the authorized recipient Project; keep the CC-only `operator_packet_private.continuation_private` separately protected. Do NOT paste the whole combined JSON into IR/PI.

For the next explicit user-driven step, use the SAME `--output guided-operator` command with `{"continuation_private": <the prior operator_packet_private.continuation_private>, "specialist_result": <the original IR or PI return JSON>}`. The established strict resume replay validates the original mandate, stage, unchanged independent IR on PI returns and actual specialist envelope, then produces the **next PI specialist prompt** or the **conditional final CC report** within the operator packet. PI-only and direct routes are supported without invented research; unavailable Work visual capture yields only a screenshot fallback, never a false PI prompt. Build the whole output before any private text is printed; any method-pin, six-mode or payload error returns only a fixed generic code/message.

This improves **manual orchestration usability** but does **not** prove method loading or actual use in ChatGPT Projects, portfolio/source authenticity, strategy approval, private archive retention, subscription access, trading, automatic cross-Project calls, time savings or the comprehensive 36-decision acceptance. The operator alone controls every transfer, protects private account contents and initiates every research request. Older CLI commands remain supported. The focused synthetic CLI test cases are authored and must be executed on an authorized checkout; no automatic work is scheduled.

## Separate CC source review versus original IR research chronology (2026-10-29)

An `EVIDENCE_ANNEX` **embedded inside the original IR_CAPSULE** must not claim an observation occurring after that capsule's `research_as_of`: this remains a **hard refusal** (`IR_SOURCE_OBSERVED_AFTER_RESEARCH_AS_OF`). However, the older separate `source_evidence_inputs` option is an **explicit CC-side supplemental review** at the request's analysis cutoff. It may legitimately contain newly gathered information after the specialist's earlier research date. Treating these inputs as interchangeable IR history would cause point-in-time contamination; rejecting every later CC observation would instead discard valid current investigation.

The integrated assembler now records `ir_timeline_relation=POST_IR_CC_REVIEW_ONLY` and the affected `post_ir_observation_ids_private` in its **private source annex** when a separate source observation postdates original IR research. It keeps the source observation and existing provenance/rights flags intact but forces **CONDITIONAL** reporting and an explicit human-facing limitation: **current CC sources cannot retroactively substantiate what original IR knew at its prior research cutoff**. An explicit new IR research request is needed if an updated IR view is desired. If none postdate research, `ir_timeline_relation=NO_POST_IR_OBSERVATIONS_REPORTED`, with no extra warning. This does not authenticate source dates, grant source rights, upgrade reported IR fact statuses or change raw IR/PI forwarding. Private observation IDs are not published to GitHub or unredacted status. Both routes and the exact boundary are covered by synthetic tests (authored; Python execution NOT_RUN).

## Source-fact PIT alignment across IR and later CC review (2026-10-29)

The newer source-reconciliation annotation from PR #339 must also reach **per-fact** evidence checks: a later separately supplied CC source is NOT evidence the earlier IR specialist knew that fact. In the current M7a call to `align_ir_facts_to_sources`, the original `IR_CAPSULE.research_as_of` is now passed explicitly. Each observation later than that original research date adds private review flag `CC_SOURCE_POSTDATES_ORIGINAL_IR` to its original IR fact, even when another older clean source exists; an IR fact reported `VERIFIED` cannot be treated as structurally corroborated **solely** by new CC observations. The report retains the original reported IR label but displays the human review flag, remains `CONDITIONAL` for later sources, and never upgrades evidence/source authentication.

Direct legacy alignment callers without an IR research cutoff remain structurally backward-compatible. Invalid source dates are refused when a cutoff is supplied; equal cutoff dates are not flagged. Embedded IR evidence observed after original IR research cutoff remains a hard refusal, as previously. No Project access, source retrieval, policy approval, trading or independent PIT certification occurs. Focused synthetic tests added; canonical Python execution still required.

## PIT continuity into M2 fundamentals and opportunity triage (2026-10-29)

The original dated `IR_CAPSULE.research_as_of` is passed from the existing manual M7a assembly into the existing M2 **fundamental dossier** and **opportunity triage**. Newly observed CC evidence is preserved as private current review material, but must not be represented as original IR-era source support. A fundamental metric period-pair using even one post-IR observation is marked `UNAVAILABLE` for original-IR descriptive arithmetic, with reason `SOURCE_OBSERVED_AFTER_ORIGINAL_IR`; independent earlier-source metric pairs remain only *conditional descriptive* observations. A candidate with any post-IR CC source link stays in `EVIDENCE_RESOLUTION` (`CC_SOURCE_POSTDATES_ORIGINAL_IR`), not `HUMAN_DEEP_DIVE`. To use new evidence as original IR research, the CEO must initiate a new dated mandate.

Direct adapter callers preserve their existing behavior when the optional IR cutoff is not provided. With the cutoff present, missing, invalid or after-analysis observation dates fail closed. Same-day evidence is only structurally eligible and does not imply authenticity, rights certification, systematic global screening, quantitative investment ranking or trade authority. No private source or portfolio values enter the nonprivate case-memory proposal; no Project automation or external data retrieval is introduced. Synthetic regression tests written; full canonical Python execution NOT_RUN.

## M5 arithmetic results in the private CEO report (2026-10-29)

The manual R1 integrated assembler now passes the **actual M5 `audit_calculation` output** through the existing private CC reporting packet as `calculation_checks_private`, alongside its existing separate `calculation_checks` annex. M4 displays up to eight structural results in a compact section (operating margin, YoY revenue growth, and CFO less PPE outflow proxy), with an explicit count of additional checks in the private annex. Unsupported/uncertain results appear as `UNAVAILABLE` with machine-generated reason codes; formal arithmetic displays the computed number and a source-rights caveat when one exists.

These are **current-observation calculations**, not retroactive source evidence available to the original IR capsule. The report never upgrades facts, certifies source authenticity, substitutes normalized owner earnings or Expected Return, or treats M5 results as decision-grade. Raw source locators, original fact IDs and input financial values do not appear in the M5 subsection or the nonprivate GitHub memory proposal; the complete private annex stays with the CEO. The report rejects forged certification/authority flags, nonfinite or malformed displayed numbers, unsupported operations, wrong units and injected reason codes. No default recurring work or Project automation is added. Focused synthetic tests authored; canonical checkout Python and live source acceptance NOT_RUN.

## Source chronology for macro/sector context in the R1 private flow (2026-10-29)

The M2 macro/sector stage now follows the same source chronology as original-IR fundamentals and opportunity triage. A source **first observed by CC after** the unchanged `IR_CAPSULE.research_as_of` remains available in the private CC evidence annex, but its linked driver receives `CC_SOURCE_POSTDATES_ORIGINAL_IR` and stays in `EVIDENCE_RESOLUTION` rather than `HUMAN_CAUSAL_REVIEW`. This avoids failing the entire current CC report merely because a later externally supplied observation is present; a fresh CEO-initiated IR session is required to establish new original IR research. An observation at the original IR research date remains structurally reviewable but is never authenticated or used to predict timing/returns.

The original hard refusal is retained for future-dated observations **embedded inside the original IR capsule**, since that would misrepresent what IR knew. Direct standalone `prepare_macro_sector_context` callers without the optional cutoff keep their earlier behavior; the connected manual R1 flow always supplies the original cutoff. No portfolio trades, financial policy changes, source retrieval or Project automation. Focused synthetic tests authored, canonical Python tests NOT_RUN.

## Direct, CEO-initiated follow-up from a manually retained sealed case (2026-10-29)

A CEO who has **manually** kept the PRIVATE output of `--output private-case-envelope` can now begin a **new** research comparison without manually extracting and transplanting its historical case JSON. In a PRIVATE terminal, run `python -m scripts.r1_manual_session_cli --output sealed-followup-operator` and pass exactly:

```json
{
  "private_case_envelope": {"...": "the unchanged saved private-case-envelope"},
  "session": {
    "request": {
      "ceo_initiated": true, "research_needed": true,
      "portfolio_needed": false, "kind": "FOLLOWUP",
      "analysis_id": "NEW-CASE-ID", "as_of": "YYYY-MM-DD",
      "subject_id": "SAME-SUBJECT-ID",
      "prior_analysis_id": "ORIGINAL-CASE-ID",
      "objective": "CEO's new research question",
      "strategy_id": "CURRENT-CEO-SELECTED-STRATEGY"
    }
  },
  "fact_links": [
    {"prior_fact_id": "OLD-F-ID", "current_fact_id": "NEW-F-ID"}
  ]
}
```

The example shows core fields; the normal session contract still requires all applicable method/mandate inputs and existing validations. `fact_links` may be an empty list pending a later explicitly reviewed comparison. The command verifies the unkeyed SHA-256 copy, reuses the existing private-case structural/date/fact gates, requires a fresh CEO-initiated FOLLOWUP mandate, a *distinct* new analysis ID, the same original subject and exact prior analysis ID, and a current research date not earlier than the saved record. An already received new IR capsule may be supplied inside `session`; otherwise, the existing operator packet contains the **one** next IR handoff. Submit the returned `continuation_private` plus a separately received IR response to `--output resume-operator` as before. The historical private case remains in that CC continuation; **do not forward the continuation to IR**. Only `next_handoff.IR_REQUEST` goes to the IR Project.

This reuses existing original-IR/PI/evidence/report safeguards and permits the existing analyst-only `compare_supplied_cases` result in the CEO's private report. The stored prior case is a *comparison baseline*, NOT a copied current request: old holdings, broker/account data, costs, old IR conclusions or rights do not become current facts or transfer to the new IR handoff. The command makes no Project call, storage write, scheduled task, GitHub private-record upload or trade. A matching **unkeyed** digest shows retained-copy consistency only, not ownership, source authenticity, storage encryption, backup, or restoration reliability. Approved real private archive location, retention and disaster recovery are still unverified. Python tests authored NOT_RUN.

### One guided private follow-up without an intermediate manual prompt assembly

Use the **same unchanged** sealed-case input JSON shown above with `--output guided-operator` instead of `--output sealed-followup-operator`. The existing checksum-matched historical recovery and explicit fresh CEO FOLLOWUP mandate gates run first. The result combines the existing PRIVATE operator packet with the **actual copy-ready IR prompt containing pinned local method text**. It returns `operator_packet_private.manual_copy_integrity=SHA256_MATCHED_RETAINED_COPY_ONLY` and `record_authenticity=NOT_ESTABLISHED`; neither is proof of owner authenticity, archive protection or source verification. Only copy `specialist_prompt_private` to IR; the historical comparison baseline, prior account fields and current CC re-entry state stay inside `operator_packet_private.continuation_private` under private operator control. No previous portfolio/fees are inherited.

For actual IR and optional PI returns, submit the saved `operator_packet_private.continuation_private` and the specialist's original JSON to **the same** `--output guided-operator` in the usual `{"continuation_private": ..., "specialist_result": ...}` shape. The existing replay/unchanged-IR and private report checks handle both stages. If the new IR capsule was already supplied in the fresh session, the guided route produces the conditional comparison report without fabricating a specialist prompt. Tampering, contradictory request/method scope, stale dates or changed handoff are refused without printing private source values. No Projects are invoked, historical archive is loaded, or research is scheduled. Regression tests are synthetic and must still be run from an authentic checkout; the integrated acceptance remains pending.

## Request-only intake review before the manual guided operator (2026-10-29)

The new `python -B -m scripts.r1_manual_session_cli --output intake-review` consumes exactly one **private** `{"request": {...}}` envelope from `--output request-template` after the CEO begins filling it. Unlike `--output status`, it deliberately accepts an **incomplete, inactive** draft and lists only **fixed schema field names** in `missing_or_invalid_fields`, plus `human_review_codes` for missing horizon, universe, risk limits, account/broker/FX/tax/commission context, policy gates, historical comparison baseline and real Project-method loading. It never reproduces private field contents, account names, source links or financial figures, and it never writes a file. Non-request annexes or duplicate JSON keys are refused to avoid accidental disclosure. A `ceo_initiated=false` template is always `INTAKE_INCOMPLETE_NOT_SENT`.

Only when essential request fields are filled, date/kind/route flags are structurally valid and the **existing** `prepare_manual_handoffs` contract accepts the request can the helper show `INTAKE_STRUCTURALLY_READY_NOT_SENT` with the existing route. That does **not** authenticate the CEO's assertion, approve non-High-CAGR strategy policies, check private screenshot coverage, load methods or start research; `UNKNOWN` account cost data remain visible human-review flags. The authorized person must separately invoke `--output guided-operator` with the original complete private request, manually transfer the returned specialist prompt and supply actual IR/PI replies. The intake-only view has no authority to choose a strategy or edit the template. Synthetic CLI tests added; actual checkout tests and live three-Project operation remain unverified.

## Scoped exposure recap in the private CC report (2026-10-29)

When a complete dated, private caller-reported M3 `P_LEDGER` and matching `exposure_classifications` are supplied, the ordinary PI-only or IR+PI manual path now shows a small aggregate breakdown: known classified %, unknown/unclassified %, cash %, each of the **explicit observed account scope only**. A prior-dated fund holdings snapshot contributes **zero to present known** and its entire fund weight to **unknown**, with a prompt to check original fund holdings. Historical illustrative issuer allocations remain exclusively in `portfolio_exposures_private.historical_fund_scenario_private`, not the report or non-sensitive GitHub memory proposal. The report includes no individual holdings/weights, dollar amounts, issuer or account names or source URLs in this subsection. If portfolio scope is incomplete, it states UNAVAILABLE. It cannot authenticate brokerage access, holdings, source rights or policy, and does not create Project automation or trades. Targeted tests were authored; actual Python execution and live CC/PI acceptance are NOT_RUN/UNVERIFIED.
