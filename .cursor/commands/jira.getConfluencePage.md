---
promp:
  package: "jira"
  version: "1.10.0"
  environment: "development"
  prompVersion: "1.0.1-beta.83"
  prompt: "getConfluencePage"
---
# jira.getConfluencePage

Retrieve a specific Confluence page by page ID or title with optional download to markdown file

## Parameter Specifications

- **`pageIdentifier`** (string) - **Required**
  - Confluence page ID (numeric) or page title to search for

- **`download`** (boolean) - *Optional*
  - Whether to save the page as a markdown file in a confluence/ directory

## Instructions

You are executing a Promp package prompt. Follow these steps:

1. **Parse the user input** to extract parameters:
   - Parameter 1: `pageIdentifier` (required) - Confluence page ID (numeric) or page title to search for
   - Parameter 2: `download` (optional) - Whether to save the page as a markdown file in a confluence/ directory

2. **Replace parameter placeholders** in the prompt content below:
   - Parameters use the format `{{parameterName}}` in the prompt
   - Replace each placeholder with the corresponding parsed value
   - If a parameter is optional and not provided, use its default value (if specified)
   - If a required parameter is missing, ask the user to provide it

3. **Execute the prompt** with the replaced parameters

## Usage

When the user invokes this command, they may provide parameters in various ways:
- Space-separated values: `/jira.getConfluencePage value1 value2`
- Named parameters: `/jira.getConfluencePage param1=value1 param2=value2`
- Mixed format: `/jira.getConfluencePage value1 param2=value2`

Parse flexibly and map values to the expected parameters in order for positional arguments.

## Expected Output

Retrieved Confluence page details

**Type:** `object`

**Properties:**

- `success` (boolean) - **Required** - Whether the retrieval was successful
- `pageId` (string) - **Required** - The Confluence page ID
- `title` (string) - **Required** - Page title
- `content` (string) - **Required** - Full page content in markdown format
- `filePath` (string) - *Optional* - Path to the downloaded markdown file (only if download=true)
## Error Handling

### ConnectionError

Error when the Atlassian MCP server connection fails

**Properties:**

- `code` (string) (values: ["CONNECTION_FAILED"]) - 
- `message` (string) - 
- `details` (string) - 

### PageNotFoundError

Error when the specified Confluence page cannot be found

**Properties:**

- `code` (string) (values: ["PAGE_NOT_FOUND"]) - 
- `message` (string) - 
- `pageIdentifier` (string) - 

### DownloadError

Error when saving the page to a file fails

**Properties:**

- `code` (string) (values: ["DOWNLOAD_FAILED"]) - 
- `message` (string) - 
- `pageId` (string) - 

## Prompt Content

# Get Confluence Page

Retrieve a specific Confluence page by page ID or title, with optional download to a local markdown file.

## Parameters

- **{{pageIdentifier}}** (string, required): Confluence page ID or title to retrieve
  - Numeric value: treated as a page ID (e.g., `123456789`)
  - Non-numeric value: treated as a page title to search for (e.g., `Deployment Runbook`)

- **{{download}}** (boolean, optional): Whether to save the page as a markdown file
  - Default value: `false`
  - When true, saves to `confluence/{pageId}_{sanitized_title}.md`

## Instructions

Load `@./.cursor\skills\get-confluence-page\SKILL.md` and execute it with these inputs.

| Skill input | Value |
|---|---|
| `pageIdentifier` | `{{pageIdentifier}}` |
| `download` | `{{download}}` (default `false`) |

The skill validates the MCP connection, resolves the page (directly by ID, or by exact-then-contains title search taking the most recently modified match), formats it as markdown, saves it when `download` is true, and notes any alternative title matches.

Return the skill's response unchanged.

## Response Format

### Success Response

```json
{
  "success": true,
  "pageId": "123456789",
  "title": "API Design Guidelines",
  "content": "# API Design Guidelines\n\n**Space:** Engineering (ENG)\n...",
  "filePath": "confluence/123456789_api-design-guidelines.md"
}
```

`filePath` is present only when `download=true`.

## Error Handling

Errors are surfaced as returned by the `get-confluence-page` skill:

- `ConnectionError` (`CONNECTION_FAILED`) — the Atlassian MCP server is unreachable or unauthenticated
- `PageNotFoundError` (`PAGE_NOT_FOUND`) — no page matched the identifier, or the user cannot view it
- `DownloadError` (`DOWNLOAD_FAILED`) — the markdown file could not be written

```json
{ "code": "PAGE_NOT_FOUND", "message": "Confluence page 'Nonexistent Page' not found", "pageIdentifier": "Nonexistent Page" }
```

