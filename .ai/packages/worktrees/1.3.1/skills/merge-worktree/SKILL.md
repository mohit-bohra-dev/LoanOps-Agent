---
name: merge-worktree
description: >-
  Merges a worktree's branch into a target branch. Validates clean state,
  locates the target branch checkout, performs the merge, and optionally
  removes the worktree afterward. Use when the user wants to merge worktree
  changes back into main, dev, or any other branch.
promp:
  package: "worktrees"
  version: "1.0.0"
  environment: "development"
  prompVersion: "1.0.1-beta.19"
  skill: "merge-worktree"
---

# Merge Worktree

Merge a worktree's branch into a target branch.

## Overview

This skill merges the branch checked out in a worktree into a specified target branch. Because git worktrees share the same object store, the merge operates on branches within the same repository. The skill finds where the target branch is checked out (main working tree, another worktree, or not checked out anywhere), performs the merge from that location, and reports the result.

If the target branch is not checked out in any worktree, the skill temporarily checks it out in the main working tree (stashing any in-progress work), performs the merge, and restores the original branch.

## When to Use

- The user wants to merge a worktree's work into another branch
- The user says "merge this worktree into main" or "merge my worktree back"
- An agent finishes work in a worktree and needs to integrate changes
- The user wants to land worktree changes without manually switching branches

## Parameters

- **{{name}}** (string, optional): Name or path of the worktree whose branch will be merged
  - Can be the short directory name (e.g., `"my-feature"`) or a full path
  - If omitted, lists available worktrees and asks the user to choose

- **{{targetBranch}}** (string, required): The branch to merge into
  - Must be an existing branch (e.g., `"main"`, `"develop"`, `"feature/dev/base"`)
  - Cannot be the same branch that the source worktree has checked out

- **{{noFastForward}}** (boolean, optional): Create a merge commit even when fast-forward is possible
  - Default: `false`
  - When `true`, uses `git merge --no-ff`

- **{{deleteAfterMerge}}** (boolean, optional): Remove the worktree after a successful merge
  - Default: `false`
  - When `true`, runs the remove-worktree workflow after the merge succeeds

## Instructions

Merge a worktree's branch into a target branch following this workflow:

### Step 1: Identify the Source Worktree

#### Inputs
- **name** (from parameters, optional)
- **projectRoot** (current workspace root)

#### Actions
- [ ] Confirm the directory is a git repository
- [ ] Run `git worktree list` to get all current worktrees
- [ ] If **name** is provided:
  - Match it against worktree directory names inside `.worktrees/`
  - If not a direct match, try matching against full paths in the worktree list
  - If not found, try partial matching
- [ ] If **name** is NOT provided:
  - List all worktrees (excluding the main working tree)
  - Present them to the user with branch info and ask which to merge
  - Wait for user selection
- [ ] Determine the branch checked out in the selected worktree

#### Outputs
- **source_worktree_path**: Full absolute path to the source worktree
- **source_worktree_name**: The directory name
- **source_branch**: The branch checked out in the source worktree
- **all_worktrees**: Full list from `git worktree list`

#### Validation
- [ ] A matching worktree was found
- [ ] The worktree has a branch checked out (not detached HEAD)

**CRITICAL STOP CONDITION**: If no matching worktree is found, **STOP** and inform the user:
```
No worktree found matching '<name>'.

Available worktrees:
<list from git worktree list, excluding main>
```

**CRITICAL STOP CONDITION**: If the worktree is in detached HEAD state, **STOP**:
```
Worktree '<name>' is in detached HEAD state (not on a branch).
Check out a branch in the worktree first, or specify a branch to merge.
```

### Step 2: Validate Preconditions

#### Inputs
- **source_worktree_path** (from Step 1)
- **source_branch** (from Step 1)
- **targetBranch** (from parameters)
- **all_worktrees** (from Step 1)

#### Actions
- [ ] Verify the target branch exists: `git rev-parse --verify <targetBranch>`
- [ ] Verify the source and target branches are different
- [ ] Check for uncommitted changes in the source worktree: `git -C <source_worktree_path> status --porcelain`
- [ ] If there are uncommitted changes, warn the user and ask whether to:
  - Commit them first (provide a message)
  - Stash them
  - Abort the merge
- [ ] Determine where the target branch is checked out by scanning `git worktree list`:
  - **Case A**: Target branch is checked out in the main working tree
  - **Case B**: Target branch is checked out in another worktree
  - **Case C**: Target branch is not checked out anywhere

#### Outputs
- **target_branch_valid**: Boolean
- **source_is_clean**: Boolean
- **target_checkout_location**: Path where target branch is checked out, or null
- **target_checkout_case**: "main", "other-worktree", or "not-checked-out"
- **main_worktree_path**: Path to the main working tree
- **main_worktree_branch**: Branch currently checked out in the main working tree

#### Validation
- [ ] **target_branch_valid** is true
- [ ] Source and target branches are different
- [ ] Source worktree is clean (or user resolved uncommitted changes)

**CRITICAL STOP CONDITION**: If the target branch does not exist, **STOP**:
```
Target branch '<targetBranch>' does not exist.
Available branches: <list a few relevant branches>
```

**CRITICAL STOP CONDITION**: If source and target are the same branch, **STOP**:
```
Source branch '<source_branch>' is the same as the target branch. Nothing to merge.
```

### Step 3: Perform the Merge

#### Inputs
- **source_branch** (from Step 1)
- **targetBranch** (from parameters)
- **noFastForward** (from parameters)
- **target_checkout_case** (from Step 2)
- **target_checkout_location** (from Step 2)
- **main_worktree_path** (from Step 2)
- **main_worktree_branch** (from Step 2)

#### Actions

**Case A — Target is checked out in the main working tree:**
- [ ] Check for uncommitted changes in the main working tree: `git -C <main_worktree_path> status --porcelain`
- [ ] If dirty, stash changes: `git -C <main_worktree_path> stash push -m "merge-worktree: auto-stash before merge"`
- [ ] Run the merge from the main working tree:
  - `git -C <main_worktree_path> merge <source_branch>` (or `--no-ff` if **noFastForward**)
- [ ] If stashed, pop the stash: `git -C <main_worktree_path> stash pop`

**Case B — Target is checked out in another worktree:**
- [ ] Check for uncommitted changes in that worktree
- [ ] If dirty, stash changes
- [ ] Run the merge from that worktree's path:
  - `git -C <target_checkout_location> merge <source_branch>` (or `--no-ff`)
- [ ] If stashed, pop the stash

**Case C — Target is not checked out anywhere:**
- [ ] Stash any changes in the main working tree if dirty
- [ ] Save the current branch of the main working tree
- [ ] Check out the target branch in the main working tree: `git -C <main_worktree_path> checkout <targetBranch>`
- [ ] Run the merge: `git -C <main_worktree_path> merge <source_branch>` (or `--no-ff`)
- [ ] Switch back to the original branch: `git -C <main_worktree_path> checkout <main_worktree_branch>`
- [ ] Pop the stash if one was created

#### Outputs
- **merge_success**: Boolean
- **merge_output**: Output from the git merge command
- **fast_forward**: Boolean — whether the merge was a fast-forward
- **merge_commit**: The merge commit SHA (if a merge commit was created)
- **conflicts**: Array of conflicting files (if merge failed due to conflicts)

#### Validation
- [ ] **merge_success** is true
- [ ] The main working tree is restored to its original state

**CRITICAL STOP CONDITION**: If merge conflicts occur, **STOP** and report:
```
Merge conflicts detected when merging '<source_branch>' into '<targetBranch>':

  <list of conflicting files>

The merge is in progress at <merge_location>.
Resolve the conflicts there, then run:
  git -C <merge_location> add .
  git -C <merge_location> commit
```

### Step 4: Optional Cleanup

#### Inputs
- **deleteAfterMerge** (from parameters)
- **merge_success** (from Step 3)
- **source_worktree_path** (from Step 1)
- **source_worktree_name** (from Step 1)

#### Actions
- [ ] If **deleteAfterMerge** is true and **merge_success** is true:
  - Run `git worktree remove <source_worktree_path>`
  - Run `git worktree prune`
- [ ] If **deleteAfterMerge** is false, skip this step

#### Outputs
- **worktree_removed**: Boolean
- **removal_output**: Output from the removal command (if applicable)

### Step 5: Report Results

#### Inputs
- All outputs from previous steps

#### Actions
- [ ] Run `git log --oneline -5 <targetBranch>` to show recent commits on the target
- [ ] Run `git worktree list` for final state
- [ ] Summarize what was done

#### Outputs
Report to the user:
- Source branch and worktree
- Target branch
- Whether the merge was fast-forward or created a merge commit
- Whether the worktree was removed
- Recent commits on the target branch

## Response Format

Present a clear summary:

```
Merge complete:

  Source: <source_branch> (worktree: <source_worktree_name>)
  Target: <targetBranch>
  Result: <fast-forward / merge commit <sha>>
  Worktree: <kept / removed>

  Recent commits on <targetBranch>:
  <git log output>

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

### TargetBranchNotFoundError

**When it occurs:** The specified target branch does not exist.

```
Target branch '<targetBranch>' does not exist.
Create it first or specify a different target.
```

### SameBranchError

**When it occurs:** The source and target branches are identical.

```
Source branch '<branch>' is the same as the target branch. Nothing to merge.
```

### DetachedHeadError

**When it occurs:** The source worktree is in detached HEAD state.

```
Worktree '<name>' is in detached HEAD state.
Check out a branch first, or specify a branch to merge.
```

### MergeConflictError

**When it occurs:** The merge produces conflicts that require manual resolution.

```
Merge conflicts detected when merging '<source_branch>' into '<targetBranch>':

  <conflicting files>

Resolve conflicts at <location>, then:
  git add .
  git commit
```

### UncommittedChangesWarning

**When it occurs:** The source worktree has uncommitted changes. This is a warning requiring user decision, not a fatal error.

## Examples

### Example 1: Merge Feature Branch into Main

**Parameters:** `name="my-feature"`, `targetBranch="main"`

**Result:**
```
Merge complete:

  Source: feature/dev/my-feature (worktree: my-feature)
  Target: main
  Result: merge commit abc1234
  Worktree: kept

  Recent commits on main:
  abc1234 Merge branch 'feature/dev/my-feature'
  def5678 Previous commit on main

  git worktree list:
  /Users/me/Sites/my-app                              abc1234 [main]
  /Users/me/.cursor/worktrees/my-app/my-feature       ghi9012 [feature/dev/my-feature]
```

### Example 2: Fast-Forward Merge and Delete Worktree

**Parameters:** `name="hotfix"`, `targetBranch="main"`, `deleteAfterMerge=true`

**Result:**
```
Merge complete:

  Source: fix/login-bug (worktree: hotfix)
  Target: main
  Result: fast-forward to abc1234
  Worktree: removed

  Recent commits on main:
  abc1234 Fix login redirect loop
  def5678 Previous commit

  git worktree list:
  /Users/me/Sites/my-app  abc1234 [main]
```

### Example 3: Merge with --no-ff

**Parameters:** `name="experiment"`, `targetBranch="develop"`, `noFastForward=true`

**Result:**
```
Merge complete:

  Source: feature/dev/experiment (worktree: experiment)
  Target: develop
  Result: merge commit abc1234 (--no-ff)
  Worktree: kept

  Recent commits on develop:
  abc1234 Merge branch 'feature/dev/experiment' into develop
  def5678 Add experiment results
  ghi9012 Set up experiment framework
```

### Example 4: Merge Conflict

**Parameters:** `name="my-feature"`, `targetBranch="main"`

**Result:**
```
Merge conflicts detected when merging 'feature/dev/my-feature' into 'main':

  src/config.ts
  src/utils/helpers.ts

The merge is in progress in the main working tree at /Users/me/Sites/my-app.
Resolve the conflicts there, then run:
  git add .
  git commit
```

## Notes

- The source worktree's branch is never modified — only the target branch receives the merge
- If the target branch is checked out in a worktree with uncommitted changes, those changes are automatically stashed and restored after the merge
- The original branch in the main working tree is always restored after the operation, even in Case C
- Merge conflicts leave the merge in progress at the location where the target was checked out — the user must resolve them there
- The `deleteAfterMerge` option only triggers if the merge succeeds without conflicts
- Deleting the worktree does NOT delete the source branch — use `git branch -d` separately if the branch is no longer needed
