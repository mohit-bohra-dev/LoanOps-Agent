---
promp:
  package: "story"
  version: "1.6.0"
  environment: "development"
  prompVersion: "1.0.1-beta.161"
  prompt: "assignStory"
---
# story.assignStory

Check a story's Jira assignment and, per policy, ensure it is assigned — assigning to the current user when unassigned and surfacing a conflict before reassigning a story held by someone else. Checks assignment in addition to state

## Parameter Specifications

- **`issueKey`** (string) - *Optional*
  - The Jira issue key (e.g. 'PAY-512')

- **`storyPath`** (string) - *Optional*
  - Path to the local [name].story.md; used to resolve a recorded issue key when issueKey is not given

- **`assignee`** (string) - *Optional*
  - The desired assignee — a Jira account id, 'me' for the current MCP-authenticated user, or 'unassigned' to clear
  - Default: `me`

- **`policy`** (string) - *Optional*
  - verify (read-only) | ensure-assigned (assign if unassigned, confirm before reassigning someone else's) | assign (set, confirming a conflict first)
  - Default: `ensure-assigned`

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
   - Parameter 1: `issueKey` (optional) - The Jira issue key (e.g. 'PAY-512')
   - Parameter 2: `storyPath` (optional) - Path to the local [name].story.md; used to resolve a recorded issue key when issueKey is not given
   - Parameter 3: `assignee` (optional) [default: me] - The desired assignee — a Jira account id, 'me' for the current MCP-authenticated user, or 'unassigned' to clear
   - Parameter 4: `policy` (optional) [default: ensure-assigned] - verify (read-only) | ensure-assigned (assign if unassigned, confirm before reassigning someone else's) | assign (set, confirming a conflict first)

2. **Replace parameter placeholders** in the prompt content below:
   - Parameters use the format `{{parameterName}}` in the prompt
   - Replace each placeholder with the corresponding parsed value
   - If a parameter is optional and not provided, use its default value (if specified)
   - If a required parameter is missing, ask the user to provide it

3. **Execute the prompt** with the replaced parameters

## Usage

When the user invokes this command, they may provide parameters in various ways:
- Space-separated values: `/story.assignStory value1 value2`
- Named parameters: `/story.assignStory param1=value1 param2=value2`
- Mixed format: `/story.assignStory value1 param2=value2`

Parse flexibly and map values to the expected parameters in order for positional arguments.

## Expected Output

Result of the assignment check

**Type:** `object`

**Properties:**

- `success` (boolean) - **Required** - 
- `issueKey` (string) - **Required** - 
- `assigned` (boolean) - **Required** - 
- `assignee` (string,null) - *Optional* - 
- `changed` (boolean) - *Optional* - 
- `conflict` (unknown) - *Optional* - 
## Error Handling

### NoIssueKeyError

No issue key was provided or recorded on the story

**Properties:**

- `code` (string) (values: ["NO_ISSUE_KEY"]) - 
- `message` (string) - 
- `storyPath` (string) - 

### ConnectionError



**Properties:**

- `code` (string) (values: ["CONNECTION_FAILED"]) - 
- `message` (string) - 

### IssueNotFoundError



**Properties:**

- `code` (string) (values: ["ISSUE_NOT_FOUND"]) - 
- `message` (string) - 
- `issueKey` (string) - 

## Prompt Content

# Assign Story

Check a story's Jira **assignment** and, per policy, ensure it is assigned — surfacing a conflict before reassigning a story held by someone else.

## Parameters

- **{{issueKey}}** (string, optional): The Jira issue key (e.g. `PAY-512`).
- **{{storyPath}}** (string, optional): Path to the local `[name].story.md`; used to resolve a recorded issue key when `issueKey` is not given.
- **{{assignee}}** (string, optional): The desired assignee — a Jira account id, or the token `me` for the current MCP-authenticated user, or `unassigned` to clear. Default `me`.
- **{{policy}}** (string, optional): `verify` | `ensure-assigned` | `assign`. Default `ensure-assigned`. See the skill's policy table.

One of `issueKey` or a `storyPath` with a recorded key is required.

## Instructions

Load **@./.cursor\skills\story-story-jira-lifecycle\SKILL.md** and execute its Invocation Contract with `operation: assign` and these inputs:

| Parameter | Skill input |
|---|---|
| — | `operation` = `assign` |
| `{{issueKey}}` | `issueKey` |
| `{{storyPath}}` | `storyPath` |
| `{{assignee}}` | `assignee` |
| `{{policy}}` | `policy` |

The skill owns issue-key resolution, the assignment policies (`references/assignment-policy.md`), current-user resolution, conflict surfacing, and the error catalogue. It loads **@./.cursor\skills\story-story-source-model\SKILL.md** when resolving a key from a file, reads the current assignee through **@./.cursor\skills\jira-retrieve-jira\SKILL.md**, and sets it through **@./.cursor\skills\jira-update-jira-issues\SKILL.md** (`profileName: Story`, `assignee`).

## Response Format

```json
{
  "success": true,
  "issueKey": "PAY-512",
  "assigned": true,
  "assignee": "me",
  "changed": true,
  "conflict": null
}
```

**Field descriptions:**

- `success`: Whether the check completed.
- `issueKey`: The issue checked.
- `assigned`: Whether the story has any assignee after the check.
- `assignee`: The resulting assignee (account id or display label), or `null` when unassigned.
- `changed`: Whether this run mutated the assignee.
- `conflict`: Present when the story was assigned to someone else — records the prior assignee and the resolution (`confirmed-reassign` / `skipped`); `null` otherwise.

## Error Handling

Return the error and stop. See `story-jira-lifecycle` (Invocation Contract → Errors) for the full detail and recovery.

- **NoIssueKeyError** (`NO_ISSUE_KEY`) — no issue key was provided or recorded; run `syncStoryToJira` first to create and link an issue.
- **ConnectionError** (`CONNECTION_FAILED`), **IssueNotFoundError** (`ISSUE_NOT_FOUND`), **UpdateError** (`UPDATE_FAILED`) — relayed from jira verbatim.

## Notes

- **Assignment is checked in addition to state.** A coordinator typically runs `assignStory` and `transitionStory` together at the start of a run — both are tracker-lifecycle concerns but independent operations.
- **Never reassign silently.** A story held by someone else is surfaced and confirmed before reassigning.
- **`me` is resolved by jira.** Pass `assignee="me"` through; jira resolves it to the caller's account id. Arbitrary display names need an account id.

