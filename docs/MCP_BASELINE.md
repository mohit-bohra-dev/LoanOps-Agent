# MCP Baseline

Phase 1 of the MCP + RDF Capability KG + ARD master plan. Records what the running tree actually does. Architecture detail: [`ARCHITECTURE.md`](../ARCHITECTURE.md). Phase matrix: [`MCP_ARD_PHASE_MATRIX.md`](MCP_ARD_PHASE_MATRIX.md).

Secret values are not included.

## Refresh log

| Date | HEAD (short) | Change |
|---|---|---|
| 2026-09-30 (original) | `8235e90` | Pre-MCP protocol; live `getLoanSummary` → **401** |
| 2026-09-30 (refresh) | `3ffbef5`+ | ADR-011/013 present; live `getLoanSummary` → **200** via modular and MCP hop |

Post-ADR-011: `python -m packages.mcp_server` is a real Streamable HTTP MCP listener on port 8001. ADR-013: `TOOLS_CLIENT__PROVIDER=mcp` routes agent tools through that listener; default `modular` remains the offline-safe path.

---

## 1. What was measured (refresh)

| Check | Result |
|---|---|
| `TOOLS_CLIENT__PROVIDER` | `mcp` (local `.env`; `MCP__AUTH_TOKEN` set) |
| In-process `call_sse_api` `getLoanSummary` | **HTTP 200**, tool success |
| MCP hop `list_tools` | Four names: search/list/call SSE + `search_docs` |
| MCP hop `call_sse_api` `getLoanSummary` | **HTTP 200**, tool success |
| Catalog | Local `sse-loanservices-catalog.json` (fixture path set; live HTTP to configured host) |
| Custom `/mcp/tools` | Still a JSON wrapper — **not** Model Context Protocol |

Earlier baseline rows (health 200, search_sse_apis success, Bedrock SSO chat failure, search_docs config issues) remain historically valid unless re-run.

---

## 2. Configuration actually loaded (refresh)

From `Settings()` against the local `.env`. Names and non-secret facts only.

| Setting | Loaded value |
|---|---|
| `TOOLS_CLIENT__PROVIDER` | `mcp` |
| `MCP__HOST` / `MCP__PORT` / `MCP__PATH` | `127.0.0.1` / `8001` / `/mcp` |
| `MCP__AUTH_TOKEN` | set (value not recorded) |
| `MCP__ROLE` | `system` |
| `AGENT_ROLE` | `system` |
| `SSE__USE_FIXTURE` | `false` |
| `SSE__FIXTURE_PATH` | `sse-loanservices-catalog.json` (catalog-only) |
| `SSE__API_KEY` | set (value not recorded) |
| `SSE__API_BASE_URL` host | `loanservicesapi-plaisse-dev.pnmac.com` |
| `SSE__SWAGGER_LINKS` | 1 link, id `loanservices` |

---

## 3. Tool surface

`ModularToolsClient` / MCP server for role `system`:

```text
search_sse_apis
list_sse_apis
call_sse_api
search_docs
```

---

## 4. Representative calls (refresh)

### 4.1 Live API via in-process client

```text
tool: call_sse_api
args: operation_id=getLoanSummary, path_params.loan_id=1000002245
success: true
downstream: HTTP 200
host: loanservicesapi-plaisse-dev.pnmac.com
```

### 4.2 Same call via MCP hop

```text
client: McpToolsClient → http://127.0.0.1:8001/mcp
tool: call_sse_api
success: true
downstream: HTTP 200
```

### 4.3 Catalog list (custom `/mcp` HTTP, not MCP protocol)

Unchanged: `POST /mcp/tools/call` with `list_sse_apis` remains a JSON helper on the Agent API.

---

## 5. Gaps (updated)

1. **Full `/chat` LLM turn compare** still needs a working Bedrock SSO session for fair MCP-vs-modular latency/answer eval.
2. **Catalog is still a local OpenAPI file**, not live swagger fetch.
3. **`search_docs`** may still fail if vector store / docs providers are not configured.
4. **Custom `/mcp/tools` is not MCP.** Prefer `packages.mcp_server` for protocol clients.
5. **RDF Capability KG** shipped after this refresh (Phase 2).
6. **Eval thresholds** unchanged; capability-selection metrics not yet in the gate.

---

## 6. Preserved behavior (do not replace)

- In-process fallback: `TOOLS_CLIENT__PROVIDER=modular` → `ModularToolsClient` → `invoke_sse_api` / `DocsService`.
- Tool names and argument shapes for the four tools above.
- SSE host allow-list and bearer attachment inside `invoke_sse_api`.
- Intent router and PII/safety middleware on `/chat`.
- Eval threshold numbers.
- Graphify stays off the request path and is not the capability registry.
- Chat UI contract: one SSE `data:` frame, `AgentTurnOutput` or `{error, turn_id}`.
