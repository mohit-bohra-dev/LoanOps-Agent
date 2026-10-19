# Layer 2 — Tool selection

Scores **which tools were chosen** (names only). Not MCP protocol (Layer 1), not argument values (Layer 3), not call order (Layer 4). No Auth suite. No `POST /chat`.

## Scoring rules

Pure function `score_tool_selection(observed_tools, expectation)`:

| Rule | Pass when |
|---|---|
| **Required** | Every name in `must_call_tools` appears ≥1 (order ignored; extras OK unless forbidden) |
| **Alternatives** | If `allowed_tool_sets` set: observed covers **one** full set (`must_call_tools` unused for required check) |
| **Forbidden** | No name in `forbidden_tools` was called |
| **Refusal / empty** | Empty `must_call_tools` + empty `allowed_tool_sets` → observed must be empty |
| **Unknown** | Every called name is one of the 10 MCP tools |

Does **not** change golden thresholds in `thresholds.py`. Layer 2 has its own pass/fail report.

## Run

```powershell
# Unit tests
uv run pytest projects/LoanOps.Eval/packages/eval/selection -q

# Canned trajectories (default — no LLM)
uv run python -m packages.eval.selection --report out/eval-l2.json

# Optional live agent (skips cleanly if no model)
uv run python -m packages.eval.selection --live --report out/eval-l2.json
```

Or: `make eval-l2`

## Drivers

| Mode | Input | When |
|---|---|---|
| **Canned** (always) | `data/eval/layer2_trajectories.jsonl` | Deterministic; green without a model |
| **`--live`** | `data/golden.jsonl` via `run_agent_turn` | Scores real tool names; skip + note if chat/providers fail; canned still gates exit |

Live skip → exit 0 when canned passed. Live ran but wrong tools → real failure.

## Files

| Path | Role |
|---|---|
| `packages/eval/selection/score.py` | `score_tool_selection` |
| `packages/eval/selection/layer2.py` | Runner + CLI |
| `data/eval/layer2_trajectories.jsonl` | Canned observed tools (five golden ids) |
| `packages/eval/selection/tests/` | Pass/fail unit + canned smoke |

## Out of scope

Argument correctness, trajectory order, answer text, Auth, live enterprise HTTP, lowering existing eval thresholds, production agent changes.
