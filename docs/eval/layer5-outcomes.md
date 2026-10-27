# Layer 5 — Outcomes

Scores the **final answer** against evidence. Not tool choice (Layer 2), not args (Layer 3), not call order (Layer 4). No Auth suite. No `POST /chat`. Does **not** change `thresholds.py` or `GoldenExpected`. Ragas stays on `make eval` — Layer 5 default path is deterministic (no judge model).

## Scoring rules

Pure function `score_outcome(observation, expectation)`:

| Rule | Pass when |
|---|---|
| **Facts** | Every `must_contain` string appears in `answer` (case-sensitive) |
| **Grounding** | Every `must_contain` string also appears in concatenation of `tool_results[].text` |
| **Citations** | Every `must_cite` prefix matches ≥1 citation source (stem before `#`); happy-path with non-empty `must_cite` also requires ≥1 citation |
| **Forbidden** | No `forbidden_phrases` substring in `answer` |
| **Refusal** | `refusal=true` → non-empty refusal string; facts/cites not required |
| **Escalation** | Observed category matches expectation; refusal text allowed; facts/cites not required |

Empty `must_contain` skips fact + grounding checks. Wrong tools are L2–L4 — Layer 5 only reads result text supplied with the case.

`--live` uses `structural_only=True`: scores citations, forbidden phrases, refusal, escalation. Skips `must_contain` / tool-text grounding so paraphrase is not a failure.

## Run

```powershell
# Unit tests
uv run pytest projects/LoanOps.Eval/packages/eval/outcomes -q

# Canned outcomes (default — no LLM)
uv run python -m packages.eval.outcomes --report out/eval-l5.json

# Optional live agent (structural clauses from golden; skips cleanly if no model)
uv run python -m packages.eval.outcomes --live --report out/eval-l5.json
```

Or: `make eval-l5`

## Drivers

| Mode | Input | When |
|---|---|---|
| **Canned** (always) | `data/eval/layer5_outcomes.jsonl` | Deterministic; green without a model |
| **`--live`** | `data/golden.jsonl` via `run_agent_turn` | Structural constraints only; skip + note if chat fails; canned still gates exit |

Live skip → exit 0 when canned passed. Live ran but wrong structural outcome → real failure.

## Files

| Path | Role |
|---|---|
| `packages/eval/outcomes/score.py` | `score_outcome` |
| `packages/eval/outcomes/layer5.py` | Runner + CLI |
| `data/eval/layer5_outcomes.jsonl` | Canned answers + tool snippets (five golden ids) |
| `packages/eval/outcomes/tests/` | Pass/fail unit + canned smoke |

## Out of scope

Ragas / LLM judge, lowering thresholds, changing `GoldenExpected`, Auth, business-state writes, tool selection/args/order, live enterprise HTTP, production agent changes.
