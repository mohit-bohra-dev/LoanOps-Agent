# Stack layer decisions

Canonical technology choices for the MCP + EAKG capability platform.  
Recorded 2026-10-02. Cross-links: [`DECIDE_AND_CLEANUP.md`](DECIDE_AND_CLEANUP.md) (D5), [`EAKG_EXTRACTOR_UPGRADE.md`](EAKG_EXTRACTOR_UPGRADE.md), ADR-014..019 in [`decisions.md`](../decisions.md).

## Decision matrix

| Layer | Recommendation | Decision | In LoanOps-Agent today |
|---|---|---|---|
| **Source-code analysis (.NET)** | **Roslyn** | ✅ Primary | ✅ **Shipping:** `tools/eakg-dotnet-extract` + `EAKG__EXTRACTOR=auto` (Roslyn then regex). Detector `dotnet_roslyn` v2. |
| **API analysis** | **OpenAPI parser** | ✅ Primary | ✅ `packages/eakg/openapi_enrich.py` + `packages/sse` OpenAPI catalog |
| **Cross-language / deep analysis** | **CodeQL** | 🟡 Phase 2 | ❌ Not started |
| **Generic parsing** | **Tree-sitter** | 🟡 Phase 2 | ❌ Optional later (was ADR-018 alt); not Phase 1 |
| **Engineering / code graph** | **Graphify** | 🟡 Reuse existing | ✅ `graphify-out/` — LoanOps code intelligence only; **not** enterprise capability registry |
| **Capability graph** | **RDF + RDFLib** | ✅ Primary | ✅ `packages/capability_kg` + `packages/eakg` shards (EAKG = truth, D4) |
| **Graph querying** | **SPARQL** | ✅ Primary | ✅ Behind `CapabilityCatalog` / EAKG query helpers |
| **Semantic capability search** | **Vector + metadata filtering** | ✅ Primary | ✅ Phase 9 optional (`CAPABILITY_KG__SEMANTIC`); keyword/SPARQL filters always |
| **Capability governance** | **Human review + provenance** | ✅ Required | ✅ Evidence nodes + `review --pilot` + `approved.ttl` (**D8:** CLI live; Web UI also planned) |
| **Capability interface** | **MCP Streamable HTTP** | ✅ Primary | ✅ `packages/mcp_server` `:8001/mcp`; agent = first-party consumer (D1-B) |
| **Resource discovery** | **ARD** | 🟡 Later | 📄 Draft [`ARD_RESOURCE_CHOICE.md`](ARD_RESOURCE_CHOICE.md); after Cursor/Gemini validation |
| **Pipeline orchestration / analysis harness** | **Harness** | 🟡 Optional | 🟡 Sync CLI + `ci/eakg.gitlab-ci.yml` / scripts; no full “Harness” product yet |
| **Existing RAG** | **Keep** | ✅ Reuse | ✅ `search_docs` / Qdrant path — separate from capability discovery |
| **Existing API execution** | **Keep** | ✅ Reuse | ✅ `invoke_sse_api` behind MCP `call_sse_api` |

## How layers fit together

```text
Roslyn (target) / regex (now)  ──►  per-repo EAKG shards (RDF)
OpenAPI parser                 ──►  enrich operations
Detectors + Evidence           ──►  cross_app.ttl → human review
                                    │
                                    ▼
                         CapabilityCatalog (SPARQL + optional vectors)
                                    │
                                    ▼
                         MCP Streamable HTTP  ◄── Agent / Cursor / Gemini
                                    │
                                    ▼
                         invoke_sse_api  +  search_docs (RAG)
```

Graphify stays beside this stack for **LoanOps repo** understanding, not as the enterprise capability store.

## Implications

1. **D5 updated:** Roslyn is the **primary** .NET analysis decision; regex is transitional until Roslyn extractor ships.
2. **Do not** make Tree-sitter or CodeQL Phase 1 blockers.
3. **Do not** replace RDFLib with Graphify for capabilities.
4. ARD waits until MCP multi-client validation (Phases 11–12).

Update this table when a Phase 2 item starts or Roslyn replaces regex.
