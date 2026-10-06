---
promp:
  package: "worktrees"
  version: "1.3.1"
  environment: "development"
  prompVersion: "1.0.1-beta.161"
  prompt: "setup"
---
# worktrees.setup

Configure Cursor git worktrees to use a project-local .worktrees/ directory with a symlink from ~/.cursor/worktrees/

## Parameter Specifications

- **`projectRoot`** (string) - *Optional*
  - Absolute path to the project root directory. Defaults to the current workspace root.

- **`setupCommands`** (array) - *Optional*
  - Shell commands to run when a new worktree is created (e.g., dependency installation). Auto-detected from project files if not provided.

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
   - Parameter 1: `projectRoot` (optional) - Absolute path to the project root directory. Defaults to the current workspace root.
   - Parameter 2: `setupCommands` (optional) - Shell commands to run when a new worktree is created (e.g., dependency installation). Auto-detected from project files if not provided.

2. **Replace parameter placeholders** in the prompt content below:
   - Parameters use the format `{{parameterName}}` in the prompt
   - Replace each placeholder with the corresponding parsed value
   - If a parameter is optional and not provided, use its default value (if specified)
   - If a required parameter is missing, ask the user to provide it

3. **Execute the prompt** with the replaced parameters

## Usage

When the user invokes this command, they may provide parameters in various ways:
- Space-separated values: `/worktrees.setup value1 value2`
- Named parameters: `/worktrees.setup param1=value1 param2=value2`
- Mixed format: `/worktrees.setup value1 param2=value2`

Parse flexibly and map values to the expected parameters in order for positional arguments.

## Expected Output

Summary of the worktree configuration that was applied

**Type:** `object`

**Properties:**

- `projectName` (string) - **Required** - The project directory name used for the symlink
- `symlinkCreated` (boolean) - **Required** - Whether a new symlink was created
- `worktreesMigrated` (number) - **Required** - Number of existing worktrees that were migrated from the global directory
- `setupCommands` (array) - **Required** - The setup commands written to worktrees.json
- `gitignoreUpdated` (boolean) - **Required** - Whether .gitignore was created or updated
## Error Handling

### NotAGitRepoError

The target directory is not a git repository

**Properties:**

- `code` (string) (values: ["NOT_A_GIT_REPO"]) - 
- `message` (string) - 

### MigrationError

Existing worktree contents could not be moved to the local directory

**Properties:**

- `code` (string) (values: ["MIGRATION_FAILED"]) - 
- `message` (string) - 
- `globalPath` (string) - 
- `localPath` (string) - 

### SymlinkConflictError

The global worktree path is already a symlink pointing to a different location

**Properties:**

- `code` (string) (values: ["SYMLINK_CONFLICT"]) - 
- `message` (string) - 
- `currentTarget` (string) - 
- `expectedTarget` (string) - 

## Prompt Content

# Setup Worktrees

Configure Cursor git worktrees to use a project-local `.worktrees/` directory with a symlink from `~/.cursor/worktrees/`.

> **PREREQUISITE — YOU MUST DO THIS FIRST**
>
> Before performing any actions, you MUST read and load @./.cursor\skills\worktrees-setup-worktrees\SKILL.md using the Read tool. That skill contains the complete setup workflow — every step, validation rule, error handler, and response format. Do NOT proceed until you have read the skill file in full. Do NOT attempt to configure worktrees from memory or improvise the workflow. The skill is the sole source of truth.

Execute the entire workflow defined in the skill, including all steps, validation, error handling, and response formatting.

