# MCP Implementation

## What exists

| Piece | Location | ADR |
|---|---|---|
| Streamable HTTP MCP server | `packages/mcp_server` | ADR-011 |
| Agent MCP client | `packages/common/mcp_tools_client.py` | ADR-013 |
| Factory flag | `TOOLS_CLIENT__PROVIDER=modular\|mcp` | ADR-013 |
| Custom JSON `/mcp/tools` | `apps/agent_api/mcp_routes.py` | **not** protocol MCP |

## Run listener

```powershell
$env:MCP__AUTH_TOKEN = "dev-mcp-token"
python -m packages.mcp_server
```

Default: `http://127.0.0.1:8001/mcp`.

## Agent hop

```env
TOOLS_CLIENT__PROVIDER=mcp
MCP__AUTH_TOKEN=dev-mcp-token
```

Rollback: `TOOLS_CLIENT__PROVIDER=modular`.

## Tools exposed (v1)

`search_sse_apis`, `list_sse_apis`, `call_sse_api` (GET-only on MCP), `search_docs`.

Execution still goes through `ModularToolsClient` → `invoke_sse_api` / docs. No per-OpenAPI MCP tool explosion.

## Multi-client

Same Streamable HTTP endpoint for LoanOps agent, Cursor, Gemini. No client-specific branches.

## Security (current)

- Bearer `MCP__AUTH_TOKEN` required
- Role scopes via `MCP__ROLE` / `scopes.py`
- `call_sse_api` GET-only + no body on MCP server
- Audit event `mcp.tool.call`
- SSE host allow-list in `invoke_sse_api`

## Next (see phase matrix)

Auth harden, capability-native tools (approved RDF caps), Cursor/Gemini validation notes.
