# Doc GraphRAG

This README is the front door for the spec and also its executive summary.

## Overview

Makes policy answers trustworthy to measure, then upgrades document retrieval in the cheapest order that can still fail closed: citation grounding and eval fixes → baseline → rerank + deterministic doc links → **kill gate**. Full GraphRAG (community summary routing, then optional LLM extraction) ships only if the global/multi-policy golden slice still fails after the cheap path. Overrides **ADR-025** only under that evidence (see draft **ADR-030**).

## Executive Summary

**Status**: Spec drafted · **Version**: 0.1.0 · **Created**: 2026-10-15

### What Gets Implemented

- **Citation grounding** — `policy:` citations must match chunks returned by `search_docs` this turn; tool names stop being rewritten into fake policy sources.
- **Honest eval** — faithfulness contexts from tool results; new `citation_groundedness` gate at 1.0 (approval required; existing thresholds unchanged).
- **Stable doc identity** — corpus-relative POSIX paths in chunk metadata; single `docs` vector namespace.
- **Global golden slice** — ≥20 multi-policy / survey questions before GraphRAG code.
- **Deterministic retrieval** — existing reranker + `doc_links.json` one-hop expand (ADR-025 path).
- **Kill-gated GraphRAG** — summary routing first; LLM extract last; artifact + fallback; Confluence must not commit into git.

### Core Approach

Measurement before graph. If P3 passes the slice, **stop** — ADR-025 stands. If not, add routing complexity only as far as gate2 justifies. Community summaries are never policy citation sources.

### Key Files

- Spec package: `.ai/specs/doc-graphrag/`
- Likely code touchpoints: `agent_core/_output_parser.py`, `packages/eval/*`, `docs/service.py`, `rag/ingest.py`, `tools/factory.py`; conditional `projects/LoanOps.GraphRag/`
- ADR draft: [ADR-030.draft.md](./ADR-030.draft.md) — **do not append to `decisions.md` until approved**

### Testing Strategy (at a glance)

Unit tests for grounding and path stability; eval baselines in `logs.md`; kill gate / gate2 recorded in the plan Notes; cross-checkout determinism if P5 unlocks.

## Documents

- [User Stories](./doc-graphrag.story.md) — WHAT/WHY, requirements `FR-`/`NFR-`/`SC-`
- [Technical Specification](./doc-graphrag.spec.md) — HOW
- [Implementation Plan](./doc-graphrag.plan.md) — phased todos `p1-*` … `p6-*`
- [ADR-030 draft](./ADR-030.draft.md) — pending human approval

## Quick Reference

**What this provides**: trustworthy citations and eval; cheaper retrieval upgrades; optional GraphRAG only when proven necessary.

**What this doesn't provide**: EAKG replacement; lowered eval thresholds; Confluence graph commits; `mode` exposed to the LLM tool schema.

## Architecture Summary

```text
P1 ground+eval+paths+slice → P2 baseline → P3 rerank+links → KILL GATE
                                                          ↓ fail
                                              P4 summaries → gate2 → P5 extract → P6 ADR/docs
```

## Kill Gate

After P3: if global slice **faithfulness ≥ 0.85** and **citation_groundedness ≥ 1.0**, do **not** build GraphRAG. Record outcome in plan Notes and treat ADR-025 as upheld (short ADR-030 note still recommended).

## User Experience

```text
User: What hardship options differ for FL disaster vs standard forbearance?
search_docs → citable chunks only (paths relative)
answer → citations policy:… must appear in that turn's retrieval
eval → faithfulness judged on retrieved text, not model footnotes
```

## Implementation Overview

### Timeline

P1 Measurement (L) → P2 Baseline (S) → P3 Deterministic + kill gate (M) → [optional] P4 Summary route (M) → [optional] P5 Extract (L) → P6 Docs/ADR (S).

### Dependencies

- Human approval: new metric gate; any ADR-030 append; any `GRAPHRAG__*` / new project if past kill gate.
- Must not lower thresholds in `packages/eval/thresholds.py`.

## Getting Started

1. Read the [story](./doc-graphrag.story.md) for requirements.
2. Read the [spec](./doc-graphrag.spec.md) for mechanisms.
3. Execute the [plan](./doc-graphrag.plan.md) in order; stop at kill gate unless authorized.
4. Keep [ADR-030.draft.md](./ADR-030.draft.md) out of `decisions.md` until a human approves.
