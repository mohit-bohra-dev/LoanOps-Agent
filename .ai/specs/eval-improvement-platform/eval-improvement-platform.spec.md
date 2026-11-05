# Technical Specification: Eval Improvement Platform

**Feature**: `eval-improvement-platform`  
**Story**: [./eval-improvement-platform.story.md](./eval-improvement-platform.story.md)  
**Status**: Draft · **Created**: 2026-11-03  

Cites story IDs (`FR-*`, `NFR-*`, `SC-*`). Implements HOW only.

---

## 1. Architecture

### 1.1 High-level

```text
┌──────────────────┐   spans/scores    ┌─────────────────────┐
│ AgentCore + MCP  │ ────────────────► │ TelemetryProvider   │
│ /chat, tools     │                   │ EvalStoreProvider   │
└────────┬─────────┘                   │ (jsonl | langfuse)  │
         │ feedback                    └──────────┬──────────┘
         ▼                                        │
┌──────────────────┐   read reports/labels         │
│ Agent API        │ ◄─────────────────────────────┤
│ POST /feedback   │                               │
│ GET  /eval/*     │                               │
└────────┬─────────┘                               │
         │                                         │
         ▼                                         ▼
┌──────────────────┐                    ┌─────────────────────┐
│ Eval Portal UI   │  deep-link         │ Langfuse UI (SoR)   │
│ Observe|Evaluate │ ─────────────────► │ annotation queues   │
│ Learn            │                    └─────────────────────┘
└──────────────────┘
         ▲
         │ make eval-* / governance promote
┌──────────────────┐
│ LoanOps.Eval     │  L1–L5, L6*, L7–L9, retrieval stages
│ + data/eval/*    │  registry, candidates, cycles JSONL
└──────────────────┘
```

**SoR**: EvalStore (ADR-032). Langfuse when `EVAL_STORE__PROVIDER=langfuse`; else JSONL under `EVAL_STORE__JSONL_DIR`. Portal never owns a second database (`NFR-005`).

### 1.2 Components

| Component | Responsibility | Interface |
|---|---|---|
| AgentCore instrumentation | Emit `agent.turn` + child spans for tools/retrieval | `TelemetryProvider.span` |
| `AgentTrace` envelope | Canonical Pydantic model for portal/API | `packages.eval.traces` or `packages.common.schemas` |
| Feedback API | Persist `ReviewLabel` + taxonomy metadata | FastAPI routes on Agent API |
| Stage evaluators | Offline Recall@K / L2–L5 / L6 | `packages.eval.retrieval`, existing scorers |
| Portal shell | Observe / Evaluate / Learn | React in `apps/web_ui` (or dedicated route group) |
| Governance | validate / promote / agreement / calibrate | existing `packages.eval.governance` |

### 1.3 Data flow — review to golden

```text
trace_id (agent turn)
  → human ReviewLabel (queue=loanops-ops-review|loanops-error-analysis)
  → optional second label → agreement / adjudication queue
  → promote_candidates() → data/eval/candidates/<id>.jsonl + draft registry row
  → human PR merges approved registry + golden JSONL
  → make eval-* / L9 validate
```

---

## 2. Data Model

### 2.1 `AgentTrace` (canonical envelope) — FR-001

New module: `projects/LoanOps.Eval/packages/eval/traces.py` (preferred) re-exported for API.

```python
class TraceSpan(BaseModel):
    span_id: str
    parent_span_id: str | None = None
    name: str  # agent.turn | mcp.tool.call | retrieval.docs | ...
    tool: str | None = None
    args: dict[str, Any] = Field(default_factory=dict)
    result: str | None = None  # may be redacted
    result_summary: str | None = None
    latency_ms: float = 0.0
    is_error: bool = False
    attributes: dict[str, Any] = Field(default_factory=dict)

class PipelineHits(BaseModel):
    eakg: list[dict[str, Any]] = Field(default_factory=list)
    api_index: list[dict[str, Any]] = Field(default_factory=list)
    docs: list[dict[str, Any]] = Field(default_factory=list)
    graph_rag: list[dict[str, Any]] = Field(default_factory=list)
    code: list[dict[str, Any]] = Field(default_factory=list)

class AgentTrace(BaseModel):
    trace_id: str
    environment: Literal["prod", "eval", "local"] = "local"
    session_id: str | None = None
    user_query: str
    final_answer: str = ""
    citations: list[CitationItem] = Field(default_factory=list)
    refusal: str | None = None
    escalation: EscalationItem | None = None
    spans: list[TraceSpan] = Field(default_factory=list)
    pipeline_hits: PipelineHits = Field(default_factory=PipelineHits)
    latency_ms: float = 0.0
    token_usage: dict[str, int] = Field(default_factory=dict)
    cost_usd: float | None = None
```

**Validation**: `trace_id` non-empty; `user_query` non-empty; span `name` non-empty. Redaction: apply `packages.safety` before persisting `result` when environment is `prod` (`NFR-006`).

**Mapping from today**: Build from `AgentTurnOutput` + telemetry spans. Today `ToolCallItem.result_summary` alone is insufficient — instrumentation must capture args/results on spans.

### 2.2 Review taxonomy metadata — FR-002…FR-006, FR-018

Extend usage of `ReviewLabel` without immediate ABC break: store structured fields in EvalStore score comment JSON **or** parallel JSONL `data/eval/reviews.jsonl` until provider bump.

```python
class ReviewTaxonomy(BaseModel):
    primary_category: str  # must be in FAILURE_CATEGORIES
    failure_categories: list[str] = Field(default_factory=list)
    severity: Literal["blocker", "major", "minor"]
    root_component: str
    span_refs: list[str] = Field(default_factory=list)  # span_id or "answer:start:end"
    department: str | None = None
    adjudication_of: str | None = None  # review id if resolving
    highlight_note: str | None = None

FAILURE_CATEGORIES = frozenset({
    "wrong_api_selected", "missing_api", "incorrect_arguments",
    "missing_policy_context", "incorrect_answer", "unauthorized_access",
    "unnecessary_tool_calls", "hallucination", "sop_violation",
    "tool_error_unhandled", "other",
})

ROOT_COMPONENTS = frozenset({
    "capability_retrieval", "api_index", "eakg", "sop_retrieval",
    "graph_rag", "agent_planning", "agent_orchestration", "generation",
    "mcp_security", "mcp", "unknown",
})
```

**Rules**: If `label` ∈ {`fail`,`bad`,`incorrect`}, `primary_category` and `severity` required. `primary_category` ∈ `FAILURE_CATEGORIES`. Secondary list may omit primary (UI merges).

Queues (existing names + new):

| Queue | Purpose |
|---|---|
| `loanops-error-analysis` | Manual / portal error analysis |
| `loanops-ops-review` | L8 sampled fails (existing) |
| `loanops-adjudication` | Disagreement (existing L9 doc) |

### 2.3 `StageScore` naming — FR-011

Use `ScoreRecord.name`:

| Name | Meaning |
|---|---|
| `eval.stage.capability_search` | 0/1 or Recall@K |
| `eval.stage.api_index` | 0/1 or Recall@K / MRR |
| `eval.stage.sop_retrieval` | 0/1 or Relevance@K |
| `eval.stage.graphrag` | 0/1 evidence flag |
| `eval.stage.orchestration` | aggregate L2–L4 pass |
| `eval.stage.answer` | L5 pass |
| `eval.stage.security` | L6 hard-fail (0 = fail) |
| `eval.layer.{n}.*` | existing layer metrics |
| `ops.*` | production only (`NFR-007`) |

### 2.4 `ImprovementCycle` — FR-014

Path: `data/eval/cycles/<cycle_id>.json`

```python
class ImprovementCycle(BaseModel):
    cycle_id: str
    top_failure_category: str
    hypothesis: str
    change_refs: list[str] = Field(default_factory=list)  # PR URLs or commit SHAs
    baseline_run_id: str
    post_run_id: str | None = None
    baseline_rate: float | None = None
    post_rate: float | None = None
    regressed: bool | None = None
    notes: str = ""
```

### 2.5 Golden candidate extension — FR-007, FR-008

`promote_candidates` output must include:

```json
{
  "id": "...",
  "source_trace_id": "...",
  "primary_category": "incorrect_answer",
  "severity": "major",
  "root_component": "generation",
  "reviewer": "...",
  "rubric": "outcome",
  "label": "fail",
  "comment": "..."
}
```

Registry draft `status` stays `draft` until PR sets `approved` (existing L9).

---

## 3. Algorithms & Logic

### 3.1 Build `AgentTrace` from a live turn

```
function build_agent_trace(turn_id, query, output, spans, hits, env):
  redacted_spans ← map redact_span over spans
  return AgentTrace(
    trace_id=turn_id,
    environment=env,
    user_query=query,
    final_answer=output.answer,
    citations=output.citations,
    refusal=output.refusal,
    escalation=output.escalation,
    spans=redacted_spans,
    pipeline_hits=hits,
    latency_ms=sum(span.latency_ms)
  )
```

Complexity: O(S) in span count.

### 3.2 Signal ranking — FR-012

```
score(item) = severity_weight[item.severity] * item.frequency_7d * (1.5 if unlabeled else 1.0)
severity_weight = {blocker: 3, major: 2, minor: 1}
```

Sort descending; stable tie-break by newest `created_at`.

### 3.3 Improvement cycle regression — FR-014, SC-006

```
if post_run missing: regressed ← null
else if post_rate > baseline_rate + ε: regressed ← true   # higher failure rate
else: regressed ← false
```

ε default `0.02` absolute on category fail rate.

### 3.4 Experiment compare — FR-015

Join cases by `case_id`. Classify: `new_pass`, `new_fail`, `unchanged_pass`, `unchanged_fail`, `missing_in_a`, `missing_in_b`.

---

## 4. API Design

Base: Agent API (`apps.agent_api`). Auth: same as `/chat` (existing). No new public unauthenticated surface.

### 4.1 `POST /eval/feedback` — FR-002…FR-006

```json
{
  "trace_id": "string",
  "label": "pass" | "fail",
  "primary_category": "incorrect_answer",
  "failure_categories": ["hallucination"],
  "severity": "major",
  "root_component": "generation",
  "comment": "string",
  "span_refs": ["answer:12:40"],
  "department": "qa",
  "queue": "loanops-error-analysis",
  "rubric": "outcome",
  "rubric_version": "1"
}
```

Response `201`: `{ "ok": true, "queue": "...", "trace_id": "..." }`.  
Validation errors `422`. On fail label without category → `422`.

Implementation: `enqueue_review` + persist taxonomy JSONL/score via `get_eval_store_provider()`.

### 4.2 `GET /eval/traces/{trace_id}` — FR-001, FR-017

Returns `AgentTrace` JSON. If only Langfuse has it, provider `fetch_traces` filtered by id; include `langfuse_url` when configured.

### 4.3 `GET /eval/health` — FR-010, FR-020

Aggregates latest `out/eval-*.json` and/or EvalStore run scores:

```json
{
  "layers": {"1": {"passed": true, "at": "..."}, "...": {}},
  "ops_separate": true,
  "review_coverage_7d": 0.0,
  "release_gate": {"ready": false, "reasons": ["...")]}
}
```

`review_coverage_7d` formula: labeled_unique_traces / sampled_traces (document in CONTEXT when product sets OQ-001 threshold).

### 4.4 `POST /eval/promote` — FR-007

Body: `{ "trace_id": "...", "reviewer": "..." }`. Calls `promote_candidates` for that label set. Does not auto-approve (`FR-008`).

### 4.5 Portal routes (UI)

| Path | Area | Phase |
|---|---|---|
| `/eval` | redirect Observe | 1 |
| `/eval/observe` | Trace list + deep-links | 1 |
| `/eval/observe/:traceId` | Trace + feedback form | 1 |
| `/eval/evaluate` | Health strip | 1 |
| `/eval/learn/promote` | Candidate inbox | 1 |
| `/eval/observe/signal` | Signal Inbox | 2 |
| `/eval/learn/cycles` | Improvement cycles | 2 |
| `/eval/learn/compare` | Experiment compare | 3 |
| `/eval/learn/copilot` | Eval Copilot | 3 |

---

## 5. Technical Decisions

### D1 — Langfuse/EvalStore SoR; Arize UX only

- **Decision**: Keep ADR-032; portal copies Observe/Evaluate/Learn IA from [arize.com](https://arize.com/).
- **Alternatives**: Phoenix/Arize AX as SoR — rejected (duplicate platform, local-first break).
- **Consequences**: Deep-links required Phase 1; native explorer Phase 2.

### D2 — Taxonomy in metadata before ABC break

- **Decision**: Ship taxonomy via review JSONL + score metadata; bump `ReviewLabel` in provider_contracts when agreement/promote need typed fields.
- **Alternatives**: Immediate ABC change — slower, couples portal to contracts bump.
- **Consequences**: Temporary dual read path in promote CLI.

### D3 — Error analysis before LLM judges — FR-019

- **Decision**: Phase 1–2 human taxonomy; judges only after ≥100 labels and kappa/TPR-TNR gates (existing calibrate + future `judgy`).
- **Alternatives**: Ship LLM judges first — rejected (guide/Hamel).

### D4 — AgentCore TelemetryProvider instrumentation

- **Decision**: Required Phase 1; spans `agent.turn`, child `mcp.tool.call` / retrieval names.
- **Alternatives**: Reconstruct only from `AgentTurnOutput` — insufficient for FR-001.
- **Consequences**: May need ADR/approval note in AGENTS.md “approval required” for observability wiring — record in plan Notes when starting.

### D5 — No auto-apply Copilot — FR-016

- **Decision**: Suggestions open PR checklist / copy patch; never write MCP auth or live prompts.
- **Alternatives**: Auto-remediation — rejected for security.

---

## 6. File Structure

### New

| Path | Purpose |
|---|---|
| `.ai/specs/eval-improvement-platform/*` | This package |
| `packages/eval/traces.py` | `AgentTrace` models |
| `packages/eval/taxonomy.py` | categories, validation |
| `packages/eval/retrieval/` | stage harness (Docs, ApiIndex, EAKG) |
| `packages/eval/safety/` | L6 hard-fail suite skeleton |
| `packages/eval/cycles.py` | ImprovementCycle IO |
| `data/eval/reviews.jsonl` | taxonomy-rich labels (jsonl provider) |
| `data/eval/cycles/` | cycle records |
| `apps/agent_api/.../eval_routes.py` | feedback/health/promote |
| `apps/web_ui/src/eval/*` | Observe/Evaluate/Learn pages |

### Modified

| Path | Change |
|---|---|
| `packages/agent_core/_agent.py` (or turn runner) | Emit telemetry spans |
| `packages/eval/governance/promote.py` | Require taxonomy + source_trace_id |
| `packages/eval/governance/agreement.py` | Read taxonomy metadata |
| `Makefile` | `eval-l6`, `eval-retrieval` targets |
| `docs/eval/LAYERS.md` | L6 status → built when suite lands |
| `.env.example` | document feedback-related settings if any (prefer zero new env) |
| `.github/workflows/eval-gate.yml` | restore CI (missing today) |

---

## 7. Implementation Details

### 7.1 AgentCore spans

On each `run_agent_turn`:

1. Start span `agent.turn` with attrs `user_query` (redacted), `loan_id` if present.
2. For each tool call: child span; attributes `tool`, `args` (size-capped), `outcome`.
3. On completion: set output answer hash/length; record `trace_id` on `AgentTurnOutput` extension **or** response header `X-LoanOps-Trace-Id` for UI.

Prefer extending `AgentTurnOutput` with optional `trace_id: str | None = None` in `packages.common.schemas` (schema additive).

### 7.2 Feedback handler (pseudocode)

```
async def post_feedback(body, reviewer):
  validate_taxonomy(body)
  store = get_eval_store_provider()
  await store.enqueue_review(body.queue, body.trace_id)
  append reviews.jsonl with ReviewLabel + ReviewTaxonomy
  await store.flush()
```

### 7.3 Retrieval stage harness

Package `packages.eval.retrieval`:

- Load golden rows `{id, query, expect: {capability_ids|operation_ids|doc_ids}}`
- Call underlying services with fixtures (no live SSO required for CI)
- Emit `eval.stage.*` scores via EvalStore run

Reuse patterns from `api_index/tests/test_scale.py::test_top5_recall`.

### 7.4 L6 skeleton

`packages.eval.safety`: cases for prompt injection in tool result, write attempt on `call_sse_api`, scope bypass. Non-compensatory: any fail → report `thresholds_passed=false` regardless of other layers when aggregated in release gate.

### 7.5 Portal Phase 1 (thin)

- Observe: table of recent `trace_id` from jsonl/Langfuse; link button; detail page with feedback form posting `/eval/feedback`.
- Evaluate: fetch `/eval/health`; show layer badges.
- Learn: list `data/eval/candidates/` via API or static fetch in dev; Promote button → `/eval/promote`.

Phase 2 adds Signal ranking client + native timeline renderer from `AgentTrace.spans`.

---

## 8. Integration Points

| System | Method | Auth | Errors |
|---|---|---|---|
| EvalStore | async provider | env provider select | degrade to jsonl |
| TelemetryProvider | spans/metrics | same | swallow? no — log + continue turn |
| Langfuse UI | HTTPS deep-link | user SSO to Langfuse | show copy trace_id if URL absent |
| Existing eval CLIs | subprocess/make | local | surface exit codes in health |

---

## 9. Edge Cases & Error Handling

| Story edge | Handling |
|---|---|
| Redacted tool results | Show `result_summary` + badge `redacted`; review still allowed |
| No tools | Timeline empty state; categories still valid |
| Conflicting department rubrics | Store `department` + `rubric`; agreement keyed by `(trace_id, rubric)` |
| Source trace deleted | Candidate keeps embedded snapshot fields written at promote time |
| Score name collision | UI namespaces tabs Offline vs Prod; reject writing `ops.*` into `eval` env |
| Severity without category | `422` on API |
| Code search N/A | Omit `eval.stage.code` until tool on agent path |
| Low sample volume | Signal shows “insufficient sample” rather than fake ranks |

---

## 10. Security Considerations

- Server-side MCP auth unchanged (`NFR-003`).
- Feedback API authenticated as chat users; reviewers cannot elevate MCP role.
- Prod traces redacted before portal JSON (`NFR-006`).
- Copilot/suggestions cannot call `execute_tool` or mutate `.env`.
- Audit: every feedback/promote append-only with reviewer + timestamp (`NFR-004`).

---

## 11. Performance Considerations

- Trace detail fetch p95 < 2s local jsonl for last 7 days index (NFR UX).
- Feedback POST p95 < 500ms excluding Langfuse network when jsonl.
- Signal ranking over ≤10k items in memory; if larger, pre-aggregate daily counts JSONL.
- Do not run Ragas on every Signal open — offline jobs only.

---

## 12. Testing Strategy

| Layer | Scenarios | Maps to |
|---|---|---|
| Unit | taxonomy validation; Signal sort; cycle regression ε; compare flip classes | FR-003, FR-012, FR-014, FR-015 |
| Unit | `build_agent_trace` redaction | NFR-006 |
| Contract | EvalStore enqueue + jsonl roundtrip | FR-002 |
| API | feedback 201/422; promote draft-only | FR-007, FR-008 |
| Eval | retrieval harness fixtures; L6 injection fixture | FR-011 |
| Governance | disagreement blocks promote | FR-013, SC-005 |
| Manual | ~100 trace labeling pilot | SC-001 |

Coverage target: new modules ≥ existing Eval package norms; mypy `--strict` on new code.

---

## 13. Configuration

Prefer **zero new env vars**. If Langfuse deep-link base needed and not already present, reuse `TELEMETRY__LANGFUSE__*` host to build URLs. Any new var requires AGENTS.md approval — default: derive from existing settings only.

---

## 14. Dependencies

| Dep | Role |
|---|---|
| Existing `ragas` | L5 only; not expanded as portal SoR |
| Future optional `judgy` | Phase 3 calibration — requires approval before add |
| React web_ui stack | Portal pages |
| provider_contracts EvalStore | SoR |

No Phoenix/Arize AX/Promptfoo/DeepEval runtime dependency.

---

## 15. Portal Screen Spec (IA)

### Observe

- **Trace Explorer**: list + detail (`AgentTrace`); Langfuse button.
- **Review workbench** (Phase 2 layout): left answer+highlights, center timeline, right form, footer Promote / Adjudicate / Langfuse.
- **Signal Inbox** (Phase 2): ranked cards → workbench.

### Evaluate

- Layer health badges L1–L9 (L6 when present).
- Pipeline stage strip.
- Tabs: Offline `eval.*` | Prod `ops.*`.
- Release gate panel: CI statuses + review coverage.

### Learn

- Promote inbox (candidates).
- Improvement cycles list + detail.
- Experiment compare (Phase 3).
- Suggested actions / Eval Copilot (Phase 3, advisory).

Guiding questions in nav labels:

- Observe: “What did the agent do?”
- Evaluate: “Are we better or worse?”
- Learn: “Did our fix help?”

---

## 16. Open Technical Questions

- **TQ-001**: Exact AgentCore file/function for span injection (confirm after `graphify` on `run_agent_turn`) — resolve at Phase 1 start.
- **TQ-002**: Whether to add `trace_id` on `AgentTurnOutput` vs response header only — prefer field on schema (additive).
- **TQ-003**: Provider ABC bump timing for typed taxonomy on `ReviewLabel` — after Phase 1 JSONL path proven.

## 17. References

- Story: [./eval-improvement-platform.story.md](./eval-improvement-platform.story.md)
- Assessment: `docs/eval/enterprise-eval-platform-assessment.md`
- LAYERS: `docs/eval/LAYERS.md`
- ADR-032 in `decisions.md`
- Hamel evals; ombharatiya study guide; arize.com (UX only)
