# EAKG extractor upgrade

**Status:** **Roslyn 2.1.0** (controllers + Minimal APIs) + **tree-sitter** for
Python/Node. Regex = .NET surface-fact fallback only.

## Default

```text
EAKG__EXTRACTOR=auto   # try Roslyn, else regex (C# ops only)
EAKG__EXTRACTOR=roslyn # fail if tool/dotnet missing
EAKG__EXTRACTOR=regex  # force legacy C# controllers
```

Tree-sitter adapters run when inventory sees python / javascript / typescript.
No separate env var.

## C# — Roslyn

Tool: `tools/eakg-dotnet-extract` (Microsoft.CodeAnalysis.CSharp syntax trees).  
Python wrapper: `packages/eakg/extractors/roslyn.py`.  
Detector id: `dotnet_roslyn` **v2.1.0**.

Extracts:

- Controller classes → HttpGet/Post/… + Authorize / AllowAnonymous
- Minimal APIs → `MapGet`/`MapPost`/… + same-method `MapGroup` + fluent
  `RequireAuthorization` / `AllowAnonymous` / `WithName`

## Non-.NET — tree-sitter

| Detector | Frameworks |
|---|---|
| `treesitter_python` | FastAPI / APIRouter, Flask / Blueprint |
| `treesitter_node` | Express, Fastify |

Package: `packages/eakg/extractors/treesitter/`. Adapter id `treesitter_api`
(`fatal=False`).

## Merge + identity

`packages/eakg/merge_api.py` + `route_identity.py`:

- Canonical key: `METHOD:/normalized/path` (`:id` / `<int:id>` / `{id:int}` → `{id}`)
- Precedence: Roslyn controller > Minimal API > tree-sitter; evidence merged
- RDF op/capability local names hash the route key — **re-onboard** after upgrade

## What stays in Python regex (.NET)

PackageReference, appsettings ServiceUrls/topics/connections, proxy classes,
String.Format route compositions.

## Out / parked

| Item | Status |
|---|---|
| CodeQL | Out (license); taint = SonarQube on SSE pipelines |
| Java / Go routes | Backlog |
| SonarQube findings → graph | Later (`TASKS.md`) |

## Build tool (once)

```powershell
dotnet build tools/eakg-dotnet-extract/EakgDotnetExtract.csproj -c Release
```

## Acceptance

- Fixture tests: controller ops, Minimal API ops, Python/Node fixtures
- `EAKG__EXTRACTOR=auto` falls back to regex if Roslyn unavailable
- Java-only repo still fails with no API extractor
