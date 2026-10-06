# API Discovery Checklist Audit — LoanOps-Agent

> Audited: 2026-10-03 | Graph-first research via `graphify query` + direct file reads

---

## Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Fully implemented |
| 🟡 | Partially implemented / flag-gated |
| ❌ | Not yet implemented |

---

## Checklist

| # | Learning | Status | Evidence |
|---|----------|--------|----------|
| 1 | API discovery at scale | ✅ | See below |
| 2 | API metadata → embeddings | ✅ | See below |
| 3 | Vector retrieval | ✅ | See below |
| 4 | Vector-search false negatives | 🟡 | See below |
| 5 | Business-process graph | ✅ | See below |
| 6 | Graph expansion | 🟡 | See below |
| 7 | Combined retrieval | 🟡 | See below |
| 8 | SPARQL / KG queries | ✅ | See below |
| 9 | Business context | 🟡 | See below |
| 10 | Final API selection (agent gets subset) | ✅ | See below |
| 11 | MCP integration | ✅ | See below |
| 12 | Context graph | 🟡 | See below |

---

## Detailed findings

### 1 · API discovery at scale ✅

**How it works:** The `CapabilityCatalog` ([catalog.py](file:///d:/Programming-Projects/LoanOps-Agent/projects/LoanOps.CapabilityKg/packages/capability_kg/catalog.py)) is a facade over the RDFLib KG. The agent never sees raw triples or the full OpenAPI spec. Discovery is performed with `search_capabilities()` / `find_capabilities_for_intent()` which return a small, filtered `CapabilityRecord` list. The `CapabilityRecord` struct exposes only the bounded view needed by the agent (id, description, operation_id, read_only, review_status, permission, uri).

The EAKG layer (`LoanOps.Eakg`) additionally catalogs APIs across multiple enterprise applications via `ShardStore` + `merge_shards()`, scaling to multi-repo discovery without exposing every operation to the LLM.

---

### 2 · API metadata → embeddings ✅

**How it works:** [`embed_index.py`](file:///d:/Programming-Projects/LoanOps-Agent/projects/LoanOps.CapabilityKg/packages/capability_kg/embed_index.py) implements the offline embedding pipeline:
- `capability_text(rec)` → synthesizes a rich text blob: `"{id}. {description}. operation {operation_id}. domain {domain}."`
- `build_index(records, embed)` → async, calls any `EmbedFn` (injected; adheres to Provider Abstraction)
- Vectors stored in `embeddings.json` sidecar alongside the TTL; loaded via `load_index()`

The text template encodes: ID, description, operation_id, and domain — i.e., all the metadata fields relevant for semantic retrieval.

---

### 3 · Vector retrieval ✅

**How it works:** [`rank()`](file:///d:/Programming-Projects/LoanOps-Agent/projects/LoanOps.CapabilityKg/packages/capability_kg/embed_index.py#L134-L144) in `embed_index.py` does cosine-similarity ranking over the loaded index and returns the top-K (`default top_k=15`). `search_capabilities()` in `catalog.py` calls `rank(qvec, self._embed_index, top_k=max(limit*3, 15))` — returning a candidate set before final re-ranking.

---

### 4 · Vector-search false negatives 🟡

**Partial.** `search_capabilities()` in `catalog.py` implements a **hybrid re-ranking strategy**: it runs keyword SPARQL search in parallel and uses a **blended score** `0.7 * cosine + 0.3 * keyword_hit`. This means APIs that match by keyword but are semantically distant still surface.

**Gap:** The keyword search (`search_by_needle`) only does label/comment `CONTAINS` substring matching. There is no synonym expansion, no fuzzy phonetic matching, and no explicit graph-neighbor expansion to catch APIs that are _neither_ semantically similar _nor_ keyword-matching but are a structural neighbor of a hit. An API that is only discoverable via a dependency chain (e.g., `dependsOn` from a hit) will still be missed.

---

### 5 · Business-process graph ✅

**How it works:** The ontology ([`ontology.py`](file:///d:/Programming-Projects/LoanOps-Agent/projects/LoanOps.CapabilityKg/packages/capability_kg/ontology.py)) defines:
- `PRED_DEPENDS_ON`, `PRED_RELATED_TO`, `PRED_DOCUMENTED_BY`, `PRED_DERIVED_FROM` — semantic relationships
- `CrossAppRelationship` class with `KIND_CALLS_OPERATION`, `KIND_CONSUMES_SDK`, `KIND_PUBLISHES_EVENT`, `KIND_SUBSCRIBES_EVENT`, etc. — enterprise-scale process edges

The EAKG builds a multi-repo RDF graph (`build_enterprise_graph()` / `ingest_taac_file()`) that captures `callsOperation`, `consumesSdk`, `sharesDto`, `publishesEvent`, `subscribesEvent`, `readsDataStore`, `ownsDataStore`, `authenticatesVia` cross-app relationships with evidence provenance.

---

### 6 · Graph expansion 🟡

**Partial.** The `impact_of_change()` function in [`eakg/query.py`](file:///d:/Programming-Projects/LoanOps-Agent/projects/LoanOps.Eakg/packages/eakg/query.py#L226-L278) traverses incoming `callsOperation / consumesSdk / sharesDto / callsApplication` edges — this is graph expansion in the impact direction.

**Gap:** There is no **outbound** graph expansion from a capability hit → "what does this API need/depend on?". Specifically:
- No `get_neighbors(capability_id)` helper for `dependsOn` / `hasNext`-style traversal
- The `CapabilityCatalog.search_capabilities()` does not expand vector hits by walking the RDF `dependsOn` edges to add structurally-related neighbors
- This is the most important missing piece for full items 4+6 coverage

---

### 7 · Combined retrieval 🟡

**Partial.** `CapabilityCatalog.search_capabilities()` does combine two signal sources:
- **SPARQL keyword hits** (via `_keyword_search()`)
- **Vector hits** (via `rank()`)

And blends them with `score = 0.7 * cos + 0.3 * hit`.

**Gap:** The combination is only **vector ∪ keyword** — it does not include **graph-derived candidates** (i.e., RDF neighbors of hits). A true 3-way merge (vector + keyword + graph expansion) is not implemented. The `impact_of_change()` data from EAKG is not piped back into the catalog-level search.

---

### 8 · SPARQL / KG queries ✅

**How it works:** [`sparql.py`](file:///d:/Programming-Projects/LoanOps-Agent/projects/LoanOps.CapabilityKg/packages/capability_kg/sparql.py) has a full set of **pre-compiled, parameterized SPARQL queries** (never string-concat, bound via `initBindings`):
- `search_by_needle` — label + comment `CONTAINS` search
- `by_domain`, `by_permission`, `by_application` — structured faceted queries
- `get_by_id` — exact capability lookup
- `list_all` — full catalog scan
- `list_read_only` — read-only safe subset

The EAKG layer additionally uses raw RDF triple-walking (`g.triples(...)`) for provenance-aware queries.

---

### 9 · Business context 🟡

**Partial.** Some business context is present:
- `loanops:hasDomain` → `BusinessDomain` class + `by_domain()` query — APIs can be scoped to a business area
- `CrossAppRelationship` with relationship kinds encodes _why_ an API is connected in the enterprise
- `find_capabilities_for_intent(intent)` is the natural-language entry point

**Gap:** The KG does not currently model **business process flows** (e.g., "Escrow Removal requires: [get loan] → [check eligibility] → [calculate balance] → [remove escrow]"). The SOP docs in `data/sops/` exist in RAG but are not linked back to API capabilities in the RDF graph. Intent-level reasoning about "why" an API is needed within a multi-step process is not wired up — the agent sees individual APIs but not the ordered process they serve.

---

### 10 · Final API selection (agent receives subset) ✅

**How it works:** The MCP server ([`server.py`](file:///d:/Programming-Projects/LoanOps-Agent/projects/LoanOps.McpServer/packages/mcp_server/server.py#L137-L186)) exposes EAKG tools (`search_capabilities`, `explain_capability`, `find_providers`, `impact_of_change`) via FastMCP. The agent calls these discovery tools first, then uses `call_sse_api` with the resolved `operation_id` — it never receives the full API catalog.

The `capability_bind` middleware additionally validates that a `capability_id` maps to a real catalog entry before dispatching the live API call, enforcing the "subset first" discipline.

---

### 11 · MCP integration ✅

**How it works:** Full Streamable HTTP MCP server (`LoanOps.McpServer` on `:8001`) with:
- Role-based tool scoping via `tools_for_role()` + `EAKG_TOOL_NAMES`
- `search_capabilities`, `explain_capability`, `find_providers`, `impact_of_change` all registered as MCP tools
- Bearer token auth (`StaticTokenVerifier`) + audit log per call
- `call_sse_api` for live invocation, gated by capability-bind + permission check

The MCP client side is `LoanOps.Tools` (`ModularToolsClient` + `McpToolsClient`).

---

### 12 · Context graph 🟡

**Partial.** At the EAKG level, a per-repository subgraph (`ShardStore.load_repo_graph()`) and a merged cross-app graph (`merge_shards()`) exist. The `impact_of_change()` function effectively constructs a task-scoped relationship subgraph for a specific operation.

**Gap:** There is no explicit **task-specific context graph builder** — a function that takes the discovered API subset + the current user intent, then returns a focused subgraph of only the relevant nodes (capabilities, apps, domains, relationships). This would be the composite output of items 3+6+7 stitched together. Currently each piece is a standalone query; no code assembles them into a single context object passed to the agent.

---

## Summary

### What's solid ✅
- RDF/SPARQL ontology + KG with full business domain/permission/app relationships
- Offline embedding index + cosine ranking with top-K
- Keyword ∪ vector hybrid blending in `CapabilityCatalog`
- Cross-app enterprise relationship graph (EAKG) with evidence provenance
- MCP tool exposure with role-scoping and capability-bind gate
- Agent never sees full API catalog — always receives a bounded subset

### Key gaps to close 🟡 → ✅

| Priority | Gap | Where to add |
|----------|-----|--------------|
| **High** | **Graph expansion**: traverse `dependsOn` / cross-app edges from vector hits to surface neighbors | `catalog.py` → `search_capabilities()` |
| **High** | **3-way merge**: vector + keyword + graph neighbors → unified ranked list | `catalog.py` → `search_capabilities()` |
| **Medium** | **SOP ↔ API links**: link `data/sops/*.md` process steps to RDF capability nodes | New TTL builder + `ontology.py` (`hasNextStep`, `precondition`) |
| **Medium** | **Context graph assembly**: a function returning a task-scoped subgraph to pass to the agent as system context | New `context_graph.py` in `LoanOps.CapabilityKg` |
| **Low** | **Synonym / fuzzy fallback**: expand keyword search with synonyms for mortgage-domain terms | `sparql.py` → `search_by_needle()` |
