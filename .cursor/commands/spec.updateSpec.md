---
promp:
  package: "spec"
  version: "2.3.0"
  environment: "development"
  prompVersion: "1.0.1-beta.161"
  prompt: "updateSpec"
---
# spec.updateSpec

Update existing spec artifacts from a description of changes, routing each change to the artifacts it touches and keeping them consistent

## Parameter Specifications

- **`featureName`** (string) - *Optional*
  - Name of the feature spec to update

- **`changes`** (string) - *Optional*
  - Description of changes or updates to make

- **`artifact`** (string) - *Optional*
  - Specific artifact to update: story, spec, plan, readme, or all. 'plan' refers to [featureName].plan.md; 'readme' is the merged README.md (overview + executive summary)

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
   - Parameter 1: `featureName` (optional) - Name of the feature spec to update
   - Parameter 2: `changes` (optional) - Description of changes or updates to make
   - Parameter 3: `artifact` (optional) - Specific artifact to update: story, spec, plan, readme, or all. 'plan' refers to [featureName].plan.md; 'readme' is the merged README.md (overview + executive summary)

2. **Replace parameter placeholders** in the prompt content below:
   - Parameters use the format `{{parameterName}}` in the prompt
   - Replace each placeholder with the corresponding parsed value
   - If a parameter is optional and not provided, use its default value (if specified)
   - If a required parameter is missing, ask the user to provide it

3. **Execute the prompt** with the replaced parameters

## Usage

When the user invokes this command, they may provide parameters in various ways:
- Space-separated values: `/spec.updateSpec value1 value2`
- Named parameters: `/spec.updateSpec param1=value1 param2=value2`
- Mixed format: `/spec.updateSpec value1 param2=value2`

Parse flexibly and map values to the expected parameters in order for positional arguments.

## Expected Output

Details about the spec update

**Type:** `object`

**Properties:**

- `success` (boolean) - **Required** - Whether the update was successful
- `featureName` (string) - **Required** - Name of the updated feature
- `filesUpdated` (array) - **Required** - List of files that were updated
- `changesSummary` (string) - *Optional* - Summary of changes made
## Error Handling

### SpecNotFoundError

Error when the specified spec does not exist

**Properties:**

- `code` (string) (values: ["SPEC_NOT_FOUND"]) - 
- `message` (string) - 
- `featureName` (string) - 

### InvalidArtifactError

Error when the artifact parameter is not one of the allowed values

**Properties:**

- `code` (string) (values: ["INVALID_ARTIFACT"]) - 
- `message` (string) - 
- `providedArtifact` (string) - 
- `allowedValues` (array) - 

## Prompt Content

# Update Technical Specification

Update existing spec artifacts from a description of changes, routing each change to the artifacts it touches and keeping them consistent.

## Parameters

- **{{featureName}}** (string, optional): Name of the spec to update
  - Must match an existing spec directory under `.ai/specs/`
  - If omitted, ask the user (and list available specs when in a specs directory)
  - Example: "payment-retries"

- **{{changes}}** (string, optional): Description of the changes to make
  - May be high-level or detailed; may describe multiple changes
  - If omitted or unclear, ask what changed and why
  - Example: "Add a P2 story for retry backoff; update the retry algorithm and timeline"

- **{{artifact}}** (string, optional): Restrict the update to one artifact
  - One of: `story`, `spec`, `plan`, `readme`, `all`
  - `readme` is the merged `README.md` (overview + executive summary)
  - When omitted, the skill's routing matrix derives the affected artifacts
  - When `all`, every artifact needed to keep the spec consistent is updated

## Instructions

Load **@./.cursor\skills\spec-spec-artifact-model\SKILL.md** and execute its Invocation Contract in `update` mode with the inputs below. The skill owns spec location, change routing, the per-artifact edit authorities, the cross-artifact consistency checks, the Jira re-sync offer, and the error catalogue — do not re-derive any of it here.

| Prompt parameter | Skill input | Notes |
|---|---|---|
| — | `mode` | `update` — the distinguishing input; this prompt is the update entry point |
| `{{featureName}}` | `featureName` | Ask the user when absent |
| `{{changes}}` | `changes` | Ask what changed and why when absent or ambiguous |
| `{{artifact}}` | `artifact` | Omit to let the routing matrix decide |

The skill routes each change to **@./.cursor\skills\story-story-authoring\SKILL.md** (`mode: revise`, local stories only), **@./.cursor\skills\spec-technical-spec-authoring\SKILL.md**, **@./.cursor\skills\spec-spec-plan-format\SKILL.md**, or its own README standards. Surface the skill's result as this prompt's output, and relay its errors verbatim.

## Response Format

```json
{
  "success": true,
  "featureName": "payment-retries",
  "filesUpdated": [
    ".ai/specs/payment-retries/payment-retries.story.md",
    ".ai/specs/payment-retries/payment-retries.spec.md"
  ],
  "changesSummary": "Added a P2 backoff story and the corresponding retry-backoff algorithm to the spec."
}
```

`filesUpdated` lists only the artifacts actually changed; `changesSummary` is one to two sentences on what changed and why.

## Error Handling

On any error, stop and return the structured error. Conditions and recovery are in the skill's Errors table.

- **`SPEC_NOT_FOUND`** — no directory exists at `.ai/specs/{{featureName}}`.
- **`INVALID_ARTIFACT`** — `artifact` is not one of `story`, `spec`, `plan`, `readme`, `all`.

