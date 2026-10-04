# jira

Atlassian Jira and Confluence integration prompts with MCP server support for retrieving tickets, pages, searching content, and creating / updating issues.

## Why use this?

Stop context-switching to a browser to read a ticket, hunt through Confluence, or fill out yet another issue form. This package brings Jira and Confluence straight into your AI workflow, so you can pull the context you need and file well-formed, standards-compliant issues without leaving your editor.

- **Stay in flow** — retrieve any Jira ticket or Confluence page (and search across them) from the command line, optionally saving to markdown, instead of tab-hopping to a browser.
- **Well-formed issues, every time** — dedicated `create`/`update` workflows for Stories, Tasks, Bugs, and Epics enforce required project fields and correctly separate markdown from ADF-formatted fields like acceptance criteria.
- **No more "which fields does this project need?"** — the `configure-jira` skill discovers your team's live project field schema into `.ai/jira.config.json`, and `verify-jira-config` detects drift, so issue creation matches each project's real requirements.
- **Grounded research** — the `search-summarize-confluence` skill runs CQL queries, downloads all relevant pages, and produces a cited summary, turning scattered docs into a single answer.
- **Feeds AI tooling** — the `search-jira` skill exposes Confluence as an arbor-compatible, ranked-and-cited search source for retrieval-augmented workflows.
- **Composable from any package** — every capability is a skill, so a package that depends on jira transitively can invoke it. See [Composing With This Package](#composing-with-this-package).
- **Zero-friction auth** — the Atlassian MCP server is configured automatically on install and handles OAuth via a one-time browser flow.

## Installation

```bash
promp install jira
```

## Prerequisites

- Atlassian MCP server configured in your IDE
- OAuth authentication completed with Atlassian (the MCP server handles this via browser-based flow)

## MCP Server

This package configures the Atlassian MCP server using HTTP transport:

| Field | Value |
|-------|-------|
| **Server URL** | `https://mcp.atlassian.com/v1/mcp` |
| **Transport** | HTTP |
| **Authentication** | OAuth (handled by MCP server) |

The MCP server is automatically configured during installation. On first use, you will be prompted to authenticate via your browser.

## Composing With This Package

**Another package composes with jira through its skills, never its prompts.**

The promp CLI writes `.cursor/commands/*.md` only for packages that are direct dependencies of the consuming repo, while skills are installed for transitive dependencies too. A cross-package prompt reference is rewritten at install time into a `.cursor/commands/jira.<name>.md` path without checking whether that file was emitted, so a prompt reference from a package that depends on jira transitively resolves to a file that does not exist.

Skills are the stable public contract. Every skill in the [Skills](#skills) tables below carries a full invocation contract — an Inputs table, a Returns shape, and an Errors list — so a caller can invoke it without reading any prompt.

| Instead of referencing | Reference |
|---|---|
| the `getJira` prompt | `{{skill:jira.retrieve-jira}}` |
| the `createStory` / `createTask` / `createBug` / `createEpic` prompts | `{{skill:jira.create-jira-issues}}` with `profileName: Story` / `Task` / `Bug` / `Epic` |
| the `updateStory` / `updateTask` / `updateBug` / `updateEpic` prompts | `{{skill:jira.update-jira-issues}}` with `profileName: Story` / `Task` / `Bug` / `Epic` |
| the `linkIssues` prompt | `{{skill:jira.link-jira-issues}}` |
| the `configureJira` prompt | `{{skill:jira.configure-jira}}` |
| the `verifyJiraConfig` prompt | `{{skill:jira.verify-jira-config}}` |
| the `search` prompt | `{{skill:jira.search-jira}}` |
| the `searchConfluence` prompt | `{{skill:jira.search-summarize-confluence}}` |
| the `getConfluencePage` prompt | `{{skill:jira.get-confluence-page}}` |

The prompts below remain as slash-command entry points for humans working in a repo that depends on jira directly. Each is a thin wrapper: parameters, a load-the-skill instruction, and the response contract.

## Prompts

### Read / Search

#### getJira

Retrieve a specific Jira ticket by issue key with optional download to a markdown file.

```text
/jira.getJira CET-123
/jira.getJira issueKey=CET-123 download=true
```

- `issueKey` (string, required)
- `download` (boolean, optional). Default: `false`

#### getConfluencePage

Retrieve a specific Confluence page by page ID or title with optional download.

```text
/jira.getConfluencePage 123456789
/jira.getConfluencePage pageIdentifier="Deployment Runbook" download=true
```

- `pageIdentifier` (string, required)
- `download` (boolean, optional). Default: `false`

#### searchConfluence

Search Confluence for a topic, download relevant pages, and produce a comprehensive summary.

```text
/jira.searchConfluence "API rate limiting"
/jira.searchConfluence searchTopic="deployment process" specificSpaces=ENG,OPS
```

#### search

Lightweight, retrieval-shaped Confluence search that returns ranked, cited results in arbor's normalized `SearchResultSet` envelope (titles + excerpts; no download/summary). It is the **arbor search source** for Confluence — register it in a repo's `.kbs/.arbor.json` `sources[]` so `/arbor.search` federates into it — and degrades gracefully (soft error, never throws) when the Atlassian MCP is unavailable. For a full download + categorized summary, use `searchConfluence` instead.

```text
/jira.search query="incident escalation policy" limit=5
/jira.search query="deployment process" filters='{"spaces":["ENG","OPS"],"dateRange":"lastModified > -90d"}'
```

Register as an arbor source — easiest via `/arbor.addSource jira-confluence`, which writes:

```json
{ "id": "jira-confluence", "kind": "skill", "skill": "jira.search-jira", "enabled": true }
```

The source resolves to the `search-jira` skill so a repo that pulls jira in transitively still resolves it.

### Create

All create prompts are thin dispatchers around the `create-jira-issues` workflow skill. Each issue type uses a per-type profile (Story / Task / Bug / Sub-task / Epic) that determines required fields and acceptance-criteria handling.

#### createStory

```text
/jira.createStory summary="Add notification preferences" description="..." acceptanceCriteria="Toggle works,Persists across sessions"
```

- `projectKey` (string, optional). Jira project key (e.g., `AIP`, `PCG`); falls back to `defaultProjectKey` from `.ai/jira.config.json`.
- `summary` (string, required)
- `description` (string, optional)
- `acceptanceCriteria` (string, optional). Set as ADF in a separate API call after creation.
- `labels` (string, optional). Comma-separated.

#### createTask

```text
/jira.createTask summary="Upgrade DB driver to v3.2" description="..." labels="tech-debt,database"
```

- `projectKey` (string, optional). Falls back to `defaultProjectKey`.
- `summary` (string, required)
- `description`, `acceptanceCriteria`, `labels` (string, optional)

#### createBug

```text
/jira.createBug summary="Login redirect loop" description="..." environment=PRD severity="Sev 2" testPhase=Production responsibleTeam=Pennymac
```

- `projectKey` (string, optional). Falls back to `defaultProjectKey`.
- `summary` (string, required)
- `description`, `acceptanceCriteria`, `labels` (string, optional)
- `environment` (string, optional). Default `PRD`.
- `severity` (string, optional). Default `Sev 2`.
- `testPhase` (string, optional). Default `Production`.
- `responsibleTeam` (string, optional). Default `Pennymac`.

Bug acceptance criteria are merged into the description because the AC custom field is unavailable for Bugs. See `skills/create-jira-issues/references/jira-field-mappings.md` for allowed values for `environment`, `severity`, `testPhase`, and `responsibleTeam`.

#### createEpic

```text
/jira.createEpic summary="AI Portal — Self-Service Onboarding and Visibility" description="..." acceptanceCriteria="..." labels="pitcrew,ai-portal,phase-2"
```

- `projectKey` (string, optional). Falls back to `defaultProjectKey`.
- `summary` (string, required). Also serves as the Epic Name in modern Jira.
- `description`, `acceptanceCriteria`, `labels` (string, optional)
- `priority` (string, optional). A **standard** Jira field, sent as `{"name": "<priority>"}`; no field-id configuration needed. Names are instance-specific (`High`/`Medium`/`Low`, or `Highest`…`Lowest` where the project defines them) and passed through unchanged.
- `epicName` (string, optional). Used when the project keeps Epic Name as a separate field.
- `targetStartDate`, `targetEndDate` (string `YYYY-MM-DD`, optional)
- `theme` (string, optional)

The Epic profile uses `acceptanceCriteriaMode = inline-description` by default (since most projects, including AIP, do not expose the AC custom field on Epic). When the consuming project **does** expose the AC field on Epic, the profile flips to `adf-field` per the AC Mode Detection note in `issue-type-requirements.md`.

### Update

All update prompts are thin dispatchers around the `update-jira-issues` workflow skill. Each issue type uses the same per-type profiles. The skill handles the markdown / ADF separation by issuing multiple `editJiraIssue` calls.

#### updateStory

```text
/jira.updateStory issueKey=PROJ-123 summary="New title" transition="In Progress"
/jira.updateStory issueKey=PROJ-123 assignee=me
/jira.updateStory issueKey=PROJ-123 parentKey=PROJ-100   # link under a parent Epic
```

- `issueKey` (string, required)
- `summary`, `description`, `acceptanceCriteria`, `labels`, `transition` (string, optional)
- `assignee` (string, optional). A Jira account id, the token `me` (the current MCP-authenticated user), or `unassigned` to clear.
- `parentKey` (string, optional). Issue key of the parent **Epic** to link this story under (the Epic Link / parent relationship). `unassigned` clears the parent. The same parameter is available on `createStory`.

#### updateTask

Same parameter shape as `updateStory` (including the optional `parentKey` Epic link).

#### updateBug

```text
/jira.updateBug issueKey=PROJ-123 severity="Sev 1" environment=PRD
```

- `issueKey` (string, required)
- `summary`, `description`, `acceptanceCriteria`, `labels`, `transition` (string, optional)
- `environment`, `severity`, `testPhase`, `responsibleTeam` (string, optional). Bug-specific fields.

#### updateEpic

```text
/jira.updateEpic issueKey=PROJ-100 summary="New epic title" transition="In Progress"
/jira.updateEpic issueKey=PROJ-100 acceptanceCriteria="Outcome A,Outcome B"
```

- `issueKey` (string, required)
- `summary`, `description`, `acceptanceCriteria`, `acMergeMode`, `labels`, `priority`, `transition`, `assignee` (string, optional)
- `epicName`, `targetStartDate`, `targetEndDate`, `theme` (string, optional). Epic-specific fields, mirroring `createEpic`.

Omitting `priority` leaves the current value untouched — there is no clear token, since Jira issues always carry a priority.

The Epic profile uses `acceptanceCriteriaMode = inline-description` by default; `acMergeMode` (`append`/`replace`) applies only when the project exposes the AC custom field on Epic (`adf-field` mode).

### Link

#### linkIssues

```text
/jira.linkIssues links='[{"inwardIssue": "AIP-520", "outwardIssue": "AIP-521"}]'
/jira.linkIssues links='[{"inwardIssue": "AIP-30", "outwardIssue": "AIP-31", "type": "Relates"}]' onTypeUnavailable=fail
```

Creates directional links between existing issues — `Blocks`, `Relates`, `Duplicate`, `Clones` — via the `link-jira-issues` workflow skill.

- `links` (array, required). Each entry: `{ inwardIssue, outwardIssue, type?, comment? }`.
- `type` (string, optional). Default link type for entries that omit their own. Default `Blocks`.
- `comment` (string, optional). Posted on the outward issue.
- `onTypeUnavailable` (string, optional). `skip` (default) or `fail`, for when the instance does not define the requested type.
- `dryRun` (boolean, optional).

**Direction:** `inwardIssue` is the blocker, `outwardIssue` is the blocked issue — read it as the sentence *inward* **blocks** *outward*. Getting this backwards produces a board that tells the team to work in the wrong order, so confirm one link as a sentence before pushing a batch.

The skill calls `getIssueLinkTypes` first rather than assuming `Blocks` exists — link types are configured per instance, and administrators rename and remove them. It also reads each inward issue's existing links before creating anything, so re-running a sync does not duplicate links (Jira will happily create a second identical link if asked directly). A reverse link that already exists comes back in `conflicts` rather than being overwritten.

**This is not the Epic Link.** The parent/child relationship between a Story and its Epic is the `parentKey` field on `createStory` / `updateStory`. Using a link where a parent is meant leaves the story outside its epic's hierarchy.

### Configuration

#### configureJira

Generate or update **one project entry** in `.ai/jira.config.json` by discovering that project's live field configuration via MCP and capturing per-team defaults. The package's config file is **multi-project**: one file can hold entries for `AIP`, `PCG`, etc. — re-run `configureJira` once per project the team works in. Each invocation **merges** into the existing file rather than overwriting, so previously-configured projects are preserved.

```text
/jira.configureJira projectKey=AIP            # first time, writes a new file
/jira.configureJira projectKey=PCG            # adds PCG to the existing file
/jira.configureJira projectKey=AIP force=true # replaces the AIP entry without prompting
```

- `projectKey` (string, optional). When omitted, the prompt asks the user.
- `siteUrl` (string, optional). When omitted, detected via `validate-mcp-connection`.
- `force` (boolean, optional). Skip the per-project replace-confirmation prompt when an entry already exists for `projectKey`. Does **not** suppress the final write-permission prompt. Default `false`.

The success response includes `replaceMode` (`"add"` / `"replace"` / `"create-file"`) and `projectsAfterWrite` (the list of project keys present in the file after the merge), so you can confirm no entries were dropped. `defaultProjectKey` is **sticky** — it is set only when the file is first created; to change it later, hand-edit the file.

#### verifyJiraConfig

Detect drift between `.ai/jira.config.json` and the live Jira project(s). Read-only — never mutates Jira state. Multi-project: when `projectKey` is supplied, verifies just that project; when omitted, iterates **every** entry in `config.projects` and returns one sub-report per project under `projects.<KEY>` in the response envelope.

```text
/jira.verifyJiraConfig                                  # all projects in config.projects
/jira.verifyJiraConfig projectKey=AIP                   # just AIP
/jira.verifyJiraConfig projectKey=AIP issueTypes=Story,Epic
```

- `projectKey` (string, optional). When provided → single-project mode. When omitted → all-projects mode (iterates `config.projects`).
- `issueTypes` (string, optional). Comma-separated list, e.g. `"Story,Epic"`. Defaults to all issue types each project exposes.

The aggregated `outcome` in all-projects mode is `no-drift`, `drift-detected`, `partial-failure` (some project unreachable while another succeeded), or `total-failure` (every project unreachable). The throws set includes `ProjectNotInConfigError` (single-project mode against a key that isn't in `config.projects`), `EmptyProjectsConfigError` (all-projects mode when `config.projects` is `{}`), and `NoConfigError` (no config file found).

## Per-Team Configuration

The package's create / update workflow skills resolve `{{*FieldId}}` placeholders (Channel, Work-Stream, Teams, Acceptance Criteria, Bug Environment / Severity / Test Phase / Responsible Team, Epic Name / Start / End / Theme) and per-team defaults from a **multi-project** configuration file. One `.ai/jira.config.json` can hold entries for several Jira projects (`AIP`, `PCG`, ...), each with its own field IDs, defaults, issue-type overrides, and custom extras.

### Quick Start

Configure one project per run; re-run for each Jira project the team works in:

```text
/jira.configureJira projectKey=AIP   # first project — creates .ai/jira.config.json
/jira.configureJira projectKey=PCG   # second project — merges into the existing file
```

Each invocation walks through the discovery dialogue, presents a JSON preview that highlights which entry is being added or replaced (and which other projects are preserved), and only writes after explicit approval. After the write, the `verify-jira-config` skill runs as a single-project sanity check on the project you just configured.

### Where the Config Lives

`.ai/jira.config.json` at the consuming repo root. The file is intended to be **committed to the repo** so the whole team picks up the same field-ID resolution for every project.

The loader skill searches in this order (first match wins):

1. `<workspace_root>/.ai/jira.config.json`
2. `<cwd>/.ai/jira.config.json`
3. The nearest ancestor with `.ai/jira.config.json`, walking up from `<cwd>`

See [skills/load-jira-config/references/lookup-paths.md](skills/load-jira-config/references/lookup-paths.md) for the full rationale.

### What's in It

The config conforms to [skills/load-jira-config/references/jira.config.schema.json](skills/load-jira-config/references/jira.config.schema.json) (JSON Schema draft 2020-12). Top-level keys:

| Key | Purpose |
|-----|---------|
| `site` | Atlassian site URL + cloudId (cached to avoid an MCP discovery call on every invocation). One site per repo. |
| `defaultProjectKey` | Project key the workflow skills target by default (when no `projectKey` parameter is supplied and the operation does not derive one from an issue key). Must be a key present in `projects`. |
| `projects` | **Required.** Map of Jira project key (e.g. `"AIP"`, `"PCG"`) to that project's per-team configuration. At least one entry. |

Each `projects.<KEY>` entry has:

| Sub-key | Purpose |
|-----|---------|
| `fieldIds` | Map of 13 logical field names → `customfield_NNN` IDs (or `null` when the project does not expose the field) |
| `defaults` | Map of 8 logical names → default values used when the prompt parameter is absent |
| `issueTypeOverrides` | Per-type overrides for `acceptanceCriteriaMode` and `channelRequired` |
| `customExtras` | Open string-to-string map for project-specific custom fields not in the package's logical-name set |

### Multi-Project Example

```json
{
  "$schema": "./skills/load-jira-config/references/jira.config.schema.json",
  "site": {
    "url": "https://pennymac.atlassian.net",
    "cloudId": "12345678-1234-1234-1234-123456789abc"
  },
  "defaultProjectKey": "AIP",
  "projects": {
    "AIP": {
      "fieldIds": {
        "acceptanceCriteria": "customfield_10001",
        "channel": "customfield_10253",
        "workStream": "customfield_10209",
        "teams": "customfield_10254",
        "bugEnvironment": null,
        "bugSeverity": null,
        "bugTestPhase": null,
        "bugResponsibleTeam": null,
        "epicName": null,
        "epicStartDate": null,
        "epicEndDate": null,
        "epicTheme": null
      },
      "defaults": {
        "channel": "PCG",
        "workStream": "AI Platform Services",
        "team": "Default",
        "subtaskTrackingLabel": "subtask",
        "bugEnvironment": null, "bugSeverity": null,
        "bugTestPhase": null, "bugResponsibleTeam": null
      },
      "issueTypeOverrides": {
        "Epic": { "acceptanceCriteriaMode": "inline-description", "channelRequired": false }
      },
      "customExtras": {}
    },
    "PCG": {
      "fieldIds": {
        "acceptanceCriteria": null,
        "channel": "customfield_10253", "workStream": null, "teams": null,
        "bugEnvironment": "customfield_10100", "bugSeverity": "customfield_10101",
        "bugTestPhase": "customfield_10102", "bugResponsibleTeam": "customfield_10103",
        "epicName": null, "epicStartDate": null, "epicEndDate": null, "epicTheme": null
      },
      "defaults": {
        "channel": "Mortgage", "workStream": null, "team": null, "subtaskTrackingLabel": null,
        "bugEnvironment": "PRD", "bugSeverity": "Sev 2",
        "bugTestPhase": "Production", "bugResponsibleTeam": "Servicing"
      },
      "issueTypeOverrides": {},
      "customExtras": { "objective": "customfield_11624" }
    }
  }
}
```

### How Workflow Skills Resolve the Active Project

| Workflow | How `projectKey` is resolved |
|---|---|
| `createStory`, `createTask`, `createBug`, `createEpic` | Use the prompt's `projectKey` parameter when provided; otherwise fall back to top-level `defaultProjectKey`. If neither is set, the workflow halts with `DefaultProjectKeyMissingError`. |
| `updateStory`, `updateTask`, `updateBug`, `updateEpic` | Derive deterministically from the `issueKey` parameter (`AIP-123` → `AIP`, `PCG-7` → `PCG`). `defaultProjectKey` is irrelevant for updates. |
| `verify-jira-config` | Use the `projectKey` input for single-project mode; iterate `config.projects` when omitted. |
| `configure-jira` | Use the `projectKey` input or ask the user. Each run targets exactly one project. |

Once the active key is resolved, `load-jira-config` returns a **flat single-project view** of `config.projects[<activeProjectKey>]`. Downstream code reads `config.fieldIds.channel`, `config.defaults.workStream`, etc. — there is no nested `config.projects.<KEY>.*` access in the workflow skills themselves.

### Drift Detection

Run the `verify-jira-config` skill (or `/jira.verifyJiraConfig`) after a Jira admin changes field configuration, or whenever a workflow halts with `ConfigInvalidError`. The skill compares configured field IDs / AC modes / required-field coverage against live MCP discovery data and reports drift by category (`fieldIdDrift`, `acModeDrift`, `requiredFieldDrift`). In all-projects mode (run with no `projectKey`), each entry in `config.projects` gets its own DriftReport under `response.projects.<KEY>`, and a per-project failure (e.g., one project unreachable) does not abort the iteration over the others — the aggregated top-level `outcome` is `partial-failure` in that case.

### Fallback Behavior

If `.ai/jira.config.json` is **missing**, the create / update workflow skills offer to bootstrap it. If it exists but has **no entry for the active project** (the loader returns `ProjectNotInConfigError`), they offer to bootstrap just that one project. The exact flow:

1. Workflow asks one of two questions depending on what's missing:
   - *"No `.ai/jira.config.json` was found. Would you like me to run `configure-jira` now? [Y/n]"*
   - *"`.ai/jira.config.json` exists but has no entry for project `<KEY>` (configured: `<list>`). Would you like me to run `configure-jira` with `projectKey = <KEY>` now? [Y/n]"*
2. **If user answers Yes** → the workflow invokes the `configure-jira` skill (with `projectKey` passed in for the missing-project case, so it skips its own project-key dialog). It discovers field IDs, gates the file write behind its own permission step, and **merges** the new entry into the existing `config.projects` map (preserving every other configured project). On success, the workflow re-loads the config and proceeds with full per-team resolution. On any hard error (`CONNECTION_FAILED`, `INVALID_PROJECT_KEY`, `PROJECT_NOT_FOUND`, `WRITE_FAILED`, `CONFIG_INVALID`), the create / update workflow halts and surfaces that error.
3. **If user answers No, or cancels mid-bootstrap** → workflow falls back to inline-prompt behavior: prompt the user for each field ID and default value, one-time, for this invocation only.
4. **`BootstrapFailedError`** is returned in the rare case `configure-jira` reports a successful write but the freshly-written file (or specifically the freshly-written project entry) cannot be re-loaded or re-validated.

For creates, if the user did not supply `projectKey` AND `config.defaultProjectKey` is unset, the workflow halts with `DefaultProjectKeyMissingError` — the user must either re-invoke with an explicit `projectKey` or run `configure-jira` to set the default. (Updates never hit this error because the project is derived from `issueKey`.)

If the file exists but **fails schema validation**, the workflow skills halt with `ConfigInvalidError` and instruct the user to run `verify-jira-config` to inspect the drift.

If a specific `config.fieldIds.<name>` is `null`, the workflow omits that key from the create / update payload entirely (rather than sending `null`). Use this to express "this project doesn't expose that field on this issue type."

## Skills

This package includes 15 skills — the composable surface other packages depend on. Eight cover read / search workflows, four are the issue create / update / link workflow skills, and three cover per-team configuration bootstrap, loading, and drift verification.

### Read / Search Skills

| Skill | Description |
|-------|-------------|
| `validate-mcp-connection` | Validates Atlassian MCP server connectivity and user access |
| `retrieve-jira` | Retrieves a single Jira ticket by key with structured data extraction, markdown formatting, and optional download |
| `get-confluence-page` | Retrieves a single Confluence page by ID or title, with optional download |
| `download-jiras` | Batch downloads Jira tickets as markdown files |
| `download-confluence-pages` | Batch downloads Confluence pages as markdown files |
| `search-jira` | Federated search entry point: one CQL query over Confluence → ranked, cited `SearchResultSet`. Soft-fails so an arbor federation degrades gracefully. Backs the `jira-confluence` arbor source. |
| `search-summarize-confluence` | Multi-step search, download, and summarization workflow |
| `confluence-search-source` | The retrieval mechanics `search-jira` executes: CQL construction, result mapping, and source-relative scoring |

### Workflow Skills

| Skill | Description |
|-------|-------------|
| `create-jira-issues` | Drives the end-to-end create workflow (Story / Task / Bug / Sub-task / Epic). Loads an issue-type profile, assembles fields, asks user permission, calls `createJiraIssue`, dispatches AC handling, verifies. |
| `update-jira-issues` | Drives the end-to-end update workflow. Retrieves the issue, builds a focused change set, asks permission, applies updates across multiple `editJiraIssue` calls (markdown / ADF separation), optionally transitions status, verifies. |
| `set-acceptance-criteria` | Sets the AC field on an existing issue using ADF JSON in a separate API call. Used by both create and update workflows for AC-supporting issue types. |
| `link-jira-issues` | Creates directional links (`Blocks`, `Relates`, `Duplicate`, `Clones`) between existing issues. Discovers the instance's real link types, resolves direction, reads existing links so re-runs are idempotent, and reports reversed links as conflicts. |

### Configuration Skills

| Skill | Description |
|-------|-------------|
| `configure-jira` | Interactive bootstrap for `.ai/jira.config.json`. Discovers one project's live issue types and field metadata, maps logical field names to custom field IDs, captures per-team defaults, and writes the merged multi-project file behind an approval gate. Invoked by the create / update workflows when the config is missing or short a project. |
| `load-jira-config` | Locates and parses the multi-project `.ai/jira.config.json`, validates against the schema, and returns either a flat single-project view (resolved from the caller's `projectKey` input or top-level `defaultProjectKey`) or the full multi-project config. Read-only; no MCP. Invoked as Step 2 of every create / update workflow. |
| `verify-jira-config` | Compares configured field IDs / AC modes / required fields against live Jira metadata and emits a structured DriftReport. Multi-project: single-project mode (`projectKey` supplied) returns one report; all-projects mode (omitted) iterates every entry in `config.projects` and returns one sub-report per project. Read-only; uses only MCP discovery tools. |

### Issue-Type Profile Reference

The create / update workflow skills are driven by per-type profiles documented in [skills/create-jira-issues/references/issue-type-requirements.md](skills/create-jira-issues/references/issue-type-requirements.md). Each profile defines:

- `issueTypeName` -- the API value passed to `createJiraIssue`
- `requiredFields` / `recommendedFields` -- the field set the project enforces
- `acceptanceCriteriaMode` -- one of `adf-field`, `inline-description`, `none`
- `specialFieldHandling` -- type-specific quirks (parent for Sub-task, bug-specific fields for Bug, optional `epicExtras` for Epic)

Custom field IDs (`{{channelFieldId}}`, `{{acceptanceCriteriaFieldId}}`, etc.) are resolved at workflow runtime from the consuming repo's `.ai/jira.config.json` (see [Per-Team Configuration](#per-team-configuration) above). When that file is missing, the workflow falls back to inline-prompting for each value.

## Output Files

When using the `download` option, files are saved to local directories:

- **Jira tickets:** `jira/{issueKey}_{sanitized-summary}.md`
- **Confluence pages:** `confluence/{pageId}_{sanitized-title}.md`
- **Search manifest:** `confluence/MANIFEST.md`
- **Search summary:** `confluence/SUMMARY.md`

## Development

**Capabilities live in skills; prompts are entry points.** Add the skill first, then a prompt only if the capability needs a slash command.

To add a new skill:

1. Create a directory in `skills/` with a `SKILL.md` file carrying `name` / `description` frontmatter
2. Give it a full invocation contract: an `## Inputs` table, a numbered `## Workflow`, an output shape, and an error list — a caller must be able to invoke it without reading any prompt
3. Split supporting detail into `references/*.md` when `SKILL.md` grows past what a reader needs on the first pass
4. Add the skill reference to `promp.json` and to the [Skills](#skills) tables above

To add a new prompt:

1. Create a markdown file in `prompts/` with exactly: title and one-sentence description, `## Parameters`, `## Instructions` (load the skill, map parameters to skill inputs), `## Response Format`, `## Error Handling`
2. Add the prompt definition to `promp.json`
3. Update this README with usage instructions

For a new issue type, add a profile to `skills/create-jira-issues/references/issue-type-requirements.md` and pass its name as `profileName` — no new workflow skill is needed.

Never reference a prompt — this package's or another's — from a skill, a rule, or another prompt. Reference the skill instead. See [Composing With This Package](#composing-with-this-package).

## Version History

### 1.10.0

- **Cross-package composition moves from prompts to skills.** Every capability is now reachable as a skill with a complete invocation contract. Prompt names, parameters, and response shapes are unchanged, so `/jira.*` usage is unaffected; dependent packages should replace each prompt reference into this package with the corresponding `{{skill:jira.*}}` target — see the mapping table in [Composing With This Package](#composing-with-this-package).
- **`configure-jira` skill (new).** Absorbs the full interactive bootstrap procedure that previously lived in the `configureJira` prompt, with `references/field-mapping-heuristics.md` and `references/merge-semantics.md` holding the discovery heuristics and multi-project merge rules.
- **`search-jira` skill (new).** The Atlassian federated-search entry point, absorbing the `search` prompt's contract. The `jira-confluence` arbor source now registers as `{ "kind": "skill", "skill": "jira.search-jira" }`.
- **Invocation contracts on every referenced skill.** `retrieve-jira`, `get-confluence-page`, and `search-summarize-confluence` gained Inputs tables, response shapes, and error catalogues moved down from their prompts; `link-jira-issues` gained prerequisites and `dryRun` handling.
- **All 15 prompts thinned to slash-command entry points** — parameters, a load-the-skill instruction with a parameter-to-input mapping table, the response shape, and the error codes. The largest drops: `configureJira` 536 → 59 lines, `searchConfluence` 511 → 78, `getJira` 309 → 57, `getConfluencePage` 305 → 54.
- **Why:** the promp CLI emits `.cursor/commands/*.md` only for direct dependencies while installing skills for transitive ones, and rewrites prompt references without checking that the command file exists. Every cross-package prompt reference into a transitively-installed jira therefore resolved to a missing file. Skills are the only artifacts guaranteed to be present, so they are now the package's public contract.

### 1.9.0

- Added **Story Points** as a first-class configured field. `fieldIds.storyPoints` joins the schema (13 logical names), `configureJira` discovers it by name, and `verifyJiraConfig` covers it like any other logical field.
- `createStory` / `updateStory` accept a `storyPoints` number. It is written as a **bare number** to the configured field in the same call as summary/labels — unlike the select fields, it takes no `{"value": ...}` wrapper.
- Rejected for `Sub-task` (`FieldValidationError`) rather than silently dropped; sub-tasks do not carry points.
- Motivation: project workflows commonly validate on Story Points (for example, requiring Epic Link **and** Story Points before an issue may leave `Backlog`), so issues created without points could not be transitioned.

### 1.8.0

- **`linkIssues` prompt (new).** Creates directional links between existing issues (`Blocks`, `Relates`, `Duplicate`, `Clones`) through a new `link-jira-issues` workflow skill wrapping `getIssueLinkTypes` and `createIssueLink`. It discovers the link types the instance actually defines rather than assuming `Blocks` exists, resolves direction (`inwardIssue` = blocker, `outwardIssue` = blocked), reads each inward issue's existing links so re-runs do not duplicate, reports a reversed existing link as a `conflict` instead of overwriting it, and soft-skips by default when the requested type is unavailable. Issue links only — the parent Epic relationship remains the `parentKey` field.
- **`priority` on `createEpic` / `updateEpic` (additive).** An optional `priority` string, sent as the standard `priority` field in object form (`{"name": "<priority>"}`). No field-id configuration is involved. Values are instance-specific and passed through unchanged; on update, omitting it leaves the current priority untouched. Also documented as a generic input on the `create-jira-issues` / `update-jira-issues` workflow skills, so it is available to every issue-type profile.
- **`promp.json` bumped to 1.8.0.** Registered `linkIssues` and the `link-jira-issues` skill; added `priority` to `createEpic` and `updateEpic`. Also corrected `package.json`, which had drifted to `1.0.0`. Fully backward compatible — every new field is optional.
- **Why:** enables the `story` package to project a story dependency graph onto Jira as native links, and the `epic` package to sync an epic's decided priority instead of leaving it planning-only.

### 1.7.0

- **`updateEpic` prompt (new).** A thin dispatcher around the `update-jira-issues` workflow skill with the Epic profile — supports `summary`, `description`, `acceptanceCriteria` (+ `acMergeMode`), `labels`, `transition`, `assignee`, and the Epic-specific `epicName` / `targetStartDate` / `targetEndDate` / `theme`. Completes the create+update pair for Epics, mirroring Story/Task/Bug.
- **Story↔Epic parent linking (additive).** `createStory` and `updateStory` gained an optional `parentKey` parameter — the issue key of the parent **Epic** to link the story under (the standard `parent` field on modern Jira Cloud, or the legacy company-managed **Epic Link** custom field resolved from `config.fieldIds.epicLink`). `unassigned` clears the parent on update. The same handling is documented for `Task`. The `create-jira-issues` / `update-jira-issues` skills now apply `parent` for the Story/Task profiles, not only Sub-task.
- **`promp.json` bumped to 1.7.0.** Registered `updateEpic`; added `parentKey` to `createStory` and `updateStory`. Fully backward compatible — every new field is optional.
- **Why:** enables a dedicated `epic` package (epic ⇄ Jira lifecycle) and story parent-awareness (`story` linking a story to its parent epic) to be built entirely on jira prompts.

### 1.5.0

- **Assignee support (additive).** `updateStory` gained an optional `assignee` parameter — a Jira account id, the token `me` (the current MCP-authenticated user, resolved via `atlassianUserInfo`), or `unassigned` to clear. The `update-jira-issues` workflow skill resolves and applies it as a standard user field in the same call as `summary` / `labels` (never combined with description markdown or AC ADF), and tracks `assignee` in `fieldsUpdated`. A bare display name is rejected with `FieldValidationError` — an account id or `me` is required.
- **`getJira` now surfaces `assignee`** in its structured return (display name, or `null` when unassigned) in addition to the existing **Assignee:** line in the formatted content.
- **`promp.json` bumped to 1.5.0.** Added the `assignee` parameter to `updateStory` and the `assignee` property to the `getJira` returns. Fully backward compatible — every new field is optional.
- **Why:** enables downstream packages (notably `story`) to check and set Jira **assignment** through prompts, alongside the existing status-transition support.

### 1.4.0

- **Multi-project `.ai/jira.config.json`.** The schema now nests project-scoped settings (`fieldIds`, `defaults`, `issueTypeOverrides`, `customExtras`) under a top-level `projects` map keyed by Jira project key. Top-level `site` and `defaultProjectKey` remain. One config file can hold entries for multiple Jira projects (e.g., `AIP` + `PCG`).
- **`load-jira-config` skill** gained `projectKey` and `mode` inputs. `mode = "resolved"` (default) returns a flat single-project view (so downstream code keeps reading `config.fieldIds.channel`, `config.defaults.workStream`, etc. unchanged); `mode = "full"` returns the entire multi-project config for `configureJira` and `verifyJiraConfig` iteration.
- **`create-jira-issues` workflow skill** now resolves the active project key from the prompt's `projectKey` parameter (falling back to `defaultProjectKey`) before calling the loader. New error branches: `PROJECT_NOT_IN_CONFIG` (offers to bootstrap that one project via `configureJira projectKey=<X>`) and `DEFAULT_PROJECT_KEY_MISSING` (halts and asks the user to either supply `projectKey` or run `configureJira` to set `defaultProjectKey`).
- **`update-jira-issues` workflow skill** now derives the active project key deterministically by splitting `issueKey` on the first `-` (e.g., `AIP-123` → `AIP`). Adds a `PROJECT_NOT_IN_CONFIG` branch with the same bootstrap offer; `DEFAULT_PROJECT_KEY_MISSING` is unreachable for updates.
- **`verify-jira-config` skill** gained an all-projects mode: omitting `projectKey` iterates every entry in `config.projects` and returns one DriftReport per project under `response.projects.<KEY>`. Per-project failures (e.g., one project unreachable) do not abort the iteration. New aggregated outcomes `partial-failure` and `total-failure`.
- **`configureJira` prompt** is now multi-project safe: it loads the existing config in full mode, detects whether the run will `add` a new project / `replace` an existing entry / `create-file` from scratch, and **merges** the new entry into `config.projects` while preserving every other project. `defaultProjectKey` is sticky — only set on first-file-creation. Each invocation configures exactly one project; success response includes `projectKey`, `replaceMode`, and `projectsAfterWrite`.
- **`promp.json` bumped to 1.4.0.** Added `ProjectNotInConfigError` and `DefaultProjectKeyMissingError` to the throws lists of the create prompts (`createStory`, `createTask`, `createBug`, `createEpic`); added `ProjectNotInConfigError` to the update prompts. Added `ConfigInvalidError` and `InvalidProjectKeyError` to `configureJira`. Updated `verifyJiraConfig` returns to document the multi-project envelope shape and replaced `ProjectKeyMissingError` with `ProjectNotInConfigError`/`EmptyProjectsConfigError`/`NoConfigError`.
- **Migration note:** there was no v2 — this is a direct change to the 1.3.x configuration shape. The single-project shape from 1.3.x is no longer accepted by the schema. To migrate, move every existing top-level `fieldIds` / `defaults` / `issueTypeOverrides` / `customExtras` under `projects.<YOUR_PROJECT_KEY>.*` and ensure `defaultProjectKey` matches that key.

### 1.3.0

- Added per-team configuration via `.ai/jira.config.json` — a project-scoped JSON file describing custom field IDs, default values, per-issue-type AC overrides, and project-specific custom-field extras
- Added `configureJira` prompt that discovers live Jira project metadata and writes the config file with explicit user approval
- Added `verifyJiraConfig` thin-dispatcher prompt for drift detection
- Added `load-jira-config` skill — read-only loader invoked as Step 2 of every create / update workflow
- Added `verify-jira-config` skill — drift detection against live Jira metadata
- Added JSON Schema (draft 2020-12) at `skills/load-jira-config/references/jira.config.schema.json`
- Updated `create-jira-issues` and `update-jira-issues` workflow skills to load the config in a new Step 2 and resolve `{{*FieldId}}` placeholders deterministically; renumbered downstream steps. When the config is missing, the workflows now offer (with user consent) to chain into `configureJira` to bootstrap the config and then resume with the freshly-loaded config; if the user declines, the workflows fall back to inline-prompting for this one invocation.
- Added `BootstrapFailedError` throw to all create / update prompts to handle the rare case where `configureJira` reports a successful write but the post-write `load-jira-config` fails.

### 1.2.0

- Added `createEpic` prompt for creating Jira Epic issues
- Refactored `create-jira-issues` from a reference-doc skill into the end-to-end create workflow
- Added new `update-jira-issues` workflow skill (drives all update-* prompts)
- Added new `set-acceptance-criteria` workflow skill (encapsulates the ADF AC pattern)
- Collapsed the 6 existing create / update prompts into thin dispatchers (50-80 lines each, down from ~150) that pass an issue-type profile to the workflow skills
- Added Epic profile + Epic-Specific Fields section to skill references

### 1.1.x

- Added `createStory`, `createTask`, `createBug` and `updateStory`, `updateTask`, `updateBug` prompts
- Added `create-jira-issues` skill (initial reference-doc form)

### 1.0.0

- Initial release: 3 prompts (`getJira`, `getConfluencePage`, `searchConfluence`) + 6 read/validation skills

## License

MIT

## Author

Pennymac AI Platform
