# MCP + Capability KG + ARD — Phase Status

Recorded 2026-09-30. Detail: [`MCP_ARD_PHASE_MATRIX.md`](MCP_ARD_PHASE_MATRIX.md).
Next plan: [`PHASE_9_SEMANTIC_RETRIEVAL.md`](PHASE_9_SEMANTIC_RETRIEVAL.md).

## Done

| Phase | Name | Evidence |
|---|---|---|
| 1 | Baseline | `docs/MCP_BASELINE.md` (live + MCP hop HTTP 200) |
| 2 | RDF Capability Graph | `packages/capability_kg/`, `data/capability_kg/capabilities.ttl` |
| 3 | Capability Catalog | `CapabilityCatalog` facade; optional `search_sse_apis` RDF block |
| 4 | Real MCP server | `packages/mcp_server`, ADR-011 |
| 5 | Streamable HTTP | FastMCP `:8001` |
| 6 | MCP client | `packages/common/mcp_tools_client.py`, ADR-013 |
| 7 | Agent behind MCP | `TOOLS_CLIENT__PROVIDER=mcp` (default still `modular`) |

Graph source for Phase 2: OpenAPI fixture `data/sse-loanservices-catalog.json` only. Not Graphify. Not live swagger. Not SSE app source.

## Partial

| Phase | Name | Done | Still open |
|---|---|---|---|
| 8 | Auth / authz / audit | Bearer, scopes, GET-only, audit; principal headers on `call_sse_api`; EAKG tools via scopes + `approved_only` → `catalog/approved.ttl` | Full OBO (still `SSE__API_KEY` service bearer); `requiresPermission` at invoke edge |
| 13 | Governance | `hasReviewStatus` in ontology; EAKG `review --pilot` + approved catalog | Human review workflow / UI |

## Pending

| Phase | Name | Notes |
|---|---|---|
| 10 | Graphify offline enrichment | Enrich RDF from LoanOps code graph; not runtime |
| 11 | Validate Cursor | Todo — checklist [`MCP_CURSOR_VALIDATION.md`](MCP_CURSOR_VALIDATION.md); evidence TBD |
| 12 | Validate Gemini | Todo — checklist [`MCP_GEMINI_VALIDATION.md`](MCP_GEMINI_VALIDATION.md); evidence TBD |
| 14 | ARD | Pending — decision draft [`ARD_RESOURCE_CHOICE.md`](ARD_RESOURCE_CHOICE.md); after 11–12 green |

## Recently completed

| Phase | Name | Notes |
|---|---|---|
| EAKG | Multi-repo enterprise KG | `packages/eakg/` ADR-015..019; real pilot shards; review --pilot; SSE shard merge |
| 9 | Semantic capability retrieval | `CAPABILITY_KG__SEMANTIC`; see `PHASE_9_SEMANTIC_RETRIEVAL.md` |

## Preserve (do not replace)

- Real SSE APIs (`invoke_sse_api`)
- Four-tool surface until approved capability tools
- Custom `/mcp/tools` JSON helper (not protocol MCP)
- Graphify = code intelligence only
- RAG `search_docs` separate from capability discovery
- Eval thresholds (never lower without approval)
