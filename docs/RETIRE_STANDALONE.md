# Standalone retirement checklist (ADR-010)

**Current focus: local testing only.** Do **not** point the wiki AWS front door
at a Python image yet. No ECR rebuild, no `tofu apply -replace`, no AgentCore
cutover until local SSE + docs + agent paths are green.

After module parity **and** an explicit go-ahead, archive — do not run two
backends for the same feature.

## SSE gateway (Node handoff)

Parity when:

- [x] `packages/sse` catalog/search/call tools exist
- [x] API key store (`packages/sse/api_keys.py`)
- [x] Fixture mode for offline demo
- [ ] Live swagger load verified against PennEDocs + CoreComponents (local `.env`)
- [ ] Token refresh (Priority-1 from handoff) ported

Then (later): freeze `sse-unified-gateway-handoff-*`, point Cursor MCP at
`POST /mcp/tools/call` on local Agent API (`http://127.0.0.1:8000`).

## plaisse-wiki

Parity when:

- [x] Wiki tool names registered (`packages/wiki`) — stubs
- [ ] Doc write / GitLab / Jira / package / screen specialists ported
- [ ] Live API/SQL exclusively via `packages/sse` + `packages/db`

**Deferred:** Python image published into existing wiki AWS front door
(API GW / AgentCore / RDS). Skip until local testing is done.

## Deploy

**Skipped for now.** Local only:

```text
make demo   # or uvicorn apps.agent_api.main:app + npm run dev in apps/web_ui
# TOOLS_CLIENT__PROVIDER=modular (only supported provider)
# SSE__USE_FIXTURE=false + SSE__API_KEY for live Loan Services
```

Reuse wiki tofu path later; not this phase.
