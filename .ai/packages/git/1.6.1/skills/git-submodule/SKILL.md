---
name: git-submodule
description: Add, update, and remove git submodules — including init on add, latest-remote tracking on update, safe deinit-and-cleanup on remove, and submodule status reporting. Use when the user wants to attach, refresh, or detach a git repository embedded as a submodule (for example knowledge bases under .kbs/).
---

# Git Submodule Operations

Add, update, and remove git submodules safely, with initialization, latest-remote tracking, and complete metadata cleanup.

## Overview

This skill automates the three git submodule operations that callers need:

1. **Add** — register a repository as a submodule at a target path and initialize it (optionally tracking a branch/ref).
2. **Update** — advance one or all submodules to the latest commit on their tracked branch.
3. **Remove** — detach a submodule and clean up every piece of git metadata it leaves behind.

Each operation reports submodule status (up-to-date vs behind) and returns a structured JSON result. Only the operation requested by the calling prompt is executed. All work is pure git — no external services are contacted beyond the submodule's own remote.

## Operation Selection

The calling prompt specifies exactly one operation: `add`, `update`, or `remove`. Execute only that operation's workflow, then return the matching success JSON (or an error JSON). Never run a different operation than the one requested.

## Critical Error Handling Requirements

**IMPORTANT**: When any error occurs during a submodule operation, **IMMEDIATELY STOP** execution and return a structured JSON error response matching one of the schemas in [Error Handling](#error-handling). Do not continue with partial operations.

**ABSOLUTELY FORBIDDEN**: Never run `git reset --hard`, `git clean -fd` outside the explicit remove-cleanup steps below, or any command that irreversibly destroys uncommitted work in the superproject or in a submodule working tree. When a submodule working tree is dirty, stop and return `DirtyWorktreeError` rather than discarding changes.

**DO NOT** return a success JSON when an error occurs. **ONLY** return the appropriate error JSON.

## Parameters

The parameters available depend on the selected operation.

- **{{repositoryUrl}}** (string, required for `add`): The URL of the repository to attach as a submodule.
- **{{path}}**:
  - For `add` (string, required): Target path for the submodule, e.g. `.kbs/<name>`.
  - For `update` (string, optional): A single submodule path to update. When omitted, all submodules are updated.
  - For `remove` (string, required): The submodule path to remove.
- **{{ref}}** (string, optional, `add` only): Branch or ref the submodule should track. When omitted, the remote's default branch is used.

## Reading Submodule Status

Use these commands to determine submodule state before and after operations:

- `git submodule status [-- <path>]` — the leading character of each line indicates state:
  - ` ` (space): the checked-out commit matches the commit recorded in the superproject (in sync).
  - `+`: the checked-out commit differs from the recorded commit (the submodule moved; the superproject has a pending gitlink change).
  - `-`: the submodule is not initialized.
  - `U`: the submodule has merge conflicts.
- To detect whether a submodule is **behind its tracked branch**: run `git -C <path> fetch` then compare `git -C <path> rev-parse HEAD` against `git -C <path> rev-parse @{upstream}` (or `origin/<ref>`). Equal hashes mean up-to-date; different means behind.
- To list all registered submodule paths: `git config --file .gitmodules --get-regexp '^submodule\..*\.path$'`.

## Add Workflow

### Step 1: Validate the target path is not already a submodule

#### Inputs
- **repositoryUrl** (required)
- **path** (required)
- **ref** (optional)

#### Actions
- [ ] Confirm the current directory is a git repository: `git rev-parse --is-inside-work-tree`.
- [ ] Check whether `path` is already a registered submodule: `git submodule status -- <path>` and `git config --file .gitmodules --get-regexp "^submodule\..*\.path$"`.
- [ ] Check whether `path` already exists on disk as a non-empty directory or tracked entry.

#### Outputs
- **already_submodule**: Boolean indicating the path is already a submodule.

#### Validation
- [ ] **already_submodule** is false and the path is free to use.

**CRITICAL STOP CONDITION**: If `path` is already a submodule (or a non-empty, conflicting path), **IMMEDIATELY RETURN** a `SubmoduleExistsError` JSON response and **STOP**:
```json
{
  "code": "SUBMODULE_EXISTS",
  "message": "A submodule already exists at the target path",
  "path": "<path>"
}
```

### Step 2: Add and initialize the submodule

#### Inputs
- **repositoryUrl**, **path**, **ref** (from parameters)

#### Actions
- [ ] **Scenario A** (`ref` provided): run `git submodule add -b <ref> -- <repositoryUrl> <path>`.
- [ ] **Scenario B** (no `ref`): run `git submodule add -- <repositoryUrl> <path>`.
- [ ] Initialize recursively to be safe: `git submodule update --init --recursive -- <path>`.
- [ ] Capture the command output and exit code.

#### Outputs
- **add_success**: Boolean indicating the add + init succeeded.
- **add_output**: Full output from the add/init commands.

#### Validation
- [ ] **add_success** is true.

**CRITICAL STOP CONDITION — repository not found / unreachable**: If the add fails because the repository does not exist, cannot be cloned, or authentication is refused, **IMMEDIATELY RETURN** a `RepoNotFoundError` JSON response:
```json
{
  "code": "REPO_NOT_FOUND",
  "message": "The submodule repository could not be found or cloned",
  "repositoryUrl": "<repositoryUrl>"
}
```

**CRITICAL STOP CONDITION — any other add failure**: If the add fails for any other reason, **IMMEDIATELY RETURN** an `AddFailedError` JSON response:
```json
{
  "code": "ADD_FAILED",
  "message": "Failed to add the submodule",
  "addOutput": "Full output from the failed git submodule add command"
}
```

### Step 3: Report the result

#### Inputs
- **path**, **ref** (from parameters)

#### Actions
- [ ] Resolve the tracked ref: the provided `ref`, or the submodule's default branch (`git -C <path> rev-parse --abbrev-ref HEAD`).
- [ ] Resolve the checked-out commit: `git -C <path> rev-parse HEAD`.
- [ ] Return the Add success JSON.

> The submodule and the updated `.gitmodules` are now staged in the superproject. This workflow does not create a commit — the caller decides when to commit the new submodule.

## Update Workflow

### Step 1: Resolve the update target(s)

#### Inputs
- **path** (optional)

#### Actions
- [ ] Confirm the current directory is a git repository.
- [ ] **Scenario A** (`path` provided): verify it is a registered submodule via `git submodule status -- <path>`.
- [ ] **Scenario B** (no `path`): collect all submodule paths via `git config --file .gitmodules --get-regexp "^submodule\..*\.path$"`.

#### Outputs
- **targets**: Array of submodule paths to update.

#### Validation
- [ ] **targets** is non-empty (for Scenario A, the path resolves to a real submodule).

**CRITICAL STOP CONDITION**: If a specific `path` was provided but is not a registered submodule, **IMMEDIATELY RETURN** a `SubmoduleNotFoundError` JSON response and **STOP**:
```json
{
  "code": "SUBMODULE_NOT_FOUND",
  "message": "No submodule is registered at the given path",
  "path": "<path>"
}
```

### Step 2: Guard against dirty submodule working trees

#### Inputs
- **targets** (from Step 1)

#### Actions
- [ ] For each target, run `git -C <target> status --porcelain` to detect uncommitted changes inside the submodule.

#### Outputs
- **dirty_targets**: Array of `{ path, dirtyFiles }` for any submodule with local changes.

#### Validation
- [ ] **dirty_targets** is empty before proceeding.

**CRITICAL STOP CONDITION**: If any target submodule has a dirty working tree, **IMMEDIATELY RETURN** a `DirtyWorktreeError` JSON response and **STOP** (never discard the local changes):
```json
{
  "code": "DIRTY_WORKTREE",
  "message": "Submodule has uncommitted changes; refusing to update",
  "path": "<path>",
  "dirtyFiles": ["list", "of", "modified", "files"]
}
```

### Step 3: Update each target to the latest tracked commit

#### Inputs
- **targets** (from Step 1)

#### Actions
- [ ] For each target, record the previous commit: `git -C <target> rev-parse HEAD`.
- [ ] Update to the latest commit on the tracked branch:
  - For a single target: `git submodule update --remote --recursive -- <target>`.
  - For all submodules: `git submodule update --remote --recursive`.
- [ ] For each target, record the new commit: `git -C <target> rev-parse HEAD`.
- [ ] Summarize changed files between previous and new commit: `git -C <target> diff --name-only <previous>..<new>` (count or list).

#### Outputs
- **updated**: Array of `{ path, previousRef, newRef, changedFiles }` (one entry per target; `previousRef === newRef` means already up-to-date).

#### Validation
- [ ] Every target produced a `previousRef` and `newRef`.

**CRITICAL STOP CONDITION**: If the update command fails for any target, **IMMEDIATELY RETURN** an `UpdateFailedError` JSON response:
```json
{
  "code": "UPDATE_FAILED",
  "message": "Failed to update the submodule(s) to the latest remote commit",
  "updateOutput": "Full output from the failed git submodule update --remote command"
}
```

### Step 4: Report the result

#### Actions
- [ ] Return the Update success JSON with the per-submodule `updated` array.

> When a submodule advances, the superproject now has a pending gitlink change. This workflow does not commit it — the caller decides when to commit the updated pointer.

## Remove Workflow

### Step 1: Verify the submodule exists

#### Inputs
- **path** (required)

#### Actions
- [ ] Confirm the current directory is a git repository.
- [ ] Verify `path` is a registered submodule: `git submodule status -- <path>` and a matching entry in `.gitmodules`.

#### Outputs
- **is_submodule**: Boolean indicating the path is a registered submodule.

#### Validation
- [ ] **is_submodule** is true.

**CRITICAL STOP CONDITION**: If `path` is not a registered submodule, **IMMEDIATELY RETURN** a `SubmoduleNotFoundError` JSON response and **STOP**:
```json
{
  "code": "SUBMODULE_NOT_FOUND",
  "message": "No submodule is registered at the given path",
  "path": "<path>"
}
```

### Step 2: Deinitialize and remove

#### Inputs
- **path** (required)

#### Actions
- [ ] Deinitialize the submodule (force handles a populated working tree): `git submodule deinit -f -- <path>`.
- [ ] Remove the submodule from the index and working tree (this also drops its `.gitmodules` entry): `git rm -f -- <path>`.
- [ ] Remove the stored git directory: `rm -rf .git/modules/<path>`.
- [ ] If `.gitmodules` still contains a stale section for the path, remove it with `git config --file .gitmodules --remove-section submodule.<path>` and stage `.gitmodules`.
- [ ] Capture the output and exit codes of each command.

#### Outputs
- **remove_success**: Boolean indicating the removal succeeded.
- **cleaned_paths**: Array of paths cleaned — the working tree `<path>`, the `.gitmodules` entry, and `.git/modules/<path>`.
- **remove_output**: Full output from the removal commands.

#### Validation
- [ ] **remove_success** is true.
- [ ] `git submodule status -- <path>` no longer lists the submodule.
- [ ] `.git/modules/<path>` no longer exists.

**CRITICAL STOP CONDITION**: If any removal step fails, **IMMEDIATELY RETURN** a `RemoveFailedError` JSON response:
```json
{
  "code": "REMOVE_FAILED",
  "message": "Failed to fully remove the submodule",
  "removeOutput": "Full output from the failed removal commands"
}
```

### Step 3: Report the result

#### Actions
- [ ] Return the Remove success JSON listing the cleaned paths.

> The submodule removal (including the `.gitmodules` change) is now staged in the superproject. This workflow does not commit it — the caller decides when to commit the removal.

## Response Format

Return the success JSON for the operation that was executed.

### Add — Success Response

```json
{
  "success": true,
  "path": ".kbs/handbook",
  "ref": "main",
  "commit": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0"
}
```

**Field Descriptions:**
- `success`: Always `true` on success.
- `path`: The submodule path that was added.
- `ref`: The tracked branch/ref (provided `ref` or the resolved default branch).
- `commit`: The commit SHA the submodule is checked out at.

### Update — Success Response

```json
{
  "success": true,
  "updated": [
    {
      "path": ".kbs/handbook",
      "previousRef": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
      "newRef": "f0e9d8c7b6a5f4e3d2c1b0a9f8e7d6c5b4a39281",
      "changedFiles": 7
    }
  ]
}
```

**Field Descriptions:**
- `success`: Always `true` on success.
- `updated`: One entry per submodule that was processed.
  - `path`: The submodule path.
  - `previousRef`: The commit SHA before the update.
  - `newRef`: The commit SHA after the update (equal to `previousRef` if already current).
  - `changedFiles`: Number of files changed between `previousRef` and `newRef`.

### Remove — Success Response

```json
{
  "success": true,
  "path": ".kbs/handbook",
  "cleanedPaths": [
    ".kbs/handbook",
    ".gitmodules entry: submodule..kbs/handbook",
    ".git/modules/.kbs/handbook"
  ]
}
```

**Field Descriptions:**
- `success`: Always `true` on success.
- `path`: The submodule path that was removed.
- `cleanedPaths`: The metadata locations that were cleaned during removal.

## Error Handling

When any error occurs, execution **IMMEDIATELY STOPS** and only the error JSON is returned.

### SubmoduleExistsError (`add`)

Returned when the target path is already a registered submodule or a conflicting non-empty path.

```json
{
  "code": "SUBMODULE_EXISTS",
  "message": "A submodule already exists at the target path",
  "path": ".kbs/handbook"
}
```

### RepoNotFoundError (`add`)

Returned when the submodule repository cannot be found, cloned, or authenticated.

```json
{
  "code": "REPO_NOT_FOUND",
  "message": "The submodule repository could not be found or cloned",
  "repositoryUrl": "git@github.com:org/handbook.git"
}
```

### AddFailedError (`add`)

Returned when `git submodule add` fails for any other reason.

```json
{
  "code": "ADD_FAILED",
  "message": "Failed to add the submodule",
  "addOutput": "fatal: <git output>"
}
```

### SubmoduleNotFoundError (`update`, `remove`)

Returned when a specified path is not a registered submodule.

```json
{
  "code": "SUBMODULE_NOT_FOUND",
  "message": "No submodule is registered at the given path",
  "path": ".kbs/handbook"
}
```

### UpdateFailedError (`update`)

Returned when `git submodule update --remote` fails.

```json
{
  "code": "UPDATE_FAILED",
  "message": "Failed to update the submodule(s) to the latest remote commit",
  "updateOutput": "fatal: <git output>"
}
```

### DirtyWorktreeError (`update`)

Returned when a submodule has uncommitted changes, so updating could discard work.

```json
{
  "code": "DIRTY_WORKTREE",
  "message": "Submodule has uncommitted changes; refusing to update",
  "path": ".kbs/handbook",
  "dirtyFiles": ["notes/draft.md"]
}
```

### RemoveFailedError (`remove`)

Returned when the submodule cannot be fully removed.

```json
{
  "code": "REMOVE_FAILED",
  "message": "Failed to fully remove the submodule",
  "removeOutput": "fatal: <git output>"
}
```

## Examples

### Example 1: Add a knowledge base submodule tracking a branch

**Operation:** `add`

**Input:**
```json
{
  "repositoryUrl": "git@github.com:org/handbook.git",
  "path": ".kbs/handbook",
  "ref": "main"
}
```

**Output:**
```json
{
  "success": true,
  "path": ".kbs/handbook",
  "ref": "main",
  "commit": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0"
}
```

### Example 2: Update a single submodule to latest

**Operation:** `update`

**Input:**
```json
{
  "path": ".kbs/handbook"
}
```

**Output:**
```json
{
  "success": true,
  "updated": [
    {
      "path": ".kbs/handbook",
      "previousRef": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
      "newRef": "f0e9d8c7b6a5f4e3d2c1b0a9f8e7d6c5b4a39281",
      "changedFiles": 7
    }
  ]
}
```

### Example 3: Update all submodules

**Operation:** `update`

**Input:**
```json
{}
```

**Output:**
```json
{
  "success": true,
  "updated": [
    {
      "path": ".kbs/handbook",
      "previousRef": "a1b2c3d4",
      "newRef": "f0e9d8c7",
      "changedFiles": 7
    },
    {
      "path": ".kbs/policies",
      "previousRef": "9c8b7a6d",
      "newRef": "9c8b7a6d",
      "changedFiles": 0
    }
  ]
}
```

### Example 4: Remove a submodule

**Operation:** `remove`

**Input:**
```json
{
  "path": ".kbs/handbook"
}
```

**Output:**
```json
{
  "success": true,
  "path": ".kbs/handbook",
  "cleanedPaths": [
    ".kbs/handbook",
    ".gitmodules entry: submodule..kbs/handbook",
    ".git/modules/.kbs/handbook"
  ]
}
```

### Example 5: Error — update a dirty submodule

**Operation:** `update`

**Error Output:**
```json
{
  "code": "DIRTY_WORKTREE",
  "message": "Submodule has uncommitted changes; refusing to update",
  "path": ".kbs/handbook",
  "dirtyFiles": ["notes/draft.md"]
}
```

## Notes

**Important Considerations:**
- Each operation leaves the resulting change (new submodule, advanced pointer, or removal) **staged but uncommitted** in the superproject. Committing is the caller's responsibility — pair with the `commit` prompt when a commit is desired.
- `update` uses `--remote`, which moves the submodule to the latest commit on its tracked branch; without a tracked branch it follows the remote's default branch.
- `remove` performs the full cleanup sequence (`deinit` → `git rm` → delete `.git/modules/<path>`), which is what leaves no orphaned metadata behind.

**Safety:**
- Never run destructive resets (`git reset --hard`, `git clean -fd` outside the documented remove steps) to force an operation through. Return the appropriate error instead.
- A dirty submodule working tree halts an update with `DirtyWorktreeError` so local work is never silently discarded.

**Git Commands Used:**
- `git submodule status [-- <path>]` — inspect submodule state
- `git config --file .gitmodules --get-regexp '^submodule\..*\.path$'` — list submodule paths
- `git submodule add [-b <ref>] -- <url> <path>` — add a submodule
- `git submodule update --init --recursive -- <path>` — initialize after add
- `git submodule update --remote --recursive [-- <path>]` — update to latest tracked commit
- `git -C <path> rev-parse HEAD` / `@{upstream}` — read submodule commits
- `git -C <path> status --porcelain` — detect a dirty submodule working tree
- `git -C <path> diff --name-only <prev>..<new>` — summarize changed files
- `git submodule deinit -f -- <path>` — deinitialize before removal
- `git rm -f -- <path>` — remove from index/working tree and `.gitmodules`
- `rm -rf .git/modules/<path>` — delete the stored submodule git directory
