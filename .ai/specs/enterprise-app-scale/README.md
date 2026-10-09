# Enterprise App Scale

This README is the front door for the spec and also its executive summary.

## Overview

Takes LoanOps from a 3-app proof of concept to a 30+ application enterprise product. Applications are registered once, their operation descriptions are fetched and cached by a pipeline (never at boot), EAKG capabilities and OpenAPI operations become one callable record, search uses pgvector with an app shortlist, each live read uses that application's own credential, and operators see per-application health. Implements **ADR-024** in [decisions.md](../../../decisions.md) (status: Accepted 2026-10-09).

## Executive Summary

**Status**: Draft · **Version**: 1.0.0 · **Created**: 2026-10-08

### What Gets Implemented

- Registry (`data/eakg/registry/repositories.yaml`) as the only app list. Each row is the application mapping: optional GitLab `git_url`, TAAC `service_url_key`, and a per-environment `base_url` (FR-022). TAAC may fill a blank address. It must not invent a repo from a URL.
- Spec fetch and cache per app/env during onboarding and refresh, with last-good retention. Runtime builds its catalog from the cache and makes no network calls.
- A unified operation record keyed `application|METHOD|normalized_path`, with one public id (`app:operationId`) that capability ids and bare names resolve to. Fixes capability bind.
- Incremental vector index in the `VectorStore` provider (namespace per env and embed model), two-stage search with app/permission filters, and a JSON sidecar fallback.
- A new `CredentialBroker` provider (static + mock + caching) and per-app invoke with origin binding, a circuit breaker, and "no access" vs "unavailable" messages that name the application.
- Per-app `/ready`, metrics, scheduled incremental refresh, and a synthetic scale suite (30 apps, ~5k ops).

### Core Approach

Slow, failure-prone work (spec fetch, join, embedding) moves to the pipeline. The runtime reads local files and the vector store only. Failures are isolated and reported per application. Every new capability goes through the provider abstraction and the settings module.

### Key Files

`packages/eakg/{registry,registry_validate,registry_import,spec_cache,onboard}.py`, `packages/sse/{loader,invoke,tools}.py`, new project `projects/LoanOps.ApiIndex/packages/api_index/`, `packages/common/providers/credential_broker.py`, `packages/tools/{factory,registry_catalog}.py`, `packages/mcp_server/{capability_bind,server}.py`.

### Testing Strategy (at a glance)

Unit and integration tests for each phase, all network-free and using synthetic data. Contract tests cover the new broker and the vector-filter semantics. A `-m scale` suite measures readiness, discovery p95, top-5 recall and 20 % failure isolation against the story targets.

## Documents

- [User Stories](./enterprise-app-scale.story.md) — WHAT/WHY, requirements `FR-`/`NFR-`/`SC-`
- [Technical Specification](./enterprise-app-scale.spec.md) — HOW
- [Implementation Plan](./enterprise-app-scale.plan.md) — phased todos

## Quick Reference

**What this provides**: single-place registration; discovery across 30+ apps that stays fast as the catalog grows; per-app credentials and clear access errors; capability = callable operation; per-app health; environment separation.

**What this doesn't provide** (story Out of Scope): data-changing operations; choosing the final access model (only kept swappable); wiki generation; UI redesign.

## Architecture Summary

```text
PIPELINE  registry ─► spec refresh (per app, isolated) ─► cached specs ─► unified operations ─► vector index
RUNTIME   catalog from files ─► 2-stage search ─► resolver ─► invoke (CredentialBroker per app, breaker) ─► audit
          /ready: per-app indexed · spec age · credential · last outcome
```

## User Experience

```text
User: What is the payment schedule for loan <synthetic id>?
search_sse_apis → loanservices:getPaymentSchedules (Loan Services) …
call_sse_api   → outcome=ok, citation tool:call_sse_api:loanservices:getPaymentSchedules
— or —
call_sse_api   → outcome=no_access: "Escrow Manager (escrow) has not granted LoanOps access in dev (HTTP 403)."
```

## Key Concepts

- **Registry record / AppEnvironment**: one app plus its per-env target (base URL, audience, spec path).
- **Spec pointer**: `current.json` per app/env recording the last good spec and the last attempt.
- **UnifiedOperation**: OpenAPI and EAKG merged into one record; `public_id` is the stable id shown to users.
- **CredentialBroker**: resolves a token for an application and audience. The implementation is pluggable.
- **Outcome**: `ok | no_access | unavailable | not_found | rejected | error`.

## Implementation Overview

### Timeline

P1 Registry + spec cache (M) → P2 Unified record + bind (M) → P3 Vector index + search (L) ∥ P4 Credentials + invoke (M) → P5 Health + scale (M) → P6 Docs (S).

### Dependencies

Approval gates G1–G10 (spec §1.1): ADR-024 acceptance, registry schema, new env vars, new `LoanOps.ApiIndex` project, `provider_contracts` filter change, the `CredentialBroker` provider (`get_credential_broker` is the 14th `get_*` factory), and benchmark thresholds. Until a product owner is named (story OQ-6), gates route to repo owner `mohit-bohra-dev`. Application teams must publish specs and grant access.

## Quality Standards

- **Testing**: ≥ 90 % line coverage on new modules; contract tests for the new provider; scale suite at story targets.
- **Documentation**: TASKS.md, logs.md, ARCHITECTURE.md, AGENTS.md, CONTEXT.md, decisions.md updated (plan Phase 6).
- **Code quality**: `mypy --strict`, async throughout, uv only, grep gates for concrete provider imports and `os.environ`, `check_project_refs`, `graphify update .`.

## Safety Guarantees

GET/HEAD only, and no request bodies. Tokens are never sent to another app's origin and are never logged. Every live read is audited. Fixtures are synthetic only. Local-first: `make demo` needs no cloud credentials.

## Performance Targets

Ready in under 10 s regardless of app count (SC-004). Discovery p95 under 1.5 s at 30+ apps / thousands of ops (SC-003). Top-5 hit rate of at least 90 % (SC-002). Targets are pending confirmation in story Q2.

## Getting Started

- **For implementers**: read spec §1.1 (gates), §2 (architecture) and §9 (per-phase details), then work the plan todos in order. Do not start a phase before its gate is approved.
- **For reviewers**: check spec §7 (decisions), §11 (edge cases), §12 (security) and §19 (open questions) against the story.

## Status

| Phase | State |
|---|---|
| P1 Registry, spec cache, catalog from cache | Not started |
| P2 Unified record, bind fix | Not started |
| P3 Vector index, two-stage search | Not started |
| P4 CredentialBroker, per-app invoke | Not started |
| P5 Health, metrics, schedule, scale | Not started |
| P6 Docs | Not started |

## Related Documents

- ADR-022, ADR-023, ADR-024 — [decisions.md](../../../decisions.md)
- [docs/ARCHITECTURE_REVIEW_LAYER2.md](../../../docs/ARCHITECTURE_REVIEW_LAYER2.md) §8 (auth program, parked)
- [logs.md](../../../logs.md) — 2026-10-08 smoke evidence

## Success Criteria

Story SC-001 … SC-010, each mapped to tests in spec §14.
