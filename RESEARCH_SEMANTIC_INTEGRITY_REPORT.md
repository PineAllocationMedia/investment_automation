# Pre-validation Correction 1B - Research Semantic Integrity

## A. Branch

`codex/fix-research-report-semantic-integrity`

## B. Pull request

To be populated after the branch is pushed. The pull request must remain unmerged.

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

No proprietary PDFs were available in `data/research_reports/bncd_morningstar/`; the directory contained only `README.md`. No report was modified or reproduced. Stable representative cases matching the documented Morningstar analyst and NBF layouts were therefore used:

- Morningstar: intrinsic fair value 3,600 and Narrow moat remain applied; Price/FVE 0.73 becomes advisory and no longer populates historical valuation.
- NBF: target 3,400 remains visible as `broker_target_price_12m`; ROIC 23% remains visible as `roic_current`; neither replaces `fair_value` or `roic_5y_avg`.
- Qualitative: "regulatory risk has declined materially" no longer creates a high-risk Boolean.

Real-PDF validation remains an explicit post-review risk because the ignored operational report set was unavailable in this workspace.

## Q. Controlled blast radius

Real local operational corpus:

- Reports inspected: 0 (none available).
- Tickers with local research reports: 0.

Identical-input representative corpus:

- Cases/tickers: 3.
- Extracted fields: 7 before, 6 after.
- Applied fields: 7 before, 3 after.
- Advisory fields: 0 before, 3 after.
- LOW-confidence fields applied before: 3; applied after: 0.
- Changed to advisory-only semantic fields: 3.
- Broker targets previously capable of entering `fair_value`: 1.
- Price/FVE mappings previously affecting historical valuation: 1.
- ROIC-period mismatches: 1.
- Qualitative detections changed: 1.
- Reliability changes: 3 cases.
- Score changes: 2 cases.
- Thesis-status changes: 0.
- Conviction-category changes: 0.
- Allocation/recommendation changes: not applicable without operational portfolio inputs; none were fabricated.

Every observed difference matched an expected correction; unresolved unexpected drift: 0.

## R. Score and monitoring impact

| Case | Change | Classification and corrected evidence |
|---|---|---|
| MSTAR | score 9.48 -> 8.48; reliability 90/HIGH -> 85/HIGH; valuation watch NORMAL -> WATCH | `EXPECTED_VALUATION_SEMANTIC_FIX`: Price/FVE no longer supplies C9 or overwrites the existing historical-valuation input. Fair value and moat remain valid. |
| NBF | score 8.61 -> 8.48; reliability 90/HIGH -> 77/MEDIUM | `EXPECTED_BROKER_TARGET_SEPARATION` and `EXPECTED_ROIC_SEMANTIC_FIX`: target and current ROIC no longer overwrite canonical fields or remove proxy corrections. |
| RISK | score unchanged at 8.48; reliability 75/MEDIUM -> 70/MEDIUM; market watch WATCH -> NORMAL | `EXPECTED_QUALITATIVE_EXTRACTION_FIX`: reversal context removes a false positive; automatic/proxy state is retained. |

All three retained `thesis_status=INTACT` and `conviction_category=VERY_HIGH` in the controlled fixture. No recommendation change requires explanation beyond the monitoring changes above.

## S. Tests

- Dependency-complete starting baseline: 722 passed, 0 failed, 0 skipped, 22.022 seconds.
- Final complete suite: 732 passed, 0 failed, 0 skipped, 21.364 seconds.
- Focused research/reliability/source-conflict/scoring/P1 suite: 96 passed.
- Added tests: 10.
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
- Real proprietary PDFs were unavailable for branch validation, so representative fixtures cannot prove every PDF layout.
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

MEDIUM. The code paths, controlled before/after results, and 732-test suite strongly support closure of the confirmed defects. Confidence is not rated HIGH because representative real PDFs were absent from this workspace.

## Y. Merge recommendation

`READY_FOR_EXTERNAL_REVIEW`

Do not merge or deploy until external review includes representative real Morningstar analyst, Morningstar tear-sheet, and NBF reports.
