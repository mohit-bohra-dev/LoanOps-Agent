---
name: configure-jira
description: >-
  Generates or repairs one project entry in the consuming repo's
  `.ai/jira.config.json` by discovering that Jira project's live issue types and
  per-type field metadata via the Atlassian MCP, heuristically mapping the
  package's logical field names to the project's custom field IDs, capturing
  per-team default values, and writing the merged multi-project file behind an
  explicit user-approval gate. Multi-project safe — merges one project entry at a
  time and preserves every other entry. Use whenever a workflow needs a config
  that does not exist yet, needs an entry for a project that is missing from an
  existing config, or when a team is onboarding a new Jira project.
promp:
  package: "jira"
  version: "1.10.0"
  environment: "development"
  prompVersion: "1.0.1-beta.83"
  skill: "configure-jira"
---

# Configure Jira

Interactive bootstrap for the per-team `.ai/jira.config.json`. Discovers **one** Jira project's live field configuration, captures the team's default values, previews the merged file, and writes it only after explicit approval.

## When to Use

- No `.ai/jira.config.json` exists in the consuming repo (`load-jira-config` returned `found = false`)
- The file exists but has no entry for the project a workflow needs (`PROJECT_NOT_IN_CONFIG`)
- A team is onboarding an additional Jira project into an existing config
- A Jira admin renamed or added fields and the project entry must be re-discovered

For drift detection against an existing config **without** rewriting it, use `verify-jira-config` instead. This skill writes; that one is read-only.

## Prerequisites

- Atlassian MCP server reachable (this skill invokes `validate-mcp-connection` in Step 1)
- The invoking user has read access to the target Jira project's issue-type metadata
- Write access to the consuming repo's `.ai/` directory

## Inputs

| Input | Type | Required | Description |
|---|---|---|---|
| `projectKey` | string | no | Jira project key to configure (e.g., `"AIP"`). Must match `^[A-Z][A-Z0-9_]+$`. When omitted, the skill asks the user. **Exactly one project per invocation.** |
| `siteUrl` | string | no | Atlassian site URL (e.g., `https://pennymac.atlassian.net`). When omitted, detected from `validate-mcp-connection`. |
| `force` | boolean | no | Skip the per-project replace-confirmation prompt when an entry already exists for `projectKey`. Default `false`. Does **not** suppress the final write-permission gate (Step 10). |

## Workflow

### Step 1: Validate the MCP Connection

Invoke the `validate-mcp-connection` skill. Capture `cloudId` (UUID) and the resolved site URL as `detectedSiteUrl`. When the caller supplied `siteUrl`, prefer it over the detected value.

**CRITICAL STOP CONDITION:** If validation fails after 2 retries, return `ConnectionError` (`CONNECTION_FAILED`) and stop.

### Step 2: Load the Existing Config (Full View) and Decide the Merge Mode

Invoke `load-jira-config` with `mode = "full"` — do **not** pass `projectKey`. The full view is required so the merge in Step 9 can preserve every other project entry.

| Loader response | Behavior |
|---|---|
| `found = false` | `existingConfig = null`, `existingConfigPath = null`, `existingProjectKeys = []`. Step 11 will create a fresh file. |
| `found = true, valid = true` | `existingConfig = response.config`, `existingConfigPath = response.configPath`, `existingProjectKeys = Object.keys(response.config.projects)`. |
| `found = true, valid = false` | **Halt with `ConfigInvalidError`** (`CONFIG_INVALID`), surfacing `response.error.message` and the per-violation `details`. Merging into an invalid file would mask the existing problem. Tell the user to hand-fix the file or run `verify-jira-config` to inspect it. |

**Resolve `projectKey` here** so the merge mode can be decided before discovery begins: use the input when supplied, otherwise run Step 3's resolution logic inline (which makes Step 3 a no-op).

Assign `replaceMode` deterministically, then apply the confirmation gate:

| Condition | `replaceMode` | Confirmation |
|---|---|---|
| `existingConfig = null` | `create-file` | none |
| `projectKey ∉ existingProjectKeys` | `add` | none — the new entry sits alongside the existing ones |
| `projectKey ∈ existingProjectKeys`, `force = false` | `replace` | Ask: `An entry for project '<projectKey>' already exists in <existingConfigPath>. Replace just this entry (other projects: <other keys>) will be preserved? [y/N]`. On decline return `UserCancelled` (`USER_CANCELLED`) and stop. |
| `projectKey ∈ existingProjectKeys`, `force = true` | `replace` | skipped |

See @./.cursor\skills\configure-jira\references\merge-semantics.md for the full merge rules and worked scenarios.

### Step 3: Resolve the Project Key

Skip when Step 2 already resolved it. Otherwise: use the `projectKey` input when supplied; else ask the user (surfacing `existingProjectKeys` in the prompt when non-empty: `Existing entries: <list>. Enter the project key to add or replace:`).

Validate against `^[A-Z][A-Z0-9_]+$`.

**CRITICAL STOP CONDITION:** On mismatch return `InvalidProjectKeyError` (`INVALID_PROJECT_KEY`) with the received value and stop.

### Step 4: Discover Issue Types

Call `mcp_atlassian_getJiraProjectIssueTypesMetadata` with `cloudId` and `projectKey`. Capture the array of `{ id, name, description }` as `issueTypes`.

- Warn (do not fail) when none of `Story` / `Task` / `Bug` / `Sub-task` / `Epic` are present — the package's profiles will have nothing to match.
- On transient failure (timeout, 5xx), retry up to 2 times with brief backoff.

**CRITICAL STOP CONDITION:** If the project does not exist or the user lacks access, return `ProjectNotFoundError` (`PROJECT_NOT_FOUND`) and stop. If discovery still fails after retries, return `ConnectionError`.

### Step 5: Discover Per-Type Field Metadata

For each issue type from Step 4, call `mcp_atlassian_getJiraIssueTypeMetaWithFields` with `cloudId`, `projectKey`, and the issue type ID. Capture:

- `typeFieldMetadata` — map of issue type name → `[{ id, name, required, allowedValues }]`
- `allCustomFields` — deduplicated `{ id, name, allowedValues }` across the project, for ids matching `^customfield_\d+$`

Retry a failing type up to 2 times. If one type still fails, warn and continue with the rest — the user can re-run later. If **every** type fails, return `ConnectionError` and stop.

### Step 6: Map Logical Names to Field IDs

For each logical field name the package supports, case-insensitively match against the live `name` values in `allCustomFields`. The complete heuristic table lives in @./.cursor\skills\configure-jira\references\field-mapping-heuristics.md.

- On a match, set `fieldIds.<logicalName> = customfield_NNN`.
- On no match, set `fieldIds.<logicalName> = null` and note it for the preview.
- Collect required custom fields with no logical-name match as `unmatchedRequiredFields` — `customExtras` candidates for Step 9.

Every key the schema defines under a project's `fieldIds` must be present in the output, each holding either a `customfield_NNN` string or `null`. No keys are omitted.

### Step 7: Detect AC Mode and Channel Requirement Per Type

For each issue type in `typeFieldMetadata`, derive the two per-type postures and emit an override **only where the live project diverges from the package default**. The detection rules and the package defaults to compare against are in @./.cursor\skills\configure-jira\references\field-mapping-heuristics.md.

Output `issueTypeOverrides`: a map of type name → an object holding only the diverging keys (`acceptanceCriteriaMode`, `channelRequired`). Types matching the package defaults are omitted from the map entirely; no entry is ever an empty object.

### Step 8: Capture Per-Team Defaults

For each non-null `fieldIds.<name>` whose field is `required` on at least one issue type, ask the user for a default value:

- When Jira returns `allowedValues`, present them as a numbered multiple-choice list and accept a selection by number or exact value. Re-prompt on a value outside the list.
- When the field is free-form (no `allowedValues`), prompt for a string and state plainly that the value is passed through verbatim.
- Accept `null` when the user has no preference — the workflow skills will inline-prompt at create time.

Always ask for `defaults.workStream`, `defaults.team`, and `defaults.subtaskTrackingLabel` (the last only when the project exposes `Sub-task`). Ask for `defaults.bugEnvironment` / `bugSeverity` / `bugTestPhase` / `bugResponsibleTeam` only when the project exposes `Bug`.

### Step 9: Assemble the Project Entry and Build the Merge Preview

Construct the project entry with the canonical key order `fieldIds`, `defaults`, `issueTypeOverrides`, `customExtras`. Initialize `customExtras` as `{}`; when `unmatchedRequiredFields` is non-empty, offer to add any of them keyed by camelCase logical name.

Merge into the multi-project envelope per @./.cursor\skills\configure-jira\references\merge-semantics.md — that reference owns the fresh-envelope shape, the shallow-clone rule that preserves sibling projects, the `defaultProjectKey` stickiness rule, and the `$schema` / `site` preservation rules.

Validate before previewing: `previewConfig` parses as JSON; `$schema` is set; `site.url` and `site.cloudId` are non-empty; `projects[projectKey]` deep-equals the assembled entry; `projects` still contains every key from `existingProjectKeys`; `defaultProjectKey` is either null or a key present in `projects`.

### Step 10: Ask Permission

Present the merged config as a pretty-printed JSON preview plus a summary. State explicitly that only the named entry is added or replaced:

```text
I'd like to write the following Jira config:

**Path:** .ai/jira.config.json
**Site:** <detectedSiteUrl> (cloudId <UUID>)
**Project being <added | replaced>:** <projectKey>
**Other projects preserved:** <other keys, or "(none)">
**defaultProjectKey:** <value or "(unset)">
**Field IDs resolved for <projectKey>:** <N of 13>  (unresolved set to null)
**Defaults captured for <projectKey>:** <N>
**Issue type overrides for <projectKey>:** <list>
**Custom extras for <projectKey>:** <count>

<full merged JSON preview>

Shall I write the file?
```

**Wait for explicit user approval.** On decline return `UserCancelled` (`USER_CANCELLED`); the existing file is left untouched. This gate applies regardless of `force`.

### Step 11: Write the Config File

Write to `existingConfigPath` when non-null (preserving the user's chosen location), otherwise `<workspace_root>/.ai/jira.config.json`, creating `.ai/` if needed. Write the **merged envelope**, not just the new entry, with 2-space indentation.

Verify by reading the file back, parsing it, and confirming `parsed.projects[projectKey]` deep-equals the assembled entry and `parsed.projects` contains every key from `existingProjectKeys` plus `projectKey`. Capture `projectsAfterWrite = Object.keys(parsed.projects)`.

**CRITICAL STOP CONDITION:** On write or verification failure return `WriteError` (`WRITE_FAILED`) with the IO error in `details`.

### Step 12: Sanity-Check via `verify-jira-config`

Invoke the `verify-jira-config` skill in **single-project mode** with `cloudId` and `projectKey` — verify only the entry just written, not every project in the file. Capture the DriftReport.

When `driftReport.outcome = "drift-detected"`, surface the findings alongside the file path so the user can patch what the Step 6 heuristics missed before running a create or update workflow. Drift here does not fail the write.

### Step 13: Report

Return the success response below.

## Output Contract

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

`replaceMode` is one of `"add"`, `"replace"`, `"create-file"`. `projectsAfterWrite` lets a calling workflow confirm that no previously-configured project was dropped during the merge.

### Error Responses

| Code | When |
|---|---|
| `CONNECTION_FAILED` | MCP validation failed (Step 1), or every per-type discovery call failed (Step 5) |
| `CONFIG_INVALID` | The existing `.ai/jira.config.json` failed schema validation (Step 2) — hand-fix or replace it before re-running |
| `INVALID_PROJECT_KEY` | The project key did not match `^[A-Z][A-Z0-9_]+$` (Step 3) |
| `PROJECT_NOT_FOUND` | The project does not exist or the user lacks access (Step 4) |
| `WRITE_FAILED` | Could not write or verify `.ai/jira.config.json` (Step 11) |
| `USER_CANCELLED` | The user declined the replace confirmation (Step 2) or the write gate (Step 10) |

```json
{ "code": "INVALID_PROJECT_KEY", "message": "Project key must match ^[A-Z][A-Z0-9_]+$", "projectKey": "aip-foo" }
```

## Calling This Skill From a Workflow

`create-jira-issues` and `update-jira-issues` invoke this skill when their config load comes back missing (`found = false`) or short a project (`PROJECT_NOT_IN_CONFIG`). Pass `projectKey` whenever the caller knows it so this skill can skip its own project-key dialog. Callers must branch on the outcome:

| Outcome | Caller behavior |
|---|---|
| `success = true` | Re-invoke `load-jira-config` for the same `projectKey` and proceed with the freshly-written entry |
| `USER_CANCELLED` | Fall back to inline-prompting for field values for that one invocation |
| Any other error code | Halt — the underlying problem recurs if the workflow proceeds |

## Notes

- **One project per invocation.** Re-run once per Jira project the team works in; each run merges into the same file.
- **`defaultProjectKey` is sticky.** It is set only when the file is first created. Changing it later is a hand-edit.
- **The written file is meant to be committed** so every team member resolves the same field IDs and defaults.
- **No surprise overwrites.** An existing entry is replaced only after the Step 2 confirmation, and nothing is written without the Step 10 gate.

## Reference Documents

- @./.cursor\skills\configure-jira\references\field-mapping-heuristics.md — logical-name ↔ live field-name heuristics (Step 6) and the AC-mode / Channel-required detection rules (Step 7)
- @./.cursor\skills\configure-jira\references\merge-semantics.md — merge modes, envelope construction, `defaultProjectKey` stickiness, and worked scenarios (Steps 2 and 9)
- `../load-jira-config/references/jira.config.schema.json` — the schema the written file must conform to
- `../load-jira-config/SKILL.md` — the loader invoked in Step 2
- `../verify-jira-config/SKILL.md` — the drift check invoked in Step 12
- `../create-jira-issues/references/issue-type-requirements.md` — package-default AC modes compared against in Step 7
