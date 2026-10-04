---
promp:
  package: "worktrees"
  version: "1.3.1"
  environment: "development"
  prompVersion: "1.0.1-beta.161"
  prompt: "update"
---
# worktrees.update

Update a worktree's branch to include changes from another branch using merge or rebase

## Parameter Specifications

- **`name`** (string) - *Optional*
  - Name or path of the worktree to update. If omitted, lists available worktrees for selection.

- **`sourceBranch`** (string) - *Optional*
  - The branch to pull changes from. Defaults to the repository's default branch (main or master).

- **`strategy`** (string) - *Optional*
  - How to incorporate changes: 'merge' creates a merge commit, 'rebase' replays commits on top of the source.
  - Default: `rebase`

- **`fetch`** (boolean) - *Optional*
  - Fetch from remote before updating to ensure the source branch is current.
  - Default: `true`

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
   - Parameter 1: `name` (optional) - Name or path of the worktree to update. If omitted, lists available worktrees for selection.
   - Parameter 2: `sourceBranch` (optional) - The branch to pull changes from. Defaults to the repository's default branch (main or master).
   - Parameter 3: `strategy` (optional) [default: rebase] - How to incorporate changes: 'merge' creates a merge commit, 'rebase' replays commits on top of the source.
   - Parameter 4: `fetch` (optional) [default: true] - Fetch from remote before updating to ensure the source branch is current.

2. **Replace parameter placeholders** in the prompt content below:
   - Parameters use the format `{{parameterName}}` in the prompt
   - Replace each placeholder with the corresponding parsed value
   - If a parameter is optional and not provided, use its default value (if specified)
   - If a required parameter is missing, ask the user to provide it

3. **Execute the prompt** with the replaced parameters

## Usage

When the user invokes this command, they may provide parameters in various ways:
- Space-separated values: `/worktrees.update value1 value2`
- Named parameters: `/worktrees.update param1=value1 param2=value2`
- Mixed format: `/worktrees.update value1 param2=value2`

Parse flexibly and map values to the expected parameters in order for positional arguments.

## Expected Output

Details of the update operation

**Type:** `object`

**Properties:**

- `worktreeName` (string) - **Required** - Name of the worktree that was updated
- `worktreeBranch` (string) - **Required** - The branch in the worktree
- `sourceBranch` (string) - **Required** - The branch changes were pulled from
- `strategy` (string) - **Required** - The strategy used
- `commitsIncorporated` (number) - **Required** - Number of new commits incorporated
- `stashRestored` (boolean) - *Optional* - Whether uncommitted changes were stashed and restored
## Error Handling

### WorktreeNotFoundError

No worktree matches the provided name

**Properties:**

- `code` (string) (values: ["WORKTREE_NOT_FOUND"]) - 
- `message` (string) - 
- `searchedName` (string) - 

### SourceBranchNotFoundError

The specified source branch does not exist

**Properties:**

- `code` (string) (values: ["SOURCE_BRANCH_NOT_FOUND"]) - 
- `message` (string) - 
- `sourceBranch` (string) - 

### MergeConflictError

The merge or rebase produced conflicts requiring manual resolution

**Properties:**

- `code` (string) (values: ["MERGE_CONFLICT"]) - 
- `message` (string) - 
- `strategy` (string) (values: ["merge","rebase"]) - 
- `conflicts` (array) - List of conflicting file paths
- `worktreePath` (string) - 

### DetachedHeadError

The worktree is in detached HEAD state

**Properties:**

- `code` (string) (values: ["DETACHED_HEAD"]) - 
- `message` (string) - 

## Prompt Content

# Update Worktree

Update a worktree's branch to include changes from another branch.

> **PREREQUISITE — YOU MUST DO THIS FIRST**
>
> Before performing any actions, you MUST read and load @./.cursor\skills\worktrees-update-worktree\SKILL.md using the Read tool. That skill contains the complete worktree update workflow — every step, validation rule, error handler, and response format. Do NOT proceed until you have read the skill file in full. Do NOT attempt to update worktrees from memory or improvise the workflow. The skill is the sole source of truth.

Execute the entire workflow defined in the skill, including all steps, validation, error handling, and response formatting.

