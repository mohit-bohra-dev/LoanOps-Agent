---
name: web-ui-process-pipeline
overview: Build a deterministic pipeline that reads application Web projects, extracts screens, navigation, and screen-to-operation uses, proposes pending-review flows into the process KG, and (flag-gated, later) surfaces approved neighbouring operations in search.
todos:
  - id: p1-approval-adr
    content: "Draft ADR-033 (UI flow knowledge, amends ADR-028 non-goal, new registry field, 2 env vars) and obtain explicit approval; record outcome in Notes"
    status: pending
  - id: p1-web-inventory
    content: "Inspect CoreComponents.Web, Escrow.Web, Fees.Web via local checkouts; record tech stack, routing style, and how each reaches API operations in Notes; pick pilot app and tiers"
    status: pending
  - id: p1-fixtures
    content: "Create synthetic fixtures tests/fixtures/webui/mvc_app and spa_app (layout, loop, unmatched call, lazy route); no PII or copied source"
    status: pending
  - id: p2-models
    content: "Add ui_flow.py dataclasses (UiPageFact, UiNavFact, UiOperationUse, UiGap, UiFactSet, UiFlowDraft) with unit tests"
    status: pending
  - id: p2-registry-field
    content: "Add RepositoryRecord.web_project_paths (default [], omitted when empty) + registry round-trip test"
    status: pending
  - id: p2-extractors
    content: "Implement extractors/web mvc, spa, lexical tiers and bounded calltrace per spec A1-A3; tiers enabled per p1 findings"
    status: pending
  - id: p2-adapter
    content: "Add analyzers/web_ui_adapter.py (Analyzer protocol, produces_api_surface=False, UiFactSet in AnalyzerResult.extra); unsupported tech -> tier none + gap"
    status: pending
  - id: p2-join
    content: "Implement join_operations against catalog operationKey (matched/ambiguous/unmatched) reusing route-identity normalisation"
    status: pending
  - id: p2-onboard-stage
    content: "Wire optional UI stage into onboard_repository behind EAKG__UI_FLOW_ENABLED (default false) with commit-keyed no-op"
    status: pending
  - id: p2-settings
    content: "Add EAKG__UI_FLOW_ENABLED to settings.py (approved env var only)"
    status: pending
  - id: p2-tests-gates
    content: "Tests for FR-002..FR-005, FR-009..FR-011, FR-015 on fixtures; mypy --strict; ruff"
    status: pending
  - id: p3-draft-flows
    content: "Implement draft_flows (entry pages, DFS, layout exclusion, prefix dedupe, fact_hash) and proposal JSON writer under data/process_kg/ui/"
    status: pending
  - id: p3-review
    content: "Implement ui_flow_review (list/approve/reject, reviewer attribution, rejected_flow_ids, apply_drift -> needs_reapproval/stale)"
    status: pending
  - id: p3-ontology-docs
    content: "Add UiPage/UiFlow terms + predicates to ontology; document in docs/CAPABILITY_ONTOLOGY.md and docs/PIPELINES.md"
    status: pending
  - id: p3-graph-load
    content: "Implement ui_flow_graph build/load to named graph ui_flow_<application_id>; approved flows only for UiFlow, facts for UiPage/nav"
    status: pending
  - id: p3-artifact-store
    content: "Persist ui_flow proposals/decisions beside existing process artifacts per ADR-027; verify hook in code"
    status: pending
  - id: p3-cli-gaps
    content: "Add ui-flow CLI commands (extract/list/approve/reject/load/gaps) and gap report output"
    status: pending
  - id: p3-tests-gates
    content: "Tests for FR-006..FR-009, FR-011, review state machine, RDF round-trip; quality gates; graphify update"
    status: pending
  - id: p4-approval-runtime
    content: "Confirm SSE__PROCESS_EXPAND_ENABLED approval and SC-004 target with eval owners; record in Notes"
    status: pending
  - id: p4-neighbors
    content: "Implement neighbors.expand one-hop SPARQL over approved UiFlow, cached, fail-open"
    status: pending
  - id: p4-search-integration
    content: "Add related_steps_block in Tools capability and third optional part in _assemble_search_parts behind flag; default off"
    status: pending
  - id: p4-eval-cases
    content: "Add multi-step question cases as a new case file; run baseline vs flag-on; never lower thresholds"
    status: pending
  - id: p4-tests-gates
    content: "Contract tests: flag off byte-identical, pending-only identical, approved shows related; quality gates"
    status: pending
  - id: p5-docs-graph
    content: "Update CONTEXT.md, TASKS.md, logs.md, decisions.md status; run graphify update ."
    status: pending
  - id: p5-pilot-review
    content: "Run pilot on chosen app, review flows with reviewers, record SC-001/SC-003 results in Notes"
    status: pending
isProject: false
---

# Web UI Process Pipeline — Implementation Plan

**Story**: [./web-ui-process-pipeline.story.md](./web-ui-process-pipeline.story.md)  
**Spec**: [./web-ui-process-pipeline.spec.md](./web-ui-process-pipeline.spec.md)

## Progress

| Phase | Focus | Todos |
|---|---|---|
| P1 | Approval, Web project inventory, fixtures | `p1-*` |
| P2 | Extraction: models, registry, adapter, join, onboard stage | `p2-*` |
| P3 | Flows, review, graph load, CLI, gaps | `p3-*` |
| P4 | Flag-gated related steps in search | `p4-*` |
| P5 | Docs, graph refresh, pilot review | `p5-*` |

MVP = P1 + P2 + P3 (reviewable report and approved graph). P4 is optional and separately gated.

---

## Phase 1 — Approval, inventory, fixtures

**Todos in this phase**: `p1-*`

### Goal

Unblock design with real knowledge of the Web projects and explicit approval for the architecture change.

### Work

1. **ADR-033** — draft per spec "Approval Gates"; request approval (`p1-approval-adr`). No code in P2+ until approved.
2. **Inventory** — from local checkouts (or `glab` clone), record for each `.Web` project: framework, routing, menu source, how API is called, auth attributes (`p1-web-inventory`). Update spec decisions 2 and open questions if findings differ.
3. **Fixtures** — synthetic MVC and SPA samples (`p1-fixtures`).

### Success criteria

- ADR-033 approved or revised.
- Inventory notes name tech and tiers to build; pilot app chosen.
- Fixtures cover loop, shared layout, unmatched call, lazy route.

### Notes

- Earlier `glab api` tree lookup on `CoreComponents.Web` returned project-not-found; use a local checkout or fix access before inventory.
- No Playwright or other new SDKs; provider_contracts lockstep not triggered.

---

## Phase 2 — Extraction

**Todos in this phase**: `p2-*`

### Goal

FR-001–FR-005, FR-009 (extraction side), FR-010, FR-011, FR-015, FR-016.

### Work

1. Models and registry field (`p2-models`, `p2-registry-field`).
2. Tiered extractors + calltrace (`p2-extractors`) and adapter (`p2-adapter`).
3. Operation join (`p2-join`).
4. Optional onboard stage, flag default off (`p2-onboard-stage`, `p2-settings`).
5. Tests and gates (`p2-tests-gates`).

### Success criteria

- Fixture run yields pages, nav, uses with provenance on every fact.
- Unsupported tech yields `tier=none` plus gap, never empty silence.
- Same commit rerun is a no-op.
- `mypy --strict`, ruff, and `scripts/check_project_refs.py` green.

### Notes

- Keep `produces_api_surface=False` so API coverage manifests do not change.
- `os.environ` only via `settings.py`.

---

## Phase 3 — Flows, review, graph

**Todos in this phase**: `p3-*`

### Goal

FR-006–FR-009, FR-012; SC-002, SC-003, SC-006.

### Work

1. Flow drafting and proposal writer (`p3-draft-flows`).
2. Review state machine and drift (`p3-review`).
3. Ontology + docs (`p3-ontology-docs`), RDF load (`p3-graph-load`), artifact store (`p3-artifact-store`).
4. CLI and gap report (`p3-cli-gaps`).
5. Tests and gates (`p3-tests-gates`).

### Success criteria

- All flows start `pending_review`; only approved flows reach `UiFlow` nodes.
- Source change flips approved flow to `needs_reapproval`; rejection survives unchanged rerun.
- RDF round-trips; named graph `ui_flow_<application_id>` replaced per run.
- Gap report lists unmatched, unsupported, and page-without-call items.

### Notes

- Flow data stays advisory; no code path reads it for authorization.

---

## Phase 4 — Related steps in search (optional, flag-gated)

**Todos in this phase**: `p4-*`

### Goal

FR-013, FR-014; SC-004, SC-005.

### Work

1. Approval for `SSE__PROCESS_EXPAND_ENABLED` and SC-004 target (`p4-approval-runtime`).
2. `neighbors.expand` (`p4-neighbors`).
3. Search integration (`p4-search-integration`).
4. Eval cases without touching thresholds (`p4-eval-cases`).
5. Contract tests (`p4-tests-gates`).

### Success criteria

- Flag off: search output byte-identical to baseline.
- Flag on with only pending/rejected flows: identical to baseline.
- Flag on with approved flow: labelled "Related steps" appended after direct matches.
- Added latency within spec budget; failure degrades to baseline.

### Notes

- ADR-028 listed capability-search ranking as a non-goal; ADR-033 must amend it before this phase.
- Direct matches are never reordered.

---

## Phase 5 — Docs, graph, pilot

**Todos in this phase**: `p5-*`

### Goal

Close the loop with real data and project hygiene.

### Work

1. `CONTEXT.md`, `TASKS.md`, `logs.md`, `decisions.md`; `graphify update .` (`p5-docs-graph`).
2. Pilot run, reviewer session, record SC-001 and SC-003 (`p5-pilot-review`).

### Success criteria

- Pilot results recorded in Notes; threshold decisions revisited with data.

### Notes

- Adjust SC-001/SC-004 targets only upward from pilot evidence; never relax existing eval gates.

---

## Dependencies between phases

```text
P1 approval + inventory -> P2 extraction -> P3 flows/review/graph -> P4 related steps
P1 fixtures -> P2 tests
P3 approved flows -> P4 (nothing to expand without approvals)
P3 + P4 -> P5 pilot
```

## Quality gates (each phase)

```powershell
uv run pytest projects/LoanOps.Eakg -q
uv run mypy --strict projects/LoanOps.Eakg
uv run ruff check projects/LoanOps.Eakg
uv run python scripts/check_project_refs.py
graphify update .
```

## Explicit non-goals (reminders)

- Browser crawl, screenshots, runtime analytics
- LLM-generated flows in the extractor
- Flow data as authorization input
- Lowering any eval threshold
- Mutating tool calls
