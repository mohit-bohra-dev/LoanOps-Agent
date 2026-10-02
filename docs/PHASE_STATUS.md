# MCP + Capability KG + ARD — Phase Status

Recorded 2026-10-02. Detail: [`MCP_ARD_PHASE_MATRIX.md`](MCP_ARD_PHASE_MATRIX.md).
North star: **MCP platform** — EAKG feeds tools; agent `/chat` + Cursor/Gemini consume same `:8001/mcp`.
See [`MCP_CLIENT_INTEGRATION.md`](MCP_CLIENT_INTEGRATION.md), [`EAKG_COMMITTED_VS_LOCAL.md`](EAKG_COMMITTED_VS_LOCAL.md), [`DECIDE_AND_CLEANUP.md`](DECIDE_AND_CLEANUP.md), [`STACK_LAYER_DECISIONS.md`](STACK_LAYER_DECISIONS.md).

## Done

| Phase | Name | Evidence |
|---|---|---|
| 1 | Baseline | `docs/MCP_BASELINE.md` (live + MCP hop HTTP 200) |
| 2 | RDF Capability Graph | `packages/capability_kg/`, `data/capability_kg/capabilities.ttl` |
| 3 | Capability Catalog | `CapabilityCatalog` facade; optional `search_sse_apis` RDF block |
| 4 | Real MCP server | `packages/mcp_server`, ADR-011 |
| 5 | Streamable HTTP | FastMCP `:8001` |
| 6 | MCP client | `packages/common/mcp_tools_client.py`, ADR-013 |
| 7 | Agent behind MCP | Flag `TOOLS_CLIENT__PROVIDER=mcp` (default still `modular` for demo) |
| 9 | Semantic capability retrieval | `CAPABILITY_KG__SEMANTIC`; [`PHASE_9_SEMANTIC_RETRIEVAL.md`](PHASE_9_SEMANTIC_RETRIEVAL.md) |
| EAKG | Multi-repo enterprise KG | `packages/eakg/` ADR-015..019; pilot; review gate; shard merge |
| 11 | Validate Cursor | [`MCP_CURSOR_VALIDATION.md`](MCP_CURSOR_VALIDATION.md) (2026-10-02) |

Graph source for Phase 2 seed: OpenAPI fixture. Live enterprise ops: EAKG shards (local).

## Partial

| Phase | Name | Done | Still open |
|---|---|---|---|
| 8 | Auth / authz / audit | Bearer, scopes, GET-only, audit; principal headers; EAKG `approved_only` | Full OBO; `requiresPermission` at invoke |
| 13 | Governance | ReviewStatus + EAKG `review --pilot` + approved catalog | Human review UI |

## Pending (next)

| Phase | Name | Notes |
|---|---|---|
| 12 | Validate Gemini | Checklist ready — record evidence |
| 14 | ARD | Decision draft only — after 11–12 |

## Parked

| Phase | Name | Notes |
|---|---|---|
| 10 | Graphify → RDF enrichment | Offline only; not runtime |
| — | Roslyn/tree-sitter extractor | Roslyn = primary target; regex interim — [`STACK_LAYER_DECISIONS.md`](STACK_LAYER_DECISIONS.md) |
| — | Live swagger CI ask | [`EAKG_SWAGGER_EXPORT.md`](EAKG_SWAGGER_EXPORT.md) |
| — | Repo #4+ | [`EAKG_ONBOARD_REPO.md`](EAKG_ONBOARD_REPO.md) |
| — | CodeQL / tree-sitter | Phase 2 per stack board |

## Preserve (do not replace)

- Real SSE APIs (`invoke_sse_api`) behind MCP server (not a second agent bypass)
- Agent `/chat` as MCP consumer (`TOOLS_CLIENT__PROVIDER=mcp` product path; `modular` = demo/rollback)
- Four-tool surface until approved capability tools (+ EAKG tools under `eakg.read`)
- Custom `/mcp/tools` JSON helper (not protocol MCP)
- Graphify = code intelligence only
- RAG `search_docs` separate from capability discovery
- Eval thresholds (never lower without approval)
