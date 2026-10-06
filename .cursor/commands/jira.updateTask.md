---
promp:
  package: "jira"
  version: "1.10.0"
  environment: "development"
  prompVersion: "1.0.1-beta.83"
  prompt: "updateTask"
---
# jira.updateTask

Update fields on an existing Jira Task with proper separation of markdown and ADF field updates

## Parameter Specifications

- **`issueKey`** (string) - **Required**
  - Jira issue key to update (e.g., 'PROJ-123')

- **`summary`** (string) - *Optional*
  - Updated task title

- **`description`** (string) - *Optional*
  - Updated description in markdown format

- **`acceptanceCriteria`** (string) - *Optional*
  - Updated acceptance criteria

- **`labels`** (string) - *Optional*
  - Comma-separated labels (replaces existing)

- **`transition`** (string) - *Optional*
  - Transition the task to this status (e.g., 'To Do', 'In Progress', 'Done')

## Instructions

You are executing a Promp package prompt. Follow these steps:

1. **Parse the user input** to extract parameters:
   - Parameter 1: `issueKey` (required) - Jira issue key to update (e.g., 'PROJ-123')
   - Parameter 2: `summary` (optional) - Updated task title
   - Parameter 3: `description` (optional) - Updated description in markdown format
   - Parameter 4: `acceptanceCriteria` (optional) - Updated acceptance criteria
   - Parameter 5: `labels` (optional) - Comma-separated labels (replaces existing)
   - Parameter 6: `transition` (optional) - Transition the task to this status (e.g., 'To Do', 'In Progress', 'Done')

2. **Replace parameter placeholders** in the prompt content below:
   - Parameters use the format `{{parameterName}}` in the prompt
   - Replace each placeholder with the corresponding parsed value
   - If a parameter is optional and not provided, use its default value (if specified)
   - If a required parameter is missing, ask the user to provide it

3. **Execute the prompt** with the replaced parameters

## Usage

When the user invokes this command, they may provide parameters in various ways:
- Space-separated values: `/jira.updateTask value1 value2`
- Named parameters: `/jira.updateTask param1=value1 param2=value2`
- Mixed format: `/jira.updateTask value1 param2=value2`

Parse flexibly and map values to the expected parameters in order for positional arguments.

## Expected Output

Update result details

**Type:** `object`

**Properties:**

- `success` (boolean) - **Required** - 
- `issueKey` (string) - **Required** - 
- `fieldsUpdated` (array) - **Required** - 
- `transitioned` (boolean) - *Optional* - 
## Error Handling

### ConnectionError



**Properties:**

- `code` (string) (values: ["CONNECTION_FAILED"]) - 
- `message` (string) - 
- `details` (string) - 

### IssueNotFoundError



**Properties:**

- `code` (string) (values: ["ISSUE_NOT_FOUND"]) - 
- `message` (string) - 
- `issueKey` (string) - 

### UpdateError



**Properties:**

- `code` (string) (values: ["UPDATE_FAILED"]) - 
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

## Prompt Content

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

Load `@./.cursor\skills\update-jira-issues\SKILL.md` and execute it with these inputs.

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

