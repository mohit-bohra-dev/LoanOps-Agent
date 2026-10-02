# MCP Security

## Current controls

| Control | Where |
|---|---|
| MCP bearer | `MCP__AUTH_TOKEN` + FastMCP `TokenVerifier` |
| Tool scope | `packages/common/scopes.py` + `MCP__ROLE` |
| Read-only SSE on MCP | GET-only `call_sse_api`, body rejected |
| Host allow-list | `invoke_sse_api` / `assert_allowed_url` |
| Audit | `mcp.tool.call` via audit sink (SSE + EAKG tools) |
| Principal headers | `x-loanops-user` / `x-loanops-tenant` from request or `MCP__PRINCIPAL_USER` / `MCP__PRINCIPAL_TENANT`; injected into `call_sse_api` outbound headers |
| EAKG `approved_only` | When `CAPABILITY_KG__APPROVED_ONLY=true`, EAKG MCP tools read `catalog/approved.ttl` only |
| Optional headers | `x-loanops-user`, `x-loanops-tenant` (audit + outbound) |

## Not yet

- End-user OBO into enterprise API (still process `SSE__API_KEY` = Subservicing Auth0 **M2M** service bearer; D7)
- Capability-level `requiresPermission` enforcement at MCP edge
- mTLS / OAuth for remote MCP

## Rules

- Do not allow model-generated absolute URLs outside allow-list
- Do not assume POST = write; use capability `readOnly` metadata
- Do not log bearer tokens or raw PII in MCP audit payloads
