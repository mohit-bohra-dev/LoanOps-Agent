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

Load **{{skill:spec-review-rubric}}** and execute its Invocation Contract with the inputs below. The skill owns the five passes, coverage and test scoring, plan-todo reconciliation, the finding taxonomy, the health-score method, and the review-artifact spec — do not re-derive any of it here.

| Prompt parameter | Skill input | Notes |
|---|---|---|
| `{{featureName}}` | `featureName` | Ask which spec to review when absent and no `specDirectory` is given |
| `{{specDirectory}}` | `specDirectory` | Defaults to `.ai/specs/{{featureName}}` |
| `{{scope}}` | `scope` | Default `full`; narrows which passes run |
| `{{phase}}` | `phase` | Required only when `scope` is `phase` |
| `{{strictness}}` | `strictness` | Default `normal` |

The run operates as **{{agent:spec-review}}**, which reads implementation code read-only for evidence and writes only `[featureName].review.md` into the spec directory. Emit its structured result unchanged, with `reviewArtifactPath` set to the persisted artifact.

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

Enums and field shapes are fixed by the skill's Returns section; full property schemas live in `promp.json`. Pass `reviewArtifactPath` to `{{skill:spec-implementation-execution}}` as its `reviewArtifact` input to act on the findings.

## Error Handling

On any error, return the structured error and stop — never fabricate a review result. Conditions and recovery are in the skill's Errors table.

- **`SPEC_NOT_FOUND`** — the resolved spec directory does not exist, or both the story and `[featureName].spec.md` are missing.
- **`INSUFFICIENT_SPEC`** — spec artifacts exist but contain no parseable requirements or technical design.
- **`NO_IMPLEMENTATION`** — none of the files the spec expects exist and no related code can be found.
