# PROMPT PI-1 — BLOSSOM PORTFOLIO (WORK + CLOUD BROWSER DEFAULT)

**Version:** `PI-WORK-PORTFOLIO-R1.5` — 2026-10-29 (private percent-only observations added; real adoption unverified)  
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
OUTPUT_CONTRACT: work_blossom_inputs / PI-WORK-PORTFOLIO-R1.5

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

A. PUBLIC_REFERENCE — the specified profile has a visible Portfolio listing treated as REFERENCE DATA. This may be observed in a signed-in session WITHOUT proof of anonymous accessibility.
Output a single fenced JSON object with top-level key "public_portfolio_reference". Its nested object MUST use EXACTLY these fields (no source URLs, account IDs, balances, credentials, raw browser HTML, personally private fields or extra keys):
- status: "PUBLIC_REFERENCE_ONLY";
- analysis_id: exact supplied/generate-once case ID;
- analysis_as_of: canonical YYYY-MM-DD analysis cutoff;
- observation_as_of: actual dated YYYY-MM-DD holdings observation ONLY if visible; otherwise "UNKNOWN" (browser capture time alone does not prove holdings sync);
- captured_at: actual timezone-aware ISO 8601 browser capture timestamp (local date must match observation_as_of if it is known), or "UNKNOWN";
- visibility_context: "ANONYMOUS_PUBLIC_CONFIRMED" only if exactly the same portfolio was inspected without authentication; otherwise "SIGNED_IN_VISIBILITY_ONLY" or "UNKNOWN". Signed-in access and an "Edit profile" control do not prove anonymous public access or holdings ownership;
- visible_scope: concise human description of the portion observed, or "UNKNOWN". Do not use account numbers or IDs here;
- account_ownership: always "NOT_ASSUMED_USER";
- positions_visible: one to 60 distinct records, EXACTLY {"security_id": ticker/string using letters/digits/dot/colon/hyphen, "weight_pct": decimal string with 0–2 decimal places or null, "value": visible monetary amount as decimal string to 2 places or null, "currency": actual visible uppercase three-letter currency or null, "visibility": "VISIBLE" or "UNCERTAIN"}. Keep displayed percent units as percentage POINTS (e.g. "25.1" means 25.1%, not 0.251); no normalized weights. If only a long descriptive company name is visible, ask Work to obtain the precise ticker; do not manufacture a ticker;
- coverage: EXACTLY six actual booleans: "all_rows_visible", "other_group_expanded_or_absent", "cash_visible", "weights_comparable", "account_filter_visible", "sync_date_visible". Unsupported scope/verification -> false. The same list of rows need not be the complete household holdings;
- displayed_weight_sum_pct: sum of ALL listed visible percentage strings, expressed as a decimal string, only when every listed row has a visible weight; otherwise null. If this is 100.3 or 99.7, report it as displayed WITHOUT rescaling, rounding it to 100, or asserting a verified denominator;
- unknowns: list of up to 12 short missing-fact descriptions (no private account identifiers).
After the JSON, provide a SHORT DESCRIPTIVE ANALYSIS of the actually visible profile portfolio: largest lines, concentration of shown percentages and cautiously identified overlap hypotheses, with account-scope, sync-date, cash, currency, and incomplete ETF composition limits. Do NOT call it the CEO's private holdings, claim a source-certified universe, calculate a personalized new-capital split or trade recommendation. The resulting object can now be passed manually to R1 as top-level "public_reference_inputs" on an explicitly CEO-initiated **CC_DIRECT** or **CC_IR_CC** route; it is NEVER input to the private M3 P-ledger or a PI personal Portfolio Room route. Neither Work nor this prompt automatically invokes the local CLI, Investment Research or Command Center.

B. OWN_PRIVATE_AUTHORIZED — an explicitly authorized view of MY own private account is actually established, with visible selected scope, observation date and at least one position. Unknown monetary basis permits descriptive percentage observation only, NOT portfolio arithmetic:
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
- currency: genuinely observed account-base 3-letter currency, or explicit "UNKNOWN" when only display percentages are visible; never invent monetary denomination;
- coverage_evidence: account_filter_visible, all_rows_visible, other_group_expanded_or_absent, cash_checked, same_currency_basis_visible (all five actual booleans);
- cash_base: exact observed account-base decimal string or null;
- cash_visibility: VERIFIED_VISIBLE / UNCERTAIN / NOT_VISIBLE;
- positions: nonempty list of p_id, security_id, market_value_base, currency, account_scope and field_statuses for security_id/market_value_base/currency/account_scope, each VERIFIED_VISIBLE / UNCERTAIN / NOT_VISIBLE. Each row MAY additionally carry displayed_weight_pct (exact observed 0–100 percentage as a decimal string with up to two places, or null) plus displayed_weight_visibility (VERIFIED_VISIBLE for truly visible numeric weight, otherwise UNCERTAIN/NOT_VISIBLE and null). Do not normalize the displayed sum (including totals slightly above 100), fabricate market values, assume cash, infer a denominator or use displayed percentages for portfolio arithmetic. Null unknown fields rather than inferring zero.
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

**Scope status:** Work signed-in profile navigation and visible positions are `PROJECT_REPORTED_PARTIAL`. The public-reference-style Work output remains separate from private M3 `work_blossom_inputs`. A **new local R1 structural parser and manual CC / CC→IR route** can accept a correctly formatted `public_portfolio_reference` packet as `public_reference_inputs`; the previously reported 20-line narrative/table was **not** this strict packet and was **not** automatically ingested. Real Project handoff, genuine source/rights verification, public anonymous access and comprehensive 36-decision acceptance remain unverified. No additional automatic research or follow-ups follow from this record.


**For R1 manual entry (docs version R1.4):** Work's public JSON wrapper is `{"public_portfolio_reference": {...}}`. Manually pass its **nested object** as `{"request": {...}, "public_reference_inputs": {...}}` to `scripts.r1_manual_session_cli`. `request.ceo_initiated=true`, `portfolio_needed=false`; `research_needed=false` returns a descriptive CC report immediately, while `research_needed=true` creates an **IR_REQUEST** containing the observed security IDs and unnormalized weights, and waits for a real unchanged IR_CAPSULE. The module does NOT look up source information, know who owns the holdings, or turn them into private allocation inputs. Use a private terminal if any uncertain or sensitive data is involved.

## 4. Capability conclusion boundary

The CEO-reported signed-in Work Portfolio observation advances the visibility leg but does not prove public anonymous access, comprehensive scope, source authenticity, private ownership or end-to-end R1. The private adapter still only consumes caller-reported private packets; it cannot browse Blossom or verify rights. Never store the resulting portfolio data, credentials or screenshots in this repository.

**36-decision coverage:** #16, #18, #29 and #35 remain `PARTIAL`. One Work task and one handoff do not equal complete R1 acceptance, `PORTFOLIO-READY`, source certification or production authority.
