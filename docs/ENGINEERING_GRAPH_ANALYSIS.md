# Engineering Graph analysis (LoanOps + EAKG)

**Date:** 2026-10-04  
**Scope:** Analysis snapshot plus **implemented MVP** (optional Graphify stage).  
**Status:** EAKG RDF pipeline is product truth. Optional `--engineering-graph` writes per-repo AST + `links.json`. That stage is **not** on by default.

## Target (MVP, implemented)

- Analyzers live in `packages/eakg/analyzers/`. Registry selects **DotNetRoslynAdapter** (API surface) and, with `--engineering-graph`, **GraphifyAstAdapter**.
- Graphify output: `data/eakg/repos/<id>/engineering/graph.json` (gitignored with shards). Links: `engineering/links.json`.
- Join key: `application|METHOD|normalized_path`. Match Roslyn evidence file + action to Graphify `source_file` + `label`. No fuzzy `Task`/`List` links.
- CLI: `uv run python -m packages.eakg onboard --id <id> --engineering-graph` then `uv run python -m packages.eakg code --id <id> --operation op_<app>_<Action>_<METHOD>`.
- Graphify failure does **not** fail EAKG index. Java has no adapter. Unknown languages are `unsupported` on the manifest.
- LoanOps `graphify-out/` is unchanged (this repo only). MCP `search_sse_apis` is unchanged.

Related: [`ARCHITECTURE.md`](../ARCHITECTURE.md) §10–10b, [`docs/STACK_LAYER_DECISIONS.md`](STACK_LAYER_DECISIONS.md), [`GRAPHIFY_SETUP.md`](../GRAPHIFY_SETUP.md), [`docs/EAKG_COMMITTED_VS_LOCAL.md`](EAKG_COMMITTED_VS_LOCAL.md), [`docs/EAKG_ONBOARD_REPO.md`](EAKG_ONBOARD_REPO.md).

---

## 1. Two graphs (do not conflate)

| Graph | Path | What it is | Runtime? |
|-------|------|------------|----------|
| **Graphify** (stack: “engineering / code graph”) | `graphify-out/` | AST + docs of **this** LoanOps-Agent repo | No. Dev aid (`graphify query` / `path` / `explain`). |
| **EAKG** (capability registry) | `data/eakg/` | RDF shards of registered SSE apps | Yes. Feeds MCP `search_sse_apis` (text block). Live calls stay `call_sse_api`. |

ADR-012 / ARCHITECTURE: **do not** put SSE OpenAPI/ops into LoanOps `graphify-out/`.

---

## 2. EAKG pipeline (what actually runs)

```
1. Register     data/eakg/registry/repositories.yaml
2. Clone        .eakg-workspace/<id>  (or --local-path)
3. Extract      Roslyn (primary) or regex → controllers, packages, URLs, topics, proxies
4. Enrich       optional OpenAPI match on METHOD:path → summary/tags on JSON
5. Write RDF    graph_build.interface_to_graph → graph.ttl + evidence.ttl + interface.json
6. Cross-app    detectors → enterprise/cross_app.ttl
7. Review       python -m packages.eakg review --pilot
8. Merge        shards → CapabilityCatalog
9. Embed        optional embeddings.json
10. Ask time    search_sse_apis (OpenAPI keyword + EAKG block) → call_sse_api
```

**STEP 5 does not graph all C#.** It serializes HTTP operations + one seeded Capability per op + CodeUnit `Controller.Action` + evidence pointers. Packages, topics, proxies, connection keys stay on **`interface.json`** for detectors.

### RDF classes actually written

| Source | Classes |
|--------|---------|
| `interface_to_graph` | Repository, Application, APIOperation, CodeUnit, Capability, Evidence (pointers on graph; full nodes in evidence.ttl) |
| Detectors | CrossAppRelationship + Evidence |
| TAAC | Enterprise, Application, AuthProvider, DataStore, EventTopic |

**Ontology present, not materialized in `graph_build.py`:** Deployable, ApiSurface, SdkPackage, Role, Principal, Documentation; `hasDeployable` / `hasApiSurface`. Registry `deployables:` (e.g. Escrow.Web) are unused in Turtle.

### Cross-app kinds implemented

`consumesSdk`, `sharesDto`, `callsApplication`, `callsOperation`, `publishesEvent`, `readsDataStore`, `authenticatesVia`, `overlapsCapability`. Many heuristics are PennyMac-shaped (`PNMAC.*.Client`, TAAC `*Url` keys, catalog owner map).

### Languages / apps

| | Status |
|--|--------|
| Extractors registered | `dotnet-aspnetcore`, `dotnet` only |
| Detected, **no** extractor | `nodejs`, `java-maven`, `python`, `unknown` → onboard fails |
| Indexed apps | escrow, fees, loanservices (`api_project_path` = WebApi only) |

Extraction of **structure** is rule-based (Roslyn/regex), not LLM. Timestamps, filesystem walk order, `auto` fallback to regex, and live OpenAPI can change bytes.

---

## 3. Graphify on LoanOps-Agent (checked-in)

Snapshot at analysis time (`graphify-out/GRAPH_REPORT.md`, commit `b0c0e86c`):

- **4473 nodes, 9648 edges**, 445 communities  
- Extraction: 86% EXTRACTED / 14% INFERRED  
- `file_type`: code 2890, document 956, rationale 472, concept 155  

**Edge relations:** `calls`, `contains`, `references`, `method`, `indirect_call`, `imports`, `imports_from`, `rationale_for`, `uses`, `inherits`, `depends_on`, `re_exports`, `defines`, `implements` (1). Hyperedges: 0. No HTTP/OpenAPI node types.

**Corpus skew:** ~965 nodes from `apps/web_ui/public/redoc/redoc.standalone.js`. God-nodes include `_`, `t()`, `r()`. React/TS coverage is small (tsx 15, ts 20). **0 HTML/CSS nodes.** C# in this graph is mainly EAKG **fixtures** + `tools/eakg-dotnet-extract`, not GitLab clones.

Wiki (`graphify-out/wiki/`) is **missing**. Graphify is **not** imported at request time.

---

## 4. Frontend vs backend representation

| Surface | Graphify (LoanOps) | EAKG |
|---------|--------------------|------|
| `apps/web_ui` React | Partial AST of `.ts`/`.tsx`. No CSS/HTML. `fetch("/api/chat")` is **not** an edge to FastAPI. | Not scanned |
| LoanOps Python | Strongest AST (modules, imports, calls) | N/A |
| SSE `*.WebApi` | Not in LoanOps graph | Controllers → TTL |
| SSE `*.Web` (listed in registry deployables) | Not scanned | **Not** extracted (`api_project_path` is API only) |

---

## 5. OpenAPI vs backend vs invoke

Join is **string match**, not a shared identity:

1. Roslyn/regex emit method + path + C# action.  
2. OpenAPI enrich (if mode ≠ `static`) copies summary onto matching `METHOD:path`. RDF `operationId` remains the **action name**.  
3. `OpenApiCatalogService` is a **second** OpenAPI parse for MCP.  
4. `search_sse_apis` concatenates EAKG capability **text** with OpenAPI hits. No RDF triple `OpenAPI op ↔ CodeUnit ↔ invoke id`.  
5. `call_sse_api` uses the catalog, **not** Turtle.

---

## 6. Graphify vs custom analyzers

| | Graphify | Custom (EAKG / capability_kg / SSE) |
|--|----------|-------------------------------------|
| Subject | This repo | External SSE clones + TAAC + OpenAPI |
| Parser | Generic AST | Roslyn + regex + OpenAPI JSON + TAAC |
| Output | `graph.json` | Turtle + `interface.json` |
| Query | CLI subgraph | SPARQL + keyword/embed + MCP |
| Cross-app | Imports/calls inside LoanOps | Detectors across escrow/fees/LS |
| Governance | None | Evidence, `review --pilot`, `approved.ttl` |

**CodeQL / Tree-sitter:** stack Phase 2, **not started**.

---

## 7. One-off Graphify on registry clones (2026-10-04)

**Not in pipeline.** `onboard.py`, `ci/eakg.gitlab-ci.yml`, and EAKG CLI have **no** Graphify calls.

Command used (AST only, no LLM, no clustering):

```powershell
graphify extract ".eakg-workspace\<id>" --code-only --no-cluster --out ".eakg-workspace\graphify\<id>"
```

| Registry id | Files scanned | Nodes | Edges | Output (gitignored) |
|-------------|--------------:|------:|------:|---------------------|
| escrow | 2757 | 39019 | 109545 | `.eakg-workspace/graphify/escrow/graphify-out/graph.json` |
| fees | 1235 | 26741 | 72120 | `.eakg-workspace/graphify/fees/graphify-out/graph.json` |
| loanservices | 1206 | 23172 | 42902 | `.eakg-workspace/graphify/loanservices/graphify-out/graph.json` |

Mostly `.cs` + wwwroot `.js` + some `.cshtml`/`.csproj`. SQL skipped (`tree_sitter_sql` missing). Graphs were **not** merged into LoanOps `graphify-out/` or MCP.

Query example:

```powershell
graphify query "PaymentSchedules" --graph ".eakg-workspace/graphify/loanservices/graphify-out/graph.json"
```

Re-onboard of EAKG **does not** refresh these files.

---

## 8. Implemented / partial / missing

| Item | Status |
|------|--------|
| Graphify of LoanOps-Agent | **Implemented** (noisy JS corpus) |
| EAKG .NET controller RDF + evidence | **Implemented** |
| OpenAPI enrich | **Partial** (optional; live spec may 404) |
| Cross-app TTL + review CLI | **Implemented** |
| Semantic capability search | **Partial** (flag) |
| Graphify of SSE clones | **Local experiment only** — not pipeline |
| UI → route → OpenAPI → controller as one path | **Missing** |
| EAKG extractors for Java/Python/Node | **Missing** |
| RDF for packages/topics/proxies | **Missing** (JSON only) |
| CodeQL / Tree-sitter | **Missing** |
| Graphify wiki | **Missing** |

**Useful today:** (a) agents navigating LoanOps **Python** via Graphify; (b) discovering SSE **controller APIs** via EAKG + OpenAPI and invoking via MCP. **Not** a single application engineering graph from screen to C# line.

---

## 9. STEP 5 (EAKG write RDF) — short

`onboard.py` calls `interface_to_graph` then `ShardStore.write_graph` / `write_evidence` / `write_interface`.

Per operation: mint `op_{app}_{action}_{METHOD}`, `code_{Controller}_{Action}`, `cap_{app}_{snake_case(action)}` with `hasReviewStatus "discovered"` and `source "static_dotnet"`. Evidence URIs live in `evidence.ttl`; graph only has `hasEvidence`.

`relationships_to_graph` is STEP 6. `enrich_operations_from_openapi` is STEP 4 (same file as STEP 5).
