# Create Technical Specification

Create a new spec directory and its skills-backed artifacts for a feature, optionally sourcing the story from a file or a Jira issue.

## Parameters

- **{{featureName}}** (string, optional): Feature name in kebab-case (e.g. `package-version-cleanup`).
  - Lowercase letters, digits, and hyphens only; must start with a letter.
  - Names the spec directory and the `[featureName].*` artifact files.
  - If not provided, ask the user for it.

- **{{description}}** (string, optional): One-line description of what the feature does and the problem it solves.
  - If not provided, ask the user for it.

- **{{storySource}}** (string, optional): Where the story comes from — a story **file path** OR a Jira **issue key**. Auto-detected by shape.
  - A value matching `^[A-Z][A-Z0-9]+-\d+$` (e.g. `ABC-123`) is a Jira issue key.
  - A value containing `/`, `\`, `.`, or a file extension is a file path. When ambiguous, treat it as a path.
  - When absent, a local `[featureName].story.md` is generated.

- **{{specDirectory}}** (string, optional): Directory for the spec.
  - Defaults to `.ai/specs/{{featureName}}`.

## Instructions

Load **{{skill:spec-artifact-model}}** and execute its Invocation Contract in `create` mode with the inputs below. The skill owns validation, story-source resolution, template rendering, the Jira-sync offer, and the error catalogue — do not re-derive any of it here.

| Prompt parameter | Skill input | Notes |
|---|---|---|
| — | `mode` | `create` — the distinguishing input; this prompt is the create entry point |
| `{{featureName}}` | `featureName` | Ask the user when absent |
| `{{description}}` | `description` | Ask the user when absent |
| `{{storySource}}` | `storySource` | Omit for a local story |
| `{{specDirectory}}` | `specDirectory` | Defaults to `.ai/specs/{{featureName}}` |

The skill loads **{{skill:technical-spec-authoring}}** and **{{skill:spec-plan-format}}** for the spec and plan it renders, and delegates story content to **{{skill:story.story-authoring}}** (`mode: create`). Surface the skill's result as this prompt's output, and relay its errors verbatim.

## Response Format

```json
{
  "success": true,
  "featureName": "package-version-cleanup",
  "specPath": ".ai/specs/package-version-cleanup",
  "storySource": null,
  "filesCreated": [
    ".ai/specs/package-version-cleanup/README.md",
    ".ai/specs/package-version-cleanup/package-version-cleanup.story.md",
    ".ai/specs/package-version-cleanup/package-version-cleanup.spec.md",
    ".ai/specs/package-version-cleanup/package-version-cleanup.plan.md"
  ]
}
```

`storySource` is the provided path/key, or `null` when a local story was generated. `filesCreated` omits `[featureName].story.md` whenever `storySource` is set.

## Error Handling

On any error, stop and return the structured error — never leave a partial spec reported as success. Conditions and recovery are in the skill's Errors tables.

- **`INVALID_NAME`** — `featureName` is not kebab-case.
- **`SPEC_EXISTS`** — the target directory already exists.
- **`STORY_NOT_FOUND`** — `storySource` cannot be resolved.
