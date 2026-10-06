---
name: set-acceptance-criteria
description: >-
  Sets the Acceptance Criteria field on an existing Jira issue using the
  Atlassian Document Format (ADF). Constructs the standard "I know this is
  done when:" + bulletList structure and applies it via editJiraIssue in a
  separate API call from any description (markdown) updates. Supports
  replacing the field outright or appending new criteria to the issue's
  existing AC list (`acMergeMode`). Use when an issue type supports the AC
  custom field (Story, Task, Sub-task, Epic -- not Bug).
---

# Set Acceptance Criteria

Single-purpose skill that writes a list of acceptance criteria into the Jira AC custom field (`{{acceptanceCriteriaFieldId}}`) using the standard ADF document pattern. Used by the `create-jira-issues` and `update-jira-issues` workflow skills, but also callable on its own.

## When to Use

- After creating an issue whose profile has `acceptanceCriteriaMode = adf-field` (Story, Task, Sub-task, Epic)
- When updating just the AC on an existing issue
- When merging new criteria into an issue's existing AC list without overwriting it (`acMergeMode = append`)
- Whenever AC needs to be set without touching the description

**Do NOT use this for Bug issues** -- the AC custom field is unavailable for Bugs; use `inline-description` mode and embed AC in the description instead (handled in the workflow skills).

## Prerequisites

- Atlassian MCP connection validated (use `validate-mcp-connection`)
- `cloudId` is known
- The target issue exists and the AC custom field is configured for its issue type

## Inputs

| Input | Type | Required | Description |
|---|---|---|---|
| `cloudId` | string | yes | Atlassian cloud instance ID |
| `issueKey` | string | yes | Existing issue key (e.g., `"PROJ-123"`) |
| `acceptanceCriteria` | string[] or string | yes | List of AC strings (array, or comma-/newline-separated string that the skill splits) |
| `acceptanceCriteriaFieldId` | string | yes | The AC custom field ID (e.g., `"customfield_10001"`). Callers resolve this from `config.fieldIds.acceptanceCriteria` (loaded via `load-jira-config`). When invoking this skill standalone (not from `create-jira-issues` / `update-jira-issues`), the caller must obtain this ID by either reading `.ai/jira.config.json` or calling `getJiraIssueTypeMetaWithFields` and locating the "Acceptance Criteria" field. |
| `acMergeMode` | enum | no | `replace` (default) or `append`. `replace` overwrites the entire AC field with the new list (the original behavior). `append` reads the issue's current AC, then appends only the new items not already present (dedupe by trimmed, case-insensitive text), preserving existing bullets' order. Applies only to this `adf-field` AC pattern; omit (or leave as `replace`) to keep the previous behavior. |

## Workflow

### Step 1: Normalize the AC List

If `acceptanceCriteria` is a string, split it:

- Newline-separated: split on `\n` and trim each line
- Comma-separated: split on `,` and trim each item
- Drop empty lines / items
- If the input is an array, just trim each entry and drop empties

If the resulting list is empty, return a `FieldValidationError` (no AC to set).

### Step 1b: Merge With Existing AC (`append` mode only)

Run this step **only** when `acMergeMode = append`. When `acMergeMode = replace` (the default), skip it entirely -- the final AC list is just the normalized list from Step 1 and behavior is exactly as before.

1. **Read the current field.** Call `mcp_atlassian_getJiraIssue` with `cloudId` and `issueKey`, and read the value of the `acceptanceCriteriaFieldId` field (the stored ADF document). If the issue does not exist, return `ISSUE_NOT_FOUND`.
2. **Extract existing bullets.** Walk the stored ADF document's `bulletList` node(s); for each `listItem`, take the text of its `paragraph` node(s). Ignore the leading "I know this is done when:" paragraph and any `heading` nodes. The result is the ordered list of existing AC strings.
3. **Merge (dedupe).** Start from the existing strings in their current order, then append each item from the Step 1 list that is **not** already present. Compare for duplicates by normalized text -- trim surrounding whitespace and compare case-insensitively. Never reorder or drop existing bullets; new items go after them.
4. Use this merged list as the final AC list for Step 2.

**Edge case -- empty or absent current field:** If the field has no value, is empty, or has no parseable `bulletList` items, treat the existing list as empty. `append` then behaves exactly like `replace` (the final list is just the Step 1 list).

**Worked example (`append`):**

- Existing AC bullets on the issue: `["User can log in", "Error shown on failure"]`
- New `acceptanceCriteria` input: `["User can log out", "user can log in"]`
- Merge: `"user can log in"` is a case-insensitive duplicate of an existing bullet, so it is dropped; `"User can log out"` is appended after the existing bullets.
- Final AC list written: `["User can log in", "Error shown on failure", "User can log out"]` → `criteriaCount: 3`, `mode: "append"`.

### Step 2: Construct the ADF Document

Build the standard "I know this is done when:" + bulletList structure documented in {{file:../create-jira-issues/references/adf-format-guide.md}} (Acceptance Criteria Pattern). Use the **final AC list** -- the merged list from Step 1b when `acMergeMode = append`, otherwise the normalized list from Step 1:

```json
{
  "type": "doc",
  "version": 1,
  "content": [
    {
      "type": "paragraph",
      "content": [{"type": "text", "text": "I know this is done when:"}]
    },
    {
      "type": "bulletList",
      "content": [
        /* one listItem per AC string */
      ]
    }
  ]
}
```

For each AC string, append a `listItem` to the `bulletList.content`:

```json
{
  "type": "listItem",
  "content": [
    {
      "type": "paragraph",
      "content": [{"type": "text", "text": "<AC string here>"}]
    }
  ]
}
```

**Required ADF rules** (full details in `adf-format-guide.md`):

- The top-level doc MUST include `"version": 1`
- Every `listItem` MUST contain a `paragraph` node (not bare text)
- Inline marks like `code` or `link` are allowed inside `text` if the AC string requires them, but the basic pattern uses plain `text`

### Step 3: Apply via `editJiraIssue` -- Separate Call

Call `mcp_atlassian_editJiraIssue`. The key in `additional_fields` is the resolved `acceptanceCriteriaFieldId` input (resolved by the caller from `config.fieldIds.acceptanceCriteria`):

```json
{
  "cloudId": "<cloudId>",
  "issueIdOrKey": "<issueKey>",
  "additional_fields": {
    "<acceptanceCriteriaFieldId>": { /* the ADF doc from Step 2 */ }
  }
}
```

The legacy placeholder `{{acceptanceCriteriaFieldId}}` referenced in older docs maps to this same input.

**CRITICAL CONSTRAINT:** This call MUST NOT include `description`, `summary` markdown updates, or any other markdown-bearing field in the same request. Combining ADF and markdown causes `"Failed to convert markdown to adf"`. The caller (workflow skill or prompt) is responsible for ordering this skill's call separately from any description update.

### Step 4: Return Status

On success, return (`criteriaCount` is the **final** number of bullets written -- after the Step 1b merge when `append`):

```json
{
  "success": true,
  "issueKey": "<issueKey>",
  "criteriaCount": <N>,
  "mode": "replace"
}
```

`mode` echoes the effective `acMergeMode` (`replace` or `append`).

On failure, return one of the error responses below.

## Output Contract

### Success Response

`criteriaCount` is the final bullet count written to the field (after the Step 1b merge when `acMergeMode = append`). `mode` echoes the effective merge mode.

```json
{
  "success": true,
  "issueKey": "PROJ-123",
  "criteriaCount": 3,
  "mode": "append"
}
```

### Error Responses

| Code | When |
|---|---|
| `FIELD_VALIDATION_FAILED` | `acceptanceCriteria` was empty or unparseable |
| `ISSUE_NOT_FOUND` | The `issueKey` does not exist |
| `UPDATE_FAILED` | `editJiraIssue` returned an unrecoverable error |

```json
{ "code": "<error code>", "message": "...", "details": "..." }
```

## Common Mistakes

| Mistake | Result | Fix |
|---|---|-----|
| Combining this call with a `description` update | `"Failed to convert markdown to adf"` | Always call this skill in its own `editJiraIssue` request |
| Using plain text for the AC field | API error | The field requires ADF JSON -- use this skill |
| Missing `version: 1` in the doc | Validation failure | Step 2 always includes `"version": 1` |
| Bare text inside `listItem` (no `paragraph` wrapper) | Rendering issue | Step 2 wraps every `listItem` content in a `paragraph` node |
| Calling this for a Bug issue | The AC field is unavailable on Bugs | Use the inline-description flow in the workflow skills instead |
| Treating `append` as a multi-write operation | Redundant `editJiraIssue` calls | `append` adds one `getJiraIssue` read (Step 1b); the merged doc is still written in a single `editJiraIssue` call (Step 3) |

## Reference Documents

- {{file:../create-jira-issues/references/adf-format-guide.md}} -- Full ADF pattern catalogue (acceptance criteria, multi-section AC, inline marks)
- {{file:../create-jira-issues/references/jira-field-mappings.md}} -- The `{{acceptanceCriteriaFieldId}}` placeholder definition
- {{file:../create-jira-issues/references/mcp-tool-usage.md}} -- The full markdown / ADF separation rule
