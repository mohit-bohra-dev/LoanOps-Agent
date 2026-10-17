# Evaluation System — Phase 1 Analysis

**Status:** Discovery only (no code changes beyond this document).  
**Date:** 2026-10-17  
**Scope (primary):** MCP Streamable HTTP server (`LoanOps.McpServer`), its tools, auth/policy, telemetry, and clients that speak MCP (Cursor, Gemini, `McpToolsClient` when `TOOLS_CLIENT__PROVIDER=mcp`).  
**Out of primary scope:** Agent API `POST /chat` (SSE) — documented for context only; not a Phase 2 build target unless re-approved.

Claims cite repo paths. Items that could not be determined from the repo are marked **UNVERIFIED** in §9.

### Eval surfaces (priority order)

| Priority | Surface | Why |
|---|---|---|
| P0 | `python -m packages.mcp_server` → `/mcp` tools | Protocol + tool correctness; shared by external agents |
| P0 | Direct `execute_tool` / MCP client `call_tool` harness | Deterministic L1; no LLM |
| P1 | In-process `run_agent_turn` **only if** evaluating LLM tool selection against MCP-backed tools | Bypasses `/chat` HTTP; optional — confirm at Checkpoint 1 |
| P2 (defer) | `POST /chat` | Session, PII pipe, SSE framing — not eval focus |

---

## 1. Stack and structure

| Concern | Finding | Evidence |
|---|---|---|
| Language | Python 3.11–3.12 (`requires-python = ">=3.11,<3.13"`) | `pyproject.toml` L6 |
| Backend API | FastAPI Agent API on `:8000` | `projects/LoanOps.AgentApi/apps/agent_api/main.py`; `CONTEXT.md` §9 |
| MCP server | FastMCP Streamable HTTP on `:8001` (default path `/mcp`) | `projects/LoanOps.McpServer/packages/mcp_server/server.py` L370–389; `__main__.py` |
| Orchestration | `AgentRuntimeProvider` — default `langgraph`, alt `native` / `mock` | `packages/common/settings.py` `AgentRuntimeConfig`; `factory.py` `get_agent_runtime_provider()` |
| UI | React 19 + TypeScript + Vite 8 + Tailwind 4 | `apps/web_ui/package.json` |
| Package manager | **uv** workspace (`loanops-*` projects) | root `pyproject.toml`; `Makefile` `install: uv sync` |
| Lint / types | ruff, mypy `--strict` | `Makefile` `lint`; `.pre-commit-config.yaml` |
| Test runner | pytest + pytest-asyncio (`asyncio_mode = auto`) | `pyproject.toml` `[tool.pytest.ini_options]` |
| Eval deps | `ragas==0.4.3` in Eval project; OTel SDK at root | `projects/LoanOps.Eval/pyproject.toml`; root `pyproject.toml` L25 |
| Provider SDKs | Via `provider-contracts` extras (ollama, openai, langfuse, langgraph, …) | `projects/LoanOps.Common/pyproject.toml` |

### How to run locally

| Target | Command | Evidence |
|---|---|---|
| Install | `make install` → `uv sync` | `Makefile` |
| Unit tests | `make test` → `uv run pytest` | `Makefile` |
| Agent API | `uv run uvicorn apps.agent_api.main:app --host 127.0.0.1 --port 8000` (also `make demo`) | `Makefile` `demo`; `AGENTS.md` |
| MCP server | `python -m packages.mcp_server` with `MCP__AUTH_TOKEN` set | `docs/MCP_IMPLEMENTATION.md`; `__main__.py` |
| Agent eval | `make eval` → `python -m packages.eval.run --golden data/golden.jsonl` | `Makefile`; `packages/eval/run.py` |
| MCP fixture eval | `python -m packages.mcp_server.eval_run` | `packages/mcp_server/eval_run.py` |
| Data validate | `python -m packages.eval.validate_data` | `packages/eval/validate_data.py` |

### CI

| Item | Status | Evidence |
|---|---|---|
| GitHub Actions workflows | **None on disk** | `CONTEXT.md` §17; `.github/` has `copilot-instructions.md` only |
| Pre-commit | ruff, mypy, project-refs gate | `.pre-commit-config.yaml` |
| Optional GitLab include | EAKG sync/nightly/audit only — **not** agent/MCP eval | `ci/eakg.gitlab-ci.yml` |

---

## 2. MCP servers

### Servers found

| Server | Transport | Package | Entry |
|---|---|---|---|
| **LoanOps MCP** (primary protocol server) | Streamable HTTP (`stateless_http=True`, `json_response=True`) | `loanops-mcp-server` → `packages/mcp_server` | `python -m packages.mcp_server` → `create_app()` |
| Agent API “MCP-tagged” HTTP routes | Custom JSON (`GET/POST /mcp/tools*`) — **not** MCP protocol | `apps/agent_api/mcp_routes.py` | Documented in `ARCHITECTURE.md` §15; `docs/MCP_IMPLEMENTATION.md` |

Only one protocol MCP server implementation exists in this repo.

### MCP spec revision

| Fact | Value | Evidence |
|---|---|---|
| SDK | `mcp>=1.27.1` (installed `1.27.1`) | `projects/LoanOps.McpServer/pyproject.toml` L12 |
| SDK `LATEST_PROTOCOL_VERSION` | `2025-11-25` | Installed `mcp.types` |
| SDK `DEFAULT_NEGOTIATED_VERSION` | `2025-03-26` | Installed `mcp.types` |
| Repo pin of negotiated version | **UNVERIFIED** — no explicit protocol-version string in LoanOps MCP code; negotiation delegated to FastMCP/SDK | `server.py` uses `FastMCP` only |

### Auth flow

| Step | Behavior | Evidence |
|---|---|---|
| Transport auth | Bearer compared to `MCP__AUTH_TOKEN` via `StaticTokenVerifier` | `server.py` L160–169, L385–389 |
| Empty token | Rejects every token | `StaticTokenVerifier` docstring; `MCP_SECURITY.md` |
| Role scope | `MCP__ROLE` → `tools_for_role()` allow-list | `execute_tool` L252–253; `scopes.py` |
| Principal headers | Optional `x-loanops-user` / `x-loanops-tenant` (or `MCP__PRINCIPAL_*`) | `CaptureHeadersMiddleware`; `MCP_SECURITY.md` |
| OAuth / OBO | **Not implemented** (shared service bearer to SSE via `SSE__API_KEY`) | `docs/MCP_SECURITY.md` “Not yet” |

### Tools registered on Streamable HTTP MCP

All annotated `readOnlyHint=True` (`_READ_ONLY` in `server.py` L43). Schemas are FastMCP function signatures (JSON Schema derived by the SDK). Outputs are **plain strings** (tool returns `str` from `_run` / `execute_tool`).

| Tool | Inputs (from signature) | Output | Evidence |
|---|---|---|---|
| `search_sse_apis` | `query: str`, `limit: int=15`, `application: str\|None`, `permission: str\|None` | `str` | `server.py` L416–443 |
| `list_sse_apis` | `source_label: str\|None`, `limit: int=50`, `refresh: bool=False` | `str` | L445–458 |
| `call_sse_api` | `capability_id`, `operation_id`, `method`, `path`, `application`, `path_params`, `query`, `body` (all optional except effective ID/path) | `str` | L460–492 |
| `search_docs` | `query: str`, `top_k: int=5` | `str` | L494–502 |
| `search_capabilities` | `query: str`, `limit: int=15` | `str` | L504–515 |
| `explain_capability` | `capability_id: str` | `str` | L517–526 |
| `find_providers` | `query: str` | `str` | L528–538 |
| `impact_of_change` | `target: str` | `str` | L540–549 |
| `describe_application` | `application_id: str` | `str` | L551–564 |
| `search_code` | `application_id: str`, `query: str`, `limit: int=20` | `str` | L566–585 |

**Note:** `docs/MCP_IMPLEMENTATION.md` “Tools exposed (v1)” lists only four tools — **stale** relative to `server.py` (ten tools). Prefer `server.py` as source of truth.

### Agent-facing tool list (chat path)

`run_agent_turn` hardcodes `_SSE_ANSWER_TOOLS` with **four** tools only: `search_sse_apis`, `list_sse_apis`, `call_sse_api`, `search_docs` (`packages/agent_core/_agent.py` L40–103). EAKG MCP tools are **not** offered to the LLM on the agent path, even when `TOOLS_CLIENT__PROVIDER=mcp` (filter still applies `_SSE_ANSWER_TOOLS` via `_tools_for_client`).

### Extra tools in ModularToolsClient (not MCP-registered)

Available in-process for roles with matching scopes (`scopes.py` + `modular_tools.py` `_LOCAL_TOOLS`):

| Tool | Scope | Notes |
|---|---|---|
| `get_customer_servicing_summary` | `db.read` | SQL read |
| `run_read_only_sql` | `db.read` | SQL read |
| `index_docs` | `docs.index` | **Mutates** vector index |
| `wiki_*` (5 names) | wiki scopes | Stubs — return “not yet ported” | `packages/wiki/tools.py` |

---

## 3. Enterprise APIs behind the tools

| Tool | Downstream | Side effects? |
|---|---|---|
| `search_sse_apis` / `list_sse_apis` | OpenAPI catalog / ApiIndex vector+keyword (`packages/sse`, `packages/api_index`) | Read-only catalog |
| `call_sse_api` | Live HTTP GET to allowed SSE hosts via `invoke_sse_api` (M2M `SSE__API_KEY`) | **Policy: GET-only, body rejected** on MCP and Modular client. No payments/holds by design. Upstream GET may still have side effects on remote APIs — **UNVERIFIED per enterprise OpenAPI** |
| `search_docs` | `DocsService.search` → vector store | Read-only |
| EAKG tools (`search_capabilities`, …) | Graph store / EAKG shards (`dispatch_eakg_tool`) | Read-only graph queries |
| `index_docs` | `DocsService.index_directory` | **Write** — indexes SOP corpus into vector store |
| `wiki_document_feature` | Placeholder | Declared write scope; implementation is stub |
| DB tools | `SqlServerClient` read helpers | Intended read-only |

**Product rule:** “No mutating tool calls in v1” (`AGENTS.md`). MCP enforces GET-only for `call_sse_api` (`server.py` L287–303; `policy.py`).

---

## 4. Agent / client flow (MCP-centric)

**Primary path under eval focus** — external or LoanOps MCP client:

```
MCP client (Cursor / Gemini / McpToolsClient)
  → Streamable HTTP + Bearer MCP__AUTH_TOKEN
  → FastMCP tool handler → execute_tool
       → auth + role scope + (call_sse_api: GET-only, capability bind/authz)
       → ModularToolsClient.call → SSE / docs / EAKG
       → audit mcp.tool.call + telemetry span/metrics
  → string tool result to client
```

**Secondary (optional for L2–L5)** — LLM loop without `/chat`:

```
run_agent_turn (packages/agent_core)  # used today by packages.eval.run and by /chat
  → intent router → system prompt → AgentRuntimeProvider
  → tools via modular or mcp client
```

`/chat` adds PII sanitize, session memory, outbound safety, SSE wrap — **out of primary eval scope**.

| Concern | Where | Evidence |
|---|---|---|
| MCP tool discovery | FastMCP `@mcp.tool` registrations (10 tools) | `server.py` |
| MCP auth / policy / termination | `execute_tool` | `server.py` L217–367 |
| Agent system prompt (if L2+ uses `run_agent_turn`) | `agent.system` → `docs/agent/system.md` | `_prompt_loader.py`; file is stub — §9 |
| Agent tool list vs MCP | Agent hardcodes 4 tools; MCP exposes 10 | `_agent.py` vs `server.py` |
| Tools hop | `TOOLS_CLIENT__PROVIDER=modular\|mcp` | `settings.py`; ADR-013 |
| Models / runtime | Chat provider + `AGENT_RUNTIME__PROVIDER` (default langgraph) | `factory.py`; `settings.py` |

---

## 5. Observability

| Signal | Present? | Evidence |
|---|---|---|
| Audit JSONL | Yes — `AUDIT__SINK=jsonl` default | `settings.py`; Agent API + MCP `AuditEvent` |
| MCP spans | `mcp.tool.call` via `TelemetryProvider.span` | `server.py` `_tool_span` |
| MCP metrics | `mcp.tool.latency_ms`, `mcp.tool.outcome` | `server.py` `_record_mcp_metrics` |
| Eval metrics push | `eval.*` and `eval.mcp.*` via telemetry | `packages/eval/run.py` L268–278; `eval_run.py` |
| Telemetry backends | `console` (default), `langfuse` (self-hosted), `appinsights` **raises NotImplemented** | `factory.py` L331–354 |
| Langfuse | Self-hosted only; keys/host in `TELEMETRY__LANGFUSE__*` | `CONTEXT.md`; `LangfuseTelemetryProvider` |
| OTel SDK | Dependency present (`opentelemetry-sdk==1.42.1`) | root `pyproject.toml` |
| `/chat` → TelemetryProvider | **No** (out of primary scope anyway) | `ARCHITECTURE.md` §14 |
| Token / cost on eval | `cost_usd` hard-coded `0.0` | `packages/eval/run.py` L85; `ARCHITECTURE.md` §14 |
| Trace ID on golden / reports | **Not** stored on `GoldenItem` / `EvalReport` | `packages/eval/models.py` |
| New Relic | **No configuration or code references** in this repo | Grep over `*.py` / settings / `.env.example` — none |

---

## 6. Existing tests and evals

### What is covered

| Layer | Coverage | Evidence |
|---|---|---|
| Unit / contract | Broad pytest suite across packages; provider contract tests | `pyproject.toml` `testpaths`; `packages/common/providers/contract_tests/` |
| MCP unit | Auth, policy, streamable HTTP bearer, capability bind/authz | `packages/mcp_server/tests/` |
| MCP fixture eval | 7 in-code cases → auth/policy/success rates to telemetry | `eval_fixtures.py`; `eval_run.py` |
| Agent golden eval | Citation coverage/groundedness, refusal correctness, optional Ragas faithfulness/relevance, latency p95 | `packages/eval/{run,metrics,thresholds}.py` |
| Golden data validation | Schema checks for loans/SOPs/golden | `validate_data.py` |
| Safety unit | `sanitize_inbound` / `evaluate_outbound` | `packages/safety/tests/` |

### What is not covered (or only declared)

| Gap | Evidence |
|---|---|
| `must_call_tools` / `forbidden_phrases` in golden **not scored** by metrics | Present on `GoldenExpected`; used in `validate_data.py` only — **absent** from `metrics.py` / `run.py` threshold dict |
| Tool-selection / argument / trajectory evals | `ARCHITECTURE.md` §13: “There is no separate tool-selection eval” |
| Protocol conformance suite against MCP revision | Only FastMCP integration + unit tests |
| Human review / promotion / golden versioning workflow | No artifacts under `evals/` or review UI |
| Production sampling / drift alerts | Telemetry hooks only; no alert thresholds in code |
| CI gate for `make eval` | No workflow YAML (`CONTEXT.md` §17) |
| Agent path EAKG tools | Not in `_SSE_ANSWER_TOOLS` |

### Golden datasets on disk

| File | Approx size | Role |
|---|---|---|
| `data/golden.jsonl` | 5 smoke items | Default `make eval` |
| `data/golden.full.jsonl` | 50 lines | Full set (CONTEXT.md) |
| `data/golden_global.jsonl` | 22 lines | GraphRAG / global slice experiments (`logs.md`) |
| `data/golden_test.jsonl` | tiny | Test fixture |

Schema today: `id`, `rep_prompt`, `loan_id`, `expected.{refusal,escalation,must_cite,must_call_tools,forbidden_phrases}` — **no** trajectory constraints, `eval_methods`, source_trace_id, reviewer, or version fields (`models.py`).

**Target golden fields (portal taxonomy — see Appendix C):** each case declares `eval_methods[]` (which checkers run), plus optional `required_tools` / `allowed_tool_sets`, `forbidden_tools`, `arg_constraints`, `trajectory` (required steps, deps, forbidden actions — not exact sequence), `outcome` / business-state checks, `safety_constraints`, `source_trace_id`, `reviewer`, `version`.

---

## 7. Data and configs

| Asset | Path / mechanism |
|---|---|
| Synthetic loans | `data/loans.json` |
| SOPs | `data/sops/` |
| SSE fixtures | `data/fixtures/loan_api/`; `SSE__USE_FIXTURE` / `SSE__CATALOG_SOURCE` |
| EAKG shards / registry | `data/eakg/`; `EAKG__ENVIRONMENT` = `local\|dev\|stage\|prod` |
| Secrets | `SECRETS__PROVIDER=env` default; `.env` / `.env.example`; Key Vault not implemented |
| Environments | Env-var swap (local Ollama+fixture vs Azure/Bedrock+live SSE) — no separate deploy manifests for eval envs in-repo |
| Audit dir | `AUDIT__JSONL_DIR` default `./audit` |
| Mock providers | `packages/common/providers/testing.py`; MCP `_FakeClient` in `eval_run.py` |

---

## 8. Gap analysis vs nine layers

| # | Layer | Rating | Evidence |
|---|---|---|---|
| 1 | MCP server | **Partial** | Fixture auth/policy mixed with success; **no** split of JSON-RPC protocol errors vs `CallToolResult.isError`; no separate protocol / business / authz / perf suites |
| 2 | Discoverability / tool selection | **Missing** | `must_call_tools` never scored; no multi-valid alternative sets |
| 3 | Arguments | **Missing** | No arg / scope / side-effect validators on golden |
| 4 | Trajectory | **Partial** | Tool call lists + MCP spans; no required-step / dep / forbidden-action matchers (exact-sequence-only would be wrong) |
| 5 | Outcomes | **Partial** | Citations + Ragas; **no** business-state verification (v1 mostly read-only — still need answer grounding vs tool strings) |
| 6 | Security | **Partial** | GET-only + scopes; no injection suite; **no** non-compensatory hard-fail gate |
| 7 | Robustness | **Missing** | No pass-rate thresholds for nondeterministic runs |
| 8 | Operations (prod) | **Missing** | Offline eval scores and prod metrics not separated; no alert thresholds |
| 9 | Evaluation governance | **Missing** | No dataset approval, rubric versions, disagreement / adjudication |

---

## 9. Risks and unknowns

Explicitly **not determined** from the repo (do not guess):

1. **Negotiated MCP protocol version at runtime** between LoanOps FastMCP server and each client (Cursor, Gemini, McpToolsClient) — only SDK constants observed.
2. **Whether `docs/agent/system.md` stub is intentional** vs sync failure from `docs/01-servicing-agent-prompts.md` §B — runtime loads the stub file only.
3. **Per-operation side effects of enterprise GET APIs** behind `call_sse_api` (OpenAPI may mark some GETs as unsafe) — not audited here operation-by-operation.
4. **Production / staging deploy topology** for Agent API + MCP (IaC under `infra/terraform/` exists but was not fully mapped for eval envs).
5. **Whether live `make eval` is currently runnable** without SSO/Azure credentials — `TASKS.md` / `logs.md` note live eval SSO-gated; not re-run in this phase.
6. **New Relic** — no in-repo config; any org-level NR for this app is outside the repository.
7. **Human review / Compliance labeling process** currently used (if any) — not in repo.
8. **Exact LangGraph graph node span attribute schema** emitted to Langfuse for agent turns — agent path does not call `TelemetryProvider` today.
9. **Whether wiki tools will gain write behavior** when ported — currently stubs.
10. **ARCHITECTURE.md §15** still describes “no MCP server class” — **stale** vs `packages/mcp_server`; treat §15 as historical unless updated.

---

## Appendix A — Thresholds in force (do not lower)

From `packages/eval/thresholds.py`:

| Metric | Threshold |
|---|---|
| faithfulness | ≥ 0.85 |
| answer_relevance | ≥ 0.85 |
| citation_coverage | ≥ 1.0 |
| citation_groundedness | ≥ 1.0 |
| refusal_correctness | ≥ 0.95 |
| latency_p95_ms | ≤ 4000 (optional via `--enforce-latency`) |

---

## Appendix B — Reuse candidates already in repo

| Library / module | Already used for | Candidate layers |
|---|---|---|
| `pytest` / `pytest-asyncio` | Unit + contract | 1 deterministic MCP |
| `ragas` | Faithfulness / answer relevancy | 5 (extend carefully; pin model+prompt) |
| `packages.eval.*` | Golden runner + thresholds | 2–5, 9 (extend models) |
| `packages.mcp_server.eval_*` | MCP fixture scores | 1 |
| `provider_contracts.telemetry` (+ Langfuse) | Spans/metrics | 4, 8 |
| `opentelemetry-sdk` | Declared dep | 4 (if agent path instrumented — **needs approval**) |
| `packages.safety` | PII + outbound | 6 |
| `packages.common.scopes` / MCP policy | Authz / GET-only | 1, 6 |
| FastMCP / `mcp` SDK | Server + client | 1 protocol tests |

**Not in repo (would need Checkpoint 1 approval before adding):** DeepEval, Promptfoo, Inspect AI, LangSmith datasets, Braintrust, custom NR exporter.

---

## Appendix C — Official portal taxonomy (approved refinements)

Nine layers kept. Adjustments locked for Phase 2+:

| Layer | Name | Design rules |
|---|---|---|
| 1 | MCP server | **Split suites:** (a) protocol conformance / JSON-RPC errors, (b) tool business logic + schema, (c) authorization, (d) performance/concurrency. Never conflate (a) with tool `isError`. |
| 2 | Discoverability | Score against **allowed tool sets / alternatives**, not a single exact tool when multiple are valid. |
| 3 | Arguments | Required fields/types/values **plus** authorization-scope fitness and **side-effect class** of the call (read vs write; v1 write must fail policy). |
| 4 | Trajectory | Assert **valid paths**: required steps, dependencies, forbidden actions, acceptable outcomes — **not** one exact sequence. |
| 5 | Outcomes | Groundedness + completeness; when a task can change data, verify **business end state** (v1: mostly N/A for writes; still verify factual answer vs tool results). **In PoC — not deferred.** |
| 6 | Security | Failures are **hard / non-compensatory** — cannot be offset by high average on other layers. |
| 7 | Robustness | Nondeterministic cases: N repeats + defined **pass-rate** threshold. |
| 8 | Operations | **Separate** production monitoring metrics from offline eval scores (connected dashboards, different stores/gates). |
| 9 | Evaluation governance | Dataset approval before promotion, **rubric versioning**, reviewer disagreement / adjudication. |

### Technical corrections (must implement)

1. **Protocol error ≠ tool error.** JSON-RPC / transport / malformed-request failures are L1a. Tool ran but failed operationally → `CallToolResult` with `isError: true` is L1b. Test both.
2. **No exact-trajectory-only cases** unless the business truly has one legal path; default to constraint-based trajectories.
3. **PoC includes a small L5 outcome set** so an agent cannot pass L1–L4 with a wrong answer.

### Golden case: executable `eval_methods`

Each JSONL case lists which checkers apply, e.g.:

| Example case | `eval_methods` |
|---|---|
| Invalid MCP tool arguments | `deterministic_assert` |
| Correct API for a payment query | `expected_tools_any_of` |
| Correct payment date in final answer | `grounding`, `outcome` |
| Prompt injection in API response | `security_hard_fail` |
| Ambiguous business request | `human_rubric` or `llm_judge_calibrated` |

### PoC build order (MCP-first; no `/chat`)

| Step | Deliverable |
|---|---|
| A | L1a protocol + L1b tool contracts (deterministic, fixtures/FakeClient) |
| B | L2 discoverability + L3 args (alternatives + scope/side-effect) |
| C | L4 constraint-based trajectory + MCP trace capture |
| D | Small L5 end-to-end outcome checks (grounding vs tool strings) |
| E | High-priority L6 injection / policy hard-fails (non-compensatory gate) |
| Later | L7 pass-rates, L8 prod-vs-offline split, L9 governance + portal |

**Connected but separate capabilities:** evaluation traces (Langfuse/audit), dataset governance (L9), production monitoring (L8).

**Reuse:** `pytest`, `mcp_server.eval_*` (refactor into L1a/L1b), extend golden JSONL, `TelemetryProvider`/Langfuse for traces, `ragas` only for calibrated L5/L9 judge cases with pinned model + rubric file. No DeepEval/Promptfoo unless gap remains after that.
