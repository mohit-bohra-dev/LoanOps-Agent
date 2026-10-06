# Update Jira Bug

Update fields on an existing Jira Bug. Thin dispatcher around the `update-jira-issues` workflow skill. Bugs use `acceptanceCriteriaMode = inline-description`, so AC updates are merged into the description rather than written to the AC custom field.

## Parameters

- **{{issueKey}}** (string, required): The Jira issue key to update (e.g., `PROJ-123`)
- **{{summary}}** (string, optional): Updated bug title
- **{{description}}** (string, optional): Updated description in markdown format
  - If `acceptanceCriteria` is also provided, it will be merged into the description by the skill
- **{{acceptanceCriteria}}** (string, optional): Updated acceptance criteria
  - Merged into the description (NOT written to the AC custom field, which is unavailable for Bugs)
- **{{environment}}** (string, optional): Updated environment value
- **{{severity}}** (string, optional): Updated severity level
- **{{testPhase}}** (string, optional): Updated test phase
- **{{responsibleTeam}}** (string, optional): Updated responsible development team
- **{{labels}}** (string, optional): Comma-separated labels (replaces existing labels)
- **{{transition}}** (string, optional): Transition the bug to this status

Allowed values for `environment`, `severity`, `testPhase`, and `responsibleTeam` are documented in the `create-jira-issues` skill's `jira-field-mappings` reference.

## Instructions

Load `{{skill:jira.update-jira-issues}}` and execute it with these inputs.

| Workflow input | Value |
|---|---|
| `profileName` | `Bug` |
| `issueKey` | `{{issueKey}}` |
| `summary` | `{{summary}}` (only if provided) |
| `description` | `{{description}}` (only if provided) |
| `acceptanceCriteria` | `{{acceptanceCriteria}}` (only if provided; merged into description by skill) |
| `labels` | `{{labels}}` (only if provided) |
| `environment` | `{{environment}}` (only if provided) |
| `severity` | `{{severity}}` (only if provided) |
| `testPhase` | `{{testPhase}}` (only if provided) |
| `responsibleTeam` | `{{responsibleTeam}}` (only if provided) |
| `transition` | `{{transition}}` (only if provided) |

The Bug profile sets `acceptanceCriteriaMode = inline-description`. The skill merges AC into description and applies the four bug-specific fields alongside summary + labels in a single `editJiraIssue` call (no ADF involved -- safe to combine).

Return the skill's response unchanged.

## Response Format

### Success Response

```json
{
  "success": true,
  "issueKey": "PROJ-123",
  "fieldsUpdated": ["summary", "description", "severity"],
  "transitioned": false
}
```

## Error Handling

Errors are surfaced as returned by the `update-jira-issues` skill:

- `ConnectionError` (`CONNECTION_FAILED`)
- `IssueNotFoundError` (`ISSUE_NOT_FOUND`)
- `UpdateError` (`UPDATE_FAILED`)
- `FieldValidationError` (`FIELD_VALIDATION_FAILED`) -- common for invalid bug-specific values
- `TransitionError` (`TRANSITION_FAILED`)
- `UserCancelled` (`USER_CANCELLED`)

```json
{ "code": "FIELD_VALIDATION_FAILED", "message": "Invalid environment value", "field": "environment", "details": "..." }
```
