# V2 PR1 — runtime isolation infrastructure

## Diagnosis and scope

Verified base: `c5fc27c82c29c2a6027eccee245098c4a072fdf1` on both
`model-v2/expected-return-challenger` and its fetched origin reference. The annotated
preservation tag `baseline-v1/pre-v2-2026-09-05-c5fc27c` peels to the same commit.
The dedicated V2 worktree was clean before creating `codex/v2-runtime-isolation`.

Architectural classification: **D — mixed**. Source-relative runtime paths were
expected in the single-runtime V1 application, but defective for dual-model
operation. Independent reconstructions bypassed the common constants; shell and
Python operational scripts additionally used shared HOME state and user-supplied
production paths. A second worktree or a changed HOME alone was insufficient.

The static audit covered all Python files in `src/`, `main.py`, and the Python and
shell entry points in `scripts/`, plus the systemd templates (read only). It examined
path constants, `__file__` and parent-derived paths, HOME/environment defaults,
file opens, directory creation, atomic replacements, serialization, copies,
removals, native PDF readers, provider caches and operational subprocesses.
The locked yfinance cache implementation was also inspected locally.

Path classes used below are separate from the architectural diagnosis:
**A** code/static configuration; **B** immutable read-only inputs;
**C** mutable runtime state; **D** external production-sensitive state.
Working CSVs and research files are conservatively C even if tracked: this PR
never implicitly seeds or shares them between runtimes.

## Runtime contract

Without either runtime override, existing V1 paths, configuration, environment,
explicit function arguments and decision behavior are preserved. Merely importing
the runtime context creates no directories or files.

`INVESTMENT_AUTOMATION_RUNTIME_ROOT=/absolute/path` enables the restricted profile.
Alternatively, `INVESTMENT_AUTOMATION_RUNTIME_PROFILE=v2-restricted` selects the
default `$HOME/.local/state/investment_automation_v2`. Unknown profiles, relative
roots and a V1 profile combined with an override are errors. The profile is fixed
before application imports; changing it in a live interpreter is unsupported.

The explicit launcher is:

```sh
.venv/bin/python -B scripts/run_v2.py --runtime-root /absolute/isolated/root runtime-info
```

`runtime-info` prints only code root, effective runtime root and profile. It creates
nothing and does not add manifest fields or validation authority. Other permitted
`main.py` commands use the same context. Missing inputs remain missing: no portfolio
or production observation is fabricated. Do not copy live production data into a
V2 runtime as an implicit setup step.

The root's parent must already exist. Runtime initialization creates only children
of the authorized root, never missing ancestors outside it. Use `-B` for restricted Python library imports. The launcher and direct main CLI
disable bytecode before application imports; production scripts reject the profile
before application imports. Direct CLI use without `-B` is regression-tested.
A Python process cannot intercept interpreter activity before its first import.

The context retains the code/config root, redirects `data`, `reports` and `backups`,
and derives `home`, `cache`, `state`, `logs`, `locks` and `tmp` beneath the runtime
root. HOME and XDG cache/state/config/data variables are reset before application
imports. Temporary files use the isolated `tmp` directory. yfinance timezone,
cookie and ISIN SQLite caches explicitly use `<root>/cache/yfinance` at each
application yfinance entry point. macOS provider HOME caches are isolated as well.

The launcher/profile retains only PATH, locale, timezone and platform essentials;
it removes inherited production variables and credentials, including Telegram,
provider keys, input source/config, project/log/lock overrides, proxy credentials
and Baseline-start overrides. Production paths are captured for rejection before
that environment is cleared.

## Production rejection and guard

Canonical overlap is checked in both directions using resolved path ancestry.
Forbidden roots include the current code tree, the main checkout and other linked
checkouts discovered through Git's worktree metadata, original HOME operational
state/log/config/provider-cache directories, inherited XDG cache/app-state roots,
macOS CloudStorage, configured input/Drive sources,
and production project/log/lock and operational config overrides. The input-sync config file is read only
to discover its source root; it is never sourced as shell code or modified.

Additional production-sensitive locations must be declared explicitly with
`INVESTMENT_AUTOMATION_FORBIDDEN_ROOTS` (OS path-separator list), or repeated
`--forbid-root /absolute/production/path` launcher arguments. This is a safety list,
not another mutable-state override. Unknown external production installations
cannot be discovered automatically.

The existing runtime tree is validated before initialization writes. Existing
symlink escapes and hard links are rejected. A restricted process audit hook checks
Python file opens, directory mutations, replacements, removals and SQLite opens;
it rejects explicit output overrides outside the root and rechecks paths at I/O,
including symlinks introduced after startup. External mutable reads are rejected;
code, dependencies and OS read-only resources remain available. Native PDF inputs
are checked before PyMuPDF/OCR access. Runtime symlink/hard-link creation is denied.

This is an accidental-I/O boundary for the audited application, **not an OS sandbox
for hostile Python/native code**. It does not claim protection against an attacker
racing filesystem operations or supplying pre-opened external descriptors. Do not
run untrusted extensions inside this process. Audited native provider writes are
contained by explicit cache location and isolated HOME/temp configuration.

Production input sync, automatic portfolio sync, scheduled maintenance, Telegram
notification/confirmation, systemd installation, deployment update and the shell
production runner are rejected at entry, before credentials or mutation. Direct
imports of these operational Python scripts are rejected too. CLI/direct analysis
rejects nonzero capital and genuine scheduled/manual decision purposes in restricted
mode. Initialization/template export, portfolio sync and tuning-application commands
are disabled. Local manual-input sync remains limited to isolated files.

External subprocesses are disabled because Python filesystem guards do not follow
them. Consequently restricted Git provenance reports its existing unavailable
status, and optional subprocess-based OCR cannot run. These restrictions do not
change V1 behavior or the validation rules that interpret unavailable provenance.

## Writer and reader coverage

Here `R` means the isolated runtime root and `P` the source/config checkout.
“Blocked” is an intentional fail-closed restriction, not an unresolved writer.

| Audited family and important constructors/writers | Class | Restricted disposition |
| --- | --- | --- |
| Source, dependency lock, static `config/*.yaml`; `utils`, model tuning/config loaders, critical config audit | A | Read from P; writes blocked. No config/weight/version changes. |
| Reviewed immutable inputs | B | No new implicit sharing. Static test fixtures are read only; mutable data and research must be separately provisioned. |
| Portfolio CSVs, transactions, account locations, working snapshots, inferred transactions, account performance; `main`, portfolio loader/change/performance/sync engines | C | R/data; production sync entry points blocked. |
| Main/latest/mode reports, HTML, CSV, SVG charts and embedded report assets; report generator/formatters, mode artifacts, account charts | C | R/reports; direct writes/copies/removals guarded. Formatter calibration/research reads redirected. |
| Analysis, allocation, audit history; history/allocation-change/audit-snapshot engines | C | R/reports/history. |
| Decision manifests, latest manifest; decision manifest engine | C | R/reports/decision_manifests and R/reports. Input fingerprints read R/data; logical names stay `data/...`; config fingerprints read P/config. |
| Failed-run audits and crash/run diagnostics; decision manifest engine, main emergency writer | C | R/reports/failed_run_audits and R/reports. |
| Universe snapshots; run logging engine | C | R/reports/universe_snapshots. |
| Walk-forward/backtest reports, inventories, simulated periods and price history; backtest and walk-forward engines | C | R/reports and R/data cache. Sibling report lookup stays inside R. |
| Market, fundamental, FX, benchmark, last-known-good caches; market/official/Canadian fetchers | C | R/data/cached_market_data and subdirectories. |
| Instrument profile, external profile, public source caches; instrument profile engine and provider clients | C | R/data/cached_market_data subdirectories. |
| Cache quarantine, replacement, maintenance, stale deletion; cache management engine | C | R/data/cached_market_data; guard applies to rename/unlink. |
| Research reports/index/scaffold and derived manual inputs/sync log; research reports/manual input sync | C | R/data/research_reports and R/data. Native PDF reads checked; no live research directory is shared. |
| Calibration and proxy correction history; proxy calibration/correction engines | C | R/data; static correction settings stay in P/config and cannot be mutated. |
| Ticker memory, watchlist, scanner/discovery cache; ticker memory/discovery/scanner engines | C | R/data. Selection rules unchanged. |
| Source health, anomalies, structured run histories; source health/anomaly/run logging engines | C | R/data and R/reports. |
| Tuning proposals/history; model improvement/model tuning engines | C/A | Proposals/history resolve inside R; config stays read only. Tuning application disabled. |
| Project backup, inventory; backup engine, main backup commands | C | R/backups, capturing R state, excluding backups themselves. V1 still backs up its original project tree. |
| CSV repair backups and diagnostic reports; CSV schema/health engines, diagnostic scripts | C | R/data/repair_backups and R/reports/diagnostics. Schema/health readers use R/data while dependency/config checks use P. |
| HOME `.local/state/investment_automation`, operations lock, portfolio-sync marker, input backups | D | Production operational entry points blocked; isolated HOME/XDG and R/state/R/locks are available for future local runtime operations. |
| HOME `investment_automation_run_logs`, log retention/deletion and log override; shell runner/storage observability | D | Production runner blocked; storage diagnostics inspect R/logs. |
| yfinance timezone/cookie/ISIN SQLite/WAL/cache state and other HOME/XDG provider caches | C/D | Explicit R/cache/yfinance; HOME/XDG beneath R. Isolated provider database creation tested without network. |
| Temporary/atomic files, permission probes and locks | C | Destination-relative atomic files plus R/tmp; guarded opens/mkdir/rename/remove. |
| Production Drive/input roots, credential files, portfolio staging/copies and synchronization state | D | Captured as forbidden; operational sync modules blocked before I/O. No read/write sharing. |
| Systemd units, scheduled/manual production runner, Telegram, deployment/Git updates | D | Restricted entry points blocked. Production templates and installed units unchanged. |

No audited mutable writer remains unresolved for the supported restricted execution
path. Functions that accept explicit paths are guarded in addition to redirected
defaults; native provider caches and PDF readers receive explicit handling.

## Changed files

| File | Exact infrastructure change |
| --- | --- |
| `src/runtime_context.py` | New immutable context, canonical root validation, production-root discovery, environment setup, filesystem guard, restrictions and provider cache setup. |
| `src/__init__.py` | Activate the opt-in profile before submodule imports. |
| `src/utils.py` | Import canonical roots; derive data/report defaults; avoid mkdir on static config under restriction. No new utility functions. |
| `main.py` | Runtime-info diagnostic, early CLI/direct operation checks, prepare isolated infrastructure directories, route backup inventory. |
| `src/validators.py` | Resolve input CSV directory through runtime context. |
| `src/csv_schema_engine.py` | Resolve schema inspection/repair data root through context. |
| `src/critical_input_engine.py` | Resolve portfolio audit input under runtime data; config/rules unchanged. |
| `src/health_check_engine.py` | Route mutable data/report/cache/research probes; retain code/config/dependency checks. |
| `src/storage_observability_engine.py` | Inspect isolated state/cache/history/log roots under restriction. |
| `src/decision_manifest_engine.py` | Fingerprint isolated working inputs; preserve logical input names and existing schema/authority. |
| `src/report_formatters.py` | Replace two source-relative mutable research/calibration readers. |
| `src/research_reports.py` | Validate restricted native PDF input paths before extraction. |
| `src/data_fetcher.py` | Configure isolated yfinance caches before its two provider call paths. |
| `src/backtest_engine.py` | Configure isolated yfinance cache before backtest price download. |
| `src/backup_engine.py` | Route restricted backup source/destination/inventory to runtime state. |
| `scripts/run_v2.py` | Explicit restricted in-process launcher with root and forbidden-root arguments. |
| `scripts/run_investment_analysis.sh` | Reject restricted mode before shell production operations. |
| `scripts/telegram_notify.py` | Reject restricted operational module before credentials/default paths. |
| `scripts/request_telegram_analysis.py` | Reject restricted operational module before Telegram imports/actions. |
| `scripts/sync_operational_inputs.py` | Reject restricted operational module before source/config/copy activity. |
| `scripts/run_automatic_portfolio_sync.py` | Reject restricted operational module before portfolio state/staging. |
| `scripts/run_scheduled_maintenance.py` | Reject restricted operational module before scheduled operations. |
| `scripts/install_systemd_automation.py` | Reject restricted operational module before installation. |
| `scripts/update_deployment_code.py` | Reject restricted operational module before deployment update. |
| `scripts/run_isolated_tests.py` | Python 3.12 test harness using disposable code/config and HOME/XDG/temp, no working data copy or credentials, network denied; a disposable code-only Git fixture supports the existing SHA regression. |
| `tests/test_runtime_isolation.py` | Subprocess path compatibility, writer coverage, unsafe configuration/operation, native cache and deterministic equivalence regressions. |
| `RUNTIME_ISOLATION_PR1.md` | Diagnosis, writer map, usage, limits and validation evidence. |

## Semantic and authority invariants

No intentional changes to scoring/score_total, conviction, CAGR classification,
valuation, VFV, opportunity cost, eligibility, liquidation, P3/P4B, sizing,
allocation, concentration, tax/friction, scanner/discovery selection, weights,
thresholds, MODEL_RULES_VERSION, VALIDATION_BASELINE_V1, validation schema or
walk-forward authority. No new factors, scores or tuning. The changed critical
input/manifest code only separates runtime input paths from static config paths.

## Validation evidence

Reproducible suite commands:

```sh
.venv/bin/python -B scripts/run_isolated_tests.py --pattern test_runtime_isolation.py
.venv/bin/python -B scripts/run_isolated_tests.py
git diff --check
```

The complete suite deliberately runs in default V1 mode in a disposable code tree
so legacy compatibility remains exercised. Its restricted regressions launch fresh
subprocesses with the runtime environment established before application imports.
The harness copies only code/config/tests, never operational data/history or
credentials. It creates its own code-only Git fixture for the existing repository-SHA
regression; it does not copy the project Git database. Existing operational tests use their own fake commands/temporary
fixtures. The equivalence fixture calls pure score/allocation functions in memory;
it never calls `run_analysis` or writes a decision observation.


Final local verification used Python **3.12.14** and all distributions matched
`requirements.lock` exactly. The existing `.python-version` (3.12.13), lock and CI
configuration were not changed.

- Complete isolated suite: **934 tests passed**, 48.675 seconds.
  Sandbox: `/private/var/folders/h4/2j4vdtds3kv0dy86_qq633vr0000gn/T/v2-pr1-suite-380o8lg9`.
- Targeted isolation suite: **25 tests passed**, 25.161 seconds.
  Sandbox: `/private/var/folders/h4/2j4vdtds3kv0dy86_qq633vr0000gn/T/v2-pr1-suite-ue3t8854`.
- The harness creates HOME at `<sandbox>/home`, XDG cache/state at
  `<sandbox>/cache` and `<sandbox>/state`, temporary files at `<sandbox>/tmp`,
  and legacy code/runtime at `<sandbox>/code`. Restricted subprocesses use
  `<sandbox>/tmp/v2-isolation-*/runtime-a` and `runtime-b`, with a separate fake
  original HOME. All these suite roots are disposable and removed after testing.
- `validate-inputs` is exercised only within a test with an empty isolated data
  root: expected failure, and no portfolio is created.
- Three-way deterministic comparison command:
  `.venv/bin/python -B /private/tmp/v2-pr1-equivalence/compare.py`.
  The helper runs the checked-in `EQUIVALENCE` fixture against a code-only archive
  of the exact preserved base, current V1 defaults and restricted V2.
  Complete analysis fields, four-mode allocation outputs, static configuration
  fingerprint, rules version and Baseline identity match exactly.
  All three canonical JSON SHA-256 values are
  `f839b577a9063689bc45d0f8c67f37a567fa967acb00b2f3d746f38450d64b94`.
  Comparison roots: `/private/tmp/v2-pr1-equivalence/{preserved-base,current-v1-default,restricted-v2}`;
  each HOME is its `home` child. No runtime state/observation is created.
- Python sources parse successfully; `git diff --check` passes.

This is deterministic unit-level equivalence, not a claim of a production-capable
end-to-end comparison. No real positive-capital analysis was used to obtain evidence.

## Deferred findings and safety

PR2 retains all Baseline/model identity and validation authority work. Restricted
Git provenance and subprocess OCR remain unavailable by design; future support
requires a separately reviewed subprocess boundary. The launcher does not provide
a migration/seed command, production synchronization or shadow observation authority.
Static config generation and tuning application remain disabled in restricted mode.

No unrelated investment bugs were fixed. No CI change was needed: the existing
pull_request trigger covers the V2 integration branch and discovers the new tests.

No merge, deployment, main modification, Chromebook modification, Drive write,
production systemd modification, historical artifact rewrite, real positive-capital
analysis, artificial operational Baseline observation or tuning application is part
of this PR. Test-only synthetic data stays in disposable test roots.
