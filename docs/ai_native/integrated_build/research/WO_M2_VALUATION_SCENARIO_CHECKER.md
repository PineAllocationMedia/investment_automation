# Work Order — M2 deterministic valuation scenarios, without forecast authority

**ID:** `WO-FIN-FS-R1-M2-VALUATION-SCENARIO-CHECKER`  
**Primary role:** Investment Research (financial method; subject review pending). **PM:** bounded implementation/integration preparation, independent specialist assurance not claimed.  
**Why now:** CEO merged PR #268; the 2026-10-28 approved build-first decision calls for a complete AI-native 36-decision first version before comprehensive evaluation. M2 valuation R1 defines bear/base/bull price-CAGR and cash-flow IRR mathematics, but no implemented checker existed.

**Objective:** pure, source-neutral deterministic calculation of annualized conditional scenario returns from already supplied security-class-compatible price, terminal-per-share valuations, explicit known or UNKNOWN distributions and assumption refs. Integrate optional private result into M7a (IR-only or IR+PI) without promoting to expected return, decision-grade source truth, portfolio trade or VFV alpha.

**Sources (minimum):** Constitution → Governance → Current State → PM charter → this WO → `AGENTS.md`, CEO 2026-10-28 Registry decision, R1 `VALUATION_R1.md`, M2 Research assembly WO, M7a flow and 01–36 coverage. No change to V2 policy, protected charter or production.

**Change scope:** new `ai_native/valuation_scenarios.py` + isolated synthetic tests; narrow opt-in parameter in `ai_native/integrated_flow.py` and `ai_native/session_bridge.py`; append method/runbook; update only #21 coverage statement; this nonprotected WO. Strict zero extra financial-source cost, no web scraping or credential access, no private portfolios committed, no trading, scheduling, Model V1/V2 changes, automatic Project calls, policy change, production or canonical merge.

**Validation:** 26 isolated targeted helper tests and Python compile PASS in local 3.13; exact Git blobs/commit scope checked. Actual-repository M7a regression **not run**; source authentication, quantitative normalized-earnings review, distribution source rights, and 36-decision comprehensive acceptance **not claimed**. Reviewer should check IRR assumptions and input/basis semantics before merging.

**Stop:** one PR, CEO merge decision separately. Status `CANDIDATE_M2_SCENARIO_ARITHMETIC / NOT_DECISION_GRADE / NO_VFV_ALPHA`.
