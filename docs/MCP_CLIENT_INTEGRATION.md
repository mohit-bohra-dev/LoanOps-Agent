# MCP Client Integration

## LoanOps Agent

```text
run_agent_turn → ToolsClientProvider
                    ├─ modular → ModularToolsClient (in-process)
                    └─ mcp → McpToolsClient → Streamable HTTP → packages.mcp_server
```

Settings: `TOOLS_CLIENT__PROVIDER`, `MCP__*`.

## Cursor / Gemini / other

Point the client's MCP config at:

```text
http://127.0.0.1:8001/mcp
Authorization: Bearer <MCP__AUTH_TOKEN>
```

Use the same four tools. Do not fork server code per client.

## Custom Agent API `/mcp/tools`

JSON helper for the React sidebar. **Not** Model Context Protocol. Prefer the Streamable HTTP listener for external agents.
