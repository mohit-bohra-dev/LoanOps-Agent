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
Cosine rank vs capability vectors (`data/eakg/enterprise/embeddings.json`)
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

Fallback: no sidecar and flag off, or embed failure → keyword SPARQL.

`search_sse_apis` also embeds **OpenAPI operations** in-process (`packages/sse/semantic.py`, same 0.7/0.3 blend). Vectors cached on `OpenApiCatalogService`. Embedder fail → keyword. No new env var.

EAKG: `CAPABILITY_KG__SEMANTIC=true` **or** `data/eakg/enterprise/embeddings.json` present.

## Enable

```env
CAPABILITY_KG__ENABLED=true
CAPABILITY_KG__SEMANTIC=true
```

Build vectors (optional; uses live embedding provider):

```powershell
uv run python -m packages.eakg embed
# smoke: uv run python -m packages.eakg query search "when is the next payment due" --semantic
```

Old OpenAPI-only TTL (not product discovery): `python -m packages.capability_kg.build --embed`

MCP `search_sse_apis` uses the shard sidecar when `CAPABILITY_KG__SEMANTIC=true`.

## Code

| File | Role |
|---|---|
| `packages/capability_kg/embed_index.py` | Sidecar build/load + cosine; rich `capability_text` (summary + HTTP path phrases) |
| `packages/capability_kg/catalog.py` | Semantic `search_capabilities`; `CapabilityRecord.http_path` |
| `packages/capability_kg/extract_openapi.py` | Comment = summary + description + tags |
| `packages/eakg/embed.py` | `embed` CLI → enterprise/embeddings.json |
| `packages/eakg/merge.py` | `catalog_from_shards` loads that sidecar |
| `packages/sse/tools.py` | Injects factory embedder when semantic on |

## Ranking tip

Re-run `uv run python -m packages.eakg embed` after extract/text changes — sidecar `text_hash` must refresh so “next payment due” ranks `PaymentSchedules` over ops that only share “due”.
