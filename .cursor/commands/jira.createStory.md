---
promp:
  package: "jira"
  version: "1.10.0"
  environment: "development"
  prompVersion: "1.0.1-beta.83"
  prompt: "createStory"
---
# jira.createStory

Create a new Jira Story with required project fields, optional acceptance criteria in ADF format, and proper field validation

## Parameter Specifications

- **`projectKey`** (string) - *Optional*
  - Jira project key the story should be created in (e.g., 'AIP', 'PCG'). When omitted, the workflow falls back to top-level defaultProjectKey in .ai/jira.config.json. If neither is set, the workflow halts with DefaultProjectKeyMissingError.

- **`summary`** (string) - **Required**
  - Story title / summary

- **`description`** (string) - *Optional*
  - Story description in markdown format

- **`acceptanceCriteria`** (string) - *Optional*
  - Acceptance criteria as a comma-separated or newline-separated list

- **`labels`** (string) - *Optional*
  - Comma-separated labels to apply to the story

- **`parentKey`** (string) - *Optional*
  - Issue key of the parent Epic to link this story under (the Epic Link / parent relationship), e.g., 'PROJ-100'. When omitted, the story is created without a parent.

- **`storyPoints`** (number) - *Optional*
  - Numeric story-point estimate written to the configured Story Points field as a bare number. Setting it at create time avoids a follow-up edit in projects whose workflow requires points before a story may leave Backlog.

## Instructions

You are executing a Promp package prompt. Follow these steps:

1. **Parse the user input** to extract parameters:
   - Parameter 1: `projectKey` (optional) - Jira project key the story should be created in (e.g., 'AIP', 'PCG'). When omitted, the workflow falls back to top-level defaultProjectKey in .ai/jira.config.json. If neither is set, the workflow halts with DefaultProjectKeyMissingError.
   - Parameter 2: `summary` (required) - Story title / summary
   - Parameter 3: `description` (optional) - Story description in markdown format
   - Parameter 4: `acceptanceCriteria` (optional) - Acceptance criteria as a comma-separated or newline-separated list
   - Parameter 5: `labels` (optional) - Comma-separated labels to apply to the story
   - Parameter 6: `parentKey` (optional) - Issue key of the parent Epic to link this story under (the Epic Link / parent relationship), e.g., 'PROJ-100'. When omitted, the story is created without a parent.
   - Parameter 7: `storyPoints` (optional) - Numeric story-point estimate written to the configured Story Points field as a bare number. Setting it at create time avoids a follow-up edit in projects whose workflow requires points before a story may leave Backlog.

2. **Replace parameter placeholders** in the prompt content below:
   - Parameters use the format `{{parameterName}}` in the prompt
   - Replace each placeholder with the corresponding parsed value
   - If a parameter is optional and not provided, use its default value (if specified)
   - If a required parameter is missing, ask the user to provide it

3. **Execute the prompt** with the replaced parameters

## Usage

When the user invokes this command, they may provide parameters in various ways:
- Space-separated values: `/jira.createStory value1 value2`
- Named parameters: `/jira.createStory param1=value1 param2=value2`
- Mixed format: `/jira.createStory value1 param2=value2`

Parse flexibly and map values to the expected parameters in order for positional arguments.

## Expected Output

Created Jira story details

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

Load `@./.cursor\skills\create-jira-issues\SKILL.md` and execute it with these inputs.

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
- `ConfigInvalidError` (`CONFIG_INVALID`) -- `.ai/jira.config.json` failed schema validation; run `@./.cursor\skills\verify-jira-config\SKILL.md` to inspect the drift
- `BootstrapFailedError` (`BOOTSTRAP_FAILED`) -- `configure-jira` reported success but the freshly-written config could not be re-loaded
- `ProjectNotInConfigError` (`PROJECT_NOT_IN_CONFIG`) -- the resolved project key has no entry in `config.projects` and the user declined to bootstrap it
- `DefaultProjectKeyMissingError` (`DEFAULT_PROJECT_KEY_MISSING`) -- neither `projectKey` parameter nor `config.defaultProjectKey` is set

```json
{ "code": "CONNECTION_FAILED", "message": "Unable to connect to Atlassian MCP server", "details": "..." }
```

