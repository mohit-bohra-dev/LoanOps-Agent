# Commit and Push

Commit staged changes with an AI-generated commit message and push to the current branch.

> **PREREQUISITE — YOU MUST DO THIS FIRST**
>
> Before performing any actions, you MUST read and load the following skills using the Read tool:
> - {{skill:git-commit}} — Contains the complete commit workflow used in Step 1
> - {{skill:git-push}} — Contains the complete push workflow used in Step 2
>
> Do NOT proceed until you have read both skill files in full. Do NOT attempt to commit or push from memory or improvise the workflows. The skills are the sole source of truth for each process.

## Overview

This prompt orchestrates a complete commit-and-push workflow by combining two standalone prompts:
1. **Commit** ({{prompt:commit}}) — Analyzes staged changes, generates a commit message, performs the commit, and handles pre-commit hook failures
2. **Push** ({{prompt:push}}) — Pushes to the remote origin, failing immediately if the remote has diverged

The two operations are executed in sequence. If the commit step fails, the push step is never attempted. If the push step fails because the remote has diverged, the user is instructed to run the `pull` command first. The `verificationMode` parameter is threaded through to both steps to control hook behavior independently.

This prompt is the default command for the git package and is equivalent to running `commit` followed by `push` with coordinated error handling and a unified success response.

## Parameters

- **{{verificationMode}}** (string, optional): Controls git hook verification behavior
  - Default value: `"full"`
  - Allowed values: `"full"`, `"no-verify"`, `"no-verify-commit"`, `"no-verify-push"`
  - `"full"`: Run all hooks normally on both commit and push
  - `"no-verify"`: Use `--no-verify` on both commit and push
  - `"no-verify-commit"`: Use `--no-verify` on commit only; push hooks run normally
  - `"no-verify-push"`: Use `--no-verify` on push only; commit hooks run normally

## Instructions

Perform a complete commit-and-push operation by executing the commit and push prompts in sequence:

### Step 1: Commit

**First, follow the commit process defined in {{prompt:commit}}** — execute that entire workflow before proceeding to push.

#### Inputs
- **verificationMode** (from parameters, optional): Pass through to the commit prompt
  - Map `"full"` → `"full"`
  - Map `"no-verify"` → `"no-verify"`
  - Map `"no-verify-commit"` → `"no-verify-commit"`
  - Map `"no-verify-push"` → `"full"` (push-only skip does not affect commit)

#### Actions
- [ ] Execute the {{prompt:commit}} workflow with the mapped `verificationMode`
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

**CRITICAL STOP CONDITION**: If the commit prompt returns any error (`NoStagedChangesError`, `PreCommitHookError`, or `CommitMessageGenerationError`), **IMMEDIATELY RETURN** that error JSON and **STOP ALL OPERATIONS**. Do not proceed to push.

### Step 2: Push

**Next, follow the push process defined in {{prompt:push}}** — execute that entire workflow.

#### Inputs
- **verificationMode** (from parameters, optional): Pass through to the push prompt
  - Map `"full"` → `"full"`
  - Map `"no-verify"` → `"no-verify"`
  - Map `"no-verify-push"` → `"no-verify-push"`
  - Map `"no-verify-commit"` → `"full"` (commit-only skip does not affect push)

#### Actions
- [ ] Execute the {{prompt:push}} workflow with the mapped `verificationMode`
- [ ] Capture the push result (success JSON or error JSON)

#### Outputs
- **push_result**: The full JSON response from the push prompt
- **push_success**: Boolean indicating if the push succeeded

#### Validation
- [ ] If **push_success** is true, proceed to Step 3
- [ ] If the push returned an error JSON, **IMMEDIATELY STOP** and return that error unchanged

**CRITICAL STOP CONDITION**: If the push prompt returns any error (`RemoteChangesError`, `PushHookError`, `NetworkError`, `AuthenticationError`, or `ProtectedBranchError`), **IMMEDIATELY RETURN** that error JSON and **STOP ALL OPERATIONS**.

### Step 3: Return Combined Success

#### Inputs
- **commit_hash** (from Step 1)
- **commit_message** (from Step 1)
- **files_changed** (from Step 1)
- **pre_commit_fixes_applied** (from Step 1)
- **fixes_applied** (from Step 1)
- **push_result** (from Step 2)

#### Actions
- [ ] Get the branch name from the push result
- [ ] Combine commit and push results into the unified success response

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
  "fixesApplied": []
}
```

**Field Descriptions:**
- `success`: Always `true` for successful commit-and-push operations
- `commitHash`: The Git commit SHA that was pushed
- `commitMessage`: The AI-generated commit message that was used
- `branch`: The branch name that was pushed to
- `filesChanged`: Number of files included in the commit
- `preCommitFixesApplied`: Whether pre-commit hook failures were encountered and fixed
- `fixesApplied`: Array of human-readable descriptions of each fix applied (empty if none)

## Error Handling

This prompt may return errors from either the commit or push step. When any error occurs, execution **IMMEDIATELY STOPS** and only the error JSON is returned.

### Commit Errors (delegated to {{prompt:commit}})

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

### Push Errors (delegated to {{prompt:push}})

#### RemoteChangesError

Returned when the remote branch has commits not present locally. The user must run `pull` first.

```json
{
  "code": "REMOTE_CHANGES_EXIST",
  "message": "Push rejected: the remote branch has commits that are not present locally. Run the 'pull' command first to integrate remote changes, then retry the push.",
  "branch": "feature/auth",
  "commitHash": "a1b2c3d4",
  "pushOutput": "To github.com:user/repo.git\n ! [rejected] feature/auth -> feature/auth (non-fast-forward)"
}
```

**When it occurs:** Remote has newer commits since the last pull

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

Returned when network connectivity issues prevent push.

```json
{
  "code": "NETWORK_ERROR",
  "message": "Failed to push to remote due to network connectivity issues",
  "commitHash": "a1b2c3d4"
}
```

**When it occurs:** Cannot reach the remote host

#### AuthenticationError

Returned when authentication fails for the remote repository.

```json
{
  "code": "AUTHENTICATION_FAILED",
  "message": "Authentication to remote repository failed",
  "remote": "git@github.com:user/repo.git"
}
```

**When it occurs:** Credentials are invalid, expired, or missing

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

### Example 1: Simple Commit and Push

**Scenario:** Everything succeeds on the first attempt

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
  "fixesApplied": []
}
```

### Example 2: Commit with Pre-Commit Fixes

**Scenario:** Pre-commit hooks fail and are automatically fixed, then push succeeds

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
  ]
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
  "fixesApplied": []
}
```

### Example 4: Error Case - Commit Fails (No Staged Changes)

**Scenario:** Nothing is staged — commit step fails immediately, push is never attempted

**Error Output:**
```json
{
  "code": "NO_STAGED_CHANGES",
  "message": "No staged changes found to commit. Use 'git add' to stage files before committing."
}
```

### Example 5: Error Case - Push Rejected (Remote Has Diverged)

**Scenario:** Commit succeeds but remote has newer commits

**Error Output:**
```json
{
  "code": "REMOTE_CHANGES_EXIST",
  "message": "Push rejected: the remote branch has commits that are not present locally. Run the 'pull' command first to integrate remote changes, then retry the push.",
  "branch": "feature/auth",
  "commitHash": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0",
  "pushOutput": "To github.com:user/repo.git\n ! [rejected] feature/auth -> feature/auth (non-fast-forward)"
}
```

## Notes

**Important Considerations:**
- This prompt delegates entirely to {{prompt:commit}} and {{prompt:push}} — it does not duplicate their logic
- If the commit step fails, the push step is never attempted
- If the push is rejected due to remote changes, the user must run `pull` first — the push does not attempt to rebase or resolve conflicts
- Error JSON from either sub-prompt is returned unchanged
- The `verificationMode` parameter is mapped appropriately for each step

**Best Practices:**
- Run the `pull` command before committing and pushing to avoid `RemoteChangesError`
- Use `"full"` verification mode (default) to catch issues at both commit and push time
- Use `"no-verify-commit"` to skip slow pre-commit hooks while still running push hooks
- Use `"no-verify-push"` to skip push hooks while still running commit hooks

**Limitations:**
- Combines two operations — if the commit succeeds but push fails, the commit remains in local history
- Cannot undo the commit if push fails (use `git reset --soft HEAD~1` manually if needed)
- Does not integrate remote changes — use the `pull` command to sync before retrying
