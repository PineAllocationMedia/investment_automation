# M3 — ChatGPT Work / Blossom private visual observation handoff R1

**Scope:** Construction-time handoff between an explicitly authorized Work browser observation and the existing M3 P-ledger. **Status:** `WORK_ADAPTER_BUILT / LIVE_BLOSSOM_COMPATIBILITY_NOT_TESTED / NOT_PORTFOLIO_READY`. Neither a browser integration nor a broker connection has been installed.

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
from ai_native.work_blossom_adapter import prepare_work_blossom_observation
from ai_native.session_bridge import complete_manual_session

prepared = prepare_work_blossom_observation(private_packet_from_authorized_work)
if prepared["observation_inputs_private"] is not None:
    result = complete_manual_session(
        ceo_initiated_request,
        observation_inputs=prepared["observation_inputs_private"],
        # pi_delta only when separately actually supplied by PI
    )
    # Keep result and prepared entirely in authorized private context.
```

`prepare_work_blossom_observation` is a **pure adapter**. It is NOT capable of opening Work, inspecting Blossom, confirming the signed-in browser or sending to PI. `source_access_reported=true` is an **external report**, not an authenticated source assertion. It passes only strictly selected structured values to `prepare_observation_ledger`; the original P-ledger guards govern dates, field statuses, cash, currency and scoped-weight calculation. Missing “Other” rows, cash, scope or currency basis prevent fully supported weights. **Portfolio Room remains UNAVAILABLE without independent strategy and issuer research.**

**Privacy:** The input packet, observation ledger, account scope and any dollar amounts must stay in a private Work/PI/CC context and must not be pasted into a public issue, PR, repo, PAM Media or research method archive. The repository contains only this synthetic schema, source and test cases.

**Platform limitations:** OpenAI documents Work's cloud-browser and secure signed-in website flow, subject to site restrictions; Blossom documents a webapp with potentially fewer features than mobile and public portfolio percentage visibility. The URLs to verify at actual future capability checking are `https://help.openai.com/en/articles/20001280-using-cloud-browser-in-chatgpt`, `https://intercom.help/blossom-social-inc/en/articles/8167582-is-blossom-available-on-web-desktop` and `https://intercom.help/blossom-social-inc/en/articles/8158797-i-m-a-new-user-how-do-i-use-blossom`. These public documents do **not** prove the CEO account is accessible.

**Effort boundary for eventual compatibility check (not performed):** one CEO-initiated authorized, read-only Work attempt to access the intended private view and capture a complete scoped position list. Stop at first definitive result: accessible and suitably transcribed, restricted/incomplete, or login/rights blocked. No repeated exploratory account logins, brokerage reconnects or alternate credential handling. No comprehensive 36-decision acceptance until full functional assembly.
