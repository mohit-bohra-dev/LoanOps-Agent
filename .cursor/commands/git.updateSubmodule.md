---
promp:
  package: "git"
  version: "1.6.1"
  environment: "development"
  prompVersion: "1.0.1-beta.83"
  prompt: "updateSubmodule"
---
# git.updateSubmodule

Update one or all submodules to the latest commit on their tracked branch

## Parameter Specifications

- **`path`** (string) - *Optional*
  - A single submodule path to update (defaults to all submodules when omitted)

## Instructions

You are executing a Promp package prompt. Follow these steps:

1. **Parse the user input** to extract parameters:
   - Parameter 1: `path` (optional) - A single submodule path to update (defaults to all submodules when omitted)

2. **Replace parameter placeholders** in the prompt content below:
   - Parameters use the format `{{parameterName}}` in the prompt
   - Replace each placeholder with the corresponding parsed value
   - If a parameter is optional and not provided, use its default value (if specified)
   - If a required parameter is missing, ask the user to provide it

3. **Execute the prompt** with the replaced parameters

## Usage

When the user invokes this command, they may provide parameters in various ways:
- Space-separated values: `/git.updateSubmodule value1 value2`
- Named parameters: `/git.updateSubmodule param1=value1 param2=value2`
- Mixed format: `/git.updateSubmodule value1 param2=value2`

Parse flexibly and map values to the expected parameters in order for positional arguments.

## Expected Output

Result of updating the submodule(s)

**Type:** `object`

**Properties:**

- `success` (boolean) - **Required** - Whether the update completed successfully
- `updated` (array) - **Required** - Per-submodule update details
## Error Handling

### SubmoduleNotFoundError

Error when the given path is not a registered submodule

**Properties:**

- `code` (string) (values: ["SUBMODULE_NOT_FOUND"]) - 
- `message` (string) - 
- `path` (string) - The path that is not a registered submodule

### UpdateFailedError

Error when git submodule update --remote fails

**Properties:**

- `code` (string) (values: ["UPDATE_FAILED"]) - 
- `message` (string) - 
- `updateOutput` (string) - The output from the failed git submodule update command

### DirtyWorktreeError

Error when a submodule has uncommitted changes, so updating could discard work

**Properties:**

- `code` (string) (values: ["DIRTY_WORKTREE"]) - 
- `message` (string) - 
- `path` (string) - The submodule path with uncommitted changes
- `dirtyFiles` (array) - The modified files inside the submodule

## Prompt Content

# Update Submodule

Update one or all submodules to the latest commit on their tracked branch.

> **PREREQUISITE — YOU MUST DO THIS FIRST**
>
> Before performing any actions, you MUST read and load @./.cursor\skills\git-submodule\SKILL.md using the Read tool. That skill contains the complete submodule workflow — every step, validation rule, error handler, and response format. Do NOT proceed until you have read the skill file in full. Do NOT attempt to update a submodule from memory or improvise the workflow. The skill is the sole source of truth.

## Parameters

- **{{path}}** (string, optional): A single submodule path to update. When omitted, all submodules are updated.

## Instructions

Execute the skill's **Update Workflow** using the parameter above, including all steps, validation, error handling, and response formatting. Return the Update success JSON (with the per-submodule `updated` array) on success, or the appropriate error JSON (`SubmoduleNotFoundError`, `UpdateFailedError`, `DirtyWorktreeError`) on failure.

