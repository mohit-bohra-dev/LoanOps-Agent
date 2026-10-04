# Sync Story to Jira

Delta-sync a `[name].story.md` to its Jira issue — create on first sync, push only the changed fields on every sync after.

## Parameters

- **{{storySource}}** (string, optional): The sync target — **either** a story file path **or** a Jira issue key. Auto-detected by shape per `story-source-model`. When it is an issue key, the existing issue is **updated**, never re-created.
  - Examples: `PAY-512`, `./payment-retries.story.md`
- **{{storyPath}}** (string, optional): Explicit path to the local `[name].story.md` when `storySource` is an issue key or omitted. Used to locate the content to diff.
- **{{projectKey}}** (string, optional): Target Jira project for a first-sync create. When omitted, the jira config's default project is used.

At least one of `storySource` or `storyPath` is needed to locate the story. If neither resolves to readable content, ask the user before proceeding.

## Instructions

Load **{{skill:story-jira-sync}}** and execute its Invocation Contract with these inputs:

| Parameter | Skill input |
|---|---|
| `{{storySource}}` | `storySource` |
| `{{storyPath}}` | `storyPath` |
| `{{projectKey}}` | `projectKey` |

The skill owns the delta-sync method (get → diff → push), the field mapping, the acceptance-criteria merge mode, conflict surfacing, config remediation, and the error catalogue. It loads **{{skill:story-source-model}}** for source detection and recording the issue key, and **{{skill:story-epic-linking}}** to ride a recorded parent epic along on the create/update call.

Every Atlassian operation happens inside the jira package's skills (`{{skill:jira.retrieve-jira}}`, `{{skill:jira.create-jira-issues}}` / `{{skill:jira.update-jira-issues}}` with `profileName: Story`). Neither this prompt nor the story layer talks to Atlassian directly.

## Response Format

```json
{
  "success": true,
  "storyPath": "./payment-retries.story.md",
  "issueKey": "PAY-512",
  "fieldsChanged": ["summary", "acceptanceCriteria"],
  "conflictReport": null
}
```

**Field descriptions:**

- `success`: Whether the sync completed (including a clean no-op when nothing changed).
- `storyPath`: The local story that was synced.
- `issueKey`: The created or updated Jira issue key.
- `fieldsChanged`: The fields actually pushed (`summary`, `description`, `acceptanceCriteria`). Empty when the story already matched Jira.
- `conflictReport`: An object describing surfaced divergences and their resolution, or `null` when there were no conflicts.

## Error Handling

Return the error and stop. See `story-jira-sync` (Invocation Contract → Errors) for the full detail and recovery.

- **StoryNotFoundError** (`STORY_NOT_FOUND`) — the story file cannot be located; carries `storyPath`. No jira call is made.
- **ConnectionError** (`CONNECTION_FAILED`) — relayed from jira; the Atlassian MCP is not connected or authenticated.
- **IssueNotFoundError** (`ISSUE_NOT_FOUND`) — relayed from jira; the issue key does not exist.
- **ConfigInvalidError** (`CONFIG_INVALID`), **ProjectNotInConfigError** (`PROJECT_NOT_IN_CONFIG`), **DefaultProjectKeyMissingError** (`DEFAULT_PROJECT_KEY_MISSING`) — relayed from jira; point the user at `{{skill:jira.configure-jira}}` or `{{skill:jira.verify-jira-config}}`.

## Notes

- **Story is truth, Jira is transport.** Push, don't pull — the one exception is conflict surfacing.
- **Lifecycle is separate.** Status transitions, assignment, and the estimate are handled by `transitionStory`, `assignStory`, and `pointStory`, not this prompt.
- **Parent epic rides along.** A recorded parent epic is pushed via `parentKey` on create/update; setting or clearing the parent on its own is `linkStoryToEpic`.
