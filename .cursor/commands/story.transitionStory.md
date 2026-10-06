---
promp:
  package: "story"
  version: "1.6.0"
  environment: "development"
  prompVersion: "1.0.1-beta.161"
  prompt: "transitionStory"
---
# story.transitionStory

Move a story's Jira issue to a target workflow status (its state), e.g. In Development at the start of work or In Review at completion. Status names are team-specific and opaque

## Parameter Specifications

- **`issueKey`** (string) - *Optional*
  - The Jira issue key to transition (e.g. 'PAY-512')

- **`storyPath`** (string) - *Optional*
  - Path to the local [name].story.md; used to resolve a recorded issue key when issueKey is not given

- **`status`** (string) - **Required**
  - The target status name (e.g. 'In Development', 'In Review', 'Done'). Passed through verbatim

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
   - Parameter 1: `issueKey` (optional) - The Jira issue key to transition (e.g. 'PAY-512')
   - Parameter 2: `storyPath` (optional) - Path to the local [name].story.md; used to resolve a recorded issue key when issueKey is not given
   - Parameter 3: `status` (required) - The target status name (e.g. 'In Development', 'In Review', 'Done'). Passed through verbatim

2. **Replace parameter placeholders** in the prompt content below:
   - Parameters use the format `{{parameterName}}` in the prompt
   - Replace each placeholder with the corresponding parsed value
   - If a parameter is optional and not provided, use its default value (if specified)
   - If a required parameter is missing, ask the user to provide it

3. **Execute the prompt** with the replaced parameters

## Usage

When the user invokes this command, they may provide parameters in various ways:
- Space-separated values: `/story.transitionStory value1 value2`
- Named parameters: `/story.transitionStory param1=value1 param2=value2`
- Mixed format: `/story.transitionStory value1 param2=value2`

Parse flexibly and map values to the expected parameters in order for positional arguments.

## Expected Output

Result of the transition

**Type:** `object`

**Properties:**

- `success` (boolean) - **Required** - 
- `issueKey` (string) - **Required** - 
- `status` (string) - **Required** - 
- `transitioned` (boolean) - *Optional* - 
## Error Handling

### NoIssueKeyError

No issue key was provided or recorded on the story

**Properties:**

- `code` (string) (values: ["NO_ISSUE_KEY"]) - 
- `message` (string) - 
- `storyPath` (string) - 

### TransitionError

Surfaced from jira when the requested status is not reachable from the issue's current status

**Properties:**

- `code` (string) (values: ["TRANSITION_FAILED"]) - 
- `message` (string) - 

### ConnectionError



**Properties:**

- `code` (string) (values: ["CONNECTION_FAILED"]) - 
- `message` (string) - 

## Prompt Content

# Transition Story

Move a story's Jira issue to a target workflow status (its **state**).

## Parameters

- **{{issueKey}}** (string, optional): The Jira issue key to transition (e.g. `PAY-512`).
- **{{storyPath}}** (string, optional): Path to the local `[name].story.md`; used to resolve a recorded issue key when `issueKey` is not given.
- **{{status}}** (string, required): The target status name (e.g. `In Development`, `In Review`, `Done`). Team-specific and opaque — passed through verbatim.

One of `issueKey` or a `storyPath` with a recorded key is required.

## Instructions

Load **@./.cursor\skills\story-story-jira-lifecycle\SKILL.md** and execute its Invocation Contract with `operation: transition` and these inputs:

| Parameter | Skill input |
|---|---|
| — | `operation` = `transition` |
| `{{issueKey}}` | `issueKey` |
| `{{storyPath}}` | `storyPath` |
| `{{status}}` | `status` |

The skill owns issue-key resolution, the transition call, the opaque-status-name rule, and the error catalogue. It loads **@./.cursor\skills\story-story-source-model\SKILL.md** when resolving a key from a file, and performs the transition through **@./.cursor\skills\jira-update-jira-issues\SKILL.md** (`profileName: Story`, `transition`).

## Response Format

```json
{
  "success": true,
  "issueKey": "PAY-512",
  "status": "In Development",
  "transitioned": true
}
```

**Field descriptions:**

- `success`: Whether the transition completed.
- `issueKey`: The transitioned issue.
- `status`: The target status requested.
- `transitioned`: Whether the status actually changed (false on a no-op when already in the target status).

## Error Handling

Return the error and stop. See `story-jira-lifecycle` (Invocation Contract → Errors) for the full detail and recovery.

- **NoIssueKeyError** (`NO_ISSUE_KEY`) — no issue key was provided or recorded; run `syncStoryToJira` first to create and link an issue.
- **TransitionError** (`TRANSITION_FAILED`) — relayed from jira; the requested status is not reachable from the current one. Report it and ask for the correct target — never guess.
- **ConnectionError** (`CONNECTION_FAILED`), **IssueNotFoundError** (`ISSUE_NOT_FOUND`) — relayed from jira verbatim.

## Notes

- **State only.** Assignment is handled by `assignStory`, the estimate by `pointStory`, and content by `syncStoryToJira`.
- **Status names are team-specific.** Treat `status` as opaque; never substitute a "canonical" name. On `TRANSITION_FAILED`, ask rather than guess.

