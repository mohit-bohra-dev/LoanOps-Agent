# Phase 9 — Semantic capability retrieval

**Status:** Implemented (v1).
**Depends on:** Phases 2–3 (RDF + `CapabilityCatalog`).
**Does not change:** MCP tool count, `invoke_sse_api`, eval thresholds, Graphify.

## Problem

Today `search_capabilities` / SPARQL `CONTAINS` matches tokens in `rdfs:label` and `rdfs:comment`.

"Show payment history for this loan" may miss `get_payment_schedules` if the words do not overlap the OpenAPI summary.

## Implemented flow

```text
User request
    ↓
Embed query (existing EmbeddingProvider) when CAPABILITY_KG__SEMANTIC=true
    ↓
Cosine rank vs capability vectors (data/capability_kg/embeddings.json)
    ↓
Top-k candidates
    ↓
Drop rejected/deprecated; prefer readOnly; honor approved_only
    ↓
Score blend 0.7*cosine + 0.3*keyword_hit
    ↓
CapabilityCatalog results → search_sse_apis text
    ↓
Agent still calls call_sse_api by operation_id
```

Fallback: flag off, missing sidecar, or embed failure → keyword SPARQL.

## Enable

```env
CAPABILITY_KG__ENABLED=true
CAPABILITY_KG__SEMANTIC=true
```

Build vectors (optional; uses live embedding provider):

```powershell
python -m packages.capability_kg.build --embed
```

## Code

| File | Role |
|---|---|
| `packages/capability_kg/embed_index.py` | Sidecar build/load + cosine |
| `packages/capability_kg/catalog.py` | Semantic `search_capabilities` |
| `packages/capability_kg/build.py` | `--embed` flag |
| `packages/sse/tools.py` | Injects factory embedder when semantic on |
