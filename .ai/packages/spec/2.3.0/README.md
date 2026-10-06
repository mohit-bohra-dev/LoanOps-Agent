# spec

Create, maintain, execute, and review technical specifications with research-grounded, scoped execution and Jira lifecycle integration.

The package uses a layered architecture: **skills own the procedures** and are the composition surface other packages call; thin prompts are slash-command entry points that load a skill and pass it inputs; agents own multi-step orchestration; one slim rule enforces non-negotiable guardrails.

## Why use this?

Take a feature from idea to reviewed implementation on a single rail: scaffold a spec, execute it in research-grounded scoped steps, review the result against the spec, and keep Jira in step the whole way — no drift between what you planned, what you built, and what the tracker says.

- **A structured spec in one command** — `createSpec` scaffolds the full artifact set (story, spec, plan, README) from templates, so you start from a consistent, navigable structure instead of a blank file.
- **Grounded execution, not guesswork** — `executeSpec` researches the codebase, triages open questions, and implements scoped units, so changes fit the real code and land in reviewable pieces.
- **Catch gaps before merge** — `reviewSpecImplementation` scores coverage against the spec and writes a review artifact that `executeSpec` can act on directly, closing the build → review → fix loop.
- **Jira stays in sync automatically** — the execution coordinator drives status transitions and assignment through the `story` package, so the tracker reflects reality without manual updates.
- **Changes routed to the right place** — `updateSpec` uses a change-routing matrix to update story, spec, plan, or README, so requirement changes don't leave artifacts inconsistent.
- **Quality gates when available** — execution runs `aidev`/repo quality gates when present and cleanly skips with a note when they aren't, so the same workflow fits different repos.

## Installation

```bash
promp install spec
```

Installs the `story` dependency (`^1.0.0`) for story authoring, Jira sync, and the tracker lifecycle — status transitions **and assignment**; `story` brings `jira` transitively. The spec also depends on `jira` (`^1.4.0`) directly, only for reading an external Jira story during `createSpec`. Quality gates during execution are optional and runtime-detected (`aidev workflow run` when `.ai/project.json` and `@pennymac/aidev` are present; otherwise repo scripts; otherwise skip with a note).

## Usage

Invoke prompts with the `/spec.<promptName>` prefix:

```bash
# Create a new spec (interactive)
/spec.createSpec

# Create with parameters
/spec.createSpec featureName="payment-retries" description="Retry failed payments with exponential backoff"

# Create using an existing Jira story
/spec.createSpec featureName="payment-retries" storySource="PAY-512"

# Update after requirements change
/spec.updateSpec featureName="payment-retries" changes="Add P2 backoff story" artifact="all"

# Execute the full spec (research → triage → scoped execution)
/spec.executeSpec featureName="payment-retries"

# Execute one phase
/spec.executeSpec featureName="payment-retries" phase="p2"

# Execute review findings from a prior review pass
/spec.executeSpec featureName="payment-retries" reviewArtifact=".ai/specs/payment-retries/payment-retries.review.md"

# Review implementation against the spec
/spec.reviewSpecImplementation featureName="payment-retries" scope="full" strictness="normal"

# Sync the local story to Jira
/spec.syncSpecToJira featureName="payment-retries"

# Deprecated alias — same behavior as executeSpec
/spec.workSpec featureName="payment-retries"
```

### Typical workflow

1. **Create** — `/spec.createSpec` scaffolds `.ai/specs/<featureName>/` and offers Jira sync when a local story is authored.
2. **Refine** — `/spec.updateSpec` routes changes to the right artifacts.
3. **Execute** — `/spec.executeSpec` runs research, triages open questions, executes scoped units, and drives Jira transitions.
4. **Review** — `/spec.reviewSpecImplementation` persists `[featureName].review.md` and returns health score and findings.
5. **Fix gaps** — `/spec.executeSpec reviewArtifact="…/[feature].review.md"` acts on review findings.
6. **Sync** — `/spec.syncSpecToJira` keeps the story and Jira issue in step.

## What It Does

Each prompt is a thin slash-command entry point: it declares the parameter contract and loads the skill that owns the procedure.

| Prompt | Loads | Role |
|--------|-------|------|
| `createSpec` | `spec-artifact-model` (`mode: create`) | Scaffold spec artifacts from templates; optional external story via file path or Jira issue key |
| `updateSpec` | `spec-artifact-model` (`mode: update`) | Route changes to story, spec, plan, or README via the change-routing matrix |
| `executeSpec` | `spec-implementation-execution` | Research → triage → scoped execution loop via `spec-execution-coordinator` |
| `reviewSpecImplementation` | `spec-review-rubric` | Score coverage and persist `[featureName].review.md` via `spec-review` |
| `authorSpec` | `technical-spec-authoring` (`mode: create \| revise`) | Author/revise spec artifacts in an isolated context via `spec-author` |
| `reviewSpecDesign` | `spec-design-review-rubric` | Pre-implementation design gate — verdict + Required Changes via `spec-design-reviewer` |
| `syncSpecToJira` | `spec-jira-sync` | Delta-sync story to Jira (create or update) — thin wrapper over the `story` package |
| `workSpec` | `spec-implementation-execution` | **Deprecated** — alias for `executeSpec`; use `executeSpec` for new callers |

## Spec artifact model

A spec lives at `.ai/specs/<featureName>/` with these artifacts:

| File | Purpose |
|------|---------|
| `README.md` | Front door, navigation, and executive summary (no separate `SUMMARY.md`) |
| `[featureName].story.md` | WHAT/WHY — user stories, requirements, success criteria (skipped when story is external) |
| `[featureName].spec.md` | HOW — architecture, algorithms, APIs, testing strategy |
| `[featureName].plan.md` | Cursor plan format — YAML todos + phased implementation body |
| `[featureName].review.md` | Written by `reviewSpecImplementation`; consumable by `executeSpec` via `reviewArtifact` |

Story source: pass a file path or Jira issue key to `storySource` on `createSpec` or `syncSpecToJira` (auto-detected by shape).

Templates in `templates/` (README, spec, plan) are rendered by the `spec-artifact-model` skill's `create` contract. The `[featureName].story.md` is produced by the `story` package (`story.story-authoring`), which owns the story template.

## What Powers It

### Prompts

| Name | Description |
|------|-------------|
| `createSpec` | Create a new spec directory and skills-backed artifacts; optional story from file or Jira |
| `updateSpec` | Update existing spec artifacts with change-routing across story, spec, plan, and README |
| `executeSpec` | Execute a spec through research → triage → scoped-execution with Jira lifecycle |
| `workSpec` | **Deprecated** — alias for `executeSpec` |
| `reviewSpecImplementation` | Review implementation against spec; persist review artifact and return structured findings |
| `authorSpec` | Author or revise a spec's artifacts in an isolated context (create/revise) via `spec-author` |
| `reviewSpecDesign` | Review a spec's design pre-implementation; verdict + Required Changes via `spec-design-reviewer` |
| `syncSpecToJira` | Delta-sync the spec story to Jira — thin wrapper over `story.story-jira-sync` |

### Agents

| Name | Description |
|------|-------------|
| `spec-research` | Codebase grounding, sizing verdict, and gap classification before execution; writes only its own context brief |
| `spec-execution` | Implements one scoped phase/todo-group; wires integration points; runs quality gates |
| `spec-execution-coordinator` | Owns the executeSpec loop; triages questions; delegates research and execution; drives the Jira lifecycle — status + assignment — via the `story` package |
| `spec-review` | Evaluates implementation against spec; writes `[featureName].review.md` |
| `spec-author` | Authors/revises a spec's artifacts in isolated context (create reuses `createSpec`; revise applies Required Changes); author-only, three-path return |
| `spec-design-reviewer` | Pre-implementation design gate — scores the spec's design, returns verdict + Required Changes, writes a design-review write-up |

### Skills

| Name | Description |
|------|-------------|
Skills marked **contract** carry an Invocation Contract (Inputs / Returns / Errors) and can be called directly by another package or workflow without reading a prompt.

| Name | Contract | Description |
|------|----------|-------------|
| `spec-artifact-model` | ✅ `mode: create \| update` | Artifact roles, `[featureName].X.md` naming, cross-links, story-source detection; the create and update lifecycle operations |
| `spec-plan-format` | — | Cursor plan YAML, `p{N}-slug` todos, progress and status lifecycle |
| `technical-spec-authoring` | ✅ `mode: create \| revise` | spec.md section standards — architecture, algorithms, API, testing; the isolated authoring run |
| `spec-review-rubric` | ✅ | Coverage matrix, finding taxonomy, strictness modes, health scoring |
| `spec-design-review-rubric` | ✅ | Pre-implementation design review — 5 passes, 1–5 scoring, pass/fail verdict, ordered Required Changes |
| `spec-implementation-execution` | ✅ | Scoped task methodology, wiring discipline, tiered quality gates; the end-to-end execution loop |
| `spec-jira-sync` | ✅ | Resolve a spec's story file and delta-sync it to Jira through the `story` package |
| `spec-research-grounding` | — | Context brief construction and big-vs-small gap classification |
| `spec-sizing` | — | One-block vs should-split verdict and split recommendations |

> Story authoring and the story ⇄ Jira lifecycle (sync, status transitions, **assignment**) live in the [`story`](../story/README.md) package. The spec consumes them through the `story-authoring`, `story-jira-sync`, and `story-jira-lifecycle` **skills** — skills are the cross-package composition surface, because they are installed whether a package is a direct or a transitive dependency.

### Rules

| Name | Description |
|------|-------------|
| `specStructure` | Required artifact set, naming, WHAT/WHY vs HOW boundary, load-skills directive (scoped to `.ai/specs/**`) |

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `story` | `^1.0.0` | Story authoring, Jira sync, and tracker lifecycle — status transitions **and assignment** — via `{{skill:story.story-authoring}}`, `{{skill:story.story-jira-sync}}`, and `{{skill:story.story-jira-lifecycle}}` |
| `jira` | `^1.4.0` | Reading an external Jira story when creating a spec — via `{{skill:jira.retrieve-jira}}`; all other Jira access goes through `story` |

Optional at runtime (not a package dependency):

| Tool | When used |
|------|-----------|
| `@pennymac/aidev` | Quality gates during execution when `.ai/project.json` is present |
| Atlassian MCP | Owned transitively by the `jira` package (via `story`) for sync, transitions, and assignment |

## License

MIT

## Author

Pennymac AI Platform
