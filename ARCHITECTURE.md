# LoanOps Architecture

> **Single architecture doc** for this repo. Living — update after ADRs / structural change.  
> Related: [`decisions.md`](decisions.md), [`docs/DECIDE_AND_CLEANUP.md`](docs/DECIDE_AND_CLEANUP.md), [`docs/PHASE_STATUS.md`](docs/PHASE_STATUS.md), [`docs/01-servicing-agent-prompts.md`](docs/01-servicing-agent-prompts.md) §A, **[`docs/FLOWS.md`](docs/FLOWS.md)** (every application flow).  
> Secrets omitted. Env = names/roles only.

**North star (D1):** EAKG fills MCP tools; agent `/chat` + Cursor/Gemini consume the same `:8001/mcp` (`TOOLS_CLIENT__PROVIDER=mcp`).

---

## 1. Executive Summary

LoanOps is an **internal AI platform for any enterprise user** (ADR-021): discover APIs/capabilities, search docs, call tools via MCP, draft grounded answers. A React chat UI talks to a FastAPI Agent API. The API runs one agent turn per message: keyword intent gate, then a Microsoft-style tool loop over a pluggable LLM (`provider_contracts` chat provider, default Bedrock). The model may call a fixed tool list.

**Product path:** `TOOLS_CLIENT__PROVIDER=mcp` → Streamable HTTP MCP on `:8001` (ADR-011/013) → `ModularToolsClient` / SSE / EAKG inside the MCP process.  
**Rollback / single-process demo:** `TOOLS_CLIENT__PROVIDER=modular` (in-process tools, no MCP hop).

Live loan facts come from SSE REST APIs (OpenAPI/swagger + `httpx`), with service Bearer `SSE__API_KEY` (D7: Subservicing Auth0 M2M). Policy text from docs vector search when configured. UI sidebar can call one SSE op via custom `/mcp/tools` JSON wrapper (not the MCP protocol).

`apps/tools_api` is gone. Legacy `RestApiLoanProvider` / `DATA__LOAN_API__*` remain for probes/tests only.

**Two graphs:** (1) Graphify (`graphify-out/`) = this repo for agents/humans, not request-time. (2) EAKG (`data/eakg/`, `packages/eakg/`) = enterprise capability KG that feeds MCP search / discovery.

---

## 2. Repository Structure

```text
LoanOps-Agent/
  pyproject.toml          uv workspace solution (members = projects/*)
  apps/
    web_ui/               React + Vite + Tailwind care-rep UI (npm)
  projects/               one LoanOps.X = one loanops-* dist (csproj-style)
    LoanOps.AgentApi/apps/agent_api/   FastAPI :8000 — /chat, /health, /mcp/*
    LoanOps.AgentCore/packages/agent_core/
    LoanOps.Tools/packages/tools/      Modular + MCP tools client factories
    LoanOps.McpServer/packages/mcp_server/
    LoanOps.Sse/packages/sse/
    LoanOps.Docs/packages/docs/
    LoanOps.Rag/packages/rag/
    LoanOps.Db/packages/db/
    LoanOps.Wiki/packages/wiki/
    LoanOps.Safety/packages/safety/
    LoanOps.Eval/packages/eval/
    LoanOps.Common/packages/common/    Settings, schemas, provider factories
    LoanOps.CapabilityKg/packages/capability_kg/
    LoanOps.Eakg/packages/eakg/
  provider_contracts/     Sibling repo (editable path dep)
  data/                   SOPs, golden, EAKG fixtures (repo root)
  graphify-out/           Offline code/doc graph (not runtime)
  infra/terraform/        AWS IaC
  docs/                   Prompts, phase status
```

| Directory | Role |
|---|---|
| `projects/LoanOps.AgentApi` | HTTP front door for chat, health, tool HTTP API |
| `apps/web_ui` | Chat transcript, session memory viewer, borrower sidebar |
| `projects/LoanOps.AgentCore` | One turn: classify, prompt, LLM, tools, JSON contract |
| `projects/LoanOps.Tools` | Tools composition; injects EAKG into SSE search |
| `projects/LoanOps.Sse` | Real HTTP calls to configured SSE hosts |
| `projects/LoanOps.Common` | Env loading and provider selection |
| `projects/LoanOps.Safety` | PII and content safety around the chat turn |
| `projects/LoanOps.Eval` | Offline golden runner; not in the request path |
| `graphify-out` | Static graph of this repo for agents and humans |

---

## 3. Current Runtime Architecture

```text
┌──────────────────────────────────────────────────────────┐
│ Chat UI (Vite :5173)                                     │
│  ChatPane  ──POST /api/chat (SSE)──►                     │
│  BorrowerContextPane ──POST /api/mcp/tools/call──►       │
└────────────┬───────────────────────────┬─────────────────┘
             │ Vite proxy strips /api    │
             ▼                           ▼
┌────────────────────────────┐  ┌─────────────────────────┐
│ Agent API FastAPI :8000    │  │ mcp_routes.py           │
│ POST /chat                 │  │ GET  /mcp/tools         │
│  sanitize_inbound (PII)    │  │ POST /mcp/tools/call    │
│  session history           │  │ POST /mcp/keys          │
│  run_agent_turn            │  └────────────┬────────────┘
│  evaluate_outbound         │               │
│  audit JSONL               │               │
└────────────┬───────────────┘               │
             │ in-process                    │ in-process
             ▼                               ▼
┌──────────────────────────────────────────────────────────┐
│ ModularToolsClient  (TOOLS_CLIENT__PROVIDER=modular)     │
│  scope filter: AGENT_ROLE (default system)               │
│    sse.read + docs.search                                │
└───────┬──────────────────────┬───────────────────────────┘
        │                      │
        ▼                      ▼
┌───────────────────┐   ┌──────────────────┐
│ packages/sse      │   │ packages/docs    │
│ search/list/call  │   │ search_docs      │
│ httpx + Bearer    │   │ embed + Qdrant   │
└─────────┬─────────┘   └────────┬─────────┘
          │                      │
          ▼                      ▼
   SSE REST hosts          Vector store
   (OpenAPI catalog)       namespace "docs"

Not on the default agent tool list (still in ModularToolsClient):
  SQL Server (packages/db) — role dev + db.read
  wiki_* stubs (packages/wiki) — role dev
  index_docs — docs.index scope

Not on the agent path:
  RestApiLoanProvider (DATA__LOAN_API__*)
  rag ingest collection "sops"
  Graphify
  Reranker provider (factory only)
```

---

## 4. End-to-End Request Flow

Example: user types `What is the status of loan 12345?` in the chat pane.

1. `apps/web_ui/src/components/ChatPane.tsx` `handleSend` POSTs JSON to `/api/chat`:
   - `message`, `session_id` (browser UUID), `rep_id` hardcoded `"rep-456"`, `loan_id` from the sidebar if a loan was looked up.
2. Vite (`apps/web_ui/vite.config.ts`) proxies `/api` to `http://127.0.0.1:8000` and strips the `/api` prefix. The backend route is `POST /chat`.
3. `apps/agent_api/main.py` `chat`:
   - `get_chat_provider()`, `get_tools_client_provider()`, `get_prompt_store_provider()`, audit, PII, content safety.
   - `sanitize_inbound` always tokenizes for the audit copy. If `PII__MODE=tokenize`, the LLM sees tokens and tools detokenize. Default mode is `redact_audit_only`, so the LLM sees the raw message.
   - If `session_id` is set, `session_store` loads or creates a session. `loan_id` is stored on the session. It is not appended to the prompt and is not passed into tool arguments. The model only sees `12345` because it is in the message text.
   - `run_agent_turn` (`packages/agent_core/_agent.py`).
4. `classify_intent` (`packages/agent_core/_intent_router.py`) keyword-matches refuse and escalate patterns before any LLM call. A status question is `ANSWER`.
5. System prompt `agent.system` is loaded from the file prompt store (`PROMPT_STORE__FILE_BASE_DIR`, default `./docs`) via `load_system_prompt`.
6. `ChatProvider.chat` (concrete class from `provider_contracts`, selected by `LLM__PROVIDER`, default `bedrock`) is called with `json_mode=True` and the tool definitions from `_tools_for_client`. Default role `system` exposes four tools: `search_sse_apis`, `list_sse_apis`, `call_sse_api`, `search_docs`. Up to 3 rounds. Tool calls execute in-process through `ToolsClientProvider.call` → `ModularToolsClient.call`.
7. Expected tool sequence for this question (model-chosen, not hard-coded):
   - `search_sse_apis` with a query about loan status/summary. Keyword score over the OpenAPI catalog (`packages/sse/catalog.py` `search_operations`).
   - `call_sse_api` with `operation_id` (for example `getLoanSummary`) and `path_params`. `packages/sse/invoke.py` `invoke_sse_api` builds the URL, checks the host allow-list, sends `Authorization: Bearer` from `SSE__API_KEY` when set, `httpx` timeout 30s, no retry.
8. Tool result text is appended as a user message. The model must return JSON matching `AgentTurnOutput` (`answer`, `confidence`, citations, optional refusal). `parse_agent_output` validates. One schema retry (`temperature` 0.1) then a refusal.
9. Back in `/chat`: detokenize the answer if tokenize mode was on; append turns to the session; `evaluate_outbound` content-safety; if unsafe, blank the answer and set a refusal. Audit event `agent_api.chat.turn` to the JSONL sink (`AUDIT__JSONL_DIR`, default `./audit`). `cost_usd` is always `0.0`.
10. One SSE event: `data: {AgentTurnOutput JSON}\n\n`. Not token streaming. The UI reads the body, parses `data: ` lines, and renders `answer` plus tool calls (`ChatMessage`).

Sidebar loan lookup is a different path. `BorrowerContextPane` → `lookupLoan` in `apps/web_ui/src/lib/api.ts` POSTs `/api/mcp/tools/call` with `name: call_sse_api` and `operation_id` `getLoanSummary` / `getBorrowerSummary`. That hits `mcp_routes.call_mcp_tool`, which calls the same `ModularToolsClient`. No LLM, no intent router, no outbound safety.

---

## 5. Chat UI

| Item | Actual |
|---|---|
| Framework | React  + TypeScript, Vite, Tailwind. Entry `apps/web_ui/src/main.tsx`, shell `App.tsx`. |
| Layout | Left `BorrowerContextPane`, main `ChatPane`. |
| Chat endpoint | `POST /api/chat` → backend `POST /chat`. |
| Memory | `GET /api/chat/memory/{sessionId}` → `GET /chat/memory/{session_id}`. |
| Sidebar data | `POST /api/mcp/tools/call` → `call_sse_api`. |
| Streaming | Fetch + `ReadableStream`. Backend sends one SSE `data:` event per turn after the full turn finishes. |
| Request | `{ message, session_id, rep_id, loan_id }`. `rep_id` is the literal `"rep-456"`. |
| Response | `AgentTurnOutput`: `answer`, `citations`, `tool_calls`, `requires_human_approval` (always true), `confidence`, `refusal`, `escalation`. Errors are `{ error, turn_id }` in the same SSE stream. |
| Errors | Non-OK HTTP throws. SSE `error` field renders an error bubble. JSON parse failures log to the console. |
| Auth | None. No login, no bearer from the browser, no session cookie. CORS allows `http://localhost:5173` and `http://localhost:3000`. |

---

## 6. Agent

| Item | Actual |
|---|---|
| Framework | Custom loop in `run_agent_turn`. LLM calls go through `provider_contracts.llm.AbstractLLMProvider`. Not a separate Agent Framework runtime in this process. |
| Initialization | Per request. Providers are `@lru_cache` factories warmed in the FastAPI lifespan. |
| Model | `LLM__PROVIDER` default `bedrock`. Bedrock defaults: region `us-east-1`, model id `us.amazon.nova-pro-v1:0`. Alternatives in settings: `ollama`, `aoai`, `openai`, `gemini`. |
| Instructions | File prompt `agent.system` plus a text-only JSON preamble in `_agent.py`. |
| Tool registration | Static list `_SSE_ANSWER_TOOLS` in `_agent.py`, filtered by `ModularToolsClient.allowed_tools`. |
| Tool selection | The LLM returns `tool_calls`. There is no embedding router and no Graphify lookup. |
| Execution | `_execute_tools` → `tools_client.call(ToolCall)`. Max 3 rounds. Args detokenized only when a PII token map exists. Recorded args stay tokenized. Result summary truncated to 500 characters for the audit item; the model sees that same truncated summary. |
| Streaming | The LLM call is not streamed to the client. `/chat` emits one SSE frame. |
| Conversation state | `SessionStoreProvider`, default in-memory, TTL 60 minutes, max 50 turns. History trimmed by `max_history_tokens` (default 2048). Turns that mention `session.loan_id` can be kept over budget. |
| Errors | Tool exceptions become `ToolResult.success=False`. Parse failure retries once, then refusal. Uncaught exceptions in `/chat` become an SSE error payload. |
| Retry | Schema retry only (`_MAX_RETRIES = 1`). No HTTP retry on SSE calls. No LLM retry on transport failure. |

Intent gate (before the LLM):

- Escalate: self-harm, threats, CFPB/attorney/complaint, bankruptcy/litigation, fraud, identity verification.
- Refuse: rate quotes, financial advice phrasing, payment/forbearance mutation phrasing, payoff quotes.
- Else: answer.

`requires_human_approval` is hard-coded `True` on `AgentTurnOutput`. The UI does not block on it.

---

## 7. Tool Inventory

The agent LLM only receives tools that are both in `_SSE_ANSWER_TOOLS` and allowed by role. Default `AGENT_ROLE=system` → `sse.read` + `docs.search`.

| Tool | Purpose | API | Read/Write | Registration | Implementation |
|---|---|---|---|---|---|
| `search_sse_apis` | Keyword search of loaded OpenAPI operations | None (local catalog) | Read | `_SSE_ANSWER_TOOLS`; scope `sse.read` | `packages/sse/tools.py` `handle_search_sse_apis` |
| `list_sse_apis` | List operations, optional `source_label`, optional catalog refresh | Swagger HTTP only when not in fixture mode | Read | same | `handle_list_sse_apis` |
| `call_sse_api` | Invoke one REST operation by `operation_id` or method+path | SSE REST via `httpx` | **Any HTTP method the caller passes.** No GET-only guard | same | `handle_call_sse_api` → `invoke_sse_api` |
| `search_docs` | Vector search of markdown docs | Embedding + vector store, namespace `docs` | Read | `_SSE_ANSWER_TOOLS`; scope `docs.search` | `packages/docs/service.py` `DocsService.search` |
| `index_docs` | Chunk and upsert `data/sops` | Same vector store | Write to index | `ModularToolsClient` only; scope `docs.index`. Not in the LLM list | `DocsService.index_directory` |
| `get_customer_servicing_summary` | Fixed SELECT or fixture text | SQL Server `dbo.SSE_Servicing_Data` | Read | Scope `db.read`. Not in the LLM list | `packages/db/client.py` |
| `run_read_only_sql` | Ad-hoc SQL if it classifies as SELECT | SQL Server | Read (keyword block on writes) | Scope `db.read`. Not in the LLM list | `SqlServerClient.run_read_only_query` |
| `wiki_document_feature` | Stub | None | n/a | Scope `wiki.write_docs`. Not in the LLM list | `packages/wiki/tools.py` returns "not yet ported" |
| `wiki_search_gitlab` | Stub | None | n/a | `wiki.gitlab` | same |
| `wiki_get_jira_ticket` | Stub | None | n/a | `wiki.jira` | same |
| `wiki_resolve_package` | Stub | None | n/a | `wiki.packages` | same |
| `wiki_read_page` | Stub | None | n/a | `wiki.screen` | same |

Classification:

- `search_sse_apis`, `list_sse_apis`: catalog search over OpenAPI, not a live business API.
- `call_sse_api`: direct HTTP wrapper over whatever the catalog describes.
- `search_docs` / `index_docs`: RAG.
- `get_customer_servicing_summary`, `run_read_only_sql`: database. Off the default agent.
- `wiki_*`: placeholders. Off the default agent.
- No graph tool is exposed to the agent.

Roles (`packages/common/scopes.py`): `system` and `user` (= SSE read + docs + eakg). `care_rep` = deprecated alias of `user`. `customer` = SSE read only. `pm` adds `wiki.jira`. `dev` adds docs index, SQL, and all wiki tools. `/mcp/tools/call` uses the process `AGENT_ROLE` allow-list. Key scopes on `POST /mcp/keys` are stored and not applied to the call.

Per-tool detail for the four agent tools:

```text
Tool name: search_sse_apis
Purpose: Rank OpenAPI operations by token overlap on id, path, summary, tags, params
Input: query (required), limit (optional, cap 50)
Output: Text lines from summarize_operation, or "No matching SSE API operations."
Implementation: packages/sse/tools.py, packages/sse/catalog.py
Underlying API: None
Authentication: None
Read/Write: Read
Where registered: packages/agent_core/_agent.py _SSE_ANSWER_TOOLS
Where executed: ModularToolsClient.call → dispatch_sse_tool

Tool name: list_sse_apis
Purpose: Dump catalog sources and operations
Input: source_label, limit (cap 200), refresh
Output: Header with source counts plus operation lines
Implementation: packages/sse/tools.py
Underlying API: Swagger GET when fixture_path is unset
Authentication: Bearer from SSE__API_KEY on swagger fetch
Read/Write: Read
Where registered: _SSE_ANSWER_TOOLS
Where executed: ModularToolsClient.call

Tool name: call_sse_api
Purpose: Perform the HTTP call for one operation
Input: operation_id and/or method+path, path_params, query, body, headers
Output: JSON string (max 8000 chars): ok, status, url, cache_hit, duration_ms, data, error
Implementation: packages/sse/invoke.py
Underlying API: URL from operation server, else source base, else SSE__API_BASE_URL
Authentication: Bearer SSE__API_KEY if Authorization not already in headers
Read/Write: Method is not restricted
Where registered: _SSE_ANSWER_TOOLS
Where executed: ModularToolsClient.call

Tool name: search_docs
Purpose: Semantic-ish nearest neighbours over embedded markdown (embed query, vector search, no rerank)
Input: query (required), top_k (default 5)
Output: Scored snippets with path and corpus, or "No matching documents."
Implementation: packages/docs/service.py
Underlying API: Embedding provider + vector store provider
Authentication: Whatever those providers use (Gemini/Bedrock/Qdrant/AI Search settings)
Read/Write: Read
Where registered: _SSE_ANSWER_TOOLS
Where executed: ModularToolsClient.call
```

---

## 8. Real API Integration

```text
Agent tool call_sse_api
   ↓
ModularToolsClient.call
   ↓
dispatch_sse_tool → invoke_sse_api
   ↓
OpenApiCatalogService (base URL, bearer, allow-list)
   ↓
httpx request to the SSE host
```

| API | Client | Configuration | Authentication | Purpose |
|---|---|---|---|---|
| SSE REST (loan servicing and other swagger apps) | `invoke_sse_api` (`httpx.AsyncClient`, timeout 30s) | `SSE__API_BASE_URL`, `SSE__API_KEY`, `SSE__USE_FIXTURE`, `SSE__FIXTURE_PATH`, `SSE__SWAGGER_LINKS` or `SSE__SWAGGER_URLS` | Static bearer on the process. Not the rep's token. | Live loan and related reads (and any other method the tool is given) |
| Swagger documents | `OpenApiCatalogService.load` | Same bearer and link list. Skipped entirely when a fixture path is set | Same bearer | Build the operation catalog |
| Default swagger links in code | `packages/sse/loader.py` `DEFAULT_SWAGGER_LINKS` | Used when `SSE__SWAGGER_LINKS` and `SSE__SWAGGER_URLS` are empty | Bearer if `SSE__API_KEY` set | PennEDocs and CoreComponents dev swagger URLs checked into source |
| SQL Server | `SqlServerClient` (`aioodbc` when not fixture) | `SQL_SERVER__*` | SQL user/password on the connection string | Optional servicing summary. Default `SQL_SERVER__FIXTURE_MODE=true` |
| Confluence | Policy source used by `packages/rag/ingest.py` | `DATA__CONFLUENCE__*` | API token + username | SOP ingest. Not called by `search_docs` |
| Legacy Loan Services client | `RestApiLoanProvider` via `get_loan_data_provider` | `DATA__LOAN_API__BASE_URL`, `DATA__LOAN_API__API_KEY`, path templates, timeout | Bearer | Probe script `scripts/probe_loan_api.py` and tests. Not `run_agent_turn` |
| LLM | `get_chat_provider` | `LLM__PROVIDER` and nested keys | Bedrock API key or IAM, or other provider keys | Generation and tool choice |
| Embeddings / Qdrant | `get_embedding_provider`, `get_vector_store_provider` | `EMBEDDING__*`, `VECTOR_STORE__*` | Provider-specific | `search_docs` and ingest |

`call_sse_api` behavior that matters for a later MCP boundary:

- Host allow-list: `assert_allowed_url` permits only origins of `SSE__API_BASE_URL` and configured swagger URLs.
- Path params are required when the template contains `{name}`.
- GET may be cached if a cache object is passed. `get_tools_client_provider` does not pass one, so cache is unused on the agent path.
- No retry, no circuit breaker. Errors return `ok: false` inside the JSON body rather than raising, except allow-list and missing path params, which raise and become a failed `ToolResult`.
- Response body is truncated to 8000 characters in the tool string, then to 500 characters in `ToolCallItem.result_summary` before the model sees it.

`SSE__USE_FIXTURE` defaults to **true**. On boot the factory writes `data/sse-fixture-openapi.json` from `packages/sse/fixture.py` and points the catalog at that file. HTTP calls still use `SSE__API_BASE_URL` (code default is the CoreComponents dev host) unless the fixture operation carries its own server URL. Live swagger is not fetched until fixture mode is off and `SSE__FIXTURE_PATH` is empty.

---

## 9. Configuration

```text
.env
  ↓  pydantic-settings, nested delimiter "__", extra=forbid
packages/common/settings.py  Settings
  ↓  packages/common/providers/factory.py
API clients / providers
  ↓
External APIs
```

Loaded once per process via a cached `Settings()`. Application code is not supposed to read `os.environ` except `settings.py`. `main.py` does use `os.makedirs` for `audit/memory.md`; that is a path, not config.

Variable names (no values):

**Agent role and tools**

- `AGENT_ROLE` — `system` (default), `user` (`care_rep` alias), `customer`, `pm`, `dev`
- `TOOLS_CLIENT__PROVIDER` — only `modular` is implemented

**SSE (the live answer API)**

- `SSE__API_BASE_URL`
- `SSE__API_KEY` — bearer for swagger fetch and REST calls
- `SSE__USE_FIXTURE` — default true
- `SSE__FIXTURE_PATH`
- `SSE__SWAGGER_LINKS` — JSON list of `{id,label,url}`
- `SSE__SWAGGER_URLS` — URL list; ids derived from hostnames

**Legacy loan client (not on the agent turn)**

- `DATA__MODE` — deprecated; maps to loan source
- `DATA__LOAN_SOURCE` — `mock` or `real`
- `DATA__LOAN_API__BASE_URL`
- `DATA__LOAN_API__API_KEY`
- `DATA__LOAN_API__TIMEOUT_SECONDS`
- `DATA__LOAN_API__API_VERSION`
- `DATA__LOAN_API__SUMMARY_PDM_MODEL`
- `DATA__LOAN_API__GET_LOAN_PATH` and the other path template fields on `LoanApiConfig`

**SOP / Confluence ingest**

- `DATA__SOP_SOURCE` — `local`, `confluence`, `both`
- `DATA__SOP_CONFLUENCE_MODE` — `cache` or `live`
- `DATA__CONFLUENCE__BASE_URL`
- `DATA__CONFLUENCE__API_TOKEN`
- `DATA__CONFLUENCE__USERNAME`
- `DATA__CONFLUENCE__SPACE_KEYS`
- `DATA__CONFLUENCE__PAGE_IDS`
- `DATA__CONFLUENCE__ANCESTOR_IDS`
- `DATA__CONFLUENCE__EXPAND_CHILDREN`
- `DATA__CONFLUENCE__PII_SCRUB`
- `DATA__CONFLUENCE__ARTIFACT_DIR`

**LLM**

- `LLM__PROVIDER` — default `bedrock`
- `LLM__OLLAMA__BASE_URL`, `LLM__OLLAMA__MODEL_FAST`, `LLM__OLLAMA__MODEL_ACCURATE`
- `LLM__AOAI__ENDPOINT`, `LLM__AOAI__DEPLOYMENT_FAST`, `LLM__AOAI__DEPLOYMENT_ACCURATE`, `LLM__AOAI__API_VERSION`
- `LLM__OPENAI__API_KEY`, `LLM__OPENAI__BASE_URL`, `LLM__OPENAI__MODEL`
- `LLM__BEDROCK__REGION`, `LLM__BEDROCK__MODEL_ID`, `LLM__BEDROCK__PROFILE`, `LLM__BEDROCK__API_KEY`, `LLM__BEDROCK__ACCESS_KEY_ID`, `LLM__BEDROCK__SECRET_ACCESS_KEY`, `LLM__BEDROCK__SESSION_TOKEN`
- `LLM__GEMINI__API_KEY`, `LLM__GEMINI__MODEL`
- `LLM__DETERMINISTIC_BY_DEFAULT`

**Embeddings and vector store**

- `EMBEDDING__PROVIDER` — default `gemini`
- `EMBEDDING__GEMINI__API_KEY`, `EMBEDDING__GEMINI__MODEL`
- `EMBEDDING__AOAI__ENDPOINT`, `EMBEDDING__AOAI__DEPLOYMENT`, `EMBEDDING__AOAI__API_VERSION`
- `EMBEDDING__BEDROCK__REGION`, `EMBEDDING__BEDROCK__MODEL_ID`, `EMBEDDING__BEDROCK__PROFILE`, `EMBEDDING__BEDROCK__DIMENSIONS`, `EMBEDDING__BEDROCK__API_KEY`, `EMBEDDING__BEDROCK__ACCESS_KEY_ID`, `EMBEDDING__BEDROCK__SECRET_ACCESS_KEY`, `EMBEDDING__BEDROCK__SESSION_TOKEN`
- `VECTOR_STORE__PROVIDER` — default `qdrant`
- `VECTOR_STORE__QDRANT__URL`, `VECTOR_STORE__QDRANT__COLLECTION`, `VECTOR_STORE__QDRANT__PATH`
- `VECTOR_STORE__AI_SEARCH__ENDPOINT`, `VECTOR_STORE__AI_SEARCH__API_KEY`, `VECTOR_STORE__AI_SEARCH__INDEX`, `VECTOR_STORE__AI_SEARCH__DIMENSIONS`
- `VECTOR_STORE__PGVECTOR_DSN`, `VECTOR_STORE__PGVECTOR_DIMENSIONS`

**SQL**

- `SQL_SERVER__FIXTURE_MODE` — default true
- `SQL_SERVER__SERVER`, `SQL_SERVER__DATABASE`, `SQL_SERVER__USER`, `SQL_SERVER__PASSWORD`, `SQL_SERVER__DRIVER`

**Safety, audit, session, telemetry**

- `PII__PROVIDER`, `PII__MODE`
- `SAFETY__PROVIDER` — `stub` or `azure`
- `AUDIT__SINK`, `AUDIT__JSONL_DIR`
- `SECRETS__PROVIDER` — `env` or `keyvault`
- `TELEMETRY__PROVIDER` — `console`, `appinsights` (factory raises), `langfuse`
- `TELEMETRY__LANGFUSE__PUBLIC_KEY`, `TELEMETRY__LANGFUSE__SECRET_KEY`, `TELEMETRY__LANGFUSE__HOST`, `TELEMETRY__LANGFUSE__FLUSH_ON_SHUTDOWN`
- `PROMPT_STORE__PROVIDER`, `PROMPT_STORE__FILE_BASE_DIR`
- `SESSION_STORE__PROVIDER`, `SESSION_STORE__TTL_MINUTES`, `SESSION_STORE__MAX_TURNS`, `SESSION_STORE__POSTGRES_DSN`
- `RERANKER__PROVIDER`, `RERANKER__MODEL` — factory exists; `search_docs` does not call it

Local vs dev: same `Settings` class. Fixture flags (`SSE__USE_FIXTURE`, `SQL_SERVER__FIXTURE_MODE`, `DATA__LOAN_SOURCE=mock`) switch clients off live hosts. There is no second settings module.

---

## 10. Graphify (LoanOps only)

Graphify analyzes **this repository**: Python, TypeScript, and markdown under LoanOps-Agent. Nodes are code and doc symbols from AST extraction plus inferred semantic edges. Relationships are imports, references, and inferred links. Output is `graphify-out/graph.json`, `graph.html`, and `GRAPH_REPORT.md`, with dated snapshots under `graphify-out/YYYY-MM-DD/`.

LoanOps does not import Graphify at runtime. It does not choose tools, retrieve APIs, or sit in `/chat`. Cursor rules tell coding agents to query it before grepping. That is a development aid for **LoanOps code**, not for SSE enterprise APIs (ADR-012).

**Do not** put SSE apps, OpenAPI operations, or servicing process edges into `graphify-out/`. Those belong in the **RDF Capability Knowledge Graph** (ADR-012 / ADR-014). Live invocation remains `OpenApiCatalogService` + `invoke_sse_api` / MCP.

The checked-in LoanOps graph may be stale relative to HEAD; treat code as authoritative for LoanOps structure.

---

## 10b. RDF Capability Knowledge Graph (ADR-012 / ADR-014)

**Implemented (v1):** offline OpenAPI → RDFLib Turtle + SPARQL; `CapabilityCatalog` facade. See [`CAPABILITY_KNOWLEDGE_GRAPH.md`](CAPABILITY_KNOWLEDGE_GRAPH.md), [`CAPABILITY_ONTOLOGY.md`](CAPABILITY_ONTOLOGY.md), [`MCP_ARD_PHASE_MATRIX.md`](MCP_ARD_PHASE_MATRIX.md).

```text
OpenAPI catalog (offline build)
        ↓
RDF Capability Graph (RDFLib / Turtle)
        ↓ CapabilityCatalog (search / get / by domain|permission|app|intent)
ordered candidate capabilities → operation_id
        ↓
MCP (execute) → ModularToolsClient → invoke_sse_api
```

- **Not Graphify.** Not the Qdrant `docs` / `sops` namespaces. Not ARD.
- Keyword `search_operations` remains the fallback when the catalog/KG is disabled.
- Semantic retrieval (embed + SPARQL constraints) is a later phase.
- Source-code / Graphify enrichment is offline and later.

KG discovery defaults on (`CAPABILITY_KG__ENABLED=true`); set `false` to disable. OpenAPI keyword search remains the fallback.

---

## 11. RAG

Two pipelines exist. Only one is on the agent path.

**Agent path — `search_docs`**

- Source: markdown under `data/sops` when someone calls `index_docs` (not the default role).
- Chunker: `MarkdownChunker`, about 600 words, 80 overlap, header-aware. `packages/rag/chunker.py`.
- Embed: `get_embedding_provider()` (default Gemini).
- Store: `get_vector_store_provider()`, namespace `"docs"` (`packages/docs/service.py`).
- Retrieve: embed the query, `vector_store.search`, top_k default 5. No reranker.
- Agent use: tool result text pasted back into the next LLM message. Citations in the JSON contract are whatever the model emits (`policy:` / `tool:` prefixes). The API does not auto-attach vector hits as citations. `retrieved_chunk_ids` in the audit record only copies citations whose source starts with `policy:`.

**Ingest CLI — `packages/rag/ingest.py` `ingest_sops`**

- Source: `get_policy_source_provider()` (local SOP files and/or Confluence, per `DATA__SOP_*`).
- Store: collection name `"sops"`, not namespace `"docs"`.
- Not called by `search_docs`. Indexed SOPs in the `sops` collection are invisible to the agent tool unless a separate process also indexes them through `DocsService`.

RAG and a future MCP capability catalog should stay separate. `search_docs` answers policy questions. MCP tool discovery should describe callable APIs. Mixing them will make the model treat SOP chunks as operations.

---

## 12. Safety

| Control | Where | Behavior |
|---|---|---|
| Intent refuse / escalate | `_intent_router.py`, before the LLM | Keyword lists. No model call. |
| Inbound PII | `packages/safety/middleware.py` `sanitize_inbound` | Presidio (or stub). Always writes a `pii.redacted` audit event with tokens, not raw spans' text in the payload fields that are stored as anonymized text. Default `PII__MODE=redact_audit_only` still sends the original message to the LLM. `tokenize` sends `[PERSON_1]` style tokens and detokenizes tool args and the final answer. |
| Outbound safety | `evaluate_outbound` after the answer | `SAFETY__PROVIDER` default `stub`. Unsafe answers are cleared and replaced with a refusal. Event `safety.evaluated`. |
| Tool scope | `ModularToolsClient.call` | Unknown or out-of-scope tool returns an error result. |
| SSE host allow-list | `assert_allowed_url` | `PermissionError` if the origin is not a configured SSE host. |
| SQL write block | `classify_read_only` | Keyword net. Not on the default agent. |
| Human approval flag | schema | Always true. Not enforced in the UI. |
| Prompt injection | No dedicated detector | Tool results are concatenated into the next user message with no sandbox marker beyond the instruction text. |
| Mutation policy | Intent keywords only | `call_sse_api` can still POST/PUT/DELETE if the model emits that method. The keyword gate does not see tool arguments. |

Before a future MCP tool call, keep the existing inbound PII step and the intent gate in the Agent API. Detokenize only inside the trust boundary (today: `_execute_tools`). After the call, keep outbound safety on the final answer, and add an explicit read-only method allow-list at the MCP server so a model cannot turn `call_sse_api` into a write. Audit the tool name, tokenized args, status, and latency on the server as well as in the agent turn record.

---

## 13. Evaluation

| Layer | Location | What it checks |
|---|---|---|
| Unit | `packages/agent_core/tests`, `packages/sse/tests`, `packages/safety/tests`, `packages/db/tests`, `packages/common/tests`, `packages/rag/tests`, `apps/agent_api/tests` | Router, tools catalog, PII, read-only SQL, scopes, API models |
| Provider contracts | `packages/common/providers/contract_tests` | Each provider protocol |
| Agent eval | `packages/eval/run.py` | Loads `data/golden.jsonl`, calls `run_agent_turn` with the live factories |
| Metrics | `packages/eval/metrics.py` | Citation coverage, refusal correctness, latency p95, cost average. Ragas-style faithfulness and answer relevance are named in the threshold table |
| Gate | `packages/eval/thresholds.py` | faithfulness ≥ 0.85, answer relevance ≥ 0.85, citation coverage ≥ 1.0, refusal correctness ≥ 0.95, latency p95 ≤ 4000 ms. Thresholds must not be lowered without approval |
| CI | Eval is a CLI (`python -m packages.eval.run`). It is not wired into the chat request |

There is no separate tool-selection eval. Golden items judge the full turn.

Later MCP selection eval can keep this runner and add checks on `tool_calls[].name` and arguments (expected `operation_id`, no unexpected method). That is a metric addition, not a new agent. Do not change thresholds to make an MCP hop pass.

---

## 14. Audit and Observability

| Signal | Tracked? | Where |
|---|---|---|
| Rep id | Yes, client-supplied string | `ChatRequest.rep_id`, audit `user_id`. UI sends `"rep-456"`. Not authenticated. |
| Session | Yes | `session_id` on the audit event and in the session store. A markdown dump is overwritten at `audit/memory.md` each turn. |
| Agent request | Yes | Audit event `agent_api.chat.turn` with redacted prompt, final output, latency |
| Tool call | Yes, truncated | `ToolCallItem` name, tokenized args, 500-char result summary inside the audit payload |
| API call | Partial | Status, URL, and duration exist on the `call_sse_api` JSON. The model and the audit record only keep 500 characters of that string. No separate HTTP span. |
| Latency | Turn-level only | `latency_ms` on the audit record. SSE invoke also computes `duration_ms` inside the tool payload. |
| Errors | Yes | Failed tools set `result_summary` to the error. Uncaught `/chat` errors are SSE payloads and are not audited. |
| Token usage | No | `cost_usd` is hard-coded `0.0`. Chat provider usage is not copied onto the audit record. |
| Telemetry provider | Configured, not used by `/chat` | `get_telemetry_provider` is not called from `main.py` or `_agent.py`. Console / Langfuse exist for other call sites. App Insights factory raises. |
| PII / safety events | Yes | `pii.redacted`, `safety.evaluated` via `AuditSinkProvider` |
| Audit sink | JSONL default | `AUDIT__SINK=jsonl`, directory `AUDIT__JSONL_DIR`. Flushed on shutdown. |

---

## 15. Existing MCP

Search covered `MCP`, `Model Context Protocol`, `FastMCP`, `MCPClient`, `MCPServer`, `tools/list`, `stdio`, and streamable HTTP.

What exists is a **custom HTTP tool API** on the Agent API, tagged `mcp`:

| Route | File | Behavior |
|---|---|---|
| `GET /mcp/tools` | `apps/agent_api/mcp_routes.py` | `tools_client.list_tools()` — names allowed for `AGENT_ROLE` |
| `POST /mcp/tools/call` | same | Body `{name, arguments}`. Optional `X-API-Key`. If the header is absent, the call is allowed. If present, the key must verify. Scopes on the key are ignored. Dispatch is `ModularToolsClient.call`. |
| `POST /mcp/keys` | same | Registers an in-memory hashed key (`packages/sse/api_keys.py`). Returns the raw key once. Store is process-local and lost on restart. Default scopes `sse.read`, `docs.search`. |

No MCP server class, no MCP client in `packages/agent_core`, no stdio, no SSE MCP transport, no `initialize` / `tools/list` JSON-RPC.

The chat agent does not call these routes. It calls `ModularToolsClient` in-process. The borrower sidebar does call `POST /mcp/tools/call`.

`packages/sse/tools.py` module docstring says "SSE MCP tool handlers". That name means these functions, not the protocol.

---

# MCP Transformation Assessment

## 16. What Should Remain Unchanged

These pieces already match the target "UI and APIs stay; MCP is inserted in the middle," and the code supports leaving them alone for a first milestone:

- Chat UI request/response for `POST /chat` (`ChatPane`, SSE frame, `AgentTurnOutput`).
- Vite proxy.
- Real SSE HTTP client (`invoke_sse_api`), host allow-list, and bearer configuration (`SSE__*`).
- OpenAPI catalog loader and keyword search.
- `DocsService` and the RAG ingest CLI (keep the two indexes distinct; do not fold them into MCP).
- Graphify (developer graph only).
- Intent router and safety middleware on the `/chat` boundary.
- Eval thresholds and golden runner shape.
- Provider factories for chat, embedding, vector store, PII, safety, audit, secrets, session, prompt store.
- `packages/db` and `packages/wiki` until a later phase explicitly exposes them.
- Legacy `RestApiLoanProvider`. Do not revive it as the MCP implementation.

The sidebar's direct `POST /mcp/tools/call` can keep its JSON shape if a thin adapter remains on the Agent API. That adapter is not the protocol server.

## 17. What Needs to Change

### A. Agent tool execution leaves the process boundary

```text
Current:
run_agent_turn → ToolsClientProvider.call → ModularToolsClient (same process)

Proposed:
run_agent_turn → MCP client → MCP server → ModularToolsClient or dispatch_sse_tool / DocsService

Files affected:
packages/agent_core/_agent.py (_execute_tools)
packages/common/providers/factory.py (get_tools_client_provider)
packages/common/settings.py (transport, command or URL — new settings need an ADR)
new MCP client module

Risk:
Extra hop adds latency against the 4000 ms p95 gate. Tool-result truncation (500 chars) still applies and can hide API errors. Schema of ToolCall must stay stable or the eval runner breaks.
```

### B. A real MCP server in front of existing handlers

```text
Current:
No protocol server. HTTP /mcp/tools is a one-shot JSON POST.

Proposed:
MCP server exposes the same four default tools (search_sse_apis, list_sse_apis, call_sse_api, search_docs) by calling the existing Python handlers. No second HTTP stack inside invoke_sse_api.

Files affected:
new server module (suggested home: packages/sse or a new packages/mcp_server — do not put business logic there)
packages/sse/tools.py and packages/docs/service.py stay the handlers
apps/agent_api/mcp_routes.py stays as the UI adapter or delegates to the client

Risk:
Two public tool doors (sidebar HTTP and MCP) can drift. Duplicate dispatch logic if the server reimplements ModularToolsClient instead of calling it.
```

### C. Read-only enforcement at the server

```text
Current:
call_sse_api forwards any HTTP method. Intent keywords only block some user phrases.

Proposed:
MCP server rejects non-GET (or an explicit allow-list of operation ids) before invoke_sse_api.

Files affected:
packages/sse/invoke.py or the MCP wrapper around handle_call_sse_api
packages/agent_core/_intent_router.py only if product wants phrase policy to stay

Risk:
A blanket GET allow-list will break any legitimate POST-read the swagger marks as POST. That list is not in this analysis; it has to come from the catalog.
```

### D. Authz on the tool door

```text
Current:
/mcp/tools/call is open when X-API-Key is omitted. Key scopes are not enforced. Agent uses AGENT_ROLE.

Proposed:
MCP server applies the same scopes.py allow-list. Sidebar and agent both present a credential. Do not invent a second permission table.

Files affected:
apps/agent_api/mcp_routes.py
packages/sse/api_keys.py
packages/common/scopes.py

Risk:
Turning on required keys breaks the sidebar until the UI sends a key. That is a behavior change even if chat copy stays the same.
```

## 18. Proposed MCP Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│ LoanOps process (unchanged UI contract)                     │
│                                                             │
│  Chat UI                                                    │
│    │ POST /chat                         POST /mcp/tools/call│
│    ▼                                        (sidebar only)  │
│  Agent API                                                  │
│    intent + PII + session + safety + audit                  │
│    │                                                        │
│    ▼                                                        │
│  run_agent_turn  (tool list still the four SSE/docs tools)  │
│    │                                                        │
│    ▼                                                        │
│  MCP client                                                 │
│    │  stdio or streamable HTTP (undecided)                  │
└────┼────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│ MCP server                                                  │
│   tools/list  = scopes for the caller                       │
│   tools/call  = ModularToolsClient or dispatch_*            │
│        │                                                    │
│        ├─ packages/sse  invoke_sse_api  (unchanged)         │
│        └─ packages/docs DocsService.search (unchanged)      │
└────┬────────────────────────────────────────────────────────┘
     │
     ▼
 SSE REST hosts (SSE__API_BASE_URL + swagger origins)
```

SQL and wiki stay off this server until Phase 5. Graphify stays outside the box. RAG ingest stays a CLI.

## 19. MCP Tool Boundary

- Existing agent tools (`search_sse_apis`, `list_sse_apis`, `call_sse_api`, `search_docs`) should become the first MCP tools. Same names, same argument schemas as `_SSE_ANSWER_TOOLS`.
- Existing API clients stay. `invoke_sse_api`, `OpenApiCatalogService`, `DocsService`, `SqlServerClient` are not rewritten.
- The MCP server should call those clients (through `ModularToolsClient.call` or `dispatch_sse_tool` / `DocsService.search`). It should not speak HTTP to SSE on its own.
- The agent should call the MCP client from `_execute_tools` instead of `tools_client.call`. The LLM tool-selection loop stays in `run_agent_turn`.
- Validation: path params and host allow-list stay in `invoke_sse_api`. JSON schema for tool args stays on the MCP tool definition (copied from `ToolDefinition.parameters`). Method allow-list is new and belongs on the server, before the client.
- Authorization: `packages/common/scopes.py` stays the allow-list. Enforce it inside `ModularToolsClient` (already) and on the MCP server for remote callers. The Agent API intent router stays the user-phrase policy. Do not move phrase policy into MCP.
- Audit: Agent API keeps the turn audit. MCP server adds a tool-call audit (name, tokenized or redacted args, status, duration, origin). Do not log bearer tokens or raw PII. Detokenize only on the side that already holds the token map; if the MCP server is another process, detokenize before the client call or pass a resolved payload and audit the tokenized form. That split is an open question (section 24).

The sidebar may keep calling the Agent API HTTP adapter. That adapter should become a client of the same server so there is one execution path.

## 20. Capability Model

Not implemented. Shape that matches the four tools already in code:

```yaml
name: call_sse_api
description: Invoke one SSE REST operation from the loaded OpenAPI catalog.
domain: loan_servicing
input_schema:
  type: object
  properties:
    operation_id: {type: string}
    method: {type: string}
    path: {type: string}
    path_params: {type: object}
    query: {type: object}
    body: {}
output_schema:
  type: object
  properties:
    ok: {type: boolean}
    status: {type: integer}
    url: {type: string}
    data: {}
    error: {type: string}
read_only: true   # desired; code today does not enforce this
permissions: [sse.read]
examples:
  - operation_id: getLoanSummary
    path_params: {loan_id: "1000002245"}
not_for:
  - payments
  - forbearance starts
  - payoff quotes
api_mapping:
  client: packages.sse.invoke.invoke_sse_api
  config: [SSE__API_BASE_URL, SSE__API_KEY, SSE__SWAGGER_LINKS]
```

`search_sse_apis` and `list_sse_apis` are catalog tools (`read_only: true`, no upstream body). `search_docs` maps to `DocsService.search` and `docs.search`, not to an SSE operation.

Do not generate one MCP tool per OpenAPI operation in the first milestone. One `call_sse_api` plus search/list keeps the tool count at four. A per-operation explosion is Phase 6.

## 21. API Discovery — Future Phase

Keep this separate from the first MCP server.

```text
OpenAPI (SSE__SWAGGER_LINKS)
Source of packages/sse (invoke, catalog)
Tests (packages/sse/tests)
API documentation
Authorization policies (scopes.py, intent router)
        ↓
API Capability Catalog   (new; not Graphify, not the Qdrant "docs" namespace)
        ↓
Semantic discovery       (search_sse_apis is keyword-only today)
        ↓
MCP tool descriptors
```

Today discovery is `search_operations`: token overlap on operation id, path, summary, tags, and parameter names. That function can remain the first catalog query. Semantic discovery and a capability catalog are a later phase. Graphify is the wrong store for it.

## 22. Migration Plan

### Phase 1

Understand and baseline current behavior. This document is that phase.

- Files: none required beyond `ARCHITECTURE.md`.
- Dependencies: none.
- Tests: existing `packages/sse/tests`, `packages/agent_core/tests`, `apps/agent_api/tests` stay green.
- Rollback: not applicable.

### Phase 2

Add an MCP server that lists and calls the four default tools by delegating to current handlers. Agent still uses in-process `ModularToolsClient`.

- Files: new server module; no change to `invoke_sse_api`.
- Dependencies: an MCP Python library (not in the tree today). Adding it is an implementation step, not part of this analysis.
- Tests: server lists the four names; `call_sse_api` against the fixture catalog hits the same handler as `ModularToolsClient`.
- Rollback: stop the server process. Agent path unchanged.

### Phase 3

Expose one real read through that server. Preferred first operation: `getLoanSummary` via existing `call_sse_api`, with `SSE__USE_FIXTURE` set so the catalog is explicit and the HTTP target is the configured base URL. Do not add a mock API.

- Files: server tool filter or a single allowed `operation_id` for the milestone; `packages/sse/invoke.py` only if a GET guard is added here.
- Dependencies: `SSE__API_BASE_URL`, `SSE__API_KEY`, network to that host.
- Tests: one integration test with a recorded non-secret fixture response or the existing fixture OpenAPI plus a stubbed `httpx` (tests already should not call production with secrets).
- Rollback: disable the server tool; sidebar and agent still use in-process client.

### Phase 4

Point `_execute_tools` at an MCP client. Keep `ModularToolsClient` as the server-side implementation so behavior matches Phase 1.

- Files: `packages/agent_core/_agent.py`, `packages/common/providers/factory.py`, `packages/common/settings.py`.
- Dependencies: Phase 2 server running; new settings (ADR required by `AGENTS.md` before new env vars).
- Tests: agent unit test with a fake MCP client; one live turn comparing tool names to the in-process path; eval golden run, thresholds unchanged.
- Rollback: factory flag back to in-process `modular` client.

### Phase 5

Move `index_docs` only if a role needs it. Then `db.read` tools. Wiki stubs stay unported. Do not expose `run_read_only_sql` until the read-only classifier is covered by MCP tests.

- Files: `packages/common/scopes.py` consumers on the server; `packages/db/client.py` unchanged.
- Dependencies: role decision (`dev` vs `user` / deprecated `care_rep`).
- Tests: scope denial for `user`/`care_rep`; SQL write keyword rejection.
- Rollback: drop the tools from the server list.

### Phase 6

Capability discovery beyond keyword `search_sse_apis`: build / query the **SSE API knowledge graph** (ADR-012) from SSE app source + OpenAPI + process edges; materialize a bounded capability catalog for MCP. Still prefer a small tool surface (catalog + `call_sse_api`), not one MCP tool per OpenAPI operation, unless eval requires otherwise.

- Files: new SSE KG package or module; `packages/sse/catalog.py` as OpenAPI feed; discovery tools. **Not** LoanOps `graphify-out/`. **Not** `DocsService`.
- Dependencies: MCP client path stable (Phase 4); access to SSE app source and swagger.
- Tests: graph build fixtures; semantic + process-order discovery; search ranking.
- Rollback: keep keyword `search_sse_apis` as the only discovery tool.

### Phase 7

Eval for tool choice: expected tool name and `operation_id` on golden items that ask for loan status. Latency budget must include the MCP hop. Do not lower `latency_p95_ms`.

- Files: `packages/eval/metrics.py`, `data/golden.jsonl`, `packages/eval/thresholds.py` only to add a metric, not to weaken one.
- Dependencies: Phase 4.
- Tests: `packages/eval/tests`.
- Rollback: revert the new metric; leave the gate numbers as they are.

### Phase 8

Per-operation tools, semantic catalog, user-token propagation, write operations. Out of scope until Phases 2–4 have a rollback.

- Files: catalog generator, auth design, safety allow-list.
- Dependencies: answers to section 24.
- Tests: authz matrix, PII audit contains no bearer and no raw PII.
- Rollback: feature flag to the four-tool server.

## 23. Risks

- Breaking the agent loop if MCP tool results are not plain text. The loop expects `ToolResult.data` and stringifies 500 characters.
- Latency: up to 3 tool rounds plus a new hop, against a 4000 ms p95 gate. SSE timeout is already 30s per call.
- Authentication is a process-wide bearer (`SSE__API_KEY`). Rep identity is not propagated. A remote MCP server that reuses that bearer widens who can exercise it.
- Tool-selection errors: the model must pick `operation_id` from keyword search. Wrong id returns an HTTP error inside the tool string, which is then truncated.
- Duplicate logic if the MCP server reimplements path substitution or auth headers instead of calling `invoke_sse_api`.
- API failures surface as `ok: false` JSON. The model can still answer. Citation coverage eval may not catch a fabricated status.
- PII: default mode sends raw prompt text to the LLM. Tool results can echo borrower fields into the audit summary (500 chars). A second process must not log `SSE__API_KEY` or detokenized args.
- Prompt injection via tool result text concatenated into the next user message. MCP does not add a boundary by itself.
- Tool count: exposing every swagger operation will blow the prompt. Default catalog already targets 10+ apps.
- Backward compatibility: sidebar JSON `{success, data.text, error}` is not MCP `CallToolResult`. Changing `mcp_routes.py` without an adapter breaks `lookupLoan`.
- Streaming: the UI assumes one SSE `data:` payload per turn. MCP streaming of tokens is not in the current contract.
- Observability: no token counts, no per-HTTP trace, `cost_usd` always 0. An MCP hop will be invisible unless the server logs it.
- `call_sse_api` is not read-only. Keyword refuse rules do not inspect tool arguments.
- `/mcp/tools/call` without `X-API-Key` is unauthenticated.
- `SSE__USE_FIXTURE` defaults true, so a "live" demo can still be a fixture catalog aimed at the configured base URL.
- Two doc indexes (`docs` vs `sops`) mean policy answers can miss ingested Confluence pages.
- Stale Graphify graph can mislead later implementation if someone treats it as the API map.

## 24. Open Questions

- Should the MCP server run in-process with the Agent API or as a separate process?
- Which transport: stdio or streamable HTTP? The current `/mcp/tools` POST must not be mistaken for either.
- Should `run_agent_turn` always use MCP, or should `TOOLS_CLIENT__PROVIDER` keep an in-process fallback?
- Is the first exposed operation `getLoanSummary`, or a different read from the real swagger?
- Should `SSE__USE_FIXTURE` stay on for the first milestone?
- How should `SSE__API_KEY` reach the server without putting it on the chat UI?
- Should MCP enforce `scopes.py`, or only `AGENT_ROLE`?
- Should non-GET `call_sse_api` be rejected? Which POST operations are actually reads?
- Where does PII detokenize if the server is out of process?
- Should the sidebar keep calling Agent API HTTP, or call the MCP server directly?
- Should `loan_id` on `ChatRequest` be injected into the prompt? Today it is not.
- Which index is canonical for policy, `docs` or `sops`?
- Is the eval latency budget allowed to stay 4000 ms once a network hop exists? (Threshold changes need explicit approval; this question does not authorize a change.)

## 25. Final Recommendation

1. Current architecture: React UI → FastAPI `/chat` → in-process agent loop → four tools → `ModularToolsClient` → SSE `httpx` client and docs vector search. Protocol MCP listener is `packages/mcp_server` (ADR-011). Custom `/mcp/tools` remains a JSON helper. LoanOps Graphify is offline and LoanOps-only (ADR-012).
2. Insertion point: between `_execute_tools` and `ModularToolsClient` for execution. API **discovery** later inserts an SSE API knowledge graph + capability catalog **above** MCP tool choice, not inside Graphify.
3. Preserve: Chat UI `/chat` contract, SSE client and `SSE__*` config, docs search, safety and intent gate on the API, eval thresholds, LoanOps Graphify (as code graph only), legacy loan provider (leave it unused).
4. Modify: agent tool client (MCP flag), then SSE KG / capability discovery; read-only guard already on MCP `call_sse_api`.
5. First implementation milestones: MCP server (ADR-011), agent MCP client flag (ADR-013), RDF capability KG + catalog (ADR-014). Next: semantic retrieval, auth harden, Cursor/Gemini validate, governance UI, ARD.
6. Risks: auth/SSO for live chat compare, mixing LoanOps Graphify with capability RDF, dumping full graph to the LLM, latency vs eval gate.
