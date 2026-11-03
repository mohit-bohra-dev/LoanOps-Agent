# Layer 9 — Evaluation governance

Golden sets are product artifacts. Repo is source of truth (PR = approval). Langfuse/EvalStore is a synced mirror for runs and review.

## Artifacts

| Path | Role |
|---|---|
| `data/eval/registry.jsonl` | Sidecar: case_id, layer, version, status, eval_methods, rubric, reviewers |
| `data/eval/rubrics/<name>.v<N>.yaml` | Immutable rubric versions → score configs `<name>@v<N>` |
| `data/eval/candidates/` | Promote output only (never auto-writes approved) |

## CLI

```powershell
uv run python -m packages.eval.governance validate
uv run python -m packages.eval.governance sync --mock
uv run python -m packages.eval.governance agreement
uv run python -m packages.eval.governance calibrate
uv run python -m packages.eval.governance promote
```

Or: `make eval-l9` (validate only).

`validate` fails CI when a layer case lacks an approved registry row or rubric file; warns on near-duplicate prompts (Jaccard ≥ 0.9) and stale reviews (>180 days).

Disagreements go to annotation queue `loanops-adjudication`. LLM judge trusted for a rubric only when kappa ≥ 0.6 vs humans.
