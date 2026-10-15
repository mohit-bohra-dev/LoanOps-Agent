# EAKG index schedule (ops)

**D10 (2026-10-02):** **Manual only.** No Windows Task Scheduler, no live GitLab CI schedules. Run CLI by hand when you need a refresh. Scripts below are optional reference for a later opt-in.

Three tiers call the same CLI. Do not re-clone everything nightly.

| Tier | Cadence | Command | LLM |
|---|---|---|---|
| Per-merge | On merge to `main` | `python -m packages.eakg sync repo --id <repo_id>` | No |
| Nightly | ~02:00 local | `python -m packages.eakg sync nightly` | Proposals only (flagged) |
| Weekly audit | Monday | `python -m packages.eakg sync audit` | No |
| Investigate (opt-in) | Manual | `python -m packages.eakg investigate --id <repo> --dry-run` then with `EAKG__INVESTIGATE_AGENT=1` | ADR-029 investigator over gap ledger only |
| Patterns | Manual | `python -m packages.eakg patterns hash` / `patterns backtest --proposal …` | No (deterministic backtest) |

ADR-029: deterministic analyzers own coverage; LLM investigates ledger gaps only when `EAKG__INVESTIGATE_AGENT=true` (default off). Candidates stay `pending_review` / `callable=false` until human publish. Pattern YAMLs under `data/eakg/patterns/` require backtest + git merge before the next extract absorbs them (`patterns_hash` → `reextract_required`).

## Prerequisites

- `uv` on PATH (or `D:\Users\<you>\.local\bin\uv.exe`)
- `glab` authenticated to `gitlab.pnmac.com`
- Workspace clones under `EAKG__WORKSPACE_DIR` (default `.eakg-workspace/`, gitignored)
- Never commit live TAAC config

## Windows Task Scheduler

From repo root (PowerShell as the service account that has `glab` auth):

```powershell
.\scripts\eakg\install-scheduled-tasks.ps1
```

That registers:

- `LoanOps-EAKG-Nightly` — daily 02:00 → `sync-nightly.ps1`
- `LoanOps-EAKG-Audit` — weekly Monday 06:00 → `sync-audit.ps1`

Manual one-offs:

```powershell
.\scripts\eakg\sync-repo.ps1 -RepositoryId loanservices
.\scripts\eakg\sync-nightly.ps1
.\scripts\eakg\sync-audit.ps1
.\scripts\eakg\refresh-taac.ps1   # glab → workspace only; never commits
```

## GitLab CI

Include [`ci/eakg.gitlab-ci.yml`](../ci/eakg.gitlab-ci.yml) from this repo or copy jobs into an ops pipeline.

- `eakg:sync-repo` — `rules: if merge to main` with `EAKG_REPO_ID` CI variable
- `eakg:nightly` — `rules: schedule` (create a GitLab pipeline schedule)
- `eakg:audit` — weekly schedule

CI needs a runner with `glab` + clone access to registered repos, and a protected `MCP`/`EAKG` workspace volume or fresh clone each job.

## TAAC refresh

Live TAAC stays under `.eakg-workspace/` (gitignored). Refresh:

```powershell
.\scripts\eakg\refresh-taac.ps1
# then either:
#   set EAKG__TAAC_CONFIG_PATH=.eakg-workspace/taac-client-config.json
#   python -m packages.eakg ingest-taac --path .eakg-workspace/taac-client-config.json
# or rely on sync nightly (reads EAKG__TAAC_CONFIG_PATH || fixture)
```

Committed fixture: `data/eakg/fixtures/taac-client-config.redacted.json` (synthetic only).
