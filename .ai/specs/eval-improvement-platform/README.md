# Eval Improvement Platform

This README is the front door for the spec and also its executive summary.

## Overview

Turns LoanOps MCP/agent evaluation from pass/fail dashboards into an **Enterprise AI Evaluation & Improvement Platform**: collect traces, human error analysis, failure categorization, stage diagnosis, governed Golden promotion, and proof that fixes helped. Portal IA follows **Observe / Evaluate / Learn** (inspired by [Arize](https://arize.com/) UX patterns only). System of record remains **EvalStore + Langfuse** (ADR-032); no second eval database.

## Executive Summary

**Status**: Spec drafted · **Version**: 0.1.0 · **Created**: 2026-11-03

### What Gets Implemented

- **Canonical agent turn traces** — instrument AgentCore; envelope for query, spans, retrieval hits, answer, citations.
- **Human feedback API + taxonomy** — binary label, primary/secondary categories, severity, root component, highlights.
- **Observe / Evaluate / Learn portal** — Phase 1 thin (Langfuse deep-links + health strip + feedback); Phase 2 native workbench + Signal Inbox; Phase 3 experiments + advisory Eval Copilot.
- **Stage evaluators** — capability / ApiIndex / SOP / GraphRAG / orchestration / answer (+ L6 security suite).
- **Improvement cycles** — baseline vs post-fix runs; regression flag.
- **Governed promote** — extend existing L9 candidates/registry; never auto-approve.

### Core Approach

Error analysis **before** proliferating LLM judges. Reuse nine layers (`docs/eval/LAYERS.md`), EvalStore, and `make eval-*`. Steal Arize IA; do **not** adopt Phoenix/Arize AX as SoR.

### Key Files

- Spec package: `.ai/specs/eval-improvement-platform/`
- Assessment: [`docs/eval/enterprise-eval-platform-assessment.md`](../../../docs/eval/enterprise-eval-platform-assessment.md)
- Eval code: `projects/LoanOps.Eval/packages/eval/`
- EvalStore: `provider_contracts/eval_store/`, `packages/common/providers/eval_store.py`
- Agent path: `projects/LoanOps.AgentCore/`
- Portal (later): `apps/web_ui/` (+ optional Agent API feedback routes)

### Testing Strategy (at a glance)

Contract tests for feedback/taxonomy; fixture traces for Observe; stage harness unit tests; governance promote/agreement tests; UI later with Playwright only if needed.

## Documents

- [User Stories](./eval-improvement-platform.story.md) — WHAT/WHY (`FR-` / `NFR-` / `SC-`)
- [Technical Specification](./eval-improvement-platform.spec.md) — HOW
- [Implementation Plan](./eval-improvement-platform.plan.md) — phased todos `p1-*` … `p3-*`

## Quick Reference

**What this provides**: inspect → categorize → promote → re-eval → prove improvement.

**What this doesn't provide**: second SoR; auto-applied AI fixes; lowered sacred thresholds; fine-tuning pipeline.

## Architecture Summary

```text
AgentCore + MCP spans → Telemetry/EvalStore (Langfuse|jsonl)
        ↓
Observe (Trace Explorer) → Review (taxonomy) → Signal Inbox
        ↓
Evaluate (layers + stage scores | ops.* separate)
        ↓
Learn (promote candidates → PR → L9 | ImprovementCycle | experiments)
```

## Methodology Lock

1. Collect traces  
2. Human error analysis (~100)  
3. Categorize (controlled vocabulary)  
4. Add deterministic evaluators (LLM judges only after calibration)  
5. Fix tools / prompts / retrieval / SOPs  
6. Golden + regression  

## Related

- [Hamel — Your AI Product Needs Evals](https://hamel.dev/blog/posts/evals/)
- [AI Evals comprehensive study guide](https://github.com/ombharatiya/ai-system-design-guide/blob/main/ai_evals_comprehensive_study_guide.md)
- ADR-032 EvalStore via Langfuse
