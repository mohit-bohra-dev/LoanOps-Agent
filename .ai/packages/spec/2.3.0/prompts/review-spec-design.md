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

Load **{{skill:spec.spec-design-review-rubric}}** and execute its Invocation Contract with the inputs below. The skill owns the five passes, the 1–5 scoring, the verdict rule, the Required Changes shape, and the write-up spec — do not re-derive any of it here.

| Prompt parameter | Skill input | Notes |
|---|---|---|
| `{{featureName}}` | `featureName` | Ask which spec to review when absent and no `specDirectory` is given |
| `{{specDirectory}}` | `specDirectory` | Defaults to `.ai/specs/{{featureName}}`; a missing directory returns `SPEC_NOT_FOUND` |
| `{{storySource}}` | `storySource` | Defaults to the local story in the spec directory |
| `{{strictness}}` | `strictness` | Default `normal` |
| `{{outputDir}}` | `outputDir` | Default `.ai/working/spec-design-reviews/` |
| `{{iteration}}` | `iteration` | Default `1`; names the write-up |

The run operates as **{{agent:spec.spec-design-reviewer}}** — an investigator that never rewrites the spec artifacts. If a `{{skill:...}}` or `{{agent:...}}` reference does not resolve from the package folder, it lives under `.ai/packages/spec/...`. Surface the returned verdict as this prompt's output.

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

`verdict` is `pass` only when `mustFixCount == 0` and `score >= 3.5`. Feed `reviewPath` into `{{skill:spec.technical-spec-authoring}}` (`mode: revise`) to address the Required Changes, then re-run with `iteration` incremented.

## Error Handling

On any error, return the structured error and stop. Conditions and recovery are in the skill's Errors table.

- **`SPEC_NOT_FOUND`** — the spec directory or `[featureName].spec.md` does not exist.
- **`INSUFFICIENT_SPEC`** — the artifacts exist but contain no parseable design to review.
- **`WRITE_FAILED`** — the write-up could not be persisted after the review computed.

There is no `questions` path — an unreachable story source becomes a must-fix coverage finding while the other passes still run.
