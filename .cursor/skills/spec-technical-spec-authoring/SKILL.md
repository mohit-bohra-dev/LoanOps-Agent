---
name: spec-technical-spec-authoring
description: >-
  Standards for authoring `[featureName].spec.md` — the HOW layer of a spec.
  Covers the technical section catalog (architecture and data flow, algorithms
  with pseudocode and complexity, data model and validation, API/function
  signatures, technical decisions with alternatives and consequences, file
  structure, implementation details, integration points, edge cases and error
  handling, security, performance, testing strategy, configuration,
  dependencies), the depth bar that makes each section buildable, the
  HOW-belongs-here boundary (code, schemas, and implementation detail live in
  the spec, not the story), and how the spec links back to the story and feeds
  the plan. Use when creating, drafting, updating, or reviewing a technical spec
  / spec.md / the HOW layer of a feature specification.
promp:
  package: "spec"
  version: "2.3.0"
  environment: "development"
  prompVersion: "1.0.1-beta.161"
  skill: "technical-spec-authoring"
---

# Technical Spec Authoring

Standards for writing `[featureName].spec.md` — the **HOW** layer of a spec. The spec is read by architects and implementers and by the plan and review flows that build on it. It is the home for everything the story deliberately excludes: architecture, data models, algorithms, code examples, schemas, and the technical decisions behind them.

This skill covers the authoring judgment for the spec's sections. The `spec-artifact-model` skill defines the artifact set, naming, and cross-link rules; `story-authoring` covers the WHAT/WHY layer; `spec-plan-format` covers the plan. The canonical section structure lives in `../../templates/spec.md.template` — this skill is the standard for filling it well, not a re-listing of every placeholder.

## When to Use

- Writing a new `[featureName].spec.md` against a story
- Adding or deepening a technical section on an existing spec
- Reviewing a spec for buildability, depth, and boundary violations
- Deciding how much technical detail a section needs before implementation can start

## The HOW Boundary

The spec answers one question: **how** will we build this. Everything the `story-authoring` skill forbids in the story belongs here and is required here:

- Code examples and pseudocode
- Data structures, database schemas, table/column names, JSON field layouts
- File paths, function signatures, class and module names
- Specific technologies, libraries, and services
- Algorithms, complexity analysis, data structures

Do not restate the story's requirements as if they were the design. The spec **cites** the story's stable IDs (`FR-`, `NFR-`, `SC-`) and then specifies the mechanism that satisfies them. A spec section that merely repeats "the system must expire sessions after 30 minutes" has not designed anything — it must say *how* (e.g., a Redis key with a 30-minute TTL). The boundary runs in one direction: user-observable requirement in the story → concrete mechanism in the spec.

For the story side of this boundary (and the borderline cases), see `story-authoring`. Do not re-derive it here.

## The Depth Bar

The single test that governs every section:

> Could a competent engineer who was **not** in the design conversation implement this section as written — and would two such engineers produce substantially the same thing?

If no, the section is underspecified. A spec is not a summary of intent; it is enough design that implementation is transcription, not invention. The depth bar is what separates an operational spec from a shallow one, and it is the most common failure: sections that gesture at an approach instead of specifying it.

Section-specific depth requirements — the ones an author will otherwise skip:

| Section | What "operational" requires (beyond a label) |
|---|---|
| Architecture | A **data-flow**, not just a box diagram. Each component named with its responsibility and its interface. |
| Algorithms & Logic | **Pseudocode AND** time/space **complexity**. A prose paragraph describing the idea is not a spec. |
| Data Model | **Validation rules and relationships**, not just a field list. Schema only if the feature persists data. |
| Technical Decisions | **Rationale + alternatives considered (with why-not) + consequences (pros/cons)**. A decision with no alternatives is an assertion. |
| File Structure | **New files vs. modified files** separated; for each, what it does or what changes. |
| Edge Cases & Error Handling | Each edge case **paired with its technical handling** (code or precise mechanism), plus error types and recovery. |
| Security / Performance | Tied to the story's `NFR-`/`SC-` IDs; turn each user-observable constraint into a concrete mechanism and, for performance, a metric + target. |
| Testing Strategy | Concrete scenarios and coverage targets **mapped to the story's `FR-`/`SC-` IDs**, not "we'll write unit tests." |

After drafting a section, re-read it against the test above. If an implementer would still have to make a design decision you left out, that decision is the spec's job — make it.

## Section Catalog

Author the sections the feature needs, in template order. The template is the exhaustive structure; this is which sections apply and when.

| Section | When | Notes |
|---|---|---|
| Architecture (high-level + component design + data flow) | Always | The orienting section. Include the data-flow. |
| Algorithms & Logic | When the feature has non-trivial logic | If the feature is pure plumbing, say so explicitly rather than inventing an algorithm. |
| Data Model | Always | Structures + validation; DB schema only if data is persisted. |
| API Design | When the feature exposes an interface | Endpoints if it serves HTTP; function signatures for the public surface either way. |
| Technical Decisions | Always | At least the decisions a reviewer would otherwise question. |
| File Structure | Always | New vs. modified, with the purpose of each. |
| Implementation Details | Always | Module-by-module; core functions with real signatures. |
| Integration Points | When the feature touches another system/service | Method, auth, and error handling per integration. |
| Edge Cases & Error Handling | Always | Resolves the edge-case **questions** the story raised. |
| Security Considerations | Always | State "no new surface" explicitly if that is genuinely true. |
| Performance Considerations | Always | Tie to story `NFR-`/`SC-`; name metrics and targets. |
| Testing Strategy | Always | Unit / integration / performance, with coverage targets. |
| Configuration | When the feature adds config or environment variables | Document type, required, default. |
| Dependencies | Always | External libraries (with versions + rationale) and internal dependencies. |
| Deployment / Migration / Open Technical Questions / References | When applicable | Template provides these; include only with real content. Mark unresolved items in Open Technical Questions rather than guessing. |

Omit a non-applicable optional section rather than leaving it empty — an empty section is noise. When the feature genuinely has nothing for an "Always" section (e.g., no new security surface), state that conclusion explicitly so a reviewer knows it was considered, not forgotten.

When you need a concrete model for how deep a specific section should go, read `references/spec-section-examples.md` for paired good/shallow examples with rationale.

## Worked Examples

**Technical Decision — shallow vs. operational.**

Shallow (an assertion):

```markdown
### Decision: Session storage
We will store sessions in Redis.
```

Operational (a decision a reviewer can trust):

```markdown
### Decision: Session storage — Redis with TTL
**Context**: NFR-004 requires sessions to expire after 30 minutes of inactivity across 3 app instances.
**Decision**: Store each session under `sessions:<id>` in Redis with a 30-minute TTL refreshed on each request.
**Alternatives considered**:
1. In-process memory — rejected: does not survive restarts or share across instances.
2. Postgres row + cron sweep — rejected: adds write load and a sweep job for behavior Redis gives natively via TTL.
**Consequences**: + expiry is free and atomic; + horizontally shared. − adds Redis as a runtime dependency (see Dependencies).
```

**Algorithm — prose vs. spec.** "We deduplicate orders by checking recent ones" is prose. A spec gives the pseudocode **and** the complexity so the implementer picks the right structure:

```
key = hash(customerId, cartFingerprint)
if store.get(key): return store.get(key)   # prior result, within 60s window
store.setex(key, 60s, placeOrder(...))     # O(1) keyed lookup vs O(n) scan
```

**Edge case — answered, not just listed.** The story asks *"What happens when a user submits the same order twice within seconds?"* The spec answers it with a mechanism: an idempotency key on submit, the dedup window, and what the second request returns.

## Cross-References

The spec does not stand alone — link it per the `spec-artifact-model` cross-link rules:

- **Back to the story** for requirements context: link `./[featureName].story.md` (or the external story location / Jira issue when the story source is external). Cite requirements by their stable IDs (`FR-007`, `NFR-004`, `SC-002`) rather than paraphrasing them.
- **Forward to the plan**: the spec is the technical source the plan's phases draw from. Make decisions, file changes, and function signatures concrete enough that `[featureName].plan.md` can lift them into phased tasks without re-designing. (Plan structure: `spec-plan-format`.)

Keep `{{#if storyPath}} … {{else}} … {{/if}}` rendering intact when filling the template — it is the switch between a local story link and an external story reference.

## Pre-Handoff Check

Before treating a spec as ready for planning:

- [ ] Every applicable section meets its depth bar — an outside engineer could implement it without re-deriving decisions.
- [ ] Algorithms include pseudocode and complexity; data structures include validation rules.
- [ ] Each technical decision states rationale, alternatives with why-not, and consequences.
- [ ] File Structure separates new from modified files, each with a purpose.
- [ ] Every story edge-case question is answered with a technical mechanism.
- [ ] Security and performance sections tie to the story's `NFR-`/`SC-` IDs (or explicitly state no new surface).
- [ ] Testing scenarios map to the story's `FR-`/`SC-` IDs with coverage targets.
- [ ] Requirements are cited by stable ID, not restated as design.
- [ ] No `{{placeholder}}` markers remain; cross-links resolve.

If any check fails, fix it before the plan is authored against the spec.

## Invocation Contract

This skill is used two ways. Most callers load it as the **standard** for filling spec
sections while doing something else (creating a spec, reviewing a design). A caller can
also invoke it as a **complete authoring run** — authoring or revising a feature's whole
spec artifact set in one isolated pass. That run is what this contract specifies.

`mode` is the distinguishing input and is **required**:

| `mode` | Operation |
|---|---|
| `create` | Author a new spec artifact set from an approved story. |
| `revise` | Apply a spec-design review's Required Changes to an existing spec. |

The run happens in a **fresh, isolated context** — that is its whole value. It is the
authoring stage an orchestrator loops through a design-quality gate
(`@./.cursor\skills\spec-spec-design-review-rubric\SKILL.md`): author → review → revise until the design passes.

### Inputs

| Input | Type | Required | Meaning |
|---|---|---|---|
| `mode` | `create` \| `revise` | no (default `create`) | Which operation to run. `revise` additionally requires `reviewPath`. |
| `featureName` | string | yes (ask when absent) | Kebab-case feature name; names the spec directory and the `[featureName].*` artifacts. |
| `specDirectory` | string | no | Directory for the spec. Defaults to `.ai/specs/<featureName>`. Always the **code repo**, never a planning workspace. |
| `storySource` | string | no | The approved story — a story **file path** or a Jira **issue key**, detected by shape. External sources are *referenced, not copied*, so no local `[featureName].story.md` is generated. Omit for a local story. |
| `description` | string | no | One-line feature description, used when a local story is generated in `create`. |
| `storyContext` | string | no | The requirements basis the caller already gathered, so it need not be re-derived from the source. |
| `reviewPath` | string | **yes when `mode: revise`** | The spec-design review write-up whose Required Changes are the authoritative change set. |

### Procedure

1. **Pre-flight.** Resolve the spec directory. When `mode: revise` and `reviewPath` is
   missing or empty, return `SPEC_INCOMPLETE` and stop — author nothing. When
   `featureName` and `specDirectory` are both absent, ask which feature to author and stop.
2. **Load the authoring context.** Operate as `@./.cursor\agents\spec-author.md`, whose definition is
   the complete operational model for the run, along with the skills it depends on:
   this skill, `@./.cursor\skills\spec-spec-artifact-model\SKILL.md`, and `@./.cursor\skills\spec-spec-plan-format\SKILL.md`.
3. **`mode: create`.** Run `@./.cursor\skills\spec-spec-artifact-model\SKILL.md` (`mode: create`) for
   scaffolding, template rendering, and the local-vs-external story switch. **Then**
   deepen `[featureName].spec.md` to the depth bar above and `[featureName].plan.md` per
   `@./.cursor\skills\spec-spec-plan-format\SKILL.md`. Surface a `SPEC_EXISTS` from the scaffold as an error —
   the caller decides whether to resume or re-author.
4. **`mode: revise`.** Read the `reviewPath` write-up and treat its **Required Changes**
   (must-fix first, then should-fix) as the authoritative change set. Apply each change to
   the artifact and section it names. Touch only what the Required Changes require — do
   not reflow passing sections, and do not regress a strength the review recorded.
5. **Self-check** against [Pre-Handoff Check](#pre-handoff-check) before returning; in
   `revise`, additionally confirm every Required Change is addressed.
6. **Return** the shape below. Report file **paths**, never artifact bodies.

Story content (WHAT/WHY) is never authored here. When the story source is external,
reference it; a local story comes from the story package via the `create` scaffold.

### Returns

```json
{
  "status": "success",
  "mode": "create",
  "featureName": "payment-retries",
  "paths": [
    ".ai/specs/payment-retries/README.md",
    ".ai/specs/payment-retries/payment-retries.spec.md",
    ".ai/specs/payment-retries/payment-retries.plan.md"
  ],
  "storySource": "PAY-512",
  "summary": "Authored the spec artifacts for payment-retries from Jira PAY-512."
}
```

| Field | Meaning |
|---|---|
| `status` | `success`, `questions`, or `error` — exactly one per invocation. |
| `mode` | The mode that ran. |
| `paths` | Artifacts created (`create`) or changed (`revise`). |
| `storySource` | The external path/key, or `null` for a local story. |
| `changesApplied` | **`revise` only** — the resolved Required Change IDs, e.g. `["RC-001", "RC-002"]`. |

On `status: questions`, return the specific decisions needed and any artifacts already
written; the caller resolves them and re-runs the same mode. Never silently assume a
requirement the story does not state.

### Errors

| Code | When | Recovery to offer |
|---|---|---|
| `SPEC_INCOMPLETE` | Handoff missing `mode`, `featureName`, `specDirectory`, or (revise) `reviewPath` | Supply the missing input and re-run |
| `SPEC_EXISTS` | `create` against an existing spec directory | Resume the existing spec, or re-author deliberately |
| `STORY_NOT_FOUND` | The story source (file path or Jira issue key) cannot be resolved | Correct the path/key, or omit it for a local story |
| `WRITE_FAILED` | A required artifact could not be written | Resolve the write failure (permissions, path) and re-run |

Never report a partial spec as success.

## Reference Documents

- `references/spec-section-examples.md` — Paired good/shallow examples with rationale for architecture and data flow, algorithms, data-model validation, technical decisions, edge-case handling, and testing strategy. Read when drafting or reviewing a specific section and you need a concrete model for how deep it must go.
