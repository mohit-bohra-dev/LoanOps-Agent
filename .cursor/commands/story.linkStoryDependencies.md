---
promp:
  package: "story"
  version: "1.6.0"
  environment: "development"
  prompVersion: "1.0.1-beta.161"
  prompt: "linkStoryDependencies"
---
# story.linkStoryDependencies

Push story-to-story dependency relationships to Jira as native issue links (Blocks / is blocked by). Complements linkStoryToEpic, which owns the orthogonal parent-epic dimension (parentKey / Epic Link) — a dependency is a sideways link between peers, a parent is hierarchy, and the two must not be conflated. Resolves each story to its Jira issue key, orients each edge (dependsOn is the blocker, story is the blocked issue), and delegates every Atlassian operation to {{skill:jira.link-jira-issues}}, which discovers the link type and stays idempotent. Stories without a Jira issue are reported as unresolved rather than failing the batch.

## Parameter Specifications

- **`dependencies`** (array) - **Required**
  - Dependency edges to push. Each entry is { story, dependsOn }, where both values are a local [name].story.md path OR a story Jira issue key (auto-detected). dependsOn may be an array when a story has several predecessors. Direction: dependsOn is the blocker (inwardIssue), story is the blocked issue (outwardIssue).

- **`comment`** (string) - *Optional*
  - Comment to post on each blocked issue when the link is created — e.g. a pointer back to the epic's dependency table

- **`onTypeUnavailable`** (string) - *Optional*
  - Passed through to jira.linkIssues for the case where the project defines no Blocks link type: 'skip' reports the links as skipped without failing, 'fail' raises LINK_TYPE_UNAVAILABLE
  - Default: `skip`

- **`dryRun`** (boolean) - *Optional*
  - Resolve and report the planned links without creating any

## Instructions

You are executing a Promp package prompt. Follow these steps:

0. **Resolve package location (required first tool call):** Run this shell command before any other tool and use the returned `packageDir` as the package root for every artifact path in this file:

```bash
promp ensure-package story --json --project-path "D:\Users\v-mbohra\Documents\Projects\LoanOps-Agent"
```

- `packageDir` is the extracted package directory. Use it for every skill, prompt, or template path below.
- If `success` is `false` and no `packageDir` is returned, the package could not be found or installed. Run `promp install story` or `promp install -g story` and retry.
- Do **not** search other workspace roots for package files — always use the path returned by this command.

1. **Parse the user input** to extract parameters:
   - Parameter 1: `dependencies` (required) - Dependency edges to push. Each entry is { story, dependsOn }, where both values are a local [name].story.md path OR a story Jira issue key (auto-detected). dependsOn may be an array when a story has several predecessors. Direction: dependsOn is the blocker (inwardIssue), story is the blocked issue (outwardIssue).
   - Parameter 2: `comment` (optional) - Comment to post on each blocked issue when the link is created — e.g. a pointer back to the epic's dependency table
   - Parameter 3: `onTypeUnavailable` (optional) [default: skip] - Passed through to jira.linkIssues for the case where the project defines no Blocks link type: 'skip' reports the links as skipped without failing, 'fail' raises LINK_TYPE_UNAVAILABLE
   - Parameter 4: `dryRun` (optional) - Resolve and report the planned links without creating any

2. **Replace parameter placeholders** in the prompt content below:
   - Parameters use the format `{{parameterName}}` in the prompt
   - Replace each placeholder with the corresponding parsed value
   - If a parameter is optional and not provided, use its default value (if specified)
   - If a required parameter is missing, ask the user to provide it

3. **Execute the prompt** with the replaced parameters

## Usage

When the user invokes this command, they may provide parameters in various ways:
- Space-separated values: `/story.linkStoryDependencies value1 value2`
- Named parameters: `/story.linkStoryDependencies param1=value1 param2=value2`
- Mixed format: `/story.linkStoryDependencies value1 param2=value2`

Parse flexibly and map values to the expected parameters in order for positional arguments.

## Expected Output

Result of the dependency-linking pass

**Type:** `object`

**Properties:**

- `success` (boolean) - **Required** - True when the pass completed, including when every link was already present or some stories were unresolved
- `linksCreated` (array) - **Required** - 
- `linksSkipped` (array) - **Required** - Edges already correct (ALREADY_LINKED) or skipped for an unavailable link type (TYPE_UNAVAILABLE)
- `conflicts` (array) - *Optional* - Pairs where the reverse link already exists — reported, never overwritten
- `unresolved` (array) - *Optional* - Stories with no Jira issue yet, and the edges dropped because of them
- `failed` (array) - *Optional* - 
## Error Handling

### NoIssueKeyError

No story in the batch resolved to a Jira issue key, so there was nothing to link

**Properties:**

- `code` (string) (values: ["NO_ISSUE_KEY"]) - 
- `message` (string) - 
- `stories` (array) - 

### ConnectionError



**Properties:**

- `code` (string) (values: ["CONNECTION_FAILED"]) - 
- `message` (string) - 

### LinkTypeUnavailableError

Relayed from jira.linkIssues when the project defines no Blocks link type and onTypeUnavailable = fail

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

# Link Story Dependencies

Push story-to-story **dependency** relationships to Jira as native issue links (`Blocks` / `is blocked by`).

## Parameters

- **{{dependencies}}** (array, required): The dependency edges to push. Each entry is `{ story, dependsOn }`, where both values are a local `[name].story.md` path **or** a story Jira issue key (auto-detected per `story-source-model`). `dependsOn` may be an array when a story has several predecessors. Direction: `dependsOn` is the blocker, `story` is the blocked issue.
- **{{comment}}** (string, optional): Comment to post on each blocked issue when the link is created — for example a pointer back to the epic's dependency table.
- **{{onTypeUnavailable}}** (string, optional): `skip` (default) or `fail`, for the case where the project defines no `Blocks` link type.
- **{{dryRun}}** (boolean, optional): Resolve and report the planned links without creating any.

## Instructions

Load **@./.cursor\skills\story-story-dependency-linking\SKILL.md** and execute its Invocation Contract with these inputs:

| Parameter | Skill input |
|---|---|
| `{{dependencies}}` | `dependencies` |
| `{{comment}}` | `comment` |
| `{{onTypeUnavailable}}` | `onTypeUnavailable` |
| `{{dryRun}}` | `dryRun` |

The skill owns the direction rule (`dependsOn` blocks `story`), issue-key resolution, edge orientation, self-edge and unresolved-story handling, batching, and the error catalogue. It loads **@./.cursor\skills\story-story-source-model\SKILL.md** for story-path → issue-key resolution, and delegates every Atlassian operation to **@./.cursor\skills\jira-link-jira-issues\SKILL.md**, which discovers the link type and stays idempotent.

Dependencies are **not** parents. This prompt never touches `parentKey`; the parent-epic dimension belongs to `linkStoryToEpic`.

## Response Format

```json
{
  "success": true,
  "linksCreated": [
    { "story": "AIP-521", "dependsOn": "AIP-520", "type": "Blocks" }
  ],
  "linksSkipped": [
    { "story": "AIP-522", "dependsOn": "AIP-520", "reason": "ALREADY_LINKED" }
  ],
  "conflicts": [],
  "unresolved": [
    { "story": "./publish-metrics.story.md", "reason": "NO_ISSUE_KEY" }
  ],
  "failed": []
}
```

**Field descriptions:**

- `success`: Whether the pass completed. `true` even when every link was already present or some stories were unresolved; `false` only when nothing could be attempted.
- `linksCreated`: Edges newly linked in Jira.
- `linksSkipped`: Edges already correct (`ALREADY_LINKED`) or skipped because the project defines no `Blocks` type (`TYPE_UNAVAILABLE`).
- `conflicts`: Pairs where the reverse link already exists — reported, never overwritten.
- `unresolved`: Stories with no Jira issue yet, and the edges dropped because of them.
- `failed`: Per-edge failures with their codes.

## Error Handling

Return the error and stop. See `story-dependency-linking` (Invocation Contract → Errors) for the full detail and recovery.

- **NoIssueKeyError** (`NO_ISSUE_KEY`) — **no** story in the batch has a Jira issue, so there is nothing to link; carries the offending `stories`. Sync those stories first.
- **ConnectionError** (`CONNECTION_FAILED`), **LinkTypeUnavailableError** (`LINK_TYPE_UNAVAILABLE`), **IssueNotFoundError** (`ISSUE_NOT_FOUND`), **PermissionError** (`PERMISSION_DENIED`) — relayed from jira verbatim.

A partially unresolved batch is **not** an error — it returns `success: true` with the dropped edges in `unresolved`.

## Notes

- **Dependencies are links, parents are not.** Keeping them separate is what keeps the epic hierarchy and the dependency graph from corrupting each other.
- **Idempotent.** Existing links are read before anything is created, so this can run on every sync without duplicating links.
- **Markdown stays the source of truth.** The dependency graph is authored in the planning artifacts; this prompt projects it onto Jira. It never reads Jira links back into the markdown.
- **Story-to-story only.** Dependencies that cross epics, or point at non-story work, are outside this prompt's scope — the caller decides whether such an edge belongs in Jira at all.

