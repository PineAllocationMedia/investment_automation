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

State immediately after merged PR #40 / PR4C6:

Merge commit:

`1da91db1b3c33ac0f65b4f84efb909b9048ae1e1`

Tree:

`32c723f382aa09b26a66fa78bf84429512dbcd4e`

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

## 7. Immediate pause / documentation chantier

### PAM memory architecture ✅ / CURRENT

Before resuming V2 feature development, establish:

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

## 8. Next technical frontier after the documentation pause

### Candidate next chantier: real admission / adapter architecture

Goal:

connect the qualified C3→C6 evidence chain to real admissible economic facts without
weakening provenance or prematurely modifying PR4B1.

Questions to resolve include:

- which upstream blockers can be discharged by which real authorities;
- how authentic acquisition provenance is carried;
- how real identity authority is established;
- how real split/share-basis authority is established;
- how reporting-subject continuity is evidenced in the real route;
- how publication/availability is represented;
- where CURRENT real facts become eligible for a future PR4B1 adapter;
- where Decimal→model-number conversion may occur;
- how the adapter remains source-neutral at the economic boundary.

This should begin with a read-only architecture audit before implementation.

---

## 9. Expected future V2 sequence

The exact PR numbering may change. The conceptual sequence is more important.

### Stage A — Real fact admission

- real acquisition authority;
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

### Stage F — Global universe

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

### Stage G — Portfolio intelligence

Build the commercializable analytical layer:

- positions;
- exposures;
- concentration;
- expected-return distribution;
- thesis state;
- watchlists;
- change history;
- alerts;
- comparative opportunity context.

### Stage H — Research product surface

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

### Stage I — Shadow validation

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

### Stage J — Authority review

Only after substantial forward evidence:

- compare V1/V2;
- audit failure modes;
- decide whether to retain V1, adopt parts of V2 or promote V2 more broadly.

No automatic promotion.

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

When development resumes after this documentation pause:

1. verify the current V2 remote head;
2. read the constitution and this roadmap;
3. audit the proposed real-admission boundary;
4. do not implement until the smallest safe next contract is identified;
5. preserve V1 unchanged.

---

*Roadmap snapshot created immediately after V2 PR4C6 / PR #40 was merged on 2026-09-13.*
