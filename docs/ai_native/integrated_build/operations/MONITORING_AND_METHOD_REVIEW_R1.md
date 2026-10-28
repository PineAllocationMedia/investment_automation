# M4 R1 — Conditional monitoring definitions and method evolution
**Owner:** Command Center, PM oversight. **Status:** `ON_DEMAND_SPECIFIED / AUTO_MONITORING_NOT_ACTIVE`.

## Observations and material triggers
For an explicit user research mandate, define a narrow **watch condition** only when the facts have a defensible source, source cutoff, method version and observed baseline. Examples of *categories*, not active automations:

| Condition | Source/evidence needed | Interpretation |
|---|---|---|
| Thesis invalidation | A recorded company-specific mechanism and new original filing | Research follow-up; not automatic sale |
| Material funding or dilution | Actual share/debt/financing event and affected period | Recalculate per-share thesis and financial room |
| Organic growth versus M&A | Original disclosures and aligned periods | Challenge Quality/Durability confidence |
| Earnings/valuation conflict | Both original accounting and secondary estimate/basis | Mark CONFLICTED until reconciled |
| Sector/macro change | Date-supported sector/macro evidence and company linkage | Contextual stress, **never market timing** |
| Portfolio change | New authorized dated portfolio input and complete scope | Conditional re-evaluation, never inferred trading |

A signal is `OBSERVED` only when checked in the stated window. `NOT_OBSERVED` requires actually completed coverage. Otherwise write `NOT_CHECKED`, `INACCESSIBLE` or `CONFLICTED`. Do not generate news alerts from stale chat summaries.

## Operating cadence
**Current supported path:** user asks Command Center for an on-demand weekly brief; CC asks IR/PI only where the material decision warrants it, carrying one minimal packet; updates trace prior analysis IDs. One human input hour per week is a *target to measure*, not a promised result.

**Potential future scheduled path:** only after the CEO explicitly authorizes a narrow scheduled task, source/tools capability is confirmed, private inputs are safe, and the triggering window/notification destination is clearly specified. A scheduled reminder is not proof the research engine can fetch data, access Blossom or route tasks to separate Projects. No background agent, unattended Codex restart, spending, self-triggered publication or brokerage action follows from this document.

## Improvement governance
For a proposed improved prompt, preserve version and test cases; check unchanged economic facts, cited source dates, counterarguments, less hallucinated precision, latency/manual handoffs and report usefulness. Do not tune to realized returns or retrospectively replace source-as-of. Specialist owns method judgment; PM integrates; CEO decides material policy and merges. Revision candidates remain `PROPOSED` until approved and installed separately.
