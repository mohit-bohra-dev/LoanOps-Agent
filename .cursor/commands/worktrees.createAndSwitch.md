---
promp:
  package: "worktrees"
  version: "1.3.1"
  environment: "development"
  prompVersion: "1.0.1-beta.161"
  prompt: "createAndSwitch"
---
# worktrees.createAndSwitch

Create a new git worktree (optionally on a new feature branch via the detached-HEAD-first technique), run worktrees.json setup hooks, and switch the active workspace to it in one flow

## Parameter Specifications

- **`newBranch`** (string) - *Optional*
  - Name of a new feature branch to create in the worktree. Created with the detached-HEAD-first technique (with automatic rollback if branch creation fails). Follow the feature/{environment}/{feature-name} convention where applicable. Mutually exclusive with branch.

- **`branch`** (string) - *Optional*
  - An existing branch name, tag, or commit SHA to check out in the worktree. Mutually exclusive with newBranch.

- **`startPoint`** (string) - *Optional*
  - Base commit/branch/tag the new branch starts from. Defaults to the current HEAD. Only meaningful with newBranch.

- **`name`** (string) - *Optional*
  - Short name for the worktree directory inside .worktrees/. Auto-derived from the branch if not provided.

- **`skipSetup`** (boolean) - *Optional*
  - Skip running worktrees.json setup commands after creation.

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
   - Parameter 1: `newBranch` (optional) - Name of a new feature branch to create in the worktree. Created with the detached-HEAD-first technique (with automatic rollback if branch creation fails). Follow the feature/{environment}/{feature-name} convention where applicable. Mutually exclusive with branch.
   - Parameter 2: `branch` (optional) - An existing branch name, tag, or commit SHA to check out in the worktree. Mutually exclusive with newBranch.
   - Parameter 3: `startPoint` (optional) - Base commit/branch/tag the new branch starts from. Defaults to the current HEAD. Only meaningful with newBranch.
   - Parameter 4: `name` (optional) - Short name for the worktree directory inside .worktrees/. Auto-derived from the branch if not provided.
   - Parameter 5: `skipSetup` (optional) - Skip running worktrees.json setup commands after creation.

2. **Replace parameter placeholders** in the prompt content below:
   - Parameters use the format `{{parameterName}}` in the prompt
   - Replace each placeholder with the corresponding parsed value
   - If a parameter is optional and not provided, use its default value (if specified)
   - If a required parameter is missing, ask the user to provide it

3. **Execute the prompt** with the replaced parameters

## Usage

When the user invokes this command, they may provide parameters in various ways:
- Space-separated values: `/worktrees.createAndSwitch value1 value2`
- Named parameters: `/worktrees.createAndSwitch param1=value1 param2=value2`
- Mixed format: `/worktrees.createAndSwitch value1 param2=value2`

Parse flexibly and map values to the expected parameters in order for positional arguments.

## Expected Output

Details of the created worktree and the switch operation

**Type:** `object`

**Properties:**

- `worktreePath` (string) - **Required** - Full absolute path to the new worktree directory
- `worktreeName` (string) - **Required** - The directory name used inside .worktrees/
- `branch` (string) - **Required** - The branch checked out in the worktree
- `newBranch` (boolean) - **Required** - Whether a new branch was created
- `method` (string) - *Optional* - How the switch was performed
- `switched` (boolean) - **Required** - Whether the active workspace was switched to the new worktree
## Error Handling

### WorktreesNotConfiguredError

The project does not have .worktrees/ set up with the symlink

**Properties:**

- `code` (string) (values: ["WORKTREES_NOT_CONFIGURED"]) - 
- `message` (string) - 

### BranchExistsError

The requested new branch name already exists (the partial detached worktree is rolled back before this is returned)

**Properties:**

- `code` (string) (values: ["BRANCH_EXISTS"]) - 
- `message` (string) - 
- `branch` (string) - 

### SwitchFailedError

The worktree was created successfully but the cursor-app-control MCP call to switch failed. The worktree can still be entered manually.

**Properties:**

- `code` (string) (values: ["SWITCH_FAILED"]) - 
- `message` (string) - 
- `worktreePath` (string) - 
- `mcpError` (string) - 

## Prompt Content

# Create and Switch Worktree

Create a new git worktree (optionally on a new feature branch), run its setup hooks, and switch the active workspace to it.

> **PREREQUISITE — YOU MUST DO THIS FIRST**
>
> Before performing any actions, you MUST read and load @./.cursor\skills\worktrees-create-and-switch-worktree\SKILL.md using the Read tool. That skill contains the complete create-then-switch workflow — every step, validation rule, error handler, and response format. Do NOT proceed until you have read the skill file in full. Do NOT attempt to create or switch worktrees from memory or improvise the workflow. The skill is the sole source of truth.

Branch options (pass at most one):

- **{{newBranch}}** — create a new feature branch in the worktree (uses the detached-HEAD-first technique with rollback). Follow the `feature/{environment}/{feature-name}` convention where applicable.
- **{{branch}}** — check out an existing branch, tag, or commit.
- (none) — create a new branch named after the worktree directory.

Execute the entire workflow defined in the skill, including all steps, validation, error handling, and response formatting. The switch step is best-effort: a failed switch never invalidates a successfully created worktree.

