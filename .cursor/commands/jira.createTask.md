---
promp:
  package: "jira"
  version: "1.10.0"
  environment: "development"
  prompVersion: "1.0.1-beta.83"
  prompt: "createTask"
---
# jira.createTask

Create a new Jira Task for technical work, maintenance, or non-feature work with required project fields

## Parameter Specifications

- **`projectKey`** (string) - *Optional*
  - Jira project key the task should be created in (e.g., 'AIP', 'PCG'). When omitted, the workflow falls back to top-level defaultProjectKey in .ai/jira.config.json. If neither is set, the workflow halts with DefaultProjectKeyMissingError.

- **`summary`** (string) - **Required**
  - Task title / summary

- **`description`** (string) - *Optional*
  - Task description in markdown format

- **`acceptanceCriteria`** (string) - *Optional*
  - Acceptance criteria as a comma-separated or newline-separated list

- **`labels`** (string) - *Optional*
  - Comma-separated labels to apply to the task

## Instructions

You are executing a Promp package prompt. Follow these steps:

1. **Parse the user input** to extract parameters:
   - Parameter 1: `projectKey` (optional) - Jira project key the task should be created in (e.g., 'AIP', 'PCG'). When omitted, the workflow falls back to top-level defaultProjectKey in .ai/jira.config.json. If neither is set, the workflow halts with DefaultProjectKeyMissingError.
   - Parameter 2: `summary` (required) - Task title / summary
   - Parameter 3: `description` (optional) - Task description in markdown format
   - Parameter 4: `acceptanceCriteria` (optional) - Acceptance criteria as a comma-separated or newline-separated list
   - Parameter 5: `labels` (optional) - Comma-separated labels to apply to the task

2. **Replace parameter placeholders** in the prompt content below:
   - Parameters use the format `{{parameterName}}` in the prompt
   - Replace each placeholder with the corresponding parsed value
   - If a parameter is optional and not provided, use its default value (if specified)
   - If a required parameter is missing, ask the user to provide it

3. **Execute the prompt** with the replaced parameters

## Usage

When the user invokes this command, they may provide parameters in various ways:
- Space-separated values: `/jira.createTask value1 value2`
- Named parameters: `/jira.createTask param1=value1 param2=value2`
- Mixed format: `/jira.createTask value1 param2=value2`

Parse flexibly and map values to the expected parameters in order for positional arguments.

## Expected Output

Created Jira task details

**Type:** `object`

**Properties:**

- `success` (boolean) - **Required** - 
- `issueKey` (string) - **Required** - Created issue key
- `summary` (string) - **Required** - 
- `issueType` (string) - **Required** - 
- `url` (string) - *Optional* - Jira issue URL
## Error Handling

### ConnectionError



**Properties:**

- `code` (string) (values: ["CONNECTION_FAILED"]) - 
- `message` (string) - 
- `details` (string) - 

### CreationError



**Properties:**

- `code` (string) (values: ["CREATION_FAILED"]) - 
- `message` (string) - 
- `details` (string) - 

### FieldValidationError



**Properties:**

- `code` (string) (values: ["FIELD_VALIDATION_FAILED"]) - 
- `message` (string) - 
- `field` (string) - 
- `details` (string) - 

### ConfigInvalidError

The .ai/jira.config.json file exists but failed schema validation. The workflow halts before attempting to create or update an issue. Run the verify-jira-config skill to see violations.

**Properties:**

- `code` (string) (values: ["CONFIG_INVALID"]) - 
- `message` (string) - 
- `configPath` (string) - Absolute path to the offending config file
- `details` (array) - Per-violation findings from schema validation

### BootstrapFailedError

The configure-jira skill reported success but the freshly-written .ai/jira.config.json could not be loaded or validated on the follow-up load-jira-config call. Indicates an unexpected discrepancy between write and read.

**Properties:**

- `code` (string) (values: ["BOOTSTRAP_FAILED"]) - 
- `message` (string) - 
- `configPath` (string) - Absolute path the configure-jira skill reported writing
- `details` (string) - Why the post-write load failed (parse error, schema violation, missing file)

### ProjectNotInConfigError

The .ai/jira.config.json file exists and is valid, but has no entry under config.projects for the requested project key. The workflow halts and the calling agent should offer to bootstrap the missing project via the configure-jira skill with projectKey=<requested>.

**Properties:**

- `code` (string) (values: ["PROJECT_NOT_IN_CONFIG"]) - 
- `message` (string) - 
- `requestedProjectKey` (string) - The project key the workflow attempted to resolve
- `availableProjectKeys` (array) - Project keys currently configured in the file
- `configPath` (string) - Absolute path to the loaded config file

### DefaultProjectKeyMissingError

The .ai/jira.config.json file is valid but the workflow could not resolve a project key — the calling prompt did not supply a projectKey parameter and config.defaultProjectKey is unset. The workflow halts; the user must either supply projectKey explicitly or run the configure-jira skill to set defaultProjectKey.

**Properties:**

- `code` (string) (values: ["DEFAULT_PROJECT_KEY_MISSING"]) - 
- `message` (string) - 
- `availableProjectKeys` (array) - Project keys configured in the file (the user can pick one to pass as projectKey)
- `configPath` (string) - Absolute path to the loaded config file

## Prompt Content

# Create Jira Task

Create a new Task issue in Jira (technical work, maintenance, or non-feature work). Thin dispatcher around the `create-jira-issues` workflow skill.

## Parameters

- **{{projectKey}}** (string, optional): Jira project key the task should be created in (e.g., `AIP`, `PCG`). When omitted, the workflow falls back to top-level `defaultProjectKey` in `.ai/jira.config.json`. If neither is set, the workflow halts with `DefaultProjectKeyMissingError`.
- **{{summary}}** (string, required): Task title / summary
- **{{description}}** (string, optional): Task description in markdown format
- **{{acceptanceCriteria}}** (string, optional): Acceptance criteria as a comma-separated or newline-separated list (set in a separate API call as ADF after creation)
- **{{labels}}** (string, optional): Comma-separated labels to apply to the task

## Instructions

Load `@./.cursor\skills\create-jira-issues\SKILL.md` and execute it with these inputs.

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
- `ConfigInvalidError` (`CONFIG_INVALID`) -- `.ai/jira.config.json` failed schema validation; run `@./.cursor\skills\verify-jira-config\SKILL.md` to inspect the drift
- `BootstrapFailedError` (`BOOTSTRAP_FAILED`) -- `configure-jira` reported success but the freshly-written config could not be re-loaded
- `ProjectNotInConfigError` (`PROJECT_NOT_IN_CONFIG`) -- the resolved project key has no entry in `config.projects` and the user declined to bootstrap it
- `DefaultProjectKeyMissingError` (`DEFAULT_PROJECT_KEY_MISSING`) -- neither `projectKey` parameter nor `config.defaultProjectKey` is set

```json
{ "code": "CREATION_FAILED", "message": "Failed to create Jira task", "details": "..." }
```

