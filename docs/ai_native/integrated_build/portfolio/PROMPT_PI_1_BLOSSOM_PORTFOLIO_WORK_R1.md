# PROMPT PI-1 — BLOSSOM PORTFOLIO (WORK + CLOUD BROWSER DEFAULT)

**Version:** `PI-WORK-PORTFOLIO-R1.3` — 2026-10-29  
**Status:** VERSIONED / COPY-READY / CEO-REPORTED SIGNED-IN PROFILE PORTFOLIO OBSERVATION PARTIAL  
**Owner:** PAM Financial Systems — Portfolio Intelligence, with PM integration  
**Trigger:** CEO/user-initiated **only**. No recurrence, polling, task installation or autonomous account access.  
**Companions:** [Work/Blossom handoff](WORK_BLOSSOM_HANDOFF_R1.md) · [PI R1 request](RUN_REQUEST_PI_R1.md) · `ai_native/work_blossom_adapter.py` · `ai_native/session_bridge.py`.

This is a **practical Work task**, analogous in interaction style to PAM Media's approved Prompt 4 but with **separate financial-account authorization and privacy**. Media's successful signed-in Posts browsing does **not** prove access to a private Portfolio view. A versioned prompt is not proof of installation, site compatibility, source authenticity, portfolio readiness or comprehensive R1 acceptance.

## 1. Copy this entire prompt into a new user-initiated ChatGPT Work task

```text
PROMPT PI-1 — BLOSSOM TARGET PORTFOLIO OBSERVATION
WORK + CLOUD BROWSER DEFAULT / READ-ONLY / ONE SESSION / PRIVATE FINANCIAL DATA

OBJECTIVE
Analyze the portfolio ACTUALLY VISIBLE at the exact Blossom profile URL I supplied, regardless of whether it is a public profile or my own authorized private account. I am selecting a URL, not claiming ownership of that portfolio. Do not stop simply because I have not preselected MY_PRIVATE_PORTFOLIO versus PUBLIC_REFERENCE. Identify the real access/visibility category from the page itself and analyze only accessible, permitted data. A public portfolio must remain a separate descriptive research reference and must NOT enter my private M3 holdings ledger. No trades, brokerage verification or portfolio synchronization.

TARGET ACCOUNT — ONLY URL IS REQUIRED
BLOSSOM_TARGET_URL: [PASTE_THE_EXACT_HTTPS_BLOSSOM_PROFILE_URL_HERE]
TARGET_ACCESS_SCOPE: AUTO_CLASSIFY_FROM_ACTUAL_VISIBLE_PORTFOLIO
SELECTED_ACCOUNT_SCOPE: OBSERVE_ACTUAL_VISIBLE_SCOPE (not assumed to belong to me)

CASE IDENTITY
ANALYSIS_ID: [use the exact ANALYSIS_ID from the Financial Systems Command Center when supplied; otherwise assign one new unique identifier, report it and reuse it unchanged in every handoff]
ANALYSIS_AS_OF: [use the exact YYYY-MM-DD cutoff supplied by CC; otherwise use today's actual date in the intended account timezone, and state the timezone; do not silently backdate holdings]
OUTPUT_CONTRACT: work_blossom_inputs / PI-WORK-PORTFOLIO-R1.3

EXECUTION
1. Use ChatGPT Work Cloud Browser. Start at the exact user-supplied BLOSSOM_TARGET_URL, with the HTTPS hostname exactly blossomsocial.com or www.blossomsocial.com. Do not invent URLs, substitute profiles, follow off-domain redirects, bypass rights or use sign-in tokens. If a login is required for MY private view, I will complete it securely within the browser; never ask for credentials in chat.
2. Navigate to the Portfolio tab/section ON THAT EXACT PROFILE if it exists, then classify using actual evidence:
   - PUBLIC_REFERENCE: Visible holdings on that profile, whether my public profile or another user's public portfolio. Report public observations descriptively; do not assume I own the holdings or demand a private account scope selection.
   - OWN_PRIVATE_AUTHORIZED: Only when this is visibly MY own private account Portfolio AND I explicitly authorize a read-only inspection; never infer ownership just because the browser is signed in.
   - INACCESSIBLE_OR_AMBIGUOUS: No accessible Portfolio content at that profile, unsupported permissions or uncertain identity. Clearly report the blocker instead of inventing data.
   Do not use the Posts feed or an unrelated account as a substitute for the actual Portfolio.

3. Within the allowed read-only view, record the selected account filter and actual observed scope. Only click, scroll, expand "Other" or change display filters when they merely change what is viewed, not account state. Examine all position rows, pagination/scroll and cash if accessible. Never link or reconnect a brokerage, edit settings, change preferences, export private archives, post, follow, like, place an order, or access unrelated accounts.
4. For every observed row record a unique P_ID, the exact visible listed security identity (ticker + venue/class only if shown), account scope, account-base currency and market value only if truly visible and on the SAME confirmed currency basis. If only an allocation percentage is visible, do NOT convert it into a dollar value. Unknown, cropped, grouped, stale or ambiguous fields remain null/NOT_VISIBLE/UNCERTAIN. NEVER invent account currency, cash=0, hidden positions, foreign-exchange rates, value conversions, account totals or unsupported weights.
5. Use the actual observation date YYYY-MM-DD and a truthful timezone-aware ISO 8601 captured_at timestamp with UTC offset, matching observed_on; use "UNKNOWN" for captured_at if this cannot be established. Clearly distinguish the observed holdings date from the analysis cutoff and time the browser was opened.
6. Five coverage_evidence booleans MUST be actual observations, not defaults:
   - account_filter_visible: the selected scope/account filter is visibly identifiable;
   - all_rows_visible: every row in this specific selected scope was inspected, including pagination;
   - other_group_expanded_or_absent: any "Other" grouping was expanded or truly absent;
   - cash_checked: the cash component was actually inspected (cash may still be NOT_VISIBLE);
   - same_currency_basis_visible: all reported market_value_base figures are demonstrably on the one declared account-base currency basis.
   If evidence is insufficient, use false. All values are caller/Work-reported visibility, NOT independently broker-verified.
7. Respect private ownership: never send holdings, amounts, screenshot bytes, account IDs or source URLs to GitHub, PAM Media, public posts or any third party. Do not persist data or schedule future visits. Do not transfer to another ChatGPT Project automatically. No trading or portfolio decision.

REQUIRED OUTPUT — CHOOSE THE BRANCH MATCHING THE ACTUAL TARGET, NOT A GUESSED OWNER

A. PUBLIC_REFERENCE — the target profile has a visible Portfolio listing treated as REFERENCE DATA, even if inspected in a signed-in session:
Return one JSON object with top-level "public_portfolio_reference" (NOT "work_blossom_inputs"), containing:
- status: "PUBLIC_REFERENCE_ONLY", analysis_id and analysis_as_of from the case, observation_as_of as actually shown or "UNKNOWN", captured_at as actually observed or "UNKNOWN";
- visibility_context: "ANONYMOUS_PUBLIC_CONFIRMED" ONLY if the exact same portfolio was actually observed without signing in; otherwise "SIGNED_IN_VISIBILITY_ONLY" or "UNKNOWN". A profile "Edit profile" control does not prove anonymous public access or a portfolio/account filter;
- visible_scope: what the URL actually shows; account_ownership: "NOT_ASSUMED_USER";
- positions_visible: one record per displayed row with visible security name/ticker, weight_pct as the displayed decimal string or null, value/currency only if visibly supplied (else null) and visibility VISIBLE or UNCERTAIN;
- coverage: booleans for all_rows_visible, other_group_expanded_or_absent, cash_visible, weights_comparable, account_filter_visible and sync_date_visible, false when not established;
- displayed_weight_sum_pct: exact sum of the displayed weights if every needed weight was actually read, else null. NEVER rescale displayed percentages just to total 100%; preserve rounding discrepancy as a limitation;
- unknowns: missing account scope, cash, denominator, currency, sync date, offscreen holdings or limits.
After that JSON, produce a SHORT DESCRIPTIVE ANALYSIS of the portfolio visible at that URL: largest displayed positions and concentrations, supported overlap hypotheses, unresolved ETF look-through and missing source evidence. Quantify only observed/comparable rows. Do not call the reference the user's own private holdings, assert full household diversification, calculate brokerage-verified weights, issue personal allocations or trade advice. "PUBLIC_REFERENCE_ONLY" is a handling label, NOT independent proof of anonymous access. This public report is NOT accepted by the existing M3 private adapter.

B. OWN_PRIVATE_AUTHORIZED — an explicitly authorized view of MY own private account is actually established, with account-base currency, scope, observation date and at least one position:
Return exactly one fenced JSON object with TOP-LEVEL key "work_blossom_inputs". Its nested object must match the existing M3 PRIVATE adapter fields, with exactly:
- capture_mode: "WORK_BROWSER";
- view_status: "VISIBLE";
- user_authorized_read_only: true only after actual authorization;
- private_portfolio_view: true only after actual private ownership is observed;
- browser_hostname: "www.blossomsocial.com" or "blossomsocial.com" (hostname only);
- work_reported_signed_in: true only if observed;
- source_access_reported: true only if observed;
- analysis_id and analysis_as_of: exact case ID/cutoff;
- observed_on: actual ISO YYYY-MM-DD dated view, never after cutoff;
- captured_at: truthful timezone-aware ISO datetime or "UNKNOWN";
- account_scope: exact visible selected scope;
- currency: genuinely observed account-base 3-letter currency;
- coverage_evidence: account_filter_visible, all_rows_visible, other_group_expanded_or_absent, cash_checked, same_currency_basis_visible (all five actual booleans);
- cash_base: exact observed account-base decimal string or null;
- cash_visibility: VERIFIED_VISIBLE / UNCERTAIN / NOT_VISIBLE;
- positions: nonempty list of p_id, security_id, market_value_base, currency, account_scope and field_statuses for security_id/market_value_base/currency/account_scope, each VERIFIED_VISIBLE / UNCERTAIN / NOT_VISIBLE. Null unknown fields rather than inferring zero.
VERIFIED_VISIBLE is a visual transcription, NOT independent brokerage verification. Never copy the target URL, login details, screenshots, raw HTML or private query tokens into the JSON. Incomplete scope must remain uncertain, not certified.

C. INACCESSIBLE_OR_AMBIGUOUS — no actual displayed Portfolio or unconfirmed authorized/private case:
Return the PRIVATE-adapter-compatible unavailable shape with actual case details, not fabricated holdings:
{"work_blossom_inputs":{"capture_mode":"WORK_BROWSER","view_status":"UNAVAILABLE","analysis_id":"<actual case ID>","analysis_as_of":"<actual YYYY-MM-DD cutoff>"}}
State the single decisive blocker separately. An optional dated screenshot fallback applies only when a private view cannot be seen; for a PUBLIC visible portfolio use branch A instead of treating public visibility as failure.

AFTER THE JSON
Summarize whether the specified target URL's Portfolio was actually visible, its observed category (PUBLIC_REFERENCE, OWN_PRIVATE_AUTHORIZED, INACCESSIBLE_OR_AMBIGUOUS) and the missing coverage. State WORK_COMPATIBILITY as OBSERVED_VISIBLE, PARTIAL or UNAVAILABLE as supported, never broker authentication. Public branch includes its short descriptive portfolio analysis; private branch provides the private structured observation for manual PI transfer. Do not advise trades, schedule access, publish or self-invoke another Project. STOP.
```

**Target URL and scope:** The CEO supplies the Blossom target URL only, and Work classifies actual visible Portfolio data. A signed-in page, even with "Edit profile", does not establish the selected brokerage-account scope or that anonymous visitors see the same positions. Treat reference-only results as distinct from private M3 holdings; never write the target URL or account data to GitHub.

**Screenshot fallback (CEO-provided image):** In a new, explicitly requested Work/PI task with the authorized dated screenshot, use the same observational rules and case identity, but `capture_mode=USER_SCREENSHOT`. Never claim Work login, browser hostname or live Blossom access based on the screenshot. This is a new human-supplied input, not an automated background retry. The adapter ignores the hostname/sign-in fields in screenshot mode; prefer omitting them.

## 2. Exact handoff after Work returns

1. For PUBLIC_REFERENCE, use the Work descriptive report as a public research reference; if needed, manually pass it to **Investment Research** with its source/rights limitations, never into the private M3 holdings adapter. For OWN_PRIVATE_AUTHORIZED, keep all private observation data in an authorized private context. For INACCESSIBLE_OR_AMBIGUOUS, no portfolio conclusion can be drawn.
2. **Only** if Work confirmed an authorized OWN private Portfolio, manually carry the `work_blossom_inputs` object and exact case identity into PAM — Portfolio Intelligence with the `PI_REQUEST`. PI produces a separately requested `PI_DELTA` and preserves the original IR capsule unmodified where applicable.
3. For an authorized **PRIVATE-portfolio only** local R1 CLI run, supply a **PRIVATE** JSON object with top-level `request` (CEO-initiated, `portfolio_needed=true`, same analysis ID/as-of), `work_blossom_inputs` (exact Work subobject) and `pi_delta` **only when actually returned by PI**. The CLI's `--output status` remains redacted. If `pi_delta` has not arrived, R1 returns `AWAITING_MANUAL_PI_DELTA`; if the visual source is unavailable, `AWAITING_MANUAL_PORTFOLIO_SCREENSHOT` (or awaits the original IR capsule first if the mandate requires IR). Source/PI date mismatches and an unavailable visual source combined with a purported PI delta are rejected.
4. When complete, CC receives only authorized handoffs for a **private, conditional** report. Record whether Work actually reached the private page, what was obscured and whether the transfers were manual. Do not claim an accepted R1 end-to-end demonstration until separately assessed.

**CLI shape (field names only; never put real values in GitHub):**
```json
{
  "request": {
    "ceo_initiated": true,
    "analysis_id": "SYN-CASE-01",
    "as_of": "2026-10-29",
    "kind": "DECISION",
    "objective": "Synthetic private portfolio observation",
    "research_needed": false,
    "portfolio_needed": true
  },
  "work_blossom_inputs": {
    "capture_mode": "WORK_BROWSER",
    "view_status": "UNAVAILABLE",
    "analysis_id": "SYN-CASE-01",
    "analysis_as_of": "2026-10-29"
  }
}
```

Run **only in a trusted private checkout**; no public file, console sharing or GitHub issue with holdings:
```bash
python -m scripts.r1_manual_session_cli --output status < private_case.json
python -m scripts.r1_manual_session_cli --output review-queue < private_case.json
```

## 3. Bounded first observation — CEO-supplied Work result

**October 29, 2026 (CEO report):** Work successfully displayed the **See all stocks** portfolio list on the targeted Blossom profile in a signed-in browser and reported 20 visible securities and their displayed percentage weights. The displayed weights summed to slightly above 100%; rounding is plausible, **not** a validated portfolio denominator. The result is a **usable partial visual observation**, not independently authenticated broker evidence, whole-account holdings, anonymous access, portfolio-sync date, cost/FX evidence or an imported R1 packet. The session also showed an account/profile-editing control, which does not itself prove the intended ownership or public availability of all positions. No authentic ticker, position weight, exact profile URL or private account identifier is stored in this repo.

**Scope status:** Work signed-in profile navigation and visible positions are `PROJECT_REPORTED_PARTIAL`. The **public-reference-style** Work output is separate from the private M3 `work_blossom_inputs` contract. Structured ingestion of that public reference, real CC handoff, complete private source verification and comprehensive 36-decision acceptance are not implemented or not verified. No additional automatic research or follow-ups follow from this record.

## 4. Capability conclusion boundary

The CEO-reported signed-in Work Portfolio observation advances the visibility leg but does not prove public anonymous access, comprehensive scope, source authenticity, private ownership or end-to-end R1. The private adapter still only consumes caller-reported private packets; it cannot browse Blossom or verify rights. Never store the resulting portfolio data, credentials or screenshots in this repository.

**36-decision coverage:** #16, #18, #29 and #35 remain `PARTIAL`. One Work task and one handoff do not equal complete R1 acceptance, `PORTFOLIO-READY`, source certification or production authority.
