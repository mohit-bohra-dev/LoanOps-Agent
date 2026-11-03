# Local stack scripts

Windows-first helpers for the LoanOps demo / live-eval path.

## Quick start

```powershell
# From repo root
.\scripts\dev\start-stack.ps1
.\scripts\dev\start-stack.ps1 -RefreshIndex   # also rebuild ApiIndex vectors
.\scripts\dev\stop-stack.ps1
.\scripts\dev\stop-stack.ps1 -IncludeGraphDb
```

```powershell
uv run python scripts/dev/stack_ops.py status
uv run python scripts/dev/stack_ops.py health
uv run python scripts/dev/stack_ops.py wait --timeout 120
uv run python scripts/dev/stack_ops.py refresh-index --env dev
```

## What `start-stack.ps1` does

1. `aws sso login --profile dev` (skip: `-SkipSso`)
2. `scripts/auth/refresh-sse-m2m.ps1` → `SSE__API_KEY` (skip: `-SkipM2m`)
3. GraphDB via `D:\Users\v-mbohra\tools\start-graphdb.cmd`
4. MCP `:8001` (recycles if already up so `.env` reloads)
5. Agent API `:8000`
6. Vite UI `:5173` (skip: `-NoUi`)
7. Optional ApiIndex refresh (`-RefreshIndex`)

Logs: `out/stack-logs/*.log`

## Ports

| Service | Port |
|---|---|
| Postgres / pgvector | 5432 (not started here) |
| GraphDB | 7200 |
| Agent API | 8000 |
| MCP | 8001 |
| Web UI | 5173 |

## Notes

- Never prints tokens.
- Postgres must already be running (`localhost:5432`).
- Override GraphDB launcher: `-GraphDbStartCmd path\to\start-graphdb.cmd`
