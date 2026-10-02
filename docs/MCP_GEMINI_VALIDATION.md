# MCP Gemini Validation

Phase **12** of the MCP + Capability KG + ARD plan. Goal: prove **Gemini** (or Gemini CLI / IDE MCP client) can use the **same** Streamable HTTP MCP endpoint as Cursor and LoanOps, with **no Gemini-specific server code**.

Related: [`MCP_CURSOR_VALIDATION.md`](MCP_CURSOR_VALIDATION.md) (Phase 11), [`MCP_CLIENT_INTEGRATION.md`](MCP_CLIENT_INTEGRATION.md), [`MCP_SECURITY.md`](MCP_SECURITY.md), [`PHASE_STATUS.md`](PHASE_STATUS.md).

**Status:** Todo — checklist ready; evidence not yet recorded.

---

## Goal

Validate Gemini against:

```text
http://127.0.0.1:8001/mcp
```

Identical listener, auth, scopes, and tools as Phase 11. Server remains client-agnostic.

---

## Prerequisites

Same as Phase 11:

| Requirement | Notes |
|---|---|
| MCP server running | Streamable HTTP on `:8001` |
| `MCP__AUTH_TOKEN` | Shared bearer |
| `MCP__ROLE` | `system` (includes `eakg.read`) |
| Reachability | Gemini client host can reach the MCP URL |

---

## Gemini client config

Gemini MCP custom-server wiring differs by product surface (CLI vs IDE vs API). Prefer the vendor’s documented “remote MCP” / custom server path.

**If unsure of the exact JSON/YAML shape for your Gemini build:** configure a remote MCP URL plus a Bearer authorization header, then run the same checklist as Phase 11 ([`MCP_CURSOR_VALIDATION.md`](MCP_CURSOR_VALIDATION.md)).

Conceptual equivalent:

```text
URL:     http://127.0.0.1:8001/mcp
Header:  Authorization: Bearer <MCP__AUTH_TOKEN>
```

Do not add Gemini-only branches in `packages/mcp_server`.

---

## Checklist

Match Phase 11. Summary:

### tools/list (role `system`)

- `search_sse_apis`, `list_sse_apis`, `call_sse_api`, `search_docs`
- Plus EAKG tools when `eakg.read` is present: `search_capabilities`, `explain_capability`, `find_providers`, `impact_of_change`

### Positive smokes

| # | Action | Expect |
|---|---|---|
| P1 | `tools/list` with valid bearer | Same tool set as Cursor / `system` role |
| P2 | `search_sse_apis` | Success (no MCP auth error) |
| P3 | `list_sse_apis` | Success |
| P4 | `call_sse_api` read/GET-style op | Usable; not MCP 401 |
| P5 | `search_docs` | Success or config-limited failure (not MCP auth) |
| P6 | EAKG tools (if listed) | Success or empty-graph result; not scope denial |

### Negative smokes

| # | Action | Expect |
|---|---|---|
| N1 | Bad / missing bearer | Auth failure |
| N2 | POST / non-GET via `call_sse_api` | Rejected by GET-only MCP guard |

---

## Compare to Phase 11

| Dimension | Phase 11 (Cursor) | Phase 12 (Gemini) |
|---|---|---|
| Endpoint | `http://127.0.0.1:8001/mcp` | Same |
| Auth | Bearer `MCP__AUTH_TOKEN` | Same |
| Server code | Unchanged | Unchanged |
| Tool checklist | Four SSE/docs + EAKG if scoped | Same |
| Client config | Cursor `mcp.json` | Gemini remote MCP URL + Bearer |
| Pass bar | Evidence table filled | Independent evidence table filled |

Differences should be **client config only**, not protocol or tool behavior.

---

## Evidence

| Date | Gemini client / version | Tester | P1–P6 | N1–N2 | Notes |
|---|---|---|---|---|---|
| TBD | TBD | TBD | TBD | TBD | Do not invent pass evidence |

---

## Out of scope

- Gemini-specific MCP server forks
- Treating Phase 11 Cursor pass as automatic Phase 12 pass
- Recording secrets or PII in evidence rows
