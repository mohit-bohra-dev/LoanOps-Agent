---
promp:
  package: "spec"
  version: "2.3.0"
  environment: "development"
  prompVersion: "1.0.1-beta.161"
  prompt: "reviewSpecDesign"
---
# spec.reviewSpecDesign

Review a spec's design before implementation by operating as the spec-design-reviewer agent: score five design dimensions (requirement coverage, architectural soundness, buildability, testability, cross-artifact consistency), return a pass/fail verdict with ordered Required Changes, and persist a design-review write-up. The design-quality gate counterpart to reviewSpecImplementation.

## Parameter Specifications

- **`featureName`** (string) - *Optional*
  - Name of the feature spec to review; resolves .ai/specs/<featureName>.

- **`specDirectory`** (string) - *Optional*
  - Path to the spec directory. Defaults to .ai/specs/<featureName>.

- **`storySource`** (string) - *Optional*
  - Approved story the design is measured against: file path, Jira issue key, or the local story (auto-detected).

- **`strictness`** (string) - *Optional*
  - How strict the review is.
  - Default: `normal`

- **`outputDir`** (string) - *Optional*
  - Where to persist the design-review write-up. Defaults to .ai/working/spec-design-reviews/.

- **`iteration`** (number) - *Optional*
  - Review pass number (1, then 2, ...), used to name the write-up. Default 1.
  - Default: `1`

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
   - Parameter 1: `featureName` (optional) - Name of the feature spec to review; resolves .ai/specs/<featureName>.
   - Parameter 2: `specDirectory` (optional) - Path to the spec directory. Defaults to .ai/specs/<featureName>.
   - Parameter 3: `storySource` (optional) - Approved story the design is measured against: file path, Jira issue key, or the local story (auto-detected).
   - Parameter 4: `strictness` (optional) [default: normal] - How strict the review is.
   - Parameter 5: `outputDir` (optional) - Where to persist the design-review write-up. Defaults to .ai/working/spec-design-reviews/.
   - Parameter 6: `iteration` (optional) [default: 1] - Review pass number (1, then 2, ...), used to name the write-up. Default 1.

2. **Replace parameter placeholders** in the prompt content below:
   - Parameters use the format `{{parameterName}}` in the prompt
   - Replace each placeholder with the corresponding parsed value
   - If a parameter is optional and not provided, use its default value (if specified)
   - If a required parameter is missing, ask the user to provide it

3. **Execute the prompt** with the replaced parameters

## Usage

When the user invokes this command, they may provide parameters in various ways:
- Space-separated values: `/spec.reviewSpecDesign value1 value2`
- Named parameters: `/spec.reviewSpecDesign param1=value1 param2=value2`
- Mixed format: `/spec.reviewSpecDesign value1 param2=value2`

Parse flexibly and map values to the expected parameters in order for positional arguments.

## Expected Output

Design-review verdict and scores

**Type:** `object`

**Properties:**

- `status` (string) - **Required** - 
- `reviewPath` (string) - **Required** - Persisted design-review write-up; consumable by authorSpec as reviewPath
- `verdict` (string) - **Required** - 
- `score` (number) - **Required** - Overall 1-5 (one decimal)
- `mustFixCount` (number) - **Required** - 
- `shouldFixCount` (number) - *Optional* - 
- `passScores` (object) - *Optional* - coverage, soundness, buildability, testability, consistency (each 1-5)
## Error Handling

### SpecNotFoundError

The spec directory or [featureName].spec.md does not exist

**Properties:**

- `code` (string) (values: ["SPEC_NOT_FOUND"]) - 
- `message` (string) - 
- `searchedPath` (string) - 

### InsufficientSpecError

Artifacts exist but contain no parseable design to review

**Properties:**

- `code` (string) (values: ["INSUFFICIENT_SPEC"]) - 
- `message` (string) - 
- `missingArtifacts` (array) - 

### WriteFailedError

The design-review write-up could not be persisted after the review computed

**Properties:**

- `code` (string) (values: ["WRITE_FAILED"]) - 
- `message` (string) - 

## Prompt Content

# Review Spec Design

Review a spec's design before implementation — score five design dimensions, return a pass/fail verdict with ordered Required Changes, and persist a design-review write-up.

## Parameters

- **{{featureName}}** (string, optional): Name of the feature spec to review.
  - Resolves the spec directory as `.ai/specs/{{featureName}}` when `specDirectory` is not given.
  - If omitted and no `{{specDirectory}}` is given, ask which spec to review.

- **{{specDirectory}}** (string, optional): Path to the spec directory. Defaults to `.ai/specs/{{featureName}}`.

- **{{storySource}}** (string, optional): The approved story the design is measured against — a story **file path**, a Jira **issue key**, or the local `[featureName].story.md` (auto-detected). If omitted, the local story in the spec directory is used.

- **{{strictness}}** (string, optional): How strict the review is — `strict`, `normal`, or `lenient`. Default `normal`.

- **{{outputDir}}** (string, optional): Where to persist the design-review write-up. Defaults to `.ai/working/spec-design-reviews/`.

- **{{iteration}}** (number, optional): The review pass number (`1`, then `2`, …), used to name the write-up and track the author → review → revise loop. Default `1`.

## Instructions

Load **@./.cursor\skills\spec-spec-design-review-rubric\SKILL.md** and execute its Invocation Contract with the inputs below. The skill owns the five passes, the 1–5 scoring, the verdict rule, the Required Changes shape, and the write-up spec — do not re-derive any of it here.

| Prompt parameter | Skill input | Notes |
|---|---|---|
| `{{featureName}}` | `featureName` | Ask which spec to review when absent and no `specDirectory` is given |
| `{{specDirectory}}` | `specDirectory` | Defaults to `.ai/specs/{{featureName}}`; a missing directory returns `SPEC_NOT_FOUND` |
| `{{storySource}}` | `storySource` | Defaults to the local story in the spec directory |
| `{{strictness}}` | `strictness` | Default `normal` |
| `{{outputDir}}` | `outputDir` | Default `.ai/working/spec-design-reviews/` |
| `{{iteration}}` | `iteration` | Default `1`; names the write-up |

The run operates as **@./.cursor\agents\spec-design-reviewer.md** — an investigator that never rewrites the spec artifacts. If a `{{skill:...}}` or `{{agent:...}}` reference does not resolve from the package folder, it lives under `.ai/packages/spec/...`. Surface the returned verdict as this prompt's output.

## Response Format

```json
{
  "status": "success",
  "reviewPath": ".ai/working/spec-design-reviews/payment-retries-1.md",
  "verdict": "fail",
  "score": 4.2,
  "mustFixCount": 1,
  "shouldFixCount": 2,
  "passScores": { "coverage": 4, "soundness": 5, "buildability": 3, "testability": 4, "consistency": 5 },
  "summary": "fail — overall 4.2; 1 must-fix (undecomposed gate phase), 2 should-fix."
}
```

`verdict` is `pass` only when `mustFixCount == 0` and `score >= 3.5`. Feed `reviewPath` into `@./.cursor\skills\spec-technical-spec-authoring\SKILL.md` (`mode: revise`) to address the Required Changes, then re-run with `iteration` incremented.

## Error Handling

On any error, return the structured error and stop. Conditions and recovery are in the skill's Errors table.

- **`SPEC_NOT_FOUND`** — the spec directory or `[featureName].spec.md` does not exist.
- **`INSUFFICIENT_SPEC`** — the artifacts exist but contain no parseable design to review.
- **`WRITE_FAILED`** — the write-up could not be persisted after the review computed.

There is no `questions` path — an unreachable story source becomes a must-fix coverage finding while the other passes still run.

