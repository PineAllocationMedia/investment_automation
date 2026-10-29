# M2 R1 — Ready-to-use CC → Investment Research request
**Status:** CANDIDATE TEMPLATE, not proof of method installation. **Primary owner:** Investment Research.  
**Use:** copy the block below into a Project/Work session where the IR instructions **and** referenced method texts are genuinely available. It is a functional execution interface to M2, not a new isolated test plan.

```text
PAM R1 — IR_REQUEST / FACT-FIRST MULTISOURCE RESEARCH

ANALYSIS_ID: [unique ID or UNKNOWN]
TRANSFER_ID: [CC transfer ID or NOT_SUPPLIED]
AS_OF: [local date/time and relevant source cutoff]
STRATEGY_ID@VERSION: [explicit approved strategy, e.g. high-cagr if applicable]
HORIZON: [user-specified 5–10 years or other]
GOAL: [compare / discover / evaluate investment research]
CANDIDATE_UNIVERSE: [holdings / watchlist / country(s) / open discovery]
RISK_AND_ACCOUNT_CONSTRAINTS: [supplied only, else UNKNOWN]
BENCHMARK: [VFV only where canonically applicable; otherwise specified or UNKNOWN]
INSTR_VERSION / METHOD_VERSION: [actually loaded; else UNKNOWN_NOT_LOADED]
PRICE_AND_REPORTING_CURRENCIES: [if specified; else verify per instrument]

TASK:
1. Define the facts required to answer the actual goal. Load SOURCE_FUSION_R1, applicable HIGH_CAGR_METHOD_R1 and VALUATION_R1 only if truly accessible; label any missing method, do not claim it was loaded.
2. Identify economic issuers and investable instruments/classes across relevant markets. Use lawful multisource web search for each fact needed. Prefer issuer/regulator originals for decisive financial claims; independent secondary pages for leads and cross-checks. Preserve exact source URLs, periods, actual verified date, native currency, financial standard, corporate action/ADR ratio and source rights.
3. For broad discovery, record source universe, selection funnel, company deduplication and missing/sector/geography biases. Do not prespecify 3 well-known stocks as supposed global winners.
4. Analyze Quality, Durability and capital/reinvestment economics; quantify per-share dilution/normalization wherever supported. Select a business-appropriate valuation method, build justified bear/base/bull only if sufficient inputs exist, and show checkable calculations. Do not invent VFV forward ER or force unsupported stock rankings.
5. Deliver concise IR_CAPSULE with evidence status + S/F/K/V EVIDENCE_ANNEX, counter-thesis, confidence, Expected Return availability, and exact next PI/CC questions. PORTFOLIO_ROOM=AWAITING_PI without dated portfolio observation. Private portfolio values should not be committed to GitHub.

OUTPUT_BUDGET: <=10-minute executive extract, with source/proof annex proportional to consequential claims.
AUTHORITY: research only; no trades, investment-policy changes, paid data, unauthorized scraping, automatic Project collaboration, scheduled execution or GitHub write.
STOP after single portable handoff; do not initiate a new discovery pilot outside this mandate.
```

**JSON return to CC (manual):** When returning a portable, structured packet, use one JSON object `{"IR_CAPSULE": {...}}` containing the complete original IR capsule unchanged, including any `EVIDENCE_ANNEX` / `PILLAR_ASSESSMENTS` actually prepared. The local R1 CLI can accept that outer object under `specialist_result` beside the explicit original `request`; no autonomous Project-to-Project transport or method/source certification is implied. The dots are documentation placeholders, not valid JSON values. Do not add imaginary facts, source rights, financial scores or private account information.

**Manual operator note:** the Project-setting docs from PR #253 are candidates until actual CEO installation is confirmed. A PR link alone does not load them, and loading only this request does not load the specialist method files. The Command Center must provide the needed method text in a compact portable form when GitHub retrieval is unavailable; otherwise mark `METHOD_NOT_LOADED` and limit research to exploratory.
