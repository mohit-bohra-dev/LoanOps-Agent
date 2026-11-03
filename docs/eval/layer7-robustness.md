# Layer 7 — Robustness

N-repeat pass-rates over paraphrases, malformed prompts, and degraded tools. Not a single lucky pass. No Auth. No `POST /chat`. Does **not** change `thresholds.py`.

## Scoring

Per run: L2 `score_tool_selection` + L4 `score_trajectory` + L5 `score_outcome(structural_only=True)`.

Faulted runs (`tool_timeout` / `tool_error` / `empty_result` via `FaultyToolsClient`) pass only if the agent refuses or escalates and avoids forbidden phrases.

Aggregation: pass-rate + Wilson 95% lower bound. Case fails if pass-rate &lt; `min_pass_rate` (default 0.8). Thresholds in `packages/eval/robustness/thresholds.py`.

## Run

```powershell
uv run pytest projects/LoanOps.Eval/packages/eval/robustness -q
uv run python -m packages.eval.robustness --report out/eval-l7.json
uv run python -m packages.eval.robustness --live --repeats 3 --report out/eval-l7.json
```

Or: `make eval-l7`

## Drivers

| Mode | Input |
|---|---|
| Canned (CI) | `data/eval/layer7_replays.jsonl` + variants |
| `--live` | `run_agent_turn` on paraphrases/malformed/faults; skip cleanly if no model |

EvalStore dataset: `loanops-l7-robustness`, environment=`eval`.
