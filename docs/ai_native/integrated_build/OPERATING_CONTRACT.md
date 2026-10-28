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

## 4. Case and memory contract

Store significant research as dated, source-referenced and versioned **analysis/case records** with separate public/institutional method memory and protected private financial storage. Never put user holdings, account identifiers or brokerage data in ordinary GitHub records. Prompt improvements require a change rationale, relevant case comparison, human approval when material and non-hindsight outcome reviews.

## 5. Acceptance counterexamples retained from T13

- GEN: SEC GAAP EPS 0.36 versus Google/issuer adjusted EPS 0.71 — not interchangeable.
- Celestica: TSX/NYSE same economic issuer and native USD reporting; equity issuance and capex affect per-share economics.
- THEON: reported EBITDA-capex 'conversion' is not CFO; fair-value gain changes headline earnings comparability.
- Cairn Homes: GBX quote versus EUR reporting and capital tied up in land/construction.
- Collegium: apparently low FCF multiple needs pharmaceutical-product durability and debt validation.

Each counterexample is an **integration test case for the eventual end-of-assembly evaluation**, not a recommendation, production readiness certificate or reason to restart a separate discovery pilot. T13 JSON sha256 `645e63ea9f4b75697b284fc5d84cdee7baffba1f3485d8bd1fcccedc86344c36` remains outside repo; references are subject to source rights.
