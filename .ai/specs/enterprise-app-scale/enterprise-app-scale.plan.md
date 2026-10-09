---
name: enterprise-app-scale
overview: Make the LoanOps registry the single source of 30+ enterprise apps with pipeline-cached specs, a unified operation record, a vector-indexed two-stage search, per-app credentials via a CredentialBroker provider, and per-app health — delivered in five independently shippable phases.
todos:
  - id: p1-approval-gate
    content: "Obtain approval for G1 (accept ADR-024), G2 (registry schema additions) and G3 (EAKG__ENVIRONMENT, SSE__CATALOG_SOURCE); record outcome in Notes"
    status: completed
  - id: p1-settings
    content: "Add EakgConfig.environment and SseConfig.catalog_source to packages/common/settings.py; ship .env.example with SSE__CATALOG_SOURCE=registry and EAKG__ENVIRONMENT=local; document auto precedence in CONTEXT.md"
    status: completed
  - id: p1-registry-schema
    content: "Add AppEnvironment, lifecycle, service_url_key, environments, optional git_url and list_active(env) to packages/eakg/registry.py with backward-compatible from_dict/to_dict"
    status: completed
  - id: p1-app-mapping
    content: "Application mapping (FR-022, spec §4.1): one registry row joins optional git_url to environments[env].base_url via application_id. TAAC import fills a blank base_url only and never writes git_url. No second map file. Test both-sides, API-only, and source-only cases."
    status: completed
  - id: p1-registry-validate
    content: "Create packages/eakg/registry_validate.py implementing every rule in spec §4.1 and a 'registry validate' subcommand in packages/eakg/__main__.py"
    status: completed
  - id: p1-taac-import
    content: "Create packages/eakg/registry_import.py and 'registry import-taac --env --dry-run' subcommand: fill-blank seeding from TAAC ServiceUrls / Auth0.Api.Identifier, conflict and unregistered-candidate report"
    status: completed
  - id: p1-spec-cache
    content: "Create packages/eakg/spec_cache.py (refresh_spec, refresh_all, read_current_spec, current.json pointer, last-good retention, prune to 3) and fetch_spec_with_source with same-origin redirects in openapi_enrich.py"
    status: completed
  - id: p1-onboard-wire
    content: "Wire onboard_repository to call refresh_spec with the env base_url and pass the spec into enrich_interface(spec=...); support API-only records (git_url empty); add 'spec-refresh' subcommand; call refresh_all from sync_nightly"
    status: completed
  - id: p1-catalog-from-cache
    content: "Add SpecSource/AppTarget, CatalogSource status fields and registry mode to OpenApiCatalogService (no network); create packages/tools/registry_catalog.py; select source in build_modular_tools_client per SSE__CATALOG_SOURCE auto precedence; P1 fingerprint hot-reload on registry YAML plus each openapi/<env>/current.json"
    status: completed
  - id: p1-swagger-links-helper
    content: "Move swagger link resolution into packages/sse/loader.py resolve_swagger_links and use it from tools factory and embed_openapi (fixes ignored SSE__SWAGGER_URLS)"
    status: completed
  - id: p1-local-fixtures
    content: "Add synthetic data/eakg/fixtures/specs/{escrow,fees,loanservices}.openapi.json and local env entries in repositories.yaml so make demo runs registry mode with zero cloud creds"
    status: completed
  - id: p1-tests
    content: "Add P1 tests from spec §14.1 plus shipped .env.example resolves to registry, auto+USE_FIXTURE=true still registry when local fixtures exist, fingerprint hot-reload, and FR-022 mapping (both sides, API-only, source-only, TAAC does not write git_url)"
    status: completed
  - id: p1-quality-gates
    content: "Run mypy --strict, pytest, contract tests, check_project_refs, provider/os.environ grep gates, make demo smoke and graphify update for Phase 1"
    status: pending
  - id: p2-approval-gate
    content: "Obtain approval for G4 (new uv workspace project projects/LoanOps.ApiIndex)"
    status: completed
  - id: p2-project-scaffold
    content: "Scaffold projects/LoanOps.ApiIndex (pyproject loanops-api-index, packages/api_index, tests); add to root workspace and LoanOps.Tools dependencies; keep check_project_refs green"
    status: completed
  - id: p2-normalize-join
    content: "Implement normalize_path and the exact/suffix/ambiguous/eakg_only/openapi_only join in packages/api_index/records.py per spec §3.1–3.2"
    status: completed
  - id: p2-unified-record
    content: "Implement UnifiedOperation, build_operations (public_id collision rules, read_only/callable rules) and atomic operations.json persistence with per-app inputs hashes"
    status: completed
  - id: p2-capability-app-id
    content: "Add application_id to CapabilityRecord from belongsToApp SPARQL (spec §8.2; merge.py unchanged)"
    status: completed
  - id: p2-resolver
    content: "Implement OperationResolver alias map (spec §3.3) and OperationCatalog runtime loader with fingerprint; make sse.catalog.find_operation delegate to the resolver and raise ambiguous errors"
    status: completed
  - id: p2-bind-fix
    content: "Update mcp_server/capability_bind.py so resolve_binding maps capability operation_id to the unified public_id (with application_id) and rejects non-read-only capabilities"
    status: completed
  - id: p2-mismatch-report
    content: "Add 'python -m packages.api_index report' and catalog_health counters in readiness_snapshot (openapi_only, eakg_only, ambiguous, capabilities_unbound)"
    status: completed
  - id: p2-tests
    content: "Add P2 tests from spec §14.1 (normalize table, join cases incl. /{id}/Summary vs /api/Loans/{loan_id}/Summary, resolver aliases and ambiguity, bind fix, report)"
    status: completed
  - id: p2-quality-gates
    content: "Run mypy --strict, pytest, check_project_refs, grep gates, make demo smoke and graphify update for Phase 2"
    status: pending
  - id: p3-approval-gate
    content: "Obtain approval for G5 (API_INDEX__ENABLED, API_INDEX__NAMESPACE_PREFIX, API_INDEX__APP_SHORTLIST_SIZE) and G6 (provider_contracts vector filter list=any-of)"
    status: pending
  - id: p3-vector-filter-contract
    content: "In provider_contracts implement list=any-of filter semantics for qdrant (MatchAny), mock, pgvector and azure_ai_search, plus a contract test; bump provider_contracts version"
    status: pending
  - id: p3-settings
    content: "Add ApiIndexConfig (enabled, namespace_prefix, app_shortlist_size) to settings.py and .env.example"
    status: pending
  - id: p3-indexer
    content: "Implement packages/api_index/indexer.py reindex: model-fingerprint namespace, manifest diff by text_hash, batch embed, upsert/delete, atomic manifest swap, sidecar write"
    status: pending
  - id: p3-keyword-index
    content: "Implement packages/api_index/keyword_index.py inverted index with graded keyword score and exact-name app lookup"
    status: pending
  - id: p3-two-stage-search
    content: "Implement ApiSearchService two-stage retrieval with defensive post-filter, query-embed LRU and fallback chain; route search_sse_apis through it and add application/permission tool args in MCP server"
    status: pending
  - id: p3-refresh-cli
    content: "Implement packages/api_index/refresh.py (app | all | nightly) orchestrating spec refresh, build_operations and reindex with per-app isolation and exit codes 0/2/1; make embed_openapi a thin wrapper"
    status: pending
  - id: p3-tests
    content: "Add P3 tests from spec §14.1 (incremental reindex cases, model change, filter contract, application/permission filters, shortlist recall guard, fallback labels)"
    status: pending
  - id: p3-quality-gates
    content: "Run mypy --strict, pytest incl. provider_contracts contract tests, grep gates, make demo smoke and graphify update for Phase 3"
    status: pending
  - id: p4-approval-gate
    content: "Obtain approval for G7 (CredentialBroker; get_credential_broker is the 14th get_* factory) and G8 (CREDENTIALS__PROVIDER, CREDENTIALS__STATIC_SHARED_APPS, APP_TOKEN_<APPID> secret names)"
    status: pending
  - id: p4-broker-protocol
    content: "Create packages/common/providers/credential_broker.py with AbstractCredentialBroker, AccessToken, Principal, CredentialCheck and CredentialError family"
    status: pending
  - id: p4-broker-impls
    content: "Implement StaticCredentialBroker, MockCredentialBroker and CachingCredentialBroker (single-flight, invalidate); add CredentialsConfig and get_credential_broker() in factory.py"
    status: pending
  - id: p4-broker-contract-tests
    content: "Add contract_tests/test_credential_broker.py parametrized over static and mock (token per app, not-configured error, hidden repr, no-I/O check, single-flight cache, invalidate)"
    status: pending
  - id: p4-invoke-per-app
    content: "Rewrite invoke_sse_api per spec §6.4: AppTarget, broker token, origin binding, header stripping, 401 invalidate+retry, outcome classification, per-app timeouts and BreakerRegistry"
    status: pending
  - id: p4-allowlist-registry
    content: "Derive allowed_origins from registry app targets in registry mode; keep swagger-link derivation only for legacy dev override"
    status: pending
  - id: p4-tool-payload
    content: "Extend call_sse_api response with application_id, application, operation_id, outcome, citation and app-named messages; update tool description to relay no_access/unavailable text"
    status: pending
  - id: p4-audit-live-read
    content: "Emit sse.live_read AuditEvent for every invoke outcome (app, operation, environment, status, outcome, duration) without tokens"
    status: pending
  - id: p4-spec-fetch-broker
    content: "Switch refresh_spec token source from EAKG__LIVE_SPEC_TOKEN to the CredentialBroker and record credential state in the spec pointer"
    status: pending
  - id: p4-tests
    content: "Add P4 tests from spec §14.1 plus raw method+path in registry mode without application returns rejected and sends no Authorization header, and spec server origin mismatch"
    status: pending
  - id: p4-quality-gates
    content: "Run mypy --strict, pytest incl. new contract tests, provider/os.environ grep gates, make demo smoke and graphify update for Phase 4"
    status: pending
  - id: p4-smoke-rerun
    content: "Re-run the 2026-10-08 smoke (loan summary, payment schedules, escrow) against dev with per-app tokens and log results in logs.md (SC-006)"
    status: pending
  - id: p5-approval-gate
    content: "Obtain approval for G9 (API_INDEX__STALE_AFTER_HOURS, API_INDEX__SCHEDULER_ENABLED) and G10 (new benchmark thresholds; confirm story Q2/Q3)"
    status: pending
  - id: p5-health-model
    content: "Implement packages/api_index/health.py AppHealthService merging registry issues, spec pointers, index coverage, broker.check, last invoke outcome and breaker state"
    status: pending
  - id: p5-ready-per-app
    content: "Return the per-app /ready body from spec §5.2 via readiness_snapshot (200 when catalog loaded, 503 only when no catalog)"
    status: pending
  - id: p5-metrics
    content: "Record telemetry metrics listed in spec §9.5 for search, invoke, refresh, reindex and catalog load"
    status: pending
  - id: p5-scheduler
    content: "Add optional in-process nightly scheduler with file lock; hot-reload already shipped in P1 (extend fingerprint to operations.json)"
    status: pending
  - id: p5-scale-fixture
    content: "Create scripts/fixtures/gen_scale_fixture.py (30 apps, ~5k ops, synthetic, seeded) and data/eval/api_discovery_benchmark.jsonl"
    status: pending
  - id: p5-scale-tests
    content: "Add -m scale tests: ready flat (SC-004), discovery p95 mock plus local bge+Qdrant variant (SC-003), non-skippable top-5 recall (SC-002), isolation latency (NFR-004), env separation (US9), 20% isolation (SC-005), incremental one-changed (US7)"
    status: pending
  - id: p5-quality-gates
    content: "Run mypy --strict, full pytest incl. scale suite, grep gates, make demo smoke and graphify update for Phase 5"
    status: pending
  - id: p6-tasks-md
    content: "Update TASKS.md: add and tick enterprise-app-scale items per completed phase"
    status: pending
  - id: p6-logs-md
    content: "Append dated logs.md entries per phase with commands run, results and open questions"
    status: pending
  - id: p6-architecture-md
    content: "Update ARCHITECTURE.md (registry-driven catalog, pipeline vs runtime, LoanOps.ApiIndex, CredentialBroker) and AGENTS.md module layout / provider category count"
    status: pending
  - id: p6-decisions-md
    content: "Update decisions.md: ADR-024 status after approval, note ADR-023 sidecar superseded as primary once API_INDEX__ENABLED ships"
    status: pending
  - id: p6-graphify-final
    content: "Run graphify update . after final doc and code changes"
    status: pending
isProject: false
---

# Implementation Plan: Enterprise App Scale

## Status

| Item | Value |
|---|---|
| Story | [enterprise-app-scale.story.md](./enterprise-app-scale.story.md) |
| Spec | [enterprise-app-scale.spec.md](./enterprise-app-scale.spec.md) |
| ADR | ADR-024 in [decisions.md](../../../decisions.md) (Proposed) |
| Status | Draft — not started |
| Phases | 5 delivery phases + 1 docs phase |
| Progress | 0 / 56 todos |

## How to Use This Plan

- The **frontmatter todos** are the task list and progress tracker; IDs are `p{N}-slug` and stable.
- Each phase section below gives the **how**: files, key code, tests, success criteria. Technical detail lives in the spec; sections cite spec § numbers instead of repeating it.
- Every phase starts with an `*-approval-gate` todo. **Do not start a phase's code todos until its gate is approved** (AGENTS.md "Approval required before").
- Each phase is independently shippable: defaults keep earlier behavior until the new path is switched on.
- Shell is Windows PowerShell 5.1 — never chain with `&&` / `||`.

## Technology Stack

Python 3.11, async throughout, uv workspace, FastAPI / MCP streamable HTTP, pydantic v2, httpx, pyyaml, rdflib, `provider_contracts` (VectorStore: Qdrant local / Qdrant Cloud / pgvector; Embedding: local bge / Bedrock / Gemini; Secrets; Audit; Telemetry). No new third-party libraries.

## Architecture Overview

Pipeline (refresh CLI / scheduler) fetches specs, builds unified operations, and indexes vectors; runtime (MCP / Agent API) reads only local files plus the vector store and resolves credentials per application. See spec §2.

```text
repositories.yaml ─► spec refresh ─► openapi/<env>/current.json ─► operations.json ─► VectorStore api_ops_<env>_<model8>
                                                                     │
runtime: OperationCatalog + Resolver + ApiSearchService + invoke_sse_api(CredentialBroker, breaker) ─► /ready per app
```

## Implementation Phases

### Phase 1 — Registry, spec cache, catalog from cache (no boot network)

**Todos in this phase**: `p1-*` · **Stories**: US1, US3 (P1) · **Reqs**: FR-001, FR-002, FR-007, FR-008, FR-016, FR-019, FR-022, NFR-002, NFR-007

1. `p1-approval-gate` — G1, G2, G3 (spec §1.1).
2. `p1-settings` — `EakgConfig.environment: Literal["local","dev","stage","prod"] = "local"`, `SseConfig.catalog_source: Literal["auto","registry","swagger_links","fixture"] = "auto"`.
3. `p1-registry-schema` — spec §4.1, §9.1. Legacy YAML must load with zero diff on save when no new fields are set.
4. `p1-app-mapping` — spec §4.1 Application mapping (FR-022). Same row holds source and live address. TAAC fills a blank address and does not invent a repo.
5. `p1-registry-validate` — every rule/code in spec §4.1 table; CLI prints JSON issues, exit 2 when any blocking issue.
6. `p1-taac-import` — spec §9.1; fill-blank address only; never writes `git_url`; `--dry-run` writes nothing.
7. `p1-spec-cache` — spec §3.6, §4.2; files under `repos/<id>/openapi/<env>/`.
8. `p1-onboard-wire` — spec §9.1; closes the "enrich_interface without base_url" gap.
9. `p1-catalog-from-cache` — spec §2.3 C, §9.1; registry mode builds `OpenApiCatalog` from `SpecSource` with no `httpx` client.
10. `p1-swagger-links-helper` — `resolve_swagger_links(sse: SseConfig)`.
11. `p1-local-fixtures` — synthetic only, hosts `127.0.0.1` / `*.example.invalid`.

**Tests** (`p1-tests`): spec §14.1 P1 rows. Files: `packages/eakg/tests/test_registry_env.py`, `test_spec_cache.py`, `test_registry_import.py`, `packages/sse/tests/test_registry_catalog_mode.py`.

**Success criteria**: registry-mode boot with 3 local apps makes zero HTTP requests; one failing app's spec leaves others discoverable and is listed with `status=failed`; `make demo` green with no cloud creds; legacy swagger-link `.env` behaves as before.

### Phase 2 — Unified operation record, id join, bind fix

**Todos in this phase**: `p2-*` · **Stories**: US2 (ids), US5 · **Reqs**: FR-006, FR-012, FR-013, FR-020, SC-007

1. `p2-approval-gate` — G4.
2. `p2-project-scaffold` — spec §6.3 layout; dependency direction `common ← sse, eakg ← api_index ← tools`.
3. `p2-normalize-join` — spec §3.1, §3.2.
4. `p2-unified-record` — spec §4.3; `operations.json` under `enterprise/api_index/<env>/`.
5. `p2-capability-app-id` — `CapabilityRecord.application_id: str | None = None`.
6. `p2-resolver` — spec §3.3, §9.2.
7. `p2-bind-fix` — spec §9.2; `capability_id=GetLoanSummary` and `get_loan_summary` both bind to `loanservices:getLoanSummary`.
8. `p2-mismatch-report` — spec §9.2.

**Tests** (`p2-tests`): spec §14.1 P2 rows in `projects/LoanOps.ApiIndex/packages/api_index/tests/test_records.py`, `test_resolver.py`; bind tests in `projects/LoanOps.McpServer/packages/mcp_server/tests/`.

**Success criteria**: every read-only capability with a joined record is callable by name (SC-007 on current shards); cross-app duplicate names return an ambiguity error naming both apps; mismatch report runs offline.

### Phase 3 — Vector index, incremental reindex, two-stage search

**Todos in this phase**: `p3-*` · **Stories**: US2, US7, US8 · **Reqs**: FR-004, FR-015, FR-017, FR-018, NFR-003

1. `p3-approval-gate` — G5, G6.
2. `p3-vector-filter-contract` — spec D6; change lives in `../provider_contracts`.
3. `p3-settings` — `ApiIndexConfig`.
4. `p3-indexer` — spec §3.4, D7.
5. `p3-keyword-index` — spec §3.5.
6. `p3-two-stage-search` — spec §3.5, §5.1.
7. `p3-refresh-cli` — spec §5.3, §9.6.

**Tests** (`p3-tests`): spec §14.1 P3 rows in `test_indexer.py`, `test_search.py`; contract test in `provider_contracts`.

**Success criteria**: second `refresh all` embeds 0 ops; `application` filter returns only that app; vector-store outage degrades to sidecar with a visible label; `API_INDEX__ENABLED=false` keeps Phase 2 behavior.

### Phase 4 — CredentialBroker, per-app invoke, registry allow-list, clear access errors

**Todos in this phase**: `p4-*` · **Stories**: US4, US3 #3/#4 · **Reqs**: FR-009, FR-010, FR-011, FR-020, FR-021, NFR-004, NFR-010, SC-006, SC-008

1. `p4-approval-gate` — G7, G8.
2. `p4-broker-protocol` — spec §6.2.
3. `p4-broker-impls` — spec §6.2, §3.7, §9.4.
4. `p4-broker-contract-tests` — `projects/LoanOps.Common/packages/common/providers/contract_tests/test_credential_broker.py`.
5. `p4-invoke-per-app` — spec §6.4, §3.8.
6. `p4-allowlist-registry` — spec §9.4.
7. `p4-tool-payload` — spec §5.1.
8. `p4-audit-live-read` — spec §6.4, §12.
9. `p4-spec-fetch-broker` — spec §9.4.
10. `p4-smoke-rerun` — operator-run against dev; record in `logs.md`.

**Tests** (`p4-tests`): spec §14.1 P4 rows in `packages/sse/tests/test_invoke_per_app.py` and contract tests.

**Success criteria**: no test observes app A's token on app B's host; `no_access` messages name the application; zero generic "unauthorized" strings in the SC-006 replay; every invoke emits one `sse.live_read` audit event.

### Phase 5 — Per-app health, metrics, scheduled refresh, scale validation

**Todos in this phase**: `p5-*` · **Stories**: US6, US7, US3, US9 (env in health) · **Reqs**: FR-008, FR-014, FR-015, FR-016, NFR-001–NFR-004, SC-002–SC-005

1. `p5-approval-gate` — G9, G10.
2. `p5-health-model` — spec §9.5.
3. `p5-ready-per-app` — spec §5.2.
4. `p5-metrics` — spec §9.5.
5. `p5-scheduler` — spec §9.6.
6. `p5-scale-fixture` — spec §14.2; seeded, synthetic, no PII.
7. `p5-scale-tests` — spec §14.2 table.

**Success criteria**: scale suite passes at story targets (pending Q2 confirmation); `/ready` shows correct state for healthy / stale / unindexed / access-failing / unreachable apps.

### Phase 6 — Documentation and graph upkeep

**Todos in this phase**: `p6-*`

`TASKS.md`, `logs.md`, `ARCHITECTURE.md`, `AGENTS.md` module layout (new `LoanOps.ApiIndex`, 11 provider categories), `CONTEXT.md` env vars, `decisions.md` ADR status; final `graphify update .`. Per-phase `logs.md` / `TASKS.md` entries may be made as each phase completes; `p6-*` closes them out.

## Timeline Summary

| Phase | Size | Depends on |
|---|---|---|
| P1 | M (3–4 days) | G1–G3 |
| P2 | M (3 days) | P1, G4 |
| P3 | L (4–5 days) | P2, G5, G6 |
| P4 | M (3–4 days) | P1 (P2 for public ids in payload), G7, G8 |
| P5 | M (3–4 days) | P3, P4, G9, G10 |
| P6 | S (0.5 day) | each phase |

P4 can run in parallel with P3 after P2.

## Success Criteria

Story SC-001 … SC-010 mapped to tests in spec §14. Plan is complete when all todos are `completed`, the scale suite passes at confirmed targets, and `make demo` passes with zero cloud credentials.

## Risk Mitigation

| Risk | Mitigation |
|---|---|
| Approvals stall | Phases ordered so P1/P2 need only schema + 2 env vars; defaults keep legacy behavior |
| App teams do not grant access | Clear `no_access` messaging + `/ready` visibility; not a blocker for delivery |
| Suffix join mis-matches | `join` field + report; ambiguous never callable; OQ-8 extractor route fix |
| Shortlist hurts recall | Keyword-exact apps always included; SC-002 benchmark gates tuning |
| `provider_contracts` change lands late | Post-filter in `ApiSearchService` keeps correctness without provider filter support |
| Shared token sent too widely | Explicit `CREDENTIALS__STATIC_SHARED_APPS` opt-in + origin binding |

## Dependencies

Spec §17. External: application teams (specs, access), identity decision (OQ-1), `provider_contracts` release for G6.

## Rollout Plan

1. P1 ship with `SSE__CATALOG_SOURCE=auto` — dev machines with swagger links unchanged; demo switches to registry.
2. Run `registry import-taac --env dev`, fill audiences, `refresh all --env dev`.
3. P3: enable `API_INDEX__ENABLED=true` in dev after index build; compare benchmark vs sidecar.
4. P4: set `APP_TOKEN_<APPID>` per app or `CREDENTIALS__STATIC_SHARED_APPS`; rerun smoke.
5. P5: enable scheduler (or external cron); stage/prod registry entries.

## Post-Implementation

- Track `catalog_health` counts weekly; drive `eakg_only`/`ambiguous` to zero via extractor route composition (OQ-8).
- Pick a non-static broker once OQ-1 is decided.

## Final Validation

```powershell
uv run mypy --strict projects/LoanOps.Common projects/LoanOps.Sse projects/LoanOps.Eakg projects/LoanOps.ApiIndex projects/LoanOps.Tools projects/LoanOps.McpServer
uv run pytest projects
uv run pytest projects/LoanOps.Common/packages/common/providers/contract_tests
uv run pytest projects/LoanOps.ApiIndex -m scale
uv run python scripts/check_project_refs.py
rg "from provider_contracts\.\w+\.\w+ import" projects --glob "!**/common/providers/**"
rg -n "os\.environ|os\.getenv" --glob "*.py" projects --glob "!**/settings.py" --glob "!**/tests/**"
make demo
graphify update .
```

Both `rg` commands must return no matches.

## Code Review Checklist

- [ ] No concrete provider imports outside `packages/common/providers/`
- [ ] No `os.environ` / `os.getenv` outside `settings.py`
- [ ] No new env var / provider / threshold without its gate recorded as approved in Notes
- [ ] GET/HEAD only; no request body; `callable ⇒ read_only`
- [ ] Tokens are `SecretStr`, never logged, audited, or returned
- [ ] Per-call origin binding enforced before cache lookup and before sending a token
- [ ] Every factual tool result carries `citation` (`tool:` prefix)
- [ ] Fixtures synthetic only; hosts `*.example.invalid` / loopback
- [ ] Async throughout; `mypy --strict` clean; no untyped `Any` without justified ignore

## Sign-off

| Role | Name | Date |
|---|---|---|
| Product owner | (OQ-6) | |
| Technical lead | (OQ-6) | |
| Approver for G1–G10 | Repo owner `mohit-bohra-dev` until OQ-6 names a product owner / technical lead | |

## Quick Command Reference

```powershell
uv run python -m packages.eakg registry validate --env local
uv run python -m packages.eakg registry import-taac --env dev --dry-run
uv run python -m packages.api_index.refresh all --env local
uv run python -m packages.api_index report --env local --json
Invoke-RestMethod http://127.0.0.1:8001/ready
```

## Notes

- 2026-10-08: Plan authored from story + ADR-024. Story `[NEEDS CLARIFICATION]` items plus technical questions are tracked as spec §19 OQ-1 … OQ-9 and are not resolved by this plan.
- 2026-10-08: Design review enterprise-app-scale-1 (fail, 3.8) applied. G1–G3 approver until OQ-6 is named: repo owner `mohit-bohra-dev`.
- 2026-10-09: FR-022 application mapping. One registry row joins optional source (`git_url`) to per-env live address (`base_url`). TAAC fills a blank address and does not invent a repo.
- 2026-10-09: G1–G3 approved by starting Phase 1 (repo owner). ADR-024 Accepted. Done: settings, registry schema, mapping, validate, TAAC import. Next: spec cache, onboard wire, catalog-from-cache.
- 2026-10-09: API index store is pgvector (`VECTOR_STORE__PROVIDER=pgvector` in `.env.example`, ADR-024, spec D6). `VectorStoreConfig.provider` default stays `qdrant` so a machine without Postgres still boots the old demo. Spec cache, onboard/`spec-refresh`/`sync_nightly`, registry catalog (no swagger at boot), local fixtures, and tests are in. `p1-quality-gates` still open (`make demo`, contract suite, grep gates).
- 2026-10-09: G4 approved (repo owner). Phase 2 starts: scaffold `projects/LoanOps.ApiIndex`.
- 2026-10-09: Phase 2 core done — `build_operations` → `operations.json`, `OperationResolver`, bind → `public_id`, `CapabilityRecord.application_id` via `belongsToApp`, `api_index report` / `build`, readiness `catalog_health`. `p2-quality-gates` still open (`make demo`).
- Approval decisions for G1–G10: (record here).
