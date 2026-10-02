# ARD Resource Choice (decision draft)

Phase **14** decision draft: which MCP resources ARD (Agent Resource Discovery) should expose to agents.

Related: [`ARD_INTEGRATION.md`](ARD_INTEGRATION.md), [`PHASE_STATUS.md`](PHASE_STATUS.md), multi-client validation [`MCP_CURSOR_VALIDATION.md`](MCP_CURSOR_VALIDATION.md) / [`MCP_GEMINI_VALIDATION.md`](MCP_GEMINI_VALIDATION.md).

**Status:** **Proposed** — not implemented. Depends on Phases **11** and **12** going green (Cursor + Gemini against the same Streamable HTTP MCP).

---

## Decision question

> Which MCP resource(s) should ARD advertise, and with what metadata, so an agent can choose *where* to connect before discovering *what* capabilities exist inside a server?

ARD answers **which server / resource**, not **what capability** (that remains RDF / Capability Catalog / EAKG inside the chosen MCP).

---

## Candidates

| Candidate | Today | Notes |
|---|---|---|
| **LoanOps MCP** (this project) | Streamable HTTP at `:8001` (`http://127.0.0.1:8001/mcp` in local/dev) | Primary candidate; SSE tools, docs search, EAKG tools under scopes |
| **Customer MCP** | Future | Customer-facing or CRM-shaped tools; separate ownership |
| **Docs MCP** | Future | Doc/RAG-focused surface; may overlap `search_docs` on LoanOps MCP |

Do not invent additional live endpoints here. Future rows stay speculative until owned and standing.

---

## Selection criteria

| Criterion | What to decide |
|---|---|
| **URL** | Stable base URL / path (env-specific; not hard-coded secrets) |
| **Auth** | Bearer today (`MCP__AUTH_TOKEN`); future mTLS / OAuth called out in [`MCP_SECURITY.md`](MCP_SECURITY.md) |
| **Scopes** | Which scope sets the resource grants (`sse.read`, `docs.search`, `eakg.read`, …) |
| **Ownership** | Team that operates the server and rotates credentials |
| **Governance** | Review / `approved_only` expectations; whether ARD may list unreviewed resources |

---

## Metadata schema draft

Proposed resource descriptor (JSON-shaped; schema not finalized):

```json
{
  "id": "loanops-mcp",
  "baseUrl": "http://127.0.0.1:8001/mcp",
  "authType": "bearer",
  "scopes": ["sse.read", "docs.search", "eakg.read"],
  "capabilitiesSummary": "SSE OpenAPI tools, docs search, enterprise capability graph queries"
}
```

| Field | Intent |
|---|---|
| `id` | Stable ARD resource id |
| `baseUrl` | Streamable HTTP MCP entry URL |
| `authType` | How clients authenticate (`bearer`, later `mtls`, `oauth`, …) |
| `scopes` | Declared scope labels (align with `packages/common/scopes.py`) |
| `capabilitiesSummary` | Human/agent short blurb; not a substitute for live `tools/list` |

---

## Dependencies

1. Phase 11 Cursor validation green — [`MCP_CURSOR_VALIDATION.md`](MCP_CURSOR_VALIDATION.md)
2. Phase 12 Gemini validation green — [`MCP_GEMINI_VALIDATION.md`](MCP_GEMINI_VALIDATION.md)
3. Clear enough auth/scope story — [`MCP_SECURITY.md`](MCP_SECURITY.md)

Until then: keep ARD **out of the runtime path**. See [`ARD_INTEGRATION.md`](ARD_INTEGRATION.md).

---

## Non-goals (this draft)

- Implementing an ARD service or registry API
- Replacing Capability KG / EAKG query tools
- Choosing production URLs or tenants without owners
