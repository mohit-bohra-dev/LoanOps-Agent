# Add Submodule

Add a git repository as a submodule at a target path and initialize it.

> **PREREQUISITE — YOU MUST DO THIS FIRST**
>
> Before performing any actions, you MUST read and load {{skill:git-submodule}} using the Read tool. That skill contains the complete submodule workflow — every step, validation rule, error handler, and response format. Do NOT proceed until you have read the skill file in full. Do NOT attempt to add a submodule from memory or improvise the workflow. The skill is the sole source of truth.

## Parameters

- **{{repositoryUrl}}** (string, required): The URL of the repository to attach as a submodule.
- **{{path}}** (string, required): The target path for the submodule, e.g. `.kbs/<name>`.
- **{{ref}}** (string, optional): The branch or ref the submodule should track. When omitted, the remote's default branch is used.

## Instructions

Execute the skill's **Add Workflow** using the parameters above, including all steps, validation, error handling, and response formatting. Return the Add success JSON on success, or the appropriate error JSON (`SubmoduleExistsError`, `RepoNotFoundError`, `AddFailedError`) on failure.
