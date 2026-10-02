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
| `decisions.md` | Architecture Decision Records |
| `logs.md` | Dated session log |
| `Makefile` | `install`, `lint`, `test`, `ingest`, `eval`, `demo`, `down` |
| `check_imports.py` | Script to verify no concrete provider imports leak |
| `docs/01-servicing-agent-prompts.md` | Full project brief (source of truth) |
| `docs/PRD.md` | Product requirements document |
| `docs/Init-Project.ps1` | Project initialisation script (PowerShell) |
| `packages/common/settings.py` | Every env var, single source |
| `packages/common/schemas.py` | Shared Pydantic models (Tools + Agent) |
| `packages/common/providers/` | 10 provider Protocols + re-exports |
| `packages/common/providers/factory.py` | Factory functions (only place with concrete imports) |
| `packages/common/providers/testing.py` | InMemory mock providers for tests |
| `packages/common/providers/contract_tests/` | 10 contract test modules (one per Protocol) |
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
| `.github/workflows/ci.yml` | CI: lint + mypy + unit tests on PR |
| `.github/workflows/eval-gate.yml` | Eval gate: nightly + PR eval runner |
| `data/golden.jsonl` | 50 Q&A golden items |
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
| `VECTOR_STORE__PROVIDER` | `qdrant` | `qdrant` / `ai_search` |
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
| `TELEMETRY__PROVIDER` | `console` | `console` / `appinsights` |
| `TOOLS_CLIENT__PROVIDER` | `modular` | `modular` (in-process) / `mcp` (Streamable HTTP → `:8001`, ADR-013) |
| `AGENT_ROLE` | `system` | Role allow-list for tools (`system`/`care_rep`/`dev`/…) |
| `MCP__HOST` / `MCP__PORT` / `MCP__PATH` | `127.0.0.1` / `8001` / `/mcp` | MCP listener bind + path |
| `MCP__AUTH_TOKEN` | `""` | Bearer for MCP; empty rejects; required when provider=`mcp` |
| `MCP__ROLE` | `system` | Scope allow-list on MCP server (align with `AGENT_ROLE`) |
| `MCP__PRINCIPAL_USER` | `""` | Optional; `x-loanops-user` on `call_sse_api` |
| `MCP__PRINCIPAL_TENANT` | `""` | Optional; `x-loanops-tenant` on `call_sse_api` |
| `CAPABILITY_KG__ENABLED` | `true` | When true, `search_sse_apis` queries EAKG shards; set `false` to disable |
| `CAPABILITY_KG__TTL_PATH` | `data/capability_kg/capabilities.ttl` | Deprecated for discovery; build CLI only |
| `CAPABILITY_KG__NAMESPACE` | `https://loanops.local/ontology/` | RDF namespace |
| `CAPABILITY_KG__APPROVED_ONLY` | `false` | Filter to approved/published review status |
| `CAPABILITY_KG__SEMANTIC` | `false` | Phase 9: cosine rank via embeddings.json (needs ENABLED) |
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
| `SSE__USE_FIXTURE` | `true` | Local OpenAPI fixture vs live swagger |
| `SSE__API_BASE_URL` | (see `.env.example`) | Default SSE host allow-list base |
| `SSE__API_KEY` | `""` | Bearer for live Loan Services / SSE apps |
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
packages/common/providers/testing.py → re-exports all 10 InMemory mocks
```

### The 10 provider categories

| # | Category | Local impl | Azure impl | Factory function |
|---|----------|-----------|------------|------------------|
| 1 | `chat` | Ollama (Llama 3.1 8B) | Azure OpenAI GPT-4o | `get_chat_provider()` |
| 2 | `embedding` | SentenceTransformers (bge-small) | Azure OpenAI text-embedding-3-large | `get_embedding_provider()` |
| 3 | `vector_store` | Qdrant | Azure AI Search | `get_vector_store_provider()` |
| 4 | `pii` | Presidio Analyzer + Anonymizer | Same | `get_pii_provider()` |
| 5 | `content_safety` | Rule-based stub | Azure AI Content Safety | `get_content_safety_provider()` |
| 6 | `audit_sink` | JSONL file | App Insights + ADLS | `get_audit_sink_provider()` |
| 7 | `secrets` | `.env` file | Key Vault + Managed Identity | `get_secrets_provider()` |
| 8 | `telemetry` | Console (structlog) | App Insights | `get_telemetry_provider()` |
| 9 | `tools_client` | HTTP (httpx + Bearer) | Same + mTLS | `get_tools_client_provider()` |
| 10 | `prompt_store` | File (.md reader) | Prompt Flow | `get_prompt_store_provider()` |

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
| `search_sse_apis` | Keyword search over OpenAPI catalogs |
| `list_sse_apis` | List operations (optional app filter) |
| `call_sse_api` | Invoke live REST by `operation_id` or method+path |
| `search_docs` | SOP / docs vector search |
| `search_capabilities` | EAKG capability keyword search (provenance) |
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
```

---

## 12. Module layout (scaffold status)

```
apps/
  agent_api/     [DONE — Step 6]  FastAPI :8000  /chat, /health, /mcp/tools
  web_ui/        [DONE — Step 9]  React + TypeScript + Vite + Tailwind v4
                                  Borrower pane → MCP call_sse_api (no tools_api)

packages/
  sse/           [DONE]           OpenAPI catalog + live invoke (Path A)
  agent_core/    [DONE — Step 5]  Multi-turn tool loop + intent router
  common/        [DONE]           Settings, schemas, providers, modular tools
  rag/           [DONE]           Chunker, ingest CLI, retrieval
  safety/        [DONE — Step 7]  PII + content-safety middleware, SafetyPipeline
  eval/          [PARTIAL]        validate_data done; eval runner + golden runner pending (Step 8)
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
  golden.jsonl     — 50 Q&A items (5 refusal, 10 escalate, 35 happy-path)
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

| Workflow | File | Trigger | Purpose |
|----------|------|---------|---------|
| CI | `ci.yml` | PR | Lint + mypy + unit tests |
| Eval gate | `eval-gate.yml` | Nightly + PR | Eval runner; uploads `out/eval.json` artifact |

> **Note:** Both workflow files exist on disk but IaC (Bicep) modules in `infra/bicep/` are **not yet scaffolded** (Step 10).

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
