---
promp:
  package: "jira"
  version: "1.10.0"
  environment: "development"
  prompVersion: "1.0.1-beta.83"
  prompt: "searchConfluence"
---
# jira.searchConfluence

Search Confluence for a topic, download all relevant pages, and produce a comprehensive summary

## Parameter Specifications

- **`searchTopic`** (string) - **Required**
  - The main topic or keyword to search for in Confluence

- **`specificSpaces`** (array) - *Optional*
  - Limit search to specific Confluence space keys (e.g., ['ENG', 'OPS'])

- **`dateRange`** (string) - *Optional*
  - Filter by date using CQL syntax (e.g., 'created > -30d', 'lastModified > -7d')

- **`contentTypes`** (array) - *Optional*
  - Filter by content types (e.g., ['page', 'blogpost']). Defaults to all types.

- **`maxResults`** (number) - *Optional*
  - Maximum number of documents to process
  - Default: `50`

- **`download`** (boolean) - *Optional*
  - Whether to save all found pages as markdown files in a confluence/ directory
  - Default: `true`

## Instructions

You are executing a Promp package prompt. Follow these steps:

1. **Parse the user input** to extract parameters:
   - Parameter 1: `searchTopic` (required) - The main topic or keyword to search for in Confluence
   - Parameter 2: `specificSpaces` (optional) - Limit search to specific Confluence space keys (e.g., ['ENG', 'OPS'])
   - Parameter 3: `dateRange` (optional) - Filter by date using CQL syntax (e.g., 'created > -30d', 'lastModified > -7d')
   - Parameter 4: `contentTypes` (optional) - Filter by content types (e.g., ['page', 'blogpost']). Defaults to all types.
   - Parameter 5: `maxResults` (optional) [default: 50] - Maximum number of documents to process
   - Parameter 6: `download` (optional) [default: true] - Whether to save all found pages as markdown files in a confluence/ directory

2. **Replace parameter placeholders** in the prompt content below:
   - Parameters use the format `{{parameterName}}` in the prompt
   - Replace each placeholder with the corresponding parsed value
   - If a parameter is optional and not provided, use its default value (if specified)
   - If a required parameter is missing, ask the user to provide it

3. **Execute the prompt** with the replaced parameters

## Usage

When the user invokes this command, they may provide parameters in various ways:
- Space-separated values: `/jira.searchConfluence value1 value2`
- Named parameters: `/jira.searchConfluence param1=value1 param2=value2`
- Mixed format: `/jira.searchConfluence value1 param2=value2`

Parse flexibly and map values to the expected parameters in order for positional arguments.

## Expected Output

Search results and comprehensive summary

**Type:** `object`

**Properties:**

- `success` (boolean) - **Required** - Whether the search and summarization completed successfully
- `searchTopic` (string) - **Required** - The topic that was searched
- `executiveSummary` (string) - **Required** - High-level summary of findings
- `documentsFound` (number) - **Required** - Total number of relevant documents found
- `documentsDownloaded` (number) - *Optional* - Number of documents downloaded (if download=true)
- `outputDirectory` (string) - *Optional* - Path to the directory containing downloaded files
- `summaryPath` (string) - *Optional* - Path to the generated summary markdown file
## Error Handling

### ConnectionError

Error when the Atlassian MCP server connection fails

**Properties:**

- `code` (string) (values: ["CONNECTION_FAILED"]) - 
- `message` (string) - 
- `details` (string) - 

### NoResultsFoundError

Error when no Confluence content matches the search topic

**Properties:**

- `code` (string) (values: ["NO_RESULTS_FOUND"]) - 
- `message` (string) - 
- `searchTopic` (string) - 
- `searchQuery` (string) - 

### SearchError

Error when the CQL search fails

**Properties:**

- `code` (string) (values: ["SEARCH_FAILED"]) - 
- `message` (string) - 
- `cqlQuery` (string) - 

### DownloadError

Error when downloading pages fails

**Properties:**

- `code` (string) (values: ["DOWNLOAD_FAILED"]) - 
- `message` (string) - 
- `failedPages` (array) - 

## Prompt Content

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

Load `@./.cursor\skills\search-summarize-confluence\SKILL.md` and execute it with these inputs.

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

