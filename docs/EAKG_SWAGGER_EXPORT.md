# Ask app teams: export OpenAPI in CI (`dotnet swagger tofile`)

**Status:** Request to Plaisse app teams — not implemented in LoanOps-Agent.

## Why

EAKG hybrid OpenAPI enrichment is more accurate when each API project publishes a
committed or artifact OpenAPI JSON on every `main` build. Static regex extraction
covers controllers; live swagger needs tokens and is flaky for batch indexing.

## Ask (copy to Jira / Slack)

Please add a CI job to each WebApi deployable (Escrow.Api, Fees.WebApi,
LoanServices.WebApi, …):

```yaml
# sketch — adapt to each repo's SDK / test host project
script:
  - dotnet tool restore   # if using swashbuckle CLI
  - dotnet build src/<ApiProject>/<ApiProject>.csproj -c Release
  - dotnet swagger tofile --output openapi.json --host http://localhost src/<ApiProject>/bin/Release/net8.0/<ApiProject>.dll v1
artifacts:
  paths:
    - openapi.json
  expire_in: 30 days
```

Also acceptable: commit `docs/openapi.json` refreshed on merge.

## Contract for EAKG consumers

| Field | Expectation |
|---|---|
| Format | OpenAPI 3.x JSON |
| Auth | No secrets in spec |
| Path | Artifact `openapi.json` or `docs/openapi.json` at repo root / api project |
| Cadence | Every merge to default branch |

Once available, set `EAKG__OPENAPI_MODE=hybrid` (default) and point onboard at the
artifact path (follow-up wiring in `packages/eakg/openapi_enrich.py`).

## Out of scope here

- Changing app Authorization policies
- LoanOps owning their pipelines
