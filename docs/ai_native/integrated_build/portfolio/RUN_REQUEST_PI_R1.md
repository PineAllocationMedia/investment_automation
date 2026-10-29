# M3 PI R1 — Operator-ready CC → Portfolio Intelligence request
**Status:** candidate copy/paste template; not evidence of Blossom access or method installation.

**JSON return to CC (manual):** Supply a complete original `PI_DELTA` JSON mapping. In an IR+PI request, return the original untouched research evidence as a *separate* `FORWARD_UNCHANGED` field alongside `PI_DELTA`, e.g. outer `{"PI_DELTA": {...}, "FORWARD_UNCHANGED": {...}}` (the ellipses are placeholders, not valid JSON). The CEO/CC must separately retain the original received IR capsule and present it as `ir_capsule` with `request` when calling the local CLI with `specialist_result`; R1 rejects any mismatch. On PI-only mandates, return only `{"PI_DELTA": {...}}`, with no fabricated IR. Original observations and any private source data remain private; no Project invocation, broker authentication, release or trade is implied.

Use with the actual PI v0.2 / R1 instructions and the companion Portfolio Intelligence M3 methods when accessible. If the receiving Project has not loaded a method, state METHOD_NOT_LOADED and limit claims accordingly. Send only the private inputs needed, through a private authorized chat, not a GitHub issue/PR.

~~~text
PAM R1 — PI_REQUEST / PRIVATE PORTFOLIO CONTEXT

ANALYSIS_ID: [from CC]
TRANSFER_ID: [current transfer]
IR_AS_OF: [research cutoff]
PORTFOLIO_AS_OF: [actual captured date/time/timezone or UNKNOWN]
SOURCE: [verified authorized Blossom view / dated screenshot / export / transcription]
ACCOUNT_SCOPE: [exactly visible account(s), or UNKNOWN]
STRATEGY_ID@VERSION: [approved mode; High-CAGR only when genuinely applicable]
CONTRIBUTION: [amount/currency and source/availability, or UNKNOWN]
ACCOUNT/BROKER/FX/FEES/TAX: [known actual inputs or UNKNOWN]
IR_CAPSULE + EVIDENCE_ANNEX: [one intact original package or PACKET_INCOMPLETE]

TASK:
1. Transcribe P records with field-level VERIFIED_VISIBLE / UNCERTAIN / NOT_VISIBLE. Identify missed accounts, cash, incomplete scope, share class/ADR duplicates and stale/cross-currency values.
2. Analyze concentrations, company/ETF overlaps, Portfolio Room and risks only on actually supported evidence; otherwise mark ROOM_CONDITIONAL/UNAVAILABLE.
3. Compare newly funded capital destinations by the **approved** strategy, source-faithful IR scenarios, benchmark and true observed constraints; avoid arbitrary precise allocations.
4. If the user/analyst provides justified 100%-summing contribution percentages and the complete scoped account inputs, optionally run the gross-only ai_native.contribution_math helper; otherwise describe conditional outcomes, never fabricate fees or net results.
5. Review exceptional trim/exit only if explicitly asked, grounded in a real thesis change and after-cost limitations.
6. Return a single PI_DELTA plus untouched FORWARD_UNCHANGED IR evidence to CC; one decisive missing datum/next action, no trading.

STATUS: EXPLORATORY unless distinct gates truly satisfied.
STOP after compact private handoff to CC. No publishing, trade, source scrape, repo write, cross-Project invocation or scheduled action.
~~~
