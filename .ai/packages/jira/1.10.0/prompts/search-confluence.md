# Search and Summarize Confluence

Search Confluence for a topic, download all relevant pages, and produce a comprehensive cited summary.

## Parameters

- **{{searchTopic}}** (string, required): The main topic or keyword to search for
  - Should be descriptive enough to find relevant content
  - Examples: `API rate limiting`, `deployment process`, `user authentication`

- **{{specificSpaces}}** (array, optional): Limit the search to specific Confluence space keys
  - Example: `["ENG", "OPS", "PLAT"]`
  - When omitted, searches all accessible spaces

- **{{dateRange}}** (string, optional): Filter by date using CQL syntax
  - Examples: `created > -30d`, `lastModified > -7d`, `lastModified > 2025-01-01`
  - When omitted, no date filtering is applied

- **{{contentTypes}}** (array, optional): Filter by content type
  - Possible values: `page`, `blogpost`
  - Default: all types

- **{{maxResults}}** (number, optional): Maximum number of documents to process
  - Default value: `50`
  - Min: 1, Max: 200

- **{{download}}** (boolean, optional): Whether to save found pages as markdown files
  - Default value: `true`
  - When true, saves to the `confluence/` directory with one file per page

## Instructions

Load `{{skill:jira.search-summarize-confluence}}` and execute it with these inputs.

| Skill input | Value |
|---|---|
| `searchTopic` | `{{searchTopic}}` |
| `specificSpaces` | `{{specificSpaces}}` (only if provided — defaults to all accessible spaces) |
| `dateRange` | `{{dateRange}}` (only if provided — CQL date clause) |
| `contentTypes` | `{{contentTypes}}` (only if provided — defaults to all types) |
| `maxResults` | `{{maxResults}}` (default `50`) |
| `download` | `{{download}}` (default `true`) |

The skill discovers accessible spaces, runs a primary CQL search followed by refined synonym / label / hierarchy passes, deduplicates the results, downloads and analyzes the content, writes `confluence/SUMMARY.md`, and cross-validates the summary against its sources.

Return the skill's response unchanged.

## Response Format

### Success Response

```json
{
  "success": true,
  "searchTopic": "API rate limiting",
  "executiveSummary": "Found 12 documents across 3 spaces covering rate limiting policies, implementation guides, and incident reports...",
  "documentsFound": 12,
  "documentsDownloaded": 12,
  "outputDirectory": "confluence/",
  "summaryPath": "confluence/SUMMARY.md"
}
```

`documentsDownloaded` is `0` when `download=false`; the summary is still written.

## Error Handling

Errors are surfaced as returned by the `search-summarize-confluence` skill:

- `ConnectionError` (`CONNECTION_FAILED`) — the Atlassian MCP server is unreachable or unauthenticated
- `NoResultsFoundError` (`NO_RESULTS_FOUND`) — the primary and every refined search returned zero matches
- `DownloadError` (`DOWNLOAD_FAILED`) — page files or the summary could not be written

```json
{ "code": "NO_RESULTS_FOUND", "message": "No Confluence content found for topic 'nonexistent topic'", "searchTopic": "nonexistent topic", "searchQuery": "text ~ 'nonexistent topic' OR title ~ 'nonexistent topic'" }
```

An inaccessible space does not abort the run — it is skipped and noted in the summary's coverage section.
