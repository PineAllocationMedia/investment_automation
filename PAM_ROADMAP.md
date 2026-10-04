# PAM_ROADMAP.md

> Dynamic project state and planned direction.
>
> This file is intentionally more changeable than `PAM_PROJECT_CONSTITUTION.md`.
> Update it when a meaningful chantier is merged, reordered, deferred or redefined.
>
> Exact remote state must always be verified before implementation.

---

## 1. Current project phase

**Phase:** V2 evidence-qualified Expected Return foundation

V1 remains the frozen operational control.

V2 is a challenger architecture being built to support a future global research and
portfolio-intelligence platform.

Current product direction:

> **PAM = financial research intelligence + portfolio intelligence**

Commercial recommendation/advisory functionality is not the immediate target.

---

## 2. Current authoritative branches

### V1

Branch:

`main`

Frozen baseline identity:

- `VALIDATION_BASELINE_V1`
- `MODEL_RULES_VERSION = 2026-08-23-allocation-room-integrity-v7`
- tuning = `PROPOSAL_ONLY`

Historical SHA at this roadmap creation:

`c5fc27c82c29c2a6027eccee245098c4a072fdf1`

Historical tree:

`26a69bb0b2185ab141af0763da2d965602c8346b`

### V2

Integration branch:

`model-v2/expected-return-challenger`

Verified pre-PR5C integration state (2026-09-28):

Commit:

`64dbfc20b6d3b282ce0d29a80ace22588d556c67`

Tree:

`755747f3452dd48267e4408ceabd2f41d29ba4c4`

Always verify current remote state before using these values.

---

## 3. Completed V2 foundation

### PR1 — runtime isolation ✅

Purpose:
keep V2 development/runtime concerns isolated from frozen V1 operation.

### PR2 — validation identity ✅

Purpose:
protect validation identity and make behavioral changes visible.

### PR3 — immutable retrospective PIT harness ✅

Purpose:
create a strict retrospective evidence framework without falsely treating current data as historical knowledge.

---

## 4. Expected Return foundation

### PR4A — pure Expected Return foundation ✅

Core ER mechanics separated from acquisition/provider logic.

### PR4B1 — synthetic assumption constructor ✅

Qualified synthetic fact constructor for ordinary-compounder ER mechanics.

### PR4B2 — PIT Expected Return sidecar ✅

Retrospective/PIT-related Expected Return support without granting false historical authority.

---

## 5. SEC / economic-fact qualification chain

### PR4C1 — offline SEC diluted-EPS archive/extractor ✅

Pure fictional/offline mechanics and provenance contracts.

### PR4C2 — trusted live SEC Companyfacts acquisition ✅

Strict acquisition contract for current Companyfacts capture.

### PR4C3 — five-year diluted-EPS resolver ✅

Resolves five consecutive reported annual diluted-EPS periods with exact Decimal values,
calendar policy, retained filing-version lineage and fail-closed conflict handling.

### PR4C4 — security identity qualification ✅

Qualifies issuer, common security/class and supported listing identity in synthetic scope.

### PR4C4.1 — cross-form compatibility correction ✅

Corrected C3→C4 compatibility so agreeing retained cross-form observations do not break the identity contract.

### PR4C5 — share-basis / split qualification ✅

Qualifies common-share denomination across the EPS history with transformation mode `NONE`.

### PR4C6 — reporting-subject continuity ✅

Merged PR #40.

Qualifies the remaining synthetic measurement-comparability property:

> all retained EPS observations belong to one continuous accounting reporting subject
> through the current qualification boundary.

No earnings normalization is introduced.

---

## 6. Current qualified synthetic chain

```text
Companyfacts-shaped source evidence
        ↓
PR4C3
reported five-year diluted EPS
        ↓
PR4C4
security / class / listing identity
        ↓
PR4C5
share basis / split denomination
        ↓
PR4C6
reporting-subject continuity
```

Important:

> This chain is still synthetic/mechanical qualification.

It does not yet constitute a complete real-data admission path into the production investment model.

---

## 7. Completed memory architecture

### PAM memory architecture ✅

Established canonical memory documents:

- `PAM_PROJECT_CONSTITUTION.md`
- `AGENTS.md`
- `PAM_ROADMAP.md`

Purpose:

- make the project transferable across AI tools;
- prevent conversation-memory dependence;
- preserve product direction;
- make V1/V2 authority boundaries obvious;
- reduce architecture drift.

Existing documents remain:

- `DECISIONS.md` — detailed decision log;
- `AUDIT_GUIDE.md` — V1 audit workflow;
- `BASELINE_V1_FREEZE.md` — V1 freeze contract;
- `docs/contracts/v2/expected_return/EXPECTED_RETURN_PR*.md` — feature contracts;
- `README.md` — operational/user documentation.

---

## 8. Current technical frontier — Stage B Expected Return completion

### Real-source chain through PR5C comparable historical EPS presentation ✅

Merged PR4D1 through PR4D4D3B now provide a controlled CURRENT Companyfacts
authority boundary; complete-submission, Submissions, Nasdaq Listed and SEC
ticker/exchange captures; registered-security and common-class/EPS source claims;
historical taxonomy profiles; a Property-4 temporal dossier and T boundary; one
exact CURRENT SEC/Nasdaq registered-listing bridge; filing-document and direct
Section-12 source discovery; common-stock source scopes; a same-filing class
source bridge; and an ordered temporal common-stock source correspondence series.

These source capabilities do not silently establish share basis, reporting
subject, quote semantics, publication time, or final admission. Merged PR5B adds
the reviewed narrow CURRENT route-local issuer/security, ordinary-common,
relevant-class, direct-listing-source and EPS-applicability qualification. D1
still establishes only route-specific acquisition provenance, capture-bound
CURRENT observed availability and snapshot scope. Factual authority remains
separate from permitted/commercial use.

Merged PR5C0A adds controlled reporting-subject filing-universe, metadata-signal
and explicit source-local claim evidence only. Merged PR5C0B separately adds
controlled corporate-action/share-basis source claims. Neither source layer alone
establishes continuity/comparability or discharges an admission blocker. PR5C now
freshly replays those layers with successful PR5B, exact C3 and one controlled
five-period SEC presentation to establish narrow historical presentation
comparability. It does not bridge a later/current quote to that basis.

### PR5A — Real Fact Admission gap review ✅

`docs/contracts/v2/expected_return/EXPECTED_RETURN_PR5A_REAL_ADMISSION_GAP_REVIEW.md`
audits the actual code, tests,
synthetic semantics and real-source chain at post-PR #62. It freezes one narrow
first route and distinguishes existing sufficient evidence, immediate real
closures, deferred requirements and optional refinements. PR5A is documentation
only and grants no implementation or admission authority.

The hyper-fragmented PR4D4D numbering sequence is closed. The attempted PR5C
evidence checkpoint correctly found that positive reporting-subject and share-
basis source foundations are still missing. The reviewed immediate sequence is:

1. **PR5C0A — Reporting-subject source foundation:** controlled SEC filing
   inventory, metadata signals, exact passages and explicit source-local claims;
   no continuity conclusion and no blocker discharge.
2. **PR5C0B — Corporate-action/share-basis source foundation:** merged source
   layer preserving controlled filing-universe, explicit action/presentation
   claims, ratios, dates, class scope, provenance and conflicts only. It does not
   establish share-basis comparability or discharge `SPLIT_BASIS_NOT_ESTABLISHED`.
3. **PR5C — Comparable real EPS qualification:** positive single-presentation
   historical share-basis and reporting-subject qualification, including only
   explicitly retrospective `ALL_PERIODS_PRESENTED` split-adjusted cases.
4. **PR5D — Remaining real Expected Return roots:** controlled current price and
   quote semantics, explicit quote-to-PR5C-basis linkage, dividend/nonpayer state,
   ordinary-compounder profile and reviewed applicable ER policies.
5. **PR5E — Final admission and real ER adapter:** completed closed
   evidence-replaying admission join and real-capable typed facts into the
   existing PR4B1/PR4A path for the explicitly supported bounded first route.

### PR5D0A — Expected Return policy governance foundation

PR5D0A is proposal/governance infrastructure only. It validates and packages one
complete four-policy candidate set under deterministic content identity and the
closed status `PROPOSAL_ONLY`. It supplies no numerical production policy, owner
approval, operational consumer, real issuer connection, or investment-rule change.
Owner-approved mature-growth, terminal-valuation, payer and nonpayer policy values
remain required in a separate reviewed repository change. PR5D remains incomplete.

### PR5D0B — Controlled SEC verified-nonpayer source qualification

PR5D0B adds a strict issuer-level Companyfacts source route for the existing
PR4B1 nonpayer alternative. It requires both reviewed annual US-GAAP common-stock
dividend-per-share concepts—declared and cash paid—to be exactly zero for the
exact latest required period, with every retained comparable version agreeing and
no positive intra-period contradiction. Missing or silent dividend data never
becomes zero. The first real ER route is therefore temporarily narrowed to
positively verified nonpayers; payer support is deferred.

This advances distribution source evidence only. PR5D remains incomplete: no
selected-class/share-basis/reporting-subject join, PR4B1 real root, price/quote,
ordinary-compounder profile, or owner-approved numerical policy values are added.

### PR5D0C — Capability-Based Partial Analysis Architecture

PR5D0C is cross-cutting architecture/documentation only. It formalizes
source-neutral dimensional capability states (`SUPPORTED`, `PARTIAL`,
`UNSUPPORTED`, `UNAVAILABLE`, `REVIEW_REQUIRED`, `CONFLICTED`), per-output
dependency and availability boundaries, and research participation separately
from Confidence and Opportunity Set authority. One missing capability may block
every dependent output without erasing independent research capabilities.

PR5D0C adds no runtime behavior, fallback Expected Return, model rule, score,
ranking, recommendation, allocation or admission authority. It did not itself
unblock PR5C, complete PR5D or start PR5E. The supported core must remain
operable without a paid financial-data subscription; paid sources may only be
optional, separately approved coverage enhancements.

### PR5D0D — Capability Contract Foundation

PR5D0D implements the first PR5D0C runtime-neutral layer: a source-neutral,
immutable capability scope and assessment representation with the exact six-state
vocabulary and separate deterministic semantic/evidence identities. Positive and
unresolved evidence-bearing states fail closed without retained support.

It implements no dependency graph, partial-analysis assembler, research
participation classifier, Confidence, Opportunity Set integration, source adapter,
or downstream consumer. It changed no admission authority, did not unblock PR5C,
did not complete PR5D, and did not start PR5E.

### PR5D0E — Dependency Contracts

PR5D0E implements the source-neutral declaration layer between capability
assessments and future analytical outputs. Each output contract declares exact
dependency roles, source-neutral capability IDs, expected subject kinds, and whether
it accepts only `SUPPORTED` or explicitly accepts `SUPPORTED + PARTIAL`.

It creates no actual analytical-output wiring, dependency evaluator, subject
binding, assembler, research participation classifier, score, admission authority,
or investment authority. It did not unblock PR5C, complete PR5D, or start PR5E.

### PR5D0F — Partial Analysis Assembler

PR5D0F implements the first pure evaluator for one analytical output's declared
dependencies. It binds every dependency role to one explicit capability scope and
produces `AVAILABLE`, `AVAILABLE_WITH_LIMITATIONS`, or `UNAVAILABLE` while
preserving partial and unavailable reasons, limitations, and semantic/exact
evidence identities.

It calculates no analytical value and does not aggregate whole-company research
participation. It changed no admission or investment authority, did not unblock
PR5C, did not complete PR5D, and did not start PR5E.

### PR5D0G — Research Participation Classifier

PR5D0G classifies one research subject from a reviewed profile contract, an
explicit profile-support capability assessment, and independently assembled output
availability. Only explicit profile-support `UNSUPPORTED` yields
`UNSUPPORTED_RESEARCH_PROFILE`; missing or unresolved data instead preserves
candidate or partial research behavior.

It implements no economic output, score, Confidence, Opportunity Set, admission,
recommendation, allocation, execution, or production authority. It did not unblock
PR5C, complete PR5D, or start PR5E at that stage.

### PR5D1 — Controlled Free Current Quote Foundation

PR5D1 adds one immutable, fixed-profile Yahoo Finance Chart route for the exact
freshly replayed PR5B direct Nasdaq listing. It establishes a positive current
observed price, explicit USD currency, `CURRENCY_PER_SHARE` unit semantics, one
reviewed Yahoo Nasdaq venue representation, and distinct provider-market/capture
timestamps. Factual authority remains separate from `UNKNOWN` licensing and
`REVIEW_REQUIRED` use status; commercial redistribution is not authorized.

PR5D1 does not establish the quote-to-PR5C basis linkage, distribution root,
ordinary-compounder profile, owner-approved policies, complete PR5D non-EPS
bundle, PR4B1 root, or final admission. PR5D2 supplies the separate bridge and
complete bundle without rewriting PR5D1's boundary.

### PR5D2 — Complete Free Real Expected Return Roots

PR5D2 adds the bounded free SEC + Yahoo action-aware quote-to-EPS basis bridge,
with an exact inspectable SEC root-snapshot boundary and monotonic continuation
of the PR5C/PR5B route inventory rather than a completeness claim through CURRENT,
the route-local same-Companyfacts verified-nonpayer join, the SEC-backed
`ORDINARY_COMPOUNDER` methodology-profile qualifier, the exact owner-approved
0%/3%/5% mature-growth and 12x/16x/20x terminal policies, and one complete
inspectable PR5D bundle. It constructs no PR4B1 real roots and calculates no
Expected Return; completed PR5E provides the separate final admission and adapter.

Basis-bridge unavailability is a legitimate per-company state but must not become
the dominant result for otherwise supported ordinary candidates. If it is
frequently the sole blocker in shadow observation, treat that as a FREE-DATA
COVERAGE ENGINEERING PROBLEM: improve free adapters, bounded reconciliation,
accessible filing capture, or official/public corroboration. Do not silently
weaken identity/economic semantics, classify the company as bad, or require paid
data for core operation. No numerical coverage threshold is established here.

```text
PR5D0D → PR5D0E → PR5D0F → PR5D0G
COMPLETE for the current capability-foundation interlude.
```

PR5E completed the first bounded real route:

```text
PR5D2 → PR5E final admission → real PR4B1 facts
→ PR4B1 assumption construction → PR4A Expected Return
```

The approved administrative interlude is complete:

```text
PR5D2 complete
    ↓
Governance Reform Phase 1 complete
    ↓
Governance Cleanup / Migration complete
    ↓
Configure ChatGPT role Projects/employees complete
    ↓
PR5E complete
    ↓
Stage B — Expected Return completion active technical frontier
    ↓
VFV CURRENT evidence foundation complete (PR #86)
    ↓
VFV standalone forward Expected Return complete (PR #88)
    ↓
VFV FX/hedge evidence prerequisite complete (PR #90)
    ↓
Bounded company-vs-VFV Expected Return comparator complete (PR #90)
    ↓
Source-neutral CASH_LIKE_CURRENT_CARRY Slice A complete (PR #92)
    ↓
Source-neutral EXECUTABLE_ENTRY_EVIDENCE B1 complete (PR #94)
```

This governance sequence was an administrative prerequisite, not a replacement for
PR5E and not an expansion of Expected Return architecture. Role configuration and
PR5E are complete. Stage B implementation now includes the bounded VFV CURRENT
evidence foundation, standalone VFV forward Expected Return diagnostic, qualified
VFV FX/hedge evidence prerequisite, bounded company-vs-VFV comparator and the
source-neutral current nominal cash-like carry Slice A and executable-entry evidence
B1 foundations; Stage B remains active and incomplete, and later technical stages
remain in their existing order.

No additional pre-Stage-B Expected Return architecture interlude is authorized in
this sequence. B1 is complete. The immediate Stage B direction belongs to Data &
Evidence for qualification of a real executable-entry evidence route where
supportable. B2 numeric seven-year entry-execution-net transformation remains
unsupported and unauthorized until real qualified executable quote and execution-
cost evidence sufficiently supports its transformation boundary.

The public SEC/free-Nasdaq source graph still lacks complete positive
no-transformation coverage through CURRENT T. PR5C therefore uses positive
historical five-period presentation evidence rather than silence. PR5D established
the separate current quote-to-qualified-EPS-basis bridge, and PR5E now freshly
replays both before final admission. This partition does not relax the final
economic comparability requirement.

Universal identity, universal issuer-wide class inventory, corporate-action, M&A,
exhaustive legal-right, listing-inventory and HISTORICAL_AS_OF engines are not
prerequisites for that first route when affected cases fail closed. PR5B must still
positively establish the supported ordinary-common participation profile and
affirmative route-local relevant-class coverage; absence of an observed second
class is insufficient. The broader capabilities remain roadmap requirements and
do not disappear merely because they are deferred. Stage A is complete only for
the explicitly supported bounded first CURRENT route; this is not universal or
global Real Fact Admission completeness. The immediate frontier is **Stage B —
Expected Return completion**, followed by the unchanged pre-shadow sequence in
section 9.

---

## 9. Expected future V2 sequence

The exact PR numbering may change. The conceptual sequence is more important.
The following are approved V2 completeness requirements, not implemented behavior
or authorization to implement them in this documentation PR. Future contracts must
define supported cases and validation without inventing thresholds here.

Permanent shadow invariant:

> **V2 shadow begins only after the approved V2 architecture is feature-complete
> within its explicitly supported scope.**

Feature-complete means that the V2 completeness requirements in this roadmap are
implemented, or deliberately and explicitly marked unsupported/deferred outside
the approved supported scope; required cross-component contracts are stable enough
for longitudinal validation; and final architecture cleanup plus the full readiness
review have passed. It does not mean every possible future PAM feature, country,
exchange, provider or commercial product surface is complete.

Stage U is therefore primarily a validation and evidence-accumulation phase, not
a normal major-feature-development phase. Beginning shadow with a largely stable
architecture keeps early and late forward observations meaningfully comparable.

```text
Real Fact Admission → Expected Return completion → Quality → Durability → Confidence
→ Opportunity Set → Position Lifecycle / Thesis Deterioration → Stress / Crisis Resilience
→ Portfolio Room / Portfolio Intelligence → Data & Operational Resilience
→ Portfolio State Integrity → Portfolio Risk / Shared Exposure / ETF look-through
→ Dependency & Invalidation → Persistent Decision / Thesis Memory
→ Decision Delta & Attribution → Outcome Evaluation → Benchmark & Performance Integrity
→ Validation / Audit / Backtest Modernization → Validation Firewall
→ Calibration Governance → Mode Contract & Objective Personalization
→ Recommendation / Execution Separation → Monitoring / Observability
→ Commercial Data Governance
→ Compact Report Information Architecture & UX → any additional future V2 chantiers
→ agreed initial international capability complete
→ FINAL Architecture Cleanup & Dead-Code Retirement
→ final regression/integrity/shadow-readiness review
→ V2 isolated Chromebook integration/automation → long-duration shadow validation
→ explicit authority review
```

Global Universe & Cross-Market Admission Architecture is a cross-cutting program,
not a separate engine added after the other stages. Its contracts integrate where
relevant into Real Fact Admission, Opportunity Set, Portfolio Intelligence,
Portfolio State, Shared Exposure, Dependency & Invalidation, Decision / Thesis
Memory, Validation and Commercial Data Governance. Complete global-market coverage
and the full commercial UI are not prerequisites for shadow. Functional initial
international capability, as defined below, is part of pre-shadow V2 scope.
Inserted stages use numeric suffixes to preserve existing stage references.

### Stage A — Real Fact Admission

- controlled CURRENT acquisition and source-correspondence foundation completed
  through PR #62, with the reviewed narrow CURRENT PR5B qualification merged in
  PR #64;
- PR5A closure review and deliberately narrow first-route definition;
- PR5B route-local issuer/security, ordinary-common participation,
  affirmative relevant-common-class coverage, direct-listing source and
  EPS-applicability qualification;
- PR5C0A reporting-subject source evidence without continuity or blocker discharge;
- PR5C0B separately reviewed corporate-action/share-basis source evidence;
- PR5C positive single-presentation historical share-basis and reporting-subject
  qualification, with explicit split-adjusted evidence where applicable and no
  current quote-basis claim;
- PR5D0A proposal-only governance for deterministic review of complete candidate
  policy sets, without owner-approved numerical values or any operational consumer;
- PR5D0B controlled issuer-level source qualification for the strict two-concept
  annual verified-nonpayer condition, with payer support deferred and no PR4B1 root;
- PR5D0C capability-based partial-analysis architecture, preserving independent
  research availability without weakening any dependent admission requirement;
- PR5D0D source-neutral capability contract foundation only, with no dependency
  graph, assembler, research participation classifier or admission authority;
- PR5D0E source-neutral per-output dependency declarations only, with canonical
  accepted states and semantic identity but no evaluator, binding, assembler,
  actual output wiring or admission authority;
- PR5D0F pure per-output dependency assembler, with explicit scope bindings,
  cross-scope relationship evidence, strict v1 boundary equality, deterministic
  output availability and preserved reasons/limitations, but no analytical value,
  research-participation aggregation or admission authority;
- PR5D0G pure research-participation classifier, with explicit profile support,
  exact output/dependency-contract pinning, common research-subject scope, and the
  four descriptive participation states, but no economic output, score, Confidence,
  Opportunity Set, admission or investment authority;
- PR5D1 controlled free current quote foundation, establishing current observed
  USD-per-share price and selected direct-listing linkage only;
- PR5D2 complete for the bounded free quote-to-PR5C-basis bridge, route-local
  verified-nonpayer evidence, ordinary-compounder methodology profile,
  selected-class joins, owner-approved policies, and complete PR5D bundle;
- PR5E completed the final admission join and real-capable adapter into Expected
  Return facts for the explicitly supported bounded first CURRENT route, reaching
  real PR4B1 facts, PR4B1 assumption construction and PR4A Expected Return;
- route-specific factual authority kept separate from permitted/commercial use;
- broader identity, action, listing, historical-PIT and international capabilities
  remain required according to their later approved scope, without blocking the
  first safe CURRENT route when unsupported cases fail closed.

### Stage B — Expected Return completion

#### VFV CURRENT evidence foundation ✅

PR #86 is the first completed Stage B implementation milestone. It establishes one
Vanguard first-party VFV route with exact immutable capture, bounded acquisition,
offline extraction, deterministic qualification, typed provenance and closed
outcomes. Its qualified `CURRENT_ONLY` facts cover current issuer market observation;
fund identity, listing and tracked-index facts; separate management fee, MER and TER
semantics; current distribution facts; trailing fund-portfolio P/E; and CAD listed/
base currency.

The milestone does not establish underlying economic currency exposure, hedge status,
FX comparability, forward earnings/growth/P/E, VFV forward Expected Return,
company-vs-VFV comparison, executable net instrument economics, cash-like opportunity
cost, PIT, `HISTORICAL_AS_OF`, or commercial/production authority. Its currency
boundary expressly retains `NO_UNDERLYING_EXPOSURE_CURRENCY_AUTHORITY`,
`NO_CURRENCY_HEDGE_STATUS_AUTHORITY` and `NO_FX_COMPARABILITY_AUTHORITY`.

#### Standalone VFV forward Expected Return ✅

PR #88 completes the bounded standalone VFV forward Expected Return methodology,
CEO numerical-policy approval and canonical research diagnostic. The approved
policy is `PAM_VFV_FORWARD_ER_POLICY_2026_10_01_V1`, hash
`31dbebd0545c233c4913dad1915dfd2eb23d91481019fec078b245541ef0e645`,
with methodology `2026-10-01-vfv-normalized-unit-cashflow-irr-v1`, seven-year
horizon, bear/base/bull growth of 0%/3%/5%, and terminal P/E of 12x/16x/20x.

The canonical path is:

```text
qualified VFV CURRENT evidence
→ fixed CEO policy
→ VFV-specific normalized-unit adapter
→ deterministic unit-holder cash-flow problem
→ shared semantic-neutral IRR solver
→ standalone VFV research diagnostic
```

The return basis is `NOMINAL_PRE_HOLDER_TAX_UNIT_HOLDER_CASHFLOW_IRR`; the principal
result is `VFV_INSTRUMENT_ER_NET_OF_WRAPPER_EXPENSES_PRE_EXECUTION`; and the FX
basis is `CONSTANT_TRANSLATION_NO_FX_CONTRIBUTION_MODELED`. The implementation uses
`V0 = 1`, treats weighted trailing P/E as `M0` rather than ETF earnings, starts
unit-holder cash flow from trailing distributions, and applies wrapper drag once as
`q = (1 - MER)(1 - TER)` while keeping management fee visible without double-counting
it. It produces neither benchmark ER nor executable-net ER. Local Stage-B confidence
is `LOW` without an Expected Return haircut. The Decimal problem path is code-owned
and deterministic; the public root remains a raw float, while identity version
`2026-10-01-vfv-forward-er-root-problem-identity-v2` binds the deterministic root
problem rather than the float result.

This standalone capability did not by itself alter company policy or grant comparator,
FX-resolution, production, recommendation, allocation, execution, V2-promotion or
automatic-tuning authority. PR #90 subsequently supplied a separate qualified
FX/hedge evidence prerequisite and bounded comparison contract without changing the
standalone diagnostic's own authority.

#### Qualified VFV FX/hedge evidence prerequisite ✅

PR #90 adds the exact evidence prerequisite for the reviewed comparison: material
underlying USD exposure and a materially-unhedged-to-CAD state at the 2026-06-30
disclosure boundary. This meaning is capture-bound and date-bound. It is not a
permanent hedge-policy claim, FX forecast, realized-CAD-return model or universal
FX-comparability authority.

#### Bounded company-vs-VFV Expected Return comparator ✅

PR #90 makes canonical the bounded current-real route:

```text
current real PR5E company Expected Return
+ standalone VFV Expected Return
+ exact qualified VFV FX/hedge evidence
→ same-label deterministic company-vs-VFV Expected Return spreads
```

The comparator contract is
`2026-10-01-company-vfv-expected-return-comparator-v1`; the unchanged reviewed
economic basis is `2026-10-01-company-vfv-constant-fx-comparison-v1`; and authority
is `RESEARCH_DIAGNOSTIC_ONLY`. Only company bear minus VFV bear, base minus base and
bull minus bull are supported. These spreads are not probability-weighted
outperformance forecasts, CAD-return forecasts, rankings, recommendations or
allocation signals.

Canonical CI #109 exposed a genuine comparator identity-boundary defect rather than
a stale pin: PR5E admission identity transitively carried platform-sensitive PR4B1
binary64 lineage and replay/provenance state. The corrected head introduced the
comparator-owned company problem identity representation
`2026-10-01-company-vfv-problem-identity-v2`. PR5E admission semantic/evidence IDs
remain trace metadata but no longer drive comparator identity. Corrected canonical
CI #110 passed `FULL_PIT`, 2,796/2,796, before the CEO merged PR #90.

#### Cash-like current-carry foundation ✅

PR #92 makes canonical the source-neutral `CASH_LIKE_CURRENT_CARRY` Slice A
contract for current nominal carry under the first bounded settled-cash-balance
profile. It preserves exact Decimal rate/currency/semantic meaning, deterministic
semantic/evidence identities and closed fail-safe qualification. Positively evidenced
zero remains zero; missing evidence never becomes zero.

Architecture & Audit found one A-class chronology defect in the initial head. The
corrected head separates absolute UTC instant comparison for complete timestamps from
the calendar date represented by `retrieved_at` in its supplied original offset for
date-only `effective_date`. Closed-result precedence is programming-contract error,
then `SOURCE_CONFLICT > UNSUPPORTED > UNAVAILABLE > AVAILABLE`. Final review returned
`MERGE READY`, CI #113 succeeded and the CEO merged PR #92 as
`679e6dda95989d9bb4b34cfc186e801f84bc823b`.

Authority is CURRENT/capture-bound only. This milestone adds no PIT,
`HISTORICAL_AS_OF`, provider acquisition route, owner-specific live cash fact,
seven-year cash Expected Return, company/VFV-versus-cash comparison, reserve
activation/release logic, recommendation, allocation, execution, production or
deployment authority. Current cash carry remains distinct from both seven-year cash
Expected Return and later opportunity-cost comparison.

#### Executable-entry evidence B1 foundation ✅

PR #94 makes canonical the source-neutral `EXECUTABLE_ENTRY_EVIDENCE` B1 contract
for one bounded CURRENT/capture-bound potentially executable purchase-entry context.
It binds opaque execution-context and target-instrument scope, preserves independent
eligibility, settled-funding, commission, settlement, currency-path and executable-
quote dimensions, and retains qualified partial facts when another required
dimension is unavailable. Exact zero commission remains valid; missing commission
never becomes zero. The first bounded settlement profile is
`POST_TRADE_REGULAR_WAY / T_PLUS_1`. Same-currency routes establish only
`FX_NOT_REQUIRED_SAME_CURRENCY`; cross-currency routes fail closed without qualified
FX execution-cost evidence. Closed precedence is
`SOURCE_CONFLICT > UNSUPPORTED > UNAVAILABLE > AVAILABLE`.

Architecture & Audit classified the implementation and its high-attention typed
executable-quote authority boundary as `C — expected behavior` and returned
`MERGE READY`. Informational/current-observed quotes do not become executable quotes;
synthetic `AVAILABLE` fixtures prove mechanics only. GitHub Baseline V1 CI #115
completed successfully, and the CEO merged PR #94 as
`6a2cc7fd96f008dbdd05d9a5fdc80480a6694fd9`, tree
`e60a91445f7b229aff92e1161c524882ceb9a635`.

B1 establishes no real executable quote route, provider/broker adapter, live owner-
specific facts, order construction/submission, execution authority, aggregate
friction, executable-net Expected Return, B2, recommendation, allocation, production,
deployment or V2 promotion authority. A real positive executable quote still requires
a separately reviewed authenticated source route/adapter.

The expected immediate sequence is:

```text
bounded company-vs-VFV Expected Return comparator complete
→ Slice A current carry complete
→ B1 executable-entry evidence foundation complete
→ real executable-entry evidence route qualification
→ B2 numeric executable-net transformation only when evidence support exists
→ confidence propagation
→ explicit unsupported cases
```

- completed: Data & Evidence currency/hedging prerequisite and reviewed compatible
  comparison basis;
- completed: bounded VFV forward ER comparator;
- completed: source-neutral `CASH_LIKE_CURRENT_CARRY` Slice A for one bounded
  settled-cash-balance profile;
- completed: source-neutral `EXECUTABLE_ENTRY_EVIDENCE` B1 foundation and closed
  failure states;
- next owner/direction: Data & Evidence qualification of a real executable-entry
  evidence route where supportable;
- B2 numeric seven-year entry-execution-net transformation remains unauthorized and
  blocked until real qualified executable quote and execution-cost evidence supports
  it; no positive real or numeric executable route currently exists;
- confidence propagation;
- explicit unsupported cases.

### Stage C — Quality

Build transparent, evidence-backed measures for topics such as:

- profitability quality;
- returns on capital;
- balance-sheet strength;
- capital allocation;
- dilution;
- cash conversion;
- economic moat evidence.

Avoid creating one opaque magic score.

### Stage D — Durability

Assess whether economic advantages are likely to persist.

Possible dimensions:

- competitive structure;
- switching costs / network effects / scale;
- disruption risk;
- regulatory dependence;
- cyclicality;
- reinvestment runway;
- business-model resilience.

Qualitative evidence must remain provenance-aware.

### Stage E — Confidence

Aggregate information uncertainty separately from economic risk.

Confidence should reflect:

- source authority;
- completeness;
- contradictions;
- freshness;
- model uncertainty;
- assumption sensitivity;
- historical evidence maturity.

Low confidence should reduce authority/sizing rather than fabricate certainty.
For new deployable capital, fail-closed evidence may support temporary reserve
rather than guessed deployment. `DATA_UNAVAILABLE` and low Confidence are neither
automatic cash rules nor sell signals; existing positions remain subject to Stage F.
Capability availability remains separate: it asks whether one exact analysis can
run at all, while Confidence describes uncertainty in an available analysis.
`PARTIAL` is not a numeric Confidence score and `SUPPORTED` does not imply high
Confidence.

### Stage E1 — Opportunity Set

Establish which securities are eligible for consideration under current evidence,
data coverage, model support and policy constraints before portfolio allocation
decisions become mature. Distinguish supported and qualified, observable but not
yet admissible, unsupported, and unavailable / insufficient evidence. This stage
defines no scoring formula or ranking threshold; observability alone is not admission.
The global discovery/admission funnel and dimensional market capability state below
must constrain this stage and fail closed.
Research participation is broader than Opportunity Set admission:
`RESEARCH_CANDIDATE`, `PARTIAL_ANALYSIS` and `FULL_ANALYSIS_ELIGIBLE` are
descriptive research states, not allocation eligibility. Every analytical output
must satisfy its own dependencies before this stricter downstream gate is applied.
Cash, cash-like holdings and short-government-bill instruments are capital
destinations/liquidity classes, not company candidates; they receive no company
Quality, Durability, moat score or company ranking.

### Stage F — Position Lifecycle / Thesis Deterioration

Distinguish normal volatility, temporary deterioration, information uncertainty,
material fundamental deterioration and structural thesis break. Conceptual states
may include `ADD`, `HOLD`, `STOP_ADDING`, `ENHANCED_REVIEW`, `TRIM_REVIEW` and
`EXIT_REVIEW`; these are future contract concepts, without numeric thresholds.

Price decline is not thesis deterioration; crisis is not an automatic sell signal.
Selling remains rare and thesis-driven. Deterioration states may recover when
evidence genuinely improves. Trim/exit review should consider Expected Return,
Quality, Durability, Confidence, Portfolio Room, concentration and shared economic
exposure.
Reserve logic applies primarily to deployable capital and must not become a parallel
liquidation engine. Market difficulty, higher volatility, recession probability or
temporarily attractive reserve carry does not authorize selling an existing healthy
position into reserve.

### Stage G — Stress / Crisis Resilience

Assess thesis resilience under stress and crisis, with explicit evidence and
uncertainty. This layer concerns business/portfolio resilience, not macro timing.
Stress state may change scenario assumptions, Confidence, liquidity awareness,
Portfolio Room and risk visibility, but must never mechanically produce
`CRISIS → CASH`. Falling prices may improve prospective benchmark Expected Return.

### Stage H — Portfolio Room / Portfolio Intelligence

Build the analytical layer for positions, room, exposures, concentration,
expected-return distribution, thesis state, watchlists, change history, alerts
and comparative opportunity context.
For supported international instruments, this includes coherent cross-listing,
wrapper, currency and economic-geography context without turning listing venue into
economic exposure.
Distinguish invested capital, deployable cash, temporary strategic reserve,
transactional cash, unsettled/unavailable cash, reserve currency and instrument,
and redeployability. Temporary reserve remains visible capital awaiting
reconsideration, not capital removed from the opportunity set.

### Stage I — Data & Operational Resilience

Explicitly handle stale data, source/provider failure, partial or contradictory
evidence, failed runs, degraded mode and freshness/source-health visibility.

> A data outage or evidence failure must not silently become an investment signal.

Cash-like yields, broker costs, FX assumptions, account capabilities and instrument
eligibility are time-sensitive evidence. Stale or unavailable values must remain
explicit and must not silently become zero cost or current truth.

### Stage J — Portfolio State Integrity

Reconcile economic ownership through transactions, cash, dividends, splits,
mergers, spin-offs, security/class/ticker/listing changes and FX where relevant.
This is a completeness requirement, not a new ledger design.
Supported cross-market instruments must preserve economic ownership across listings,
wrappers, quote/transaction currencies and relevant corporate actions.
Future state must reconcile CAD and USD cash, cash-like and benchmark holdings,
individual securities, contributions, distributions, proceeds, FX conversions,
reserve creation/release, trades and settlement state while preserving native
currency before any reporting conversion.

### Stage K — Portfolio Risk / Shared Exposure

Expose interpretable risks across sector, geography, currency, business model,
common macro drivers, liquidity, concentration and hidden/shared economic exposure.
Do not prescribe Markowitz or covariance-driven optimization.

#### ETF / Fund Look-Through & Exposure Intelligence

Future V2 capability: understand an ETF/fund as an economic exposure container.
**Nominal concentration** is the portfolio weight in each directly held ticker/fund;
**economic concentration** is aggregated underlying exposure after appropriate
look-through. Preserve both views. This subsection authorizes no implementation;
future contracts will define exact sources, schemas, algorithms and supported cases.

- **Economic classification:** identify broad-market equity, sector/thematic equity,
  country/region equity, emerging markets, fixed income, cash-like, commodity,
  digital asset, asset-allocation funds and other reviewed structures where evidence
  permits. Classification must be evidence-backed, never inferred solely from ticker
  text. Remain fund/provider/global-neutral: no universal dependency on one provider,
  exchange, country, identifier system or fund-report format. Source-specific adapters
  should map into source-neutral economic exposure concepts.
- **Holdings and overlap:** where reliable holdings evidence exists, decompose funds
  across constituent/security, sector, industry, country/geography, currency,
  market-cap profile, business-model/theme, common macro drivers and relevant risk
  factors. Transparency varies by fund. Aggregate direct exposure to a security plus
  indirect exposure through all funds; apply the same principle to other reviewed
  exposure dimensions. Detect direct-stock ↔ fund overlap and fund-to-fund shared
  constituents and economic drivers, so nominally different wrappers do not conceal
  combined exposure or hidden concentration.
- **Geography and currency:** distinguish fund domicile/listing venue, quote currency
  and underlying economic geography. Canadian listing does not imply Canadian
  economic exposure. Separately retain quote currency, underlying asset denomination,
  economic FX exposure and hedged/unhedged structure where evidence permits;
  CAD quotation does not imply CAD economic exposure.
- **Sector/theme concentration:** **A diversified wrapper must not be mistaken for
  diversified economic exposure.** Detect concentration created or amplified by a
  fund in, for example, technology, semiconductors, AI-related businesses, financials,
  energy, emerging markets, specific countries or rates-sensitive assets. These are
  illustrative themes/factors, not hard-coded investment categories or fund rules.
- **Evidence and freshness:** holdings change over time. Retain source, relevant
  source authority/use status, effective/reporting date, capture time,
  completeness/scope, freshness, extraction/provenance and uncertainty. Distinguish
  reliable current-enough, partial, stale and unavailable look-through. Never present
  stale holdings as the exact current composition or fabricate missing precision.
- **Coverage and confidence:** known look-through exposure plus explicit unresolved
  residual exposure must account for the fund position. Do not silently renormalize
  partial evidence into 100% certainty. Fund-specific uncertainty must propagate into
  portfolio-level confidence: a fund at 20% portfolio weight with only 70% reliably
  classified holdings does not yield fully known portfolio exposure. Lower evidence
  quality reduces confidence in interpretation, without an invented numeric formula:
  **Be aggressive with economic risk, not information uncertainty.**
- **Multi-layer funds:** fund-of-funds may require bounded recursive look-through,
  safe handling of cycles and prevention of double counting. Unsupported structures
  must remain explicit; implementation design belongs to a later contract.
- **Portfolio use and stage relationships:** use the exposure map for concentration,
  hidden/shared exposure, sector, geography, currency and macro-driver risk,
  liquidity/context interpretation and portfolio-room analysis. Stage H uses it for
  portfolio context; Stage I handles stale/missing/provider-failed holdings data;
  Stage J establishes actual nominal ownership; Stage P presents direct/indirect
  exposure clearly to the owner.
- **Scope and sequence:** these are analytical capability requirements only. No
  investment thresholds, allocation/diversification/country/sector limits, overlap
  penalties or automatic sell rules are added; such policy requires later approved
  contracts. This work remains within Stage K's existing sequence. Final Architecture
  Cleanup & Dead-Code Retirement remains the final development chantier before
  Chromebook integration; look-through does not bypass that gate.

### Stage K1 — Dependency & Invalidation

Track analytical dependencies on evidence, derived facts, assumptions, model
versions and portfolio state. Upstream changes, staleness, corrections, lost
authority or contradictions must identify dependent results needing recomputation
or review; prior outputs must not silently retain authority. Implementation design
belongs in a later contract.
Cross-market evidence, capability-registry and FX changes must participate in these
dependency and invalidation semantics rather than leaving stale authority in place.
Reserve recommendations must also invalidate on material changes to benchmark ER,
cash-like carry, broker fees, instrument properties/eligibility, account capability,
portfolio state, Confidence or available capital.

### Stage K2 — Persistent Decision / Thesis Memory

Durably preserve inspectable prior analytical state: thesis, material evidence,
important assumptions, valuation / Expected Return, Quality / Durability /
Confidence, portfolio context, decision/recommendation state and relevant model/data
identities. This is project analytical memory, distinct from conversation memory
and the canonical project documents in section 7. It must precede Decision Delta:
a comparison requires a durably recorded account of what PAM previously believed.
Multiple listings or wrappers for one qualified economic exposure must not create
independent business theses merely because their symbols differ.
Future reserve memory should preserve amount, currency, instrument/form, reason,
mode, decision date, relevant ER comparison, Confidence, benchmark state,
broker/FX assumptions, estimated net carry and review/release state. Historical
decisions retain the mode and assumptions actually used.

### Stage L — Decision Delta & Attribution

Consume persistent prior decision/thesis state from Stage K2 to explain what
changed and why across evidence, Expected Return, Quality, Durability, Confidence,
Position State, Portfolio Room, allocation, concentration and provenance/context.
Distinguish fundamental, valuation, information-quality/evidence, assumption/model,
portfolio-context and policy/mode changes. No attribution weights are prescribed.
For reserve, explain creation, maintenance, partial/full release and changes caused
by contributions, individual opportunities, benchmark ER, carry, Confidence, FX,
fees, Portfolio Room or mode without rewriting prior history.

### Stage L1 — Outcome Evaluation

Evaluate what happened after prior analyses or recommendations using persistent
decision memory and Decision Delta, without rewriting history. Assess thesis
outcomes, Expected Return realization/error, avoided mistakes, missed opportunities,
lifecycle decisions, concentration consequences, benchmark-relative outcomes,
evidence-quality failures and calibration quality. Keep actual V1 portfolio,
hypothetical V2 shadow and benchmark histories separate; Stage M establishes the
performance integrity needed for these comparisons. Outcomes inform model assessment
and must not automatically rewrite investment rules.
Reserve evaluation should attribute carry, FX, fund costs, friction, benchmark
opportunity cost, foregone upside, avoided downside, duration and redeployment
quality against the policy and information available at decision time. Avoided
downside in hindsight does not by itself prove that a reserve decision was sound.

### Stage M — Benchmark & Performance Integrity

Preserve and modernize the existing portfolio-vs-VFV/S&P 500 capability, including
TWR, XIRR, external flows, total-return basis, CAD/FX coherence, benchmark continuity
and freshness, and value-added comparison.

During shadow, keep three histories strictly separate:

1. actual V1/production portfolio;
2. hypothetical V2 shadow portfolio;
3. VFV benchmark.

V2 shadow history must never contaminate real portfolio history. Benchmark results
remain validation/context evidence, not direct investment-rule authority.
Temporary reserve remains in total-portfolio denominators. Shadow performance must
retain reserve entries, carry, costs, FX, redeployment and the benchmark
counterfactual, with attribution separating security selection, benchmark fallback,
reserve carry, allocation timing, FX and friction.

### Stage N — Validation / Audit / Backtest Modernization

Before long-duration V2 shadow, preserve relevant V1 validation, performance,
benchmark, audit and maintenance capabilities or supersede them only with validated
V2-aware equivalents. Audit coverage must understand ER, Quality, Durability,
Confidence, Position Lifecycle, Portfolio Room, data authority/provenance,
Decision Delta and portfolio state.

Maintain the authority hierarchy:

- theoretical retrospective backtest = diagnostic;
- genuine PIT/walk-forward = stronger validation evidence;
- genuine accumulated forward V2 shadow = principal evidence of real V2 behavior;
- promotion/authority migration = separate explicit owner decision.

Any recurring integrity, audit, validation or benchmark task that can be executed
deterministically should be automated and condition-driven rather than becoming an
owner maintenance obligation. Preserve existing V1 maintenance/runtime protection;
future V2 shadow maintenance must use an isolated V2 path without weakening V1 guards.
`AUDIT_GUIDE.md` remains a V1-only workflow; governance scope notices do not add
V2 audit commands or authority.

Pre-shadow validation must include the cross-market invariance, reconciliation,
fail-closed and coverage-bias requirements in the cross-cutting program below.
It must also include the benchmark-first/reserve scenarios and anti-market-timing,
anti-churn and transition-path audits in the reserve program below.

### Stage N1 — Validation Firewall

Maintain explicit boundaries between research/development, retrospective validation,
genuine PIT/walk-forward evidence, forward shadow evidence, calibration and
production authority. Evidence in one domain must not silently grant authority in
another. Backtests remain diagnostic; forward shadow evidence is stronger, while
production authority remains a separate explicit owner decision.
Reserve research, retrospective diagnostics and shadow records grant no execution
or production authority.

### Stage N2 — Calibration Governance

Future calibration/tuning must be versioned, reproducible, auditable, evidence-backed
and separated from live decision generation. Protect against look-ahead leakage and
automatically learning from the model's own latest recommendations. Acceptance and
promotion require explicit review. Preserve V1's `PROPOSAL_ONLY` safety philosophy:
no self-modifying investment model or automatic threshold optimization from live
outcomes.
Reserve activation/release margins, persistence and hysteresis require a separate
reviewed investment-rule contract, validation, calibration and owner approval.

### Stage O — Mode Contract & Objective Personalization

Preserve and modernize the existing allocation-mode contract and all four modes.
Economic facts about a company should not change merely because the selected mode
changes. The mode changes the policy response to those facts.

| Mode | Broad objective |
| --- | --- |
| `balanced` | Growth with greater diversification/defensiveness. |
| `family-office` | Long-term compounding with stronger portfolio resilience awareness. |
| `rational-aggressive` | Higher willingness to concentrate when evidence justifies it. |
| `high-cagr` | Strongest long-term CAGR orientation and drawdown tolerance, while remaining strict on evidence uncertainty/permanent-loss risk. |

Future policy differences may include hurdle, uncertainty tolerance, diversification,
concentration, sizing, Portfolio Room, fallback behavior, stress emphasis and
lifecycle/action policy. Final thresholds require future contracts.

All modes remain benchmark-first and reserve-last-resort. With identical economic
facts, conceptual reserve propensity is ordered:

```text
balanced >= family-office >= rational-aggressive >= high-cagr
```

This is a policy ordering, not a required allocation pattern; zero reserve in all
four modes is valid. Cross-mode audit should preserve these conceptual policy
orderings without requiring different results on every run:

```text
DEFENSIVENESS:           balanced >= family-office >= rational-aggressive >= high-cagr
RESERVE PROPENSITY:      balanced >= family-office >= rational-aggressive >= high-cagr
CONCENTRATION TOLERANCE: balanced <= family-office <= rational-aggressive <= high-cagr
```

`balanced` may tolerate temporary undeployed
capital more readily under material uncertainty, stretched concentration or
marginal deployment economics. `family-office` may give more weight to resilience,
liquidity optionality and permanent-impairment avoidance without creating a routine
strategic cash allocation. `rational-aggressive` generally prefers qualified
opportunities and then the benchmark, while still refusing investment at any price.
Reserve is most exceptional in `high-cagr`, which remains especially resistant to
crisis-based cash flight and drawdown timing while failing closed under information
uncertainty.

Future scheduled/manual Telegram analysis initiation should let the owner select
among all four modes before capital confirmation, instead of being implicitly
locked to `high-cagr`. This is interface/orchestration work, not an investment-rule
change; no Telegram implementation is part of this documentation update.

### Stage O1 — Recommendation / Execution Separation

PAM remains research intelligence + portfolio intelligence. Recommendation state
and brokerage execution must remain separate: a model conclusion is not an
execution instruction. Automatic brokerage trading remains out of scope unless
separately and explicitly authorized in the future.
Reserve recommendation is analytical state only: no broker order, reserve-instrument
purchase, cash conversion or FX transaction follows automatically.

### Stage O2 — Monitoring / Observability

Make provider/source failures, stale evidence, unsupported variants, degraded
pipelines, unresolved conflicts, invalidated dependencies, failed scheduled runs,
model/input version drift and shadow/runtime health visible across V2. Distinguish
operational/data failures from investment signals. Prefer automated deterministic
monitoring over routine owner maintenance; build on Stage I's resilience behavior.
Future reserve observability should expose amount, weight, currency, instrument/form,
age, reason, mode, estimated carry, data and broker-cost freshness, redeployable
amount, review/release state, activation frequency, duration and FX round trips.

### Stage O3 — Commercial Data Governance

Before commercialization, establish source/provider identity, permitted use,
redistribution/display rights where relevant, retention, provenance, licensing
constraints, attribution, geographic/product limitations, replacement/deprecation
and paid-vs-free dependency risk. Keep factual authority separate from legal or
permitted-use authority. PR4D2C and existing source contracts do not universally
license Nasdaq or other provider data.
The Global/Market Capability Registry must represent permitted-use and commercial-use
status dimensionally; registry membership must never grant evidence authority.

### Stage P — Compact Report Information Architecture & UX

The compact HTML report is the owner's primary post-analysis human interface.

> Compact means consolidated, not information-poor.

Preserve useful analytical content; shortening reading time is not a reason to
reduce that content. Improve organization, hierarchy, navigation, visual clarity,
intuitiveness and grouping of related information once the analytical V2 layers
are stable enough to design against their real information architecture.

Coherently present, when available: analysis/mode context; portfolio and benchmark
performance; positions; ER / Quality / Durability / Confidence; Position Lifecycle;
allocation reasoning; changes since the previous run; risks/stress; watchlist/discovery;
data reliability/provenance; and model/audit health. No report redesign occurs now.
Future compact reporting should reconcile new contributions, redeployable reserve
and other settled deployable cash into current available capital, while separating
strategic investments, temporary reserve, transactional cash and unsettled or
unavailable cash. Explain why reserve remains or what changed when it releases.

### Stage Q — Any additional future V2 chantiers

New V2 development must precede final cleanup. Adding a chantier automatically
moves that cleanup after it; the gate cannot be bypassed by later additions.

### Stage R — FINAL Architecture Cleanup & Dead-Code Retirement

Permanent sequencing invariant: final cleanup always occurs after every V2
development chantier, including any added in the future, and before V2 integration/
automation on the Chromebook. Inventory obsolete, dead or duplicated components
and prove whether they are still used before removing genuinely obsolete code or
functionality.

Review imports/references, CLI paths, tests, reports/artifacts, runners/systemd,
mode-specific paths, indirect dependencies, historical/shadow needs and compatibility
requirements. Classify candidates as `ACTIVE`, `UNCERTAIN — KEEP`,
`SUPERSEDED BUT STILL REQUIRED` or `SAFE TO RETIRE`.

> No code or feature should be removed merely because it looks old. If no genuinely
> dead component exists, no deletion is required.

No cleanup is performed in this documentation PR.

### Stage S — Final regression / integrity / shadow-readiness review

Before Chromebook integration or long-duration V2 shadow, require evidence that:

- the approved V2 feature set is complete within its declared supported scope and
  major analytical/core architecture is no longer awaiting construction;
- Real Fact Admission works for every declared supported route;
- the initial cross-market/international proof defined below exists;
- unsupported markets and cases are explicit and fail closed;
- dependency/invalidation behavior is coherent and persistent Decision / Thesis
  Memory exists;
- monitoring is adequate and actual V1, hypothetical V2 shadow and benchmark
  performance histories remain correctly separated;
- Portfolio State, cross-listing, wrapper and currency semantics are coherent for
  supported instruments;
- validation boundaries are intact, no V1 authority has silently migrated and no
  V2 path has positive-capital decision authority;
- runtime isolation is preserved; and
- final architecture cleanup and the full regression/integrity review have passed.

Shadow-readiness is not production readiness and grants no investment authority.

### Stage T — V2 isolated Chromebook integration / automation

Only after final cleanup and readiness review, integrate a separately approved,
isolated V2 shadow path. Preserve V1 runtime guards and production authority.

### Stage U — Long-duration shadow validation

Run V2 beside V1 with zero decision authority. This stage is intended to maximize
the value of accumulated forward evidence from a largely stable V2 architecture;
major structural feature development should not normally occur during it.

Track:

- stability;
- evidence failures;
- selection differences;
- concentration;
- turnover;
- drawdowns;
- missed/avoided errors;
- benchmark behavior;
- quality of explanations;
- operational reliability.

Bug fixes, security fixes, source-compatibility repairs, operational-reliability
fixes and bounded extensions using already-reviewed contracts may still occur.
Major new analytical pillars, identity/admission semantics, portfolio-state
semantics, decision-memory semantics, cross-market core contracts or
recommendation/execution semantics should not normally be introduced during shadow.

If a material semantic, model or capability change becomes necessary, preserve the
prior evidence, version the change, mark a clearly distinguishable validation/shadow
epoch where appropriate, and never silently pool pre-change and post-change evidence
as one homogeneous forward record. Do not rewrite history.

### Stage V — Explicit authority review

Only after substantial forward evidence:

- compare V1/V2;
- audit failure modes;
- decide whether to retain V1, adopt parts of V2 or promote V2 more broadly.

No automatic promotion.

---

### Cross-cutting program — Benchmark-First Fallback & Exceptional Liquidity Reserve

This program is a pre-shadow V2 completeness requirement whose executable
implementation remains pending and requires separately reviewed contracts. It
changes no current investment behavior, threshold, instrument selection, model
version, V1 authority or execution authority. The existing rough individual-security
hurdle and VFV philosophy remain unchanged.

#### Capital-destination hierarchy and scope

Canonical hierarchy:

```text
QUALIFIED INDIVIDUAL OPPORTUNITIES
        ↓
BROAD MARKET BENCHMARK
        ↓
ONLY THEN, EXCEPTIONAL TEMPORARY LIQUIDITY RESERVE
```

The benchmark is the normal fallback when no individual security clears its
required hurdle. Reserve is not a third equal tactical alternative and is not a
market-timing response. Difficult markets, recessions, volatility, drawdowns,
negative headlines or a crisis classification do not automatically justify it.
Reserve may become appropriate only when both individual deployment and benchmark
deployment fail a future reviewed net-economics/confidence policy after considering
conservative ER, cash-like carry, information uncertainty, permanent-loss risk,
Portfolio Room and the full executable cost path. No activation number is approved
here.

#### Deployable capital and reserve lifecycle

Every future analysis should reconsider the full actually settled and deployable
pool, subject to account, settlement, currency, broker-eligibility and operational
constraints:

```text
new contribution
+ free settled cash
+ releasable temporary reserve
+ relevant distributions/proceeds
= current deployable capital
```

Reserve is re-evaluated for maintenance, partial release or full release each run.
It is not permanently removed from the opportunity set. Transitions from existing
investments remain governed by Position Lifecycle; transitions from reserve back
to investment may be reconsidered each analysis.
For example, a settled $500 temporary reserve plus a new settled $330 contribution
means reconsidering up to $830, subject to the actual account and settlement state.

#### Comparable economics, broker adapter and currencies

Future capital-destination analysis must separate underlying economic ER from
executable net instrument ER. Compare the likely full transition path, including
reserve carry, fund expense, bid-ask spread, slippage, commission, FX conversion
and spread, and eventual redeployment friction. Avoid unnecessary FX round trips.
Distinguish incremental transaction costs, fixed recurring account costs,
sunk/shared platform costs, fund-level recurring costs and FX-path costs; a fixed
fee already incurred for another reason must not be charged blindly to every
transaction.

Representative paths include CAD contribution → CAD reserve → Canadian security;
CAD contribution → CAD reserve → FX → U.S. security; CAD contribution → FX → USD
reserve → U.S. security; and USD proceeds → USD reserve → U.S. security. The likely
next deployment currency can change which temporary route has better net economics.

Preserve portfolio base, contribution, reserve/cash, quote, transaction, reporting
and eventual deployment currencies, plus economic FX exposure. Nominal yield or
quote currency alone does not determine superiority or economic risk. No reserve
instrument is universally risk-free; duration, credit/sovereign, currency,
liquidity, wrapper and tracking/friction risks remain explicit.

The core is broker-, jurisdiction-, source- and currency-neutral. The owner's
initial execution context is Wealthsimple self-directed: provider/account
capabilities, eligible listed Canadian and U.S. securities, currency paths and
costs affect future implementation feasibility and executable net economics only.
They must be dated, versioned, sourced and revalidated as adapter metadata, never
constitutional constants. Do not assume direct individual Treasury-bill access.
Initial routes may include settled CAD/USD cash or later-qualified eligible listed
cash-like/short-government-bill funds; this roadmap selects no product or ticker.

Current noncanonical context observed **2026-09-26** from Wealthsimple's official
[Trade fee schedule](https://www.wealthsimple.com/en-ca/legal/fees/trade) and
[USD-account documentation](https://help.wealthsimple.com/hc/en-ca/articles/4418893583515-Using-USD-stock-trading-accounts): listed Canadian and U.S. securities currently
have $0 commission; CAD-account trades in U.S.-listed securities can incur currency
conversion; and an applicable USD account can hold USD and avoid a new conversion
on each U.S.-security trade. These provider facts are dated, subject to change and
must be revalidated before use.

A future broker-cost/capability contract may include provider, account type,
account/cash/contribution/reserve/trade/quote/eventual-deployment currencies,
commission, FX fee and spread, fund expense, bid-ask spread, slippage, incremental
fixed/subscription cost, settlement, security/fractional eligibility, minimums,
effective date, source/provenance and freshness. This roadmap defines no schema.

#### Facts, mode policy and anti-churn

For identical market/account state, all modes consume the same company Quality and
Durability, underlying and benchmark ER, cash-like carry, prices, currencies,
broker/FX/fund/trading costs, eligibility, evidence authority, freshness and
provenance. Modes change policy response, not economics. The Stage O ordering
governs reserve propensity but never forces visibly different allocations.

Because benchmark ER is uncertain, future activation and release require a
meaningful economic margin, persistence, hysteresis and confidence-aware safeguards.
Tiny or model-noisy differences must not cause frequent reserve/benchmark switching.
Exact margins and persistence periods are deferred to an owner-approved contract.

#### Validation, reporting and shadow evidence

Before shadow readiness, validate at least:

1. strong individual opportunity;
2. no qualifying individual but attractive benchmark;
3. marginal benchmark versus reserve;
4. severe drawdown with improved prospective benchmark ER;
5. insufficient evidence authority for new deployment;
6. high cash-like carry with weak benchmark economics;
7. large FX friction;
8. prior reserve plus new contribution;
9. mode switching;
10. CAD-reserve versus USD-reserve paths;
11. stale broker fees;
12. stale cash-like yield;
13. reserve instrument becoming ineligible;
14. frequent reserve activation;
15. reserve↔benchmark oscillation;
16. unnecessary CAD↔USD round trips;
17. no-stock-but-benchmark-attractive;
18. crisis-but-benchmark-attractive;
19. different modes under identical economic facts; and
20. existing positions remaining under lifecycle rather than cash-flight logic.

Frequent activation, excessive duration, repeated FX round trips or rapid switching
are audit signals for hidden timing, noisy ER comparisons, cost-attribution defects
or overly defensive mode behavior. Shadow operation retains zero authority while
recording hypothetical reserve decisions, carry, FX, fund/transaction costs,
redeployment and the benchmark counterfactual. A material later semantic change
starts a distinct version/shadow epoch rather than pooling incompatible evidence.

---

### Cross-cutting program — Global Universe & Cross-Market Admission Architecture

Global expansion must preserve one source-neutral analytical architecture:

```text
GLOBAL ECONOMIC CONTRACTS
        ↑
jurisdiction/source adapters
        ↓
SAME ECONOMIC FACT MODEL
        ↓
ER / Quality / Durability / Confidence
        ↓
GLOBAL OPPORTUNITY SET
        ↓
PORTFOLIO ROOM
```

Jurisdiction-specific source adapters may differ, but downstream economic contracts
must remain source-, provider-, jurisdiction-, currency-, identifier- and
exchange-neutral where economically appropriate. Do not create separate country
analyzers as the core architecture.

#### Global economic identity

The intended conceptual identity graph is:

```text
ECONOMIC ISSUER / ENTITY
→ REPORTING SUBJECT
→ SECURITY / SHARE CLASS
→ LISTING and/or WRAPPER
→ executable/observable instrument
```

Ticker is a property of a listing, not permanent economic identity. CIK is an
SEC-route identifier, not PAM's global entity identity. LEI, FIGI, ISIN, CIK and
other external identifiers are evidence-backed external claims or anchors, not
automatic economic qualification. Future contracts may establish stable
PAM-internal economic IDs; this roadmap does not prescribe their implementation.

> **One economic thesis per economic security/issuer context, not per ticker.**

Multiple listings or wrappers representing the same economic exposure must not
become independent business theses merely because they use different symbols.
Instrument-level price, quote currency, liquidity, transaction friction, wrapper
ratio, fees and venue may still differ.

#### Global/Market Capability Registry

Pre-shadow V2 requires a versioned, dimensional Global/Market Capability Registry.
It should represent, as applicable, jurisdiction, regulator/source route, listing
venues, identity and filing routes, supported accounting bases, current and
historical authority, corporate-actions and listing-continuity support, pricing,
FX, instrument types, legal/permitted-use status and commercial-use status.

Do not collapse these dimensions into one synthetic coverage score. Capabilities
must fail closed through explicit states conceptually such as `SUPPORTED`, `PARTIAL`,
`UNSUPPORTED`, `UNAVAILABLE`, `REVIEW_REQUIRED` and `CONFLICTED`. Registry
membership never grants evidence authority. Independent supported capabilities may
continue to serve research when another dimension fails, but every output depending
on the failed dimension remains unavailable.

#### Global discovery and admission funnel

```text
DISCOVERY
→ OBSERVABLE
→ QUALIFICATION CANDIDATE / QUEUE
→ V2 ADMISSIBLE
```

Cheap discovery may span a much larger universe than deep evidence qualification.
Market-data availability, or a provider returning a ticker or price, never grants
admission. Unknown or incomplete international evidence should reduce capability
availability, Confidence or Admission as applicable, not automatically reduce a
company's economic Quality. Discovery may progress through `RESEARCH_CANDIDATE`,
`PARTIAL_ANALYSIS` and `FULL_ANALYSIS_ELIGIBLE` before strict admission; these
states are not necessarily irreversible. No geographic quotas are introduced.

#### Initial international capability before shadow

Complete global-market coverage is **not** a prerequisite for shadow. Functional
international V2 capability **is** part of the pre-shadow V2 supported scope. Before
final shadow-readiness, subject to separate implementation contracts and evidence
review, the architecture must demonstrate real cross-market capability through:

1. the fully qualified initial US/SEC real-admission route;
2. at least one real foreign-issuer / IFRS route, with SEC foreign private issuers,
   Form 20-F and IFRS as the preferred high-reuse candidate unless later evidence
   establishes a better route;
3. at least one real non-SEC jurisdiction/source adapter selected later using source
   quality, licensing/permitted use, historical coverage, reliability and
   implementation cost—this roadmap does not select ESEF, OpenDART or another route;
4. evidence-backed wrapper/entitlement capability for the supported ADR/ADS scope
   required by the approved international universe;
5. multi-currency portfolio/FX architecture sufficient for explicitly supported
   international instruments and currencies;
6. cross-market/source-neutral invariance validation; and
7. a Global Coverage Bias Audit.

This proof establishes that the architecture is actually source-neutral. It does
not require Europe, Japan, Korea, Canada and every other market before shadow.
Additional markets may be added later through the same reviewed contracts.
A material expansion of the supported market universe during Stage U must follow
the shadow-epoch/versioning rules above and must not be silently pooled with prior
forward evidence as one unchanged validation record.

#### Currency and geography semantics

Future contracts must distinguish reporting currency, economic-fact currency,
quote currency, transaction currency, portfolio base currency and economic FX
exposure. Quote currency must be evidence-backed for V2 authority; ticker-suffix
inference may not become authoritative evidence.

They must also distinguish incorporation/domicile, reporting jurisdiction, listing
geography, revenue/economic geography, asset geography and regulatory geography.
Listing geography is not economic geography.
Temporary highly liquid capital-preservation destinations must likewise remain
jurisdiction-neutral and instrument-aware, with explicit currency, issuer/credit,
duration, liquidity, wrapper, cost and evidence properties rather than defining a
global “safe asset” as one country's bill.

#### Cross-market validation

Pre-shadow validation must cover:

- cross-source economic-fact equivalence;
- listing invariance;
- wrapper/ADR-underlying reconciliation;
- multi-currency reconciliation;
- a no-US-identifier core-contract test;
- capability-registry fail-closed behavior;
- provider/source-outage behavior; and
- the Global Coverage Bias Audit.

Equivalent qualified economic facts from different adapters must feed the same
downstream economic contracts. Different listings of the same economic security
must not change business Quality, Durability or the underlying economic Expected
Return assumptions merely because the venue or symbol changed. Instrument-level
Expected Return may differ only when evidence-backed instrument properties such as
price, wrapper entitlement, fees, trading friction or currency conversion
legitimately change executable economics. Quote currency or listing venue alone
does not alter business economics. A source outage may reduce availability,
Confidence or Admission, but must not become `THESIS_BROKEN`, `SELL` or degraded
economic Quality without economic evidence.

### Longer-term direction — Research product surface

Potential features:

- company research pages;
- comparable-company views;
- screener;
- watchlists;
- evidence explorer;
- thesis timeline;
- change alerts;
- portfolio dashboard;
- generated research reports;
- API / B2B surface.

Full commercial UI and complete global coverage are not pre-shadow gates. Any V2
development included before integration remains subject to the final-cleanup invariant.

---

## 10. Product commercialization path

Preferred first commercialization:

### Phase 1 — research product

- searchable company analysis;
- Expected Return;
- Quality;
- Durability;
- Confidence;
- risk/thesis;
- evidence/provenance;
- comparisons;
- watchlists.

### Phase 2 — portfolio intelligence

- portfolio import/tracking;
- concentration;
- exposures;
- thesis health;
- valuation / ER context;
- alerts;
- analytical history.

### Phase 3 — premium / B2B

Possible:

- premium research;
- richer screeners;
- reports;
- API;
- team workflows;
- analyst/adviser tooling.

Personalized regulated advice is a separate strategic decision and should not be assumed.

---

## 11. Validation milestones before commercialization

Before PAM is presented as a serious research product, target:

- stable source contracts;
- legally usable source set;
- explicit provenance;
- clear failure states;
- secure account/data architecture;
- reproducible outputs;
- monitoring;
- privacy/security controls;
- product terms and disclosures;
- meaningful shadow evidence;
- reliable update cadence.

The exact commercial launch threshold should be a future explicit product decision.

---

## 12. Things deliberately NOT on the immediate roadmap

Unless explicitly revisited:

- automatic brokerage trading;
- autonomous personalized financial advice;
- self-modifying investment rules;
- Markowitz/covariance optimizer;
- opaque machine-learning stock picker with no explanation;
- fragile full DCF as the default ER engine;
- paid-data dependency before the free/official architecture is understood;
- any paid financial-data subscription becoming mandatory for supported core
  operation;
- broad global ingestion without evidence/licensing qualification.

---

## 13. Memory-document update rule

After each meaningful merged PR:

1. verify whether `PAM_ROADMAP.md` needs an update;
2. update the specific feature contract;
3. update `DECISIONS.md` only for meaningful design decisions;
4. update `PAM_PROJECT_CONSTITUTION.md` only for foundational vision/governance changes.

Do not allow all four documents to repeat the same implementation details.

---

## 14. Next session handoff

PR #84 merged and PR5E is complete. The explicitly supported bounded first CURRENT
nonpayer route now runs from PR5D2 through PR5E final admission to real PR4B1 facts,
PR4B1 assumption construction and PR4A Expected Return. The route remains
publication-unknown/capture-bound, route-local, bounded in corporate-action coverage,
nonpayer-only and without `HISTORICAL_AS_OF`, PIT, production, recommendation,
allocation, execution or promotion authority.

Stage A — Real Fact Admission is complete only for that bounded route; broader
identity, international, PIT, data and licensing limitations remain. Stage B —
Expected Return completion is active and incomplete. PR #86 completed the first
bounded VFV CURRENT evidence foundation, and PR #88 completed the reviewed standalone
VFV forward Expected Return methodology, CEO-approved numerical policy and canonical
research diagnostic. PR #90 completed the qualified VFV USD-exposure / dated
materially-unhedged prerequisite and the bounded same-label company-vs-VFV Expected
Return comparator under constant FX, including the comparator-owned company problem
identity-v2 correction. PR #92 completed the source-neutral current nominal
`CASH_LIKE_CURRENT_CARRY` Slice A foundation for the first bounded
settled-cash-balance profile. Current cash carry is not seven-year cash Expected
Return and is not an opportunity-cost comparison. PR #94 completed the source-neutral
`EXECUTABLE_ENTRY_EVIDENCE` B1 foundation and closed failure states for one bounded
CURRENT/capture-bound context, including independent partial facts, exact Decimal
commission and executable-quote semantics, `POST_TRADE_REGULAR_WAY / T_PLUS_1`,
same-currency `FX_NOT_REQUIRED_SAME_CURRENCY`, deterministic identities and closed
precedence. Synthetic `AVAILABLE` fixtures prove mechanics only.

The immediate next direction belongs to Data & Evidence for qualification of a real
executable-entry evidence route where supportable. No qualified real executable
bid/ask route, provider/broker adapter, live owner-specific route or positive numeric
executable route is established; informational/current-observed quotes do not gain
executable authority. B2 numeric seven-year entry-execution-net transformation
remains unauthorized and blocked until real qualified executable quote and execution-
cost evidence sufficiently supports its transformation boundary. This Governance
Sync starts neither real-route implementation nor B2.

---

*Roadmap state updated on 2026-10-04 through canonical PR #94. Governance Reform
Phase 1, Governance Cleanup / Migration, role Projects/employees configuration and
PR5E are complete. Stage B — Expected Return completion is the active technical
frontier; its VFV CURRENT evidence foundation, standalone forward Expected Return,
qualified FX/hedge prerequisite, bounded company-vs-VFV comparator and source-neutral
cash-like current-carry Slice A and executable-entry evidence B1 milestones are
complete, while Stage B remains incomplete. Data & Evidence qualification of a real
executable-entry evidence route is next; B2 numeric entry-execution-net transformation
remains unsupported and unauthorized until real qualified executable quote and
execution-cost evidence exists.
Later architecture stages and shadow-readiness gates remain requirements only.
The reviewed PR5D2 Expected Return assumption policies are now pinned, but no
investment-rule, model-rule, V1 or production-authority change is authorized
here.*
