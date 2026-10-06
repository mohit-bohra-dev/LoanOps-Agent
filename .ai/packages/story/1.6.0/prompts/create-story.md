# Create Story

Author a new `[name].story.md` — the WHAT/WHY of a unit of work — from a feature description, and optionally offer a first Jira sync.

## Parameters

- **{{name}}** (string, optional): Kebab-case name for the unit of work (e.g. `payment-retries`). Names the `[name].story.md` file. If not provided, ask the user.
- **{{description}}** (string, optional): One-line description of what the feature does and the problem it solves. If not provided, ask the user.
- **{{storyPath}}** (string, optional): Where to write the story file. May be a directory (the file is created as `<dir>/[name].story.md`) or a full file path. Defaults to `./[name].story.md`.
- **{{parentEpic}}** (string, optional): Parent epic to link the story under — a local `[name].epic.md` path **or** an epic Jira issue key. Recorded in the story and applied on first Jira sync.
- **{{template}}** (string, optional): Path to a template file **or** an inline section-contract that overrides the package's default `story.md.template`. Lets a caller (e.g. `nexus`) supply its own story format while reusing this package's authoring + sync. When omitted, the package default is used.
- **{{offerSync}}** (boolean, optional): Whether to offer a first Jira sync after authoring. Default `true`. Offered as an option — never run automatically.

## Instructions

Load **{{skill:story-authoring}}** and execute its Invocation Contract with `mode: create` and these inputs:

| Parameter | Skill input |
|---|---|
| — | `mode` = `create` |
| `{{name}}` | `name` |
| `{{description}}` | `description` |
| `{{storyPath}}` | `storyPath` |
| `{{parentEpic}}` | `parentEpic` |
| `{{template}}` | `template` |
| `{{offerSync}}` | `offerSync` |

The skill owns the authoring standards, the numbered procedure, and the error catalogue. It loads **{{skill:story-source-model}}** for path resolution and naming, **{{skill:story-epic-linking}}** when `{{parentEpic}}` is given, and offers **{{skill:story-jira-sync}}** for the first sync.

## Response Format

```json
{
  "success": true,
  "name": "payment-retries",
  "storyPath": "./payment-retries.story.md",
  "filesCreated": ["./payment-retries.story.md"]
}
```

**Field descriptions:**

- `success` (boolean): Whether the story was created.
- `name` (string): The kebab-case name.
- `storyPath` (string): Path to the created story file.
- `filesCreated` (array of string): Paths of the files created.

## Error Handling

Return the error and stop. See `story-authoring` (Invocation Contract → Errors) for the full detail and recovery.

- **InvalidNameError** (`INVALID_NAME`) — `{{name}}` is not kebab-case; carries `providedName`.
- **StoryExistsError** (`STORY_EXISTS`) — a story already exists at the resolved path; carries `storyPath`. Use `reviseStory` to edit it.

## Notes

- **Story is WHAT/WHY only.** Technical design belongs elsewhere; keep this file technology-agnostic per `story-authoring`.
- **Format is pluggable.** A caller can supply its own story format via `template`; the authoring judgment in `story-authoring` still applies.
- **Parent epic is recorded, pushed on sync.** When `parentEpic` is given it is recorded locally now and applied to Jira on the first sync. Use `linkStoryToEpic` to set/verify/clear the parent later.
- **Sync is offered, never automatic.** A first sync records the issue key back into the story so future syncs update instead of re-creating.
