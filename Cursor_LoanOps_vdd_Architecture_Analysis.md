# Cursor Task — Analyze LoanOps `vdd` Branch Before MCP Transformation

## Context

You are working in the `vdd` branch of the LoanOps-Agent repository.

The goal is eventually to transform LoanOps into an end-to-end MCP-based application:

```text
User
  ↓
LoanOps Chat UI
  ↓
Existing Agent / LLM
  ↓
MCP Client
  ↓
LoanOps MCP Server
  ↓
Existing Real APIs
  ↓
Response
  ↓
Agent
  ↓
Chat UI
```

However, **do not implement this yet**.

First, understand the actual implementation in the `vdd` branch. The code in this branch is the source of truth.

Do not rely on assumptions from older versions, README documentation, other branches, or external repositories when the actual code differs.

---

# Primary Task

Perform a thorough architectural analysis of the current `vdd` branch.

Before changing any application code, inspect the repository and determine:

1. What exists today?
2. How does the current LoanOps application work end-to-end?
3. Where are the real APIs called?
4. How are API URLs/configuration loaded from `.env`?
5. How does the current agent select and invoke tools?
6. How does the Chat UI communicate with the agent?
7. What role does Graphify currently play?
8. What parts of the system can be reused for MCP?
9. Where should an MCP Client and MCP Server be introduced?
10. What should remain unchanged?

---

# Important Constraints

## 1. Do not modify application code yet

During this task:

- Do not refactor production code.
- Do not add MCP dependencies.
- Do not create an MCP server.
- Do not replace existing tools.
- Do not change API calls.
- Do not change the Chat UI.
- Do not change `.env` files.
- Do not change agent behavior.

The only requested artifact at this stage is an architecture-analysis document.

## 2. Inspect actual code

Do not assume that the README accurately represents the current implementation.

If documentation and code disagree:

> Treat the code in the `vdd` branch as authoritative.

## 3. Protect secrets

Do not copy or expose:

- API keys
- tokens
- passwords
- secrets
- credentials
- private URLs containing credentials

When documenting `.env`, document variable names and configuration relationships, not secret values.

---

# Areas to Inspect

## 1. Repository Structure

Identify:

- Applications
- Packages
- Libraries
- Services
- Frontend
- Backend
- Agent
- Tools
- API clients
- Configuration
- Tests
- Evaluation
- Graphify
- Infrastructure

Create a concise structure overview.

---

# 2. Chat UI

Determine:

- Technology/framework
- Entry point
- Main chat components
- API/backend endpoint used by the UI
- Streaming mechanism
- Request schema
- Response schema
- Error handling
- Authentication/session handling if present

Document the actual flow:

```text
User
 ↓
Chat UI
 ↓
HTTP/SSE/WebSocket/etc.
 ↓
Backend
```

Identify the exact files responsible for this flow.

---

# 3. Agent / LLM

Determine:

- Which framework is used
- Agent initialization
- Model configuration
- System instructions
- Tool registration
- Tool selection
- Agent execution loop
- Streaming
- Conversation state
- Error handling
- Retry behavior

Document the flow:

```text
User Message
     ↓
Agent
     ↓
LLM
     ↓
Tool Selection
     ↓
Tool Execution
     ↓
Tool Result
     ↓
LLM
     ↓
Final Answer
```

Identify the actual classes/functions/modules involved.

---

# 4. Existing Tools

Inventory every tool currently available to the agent.

For each tool document:

```text
Tool name:
Purpose:
Input:
Output:
Implementation:
Underlying API:
Authentication:
Read/Write:
Where registered:
Where executed:
```

Also determine whether the existing tools are:

- Direct API wrappers
- Internal business functions
- Database operations
- RAG tools
- Search tools
- Graph tools
- Other capabilities

---

# 5. Real API Integration

This is especially important.

Find how LoanOps currently calls the real APIs.

Determine:

- API client classes/modules
- HTTP library
- Base URL configuration
- Environment variable names
- Authentication
- Headers
- Timeouts
- Retry logic
- Error handling
- Request models
- Response models
- API-specific transformations

Document:

```text
Agent Tool
   ↓
API Client
   ↓
Configuration
   ↓
Real API
```

Identify the exact files/classes/functions.

Do not expose secret values.

---

# 6. `.env` / Configuration

Inspect configuration handling.

Determine:

- Which `.env` variables configure APIs
- Where they are loaded
- Which settings classes/modules consume them
- Whether configuration is centralized
- Whether different APIs have separate configuration
- How local/dev environments are handled

Document only variable names and their purpose.

Example:

```text
LOAN_API_URL
CUSTOMER_API_URL
PAYMENT_API_URL
```

Do not print their actual values.

---

# 7. Authentication and Authorization

Determine:

- How LoanOps authenticates to external APIs
- Whether API credentials are static, dynamic, or token-based
- Whether user identity is propagated
- Existing RBAC/permissions
- Any authorization checks before tools execute
- Whether tools can perform write operations

Document the current behavior.

---

# 8. Graphify

Inspect the Graphify implementation carefully.

Determine:

- What repository/code Graphify analyzes
- What nodes represent
- What relationships represent
- Where the generated graph is stored
- How LoanOps uses the graph
- Whether it participates in agent/tool selection
- Whether it is runtime or build/index time
- Whether it should remain independent from the future API knowledge layer

Important:

Do not assume Graphify represents the external enterprise APIs.

Explicitly document what it currently represents based on the code.

---

# 9. RAG

Inspect the RAG implementation.

Determine:

- Data sources
- Ingestion
- Chunking
- Embedding
- Storage/index
- Retrieval
- Reranking if any
- How the agent uses retrieved context

Determine whether RAG and future MCP capability discovery should remain separate or interact.

---

# 10. Safety

Inspect existing safety mechanisms.

Determine:

- PII detection/redaction
- Prompt injection handling
- Input validation
- Output filtering
- Tool safety
- Sensitive-data handling

Identify what should happen before and after MCP tool calls.

---

# 11. Evaluation / Testing

Inspect:

- Unit tests
- Integration tests
- Agent evaluations
- Tool evaluations
- RAG evaluations
- Safety evaluations
- Ragas/custom metrics
- CI evaluation gates

Determine how MCP tool selection could later be evaluated.

Do not implement the evaluation changes yet.

---

# 12. Audit / Observability

Determine whether the current system tracks:

- User/session
- Agent request
- Tool call
- API call
- Latency
- Errors
- Token usage
- Audit events

Identify where these are implemented.

---

# 13. Existing MCP Code

Search the entire repository for:

```text
MCP
Model Context Protocol
mcp
FastMCP
MCPClient
MCPServer
tool/list
tools/list
stdio
SSE
streamable HTTP
```

If MCP already exists anywhere in the `vdd` branch:

- Explain what it does.
- Identify server/client components.
- Identify transports.
- Identify tools.
- Explain how it integrates with the existing agent.

Do not modify it.

---

# Produce This Document

Create:

```text
docs/CURRENT_ARCHITECTURE.md
```

Use the following structure.

---

# Current LoanOps Architecture

## 1. Executive Summary

Explain in a few paragraphs what LoanOps currently does and how the major components interact.

---

## 2. Repository Structure

Show the relevant structure:

```text
...
```

Explain the purpose of important directories.

---

## 3. Current Runtime Architecture

Provide an ASCII architecture diagram.

Example:

```text
┌─────────────┐
│   Chat UI   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Agent API   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Agent/LLM   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Tools     │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Real APIs   │
└─────────────┘
```

Replace this with the actual architecture discovered in the code.

---

## 4. End-to-End Request Flow

Describe exactly what happens when a user sends:

```text
"What is the status of loan 12345?"
```

Follow the request through the actual code.

Include relevant file paths and important functions/classes.

---

## 5. Chat UI

Document:

- Framework
- Components
- API endpoints
- Streaming
- Request/response flow

---

## 6. Agent

Document:

- Framework
- Initialization
- Model
- Instructions
- Tool registration
- Tool selection
- Execution
- Streaming

---

## 7. Tool Inventory

Create a table:

| Tool | Purpose | API | Read/Write | Registration | Implementation |
|---|---|---|---|---|---|

---

## 8. Real API Integration

Document each API integration.

| API | Client | Configuration | Authentication | Purpose |
|---|---|---|---|---|

Do not include secret values.

---

## 9. Configuration

Document:

```text
.env
 ↓
Settings
 ↓
API Clients
 ↓
External APIs
```

Include environment variable names only.

---

## 10. Graphify

Explain exactly what Graphify represents and how it is used.

---

## 11. RAG

Explain the current RAG pipeline.

---

## 12. Safety

Explain current safety mechanisms.

---

## 13. Evaluation

Explain current evaluation/testing architecture.

---

## 14. Audit and Observability

Explain current logging/audit/tracing.

---

## 15. Existing MCP

Document any MCP implementation already present.

---

# MCP Transformation Assessment

After documenting the current system, add this section.

## 16. What Should Remain Unchanged

List components that should NOT need major changes.

For example:

```text
Chat UI
Real APIs
.env configuration
API clients
RAG
Graphify
Safety
Evaluation
```

Only list these if the actual code supports the conclusion.

---

## 17. What Needs to Change

Identify the minimum changes required to introduce:

```text
Existing Agent
      ↓
MCP Client
      ↓
MCP Server
      ↓
Existing API Clients
      ↓
Real APIs
```

For each change specify:

```text
Current:
...

Proposed:
...

Files affected:
...

Risk:
...
```

---

## 18. Proposed MCP Architecture

Provide an architecture diagram based on the actual code.

The target concept is:

```text
                         LoanOps
┌─────────────────────────────────────────────────┐
│                                                 │
│  Chat UI                                        │
│     │                                           │
│     ▼                                           │
│  Existing Agent                                 │
│     │                                           │
│     ▼                                           │
│  MCP Client                                     │
│     │                                           │
│     ▼                                           │
│  MCP Server                                     │
│     │                                           │
│     ▼                                           │
│  Existing API Clients                           │
│     │                                           │
└─────┼───────────────────────────────────────────┘
      │
      ▼
 Existing Real APIs
```

Modify the architecture according to what you discover.

---

## 19. MCP Tool Boundary

Recommend where the MCP boundary should sit.

Explicitly answer:

- Should existing tools become MCP tools?
- Should existing API clients remain unchanged?
- Should MCP call API clients directly?
- Should the agent call MCP instead of direct tools?
- Where should validation occur?
- Where should authorization occur?
- Where should audit occur?

---

## 20. Capability Model

Propose an initial capability representation.

Example:

```yaml
name:
description:
domain:
input_schema:
output_schema:
read_only:
permissions:
examples:
not_for:
api_mapping:
```

Do not implement it yet.

---

## 21. API Discovery — Future Phase

Explain how the system could eventually support:

```text
OpenAPI
Source code
Tests
API documentation
Authorization policies
        ↓
API Capability Catalog
        ↓
Semantic Discovery
        ↓
MCP
```

Keep this explicitly separate from the first MCP implementation.

---

## 22. Migration Plan

Create an incremental implementation plan:

### Phase 1
Understand and baseline current behavior.

### Phase 2
Add MCP Server.

### Phase 3
Expose one existing real API through MCP.

### Phase 4
Add MCP Client to the existing agent.

### Phase 5
Move additional capabilities.

### Phase 6
Add capability discovery.

### Phase 7
Add evaluation.

### Phase 8
Add advanced API intelligence.

For every phase identify:

- Files/modules likely affected
- Dependencies
- Tests required
- Rollback strategy

---

## 23. Risks

Identify risks including:

- Breaking existing agent behavior
- MCP latency
- Authentication propagation
- Tool-selection errors
- Duplicate business logic
- API failures
- Security/PII exposure
- Prompt injection
- Excessive tool count
- Backward compatibility
- Streaming behavior
- Observability gaps

---

## 24. Open Questions

List questions that must be answered before implementation.

Do not invent answers.

Examples:

```text
- Should MCP run in the same process or separately?
- Which MCP transport should be used?
- Should the agent always use MCP or support fallback?
- Which tools should be exposed first?
- How should API authentication be propagated?
- Should MCP own authorization or delegate it?
```

---

## 25. Final Recommendation

Conclude with:

1. Current architecture summary.
2. Recommended MCP insertion point.
3. Components to preserve.
4. Components to modify.
5. First implementation milestone.
6. Risks requiring attention.

---

# Final Rules

1. **Do not write application code in this task.**
2. **Do not modify `.env`.**
3. **Do not expose secrets.**
4. **Do not assume README = implementation.**
5. **Use the `vdd` branch code as the source of truth.**
6. **Do not replace existing real API integrations.**
7. **Do not introduce mock APIs.**
8. **Do not redesign the Chat UI yet.**
9. **Do not redesign Graphify.**
10. **Do not implement MCP yet.**
11. **Do not commit changes automatically.**
12. Only create/update:
   `docs/CURRENT_ARCHITECTURE.md`

After completing the analysis, provide a concise summary in the Cursor response showing:

- What you discovered
- Current request flow
- Existing API integration
- Existing tool architecture
- Recommended MCP boundary
- Major risks
- Files that would likely change during implementation

Wait for further instructions before implementing the MCP transformation.
