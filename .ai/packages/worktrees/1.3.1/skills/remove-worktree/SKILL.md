---
name: remove-worktree
description: >-
  Removes a Cursor git worktree by name or path, cleaning up the directory and
  git metadata. Supports listing available worktrees for interactive selection.
  Use when the user wants to remove a worktree, clean up old worktrees, or
  delete a parallel working copy.
---

# Remove Worktree

Remove a git worktree and clean up its directory and git metadata.

## Overview

This skill removes a git worktree that was created in the project's `.worktrees/` directory. It handles the full cleanup: removing the working directory via `git worktree remove`, and running `git worktree prune` to clean up stale metadata. If the worktree has uncommitted changes, the skill warns the user and requires confirmation before proceeding with a force removal.

## When to Use

- The user wants to remove or delete a worktree
- The user wants to clean up old or stale worktrees
- The user asks to "remove a worktree", "delete a worktree", or "clean up worktrees"
- An agent is done with a temporary worktree and needs to clean up

## Parameters

- **{{name}}** (string, optional): Name or path of the worktree to remove
  - Can be the short directory name (e.g., `"my-feature"`) or a full path
  - If omitted, the skill lists available worktrees and asks the user to choose

- **{{force}}** (boolean, optional): Force removal even if the worktree has uncommitted changes
  - Default: `false`
  - When `false`, the skill will warn about uncommitted changes and ask for confirmation
  - When `true`, removes immediately without prompting

## Instructions

Remove a git worktree following this workflow:

### Step 1: Identify the Worktree

#### Inputs
- **name** (from parameters, optional)
- **projectRoot** (current workspace root)

#### Actions
- [ ] Confirm the directory is a git repository
- [ ] Run `git worktree list` to get all current worktrees
- [ ] Determine the `.worktrees/` directory path
- [ ] If **name** is provided:
  - Check if it matches a directory name inside `.worktrees/`
  - If not a direct match, check if it matches a full path in the worktree list
  - If not found, check if it is a partial match (e.g., user typed `"feat"` and there is `"my-feature"`)
- [ ] If **name** is NOT provided:
  - List all worktrees (excluding the main working tree)
  - Present them to the user with branch info and ask which to remove
  - Wait for user selection

#### Outputs
- **worktree_path**: Full absolute path to the worktree to remove
- **worktree_branch**: The branch checked out in the worktree
- **worktree_name**: The directory name
- **all_worktrees**: Full list from `git worktree list` (for reference)

#### Validation
- [ ] A matching worktree was found
- [ ] The selected worktree is NOT the main working tree

**CRITICAL STOP CONDITION**: If no matching worktree is found, **STOP** and inform the user:
```
No worktree found matching '<name>'.

Available worktrees:
<list from git worktree list, excluding main>

Use /worktrees.remove name="<worktree-name>" to remove one.
```

**CRITICAL STOP CONDITION**: If the user selects the main working tree, **STOP**:
```
Cannot remove the main working tree. Only additional worktrees can be removed.
```

### Step 2: Check for Uncommitted Changes

#### Inputs
- **worktree_path** (from Step 1)
- **force** (from parameters)

#### Actions
- [ ] Run `git -C <worktree_path> status --porcelain` to check for uncommitted changes
- [ ] Run `git -C <worktree_path> log --oneline @{upstream}..HEAD 2>/dev/null` to check for unpushed commits (if the branch tracks a remote)
- [ ] Assess the risk:
  - Uncommitted changes: files that would be lost
  - Unpushed commits: commits that exist only in this worktree

#### Outputs
- **has_uncommitted_changes**: Boolean
- **uncommitted_files**: Array of file paths with uncommitted changes
- **has_unpushed_commits**: Boolean
- **unpushed_commit_count**: Number of unpushed commits
- **safe_to_remove**: Boolean — true if no uncommitted changes and no unpushed commits

#### Validation
- [ ] If **safe_to_remove** is true, proceed to Step 3
- [ ] If **safe_to_remove** is false and **force** is false, warn the user and ask for confirmation
- [ ] If **safe_to_remove** is false and **force** is true, proceed to Step 3

**CONFIRMATION REQUIRED** (when not safe and not forced):
```
Worktree '<worktree_name>' has unsaved work:

  Uncommitted changes: <count> file(s)
  <list of files>

  Unpushed commits: <count>
  <list of commit summaries>

These changes will be permanently lost. Proceed with removal? (yes/no)
```

If the user says no, **STOP** without removing.

### Step 3: Remove the Worktree

#### Inputs
- **worktree_path** (from Step 1)
- **safe_to_remove** (from Step 2)
- **force** (from parameters or user confirmation)

#### Actions
- [ ] If **safe_to_remove** is true:
  - Run `git worktree remove <worktree_path>`
- [ ] If not safe but force/confirmed:
  - Run `git worktree remove --force <worktree_path>`
- [ ] If the remove command fails (e.g., locked worktree):
  - Try `git worktree remove --force <worktree_path>`
  - If still fails, manually remove the directory and run `git worktree prune`
- [ ] Run `git worktree prune` to clean up any stale worktree metadata

#### Outputs
- **removal_success**: Boolean
- **git_output**: Output from the removal commands
- **method_used**: `"clean"`, `"force"`, or `"manual+prune"`

#### Validation
- [ ] The worktree directory no longer exists
- [ ] `git worktree list` no longer includes the removed worktree

**CRITICAL STOP CONDITION**: If removal fails even with force and manual cleanup, **STOP** and report:
```
Failed to remove worktree at <worktree_path>.
Git error: <error output>

You may need to manually remove the directory and run:
  rm -rf <worktree_path>
  git worktree prune
```

### Step 4: Report Results

#### Inputs
- All outputs from previous steps

#### Actions
- [ ] Run `git worktree list` for final confirmation
- [ ] Summarize what was done

#### Outputs
Report to the user:
- Which worktree was removed
- What branch it was on
- Whether force was needed
- Updated worktree list

## Response Format

Present a clear summary:

```
Worktree removed:

  Path: <worktree_path>
  Branch: <branch_name>
  Method: <clean/force>

  git worktree list:
  <output>
```

## Error Handling

### WorktreeNotFoundError

**When it occurs:** No worktree matches the provided name.

```
No worktree found matching '<name>'.

Available worktrees:
<list>
```

### MainWorktreeError

**When it occurs:** The user attempts to remove the main working tree.

```
Cannot remove the main working tree. Only additional worktrees can be removed.
```

### RemovalFailedError

**When it occurs:** The git worktree remove command fails even with --force.

```
Failed to remove worktree at <path>.
Git error: <output>

Manual cleanup:
  rm -rf <path>
  git worktree prune
```

### UnsavedChangesWarning

**When it occurs:** The worktree has uncommitted changes or unpushed commits and force is not set. This is a warning that requires user confirmation, not a fatal error.

## Examples

### Example 1: Clean Removal by Name

**Parameters:** `name="my-feature"`

**Result:**
```
Worktree removed:

  Path: /Users/me/Sites/my-app/.worktrees/my-feature
  Branch: feature/dev/my-feature
  Method: clean

  git worktree list:
  /Users/me/Sites/my-app  abc1234 [main]
```

### Example 2: Interactive Selection (No Name Provided)

**Parameters:** (none)

**Interaction:**
```
Which worktree would you like to remove?

  1. my-feature    (branch: feature/dev/my-feature)
  2. experiment    (branch: main)
  3. hotfix        (branch: fix/login-bug)
```

User selects `1`.

**Result:**
```
Worktree removed:

  Path: /Users/me/Sites/my-app/.worktrees/my-feature
  Branch: feature/dev/my-feature
  Method: clean

  git worktree list:
  /Users/me/Sites/my-app                              abc1234 [main]
  /Users/me/.cursor/worktrees/my-app/experiment       def5678 [main]
  /Users/me/.cursor/worktrees/my-app/hotfix           ghi9012 [fix/login-bug]
```

### Example 3: Removal with Uncommitted Changes

**Parameters:** `name="experiment"`

**Interaction:**
```
Worktree 'experiment' has unsaved work:

  Uncommitted changes: 3 file(s)
    M  src/config.ts
    M  src/utils.ts
    ?? src/temp.ts

  Unpushed commits: 0

These changes will be permanently lost. Proceed with removal? (yes/no)
```

User says `yes`.

**Result:**
```
Worktree removed:

  Path: /Users/me/Sites/my-app/.worktrees/experiment
  Branch: main
  Method: force (user confirmed)
```

### Example 4: Force Removal

**Parameters:** `name="hotfix"`, `force=true`

**Result:**
```
Worktree removed:

  Path: /Users/me/Sites/my-app/.worktrees/hotfix
  Branch: fix/login-bug
  Method: force

  git worktree list:
  /Users/me/Sites/my-app  abc1234 [main]
```

## Notes

- Removing a worktree does NOT delete the branch — the branch still exists in the repository
- If the branch was created specifically for the worktree and is no longer needed, the user should delete it separately with `git branch -d <branch>`
- `git worktree prune` is always run after removal to clean up any stale metadata entries
- The main working tree (the original clone directory) can never be removed
- Worktrees with a locked state (`git worktree lock`) require unlocking before removal, or use `--force`
