# Enterprise AI Evaluation & Improvement Platform — Architecture Assessment

**Status:** Evidence-based analysis only (no code changes).  
**Date:** 2026-11-10  
**Supersedes:** assessment dated 2026-11-03 (portal, CI, AgentCore telemetry, agent tool surface now present).  
**Related:** ADR-032, `docs/eval/LAYERS.md`, `.ai/specs/eval-improvement-platform/`, `provider_contracts/eval_store/`.  

**Legend:** Implemented | Partially implemented | Planned | Missing | Not applicable  

**Primary question answered:** What do we already have, what can we reuse from open source, what must we build, and what is the shortest sensible roadmap?

---

## 1. Executive Summary

LoanOps is **not** a greenfield eval product. It already has a working **nine-layer offline evaluation engine**, sacred golden gates (Ragas + citation metrics), MCP contract suites, retrieval stage harness, EvalStore/Langfuse provider lockstep, Agent API `/eval/*` routes, and a React **Eval Portal** (scenario board, spreadsheet matrix, trace review drawer, promote-to-candidate).

What is missing for an **enterprise Evaluation & Improvement Platform** is not another metrics library. Gaps are:

1. **Product hardening** — AuthN/RBAC on Agent API + portal; audit of reviews; multi-reviewer adjudication UX.
2. **Governance depth** — versioned golden lifecycle UI; production-trace → candidate → human-approve → golden (no auto-promote).
3. **Observability completeness** — Langfuse as SoR exists; deep agent/MCP span fidelity and cost/token accounting still thin; portal still dual-modes with mock/demo data.
4. **Security eval (L6)** — skeleton only; must remain non-compensatory.
5. **CI completeness** — `eval-gate.yml` covers L1–L5, L6 skeleton, retrieval, L9 validate; omits L7/L8 and sacred `make eval`.
6. **Multi-target platform** — today LoanOps-shaped; need a shared evaluation model so other agents/MCP servers can plug in.

**Reuse strategy (locked):** Keep **Langfuse + EvalStore** as observability/dataset/score SoR (ADR-032). Keep **in-repo deterministic scorers** as the evaluation engine. Use **MCPJam** as optional MCP *interactive* testing / CI probe — not as SoR. Do **not** adopt MLflow, Opik, or DeepEval as a second platform. Optionally cherry-pick DeepEval/Promptfoo *patterns* or isolated red-team YAML later; never duplicate traces/datasets.

**Shortest path to a working platform:** Harden what exists into one end-to-end loop — *run scenario → capture trace → deterministic + optional LLM scores → human matrix review → promote draft golden → regression gate* — before building department tenants or analytics warehouses.

---

## 2. Existing Implementation Inventory

### 2.1 Capability rollup

| Area | Status | Evidence |
|---|---|---|
| Agent API (`/chat`, `/health`, `/mcp/*`) | **Implemented** | `projects/LoanOps.AgentApi/apps/agent_api/main.py`, `mcp_routes.py` |
| AgentCore turn loop + agent_runtime | **Implemented** | `packages/agent_core/_agent.py` `run_agent_turn`; `get_agent_runtime_provider()` |
| Agent telemetry spans | **Implemented** (depth **Partial**) | `_agent.py` uses `get_telemetry_provider()`; cost often stub |
| MCP Streamable HTTP server | **Implemented** | `packages/mcp_server/server.py` `create_app`, `execute_tool` |
| MCP auth (static bearer) + GET-only policy | **Implemented** | `StaticTokenVerifier`, `policy.py` |
| Capability bind / permission enforce | **Partially implemented** | `capability_bind.py`, `capability_authz.py`; flags default **off** |
| Modular vs MCP tools client | **Implemented** | `packages/tools/factory.py`; default `modular` |
| Agent tool surface ≈ MCP tools | **Implemented** | `_SSE_ANSWER_TOOLS` (10 tools incl. EAKG + docs) |
| EAKG / capability search | **Implemented** | `LoanOps.Eakg`, MCP tools `search_capabilities`…`search_code` |
| ApiIndex two-stage search | **Partially implemented** | Built; `API_INDEX__ENABLED` default false |
| Docs / SOP RAG | **Implemented** | `LoanOps.Docs`, `search_docs` |
| GraphRAG | **Partially implemented** | Exists; `graphrag.enabled` default false |
| Audit JSONL | **Implemented** | `get_audit_sink_provider()`; AppInsights not implemented |
| Session / prompt stores | **Implemented** | memory/file defaults; Postgres session optional |
| UI AuthN / RBAC | **Missing** | Open fetch; reviewer name in localStorage |
| Agent API AuthN | **Missing** | No JWT/bearer on `/chat` or `/eval/*` |
| Nine-layer eval package | **Implemented** (L6 **Partial**) | `projects/LoanOps.Eval/packages/eval/` |
| Golden datasets | **Implemented** | `data/golden.jsonl`, `golden.full.jsonl`, layer fixtures under `data/eval/` |
| Eval API | **Implemented** | `eval_routes.py` — feedback, matrix, traces, health, promote |
| Eval Portal UI | **Implemented** (enterprise UX **Partial**) | `EvalPortal.tsx`, `ScenarioBoard`, `EvalSpreadsheet`, `TraceReviewDrawer` |
| Multi-reviewer disagreement gate | **Planned** | `docs/eval/multi-user-scenario-testing.md`; plan `p2-multi-reviewer` |
| Langfuse docker + providers | **Implemented** | `docker-compose.langfuse.yml`; Telemetry + EvalStore adapters |
| EvalStore contract | **Implemented** | `provider_contracts/eval_store/` |
| CI eval gate | **Partially implemented** | `.github/workflows/eval-gate.yml` (no L7/L8/sacred golden) |
| Full product CI (lint/unit/deploy) | **Missing / Partial** | Only eval-gate workflow found |
| Ragas LLM metrics | **Implemented** | `eval/run.py` `_compute_ragas_metrics`; skippable |
| DeepEval / Promptfoo / Opik / MLflow | **Missing** (by design) | ADR-032 non-goals |

### 2.2 Evaluation layers (engine)

| Layer | Question | Status | Paths |
|---|---|---|---|
| L1 MCP | Protocol/contracts/functional/errors/perf | **Implemented** | `eval/mcp/` |
| L2 Selection | Right tools / alternatives / forbidden | **Implemented** | `eval/selection/` |
| L3 Arguments | Arg correctness + constraints | **Implemented** | `eval/arguments/` |
| L4 Trajectory | Constraint path (not exact sequence) | **Implemented** | `eval/trajectory/` |
| L5 Outcomes | Grounding, citations, optional Ragas | **Implemented** | `eval/outcomes/`, `eval/run.py` |
| L6 Safety | Hard-fail security | **Partially implemented** | `eval/safety/layer6.py` skeleton |
| L7 Robustness | N-repeat / faults / Wilson LB | **Implemented** (not in CI) | `eval/robustness/` |
| L8 Operations | Prod SLOs vs offline | **Implemented** (not in CI) | `eval/operations/` |
| L9 Governance | Registry, rubrics, promote, agreement | **Implemented** | `eval/governance/` |
| Retrieval stages | Multi-pipeline recall harness | **Implemented** | `eval/retrieval/` |

### 2.3 Human review & taxonomy

| Item | Status | Evidence |
|---|---|---|
| Failure categories + root components | **Implemented** | `eval/taxonomy.py` `FAILURE_CATEGORIES`, `ROOT_COMPONENTS` |
| AgentTrace persist from `/chat` | **Implemented** | `eval/traces.py`; `main.py` persist |
| Feedback → reviews.jsonl + EvalStore | **Implemented** | `POST /eval/feedback` |
| Spreadsheet matrix | **Implemented** | `GET /eval/matrix`, `EvalSpreadsheet.tsx` |
| Promote draft candidates only | **Implemented** | `POST /eval/promote` → `promote_candidates` |
| Assignment / adjudication workflow | **Planned** | Spec plan; not productized |
| Department rubrics | **Partially implemented** | Rubric YAMLs under `data/eval/rubrics/`; no dept RBAC |

### 2.4 Prior assessment corrections (2026-11-03 → 2026-11-10)

| Prior claim | Current fact |
|---|---|
| No Evaluation Portal | Portal exists (`EvalPortal`, scenarios, matrix, drawer) |
| No `.github/workflows` | `eval-gate.yml` present |
| AgentCore untraced | Telemetry hooks present in `_agent.py` |
| Agent 4 tools vs MCP 10 | Agent exposes 10 tools aligned with MCP |

---

## 3. Current Architecture

```text
┌──────────────── web_ui (Vite) ────────────────┐
│ ChatPane ──POST /chat (SSE)                   │
│ EvalPortal ── /eval/matrix|feedback|promote   │
│ ScenarioBoard (Isolated chat, no session_id)  │
└───────────────┬───────────────┬───────────────┘
                ▼               ▼
┌──────── Agent API :8000 ──────────────────────┐
│ safety → run_agent_turn → audit + AgentTrace  │
│ mcp_routes (HTTP tool wrapper)                │
│ eval_routes (review / matrix / promote)       │
└───────┬───────────────────┬───────────────────┘
        ▼                   ▼
 AgentCore + Runtime    ToolsClient
 (LangGraph|native)     modular | mcp
        │                   │
        ▼                   ▼
 TelemetryProvider ──► Langfuse|console
        │
        ▼
 MCP :8001 (when mcp mode) → ModularToolsClient
        │
        ├─ SSE / ApiIndex ─► enterprise REST
        ├─ Docs / GraphRAG ─► Qdrant
        └─ EAKG / CapabilityKg ─► files|SPARQL

Offline (not request path):
  make eval* → LoanOps.Eval L1–L9 + retrieval
  EvalStore (jsonl|langfuse) for datasets/runs/scores/reviews
```

**MCP / Agent / System eval mapping today**

| Dimension | How expressed today |
|---|---|
| **A. MCP evaluation** | L1 suites + `mcp_server/eval_run.py` + L8 MCP SLOs |
| **B. AI Agent evaluation** | L2–L5, L7; golden `run_eval`; portal scenario runs via `/chat` |
| **C. AI System evaluation** | Partial — chat UX manual; L8 ops; no formal e2e UX/perf suite |

**Recommendation:** Keep **one evaluation engine** (LoanOps.Eval + EvalStore) with **three target adapters** (MCP harness, Agent harness, System/e2e harness). Shared model: `Scenario → Target → Dataset → Criteria → Run → TraceRef → Scores → Reviews → Promotion`.

---

## 4. Open-Source Project Comparison

Sources: official docs/GitHub READMEs fetched 2026-11-10 (Langfuse, MCPJam, DeepEval, Promptfoo, Opik, MLflow). Capabilities verified against documentation, not assumed.

### 4.1 Project profiles

| Project | Primary purpose | Stack | License | Self-host | MCP support |
|---|---|---|---|---|---|
| **Langfuse** | LLM observability + datasets/experiments/scores/annotation | TS app + ClickHouse/Postgres; Python/JS SDKs | OSS (+ paid add-ons) | Yes (compose/Helm) | Langfuse *data* MCP server (manage datasets/scores); **not** an MCP *server under test* tool |
| **MLflow** | MLOps + GenAI tracing/eval datasets/scorers | Python; tracking server + SQL backend for eval datasets | Apache-2.0 | Yes | No first-class MCP inspector; agent/tool scorers experimental |
| **MCPJam Inspector** | Interactive MCP test/debug + MCP evals + CI | App + CLI/SDK | OSS (verify LICENSE on pin) | Local app/CLI | **Yes** — core product (tools/resources/prompts, OAuth debugger, JSON-RPC, eval suites) |
| **DeepEval** | Pytest-style LLM/agent/RAG/MCP metrics | Python (+ TS beta) | Apache-2.0 | Library; Confident AI optional SaaS | **Yes** — `MCPUseMetric`, multi-turn MCP metrics |
| **Opik** | OSS observability + online/offline eval + prompt opt | Comet platform | Apache-2.0 | Yes | Opik MCP for *driving Opik*; duplicates Langfuse role |
| **Promptfoo** | YAML/CLI prompt eval + red team | Node CLI | MIT (now part of OpenAI; remains OSS) | Local-first | Agent/tool trajectory assertions; not MCP protocol suite |

### 4.2 Feature comparison matrix

| Capability | Langfuse | MLflow | MCPJam | DeepEval | Opik | Promptfoo | LoanOps today |
|---|---|---|---|---|---|---|---|
| Production traces | Yes | Yes | Limited (MCP RPC) | Via platform | Yes | Limited | Partial (Telemetry + AgentTrace JSONL) |
| Datasets / experiments | Yes | Yes | Eval suites | Test cases | Yes | Yes | EvalStore + golden JSONL |
| Human annotation queues | Yes | Labeling sessions | Limited | Via Confident | Yes | Review UI | Portal + L9; Langfuse queues via provider |
| Deterministic MCP protocol tests | No | No | Conformance/CI | Host-use metrics | No | No | **L1 strong** |
| Agent tool-select/args/traj | Custom scorers | Experimental scorers | Expected tool calls | Strong metrics | Agent metrics | Trajectory asserts | **L2–L4 custom** |
| RAG metrics | Custom / judges | Scorers | N/A | Strong | Strong | Assertions | Ragas + retrieval harness |
| Security / red team | Limited | Limited | OAuth conformance | DeepTeam ecosystem | Guardrails | **Strong red team** | L6 skeleton + Safety middleware |
| CI gating | Experiment action | Possible | Native GHA story | `deepeval test run` | pytest | Official Action | `eval-gate.yml` |
| Overlap with ADR-032 SoR | **SoR** | High duplicate | Complementary | Metric layer only | High duplicate | Scenario runner | — |

### 4.3 Classification (what to do)

| Capability need | Classification | Choice |
|---|---|---|
| Traces, scores, datasets, annotation queues | **Reuse directly / Integrate SDK** | Langfuse via existing Telemetry + EvalStore |
| Offline MCP protocol + LoanOps policy tests | **Build ourselves** (done) | Keep `eval/mcp` |
| Interactive MCP debug / OAuth / cross-client | **Integrate** | MCPJam CLI/Inspector beside L1 |
| Deterministic agent scorers (select/args/traj) | **Build ourselves** (done) | Keep L2–L4; do not replace with DeepEval SoR |
| LLM-as-judge RAG metrics | **Integrate** | Keep Ragas; optional later DeepEval metric *ideas* only |
| Red-team YAML packs | **Integrate optionally** | Promptfoo *later* for L6 expansion — not SoR |
| Second observability platform | **Not required** | Skip Opik / MLflow / Phoenix |
| Enterprise review UX (matrix, taxonomy, promote) | **Extend custom** | Portal over Langfuse deep-links |
| Multi-tenant RBAC / audit of reviews | **Build ourselves** | On Agent API + optional Postgres metadata |

---

## 5. Reuse vs Build Analysis

### Reuse (already ours)

- Nine-layer engine, thresholds, fixtures, Makefile targets  
- EvalStore ABC + jsonl/langfuse/mock  
- Portal spreadsheet + taxonomy + promote draft path  
- MCP server policy/scopes/audit  
- Sacred golden runner  

### Reuse (external)

- **Langfuse** — traces, datasets, runs, scores, comments, annotation queues, dataset versioning  
- **Ragas** — faithfulness / answer relevancy (pinned)  
- **MCPJam** — interactive MCP + optional CI probes (complements L1)  
- **judgy** (recommended later) — judge bias correction after human labels exist  

### Build (must be ours)

- LoanOps/domain failure taxonomy → improvement recommendations  
- Golden governance workflow with human approval gates  
- Department rubrics + RBAC  
- Pluggable **target adapters** (MCP server URL, agent endpoint, system e2e)  
- Security hard-fail aggregation (L6) tied to LoanOps policy  
- Eval Portal as department collaboration surface (not a Langfuse clone)

### Do not build / do not adopt

- Parallel trace store  
- MLflow or Opik as second GenAI platform  
- DeepEval as primary engine (duplicates L2–L5 + pulls Confident gravity)  
- Auto-apply production changes from AI recommendations  

---

## 6. Langfuse Integration Strategy

### What we have installed

| Piece | Evidence |
|---|---|
| Optional compose stack | `docker-compose.langfuse.yml` (`langfuse/langfuse:latest`) |
| Settings | `LangfuseConfig`, `TELEMETRY__PROVIDER`, `EVAL_STORE__PROVIDER` |
| Telemetry adapter | `provider_contracts/telemetry/langfuse.py` |
| EvalStore adapter | `provider_contracts/eval_store/langfuse.py` (datasets, items, runs, scores; queues degrade gracefully) |
| Default local path | `jsonl` / `console` — zero Langfuse required |

**Caveat:** Image tag `latest` means “installed version” is environment-specific. Treat capabilities below as **Langfuse platform capabilities we intentionally target via provider**, not a pinned feature matrix of one digest. Pin a version before production.

### Stay in Langfuse

- Span/trace storage and UI drill-down  
- Token/latency/cost when emitted by providers  
- Dataset items + dataset runs + scores  
- Annotation queues / comments for adjudication support  
- Prompt version labels (when PromptStore syncs)  
- Production vs eval `environment` separation (already locked ADR-032)

### Stay in LoanOps portal / APIs

- Domain spreadsheet columns (AI vs Human outcome, failure category, severity, root component)  
- Scenario board for multi-user QA protocols  
- Promote-to-**draft** golden + git-backed registry as source of truth for sacred sets  
- Layer health from `out/eval-*.json`  
- Department-specific rubrics vocabulary  
- Improvement recommendations mapped to EAKG/ApiIndex/SOP owners  

### Boundary rule

Portal **reads/writes through EvalStore + Agent API**. Deep-link to Langfuse for raw spans. Never re-implement Langfuse’s trace search UI.

---

## 7. Target Architecture

### 7.1 Current vs target

```text
CURRENT                              TARGET (incremental)
-------                              --------------------
Chat + EvalPortal (open)             Same UI + AuthN/RBAC + assignments
Agent API /eval/*                    + async eval jobs + targets registry
LoanOps.Eval CLIs                    + EvalOrchestrator service API
EvalStore jsonl|langfuse             Same SoR (prefer langfuse in shared envs)
L6 skeleton                          L6 hard-fail suite in CI
L7/L8 local only                     Optional nightly + sampled online
LoanOps-only targets                 Target adapters: mcp | agent | system
Recommendations informal             Failure→component→ticket suggestions (human approve)
```

### 7.2 Component responsibilities

| Component | Responsibility |
|---|---|
| **Eval Portal (React)** | Scenario runs, matrix review, assignments, deep-links, promote UX |
| **Agent API eval domain** | Feedback, matrix join, promote, job submit/status, target registry |
| **EvalOrchestrator** (`LoanOps.Eval`) | Lifecycle: load dataset → execute target → attach traces → run evaluators → persist scores |
| **Evaluator registry** | Pluggable deterministic / LLM-judge / human / security / retrieval / business-rule scorers |
| **EvalStore provider** | Datasets, runs, scores, review labels (Langfuse|jsonl) |
| **Telemetry provider** | Spans for agent + MCP |
| **MCPJam (optional)** | Dev/CI interactive MCP conformance — reports ingested as L1-adjacent artifacts |
| **Langfuse UI** | Power-user trace/annotation workbench |
| **Git + `data/eval`** | Sacred golden + registry versioning (PR review) |

### 7.3 Data flow

```text
Reviewer picks Scenario + Target + Dataset + Criteria
        → Orchestrator executes Target (MCP|Agent|/system)
        → Traces → Telemetry (Langfuse) + AgentTrace envelope
        → Deterministic evaluators (sync in worker)
        → Optional LLM judges (async, calibrated)
        → Scores → EvalStore
        → Matrix row for humans
        → Human labels → EvalStore + reviews.jsonl
        → AI↔Human agreement metrics (L9)
        → Promote draft candidate (never auto golden)
        → Human PR merges golden → regression run
```

### 7.4 Evaluation execution sequence

1. Create/select `EvaluationRun` (async job).  
2. Resolve `Target` (MCP base URL + token, or Agent `/chat`, or composite system).  
3. For each dataset item: execute, capture `trace_id`, persist envelope.  
4. Run evaluator set; security fails short-circuit aggregate pass.  
5. Emit `ScoreRecord`s; update run summary.  
6. Optionally enqueue annotation queue items for fails / sample.

### 7.5 Human review sequence

1. Assignment (role + department rubric).  
2. Open matrix row → TraceReviewDrawer + Langfuse link.  
3. Label Good/Bad/Needs Review; critique; categories; severity; highlights.  
4. Second reviewer if policy requires; disagreement → adjudication.  
5. Eligible fails → promote **draft** candidate with provenance.  
6. Curator approves into versioned golden via PR / L9 validate.

### 7.6 Integration boundaries

- Domain packages never import Langfuse/MCPJam/DeepEval SDKs — only `packages.common.providers`.  
- MCPJam remains **out-of-process** CLI/Inspector.  
- Qdrant stays retrieval-only.  
- No new primary eval database unless Langfuse+jsonl proven insufficient for RBAC audit (then thin Postgres for *assignments/approvals only*).

### 7.7 Recommended entities (logical)

`Target`, `Scenario`, `Dataset`, `DatasetItem` (status: draft|candidate|approved|deprecated), `EvaluationCriteria`, `EvaluationRun`, `RunItemResult`, `Score`, `Review`, `Adjudication`, `PromotionRecord`, `ImprovementRecommendation` (status: proposed|accepted|rejected).

Physical: prefer EvalStore/Langfuse for Dataset/Run/Score/Review; Postgres only if assignment/RBAC audit cannot live in Langfuse metadata + git.

### 7.8 API contract examples (illustrative)

```http
POST /eval/runs
{ "target_id": "loanops-agent", "dataset": "golden", "layers": ["l2","l5"], "async": true }

GET  /eval/runs/{run_id}

POST /eval/feedback          # exists
GET  /eval/matrix            # exists
POST /eval/promote           # exists — draft only
GET  /eval/traces/{id}       # exists
```

Extend; do not replace existing routes casually.

### 7.9 Security considerations

- AuthN on all `/eval/*` and `/chat` before multi-dept use.  
- RBAC: Engineer / QA / Reviewer / Adjudicator / Curator / Admin.  
- No PII in fixtures, reviews, or Langfuse payloads (tokenize/redact).  
- MCP tokens only server-side; never in browser.  
- Security category failures cannot be outweighed by aggregate quality scores.  
- Audit every promote/adjudication/criteria change.

---

## 8. Evaluation Framework Design

### Lifecycle (supported by Orchestrator)

Define scenarios → select target → select dataset → configure criteria → execute → capture traces → deterministic evaluators → LLM judges → human feedback → AI↔human compare → categorize failures → recommend improvements → approve golden candidates → regression.

### Pluggable evaluators

| Kind | Provider | Notes |
|---|---|---|
| Deterministic | In-repo L1–L5, L7, retrieval | Primary CI path |
| Security | L6 + Safety middleware cases | Hard fail |
| LLM-as-judge | Ragas now; custom rubric judges later | Calibrate with humans before prod weight |
| Human | Portal + Langfuse queues | Source of truth for promotion |
| MCP-specific | L1 + optional MCPJam reports | Keep split suites |
| Retrieval | `eval/retrieval` | Attribute before blaming LLM |
| Business-rule | Custom Python plugins | Domain assertions |
| DeepEval | **Not primary** | Optional metric research only |

### Metrics (recommended)

| Metric | Type | Critical? |
|---|---|---|
| Task success rate | Det + human | Yes |
| Tool selection accuracy | Det (L2) | Yes |
| Tool argument correctness | Det (L3) | Yes |
| API invocation success | Det | Yes |
| Retrieval Recall@K / MRR | Det | Yes |
| Citation accuracy / coverage / groundedness | Det | Sacred |
| Answer relevance / faithfulness | LLM-judge (Ragas) | Gated |
| Hallucination rate | Human + judge | Yes |
| Security violation rate | Det/human | **Critical hard fail** |
| Latency p95 / tokens / cost | Det/telemetry | Ops (L8) |

Aggregate dashboards must **surface security fails separately** — never bury in a blended quality score.

---

## 9. Human Review Workflow

### Spreadsheet columns (portal)

Align with existing matrix + taxonomy:

1. Test Scenario / User Input  
2. Agent Response  
3. AI Critique / scores  
4. AI Outcome  
5. Human Critique  
6. Human Outcome (Good / Bad / Needs Review)  
7. AI vs Human Alignment  
8. Failure Category  
9. Severity  
10. Trace & Evidence (Langfuse URL + span refs)

### Workflow

Assignments → review → optional second review → adjudication on disagreement → promote draft → curator merge. Department rubrics select category subsets and severity defaults. Full history via EvalStore reviews + audit sink.

### OSS annotation reuse

Prefer **Langfuse annotation queues** for raw labeling scale; keep LoanOps matrix for domain columns and golden promotion. Do not introduce Label Studio unless Langfuse queues fail enterprise needs.

---

## 10. Golden Dataset Governance

### Lifecycle

`draft` → `candidate` (from prod/trace or scenario) → `human-reviewed` → `approved` (versioned golden) → executed (run history) → compared (regression) → `deprecated` / archived.

**Production feedback never auto-approves.**

### Item fields

Scenario ID, description, input + conversation context, expected outcome, expected tools **or acceptable alternatives**, argument constraints (not only exact args), required evidence, evaluation criteria, severity, tags/department, approval status, version, provenance (`source_trace_id`).

L2/L4 already score **alternatives / constraints** — preserve that; do not force one tool sequence.

Git-backed `data/golden*.jsonl` + `data/eval/registry.jsonl` remain the compliance-friendly source of truth; Langfuse mirrors for experimentation.

---

## 11. Data Model and API Recommendations

- Keep `DatasetItem.status`, `ScoreRecord`, `ReviewLabel`, `TraceRecord` in EvalStore.  
- Add thin API resources: `Target`, `EvaluationRun` (async), `Assignment`.  
- Failure → improvement map (portal + optional recommendation records):

| Failure | Improvement area |
|---|---|
| Wrong API selected | Capability retrieval / tool discovery |
| Incorrect arguments | Tool schemas / arg validation |
| Missing business rule | SOP / knowledge sources |
| Hallucinated response | Grounding / L5 eval |
| Unnecessary tool calls | Agent orchestration |
| Unauthorized access | MCP authz / policy |
| Incomplete retrieval | EAKG / ApiIndex / RAG |
| Incorrect API output | API contract / backend |

Recommendations require human approval before production change.

---

## 12. Security and Governance

| Control | Today | Target |
|---|---|---|
| MCP GET-only + scopes | Implemented | Keep |
| Capability authz enforce | Off by default | Enable per env + L1 auth suite |
| Portal/API AuthN | Missing | Required for Phase 3+ enterprise |
| Review audit | JSONL partial | Mandatory for promote/adjudicate |
| PII | Safety middleware | Enforce on eval payloads |
| Sacred thresholds | Non-negotiable | Never lower |
| Tenant isolation | Headers only | RBAC + dataset scoping |

---

## 13. Prioritized Implementation Roadmap

### Phase 0 — Assessment (this document)

**Complexity:** Low · **Reuse:** inventory, ADR-032, spec package  

**Acceptance:** Stakeholder sign-off on reuse vs build and Langfuse boundary.

---

### Phase 1 — Evaluation Foundation (shortest E2E)

**Objectives:** One reliable loop: scenario → run → scores → matrix → draft promote.  

| | |
|---|---|
| **Features** | EvalOrchestrator API over existing CLIs; async runs; wire portal to live data only (kill mock as default); pin Langfuse version; expand L6 beyond skeleton; keep L1 in CI |
| **Backend** | Job model on Agent API; deepen EvalStore run listing; L6 cases |
| **Frontend** | Matrix/scenario always live; Langfuse deep-link polish |
| **Integrations** | Langfuse; optional MCPJam doctor in docs/CI sidecar |
| **Dependencies** | None |
| **Deliverables** | Working E2E demo for QA |
| **Acceptance** | Reviewer completes scenario, sees scores+trace, files feedback, promotes draft candidate |
| **Complexity** | Medium |
| **Reuse** | eval_routes, portal, L1–L5, EvalStore |

---

### Phase 2 — Agent Evaluation depth

| | |
|---|---|
| **Features** | Richer L2–L5 live (not only canned); calibrated LLM judges; retrieval attribution in matrix; trajectory efficiency metrics |
| **Backend** | Judge registry; retrieval scores on RunItem |
| **Frontend** | AI critique column populated from judges |
| **Integrations** | Ragas; optional DeepEval metric *research* only |
| **Dependencies** | Phase 1 traces reliable |
| **Acceptance** | Failures tagged with first failing layer + root_component |
| **Complexity** | Medium–High |
| **Reuse** | L2–L5, retrieval harness, taxonomy |

---

### Phase 3 — Human Review Portal

| | |
|---|---|
| **Features** | Assignments, multi-reviewer, adjudication, AI↔human alignment views, highlight unsupported spans |
| **Backend** | Assignment APIs; agreement endpoints wrapping L9 |
| **Frontend** | Workbench UX; remove remaining demo paths |
| **Integrations** | Langfuse annotation queues |
| **Dependencies** | AuthN minimum viable |
| **Acceptance** | Two reviewers + adjudicator path works; disagreement measured |
| **Complexity** | High |
| **Reuse** | taxonomy, TraceReviewDrawer, L9 agreement |

---

### Phase 4 — Governance & Improvement

| | |
|---|---|
| **Features** | Versioned golden UI; regression compare; recommendation tickets; department rubrics; audit history |
| **Backend** | Promotion workflow states; ImprovementRecommendation store |
| **Frontend** | Candidates inbox; before/after experiment compare |
| **Integrations** | Git PR checklist; Langfuse dataset versions |
| **Acceptance** | Prod fail → candidate → approved golden → CI regression proves fix |
| **Complexity** | High |
| **Reuse** | governance/*, promote, registry |

---

### Phase 5 — Enterprise readiness

| | |
|---|---|
| **Features** | RBAC/tenants; full L6 security pack; CI includes L7 nightly + sacred golden; prod sampling L8; reporting; multi-agent/MCP targets |
| **Backend** | Target registry; authz middleware; Postgres only if required for RBAC audit |
| **Frontend** | Role-aware navigation |
| **Integrations** | MCPJam CI; IdP |
| **Acceptance** | External MCP target evaluable; security fails block release; audit exportable |
| **Complexity** | High |
| **Reuse** | Provider factories, scopes, L8 |

**Priority rule:** Finish Phase 1 E2E before Phase 5 sprawl.

---

## 14. Risks and Trade-offs

| Risk | Trade-off |
|---|---|
| Dual SoR if DeepEval/Opik/MLflow added | Short-term metrics vs long-term ops cost — **reject dual SoR** |
| Langfuse `latest` drift | Convenience vs reproducibility — **pin versions** |
| Portal mock data masks holes | Fast demo vs false confidence — **live-only in shared envs** |
| Async jobs without auth | Power vs abuse — ship jobs with AuthN |
| Exact tool-sequence goldens | Brittle CI vs real multi-path agents — keep constraint scoring |
| Enabling capability_authz | Security vs demo friction — stage by environment |
| Promptfoo under OpenAI ownership | Strong red team vs supply-chain optics — isolate optional |

---

## 15. Final Recommendations

1. **Continue Langfuse** as main observability + eval dataset/score platform (ADR-032).  
2. **Do not integrate MLflow** for GenAI eval — duplicates Langfuse.  
3. **MCPJam is suitable** as complementary MCP inspector/CI probe — not replacement for L1.  
4. **Do not make DeepEval the primary engine** — keep in-repo scorers; Ragas stays for LLM metrics.  
5. **Build ourselves:** portal collaboration, taxonomy→improvement loop, golden governance, target adapters, L6, RBAC.  
6. **Eval execution:** async for suite runs; sync OK for single-scenario portal trials.  
7. **Human feedback:** both — operational labels in EvalStore/Langfuse; compliance mirror in audit/git as needed.  
8. **Versioning:** git for sacred golden/registry; Langfuse dataset versions for experiments.  
9. **Shared model:** one Orchestrator; three target types (MCP / Agent / System).  
10. **Beyond LoanOps:** Target registry + ToolsClient/MCP URL config; scorers consume normalized traces.  
11. **Prod → candidate:** sample/flag → human review → draft promote → curator approve.  
12. **Results → improvements:** map failure category → root_component → suggested action; human ticket approval only.

### Modules likely to change (when implementation starts)

- `projects/LoanOps.Eval/packages/eval/` (orchestrator, L6, run jobs)  
- `projects/LoanOps.AgentApi/apps/agent_api/eval_routes.py`  
- `apps/web_ui/src/eval/*`, `EvalPortal.tsx`  
- `provider_contracts/eval_store/*` (if assignment/run APIs need extension)  
- `packages/common/settings.py` (only with approval for new env vars)  
- `.github/workflows/eval-gate.yml`  
- `data/eval/**` fixtures/rubrics  
- Spec sync: `.ai/specs/eval-improvement-platform/`

### Clarifying questions before implementation

1. Is Langfuse approved for enterprise prod traces (data residency / self-host mandate)?  
2. Which IdP for portal AuthN (Auth0/Entra/other)?  
3. Must sacred golden stay git-only, or may Langfuse be co-SoR for approved items?  
4. Priority order: L6 security pack vs multi-reviewer vs multi-target MCP?  
5. Are non-LoanOps MCP servers in scope for Phase 1 or Phase 5?  
6. Is MCPJam allowed on developer workstations / CI runners (network policy)?  
7. Who is Curator of golden approvals (role/team)?  
8. Cost/token accounting required for Phase 1 exit or later?

---

## Appendix A — Critical architecture answers (explicit)

| # | Question | Recommendation |
|---|---|---|
| 1 | Langfuse as main observability? | **Yes.** Already ADR-032 + adapters. |
| 2 | Integrate MLflow? | **No** — duplicates tracing/datasets/evals. |
| 3 | MCPJam suitable? | **Yes, as integration** for interactive/CI MCP — beside L1. |
| 4 | DeepEval primary engine? | **No.** Optional ideas only; engine = LoanOps.Eval. |
| 5 | Build ourselves? | Portal workflows, governance, taxonomy loop, adapters, L6, RBAC. |
| 6 | Sync vs async execution? | **Async suites**; sync single interactive runs. |
| 7 | Where store human feedback? | **EvalStore/Langfuse primary**; audit/git for promote trail. |
| 8 | Dataset/result versioning? | Git sacred sets + Langfuse dataset versions + run IDs. |
| 9 | Shared model across MCP/agent/system? | One Orchestrator; three targets; shared Score/Review. |
| 10 | Other agents/MCP servers? | Target registry + normalized trace schema. |
| 11 | Prod traces → candidates? | Sample → human review → draft promote → approve. |
| 12 | Actionable recommendations? | Category→component→action; human-approved tickets only. |

---

## Appendix B — Implementation backlog (by phase)

**P0:** Stakeholder sign-off on this assessment; pin Langfuse image; refresh stale claims in `docs/eval/analysis.md`.  

**P1:** Orchestrator API; live portal default; L6 expansion; MCPJam sidecar doc; run history UI.  

**P2:** Live agent layer scoring; judge calibration; retrieval columns.  

**P3:** Assignments; multi-reviewer; adjudication; AuthN MVP.  

**P4:** Golden versioning UX; regression compare; recommendations.  

**P5:** RBAC/tenants; multi-target; CI expansion; L8 online; reporting.

---

## Appendix C — Assumptions & unknowns

| Item | Class |
|---|---|
| Langfuse remains org-approved SoR | Assumption |
| Exact Langfuse digest feature parity | Unknown until pin |
| MCPJam license/org policy acceptance | Unknown |
| Postgres required for RBAC | Assumption: defer until proven need |
| Agent cost_usd still often 0.0 | Verified weakness — fix under telemetry work |
| Spec package still accurate for portal existence | Partially stale — update on next executeSpec |

---

**Bottom line:** You already own ~70% of an enterprise eval platform’s *engine*. Shortest path is productize the loop you have (portal + EvalStore + layers + Langfuse), close L6/auth/governance gaps, and treat MCPJam as a power tool — not a rewrite.
