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

Load `{{skill:jira.get-confluence-page}}` and execute it with these inputs.

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
