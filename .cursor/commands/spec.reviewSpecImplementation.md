---
promp:
  package: "spec"
  version: "2.3.0"
  environment: "development"
  prompVersion: "1.0.1-beta.161"
  prompt: "reviewSpecImplementation"
---
# spec.reviewSpecImplementation

Review an implementation against its specification by operating as the spec-review agent, which scores coverage, classifies findings, persists a review artifact, and returns the structured result

## Parameter Specifications

- **`featureName`** (string) - *Optional*
  - Name of the feature spec to review

- **`specDirectory`** (string) - *Optional*
  - Path to the spec directory (defaults to .ai/specs/<featureName>)

- **`scope`** (string) - *Optional*
  - Scope of the review: full, requirements, technical, tests, or phase
  - Default: `full`

- **`phase`** (string) - *Optional*
  - Specific phase to review (when scope is 'phase')

- **`strictness`** (string) - *Optional*
  - How strict the review should be: strict, normal, or lenient
  - Default: `normal`

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
   - Parameter 1: `featureName` (optional) - Name of the feature spec to review
   - Parameter 2: `specDirectory` (optional) - Path to the spec directory (defaults to .ai/specs/<featureName>)
   - Parameter 3: `scope` (optional) [default: full] - Scope of the review: full, requirements, technical, tests, or phase
   - Parameter 4: `phase` (optional) - Specific phase to review (when scope is 'phase')
   - Parameter 5: `strictness` (optional) [default: normal] - How strict the review should be: strict, normal, or lenient

2. **Replace parameter placeholders** in the prompt content below:
   - Parameters use the format `{{parameterName}}` in the prompt
   - Replace each placeholder with the corresponding parsed value
   - If a parameter is optional and not provided, use its default value (if specified)
   - If a required parameter is missing, ask the user to provide it

3. **Execute the prompt** with the replaced parameters

## Usage

When the user invokes this command, they may provide parameters in various ways:
- Space-separated values: `/spec.reviewSpecImplementation value1 value2`
- Named parameters: `/spec.reviewSpecImplementation param1=value1 param2=value2`
- Mixed format: `/spec.reviewSpecImplementation value1 param2=value2`

Parse flexibly and map values to the expected parameters in order for positional arguments.

## Expected Output

Comprehensive review results comparing implementation against specification

**Type:** `object`

**Properties:**

- `success` (boolean) - **Required** - Whether the review completed successfully
- `featureName` (string) - **Required** - Name of the reviewed feature
- `healthScore` (number) - **Required** - Overall implementation health score from 0-100
- `requirementCoverage` (object) - **Required** - Breakdown of requirement implementation status
- `findings` (array) - **Required** - List of review findings categorized by severity
- `testCoverage` (object) - *Optional* - Assessment of test coverage
- `trackerAccuracy` (object) - *Optional* - Accuracy of todo status tracking in [featureName].plan.md's YAML frontmatter
- `recommendations` (array) - **Required** - Prioritized list of recommended actions
- `positiveNotes` (array) - *Optional* - Things that were done well
- `reviewArtifactPath` (string) - *Optional* - Path to the persisted [featureName].review.md artifact, consumable by executeSpec via reviewArtifact
## Error Handling

### SpecNotFoundError

Error when the specified spec does not exist

**Properties:**

- `code` (string) (values: ["SPEC_NOT_FOUND"]) - 
- `message` (string) - 
- `featureName` (string) - 
- `searchedPath` (string) - 

### InsufficientSpecError

Error when the spec lacks enough detail for meaningful review

**Properties:**

- `code` (string) (values: ["INSUFFICIENT_SPEC"]) - 
- `message` (string) - 
- `featureName` (string) - 
- `missingArtifacts` (array) - 
- `recommendation` (string) - 

### NoImplementationError

Error when no implementation code can be found for the specification

**Properties:**

- `code` (string) (values: ["NO_IMPLEMENTATION"]) - 
- `message` (string) - 
- `featureName` (string) - 
- `expectedFiles` (array) - 
- `recommendation` (string) - 

## Prompt Content

# Review Spec Implementation

Review an implementation against its specification — score coverage, classify findings, persist a review artifact, and return the structured result.

## Parameters

- **{{featureName}}** (string, optional): Name of the feature spec to review
  - Resolves the spec directory as `.ai/specs/{{featureName}}` when `specDirectory` is not given
  - Used to name the persisted `[featureName].review.md` artifact
  - Example: "package-version-cleanup"

- **{{specDirectory}}** (string, optional): Path to the spec directory
  - Defaults to `.ai/specs/{{featureName}}`
  - Absolute or relative path

- **{{scope}}** (string, optional): Scope of the review — narrows which review passes run
  - `full` - Review everything (default)
  - `requirements` - Requirement coverage only
  - `technical` - Technical design adherence only
  - `tests` - Test coverage and quality only
  - `phase` - A single implementation phase (requires `phase`)

- **{{phase}}** (string, optional): Phase to review when `scope` is `phase`
  - A phase name or todo-id prefix from `[featureName].plan.md` (e.g., "Phase 2", "p2")
  - Required only when `scope` is `phase`

- **{{strictness}}** (string, optional): How strict the review should be — calibrates finding classification and severity
  - `strict` - Flag any deviation from spec
  - `normal` - Flag significant deviations (default)
  - `lenient` - Only flag critical gaps and missing functionality

## Instructions

Load **@./.cursor\skills\spec-spec-review-rubric\SKILL.md** and execute its Invocation Contract with the inputs below. The skill owns the five passes, coverage and test scoring, plan-todo reconciliation, the finding taxonomy, the health-score method, and the review-artifact spec — do not re-derive any of it here.

| Prompt parameter | Skill input | Notes |
|---|---|---|
| `{{featureName}}` | `featureName` | Ask which spec to review when absent and no `specDirectory` is given |
| `{{specDirectory}}` | `specDirectory` | Defaults to `.ai/specs/{{featureName}}` |
| `{{scope}}` | `scope` | Default `full`; narrows which passes run |
| `{{phase}}` | `phase` | Required only when `scope` is `phase` |
| `{{strictness}}` | `strictness` | Default `normal` |

The run operates as **@./.cursor\agents\spec-review.md**, which reads implementation code read-only for evidence and writes only `[featureName].review.md` into the spec directory. Emit its structured result unchanged, with `reviewArtifactPath` set to the persisted artifact.

## Response Format

```json
{
  "success": true,
  "featureName": "package-version-cleanup",
  "healthScore": 82,
  "requirementCoverage": { "total": 15, "implemented": 12, "partial": 2, "missing": 1, "percentage": 87 },
  "findings": [
    {
      "id": "F-001",
      "severity": "major",
      "category": "requirement",
      "title": "Missing global package support",
      "description": "FR-005 specifies global package cleanup but no implementation was found.",
      "specReference": "story.md - FR-005",
      "recommendation": "Implement global package cleanup as specified in spec.md Section 8.3."
    }
  ],
  "testCoverage": { "testFilesExpected": 8, "testFilesFound": 6, "qualityAssessment": "good", "missingAreas": ["integration tests for CLI commands"] },
  "trackerAccuracy": { "percentage": 91, "falseCompletions": 2, "unreportedCompletions": 1 },
  "recommendations": [
    "Implement FR-005 global package support.",
    "Add missing integration tests for CLI commands."
  ],
  "positiveNotes": [
    "Core cleanup algorithm matches spec exactly.",
    "Error handling follows spec patterns consistently."
  ],
  "reviewArtifactPath": ".ai/specs/package-version-cleanup/package-version-cleanup.review.md"
}
```

Enums and field shapes are fixed by the skill's Returns section; full property schemas live in `promp.json`. Pass `reviewArtifactPath` to `@./.cursor\skills\spec-spec-implementation-execution\SKILL.md` as its `reviewArtifact` input to act on the findings.

## Error Handling

On any error, return the structured error and stop — never fabricate a review result. Conditions and recovery are in the skill's Errors table.

- **`SPEC_NOT_FOUND`** — the resolved spec directory does not exist, or both the story and `[featureName].spec.md` are missing.
- **`INSUFFICIENT_SPEC`** — spec artifacts exist but contain no parseable requirements or technical design.
- **`NO_IMPLEMENTATION`** — none of the files the spec expects exist and no related code can be found.

