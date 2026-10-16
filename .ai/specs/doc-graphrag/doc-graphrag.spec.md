# Technical Specification: Doc GraphRAG

**Related User Stories**: [doc-graphrag.story.md](./doc-graphrag.story.md)  
**Created**: 2026-10-15  
**Status**: Draft  
**Related ADRs**: ADR-025 (defer GraphRAG — to be superseded/clarified by draft ADR-030); ADR-026 (EAKG GraphStore stays capability RDF only)

---

## Overview

This document describes **HOW** to implement [doc-graphrag.story.md](./doc-graphrag.story.md): fix citation measurement and path stability first, ship deterministic retrieval upgrades, then kill-gate any LLM GraphRAG behind proven need.

**Purpose**: Architecture, algorithms, data models, signatures, and decisions concrete enough that implementation is transcription.

**Audience**: Architects, implementers, reviewers.

**Non-goals in code until kill gate fails**: `LoanOps.GraphRag` project, community summary namespace, LLM extraction CLI. P1–P3 land inside existing packages.

---

## Architecture

### High-Level Architecture

```
P1 MEASUREMENT
  AgentTurn → parse_agent_output → ground_citations(recorded_tools)
  Eval → faithfulness contexts from tool results
       → citation_groundedness metric (gate 1.0)

P2 BASELINE
  golden suite + global slice → logs.md p95

P3 DETERMINISTIC (ADR-025 path)
  DocsService.search:
    embed → vector top candidate_k → optional doc_links one-hop
    → get_reranker_provider().rerank → top_k 5
  paths = corpus-relative POSIX; metadata frozen

KILL GATE ──pass──► stop (ADR-025 upheld)
          └──fail──► P4+ GraphRAG

P4 SUMMARY ROUTING (no LLM extract)
  louvain on doc_links → community summaries → ns graphrag_summaries
  GraphRagService wraps DocsService; global resolve → member chunks only

P5 LLM EXTRACT (optional)
  cache keyed (chunk, model_id, prompt_ver, schema_ver)
  artifact data/graphrag/{graph,communities,manifest}.json
  refuse commit when policy source ≠ local sops
```

### Component Design

#### CitationGrounder (AgentCore)

**Purpose**: Enforce FR-001 / FR-002 after `_fix_citations`.

**Responsibilities**:
- Collect policy paths and chunk texts from `recorded_tools` entries whose name is `search_docs` (and any registered doc-search alias).
- Drop or flag `policy:` citations whose source path (strip `#fragment`) is not in the retrieved path set.
- Require citation `snippet` to be a substring of some retrieved chunk text (normalized whitespace), else drop.
- Never rewrite `tool:` ↔ `policy:` incorrectly; `_TOOL_NAMES` must match the live tool registry.

**Interfaces**:
```python
def ground_citations(
    data: dict[str, Any],
    recorded_tools: list[Any],
) -> GroundingReport:
    """Mutate citations in place; return counts of kept/dropped."""

@dataclass(frozen=True)
class GroundingReport:
    kept: int
    dropped_ungrounded: int
    dropped_bad_snippet: int
```

**Dependencies**: `parse_agent_output` already accepts `recorded_tools`.

---

#### Eval metrics (LoanOps.Eval)

**Purpose**: FR-003, FR-004, SC-001, SC-002.

**Responsibilities**:
- Build Ragas `contexts` from tool result texts on the turn (prefer `ToolResult.data["text"]` for `search_docs`), not `citation.snippet`.
- Add `compute_citation_groundedness(results) -> float` = fraction of items where every emitted `policy:` citation is grounded (or item has zero policy citations and is refusal).
- Gate `citation_groundedness` at 1.0 in `thresholds.py` (**approval required** — new metric, does not lower existing).

---

#### DocsService (LoanOps.Docs) — P1 path + P3 retrieval

**Purpose**: Stable chunk identity (FR-013); ranking + expand (FR-007).

**Responsibilities**:
- Normalise `path` to POSIX relative to corpus root before chunking.
- Freeze metadata keys: `corpus`, `path`, `category`, `state`, `heading_path` (optional empties allowed; key set frozen).
- `search(query, *, top_k=5)` → retrieve `candidate_k` (ctor default 20), expand one hop via `DocLinkGraph`, rerank, return formatted string with citable paths only.
- Constructor injects optional `AbstractRerankerProvider` and `DocLinkGraph`; no new env var for `candidate_k`.

**Interfaces**:
```python
class DocsService:
    def __init__(
        self,
        embedding: EmbeddingProvider,
        vector_store: VectorStoreProvider,
        *,
        namespace: str = DOCS_NAMESPACE,
        reranker: AbstractRerankerProvider | None = None,
        link_graph: DocLinkGraph | None = None,
        candidate_k: int = 20,
    ) -> None: ...

    async def search(self, query: str, *, top_k: int = 5) -> str: ...
```

---

#### DocLinkGraph (LoanOps.Rag or LoanOps.Docs)

**Purpose**: Deterministic edges for one-hop expand (FR-007).

**Responsibilities**:
- Offline builder writes `data/graphrag/doc_links.json` (or `data/docs/doc_links.json` in P3 — prefer `data/docs/` until GraphRAG project exists).
- Edges from: markdown links, shared `category`, shared `state`, optional SOP→capability id tags from front-matter.
- Runtime: `neighbors(path: str) -> list[str]` sorted for determinism.

---

#### GraphRagService (LoanOps.GraphRag) — P4+ only

**Purpose**: Wrap `DocsService`; FR-009–FR-012.

**Responsibilities**:
- Same `async def search(self, query: str, *, top_k: int = 5) -> str` signature.
- Internal pure function `select_route(query: str) -> Literal["local","global"]` — **not** exposed on the LLM tool schema.
- Local: delegate to wrapped DocsService (already rerank+hop).
- Global: search namespace `graphrag_summaries`; map hits → `member_chunk_ids` → load verbatim chunk texts; emit summaries only under a `context (not citable)` section; citable lines remain `policy:<relpath>#...`.
- On missing/stale/corrupt artifact: delegate entirely to DocsService; set health flag.

**Dependencies**: embedding, vector store, DocsService, artifact loader. Chosen once in `build_modular_tools_client`.

---

### Data Flow

**Query (P3)**:
```
query → embed → vector_store.search(ns=docs, top_k=candidate_k)
     → union(one-hop neighbors' chunks from store by path)
     → reranker.rerank(query, texts) → take top_k
     → format bullets with relative path + snippet
     → ModularToolsClient → agent → ground_citations
```

**Query (P4 global)**:
```
query → embed → search(ns=graphrag_summaries)
     → community records → member_chunk_ids
     → fetch chunk texts from docs ns
     → format: citable chunks + non-citable summary block
     → ground_citations (summaries cannot pass path check unless path was in member set — summaries have no policy path in citable section)
```

**Index (P5)**:
```
policy_source.fetch_pages → MarkdownChunker (relative meta)
  → per chunk: cache lookup | chat extract (temp 0, JSON schema)
  → PII scrub (allowlist entity types)
  → grounding filter (name in chunk; endpoints co-occur)
  → resolve entities deterministically → edges
  → merge DocLinkGraph edges
  → louvain_partitions(seed=FIXED)
  → summarize communities → embed → upsert graphrag_summaries
  → write artifact + manifest.corpus_hash
```

---

## Algorithms & Logic

### Citation grounding

**Purpose**: FR-001, FR-002.

**Pseudocode**:
```
paths, texts = extract_from_search_docs(recorded_tools)
for cite in citations:
  if source starts with tool:
    continue  # keep; do not rewrite to policy
  if source starts with policy: OR will be fixed to policy:
    path = strip_prefix_and_fragment(source)
    if path not in paths and not any(path_endswith_match):
      drop(cite); continue
    if cite.snippet and not substring(normalize(cite.snippet), texts):
      drop(cite)
return report
```

**Complexity**: O(C × T) citations × retrieved text length; C and T small per turn.

### Path normalisation (chunk id stability)

**Purpose**: FR-013, SC-006.

**Pseudocode**:
```
rel = path.resolve().relative_to(corpus_root.resolve())
meta["path"] = rel.as_posix()  # never str(Path) absolute
# category/state from first path parts / front-matter; heading_path from chunker headers
chunk_id = sha256(content + str(sorted(meta.items())))[:16]
```

**Complexity**: O(n) per file.

### Local search with rerank + hop

**Purpose**: FR-007.

**Pseudocode**:
```
hits = vector.search(emb, top_k=candidate_k)
paths = {h.metadata["path"] for h in hits}
for p in list(paths):
  for n in link_graph.neighbors(p):  # sorted
    paths.add(n)
docs = fetch_by_paths(paths)  # preserve text+meta
if reranker:
  order = reranker.rerank(query, [d.text for d in docs])
  docs = take(order, top_k)
else:
  docs = take(hits, top_k)
return format(docs)
```

**Complexity**: O(candidate_k + E_neighbors + R) where R = rerank cost ~ O(candidate_k) cross-encoder forwards.

### Kill gate

**Purpose**: FR-008, SC-004.

**Pseudocode**:
```
baseline = eval(slice, flat)
after = eval(slice, docs_with_rerank_hop)
if after.faithfulness >= 0.85 and after.citation_groundedness >= 1.0:
  STOP  # no P4+
else:
  authorize P4
```

### Community routing (P4)

**Purpose**: FR-009.

**Pseudocode**:
```
G = graph_from_doc_links(nodes=paths, edges=doc_links)
parts = list(louvain_partitions(G, seed=42))  # take level 0 and 1 if available
for community in parts[level]:
  summary = llm_or_extractive_summary(member_texts)  # P4 may use extractive first
  record = {id, member_chunk_ids, source_paths, summary}
embed_upsert(record, ns="graphrag_summaries")
```

**Complexity**: Louvain ~ O(n log n) typical; n ≈ 100–200 chunks.

### Extraction cache key (P5)

```
key = sha256(chunk.content | model_id | prompt_version | schema_version)
path = cache_dir / f"{key.hex()}.json"
```

### Extraction grounding filter (P5)

```
for entity in extracted:
  if normalize(entity.name) not in normalize(chunk.text): drop
for rel in relations:
  if not (endpoints co-occur in same chunk text): drop
```

---

## Data Model

### Frozen chunk metadata

| Field | Type | Validation |
|-------|------|------------|
| `corpus` | str | non-empty; default `sop` |
| `path` | str | POSIX relative; no drive letter; no `..` |
| `category` | str | optional; from path segment or front-matter |
| `state` | str | optional; empty if N/A |
| `heading_path` | str | optional; `>`-joined headers |

Changing this key set after freeze **requires** full re-index and artifact rebuild.

### `doc_links.json`

```json
{
  "version": 1,
  "edges": [
    {"from": "hardship/forbearance.md", "to": "hardship/disaster.md", "kind": "markdown_link"}
  ]
}
```

`kind` ∈ `markdown_link | category | state | capability`.

### Graph artifact (P5) — `data/graphrag/`

| File | Role |
|------|------|
| `graph.json` | entities, relations, chunk_ids |
| `communities.json` | community id → member_chunk_ids, summary ref |
| `manifest.json` | `corpus_hash`, `model_id`, `prompt_version`, `schema_version`, `created_at` |

**Validation**: `manifest.corpus_hash == hash_tree(data/sops)`; else stale.  
**Git**: commit the three files when source is local; **do not** commit `cache/`.  
**Confluence**: CLI exits non-zero if `DATA__SOP_SOURCE` ≠ `local` and `--write-repo-artifact` is set.

### Tool output contract (search_docs)

Citable lines:
```
- [sop] hardship/forbearance.md (score=0.81)
  <verbatim snippet ≤ N chars, N chosen so total tool text ≤ ~1500 tokens>
```

Optional non-citable block (P4+):
```
## context (not citable)
Community summary: ...
```

---

## API Design / Function Signatures

### Agent / tools / MCP

- Keep tool name `search_docs`.
- Parameters remain `{ query: string, top_k?: integer }` — **do not** add `mode` to the LLM schema (variance).
- Handler continues to call `self._docs.search(...)`; factory may inject `GraphRagService` where `DocsService` was.

### Eval

```python
def compute_citation_groundedness(results: list[EvalItemResult]) -> float: ...

# thresholds.py
THRESHOLDS["citation_groundedness"] = (1.0, "gte")
```

### Health (P6 / FR-014)

Extend `/health` (or readiness payload) with:
```json
{
  "docs_search": "flat|rerank_hop|graphrag_local|graphrag_degraded",
  "graphrag_artifact": "absent|ok|stale|corrupt"
}
```

---

## Technical Decisions

### D1 — Artifact vs SPARQL store

**Context**: FR-009–012; NFR-005; ADR-026 reserves GraphStore for EAKG.  
**Decision**: Checked-in JSON artifact for local corpus; no new Provider for v1 GraphRAG.  
**Alternatives**: Named graph in GraphDB — rejected (overkill ~120 chunks; mixes governed capability RDF with noisy doc entities). Startup-only rebuild — rejected (loses cross-run reproducibility).  
**Consequences**: + demo/local-first; + diffable. − merge conflicts on communities (regenerate after merge). − Confluence must not write into repo.

### D2 — Extraction model pinning

**Decision**: Pin via process-scoped `LLM__*` for the index CLI; record resolved model id in manifest; refuse build if model ≠ manifest without `--rebuild`. No `GRAPHRAG__EXTRACT_MODEL` unless later required.  
**Alternatives**: Factory override path — rejected (new surface + env approval).  
**Consequences**: + fewer approvals. − operators must set env correctly for rebuilds.

### D3 — Vector target

**Decision**: Single namespace `docs`. Point `ingest_sops` at DocsService indexing or delete dead `sops` collection path.  
**Alternatives**: Dual-write — rejected (drift).  
**Consequences**: Agent and CLI share one index.

### D4 — Golden tool names + `_TOOL_NAMES`

**Decision**: Rewrite golden `search_policy` → `search_docs`; update `validate_data.valid_tools`; replace `_TOOL_NAMES` with the live agent tool registry set.  
**Alternatives**: Keep alias forever — rejected (feeds finding 1).  

### D5 — Faithfulness contexts

**Decision**: Contexts from tool results (`search_docs` text and other tool data), not citation snippets.  
**Consequences**: Scores may drop; thresholds unchanged (NFR-001).

### D6 — Reranker wiring

**Decision**: Constructor injection on DocsService; `candidate_k` ctor arg; use existing `get_reranker_provider()`. No new env var.  
**Alternatives**: Env-gated — rejected (unnecessary approval).

### D7 — Kill-gate ordering

**Decision**: P1 measurement → P2 baseline → P3 deterministic → gate → P4 summaries → gate2 → P5 extract → P6 ADR/docs.  
**Alternatives**: Build GraphRAG first — rejected (cannot measure; ADR-025 violated).

### D8 — Community algorithm

**Decision**: `networkx.algorithms.community.louvain_partitions` with fixed `seed` and sorted node insertion order.  
**Alternatives**: `greedy_modularity_communities` — rejected (no seed; not hierarchical).

### D9 — PII scrub allowlist

**Decision**: Scrub PERSON/PHONE/EMAIL/US_SSN etc.; allowlist LOCATION tokens that match known state names / policy vocab when present in source chunk as whole words.  
**Alternatives**: Full Presidio default — rejected (redacts FL / agency names).  

### D10 — Cross-project imports

**Decision**: Copy gap-ledger *shape* into GraphRag; do not import `packages.eakg`.  

---

## File Structure

### New (after kill gate / as phases unlock)

| Path | Purpose |
|------|---------|
| `.ai/specs/doc-graphrag/*` | This spec package |
| `projects/LoanOps.GraphRag/packages/graph_rag/` | P4+ service, index CLI, schemas |
| `data/docs/doc_links.json` | P3 link graph |
| `data/graphrag/{graph,communities,manifest}.json` | P5 artifact (if unlocked) |
| `data/graphrag/cache/` | Untracked extraction cache |
| `.ai/specs/doc-graphrag/ADR-030.draft.md` | ADR draft pending approval |

### Modified (P1–P3)

| Path | Change |
|------|--------|
| `projects/LoanOps.AgentCore/packages/agent_core/_output_parser.py` | Real tool names; call `ground_citations` |
| `projects/LoanOps.Eval/packages/eval/{metrics,thresholds,run,validate_data}.py` | Groundedness; tool contexts; valid_tools |
| `data/golden.jsonl` | `search_policy` → `search_docs`; add ≥20 slice items (or `data/golden_global.jsonl` + runner flag) |
| `projects/LoanOps.Docs/packages/docs/service.py` | Relative path meta; rerank; hop |
| `projects/LoanOps.Rag/packages/rag/ingest.py` | Index into `docs` / DocsService |
| `projects/LoanOps.Tools/packages/tools/factory.py` | Inject reranker; later GraphRagService |
| `ARCHITECTURE.md`, `docs/GRAPHRAG_REVIEW.md`, `logs.md` | P6 / baselines |

---

## Implementation Details

### P1 — Measurement

1. Implement `ground_citations` in AgentCore; invoke from `parse_agent_output` after `_fix_citations`.
2. Fix `_TOOL_NAMES` to include at least: `lookup_loan`, `get_payment_schedule`, `get_escrow_breakdown`, `check_hardship_eligibility`, `search_docs`, `call_sse_api`, and other tools from `_agent.py` ToolDefinition list (single source: import or shared constant).
3. Change `run.py` context build to collect tool texts from item results (extend `EvalItemResult` to store tool payloads if not present).
4. Add metric + threshold (approval gate G-metric).
5. Path normalisation in `DocsService.index_markdown_file` / directory indexer; unit test two fake roots → same chunk ids.
6. Fix golden + validate_data.
7. Author global slice (≥20).

### P2 — Baseline

Run eval; append dated entry to `logs.md` with faithfulness, groundedness, citation_coverage, latency p95.

### P3 — Deterministic upgrades

Wire reranker; build `doc_links.json` CLI; one-hop; re-eval; **kill gate decision recorded in plan Notes**.

### P4–P6

Only if authorized; implement GraphRagService wrap; louvain; summaries; optional extract; ADR-030 append to `decisions.md` after human approval of draft.

---

## Integration Points

| System | Method | Error handling |
|--------|--------|----------------|
| Embedding / VectorStore / Reranker / Chat / PII | Existing factories | Fail closed to flat DocsService |
| Policy source | `get_policy_source_provider()` | Confluence → no repo artifact write |
| MCP / ModularToolsClient | `search_docs` unchanged schema | docs None → existing error string |
| Eval / golden | files under `data/` | validate_data fails CI on bad tool names |

---

## Edge Cases & Error Handling

| Story edge | Handling |
|------------|----------|
| No docs returned + model cites policy | All policy cites dropped; groundedness fails if golden required cites |
| Path match but snippet not in chunk | Drop cite (`dropped_bad_snippet`) |
| Summary vs member chunk | Only member paths appear in citable section |
| Confluence source | CLI refuse `--write-repo-artifact` |
| Absolute paths historically | Re-index required once; document in migration notes |
| Runtime `index_docs` without graph refresh | Health `stale`; global disabled |
| Prompt blow-up | Cap tool output ~1500 tokens; prefer 400–800 char snippets still from verbatim text |
| PII over-redaction | Allowlist state/vocab tokens |

**Error types**: `GraphArtifactError` (corrupt/schema); treat as degenerate → DocsService. Never raise through `/chat` for stale graph.

---

## Security Considerations

- Citation grounding reduces citation spoofing (FR-001).
- PII scrub on extraction outputs (story Security).
- No new public HTTP surface beyond existing `/chat` and MCP tools.
- Audit: prefer logging grounded `policy:` sources only (already filters prefix in agent API).

---

## Performance Considerations

Tied to NFR-001–NFR-003:

| Metric | Target |
|--------|--------|
| `search_docs` p95 local (warm) | ≤ 300 ms |
| `search_docs` p95 global (warm) | ≤ 500 ms |
| Tool output size | ≤ ~1500 tokens |
| Turn p95 | ≤ 4000 ms (existing gate) |
| Index (P5, ~120 chunks) | ≤ 10 min local |
| Artifact size | ≤ 3 MB total CI fail |

Primary latency risk is prompt prefill from large verbatim chunks, not MiniLM rerank (~0.2–0.6 s warm).

---

## Testing Strategy

| Layer | Scenarios | Maps to |
|-------|-----------|---------|
| Unit | `ground_citations` keep/drop; path norm hash stability; louvain seed determinism | FR-001, FR-013, SC-006 |
| Unit | DocsService rerank order; hop adds neighbour | FR-007 |
| Unit | Artifact stale/missing → fallback | FR-012 |
| Integration | parse_agent_output + recorded_tools end-to-end | FR-001, FR-002 |
| Eval | golden rewrite validates; global slice runs; groundedness gate | FR-004–006, SC-001–003 |
| Eval | Kill-gate comparison script/notes | FR-008, SC-004 |
| Contract | No new provider unless P5+ store appears | NFR-005 |
| Cross-machine | Two temp checkouts, same relative corpus, identical chunk ids | SC-006 |

Coverage targets: new modules ≥ existing package norms; AgentCore grounding ≥ 5 unit cases; DocsService search ≥ 3.

---

## Configuration

| Variable | Phase | Required | Default | Notes |
|----------|-------|----------|---------|-------|
| *(none for P1–P3 rerank)* | P3 | — | `candidate_k=20` ctor | Avoid env |
| `GRAPHRAG__ENABLED` | P4+ | no | `false` | Only if wrap needs flag; prefer factory selection |
| `GRAPHRAG__ARTIFACT_DIR` | P4+ | no | `data/graphrag` | |
| Approval: new metric gate | P1 | yes | — | Human |

Prefer **zero** new env vars through P3. Any `GRAPHRAG__*` requires AGENTS.md approval.

---

## Dependencies

**External**: `networkx` (already transitive in lock — declare direct if importing); `sentence-transformers` / torch (existing reranker).

**Internal**: `LoanOps.Docs`, `LoanOps.Rag`, `LoanOps.AgentCore`, `LoanOps.Eval`, `LoanOps.Tools`, `packages.common.providers.factory`, `provider_contracts.reranker`.

**Do not depend on**: `LoanOps.Eakg` packages from GraphRag.

---

## Deployment / Migration

1. Re-index all docs after path normalisation (chunk ids change once).
2. Regenerate `doc_links.json` when SOPs change.
3. After merge conflicts on communities: regenerate, never hand-merge.
4. Feature flag / default off until kill gate path chosen.

---

## Open Technical Questions

- **TQ-001**: Store global golden slice in `data/golden.jsonl` vs separate file + runner flag? Prefer separate `data/golden_global.jsonl` to avoid diluting latency stats — confirm with eval owners.
- **TQ-002**: Does `EvalItemResult` already retain tool payloads? If not, thread them from `run_agent_turn` recording.
- **TQ-003**: Extractive vs LLM community summaries in P4 — prefer extractive first to avoid index LLM cost before P5.

---

## References

- [doc-graphrag.story.md](./doc-graphrag.story.md)
- [docs/GRAPHRAG_REVIEW.md](../../../docs/GRAPHRAG_REVIEW.md)
- [decisions.md](../../../decisions.md) ADR-025, ADR-026, ADR-029
- [ARCHITECTURE.md](../../../ARCHITECTURE.md) §11, §13
- [ADR-030.draft.md](./ADR-030.draft.md)
