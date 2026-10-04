# Create Jira Story

Create a new Story issue in Jira. Thin dispatcher around the `create-jira-issues` workflow skill.

## Parameters

- **{{projectKey}}** (string, optional): Jira project key the story should be created in (e.g., `AIP`, `PCG`). When omitted, the workflow falls back to top-level `defaultProjectKey` in `.ai/jira.config.json`. If neither is set, the workflow halts with `DefaultProjectKeyMissingError`.
- **{{summary}}** (string, required): Story title / summary
- **{{description}}** (string, optional): Story description in markdown format
- **{{acceptanceCriteria}}** (string, optional): Acceptance criteria as a comma-separated or newline-separated list (set in a separate API call as ADF after creation)
- **{{labels}}** (string, optional): Comma-separated labels to apply to the story
- **{{parentKey}}** (string, optional): Issue key of the parent **Epic** to link this story under (the Epic Link / parent relationship), e.g., `PROJ-100`. When omitted, the story is created without a parent.
- **{{storyPoints}}** (number, optional): Numeric story-point estimate. Setting it at create time avoids a follow-up edit in projects whose workflow requires points before a story may leave `Backlog`.

## Instructions

Load `{{skill:jira.create-jira-issues}}` and execute it with these inputs.

| Workflow input | Value |
|---|---|
| `profileName` | `Story` |
| `projectKey` | `{{projectKey}}` (omit to fall back to `config.defaultProjectKey`) |
| `summary` | `{{summary}}` |
| `description` | `{{description}}` |
| `acceptanceCriteria` | `{{acceptanceCriteria}}` (parsed by the skill into a list) |
| `labels` | `{{labels}}` (parsed by the skill into an array) |
| `parentKey` | `{{parentKey}}` (only if provided — links the story to its parent Epic) |
| `storyPoints` | `{{storyPoints}}` (only if provided — written as a bare number to the configured Story Points field) |

The Story profile sets `acceptanceCriteriaMode = adf-field`, so the skill will:

1. Validate the MCP connection (via `validate-mcp-connection`)
2. Assemble required fields per the Story profile in the skill's `issue-type-requirements` reference
3. Ask for explicit user approval before creating
4. Call `createJiraIssue`
5. If `acceptanceCriteria` is provided, delegate to the `set-acceptance-criteria` skill (separate API call with ADF JSON)
6. Verify with `getJiraIssue` and report

Return the skill's response unchanged.

## Response Format

### Success Response

```json
{
  "success": true,
  "issueKey": "PROJ-123",
  "summary": "Story summary here",
  "issueType": "Story",
  "url": "https://pennymac.atlassian.net/browse/PROJ-123"
}
```

## Error Handling

Errors are surfaced as returned by the `create-jira-issues` skill:

- `ConnectionError` (`CONNECTION_FAILED`) -- MCP connection failed
- `CreationError` (`CREATION_FAILED`) -- `createJiraIssue` returned an unrecoverable error
- `FieldValidationError` (`FIELD_VALIDATION_FAILED`) -- a required field was missing or invalid
- `UserCancelled` (`USER_CANCELLED`) -- the user declined the proposed creation
- `ConfigInvalidError` (`CONFIG_INVALID`) -- `.ai/jira.config.json` failed schema validation; run `{{skill:jira.verify-jira-config}}` to inspect the drift
- `BootstrapFailedError` (`BOOTSTRAP_FAILED`) -- `configure-jira` reported success but the freshly-written config could not be re-loaded
- `ProjectNotInConfigError` (`PROJECT_NOT_IN_CONFIG`) -- the resolved project key has no entry in `config.projects` and the user declined to bootstrap it
- `DefaultProjectKeyMissingError` (`DEFAULT_PROJECT_KEY_MISSING`) -- neither `projectKey` parameter nor `config.defaultProjectKey` is set

```json
{ "code": "CONNECTION_FAILED", "message": "Unable to connect to Atlassian MCP server", "details": "..." }
```
