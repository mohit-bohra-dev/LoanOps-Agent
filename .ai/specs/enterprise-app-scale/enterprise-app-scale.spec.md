# Technical Specification: Enterprise App Scale

**Story**: [Enterprise App Scale — User Stories](./enterprise-app-scale.story.md)
**Architecture decision**: [ADR-024 — Enterprise app scale: registry-driven API catalog](../../../decisions.md) (status: Proposed — this spec implements it)
**Created**: 2026-10-08
**Status**: Draft
**Version**: 1.2.0 (application mapping, FR-022)

> Requirements are cited by their stable IDs from the story (`FR-`, `NFR-`, `SC-`) and are not restated here. This document specifies **how** they are met.

---

## 1. Overview

LoanOps today discovers and calls enterprise APIs through an `OpenApiCatalogService` that serially fetches a hand-kept list of swagger URLs (`SSE__SWAGGER_LINKS`) at first load, sends one bearer (`SSE__API_KEY`) to every host, ranks operations with a pure-Python cosine loop over a JSON sidecar, and keeps EAKG capability ids (`GetLoanSummary`, path `/{id}/Summary`) disjoint from SSE catalog ids (`loanservices:getLoanSummary`, path `/api/Loans/{loan_id}/Summary`). ADR-024 replaces this with:

1. **One registry** (`data/eakg/registry/repositories.yaml`) that lists applications plus the application mapping (FR-022): optional GitLab `git_url`, TAAC `service_url_key`, and per-environment base URL, auth audience and spec override (FR-001, FR-019).
2. **Pipeline-only spec fetch** — onboarding / refresh fetches and caches each application's OpenAPI document; the MCP / Agent process builds its catalog from the cache with **zero network at boot** (NFR-002, FR-007).
3. **A unified operation record** keyed `application|METHOD|normalized_path`, merging OpenAPI + EAKG, with one stable public id that capability ids and operation ids both resolve to (FR-006, FR-012, FR-013).
4. **A vector index** in the existing `VectorStore` provider (namespace per environment), built incrementally at refresh time, searched in two stages (app shortlist → operation ranking) with metadata filters (FR-004, FR-017, FR-018, NFR-003).
5. **A new `CredentialBroker` provider** resolving a token per application/audience, so each live read uses that application's access and failures are classified as "no access" vs "unavailable" (FR-009, FR-010, FR-011, NFR-010).
6. **Per-application health** on `/ready`, metrics, scheduled incremental refresh and per-app fail isolation (FR-008, FR-014, FR-015, FR-016, NFR-004).

Delivery is five independently shippable phases (see [plan](./enterprise-app-scale.plan.md)). Every phase keeps `make demo` working with zero cloud credentials (NFR-007).

### 1.1 Approval gates (must be cleared before the gated phase starts)

AGENTS.md requires human approval for new env vars, new provider protocols, new ADRs/architecture changes, schema-breaking migrations and eval-threshold changes. This spec **proposes**; nothing below is approved yet.

**Approver (precondition for `p1-approval-gate`)**: TBD — repo owner (`mohit-bohra-dev`) until a product owner / technical lead is named. OQ-6 stays open; until it is answered, every gate below routes to the repo owner, and the decision is recorded in the plan's Notes.

| Gate | What needs approval | Phase | Section |
|---|---|---|---|
| G1 | Accept ADR-024 (currently Proposed) | before P1 | §7 |
| G2 | Registry schema additions (`lifecycle`, `service_url_key`, `environments`, optional `git_url`) — additive, backward compatible | P1 | §5.1 |
| G3 | New env vars `EAKG__ENVIRONMENT`, `SSE__CATALOG_SOURCE` | P1 | §15 |
| G4 | New uv workspace project `projects/LoanOps.ApiIndex` (`loanops-api-index`) | P2 | §7 D3 |
| G5 | New env vars `API_INDEX__ENABLED`, `API_INDEX__NAMESPACE_PREFIX`, `API_INDEX__APP_SHORTLIST_SIZE` | P3 | §15 |
| G6 | `VectorStore` contract extension in `provider_contracts`: list filter value = any-of, `supports_any_of_filter` flag, idempotent namespace-resolved `ensure_namespace` | P3 | §7 D6 |
| G7 | New provider protocol `CredentialBroker` (new provider category; 14th `get_*` factory in `factory.py`) | P4 | §6.2 |
| G8 | New env vars `CREDENTIALS__PROVIDER`, `CREDENTIALS__STATIC_SHARED_APPS` and secret names `APP_TOKEN_<APPID>` | P4 | §15 |
| G9 | New env vars `API_INDEX__STALE_AFTER_HOURS`, `API_INDEX__SCHEDULER_ENABLED` | P5 | §15 |
| G10 | New eval/benchmark thresholds (SC-002 top-5 ≥ 90 %, SC-003 p95 < 1.5 s, SC-004 ready < 10 s) — values pending story Q2 | P5 | §14.4 |

---

## 2. Architecture

### 2.1 High-level

```text
                        ┌──────────────────── PIPELINE (offline / scheduled) ────────────────────┐
 TAAC client config ──► registry_import ──► repositories.yaml (single source of truth, per env) │
                        │                          │                                            │
                        │                          ▼                                            │
                        │   eakg onboard / spec-refresh (per app, isolated, bounded concurrency) │
                        │     clone+extract (EAKG)   fetch_spec(base_url, CredentialBroker)      │
                        │            │                         │                                 │
                        │            ▼                         ▼                                 │
                        │   repos/<id>/interface.json   repos/<id>/openapi/<env>/<hash>.json     │
                        │                              repos/<id>/openapi/<env>/current.json     │
                        │            └──────────┬──────────────┘                                 │
                        │                       ▼                                                │
                        │   api_index build: UnifiedOperation join (app|METHOD|normalized_path)  │
                        │         enterprise/api_index/<env>/operations.json                      │
                        │                       ▼                                                │
                        │   api_index reindex (incremental by text_hash) ──► VectorStore          │
                        │         namespace api_ops_<env>_<model8>   + JSON sidecar fallback      │
                        └───────────────────────────────────────────────────────────────────────┘
                                                │ files + vector store (no swagger fetch)
                        ┌──────────────── RUNTIME (MCP :8001 / Agent API :8000) ─────────────────┐
                        │ build_modular_tools_client                                              │
                        │   OperationCatalog (operations.json + registry targets)  ── /ready      │
                        │   ApiSearchService (2-stage vector + keyword blend, filters)            │
                        │   OperationResolver (public_id / uid / capability_id / bare name)       │
                        │   invoke_sse_api(target app) ── CredentialBroker.get_token(app, aud)    │
                        │        origin bound to app ── circuit breaker per app ── audit event    │
                        └───────────────────────────────────────────────────────────────────────┘
```

### 2.2 Component design

| Component | Location | Responsibility | Interface |
|---|---|---|---|
| `RepositoryRecord` + `AppEnvironment` | `projects/LoanOps.Eakg/packages/eakg/registry.py` (modified) | Single app registration incl. per-env target | dataclasses, `RepositoryRegistry.list_active(env)` |
| `registry_validate` | `projects/LoanOps.Eakg/packages/eakg/registry_validate.py` (new) | Field + env-mismatch validation | `validate_registry(registry) -> dict[str, list[RegistryIssue]]`, `blocking_issues(rec, env)` (§4.6) |
| `registry_import` | `projects/LoanOps.Eakg/packages/eakg/registry_import.py` (new) | Seed `environments[env]` from TAAC `ServiceUrls` / `Auth0.Api.Identifier` | `import_taac(registry, taac_path, env, *, dry_run) -> ImportReport` |
| `spec_cache` | `projects/LoanOps.Eakg/packages/eakg/spec_cache.py` (new) | Fetch + cache spec per app/env; last-good retention | `refresh_spec(...) -> SpecRefreshResult`, `read_current_spec(...)` |
| `onboard_repository` | `projects/LoanOps.Eakg/packages/eakg/onboard.py` (modified) | Calls `refresh_spec` with `base_url`; passes spec to `enrich_interface` | unchanged signature |
| `SpecSource` + registry mode | `projects/LoanOps.Sse/packages/sse/loader.py` (modified) | Build `OpenApiCatalog` from pre-fetched docs, no network | `OpenApiCatalogService(spec_sources=...)` |
| `registry_catalog` | `projects/LoanOps.Tools/packages/tools/registry_catalog.py` (new) | Compose registry + `ShardStore` → `SpecSource` / `AppTarget` lists | `build_spec_sources(cfg)`, `build_app_targets(cfg)` |
| `UnifiedOperation`, join, resolver | `projects/LoanOps.ApiIndex/packages/api_index/` (new project) | Merge OpenAPI + EAKG; alias resolution; mismatch report | §6.3 |
| `indexer` | `packages/api_index/indexer.py` (new) | Incremental embed + upsert/delete in `VectorStore` | `reindex(...) -> IndexReport` |
| `ApiSearchService` | `packages/api_index/search.py` (new) | Two-stage retrieval + keyword blend + filters + fallback | `search(query, *, limit, application_ids, permission)` |
| `AbstractCredentialBroker` | `projects/LoanOps.Common/packages/common/providers/credential_broker.py` (new) | Provider protocol + static/mock/caching impls | §6.2 |
| `get_credential_broker` | `projects/LoanOps.Common/packages/common/providers/factory.py` (modified) | DI factory by `CREDENTIALS__PROVIDER` | `-> AbstractCredentialBroker` |
| `invoke_sse_api` | `projects/LoanOps.Sse/packages/sse/invoke.py` (modified) | Per-app token, origin binding, outcome classification, breaker | §6.4 |
| `AppHealthService` | `packages/api_index/health.py` (new) | Per-app health aggregation for `/ready` | `snapshot() -> HealthSnapshot` |
| `refresh` CLI | `packages/api_index/refresh.py` (new) | `app` / `all` / `nightly` orchestration | `python -m packages.api_index.refresh ...` |

### 2.3 Data flow

**A. Registration → discoverable (FR-001, FR-002, US1)**

1. Operator edits `repositories.yaml` (or runs `python -m packages.eakg registry import-taac --env dev`) and runs `python -m packages.eakg registry validate`.
2. `python -m packages.api_index.refresh app --id <id>` (or the scheduler, §9.6):
   a. `refresh_spec` → resolves `environments[env]`, gets token via `CredentialBroker` (P4; in P1–P3 `EAKG__LIVE_SPEC_TOKEN`, sent only to apps on the shared TAAC audience — §3.6), tries `spec_path` then `SPEC_CANDIDATES`, writes `openapi/<env>/<sha12>.json` + `current.json`.
   b. If `git_url` set: EAKG extract (existing) with the fetched spec passed to `enrich_interface`.
   c. `build_operations(env)` writes `enterprise/api_index/<env>/operations.json`.
   d. `reindex(env)` embeds only changed `text_hash` rows, upserts, deletes removed rows.
3. Running MCP detects the catalog fingerprint change on the next tool call and swaps its in-memory catalog (no restart, no network). The fingerprint is built in **P1** from `(mtime_ns, size)` of the registry YAML plus every active app's `openapi/<env>/current.json`; **P2** adds `operations.json`. `ModularToolsClient` re-stats at most once per `_RELOAD_CHECK_INTERVAL_S = 5.0` (code constant), so a reload costs ≤ 31 `stat` calls at 30 apps. A reload that fails keeps the previous catalog and adds `/ready` warning `catalog_reload_failed` (FR-002, US1 #1).

**B. Question → cited answer (FR-004, FR-005, US2)**

1. `search_sse_apis(query, limit, application?, permission?)` → `ApiSearchService.search`.
2. Stage 1 probe (vector, top 60, `read_only=True`) → app scores → shortlist (≤ `APP_SHORTLIST_SIZE` + keyword-exact apps).
3. Stage 2 (vector, `application_id ∈ shortlist`) ∪ keyword candidates → blended rank `0.7·cos + 0.3·kw` → top `limit`.
4. Output lines carry `public_id`, application label and id, method, path (FR-006). When no hit clears the confidence floor (§3.5), the output header says so (US2 #4).
5. `call_sse_api(operation_id=<public_id>|capability_id=...)` → `OperationResolver` → `invoke_sse_api(target)` → JSON with `application_id`, `outcome`, `citation="tool:call_sse_api:<public_id>"`. A raw `method`+`path` call in registry mode also needs `application` (§6.4).

**C. Boot (NFR-002, US3)**

`build_modular_tools_client` resolves the catalog source (D1, `resolve_catalog_source`), then reads registry YAML + `operations.json` (or, if absent, the per-app `current.json` specs) from local disk; builds `OperationCatalog`, `OperationResolver`, keyword index. No HTTP. Vector store is contacted lazily on first search; failure ⇒ sidecar fallback.

---

## 3. Algorithms & Logic

### 3.1 Path normalization

```python
_PARAM = re.compile(r"^\{[^}]*\}$|^:[A-Za-z_]\w*$")

def normalize_path(path: str, *, controller: str | None = None) -> str:
    raw = path.split("?", 1)[0].strip()
    segs = [s for s in raw.replace("\\", "/").split("/") if s]
    out: list[str] = []
    for s in segs:
        if s == "[controller]" and controller:
            s = controller.removesuffix("Controller")
        out.append("{}" if _PARAM.match(s) else s.lower())
    return "/" + "/".join(out)
```

- `/api/Loans/{loan_id}/Summary` → `/api/loans/{}/summary`; `/{id:int}/Summary` → `/{}/summary`.
- O(L) in path length. Validation: result always starts with `/`, contains no empty segments, never contains `?`.

### 3.2 Unified id and join (FR-006, FR-012, FR-013)

```text
uid(app, method, np)  = f"{app}|{method.upper()}|{np}"
public_id(app, op)    = f"{app}:{op.operationId}"           if operationId unique within app
                      = f"{app}:{METHOD}_{slug(np)}"        otherwise (slug = existing catalog._slugify)
```

`public_id` deliberately equals today's SSE catalog id format (`loanservices:getLoanSummary`) so existing clients/tests keep working.

```text
build_operations(env):
  for app in registry.list_active(env):
      spec = read_current_spec(app, env)            # may be None → app degraded, no ops
      oa_ops  = parse_openapi_document(spec, app.application_id, app.application, base_url)
      ea_ops  = interface.operations (if interface exists)   # ApiOperationFact dicts
      by_uid  = {uid(o): o for o in oa_ops}                    # O(n_oa)
      buckets = group oa_ops by (method, last_literal_segment(np))   # O(n_oa)
      for e in ea_ops:                                          # O(n_ea · k), k = bucket size
          np_e = normalize_path(e.http_path, controller=e.controller)
          if uid(app, e.method, np_e) in by_uid:       join = "exact"
          else:
              cands = [o for o in buckets[(e.method, last_literal(np_e))]
                       if segs(np(o)).endswith(segs(np_e)) and len(segs(np(o))) > len(segs(np_e))]
              if len(cands) > 1:
                  stem = e.controller.removesuffix("Controller").lower()
                  cands = [o for o in cands if stem in segs(np(o))[:-len(segs(np_e))]]
              join = "suffix" if len(cands) == 1 else ("ambiguous" if cands else "eakg_only")
          merge e into the matched record (code_unit, permission, authz_source, evidence[:3], eakg key)
      remaining oa_ops with no EAKG match → join = "openapi_only"
```

Complexity per app: O(n_oa + n_ea·k) time, O(n_oa) space; k is typically 1–3. At 30 apps × ~170 ops the full build is < 50 ms CPU.

Merge rules:

| Field | Source of truth |
|---|---|
| `method`, `path`, `parameters`, `summary`, `description`, `tags`, `has_request_body` | OpenAPI (callable surface) |
| `code_unit` (`<Controller>.<Action>`), `permission` (`authz_policy`), `authz_source`, `evidence` | EAKG |
| `read_only` | `method ∈ {get, head}` **and** `not has_request_body` **and** `eakg.read_only is not False` |
| `has_request_body` (GET/HEAD) | `True` only for an explicit OpenAPI 3 `requestBody` or a Swagger 2 parameter `in: body` / `in: formData`. A Swagger 2 `consumes` list alone is **ignored** for GET/HEAD, so legitimate GETs stay callable. Today `parse_openapi_document` sets `has_request_body = True` for any op with `consumes`; P2 changes that rule in `packages/sse/catalog.py` (other methods unchanged) |
| `capability_ids` | `CapabilityRecord`s with `application_id == app` and `operation_id == eakg key` (normalized compare) |

`eakg_only` and `ambiguous` records are **not callable** (no trustworthy OpenAPI path) and are reported (FR-013). `openapi_only` records are callable.

### 3.3 Alias resolution (FR-012, US5)

```text
key(s) = re.sub(r"[^a-z0-9]", "", s.lower())

aliases(rec) = { rec.public_id, rec.uid,                       # exact, case-insensitive
                 f"{app}:{key(operationId)}", f"{app}:{key(eakg_key)}",
                 key(operationId), key(eakg_key), *map(key, capability_ids) }

resolve(ref, application_id=None):
  hits = alias_map.get(normalize_ref(ref), [])                  # O(1)
  if application_id: hits = [h for h in hits if h.app == application_id]
  len(hits) == 1 → Resolved(rec)
  len(hits) == 0 → NotFound(suggestions = top 3 keyword matches)
  len(hits) > 1  → Ambiguous(candidates=[public_id, application label] …)   # never guess (FR-006)
```

`get_loan_summary`, `GetLoanSummary`, `getLoanSummary`, `loanservices:getLoanSummary` all resolve to the same record when unique. Build O(Σ aliases); lookup O(1).

### 3.4 Incremental reindex (FR-015, US7)

```text
reindex(env, records, store, embedder, manifest_path):
  model_id   = f"{probe.model}:{probe.dimensions}"              # one embed() of "probe"
  ns         = f"{prefix}_{env}_{sha256(model_id)[:8]}"
  manifest   = load(manifest_path) or empty
  if manifest.namespace != ns:                                   # model change ⇒ full rebuild
      todo = all callable records; stale_ns = manifest.namespace
      await store.ensure_namespace(ns, vector_size=dims)         # G6: idempotent, provider resolves ns → collection
  else:
      todo = [r for r in callable if manifest.entries.get(r.uid, {}).text_hash != text_hash(text(r))]
  for batch in chunks(todo, 64): vectors = await embedder.embed_batch(texts)   # concurrency 4 batches
      await store.upsert([VectorDocument(id=point_id(env, r.uid), embedding=v, metadata=meta(r), text=t)], namespace=ns)
  removed = manifest.entries.keys() - {r.uid for r in callable}
  await store.delete([point_id(env, u) for u in removed], namespace=ns)
  write manifest atomically (tmp + os.replace) with namespace=ns, entries
  if stale_ns: await store.delete(old ids, namespace=stale_ns)   # after pointer swap
  write sidecar (§3.6)
```

- `point_id(env, uid) = str(uuid5(NAMESPACE_URL, f"loanops:{env}:{uid}"))` — valid for Qdrant, pgvector, AI Search; `uid` kept in metadata.
- `text(r)` = existing `packages.sse.semantic.operation_text` extended with `code_unit` and capability ids; `text_hash` = existing `text_hash` (sha256[:16]).
- Cost: O(changed) embed calls; unchanged nightly run = 1 probe embed + manifest diff (O(n)).
- Manifest: `<shard_dir>/enterprise/api_index/<env>/index.manifest.json`. Needed because the `VectorStore` contract has no scan/list API.
- `ensure_namespace(namespace, vector_size)` is part of the G6 contract change. Each provider maps `namespace` to its physical collection with the **same** resolution it uses in `upsert` / `search` / `delete` (Qdrant: `_resolve_collection(namespace)` = `{collection}_{namespace}`; mock: the namespace itself). It is a no-op when the collection exists with that vector size, and raises `ProviderConfigError` when it exists with a different size. `api_index` never computes a physical collection name, so no provider-specific knowledge leaks out of `provider_contracts`.

### 3.5 Two-stage search (FR-004, FR-017, FR-018, NFR-003)

```text
search(query, *, limit=15, application_ids=None, permission=None):
  q = query.strip(); if not q: return SearchOutcome(hits=[], backend=..., confident=False)
  if model_mismatch: return keyword_or_sidecar_search(...)       # RC-018 guard, see below
  qvec = await embed_cached(q)                                   # LRU(1024) keyed by q.lower()
  base = {"read_only": True}
  if application_ids: shortlist = application_ids
  else:
     probe = await vs.search(qvec, namespace=ns, top_k=60, filter=base)
     score[a] = mean(top3(scores of a in probe))
     kw_apps  = apps owning an op whose key(operationId|eakg_key) == key(q-token) (exact name hit)
     shortlist = top APP_SHORTLIST_SIZE apps by score  ∪ kw_apps        (cap 8)
  if vs_any_of:                                                  # provider advertises list = any-of (G6)
      vec_hits = await vs.search(qvec, namespace=ns, top_k=max(4*limit, 40),
                                 filter={**base, "application_id": shortlist})
  else:                                                          # pre-G6 provider: never send a list value
      vec_hits = await vs.search(qvec, namespace=ns, top_k=max(8*limit, 120), filter=base)
  vec_hits = [h for h in vec_hits if post_filter(h.metadata)]   # defensive: never trust provider filter
  kw = keyword_index.score(q, apps=shortlist, limit=3*limit)     # uid → kw ∈ [0,1]
  cand = {h.uid: 0.7*h.score for h in vec_hits}
  for uid, k in kw.items(): cand[uid] = cand.get(uid, 0) + 0.3*k
  hits = top `limit` by score (tie-break public_id) mapped to UnifiedOperation
  return SearchOutcome(hits, backend, confident = bool(hits) and hits[0].score >= _MIN_CONFIDENT_SCORE)
```

- **Any-of capability (RC-004)**: `vs_any_of = getattr(vector_store, "supports_any_of_filter", False)`. G6 adds the class attribute `supports_any_of_filter: ClassVar[bool] = True` to every provider that implements list = any-of. Today's Qdrant provider maps every filter value to `MatchValue(value=v)`, so a list value would fail validation, and pgvector ignores `filter`. Without the flag the service omits the `application_id` key, over-fetches (`top_k = max(8*limit, 120)`) and relies on `post_filter`. The scalar `read_only` filter is safe on every provider. P3 therefore works before the `provider_contracts` release; it only gets cheaper after it.
- **No confident match (US2 #4)**: `_MIN_CONFIDENT_SCORE = 0.35` on the blended score (code constant, tuned with the SC-002 benchmark, not an eval threshold). Keyword-only mode uses `kw ≥ 0.5` on the top hit. When `confident` is false, `search_sse_apis` prints `No confident match for "<query>" — the operations below are the closest, and may not answer the question.` above any hits, and the tool description tells the agent to say it found no matching operation rather than guess.
- **Embed-model guard (RC-018)**: on first search (and after each catalog reload) the service compares the live embedder's `f"{model}:{dimensions}"` with `manifest.embed_model_id` (the input to the namespace fingerprint, §3.4). On mismatch it sets `model_mismatch = True`, skips the vector stage (sidecar if its `embed_model_id` matches, else keyword only), labels the output with the fallback backend, and `/ready` gets warning `embed_model_mismatch` with both ids. It never sends a wrong-dimension vector to the store.

- `post_filter`: `read_only is True`, `application_id ∈ shortlist`, and when `permission` given or `CAPABILITY_KG__ENFORCE_PERMISSIONS=true`, `permission ∈ allowed set` (existing `CAPABILITY_KG__ALLOWED_PERMISSIONS`).
- Keyword index: built once per catalog load; token → postings set of uids from `operation_text` tokens (same tokenizer as `catalog.search_operations`, camelCase split). `kw = |matched query tokens| / |query tokens|`. Build O(T), query O(Σ postings of query tokens).
- Vector cost: 2 ANN queries, O(log N) each in pgvector ivfflat. Python work O(K) with K ≤ 260 (≤ 300 in the pre-G6 over-fetch path).
- Fallback chain: vector store error → in-memory cosine over sidecar vectors (existing `search_operations_semantic` path, labelled `(fallback: local vector sidecar)`) → embed error → keyword only (existing label).

### 3.6 Spec refresh with last-good retention (FR-007, FR-016)

```text
refresh_spec(rec, env, store, token_source):
  t = rec.environments.get(env); if t is None or not t.enabled → status "not_registered_in_env"
  doc, url, err = None, None, None
  if t.spec_fixture: doc = load_fixture_spec(t.spec_fixture); url = t.spec_fixture
  else:
     token = await token_source(rec.application_id, t.auth_audience)   # P4 broker; P1–P3 interim source below
     doc, url, err = await fetch_spec_with_source(t.base_url, token, paths=[t.spec_path] or SPEC_CANDIDATES,
                                                  timeout=SPEC_HTTP_TIMEOUT_S, same-origin redirects only)
  ptr = read current.json (may be None)
  if doc is valid OpenAPI:
      h = sha256(canonical_json(doc))[:12]
      write openapi/<env>/<h>.json if absent; prune to newest 3
      ptr = {spec_hash: h, source_url: url, fetched_at: now, status: "ok", last_error: None, changed: h != old}
  else:
      ptr = {**(ptr or {}), status: "failed", last_error: err[:300], last_attempt_at: now}   # keeps last good spec_hash
  atomic write current.json
```

**Timeouts (single source)**: `SPEC_HTTP_TIMEOUT_S = 20.0` is the timeout of each HTTP request (one candidate path). `SPEC_APP_BUDGET_S = 30.0` is the per-app wall-clock budget around the whole `refresh_spec` call (all candidate paths and redirects). Both are code constants in `spec_cache.py`; §10 and §13 refer to these names.

`refresh_all(env)` runs `refresh_spec` for every active app with `asyncio.Semaphore(8)` and `asyncio.wait_for(..., SPEC_APP_BUDGET_S)` per app; exceptions are captured per app (US3 #2). Total time ≈ ceil(30/8) × ≤ 30 s worst case, offline.

**Interim spec-fetch token, P1–P3 (NFR-010)**: `interim_spec_token_source(cfg)` returns `EAKG__LIVE_SPEC_TOKEN` **only** when the app's `environments[env].auth_audience` equals the shared TAAC identifier (`Auth0.Api.Identifier`, read once by the new helper `taac.load_api_identifier(cfg.eakg.taac_config_path)`; this is the OQ-7 placeholder). For every other app, or when the TAAC file or identifier is missing, it returns `""` and the fetch is unauthenticated. The single bearer therefore never reaches a host outside the shared audience. `p4-spec-fetch-broker` replaces this source with the `CredentialBroker`.

```python
def interim_spec_token_source(cfg: Settings) -> TokenSource:
    shared_aud = load_api_identifier(cfg.eakg.taac_config_path) if cfg.eakg.taac_config_path else ""
    token = cfg.eakg.live_spec_token
    async def source(application_id: str, audience: str) -> str:
        return token if token and shared_aud and audience == shared_aud else ""
    return source
```

### 3.7 Credential cache (single-flight)

```text
CachingCredentialBroker.get_token(app, aud, principal):
  k = (app, aud, principal.user_id if principal else "-")
  t = cache.get(k); if t and (t.expires_at is None or t.expires_at - 60s > now): return t
  async with locks[k]:                                   # one in-flight fetch per key
      re-check cache; t = await inner.get_token(app, aud, principal=principal); cache[k] = t; return t
invalidate(app, aud): drop all keys with (app, aud, *)
```

O(1) per call; memory O(apps × principals).

### 3.8 Per-app circuit breaker (NFR-004, US3 #4)

State per `application_id`: `closed | open(until) | half_open`. 5 consecutive `unavailable` outcomes → `open` for 30 s; while open, `invoke_sse_api` returns `outcome="unavailable"` immediately (no socket). After 30 s one trial request (`half_open`); success → `closed`, failure → `open` again. `no_access` outcomes do **not** trip the breaker (they are fast and informative). Constants live in code (`_BREAKER_THRESHOLD = 5`, `_BREAKER_COOLDOWN_S = 30.0`), not env vars.

---

## 4. Data Model

### 4.1 Registry record (persisted YAML; additive) — G2

**Application mapping (FR-022).** One registry row is the join. There is no second map file.

| Side | Field | Required |
|---|---|---|
| Identity | `application_id` | Yes. The key both sides hang off. |
| Source | `git_url` | No. GitLab project URL. Empty means API-only: callable from the spec, no code provenance. |
| Address seed | `service_url_key` | No. TAAC `ServiceUrls` key (for example `FeesApiUrl`). Used only to fill a blank address. |
| Live address | `environments[<env>].base_url` | Yes for that env to be callable. Differs per environment. |

`import-taac` matches an existing row by `application_id` or `service_url_key` and sets `base_url` / `auth_audience` only when blank. It never writes `git_url`. `url_key_to_app_id` (`FeesApiUrl` → `fees`) is a match hint, not a repo lookup. A URL with no matching row is reported as an unregistered candidate. Plaisse wiki does not store this join: TAAC destinations and GitLab paths stay separate and meet only when a person names both.

A row with `git_url` and no `base_url` for the active environment is indexed from source and is not callable there. A row with `base_url` and empty `git_url` is callable and has no code evidence.

```python
Environment = Literal["local", "dev", "stage", "prod"]
Lifecycle = Literal["registered", "active", "degraded", "retired"]

@dataclass
class AppEnvironment:
    base_url: str                 # https://host[/prefix]; origin used for allow-list + per-call binding; URL composition with spec servers/basePath in §6.4
    auth_audience: str = ""       # token audience for this app in this env
    spec_path: str = ""           # optional override, e.g. "/swagger/FF/swagger.json"
    spec_fixture: str = ""        # local-only: repo-relative path to a synthetic OpenAPI doc
    enabled: bool = True

@dataclass
class RepositoryRecord:          # existing fields unchanged
    ...
    git_url: str = ""            # now optional: "" ⇒ API-only app (no EAKG extract)
    lifecycle: Lifecycle = "active"
    service_url_key: str = ""    # TAAC ServiceUrls key, e.g. "FeesApiUrl"
    environments: dict[str, AppEnvironment] = field(default_factory=dict)
```

Example:

```yaml
- repository_id: fees
  application: Fees
  application_id: fees
  git_url: https://gitlab.pnmac.com/servicing/plaisse/applications/fees/Fees.git
  lifecycle: active
  service_url_key: FeesApiUrl
  environments:
    local:
      base_url: http://127.0.0.1:9101
      spec_fixture: data/eakg/fixtures/specs/fees.openapi.json
    dev:
      base_url: https://feesapi.dev.example.invalid
      auth_audience: https://api.example.invalid
      spec_path: /swagger/FF/swagger.json
```

**Validation** (`registry_validate.validate_registry`, returns all issues per app; a record with a **blocking** issue for env E is excluded from E's catalog/index, others unaffected — US1 #4). Issue type and `blocking_issues` are defined in §4.6.

| Rule | Issue code | Severity | Scope |
|---|---|---|---|
| `application_id` matches `^[a-z][a-z0-9_]{1,62}$` and is unique across registry | `bad_app_id`, `duplicate_app_id` | blocking | record |
| `environments` keys ⊆ `{local, dev, stage, prod}` | `bad_env` | blocking | that env key |
| `base_url` parses; scheme `https`, or `http` only when host is `localhost`/`127.0.0.1` **and** env is `local`; no userinfo, query or fragment | `bad_base_url` | blocking | env |
| Host is not an IP literal outside loopback | `ip_literal_host` | blocking | env |
| Env marker mismatch (matching rule below) | `env_mismatch` (FR-019, US9 #3) | blocking | env |
| Same origin appears under two different env keys of one app | `env_origin_reuse` | blocking | both envs |
| Two apps share one origin+path-prefix in the same env | `origin_collision` (protects NFR-010) | blocking | env, both apps |
| `spec_fixture` set on non-`local` env | `fixture_outside_local` | blocking | env |
| `enabled` and `auth_audience == ""` on non-local env | `audience_missing` | warning (app listed, `/ready` shows `credential: missing`) | env |
| `lifecycle == "retired"` | — (not an issue; excluded from `list_active`) | — | record |

**`env_mismatch` matching (RC-017)**: lowercase the host, split it on `.` and `-` into tokens, and compare tokens by **exact equality** against the marker sets `dev = {"dev"}`, `stage = {"stg", "stage"}`, `prod = {"prd", "prod"}`. The rule fires when the host contains a token from a marker set other than the entry's env key (`local` has no marker set; any marker token under `local` fires). Substrings never match: `devops-api.example.invalid` and `products.example.invalid` produce no marker tokens. A host with tokens from two different sets also fires.

### 4.2 Spec pointer (`repos/<id>/openapi/<env>/current.json`)

```json
{"environment": "dev", "spec_hash": "a1b2c3d4e5f6", "source_url": "https://…/swagger/v1/swagger.json",
 "fetched_at": "2026-10-08T02:00:04Z", "last_attempt_at": "2026-10-08T02:00:04Z",
 "status": "ok", "last_error": null, "operation_count": 242}
```

`status ∈ {ok, failed}`. `stale` is derived at read time: `now - fetched_at > API_INDEX__STALE_AFTER_HOURS` **or** `status == failed`.

### 4.3 Unified operation (`packages/api_index/records.py`)

```python
class UnifiedOperation(BaseModel):
    uid: str                          # "fees|GET|/api/fees/{}"
    public_id: str                    # "fees:getFees"
    application_id: str
    application_label: str
    environment: Environment
    method: HttpMethod
    path: str                         # OpenAPI template (invoke uses this)
    normalized_path: str
    summary: str | None = None
    description: str | None = None
    tags: list[str] = []
    parameters: list[ApiParameter] = []
    has_request_body: bool = False
    read_only: bool
    callable: bool                    # read_only and join not in {"eakg_only", "ambiguous"}
    permission: str | None = None
    authz_source: str | None = None
    code_unit: str | None = None
    evidence: list[dict[str, str | int]] = []   # ≤ 3 {file, line, extractor}
    eakg_operation_key: str | None = None
    capability_ids: list[str] = []
    join: Literal["exact", "suffix", "openapi_only", "eakg_only", "ambiguous"]
    spec_hash: str | None = None
```

Validation: `uid` unique per env; `public_id` unique per env (builder falls back to `METHOD_slug` on collision, then appends `_2`… deterministically by path sort); `callable ⇒ read_only`; `method ∈ {get, head} ⇐ callable`.

Persisted as `enterprise/api_index/<env>/operations.json`: `{"environment", "built_at", "inputs": {app_id: {spec_hash, interface_hash}}, "operations": [...]}`. `inputs` drives "only changed apps reprocess" (US7 #2).

### 4.4 Vector document metadata (namespace `api_ops_<env>_<model8>`)

`application_id, application_label, environment, method, path, normalized_path, public_id, uid, read_only, permission, capability_ids, text_hash, embed_model_id, spec_hash`. All scalars except `capability_ids` (list of str).

### 4.5 Credentials (in memory only, never persisted)

```python
class AccessToken(BaseModel):
    application_id: str
    audience: str
    token: SecretStr                 # never in repr/logs/audit
    token_type: Literal["Bearer"] = "Bearer"
    expires_at: datetime | None = None
```

### 4.6 Supporting types (referenced by §5.4 signatures)

```python
# packages/eakg/registry_validate.py
@dataclass(frozen=True)
class RegistryIssue:
    code: str                                  # §4.1 issue code
    severity: Literal["blocking", "warning"]
    application_id: str
    environment: str | None                    # None = applies to the whole record
    field: str                                 # e.g. "environments.dev.base_url"
    message: str

def validate_registry(registry: RepositoryRegistry) -> dict[str, list[RegistryIssue]]: ...   # keyed by application_id; cross-record rules need the whole registry
def blocking_issues(rec: RepositoryRecord, environment: str, issues: dict[str, list[RegistryIssue]]) -> list[RegistryIssue]:
    return [i for i in issues.get(rec.application_id, [])
            if i.severity == "blocking" and i.environment in (None, environment)]
# RepositoryRegistry computes `issues` once per load (cached with the registry fingerprint) and list_active uses it.

# packages/eakg/spec_cache.py
class SpecPointer(BaseModel):                  # persisted shape of current.json (§4.2)
    environment: str
    spec_hash: str | None = None
    source_url: str | None = None
    fetched_at: datetime | None = None
    last_attempt_at: datetime | None = None
    status: Literal["ok", "failed"]
    last_error: str | None = None              # ≤ 300 chars, no token material
    operation_count: int | None = None
    credential: Literal["configured", "missing", "error", "interim"] | None = None   # P4 records broker state; P1–P3 "interim"
    def is_stale(self, now: datetime, stale_after_hours: int) -> bool: ...

# packages/api_index/records.py
class CapabilityLookupAll(Protocol):           # satisfied by capability_kg.CapabilityCatalog
    def list_capabilities(self, *, limit: int = 100) -> list[CapabilityRecord]: ...   # build_operations calls limit=100_000

class OperationSet(BaseModel):                 # in-memory + operations.json shape (§4.3)
    environment: str
    built_at: datetime
    inputs: dict[str, AppInputs]               # application_id → hashes
    operations: list[UnifiedOperation]
    issues: dict[str, list[str]] = {}          # application_id → build issue codes, e.g. "spec_missing", "spec_server_origin_mismatch"
class AppInputs(BaseModel):
    spec_hash: str | None
    interface_hash: str | None

@dataclass(frozen=True)
class Resolved:
    record: UnifiedOperation
    matched_alias: str
    @property
    def public_id(self) -> str: ...
    @property
    def read_only(self) -> bool: ...
@dataclass(frozen=True)
class Ambiguous:
    ref: str
    candidates: list[tuple[str, str]]          # (public_id, application_label), sorted by public_id
@dataclass(frozen=True)
class NotFound:
    ref: str
    suggestions: list[str]                     # ≤ 3 public_ids from the keyword index

# packages/api_index/indexer.py
class IndexReport(BaseModel):
    environment: str
    namespace: str
    embed_model_id: str                        # "model:dimensions"
    embedded: int
    deleted: int
    unchanged: int
    failed_apps: dict[str, str] = {}           # application_id → error (≤ 300 chars)
    full_rebuild: bool
    duration_ms: float

# packages/api_index/search.py
class SearchHit(BaseModel):
    record: UnifiedOperation
    score: float                               # blended, 0..1
    vector_score: float | None
    keyword_score: float | None
class SearchOutcome(BaseModel):
    hits: list[SearchHit]
    backend: Literal["vector_index", "sidecar", "keyword"]
    confident: bool                            # §3.5 confidence floor
    shortlist: list[str]
    warnings: list[str] = []                   # e.g. "embed_model_mismatch", "vector_store_unavailable"

# packages/api_index/health.py
class AppHealth(BaseModel):                    # one element of /ready "apps" (§5.2)
    application_id: str; lifecycle: str; indexed: bool; operation_count: int
    spec_fetched_at: datetime | None; spec_age_hours: float | None; stale: bool
    spec_status: Literal["ok", "failed", "missing"]
    credential: Literal["configured", "missing", "error"]
    last_invoke: dict[str, str] | None; breaker: Literal["closed", "open", "half_open"]
    issues: list[str]
class HealthSnapshot(BaseModel):               # full /ready body (§5.2)
    status: Literal["ready", "no_catalog"]; environment: str
    catalog: dict[str, str | int]; index: dict[str, str | float]
    summary: dict[str, int]; apps: list[AppHealth]
    catalog_health: dict[str, int]; warnings: list[str]
```

---

## 5. API Design

### 5.1 MCP tool surface (additive)

| Tool | Change |
|---|---|
| `search_sse_apis(query, limit=15, application: str \| None = None, permission: str \| None = None)` | new optional filters (FR-017) |
| `call_sse_api(..., application: str \| None = None)` | `operation_id` accepts any alias (§3.3); new optional `application` narrows alias resolution and is **required** for a raw `method`+`path` call in registry mode (§6.4); response JSON adds `application_id`, `application`, `operation_id` (public), `outcome`, `citation` |
| `list_sse_apis(source_label?, application?)` | sources list shows per-app `status`, `fetched_at`, `stale` |

`call_sse_api` response:

```json
{"ok": false, "status": 403, "outcome": "no_access", "application_id": "escrow", "application": "Escrow Manager",
 "operation_id": "escrow:getEscrowAnalysis", "citation": "tool:call_sse_api:escrow:getEscrowAnalysis",
 "url": "https://…", "duration_ms": 41.2, "data": null,
 "error": "Escrow Manager (escrow) has not granted LoanOps access in dev (HTTP 403). Ask the owning team to grant access."}
```

`outcome ∈ {ok, no_access, unavailable, not_found, rejected, error}`.

### 5.2 `/ready` (MCP) — Phase 5

`200` whenever the catalog loaded (even if apps are degraded); `503` only if no catalog could be built.

```json
{"status": "ready", "environment": "dev", "catalog": {"operations": 5120, "built_at": "…", "source": "registry"},
 "index": {"backend": "vector_store", "namespace": "api_ops_dev_3f2a9c1b", "coverage": 1.0},
 "summary": {"apps": 30, "healthy": 27, "degraded": 3},
 "apps": [{"application_id": "fees", "lifecycle": "active", "indexed": true, "operation_count": 242,
           "spec_fetched_at": "…", "spec_age_hours": 5.1, "stale": false, "spec_status": "ok",
           "credential": "configured", "last_invoke": {"outcome": "ok", "at": "…"}, "breaker": "closed",
           "issues": []}],
 "catalog_health": {"openapi_only": 61, "eakg_only": 12, "ambiguous": 2, "capabilities_unbound": 4},
 "warnings": []}
```

`credential ∈ {configured, missing, error}` comes from `broker.check()` (no network; §6.2). Possible `warnings`: `vector_store_unavailable`, `embed_model_mismatch`, `operations_json_invalid`, `catalog_reload_failed`. `issues` lists registry validation codes and `access_denied` / `unreachable` from the last invoke outcome (US6 #3).

### 5.3 CLIs

```text
python -m packages.eakg registry validate [--env dev]
python -m packages.eakg registry import-taac --env dev [--taac PATH] [--dry-run]
python -m packages.eakg spec-refresh [--id ID | --all] [--env dev]
python -m packages.api_index.refresh app --id ID [--env dev]
python -m packages.api_index.refresh all [--env dev] [--force]
python -m packages.api_index.refresh nightly [--env dev]
python -m packages.api_index report [--env dev] [--json]          # FR-013 mismatch report
python -m packages.api_index health --probe [--env dev]           # operator-run access probe (network)
```

All CLIs exit `0` when every app succeeded, `2` when some apps failed (others still processed), `1` on fatal error; JSON report on stdout.

### 5.4 Function signatures (public surface)

```python
# packages/eakg/registry.py
class RepositoryRegistry:
    def list_active(self, environment: str) -> list[RepositoryRecord]: ...   # lifecycle != retired, env enabled, no blocking_issues (§4.6)

# packages/tools/registry_catalog.py
CatalogSourceKind = Literal["registry", "swagger_links", "fixture"]
def resolve_catalog_source(cfg: Settings, registry: RepositoryRegistry, store: ShardStore) -> CatalogSourceKind: ...   # D1 precedence

# packages/eakg/spec_cache.py
TokenSource = Callable[[str, str], Awaitable[str]]          # (application_id, audience) -> bearer ("" = none)
@dataclass(frozen=True)
class SpecRefreshResult:
    application_id: str; environment: str; status: Literal["ok", "failed", "not_registered_in_env"]
    spec_hash: str | None; changed: bool; error: str | None
async def refresh_spec(rec: RepositoryRecord, environment: str, store: ShardStore, *, token_source: TokenSource) -> SpecRefreshResult: ...
async def refresh_all(registry: RepositoryRegistry, store: ShardStore, environment: str, *, token_source: TokenSource, concurrency: int = 8) -> list[SpecRefreshResult]: ...
def read_current_spec(store: ShardStore, repository_id: str, environment: str) -> tuple[dict[str, Any] | None, SpecPointer | None]: ...
def interim_spec_token_source(cfg: Settings) -> TokenSource: ...           # P1–P3 only (§3.6)

# packages/eakg/taac.py (modified)
def load_api_identifier(path: str | Path) -> str: ...                      # Auth0.Api.Identifier, "" when absent

# packages/eakg/openapi_enrich.py (modified)
async def fetch_spec_with_source(base_url: str, *, token: str = "", paths: Sequence[str] = SPEC_CANDIDATES, timeout: float = SPEC_HTTP_TIMEOUT_S, transport: httpx.AsyncBaseTransport | None = None) -> tuple[dict[str, Any] | None, str | None, str | None]: ...
async def enrich_interface(iface, store, *, mode, base_url="", token="", fixture_path="", spec: dict[str, Any] | None = None) -> RepoInterface: ...

# packages/sse/loader.py (modified)
@dataclass(frozen=True)
class SpecSource:
    source_id: str; label: str; base_url: str; document: dict[str, Any] | None
    environment: str; fetched_at: str | None; status: str; error: str | None
def resolve_swagger_links(sse: SseConfig) -> list[dict[str, str]]: ...
class OpenApiCatalogService:
    def __init__(self, *, ..., spec_sources: Callable[[], list[SpecSource]] | None = None, app_targets: Callable[[], dict[str, AppTarget]] | None = None) -> None: ...

# packages/sse/types.py (modified)
class AppTarget(BaseModel):
    application_id: str; label: str; environment: str; base_url: str; origin: str; audience: str
class CatalogSource(BaseModel):  # + status: str = "ok", fetched_at: str | None = None, environment: str | None = None, stale: bool = False

# packages/api_index/records.py
def build_operations(registry: RepositoryRegistry, store: ShardStore, environment: str, *, capabilities: CapabilityLookupAll | None) -> OperationSet: ...
class OperationResolver:
    def resolve(self, ref: str, *, application_id: str | None = None) -> Resolved | Ambiguous | NotFound: ...

# packages/api_index/indexer.py
async def reindex(environment: str, ops: OperationSet, *, vector_store: AbstractVectorStoreProvider, embedder: AbstractEmbeddingProvider, manifest_path: Path, namespace_prefix: str, sidecar_path: Path) -> IndexReport: ...

# packages/api_index/search.py
class ApiSearchService:
    async def search(self, query: str, *, limit: int = 15, application_ids: list[str] | None = None, permission: str | None = None) -> SearchOutcome: ...   # hits + backend label

# packages/sse/invoke.py (modified)
async def invoke_sse_api(service, *, method, path, path_params=None, query=None, headers=None, body=None,
                         operation=None, cache=None, cache_ttl=60,
                         target: AppTarget | None = None, credentials: AbstractCredentialBroker | None = None,
                         breaker: BreakerRegistry | None = None, audit: AbstractAuditSinkProvider | None = None,
                         principal: Principal | None = None, registry_mode: bool = False,
                         transport: httpx.AsyncBaseTransport | None = None) -> InvokeResult: ...

# packages/sse/tools.py (modified) — target resolution before invoke (§6.4 step 0)
def resolve_invoke_target(service, *, operation_ref: str | None, method: str | None, path: str | None,
                          application: str | None, resolver: OperationRefResolver | None,
                          registry_mode: bool) -> InvokeTarget | Rejection: ...

# packages/sse/types.py (modified) — sse never imports api_index; api_index.OperationResolver satisfies this Protocol
class OperationRefResolver(Protocol):
    def resolve(self, ref: str, *, application_id: str | None = None) -> object: ...   # Resolved | Ambiguous | NotFound
@dataclass(frozen=True)
class InvokeTarget:
    operation: ApiOperation | None              # None only in legacy modes
    target: AppTarget | None                    # None only in legacy modes
@dataclass(frozen=True)
class Rejection:
    reason: Literal["application_required", "unknown_application", "operation_not_in_application", "ambiguous", "not_found"]
    message: str
    application_id: str | None = None
```

---

## 6. Provider and module design

### 6.1 Provider abstraction compliance

- New protocol `AbstractCredentialBroker` lives in `packages/common/providers/credential_broker.py`; concrete classes (`StaticCredentialBroker`, `MockCredentialBroker`, `CachingCredentialBroker`) live in the same module (precedent: `loan_data.py`). Only `factory.py` imports concrete classes.
- `packages/sse`, `packages/eakg`, `packages/api_index`, `packages/tools` import only the ABC and `get_credential_broker()`.
- No `os.environ` / `os.getenv` anywhere outside `settings.py`; per-app secrets are read through `get_secrets_provider()`.

### 6.2 `CredentialBroker` protocol — G7

```python
class CredentialError(Exception):
    def __init__(self, application_id: str, message: str) -> None: ...
class CredentialNotConfigured(CredentialError): ...   # no access arrangement → "has not granted access"
class CredentialDenied(CredentialError): ...          # issuer refused (revoked / not entitled)
class CredentialUnavailable(CredentialError): ...     # issuer unreachable

class Principal(BaseModel):                           # reserved for on-behalf-of (FR-011)
    user_id: str | None = None
    tenant: str | None = None
    subject_token: SecretStr | None = None

class CredentialCheck(BaseModel):
    application_id: str
    state: Literal["configured", "missing", "error"]
    detail: str | None = None

class AbstractCredentialBroker(ABC):
    @abstractmethod
    async def get_token(self, application_id: str, audience: str, *, principal: Principal | None = None) -> AccessToken: ...
    @abstractmethod
    async def invalidate(self, application_id: str, audience: str) -> None: ...
    @abstractmethod
    async def check(self, application_id: str, audience: str) -> CredentialCheck: ...   # MUST NOT do network I/O
    async def prime(self, application_ids: Sequence[str]) -> None:                      # optional; default no-op
        return None
```

**`check()` without I/O (RC-008)**. `check` answers only from in-memory state, so it holds even when `SecretsProvider` is remote (AWS Secrets Manager):

1. `prime(application_ids)` is the only place a broker may touch `SecretsProvider` for presence. The MCP / Agent API lifespan calls it once at startup with `[r.application_id for r in registry.list_active(env)]`, and again after a catalog reload adds apps. `StaticCredentialBroker.prime` stores the set of app ids whose `APP_TOKEN_<APPID>` secret is non-empty (`_present`). A per-app lookup failure records that app in `_errored`; it never raises.
2. `CachingCredentialBroker.check` uses its last-known state per `(app, aud)` first: a cached unexpired token ⇒ `configured`; last `get_token` raised `CredentialNotConfigured` ⇒ `missing`; last raised `CredentialDenied` / `CredentialUnavailable` ⇒ `error` with that class name as `detail`. Otherwise it delegates to `inner.check`.
3. `StaticCredentialBroker.check`: app in `_present`, or in `shared_apps` with a non-empty shared token ⇒ `configured`; app in `_errored` ⇒ `error`; primed and absent ⇒ `missing`; **not primed** for this app ⇒ `state="error", detail="unknown"`.
4. `MockCredentialBroker.check` answers from its constructor dicts.

The contract test asserts `check` makes no `SecretsProvider` call (spy) and no HTTP request.

**`StaticCredentialBroker(secrets, shared_token, shared_apps)`** (local + current dev):

1. `secrets.get_or_default(f"APP_TOKEN_{application_id.upper()}", "")` → if non-empty, return it.
2. Else if `application_id ∈ shared_apps` and `shared_token` (= `cfg.sse.api_key`) → return it.
3. Else raise `CredentialNotConfigured`.

The shared `SSE__API_KEY` is therefore sent **only** to explicitly listed apps — closes today's "one bearer to every host" (NFR-010). `expires_at=None`.

**`MockCredentialBroker(tokens: dict[str, str], denied: set[str] = set())`** — tests and contract tests.

**`CachingCredentialBroker(inner)`** — §3.7; the factory always wraps the selected broker.

Future implementations (not built here, FR-011): `Auth0M2MCredentialBroker` (client-credentials per audience), `OnBehalfOfCredentialBroker` (token exchange using `Principal.subject_token`). Neither changes onboarding, discovery, or tool responses.

### 6.3 `packages/api_index` project — G4

```text
projects/LoanOps.ApiIndex/
  pyproject.toml            # loanops-api-index; deps: loanops-common, loanops-sse, loanops-eakg, loanops-capability-kg
  packages/api_index/
    __init__.py
    __main__.py             # report / health CLIs
    paths.py                # operations.json, manifest, sidecar paths per env
    records.py              # UnifiedOperation, normalize_path, build_operations, OperationResolver
    keyword_index.py
    indexer.py
    search.py
    health.py
    refresh.py
    breaker.py              # BreakerRegistry (also used by sse.invoke via injected instance)
    tests/
```

`LoanOps.Tools` adds `loanops-api-index` to its dependencies; `scripts/check_project_refs.py` must stay green. Dependency direction: `common ← sse, eakg ← api_index ← tools ← mcp_server / agent_api`. `breaker.py` defines a `BreakerRegistry` Protocol in `packages/sse/types.py` so `sse` does not import `api_index`.

### 6.4 `invoke_sse_api` per-app flow (FR-009, FR-010, NFR-010)

**Step 0 — target resolution (`packages/sse/tools.py` `resolve_invoke_target`, before `invoke_sse_api`)**. Registry mode (`registry_mode=True`):

| Input | Behaviour |
|---|---|
| `operation_id` / `capability_id` resolves (`Resolved`) | `operation = record`, `target = service.target_for(record.application_id)`; if `application` is given and differs ⇒ reject `operation_not_in_application` |
| alias `Ambiguous` / `NotFound` | reject `ambiguous` (lists candidates) / `not_found` (lists suggestions) |
| raw `method`+`path`, **no** `application` | reject `application_required`: "In registry mode, a raw method and path need `application`. Prefer `operation_id` from `search_sse_apis`." |
| raw `method`+`path` + `application` | `target = service.target_for(application)` (unknown ⇒ reject `unknown_application`); match `(METHOD, normalize_path(path))` against **that app's** callable operations only; exactly one match ⇒ `operation = match`; none ⇒ reject `operation_not_in_application` |

A rejection returns `outcome="rejected"` with the message, emits the `sse.live_read` audit event with `outcome="rejected"`, and **never calls `get_token` or opens a socket**. The `target=None` / `operation=None` branch exists only in legacy `swagger_links` / `fixture` modes (`registry_mode=False`); `invoke_sse_api` raises `ToolPolicyError` if `registry_mode=True` and `target is None` (defence in depth).

**URL composition (RC-005)**. `effective_base(target, operation)`:

1. Start from `target.base_url` (origin + optional registry prefix), trailing `/` stripped.
2. Take the spec base path from `operation.server_url` (OpenAPI `servers[0].url`, or Swagger 2 `basePath`):
   - relative URL (no scheme, e.g. `/api/v2`) ⇒ use its path;
   - absolute URL with origin equal to `target.origin` ⇒ use its path;
   - absolute URL on a **different** origin ⇒ ignore it, and `build_operations` records app build issue `spec_server_origin_mismatch` (shown in `/ready` `issues`);
   - missing ⇒ empty path.
3. Append the spec base path unless the registry prefix already ends with it (segment comparison, case-insensitive). The registry is authoritative for the origin; the spec is authoritative for its base path.
4. `url = base + substitute_path(path, path_params) + query`.

Example: `base_url = https://feesapi.dev.example.invalid`, `servers = [{"url": "https://feesapi.dev.example.invalid/fees"}]`, `path = /api/fees/{id}` ⇒ `https://feesapi.dev.example.invalid/fees/api/fees/123`. With `servers = [{"url": "https://other.example.invalid"}]` the spec server is ignored ⇒ `https://feesapi.dev.example.invalid/api/fees/123` plus the issue. Legacy modes keep today's `resolve_base_url`.

```text
op, target = step 0 result                                         # Rejection ⇒ return "rejected" (no token, no I/O)
url    = effective_base(target, op) + substitute_path(path, path_params) + query
assert method in GET/HEAD                                          # unchanged, FR-020
assert origin(url) == target.origin   (else PermissionError)        # per-app binding, stricter than allow-list
headers = {k: v for k, v in (headers or {}).items() if k.lower() not in {"authorization", "cookie", "proxy-authorization"}}
cache_key = f"sse:api:{env}:{app}:{principal_key}:{METHOD}:{url}"   # principal_key = principal.user_id or "service"
if cache hit: return cached result (outcome "ok")                  # only after the origin assert
if breaker.is_open(app): return outcome "unavailable" (no I/O)
try token = await credentials.get_token(app, target.audience)
except CredentialNotConfigured → outcome "no_access"  ("<label> (<id>) has not granted LoanOps access in <env>.")
except CredentialDenied        → outcome "no_access"  ("… access was refused or revoked.")
except CredentialUnavailable   → outcome "error"      ("Could not obtain credentials for <label>; try again later.")
resp = GET with Authorization: Bearer <token>, timeout httpx.Timeout(10.0, connect=3.0), follow_redirects=False
401 → await credentials.invalidate(app, aud); retry once iff new token differs; still 401 → "no_access" (credentials rejected)
403 → "no_access" (lacks permission); 404 → "not_found"; 5xx / timeout / connect error → "unavailable" (+ breaker.record_failure)
2xx → "ok" (+ breaker.record_success); store under cache_key (TTL 60 s as today)
emit AuditEvent(event_type="sse.live_read", payload={application_id, operation_id, environment, status, outcome, duration_ms, url_path_template})
```

**Response cache key (RC-007)**: `sse:api:{env}:{application_id}:{principal_key}:{METHOD}:{url}` with `principal_key = principal.user_id if principal and principal.user_id else "service"`. Today every call runs under the service identity, so behaviour is unchanged. Once an on-behalf-of broker passes a `Principal`, user A's cached response can never be served to user B, so FR-011 needs no redesign. Legacy modes use `env="legacy"` and `application_id = operation.source_id or "-"`.

Legacy modes (`swagger_links`, `fixture`) keep today's behavior: `target=None` ⇒ shared bearer via the static broker's shared-token path only when the source id is in `CREDENTIALS__STATIC_SHARED_APPS`; otherwise as before with `service.bearer_token` (local-dev only; documented as deprecated).

---

## 7. Technical Decisions

### D1 — Registry is the only app list; swagger links become a dev override
**Context**: FR-001, SC-001; two drifting lists today. **Decision**: extend `RepositoryRecord` with `environments`. Catalog source is chosen by `resolve_catalog_source(cfg, registry, store)` (RC-001 — both mechanisms are used, so demo runs registry mode even with an older `.env`):

1. Explicit `SSE__CATALOG_SOURCE` ∈ {`registry`, `swagger_links`, `fixture`} wins.
2. `auto`:
   1. `swagger_links` when `SSE__SWAGGER_LINKS` / `SSE__SWAGGER_URLS` are set (keeps existing dev `.env` files unchanged);
   2. else `registry` when at least one `registry.list_active(EAKG__ENVIRONMENT)` record has a usable spec — a cached `openapi/<env>/current.json` with a `spec_hash`, or an `environments[env].spec_fixture` that exists on disk;
   3. else `fixture` when `SSE__USE_FIXTURE=true` (today's default, `SseConfig.use_fixture = True`);
   4. else `registry` (empty catalog; every app listed as degraded).
3. The shipped `.env.example` sets `SSE__CATALOG_SOURCE=registry` and `EAKG__ENVIRONMENT=local` explicitly. `SSE__USE_FIXTURE=true` stays in `.env.example` for the legacy fixture path and no longer decides demo mode.

A P1 test loads `.env.example` into `Settings` (no process env) together with the committed registry and fixtures, and asserts `resolve_catalog_source(...) == "registry"`. A second test asserts `auto` + `SSE__USE_FIXTURE=true` + local fixtures present ⇒ `registry`.

**Alternatives**: (1) keep swagger links as primary — rejected: second list, serial boot fetch; (2) separate `apps.yaml` — rejected: duplicates `repositories.yaml` identity fields and owners; (3) only change `.env.example` — rejected alone: developers with an older `.env` (`SSE__USE_FIXTURE=true`, no `SSE__CATALOG_SOURCE`) would silently stay on `fixture`. **Consequences**: + one edit onboards an app; + API-only apps supported via empty `git_url`; + `make demo` exercises the new path (NFR-007, SC-010); − `RepositoryRecord` grows; − `auto` precedence must be documented in `CONTEXT.md`.

### D2 — Fetch specs in the pipeline, never at boot
**Context**: NFR-002, FR-007, US3; `OpenApiCatalogService.load()` fetches serially with 15 s timeouts. **Decision**: `refresh_spec` writes per-env cached specs + pointer; runtime reads files only. **Alternatives**: (1) parallel fetch at boot — rejected: readiness still depends on the slowest app and on network; (2) fetch lazily on first search — rejected: first user pays latency and partial catalogs are silent. **Consequences**: + boot is O(apps) disk reads; + last-good spec survives outages (FR-016); − catalog freshness depends on the refresh schedule (open Q3).

### D3 — New `LoanOps.ApiIndex` project for the unified record, index and search — G4
**Context**: the join needs both `sse` (OpenAPI parsing) and `eakg` (interfaces); neither may depend on the other. **Decision**: new workspace project depending on both; `tools` composes it. **Alternatives**: (1) put in `LoanOps.Tools` — rejected: Tools is composition, and the refresh CLI would drag MCP deps into the pipeline; (2) put in `LoanOps.Sse` with an `eakg` dependency — rejected: inverts the layering. **Consequences**: + clean layering, testable in isolation; − one more project to register in AGENTS.md / ARCHITECTURE.md / `check_project_refs`.

### D4 — Join key `app|METHOD|normalized_path` with suffix fallback
**Context**: FR-012/FR-013; EAKG paths lack controller route prefixes (`/{id}/Summary` vs `/api/Loans/{loan_id}/Summary`). **Decision**: exact normalized match, then unique segment-suffix match within the same app and method, disambiguated by controller stem; else report. **Alternatives**: (1) join on operationId — rejected: EAKG keys are action names, OpenAPI operationIds are often absent or differently cased; (2) fix the extractor to compose full routes first — preferred long-term, but not a prerequisite; the suffix join tolerates both. **Consequences**: + works with today's shards; + `join` field makes quality measurable; − ambiguous joins require extractor improvements to clear.

### D5 — Public id keeps today's `app:operationId` format
**Context**: existing tests, Cursor sessions and logs use `loanservices:getLoanSummary`. **Decision**: `public_id` = existing SSE id format; `uid` is internal. **Alternatives**: expose `uid` (`app|GET|/path`) — rejected: unfriendly and leaks normalized paths into prompts. **Consequences**: + no client break; − collision fallback (`METHOD_slug`) needs deterministic tie-breaking (§4.3).

### D6 — Reuse `VectorStore` provider; extend filter semantics — G6
**Context**: FR-017/FR-018, NFR-003; Python cosine over thousands of ops; no metadata filters. Today `QdrantVectorStoreProvider.search` maps filters to `MatchValue` equality only and `MockVectorStoreProvider.search` ignores `filter`. **Decision**: the API operation index uses the existing **pgvector** provider (`VECTOR_STORE__PROVIDER=pgvector`, table `vs_<namespace>`). Qdrant remains available for other deployments. In `provider_contracts`: (a) define `filter` values: scalar ⇒ equality, `list` ⇒ any-of; implement in qdrant (`MatchAny`), mock, pgvector, azure_ai_search; (b) add `supports_any_of_filter: ClassVar[bool]` (True on providers that implement (a)); (c) add `ensure_namespace(namespace, vector_size)` to the contract — idempotent (no-op if it exists with that size, `ProviderConfigError` on size mismatch) and resolving namespace → physical collection exactly as `upsert` / `search` / `delete` do (§3.4); add contract tests for all three. `ApiSearchService` sends a list filter only when (b) is true and always post-filters, so correctness never depends on provider support (§3.5). **Alternatives**: (1) separate Postgres+pgvector store (Plaisse pattern) — rejected in ADR-024: extra infra, the provider already abstracts it; (2) keep JSON sidecar — rejected: no filters, per-process memory, O(n) per query; (3) one namespace per app — rejected: stage-2 would need N queries. **Consequences**: + ANN latency; + shared across processes; − cross-repo change to `provider_contracts`; + namespace → collection naming stays inside each provider (verified today: Qdrant `create_collection(name)` uses the raw name while `upsert`/`search` use `{collection}_{namespace}`; `ensure_namespace` removes that mismatch instead of working around it in `api_index`).

### D7 — Model fingerprint in namespace name
**Context**: embed model change must force reindex (ADR-024) and vector sizes differ (384 vs 768/1024). **Decision**: `api_ops_<env>_<sha8(model:dims)>`; build new namespace, swap manifest pointer, then delete old ids. **Alternatives**: store `embed_model_id` in metadata and re-embed in place — rejected: mixed-dimension collections are invalid. **Consequences**: + zero-downtime model swap; − old namespace data lingers until deleted (contract has no drop-collection).

### D8 — Two-stage retrieval via probe aggregation (no app-level vectors)
**Context**: FR-018. **Decision**: stage 1 is a top-60 probe over operations aggregated per app; stage 2 filters to the shortlist. **Alternatives**: (1) app description vectors in a second namespace — rejected for v1: extra embed/maintenance, description quality varies by team; (2) single-stage with filter only when user supplies an app — rejected: does not satisfy FR-018. **Consequences**: + no extra index; + keyword-exact apps always included (guards recall); − recall depends on probe size — measured by SC-002 benchmark, tunable constant.

### D9 — `CredentialBroker` as a local provider with static impl first — G7
**Context**: FR-009/FR-010/FR-011, NFR-010; access model undecided (story Q1). **Decision**: ABC in `packages/common/providers/credential_broker.py`, static + mock + caching wrapper; per-app secrets via `SecretsProvider`. **Alternatives**: (1) extend `SecretsProvider` with per-app names only — rejected: no audience/expiry/OBO path, no "not configured" vs "denied" distinction; (2) implement Auth0 M2M now — rejected: premature (ADR-024, ARCHITECTURE_REVIEW_LAYER2 §8); (3) put the ABC in `provider_contracts` now — deferred: can be upstreamed later without changing callers (re-export pattern). **Consequences**: + auth model swappable behind one call; + explicit opt-in for the shared token; − one more provider category to document. Verified count: `factory.py` already exposes 13 `get_*` factories (`loan_data`, `policy_source`, `chat`, `embedding`, `vector_store`, `pii`, `content_safety`, `audit_sink`, `secrets`, `telemetry`, `prompt_store`, `session_store`, `reranker`), so `get_credential_broker` is the 14th. AGENTS.md still lists 10 categories (including `tools_client`, whose factory lives in `LoanOps.Tools`); `p6-architecture-md` reconciles that list.

### D10 — Classify outcomes in the tools layer, not the LLM
**Context**: FR-010, SC-006. **Decision**: `invoke_sse_api` returns `outcome` + human message naming the app; tool description instructs the agent to relay `error` verbatim for `no_access`/`unavailable`. **Alternatives**: let the LLM interpret status codes — rejected: inconsistent and untestable. **Consequences**: + deterministic tests for SC-006; − message wording is code, changes need test updates.

---

## 8. File Structure

### 8.1 New files

| File | Purpose | Phase |
|---|---|---|
| `projects/LoanOps.Eakg/packages/eakg/registry_validate.py` | `RegistryIssue`, `validate_record`, `validate_registry` | P1 |
| `projects/LoanOps.Eakg/packages/eakg/registry_import.py` | TAAC → `environments[env]` seeding (fill-blank only) | P1 |
| `projects/LoanOps.Eakg/packages/eakg/spec_cache.py` | `refresh_spec`, `refresh_all`, `read_current_spec`, pointer model, pruning | P1 |
| `projects/LoanOps.Tools/packages/tools/registry_catalog.py` | `build_spec_sources`, `build_app_targets` from registry + store | P1 |
| `data/eakg/fixtures/specs/{escrow,fees,loanservices}.openapi.json` | Synthetic local specs (no PII) | P1 |
| `projects/LoanOps.Eakg/packages/eakg/tests/test_registry_env.py`, `test_spec_cache.py`, `test_registry_import.py` | P1 tests | P1 |
| `projects/LoanOps.Sse/packages/sse/tests/test_registry_catalog_mode.py` | No-network boot, hot reload, env separation tests | P1 |
| `projects/LoanOps.Tools/packages/tools/tests/test_catalog_source.py` | `resolve_catalog_source` precedence incl. shipped `.env.example` ⇒ `registry` | P1 |
| `projects/LoanOps.AgentCore/packages/agent_core/tests/test_partial_availability.py` | US3 #3 agent-level case: one app `unavailable`, answer still cites the other | P4 |
| `projects/LoanOps.ApiIndex/**` (see §6.3) | Unified record, resolver, index, search, health, refresh | P2–P5 |
| `projects/LoanOps.Common/packages/common/providers/credential_broker.py` | Protocol + static/mock/caching impls | P4 |
| `projects/LoanOps.Common/packages/common/providers/contract_tests/test_credential_broker.py` | Contract tests | P4 |
| `projects/LoanOps.Sse/packages/sse/tests/test_invoke_per_app.py` | Outcome classification, origin binding, header stripping | P4 |
| `scripts/fixtures/gen_scale_fixture.py` | Synthetic 30 apps / ~5k ops / registry / benchmark generator | P5 |
| `data/eval/api_discovery_benchmark.jsonl` | Benchmark questions → expected `public_id` (synthetic) | P5 |
| `projects/LoanOps.ApiIndex/packages/api_index/tests/test_scale.py` | NFR/SC scale tests (marker `scale`) | P5 |

### 8.2 Modified files

| File | Change | Phase |
|---|---|---|
| `projects/LoanOps.Common/packages/common/settings.py` | `EakgConfig.environment`, `SseConfig.catalog_source` (P1); `ApiIndexConfig` (P3/P5); `CredentialsConfig` (P4) | P1/P3/P4/P5 |
| `projects/LoanOps.Eakg/packages/eakg/registry.py` | `AppEnvironment`, new fields, `list_active(env)`, round-trip `from_dict`/`to_dict` | P1 |
| `projects/LoanOps.Eakg/packages/eakg/openapi_enrich.py` | `fetch_spec_with_source` (same-origin redirects), `enrich_interface(spec=...)` | P1 |
| `projects/LoanOps.Eakg/packages/eakg/onboard.py` | Call `refresh_spec` with env `base_url`; pass spec into `enrich_interface`; skip clone/extract when `git_url == ""` | P1 |
| `projects/LoanOps.Eakg/packages/eakg/__main__.py` | `registry validate`, `registry import-taac`, `spec-refresh` subcommands | P1 |
| `projects/LoanOps.Eakg/packages/eakg/sync.py` | `sync_nightly` calls `refresh_all` for specs | P1 |
| `projects/LoanOps.Sse/packages/sse/types.py` | `AppTarget`, `CatalogSource` status fields, `BreakerRegistry` Protocol | P1/P4 |
| `projects/LoanOps.Sse/packages/sse/loader.py` | `SpecSource`, `spec_sources`/`app_targets` ctor args, registry mode, `resolve_swagger_links`, `target_for`, registry-derived `allowed_origins` | P1/P4 |
| `projects/LoanOps.Sse/packages/sse/embed_openapi.py` | Use `resolve_swagger_links` (fixes ignored `SSE__SWAGGER_URLS`); P3: thin wrapper over `api_index.refresh` sidecar output | P1/P3 |
| `projects/LoanOps.Tools/packages/tools/factory.py` | Select catalog source; wire resolver, search service, broker, breaker | P1–P4 |
| `projects/LoanOps.Sse/packages/sse/catalog.py` | `find_operation` delegates to resolver when provided; GET/HEAD `has_request_body` ignores Swagger 2 `consumes` (§3.2) | P2 |
| `projects/LoanOps.Sse/packages/sse/tools.py` | Search via `ApiSearchService`; filter args; no-confident-match header; `resolve_invoke_target` + `application` arg (§6.4 step 0); call payload fields | P2–P4 |
| `projects/LoanOps.CapabilityKg/packages/capability_kg/sparql.py` + `catalog.py` | `CapabilityRecord.application_id: str \| None = None`, sourced from the existing `belongsToApp` predicate: add `OPTIONAL { { ?capability loanops:belongsToApp ?app } UNION { ?capability loanops:implementedBy ?appOp . ?appOp loanops:belongsToApp ?app } }` to `_OP_OPTIONALS` and `?app` to `_SELECT`; `_to_record` maps the app URI local name `app_<id>` → `<id>` (strip the `app_` prefix). `eakg/graph_build.py` already adds `cap → belongsToApp → app_<id>`; `capability_kg/extract_openapi.py` adds it on the op, hence the UNION. `eakg/merge.py` is **not** changed (it flattens graphs and loses per-repo provenance) | P2 |
| `projects/LoanOps.Eakg/packages/eakg/taac.py` | `load_api_identifier(path)` for the interim spec-token source (§3.6) | P1 |
| `projects/LoanOps.McpServer/packages/mcp_server/capability_bind.py` | `resolve_binding` maps to `public_id` via resolver; `CapabilityBinding.application_id` | P2 |
| `projects/LoanOps.McpServer/packages/mcp_server/server.py` | Tool arg additions; `/ready` per-app body | P3/P5 |
| `projects/LoanOps.Tools/packages/tools/modular_tools.py` | Hot-reload fingerprint over registry + `current.json` (P1, §2.3 A.3), extended with `operations.json` (P2); `operation_resolver()`; `readiness_snapshot` per app (P5) | P1/P2/P5 |
| `projects/LoanOps.Sse/packages/sse/invoke.py` | Per-app flow §6.4 | P4 |
| `projects/LoanOps.Common/packages/common/providers/factory.py` | `get_credential_broker()` | P4 |
| `../provider_contracts/provider_contracts/vector_store/{qdrant,mock,pgvector,azure_ai_search}.py` + contract test | list ⇒ any-of filter, `supports_any_of_filter`, `ensure_namespace` (D6) | P3 |
| `data/eakg/registry/repositories.yaml` | `environments.local` entries with `spec_fixture`; `lifecycle`; `service_url_key` | P1 |
| `Makefile` (`demo` target) + new `scripts/demo.ps1` | Today `demo` backgrounds uvicorn with POSIX `&`, which does not work on Windows PowerShell 5.1. Add a PowerShell-native launcher (`Start-Process` for uvicorn, then `npm run dev`) and point the Windows instructions at it, so SC-010 can be validated on this workstation. Not feature logic | P1 |
| `pyproject.toml` (root), `projects/LoanOps.Tools/pyproject.toml` | Add `LoanOps.ApiIndex` member / dependency | P2 |
| `.env.example` | P1: explicit `SSE__CATALOG_SOURCE=registry`, `EAKG__ENVIRONMENT=local` (D1); later phases: new env vars (after approval) | P1/P3/P4/P5 |

---

## 9. Implementation Details

### 9.1 Phase 1 — Registry, spec cache, catalog from cache

- `RepositoryRecord.from_dict`: parse `environments` as `{k: AppEnvironment(**v)}` tolerating missing keys; unknown env keys are kept but reported by validation; `git_url` default `""`. `to_dict` emits new fields only when non-default to keep YAML diffs small.
- `RepositoryRegistry.list_active(env)`: `issues = self._issues()` (cached `validate_registry(self)`), then `[r for r in records if r.lifecycle != "retired" and env in r.environments and r.environments[env].enabled and not blocking_issues(r, env, issues)]` (§4.6).
- `registry_import.import_taac(registry, taac_path, env, dry_run)`:
  - `ServiceUrls` key→url; `app_id = taac.url_key_to_app_id(key)`; audience = `Auth0.Api.Identifier` (open question: per-app audiences).
  - For an existing record with matching `application_id` (or `service_url_key`): set `environments[env].base_url` / `auth_audience` **only if blank**; record conflicts (different non-blank value) in the report without overwriting.
  - Keys with no registry record are listed as `unregistered_candidates` — never auto-registered (registration stays an operator action, FR-001).
- `spec_cache` per §3.6. `fetch_spec_with_source` uses `follow_redirects=False` and manually follows ≤ 3 redirects only when the `Location` origin equals the base origin.
- `onboard_repository`: before extract, `res = await refresh_spec(record, cfg.eakg.environment, store, token_source=interim_spec_token_source(cfg))` (§3.6; audience-restricted); after extract, `doc, _ = read_current_spec(...)`; `enrich_interface(iface, store, mode=..., spec=doc)`. When `record.git_url == ""`: skip access/clone/extract, run `refresh_spec` only, mark `index_status="indexed"` if spec ok else `"failed"`.
- `OpenApiCatalogService.load()` registry mode: `for s in spec_sources(): ops += parse_openapi_document(s.document, s.source_id, s.label, s.base_url) if s.document else []`; one `CatalogSource` per app with `status`, `fetched_at`, `stale`, `error`. No `httpx` client is created in this branch (asserted by test).
- `build_modular_tools_client`: `source = resolve_catalog_source(cfg, registry, store)` (D1); registry mode passes `spec_sources=lambda: build_spec_sources(cfg)` and `app_targets=lambda: build_app_targets(cfg)`.
- Hot reload (FR-002, built in P1): `ModularToolsClient` holds `catalog_fingerprint()` = tuple of `(path, mtime_ns, size)` for the registry YAML and each active app's `openapi/<env>/current.json`. Before each tool call, at most once per `_RELOAD_CHECK_INTERVAL_S`, it recomputes the fingerprint; on change it rebuilds the catalog from disk off the request path (`asyncio.Lock`, one rebuild at a time), swaps it atomically, and re-primes the credential broker for new apps (P4). Rebuild errors keep the old catalog and set warning `catalog_reload_failed`.
- `.env.example`: set `SSE__CATALOG_SOURCE=registry` and `EAKG__ENVIRONMENT=local` (D1); keep `SSE__USE_FIXTURE=true` with a comment that it applies only to `SSE__CATALOG_SOURCE=fixture` or to `auto` when no registry spec is available.
- `resolve_swagger_links(sse)` moves the existing factory logic (links, then urls→slug) into `loader.py`; factory and `embed_openapi` both call it.

### 9.2 Phase 2 — Unified record and bind fix

- `build_operations` per §3.2; persisted with atomic write; `inputs` map lets `refresh app` rebuild one app and splice it into the set (O(ops of app)).
- `OperationCatalog` (runtime): loads `operations.json` (fallback: build in-process from cached specs + interfaces); exposes `ops`, `by_public_id`, `resolver`, `keyword_index`; P2 extends the P1 `catalog_fingerprint()` with `operations.json` (mtime_ns+size).
- `find_operation(..., resolver=...)`: when a resolver is supplied, `operation_id` goes through `resolver.resolve`; `Ambiguous` raises `ToolPolicyError("ambiguous operation 'X': fees:getFees (Fees), escrow:getFees (Escrow Manager) — pass the application-qualified id")`.
- `capability_bind.resolve_binding(catalog, capability_id, resolver)`: `record = catalog.get_capability(cid)`; `res = resolver.resolve(record.operation_id, application_id=record.application_id)`; `Resolved` → `CapabilityBinding(operation_id=res.public_id, application_id=..., read_only=res.read_only, permission=...)`; non-read-only → `PolicyError("capability 'X' maps to a data-changing operation; not callable in this version")` (US5 #2).
- `api_index report`: JSON `{openapi_only:[public_id], eakg_only:[{app, eakg_key, path}], ambiguous:[...], capabilities_unbound:[capability_id]}`.

### 9.3 Phase 3 — Vector index and search

- `reindex` per §3.4; called by `refresh app|all|nightly` after `build_operations`.
- `ApiSearchService` per §3.5; backend label in output header: `(vector index)`, `(fallback: local vector sidecar)`, `(keyword search — embeddings unavailable)`.
- Sidecar: same `OpenApiEmbeddingEntry` format keyed by `public_id`, written by `reindex`; `embed_openapi` CLI becomes `refresh all --sidecar-only` equivalent.
- `API_INDEX__ENABLED=false` (default until approved/rolled out) ⇒ existing `search_operations_with_embeddings` path over the unified ops.

### 9.4 Phase 4 — Credentials and per-app invoke

- `get_credential_broker()`: `static` → `CachingCredentialBroker(StaticCredentialBroker(get_secrets_provider(), shared_token=cfg.sse.api_key, shared_apps=set(cfg.credentials.static_shared_apps)))`; `mock` → `CachingCredentialBroker(MockCredentialBroker({}))`.
- `refresh_spec` token source becomes `lambda app, aud: broker.get_token(app, aud)` (`CredentialNotConfigured` ⇒ unauthenticated attempt, recorded as `credential: missing`). This retires `interim_spec_token_source` and closes the P1–P3 interim arrangement (§3.6, §12).
- MCP / Agent API lifespan calls `await broker.prime([r.application_id for r in registry.list_active(env)])` once at startup and after a catalog reload adds apps (§6.2).
- `allowed_origins()` registry mode: `sorted({t.origin for t in app_targets().values()})`; per-call origin binding §6.4.
- Tool description for `call_sse_api` adds: "If `outcome` is `no_access` or `unavailable`, tell the user the `error` text as-is and continue with parts of the answer that do not depend on that application."

### 9.5 Phase 5 — Health, metrics, schedule, scale

- `AppHealthService.snapshot()` merges registry issues, spec pointers, operations counts, index manifest coverage, `broker.check()`, last invoke outcome (in-memory ring per app), breaker state.
- Metrics via `get_telemetry_provider().record_metric`: `api_index.search.latency_ms` (attrs: backend), `api_index.search.shortlist_size`, `sse.invoke.latency_ms` (app, outcome), `sse.invoke.outcome` (app, outcome, value 1), `api_index.refresh.duration_ms` (app, status), `api_index.reindex.embedded` (count), `api_index.catalog.load_ms`.

### 9.6 Scheduled refresh

- Production: external scheduler (ECS scheduled task / cron) runs `python -m packages.api_index.refresh nightly` at `EAKG__NIGHTLY_HOUR` — existing setting, frequency open (story Q3).
- Optional in-process: when `API_INDEX__SCHEDULER_ENABLED=true`, MCP lifespan starts one asyncio task: sleep until next `nightly_hour` UTC, run `refresh nightly` under a file lock (`.eakg-workspace/.locks/api_index_refresh`) so multiple replicas never refresh concurrently.
- `nightly` = `refresh_all` specs → for apps with changed `spec_hash` or `interface_hash`: rebuild their records → `reindex` (incremental) → retired apps' points deleted.

---

## 10. Integration Points

| Integration | Method | Auth | Error handling |
|---|---|---|---|
| Enterprise app OpenAPI endpoints | HTTPS GET at refresh time only | Bearer from `CredentialBroker` (P4) / `EAKG__LIVE_SPEC_TOKEN` (P1–P3) | Per-app timeout 30 s; failure keeps last-good spec, pointer `status=failed` |
| Enterprise app data endpoints | HTTPS GET/HEAD via `invoke_sse_api` | Per-app token, origin-bound | Outcome classification §6.4; breaker §3.8 |
| TAAC client config | Local JSON file (`EAKG__TAAC_CONFIG_PATH` / fixture) | n/a | Missing file ⇒ import report error, registry unchanged |
| GitLab | Existing `access_check` / `clone_or_fetch` | Existing | Unchanged; API-only apps skip it |
| VectorStore provider (Qdrant local / Qdrant Cloud / pgvector) | `create_collection`, `upsert`, `search`, `delete` | Provider config | Search error ⇒ sidecar fallback; refresh error ⇒ app reported `indexed=false`, CLI exit 2 |
| Embedding provider | `embed`, `embed_batch` | Provider config | Refresh: retry batch ×2 then mark rows unindexed; search: keyword fallback |
| Secrets provider | `get_or_default("APP_TOKEN_<APPID>")` | n/a | Missing ⇒ `CredentialNotConfigured` |
| Audit sink | `emit(AuditEvent)` | n/a | Suppressed exceptions (existing pattern) but counted in metric `audit.emit.failed` |
| Telemetry provider | `record_metric` | n/a | Best-effort |

---

## 11. Edge Cases & Error Handling

| Story edge case | Handling |
|---|---|
| App registered but spec unavailable/invalid | `refresh_spec` → pointer `status=failed`, `last_error`; no prior spec ⇒ app has 0 ops, `/ready` shows `spec_status=failed`, `indexed=false`, listed as degraded (FR-008); prior spec ⇒ served and flagged `stale` (FR-016). Invalid = not a JSON object or lacks `paths`/`openapi`/`swagger`. |
| Spec changes between refreshes (added/renamed/removed ops) | New `spec_hash` ⇒ app rebuilt; renamed op ⇒ new `uid`/`public_id` upserted, old deleted (manifest diff); `public_id` lookups for the old name return `NotFound` with suggestions. |
| App removed/retired | `lifecycle: retired` ⇒ excluded from `list_active`; next refresh deletes its points and records; runtime hot-reload drops it from resolver (call ⇒ `NotFound`, FR-003); response cache entries keyed by URL expire by TTL (60 s) and the origin is no longer allowed, so cached hits are not served: cache lookup happens **after** `assert origin == target.origin`. |
| App down at call time | Connect/timeout/5xx ⇒ `outcome=unavailable` with app-named message; breaker opens after 5; other apps unaffected (US3 #3/#4). |
| Access revoked between discovery and call | 401/403 ⇒ `invalidate` + single retry ⇒ `no_access`; last invoke outcome feeds `/ready` `issues: ["access_denied"]` (US4 #3). |
| Same-named ops in two apps | `public_id` is app-qualified; bare name resolves only if unique, else `Ambiguous` error listing both; search output always prints application label + id (FR-006). |
| Live address with no source, or source with no address in this env | Empty `git_url` ⇒ callable, `code_unit` absent, provenance says source unknown (FR-022). `git_url` set and no `base_url` for `EAKG__ENVIRONMENT` ⇒ excluded from `list_active` for calls; EAKG shard may still explain the capability; invoke returns `not_registered_in_env`. |
| Registration env ≠ runtime env | Process serves only `EAKG__ENVIRONMENT`; registry validation flags `env_mismatch`/`env_origin_reuse` and excludes the entry (FR-019, US9 #3). |
| Capability points to non-read-only op | Resolver returns record with `callable=false` ⇒ `PolicyError` "data-changing operation; not callable in this version" (US5 #2, FR-020). |
| Many apps fail at once (shared outage) | Refresh: each app keeps last-good spec; CLI exit 2. Runtime: breakers open per app; `/ready` stays 200 with `status=ready`, `summary.degraded=N`; if **all** apps lack specs and no `operations.json` exists ⇒ `/ready` 503 `no_catalog`. |
| Vector store down | Search falls back to sidecar; `/ready` warning `vector_store_unavailable`. |
| Embed model changed | New namespace build (D7); until done, search uses the previous namespace from manifest. |
| `operations.json` corrupt | Fallback to in-process build from cached specs; warning `operations_json_invalid`. |
| Duplicate `operationId` within app | `public_id` fallback to `METHOD_slug` (§4.3). |
| Client sends `Authorization` header | Stripped (§6.4); never forwarded. |

Error types: `RegistryValidationError(issues)`, `SpecFetchError` (internal, captured in pointer), `CredentialError` family, `ToolPolicyError` / `PolicyError` (existing), `IndexError`-free `IndexReport.failed_apps`.

---

## 12. Security Considerations

| Concern | Mechanism | Story ref |
|---|---|---|
| Credentials sent to wrong app | Per-call origin binding to `target.origin`; shared token only for `CREDENTIALS__STATIC_SHARED_APPS`; registry `origin_collision` check | NFR-010 |
| Token leakage | `SecretStr`; tokens never in audit payload, logs, `/ready`, exceptions; `sanitize_args` (existing) plus header stripping | NFR-010 |
| SSRF via registry | https-only (loopback http in `local`), no userinfo, no non-loopback IP literals, same-origin redirects only (spec fetch + invoke `follow_redirects=False`) | FR-019 |
| Mutating calls | GET/HEAD only (existing), `callable` requires `read_only`, no body ever sent | FR-020, NFR-005, SC-009 |
| Cross-environment leakage | Environment in namespace name, operations path and audit; process serves one env | FR-019 |
| Audit | `sse.live_read` event for every invoke (incl. rejected/no_access) with app, op, env, outcome | FR-021, SC-008 |
| PII | All fixtures and benchmark synthetic; hosts `*.example.invalid`; response bodies not persisted beyond existing 60 s cache | NFR-008 |
| Retention | Audit retention unchanged (JSONL / CloudWatch) — pending story Q4 | NFR-009 |

---

## 13. Performance Considerations

| Target (story) | Mechanism | Metric | Budget |
|---|---|---|---|
| NFR-002 / SC-004 ready < 10 s, flat in app count | No network at boot; read `operations.json` (1 file) + registry; lazy vector store | `api_index.catalog.load_ms` | < 3 s at 30 apps / 5k ops |
| NFR-003 / SC-003 discovery p95 < 1.5 s | Query-embed LRU; 2 ANN queries; O(K) blend | `api_index.search.latency_ms` p95 | embed ≤ 600 ms, vector 2×≤ 50 ms, blend ≤ 20 ms |
| NFR-004 isolation | Per-app breaker, per-app timeouts (connect 3 s, read 10 s), per-app refresh tasks | `sse.invoke.latency_ms` by app | healthy-app p95 unchanged (± 10 %) with 20 % apps failing |
| SC-002 relevance | Shortlist + keyword-exact inclusion + blend | benchmark top-5 hit rate | ≥ 90 % |
| US7 incremental | `text_hash` diff, `spec_hash` short-circuit | `api_index.reindex.embedded` | unchanged nightly: 1 embed call |

Memory: 5k `UnifiedOperation` ≈ 10–15 MB; keyword index ≈ 2–3 MB; no vectors held in memory when the vector index is active.

---

## 14. Testing Strategy

All tests async (`pytest-asyncio`), no network (`httpx.MockTransport` injected via a transport parameter on the HTTP helpers), synthetic data only, `mypy --strict` clean.

### 14.1 Unit / integration by phase

| Phase | Test | Covers |
|---|---|---|
| P1 | one `application_id` resolves `git_url` and `environments[env].base_url`; TAAC import fills a blank `base_url` and does not write `git_url`; empty `git_url` stays callable; missing env `base_url` is not callable in that env | FR-022 |
| P1 | registry round-trip with/without `environments`; legacy YAML loads unchanged | FR-001 |
| P1 | each validation rule in §4.1 produces its code; invalid record excluded, others listed | US1 #4, FR-019 |
| P1 | `import_taac` fills blanks, never overwrites, reports conflicts + unregistered candidates | FR-001 |
| P1 | `refresh_spec`: ok, 404-all-candidates, invalid JSON, timeout ⇒ last-good kept + `failed` pointer; prune to 3 | FR-016, US3 #2 |
| P1 | `refresh_all` with one app raising ⇒ others ok | FR-007 |
| P1 | registry catalog mode builds ops with **no `httpx.AsyncClient` constructed** (monkeypatch raises) | NFR-002 |
| P1 | `onboard_repository` passes `base_url`-fetched spec to `enrich_interface` | ADR-024 gap |
| P1 | shipped `.env.example` + committed local fixtures ⇒ `resolve_catalog_source == "registry"`; `auto` + `SSE__USE_FIXTURE=true` + fixtures present ⇒ `registry` | RC-001, NFR-007 |
| P1 | fingerprint change on registry YAML or `current.json` swaps catalog without restart; failed rebuild keeps previous catalog | FR-002, RC-009 |
| P1 | `embed_openapi` honors `SSE__SWAGGER_URLS` via `resolve_swagger_links` | bug fix |
| P2 | `normalize_path` table tests; exact / suffix / ambiguous / eakg_only / openapi_only joins incl. `/{id}/Summary` ↔ `/api/Loans/{loan_id}/Summary` | FR-012, FR-013 |
| P2 | resolver: `get_loan_summary`, `GetLoanSummary`, `loanservices:getLoanSummary` ⇒ same record; cross-app duplicate ⇒ `Ambiguous` | FR-006, SC-007 |
| P2 | `apply_capability_bind` with `capability_id=GetLoanSummary` ⇒ `operation_id=loanservices:getLoanSummary`; non-read-only ⇒ PolicyError | US5 #1/#2 |
| P2 | `report` lists mismatches | FR-013, US5 #3 |
| P3 | `reindex`: first run embeds all; second run embeds 0; one changed op ⇒ 1; removed op ⇒ delete; model change ⇒ new namespace | US7, FR-015 |
| P3 | `provider_contracts` vector-store contract test: list filter ⇒ any-of, scalar ⇒ equality (mock always; qdrant when a local Qdrant is reachable, else skipped) | FR-017 |
| P3 | search: application filter returns only that app; permission filter; shortlist contains keyword-exact app; vector error ⇒ sidecar label; embed error ⇒ keyword label; blended top score &lt; 0.35 ⇒ header `No confident match` | FR-017, FR-018, US2 #4, US8 |
| P3 | same app in `dev` and `stage` with different fixture specs ⇒ each process sees only its env's operations and namespace | US9 #1/#2 |
| P4 | broker contract tests (static, mock): configured app token; unknown app ⇒ `CredentialNotConfigured`; `repr` hides token; `check` performs no I/O; caching single-flight (10 concurrent ⇒ 1 inner call); `invalidate` | FR-009, FR-011, NFR-010 |
| P4 | invoke: per-app token used; app B never receives app A token (MockTransport asserts header per host); 401 ⇒ retry once ⇒ `no_access`; 403 ⇒ `no_access`; timeout ⇒ `unavailable`; breaker opens after 5; client `Authorization` stripped; origin mismatch ⇒ PermissionError | FR-010, NFR-010, US4 |
| P4 | audit `sse.live_read` emitted for ok/no_access/unavailable/rejected | FR-021, SC-008 |
| P4 | registry mode raw `method`+`path` without `application` ⇒ `outcome=rejected`, MockTransport sees no request and no Authorization header | RC-002, NFR-010 |
| P4 | spec `servers` on a different origin ignored; same-origin `servers` path kept; issue `spec_server_origin_mismatch` | RC-005 |
| P4 | SC-006 replay: synthetic loan summary / payment schedules / escrow with one app lacking access ⇒ named message, zero generic "unauthorized" strings | SC-006 |
| P4 | one app `unavailable`, second app healthy ⇒ answer still covers the healthy app | US3 #3 |
| P5 | `/ready` per-app states (healthy, stale, unindexed, access-failing, unreachable) | FR-014, US6 |
| P5 | scheduler lock prevents concurrent refresh; hot reload swaps catalog on fingerprint change | US7, FR-002 |

### 14.2 Scale suite (`-m scale`, Phase 5)

`gen_scale_fixture.py --apps 30 --ops-per-app 170 --seed 42` generates registry (`local` env, `spec_fixture`), specs and `api_discovery_benchmark.jsonl` (≥ 100 questions, synthetic domain vocabulary, ≥ 10 cross-app same-name pairs). Tests:

| Test | Assertion | Story |
|---|---|---|
| `test_ready_flat` | catalog load at 5 apps and 30 apps both < 10 s and ratio < 2× | SC-004, NFR-002 |
| `test_discovery_p95` | 200 queries, p95 < 1.5 s with mock vector store + deterministic embedder (latency budget) | SC-003 |
| `test_discovery_p95_local` | same 200 queries against local `bge-small` + local Qdrant; records embed ms and ANN ms against the §13 budgets (600 ms embed, 50 ms ANN). Required in `p5-quality-gates` when those services are up; the gate run starts local Qdrant | SC-003, §13 |
| `test_top5_recall` | local `bge-small` + local Qdrant ⇒ top-5 ≥ 90 %. **Not skippable** in `p5-quality-gates`: missing model or Qdrant fails the gate | SC-002, RC-013 |
| `test_isolation_latency` | healthy-app `sse.invoke` p95 stays within ±10 % when 6/30 apps are delayed or failing via MockTransport | NFR-004, RC-012 |
| `test_isolation_20pct` | 6/30 apps unreachable ⇒ 24 discoverable & callable, 6 degraded on `/ready` | SC-005 |
| `test_incremental_one_changed` | change 1 app spec ⇒ only that app reprocessed | US7 #2 |

### 14.3 Gates per phase

`uv run mypy --strict` on touched projects; `uv run pytest` for touched projects + `contract_tests`; `uv run python scripts/check_project_refs.py`; grep gates from AGENTS.md (no concrete provider imports outside `packages/common/providers/`, no `os.environ`/`os.getenv` outside `settings.py`); `make demo` smoke with zero cloud creds (SC-010); `graphify update .`.

### 14.4 Coverage / thresholds — G10

New modules ≥ 90 % line coverage. Benchmark thresholds equal story targets (SC-002/003/004) and are **added**, never lowered; final values wait for story Q2.

---

## 15. Configuration

All via `packages/common/settings.py`, nested delimiter `__`. **None approved yet.**

| Env var | Settings field | Type | Default | Required | Phase / Gate |
|---|---|---|---|---|---|
| `EAKG__ENVIRONMENT` | `EakgConfig.environment` | `Literal["local","dev","stage","prod"]` | `"local"` | no | P1 / G3 |
| `SSE__CATALOG_SOURCE` | `SseConfig.catalog_source` | `Literal["auto","registry","swagger_links","fixture"]` | `"auto"` | no | P1 / G3 |
| `API_INDEX__ENABLED` | `ApiIndexConfig.enabled` | `bool` | `false` | no | P3 / G5 |
| `API_INDEX__NAMESPACE_PREFIX` | `ApiIndexConfig.namespace_prefix` | `str` | `"api_ops"` | no | P3 / G5 |
| `API_INDEX__APP_SHORTLIST_SIZE` | `ApiIndexConfig.app_shortlist_size` | `int` (1–20) | `5` | no | P3 / G5 |
| `CREDENTIALS__PROVIDER` | `CredentialsConfig.provider` | `Literal["static","mock"]` | `"static"` | no | P4 / G8 |
| `CREDENTIALS__STATIC_SHARED_APPS` | `CredentialsConfig.static_shared_apps` | `list[str]` (JSON) | `[]` | no | P4 / G8 |
| `APP_TOKEN_<APPID>` (secret name, via `SecretsProvider`) | — | `str` | unset | per app | P4 / G8 |
| `API_INDEX__STALE_AFTER_HOURS` | `ApiIndexConfig.stale_after_hours` | `int` | `48` (pending Q3) | no | P5 / G9 |
| `API_INDEX__SCHEDULER_ENABLED` | `ApiIndexConfig.scheduler_enabled` | `bool` | `false` | no | P5 / G9 |

Reused (no change): `EAKG__REGISTRY_PATH`, `EAKG__SHARD_DIR`, `EAKG__LIVE_SPEC_TOKEN` (P1–P3 spec fetch; superseded by broker in P4), `EAKG__NIGHTLY_HOUR`, `EAKG__TAAC_CONFIG_PATH`, `SSE__API_KEY` (becomes the static broker shared token), `SSE__SWAGGER_LINKS`/`SSE__SWAGGER_URLS` (dev override), `VECTOR_STORE__*`, `EMBEDDING__*`, `CAPABILITY_KG__ENFORCE_PERMISSIONS`, `CAPABILITY_KG__ALLOWED_PERMISSIONS`.

Local `.env.example` (after approval): `EAKG__ENVIRONMENT=local`, `SSE__CATALOG_SOURCE=auto`, `CREDENTIALS__STATIC_SHARED_APPS=["loanservices"]` only if the developer has a dev token.

---

## 16. Deployment Considerations

- Pipeline (refresh CLI) and runtime (MCP / Agent API) share `EAKG__SHARD_DIR`. On AWS: shard dir on EFS (or S3 sync before start); vector store Qdrant Cloud; refresh as ECS scheduled task; runtime tasks read-only on shard dir.
- Rollout per phase behind defaults that preserve today's behavior: `SSE__CATALOG_SOURCE=auto` with existing `.env` (swagger links set) keeps legacy; `API_INDEX__ENABLED=false`; `CREDENTIALS__PROVIDER=static` with `SSE__API_KEY` + explicit shared apps.
- `make demo`: registry `local` env + `spec_fixture` + mock/local Qdrant + static broker; zero cloud credentials (NFR-007, SC-010).

## 17. Dependencies

External (already in lockfile): `httpx`, `pydantic`, `pyyaml`, `rdflib`, `qdrant-client` (provider extra). **No new third-party libraries.**

Internal: `loanops-common`, `loanops-sse`, `loanops-eakg`, `loanops-capability-kg`, `provider_contracts` (vector-store filter change, G6). Organizational: application teams must publish specs and grant access; identity decision (story Q1) for non-static brokers.

## 18. Migration Path

1. Registry YAML is additive: existing 3 records load unchanged (`environments={}` ⇒ not active in any env until filled). P1 adds `local` entries for escrow/fees/loanservices and runs `import-taac --env dev` for dev.
2. Swagger-link users: no change until they unset `SSE__SWAGGER_LINKS`; `CONTEXT.md` documents `auto` precedence.
3. OpenAPI sidecar (ADR-023): kept; written by `reindex` from P3; `embed_openapi` retained as wrapper; superseded as primary when `API_INDEX__ENABLED=true`.
4. `SSE__API_KEY`: from P4 only sent to `CREDENTIALS__STATIC_SHARED_APPS`; operators must list apps or set `APP_TOKEN_<APPID>` — release note required.

## 19. Open Technical Questions

Story `[NEEDS CLARIFICATION]` items — **not resolved here**; defaults below are placeholders that keep work unblocked and are trivially changeable.

| # | Question (story ref) | Spec impact | Placeholder |
|---|---|---|---|
| OQ-1 | Access model: service identity per app, on-behalf-of user, or mix (FR-011, story Q1) | Which non-static `CredentialBroker` impl to build next; `Principal` usage | Static broker only; protocol supports both |
| OQ-2 | Confirm targets: ready < 10 s, discovery p95 < 1.5 s, top-5 ≥ 90 % (NFR-002, NFR-003, SC-002, story Q2) | Scale-suite thresholds (G10) | Story values |
| OQ-3 | Refresh frequency and stale window (FR-015, story Q3) | `EAKG__NIGHTLY_HOUR` schedule, `API_INDEX__STALE_AFTER_HOURS` | Nightly, 48 h |
| OQ-4 | Audit/question-history retention and applicable regulations (NFR-009, story Q4, Privacy) | Audit sink retention config, data classification of cached responses | Unchanged existing retention |
| OQ-5 | Permission filter: user's entitlements vs assistant's access (FR-017, story Q5) | Source of `permission` allow-set in search post-filter | Assistant-level `CAPABILITY_KG__ALLOWED_PERMISSIONS` |
| OQ-6 | Product owner / technical lead (story Stakeholders) | Approval routing for G1–G10 | — |
| OQ-7 | Does each app have its own token audience, or is TAAC `Auth0.Api.Identifier` shared? | `registry_import` audience seeding | Seed shared Identifier; operators override per app |
| OQ-8 | Should EAKG extractor compose full controller routes so joins are exact? | Reduces `suffix`/`ambiguous` joins | Suffix join (D4) |
| OQ-9 | Spec from deployed env vs from repo build artifact (team `swagger tofile` still open per logs) | `spec_fixture`/artifact path as alternative source | Deployed-env fetch; fixture for local |

## 20. References

- Story: [enterprise-app-scale.story.md](./enterprise-app-scale.story.md)
- Plan: [enterprise-app-scale.plan.md](./enterprise-app-scale.plan.md)
- ADR-024, ADR-023, ADR-022, ADR-016: [decisions.md](../../../decisions.md)
- Auth program (parked): [docs/ARCHITECTURE_REVIEW_LAYER2.md](../../../docs/ARCHITECTURE_REVIEW_LAYER2.md) §8
- Smoke evidence 2026-10-08: [logs.md](../../../logs.md)
