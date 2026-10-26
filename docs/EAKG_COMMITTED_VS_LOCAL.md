# EAKG: committed vs local-only

Quick map so clean clones and CI do not confuse registry seed with live enterprise data.

**How TAAC becomes graph (simple):** [`EAKG_TAAC.md`](EAKG_TAAC.md).  
**Pipelines / stores:** [`PIPELINES.md`](PIPELINES.md).

**Source of truth (D4):** EAKG (GraphDB / Neptune) + Postgres artifacts + pgvector.  
ADR-014 single TTL fallback **removed** from product search. **No S3.**

## In git (safe to commit)

| Path | What |
|---|---|
| `packages/eakg/` | Pipeline code + synthetic fixture tests |
| `data/eakg/registry/repositories.yaml` | Repo registry seed (ids, GitLab URLs) |
| `data/eakg/fixtures/` | Redacted TAAC / synthetic configs only |
| `data/eakg/patterns/` | Detector patterns |
| `data/pipeline_store/README.md` | File-mode layout note (contents gitignored) |
| `docs/EAKG_*.md`, `ci/eakg.gitlab-ci.yml`, `scripts/eakg/` | Ops + docs |
| `packages/capability_kg/` + `data/capability_kg/README.md` | Catalog facade / ontology shared by EAKG |

## Product stores (`EAKG_STORE__BACKEND=postgres`)

| Store | Holds |
|---|---|
| GraphDB / Neptune | RDF named graphs (apps, cross-app, approved) |
| Postgres | Registry, interface, OpenAPI, operations, embeddings, proposals, decisions, engineering, GraphRAG, SOP page cache |
| pgvector | API index + SOP/doc vectors |

**Zero** product pipeline output under the repo (`data/eakg/repos`, `data/pipeline_store`, …).

## File mode (`EAKG_STORE__BACKEND=file`) — tests / offline

Root: `EAKG_STORE__FILE_SHARD_DIR` (default `data/pipeline_store`, gitignored except README).

| Path | Mirrors |
|---|---|
| `GraphDb/named_graphs/*.ttl` | SPARQL named graphs |
| `Postgres/…` | Artifact tables (interface, ops, embeddings, engineering, …) |
| `Pgvector/…` | Optional offline vector sidecars |

Legacy `data/eakg/repos|enterprise|…` shards are **not** product layout anymore.

## Rebuild after clone (product)

Point env at GraphDB + Postgres + pgvector, then onboard / cross-app / ApiIndex refresh as in [`PIPELINES.md`](PIPELINES.md). File-mode operators use `EAKG_STORE__BACKEND=file` and the pipeline_store tree.

## Agent / MCP

When `CAPABILITY_KG__ENABLED=true`, discovery reads GraphStore / merged file mirrors. No shards → OpenAPI keyword search only. Product agent path: `TOOLS_CLIENT__PROVIDER=mcp`. See [`MCP_CLIENT_INTEGRATION.md`](MCP_CLIENT_INTEGRATION.md).
