# MCP / ARD Phase Matrix

Recorded on 2026-09-30 against `vdd`. Checklist copy: [`PHASE_STATUS.md`](PHASE_STATUS.md). Next: [`PHASE_9_SEMANTIC_RETRIEVAL.md`](PHASE_9_SEMANTIC_RETRIEVAL.md).

Layer boundaries (do not mix):

| Layer | Job |
|---|---|
| Graphify | How LoanOps software is implemented (`graphify-out/`) |
| RDF Capability KG | What the enterprise can do (capabilities, permissions, API maps) |
| Capability Catalog | How apps discover capabilities (hides RDF) |
| MCP | How AI clients invoke capabilities |
| ARD | Which enterprise MCP resource to connect to (later) |

---

## Phase status

| Master phase | Name | Status | Notes |
|---|---|---|---|
| 1 | Baseline | **Done** (refreshed 2026-09-30) | Docs + smoke; no app change for refresh |
| 2 | RDF Capability Graph | **Done** (v1) | RDFLib + Turtle + SPARQL; OpenAPI extract |
| 3 | Capability Catalog service | **Done** (v1) | `CapabilityCatalog` facade over RDF |
| 4 | Real MCP server | **Done** | ADR-011 `packages/mcp_server` |
| 5 | Streamable HTTP | **Done** | FastMCP on `:8001` |
| 6 | MCP client abstraction | **Done** | ADR-013 `McpToolsClient` |
| 7 | Agent behind MCP | **Done** (flag) | `TOOLS_CLIENT__PROVIDER=mcp`; default still `modular` |
| 8 | Auth / authz / audit harden | **Partial** | Bearer + scopes + GET guard + audit; no full principal→API identity |
| 9 | Semantic capability retrieval | **Done** (v1) | Cosine over embeddings.json + SPARQL filters; `CAPABILITY_KG__SEMANTIC` |
| 10 | Graphify offline enrichment | **Todo** | Enrich RDF from LoanOps code graph; not runtime |
| 11 | Validate Cursor | **Todo** | Same remote MCP endpoint |
| 12 | Validate Gemini | **Todo** | Same remote MCP endpoint |
| 13 | Capability governance / human review | **Partial model** | ReviewStatus in ontology; UI/workflow later |
| 14 | ARD integration | **Todo** | Explicitly after MCP + catalog stable |

---

## Preserve

- Real SSE / Loan Services APIs (`invoke_sse_api`)
- Four-tool surface (`search_sse_apis`, `list_sse_apis`, `call_sse_api`, `search_docs`) until capability tools are approved
- Custom `/mcp/tools` JSON helper (not protocol MCP)
- Graphify as code intelligence only
- RAG (`search_docs`) separate from capability discovery
- Eval thresholds (never lower without approval)
- Safety / intent / host allow-list
