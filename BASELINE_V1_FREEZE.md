# Baseline V1 freeze contract

## Frozen identity

- Baseline ID: `VALIDATION_BASELINE_V1`
- Investment rules: `2026-08-23-allocation-room-integrity-v7`
- Validation schema: `2026-08-23-validation-architecture-v3`
- Auto-tuning policy: `PROPOSAL_ONLY`
- Baseline start: `INVESTMENT_AUTOMATION_BASELINE_STARTED_AT` or `config/baseline.yaml:baseline_started_at`, populated only at the approved Baseline deployment. A blank value means that Baseline forward evidence has not started. The environment variable is preferred on the deployed host so the frozen Git tree remains clean.

The baseline ID is additive validation metadata. It does not replace or advance `MODEL_RULES_VERSION`.
The approved non-baseline configuration set is pinned by `approved_config_fingerprint`; decision-capable analysis fails closed on unreviewed configuration drift.

## Frozen scope

Baseline V1 observes the current approved investment model. Company scoring, weights, conviction, CAGR, valuation, VFV hurdle, discovery, promotion, add/sell rules, P3 drawdown policy, P4B allocation-room policy, concentration logic, tax/friction investment treatment, ranking, sizing, overflow, defensive allocation, and the current universe are frozen.

The authoritative predecessor safeguards remain:

- P1: field-level provenance and freshness.
- P1B: research semantic integrity.
- P2: validation-authority architecture.
- P3: deep averaging-down evidence safeguard.
- P4B: shared allocation-room integrity.

P5A deferred global coverage. Global discovery, economic-entity architecture, new currencies/tickers, P5B, and global shadow collection remain outside Baseline V1.

## Evidence authority

Only genuine `SCHEDULED_DECISION` and `MANUAL_DECISION` observations generated at or after the approved `baseline_started_at` may carry `BASELINE_V1_FORWARD_OBSERVATION` status. Pre-Baseline history remains visible but separate. Diagnostic, development, maintenance, zero-capital, failed-input, and legacy-uncertain runs cannot increase Baseline maturity.

Theoretical historical backtests remain `MECHANICAL_DIAGNOSTIC`. Legacy partially recoverable walk-forward records do not become genuine OOS evidence. Evidence maturity measures observation depth, not investment skill.

Every decision-capable run records a compact manifest linking the exact Git SHA, versions, purpose, fingerprints of relevant configuration and inputs, dependency environment, consumed market/research state, and deterministic decision output. Failed critical-input runs record no allocation and no forward-evidence authority.

## Allowed operational maintenance

Subject to normal tests and review, the following are allowed when they restore intended semantics without changing investment policy:

- Critical bug and security fixes.
- Source-outage and parser-compatibility repairs.
- Operational reliability, cache, storage, and bounded-retention maintenance.
- Report-formatting fixes.
- Data-quality corrections.

Any change that can alter recommendations must be reviewed explicitly for `MODEL_RULES_VERSION` impact.

## Forbidden changes

The freeze prohibits new factors, scores, weights, optimized thresholds, allocation strategies, optimizer/covariance redesign, geography coverage, global shadow collection during the intended Baseline observation period, P5B, automatic self-modification, and new alpha claims based on theoretical backtests.

## Breaking the freeze

A behavior-changing modification requires an explicit code change, a new `MODEL_RULES_VERSION` where appropriate, targeted and complete regression tests, deterministic decision blast-radius analysis, one reviewed pull request, external review, and controlled deployment. No audit, scheduled job, maintenance command, walk-forward process, or improvement command may self-apply a rule change.

## Repository governance

GitHub administrators should manually protect `main`: require a pull request, at least one external approval, and the `Baseline V1 CI / test` status check before merge; disallow force pushes and branch deletion. These account-level settings are intentionally not changed by repository code.
