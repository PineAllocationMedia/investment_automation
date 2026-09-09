# PR4A — Expected Return calculation foundation

> PR4A calculates returns from explicitly qualified economic assumptions. It does not yet construct those assumptions automatically from the current V1 proxy architecture.

> A valid calculation is not evidence that the forecast assumptions are correct.

## Objective and authority

Provide a transparent mathematical foundation for the future **High-CAGR Quality
Compounder — Asymmetric** model: “The stock-picker should earn its right to replace
the market.” This module has **DIAGNOSTIC_ONLY** authority. It cannot select a
security, establish superiority to VFV, size a position, allocate capital or sell.

Only `src/expected_return_engine.py`, its synthetic unit tests and this document
are added. No existing decision or reporting path imports the engine. There are
no provider calls, file reads/writes, environment reads, current-clock reads,
randomness, runtime-context access or external dependencies in the module.
As with other modules in this repository, importing it through `src` first loads
the existing package initializer; the calculator itself never accesses runtime
context. Tests run through the repository's isolated code-only test runner.

## Supported methodology and identity

- Profile: `ORDINARY_COMPOUNDER` only.
- Metric: `NORMALIZED_DILUTED_EPS` only.
- Horizon: exactly seven annual periods.
- Return: `NOMINAL_PRETAX_EQUITY_CASHFLOW_IRR`.
- FX: `CONSTANT_FX`; all monetary inputs must already use one currency.
- Methodology: `2026-09-08-normalized-eps-cashflow-irr-v1`.
- Diagnostic schema: `2026-09-08-expected-return-diagnostic-v1`.

`MODEL_RULES_VERSION` remains `2026-08-23-allocation-room-integrity-v7`.
It controls decision/history compatibility and is not changed for this isolated
calculation contract. Diagnostic identity is separate.

## Exact mathematics

For each scenario, with observed purchase price P0, normalized diluted EPS F0,
annual per-share growth g1...g7, annual dividends D1...D7 and terminal P/E M7:

```text
Ft = F(t-1) * (1 + gt), t = 1...7
P7 = F7 * M7
P0 = sum(Dt / (1+r)^t, t=1...7) + P7 / (1+r)^7
```

Dividends are paid at each year-end. Year seven includes both D7 and P7;
P7 is the residual equity price, excluding the separately received D7.
With seven zero dividends:

```text
r = (P7 / P0)^(1/7) - 1
```

P0, F0 and M7 must be positive; gt must be greater than -1; Dt must be
nonnegative. These conditions produce a strictly decreasing present-value
function for r > -1 and a unique mathematical root: terminal value is positive.
No negative shareholder contributions or rights-issue cash calls are supported.

The solver bisects x = log(1+r), evaluating log present value with log-sum-exp.
This avoids forming huge discounted cash flows near -100%. The bracket is set by
the representable binary64 annual-return range, not financial return assumptions.
It allows at most 256 iterations, uses a log-return interval tolerance of 1e-14
times max(1, abs(x)), and checks the returned binary64 rate against a log-NPV
residual tolerance of 1e-10. Failed bracketing, representability, residual checks,
overflow, underflow or convergence raise `ExpectedReturnNumericalError`.

No intermediate calculation is rounded for presentation. This is a shareholder
cash-flow IRR, not a full enterprise DCF, probability-weighted forecast or assumed
reinvested portfolio CAGR. The cash flows, not a discount-rate guess, define the
reported annualized rate.

## Units

- Growth and returns are decimal fractions: `0.12` means 12%.
- Terminal P/E is a dimensionless positive multiple.
- Price, EPS and dividends are currency per common share.
- Currency is a three-uppercase-letter identifier. No FX conversion is performed.
- `share_basis` identifies the same security/share denomination and split basis
  across the request, monetary evidence and scenarios. EPS is explicitly diluted
  by its metric/accounting basis; this identifier is not a share-count forecast.
- Missing inputs use `None`/JSON null. Unknown dividends do not become zeros.
- Booleans, strings in numeric slots, NaN, infinity and numbers outside the
  finite binary64 input range are rejected.

Reports may eventually display whole percentage points. Computational precision
does not imply forecast precision. Display formatting is outside this module.

## Typed immutable input contract

The public function is:

```python
calculate_expected_return(request: ExpectedReturnRequest) -> ExpectedReturnDiagnostic
```

All records are frozen, slotted standard-library dataclasses. Collection fields
must be tuples, not mutable lists. There is no dictionary/JSON input parser and
no generic extra-field bag. Dataclass constructors reject unknown keyword fields;
the public function rejects mappings and validates all runtime field types.
Construction alone is not validation: calculation validates the full graph first.

`ExpectedReturnRequest` fields:

| Field | Meaning |
| --- | --- |
| `schema_version`, `methodology_version` | Exact supported identities |
| `as_of` | Offset-aware ISO timestamp supplied by caller |
| `profile`, `metric` | Explicit uppercase semantic identifiers |
| `currency`, `share_basis` | Common monetary/share denomination |
| `horizon_years` | Integer 7, not a floating-point or boolean value |
| `current_price` | Positive observed purchase price, or absent |
| `current_price_evidence_id` | Direct observed-price record ID, or absent |
| `scenarios` | Tuple containing exactly one `bear`, `base`, `bull` |
| `confidence` | `ConfidenceComponents` record |
| `evidence` | Tuple of `Evidence` records |
| `assumptions` | Tuple of `Assumption` records |

`Scenario` fields:

- `name`;
- `starting_eps_per_share`: qualified positive normalized diluted EPS, or absent;
- `growth_rates`: exactly seven per-share EPS growth rates, or absent;
- `dividends_per_share`: exactly seven nonnegative cash flows, or absent;
- `terminal_pe`: positive explicit assumption, or absent;
- `currency`, `share_basis`: must equal the request;
- `fundamental_refs`, `growth_refs`, `distribution_refs`, `terminal_refs`.

Each reference field is `References(evidence_ids=(), assumption_ids=())`.
Every material scenario component must have evidence and/or an explicit assumption.
Growth and terminal valuation always require an assumption; a terminal multiple
is never established as truth just by giving it an evidence label. Starting EPS
requires direct qualified evidence or an explicit normalization assumption with
supporting evidence. No normalization or price/PE inference is performed here.

An assumption with a literal value must match the scenario input exactly. A
rule-only assumption documents an upstream deterministic construction; PR4A
does not execute arbitrary rule text or prove that the upstream construction is
correct. The caller still supplies the exact seven-year numeric paths.

## Provenance contract

`Evidence` fields:

```text
id, field, value, unit, source_kind, source_reference, source_version,
published_at, available_at, captured_at, freshness_status, reliability_status,
currency=None, share_basis=None, period_start=None, period_end=None,
accounting_basis=None, parent_evidence_ids=()
```

Values can be finite numbers, immutable numerical tuples or nonempty descriptive
strings. `source_version` may contain an immutable source version or content hash.
It is an attribution requirement, not an assertion that PR4A fetched or verified
the external source. Optional fields are not required for irrelevant evidence.

Allowed source kinds: `OFFICIAL_CURRENT_DATA`, `MARKET_PROVIDER`,
`RESEARCH_REPORT`, `HUMAN_MANUAL`, `DERIVED`. Model assumptions are separate records.

Direct component evidence must use the following field/unit pairs:

| Component | Evidence field | Unit |
| --- | --- | --- |
| Purchase price | `current_price` | `CURRENCY_PER_SHARE` |
| Starting EPS | `normalized_diluted_eps` | `CURRENCY_PER_SHARE` |
| Growth | `per_share_eps_growth` | `DECIMAL_FRACTION` |
| Dividends | `dividends_per_share` | `CURRENCY_PER_SHARE` |
| Terminal valuation context | `terminal_pe` | `MULTIPLE` |

Direct normalized EPS evidence also requires accounting basis
`NORMALIZED_DILUTED_EPS`. Price and directly linked monetary evidence must match
the requested currency and share basis. Direct evidence values must equal the
economic inputs they purport to measure. Transformations belong in assumptions
with supporting evidence, not contradictory direct-evidence references.

`Assumption` fields:

```text
id, component, scenario, rationale, policy_version,
supporting_evidence_ids=(), value=None, rule=None
```

An assumption requires a literal value and/or nonempty deterministic-rule
description, a rationale and a policy version. Its component and scenario must
match each reference. A policy version is retained as supplied; it need not be
the calculator version, since the upstream assumption policy is separate.

All IDs are unique across evidence and assumptions. Dangling references,
duplicate references and cyclic evidence ancestry are errors. A derived record
cannot have become available before its parent evidence.

Timestamps require an explicit UTC offset; calculations compare UTC instants.
PR4A conservatively requires:

```text
published_at <= available_at <= as_of
available_at <= captured_at <= as_of
```

Thus later recapture of an old source is not supported by this initial contract;
PR4B would need an explicit historical-version attestation policy to permit it.
Future forecast target dates are allowed and distinguished from information
availability. Fiscal/target date ranges must be valid and ordered. An observed
current price cannot claim a future target date. This is local provenance
validation, not PR3 COMPLETE_PIT certification.

## Confidence and availability

`ConfidenceComponents` contains `fundamental`, `growth`, `distributions`,
`terminal_valuation`. Each is one of `NONE < LOW < MEDIUM < HIGH`.

For each component, confidence cannot exceed the caller's declared confidence
or the reliability of its linked evidence, assumption support and transitive
evidence parents. Price reliability also limits fundamental confidence.
Stale linked evidence caps the relevant component at LOW and produces a warning.
Unknown freshness or NONE reliability makes linked evidence unusable.
Unreferenced evidence is still schema/date-validated but does not change confidence.

- All effective components HIGH, and all essential inputs present: `AVAILABLE`.
- Valid complete inputs with one or more MEDIUM/LOW components: `DEGRADED`.
- Missing essentials, unsupported economics, unusable evidence or any essential
  NONE component: `UNAVAILABLE`, overall confidence NONE.

MEDIUM/LOW confidence never changes the computed return. NONE withholds numeric
returns rather than manufacturing a confidence-adjusted return. For any unavailable
request, all three numeric return/terminal-result fields are null; original input
assumptions remain visible. No partially available scenario ranking is published.

Confidence is not a probability, volatility measure or quality score. It cannot
validate the economic plausibility of a caller-supplied HIGH assertion.

## Scenario ordering

Bear, base and bull name economic assumptions. The complete calculated results
must satisfy `bear <= base <= bull` with no relabeling or sorting of returns.
Equal returns are valid. Crossing raises `ExpectedReturnError`.
The output orders named scenarios bear/base/bull regardless of input tuple order.
This is canonical serialization, not reassignment of economic labels.

## Result contract

The frozen `ExpectedReturnDiagnostic` exposes:

```text
schema_version, methodology_version, status, authority, as_of, horizon_years,
profile, metric, currency, share_basis, current_price, current_price_evidence_id,
return_basis, fx_basis, confidence, overall_confidence, scenarios,
evidence, assumptions, warnings, unavailable_reasons
```

Each `ScenarioResult` exposes:

```text
name, annualized_return, starting_eps_per_share, growth_rates,
dividends_per_share, terminal_eps_per_share, terminal_pe, terminal_price,
fundamental_refs, growth_refs, distribution_refs, terminal_refs
```

`result.to_dict()` returns a fresh JSON-compatible object nested under
`expected_return_diagnostic`, with a bear/base/bull scenario mapping and lists
for tuples. It never shares mutable internal state. Evidence/assumptions and
their references are canonically ordered, timestamps normalized to UTC and
warning/reason codes sorted. Repeated equivalent requests and reordered record
collections yield the same semantic output. No weighted expected return,
stock-minus-VFV spread, recommendation, winner label or target weight exists.

## Unavailable versus malformed

Missing price, normalized EPS, paths, terminal assumptions or essential evidence
are economic absence. Validly named unsupported profiles/metrics also produce
UNAVAILABLE. No ordinary-compounder fallback is used.

Explicit invalid values (nonpositive price/EPS/multiple, growth <= -1, negative
dividends), invalid types/lengths/identities, inconsistent currency/share basis,
bad timestamps, duplicate IDs, dangling links, contradictory direct evidence and
crossed scenario returns raise `ExpectedReturnError`. Invalid numerical behavior
raises its `ExpectedReturnNumericalError` subclass. Unexpected programming errors
propagate; there is no catch-all exception-to-UNAVAILABLE conversion.

The full schema is checked before economic availability. An unsupported profile
does not hide a malformed contract. Dataclass unknown-key/frozen-assignment errors
remain normal Python construction errors before the public calculation boundary.

## Anti-double-counting invariants

**Per-share EPS growth already includes buybacks and dilution. There is no additive
buyback yield and no second dilution subtraction.** Upstream assumption construction
must account for net issuance, SBC and the financing consequences of repurchases.

Dividends enter once in the cash-flow equation. No dividend yield is added again.
Terminal valuation enters once through terminal price. There is no fair-value
upside adjustment. The API has no historical CAGR, PEG, score, conviction,
quality/durability multiplier, opportunity-cost or allocation input.

PR4A cannot establish whether growth, dividends and repurchases are jointly funded.
That economic qualification belongs upstream; a mathematically valid assumption
set can still be economically wrong.

## Limitations and deferred work

Banks, insurers, REITs, asset managers, utilities, pipelines, resources, energy
cyclicals, turnarounds, loss-making companies and unknown profiles are unsupported.
There is no FCF/owner-earnings model, FX forecast, tax/inflation adjustment,
automatic normalization, growth-fade policy or universal terminal-P/E default.

**PR4B PIT diagnostic integration is explicitly deferred.** No adapter, bundle,
runner, worker, source-export, PIT schema, existing history reader or `main.py`
change is included. The flat module fits the existing source-export policy.
Automatic assumption construction from qualified source evidence is also deferred.

**A compatible forward VFV model is explicitly deferred.** VFV historical CAGR
is not substituted. Opportunity cost, sizing, portfolio room, concentration,
selling, reporting and prospective shadow activation remain unchanged.

## Validation

The new tests use only fictitious economic records. They verify analytical
zero-dividend identities, an 8% dividend/terminal-par fixture, independent NPV
substitution, monotonic properties, currency scaling, numerical failure handling,
strict provenance, confidence separation, immutability and deterministic output.

Run through Python 3.12 with `requirements.lock` installed:

```sh
.venv/bin/python -B scripts/run_isolated_tests.py --pattern test_expected_return_engine.py
.venv/bin/python -B scripts/run_isolated_tests.py
git diff --check
```

The isolated runner uses disposable code/config/test copies, synthetic fixtures,
separate HOME/cache/state directories and denied network access. It does not copy
real portfolio, research reports, provider cache or operational output.
Correct arithmetic and unchanged decision fingerprints provide engineering
validation only, not historical performance evidence or investment authority.
