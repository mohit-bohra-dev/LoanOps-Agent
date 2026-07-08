# Real Data Integration — Mock ↔ Real Toggle

## Overview

The LoanOps-Agent currently uses `data/loans.json` (synthetic) as its loan database and hardcoded SOP files for RAG. We want to integrate **real APIs** (a loan servicing API) and **Confluence pages** (for SOPs/policies) while keeping a dead-simple toggle to switch between mock and real data at runtime — no code changes, just env vars.

---

## Architecture: The Toggle

A single env var drives the entire switch:

```env
DATA_MODE=mock    # default — uses loans.json + local Qdrant SOPs
DATA_MODE=real    # uses real loan API + Confluence pages
```

This plugs into the existing Provider pattern already in the codebase. We add two new provider categories:

| Provider | Mock | Real |
|---|---|---|
| **LoanDataProvider** | `JsonFileLoanProvider` (current loans.json logic) | `RestApiLoanProvider` (calls real servicing API) |
| **PolicySourceProvider** | `QdrantPolicyProvider` (current local RAG) | `ConfluencePolicyProvider` (fetches Confluence pages → RAG) |

Both are controlled by `DATA_MODE` (or separate `LOAN_PROVIDER` / `POLICY_PROVIDER` env vars for finer control).

---

## User Review Required

> [!IMPORTANT]
> **What real APIs do you have?** I need to know:
> 1. The base URL of your real loan servicing API (REST? SOAP? GraphQL?)
> 2. How it authenticates (API key, OAuth2, mTLS?)
> 3. Does it match the current `LoanSummary` schema, or do we need field mapping?
> 4. Your Confluence base URL and auth method (API token? OAuth?)
> 5. Which Confluence space(s) / page IDs hold the SOPs we should RAG over?

> [!WARNING]
> The plan below is fully buildable **without** answers to the above — mock stays mock. The real providers will just be stubs that raise `NotImplementedError` until you give me the actual API details.

---

## Proposed Changes

### 1. Settings

#### [MODIFY] [settings.py](file:///d:/Programming-Projects/LoanOps-Agent/packages/common/settings.py)

Add two new config sections:

```python
class LoanApiConfig(BaseModel):
    base_url: str = ""
    api_key: str = ""
    timeout_seconds: int = 10

class ConfluenceConfig(BaseModel):
    base_url: str = ""           # e.g. https://yourco.atlassian.net
    api_token: str = ""
    username: str = ""           # Atlassian email
    space_keys: list[str] = []   # e.g. ["SERV", "POLICY"]

class DataConfig(BaseModel):
    mode: Literal["mock", "real"] = "mock"
    loan_api: LoanApiConfig = Field(default_factory=LoanApiConfig)
    confluence: ConfluenceConfig = Field(default_factory=ConfluenceConfig)

# Add to Settings:
data: DataConfig = Field(default_factory=DataConfig)
```

Env vars:
```env
DATA__MODE=mock            # or real
DATA__LOAN_API__BASE_URL=https://your-servicing-api.com
DATA__LOAN_API__API_KEY=secret
DATA__CONFLUENCE__BASE_URL=https://yourco.atlassian.net
DATA__CONFLUENCE__API_TOKEN=...
DATA__CONFLUENCE__USERNAME=you@co.com
DATA__CONFLUENCE__SPACE_KEYS=["SERV","POLICY"]
```

---

### 2. Loan Data Provider

#### [NEW] `packages/common/providers/loan_data.py`

Protocol + two implementations:

```python
# Protocol
class AbstractLoanDataProvider(ABC):
    async def get_loan(self, loan_id: str) -> dict | None: ...
    async def search_by_name(self, name: str) -> list[dict]: ...

# Mock: reads loans.json (extracts the current LOANS_DB logic from tools_api/main.py)
class JsonFileLoanProvider(AbstractLoanDataProvider): ...

# Real: calls your REST API
class RestApiLoanProvider(AbstractLoanDataProvider): ...
```

#### [MODIFY] [factory.py](file:///d:/Programming-Projects/LoanOps-Agent/packages/common/providers/factory.py)

Add `get_loan_data_provider()`:

```python
@lru_cache(maxsize=1)
def get_loan_data_provider() -> AbstractLoanDataProvider:
    cfg = _get_settings()
    if cfg.data.mode == "real":
        from packages.common.providers.loan_data import RestApiLoanProvider
        return RestApiLoanProvider(cfg.data.loan_api)
    from packages.common.providers.loan_data import JsonFileLoanProvider
    return JsonFileLoanProvider()
```

#### [MODIFY] [tools_api/main.py](file:///d:/Programming-Projects/LoanOps-Agent/apps/tools_api/main.py)

- Remove the `LOANS_DB` in-memory dict and `load_loans_db()` — that logic moves into `JsonFileLoanProvider`
- Replace direct dict lookups with `await get_loan_data_provider().get_loan(loan_id)`

---

### 3. Policy Source Provider

#### [NEW] `packages/common/providers/policy_source.py`

Protocol + two implementations:

```python
class AbstractPolicySourceProvider(ABC):
    async def fetch_pages(self) -> list[PolicyPage]: ...

# Mock: reads data/sops/*.md files (current behavior, already ingested into Qdrant)
class LocalFilePolicyProvider(AbstractPolicySourceProvider): ...

# Real: fetches pages from Confluence REST API and returns raw text
class ConfluencePolicyProvider(AbstractPolicySourceProvider): ...
```

`ConfluencePolicyProvider` hits `GET /wiki/rest/api/content?spaceKey=SERV&expand=body.storage` and converts HTML body → plain text. The RAG ingest pipeline (`packages/rag/ingest.py`) calls this provider instead of reading files directly.

#### [MODIFY] [factory.py](file:///d:/Programming-Projects/LoanOps-Agent/packages/common/providers/factory.py)

Add `get_policy_source_provider()`.

#### [MODIFY] `packages/rag/ingest.py`

Switch from `glob("data/sops/*.md")` to calling `get_policy_source_provider().fetch_pages()`.

---

### 4. .env Files

#### [NEW] `.env.mock` — zero-credential local dev

```env
DATA__MODE=mock
# ... everything else stays the same as current .env
```

#### [NEW] `.env.real` — production/staging (fill with real creds)

```env
DATA__MODE=real
DATA__LOAN_API__BASE_URL=https://...
DATA__LOAN_API__API_KEY=...
DATA__CONFLUENCE__BASE_URL=https://yourco.atlassian.net
DATA__CONFLUENCE__API_TOKEN=...
DATA__CONFLUENCE__USERNAME=you@yourco.com
DATA__CONFLUENCE__SPACE_KEYS=["SERV"]
```

#### [MODIFY] `.env.example`

Add the new `DATA__*` variables with comments.

---

### 5. Quick-Switch Convenience (PowerShell)

#### [NEW] `switch-mode.ps1`

```powershell
param([ValidateSet("mock","real")][string]$Mode = "mock")
Copy-Item ".env.$Mode" ".env" -Force
Write-Host "Switched to $Mode mode. Restart services to apply."
```

Usage: `.\switch-mode.ps1 -Mode real`

---

## File Summary

| File | Action |
|---|---|
| `packages/common/settings.py` | Add `DataConfig`, `LoanApiConfig`, `ConfluenceConfig` |
| `packages/common/providers/loan_data.py` | **NEW** — Protocol + Mock + Real impl |
| `packages/common/providers/policy_source.py` | **NEW** — Protocol + Local + Confluence impl |
| `packages/common/providers/factory.py` | Add `get_loan_data_provider()`, `get_policy_source_provider()` |
| `apps/tools_api/main.py` | Remove `LOANS_DB` dict, use `get_loan_data_provider()` |
| `packages/rag/ingest.py` | Use `get_policy_source_provider()` |
| `.env.mock` | **NEW** — mock preset |
| `.env.real` | **NEW** — real creds preset (gitignored) |
| `.env.example` | Add `DATA__*` vars |
| `switch-mode.ps1` | **NEW** — one-command toggle |

---

## Open Questions

1. **Real loan API**: What is the endpoint and auth scheme? Does it return data in a shape matching `LoanSummary`, or do we need a field mapper?
2. **Confluence auth**: Atlassian Cloud uses API token + email. Is this on-prem (different auth)?
3. **Confluence ingestion strategy**: Should Confluence pages be fetched on-demand per query, or pre-ingested into Qdrant on a schedule (like the current SOPs)?
4. **Per-provider toggle**: Should `DATA__MODE` be a single switch, or should `LOAN_PROVIDER` and `POLICY_PROVIDER` be independently switchable (e.g., real loans + mock policy during development)?

---

## Verification Plan

### Automated
- Extend `packages/common/providers/contract_tests/` with `test_loan_data_provider.py` — runs against both mock and (if env creds present) real.
- `mypy --strict packages/common` — no new errors.

### Manual
- `.\switch-mode.ps1 -Mode mock` → start services → agent answers loan queries from `loans.json` ✅
- `.\switch-mode.ps1 -Mode real` → start services → agent answers from real API ✅
- Confluence: ingest run fetches pages from configured space ✅
