# Debug Layer 2 (one request)

Search the repo for `LAYER2-BP` — those comments are the hop points. Set a **red gutter breakpoint** on the next executable line after each comment (Cursor: click left of the line number).

Kill anything already on `:8000` / `:8001` first. Then **Run and Debug**:

| Flow | `.env` | Launch compound |
|------|--------|-----------------|
| **A** UI → Agent in-process | `TOOLS_CLIENT__PROVIDER=modular` | `Layer2: Flow A (modular — Agent only)` |
| **B** UI → Agent → MCP | `TOOLS_CLIENT__PROVIDER=mcp` | `Layer2: Flow B (mcp hop — Agent + MCP)` |
| **C** Cursor Chat | (flag unused) | `Layer2: Flow C (Cursor — MCP only)` |

Trigger: UI `POST /chat`, or Cursor MCP tool, or:

```http
POST http://127.0.0.1:8000/chat
Content-Type: application/json

{"message": "loan summary for 1000002245"}
```

`justMyCode` is **off** so you can step into `packages.*`.

## Breakpoints (`LAYER2-BP`)

| ID | Flow | File | What you see |
|----|------|------|----------------|
| A1 | A B | `projects/LoanOps.AgentApi/apps/agent_api/main.py` | `/chat` after factories — inspect `tools_client` type |
| A2 | A B | `projects/LoanOps.Tools/packages/tools/factory.py` | `modular` vs `mcp` branch |
| A3 | A B | `projects/LoanOps.AgentCore/packages/agent_core/_agent.py` | `run_agent_turn` — intent, then LLM tool loop |
| A4 | A B | same `_agent.py` `_execute_tools` | LLM chose `tc.name` / args before `tools_client.call` |
| A5 | A | `projects/LoanOps.Tools/packages/tools/modular_tools.py` | in-process helper dispatch |
| B1 | B | `projects/LoanOps.Tools/packages/tools/mcp_tools_client.py` | Agent about to HTTP `tools/call` |
| C1 | B C | `projects/LoanOps.McpServer/packages/mcp_server/server.py` | MCP wrapper e.g. `search_sse_apis` → `_run` |
| C2 | B C | same `execute_tool` | auth / scope / EAKG vs SSE |
| S1 | A B C | `projects/LoanOps.Sse/packages/sse/tools.py` | `handle_search_sse_apis` keyword + optional EAKG block |
| S2 | A B C | same | `handle_call_sse_api` live GET |

**Flow A path:** A1 → A2 → A3 → A4 → A5 → S1/S2  
**Flow B path:** A1 → A2 → A3 → A4 → B1 → C1 → C2 → A5 (inside MCP process) → S1/S2  
**Flow C path:** C1 → C2 → A5 (MCP process) → S1/S2  

Related: `docs/THREE_QUERY_FLOWS.md`.
