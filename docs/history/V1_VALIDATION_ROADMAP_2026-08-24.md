# Archived V1 Validation Roadmap — 2026-08-24

> **HISTORICAL V1 PLANNING CONTEXT ONLY.**
>
> This file preserves the complete former contents of the root `ROADMAP.md`.
> It is not PAM's current roadmap. Use `PAM_ROADMAP.md` for current technical
> and program sequencing, and `governance/PAM_CURRENT_STATE.md` for current
> administrative and operational state.

---

# ROADMAP — investment_automation

**Phase:** Validation / maturation
**Last updated:** 2026-08-24

## 1. Governing objective

The project now prioritizes long-term reliability, robustness, auditability, and confidence in investment decisions. Evidence accumulation and stability take precedence over feature expansion. This roadmap governs maturation of the validated system; it is not a development backlog.

Future development priority is:

1. Confidence in decisions.
2. Hidden-bug and edge-case reduction.
3. Data quality and provenance.
4. Genuine forward and walk-forward validation.
5. Decision stability and low unnecessary turnover.
6. Operational reliability.
7. Low-risk maintainability and refactoring.
8. New functionality only where evidence demonstrates a genuine long-term investment benefit.

## 2. Completed validation program

The pre-Baseline program is complete:

- **P1 / PR #14 — COMPLETED:** Provenance and freshness correction.
- **P1B / PR #15 — COMPLETED:** BNCD / Morningstar research semantic integrity.
- **P2 / PR #16 — COMPLETED:** Validation architecture hardening.
- **P3 / PR #17 — COMPLETED:** Deep averaging-down safeguard and combined portfolio visibility.
- **P4A — COMPLETED:** Marginal portfolio concentration audit.
- **P4B / PR #18 — COMPLETED:** Allocation-room integrity hardening.
- **P5A — COMPLETED:** Global Equity Coverage Readiness Audit. Final disposition: **SHADOW-ONLY AFTER BASELINE V1**.
- **P6 / PR #19 — COMPLETED:** Final Baseline V1 hardening and freeze.

The frozen Baseline identity is:

- Baseline ID: `VALIDATION_BASELINE_V1`
- Investment rules: `2026-08-23-allocation-room-integrity-v7`
- Validation schema: `2026-08-23-validation-architecture-v3`
- Auto tuning: `PROPOSAL_ONLY`

## 3. Current state — Baseline V1 awaiting deployment

P6 is merged and the Baseline V1 implementation is complete. The approved code is ready for controlled deployment.

**BASELINE IMPLEMENTATION COMPLETE does not mean BASELINE FORWARD OBSERVATION ACTIVE.**

Baseline V1 has not started. `baseline_started_at` remains unset and Baseline status remains `PENDING_APPROVED_DEPLOYMENT`. Chromebook deployment and activation are the immediate next operational step. No pre-deployment run counts as Baseline V1 forward evidence.

## 4. Immediate next operational milestone

The next milestone is controlled production deployment and verified Baseline activation:

1. Protect GitHub `main` where practical.
2. Deploy the approved `main` to the Chromebook under controlled conditions.
3. Verify Python and dependency compatibility.
4. Verify Google Drive input synchronization.
5. Complete the health check.
6. Where appropriate, perform a controlled zero-capital, non-authoritative smoke validation.
7. Verify timers and services.
8. Set the approved Baseline start timestamp only after production deployment is verified.
9. Confirm that the first positive-capital scheduled or manual decision after activation is correctly classified as Baseline V1 forward evidence.

## 5. Baseline V1 forward-validation phase

After verified deployment and activation, the main project phase becomes **FORWARD VALIDATION / EVIDENCE ACCUMULATION**.

During this phase, investment logic remains frozen while normal scheduled and manual decisions continue. Genuine forward/out-of-sample observations, walk-forward history, account performance history, decision manifests, and source/data-health history accumulate. Tuning remains proposal-only.

Observation should assess:

- recommendation stability and unnecessary turnover;
- reliability across market regimes;
- data-source robustness and operational reliability;
- decision quality;
- benchmark-relative performance using valid return methodology; and
- rare failure modes.

Evidence maturity describes the quality and depth of observation. It does not prove alpha or investment skill.

## 6. Evidence gates for reopening development

Major behavior-changing work may be reconsidered only after sufficient high-quality Baseline evidence has accumulated and an explicit review authorizes it. Several months of forward evidence may be expected, but elapsed time alone is not an authorization gate.

The review should weigh coverage across market conditions, observation quality, decision stability, turnover, source and operational health, performance-methodology validity, unresolved failures, and the expected reliability benefit of any proposed change.

No new scoring mechanism, allocation architecture, optimizer design, or global direct-equity implementation is authorized during the intended observation period.

## 7. Global equity roadmap — P5A → P5B/G1 → G2 → G3

International coverage remains a real future project; it has not been abandoned.

### P5A — COMPLETE: readiness audit

The completed audit establishes the future work required. Its approved disposition remains **SHADOW-ONLY AFTER BASELINE V1**.

### Baseline V1 forward-validation period

Baseline evidence must first accumulate sufficiently. An explicit evidence review must then authorize reopening the global chantier.

### P5B / G1 — GLOBAL SHADOW FOUNDATION

Initial work should establish issuer and economic-entity identity; ADR, native, and cross-listing handling; currency provenance; market-cap currency normalization; IFRS and fundamental semantic validation; Canadian-investor implementation friction; broker and instrument eligibility; and reuse of P1/P1B provenance and reliability controls.

G1 has no allocation authority.

### G2 — VERIFIED GLOBAL SHADOW ANALYSIS

Only markets and instruments with demonstrated reliable data semantics may enter verified shadow analysis. Foreign companies may be analyzed and compared with VFV, but cannot automatically receive capital.

### G3 — LIMITED GLOBAL ALLOCATION PILOT

G3 may be considered only if shadow evidence demonstrates sufficient reliability and explicit external approval is granted. It is not promised and may never be authorized.

Across all global stages, international companies should become easier to **discover**, not easier to **qualify**. There is no geography bonus. Foreign securities must meet the same or stricter quality, reliability, valuation, durability, expected-CAGR, opportunity-cost, and portfolio-guardrail standards. Tax, foreign-exchange, and trading friction remain separate from intrinsic company-quality assessment.

## 8. Allowed maintenance during the freeze

Baseline does not mean zero maintenance. With normal review, allowed work includes critical bug and security fixes; source-outage and parser-compatibility repairs; operational-reliability fixes; cache and storage maintenance; report-formatting corrections; and data-quality corrections that restore intended semantics.

Any change that can affect recommendations requires explicit review for `MODEL_RULES_VERSION` impact.

## 9. Explicitly deferred work

During the intended Baseline observation period, defer:

- new factors, scores, and scoring mechanisms;
- score-weight or threshold optimization;
- new allocation strategies or architecture;
- Markowitz/covariance optimizer work;
- new geography allocation;
- P5B / global shadow work;
- global direct-equity implementation;
- alpha claims based on theoretical historical backtests; and
- large architectural refactors without a reliability justification.

## 10. Long-term decision rule

Preserve the frozen system while trustworthy forward evidence accumulates. Reopen behavior-changing development only when evidence quality, explicit review, and a credible long-term reliability or investment benefit justify the added complexity. Prefer a stable, auditable decision process over a larger feature set.
