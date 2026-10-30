# M2 R1 — Opportunity research triage, private and non-ranking

**Status:** candidate manual research component; no live global discovery, investability verdict, valuation, automatic recommendations, or portfolio optimization.
**Function:** `ai_native.opportunity_triage.prepare_opportunity_triage`.
**Decision:** #19 `PARTIAL`; does not complete the requested end-to-end 36-decision release.

## Purpose and scope

The CEO or authorized analyst may supply a small opportunity universe (1–30 named securities) from personal portfolio, watchlist, public discovery or another requested scope. The module prepares a **private research work queue** from existing supplied IR facts and the M2 provenance annex. It does not discover stocks, establish the actual universe of investable securities, select the “best” company, forecast growth or normalize financial data. The initial candidate ordering is **preserved**; there is never a new ranking, score, buy recommendation, return forecast or claim that GLOBAL_DISCOVERY exhaustively screened a global universe.

## Exact manually supplied input

`analysis_id`, `analysis_as_of` (canonical YYYY-MM-DD), `strategy_id`, `universe_scope` (OWN_PORTFOLIO, WATCHLIST, GLOBAL_DISCOVERY, MIXED_REQUEST), `universe_note` and a `candidates` list of 1–30 records. Each candidate contains:

- `candidate_id` and a unique `economic_issuer` + `instrument` pair, `target_type` (ISSUER, SECTOR_ETF, REFERENCE_ETF) and `origin_scope` (OWN_PORTFOLIO, WATCHLIST, PUBLIC_DISCOVERY, CEO_NOMINATED).
- `research_question`, `ir_fact_ids` (which may be empty, explicitly recording a gap), nonempty `open_questions`, and an explicit `known_risks` list (which may be empty without proving no risk).

The runtime additionally requires the original supplied `ir_facts` list and a preassembled M2 `source_annex` for the **same ANALYSIS_ID and analysis cutoff**. A candidate references only original IR fact IDs. A linked source observation must carry the same issuer/instrument identity. Any missing observation, unavailable/incomplete/conflicted source, uncertain/restricted rights, non-primary-source record, or unresolved original IR fact produces an explicit **research evidence issue**. A single negative observation is not cancelled by a clean observation; no source becomes authenticated. Original-source retrieval, publisher identity/rights, PIT market availability, security comparability and observation validity still require external verification.

## From a human-selected research candidate to a new deep-dive request (R1 manual CC→IR)

The existing original-source-dependent opportunity triage can now feed a **new, explicitly non-executable** private Command Center draft. Once the user has already completed a CEO-initiated IR analysis with the original `IR_CAPSULE`, supplied M2 `source_evidence_inputs` or original `EVIDENCE_ANNEX`, and `opportunity_triage_inputs`, run:

```sh
python3 -B -m scripts.r1_manual_session_cli --output candidate-deep-dive-draft < private-selected-candidate.json
```

Here `private-selected-candidate.json` is an **operator-controlled private input** with **exactly** `{"session": { ...the original complete CEO-authorized R1 session... }, "candidate_id": "the exact triage candidate ID"}`. Never upload private source records or this output to GitHub, Media or a public channel. The CLI **re-evaluates the original complete M1→M2→M7a session** and consumes only its computed `integrated_private.opportunity_triage_private`. It rejects an isolated submitted triage JSON, a pending IR case or an unknown candidate ID. The original candidate order remains unchanged and there is no automatic selection, search, score, recommendation, or implicit extra CEO instruction.

The private draft has the original candidate's named issuer/instrument, open questions, risks, *referenced IDs only* for prior original facts/source observations, and actual `EVIDENCE_RESOLUTION` or `HUMAN_DEEP_DIVE` stage. It **does not copy old source URLs, numeric financial values or research claims into the new request**, nor treat any previous fact ID as a newly checked fact. The new `input_template.request` carries `ceo_initiated=false`, empty analysis identity/cutoff/objective, unknown account costs and method load, and **only the previously selected strategy label**, which the CEO must reconfirm. It defaults to a separate `DECISION` research case (`research_needed=true`, `portfolio_needed=false`), not an unrequested historic `FOLLOWUP` or Portfolio Intelligence analysis. The user must explicitly fill a **new** dated mandate with objective, horizon, risk, account/cost and other constraints and then choose whether to run `intake-review` and `guided-operator`. Until then the draft is inert and the existing R1 request validator rejects it.

All six strategy labels remain non-authorizing: the five new R1 policy designs besides existing scoped High-CAGR are not approved financial policy. An `EVIDENCE_RESOLUTION` candidate remains a research question, never promoted to investable security or admitted solely because it was selected. The prototype does not perform global screening, live Project invocation, independent source/rights certification, private persistence, or trading. Tests are synthetic and require execution in an authenticated clean checkout; no R1 system-wide acceptance is claimed.

## Two work stages, not investment ratings

- `EVIDENCE_RESOLUTION`: material structural evidence issues, such as missing IR links or source conflicts. Continue research only after human review.
- `HUMAN_DEEP_DIVE`: supplied fact IDs and their source observation metadata are structurally aligned enough to *invite* an analyst deep dive. **Not** decision-grade, approved, eligible, certified, or recommended; the separate qualitative, valuation, constraints and risk analysis remains to do.

The private output preserves candidate identity, questions, original fact and observation IDs, warnings and declared origins. It always sets `universe_completeness=NOT_VERIFIED_NOT_GLOBAL_SCREENING`, `source_authentication=NOT_PERFORMED`, `normalized_expected_return=NOT_ESTABLISHED`, `ranking_or_buy_recommendation=NONE`, `portfolio_allocation=NONE`. Do not use the numerical stage counts as a score, market ranking or evidence of global coverage.

## Manual M1 → M7a integration

Optionally pass `opportunity_triage_inputs` with the **exact six manual user fields** (analysis ID, cutoff, strategy, scope, note, candidates) alongside `source_evidence_inputs` in a CEO-initiated IR route. M7a derives `ir_facts` from the preserved IR capsule, builds the private provenance annex and returns `opportunity_triage_private`. It does not store or publish the results. The concise report states only that a private research queue was organized without source certification, global screening or recommendation. No candidate name or sensitive source observation ID is added to `memory_proposal_nonprivate`.

When actual source observations are missing, supply an explicit empty M2 source observation list; the candidate stays in `EVIDENCE_RESOLUTION`. Without a source annex at all, triage is rejected rather than creating a fake global selection.

**Validation limits:** new helper unit tests and manual seam tests are synthetic; full repository check, real multi-country issuer research, authentic permitted source verification, user-facing Project handoffs, and full acceptance of the 36 decisions are separate and not proven here.
