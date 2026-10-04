# Update Submodule

Update one or all submodules to the latest commit on their tracked branch.

> **PREREQUISITE — YOU MUST DO THIS FIRST**
>
> Before performing any actions, you MUST read and load {{skill:git-submodule}} using the Read tool. That skill contains the complete submodule workflow — every step, validation rule, error handler, and response format. Do NOT proceed until you have read the skill file in full. Do NOT attempt to update a submodule from memory or improvise the workflow. The skill is the sole source of truth.

## Parameters

- **{{path}}** (string, optional): A single submodule path to update. When omitted, all submodules are updated.

## Instructions

Execute the skill's **Update Workflow** using the parameter above, including all steps, validation, error handling, and response formatting. Return the Update success JSON (with the per-submodule `updated` array) on success, or the appropriate error JSON (`SubmoduleNotFoundError`, `UpdateFailedError`, `DirtyWorktreeError`) on failure.
