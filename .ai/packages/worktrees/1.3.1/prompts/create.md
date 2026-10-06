# Create Worktree

Create a new git worktree in the project-local `.worktrees/` directory and run setup hooks. Optionally create a **new feature branch** for the worktree.

> **PREREQUISITE — YOU MUST DO THIS FIRST**
>
> Before performing any actions, you MUST read and load {{skill:create-worktree}} using the Read tool. That skill contains the complete worktree creation workflow — every step, validation rule, error handler, and response format. Do NOT proceed until you have read the skill file in full. Do NOT attempt to create worktrees from memory or improvise the workflow. The skill is the sole source of truth.

Branch options (pass at most one):

- **{{newBranch}}** — create a new feature branch in the worktree (uses the detached-HEAD-first technique with rollback). Follow the `feature/{environment}/{feature-name}` convention where applicable.
- **{{branch}}** — check out an existing branch, tag, or commit.
- **{{detach}}** — create the worktree at a detached HEAD with no branch.
- (none) — create a new branch named after the worktree directory.

If the user wants to create the worktree and immediately switch into it, use `/worktrees.createAndSwitch` instead.

Execute the entire workflow defined in the skill, including all steps, validation, error handling, and response formatting.
