# VFV standalone forward Expected Return v1

> This contract implements one bounded standalone VFV research diagnostic under
> explicit CEO policy `PAM_VFV_FORWARD_ER_POLICY_2026_10_01_V1`. It is not a
> company comparator, benchmark forecast, recommendation, allocation, executable
> return, production integration, or generic ETF model.

## Verified base and authority

| Item | Value |
| --- | --- |
| Canonical branch | `origin/model-v2/expected-return-challenger` |
| Starting commit | `da1ee32d58a0d60ca89ea3e373040b82878fd686` |
| Starting tree | `812927036e4977b74980d6ba6b2c7322a112b226` |
| Implementation branch | `codex/vfv-standalone-forward-er` |
| Policy authority | `PAM_VFV_FORWARD_ER_POLICY_2026_10_01_V1` |
| Methodology | `2026-10-01-vfv-normalized-unit-cashflow-irr-v1` |

The worktree and index were clean before implementation. V1 remains frozen
operational authority and V2 remains a challenger. No merge, deployment,
production authority, self-tuning, comparator, FX acquisition, source expansion,
company Expected Return policy change, or model-rules change is authorized.

## Public analytical boundary

```python
calculate_vfv_forward_expected_return(
    qualification: VFVCurrentEvidenceQualification,
    request: VFVForwardERRequest,
) -> VFVForwardERDiagnostic
```

The request carries only the exact instrument/basis and anti-drift pins for the
upstream semantic/evidence identities and approved policy ID/hash. It contains no
scenario values, horizon, approval boolean, qualification boolean, expense
assumption, growth assumption, or terminal multiple. The function accepts only
the exact canonical VFV qualification type and never parses Vanguard artifacts.

Closed statuses are `AVAILABLE`, `UNAVAILABLE`, `UNSUPPORTED`, and
`SOURCE_CONFLICT`. Upstream closed statuses retain their meaning. A policy-pin
mismatch is `UNAVAILABLE`; a detached upstream identity mismatch is
`SOURCE_CONFLICT`; a non-VFV instrument or foreign analytical basis is
`UNSUPPORTED`. Essential missing facts, unusable MER/TER semantics, or numerical
failure are `UNAVAILABLE`. No failure becomes a bear case or poor-economics claim.

## Fixed content-addressed policy

`src/vfv_forward_er_policy.py` contains the sole repository-approved policy. Its
canonical JSON serialization is deterministic, and its pinned SHA-256 is:

```text
31dbebd0545c233c4913dad1915dfd2eb23d91481019fec078b245541ef0e645
```

The exact policy is:

- seven annual periods;
- bear/base/bull fundamental growth `0.00 / 0.03 / 0.05`;
- bear/base/bull terminal weighted P/E `12 / 16 / 20`;
- normalized initial unit value `V0 = 1`;
- principal return type
  `NOMINAL_PRE_HOLDER_TAX_UNIT_HOLDER_CASHFLOW_IRR`;
- FX basis `CONSTANT_TRANSLATION_NO_FX_CONTRIBUTION_MODELED`.

Changing any policy content changes the computed hash and requires a reviewed
repository change. Callers cannot substitute a policy object or dynamic values.

## Evidence and exact mathematics

The adapter requires qualified VFV identity, current CAD market observation,
provider trailing weighted fund-portfolio P/E, issuer trailing-12-month
distribution yield, distinct management fee/MER/TER facts, listed/base CAD
currency, field dates, fact-level evidence, and upstream identities.

The market price remains required context and lineage. It is never divided by
weighted P/E and never relabelled as ETF earnings, EPS, or normalized EPS. The
qualified weighted P/E is used directly as `M0`.

Source percentages cross to decimal-fraction arithmetic by dividing by 100:

```text
y0  = trailing-12-month distribution yield / 100
mer = MER / 100
ter = TER / 100
q   = (1 - mer) * (1 - ter)
```

Management fee remains separately visible and is not added to, or deducted in
addition to, MER and TER. Required expense facts must retain supported explicit
annual-rate/annualized-as-of-date semantics. The latest quarterly distribution
amount is retained upstream but is never annualized or extrapolated here.

All material Decimal derivations execute inside a fresh code-owned local context
with precision 28, `ROUND_HALF_EVEN`, `Emin=-999999`, `Emax=999999`, capitals 1,
clamp 0, and explicit invalid-operation/division-by-zero/overflow traps. This
preserves the original default-context economics while preventing ambient caller
or process Decimal precision, rounding, exponent, flags, or traps from becoming
an analytical input. No presentation quantization or arbitrary rounding is added.

For each fixed scenario:

```text
D1 = y0
Dt = y0 * (((1 + g) * q) ** (t - 1)), t=2..7

V7 = (((1 + g) * q) ** 7) * (MT / M0)

1 = sum(Dt / (1+r)^t, t=1..7) + V7 / (1+r)^7
```

`MT/M0` is an analytical relative-valuation factor, not an accounting fact.
The distribution continuation, wrapper-expense factor, growth assumptions,
terminal multiples, normalized unit basis, and zero-modeled-FX contribution are
policy or deterministic derived values, never source evidence.

## Shared numerical boundary and PR4A preservation

`src/annual_cashflow_irr.py` is the smallest semantic-neutral extraction of
PR4A's existing log-gross-return bisection and log-sum-exp residual calculation.
It accepts one positive initial value, nonnegative annual cash flows, and one
positive terminal value. It contains no company, ETF, evidence, policy, portfolio,
or recommendation semantics.

PR4A retains its private `_solve_return` compatibility boundary, constants,
public exception type, validation, seven-year company semantics, result shape,
and numerical output. That wrapper delegates to the shared solver and translates
the shared numerical exception into the unchanged PR4A exception. No IRR solver
was duplicated and no company policy was changed.

## Result and lineage

The principal scenario result semantics are exactly:

```text
VFV_INSTRUMENT_ER_NET_OF_WRAPPER_EXPENSES_PRE_EXECUTION
```

It includes modeled distributions, terminal normalized unit value, and approved
MER/TER treatment. It excludes holder taxes, brokerage, spread, slippage,
transactional FX, and execution costs. No numeric
`UNDERLYING_BENCHMARK_ECONOMIC_ER`, `VFV_EXECUTABLE_NET_ER`, or gross benchmark
result is exposed.

The diagnostic keeps factual inputs separate from fixed policy and derived
scenario results. Deterministic semantic identity binds the upstream semantic
identity, exact factual inputs, policy ID/hash, method, derived components,
confidence, statuses, and limitations. Deterministic evidence identity adds the
exact upstream evidence identity and fact-evidence records. A capture/provenance
change therefore changes evidence identity without necessarily changing the
economic semantic identity.

Semantic identity version
`2026-10-01-vfv-forward-er-root-problem-identity-v2` binds each scenario's
deterministic IRR problem specification: name, growth, terminal weighted P/E,
normalized initial unit value, annual distributions, terminal normalized unit
value, and result semantics. It intentionally does not bind `annualized_return`.
That public field remains the raw binary64 result of the shared solver and may
differ at insignificant final bits across legitimate platform/libm
implementations. This distinction is not economic rounding and does not imply
that 17 float digits represent forecast precision. The deterministic cash-flow
problem is the economic semantic identity; the float root is its computational
numerical realization.

## Confidence and limitations

An available result has typed local confidence:

```text
evidence_authority             = CURRENT_CAPTURE_BOUND
forward_assumption_dependence  = MATERIAL_FIXED_POLICY
currency_basis_status          = CONSTANT_TRANSLATION_POLICY_ONLY_NO_FX_AUTHORITY
overall_vfv_er_confidence      = LOW
```

LOW confidence never modifies or haircuts Expected Return. If essential evidence,
approved policy identity, expense semantics, or numerical representation cannot
be established, overall confidence is `NONE` and all numeric scenarios are
withheld. This is local Stage-B confidence only; it is not global Confidence and
contains no probabilities.

Every result retains all upstream limitations plus explicit research-only,
CURRENT-only, capture-bound, no-PIT, no-historical-as-of, no-underlying-currency,
no-hedge-status, no-FX-comparability, zero-FX-policy-only, no realized-CAD-FX,
no-provider-forward-estimate, no-underlying-benchmark-ER, no-executable-net-ER,
no-comparator, no-recommendation/allocation, no-execution/production, and
no-generic-ETF limitations.

## Isolation and validation

No V1/runtime, `main.py`, portfolio, PIT transport, recommendation, allocation,
execution, or production consumer imports this diagnostic. The modules perform
no file, environment, clock, provider, archive, network, or runtime-context I/O.
The existing qualified object is the only factual input.

Targeted coverage pins the policy hash and identities; exact formulas and ordering;
hand checks for zero growth/par valuation/zero expenses, growth, contraction,
expansion, distributions, expenses, and combined effects; absence of ETF-EPS
inference and latest-quarter annualization; management-fee non-duplication;
gross/net authority separation; confidence invariance; all closed outcomes;
numerical failure; deterministic identities; PR4A equivalence; and consumer
isolation.

Because the change extracts shared mathematics under `src/**`, the repository
risk-aware planner determines the final tier from the complete changed-file set;
the expected result is `FULL_PIT`. `MODEL_RULES_VERSION` remains
`2026-08-23-allocation-room-integrity-v7`.
