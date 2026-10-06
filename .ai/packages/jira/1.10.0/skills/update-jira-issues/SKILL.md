---
name: update-jira-issues
description: >-
  Drives the end-to-end update workflow for existing Jira issues
  (Story / Task / Bug / Sub-task / Epic) via the Atlassian MCP server.
  Retrieves the current issue, builds a change set, asks user permission,
  applies updates in separate API calls (markdown vs ADF separation),
  optionally transitions status, and verifies the result. Use whenever a
  prompt or agent needs to update fields on an existing Jira issue.
---

# Update Jira Issues

End-to-end update workflow for any supported Jira issue type. Retrieves the current issue, builds a focused change set from caller-provided fields, asks for explicit user approval showing only the fields that will change, applies updates across the multiple API calls required by Atlassian's markdown / ADF separation, optionally transitions status, and verifies the result.

## When to Use

- Updating fields on an existing Story, Task, Bug, Sub-task, or Epic
- Changing summary, description, labels, acceptance criteria, or type-specific fields (Bug environment / severity / etc.)
- Transitioning an issue to a different status

For creation, use the `create-jira-issues` skill instead. For just the ADF acceptance-criteria pattern, use the `set-acceptance-criteria` skill.

## Prerequisites

- Atlassian MCP server reachable (use `validate-mcp-connection` first)
- The issue key must exist and the user must have permission to edit it

## Inputs

| Input | Type | Required | Description |
|---|---|---|---|
| `profileName` | enum | yes | One of `Story`, `Task`, `Bug`, `Sub-task`, `Epic` |
| `issueKey` | string | yes | Existing issue key (e.g., `"PROJ-123"`) |
| `summary` | string | no | Updated title |
| `description` | string (markdown) | no | Updated description |
| `acceptanceCriteria` | string or string[] | no | Updated AC list |
| `acMergeMode` | enum | no | `replace` (default) or `append`. Passed through to `set-acceptance-criteria` (Step 6b) to control whether the AC field is overwritten or merged with the issue's existing criteria. Applies only when the effective AC mode is `adf-field`; ignored for `inline-description` (Bug) profiles. |
| `labels` | string or string[] | no | Replaces existing labels |
| `priority` | string | no | Updated priority name as defined in the target Jira instance (e.g. `"High"`). Standard field, sent in object form as `{"name": "<priority>"}` in Call 1. Values are instance-specific and are not translated by this skill. |
| `storyPoints` | number | no | Numeric estimate written to `config.fieldIds.storyPoints` as a **bare number** (not an option object) in Call 1. Pass `null` to clear. Estimable types only (Story / Task / Bug) — Sub-tasks do not carry points. |
| `transition` | string | no | Target status name (e.g., `"To Do"`, `"In Progress"`, `"Done"`) |
| `assignee` | string | no | Set the assignee. A Jira account id, the token `"me"` (the current MCP-authenticated user), or `"unassigned"` to clear. Resolved in Step 6a. |
| `parentKey` | string | no | Story/Task-only: issue key of the parent **Epic** to link the issue under (Epic Link / parent). `"unassigned"` clears the parent. Resolved in Step 6a. |
| `environment` | string | no | Bug-only: updated environment |
| `severity` | string | no | Bug-only: updated severity |
| `testPhase` | string | no | Bug-only: updated test phase |
| `responsibleTeam` | string | no | Bug-only: updated responsible team |
| `epicExtras` | object | no | Epic-only: per-team Epic-specific custom fields (see `create-jira-issues` references) |

The skill operates on whatever subset of optional inputs is provided -- nothing else changes.

## Workflow

### Step 1: Validate MCP Connection

Invoke the `validate-mcp-connection` skill. Capture `cloudId`.

**CRITICAL STOP CONDITION:** If validation fails after 2 retries, return a `ConnectionError` and stop.

### Step 2: Load Jira Config

This package is **multi-project**: `.ai/jira.config.json` can hold entries for several Jira projects. For update operations, the active project is unambiguous — it is encoded in the `issueKey` parameter — so derive it deterministically before invoking the loader.

**2.0 — Derive the active project key from `issueKey` (BEFORE invoking `load-jira-config`):**

Split `issueKey` on the first `-` character. The portion before the dash is the project key (e.g., `"AIP-123"` → `"AIP"`, `"PCG-7"` → `"PCG"`, `"PROJ_X-42"` → `"PROJ_X"`). Validate the result against `^[A-Z][A-Z0-9_]+$` — if it does not match, return `FieldValidationError` (`FIELD_VALIDATION_FAILED`) with `field: "issueKey"` and a message that the issue key is malformed (do not invoke any further skills). `IssueNotFoundError` (Step 3) is reserved for the case where the key parses but the issue does not exist in Jira.

Set `activeProjectKey` to the derived value. Update operations always have a concrete project key, so `DEFAULT_PROJECT_KEY_MISSING` is impossible from this code path.

**2.1 — Invoke `load-jira-config`** with `mode = "resolved"` and `projectKey = activeProjectKey`. The skill returns one of four resolved-mode response shapes (the fifth, `DEFAULT_PROJECT_KEY_MISSING`, is unreachable here because `projectKey` is always supplied):

| `load-jira-config` response | Behavior |
|---|---|
| `found = true, valid = true` (no `error` field) | The response's `config` is the **flat single-project view**: `config.projectKey`, `config.site`, `config.fieldIds`, `config.defaults`, `config.issueTypeOverrides`, `config.customExtras`. Set `config = response.config` and continue to Step 3. |
| `found = true, valid = false` | **Halt with `ConfigInvalidError`.** Surface `response.error.message` and the per-violation `details`, and instruct the user to run the `verify-jira-config` skill to inspect drift. Do not attempt updates against an invalid config. |
| `found = false` | **Offer to bootstrap the config via `configure-jira`** — see Step 2a below. |
| `error.code = "PROJECT_NOT_IN_CONFIG"` | The config exists but has no entry for `activeProjectKey` (the project the issue lives in). **Offer to bootstrap that one project via `configure-jira` with `projectKey = <activeProjectKey>`** — see Step 2a below. |

The remainder of this skill is written assuming `config` is populated. Wherever a `{{*FieldId}}` placeholder appears in Step 6, resolve it via the **Config Resolution Reference** at the bottom of this skill (the same table that lives in `create-jira-issues/SKILL.md`). When `config = null` (after Step 2a fallback), prompt the user inline for each value the change set needs.

#### Step 2a: Conditionally Bootstrap via `configure-jira` (when `found = false` or `error.code = "PROJECT_NOT_IN_CONFIG"`)

When `load-jira-config` returns `found = false` or `error.code = "PROJECT_NOT_IN_CONFIG"`, ask the user before chaining into a configuration flow. Pick the message that matches the response:

**If `found = false`:**

> No `.ai/jira.config.json` was found at any of the searched paths: `<response.searchedPaths>`.
> Would you like me to run **`configure-jira` with `projectKey = <activeProjectKey>`** now to discover the project's field IDs and write a config? [Y/n]
> (If you decline, I'll fall back to asking for each field inline for this one update.)

**If `error.code = "PROJECT_NOT_IN_CONFIG"`:**

> `.ai/jira.config.json` exists but has no entry for project **`<activeProjectKey>`** (derived from `issueKey = <issueKey>`). The configured projects are: `<response.error.availableProjectKeys>`.
> Would you like me to run **`configure-jira` with `projectKey = <activeProjectKey>`** now to add an entry for this project? [Y/n]
> (If you decline, I'll fall back to asking for each field inline for this one update.)

Branch on the user's answer:

| User answer | Behavior |
|---|---|
| **Yes** (default) | Invoke the **`configure-jira`** skill with `projectKey = activeProjectKey` so it can skip its own project-key dialog. It will discover issue types, map field IDs, capture defaults, present a JSON preview, and gate the write behind its own permission step; it will **merge** the new entry into any existing `config.projects` map. After it returns, branch on its outcome (next table). |
| **No** | Set `config = null` and fall back to today's inline-prompt behavior. Each subsequent `{{*FieldId}}` reference must be resolved by asking the user for the value. Surface a one-line hint: `Tip: Run configure-jira anytime to add this project to .ai/jira.config.json so future invocations don't have to ask.` Continue to Step 3. |

After `configure-jira` returns, branch on its response:

| `configure-jira` outcome | Behavior |
|---|---|
| `success = true` | **Re-invoke `load-jira-config`** with the same `projectKey = activeProjectKey` to pick up the freshly-written entry. Expect `found = true, valid = true` (no `error`) on the second invocation. Set `config = response.config` (the flat single-project view) and continue to Step 3. If the second `load-jira-config` returns `found = false`, `valid = false`, or `error.code = "PROJECT_NOT_IN_CONFIG"`, halt with `BootstrapFailedError` (the write reported success but the entry is unreadable, invalid, or missing for the requested project). |
| `code = USER_CANCELLED` (declined overwrite, declined write preview, or aborted mid-flow) | Set `config = null` and fall back to inline-prompt behavior, exactly as if the user had answered "No" above. Continue to Step 3. |
| Any other error code (`CONNECTION_FAILED`, `INVALID_PROJECT_KEY`, `PROJECT_NOT_FOUND`, `WRITE_FAILED`) | **Halt this workflow** and surface the error to the user. The underlying problem will recur if the workflow proceeds. Do not fall back to inline prompts. |

Invoke `{{skill:jira.configure-jira}}` directly, supplying `projectKey` so the skill can skip its own project-key dialog.

### Step 3: Retrieve the Current Issue

Call `mcp_atlassian_getJiraIssue` with `cloudId` and `issueKey`.

- Confirm the issue exists.
- Confirm the issue type matches `profileName` (warn but continue if it differs; the workflow still works as long as the project's field schema for that type is valid).
- Capture current values for the fields the caller wants to change so the permission preview can show old to new.

**CRITICAL STOP CONDITION:** If the issue is not found, return an `IssueNotFoundError` and stop.

### Step 4: Load the Profile and Build the Change Set

Read the profile from {{file:../create-jira-issues/references/issue-type-requirements.md}} matching `profileName`. The profile drives AC handling (`adf-field` vs `inline-description`) and which type-specific fields are valid.

**Effective AC mode:** the per-issue-type AC mode is `config.issueTypeOverrides[profileName].acceptanceCriteriaMode` if set, otherwise the profile's documented `acceptanceCriteriaMode`. If `config.fieldIds.acceptanceCriteria` is `null`, force the mode to `inline-description` regardless of the profile (the project does not expose an AC custom field for this type).

Build a change set containing only the fields the caller provided:

- **Always-allowed (any profile):** `summary`, `labels`, `description`, `acceptanceCriteria`, `transition`, `assignee`
- **Estimable profiles (`Story` / `Task` / `Bug`):** `storyPoints`. Reject it for `Sub-task` with `FieldValidationError` (`field: "storyPoints"`) rather than silently dropping it — sub-tasks do not carry points.
- **Story / Task profile additions:** `parentKey` — re-parents the issue to a different Epic (or clears it). Applied in Call 1 (Step 6a).
- **Bug profile additions:** `environment`, `severity`, `testPhase`, `responsibleTeam`
- **Epic profile additions:** any keys in `epicExtras` matching configured Epic field placeholders, mapped through `config.fieldIds.epicName` / `epicStartDate` / `epicEndDate` / `epicTheme`
- **Effective AC mode = `adf-field`:** `acceptanceCriteria` becomes an ADF update via `set-acceptance-criteria` (Step 6b)
- **Effective AC mode = `inline-description`:** `acceptanceCriteria` is merged into `description` (see Step 6c)

If the change set is empty (no fields to update and no transition), return success with `fieldsUpdated: []` and skip to Step 8.

### Step 5: Ask Permission

Show the user only the fields that will change, with old to new values:

```text
I'd like to update {{issueKey}} with the following changes:

- **Summary:** "<old>" -> "<new>"
- **Labels:** [<old>] -> [<new>]
- **Acceptance Criteria:** <old preview> -> <new preview>
- **Transition:** <current status> -> <target status>
[type-specific fields as relevant]

Shall I proceed?
```

**Wait for explicit user approval before proceeding.**

If the user declines, return a `UserCancelled` outcome (not an error) and stop.

### Step 6: Apply Updates (Separate API Calls)

**CRITICAL:** Different field types must be updated in **separate** `editJiraIssue` calls. Combining markdown (description) with ADF (acceptance criteria) in one call causes `"Failed to convert markdown to adf"`. See {{file:../create-jira-issues/references/mcp-tool-usage.md}} `Multi-Field Update Strategy` for the full constraint.

**Resolve every `{{*FieldId}}` placeholder via `config`** (see the Config Resolution Reference at the end of this skill). When `config.fieldIds.<name>` is `null`, the project does not expose that field for this issue type — **omit the key from the payload** rather than sending `null`.

Call the subset that applies. Track each successful field name in `fieldsUpdated`.

#### Step 6a: Summary + Simple Fields (Call 1)

Combine all non-markdown, non-ADF fields into one call:

```json
{
  "cloudId": "{{cloudId}}",
  "issueIdOrKey": "{{issueKey}}",
  "summary": "<new summary if changed>",
  "additional_fields": {
    "labels": ["<new labels if changed>"],
    "priority": {"name": "<new priority if changed>"},
    "assignee": {"accountId": "<resolved account id when assignee provided>"},
    "<config.fieldIds.storyPoints>":        "<new storyPoints if changed — bare number, e.g. 5, NOT {\"value\": 5}>",
    "<config.fieldIds.bugEnvironment>":     {"value": "<new environment if Bug + changed>"},
    "<config.fieldIds.bugSeverity>":        {"value": "<new severity if Bug + changed>"},
    "<config.fieldIds.bugTestPhase>":       {"value": "<new testPhase if Bug + changed>"},
    "<config.fieldIds.bugResponsibleTeam>": {"value": "<new responsibleTeam if Bug + changed>"}
    /* Epic extras merged here when present, keyed by config.fieldIds.epic* */
  }
}
```

Only include keys whose values are actually changing. If `config.fieldIds.<name>` is `null` for any of these, omit that key entirely. If no simple-field changes, skip this call.

**Resolving `assignee`** (only when the caller provided it):

- `"me"` → resolve to the current user's `accountId` from `mcp_atlassian_atlassianUserInfo` (already retrieved during `validate-mcp-connection` in Step 1) and send `{"accountId": "<that id>"}`.
- a Jira account id → send `{"accountId": "<that id>"}` as-is.
- `"unassigned"` → send `{"accountId": null}` (or the equivalent unassign payload) to clear the assignee.
- a bare display name → **not resolvable here.** Return `FieldValidationError` (`FIELD_VALIDATION_FAILED`, `field: "assignee"`) explaining that an account id or `me` is required; do not guess an account id.

The assignee is a standard user field — it goes in the same Call 1 as `summary` / `labels` (never combined with description markdown or AC ADF). Track `assignee` in `fieldsUpdated` when applied.

**Resolving `parentKey`** (Story / Task only, when the caller provided it):

- An Epic issue key (e.g. `"PROJ-100"`) → on modern Jira Cloud send the standard `parent` field: `"parent": {"key": "<parentKey>"}`. When the consuming project uses the legacy company-managed **Epic Link** custom field, set `<config.fieldIds.epicLink>: "<parentKey>"` instead (resolved from config); send only one of the two.
- `"unassigned"` → clear the parent (`"parent": null`, or clear the configured Epic Link field).

`parentKey` is a standard field — include it in Call 1 alongside `summary` / `labels` / `priority` / `assignee` (never combined with description markdown or AC ADF). Track `parentKey` in `fieldsUpdated` when applied.

`priority` is likewise a standard field sent in Call 1 as `{"name": "<priority>"}`. Include it only when the caller provided it, so an omitted priority leaves the current value untouched rather than clearing it. Track `priority` in `fieldsUpdated` when applied. When Jira rejects the value because the name is not defined in the instance, surface `FieldValidationError` naming the rejected value — do not silently drop it.

#### Step 6b: Acceptance Criteria via ADF (Call 2 -- only when effective `acceptanceCriteriaMode = adf-field`)

If `acceptanceCriteria` is in the change set and the effective AC mode (from Step 4) is `adf-field`:

- Invoke the `set-acceptance-criteria` skill with the four required inputs plus the optional `acMergeMode` pass-through:
  - `cloudId` (from Step 1)
  - `issueKey` (the existing issue key)
  - `acceptanceCriteria` (the new AC list from the change set)
  - `acceptanceCriteriaFieldId` = **`config.fieldIds.acceptanceCriteria`** (resolved by THIS skill before delegating; the called skill does not load config itself)
  - `acMergeMode` (optional) -- forward this skill's `acMergeMode` input unchanged (default `replace`) so callers can request append/merge instead of overwrite
- This is a separate API call -- do not combine with description.

#### Step 6c: Description (Call 3 -- markdown alone)

If `description` is in the change set:

- For effective AC mode = `inline-description`: if `acceptanceCriteria` was also provided, merge it into the description before sending. If only `acceptanceCriteria` is provided without a new description, retrieve the current description from Step 3 and replace the AC section (or append it). `acMergeMode` does **not** apply here -- append/merge is only meaningful for the `adf-field` AC path (Step 6b); for `inline-description`, AC handling is governed by this description-merge logic.

```json
{
  "cloudId": "{{cloudId}}",
  "issueIdOrKey": "{{issueKey}}",
  "description": "<new markdown description, with merged AC for inline-description profiles>"
}
```

This call is markdown-only -- never combine with ADF fields.

### Step 7: Transition (Conditional)

If `transition` is in the change set:

1. Call `mcp_atlassian_getTransitionsForJiraIssue` with `cloudId` and `issueKey` to list available transitions.
2. Match the transition by name (case-insensitive). If no match, return a `TransitionError` listing the available transition names.
3. Call `mcp_atlassian_transitionJiraIssue` with the matching `transitionId`.
4. Set `transitioned = true` in the response.

### Step 8: Verify and Report

- Call `mcp_atlassian_getJiraIssue` to confirm the updates landed.
- Report which fields were updated and the new status (if transitioned).

## Output Contract

### Success Response

```json
{
  "success": true,
  "issueKey": "PROJ-123",
  "fieldsUpdated": ["summary", "labels", "acceptanceCriteria", "description"],
  "transitioned": false
}
```

When `transition` was applied, `transitioned: true` and the response includes the new status name.

### Error Responses

| Code | When |
|---|---|
| `CONNECTION_FAILED` | MCP connection or auth failed |
| `ISSUE_NOT_FOUND` | The `issueKey` does not exist |
| `FIELD_VALIDATION_FAILED` | Invalid field value for the profile (e.g., bad Bug severity) |
| `UPDATE_FAILED` | An `editJiraIssue` call returned an unrecoverable error |
| `TRANSITION_FAILED` | The requested transition is not available from the issue's current status |
| `USER_CANCELLED` | User declined the proposed update |

```json
{ "code": "<error code>", "message": "...", "field": "...", "details": "..." }
```

## Multi-Call Compatibility Matrix

| Combination | Result |
|---|---|
| `summary` + `labels` + `priority` + `assignee` + simple fields | Works in one call (Step 6a) |
| `acceptanceCriteria` (ADF) alone | Works as separate call (Step 6b) |
| `description` (markdown) alone | Works as separate call (Step 6c) |
| `description` + `acceptanceCriteria` (ADF profiles) | **FAILS** -- always split into Step 6b + Step 6c |
| `description` + `acceptanceCriteria` (Bug profile) | OK in one call after merging AC into description (no ADF involved) |

## Config Resolution Reference

This skill consumes the same config object shape as `create-jira-issues/SKILL.md`. See the **Config Resolution Reference** table in that skill for the full mapping of `{{*FieldId}}` placeholders → `config.fieldIds.*` paths and default-value placeholders → `config.defaults.*` paths.

**Rules (mirror of create-jira-issues):**

- A field ID resolved to `null` from `config` means the project does not expose that field for this issue type — **omit the key from the payload entirely**, never send `null`.
- A default resolved to `null` means the team has no default — **prompt the user inline** for the value when it's required.
- `config.issueTypeOverrides[profileName].acceptanceCriteriaMode` overrides the profile's documented AC mode when present.
- If `config.fieldIds.acceptanceCriteria` is `null`, the effective AC mode is forced to `inline-description`.

**Config keys this skill intentionally does NOT consume:**

- Top-level `config.defaultProjectKey` — not needed; update operations derive the project from `issueKey` in Step 2.0 (the project is unambiguous), so the loader is always called with an explicit `projectKey`.
- `config.issueTypeOverrides[profileName].channelRequired` — not needed; update operations only modify fields the caller asked about, and "Channel required" applies at create-time only.
- `config.defaults.*` (channel/workStream/team/subtaskTrackingLabel/bug*) — not consumed for updates because an existing issue already has values; the user must explicitly request a change. Defaults remain a create-only convenience.

## Reference Documents

- {{file:../create-jira-issues/references/issue-type-requirements.md}} -- Per-type profiles consumed by this skill
- {{file:../create-jira-issues/references/jira-field-mappings.md}} -- Field IDs and format types
- {{file:../create-jira-issues/references/adf-format-guide.md}} -- ADF structure (delegated to `set-acceptance-criteria`)
- {{file:../create-jira-issues/references/mcp-tool-usage.md}} -- Multi-call update strategy and known quirks
- `../load-jira-config/SKILL.md` -- Loader skill invoked in Step 2; documents the config object shape consumed throughout this workflow
- `../configure-jira/SKILL.md` -- Invoked in Step 2a to bootstrap or repair the project's `.ai/jira.config.json` entry
- `../verify-jira-config/SKILL.md` -- Read-only drift check the user runs when Step 2 halts with `ConfigInvalidError`
- `../create-jira-issues/SKILL.md` -- Sibling create workflow; canonical Config Resolution Reference table lives there
