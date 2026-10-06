---
description: Break work into tasks — use Promp [feature].plan.md under .ai/specs/
---

This repo does **not** use `tasks/plan.md`.

1. Find or create `.ai/specs/<featureName>/<featureName>.plan.md` (Cursor plan YAML + todos).
2. Load `.cursor/skills/spec-spec-plan-format/SKILL.md`. If the spec is missing, `/spec.authorSpec` first.
3. Optionally load `.cursor/skills/planning-and-task-breakdown/SKILL.md` for slicing quality, but **write todos into the Promp plan file**, not `tasks/todo.md`.
4. Graphify-first before exploratory reads. Present plan for human review. No code in this command.
