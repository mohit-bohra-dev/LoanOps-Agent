# Target Architecture

**Product goal:** Enterprise **capability discovery and execution** layer — not a generic MCP wrapper.  
**Clients:** Cursor, Gemini, LoanOps agent — same Streamable HTTP MCP.  
**Non-goals (Phase 1):** ARD dependency, CodeQL, tree-sitter, Graphify-as-capability-store.

Companion: [`ARCHITECTURE.md`](../ARCHITECTURE.md), [`PHASE_1_PLAN.md`](PHASE_1_PLAN.md).

---

## 1. North-star diagram

```text
Enterprise Repos
      ↓
Roslyn + OpenAPI (+ Docs/Tests later)
      ↓
Evidence
      ↓
Capability Extraction (candidates)
      ↓
Human Review
      ↓
RDF/RDFLib + SPARQL  →  Capability Catalog
      ↓
MCP Streamable HTTP  (authn / authz / scopes / validation / R-W / host allow / audit)
      ↓
Cursor / Gemini / LoanOps
      ↓
Existing API client (invoke_sse_api)
      ↓
Existing Enterprise APIs
```

**Parallel, separate:** Graphify = LoanOps **engineering** code KG only.

---

## 2. Responsibility matrix

| Concern | Owner | Not owner |
|---|---|---|
| .NET semantic analysis | **Roslyn** (`eakg-dotnet-extract`) | LLM, Graphify |
| API / operation discovery | **OpenAPI** parser + enrich | Graphify |
| Deep cross-language / security graph | **CodeQL** (later) | Phase 1 |
| Extra languages | **Tree-sitter** (later) | Phase 1 |
| LoanOps code intelligence | **Graphify** | Capability catalog / runtime |
| Business capabilities | **RDF / RDFLib + SPARQL** (EAKG shards) | Graphify, Qdrant docs |
| Runtime client interface | **MCP Streamable HTTP** | Custom `/mcp/tools` (UI adapter only) |
| Resource registry | **ARD** (later) | Phase 1 |
| Permission decisions | **Policy code** (scopes, allow-lists, capability ACL) | LLM |
| Execution | Existing **SSE HTTP client** | New HTTP stack inside MCP |

---

## 3. Capability model (canonical)

Capabilities are **business-facing**, evidence-backed, reviewable.

```text
GetLoanPaymentHistory
 ├─ belongsTo / hasDomain     → Loan Servicing
 ├─ implementedBy             → APIOperation (OpenAPI)
 ├─ implementedByCodeUnit     → PaymentsController.GetPayments
 ├─ mapsTo (httpMethod/Path)  → GET /loans/{id}/payments
 ├─ requiresPermission        → ViewLoanPayments (or loan.read)
 ├─ readOnly                  → true
 ├─ hasEvidence               → repo / commit / file / lines / detector
 └─ hasReviewStatus           → approved | …
```

Ontology: [`CAPABILITY_ONTOLOGY.md`](CAPABILITY_ONTOLOGY.md) (ADR-014/015).  
Store: EAKG shards + optional `catalog/approved.ttl` (D4).

### Lifecycle

```text
discovered → enriched → pending_review → approved | rejected → (deprecated)
```

- Structural extractors write **Evidence** (required for cross-app claims).
- LLM may propose semantic overlays only as **Proposal** → human gate.
- MCP prefers **approved** when `CAPABILITY_KG__APPROVED_ONLY=true`.

---

## 4. Analysis pipeline (source of truth)

```text
Roslyn + OpenAPI + Docs + Tests
              ↓
        Evidence Model
              ↓
      Capability Candidate
              ↓
        Human Review
              ↓
       Approved RDF Graph
```

**Rules**

1. Extractors emit facts + evidence; not free-form “capabilities” from chat.
2. Cross-app edges without evidence are **invalid** (drop at write).
3. Human review required before promoting sensitive / write / high-risk edges.
4. Graphify may **offline-enrich** LoanOps-side docs later (Phase 10) — never replace EAKG.

---

## 5. Runtime flow (client-independent)

```text
Client (Cursor | Gemini | LoanOps McpToolsClient)
  ↓
MCP Streamable HTTP  (:8001/mcp)
  ↓ authn (Bearer) + role scopes
Capability Search
  (search_capabilities / search_sse_apis KG block)
  ↓
RDF/SPARQL + optional semantic retrieval + permission filters
  ↓
Capability (approved / allowed)
  ↓ resolve operation_id + method + path template
OpenAPI operation
  ↓ MCP policy: readOnly / GET / no body / host allow-list / requiresPermission
Existing API client (invoke_sse_api)
  ↓ SSE__API_KEY (service M2M today; OBO later)
Enterprise API
```

### MCP security (must stay server-side)

| Control | Behavior |
|---|---|
| Authentication | Non-empty `MCP__AUTH_TOKEN`; empty → reject all |
| Authorization / scopes | `scopes.py` + `MCP__ROLE`; tool allow-list |
| Input validation | Tool JSON schema + path params in invoke |
| Read/write classification | Capability `readOnly` + MCP GET-only for `call_sse_api` |
| Host allow-listing | `assert_allowed_url` — no model-supplied absolute URLs |
| Auditing | `mcp.tool.call` (redacted args, status, latency, principal headers) |
| Permissions | Enforce `requiresPermission` from catalog before invoke (**target**) |

**Never** ask the model whether a call is allowed.

### Tool surface (keep small)

| Tool | Role |
|---|---|
| `search_capabilities` / `explain_capability` / `find_providers` / `impact_of_change` | Discovery (EAKG) |
| `search_sse_apis` / `list_sse_apis` | OpenAPI fallback + KG block |
| `call_sse_api` | Execute bound GET ops |
| `search_docs` | Policy RAG — **not** capability discovery |

Do **not** generate one MCP tool per OpenAPI operation in Phase 1.

---

## 6. Two graphs forever

| Graph | Content | Runtime? |
|---|---|---|
| Graphify (`graphify-out/`) | LoanOps-Agent code/docs | No |
| EAKG / Capability RDF (`data/eakg/`) | Enterprise apps, ops, capabilities, permissions, evidence | Yes (via catalog/MCP) |

Mixing them collapses engineering noise into business discovery.

---

## 7. LoanOps placement

```text
Care-rep UI → Agent API /chat
                 ↓ TOOLS_CLIENT__PROVIDER=mcp
              McpToolsClient → same :8001/mcp as Cursor
```

`modular` remains **demo/rollback** only — not the long-term product path (D1 / ADR-013).

---

## 8. Explicit later layers

| Layer | When |
|---|---|
| CodeQL | After Phase-1 governance/permissions stable |
| Tree-sitter | When non-.NET repos onboard |
| ARD | After multi-client MCP validation (Cursor ✓, Gemini TBD) |
| Full OBO / per-rep RBAC | After M2M path proven in production use |
| Review Web UI | When CLI insufficient for reviewers (D8) |
| Graphify → RDF enrichment | Offline Phase 10 |

---

## 9. Success definition

System succeeds when a **client-agnostic** MCP caller can:

1. Discover an **approved** capability by intent (SPARQL ± semantic).
2. See provenance (evidence) and permissions.
3. Invoke **only** the mapped read operation through existing enterprise APIs.
4. Fail closed on auth, scope, permission, write, or host violations — without trusting the LLM.
