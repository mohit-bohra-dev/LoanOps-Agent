# Verify Jira Config

Detect drift between the team's `.ai/jira.config.json` and the live Jira project(s). Read-only — never mutates Jira state.

## Parameters

- **{{projectKey}}** (string, optional): Jira project key to verify (e.g., `AIP`, `PCG`). When provided → single-project mode. When omitted → all-projects mode (iterates every entry in `config.projects`). There is **no fallback** to `config.defaultProjectKey`; omitting the parameter explicitly selects all-projects mode.
- **{{issueTypes}}** (string, optional): Comma-separated list of issue type names to verify (e.g., `"Story,Epic"`), parsed into a `string[]` before invoking the skill. Defaults to all issue types each project exposes. In all-projects mode the same filter applies uniformly to every project.

## Instructions

Load `{{skill:jira.verify-jira-config}}` and execute it with these inputs.

| Skill input | Value |
|---|---|
| `cloudId` | obtained from `validate-mcp-connection` (invoked by the skill's prerequisite chain) |
| `projectKey` | `{{projectKey}}` (omit for all-projects mode) |
| `issueTypes` | `{{issueTypes}}` (parsed into an array) |

The skill loads the config in full multi-project mode, determines the verification list, discovers live issue types and per-type field metadata for each project, compares configured field IDs / AC modes / required-field coverage against that metadata, and returns either a flat single-project DriftReport or a multi-project envelope with one sub-report per project.

Return the skill's response unchanged.

## Response Format

### Single-project Response

```json
{
  "outcome": "drift-detected",
  "mode": "single-project",
  "configPath": "/abs/path/to/.ai/jira.config.json",
  "projectKey": "AIP",
  "issueTypesChecked": ["Story", "Task", "Bug", "Sub-task", "Epic"],
  "findings": {
    "fieldIdDrift": [{ "category": "field-id-missing", "logicalName": "channel", "configuredId": "customfield_10253" }],
    "acModeDrift": [{ "category": "ac-mode-drift", "issueType": "Epic", "expected": "adf-field", "live": "no-ac-field", "suggestedFix": "set issueTypeOverrides.Epic.acceptanceCriteriaMode = inline-description" }],
    "requiredFieldDrift": []
  }
}
```

`outcome` is `no-drift` or `drift-detected`; `findings` is present only when drift was detected.

### All-projects Response (envelope)

```json
{
  "outcome": "drift-detected",
  "mode": "all-projects",
  "configPath": "/abs/path/to/.ai/jira.config.json",
  "projects": {
    "AIP": { "outcome": "no-drift", "projectKey": "AIP", "issueTypesChecked": ["Story", "Epic"] },
    "PCG": { "outcome": "drift-detected", "projectKey": "PCG", "issueTypesChecked": ["Story", "Bug"], "findings": { "fieldIdDrift": [], "acModeDrift": [], "requiredFieldDrift": [] } }
  }
}
```

Each entry under `projects.<KEY>` is shaped like the single-project response. The aggregated top-level `outcome` is `no-drift`, `drift-detected`, `partial-failure` (one project errored while another succeeded), or `total-failure` (every project errored).

## Error Handling

Failure outcomes use the same envelope; the `outcome` field is the structured error code:

- `NoConfigError` (`no-config`) — no `.ai/jira.config.json` at any search path; run `{{skill:jira.configure-jira}}` to create one
- `ConfigInvalidError` (`config-invalid`) — the file failed schema validation; the loader's `details` array names each violation
- `ProjectNotInConfigError` (`project-not-in-config`) — single-project mode; the key has no entry. Includes `requestedProjectKey` and `availableProjectKeys`
- `EmptyProjectsConfigError` (`empty-projects-config`) — all-projects mode; `config.projects` is empty
- `ProjectNotAccessibleError` (`project-not-accessible`) — a project's MCP discovery failed. Top-level in single-project mode; per-project in all-projects mode, where iteration continues
- `ConnectionError` (`connection-error`) — MCP connection failed after retries

```json
{ "outcome": "project-not-in-config", "message": "Project 'XYZ' is not configured", "requestedProjectKey": "XYZ", "availableProjectKeys": ["AIP", "PCG"] }
```
