---
promp:
  package: "jira"
  version: "1.10.0"
  environment: "development"
  prompVersion: "1.0.1-beta.83"
  prompt: "linkIssues"
---
# jira.linkIssues

Create directional links between existing Jira issues (Blocks, Relates, Duplicate, Clones) via the link-jira-issues workflow skill. Discovers the link types the instance actually defines, resolves direction (inwardIssue = blocker, outwardIssue = blocked), reads existing links so re-runs are idempotent, reports a reversed existing link as a conflict, and soft-skips when the requested type is unavailable. For dependency/blocking relationships only — the parent Epic relationship is the parentKey input on the create-jira-issues / update-jira-issues skills, not an issue link.

## Parameter Specifications

- **`links`** (array) - **Required**
  - Links to create. Each entry is an object: { inwardIssue, outwardIssue, type?, comment? }. Pass an array of one to create a single link. For directional types, inwardIssue is the blocker and outwardIssue is the blocked issue — for a dependency edge where the dependent needs the predecessor, inwardIssue = predecessor and outwardIssue = dependent.

- **`type`** (string) - *Optional*
  - Default link type for entries that omit their own. Matched case-insensitively against the types the instance defines, including their inward/outward descriptions.
  - Default: `Blocks`

- **`comment`** (string) - *Optional*
  - Default comment for entries that omit one. Posted on the outward issue.

- **`onTypeUnavailable`** (string) - *Optional*
  - What to do when the instance does not define the requested link type. 'skip' returns success with every link reported as skipped, so a project-configuration gap does not block the caller's wider workflow; 'fail' raises LINK_TYPE_UNAVAILABLE.
  - Default: `skip`

- **`dryRun`** (boolean) - *Optional*
  - Resolve and report the planned links without creating any.

## Instructions

You are executing a Promp package prompt. Follow these steps:

1. **Parse the user input** to extract parameters:
   - Parameter 1: `links` (required) - Links to create. Each entry is an object: { inwardIssue, outwardIssue, type?, comment? }. Pass an array of one to create a single link. For directional types, inwardIssue is the blocker and outwardIssue is the blocked issue — for a dependency edge where the dependent needs the predecessor, inwardIssue = predecessor and outwardIssue = dependent.
   - Parameter 2: `type` (optional) [default: Blocks] - Default link type for entries that omit their own. Matched case-insensitively against the types the instance defines, including their inward/outward descriptions.
   - Parameter 3: `comment` (optional) - Default comment for entries that omit one. Posted on the outward issue.
   - Parameter 4: `onTypeUnavailable` (optional) [default: skip] - What to do when the instance does not define the requested link type. 'skip' returns success with every link reported as skipped, so a project-configuration gap does not block the caller's wider workflow; 'fail' raises LINK_TYPE_UNAVAILABLE.
   - Parameter 5: `dryRun` (optional) - Resolve and report the planned links without creating any.

2. **Replace parameter placeholders** in the prompt content below:
   - Parameters use the format `{{parameterName}}` in the prompt
   - Replace each placeholder with the corresponding parsed value
   - If a parameter is optional and not provided, use its default value (if specified)
   - If a required parameter is missing, ask the user to provide it

3. **Execute the prompt** with the replaced parameters

## Usage

When the user invokes this command, they may provide parameters in various ways:
- Space-separated values: `/jira.linkIssues value1 value2`
- Named parameters: `/jira.linkIssues param1=value1 param2=value2`
- Mixed format: `/jira.linkIssues value1 param2=value2`

Parse flexibly and map values to the expected parameters in order for positional arguments.

## Expected Output

Per-link outcome of the linking pass

**Type:** `object`

**Properties:**

- `success` (boolean) - **Required** - True when the pass completed, including when every link was skipped. False only when nothing could be attempted.
- `resolvedType` (string) - *Optional* - The link type name as the instance defines it
- `created` (array) - **Required** - 
- `skipped` (array) - **Required** - Links not created, each with a reason (ALREADY_LINKED, TYPE_UNAVAILABLE)
- `conflicts` (array) - *Optional* - Pairs where a reverse link of the same type already exists; reported rather than overwritten
- `failed` (array) - *Optional* - 
- `availableTypes` (array) - *Optional* - 
## Error Handling

### ConnectionError

The Atlassian MCP server is unreachable or unauthenticated

**Properties:**

- `code` (string) (values: ["CONNECTION_FAILED"]) - 
- `message` (string) - 
- `details` (string) - 

### LinkTypeUnavailableError

The requested link type is not defined in this Jira instance and onTypeUnavailable = fail

**Properties:**

- `code` (string) (values: ["LINK_TYPE_UNAVAILABLE"]) - 
- `message` (string) - 
- `availableTypes` (array) - 

### PermissionError

The user lacks the Link Issues permission on the project

**Properties:**

- `code` (string) (values: ["PERMISSION_DENIED"]) - 
- `message` (string) - 

## Prompt Content

# Link Jira Issues

Create directional links between existing Jira issues — `Blocks`, `Relates`, `Duplicate`, `Clones`.

Use this for **dependency and blocking relationships**. The parent Epic relationship is not an issue link — it is the `parentKey` input on `@./.cursor\skills\create-jira-issues\SKILL.md` / `@./.cursor\skills\update-jira-issues\SKILL.md`.

## Parameters

- **{{links}}** (array, required): The links to create. Each entry is `{ inwardIssue, outwardIssue, type?, comment? }`. Pass an array of one to create a single link.
- **{{type}}** (string, optional): Default link type for entries that omit their own. Defaults to `Blocks`. Matched case-insensitively against the types the instance defines, including their inward/outward descriptions.
- **{{comment}}** (string, optional): Default comment for entries that omit one. Posted on the **outward** issue.
- **{{onTypeUnavailable}}** (string, optional): `skip` (default) or `fail`. What to do when the instance does not define the requested link type. `skip` returns success with every link reported as skipped, so a caller's wider workflow is not blocked by a project-configuration gap.
- **{{dryRun}}** (boolean, optional): Resolve and report the planned links without creating any.

## Direction

For directional types, **`inwardIssue` is the blocker and `outwardIssue` is the blocked issue** — read it as the sentence *inward* **blocks** *outward*.

Translating from a dependency graph: for an edge where `dependent` needs `predecessor`, pass `inwardIssue = predecessor`, `outwardIssue = dependent`.

So "AIP-20 is blocked by AIP-10" is `inwardIssue: AIP-10, outwardIssue: AIP-20`. Getting this backwards produces a link that tells the team to do the work in the wrong order, so confirm one link as a sentence before running a batch.

## Instructions

Load `@./.cursor\skills\link-jira-issues\SKILL.md` and execute it with these inputs.

| Skill input | Value |
|---|---|
| `links` | `{{links}}` |
| `type` | `{{type}}` (default `Blocks`) |
| `comment` | `{{comment}}` (only if provided) |
| `onTypeUnavailable` | `{{onTypeUnavailable}}` (default `skip`) |
| `dryRun` | `{{dryRun}}` (default `false`) |

The skill validates the MCP connection, resolves the requested type against the types the instance actually defines, reads existing links on each inward issue so already-correct links are skipped and re-runs are safe, creates only the missing links one at a time, and reports created / skipped / conflicting / failed links.

Return the skill's response unchanged.

## Response Format

### Success Response

```json
{
  "success": true,
  "resolvedType": "Blocks",
  "created": [{ "inwardIssue": "AIP-10", "outwardIssue": "AIP-20", "type": "Blocks" }],
  "skipped": [{ "inwardIssue": "AIP-10", "outwardIssue": "AIP-21", "type": "Blocks", "reason": "ALREADY_LINKED" }],
  "conflicts": [],
  "failed": [],
  "availableTypes": ["Blocks", "Clones", "Duplicate", "Relates"]
}
```

`success` is `true` whenever the pass completed — including when every link was skipped because it already existed or the type is unavailable. It is `false` only when nothing could be attempted. A reversed existing link comes back in `conflicts` with both directions named rather than being overwritten.

## Error Handling

Errors are surfaced as returned by the `link-jira-issues` skill:

- `ConnectionError` (`CONNECTION_FAILED`) — Atlassian MCP server unreachable or unauthenticated
- `LinkTypeUnavailableError` (`LINK_TYPE_UNAVAILABLE`) — requested type not defined and `onTypeUnavailable = fail`; includes `availableTypes`
- `IssueNotFoundError` (`ISSUE_NOT_FOUND`) — per-link; an issue key did not resolve
- `PermissionError` (`PERMISSION_DENIED`) — the user lacks the Link Issues permission on the project

```json
{ "code": "CONNECTION_FAILED", "message": "Unable to connect to Atlassian MCP server", "details": "..." }
```

