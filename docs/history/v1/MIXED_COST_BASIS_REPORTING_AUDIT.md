# Mixed-currency acquisition-cost reporting audit

Date: 2026-09-05. Base: `4d64e143930948eb677a27f215a7aef3d8b43f05`
(current `main` at investigation). Phase: `VALIDATION_BASELINE_V1`.

## Diagnosis: B — conservative logic with misleading reporting

PR #22 (`cc91d992b1cb4d72eaf96f3cc17a92fa2566c0b1`) correctly preserves
account lots and prevents raw acquisition-cost addition across currencies.
The defect is the explanation in `compute_winner_protection`, not that safeguard.

Both `resolve_portfolio_rows` in `src/ticker_resolver.py` and
`merge_portfolio_rows` in `src/portfolio_loader.py` distinguish:

| Economic cost basis | `cost_basis_aggregation_status` | Aggregate cost |
| --- | --- | --- |
| One currency, valid costs | `SINGLE_CURRENCY` | Existing aggregation retained |
| No usable acquisition costs | `UNAVAILABLE` | Unavailable |
| Positive cost-bearing lots in different currencies | `MIXED_CURRENCY_UNNORMALIZED` | Unavailable |

Mixed rows also retain `cost_basis_currencies = ["CAD", "USD"]`.
Their aggregate `average_cost`, `average_cost_cad`, `acquisition_value`, and
`acquisition_value_cad` are `None`. Individual rows returned by
`resolve_portfolio_lot_rows` retain costs, currencies, and accounts.
`enrich_portfolio_with_market_data` preserves the marker and can normalize
current exposure without restoring mixed historical costs. `main.py` passes
the marker and currencies into the analysis object.

Before editing, deterministic INTU reproduction with TFSA1 CAD cost 568.87 and
TFSA2 USD cost 395.59 produced the correct mixed marker and unavailable aggregate
costs, followed by the misleading missing-cost reason. The initial 37 tests
(PR #22 mixed-cost tests, Baseline hardening, and winner protection) passed.

Exact cause: the `gain_percent is None` branch in `compute_winner_protection`
unconditionally selected the missing-cost sentence. It ignored the already
available aggregation status. The compatibility status `NO_COST_DATA` means
winner gain/protection cannot be evaluated here; this patch retains that status,
the `HOLD` action, empty signals, all numerical fields, and the existing P3 block.

## Before and after

Before, both genuinely missing costs and mixed costs said:

> Coût d’acquisition absent; remplir average_cost et average_cost_currency pour activer la protection.

After, only the existing `MIXED_CURRENCY_UNNORMALIZED` case says:

> Coût d’acquisition disponible par lot/compte, mais coût historique agrégé indisponible : devises mixtes et absence de conversion fiable aux taux de change historiques.

The missing-cost sentence and ordinary single-currency behavior are unchanged.
No manual cost re-entry is requested for valid mixed lots. This selects the reason
at its existing source; no new report dependency or formatting refactor is needed.

## Reporting surfaces traced

| Surface | How the reason reaches it |
| --- | --- |
| Compact and full Markdown/HTML, including mode-specific copies | `sell_recommendation_narrative_lines` → `_sell_position_narrative` includes the reason when an independent real sell/reduction recommendation is already present. The paragraph also discusses thesis status. |
| Full report winner-protection table | `winner_protection_rows` → `winner_rows_for_output` → `compact_winner_rows`; reason is shown if the row passes the existing display filter. `NO_COST_DATA`/`HOLD` alone normally does not qualify unless the ticker is allocated. No display filter changed. |
| Full sell-validation table and `latest_sell_validation_checklist*.csv` | `_checklist_row` → `_winner_text` copies the reason into `winner_protection_check` for rows qualifying for validation. Validation level/manual-action logic is unchanged. |
| `latest_winner_protection_report*.csv` and `latest_scores*.csv` | Existing `winner_protection_reason` column; unchanged schemas. |
| Legacy `_position_section` helper | Includes the same reason, but currently has no callers in report generation. It is not a separate active dossier surface. |

The normal compact validation summary selects higher-priority news/data checks;
it does not independently generate the missing-cost sentence. The native company
dossier builder and its CSV do not consume this reason, and the thesis-reversal
engine does not consume it. Tests confirm the company dossier is identical when
only the reason wording differs. Critical-input validation already accepts valid
explicit mixed lots and retains its failures for malformed, missing-currency,
unsupported-currency, or contradictory inputs; no validation wording changes.

## Verification

Changed files:

- `src/winner_protection_engine.py`: select the existing reason from the existing marker.
- `tests/test_mixed_cost_basis_reporting.py`: seven deterministic regression tests.
- `MIXED_COST_BASIS_REPORTING_AUDIT.md`: diagnosis, surface trace, and verification record.

New tests cover CAD-only and USD-only behavior, truly missing costs even when
account currency labels differ, mixed costs in both orders through both
aggregators, multiple current FX rates, no synthesized historical costs or gains,
unchanged winner status/action/sell overlay, conservative P3, no-position behavior,
zero-capital compact/full Markdown/HTML and CSV output, stable validation decisions,
unchanged dossier content, and preservation of synthetic archival sentinels.

Focused command, using a fresh temporary HOME:

```sh
validation_home=$(mktemp -d /tmp/mixed-cost-focused-home.XXXXXX)
env HOME="$validation_home" .venv/bin/python -m unittest tests.test_mixed_cost_basis_reporting tests.test_mixed_cost_basis_currency tests.test_baseline_hardening tests.test_winner_protection tests.test_portfolio_loader tests.test_deep_averaging_down tests.test_allocation_room_integrity tests.test_account_performance tests.test_baseline_authority_corrections tests.test_validation_architecture tests.test_sell_validation_checklist tests.test_thesis_reversal_engine tests.test_company_dossier_engine tests.test_report_generator tests.test_compact_report_portability tests.test_compact_operational_guidance -q
```

Result: **177 passed**, including all 12 PR #22 mixed-cost regression tests and
all Baseline hardening tests. Existing tests verify unrelated safe candidates
remain allocatable and generic UNKNOWN behavior is not broadened.

Canonical full suite and ancillary checks:

```sh
validation_home=$(mktemp -d /tmp/mixed-cost-full-home.XXXXXX)
env HOME="$validation_home" .venv/bin/python -m unittest discover -s tests -q
.venv/bin/python -m compileall -q main.py src scripts tests
git diff --check
.venv/bin/python main.py validate-inputs
```

- Python **3.12.14**, full suite: **909 passed** in 24.130 seconds.
- Compilation and `git diff --check`: passed.
- `validate-inputs`: failed solely because this checkout lacks `data/portfolio.csv`.
  No operational portfolio was created or modified to bypass that check.
- Additional parent-main differential: 72 deterministic winner-protection cases
  (CAD, USD, missing, mixed × three current FX rates × three existing sell actions
  × held/no-position). Only `winner_protection_reason` differed, in nine held
  mixed-cost cases. Every other field was identical to base.

## Semantic invariants

All of the following remain unchanged:

- Scoring, allocation, thresholds, candidate eligibility, and high-CAGR budget behavior.
- P3 behavior (UNKNOWN/blocked for unsafe mixed history), P4B behavior, and unrelated safe candidates.
- FX calculation methodology, historical FX handling, and portfolio normalization logic.
  Existing single-currency conversion behavior is preserved; this task adds no conversion.
- Research/data precedence, sell logic, and thesis-reversal logic.
- `MODEL_RULES_VERSION`, validation schema, Baseline identity, and Baseline eligibility.
- systemd/timers and Telegram capital-confirmation workflow.
- Historical manifests/reports, including the immutable 2026-09-01 forward observation.

The operational 2026-09-01 observation is not present in this checkout and was
neither accessed, regenerated, nor reclassified. Its remote bytes were not verified.
Archival regression checks use clearly named temporary fixtures, not a copy or
reinterpretation of that observation. Existing Baseline tests cover immutable
manifest refusal and forward-authority rules. Repository scope verification shows
no changes to `data/`, `reports/`, `config/`, `deploy/`, or any decision/validation
engine other than the explanation selection above.

No positive-capital analysis, operational data synthesis, merge, or deployment
was performed. Positive amounts inside existing unit tests remain isolated test
fixtures. The correction is submitted for review on a dedicated branch.
