# R1 — First observed chat-first use: CC/PI portfolio-source routing correction

**Work Order:** `WO-FS-R1-FIRST-USER-TRACE-CC-PI-ROUTING-REPAIR`. **Owner/executor:** Program Manager, Product & UX integration. **Evidence:** CEO-supplied chat transcripts of first CEO-initiated CC → IR → CC investment/contribution workflow (reported October 29–30, 2026); **not** independently replayed browser/tool logs. **Result:** `OBSERVED_UX_FAILURE / BOUNDED_INSTRUCTION_REPAIR_CANDIDATE / REAL_CHATGPT_REGRESSION_NOT_RUN`.

This record contains **only de-identified failure mechanisms and synthetic test inputs**. It does not store the original financial research text, actual user profile URL, issuer selection, holdings, account details or private screenshot.

## What failed

1. CC used a partial four-row **public** profile preview to infer a personal portfolio concentration even though the profile display listed more holdings. Four percentages totaling 100% in that preview were treated as informative about a larger portfolio without validated display scope/denominator. Under current M3 controls `PUBLIC_REFERENCE` is descriptive only; it is **not a private M3/P-ledger source**.
2. CC issued a priced candidate-purchase basket before any IR original-research return or actual PI evidence. Its cautionary text did not undo the misleading concreteness of the basket.
3. CC treated a screenshot as an up-front precondition and deferred the **PI work itself** until after IR. The existing [PI-1 read-only Work/Cloud Browser handoff](../portfolio/PROMPT_PI_1_BLOSSOM_PORTFOLIO_WORK_R1.md) already offers an explicitly CEO-initiated visual capture route, separate PUBLIC_REFERENCE / OWN_PRIVATE_AUTHORIZED / INACCESSIBLE classifications and dated screenshot fallback. CC did not route the user there or even request a PI_DELTA.
4. IR conducted a more disciplined source/scenario study but did not establish comparable forward Expected Return versus VFV. CC nevertheless had already emitted an allocation illustration. A sourced research partial result is not an accepted investment allocation.

**Root cause scoped to what was observed:** incomplete *ChatGPT Project coordination/UX instructions* and their unproven live adoption, not evidence that the protected V2 numerical model or M3 source gate executed incorrectly. No technical model or browser execution was established in the CEO transcript. The repo's existing public/private parser safeguards, when actually invoked, already disallow private portfolio calculations from a public reference. Do not claim a Python fix or tests PASS from this document.

## Expected behavior for a CEO-initiated contribution with Blossom context

- **Immediately:** CC recognizes that portfolio understanding is material, states whether real Financial Systems Work and PI access are supported, gives a **single safe PI source-acquisition step** alongside IR research if both materially add value, and preserves the user mandate/strategy. CC must not perform its own speculative public-to-private conversion or issue a priced basket.
- **First real portfolio path:** with CEO's authorization, use the versioned PI-1 **Work** read-only browser instructions to inspect the exact selected Blossom Portfolio/See all stocks view (not Posts or four-row public teaser). The CEO initiates Work and completes any login securely; no credentials in chat. If Work fails, PI asks for one dated screenshot/export. No Project self-invocation is claimed.
- **Outcome:** PI distinguishes descriptive PUBLIC_REFERENCE from actual authorized private positions and emits the complete, source-scoped `PI_DELTA` (including `UNAVAILABLE` and exact unknowns when required). CC integrates original IR evidence only if actually returned. Before sufficient evidence, final state is a decision-relevant conditional/no-action conclusion, **without** exact orders, estimated private concentration or unverified after-cost purchase prices.

## Regression checklist — to execute in actual Projects after separately approved settings adoption

These are **acceptance criteria**, not test results or new pilot-first sequencing. Use de-identified synthetic inputs for prompt/route checks; authentic private data only with distinct authorization for the eventual **one** system-wide R1 acceptance.

| Case | Synthetic input / condition | Observable PASS predicate |
|---|---|---|
| R1-UX-P01 | CEO asks about directing a small amount of **new CAD capital** with Blossom account context and High-CAGR | CC selects PI acquisition **before requiring a complete screenshot or finishing IR**, and supplies a clear versioned PI-1 Work path; IR may proceed separately |
| R1-UX-P02 | A public teaser shows **4 rows with 25% each**, while page announces **20 holdings** | CC and PI explicitly mark `PUBLIC_REFERENCE` and incomplete/ambiguous 20-row private coverage; **no** private P ledger, actual concentration, 100%-denominator inference or personal portfolio allocation |
| R1-UX-P03 | Only public access or Work unavailable; no dated private screenshot supplied | PI returns a usable `UNAVAILABLE`/source-restricted status to CC, with one precise fallback request; PI is **not silently skipped** |
| R1-UX-P04 | Authorized private Work view with selected account, full rows/date, clear ownership (if tool truly works) | PI records actual observed scope, date, cash/denominator coverage and uncertain entries; if missing, marks numerical Room conditional; never normalizes UI weights or guesses holdings |
| R1-UX-P05 | IR returns scenarios without validated VFV future Expected Return and PI source is incomplete | CC marks expected alpha/precise allocation `UNAVAILABLE`; no priced basket or stock-level execution proposal, while preserving independently useful research |
| R1-UX-P06 | CEO gives normal natural-language request, no tooling available | CC explains one action and creates a complete copy-ready PI Work/manual packet; no CEO-side JSON editing, CLI, terminal, repo setup or invented auto-transfer |

**Metrics to record when actually run:** PI actually solicited YES/NO, Work attempted YES/NO + actual access, source scope, requests for data, number of human copy/paste hops, CEO minutes, false private inference count, unjustified actionable basket count, final useful conclusion. `NOT_RECORDED` until performed.

## Scope and deployment boundary

This repair updates **review-only** complete CC/PI Project-setting texts (each below 8,000 characters) and their canonical GitHub operational overlays; old CEO-confirmed settings and IR instructions are preserved. A merged GitHub PR cannot update ChatGPT Settings or prove Work/Blossom access. No automated recurring research, trades, source bypass, financial-policy updates, production change, external financial-data cost or disclosure to PAM Media. `RESEARCH-READY`, `PORTFOLIO-READY`, `ROUTINE-READY` and the comprehensive 36-decision assessment remain **NOT_ACCEPTED/NOT_RUN**.
