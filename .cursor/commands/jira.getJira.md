---
promp:
  package: "jira"
  version: "1.10.0"
  environment: "development"
  prompVersion: "1.0.1-beta.83"
  prompt: "getJira"
---
# jira.getJira

Retrieve a specific Jira ticket by issue key with optional download to markdown file

## Parameter Specifications

- **`issueKey`** (string) - **Required**
  - Jira issue key (e.g., 'PROJ-123', 'CET-456')

- **`download`** (boolean) - *Optional*
  - Whether to save the ticket as a markdown file in a jira/ directory

## Instructions

You are executing a Promp package prompt. Follow these steps:

1. **Parse the user input** to extract parameters:
   - Parameter 1: `issueKey` (required) - Jira issue key (e.g., 'PROJ-123', 'CET-456')
   - Parameter 2: `download` (optional) - Whether to save the ticket as a markdown file in a jira/ directory

2. **Replace parameter placeholders** in the prompt content below:
   - Parameters use the format `{{parameterName}}` in the prompt
   - Replace each placeholder with the corresponding parsed value
   - If a parameter is optional and not provided, use its default value (if specified)
   - If a required parameter is missing, ask the user to provide it

3. **Execute the prompt** with the replaced parameters

## Usage

When the user invokes this command, they may provide parameters in various ways:
- Space-separated values: `/jira.getJira value1 value2`
- Named parameters: `/jira.getJira param1=value1 param2=value2`
- Mixed format: `/jira.getJira value1 param2=value2`

Parse flexibly and map values to the expected parameters in order for positional arguments.

## Expected Output

Retrieved Jira ticket details

**Type:** `object`

**Properties:**

- `success` (boolean) - **Required** - Whether the retrieval was successful
- `issueKey` (string) - **Required** - The Jira issue key
- `summary` (string) - **Required** - Issue summary/title
- `status` (string) - **Required** - Current issue status
- `assignee` (string,null) - *Optional* - Display name of the current assignee, or null when the issue is unassigned
- `content` (string) - **Required** - Full issue content in markdown format
- `filePath` (string) - *Optional* - Path to the downloaded markdown file (only if download=true)
## Error Handling

### ConnectionError

Error when the Atlassian MCP server connection fails

**Properties:**

- `code` (string) (values: ["CONNECTION_FAILED"]) - 
- `message` (string) - 
- `details` (string) - 

### IssueNotFoundError

Error when the specified Jira issue cannot be found

**Properties:**

- `code` (string) (values: ["ISSUE_NOT_FOUND"]) - 
- `message` (string) - 
- `issueKey` (string) - 

### DownloadError

Error when saving the issue to a file fails

**Properties:**

- `code` (string) (values: ["DOWNLOAD_FAILED"]) - 
- `message` (string) - 
- `issueKey` (string) - 

## Prompt Content

# Get Jira Ticket

Retrieve a specific Jira ticket by issue key, with optional download to a local markdown file.

## Parameters

- **{{issueKey}}** (string, required): The Jira issue key to retrieve
  - Format: `PROJECT-NUMBER` (e.g., `CET-123`, `PLAT-456`)
  - Must contain a project prefix, hyphen, and numeric ID
  - Case-insensitive (normalized to uppercase)

- **{{download}}** (boolean, optional): Whether to save the ticket as a markdown file
  - Default value: `false`
  - When true, saves to `jira/{issueKey}_{sanitized_summary}.md`

## Instructions

Load `@./.cursor\skills\retrieve-jira\SKILL.md` and execute it with these inputs.

| Skill input | Value |
|---|---|
| `issueKey` | `{{issueKey}}` |
| `download` | `{{download}}` (default `false`) |

The skill validates the MCP connection, fetches the issue, formats it as a structured markdown document, saves it when `download` is true, and verifies the result.

Return the skill's response unchanged.

## Response Format

### Success Response

```json
{
  "success": true,
  "issueKey": "CET-123",
  "summary": "Implement user authentication",
  "status": "In Progress",
  "assignee": "Jane Doe",
  "content": "# CET-123: Implement user authentication\n\n**Status:** In Progress\n...",
  "filePath": "jira/CET-123_implement-user-authentication.md"
}
```

`assignee` is the display name, or `null` / `"Unassigned"` when the issue has no assignee. `filePath` is present only when `download=true`.

## Error Handling

Errors are surfaced as returned by the `retrieve-jira` skill:

- `ConnectionError` (`CONNECTION_FAILED`) — the Atlassian MCP server is unreachable or unauthenticated
- `IssueNotFoundError` (`ISSUE_NOT_FOUND`) — the key does not exist or the user cannot view the issue
- `DownloadError` (`DOWNLOAD_FAILED`) — the markdown file could not be written

```json
{ "code": "ISSUE_NOT_FOUND", "message": "Jira issue 'CET-999' not found", "issueKey": "CET-999" }
```

