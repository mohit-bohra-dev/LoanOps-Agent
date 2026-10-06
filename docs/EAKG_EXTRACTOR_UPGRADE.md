# EAKG .NET extractor upgrade

**Status:** **Roslyn shipping** (D5). Regex = fallback only.

## Default

```text
EAKG__EXTRACTOR=auto   # try Roslyn, else regex
EAKG__EXTRACTOR=roslyn # fail if tool/dotnet missing
EAKG__EXTRACTOR=regex  # force legacy
```

Tool: `tools/eakg-dotnet-extract` (Microsoft.CodeAnalysis.CSharp syntax trees).  
Python wrapper: `packages/eakg/extractors/roslyn.py`.  
Detector id: `dotnet_roslyn` v2.0.0.

## What Roslyn extracts

Controller classes → HttpGet/Post/… methods with correct attribute→method binding,
routes, authorize/allow-anonymous, line evidence.

## What stays in Python regex

PackageReference, appsettings ServiceUrls/topics/connections, proxy classes,
String.Format route compositions.

## Phase 2 (not D5)

| Tool | Role |
|---|---|
| Tree-sitter | Generic / cross-language parsing |
| CodeQL | Deep / security-style analysis |

## Build tool (once)

```powershell
dotnet build tools/eakg-dotnet-extract/EakgDotnetExtract.csproj -c Release
```

## Acceptance (met)

- Same `ApiOperationFact` / evidence model
- Fixture tests: GetLoanSummary + GetPaymentSchedules via `extractor=roslyn`
- `EAKG__EXTRACTOR=auto` falls back to regex if Roslyn unavailable

## Live GitLab clones (2026-10-03)

Re-onboarded existing `.eakg-workspace/{escrow,fees,loanservices}` with `EAKG__EXTRACTOR=roslyn` (same commits as registry). Manifest `extractor: dotnet_roslyn`. Query `GetLoanSummary` evidence `detectorId=dotnet_roslyn`.

| Repo | Regex ops (2026-10-02) | Roslyn ops (2026-10-03) |
|---|---|---|
| loanservices | 229 | 261 |
| escrow | 482 | 510 |
| fees | 236 | 242 |

```powershell
$env:EAKG__EXTRACTOR = "roslyn"
uv run python -m packages.eakg onboard --id loanservices --local-path ".eakg-workspace/loanservices"
uv run python -m packages.eakg cross-app
```

Tool path: `roslyn.py` finds `tools/eakg-dotnet-extract` via cwd/git (uv copies eakg into `.venv`).
