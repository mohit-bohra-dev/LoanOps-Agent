# Servicing Agent — Task Tracker

> **Current focus:** EAKG ops schedule + Phase 8 principal slice + MCP 11/12/14 docs; run Cursor/Gemini validation evidence next

---

## Step 1 — Repo skeleton (acceptance: `make install lint test` exits 0)

- [x] Configure `uv` workspace (`pyproject.toml` already stubbed)
- [x] Wire `ruff`, `mypy --strict`, `pytest` via `pyproject.toml`
- [x] Install and configure `pre-commit`
- [x] Verify `make install lint test` exits 0 on clean clone

## Step 1.5 — Provider contracts (do before any feature work)

- [x] `packages/common/settings.py` — full Pydantic Settings with nested provider configs
- [x] `packages/common/providers/base.py` — ProviderHealth, ProviderError, ProviderCallEvent
- [x] Implement Protocol + InMemory impl for all 10 provider categories
- [x] `packages/common/providers/factory.py` — 10 factory functions, lru_cache
- [x] `packages/common/providers/contract_tests/` — one test module per Protocol
- [ ] CI grep gate: no concrete imports outside providers/
- [x] Accept: `mypy --strict packages/common` clean; contract tests green

## Step 2 — Synthetic data

- [x] `data/loans.json` — 50 synthetic loans (CA/TX/FL/NY/OH mix)
- [x] `data/sops/` — 30 synthetic markdown SOPs with YAML frontmatter
- [x] `data/golden.jsonl` — 50 Q&A items (≥5 refusal, ≥5 escalation)
- [x] `python -m packages.eval.validate_data` reports 0 errors

## Step 3 — RAG pipeline

- [x] `LocalBgeEmbeddingProvider` + `QdrantVectorStoreProvider`
- [x] `AWSOpenAIEmbeddingProvider` + `AWSAISearchVectorStoreProvider`
- [x] Chunker: ~600 tokens, 80 overlap, markdown header-aware
- [x] `python -m packages.rag.ingest data/sops` ingests all SOPs
- [x] Nearest-neighbour test: 10 known queries return correct chunk
- [x] `ConfluencePolicyProvider` live ingest (Escrow + Hardship seeds)
- [x] `CompositePolicyProvider` — local dummy + Confluence when `DATA__MODE=real`
- [x] Gitignored local markdown artifacts under `data/sops/_confluence/`

## Step 4 — Tools API → retired

- [x] Originally: FastAPI :8001 mock servicing endpoints
- [x] **Removed `apps/tools_api`** — answers via `packages/sse` + `/mcp/tools` (ADR-010)
- [x] Web UI borrower lookup rewired to MCP `call_sse_api`

## Step 5 — Agent core

- [x] Microsoft Agent Framework agent wired to `get_chat_provider()`
- [x] System prompt loaded from `docs/01-servicing-agent-prompts.md` §B
- [x] Intent router (pure function, no concrete provider import)
- [x] JSON output contract enforced; retry once on schema failure
- [x] Unit tests: happy / refuse / escalate paths against InMemory providers
- [x] Fix test monkeypatches to match protocol signature (self, json_mode)

## Step 6 — Agent API

- [x] FastAPI :8000, `POST /chat` (SSE), `GET /health`, `GET /version`
- [x] `GET /health` aggregates all 10 providers; 503 on failure
- [x] Audit record written per turn via `get_audit_sink_provider()`
- [x] No concrete provider imports in `apps/agent_api`

## Step 7 — Safety layer

- [x] `PresidioPiiProvider` — SSN, DOB, account, name redaction
- [x] `RuleBasedSafetyProvider` + `AWSContentSafetyProvider`
- [x] Middleware: PII anonymize inbound, safety evaluate outbound
- [x] Tests: redaction + blocking pass against both provider configs

## Step 8 — Eval harness

- [x] Runner: `python -m packages.eval.run`
- [x] Metrics: faithfulness >=0.85, citation_coverage =1.0, refusal_correctness >=0.95, p95 <=4000ms
- [x] CI fails on threshold breach; `make eval` seeded regression exits non-zero

## Step 9 — React + TypeScript rep UI

- [x] Two-pane layout: borrower context | conversation
- [x] Citations, tool trace, confidence, Approve & copy, Escalate
- [x] `make demo` brings up full stack end-to-end

## Step 10 — IaC + CI

- [x] Terraform modules: Bedrock, AI Search, ECS Fargate, KV, MI, CloudWatch Logs, Private Endpoints
- [x] `ci.yml`: lint + mypy + unit tests on PR
- [x] `eval-gate.yml`: nightly + PR; uploads `out/eval.json` artifact

## Step 11 — Conversational Memory (Feature)

- [x] Session store abstraction (InMemory impl)
- [x] Background TTL cleanup task
- [x] Agent core memory strategy (Sliding window)
- [x] API integration with session context
- [x] UI updates to handle session IDs and active loan mapping

## Step 12 — Observability & Eval Dashboard

- [x] Implement `LangfuseTelemetryProvider` in `provider-contracts`
- [x] Wire Langfuse into `LoanOps-Agent` settings and factory
- [x] Push eval metrics to Langfuse dashboard from `run_eval`
- [x] Provide `docker-compose.langfuse.yml` for self-hosted instance

## Step 13 — One modular Python product (ADR-010)

- [x] ADR-010 + keep/remove duplicate list
- [x] `provider_contracts`: Bedrock embeddings + Postgres session store
- [x] Embedding choice: local `bge-small` / AWS Titan v2 1024-dim
- [x] SQL prerequisite: `aioodbc` + ODBC Driver 18 documented
- [x] `packages/sse` OpenAPI catalog, invoke, API keys, fixture
- [x] `packages/db` fixed + read-only SQL
- [x] `packages/docs` unified doc search service
- [x] `packages/wiki` specialist stubs (full port pending)
- [x] Modular tools client + scopes; MCP routes on Agent API
- [ ] Live SSE swagger verification
- [ ] Full wiki specialist port
- [ ] ~~AWS image cutover~~ **deferred — local testing only for now**

## Step 14 — Agent MCP client (ADR-013 / Architecture Phase 4)

- [x] ADR-013: `TOOLS_CLIENT__PROVIDER=modular|mcp`
- [x] `McpToolsClient` + Streamable HTTP session → `packages.mcp_server`
- [x] Factory wiring; empty `MCP__AUTH_TOKEN` refuses `mcp` provider
- [x] Unit tests: fake session + agent turn via MCP client
- [x] Live MCP hop smoke (`getLoanSummary` 200) — SSO chat compare still optional
- [ ] Eval golden with MCP hop — after Bedrock SSO green for full `/chat`

## Step 15 — RDF Capability Knowledge Graph (ADR-014)

- [x] Phase 1 baseline refresh + `docs/MCP_ARD_PHASE_MATRIX.md`
- [x] RDFLib + Turtle + SPARQL (`packages/capability_kg`)
- [x] OpenAPI extract → `data/capability_kg/capabilities.ttl`
- [x] `CapabilityCatalog` facade
- [x] Optional `search_sse_apis` KG block when `CAPABILITY_KG__ENABLED=true`
- [x] Semantic retrieval (embed + SPARQL constraints) — `docs/PHASE_9_SEMANTIC_RETRIEVAL.md`
- [ ] Graphify offline enrichment
- [ ] Human review workflow UI
- [ ] ARD (phase 14)

## Step 16 — Enterprise Application Knowledge Graph (ADR-015..019)

- [x] Registry + TAAC + sharded store + .NET extractor + detectors + MCP query tools
- [x] Real pilot onboard (escrow/fees/loanservices via glab)
- [x] Pilot review gate: approve high-value edges; reject noisy `callsOperation` (`review --pilot`)
- [x] Fix extractor method window → `GetLoanSummary` extracted; ranked query smoke
- [x] `search_sse_apis` merges EAKG shards when `CAPABILITY_KG__ENABLED` + `data/eakg/repos` present
- [x] Index schedule ops: `docs/EAKG_INDEX_SCHEDULE.md`, `ci/eakg.gitlab-ci.yml`, `scripts/eakg/*`
- [x] Swagger export ask + extractor upgrade design + registry onboard guide (point 5 docs)
- [ ] Static analyzer upgrade (deferred — see `docs/EAKG_EXTRACTOR_UPGRADE.md`)
- [ ] Live repo #4+ when URL chosen (`docs/EAKG_ONBOARD_REPO.md`)
- [ ] Record Cursor / Gemini validation evidence (checklists ready)

