# Work Order — M4 reporting, routine intelligence and institutional memory (R1)

**ID:** `WO-FIN-FS-R1-M4-REPORTING-MEMORY`  
**Primary owner:** Financial Systems Command Center (functional reporting design); PM prepares coordination and governed memory boundaries. Product & UX review remains pending.  
**Why now:** PR #255 merged; the CEO-approved integrated-first program now needs report, weekly-intelligence and history outputs to connect M1–M3.  
**Status:** `M4_CANDIDATE_ASSEMBLED / NOT_INSTALLED / NOT_ROUTINE_READY`.

## Objective and minimum context
Make the integrated system capable of producing concise, decision-first reports, an on-demand weekly intelligence brief, a dated research-history proposal and reviewable method-improvement suggestions. The renderer takes **already supplied** research facts: it cannot independently retrieve, certify or archive sources. The first integrated evaluation of all 36 decisions occurs only after functional assembly.

**Canonical references:** Constitution → Governance → Current State → Program Manager charter → 2026-10-28 CEO decision → [36-decision Blueprint](../../../strategy/PAM_FINANCIAL_SYSTEMS_AI_NATIVE_REFORM.md) → [Operating Contract](../OPERATING_CONTRACT.md) → approved CC/IR/PI v0.2 and the R1 Project-setting candidates → this WO and the M2/M3 contracts. Report substantive conflicts with existing investment authority, do not resolve them by rewriting policy.

## Deliverables and roles
- `REPORT_AND_WEEKLY_R1.md` — reusable standard report and weekly format, prioritizing material changes and explicit no-action.
- `MEMORY_RECORD_R1.md` — proposed versioned research records, privacy tiers, append-only correction and provenance contract.
- `MONITORING_AND_METHOD_REVIEW_R1.md` — event specification, supported/manual fallback and human-approved version improvement.
- `RUN_REQUEST_CC_R1.md` — copy-ready on-demand workflow.
- `M4_COVERAGE_DELTA.md` — decision-number mapping and truthful status.
- `ai_native/reporting.py` — pure read-only formatter for supplied research/weekly packets; no network, persistence, scheduling or trades.
- `tests/test_ai_native_reporting.py` — synthetic component checks.

**Responsibility:** CC owns interpretation and concise report; Investment Research owns issuer claims and valuations; Portfolio Intelligence owns only actually observed portfolio implications; PM owns governance integration. No imaginary specialist delegation or automatic cross-Project calls.

**Authority:** create bounded new docs and isolated helper/tests on a feature branch, open PR; never merge, install Project settings or activate a scheduler without distinct CEO decision. No private holdings, subscriptions, new external costs, source-rights bypass, automated broker actions, production change, legacy code edits, secrets or PAM Media publication.

**Complexity / resources:** STANDARD, Python standard library only, zero external financial-data cost. **Validation:** isolated synthetic unittest, compile check, no side-effect review, GitHub diff and link scope. These checks do not establish routine readiness, financial truth or complete system acceptance.

**Next dependency:** M5 evidence/method checks, M6 separately authorized read-only knowledge inventory, then M7 36-decision integration/functional assembly assessment and CEO-approved Project-settings installation. Keep M4 in one release, not as a separate finance pilot. **Stop at PR before merge.**
