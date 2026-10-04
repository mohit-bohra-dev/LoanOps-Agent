---
name: worktrees-setup-worktrees
description: >-
  Configures Cursor git worktrees for a project by creating a local .worktrees
  directory and symlinking it into ~/.cursor/worktrees/. Handles migrating
  existing worktrees, creating worktrees.json with setup commands, and updating
  .gitignore. Use when setting up worktrees for a new project, migrating
  worktrees to a project-local directory, or configuring worktree setup hooks.
promp:
  package: "worktrees"
  version: "1.3.1"
  environment: "development"
  prompVersion: "1.0.1-beta.161"
  skill: "setup-worktrees"
---

# Setup Worktrees

Configure Cursor git worktrees so they live inside the project directory rather than the global `~/.cursor/worktrees/` folder.

## Overview

By default, Cursor stores git worktrees in `~/.cursor/worktrees/<project-name>/`. This skill reconfigures that location so worktrees live in `<project-root>/.worktrees/` with a symlink from the global path. This keeps worktree data co-located with the project and makes it visible in the project tree.

The skill also creates or updates `.cursor/worktrees.json`, which tells Cursor what setup commands to run when a new worktree is created (e.g., dependency installation).

## When to Use

- Setting up a new project for Cursor worktree support
- Migrating existing worktrees from `~/.cursor/worktrees/` into the project
- Configuring `worktrees.json` setup hooks for a project
- A user asks to "set up worktrees" or "configure worktrees"

## Parameters

- **{{projectRoot}}** (string, optional): Absolute path to the project root directory
  - Default: the current workspace root
  - Must be a git repository

- **{{setupCommands}}** (array of strings, optional): Commands to run when a new worktree is created
  - Default: inferred from the project (see Step 2)
  - Examples: `["npm install"]`, `["pip install -r requirements.txt"]`, `["bundle install"]`

## Instructions

Set up Cursor worktrees for the project following this workflow:

### Step 1: Detect Project Context

#### Inputs
- **projectRoot** (from parameters or current workspace)

#### Actions
- [ ] Confirm the directory is a git repository by checking for a `.git` directory or running `git rev-parse --show-toplevel`
- [ ] Determine the project name from the directory basename (e.g., `/Users/me/Sites/my-project` → `my-project`)
- [ ] Check if `~/.cursor/worktrees/<project-name>` already exists
- [ ] If it exists, check whether it is already a symlink (setup may already be done)
- [ ] Check if `<projectRoot>/.worktrees/` already exists
- [ ] Check if `<projectRoot>/.cursor/worktrees.json` already exists

#### Outputs
- **project_name**: The basename of the project directory
- **global_worktree_path**: `~/.cursor/worktrees/<project_name>`
- **local_worktree_path**: `<projectRoot>/.worktrees`
- **global_exists**: Boolean — whether the global path exists
- **global_is_symlink**: Boolean — whether the global path is already a symlink
- **local_exists**: Boolean — whether `.worktrees/` already exists locally
- **worktrees_json_exists**: Boolean — whether `.cursor/worktrees.json` exists
- **existing_worktrees**: Array of worktree directory names found at the global path (if any)

#### Validation
- [ ] The directory is a valid git repository
- [ ] **project_name** is not empty

**CRITICAL STOP CONDITION**: If the directory is not a git repository, **IMMEDIATELY STOP** and inform the user:
```
This directory is not a git repository. Worktrees require a git repository.
Run `git init` first, or navigate to a project that is already a git repository.
```

**ALREADY CONFIGURED**: If **global_is_symlink** is true and the symlink target matches **local_worktree_path**, inform the user that worktrees are already configured and skip to Step 4 (worktrees.json).

### Step 2: Infer Setup Commands

#### Inputs
- **projectRoot** (from parameters)
- **setupCommands** (from parameters, optional)

#### Actions
- [ ] If **setupCommands** was provided, use those directly
- [ ] Otherwise, detect the project type by checking for dependency files:
  - `package.json` → `["npm install"]`
  - `package-lock.json` → `["npm ci"]`
  - `yarn.lock` → `["yarn install"]`
  - `pnpm-lock.yaml` → `["pnpm install"]`
  - `requirements.txt` → `["pip install -r requirements.txt"]`
  - `Pipfile` → `["pipenv install"]`
  - `pyproject.toml` → `["pip install -e ."]`
  - `Gemfile` → `["bundle install"]`
  - `go.mod` → `["go mod download"]`
  - `Cargo.toml` → `["cargo fetch"]`
  - `promp.json` → append `"promp i"` to the list
- [ ] If the project has a `.cursor/worktrees.json` already, read it and merge — keep any existing commands the user already configured
- [ ] Multiple dependency files can result in multiple setup commands (e.g., a Node project with promp would get `["npm install", "promp i"]`)

#### Outputs
- **setup_commands**: Array of shell commands to include in `worktrees.json`

#### Validation
- [ ] **setup_commands** is a non-empty array

### Step 3: Create Local Worktrees Directory and Symlink

#### Inputs
- **local_worktree_path** (from Step 1)
- **global_worktree_path** (from Step 1)
- **global_exists** (from Step 1)
- **global_is_symlink** (from Step 1)
- **existing_worktrees** (from Step 1)

#### Actions

**Scenario A — Global path does not exist:**
- [ ] Create the local `.worktrees/` directory: `mkdir -p <local_worktree_path>`
- [ ] Ensure the parent `~/.cursor/worktrees/` directory exists: `mkdir -p ~/.cursor/worktrees`
- [ ] Create the symlink: `ln -s <local_worktree_path> <global_worktree_path>`

**Scenario B — Global path exists as a regular directory:**
- [ ] Create the local `.worktrees/` directory: `mkdir -p <local_worktree_path>`
- [ ] Move existing worktree contents into the local directory: `mv <global_worktree_path>/* <local_worktree_path>/`
- [ ] Remove the now-empty global directory: `rmdir <global_worktree_path>`
- [ ] Create the symlink: `ln -s <local_worktree_path> <global_worktree_path>`

**Scenario C — Global path is already a symlink:**
- [ ] If the symlink points to `<local_worktree_path>`, no action needed — skip to next step
- [ ] If the symlink points elsewhere, warn the user and ask before changing it

#### Outputs
- **symlink_created**: Boolean — whether the symlink was created or already existed
- **worktrees_migrated**: Number of existing worktrees that were migrated

#### Validation
- [ ] `<global_worktree_path>` is a symlink pointing to `<local_worktree_path>`
- [ ] `<local_worktree_path>` exists and is a directory
- [ ] Verify with `ls -la <global_worktree_path>` that the symlink is correct
- [ ] If worktrees were migrated, verify they still appear in `git worktree list`

**CRITICAL STOP CONDITION**: If `rmdir` fails because the global directory is not empty after the move, **STOP** and report the error. Do not force-delete — there may be files that failed to move.

### Step 4: Create or Update worktrees.json

#### Inputs
- **setup_commands** (from Step 2)
- **worktrees_json_exists** (from Step 1)
- **projectRoot** (from parameters)

#### Actions
- [ ] Create the `.cursor/` directory if it does not exist: `mkdir -p <projectRoot>/.cursor`
- [ ] Write `.cursor/worktrees.json` with the following structure:

```json
{
  "setup-worktree": [<setup_commands>]
}
```

- [ ] If the file already exists, read it first and merge the `setup-worktree` array — do not duplicate commands, but add any new ones that were detected

#### Outputs
- **worktrees_json_path**: Path to the created/updated file
- **worktrees_json_content**: The final JSON content

#### Validation
- [ ] The file exists at `<projectRoot>/.cursor/worktrees.json`
- [ ] The file is valid JSON
- [ ] `setup-worktree` is a non-empty array

### Step 5: Update .gitignore

#### Inputs
- **projectRoot** (from parameters)
- **local_worktree_path** (from Step 1)

#### Actions
- [ ] Check if `<projectRoot>/.gitignore` exists
- [ ] If it exists, check whether `.worktrees/` is already listed
- [ ] If `.worktrees/` is not listed, append it to the `.gitignore` file:
  ```
  # Cursor worktrees
  .worktrees/
  ```
- [ ] If `.gitignore` does not exist, create it with the `.worktrees/` entry

#### Outputs
- **gitignore_updated**: Boolean — whether the `.gitignore` was modified

#### Validation
- [ ] `.gitignore` contains a line matching `.worktrees/`

### Step 6: Verify and Report

#### Inputs
- All outputs from previous steps

#### Actions
- [ ] Run `git worktree list` to confirm git still recognizes all worktrees
- [ ] Run `ls -la <global_worktree_path>` to confirm the symlink
- [ ] Summarize what was done

#### Outputs
Report to the user with:
- Whether the symlink was created or was already in place
- How many existing worktrees were migrated (if any)
- The `worktrees.json` setup commands that were configured
- Whether `.gitignore` was updated
- The output of `git worktree list` for confirmation

## Response Format

Present a clear summary to the user:

```
Worktrees configured for <project_name>:

  Symlink: ~/.cursor/worktrees/<project_name> → <local_worktree_path>
  Migrated worktrees: <count>
  Setup commands: <setup_commands>
  .gitignore updated: <yes/no>

  git worktree list:
  <output>
```

## Error Handling

### NotAGitRepoError

**When it occurs:** The target directory is not a git repository.

```
This directory is not a git repository. Worktrees require a git repository.
Run `git init` first, or navigate to a project that is already a git repository.
```

### MigrationError

**When it occurs:** Existing worktree contents could not be moved to the local directory.

```
Failed to migrate worktrees from <global_path> to <local_path>.
The global directory is not empty after the move attempt.
Please manually check <global_path> and move any remaining files.
```

### SymlinkConflictError

**When it occurs:** The global path is already a symlink pointing to a different location.

```
~/.cursor/worktrees/<project_name> is already a symlink pointing to <current_target>.
Expected it to point to <local_worktree_path>.
Would you like to update the symlink? This will not affect the files at <current_target>.
```

## Examples

### Example 1: Fresh Setup (Node.js project with promp)

A project at `/Users/me/Sites/my-app` with `package.json` and `promp.json`, no existing worktrees.

**Result:**
```
Worktrees configured for my-app:

  Symlink: ~/.cursor/worktrees/my-app → /Users/me/Sites/my-app/.worktrees
  Migrated worktrees: 0
  Setup commands: ["npm install", "promp i"]
  .gitignore updated: yes

  git worktree list:
  /Users/me/Sites/my-app  abc1234 [main]
```

### Example 2: Migration with Existing Worktrees

A project at `/Users/me/Sites/my-app` where `~/.cursor/worktrees/my-app/` already contains a worktree `vvg`.

**Result:**
```
Worktrees configured for my-app:

  Symlink: ~/.cursor/worktrees/my-app → /Users/me/Sites/my-app/.worktrees
  Migrated worktrees: 1 (vvg)
  Setup commands: ["npm install"]
  .gitignore updated: yes

  git worktree list:
  /Users/me/Sites/my-app                        abc1234 [main]
  /Users/me/.cursor/worktrees/my-app/vvg        def5678 (detached HEAD)
```

### Example 3: Already Configured

A project where `.worktrees/` exists and the symlink is already correct.

**Result:**
```
Worktrees are already configured for my-app:

  Symlink: ~/.cursor/worktrees/my-app → /Users/me/Sites/my-app/.worktrees (already exists)
  Setup commands: ["npm install", "promp i"] (unchanged)
  .gitignore: already includes .worktrees/

  No changes were needed.
```

## Notes

- The `.worktrees/` directory should always be gitignored — it contains working copies, not source content
- The `worktrees.json` file should be committed to the repo so all developers share the same setup hooks
- If the project uses multiple package managers (e.g., npm + promp), all relevant install commands are included
- This setup is idempotent — running it again on an already-configured project makes no changes
- On macOS, symlinks work transparently. On Windows, symlinks may require elevated permissions
