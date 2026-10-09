# Context brief — enterprise-app-scale (execution grounding)

**Date**: 2026-10-09  
**Spec**: `.ai/specs/enterprise-app-scale/`  
**Scope**: Ground remaining open todos (p1/p2 quality gates + P3–P6). P1–P2 core claimed done thru `5c3956d`. G1–G10 approved (coordinator).  
**Method**: `spec-research-grounding` + `spec-sizing`; graphify-first then targeted reads. Readonly — no builds/tests run.

---

## Status snapshot

| Area | Code reality |
|---|---|
| P1 core | Present: registry schema/validate/import, spec_cache, registry catalog mode, fixtures, fingerprint (incl. `operations.json`) |
| P2 core | Present: `LoanOps.ApiIndex` records/catalog/resolver, bind → `public_id`, `application_id` via SPARQL, report CLI, readiness `catalog_health` |
| P3 | **Stubs only**: `indexer.py`, `keyword_index.py`, `search.py`, `refresh.py` return empty / `not_implemented` |
| P4 | **Absent**: no `credential_broker.py`; `invoke_sse_api` still shared `SSE__API_KEY`; no `AppTarget` |
| P5 | **Stub**: `health.py` empty snapshot; `__main__` health prints scaffold |
| Settings | `EakgConfig.environment`, `SseConfig.catalog_source` shipped. **No** `ApiIndexConfig` / `CredentialsConfig` |
| provider_contracts | v0.2.0 path-dep. Qdrant filter = `MatchValue` only; pgvector **ignores** `filter`; **no** `ensure_namespace` / `supports_any_of_filter` |

Product: API index store = pgvector (`.env.example`); `VectorStoreConfig.provider` default stays `qdrant`. Do not edit user `.env`.

---

## Relevant files

### P1–P2 already shipped (touch carefully; gates verify)

| Path | Why |
|---|---|
| `projects/LoanOps.Common/packages/common/settings.py` | `EakgConfig.environment`, `SseConfig.catalog_source`; add `ApiIndexConfig` (P3/P5), `CredentialsConfig` (P4) |
| `projects/LoanOps.Eakg/packages/eakg/registry.py` | `AppEnvironment`, `list_active`, mapping |
| `projects/LoanOps.Eakg/packages/eakg/registry_validate.py` | Validation rules |
| `projects/LoanOps.Eakg/packages/eakg/registry_import.py` | TAAC import + `load_api_identifier` (interim audience helper exists here) |
| `projects/LoanOps.Eakg/packages/eakg/spec_cache.py` | `refresh_spec` / `refresh_all` with `TokenSource` |
| `projects/LoanOps.Eakg/packages/eakg/onboard.py` | Calls `refresh_spec`; currently passes `cfg.eakg.live_spec_token` for every app (not audience-gated interim) |
| `projects/LoanOps.Eakg/packages/eakg/sync.py` | `sync_nightly` → `refresh_all` with empty token |
| `projects/LoanOps.Eakg/packages/eakg/__main__.py` | `registry validate` / `import-taac` / `spec-refresh` |
| `projects/LoanOps.Tools/packages/tools/registry_catalog.py` | `catalog_mode`, `build_registry_specs`, `catalog_fingerprint` (registry + current.json + operations.json) |
| `projects/LoanOps.Tools/packages/tools/factory.py` | Wires registry mode + `OperationCatalog.load_or_build` |
| `projects/LoanOps.Tools/packages/tools/modular_tools.py` | Hot-reload, `operation_resolver()`, `readiness_snapshot` + `catalog_health` |
| `projects/LoanOps.Sse/packages/sse/loader.py` | `resolve_swagger_links`, registry `_load_registry_specs` (no HTTP) |
| `projects/LoanOps.Sse/packages/sse/catalog.py` | `find_operation(..., resolver=)` + `AmbiguousOperationError` |
| `projects/LoanOps.Sse/packages/sse/types.py` | `CatalogSource` today: id/label/url/operation_count/error — **missing** spec status/fetched_at/stale |
| `projects/LoanOps.ApiIndex/packages/api_index/{records,catalog,resolver,paths}.py` | Unified ops + persistence paths |
| `projects/LoanOps.ApiIndex/packages/api_index/__main__.py` | `build` / `report` live; `health` stub |
| `projects/LoanOps.McpServer/packages/mcp_server/capability_bind.py` | Resolver → `public_id`, rejects non-read-only |
| `projects/LoanOps.CapabilityKg/packages/capability_kg/{sparql,catalog}.py` | `application_id` from `belongsToApp` |
| `data/eakg/registry/repositories.yaml` | local env + `spec_fixture` for 3 apps |
| `data/eakg/fixtures/specs/{escrow,fees,loanservices}.openapi.json` | Synthetic fixtures |
| `.env.example` | `SSE__CATALOG_SOURCE=registry`, `VECTOR_STORE__PROVIDER=pgvector` |
| `run-demo.ps1` / `stop-demo.ps1` | Windows-native demo (Makefile `demo` still POSIX) |

### P3–P5 implementation targets

| Path | Why |
|---|---|
| `projects/LoanOps.ApiIndex/packages/api_index/indexer.py` | Stub `IndexReport` only — implement `reindex` §3.4 |
| `projects/LoanOps.ApiIndex/packages/api_index/keyword_index.py` | Placeholder `suggest` — need graded `score()` §3.5 |
| `projects/LoanOps.ApiIndex/packages/api_index/search.py` | `ApiSearchService.search` returns empty — two-stage + fallback |
| `projects/LoanOps.ApiIndex/packages/api_index/refresh.py` | `not_implemented` — orchestrate spec → build → reindex |
| `projects/LoanOps.ApiIndex/packages/api_index/breaker.py` | Simple failure counter — need open/half_open §3.8; Protocol also belongs in `sse/types.py` |
| `projects/LoanOps.ApiIndex/packages/api_index/health.py` | Empty `AppHealthService` |
| `projects/LoanOps.Sse/packages/sse/invoke.py` | Rewrite per §6.4 (broker, origin bind, outcomes, audit) |
| `projects/LoanOps.Sse/packages/sse/tools.py` | Route search via `ApiSearchService`; `resolve_invoke_target`; payload fields |
| `projects/LoanOps.Sse/packages/sse/embed_openapi.py` | Become thin wrapper over refresh sidecar |
| `projects/LoanOps.Common/packages/common/providers/credential_broker.py` | **Create** (precedent: `loan_data.py` ABC+impls colocated) |
| `projects/LoanOps.Common/packages/common/providers/factory.py` | Add `get_credential_broker()` (14th `get_*`; 13 exist today) |
| `projects/LoanOps.Common/packages/common/providers/contract_tests/test_credential_broker.py` | **Create** |
| `../provider_contracts/provider_contracts/vector_store/{_base,qdrant,mock,pgvector,azure_ai_search}.py` | G6: list=any-of, `supports_any_of_filter`, `ensure_namespace` |
| `scripts/fixtures/gen_scale_fixture.py` | **Create** (P5) |
| `data/eval/api_discovery_benchmark.jsonl` | **Create** (P5) |

### Tests present vs plan names

| Present | Plan-named gaps |
|---|---|
| `eakg/tests/test_registry_env.py`, `test_spec_cache.py` | No separate `test_registry_import.py` / `sse/tests/test_registry_catalog_mode.py` (coverage partially folded into above) |
| `api_index/tests/test_{normalize,build,resolver}.py` | Need `test_indexer.py`, `test_search.py`, `test_scale.py` |
| `mcp_server/tests/test_capability_bind.py` | Extend as needed |
| — | `sse/tests/test_invoke_per_app.py` (P4) |

---

## Integration & wiring points

1. **Catalog source selection** — `factory.build_modular_tools_client` → `registry_catalog.catalog_mode(cfg)` → `OpenApiCatalogService(registry_specs=..., reload_specs=...)`. P3 must inject `ApiSearchService` here (or via `ModularToolsClient`) when `API_INDEX__ENABLED`; default false keeps sidecar cosine path (`sse/semantic.py`).

2. **OperationCatalog runtime** — factory already `OperationCatalog.load_or_build(...)`. Search/indexer consume `catalog.ops` / `resolver` / keyword index built from that set. Fingerprint already includes `operations_path` (`registry_catalog.catalog_fingerprint`).

3. **Search tool surface** — `packages/sse/tools.py` `handle_search_sse_apis` still uses local semantic helpers; must branch to `ApiSearchService` + MCP tool args `application` / `permission` (`mcp_server/server.py`).

4. **Invoke path** — `tools.py` → `find_operation` → `invoke_sse_api` with shared bearer. P4: add `resolve_invoke_target` before invoke; inject broker + breaker from factory/MCP lifespan; `registry_mode` reject raw method+path without `application`.

5. **Allow-list** — `OpenApiCatalogService.allowed_origins()` only swagger/api_base today. P4: derive from registry app targets (`build_app_targets` **missing** — add beside `build_registry_specs`).

6. **Spec-fetch token** — `TokenSource` hook exists on `refresh_spec`, but callers use blank token or raw `live_spec_token` (not `interim_spec_token_source`). P4 replaces with broker; until then NFR-010 interim is incomplete.

7. **VectorStore DI** — `get_vector_store_provider()` / `get_embedding_provider()` from `factory.py` only. Indexer/search must not import concrete providers. LoanOps path-depends `../provider_contracts` editable — G6 edits land in sibling repo, bump from `0.2.0`.

8. **G6 filter capability** — `ApiSearchService` must `getattr(vs, "supports_any_of_filter", False)` and post-filter always (spec §3.5). Works before/after provider release.

9. **`/ready`** — `ModularToolsClient.readiness_snapshot` already emits `catalog_health`. P5 merges `AppHealthService` per-app body (spec §5.2); MCP `server.py` exposes it. 503 only when no catalog.

10. **Scheduler** — P5 optional asyncio task under `API_INDEX__SCHEDULER_ENABLED`; file lock under `.eakg-workspace/.locks/` (pattern: `eakg/locks.py`). Production still external cron → `python -m packages.api_index.refresh nightly`.

11. **Broker priming** — MCP/Agent lifespan must `await broker.prime(active_app_ids)` (P4); hot-reload path in `modular_tools._maybe_reload_catalog` must re-prime new apps.

12. **Dependency direction** — `common ← sse, eakg ← api_index ← tools ← mcp_server/agent_api`. Keep `BreakerRegistry` Protocol in `sse/types.py` so `sse.invoke` does not import `api_index`.

13. **Windows demo smoke** — `Makefile` `demo:` uses `uvicorn … &` (fails on PS 5.1). SC-010 / quality gates: use `.\run-demo.ps1` (or fix Makefile per spec §8.2). Do not treat POSIX `make demo` as the Windows gate.

14. **Live smoke `p4-smoke-rerun`** — needs real JWT; coordinator: skip if credentials missing; prefer fixture/local; log skip in `logs.md`.

---

## Conventions execution must follow

| Convention | Exemplar |
|---|---|
| Provider ABC + concrete + factory; no concrete imports outside `providers/` | `packages/common/providers/loan_data.py`, `factory.py` |
| All env via settings nested `__` | `settings.py` (`SseConfig.catalog_source` pattern) |
| Secrets via `get_secrets_provider().get_or_default` | existing env secrets provider |
| Contract tests parametrized over impls | `providers/contract_tests/test_vector_store.py` |
| Atomic JSON writes (tmp + replace) | `api_index` operations persistence pattern in `catalog.py` |
| Synthetic fixtures / `*.example.invalid` / loopback | `data/eakg/fixtures/specs/`, registry local URLs |
| Async throughout; `mypy --strict` | AGENTS.md |
| PowerShell: no `&&` / `\|\|` | `.cursor/rules/shell-powershell.mdc` |
| Graphify update after code changes | AGENTS.md |
| `check_project_refs.py` green when touching workspace deps | root `scripts/` |

---

## P1 / P2 quality-gate blockers (for execution)

Research did **not** run mypy/pytest/`make demo` (readonly). Blockers/risks from static evidence:

| Risk | Severity | Notes |
|---|---|---|
| `make demo` POSIX `&` / `pkill` | **Hard on Windows** | Use `.\run-demo.ps1` for SC-010; optionally land Makefile/demo.ps1 fix during gate |
| Incomplete P1 vs completed todos | Medium | `CatalogSource` lacks status/stale/fetched_at; no `interim_spec_token_source` wiring; no `AppTarget`/`build_app_targets` (latter is P4) |
| Plan test file names missing | Low | Import/catalog coverage exists under other names — gates should run existing suites, not require rename |
| `.env.example` pgvector | Low if demo path avoids store | DocsService construction is try/except; registry demo should not need Postgres if embeddings optional |
| Unverified green suite | Unknown | Gate todos themselves must run mypy/pytest/contract/grep/`check_project_refs`/graphify |

No approval-gate blockers remain (G1–G10 granted).

---

## Sizing

See coordinator return YAML. Verdict: **should-split** for remaining delivery (P3 ∥ P4, then P5). P1/P2 quality-gate closeout stays on current spec first.

---

## Gap classification summary

**Open questions (BIG)** — residual story items that do **not** block static-broker P4 or flag-gated P3, but remain product decisions:

- OQ-1 / story Q1: final access model (beyond static/mock)
- OQ-5 / story Q5: user vs assistant permission filter (depends on Q1)
- OQ-4: audit retention (compliance)

**Not escalated as blockers** (approved or placeholder-settled): G1–G10; OQ-2/OQ-3 → use story threshold values and 48 h stale / nightly per G9/G10 approval; OQ-6 gates already routed to repo owner; OQ-7/OQ-8/OQ-9 have spec placeholders.

**Proposed assumptions (SMALL)** — see coordinator return.
