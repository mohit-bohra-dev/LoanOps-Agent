## [2026-11-10] — Pipeline control plane Phase 1 PoC (ADR-033)

**Session type:** Implementation

**Completed:**
- ADR-033: FastAPI + Postgres/file run ledger; Step Functions later; Dagster optional
- `eakg_pipeline_runs` + artifact store put/get/list; ApiIndex manifest via `eakg_kv` in Postgres mode
- New `loanops-pipelines`: catalog (`openapi_to_api_index`), create/dispatch_local/execute, CLI
- Agent API `/pipelines/*`; Eval Portal Pipelines tab; tests green; mypy `--strict` clean

**Risk:** `/pipelines` POST unauthenticated (same as `/eval/*`); stuck `running` if child killed.

**Next:** Phase 2 Step Functions launcher behind provider; remaining six pipelines; auth scopes.

---

## [2026-11-10] — Make search_sse_apis cheap

**Session type:** Performance (latency)

**Completed:**
- Diagnosed turn latency from agent traces: `search_sse_apis` 2.1–6.7s (SLO p95 1.5s) — waste was per-call `embed("probe")`, serial KG+OpenAPI, and N+1 SPARQL `explain_capability`
- `ApiSearchService`: derive live model id / mismatch / namespace from first successful query embed; no separate `embed("probe")`; transient embed fail does not set `_model_probed`
- `eakg/query.py`: full Capability→op SPARQL projection; drop N+1 `explain_capability` from `_search_capability_rows`; 60s TTL cache for ops + caps dumps
- `handle_search_sse_apis`: `asyncio.gather` capability_block ∥ api_search; skip unused `service.load()` on ApiIndex path; isolate KG errors
- Tests: embed-once / no-probe, transient recovery, no-explain + dump cache, parallel wall-time; related suites green; mypy `--strict` clean on touched modules

**Risk:** Warm path still needs `API_INDEX__ENABLED` + healthy vector index; first call still pays one query embed + one SPARQL dump fill.

**Next:** Optional search-result string LRU; measure warm `search_sse_apis` on live stack vs 1.5s SLO.

---

## [2026-11-03] — Eval Improvement Platform Phase 1

**Session type:** Implementation (spec Phase 1)

**Completed:**
- Spec package already authored; Phase 1 code: `AgentTrace` + taxonomy, AgentCore `agent.turn`/`mcp.tool.call` spans + `trace_id` on `AgentTurnOutput`
- APIs: `POST /eval/feedback`, `GET /eval/traces/{id}`, `GET /eval/health`, `POST /eval/promote`
- Promote accepts fail→draft candidates; L6 skeleton + retrieval stage harness; `eval-gate.yml`; thin Eval Portal UI
- Tests: taxonomy + eval routes + agent_core green (34 focused)

**Risk:** L6 is skeleton (not full injection corpus). Portal is thin (no native timeline yet).

**Next:** Phase 2 Signal Inbox + native Trace Explorer; expand L6 cases.

---

## [2026-10-20] — DB-only pipeline storage + file-mode mirrors

**Session type:** Storage cutover

**Completed:**
- Product: GraphDB + Postgres + pgvector (`EAKG_STORE__BACKEND=postgres`); no S3; no repo product truth
- File mode: `data/pipeline_store/{GraphDb,Postgres,Pgvector}/` layout; `FileEakgArtifactStore` under `Postgres/`
- Schema: embeddings, proposals, decisions, engineering, graphrag, kv, sop_page_cache
- SOP ingest: live Confluence → pgvector; file cache under `Postgres/sop_page_cache`
- Docs: PIPELINES, EAKG_COMMITTED, CONTEXT, ADR-027 amendment; `.env.example` product defaults

**Risk:** Local `.env` with `BACKEND=postgres` needs live DBs; GraphRAG/Docs now depend on `loanops-eakg`.

**Next:** migrate any leftover disk shards; verify onboard against GraphDB+Postgres.

---

## [2026-10-20] — Drop synthetic SOPs; Confluence-only corpus

**Session type:** Cleanup

**Completed:**
- Deleted synthetic category trees under `data/sops/` (escrow, payments, …); kept `_confluence`
- Defaults: ingest / docs_root / GraphRAG corpus → `data/sops/_confluence`
- `DocsService.index_directory` skips `_` dirs relative to corpus root (so `_confluence` as root still indexes)
- README under `data/sops/`; CONTEXT + PIPELINES updated

**Risk:** `data/golden.jsonl` still cites old synthetic paths — re-align citations after Confluence paths stabilize. GraphRAG artifact may need rebuild.

**Next:** re-ingest + optional GraphRAG rebuild from `_confluence`.

---

## [2026-10-20] — Pipelines source→output doc

**Session type:** Docs

**Completed:**
- Added [`docs/PIPELINES.md`](docs/PIPELINES.md) — product batch jobs + Graphify (dev-only)
- Data→knowledge transform table (Code/OpenAPI/SOP paths); commands removed (ops how-to elsewhere)
- Per-pipeline source→output examples; Engineering KG called out
- Linked from CONTEXT.md

**Next:** none.

---

## [2026-10-20] — Drop same-purpose pipeline duplicates

**Session type:** Cleanup

**Completed:**
- Removed `packages.capability_kg.build` / `__main__` and `CAPABILITY_KG__TTL_PATH` (D4 EAKG-only; shared library kept)
- SOP ingest: `DocsService.index_directory` is the only writer; `packages.rag.ingest` → subprocess `packages.docs.ingest`
- Removed `packages.sse.embed_openapi`; sidecar rebuild = `python -m packages.api_index.refresh all --sidecar-only`
- Docs: ARCHITECTURE §11, CONTEXT, decisions ADR-014/023, DECIDE D4, PHASE_9, EAKG_COMMITTED_VS_LOCAL, `.env.example`

**Next:** none for this cut.

---

## [2026-10-16] — MCP observability (self-hosted Langfuse)

**Session type:** Implementation

**Completed:**
- `execute_tool`: span `mcp.tool.call` + metrics `mcp.tool.latency_ms` / `mcp.tool.outcome` via TelemetryProvider (injectable; fail-open)
- In-code MCP fixture eval: `python -m packages.mcp_server.eval_run` → `eval.mcp.*` scores only (no report file)
- Local Langfuse: shared Postgres DB `langfuse` (same server as `loanops`); **native self-host, no Docker required**; compose file optional only
- Docs: ARCHITECTURE §14, CONTEXT, TASKS, `.env.example`
- MockTelemetry `recorded_spans` for assertions

**Next:** Native Langfuse against local Postgres; agent MCP-hop golden still SSO-gated.

---

## [2026-10-16] — Eval golden MCP refresh (remove stale)

**Session type:** Maintenance

**Completed:**
- `data/golden.jsonl`: all 50 items `must_call_tools` / `tool:` cites → MCP (`search_sse_apis`, `call_sse_api`, `search_docs`)
- `validate_data` allowlist drops legacy tools; DATA_DIR resolves repo-root `data/`
- CONTEXT/TASKS: Eval DONE, phantom `eval-gate.yml` claims removed; golden refresh checked off
- Eval unit tests: 34 passed

**Next:** Live `make eval` with MCP + Bedrock SSO; add real `.github/workflows/eval-gate.yml` when ready.

---

## [2026-10-16] — Provider contracts lockstep + agent_runtime (LangGraph)

**Session type:** Implementation

**Completed:**
- `provider_contracts`: `graph_store/`, `credential_broker/`, `reranker/mock.py`, `agent_runtime/` (langgraph/native/mock) + contract tests
- LoanOps.Common re-exports + `get_agent_runtime_provider()`; `AGENT_RUNTIME__PROVIDER`; ADR-031 (supersedes ADR-001)
- `LoanOps.AgentCore` uses `AgentRuntimeProvider.run()`; dropped unused `agent-framework`
- Domain packages: no direct `provider_contracts` imports; policy_source uses `get_pii_provider()`
- Gates: lockstep rule, `check_project_refs` allowlist, `test_provider_boundaries.py`
- Tests: PC agent/graph/cred 9 passed; AgentCore+boundaries 44; Tools 14; check_project_refs OK

**Next:** Wire AgentApi SSE to `stream_events`; optional Postgres checkpointer; migrate `investigate_agent` loop later.

---

## [2026-10-15] — Doc GraphRAG P5 LLM extract


**Session type:** Implementation

**Completed (P5):**
- Extract pipeline: cache key (content|model|prompt|schema), grounding filter, PII scrub + state/vocab allowlist, gap-ledger shape (no eakg import)
- `graph.json` + `gap_ledger.json` + richer `manifest.json`; Confluence/`--write-repo-artifact` refuse; `--rebuild` model pin
- CLI: `uv run python -m packages.graph_rag.build --extract`
- Unit tests: cache, grounding, PII, refuse, cache-hit (12 GraphRag tests green)

**Next:** Run `--extract` on local corpus when ready (Bedrock cost); P6 ADR-030 append on human approval; gate2 still deferred.

---

## [2026-10-15] — Doc GraphRAG P4 summary routing (golden deferred)

**Session type:** Implementation

**Completed (P4):**
- New `projects/LoanOps.GraphRag` (`loanops-graphrag`): Louvain communities (seed=42), extractive summaries, `GraphRagService` wrap, artifact load/fallback
- Settings: `GRAPHRAG__ENABLED` (default false), `GRAPHRAG__ARTIFACT_DIR=data/graphrag`
- Factory injects wrap when enabled; build CLI `python -m packages.graph_rag.build`
- Unit tests: route, Louvain determinism, degraded/global search
- Owner skipped golden/gate2; ADR-030 still draft

**Next:** `uv run python -m packages.graph_rag.build`; set `GRAPHRAG__ENABLED=true`; gate2 when ready; P5 only if gate2 warrants.

---

## [2026-10-15] — Doc GraphRAG P1–P3 implementation + kill-gate STOP

**Session type:** Implementation

**Completed (P1):**
- `ground_citations` + live `_TOOL_NAMES` (`search_docs` not mangled to `policy:`)
- `citation_groundedness` metric + threshold 1.0; faithfulness contexts from tool results
- Path-normalised frozen chunk metadata; `ingest_sops` → `docs` namespace
- Golden: `search_policy`→`search_docs` (34); `data/golden_global.jsonl` (22 items)

**Completed (P3):**
- DocsService reranker (`candidate_k=20`) + `DocLinkGraph` one-hop; `data/docs/doc_links.json`
- Factory wires optional reranker + links file
- Unit tests: citation grounding, path meta, link graph + rerank

**P2 / kill gate:** Live eval blocked — SSO token expired. Recorded STOP: no P4+ GraphRAG until credentials refreshed and slice re-measured. ADR-025 stands meantime.

**Next:** Refresh LLM SSO; re-run `python -m packages.eval.run --golden data/golden_global.jsonl`; decide kill gate; only then P4+.

---

## [2026-10-15] — Doc GraphRAG spec package authored

**Session type:** Spec authoring

**Completed:**
- `.ai/specs/doc-graphrag/` — README, story, spec, plan (P1–P6 kill-gated)
- `ADR-030.draft.md` — pending human approval; not appended to `decisions.md`
- Architect review folded in: citation grounding + tool-context faithfulness before any GraphRAG code

**Next:** Execute plan P1 (metric approval + grounding); stop at P3 kill gate unless authorized.

---

## [2026-10-15] — ADR-029 investigator + pattern feedback (implemented)

**Session type:** Implementation

**Completed:**
- ADR-029 revised: deterministic coverage/facts; LLM investigates gap ledger only; pattern feedback via git
- Modules: `coverage`, `gap_ledger`, `candidate_gate`, `investigate_agent`, `patterns`, `pattern_backtest`, `openapi_ledger`
- `ConflictRecord` in `merge_api`; near-misses in `detectors`; onboard writes coverage + ledger
- Settings: `EAKG__INVESTIGATE_AGENT` (default off), `patterns_dir`, `investigate_max_rounds`
- CLI: `investigate`, `patterns hash|backtest`; bootstrap patterns under `data/eakg/patterns/`
- Tests: `test_adr029_investigate.py`, process rule baseline benchmark
- Docs/TASKS/schedule updated

---

## [2026-10-15] — ADR-029 LLM gap-fill structural facts

**Session type:** Decision / plan revise

**Completed:**
- Evolved through Option 3 → LLM-primary → agent-tools → design review → investigator architecture
- ADR-029 rewritten (see implementation entry above)

---

## [2026-10-15] — Multi-lang structural API extract (review fixes)

**Session type:** Implementation

**Completed:**
- Express `router.route(path).get` applies `app.use` mount prefixes; Fastify object-only `route`
- Engineering join `eakg_operation_local_name` matches RDF route-key hash URIs
- Fixture: Node legacy under `/api`; Python `APIRouter` paren typo fixed
- Zero-ops onboard fail kept (plan contract); package/proxy surface still DotNet-only
- Break merge_api ↔ treesitter_adapter circular import; lock RDF↔join + preserve-shard tests

**Migration:** Re-onboard registered apps for new op/capability IRIs (no committed shards in repo).

---

## [2026-10-15] — Multi-lang structural API extract

**Session type:** Implementation

**Completed:**
- Canonical route identity (`route_identity.py`) + multi-adapter merge (`merge_api.py`)
- RDF op/capability URIs keyed by route-key hash (re-onboard required)
- Roslyn `dotnet_roslyn` 2.1.0: Minimal APIs (`Map*`/`MapGroup`/fluent authz)
- Tree-sitter adapters: FastAPI/Flask + Express/Fastify (MIT wheels)
- Onboard runs all API adapters; Java still unsupported
- ADR-018 amended; extractor + stack docs + TASKS updated
- Tests: route identity, Minimal API fixture, Python/Node fixtures

**Migration:** Re-onboard registered apps so GraphDB named graphs pick up new op/capability IRIs.

---

## [2026-10-15] — Park SonarQube findings → EAKG graph

**Session type:** Note

**Decision:** Do not add CodeQL for taint. Every SSE pipeline already runs SonarQube. Later task in `TASKS.md`: import open vulnerabilities / hotspots as finding nodes + evidence, linked to operations by file+line. Not `callsApplication`. Needs a SonarQube provider + env var first.

---

## [2026-10-15] — ADR-028 process KG pilot (Account Maintenance)

**Session type:** Implementation

**Completed:**
- ADR-028: deterministic SOP → RDF process graph; LLM maps offline only; never authorizes
- Ontology: BusinessProcess / ProcessStep / Transition / CapabilityLink / BusinessSystem / Regulation
- Extractor + validator + GraphStore load (`process_extract` / `process_validate` / `process_graph`)
- CLI: `python -m packages.eakg process extract|validate|load|show|approve|verify-fresh|revalidate|report`
- Fixtures + maps under `data/process_kg/`; proposal `account-maintenance.proposal.json`
- Tests: 14 passed (FakeGraphStore); authz isolation; opt-in `@pytest.mark.graphdb` stub
- Pilot stays `pending_review` (no reviewer named)

---

## [2026-10-13] — CoreComponents onboard + eakg-onboard-repo skill

**Session type:** Ops + tooling

**Completed:**
- Registered/onboarded `corecomponents` (GitLab `15617`, `src/CoreComponents.Api`) — Roslyn ops, GraphDB, eng graph ~7MB, cross-app
- Dev env: `https://corecomponentsapi-plaisse-dev.pnmac.com`, `CoreComponentsApiUrl`
- `gitops.run_glab`: `GITLAB_HOST` for `repo clone` (not `--hostname` after repo)
- Skill: `.cursor/skills/eakg-onboard-repo/SKILL.md`; pointer in `docs/EAKG_ONBOARD_REPO.md`
- Exported registry → `data/eakg/registry/repositories.yaml` (4 apps)

---

## [2026-10-12] — Full eng graph sync (1C Phase A+B)

**Session type:** Implementation

**Completed:**
- Phase A: `interface_to_graph` materializes ServiceProxy / SdkPackage / EventTopic / RouteComposition + keys
- MCP `describe_application` (SPARQL + interface.json fallback); scopes / MCP policy / server wired
- `rebuild-graphs` CLI; GraphDB re-index escrow/fees/loanservices — loanservices proxies: BulkUpload, Cash, Escrow, Lafa, Lamp
- Phase B: `EAKG__ENGINEERING_GRAPH` default `true`; sync/onboard pass flag; MCP `search_code` over shard `engineering/graph.json`
- Tests: `test_interface_surface.py` + scopes; docs: CONTEXT, test-queries ENG lines, ENGINEERING_GRAPH_ANALYSIS, FLOWS
- Note: removed stale `.venv/Lib/site-packages/packages` shadow (was masking editable installs)

---

## [2026-10-12] — Plaisse-dev URLs (EAKG env=dev)

**Session type:** Ops

**Completed:**
- Registry `dev` bases: escrowapi / fees / loanservicesapi `*.dev.pennymac.plaisse.com`
- `.env` `EAKG__ENVIRONMENT=dev`; SSE + loan-api bases aligned
- Specs refreshed (escrow 513, loanservices 266 paths); ApiIndex **1090** ops
- Wired `registry_catalog` + `AppHealthService` through `eakg_runtime` (Postgres openapi)
- MCP `/ready`: env=dev, catalog ops=1090; LoanServices Summary live **200**
- Note: Escrow M2M may **401** (host reachable; audience/perm separate from old `:9101` unreachable)

---

## [2026-10-12] — ADR-027 Postgres artifact store cutover

**Session type:** Implementation + ops

**Completed:**
- ADR-027 accepted: `EakgArtifactStore` (`file` \| `postgres`); schema `sql/eakg_artifacts.sql`
- Wired registry / ShardStore / ApiIndex catalog / Tools factory + modular hot-reload via `eakg_runtime`
- `.env` `EAKG_STORE__BACKEND=postgres` (DSN ← pgvector)
- `uv run python -m packages.eakg artifacts migrate-from-disk` → registry 3, interfaces+manifests+openapi for escrow/fees/loanservices, ops env `local`
- Verify: `artifacts status` backend=postgres; ApiIndex `load_or_build` → **980** ops
- Tests: `test_artifact_store.py` green
- CONTEXT.md: `EAKG_STORE__*` env rows

---

## [2026-10-12] — TASKS: Minimal API + multi-language extract

**Session type:** Backlog

**Completed:**
- Added **Next (EAKG feed)** task: Multi-stack API extract (ASP.NET Minimal APIs + pluggable extractors for other languages; OpenAPI-primary when complete)
- Linked parked “tree-sitter / CodeQL” line to that task

---

## [2026-10-09] — GraphDB Free live + graph-load + MCP restart

**Session type:** Ops

**Completed:**
- Temurin 17 + GraphDB 10.8.13 under `D:\Users\v-mbohra\tools\` (outside clone)
- Home/data: `D:\Users\v-mbohra\graphdb-home` — repo `loanops` created
- `uv run python -m packages.eakg graph-load` → escrow/fees/loanservices OK; SPARQL COUNT ops = **949**
- `.env` `GRAPH_STORE__*` pointed at `localhost:7200/repositories/loanops`
- MCP restarted on `:8001` (health 200); Workbench opened
- Helper: `D:\Users\v-mbohra\tools\start-graphdb.cmd`

---

## [2026-10-09] — ADR-026 SPARQL graph store (GraphDB / Neptune path)

**Session type:** Architecture + implementation

**Completed:**
- ADR-026 in `decisions.md` (partial supersede ADR-017 query path)
- `GraphStoreConfig` + `get_graph_store()` (15th factory) + `HttpSparqlGraphStore` / `FakeGraphStore`
- EAKG `query.py` async SPARQL; MCP/tools dispatch off `merge_shards`
- Onboard/cross-app upload named graphs (no new `graph.ttl` / `evidence.ttl`)
- CLI: `python -m packages.eakg graph-load` + `scripts/_cutover_graph_store.py`
- Fake cutover OK: escrow/fees/loanservices → 949 ops; `data/eakg/repos/` already gitignored

**Blocked (operator):** GraphDB Free not running on this machine (`localhost:7200` refused). After install + repo `loanops`: `uv run python -m packages.eakg graph-load` then Workbench `http://localhost:7200`.

---

## [2026-10-09] — MCP discovery answer gaps

**Session type:** Fix (TESTX chat review)

**Completed:**
- `format_search_outcome`: `backend:` always first; `invoke` GET-only (not HEAD); `params: none in cached spec`
- EAKG: `search_capabilities` prefers GET + `non_get_omitted`; `find_providers` keeps all methods; `mcp_invoke` = GET only
- MCP tool descriptions match those contracts
- Review findings from ecc-code-reviewer + ecc-architect addressed; MCP `:8001` restarted

**Not done:** real query-parameter names. Local fixtures come from `interface.json` (path tokens only). Needs a swagger refresh.

---

## [2026-10-09] — GraphRAG review recorded (ADR-025)

**Session type:** Docs / decision

**Completed:**
- `docs/GRAPHRAG_REVIEW.md` — verdict, evidence, alternatives, revisit triggers
- ADR-025 in `decisions.md` (Deferred): do not add GraphRAG
- Pointer from `ARCHITECTURE.md` §11

**Reason:** User asked to save the GraphRAG recommendation.

---

## [2026-10-09] — Part 1 local enable: escrow / fees / loanservices + pgvector

**Session type:** Ops / local enable (enterprise-app-scale)

**Completed:**
- `provider_contracts` `PgVectorProvider`: `CAST(:x AS vector|jsonb)` for asyncpg; dim probe via `format_type` (pgvector `atttypmod` is dims, not typmod-4)
- Expanded local fixtures from shard `interface.json` (`scripts/_gen_local_openapi_from_interface.py`) — escrow/fees/loanservices
- Postgres `loanops` + `refresh all --env local`: **625** callable GETs embedded (`vs_api_ops_local_47084b1c`); apps 374/140/111
- Search smoke (`vector_index`): escrow / fees / loanservices queries hit correct apps
- Idempotent second refresh: embedded=0, unchanged=625

**Config (local `.env`):** `VECTOR_STORE__PROVIDER=pgvector`, `API_INDEX__ENABLED=true`, `CREDENTIALS__STATIC_SHARED_APPS=["escrow","fees","loanservices"]`

**Open:** restart MCP/Agent API to pick up `.env`; live JWT smoke when tokens available; commit CAST/typmod fix in `provider_contracts` when ready.

---

## [2026-10-09] — Phase 6: documentation + graph upkeep

**Session type:** Docs / bookkeeping (enterprise-app-scale P6)

**Completed:**
- `TASKS.md` Step 17 — P1–P6 ticked; backlog pointer + operator follow-ups
- `ARCHITECTURE.md` — registry-driven catalog, pipeline vs runtime, LoanOps.ApiIndex, CredentialBroker, two-stage search, per-app `/ready` (ADR-024)
- `AGENTS.md` — `get_credential_broker` as 14th common `get_*`; provider category list; ApiIndex already in module layout
- `CONTEXT.md` — `API_INDEX__STALE_AFTER_HOURS` / `SCHEDULER_ENABLED`; ApiIndex + credential one-liners; module layout + provider row
- `decisions.md` — ADR-024 Accepted (confirmed); ADR-023 OpenAPI sidecar noted superseded as **primary** when `API_INDEX__ENABLED=true` (sidecar remains fallback)
- Spec README status table P1–P6 → Completed; plan `p6-*` → completed
- `graphify update .`

**P3–P5:** already logged above this entry (vector index, CredentialBroker, health/scale). No product code changes this phase.

**Open / follow-up:** live SC-006 JWT smoke when per-app tokens available; enable `API_INDEX__ENABLED` in shared envs after index build; OQ-1 non-static broker.

**Plan:** all `p6-*` → completed. Spec delivery todos 56/56 completed (operator follow-ups outside plan).

---

## [2026-10-09] — Phase 5: health, metrics, scheduler, scale suite

**Session type:** Implementation (enterprise-app-scale P5)

**Completed:**
- `AppHealthService` (`health.py`): registry issues, spec pointers/stale (48h), index coverage, `broker.check`, last-invoke ring, breaker `state_of`
- `/ready` §5.2 body via `ModularToolsClient.readiness_snapshot`; MCP 503 only when no catalog
- Metrics §9.5: `api_index.search.*`, `sse.invoke.*`, `api_index.refresh.duration_ms`, `api_index.reindex.embedded`, `api_index.catalog.load_ms`
- Scheduler §9.6: `scheduler.py` + file lock `api_index_refresh`; Agent API/MCP start via tools client when `API_INDEX__SCHEDULER_ENABLED`
- `scripts/fixtures/gen_scale_fixture.py` (seeded synthetic, default 30×170); `data/eval/api_discovery_benchmark.jsonl` (120 Q)
- `-m scale` tests (`test_scale.py`): SC-002–005, ready flat, isolation, env separation, incremental, scheduler lock; `--scale-profile=small|full`
- Gates: mypy --strict (P5 modules), pytest api_index+invoke (45p/1s scale small), check_project_refs OK, graphify update
- Demo: skipped full `run-demo.ps1` this unit (scale/fixture tests cover health+ready path)

**Scale sizing:** CI default `--scale-profile=small` (5×20); full 30×170 via `--scale-profile=full`. `test_top5_recall` uses mock embed+exact indexed text (non-skippable); `test_discovery_p95_local` skips when bge/Qdrant server unavailable.

**Assumptions:** stale=48h / nightly placeholders (G9/G10); thresholds ready&lt;10s, discovery p95&lt;1.5s, top-5≥90%; hot-reload fingerprint already includes operations.json from P1/P2.

**Plan:** all `p5-*` → completed.

---

## [2026-10-09] — Phase 4: CredentialBroker + per-app invoke

**Session type:** Implementation (enterprise-app-scale P4)

**Completed:**
- `credential_broker.py`: AbstractCredentialBroker, AccessToken, Principal, CredentialCheck, CredentialError family; Static/Mock/Caching (single-flight + invalidate)
- `CredentialsConfig` + `get_credential_broker()` (14th `get_*`); `.env.example` / CONTEXT rows
- Contract tests `test_credential_broker.py`; invoke rewrite §6.4 (AppTarget, origin bind, header strip, 401 retry, outcomes, breaker, audit `sse.live_read`)
- `resolve_invoke_target`; registry `allowed_origins` / `build_app_targets`; call payload fields + MCP tool description
- Spec refresh via broker (`broker_token_source`); pointer `credential` field; ModularToolsClient primes broker
- `BreakerRegistry` Protocol in `sse/types.py`; `InMemoryBreaker` open/half_open in `api_index/breaker.py`
- Tests: `test_invoke_per_app.py` (§14.1 P4) — 25 broker+invoke green; broader sse/tools 41 passed
- Gates: mypy --strict (P4 modules), check_project_refs OK, os.environ gate clean, `graphify update .`
- Demo: skipped full `run-demo.ps1` this unit (fixture/local tests cover invoke path)

**Skipped:** `p4-smoke-rerun` live JWT SC-006 against real dev — no per-app `APP_TOKEN_*` / operator JWT path exercised; fixture SC-006 named `no_access` covered in `test_invoke_per_app.py`. Log for operator re-run when tokens available.

**Assumptions:** Static+Mock M2M only (OBO deferred); legacy swagger/fixture still uses `service.bearer_token` when no target; `normalize_path` moved to `sse/catalog.py` (api_index re-exports).

**Plan:** all `p4-*` → completed (smoke = skipped-with-note).

---

## [2026-10-09] — Phase 3: vector index + two-stage search

**Session type:** Implementation (enterprise-app-scale P3)

**Completed:**
- `ApiIndexConfig` (`API_INDEX__ENABLED` / `NAMESPACE_PREFIX` / `APP_SHORTLIST_SIZE`) in settings + `.env.example` + CONTEXT.md
- `indexer.reindex`: model-fingerprint namespace, manifest text_hash diff, batch embed, upsert/delete, atomic manifest, sidecar
- `KeywordIndex` graded score + exact-name apps
- `ApiSearchService` two-stage + always post-filter + query-embed LRU + sidecar/keyword fallback
- Wire: factory builds search when enabled; MCP `search_sse_apis` gains `application` / `permission`; sse.tools duck-types (no api_index import)
- `refresh` CLI `app|all|nightly`; `embed_openapi` → subprocess `refresh all --sidecar-only`
- Tests: `test_indexer.py`, `test_search.py` (§14.1 P3); provider_contracts vector contracts already green (G6)
- Gates: mypy --strict, pytest ApiIndex+contracts (34p/2s), check_project_refs, graphify update
- Demo: skipped full `run-demo.ps1` this unit; Settings/CLI smoke after `uv sync --reinstall-package`

**Assumptions:** interim refresh token = `EAKG__LIVE_SPEC_TOKEN` passthrough (audience-gated interim deferred); sidecar-only skips vector store; P5 ApiIndex fields present with defaults.

**Plan:** all `p3-*` → completed (approval + vector-filter were already done).

---

## [2026-10-09] — P1/P2 quality gates closed

**Session type:** Quality gates (enterprise-app-scale)

**Gates (tier: repo-scripts / DoD):**
- `uv run mypy --strict` on Common/Sse/Eakg/ApiIndex/Tools/McpServer — pass (fixed 40→0)
- pytest P1/P2 + contract_tests — 128 passed
- `check_project_refs` — OK (15 projects)
- provider concrete-import / `os.environ` grep — pass (Protocols + factory/testing only; no os.environ outside settings)
- Windows smoke `.\run-demo.ps1` — MCP/Agent/Web UP; `/ready` registry mode `source_count=3`, `source_errors=[]`
- Live JWT invoke smoke — skipped (SSE__API_KEY present; not required for P1/P2 readiness)
- `graphify update .` — rebuilt

**Fixes during gates:**
- mypy: factory Qdrant `path` removed (provider_contracts), Langfuse None guard, `_Tools.operation_resolver`, eakg typing
- `run-demo.ps1` → `python -m packages.mcp_server` (tools_api gone); child env forces `SSE__CATALOG_SOURCE=registry` / `EAKG__ENVIRONMENT=local`
- `stop-demo.ps1` `${port}:` parse fix
- `uv sync --reinstall-package` for stale site-packages `packages/sse`

**Plan:** `p1-quality-gates`, `p2-quality-gates` → completed.

---

## [2026-10-09] — Phase 2: unified ops, resolver, bind

**Session type:** Implementation

**Completed:**
- `build_operations` + atomic `operations.json`; CLI `build` / `report`.
- `OperationResolver` aliases; `find_operation` + bind map to `public_id`; non-read-only rejected.
- `CapabilityRecord.application_id` from `belongsToApp` SPARQL.
- Readiness `catalog_health`. Factory loads/builds OperationCatalog in registry mode.
- Tests: ApiIndex + bind (15) green; mypy + `check_project_refs` green.

**Not done (at time of entry):** `p2-quality-gates` — closed in later gate session above.

---

## [2026-10-09] — Phase 2 started: LoanOps.ApiIndex

**Session type:** Implementation

**Completed:**
- G4 approved. Commit Phase 1 (`1f906b2`).
- Scaffold `projects/LoanOps.ApiIndex` (`loanops-api-index`). Workspace + Tools deps. `check_project_refs` OK.
- `normalize_path` + OpenAPI↔EAKG join (`exact`/`suffix`/…). Tests: 3 passed. mypy clean.

**Next:** (done in session continuation)

---

## [2026-10-09] — Phase 1: spec cache, registry catalog, pgvector

**Session type:** Implementation

**Completed:**
- Cached OpenAPI under `repos/<id>/openapi/<env>/` (`refresh_spec`, last-good pointer, `spec-refresh`, nightly `refresh_all`).
- MCP catalog in registry mode reads those files. No swagger HTTP at boot. Fingerprint reload every 5s.
- Synthetic local specs for escrow, fees, loanservices.
- API index target is pgvector (`.env.example`, ADR-024, spec D6). Settings default stays `qdrant`.

**Not done:** `p1-quality-gates` (`make demo`, provider contract suite). Phase 3 is the actual upsert into `vs_*`.

**Reason:** Continue Phase 1. User chose pgvector for the API index.

---

## [2026-10-09] — Phase 1 started: application mapping

**Session type:** Implementation

**Completed:**
- ADR-024 Accepted. G1–G3 treated as approved by starting Phase 1.
- `EAKG__ENVIRONMENT`, `SSE__CATALOG_SOURCE` in settings, `.env.example`, `CONTEXT.md`.
- Registry row is the source↔address mapping (`git_url`, `service_url_key`, `environments`).
- `registry validate` and `registry import-taac` (fills a blank URL, never writes `git_url`).
- Tests: `projects/LoanOps.Eakg/packages/eakg/tests/test_registry_env.py` (6 passed).

**Not done:** spec cache, onboard wiring, catalog-from-cache, local fixtures, full Phase 1 gates.

**Reason:** User said plan and start working on enterprise-app-scale.

---

## [2026-10-08] — Spec: enterprise app scale (30+ apps)

**Session type:** Design

**Completed:**
- ADR-024 Proposed in `decisions.md` (registry-driven catalog, pipeline specs, vector index, pluggable `CredentialBroker`).
- Spec package `.ai/specs/enterprise-app-scale/` (story, spec, plan, README).
- Design review `.ai/working/spec-design-reviews/enterprise-app-scale-1.md` failed at 3.8 (2 must-fix, 16 should-fix). Fixes applied in spec + plan (demo runs registry mode; raw method+path needs `application`; remaining RC-003–RC-018).

**Not started:** implementation. Phase 1 waits on G1–G3 approval (repo owner until a product owner is named).

**Reason:** User wants LoanOps to support 30+ enterprise apps, not a POC. Auth model stays undecided and pluggable.

---

## [2026-10-08] — EAKG-only Cursor MCP query (no SSE invoke)

**Session type:** Validation

**Query:** “Which app provides GetLoanSummary? Explain it.” (no loan id / no `call_sse_api`)

| Tool | Args | Result |
|------|------|--------|
| `search_capabilities` | `query=loan summary`, `limit=5` | Top: `GetLoanSummary` → app `loanservices`, `GET /{id}/Summary`, evidence `LoansController.cs:235` (roslyn, conf 0.97) |
| `find_providers` | `query=GetLoanSummary` | Same: provider `loanservices` |
| `explain_capability` | `capability_id=GetLoanSummary` | Full card: op, path, code_unit, evidence, authz_source=`unknown` |

**Verdict:** **PASS** — answered from EAKG shards only; no live SSE / no 401 path.

**Reason:** User asked to test a query where only EAKG required.

---

## [2026-10-08] — Flow C Cursor-chat smoke (3 parallel subagents)

**Session type:** Validation

**Setup:** Authenticated `user-loanops` MCP (`mcp_auth`). Spun 3 local `generalPurpose` subagents in parallel (Flow C: Cursor → MCP `:8001` → `search_sse_apis` → `call_sse_api`). Demo loan `1000002245` from `docs/06-demo-queries-100245.md`.

| # | Query | Subagent | Discovery | Invoke URL | HTTP | Verdict |
|---|-------|----------|-----------|------------|------|---------|
| 1 | Show me the loan summary for 1000002245 | [Loan summary](71cf61f3-dfdb-4ae1-93e2-bf81cd5bed9c) | `loanservices:getLoanSummary` | `…/api/Loans/1000002245/Summary` | 401 | PARTIAL |
| 2 | What are the payment schedules for loan 1000002245? | [Payment schedules](caafad12-e96a-4f2b-b4da-e7783f12117b) | `loanservices:getPaymentSchedules` | `…/api/Loans/1000002245/PaymentSchedules` | 401 | PARTIAL |
| 3 | Get escrow details for loan 1000002245 | [Escrow details](bb0c933b-8a81-4665-b95c-0154f0fff9dc) | `loanservices:getEscrows` | `…/api/Loans/1000002245/Escrows` | 401 | PARTIAL |

**Worked:** MCP namespace ready; search (OpenAPI + EAKG) found correct ops; GET-only invoke hit right LoanServices DEV URLs (~170–200 ms).  
**Failed:** All three live calls **401** — SSE/LoanServices bearer not accepted (refresh `SSE__API_KEY` / MCP process env).  
**Note:** Q1 `capability_id=get_loan_summary` and bare `operation_id=GetLoanSummary` rejected (“only allows a resolved GET operation”); catalog id `loanservices:…` required.

**Reason:** User asked to test 3 Cursor-chat queries via subagents and record everything.

---

## [2026-04-08] — Cursor → MCP hardening (5 Required)

**Session type:** Implementation

**Completed:**
- `get_settings()` cached; hot paths wired.
- Shared GET-only policy in `packages/tools/policy.py` + `ModularToolsClient` + fail-closed `invoke_sse_api`; MCP reuses asserts (ADR-022 Proposed).
- EAKG tools moved to `packages/tools/eakg_tools.py`; MCP `execute_tool` always `client.call`.
- `CapabilityCatalogService` fingerprint cache; OpenAPI embed sidecar + `python -m packages.sse.embed_openapi` (ADR-023 Proposed).
- MCP `/health` liveness + `/ready` snapshot.
- Docs: Flow C first in `THREE_QUERY_FLOWS` / `DEBUG_LAYER2`; ARCHITECTURE + review doc updated.

**Reason:** Execute architecture review active Required items (auth/PII/UI deferred).

---

## [2026-10-06] — Embedding search for OpenAPI + EAKG

**Session type:** Implementation

**Completed:**
- `packages/sse/semantic.py` — cosine search over OpenAPI ops; `search_sse_apis` uses EmbeddingProvider (keyword fallback).
- EAKG capability block uses sidecar `embeddings.json` even when `CAPABILITY_KG__SEMANTIC` is false.

**Reason:** User asked for embedding search on both swagger catalog and RDF-backed capabilities.

---

## [2026-10-04] — Plaisse wiki vs LoanOps comparison doc

**Session type:** Analysis / docs

**Completed:**
- Wrote `docs/PLAISSE_WIKI_VS_LOANOPS.md` (goals, knowledge stores, live GET, docs-from-code, when to use which).

**Reason:** Capture wiki vs LoanOps in simple words after architecture comparison in chat.

---

## [2026-10-04] — EAKG engineering graph MVP

**Session type:** Implementation

**Completed:**
- Analyzer registry (`DotNetRoslynAdapter`, optional `GraphifyAstAdapter`); onboard no longer uses hardcoded `EXTRACTORS`.
- `--engineering-graph` + `python -m packages.eakg code --id --operation`.
- Projector `links.json`; `.graphifyignore` template; Graphify failure does not fail index.

**Reason:** Link EAKG operations to Graphify symbols without copying AST into Turtle.

---

## [2026-10-04] — Engineering graph analysis doc

**Session type:** Analysis / docs

**Completed:**
- Wrote `docs/ENGINEERING_GRAPH_ANALYSIS.md` (Graphify vs EAKG, STEP 5, OpenAPI join, gaps).
- One-off `graphify extract --code-only` on `.eakg-workspace/{escrow,fees,loanservices}` → `.eakg-workspace/graphify/` (gitignored, **not** onboard/CI).
- Pointers in ARCHITECTURE §10, CONTEXT §19, `EAKG_COMMITTED_VS_LOCAL.md`.

**Reason:** Record current graph state so Graphify-on-SSE is not mistaken for pipeline.

---

## [2026-10-04] — Pull Cursor engineering pack from pennysenselambda

**Session type:** Tooling / agent config

**Completed:**
- Copied Addy Osmani skills + `references/` + `/review` `/ship` `/test` `/build` `/webperf` `/code-simplify`.
- `/spec` `/plan` rewritten to Promp `.ai/specs/` (no root `SPEC.md`).
- `agent-skills.mdc`; restored `git.github-gitlab.mdc`.
- Skipped PennySense product rule and always-`glab` rule.

**Reason:** Reuse impl/test/review workflows without colliding Promp spec layout or GitHub origin.

---

## [2026-10-04] — ADR-021 general internal audience

**Session type:** Positioning / docs + light code

**Completed:**
- ADR-021: platform for any internal role (not care-rep-only).
- `user` role in scopes; `care_rep` = deprecated alias.
- AGENTS / README / ARCHITECTURE / CONTEXT / one-pager 09 / §B prompt opener.
- Agent API title/description + ChatRequest docstring.

**Reason:** Product moved off care-rep-only; docs/roles catch up.

---

## [2026-10-04] — Richer capability embed text

**Session type:** Feature

**Completed:**
- `capability_text`: summary + op camel-split + HTTP path phrases.
- SPARQL / `CapabilityRecord.http_path`; OpenAPI comment = summary+description+tags.
- EAKG `graph_build`: persist summary → `rdfs:comment`; enrich pulls description/tags.
- Tests: payment-due ranks above fees-due (capability_kg + eakg).

**Reason:** “next payment due” was matching random “due” ops; path/summary density fixes rank.

---

## [2026-10-04] — Product CAPABILITY_KG__SEMANTIC=true

**Session type:** Config / smoke

**Completed:**
- `.env`: `CAPABILITY_KG__SEMANTIC=true`; `EMBEDDING__PROVIDER=local_bge` (match sidecar).
- Smoke: `eakg_capability_search_block("when is the next payment due")` → EAKG hits.
- `.env.example` note updated.

**Reason:** Wire NL capability rank into product search path.

---

## [2026-10-04] — Park golden-set refresh task

**Session type:** Backlog

**Completed:**
- TASKS: refresh `data/golden.jsonl` for SSE/MCP tool names (later).
- Eval MCP hop stays blocked until that + Bedrock SSO.

**Reason:** Golden answer key still pre-ADR-010 tools.

---

## [2026-10-04] — Wire EAKG capability embeddings

**Session type:** Feature

**Completed:**
- `catalog_from_shards` loads `enterprise/embeddings.json`.
- CLI `python -m packages.eakg embed` + `query search --semantic`.
- Keyword still `[]` for “when is the next payment due”; semantic returns due/schedule APIs.

**Reason:** Plug Phase 9 cosine into live shards.

---

## [2026-10-03] — Roslyn reindex pilot git clones

**Session type:** Ops / extractor

**Completed:**
- Fixed Roslyn tool discovery (cwd/git; uv site-packages). `extractor=roslyn` no silent regex if 0 ops.
- Manifest records `extractor`. Re-onboarded escrow/fees/loanservices from `.eakg-workspace`.
- Ops 510 / 242 / 261. `cross-app` 243 rels. Query `GetLoanSummary` → `dotnet_roslyn`.

**Reason:** Live shards were still regex (`dotnet_static`).

---

## [2026-10-03] — Live SSE swagger verify

**Session type:** Ops / evidence

**Completed:**
- Forced HTTP swagger (`fixture_path=None`). Stale M2M → swagger 401; refresh → 292 ops.
- Hand catalog 6 paths HIT vs live `{id}` templates. `GET /api/Loans/{id}/Summary` HTTP 200.
- Script `scripts/verify_live_sse_swagger.py`. Evidence `docs/SSE_LIVE_SWAGGER.md`.
- Team `swagger tofile` still open.

**Reason:** Prove live OpenAPI fetch, not only hand catalog.

---

## [2026-10-03] — Skip Gemini MCP validation

**Session type:** Backlog

**Completed:**
- Phase 12 Gemini parked. No evidence table. Cursor Phase 11 stays IDE proof.
- Next: live SSE swagger verify; eval MCP hop still SSO-blocked.

**Reason:** User skip Gemini.

---

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


## [2026-10-02] - Gap 1+2: capability bind + requiresPermission at MCP

**Session type:** Feature (MCP policy)

**Completed:**
- Subagents: `capability_bind.py` + `capability_authz.py` + unit tests.
- Wired `execute_tool` / `call_sse_api(capability_id=…)` in `packages/mcp_server/server.py`.
- Settings: `CAPABILITY_KG__REQUIRE_CAPABILITY_BIND`, `ENFORCE_PERMISSIONS`, `ALLOWED_PERMISSIONS` (defaults off).
- Docs: `MCP_SECURITY.md`, `.env.example`. Tests: 24 MCP suite green.

**Reason:** User: Work on gaps 1 and 2 in subagents.

## [2026-10-12] - Auth0 M2M `requested_destination`

**Session type:** Feature (credentials)

**Completed:**
- `packages.common.auth0_destination.resolve_destination` (PNMAC/wiki port).
- `Auth0M2MCredentialBroker` + factory `CREDENTIALS__PROVIDER=auth0_m2m`; destinations from registry `base_url`.
- Settings/`.env.example`/`CONTEXT.md` Auth0 knobs.
- Unit tests `test_auth0_destination.py` (2 passed).
- Smoke: modular `call_sse_api` `escrow:GET_api_escrow_getescrowbyloannumber` → HTTP 200 (loan 1000002245). Dest map: escrow→escrowapi, fees→feesapi, loanservices→loanservicesapi.
- MCP restarted on :8001 with `auth0_m2m`.

**Reason:** User: Can you use destination.

## [2026-10-13] - Eng graph sync ops (plan 1C steps 1-4)

**Session type:** Ops

**Completed:**
- graphify 0.9.72 on PATH
- `eakg sync repo` escrow / fees / loanservices — engineering_graph=ok
- Shard graphs: escrow 64.9MB, fees 33.6MB, loanservices 31.2MB (+ links.json)
- MCP restarted :8001
- Smoke: `describe_application` loanservices → 5 proxies; `search_code` Proxy hits; Facade → 0 (no *Facade* in AST)

**Reason:** User: do 1-4 (graphify, sync, restart MCP, smoke ENG queries).

## [2026-10-29] — Layers 7-9 on Langfuse (EvalStore)

**Session type:** Eval layers

**Completed:**
- ADR-032: EvalStore provider (jsonl default + langfuse) for L7-L9
- provider_contracts.eval_store + telemetry environment; MCP `mcp.client_name` on tool spans
- L7 robustness (canned replays + Wilson pass-rate; `make eval-l7`)
- L8 operations (fixture MCP traces + ops_slos.yaml; `make eval-l8`)
- L9 governance (registry + rubrics + validate/sync/agreement/calibrate/promote; `make eval-l9`)
- Sacred `thresholds.py` / `GoldenExpected` untouched

**Risk:** Live Langfuse path needs running instance; CI uses jsonl/fixtures.

**Next:** L6 security hard-fail suite; optional Langfuse dashboard wiring.
