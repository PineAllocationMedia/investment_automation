# Work Order — M1 to M7a manual session bridge

**ID:** `WO-FIN-FS-R1-M1-M7A-SESSION-BRIDGE`  
**Primary role:** Product & UX (functional interface). **Implementation:** Program Manager prepared bounded code and contract changes; no claim of completed independent Product & UX or Architecture & Audit specialist review.  
**Why now:** PR #264 merged and the CEO reiterated the **full 36-decision functional assembly first**, followed by one comprehensive integrated assessment. The M1 IR/PI request generator and M7a response/report assembler are separate interfaces with no unified manual route handling.

**Objective:** Route an explicit CEO-initiated REQUEST through the already implemented M1 handoff generator; apply M7a private synthesis to IR-only and IR+PI cases; provide a strictly conditional portfolio-only report; return pending status without imaginary responses when manual transfers have not occurred. Conserve source identities, method/status uncertainty, dates and unchanged IR evidence.

**Sources:** Constitution → Governance → Current State → Program Manager charter → this WO → CEO 2026-10-28 build-first Decision Registry entry, AGENTS.md, R1 Operating Contract, M1 assembly WO, M7a runbook, M1 request generator, M7a assembler, reporting module and 01–36 coverage. No V1/V2 investment policy modifications.

**Scope/authority:** Add one pure standard-library `ai_native/session_bridge.py` and its bounded synthetic tests; append the existing nonprotected manual runbook; update only applicable evidence text in the existing 36-row coverage matrix; create this nonprotected WO. This is a *construction-time* supervised interface with no new financial-data sources, storage, trading, automatic Project calls or scheduling.

**Prohibitions:** no edits to CEO_PROTECTED governance, V1/V2 core model rules, production/deployment, brokerage actions, Project settings, private holdings in GitHub, source rights, paid external data, local device inventory, merges or autonomous orchestration. No new investment philosophy; $0 incremental external data costs.

**Validation:** exact tested source/test Git blob parity, syntax compilation and 18 synthetic seam tests locally; GitHub diff scope and ledger row count. Integration and full repo tests should be run in a complete checkout before merge where available, but do not claim them if not. All PI-only outcomes are conditional and actual human labor not observed. Comprehensive acceptance remains deferred until full integrated functionality is assembled.

**Output/resource budget:** STANDARD, smallest sufficient capability and documentation; no external financial data cost.  
**Stop:** open PR, no canonical merge. CEO controls merge separately.
