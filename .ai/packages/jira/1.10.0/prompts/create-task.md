# Create Jira Task

Create a new Task issue in Jira (technical work, maintenance, or non-feature work). Thin dispatcher around the `create-jira-issues` workflow skill.

## Parameters

- **{{projectKey}}** (string, optional): Jira project key the task should be created in (e.g., `AIP`, `PCG`). When omitted, the workflow falls back to top-level `defaultProjectKey` in `.ai/jira.config.json`. If neither is set, the workflow halts with `DefaultProjectKeyMissingError`.
- **{{summary}}** (string, required): Task title / summary
- **{{description}}** (string, optional): Task description in markdown format
- **{{acceptanceCriteria}}** (string, optional): Acceptance criteria as a comma-separated or newline-separated list (set in a separate API call as ADF after creation)
- **{{labels}}** (string, optional): Comma-separated labels to apply to the task

## Instructions

Load `{{skill:jira.create-jira-issues}}` and execute it with these inputs.

| Workflow input | Value |
|---|---|
| `profileName` | `Task` |
| `projectKey` | `{{projectKey}}` (omit to fall back to `config.defaultProjectKey`) |
| `summary` | `{{summary}}` |
| `description` | `{{description}}` |
| `acceptanceCriteria` | `{{acceptanceCriteria}}` |
| `labels` | `{{labels}}` |

The Task profile sets `acceptanceCriteriaMode = adf-field`. The skill validates the connection, assembles fields per its `issue-type-requirements` reference, asks for user approval, creates the issue, applies AC via the `set-acceptance-criteria` skill in a separate call, and verifies the result.

Return the skill's response unchanged.

## Response Format

### Success Response

```json
{
  "success": true,
  "issueKey": "PROJ-123",
  "summary": "Task summary here",
  "issueType": "Task",
  "url": "https://pennymac.atlassian.net/browse/PROJ-123"
}
```

## Error Handling

Errors are surfaced as returned by the `create-jira-issues` skill:

- `ConnectionError` (`CONNECTION_FAILED`)
- `CreationError` (`CREATION_FAILED`)
- `FieldValidationError` (`FIELD_VALIDATION_FAILED`)
- `UserCancelled` (`USER_CANCELLED`)
- `ConfigInvalidError` (`CONFIG_INVALID`) -- `.ai/jira.config.json` failed schema validation; run `{{skill:jira.verify-jira-config}}` to inspect the drift
- `BootstrapFailedError` (`BOOTSTRAP_FAILED`) -- `configure-jira` reported success but the freshly-written config could not be re-loaded
- `ProjectNotInConfigError` (`PROJECT_NOT_IN_CONFIG`) -- the resolved project key has no entry in `config.projects` and the user declined to bootstrap it
- `DefaultProjectKeyMissingError` (`DEFAULT_PROJECT_KEY_MISSING`) -- neither `projectKey` parameter nor `config.defaultProjectKey` is set

```json
{ "code": "CREATION_FAILED", "message": "Failed to create Jira task", "details": "..." }
```
