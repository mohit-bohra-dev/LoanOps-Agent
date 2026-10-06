---
name: worktrees-create-worktree
description: >-
  Creates a new Cursor git worktree from a branch or commit, places it in the
  project-local .worktrees/ directory, and runs worktrees.json setup commands.
  Use when the user wants to create a worktree, work on a branch in a separate
  directory, or spin up a parallel working copy.
promp:
  package: "worktrees"
  version: "1.3.1"
  environment: "development"
  prompVersion: "1.0.1-beta.161"
  skill: "create-worktree"
---

# Create Worktree

Create a new git worktree in the project-local `.worktrees/` directory and run setup hooks.

## Overview

This skill creates a git worktree inside the project's `.worktrees/` directory (which is symlinked from `~/.cursor/worktrees/<project>/`). After creation, it runs any setup commands defined in `.cursor/worktrees.json` (e.g., `npm install`, `promp i`) so the worktree is immediately ready for development.

The git-level creation is performed by a **bundled, tested script** — `scripts/worktree-create.sh` — rather than ad-hoc git commands, so the sequence is deterministic and consistent every time.

**Creating a new branch uses a two-phase technique:** the script first creates the worktree on a **detached HEAD** (`git worktree add --detach <path> <start-point>`), then creates the branch **inside** that worktree (`git -C <path> switch -c <branch>`). This decouples worktree creation from branch creation so each step is independently recoverable. Critically, if the branch step fails (e.g., the branch name is already taken or already checked out elsewhere), the script **removes the detached worktree it just created** so no orphaned worktree is left behind. The script's test harness (`scripts/test-worktree-create.sh`) verifies this rollback.

If the project's worktree symlink is not yet configured, the skill will inform the user to run the setup-worktrees skill first.

## Bundled Script

The git operations are owned by `scripts/worktree-create.sh`, located next to this skill file. Resolve its absolute path from wherever this `SKILL.md` was loaded (e.g. `.cursor/skills/create-worktree/scripts/worktree-create.sh`, or `<packageRoot>/skills/create-worktree/scripts/worktree-create.sh` after `promp i`).

```bash
worktree-create.sh --path <abs-worktree-path> [mode] [--start-point <ref>] [--repo <repo>] [--json]
```

Modes (choose at most one; default = new branch named after the worktree dir):

- `--create-branch <branch>` — new branch via detached-first + rollback
- `--branch <branch>` — check out an existing branch
- `--detach` — detached HEAD, no branch

It prints `KEY=VALUE` lines (or JSON with `--json`): on success `STATUS=created`, `WORKTREE_PATH`, `BRANCH`, `MODE`, `NEW_BRANCH`, `START_POINT`; on failure `STATUS=error`, `ERROR_CODE` (one of `BAD_USAGE`, `NOT_A_REPO`, `WORKTREE_EXISTS`, `INVALID_REF`, `BRANCH_EXISTS`, `BRANCH_IN_USE`, `GIT_ERROR`), and `ERROR`. Exit codes: `0` success, `1` operation error, `2` usage error. Parse this output rather than re-deriving state by hand.

## When to Use

- The user wants to create a new worktree
- The user wants to work on a branch in a separate directory
- The user asks to "add a worktree", "create a worktree", or "spin up a worktree"
- An agent needs a parallel working copy for isolated work (e.g., best-of-n)

## Parameters

- **{{branch}}** (string, optional): An **existing** branch, tag, or commit ref to check out in the worktree
  - Use this to work on a branch that already exists
  - Mutually exclusive with **{{newBranch}}**
  - Examples: `"feature/dev/my-feature"`, `"main"`, `"abc1234"`

- **{{newBranch}}** (string, optional): The name of a **new** feature branch to create in the worktree
  - Use this to start fresh work on a new branch
  - The branch is created with the detached-HEAD-first technique (see Overview) so a failed branch creation never leaves an orphaned worktree
  - Follow the repo branching convention where applicable: `feature/{environment}/{feature-name}` (default environment `dev`)
  - Mutually exclusive with **{{branch}}**
  - Examples: `"feature/dev/new-thing"`, `"fix/login-bug"`

- **{{startPoint}}** (string, optional): The base commit/branch/tag the new branch (or detached worktree) starts from
  - Default: `HEAD` of the current repository
  - Only meaningful with **{{newBranch}}**, **{{detach}}**, or the default (dir-named) branch mode
  - Example: `"main"`, `"origin/main"`, `"v1.2.0"`

- **{{detach}}** (boolean, optional): Create the worktree at a detached HEAD with no branch
  - Default: `false`
  - Mutually exclusive with **{{branch}}** and **{{newBranch}}**

- **{{name}}** (string, optional): A short name for the worktree directory
  - Default: auto-generated from the branch name (last segment, kebab-cased)
  - Used as the directory name inside `.worktrees/`
  - Examples: `"my-feature"`, `"hotfix"`, `"experiment-1"`

- **{{skipSetup}}** (boolean, optional): Skip running worktrees.json setup commands after creation
  - Default: `false`
  - Set to `true` for a faster worktree creation when setup is not needed

### Branch mode resolution

The parameters resolve to exactly one creation mode (the bundled script enforces mutual exclusion):

| Provided | Mode | Behavior |
|----------|------|----------|
| `newBranch` | create-branch | Detached-HEAD worktree, then create the new branch inside it (rolls back on failure) |
| `branch` (existing) | existing-branch | `git worktree add <path> <branch>` |
| `detach=true` | detached | Detached-HEAD worktree at `startPoint`, no branch |
| none | default-branch | New branch named after the worktree directory (same detached-first flow) |

## Instructions

Create a new git worktree following this workflow:

### Step 1: Validate Prerequisites

#### Inputs
- **projectRoot** (current workspace root)

#### Actions
- [ ] Confirm the directory is a git repository
- [ ] Check if `.worktrees/` directory exists in the project root
- [ ] Check if `~/.cursor/worktrees/<project-name>` is a symlink pointing to `.worktrees/`
- [ ] Run `git worktree list` to see current worktrees
- [ ] Validate that at most one of **branch**, **newBranch**, **detach** was provided (the script also enforces this, but catching it early gives a clearer message)

#### Outputs
- **project_name**: Basename of the project directory
- **worktrees_dir**: Absolute path to `.worktrees/`
- **worktrees_configured**: Boolean — whether the symlink setup is in place
- **existing_worktrees**: List of current worktrees from `git worktree list`

#### Validation
- [ ] The directory is a valid git repository
- [ ] `.worktrees/` directory exists

**CRITICAL STOP CONDITION**: If `.worktrees/` does not exist or the symlink is not configured, **STOP** and inform the user:
```
Worktrees are not configured for this project yet.
Run /worktrees.setup first to configure the project-local worktree directory.
```

### Step 2: Determine Worktree Path and Mode

#### Inputs
- **branch**, **newBranch**, **detach**, **name**, **startPoint** (from parameters, all optional)
- **worktrees_dir** (from Step 1)
- **existing_worktrees** (from Step 1)

#### Actions
- [ ] Determine the worktree directory name:
  - If **name** is provided, use it
  - Else if **branch** or **newBranch** is provided, derive the name from it (last path segment, kebab-cased — e.g., `feature/dev/my-feature` → `my-feature`)
  - Else ask the user what to name the worktree (or what branch they want)
- [ ] Set the full worktree path: `<worktrees_dir>/<name>`
- [ ] Map the parameters to the script mode flag:
  - **newBranch** provided → `--create-branch <newBranch>`
  - **branch** provided → `--branch <branch>`
  - **detach** true → `--detach`
  - none → (no mode flag; the script creates a branch named after the directory)
- [ ] If **startPoint** is provided, append `--start-point <startPoint>`

#### Outputs
- **worktree_path**: Full absolute path to the new worktree
- **worktree_name**: The directory name used
- **script_args**: The exact argument list to pass to `worktree-create.sh`
- **creates_new_branch**: Boolean — true for newBranch mode and the default (dir-named) mode

#### Validation
- [ ] **worktree_name** is a valid directory name (no spaces or special characters)

### Step 3: Create the Worktree (via the bundled script)

#### Inputs
- **worktree_path** and **script_args** (from Step 2)
- **projectRoot** (current workspace root)

#### Actions
- [ ] Resolve the absolute path to `scripts/worktree-create.sh` (see Bundled Script above)
- [ ] Run it, passing `--repo <projectRoot> --path <worktree_path>` plus **script_args**. Example:
  ```bash
  bash <script> --repo "<projectRoot>" --path "<worktree_path>" --create-branch "feature/dev/new-thing"
  ```
- [ ] Parse the `KEY=VALUE` output. On `STATUS=created`, capture `BRANCH`, `MODE`, `NEW_BRANCH`
- [ ] On `STATUS=error`, map `ERROR_CODE` to the matching Error Handling section below and **STOP**

#### Outputs
- **creation_success**: Boolean — true when `STATUS=created`
- **worktree_branch**: The `BRANCH` value (empty for detached)
- **error_code**: The `ERROR_CODE` value on failure, else null

#### Validation
- [ ] **creation_success** is true
- [ ] The worktree directory exists
- [ ] `git worktree list` includes the new worktree

**CRITICAL STOP CONDITION**: If the script returns `STATUS=error`, **STOP** and report the `ERROR` message. The script has already rolled back any partial detached worktree — do NOT attempt manual cleanup. Common `ERROR_CODE`s:
- `BRANCH_IN_USE` — branch already checked out in another worktree
- `BRANCH_EXISTS` — the new branch name is already taken
- `WORKTREE_EXISTS` — a directory already exists at the target path
- `INVALID_REF` — the start-point or existing branch does not resolve

### Step 4: Run Setup Commands

#### Inputs
- **worktree_path** (from Step 2)
- **skipSetup** (from parameters)
- **projectRoot** (current workspace root)

#### Actions
- [ ] If **skipSetup** is true, skip this step entirely
- [ ] Read `.cursor/worktrees.json` from the project root
- [ ] Extract the `setup-worktree` array
- [ ] For each command in the array, run it inside the worktree directory:
  - Change working directory to **worktree_path**
  - Execute the command
  - Capture output and exit code
- [ ] If a setup command fails, warn the user but do not delete the worktree

#### Outputs
- **setup_ran**: Boolean — whether setup commands were executed
- **setup_results**: Array of `{ command, exitCode, output }` for each command
- **setup_all_passed**: Boolean — whether all commands succeeded

#### Validation
- [ ] If setup was not skipped, at least one command was run
- [ ] Report any failed commands to the user

### Step 5: Report Results

#### Inputs
- All outputs from previous steps

#### Actions
- [ ] Run `git worktree list` for final confirmation
- [ ] Summarize what was done

#### Outputs
Report to the user:
- The worktree path
- The branch checked out
- Whether a new branch was created
- Setup command results (if any)
- How to navigate to the worktree

## Response Format

Present a clear summary:

```
Worktree created:

  Path: <worktree_path>
  Branch: <branch_name> (<new/existing>)
  Setup: <passed/failed/skipped>

  To work in this worktree:
    cd <worktree_path>

  git worktree list:
  <output>
```

## Error Handling

### WorktreesNotConfiguredError

**When it occurs:** The project does not have `.worktrees/` set up with the symlink.

```
Worktrees are not configured for this project yet.
Run /worktrees.setup first to configure the project-local worktree directory.
```

### WorktreeExistsError

**When it occurs:** A worktree directory with the requested name already exists.

```
A worktree already exists at <worktree_path>.
Use a different name, or remove the existing worktree first with /worktrees.remove.
```

### BranchInUseError

**When it occurs:** The branch is already checked out in another worktree.

```
Branch '<branch>' is already checked out in worktree at <other_path>.
Each branch can only be checked out in one worktree at a time.
Use a different branch or remove the other worktree first.
```

### GitCommandError

**When it occurs:** The `git worktree add` command fails for any other reason.

```
Failed to create worktree: <git error output>
```

## Examples

### Example 1: Create Worktree from Existing Branch

**Parameters:** `branch="feature/dev/my-feature"`

**Result:**
```
Worktree created:

  Path: /Users/me/Sites/my-app/.worktrees/my-feature
  Branch: feature/dev/my-feature (existing)
  Setup: npm install ✓, promp i ✓

  To work in this worktree:
    cd /Users/me/Sites/my-app/.worktrees/my-feature

  git worktree list:
  /Users/me/Sites/my-app                                abc1234 [main]
  /Users/me/.cursor/worktrees/my-app/my-feature         def5678 [feature/dev/my-feature]
```

### Example 2: Create Worktree with Custom Name

**Parameters:** `branch="main"`, `name="experiment"`

**Result:**
```
Worktree created:

  Path: /Users/me/Sites/my-app/.worktrees/experiment
  Branch: main (existing)
  Setup: npm install ✓

  To work in this worktree:
    cd /Users/me/Sites/my-app/.worktrees/experiment
```

### Example 3: Create Worktree for New Branch

**Parameters:** `branch="feature/dev/new-thing"`  (branch does not exist yet)

**Result:**
```
Worktree created:

  Path: /Users/me/Sites/my-app/.worktrees/new-thing
  Branch: feature/dev/new-thing (new — created from HEAD)
  Setup: npm install ✓

  To work in this worktree:
    cd /Users/me/Sites/my-app/.worktrees/new-thing
```

### Example 4: Skip Setup

**Parameters:** `branch="main"`, `name="quick"`, `skipSetup=true`

**Result:**
```
Worktree created:

  Path: /Users/me/Sites/my-app/.worktrees/quick
  Branch: main (existing)
  Setup: skipped

  To work in this worktree:
    cd /Users/me/Sites/my-app/.worktrees/quick
```

## Notes

- **New branches use the detached-HEAD-first technique.** The script creates the worktree detached, then creates the branch inside it, and removes the worktree if branch creation fails. This guarantees no orphaned detached worktrees accumulate from failed attempts.
- Each git branch can only be checked out in one worktree at a time — attempting to create a second worktree for the same branch will fail with `BRANCH_IN_USE`
- The worktree path appears under `~/.cursor/worktrees/<project>/` because of the symlink, which is how Cursor discovers and manages worktrees
- Setup commands run sequentially in the worktree directory; a failure in one does not prevent subsequent commands from running
- If setup commands fail, the worktree is still created — the user can fix and re-run manually
- Worktrees share the same git object store as the main repo, so they are lightweight on disk
- To create a worktree **and** immediately switch to it, use the `create-and-switch-worktree` skill (`/worktrees.createAndSwitch`)

## Testing

The bundled script has a test harness. Run it from the repo root:

```bash
bash <skill-dir>/scripts/test-worktree-create.sh
```

It builds throwaway git repos and asserts on all creation modes, the branch-creation rollback (no orphaned worktree), and every error code. It prints `PASS`/`FAIL` per scenario and exits non-zero if any fail.
