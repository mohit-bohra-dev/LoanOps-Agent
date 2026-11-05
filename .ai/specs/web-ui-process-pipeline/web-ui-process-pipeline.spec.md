# Web UI Process Pipeline — Technical Specification

**Feature Branch**: `feat/web-ui-process-pipeline`  
**Created**: 2026-11-05  
**Status**: Draft  
**Story**: [web-ui-process-pipeline.story.md](./web-ui-process-pipeline.story.md)  
**Plan**: [web-ui-process-pipeline.plan.md](./web-ui-process-pipeline.plan.md)

---

## Overview

Add a deterministic pipeline to `LoanOps.Eakg` that reads each application's **web front-end project** (`*.Web` deployables), recovers **screens**, **navigation links**, and **screen → backend operation uses**, matches the uses to the unified operation catalog (`operationKey = app|METHOD|path`), and emits **pending-review flow proposals** into the existing process KG (ADR-028). Approved flows can later be used to expand `search_sse_apis` results with neighbouring operations (flag-gated, off by default).

This spec covers the full path, but only Phases 1–3 are needed for a useful MVP (a reviewable report). Phase 4 (runtime expansion) is separately gated.

### Goals

- Extract screens, nav links, and screen→operation uses from Web projects (FR-002..FR-004, FR-005).
- Propose flows as `pending_review` and support approve/reject with re-approval on drift (FR-006..FR-008).
- Produce a gap report (FR-009, FR-010) and be idempotent per commit (FR-011).
- Optionally offer neighbouring operations from approved flows in search (FR-013, FR-014).

### Non-Goals

- Runtime user analytics, screenshots, browser crawling or running the app (FR-016).
- LLM-generated flows (ADR-029 boundary; extractor stays LLM-free).
- Re-extracting Confluence SOP processes (ADR-028 pipeline unchanged).
- Process data as authorization input (FR-012; ADR-028 invariant).
- Mutating tool calls (AGENTS.md rule).

### Approval Gates (AGENTS.md "Approval required before")

| Item | Why | Gate |
|------|-----|------|
| ADR-033 "UI flow knowledge" | Architecture change; amends ADR-028 non-goal "capability-search ranking" for Phase 4 | Human approval before Phase 2 |
| New registry field `web_project_path` | Schema change (YAML registry, additive, defaulted) | Included in ADR-033 |
| New env vars `EAKG__UI_FLOW_ENABLED`, `SSE__PROCESS_EXPAND_ENABLED` | AGENTS.md: new env vars need approval | Included in ADR-033; Phase 4 only needs the second |

No new external provider SDK: tree-sitter, rdflib, and the existing .NET analyzer are already used, so `provider_contracts` lockstep is not triggered. No Playwright / headless browser.

---

## Architecture

### System Context

```text
registry (repositories.yaml)
   web_project_path ─┐
                     v
git clone/fetch ──> WebUiAdapter (Analyzer protocol)
                     │  detect() → tier select
                     │  extract() → UiFacts
                     v
              UiFactSet {pages, nav, uses, gaps}
                     │
        join ──> RepoInterface.operations + ApiIndex catalog (operationKey)
                     │
          ┌──────────┴───────────┐
          v                      v
   UiFlow draft builder     Gap ledger
   (nav-ordered flows)      (unmatched / unsupported)
          │
   proposal JSON (pending_review)  ──> review CLI (approve/reject)
          │ approved only
          v
   RDF build ──> named graph `ui_flow_<application_id>` (GraphDB)
          │ Phase 4 only, flag-gated
          v
   expand_neighbors(op_keys) ──> search_sse_apis "Related steps" block
```

### Component Overview

| Component | Responsibility | Location | New / Modified |
|-----------|----------------|----------|----------------|
| `RepositoryRecord.web_project_paths` | Declare Web projects per app | `projects/LoanOps.Eakg/packages/eakg/registry.py` | Modified |
| `WebUiAdapter` | Analyzer: detect tier, extract UiFacts | `.../eakg/analyzers/web_ui_adapter.py` | New |
| Extractors (`mvc`, `spa`, `lexical`) | Tier-specific page / nav / call extraction | `.../eakg/extractors/web/` | New |
| `ui_flow.py` | Dataclasses, operation join, flow drafting | `.../eakg/ui_flow.py` | New |
| `ui_flow_graph.py` | UiFacts + approved flows → RDF, named graph load | `.../eakg/ui_flow_graph.py` | New |
| `ui_flow_review.py` | Proposal store, approve/reject, drift detection | `.../eakg/ui_flow_review.py` | New |
| Ontology additions | `UiPage`, `UiFlow` + predicates | `.../eakg/ontology.py`, `docs/CAPABILITY_ONTOLOGY.md` | Modified |
| `onboard.py` | New optional stage after API extract | `.../eakg/onboard.py` | Modified |
| EAKG CLI | `ui-flow extract|list|approve|reject|load` | `.../eakg/__main__.py` (existing CLI module) | Modified |
| `neighbors.py` | One-hop SPARQL expansion over approved flows | `.../eakg/neighbors.py` | New (Phase 4) |
| Tools capability block | `related_steps_block()` | `projects/LoanOps.Tools/packages/tools/capability.py` | Modified (Phase 4) |
| `_assemble_search_parts` | Third optional part "Related steps" | `projects/LoanOps.Sse/packages/sse/tools.py` | Modified (Phase 4) |

Exact module names for the CLI entry point and ontology constants are confirmed in `p2-*` todos by reading the current files; the locations above follow the existing package layout.

### Data Flow

1. `onboard_repository` clones/fetches (existing), runs API adapters (existing), then — if `EAKG__UI_FLOW_ENABLED` and the record has `web_project_paths` — runs `WebUiAdapter.extract` per path.
2. Adapter returns a `UiFactSet` (pages, nav links, operation-use candidates, gaps).
3. `ui_flow.join_operations` maps each candidate to a catalog `operationKey` via the same route-identity normalisation used for cross-app joins; unmatched → gap.
4. `ui_flow.draft_flows` builds flows from nav edges; writes `data/process_kg/ui/<application_id>.proposal.json` with `review_status = pending_review`.
5. Reviewer runs the CLI to list/approve/reject. Decisions are persisted in the proposal file (and artifact store, see below).
6. `ui_flow_graph.load` uploads **approved** flows (and all pages/nav facts as discovered) to named graph `ui_flow_<application_id>`.
7. Phase 4: `search_sse_apis` calls `neighbors.expand(op_keys)` when enabled.

---

## Technical Decisions

### Decision 1: Static extraction, not a browser crawl

**Context**: Need screens + calls per page, with no credentials, no PII, runnable in CI.

**Options Considered**:
1. Static analysis of source — deterministic, offline, no auth, no PII; misses fully dynamic routes.
2. Headless-browser crawl against a running environment — sees real DOM and XHR; needs a running env, credentials, may touch customer data, flaky.
3. LLM reads source and writes flows — flexible; non-deterministic, violates ADR-029 core boundary.

**Decision**: Option 1.

**Rationale**: FR-015/FR-016 and NFR-002/003 rule out 2 and 3. Dynamic gaps are surfaced in the gap ledger rather than guessed.

**Trade-offs**: Lower recall on data-driven menus; accepted and measured via SC-001.

### Decision 2: Tiered extraction (inventory decides, Phase 1 confirms)

**Context**: Web tech is unknown today (MVC/Razor, Blazor, or SPA are all plausible; the registry only knows project names).

**Options Considered**:
1. One extractor for one assumed stack — fast; wrong if assumption is wrong.
2. Tier A `mvc` (controllers + views), Tier B `spa` (tree-sitter JS/TS routes + HTTP calls), Tier C `lexical` fallback (regex over views/code for known patterns) — handles unknowns.
3. Wait for a full Roslyn extension — cleanest for C#; external .NET tool change is the riskiest dependency.

**Decision**: Option 2, with tiers enabled by Phase 1 inventory findings. Tier A uses the existing Roslyn-derived `RepoInterface.proxies` and `ApiOperationFact` names as the matching vocabulary; it only uses lexical C#/view scanning unless Phase 1 shows Roslyn extension is worth it.

**Rationale**: Reuses the repo's existing surface (`RepoInterface`, `ProxyFact`, `RouteCompositionFact`, tree-sitter adapter) and avoids committing to an unverified stack.

**Trade-offs**: Lexical tier has lower precision (lower confidence score, flagged in evidence).

### Decision 3: UiPage as evidence layer, process flow as review layer

**Context**: ADR-028 already defines `BusinessProcess/ProcessStep/Transition/CapabilityLink` with review lifecycle.

**Options Considered**:
1. Write UI facts straight into `ProcessStep` — simple; conflates "found in code" with "business process" and bypasses review semantics.
2. Separate `UiPage` facts (evidence) and derive **flow drafts** that reuse the process review lifecycle and `CapabilityLink` shape — keeps facts and curated meaning apart.
3. New independent flow ontology — duplicates review/validation.

**Decision**: Option 2. `UiPage` and `navigatesTo`/`callsOperation` are raw facts; `UiFlow` reuses process status predicates (`hasReviewStatus`, `sourceStatus`) and `CapabilityLink` semantics (`operationKey`, `linkStatus`).

**Rationale**: FR-006/FR-008 mirror ADR-028 lifecycle; reusing it avoids a second validator.

**Trade-offs**: Two layers to explain; documented in `docs/CAPABILITY_ONTOLOGY.md`.

### Decision 4: Separate named graph per application

**Decision**: `ui_flow_<application_id>` (e.g. `ui_flow_corecomponents`), independent of `process_account_maintenance`.

**Rationale**: Replace-per-app on re-run without touching SOP processes; supports staleness and rollback.

### Decision 5: Advisory-only, flag-gated runtime

**Decision**: No change to tool routing or authorization. Phase 4 only appends a labelled "Related steps" block; default off via `SSE__PROCESS_EXPAND_ENABLED=false`.

**Rationale**: FR-012, FR-014, NFR-004, SC-005.

---

## Data Models

Python dataclasses (repo is Python; `mypy --strict`). Location: `projects/LoanOps.Eakg/packages/eakg/ui_flow.py`.

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal

from packages.eakg.models import Evidence

NavKind = Literal["menu", "link", "button", "redirect", "form_post"]
MatchStatus = Literal["matched", "unmatched", "ambiguous"]
ReviewStatus = Literal["pending_review", "approved", "rejected", "needs_reapproval"]
GapKind = Literal[
    "unmatched_call", "page_without_calls", "unsupported_tech",
    "dynamic_route", "unresolved_helper", "orphan_operation",
]


@dataclass
class UiPageFact:
    page_id: str            # f"{application_id}:{route_key}", stable
    application_id: str
    route: str              # normalised: "/escrow/{id}"
    label: str              # nav text or view title; "" if unknown
    source_file: str
    requires_auth: bool | None  # None = unknown
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class UiNavFact:
    from_page: str          # page_id
    to_page: str            # page_id
    kind: NavKind
    order: int | None       # position in menu / source order; None if unordered
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class UiOperationUse:
    page_id: str
    operation_key: str | None   # "app|METHOD|path" once matched
    raw_call: str               # proxy method / url template as seen
    match: MatchStatus
    confidence: float           # tier A/B high, tier C lowered
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class UiGap:
    kind: GapKind
    page_id: str | None
    detail: str
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class UiFactSet:
    application_id: str
    commit_sha: str
    tier: Literal["mvc", "spa", "lexical", "none"]
    pages: list[UiPageFact] = field(default_factory=list)
    nav: list[UiNavFact] = field(default_factory=list)
    uses: list[UiOperationUse] = field(default_factory=list)
    gaps: list[UiGap] = field(default_factory=list)


@dataclass
class UiFlowDraft:
    flow_id: str            # sha1(application_id + ordered page_ids)[:12]
    application_id: str
    page_ids: list[str]     # ordered entry → leaf
    operation_keys: list[str]
    review_status: ReviewStatus = "pending_review"
    fact_hash: str = ""     # hash of contributing pages/nav/uses; drift detector
    reviewer: str = ""
    reviewed_at: str = ""
```

### Proposal file (`data/process_kg/ui/<application_id>.proposal.json`)

```json
{
  "schema": 1,
  "application_id": "corecomponents",
  "commit_sha": "<sha>",
  "extractor_version": "web-ui-1",
  "tier": "mvc",
  "flows": [
    {
      "flow_id": "ab12cd34ef56",
      "page_ids": ["corecomponents:/loan/{id}", "corecomponents:/loan/{id}/escrow"],
      "operation_keys": ["escrow|GET|/api/escrow/{loanNumber}"],
      "review_status": "pending_review",
      "fact_hash": "..."
    }
  ],
  "gaps": []
}
```

Decisions persist in this file (`reviewer`, `reviewed_at`, `review_status`). Rejected `flow_id`s are kept in a `rejected_flow_ids` list keyed by `flow_id` + `fact_hash` so unchanged source does not re-propose them (FR-008).

### RDF terms (namespace `lo:` = `https://loanops.local/ontology/`)

| Term | Kind | Notes |
|------|------|-------|
| `lo:UiPage` | class | one per `UiPageFact` |
| `lo:UiFlow` | class | one per **approved** flow |
| `lo:routePath`, `lo:pageLabel`, `lo:requiresAuth` | datatype props | literals only; no UI text bodies |
| `lo:navigatesTo` | UiPage → UiPage | with reified `lo:navOrder`, `lo:navKind` via blank-node `lo:NavLink` if order needed |
| `lo:callsOperation` | UiPage → APIOperation (by `operationKey` literal on a `CapabilityLink`-style node) | reuses `lo:operationKey`, `lo:linkStatus` |
| `lo:hasFlowPage` | UiFlow → UiPage (ordered via `lo:ordinal`) | |
| `lo:hasReviewStatus`, `lo:sourceStatus` | existing predicates | reused |

`docs/CAPABILITY_ONTOLOGY.md` documents the additions in `p3-ontology-docs`.

### Registry field

`RepositoryRecord.web_project_paths: list[str]` (YAML key `web_project_paths`, default `[]`, omitted when empty so existing registry files stay byte-stable). Replaces any need to infer `.Web` from `deployables`.

---

## Algorithms

### A1. Page discovery

- **Tier A (mvc)**: for each controller in a Web project that returns a view (`View()` / `return View(...)` / `[Route]`), compute route from attribute routes or the conventional `/{controller}/{action}/{id?}` pattern, normalise route params to `{name}`. Label from `ViewData["Title"]` / `<title>` / nav text.
- **Tier B (spa)**: tree-sitter parse of route tables (`path:`/`<Route path=`/`createBrowserRouter`) in `.ts/.tsx/.js`; component name → file link; lazy routes tracked as `dynamic_route` gap if path not statically known.
- **Tier C (lexical)**: regex over `.cshtml/.razor/.html` for `@page "..."`, `asp-controller/asp-action`, `href="/..."`.

Complexity: O(total source bytes); files under skip dirs (`node_modules`, `bin`, `obj`, `dist`) excluded using `_under_skip` from `analyzers/protocol.py`.

### A2. Navigation edges

```text
for each layout/partial/menu file and each page file:
    for each link target (asp-action, Url.Action, href, routerLink, <Link to>, redirect call):
        resolve target to page_id via route table (exact, then param-normalised match)
        if resolved: add UiNavFact(from_page=file's page(s) or "layout" fan-out,
                                   to_page, kind, order=source index)
        else: gap dynamic_route
```

Shared layouts: a layout's links are attached to a synthetic `layout:<name>` page; flow drafting excludes layout fan-out edges from flows (prevents the "everything links to everything" explosion) but keeps them as `menu` facts.

### A3. Screen → operation use (bounded call trace)

```text
for each page entry point (controller action | component | script module):
    BFS call graph with depth <= 4, visited set (cycle-safe), node cap 200
    at each node, test for outbound call signature:
        - proxy / client method whose class ∈ RepoInterface.proxies  (tier A)
        - http call with url template (fetch/axios/HttpClient)       (tier B/C)
    record raw_call + evidence
join: normalise raw_call → (METHOD, path template) → operationKey candidates
    exactly 1 candidate  → matched
    >1 candidate         → ambiguous (gap)
    0                    → unmatched (gap unmatched_call)
generic helper (call target is parameterised wrapper) → gap unresolved_helper
```

Confidence: A=0.9 matched exact, B=0.8, C=0.5 (capped). Evidence `detector_id = "web_ui_<tier>"`.

### A4. Flow drafting

```text
graph G = pages as nodes, nav edges (excluding layout fan-out) as directed edges
entry pages = in-degree 0 or pages named in menu facts
for each entry page: DFS with visited set (cycles cut), path length <= 8
    emit path if it contains >= 2 pages and >= 1 matched operation
dedupe: flow_id = sha1(application_id + "|".join(page_ids))[:12]
        drop flows whose page_ids are a strict prefix of a longer flow
operation_keys = ordered unique matched keys along the path
fact_hash = sha1 of sorted (page, nav, use) tuples contributing to the flow
```

Complexity: O(V + E) per entry with depth cap; V is pages per app (hundreds).

### A5. Drift detection (re-approval)

On re-run with a new commit: recompute each flow's `fact_hash`. If a persisted approved flow's hash changed → `needs_reapproval`; if flow disappeared → `sourceStatus = stale`. Same commit → early return "no change" before extraction (FR-011), keyed by `(application_id, commit_sha, extractor_version)`.

### A6. Runtime expansion (Phase 4)

```sparql
PREFIX lo: <https://loanops.local/ontology/>
SELECT DISTINCT ?neighborKey ?dir ?flow WHERE {
  VALUES ?hit { <op-key literals> }
  ?flow a lo:UiFlow ; lo:hasReviewStatus "approved" ; lo:hasFlowPage ?p1, ?p2 .
  ?p1 lo:ordinal ?o1 ; lo:callsOperation/lo:operationKey ?hit .
  ?p2 lo:ordinal ?o2 ; lo:callsOperation/lo:operationKey ?neighborKey .
  FILTER(?o2 = ?o1 + 1 || ?o2 = ?o1 - 1)
  BIND(IF(?o2 > ?o1, "next", "previous") AS ?dir)
}
LIMIT 20
```

`related_steps_block()` formats up to 5 neighbours: `Related steps (approved application flow ...): after X → Y`. Never calls tools, never changes ranking of direct matches (appended after OpenAPI and EAKG blocks).

---

## Interfaces

### CLI (PowerShell)

```powershell
uv run python -m packages.eakg ui-flow extract --application corecomponents --local-path D:\src\CoreComponents
uv run python -m packages.eakg ui-flow list --application corecomponents --status pending_review
uv run python -m packages.eakg ui-flow approve <flow_id> --reviewer <name>
uv run python -m packages.eakg ui-flow reject <flow_id> --reviewer <name> --reason "..."
uv run python -m packages.eakg ui-flow load --application corecomponents
uv run python -m packages.eakg ui-flow gaps --application corecomponents
```

The module entry (`python -m packages.eakg`) matches how other EAKG commands are run; confirm in `p2-cli`.

### Internal Python API

```python
class WebUiAdapter:           # satisfies analyzers.protocol.Analyzer
    id = "web_ui"; version = "1"
    languages = frozenset({"csharp", "javascript", "typescript"})
    produces_api_surface = False
    fatal = False
    def detect(self, repo: Path) -> float: ...
    def extract(self, repo: Path, *, repository_id: str, application_id: str,
                commit_sha: str, api_project_path: str = "",
                dest: Path | None = None) -> AnalyzerResult: ...
        # UiFactSet returned in AnalyzerResult.extra["ui_facts"]

def join_operations(facts: UiFactSet, catalog_keys: Collection[str]) -> UiFactSet: ...
def draft_flows(facts: UiFactSet) -> list[UiFlowDraft]: ...
def apply_drift(prev: list[UiFlowDraft], new: list[UiFlowDraft]) -> list[UiFlowDraft]: ...
```

`produces_api_surface = False` keeps `select_analyzers` / coverage manifest unchanged for the API path; `onboard` invokes the adapter explicitly in its own stage (`select_analyzers` is not extended with a UI result).

---

## File Structure

New:

```text
projects/LoanOps.Eakg/packages/eakg/
  analyzers/web_ui_adapter.py
  extractors/web/__init__.py
  extractors/web/mvc.py
  extractors/web/spa.py
  extractors/web/lexical.py
  extractors/web/calltrace.py
  ui_flow.py
  ui_flow_graph.py
  ui_flow_review.py
  neighbors.py                      # Phase 4
  tests/test_ui_flow_models.py
  tests/test_web_ui_adapter.py
  tests/test_ui_flow_join.py
  tests/test_ui_flow_draft.py
  tests/test_ui_flow_review.py
  tests/test_ui_flow_graph.py
  tests/test_neighbors.py           # Phase 4
  tests/fixtures/webui/
    mvc_app/    (synthetic controllers + views)
    spa_app/    (synthetic route table + fetch calls)
data/process_kg/ui/                 # proposals (gitignored? no — mirrors existing process_kg proposals)
```

Modified:

```text
registry.py, onboard.py, __main__.py (CLI), ontology.py (terms), gap_ledger.py,
projects/LoanOps.Tools/packages/tools/capability.py          # Phase 4
projects/LoanOps.Sse/packages/sse/tools.py                   # Phase 4
projects/LoanOps.Common/packages/common/settings.py          # new env vars (approval-gated)
docs/PIPELINES.md, docs/CAPABILITY_ONTOLOGY.md, decisions.md (ADR-033), TASKS.md, logs.md
```

Fixtures are synthetic (no PII, no copied proprietary source).

---

## Edge Cases

| Case | Handling | Req |
|------|----------|-----|
| Shared layout links on every page | Synthetic `layout:` node; excluded from flow edges | FR-003 |
| Auth-only / role-only pages | `requires_auth` captured from attributes when static; else `None`; flows not filtered | Open Q4 |
| Generic helper hides operation | `unresolved_helper` gap, no guessed operation | FR-009 |
| Data-driven / lazy routes | `dynamic_route` gap | FR-009 |
| Nav loop A→B→A | DFS visited set cuts loop | FR-003 |
| Operation used by many pages | Appears in multiple flows; dedupe by `flow_id`; no cross-flow merge | FR-004 |
| Ambiguous operation match | `ambiguous` status, gap, never auto-linked | FR-004 |
| Unsupported tech | `tier = none`, `unsupported_tech` gap with file extensions found | FR-010 |
| Partial / inaccessible checkout | `access_check` result reused; run fails visibly, no partial publish | NFR-003 |
| Feature-toggled page | Captured as normal page; label/flag noted if statically visible; reviewer decides | Edge case |
| Shared-library pages | Attributed to the application whose Web project referenced them (project path), not the library | Edge case |
| Rejected flow, source unchanged | `rejected_flow_ids` match on `flow_id + fact_hash` → not re-proposed | FR-008 |
| Same commit rerun | Early return "no change" | FR-011 |

---

## Security Considerations

- Read-only clone/fetch via existing `gitops` and `access_check`; no new credentials.
- Outputs hold route templates, labels, file paths, line ranges, operation keys. No source snippets, no config values, no secrets; config keys referenced by name only (`ServiceUrlFact` pattern).
- Labels are truncated to 120 chars and stripped of control chars; no runtime data.
- Graph stores no SOP or UI body text, matching ADR-028 "short labels only".
- Flow data never reaches authorization code paths (FR-012); Phase 4 block is read-only text.
- `uv` only; no new third-party SDKs; `mypy --strict`; no `os.environ` use outside `settings.py`.

---

## Performance Considerations

- Extraction budget: 10 min per Web project (NFR-001). Single pass file walk, tree-sitter parsing capped per file (skip files > 1 MB), call trace depth 4 / 200 nodes.
- Idempotence: commit-keyed early exit (SC-006).
- Phase 4: one SPARQL per search, cached by `(sorted op_keys, graph_version)`; target ≤ 100 ms p95 added latency; failure degrades silently to current behaviour (log warning).

---

## Testing Strategy

| Level | Scope | Requirements covered |
|-------|-------|----------------------|
| Unit | models, route normalisation, join (matched / ambiguous / unmatched), flow drafting (loop, layout fan-out, prefix dedupe), drift (hash change, same commit, stale) | FR-003, FR-004, FR-008, FR-011 |
| Unit | adapter detect/tier selection on fixtures; unsupported tech → `none` + gap | FR-002, FR-010 |
| Unit | review state machine (pending→approved/rejected, needs_reapproval, remembered rejection) | FR-006..FR-008 |
| Integration | `onboard_repository(local_path=fixtures/mvc_app)` produces proposal with provenance on every fact | FR-005, FR-009, SC-002 |
| Integration | RDF build → parse back with rdflib; named graph id; approved-only flows loaded | FR-006, FR-013 |
| Contract | Phase 4: flag off ⇒ `handle_search_sse_apis` output byte-identical to baseline; flag on + pending-only ⇒ identical; flag on + approved ⇒ related block | FR-013, FR-014, SC-005 |
| Privacy | scan outputs of fixtures for secret-like strings and snippet content | FR-015, NFR-003 |
| Eval | Multi-step question set added as a **new** case file; existing thresholds untouched | SC-004, NFR-004 |

Commands (PowerShell):

```powershell
uv run pytest projects/LoanOps.Eakg -k "ui_flow or web_ui or neighbors" -q
uv run pytest projects/LoanOps.Sse projects/LoanOps.Tools -q
uv run mypy --strict projects/LoanOps.Eakg
uv run python scripts/check_project_refs.py
```

### Test Data

Synthetic fixtures only: `tests/fixtures/webui/mvc_app` (3 controllers, 1 shared layout, 1 proxy call, 1 unmatched call, 1 loop) and `spa_app` (route table, 2 `fetch` calls, 1 lazy route).

---

## Rollout and Compatibility

- Additive registry field; defaults keep current files unchanged.
- `EAKG__UI_FLOW_ENABLED=false` default: `onboard_repository` skips the stage entirely.
- `SSE__PROCESS_EXPAND_ENABLED=false` default: search output unchanged.
- Rollback: delete named graph `ui_flow_<application_id>`; proposal files are standalone.
- Pilot: one application, chosen after Phase 1 inventory (candidates: CoreComponents, Escrow, Fees — each already lists a `.Web` deployable).

---

## Risks

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Web tech differs from assumption | Extractor rewrite | Phase 1 inventory + tiering; ADR gate before build |
| Calls routed through generic helpers | Low match rate (SC-001) | Gap ledger shows it; consider Roslyn extension as a follow-up decision |
| Review fatigue (too many flows) | Flows never approved | Cap flow length; prefix-dedupe; entry-page grouping; report counts first |
| Operation-key mismatch with catalog | False unmatched | Reuse existing route-identity normalisation; fixture covering path-param naming |
| Phase 4 adds noise to answers | Eval regression | Flag default off; approved-only; neighbour cap 5; contract test |
| Private repo access (earlier project-tree lookup returned not found) | Cannot inspect | Use `local_path` checkout; `access_check` surfaced in report |

---

## Open Technical Questions

1. Web stack and how it reaches the API (generated proxy package, typed `HttpClient`, JS `fetch`)? Resolved in `p1-web-inventory`.
2. Is the existing Roslyn analyzer extensible with a Web-project mode, or is lexical scanning sufficient for tier A? Decided after inventory.
3. Reviewer surface: CLI first (assumed) vs web app screen.
4. Exact artifact-store hook for persisting `ui_flow` proposals beside existing `process` artifacts (ADR-027); verified in `p3-artifact-store`.
