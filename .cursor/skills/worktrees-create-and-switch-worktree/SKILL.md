---
name: worktrees-create-and-switch-worktree
description: >-
  Creates a new Cursor git worktree (optionally on a new feature branch created
  with the detached-HEAD-first technique), runs worktrees.json setup commands,
  and then switches the active workspace to it. Use when the user wants to
  create a worktree and immediately start working in it — e.g. "spin up a
  worktree for feature X and switch to it".
promp:
  package: "worktrees"
  version: "1.3.1"
  environment: "development"
  prompVersion: "1.0.1-beta.161"
  skill: "create-and-switch-worktree"
---

# Create and Switch Worktree

Create a new git worktree — optionally creating a new feature branch — run its setup hooks, and switch the active workspace to it in one flow.

## Overview

This skill is the composition of `create-worktree` and `switch-worktree`. It is the most common worktree workflow: start fresh work on a new branch in an isolated directory and immediately move the IDE there.

It performs three phases:

1. **Create** — creates the worktree using the bundled `worktree-create.sh` script. When creating a new branch, the script uses the **detached-HEAD-first technique** (create the worktree detached, then create the branch inside it) and rolls back the worktree if the branch step fails, so no orphaned worktree is left behind.
2. **Setup** — runs the `setup-worktree` commands from `.cursor/worktrees.json` inside the new worktree (unless skipped).
3. **Switch** — moves the active workspace to the new worktree. Inside Cursor, this calls the `cursor-app-control.move_agent_to_root` MCP tool; outside Cursor, it prints the `cd` command for the user.

If the switch fails, the worktree still exists and is fully usable — the user can switch manually.

## When to Use

- The user wants to create a worktree **and** start working in it right away
- The user says "create a branch and switch to it", "spin up a worktree for X and open it", "new worktree for feature Y and take me there"
- An agent needs to create an isolated working copy and continue its work there

## Parameters

- **{{newBranch}}** (string, optional): Name of a **new** feature branch to create in the worktree
  - Created with the detached-HEAD-first technique (with rollback on failure)
  - Follow the repo branching convention where applicable: `feature/{environment}/{feature-name}` (default environment `dev`)
  - Mutually exclusive with **{{branch}}**
  - Example: `"feature/dev/new-thing"`

- **{{branch}}** (string, optional): An **existing** branch, tag, or commit ref to check out
  - Mutually exclusive with **{{newBranch}}**
  - Example: `"feature/dev/existing-work"`

- **{{startPoint}}** (string, optional): Base commit/branch/tag for the new branch
  - Default: `HEAD` of the current repository
  - Only meaningful with **{{newBranch}}**

- **{{name}}** (string, optional): Short name for the worktree directory
  - Default: derived from the branch name (last segment, kebab-cased)

- **{{skipSetup}}** (boolean, optional): Skip the `worktrees.json` setup commands
  - Default: `false`

## Bundled Scripts

This skill drives two tested scripts from sibling skills. Resolve their absolute paths from wherever the package is installed (e.g. `.cursor/skills/<name>/scripts/...` or `<packageRoot>/skills/<name>/scripts/...`):

- **Create:** `create-worktree/scripts/worktree-create.sh` — see the `create-worktree` skill for its full contract.
- **Resolve (for the switch):** `switch-worktree/scripts/worktree-resolve.sh` — see the `switch-worktree` skill for its full contract.

The Cursor UI move itself is an MCP call (`cursor-app-control.move_agent_to_root`) and is performed by the agent, not a script.

## Instructions

### Step 1: Validate Prerequisites

#### Inputs
- **projectRoot** (current workspace root)
- **branch**, **newBranch** (from parameters)

#### Actions
- [ ] Confirm the directory is a git repository
- [ ] Confirm `.worktrees/` exists and `~/.cursor/worktrees/<project>` is a symlink to it
- [ ] Validate that at most one of **branch** / **newBranch** was provided

#### Validation
- [ ] The directory is a valid git repository
- [ ] `.worktrees/` is configured

**CRITICAL STOP CONDITION**: If worktrees are not configured, **STOP**:
```
Worktrees are not configured for this project yet.
Run /worktrees.setup first to configure the project-local worktree directory.
```

### Step 2: Create the Worktree

#### Inputs
- **projectRoot**, **name**, **newBranch**, **branch**, **startPoint** (from parameters)

#### Actions
- [ ] Determine the worktree directory name (from **name**, else derived from the branch, else ask the user)
- [ ] Set `worktree_path = <worktrees_dir>/<name>`
- [ ] Build the mode flag: **newBranch** → `--create-branch <newBranch>`; **branch** → `--branch <branch>`; neither → (default dir-named branch)
- [ ] If **startPoint** is provided, append `--start-point <startPoint>`
- [ ] Run `worktree-create.sh --repo <projectRoot> --path <worktree_path> <mode-flag> [--start-point ...]`
- [ ] Parse the `KEY=VALUE` output

#### Outputs
- **worktree_path**: `WORKTREE_PATH` from the script
- **worktree_branch**: `BRANCH` from the script
- **creation_success**: true when `STATUS=created`

#### Validation
- [ ] `STATUS=created`

**CRITICAL STOP CONDITION**: If the script returns `STATUS=error`, **STOP** and report the `ERROR` message. The script has already rolled back any partial worktree — do not attempt a switch, and do not clean up manually. Map `ERROR_CODE` per the `create-worktree` skill's Error Handling.

### Step 3: Run Setup Commands

#### Inputs
- **worktree_path** (from Step 2), **skipSetup** (from parameters)

#### Actions
- [ ] If **skipSetup** is true, skip this step
- [ ] Read `.cursor/worktrees.json`, extract `setup-worktree`, and run each command inside **worktree_path**
- [ ] If a setup command fails, warn but continue — do not abort the switch

#### Outputs
- **setup_results**: Per-command exit codes/output

### Step 4: Switch the Active Workspace

#### Inputs
- **worktree_path** (from Step 2)
- **projectRoot** (current workspace root)

#### Actions
- [ ] Confirm the canonical target with `worktree-resolve.sh --repo <projectRoot> --current <projectRoot> --query <worktree_path>` and take `TARGET_PATH` (already symlink-normalized)
- [ ] Detect whether `cursor-app-control.move_agent_to_root` is available in the agent's tool surface
- [ ] If available: call `move_agent_to_root` with `{ "rootPath": "<TARGET_PATH>" }`
- [ ] If not available: prepare the `cd <TARGET_PATH>` instruction for the user

#### Outputs
- **switch_method**: `"cursor-mcp"` or `"manual-cd"`
- **switch_success**: Boolean

**CRITICAL STOP CONDITION**: If in Cursor and the MCP call fails, report a `SwitchFailedError` but make clear the worktree WAS created successfully and can be entered manually with `cd <worktree_path>`.

### Step 5: Report Results

#### Actions
- [ ] Summarize: worktree path, branch (new/existing), setup result, and switch method
- [ ] For `manual-cd`, print the exact `cd` command

## Response Format

### Created and switched via Cursor MCP

```
Created and switched to worktree '<name>':

  Path: <worktree_path>
  Branch: <branch> (<new/existing>)
  Setup: <passed/failed/skipped>
  Switch: cursor-app-control (UI updated)

  Cursor's workspace is now pointing at the new worktree.
  New terminals will open in this directory.
```

### Created; manual switch required (not in Cursor)

```
Created worktree '<name>':

  Path: <worktree_path>
  Branch: <branch> (<new/existing>)
  Setup: <passed/failed/skipped>

  Run this command in your shell to switch:

    cd <worktree_path>
```

## Error Handling

All creation errors come from `worktree-create.sh` — see the `create-worktree` skill's Error Handling for `WORKTREE_EXISTS`, `BRANCH_EXISTS`, `BRANCH_IN_USE`, `INVALID_REF`, etc. Switch errors mirror the `switch-worktree` skill's `SwitchFailedError`, with the important distinction that **the worktree already exists** when a switch fails.

### WorktreesNotConfiguredError

```
Worktrees are not configured for this project yet.
Run /worktrees.setup first to configure the project-local worktree directory.
```

### SwitchFailedError (worktree still created)

```
Worktree '<name>' was created at <worktree_path>, but switching Cursor failed.

  MCP error: <error message>

Enter it manually with:
  cd <worktree_path>
```

## Examples

### Example 1: New feature branch, create and switch (inside Cursor)

**Parameters:** `newBranch="feature/dev/payment-retry"`

**Result:**
```
Created and switched to worktree 'payment-retry':

  Path: /Users/me/Sites/my-app/.worktrees/payment-retry
  Branch: feature/dev/payment-retry (new)
  Setup: npm install ✓, promp i ✓
  Switch: cursor-app-control (UI updated)
```

### Example 2: Existing branch with custom name

**Parameters:** `branch="feature/dev/existing-work"`, `name="review"`

**Result:**
```
Created and switched to worktree 'review':

  Path: /Users/me/Sites/my-app/.worktrees/review
  Branch: feature/dev/existing-work (existing)
  Setup: npm install ✓
  Switch: cursor-app-control (UI updated)
```

### Example 3: New branch, but branch already exists (rollback, no switch)

**Parameters:** `newBranch="feature/dev/taken"`

The create script returns `ERROR_CODE=BRANCH_EXISTS` and rolls back the detached worktree.

**Result:**
```
Could not create worktree: a branch named 'feature/dev/taken' already exists.

No worktree was created (the partial worktree was rolled back).
Choose a different branch name, or use branch="feature/dev/taken" to check out the existing branch.
```

## Notes

- This skill is a thin orchestrator over the `create-worktree` and `switch-worktree` scripts — it does not re-implement their logic, so their tests cover the create and resolve behavior.
- The switch step is best-effort: a switch failure never invalidates a successfully created worktree.
- When creating a new branch, the detached-HEAD-first rollback guarantee applies here exactly as in `create-worktree`.
