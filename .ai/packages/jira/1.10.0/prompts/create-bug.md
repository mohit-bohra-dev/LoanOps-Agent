# Create Jira Bug

Create a new Bug issue in Jira. Thin dispatcher around the `create-jira-issues` workflow skill. Bugs require additional mandatory fields (Environment, Severity, Test Phase, Responsible Dev Team) and the AC custom field is **not available**, so AC is merged into the description.

## Parameters

- **{{projectKey}}** (string, optional): Jira project key the bug should be created in (e.g., `AIP`, `PCG`). When omitted, the workflow falls back to top-level `defaultProjectKey` in `.ai/jira.config.json`. If neither is set, the workflow halts with `DefaultProjectKeyMissingError`.
- **{{summary}}** (string, required): Bug title / summary
- **{{description}}** (string, optional): Bug description in markdown
  - Should include: Summary, Steps to Reproduce, Expected Behavior, Actual Behavior
- **{{acceptanceCriteria}}** (string, optional): Acceptance criteria as a comma-separated or newline-separated list
  - Will be appended to the description (NOT placed in the AC custom field)
- **{{environment}}** (string, optional): Environment where the bug was found. Default: `PRD`
- **{{severity}}** (string, optional): Bug severity level. Default: `Sev 2`
- **{{testPhase}}** (string, optional): Testing phase where bug was discovered. Default: `Production`
- **{{responsibleTeam}}** (string, optional): Development team responsible for the fix. Default: `Pennymac`
- **{{labels}}** (string, optional): Comma-separated labels to apply to the bug

Allowed values for `environment`, `severity`, `testPhase`, and `responsibleTeam` are documented in the skill's `jira-field-mappings` reference (Bug Field Allowed Values).

## Instructions

Load `{{skill:jira.create-jira-issues}}` and execute it with these inputs.

| Workflow input | Value |
|---|---|
| `profileName` | `Bug` |
| `projectKey` | `{{projectKey}}` (omit to fall back to `config.defaultProjectKey`) |
| `summary` | `{{summary}}` |
| `description` | `{{description}}` |
| `acceptanceCriteria` | `{{acceptanceCriteria}}` (merged into description by the skill, since AC field is unavailable) |
| `labels` | `{{labels}}` |
| `environment` | `{{environment}}` |
| `severity` | `{{severity}}` |
| `testPhase` | `{{testPhase}}` |
| `responsibleTeam` | `{{responsibleTeam}}` |

The Bug profile sets `acceptanceCriteriaMode = inline-description`, so the skill appends a `## Acceptance Criteria` section into the description before creation rather than calling `set-acceptance-criteria`. The four bug-specific custom fields are resolved from `.ai/jira.config.json` and added per the Bug profile in the skill's `issue-type-requirements` reference.

Return the skill's response unchanged.

## Response Format

### Success Response

```json
{
  "success": true,
  "issueKey": "PROJ-123",
  "summary": "Bug summary here",
  "issueType": "Bug",
  "environment": "PRD",
  "severity": "Sev 2",
  "url": "https://pennymac.atlassian.net/browse/PROJ-123"
}
```

## Error Handling

Errors are surfaced as returned by the `create-jira-issues` skill:

- `ConnectionError` (`CONNECTION_FAILED`)
- `CreationError` (`CREATION_FAILED`)
- `FieldValidationError` (`FIELD_VALIDATION_FAILED`) -- common for invalid `environment`, `severity`, `testPhase`, or `responsibleTeam` values; verify against the skill's `jira-field-mappings` reference
- `UserCancelled` (`USER_CANCELLED`)
- `ConfigInvalidError` (`CONFIG_INVALID`) -- `.ai/jira.config.json` failed schema validation; run `{{skill:jira.verify-jira-config}}` to inspect the drift
- `BootstrapFailedError` (`BOOTSTRAP_FAILED`) -- `configure-jira` reported success but the freshly-written config could not be re-loaded
- `ProjectNotInConfigError` (`PROJECT_NOT_IN_CONFIG`) -- the resolved project key has no entry in `config.projects` and the user declined to bootstrap it
- `DefaultProjectKeyMissingError` (`DEFAULT_PROJECT_KEY_MISSING`) -- neither `projectKey` parameter nor `config.defaultProjectKey` is set

```json
{ "code": "FIELD_VALIDATION_FAILED", "message": "Invalid severity value", "field": "severity", "details": "Must be one of: Sev 1, Sev 2, Sev 3, TBD" }
```
