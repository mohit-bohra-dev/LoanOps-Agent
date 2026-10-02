# MCP Security

## Current controls

| Control | Where |
|---|---|
| MCP bearer | `MCP__AUTH_TOKEN` + FastMCP `TokenVerifier` |
| Tool scope | `packages/common/scopes.py` + `MCP__ROLE` |
| Read-only SSE on MCP | GET-only `call_sse_api`, body rejected |
| Capability bind | `capability_bind.py` — `capability_id` → catalog `operation_id`; mismatch rejected. Hard-require via `CAPABILITY_KG__REQUIRE_CAPABILITY_BIND` |
| Capability permission | `capability_authz.py` — `requiresPermission` vs role/config allow-list when `CAPABILITY_KG__ENFORCE_PERMISSIONS=true` |
| Host allow-list | `invoke_sse_api` / `assert_allowed_url` |
| Audit | `mcp.tool.call` via audit sink (SSE + EAKG tools) |
| Principal headers | `x-loanops-user` / `x-loanops-tenant` from request or `MCP__PRINCIPAL_USER` / `MCP__PRINCIPAL_TENANT`; injected into `call_sse_api` outbound headers |
| EAKG `approved_only` | When `CAPABILITY_KG__APPROVED_ONLY=true`, EAKG MCP tools read `catalog/approved.ttl` only |
| Optional headers | `x-loanops-user`, `x-loanops-tenant` (audit + outbound) |

## Not yet

- End-user OBO into enterprise API (still process `SSE__API_KEY` = Subservicing Auth0 **M2M** service bearer; D7)
- Defaults still off for bind-required + permission enforce (flip flags when ready)
- mTLS / OAuth for remote MCP

## Rules

- Do not allow model-generated absolute URLs outside allow-list
- Do not assume POST = write; use capability `readOnly` metadata
- Do not log bearer tokens or raw PII in MCP audit payloads
- Prefer `search_capabilities` → `call_sse_api(capability_id=…)` over free-form `operation_id`
