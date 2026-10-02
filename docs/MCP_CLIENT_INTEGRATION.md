# MCP Client Integration

## Product shape

**LoanOps agent `/chat` is a first-party consumer of `packages.mcp_server`.**
Same Streamable HTTP endpoint as Cursor / Gemini. Do not grow a second,
agent-only tools architecture beside MCP.

| Mode | When |
|---|---|
| `TOOLS_CLIENT__PROVIDER=mcp` | Product path — agent → MCP → SSE / docs / EAKG |
| `TOOLS_CLIENT__PROVIDER=modular` | Local-first single-process demo + rollback |

Server-side execution stays `ModularToolsClient` / `invoke_sse_api` inside the
MCP process. The hop is agent → MCP; not agent → SSE bypassing MCP.

## LoanOps Agent

```text
run_agent_turn → ToolsClientProvider
                    ├─ modular → ModularToolsClient (in-process; demo/rollback)
                    └─ mcp → McpToolsClient → Streamable HTTP → packages.mcp_server
                                      └─ SSE / docs / EAKG tools
```

Settings: `TOOLS_CLIENT__PROVIDER`, `MCP__*`, align `AGENT_ROLE` with `MCP__ROLE`.

## Cursor / Gemini / other

Point the client's MCP config at:

```text
http://127.0.0.1:8001/mcp
Authorization: Bearer <MCP__AUTH_TOKEN>
```

Same tool surface as the agent MCP client. Do not fork server code per client.
Validation checklists: [`MCP_CURSOR_VALIDATION.md`](MCP_CURSOR_VALIDATION.md),
[`MCP_GEMINI_VALIDATION.md`](MCP_GEMINI_VALIDATION.md).

## Custom Agent API `/mcp/tools`

JSON helper for the React sidebar. **Not** Model Context Protocol. Prefer the
Streamable HTTP listener for the agent and for external clients.
