---
promp:
  package: "worktrees"
  version: "1.3.1"
  environment: "development"
  prompVersion: "1.0.1-beta.161"
  prompt: "merge"
---
# worktrees.merge

Merge a worktree's branch into a target branch, with optional worktree cleanup after successful merge

## Parameter Specifications

- **`name`** (string) - *Optional*
  - Name or path of the worktree whose branch will be merged. If omitted, lists available worktrees for selection.

- **`targetBranch`** (string) - **Required**
  - The branch to merge into (e.g., 'main', 'develop'). Must be an existing branch.

- **`noFastForward`** (boolean) - *Optional*
  - Create a merge commit even when fast-forward is possible.

- **`deleteAfterMerge`** (boolean) - *Optional*
  - Remove the worktree after a successful merge.

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
   - Parameter 1: `name` (optional) - Name or path of the worktree whose branch will be merged. If omitted, lists available worktrees for selection.
   - Parameter 2: `targetBranch` (required) - The branch to merge into (e.g., 'main', 'develop'). Must be an existing branch.
   - Parameter 3: `noFastForward` (optional) - Create a merge commit even when fast-forward is possible.
   - Parameter 4: `deleteAfterMerge` (optional) - Remove the worktree after a successful merge.

2. **Replace parameter placeholders** in the prompt content below:
   - Parameters use the format `{{parameterName}}` in the prompt
   - Replace each placeholder with the corresponding parsed value
   - If a parameter is optional and not provided, use its default value (if specified)
   - If a required parameter is missing, ask the user to provide it

3. **Execute the prompt** with the replaced parameters

## Usage

When the user invokes this command, they may provide parameters in various ways:
- Space-separated values: `/worktrees.merge value1 value2`
- Named parameters: `/worktrees.merge param1=value1 param2=value2`
- Mixed format: `/worktrees.merge value1 param2=value2`

Parse flexibly and map values to the expected parameters in order for positional arguments.

## Expected Output

Details of the merge operation

**Type:** `object`

**Properties:**

- `sourceBranch` (string) - **Required** - The branch that was merged from (the worktree's branch)
- `targetBranch` (string) - **Required** - The branch that was merged into
- `mergeCommit` (string) - *Optional* - The merge commit SHA, or null if fast-forward
- `fastForward` (boolean) - **Required** - Whether the merge was a fast-forward
- `worktreeRemoved` (boolean) - **Required** - Whether the worktree was removed after merge
## Error Handling

### WorktreeNotFoundError

No worktree matches the provided name

**Properties:**

- `code` (string) (values: ["WORKTREE_NOT_FOUND"]) - 
- `message` (string) - 
- `searchedName` (string) - 

### TargetBranchNotFoundError

The specified target branch does not exist

**Properties:**

- `code` (string) (values: ["TARGET_BRANCH_NOT_FOUND"]) - 
- `message` (string) - 
- `targetBranch` (string) - 

### MergeConflictError

The merge produced conflicts requiring manual resolution

**Properties:**

- `code` (string) (values: ["MERGE_CONFLICT"]) - 
- `message` (string) - 
- `conflicts` (array) - List of conflicting file paths
- `mergeLocation` (string) - Path where the merge is in progress

### SameBranchError

The source and target branches are identical

**Properties:**

- `code` (string) (values: ["SAME_BRANCH"]) - 
- `message` (string) - 

## Prompt Content

# Merge Worktree

Merge a worktree's branch into a target branch.

> **PREREQUISITE — YOU MUST DO THIS FIRST**
>
> Before performing any actions, you MUST read and load @./.cursor\skills\worktrees-merge-worktree\SKILL.md using the Read tool. That skill contains the complete worktree merge workflow — every step, validation rule, error handler, and response format. Do NOT proceed until you have read the skill file in full. Do NOT attempt to merge worktrees from memory or improvise the workflow. The skill is the sole source of truth.

Execute the entire workflow defined in the skill, including all steps, validation, error handling, and response formatting.

