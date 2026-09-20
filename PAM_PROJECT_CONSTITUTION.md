# PAM_PROJECT_CONSTITUTION.md

> Canonical project constitution for PAM / `investment_automation`.
>
> Purpose: allow a new human or AI agent to understand what PAM is, why it exists,
> what is already decided, what must not drift, and what the project is intended to become.
>
> This document is intentionally slow-changing. It should change only when the owner
> explicitly changes project vision, investment philosophy, governance, or the target product.

---

## 1. Project identity

**Project:** PAM
**Repository:** `PineAllocationMedia/investment_automation`

PAM began as a personal investment-allocation automation system and is evolving into
a broader financial research and portfolio-intelligence platform.

The long-term ambition is not merely to produce a buy/sell output. PAM should become
a reliable, explainable and auditable research engine that can ingest financial
evidence, qualify it, analyze securities, compare opportunities and help a user
understand and manage a portfolio.

### Canonical product vision

**PAM = financial research intelligence + portfolio intelligence.**

The commercial product should primarily help users:

- research companies and securities;
- understand expected return, quality, durability, confidence and risk;
- compare opportunities;
- monitor thesis changes and fundamental changes;
- manage watchlists and portfolios analytically;
- understand concentration and exposures;
- retain a traceable history of evidence and analysis;
- receive useful alerts and structured research outputs.

The **user keeps the final investment decision**.

PAM should not be designed primarily as a personalized robo-adviser or a system that
commercially tells each user exactly what to buy or sell. The internal/private model
may still generate recommendations for the owner, but commercialization should first
expose the research and portfolio-intelligence layers.

A useful product analogy is:

> a more automated, explainable and evidence-aware research/portfolio platform,
> not merely a recommendation bot.

---

## 2. Why PAM should exist

PAM should reduce the gap between:

1. raw financial data;
2. trustworthy economic evidence;
3. an understandable investment thesis;
4. portfolio context;
5. a disciplined human decision.

The system should eventually be able to answer questions such as:

- What is this business economically?
- How reliable are the facts supporting the analysis?
- Is the business high quality and durable?
- What is a conservative forward expected return?
- What assumptions matter most?
- What has changed since the last analysis?
- How does this opportunity compare with the market benchmark and other candidates?
- What risks or concentrations already exist in the portfolio?
- What information is missing or uncertain?
- Why did PAM reach this conclusion?

The valuable asset is therefore not only a model score. It is the **research and
decision infrastructure** that makes the score explainable, reproducible and auditable.

---

## 3. Core V2 investment philosophy

V2 is a challenger architecture designed around:

> **High-CAGR Quality Compounder — Asymmetric**

The objective is high long-term compound growth while avoiding unnecessary
permanent-loss risk.

The core analytical pillars are:

1. **QUALITY**
2. **DURABILITY**
3. **EXPECTED RETURN**
4. **CONFIDENCE**
5. **PORTFOLIO ROOM**

A useful conceptual expression is:

> marginal attractiveness ≈ expected-return advantage versus VFV × confidence × quality × room

This is a conceptual guide, not permission to introduce an opaque single formula.

### Investment principles already chosen

- Long-term CAGR matters more than short-term noise.
- Temporary drawdowns around 35–45% can be tolerated when the thesis remains intact.
- Permanent-loss risk matters more than volatility for its own sake.
- VFV acts as the market opportunity-cost benchmark and safety core.
- VFV target is roughly 20%, with a conceptual floor around 15% unless explicitly revised.
- Equities will usually dominate the portfolio, often around 70–85%.
- A natural individual-stock count is approximately 8–20.
- An intended exceptional initial stock maximum is around 20%.
- A position that exceeds a maximum through appreciation is reviewed / stopped from
  receiving new capital rather than automatically sold.
- Smaller companies can be admitted when evidence quality is sufficient.
- For less-established companies, initial sizing should be smaller and required
  expected-return advantage higher.
- A rough hurdle for established companies is VFV + ~2 percentage points of expected return.
- Less-established companies may require roughly +3–4 percentage points.
- Cash/T-bill target is normally 0; reserve cash is exceptional, not the default.
- Selling should remain rare and thesis-driven.
- High valuation is not by itself a sell reason if conservative forward expected return remains adequate.
- Economic portfolio construction comes before tax-location optimization.
- Missing or uncertain data should reduce confidence and/or allocation rather than be silently invented.

Canonical maxim:

> **Be aggressive with economic risk, not information uncertainty.**

### Position lifecycle doctrine

Distinguish normal volatility, temporary deterioration, information uncertainty,
material fundamental deterioration and structural thesis break. Price decline is
not thesis deterioration; crisis is not an automatic sell signal. Selling remains
rare and thesis-driven, and deterioration states may recover when evidence genuinely
improves. Review thesis resilience under stress rather than attempting macro timing.
Trim/exit review considers Expected Return, Quality, Durability, Confidence,
Portfolio Room, concentration and shared economic exposure.

### Four-mode architecture

Preserve and modernize `balanced`, `family-office`, `rational-aggressive` and
`high-cagr`. Economic facts about a company should not change merely because the
selected mode changes; the mode changes the policy response to those facts.
Mode objectives and future policy contracts belong in the roadmap and specific
contracts, without relaxing evidence integrity.

---

## 4. Expected Return philosophy

The intended Expected Return horizon is approximately 5–10 years.

Preferred decomposition:

- normalized per-share earnings / FCF / owner-earnings growth;
- distributions;
- plausible valuation normalization;
- bear / base / bull scenarios;
- explicit confidence.

Do not default to:

- fragile point-estimate DCFs;
- opaque Monte Carlo;
- Markowitz/covariance optimization;
- complex machinery that cannot be audited.

The benchmark VFV should eventually receive an analogous forward-looking expected-return
treatment rather than relying only on historical CAGR.

---

## 5. Data and evidence philosophy

V2 is being built around the following pipeline:

```text
SOURCE
  ↓
IMMUTABLE CAPTURE
  ↓
EXTRACTION
  ↓
QUALIFICATION
  ↓
ECONOMIC FACTS
  ↓
EXPECTED RETURN
  ↓
QUALITY / DURABILITY / CONFIDENCE
  ↓
PORTFOLIO ROOM
  ↓
RESEARCH / PORTFOLIO OUTPUT
```

The purpose of this structure is to separate:

- what a source said;
- what was captured;
- what was extracted;
- what has been qualified;
- what is economically comparable;
- what is an analytical assumption;
- what is a model conclusion.

### Required engineering properties

- provenance;
- deterministic behavior where applicable;
- immutable evidence capture where applicable;
- fail-closed qualification;
- explicit versioned contracts;
- exact semantic/evidence identities where appropriate;
- CURRENT versus HISTORICAL_AS_OF separation;
- no false PIT claims;
- no silent source substitution;
- no caller boolean that simply asserts qualification;
- no output-driven rule changes.

If evidence is missing, contradictory or outside the supported contract, the system
should prefer **unavailable / unsupported / lower confidence** over fabricated certainty.

---

## 6. Point-in-time and validation doctrine

Historical data contaminated by current knowledge is not evidence of alpha.

PAM must distinguish:

- current-data diagnostics;
- retrospective mechanical tests;
- genuine point-in-time historical evidence;
- true forward / out-of-sample observations.

A theoretical backtest does not become investment-skill evidence merely because it is
long or profitable.

Tuning remains:

> `PROPOSAL_ONLY`

No automated process may silently tune model rules and promote the tuned rules into authority.

---

## 7. V1 and V2 roles

### V1

`main` is the frozen operational baseline.

Canonical V1 identity at the time this constitution was created:

- baseline: `VALIDATION_BASELINE_V1`
- model rules: `2026-08-23-allocation-room-integrity-v7`
- validation architecture: `2026-08-23-validation-architecture-v3`
- tuning policy: `PROPOSAL_ONLY`

The exact V1 freeze contract is authoritative in:

`BASELINE_V1_FREEZE.md`

V1 remains the operational control and must not be casually altered by V2 work.

### V2

Primary integration branch:

`model-v2/expected-return-challenger`

V2 is a **challenger**, not production authority.

At the creation of this constitution, PR4C6 had been merged and the V2 integration
branch was at merge commit:

`1da91db1b3c33ac0f65b4f84efb909b9048ae1e1`

Agents must always verify the current remote state rather than assuming this SHA is still current.

V2 must earn authority through validation and shadow operation. It does not become
authoritative merely because it is more sophisticated.

---

## 8. Current V2 foundation

The following major building blocks existed when this constitution was created:

### Runtime / validation foundation

- runtime isolation;
- validation identity;
- immutable retrospective PIT harness.

### Expected Return foundation

- pure Expected Return engine foundation;
- synthetic assumption constructor;
- PIT Expected Return sidecar.

### SEC / economic-fact qualification chain

- PR4C1 — offline fictional SEC diluted-EPS archive/extractor;
- PR4C2 — trusted live SEC Companyfacts acquisition contract;
- PR4C3 — five-year reported diluted-EPS resolver;
- PR4C4 — security / common-class / listing identity qualification;
- PR4C4.1 — cross-form lineage compatibility correction;
- PR4C5 — corporate-action / share-basis qualification;
- PR4C6 — accounting reporting-subject continuity qualification.

Conceptual chain:

```text
SEC/companyfacts evidence
        ↓
PR4C3  five-year EPS series
        ↓
PR4C4  security/class/listing identity
        ↓
PR4C5  share basis / split denomination
        ↓
PR4C6  reporting-subject continuity
        ↓
future real admission / adapter
        ↓
PR4B1 / Expected Return inputs
```

PR4C3–6 currently prove synthetic mechanics and preserve real-admission blockers.
They do not by themselves authorize real production investment facts.

---

## 9. Economic comparability doctrine

For the initial reported-EPS route, economic comparability should mean:

> the same supported reported economic measurement for the same qualified common
> equity / share denomination / reporting subject.

It does **not** require a static business perimeter.

Ordinary changes such as:

- acquisitions;
- divestitures;
- geographic expansion;
- product-mix evolution;
- restructuring;
- impairments;
- ordinary accounting-policy changes;

must not automatically make historical total EPS incomparable when the reporting
subject and economic entitlement remain continuous.

Transformative predecessor/successor or accounting-subject discontinuities are different
and can block comparability.

Comparability is not normalization.

Do not hide adjustments such as:

- organic-growth reconstruction;
- acquisition-adjusted EPS;
- constant-currency EPS;
- adjusted/non-GAAP EPS;
- removal of impairments or restructuring;
- normalized tax;
- cyclicality smoothing;

inside a comparability qualifier.

Those belong, if ever, in later analytical layers with explicit assumptions.

---

## 10. Global architecture

PAM is intended to become globally extensible.

Core economic contracts must not be defined by one jurisdiction, source or exchange.

Canonical rule:

> **No source-specific or country-specific identifier, accounting standard,
> filing type or exchange convention may define the core V2 economic model.**

Source-specific adapters may prove a source-neutral economic property in different ways.

Examples:

```text
SEC / Companyfacts
      ↓
source-neutral economic fact

future ESEF / IFRS
      ↓
same economic contract

future EDINET / OpenDART / Canada
      ↓
same economic contract
```

Useful long-term source families may include official filing systems, legal-entity
registries, security identifiers, exchange directories, market-data providers,
macroeconomic authorities and other legally usable sources.

Licensing and permitted use are first-class concerns. A technically accessible source
is not automatically commercially usable.

---

## 11. Commercial product direction

The preferred commercialization path is:

### PAM Research

- security research pages;
- Expected Return;
- Quality;
- Durability;
- Confidence;
- risk factors;
- thesis tracking;
- evidence/provenance;
- company comparisons;
- watchlists;
- global screening.

### PAM Portfolio Intelligence

- portfolio positions;
- concentration;
- factor / sector / geography / currency exposures;
- thesis status;
- valuation and expected-return context;
- change detection;
- portfolio health;
- analytical alerts;
- historical decision/research log.

### PAM Monitor

- new filings and evidence;
- fundamental changes;
- valuation drift;
- thesis changes;
- confidence deterioration/improvement;
- source/data-quality changes.

### PAM Explore

- screeners;
- rankings;
- comparisons;
- candidate discovery;
- thematic or regional exploration.

The public/commercial surface should emphasize **information, analysis and portfolio
intelligence**. Personalized recommendation or discretionary portfolio management is a
separate regulatory/business decision and is not the default target.

The proprietary engine should remain server-side where practical.

### Primary owner interface

The compact HTML report is the owner's primary post-analysis human interface.
Compact means consolidated, not information-poor. Preserve useful analytical content
while improving organization, hierarchy, navigation, visual clarity and grouping;
shorter reading time alone is not a reason to remove analytical information.

---

## 12. Potential business forms

PAM may eventually support:

- B2C subscription SaaS;
- advanced investor research;
- portfolio-intelligence dashboards;
- premium research reports;
- API / B2B research infrastructure;
- tooling for analysts or advisers;
- model portfolios or generalized research outputs where legally appropriate.

Commercial defensibility may come from a combination of:

- proprietary code;
- copyright;
- trademarks;
- trade secrets;
- evidence/history datasets;
- validation history;
- operational reliability;
- source integration;
- model/process know-how;
- selective patents only where genuinely appropriate.

A patent is not a prerequisite for PAM to become a company.

---

## 13. Shadow validation and authority migration

V2 must not replace V1 through enthusiasm or one strong backtest.

Preferred progression:

1. build the challenger;
2. closed validation;
3. V1/V2 shadow comparison on the same decision dates;
4. accumulate genuine forward observations;
5. formal promotion audit;
6. explicit owner decision.

V1 remains sole authority during shadow validation. V2 remains a challenger until
explicit owner promotion.

Promotion must never be automatic.

Useful evidence includes:

- stability;
- provenance quality;
- PIT integrity;
- selection quality;
- concentration;
- turnover;
- drawdown behavior;
- avoided errors;
- relative behavior versus V1 and VFV;
- quality of explanations;
- operational reliability.

Raw return alone is insufficient.

A rough planning horizon is at least ~12 months / ~24 decision cycles before a
serious first promotion audit, with ~18–24 months / ~36–48 cycles preferable for
high confidence. This is a planning guideline, not an automatic rule.

---

## 14. Governance

The project owner controls:

- product vision;
- investment philosophy;
- model authority;
- merges;
- deployment;
- production;
- commercialization;
- regulatory posture.

AI agents are assistants, not autonomous governors.

### Default role separation

- **ChatGPT / review agents:** independent review, architecture reasoning, product reasoning,
  audit, diagnosis, and generation of implementation prompts.
- **Codex / implementation agent:** repository implementation when explicitly authorized.
- **Owner:** final decision, merge, deployment and production authority.

No AI may claim authority it has not been granted.

---

## 15. Change-control doctrine

Before changing model behavior, ask:

1. Is this a bug fix or a new investment rule?
2. Does it alter recommendation semantics?
3. Does it alter the benchmark / hurdle?
4. Does it alter eligibility, scoring, sizing, allocation or selling?
5. Does it change data authority?
6. Does it weaken provenance or PIT requirements?
7. Does it make the result look better merely because the previous output seemed odd?

If a technical issue actually hides a product or investment-philosophy choice, the
owner must decide.

Technical choices that simply implement already-approved principles may be recommended
and executed through normal review.

---

## 16. Defect classification

When reviewing a surprising result, classify it before changing anything:

- **A — defective logic**
- **B — correct logic, misleading reporting**
- **C — expected behavior**
- **D — mixed**

Do not change investment rules merely because output feels unintuitive.

Prefer the smallest correction that fixes the actual defect.

---

## 17. Development principles

Prefer:

- narrow pull requests;
- investigation before modification;
- versioned contracts;
- adversarial tests;
- fail-closed behavior;
- explicit unsupported states;
- exact replay where it adds integrity;
- minimal blast radius;
- reproducibility;
- maintainability;
- transparent assumptions.

Avoid:

- broad refactors during a narrow evidence chantier;
- hidden normalization;
- invented historical authority;
- silent fallback chains;
- duplicated proof layers;
- provider-specific concepts in the core model;
- optimizing to a desired recommendation;
- unnecessary complexity without decision value.

Canonical engineering principle:

> Build the smallest architecture that closes the real risk.

### Deterministic maintenance and final cleanup

Any recurring integrity, audit, validation or benchmark task that can be executed
deterministically should be automated and condition-driven rather than becoming an
owner maintenance obligation. Preserve V1 maintenance/runtime protection; future
V2 shadow maintenance uses an isolated path. A data outage or evidence failure must
not silently become an investment signal.

Final Architecture Cleanup & Dead-Code Retirement always occurs after every V2
development chantier, including any new chantier added in the future, and before
V2 integration/automation on the Chromebook. New V2 work automatically moves this
cleanup after it. Follow cleanup with final regression/integrity/shadow-readiness
review before integration. Prove usage and compatibility needs before retirement;
no code or feature is removed merely because it looks old. If no genuinely dead
component exists, no deletion is required.

---

## 18. Production and machine roles

Current operating philosophy:

- Mac is the development machine.
- Chromebook/Linux is the operational V1 host.
- GitHub is the code source of truth.
- Google Drive is for approved human operational inputs, not code authority.

V2 development must not casually modify Chromebook production.

A future V2 shadow deployment on the Chromebook or other host must be isolated and
zero-authority until explicitly promoted.

---

## 19. Existing authoritative documents

This constitution does not replace detailed technical sources.

Use this precedence:

### Level 1 — Project vision / governance

1. `PAM_PROJECT_CONSTITUTION.md`
2. explicit owner instruction in the current task/conversation

### Level 2 — Agent operating rules

3. `AGENTS.md`

### Level 3 — Current project state / planned work

4. `PAM_ROADMAP.md`

### Level 4 — Specific authoritative contracts

5. `BASELINE_V1_FREEZE.md`
6. active PR / feature contract documents such as `EXPECTED_RETURN_PR4*.md`
7. versioned code contracts and tests

### Level 5 — Detailed decision history / operational guidance

8. `DECISIONS.md`
9. `AUDIT_GUIDE.md`
10. `README.md`
11. other historical audit / impact documents

When documents conflict:

- do not silently choose;
- identify the conflict;
- prefer the more specific active contract for implementation details;
- never override constitution-level product vision without explicit owner approval.

---

## 20. Memory maintenance policy

This document should NOT be updated after every PR.

Update the constitution only when one of these changes:

- product vision;
- investment philosophy;
- authority model;
- commercialization direction;
- fundamental architecture doctrine;
- governance;
- validation/promotion doctrine.

Use `PAM_ROADMAP.md` for normal progress updates.

Use feature contract documents for detailed implementation.

Use `DECISIONS.md` for major technical decision history.

This separation is intended to prevent project memory from becoming another stale monolith.

---

## 21. Canonical summary for a new AI

If an AI has only two minutes to understand PAM, it should retain this:

> PAM is evolving from a frozen personal investment-allocation system (V1) into a
> globally extensible, evidence-qualified research and portfolio-intelligence platform (V2).
> The commercial vision is research + portfolio intelligence, with the human retaining
> the final investment decision. V2 prioritizes provenance, PIT integrity, deterministic
> contracts, fail-closed evidence qualification and explainable long-term investing.
> Its investment style is High-CAGR Quality Compounder — Asymmetric, built around
> Quality, Durability, Expected Return, Confidence and Portfolio Room. V1 remains the
> operational control while V2 earns authority through shadow validation. Never change
> model rules because an output looks odd, never fabricate missing evidence, and never
> confuse technical sophistication with validated investment superiority.

---

*Initial constitution created after the merge of V2 PR4C6 on 2026-09-13.*
