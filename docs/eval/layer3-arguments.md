# Layer 3 — Arguments

Scores **argument contents** of already-chosen tools. Not tool selection (Layer 2), not call order (Layer 4), not answer text (Layer 5). No Auth suite. No `POST /chat`.

## Scoring rules

Pure function `score_tool_args(observed_calls, expectation)`:

| Rule | Pass when |
|---|---|
| **Match** | Each constraint is satisfied by ≥1 observed call of that tool name |
| **Required keys** | Listed keys present and not null |
| **Types** | Optional `str` / `int` / `bool` / `dict` / `list` on keys |
| **Equals** | Exact value on listed keys |
| **Contains** | Substring on string keys |
| **Forbid keys** | Key absent or empty (`body`) |
| **Side-effect** | Every `call_sse_api`: no body; `method` if set must be `GET` |
| **Unknown** | Every call name is one of the 10 MCP tools |
| **Refusal** | Empty calls + empty constraints → pass |

Does **not** change golden thresholds in `thresholds.py`. Layer 3 has its own pass/fail report.

Does **not** call MCP `assert_sse_read_only` (needs catalog `resolved_method`). Resolved-method policy stays in MCP / Layer 1.

## Run

```powershell
# Unit tests
uv run pytest projects/LoanOps.Eval/packages/eval/arguments -q

# Canned args (default — no LLM)
uv run python -m packages.eval.arguments --report out/eval-l3.json

# Optional live agent (structural constraints only; skips cleanly if no model)
uv run python -m packages.eval.arguments --live --report out/eval-l3.json
```

Or: `make eval-l3`

## Drivers

| Mode | Input | When |
|---|---|---|
| **Canned** (always) | `data/eval/layer3_args.jsonl` | Deterministic; green without a model |
| **`--live`** | `data/golden.jsonl` via `run_agent_turn` | Structural only (`required_keys`, `types`, `forbid_keys`, side-effect); skip + note if chat fails; canned still gates exit |

Live skip → exit 0 when canned passed. Live ran but wrong structural args → real failure.

## Files

| Path | Role |
|---|---|
| `packages/eval/arguments/score.py` | `score_tool_args` |
| `packages/eval/arguments/layer3.py` | Runner + CLI |
| `data/eval/layer3_args.jsonl` | Canned observed args (five golden ids) |
| `packages/eval/arguments/tests/` | Pass/fail unit + canned smoke |

## Out of scope

Role/permission allow-lists, capability bind, catalog resolution, argument order, outcome text, Auth, live enterprise HTTP, lowering existing eval thresholds, production agent changes.
