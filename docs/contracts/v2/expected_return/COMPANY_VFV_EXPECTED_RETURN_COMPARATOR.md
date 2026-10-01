# Company vs VFV Expected Return comparator

> One bounded Stage B research diagnostic. It compares one admitted PR5E
> company Expected Return with one standalone VFV forward Expected Return under
> an explicit constant-FX convention. It grants no recommendation, ranking,
> allocation, execution, production, deployment, or V2-promotion authority.

## Contract identities

```text
Comparator contract
2026-10-01-company-vfv-expected-return-comparator-v1

Comparison basis identity/version
2026-10-01-company-vfv-constant-fx-comparison-v1

Comparison semantics
SAME_LABEL_DETERMINISTIC_SCENARIO_SPREADS

Authority
RESEARCH_DIAGNOSTIC_ONLY
```

The comparison convention is:

```text
CONSTANT_FX
+
ZERO_MODELED_FUTURE_FX_CONTRIBUTION
```

This is not an FX forecast or a realized-CAD-return calculation. Actual CAD
investor returns may differ because CAD/USD exchange rates can change.

## Supported company route

The company input must be an exact `PR5EAdmissionResult` from the current real
PR5E route. The comparator does not rerun acquisition or analysis. It accepts
only:

```text
PR5E status       REAL_EXPECTED_RETURN_ADMITTED
quote currency    USD
quote unit        CURRENCY_PER_SHARE
accounting basis  US_GAAP
profile           ORDINARY_COMPOUNDER
distribution      exactly one VerifiedNonpayer and no payer fact
return basis      NOMINAL_PRETAX_EQUITY_CASHFLOW_IRR
FX basis          CONSTANT_FX
horizon           7 years
facts contract    2026-09-30-pr5e-real-qualified-facts-v1
methodology       2026-09-08-normalized-eps-cashflow-irr-v1
```

The current owner-approved company policy proposal, proposal hash, mature-growth
policy hash, terminal-valuation policy hash, and selected nonpayer policy hash
must all match the repository-approved identities. The comparator supports no
CAD/EUR/JPY company route, payer route, other profile, other accounting basis,
or synthetic-only route. Reusable mathematics does not create factual authority.

## Supported VFV route

The VFV input must be an exact AVAILABLE standalone
`VFVForwardERDiagnostic` with:

```text
policy
PAM_VFV_FORWARD_ER_POLICY_2026_10_01_V1

policy hash
31dbebd0545c233c4913dad1915dfd2eb23d91481019fec078b245541ef0e645

methodology
2026-10-01-vfv-normalized-unit-cashflow-irr-v1

return basis
NOMINAL_PRE_HOLDER_TAX_UNIT_HOLDER_CASHFLOW_IRR

FX basis
CONSTANT_TRANSLATION_NO_FX_CONTRIBUTION_MODELED

horizon
7 years
```

The standalone VFV module remains unchanged. Its standalone limitations,
including no independent FX-comparability authority, remain valid. Comparator
authority is additive and exists only when the separate qualified FX/hedge
evidence below is supplied and exactly pinned.

## VFV FX/hedge evidence boundary

`economic_facts/vfv_fx_hedge_evidence.py` is a pure qualification boundary. It
performs no network access, document download, parsing, filesystem access, clock
read, or source substitution. It accepts immutable typed source records and
supports only this reviewed disclosure meaning:

```text
instrument                         VFV / CA92205Y1051
listed currency                    CAD
base currency                      CAD
material economic exposure         USD
material hedge-state classification materially unhedged USD exposure to CAD
measurement date                   2026-06-30
reported net USD exposure          100.0% of NAV after currency contracts
availability                       capture-bound
confidence                         LOW
```

This dated observation is not represented as a permanent no-hedging mandate,
zero currency contracts, a hedge ratio after 2026-06-30, or historical/PIT
hedge state. Passage of time alone does not relabel it false. A caller must
supply the exact qualified object; discovering newer contradictory disclosures
is outside this pure comparator.

The evidence contract and qualification versions are:

```text
2026-10-01-vfv-fx-hedge-evidence-v1
2026-10-01-vfv-fx-hedge-qualification-v1
```

Closed evidence statuses are `AVAILABLE`, `UNAVAILABLE`, `UNSUPPORTED`, and
`SOURCE_CONFLICT`. Only the exact AVAILABLE supported meaning can unlock a
comparison.

## Public comparator boundary

```python
compare_company_vfv_expected_returns(
    company,
    vfv,
    hedge,
    request,
) -> CompanyVFVComparisonResult
```

The request pins exactly six identities:

- company PR5E admission semantic/evidence IDs;
- VFV diagnostic semantic/evidence IDs;
- VFV FX/hedge semantic/evidence IDs.

It accepts no growth, terminal-multiple, FX-forecast, hedge-ratio, scenario
weight, winner, recommendation, or allocation input.

## Compatibility and closed outcomes

Comparison is AVAILABLE only when every company, VFV, FX/hedge, currency,
policy, methodology, return-basis, horizon, identity, scenario-label, and
numeric condition above holds. The comparator uses closed statuses:

```text
AVAILABLE
UNAVAILABLE
UNSUPPORTED
SOURCE_CONFLICT
```

Failures include upstream unavailability, unsupported company route, any exact
identity mismatch, VFV policy/methodology/basis mismatch, missing or unsupported
FX evidence, FX source conflict, currency incompatibility, horizon mismatch,
incomplete scenario labels, and unavailable numeric spreads. No failure is a
negative investment conclusion.

## Same-label spread semantics

For an AVAILABLE result, the only numeric comparisons are:

```text
bear_spread = company bear annualized_return - VFV bear annualized_return
base_spread = company base annualized_return - VFV base annualized_return
bull_spread = company bull annualized_return - VFV bull annualized_return
```

No cross-label combination is calculated. A positive value means only that the
company scenario's modeled annualized cash-flow IRR exceeds the same-label VFV
modeled IRR by that number of annualized-return percentage points under the
constant-FX/zero-modeled-future-FX convention and each instrument's own scenario
construction. It does not mean probability-weighted expected outperformance,
expected CAD outperformance, a synchronized macro state, or a recommendation.

No scenario probabilities or weights exist. Neither upstream Expected Return nor
the spread receives a confidence haircut.

## Confidence

Local comparator confidence is the minimum supported confidence of material
inputs and is capped at `LOW`. Missing, mismatched, unsupported, or conflicted
FX/hedge evidence removes numeric comparison availability rather than applying a
penalty.

## Result and identity discipline

The result carries the contract/basis identities, closed status/reasons,
upstream semantic/evidence IDs, supported basis metadata, dated FX/hedge state,
raw same-label spreads when available, local confidence, upstream limitations,
comparator limitations, and deterministic `semantic_id`/`evidence_id`.

Semantic identity binds comparison meaning: upstream semantic identities,
supported route/policy/basis metadata, same-label pairing, status/reasons,
confidence, and limitations. It excludes the derived binary64 spread realization.
Evidence identity additionally binds the exact company, VFV, and FX/hedge
evidence identities. Therefore a one-ULP-only perturbation of a derived spread
does not change either identity when the upstream analytical problems are
unchanged; the raw perturbed spread remains observable. Provenance-only changes
can change `evidence_id` without changing economic `semantic_id`.

## Mandatory limitations and non-authority

Every successful result explicitly retains:

```text
CONSTANT_FX_ZERO_FUTURE_FX_CONTRIBUTION_ASSUMPTION
VFV_MATERIAL_UNDERLYING_USD_EXPOSURE
VFV_MATERIALLY_UNHEDGED_TO_CAD_AT_2026_06_30_DISCLOSURE_STATE
VFV_HEDGE_STATE_DATE_BOUND_NOT_PERMANENT
ACTUAL_CAD_INVESTOR_RETURN_MAY_DIFFER_DUE_TO_CAD_USD_MOVEMENT
NO_FX_FORECAST
NO_REALIZED_CAD_RETURN_CLAIM
SAME_LABEL_SCENARIOS_ARE_NOT_COMMON_PROBABILISTIC_STATES
RESEARCH_DIAGNOSTIC_ONLY
NOT_EXECUTABLE_RETURN
NO_RECOMMENDATION_OR_ALLOCATION_AUTHORITY
NO_PRODUCTION_OR_EXECUTION_AUTHORITY
NO_HISTORICAL_AS_OF_OR_PIT_AUTHORITY
```

Material upstream company, VFV CURRENT, VFV forward-ER, and FX/hedge limitations
are preserved separately. The result has no winner, rank, score, recommendation,
allocation, target weight, position size, execution instruction, or probability
of outperformance.

No production/V1 module, portfolio or allocation component, operational runtime,
or execution path imports this comparator. V1 remains frozen operational
authority; V2 remains challenger-only.
