---
promp:
  package: "spec"
  version: "2.3.0"
  environment: "development"
  prompVersion: "1.0.1-beta.161"
  prompt: "workSpec"
---
# spec.workSpec

DEPRECATED — alias for executeSpec; use executeSpec. Execute a technical specification end to end through a research → triage → scoped-execution loop, operating as the spec execution coordinator

## Parameter Specifications

- **`featureName`** (string) - *Optional*
  - Name of the feature spec to execute

- **`phase`** (string) - *Optional*
  - Specific phase to scope the run to (e.g., 'p1' or a phase name from the plan)

- **`task`** (string) - *Optional*
  - Specific todo id to scope the run to (e.g., 'p1-create-utility')

- **`reviewArtifact`** (string) - *Optional*
  - Path to [featureName].review.md; when provided, review findings become the work source instead of plan phases

## Instructions

You are executing a Promp package prompt. Follow these steps:

0. **Resolve package location (required first tool call):** Run this shell command before any other tool and use the returned `packageDir` as the package root for every artifact path in this file:

```bash
promp ensure-package spec --json --project-path "D:\Users\v-mbohra\Documents\Projects\LoanOps-Agent"
```

- `packageDir` is the extracted package directory. Use it for every skill, prompt, or template path below.
- If `success` is `false` and no `packageDir` is returned, the package could not be found or installed. Run `promp install spec` or `promp install -g spec` and retry.
- Do **not** search other workspace roots for package files — always use the path returned by this command.

1. **Parse the user input** to extract parameters:
   - Parameter 1: `featureName` (optional) - Name of the feature spec to execute
   - Parameter 2: `phase` (optional) - Specific phase to scope the run to (e.g., 'p1' or a phase name from the plan)
   - Parameter 3: `task` (optional) - Specific todo id to scope the run to (e.g., 'p1-create-utility')
   - Parameter 4: `reviewArtifact` (optional) - Path to [featureName].review.md; when provided, review findings become the work source instead of plan phases

2. **Replace parameter placeholders** in the prompt content below:
   - Parameters use the format `{{parameterName}}` in the prompt
   - Replace each placeholder with the corresponding parsed value
   - If a parameter is optional and not provided, use its default value (if specified)
   - If a required parameter is missing, ask the user to provide it

3. **Execute the prompt** with the replaced parameters

## Usage

When the user invokes this command, they may provide parameters in various ways:
- Space-separated values: `/spec.workSpec value1 value2`
- Named parameters: `/spec.workSpec param1=value1 param2=value2`
- Mixed format: `/spec.workSpec value1 param2=value2`

Parse flexibly and map values to the expected parameters in order for positional arguments.

## Expected Output

Implementation progress details from the execution loop

**Type:** `object`

**Properties:**

- `success` (boolean) - **Required** - Whether the in-scope work completed without an unrecoverable error
- `featureName` (string) - **Required** - Name of the feature being executed
- `phase` (string,null) - *Optional* - The phase scope of the run, or null when the full plan ran
- `todosCompleted` (array) - **Required** - Todos completed in this run, each as id: summary
- `todosRemaining` (number) - *Optional* - Count of todos not yet complete across the plan
- `percentComplete` (number) - *Optional* - Overall plan completion percentage (0-100)
- `assumptionsMade` (array) - *Optional* - Confirmed assumptions execution acted within
- `openQuestionsRaised` (array) - *Optional* - Open questions raised this run and their disposition
- `filesChanged` (array) - *Optional* - Files created or modified during the run
## Error Handling

### SpecNotFoundError

Error when the specified spec does not exist

**Properties:**

- `code` (string) (values: ["SPEC_NOT_FOUND"]) - 
- `message` (string) - 
- `featureName` (string) - 

## Prompt Content

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

Load **@./.cursor\skills\spec-spec-implementation-execution\SKILL.md** and execute its Invocation Contract with the inputs below. The skill owns the loop, gap triage, the sizing recommendation, per-unit scope and wiring discipline, quality gates, and the Jira lifecycle — do not re-derive any of it here.

| Prompt parameter | Skill input | Notes |
|---|---|---|
| `{{featureName}}` | `featureName` | Resolved before the run starts; a missing directory returns `SPEC_NOT_FOUND` |
| `{{phase}}` | `phase` | Optional scope selector |
| `{{task}}` | `task` | Optional scope selector |
| `{{reviewArtifact}}` | `reviewArtifact` | Switches the work source from the plan's phases to a review's findings |

With none of the three selectors, the full plan is executed. The run operates as **@./.cursor\agents\spec-execution-coordinator.md**, which is the only agent that talks to the user after hand-off; sub-agents return to it. Surface its final progress summary as this prompt's output.

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

