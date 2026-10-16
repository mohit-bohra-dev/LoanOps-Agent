---
name: doc-graphrag
overview: Fix citation grounding and eval measurement, baseline flat search, ship deterministic rerank+link-hop upgrades, then kill-gate any GraphRAG (summary routing first, LLM extraction last) behind proven need.
todos:
  - id: p1-approval-metric
    content: "Obtain approval to add citation_groundedness gate at 1.0 (new metric; do not lower existing thresholds); record outcome in Notes"
    status: completed
  - id: p1-ground-citations
    content: "Implement ground_citations after _fix_citations; wire recorded_tools; unit tests for keep/drop/snippet/tool-prefix"
    status: completed
  - id: p1-tool-names
    content: "Replace _TOOL_NAMES with live tool registry; rewrite golden search_policy→search_docs; update validate_data.valid_tools"
    status: completed
  - id: p1-faithfulness-contexts
    content: "Build Ragas faithfulness contexts from tool/search results not citation snippets; thread tool payloads on EvalItemResult if needed"
    status: completed
  - id: p1-path-metadata
    content: "Normalise path to corpus-relative POSIX; freeze metadata keys category/state/heading_path; cross-root chunk-id stability test"
    status: completed
  - id: p1-vector-target
    content: "Consolidate ingest_sops onto docs namespace / DocsService; remove or redirect dead sops collection path"
    status: completed
  - id: p1-global-slice
    content: "Author ≥20 global/multi-policy golden items (golden_global.jsonl or equivalent) with must_cite policy paths"
    status: completed
  - id: p2-baseline-eval
    content: "Run eval on flat search with new metrics; record faithfulness, groundedness, citation_coverage, latency p95 in logs.md"
    status: completed
  - id: p3-reranker
    content: "Inject get_reranker_provider into DocsService with candidate_k ctor arg (default 20); tests with mock reranker"
    status: completed
  - id: p3-doc-links
    content: "Offline builder for data/docs/doc_links.json (markdown links, category, state); DocLinkGraph.neighbors sorted"
    status: completed
  - id: p3-one-hop
    content: "One-hop expand in DocsService.search; neighbours remain separately citable chunks; re-eval vs P2"
    status: completed
  - id: p3-kill-gate
    content: "Kill gate: if global slice faithfulness≥0.85 and groundedness≥1.0 after P3, STOP and record ADR-025 upheld; else authorize P4"
    status: completed
  - id: p4-approval-graphrag
    content: "If kill gate failed: obtain approval for LoanOps.GraphRag project and any GRAPHRAG__* env vars; record in Notes"
    status: completed
  - id: p4-communities
    content: "Louvain partitions (seeded) over deterministic doc_links; community records with member_chunk_ids; embed to graphrag_summaries"
    status: completed
  - id: p4-service-wrap
    content: "GraphRagService wraps DocsService same search() signature; pure select_route; no mode on tool schema; factory inject"
    status: completed
  - id: p4-fallback
    content: "Missing/corrupt/stale artifact → DocsService only; health flag; re-measure slice (gate2)"
    status: completed
  - id: p5-approval-extract
    content: "If gate2 shows summary routing helps: approve index-time LLM cost and artifact commit policy; else STOP"
    status: completed
  - id: p5-extract-cache
    content: "Pinned process LLM__* extract with cache key; grounding filter; PII allowlist; gap ledger shape (no eakg import)"
    status: completed
  - id: p5-artifact
    content: "Write data/graphrag graph/communities/manifest; refuse Confluence→repo; CI corpus_hash; twin-checkout determinism test"
    status: completed
  - id: p6-adr-docs
    content: "After human approval, append ADR-030 to decisions.md from ADR-030.draft.md; update ARCHITECTURE §11/§13 and GRAPHRAG_REVIEW.md"
    status: pending
isProject: false
---

# doc-graphrag - Implementation Plan

## Status

| Field | Value |
|-------|-------|
| **Status** | Draft |
| **Version** | 0.1.0 |
| **Created** | 2026-10-15 |
| **User Stories** | [doc-graphrag.story.md](./doc-graphrag.story.md) |
| **Technical Spec** | [doc-graphrag.spec.md](./doc-graphrag.spec.md) |
| **ADR draft** | [ADR-030.draft.md](./ADR-030.draft.md) |

---

## How to Use This Plan

1. **Todos (YAML frontmatter)** — track progress (`pending` | `in_progress` | `completed`). IDs use `p{N}-{slug}`.
2. **Markdown body** — how to execute each phase.

**Hard rule:** Do not start `p4-*` until `p3-kill-gate` completes with an explicit fail authorization. Do not start `p5-*` until `p4-fallback` gate2 says extraction is warranted.

---

## Technology Stack

### Core Dependencies

- Existing: embedding, vector store, chat, PII, reranker (`sentence-transformers`), eval/Ragas
- Conditional P4+: `networkx` (declare direct if importing), new `loanops-graphrag` uv project

### Existing Infrastructure

- `DocsService.search`, `MarkdownChunker`, `ModularToolsClient`, `parse_agent_output`, `packages.eval`, `get_*` factories
- Spec package skills / Cursor plan format

---

## Architecture Overview

```
P1 measure → P2 baseline → P3 rerank+links → KILL GATE
                              ↓ fail
                         P4 summary route → gate2 → P5 extract → P6 ADR/docs
                              ↓ pass
                            STOP
```

---

## Implementation Phases

### Phase 1: Fix measurement (no GraphRAG)

**Todos in this phase**: `p1-*`  
**Maps to**: FR-001–FR-006, FR-013, SC-001–SC-003, SC-006

**Work**:
- Approval for `citation_groundedness` only (G-metric).
- `ground_citations` + real `_TOOL_NAMES` / golden / validate_data.
- Faithfulness contexts from tools.
- Relative paths + frozen metadata; consolidate vector target `docs`.
- Author ≥20 global/multi-policy golden items.

**Tests**: Unit tests for grounding and path hashes; `validate_data` green; slice loads.

**Success**: Grounding enforced in parser path; eval uses tool contexts; slice exists.

---

### Phase 2: Baseline

**Todos**: `p2-*`  
**Maps to**: FR-008 (baseline half), SC-002

**Work**: Full eval + global slice; write `logs.md` entry with metrics and p95.

**Success**: Numbers on disk for P3 comparison.

---

### Phase 3: Deterministic alternatives + kill gate

**Todos**: `p3-*`  
**Maps to**: FR-007, FR-008, SC-004

**Work**: Reranker injection; `doc_links.json`; one-hop; re-eval; **kill gate decision in Notes below**.

**Success**: Either STOP (ADR-025 upheld) or written authorization for Phase 4.

---

### Phase 4: Summary routing (no LLM extract)

**Todos**: `p4-*` — **blocked on kill-gate fail**  
**Maps to**: FR-009, FR-012, FR-014

**Work**: GraphRag project/service wrap; louvain; summaries namespace; fallback/health; gate2 re-measure.

**Success**: Gate2 recorded — proceed to P5 only if routing moved the slice.

---

### Phase 5: LLM extraction

**Todos**: `p5-*` — **blocked on gate2**  
**Maps to**: FR-010, FR-011, NFR-003–NFR-006

**Work**: Cache + filter + PII allowlist + artifact + CI hash + twin-checkout test.

**Success**: Identical second build; Confluence write refused; eval still groundedness 1.0.

---

### Phase 6: ADR and docs

**Todos**: `p6-*`  
**Maps to**: SC-005, documentation

**Work**: Human approves [ADR-030.draft.md](./ADR-030.draft.md) → append `decisions.md`; update ARCHITECTURE + GRAPHRAG_REVIEW. If kill gate passed early, ADR may document "ADR-025 upheld after measurement + P3".

---

## Testing Strategy (plan-level)

- P1: parser + metrics unit tests; golden validate
- P2/P3: eval runs; no threshold lowering
- P4/P5: fallback tests; determinism; citation invariant under global mode

---

## Notes

### Blockers / decisions (fill during execution)

- **G-metric approval**: **approved 2026-10-15** — user directed "start the work" / implement the plan as specified, including `citation_groundedness` gate at 1.0 (new metric; existing thresholds unchanged).
- **Kill gate outcome**: **P4 authorized by owner 2026-10-15** — user directed skip golden re-measure and proceed with GraphRAG. Prior SSO-blocked STOP superseded. Gate2 (golden re-measure) deferred.
- **Gate2 outcome**: _deferred (owner: skip golden sets for now)_
- **P4 approval**: **approved 2026-10-15** — `LoanOps.GraphRag` + `GRAPHRAG__ENABLED` / `GRAPHRAG__ARTIFACT_DIR` (default off).
- **P5 approval**: **approved 2026-10-15** — owner directed "work on P5 LLM extract" (gate2 still deferred; index-time LLM + local `data/graphrag` artifact commit policy accepted for local `data/sops` only).
- **ADR-030 append**: draft only until human approval — do not edit `decisions.md` until owner accepts ADR-030

### Deviations

- P2 baseline / P3 kill-gate re-eval blocked on live LLM credentials; P3 code (reranker + doc_links + one-hop) still shipped and unit-tested.
- `validate_data` `DATA_DIR` still resolves under `LoanOps.Eval/` (pre-existing); golden rewrite verified via direct file edit (34× `search_docs`).
