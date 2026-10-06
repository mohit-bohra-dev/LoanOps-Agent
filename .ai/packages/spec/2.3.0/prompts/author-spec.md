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

Load **{{skill:spec.technical-spec-authoring}}** and execute its Invocation Contract with the inputs below. The skill owns the pre-flight checks, both mode procedures, the depth bar, the self-check, and the error catalogue — do not re-derive any of it here.

| Prompt parameter | Skill input | Notes |
|---|---|---|
| `{{mode}}` | `mode` | The distinguishing input — `create` (default) or `revise` |
| `{{featureName}}` | `featureName` | Ask which feature to author when absent and no `specDirectory` is given |
| `{{specDirectory}}` | `specDirectory` | Defaults to `.ai/specs/{{featureName}}` |
| `{{storySource}}` | `storySource` | Omit for a local story |
| `{{description}}` | `description` | Used when a local story is generated in `create` |
| `{{reviewPath}}` | `reviewPath` | Required when `mode` is `revise`; the review's Required Changes are the authoritative change set |

The run happens in an isolated context as **{{agent:spec.spec-author}}**, alongside **{{skill:spec.spec-artifact-model}}** and **{{skill:spec.spec-plan-format}}**. If a `{{skill:...}}` or `{{agent:...}}` reference does not resolve from the package folder, it lives under `.ai/packages/spec/...`. Surface the skill's returned status as this prompt's output.

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
