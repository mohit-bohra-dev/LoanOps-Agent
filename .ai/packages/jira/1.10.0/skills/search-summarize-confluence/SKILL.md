---
name: search-summarize-confluence
description: Systematically searches Confluence for a topic using CQL queries, downloads all relevant content, analyzes and categorizes findings, and produces a comprehensive summary. Use when researching a topic across Confluence and need a synthesized overview.
---

# Search and Summarize Confluence

Performs a comprehensive search of Confluence for a given topic, downloads all relevant content, and produces a structured summary with key insights.

## When to Use

Use this skill when you need to:
- Research a topic across Confluence and synthesize findings
- Gather all documentation on a subject for analysis
- Produce an executive summary from multiple Confluence pages

For ranked, cited hits without downloads or a written summary, use `search-jira` instead — it is the lightweight retrieval counterpart.

## Prerequisites

- Atlassian MCP connection validated (use `validate-mcp-connection` skill first)
- Valid cloud ID obtained from connection validation
- Write access to the workspace when `download` is left at its default of `true`

## Inputs

| Input | Type | Required | Description |
|---|---|---|---|
| `searchTopic` | string | yes | The topic or keyword to research (e.g., `"API rate limiting"`). Descriptive enough to match real content. |
| `specificSpaces` | string[] | no | Restrict the search to these Confluence space keys (e.g., `["ENG", "OPS"]`). Defaults to every accessible space. |
| `dateRange` | string | no | CQL date clause (e.g., `created > -30d`, `lastModified > 2025-01-01`). No date filtering by default. |
| `contentTypes` | string[] | no | Content types to include — `page`, `blogpost`. Defaults to all types. |
| `maxResults` | number | no | Maximum documents to process. Default `50`, min `1`, max `200`. |
| `download` | boolean | no | Save each found page as markdown under `confluence/`. Default `true`. When `false`, page content is held in memory for analysis and only the summary is written. |

## Workflow Overview

```text
Validate -> Discover Spaces -> Primary Search -> Refined Search ->
Download Content -> Analyze & Categorize -> Generate Summary -> Cross-Validate
```

## Instructions

### Step 1: Discover Available Spaces

Call `mcp_atlassian_getConfluenceSpaces` to retrieve accessible spaces.

- If `specificSpaces` are provided, filter to only those spaces
- Validate that target spaces exist and are accessible
- Prioritize spaces by likely relevance to the search topic

### Step 2: Execute Primary Search

Construct and execute a CQL query:

**Base query:**
```text
text ~ '{search_topic}' OR title ~ '{search_topic}'
```

**Add filters as provided:**
- Space filter: `AND space.key IN ('SPACE1', 'SPACE2')`
- Date filter: `AND {dateRange}` (e.g., `created > -30d`)
- Type filter: `AND type = '{contentType}'`
- Sort: `ORDER BY lastModified DESC`

Call `mcp_atlassian_searchConfluenceUsingCql` with the constructed query.

Collect all matching page IDs and metadata from results.

### Step 3: Execute Refined Searches

Expand the search to catch related content:

1. **Synonym search:** Extract keywords from initial results and search for variations
2. **Label search:** `label IN ('label1', 'label2')` using labels found in initial results
3. **Hierarchical search:** `ancestor = {pageId}` for pages that are children of relevant content
4. **Space-specific deep search:** Use `mcp_atlassian_getPagesInConfluenceSpace` for thorough coverage

Deduplicate across all search results by page ID.

### Step 4: Download and Process Content

Use the `download-confluence-pages` skill methodology:

- Process pages sequentially, one at a time
- For each page, call `mcp_atlassian_getConfluencePage` to get full content
- Save each page as markdown in the `confluence/` directory
- Use naming convention: `{page_id}_{sanitized_title}.md`
- Confirm each file is saved before proceeding to the next

Optionally collect additional context per page:
- `mcp_atlassian_getConfluencePageAncestors` for hierarchy context
- `mcp_atlassian_getConfluencePageFooterComments` for discussions
- `mcp_atlassian_getConfluencePageDescendants` for child content

### Step 5: Analyze and Categorize

Review all downloaded content and:

1. **Score relevance:** Rate each document's relevance to the search topic, weighting more recent content higher
2. **Categorize by theme:** Group documents into logical categories/subtopics
3. **Extract key insights:** Identify important findings, decisions, and patterns
4. **Map relationships:** Document how pages relate to each other
5. **Identify gaps:** Note areas where information is missing or insufficient

### Step 6: Generate Summary

Produce a structured summary document (`confluence/SUMMARY.md`):

```markdown
# Confluence Research: {search_topic}

**Searched:** {timestamp}
**Documents Found:** {count}
**Spaces Searched:** {space_list}

## Executive Summary

{2-3 paragraphs summarizing the overall findings}

## Detailed Findings by Category

### {Category 1}
{Analysis with references to source documents}

### {Category 2}
{Analysis with references to source documents}

## Key Insights

1. {Insight with supporting evidence}
2. {Insight with supporting evidence}

## Information Gaps

- {Area with insufficient documentation}

## Recommendations

1. {Actionable recommendation}

## Source Documents

| # | Title | Space | Relevance | File |
|---|-------|-------|-----------|------|
| 1 | Page Title | ENG | High | 123456_page-title.md |
```

### Step 7: Cross-Validate

Before finalizing:

1. Spot-check summary statements against source documents
2. Verify all major themes from the content are represented
3. Confirm category assignments are logical
4. Re-run a targeted search with different terms to check for missed content
5. Validate that downloaded files are complete and readable

## Output Contract

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

| Field | Meaning |
|---|---|
| `success` | Whether the search and summarization completed |
| `searchTopic` | The topic that was searched |
| `executiveSummary` | High-level summary of the findings |
| `documentsFound` | Total relevant documents discovered across all search passes |
| `documentsDownloaded` | Documents saved as files — `0` when `download = false` |
| `outputDirectory` | Directory holding the downloaded files |
| `summaryPath` | Path to the generated summary markdown |

### Errors

| Code | When |
|---|---|
| `CONNECTION_FAILED` | MCP server not configured, OAuth expired, or network failure (Step 1 prerequisite) |
| `NO_RESULTS_FOUND` | The primary search and every refined search returned zero matches for the topic |
| `DOWNLOAD_FAILED` | Page files or the summary could not be written (filesystem permissions, disk space) |

```json
{ "code": "NO_RESULTS_FOUND", "message": "No Confluence content found for topic 'nonexistent topic'", "searchTopic": "nonexistent topic", "searchQuery": "text ~ 'nonexistent topic' OR title ~ 'nonexistent topic'" }
```

A space that is inaccessible does not abort the run — skip it, note it in the summary's coverage section, and continue with the remaining spaces.

## Quality Checklist

- [ ] All relevant spaces were searched
- [ ] Multiple search strategies were used (text, title, labels, hierarchy)
- [ ] Results are deduplicated
- [ ] All identified documents were downloaded
- [ ] Content is properly categorized
- [ ] Summary accurately reflects source documents
- [ ] Key insights are supported by evidence
- [ ] Information gaps are honestly acknowledged
