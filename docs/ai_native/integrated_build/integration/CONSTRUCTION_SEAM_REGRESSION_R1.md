# R1 — Construction-time cross-module seam regression

**Status:** `CONSTRUCTION_CHECKS_ONLY / NO_36_DECISION_ACCEPTANCE / NO_EXTERNAL_SOURCE_OR_PORTFOLIO_PROOF`  
**Purpose:** protect the functionality already built in M1 (manual handoffs), M2 (source provenance + valuation), M3 (private P-ledger + fund look-through), M4 (private memory review gate), and their shared ANALYSIS_ID and dates. This is *one* test file using **synthetic** values and does not create a pilot, production integration or new financial-data dependency.

## Run from the actual repository checkout

```sh
python -m unittest -v tests.test_ai_native_construction_contracts
python -m unittest discover -s tests -p 'test_ai_native_*.py'
```

These are ordinary, **on-demand component checks**, not a weekly task or a comprehensive acceptance gate. No network, Blossom, accounts, passwords, real holdings, GitHub writes, source retrieval, paid source usage or production changes are required.

## What the new test file enforces

- All five independently prepared objects (P observation, exposure, source annex, scenario valuation, private history) keep an identical `ANALYSIS_ID`, while original publication, quote and observation dates remain distinct. No source or value is automatically promoted to `VERIFIED`.
- An incomplete source/ETF/visible-account scope cannot yield unsupported total issuer concentration or `ROOM_EVIDENCE_SUPPORTED`. Known direct issuer plus known fund constituent exposure is a **lower bound**, and unknown fund residual is preserved.
- An uncertain source-use right is not treated as licensed evidence; distribution-unknown scenario CAGR is not total return or benchmark alpha.
- A memory publication gate is always withheld and contains no research-case identity. Private contents remain in the private proposal only.
- The true `complete_manual_session` boundary waits for the original IR capsule, preserves it unchanged for PI, refuses unsupported cross-route optional inputs, and passes supplied source/valuation annexes to M7a without invoking another ChatGPT Project.

## What was really executed during authoring

The 12 newly authored tests **PASS** in a local reconstruction containing the **exact GitHub blob content** for `request_assembly.py`, `session_bridge.py`, `portfolio_observation.py`, `portfolio_exposure.py`, `source_fusion.py`, `valuation_scenarios.py` and `research_memory.py`. Full same-environment discovery of locally available M1–M4 test files passed **130 tests**, including these 12, on Python 3.13. The checked Git blob for `tests/test_ai_native_construction_contracts.py` is tracked alongside this document.

**Crucial boundary:** the reconstruction substitutes local test doubles for `integrated_flow.py` and `reporting.py` because the complete canonical checkout was unavailable in the execution container. Only the M7a forwarding-invocation test intentionally mocks `assemble_manual_run`; other new tests never invoke those substituted modules. **The actual current GitHub M7a and renderer regression, all existing repository tests, CI execution, real Work/Blossom account observation, genuine financial filings and whole-system 36-decision evaluation were NOT run.** Do not advertise the 130 local tests as full current-repository test completion. A canonical checkout must run the commands above before higher-confidence merge/readiness claims.

## Follow-on

The suite is an anti-regression *construction tool*, not an alternative to full functional assembly. Continue implementing missing IR/PI/CC functional paths. On completion of the 36-decision release, perform the CEO-approved one comprehensive integrated acceptance with authentic sources, private authorized data, privacy, manual handoffs and workload observation. No readiness gates, account or production authority arise from this suite.
