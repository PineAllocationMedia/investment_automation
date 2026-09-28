# Capability-Based Partial Analysis Architecture

> PR5D0C — cross-cutting V2 architecture only.
>
> This document defines how PAM may retain a security for research and expose
> legitimate partial analysis when another independent capability is missing,
> incomplete, unsupported, unresolved, or conflicted. It implements no runtime
> behavior and grants no investment or admission authority.

## 1. Purpose

Global research coverage is inherently uneven. Official and public sources may
support revenue, balance-sheet, cash-flow, business-description, price, class,
corporate-action, or distribution evidence to different degrees for the same
security. PAM must preserve every valid fact without allowing strength in one
dimension to manufacture authority in another.

The canonical rule is:

> **Failure of one qualification or analytical capability must not automatically
> invalidate every other independent research capability for the same security.**

Equivalently:

```text
one missing capability != whole-company research failure
```

This architecture formalizes dimensional research availability while preserving
strict fail-closed admission. It extends the existing Global/Market Capability
Registry, Real Fact Admission, Confidence, Opportunity Set, and global-adapter
direction; it does not create a competing evidence architecture.

## 2. Canonical rules

1. Economic evidence, capability coverage, analytical conclusions, and
   investment/admission authority are separate layers. They never collapse into
   one boolean.
2. Every analytical output owns an explicit dependency contract. It is available
   only when that exact contract permits it.
3. A capability result has authority only for its declared operation and evidence
   boundary. `SUPPORTED` never means globally admitted.
4. Missing, partial, unsupported, review-required, or conflicted evidence remains
   explicit. No neighboring capability may fill the gap by inference.
5. Independent supported outputs may continue when a different output is blocked.
6. Any output whose dependency is not satisfied remains unavailable. Partial
   research does not create a fallback Expected Return or weaker admission route.
7. Economic Quality is not a proxy for source coverage. Missing evidence may
   reduce availability, Confidence, or Admission, but it does not make a company
   economically bad.
8. Research participation is broader than Opportunity Set participation and
   grants no recommendation, allocation, execution, or production authority.
9. Capability authority is dimensional. It must not be converted into a global
   synthetic coverage score for authority decisions.
10. PAM prefers narrow trustworthy coverage plus explicit partial analysis over
    universal-looking coverage built from guessed facts.

Useful invariants are:

```text
DATA_UNAVAILABLE != BAD_COMPANY
DATA_UNAVAILABLE != SELL
UNSUPPORTED != LOW_QUALITY
PARTIAL_COVERAGE != THESIS_BROKEN
ONE_CAPABILITY_FAILURE != WHOLE_RESEARCH_FAILURE
```

## 3. Four concepts that must remain separate

### 3.1 Economic evidence

Economic evidence records what has actually been established about an issuer,
security, listing, period, or event. Examples include revenue, EPS, debt, cash,
operating cash flow, free cash flow, a business description, corporate actions,
and an observed current price.

Evidence retains its provenance, scope, time semantics, authority, conflicts, and
limitations. A fact remains a fact even when another required fact is unavailable.
Evidence alone does not authorize an analytical output.

### 3.2 Capability coverage

Capability coverage answers whether PAM has the supported evidence and contract
support required for one exact analytical operation. Examples include comparable
revenue history, share-basis comparability, balance-sheet analysis, verified
nonpayer qualification, or controlled quote semantics.

Coverage is source-neutral at the core. A source adapter may prove a capability,
but a provider, jurisdiction, ticker convention, filing type, or registry entry
does not define the economic capability itself.

### 3.3 Analytical conclusion

An analytical conclusion is an output PAM may legitimately calculate or state
from satisfied capability dependencies. Revenue growth, leverage context,
comparable EPS growth, and strict Expected Return are different outputs with
different dependencies.

No conclusion may inherit a security-wide pass bit. Each output carries its own
availability, reasons, limitations, evidence dependencies, and authority boundary.

### 3.4 Investment/admission authority

Investment/admission authority determines whether a result may enter a stricter
Expected Return route, Opportunity Set, portfolio, recommendation, or future
allocation path. It is a separate downstream gate.

Valid evidence, supported capability coverage, or a valid analytical conclusion
does not by itself grant investment/admission authority. Final admission remains
closed, evidence-replaying, profile-specific, and fail-closed.

## 4. Canonical capability states

These conceptual states are source-neutral and apply per capability, never to the
company's overall economic merit.

### `SUPPORTED`

All evidence, qualification, and contract requirements for that exact capability
are satisfied within its declared scope and time boundary.

`SUPPORTED` does not mean every capability is supported, the research profile is
complete, the security is admitted, or an allocation is authorized.

### `PARTIAL`

Some useful qualified evidence or bounded analytical context exists, but the full
contract for that capability is not satisfied.

The partial result may support research only within explicit limitations. It must
not masquerade as the complete output or satisfy a dependency that requires
`SUPPORTED`.

### `UNSUPPORTED`

The issuer, security, instrument, accounting, jurisdiction, source, or analytical
profile lies outside the currently implemented supported contract.

This means PAM does not support the case yet. It is not an economic criticism and
must not mechanically lower Quality.

### `UNAVAILABLE`

Required evidence was not present or cannot currently be obtained under the
supported routes. Absence remains absence: it is not zero, false, unchanged, or a
permission to guess.

### `REVIEW_REQUIRED`

Relevant evidence exists, but automatic qualification cannot safely resolve the
case. The material remains useful for research or manual investigation, while the
automated capability stays unavailable for any dependency requiring support.

`REVIEW_REQUIRED` is never equivalent to `SUPPORTED`, and manual review must not
silently create automated authority.

### `CONFLICTED`

Relevant retained evidence materially conflicts within the capability boundary.
The conflict stays visible. Latest, earliest, majority, duplicate count, caller
order, or most-convenient-value rules may not select a winner unless a later
reviewed contract defines a legitimate resolution rule.

## 5. Dimensional state, not a global score

Authority decisions must not compress capability states into a scalar such as:

```text
coverage_score = 78%
```

For example, these profiles are not interchangeable:

```text
Price                 SUPPORTED
Revenue               SUPPORTED
EPS                   SUPPORTED
Share basis           UNAVAILABLE
```

```text
Price                 UNAVAILABLE
Revenue               PARTIAL
EPS                   UNAVAILABLE
Share basis           SUPPORTED
```

A future UI may describe coverage compactly, but it must preserve the dimensions
and must not use a summary percentage to grant evidence, analytical, admission,
ranking, recommendation, or allocation authority.

## 6. Per-output dependency model

Every future analytical output must declare its exact required capabilities and
the states each dependency accepts. The declaration must be inspectable and
versioned. It must not depend on a global security-wide pass/fail bit.

Conceptually, an output result exposes:

```text
output capability
status
reasons
limitations
evidence dependencies
authority boundary
```

This document prescribes no dataclass, schema, function signature, or runtime
orchestration. Later implementation contracts must define those details.

### Revenue growth example

Possible dependencies include reporting-subject identity, revenue history,
period comparability, and supported accounting basis. Revenue growth does not
inherently require per-share or share-basis comparability.

### Balance-sheet analysis example

Possible dependencies include the reporting subject, cash, debt, relevant
balance-sheet periods, and accounting-basis comparability. It does not inherently
require comparable EPS or share-basis authority.

### EPS growth example

Comparable EPS growth requires qualified EPS history, reporting-subject
continuity, and share-basis comparability. A failure of either comparability
dimension blocks the strict EPS-growth output even when the retained EPS source
facts remain useful evidence.

### Strict Expected Return example

The current first profile ultimately requires the reviewed PR5B/PR5C/PR5D/PR5E
chain, including security/class identity, comparable EPS, controlled price and
quote semantics, distribution status, ordinary-compounder profile, governed
policies, and final admission.

Consequently, unavailable share-basis comparability blocks strict Expected Return
without automatically blocking unrelated revenue or balance-sheet research.

## 7. Analytical output availability

Each output independently determines availability from its declared dependencies.
A supported fact or output remains valid inside its boundary even when another
output is unavailable. Conversely, a successful capability cannot grant global
admission or conceal a missing dependency.

Example:

```text
REVENUE HISTORY                SUPPORTED
BALANCE SHEET                  SUPPORTED
CASH FLOW HISTORY              SUPPORTED
EPS HISTORY                    SUPPORTED
SHARE-BASIS COMPARABILITY      UNAVAILABLE

revenue analysis               potentially available
balance-sheet analysis         potentially available
cash-flow analysis             potentially available
strict comparable-EPS growth   unavailable
strict Expected Return         unavailable
research participation         PARTIAL_ANALYSIS
```

The qualification of revenue, balance-sheet, or cash-flow evidence cannot invent
the missing share-basis evidence. The inability to calculate strict Expected
Return cannot erase independently established facts.

## 8. Research participation states

Research participation describes how much legitimate research PAM can presently
offer. It is descriptive, not an economic ranking or admission decision.

### `FULL_ANALYSIS_ELIGIBLE`

Every capability required by the currently declared complete research profile is
supported. This does not itself grant Opportunity Set, portfolio, recommendation,
allocation, execution, production, or promotion authority.

### `PARTIAL_ANALYSIS`

At least one meaningful analytical output is legitimately available, but the
complete declared research profile is not satisfied. Available outputs remain
usable with their limits; unavailable outputs remain unavailable.

### `RESEARCH_CANDIDATE`

Identity or discovery is sufficient to retain, monitor, and retry the security,
but too little qualified evidence exists for a meaningful analytical output.
This state supports future evidence acquisition, not investment authority.

### `UNSUPPORTED_RESEARCH_PROFILE`

The current architecture does not support the economic or instrument profile
sufficiently for research analysis. It means “not supported by PAM yet,” not
“bad company,” “rejected investment,” or “sell.”

Data scarcity alone must not create a global `REJECTED` state.

## 9. Discovery, research, and admission funnel

The conceptual funnel is:

```text
DISCOVERY
    ↓
OBSERVABLE
    ↓
RESEARCH_CANDIDATE
    ↓
PARTIAL_ANALYSIS
    ↓
FULL_ANALYSIS_ELIGIBLE
    ↓
STRICT ADMISSION / OPPORTUNITY SET
```

These states are not necessarily irreversible. New, stale, corrected, lost, or
conflicting evidence can upgrade or downgrade individual capabilities and research
participation. A security may remain useful in `PARTIAL_ANALYSIS` for years.

Market-data availability never grants analytical admission. Research participation
never implies allocation eligibility.

## 10. Economic Quality and existing positions

Missing or incomplete data must not directly reduce economic Quality. When the
evidence contract cannot establish Quality, the correct result is unavailable,
partial, or low-confidence Quality—not bad Quality.

The same separation applies to existing positions. A provider outage or lost
evidence may make a capability stale, unavailable, or review-required and may
reduce Confidence or trigger enhanced review. It is not evidence that the company
thesis deteriorated and is not an automatic sell signal.

```text
previous evidence available
provider outage
-> Confidence may deteriorate
-> capability may become stale or unavailable
-> enhanced review may be appropriate
-> NOT automatic SELL
```

Stage F Position Lifecycle remains responsible for material economic deterioration
and structural thesis-break semantics.

## 11. Separation from Confidence

Capability state answers:

> Can PAM perform this exact analysis under its contract at all?

Confidence answers:

> How much evidentiary and model uncertainty remains in an available analysis?

They are related but not interchangeable. `PARTIAL` is not a numeric confidence
score, `SUPPORTED` does not imply high Confidence, and low Confidence does not
retroactively turn valid evidence into false evidence. PR5D0C defines no Confidence
formula or aggregation rule.

## 12. Separation from Opportunity Set

Stage E1 Opportunity Set remains the later, stricter point at which PAM determines
whether a security may participate in investment consideration under current
evidence, model support, and policy constraints.

```text
PARTIAL_ANALYSIS != eligible for allocation
FULL_ANALYSIS_ELIGIBLE != admitted to Opportunity Set
```

Opportunity Set, ranking, recommendation, Portfolio Room, allocation, and execution
must apply their own separately reviewed downstream contracts.

## 13. Relationship to PR5C

PR5C remains the strict comparable-real-EPS route. PR5D0C neither discharges its
blockers nor creates a weaker alternative.

```text
PR5C failure
does NOT automatically mean
security research failure

PR5C failure
DOES mean
every output requiring PR5C remains unavailable
```

Example:

```text
PR5C blocker: SPLIT_BASIS_NOT_ESTABLISHED

strict EPS-growth capability   UNAVAILABLE
strict Expected Return         UNAVAILABLE
revenue analysis               potentially available if its dependencies pass
balance-sheet analysis         potentially available if its dependencies pass
research participation         PARTIAL_ANALYSIS
```

The public SEC/free-Nasdaq evidence graph still lacks complete positive
no-transformation coverage through CURRENT T. Empty event inventories, stable
tickers, stable CIKs, exact EPS values, or other good capabilities do not repair
that source gap.

## 14. Relationship to PR5D0B

PR5D0B illustrates dimensional authority:

```text
VERIFIED_NONPAYER        SUPPORTED
SHARE_BASIS              UNAVAILABLE
PRICE_QUOTE              PARTIAL
BUSINESS_PROFILE         SUPPORTED
```

The supported issuer-level nonpayer source proposition remains valid inside its
explicit limitations. It does not establish selected-class, share-basis,
reporting-subject, PR4B1-root, or final-admission authority. Failure of the
nonpayer route likewise does not invalidate independent revenue, balance-sheet,
or other research capabilities.

## 15. International and source-neutral architecture

Jurisdiction/source adapters may differ while the economic and analytical core
remains source-neutral:

```text
SEC adapter
ESEF adapter
SEDAR+/Canadian adapter
UK adapter
Japan adapter
future adapters
        ↓
source-neutral economic facts
        ↓
dimensional capability assessment
        ↓
only supported analytical outputs execute
```

This architecture does not select a future non-US provider. Jurisdiction-specific
identifiers, filing types, exchange conventions, accounting extraction, and
permitted-use constraints belong in source/admission adapters. They must not create
separate country-specific core analytical models.

## 16. Free-core-operation invariant

> **PAM's supported core system must remain operable without a paid
> financial-data subscription.**

No paid dataset may become a hidden prerequisite for supported core operation.
In particular, core PAM may not require Bloomberg, Refinitiv/LSEG, a Nasdaq
premium dataset, a paid corporate-action feed, or another commercial market-data
API merely to function.

Free, public, and official sources may provide narrower coverage. When those
sources cannot establish a capability, the honest result is `PARTIAL`,
`UNAVAILABLE`, `UNSUPPORTED`, `REVIEW_REQUIRED`, or `CONFLICTED` as applicable.
Guessing, optimistic silence, or weakening a qualification contract is not an
acceptable substitute.

Paid sources may be researched or supported later only as optional coverage
enhancements after separate owner approval and factual-authority, permitted-use,
licensing, retention, and commercial-use review. They must not become necessary
for the supported core system to operate. Commercialization and licensing remain
separate future decisions.

## 17. Legacy V1 boundary

Existing V1 concepts such as:

```text
PROMISING_BUT_INCOMPLETE
INSUFFICIENT_DATA
data_quality HIGH / MEDIUM / LOW
score_missing_data_count
```

are legacy operational, scoring, and reporting semantics. They may inform future
UX research, but they are not V2 economic evidence, capability states, dependency
contracts, Confidence, or admission authority. V1 score thresholds and missing-
data counts must not be reused as V2 evidence authority. PR5D0C does not modify V1.

## 18. Anti-patterns

The following are prohibited:

```text
missing EPS basis
-> assume adjusted

missing corporate-action history
-> company rejected as low quality

missing price
-> use stale guessed price

partial evidence
-> manufacture one global confidence or coverage number

international source is weaker
-> lower company Quality mechanically

unsupported model profile
-> substitute another company or model's assumptions

provider failure
-> sell

market-data ticker exists
-> admit security

one good capability
-> grant global admission
```

It is also prohibited to select the latest, majority, or most convenient evidence
to hide a conflict; to convert review-required evidence into automatic support; or
to let a descriptive UI summary become an authority token.

## 19. Implementation roadmap

PR5D0D, PR5D0E, and PR5D0F implement the first three foundations below. Every
later stage still requires its own reviewed contract and narrow PR.

### Capability contract foundation — implemented by PR5D0D

The source-neutral `analysis_capabilities` package now provides pure, versioned
state, scope and dimensional assessment records with explicit reasons,
limitations, retained support and separate deterministic semantic/evidence
identity. It has no evidence resolver or downstream consumer.

### Dependency contracts — implemented by PR5D0E

The source-neutral `analysis_capabilities` package now provides immutable output
dependency declarations with explicit dependency roles, required capability IDs,
expected subject kinds, accepted `SUPPORTED` or explicit `SUPPORTED + PARTIAL`
states, and deterministic semantic identity.

PR5D0E provides no evaluation, subject binding, assembler, output execution,
research participation classifier, or investment authority. It creates no actual
production output contract. Its declaration layer is now consumed by the PR5D0F
Partial Analysis Assembler described below.

### Partial analysis assembler — implemented by PR5D0F

The source-neutral `analysis_capabilities` package now matches every explicit
dependency role to one exact bound capability scope and determines that output's
dependency availability as `AVAILABLE`, `AVAILABLE_WITH_LIMITATIONS`, or
`UNAVAILABLE`.

Cross-scope dependencies require retained semantic and exact-evidence relationship
identities. Assembler v1 requires exact authority-boundary equality, including
`None`. Exact capability-plus-scope matching accepts semantically equivalent
recaptures while retaining all exact evidence identities; semantically different
matches remain ambiguous and block availability rather than selecting a latest,
majority, or caller-order winner. Upstream partial, unavailable, review-required,
and conflicted reasons and limitations remain visible.

PR5D0F performs no economic calculation or analytical-output execution, creates no
research-participation state, and grants no investment, admission, Opportunity Set,
recommendation, allocation, execution, production, or promotion authority. The
next implementation stage is the Research Participation Classifier.

### Research participation classifier

Derive descriptive participation from legitimate output availability, not from
economic ranking, model score, or investment eligibility.

### Confidence integration

Add uncertainty semantics only after capability availability is stable. Do not
turn capability states into an opaque confidence score.

### Opportunity Set integration

Keep investment consideration as a stricter downstream gate. No research state
alone grants Opportunity Set or allocation authority.

### International adapters

Populate the same source-neutral facts and capabilities from reviewed jurisdiction-
specific sources without country-specific analytical engines.

## 20. Explicit nonclaims

```text
Does this PR make PR5C more permissive? NO.

Does this PR create a fallback Expected Return model? NO.

Does this PR make partially analyzed securities investable? NO.

Does this PR change Quality calculations? NO.

Does this PR implement Confidence? NO.

Does this PR modify Opportunity Set behavior? NO.

Does this PR change V1? NO.

Does this PR change model rules? NO.

Does this PR require paid data? NO.

Can paid data become mandatory for core PAM operation? NO.
```

PR5D0C adds no runtime types, assembler, classifier, source adapter, analytical
module, score, threshold, formula, policy value, recommendation, allocation,
deployment, production authority, or automatic promotion. PR5C remains blocked,
PR5D remains incomplete, and PR5E has not started.
