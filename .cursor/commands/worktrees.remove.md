---
promp:
  package: "worktrees"
  version: "1.3.1"
  environment: "development"
  prompVersion: "1.0.1-beta.161"
  prompt: "remove"
---
# worktrees.remove

Remove a git worktree by name or path, cleaning up the directory and git metadata. Lists available worktrees if no name is provided.

## Parameter Specifications

- **`name`** (string) - *Optional*
  - Name or path of the worktree to remove. If omitted, lists available worktrees for selection.

- **`force`** (boolean) - *Optional*
  - Force removal even if the worktree has uncommitted changes.

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
   - Parameter 1: `name` (optional) - Name or path of the worktree to remove. If omitted, lists available worktrees for selection.
   - Parameter 2: `force` (optional) - Force removal even if the worktree has uncommitted changes.

2. **Replace parameter placeholders** in the prompt content below:
   - Parameters use the format `{{parameterName}}` in the prompt
   - Replace each placeholder with the corresponding parsed value
   - If a parameter is optional and not provided, use its default value (if specified)
   - If a required parameter is missing, ask the user to provide it

3. **Execute the prompt** with the replaced parameters

## Usage

When the user invokes this command, they may provide parameters in various ways:
- Space-separated values: `/worktrees.remove value1 value2`
- Named parameters: `/worktrees.remove param1=value1 param2=value2`
- Mixed format: `/worktrees.remove value1 param2=value2`

Parse flexibly and map values to the expected parameters in order for positional arguments.

## Expected Output

Details of the removed worktree

**Type:** `object`

**Properties:**

- `worktreePath` (string) - **Required** - Full path of the removed worktree
- `worktreeName` (string) - **Required** - The directory name that was removed
- `branch` (string) - **Required** - The branch that was checked out in the removed worktree
- `method` (string) - **Required** - How the removal was performed
## Error Handling

### WorktreeNotFoundError

No worktree matches the provided name

**Properties:**

- `code` (string) (values: ["WORKTREE_NOT_FOUND"]) - 
- `message` (string) - 
- `searchedName` (string) - 

### MainWorktreeError

The user attempted to remove the main working tree

**Properties:**

- `code` (string) (values: ["CANNOT_REMOVE_MAIN"]) - 
- `message` (string) - 

### RemovalFailedError

The git worktree remove command failed even with --force

**Properties:**

- `code` (string) (values: ["REMOVAL_FAILED"]) - 
- `message` (string) - 
- `gitOutput` (string) - 
- `worktreePath` (string) - 

## Prompt Content

# Remove Worktree

Remove a git worktree and clean up its directory and git metadata.

> **PREREQUISITE — YOU MUST DO THIS FIRST**
>
> Before performing any actions, you MUST read and load @./.cursor\skills\worktrees-remove-worktree\SKILL.md using the Read tool. That skill contains the complete worktree removal workflow — every step, validation rule, error handler, and response format. Do NOT proceed until you have read the skill file in full. Do NOT attempt to remove worktrees from memory or improvise the workflow. The skill is the sole source of truth.

Execute the entire workflow defined in the skill, including all steps, validation, error handling, and response formatting.

