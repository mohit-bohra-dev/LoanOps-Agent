---
promp:
  package: "git"
  version: "1.6.1"
  environment: "development"
  prompVersion: "1.0.1-beta.83"
  prompt: "commitPullPush"
---
# git.commitPullPush

Commit staged changes, pull remote changes with rebase, and push — a complete sync-and-ship workflow

## Parameter Specifications

- **`verificationMode`** (string) - *Optional*
  - Controls git hook verification behavior
  - Default: `full`

## Instructions

You are executing a Promp package prompt. Follow these steps:

1. **Parse the user input** to extract parameters:
   - Parameter 1: `verificationMode` (optional) [default: full] - Controls git hook verification behavior

2. **Replace parameter placeholders** in the prompt content below:
   - Parameters use the format `{{parameterName}}` in the prompt
   - Replace each placeholder with the corresponding parsed value
   - If a parameter is optional and not provided, use its default value (if specified)
   - If a required parameter is missing, ask the user to provide it

3. **Execute the prompt** with the replaced parameters

## Usage

When the user invokes this command, they may provide parameters in various ways:
- Space-separated values: `/git.commitPullPush value1 value2`
- Named parameters: `/git.commitPullPush param1=value1 param2=value2`
- Mixed format: `/git.commitPullPush value1 param2=value2`

Parse flexibly and map values to the expected parameters in order for positional arguments.

## Expected Output

Result of the commit, pull, and push operation

**Type:** `object`

**Properties:**

- `success` (boolean) - **Required** - Whether the operation completed successfully
- `commitHash` (string) - **Required** - The Git commit hash (SHA) of the created commit
- `commitMessage` (string) - **Required** - The generated commit message that was used
- `branch` (string) - **Required** - The branch name that was pushed to
- `filesChanged` (number) - *Optional* - Number of files changed in the commit
- `preCommitFixesApplied` (boolean) - *Optional* - Whether pre-commit hook failures required fixes
- `fixesApplied` (array) - *Optional* - List of fixes that were applied due to pre-commit hooks
- `newCommitsPulled` (boolean) - *Optional* - Whether new commits were fetched from remote during pull
- `mergeConflictsResolved` (boolean) - *Optional* - Whether merge conflicts from the pull were encountered and resolved
## Error Handling

### NoStagedChangesError

Error when there are no staged changes to commit

**Properties:**

- `code` (string) (values: ["NO_STAGED_CHANGES"]) - 
- `message` (string) - 

### PreCommitHookError

Error when pre-commit hook fails and cannot be automatically fixed

**Properties:**

- `code` (string) (values: ["PRE_COMMIT_HOOK_FAILED"]) - 
- `message` (string) - 
- `hookOutput` (string) - The output from the failed pre-commit hook
- `failedChecks` (array) - List of checks that failed

### CommitMessageGenerationError

Error when AI fails to generate a suitable commit message

**Properties:**

- `code` (string) (values: ["COMMIT_MESSAGE_GENERATION_FAILED"]) - 
- `message` (string) - 
- `reason` (string) - Reason why commit message generation failed

### StashError

Error when git stash fails during pull

**Properties:**

- `code` (string) (values: ["STASH_FAILED"]) - 
- `message` (string) - 
- `stashOutput` (string) - The output from the failed stash command

### PullError

Error when git pull --rebase fails

**Properties:**

- `code` (string) (values: ["PULL_FAILED"]) - 
- `message` (string) - 
- `pullOutput` (string) - The output from the failed pull command
- `recoverySteps` (array) - Suggested recovery steps

### StashPopConflictError

Error when stash pop produces merge conflicts too complex to auto-resolve

**Properties:**

- `code` (string) (values: ["STASH_POP_CONFLICT"]) - 
- `message` (string) - 
- `conflictedFiles` (array) - List of files with unresolved conflicts
- `localChanges` (string) - Description of stashed local changes
- `remoteChanges` (string) - Description of newly pulled remote changes
- `clarificationNeeded` (string) - Specific questions that need user input to resolve

### RebaseError

Error when rebase fails during pull due to corrupted repository state

**Properties:**

- `code` (string) (values: ["REBASE_FAILED"]) - 
- `message` (string) - 
- `rebaseOutput` (string) - The output from the failed rebase operation
- `recoverySteps` (array) - Suggested recovery steps

### RemoteChangesError

Error when push is rejected because the remote has commits not present locally

**Properties:**

- `code` (string) (values: ["REMOTE_CHANGES_EXIST"]) - 
- `message` (string) - 
- `branch` (string) - The branch that was being pushed to
- `commitHash` (string) - The local commit hash that failed to push
- `pushOutput` (string) - The output from the rejected push command

### PushHookError

Error when push hook fails (not retried)

**Properties:**

- `code` (string) (values: ["PUSH_HOOK_FAILED"]) - 
- `message` (string) - 
- `hookOutput` (string) - The output from the failed push hook
- `commitHash` (string) - The commit hash that was created (commit succeeded but push failed)

### NetworkError

Error when network connectivity issues prevent pull or push

**Properties:**

- `code` (string) (values: ["NETWORK_ERROR"]) - 
- `message` (string) - 

### AuthenticationError

Error when authentication fails for remote repository

**Properties:**

- `code` (string) (values: ["AUTHENTICATION_FAILED"]) - 
- `message` (string) - 
- `remote` (string) - The remote URL that failed authentication

### ProtectedBranchError

Error when pushing to a protected branch without permissions

**Properties:**

- `code` (string) (values: ["PROTECTED_BRANCH"]) - 
- `message` (string) - 
- `branch` (string) - The protected branch name
- `requiredPermissions` (array) - List of required permissions

## Prompt Content

# Commit, Pull, Push

Commit staged changes, pull remote changes with rebase, and push to the remote — all in one workflow.

> **PREREQUISITE — YOU MUST DO THIS FIRST**
>
> Before performing any actions, you MUST read and load the following skills using the Read tool:
> - @./.cursor\skills\git-commit\SKILL.md — Contains the complete commit workflow used in Step 1
> - @./.cursor\skills\git-pull\SKILL.md — Contains the complete pull workflow used in Step 2
> - @./.cursor\skills\git-push\SKILL.md — Contains the complete push workflow used in Step 3
>
> Do NOT proceed until you have read all three skill files in full. Do NOT attempt to commit, pull, or push from memory or improvise the workflows. The skills are the sole source of truth for each process.

## Overview

This prompt orchestrates a complete sync-and-ship workflow by combining three standalone prompts in sequence:
1. **Commit** (@./.cursor\commands\git.commit.md) — Analyzes staged changes, generates a commit message, performs the commit, and handles pre-commit hook failures
2. **Pull** (@./.cursor\commands\git.pull.md) — Stashes any remaining local changes, pulls remote changes with rebase, restores the stash, and resolves merge conflicts
3. **Push** (@./.cursor\commands\git.push.md) — Pushes to the remote origin

By pulling between commit and push, this workflow ensures the local branch is up to date with the remote before pushing, which avoids push rejections due to diverged history. Each step must succeed before the next begins. If any step fails, execution stops immediately and the error is returned.

This prompt is the recommended workflow for the common pattern of "save my work, sync with the team, and share."

## Parameters

- **{{verificationMode}}** (string, optional): Controls git hook verification behavior
  - Default value: `"full"`
  - Allowed values: `"full"`, `"no-verify"`, `"no-verify-commit"`, `"no-verify-push"`
  - `"full"`: Run all hooks normally on both commit and push
  - `"no-verify"`: Use `--no-verify` on both commit and push
  - `"no-verify-commit"`: Use `--no-verify` on commit only; push hooks run normally
  - `"no-verify-push"`: Use `--no-verify` on push only; commit hooks run normally

## Instructions

Perform a complete commit-pull-push operation by executing the three prompts in sequence:

### Step 1: Commit

**First, follow the commit process defined in @./.cursor\commands\git.commit.md** — execute that entire workflow before proceeding.

#### Inputs
- **verificationMode** (from parameters, optional): Pass through to the commit prompt
  - Map `"full"` → `"full"`
  - Map `"no-verify"` → `"no-verify"`
  - Map `"no-verify-commit"` → `"no-verify-commit"`
  - Map `"no-verify-push"` → `"full"` (push-only skip does not affect commit)

#### Actions
- [ ] Execute the @./.cursor\commands\git.commit.md workflow with the mapped `verificationMode`
- [ ] Capture the commit result (success JSON or error JSON)

#### Outputs
- **commit_result**: The full JSON response from the commit prompt
- **commit_success**: Boolean indicating if the commit succeeded
- **commit_hash**: The SHA of the created commit (null if commit failed)
- **commit_message**: The generated commit message (null if commit failed)
- **files_changed**: Number of files in the commit
- **pre_commit_fixes_applied**: Boolean indicating if hook fixes were needed
- **fixes_applied**: Array of fix descriptions

#### Validation
- [ ] If **commit_success** is true, proceed to Step 2
- [ ] If the commit returned an error JSON, **IMMEDIATELY STOP** and return that error unchanged

**CRITICAL STOP CONDITION**: If the commit prompt returns any error (`NoStagedChangesError`, `PreCommitHookError`, or `CommitMessageGenerationError`), **IMMEDIATELY RETURN** that error JSON and **STOP ALL OPERATIONS**. Do not proceed to pull or push.

### Step 2: Pull

**Next, follow the pull process defined in @./.cursor\commands\git.pull.md** — execute that entire workflow to integrate remote changes before pushing.

#### Inputs
- No parameters — the pull prompt takes no inputs

#### Actions
- [ ] Execute the @./.cursor\commands\git.pull.md workflow
- [ ] Capture the pull result (success JSON or error JSON)

#### Outputs
- **pull_result**: The full JSON response from the pull prompt
- **pull_success**: Boolean indicating if the pull succeeded
- **new_commits_pulled**: Boolean indicating if new commits were fetched
- **merge_conflicts_resolved**: Boolean indicating if stash pop conflicts were resolved

#### Validation
- [ ] If **pull_success** is true, proceed to Step 3
- [ ] If the pull returned an error JSON, **IMMEDIATELY STOP** and return that error unchanged

**CRITICAL STOP CONDITION**: If the pull prompt returns any error (`StashError`, `PullError`, `StashPopConflictError`, `NetworkError`, `AuthenticationError`, or `RebaseError`), **IMMEDIATELY RETURN** that error JSON and **STOP ALL OPERATIONS**. Do not proceed to push.

### Step 3: Push

**Finally, follow the push process defined in @./.cursor\commands\git.push.md** — execute that entire workflow.

#### Inputs
- **verificationMode** (from parameters, optional): Pass through to the push prompt
  - Map `"full"` → `"full"`
  - Map `"no-verify"` → `"no-verify"`
  - Map `"no-verify-push"` → `"no-verify-push"`
  - Map `"no-verify-commit"` → `"full"` (commit-only skip does not affect push)

#### Actions
- [ ] Execute the @./.cursor\commands\git.push.md workflow with the mapped `verificationMode`
- [ ] Capture the push result (success JSON or error JSON)

#### Outputs
- **push_result**: The full JSON response from the push prompt
- **push_success**: Boolean indicating if the push succeeded

#### Validation
- [ ] If **push_success** is true, proceed to Step 4
- [ ] If the push returned an error JSON, **IMMEDIATELY STOP** and return that error unchanged

**CRITICAL STOP CONDITION**: If the push prompt returns any error (`RemoteChangesError`, `PushHookError`, `NetworkError`, `AuthenticationError`, or `ProtectedBranchError`), **IMMEDIATELY RETURN** that error JSON and **STOP ALL OPERATIONS**.

### Step 4: Return Combined Success

#### Inputs
- **commit_hash** (from Step 1)
- **commit_message** (from Step 1)
- **files_changed** (from Step 1)
- **pre_commit_fixes_applied** (from Step 1)
- **fixes_applied** (from Step 1)
- **new_commits_pulled** (from Step 2)
- **merge_conflicts_resolved** (from Step 2)
- **push_result** (from Step 3)

#### Actions
- [ ] Get the branch name from the push result
- [ ] Combine results from all three steps into the unified success response

#### Outputs
- Return the success JSON matching the Response Format schema

#### Validation
- [ ] **success** is true
- [ ] **commitHash** is a valid git SHA
- [ ] **branch** is not empty
- [ ] Output matches the returns schema exactly

## Response Format

This prompt returns structured JSON output.

### Success Response

```json
{
  "success": true,
  "commitHash": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0",
  "commitMessage": "feat: add user authentication with JWT tokens",
  "branch": "feature/auth",
  "filesChanged": 5,
  "preCommitFixesApplied": false,
  "fixesApplied": [],
  "newCommitsPulled": true,
  "mergeConflictsResolved": false
}
```

**Field Descriptions:**
- `success`: Always `true` for successful commit-pull-push operations
- `commitHash`: The Git commit SHA that was pushed
- `commitMessage`: The AI-generated commit message that was used
- `branch`: The branch name that was pushed to
- `filesChanged`: Number of files included in the commit
- `preCommitFixesApplied`: Whether pre-commit hook failures were encountered and fixed
- `fixesApplied`: Array of human-readable descriptions of each fix applied (empty if none)
- `newCommitsPulled`: Whether new commits were fetched from the remote during pull
- `mergeConflictsResolved`: Whether merge conflicts from the pull were encountered and resolved

## Error Handling

This prompt may return errors from the commit, pull, or push step. When any error occurs, execution **IMMEDIATELY STOPS** and only the error JSON is returned.

### Commit Errors (delegated to @./.cursor\commands\git.commit.md)

#### NoStagedChangesError

Returned when there are no staged changes to commit.

```json
{
  "code": "NO_STAGED_CHANGES",
  "message": "No staged changes found to commit. Use 'git add' to stage files before committing."
}
```

**When it occurs:** No files have been staged with `git add`

#### PreCommitHookError

Returned when pre-commit hook fails and cannot be automatically fixed.

```json
{
  "code": "PRE_COMMIT_HOOK_FAILED",
  "message": "Pre-commit hook failed with unfixable errors",
  "hookOutput": "Full output from the failed pre-commit hook",
  "failedChecks": ["eslint", "type-check"]
}
```

**When it occurs:** Hook errors persist after automatic fix attempts

#### CommitMessageGenerationError

Returned when the AI fails to generate a suitable commit message.

```json
{
  "code": "COMMIT_MESSAGE_GENERATION_FAILED",
  "message": "Failed to generate commit message from staged changes",
  "reason": "Unable to analyze diff output"
}
```

**When it occurs:** Changes are too complex or incoherent to summarize

### Pull Errors (delegated to @./.cursor\commands\git.pull.md)

#### StashError

Returned when git stash fails.

```json
{
  "code": "STASH_FAILED",
  "message": "Failed to stash local changes",
  "stashOutput": "Full output from the failed stash command"
}
```

**When it occurs:** Git stash encounters an error before the pull can proceed

#### PullError

Returned when git pull --rebase fails.

```json
{
  "code": "PULL_FAILED",
  "message": "git pull --rebase failed",
  "pullOutput": "Full output from the failed pull command",
  "recoverySteps": ["Run 'git rebase --abort'", "Manually resolve conflicts"]
}
```

**When it occurs:** Rebase conflicts during pull are too complex to auto-resolve

#### StashPopConflictError

Returned when stash pop produces merge conflicts too complex to auto-resolve.

```json
{
  "code": "STASH_POP_CONFLICT",
  "message": "Stash pop produced merge conflicts that require user input",
  "conflictedFiles": ["src/auth.ts"],
  "localChanges": "Description of stashed local changes",
  "remoteChanges": "Description of newly pulled remote changes",
  "clarificationNeeded": "Specific question for the user"
}
```

**When it occurs:** Pulled changes conflict with uncommitted local work

#### RebaseError

Returned when rebase fails during pull due to corrupted repository state.

```json
{
  "code": "REBASE_FAILED",
  "message": "Rebase operation failed during pull",
  "rebaseOutput": "Full output from the failed rebase operation",
  "recoverySteps": ["Run 'git rebase --abort'", "Run 'git stash pop'"]
}
```

**When it occurs:** Internal git error or corrupted state during rebase

### Push Errors (delegated to @./.cursor\commands\git.push.md)

#### RemoteChangesError

Returned when the remote has diverged since the pull. This is unlikely in normal usage since pull runs immediately before push.

```json
{
  "code": "REMOTE_CHANGES_EXIST",
  "message": "Push rejected: the remote branch has commits that are not present locally. Run the 'pull' command first.",
  "branch": "feature/auth",
  "commitHash": "a1b2c3d4",
  "pushOutput": "Full output from the rejected push command"
}
```

**When it occurs:** Another developer pushed between the pull and push steps (rare)

#### PushHookError

Returned when a push hook fails. Never retried.

```json
{
  "code": "PUSH_HOOK_FAILED",
  "message": "Push hook failed. Manual intervention required.",
  "hookOutput": "Full output from the failed push hook",
  "commitHash": "a1b2c3d4"
}
```

**When it occurs:** A pre-push hook script exits with a non-zero code

#### NetworkError

Returned when network connectivity issues prevent pull or push.

```json
{
  "code": "NETWORK_ERROR",
  "message": "Failed to connect to remote due to network connectivity issues"
}
```

**When it occurs:** Cannot reach the remote host (can occur during pull or push step)

#### AuthenticationError

Returned when authentication fails for the remote repository.

```json
{
  "code": "AUTHENTICATION_FAILED",
  "message": "Authentication to remote repository failed",
  "remote": "git@github.com:user/repo.git"
}
```

**When it occurs:** Credentials are invalid, expired, or missing (can occur during pull or push step)

#### ProtectedBranchError

Returned when pushing to a protected branch without permissions.

```json
{
  "code": "PROTECTED_BRANCH",
  "message": "Cannot push to protected branch without required permissions",
  "branch": "main",
  "requiredPermissions": ["push", "bypass-branch-protection"]
}
```

**When it occurs:** Branch protection rules prevent the push

## Examples

### Example 1: Clean Commit, Pull, Push

**Scenario:** Everything succeeds — no remote changes, no conflicts

**Input:**
```json
{
  "verificationMode": "full"
}
```

**Output:**
```json
{
  "success": true,
  "commitHash": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0",
  "commitMessage": "feat: add user authentication with JWT tokens",
  "branch": "feature/auth",
  "filesChanged": 5,
  "preCommitFixesApplied": false,
  "fixesApplied": [],
  "newCommitsPulled": false,
  "mergeConflictsResolved": false
}
```

### Example 2: Commit with Fixes, Pull with Remote Changes

**Scenario:** Pre-commit hooks fail and are fixed; pull integrates new remote commits cleanly

**Input:**
```json
{
  "verificationMode": "full"
}
```

**Output:**
```json
{
  "success": true,
  "commitHash": "b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0a1",
  "commitMessage": "fix: resolve validation errors and apply linting fixes",
  "branch": "main",
  "filesChanged": 3,
  "preCommitFixesApplied": true,
  "fixesApplied": [
    "Fixed ESLint errors in src/auth.ts",
    "Applied Prettier formatting to src/components/Login.tsx"
  ],
  "newCommitsPulled": true,
  "mergeConflictsResolved": false
}
```

### Example 3: Skip All Verification

**Scenario:** Commit and push with all hooks skipped

**Input:**
```json
{
  "verificationMode": "no-verify"
}
```

**Output:**
```json
{
  "success": true,
  "commitHash": "i9j0k1l2m3n4o5p6q7r8s9t0a1b2c3d4e5f6g7h8",
  "commitMessage": "chore: update dependencies",
  "branch": "develop",
  "filesChanged": 2,
  "preCommitFixesApplied": false,
  "fixesApplied": [],
  "newCommitsPulled": false,
  "mergeConflictsResolved": false
}
```

### Example 4: Error Case - Commit Fails (No Staged Changes)

**Scenario:** Nothing is staged — workflow stops at Step 1

**Error Output:**
```json
{
  "code": "NO_STAGED_CHANGES",
  "message": "No staged changes found to commit. Use 'git add' to stage files before committing."
}
```

### Example 5: Error Case - Pull Fails (Complex Stash Pop Conflict)

**Scenario:** Commit succeeds but pull produces merge conflicts that cannot be auto-resolved

**Error Output:**
```json
{
  "code": "STASH_POP_CONFLICT",
  "message": "Stash pop produced merge conflicts that require user input to resolve",
  "conflictedFiles": ["src/auth.ts"],
  "localChanges": "Uncommitted changes to auth validation logic",
  "remoteChanges": "Refactored auth module structure",
  "clarificationNeeded": "Both versions modify the auth validation. Which approach should be used?"
}
```

## Notes

**Important Considerations:**
- This prompt delegates entirely to @./.cursor\commands\git.commit.md, @./.cursor\commands\git.pull.md, and @./.cursor\commands\git.push.md — it does not duplicate their logic
- Each step must succeed before the next begins
- Error JSON from any sub-prompt is returned unchanged
- The `verificationMode` parameter is mapped appropriately for commit and push steps
- By pulling between commit and push, this avoids `RemoteChangesError` in most cases (it can still occur if a remote push happens in the brief window between pull and push)

**Best Practices:**
- Use this prompt as your default workflow when you want to commit and share changes
- Prefer this over `commitAndPush` when working on shared branches where others may have pushed
- Use `"full"` verification mode (default) to catch issues at both commit and push time

**Limitations:**
- Three-step workflow — if the commit succeeds but pull or push fails, the commit remains in local history
- Cannot undo the commit if a later step fails (use `git reset --soft HEAD~1` manually if needed)
- The pull step may encounter merge conflicts if remote changes overlap with uncommitted local work

