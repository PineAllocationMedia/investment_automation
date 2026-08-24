# P4B allocation-room integrity hardening

## Scope and versioning

- Exact base: `115554edcc28aff75d7aacd64622f574fa85c18e`
- Starting `MODEL_RULES_VERSION`: `2026-08-23-deep-drawdown-allocation-safeguard-v6`
- Ending `MODEL_RULES_VERSION`: `2026-08-23-allocation-room-integrity-v7`
- `VALIDATION_SCHEMA_VERSION`: unchanged at `2026-08-23-validation-architecture-v3`

This correction changes allocation room only. It does not change company
quality, fundamental scoring, capital-allocation scoring, conviction, expected
CAGR, thesis, liquidation, provenance, reliability interpretation, validation
evidence, sector/cluster/factor definitions, or portfolio entity resolution.

## Reproduced root cause

The normal allocation loop called `_external_budget_room()`, which correctly
shared `HIGH_CAGR_EMERGING_SATELLITE_BUDGET = 0.225` across all qualifying
satellites. The high-CAGR overflow loop instead called
`_high_cagr_overflow_room()`, whose minimum included its overflow candidate cap,
watch budget, and cycle budget, but not the aggregate emerging-satellite run
budget or the existing 15% satellite portfolio target.

On the exact deterministic P4A-class fixture (a $1,000 contribution and two
eligible high-CAGR external `HIGH_GROWTH_BUT_FRAGILE` satellites), the base code
allocated $350 to `SAT1` and $300 to `SAT2`: $650 combined. The corrected code
allocates $125 and $100: $225 combined. The remaining $775 goes to the existing
VFV fallback. The final satellite rows expose
`EMERGING_SATELLITE_RUN_BUDGET_EXHAUSTED`.

The second root cause was `_current_portfolio_value()`: when no positive current
value was present, it returned a fabricated $100,000. That denominator enlarged
normal post-purchase target room and suppressed overflow concentration checks.

## Authoritative room contract

Both normal and overflow paths now call one authoritative helper:
`_applicable_hard_additional_capital_room()`.

For a candidate and path:

`final room = min(path-specific room, every applicable hard invariant room)`

The shared layer can only reduce room. It never creates eligibility. It applies
the P3 zero-room block first, rejects unsafe percentage-room calculations when
an owned portfolio has no valid value basis, recomputes watch/cycle budgets, and
recomputes the shared satellite run budget after every chunk. For an emerging
satellite it also recomputes the existing individual 15% post-contribution
target using current whole-position value plus all same-run allocations.

## Constraint classification

| Classification | Existing constraints and final treatment |
|---|---|
| HARD INVARIANT | P3 `deep_averaging_down_blocked`; thesis/add/liquidation eligibility; LOW-reliability exclusion and existing reliability size caps; drift add eligibility; applicable watch and cycle run budgets; the aggregate 22.5% emerging-satellite run budget; the existing individual 15% emerging-satellite post-purchase target; valid portfolio-value basis for percentage room. Overflow cannot bypass these. |
| PATH-SPECIFIC INTENTIONAL LIMIT | Normal generic target room; normal candidate monthly cap; mode-specific external budgets and individual caps; high-CAGR overflow candidate cap and its existing concentration gate; VFV redirection policy. Generic high-CAGR external compounders and core winners retain intentional overflow semantics and do not inherit the emerging-satellite budget. |
| SOFT STEERING | Marginal allocation score, sector/hidden-cluster/factor score treatments, quality-diversifier bonus, allocation-stability adjustment, cycle score penalty, and concentration drag. None became a new hard guard. |
| DIAGNOSTIC ONLY | Allocation logs, model/mode audit outputs, validation evidence, and the new room/reason metadata. These describe decisions and do not independently change eligibility or scoring. |

## Existing 22.5% and 15% semantics

The 22.5% constant remains one cumulative per-run budget across every qualifying
emerging satellite. Normal allocations count before overflow begins. At $200
already allocated, only $25 remains. At $225 or $225.01 used, room is zero. At
$224.99 used, the final room is exactly $0.01. A $50 overflow chunk with $25 of
remaining budget deploys exactly $25.

The 15% constant remains an individual fragile-satellite portfolio target, not
an aggregate sector or cluster cap. Normal and overflow compute identical room
against `current portfolio value + current contribution`, subtracting the
candidate's canonical whole-position current value and every same-run chunk.

## Portfolio-value basis

- `VALID_CURRENT_PORTFOLIO_VALUE`: sum positive `current_value`, with existing
  canonical `current_value_cad` as a per-position fallback, provided the explicit
  source is not `acquisition_value_fallback`. Existing valid-value behavior is preserved.
- `EMPTY_PORTFOLIO_POST_CONTRIBUTION`: no owned position and no current value.
  Current total is zero and the contribution itself is the mathematically valid
  post-contribution denominator. No $100,000 is invented.
- `MISSING_CURRENT_PORTFOLIO_VALUE`: at least one owned position lacks a positive
  current value, including a partially valued portfolio. Percentage-based stock
  room is zero and capital continues through the existing defensive/VFV fallback.

No transaction reconstruction or new valuation system was added.

### Current-value source authority

The allocation-room layer rejects exactly `acquisition_value_fallback` as a
current-market-value basis. The loader's numeric approximation and provenance
remain visible and unchanged, but acquisition cost cannot authorize percentage
room. A mixed portfolio with even one owned acquisition-cost fallback position
fails closed for whole-portfolio percentage calculations.

Positive values remain accepted from `shares_x_market_price_CAD`,
`shares_x_market_price_fx_to_CAD`, `manual_current_value_fallback`, and
`manual_current_value_legacy`. For backward-compatible synthetic fixtures, a
positive current value with no source metadata also remains accepted. Owned
positions without a positive current value remain unsafe as before.

### Reviewed-head safe-value corrections

Against reviewed PR head `98e3986e220c1465912370d818c21f1c068e3220`:

| Case | Reviewed head | Corrected | Expected |
|---|---:|---:|---|
| Acquisition-cost fallback basis | `VALID`; NEW $600; VFV $400 | `MISSING`; NEW $0; VFV $1,000 | Yes |
| EMPTY overflow already at 35% | $100 additional room | $0 additional room | Yes |
| EMPTY overflow at 33% | $120 room | $120 room | Unchanged |
| Two satellites | $225 combined | $225 combined | Unchanged |
| Three satellites | $225 combined | $225 combined | Unchanged |
| Individual 15% target fixture | $10 normal / $10 overflow | $10 / $10 | Unchanged |
| Core-winner overflow | CORE1 $180 / CORE2 $180 | $180 / $180 | Unchanged |
| Generic durable external overflow | $450 room | $450 room | Unchanged |
| P3 block | $0 normal / $0 overflow | $0 / $0 | Unchanged |

The existing `>34%` overflow concentration threshold is unchanged. The only
logic correction is that both `VALID_CURRENT_PORTFOLIO_VALUE` and
`EMPTY_PORTFOLIO_POST_CONTRIBUTION` use their trustworthy denominator; only
`MISSING_CURRENT_PORTFOLIO_VALUE` fails closed.

## Controlled blast radius

The same fixtures were run from the exact base archive and the corrected tree.

| Case | Base | Corrected | Expected | Limiting guard |
|---|---:|---:|---|---|
| Two emerging satellites | SAT1 $350; SAT2 $300; combined $650 | SAT1 $125; SAT2 $100; combined $225 | Yes | `EMERGING_SATELLITE_RUN_BUDGET_EXHAUSTED` |
| Normal emerging satellite with valid $100k portfolio | $225 | $225 | Unchanged | Existing 22.5% normal run budget |
| Legitimate core winner overflow | CORE1 $180; CORE2 $180 | CORE1 $180; CORE2 $180 | Unchanged | Existing overflow candidate/concentration room |
| Ordinary diversified candidates | MSFT $700; MA $250 | MSFT $700; MA $250 | Unchanged | Existing normal caps |
| P3-blocked owned position | $0 stock; $1,000 VFV | $0 stock; $1,000 VFV | Unchanged | `DEEP_AVERAGING_DOWN_BLOCKED` |
| LOW-reliability candidate | $0 stock; $1,000 VFV | $0 stock; $1,000 VFV | Unchanged | Existing reliability eligibility |
| Zero capital | no allocations | no allocations | Unchanged | Existing zero-capital rule |
| Genuine empty portfolio, one core | $700 stock; $300 VFV | $300 stock; $700 VFV | Yes | Valid post-contribution target, no fictitious denominator |
| Owned portfolio, missing values | $700 stock; $300 VFV | $0 stock; $1,000 VFV | Yes | `POST_PURCHASE_ROOM_UNAVAILABLE_MISSING_PORTFOLIO_VALUE` |
| Fallback in missing-value case | $300 VFV | $1,000 VFV | Yes | Existing VFV fallback receives blocked room |

All controlled changes are the demonstrated hard-room defect or unsafe
fabricated-denominator cases. `UNEXPECTED=0`.

## Audit fields and reason codes

Allocation rows and `latest_allocations.csv` now expose:

- `applicable_hard_room`
- `limiting_room_reason`
- `satellite_run_budget`
- `satellite_allocated_this_run`
- `satellite_remaining_run_room`
- `post_purchase_position_weight`
- `portfolio_value_basis_status`

New room reasons include `EMERGING_SATELLITE_RUN_BUDGET_EXHAUSTED`,
`EMERGING_SATELLITE_TARGET_REACHED`, `DEEP_AVERAGING_DOWN_BLOCKED`, and
`POST_PURCHASE_ROOM_UNAVAILABLE_MISSING_PORTFOLIO_VALUE`, plus existing-room
descriptions for monthly, external, watch, cycle, normal-target, and overflow
limits.

## Non-goals confirmed

No company score, scoring weight, conviction formula, expected-CAGR logic,
sector/cluster/factor threshold, sell rule, forced rebalance, transaction memory,
provenance/reliability interpretation, validation architecture, portfolio
aggregation rule, Chromebook deployment, or Drive data was changed.

## Validation result

- P4B and predecessor/behavior-focused selection: 327 tests passed.
- Complete repository suite: 829 tests passed.
- Repository Python sources/tests/scripts: `py_compile` passed.
- `git diff --check`: passed.
- Controlled blast radius: `UNEXPECTED=0`.
