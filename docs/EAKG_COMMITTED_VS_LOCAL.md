# EAKG: committed vs local-only

Quick map so clean clones and CI do not confuse registry seed with live enterprise shards.

**How TAAC becomes graph (simple):** [`EAKG_TAAC.md`](EAKG_TAAC.md).

**Source of truth (D4):** EAKG shards / approved catalog only.  
ADR-014 single TTL fallback **removed** from product search.

## In git (safe to commit)

| Path | What |
|---|---|
| `packages/eakg/` | Pipeline code + synthetic fixture tests |
| `data/eakg/registry/repositories.yaml` | Repo registry (ids, GitLab URLs, index metadata) |
| `data/eakg/fixtures/` | Redacted TAAC / synthetic configs only |
| `docs/EAKG_*.md`, `ci/eakg.gitlab-ci.yml`, `scripts/eakg/` | Ops + docs |
| `packages/capability_kg/` + `data/capability_kg/README.md` | Catalog facade + build CLI (not product discovery) |

## Local only (gitignored — never commit)

| Path | What | Role |
|---|---|---|
| `.eakg-workspace/` | `glab` clones of Escrow/Fees/LoanServices (+ live TAAC drop) | Input |
| `.eakg-workspace/graphify/` | Optional local Graphify AST dumps of those clones | **Not pipeline** — see [`ENGINEERING_GRAPH_ANALYSIS.md`](ENGINEERING_GRAPH_ANALYSIS.md) |
| `data/eakg/repos/` | Per-repo `graph.ttl` / `interface.json` shards (+ optional `engineering/`) | **Truth** |
| `data/eakg/enterprise/` | Merged apps + `cross_app.ttl` | **Truth** |
| `data/eakg/catalog/` | `approved.ttl` publish output | **Truth** (reviewed slice) |
| `data/eakg/proposals/` | LLM semantic proposal queue | Overlay |
| `data/eakg/decisions/` | Append-only review decisions JSONL | Audit |

## Rebuild after clone

```powershell
# register already in yaml for pilot three
uv run python -m packages.eakg onboard --id escrow
uv run python -m packages.eakg onboard --id fees
uv run python -m packages.eakg onboard --id loanservices
uv run python -m packages.eakg cross-app
uv run python -m packages.eakg review --pilot
```

Or nightly: `.\scripts\eakg\sync-nightly.ps1` (needs `glab` auth).

## Agent / MCP

When `CAPABILITY_KG__ENABLED=true` and `data/eakg/repos/*` exist, `search_sse_apis`
merges **EAKG**. If no shards → OpenAPI keyword search only (no TTL fallback).
Product agent path: `TOOLS_CLIENT__PROVIDER=mcp` → same MCP tools. See
[`MCP_CLIENT_INTEGRATION.md`](MCP_CLIENT_INTEGRATION.md).
