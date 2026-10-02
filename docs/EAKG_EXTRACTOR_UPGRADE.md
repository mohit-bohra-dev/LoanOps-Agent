# EAKG .NET extractor upgrade (deferred)

**Status:** Design only. Current extractor: static regex in
`packages/eakg/extractors/dotnet.py` (ADR-018). Do **not** replace until pilot
questions stay green on regex baseline.

## Why upgrade later

| Gap | Regex today | Better tool |
|---|---|---|
| Method after many attributes | Widened window (1200 chars) — fragile | Roslyn / tree-sitter C# AST |
| Partial classes / nested types | Missed or duplicate | Roslyn |
| Route tokens `[controller]` | Heuristic | Framework-aware Roslyn analyzer |
| Generated Minimal APIs | Mostly skipped | Specialized walker |

## Options (pick one when circling back)

1. **tree-sitter-c-sharp** — portable, no `dotnet` SDK on indexer; good for CI Linux runners.
2. **Roslyn** (`Microsoft.CodeAnalysis.CSharp`) via a small `dotnet` tool — highest fidelity; requires SDK on runners.
3. **Keep regex + OpenAPI hybrid** — enough if teams ship `openapi.json` ([EAKG_SWAGGER_EXPORT.md](EAKG_SWAGGER_EXPORT.md)).

## Acceptance if upgraded

- Same `ApiOperationFact` / evidence model (no ontology break)
- Fixture tests in `packages/eakg/tests` stay green
- Real pilot: GetLoanSummary + PaymentSchedules still found
- Detector versions bumped; shards re-indexed once

## Non-goals

- SonarQube as KG source of truth
- LLM-written edges from source text
