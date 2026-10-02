# MCP Security

## Current controls

| Control | Where |
|---|---|
| MCP bearer | `MCP__AUTH_TOKEN` + FastMCP `TokenVerifier` |
| Tool scope | `packages/common/scopes.py` + `MCP__ROLE` |
| Read-only SSE on MCP | GET-only `call_sse_api`, body rejected |
| Host allow-list | `invoke_sse_api` / `assert_allowed_url` |
| Audit | `mcp.tool.call` via audit sink |
| Optional headers | `x-loanops-user`, `x-loanops-tenant` (audit only today) |

## Not yet

- End-user identity propagation into enterprise API (still process `SSE__API_KEY`)
- Capability-level `requiresPermission` enforcement at MCP edge
- `approved_only` gate on MCP tool list
- mTLS / OAuth for remote MCP

## Rules

- Do not allow model-generated absolute URLs outside allow-list
- Do not assume POST = write; use capability `readOnly` metadata
- Do not log bearer tokens or raw PII in MCP audit payloads
