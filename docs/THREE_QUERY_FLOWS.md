# Three query flows (Cursor MCP first)

Layman + code path for the same helpers (`ModularToolsClient`).

**North star:** EAKG fills tools → MCP `:8001` → Cursor (and later agent `/chat`) share that endpoint.

**Current product focus:** **Flow C** (Cursor → MCP). Flows A/B (UI chat) are supported but secondary.

---

## Flow C — Cursor Chat (primary)

**When:** Cursor MCP server `loanops` / namespace `user-loanops`  
**Need:** MCP `:8001` only (`TOOLS_CLIENT__PROVIDER` irrelevant)

```text
You (Cursor Chat)  →  Cursor MCP client
                   →  HTTP Streamable MCP (:8001/mcp) + Bearer MCP__AUTH_TOKEN
                   →  mcp_server auth + scope + GET-only bind
                   →  ModularToolsClient.call  (policy + SSE / docs / EAKG)
```

Not the ChatGPT-style LoanOps app. Cursor is **another client of the same tool room**.

| Step | Where |
|------|--------|
| Config | `~/.cursor/mcp.json` → `url: http://127.0.0.1:8001/mcp` |
| Tools | `search_sse_apis`, `list_sse_apis`, `call_sse_api`, `search_docs`, EAKG tools, … |
| Server | `python -m packages.mcp_server` → `build_modular_tools_client` |
| Readiness | `GET http://127.0.0.1:8001/ready` (liveness: `/health`) |

Evidence: `docs/MCP_CURSOR_VALIDATION.md`. Diagram twin: `docs/FLOWS.md` **F11**.  
Debug: `docs/DEBUG_LAYER2.md` Flow C. Review focus: `docs/ARCHITECTURE_REVIEW_LAYER2.md`.

---

## Flow A — UI with modular (desk drawer)

**When:** `TOOLS_CLIENT__PROVIDER=modular`  
**Need:** Agent API `:8000` only (MCP optional)

```text
UI  →  POST /chat (:8000)  →  run_agent_turn
                            →  ModularToolsClient.call
                            →  SSE / docs / db / wiki / EAKG
```

| Step | Code |
|------|------|
| HTTP entry | `apps.agent_api.main` `POST /chat` |
| Pick client | `packages.tools.factory.get_tools_client_provider` → `build_modular_tools_client` |
| Agent loop | `packages.agent_core._agent.run_agent_turn` → `tools_client.call` |
| Helpers | `ModularToolsClient.call` → `dispatch_sse_tool` / EAKG / docs / … |

**Use:** local demo, rollback when `:8001` down.

---

## Flow B — UI with MCP hop

**When:** `TOOLS_CLIENT__PROVIDER=mcp`  
**Need:** Agent API `:8000` **and** MCP `:8001`

```text
UI  →  POST /chat (:8000)  →  run_agent_turn
                            →  McpToolsClient.call
                            →  HTTP Streamable MCP (:8001/mcp)
                            →  mcp_server → ModularToolsClient.call
```

| Step | Code |
|------|------|
| HTTP entry | same `POST /chat` |
| Pick client | `get_tools_client_provider` → `build_mcp_tools_client` |
| MCP server | `packages.mcp_server.server` `@mcp.tool` → `_run` → modular client |

**Use:** product path when UI should share the Cursor tool room (D1).

---

## One picture

```text
Cursor Chat ──────────────── C ────────────────────► MCP :8001 ─┐
                                                                 ├─► ModularToolsClient
UI ──► Agent :8000 ─┬── A modular ──► ModularToolsClient ───────┤
                    └── B mcp ──────► McpToolsClient ─HTTP──────┘
```

**Helpers same in A, B, and C.** Difference = who calls them and whether Agent hops HTTP.

Read-only policy is enforced in `ModularToolsClient` / `invoke_sse_api` **and** at MCP `execute_tool` (defense-in-depth).
