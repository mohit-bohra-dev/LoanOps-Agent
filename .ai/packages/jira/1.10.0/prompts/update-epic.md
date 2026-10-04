# Update Jira Epic

Update fields on an existing Jira Epic. Thin dispatcher around the `update-jira-issues` workflow skill, which handles the markdown / ADF separation across multiple `editJiraIssue` calls.

## Parameters

- **{{issueKey}}** (string, required): The Jira issue key to update (e.g., `PROJ-123`)
- **{{summary}}** (string, optional): Updated epic title (also serves as the Epic Name in modern Jira)
- **{{description}}** (string, optional): Updated description in markdown format
- **{{acceptanceCriteria}}** (string, optional): Updated high-level epic-completion acceptance criteria as a comma-separated or newline-separated list. By default the workflow merges these into the description (`inline-description` mode); when the project exposes the AC custom field on Epic, the workflow sets it via a separate ADF API call instead.
- **{{acMergeMode}}** (string, optional): How acceptance criteria are applied when the effective AC mode is `adf-field` — `replace` (default, overwrites the whole AC field) or `append` (merges new AC items into the existing ones). Ignored for `inline-description` (the Epic default in most projects) and when no acceptanceCriteria is provided.
- **{{labels}}** (string, optional): Comma-separated labels (replaces existing labels)
- **{{priority}}** (string, optional): Updated priority name as defined in the target Jira instance (e.g. `High`, `Medium`, `Low`). Sent as the standard `priority` field in object form — `{"name": "<priority>"}`. Omit to leave the current priority untouched; there is no "clear" token, since Jira issues always carry a priority.
- **{{transition}}** (string, optional): Transition the epic to this status (e.g., `To Do`, `In Progress`, `Done`)
- **{{assignee}}** (string, optional): Set the assignee — a Jira account id, the token `me` (the current MCP-authenticated user), or `unassigned` to clear
- **{{epicName}}** (string, optional): Separate Epic Name field, when the consuming Jira project keeps Epic Name distinct from `summary`. Maps to `{{epicNameFieldId}}`
- **{{targetStartDate}}** (string, optional): Target start date in `YYYY-MM-DD` format. Maps to `{{epicStartDateFieldId}}`
- **{{targetEndDate}}** (string, optional): Target end date in `YYYY-MM-DD` format. Maps to `{{epicEndDateFieldId}}`
- **{{theme}}** (string, optional): Epic theme value, when the consuming project defines themes. Maps to `{{epicThemeFieldId}}`

The four Epic-specific parameters (`epicName`, `targetStartDate`, `targetEndDate`, `theme`) are optional and only meaningful when the consuming team has configured the corresponding placeholders. See the `create-jira-issues` skill's `jira-field-mappings` reference (Epic-Specific Fields) for the full list. `priority` is different — it is a **standard** Jira field (see Standard Jira Fields in the same reference), so it needs no field-id configuration.

## Instructions

Load `{{skill:jira.update-jira-issues}}` and execute it with these inputs.

| Workflow input | Value |
|---|---|
| `profileName` | `Epic` |
| `issueKey` | `{{issueKey}}` |
| `summary` | `{{summary}}` (only if provided) |
| `description` | `{{description}}` (only if provided) |
| `acceptanceCriteria` | `{{acceptanceCriteria}}` (only if provided) |
| `acMergeMode` | `{{acMergeMode}}` (only if provided) |
| `labels` | `{{labels}}` (only if provided) |
| `priority` | `{{priority}}` (only if provided -- standard field, object form) |
| `transition` | `{{transition}}` (only if provided) |
| `assignee` | `{{assignee}}` (only if provided) |
| `epicExtras.{{epicNameFieldId}}` | `{{epicName}}` (only if provided) |
| `epicExtras.{{epicStartDateFieldId}}` | `{{targetStartDate}}` (only if provided) |
| `epicExtras.{{epicEndDateFieldId}}` | `{{targetEndDate}}` (only if provided) |
| `epicExtras.{{epicThemeFieldId}}` | `{"value": "{{theme}}"}` (only if provided -- single-select format) |

The Epic profile sets `acceptanceCriteriaMode = inline-description` by default (most projects, including AIP, do not expose the AC custom field on Epic). The skill will:

1. Validate the connection and retrieve the current issue
2. Build a change set from only the parameters provided (merging any `epicExtras` into `additional_fields`)
3. Ask for explicit user approval showing old to new for each changed field
4. Apply updates in separate API calls (Call 1: summary + labels + assignee + epic extras; Call 2: AC via `set-acceptance-criteria` only in `adf-field` mode; Call 3: description, with AC merged in for `inline-description` mode)
5. Optionally transition status
6. Verify and report

If a consuming project's Jira **does** expose the AC custom field on Epic, the effective AC mode is `adf-field` per the AC Mode Detection note in `issue-type-requirements.md`. No prompt change is required — the dispatch is handled in the workflow skill.

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

When `transition` was applied, `transitioned: true` and the response includes the new status name.

## Error Handling

Errors are surfaced as returned by the `update-jira-issues` skill:

- `ConnectionError` (`CONNECTION_FAILED`)
- `IssueNotFoundError` (`ISSUE_NOT_FOUND`)
- `FieldValidationError` (`FIELD_VALIDATION_FAILED`) -- an invalid Epic-specific value, or the AC field is not available on Epic in this project (the workflow falls back to `inline-description`)
- `UpdateError` (`UPDATE_FAILED`)
- `TransitionError` (`TRANSITION_FAILED`) -- when the requested transition is not available from the issue's current status
- `UserCancelled` (`USER_CANCELLED`)

```json
{ "code": "ISSUE_NOT_FOUND", "message": "Jira issue 'PROJ-999' not found", "issueKey": "PROJ-999" }
```

## Notes

- **Epic Name vs Summary:** Modern Jira projects use `summary` as the Epic Name. Older projects may keep Epic Name as a separate custom field; provide `epicName` when that's the case.
- **AC Field Availability:** The Epic AC field availability varies by Jira project configuration. The default mode is `inline-description` (verified for AIP, where Epic does not expose the AC custom field). When the project exposes `{{acceptanceCriteriaFieldId}}` for Epic, the effective mode flips to `adf-field` (handled in the `update-jira-issues` skill / `issue-type-requirements.md`), and `acMergeMode` then controls append vs replace.
- **Children:** Linking child Stories / Tasks / Bugs to this Epic is done by setting the parent / Epic Link field on the children — the `parentKey` parameter when creating or updating a Story or Task — not on the Epic itself.
