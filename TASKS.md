# Servicing Agent — Task Tracker

> **Current focus:** Enterprise app scale (ADR-024) shipped P1–P6 — registry catalog, ApiIndex, CredentialBroker, per-app health; product path still MCP (`TOOLS_CLIENT__PROVIDER=mcp`)

## Backlog buckets (C6)

Use these instead of treating every open checkbox as equal priority.

### Now (MCP platform)

- [x] Pipeline control plane Phase 1 PoC (ADR-033) — `openapi_to_api_index` via `/pipelines/*` + ledger + Eval Portal Pipelines tab (2026-11-10)
- [x] Record Cursor validation evidence — `docs/MCP_CURSOR_VALIDATION.md` (2026-10-02)
- [x] Record Gemini validation evidence — **skipped** 2026-10-03 (`docs/MCP_GEMINI_VALIDATION.md`)
- [x] Product demo path: `TOOLS_CLIENT__PROVIDER=mcp` + MCP up + EAKG shards present — MCP hop `getLoanSummary` **200** with Subservicing M2M (2026-10-02)
- [x] MCP server observability — `execute_tool` spans/metrics via TelemetryProvider; fixture eval `python -m packages.mcp_server.eval_run`; self-hosted Langfuse on shared local Postgres DB `langfuse` (native, no Docker; compose optional) (2026-10-16)
- [ ] Eval golden with MCP hop — golden refreshed to MCP tools; **blocked on Bedrock SSO** for full `/chat`
- [x] EAKG capability embeddings wired — `python -m packages.eakg embed`; `query --semantic` (2026-10-04)
- [x] Product semantic on — `CAPABILITY_KG__SEMANTIC=true`; `search_sse_apis` / capability block returns NL hits (2026-10-04; embedder=`local_bge` matches sidecar)
- [x] OpenAPI `search_sse_apis` uses embeddings (2026-10-06); EAKG vectors auto if `embeddings.json` exists
- [x] Richer embed text (summary + HTTP path phrases) — “next payment due” ranks payment-schedule over random “due” ops (2026-10-04); re-run `python -m packages.eakg embed` after reindex
- [x] Cursor→MCP hardening (review 5 Required) — shared GET-only policy, EAKG in Tools, catalog cache, OpenAPI sidecar CLI, `/ready` (ADR-022/023 Proposed) — 2026-04-08


### Next (EAKG feed)

- [x] ADR-027 EAKG non-graph artifacts in Postgres — `EakgArtifactStore` file|postgres; migrate CLI; registry/interface/OpenAPI/ApiIndex ops wired; local 3 apps migrated (`artifacts status` backend=postgres, registry=3) — 2026-10-12
- [x] ADR-028 process KG pilot (Account Maintenance hub + 3 leaf SOPs) — rule extractor, maps, validator, `process extract|load|show|approve|verify-fresh|revalidate|report`; loads stay `pending_review`; no quotes in graph — 2026-10-15
- [ ] Process KG: name escrow SME reviewer → `verified_complete` + capability-link approval + `process approve` (blocked until named)
- [ ] Manual EAKG sync only — **D10:** no Task Scheduler, no cloud schedule — `docs/EAKG_INDEX_SCHEDULE.md`
- [x] Live SSE swagger verify — Loan Services dev 292 ops + GET Summary **200** (2026-10-03) — `docs/SSE_LIVE_SWAGGER.md`
- [ ] Team `swagger tofile` ask — `docs/EAKG_SWAGGER_EXPORT.md`
- [x] **Multi-stack API extract (beyond `*Controller`)** — Roslyn Minimal APIs + tree-sitter Python/Node (2026-10-15). Canonical route identity + multi-adapter merge. Re-onboard after RDF URI change.
  - [x] .NET Minimal API: `Map*` / `MapGroup` / fluent authz in `tools/eakg-dotnet-extract` v2.1.0
  - [x] Tree-sitter: Python (FastAPI/Flask) + Node (Express/Fastify); Java/Go still backlog
  - [ ] Prefer OpenAPI-primary when swagger is complete; code extract fills gaps + evidence (same join shape as today)
  - [x] ADR-018 amended: tree-sitter shipping for py/node; CodeQL out; LLM investigator under ADR-029
- [x] **ADR-029** — Deterministic extract + LLM investigator + pattern feedback (not GraphRAG) — revised 2026-10-15; implemented
  - [x] Coverage manifest + `ConflictRecord` + `gap_ledger` + `candidate_gate` + `investigate_agent`
  - [x] Pattern store `data/eakg/patterns/` + backtest + CLI `investigate` / `patterns`
  - [x] Sources: OpenAPI join gaps, cross-app near-misses, TAAC unmapped keys, code coverage holes
  - [x] Process: rule baseline benchmark tests; investigator gated until benchmark wins
  - [ ] Process investigator adoption (after fixture A/B beats rule extractor)

### Later / parked

- [x] **Refresh golden set for SSE/MCP** — `data/golden.jsonl` `must_call_tools` / `must_cite` rewritten to `search_sse_apis` → `call_sse_api` + `search_docs` (all 50). Thresholds unchanged. Live eval still SSO-gated.
- [ ] **D9** push `vdd` to GitLab — **not yet**; after full test pass
- [x] **Roslyn .NET extractor** cutover (D5) — `tools/eakg-dotnet-extract`, `EAKG__EXTRACTOR=auto`
- [x] Repo #4+ — **D6 freeze at 3** (Escrow/Fees/LoanServices); guide when unfrozen: `docs/EAKG_ONBOARD_REPO.md`
- [x] Static analyzer extras: tree-sitter Python/Node shipped with multi-stack extract (2026-10-15). CodeQL out (license). Taint = SonarQube on SSE pipelines.
- [ ] **SonarQube findings → EAKG graph** — every SSE pipeline already runs SonarQube. Later: pull open vulnerabilities / security hotspots (`api/issues/search`, `api/hotspots/search`) into the graph as finding nodes with `Evidence` (`detector_id=sonarqube`), linked to an existing operation when file+line overlap. Do **not** store them as `callsApplication` (Sonar gives locations, not a resolved app URL). Needs a SonarQube provider + env var (token, base URL, project-key → repository id) before any client code. Re-sync and drop closed issues. Not an API catalog.
- [ ] Graphify offline enrichment into RDF (Phase 10)
- [ ] Human review workflow UI — **D8:** both CLI + Web UI (CLI live; UI still to build)
- [ ] ARD implement (Phase 14) — after 11–12; draft `docs/ARD_RESOURCE_CHOICE.md`
- [ ] Full OBO / RBAC / `requiresPermission` at MCP invoke — **D7 / OQ-1:** static `CredentialBroker` + optional `CREDENTIALS__STATIC_SHARED_APPS` / `APP_TOKEN_*` shipped (ADR-024); later auto-fetch → user OBO → RBAC
- [x] Enterprise app scale P1–P6 (ADR-024) — see **Step 17** (2026-10-09)
- [ ] Full wiki specialist port
- [ ] CI grep gate: no concrete imports outside providers/
- [ ] ~~AWS image cutover~~ **deferred — local testing only**

### Hygiene

- [x] ADR-021 general internal audience (not care-rep-only) — `user` role; docs/prompt — 2026-10-04
- [x] Split into csproj-style uv workspace (`projects/LoanOps.*`, ADR-020) — 2026-10-02
- Decide / cleanup board: [`docs/DECIDE_AND_CLEANUP.md`](docs/DECIDE_AND_CLEANUP.md)
- Committed vs local EAKG: [`docs/EAKG_COMMITTED_VS_LOCAL.md`](docs/EAKG_COMMITTED_VS_LOCAL.md)
- Phase tracker: [`docs/PHASE_STATUS.md`](docs/PHASE_STATUS.md)

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
- [ ] CI grep gate: no concrete imports outside providers/ → **Later / parked**
- [x] Accept: `mypy --strict packages/common` clean; contract tests green

## Step 2 — Synthetic data

- [x] `data/loans.json` — 50 synthetic loans (CA/TX/FL/NY/OH mix)
- [x] `data/sops/` — 30 synthetic markdown SOPs with YAML frontmatter
- [x] `data/golden.jsonl` — 5 smoke items (1 refusal, 1 escalation, 3 happy); full 50 in `data/golden.full.jsonl`
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
- [x] Langfuse local path: shared Postgres DB `langfuse` (native self-host; `docker-compose.langfuse.yml` optional only)
- [x] MCP `execute_tool` telemetry + `packages.mcp_server.eval_run` scores to Langfuse

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
- [x] Live SSE swagger verification → `docs/SSE_LIVE_SWAGGER.md`
- [ ] Full wiki specialist port → see **Later / parked**
- [ ] ~~AWS image cutover~~ **deferred — local testing only for now**

## Step 14 — Agent MCP client (ADR-013 / Architecture Phase 4)

- [x] ADR-013: `TOOLS_CLIENT__PROVIDER=modular|mcp`
- [x] `McpToolsClient` + Streamable HTTP session → `packages.mcp_server`
- [x] Factory wiring; empty `MCP__AUTH_TOKEN` refuses `mcp` provider
- [x] Unit tests: fake session + agent turn via MCP client
- [x] Live MCP hop smoke (`getLoanSummary` 200) — SSO chat compare still optional
- [ ] Eval golden with MCP hop → see **Backlog buckets → Now** (golden refreshed; SSO still blocks live run)

## Step 15 — RDF Capability Knowledge Graph (ADR-014)

- [x] Phase 1 baseline refresh + `docs/MCP_ARD_PHASE_MATRIX.md`
- [x] RDFLib + Turtle + SPARQL (`packages/capability_kg`)
- [x] OpenAPI extract → `data/capability_kg/capabilities.ttl`
- [x] `CapabilityCatalog` facade
- [x] Optional `search_sse_apis` KG block when `CAPABILITY_KG__ENABLED=true`
- [x] Semantic retrieval (embed + SPARQL constraints) — `docs/PHASE_9_SEMANTIC_RETRIEVAL.md`
- [ ] Graphify offline enrichment → **Later / parked**
- [ ] Human review workflow UI → **Later / parked**
- [ ] ARD (phase 14) → **Later / parked**

## Step 16 — Enterprise Application Knowledge Graph (ADR-015..019)

- [x] Registry + TAAC + sharded store + .NET extractor + detectors + MCP query tools
- [x] Real pilot onboard (escrow/fees/loanservices via glab)
- [x] Pilot review gate: approve high-value edges; reject noisy `callsOperation` (`review --pilot`)
- [x] Fix extractor method window → `GetLoanSummary` extracted; ranked query smoke
- [x] `search_sse_apis` merges EAKG shards when `CAPABILITY_KG__ENABLED` + `data/eakg/repos` present
- [x] Index schedule ops: `docs/EAKG_INDEX_SCHEDULE.md`, `ci/eakg.gitlab-ci.yml`, `scripts/eakg/*`
- [x] Swagger export ask + extractor upgrade design + registry onboard guide (point 5 docs)
- [x] Cleanup C1–C6 (gitignore dated graphify backups; committed-vs-local doc; backlog buckets)
- [ ] Static analyzer / repo #4 / validation evidence → see **Backlog buckets**

## Step 17 — Enterprise app scale (ADR-024 / `.ai/specs/enterprise-app-scale/`)

- [x] **P1** Registry schema + env mapping, validate/import-taac, spec cache, catalog-from-cache (no boot network), local fixtures
- [x] **P2** `LoanOps.ApiIndex`: unified operations, resolver, capability bind → `public_id`, mismatch report, `/ready` catalog_health
- [x] **P3** Vector index + keyword index + two-stage `ApiSearchService` (`API_INDEX__ENABLED`); refresh CLI; provider_contracts any-of filter
- [x] **P4** `CredentialBroker` (`get_credential_broker` 14th `get_*`); per-app invoke, origin bind, audit `sse.live_read` (live JWT smoke skipped — see logs.md)
- [x] **P5** Per-app health, metrics, optional scheduler, scale fixture + `-m scale` suite
- [x] **P6** Docs: TASKS, logs, ARCHITECTURE, AGENTS, CONTEXT, decisions; `graphify update .`
- [ ] Operator follow-up: live SC-006 smoke with per-app `APP_TOKEN_*` when tokens available
- [ ] Enable `API_INDEX__ENABLED=true` in shared envs after index build; non-static broker when OQ-1 decided


- [x] Layers 7-9 EvalStore/Langfuse (ADR-032) — L7 robustness, L8 ops, L9 governance (2026-10-29)
- [x] Eval Improvement Platform Phase 1 — AgentTrace + taxonomy + `/eval/*` APIs + AgentCore spans + L6/retrieval skeleton + thin portal + eval-gate CI (2026-11-03)
- [ ] Eval Improvement Platform Phase 2 — native Trace Explorer, Signal Inbox, multi-reviewer, ImprovementCycle UI

