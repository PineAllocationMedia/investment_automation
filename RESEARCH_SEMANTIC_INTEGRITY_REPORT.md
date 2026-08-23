# Pre-validation Correction 1B - Research Semantic Integrity

## A. Branch

`codex/fix-research-report-semantic-integrity`

## B. Pull request

[PR #15](https://github.com/PineAllocationMedia/investment_automation/pull/15), targeting `main`. The pull request is OPEN, UNMERGED, non-draft, and has no auto-merge request.

## C. Starting state

- Starting main SHA: `61a961fb7d303587cc9020a0db2f6855588512ba`.
- Starting `MODEL_RULES_VERSION`: `2026-08-23-provenance-freshness-confirmation-v3`.
- P1 / PR #14: verified as the starting merge commit.
- P1 predecessor contract: verified. Human, research, official, automatic, and calibration origins are distinct; stale calibration is non-authoritative; conflicts remain auditable; no research-path VRT exception exists.

## D. Root causes

| Problem | Status | Actual path and failure mechanism |
|---|---|---|
| 1. Confidence-aware application | CONFIRMED | `parse_research_report()` recorded field confidence, but `merge_research_with_automated()` applied every `research_report_fields` value, removed automatic/proxy dependencies, and let reliability count LOW fields as confirmed. |
| 2. Broker target vs intrinsic fair value | CONFIRMED | `_extract_fair_value_estimate()` deliberately added the NBF target candidate and could return it as `fair_value` when no Morningstar value existed. |
| 3. Price/FVE vs historical five-year valuation | CONFIRMED | `extract_morningstar_valuation_ok()` converted Price/FVE directly into `valuation_vs_5y_avg_ok`. |
| 4. C9/C10 double counting | CONFIRMED | The Price/FVE-derived Boolean credited C9 while intrinsic fair value independently supplied C10. |
| 5. ROIC period/definition | CONFIRMED | `ROIC_PATTERNS` found a generic ROIC number; `parse_research_report()` stored it as `roic_5y_avg`, including current/TTM broker ROIC. |
| 6. Qualitative keyword false positives | CONFIRMED | Global keyword patterns made phrases such as "regulatory risk has declined materially" produce `regulatory_risk_high=True`. |
| 7. Text/extraction quality propagation | PARTIALLY_CONFIRMED | Text quality already downgraded field confidence and reliability had a global penalty, but LOW fields were still applied, removed proxy status, and counted as reliability evidence. |
| 8. Preserve working extraction | NOT_CONFIRMED as a defect | Intrinsic fair value, structured moat precedence, grouped-number parsing, descriptive fields, and corruption guards already worked. Regression tests confirm they remain intact. |

## E. Architecture before

`load_research_report_inputs()` discovered reports and called `parse_research_report()`. `extract_report_text_detailed()` selected pypdf, PyMuPDF, or OCR and attached text-quality metadata. Parser regexes wrote manual-like canonical fields and confidence labels. `merge_research_rows()` selected multi-report values. `merge_research_with_automated()` then applied all listed research fields without enforcing confidence or semantic compatibility, removed their automatic/proxy markers, and passed them to `compute_data_reliability()` and `compute_fundamental_score()`.

## F. Architecture after

- Extraction retains every useful observation in `research_report_extracted_fields`.
- Semantic normalization routes broker targets, Price/FVE, and non-five-year ROIC to informational fields.
- `research_report_fields` contains only application-eligible canonical fields.
- `research_report_advisory_fields`, field status, reason, file, provider, source type, report date, confidence, extraction method, text quality, and OCR metadata preserve the audit trail.
- LOW fields remain advisory. MEDIUM/HIGH application follows canonical authority and cannot replace official evidence.
- Applied values remain `RESEARCH_REPORT` provenance and feed the existing reliability/scoring interfaces.
- Advisory values do not remove automatic fields or proxy corrections and do not count as confirmed reliability evidence.

No parallel provenance or reliability system was introduced.

## G. Files changed

- `src/research_reports.py`: semantic extraction, lifecycle metadata, confidence-aware application, contextual qualitative guards, and field-level audit metadata.
- `src/data_reliability_engine.py`: legacy-safe exclusion of LOW research fields from confirmed reliability evidence.
- `src/auto_fundamentals.py`: preserve research evidence entries when calibration evidence is added.
- `main.py`: export additive research audit/informational fields in analysis rows.
- `src/model_version.py`: advance the behavioral correctness version.
- `tests/test_research_reports.py`: required semantic, confidence, OCR, provenance, and scoring regressions.
- `DECISIONS.md`: record the correction, non-goals, P1 relationship, and version decision.
- `RESEARCH_SEMANTIC_INTEGRITY_REPORT.md`: this impact and review report.

## H. Functions modified or added

- `parse_research_report`
- `merge_research_rows`
- `merge_research_with_automated`
- `_extract_fair_value_estimate`
- `_extract_broker_target_price_candidate`
- `_normalized_report_currency`
- `_select_priority_research_field`
- `extract_bool_from_patterns`
- `extract_explicit_high_risk`
- `research_field_confidence`
- `extract_morningstar_valuation_ok`
- `_extract_semantic_roic_values`
- `_research_sentences`
- `_semantic_match_is_reversed`
- `compute_data_reliability`
- `_field_evidence_sources`
- `build_position_analyses` analysis-row assembly

## I. Confidence policy

- HIGH: may apply under the existing hierarchy, remains research provenance, and may reduce lower-authority proxy dependency.
- MEDIUM: applies only with clear canonical semantics and no higher-authority official evidence; remains distinguishable from HIGH.
- LOW: audit/advisory only. It cannot overwrite a proxy, remove proxy correction metadata, become confirmed evidence, improve reliability as HIGH evidence, or independently drive deterioration/allocation exceptions.

OCR/LOW text quality downgrades field confidence before application. A structured HIGH field read through OCR may become MEDIUM; a MEDIUM numeric extraction becomes LOW and advisory.

## J. Fair value and broker target

`fair_value` now accepts intrinsic-fair-value semantics only. NBF 12-month targets populate `broker_target_price_12m`, retain field-level source metadata, and remain informational. They do not fill a missing intrinsic fair value and do not receive a new score.

## K. Price/FVE and historical valuation

Morningstar Price/FVE is retained as informational `price_to_fair_value` evidence. It no longer populates `valuation_vs_5y_avg_ok`. Only explicit historical five-year valuation comparisons can populate that canonical field.

## L. C9/C10

The corrected Price/FVE pathway cannot credit C9. Intrinsic fair value may continue to affect C10 through the unchanged current-price/fair-value calculation. Scoring weights are unchanged.

## M. ROIC

Only explicit five-year-average language populates `roic_5y_avg`. Current/TTM/annual observations may populate informational `roic_current`; explicit trailing-decade observations may populate informational `roic_10y_avg`. Neither informational field enters C1.

## N. Qualitative extraction

Risk-high fields now require explicit high/elevated/material/severe semantics, evaluated at sentence level with simple negation/reversal guards. Ambiguous language returns unknown instead of a forced Boolean. Existing structured company-level moat precedence remains unchanged. This is intentionally conservative and does not attempt full natural-language understanding.

## O. Text and source quality

Field confidence reflects extraction method and text quality. Application filters use that confidence; reliability sees only applied, non-LOW research fields. Field-level evidence records file, provider, report date, confidence, status, reason, and current authority.

## P. Report examples

The active read-only operational source was located at:

`/Users/jordansoucy/Library/CloudStorage/GoogleDrive-jsoucy98@gmail.com/Mon disque/Investment_Automation/data/research_reports/bncd_morningstar/`

It contained 77 PDFs across 41 tickers: 34 Morningstar Stock Analyst Reports, 33 Morningstar Data Tear Sheets, and 10 NBF Company Reports. All 77 were copied unchanged into isolated `/private/tmp` validation directories and inspected. No Drive file was edited, renamed, deleted, or rewritten.

All 77 extracted through `pypdf`, reported `TEXT_OK`, used no OCR, and produced at least one field. The real corpus therefore did not contain a naturally LOW-text or OCR case; LOW/OCR non-authority remains covered by deterministic regression tests and the application policy.

Representative real results, without proprietary prose:

- Morningstar Analyst / AEM.TO: text quality 100, no OCR; intrinsic `fair_value=125`, company-level `moat_clear=False`, `forward_pe_manual=17`, `roic_5y_avg=10` applied; `price_to_fair_value=1.63` and `roic_10y_avg=7.5` retained as advisory with explicit semantic reasons.
- Morningstar Tear Sheet / ADBE: text quality 100, no OCR; `fair_value=380`, `moat_clear=True`, `forward_pe_manual=9.6`, and `peg_manual=0.6` applied. No historical-valuation Boolean was fabricated.
- NBF / CSU.TO: text quality 85, no OCR; `broker_target_price_12m=3700` retained as advisory with `BROKER_TARGET_NOT_INTRINSIC_FAIR_VALUE`; `forward_pe_manual=18.8` remained applied; `fair_value` was not populated by the NBF report.

Real-layout validation exposed two small general parser defects, both corrected without ticker-specific rules:

- Structured NBF headers can show a trading-currency current price, a reporting-currency equivalent, and then the target. Header-first, matching-currency selection now extracts the actual target and ignores later ratio labels such as `Target Price 1.39`.
- A sentence can contain both ten-year and five-year ROIC values. Period matching now selects the nearest percentage associated with each period, so AEM.TO correctly yields five-year 10.0 and ten-year 7.5.

Grouped values were confirmed on real layouts, including CSU.TO fair value 3,500 and NBF target 3,700. The implausible-fair-value guard remains covered by regression. Structured company-level moat was retained for all 34 Analyst reports and was not displaced by incidental text.

## Q. Controlled blast radius

Real report corpus:

- Reports available and inspected: 77 of 77.
- Tickers with reports: 41.
- Report types: 34 Analyst, 33 Tear Sheet, 10 NBF.
- Legacy extracted/applied observations: 316.
- Corrected extracted observations: 292.
- Corrected applied observations: 247.
- Corrected advisory observations: 45.
- Confidence before: LOW 29, MEDIUM 192, HIGH 95.
- Confidence after: LOW 0, MEDIUM 197, HIGH 95.
- NBF observations removed from `fair_value`: 10; actual model-wide canonical contaminations removed: 6.
- Price/FVE-to-historical-valuation mappings removed: 34; model-wide C9 inputs changed: 7.
- Legacy ROIC observations stored as five-year: 5; corrected real five-year observations: 2. Four legacy period/value mismatches were removed, while the AEM.TO five-year value was corrected from 7.5 to 10.0.
- Qualitative risk detections removed or changed: 18 (`regulatory_risk_high` 11, `geopolitical_risk_high` 6, `single_product_dependency_high` 1).

Real same-input model-wide comparison:

- Base: `61a961fb7d303587cc9020a0db2f6855588512ba`.
- Corrected: PR #15 implementation plus the two real-layout corrections above.
- Frozen inputs: identical portfolio, calibration, generated friendly/manual input, discovery universe, report corpus, and an 825-file market cache. SHA-256 manifests matched before both runs.
- Analysis path: `high-cagr`, capital 0, no independent refresh.
- Evaluated rows: 266 = 24 core + 5 watchlist + 123 market-scanner + 114 discovery.
- Report-bearing evaluated rows with material P1B differences: 41.
- Reliability changes: 25.
- Score changes: 13.
- Capital-allocation-score changes: 28.
- Conviction-score changes: 29.
- Recommendation, action, thesis, or monitoring changes: 6 tickers.
- `UNEXPECTED`: 0.

Run timestamps, fetch-attempt timestamps, and market-data age counters differed only because the two executions occurred sequentially; they were excluded from model-semantic classification. Market payloads and starting cache manifests were identical.

## R. Score and monitoring impact

| Case | Change | Classification and corrected evidence |
|---|---|---|
| MSTAR | score 9.48 -> 8.48; reliability 90/HIGH -> 85/HIGH; valuation watch NORMAL -> WATCH | `EXPECTED_VALUATION_SEMANTIC_FIX`: Price/FVE no longer supplies C9 or overwrites the existing historical-valuation input. Fair value and moat remain valid. |
| NBF | score 8.61 -> 8.48; reliability 90/HIGH -> 77/MEDIUM | `EXPECTED_BROKER_TARGET_SEPARATION` and `EXPECTED_ROIC_SEMANTIC_FIX`: target and current ROIC no longer overwrite canonical fields or remove proxy corrections. |
| RISK | score unchanged at 8.48; reliability 75/MEDIUM -> 70/MEDIUM; market watch WATCH -> NORMAL | `EXPECTED_QUALITATIVE_EXTRACTION_FIX`: reversal context removes a false positive; automatic/proxy state is retained. |

All three retained `thesis_status=INTACT` and `conviction_category=VERY_HIGH` in the controlled fixture. No recommendation change requires explanation beyond the monitoring changes above.

The three-case deterministic comparison above remains as a regression fixture. The real model-wide action changes were:

| Ticker | Before -> after | Exact semantic cause |
|---|---|---|
| ASML | allocation/final action `NO_NEW_ALLOCATION` -> `DO_NOT_ADD` | `EXPECTED_VALUATION_SEMANTIC_FIX`: Price/FVE stopped supplying C9; C9 changed True -> False, score 9.46 -> 8.46, triggering the existing excessive-valuation guard. |
| AVGO | allocation/final action `NO_NEW_ALLOCATION` -> `DO_NOT_ADD` | `EXPECTED_VALUATION_SEMANTIC_FIX`: Price/FVE stopped supplying C9; score 9.48 -> 8.48 and valuation watch changed NORMAL -> WATCH. |
| DXCM | thesis `WEAKENING` -> `INTACT`; `DO_NOT_ADD/WATCH` -> `ELIGIBLE_BUT_NOT_SELECTED` | `EXPECTED_RESEARCH_CONFIDENCE_FIX` and `EXPECTED_QUALITATIVE_EXTRACTION_FIX`: ambiguous single-product language no longer became a high-risk Boolean; report margin pressure remained auditable but advisory because higher-authority current evidence was False. |
| FNV.TO | allocation/final action `DO_NOT_ADD` -> `NO_NEW_ALLOCATION` | `EXPECTED_BROKER_TARGET_SEPARATION`: the legacy current-price-like value 235.94 stopped being fair value; NBF target 360 became advisory and automatic fair value 399.34 was restored, removing the C10 extreme-valuation failure. A regulatory keyword false positive was also removed. |
| GILD | monitoring `WATCH/WATCH_POSITION` -> `MANUAL_REVIEW/MANUAL_REVIEW_BEFORE_ADD` | `EXPECTED_RESEARCH_CONFIDENCE_FIX`: research balance-sheet=True remained auditable but non-authoritative against official/current=False; conviction changed 72 -> 67 without a score change. |
| WSP.TO | thesis `INTACT` -> `WEAKENING`; allocation `NO_NEW_ALLOCATION` -> `DO_NOT_ADD`; final action `NO_NEW_ALLOCATION` -> `WATCH` | `EXPECTED_BROKER_TARGET_SEPARATION`, `EXPECTED_ROIC_SEMANTIC_FIX`, and `EXPECTED_QUALITATIVE_EXTRACTION_FIX`: target 272 stopped populating fair value, generic ROIC 15 stopped populating five-year ROIC, automatic fair value 257.35 and ROIC 12.102 returned, and explicit real margin-pressure evidence remained applied. |

All other changed rows affected score/reliability/conviction or audit metadata without changing recommendation/action. Every changed row was classified only with the allowed P1B labels; none required historical-return optimization.

Source-conflict audit:

- 31 research-field observations across 22 tickers were correctly made advisory because higher-authority official/current evidence existed.
- Five cases had differing values: C `eps_growth_estimated_3_5y`, DXCM `margin_or_profitability_under_pressure`, GILD `balance_sheet_strong`, NEM `roic_5y_avg`, and PWR `eps_growth_estimated_3_5y`.
- In every case the research value remained in `field_evidence_sources` with file, provider, date, confidence, `currently_authoritative=False`, status, and reason; the canonical value and official source metadata remained visible.
- Broker targets, intrinsic fair values, ten-year ROIC, and five-year ROIC remained separate metrics and were not mislabeled as factual conflicts.
- No new conflict engine was required.

## S. Tests

- Dependency-complete starting baseline: 722 passed, 0 failed, 0 skipped, 22.022 seconds.
- Final complete suite after real-data validation: 734 passed, 0 failed, 0 skipped, 22.275 seconds.
- Focused research/reliability/source-conflict/scoring/P1 suite: 121 passed.
- Added tests: 12 total, including the structured multi-currency NBF header and dual-period ROIC regressions.
- `py_compile`: passed.
- `git diff --check`: passed.

An initial host-Python run lacked declared dependencies and was non-authoritative. The repository `requirements.txt` was installed into `/tmp/p1b-venv`; no dependency or environment file was changed.

## T. Versioning

- Starting `MODEL_RULES_VERSION`: `2026-08-23-provenance-freshness-confirmation-v3`.
- Ending `MODEL_RULES_VERSION`: `2026-08-23-research-semantic-integrity-v4`.
- Changed: yes, because corrected canonical inputs can validly change scores and monitoring/recommendation behavior.
- Parser/schema/cache version: no separate change. Research reports are parsed directly on each run; no parsed-research cache exists, so no invalidation or destructive cleanup is needed.
- `VALIDATION_BASELINE_V1`: not declared.

## U. Chromebook compatibility

- Google Drive paths: unchanged.
- BNCD/Morningstar folder: unchanged.
- Telegram: unchanged.
- systemd and production scheduling: unchanged.
- CLI and mandatory flags: unchanged.
- Portfolio, manual-input, calibration, reporting, compact-report, history, maintenance, and refresh workflows: unchanged.
- New dependencies/network services: none.
- Eventual deployment: update code normally; future runs reparse reports with corrected semantics. No history rewrite or arbitrary cache deletion is required.

Nothing was deployed or pulled onto the Chromebook.

## V. Remaining risks

- The conservative regex policy can produce false negatives for unusual report wording; missing is preferred to semantically wrong data.
- The 77-file real corpus contained no naturally poor-text or OCR report, so that pathway remains validated by deterministic tests rather than a real OCR specimen.
- Field-level metadata is additive and backward compatible, but external consumers that assumed every extracted observation lived in `research_report_fields` should use `research_report_extracted_fields` for audit inventory.

## W. Successor compatibility

- Special P1B API required by later chantiers: no.
- Research-only reliability taxonomy introduced: no.
- Existing `data_reliability` output remains canonical: yes.
- Existing scoring fields retain canonical meaning: yes, with corrected inputs.
- Mandatory configuration/workflow changes: no.
- New investment factor, scoring weight, allocation threshold, or portfolio-construction rule: no.
- Later chantiers can consume the normal provenance/reliability/scoring interfaces: yes.

## X. Confidence

HIGH. All 77 available operational PDFs were inspected, the real complete-universe comparison used identical frozen inputs and market data, every model difference was classified, `UNEXPECTED=0`, source conflicts remained auditable, and the complete 734-test suite passed. The absence of a naturally poor-text/OCR report remains a bounded residual risk covered by deterministic tests.

## Y. Merge recommendation

`READY_FOR_EXTERNAL_REVIEW`

Do not merge or deploy until the external reviewer accepts this real-PDF and model-wide validation update.

## Z. Real complete-universe classification table

`-` means the field did not change. All classifications are from the acceptance list; `UNEXPECTED=0`.

| Universe | Ticker | Classification(s) | Score | Reliability | Recommendation/action |
|---|---|---|---:|---:|---|
| CORE | ANET | `EXPECTED_VALUATION_SEMANTIC_FIX`; `EXPECTED_RESEARCH_CONFIDENCE_FIX`; `EXPECTED_RELIABILITY_FIX` | 8.28 -> 7.28 | 84.62 -> 89.62 | - |
| CORE | APH | `EXPECTED_VALUATION_SEMANTIC_FIX` | 8.84 -> 7.84 | - | - |
| CORE | APP | `EXPECTED_VALUATION_SEMANTIC_FIX`; `EXPECTED_RESEARCH_CONFIDENCE_FIX` | - | - | - |
| CORE | ASML | `EXPECTED_VALUATION_SEMANTIC_FIX` | 9.46 -> 8.46 | - | `NO_NEW_ALLOCATION` -> `DO_NOT_ADD` |
| CORE | AVGO | `EXPECTED_VALUATION_SEMANTIC_FIX`; `EXPECTED_RELIABILITY_FIX` | 9.48 -> 8.48 | 83.0 -> 88.0 | `NO_NEW_ALLOCATION` -> `DO_NOT_ADD` |
| CORE | BAM | `EXPECTED_VALUATION_SEMANTIC_FIX`; `EXPECTED_ROIC_SEMANTIC_FIX`; `EXPECTED_RESEARCH_CONFIDENCE_FIX`; `EXPECTED_RELIABILITY_FIX` | - | 89.06 -> 94.06 | - |
| CORE | CBOE | `EXPECTED_VALUATION_SEMANTIC_FIX`; `EXPECTED_RESEARCH_CONFIDENCE_FIX` | - | - | - |
| WATCHLIST | CSU.TO | `EXPECTED_BROKER_TARGET_SEPARATION`; `EXPECTED_VALUATION_SEMANTIC_FIX`; `EXPECTED_QUALITATIVE_EXTRACTION_FIX` | - | - | - |
| WATCHLIST | WSP.TO | `EXPECTED_BROKER_TARGET_SEPARATION`; `EXPECTED_ROIC_SEMANTIC_FIX`; `EXPECTED_QUALITATIVE_EXTRACTION_FIX`; `EXPECTED_RELIABILITY_FIX` | 5.33 -> 4.93 | 68.0 -> 66.0 | thesis `INTACT` -> `WEAKENING`; allocation `NO_NEW_ALLOCATION` -> `DO_NOT_ADD`; final `NO_NEW_ALLOCATION` -> `WATCH` |
| MARKET | ADBE | `EXPECTED_VALUATION_SEMANTIC_FIX`; `EXPECTED_RESEARCH_CONFIDENCE_FIX` | - | - | - |
| MARKET | ADI | `EXPECTED_VALUATION_SEMANTIC_FIX`; `EXPECTED_RESEARCH_CONFIDENCE_FIX`; `EXPECTED_RELIABILITY_FIX` | - | 88.0 -> 93.0 | - |
| MARKET | AEM.TO | `EXPECTED_BROKER_TARGET_SEPARATION`; `EXPECTED_VALUATION_SEMANTIC_FIX`; `EXPECTED_ROIC_SEMANTIC_FIX`; `EXPECTED_QUALITATIVE_EXTRACTION_FIX` | 5.85 -> 7.35 | - | - |
| MARKET | AIR.PA | `EXPECTED_VALUATION_SEMANTIC_FIX`; `EXPECTED_RELIABILITY_FIX` | - | 84.0 -> 95.0 | - |
| MARKET | ALNY | `EXPECTED_VALUATION_SEMANTIC_FIX`; `EXPECTED_ROIC_SEMANTIC_FIX` | 7.42 -> 7.03 | - | - |
| MARKET | AMAT | `EXPECTED_VALUATION_SEMANTIC_FIX`; `EXPECTED_QUALITATIVE_EXTRACTION_FIX`; `EXPECTED_RESEARCH_CONFIDENCE_FIX` | - | - | - |
| MARKET | BKNG | `EXPECTED_VALUATION_SEMANTIC_FIX`; `EXPECTED_RESEARCH_CONFIDENCE_FIX` | - | - | - |
| MARKET | BX | `EXPECTED_VALUATION_SEMANTIC_FIX`; `EXPECTED_RESEARCH_CONFIDENCE_FIX`; `EXPECTED_RELIABILITY_FIX` | - | 88.0 -> 93.0 | - |
| MARKET | C | `EXPECTED_VALUATION_SEMANTIC_FIX`; `EXPECTED_RESEARCH_CONFIDENCE_FIX` | 8.47 -> 8.71 | - | - |
| MARKET | CS.TO | `EXPECTED_BROKER_TARGET_SEPARATION`; `EXPECTED_QUALITATIVE_EXTRACTION_FIX`; `EXPECTED_RELIABILITY_FIX` | - | 95.0 -> 92.0 | - |
| MARKET | CSGP | `EXPECTED_VALUATION_SEMANTIC_FIX`; `EXPECTED_RESEARCH_CONFIDENCE_FIX`; `EXPECTED_RELIABILITY_FIX` | - | 84.0 -> 89.0 | - |
| MARKET | DDOG | `EXPECTED_VALUATION_SEMANTIC_FIX`; `EXPECTED_RELIABILITY_FIX` | - | 84.0 -> 89.0 | - |
| MARKET | DXCM | `EXPECTED_VALUATION_SEMANTIC_FIX`; `EXPECTED_QUALITATIVE_EXTRACTION_FIX`; `EXPECTED_RESEARCH_CONFIDENCE_FIX` | - | - | thesis `WEAKENING` -> `INTACT`; `DO_NOT_ADD/WATCH` -> `ELIGIBLE_BUT_NOT_SELECTED` |
| MARKET | FNV.TO | `EXPECTED_BROKER_TARGET_SEPARATION`; `EXPECTED_QUALITATIVE_EXTRACTION_FIX`; `EXPECTED_RELIABILITY_FIX` | 8.15 -> 9.15 | 95.0 -> 92.0 | `DO_NOT_ADD` -> `NO_NEW_ALLOCATION` |
| MARKET | FTNT | `EXPECTED_VALUATION_SEMANTIC_FIX`; `EXPECTED_RESEARCH_CONFIDENCE_FIX`; `EXPECTED_RELIABILITY_FIX` | - | 88.88 -> 93.88 | - |
| MARKET | FTV | `EXPECTED_RESEARCH_CONFIDENCE_FIX` | - | - | - |
| MARKET | GFL.TO | `EXPECTED_BROKER_TARGET_SEPARATION`; `EXPECTED_QUALITATIVE_EXTRACTION_FIX`; `EXPECTED_RELIABILITY_FIX` | 3.18 -> 2.18 | 91.0 -> 88.0 | - |
| MARKET | GILD | `EXPECTED_VALUATION_SEMANTIC_FIX`; `EXPECTED_RESEARCH_CONFIDENCE_FIX` | - | - | monitoring `WATCH` -> `MANUAL_REVIEW` |
| MARKET | GWO.TO | `EXPECTED_BROKER_TARGET_SEPARATION`; `EXPECTED_VALUATION_SEMANTIC_FIX`; `EXPECTED_QUALITATIVE_EXTRACTION_FIX`; `EXPECTED_RELIABILITY_FIX` | 6.53 -> 7.53 | 84.0 -> 95.0 | - |
| MARKET | HPS-A.TO | `EXPECTED_BROKER_TARGET_SEPARATION`; `EXPECTED_QUALITATIVE_EXTRACTION_FIX`; `EXPECTED_RELIABILITY_FIX` | - | 91.0 -> 88.0 | - |
| MARKET | KLAC | `EXPECTED_VALUATION_SEMANTIC_FIX`; `EXPECTED_QUALITATIVE_EXTRACTION_FIX`; `EXPECTED_RESEARCH_CONFIDENCE_FIX`; `EXPECTED_RELIABILITY_FIX` | - | 88.0 -> 93.0 | - |
| MARKET | MFC.TO | `EXPECTED_BROKER_TARGET_SEPARATION`; `EXPECTED_VALUATION_SEMANTIC_FIX`; `EXPECTED_QUALITATIVE_EXTRACTION_FIX`; `EXPECTED_RELIABILITY_FIX` | - | 84.0 -> 95.0 | - |
| MARKET | MG.TO | `EXPECTED_VALUATION_SEMANTIC_FIX`; `EXPECTED_RELIABILITY_FIX` | - | 80.0 -> 91.0 | - |
| MARKET | MRK | `EXPECTED_VALUATION_SEMANTIC_FIX`; `EXPECTED_RESEARCH_CONFIDENCE_FIX`; `EXPECTED_RELIABILITY_FIX` | - | 84.31 -> 89.31 | - |
| MARKET | MU | `EXPECTED_VALUATION_SEMANTIC_FIX`; `EXPECTED_RESEARCH_CONFIDENCE_FIX` | - | - | - |
| MARKET | NEM | `EXPECTED_VALUATION_SEMANTIC_FIX`; `EXPECTED_ROIC_SEMANTIC_FIX`; `EXPECTED_QUALITATIVE_EXTRACTION_FIX`; `EXPECTED_RESEARCH_CONFIDENCE_FIX`; `EXPECTED_RELIABILITY_FIX` | 6.4 -> 8.0 | 88.0 -> 93.0 | - |
| MARKET | NTR.TO | `EXPECTED_VALUATION_SEMANTIC_FIX`; `EXPECTED_RELIABILITY_FIX` | - | 84.0 -> 95.0 | - |
| MARKET | NVDA | `EXPECTED_VALUATION_SEMANTIC_FIX`; `EXPECTED_QUALITATIVE_EXTRACTION_FIX`; `EXPECTED_RESEARCH_CONFIDENCE_FIX`; `EXPECTED_RELIABILITY_FIX` | - | 88.69 -> 93.69 | - |
| MARKET | PWR | `EXPECTED_VALUATION_SEMANTIC_FIX`; `EXPECTED_RESEARCH_CONFIDENCE_FIX`; `EXPECTED_RELIABILITY_FIX` | 3.08 -> 3.18 | 84.5 -> 89.5 | - |
| MARKET | STN.TO | `EXPECTED_BROKER_TARGET_SEPARATION`; `EXPECTED_QUALITATIVE_EXTRACTION_FIX`; `EXPECTED_RELIABILITY_FIX` | - | 85.0 -> 82.0 | - |
| MARKET | UNH | `EXPECTED_VALUATION_SEMANTIC_FIX`; `EXPECTED_QUALITATIVE_EXTRACTION_FIX`; `EXPECTED_RESEARCH_CONFIDENCE_FIX`; `EXPECTED_RELIABILITY_FIX` | - | 84.0 -> 89.0 | - |
| DISCOVERY | SCHW | `EXPECTED_VALUATION_SEMANTIC_FIX`; `EXPECTED_RESEARCH_CONFIDENCE_FIX` | - | - | - |
