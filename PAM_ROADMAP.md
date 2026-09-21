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

Verified post-PR4D2B state after merged PR #45 (2026-09-21):

Merge commit:

`f892a1e693472b840b1e93274e2a583b270f6c6f`

Tree:

`83a89549d98e337852d3985dcc720fd932bca82e`

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
- `EXPECTED_RETURN_PR*.md` — feature contracts;
- `README.md` — operational/user documentation.

---

## 8. Current technical frontier — remaining real admission

### PR4D1 — CURRENT real-authority foundation ✅

Merged PR #42 establishes acquisition provenance, capture-bound CURRENT observed
availability and CURRENT snapshot scope through the controlled LIVE SEC Companyfacts
route. Its source-route registry grants no provider-wide trust. Exact publication
remains unknown; there is no historical-as-of authority or freshness beyond capture.

Real identity, share-basis and reporting-subject qualifications remain unresolved.
There is no final economic admission or Decimal→float model adaptation. Factual
authority remains separate from licensing/use authority. The detailed contract is
`EXPECTED_RETURN_PR4D1.md`; the C3→C6 synthetic chain is unchanged.

### PR4D2A — Controlled SEC complete-submission filing capture ✅

Merged PR #44 adds immutable exact-byte filing evidence and controlled acquisition.
It grants no economic identity qualification or D1 authority upgrade.

### PR4D2B — Controlled SEC Submissions inventory ✅

Merged PR #45 adds controlled SEC Submissions root/history acquisition, immutable
parent-linked receipts, deterministic offline replay and captured-reference closure.
The detailed implementation contract is `EXPECTED_RETURN_PR4D2B.md`.

> Captured-reference closure is not filing-history completeness, economic-event
> completeness, historical authority, property-4 qualification, or coverage through
> the D1 CURRENT boundary.

Real property 4 and obligations 5–7 remain unresolved. D2B does not advance economic
admission authority. Do not reinterpret synthetic qualifications as real authority
or weaken existing blockers. The next evidence/temporal-coverage and real-qualification
contract requires separate review.

---

## 9. Expected future V2 sequence

The exact PR numbering may change. The conceptual sequence is more important.
The following are approved V2 completeness requirements, not implemented behavior
or authorization to implement them in this documentation PR. Future contracts must
define supported cases and validation without inventing thresholds here.

```text
Real Fact Admission → Expected Return completion → Quality → Durability → Confidence
→ Position Lifecycle / Thesis Deterioration → Stress / Crisis Resilience
→ Portfolio Room / Portfolio Intelligence → Data & Operational Resilience
→ Portfolio State Integrity → Portfolio Risk / Shared Exposure
→ Decision Delta & Attribution → Benchmark & Performance Integrity
→ Validation/Audit/Backtest Modernization → Mode Contract & Objective Personalization
→ Compact Report Information Architecture & UX → any additional future V2 chantiers
→ FINAL Architecture Cleanup & Dead-Code Retirement
→ final regression/integrity/shadow-readiness review
→ V2 isolated Chromebook integration/automation → long-duration shadow validation
→ explicit authority review
```

Global source expansion may proceed in parallel where appropriate. Neither complete
global-market coverage nor the full commercial UI is a prerequisite for shadow.

### Stage A — Real fact admission

- CURRENT acquisition authority foundation completed by PR4D1; remaining admission work;
- source registry / permitted-use metadata;
- real identity authorities;
- real corporate-action/share-basis evidence;
- reporting-subject evidence;
- publication / availability qualification;
- real admission join;
- real-capable adapter into Expected Return facts.

### Stage B — Expected Return completion

- robust current forward ER inputs;
- bear/base/bull assumptions;
- VFV forward ER comparator;
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

### Stage G — Stress / Crisis Resilience

Assess thesis resilience under stress and crisis, with explicit evidence and
uncertainty. This layer concerns business/portfolio resilience, not macro timing.

### Stage H — Portfolio Room / Portfolio Intelligence

Build the analytical layer for positions, room, exposures, concentration,
expected-return distribution, thesis state, watchlists, change history, alerts
and comparative opportunity context.

### Stage I — Data & Operational Resilience

Explicitly handle stale data, source/provider failure, partial or contradictory
evidence, failed runs, degraded mode and freshness/source-health visibility.

> A data outage or evidence failure must not silently become an investment signal.

### Stage J — Portfolio State Integrity

Reconcile economic ownership through transactions, cash, dividends, splits,
mergers, spin-offs, security/class/ticker/listing changes and FX where relevant.
This is a completeness requirement, not a new ledger design.

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

### Stage L — Decision Delta & Attribution

Explain what changed between analyses and why: evidence, Expected Return, Quality,
Durability, Confidence, Position State, Portfolio Room, allocation, concentration
and provenance/context. Distinguish fundamental change, valuation change,
information-quality change and portfolio-context change.

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
`AUDIT_GUIDE.md` stays unchanged until actual V2 audit commands/contracts exist.

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

Future scheduled/manual Telegram analysis initiation should let the owner select
among all four modes before capital confirmation, instead of being implicitly
locked to `high-cagr`. This is interface/orchestration work, not an investment-rule
change; no Telegram implementation is part of this documentation update.

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

Verify the completed architecture, preserved capabilities, evidence boundaries and
isolated operational readiness before integration. This gate grants no production
or investment authority.

### Stage T — V2 isolated Chromebook integration / automation

Only after final cleanup and readiness review, integrate a separately approved,
isolated V2 shadow path. Preserve V1 runtime guards and production authority.

### Stage U — Long-duration shadow validation

Run V2 beside V1 with zero decision authority.

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

### Stage V — Explicit authority review

Only after substantial forward evidence:

- compare V1/V2;
- audit failure modes;
- decide whether to retain V1, adopt parts of V2 or promote V2 more broadly.

No automatic promotion.

---

### Parallel direction — Global universe

Expand progressively from the initial SEC/US route.

Conceptual source expansion may include:

- OpenFIGI;
- GLEIF;
- official exchange/listing directories;
- ESEF / filings.xbrl.org;
- EDINET;
- OpenDART;
- Canadian sources where legally usable;
- other official jurisdictions.

Each market may use different source adapters but should map to common economic contracts.

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

After merged PR4D2B, for the remaining real-admission frontier:

1. verify the current V2 remote head;
2. read the constitution and this roadmap;
3. read `EXPECTED_RETURN_PR4D1.md`, `EXPECTED_RETURN_PR4D2A.md` and `EXPECTED_RETURN_PR4D2B.md`;
4. obtain separate review of the next evidence/temporal-coverage and real-qualification
   contract; property 4 and obligations 5–7 remain unresolved;
5. preserve V1 unchanged.

---

*Roadmap state updated on 2026-09-21 to verified post-PR #45 / PR4D2B.
ETF/fund look-through is recorded under Stage K as a future V2 requirement only.
No implementation, runtime, investment-rule or authority change is authorized here.*
