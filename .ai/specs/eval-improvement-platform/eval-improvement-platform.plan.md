---
name: eval-improvement-platform
overview: Ship an Enterprise AI Evaluation & Improvement Platform—canonical traces, human error analysis with failure taxonomy, Observe/Evaluate/Learn portal, stage evaluators, and governed Golden promotion—without a second eval database or lowering sacred thresholds.
todos:
  - id: p1-approval-instrumentation
    content: "Confirm approval to instrument AgentCore via TelemetryProvider; record outcome in Notes"
    status: completed
  - id: p1-agent-trace-model
    content: "Add AgentTrace/TraceSpan/PipelineHits in packages/eval/traces.py (+ optional trace_id on AgentTurnOutput)"
    status: completed
  - id: p1-taxonomy-module
    content: "Add packages/eval/taxonomy.py with FAILURE_CATEGORIES, ROOT_COMPONENTS, ReviewTaxonomy validation"
    status: completed
  - id: p1-agentcore-spans
    content: "Emit agent.turn + tool/retrieval child spans from run_agent_turn; wire redaction"
    status: completed
  - id: p1-feedback-api
    content: "Implement POST /eval/feedback and GET /eval/traces/{id} on Agent API using EvalStore + reviews.jsonl"
    status: completed
  - id: p1-health-api
    content: "Implement GET /eval/health aggregating out/eval-*.json + release_gate stub"
    status: completed
  - id: p1-promote-taxonomy
    content: "Extend governance promote to require source_trace_id + primary_category; POST /eval/promote"
    status: completed
  - id: p1-retrieval-harness
    content: "Add packages/eval/retrieval fixture harness for Docs + ApiIndex + EAKG stage scores"
    status: completed
  - id: p1-l6-skeleton
    content: "Add packages/eval/safety L6 hard-fail skeleton + make eval-l6"
    status: completed
  - id: p1-ci-eval-gate
    content: "Add .github/workflows/eval-gate.yml for eval-mcp-l1, L2–L5, L9 validate"
    status: completed
  - id: p1-portal-shell
    content: "Add web_ui Observe/Evaluate/Learn shell with Langfuse deep-links, feedback form, health strip, candidates list"
    status: completed
  - id: p1-tests-gates
    content: "Unit/API tests for taxonomy, feedback, promote draft-only; mypy strict; graphify update"
    status: completed
  - id: p2-native-trace-explorer
    content: "Native Trace Explorer + review workbench (highlights, timeline, promote/adjudicate actions)"
    status: pending
  - id: p2-signal-inbox
    content: "Signal Inbox ranking (severity×frequency) over sampled fails and L8 breaches"
    status: pending
  - id: p2-multi-reviewer
    content: "Multi-reviewer UX + block promote on disagreement; wire agreement CLI into portal"
    status: pending
  - id: p2-improvement-cycles
    content: "ImprovementCycle JSONL + Learn UI baseline/post/regress"
    status: pending
  - id: p2-online-sample-board
    content: "Production sampling board UI over L8 sample_score + enqueue CTA"
    status: pending
  - id: p2-tests-gates
    content: "Tests for Signal sort, cycle regression, disagreement gate; quality gates"
    status: pending
  - id: p3-experiment-compare
    content: "Experiment compare API/UI for two runs on same case set"
    status: pending
  - id: p3-suggested-actions
    content: "Suggested actions cards on failure clusters (advisory only, no auto-apply)"
    status: pending
  - id: p3-eval-copilot
    content: "Optional Eval Copilot chat grounded on reviews/scores (advisory)"
    status: pending
  - id: p3-session-cost
    content: "Session multi-turn explorer stub + real token/cost on traces when providers expose them"
    status: pending
  - id: p3-judgy-calibrate
    content: "Optional judgy integration behind governance calibrate (requires dep approval)"
    status: pending
  - id: p3-tests-docs
    content: "Phase 3 tests; update LAYERS.md/CONTEXT.md/logs.md; graphify update"
    status: pending
isProject: false
---

# Eval Improvement Platform — Implementation Plan

**Story**: [./eval-improvement-platform.story.md](./eval-improvement-platform.story.md)  
**Spec**: [./eval-improvement-platform.spec.md](./eval-improvement-platform.spec.md)

## Progress

| Phase | Focus | Todos |
|---|---|---|
| P1 | Observe foundation + thin portal + APIs + harnesses | `p1-*` |
| P2 | Native workbench, Signal, cycles, multi-reviewer | `p2-*` |
| P3 | Experiments, Copilot, session/cost, judgy | `p3-*` |

---

## Phase 1 — Observe foundation

**Todos in this phase**: `p1-*`

### Goal

Complete FR-001–FR-010, FR-017–FR-020 (thin), SC-001–SC-003 path enabled; error analysis usable before native polish.

### Work

1. **Approval** — AgentCore → TelemetryProvider (`p1-approval-instrumentation`).
2. **Models** — `traces.py`, `taxonomy.py`; optional `AgentTurnOutput.trace_id`.
3. **Instrumentation** — spans on turn/tools; redaction via safety.
4. **APIs** — `/eval/feedback`, `/eval/traces/{id}`, `/eval/health`, `/eval/promote`.
5. **Harnesses** — retrieval stages + L6 skeleton + Makefile targets.
6. **CI** — restore eval-gate workflow.
7. **Portal shell** — Observe/Evaluate/Learn nav; Langfuse links; feedback form; health badges; candidates list.

### Success criteria

- Feedback round-trips to reviews.jsonl / EvalStore.
- Health endpoint reads layer reports without mixing `ops.*`.
- Promote writes draft only.
- CI runs deterministic L1–L5 + L9 validate.

### Notes

- **2026-11-03**: User “lets build” = approval for AgentCore → TelemetryProvider spans (`agent.turn` + `mcp.tool.call`). Shipped Phase 1 core.
- Do not add Phoenix/Arize/Promptfoo deps.
- Do not lower `thresholds.py`.
- Tool child spans fire around each tools_client.call; parent span fail-open.

---

## Phase 2 — Evaluate + Learn workbench

**Todos in this phase**: `p2-*`

### Goal

FR-011–FR-014, Signal, native review (SC-004–SC-006).

### Work

- Native Trace Explorer + workbench layout per spec §15.
- Signal ranking algorithm per spec §3.2.
- Multi-reviewer + adjudication queue UX.
- ImprovementCycle persistence + UI.
- L8 online sample board.

### Success criteria

- Seeded retrieval-miss vs generation-miss show different stage attribution.
- Disagreement blocks promote.
- Cycle shows improved/unchanged/regressed.

### Notes

- LLM judges only after ~100 labels; use existing calibrate kappa first.

---

## Phase 3 — Continual improvement UX

**Todos in this phase**: `p3-*`

### Goal

FR-015–FR-016 and advanced Observe/Evaluate charts; advisory Copilot.

### Work

- Experiment compare.
- Suggested actions (no auto-apply).
- Optional Eval Copilot.
- Session strip + cost/tokens when available.
- Optional `judgy` (approval for new dependency).

### Success criteria

- Compare lists new_pass/new_fail.
- Suggestions never mutate MCP auth or live prompts.
- Docs/LAYERS/CONTEXT updated; graphify refreshed.

### Notes

- Engineering KG stage remains N/A until `search_code` on agent path.

---

## Dependencies between phases

```text
P1 models + spans → P1 APIs → P1 portal shell
P1 feedback taxonomy → P2 Signal + multi-reviewer
P1 health/runs → P2 cycles + P3 compare
P2 labels volume → P3 judgy/judges
```

## Explicit non-goals (reminders)

- Second eval database / Arize AX as SoR
- Auto-applied AI fixes
- Lowering sacred thresholds
- Thick UI before AgentTrace + feedback exist
