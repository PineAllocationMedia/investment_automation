# AGENTS.md

> Tool-neutral operating instructions for any AI or automated development agent working on PAM.

---

## 1. Mandatory reading order

For substantive governed work, use minimum necessary context in this order:

1. Read `PAM_PROJECT_CONSTITUTION.md`.
2. Read `governance/PAM_GOVERNANCE.md`.
3. Read `governance/PAM_CURRENT_STATE.md`.
4. Read the acting role's own `governance/roles/<ROLE>.md` charter.
5. Read the assigned Work Order, when one exists.
6. Read only the task-specific technical contracts and source documents needed.

Read `governance/PAM_STRATEGY.md` when strategy, product or commercial context is
relevant. Do not force every role to read `PAM_ROADMAP.md`, `DECISIONS.md` or
`README.md` in full for every task. Read relevant roadmap and Decision Registry
portions when current sequencing or historical rationale matters. Read
`BASELINE_V1_FREEZE.md` if V1 or production behavior could be affected, and
`AUDIT_GUIDE.md` only for V1 audit workflows.

Do not use `README.md` or `AUDIT_GUIDE.md` as the sole description of PAM's long-term V2/product direction.

---

## 2. Verify reality before acting

Never trust a stale document for exact Git state.

Before implementation:

- `git fetch origin`;
- verify the intended base branch;
- verify exact base SHA/tree;
- inspect current working tree/index;
- preserve divergent local refs;
- inspect the actual implementation before changing it.

At the time this file was first created, the V2 integration branch was:

`model-v2/expected-return-challenger`

after PR4C6 merge commit:

`1da91db1b3c33ac0f65b4f84efb909b9048ae1e1`

This is historical context, not a permanent expected SHA.

---

## 3. Role boundaries

The canonical role charters and administrative authority model are in
`governance/roles/` and `governance/PAM_GOVERNANCE.md`. Every Work Order has one
primary responsible role. No role may expand its own authority, amend its own
charter or merge to a canonical branch.

### Owner

Only the owner decides:

- merges;
- deployment;
- production authority;
- investment-philosophy changes;
- commercialization direction;
- regulatory posture;
- final promotion of V2.

### Review / reasoning agents

Default responsibilities:

- inspect;
- audit;
- diagnose;
- classify defects;
- compare architecture options;
- recommend;
- write precise implementation prompts.

Do not claim something was changed, merged, deployed or deleted unless it actually was.

### Implementation agents

When explicitly authorized:

- investigate first;
- use the exact approved base;
- make the smallest safe change;
- add regression tests;
- validate;
- commit/push/open PR when requested;
- stop before merge unless explicitly authorized.

---

## 4. Permanent safeguards

Unless explicitly superseded by an approved contract:

- V1 `main` remains frozen operational authority.
- V2 remains a challenger.
- Tuning remains `PROPOSAL_ONLY`.
- Historical diagnostics are not automatically PIT evidence.
- Synthetic qualification is not real-data authority.
- Missing data does not become a guessed value.
- Data uncertainty reduces confidence/admission rather than being hidden.
- Investment rules must not be altered because an output looks strange.
- No automatic self-modification of investment rules.
- No autonomous promotion of V2.
- No production deployment as a side effect of development work.

---

## 5. Product direction

Remember that the target commercial product is:

> **PAM = financial research intelligence + portfolio intelligence**

The commercial surface should prioritize:

- research;
- explanation;
- evidence/provenance;
- screening;
- monitoring;
- comparisons;
- watchlists;
- portfolio analytics;
- thesis tracking;
- alerts.

The user retains the final investment decision.

Do not redesign PAM primarily as a personalized recommendation bot unless the owner explicitly changes this vision.

---

## 6. Investment architecture

V2 pillars:

1. QUALITY
2. DURABILITY
3. EXPECTED RETURN
4. CONFIDENCE
5. PORTFOLIO ROOM

Style:

> High-CAGR Quality Compounder — Asymmetric

Canonical principle:

> Be aggressive with economic risk, not information uncertainty.

Do not introduce mean-variance optimization, covariance-driven allocation or opaque complexity merely because it is mathematically sophisticated.

---

## 7. Evidence architecture

Preferred flow:

```text
source
→ immutable capture
→ extraction
→ qualification
→ economic facts
→ analytical assumptions
→ expected return / quality / durability / confidence
→ portfolio context
→ research output
```

Keep source semantics, evidence authority and model inference separate.

Do not let:

- source-specific identifiers;
- country-specific filing types;
- ticker conventions;
- exchange conventions;

define core economic contracts.

---

## 8. Defect-review protocol

For any surprising behavior, classify:

- A — defective logic
- B — correct logic / misleading reporting
- C — expected behavior
- D — mixed

Then repair the smallest real defect.

If logic is correct and reporting is confusing, prefer a reporting fix.

If the issue hides a product or investment-philosophy decision, stop and ask the owner.

---

## 9. Coding / PR discipline

Prefer one narrow chantier at a time.

Every implementation prompt or PR should make explicit:

- base branch/SHA;
- files in scope;
- files out of scope;
- invariants;
- supported/unsupported cases;
- authority limitations;
- regression tests;
- full-suite expectations;
- whether model rules change.

Avoid opportunistic refactors.

Do not modify unrelated code because it is nearby.

---

## 10. Validation defaults

Use the repository's pinned Python / locked dependencies and isolated test runner.

For substantive V2 work, preserve and verify as applicable:

- targeted tests;
- adjacent-layer regression tests;
- the validation tier determined from the complete change set:
  - `DOCS_ONLY` — documentation integrity for an all-Markdown diff;
  - `STANDARD` — complete discovered ordinary suite minus only the isolated
    heavyweight PIT adapter-equivalence module;
  - `FULL_PIT` — the complete ordinary suite plus that heavyweight PIT module;
- unknown or ambiguous paths must fail toward `FULL_PIT`;
- `git diff --check`;
- `git diff --cached --check`;
- `git show --format= --check HEAD`;
- protected PIT fingerprint;
- protected determinism fingerprint;
- unchanged `MODEL_RULES_VERSION` when no investment-rule change is intended.

Current protected identities at creation:

- PIT: `f1e73b27b80e41d96ff5e0fe990b482bad71b7220db0b5bd6a2f470d72786166`
- Determinism: `f8457910665391e39c234274cae4c029802c681211eebc7dba986a63000876f1`
- Model rules: `2026-08-23-allocation-room-integrity-v7`

If these legitimately change in a future approved architecture, update the canonical documents deliberately.

---

## 11. Forbidden shortcuts

Do not:

- fabricate portfolio inputs to bypass validation;
- run positive-capital development analysis unless explicitly requested;
- use contaminated historical data as alpha proof;
- silently accept caller assertions like `qualified=True`;
- remove blockers merely to make a real issuer pass;
- broaden source authority without evidence;
- convert CURRENT evidence into HISTORICAL_AS_OF authority;
- normalize EPS inside a comparability layer;
- merge or deploy because tests pass;
- touch Chromebook production during normal V2 development.

---

## 12. Global expansion

Long-term coverage should be global where legally and technically supportable.

Coverage maturity should conceptually distinguish:

1. DISCOVERY
2. OBSERVABLE
3. V2 ADMISSIBLE

Do not equate “we can fetch a ticker” with “we can safely admit it into the stock picker.”

Licensing / terms of use are part of source architecture.

---

## 13. Current V2 evidence chain

At creation:

```text
PR4C3  five-year reported diluted EPS
  ↓
PR4C4  issuer/security/common-class/listing identity
  ↓
PR4C5  corporate actions / share basis
  ↓
PR4C6  accounting reporting-subject continuity
  ↓
future real admission / adapter
  ↓
Expected Return inputs
```

Each synthetic layer proves mechanics, not real admission.

---

## 14. Updating project memory

After a normal merged PR:

- update `PAM_ROADMAP.md` if project state/next work changed;
- update the feature contract if needed;
- add to `DECISIONS.md` only for meaningful design decisions;
- do **not** edit `PAM_PROJECT_CONSTITUTION.md` unless a foundational principle changed.

This prevents documentation drift.

---

## 15. Agent handoff format

Before ending a substantial chantier, leave enough information for another agent to continue:

- exact base/head/merge state;
- what was implemented;
- what remains unsupported;
- tests;
- blockers;
- next recommended chantier;
- any unresolved product decision.

Do not rely on conversation memory as the only handoff.

---

## 16. Conflict handling

If two documents conflict:

1. identify the conflict explicitly;
2. check `PAM_PROJECT_CONSTITUTION.md`;
3. check the most specific active technical contract;
4. check owner instructions;
5. do not silently reinterpret investment philosophy.

---

## 17. Security and privacy

Never commit:

- passwords;
- API secrets;
- tokens;
- private user identifiers;
- private SEC User-Agent contact values;
- local credentials.

Do not reproduce secrets found in logs or Git metadata in reports.

---

## 18. Short operating mantra

> Verify the state.
> Understand the contract.
> Change the smallest thing.
> Preserve provenance.
> Fail closed.
> Test adversarially.
> Do not promote authority implicitly.
> Leave a clean handoff.
