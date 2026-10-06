---
promp:
  package: "worktrees"
  version: "1.3.1"
  environment: "development"
  prompVersion: "1.0.1-beta.161"
  prompt: "switch"
---
# worktrees.switch

Switch the active workspace to a different git worktree. Inside Cursor, uses the cursor-app-control MCP to redirect the UI; outside Cursor, prints the cd command for manual use.

## Parameter Specifications

- **`name`** (string) - *Optional*
  - Name, path, or branch of the worktree to switch to. If omitted, lists available worktrees for selection.

## Instructions

You are executing a Promp package prompt. Follow these steps:

0. **Resolve package location (required first tool call):** Run this shell command before any other tool and use the returned `packageDir` as the package root for every artifact path in this file:

```bash
promp ensure-package worktrees --json --project-path "D:\Users\v-mbohra\Documents\Projects\LoanOps-Agent"
```

- `packageDir` is the extracted package directory. Use it for every skill, prompt, or template path below.
- If `success` is `false` and no `packageDir` is returned, the package could not be found or installed. Run `promp install worktrees` or `promp install -g worktrees` and retry.
- Do **not** search other workspace roots for package files — always use the path returned by this command.

1. **Parse the user input** to extract parameters:
   - Parameter 1: `name` (optional) - Name, path, or branch of the worktree to switch to. If omitted, lists available worktrees for selection.

2. **Replace parameter placeholders** in the prompt content below:
   - Parameters use the format `{{parameterName}}` in the prompt
   - Replace each placeholder with the corresponding parsed value
   - If a parameter is optional and not provided, use its default value (if specified)
   - If a required parameter is missing, ask the user to provide it

3. **Execute the prompt** with the replaced parameters

## Usage

When the user invokes this command, they may provide parameters in various ways:
- Space-separated values: `/worktrees.switch value1 value2`
- Named parameters: `/worktrees.switch param1=value1 param2=value2`
- Mixed format: `/worktrees.switch value1 param2=value2`

Parse flexibly and map values to the expected parameters in order for positional arguments.

## Expected Output

Details of the worktree switch operation

**Type:** `object`

**Properties:**

- `worktreePath` (string) - **Required** - Full absolute path to the worktree that is now active
- `worktreeName` (string) - **Required** - The directory name of the new active worktree
- `branch` (string) - **Required** - The branch checked out in the new active worktree
- `method` (string) - **Required** - How the switch was performed
- `previousPath` (string) - *Optional* - The workspace root path before the switch
## Error Handling

### NoWorktreesError

The project has no additional worktrees to switch to

**Properties:**

- `code` (string) (values: ["NO_WORKTREES"]) - 
- `message` (string) - 

### WorktreeNotFoundError

No worktree matches the provided name, path, or branch

**Properties:**

- `code` (string) (values: ["WORKTREE_NOT_FOUND"]) - 
- `message` (string) - 
- `searchedName` (string) - 

### AlreadyOnWorktreeError

The current workspace is already the requested worktree

**Properties:**

- `code` (string) (values: ["ALREADY_ON_WORKTREE"]) - 
- `message` (string) - 
- `worktreePath` (string) - 

### SwitchFailedError

The cursor-app-control MCP call to switch the workspace failed

**Properties:**

- `code` (string) (values: ["SWITCH_FAILED"]) - 
- `message` (string) - 
- `worktreePath` (string) - 
- `mcpError` (string) - 

## Prompt Content

# Switch Worktree

Switch the active workspace to a different git worktree, updating Cursor's UI when running inside Cursor.

> **PREREQUISITE — YOU MUST DO THIS FIRST**
>
> Before performing any actions, you MUST read and load @./.cursor\skills\worktrees-switch-worktree\SKILL.md using the Read tool. That skill contains the complete worktree switch workflow — every step, validation rule, Cursor environment detection logic, error handler, and response format. Do NOT proceed until you have read the skill file in full. Do NOT attempt to switch worktrees from memory or improvise the workflow. The skill is the sole source of truth.

Execute the entire workflow defined in the skill, including all steps, validation, error handling, and response formatting.

