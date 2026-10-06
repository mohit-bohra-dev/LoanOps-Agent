---
description: Start spec-driven work — Promp artifacts under .ai/specs/, not root SPEC.md
---

This repo does **not** use root `SPEC.md`. Spec/story live in Promp layout.

1. Load `.cursor/rules/spec.specStructure.mdc` and `.cursor/skills/spec-spec-artifact-model/SKILL.md`.
2. If no feature folder yet: run `/spec.createSpec` (story + spec + plan under `.ai/specs/<featureName>/`).
3. If story exists and spec needs authoring: `/spec.authorSpec`.
4. Engineering process skills (`using-agent-skills`, TDD, review) still apply **after** those artifacts exist.

Do not write `SPEC.md`, `docs/SPEC.md`, or `tasks/plan.md` for product features.
