---
name: update-worktree
description: >-
  Updates a worktree's branch to include changes from another branch using
  merge or rebase. Handles stashing, conflict detection, and recovery. Use
  when the user wants to pull in latest main, sync a worktree, or rebase a
  worktree branch onto another branch.
promp:
  package: "worktrees"
  version: "1.0.0"
  environment: "development"
  prompVersion: "1.0.1-beta.19"
  skill: "update-worktree"
---

# Update Worktree

Update a worktree's branch to include changes from another branch.

## Overview

This skill brings a worktree's branch up to date with another branch (typically `main` or `develop`). It supports two strategies: **merge** (bring changes in via a merge commit) or **rebase** (replay the worktree's commits on top of the source branch). The skill handles stashing uncommitted work, fetching the latest remote state, performing the update, and restoring the working state.

This is the worktree equivalent of "pull latest main into my feature branch" — but operating within the worktree context where branch switching is not needed.

## When to Use

- The user wants to update a worktree with the latest changes from another branch
- The user says "sync my worktree with main", "rebase onto main", or "update worktree"
- An agent needs to bring a worktree up to date before continuing work
- The user wants to pull upstream changes into a feature branch in a worktree

## Parameters

- **{{name}}** (string, optional): Name or path of the worktree to update
  - Can be the short directory name (e.g., `"my-feature"`) or a full path
  - If omitted, lists available worktrees and asks the user to choose

- **{{sourceBranch}}** (string, optional): The branch to pull changes from
  - Default: auto-detected from the repository's default branch (`main` or `master`)
  - Examples: `"main"`, `"develop"`, `"feature/dev/base"`

- **{{strategy}}** (string, optional): How to incorporate the changes
  - Default: `"rebase"`
  - Allowed values: `"merge"`, `"rebase"`
  - `"merge"` — creates a merge commit bringing source changes into the worktree's branch
  - `"rebase"` — replays worktree commits on top of the source branch

- **{{fetch}}** (boolean, optional): Fetch from remote before updating
  - Default: `true`
  - When `true`, runs `git fetch origin` to get the latest remote state before merging/rebasing

## Instructions

Update a worktree's branch following this workflow:

### Step 1: Identify the Worktree

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
  - Present them to the user with branch info and ask which to update
  - Wait for user selection
- [ ] Determine the branch checked out in the selected worktree

#### Outputs
- **worktree_path**: Full absolute path to the worktree
- **worktree_name**: The directory name
- **worktree_branch**: The branch checked out in the worktree
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
Cannot update a detached HEAD. Check out a branch first.
```

### Step 2: Determine Source Branch and Validate

#### Inputs
- **sourceBranch** (from parameters, optional)
- **worktree_branch** (from Step 1)
- **worktree_path** (from Step 1)

#### Actions
- [ ] If **sourceBranch** is not provided, detect the default branch:
  - Try `git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null` and extract the branch name
  - If that fails, check if `main` exists: `git rev-parse --verify main 2>/dev/null`
  - If that fails, check if `master` exists: `git rev-parse --verify master 2>/dev/null`
  - If none found, ask the user to specify
- [ ] Verify the source branch exists: `git rev-parse --verify <sourceBranch>`
- [ ] Verify source and worktree branches are different
- [ ] Check if there are any changes to incorporate:
  - `git log --oneline <worktree_branch>..<sourceBranch>` to see what's new on the source
  - If empty, the worktree is already up to date

#### Outputs
- **resolved_source_branch**: The source branch name (resolved from default or parameter)
- **source_branch_valid**: Boolean
- **branches_differ**: Boolean
- **new_commits_count**: Number of new commits on the source branch
- **already_up_to_date**: Boolean — true if no new commits

#### Validation
- [ ] **source_branch_valid** is true
- [ ] **branches_differ** is true

**CRITICAL STOP CONDITION**: If the source branch does not exist, **STOP**:
```
Source branch '<sourceBranch>' does not exist.
Available branches: <list a few relevant branches>
```

**EARLY EXIT**: If **already_up_to_date** is true, inform the user and stop:
```
Worktree '<worktree_name>' is already up to date with '<sourceBranch>'.
No changes to incorporate.
```

### Step 3: Prepare the Worktree

#### Inputs
- **worktree_path** (from Step 1)
- **fetch** (from parameters)

#### Actions
- [ ] If **fetch** is true:
  - Run `git fetch origin` from the worktree to get the latest remote state
  - If the source branch has an upstream, update the local tracking: the fetch covers this
- [ ] Check for uncommitted changes in the worktree: `git -C <worktree_path> status --porcelain`
- [ ] If there are uncommitted changes:
  - Stash them: `git -C <worktree_path> stash push -m "update-worktree: auto-stash before update"`
  - Record that a stash was created

#### Outputs
- **fetch_ran**: Boolean
- **fetch_output**: Output from git fetch (if ran)
- **had_uncommitted_changes**: Boolean
- **stash_created**: Boolean
- **stash_ref**: The stash reference (if created)

#### Validation
- [ ] If fetch was requested, it completed successfully
- [ ] The worktree is clean (either was already clean or changes were stashed)

### Step 4: Perform the Update

#### Inputs
- **worktree_path** (from Step 1)
- **worktree_branch** (from Step 1)
- **resolved_source_branch** (from Step 2)
- **strategy** (from parameters)

#### Actions

**Strategy: merge**
- [ ] Run `git -C <worktree_path> merge <resolved_source_branch>`
- [ ] Capture the output and check for conflicts

**Strategy: rebase**
- [ ] Run `git -C <worktree_path> rebase <resolved_source_branch>`
- [ ] Capture the output and check for conflicts

#### Outputs
- **update_success**: Boolean
- **update_output**: Output from the git command
- **strategy_used**: "merge" or "rebase"
- **conflicts**: Array of conflicting files (if any)
- **commits_applied**: Number of commits applied/merged
- **new_head**: The new HEAD commit SHA after the update

#### Validation
- [ ] **update_success** is true

**CRITICAL STOP CONDITION**: If conflicts occur during **merge**, **STOP** and report:
```
Merge conflicts detected when merging '<sourceBranch>' into '<worktree_branch>':

  <list of conflicting files>

The merge is in progress in the worktree at <worktree_path>.
Resolve the conflicts there, then run:
  cd <worktree_path>
  git add .
  git commit

Note: Uncommitted changes were stashed. After resolving, run `git stash pop` to restore them.
```

**CRITICAL STOP CONDITION**: If conflicts occur during **rebase**, **STOP** and report:
```
Rebase conflicts detected when rebasing '<worktree_branch>' onto '<sourceBranch>':

  <list of conflicting files>

The rebase is in progress in the worktree at <worktree_path>.
Resolve the conflicts there, then run:
  cd <worktree_path>
  git add .
  git rebase --continue

To abort the rebase and return to the original state:
  git -C <worktree_path> rebase --abort

Note: Uncommitted changes were stashed. After completing the rebase, run `git stash pop` to restore them.
```

### Step 5: Restore Working State

#### Inputs
- **update_success** (from Step 4)
- **stash_created** (from Step 3)
- **worktree_path** (from Step 1)

#### Actions
- [ ] If **stash_created** is true and **update_success** is true:
  - Pop the stash: `git -C <worktree_path> stash pop`
  - If the stash pop has conflicts, warn the user
- [ ] If **update_success** is false and **stash_created** is true:
  - Inform the user that their changes are still in the stash
  - Provide the command to restore: `git -C <worktree_path> stash pop`

#### Outputs
- **stash_restored**: Boolean
- **stash_conflicts**: Boolean — whether the stash pop had conflicts

### Step 6: Report Results

#### Inputs
- All outputs from previous steps

#### Actions
- [ ] Run `git -C <worktree_path> log --oneline -5` to show recent commits
- [ ] Summarize what was done

#### Outputs
Report to the user:
- Which worktree was updated
- Source branch used
- Strategy used (merge or rebase)
- Number of new commits incorporated
- Whether uncommitted changes were stashed and restored
- Recent commits on the worktree's branch

## Response Format

Present a clear summary:

```
Worktree updated:

  Worktree: <worktree_name> (<worktree_path>)
  Branch: <worktree_branch>
  Source: <resolved_source_branch>
  Strategy: <merge / rebase>
  Commits incorporated: <count>
  Stash: <restored / not needed / still stashed (conflicts)>

  Recent commits on <worktree_branch>:
  <git log output>
```

## Error Handling

### WorktreeNotFoundError

**When it occurs:** No worktree matches the provided name.

```
No worktree found matching '<name>'.

Available worktrees:
<list>
```

### SourceBranchNotFoundError

**When it occurs:** The specified source branch does not exist.

```
Source branch '<sourceBranch>' does not exist.
Specify an existing branch to pull changes from.
```

### DetachedHeadError

**When it occurs:** The worktree is in detached HEAD state.

```
Worktree '<name>' is in detached HEAD state.
Cannot update a detached HEAD. Check out a branch first.
```

### MergeConflictError

**When it occurs:** The merge produces conflicts.

```
Merge conflicts detected. Resolve in the worktree, then:
  git add . && git commit
```

### RebaseConflictError

**When it occurs:** The rebase produces conflicts.

```
Rebase conflicts detected. Resolve in the worktree, then:
  git add . && git rebase --continue

To abort: git rebase --abort
```

### AlreadyUpToDate

**When it occurs:** No new commits on the source branch. This is informational, not an error.

```
Worktree '<name>' is already up to date with '<sourceBranch>'.
```

## Examples

### Example 1: Rebase onto Main (Default)

**Parameters:** `name="my-feature"`

**Result:**
```
Worktree updated:

  Worktree: my-feature (/Users/me/Sites/my-app/.worktrees/my-feature)
  Branch: feature/dev/my-feature
  Source: main
  Strategy: rebase
  Commits incorporated: 3
  Stash: not needed

  Recent commits on feature/dev/my-feature:
  abc1234 My latest feature change
  def5678 Add feature scaffolding
  ghi9012 Latest commit from main
  jkl3456 Previous main commit
```

### Example 2: Merge from Develop

**Parameters:** `name="my-feature"`, `sourceBranch="develop"`, `strategy="merge"`

**Result:**
```
Worktree updated:

  Worktree: my-feature (/Users/me/Sites/my-app/.worktrees/my-feature)
  Branch: feature/dev/my-feature
  Source: develop
  Strategy: merge
  Commits incorporated: 5
  Stash: restored

  Recent commits on feature/dev/my-feature:
  abc1234 Merge branch 'develop' into feature/dev/my-feature
  def5678 My feature work
  ghi9012 Latest develop commit
```

### Example 3: Already Up to Date

**Parameters:** `name="my-feature"`, `sourceBranch="main"`

**Result:**
```
Worktree 'my-feature' is already up to date with 'main'.
No changes to incorporate.
```

### Example 4: Rebase with Conflicts

**Parameters:** `name="experiment"`, `sourceBranch="main"`, `strategy="rebase"`

**Result:**
```
Rebase conflicts detected when rebasing 'feature/dev/experiment' onto 'main':

  src/config.ts
  src/utils/helpers.ts

The rebase is in progress in the worktree at /Users/me/Sites/my-app/.worktrees/experiment.
Resolve the conflicts there, then run:
  cd /Users/me/Sites/my-app/.worktrees/experiment
  git add .
  git rebase --continue

To abort the rebase and return to the original state:
  git -C /Users/me/Sites/my-app/.worktrees/experiment rebase --abort

Note: Uncommitted changes were stashed. After completing the rebase, run `git stash pop` to restore them.
```

### Example 5: Update Without Fetching

**Parameters:** `name="my-feature"`, `sourceBranch="main"`, `fetch=false`

**Result:**
```
Worktree updated:

  Worktree: my-feature (/Users/me/Sites/my-app/.worktrees/my-feature)
  Branch: feature/dev/my-feature
  Source: main (local only, no fetch)
  Strategy: rebase
  Commits incorporated: 2
  Stash: not needed

  Recent commits on feature/dev/my-feature:
  abc1234 My feature change
  def5678 Recent main commit
```

## Notes

- The default strategy is `rebase` because it produces a cleaner commit history for feature branches
- `git fetch` runs by default to ensure the source branch is up to date with the remote — use `fetch=false` to skip this if working offline or with local-only branches
- Uncommitted changes are automatically stashed before the operation and restored afterward
- If stash restoration conflicts with the updated branch, the stash remains applied but with conflict markers — the user must resolve manually
- Rebase rewrites commit history — if the worktree's branch has been pushed to a remote, the user will need to force-push afterward (`git push --force-with-lease`)
- The source branch itself is never modified — changes flow one way, from source into the worktree's branch
