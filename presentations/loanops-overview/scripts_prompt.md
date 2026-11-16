# LoanOps-Agent – Complete Technical Demo Script Generator

## Role

Act as a Principal Software Engineer, AI Solutions Architect, Technical Demo Engineer and Professional Technical Script Writer.

You have access to the complete LoanOps-Agent source code in the current Cursor workspace.

Your task is to inspect the actual implementation and create a complete, executable demonstration of the platform.

I want to demonstrate the entire system to an enterprise technical audience, including:

- Knowledge engineering pipelines.
- EAKG and Knowledge Graph.
- OpenAPI ingestion and API discovery.
- API embeddings and semantic search.
- MCP server and tools.
- AI Agent execution.
- SOP RAG and GraphRAG.
- Engineering Knowledge Graph.
- Langfuse observability.
- AI Agent evaluation.
- Golden Dataset.
- Human feedback and evaluation.
- Continuous improvement architecture.

The final output must contain both:

1. A professional presenter script explaining what is happening.
2. Actual executable commands, API calls, test scripts and UI navigation instructions wherever applicable.

Do not simply write a conceptual demo.

---

# LANGUAGE STYLE (MANDATORY)

Keep all generated content **simple and detailed**. Assume the audience may be technical but not familiar with this codebase.

Rules:

1. **Simple words first.** Prefer plain English over jargon. When a term is required (EAKG, MCP, pgvector, Langfuse), define it once in one short sentence, then use it.
2. **Be detailed, not vague.** Say exactly what happens, where to look, and what “good” looks like. Avoid “the system processes the request” — say *what* it processes and *where* the result appears.
3. **Always include a real example.** Every module must show at least one concrete input → expected output pair from the actual product (synthetic data only).
4. **Always include a use case.** For each component, state one realistic employee or ops scenario that answers: “When would someone need this?”
5. **Show, then explain.** Lead with the example or command; follow with a short “why this matters” paragraph.
6. **No unexplained acronyms.** First mention expands the name.

Example of the required style:

```text
Bad:  "The agent uses semantic search over the capability graph."

Good: "Use case: An ops analyst needs the next payment dates for loan LN-10025.
       Example: They type 'Show me the upcoming payment schedule for loan LN-10025'
       in the chat UI. The agent searches the capability index (a searchable list of
       what our APIs can do), finds the payment-schedule API, calls it, and returns
       the dates with a citation. That is how we avoid guessing which API to use."
```

Apply this style to: module markdown, presenter narration (“What to say”), runbooks, README troubleshooting, and script console messages where they explain a step to a human.

---

# WORKSPACE RULES FOR ALL GENERATED ASSETS

These are non-negotiable when generating demo scripts and docs:

- **Windows PowerShell only** (`powershell` v5.1). Never emit bash syntax — no `&&` / `||` chaining, no `export`, no `rm -rf`. Use separate commands or `;`.
- **uv for all Python execution**: `uv run python demo/scripts/preflight.py`. Never raw `pip install`.
- **Graphify-first research**: before grepping or reading raw source, run `graphify query "<topic>"` / `graphify path "<A>" "<B>"` against `graphify-out/graph.json` to scope exploration. After modifying code files, run `graphify update .`.
- **Provider abstraction**: demo code imports external capabilities only via `packages.common` provider factories (`get_*_provider()`, `packages.common.providers.testing` mocks). Never import `provider_contracts` or a vendor SDK directly in demo scripts.
- **No PII anywhere** — use the synthetic fixtures in `data/` (`data/golden.jsonl`, `data/loans.json`, `data/sops/`).
- Never print secret values; never invoke mutating APIs; every factual demo claim must show a citation or verifiable artifact.

---

# PHASE 1: INSPECT THE ACTUAL SOURCE CODE

Before creating anything, explore the repository thoroughly.

Inspect:

1. Backend entry points and FastAPI routes.
2. Frontend routes and components.
3. AI agent orchestration.
4. MCP server implementation.
5. All registered MCP tools.
6. MCP client integration.
7. OpenAPI processing.
8. EAKG implementation.
9. RDF generation and querying.
10. Capability discovery.
11. ApiIndex and vector search.
12. pgvector / vector store integration.
13. SOP ingestion and embeddings.
14. GraphRAG implementation.
15. Engineering KG and Graphify integration.
16. Existing pipeline execution scripts.
17. Langfuse integration.
18. Evaluation framework.
19. Golden Dataset.
20. Existing tests and fixtures.
21. Docker and deployment configuration.
22. Eval result store backends (`provider_contracts/eval_store`: JSONL, Langfuse, mock) and how eval runs are recorded.
23. Pipeline freshness monitoring (`projects/LoanOps.Pipelines/packages/pipelines/freshness.py`) and the web UI Pipelines view (`apps/web_ui/src/eval/PipelinesView.tsx`).
24. Web UI routes and components (`apps/web_ui/`): chat experience, pipelines/eval views.
25. AWS deployment configuration (`infra/terraform/`: ECS, ECR, RDS, secrets, UI module).

Search for actual CLI commands, API endpoints, configuration variables, MCP tools, test cases and UI routes.

Build an implementation inventory.

For every component classify it as:

- Fully implemented.
- Partially implemented.
- Requires configuration.
- Planned.
- Not implemented.

Do not invent commands, API endpoints, tool names or functionality.

Use the actual source code as the primary reference.

---

# PHASE 2: DESIGN THE DEMO STORY

Create a single business scenario that connects the major components.

Use this scenario:

An employee asks:

"Show me the upcoming payment schedule for loan LN-10025."

The demonstration should explain how the system handles this request from beginning to end.

The expected conceptual flow:

1. Enterprise source code and OpenAPI specifications are processed.
2. Knowledge pipelines generate EAKG and API indexes.
3. Capability embeddings and document knowledge are generated.
4. MCP server exposes enterprise capabilities.
5. AI agent receives the employee's request.
6. Agent discovers relevant capabilities and APIs.
7. Agent selects the appropriate API.
8. Agent invokes the MCP tool.
9. Enterprise API returns the payment schedule.
10. Agent generates the final response.
11. Langfuse records the execution trace.
12. Evaluation framework compares actual behavior with expected behavior.
13. Human reviewers inspect the result.
14. Feedback can become a candidate for the Golden Dataset.
15. Improvements can be validated through regression evaluations.

Adapt this sequence to the actual implementation.

If any step does not exist, mark it as a future capability and do not pretend it works.

---

# PHASE 3: CREATE EXECUTABLE DEMO SCRIPTS

Create a dedicated directory:

`demo/`

Use this structure, adjusting it if necessary:

```text
demo/
├── README.md
├── 00-environment-check.md
├── 01-platform-overview.md
├── 02-knowledge-pipelines.md
├── 03-eakg-and-api-discovery.md
├── 04-mcp-server.md
├── 05-ai-agent-execution.md
├── 06-langfuse-observability.md
├── 07-agent-evaluation.md
├── 08-human-review-and-golden-dataset.md
├── 09-complete-platform-demo.md
├── 10-architecture-and-business-value.md
│
├── scripts/
│   ├── preflight.py
│   ├── run_knowledge_pipeline.py
│   ├── test_eakg.py
│   ├── test_api_discovery.py
│   ├── test_mcp_tools.py
│   ├── run_agent_demo.py
│   ├── inspect_evaluation.py
│   └── verify_demo_results.py
│
├── requests/
│   ├── api-discovery.http
│   ├── mcp-tools.http
│   └── agent-demo.http
│
├── data/
│   └── README.md
│
└── results/
    └── .gitkeep
```

Only create scripts that are supported by actual repository capabilities.

If equivalent scripts already exist, reuse them rather than creating duplicates.

Do not create empty or misleading scripts just to match this structure.

Write the implementation inventory from Phase 1 to `demo/results/implementation-inventory.md` so the demo can cite verified capabilities, not assumptions.

---

# PHASE 4: SCRIPT REQUIREMENTS

Every executable Python script must:

- Use the existing project configuration.
- Reuse existing application services where possible.
- Support configurable environment variables.
- Provide readable console output.
- Include meaningful error messages.
- Return appropriate exit codes.
- Avoid hardcoded credentials.
- Avoid destructive operations.
- Avoid unnecessary dependencies.
- Include type hints where appropriate.

Where suitable, use a consistent console format:

```text
==================================================
LOANOPS AGENT - TECHNICAL DEMONSTRATION
==================================================

[1/5] Checking backend connectivity...
[SUCCESS] Backend is available.

[2/5] Checking MCP server...
[SUCCESS] MCP server is reachable.

[3/5] Checking knowledge infrastructure...
[SUCCESS] EAKG is available.

[4/5] Running API discovery...
[SUCCESS] Expected operation discovered.

[5/5] Demo completed successfully.
```

The output must reflect actual execution results, not fabricated success messages.

Support a dry-run mode wherever appropriate.

---

# PHASE 5: KNOWLEDGE PIPELINE DEMONSTRATION

Demonstrate the existing knowledge-generation processes.

For each pipeline, document:

- Source.
- Processing stages.
- Actual execution command.
- Input parameters.
- Output artifacts.
- Storage destination.
- Validation procedure.
- Expected result.
- Known limitations.

Cover these pipelines where implemented:

1. Code → EAKG.
2. OpenAPI → EAKG.
3. OpenAPI → ApiIndex.
4. EAKG → Capability Embeddings.
5. SOP → Document Embeddings.
6. SOP → GraphRAG.
7. Code → Engineering KG (Graphify).
8. Pipeline freshness monitoring — how the platform tracks whether each knowledge source is current and how the web UI Pipelines view (`apps/web_ui/src/eval/PipelinesView.tsx`) surfaces freshness status.

Create a pipeline demonstration that shows how knowledge is prepared before the agent uses it.

Do not automatically rerun expensive or destructive indexing processes during a demo.

Provide safe execution instructions and distinguish between read-only inspection and actual refresh operations.

---

# PHASE 6: MCP SERVER DEMONSTRATION

Inspect all actual MCP tools.

Previously identified tools include:

- search_sse_apis
- list_sse_apis
- call_sse_api
- search_docs
- search_capabilities
- explain_capability
- find_providers
- impact_of_change
- mcp_auth

Verify the actual registered tool names and schemas before using them.

For each tool document:

- Purpose.
- Input schema.
- Example request.
- Example response.
- What the tool demonstrates.
- How to verify its result.

Demonstrate:

1. MCP server startup.
2. MCP connection.
3. Tool discovery.
4. Capability search.
5. API discovery.
6. API invocation.
7. Documentation search.
8. Knowledge graph queries.

Use the actual configured transport and authentication.

Never bypass authorization for demo convenience.

---

# PHASE 7: AI AGENT DEMONSTRATION

Use the existing agent implementation.

Demonstrate the complete user journey.

Example:

```text
User:
Show me the upcoming payment schedule for loan LN-10025.
```

Show:

1. User input.
2. Agent interpretation.
3. Capability discovery.
4. API selection.
5. Tool arguments.
6. MCP invocation.
7. API result.
8. Final answer.

Where possible, display the actual execution trace and intermediate events.

Demonstrate both surfaces where available:

- API / CLI: call the Agent API directly (`/chat`, `/health` in `projects/LoanOps.AgentApi/`).
- Web UI: open the React chat in `apps/web_ui/`, type the same question, and show the streaming answer with citations.

Do not simulate tool calls if the real implementation can be invoked.

If live API access is unavailable, use existing fixtures or safe mock responses and clearly label the demonstration as simulated.

---

# PHASE 8: LANGFUSE OBSERVABILITY

Inspect the existing Langfuse integration.

Create a walkthrough showing:

- Trace creation.
- Agent execution.
- Tool calls.
- Model interactions.
- Input and output.
- Latency.
- Token usage.
- Errors and retries.
- Prompt and model information where available.

Provide exact navigation instructions based on the actual Langfuse integration.

Do not claim that an event is captured if the current implementation does not emit it.

---

# PHASE 9: EVALUATION DEMONSTRATION

Inspect the current evaluation framework and Golden Dataset.

Create a realistic scenario:

Input:
"Show me the upcoming payment schedule for loan LN-10025."

Expected API:
The correct payment schedule operation identified from the actual OpenAPI index.

Expected behavior:
- Correct API discovery.
- Correct tool selection.
- Correct loan ID argument.
- Successful authorized invocation.
- Accurate final response.
- Appropriate evidence and citations.

Show:

1. How evaluation scenarios are defined.
2. How expected API operations are specified.
3. How actual calls are captured.
4. How expected and actual API selections are compared.
5. How arguments are validated.
6. How final answers are evaluated.
7. How results are recorded — including the actual eval-store backend in use (`provider_contracts/eval_store`: JSONL on disk, Langfuse, or mock; check `packages/common/settings.py` for the configured selection).

Separate deterministic checks from LLM-as-judge evaluations.

Do not invent evaluation metrics or results.

If the evaluation UI or framework is not implemented, demonstrate the existing backend capabilities and document the missing UI.

---

# PHASE 10: HUMAN REVIEW AND CONTINUOUS IMPROVEMENT

Inspect existing human feedback functionality.

If implemented, demonstrate:

- AI critique.
- Human critique.
- Human outcome.
- Failure categorization.
- Reviewer comments.
- AI versus human agreement.
- Golden Dataset candidate creation.
- Approval workflow.
- Regression evaluation.

If not implemented, create a clearly labelled future-state walkthrough explaining the intended workflow.

Do not present planned functionality as an existing feature.

---

# PHASE 11: PRESENTER SCRIPT

Every module must include two separate sections.

## A. What to show

Exact instructions:

- Which application to open.
- Which page to navigate to.
- Which button to click.
- Which command to execute.
- Which input to provide.
- Which output to inspect.

## B. What to say

Write natural technical narration in the **Language Style** rules above: simple words, detailed steps, one example, one use case.

The narration must explain:

- What the component does (in plain language).
- Why it exists (the use case).
- How it connects to other components.
- What business problem it solves.
- One concrete example with sample input and expected output.
- What evidence demonstrates that it works.

Avoid reading code line by line.

Explain architectural decisions only when they are relevant to the demonstration.

---

# PHASE 12: COMPLETE DEMO RUNBOOK

Create a master 25–30 minute demonstration.

Suggested sequence:

| Section | Duration |
|---|---:|
| Product introduction | 2 minutes |
| Knowledge engineering | 5 minutes |
| MCP server | 4 minutes |
| AI agent execution | 4 minutes |
| Langfuse observability | 3 minutes |
| Evaluation framework | 5 minutes |
| Human review and improvement | 4 minutes |
| Architecture and conclusion | 2 minutes |

Adjust durations according to the features actually implemented.

For infra-focused audiences, add an optional segment covering the AWS deployment story (`infra/terraform/`: ECS Fargate, ECR, RDS, Secrets Manager, UI module) — only if the environment can show it; otherwise present the architecture diagram and mark it as a roadmap item.

Also create:

- A 10-minute executive demonstration.
- A 15-minute technical demonstration.
- A 30-minute complete demonstration.

Each runbook must map every timed section to its module file(s) and scripts, so a presenter can run the runbook without reading all modules first.

---

# PHASE 13: ENVIRONMENT AND PRE-DEMO VALIDATION

Create a preflight script that checks:

- Required environment variables are present.
- Backend is reachable.
- Frontend is reachable where applicable.
- MCP server is available.
- Required dependencies are installed (uv workspace resolves; web UI `node_modules` exists).
- Knowledge artifacts exist (EAKG output, ApiIndex, pgvector tables, Graphify `graphify-out/`).
- Pipeline freshness status is resolvable (read-only).
- pgvector (Postgres) is reachable if `VECTOR_STORE__PROVIDER=pgvector`.
- Langfuse is reachable if configured.
- Test data is available (`data/golden.jsonl`, `data/loans.json`).
- Required API operations are discoverable.

Never print secret values.

Provide a summary of missing prerequisites and actionable remediation instructions.

Do not make destructive changes during preflight.

All preflight and demo commands must be PowerShell-compatible and run via `uv run python ...`.

---

# PHASE 14: QUALITY VALIDATION

After creating the scripts:

1. Review every generated script.
2. Verify imports against the actual repository.
3. Verify all API endpoints.
4. Verify MCP tool names and arguments.
5. Verify CLI commands.
6. Verify artifact paths.
7. Run safe static checks.
8. Execute non-destructive tests where possible.
9. Fix errors caused by generated scripts.
10. Document anything that cannot be tested.

Do not claim scripts are executable unless they have actually been validated.

---

# FINAL DELIVERABLES

The repository should contain:

1. Complete master demonstration script.
2. Individual module scripts.
3. Actual executable Python demo utilities.
4. HTTP request examples.
5. Environment preflight checks.
6. Presenter narration.
7. Screen navigation instructions.
8. Expected outputs and verification steps.
9. Troubleshooting guide.
10. Executive and technical demo runbooks.
11. `demo/results/implementation-inventory.md` — the Phase 1 capability inventory backing every demo claim.
12. Live-vs-simulated labeling: every module states explicitly which parts run live and which use fixtures/mocks.

## Final quality requirement

The result should allow another engineer to clone/open the repository, configure the environment, follow the README and confidently reproduce the demonstration.

The demonstration must be based on the actual source code.

**Do not modify the application's business logic, architecture or production configuration. Only create and validate the demo assets and scripts.**

Begin by inspecting the repository. Present a short implementation inventory before creating the demo files.