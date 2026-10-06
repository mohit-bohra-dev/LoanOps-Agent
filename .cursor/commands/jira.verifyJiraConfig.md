---
promp:
  package: "jira"
  version: "1.10.0"
  environment: "development"
  prompVersion: "1.0.1-beta.83"
  prompt: "verifyJiraConfig"
---
# jira.verifyJiraConfig

Detect drift between the team's .ai/jira.config.json and live Jira project(s). Multi-project: when projectKey is supplied, verifies that single project; when omitted, iterates every entry in config.projects and returns a multi-project envelope with one DriftReport per project. Compares configured field IDs, AC handling modes, and required-field coverage against MCP discovery data. Read-only — never mutates Jira state.

## Parameter Specifications

- **`projectKey`** (string) - *Optional*
  - Jira project key to verify against. When provided, runs in single-project mode. When omitted, runs in all-projects mode and iterates every entry in config.projects.

- **`issueTypes`** (string) - *Optional*
  - Comma-separated list of issue type names to verify (e.g., 'Story,Epic'). Defaults to all issue types each project exposes. Applied uniformly to every project in all-projects mode.

## Instructions

You are executing a Promp package prompt. Follow these steps:

1. **Parse the user input** to extract parameters:
   - Parameter 1: `projectKey` (optional) - Jira project key to verify against. When provided, runs in single-project mode. When omitted, runs in all-projects mode and iterates every entry in config.projects.
   - Parameter 2: `issueTypes` (optional) - Comma-separated list of issue type names to verify (e.g., 'Story,Epic'). Defaults to all issue types each project exposes. Applied uniformly to every project in all-projects mode.

2. **Replace parameter placeholders** in the prompt content below:
   - Parameters use the format `{{parameterName}}` in the prompt
   - Replace each placeholder with the corresponding parsed value
   - If a parameter is optional and not provided, use its default value (if specified)
   - If a required parameter is missing, ask the user to provide it

3. **Execute the prompt** with the replaced parameters

## Usage

When the user invokes this command, they may provide parameters in various ways:
- Space-separated values: `/jira.verifyJiraConfig value1 value2`
- Named parameters: `/jira.verifyJiraConfig param1=value1 param2=value2`
- Mixed format: `/jira.verifyJiraConfig value1 param2=value2`

Parse flexibly and map values to the expected parameters in order for positional arguments.

## Expected Output

Drift detection report. Shape varies by mode: single-project returns a flat report; all-projects returns an envelope containing per-project sub-reports under projects.<KEY>.

**Type:** `object`

**Properties:**

- `outcome` (string) - **Required** - Aggregated outcome. In single-project mode this is the project's outcome. In all-projects mode: no-drift if all projects pass; drift-detected if any project has drift; partial-failure if at least one project errored AND another succeeded; total-failure if every project errored.
- `mode` (string) - **Required** - Which verification mode produced this report
- `configPath` (string) - *Optional* - 
- `projectKey` (string) - *Optional* - Present only in single-project mode — the project that was verified
- `issueTypesChecked` (array) - *Optional* - Present only in single-project mode
- `findings` (object) - *Optional* - Drift findings grouped by category. Present only when outcome = drift-detected in single-project mode.
- `projects` (object) - *Optional* - Present only in all-projects mode — map of project key to per-project sub-report. Each value has the shape { outcome, projectKey, issueTypesChecked?, findings? } matching a single-project report (minus mode and configPath).
## Error Handling

### ConnectionError



**Properties:**

- `code` (string) (values: ["CONNECTION_FAILED"]) - 
- `message` (string) - 

### ConfigInvalidError



**Properties:**

- `code` (string) (values: ["CONFIG_INVALID"]) - 
- `message` (string) - 
- `details` (array) - 

### NoConfigError

No .ai/jira.config.json exists at any of the searched paths.

**Properties:**

- `code` (string) (values: ["NO_CONFIG"]) - 
- `message` (string) - 
- `searchedPaths` (array) - 

### ProjectNotInConfigError

Single-project mode only: the supplied projectKey has no entry under config.projects.

**Properties:**

- `code` (string) (values: ["PROJECT_NOT_IN_CONFIG"]) - 
- `message` (string) - 
- `requestedProjectKey` (string) - 
- `availableProjectKeys` (array) - 

### EmptyProjectsConfigError

All-projects mode only: config.projects exists but is empty (no projects to verify). Run the configure-jira skill to add at least one project.

**Properties:**

- `code` (string) (values: ["EMPTY_PROJECTS_CONFIG"]) - 
- `message` (string) - 

### ProjectNotAccessibleError

Single-project mode only: the Jira project is unreachable or the user lacks access. In all-projects mode this is captured per-project inside projects.<KEY>.outcome instead.

**Properties:**

- `code` (string) (values: ["PROJECT_NOT_ACCESSIBLE"]) - 
- `message` (string) - 
- `projectKey` (string) - 

## Prompt Content

# Verify Jira Config

Detect drift between the team's `.ai/jira.config.json` and the live Jira project(s). Read-only — never mutates Jira state.

## Parameters

- **{{projectKey}}** (string, optional): Jira project key to verify (e.g., `AIP`, `PCG`). When provided → single-project mode. When omitted → all-projects mode (iterates every entry in `config.projects`). There is **no fallback** to `config.defaultProjectKey`; omitting the parameter explicitly selects all-projects mode.
- **{{issueTypes}}** (string, optional): Comma-separated list of issue type names to verify (e.g., `"Story,Epic"`), parsed into a `string[]` before invoking the skill. Defaults to all issue types each project exposes. In all-projects mode the same filter applies uniformly to every project.

## Instructions

Load `@./.cursor\skills\verify-jira-config\SKILL.md` and execute it with these inputs.

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

- `NoConfigError` (`no-config`) — no `.ai/jira.config.json` at any search path; run `@./.cursor\skills\configure-jira\SKILL.md` to create one
- `ConfigInvalidError` (`config-invalid`) — the file failed schema validation; the loader's `details` array names each violation
- `ProjectNotInConfigError` (`project-not-in-config`) — single-project mode; the key has no entry. Includes `requestedProjectKey` and `availableProjectKeys`
- `EmptyProjectsConfigError` (`empty-projects-config`) — all-projects mode; `config.projects` is empty
- `ProjectNotAccessibleError` (`project-not-accessible`) — a project's MCP discovery failed. Top-level in single-project mode; per-project in all-projects mode, where iteration continues
- `ConnectionError` (`connection-error`) — MCP connection failed after retries

```json
{ "outcome": "project-not-in-config", "message": "Project 'XYZ' is not configured", "requestedProjectKey": "XYZ", "availableProjectKeys": ["AIP", "PCG"] }
```

