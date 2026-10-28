# Work Order — M5 private fact-to-source coherence in manual R1 flow

**ID:** `WO-FIN-FS-R1-M5-IR-FACT-SOURCE-ALIGNMENT`  
**Primary role:** Program Manager, executing directly at CEO request (no Codex). **Why now:** GitHub hygiene issue #275 closed with eight surviving refs and merged PR #278; the 36-decision integrated build continues. Current M7a can accept IR `VERIFIED` labels while supplied provenance observations for the same fact are missing or unusable, without a per-fact alignment review.

**Objective:** Add a small deterministic, **private-only** M5 helper to reconcile original IR fact IDs and original caller statuses with the private M2 source annex; surface missing, conflicted, incomplete/unavailable and unsupported verified-label cases, preserving source rights and fact uncertainty. Optionally attach in M7a and keep any warning generic in the report.

**Sources:** Constitution → Governance → Current State → PM charter → this Work Order; CEO 2026-10-28 build-first decision, `AGENTS.md`, AI-native R1 Delivery Plan, existing M2 `source_fusion.py` and M7a `integrated_flow.py`, `reporting.py`, 01–36 ledger (#06/#07/#28).

**Authorized scope:** New `ai_native/fact_evidence_alignment.py` and `tests/test_ai_native_fact_evidence_alignment.py`, limited `ai_native/integrated_flow.py` and its synthetic tests, plus this WO, M5 note, manual runbook and three ledger rows kept `PARTIAL`. No writes to protected docs, V1 code, historical evidence, financial data, branch cleanup or operating settings.

**Prohibitions:** No external source or private-account access, source-status upgrade, publication of fact identities into GitHub, trading, model/policy changes, automatic inter-Project execution, scheduled research, spending, device operations or branch deletion. $0 incremental external financial-data cost.

**Validation:** New helper 17/17 synthetic tests PASS and compilation PASS locally. Exact source/test Git blobs must match locally tested files. Three integration regressions authored but remain `NOT_RUN` in a complete canonical checkout; do not claim CI/whole-system or original-source verification. Readiness gates unchanged. **Status:** CANDIDATE / REVIEW REQUIRED. **Stop:** PR only; CEO approves merge separately.
