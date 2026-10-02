# Onboard repository #N (registry-only)

EAKG never hard-codes Escrow/Fees/LoanServices. New apps = registry row + onboard.

## Steps

1. Register (no clone yet):

```powershell
uv run python -m packages.eakg register `
  --id <repo_id> `
  --application "<Display Name>" `
  --application-id <repo_id> `
  --git-url https://gitlab.pnmac.com/<group>/<project>.git `
  --gitlab-project-id <id> `
  --api-project-path src/<ApiProject> `
  --team <group>
```

2. Onboard (glab clone into `.eakg-workspace/<id>` unless `--local-path` set):

```powershell
uv run python -m packages.eakg onboard --id <repo_id>
```

3. Rebuild cross-app + review:

```powershell
uv run python -m packages.eakg cross-app
uv run python -m packages.eakg review --pilot   # or manual approve/reject
uv run python -m packages.eakg publish
```

4. Smoke:

```powershell
uv run python -m packages.eakg query search <needle> --limit 5
uv run python -m packages.eakg query impact <repo_id>
```

## Proof already in tests

`packages/eakg/tests/test_eakg.py` registers a fourth synthetic repo and onboards
without editing detector code — registry-driven path.

## Live repo #4+

Pick next Plaisse app when ready; pass real `--git-url` / `--gitlab-project-id`.
Do not invent URLs in this doc. Prefer apps that share LoanServices SDK or TAAC
`ServiceUrls` so cross-app detectors fire.
