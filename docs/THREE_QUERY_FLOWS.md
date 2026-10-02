# Three query flows (UI Agent vs Cursor)

Layman + code path for the same helpers (`ModularToolsClient`).

**North star:** EAKG fills tools → MCP `:8001` → agent `/chat` + Cursor share that endpoint.

---

## Flow A — Care-rep UI with modular (desk drawer)

**When:** `TOOLS_CLIENT__PROVIDER=modular`  
**Need:** Agent API `:8000` only (MCP optional)

```text
Care-rep UI  →  POST /chat (:8000)  →  run_agent_turn
                                      →  ModularToolsClient.call
                                      →  SSE / docs / db / wiki / EAKG
```

Like ChatGPT app → backend → model + tools **inside same process**.

| Step | Code |
|------|------|
| HTTP entry | `apps.agent_api.main` `POST /chat` |
| Pick client | `packages.tools.factory.get_tools_client_provider` → `build_modular_tools_client` |
| Agent loop | `packages.agent_core._agent.run_agent_turn` → `tools_client.call` |
| Helpers | `packages.tools.modular_tools.ModularToolsClient.call` → `dispatch_sse_tool` / docs / … |

**Use:** local demo, rollback when `:8001` down.

---

## Flow B — Care-rep UI with MCP hop (shared supply closet via Agent)

**When:** `TOOLS_CLIENT__PROVIDER=mcp`  
**Need:** Agent API `:8000` **and** MCP `:8001`

```text
Care-rep UI  →  POST /chat (:8000)  →  run_agent_turn
                                      →  McpToolsClient.call
                                      →  HTTP Streamable MCP (:8001/mcp)
                                      →  mcp_server tool handler
                                      →  ModularToolsClient.call
                                      →  SSE / docs / …
```

Same ChatGPT-style UI. Agent walks to **shared tool room** instead of desk drawer.

| Step | Code |
|------|------|
| HTTP entry | same `POST /chat` |
| Pick client | `get_tools_client_provider` → `build_mcp_tools_client` |
| Agent loop | same `run_agent_turn` → `tools_client.call` |
| MCP client | `packages.tools.mcp_tools_client.McpToolsClient.call` → `session.call_tool` |
| MCP server | `packages.mcp_server.server` `@mcp.tool` → `_run` → `build_modular_tools_client` |

Branch (modular vs mcp):

```python
# packages/tools/factory.py — get_tools_client_provider()
if cfg.tools_client.provider == "modular":
    return build_modular_tools_client(...)
if cfg.tools_client.provider == "mcp":
    return build_mcp_tools_client(...)
```

**Use:** product path (D1) — agent uses same MCP server as IDEs.

---

## Flow C — Cursor Chat (skip Agent API)

**When:** Cursor MCP server `loanops` / namespace `user-loanops`  
**Need:** MCP `:8001` only (`TOOLS_CLIENT__PROVIDER` irrelevant)

```text
You (Cursor Chat)  →  Cursor MCP client
                   →  HTTP Streamable MCP (:8001/mcp) + Bearer MCP__AUTH_TOKEN
                   →  mcp_server auth + policy
                   →  ModularToolsClient.call
                   →  SSE / docs / EAKG
```

Not the ChatGPT-style LoanOps app. Cursor is **another client of the same tool room**.

| Step | Where |
|------|--------|
| Config | `~/.cursor/mcp.json` → `url: http://127.0.0.1:8001/mcp` |
| Tools | `search_sse_apis`, `list_sse_apis`, `call_sse_api`, `search_docs`, EAKG tools, … |
| Server | `python -m packages.mcp_server` → always `build_modular_tools_client` |

Evidence: `docs/MCP_CURSOR_VALIDATION.md`. Diagram twin: `docs/FLOWS.md` **F11**.

---

## One picture

```text
                    ┌── A modular ──► ModularToolsClient ──► SSE/docs/...
UI ──► Agent :8000 ─┤
                    └── B mcp ──────► McpToolsClient ─HTTP─► MCP :8001 ─┐
                                                                       ├─► ModularToolsClient
Cursor Chat ──────────────────────── C ────────────────────► MCP :8001 ─┘
```

**Helpers same in A, B, and C.** Difference = who calls them and whether Agent hops HTTP.

---

## Who decides which tool to call?

Code does **not** map “loan summary” → `getLoanSummary` with a big if/else.  
A **model** picks the tool name; code offers a menu and executes what was named.

### Flow A — modular

1. `classify_intent` may refuse / escalate → **no tools**.
2. Agent builds menu from `_SSE_ANSWER_TOOLS` (filtered by role `allowed_tools`): typically `search_sse_apis`, `list_sse_apis`, `call_sse_api`, `search_docs`.
3. Agent LLM (`chat_provider.chat(..., tools=tools_def)`) returns `tool_calls`.
4. `run_agent_turn` → `_execute_tools` → `ModularToolsClient.call` for each name.
5. Up to 3 rounds: tool results fed back → model may call again or emit final JSON.

**Chooser:** Agent’s LLM. **Executor:** in-process `ModularToolsClient`.

### Flow B — Agent MCP hop

Same as A through step 3 (same Agent menu + same Agent LLM).

4. `_execute_tools` → `McpToolsClient.call` → HTTP `tools/call` on `:8001`.
5. MCP server runs that name via `ModularToolsClient` (does **not** re-decide).

**Chooser:** Agent’s LLM. **Executor:** MCP → `ModularToolsClient`.

### Flow C — Cursor

1. No Agent API / no `TOOLS_CLIENT__PROVIDER`.
2. Cursor `tools/list` on MCP → LoanOps tool schemas (SSE + docs + EAKG for role).
3. **Cursor’s model** picks tool + args.
4. Cursor `tools/call` → MCP → `ModularToolsClient`.

**Chooser:** Cursor’s LLM. **Executor:** MCP → `ModularToolsClient`  
(line “ModularToolsClient.call” in Flow C = **server** after auth, not Cursor importing that class).

### Side by side

| | A modular | B MCP hop | C Cursor |
|---|---|---|---|
| Chooses tool | Agent LLM | Agent LLM | Cursor LLM |
| Menu source | `_SSE_ANSWER_TOOLS` in Agent | Same in Agent | MCP `tools/list` |
| Executes | `ModularToolsClient` in Agent | MCP → `ModularToolsClient` | MCP → `ModularToolsClient` |

Code refs: `packages/agent_core/_agent.py` (`_tools_for_client`, tool loop); `packages/tools/factory.py` (modular vs mcp client).

---

## Related

| Doc | Content |
|-----|---------|
| `docs/FLOWS.md` F1 | Product chat (MCP hop) |
| `docs/FLOWS.md` F2 | Modular in-process |
| `docs/FLOWS.md` F11 | Real MCP (Cursor / Gemini / agent client) |
| `ARCHITECTURE.md` | Living architecture |
| ADR-013 | Agent as MCP consumer |
