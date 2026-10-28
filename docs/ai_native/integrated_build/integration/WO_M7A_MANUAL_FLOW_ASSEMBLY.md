# Work Order — M7a manual integrated-flow assembly

**WO:** `WO-FIN-FS-R1-M7A-MANUAL-INTEGRATION`  
**Primary role:** Program Manager (cross-component integration), with subsequent Product & UX review and specialist verification of IR/PI boundaries.  
**Status:** `COMPONENT_INTEGRATION_CANDIDATE / NOT_INSTALLED / NO_END_TO_END_ACCEPTANCE`.

## Objective and why now
PR #257 merged and the five preceding R1 modules are in GitHub. Connect M2 (research evidence), M3 (portfolio/contribution arithmetic), M4 (reporting/memory proposal) and M5 (fact arithmetic) through one **manual-transfer component**, without creating a new agent network, another discovery pilot or a scheduling dependency. This is assembly work, **not** the comprehensive test of all 36 decisions.

## Minimum canonical context
`PAM_PROJECT_CONSTITUTION.md` → `governance/PAM_GOVERNANCE.md` → `governance/PAM_CURRENT_STATE.md` → `governance/roles/PROGRAM_MANAGER.md` → `DECISIONS.md` (2026-10-28 build-first) → `docs/strategy/PAM_FINANCIAL_SYSTEMS_AI_NATIVE_REFORM.md` → `docs/ai_native/integrated_build/DELIVERY_PLAN.md` / `OPERATING_CONTRACT.md` → M1–M5 methods. Respect `AGENTS.md`.

## Bounded implementation
Introduce `ai_native/integrated_flow.py`, an executable **pure in-memory** protocol adapter with `assemble_manual_run()`, and synthetic tests. It consumes a CEO-initiated request and already-researched `IR_CAPSULE`; accepts optional PI result only when the identical original IR capsule is forwarded. It uses existing M5/M3 arithmetic helpers if expressly supplied with calculations or a gross-only proposed contribution and delegates Markdown rendering to M4.

Include `MANUAL_FLOW_RUNBOOK_R1.md` showing exact input schema, real handoff path, supported research-only route and conditional portfolio route. No private data in committed examples.

**Authority:** new bounded files and PR only. **No** production, trade, autonomous cross-Project messaging, source retrieval/certification, method/policy amendment, source-rights bypass, paid data, device changes, external contact, automatic follow-up or scheduled work. No V1/V2 code edits, no protected changes and no GitHub storage of personal holdings.

**Resources:** existing GitHub and Python standard library; $0 external financial-data costs. **Complexity:** STANDARD. **Validation:** 14 synthetic tests against exact existing component files, compileall, source blob parity, docs references, diff scope. This is not proof of live ChatGPT Project installation, Blossom access or research source authenticity. **Stop:** PR before CEO merge.

## Next coordination
After this PR is approved, perform Product & UX specialist review/adoption of the 3 candidate Project instruction sets and their actual method availability; document observed manual transfers. M6 legacy device inventory stays separately scoped (read-only only, no cleanup). Then comprehensive M7 whole-system evaluation and individual readiness gates. CEO alone authorizes Project-setting installation where actual account action is required, canonical merge and any production change.
