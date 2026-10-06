---
promp:
  package: "story"
  version: "1.6.0"
  environment: "development"
  prompVersion: "1.0.1-beta.161"
  prompt: "pointStory"
---
# story.pointStory

Check a story's Jira story-point estimate and, per policy, ensure it carries one — setting points when unpointed and surfacing a conflict before overwriting an estimate the team already recorded. Persists an estimate but never derives one (see nexus.estimateStory); checks the estimate in addition to state and assignment, because workflows commonly require Story Points before an issue may leave Backlog

## Parameter Specifications

- **`issueKey`** (string) - *Optional*
  - The Jira issue key (e.g. 'PAY-512')

- **`storyPath`** (string) - *Optional*
  - Path to the local [name].story.md; used to resolve a recorded issue key when issueKey is not given

- **`points`** (number) - *Optional*
  - The desired estimate. Required for ensure-pointed and set; ignored by verify. Passed through opaquely — the team's scale is not validated here

- **`policy`** (string) - *Optional*
  - verify (read-only) | ensure-pointed (set if unpointed, confirm before overwriting a different estimate) | set (force, confirming a conflict first)
  - Default: `ensure-pointed`

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
   - Parameter 3: `points` (optional) - The desired estimate. Required for ensure-pointed and set; ignored by verify. Passed through opaquely — the team's scale is not validated here
   - Parameter 4: `policy` (optional) [default: ensure-pointed] - verify (read-only) | ensure-pointed (set if unpointed, confirm before overwriting a different estimate) | set (force, confirming a conflict first)

2. **Replace parameter placeholders** in the prompt content below:
   - Parameters use the format `{{parameterName}}` in the prompt
   - Replace each placeholder with the corresponding parsed value
   - If a parameter is optional and not provided, use its default value (if specified)
   - If a required parameter is missing, ask the user to provide it

3. **Execute the prompt** with the replaced parameters

## Usage

When the user invokes this command, they may provide parameters in various ways:
- Space-separated values: `/story.pointStory value1 value2`
- Named parameters: `/story.pointStory param1=value1 param2=value2`
- Mixed format: `/story.pointStory value1 param2=value2`

Parse flexibly and map values to the expected parameters in order for positional arguments.

## Expected Output

Result of the pointing check

**Type:** `object`

**Properties:**

- `success` (boolean) - **Required** - 
- `issueKey` (string) - **Required** - 
- `pointed` (boolean) - **Required** - 
- `points` (number,null) - *Optional* - 
- `changed` (boolean) - *Optional* - 
- `conflict` (unknown) - *Optional* - 
## Error Handling

### NoIssueKeyError

No issue key was provided or recorded on the story

**Properties:**

- `code` (string) (values: ["NO_ISSUE_KEY"]) - 
- `message` (string) - 
- `storyPath` (string) - 

### MissingPointsError

A mutating policy was requested without a points value; this prompt never invents an estimate

**Properties:**

- `code` (string) (values: ["MISSING_POINTS"]) - 
- `message` (string) - 
- `policy` (string) - 

### FieldNotConfiguredError

The project has no Story Points field configured (fieldIds.storyPoints is null)

**Properties:**

- `code` (string) (values: ["FIELD_NOT_CONFIGURED"]) - 
- `message` (string) - 
- `projectKey` (string) - 

### ConnectionError



**Properties:**

- `code` (string) (values: ["CONNECTION_FAILED"]) - 
- `message` (string) - 

### IssueNotFoundError



**Properties:**

- `code` (string) (values: ["ISSUE_NOT_FOUND"]) - 
- `message` (string) - 
- `issueKey` (string) - 

### FieldValidationError

The issue type is not estimable (Sub-tasks carry no story points)

**Properties:**

- `code` (string) (values: ["FIELD_VALIDATION_FAILED"]) - 
- `message` (string) - 
- `field` (string) - 

## Prompt Content

# Point Story

Check a story's Jira **story-point estimate** and, per policy, ensure it carries one — surfacing a conflict before overwriting an estimate the team already set.

## Parameters

- **{{issueKey}}** (string, optional): The Jira issue key (e.g. `PAY-512`).
- **{{storyPath}}** (string, optional): Path to the local `[name].story.md`; used to resolve a recorded issue key when `issueKey` is not given.
- **{{points}}** (number, optional): The desired estimate. Required for `ensure-pointed` and `set`; ignored by `verify`.
- **{{policy}}** (string, optional): `verify` | `ensure-pointed` | `set`. Default `ensure-pointed`. See the skill's policy table.

One of `issueKey` or a `storyPath` with a recorded key is required.

## Instructions

Load **@./.cursor\skills\story-story-jira-lifecycle\SKILL.md** and execute its Invocation Contract with `operation: point` and these inputs:

| Parameter | Skill input |
|---|---|
| — | `operation` = `point` |
| `{{issueKey}}` | `issueKey` |
| `{{storyPath}}` | `storyPath` |
| `{{points}}` | `points` |
| `{{policy}}` | `policy` |

The skill owns issue-key resolution, the pointing policies (`references/pointing-policy.md`), conflict surfacing, the unconfigured-field path, and the error catalogue. It loads **@./.cursor\skills\story-story-source-model\SKILL.md** when resolving a key from a file, reads the current estimate through **@./.cursor\skills\jira-retrieve-jira\SKILL.md**, and sets it through **@./.cursor\skills\jira-update-jira-issues\SKILL.md** (`profileName: Story`, `storyPoints`).

**This prompt persists an estimate; it does not derive one.** Deciding the number is a judgment-bearing concern that belongs to the nexus `/nexus.estimateStory` command, exactly as deciding *who* should own a story sits outside `assignStory`.

## Response Format

```json
{
  "success": true,
  "issueKey": "PAY-512",
  "pointed": true,
  "points": 5,
  "changed": true,
  "conflict": null
}
```

**Field descriptions:**

- `success`: Whether the check completed.
- `issueKey`: The issue checked.
- `pointed`: Whether the story carries an estimate after the check.
- `points`: The resulting estimate, or `null` when unpointed.
- `changed`: Whether this run mutated the estimate.
- `conflict`: Present when the story already carried a different estimate — records the prior value and the resolution (`confirmed-repoint` / `skipped`); `null` otherwise.

## Error Handling

Return the error and stop. See `story-jira-lifecycle` (Invocation Contract → Errors) for the full detail and recovery.

- **NoIssueKeyError** (`NO_ISSUE_KEY`) — no issue key was provided or recorded; run `syncStoryToJira` first to create and link an issue.
- **MissingPointsError** (`MISSING_POINTS`) — a mutating policy was requested without `{{points}}`; this prompt never invents an estimate.
- **FieldNotConfiguredError** (`FIELD_NOT_CONFIGURED`) — the project has no Story Points field (`fieldIds.storyPoints` is `null`); re-run jira config discovery rather than guessing a field id.
- **ConnectionError** (`CONNECTION_FAILED`), **IssueNotFoundError** (`ISSUE_NOT_FOUND`), **UpdateError** (`UPDATE_FAILED`), **FieldValidationError** (`FIELD_VALIDATION_FAILED`, e.g. points on a Sub-task) — relayed from jira verbatim.

## Notes

- **Estimates are checked in addition to state and assignment.** A coordinator typically runs `assignStory`, `pointStory`, and `transitionStory` together — all tracker-lifecycle concerns, but independent operations.
- **Pointing has a one-way coupling to state.** When `transitionStory` fails with `TRANSITION_FAILED` and the message names Story Points, run `pointStory` and retry the transition; picking a different target status is not the fix.
- **Never re-point silently.** An existing estimate is a recorded team decision, usually from a planning session — overwriting it destroys that signal.
- **Sub-tasks are not estimable.** jira rejects `storyPoints` for the `Sub-task` profile; relay the error rather than retrying without the field.
- **The scale is the team's.** Fibonacci, linear, or t-shirt-mapped — the value is passed through opaquely and validated by Jira, not by this prompt.

