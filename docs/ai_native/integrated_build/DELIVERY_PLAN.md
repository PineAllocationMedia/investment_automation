# PAM Financial Systems — initial integrated release construction plan

**Version:** construction baseline 0.2 (2026-10-29 R1 scope clarification; acceptance NOT RUN)  
**Authority:** CEO build-first decision in `DECISIONS.md`, PR #251 merged; implementation only through appropriately bounded Work Orders.  
**Status:** PLAN / FIRST INTEGRATED VERSION NOT BUILT; comprehensive acceptance NOT RUN.  
**Primary program owner:** Program Manager / Chief of Staff. Specialists own their bounded sub-deliverables; Codex is an executor only where warranted.  
**Reference:** `model-v2/expected-return-challenger` at `da50ddfa6e6da9e70a39c3dc9f0fe1809175f062` before this PR.

## Result sought

Deliver **one functional AI-native Financial Systems** implementing the 36 CEO-selected design decisions, without duplicating V1/V2's historical software complexity. A normal investment request flows through **Financial Systems Command Center → (Investment Research and, when portfolio information is needed, Portfolio Intelligence) → Command Center report + governed research record**. The route stays manual until inter-Project invocation is actually verified. Absence of a feature is an explicit open gap, not a successful implementation.

The first complete version should support: (a) on-demand global/multisource opportunity discovery and research, (b) selected strategy and context-specific Quality/Durability/Expected Return/Confidence, (c) portfolio/screenshot-assisted Portfolio Room, contribution allocation and costs, (d) layered reports, (e) on-demand comparisons of prior analyses whenever the CEO initiates them (no default recurrence or monitoring), (f) versioned case/prompt memory and constrained private records, (g) auditable source and assumption traces, and (h) read-only preservation planning. This is a **functionality coverage target**, not an unfunded guarantee that external platforms will offer unavailable APIs.

## CEO-confirmed R1 scope clarification — four strategies and manual private archive (2026-10-29)

**Decision provenance:** The CEO selected **D: multiple fully supported investment strategies in R1** and **B: secure manual private-record archive** in the PAM Project conversation on 2026-10-29. These are R1 *delivery-scope* clarifications, not completed software, executed acceptance, source licensing, a chosen storage provider, or approval of new investment-policy numbers. The canonical append-only `DECISIONS.md` is not edited here; a separate authorized Governance Sync may later record this clarification without rewriting the 36 original selections.

**One architecture, four complete strategy-specific experiences:** The R1 target now explicitly includes `High-CAGR`, `Capital Preservation`, `Income`, and `Balanced`. They reuse one CC/IR/PI route, the five shared QUALITY/DURABILITY/EXPECTED RETURN/CONFIDENCE/PORTFOLIO ROOM lenses, provenance, arithmetic checks, reporting and human control. *Complete* means a distinct approved contract/method, contextual intake, source/economic tests, risk/portfolio treatment and conditional user-facing report for **each** strategy; merely accepting an arbitrary `strategy_id` or producing an exploratory narrative does **not** satisfy D.

| R1 strategy | Current policy authority | Mandatory approval dependency for full R1 |
|---|---|---|
| High-CAGR | Existing approved V2 High-CAGR policy **within its current scope only** | Preserve and explicitly load/check applicable method version; no silent reinterpretation |
| Capital Preservation | Specific R1 policy **NOT APPROVED** | CEO approval of separately proposed objective, horizon, eligible instruments, capital-loss/liquidity limits, benchmark, evidence/valuation doctrine, diversification and exit rules |
| Income | Specific R1 policy **NOT APPROVED** | CEO approval of separately proposed income objective, payout/source sustainability, eligible instruments, horizon, constraints, benchmark, tax/cost treatment and turnover/sale rules |
| Balanced | Existing V2 `balanced` mode is **not automatically** a complete AI-native R1 Balanced policy | Map V2's four-mode rules without changing their authority; CEO approves a distinct R1 mandate/contract and any material policy amendment |

**Three CEO policy proposals prepared (NOT APPROVED / NOT IMPLEMENTED):** [Capital Preservation](research/POLICY_PROPOSAL_CAPITAL_PRESERVATION_R1.md), [Income](research/POLICY_PROPOSAL_INCOME_R1.md), and [Balanced](research/POLICY_PROPOSAL_BALANCED_R1.md). Each has explicit approval choices, scenario/evidence/portfolio requirements and a non-actionable acceptance outline. These are a single decision package, **not three new pilot releases**. After separate CEO policy authorization, implement and source-check the three concrete R1 methods on the existing shared CC/IR/PI pipeline. Before then, no apparently complete strategy-specific decision or numerical allocation may be claimed from the proposals.

**No policy invention:** Preserve V2's binding existing policies, four-mode/capital-destination semantics and protected governance. Do not transfer High-CAGR's VFV hurdle, drawdown tolerance, reserve propensity, concentration or sale doctrine into preservation, income or balanced by default. Each proposed contract must make instrument universe, investment objective, horizon, risk and permanent-loss limits, opportunity-cost reference, required evidence, Expected Return/cash-flow interpretation, portfolio concentration/room, contribution/sale policy, account FX/fees/tax costs and exceptional lifecycle rules explicit; **leave unset values UNKNOWN**. Building a reusable strategy *interface* and drafting policy proposals is allowed; a distinct strategy-specific actionable recommendation or `IMPLEMENTED_AND_CHECKED` claim remains gated on separate CEO approval, appropriately reviewed implementation and real evidence. If this gate blocks complete R1 delivery, escalate it as `REQUIRES_CEO_DECISION`; do not silently redefine D as exploratory-only.

**Manual Tier-III private-memory scope:** R1 must support on-demand generation/export of a private research record, **human-controlled saving** to a CEO-approved access-restricted and appropriately protected location, and **manual retrieval/re-supply** of that record for a separately CEO-initiated follow-up. Existing `--output private-case` and `--output followup-draft` are construction components, **not** evidence that storage or restoration worked. Until the CEO selects/authorizes the actual location and its privacy, retention, backup and recovery procedures are checked, durable private memory is **PARTIAL / operationally UNVERIFIED**. GitHub holds only governed non-sensitive method/version records and content-free review proposals; never private holdings, account identifiers, credentials, private case bodies, or rights-restricted source archives. No automatic archive, connector purchase, synchronization, recurring research, broker action or silent multi-Project transfer.

**Minimum incremental delivery sequence (inside the same integrated build):**
1. Maintain shared CC/IR/PI contracts; prepare **three policy proposals** for CEO review and map existing High-CAGR/V2 modes without changing protected documents or implementing invented rules.
2. Once strategy-specific policy authority is obtained, implement the smallest reusable strategy-specific IR/PI behavior and matching honest, source-linked reporting **for all four mandates**; run essential deterministic/source/privacy tests while constructing.
3. Reuse existing private JSON export/follow-up; choose and check one protected **manual** archive/recovery procedure, with no required always-on private-memory service.
4. Complete the existing 01–36 evidence map and perform **one comprehensive system-wide acceptance after assembly**, including four strategy cases, manual archive/recovery, privacy, actual three-Project handoffs, costs and human time. Readiness remains distinct from production and CEO-controlled merges.

## Build as one integrated product — parallel modules, no recurring micro-pilots

| Module | Responsible capability | Concrete working deliverable | Boundary / handoff |
|---|---|---|---|
| M1. Experience and CC integration | Product & UX with PM integration | Intake UX, configurable mandate, dynamic prompt assembly, routing, complete report, manual transfers | Request → IR / PI → final, without false auto-orchestration claims |
| M2. Investment Research | Investment Research with Data & Evidence as warranted | Shared source/quant/qual library plus four separate strategy methods: existing High-CAGR and CEO-policy-gated Capital Preservation, Income, Balanced; company/sector/macro, valuation and counter-thesis | Only an approved method can govern its strategy-specific economic/portfolio response; no automatic stock purchase |
| M3. Portfolio Intelligence | Portfolio Intelligence with Product & UX | Authorized Blossom-view or dated screenshot reading, known/unknown holdings, risk/look-through, allocation of new contributions, true costs, exceptional thesis reviews | Uses observed positions only; no trading; private data excluded from repository |
| M4. Monitoring and memory | CC + PM for governable contracts | CEO-requested follow-up, dated case/prompt versions, non-sensitive GitHub proposals and explicit manual export/re-import of a private case | Human chooses/protects the private storage; secure location and recovery still unverified; no recurring schedule or publication |
| M5. Evidence and deterministic checks | Data & Evidence / Data Analyst as needed | Simple recalculation/FX/date/identity/conflict checks only where accuracy warrants code, source rights ledger | No new broad parser stack; no $ financial data |
| M6. Legacy knowledge recovery | Architecture & Audit | Read-only inventories GitHub/Mac/Chromebook/PC and unique-knowledge map | Separate device scopes; no move/delete before verified preservation and CEO approval |
| M7. Integration and acceptance | Program Manager, Architecture & Audit only for consequential assurance | 01–36 evidence map, integrated scenario, adversarial error cases, independent checks, final owner decision package | Full-system acceptance **after** functional assembly; gates remain distinct |

These are **modules of one release**, not seven mandatory sequential qualification pilots. Reversible work already approved within bounded WOs does not require new PM permission at every internal step. When a new source, device access or protected policy change needs distinct authority, separate it without stalling other permitted work.

## Delivery integration rules

1. Start from the editable `REQUEST` envelope in `OPERATING_CONTRACT.md`, not a rigid provider dataset. Translate the investor's question into required economic facts and strategy.
2. For each **material fact**, find a permitted original source when feasible, use a reputable secondary source for discovery/cross-check, and record period, units, currency, identity, definition, rights, conflicting values and observation date. Fail closed on unsupported *claims*, not on the whole company.
3. Reuse V2's five pillars for the four CEO-selected R1 mandates, preserve existing High-CAGR scope and V2 four-mode authority, and require **separate CEO-approved policy contracts** for Capital Preservation, Income and R1 Balanced before treating them as complete or decision-grade. Do not silently alias V2 modes or invent new rules. Explicitly load/check approved methods.
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
