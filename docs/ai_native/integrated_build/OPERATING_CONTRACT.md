# PAM Financial Systems — integration operating contract (construction draft)

**Scope:** portable interfaces for one coherent CC/IR/PI workflow; **not deployed**. Use this to create versioned Project instructions and request/report templates. Does not override existing CEO-protected investment policy or the approved Project v0.2 instructions until separately adopted. Manual transfer is the current verified fallback.

## 1. Request and strategy context

A request carries **only supplied or explicitly confirmed values**, not fabricated defaults for account/tax/FX costs:

```json
{
  "analysis_id": "user-selected-or-generated-ID",
  "as_of": "YYYY-MM-DD",
  "objective": "research | compare | portfolio_contribution | user_requested_followup",
  "strategy_id": "approved-strategy-and-version",
  "horizon": "explicit-user-horizon",
  "risk_constraints": ["supplied"],
  "universe": ["user holdings", "watchlist", "worldwide discovery as justified"],
  "account_context": {"type": "UNKNOWN", "broker": "UNKNOWN", "tax": "UNKNOWN", "commission": "UNKNOWN", "fx_cost": "UNKNOWN"},
  "portfolio_input": {"source": "NONE | authorized Blossom view | dated screenshot", "observed_at": null},
  "privacy": "PRIVATE",
  "output_budget": "executive <=10 minutes; detailed evidence on demand"
}
```

Missing decisive context is asked concisely or preserved as conditional `UNKNOWN`, never invented. High-CAGR's existing policies are not generalized to another strategy.

## 2. Reusable source-neutral fact record

```json
{
  "economic_entity": "evidence-backed identity",
  "instrument": "ticker/class/exchange/ADR-ratio only if known",
  "metric": "precise economic concept",
  "value": "number or null",
  "unit_currency": "unit and native currency",
  "start_end_or_quote_timestamp": "exact applicable period/date",
  "definition_basis": "US-GAAP / IFRS / issuer-adjusted / provider estimate",
  "source_url": "exact reference",
  "observed_at": "capture date",
  "publication_at": "if verified",
  "source_rights_status": "PERMITTED | UNCERTAIN | RESTRICTED",
  "verification_status": "VERIFIED | INDICATIVE | CONFLICTED | MISSING",
  "classification": "SOURCE_FACT | THIRD_PARTY_ESTIMATE | PAM_ASSUMPTION",
  "conflict_or_qualification": "explicit limitation or null"
}
```

If two sources disagree, compare accounting definitions, periods, currency, corporate-action basis and instrument identity; log both without selecting the higher-impact number. Data absence is **not** Quality failure. Providers are chosen per **fact needed**, not used as a universal company database.

## 3. Handoff, provenance, and report

`CC` creates a compact `IR_REQUEST` specifying needed facts, question, scope, strategy, expected output and source budget. `IR` returns `IR_CAPSULE` with `FACTS_VERIFIED`, `UNVERIFIED`, `ASSUMPTIONS`, `COUNTER_THESIS`, `VALUATION_SCENARIOS`, `EXPECTED_RETURN_STATUS`, `CONFIDENCE_RATIONALE`, citations and `NEXT_OWNER`. `PI`, only when requested portfolio inputs exist, returns a `PI_DELTA` with `VISIBLE_HOLDINGS`, `UNKNOWN_HOLDINGS`, `AS_OF`, `EXPOSURES`, `COST_INPUTS`, `CONTRIBUTION_WEIGHTS` and reasoned no-action/exceptional-trim decisions. `CC` checks coverage and synthesizes a final decision report, **without inflating evidence confidence**.

When IR has collected source observations, it may attach an optional **PRIVATE** `EVIDENCE_ANNEX` directly to the unchanged `IR_CAPSULE`: `{"analysis_id":"same-analysis-id","analysis_as_of":"request-YYYY-MM-DD","observations":[...]}` with the existing `ai_native.source_fusion` observation schema. M7a consumes this field automatically through both CC→IR→CC and CC→IR→PI→CC manual routes; no second source-entry argument is needed. If both embedded and separate annexes are supplied, reject rather than select silently. Reject mismatched identity/date, unknown IR fact IDs and observations occurring after `IR_CAPSULE.research_as_of`. Keep the complete original capsule unchanged when forwarding to PI; keep the resulting source/alignment annex private. Structural alignment does **not** establish authenticity, rights, PIT authority, independent verification or readiness.

Minimal shared envelope: `ANALYSIS_ID`, `PROMPT_VERSION`, `METHOD_VERSION`, `OBJECTIVE`, `AS_OF`, `SOURCE_REFERENCES`, `FACTS_VERIFIED`, `INTERPRETATIONS`, `ASSUMPTIONS`, `UNKNOWN_OR_DISPUTED`, `SCENARIOS`, `IMPACT_ON_DECISION`, `CONFIDENCE_RATIONALE`, `FURTHER_CHECK_REQUIRED`, `NEXT_OWNER`, `OUTPUT_BUDGET`. Transfer only the compact delta plus exact archive references; keep needed attachments when source locators are unavailable.

**Final report template:** (1) decision question and what was actually checked; (2) top conclusions and counter-arguments; (3) Quality/Durability/Expected Return/Confidence; (4) price and after-cost/portfolio implications **only if supported**; (5) missing decisive facts and recommended next action; (6) evidence annex reference. For a CEO-requested follow-up compare with the actual earlier analysis regardless of elapsed time, including thesis/invalidation changes and justified no-action. There is no scheduled or default weekly analysis. No auto-trading.

**PI-only capital route (M1→M3→M4):** A CEO-initiated portfolio-only request can now produce the same supplied gross/cost/funded contribution summary as the IR+PI path after the manual PI delta arrives, **without manufacturing an IR capsule**. The shared private calculator requires portfolio date parity; any incomplete supplied observation cannot be overridden by a contradictory complete-scope assertion. Research-only annexes remain unavailable without IR. No automatic holdings access or executable orders follow.

**Research discovery/triage reporting seam (M2→M4):** after CEO-requested IR/source evidence is structurally assembled, M2 classifies only caller-supplied candidate research tasks into EVIDENCE_RESOLUTION and HUMAN_DEEP_DIVE. The private CC report now shows stage counts and at most eight candidate references **in submitted order, never ranked**. Unusable source observations, rights gaps and missing IR facts remain explicit research blockers. No global discovery, source authentication, normalized Expected Return, investability, automatic portfolio action or independent ranking is established. Detailed candidate rationale, economic issuer, source records and original research questions remain in the private annex, excluded from GitHub memory.

**Fundamental economics reporting seam (M2→M4):** a supplied IR source-annex and compatible original-source observations can produce a private two-period M2 dossier. M4 now shows **only descriptive, structurally comparable** reported revenue change, operating margins, CFO less cash capex (explicitly *not* normalized owner earnings), diluted-share changes, and specialist-reported qualitative-axis statuses. Noncomparable/missing pairs remain UNAVAILABLE; original sources, qualitative rationales and financial details remain in the private dossier, never in institutional GitHub memory. No independent source authentication, organic-growth conclusion, Quality/Durability verdict or Expected Return is implied.

**Research valuation reporting seam (M2→M4):** conditional BEAR/BASE/BULL scenario measures from the existing M2 arithmetic may appear in the **private** CC decision report. Each displays only its available annualized price-only CAGR, separately its conditional year-end cash-flow IRR when distributions are explicitly supplied, or UNAVAILABLE on unconfirmed security/currency basis. These alternative scenario calculations are *not* probability-weighted Expected Return, not a VFV alpha forecast and not proof of source authentication or investability; details and rationale stay in the private valuation annex. No valuation payload enters public GitHub memory.

**Portfolio Room reporting seam (M3→M4):** for an explicitly CEO-requested IR+PI mandate, a scoped private portfolio observation and qualitative Portfolio Room assessment now surface in the **private final CC report**: caller-reported four research pillars, four portfolio checks, supplied known issuer exposure as a conditional lower bound, unknown look-through, and a count of unresolved conditions. Neither market/issuer narrative nor account scope, holdings details or personal balances are copied into GitHub memory. ROOM_CONDITIONAL/UNAVAILABLE is **not** investment admission, portfolio target weight or trade approval. If no PI delta is delivered, the session stays awaiting a manual PI handoff rather than manufacturing a completed report.

**New-contribution reporting seam (M3→M4):** if a scoped, dated PI contribution projection is available, the private CC report may display up to eight **caller-supplied percentages of NEW capital**, never portfolio target weights. The report keeps cost/funding outcomes separate: gross only, conditionally reconciled supplied fixed fees, or unavailable. The summary excludes balances, purchase amounts and detailed cost quotes, and nothing is copied to public GitHub memory. More destinations stay in the private annex. No recommendation, authentication, executable order, or net Expected Return follows from this display.

## 4. Case and memory contract

Store significant research as dated, source-referenced and versioned **analysis/case records** with separate public/institutional method memory and protected private financial storage. Never put user holdings, account identifiers or brokerage data in ordinary GitHub records. Prompt improvements require a change rationale, relevant case comparison, human approval when material and non-hindsight outcome reviews.

## 5. Acceptance counterexamples retained from T13

- GEN: SEC GAAP EPS 0.36 versus Google/issuer adjusted EPS 0.71 — not interchangeable.
- Celestica: TSX/NYSE same economic issuer and native USD reporting; equity issuance and capex affect per-share economics.
- THEON: reported EBITDA-capex 'conversion' is not CFO; fair-value gain changes headline earnings comparability.
- Cairn Homes: GBX quote versus EUR reporting and capital tied up in land/construction.
- Collegium: apparently low FCF multiple needs pharmaceutical-product durability and debt validation.

Each counterexample is an **integration test case for the eventual end-of-assembly evaluation**, not a recommendation, production readiness certificate or reason to restart a separate discovery pilot. T13 JSON sha256 `645e63ea9f4b75697b284fc5d84cdee7baffba1f3485d8bd1fcccedc86344c36` remains outside repo; references are subject to source rights.
