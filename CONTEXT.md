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
| `ARCHITECTURE.md` | Detailed architecture documentation |
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
| `apps/tools_api/main.py` | 5 mock servicing endpoints, Bearer auth |
| `apps/tools_api/tests/test_tools_api.py` | Unit tests for Tools API |
| `apps/agent_api/main.py` | Agent API: `/chat` (SSE), `/health`, `/version` |
| `apps/agent_api/models.py` | Agent API request/response models |
| `apps/agent_api/tests/test_agent_api.py` | Unit tests for Agent API |
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
| `TOOLS_CLIENT__PROVIDER` | `http` | `http` / `http_mtls` |
| `TOOLS_CLIENT__BASE_URL` | `http://localhost:8001` | Tools API base URL (client side) |
| `TOOLS_CLIENT__TOKEN` | `dev-token` | Bearer token sent by the client |
| `TOOLS_API_TOKEN` | `dev-token` | Bearer token validated by the Tools API |
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

> `TOOLS_CLIENT__TOKEN` and `TOOLS_API_TOKEN` must match in local dev.

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
| | | `GET /openapi.json` | **exposed** |
| Tools API | `:8001` | `POST /tools/lookup_loan` | **done — Step 4** |
| | | `POST /tools/get_payment_schedule` | **done** |
| | | `POST /tools/get_escrow_breakdown` | **done** |
| | | `POST /tools/check_hardship_eligibility` | **done** |
| | | `POST /tools/search_policy` | **done** |
| | | `GET /tools` (list) | **done** |
| | | `GET /openapi.json` | **exposed** |
| Web UI | Vite dev | proxied via Vite | **done — Step 9** |
| | | `/docs/` | **Redoc Portal** |
| Qdrant | `:6333` | `:6333` (gRPC) | Docker | external |
| Ollama | `:11434` | `:11434` (HTTP) | Docker | external |

---

## 5. Tools API endpoints (live — `apps/tools_api/main.py`)

All endpoints require `Authorization: Bearer <TOOLS_API_TOKEN>` header.

| # | Method | Path | Request body key fields | Returns |
|---|--------|------|------------------------|---------|
| 1 | `POST` | `/tools/lookup_loan` | `loan_id` | `LoanSummary` |
| 2 | `POST` | `/tools/get_payment_schedule` | `loan_id`, `months?` (default 12) | `PaymentSchedule` |
| 3 | `POST` | `/tools/get_escrow_breakdown` | `loan_id` | `EscrowBreakdown` |
| 4 | `POST` | `/tools/check_hardship_eligibility` | `loan_id`, `program` | `EligibilityHint` |
| 5 | `POST` | `/tools/search_policy` | `query`, `state?`, `k?` (default 3) | `PolicyChunks` |
| — | `GET` | `/tools` | — | `list[str]` (tool names) |

Each tool is also aliased at `/{tool_name}` for direct calls. All are **read-only** (no mutations in v1).
Schema models live in `packages/common/schemas.py`.

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
    {"name": "lookup_loan", "args": {"loan_id": "100245"}, "result_summary": "..."}
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
- Allowed `tool_calls.name` values: `lookup_loan`, `get_payment_schedule`, `get_escrow_breakdown`, `check_hardship_eligibility`, `search_policy`

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
make demo        # Tools API :8001 + Agent API :8000 + Vite dev
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

# Run Tools API tests only
uv run pytest apps/tools_api/tests/ -v

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

# Start Tools API locally
uv run uvicorn apps.tools_api.main:app --port 8001 --reload

# Start Agent API locally
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
  agent_api/     [DONE — Step 6]  FastAPI :8000  /chat (SSE), /health, /version
  tools_api/     [DONE — Step 4]  FastAPI :8001  5 endpoints, Bearer auth, unit tests
  web_ui/        [DONE — Step 9]  React + TypeScript + Vite + Tailwind v4
                                  Components: BorrowerContextPane, ChatMessage, ChatPane

packages/
  agent_core/    [DONE — Step 5]  MS Agent Framework agent, intent router,
                                  output parser, prompt loader
  common/        [DONE]           Settings, schemas (full), 10 provider Protocols
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
Proxy: Vite dev server proxies `/api` → Agent API `:8000`, `/tools` → Tools API `:8001`.

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
