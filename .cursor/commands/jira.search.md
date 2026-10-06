---
promp:
  package: "jira"
  version: "1.10.0"
  environment: "development"
  prompVersion: "1.0.1-beta.83"
  prompt: "search"
---
# jira.search

Arbor-compatible search source over Confluence: runs one CQL query and returns ranked, cited results in arbor's normalized SearchResultSet/RankedResult envelope (lightweight retrieval, no download/summarize). Designed to be registered as a federated source in arbor's .kbs/.arbor.json and to degrade gracefully (soft error, never throws) when the Atlassian MCP is unavailable.

## Parameter Specifications

- **`query`** (string) - **Required**
  - The search text

- **`limit`** (number) - *Optional*
  - Maximum number of results to return
  - Default: `10`

- **`type`** (string) - *Optional*
  - Content-type filter; honored when 'page' or 'blogpost', otherwise ignored

- **`filters`** (object) - *Optional*
  - Source-specific filters: { spaces: [space keys], dateRange: CQL date clause }

- **`timeoutMs`** (number) - *Optional*
  - Soft time budget; return available results with partial=true if exceeded

## Instructions

You are executing a Promp package prompt. Follow these steps:

1. **Parse the user input** to extract parameters:
   - Parameter 1: `query` (required) - The search text
   - Parameter 2: `limit` (optional) [default: 10] - Maximum number of results to return
   - Parameter 3: `type` (optional) - Content-type filter; honored when 'page' or 'blogpost', otherwise ignored
   - Parameter 4: `filters` (optional) - Source-specific filters: { spaces: [space keys], dateRange: CQL date clause }
   - Parameter 5: `timeoutMs` (optional) - Soft time budget; return available results with partial=true if exceeded

2. **Replace parameter placeholders** in the prompt content below:
   - Parameters use the format `{{parameterName}}` in the prompt
   - Replace each placeholder with the corresponding parsed value
   - If a parameter is optional and not provided, use its default value (if specified)
   - If a required parameter is missing, ask the user to provide it

3. **Execute the prompt** with the replaced parameters

## Usage

When the user invokes this command, they may provide parameters in various ways:
- Space-separated values: `/jira.search value1 value2`
- Named parameters: `/jira.search param1=value1 param2=value2`
- Mixed format: `/jira.search value1 param2=value2`

Parse flexibly and map values to the expected parameters in order for positional arguments.

## Expected Output

A SearchResultSet in arbor's Search Source contract shape. Never throws; soft failures are reported via error + partial.

**Type:** `object`

**Properties:**

- `source` (string) - **Required** - The source id
- `query` (string) - **Required** - The query that was searched
- `count` (number) - **Required** - Number of results returned
- `partial` (boolean) - *Optional* - True when results were truncated or the source was skipped due to a soft error
- `error` (object,null) - *Optional* - Soft error when the source could not run, else null
- `results` (array) - **Required** - Ranked results (RankedResult shape). Empty means no matches — not an error.
## Prompt Content

# Search

Run one CQL query over Confluence and return ranked, cited results in arbor's normalized `SearchResultSet` envelope.

## Parameters

- **{{query}}** (string, required): The search text
  - Example: `incident escalation policy`
- **{{limit}}** (number, optional): Maximum number of results to return
  - Default: `10`
  - Min: 1
- **{{type}}** (string, optional): Content-type filter; honored when it is `page` or `blogpost`, otherwise ignored
- **{{filters}}** (object, optional): Source-specific filters
  - `spaces` (array): Confluence space keys to restrict to (e.g. `["ENG", "OPS"]`)
  - `dateRange` (string): CQL date clause (e.g. `lastModified > -90d`)
- **{{timeoutMs}}** (number, optional): Soft time budget; return what is available with `partial: true` if exceeded

The `spaces` / `dateRange` values are read from the `filters` envelope; the top-level native names `specificSpaces` and `dateRange` are also tolerated.

## Instructions

Load `@./.cursor\skills\search-jira\SKILL.md` and execute it with these inputs.

| Skill input | Value |
|---|---|
| `query` | `{{query}}` |
| `limit` | `{{limit}}` (default `10`) |
| `type` | `{{type}}` (only if provided — honored for `page` / `blogpost`) |
| `filters.spaces` | `{{filters}}.spaces` (only if provided) |
| `filters.dateRange` | `{{filters}}.dateRange` (only if provided) |
| `timeoutMs` | `{{timeoutMs}}` (only if provided) |

The skill validates the MCP connection, builds one CQL query from the inputs sorted `ORDER BY lastModified DESC`, runs it, maps each match to a `RankedResult` with a source-relative score, and returns the envelope.

**Soft failure:** the skill never throws for connection, auth, search, or empty-result conditions. It always returns a `SearchResultSet`; problems are reported via `error` + `partial` so a calling federation keeps working.

Return the skill's response unchanged.

## Response Format

### Success Response

```json
{
  "source": "jira-confluence",
  "query": "incident escalation policy",
  "count": 1,
  "partial": false,
  "error": null,
  "results": [
    {
      "source": "jira-confluence",
      "ref": "123456",
      "url": "https://acme.atlassian.net/wiki/spaces/ENG/pages/123456",
      "type": "page",
      "title": "On-Call Escalation Runbook",
      "score": 20,
      "matchedSections": [ { "heading": "Excerpt", "excerpt": "Page the secondary on-call if the primary does not ack within 5 minutes…" } ],
      "citation": "Confluence › ENG › On-Call Escalation Runbook"
    }
  ]
}
```

Required fields: `source`, `query`, `count`, `results`. An empty `results` array means no matches — not an error. `partial` is `true` when results were truncated or the source was skipped by a soft error.

## Error Handling

Both conditions are returned **as a `SearchResultSet` with a soft `error`**, never thrown:

- `CONNECTION_FAILED` — Atlassian MCP not configured, OAuth expired, or network failure
- `SEARCH_FAILED` — CQL syntax or API error on the search call

```json
{ "source": "jira-confluence", "query": "rate limiting", "count": 0, "partial": true, "error": { "code": "SEARCH_FAILED", "message": "CQL search failed: text ~ 'rate limiting' AND bad_field = 'x'" }, "results": [] }
```

