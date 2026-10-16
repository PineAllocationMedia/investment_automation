# PAM Opportunity Backlog

> Ideas and opportunities, distinct from committed work.

Lifecycle:

```text
NEW
→ REVIEWED
→ PARKED / PROMOTED / REJECTED
```

Only `PROMOTED` ideas may become Work Order or roadmap candidates.

Each entry records:

- `ID`
- `TITLE`
- `SOURCE`
- `DESCRIPTION`
- `POTENTIAL VALUE`
- `ESTIMATED EFFORT`
- `DEPENDENCIES`
- `STATUS`
- `CEO DISPOSITION`

## Entries

### OPP-TECH-001 — SQLite FTS5/BM25 advisory passage retrieval

- **ID:** `OPP-TECH-001`
- **TITLE:** SQLite FTS5/BM25 advisory passage retrieval
- **SOURCE:** CEO-reviewed SEC isolated pilot and evidence handoff, 2026-10-09
- **DESCRIPTION:** Optional deterministic lexical passage retrieval for source-linked research assistance; no canonical PAM implementation exists.
- **POTENTIAL VALUE:** Fast, local and auditable first-pass retrieval over qualified document captures.
- **ESTIMATED EFFORT:** Medium
- **DEPENDENCIES:** Human passage-relevance review; issuer scoping and source-location design; licensing/provenance review; Chromebook verification; explicit implementation Work Order.
- **STATUS:** `PARKED`
- **CEO DISPOSITION:** Approved to preserve and periodically reconsider; not approved to implement.

### OPP-TECH-002 — Hypothesis property-based validation

- **ID:** `OPP-TECH-002`
- **TITLE:** Hypothesis property-based validation
- **SOURCE:** CEO technology-opportunity disposition, 2026-10-09
- **DESCRIPTION:** Conditional property-based testing for high-value invariants and adversarial state spaces.
- **POTENTIAL VALUE:** Broader deterministic defect discovery beyond curated examples.
- **ESTIMATED EFFORT:** Medium
- **DEPENDENCIES:** Narrow target contract, deterministic strategies, dependency/cost review and explicit implementation Work Order.
- **STATUS:** `PARKED`
- **CEO DISPOSITION:** Approved to preserve and periodically reconsider; not approved to implement.

### OPP-TECH-003 — MiniLM-L3 semantic retrieval challenger

- **ID:** `OPP-TECH-003`
- **TITLE:** MiniLM-L3 optional semantic retrieval challenger
- **SOURCE:** CEO technology-opportunity disposition, 2026-10-09
- **DESCRIPTION:** Optional semantic challenger to a lexical retrieval baseline; never a silent replacement or authority source.
- **POTENTIAL VALUE:** Candidate recovery where relevant passages lack direct keyword overlap.
- **ESTIMATED EFFORT:** Medium
- **DEPENDENCIES:** Human relevance judgments, model/license and recurring-inference-cost review, deterministic evaluation design and explicit implementation Work Order.
- **STATUS:** `PARKED`
- **CEO DISPOSITION:** Approved to preserve and periodically reconsider; not approved to implement.

### OPP-TECH-004 — GLEIF legal-entity evidence

- **ID:** `OPP-TECH-004`
- **TITLE:** GLEIF legal-entity evidence
- **SOURCE:** CEO technology-opportunity disposition, 2026-10-09
- **DESCRIPTION:** Potential official legal-entity evidence adapter without making LEIs universal identity.
- **POTENTIAL VALUE:** Stronger issuer and legal-entity provenance for supported jurisdictions and entities.
- **ESTIMATED EFFORT:** Medium
- **DEPENDENCIES:** Coverage, licensing/permitted-use, source semantics, source-neutral contract and explicit implementation Work Order.
- **STATUS:** `PARKED`
- **CEO DISPOSITION:** Approved to preserve and periodically reconsider; not approved to implement.

### OPP-TECH-005 — OpenFIGI security/listing identity evidence

- **ID:** `OPP-TECH-005`
- **TITLE:** OpenFIGI security/listing identity evidence
- **SOURCE:** CEO technology-opportunity disposition, 2026-10-09
- **DESCRIPTION:** Potential security/listing identity evidence source without defining core identity by one provider.
- **POTENTIAL VALUE:** Better security-class and listing resolution where supportable.
- **ESTIMATED EFFORT:** Medium
- **DEPENDENCIES:** Terms, rate limits, redistribution rights, identifier semantics, source-neutral integration and explicit implementation Work Order.
- **STATUS:** `PARKED`
- **CEO DISPOSITION:** Approved to preserve and periodically reconsider; not approved to implement.

### OPP-TECH-006 — DuckDB/Parquet historical analytics

- **ID:** `OPP-TECH-006`
- **TITLE:** DuckDB/Parquet historical analytics
- **SOURCE:** CEO technology-opportunity disposition, 2026-10-09
- **DESCRIPTION:** Optional local analytical storage/query layer for qualified historical datasets.
- **POTENTIAL VALUE:** Efficient reproducible analysis without changing evidence authority.
- **ESTIMATED EFFORT:** Medium
- **DEPENDENCIES:** Qualified historical data, PIT semantics, storage architecture, dependency/cost review and explicit implementation Work Order.
- **STATUS:** `PARKED`
- **CEO DISPOSITION:** Approved to preserve and periodically reconsider; not approved to implement.

### OPP-TECH-007 — FRED/ALFRED macroeconomic and vintage evidence

- **ID:** `OPP-TECH-007`
- **TITLE:** FRED/ALFRED macroeconomic and vintage evidence
- **SOURCE:** CEO technology-opportunity disposition, 2026-10-09
- **DESCRIPTION:** Potential official macroeconomic and vintage-aware evidence source for bounded research context.
- **POTENTIAL VALUE:** Better provenance and revision awareness for supported macro observations.
- **ESTIMATED EFFORT:** Medium
- **DEPENDENCIES:** Exact series semantics, vintage/PIT qualification, licensing/permitted-use and explicit implementation Work Order.
- **STATUS:** `PARKED`
- **CEO DISPOSITION:** Approved to preserve and periodically reconsider; not approved to implement.

### OPP-TECH-008 — Conditional NLP tooling

- **ID:** `OPP-TECH-008`
- **TITLE:** FinBERT, TinyBERT and spaCy as conditional NLP opportunities
- **SOURCE:** CEO technology-opportunity disposition, 2026-10-09
- **DESCRIPTION:** Separately assessable NLP options for bounded classification or extraction tasks; no model is selected.
- **POTENTIAL VALUE:** Potential structured assistance on text-heavy evidence workflows.
- **ESTIMATED EFFORT:** Medium / High
- **DEPENDENCIES:** Specific task and benchmark, human labels, model/license/cost review, explainability safeguards and explicit implementation Work Order.
- **STATUS:** `PARKED`
- **CEO DISPOSITION:** Approved to preserve and periodically reconsider; not approved to implement.

### OPP-TECH-009 — Targeted OCR/Tesseract improvements

- **ID:** `OPP-TECH-009`
- **TITLE:** Targeted improvements to existing OCR/Tesseract capabilities
- **SOURCE:** CEO technology-opportunity disposition, 2026-10-09
- **DESCRIPTION:** Improve selected weaknesses in PAM's existing OCR/Tesseract path; OCR capability is not absent.
- **POTENTIAL VALUE:** Better recovery and diagnostics for eligible image-based evidence.
- **ESTIMATED EFFORT:** Medium
- **DEPENDENCIES:** Measured failure corpus, accuracy review, provenance-preserving output contract and explicit implementation Work Order.
- **STATUS:** `PARKED`
- **CEO DISPOSITION:** Approved to preserve and periodically reconsider; not approved to implement.

### OPP-PROD-001 — Sector ETF opportunity and deterioration/rotation radar

- **ID:** `OPP-PROD-001`
- **TITLE:** Two-indicator research radar across 11 U.S. sector ETFs
- **SOURCE:** CEO-requested roadmap feature from a supplied exploratory AI discussion, 2026-10-16; its thresholds, examples and performance claims are unvalidated.
- **DESCRIPTION:** Distinct sector Opportunity Context and Deterioration / Rotation Review research indicators, with a compact V2 Sector Radar summary; no automatic buy/sell decisions.
- **POTENTIAL VALUE:** Compare sector valuation, quality, stress, interest-rate context and long-term opportunity cost with evidence and uncertainty visible.
- **ESTIMATED EFFORT:** High / multi-stage; exact feasibility and scope unknown.
- **DEPENDENCIES:** Future bounded Product & UX contract; qualified free/PIT sector and macro data; licensing/redistribution verification; Architecture & Audit review; out-of-sample benchmarking; CEO authorization of each implementation scope.
- **STATUS:** `PROMOTED` (roadmap candidate only; implementation `NOT AUTHORIZED`).
- **CEO DISPOSITION:** Requested future roadmap inclusion on 2026-10-16; no model-rule, trading, deployment or investment-philosophy change.
