---
promp:
  package: "spec"
  version: "2.3.0"
  environment: "development"
  prompVersion: "1.0.1-beta.161"
  prompt: "authorSpec"
---
# spec.authorSpec

Author (create) or revise a feature's spec artifacts (README, [featureName].spec.md, [featureName].plan.md) in an isolated context by loading the technical-spec-authoring skill's invocation contract and operating as the spec-author agent. In create mode it runs the spec-artifact-model create contract and deepens the spec and plan; in revise mode it applies a spec-design review's Required Changes. The isolated-context authoring stage an orchestrator loops through a design-quality gate.

## Parameter Specifications

- **`featureName`** (string) - *Optional*
  - Feature name in kebab-case; names the spec directory and [featureName].* artifacts.

- **`mode`** (string) - *Optional*
  - create or revise. Default create. revise requires reviewPath.

- **`storySource`** (string) - *Optional*
  - Approved story: file path OR Jira issue key (auto-detected). External sources are referenced, not copied. Omit for a local story.

- **`description`** (string) - *Optional*
  - One-line feature description, used when a local story is generated in create mode.

- **`specDirectory`** (string) - *Optional*
  - Directory for the spec. Defaults to .ai/specs/<featureName>.

- **`reviewPath`** (string) - *Optional*
  - Spec-design review write-up whose Required Changes drive a revise. Required when mode is revise.

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
   - Parameter 1: `featureName` (optional) - Feature name in kebab-case; names the spec directory and [featureName].* artifacts.
   - Parameter 2: `mode` (optional) - create or revise. Default create. revise requires reviewPath.
   - Parameter 3: `storySource` (optional) - Approved story: file path OR Jira issue key (auto-detected). External sources are referenced, not copied. Omit for a local story.
   - Parameter 4: `description` (optional) - One-line feature description, used when a local story is generated in create mode.
   - Parameter 5: `specDirectory` (optional) - Directory for the spec. Defaults to .ai/specs/<featureName>.
   - Parameter 6: `reviewPath` (optional) - Spec-design review write-up whose Required Changes drive a revise. Required when mode is revise.

2. **Replace parameter placeholders** in the prompt content below:
   - Parameters use the format `{{parameterName}}` in the prompt
   - Replace each placeholder with the corresponding parsed value
   - If a parameter is optional and not provided, use its default value (if specified)
   - If a required parameter is missing, ask the user to provide it

3. **Execute the prompt** with the replaced parameters

## Usage

When the user invokes this command, they may provide parameters in various ways:
- Space-separated values: `/spec.authorSpec value1 value2`
- Named parameters: `/spec.authorSpec param1=value1 param2=value2`
- Mixed format: `/spec.authorSpec value1 param2=value2`

Parse flexibly and map values to the expected parameters in order for positional arguments.

## Expected Output

Result of authoring or revising the spec artifacts

**Type:** `object`

**Properties:**

- `status` (string) - **Required** - 
- `mode` (string) - *Optional* - 
- `featureName` (string) - **Required** - 
- `paths` (array) - *Optional* - Artifacts created (create) or changed (revise)
- `storySource` (string,null) - *Optional* - External story path/key, or null for a local story
- `changesApplied` (array) - *Optional* - Resolved Required Change IDs (revise only)
## Error Handling

### SpecIncompleteError

Handoff missing mode, featureName, specDirectory, or (revise) reviewPath

**Properties:**

- `code` (string) (values: ["SPEC_INCOMPLETE"]) - 
- `message` (string) - 

### SpecExistsError

create against an existing spec directory

**Properties:**

- `code` (string) (values: ["SPEC_EXISTS"]) - 
- `message` (string) - 
- `existingSpecPath` (string) - 

### StoryNotFoundError

The story source cannot be resolved (missing file or Jira issue)

**Properties:**

- `code` (string) (values: ["STORY_NOT_FOUND"]) - 
- `message` (string) - 
- `storySource` (string) - 

### WriteFailedError

A required artifact could not be written

**Properties:**

- `code` (string) (values: ["WRITE_FAILED"]) - 
- `message` (string) - 

## Prompt Content

# Author Specification

Author (or revise) a feature's spec artifacts — `README.md`, `[featureName].spec.md`, and `[featureName].plan.md` — in a fresh, isolated context.

## Parameters

- **{{featureName}}** (string, optional): Feature name in kebab-case (e.g. `payment-retries`).
  - Names the spec directory and the `[featureName].*` artifacts.
  - If omitted and no `{{specDirectory}}` is given, ask which feature to author.

- **{{mode}}** (string, optional): `create` or `revise`.
  - Default: `create`.
  - `revise` requires `{{reviewPath}}`.

- **{{storySource}}** (string, optional): The approved story — a story **file path** OR a Jira **issue key** (auto-detected by shape). External sources are referenced, not copied (no local `[featureName].story.md` is generated). Omit for a local story.

- **{{description}}** (string, optional): One-line description of the feature, used when a local story is generated in `create` mode.

- **{{specDirectory}}** (string, optional): Directory for the spec. Defaults to `.ai/specs/{{featureName}}`.

- **{{reviewPath}}** (string, optional): Path to a spec-design review write-up whose Required Changes drive a `revise`. **Required when `{{mode}}` is `revise`.**

## Instructions

Load **@./.cursor\skills\spec-technical-spec-authoring\SKILL.md** and execute its Invocation Contract with the inputs below. The skill owns the pre-flight checks, both mode procedures, the depth bar, the self-check, and the error catalogue — do not re-derive any of it here.

| Prompt parameter | Skill input | Notes |
|---|---|---|
| `{{mode}}` | `mode` | The distinguishing input — `create` (default) or `revise` |
| `{{featureName}}` | `featureName` | Ask which feature to author when absent and no `specDirectory` is given |
| `{{specDirectory}}` | `specDirectory` | Defaults to `.ai/specs/{{featureName}}` |
| `{{storySource}}` | `storySource` | Omit for a local story |
| `{{description}}` | `description` | Used when a local story is generated in `create` |
| `{{reviewPath}}` | `reviewPath` | Required when `mode` is `revise`; the review's Required Changes are the authoritative change set |

The run happens in an isolated context as **@./.cursor\agents\spec-author.md**, alongside **@./.cursor\skills\spec-spec-artifact-model\SKILL.md** and **@./.cursor\skills\spec-spec-plan-format\SKILL.md**. If a `{{skill:...}}` or `{{agent:...}}` reference does not resolve from the package folder, it lives under `.ai/packages/spec/...`. Surface the skill's returned status as this prompt's output.

## Response Format

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

On `revise`, `paths` lists the artifacts changed and `changesApplied` lists the resolved Required Change IDs (e.g. `["RC-001", "RC-002"]`).

## Error Handling

On any error, return the structured error and stop — never report a partial spec as success. Conditions and recovery are in the skill's Errors table.

- **`SPEC_INCOMPLETE`** — handoff missing `mode`, `featureName`, `specDirectory`, or (revise) `reviewPath`.
- **`SPEC_EXISTS`** — `create` against an existing spec directory.
- **`STORY_NOT_FOUND`** — the story source cannot be resolved.
- **`WRITE_FAILED`** — a required artifact could not be written.

On `status: questions`, surface the questions for resolution and re-run the same mode once answered.

