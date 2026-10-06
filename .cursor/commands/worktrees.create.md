---
promp:
  package: "worktrees"
  version: "1.3.1"
  environment: "development"
  prompVersion: "1.0.1-beta.161"
  prompt: "create"
---
# worktrees.create

Create a new git worktree in the project-local .worktrees/ directory, optionally creating a new feature branch (via the detached-HEAD-first technique), and run worktrees.json setup hooks

## Parameter Specifications

- **`branch`** (string) - *Optional*
  - An existing branch name, tag, or commit SHA to check out in the worktree. Mutually exclusive with newBranch and detach.

- **`newBranch`** (string) - *Optional*
  - Name of a new feature branch to create in the worktree. Created with the detached-HEAD-first technique: the worktree is created detached, then the branch is created inside it, with automatic rollback if branch creation fails. Follow the feature/{environment}/{feature-name} convention where applicable. Mutually exclusive with branch and detach.

- **`startPoint`** (string) - *Optional*
  - Base commit/branch/tag the new branch or detached worktree starts from. Defaults to the current HEAD. Only meaningful with newBranch, detach, or the default (dir-named) branch mode.

- **`detach`** (boolean) - *Optional*
  - Create the worktree at a detached HEAD with no branch. Mutually exclusive with branch and newBranch.

- **`name`** (string) - *Optional*
  - Short name for the worktree directory inside .worktrees/. Auto-derived from branch if not provided.

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
   - Parameter 1: `branch` (optional) - An existing branch name, tag, or commit SHA to check out in the worktree. Mutually exclusive with newBranch and detach.
   - Parameter 2: `newBranch` (optional) - Name of a new feature branch to create in the worktree. Created with the detached-HEAD-first technique: the worktree is created detached, then the branch is created inside it, with automatic rollback if branch creation fails. Follow the feature/{environment}/{feature-name} convention where applicable. Mutually exclusive with branch and detach.
   - Parameter 3: `startPoint` (optional) - Base commit/branch/tag the new branch or detached worktree starts from. Defaults to the current HEAD. Only meaningful with newBranch, detach, or the default (dir-named) branch mode.
   - Parameter 4: `detach` (optional) - Create the worktree at a detached HEAD with no branch. Mutually exclusive with branch and newBranch.
   - Parameter 5: `name` (optional) - Short name for the worktree directory inside .worktrees/. Auto-derived from branch if not provided.
   - Parameter 6: `skipSetup` (optional) - Skip running worktrees.json setup commands after creation.

2. **Replace parameter placeholders** in the prompt content below:
   - Parameters use the format `{{parameterName}}` in the prompt
   - Replace each placeholder with the corresponding parsed value
   - If a parameter is optional and not provided, use its default value (if specified)
   - If a required parameter is missing, ask the user to provide it

3. **Execute the prompt** with the replaced parameters

## Usage

When the user invokes this command, they may provide parameters in various ways:
- Space-separated values: `/worktrees.create value1 value2`
- Named parameters: `/worktrees.create param1=value1 param2=value2`
- Mixed format: `/worktrees.create value1 param2=value2`

Parse flexibly and map values to the expected parameters in order for positional arguments.

## Expected Output

Details of the created worktree

**Type:** `object`

**Properties:**

- `worktreePath` (string) - **Required** - Full absolute path to the new worktree directory
- `worktreeName` (string) - **Required** - The directory name used inside .worktrees/
- `branch` (string) - **Required** - The branch checked out in the worktree
- `newBranch` (boolean) - **Required** - Whether a new branch was created
- `setupResults` (array) - *Optional* - Results of each setup command that was run
## Error Handling

### WorktreesNotConfiguredError

The project does not have .worktrees/ set up with the symlink

**Properties:**

- `code` (string) (values: ["WORKTREES_NOT_CONFIGURED"]) - 
- `message` (string) - 

### WorktreeExistsError

A worktree directory with the requested name already exists

**Properties:**

- `code` (string) (values: ["WORKTREE_EXISTS"]) - 
- `message` (string) - 
- `existingPath` (string) - 

### BranchInUseError

The branch is already checked out in another worktree

**Properties:**

- `code` (string) (values: ["BRANCH_IN_USE"]) - 
- `message` (string) - 
- `branch` (string) - 
- `otherWorktree` (string) - 

### BranchExistsError

The requested new branch name already exists (the partial detached worktree is rolled back before this is returned)

**Properties:**

- `code` (string) (values: ["BRANCH_EXISTS"]) - 
- `message` (string) - 
- `branch` (string) - 

### GitCommandError

The git worktree add command failed

**Properties:**

- `code` (string) (values: ["GIT_COMMAND_FAILED"]) - 
- `message` (string) - 
- `gitOutput` (string) - 

## Prompt Content

# Create Worktree

Create a new git worktree in the project-local `.worktrees/` directory and run setup hooks. Optionally create a **new feature branch** for the worktree.

> **PREREQUISITE — YOU MUST DO THIS FIRST**
>
> Before performing any actions, you MUST read and load @./.cursor\skills\worktrees-create-worktree\SKILL.md using the Read tool. That skill contains the complete worktree creation workflow — every step, validation rule, error handler, and response format. Do NOT proceed until you have read the skill file in full. Do NOT attempt to create worktrees from memory or improvise the workflow. The skill is the sole source of truth.

Branch options (pass at most one):

- **{{newBranch}}** — create a new feature branch in the worktree (uses the detached-HEAD-first technique with rollback). Follow the `feature/{environment}/{feature-name}` convention where applicable.
- **{{branch}}** — check out an existing branch, tag, or commit.
- **{{detach}}** — create the worktree at a detached HEAD with no branch.
- (none) — create a new branch named after the worktree directory.

If the user wants to create the worktree and immediately switch into it, use `/worktrees.createAndSwitch` instead.

Execute the entire workflow defined in the skill, including all steps, validation, error handling, and response formatting.

