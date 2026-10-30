# M4 R1 — Decision reports and CEO-requested follow-up analyses
**Owner:** Financial Systems Command Center; Product & UX review pending.  
**Status:** `CANDIDATE_TEMPLATE / USER_INITIATED_ONLY`. No report or analysis is generated automatically.

## Decision report — conclusions first, evidence after
Use [Operating Contract](../OPERATING_CONTRACT.md) and the actual, accessible R1 handoffs. Target at most ten minutes of reading where possible, without making report length an artificial minimum.

1. **Decision line/status:** distinguish exploratory, conditional and supported conclusions; explicit no-action when justified.
2. **Mandate:** CEO request, strategy, horizon, dated information cutoff, currencies and relevant account context only if authorized.
3. **Economic lenses:** separate Quality, Durability, Expected Return status, Confidence, and Portfolio Room only when PI has genuine dated holdings.
4. **Countercase and alternatives:** strongest contrary evidence, permanent-loss risk, material conflicting facts, qualified benchmark when available.
5. **Action or no-action:** contribution percentages only when actually justified and adding to 100%; known transaction costs, otherwise conditional.
6. **Recoverable evidence:** precise S/F/K/V/P identifiers, source dates and status, without false verification.
7. **Memory proposal:** versioned research record with analysis ID, original cutoff, actual method/prompt version and **PROPOSED_NOT_COMMITTED** archival status.

`ai_native.reporting.render_report(packet)` optionally formats a supplied packet; it does **not** collect evidence, certify facts, preserve data, schedule analyses or initiate trades.

## Reassessment — only when the CEO asks
The CEO may ask for the first analysis of a company or request re-evaluation **at any interval**. No weekly, monthly or annual default exists. A user-specified week is simply one possible historical window, never a recurring obligation.

When an actually accessible relevant previous analysis exists, compare:
- The original report ID, source cutoff, strategy/method version, thesis, assumptions, valuation and confidence as they were documented.
- Newly checked source facts with **their own** observation date, reporting basis, security class and evidence status.
- Which changes actually affect Quality, Durability, Expected Return assumptions, Confidence or Portfolio Room (the last only with a newly observed authorized portfolio).
- Contradictions, new information, key invalidation conditions, benchmark relevance and whether no investment action is justified.

Keep original findings immutable; corrections are appended, not rewritten. If no prior report is accessible, state `BASELINE_NOT_AVAILABLE` rather than claiming a change or inventing previous analysis. No update since the last user request means **NOT_CHECKED**, not no event.

## On-demand execution and required fields
The CC produces a result **only after a CEO-initiated request**. Neither these templates nor Project instructions authorize background monitoring, reminders, notifications, automatic weekly briefings or recurring analysis.

Minimum fields: `ANALYSIS_ID`, `REPORT_KIND=DECISION|FOLLOWUP`, `AS_OF`, actual `STRATEGY_ID@VERSION`, `METHOD_ID@VERSION` or `UNKNOWN_NOT_LOADED`, `FACT_IDS`, `SOURCE_LOCATORS`, `EVIDENCE_STATUS`, `CONFLICTS`, `DECISION_LINE`, `COUNTERCASE`, `NEXT_ACTION`. If FOLLOWUP: optional actual `PRIOR_ANALYSIS_ID`, with source cutoff, and optional CEO-defined interval. A comparison cannot be claimed when the previous report is inaccessible. No retrospective PIT claim.

## First decision-first executive view (component, not Project deployment)

The optional local `--output executive-report` reads the SAME completed manual R1 packet as `--output report` and produces a short French decision-first summary followed by the entire prevalidated detailed report. It does not fabricate an allocation, benchmark alpha, five-pillar rating, market-wide screening or private Portfolio Room. It preserves the source facts, dates, strategy-policy boundary, counter-thesis and next human action in the full annex. The original `--output report` and operator/closeout output contracts remain unchanged. Pending handoffs produce `REPORT_NOT_AVAILABLE`. This is a verified-source-independent formatter, not a ChatGPT Project installation or authentic three-Project acceptance; no archiving or writes.

## ChatGPT-native CC final report (R1.1 candidate, not installed)

The existing 8,000-character [copy-ready CC Project Settings](../project_settings/CC_R1_SINGLE_ACTION_PI_WORK_REVIEW_20261030.txt) now carry an explicit **final-turn** report contract: natural-language decision/status first; evidence-grounded five-pillar interpretations; a distinguishable researched candidate versus a justified new-cash percentage allocation; a precise blocker and one next human action when allocation is unavailable; and a separate S/F/K/V/P technical annex. No CLI/JSON is required of the CEO. This modifies the **Project instructions candidate**, not ChatGPT Project Settings: CEO adoption in CC and a real post-handoff report are **NOT_VERIFIED**. The existing optional local `--output executive-report` from PR #399 is unchanged and is not assumed executed by CC. No user data is archived.
