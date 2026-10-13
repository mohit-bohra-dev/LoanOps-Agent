---
name: eakg-onboard-repo
description: >-
  Register and onboard a Plaisse (or other) GitLab application into the LoanOps
  EAKG registry, extract Roslyn interface + optional Graphify engineering graph,
  load GraphDB, and smoke MCP describe_application / search_code. Use when adding
  a new repo to EAKG, onboarding CoreComponents or any SSE app, or the user says
  "onboard repo", "register application", or "add to EAKG".
---

# EAKG onboard repository

PowerShell only (no `&&`). Host for enterprise clones: `gitlab.pnmac.com` via `glab`
(`GITLAB_HOST` / `--hostname` on `api` only — see `packages/eakg/gitops.py`).

Canonical doc: [`docs/EAKG_ONBOARD_REPO.md`](../../../docs/EAKG_ONBOARD_REPO.md).

## Inputs (ask if missing)

| Field | Example |
|-------|---------|
| GitLab URL or `group/…/project` | `https://gitlab.pnmac.com/servicing/plaisse/applications/corecomponents/CoreComponents` |
| `repository_id` / `application_id` | `corecomponents` (lowercase, no spaces) |
| Display name | `Core Components` |
| `api_project_path` | `src/CoreComponents.Api` (WebApi/Api csproj folder) |
| Optional `dev` `base_url` | from appsettings `ServiceUrls.*` or TAAC |
| Optional `service_url_key` | e.g. `CoreComponentsApiUrl` |

## Steps

### 1. Resolve GitLab project

```powershell
$enc = [uri]::EscapeDataString('servicing/plaisse/applications/corecomponents/CoreComponents')
glab api --hostname gitlab.pnmac.com "projects/$enc"
```

Record: `id` → `--gitlab-project-id`, `http_url_to_repo`, `default_branch`, path for clone.

Find API project (tree or after clone):

```powershell
glab api --hostname gitlab.pnmac.com "projects/<id>/repository/tree?recursive=true&per_page=100&path=src"
```

Prefer `src/<Name>.Api` or `src/<Name>.WebApi` for `--api-project-path`.

### 2. Register (no clone)

```powershell
uv run python -m packages.eakg register `
  --id <repository_id> `
  --application "<Display Name>" `
  --application-id <repository_id> `
  --git-url https://gitlab.pnmac.com/<group>/<project>.git `
  --gitlab-project-id <id> `
  --api-project-path src/<ApiProject> `
  --team <group/path>
```

If product uses Postgres artifacts (`EAKG_STORE__BACKEND=postgres`), register writes there. Keep `data/eakg/registry/repositories.yaml` in sync only if file backend / committed registry is still used.

### 3. Set env target (for live SSE / spec refresh)

After register, patch environments (Python) when `base_url` known:

```powershell
uv run python -c @"
from packages.common.settings import get_settings
get_settings.cache_clear()
from packages.eakg.runtime import eakg_runtime
from packages.eakg.registry import AppEnvironment
reg, _, _ = eakg_runtime(get_settings())
r = reg.get('<repository_id>')
r.service_url_key = '<ServiceUrlKey>'
r.deployables = ['<Api>', '<Web>']
r.environments = {
    'dev': AppEnvironment(base_url='https://…', auth_audience='https://pennymac'),
}
reg.upsert(r); reg.save()
"@
```

Without `base_url`, onboard still extracts code; OpenAPI `spec` stage may `failed`.

### 4. Onboard (clone + extract + GraphDB + eng graph)

Default `EAKG__ENGINEERING_GRAPH=true` runs Graphify AST → `data/eakg/repos/<id>/engineering/graph.json` (non-fatal if graphify missing).

```powershell
$env:GITLAB_HOST = 'gitlab.pnmac.com'
$env:EAKG__ENGINEERING_GRAPH = 'true'
uv run python -m packages.eakg onboard --id <repository_id> --engineering-graph
```

If `glab repo clone` fails inside onboard, clone manually then pass local path:

```powershell
$env:GITLAB_HOST = 'gitlab.pnmac.com'
glab repo clone '<group>/<project>' .eakg-workspace/<repository_id> -- --filter=blob:none --branch main --single-branch
uv run python -m packages.eakg onboard --id <repository_id> --local-path .eakg-workspace/<repository_id> --engineering-graph
```

Expect JSON stages: `clone` ok, `extract` ops>0, `graph_store` named graph, `engineering_graph` ok|failed|skipped.

### 5. Cross-app + smoke

```powershell
uv run python -m packages.eakg cross-app
uv run python -m packages.eakg query search <needle> --limit 5
uv run python -c @"
import asyncio, json
from packages.common.settings import get_settings
get_settings.cache_clear()
from packages.common.providers.factory import get_graph_store
get_graph_store.cache_clear()
from packages.eakg.query import describe_application
async def main():
    print(json.dumps(await describe_application(get_graph_store(), '<repository_id>'), indent=2)[:1500])
asyncio.run(main())
"@
```

Optional AST: `search_code` / MCP tool with `application_id` + query (after eng graph file exists).

### 6. Session hygiene

- Append dated note to `logs.md`
- Restart MCP (`:8001`) if tools client must see new registry apps for credentials destinations
- Do **not** commit secrets; shards under `data/eakg/repos/` are gitignored

## Anti-patterns

- Hard-coding app lists in detectors — registry only
- `glab repo clone --hostname …` (broken); use `GITLAB_HOST` or `glab api --hostname`
- Merging SSE AST into LoanOps `graphify-out/`
- Skipping `--api-project-path` on multi-project solutions (wrong surface)

## Done when

- [ ] Registry row `index_status: indexed`
- [ ] `interface.json` / GraphDB named graph present
- [ ] `engineering/graph.json` present if Graphify on PATH
- [ ] `describe_application` returns proxies/packages (or empty lists with `source`)
- [ ] `cross-app` completed without error
