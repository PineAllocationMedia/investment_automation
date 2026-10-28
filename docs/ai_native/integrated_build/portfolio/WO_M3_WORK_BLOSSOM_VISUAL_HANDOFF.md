# Work Order — M3 Work-to-Blossom private visual packet adapter

**ID:** `WO-FIN-FS-R1-M3-WORK-BLOSSOM-VISUAL-HANDOFF`  
**Primary specialist:** Portfolio Intelligence (M3 observation contract), implemented through bounded Program Manager preparation; **independent PI/Product & UX review not claimed**.  
**Why now:** PR #266 merged on 2026-10-28. CEO-selected decision #16 prioritizes Work viewing the private Blossom portfolio *if compatible*, with manual screenshots as fallback. M3 currently consumes structured transcriptions but cannot distinguish Work reports from screenshot fallback at the input boundary.

**Objective and deliverables:** (a) pure in-memory adapter `ai_native/work_blossom_adapter.py` between a manually supplied Work observation and existing `prepare_observation_ledger`; (b) one synthetic test file; (c) one precise Work task/packet contract `WORK_BLOSSOM_HANDOFF_R1.md`; (d) small updates to M3 method, M7a runbook and the existing #16–18 coverage rows. **Do not construct another portfolio weight engine** or invent web automation.

**Sources/authority:** Constitution → Governance → Current State → PM role → this WO → `AGENTS.md`, CEO 2026-10-28 build-first decision and Blueprint §5.5/§7.3, `DELIVERY_PLAN.md`, `OBSERVATION_AND_ROOM_R1.md`, actual `portfolio_observation.py` and `session_bridge.py`. Public OpenAI Work and Blossom web capability documentation is context, not authorized account evidence.

**Authorized scope:** Pure Python standard library; structured private in-memory packet conversion, explicit source/field/coverage gating, copy-ready Work instructions, read-only contracts, tests and nonprotected documentation. $0 incremental external financial-data cost. No programmatic Work/Blossom login, internet scraping, credential handling, private account/file transfer, brokerage linkage, new subscription, unapproved device access, GitHub storage of holdings, public/private conflation, autonomous messaging, scheduling, production, V1/V2 rules changes, trading or deployment. CEO controls protected changes and canonical merges.

**Validation & stop:** one time-boxed code delivery and isolated synthetic adapter tests; exact blob parity, 36-row matrix and diff scope. Full integration tests and real Work/Blossom compatibility intentionally NOT RUN; remaining capability requires a separate authorized read-only Work session when the full assembly reaches the appropriate capability-evidence step. Do not pass PORTFOLIO-READY or all-36 acceptance. Stop at one PR before CEO merge.

**Status:** `ADAPTER_PREPARED / SIGNED_IN_WORK_BLOSSOM_POSTS_ACCESS_PROJECT_DOCUMENTED / PRIVATE_PORTFOLIO_VIEW_NOT_OBSERVED / FALLBACK_DEFINED`. See Media Prompt 4 and the 2026-10-22/2026-10-28 authenticated profile observations; these prove signed-in website navigation, **not** private position visibility or additional financial authorization.
