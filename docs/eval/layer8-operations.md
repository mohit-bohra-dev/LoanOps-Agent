# Layer 8 — Operations

Production MCP monitoring, separate from offline eval scores. Works for **every agent** that consumes the MCP (spans carry `mcp.client_name`).

## Locked rule

`ops.*` scores live in Langfuse/EvalStore environment `prod`. Offline scores use `eval.*` in environment `eval`. Different stores/gates; connected dashboards.

## SLOs

[`data/eval/ops_slos.yaml`](../../data/eval/ops_slos.yaml) — per-tool p95 latency, error rate, `isError` rate, min sample, drift delta. **Not** `thresholds.py`.

## Job

```powershell
uv run pytest projects/LoanOps.Eval/packages/eval/operations -q
uv run python -m packages.eval.operations --report out/eval-l8.json
uv run python -m packages.eval.operations --live-store --env prod --window 24 --sample 0.05
```

Or: `make eval-l8` (fixture traces; zero Langfuse credentials).

Steps: fetch `mcp.tool.call` traces → metrics by tool and by `mcp.client_name` → sample deterministic online checks (L5-ish structural + no-PII) → enqueue fails to `loanops-ops-review` → write `ops.*` scores.

## Dashboard notes (manual in Langfuse UI)

- Board A (offline): environment=`eval`, scores `eval.*`
- Board B (prod): environment=`prod`, scores `ops.*`, group by `mcp.client_name`
