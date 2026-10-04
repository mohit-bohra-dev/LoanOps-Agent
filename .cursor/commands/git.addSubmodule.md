---
promp:
  package: "git"
  version: "1.6.1"
  environment: "development"
  prompVersion: "1.0.1-beta.83"
  prompt: "addSubmodule"
---
# git.addSubmodule

Add a git repository as a submodule at a target path and initialize it, optionally tracking a branch/ref

## Parameter Specifications

- **`repositoryUrl`** (string) - **Required**
  - The URL of the repository to attach as a submodule

- **`path`** (string) - **Required**
  - The target path for the submodule (e.g. .kbs/<name>)

- **`ref`** (string) - *Optional*
  - The branch or ref the submodule should track (defaults to the remote's default branch)

## Instructions

You are executing a Promp package prompt. Follow these steps:

1. **Parse the user input** to extract parameters:
   - Parameter 1: `repositoryUrl` (required) - The URL of the repository to attach as a submodule
   - Parameter 2: `path` (required) - The target path for the submodule (e.g. .kbs/<name>)
   - Parameter 3: `ref` (optional) - The branch or ref the submodule should track (defaults to the remote's default branch)

2. **Replace parameter placeholders** in the prompt content below:
   - Parameters use the format `{{parameterName}}` in the prompt
   - Replace each placeholder with the corresponding parsed value
   - If a parameter is optional and not provided, use its default value (if specified)
   - If a required parameter is missing, ask the user to provide it

3. **Execute the prompt** with the replaced parameters

## Usage

When the user invokes this command, they may provide parameters in various ways:
- Space-separated values: `/git.addSubmodule value1 value2`
- Named parameters: `/git.addSubmodule param1=value1 param2=value2`
- Mixed format: `/git.addSubmodule value1 param2=value2`

Parse flexibly and map values to the expected parameters in order for positional arguments.

## Expected Output

Result of adding the submodule

**Type:** `object`

**Properties:**

- `success` (boolean) - **Required** - Whether the submodule was added successfully
- `path` (string) - **Required** - The submodule path that was added
- `ref` (string) - *Optional* - The tracked branch/ref (provided ref or the resolved default branch)
- `commit` (string) - **Required** - The commit SHA the submodule is checked out at
## Error Handling

### SubmoduleExistsError

Error when a submodule already exists at the target path

**Properties:**

- `code` (string) (values: ["SUBMODULE_EXISTS"]) - 
- `message` (string) - 
- `path` (string) - The conflicting target path

### RepoNotFoundError

Error when the submodule repository cannot be found, cloned, or authenticated

**Properties:**

- `code` (string) (values: ["REPO_NOT_FOUND"]) - 
- `message` (string) - 
- `repositoryUrl` (string) - The repository URL that could not be cloned

### AddFailedError

Error when git submodule add fails for any other reason

**Properties:**

- `code` (string) (values: ["ADD_FAILED"]) - 
- `message` (string) - 
- `addOutput` (string) - The output from the failed git submodule add command

## Prompt Content

# Add Submodule

Add a git repository as a submodule at a target path and initialize it.

> **PREREQUISITE — YOU MUST DO THIS FIRST**
>
> Before performing any actions, you MUST read and load @./.cursor\skills\git-submodule\SKILL.md using the Read tool. That skill contains the complete submodule workflow — every step, validation rule, error handler, and response format. Do NOT proceed until you have read the skill file in full. Do NOT attempt to add a submodule from memory or improvise the workflow. The skill is the sole source of truth.

## Parameters

- **{{repositoryUrl}}** (string, required): The URL of the repository to attach as a submodule.
- **{{path}}** (string, required): The target path for the submodule, e.g. `.kbs/<name>`.
- **{{ref}}** (string, optional): The branch or ref the submodule should track. When omitted, the remote's default branch is used.

## Instructions

Execute the skill's **Add Workflow** using the parameters above, including all steps, validation, error handling, and response formatting. Return the Add success JSON on success, or the appropriate error JSON (`SubmoduleExistsError`, `RepoNotFoundError`, `AddFailedError`) on failure.

