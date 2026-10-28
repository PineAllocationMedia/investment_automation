# Work Order — M3 scoped issuer/sector/region exposure and fund look-through

**ID:** `WO-FIN-FS-R1-M3-SCOPED-EXPOSURE-LOOKTHROUGH`  
**Primary specialist:** Portfolio Intelligence (economic interpretation and risk scope); implementation prepared by Program Manager, independent PI review **not claimed**.  
**Why now:** PR #269 merged 2026-10-28 and the approved 36-decision **build-first** program still lacks a working economic issuer/sector/region aggregation from the existing private P-ledger, particularly for multiple fund holdings overlapping direct equities. We should reuse existing M3 ledger/denominator, not build new prices or a universal optimizer.

**Objective:** one pure, in-memory, private `portfolio_exposure.py` that aggregates on dated source-specific, caller-provided classifications, including partial fund composition as unknown; connect as optional `exposure_classifications` in the existing PI session bridge, retaining original P data and refusing unsupported complete-room assertions. No new asset-allocation policy, ETF source or numeric strategic concentration threshold.

**Sources:** Constitution → Governance → Current State → PM charter → this WO → `AGENTS.md`, approved CEO build-first Decision Registry entry, `OBSERVATION_AND_ROOM_R1.md`, `portfolio_observation.py`, `session_bridge.py`, operating contract and 01–36 matrix. PI charter/technical review to be applied independently before treating methodology as approved.

**Authorized scope:** new pure source, two synthetic test files, targeted bridge optional input, M3 observation-method/runbook notes and exact #18 evidence delta, this nonprotected WO. $0 incremental financial-data cost. No accounts/real holdings, authenticated sources, external connectivity, live Work session, trading, production/deployment, scheduling, automatic Project invocation, local device access, protected docs, V1/V2 model edits, policy amendment or merge.

**Validation:** local 22 exposure + 5 bridge cases plus 44 earlier local M3/M1 unit tests PASS (71 total), Python compilation PASS. Git blob parity and PR exact-scope review. The locally run prior bridge snapshot is not the latest repository; full canonical tests and PI subject review remain open. Preserve unknown source-rights and partial fund compositions, don't turn source/ref age into automatic certified correctness.

**Delivery status:** `BOUNDED_M3_PRIVATE_EXPOSURE_ASSEMBLY / NOT_PORTFOLIO_READY / NO_REAL_BLOSSOM_OR_FUNDS_AUTHENTICATION`. Stop after PR; CEO controls merge. Comprehensive 36-decision assessment follows only after full functional assembly.
