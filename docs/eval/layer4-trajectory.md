# Layer 4 — Trajectory

Scores **valid paths** over an ordered list of tool names. Not which tools alone (Layer 2), not argument values (Layer 3), not answer text (Layer 5). No Auth suite. No `POST /chat`. MCP/Langfuse span capture deferred.

## Scoring rules

Pure function `score_trajectory(observed_tools, expectation)`:

| Rule | Pass when |
|---|---|
| **Required steps** | Every name in `required_steps` appears ≥1 (order free unless deps) |
| **Dependencies** | For each `[before, after]`: first `before` index &lt; first `after` (if `after` present; if `after` absent, skip) |
| **Forbidden** | No name in `forbidden_steps` was called |
| **Alternatives** | If `allowed_path_sets` set: observed covers **one** full set (`required_steps` unused for presence) |
| **Extras OK** | Tools between/around required steps allowed — **no** exact-sequence matcher |
| **Unknown** | Every called name is one of the 10 MCP tools |
| **Refusal** | Empty `required_steps` + empty `allowed_path_sets` → observed must be empty |

Does **not** change golden thresholds in `thresholds.py`. Layer 4 has its own pass/fail report.

## Run

```powershell
# Unit tests
uv run pytest projects/LoanOps.Eval/packages/eval/trajectory -q

# Canned trajectories (default — no LLM)
uv run python -m packages.eval.trajectory --report out/eval-l4.json

# Optional live agent (constraints from canned by golden id; skips cleanly if no model)
uv run python -m packages.eval.trajectory --live --report out/eval-l4.json
```

Or: `make eval-l4`

## Drivers

| Mode | Input | When |
|---|---|---|
| **Canned** (always) | `data/eval/layer4_trajectories.jsonl` | Deterministic; green without a model |
| **`--live`** | `data/golden.jsonl` via `run_agent_turn` | Scores ordered tool names vs canned constraints (matched by id); skip + note if chat fails; canned still gates exit |

Live skip → exit 0 when canned passed. Live ran but wrong path → real failure.

## Files

| Path | Role |
|---|---|
| `packages/eval/trajectory/score.py` | `score_trajectory` |
| `packages/eval/trajectory/layer4.py` | Runner + CLI |
| `data/eval/layer4_trajectories.jsonl` | Canned ordered tools + deps (five golden ids) |
| `packages/eval/trajectory/tests/` | Pass/fail unit + canned smoke |

## Out of scope

Exact-sequence matcher, argument correctness, outcome text, Auth, Langfuse/MCP span capture, live enterprise HTTP, lowering existing eval thresholds, production agent changes.
