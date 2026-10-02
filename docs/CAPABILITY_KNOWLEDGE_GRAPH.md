# Capability Knowledge Graph

**Status:** Phase 2+ (RDFLib). Phase 1 documented intent only; implementation lives in `packages/capability_kg/`.

## Purpose

Represent **enterprise capabilities** independently of raw OpenAPI and of LoanOps code structure.

```text
OpenAPI (+ later source / docs / policies)
        ↓ offline build
RDF Capability Graph (Turtle)
        ↓ CapabilityCatalog
MCP / Agent discovery
        ↓ call_sse_api / invoke_sse_api
Real enterprise APIs
```

## Not this graph

| System | Role |
|---|---|
| Graphify (`graphify-out/`) | LoanOps engineering / code intelligence |
| Qdrant `docs` / `sops` | Policy RAG (`search_docs`) |
| OpenAPI catalog alone | Flat operation list (keyword search) |

## Stack

- **RDFLib** in-process
- Persist: Turtle (`data/capability_kg/capabilities.ttl`)
- Query: SPARQL via parameterized helpers (no raw user string concat into SPARQL)
- Swap path later: remote SPARQL store behind the same `CapabilityCatalog` API

## Ontology

See [`CAPABILITY_ONTOLOGY.md`](CAPABILITY_ONTOLOGY.md).

## Lifecycle (governance)

```text
discovered → enriched → pending_review → approved | rejected → (deprecated)
```

AI may discover/enrich; humans approve before publishing sensitive or write capabilities.
MCP should prefer `approved` / `published` capabilities when enforcement is enabled.

## Initial capabilities (from Loan Services catalog)

| Capability | OpenAPI operationId |
|---|---|
| `get_loan_summary` | `getLoanSummary` |
| `get_payment_schedules` | `getPaymentSchedules` |
| `get_escrow_details` | `getEscrows` |
| `get_borrower_summary` | `getBorrowerSummary` |
| `get_delinquencies` | `getDelinquencies` |

## Related docs

- [`CAPABILITY_ONTOLOGY.md`](CAPABILITY_ONTOLOGY.md)
- [`MCP_ARD_PHASE_MATRIX.md`](MCP_ARD_PHASE_MATRIX.md)
- ADR-012 / ADR-014 in `decisions.md`
