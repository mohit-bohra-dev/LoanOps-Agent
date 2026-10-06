# Create Jira Epic

Create a new Epic issue in Jira. Thin dispatcher around the `create-jira-issues` workflow skill. Epics group related Stories, Tasks, and Bugs under a higher-level initiative or capability theme.

## Parameters

- **{{projectKey}}** (string, optional): Jira project key the epic should be created in (e.g., `AIP`, `PCG`). When omitted, the workflow falls back to top-level `defaultProjectKey` in `.ai/jira.config.json`. If neither is set, the workflow halts with `DefaultProjectKeyMissingError`.
- **{{summary}}** (string, required): Epic title / summary (also serves as the Epic Name in modern Jira)
- **{{description}}** (string, optional): Epic description in markdown format
  - Recommended sections: Overview, User Problem, Key Features, Success Metrics, Dependencies
- **{{acceptanceCriteria}}** (string, optional): High-level epic-completion acceptance criteria as a comma-separated or newline-separated list. By default the workflow appends these to the description (`inline-description` mode); when the project exposes the AC custom field on Epic, the workflow sets it via a separate ADF API call instead.
- **{{labels}}** (string, optional): Comma-separated labels to apply (e.g., initiative or theme keys like `pitcrew`, `phase-2`)
- **{{priority}}** (string, optional): Priority name as defined in the target Jira instance (e.g. `High`, `Medium`, `Low`, or `Highest`/`Lowest` where the project defines them). Sent as the standard `priority` field in object form — `{"name": "<priority>"}`. Omit to let the project's default apply. Names are **instance-specific and passed through unchanged**; an unknown name comes back as `FieldValidationError`.
- **{{epicName}}** (string, optional): Separate Epic Name field, when the consuming Jira project keeps Epic Name distinct from `summary`. Maps to `{{epicNameFieldId}}`
- **{{targetStartDate}}** (string, optional): Target start date in `YYYY-MM-DD` format. Maps to `{{epicStartDateFieldId}}`
- **{{targetEndDate}}** (string, optional): Target end date in `YYYY-MM-DD` format. Maps to `{{epicEndDateFieldId}}`
- **{{theme}}** (string, optional): Epic theme value, when the consuming project defines themes. Maps to `{{epicThemeFieldId}}`

The four Epic-specific parameters (`epicName`, `targetStartDate`, `targetEndDate`, `theme`) are optional and only meaningful when the consuming team has configured the corresponding placeholders. See the `create-jira-issues` skill's `jira-field-mappings` reference (Epic-Specific Fields) for the full list. `priority` is different — it is a **standard** Jira field (see Standard Jira Fields in the same reference), so it needs no field-id configuration.

## Instructions

Load `{{skill:jira.create-jira-issues}}` and execute it with these inputs.


| Workflow input                        | Value                                                               |
| ------------------------------------- | ------------------------------------------------------------------- |
| `profileName`                         | `Epic`                                                              |
| `projectKey`                          | `{{projectKey}}` (omit to fall back to `config.defaultProjectKey`)  |
| `summary`                             | `{{summary}}`                                                       |
| `description`                         | `{{description}}`                                                   |
| `acceptanceCriteria`                  | `{{acceptanceCriteria}}`                                            |
| `labels`                              | `{{labels}}`                                                        |
| `priority`                            | `{{priority}}` (only if provided -- standard field, object form)    |
| `epicExtras.{{epicNameFieldId}}`      | `{{epicName}}` (only if provided)                                   |
| `epicExtras.{{epicStartDateFieldId}}` | `{{targetStartDate}}` (only if provided)                            |
| `epicExtras.{{epicEndDateFieldId}}`   | `{{targetEndDate}}` (only if provided)                              |
| `epicExtras.{{epicThemeFieldId}}`     | `{"value": "{{theme}}"}` (only if provided -- single-select format) |


The Epic profile sets `acceptanceCriteriaMode = inline-description` by default (most projects, including AIP, do not expose the AC custom field on Epic). The skill will:

1. Validate the MCP connection (via `validate-mcp-connection`)
2. Assemble required fields per the Epic profile in the skill's `issue-type-requirements` reference
3. Merge any provided `epicExtras` into `additional_fields`
4. Append the `acceptanceCriteria` list as a `## Acceptance Criteria` section to `description` (inline-description mode)
5. Ask for explicit user approval before creating
6. Call `createJiraIssue`
7. (Adf-field mode only — when the project exposes the AC custom field on Epic) Delegate to the `set-acceptance-criteria` skill in a separate API call
8. Verify with `getJiraIssue` and report

If a consuming project's Jira **does** expose the AC custom field on Epic, the Epic profile's `acceptanceCriteriaMode` is flipped to `adf-field` per the AC Mode Detection note in `issue-type-requirements.md`. No prompt change is required -- the dispatch is handled in the workflow skill.

Return the skill's response unchanged.

## Response Format

### Success Response

```json
{
  "success": true,
  "issueKey": "PROJ-123",
  "summary": "Epic summary here",
  "issueType": "Epic",
  "url": "https://pennymac.atlassian.net/browse/PROJ-123"
}
```

## Error Handling

Errors are surfaced as returned by the `create-jira-issues` skill:

- `ConnectionError` (`CONNECTION_FAILED`) -- MCP connection failed
- `CreationError` (`CREATION_FAILED`) -- `createJiraIssue` returned an unrecoverable error
- `FieldValidationError` (`FIELD_VALIDATION_FAILED`) -- a required field was missing, an Epic-specific value was invalid, or the AC field is not available on Epic in this project (consider switching to `inline-description` mode)
- `UserCancelled` (`USER_CANCELLED`) -- the user declined the proposed creation
- `ConfigInvalidError` (`CONFIG_INVALID`) -- `.ai/jira.config.json` failed schema validation; run `{{skill:jira.verify-jira-config}}` to inspect the drift
- `BootstrapFailedError` (`BOOTSTRAP_FAILED`) -- `configure-jira` reported success but the freshly-written config could not be re-loaded
- `ProjectNotInConfigError` (`PROJECT_NOT_IN_CONFIG`) -- the resolved project key has no entry in `config.projects` and the user declined to bootstrap it
- `DefaultProjectKeyMissingError` (`DEFAULT_PROJECT_KEY_MISSING`) -- neither `projectKey` parameter nor `config.defaultProjectKey` is set

```json
{ "code": "CONNECTION_FAILED", "message": "Unable to connect to Atlassian MCP server", "details": "..." }
```

## Notes

- **Epic Name vs Summary:** Modern Jira projects use `summary` as the Epic Name. Older projects may keep Epic Name as a separate custom field; provide `epicName` when that's the case.
- **AC Field Availability:** The Epic AC field availability varies by Jira project configuration. The default mode is `inline-description` (verified for AIP, where Epic does not expose the AC custom field). If your project exposes `{{acceptanceCriteriaFieldId}}` for Epic, flip the Epic profile's `acceptanceCriteriaMode` to `adf-field` (handled in the `create-jira-issues` skill / `issue-type-requirements.md`).
- **Children:** Linking child Stories / Tasks / Bugs to this Epic is a follow-up step done by setting the parent / Epic Link field on the children, not on the Epic itself.

