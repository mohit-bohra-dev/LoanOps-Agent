---
name: spec-spec-plan-format
description: >-
  The Cursor `[feature].plan.md` plan format used across the spec workflows:
  the YAML frontmatter schema (name, overview, todos, isProject), the
  `p{N}-slug` todo ID convention, the pending → in_progress → completed status
  lifecycle, progress math by phase, the markdown-body-vs-frontmatter-todos
  split, and the discipline of never marking a todo completed before the work
  is actually done. Use when reading, parsing, or editing a plan's todos,
  computing spec progress, scoping work to a phase or todo, or updating todo
  status.
promp:
  package: "spec"
  version: "2.3.0"
  environment: "development"
  prompVersion: "1.0.1-beta.161"
  skill: "spec-plan-format"
---

# Spec Plan Format

The `[feature].plan.md` file is a spec's implementation plan in **Cursor plan format**. It has two parts that serve two different purposes:

- **YAML frontmatter `todos`** — the atomic, trackable units of work. This is the source of truth for *what* is being done and *progress*.
- **Markdown body** — phase-by-phase context: architecture, code examples, file paths, test requirements, success criteria. This is the source of truth for *how* to execute each task.

Keep these roles straight: read the **todos** for the task list and tracking; read the matching **body** section for execution detail. Update the **todos** to record progress; update the **body** Notes to record blockers and decisions.

## When to Use

- Reading or parsing a plan to determine what to work on next
- Computing progress (completed / remaining / percent) for a spec
- Scoping execution or review to a phase (`p2`) or a single todo (`p2-extract-skills`)
- Updating a todo's `status` after starting or finishing work
- Reconciling todo statuses against the actual state of the implementation
- Creating or updating a plan's frontmatter

## Frontmatter Schema

```yaml
---
name: spec-rebuild                 # kebab-case; matches the spec dir and [feature].* artifacts
overview: Rebuild the spec package into a layered, skills-backed architecture.
todos:
  - id: p1-template-rewrite        # p{N}-{slug}: N = phase number, slug = kebab-case
    content: "Rewrite the plan template with the new frontmatter schema"
    status: pending                # pending | in_progress | completed
  - id: p1-rule-slim
    content: "Slim the specStructure rule to guardrails only"
    status: pending
  - id: p2-extract-skills
    content: "Extract shared plan/artifact knowledge into skills"
    status: pending
isProject: false                   # always false for feature spec plans
---
```

| Field | Type | Required | Rule |
|-------|------|----------|------|
| `name` | string | yes | kebab-case feature name; matches the spec directory and the `[feature].*` artifacts |
| `overview` | string | yes | one sentence describing what the plan accomplishes |
| `todos` | array | yes | ordered list of todo objects (see below); the tracking layer |
| `isProject` | boolean | yes | always `false` for feature spec plans |

Each `todos` entry has exactly three fields:

| Field | Type | Rule |
|-------|------|------|
| `id` | string | `p{N}-{slug}` (see [Todo IDs](#todo-ids)). Stable once assigned |
| `content` | string | specific, actionable, independently verifiable task description |
| `status` | enum | `pending` \| `in_progress` \| `completed` |

## Todo IDs

The `id` follows `p{N}-{slug}`:

- `{N}` is the **phase number** (1-based). It is the grouping key — every todo in phase 2 starts with `p2-`.
- `{slug}` is a short kebab-case description of the task (e.g. `p1-template-rewrite`, `p3-thin-prompts`).

The phase prefix does double duty: it groups todos for [progress math](#progress-math) and it is the join key between the frontmatter and the body's phase sections.

**IDs are stable.** Once a todo has an ID, do not renumber or rename it — downstream scoping depends on it (a caller may pass `phase: p2` or `task: p2-extract-skills`). When adding work, append a new todo with a new slug; never recycle or reorder existing IDs.

## Status Lifecycle

```text
pending  →  in_progress  →  completed
```

- Move a todo to `in_progress` when you **start** it.
- Move a todo to `completed` only when the work is **actually done and verified** (see [Completion Accuracy](#completion-accuracy)).

### Editing discipline

When you change a status, edit **only the `status` field** of the affected todo. Preserve everything else exactly:

- Keep todo order unchanged.
- Do not alter any `id` or `content`.
- Do not touch the top-level `name`, `overview`, or `isProject`.
- Do not reflow, reindent, or rewrite the whole frontmatter block — make the smallest edit that changes the one (or few) statuses.

This keeps diffs minimal and avoids merge conflicts when several people edit the same plan.

## Progress Math

Compute progress from the `todos` array:

- **Total** = number of todos.
- **Completed** = count of `status: completed`.
- **In progress** = count of `status: in_progress`.
- **Remaining** = Total − Completed.
- **Percent complete** = round(Completed ÷ Total × 100).

**By phase** — group todos by their `p{N}-` prefix and apply the same counts per group. A phase is **complete** when every todo in its group is `completed`. The **current phase** is the one containing the first `pending` or `in_progress` todo (by order). The **next todo** is the first todo whose status is `pending` or `in_progress`.

## Markdown Body Conventions

The body is organized by phase and holds the execution detail the todos summarize:

- Each phase section declares which todos it covers via the prefix, e.g. **Todos in this phase**: `p2-*`.
- A body task maps to one or more frontmatter todos sharing the matching `p{N}-` prefix.
- The **Notes** section records blockers, deviations, and decisions discovered during execution.

When executing: get the *what* and *tracking* from the todos, get the *how* from the matching phase section. When recording progress: update the todo `status` (tracking) and, if relevant, add to Notes (context).

## Completion Accuracy

A plan's todo statuses must reflect the true state of the implementation at all times. Progress numbers are only trustworthy when statuses are accurate.

Mark a todo `completed` **only** when its work is actually implemented and verified — not when it is "mostly done", planned, or merely expected to pass. When reconciling todos against the real codebase, watch for two failure modes:

- **False completion** — a todo marked `completed` with no implementation evidence. This is always wrong: either finish the work or correct the status back to `in_progress`/`pending`.
- **Unreported completion** — work that is actually done but whose todo is still `pending` or `in_progress`. Update the status to match reality.

If work was performed that no todo covers, add a todo for it (with a correct `p{N}-` prefix) so the plan stays complete.

## Examples

### Recording progress after finishing work

Finished `p2-create-command`, still working on `p2-command-tests`. Change only the `status` fields:

```yaml
# before
todos:
  - id: p2-create-command
    content: "Create prune command file at packages/cli/src/commands/prune.ts"
    status: in_progress
  - id: p2-command-tests
    content: "Create test file at packages/cli/src/commands/prune.test.ts"
    status: pending
```

```yaml
# after
todos:
  - id: p2-create-command
    content: "Create prune command file at packages/cli/src/commands/prune.ts"
    status: completed
  - id: p2-command-tests
    content: "Create test file at packages/cli/src/commands/prune.test.ts"
    status: in_progress
```

`id`, `content`, order, and all top-level fields are untouched.

### Computing progress

Given 5 todos — `p1-a` completed, `p1-b` completed, `p2-a` completed, `p2-b` in_progress, `p3-a` pending:

- Total 5, Completed 3, In progress 1, Remaining 2, Percent = round(3 ÷ 5 × 100) = **60%**.
- Phase 1: 2/2 → **complete**. Phase 2: 1/2 → in progress (current phase). Phase 3: 0/1 → not started.
- Next todo: `p2-b` (first non-completed by order).

### Detecting a false completion

A todo reads `status: completed` but the file it claims to create does not exist in the codebase. This is a **false completion** — reset it to `pending` (or finish the work) before reporting progress.

## When Editing a Plan

- [ ] Frontmatter has `name`, `overview`, `todos`, `isProject: false`.
- [ ] Every todo has `id` (`p{N}-{slug}`), `content`, and a valid `status`.
- [ ] Status changes touch only the `status` field; order and other fields preserved.
- [ ] Statuses match the real implementation state (no false or unreported completions).
- [ ] New work is captured as a todo with the correct phase prefix.
