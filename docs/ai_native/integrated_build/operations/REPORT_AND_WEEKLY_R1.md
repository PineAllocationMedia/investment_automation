# M4 R1 — Report and weekly intelligence output contract
**Owner:** Financial Systems Command Center; Product & UX review pending.  
**State:** `CANDIDATE_TEMPLATE / ON_DEMAND_ONLY`, not automatically generated or delivered.

## Decision report — one screen first, evidence after
Use the [Operating Contract](../OPERATING_CONTRACT.md) and R1 handoffs as input. The executive layer targets **no more than ten minutes of reading**, without requiring a long report when the decision is simple.

1. **Decision line / status:** clearly state `EXPLORATORY`, `CONDITIONAL` or scoped capability status. State no-action or refusal of unsupported conclusion where appropriate.
2. **Mandate:** date/cutoff, approved strategy and version, horizon, relevant company/security identities, currencies, account scope where authorized.
3. **Key comparisons:** Quality, Durability, Expected Return availability and confidence **separately**. Portfolio Room only after PI supplied verified dated portfolio observations. Include VFV or other benchmark only when valid.
4. **Countercase:** strongest disconfirming thesis, permanent-loss path and material unresolved conflict.
5. **Actions/alternatives:** new-contribution percentages only if supported and totaling 100%, with genuine costs and account constraints; otherwise explicit conditions and decisive missing inputs.
6. **Sources:** compact inline source IDs and a recoverable S/F/K/V/P appendix, not an unsupported list of links or a citation-only substitute for proof.
7. **Memory proposal:** analysis ID, method and prompt versions, as-of and proposed history pointer. **Proposal is not a committed archive**.

Use `ai_native.reporting.render_report(packet)` optionally for a **read-only Markdown skeleton**. It does not generate analyses or certify citations; it requires enough identifiers and stamps to render caller-reported VERIFIED facts. Portfolio-sensitive output stays private in its actual handling environment. No report is automatically uploaded to GitHub.

## Weekly on-demand briefing — meaningful deltas
Report **changes since a specified previous baseline**, or `BASELINE_NOT_AVAILABLE` instead of invented changes. Suggested compact order:

- As-of / window, the prior baseline's actual record ID and cutoff, strategy, market coverage and source freshness.
- **What materially changed:** earnings, thesis-break evidence, valuation assumptions, portfolio overlap, governance/source caveats and macro/sector mechanisms; report source and confidence for each.
- **What did not become decision-worthy:** explicit no-action when data do not justify capital movement.
- **Watch items:** thesis-linked observable triggers, not speculative price timing.
- **Capital destination** (only if requested/qualified): identified candidates versus VFV/opportunity cost; distinguish contributions from exceptional sale requests.
- **Unresolved contradictions, human decisions and next review:** one necessary follow-up, not an endless crawl.

No claim that “nothing changed” from an empty update set. An absent monitoring result means `NOT_CHECKED`, not `NO_EVENT`. On-demand execution is available through a human prompt; recurring runs, notifications, event monitoring, Blossom access and cross-Project handoffs remain **unverified unless separately activated with actual supported tools**.

## Required audit fields
`ANALYSIS_ID`, `REPORT_KIND`, `AS_OF`, `STRATEGY_ID@VERSION`, `METHOD_ID@VERSION` (or `UNKNOWN_NOT_LOADED`), `FACT_IDS`, `SOURCE_LOCATORS`, `EVIDENCE_STATUS`, `CONFLICTS`, `DECISION_LINE`, `ASSUMPTIONS`, `COUNTERCASE`, `NEXT_ACTION`, and actual portfolio observation timestamp if relevant. For a weekly brief include `WINDOW_START`, `WINDOW_END`, `PRIOR_BASELINE_ID` or `BASELINE_UNKNOWN`. Never call retrospective research authentic historical PIT.
