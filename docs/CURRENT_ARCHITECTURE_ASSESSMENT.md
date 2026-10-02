# Current Architecture Assessment

**Branch:** `vdd`  
**Assessed:** 2026-10-02  
**Sources:** live code + ADRs + `docs/FLOWS.md` / `PHASE_STATUS.md` / `STACK_LAYER_DECISIONS.md` / `MCP_SECURITY.md`; git copy of deleted `docs/CURRENT_ARCHITECTURE.md` (stale in §15)

**Constraint:** Do not rewrite working functionality. This assessment maps what exists vs the enterprise capability discovery + MCP target.

---

## 1. Verdict

LoanOps already has the **spine** of the requested architecture:

```text
Enterprise repos → Roslyn + OpenAPI → Evidence → EAKG RDF shards
  → human review CLI → CapabilityCatalog (SPARQL + optional vectors)
  → MCP Streamable HTTP → Cursor / agent → invoke_sse_api → enterprise APIs
```

Graphify stays **separate** (LoanOps engineering KG only). ARD is correctly **not** a Phase-1 dependency.

What remains is **not** greenfield MCP/RDF. Gaps are: capability-first invoke path, permission enforcement at the edge, governance defaults, evidence completeness (docs/tests), and later CodeQL / multi-language / ARD.

---

## 2. Note on `CURRENT_ARCHITECTURE.md`

| Fact | Detail |
|---|---|
| Disk | **Deleted** in working tree (`git status`: `deleted: docs/CURRENT_ARCHITECTURE.md`) |
| Git | Still at `HEAD`; analyzed older HEAD `8235e90` |
| Stale claims | §15 says “No MCP server class…” — **false today** (`packages/mcp_server`, ADR-011) |
| Still useful | Runtime chat/SSE/safety/RAG/eval descriptions; “what must remain unchanged” list |
| Living docs | Prefer `ARCHITECTURE.md`, `docs/FLOWS.md`, `docs/PHASE_STATUS.md`, `docs/STACK_LAYER_DECISIONS.md` |

Treat the deleted file as a **historical snapshot**, not current truth.

---

## 3. Layer-by-layer scorecard

| Layer (target) | Status | Evidence in repo | Gap |
|---|---|---|---|
| **Roslyn** (.NET semantic) | **Done (primary)** | `tools/eakg-dotnet-extract`, `packages/eakg/extractors/roslyn.py`, `EAKG__EXTRACTOR=auto`, ADR-018 | Regex still fallback for packages/appsettings/proxy patterns |
| **OpenAPI** | **Done** | `packages/sse` catalog + `packages/eakg/openapi_enrich.py` + legacy `capability_kg/extract_openapi.py` | Live swagger CI export still ops ask (`EAKG_SWAGGER_EXPORT.md`) |
| **Evidence model** | **Done** | `packages/eakg/models.Evidence`, `ApiOperationFact`, detectors write provenance | Docs/tests as first-class evidence sources thin |
| **Capability candidates** | **Partial** | Structural extract → shards; proposals JSONL for review | Naming/shape vs product “GetLoanPaymentHistory” capability IDs not fully productized |
| **Human review** | **Partial** | `packages/eakg/review.py`, `review --pilot`, `publish` → `approved.ttl` (D8 CLI) | Web UI missing; `APPROVED_ONLY` default **false** (D3) |
| **RDF / RDFLib + SPARQL** | **Done** | `packages/capability_kg`, EAKG shards under `data/eakg` (local), ontology ADR-014/015 | Product discovery = **EAKG only** (D4); single-TTL seed retired |
| **Capability Catalog** | **Done** | `CapabilityCatalog` facade; EAKG merge; MCP tools + optional block in `search_sse_apis` | Invoke still keyed by OpenAPI `operation_id`, not capability id |
| **Semantic retrieval** | **Done (optional)** | Phase 9: embeddings + SPARQL filters (`CAPABILITY_KG__SEMANTIC`) | Off unless configured |
| **MCP Streamable HTTP** | **Done** | FastMCP `:8001/mcp`, ADR-011/013 | Client-independent ✓ |
| **Cursor → MCP** | **Done** | `MCP_CURSOR_VALIDATION.md` (2026-10-02) | Gemini validation still open |
| **Agent → MCP** | **Done (flag)** | `TOOLS_CLIENT__PROVIDER=mcp`; demo hop proven | Default can still be modular for local demo; eval golden via MCP hop pending |
| **AuthN / AuthZ / audit** | **Partial** | Bearer, scopes, GET-only, host allow-list, audit, principal headers | No OBO; **`requiresPermission` not enforced at invoke**; LLM never decides authz (good) |
| **Graphify** | **Separate ✓** | `graphify-out/` — LoanOps only | Phase 10 offline enrichment still parked |
| **CodeQL** | **Later ✓** | Not started | Correctly parked |
| **Tree-sitter** | **Later ✓** | Not Phase-1 | Correctly parked |
| **ARD** | **Later ✓** | Draft only | After Cursor/Gemini |

---

## 4. What already matches the target diagrams

### Analysis pipeline (mostly live)

```text
Roslyn + OpenAPI (+ detectors)
        ↓
  Evidence / ApiOperationFact
        ↓
  EAKG repo shards + cross_app.ttl
        ↓
  review CLI (pending → approved|rejected)
        ↓
  approved.ttl (optional publish)
        ↓
  CapabilityCatalog → MCP tools
```

LLM is **not** source of truth for structural facts. Proposals/enrichment stay review-gated (ADR-015).

### Runtime (live, with nuance)

```text
Cursor / Gemini / McpToolsClient
  ↓ Streamable HTTP + Bearer
MCP :8001
  ↓ search_capabilities | search_sse_apis
RDF/SPARQL (+ optional semantic)  OR  OpenAPI keyword
  ↓
call_sse_api(operation_id)   ← still OpenAPI-centric execute
  ↓ host allow-list + GET-only (MCP edge)
invoke_sse_api → enterprise API (SSE__API_KEY = Subservicing M2M)
```

**Nuance:** Discovery can be capability/RDF-first. **Execution** still resolves OpenAPI ops via `call_sse_api`. That is correct for not exploding one MCP tool per op — but the product story “Capability → OpenAPI operation → client” needs an explicit capability-id → operation binding at invoke time (metadata already on RDF; enforcement incomplete).

### Capability example vs ontology

Target shape:

```text
GetLoanPaymentHistory
 ├─ belongsTo → Loan Servicing
 ├─ implementedBy → PaymentsController.GetPayments
 ├─ mapsTo → GET /loans/{id}/payments
 ├─ requiresPermission → ViewLoanPayments
 └─ readOnly → true
```

Ontology already models: `hasDomain`, `implementedBy` (APIOperation), `implementedByCodeUnit`, `httpMethod`/`httpPath`, `requiresPermission`, `readOnly`, Evidence. Roslyn extracts controller/action + authz into facts. **Gap:** consistent published capability ids + code-unit edges in approved catalog + permission check at MCP before invoke.

---

## 5. What must not be rewritten

Preserve (also in `PHASE_STATUS.md` / ADR-013):

| Keep | Why |
|---|---|
| `packages/mcp_server` Streamable HTTP | Working client-independent MCP |
| `invoke_sse_api` + host allow-list | Real enterprise execution |
| `ModularToolsClient` as server-side executor | Single dispatch; agent/Cursor share it |
| Graphify outside runtime / outside capability store | ADR-012 |
| `search_docs` / RAG separate from capability discovery | Avoid SOP≠API confusion |
| Four (+ EAKG) tool surface | Avoid per-op MCP tool explosion |
| Custom `/mcp/tools` JSON for UI sidebar | Not protocol MCP; fine as adapter |
| Eval thresholds | Never lower |
| Roslyn primary + regex fallback | D5 shipping |
| EAKG shards as product discovery source | D4 |

---

## 6. Stale / conflicting signals to ignore when planning Phase 1

1. `CURRENT_ARCHITECTURE.md` §15–22 “build MCP from scratch” — **already shipped**.
2. Greenfield order “1… build Roslyn + OpenAPI… 5… add MCP…” — treat as **maturity checklist**, not build sequence.
3. ADR-014 single-TTL as product path — **superseded by D4 / EAKG**.
4. Graphify as enterprise capability registry — **forbidden**.

---

## 7. Residual risk (honest)

| Risk | Severity | Mitigation direction |
|---|---|---|
| Model invents `operation_id` / path | High | Prefer `search_capabilities` → bind only published `operation_id`; reject unbound invoke |
| `requiresPermission` metadata unused | High | Enforce at MCP before `call_sse_api` / capability invoke |
| Shared M2M token (D7) | Medium (accepted) | Document; OBO later — not Phase-1 blocker |
| Shards machine-local not in git | Medium | Ops: onboard/sync; see `EAKG_COMMITTED_VS_LOCAL.md` |
| `APPROVED_ONLY=false` | Medium | Turn on when review process owned |
| Modular bypass of MCP GET-only | Medium | Product path = MCP; modular = demo/rollback only |
| Doc sprawl / deleted CURRENT_ARCHITECTURE | Low | This assessment + TARGET + PHASE_1 replace it for planning |

---

## 8. Bottom line

**Enterprise capability discovery + execution layer is underway and largely wired.**  
Phase 1 must **harden and close the loop** (capability-bound invoke, permissions, governance), not rebuild Roslyn/RDF/MCP.
