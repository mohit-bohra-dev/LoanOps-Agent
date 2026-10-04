---
promp:
  package: "git"
  version: "1.6.1"
  environment: "development"
  prompVersion: "1.0.1-beta.83"
  prompt: "removeSubmodule"
---
# git.removeSubmodule

Remove a submodule and clean up its git metadata (deinit, git rm, and .git/modules cleanup)

## Parameter Specifications

- **`path`** (string) - **Required**
  - The submodule path to remove

## Instructions

You are executing a Promp package prompt. Follow these steps:

1. **Parse the user input** to extract parameters:
   - Parameter 1: `path` (required) - The submodule path to remove

2. **Replace parameter placeholders** in the prompt content below:
   - Parameters use the format `{{parameterName}}` in the prompt
   - Replace each placeholder with the corresponding parsed value
   - If a parameter is optional and not provided, use its default value (if specified)
   - If a required parameter is missing, ask the user to provide it

3. **Execute the prompt** with the replaced parameters

## Usage

When the user invokes this command, they may provide parameters in various ways:
- Space-separated values: `/git.removeSubmodule value1 value2`
- Named parameters: `/git.removeSubmodule param1=value1 param2=value2`
- Mixed format: `/git.removeSubmodule value1 param2=value2`

Parse flexibly and map values to the expected parameters in order for positional arguments.

## Expected Output

Result of removing the submodule

**Type:** `object`

**Properties:**

- `success` (boolean) - **Required** - Whether the submodule was removed successfully
- `path` (string) - **Required** - The submodule path that was removed
- `cleanedPaths` (array) - **Required** - The metadata locations that were cleaned during removal
## Error Handling

### SubmoduleNotFoundError

Error when the given path is not a registered submodule

**Properties:**

- `code` (string) (values: ["SUBMODULE_NOT_FOUND"]) - 
- `message` (string) - 
- `path` (string) - The path that is not a registered submodule

### RemoveFailedError

Error when the submodule cannot be fully removed

**Properties:**

- `code` (string) (values: ["REMOVE_FAILED"]) - 
- `message` (string) - 
- `removeOutput` (string) - The output from the failed removal commands

## Prompt Content

# Remove Submodule

Remove a submodule and clean up its git metadata.

> **PREREQUISITE — YOU MUST DO THIS FIRST**
>
> Before performing any actions, you MUST read and load @./.cursor\skills\git-submodule\SKILL.md using the Read tool. That skill contains the complete submodule workflow — every step, validation rule, error handler, and response format. Do NOT proceed until you have read the skill file in full. Do NOT attempt to remove a submodule from memory or improvise the workflow. The skill is the sole source of truth.

## Parameters

- **{{path}}** (string, required): The submodule path to remove.

## Instructions

Execute the skill's **Remove Workflow** using the parameter above, including all steps, validation, error handling, and response formatting. Return the Remove success JSON (with the `cleanedPaths` list) on success, or the appropriate error JSON (`SubmoduleNotFoundError`, `RemoveFailedError`) on failure.

