# Work Order — M5 Evidence / deterministic checks R1

**ID:** WO-FIN-FS-R1-M5-EVIDENCE-ARITHMETIC  
**Primary owner:** Data & Evidence (method review pending; PM assembled code and docs).  
**Why now:** CEO merged PR #256. M1–M4 candidates need a small reusable arithmetic/compatibility check in the complete 36-decision integrated release, without rebuilding a V2-style data platform.  
**Status:** PR_CANDIDATE / NOT_DEPLOYED / NO_FULL-SYSTEM_ACCEPTANCE.

## Objective, authority, resources
Deliver `ai_native/evidence_math.py`, `tests/test_ai_native_evidence_math.py`, and the companion contract in this directory. Use only verified-on-hand source facts from authorized research and no private portfolio data. This is one bounded M5 release component, not a new market discovery pilot.

**Mandatory context:** Constitution, Governance, Current State, Program Manager charter, CEO 2026-10-28 build-first decision, `DECISION_COVERAGE.md`, `OPERATING_CONTRACT.md`, Research M2 `SOURCE_FUSION_R1.md`, `VALUATION_R1.md`, Portfolio M3 and Reporting M4 interfaces; apply existing V2 semantic/PIT restrictions as boundaries, not copied numerical rules.

**Scope:** static, read-only, deterministic arithmetic on supplied fact records with explicit compatibility and support limits. Python standard library only. `UNAVAILABLE` applies to an unsupported calculation, **not** the company Quality. Validation: synthetic unit tests and compile, financial concepts/period/FX edge cases, local/GitHub blob parity, PR diff. Not authority to change model policy or certify real sources.

**Prohibited:** API calls, source-scraping, paid data, HTTP-rate workarounds, private portfolio uploads, browser/Blossom/broker connection, automatic transactions, background tasks, GitHub autonomous writes, V1/V2 source changes, production promotion, protected edits or merge. The CEO alone approves canonical merges.

**Complexity:** STANDARD. **Output:** code + tests + short contract, concise PM handoff. **GitHub:** new files only in M5 and isolated ai_native/test paths. **Resources:** existing GitHub/ChatGPT, $0 external financial-data spend.

**Stop:** opened PR, not merge. Next Program Manager should prioritize **connecting the already prepared modules and verifying real Project installation**, plus separately authorized read-only legacy knowledge inventory. No fixed weekly cadence or automatic research.
