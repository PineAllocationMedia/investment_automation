# PROMPT PI-1 — BLOSSOM PORTFOLIO (WORK + CLOUD BROWSER DEFAULT)

**Version:** `PI-WORK-PORTFOLIO-R1.0` — 2026-10-29  
**Status:** VERSIONED / COPY-READY / REAL PRIVATE BLOSSOM VIEW **NOT YET TESTED**  
**Owner:** PAM Financial Systems — Portfolio Intelligence, with PM integration  
**Trigger:** CEO/user-initiated **only**. No recurrence, polling, task installation or autonomous account access.  
**Companions:** [Work/Blossom handoff](WORK_BLOSSOM_HANDOFF_R1.md) · [PI R1 request](RUN_REQUEST_PI_R1.md) · `ai_native/work_blossom_adapter.py` · `ai_native/session_bridge.py`.

This is a **practical Work task**, analogous in interaction style to PAM Media's approved Prompt 4 but with **separate financial-account authorization and privacy**. Media's successful signed-in Posts browsing does **not** prove access to a private Portfolio view. A versioned prompt is not proof of installation, site compatibility, source authenticity, portfolio readiness or comprehensive R1 acceptance.

## 1. Copy this entire prompt into a new user-initiated ChatGPT Work task

```text
PROMPT PI-1 — BLOSSOM PRIVATE PORTFOLIO OBSERVATION
WORK + CLOUD BROWSER DEFAULT / READ-ONLY / ONE SESSION / PRIVATE FINANCIAL DATA

OBJECTIVE
Observe my own explicitly authorized private Portfolio view on Blossom and return ONE exact, portable private JSON observation for PAM Financial Systems R1. This is a visual transcription task, NOT financial advice, a trade, a brokerage audit or portfolio synchronization.

CASE IDENTITY
ANALYSIS_ID: [use the exact ANALYSIS_ID from the Financial Systems Command Center when supplied; otherwise assign one new unique identifier, report it and reuse it unchanged in every handoff]
ANALYSIS_AS_OF: [use the exact YYYY-MM-DD cutoff supplied by CC; otherwise use today's actual date in the intended account timezone, and state the timezone; do not silently backdate holdings]
OUTPUT_CONTRACT: work_blossom_inputs / PI-WORK-PORTFOLIO-R1.0

EXECUTION
1. Use ChatGPT Work with Cloud Browser and my authorized signed-in Blossom session at https://www.blossomsocial.com. I will complete sign-in if prompted by the secure browser. Do NOT request credentials, MFA codes, tokens, cookies or bank credentials in chat. Do not bypass access controls or paywalls.
2. Navigate ONLY to the private Portfolio view for the account(s) I explicitly authorize for this request. A public profile, the @therealpam Posts feed, a featured public investor's portfolio and a generic chart are NOT proof of my private account holdings. If the view is public, not accessible, or its private identity cannot be established, report UNAVAILABLE as specified below. Do not guess from public holdings.
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

REQUIRED OUTPUT
Return exactly one fenced JSON object with TOP-LEVEL key "work_blossom_inputs". The nested object must match the existing PAM R1 adapter fields. Do not put explanations, markdown tables, raw HTML, URLs, credentials, screenshots, tax data or speculative figures INSIDE that JSON. Keep only the fields listed below.

WHEN PRIVATE VIEW IS ACCESSIBLE AND THE ACCOUNT'S 3-LETTER BASE CURRENCY, ACTUAL SCOPE, OBSERVATION DATE AND AT LEAST ONE POSITION CAN BE REPORTED:
"work_blossom_inputs" must contain EXACTLY these keys:
- capture_mode: "WORK_BROWSER";
- view_status: "VISIBLE";
- user_authorized_read_only: true ONLY IF I actually authorized this private read-only task;
- private_portfolio_view: true ONLY WHEN the private ownership/scope was actually observed;
- browser_hostname: "www.blossomsocial.com" or "blossomsocial.com" ONLY IF actually used (hostname only, never URL/query);
- work_reported_signed_in: true ONLY IF the authenticated session was actually observed;
- source_access_reported: true ONLY IF the private scope was actually visible;
- analysis_id: the exact case ID above;
- analysis_as_of: exact cutoff above, canonical YYYY-MM-DD;
- observed_on: the ACTUAL dated view, canonical YYYY-MM-DD (never newer than analysis_as_of);
- captured_at: truthful timezone-aware datetime or "UNKNOWN";
- account_scope: descriptive exact selected scope (never claim all accounts without proof);
- currency: actual observed 3-letter account-base currency, uppercase;
- coverage_evidence: exactly the five boolean keys above;
- cash_base: actual nonnegative account-base-currency decimal string with no more than two decimal places if visible and supported; otherwise null;
- cash_visibility: "VERIFIED_VISIBLE", "UNCERTAIN" or "NOT_VISIBLE";
- positions: a nonempty list, each item with EXACTLY:
  p_id (unique "P-001", "P-002"...),
  security_id (exactly visible identifier string or null),
  market_value_base (nonnegative decimal string to two places ONLY if visibly reported in the declared base currency, otherwise null),
  currency (observed account-base currency string or null if not visible),
  account_scope (exact observed row scope string or null if not visible),
  field_statuses (exactly "security_id", "market_value_base", "currency", "account_scope", each "VERIFIED_VISIBLE", "UNCERTAIN" or "NOT_VISIBLE").
Never copy these instructions as literal portfolio values. A "VERIFIED_VISIBLE" field is directly visible in the allowed source, NOT independently validated by a broker.

IF PRIVATE PORTFOLIO VIEW IS UNAVAILABLE, PUBLIC-ONLY, NOT AUTHORIZED, OR ESSENTIAL CASE/SCOPE/CURRENCY/DATE FIELDS CANNOT BE FAITHFULLY TRANSCRIBED:
Output ONLY:
{"work_blossom_inputs":{"capture_mode":"WORK_BROWSER","view_status":"UNAVAILABLE","analysis_id":"<actual case ID>","analysis_as_of":"<actual YYYY-MM-DD cutoff>"}}
Replace bracketed placeholders with the real case fields. Do not include hidden/partial positions, account labels, source URLs or speculative values. State the single blocker separately in one short sentence and suggest one dated, private user-supplied screenshot/transcription as the fallback, without claiming it was already obtained.

AFTER THE JSON
Give only a two-sentence private summary: whether the private view was ACTUALLY accessible and whether the scoped position/cash/currency coverage is complete. Mark WORK_COMPATIBILITY as OBSERVED_VISIBLE, PARTIAL, or UNAVAILABLE as applicable, explicitly NOT broker authentication. Do not compute allocations, advise trades, publish, create an archive or claim cross-Project transfer. STOP.
```

**Screenshot fallback (CEO-provided image):** In a new, explicitly requested Work/PI task with the authorized dated screenshot, use the same observational rules and case identity, but `capture_mode=USER_SCREENSHOT`. Never claim Work login, browser hostname or live Blossom access based on the screenshot. This is a new human-supplied input, not an automated background retry. The adapter ignores the hostname/sign-in fields in screenshot mode; prefer omitting them.

## 2. Exact handoff after Work returns

1. Keep the **full JSON private**. Read the Work capability summary; never infer completeness from a graph alone. If `view_status=UNAVAILABLE`, stop the portfolio inference and ask for the dated screenshot. Do not pretend the private view was inspected.
2. Manually carry the `work_blossom_inputs` object and matching `ANALYSIS_ID` / `ANALYSIS_AS_OF` into the **PAM — Portfolio Intelligence** Project, with the original `PI_REQUEST` from CC when available. PI should produce **one separate `PI_DELTA`**, and, on an IR+PI route, a verbatim `FORWARD_UNCHANGED` original IR capsule. Work itself does not author the IR analysis or the PI investment conclusion.
3. For an authorized local R1 CLI run, supply a **PRIVATE** JSON object with top-level `request` (CEO-initiated, `portfolio_needed=true`, same analysis ID/as-of), `work_blossom_inputs` (exact Work subobject) and `pi_delta` **only when actually returned by PI**. The CLI's `--output status` remains redacted. If `pi_delta` has not arrived, R1 returns `AWAITING_MANUAL_PI_DELTA`; if the visual source is unavailable, `AWAITING_MANUAL_PORTFOLIO_SCREENSHOT` (or awaits the original IR capsule first if the mandate requires IR). Source/PI date mismatches and an unavailable visual source combined with a purported PI delta are rejected.
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

## 3. Capability conclusion boundary

The existing signed-in **Media Posts** workflow supports using Work as a reasonable **first attempt**, not a claim of private holdings access. The adapter tests only a caller-reported structured packet; it does not fetch Blossom or verify rights. The CEO must run the real one-off private-view check in Work. Its outcome will be `OBSERVED_VISIBLE`, `PARTIAL`, or `UNAVAILABLE` **based on what Work actually reports**, not on this prompt's existence. Never store the resulting portfolio data, credentials or screenshots in this repository.

**36-decision coverage:** #16, #18, #29 and #35 remain `PARTIAL`. One Work task and one handoff do not equal complete R1 acceptance, `PORTFOLIO-READY`, source certification or production authority.
