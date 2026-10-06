# Update Jira Story

Update fields on an existing Jira Story. Thin dispatcher around the `update-jira-issues` workflow skill, which handles the markdown / ADF separation across multiple `editJiraIssue` calls.

## Parameters

- **{{issueKey}}** (string, required): The Jira issue key to update (e.g., `PROJ-123`)
- **{{summary}}** (string, optional): Updated story title
- **{{description}}** (string, optional): Updated description in markdown format
- **{{acceptanceCriteria}}** (string, optional): Updated acceptance criteria as a comma-separated or newline-separated list (applied as ADF in a separate API call)
- **{{acMergeMode}}** (string, optional): How acceptance criteria are applied — `replace` (default, overwrites the whole AC field) or `append` (merges new AC items into the existing ones). Only affects the AC field; ignored when no acceptanceCriteria is provided.
- **{{labels}}** (string, optional): Comma-separated labels (replaces existing labels)
- **{{transition}}** (string, optional): Transition the story to this status (e.g., `To Do`, `In Progress`, `Done`)
- **{{assignee}}** (string, optional): Set the assignee — a Jira account id, the token `me` (the current MCP-authenticated user), or `unassigned` to clear
- **{{parentKey}}** (string, optional): Issue key of the parent **Epic** to link this story under (the Epic Link / parent relationship), e.g., `PROJ-100`. Pass `unassigned` to clear the parent.
- **{{storyPoints}}** (number, optional): Numeric story-point estimate. Many project workflows require it before a story may leave `Backlog`.

## Instructions

Load `{{skill:jira.update-jira-issues}}` and execute it with these inputs.

| Workflow input | Value |
|---|---|
| `profileName` | `Story` |
| `issueKey` | `{{issueKey}}` |
| `summary` | `{{summary}}` (only if provided) |
| `description` | `{{description}}` (only if provided) |
| `acceptanceCriteria` | `{{acceptanceCriteria}}` (only if provided) |
| `acMergeMode` | `{{acMergeMode}}` (only if provided) |
| `labels` | `{{labels}}` (only if provided) |
| `transition` | `{{transition}}` (only if provided) |
| `assignee` | `{{assignee}}` (only if provided) |
| `parentKey` | `{{parentKey}}` (only if provided — re-parents the story to a different Epic, or `unassigned` to clear) |
| `storyPoints` | `{{storyPoints}}` (only if provided — written as a bare number to the configured Story Points field) |

The Story profile sets `acceptanceCriteriaMode = adf-field`, so the skill:

1. Validates the connection and retrieves the current issue
2. Builds a change set from only the parameters provided
3. Asks for explicit user approval showing old to new for each changed field
4. Applies updates in separate API calls (Call 1: summary + labels; Call 2: AC via `set-acceptance-criteria`; Call 3: description)
5. Optionally transitions status
6. Verifies and reports

Return the skill's response unchanged.

## Response Format

### Success Response

```json
{
  "success": true,
  "issueKey": "PROJ-123",
  "fieldsUpdated": ["summary", "description", "acceptanceCriteria"],
  "transitioned": false
}
```

## Error Handling

Errors are surfaced as returned by the `update-jira-issues` skill:

- `ConnectionError` (`CONNECTION_FAILED`)
- `IssueNotFoundError` (`ISSUE_NOT_FOUND`)
- `UpdateError` (`UPDATE_FAILED`)
- `TransitionError` (`TRANSITION_FAILED`) -- when the requested transition is not available from the issue's current status
- `UserCancelled` (`USER_CANCELLED`)

```json
{ "code": "ISSUE_NOT_FOUND", "message": "Jira issue 'PROJ-999' not found", "issueKey": "PROJ-999" }
```
