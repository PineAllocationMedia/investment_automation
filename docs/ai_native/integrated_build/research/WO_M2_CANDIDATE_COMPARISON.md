# Work Order — M2 guarded comparison of candidate research scenarios

**ID:** `WO-FIN-FS-R1-M2-CANDIDATE-COMPARISON`  
**Primary role:** Investment Research. **Implementation preparation:** Program Manager; no independent IR or Architecture & Audit specialist review claimed.  
**Why now:** PR #272 CEO-merged at `ab5981cfe11effabdcf43662e497c062d00e92d4`. The CEO-approved sequence remains complete functional 36-decision assembly first, one comprehensive assessment later. M2 has single-company scenario arithmetic and M3 a conditional Portfolio Room research packet, but no unified multi-security scenario comparison.

**Objective:** Build a small private, deterministic 2–6 candidate comparison calling the already implemented per-security `valuation_scenarios.py`, preserving same request identity/date, same horizon and quote dates, currency and return measure; compare only genuinely comparable BEAR/BASE/BULL annual percentages, with no probability, ranking, alpha, net economic certainty or trade. Attach as optional `candidate_comparison_inputs` in the existing M1/M7a manual flow; no new Project runtime.

**Minimum sources:** Constitution → Governance → Current State → Program Manager charter → this WO → `AGENTS.md`, Strategy, CEO-approved 36-decision Blueprint, `VALUATION_R1.md`, existing R1 M2 source/evidence and M3 room contracts, current M7a code and ledger #21. Relevant V2 comparator requirements remain historical intellectual constraints; no automatic V2 policy or method mutation.

**Files and scope:** new `ai_native/candidate_comparison.py` and synthetic tests; only optional input/return in `ai_native/integrated_flow.py` and `ai_native/session_bridge.py`; this WO, one nonprotected M2 method, R1 runbook addition, #21 evidence wording (still PARTIAL). No CEO_PROTECTED changes.

**Prohibitions:** no scraping, external subscriptions/spend, source-rights certification, real portfolio records in GitHub, speculative market timing, FX forecasts, investment ranking, portfolio optimizer/trade, V1/V2 policy edits, automatic ChatGPT Project calls, unattended worker, scheduling, deployment or canonical merge. $0 incremental external financial-data cost.

**Verification:** 20 local synthetic tests with exact current valuation checker and compile PASS; GitHub source and test blob parity, constrained diff and 36-row ledger. Real canonical M7a/checkouts and specialist math review remain to be run before assurance; no claims of live source, Blossom, Work, readiness or 36-decision acceptance.

**Status/stop:** `COMPONENT_PREPARED / NO_DECISION_GRADE_CANDIDATE_RANKING`. Standard effort. Open one PR, stop. CEO alone authorizes merge.
