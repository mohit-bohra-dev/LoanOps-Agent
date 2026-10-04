# Git Workflow Prompts

A collection of AI-powered prompts for automating common Git workflows including intelligent commit message generation, automatic push handling, and merge conflict resolution.

## Why use this?

Git ceremony — writing commit messages, un-sticking failed pre-commit hooks, rebasing around a diverged remote, untangling conflicts — eats focus on every change. This package automates the whole commit-to-ship loop so you stay on the actual work.

- **Never hand-write a commit message again** — analyzes your staged diff and generates a clear, conventional-commit message automatically.
- **Pre-commit hooks fix themselves** — when a commit hook fails on lint/format/type errors, it applies the fixes and retries instead of dumping the failure on you.
- **Ship in one step** — `commitAndPush` and `commitPullPush` chain commit, rebase-pull, and push, handling a diverged remote and simple merge conflicts along the way.
- **Zero-data-loss pulls** — `pull` stashes local work, rebases for linear history, restores it, and resolves stash-pop conflicts; it never runs a destructive `reset --hard`.
- **Consistent branch names** — `createBranch` builds `feature/[environment]/[feature-name]` names for you and can push with upstream tracking in the same step.
- **Submodules without the footguns** — add, update, and remove submodules with recursive init, dirty-tree safety (refuses to discard uncommitted work), and full `.git/modules` cleanup.

## Installation

```bash
promp install git
```

## Included Prompts

### `commitAndPush`

Automatically commit staged changes with an AI-generated commit message and push to the current branch. This prompt intelligently handles:

- **AI-Generated Commit Messages** - Analyzes your changes and creates clear, descriptive commit messages following conventional commit format
- **Pre-Commit Hook Handling** - Automatically fixes linting, formatting, and type errors from pre-commit hooks
- **Smart Push Management** - Handles remote changes and merge conflicts automatically
- **Merge Conflict Resolution** - Attempts intelligent auto-resolution of simple conflicts, asks for clarification on complex ones

### `pull`

Safely pull the latest remote changes while preserving any local work-in-progress. Uses a stash-based rebase workflow:

- **Stash-Based Safety** - Automatically stages and stashes all local changes before pulling, then restores them afterward
- **Rebase for Linear History** - Uses `git pull --rebase` to keep a clean, linear commit history
- **Stash Pop Conflict Resolution** - Intelligently resolves conflicts between your stashed local work and newly pulled remote changes
- **Zero Data Loss Guarantee** - Never runs `git reset --hard` or any destructive command; local work is always preserved

### `createBranch`

Create and switch to a new Git branch, with built-in support for the standard feature branch naming convention (`feature/[environment]/[feature-name]`).

- **Feature Branch Mode** - Provide a `featureName` and optional `environment` to auto-construct the branch name
- **Direct Mode** - Provide an exact `branchName` for non-feature branches
- **Auto-Push** - Optionally push the new branch and set upstream tracking in one step

### `addSubmodule`

Add a git repository as a submodule at a target path and initialize it. Useful for attaching knowledge bases or shared repos (for example under `.kbs/`).

- **Optional Branch Tracking** - Pass a `ref` to track a specific branch; otherwise the remote's default branch is used
- **Auto-Init** - Runs `git submodule update --init --recursive` so the submodule is ready immediately
- **Structured Result** - Returns the submodule path, tracked ref, and checked-out commit

### `updateSubmodule`

Update one or all submodules to the latest commit on their tracked branch.

- **Single or All** - Pass a `path` to update one submodule, or omit it to update every submodule
- **Dirty-Tree Safety** - Refuses to update a submodule with uncommitted changes (returns `DirtyWorktreeError`) instead of discarding work
- **Change Summary** - Reports each submodule's previous → new commit and the number of changed files

### `removeSubmodule`

Remove a submodule and clean up its git metadata.

- **Complete Cleanup** - Runs `deinit` → `git rm` → removes `.git/modules/<path>` so no orphaned metadata is left behind
- **`.gitmodules` Maintenance** - Drops the submodule's `.gitmodules` entry as part of removal
- **Structured Result** - Returns the removed path and the list of cleaned metadata locations

## Rules

### `branchingStructure`

Defines the Git branching convention for feature branches. Always applied.

Feature branches follow the format: `feature/[environment]/[feature-name]`

**Valid environments:** `dev`, `dev2`, `qa`, `qa2`, `stg`, `prod`

**Examples:**
```text
feature/dev/add-user-authentication
feature/qa/fix-payment-processing
feature/stg/update-dashboard-layout
feature/prod/hotfix-login-redirect
```

**See:** [rules/branching-structure.md](./rules/branching-structure.md)

## Usage

### Create Branch

Create a feature branch (defaults to `dev` environment):

```bash
/git.createBranch featureName=add-user-auth
```

Create a feature branch for a specific environment:

```bash
/git.createBranch featureName=fix-payment-flow environment=qa
```

Create a branch with an exact name:

```bash
/git.createBranch branchName=hotfix/critical-fix
```

Create and push a feature branch from a specific base:

```bash
/git.createBranch featureName=redesign-dashboard environment=dev2 baseBranch=develop push=true
```

### Commit and Push

First stage your changes.

```bash
git add .
```

Then simply run the prompt in Cursor or VS Code:

```bash
/git.commitAndPush
```

The prompt will:
1. Analyze your staged changes
2. Generate a descriptive commit message
3. Commit the changes
4. Push to your current branch

### Pull

Run the prompt to safely pull remote changes:

```bash
/git.pull
```

The prompt will:
1. Stage and stash any local changes
2. Pull remote changes with rebase
3. Restore your stashed changes
4. Resolve any conflicts from the stash pop

### Submodules

Add a repository as a submodule (optionally tracking a branch):

```bash
/git.addSubmodule repositoryUrl=git@github.com:org/handbook.git path=.kbs/handbook ref=main
```

Update a single submodule to the latest commit on its tracked branch:

```bash
/git.updateSubmodule path=.kbs/handbook
```

Update all submodules:

```bash
/git.updateSubmodule
```

Remove a submodule and clean up its metadata:

```bash
/git.removeSubmodule path=.kbs/handbook
```

Each submodule prompt leaves the resulting change (new submodule, advanced pointer, or removal) **staged but uncommitted** in the superproject, so you control when to commit it — pair with `/git.commit` when you want to commit the change.

### Verification Modes

Control git hook verification with the `verificationMode` parameter:

#### Full Verification (Default)
Run all pre-commit and push hooks:
```yaml
verificationMode: "full"
```

#### Skip All Verification
Skip both commit and push hooks:
```yaml
verificationMode: "no-verify"
```

#### Skip Commit Verification Only
Skip pre-commit hooks but run push hooks:
```yaml
verificationMode: "no-verify-commit"
```

#### Skip Push Verification Only
Run pre-commit hooks but skip push hooks:
```yaml
verificationMode: "no-verify-push"
```

## Features

### Intelligent Commit Messages

The prompt analyzes your changes and generates commit messages that:
- Follow conventional commit format (feat:, fix:, chore:, etc.)
- Summarize the high-level purpose of changes
- Group related changes together
- Use imperative mood

**Example Generated Messages:**
```yaml
feat: add user authentication with JWT tokens
fix: resolve validation errors in login form
chore: update dependencies and apply linting fixes
```

### Automatic Pre-Commit Fix Handling

When pre-commit hooks fail (linting, formatting, type errors):
1. Analyzes the error output
2. Fixes all reported issues
3. Stages the fixed files
4. Regenerates commit message to include both original changes AND fixes
5. Retries the commit

**Example Flow:**
```text
Original changes: Added login feature
→ Pre-commit fails: ESLint errors detected
→ Fixes applied: Auto-fix ESLint issues
→ New commit message: "feat: add login feature and fix linting errors"
```

### Smart Merge Conflict Resolution

When pushing fails due to remote changes:
1. Runs `git pull --rebase` to fetch remote changes
2. If conflicts occur:
   - Analyzes conflicted files
   - Reviews incoming commit messages
   - Attempts automatic resolution for simple conflicts
   - **Asks for clarification** on complex conflicts

**Auto-Resolvable Conflicts:**
- Changes in different functions/methods
- Non-overlapping additions (imports, new functions)
- Formatting changes vs. logic changes
- Documentation updates vs. code changes

**Requires User Input:**
- Same function modified differently
- Different logic for same operation
- Conflicting API changes
- Configuration changes with different values

## Response Format

### Success Response

```json
{
  "success": true,
  "commitHash": "a1b2c3d4",
  "commitMessage": "feat: add user authentication flow",
  "branch": "feature/auth",
  "filesChanged": 5,
  "mergeConflictsResolved": false,
  "preCommitFixesApplied": false,
  "fixesApplied": []
}
```

### With Pre-Commit Fixes

```json
{
  "success": true,
  "commitHash": "e5f6g7h8",
  "commitMessage": "fix: resolve validation errors and apply linting fixes",
  "branch": "main",
  "filesChanged": 3,
  "mergeConflictsResolved": false,
  "preCommitFixesApplied": true,
  "fixesApplied": [
    "Fixed ESLint errors in auth.ts",
    "Applied Prettier formatting to login.tsx"
  ]
}
```

## Error Handling

### Automatic Retry Errors

These errors are automatically fixed and retried:
- **Pre-commit hook failures** - Linting, formatting, type errors
- **Push rejections due to remote changes** - Resolved via rebase

### Stop and Report Errors

These errors stop execution and are reported:
- **No staged changes** - Nothing to commit
- **Push hook failures** - Must be manually resolved
- **Network errors** - Connection issues
- **Authentication failures** - Credential issues
- **Protected branch violations** - Permission issues

### Complex Merge Conflict Errors

When conflicts are too complex to auto-resolve, you'll receive:
- List of conflicted files
- Description of local vs. remote changes
- Incoming commit messages for context
- Specific clarifying questions

**Example Clarification Request:**
```text
Merge conflict in src/auth.ts

Your version: function calculate() { return a + b; }
Remote version: function calculate() { return a * b; }

Incoming commits:
- "fix: update calculation to use multiplication"

Question: Should calculate() add or multiply? Your version adds, 
but the remote version multiplies. Which approach is correct for 
the current requirements?
```

## Git Commands Used

The prompt uses these git commands under the hood:
- `git status --porcelain` - Check staged files and conflicts
- `git diff --cached` - Analyze changes
- `git branch --show-current` - Get current branch
- `git commit` - Create commit (with optional --no-verify)
- `git push` - Push to remote (with optional --no-verify)
- `git pull --rebase` - Fetch and rebase remote changes
- `git log origin/<branch> --not HEAD` - View incoming commits
- `git rebase --continue` - Continue after conflict resolution

## Important Notes

- **Only commits staged files** - Does not auto-stage unstaged changes
- **Respects git hooks by default** - Only skips when explicitly requested
- **Linear history via rebase** - Uses rebase strategy for clean history
- **Never retries push hook failures** - These must be manually resolved
- **Rewrites commit message after fixes** - Includes both original changes and hook fixes

## Pull Workflow Details

### How It Works

The `pull` prompt follows this safe sequence:

```bash
git add -A          → Stage all local changes
git stash push      → Stash them with a labeled message
git pull --rebase   → Pull remote changes with rebase
git stash pop       → Restore your stashed changes
```

If the working tree is already clean, the stash/pop steps are skipped entirely.

### Pull Response Format

#### Success Response

```json
{
  "success": true,
  "branch": "feature/auth",
  "newCommitsPulled": true,
  "stashUsed": true,
  "mergeConflictsResolved": false,
  "resolvedFiles": []
}
```

#### With Auto-Resolved Conflicts

```json
{
  "success": true,
  "branch": "feature/auth",
  "newCommitsPulled": true,
  "stashUsed": true,
  "mergeConflictsResolved": true,
  "resolvedFiles": ["src/config.ts", "src/utils/helpers.ts"]
}
```

### Pull Error Handling

- **Stash failures** - Reported immediately if git stash fails
- **Network/auth errors** - Stashed changes are restored before reporting the error
- **Rebase failures** - Rebase is aborted and stashed changes are restored
- **Complex stash pop conflicts** - Reports conflicted files with clarifying questions for the user

### Pull Safety Guarantees

- **Never runs `git reset --hard`** or any destructive command
- Stashed changes are always restored, even on failure paths
- Uses a labeled stash (`promp-pull-autostash`) for easy manual recovery
- Prefers aborting and returning an error over any action that could lose work

## Examples

### Example 1: Simple Feature Addition

```text
Staged changes:
- src/components/Button.tsx (new file)
- src/styles/button.css (new file)

Generated message:
"feat: add reusable Button component with custom styling"

Result: Committed and pushed successfully
```

### Example 2: Bug Fix with Linting Issues

```text
Staged changes:
- src/utils/validation.ts (modified)

Pre-commit hook fails:
- ESLint: Unused variable 'temp'
- ESLint: Missing return type

Fixes applied automatically:
- Removed unused variable
- Added return type annotation

Generated message:
"fix: correct email validation logic and resolve linting errors"

Result: Committed and pushed successfully
```

### Example 3: Merge Conflict Resolution

```text
Staged changes:
- src/auth/login.ts (added login function)

Push fails: Remote has new commits

Incoming commits:
- "feat: add logout functionality"

Conflicts detected in: src/auth/login.ts

Auto-resolution:
- Both added non-overlapping functions
- Kept both login() and logout() functions

Generated message:
"feat: add login functionality"

Result: Rebased, conflicts resolved, pushed successfully
```

## Best Practices

1. **Stage intentionally** - Only stage the files you want to commit
2. **Review generated messages** - Verify the AI-generated commit message is accurate
3. **Use appropriate verification mode** - Default to full verification unless you have a specific reason to skip
4. **Understand conflict resolution** - Review auto-resolved conflicts to ensure correctness
5. **Keep commits focused** - Smaller, focused changes lead to better commit messages

## Troubleshooting

### "No staged changes" error
**Solution:** Stage your changes with `git add` before running the prompt

### Pre-commit hook keeps failing
**Solution:** Check the hook output for issues that can't be auto-fixed, or use `verificationMode: "no-verify-commit"` temporarily

### Push hook failure
**Solution:** Push hooks cannot be auto-fixed. Review the hook output and resolve manually, then retry

### Complex merge conflict
**Solution:** Answer the clarification questions, or resolve conflicts manually using `git rebase --abort` and standard git workflow

### Stash pop conflict after pull
**Solution:** Answer the clarification questions provided by the `pull` prompt. If you need to resolve manually, the conflict markers are left in the affected files and the stash entry remains available via `git stash list`

### Authentication failure
**Solution:** Verify your git credentials and remote URL are correct

## Skills

### `git-commit`

Defines the canonical commit process: analyzing staged changes, generating conventional commit messages, performing the commit, and automatically handling pre-commit hook failures. This skill is the source of truth for how the commit workflow operates and is referenced by the `commit`, `commitAndPush`, and `commitPullPush` prompts.

**Capabilities:**
- Staged change analysis and categorization
- Conventional commit message generation (feat:, fix:, chore:, etc.)
- Automatic pre-commit hook failure detection and fixing (linting, formatting, type errors)
- Retry logic with up to 3 fix-stage-recommit cycles
- Configurable hook verification modes

**See:** [skills/git-commit/SKILL.md](./skills/git-commit/SKILL.md)

### `git-submodule`

Defines the canonical submodule operations: adding and initializing a submodule, updating one or all submodules to their latest tracked commit, and safely removing a submodule with full metadata cleanup. This skill is the source of truth for how submodule workflows operate and is referenced by the `addSubmodule`, `updateSubmodule`, and `removeSubmodule` prompts.

**Capabilities:**
- Add with optional branch/ref tracking and recursive init
- Update to latest remote with dirty-working-tree protection
- Safe removal via `deinit` → `git rm` → `.git/modules` cleanup
- Submodule status reporting (in-sync vs behind vs uninitialized)
- Structured JSON results and error handling for every operation

**See:** [skills/git-submodule/SKILL.md](./skills/git-submodule/SKILL.md)

## Version

Current version: 1.6.0

## License

MIT

## Author

Pennymac AI Platform

## Keywords

git, commit, push, pull, rebase, stash, merge, workflow, automation, ai-generated-commits, conflict-resolution
