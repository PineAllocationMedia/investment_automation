# M3/R1 — Blossom profile Portfolio reference → Command Center / Investment Research

**Status:** INTEGRATED MANUAL CONSTRUCTION / SOURCE RIGHTS AND LIVE END-TO-END UNVERIFIED  
**Owner:** PAM PM (bounded integrated-first execution)  
**CEO mandate:** Analyze the Portfolio actually displayed at a user-provided Blossom profile URL, even when ownership is unestablished. **Never** convert a profile reference into the CEO's own positions.

## Actual path

1. CEO initiates a one-time Work task with [PI-1 R1.4](PROMPT_PI_1_BLOSSOM_PORTFOLIO_WORK_R1.md), providing **only** the target profile URL. Work checks the real Portfolio/See all stocks rows in the authorized visible scope, treating its own source output as caller-reported, never broker-verified. URL and authentication tokens are **not** forwarded to Python or the repository.
2. If observed profile rows are treated as `PUBLIC_REFERENCE_ONLY`, Work provides a fenced `{"public_portfolio_reference": {...}}` object in the contract below; **not** `work_blossom_inputs` and **not** a private account. Work cannot invoke the local runner or other ChatGPT Projects automatically.
3. In a trusted private environment, the human places that **nested** `public_portfolio_reference` object as `public_reference_inputs` in the existing local manual R1 CLI. `request.ceo_initiated=true` and `portfolio_needed=false` are mandatory. Choose:
   - `research_needed=false` (`CC_DIRECT`): a compact display-only human report now, status `PUBLIC_REFERENCE_DESCRIPTIVE_REPORT_READY`;
   - `research_needed=true` (`CC_IR_CC`): the actual `IR_REQUEST` manual handoff includes original observed ticker IDs/weights with explicit unverified-reference status; until an **actual separate** `IR_CAPSULE` is received, R1 remains `AWAITING_MANUAL_IR_CAPSULE`. It never fabricates a capsule or investigates tickers itself. On a real IR response, it attaches the separate descriptive reference without changing IR evidence, source status or the memory proposal.
4. There is **no** `CC_PI_CC` / `CC_IR_PI_CC` admission for this input, no M3 scoped private weights, no automatic personal Portfolio Room, no optimization, contribution split or trade. No direct source/Blossom/Project access, storage or scheduled processing is implemented.

## Exact Work-to-R1 public-reference packet

`public_reference_inputs` must be a mapping with **exactly** these keys:

| Field | Meaning |
|---|---|
| `status` | Literal `PUBLIC_REFERENCE_ONLY`, a handling class **not** proof of anonymous browsing |
| `analysis_id`, `analysis_as_of` | Match request exactly; date YYYY-MM-DD |
| `observation_as_of` | Actual dated holdings observation (YYYY-MM-DD not later than cutoff) or `UNKNOWN` |
| `captured_at` | Truthful timezone-aware actual capture datetime (`observed_on` may be earlier), on/after the observation date when known and on/before the analysis cutoff, or `UNKNOWN` |
| `visibility_context` | `SIGNED_IN_VISIBILITY_ONLY`, `ANONYMOUS_PUBLIC_CONFIRMED`, or `UNKNOWN` |
| `visible_scope` | Bounded non-sensitive label; **not** copied into IR/report or memory |
| `account_ownership` | Literal `NOT_ASSUMED_USER`; never accept an unproven private-ownership claim |
| `positions_visible` | 1–60 rows with exact `security_id`, `weight_pct`, `value`, `currency`, `visibility` |
| `coverage` | Six explicit booleans: `all_rows_visible`, `other_group_expanded_or_absent`, `cash_visible`, `weights_comparable`, `account_filter_visible`, `sync_date_visible` |
| `displayed_weight_sum_pct` | Optional exact total of displayed percentages; if supplied it MUST equal the arithmetic total of reported rows; never normalized |
| `unknowns` | At most 12 bounded strings; their raw content isn't propagated to report or IR |

Each row uses `security_id` = visibly observed ticker/identifier of at most 32 characters, no spaces or markup, unique within the captured list; `weight_pct` = **decimal-string percentage points** within 0–100 with at most 2 decimal places or `null` if absent; `value` = visible exact nonnegative decimal-string amount with at most 2 decimals or `null`; `currency` = actual uppercase 3-letter currency or `null`; `visibility` = `VISIBLE` or `UNCERTAIN`. **Visible values are validated but deliberately omitted** from the derived profile report/IR handoff to avoid unnecessary carrying of possibly sensitive account balances. All key/scope/date/visibility and numeric-shape mismatches fail closed.

The capture timestamp does **not** automatically become the effective date of the displayed holdings. A capture taken after an older visible sync/observation date is admitted, identified separately in the CC report, and never upgrades portfolio freshness or ownership. Future-cutoff capture, capture before the asserted observation date, and timezone-naive timestamps are rejected; if sync/observation date is `UNKNOWN`, even a known capture date cannot fill it. The reference aggregator sums displayed weights without treating 100.3% as a new account denominator. A top-five sum is **displayed percentage points**, not effective whole-portfolio allocation. `ANONYMOUS_PUBLIC_CONFIRMED` is accepted only as a *Work-reported* assertion; this parser cannot independently test an anonymous session. Unknown ticker names, missing values, incomparability and stale snapshots are NOT filled from the market or guessed.

### Synthetic format example (not a real account)

```json
{
  "request": {
    "ceo_initiated": true,
    "research_needed": false,
    "portfolio_needed": false,
    "analysis_id": "SYN-REF-CASE",
    "as_of": "2026-10-29",
    "objective": "Synthetic Blossom reference research",
    "kind": "DECISION"
  },
  "public_reference_inputs": {
    "status": "PUBLIC_REFERENCE_ONLY",
    "analysis_id": "SYN-REF-CASE",
    "analysis_as_of": "2026-10-29",
    "observation_as_of": "UNKNOWN",
    "captured_at": "UNKNOWN",
    "visibility_context": "SIGNED_IN_VISIBILITY_ONLY",
    "visible_scope": "SYNTHETIC_PROFILE",
    "account_ownership": "NOT_ASSUMED_USER",
    "positions_visible": [
      {"security_id": "SYN-A", "weight_pct": "40.1", "value": null, "currency": null, "visibility": "VISIBLE"},
      {"security_id": "SYN-B", "weight_pct": "30.1", "value": null, "currency": null, "visibility": "VISIBLE"},
      {"security_id": "SYN-C", "weight_pct": "20.1", "value": null, "currency": null, "visibility": "VISIBLE"},
      {"security_id": "SYN-D", "weight_pct": "10.0", "value": null, "currency": null, "visibility": "VISIBLE"}
    ],
    "coverage": {
      "all_rows_visible": true,
      "other_group_expanded_or_absent": true,
      "cash_visible": false,
      "weights_comparable": true,
      "account_filter_visible": false,
      "sync_date_visible": false
    },
    "displayed_weight_sum_pct": "100.30",
    "unknowns": ["SYNTHETIC_SOURCE_SYNC_DATE_UNKNOWN"]
  }
}
```

In a locally authorized checkout, **only after the CEO explicitly requests the run**:

```sh
python -B -m scripts.r1_manual_session_cli --output status < private_case.json
python -B -m scripts.r1_manual_session_cli --output report < private_case.json
python -B -m scripts.r1_manual_session_cli --output review-queue < private_case.json
```

For `CC_IR_CC`, `--output handoffs` gives an explicit copyable `IR_REQUEST` with its public-reference context, requiring user transfer. The reference is NOT a replacement for an original research source. Never place a real profile snapshot, account information, target URL or the private JSON in GitHub. R1's default status/review queue stays source-name/amount-free.

## New bounded Work Markdown-table intake — no JSON regeneration required

The CEO's first Work result already contained a **two-column Markdown table** headed `Position affichée | Poids affiché`. The local R1 runner can now accept that *actual table as text* directly, without requesting a second Work run to rewrite all 20 rows into a verbose JSON list. This is a conversion of caller-reported observation only, **not** a verified live Work-to-Project connection.

Use the same top-level `request`, but pass exactly one of:
- `public_reference_inputs`: the original R1.4 structured public-reference object;
- `public_reference_table_inputs`: a compact table envelope using **the same reference fields except** replace `positions_visible` and `displayed_weight_sum_pct` with one `positions_table` Markdown string.

The `positions_table` value must contain **only** the two-column table, including the heading and Markdown separator, followed by 1–60 actual display rows. Permitted headings: `Position affichée | Poids affiché`, `Position | Poids`, `Security | Weight`, or `Holding | Displayed weight`. Each row begins with the visibly reported ticker/identifier, optionally followed by a description after a spaced dash; the identifier is the ONLY label retained. Each second cell must be a percentage such as `25,1 %` or `25.1 %`, or `UNKNOWN` / `NOT_VISIBLE`. Non-tickers, extra columns, invalid amounts, repeated tickers and prose outside the table are rejected. This is **not** arbitrary parsing of an AI narrative. Work-reported company descriptions are discarded; no security master is inferred.

**Synthetic one-time input shape** (replace the table with an authorized observation in a trusted private session only):

```json
{
  "request": {
    "ceo_initiated": true,
    "research_needed": false,
    "portfolio_needed": false,
    "analysis_id": "SYN-TABLE-CASE",
    "as_of": "2026-10-29",
    "objective": "One descriptive Blossom reference",
    "kind": "DECISION"
  },
  "public_reference_table_inputs": {
    "status": "PUBLIC_REFERENCE_ONLY",
    "analysis_id": "SYN-TABLE-CASE",
    "analysis_as_of": "2026-10-29",
    "observation_as_of": "UNKNOWN",
    "captured_at": "UNKNOWN",
    "visibility_context": "SIGNED_IN_VISIBILITY_ONLY",
    "visible_scope": "SELECTED_PROFILE_ACCOUNT_FILTER_UNKNOWN",
    "account_ownership": "NOT_ASSUMED_USER",
    "positions_table": "| Position affichée | Poids affiché |\n| --- | --- |\n| SYN-A — Synthetic A | 40,1 % |\n| SYN-B — Synthetic B | 30,1 % |\n| SYN-C — Synthetic C | 20,1 % |\n| SYN-D — Synthetic D | 10,0 % |",
    "coverage": {
      "all_rows_visible": true,
      "other_group_expanded_or_absent": true,
      "cash_visible": false,
      "weights_comparable": true,
      "account_filter_visible": false,
      "sync_date_visible": false
    },
    "unknowns": ["SOURCE_HOLDINGS_SYNC_DATE_NOT_VISIBLE"]
  }
}
```

The parser converts only the observed ticker and displayed percentage into the **same previously validated** reference format; `displayed_weight_sum_pct` is derived exactly, without forcing 100%. All other date, source, account-scope, value/rights, public/private separation and manual CC/IR guards are inherited without bypass. The Markdown description, source URL, broker account identifier, raw narrative, cash balance and unseen positions never enter the resulting report. Use `--output status` to see only fixed status; `--output report` or `--output handoffs` is an explicit private-terminal action. **Work tables are not fetched or retained by R1.**

## First observed capability versus implementation

The CEO provided Work's **2026-10-29 signed-in profile Portfolio** narrative: 20 lines were visible after **See all stocks**, with one-decimal displayed percentages summing to 100.3%, visible cash/account filters and actual sync date **not established**. This is human-supplied evidence of Work-reported view/transcription, *not* a strict packet matching the schema above, and has **not** been ingested or replayed against code. It is not an anonymous availability check or a broker statement.

**Synthetic tests authored (runtime not established for this extension):** `python -B -m unittest -v tests.test_ai_native_public_portfolio_reference tests.test_ai_native_session_bridge tests.test_ai_native_r1_manual_cli tests.test_ai_native_manual_review_queue`. Authenticated end-to-end execution, original-source verification, site rights, actual source date, model acceptance, deployment/trades and any public-to-private transfer remain unavailable. Decisions #16–18, #29 and #35 remain **PARTIAL**.
