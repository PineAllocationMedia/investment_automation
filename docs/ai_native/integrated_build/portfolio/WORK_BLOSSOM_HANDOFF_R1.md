# M3 — ChatGPT Work / Blossom private visual observation handoff R1

**Scope:** Construction-time handoff between an explicitly authorized Work browser observation and the existing M3 P-ledger. The R1.5 private handoff optionally preserves displayed percentages separately from amount-derived weights, including unknown-currency or missing-cash observations; percentages are never normalized or substituted for monetary holdings. **Status:** `WORK_ADAPTER_AND_MANUAL_R1_BRIDGE_BUILT / LIVE_PRIVATE_PORTFOLIO_NOT_TESTED / NOT_PORTFOLIO_READY`. Neither a browser integration nor a broker connection has been installed.

**Default copy-ready one-off Work prompt:** [PROMPT PI-1 — BLOSSOM PORTFOLIO (WORK + CLOUD BROWSER DEFAULT)](PROMPT_PI_1_BLOSSOM_PORTFOLIO_WORK_R1.md), version `PI-WORK-PORTFOLIO-R1.5`. This supersedes only the shorter *example task wording* below for actual Work operations; the adapter/ledger schema and all privacy safeguards remain unchanged. The CEO must run it explicitly in Work; GitHub cannot invoke a signed-in browser. The task requires the CEO's exact `BLOSSOM_TARGET_URL` only; **Work must classify the Portfolio actually shown** as `PUBLIC_REFERENCE`, `OWN_PRIVATE_AUTHORIZED`, or `INACCESSIBLE_OR_AMBIGUOUS`. No mandatory CEO-owned/private-vs-public preselection. A visible public reference receives a separate **descriptive Work portfolio analysis**, never the private M3 holdings adapter. Only a genuinely authorized owner-private view yields `work_blossom_inputs` for the private R1 session. **CEO-reported 2026-10-29 observation:** signed-in profile navigation and the See all stocks list were visible with 20 holdings and displayed percentages. This is Work-reported partial visibility, not proof of anonymous access, the account denominator or source-authenticated brokerage holdings. Keep the reference report separate from the private M3 adapter, without renormalizing rounded display weights.

## Preferred authorized acquisition: Work mode

1. The CEO explicitly asks for a **read-only** observation of the private portfolio view on `www.blossomsocial.com` in a ChatGPT **Work** chat (ideally within the Portfolio Intelligence Project if the feature is available). Work can interact with some signed-in websites using its own browser, but **Blossom-specific login, private holdings access and transfer compatibility remain unverified**. The CEO alone grants site access and uses the secure browser sign-in/takeover flow; no credentials, session tokens, cookies, screenshots or account IDs belong in GitHub.
2. Restrict browsing to the correct private view, with any necessary **non-mutating** filter/expand operations. Do not connect a brokerage, adjust account settings, link institutions, post, follow, buy/sell, export sensitive archives or initiate recurring work. Stop promptly if login, website limitations, rights or private-view identity prevent observation.
3. Record a **reported** hostname, signed-in view status, screenshot/view timestamp and timezone, explicitly chosen account scope, display currency, visible positions and cash. Inspect the detailed rows behind a grouped **Other** chart slice and the selected account filters when accessible. Verify whether this is a private account page rather than the public profile of the CEO or another investor.
4. For each position, supply a P_ID and every existing P-ledger required field with `VERIFIED_VISIBLE | UNCERTAIN | NOT_VISIBLE`. These are **visual transcription labels, never independent brokerage verification**. A displayed percentage does not imply a dollar amount. Do not infer absent accounts, exact cost basis, current FX, net contribution economics or cash=0.
5. Return one small **PRIVATE** structured observation. If the view or login fails, return `view_status=UNAVAILABLE` without copying hidden content; fall back to a dated CEO-supplied screenshot/transcription. No repeating login attempts, background access or automatic scheduling.

**One-time Work task wording (only on CEO request; not a scheduled operation):**

> Using your authorized cloud browser in read-only mode, open the private Portfolio view of Blossom at www.blossomsocial.com if permitted. Ask me to sign in securely if required. Do not interact with brokerage linking, transactions, account settings, posts or paid features. Look at the exact selected account scope, date/time and display currency; expand visible “Other” holdings or account filters only if these are non-mutating. Transcribe only values actually shown with P_ID and field-level VERIFIED_VISIBLE/UNCERTAIN/NOT_VISIBLE, plus separate cash status. State explicitly if the web page is public, the position list is incomplete, cash is hidden or FX basis is unknown. Return a private structured packet with the fields below; never infer, purchase, store credentials, post or send my portfolio to GitHub. If not accessible, report UNAVAILABLE and stop.

## Structured private packet contract (example is synthetic, not an account snapshot)

```json
{
  "capture_mode": "WORK_BROWSER",
  "view_status": "VISIBLE",
  "user_authorized_read_only": true,
  "private_portfolio_view": true,
  "browser_hostname": "www.blossomsocial.com",
  "work_reported_signed_in": true,
  "source_access_reported": true,
  "analysis_id": "SYN-001",
  "analysis_as_of": "2026-10-28",
  "observed_on": "2026-10-28",
  "captured_at": "2026-10-28T10:00:00-04:00",
  "account_scope": "SYN-ACCOUNT",
  "currency": "CAD",
  "coverage_evidence": {
    "account_filter_visible": true,
    "all_rows_visible": false,
    "other_group_expanded_or_absent": false,
    "cash_checked": false,
    "same_currency_basis_visible": false
  },
  "cash_base": null,
  "cash_visibility": "NOT_VISIBLE",
  "positions": [{
    "p_id": "P-1",
    "security_id": "ABC:TSX",
    "market_value_base": null,
    "currency": "CAD",
    "account_scope": "SYN-ACCOUNT",
    "field_statuses": {
      "security_id": "VERIFIED_VISIBLE",
      "market_value_base": "NOT_VISIBLE",
      "currency": "VERIFIED_VISIBLE",
      "account_scope": "VERIFIED_VISIBLE"
    }
  }]
}
```

For a screenshot fallback use `capture_mode=USER_SCREENSHOT`, not a false Work login claim. `view_status=UNAVAILABLE` produces only a fallback status; do not include private positions. An exact hostname is accepted, **not** a full URL containing query tokens.

## Runnable handoff to existing M3/M1→M7a code

```python
from ai_native.session_bridge import complete_manual_session

# Work's PI-1 output contains {"work_blossom_inputs": <private observation>}.
# Do not pass the outer wrapper as the nested object.
result = complete_manual_session(
    ceo_initiated_request,  # must request PI, with matching analysis_id / as_of
    work_blossom_inputs=work_result["work_blossom_inputs"],
    # pi_delta=the actual manually received PI_DELTA, only if supplied
    # ir_capsule=the unchanged original IR package, only if IR was requested
)
# Keep the full result inside the authorized private environment.
# No auto Project transfer or source authentication has occurred.
```

**Direct PI-1 JSON envelope through the manual R1 CLI:** When Work returns its one fenced JSON object with outer key `public_portfolio_reference` or `work_blossom_inputs`, copy **only the JSON object** into `work_portfolio_result` beside the explicitly CEO-initiated `request` in the local CLI input. The CLI accepts exactly one of those two keys and maps it to the already separate public-reference or authorized private-PI validators; do **not** rename/retype the nested holdings or use this for automatic Project transfer. The direct fields `public_reference_inputs` and `work_blossom_inputs` remain supported; never mix them with the wrapper. Case identity, source status, rights, account scope and route are still validated. `--output status` remains redacted, while manual handoffs are sensitive. No Work browsing is performed by this code.

**Connected private PI handoff (R1 construction):** When the CEO supplies a structurally valid private `work_blossom_inputs` (or an authorized private `observation_inputs`) alongside a PI route, `complete_manual_session` attaches its original M3 `portfolio_observation_private` under `P_LEDGER_FOR_REVIEW_PRIVATE` in the existing copy-ready `PI_REQUEST`. The receiving PI Project can review the same dated, scoped P records without asking the CEO to type them a second time. `P_LEDGER_HANDOFF_AUTHORITY=CALLER_REPORTED_PRIVATE_OBSERVATION_MANUAL_REVIEW_ONLY` prohibits treating them as independently authenticated. When IR is required, the `FORWARD_UNCHANGED` IR capsule is preserved exactly and the PI request still waits for IR first. A public/reference-only observation is rejected from this private handoff; use the separate `public_reference_inputs` CC/IR path. If no observation exists, the PI request contains no invented ledger. Conflicts with an explicit account-scope/date context are rejected rather than silently resolved. The entire PI_REQUEST is **PRIVATE**: transfer only within a CEO-authorized Project/session; `--output handoffs` intentionally contains financial records, unlike the redacted `--output status`. This is a portable manual transfer, not Work→PI automation or investment/Portfolio Room validation.

For the unchanged local JSON-over-stdin CLI, use the same `work_blossom_inputs` key beside the `request` key, and include `pi_delta` only when separately obtained. A view reported `UNAVAILABLE` has no usable holdings and leads to `AWAITING_MANUAL_PORTFOLIO_SCREENSHOT` (after any required IR handoff); an observed view without PI_DELTA remains `AWAITING_MANUAL_PI_DELTA`. Do not claim Work accessed the holdings until the explicit real browser task returns evidence.

`prepare_work_blossom_observation` is a **pure adapter**. It is NOT capable of opening Work, inspecting Blossom, confirming the signed-in browser or sending to PI. `source_access_reported=true` is an **external report**, not an authenticated source assertion. It passes only strictly selected structured values to `prepare_observation_ledger`; the original P-ledger guards govern dates, field statuses, cash, currency and scoped-weight calculation. Missing “Other” rows, cash, scope or currency basis prevent fully supported weights. **Portfolio Room remains UNAVAILABLE without independent strategy and issuer research.**

**Privacy:** The input packet, observation ledger, account scope and any dollar amounts must stay in a private Work/PI/CC context and must not be pasted into a public issue, PR, repo, PAM Media or research method archive. The repository contains only this synthetic schema, source and test cases.

**Platform limitations:** OpenAI documents Work's cloud-browser and secure signed-in website flow, subject to site restrictions; Blossom documents a webapp with potentially fewer features than mobile and public portfolio percentage visibility. The URLs to verify at actual future capability checking are `https://help.openai.com/en/articles/20001280-using-cloud-browser-in-chatgpt`, `https://intercom.help/blossom-social-inc/en/articles/8167582-is-blossom-available-on-web-desktop` and `https://intercom.help/blossom-social-inc/en/articles/8158797-i-m-a-new-user-how-do-i-use-blossom`. These public documents do **not** prove the CEO account is accessible.

**Effort boundary for eventual compatibility check (not performed):** one CEO-initiated authorized, read-only Work attempt to access the intended private view and capture a complete scoped position list. Stop at first definitive result: accessible and suitably transcribed, restricted/incomplete, or login/rights blocked. No repeated exploratory account logins, brokerage reconnects or alternate credential handling. No comprehensive 36-decision acceptance until full functional assembly.

## Evidence inherited from PAM Media & Communication — verified signed-in Blossom browser use

The **same Blossom website is already used successfully with an authorized signed-in ChatGPT Work Cloud Browser** in PAM Media & Communication's separate `@therealpam` Prompt 4 measurement workflow. This is **actual project-recorded evidence**, not only a hypothetical platform ability:

- `docs/marketing/MACRO_LENS_PLAYBOOK.md`, Prompt 4 (CEO-approved 2026-10-22), documents Work + signed-in Cloud Browser as the default read-only route, including human-completed secure login, page navigation and GitHub retention of observations when authorized.
- `docs/marketing/MACRO_LENS_EDITORIAL_LOG.md`, `Authenticated profile scan — 2026-10-22 continuation`, records CEO-completed sign-in and inspection of 19 original-post permalinks, compared with four accessible through an earlier public-only scan.
- The same log's `Profile scan — 2026-10-28 (authorized signed-in Cloud Browser)` records **29 original publications individually inspected**, with the feed dynamically loading 13 → 23 → 29 records and existing measurements appended. Historical completeness remains unproven.

**Capability classification:**
- `WORK_BLOSSOM_AUTHENTICATED_PROFILE_NAVIGATION = PROJECT_DOCUMENTED` — access, browser interaction, signed-in Posts feed and read-only metrics retrieval are demonstrated in the Media activity.
- `WORK_BLOSSOM_PRIVATE_PORTFOLIO_VISIBILITY = NOT_OBSERVED` — those Media observations are of the signed-in **Posts** view, **not** a private holdings page; neither private account position list nor brokerage statements were inspected in this evidence.
- `WORK_TO_PI_HANDOFF = MANUAL_CONTRACT_ONLY` — no proven automatic cross-Project invocation, direct Work-to-Python runtime or permanent portfolio sync.
- `AUTHORITY = PER_MANDATE` — Media's publication/measurement permissions **do not extend** to private financial portfolio access. Any Work observation of personal holdings requires a separate CEO-requested read-only scope and secure sign-in, if needed.

**Practical implication:** Do not repeat broad Work login/navigation feasibility experiments already supported by the Media history. For Financial Systems, the **single narrow outstanding capability question** is whether the same authorized Work browser can open and read a sufficiently complete **private Portfolio view** on Blossom (including account scope, positions, cash, "Other" and currency), without changing account state. If that page proves accessible, supply one private observation packet to the already built M3 adapter; if not, use a dated screenshot fallback. The full integrated 36-decision acceptance remains deferred until functional assembly.
