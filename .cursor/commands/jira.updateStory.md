---
promp:
  package: "jira"
  version: "1.10.0"
  environment: "development"
  prompVersion: "1.0.1-beta.83"
  prompt: "updateStory"
---
# jira.updateStory

Update fields on an existing Jira Story with proper separation of markdown and ADF field updates into distinct API calls

## Parameter Specifications

- **`issueKey`** (string) - **Required**
  - Jira issue key to update (e.g., 'PROJ-123')

- **`summary`** (string) - *Optional*
  - Updated story title

- **`description`** (string) - *Optional*
  - Updated description in markdown format

- **`acceptanceCriteria`** (string) - *Optional*
  - Updated acceptance criteria as a comma-separated or newline-separated list

- **`acMergeMode`** (string) - *Optional*
  - How acceptance criteria are applied: 'replace' (default, overwrites the whole AC field) or 'append' (merges new AC items into the existing ones, deduped). Only affects the AC field; ignored when acceptanceCriteria is not provided.
  - Default: `replace`

- **`labels`** (string) - *Optional*
  - Comma-separated labels (replaces existing)

- **`transition`** (string) - *Optional*
  - Transition the story to this status (e.g., 'To Do', 'In Progress', 'Done')

- **`assignee`** (string) - *Optional*
  - Set the assignee — a Jira account id, the token 'me' (the current MCP-authenticated user), or 'unassigned' to clear. Applied as a standard user field in the same call as summary/labels.

- **`parentKey`** (string) - *Optional*
  - Issue key of the parent Epic to link this story under (the Epic Link / parent relationship), e.g., 'PROJ-100'. Pass 'unassigned' to clear the parent. Applied as a standard field in the same call as summary/labels.

- **`storyPoints`** (number) - *Optional*
  - Numeric story-point estimate written to the configured Story Points field as a bare number, in the same call as summary/labels. Many project workflows require it before a story may leave Backlog.

## Instructions

You are executing a Promp package prompt. Follow these steps:

1. **Parse the user input** to extract parameters:
   - Parameter 1: `issueKey` (required) - Jira issue key to update (e.g., 'PROJ-123')
   - Parameter 2: `summary` (optional) - Updated story title
   - Parameter 3: `description` (optional) - Updated description in markdown format
   - Parameter 4: `acceptanceCriteria` (optional) - Updated acceptance criteria as a comma-separated or newline-separated list
   - Parameter 5: `acMergeMode` (optional) [default: replace] - How acceptance criteria are applied: 'replace' (default, overwrites the whole AC field) or 'append' (merges new AC items into the existing ones, deduped). Only affects the AC field; ignored when acceptanceCriteria is not provided.
   - Parameter 6: `labels` (optional) - Comma-separated labels (replaces existing)
   - Parameter 7: `transition` (optional) - Transition the story to this status (e.g., 'To Do', 'In Progress', 'Done')
   - Parameter 8: `assignee` (optional) - Set the assignee — a Jira account id, the token 'me' (the current MCP-authenticated user), or 'unassigned' to clear. Applied as a standard user field in the same call as summary/labels.
   - Parameter 9: `parentKey` (optional) - Issue key of the parent Epic to link this story under (the Epic Link / parent relationship), e.g., 'PROJ-100'. Pass 'unassigned' to clear the parent. Applied as a standard field in the same call as summary/labels.
   - Parameter 10: `storyPoints` (optional) - Numeric story-point estimate written to the configured Story Points field as a bare number, in the same call as summary/labels. Many project workflows require it before a story may leave Backlog.

2. **Replace parameter placeholders** in the prompt content below:
   - Parameters use the format `{{parameterName}}` in the prompt
   - Replace each placeholder with the corresponding parsed value
   - If a parameter is optional and not provided, use its default value (if specified)
   - If a required parameter is missing, ask the user to provide it

3. **Execute the prompt** with the replaced parameters

## Usage

When the user invokes this command, they may provide parameters in various ways:
- Space-separated values: `/jira.updateStory value1 value2`
- Named parameters: `/jira.updateStory param1=value1 param2=value2`
- Mixed format: `/jira.updateStory value1 param2=value2`

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

# Update Jira Story

Update fields on an existing Jira Story. Thin dispatcher around the `update-jira-issues` workflow skill, which handles the markdown / ADF separation across multiple `editJiraIssue` calls.

## Parameters

- **{{issueKey}}** (string, required): The Jira issue key to update (e.g., `PROJ-123`)
- **{{summary}}** (string, optional): Updated story title
- **{{description}}** (string, optional): Updated description in markdown format
- **{{acceptanceCriteria}}** (string, optional): Updated acceptance criteria as a comma-separated or newline-separated list (applied as ADF in a separate API call)
- **{{acMergeMode}}** (string, optional): How acceptance criteria are applied — `replace` (default, overwrites the whole AC field) or `append` (merges new AC items into the existing ones). Only affects the AC field; ignored when no acceptanceCriteria is provided.
- **{{labels}}** (string, optional): Comma-separated labels (replaces existing labels)
- **{{transition}}** (string, optional): Transition the story to this status (e.g., `To Do`, `In Progress`, `Done`)
- **{{assignee}}** (string, optional): Set the assignee — a Jira account id, the token `me` (the current MCP-authenticated user), or `unassigned` to clear
- **{{parentKey}}** (string, optional): Issue key of the parent **Epic** to link this story under (the Epic Link / parent relationship), e.g., `PROJ-100`. Pass `unassigned` to clear the parent.
- **{{storyPoints}}** (number, optional): Numeric story-point estimate. Many project workflows require it before a story may leave `Backlog`.

## Instructions

Load `@./.cursor\skills\update-jira-issues\SKILL.md` and execute it with these inputs.

| Workflow input | Value |
|---|---|
| `profileName` | `Story` |
| `issueKey` | `{{issueKey}}` |
| `summary` | `{{summary}}` (only if provided) |
| `description` | `{{description}}` (only if provided) |
| `acceptanceCriteria` | `{{acceptanceCriteria}}` (only if provided) |
| `acMergeMode` | `{{acMergeMode}}` (only if provided) |
| `labels` | `{{labels}}` (only if provided) |
| `transition` | `{{transition}}` (only if provided) |
| `assignee` | `{{assignee}}` (only if provided) |
| `parentKey` | `{{parentKey}}` (only if provided — re-parents the story to a different Epic, or `unassigned` to clear) |
| `storyPoints` | `{{storyPoints}}` (only if provided — written as a bare number to the configured Story Points field) |

The Story profile sets `acceptanceCriteriaMode = adf-field`, so the skill:

1. Validates the connection and retrieves the current issue
2. Builds a change set from only the parameters provided
3. Asks for explicit user approval showing old to new for each changed field
4. Applies updates in separate API calls (Call 1: summary + labels; Call 2: AC via `set-acceptance-criteria`; Call 3: description)
5. Optionally transitions status
6. Verifies and reports

Return the skill's response unchanged.

## Response Format

### Success Response

```json
{
  "success": true,
  "issueKey": "PROJ-123",
  "fieldsUpdated": ["summary", "description", "acceptanceCriteria"],
  "transitioned": false
}
```

## Error Handling

Errors are surfaced as returned by the `update-jira-issues` skill:

- `ConnectionError` (`CONNECTION_FAILED`)
- `IssueNotFoundError` (`ISSUE_NOT_FOUND`)
- `UpdateError` (`UPDATE_FAILED`)
- `TransitionError` (`TRANSITION_FAILED`) -- when the requested transition is not available from the issue's current status
- `UserCancelled` (`USER_CANCELLED`)

```json
{ "code": "ISSUE_NOT_FOUND", "message": "Jira issue 'PROJ-999' not found", "issueKey": "PROJ-999" }
```

