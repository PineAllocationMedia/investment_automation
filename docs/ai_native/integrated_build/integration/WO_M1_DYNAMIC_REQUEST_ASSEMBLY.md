# M1 construction — dynamic manual request assembly

**Work Order:** `WO-FIN-FS-R1-M1-DYNAMIC-REQUEST-ASSEMBLY`  
**Primary capability:** Product & UX (subject-method review not claimed). **Implementation:** PM bounded direct GitHub code preparation.  
**CEO direction:** after the Oct 28 T13 return, construct the whole 36-decision R1 system **before** comprehensive integrated acceptance; small component/safety checks remain appropriate during build.  
**Base:** `model-v2/expected-return-challenger` @ `19dab7598c5c512f281eb729fa233714b46d9d5d`.  
**Sources:** PAM Constitution → Governance → Current State → Program Manager role → this WO → `AGENTS.md`, integrated `OPERATING_CONTRACT.md`, M1 Project adoption files, the IR/PI manual request templates, M7a runbook and decision matrix.

## Goal and reason

CC/IR/PI Project instructions and request templates are CEO-confirmed and in GitHub, but the integrated R1 repository lacked a reusable **construction-time prompt/transfer assembler**. Create a small, source-neutral component turning an explicit CEO-initiated request envelope and two user-supplied routing flags into human-copyable IR/PI requests. Do not infer issuer facts, strategies, account data, holdings or loaded methods.

**Proposed paths:** new `ai_native/request_assembly.py`, new `tests/test_ai_native_request_assembly.py`, this WO, append M7a runbook, and a truthful M1/coordination ledger update. No code elsewhere, no protected files.

## Interface and safeguards

- `prepare_manual_handoffs(request, ir_capsule=None, portfolio_context=None)` is a **pure Python constructor**: no GitHub writes, web, Project invocation, trading or schedule.
- `request` explicitly asserts `ceo_initiated=True`, `research_needed` and `portfolio_needed` booleans, `analysis_id`, `as_of`, `kind`, `objective`; other strategy/horizon/account/FX/benchmark contexts remain supplied or UNKNOWN/EXPLORATORY.
- Route selection: `CC_DIRECT`, `CC_IR_CC`, `CC_PI_CC`, `CC_IR_PI_CC`. A combined route **does not create PI_REQUEST until the original IR capsule is supplied**.
- PI transfer carries `FORWARD_UNCHANGED` exactly once for a supplied IR packet (including its embedded evidence annex); same analysis ID, research cutoff and portfolio observation cutoff guards; JSON copy rejects nonportable coercions.
- Outputs are **PRIVATE** `ir_request_private`, `pi_request_private` and `copy_ready_private`; no claim that method references were loaded or a specialist was actually invoked. Missing portfolio context stays NOT_SUPPLIED.
- Only standard-library dependencies and $0 external financial-data costs; V1 main operational authority and V2 challenger unchanged; no new investment policy, account access, spending, data collection, device access or automated development.

**Validation:** local standalone 17 synthetic Python unittest cases and compilation (must verify exact Git blob parity); GitHub scope/blob checks; read-back after commit. This is **component validation during construction**, not system-wide acceptance, RESEARCH/PORTFOLIO/ROUTINE-READY or a complete 36-decision system.

**Stop:** one PR, no merge. CEO controls merge separately. Any independent Product & UX review is a separate observed event, not implicitly performed here.
