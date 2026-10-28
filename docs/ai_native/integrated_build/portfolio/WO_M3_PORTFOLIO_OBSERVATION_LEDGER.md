# Work Order — M3 private portfolio observation ledger and session interface

**ID:** `WO-FIN-FS-R1-M3-PORTFOLIO-OBSERVATION-LEDGER`  
**Primary capability:** Portfolio Intelligence; implementation prepared by Program Manager, independent PI/Architecture & Audit review not claimed.  
**Why now:** PR #265 merged at `d454b895275ecab89bda87934c5fa5f1b794c721`; the CEO's validated sequencing requires a complete 36-decision R1 functional build **before** comprehensive integrated acceptance. The existing P-record method was documentation-only; missing/partial portfolio fields could not be guarded by executable logic.

**Objective:** Create one pure-Python private ledger from a dated, explicitly scoped CEO-provided portfolio transcription; enforce field-level visibility, cash/denominator/FX/date/private-public distinctions; produce conditional scoped weights only with complete compatible evidence; connect this ledger to the M1→M7a manual PI session bridge without asserting Project, Blossom or broker access.

**Sources:** Constitution → Governance → Current State → PM charter → this WO → `AGENTS.md`, `OBSERVATION_AND_ROOM_R1.md`, `WO_M3_PORTFOLIO_ASSEMBLY.md`, M1/M7a bridge, Operating Contract, the CEO 2026-10-28 decision and 01–36 coverage.

**Files authorized:** new `ai_native/portfolio_observation.py`; narrow optional parameters/guard in `ai_native/session_bridge.py`; two synthetic unit-test files; updates only to nonprotected M3 method, M7a runbook and exact #16/#17/#18 ledger descriptions; this WO. All example names and amounts are synthetic and cannot be interpreted as the user's finances.

**Authority / prohibitions:** read-only arithmetic on supplied data; no user account access, private screenshots/raw exports stored in GitHub, automatic screenshot/OCR, claims of live Blossom integration, financial advice, trades, policy change, V1/V2 code, automatic Projects, schedules, source rights bypass, spending, production/deployment, protected docs or canonical merge. Hard $0 external financial-data cost.

**Validation and effort stop:** Python standard library only; local 19 helper + 7 bridge integration + 18 pre-existing local bridge seam tests and syntax compile, using local M7a/reporting stubs rather than a complete-repo integration. Exact Git blob parity and 36-row matrix reconciliation required. Stop at one new PR; independent code/security review and full checkout regressions remain prerequisites for higher-confidence integration claims. Comprehensive 36-decision evaluation deferred until complete functional assembly.

**Status:** `CANDIDATE_COMPONENT_PREPARED / NO_PORTFOLIO_READY / NO_REAL_BLOSSOM_SOURCE`; human-reviewed CEO merger remains separately required.
