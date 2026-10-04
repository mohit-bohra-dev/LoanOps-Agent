# Update Jira Task

Update fields on an existing Jira Task. Thin dispatcher around the `update-jira-issues` workflow skill.

## Parameters

- **{{issueKey}}** (string, required): The Jira issue key to update (e.g., `PROJ-123`)
- **{{summary}}** (string, optional): Updated task title
- **{{description}}** (string, optional): Updated description in markdown format
- **{{acceptanceCriteria}}** (string, optional): Updated acceptance criteria as a comma-separated or newline-separated list (applied as ADF in a separate API call)
- **{{labels}}** (string, optional): Comma-separated labels (replaces existing labels)
- **{{transition}}** (string, optional): Transition the task to this status (e.g., `To Do`, `In Progress`, `Done`)

## Instructions

Load `{{skill:jira.update-jira-issues}}` and execute it with these inputs.

| Workflow input | Value |
|---|---|
| `profileName` | `Task` |
| `issueKey` | `{{issueKey}}` |
| `summary` | `{{summary}}` (only if provided) |
| `description` | `{{description}}` (only if provided) |
| `acceptanceCriteria` | `{{acceptanceCriteria}}` (only if provided) |
| `labels` | `{{labels}}` (only if provided) |
| `transition` | `{{transition}}` (only if provided) |

The Task profile sets `acceptanceCriteriaMode = adf-field`. The skill applies updates in separate API calls (summary + labels; AC via ADF; description as markdown), optionally transitions status, and verifies.

Return the skill's response unchanged.

## Response Format

### Success Response

```json
{
  "success": true,
  "issueKey": "PROJ-123",
  "fieldsUpdated": ["summary", "description"],
  "transitioned": false
}
```

## Error Handling

Errors are surfaced as returned by the `update-jira-issues` skill:

- `ConnectionError` (`CONNECTION_FAILED`)
- `IssueNotFoundError` (`ISSUE_NOT_FOUND`)
- `UpdateError` (`UPDATE_FAILED`)
- `TransitionError` (`TRANSITION_FAILED`)
- `UserCancelled` (`USER_CANCELLED`)

```json
{ "code": "UPDATE_FAILED", "message": "Failed to update field", "field": "labels", "details": "..." }
```
