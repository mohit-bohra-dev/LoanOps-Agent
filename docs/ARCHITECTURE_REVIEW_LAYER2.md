# LoanOps-Agent Architecture Review — Cursor → MCP (Flow C)

**Date:** 2026-04-08 (refocused)  
**Primary scope:** Cursor Chat → Streamable HTTP MCP `:8001` → ModularToolsClient → SSE / docs / EAKG  
**Out of scope for now:** UI `/chat`, Agent Core, Agent API sidebar, **PII / audit redaction**, **auth / identity / tokens / principals** — see §8 Deferred  
**Status:** Active Required items implemented 2026-04-08 (ADR-022/023 Proposed). Auth / PII / UI still deferred (§8).

---

## 1. Focus for this document

LoanOps exposes the same tool helpers three ways. **This review cares about Flow C only:**

| Flow | Path | This doc |
|------|------|----------|
| **A — Modular** | UI → Agent API → tools in-process | Deferred |
| **B — MCP hop** | UI → Agent API → HTTP → MCP `:8001` | Deferred |
| **C — Cursor / IDE** | Cursor → MCP `:8001` directly | **In scope** |

**Plain English:** You talk in Cursor. Cursor’s MCP client calls `http://127.0.0.1:8001/mcp` (existing Bearer setup as-is). The LoanOps MCP server runs tools via `ModularToolsClient` against SSE OpenAPI hosts and EAKG.

You do **not** need Agent API `:8000` or `TOOLS_CLIENT__PROVIDER` for Flow C. Debug tips: `docs/DEBUG_LAYER2.md` Flow C; validation notes: `docs/MCP_CURSOR_VALIDATION.md` (if present); layman path: `docs/THREE_QUERY_FLOWS.md` Flow C.

**Assumption for this pass:** keep today’s MCP Bearer / role env as-is. No token redesign, no OIDC, no principal-header work until §8 auth items are un-parked.

---

## 2. Executive summary (Cursor → MCP)

**What works well for Cursor**

- Cursor and future IDE clients share one tool room (`:8001`) — matches north star D1.
- MCP server already enforces GET-only / no body on `call_sse_api`, plus optional capability bind.
- Full MCP tool menu (SSE + docs + EAKG discovery tools) is available to Cursor — richer than the UI agent’s hard-coded four-tool menu.
- Shared allow-list (`scopes.py`) and MCP audit events (`mcp.tool.call`).

**What matters most on this path (active)**

1. **Required — Read-only policy only in `execute_tool`.** Cursor always goes through MCP today, but `ModularToolsClient` / `invoke_sse_api` do not enforce GET-only themselves. Defense-in-depth at the execution core still worth doing (product rule: no mutating tool calls — not an auth redesign).
2. **Required — Hot-path cost on every Cursor tool call.** RDF shards merged from disk on search/bind/EAKG; semantic OpenAPI search can embed every operation serially on cold start inside the MCP process.
3. **Required — MCP server holds EAKG business logic.** EAKG tools in `server._execute_eakg_tool` instead of the modular client — harder to test and reuse; schemas duplicated with SSE docs.
4. **Required — Health / ops for `:8001`.** MCP `/health` is shallow; Settings rebuilds hurt operator confidence when Cursor tools break.
5. **Required — Docs/ADR drift** on capability-bind *product* flags, semantic search, Flow C as primary walkthrough (not identity/OIDC docs).

**Not the focus now (parked in §8):** UI chat/sidebar, **all PII**, **all auth/identity** (shared token, per-client tokens, JWT/OIDC, `MCP__ROLE` per caller, `x-loanops-*` / `MCP__PRINCIPAL_*`, Auth0), agent citations/menu, Flow B MCP client connect-per-call.

---

## 3. How Cursor → MCP works today

### 3.1 Hop-by-hop map (Flow C)

| Hop | Main code | What happens |
|-----|-----------|--------------|
| Cursor | `~/.cursor/mcp.json` (or project MCP config) | Points at `http://127.0.0.1:8001/mcp` + existing Bearer |
| MCP transport | `packages/mcp_server/server.py` | Streamable HTTP; tool wrappers → `_run` → `execute_tool` |
| Policy (read-only / bind) | `execute_tool`, `policy.py`, `capability_bind.py` | GET-only, optional bind — **auth token work deferred** |
| EAKG tools | `server._execute_eakg_tool` | Discovery tools — server-side today |
| Helpers | `build_modular_tools_client` → `ModularToolsClient.call` | SSE search/list/call, docs, etc. |
| SSE call | `packages/sse/tools.py` → `invoke_sse_api` | Live HTTP with `SSE__API_KEY` (no second method guard) |
| EAKG data | `data/eakg/` shards via merge/catalog helpers | Loaded/merged often per call (see R4) |

### 3.2 Picture (Flow C only)

```text
You (Cursor Chat)
        │
        │  Streamable HTTP MCP
        │  (existing Bearer — leave as-is for now)
        ▼
┌─────────────────────────────────────────┐
│  MCP Server :8001                       │
│  GET-only + bind (keep); auth redesign  │
│  deferred                               │
│  EAKG tools (today: in server)          │
│           │                             │
│           ▼                             │
│  ModularToolsClient.call                │
│           │                             │
│           ├─► search_sse_apis / list    │
│           ├─► call_sse_api → SSE hosts  │
│           └─► search_docs / …           │
└─────────────────────────────────────────┘
        │
        ▼
   SSE REST + EAKG shards + docs vector store
```

**Target for this focus:** make Cursor tools faster and clearer — defense-in-depth GET-only at the execution core, EAKG tools living with the rest of the helpers, cached catalogs/embeddings, real MCP readiness. Auth/identity and PII later. UI chat adopts the same room when un-parked.

---

## 4. Findings in detail (Cursor → MCP)

Severity:

- **Critical** — blocks treating MCP as a shared trusted tool room  
- **Required** — should fix while Cursor is the primary client  
- **Optional** — later  
- **Nit** — cleanup  

### 4.1 Critical (on Flow C)

*None in the active scope.*  
UI bypass findings (C1/C2) and shared-token / identity risks (**R2**) are parked in §8. Leave existing MCP Bearer setup unchanged for this pass.

---

### 4.2 Required (active)

#### R-policy. Defense-in-depth for read-only

Cursor always enters via `execute_tool`, so GET-only is enforced today. Gaps remain:

- `ModularToolsClient` / `invoke_sse_api` do not refuse non-GET themselves (test harness or mistaken direct call could mutate via `SSE__API_KEY`).
- Binding may not fully assert `path` matches the bound operation (**O4**).

**In scope now:** `ToolPolicy` on `ModularToolsClient.call` + fail-closed GET check in `invoke_sse_api` (product rule: no mutating tool calls in v1).

**Deferred with auth (§8.1):** tightening `require_capability_bind` / permission defaults as an authorization program; stripping or redesigning client identity headers.

#### R3c. EAKG and tool definitions concentrated in the MCP server

For Cursor, EAKG tools *are* available (unlike the UI agent menu). Cost: implementations and `@mcp.tool` schemas live in `server.py`, separate from SSE handler docs. Harder to unit-test without standing up MCP; risk of description drift.

**Decision:** Move EAKG handlers into `LoanOps.Tools` (same registry as SSE/docs). MCP server becomes thin wrappers: transport → `client.call`. One registry drives Cursor’s `tools/list` and future UI Flow B. *(“Thin” here means less business logic in the server — not an auth rewrite.)*

#### R4. EAKG / catalog reloaded from disk on every Cursor tool call

`search_sse_apis` (capability block), bind on `call_sse_api`, and EAKG tools repeatedly merge RDF shards. Latency grows with shard size — Cursor users feel this as slow tools.

**Decision:** Cached `CapabilityCatalogService` in Tools (mtime/commit keyed), shared by search, bind, and EAKG tools inside the MCP process.

#### R5. Semantic OpenAPI search cold-start in the MCP process

First `search_sse_apis` in a cold MCP process can embed every OpenAPI operation serially (remote embedding). Cache is process-local; refresh invalidation is weak; failures can be swallowed; empty scores fall back to arbitrary first-N ops.

**Decision:** Offline OpenAPI embedding sidecar; batch embed; invalidate on catalog refresh; fail clearly rather than silent keyword-looking garbage.

#### R7c. Resilience of tool execution (server-side)

Cursor owns the MCP client connection (not LoanOps’ `McpToolsClient`). Still on the server:

- SSE call timeout (~30s) with no retry for idempotent GET.
- Serial work inside a single tool if helpers do heavy sequential work.
- No circuit breaker when an SSE host is down — Cursor just sees tool errors.

**Decision:** Retry once for idempotent GET in `invoke_sse_api`; clear error messages; optional short-circuit when host health is known bad. (Do not assume Agent’s “reuse ClientSession” fix — that is Flow B.)

#### R8c. MCP health and settings

MCP `/health` mainly proves the modular client can be built, not that SSE hosts or EAKG shards are readable. `Settings()` may be rebuilt often inside helpers.

**Decision:** Cache `get_settings()`. Readiness: shards present, catalog loadable, optional lightweight SSE probe. Cursor operators need a one-line “MCP is ready” check.

#### R9c. ADRs / docs for the MCP tool room (non-auth)

Priority docs for this pass:

| Topic | Gap |
|-------|-----|
| Tool policy placement | Shared GET-only / no-body vs MCP-only |
| Semantic OpenAPI search | Behavior + cache ownership |
| ARCHITECTURE / THREE_QUERY_FLOWS | Flow C as primary walkthrough while UI is deferred |

*(Identity / OIDC / principal ADRs → §8.1. Capability-bind *authorization defaults* → §8.1.)*

#### R10c. Local vs cloud for the MCP process

MCP process needs embeddings for semantic search and may pull cloud defaults from settings/`.env`. Cursor demos that “need a cloud key to search OpenAPI” fight local-first.

**Decision:** Local-safe defaults for the MCP worker; document which env vars Cursor demos require for embeddings; keyword fallback must be explicit in tool output when embeddings are unavailable. *(Not about MCP Bearer auth.)*

---

### 4.3 Optional (still useful for Cursor)

| ID | Topic | Notes |
|----|--------|-------|
| **O1** | MCP image / deps | MCP pulls db/docs/wiki/sse/eakg via modular builder — heavy for “Cursor tools only” |
| **O2** | Scale-out | JSONL audit + per-process embed cache — fine for single local MCP; not multi-replica |
| **O3** | EAKG engineering join | False path matches; expensive joins — affects quality of EAKG tools Cursor uses |
| **O4** | Capability binding path assert | Bound op vs client `path` not always asserted (correctness, not token auth) |

### 4.4 Nits (MCP / tools)

- Clients import private `provider_contracts.tools_client._base`.
- `sse/tools.py` docstring wording mixes “MCP tool handlers” with plain handlers.
- Prefer clearer tool descriptions on `@mcp.tool` (those are what Cursor shows the model).

---

## 5. Anti-patterns (active scope)

| Anti-pattern | Where |
|--------------|--------|
| Policy only in the transport layer | GET-only in `execute_tool`, not in `invoke_sse_api` |
| Business logic in the server process | EAKG tools in `server.py` |
| Hot-path disk / embed work | Shard merge + serial op embedding on Cursor tool calls |
| Docs drifting from MCP reality | Semantic search, Flow C primacy, tool-policy placement |

*(“Shared secret = god mode” parked with auth — §8.1.)*

---

## 6. ADR gaps (active / Cursor-first)

1. [x] **Tool policy placement** — ADR-022 Proposed.  
2. [x] **Semantic OpenAPI search + catalog cache** — ADR-023 Proposed.  
3. **Graphify / engineering join as enterprise extractor** — still open (beyond ADR-012).

*(Auth identity, capability-bind authorization defaults, PII audit ADRs — parked in §8.)*

---

## 7. Recommended next five moves — DONE (2026-04-08)

1. [x] **Defense-in-depth read-only** — `packages/tools/policy.py` + `ModularToolsClient` + `invoke_sse_api`. (*R-policy*, ADR-022)  
2. [x] **EAKG in Tools** — `packages/tools/eakg_tools.py`; MCP = transport + dispatch. (*R3c*; full ToolRegistry later)  
3. [x] **Cached capability catalog** — `CapabilityCatalogService` fingerprint cache. (*R4*, ADR-023)  
4. [x] **OpenAPI embed sidecar** — `openapi_embeddings.json` + concurrent embed + CLI. (*R5*, ADR-023)  
5. [x] **MCP readiness** — `get_settings()`; `/health` liveness + `/ready` snapshot. (*R8c*)

**Docs:** ADR-022/023 Proposed; Flow C primary in `THREE_QUERY_FLOWS` / `DEBUG_LAYER2`.

**Nice follow-ons (still non-auth):** R7c GET retry; R10c local embedding defaults; O4 path assert on bind; full ToolRegistry.

---

## 8. Deferred — not now

Parked. Do not block current Cursor → MCP work on these.

### 8.1 Auth / identity (explicitly skipped)

| Former ID | Topic | Notes |
|-----------|--------|-------|
| **R2** | Shared `MCP__AUTH_TOKEN`; process-wide `MCP__ROLE`; per-client tokens; JWT/OIDC | Leave Bearer as-is |
| **R2 headers** | Spoofable `x-loanops-user` / `x-loanops-tenant` forward to SSE | |
| **R2 principals** | `MCP__PRINCIPAL_USER` / `MCP__PRINCIPAL_TENANT` ADR | |
| **Authz defaults** | Turning on `REQUIRE_CAPABILITY_BIND` / `ENFORCE_PERMISSIONS` as a program | Keep optional flags; no rollout push now |
| **C2** | Sidebar `/mcp/keys` + optional API key on Agent API | UI; also auth |
| **ADR-010 Auth0** | Human auth for `/chat` | UI |

### 8.2 PII / audit redaction (explicitly skipped)

| Former ID | Topic | Notes |
|-----------|--------|-------|
| **R1c** | PII in MCP audit (`mcp.tool.call` args/result snippets) | Redact via PII provider later |
| **R1 (UI)** | `audit/memory.md`, session store, agent audit summaries | `/chat` path |
| **ADR** | PII detokenization boundary (Flow B) / what MCP may persist | Write when PII work resumes |

### 8.3 UI chat / Agent API

| Former ID | Topic | Why deferred |
|-----------|--------|--------------|
| **C1 (UI angle)** | Modular path skips GET-only | Only hurts Flow A / non-MCP callers |
| **R3 (UI menu)** | `_SSE_ANSWER_TOOLS` four-tool menu | Agent Core, not Cursor |
| **R6** | `_fix_citations`, tool-as-user messages | Agent Core eval / grounding |
| **R7 (Flow B client)** | New HTTP + `initialize` per Agent tool call | `McpToolsClient` used by Agent, not Cursor |
| **R8 (Agent `/health`)** | Agent API readiness / `/chat` error leak | `:8000` |
| Parts of **R9/R10** | ADR-001 MAF loop, UI telemetry | UI stack |

When UI returns: Flow B should reuse the same hardened `:8001` room Cursor already uses — that is the north star.

---

## 9. Related reading

| Document | Why |
|----------|-----|
| `docs/THREE_QUERY_FLOWS.md` | Flow C layman path |
| `docs/DEBUG_LAYER2.md` | Flow C breakpoints (`C1`, `C2`, `S1`, `S2`) |
| `ARCHITECTURE.md` | Living architecture; north star D1 |
| `decisions.md` | ADRs (esp. MCP / EAKG) |
| `AGENTS.md` | Non-negotiable rules |
| `docs/MCP_CURSOR_VALIDATION.md` | Cursor validation notes (if present) |

---

## 10. Review method notes

- Original ECC review covered A/B/C; this document re-scoped to **Cursor → MCP**, then deferred **PII** and **auth/identity**.  
- Active work = tool structure, read-only defense-in-depth, speed, readiness.  
- Existing MCP Bearer / role env stays; do not block on token redesign.

---

*End of review document (Cursor → MCP; PII and auth deferred).*
