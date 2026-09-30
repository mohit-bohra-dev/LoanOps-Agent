# MCP Baseline

Phase 0 of `MCP_ARD_IMPLEMENTATION_PLAN.md`. No application behavior was changed.

Recorded on 2026-09-30 against `vdd` HEAD `8235e90` (`chore: remove tools_api; document SSE-only answer path`). Architecture detail is in `docs/CURRENT_ARCHITECTURE.md`. This file records what the running tree actually did.

Secret values are not included.

Post-baseline (ADR-011): `python -m packages.mcp_server` is a real Streamable HTTP MCP listener on port 8001. Chat still uses the in-process tools client. The chunker hang in section 5 was fixed in that change so pytest can finish; the concrete-import failure was left as recorded here.

---

## 1. What was measured

| Check | Result |
|---|---|
| Unit tests, `packages/rag` excluded | **164 passed, 1 failed**, 1 deselected, 1.40s |
| Full `pytest` including `packages/rag` | **Hangs.** Does not finish. |
| `GET /health` via ASGI test client | **200.** Boot ~420 ms. All 10 provider factories construct. |
| `POST /chat` — "What is the status of loan 1000002245?" | **200 SSE**, ~919 ms, body is an error event. LLM never ran. |
| `search_sse_apis` query `loan summary` | **Success**, ~1.1 ms, local catalog |
| `call_sse_api` `getLoanSummary` | **HTTP 401** from the real host, ~462 ms |
| `list_sse_apis` via `POST /mcp/tools/call` | **Success**, ~2.1 ms, 6 operations, 1 source |
| `search_docs` | **Fails immediately.** `docs not configured` |
| Eval runner | **Not run.** No saved report under `out/`. Golden file has 50 lines. |
| Sidebar UI in a browser | **Not run.** Same backend call as `call_sse_api` above. |

`uv` is not on PATH in this shell. Tests used `.venv\Scripts\python.exe -m pytest`.

---

## 2. Configuration actually loaded

From `Settings()` against the local `.env`. Names and non-secret facts only.

| Setting | Loaded value |
|---|---|
| `LLM__PROVIDER` | `bedrock` |
| Bedrock chat | region `us-west-2`, model `us.amazon.nova-pro-v1:0`, named profile set, API key empty |
| `EMBEDDING__PROVIDER` | `bedrock` |
| `VECTOR_STORE__PROVIDER` | `qdrant` |
| Qdrant | `path` set (embedded). URL still `http://localhost:6333`. Collection `sops` |
| `TOOLS_CLIENT__PROVIDER` | `modular` |
| `AGENT_ROLE` | `system` |
| `SSE__USE_FIXTURE` | `false` |
| `SSE__FIXTURE_PATH` | set, file name `sse-loanservices-catalog.json` |
| `SSE__API_KEY` | set (value not recorded) |
| `SSE__API_BASE_URL` host | `loanservicesapi-plaisse-dev.pnmac.com` |
| `SSE__SWAGGER_LINKS` | 1 link, id `loanservices` |
| `SQL_SERVER__FIXTURE_MODE` | `true` |
| `DATA__LOAN_SOURCE` | `mock` |
| `DATA__SOP_SOURCE` | `confluence` |
| `PII__PROVIDER` / `PII__MODE` | `stub` / `redact_audit_only` |
| `SAFETY__PROVIDER` | `stub` |
| `AUDIT__SINK` | `jsonl` |

Catalog selection in `get_tools_client_provider`: a fixture path is used when `SSE__USE_FIXTURE` is true **or** `SSE__FIXTURE_PATH` is non-empty. This environment has fixture mode off and a path set, so the catalog is the local JSON file, not a live swagger fetch. HTTP invocation still targets the host above.

`DATA__LOAN_API__*` is also set and points at the same host. The agent turn does not call `RestApiLoanProvider`.

---

## 3. Tool surface at baseline

`ModularToolsClient.list_tools()` for role `system`:

```text
search_sse_apis
list_sse_apis
call_sse_api
search_docs
```

`GET /health` providers, all `ok: true` at construct time (no live LLM or API call): chat, embedding, pii, content_safety, audit_sink, secrets, telemetry, tools_client, prompt_store, session_store. Vector store is not in the health list when Qdrant `path` is set (`_agent_owns_vector_store` is false).

---

## 4. Representative calls

### 4.1 Catalog search

```text
tool: search_sse_apis
args: query="loan summary", limit=5
success: true
latency: ~1.1 ms
first hit:
  id: loanservices:getLoanSummary
  GET /api/Loans/{loan_id}/Summary
  summary: Get loan summary
  params: loan_id (path, required, string)
```

Search does not touch the network. It scores the local catalog.

### 4.2 Live API invocation

```text
tool: call_sse_api
args: operation_id=getLoanSummary, path_params.loan_id=1000002245
success: true (tool layer)
latency: ~462 ms
downstream: HTTP 401
ok: false
host: loanservicesapi-plaisse-dev.pnmac.com
body: non-JSON text (not copied)
```

The tool wrapper succeeded. The enterprise API rejected the bearer. No loan fields were returned. Sidebar lookup uses this same call (`getLoanSummary`, then `getBorrowerSummary`) and would fail the same way.

### 4.3 Catalog list (custom `/mcp` HTTP, not MCP protocol)

```text
POST /mcp/tools/call
body: {"name":"list_sse_apis","arguments":{"limit":20}}
status: 200
latency: ~2.1 ms
success: true
header: Loaded 6 operations from 1 sources
```

The six operations are the paths in `data/sse-loanservices-catalog.json` (loan, summary, borrower summary, payment schedules, escrows, delinquencies). This is not the full enterprise swagger.

### 4.4 Docs search

```text
tool: search_docs
args: query="escrow analysis", top_k=3
success: false
latency: ~0 ms
error: docs not configured
```

Cause, from constructing the providers directly:

```text
embedding: BedrockEmbeddingProvider constructed
vector: TypeError: QdrantVectorStoreProvider.__init__() got an unexpected keyword argument 'path'
```

`get_tools_client_provider` swallows that exception and sets `docs = None`. `search_docs` cannot run until the vector-store factory matches the installed `provider_contracts` constructor. RAG ingest into collection `sops` is a separate path and was not executed.

### 4.5 Chat

```text
POST /chat
message: What is the status of loan 1000002245?
session_id: baseline-1
status: 200 text/event-stream
latency: ~919 ms
SSE payload: {"error": "Error when retrieving token from sso: Token has expired and refresh failed"}
```

Bedrock auth uses a named AWS profile. SSO refresh failed (`InvalidGrantException` / `TokenRetrievalError`). The agent loop did not start. No tool calls, no answer, no audit turn record for a successful completion.

Health still reports chat `ok` because the factory only constructs the client.

---

## 5. Test suite

Command that completed:

```text
.venv\Scripts\python.exe -m pytest -q --tb=line -m "not integration" --ignore=packages/rag
```

| Result | Detail |
|---|---|
| 164 passed | agent API, agent core, provider contracts, scopes, modular tools, SQL read-only classifier, eval metrics, safety, SSE catalog |
| 1 failed | `apps/agent_api/tests/test_agent_api.py::test_no_concrete_provider_imports` |
| 1 deselected | integration marker outside `packages/rag` |

Failure:

```text
apps/agent_api/mcp_routes.py imports
    from provider_contracts.tools_client import ToolCall
```

The test forbids any `provider_contracts` import under `apps/agent_api/`. That import is on the custom `/mcp/tools/call` path.

Hang:

```text
packages/rag/tests/test_rag.py::test_markdown_chunker_splits_by_header
```

`MarkdownChunker(target_tokens=2)` keeps the default `overlap_tokens=80`. `_split_large_section` sets `position = end_position - overlap_tokens`, which moves backward when overlap is larger than the target. The `while` loop does not terminate. A full `pytest` run reaches this test and never prints a summary.

`packages/rag/tests/test_nearest_neighbour.py` is `@pytest.mark.integration` (needs live embed + vector store). It was not given its own timed run after the suite hang. Vector-store init already fails with the `path` TypeError above, so that test cannot pass against this `.env` until the factory is fixed.

26 Pydantic `datetime.utcnow()` deprecation warnings. Not failures.

---

## 6. Evaluation

`data/golden.jsonl` has 50 items. No `out/eval.json` or other saved runner report is in the tree.

Thresholds in `packages/eval/thresholds.py` (do not lower them):

| Metric | Gate |
|---|---|
| faithfulness | ≥ 0.85 |
| answer_relevance | ≥ 0.85 |
| citation_coverage | ≥ 1.0 |
| refusal_correctness | ≥ 0.95 |
| latency_p95_ms | ≤ 4000 |

This session did not execute `python -m packages.eval.run`. A live golden run needs a working Bedrock SSO session. Ragas faithfulness and answer relevance are skipped when `--skip-llm-metrics` is set.

There is no tool-selection metric yet (`expected_tool`, `expected_operation_id`).

---

## 7. Latency snapshot

Single samples, not percentiles. Not an eval gate result.

| Step | Time |
|---|---|
| ASGI app boot (provider factories) | ~420 ms |
| `search_sse_apis` | ~1.1 ms |
| `list_sse_apis` via `/mcp/tools/call` | ~2.1 ms |
| `call_sse_api` → HTTP 401 | ~462 ms |
| `search_docs` | ~0 ms (failed before I/O) |
| `POST /chat` until SSO error SSE | ~919 ms |

No successful end-to-end answer latency exists for this baseline. The 4000 ms p95 gate is unmeasured against a real model turn.

---

## 8. Gaps that block a meaningful MCP comparison

These are current-behavior facts. Phase 0 does not fix them.

1. **Bedrock SSO expired.** Chat cannot complete a turn. Refresh the named profile before any MCP-vs-in-process latency or answer comparison.
2. **Loan Services bearer returns 401.** `SSE__API_KEY` is present and is sent. The host rejects it. Real API success is not established.
3. **Catalog is a 6-operation local file**, not live swagger, because `SSE__FIXTURE_PATH` is set.
4. **`search_docs` is dead** on this machine: Qdrant provider rejects `path`.
5. **pytest does not finish** while `test_markdown_chunker_splits_by_header` infinite-loops.
6. **One unit test is already red:** concrete import in `mcp_routes.py`.
7. **Custom `/mcp/tools` is not MCP.** Unauthenticated when `X-API-Key` is omitted. Recorded here so later phases do not treat this route as the protocol baseline.

---

## 9. Preserved behavior (do not replace in later phases)

- In-process path: `POST /chat` → `run_agent_turn` → `ModularToolsClient` → `invoke_sse_api` / `DocsService`.
- Tool names and argument shapes for the four tools above.
- SSE host allow-list and bearer attachment inside `invoke_sse_api`.
- Intent router and PII/safety middleware on `/chat` (not exercised successfully this session; code path unchanged).
- Eval threshold numbers.
- Graphify stays off the request path.
- Chat UI contract: one SSE `data:` frame, `AgentTurnOutput` or `{error, turn_id}`.

In-process `ModularToolsClient` remains the fallback until a later phase passes the same checks with a working SSO session and a non-401 API call.
