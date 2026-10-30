# R1 — Second CEO test: single-step Work/PI ownership and universal CC intake

**Date:** 2026-10-30. **Work Order:** `WO-FS-R1-CC-START-NORTH-STAR-SEQUENTIAL-PI-WORK`. **Owner:** Program Manager (Product & UX integration). **Evidence:** CEO-shared CC transcript after merged PRs #396 and #397; no independent inspection of ChatGPT project settings, Cloud Browser session, source identity or full IR/PI returns. **Result:** `CEO_REPORTED_PARTIAL_UX_IMPROVEMENT / ORCHESTRATION_CONFLICT_FOUND / NOT_ACCEPTED`.

This record is **de-identified**. It intentionally omits the CEO's actual portfolio URL, investment amount, account details, prior case identifiers, trades, screenshots and private research contents. Do not copy the chat transcript or any private account observations into GitHub.

## Observed issues (from CEO report)

1. On one new complete-analysis request, CC emitted **two simultaneous handoffs** (IR + preliminary PI), creating needless multitasking/copying for the CEO despite the chat-first UX goal.
2. CC itself tried to open Blossom via a connected browser/Web path and reached an unrelated browser security block; **that is not an authentic PI Work/Cloud Browser attempt**. The existing versioned PI-1 task expects the CEO to launch a read-only Work task, ideally in the PI Project if the UI supports it. Separate Financial Systems account authorization must be real; PAM Media's successful Posts workflow is a reference pattern, not proof of private Portfolio access.
3. CC accurately identified **no real private portfolio observation yet** and withheld actionable allocation: partial improvement compared with the first user trace. No IR or PI specialist result was returned in the supplied excerpt, so actual three-Project behavior remains unverified.

## User-visible expected behavior (one next step)

When the [universal CEO CC gabarit](../operations/UNIVERSAL_CC_ANALYSIS_START_R1.md) requests a new contribution analysis **and** an authorized private portfolio source is material:

1. **CC → CEO (only one action):** prepare a complete, copy-ready **PI-1 read-only Cloud Browser Work** request for the *actual selected Portfolio URL/view*; explicitly instruct the CEO to start Work inside PI Project **if available**, otherwise use a separate Work session and carry the result to PI. CC does **not** navigate Blossom itself. If no authorized Work capability, ask for one dated screenshot/export directly.
2. **PI Work → CC:** classify public/private/inaccessible from the *actual observed view*, preserve capture time and scope and return the concise initial source receipt or `UNAVAILABLE`. No speculative position weights; no PI investment conclusion before needed IR.
3. **CC → IR → CC:** if fresh issuer discovery/valuation adds material value, carry one complete IR_REQUEST, receive authentic IR_CAPSULE/EVIDENCE_ANNEX. If PI acquisition was blocked, IR may still provide an evidence-qualified conditional research result.
4. **CC → PI → CC:** send exact original IR capsule/annex **unchanged** plus only the actually authorized PI observation; PI returns PI_DELTA or unresolved Room, after which CC produces the only combined report. If either specialist is unnecessary, omit that leg. The CEO should **never receive two independent next actions at once**.

The earlier prompt's « engage PI dès le départ, en parallèle d'IR si utile » means prepare/recognize both tracks at intake, **not** two concurrent *user-visible* copy/paste jobs. PI source acquisition can precede IR without changing the approved investment strategy.

## Evidence-oriented regression predicates (NOT YET RUN)

| Case | Required observable outcome |
|---|---|
| R1-UX-02-01 — full CC intake | CC recognizes the `CC-START-R1-v1.0` six-section input, returns **one** first next action and does not demand CEO JSON/CLI |
| R1-UX-02-02 — Blossom | CC performs **zero** direct Blossom navigation/search; source acquisition belongs to CEO-launched PI Work (if available) |
| R1-UX-02-03 — permissions/fallback | Actual user-authorized Work supports selected view or PI explicitly reports limited/failed access and requests one dated screenshot, without fake P ledger |
| R1-UX-02-04 — combined research | IR has an actual request and produces original capsule; final PI receives and preserves it unchanged; CC returns one justified report |
| R1-UX-02-05 — privacy/time/cost | No public-to-private inference, no assumed time/source/cash/fees, no private archive claim, no new financial-data cost |
| R1-UX-02-06 — user effort | Count **actual** user-carried messages and minutes; prompt generation or planned calls do not count as specialist invocation |

**Known construction gap:** The optional local JSON/manual session bridge still uses an **IR-first** pending-specialist ordering for combined routes. A chat-first PI source-acquisition step is a **user-facing Work procedure**, not proven automatic invocation or a changed local backend. Before claiming code-backed end-to-end sequencing, actual session bridge alignment and live Work/Project traces must be checked; do not mislabel a docs change as runtime integration. This is a targeted component UX check during assembly, **not** the comprehensive 36-decision acceptance or a recurrence/pilot-first development mandate.

**Version boundary:** The CEO explicitly supplied a slightly revised **display-labeled** `CC-START-R1-v1.0` after its first GitHub merge. The prompt remains exactly CEO-chosen; the later revision is identified by repository commit/date for traceability. Future substantive changes should use an explicit new version, preserving old test comparisons.
