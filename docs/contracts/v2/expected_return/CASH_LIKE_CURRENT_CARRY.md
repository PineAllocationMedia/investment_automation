# CASH_LIKE_CURRENT_CARRY

> Source-neutral, deterministic, fail-closed CURRENT carry contract for one
> reviewed settled-cash-balance profile. This contract creates no live owner fact,
> acquisition route, Expected Return comparison, reserve policy, or execution
> authority.

## Purpose and exact semantic object

`CASH_LIKE_CURRENT_CARRY` is:

> the currently evidenced nominal carry earned by a qualified temporary-liquidity
> destination, in its native accrual currency, before holder tax and before
> transactional execution friction.

It is not called opportunity cost. Opportunity cost is a later comparison between
alternatives. Current cash carry is not seven-year Expected Return, does not imply
that a destination is risk-free, and does not forecast rollover or reinvestment.

The versioned identities are:

```text
CASH_LIKE_CURRENT_CARRY_CONTRACT_VERSION
  = 2026-10-01-cash-like-current-carry-v1
CASH_LIKE_CURRENT_CARRY_RECEIPT_VERSION
  = 2026-10-01-cash-like-current-carry-receipt-v1
CASH_LIKE_CURRENT_CARRY_QUALIFICATION_VERSION
  = 2026-10-01-cash-like-current-carry-qualification-v1
```

## Supported first profile

V1 supports only:

```text
balance_form       = SETTLED_CASH_BALANCE
settlement_state   = SETTLED_AND_AVAILABLE
rate_type          = NOMINAL_ANNUAL_RATE
rate_unit          = PERCENTAGE_POINTS_PER_YEAR
accrual_semantics  = DAILY_ON_END_OF_DAY_SETTLED_BALANCE
payment_semantics  = PAID_MONTHLY
term_semantics     = NO_FIXED_TERM
freshness          = CURRENT_SAME_RUN_CAPTURE
availability       = CAPTURE_BOUND
```

The contract is capable of representing a future qualified
`SETTLED_CASH_BALANCE_CURRENT_CARRY` receipt, but this slice does not provide such
an owner-specific receipt. A positive result also requires an exact native accrual
currency, exact `Decimal` rate, explicit effective-date semantics, explicit
recurring-expense treatment, and structurally valid capture metadata.

A positively evidenced zero rate is `AVAILABLE` and remains exact zero. A missing
rate is `UNAVAILABLE`; it never defaults to zero. The same distinction applies to
currency and every required semantic field.

## Source-neutral evidence boundary

`CashLikeCurrentCarryReceipt` is a compact input for an externally supplied,
authenticated capture. It preserves:

- receipt schema and qualification-input versions;
- source owner, descriptor and field locator;
- receipt, content/account-state and capture SHA-256 identities;
- exact offset-aware retrieval timestamp;
- nullable publication timestamp and closed publication semantics;
- capture-bound availability semantics;
- licensing/use review states;
- explicit same-run/current freshness state; and
- one typed economic claim.

The module starts after acquisition and authentication. It does not scrape, call a
provider, read ambient account state, store credentials, or decide that a caller's
untyped assertion is qualified. Malformed object types, versions, hashes,
timestamps, enum values, non-finite numbers, floats and noncanonical dates are
programming-contract errors. Missing economic evidence produces a closed status.

No account number, credential, private token or private owner identifier belongs in
the receipt. No real owner evidence is committed by this slice.

The core contract does not register or name a provider. Public observability does
not establish automated acquisition, commercial ingestion, redistribution or
production authority. A later source adapter must separately establish its legal,
technical, authentication and freshness boundary.

In particular, this slice does not automate or call Wealthsimple, encode a
Wealthsimple URL, assume a Wealthsimple account or rate mode, or establish automated
or commercial Wealthsimple ingestion authority. The public existence of a possible
route does not prove that the owner holds the relevant account, that cash is settled
and available, or that an owner-specific positive fact exists.

## Economic fact and exact semantics

An `AVAILABLE` result contains a `CashLikeCurrentCarryFact`, separate from
`CashLikeCurrentCarryEvidence`. The fact retains:

- supported balance form;
- exact native accrual currency;
- exact `Decimal` rate;
- rate type and unit;
- explicit accrual and payment semantics;
- explicit compounding and day-count semantics;
- exact effective date and its semantics;
- term/maturity semantics; and
- whether recurring instrument expenses are absent, already reflected, not
  reflected, or unspecified by the source.

Binary floats are forbidden. Decimal identity material is normalized without
performing Decimal context arithmetic, so economically equal values such as
`3.1250` and `3.125000` have the same semantic identity while the fact preserves
the originally supplied exact `Decimal` value.

### Compounding and day count

The contract explicitly permits `UNSPECIFIED_BY_SOURCE` for compounding and day
count. That state is supported truth: it means the source did not establish the
convention. It does not mean daily compounding, monthly compounding, Actual/365 or
any other guessed convention. A missing state is unavailable; a typed `OTHER`
state is unsupported.

### Effective, publication and retrieval chronology

Economic effective date, publication timestamp and retrieval timestamp are distinct:

```text
effective_date         -> when the source says the rate is effective/current as of
publication_timestamp  -> nullable; no first-publication claim when unknown
retrieved_at            -> when this exact evidence was captured
availability_timestamp -> retrieval time under CAPTURE_BOUND availability only
```

Retrieval never substitutes for publication or economic effective time. An
effective date after retrieval, publication timestamp after retrieval, or maturity
before effective date is a `SOURCE_CONFLICT / CHRONOLOGY_CONFLICT`.

Freshness is an explicit qualification input. V1 requires
`CURRENT_SAME_RUN_CAPTURE`; it defines no universal day-count TTL. Future adapters
may establish their evidence-class freshness rules without changing the economic
meaning of current carry.

## Qualification

`qualify_cash_like_current_carry` is pure and deterministic. It accepts one typed
receipt or `None`, performs no network or filesystem access, uses no runtime clock,
and has no ambient dependency.

A positive result requires all of the following:

1. the supported settled-cash balance form;
2. positive settled-and-available applicability;
3. exact native currency;
4. an exact finite `Decimal` rate, including exact zero;
5. supported nominal annual rate type and percentage-points-per-year unit;
6. supported explicit daily settled-balance accrual semantics;
7. supported explicit monthly payment semantics;
8. explicit compounding and day-count states, including source-unspecified states;
9. explicit effective date and supported effective/as-of semantics;
10. no-fixed-term semantics and no maturity for this first profile;
11. explicit recurring-expense treatment;
12. a structurally valid, version-pinned capture receipt;
13. explicit same-run/current freshness;
14. `UNKNOWN` publication semantics and `CAPTURE_BOUND` availability for V1; and
15. consistent chronology.

Conflict takes precedence over unsupported, which takes precedence over unavailable.
No partially qualified economic fact is emitted.

## Closed statuses and reasons

Statuses are exactly:

- `AVAILABLE`
- `UNAVAILABLE`
- `UNSUPPORTED`
- `SOURCE_CONFLICT`

Reasons are closed and include:

| Status family | Reasons |
| --- | --- |
| `UNAVAILABLE` | `REQUIRED_RECEIPT_MISSING`, `CURRENT_FRESHNESS_NOT_ESTABLISHED`, `RATE_UNAVAILABLE`, `EXACT_CURRENCY_UNAVAILABLE`, `ACCOUNT_BALANCE_FORM_UNAVAILABLE`, `SETTLED_AVAILABLE_STATE_NOT_ESTABLISHED`, missing required rate/accrual/payment/compounding/day-count/effective/term/expense semantics |
| `UNSUPPORTED` | `ACCOUNT_BALANCE_FORM_UNSUPPORTED`, unsupported rate/accrual/payment/compounding/day-count semantics, `TERM_PROFILE_UNSUPPORTED`, `SOURCE_SEMANTICS_UNSUPPORTED` |
| `SOURCE_CONFLICT` | `CHRONOLOGY_CONFLICT` |

Malformed typed inputs are `CashLikeCurrentCarryError`, not economic availability.

## Identity rules

Every qualification exposes deterministic SHA-256 `semantic_id` and `evidence_id`.

`semantic_id` binds only material contract meaning:

- contract and qualification versions;
- status and reasons;
- the complete qualified economic fact;
- current/capture-bound authority; and
- material limitations.

It excludes source owner, receipt IDs, source locators, hashes, retrieval time and
other provenance-only recapture state. Equivalent recapture of unchanged economics
therefore preserves `semantic_id`. A changed rate, currency or rate semantics changes
it.

`evidence_id` additionally binds the complete evidence metadata. A new capture,
changed content/account-state hash, retrieval time, source descriptor or use status
therefore changes `evidence_id` even when economics are unchanged.

## Authority and limitations

Positive factual authority is exactly `CURRENT_CAPTURE_BOUND_ONLY`. Every result,
including a positive result, exposes limitations with the substance of:

- CURRENT/capture-bound only;
- no PIT or `HISTORICAL_AS_OF` authority;
- no first-publication authority;
- no seven-year cash Expected Return;
- no company-versus-cash or VFV-versus-cash comparison;
- no holder-tax modeling;
- no reserve activation/release policy;
- no recommendation or allocation authority;
- no execution or production authority;
- no generic cash ETF or Treasury-bill authority; and
- public/source observability does not establish automated or commercial ingestion.

The output is nominal carry in native accrual currency before holder tax and before
transactional execution friction. It says nothing about deposit insurance, credit,
sovereign, duration, liquidity, currency, wrapper, tracking or other risks and must
not be labelled risk-free.

## Explicitly unsupported behavior

This slice does not calculate or expose:

- company Expected Return minus current cash yield;
- VFV Expected Return minus current cash yield;
- any cash-versus-equity spread;
- seven-year cash rate or cash Expected Return;
- rollover or reinvestment forecast;
- reserve activation, persistence, hysteresis or release policy;
- generic cash ETF, money-market fund or Treasury-bill admission;
- holder-specific tax or transaction costs;
- recommendation, allocation, order or deployment output; or
- automated acquisition from any provider.

`source_authority.py`, V1 runtime, company/VFV Expected Return engines, comparator,
Confidence, Portfolio Room and `MODEL_RULES_VERSION` remain unchanged.
