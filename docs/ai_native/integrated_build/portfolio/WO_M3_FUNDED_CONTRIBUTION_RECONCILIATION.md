# Work Order — M3 conditional funded-contribution budget reconciliation

**ID:** WO-FIN-FS-R1-M3-FUNDED-CONTRIBUTION-RECONCILIATION
**Primary role:** Program Manager; direct CEO-requested implementation without Codex. Independent Portfolio Intelligence/Data Analyst review NOT CLAIMED.
**Status:** PR_CANDIDATE / COMPONENT_TESTED_ONLY / NOT_MERGED
**Why now:** The CEO-approved integrated-first Financial Systems R1 build has gross contribution and source-attributed purchase-cost tally but lacks the funded budget link. This is a bounded implementation of decisions 22/25, not a new research pilot.

**Sources:** Constitution; Governance; Current State; PM charter; 2026-10-28 Decision Registry; AGENTS.md; 36-decision Blueprint; R1 delivery plan and coverage; M3 Contributions and Costs R1; original contribution_math, known_costs, integrated_flow and tests.

**Mandate:** Add one pure standard-library helper, synthetic tests, M7a private result linkage, compact method documentation and only rows 22/25 of the 36-decision matrix. If fees come from the contribution, conditionally reproject new-capital percentages and cents after supplied absolute fees. If fees are externally funded, preserve full original allocation and state extra cash. Unknown, incomplete and altered destination/denominator states must not create supported net allocations.

**Prohibitions:** V1/legacy V2 runtime/model-policy modifications; invented quotes, taxes or FX; publication of portfolio data; private account access, trades, provider fees, external financial-data spending, unattended development, automated Projects, device operations, branch deletion, protected amendments, production or deployment. CEO alone approves canonical merge.

**Validation:** 11 focused local synthetic tests for the new helper against a locally recreated copy of canonical gross helper, plus 2 new repository-level manual integration test cases not yet run against a full canonical checkout. Local syntax checks limited to staged focused files, not whole-repo acceptance. Source/cost authenticity, fee repricing and real finance integration NOT VERIFIED.

**Stop:** single bounded GitHub PR; no merge or comprehensive 36-decision acceptance.
