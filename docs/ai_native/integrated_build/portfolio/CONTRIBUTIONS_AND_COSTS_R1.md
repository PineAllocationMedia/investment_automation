# PI R1 — New-contribution scenarios and execution-cost discipline
**Status:** candidate research/operational method; no automatic trading or tax calculation. **Inputs:** dated P ledger + intact IR capsule, approved strategy, amount and same-currency basis, user-provided/account-supported costs.

## New contributions before routine turnover
Use the **percentage allocation of new funds** as the default research question when High-CAGR mandate allows. An eligible destination may be a researched individual stock, benchmark VFV where applicable, or conditional no-action/temporary reserve under already approved policy. Never convert missing expected-return or cost information into a confident share split. Distinguish research-priority ranking from permitted account investment candidates.

When data support weights, identify:
- Explicit scope (account vs all accounts), holdings and verified cash; observation date; source completeness.
- Exact capital amount and base currency, conversion basis for each foreign holding; trade currency is not necessarily company reporting currency.
- Current and proposed exposure denominator and all existing holdings; dated observations may be incomparable.
- User/analyst-supplied allocation percentages totaling 100% *of the new contribution*; rationale sourced to IR, concentration, risk and after-cost opportunity value.
- Known commission, trade FX spread/conversion charges, bid/ask, account tax or withholding, currency balance, account and fractional-share capability. Do not assume Wealthsimple or any broker universally has zero fees.
- Scenario flags: GROSS_ONLY / AFTER_COST_SUPPORTED / NET_UNAVAILABLE; after-cost superiority is **not** inferred from missing costs.

## Formula contract and deterministic helper
The isolated Python helper at ai_native/contribution_math.py computes **gross** arithmetic only, given account-base-currency monetary values for an explicitly verified complete scoped account and preselected allocation percentages:

- Amount assigned per destination = new capital × proposed percentage / 100, cents conserved by deterministic largest-remainder rounding.
- Current weight = current position value / verified scoped total (undefined when total=0).
- Projected *gross* position = current position + assigned gross contribution; projected scoped total = verified total + contribution; projected gross weight = projected position / projected total.
- Exact amounts, gross total and percentages are reported. No trade cost, quantity/share fill, tax, FX, future quote, price impact, net portfolio value or recommendation is calculated.

Helper input flags MUST be independently supported: scope_complete, cash_accounted_for, same_currency_basis_verified, instrument_identity_verified and valid observation date. A missing/false flag returns UNAVAILABLE; it must not be set to true for convenience. Positions are fully scoped market values in one **already verified** account currency, not tickers and number of shares. A separately identified cash account can be included in the supplied positions, but any planned cash consumption must be explicitly accounted for outside this new-contribution-only helper.

**Synthetic illustration only:** account has ABC:TSX 400 CAD and VFV:TSX 600 CAD; separately funded 1,000 CAD new contribution splits 60% ABC and 40% VFV. Gross post-contribution positions = 1,000 CAD each, equal 50% weights; status GROSS_ONLY. It is neither a real portfolio nor advice.

## Cost qualification and exceptional insufficiency
A complete after-cost analysis would require dated executable security-class price, account currency, available FX rate and spread, commissions, quoted bid/ask, order constraints, account tax regime and relevant withholding/lot facts when material. If any material input is missing: keep gross arithmetic separately labeled and state NET_UNAVAILABLE; do not subtract assumed 0 or invent net expected return. Pre-existing cross-currency values require documented conversion; if not verified, block projection.

Do not optimize for one account's tax conditions without known account type. Allocation percentages must reconcile to exactly 100% of the new contribution after rounding, but this numerical identity alone proves no investment merit.

## R1 M3 cost arithmetic continuation — supplied-input tally, NOT certified net execution

The optional `ai_native.known_costs.tally_supplied_costs` is a deterministic *purchase-cost tally*, **not** pricing, optimization, tax advice, quotation, source certification or a post-cost position model. It is used only with a `GROSS_PROJECTION_ONLY` result from `project_gross_contribution`. The caller supplies, for **each destination receiving a positive gross contribution**, five explicit **account-base-currency** entries: `commission`, `bid_ask_spread`, `fx_conversion`, `purchase_tax`, `other_fees`. Each entry must have `amount_base` (nonnegative decimal, at most two places) and a source locator `source_ref`. An explicit `0.00` requires a real supplied supporting reference, not a system-imputed zero. The code cannot verify the underlying source or rights.

The supplied cost quote date may not be after the stated analysis cutoff. The helper rejects mismatched account currencies, mismatched positive-trade destinations, negative/nonfinite/overprecise amounts and fees that fully consume a contribution funded from that contribution. Missing cost categories or source references yield `INCOMPLETE_COST_INPUTS`, a **known subtotal only**, and no complete cost total. `SUPPLIED_COST_TALLY_ONLY` means all *named inputs were supplied*, not that their values were authenticated or exhaustive.

Funding must be one of `FROM_CONTRIBUTION`, `EXTERNAL_CASH`, `UNKNOWN`. When costs are paid from the contribution, the function returns a **maximum remaining contribution budget**, flags that the gross full-budget allocation conflicts with fee funding and never pretends to generate new net weights. External-cash costs are listed separately, without deducting them again from position purchases. Unknown funding yields no investable-budget claim. In all cases `net_economics_status=UNAVAILABLE_NOT_EXECUTION_CERTIFIED`: price, bid/ask, share quantities, actual execution, tax applicability and after-tax Expected Return still need external human/source verification.

The existing manual assembler accepts an **optional** `cost_inputs` only alongside an authorized PI gross contribution, checks the same analysis cutoff, stores cost details in the **private** `supplied_costs_private` return field, and keeps the overall report `CONDITIONAL`. No fees, amounts, account data or source IDs are written to the GitHub memory proposal. Neither this code nor the synthetic unit checks pass the whole-system M7 acceptance.


## Conditional funded-contribution reconciliation — proposed R1 component

The pure private helper ai_native.funded_costs_reconciliation.reconcile_funded_contribution consumes the same scoped gross projection, original supplied percentages and output of tally_supplied_costs. It rechecks gross-input consistency and requires source locators covering all five types for each positive original contribution destination. It does not authenticate sources.

With FROM_CONTRIBUTION, all five charges per positive trade must be supplied; the fixed stated monetary subtotal reduces the available new capital. The existing cents-conserving allocation is rerun using the original supplied percentages. If rounding removes an originally positive trade, the conditional projection is withheld because the cost tally would describe a different trade set. Infeasible costs likewise block.

With EXTERNAL_CASH, the full new contribution is preserved and extra supplied fees are shown separately. UNKNOWN funding and incomplete/mismatched costs return UNAVAILABLE without invented zeros. This remains **conditional budget arithmetic only**: actual broker fees, spread, FX, quantities, taxes and other size-dependent charges may change when orders are resized and must be reverified. It is not a certified after-tax/net-return model or an executable investment recommendation.

The result is returned in M7a only as funded_contribution_private, with a general limitation in the concise report. Source and portfolio amounts are not added to the nonprivate GitHub memory proposal. Decision rows #22 and #25 remain PARTIAL; live evidence, real account inputs, complete integration assessment and readiness are not certified.
