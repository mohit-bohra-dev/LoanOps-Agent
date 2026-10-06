---
name: verify-jira-config
description: Detects drift between the per-team `.ai/jira.config.json` and the live Jira project(s). Compares configured field IDs, AC handling modes, and required-field coverage against what `getJiraIssueTypeMetaWithFields` returns, and emits a structured DriftReport. Multi-project: when the caller supplies a `projectKey`, verifies that single project; otherwise iterates every entry in `config.projects` and returns one sub-report per project. Read-only — never creates, updates, or deletes Jira issues. Use to check that an existing config still matches reality after Jira admins change field configurations, or as a sanity step inside `configure-jira`.
---

# Verify Jira Config

Compares the team's `.ai/jira.config.json` against live Jira project metadata and reports drift. Read-only: invokes only MCP discovery tools (`getJiraProjectIssueTypesMetadata`, `getJiraIssueTypeMetaWithFields`), never `createJiraIssue` or `editJiraIssue`.

This package is **multi-project**: a single `.ai/jira.config.json` can hold entries for multiple Jira projects under `config.projects.<KEY>`. This skill operates in two modes:

- **Single-project mode** — the caller supplies `projectKey`; the skill verifies just that project and returns one DriftReport.
- **All-projects mode** — the caller omits `projectKey`; the skill iterates every entry in `config.projects` and returns a multi-project report containing one sub-report per project (each shaped exactly like the single-project DriftReport).

## When to Use

- After a Jira admin changes field configurations on the project
- When `create-jira-issues` or `update-jira-issues` halts with `ConfigInvalidError` or `ProjectNotInConfigError`
- As a sanity-check step at the end of `configure-jira`
- Periodically to catch silent drift across all configured projects (run with `projectKey` omitted)

## Prerequisites

- Atlassian MCP server reachable (use `validate-mcp-connection` first)
- A `.ai/jira.config.json` file exists at one of the search paths (use `load-jira-config` first); when none exists, this skill returns the `no-config` outcome rather than erroring

## Inputs

| Input | Type | Required | Description |
|---|---|---|---|
| `cloudId` | string (uuid) | yes | Atlassian cloud ID, captured from `validate-mcp-connection` |
| `projectKey` | string | no | Project to verify against. When provided, runs in **single-project mode** for just this key. When omitted, runs in **all-projects mode** and iterates every entry in `config.projects`. |
| `issueTypes` | string[] | no | Subset of issue type names to verify (e.g., `["Story", "Epic"]`). Defaults to all issue types each project exposes. Applied uniformly to every project in all-projects mode. |

## Workflow

### Step 1: Load the Config (full multi-project view)

Invoke the `load-jira-config` skill with `mode = "full"` (do **not** pass `projectKey` — this skill needs the entire `config.projects` map to be able to iterate in all-projects mode and to validate single-project keys without re-loading).

- **`found = true, valid = true`** → continue with `config = response.config` (the full multi-project shape: `config.site`, `config.defaultProjectKey`, `config.projects`).
- **`found = true, valid = false`** → return the `ConfigInvalidError` outcome immediately, surfacing the loader's `error.code` and `details`. Do not call any MCP tool — there is nothing to verify against.
- **`found = false`** → return the `no-config` outcome with the loader's `searchedPaths` and the hint to run `configure-jira`. Do not call any MCP tool.

(Because we requested `mode = "full"`, the `PROJECT_NOT_IN_CONFIG` and `DEFAULT_PROJECT_KEY_MISSING` outcomes do not apply — they are exclusive to `mode = "resolved"`.)

### Step 2: Build the List of Projects to Verify

Branch on whether `projectKey` was supplied:

#### Single-project mode (`projectKey` input provided)

1. Look up `config.projects[<projectKey>]`.
2. If the entry does not exist, return `ProjectNotInConfigError` outcome with `requestedProjectKey` and `availableProjectKeys = Object.keys(config.projects)`. Do not call any MCP tool.
3. Set `projectsToVerify = [{ projectKey, projectEntry: config.projects[<projectKey>] }]`.

#### All-projects mode (`projectKey` input omitted)

1. Set `projectsToVerify = Object.entries(config.projects).map(([key, entry]) => ({ projectKey: key, projectEntry: entry }))`.
2. If `projectsToVerify` is empty (the `projects` map exists but has no entries), return `EmptyProjectsConfigError` outcome with the hint to run `configure-jira` to add at least one project.

### Step 3: Verify Each Project

For each `{ projectKey, projectEntry }` in `projectsToVerify`, run Steps 3a–3g below. Build one `projectReport` per project. Do not let one project's failure abort the others — capture per-project failure outcomes (`ProjectNotAccessibleError`, etc.) into the per-project report and continue to the next project.

#### Step 3a: Discover Issue Types

Call `mcp_atlassian_getJiraProjectIssueTypesMetadata` with `cloudId` and `projectKey` to enumerate the project's issue types.

- If the project does not exist or the user lacks access, set the project's `outcome = "ProjectNotAccessibleError"` with the project key and continue to the next project.
- If `issueTypes` input was provided, filter to that subset and warn (in the project report) about any names that don't match a real issue type for this project.

#### Step 3b: Discover Per-Type Field Metadata

For each issue type from Step 3a, call `mcp_atlassian_getJiraIssueTypeMetaWithFields` with `cloudId`, `projectKey`, and the issue type ID. Capture for each type:

- `issueTypeName` (e.g., `Story`)
- `fields` — array of `{ id, name, required }` covering both system and custom fields the issue type exposes
- `hasAcceptanceCriteriaField` — true iff any custom field's `name` matches the configured AC field name (heuristic: case-insensitive match against `Acceptance Criteria`)

Call this set `typeFieldMetadata` for the current project.

#### Step 3c: Compare Field IDs (Drift Category 1)

For each `projectEntry.fieldIds.<name>` entry that is **not null**:

1. Look up the field by ID in the merged set of fields across all issue types from Step 3b.
2. If the field ID does not exist in any issue type, append `{ category: "field-id-missing", logicalName, configuredId }` to the project's drift findings.
3. If the field exists but its `name` does not match the heuristic associated with `<name>` (e.g., `channel` should match a field named `Channel` or similar), append `{ category: "field-id-name-mismatch", logicalName, configuredId, liveName }`.

For each `projectEntry.fieldIds.<name>` entry that **is null**:

1. If a field with a matching heuristic name exists in the live metadata, append `{ category: "field-id-newly-available", logicalName, suggestedId, liveName }`. (Informational — the project has gained a field that's now configurable.)

#### Step 3d: Compare AC Modes (Drift Category 2)

Iterate **only over issue types that were actually discovered (and optionally filtered) in Steps 3a–3b** — not a fixed list. The set of types under inspection here is exactly `typeFieldMetadata` for this project.

For each issue type in `typeFieldMetadata`:

1. Determine the **expected AC mode**: `projectEntry.issueTypeOverrides[type].acceptanceCriteriaMode` if set, else the package's default for that type from the issue-type-requirements profiles. If the type has no package default and no override, skip it (no expectation to compare).
2. Determine the **live AC capability**: from Step 3b's `hasAcceptanceCriteriaField` flag for this type.
3. If `expected = adf-field` but live capability is false, append `{ category: "ac-mode-drift", issueType, expected: "adf-field", live: "no-ac-field", suggestedFix: "set issueTypeOverrides.<type>.acceptanceCriteriaMode = inline-description" }`.
4. If `expected = inline-description` but live capability is true, append `{ category: "ac-mode-drift", issueType, expected: "inline-description", live: "ac-field-available", suggestedFix: "set issueTypeOverrides.<type>.acceptanceCriteriaMode = adf-field" }`.

**Package-default type not discovered in project (informational):** Separately, after the iteration above, walk the package's documented profiles (Story, Task, Bug, Sub-task, Epic). For each one **not** present in `typeFieldMetadata`, append an informational finding `{ category: "package-type-absent", issueType, message: "Project does not expose this issue type; AC-mode drift not checked" }`. This keeps the report explicit about coverage gaps rather than silently skipping.

#### Step 3e: Compare Required Custom Fields (Drift Category 3)

A required custom field is considered **covered** by the project entry if its live `fieldId` (a `customfield_NNN`) appears as a value in **either** `projectEntry.fieldIds.*` **or** `projectEntry.customExtras.*`. Only required custom fields that are uncovered by **both** maps trigger drift findings.

For each issue type from Step 3b, identify required custom fields (`required = true` AND `id` matches `customfield_\d+`) where the `fieldId` is **not** present as a value in `projectEntry.fieldIds.*` **and** is **not** present as a value in `projectEntry.customExtras.*`:

1. If the field's name matches a logical name the package knows about (Channel, Work-Stream, Teams, etc.), append `{ category: "required-field-uncovered", issueType, fieldId, fieldName, logicalName, suggestedFix: "set fieldIds.<logicalName> in this project's config" }`.
2. If the field's name does NOT match a logical name, append `{ category: "required-field-unknown", issueType, fieldId, fieldName, suggestedFix: "add to this project's customExtras and supply value at create time" }`.

Additionally, if a required field IS covered by `projectEntry.fieldIds.*` (logical-name mapping) but the corresponding `projectEntry.defaults.*` is `null`, append `{ category: "required-default-missing", issueType, logicalName, suggestedFix: "set defaults.<logicalName> in this project's config" }`. Required fields covered only via `customExtras` do not trigger this finding (because `customExtras` is open-ended and not paired with package-level defaults).

#### Step 3f: Assemble the Per-Project Report

If no findings accumulated across Steps 3c–3e for this project, set the project's `outcome = "no-drift"`.

Otherwise, set `outcome = "drift-detected"` and group the findings by category as shown in the Output Contract.

#### Step 3g: Loop

Continue to the next project in `projectsToVerify`.

### Step 4: Aggregate and Return

#### Single-project mode

Return the single per-project report directly (one of `no-drift`, `drift-detected`, or `ProjectNotAccessibleError` shapes from Output Contract). The top-level `outcome` reflects that one project.

#### All-projects mode

Wrap the per-project reports in a multi-project envelope (Output Contract → Multi-project response). Aggregate the top-level `outcome`:

- `no-drift` if every project's `outcome = "no-drift"`
- `drift-detected` if any project has `outcome = "drift-detected"` and none have an error outcome
- `partial-failure` if at least one project has `outcome = "ProjectNotAccessibleError"` (or other per-project failure) AND at least one other project has a successful report
- `total-failure` if every project has a per-project failure outcome

## Output Contract

### Single-project mode — `no-drift`

```json
{
  "outcome": "no-drift",
  "mode": "single-project",
  "configPath": "/abs/path/to/.ai/jira.config.json",
  "projectKey": "AIP",
  "issueTypesChecked": ["Story", "Task", "Bug", "Sub-task", "Epic"]
}
```

### Single-project mode — `drift-detected`

```json
{
  "outcome": "drift-detected",
  "mode": "single-project",
  "configPath": "/abs/path/to/.ai/jira.config.json",
  "projectKey": "AIP",
  "issueTypesChecked": ["Story", "Task", "Bug", "Sub-task", "Epic"],
  "findings": {
    "fieldIdDrift": [
      { "category": "field-id-missing", "logicalName": "channel", "configuredId": "customfield_10253" }
    ],
    "acModeDrift": [
      { "category": "ac-mode-drift", "issueType": "Epic", "expected": "adf-field", "live": "no-ac-field", "suggestedFix": "..." }
    ],
    "requiredFieldDrift": [
      { "category": "required-field-uncovered", "issueType": "Story", "fieldId": "customfield_10500", "fieldName": "Component", "logicalName": null, "suggestedFix": "..." }
    ]
  }
}
```

### All-projects mode — multi-project response

```json
{
  "outcome": "drift-detected" | "no-drift" | "partial-failure" | "total-failure",
  "mode": "all-projects",
  "configPath": "/abs/path/to/.ai/jira.config.json",
  "projects": {
    "AIP": {
      "outcome": "no-drift",
      "projectKey": "AIP",
      "issueTypesChecked": ["Story", "Task", "Bug", "Sub-task", "Epic"]
    },
    "PCG": {
      "outcome": "drift-detected",
      "projectKey": "PCG",
      "issueTypesChecked": ["Story", "Bug"],
      "findings": {
        "fieldIdDrift": [],
        "acModeDrift": [
          { "category": "ac-mode-drift", "issueType": "Bug", "expected": "inline-description", "live": "ac-field-available", "suggestedFix": "..." }
        ],
        "requiredFieldDrift": []
      }
    }
  }
}
```

Each entry under `projects.<KEY>` is shaped exactly like the corresponding single-project response (minus the outer `mode` and `configPath`, which live at the envelope level). A project entry with `outcome = "ProjectNotAccessibleError"` looks like:

```json
{
  "outcome": "ProjectNotAccessibleError",
  "projectKey": "PCG",
  "message": "Project not found or access denied"
}
```

### Failure outcomes (no drift report produced — top-level only)

| `outcome` | Trigger | Mode |
|---|---|---|
| `no-config` | `load-jira-config` returned `found = false` | either |
| `ConfigInvalidError` | `load-jira-config` returned `found = true, valid = false` | either |
| `ProjectNotInConfigError` | Single-project mode, `projectKey` not in `config.projects` | single-project |
| `EmptyProjectsConfigError` | All-projects mode, `config.projects` exists but is empty | all-projects |
| `ConnectionError` | MCP discovery tool timed out or auth failed after retries | either |

```json
{ "outcome": "<outcome code>", "message": "...", "details": "..." }
```

(`ProjectNotAccessibleError` is per-project, not top-level — it appears inside `projects.<KEY>` in all-projects mode, or as the top-level outcome in single-project mode.)

## Read-Only Guarantee

This skill MUST NOT call:

- `mcp_atlassian_createJiraIssue`
- `mcp_atlassian_editJiraIssue`
- `mcp_atlassian_transitionJiraIssue`
- `mcp_atlassian_addCommentToJiraIssue`
- Any other MCP tool that mutates Jira state

It MUST NOT write to disk. The DriftReport is returned to the caller, never persisted.

## Reference

- `../load-jira-config/SKILL.md` — config source consumed in Step 1 (called with `mode = "full"`)
- `../configure-jira/SKILL.md` — the write path that creates or repairs the entries this skill verifies
- `../create-jira-issues/references/issue-type-requirements.md` — package-default AC modes consumed in Step 3d
- `../create-jira-issues/references/jira-field-mappings.md` — logical-name ↔ field-name heuristics consumed in Steps 3c and 3e
