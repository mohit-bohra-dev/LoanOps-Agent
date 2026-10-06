# Transition Story

Move a story's Jira issue to a target workflow status (its **state**).

## Parameters

- **{{issueKey}}** (string, optional): The Jira issue key to transition (e.g. `PAY-512`).
- **{{storyPath}}** (string, optional): Path to the local `[name].story.md`; used to resolve a recorded issue key when `issueKey` is not given.
- **{{status}}** (string, required): The target status name (e.g. `In Development`, `In Review`, `Done`). Team-specific and opaque — passed through verbatim.

One of `issueKey` or a `storyPath` with a recorded key is required.

## Instructions

Load **{{skill:story-jira-lifecycle}}** and execute its Invocation Contract with `operation: transition` and these inputs:

| Parameter | Skill input |
|---|---|
| — | `operation` = `transition` |
| `{{issueKey}}` | `issueKey` |
| `{{storyPath}}` | `storyPath` |
| `{{status}}` | `status` |

The skill owns issue-key resolution, the transition call, the opaque-status-name rule, and the error catalogue. It loads **{{skill:story-source-model}}** when resolving a key from a file, and performs the transition through **{{skill:jira.update-jira-issues}}** (`profileName: Story`, `transition`).

## Response Format

```json
{
  "success": true,
  "issueKey": "PAY-512",
  "status": "In Development",
  "transitioned": true
}
```

**Field descriptions:**

- `success`: Whether the transition completed.
- `issueKey`: The transitioned issue.
- `status`: The target status requested.
- `transitioned`: Whether the status actually changed (false on a no-op when already in the target status).

## Error Handling

Return the error and stop. See `story-jira-lifecycle` (Invocation Contract → Errors) for the full detail and recovery.

- **NoIssueKeyError** (`NO_ISSUE_KEY`) — no issue key was provided or recorded; run `syncStoryToJira` first to create and link an issue.
- **TransitionError** (`TRANSITION_FAILED`) — relayed from jira; the requested status is not reachable from the current one. Report it and ask for the correct target — never guess.
- **ConnectionError** (`CONNECTION_FAILED`), **IssueNotFoundError** (`ISSUE_NOT_FOUND`) — relayed from jira verbatim.

## Notes

- **State only.** Assignment is handled by `assignStory`, the estimate by `pointStory`, and content by `syncStoryToJira`.
- **Status names are team-specific.** Treat `status` as opaque; never substitute a "canonical" name. On `TRANSITION_FAILED`, ask rather than guess.
