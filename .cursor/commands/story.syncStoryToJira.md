---
promp:
  package: "story"
  version: "1.6.0"
  environment: "development"
  prompVersion: "1.0.1-beta.161"
  prompt: "syncStoryToJira"
---
# story.syncStoryToJira

Delta-sync a story to its Jira issue — create on first sync, push only the changed fields (summary, description, acceptance criteria) on every sync after; surfaces Jira-side conflicts before overwriting

## Parameter Specifications

- **`storySource`** (string) - *Optional*
  - The sync target — a story file path OR a Jira issue key (auto-detected). When an issue key, the existing issue is updated, never re-created

- **`storyPath`** (string) - *Optional*
  - Explicit path to the local [name].story.md when storySource is an issue key or omitted

- **`projectKey`** (string) - *Optional*
  - Target Jira project for a first-sync create. When omitted, the jira config's default project is used

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
   - Parameter 1: `storySource` (optional) - The sync target — a story file path OR a Jira issue key (auto-detected). When an issue key, the existing issue is updated, never re-created
   - Parameter 2: `storyPath` (optional) - Explicit path to the local [name].story.md when storySource is an issue key or omitted
   - Parameter 3: `projectKey` (optional) - Target Jira project for a first-sync create. When omitted, the jira config's default project is used

2. **Replace parameter placeholders** in the prompt content below:
   - Parameters use the format `{{parameterName}}` in the prompt
   - Replace each placeholder with the corresponding parsed value
   - If a parameter is optional and not provided, use its default value (if specified)
   - If a required parameter is missing, ask the user to provide it

3. **Execute the prompt** with the replaced parameters

## Usage

When the user invokes this command, they may provide parameters in various ways:
- Space-separated values: `/story.syncStoryToJira value1 value2`
- Named parameters: `/story.syncStoryToJira param1=value1 param2=value2`
- Mixed format: `/story.syncStoryToJira value1 param2=value2`

Parse flexibly and map values to the expected parameters in order for positional arguments.

## Expected Output

Result of syncing the story to Jira

**Type:** `object`

**Properties:**

- `success` (boolean) - **Required** - 
- `storyPath` (string) - *Optional* - 
- `issueKey` (string) - **Required** - 
- `fieldsChanged` (array) - **Required** - 
- `conflictReport` (unknown) - *Optional* - 
## Error Handling

### StoryNotFoundError

The story file cannot be located

**Properties:**

- `code` (string) (values: ["STORY_NOT_FOUND"]) - 
- `message` (string) - 
- `storyPath` (string) - 

### ConnectionError

Surfaced from the jira skills when the Atlassian MCP server is not connected or authenticated

**Properties:**

- `code` (string) (values: ["CONNECTION_FAILED"]) - 
- `message` (string) - 

### IssueNotFoundError

Surfaced from the jira skills when the issue key does not exist

**Properties:**

- `code` (string) (values: ["ISSUE_NOT_FOUND"]) - 
- `message` (string) - 
- `issueKey` (string) - 

## Prompt Content

# Sync Story to Jira

Delta-sync a `[name].story.md` to its Jira issue — create on first sync, push only the changed fields on every sync after.

## Parameters

- **{{storySource}}** (string, optional): The sync target — **either** a story file path **or** a Jira issue key. Auto-detected by shape per `story-source-model`. When it is an issue key, the existing issue is **updated**, never re-created.
  - Examples: `PAY-512`, `./payment-retries.story.md`
- **{{storyPath}}** (string, optional): Explicit path to the local `[name].story.md` when `storySource` is an issue key or omitted. Used to locate the content to diff.
- **{{projectKey}}** (string, optional): Target Jira project for a first-sync create. When omitted, the jira config's default project is used.

At least one of `storySource` or `storyPath` is needed to locate the story. If neither resolves to readable content, ask the user before proceeding.

## Instructions

Load **@./.cursor\skills\story-story-jira-sync\SKILL.md** and execute its Invocation Contract with these inputs:

| Parameter | Skill input |
|---|---|
| `{{storySource}}` | `storySource` |
| `{{storyPath}}` | `storyPath` |
| `{{projectKey}}` | `projectKey` |

The skill owns the delta-sync method (get → diff → push), the field mapping, the acceptance-criteria merge mode, conflict surfacing, config remediation, and the error catalogue. It loads **@./.cursor\skills\story-story-source-model\SKILL.md** for source detection and recording the issue key, and **@./.cursor\skills\story-story-epic-linking\SKILL.md** to ride a recorded parent epic along on the create/update call.

Every Atlassian operation happens inside the jira package's skills (`@./.cursor\skills\jira-retrieve-jira\SKILL.md`, `@./.cursor\skills\jira-create-jira-issues\SKILL.md` / `@./.cursor\skills\jira-update-jira-issues\SKILL.md` with `profileName: Story`). Neither this prompt nor the story layer talks to Atlassian directly.

## Response Format

```json
{
  "success": true,
  "storyPath": "./payment-retries.story.md",
  "issueKey": "PAY-512",
  "fieldsChanged": ["summary", "acceptanceCriteria"],
  "conflictReport": null
}
```

**Field descriptions:**

- `success`: Whether the sync completed (including a clean no-op when nothing changed).
- `storyPath`: The local story that was synced.
- `issueKey`: The created or updated Jira issue key.
- `fieldsChanged`: The fields actually pushed (`summary`, `description`, `acceptanceCriteria`). Empty when the story already matched Jira.
- `conflictReport`: An object describing surfaced divergences and their resolution, or `null` when there were no conflicts.

## Error Handling

Return the error and stop. See `story-jira-sync` (Invocation Contract → Errors) for the full detail and recovery.

- **StoryNotFoundError** (`STORY_NOT_FOUND`) — the story file cannot be located; carries `storyPath`. No jira call is made.
- **ConnectionError** (`CONNECTION_FAILED`) — relayed from jira; the Atlassian MCP is not connected or authenticated.
- **IssueNotFoundError** (`ISSUE_NOT_FOUND`) — relayed from jira; the issue key does not exist.
- **ConfigInvalidError** (`CONFIG_INVALID`), **ProjectNotInConfigError** (`PROJECT_NOT_IN_CONFIG`), **DefaultProjectKeyMissingError** (`DEFAULT_PROJECT_KEY_MISSING`) — relayed from jira; point the user at `@./.cursor\skills\jira-configure-jira\SKILL.md` or `@./.cursor\skills\jira-verify-jira-config\SKILL.md`.

## Notes

- **Story is truth, Jira is transport.** Push, don't pull — the one exception is conflict surfacing.
- **Lifecycle is separate.** Status transitions, assignment, and the estimate are handled by `transitionStory`, `assignStory`, and `pointStory`, not this prompt.
- **Parent epic rides along.** A recorded parent epic is pushed via `parentKey` on create/update; setting or clearing the parent on its own is `linkStoryToEpic`.

