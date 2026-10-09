# Spec Design Review — enterprise-app-scale (iteration 1)

## Header

| Field | Value |
|---|---|
| Feature | `enterprise-app-scale` |
| Spec dir | `.ai/specs/enterprise-app-scale/` (README.md, story, spec, plan — all present) |
| Story reference | `.ai/specs/enterprise-app-scale/enterprise-app-scale.story.md` (local, Draft) |
| Related ADR | `decisions.md` ADR-024 (Proposed 2026-10-08) |
| Iteration | 1 |
| Strictness | normal |
| Date | 2026-10-08 |
| Method | `spec-spec-design-review-rubric` Passes 1–5; claims verified with `graphify query` + targeted reads of the live code and `../provider_contracts` |

## Verdict

**fail** — overall **3.8**, **mustFixCount = 2**, shouldFixCount = 16.

The design is deep and mostly transcription-ready. It fails on two cheap but blocking items. First, the spec's own `auto` catalog-source precedence plus today's `SSE__USE_FIXTURE=true` default means `make demo` would never run registry mode, which contradicts the Phase 1 acceptance (RC-001). Second, registry-mode `call_sse_api` with a raw `method`+`path` and no resolved operation has no defined target, so which application's credential is used is unspecified (NFR-010) (RC-002).

**Phase 1 blockers (OQ / gates):** none of OQ-1…OQ-9 technically blocks Phase 1 code. Each has a usable placeholder: P1 uses the existing `EAKG__LIVE_SPEC_TOKEN`, OQ-7 seeds the shared TAAC identifier, and OQ-9 uses deployed-env fetch plus fixtures. Phase 1 is blocked by design on G1–G3. **OQ-6 (no product owner / technical lead) is the effective P1 blocker**, because nobody is named to approve G1–G3 (RC-016). RC-001 is also inside P1 scope and must be fixed before P1 starts.

## Pass Scores

| Pass | Dimension | Score | Justification |
|---|---|---|---|
| 1 | Coverage | 4 | Every FR/NFR/SC maps to a cited design element. FR-002 is claimed by P1 but hot-reload only lands in P5. US2 #4 (no-answer), US9 #1/#2 and the FR-011 cache path are partial. |
| 2 | Soundness | 4 | Pipeline/runtime split, join, resolver, broker and breaker are coherent and justified with alternatives. One must-fix: the raw method+path invoke has no target. Several edge mechanisms need tightening: Qdrant namespace vs `create_collection`, list filters before G6, `servers` basePath, the interim spec-token scope, the cache key, and `check()` without I/O. |
| 3 | Buildability | 4 | Pseudocode, complexity, signatures, file tables and 56 `p{N}-slug` todos (count verified) are present. Some referenced types are undefined. The capability `application_id` source points at the wrong module. P1's reload depends on a P2 artifact. |
| 4 | Testability | 4 | §14.1/§14.2 map concrete, network-free tests to FR/SC IDs. Gaps: NFR-004 latency isolation is not asserted, US9 env separation is not tested, the SC-002 gate can silently skip, and US2 #4 / US3 #3 have no verification path. |
| 5 | Consistency | 3 | The demo/`auto` precedence contradiction (must-fix). The "11th provider category" claim is wrong because 13 factories already exist. Plan Notes cite OQ-1…OQ-6 while the spec has OQ-1…OQ-9. FR-002 phase attribution conflicts with where hot-reload is built. |

`overall = round1(mean(4, 4, 4, 4, 3)) = 3.8`; mustFixCount 2 ⇒ **fail**.

## Requirement Coverage

| Req | Verdict | Design location / gap |
|---|---|---|
| FR-001 single registration | ADDRESSED | spec §7 D1, §4.1, §9.1; registry_import never auto-registers |
| FR-002 discoverable w/o further step | PARTIAL | §2.3 A.3 hot-reload keyed on `operations.json` (P2), built in `p5-scheduler`; P1 claims FR-002 but runtime `OpenApiCatalogService._catalog` is cached until restart (RC-009) |
| FR-003 retire | ADDRESSED | §11 "App removed/retired", `list_active` |
| FR-004 ranked discovery | ADDRESSED | §3.5 |
| FR-005 citation app+op | ADDRESSED | §5.1 `citation=tool:call_sse_api:<public_id>` + `application` |
| FR-006 same-name disambiguation | ADDRESSED | §3.2 public_id, §3.3 `Ambiguous`, D5 |
| FR-007 per-app isolation | ADDRESSED | §3.6 `refresh_all` semaphore/timeout, §3.8 breaker |
| FR-008 degraded not dropped | ADDRESSED | §9.1 `CatalogSource.status`, §5.2 `/ready` |
| FR-009 per-app access | ADDRESSED | §6.2 broker, §6.4 — except raw method+path path (RC-002) |
| FR-010 clear no-access msg | ADDRESSED | §6.4 outcome classification, D10 |
| FR-011 swappable access model | PARTIAL | §6.2 `Principal`, future brokers; response cache key ignores app/principal, would leak across users under OBO (RC-007) |
| FR-012 capability callable by name | ADDRESSED | §3.3, §9.2 bind fix (source of `application_id` misdirected — RC-010) |
| FR-013 mismatch report | ADDRESSED | §9.2 `api_index report`, §5.2 `catalog_health` |
| FR-014 per-app health | ADDRESSED | §5.2, §9.5, `health --probe` |
| FR-015 scheduled incremental refresh | ADDRESSED | §3.4, §9.6 (frequency = OQ-3) |
| FR-016 last-good + stale | ADDRESSED | §3.6, §4.2 |
| FR-017 app/permission filter | ADDRESSED | §3.5, §5.1 (permission source = OQ-5); pre-G6 behaviour unsound on Qdrant (RC-004) |
| FR-018 narrow apps first | ADDRESSED | §3.5 stage 1, D8 |
| FR-019 env separation | ADDRESSED | §4.1 validation, namespace per env, process serves one env |
| FR-020 read-only | ADDRESSED | §6.4, §3.2 `read_only` rule, §12 |
| FR-021 audit per read | ADDRESSED | §6.4 `sse.live_read`, §12 |
| NFR-001 scale | ADDRESSED | §13, §14.2 |
| NFR-002 readiness | ADDRESSED | D2, §2.3 C, `test_ready_flat` |
| NFR-003 discovery p95 | ADDRESSED | §3.5, §13, `test_discovery_p95` (mock-only — RC-013) |
| NFR-004 isolation latency | PARTIAL | §3.8, §13 budget ±10 %; no test asserts latency (RC-012) |
| NFR-005 never mutate | ADDRESSED | §12 |
| NFR-006 grounding | ADDRESSED | §5.1 citation; policy citations unchanged |
| NFR-007 local-first | PARTIAL | §16 claims demo = registry + fixtures, but `auto` precedence resolves to `fixture` under shipped defaults (RC-001) |
| NFR-008 synthetic data | ADDRESSED | §12, fixtures `*.example.invalid` |
| NFR-009 audit retention | ADDRESSED (pending OQ-4) | §12 |
| NFR-010 credential safety | PARTIAL | §6.4 origin binding + shared-app opt-in; holes: raw method+path (RC-002), P1–P3 spec token sent to every host (RC-006) |
| US1 #1–#4 | ADDRESSED | §2.3 A, §11, §4.1 validation |
| US2 #1–#3 | ADDRESSED | §3.5, §5.1 |
| US2 #4 no answer → say so | PARTIAL | no min-score / "no confident match" signal; two-stage search always returns top `limit` (RC-012) |
| US3 #1–#4 | ADDRESSED | D2, §3.6, §3.8, §9.4 tool description (US3 #3 untested — RC-012) |
| US4 #1–#4 | ADDRESSED | §6.2, §6.4, §11 |
| US5 #1–#3 | ADDRESSED | §9.2 |
| US6 #1–#3 | ADDRESSED | §5.2 |
| US7 #1–#3 | ADDRESSED | §3.4, §3.6, §9.6 |
| US8 #1–#3 | ADDRESSED | §3.5 |
| US9 #1–#3 | PARTIAL | design present; only #3 (validation codes) has a test (RC-012) |
| SC-001…SC-010 | ADDRESSED | §14.1/§14.2; SC-002 test skippable (RC-013) |

## Required Changes

Ordered: must-fix first, then should-fix.

| id | severity | pass | location | change | why |
|----|----------|------|----------|--------|-----|
| RC-001 | must-fix | consistency | `spec.md › §7 D1`, `§9.1`, `§15` (local `.env.example`), `§16`, `§18`; `plan.md › p1-local-fixtures`, `Rollout Plan` step 1 | Pick one mechanism so that `make demo` actually runs registry mode. Option (a): ship `.env.example` with `SSE__CATALOG_SOURCE=registry` (or `SSE__USE_FIXTURE=false`). Option (b): change the `auto` precedence to `swagger_links` → `registry` (when ≥1 `list_active(env)` record has a cached spec or `spec_fixture`) → `fixture`. State the choice in D1. Add a P1 test asserting that the shipped `.env.example` settings resolve to `registry`. | Verified: `SseConfig.use_fixture` defaults to `True` and `.env.example` sets `SSE__USE_FIXTURE=true`. Under D1's `auto` order, that resolves to `fixture`. This contradicts `p1-local-fixtures` ("make demo runs registry mode"), §16 and Rollout step 1. NFR-007/SC-010 would pass without ever exercising the new path. |
| RC-002 | must-fix | soundness | `spec.md › §6.4` (first line), `§5.1` `call_sse_api`; `plan.md › p4-invoke-per-app`, `p4-tests` | Define registry-mode behaviour when `call_sse_api` receives `method`+`path` with no resolvable operation (today `handle_call_sse_api` allows this). Require an `application` argument, resolve `target` by `application_id`, and match method+path against that app's operations. Otherwise return `outcome="rejected"` with no token fetched or sent. Restrict the `target=None` branch to legacy `swagger_links`/`fixture` modes only. Add a P4 test: raw method+path in registry mode without `application` ⇒ `rejected`, no Authorization header observed. | `target = target or service.target_for(operation.source_id)` is undefined when `operation is None`. Registry-mode `allowed_origins` spans every app, so the credential choice for a raw call is unspecified. This is a critical-route hole against NFR-010 and FR-009. |
| RC-003 | should-fix | soundness | `spec.md › §7 D6` consequences, `§3.4` (`create_collection`); `plan.md › p3-vector-filter-contract` | Fold a namespace-consistent creation API into the G6 `provider_contracts` change. Make `create_collection` honour the same namespace → collection resolution as `upsert`/`search`/`delete` (or add an idempotent `ensure_namespace(namespace, vector_size)`), and define idempotency (no-op on exists) in the contract. Drop the "provider-resolved name via a small helper" and the undefined `AlreadyExists`. | Verified: Qdrant `create_collection(name)` uses the raw name while `upsert`/`search` use `_resolve_collection(namespace)` = `{collection}_{namespace}`; mock uses the raw namespace. A helper in `api_index` would need provider-specific knowledge, which breaks the provider abstraction. |
| RC-004 | should-fix | soundness | `spec.md › §3.5` stage 2, `plan.md › Risk Mitigation` row "`provider_contracts` change lands late" | Specify that `ApiSearchService` sends a list-valued `application_id` filter only when the provider supports any-of (G6 shipped / version check). Otherwise it omits that key, over-fetches (`top_k = max(8*limit, 120)`) and relies on `post_filter`. Alternatively, declare P3 hard-blocked on the G6 release and delete the risk-row claim. | Verified: Qdrant maps every filter value to `MatchValue(value=v)`; a list value fails validation rather than being ignored, so search would always drop to the sidecar. pgvector ignores `filter`. The risk-table mitigation does not hold as written. |
| RC-005 | should-fix | soundness | `spec.md › §6.4` URL line, `§4.1` `base_url` comment | Define how OpenAPI `servers[0].url` / Swagger `basePath` combine with `target.base_url`. Proposed rule: use `target.origin`, keep the path component of a relative or same-origin `servers` URL, and ignore and flag (`issues: ["spec_server_origin_mismatch"]`) any absolute `servers` URL on a different origin. Add a P4 test. | Today `resolve_base_url` prefers `operation.server_url` (built from `servers`/`basePath`). §6.4 replaces it with `target.base_url` without saying what happens to spec base paths, so implementers will diverge and calls may 404 or fail origin binding. |
| RC-006 | should-fix | soundness | `spec.md › §3.6`, `§9.1` (`_static_token(cfg.eakg.live_spec_token)`), `§12` | During P1–P3, either send `EAKG__LIVE_SPEC_TOKEN` only to apps whose `environments[env].auth_audience` equals the TAAC shared identifier (the OQ-7 placeholder), or record an explicit, time-boxed NFR-010 exception in §12 and §19 that closes in `p4-spec-fetch-broker`. | P1 sends one spec-fetch bearer to every registered host. This is the same "one bearer to every host" pattern the spec claims to close for NFR-010, now on the pipeline path. |
| RC-007 | should-fix | soundness | `spec.md › §6.4` cache, `§11` retired-app row | Make the response cache key `sse:api:{env}:{application_id}:{principal_key}:{METHOD}:{url}`, where `principal_key = principal.user_id or "service"`. | The current key `sse:api:{METHOD}:{url}` would serve user A's response to user B once an on-behalf-of broker lands. That breaks FR-011 ("no redesign") and the story privacy rule (data shown only to the requesting user). |
| RC-008 | should-fix | soundness | `spec.md › §6.2` `check()` contract, `§5.2` | Define how `StaticCredentialBroker.check` satisfies "MUST NOT do network I/O" when `SecretsProvider` is remote (AWS Secrets Manager). For example, answer from the caching broker's last-known state plus a startup-loaded secret-name presence set, and return `state="error", detail="unknown"` otherwise. | `get_or_default` is async and may be network-backed. As written the contract cannot hold for the AWS profile. |
| RC-009 | should-fix | coverage | `spec.md › §2.3 A.3`; `plan.md › Phase 1` Reqs, `p1-catalog-from-cache`, `p5-scheduler` | Move the fingerprint hot-reload into P1 (fingerprint = registry YAML + every `openapi/<env>/current.json`), and extend it in P2 to `operations.json`. Alternatively, remove FR-002 from P1's Reqs and state that a restart or `list_sse_apis refresh=true` is needed until P5. | §2.3 A.3 keys reload on `operations.json` (a P2 artifact) and the reload is built in `p5-scheduler`. P1 therefore cannot meet FR-002 / US1 #1 as claimed. |
| RC-010 | should-fix | buildability | `spec.md › §8.2` row `capability_kg/catalog.py + eakg/merge.py`; `plan.md › p2-capability-app-id` | Source `CapabilityRecord.application_id` from the existing `belongsToApp` predicate (`graph_build.py` already adds `cap → belongsToApp → app_<id>`). Do this by extending the capability SPARQL in `packages/capability_kg/sparql.py` and `_to_record`, not in `merge.py`. | Verified: `merge_shards` flattens all repo graphs into one `Graph`, losing per-repo provenance, so "populate from the source shard repo" in `merge.py` is not implementable. The predicate already exists. |
| RC-011 | should-fix | buildability | `spec.md › §5.4`, `§4.1`, `§9.1` | Define the fields of `CapabilityLookupAll`, `OperationSet`, `IndexReport`, `SearchOutcome`, `SpecPointer`, `HealthSnapshot`, `Resolved`/`Ambiguous`/`NotFound`, and `RegistryIssue` (incl. `severity: blocking | warning`). Define `blocking_issues(rec, env)`, which `list_active` uses. | These are referenced in public signatures but never specified, so an implementer has to invent them. Which validation codes block `list_active` (e.g. is `audience_missing` blocking?) is ambiguous. |
| RC-012 | should-fix | testability | `spec.md › §14.1`, `§14.2`, `§3.5` | Add the following tests. (a) `test_isolation_latency`: healthy-app `sse.invoke` p95 within ±10 % with 6/30 apps delayed or failing via MockTransport (NFR-004). (b) US9 #1/#2: the same app registered in `dev` and `stage` with different fixture specs ⇒ each process discovers only its own operations and namespace. (c) US2 #4: define a "no confident match" signal (min blended score or empty-after-threshold) in §3.5 and test it. (d) US3 #3: a golden/eval case where one app is `unavailable` and the answer still covers the other app. | These acceptance scenarios have a design but no verification path. |
| RC-013 | should-fix | testability | `spec.md › §14.2` `test_top5_recall`, `test_discovery_p95`; `plan.md › p5-quality-gates` | Make `p5-quality-gates` run `test_top5_recall` non-skippably (fail if the local model is unavailable in the gate run). Add a second `test_discovery_p95` variant with local bge + local Qdrant, so the 600 ms embed and 50 ms ANN budgets from §13 are measured. | As written, SC-002 can pass by skipping, and SC-003 is measured only against the mock store and deterministic embedder. |
| RC-014 | should-fix | consistency | `spec.md › §1.1 G7`, `§7 D9`, `§6.2`; `README.md › Dependencies`; `plan.md › p4-approval-gate`, `p6-architecture-md`; ADR-024 Implications | Replace "11th provider category" with the correct count, or drop the ordinal. `factory.py` already exposes 13 factories (`loan_data`, `policy_source`, `session_store` and `reranker` beyond AGENTS.md's 10). Have `p6-architecture-md` reconcile the AGENTS.md category list. | The doc updates in P6 would otherwise record a wrong count. |
| RC-015 | should-fix | consistency | `plan.md › Notes` | Change "OQ-1 … OQ-6" to "OQ-1 … OQ-9" to match spec §19. | Dangling or partial reference. |
| RC-016 | should-fix | consistency | `spec.md › §1.1`; `plan.md › Sign-off`, `p1-approval-gate` | Name the approver for G1–G3 (resolve OQ-6 at least for approval routing), and mark it in §1.1 as the precondition for `p1-approval-gate`. | With no product owner or technical lead, P1 has no path to approval. This is the only OQ that effectively blocks Phase 1. |
| RC-017 | should-fix | soundness | `spec.md › §4.1` rule `env_mismatch` | Specify the matching: split the host on `.` and `-`, then require exact token equality against `{dev}`, `{stg, stage}`, `{prd, prod}`. A substring such as `devops` must not match. | "Host labels contain" is ambiguous and would false-positive or false-negative. |
| RC-018 | should-fix | soundness | `spec.md › §3.5`, `§7 D7`, `§5.2` | At runtime, compare the live embedder's `model:dimensions` with the manifest namespace fingerprint. On mismatch, skip the vector stage (sidecar or keyword fallback) and emit `/ready` warning `embed_model_mismatch`. | Otherwise a dev who swaps `EMBEDDING__*` without reindexing gets dimension errors on every search with no explanation. |

## Recommended (non-blocking notes)

- Under the read-only rule (§3.2), consider ignoring Swagger-2 `consumes` on GET when computing `has_request_body`. `parse_openapi_document` sets `has_request_body = True` for any op with `consumes`, which can make legitimate GETs non-callable.
- §3.6 runs a 30 s per-app `wait_for` around a 20 s HTTP timeout, and §10 says "per-app timeout 30 s". State both values once.
- `Makefile` `demo` uses `&`, a POSIX background operator, which does not work on Windows PowerShell 5.1. Not this spec's scope, but SC-010 "passes locally" is validated on this workstation.

## Strengths

- The pipeline/runtime split (D2) removes every boot-time network call, with a precise test hook (no `httpx.AsyncClient` constructed).
- The join algorithm (§3.2) is grounded in the real ID split: verified `GetLoanSummary` / `/{id}/Summary` vs `loanservices:getLoanSummary` / `/api/Loans/{loan_id}/Summary`. It has complexity bounds and an explicit `join` quality field. `ambiguous` records are never callable.
- `public_id` keeps today's `parse_openapi_document` id format, verified as `f"{source_id}:{operationId or METHOD_slug}"`, so there is no client break.
- `CredentialBroker` follows the `loan_data.py` precedent (ABC plus concretes in one module, factory-only imports). Its exception taxonomy maps cleanly onto user-facing outcomes. The shared bearer becomes explicit opt-in.
- Every new env var, project, provider and threshold is enumerated as an approval gate (G1–G10) with phase and section. Defaults preserve legacy behaviour per phase.
- Layering verified against the real `pyproject.toml` deps. `sse` and `eakg` are independent and `tools` already depends on both, so the new `LoanOps.ApiIndex` slots in cleanly.
- The plan has 56 verifiable `p{N}-slug` todos (count matches), each phase with tests, success criteria and quality gates, and PowerShell-safe commands.
