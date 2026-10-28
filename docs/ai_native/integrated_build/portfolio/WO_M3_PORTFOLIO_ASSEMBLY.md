# Work Order: M3 Portfolio Intelligence R1 — integrated functional assembly

**ID:** WO-FIN-FS-R1-M3-PORTFOLIO-ASSEMBLY
**Primary specialist role:** Portfolio Intelligence; PM prepared the initial implementation; Portfolio Intelligence subject review is pending.
**Status:** CANDIDATE_COMPONENT_ASSEMBLED / NOT_INSTALLED / NOT_PORTFOLIO_READY
**Why now:** PR #254 merged. This is M3 in the one integrated 36-decision build, not another discovery/qualification pilot.
**Context:** Constitution, Governance, Current State, Program Manager charter, CEO 2026-10-28 build-first decision, 36-decision Blueprint, integrated Operating Contract, approved PI v0.2 instructions and PR #253 PI R1 Project-setting candidate. Respect relevant V2 allocation/position lifecycle principles, but do not import V1/V2 execution policy into this new AI-native tool.

## Objective and interfaces
Produce a usable Portfolio Intelligence workflow for private read-only/screenshot-based observations, IR→PI evidence inheritance, portfolio room, contribution prioritization, known transaction costs, and exceptional thesis-linked lifecycle reviews. Supported by a narrowly scoped deterministic **gross-only** arithmetic helper, never an automatic allocation optimizer.

**Inputs:** dated user-supplied portfolio/screenshot/export or actually verified authorized Blossom view; incoming IR_CAPSULE plus recoverable S/F/K/V facts; strategy/horizon/account type and broker/FX/fee/tax parameters if known. Missing fields stay UNKNOWN.
**Deliverables:** OBSERVATION_AND_ROOM_R1.md; CONTRIBUTIONS_AND_COSTS_R1.md; LIFECYCLE_AND_HANDOFF_R1.md; RUN_REQUEST_PI_R1.md; standalone pure-Python ai_native/contribution_math.py, with synthetic unittest coverage.
**Correspondence to 36 decisions:** #16–18, #22, #24–25, #32 and #35; other decisions remain on the common integrated-build matrix.

## Authority, safety and prohibitions
Read-only, supervised and bounded. No real portfolio data, secrets or account identifiers in GitHub; no direct brokerage access, live-trade action, private-profile reuse for Media, autonomous scheduling/Projects, source-rights bypass, paid external financial data, V1/V2 runtime edit, new investment policy, spending or deployment. Unattended developer orchestration remains paused.

**Resource/complexity:** STANDARD; local Python standard library only for precise arithmetic. **Proposed repo changes:** new docs in this folder, one new ai_native Python package, and new synthetic tests. No production runner integration. **Validation:** local isolated unittest, syntax check, source/contract cross-references, scope and privacy; do not claim a live Blossom integration or after-cost recommendation. **Stop:** PR before canonical merge; comprehensive R1 acceptance only after complete assembly.

**Next dependency:** M4 report, weekly workflow and governed memory, then coordinated decision-coverage audit, actual Project-settings adoption and whole-system evaluation. Portfolio Room cannot be validated until the CEO provides actually observable private inputs under explicit scope.
