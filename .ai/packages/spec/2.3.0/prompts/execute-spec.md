# Execute Specification

Execute a technical specification end to end through a research → triage → scoped-execution loop.

> **Deprecated alias:** `workSpec` maps to this same prompt and behavior. New callers should use `executeSpec`.

## Parameters

- **{{featureName}}** (string, optional): Name of the spec to execute.
  - Resolves the spec directory at `.ai/specs/{{featureName}}/`.
  - Must match an existing spec directory name. Example: `package-version-cleanup`
  - If omitted, the run asks which spec to execute once it has control.

- **{{phase}}** (string, optional): A specific phase to scope the run to.
  - Matches a phase prefix from the plan (e.g. `p1`, `p2`) or a phase name.
  - Default: execute the full plan from the first incomplete unit.

- **{{task}}** (string, optional): A specific todo id to scope the run to.
  - Matches a todo id from the plan frontmatter (e.g. `p1-create-utility`).
  - Default: execute the full plan (or the full `phase` when one is provided).

- **{{reviewArtifact}}** (string, optional): Path to a `{{featureName}}.review.md`.
  - When provided, the review's findings — not the plan's phases — become the work source for the loop.
  - Example: `.ai/specs/package-version-cleanup/package-version-cleanup.review.md`

## Instructions

Load **{{skill:spec-implementation-execution}}** and execute its Invocation Contract with the inputs below. The skill owns the loop, gap triage, the sizing recommendation, per-unit scope and wiring discipline, quality gates, and the Jira lifecycle — do not re-derive any of it here.

| Prompt parameter | Skill input | Notes |
|---|---|---|
| `{{featureName}}` | `featureName` | Resolved before the run starts; a missing directory returns `SPEC_NOT_FOUND` |
| `{{phase}}` | `phase` | Optional scope selector |
| `{{task}}` | `task` | Optional scope selector |
| `{{reviewArtifact}}` | `reviewArtifact` | Switches the work source from the plan's phases to a review's findings |

With none of the three selectors, the full plan is executed. The run operates as **{{agent:spec-execution-coordinator}}**, which is the only agent that talks to the user after hand-off; sub-agents return to it. Surface its final progress summary as this prompt's output.

## Response Format

```json
{
  "success": true,
  "featureName": "package-version-cleanup",
  "phase": "Phase 2: CLI Integration",
  "todosCompleted": [
    "p2-create-command: Create prune command file",
    "p2-command-options: Add command options"
  ],
  "todosRemaining": 86,
  "percentComplete": 30,
  "assumptionsMade": [
    "Reused the existing logger instead of adding a dependency (documented in spec.md)"
  ],
  "openQuestionsRaised": [],
  "filesChanged": [
    "packages/cli/src/commands/prune.ts (created)",
    "packages/cli/src/index.ts (modified)"
  ]
}
```

`phase` is `null` when the full plan ran. Field meanings are in the skill's Returns table.

## Error Handling

- **`SPEC_NOT_FOUND`** — `{{featureName}}` resolves to a `.ai/specs/{{featureName}}/` directory that does not exist, checked before the run starts.

Blocking questions and sub-agent errors that arise once the run has control are handled in-conversation by the coordinator — it pauses and escalates genuine unknowns and reports what completed rather than fabricating success. They are not returned as throws from this prompt.
