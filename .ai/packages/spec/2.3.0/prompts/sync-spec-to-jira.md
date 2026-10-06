# Sync Spec Story to Jira

Delta-sync a spec's story to its Jira issue — create on first sync, push only the changed fields on every sync after.

## Parameters

- **{{featureName}}** (string, optional): The spec whose story to sync.
  - Locates the spec at `.ai/specs/{{featureName}}/` and its `{{featureName}}.story.md`.
  - Example: `payment-retries`

- **{{storySource}}** (string, optional): The sync target — **either** a story file path **or** a Jira issue key, auto-detected by shape. When it is an issue key, the existing issue is **updated**, never re-created.
  - Examples: `PAY-512`, `./payment-retries.story.md`

- **{{projectKey}}** (string, optional): Target Jira project for a first-sync create. When omitted, the jira config's default project is used.

At least one of `featureName` or `storySource` is needed to locate the work. If neither is provided, ask the user which spec to sync before proceeding.

## Instructions

Load **{{skill:spec-jira-sync}}** and execute its Invocation Contract with the inputs below. The skill owns story-file resolution, the delegation to **{{skill:story.story-jira-sync}}**, the result mapping, and the error relay — do not re-derive any of it here.

| Prompt parameter | Skill input | Notes |
|---|---|---|
| `{{featureName}}` | `featureName` | Locates `.ai/specs/{{featureName}}/{{featureName}}.story.md` |
| `{{storySource}}` | `storySource` | Passed through; the story package auto-detects path vs. issue key |
| `{{projectKey}}` | `projectKey` | Passed through for a first-sync create |

The delta-sync method, acceptance-criteria merge mode, conflict surfacing, and issue-key recording all live in the **story** package. Surface its permission prompts and conflict confirmations to the user as-is, and relay its errors verbatim.

## Response Format

```json
{
  "success": true,
  "featureName": "payment-retries",
  "issueKey": "PAY-512",
  "fieldsChanged": ["summary", "acceptanceCriteria"],
  "conflictReport": null
}
```

An empty `fieldsChanged` with `success: true` is a clean no-op sync — the story already matched Jira. `conflictReport` is `null` when there were no divergences.

## Error Handling

`SPEC_NOT_FOUND` is raised by this layer; every other code is relayed verbatim from the story package (which relays the jira skills). Conditions and recovery are in the skill's Errors table.

- **`SPEC_NOT_FOUND`** — the spec or its `[featureName].story.md` cannot be located, and no `storySource` resolves to syncable content.
- **`STORY_NOT_FOUND`** — the story file could not be located.
- **`CONNECTION_FAILED`** — the Atlassian MCP server is not connected or authenticated.
- **`ISSUE_NOT_FOUND`** — the issue key does not exist.
- **`CONFIG_INVALID`** / **`PROJECT_NOT_IN_CONFIG`** / **`DEFAULT_PROJECT_KEY_MISSING`** — jira config problems; point the user at `{{skill:jira.configure-jira}}` or `{{skill:jira.verify-jira-config}}`.
