# PAM Financial Systems — initial integrated release construction plan

**Version:** construction baseline 0.1 (2026-10-28)  
**Authority:** CEO build-first decision in `DECISIONS.md`, PR #251 merged; implementation only through appropriately bounded Work Orders.  
**Status:** PLAN / FIRST INTEGRATED VERSION NOT BUILT; comprehensive acceptance NOT RUN.  
**Primary program owner:** Program Manager / Chief of Staff. Specialists own their bounded sub-deliverables; Codex is an executor only where warranted.  
**Reference:** `model-v2/expected-return-challenger` at `da50ddfa6e6da9e70a39c3dc9f0fe1809175f062` before this PR.

## Result sought

Deliver **one functional AI-native Financial Systems** implementing the 36 CEO-selected design decisions, without duplicating V1/V2's historical software complexity. A normal investment request flows through **Financial Systems Command Center → (Investment Research and, when portfolio information is needed, Portfolio Intelligence) → Command Center report + governed research record**. The route stays manual until inter-Project invocation is actually verified. Absence of a feature is an explicit open gap, not a successful implementation.

The first complete version should support: (a) on-demand global/multisource opportunity discovery and research, (b) selected strategy and context-specific Quality/Durability/Expected Return/Confidence, (c) portfolio/screenshot-assisted Portfolio Room, contribution allocation and costs, (d) layered reports, (e) weekly-intelligence workflow and selective monitoring only if supported, (f) versioned case/prompt memory and constrained private records, (g) auditable source and assumption traces, and (h) read-only preservation planning. This is a **functionality coverage target**, not an unfunded guarantee that external platforms will offer unavailable APIs.

## Build as one integrated product — parallel modules, no recurring micro-pilots

| Module | Responsible capability | Concrete working deliverable | Boundary / handoff |
|---|---|---|---|
| M1. Experience and CC integration | Product & UX with PM integration | Intake UX, configurable mandate, dynamic prompt assembly, routing, complete report, manual transfers | Request → IR / PI → final, without false auto-orchestration claims |
| M2. Investment Research | Investment Research with Data & Evidence as warranted | Source-neutral fact router, quantified+qualitative method library, High-CAGR module, company/sector/macro lenses, valuation and counter-thesis | Evidence-rich IR capsule; no automatic stock purchase |
| M3. Portfolio Intelligence | Portfolio Intelligence with Product & UX | Authorized Blossom-view or dated screenshot reading, known/unknown holdings, risk/look-through, allocation of new contributions, true costs, exceptional thesis reviews | Uses observed positions only; no trading; private data excluded from repository |
| M4. Monitoring and memory | CC + PM for governable contracts | Weekly briefing template, exception-trigger protocol, dated case and prompt versions, GitHub institutional-memory proposal + private archive policy | Scheduling is opt-in and contingent on verified product abilities; no auto-publishing |
| M5. Evidence and deterministic checks | Data & Evidence / Data Analyst as needed | Simple recalculation/FX/date/identity/conflict checks only where accuracy warrants code, source rights ledger | No new broad parser stack; no $ financial data |
| M6. Legacy knowledge recovery | Architecture & Audit | Read-only inventories GitHub/Mac/Chromebook/PC and unique-knowledge map | Separate device scopes; no move/delete before verified preservation and CEO approval |
| M7. Integration and acceptance | Program Manager, Architecture & Audit only for consequential assurance | 01–36 evidence map, integrated scenario, adversarial error cases, independent checks, final owner decision package | Full-system acceptance **after** functional assembly; gates remain distinct |

These are **modules of one release**, not seven mandatory sequential qualification pilots. Reversible work already approved within bounded WOs does not require new PM permission at every internal step. When a new source, device access or protected policy change needs distinct authority, separate it without stalling other permitted work.

## Delivery integration rules

1. Start from the editable `REQUEST` envelope in `OPERATING_CONTRACT.md`, not a rigid provider dataset. Translate the investor's question into required economic facts and strategy.
2. For each **material fact**, find a permitted original source when feasible, use a reputable secondary source for discovery/cross-check, and record period, units, currency, identity, definition, rights, conflicting values and observation date. Fail closed on unsupported *claims*, not on the whole company.
3. Use the existing V2 five pillars, separate the **approved High-CAGR method** from generic research, and do not silently invent new policies for balanced/preservation modes. Explicitly load approved methods before decision-grade work.
4. Build valuation from normalized per-share economics and appropriate methods. A forward multiple from adjusted EPS is a lead, not normalized Expected Return. No unsupported VFV alpha.
5. Portfolio analysis depends on reliable dated Blossom visuals/screenshot and provided account type, broker, commissions, FX, taxes and constraints. Recommend percentages **of new contributions** first; do not infer invisible holdings.
6. Do not assert automatic CC↔IR↔PI messaging, portfolio integrations or proactive weekly execution until supported and observed. Use one compact manual handoff when necessary.
7. Report ≤10-minute user-facing conclusions, with expandable evidence and unverified assumptions; keep significant analyses traceable but exclude private portfolio values, secrets and large raw archives from GitHub.
8. Historical T05–T13 evidence is retained, including T13's observed 30-case source-fusion precedent. No automatic recommendation to buy its five conditional candidates.

## Build completion versus acceptance

**Functional assembly complete** means all 36 Blueprint decisions have a linked real component or a separately CEO-accepted supported fallback; every unresolved platform/legal/policy feature is visible, and any material inability is elevated to the CEO **before** claiming completeness. Do not reduce this to 'the prompts exist.' Security, source, arithmetic and minimal component checks occur during construction.

After assembly, perform **one comprehensive integrated acceptance evaluation**: dated real-source multi-country securities, calibrated provenance, contradictory adjusted/GAAP results, FX and corporate actions, strategy correctness, honest unsupported-case behavior, portfolio visual edge cases, costs and privacy, 3-Project handoff trace, actual weekly/report effort, historical memory/invalidations and degraded provider access. Evaluate `RESEARCH-READY`, `PORTFOLIO-READY` and `ROUTINE-READY` separately. Real usage then drives versioned, human-reviewed updates and selective regression.

**Never infer production authority from an integrated test**. V1 on `main` remains frozen operational control; V2 challenger and Stage D remain unchanged. No automated trades, spending, policy drift, unattended dev restart, source-rights bypass, device cleanup, Media scope change, production, deployment or merges without separate CEO authority.

## First authorized next work package after approval of this planning PR

**WO-FIN-FS-INTEGRATED-EXPERIENCE-ASSEMBLY (proposed):** primary Product & UX; create the actual CC/IR/PI v1 integrated Project instruction drafts, selected-strategy request UX, real handoff templates and report contract, with a portable manual fallback and a complete mapping back to `DECISION_COVERAGE.md`. Consult Investment Research and Portfolio Intelligence only for their own portions; no protected edits, production integration or speculative API claims. Follow it with coordinated implementation of methods, portfolio flow, reporting/memory and essential checks; **do not run a new unrelated discovery pilot**.

**Resources:** existing GitHub and ChatGPT/Work; 0 $ additional external financial-data costs; no local machine access unless separately scoped. **Stop:** open PR, do not merge; report actual changes and unresolved capabilities.
