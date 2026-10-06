# worktrees

Cursor git worktree configuration — sets up project-local worktree storage with symlinks and setup hooks.

## Why use this?

Run several branches in parallel without the pain — no hidden global worktree directories, no re-installing dependencies by hand, no fear of clobbering uncommitted work. This package makes worktrees a first-class, team-shareable, one-command workflow that keeps every parallel checkout close to your project and ready to build.

- **Worktrees live with your project** — `setup` moves storage into `<project-root>/.worktrees/` (symlinked from Cursor's global path and gitignored), so parallel checkouts are visible, discoverable, and no longer buried in `~/.cursor/`.
- **New worktrees are ready to run instantly** — setup hooks in a committed `.cursor/worktrees.json` run automatically on `create` (e.g. `npm install`, `promp i`), so a fresh worktree builds without manual setup — and the whole team shares the same config.
- **Full lifecycle, one namespace** — `create`, `createAndSwitch`, `remove`, `merge`, `update`, and `switch` cover the entire worktree flow, including creating feature branches, rebasing/merging in upstream changes, and switching Cursor's active workspace.
- **Deterministic, tested git operations** — worktree creation and target resolution are performed by bundled, unit-tested shell scripts (not ad-hoc commands), so the tricky sequences behave the same every time — including a rollback guarantee for failed branch creation.
- **Guards your uncommitted work** — `remove` warns on unpushed commits and uncommitted changes before deleting, and `update` stashes and restores local edits around a merge or rebase, so you don't lose work spinning worktrees up and down.
- **Perfect for parallel and best-of-n runs** — each skill is directly callable by other agents, making it easy to fan work out across isolated checkouts and later merge the winner back.

## Installation

```bash
promp install worktrees
```

## Problem

By default, Cursor stores git worktrees in `~/.cursor/worktrees/<project-name>/`. This has two downsides:

1. Worktree data is hidden away in a global directory, disconnected from the project
2. There is no way to share worktree setup hooks (dependency installation, etc.) across the team without manual configuration

This package solves both by:
- Moving worktree storage into `<project-root>/.worktrees/` with a symlink from the global path
- Creating a `.cursor/worktrees.json` file that defines setup commands to run when new worktrees are created

## Prompts

### setup

Configure Cursor git worktrees for the current project.

**Usage:**

```bash
/worktrees.setup
```

**What it does:**
1. Creates a `.worktrees/` directory in the project root
2. Symlinks `~/.cursor/worktrees/<project-name>` to point to it
3. Migrates any existing worktrees from the global directory
4. Auto-detects setup commands from project dependency files (package.json, requirements.txt, etc.)
5. Creates or updates `.cursor/worktrees.json` with the setup commands
6. Adds `.worktrees/` to `.gitignore`

**Parameters:**
- `projectRoot` (string, optional): Absolute path to the project root. Defaults to current workspace.
- `setupCommands` (array, optional): Override auto-detected setup commands. Example: `["npm ci", "promp i"]`

### create

Create a new git worktree — optionally creating a **new feature branch** for it.

**Usage:**

```bash
# New feature branch (created with the detached-HEAD-first technique)
/worktrees.create newBranch="feature/dev/new-thing"

# Existing branch, custom directory name
/worktrees.create branch="feature/dev/my-feature" name="experiment"

# New branch based on a specific start point
/worktrees.create newBranch="feature/dev/hotfix" startPoint="origin/main"

# Detached HEAD, no branch
/worktrees.create detach=true
```

**What it does:**
1. Validates that worktrees are configured for the project (run `setup` first)
2. Creates the worktree in `.worktrees/<name>` using the bundled `worktree-create.sh` script
3. When creating a **new branch**, it first creates the worktree on a detached HEAD, then creates the branch inside it — and **rolls back the worktree if branch creation fails**, so no orphaned worktree is left behind
4. Runs `worktrees.json` setup commands in the new worktree (e.g., `npm install`)

**Parameters (pass at most one branch mode):**
- `newBranch` (string, optional): Name of a new feature branch to create (detached-HEAD-first, with rollback). Follow the `feature/{environment}/{feature-name}` convention where applicable.
- `branch` (string, optional): An existing branch, tag, or commit to check out.
- `detach` (boolean, optional): Create the worktree at a detached HEAD with no branch. Default: `false`.
- `startPoint` (string, optional): Base ref for `newBranch`/`detach`/default mode. Defaults to current `HEAD`.
- `name` (string, optional): Directory name for the worktree. Auto-derived from the branch if not provided.
- `skipSetup` (boolean, optional): Skip running setup commands. Default: `false`.

If no branch mode is given, a new branch named after the worktree directory is created.

### createAndSwitch

Create a new worktree (optionally on a new feature branch), run setup hooks, and switch the active workspace to it — the create + switch flow in one command.

**Usage:**

```bash
/worktrees.createAndSwitch newBranch="feature/dev/payment-retry"
/worktrees.createAndSwitch branch="feature/dev/existing-work" name="review"
```

**What it does:**
1. Creates the worktree (same script and rollback guarantee as `create`)
2. Runs `worktrees.json` setup commands
3. Switches the active workspace to the new worktree — inside Cursor via `cursor-app-control.move_agent_to_root`, otherwise by printing the `cd` command

The switch is best-effort: a failed switch never invalidates a successfully created worktree.

**Parameters (pass at most one branch mode):**
- `newBranch` (string, optional): Name of a new feature branch to create.
- `branch` (string, optional): An existing branch, tag, or commit to check out.
- `startPoint` (string, optional): Base ref for `newBranch`. Defaults to current `HEAD`.
- `name` (string, optional): Directory name for the worktree.
- `skipSetup` (boolean, optional): Skip running setup commands. Default: `false`.

### remove

Remove a git worktree and clean up its directory.

**Usage:**

```bash
/worktrees.remove name="my-feature"
/worktrees.remove name="experiment" force=true
/worktrees.remove
```

**What it does:**
1. Identifies the worktree by name (or lists available worktrees for selection)
2. Checks for uncommitted changes and unpushed commits
3. Warns and asks for confirmation if there is unsaved work (unless `force=true`)
4. Removes the worktree via `git worktree remove` and prunes metadata

**Parameters:**
- `name` (string, optional): Name or path of the worktree. If omitted, lists worktrees interactively.
- `force` (boolean, optional): Force removal even with uncommitted changes. Default: `false`.

### merge

Merge a worktree's branch into a target branch.

**Usage:**

```bash
/worktrees.merge name="my-feature" targetBranch="main"
/worktrees.merge name="hotfix" targetBranch="main" deleteAfterMerge=true
/worktrees.merge name="experiment" targetBranch="develop" noFastForward=true
```

**What it does:**
1. Identifies the worktree and its branch
2. Checks for uncommitted changes in the worktree
3. Finds where the target branch is checked out (main working tree, another worktree, or nowhere)
4. Performs the merge from the target branch's location
5. Optionally removes the worktree after a successful merge

**Parameters:**
- `name` (string, optional): Name of the worktree to merge from. If omitted, lists worktrees interactively.
- `targetBranch` (string, required): The branch to merge into (e.g., `"main"`, `"develop"`).
- `noFastForward` (boolean, optional): Force a merge commit even when fast-forward is possible. Default: `false`.
- `deleteAfterMerge` (boolean, optional): Remove the worktree after a successful merge. Default: `false`.

### update

Update a worktree's branch to include changes from another branch.

**Usage:**

```bash
/worktrees.update name="my-feature"
/worktrees.update name="my-feature" sourceBranch="develop" strategy="merge"
/worktrees.update name="experiment" sourceBranch="main" strategy="rebase" fetch=false
```

**What it does:**
1. Identifies the worktree and its branch
2. Fetches the latest remote state (unless `fetch=false`)
3. Stashes any uncommitted changes in the worktree
4. Merges or rebases the source branch into the worktree's branch
5. Restores stashed changes

**Parameters:**
- `name` (string, optional): Name of the worktree to update. If omitted, lists worktrees interactively.
- `sourceBranch` (string, optional): The branch to pull changes from. Defaults to the repository's default branch (`main` or `master`).
- `strategy` (string, optional): `"merge"` or `"rebase"`. Default: `"rebase"`.
- `fetch` (boolean, optional): Fetch from remote before updating. Default: `true`.

### switch

Switch the active workspace to a different git worktree.

**Usage:**

```bash
/worktrees.switch name="my-feature"
/worktrees.switch name="fix/login-bug"
/worktrees.switch
```

**What it does:**
1. Lists all current worktrees and resolves the target by name, path, or branch (or asks the user to pick if no name is provided)
2. Detects whether the agent is running inside Cursor by checking for the `cursor-app-control` MCP server
3. **Inside Cursor:** Calls `cursor-app-control.move_agent_to_root` to redirect Cursor's UI to the worktree path. New terminals will open in the new worktree directory.
4. **Outside Cursor:** Prints the `cd <worktree_path>` command for the user to run manually (a tool call cannot change the user's interactive shell cwd)
5. Reports the new active worktree, branch, and how to switch back

**Parameters:**
- `name` (string, optional): Name, path, or branch of the worktree to switch to. If omitted, lists worktrees interactively.

**Returns:** The new active worktree path, branch, and the method used (`cursor-mcp` or `manual-cd`).

**See:** [prompts/switch.md](./prompts/switch.md)

## Skills

### setup-worktrees

The full worktree setup workflow. Automatically loaded by the `setup` prompt.

### create-worktree

The full worktree creation workflow. Automatically loaded by the `create` prompt. Drives the bundled `scripts/worktree-create.sh` script for the git-level creation.

### create-and-switch-worktree

The combined create-then-switch workflow. Automatically loaded by the `createAndSwitch` prompt. Composes the `create-worktree` and `switch-worktree` scripts.

### remove-worktree

The full worktree removal workflow. Automatically loaded by the `remove` prompt.

### merge-worktree

The full worktree merge workflow. Automatically loaded by the `merge` prompt.

### update-worktree

The full worktree update workflow. Automatically loaded by the `update` prompt.

### switch-worktree

The full worktree switch workflow, including Cursor environment detection and `cursor-app-control` MCP integration. Automatically loaded by the `switch` prompt. Drives the bundled `scripts/worktree-resolve.sh` script for worktree enumeration and target resolution.

All skills can also be used directly by agents that need worktree operations as part of a larger workflow (e.g., best-of-n runners).

## Bundled Scripts & Testing

The git-level operations are owned by tested shell scripts so the sequences are deterministic and consistent:

| Script | Skill | Responsibility |
|--------|-------|----------------|
| `scripts/worktree-create.sh` | `create-worktree` | Create a worktree in any mode; new-branch flow uses detached-HEAD-first with rollback |
| `scripts/worktree-resolve.sh` | `switch-worktree` | Enumerate worktrees and resolve a switch target (name/branch/symlinked-path) |

Each script ships with a test harness that builds throwaway git repos and asserts on behavior and every error code. Run them from the package directory:

```bash
npm run test:scripts
# or individually:
bash skills/create-worktree/scripts/test-worktree-create.sh
bash skills/switch-worktree/scripts/test-worktree-resolve.sh
```

## worktrees.json

The `.cursor/worktrees.json` file tells Cursor what commands to run when setting up a new worktree. It is committed to the repository so all team members share the same configuration.

**Format:**

```json
{
  "setup-worktree": [
    "npm install",
    "promp i"
  ]
}
```

The `setup-worktree` array contains shell commands that run sequentially when a new worktree is created. Typical use cases:
- Installing dependencies (`npm install`, `pip install -r requirements.txt`)
- Installing promp packages (`promp i`)
- Running build steps or code generation

## Directory Structure

After running `setup`, a project will have:

```
my-project/
├── .cursor/
│   └── worktrees.json    # Setup hooks (committed)
├── .worktrees/            # Worktree storage (gitignored)
│   └── <worktree-id>/    # Individual worktrees
├── .gitignore             # Updated with .worktrees/
└── ...
```

And in the global Cursor directory:

```
~/.cursor/worktrees/
└── my-project -> /path/to/my-project/.worktrees   # Symlink
```

## Version History

### 1.3.0
- Added `createAndSwitch` prompt and `create-and-switch-worktree` skill: create a worktree (optionally on a new feature branch) and switch to it in one flow
- Enhanced `create` with explicit branch options — `newBranch`, `branch`, `detach`, and `startPoint`
- New feature branches are now created with the **detached-HEAD-first technique**: create the worktree detached, then create the branch inside it, with automatic **rollback** if branch creation fails (no more orphaned worktrees)
- Extracted git operations into bundled, unit-tested scripts (`worktree-create.sh`, `worktree-resolve.sh`) with test harnesses (`npm run test:scripts`)

### 1.2.0
- Added `switch` prompt and `switch-worktree` skill for switching the active workspace between worktrees
- Inside Cursor, uses the `cursor-app-control` MCP server to redirect Cursor's UI to the new worktree path; outside Cursor, prints the `cd` command for manual use

### 1.1.0
- Added `merge` prompt and `merge-worktree` skill for merging worktree branches into target branches
- Added `update` prompt and `update-worktree` skill for syncing worktrees with upstream branches (merge or rebase)

### 1.0.0
- Initial release
- Setup worktrees skill and prompt
- Auto-detection of setup commands from project dependency files

## License

MIT

## Author

Pennymac AI Platform
