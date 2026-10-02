# MCP Cursor Validation

Phase **11** of the MCP + Capability KG + ARD plan. Goal: prove **Cursor** can use the same Streamable HTTP MCP endpoint already used by LoanOps (`McpToolsClient`), with **no Cursor-specific server code**.

Related: [`MCP_CLIENT_INTEGRATION.md`](MCP_CLIENT_INTEGRATION.md), [`MCP_SECURITY.md`](MCP_SECURITY.md), [`PHASE_STATUS.md`](PHASE_STATUS.md).

**Status:** Done — evidence recorded 2026-10-02 (Cursor MCP namespace `user-loanops` + Streamable HTTP).

---

## Goal

Validate Cursor against:

```text
http://127.0.0.1:8001/mcp
```

Same listener as Phase 5 (`packages/mcp_server`, FastMCP Streamable HTTP). Same auth, scopes, and tool surface as the in-repo MCP client.

---

## Prerequisites

| Requirement | Notes |
|---|---|
| MCP server running | `python -m packages.mcp_server` (or equivalent) listening on `:8001` |
| `MCP__AUTH_TOKEN` | Non-empty bearer shared with Cursor config |
| `MCP__ROLE` | `system` (includes `sse.read`, `docs.search`, `eakg.read`) |
| Network | Cursor host can reach `127.0.0.1:8001` (local Cursor Desktop) |

Secret values are not recorded in this doc.

---

## Cursor `mcp.json` snippet

Point Cursor at the remote Streamable HTTP URL and pass the bearer. Exact Cursor UI path may vary by version; the effective config is:

```json
{
  "mcpServers": {
    "loanops": {
      "url": "http://127.0.0.1:8001/mcp",
      "headers": {
        "Authorization": "Bearer <MCP__AUTH_TOKEN>"
      }
    }
  }
}
```

Replace `<MCP__AUTH_TOKEN>` with the same value loaded by the MCP server settings. Do not commit real tokens.

Configured on this machine: user `~/.cursor/mcp.json` entry `loanops` → Cursor namespace `user-loanops`.

---

## Checklist

### tools/list (role `system`)

Expect at least:

| Tool | Scope |
|---|---|
| `search_sse_apis` | `sse.read` |
| `list_sse_apis` | `sse.read` |
| `call_sse_api` | `sse.read` |
| `search_docs` | `docs.search` |

If the role includes `eakg.read` (default for `system`), also expect:

| Tool | Scope |
|---|---|
| `search_capabilities` | `eakg.read` |
| `explain_capability` | `eakg.read` |
| `find_providers` | `eakg.read` |
| `impact_of_change` | `eakg.read` |

### Positive smokes

| # | Action | Expect |
|---|---|---|
| P1 | `tools/list` with valid bearer | Lists SSE + docs tools; EAKG tools when `eakg.read` present |
| P2 | `search_sse_apis` with a simple query | Success; non-empty or structured empty result (no auth error) |
| P3 | `list_sse_apis` | Success |
| P4 | `call_sse_api` GET-style op (e.g. known read operation) | Success path or documented downstream HTTP; not MCP 401 |
| P5 | `search_docs` | Success or config-limited failure (not MCP auth failure) |
| P6 | `search_capabilities` / `explain_capability` (if EAKG tools listed) | Success or graph-empty result; not scope denial |

### Negative smokes

| # | Action | Expect |
|---|---|---|
| N1 | Connect / call with bad or missing bearer | Auth failure; tools not usable |
| N2 | `call_sse_api` with POST / non-GET mutation shape | Rejected by MCP GET-only guard (see [`MCP_SECURITY.md`](MCP_SECURITY.md)) |

---

## Evidence

| Date | Cursor version | Tester | P1–P6 | N1–N2 | Notes |
|---|---|---|---|---|---|
| 2026-10-02 | Cursor Desktop (this session) | agent | **PASS** | **PASS** | Via Cursor MCP `user-loanops` after `mcp_auth`. P1: 8 tools ready. P2/P3 OK. P4 `getLoanSummary` → downstream **HTTP 200**. P5 `search_docs` → config-limited (`docs not configured`, not auth). P6 `search_capabilities` OK after fixing `_READ_ONLY_TOOLS` to include EAKG. N1: bad bearer rejected (Streamable HTTP). N2: body + `method=POST` rejected. |

### Fix during validation

`packages/mcp_server/policy.py`: `_READ_ONLY_TOOLS` omitted EAKG tool names → listed tools failed at execute with scope denial. Added EAKG names; MCP tests green.

---

## Out of scope

- Forking or branching MCP server code for Cursor
- Lowering eval thresholds
- Recording bearer tokens or PII in evidence rows
