# Live SSE swagger verification

**Status:** Done — 2026-10-03. Loan Services **dev** swagger fetch + parse + GET invoke.

Related: [`EAKG_SWAGGER_EXPORT.md`](EAKG_SWAGGER_EXPORT.md) (separate: ask app teams for CI `swagger tofile`), [`MCP_BASELINE.md`](MCP_BASELINE.md).

Re-run (from repo root, after M2M refresh if swagger 401):

```powershell
.\scripts\auth\refresh-sse-m2m.ps1
uv run python scripts/verify_live_sse_swagger.py
```

Local dump (gitignored `data/sse-live/`):

- `{id}.swagger.json` — raw List B spec
- `operations.json` — parsed method/path/`operationId` index

The script **ignores** `SSE__FIXTURE_PATH`. Product factory still uses that path when set, even if `SSE__USE_FIXTURE=false` — so Agent/MCP catalog can stay the 6-op hand file while this check hits live swagger.

## Evidence (2026-10-03)

| Check | Result |
|---|---|
| Host | `https://loanservicesapi-plaisse-dev.pnmac.com` |
| Spec URL | `/swagger/1.0/swagger.json` |
| Auth | Subservicing Auth0 M2M → `SSE__API_KEY` (refreshed first; stale token → swagger **401**) |
| Parse | **292** operations via `OpenApiCatalogService` (`fixture_path=None`) |
| Hand catalog paths (`data/sse-loanservices-catalog.json`) | All 6 **HIT** (template `{loan_id}` ≡ live `{id}`) |
| Live summary op | `GET /api/Loans/{id}/Summary` — **no** `operationId` in spec (`loanservices:GET_api_loans_id_summary`) |
| Invoke | **HTTP 200** (body not recorded; no PII in this doc) |

## Not proven

- Escrow / Fees / PennEDocs / CoreComponents swagger URLs (not in this `.env` `SSE__SWAGGER_LINKS`)
- Product default catalog = live 292 ops (still fixture-path catalog unless path cleared)
- App-team CI `dotnet swagger tofile` ([`EAKG_SWAGGER_EXPORT.md`](EAKG_SWAGGER_EXPORT.md))
