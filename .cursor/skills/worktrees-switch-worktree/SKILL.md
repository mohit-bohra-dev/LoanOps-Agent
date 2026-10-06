---
name: worktrees-switch-worktree
description: >-
  Switches the active workspace to a different git worktree. When running inside
  Cursor, uses the cursor-app-control MCP server to redirect Cursor's UI and the
  default terminal cwd to the new worktree path. Outside of Cursor, prints the
  cd command for the user to run manually. Use when the user wants to switch
  worktrees, change to a different worktree, or move the active workspace to a
  parallel working copy.
promp:
  package: "worktrees"
  version: "1.3.1"
  environment: "development"
  prompVersion: "1.0.1-beta.161"
  skill: "switch-worktree"
---

# Switch Worktree

Switch the active workspace to a different git worktree, updating Cursor's UI when available.

## Overview

This skill changes which worktree is the active workspace. It identifies the target worktree (by name, path, or interactive selection), detects whether the agent is running inside Cursor, and then either:

- **Inside Cursor:** Calls the `cursor-app-control.move_agent_to_root` MCP tool to redirect Cursor's UI to the new worktree path. New terminals will open with the worktree as their default working directory.
- **Outside Cursor:** Prints the `cd <worktree_path>` command for the user to run manually, since the skill cannot directly change the user's shell working directory.

The skill never modifies files or git state — it only changes which directory is the active workspace.

## Bundled Script

Worktree enumeration and target resolution are handled by a **tested script** — `scripts/worktree-resolve.sh`, located next to this skill file. Resolve its absolute path from wherever this `SKILL.md` was loaded (e.g. `.cursor/skills/switch-worktree/scripts/worktree-resolve.sh`, or `<packageRoot>/skills/switch-worktree/scripts/worktree-resolve.sh` after `promp i`). It owns the deterministic parts (listing, symlink-normalized matching, already-at-target detection) so they behave consistently; the actual Cursor UI move stays with the agent (Steps 3–4), since it requires an MCP call that cannot be scripted.

```bash
worktree-resolve.sh [--repo <repo>] [--query <name|branch|path>] [--current <active-path>]
```

- Always prints one `WT<TAB>path<TAB>head<TAB>branch<TAB>is_main<TAB>is_current` line per worktree.
- With `--query`, adds either `STATUS=resolved` (+ `TARGET_PATH`, `TARGET_BRANCH`, `TARGET_NAME`, `IS_MAIN`, `ALREADY_AT_TARGET`) or `STATUS=not_found`.
- The query is matched, in order, against: exact directory basename → exact branch → symlink-normalized full path → basename prefix.
- Exit codes: `0` resolved/listed, `1` query not found, `2` usage / not a git repo.

Parse this output rather than re-parsing `git worktree list` by hand.

## When to Use

- The user wants to switch to a different worktree
- The user asks to "switch worktrees", "change to worktree X", "open worktree X", or "move to worktree X"
- The user wants the IDE to point at a parallel working copy
- An agent has finished work in one worktree and needs to continue in another

## Parameters

- **{{name}}** (string, optional): Name or path of the worktree to switch to
  - Can be the short directory name (e.g., `"my-feature"`)
  - Can be a full path
  - Can be a branch name (the skill will find the worktree that has that branch checked out)
  - If omitted, the skill lists available worktrees and asks the user to choose

## Instructions

Switch to a different git worktree following this workflow:

### Step 1: Validate Prerequisites

#### Inputs
- **projectRoot** (current workspace root)

#### Actions
- [ ] Confirm the directory is a git repository
- [ ] Run `scripts/worktree-resolve.sh --repo <projectRoot> --current <projectRoot>` to enumerate all current worktrees (the `WT` lines) — this replaces hand-parsing `git worktree list`
- [ ] Determine the `.worktrees/` directory path (or symlink target)

#### Outputs
- **project_root**: Absolute path to the current workspace root
- **all_worktrees**: Parsed list of worktrees from `git worktree list`, each with `path`, `head`, `branch`
- **main_worktree_path**: Absolute path to the main working tree
- **worktrees_configured**: Boolean — whether the project has any additional worktrees beyond the main tree

#### Validation
- [ ] The directory is a valid git repository
- [ ] **all_worktrees** contains at least one entry

**CRITICAL STOP CONDITION**: If there are no additional worktrees (only the main working tree exists), **STOP** and inform the user:
```
No additional worktrees exist for this project.
Use /worktrees.create to create one first.
```

### Step 2: Resolve the Target Worktree

#### Inputs
- **name** (from parameters, optional)
- **all_worktrees** (from Step 1)
- **main_worktree_path** (from Step 1)
- **project_root** (from Step 1)

#### Actions
- [ ] If **name** is provided:
  - Run `scripts/worktree-resolve.sh --repo <projectRoot> --current <projectRoot> --query <name>`
  - The script matches (in order) directory basename → branch name → symlink-normalized full path → basename prefix, and returns the canonical `TARGET_PATH`, `TARGET_BRANCH`, `TARGET_NAME`, `IS_MAIN`, and `ALREADY_AT_TARGET`
  - If it returns `STATUS=not_found` (exit 1), STOP with `WorktreeNotFoundError` using the `WT` listing lines as the available options
- [ ] If **name** is NOT provided:
  - Run the script with no `--query` to get the `WT` listing (each line has path, head, branch, is_main, is_current)
  - Build a numbered list from those lines, marking the `is_current=true` worktree as `[current]`
  - Present the list to the user and ask which to switch to; wait for their selection
  - Re-run the script with `--query <selection>` to resolve the chosen target's canonical path
- [ ] The script already returns the symlink-normalized canonical path in `TARGET_PATH`; use it directly (no further path resolution needed)

#### Outputs
- **target_path**: Full absolute path to the worktree to switch to (canonical, after symlink resolution)
- **target_branch**: The branch checked out in the target worktree
- **target_name**: The directory basename of the target worktree
- **is_main_worktree**: Boolean — whether the target is the main working tree
- **already_at_target**: Boolean — whether **target_path** equals **project_root** (after resolving symlinks on both sides)

#### Validation
- [ ] A matching worktree was found
- [ ] **target_path** exists as a directory

**CRITICAL STOP CONDITION**: If no matching worktree is found, **STOP** and return a `WorktreeNotFoundError`:
```
No worktree found matching '<name>'.

Available worktrees:
<numbered list with paths and branches>

Use /worktrees.switch name="<worktree-name>" to switch to one.
```

**CRITICAL STOP CONDITION**: If **already_at_target** is true, **STOP** and return an `AlreadyOnWorktreeError`:
```
Already on worktree '<target_name>' at <target_path>.
No switch needed.
```

### Step 3: Detect the Cursor Environment

#### Inputs
- (none — this is a runtime capability check)

#### Actions
- [ ] Determine whether the `cursor-app-control` MCP server is available to this agent
  - The deterministic signal is the presence of the `cursor-app-control` MCP tools (specifically `move_agent_to_root`) in the agent's available tool surface
  - Do NOT rely on environment variables like `$CURSOR_*` — they are not reliable indicators of the ability to control Cursor's UI
- [ ] Record the result for use in Step 4

#### Outputs
- **in_cursor**: Boolean — whether `cursor-app-control.move_agent_to_root` is available

#### Validation
- [ ] The detection completed without error (this step never fails — absence of the MCP server simply means **in_cursor** is false)

### Step 4: Switch the Active Workspace

#### Inputs
- **target_path** (from Step 2)
- **target_branch** (from Step 2)
- **target_name** (from Step 2)
- **in_cursor** (from Step 3)

#### Actions
- [ ] If **in_cursor** is true:
  - Call the `cursor-app-control` MCP server's `move_agent_to_root` tool with `{ "rootPath": "<target_path>" }`
  - Capture the response
  - On success: Cursor's UI will redirect to the new root, and new terminals will open with **target_path** as their cwd
  - On failure: capture the error message for reporting
- [ ] If **in_cursor** is false:
  - Do NOT attempt to `cd` from within a tool call — that would only change the agent's shell, not the user's interactive shell
  - Prepare a clear instruction for the user to run `cd <target_path>` themselves

#### Outputs
- **switch_method**: One of `"cursor-mcp"` (used the MCP) or `"manual-cd"` (user must cd themselves)
- **switch_success**: Boolean — true if the MCP call succeeded, or true if the manual instruction was issued cleanly
- **mcp_error**: String containing the MCP error message, or null

#### Validation
- [ ] If **switch_method** is `"cursor-mcp"`, the MCP call returned successfully
- [ ] If **switch_method** is `"manual-cd"`, the user has been given the exact command to run

**CRITICAL STOP CONDITION**: If **in_cursor** is true and the MCP call failed, **STOP** and return a `SwitchFailedError`:
```
Failed to switch Cursor to worktree '<target_name>'.

  Target path: <target_path>
  MCP error: <mcp_error>

You can switch manually by running:
  cd <target_path>
```

### Step 5: Report Results

#### Inputs
- All outputs from previous steps

#### Actions
- [ ] Summarize the switch with the target worktree, branch, and method used
- [ ] If `"cursor-mcp"`: confirm Cursor's UI has been moved
- [ ] If `"manual-cd"`: clearly print the `cd` command the user needs to run

#### Outputs
Report to the user:
- The target worktree path and branch
- Which method was used (Cursor MCP or manual cd)
- For manual mode: the exact `cd` command
- A reminder of how to switch back

## Response Format

### When switched via Cursor MCP

```
Switched to worktree '<target_name>':

  Path: <target_path>
  Branch: <target_branch>
  Method: cursor-app-control (UI updated)

  Cursor's workspace is now pointing at the new worktree.
  New terminals will open in this directory.

  To switch back: /worktrees.switch name="<previous-name>"
```

### When manual cd is required (not in Cursor)

```
Ready to switch to worktree '<target_name>':

  Path: <target_path>
  Branch: <target_branch>
  Method: manual (cursor-app-control MCP not available)

  Run this command in your shell to switch:

    cd <target_path>

  To switch back: cd <previous-path>
```

## Error Handling

### NoWorktreesError

**When it occurs:** The project has no additional worktrees beyond the main working tree.

```
No additional worktrees exist for this project.
Use /worktrees.create to create one first.
```

### WorktreeNotFoundError

**When it occurs:** The provided name does not match any worktree by directory name, full path, or branch.

```
No worktree found matching '<name>'.

Available worktrees:
<numbered list>
```

### AlreadyOnWorktreeError

**When it occurs:** The resolved target path is the same as the current workspace root.

```
Already on worktree '<target_name>' at <target_path>.
No switch needed.
```

### SwitchFailedError

**When it occurs:** The agent is in Cursor but the `move_agent_to_root` MCP call failed.

```
Failed to switch Cursor to worktree '<target_name>'.

  Target path: <target_path>
  MCP error: <error message>

You can switch manually by running:
  cd <target_path>
```

## Examples

### Example 1: Switch by Name (Inside Cursor)

**Parameters:** `name="my-feature"`

**Result:**
```
Switched to worktree 'my-feature':

  Path: /Users/me/Sites/my-app/.worktrees/my-feature
  Branch: feature/dev/my-feature
  Method: cursor-app-control (UI updated)

  Cursor's workspace is now pointing at the new worktree.
  New terminals will open in this directory.

  To switch back: /worktrees.switch name="my-app"
```

### Example 2: Interactive Selection (No Name Provided)

**Parameters:** (none)

**Interaction:**
```
Which worktree would you like to switch to?

  1. my-app          (branch: main)              [current]
  2. my-feature      (branch: feature/dev/my-feature)
  3. experiment      (branch: main)
  4. hotfix          (branch: fix/login-bug)
```

User selects `2`.

**Result:**
```
Switched to worktree 'my-feature':

  Path: /Users/me/Sites/my-app/.worktrees/my-feature
  Branch: feature/dev/my-feature
  Method: cursor-app-control (UI updated)
```

### Example 3: Switch by Branch Name

**Parameters:** `name="fix/login-bug"`

**Result:** The skill matches the branch to the worktree where it is checked out.

```
Switched to worktree 'hotfix':

  Path: /Users/me/Sites/my-app/.worktrees/hotfix
  Branch: fix/login-bug
  Method: cursor-app-control (UI updated)
```

### Example 4: Outside Cursor (Manual cd)

**Parameters:** `name="experiment"`

The agent detects that `cursor-app-control` MCP is not available.

**Result:**
```
Ready to switch to worktree 'experiment':

  Path: /Users/me/Sites/my-app/.worktrees/experiment
  Branch: main
  Method: manual (cursor-app-control MCP not available)

  Run this command in your shell to switch:

    cd /Users/me/Sites/my-app/.worktrees/experiment

  To switch back: cd /Users/me/Sites/my-app
```

### Example 5: Already on Target

**Parameters:** `name="my-feature"` (already the active workspace)

**Result:**
```
Already on worktree 'my-feature' at /Users/me/Sites/my-app/.worktrees/my-feature.
No switch needed.
```

## Notes

- The `cursor-app-control.move_agent_to_root` tool updates Cursor's visible workspace AND the default cwd for newly opened terminals — but it does NOT change the cwd of terminals that are already open
- Symlinked paths under `~/.cursor/worktrees/<project>/` and the canonical paths under `<project>/.worktrees/` refer to the same worktrees; the skill normalizes both forms when matching and reporting
- The main working tree (the original clone directory) is a valid switch target — switching back to the main worktree is supported and useful
- The skill never modifies git state, never stashes changes, and never touches files in either worktree — uncommitted work in the source worktree remains exactly where it is
- Outside of Cursor, the skill cannot directly change the user's interactive shell cwd; the `cd` command must be run by the user
- This skill complements `create-worktree`: a common workflow is to create a worktree and then immediately switch to it — see the `create-and-switch-worktree` skill (`/worktrees.createAndSwitch`) which does both in one step

## Testing

The resolver script has a test harness. Run it from the repo root:

```bash
bash <skill-dir>/scripts/test-worktree-resolve.sh
```

It builds a throwaway repo with multiple worktrees (including a symlinked global path) and asserts on listing, resolution by name/branch/symlinked-path, already-at-target detection, and not-found handling. It prints `PASS`/`FAIL` per scenario and exits non-zero if any fail.
