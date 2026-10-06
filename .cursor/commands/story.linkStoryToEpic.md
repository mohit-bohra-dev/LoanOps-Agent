---
promp:
  package: "story"
  version: "1.6.0"
  environment: "development"
  prompVersion: "1.0.1-beta.161"
  prompt: "linkStoryToEpic"
---
# story.linkStoryToEpic

Set, verify, or clear a story's parent epic — recording it in the local [name].story.md and pushing the Epic Link / parent to the story's Jira issue. The desired parent may be a local [name].epic.md path or an epic Jira issue key (auto-detected); surfaces a conflict before re-parenting a story already under a different epic

## Parameter Specifications

- **`storyPath`** (string) - *Optional*
  - Path to the local [name].story.md to link; used to record the parent locally and resolve a recorded story issue key

- **`issueKey`** (string) - *Optional*
  - The story's Jira issue key (e.g. 'PAY-512'); when omitted, resolved from storyPath

- **`parentEpic`** (string) - *Optional*
  - The desired parent epic — a local [name].epic.md path OR an epic Jira issue key, or 'none' to clear. Required unless policy=verify

- **`policy`** (string) - *Optional*
  - verify (read-only) | ensure-linked (link if unparented, confirm before re-parenting a different epic) | link (set, confirming a conflict first)
  - Default: `ensure-linked`

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
   - Parameter 1: `storyPath` (optional) - Path to the local [name].story.md to link; used to record the parent locally and resolve a recorded story issue key
   - Parameter 2: `issueKey` (optional) - The story's Jira issue key (e.g. 'PAY-512'); when omitted, resolved from storyPath
   - Parameter 3: `parentEpic` (optional) - The desired parent epic — a local [name].epic.md path OR an epic Jira issue key, or 'none' to clear. Required unless policy=verify
   - Parameter 4: `policy` (optional) [default: ensure-linked] - verify (read-only) | ensure-linked (link if unparented, confirm before re-parenting a different epic) | link (set, confirming a conflict first)

2. **Replace parameter placeholders** in the prompt content below:
   - Parameters use the format `{{parameterName}}` in the prompt
   - Replace each placeholder with the corresponding parsed value
   - If a parameter is optional and not provided, use its default value (if specified)
   - If a required parameter is missing, ask the user to provide it

3. **Execute the prompt** with the replaced parameters

## Usage

When the user invokes this command, they may provide parameters in various ways:
- Space-separated values: `/story.linkStoryToEpic value1 value2`
- Named parameters: `/story.linkStoryToEpic param1=value1 param2=value2`
- Mixed format: `/story.linkStoryToEpic value1 param2=value2`

Parse flexibly and map values to the expected parameters in order for positional arguments.

## Expected Output

Result of the link operation

**Type:** `object`

**Properties:**

- `success` (boolean) - **Required** - 
- `storyPath` (string) - *Optional* - 
- `issueKey` (string,null) - *Optional* - 
- `parentEpicKey` (string,null) - *Optional* - 
- `linked` (boolean) - **Required** - 
- `changed` (boolean) - *Optional* - 
- `pushedToJira` (boolean) - *Optional* - 
- `conflict` (unknown) - *Optional* - 
## Error Handling

### NoIssueKeyError

A Jira push was required but no story issue key resolved and the link could not be recorded locally

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

# Link Story to Epic

Set, verify, or clear a story's parent **epic** — recording it locally and pushing the Epic Link / parent to Jira.

## Parameters

- **{{storyPath}}** (string, optional): Path to the local `[name].story.md` to link. Used to record the parent locally and to resolve a recorded story issue key.
- **{{issueKey}}** (string, optional): The story's Jira issue key (e.g. `PAY-512`). When omitted, resolved from `{{storyPath}}` per `story-source-model`.
- **{{parentEpic}}** (string, optional): The desired parent epic — a local `[name].epic.md` path **or** an epic Jira issue key, or `none` to clear. Required unless `policy=verify`.
- **{{policy}}** (string, optional): `verify` | `ensure-linked` | `link`. Default `ensure-linked`. See the skill's policy table.

One of `storyPath` or `issueKey` is required (to push to Jira a recorded story issue key must resolve; without one, the link is recorded locally only).

## Instructions

Load **@./.cursor\skills\story-story-epic-linking\SKILL.md** and execute its Invocation Contract with these inputs:

| Parameter | Skill input |
|---|---|
| `{{storyPath}}` | `storyPath` |
| `{{issueKey}}` | `issueKey` |
| `{{parentEpic}}` | `parentEpic` |
| `{{policy}}` | `policy` |

The skill owns parent-epic source detection, epic-file→issue-key resolution, the link policies, conflict surfacing, and the error catalogue. It loads **@./.cursor\skills\story-story-source-model\SKILL.md** when resolving keys from files, and pushes through **@./.cursor\skills\jira-update-jira-issues\SKILL.md** (`profileName: Story`, `parentKey`).

## Response Format

```json
{
  "success": true,
  "storyPath": "./payment-retries.story.md",
  "issueKey": "PAY-512",
  "parentEpicKey": "AIP-100",
  "linked": true,
  "changed": true,
  "pushedToJira": true,
  "conflict": null
}
```

**Field descriptions:**

- `success`: Whether the operation completed.
- `storyPath` / `issueKey`: The story acted on.
- `parentEpicKey`: The resulting parent epic issue key, or `null` when unparented / unresolved.
- `linked`: Whether the story has a parent epic after the operation.
- `changed`: Whether this run mutated the parent (locally and/or in Jira).
- `pushedToJira`: Whether the parent was pushed to Jira (false when only recorded locally because the story or epic has no issue yet).
- `conflict`: Present when the story was under a different epic — records the prior parent and resolution (`confirmed-reparent` / `skipped`); `null` otherwise.

## Error Handling

Return the error and stop. See `story-epic-linking` (Invocation Contract → Errors) for the full detail and recovery.

- **NoIssueKeyError** (`NO_ISSUE_KEY`) — a Jira push was required but no story issue key resolved and the link could not be recorded locally either.
- **ConnectionError** (`CONNECTION_FAILED`), **IssueNotFoundError** (`ISSUE_NOT_FOUND`), **UpdateError** (`UPDATE_FAILED`) — relayed from jira verbatim.

An epic that has not been synced is **not** an error — the link is recorded locally and `pushedToJira` returns `false`.

## Notes

- **Parent epic may be a file or a key.** A local `[name].epic.md` is resolved to its Jira issue key before pushing; an epic that has not been synced records the link locally until the epic has a Jira issue.
- **Never re-parent silently.** A story under a different epic is surfaced and confirmed before re-parenting.
- **Linking lives in the story layer.** The epic package never sets parents on its children; this prompt is the single **parent** linking entry point.
- **Parent is not dependency.** This prompt only sets the Epic Link / parent relationship. Story-to-story dependency links ("blocked by a sibling story") are a different Jira mechanism — an issue link, not hierarchy — and belong to `linkStoryDependencies`. Never model a dependency as a parent: it would move the story out of its epic.

