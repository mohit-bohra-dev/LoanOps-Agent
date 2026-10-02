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
