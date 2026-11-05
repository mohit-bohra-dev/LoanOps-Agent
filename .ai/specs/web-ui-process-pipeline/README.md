# Web UI Process Pipeline

This README is the front door for the spec and also its executive summary.

## Overview

Recovers real multi-step process knowledge from application **Web front-end projects** (for example `CoreComponents.Web`, `Escrow.Web`, `Fees.Web`): screens, how users move between them, and which backend operations each screen uses. Output starts as **pending-review flow proposals** in the existing process KG (ADR-028). Approved flows can later add "related steps" to `search_sse_apis` answers, flag-gated and off by default.

## Executive Summary

**Status**: Spec drafted · **Version**: 0.1.0 · **Created**: 2026-11-05

### What Gets Implemented

- **Web project registration** — `web_project_paths` per application in the EAKG registry.
- **Tiered static extractor** — MVC/Razor, SPA (tree-sitter), lexical fallback; chosen after an inventory of the real Web projects.
- **Page → API edges** — each screen mapped to catalog `operationKey` values (matched / ambiguous / unmatched).
- **Flow proposals + review** — `pending_review` → approve / reject; `needs_reapproval` on source drift.
- **Gap report** — unmatched calls, unsupported tech, dynamic routes, screens with no detected calls.
- **Graph load** — approved flows into named graph `ui_flow_<application_id>`.
- **Related steps (optional)** — one-hop neighbours from approved flows appended to search results.

### Core Approach

Deterministic static analysis only (no browser crawl, no LLM in the extractor). UI facts are the evidence layer; flows are the reviewed meaning layer reusing ADR-028 lifecycle. Process data stays advisory and never authorizes calls.

### Key Files

- Spec package: `.ai/specs/web-ui-process-pipeline/`
- EAKG code: `projects/LoanOps.Eakg/packages/eakg/` (new `analyzers/web_ui_adapter.py`, `extractors/web/`, `ui_flow*.py`)
- Search integration (Phase 4): `projects/LoanOps.Sse/packages/sse/tools.py`, `projects/LoanOps.Tools/packages/tools/capability.py`
- Prior art: ADR-028 / ADR-029 process KG, `projects/LoanOps.Eakg/packages/eakg/process_graph.py`

### Testing Strategy (at a glance)

Synthetic MVC and SPA fixtures; unit tests for join, drafting, drift, and review; RDF round-trip; contract tests that flag-off search output is byte-identical; no eval threshold changes.

### Approval needed before build

ADR-033, new registry field `web_project_paths`, env vars `EAKG__UI_FLOW_ENABLED` and `SSE__PROCESS_EXPAND_ENABLED` (see AGENTS.md approval list).

## Documents

- [User Stories](./web-ui-process-pipeline.story.md) — WHAT/WHY (`FR-` / `NFR-` / `SC-`)
- [Technical Specification](./web-ui-process-pipeline.spec.md) — HOW
- [Implementation Plan](./web-ui-process-pipeline.plan.md) — phased todos `p1-*` … `p5-*`

## Quick Reference

**What this provides**: screens → navigation → operation uses → reviewed flows → optional related steps.

**What this doesn't provide**: runtime analytics, screenshots, LLM-built flows, authorization from flow data, write/mutating calls.

## Architecture Summary

```text
registry web_project_paths
        ↓
clone/fetch → WebUiAdapter (mvc | spa | lexical)
        ↓
UiFactSet → join to operationKey → gaps
        ↓
flow drafts (pending_review) → review CLI (approve/reject)
        ↓ approved
named graph ui_flow_<app>
        ↓ (Phase 4, flag-gated)
search_sse_apis "Related steps"
```

## Open Questions

1. Real stack of the Web projects and how they reach API operations (Phase 1 inventory).
2. Pilot application.
3. Reviewer surface: CLI first or web app.
4. Auth-only screens: record or ignore.

## Related

- ADR-028 business process KG, ADR-029 deterministic extract + investigation
- `docs/PIPELINES.md`, `docs/CAPABILITY_ONTOLOGY.md`
