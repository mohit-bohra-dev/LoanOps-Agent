# GraphRAG — should LoanOps add it?

**Date:** 2026-10-09
**Status:** Deferred. Do not add GraphRAG now. Recorded as ADR-025.
**Reviews:** architect (fresh context) and an adversarial review (`doubt-driven-development`). Both reached the same verdict independently.

## Verdict

Do not add GraphRAG (LLM entity/relation extraction over SOP docs, community clustering, community summaries, graph-aware retrieval at query time).

The SOP corpus is too small, citations would break, and the graph questions this platform actually has are already answered by EAKG. Do a narrower retrieval upgrade first. Revisit GraphRAG only when the triggers below are met.

## What GraphRAG means here

Graph-structured retrieval-augmented generation: at index time an LLM extracts entities and relations from documents, clusters them into communities, and summarizes each community. At query time retrieval walks that graph (and optionally vectors) instead of only nearest-neighbour chunk search.

LoanOps does **not** implement this. Related pieces that are not GraphRAG:

| Piece | What it is |
|---|---|
| Docs RAG (`LoanOps.Rag`, `search_docs`) | Chunk markdown, embed, flat vector search. No rerank, top_k 5. |
| EAKG (`LoanOps.Eakg`, `LoanOps.CapabilityKg`) | RDF capability graph for API/capability discovery (`search_capabilities`, `explain_capability`, `find_providers`, `impact_of_change`). |
| ApiIndex + pgvector | Flat vectors of callable API operations for `search_sse_apis`. |
| Graphify (`graphify-out/`) | Offline code graph for agents. Not request-time. |

## Evidence

| Claim | Proof |
|---|---|
| SOP corpus is 60 markdown files, ~339 KB | `data/sops/` measured 2026-10-09 |
| Chunks are ~600 words with 80 overlap, header-aware | `projects/LoanOps.Rag/packages/rag/chunker.py`; `ARCHITECTURE.md` §11 |
| Docs search is embed + top_k 5, no reranker | `projects/LoanOps.Docs/packages/docs/service.py` |
| A reranker provider exists and is not called by `search_docs` | `get_reranker_provider()` in `packages/common/providers/factory.py` |
| Golden set is ~50 items; no global "summarize everything" questions | `data/golden.jsonl` |
| Cross-app multi-hop and impact are already EAKG tools | `projects/LoanOps.Tools/packages/tools/eakg_tools.py` |
| Policy RAG and the capability catalog must stay separate | `ARCHITECTURE.md` §11 |
| Factual answers need a `policy:` or `tool:` citation; eval citation coverage is 1.0 | `AGENTS.md`; `ARCHITECTURE.md` §13 |
| LoanOps consumes docs; it does not author a wiki | `docs/PLAISSE_WIKI_VS_LOANOPS.md` |

The architect review counted 38 SOP files. The measured count is 60 files / ~339 KB. Either number is an order of magnitude below a GraphRAG corpus.

## What GraphRAG would and would not fix

**Would fix in theory:** global questions ("summarise all hardship options across states") and multi-hop reasoning across policy docs. Neither appears in the golden set, and the SOPs barely cross-link.

**Already covered by EAKG:** which apps provide a capability, cross-app dependencies, impact of a change, joining operations to capabilities.

**Would make worse:**

- **Citations.** Community summaries are not source text. They have no `policy:` path, so they fail the citation rule and the citation-coverage gate of 1.0.
- **Extraction quality.** Entity extraction on local Llama 3.1 8B is noisy. Hallucinated edges become retrieval.
- **Eval determinism.** LLM extraction varies between index runs, so eval scores move without a product change.
- **Staleness.** Every SOP edit needs re-extraction.
- **PII.** Extracted entities can land in a new store.
- **Provider rules.** A graph store is a new external capability: new Provider Protocol plus human approval, plus index-time LLM cost on AWS.

## Do this instead

1. **Wire the existing reranker into `DocsService.search` (small).** Retrieve ~20 candidates, cross-encode, keep 5. Uses `get_reranker_provider()` as-is. No new env var, no new provider.
2. **Hybrid keyword + vector for docs, plus deterministic metadata (small to medium).** Same two-stage shape as ApiIndex. Tag each chunk with category, state, and heading path from the file path and front-matter. No LLM. Helps joins like "FL + disaster".
3. **Deterministic doc-link graph (medium).** Edges from markdown links, shared category, state overlays, and SOP → EAKG capability ids. Expand one hop from the top hit and return the neighbour as its own citable chunk. Provenance stays verbatim. Checked-in artifact, not Graphify, not request-time GraphRAG.

Sketch that stays inside the provider rules:

1. Inject the reranker into `DocsService` via the factory. `candidate_k` as a constructor argument, not a new env var. Test with the in-memory provider.
2. Extend chunk metadata with `category`, `state`, `heading_path` parsed from path and front-matter.
3. Offline builder in `LoanOps.Rag` writes `doc_links.json` (markdown links, state overlays, SOP → capability id). Not a runtime store.
4. Search: top hits, one-hop expand, rerank, each chunk keeps a `policy:` path.
5. Add golden items for multi-policy joins. Do not lower eval thresholds.

Before new golden items: some items name a `search_policy` tool; the agent path in `ARCHITECTURE.md` §11 is `search_docs`. Resolve that mismatch first.

## When GraphRAG becomes justified

Any **two** of:

- Corpus passes ~2,000 docs or ~20k chunks (for example Confluence via `DATA__SOP_*`).
- A golden slice of 20+ global or multi-policy questions still fails faithfulness ≥ 0.85 **after** the three alternatives above ship.
- The new source is dense, interlinked narrative (runbooks, incident postmortems), not short procedural SOPs.
- Summaries can be stored with chunk-level provenance and cited back to source chunks, and the extraction model is pinned so eval stays reproducible.

## Reviews

- Architect review, 2026-10-09: do not add; narrower retrieval upgrade; triggers as above.
- Adversarial review (`doubt-driven-development`), 2026-10-09: 3 blockers (citation coverage, no graph-store protocol, non-deterministic 8B extraction), 3 major, 1 minor. Same direction: reranker already exists and is unwired; corpus too small; EAKG is the graph layer for this domain.
