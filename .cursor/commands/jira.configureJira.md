---
promp:
  package: "jira"
  version: "1.10.0"
  environment: "development"
  prompVersion: "1.0.1-beta.83"
  prompt: "configureJira"
---
# jira.configureJira

Generate or update one project entry in .ai/jira.config.json by discovering the team's live Jira project field configuration via MCP and capturing per-team defaults. Multi-project safe: when an existing config has entries for other projects, this prompt merges the new entry into config.projects rather than overwriting the file. Run once per Jira project the team works in.

## Parameter Specifications

- **`projectKey`** (string) - *Optional*
  - Jira project key to configure against (e.g., 'AIP'). When omitted, the prompt asks the user.

- **`siteUrl`** (string) - *Optional*
  - Atlassian site URL (e.g., https://pennymac.atlassian.net). When omitted, the prompt detects via validate-mcp-connection.

- **`force`** (boolean) - *Optional*
  - Skip the per-project replace-confirmation prompt when an entry already exists for projectKey. Does not suppress the final write-permission prompt. Default: false.

## Instructions

You are executing a Promp package prompt. Follow these steps:

1. **Parse the user input** to extract parameters:
   - Parameter 1: `projectKey` (optional) - Jira project key to configure against (e.g., 'AIP'). When omitted, the prompt asks the user.
   - Parameter 2: `siteUrl` (optional) - Atlassian site URL (e.g., https://pennymac.atlassian.net). When omitted, the prompt detects via validate-mcp-connection.
   - Parameter 3: `force` (optional) - Skip the per-project replace-confirmation prompt when an entry already exists for projectKey. Does not suppress the final write-permission prompt. Default: false.

2. **Replace parameter placeholders** in the prompt content below:
   - Parameters use the format `{{parameterName}}` in the prompt
   - Replace each placeholder with the corresponding parsed value
   - If a parameter is optional and not provided, use its default value (if specified)
   - If a required parameter is missing, ask the user to provide it

3. **Execute the prompt** with the replaced parameters

## Usage

When the user invokes this command, they may provide parameters in various ways:
- Space-separated values: `/jira.configureJira value1 value2`
- Named parameters: `/jira.configureJira param1=value1 param2=value2`
- Mixed format: `/jira.configureJira value1 param2=value2`

Parse flexibly and map values to the expected parameters in order for positional arguments.

## Expected Output

Result of the configuration generation or update for one project entry

**Type:** `object`

**Properties:**

- `success` (boolean) - **Required** - 
- `configPath` (string) - **Required** - Absolute path to the written .ai/jira.config.json file
- `projectKey` (string) - **Required** - Project key whose entry was added or replaced
- `replaceMode` (string) - **Required** - How the file was modified: add (new project added to existing file), replace (existing entry overwritten), create-file (no file existed; new file created)
- `projectsAfterWrite` (array) - **Required** - Project keys present in the file after the merge — useful for the calling workflow to confirm no previously-configured projects were dropped
- `fieldsResolved` (number) - *Optional* - Count of logical field IDs resolved to a customfield_NNN value for this project
- `fieldsUnresolved` (number) - *Optional* - Count of logical field IDs left as null because the project does not expose them
- `defaultsConfigured` (number) - *Optional* - Count of per-team defaults the user supplied for this project
- `issueTypesProfiled` (array) - *Optional* - Names of issue types whose field metadata was inspected
- `driftReport` (object) - *Optional* - Result of the post-write verify-jira-config sanity check (single-project mode against the freshly-written project)
## Error Handling

### ConnectionError



**Properties:**

- `code` (string) (values: ["CONNECTION_FAILED"]) - 
- `message` (string) - 
- `details` (string) - 

### ProjectNotFoundError



**Properties:**

- `code` (string) (values: ["PROJECT_NOT_FOUND"]) - 
- `message` (string) - 
- `projectKey` (string) - 

### WriteError



**Properties:**

- `code` (string) (values: ["WRITE_FAILED"]) - 
- `message` (string) - 
- `details` (string) - 

### UserCancelled



**Properties:**

- `code` (string) (values: ["USER_CANCELLED"]) - 
- `message` (string) - 

### ConfigInvalidError

An existing .ai/jira.config.json was found but failed schema validation. The configure-jira skill halts to avoid merging a new project entry into a malformed file. The user must hand-fix or replace the file before re-running.

**Properties:**

- `code` (string) (values: ["CONFIG_INVALID"]) - 
- `message` (string) - 
- `configPath` (string) - 
- `details` (array) - 

### InvalidProjectKeyError



**Properties:**

- `code` (string) (values: ["INVALID_PROJECT_KEY"]) - 
- `message` (string) - 
- `projectKey` (string) - 

## Prompt Content

# Configure Jira

Generate or update one project entry in `.ai/jira.config.json` by discovering that Jira project's live field configuration and capturing per-team defaults.

## Parameters

- **{{projectKey}}** (string, optional): Jira project key to configure against (e.g., `AIP`). When omitted, the skill asks the user. Each invocation configures exactly one project.
- **{{siteUrl}}** (string, optional): Atlassian site URL (e.g., `https://pennymac.atlassian.net`). When omitted, detected during MCP validation.
- **{{force}}** (boolean, optional): Skip the per-project replace-confirmation prompt when an entry already exists for `{{projectKey}}`. Does **not** suppress the final write-permission prompt. Default: `false`.

## Instructions

Load `@./.cursor\skills\configure-jira\SKILL.md` and execute it with these inputs.

| Skill input | Value |
|---|---|
| `projectKey` | `{{projectKey}}` (omit to have the skill ask) |
| `siteUrl` | `{{siteUrl}}` (omit to auto-detect) |
| `force` | `{{force}}` (default `false`) |

The skill validates the MCP connection, loads any existing config in full multi-project mode, decides whether this run adds / replaces / creates the file, discovers the project's issue types and per-type field metadata, maps logical field names to custom field IDs, detects per-type AC and Channel-required postures, captures per-team defaults, previews the merged file, writes it after explicit approval, and sanity-checks the result with a single-project drift report.

Return the skill's response unchanged.

## Response Format

### Success Response

```json
{
  "success": true,
  "configPath": "/abs/.ai/jira.config.json",
  "projectKey": "AIP",
  "replaceMode": "add",
  "projectsAfterWrite": ["AIP", "PCG"],
  "fieldsResolved": 9,
  "fieldsUnresolved": 3,
  "defaultsConfigured": 5,
  "issueTypesProfiled": ["Story", "Task", "Bug", "Sub-task", "Epic"],
  "driftReport": { "outcome": "no-drift" }
}
```

`replaceMode` is `add`, `replace`, or `create-file`. `projectsAfterWrite` confirms no previously-configured project was dropped during the merge.

## Error Handling

Errors are surfaced as returned by the `configure-jira` skill:

- `ConnectionError` (`CONNECTION_FAILED`) — MCP validation failed, or every per-type discovery call failed
- `ConfigInvalidError` (`CONFIG_INVALID`) — the existing `.ai/jira.config.json` failed schema validation and must be fixed before merging into it
- `InvalidProjectKeyError` (`INVALID_PROJECT_KEY`) — the project key did not match `^[A-Z][A-Z0-9_]+$`
- `ProjectNotFoundError` (`PROJECT_NOT_FOUND`) — the project does not exist or the user lacks access
- `WriteError` (`WRITE_FAILED`) — the config file could not be written or verified
- `UserCancelled` (`USER_CANCELLED`) — the user declined the replace confirmation or the write gate

```json
{ "code": "INVALID_PROJECT_KEY", "message": "Project key must match ^[A-Z][A-Z0-9_]+$", "projectKey": "aip-foo" }
```

