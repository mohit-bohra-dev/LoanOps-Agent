# Multi-user scenario testing

How several people can run different agent scenarios without sharing chat memory, then leave reviews in the Eval Portal.

**Related:** [query-checklist.md](../query-checklist.md), [test-queries.txt](../test-queries.txt), eval plan P1 portal (`eval-improvement-platform`).

## Prerequisites

- Shared stack: Agent API `:8000`, Web UI `:5173`, GraphDB/MCP as needed.
- Optional: Langfuse project access for span detail.
- Loan under test: `1000002245` (unless your scenario says otherwise).

## Protocol (isolated)

1. Open the Web UI → **Eval Portal** → **Scenarios** tab.
2. Set **Reviewer** to your name (saved in the browser).
3. Filter by owner (`docs`, `sse`, `eakg`, …) and pick an **open** scenario.
4. **Copy query**.
5. Close portal → Chat. Leave **Isolated (no memory)** checked (default).  
   That omits `session_id` so prior turns do not affect this answer.
6. Paste and send. Wait for the answer + tools.
7. Eval Portal → **Spreadsheet Matrix** → open the new row → **trace** tab (tools) → leave outcome + taxonomy → Save. Feedback stores your reviewer name.

One person = one scenario at a time. Do not reuse a shared session for checklist work.

## Phases

| Phase | Scenarios | Goal |
|---|---|---|
| 1 — one tool | S3–S5, S7–S10, Q8 | Prove each knowledge source alone |
| 2 — chain | S1, S2, S11, S12 | Prove search→call or docs+API in one turn |
| Gaps | process KG | Expect weak until a process tool exists |

Phase 2 formal multi-reviewer disagreement gate is still planned (`p2-multi-reviewer` on the eval plan). Until then, two people can review the same `trace_id` manually; both reviews append to `reviews.jsonl`.

## Assigning work

- Split by **ownerHint** on the Scenario board (`sse`, `docs`, `eakg`, `combo`).
- After a run, update [test-queries.txt](../test-queries.txt) status (OK / PARTIAL / FAIL + trace id) or leave the matrix feedback as the record of truth.

## What not to do

- Share one long-lived `session_id` across testers.
- Judge “memory” follow-ups in this phase.
- Lower eval thresholds based on informal fails.
