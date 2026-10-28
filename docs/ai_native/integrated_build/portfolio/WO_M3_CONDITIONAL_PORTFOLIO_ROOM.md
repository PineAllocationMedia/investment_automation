# Work Order — M3 qualitative, strategy-conditional Portfolio Room packet

**ID:** `WO-FIN-FS-R1-M3-CONDITIONAL-PORTFOLIO-ROOM`  
**Primary role:** Portfolio Intelligence (PI analytical decision interpretation). **Implementation preparation:** Program Manager; independent Portfolio Intelligence/Architecture & Audit review not yet executed.

**Why now:** PR #271 is CEO-merged on 2026-10-28. The approved AI-native 36-decision **build-first** approach still lacks executable connection between IR's Quality/Durability/Expected Return/Confidence, observed scoped holdings/exposures and qualitative Portfolio Room. Numeric exposure alone must not authorize a position.

**Objective and deliverable:** one private pure-Python `ai_native/portfolio_room.py` to interpret an explicit strategy, account, horizon and capital-source mandate, preserve actual IR fact links and uncertainties, the existing P-ledger and economic-issuer lower bound, candidate thesis and four PI constraint checks, plus strongest opposing case and one decisive next verification. Add optional `room_assessment_inputs` on the existing `CC_IR_PI_CC` manual bridge. Add two synthetic test files and bounded method/runbook/coverage updates. This is **qualitative conditional research, not a weight optimizer**.

**Context sources:** Constitution → Governance → Current State → PM charter → this WO → `AGENTS.md`, CEO-approved 2026-10-28 build-first decision, `OBSERVATION_AND_ROOM_R1.md`, `LIFECYCLE_AND_HANDOFF_R1.md`, actual `portfolio_observation.py`, `portfolio_exposure.py`, `session_bridge.py`, `DECISION_COVERAGE.md`.

**Safeguards/authority:** no strategy amendment, mechanical concentration thresholds, inferable net fees/FX/tax, account read, newly granted private Blossom/Work access, unlicensed source use, brokerage login, trading, spontaneous trim/sell, automatic Project invocation, private holdings in GitHub, archival write, production/deployment, spending or CEO_PROTECTED edits. Explicit `SPECIALIST_REPORTED` never means source-verified; **highest permitted status `ROOM_CONDITIONAL`**. CEO retains final capital decisions and merge authority. Incremental external financial-data cost $0.

**Validation:** Python local 21 room + 6 bridge targeted tests (27 total) PASS, using actual content-verified M1/P/exposure/bridge module files and locally simulated integrated_flow/render_report; `compileall` PASS. Exact authored blob SHA parity and narrow GitHub diff check. No source-authentic private holdings, full current M7a canonical regression or comprehensive 36-decision acceptance. All 36 matrix rows retained, only #18 evidence description updated, still PARTIAL.

**Resource/stop:** STANDARD; one bounded PR, no merge. Additional financial source corroboration and specialized PI semantic review remain separate from this component build.
