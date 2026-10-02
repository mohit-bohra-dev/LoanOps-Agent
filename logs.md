## [2026-10-02] — uv workspace split (ADR-020)

**Session type:** Architecture / refactor

**Completed:**
- Broke import cycles: `LoanOps.Tools` owns modular/MCP tools factories;
  EAKG `capability_block` injected into SSE search (no sse→eakg import).
- Moved packages into `projects/LoanOps.X/` with per-project `pyproject.toml`.
- Root becomes uv workspace solution; hatchling `force-include` keeps
  `packages.*` / `apps.agent_api` imports.
- `scripts/check_project_refs.py` + pytest + pre-commit ProjectReference gate.
- Docs: ADR-020, AGENTS/CONTEXT/ARCHITECTURE layout.
- Verify: `uv sync`; pytest **200 passed** (1 pre-existing Qdrant fail);
  MCP `getLoanSummary` 200; `/health` 200.

**Reason:** csproj-style project boundaries with explicit loanops-* refs.

---

## [2026-09-30] — Phase 9 semantic capability retrieval

**Session type:** Feature

**Completed:**
- `CAPABILITY_KG__SEMANTIC` (default false).
- `packages/capability_kg/embed_index.py` — JSON sidecar + cosine.
- `CapabilityCatalog.search_capabilities` semantic blend; keyword fallback.
- `build.py --embed` optional (live embedder).
- Tests: stub embedder ranks `payment history` → `get_payment_schedules`.

**Reason:** Natural-language intent beyond SPARQL CONTAINS without new MCP tools or Qdrant.

---

## [2026-09-30] — Phase status file + Phase 9 plan

**Session type:** Docs

**Completed:**
- `docs/PHASE_STATUS.md` — done / partial / pending phases.
- `docs/PHASE_9_SEMANTIC_RETRIEVAL.md` — hybrid embed + SPARQL plan (not implemented).

**Reason:** Persist phase tracker and lock Phase 9 design before coding.

---

## [2026-09-30] — ADR-014 RDF Capability KG + Phase 1 baseline refresh

**Session type:** MCP + Capability KG (Phases 1–3)

**Completed:**
- Phase 1: refreshed `docs/MCP_BASELINE.md` (live/MCP hop HTTP 200); `docs/MCP_ARD_PHASE_MATRIX.md`.
- ADR-014: RDFLib + Turtle + SPARQL; settings `CAPABILITY_KG__*`.
- `packages/capability_kg`: OpenAPI extract, SPARQL helpers, `CapabilityCatalog`, build CLI.
- Seed `data/capability_kg/capabilities.ttl` from Loan Services catalog.
- `search_sse_apis` optional RDF block when enabled (keyword OpenAPI fallback).
- Docs: CAPABILITY_*, MCP_IMPLEMENTATION/SECURITY/CLIENT_INTEGRATION, ARD_INTEGRATION.

**Reason:** Evolve toward enterprise capability platform without replacing SSE execution or Graphify.

---

## [2026-09-30] — ADR-013 Agent MCP client flag

**Session type:** MCP phase 4 (Architecture Phase 4)

**Completed:**
- ADR-013. `TOOLS_CLIENT__PROVIDER=modular|mcp` (default modular).
- `packages/common/mcp_tools_client.py`: Streamable HTTP session → LoanOps MCP listener.
- Factory builds MCP client from existing `MCP__*` settings; empty token raises.
- Tests: fake session + agent turn tool hop via `McpToolsClient`.
- Sidebar `/mcp/tools` and server-side execution still in-process `ModularToolsClient`.

**Reason:** Insert MCP hop for agent tool calls with factory rollback. Live compare / eval still blocked by SSO + SSE 401 baseline gaps.

---

## [2026-09-30] — ADR-011 Streamable HTTP MCP server

**Session type:** MCP phase 1

**Completed:**
- ADR-011. Settings `MCP__HOST`, `MCP__PORT`, `MCP__AUTH_TOKEN`, `MCP__ROLE`, `MCP__PATH`.
- `packages/mcp_server`: FastMCP Streamable HTTP, bearer required, scope + GET-only `call_sse_api`, audit `mcp.tool.call`.
- Tools still execute through `ModularToolsClient`. Agent `/chat` path unchanged.
- Chunker no longer loops when overlap is wider than the target window.

**Reason:** Remote MCP clients need the protocol. The existing `/mcp/tools` routes stay a custom JSON API.

---

## [2026-09-29] — ADR-010 One modular Python product

**Session type:** Architecture / module scaffold

**Completed:**
- ADR-010: Python-only backend, provider_contracts, duplicate keep/remove table.
- provider_contracts: `BedrockEmbeddingProvider`, session_store ABC + memory/mock/postgres.
- LoanOps modules: `packages/sse`, `packages/db`, `packages/docs`, `packages/wiki`.
- ModularToolsClient + scopes; Agent API `/mcp/tools`, `/mcp/keys`.
- Settings: `SSE__*`, `SQL_SERVER__*`, session postgres, vector pgvector, tools=modular.
- Docs: `docs/RETIRE_STANDALONE.md`. SQL driver = aioodbc + ODBC 18.
- Embedding: local bge-small; AWS Titan embed v2 1024-dim.

**Reason:** Single product for users/agents querying SSE APIs + docs; retire Node gateway and standalone wiki after parity.

---

## [2026-07-24] — Independent DATA__LOAN_SOURCE / DATA__SOP_SOURCE

**Session type:** Config / provider wiring

**Completed:**
- Split loan vs SOP selection: `DATA__LOAN_SOURCE`, `DATA__SOP_SOURCE`,
  `DATA__SOP_CONFLUENCE_MODE` (cache|live).
- Factory wires Confluence-only via `_confluence` cache or live API.
- Deprecated `DATA__MODE` with backcompat mapping; ADR-009.
- `.env` demo mix: mock fixtures + Confluence-only cache.

**Reason:** Use ingested Confluence SOPs without synthetic local SOPs while
keeping loan fixtures offline.

---

## [2026-07-21] — Live Confluence SOP ingest (Escrow + Hardship)

**Session type:** Feature implementation

**Completed:**
- Implemented `ConfluencePolicyProvider` (REST v2, markitdown HTML→md, regex/presidio scrub, local artifact write).
- Added `CompositePolicyProvider`; `DATA__MODE=real` = local dummy SOPs + Confluence (add, not replace).
- Extended `ConfluenceConfig` with `page_ids`, `ancestor_ids`, `expand_children`, `pii_scrub`, `artifact_dir`.
- `LocalFilePolicyProvider` skips `_`-prefixed dirs so Confluence cache is not double-ingested.
- Gitignored `data/sops/_confluence/`; documented seed page IDs in `.env.example`.
- Unit tests for skip/composite/scrub; ADR-008.

**Reason:** Feed curated real SC-space Escrow/Hardship SOPs into RAG without committing confidential content or breaking offline `make demo`.

---

## [2026-06-21] — Langfuse Telemetry Integration

**Session type:** Feature implementation

**Completed:**
- Created `LangfuseTelemetryProvider` in `provider-contracts` using official Langfuse Python SDK.
- Wired provider into `factory.py` with `TELEMETRY__PROVIDER=langfuse`.
- Added configuration to `settings.py` (keys, host, optional).
- Updated eval harness (`run.py`) to push custom scores (citation coverage, refusal correctness, latency) to Langfuse.
- Added `docker-compose.langfuse.yml` for local self-hosting.
- Fixed 6 review issues (imports, lazy load, test mock, dummy traces, etc.).

**Reason:** Needed a dedicated eval UI/dashboard for OTel traces and metrics, per approved implementation plan.

---

## [2026-06-18] — Fix EscrowBalance Field Collision
**Session type:** Bug fix

**Completed:**
- Renamed `current_balance_usd` to `escrow_balance_usd` inside the `EscrowBreakdown` schema (`packages/common/schemas.py`).
- Updated `apps/tools_api/main.py` to use `escrow_balance_usd` in all `get_escrow_breakdown` tool return paths.
- Updated the testing mock data (`packages/agent_core/tests/conftest.py`) and documentation (`docs/01-servicing-agent-prompts.md`) to reflect the new `escrow_balance_usd` key.
- Kept `LoanSummary.current_balance_usd` intact, ensuring principal loan balance remains accurately represented.

**Reason:** The LLM was hallucinating because the `EscrowBreakdown` and `LoanSummary` schemas previously shared the exact same field name (`current_balance_usd`). The agent mistakenly used the $0.00 escrow account balance as the principal loan balance when answering queries. Disambiguating the field name prevents this collision.

---

## [2026-06-18] — Bedrock API Key Auth & PII Stub Fixes

**Session type:** Bug fix

**Completed:**
- Added a `stub` mode for the `PiiProvider` (`MockPiiProvider`) via `settings.py` and `factory.py` to fix slow local startup times caused by Presidio/spaCy loading.
- Fixed Bedrock's `Converse` API integration returning blank responses by mapping non-compliant roles (`tool`, `function`) to `user` and throwing explicit errors if the `messages` array is empty.
- Fixed Bedrock API key authentication (bearer token mode) by properly setting `os.environ["AWS_BEARER_TOKEN_BEDROCK"]` and using `bedrock-runtime.{region}` instead of forcing it through `aws_session_token`.
- Added verbose `logging` to `BedrockProvider.chat()` for easier diagnostics.

**Reason:** Agent API took 10-15s to start, and Bedrock was returning silent blanks due to malformed payload roles and incorrect AWS IAM header injection.

---

## [2026-06-10] — Conversational Memory Feature

**Session type:** Feature implementation

**Completed:**
- Added `SessionStoreProvider` and `InMemorySessionStoreProvider` to `provider_contracts` and `packages/common/providers`.
- Implemented sliding window memory strategy in `packages/agent_core/_memory.py`.
- Integrated memory state into `/chat` API loop using the session store.
- Updated `ChatPane.tsx` to handle dynamic session IDs, pass active `loan_id`, and added a "New Chat" button.
- Lifted `activeLoanId` state in `App.tsx` and updated `BorrowerContextPane.tsx` to invoke `onLoanLoaded`.
- Created tests for memory logic (`test_memory.py`) and contracts (`test_contract.py`). All tests pass.

**Reason:** Added conversational memory capabilities with context expiration per the newly approved implementation plan.

---

## [2026-06-09] — Graphify-first rule added to all agent instructions

**Session type:** Tooling / agent workflow

**Completed:**
- Added `§Knowledge graph (Graphify) — mandatory` section to both `AGENTS.md` and `GEMINI.md`
- Added `Graphify-first` as the first non-negotiable rule in both files
- Added `graphify-out/graph.json` to the Read order table
- Updated "Build a step" workflow: step 2 now runs `graphify query`, step 6 runs `graphify update .`
- Coverage: Cursor (`.cursor/rules/graphify.mdc`), Gemini (`GEMINI.md`), Copilot/others (`AGENTS.md`)

**Reason:** Graphify graph existed but only the Cursor `.mdc` rule referenced it. Other agentic IDEs (Gemini, Copilot, Windsurf) had no instruction to use the knowledge graph, leading to redundant grep/file-reads.

---

## [2026-06-09] — Fix Safety Middleware Showstopper

**Session type:** Bug fix / Implementation

**Completed:**
- Wired up `SafetyPipeline.sanitize_inbound` to the `/chat` endpoint in `apps/agent_api/main.py`.
- Wired up `SafetyPipeline.evaluate_outbound` to the agent response.
- Removed Step 7 TODO from `apps/agent_api/models.py`.
- Updated test mocks in `apps/agent_api/tests/test_agent_api.py` to properly mock async middleware calls.
- Reviewed conversation memory architecture plan.

**Reason:** PII was going unredacted into the audit log and the `run_agent_turn` function. Outbound safety checks were also skipped.

---

## [2026-06-08] — Fix mypy test monkeypatch signatures

**Session type:** Bug fix

**Completed:**
- Fixed `packages/agent_core/tests/test_agent_core.py` patch signatures for `patched_chat`, `failing_then_valid`, `always_fails`
- Updated signatures to include `self`, `json_mode: bool`, and return `LLMResponse`
- Used `MethodType` to bind local async functions to `MockLLMProvider`
- Updated `# type: ignore[assignment]` → `# type: ignore[method-assign]`
- Verified `make lint` now passes (ruff + mypy)

**Reason:** Mypy error caused by incompatible callable shape (missing `self` + missing `json_mode`).

---

## [2026-09-29] — Docs sync: tools_api retired

Updated ARCHITECTURE, PRD, ANALYSIS, CONTEXT, demo/query docs, and STEP 4 in
`docs/01-servicing-agent-prompts.md` to match SSE-only runtime (ADR-010).

---

## [2026-09-29] — Remove tools_api; SSE-only answer path

**Session type:** Cleanup / architecture follow-through (ADR-010)

**Completed:**
- Deleted `apps/tools_api` (mock HTTP :8001)
- `TOOLS_CLIENT__PROVIDER=modular` only; dropped `TOOLS_API_TOKEN` / http tools client
- Removed helix `lookup_loan` scopes; system/care_rep = SSE + docs
- Web UI: Vite `/tools` proxy gone; `lookupLoan` → Agent MCP `call_sse_api`
- Docs: README, AGENTS, CONTEXT, RETIRE_STANDALONE, decisions ADR-010 note

**Next:** Optional commit/push; more `SSE__SWAGGER_LINKS` apps.

---

## [2026-05-31] — Tooling: Graphify knowledge graph

**Session type:** Tooling / developer experience

**Completed:**
- Installed Graphify CLI globally via `uv tool install graphifyy --with openai`
- Registered project-scoped Cursor skill (`graphify cursor install --project`) → `.cursor/rules/graphify.mdc` (`alwaysApply: true`)
- Added `.graphifyignore` (excludes `.venv/`, `node_modules/`, `.env`, `graphify-out/`, etc.)
- Built initial graph: 83 code files + 62 docs → `graphify-out/graph.json`
- Installed git post-commit / post-checkout hooks for auto-rebuild (AST-only, no API cost)
- `.gitignore`: ignore local-only `graphify-out/manifest.json`, `cost.json`, `cache/`
- Docs: added `GRAPHIFY_SETUP.md`; added §19 to `CONTEXT.md`
- Verified `graphify query "..."` returns scoped subgraphs

**Note:** Backend defaults to `gemini`; semantic extraction of docs/PDFs needs an API key for headless `graphify extract`. Code extraction is local (tree-sitter, no API calls).

**Next:** Step 8 eval harness is marked done in `TASKS.md`; remaining work is Step 10 (IaC + CI) and the Step 1.5 CI grep gate for concrete imports.

---

## [2026-05-28] — Step 7: Safety layer implemented

**Session type:** Implementation

**Completed:**
- Middleware: PII anonymize inbound, safety evaluate outbound
- Tests: redaction + blocking pass against both provider configs

**Next:** Step 8 — Eval harness. FastAPI :8000, `POST /chat` (SSE), `GET /health`, `GET /version`.

## [2026-10-02] - Enterprise Application Knowledge Graph (EAKG) pilot

**Session type:** Feature

**Completed:**
- ADR-015..019 (ontology v2+provenance, registry, sharded store, static .NET extract, EAKG__* settings).
- `packages/eakg/` pipeline: registry, TAAC ingest, .NET extractor, hybrid OpenAPI, 8 detectors, semantic proposals, review CLI, sync repo/nightly/audit.
- Seed registry for escrow/fees/loanservices; redacted TAAC fixture.
- MCP tools: `search_capabilities`, `explain_capability`, `find_providers`, `impact_of_change`.
- Tests: 10/10 green on synthetic fixtures proving pilot cross-app edges + repo #4 registry-only onboard.

**Reason:** Scalable multi-repo capability graph with evidence; LLM proposes semantics only.


## [2026-10-02] - Real pilot KG via glab

**Session type:** Ops

**Completed:**
- `packages/eakg/gitops.py` now uses **glab only** for access (`api projects`), clone (`repo clone`), remote HEAD (`api branches`).
- Cloned Escrow/Fees/LoanServices into `.eakg-workspace/` (glab/SSH).
- Ingested live TAAC via `glab api` → enterprise applications.ttl (744 triples).
- Extracted real shards: escrow 482 ops, fees 236 ops, loanservices 174 ops.
- Cross-app: 243 relationships (0 dropped); approved catalog 250 triples.

**Reason:** User required glab for all GitLab access; finish pilot graph build.

## [2026-10-02] - EAKG point 1: review + GetLoanSummary + SSE shards

**Session type:** Feature

**Completed:**
- `review --pilot`: approved 141 high-value edges; rejected 69 noisy `callsOperation`; republished `catalog/approved.ttl` (1523 triples).
- Re-extracted loanservices (174→229 ops) after 1200-char Http*→method window; `GetLoanSummary` now in graph.
- Query ranking fix (camelCase tokens; reject short oid substring); CLI `query search|find|explain|impact`.
- `search_sse_apis` uses `catalog_from_shards` when CAPABILITY_KG enabled + EAKG repos present.
- Tests: 10/10 `packages/eakg/tests` green.

**Reason:** Point-1 pilot cleanup so agent discovery sees real ops + curated cross-app edges.

## [2026-10-02] - EAKG points 3–5 + Phase 8 slice

**Session type:** Ops + Feature + Docs

**Completed:**
- Point 3: `docs/EAKG_INDEX_SCHEDULE.md`, `ci/eakg.gitlab-ci.yml`, `scripts/eakg/` (sync-repo/nightly/audit, refresh-taac, install-scheduled-tasks).
- Point 4: Phase 8 — principal headers on `call_sse_api`; EAKG tools via `execute_tool` scopes+audit; `approved_only` → approved.ttl. Checklists `MCP_CURSOR_VALIDATION.md`, `MCP_GEMINI_VALIDATION.md`; ARD draft `ARD_RESOURCE_CHOICE.md`.
- Point 5: `EAKG_SWAGGER_EXPORT.md`, `EAKG_EXTRACTOR_UPGRADE.md` (deferred), `EAKG_ONBOARD_REPO.md` (registry #N).
- Tests: mcp_server + eakg + mcp factory green.

**Reason:** Schedule ops, harden MCP principal/EAKG gates, and leave analyzer/live repo#4 as explicit later work.

## [2026-10-02] - Mold agent as MCP consumer

**Session type:** Docs / ADR

**Completed:**
- ADR-013 product-shape note: `/chat` = first-party MCP consumer; `modular` = demo/rollback only.
- `docs/MCP_CLIENT_INTEGRATION.md` + `PHASE_STATUS` preserve + `TASKS` focus updated.

**Reason:** User rejected D1-B as standalone chat path; want agent molded as MCP client same as Cursor/Gemini.

## [2026-10-02] - Cleanup C1–C6

**Session type:** Hygiene

**Completed:**
- C1: deleted `graphify-out/2026-10-02/`; gitignore `graphify-out/20*/`
- C2: verified only `data/eakg/registry` + `fixtures` tracked; shards/workspace ignored
- C3–C6: TASKS backlog buckets; PHASE_STATUS north star refresh; `docs/EAKG_COMMITTED_VS_LOCAL.md`

**Reason:** Decide/clean before next MCP-platform work.

## [2026-10-02] - Decide/Cleanup board doc

**Session type:** Docs

**Completed:**
- `docs/DECIDE_AND_CLEANUP.md` — all D1–D10 and C1–C6 with plain-English meaning + status.
- Linked from TASKS + PHASE_STATUS.

**Reason:** User asked for one place explaining D/C items and status.

## [2026-10-02] - D2: CAPABILITY_KG enabled by default

**Session type:** Config

**Completed:**
- `CapabilityKgConfig.enabled` default `True`; `.env.example` / CONTEXT / DECIDE board updated.
- Still toggle anytime: `CAPABILITY_KG__ENABLED=false`.

**Reason:** User chose D2=true with env override.

## [2026-10-02] - D4: EAKG is source of truth

**Session type:** Decision

**Completed:**
- Locked D4 on decide board; ADR-014 amendment; `EAKG_COMMITTED_VS_LOCAL` marks shards as truth, single TTL as fallback only.

**Reason:** User: treat EAKG as truth.

## [2026-10-02] - D4: remove single-TTL discovery fallback

**Session type:** Cleanup

**Completed:**
- `search_sse_apis` EAKG-only; deleted `data/capability_kg/capabilities.ttl`; README in place.
- Tests + decide board / ADR / CONTEXT updated.

**Reason:** User: delete fallback.

## [2026-10-02] - Stack layer decisions board

**Session type:** Docs / ADR

**Completed:**
- `docs/STACK_LAYER_DECISIONS.md` — full layer matrix with today vs target.
- ADR-018 amended: Roslyn primary, regex interim; D5 + extractor upgrade doc aligned.

**Reason:** User supplied stack recommendation table (Roslyn/OpenAPI/RDF/MCP primary).

## [2026-10-02] - D5 Roslyn extractor upgrade

**Session type:** Feature

**Completed:**
- `tools/eakg-dotnet-extract` Roslyn syntax-tree CLI; Python `extractors/roslyn.py`.
- `EAKG__EXTRACTOR=auto|roslyn|regex` (default auto); regex fallback.
- Tests + ADR-018 / D5 / stack docs updated.

**Reason:** D5 upgrade — Roslyn primary for controller ops.

## [2026-10-02] - D6 freeze at three pilot repos

**Session type:** Decision

**Completed:** Locked D6 — Escrow/Fees/LoanServices enough; no repo #4 for now.

**Reason:** User: 3 enough for now.

## [2026-10-02] - D7 OBO target; M2M from SubservicingClient

**Session type:** Decision

**Completed:**
- Locked D7 = OBO direction.
- Clarified: SubservicingClient Auth0 M2M (`IJwtRetriever` / client_credentials) is usable as **service** Bearer for SSE (same class as `SSE__API_KEY`), not true end-user OBO. User session tokens in that app are a separate path for later OBO.

**Reason:** User chose OBO and asked about subservicingclient M2M.

## [2026-10-02] - D7 simplest auth for now

**Session type:** Decision

**Completed:**
- Re-locked D7: keep `SSE__API_KEY` + `x-loanops-user`/`x-loanops-tenant`. No M2M provider, login, OBO, or RBAC this phase.
- Deferred ladder: M2M → user OBO → RBAC later.
- Updated `docs/DECIDE_AND_CLEANUP.md`, `TASKS.md`.

**Reason:** User: keep simplest for now; improve later (probably RBAC).

## [2026-10-02] - D8 both CLI and Web UI

**Session type:** Decision

**Completed:**
- Locked D8 = **both**: CLI (`review --pilot`) now; Web UI in scope (same review model).
- Updated `docs/DECIDE_AND_CLEANUP.md`, `TASKS.md`, `STACK_LAYER_DECISIONS.md`, `MCP_ARD_PHASE_MATRIX.md`.

**Reason:** User: d8 both.

## [2026-10-02] - D9 push deferred

**Session type:** Decision

**Completed:**
- D9 = not yet. Test everything first; push `vdd` when green.
- Updated `docs/DECIDE_AND_CLEANUP.md`, `TASKS.md`.

**Reason:** User: D9 not yet, will test everything then.

## [2026-10-02] - D10 local first; cloud later

**Session type:** Decision

**Completed:**
- Locked D10: re-index everything local (manual / Task Scheduler). Cloud GitLab CI schedules only after local tested.
- All D rows decided (D9 deferred). Updated `docs/DECIDE_AND_CLEANUP.md`, `TASKS.md`, `docs/EAKG_INDEX_SCHEDULE.md`.

**Reason:** User: D10 everything local; once tested on cloud.

## [2026-10-02] - D10 manual only (no schedulers)

**Session type:** Decision

**Completed:**
- Tightened D10: manual CLI only. No Windows Task Scheduler, no cloud GitLab schedules.
- Updated `docs/DECIDE_AND_CLEANUP.md`, `TASKS.md`, `docs/EAKG_INDEX_SCHEDULE.md`.

**Reason:** User: no local task scheduler; manual only for everything.

## [2026-10-02] - D7 Subservicing M2M as SSE bearer

**Session type:** Decision

**Completed:**
- D7: `SSE__API_KEY` = SubservicingClient Auth0 M2M (shared audience `https://pennymac`) so one token reaches all Plaisse APIs.
- Still paste/process-wide; no auto-fetch / OBO / RBAC yet.
- Updated `docs/DECIDE_AND_CLEANUP.md`, `TASKS.md`, `.env.example`, `docs/MCP_SECURITY.md`.

**Reason:** User: use subservices M2M; it can access all.

## [2026-10-02] - Minted Subservicing M2M into SSE__API_KEY

**Session type:** Ops / wiring

**Completed:**
- Minted Auth0 M2M (`client_credentials`, audience `https://pennymac`) from SubservicingClient user-secrets.
- Wrote `SSE__API_KEY` in local `.env`. Probe Loan Services Summary → HTTP 200.
- Added `scripts/auth/refresh-sse-m2m.ps1` for manual re-mint. Updated `.env.example`.

**Reason:** User: You do it.

## [2026-10-02] - Demo path up: MCP + M2M live Summary

**Session type:** Ops / validation

**Completed:**
- Restarted `packages.mcp_server` `:8001` + Agent API `:8000` with fresh M2M `SSE__API_KEY`.
- MCP hop `list_tools` OK (8 tools incl. EAKG).
- MCP hop `call_sse_api` `getLoanSummary` loan `1000002245` → **HTTP 200**.
- Agent `/health` → 200.
- Marked product demo path done in `TASKS.md`.

**Reason:** User: Go ahead.

## [2026-10-02] - Cursor MCP validation (Phase 11)

**Session type:** Validation

**Completed:**
- Wired `loanops` into `~/.cursor/mcp.json` → Cursor namespace `user-loanops`.
- Fixed `packages/mcp_server/policy.py` `_READ_ONLY_TOOLS` to include EAKG tools (were listed but denied).
- Cursor MCP smokes: P1–P6 + N2 via `user-loanops`; N1 via Streamable HTTP bad bearer.
- Evidence: `docs/MCP_CURSOR_VALIDATION.md`. Updated `PHASE_STATUS.md`, `TASKS.md`.
- MCP tests: 7 passed.

**Reason:** User: Test on cursor.

## [2026-10-02] - Single ARCHITECTURE.md; delete duplicates

**Session type:** Docs cleanup

**Completed:**
- Consolidated architecture into root `ARCHITECTURE.md` (from `docs/CURRENT_ARCHITECTURE.md` + north-star refresh).
- Deleted `docs/CURRENT_ARCHITECTURE.md`, `Cursor_LoanOps_vdd_Architecture_Analysis.md`.
- Retargeted refs in AGENTS, CONTEXT, README, PRD, MCP_BASELINE, prompts brief.
- Kept `presentations/demo-pitch/architecture.md` as slide one-pager → points at `ARCHITECTURE.md`.

**Reason:** User: Create one file for Architecture delete others.

## [2026-10-02] - docs/FLOWS.md all application flows

**Session type:** Docs

**Completed:**
- Added `docs/FLOWS.md` — flows F1–F25 (chat MCP/modular, intent, safety, UI sidebar, MCP protocol, SSE, EAKG, ops).
- Linked from `ARCHITECTURE.md`, `CONTEXT.md`.

**Reason:** User: Create every flow possible for this Application in md file.

