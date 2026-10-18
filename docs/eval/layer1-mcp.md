# Layer 1 — MCP server evaluation

Deterministic MCP protocol + tool contract suite. **No LLM. No Auth evaluation suite** (fixture bearer is harness plumbing only).

## Run

```powershell
# Pytest (default ASGI + execute_tool FakeClient)
uv run pytest projects/LoanOps.Eval/packages/eval/mcp -q

# Full runner + JSON report
uv run python -m packages.eval.mcp --report out/eval-mcp-l1.json

# Optional latency gate (FakeClient p95)
uv run python -m packages.eval.mcp --report out/eval-mcp-l1.json --enforce-latency

# Live Streamable HTTP + SDK client
uv run pytest projects/LoanOps.Eval/packages/eval/mcp/tests/test_live_mcp.py -m integration -q
```

Or: `make eval-mcp-l1`

## Suites

| Suite | What |
|---|---|
| `protocol` | `initialize` / `protocolVersion`, JSON-RPC `-32700`, unknown method, invalid params, unknown tool |
| `contracts` | `tools/list` names, `readOnlyHint`, input schemas, snapshot, GET-only policy, FakeClient happy path per tool |
| `functional` | Empty vs ok results, fixture-catalog SSE stubs, response snapshots |
| `errors` | Upstream fail, exception, timeout, rate-limit → clear failure + audit/telemetry |
| `perf` | Concurrent isolation, p50/p95, payload-size budgets |

## Add a case

1. Add a `McpL1Case` in [`packages/eval/mcp/cases.py`](../../projects/LoanOps.Eval/packages/eval/mcp/cases.py) with `suite` + `eval_methods`.
2. Wire assertion in [`layer1.py`](../../projects/LoanOps.Eval/packages/eval/mcp/layer1.py) or a focused test under `packages/eval/mcp/tests/`.
3. Prefer `FakeClient` / `FixtureCatalogClient` — never live enterprise HTTP.

## Snapshots

- `packages/eval/mcp/snapshots/tools.json` — tool list + schemas
- `packages/eval/mcp/snapshots/responses/` — stable text bodies

If a snapshot fails after an intentional tool-schema change, regenerate by deleting the file and re-running the snapshot test / runner (it writes on first miss).

## Notes

- Unknown JSON-RPC methods may return **`-32602`** (SDK) rather than classic `-32601`.
- Auth / OAuth / role matrix: deferred (existing unit tests in `packages/mcp_server/tests/` only).
- Cursor/Gemini negotiated `protocolVersion` in the wild: unverified.
