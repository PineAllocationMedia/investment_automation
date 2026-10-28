# Work Order — R1 bounded construction seam regression

**ID:** `WO-FIN-FS-R1-M7-CONSTRUCTION-SEAM-REGRESSION`  
**Primary role:** Architecture & Audit (technical boundary and integration-contract assurance). **Preparation/implementation:** Program Manager; **no independent specialist review has been invoked or completed**. This Work Order adds a targeted test asset, not the global M7 acceptance.

**Why now:** PR #270 is merged at `b9babe190b6f15f5a832a4af54d09c450d4fa9fb`; the first AI-native 36-decision integrated functional build is **still incomplete**. The recently added M1–M4 components were checked mostly in separate synthetic runs, some using old/local M7a seam mocks. Before continuing construction, guard their cross-module ID/date/unknown/privacy contracts with one bounded canonical-repo test file. Do **not** substitute this for the final system evaluation or delay independent next functional work unnecessarily.

**Sources:** Constitution → Governance → Current State → Program Manager charter → this WO → Architecture & Audit charter, `AGENTS.md`, 2026-10-28 CEO build-first decision, existing M1–M4 module sources and previous portfolio-exposure Work Order, 36-decision coverage matrix.

**Deliverable and scope:** one synthetic `tests/test_ai_native_construction_contracts.py`, this WO, `integration/CONSTRUCTION_SEAM_REGRESSION_R1.md`, and a truthful #28 evidence-row update (remains `PARTIAL`). No production runtime changes or additional external dependencies. Run 12 newly authored tests and locally available component tests, verify exact code SHA/parity, and give checkout commands for authentic current-repo regression. **Independent actual-repository suite remains unexecuted; flag transparently.**

**Authority/resources:** STANDARD, purely reversible nonprotected paths, local Python stdlib, $0 incremental financial-data cost. **Prohibited:** V1/V2 policy edits, private holdings in repo, web access to accounts, source-licence promotion, autonomous Projects/trades, spending, schedules, device access, deployment, GitHub record auto-publication, protected amendments, CEO merge and declaring READY.

**Exit:** Open one PR and stop before merge. The CEO alone decides merge. Next priority: resume functional portfolio-room and research assembly; **comprehensive acceptance only after the complete 36-decision functional version**.
