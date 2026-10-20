# CONTEXT.md — Quick-Reference Companion

> Read `AGENTS.md` first, then use this file for fast lookups.
> One section per common task — bookmark the one you need.

---

## 1. Project map (file → purpose)

| Path | Purpose |
|------|---------|
| `AGENTS.md` | Full agent instructions, rules, tech stack |
| `CONTEXT.md` | This file — quick ref |
| `TASKS.md` | Active build steps with checkboxes |
| `ARCHITECTURE.md` | **Only** architecture doc (living) |
| `docs/FLOWS.md` | Every application / ops flow (F1–F25) |
| `docs/THREE_QUERY_FLOWS.md` | UI modular vs UI+MCP vs Cursor (3 paths) |
| `docs/DEBUG_LAYER2.md` | Debugger hops (`LAYER2-BP`) + launch compounds |
| `decisions.md` | Architecture Decision Records |
| `logs.md` | Dated session log |
| `Makefile` | `install`, `lint`, `test`, `ingest`, `eval`, `demo`, `down` |
| `scripts/check_project_refs.py` | ProjectReference gate (loanops-* deps vs imports) |
| `docs/01-servicing-agent-prompts.md` | Full project brief (source of truth) |
| `docs/PRD.md` | Product requirements document |
| `docs/Init-Project.ps1` | Project initialisation script (PowerShell) |
| `packages/common/settings.py` | Every env var, single source |
| `packages/common/schemas.py` | Shared Pydantic models (Tools + Agent) |
| `packages/common/providers/` | Provider Protocols + re-exports (incl. graph_store ADR-026) |
| `packages/common/providers/factory.py` | Factory functions (only place with concrete imports) |
| `packages/common/providers/testing.py` | Mock providers for tests (`FakeGraphStore`, …) |
| `packages/common/providers/contract_tests/` | Contract test modules (one per Protocol) |
| `packages/agent_core/_agent.py` | MS Agent Framework agent implementation |
| `packages/agent_core/_intent_router.py` | Pure-function intent router |
| `packages/agent_core/_output_parser.py` | JSON output contract parser with retry |
| `packages/agent_core/_prompt_loader.py` | System prompt loader from docs/ |
| `packages/rag/chunker.py` | `MarkdownChunker` — ~600 token, 80 overlap |
| `packages/rag/ingest.py` | CLI: chunk + embed + upsert SOPs |
| `packages/safety/middleware.py` | `sanitize_inbound` + `evaluate_outbound` + `SafetyPipeline` |
| `packages/safety/models.py` | `SanitizeResult`, `EvaluationResult`, `PiiSpan` |
| `packages/eval/validate_data.py` | Validates loans, SOPs, golden.jsonl |
| `apps/agent_api/main.py` | Agent API: `/chat` (SSE), `/health`, `/mcp/tools` |
| `apps/agent_api/models.py` | Agent API request/response models |
| `apps/agent_api/tests/test_agent_api.py` | Unit tests for Agent API |
| `packages/sse/` | OpenAPI catalog + live `call_sse_api` (replaces tools_api) |
| `apps/web_ui/` | React + TypeScript rep UI (Vite + Tailwind v4) |
| `data/golden.jsonl` | 5 Q&A smoke golden items (MCP tools); full 50 in `data/golden.full.jsonl` |
| `data/sops/` | 38 synthetic SOP markdown files |
| `data/loans.json` | 55 synthetic loans |

---

## 2. Env var quick reference (all from `settings.py`)

| Env var | Default | What it controls |
|---------|---------|------------------|
| `LLM__PROVIDER` | `ollama` | `ollama` / `aoai` |
| `LLM__OLLAMA__BASE_URL` | `http://localhost:11434` | Ollama endpoint |
| `LLM__OLLAMA__MODEL_FAST` | `llama3.1:8b` | Fast LLM |
| `LLM__OLLAMA__MODEL_ACCURATE` | `llama3.1:8b` | Accurate LLM |
| `LLM__AOAI__ENDPOINT` | `""` | Azure OpenAI endpoint |
| `LLM__AOAI__DEPLOYMENT_FAST` | `gpt-4o-mini` | Azure fast deployment |
| `LLM__AOAI__DEPLOYMENT_ACCURATE` | `gpt-4o` | Azure accurate deployment |
| `LLM__AOAI__API_VERSION` | `2024-08-01-preview` | Azure OpenAI API version |
| `LLM__DETERMINISTIC_BY_DEFAULT` | `false` | Deterministic (temp=0) mode |
| `EMBEDDING__PROVIDER` | `local_bge` | `local_bge` / `aoai` |
| `EMBEDDING__AOAI__ENDPOINT` | `""` | Azure embedding endpoint |
| `EMBEDDING__AOAI__DEPLOYMENT` | `text-embedding-3-large` | Azure embedding deployment |
| `VECTOR_STORE__PROVIDER` | `pgvector` | `pgvector` (API index) / `qdrant` / `ai_search` |
| `VECTOR_STORE__QDRANT__URL` | `http://localhost:6333` | Qdrant endpoint |
| `VECTOR_STORE__QDRANT__COLLECTION` | `sops` | Qdrant collection name |
| `VECTOR_STORE__AI_SEARCH__ENDPOINT` | `""` | AI Search endpoint |
| `VECTOR_STORE__AI_SEARCH__API_KEY` | `""` | AI Search API key |
| `VECTOR_STORE__AI_SEARCH__INDEX` | `sops` | AI Search index name |
| `VECTOR_STORE__AI_SEARCH__DIMENSIONS` | `1536` | AI Search vector dimensions |
| `PII__PROVIDER` | `presidio` | PII redactor |
| `PII__MODE` | `redact_audit_only` | `redact_audit_only` / `tokenize` |
| `SAFETY__PROVIDER` | `stub` | `stub` / `azure` |
| `AUDIT__SINK` | `jsonl` | `jsonl` / `appinsights` |
| `AUDIT__JSONL_DIR` | `./audit` | JSONL output directory |
| `SECRETS__PROVIDER` | `env` | `env` / `keyvault` |
| `TELEMETRY__PROVIDER` | `console` | `console` / `langfuse` / `appinsights` — MCP + eval use this; Langfuse = self-hosted only |
| `TELEMETRY__LANGFUSE__HOST` | `http://localhost:3000` | Native self-hosted Langfuse UI (no Docker required); not Langfuse Cloud |
| `TELEMETRY__LANGFUSE__PUBLIC_KEY` / `SECRET_KEY` | `pk-lf-local` / `sk-lf-local` | Match compose `LANGFUSE_INIT_PROJECT_*` |
| `TOOLS_CLIENT__PROVIDER` | `modular` | `modular` (in-process) / `mcp` (Streamable HTTP → `:8001`, ADR-013) |
| `AGENT_ROLE` | `system` | Role allow-list (`system`/`user`/`dev`/`pm`/…; `care_rep`=`user` alias) |
| `MCP__HOST` / `MCP__PORT` / `MCP__PATH` | `127.0.0.1` / `8001` / `/mcp` | MCP listener bind + path |
| `MCP__AUTH_TOKEN` | `""` | Bearer for MCP; empty rejects; required when provider=`mcp` |
| `MCP__ROLE` | `system` | Scope allow-list on MCP server (align with `AGENT_ROLE`) |
| `MCP__PRINCIPAL_USER` | `""` | Optional; `x-loanops-user` on `call_sse_api` |
| `MCP__PRINCIPAL_TENANT` | `""` | Optional; `x-loanops-tenant` on `call_sse_api` |
| `CAPABILITY_KG__ENABLED` | `true` | When true, `search_sse_apis` queries EAKG shards; set `false` to disable |
| `CAPABILITY_KG__NAMESPACE` | `https://loanops.local/ontology/` | RDF namespace |
| `CAPABILITY_KG__APPROVED_ONLY` | `false` | Filter to approved/published review status |
| `CAPABILITY_KG__SEMANTIC` | `false` | Cosine over `embeddings.json`; also auto-on when that sidecar file exists |
| — | — | Discovery = EAKG only: `docs/EAKG_COMMITTED_VS_LOCAL.md` |
| `EAKG__WORKSPACE_DIR` | `.eakg-workspace` | Cloned enterprise repos (gitignored) |
| `EAKG__REGISTRY_PATH` | `data/eakg/registry/repositories.yaml` | Repository Registry |
| `EAKG__SHARD_DIR` | `data/eakg` | Sharded Turtle/JSON store root |
| `EAKG__GITLAB_HOST` | `gitlab.pnmac.com` | glab/SSH host for onboarding |
| `EAKG__OPENAPI_MODE` | `hybrid` | `static` \| `hybrid` \| `live` OpenAPI enrichment |
| `EAKG__LIVE_SPEC_TOKEN` | `""` | Bearer for live swagger fetch |
| `EAKG__CONFIDENCE_THRESHOLD` | `0.85` | Review queue threshold |
| `EAKG__AUTO_APPROVE_STRUCTURAL` | `true` | Auto-approve confidence-1.0 edges |
| `EAKG__NIGHTLY_HOUR` | `2` | Documented nightly hour (external cron) |
| `EAKG__REVIEW_STALE_DAYS` | `14` | Weekly audit stale-proposal age |
| `EAKG__TAAC_FIXTURE_PATH` | `data/eakg/fixtures/taac-client-config.redacted.json` | Redacted TAAC for CI |
| `EAKG__EXTRACTOR` | `auto` | `auto`\|`roslyn`\|`regex` — Roslyn primary (D5) |
| `EAKG__ENGINEERING_GRAPH` | `true` | Graphify AST → `data/eakg/repos/<id>/engineering/graph.json` on sync (non-fatal) |
| `EAKG__ENVIRONMENT` | `local` | Registry env: `local` \| `dev` \| `stage` \| `prod` |
| `EAKG_STORE__BACKEND` | `file` | `postgres` (product) \| `file` (tests) — ADR-027 |
| `EAKG_STORE__DSN` | `""` | Empty → `VECTOR_STORE__PGVECTOR_DSN` |
| `EAKG_STORE__FILE_SHARD_DIR` | (shard dir) | File-backend root when `backend=file` |
| `SSE__CATALOG_SOURCE` | `auto` | `auto` \| `registry` \| `swagger_links` \| `fixture`. `auto`: explicit swagger links, else registry with a usable spec, else fixture |
| `SSE__USE_FIXTURE` | `true` | Legacy fixture switch. Does not override an explicit `SSE__CATALOG_SOURCE` |
| `API_INDEX__ENABLED` | `false` | When true, `search_sse_apis` uses `ApiSearchService` (two-stage vector+keyword). Default keeps sidecar/keyword path |
| `API_INDEX__NAMESPACE_PREFIX` | `api_ops` | Vector namespace prefix → `api_ops_<env>_<model8>` |
| `API_INDEX__APP_SHORTLIST_SIZE` | `5` | Stage-1 app shortlist size (1–20; hard cap 8 with keyword-exact apps) |
| `API_INDEX__STALE_AFTER_HOURS` | `48` | Spec/index age threshold for `/ready` per-app `stale` |
| `API_INDEX__SCHEDULER_ENABLED` | `false` | Optional in-process nightly refresh (file lock); prod prefers external cron → `python -m packages.api_index.refresh nightly` |
| `SSE__API_BASE_URL` | (see `.env.example`) | Default SSE host allow-list base |
| `SSE__API_KEY` | `""` | Shared bearer for static broker apps listed in `CREDENTIALS__STATIC_SHARED_APPS`; not sent to every host |
| `CREDENTIALS__PROVIDER` | `static` | `static` \| `mock` \| `auth0_m2m` — `get_credential_broker()` (14th `get_*` in common factory) |
| `CREDENTIALS__STATIC_SHARED_APPS` | `[]` | JSON list of app ids allowed to use `SSE__API_KEY` |
| `CREDENTIALS__AUTH0_DOMAIN` | `""` | Auth0 tenant host for `auth0_m2m` (e.g. `auth.dev.pennymac.plaisse.com`) |
| `CREDENTIALS__AUTH0_CLIENT_ID` | `""` | M2M client id (`auth0_m2m`) |
| `CREDENTIALS__AUTH0_CLIENT_SECRET` | `""` | M2M client secret (`auth0_m2m`) |
| `CREDENTIALS__AUTH0_AUDIENCE` | `https://pennymac` | Shared Plaisse API audience; per-app `requested_destination` from registry `base_url` |
| `GRAPH_STORE__QUERY_URL` | `http://localhost:7200/repositories/loanops` | SPARQL query (GraphDB local; Neptune later) — ADR-026 |
| `GRAPH_STORE__UPDATE_URL` | `…/repositories/loanops/statements` | SPARQL update / statements |
| `GRAPH_STORE__AUTH_TOKEN` | `""` | Optional Bearer (empty local) |
| `GRAPH_STORE__TIMEOUT_SECONDS` | `30` | HTTP timeout for graph store |
| `APP_TOKEN_<APPID>` | unset | Per-app secret via SecretsProvider (e.g. `APP_TOKEN_FEES`) |
| `SSE__SWAGGER_LINKS` | `[]` | JSON list of `{id,label,url}` swagger sources |
| `PROMPT_STORE__PROVIDER` | `file` | `file` / `promptflow` |
| `PROMPT_STORE__FILE_BASE_DIR` | `./docs` | Prompt file directory |
| `DATA__LOAN_SOURCE` | `mock` | `mock` (fixtures) / `real` (Loan Services API) |
| `DATA__SOP_SOURCE` | `local` | `local` / `confluence` / `both` |
| `DATA__SOP_CONFLUENCE_MODE` | `cache` | `cache` (`data/sops/_confluence`) / `live` (Confluence REST) |
| `DATA__MODE` | — | **Deprecated.** `mock`→loan mock+sop local; `real`→loan real+sop both+live |
| `DATA__CONFLUENCE__BASE_URL` | `""` | Confluence site (e.g. `https://pennymac.atlassian.net`) |
| `DATA__CONFLUENCE__USERNAME` | `""` | Atlassian account email |
| `DATA__CONFLUENCE__API_TOKEN` | `""` | Atlassian API token |
| `DATA__CONFLUENCE__PAGE_IDS` | `[]` | Explicit page IDs to ingest |
| `DATA__CONFLUENCE__ANCESTOR_IDS` | `[]` | Book page IDs (expand to leaf children) |
| `DATA__CONFLUENCE__EXPAND_CHILDREN` | `true` | Expand ancestors to direct leaf children |
| `DATA__CONFLUENCE__PII_SCRUB` | `regex` | `regex` / `presidio` / `off` |
| `DATA__CONFLUENCE__ARTIFACT_DIR` | `data/sops/_confluence` | Local markdown cache (gitignored) |

> Loan answers: `search_sse_apis` → `call_sse_api` (live OpenAPI). No `apps/tools_api`.

---

## 3. Provider layer (load-bearing abstraction)

### Pattern

```
packages/common/providers/<name>.py  → re-exports Protocol from provider_contracts
packages/common/providers/factory.py → get_<name>_provider() → reads Settings → returns impl
packages/common/providers/testing.py → re-exports InMemory mocks
```

### Provider categories

`packages/common/providers/factory.py` exposes **14** `get_*` factories (incl. `get_credential_broker`). `get_tools_client_provider()` lives in `packages/tools/factory.py`.

| # | Category | Local impl | Azure / cloud | Factory function |
|---|----------|-----------|---------------|------------------|
| 1 | `chat` | Ollama (Llama 3.1 8B) | Azure OpenAI GPT-4o / Bedrock | `get_chat_provider()` |
| 2 | `embedding` | SentenceTransformers (bge-small) | Azure OpenAI / Bedrock | `get_embedding_provider()` |
| 3 | `vector_store` | Qdrant (default); API index prefers pgvector | Azure AI Search / Qdrant Cloud | `get_vector_store_provider()` |
| 4 | `pii` | Presidio Analyzer + Anonymizer | Same | `get_pii_provider()` |
| 5 | `content_safety` | Rule-based stub | Azure AI Content Safety | `get_content_safety_provider()` |
| 6 | `audit_sink` | JSONL file | App Insights + ADLS | `get_audit_sink_provider()` |
| 7 | `secrets` | `.env` file | Key Vault + Managed Identity | `get_secrets_provider()` |
| 8 | `telemetry` | Console (structlog) | App Insights / Langfuse | `get_telemetry_provider()` |
| 9 | `tools_client` | Modular / MCP HTTP | Same | `get_tools_client_provider()` (Tools) |
| 10 | `prompt_store` | File (.md reader) | Prompt Flow | `get_prompt_store_provider()` |
| 11 | `session_store` | In-memory / file | Postgres | `get_session_store_provider()` |
| 12 | `reranker` | Local / none | Cloud rerank | `get_reranker_provider()` |
| 13 | `loan_data` / `policy_source` | Mock / local | Live APIs | `get_loan_data_provider()` / `get_policy_source_provider()` |
| 14 | `credential_broker` | Static / Mock (+ cache) | Pluggable (OQ-1) | `get_credential_broker()` |

### Rules
- **No concrete imports** outside `packages/common/providers/`
- **No `os.environ` / `os.getenv`** outside `packages/common/settings.py`
- All factory functions use `@lru_cache` (singleton per Settings)

---

## 4. Ports & services

| Service | Port | Route | Status |
|---------|------|-------|--------|
| Agent API | `:8000` | `POST /chat` (SSE) | **done — Step 6** |
| | | `GET /health` | **done** |
| | | `GET /version` | **done** |
| | | `GET /mcp/tools`, `POST /mcp/tools/call` | **done** |
| | | `GET /openapi.json` | **exposed** |
| Web UI | Vite `:5173` | `/api` → Agent `:8000` | **done — Step 9** |
| | | Borrower pane uses MCP `call_sse_api` | **done** |
| | | `/docs/` | **Redoc Portal** |
| Qdrant | `:6333` or embedded path | vector store | external / local |
| Ollama | `:11434` | optional local LLM | external |

---

## 5. Live SSE tools (replaces tools_api)

Agent / MCP tools (role `system`):

| Tool | Purpose |
|------|---------|
| `search_sse_apis` | Embedding search over OpenAPI ops (keyword fallback) + optional EAKG vectors |
| `list_sse_apis` | List operations (optional app filter) |
| `call_sse_api` | Invoke live REST by `operation_id` or method+path |
| `search_docs` | SOP / docs vector search |
| `search_capabilities` | EAKG capability keyword search (provenance) |
| `describe_application` | Proxies / packages / topics / outbound routes for one app |
| `search_code` | Needle search over per-app `engineering/graph.json` (AST) |
| `explain_capability` | Capability → API → code → authz + evidence |
| `find_providers` | Which app/API provides a capability |
| `impact_of_change` | Incoming cross-app edges for an API/app |

Configure sources with `SSE__SWAGGER_LINKS` + `SSE__API_KEY`. Catalog fallback: `SSE__FIXTURE_PATH`.

Enterprise multi-repo graph: `python -m packages.eakg onboard --id fees --local-path ...` then
`python -m packages.eakg cross-app`. Schedule: `python -m packages.eakg sync repo|nightly|audit`.

---

## 6. Safety middleware processing order

```
Inbound:  PII anonymize → Audit emit → Agent
Outbound: Agent → Content safety check → Audit emit → User
```

Implementation: `packages/safety/middleware.py` — `sanitize_inbound()`, `evaluate_outbound()`, `SafetyPipeline` class.
Models: `packages/safety/models.py` — `SanitizeResult`, `EvaluationResult`, `PiiSpan`.

On safety block: return `{ "intent": "escalate", "reply": "...", "citations": [] }`

---

## 7. Agent output contract (`AgentTurnOutput` schema)

Every agent turn produces a JSON object matching `AgentTurnOutput` in `packages/common/schemas.py`:

```json
{
  "answer": "rep-facing draft reply with [1] citation markers",
  "citations": [
    {"id": 1, "source": "policy:escrow/annual-analysis.md#sec-2", "snippet": "..."}
  ],
  "tool_calls": [
    {"name": "call_sse_api", "args": {"operation_id": "getLoanSummary", "path_params": {"loan_id": "1000002245"}}, "result_summary": "..."}
  ],
  "requires_human_approval": true,
  "confidence": 0.92,
  "refusal": null,
  "escalation": null
}
```

- `requires_human_approval` is always `true` in v1
- `confidence` is 0.0–1.0 (model self-rated grounding)
- `refusal` is a string or null; set when refusing out-of-scope requests
- `escalation` is `{category, reason}` or null; `category` ∈ `safety | complaint_or_regulatory | legal_status | fraud | identity`
- Every factual claim must have a `policy:` or `tool:` source prefix in `citations`
- Allowed `tool_calls.name` values (system role): `search_sse_apis`, `list_sse_apis`, `call_sse_api`, `search_docs`

---

## 8. Eval gates (do not lower thresholds)

| Metric | Threshold | What it measures |
|--------|-----------|-----------------|
| `faithfulness` | ≥0.85 | Answer grounded in context |
| `citation_coverage` | =1.0 | Every factual claim cited |
| `refusal_correctness` | ≥0.95 | Correctly refused out-of-scope |
| `p95_latency_ms` | ≤4000 | 95th percentile response time |

---

## 9. Make targets

```makefile
make install     # uv sync (install all deps)
make lint        # ruff check + ruff format --check + mypy --strict
make test        # pytest (all tests)
make ingest      # python -m packages.rag.ingest data/sops
make eval        # python -m packages.eval.run --golden data/golden.jsonl --report out/eval.json
make ui-install  # npm install in apps/web_ui
make demo        # Agent API :8000 + Vite :5173
make down        # kill background processes
```

MCP observability (self-hosted Langfuse, shared local Postgres — **no Docker**):

```bash
# once on same Postgres server as loanops:
psql -U postgres -h localhost -c "CREATE DATABASE langfuse;"
# Run Langfuse natively (upstream self-host) with:
#   DATABASE_URL=postgresql://postgres:postgres@localhost:5432/langfuse
# UI http://localhost:3000 — keys pk-lf-local / sk-lf-local (or your project keys)
# TELEMETRY__PROVIDER=langfuse  (+ TELEMETRY__LANGFUSE__* in .env)
python -m packages.mcp_server.eval_run   # fixture scores → telemetry only
# Without Langfuse running: leave TELEMETRY__PROVIDER=console (spans/metrics to stdout)
# Optional (Docker users only): docker compose -f docker-compose.langfuse.yml up -d
```


---

## 10. PII patterns (Presidio)

Redacted in all user messages before reaching the LLM:

| Pattern | Example | Replacement |
|---------|---------|-------------|
| SSN | `123-45-6789` | `[REDACTED SSN]` |
| DOB | `05/15/1980` | `[REDACTED DOB]` |
| Account number | `****1234` | `[REDACTED ACCT]` |
| Full name | `John Smith` | `[REDACTED NAME]` |
| Phone | `(555) 123-4567` | `[REDACTED PHONE]` |
| Email | `a@b.com` | `[REDACTED EMAIL]` |

---

## 11. Common one-liners

```bash
# Run all tests
uv run pytest

# Run a single test file
uv run pytest packages/common/providers/contract_tests/test_embedding.py -v

# Run SSE modular + scopes tests
uv run pytest packages/common/tests packages/sse/tests -v

# Run Agent API tests only
uv run pytest apps/agent_api/tests/ -v

# Run provider contract tests only
uv run pytest packages/common/providers/contract_tests/ -v

# Run safety tests only
uv run pytest packages/safety/tests/ -v

# Run agent core tests only
uv run pytest packages/agent_core/tests/ -v

# Type-check
uv run mypy --strict packages

# Lint + format
uv run ruff check . && uv run ruff format --check .

# Ingest SOPs
uv run python -m packages.rag.ingest data/sops

# Validate synthetic data
uv run python -m packages.eval.validate_data

# Start Agent API locally (sole backend — no tools_api)
uv run uvicorn apps.agent_api.main:app --port 8000 --reload

# Check no concrete provider imports leak
rg "from packages.common.providers.*import" apps/ packages/agent_core packages/rag packages/safety packages/eval

# Check no direct os.environ leaks
rg -n "os\.environ|os\.getenv" --include="*.py" . | rg -v "settings\.py|tests/"

# Registry validate / TAAC dry-run (PowerShell-friendly; no &&)
uv run python -m packages.eakg registry validate --env local
uv run python -m packages.eakg registry import-taac --env dev --dry-run

# Build unified ops + (re)index; sidecar-only skip vector store
uv run python -m packages.api_index.refresh all --env local
uv run python -m packages.api_index report --env local --json

# Scale suite (CI default small; full 30×170)
uv run pytest projects/LoanOps.ApiIndex -m scale --scale-profile=small

# Ready snapshot (MCP up)
Invoke-RestMethod http://127.0.0.1:8001/ready
```

---

## 12. Module layout (scaffold status)

uv workspace under `projects/LoanOps.*` (import paths still `packages.*` /
`apps.agent_api`). See ADR-020.

```
apps/
  web_ui/        [DONE — Step 9]  React + TypeScript + Vite + Tailwind v4

projects/
  LoanOps.AgentApi/   [DONE — Step 6] FastAPI :8000
  LoanOps.AgentCore/  [DONE — Step 5] Multi-turn tool loop
  LoanOps.Tools/      [DONE]          Modular + MCP tools factories
  LoanOps.McpServer/  [DONE]          Streamable HTTP MCP :8001
  LoanOps.Sse/        [DONE]          OpenAPI catalog + live invoke
  LoanOps.Common/     [DONE]          Settings, schemas, providers
  LoanOps.Rag/        [DONE]          Chunker, ingest CLI
  LoanOps.Docs/       [DONE]          Docs vector search
  LoanOps.Db/         [DONE]          Read-only SQL
  LoanOps.Wiki/       [DONE]          Wiki stubs
  LoanOps.Safety/     [DONE — Step 7] PII + content-safety
  LoanOps.CapabilityKg/ [DONE]        RDF capability catalog
  LoanOps.Eakg/       [DONE]          Enterprise capability KG
  LoanOps.ApiIndex/   [DONE]          Unified ops + vector search (ADR-024)
  LoanOps.Eval/       [DONE]          harness + thresholds; golden on MCP tools; live MCP eval still SSO-gated
```

---

## 13. Data directory

```
data/
  loans.json       — 55 synthetic loans
  sops/            — 38 SOP markdown files with YAML frontmatter
                     7 subdirectories: complaints, escrow, hardship,
                     loss-mitigation, payments, payoff, state-specific
  sops/_confluence/ — gitignored Confluence export cache
                      (DATA__SOP_SOURCE=confluence|both + MODE=cache|live)
  golden.jsonl     — 5 smoke items (1 refusal, 1 escalate, 3 happy-path)
  golden.full.jsonl — full 50-item suite (archive)
```

SOP selection (`DATA__SOP_SOURCE`): `local` | `confluence` | `both`.
Confluence mode (`DATA__SOP_CONFLUENCE_MODE`): `cache` reads
`data/sops/_confluence/`; `live` fetches Confluence REST and refreshes cache.
Demo mix: `DATA__LOAN_SOURCE=mock` + `DATA__SOP_SOURCE=confluence` +
`DATA__SOP_CONFLUENCE_MODE=cache`.

---

## 14. Docker dependencies (local dev)

```bash
# Start Qdrant
docker run -d -p 6333:6333 qdrant/qdrant

# Start Ollama
docker run -d -p 11434:11434 ollama/ollama
docker exec -it <container> ollama pull llama3.1:8b
```

---

## 15. Commit conventions

```
feat:     new feature
fix:      bug fix
chore:    tooling, deps, CI
docs:     documentation
refactor: code change with no behavior change
test:     test-only change
```

Subject ≤ 50 chars, body explains "why" not "what". Use scope for affected area: `feat(rag):`, `fix(tools):`, `chore(deps):`.

---

## 16. Web UI components (`apps/web_ui/`)

| Component | File | Purpose |
|-----------|------|---------|
| `BorrowerContextPane` | `src/components/BorrowerContextPane.tsx` | Left pane — borrower loan context display |
| `ChatMessage` | `src/components/ChatMessage.tsx` | Single message with citations, tool traces, confidence |
| `ChatPane` | `src/components/ChatPane.tsx` | Right pane — conversation, Approve & copy, Escalate |
| `App` | `src/App.tsx` | Root component, two-pane layout |

Stack: React 18 + TypeScript + Vite + Tailwind CSS v4.
Proxy: Vite proxies `/api` → Agent API `:8000` only (tools_api removed).

---

## 17. CI / CD (`.github/workflows/`)

No workflow YAMLs on disk yet (`make lint` / `make test` / `make eval` local). Eval gate + PR CI still to add.

---

## 18. Current focus

**Loan fixtures + Confluence-only SOPs:** set
`DATA__LOAN_SOURCE=mock`, `DATA__SOP_SOURCE=confluence`,
`DATA__SOP_CONFLUENCE_MODE=cache`, then re-ingest + restart demo.
Live Confluence refresh: `DATA__SOP_CONFLUENCE_MODE=live` + `make ingest`.

**Remaining leftovers:**
- Step 1.5 leftover — CI grep gate for concrete imports

---

## 19. Knowledge Graph (Graphify)

Batch pipelines (source → output): [`docs/PIPELINES.md`](docs/PIPELINES.md). Engineering-graph analysis (Graphify vs EAKG, registry clones): [`docs/ENGINEERING_GRAPH_ANALYSIS.md`](docs/ENGINEERING_GRAPH_ANALYSIS.md). Wiki vs LoanOps: [`docs/PLAISSE_WIKI_VS_LOANOPS.md`](docs/PLAISSE_WIKI_VS_LOANOPS.md).

This project includes a knowledge graph generated by Graphify to help understand the codebase structure and relationships.

| Resource | Location | Purpose |
|----------|----------|---------|
| Graph data | `graphify-out/graph.json` | Full knowledge graph in JSON format |
| Graph visualization | `graphify-out/graph.html` | Interactive HTML visualization |
| Query tool | `graphify query "<question>"` | Ask questions about the codebase |
| Path finder | `graphify path "<A>" "<B>"` | Find connections between components |
| Documentation | `GRAPHIFY_SETUP.md` | Setup and usage instructions |

To use the knowledge graph:
1. Run `graphify query "What are the main components of this project?"` to get an overview
2. Use `graphify path "ComponentA" "ComponentB"` to find relationships between specific components
3. Open `graphify-out/graph.html` in a browser to explore the interactive visualization

The graph is automatically updated on git commits thanks to the installed hooks.
