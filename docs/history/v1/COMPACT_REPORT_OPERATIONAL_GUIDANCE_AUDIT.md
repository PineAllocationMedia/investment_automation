# Compact report operational guidance — Baseline V1

Investigated against production `c63fa13c1ae4ff822d9c8f64b53a8b159ea8df30`
for the reported 2026-09-05 zero-capital run. This is a source-level investigation
with synthetic regression fixtures, not a replay of production history.

## Diagnosis before implementation

All three findings are **B: correct underlying logic with misleading reporting**.

1. **Walk-forward:** `main.py:run_analysis` reads the walk-forward signal before
   report generation. `scripts/run_investment_analysis.sh` subsequently runs
   `walk-forward-backtest` for the same mode after successful analysis and a
   nonempty compact Markdown report. Its failure is reported in the runner log
   and completion notification; it does not invalidate the analysis report.
   `src/walk_forward_signal_engine.py` correctly describes the existing artifact
   under its current thresholds. A dormant signal counts simulated periods; it
   does not prove that automation failed to run. The compact triage formatter
   nevertheless turned dormancy into a required manual command. Re-execution
   alone cannot guarantee more eligible evidence.
2. **Audits:** `scripts/run_scheduled_maintenance.py:due_audit_commands` selects
   a full audit when absent/stale, otherwise a due model audit. Maintenance runs
   it only after successful input prerequisites and health-check. Staleness is
   a current artifact fact, not proof that maintenance is broken or a manual
   launch is required. The compact health formatter reused standalone signal
   messages containing manual commands. The full audit takes precedence over
   the model audit; they are not promised as two separate pending jobs.
3. **Confidence:** `src/decision_quality_engine.py:compute_decision_quality`
   explicitly returns HIGH/100 when total allocated capital is zero, with
   `data_quality_status`, `stability_status`, and `sensitivity_status` all
   `NOT_APPLICABLE`. The sensitivity engine skips zero-capital scenarios.
   Existing compact explanation text already recognizes non-applicability,
   but `_decision_quality_line` still prepended HIGH/100. This is a fallback
   value, not an observed 100% probability that the investment conclusions are
   correct, nor a computed allocation-sensitivity result.

## Reporting corrections

- Remove walk-forward from required triage actions. Preserve its status and
  artifact facts in model health, removing legacy launch advice before text
  truncation. Also remove the healthy signal's “next execution in ~21 days”
  wording: that threshold does not describe the production runner's schedule.
- Explain that, with the production runner, walk-forward is planned after
  report generation and the displayed artifact status is not that step's
  result. Direct result checks to the run log/notification without claiming
  success or promising more simulated periods.
- Explain scheduled maintenance ownership, full/model precedence, prerequisites,
  and failure follow-up. Strip legacy manual audit-launch advice from compact
  status text. Descriptions are explicitly conditional on the production
  workflow; a standalone report does not establish that automation is active.
- Display `Confiance : N/A` for the existing non-applicable decision-quality
  marker, with an explanation that zero-capital monitoring does not measure
  certainty in investment conclusions. Missing quality remains N/D; applicable
  quality scores retain their current display. Non-applicable sensitivity alone
  does not suppress an otherwise applicable decision-quality score.

Signal payloads, CLI command metadata, raw quality scores, full-report numeric
tables, and machine-readable evidence remain unchanged. Implementation is
confined to `src/report_formatters.py`. No investment policy, allocation,
threshold, methodology, cadence, timer, eligibility, or version changes are
included. No historical reports or manifests are edited.

## Regression verification

`tests/test_compact_operational_guidance.py` exercises real signal readers on
temporary mode-specific artifacts (absent, unreadable, dormant, early, healthy,
and stale); maintenance planning ownership; and zero-capital compact Markdown
and HTML generation, including the mode-specific delivery copies. It verifies
that reporting does not mutate signal or allocation payloads. Existing runner
tests cover ordering, analysis/report failures, and walk-forward failure
notification; maintenance tests cover due selection and health-check failure.

Run focused tests and the canonical complete suite using the Python 3.12 venv
and a fresh temporary HOME for each invocation:

```sh
test_home=$(mktemp -d /tmp/compact-guidance-tests-home.XXXXXX)
env HOME="$test_home" .venv/bin/python -m unittest discover -s tests -q
.venv/bin/python -m compileall -q main.py src scripts tests
git diff --check
```

No positive-capital analysis command is required or run. Positive amounts in
existing unit tests are isolated synthetic fixtures, not production analyses.

Verification on 2026-09-05: 93 focused tests passed; the complete isolated-HOME
suite passed all 902 tests on Python 3.12.14. Compilation and whitespace checks
passed. `main.py validate-inputs` was attempted but failed because this local
checkout does not contain `data/portfolio.csv`; no operational inputs were
created or replaced to bypass that missing-input check.
