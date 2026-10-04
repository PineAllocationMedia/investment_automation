# EXECUTABLE_ENTRY_EVIDENCE

> Source-neutral, deterministic, fail-closed CURRENT evidence for one bounded
> potentially executable purchase-entry context. This B1 contract creates no
> order, execution instruction, aggregate friction, or executable-net Expected
> Return.

## Purpose and semantic object

`EXECUTABLE_ENTRY_EVIDENCE` is:

> evidence that one opaque account/instrument/funding context currently satisfies
> the prerequisites for a potentially executable purchase entry.

It is not an order, recommendation, allocation, broker integration, owner-specific
live route, entry-price transformation, or execution authority. B1 ends at typed
facts plus explicit closed failure states. B2 is outside this contract.

The versioned identities are:

```text
EXECUTABLE_ENTRY_EVIDENCE_CONTRACT_VERSION
  = 2026-10-03-executable-entry-evidence-v1
EXECUTABLE_ENTRY_EVIDENCE_SCHEMA_VERSION
  = 2026-10-03-executable-entry-evidence-schema-v1
EXECUTABLE_ENTRY_EVIDENCE_QUALIFICATION_VERSION
  = 2026-10-03-executable-entry-evidence-qualification-v1
```

## Supported first profile

B1 v1 supports only a source-neutral listed-security purchase-entry evidence
profile in which:

- an opaque execution-context identity and opaque target-instrument identity bind
  every evidence dimension without containing private account data;
- account/instrument eligibility is positively established;
- funding is positively established as settled and available;
- exact funding and transaction currencies are present;
- commission is an exact finite `Decimal`, including exact zero, under
  `FLAT_PER_ORDER_TRANSACTION_CURRENCY` semantics;
- commission currency equals transaction currency;
- post-trade regular-way settlement is explicitly `T_PLUS_1`;
- the funding and transaction currencies are identical, establishing
  `FX_NOT_REQUIRED_SAME_CURRENCY`; and
- an exact current executable bid/ask quote is positively established in the
  transaction currency.

No quantity, notional, order-size, odd-lot, or fractional-share authority exists.
The scope identities bind context only. They do not establish evidence authority
and cannot replace qualification.

## Independent evidence and partial facts

Eligibility, funding, commission, settlement, and executable quote are separate
immutable evidence records. Each record carries its own source descriptor, source
locator, receipt/content/capture identities, retrieval timestamp, publication
semantics, availability semantics, licensing/use state, and current freshness.
The contract therefore does not imply that distinct facts came from one source or
capture.

Qualification preserves every independently established subfact even when the
overall route fails closed. For example, absent executable quote evidence produces
`UNAVAILABLE / EXECUTABLE_QUOTE_UNAVAILABLE` while preserving already qualified:

- eligibility;
- settled/available funding;
- exact commission, including zero;
- `T_PLUS_1` settlement; and
- the exact same-currency path.

Missing quote authority does not convert those facts into unsupported economics.
Likewise, one unavailable dimension does not erase unrelated facts.

## Scope and provenance contract

Execution-context identities have the exact form `execctx:<lowercase-sha256>`.
Target-instrument identities have the exact form
`instrument:<lowercase-sha256>`. They must not encode account numbers, owner names,
credentials, tokens, or other private identifiers.

Every evidence record is pinned to:

- the B1 evidence schema version;
- exact scope identities;
- nonempty source owner, descriptor, and locator;
- receipt, content, and capture SHA-256 identities;
- an exact offset-aware retrieval/capture timestamp;
- nullable publication timestamp with publication semantics kept distinct;
- `CAPTURE_BOUND` availability;
- licensing and use-review states; and
- explicit current/same-run freshness.

The qualifier performs no network, filesystem, acquisition, authentication, or
provider-adapter work. Public observability does not establish automated or
commercial ingestion permission.

## Eligibility and funding

Positive eligibility requires `ELIGIBLE`. `NOT_ESTABLISHED` is unavailable.
`NOT_ELIGIBLE` and `UNSUPPORTED_INSTRUMENT` are explicit unsupported routes; they
are not bad economics.

Positive funding requires `SETTLED_AND_AVAILABLE`. `UNSETTLED` and
`AVAILABILITY_NOT_ESTABLISHED` fail closed. Missing funding or transaction currency
never acquires a default value.

## Commission and settlement

Commission must be an exact finite `Decimal` amount in the exact transaction
currency. Binary floats are programming-contract errors. Positively evidenced
zero is valid. Missing amount, currency, or semantics is unavailable and never
becomes zero. Negative commission or currency disagreement is a source conflict.
Other commission semantics are unsupported.

Settlement must explicitly state `POST_TRADE_REGULAR_WAY / T_PLUS_1`. Missing
semantics are unavailable. Other semantics or settlement cycles are unsupported.

## FX boundary

When funding currency equals transaction currency, B1 establishes only:

```text
FX_NOT_REQUIRED_SAME_CURRENCY
```

When currencies differ, B1 preserves both currencies and the state
`FX_REQUIRED_EXECUTION_COST_UNAVAILABLE`, then fails the route closed with:

```text
FX_EXECUTION_COST_EVIDENCE_UNAVAILABLE
```

B1 does not infer FX cost from a percentage fee, public schedule, indicative
exchange rate, or spread. It creates no cross-currency pricing architecture.

## Executable quote authority

A positive executable quote requires:

- exact finite `Decimal` bid and ask;
- `bid > 0`, `ask > 0`, and `bid <= ask`;
- exact quote currency equal to transaction currency;
- exact offset-aware market timestamp;
- market timestamp not after capture;
- explicit `EXECUTABLE_BID_ASK` authority;
- an exact source/venue/execution-source descriptor; and
- structurally valid capture provenance and current freshness.

Informational, displayed, delayed, indicative, or otherwise non-executable quote
authority fails closed with `EXECUTABLE_QUOTE_UNAVAILABLE` and
`EXECUTABLE_QUOTE_AUTHORITY_INSUFFICIENT`.

The existing Yahoo current-quote route establishes observed market-price authority,
not executable bid/ask authority. This module does not import, accept, adapt, or
promote a Yahoo current quote. No real positive executable quote route is established
by B1; positive tests are synthetic mechanics only.

B1 does not calculate midpoint, spread cost, market impact, slippage, or aggregate
entry friction.

## CURRENT and chronology

Authority is CURRENT/capture-bound only. Every positive dimension requires
`CURRENT_SAME_RUN_CAPTURE`. `STALE` and `NOT_ESTABLISHED` fail closed. There is no
universal TTL.

Publication time, market time, and retrieval/capture time remain distinct.
Retrieval never becomes first-publication time. Publication after retrieval is a
provenance chronology conflict. Quote market time after capture is a quote
chronology conflict. All timestamp comparisons use exact offset-aware instants
normalized to UTC only for comparison.

No PIT or `HISTORICAL_AS_OF` authority is created.

## Closed qualification

`qualify_executable_entry_evidence` is pure and deterministic. It accepts one exact
typed request or `None`, reads no ambient state, and uses no runtime clock.

Statuses are exactly:

- `AVAILABLE`
- `UNAVAILABLE`
- `UNSUPPORTED`
- `SOURCE_CONFLICT`

Precedence is exact:

```text
malformed programming contract -> ExecutableEntryEvidenceError

otherwise:
SOURCE_CONFLICT > UNSUPPORTED > UNAVAILABLE > AVAILABLE
```

Closed reasons distinguish:

- required evidence missing;
- eligibility not established, explicit ineligibility, and unsupported instrument;
- settled/available funding not established;
- funding and transaction currency unavailable;
- commission unavailable, unsupported, negative, or currency-conflicted;
- settlement unavailable or unsupported and settlement cycle unsupported;
- cross-currency FX execution-cost evidence unavailable;
- executable quote unavailable or authority-insufficient;
- invalid bid/ask, quote currency, and quote chronology conflicts;
- provenance chronology and scope identity conflicts; and
- current freshness not established.

Malformed object types, schema versions, identifiers, hashes, timestamps, enum
values, currencies, non-finite Decimals, and binary floats remain programming
errors, not economic availability states.

## Identity rules

Every result exposes deterministic SHA-256 `semantic_id` and `evidence_id` values.

`semantic_id` binds material route meaning:

- contract and qualification versions;
- opaque context and target-instrument scope;
- status and closed reasons;
- every independently established fact;
- authority scope; and
- limitations.

It excludes provenance-only recapture metadata. Decimal identity material uses
exact tuple encoding with equivalent trailing-zero normalization and no binary64
material.

`evidence_id` additionally binds every dimension's claim identity and complete
provenance. Therefore:

```text
equivalent economics + new capture
-> same semantic_id
-> different evidence_id

changed eligibility, funding/currency path, commission, settlement, or quote
-> changed semantic_id
```

## Authority and limitations

Facts carry `CURRENT_CAPTURE_BOUND_EVIDENCE_ONLY` authority even when another
dimension leaves the overall route unavailable. A result with no established fact
has `NONE` authority.

Every result preserves limitations equivalent to:

- CURRENT/capture-bound only;
- no PIT, `HISTORICAL_AS_OF`, or first-publication authority;
- no broker/provider acquisition authority or owner-specific live route;
- no order construction, order submission, or execution authority;
- no recommendation, allocation, production, deployment, or V2 promotion;
- no seven-year cash Expected Return or executable-net Expected Return;
- no company/VFV-versus-cash comparison;
- no aggregate entry-friction, midpoint, spread-cost, market-impact, or slippage
  calculation;
- no quantity, notional, order-size, fractional-share, or odd-lot capability claim;
- displayed/public quote observability does not establish executable authority; and
- public observability does not establish automated or commercial ingestion
  permission.

## Explicitly out of scope

B1 adds no provider registration, scraper, API, UI automation, provider URL,
hard-coded provider commission, owner account fact, owner currency fact, portfolio
cash fact, real instrument tradability, real executable quote, or paid-data route.

It does not change `economic_facts/source_authority.py`, company/VFV Expected Return,
the company-versus-VFV comparator, V1 runtime, Confidence, Portfolio Room, reserve
policy, dashboard, broker execution, protected governance, or
`MODEL_RULES_VERSION`.

No B2 surface exists: no execution-adjusted entry price, commission/spread/FX-
adjusted IRR, executable-net Expected Return, seven-year executable cash flows, or
executable-net company/VFV comparison.
