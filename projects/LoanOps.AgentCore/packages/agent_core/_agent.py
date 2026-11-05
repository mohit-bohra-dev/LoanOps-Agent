"""Agent runner — orchestrates a single agent turn.

Flow:
1. Load the system prompt via PromptStoreProvider
2. Classify intent via the pure-function router
3. If ANSWER: run AgentRuntimeProvider (LangGraph/native) with tools + validator
4. Map ToolCallRecord → ToolCallItem; return AgentTurnOutput
"""

from __future__ import annotations

import contextlib
import time
import uuid
from collections.abc import Sequence
from typing import Any

from packages.agent_core._intent_router import IntentType, classify_intent
from packages.agent_core._output_parser import AgentParseError, parse_agent_output
from packages.agent_core._prompt_loader import load_system_prompt
from packages.common.providers import (
    ChatProvider,
    LLMMessage,
    PromptStoreProvider,
    ToolCall,
    ToolCallRequest,
    ToolDefinition,
    ToolsClientProvider,
)
from packages.common.providers.agent_runtime import (
    AgentTurnRequest,
    AgentValidatorResult,
    ToolCallRecord,
)
from packages.common.providers.factory import get_agent_runtime_provider, get_telemetry_provider
from packages.common.schemas import AgentTurnOutput, EscalationItem, ToolCallItem
from packages.safety.tokenizer import PiiTokenizer

_SYSTEM_PROMPT_NAME = "agent.system"
_MAX_RETRIES = 1

# Answers come from SSE OpenAPI catalog (+ docs). No tools_api / SQL loan fixtures.
_SSE_ANSWER_TOOLS = [
    ToolDefinition(
        name="search_sse_apis",
        description=(
            "Search SSE OpenAPI catalogs by keywords. Use for loan summary, payment "
            "schedules, escrow, borrower, delinquency — prefer this first, then call_sse_api. "
            "Do not answer loan facts without calling an API."
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["query"],
        },
    ),
    ToolDefinition(
        name="list_sse_apis",
        description=(
            "List discovered SSE REST operations from all swagger sources "
            "(10+ apps when configured). Optional source_label filters one app."
        ),
        parameters={
            "type": "object",
            "properties": {
                "source_label": {"type": "string"},
                "limit": {"type": "integer"},
                "refresh": {"type": "boolean"},
            },
        },
    ),
    ToolDefinition(
        name="call_sse_api",
        description=(
            "Invoke an SSE REST API by operation_id from search_sse_apis/list_sse_apis "
            "(e.g. GetEscrowByLoanNumber, getLoanSummary). Pass loan identifiers in "
            "query (preferred for query-param ops) or path_params; misplaced keys are "
            "auto-routed. Required for live loan data. Do not invent other tool names."
        ),
        parameters={
            "type": "object",
            "properties": {
                "operation_id": {"type": "string"},
                "method": {"type": "string"},
                "path": {"type": "string"},
                "path_params": {"type": "object"},
                "query": {"type": "object"},
                "query_params": {"type": "object"},
                "body": {},
            },
        },
    ),
    ToolDefinition(
        name="describe_application",
        description=(
            "Describe one application's interface from the EAKG graph: outbound "
            "ServiceProxy classes, SDK packages, event topics, and URL keys. "
            "Use for 'does <app> use outbound proxies' or 'list proxies'. "
            "application_id is the registry id, for example loanservices. "
            "Not search_docs."
        ),
        parameters={
            "type": "object",
            "properties": {
                "application_id": {"type": "string"},
            },
            "required": ["application_id"],
        },
    ),
    ToolDefinition(
        name="search_capabilities",
        description=(
            "Search the enterprise capability knowledge graph for invoke discovery. "
            "GET hits are preferred. Use for capability discovery; then call_sse_api "
            "when mcp_invoke is true. Not for live loan numbers."
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["query"],
        },
    ),
    ToolDefinition(
        name="explain_capability",
        description=(
            "Explain one capability: application, API operation, code unit, "
            "permission/authzSource, and evidence. Pass capability_id from "
            "search_capabilities or a known operation name."
        ),
        parameters={
            "type": "object",
            "properties": {
                "capability_id": {"type": "string"},
            },
            "required": ["capability_id"],
        },
    ),
    ToolDefinition(
        name="find_providers",
        description=(
            "Which application/API provides a capability or operation name "
            "(e.g. GetLoanSummary). Returns all methods; mcp_invoke true means "
            "call_sse_api can run it. Prefer this over search_docs for ownership."
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
            },
            "required": ["query"],
        },
    ),
    ToolDefinition(
        name="impact_of_change",
        description=(
            "Which applications depend on an API or application via "
            "callsOperation/consumesSdk (evidence included). Pass an app id "
            "or operation name as target."
        ),
        parameters={
            "type": "object",
            "properties": {
                "target": {"type": "string"},
            },
            "required": ["target"],
        },
    ),
    ToolDefinition(
        name="search_code",
        description=(
            "Search one app's engineering AST graph for class/method/file hits "
            "(e.g. Facades). Requires application_id (loanservices) and a query. "
            "Not search_docs; not the LoanOps-Agent graphify-out/."
        ),
        parameters={
            "type": "object",
            "properties": {
                "application_id": {"type": "string"},
                "query": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["application_id", "query"],
        },
    ),
    ToolDefinition(
        name="search_docs",
        description="Search indexed documentation (SOPs / wiki narratives). Not for live loan numbers.",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "top_k": {"type": "integer"},
            },
            "required": ["query"],
        },
    ),
]


def _tools_for_client(tools_client: ToolsClientProvider) -> list[ToolDefinition]:
    """Expose only tools allowed by the modular client's scope (SSE-first)."""
    allowed = getattr(tools_client, "allowed_tools", None)
    if not allowed:
        return list(_SSE_ANSWER_TOOLS)
    return [t for t in _SSE_ANSWER_TOOLS if t.name in allowed]


def _tool_result_text(data: Any) -> str:
    """Prefer clean ``text`` payloads over Python dict repr for the LLM."""
    if isinstance(data, dict):
        text = data.get("text")
        if isinstance(text, str):
            return text
    if isinstance(data, str):
        return data
    return str(data)


_LEGACY_TOOL_NAMES: tuple[tuple[str, str], ...] = (
    ("lookup_loan", "search_sse_apis"),
    ("get_escrow_breakdown", "call_sse_api"),
    ("get_payment_schedule", "call_sse_api"),
    ("search_policy", "search_docs"),
)


def _normalize_legacy_tool_names(prompt: str) -> str:
    """Rewrite few-shot legacy tool names to live SSE/docs tools."""
    out = prompt
    for old, new in _LEGACY_TOOL_NAMES:
        out = out.replace(old, new)
    return out


async def _execute_tools(
    tool_calls: list[ToolCallRequest],
    tools_client: ToolsClientProvider,
    pii_token_map: dict[str, str] | None = None,
    *,
    trace_id: str | None = None,
) -> list[ToolCallItem]:
    """Execute tool calls and return recorded items (PII-aware)."""
    tel = None
    with contextlib.suppress(Exception):
        tel = get_telemetry_provider()
    recorded: list[ToolCallItem] = []
    for tc in tool_calls:
        resolved_args: dict[str, Any] = (
            PiiTokenizer.detokenize_dict(tc.arguments, pii_token_map)
            if pii_token_map
            else tc.arguments
        )

        call_name = tc.name
        call_args = tc.arguments
        call_params = resolved_args

        async def _one_call() -> ToolCallItem:
            tool = ToolCall(tool_name=call_name, parameters=call_params)
            result = await tools_client.call(tool)
            # search_docs / SSE search+call need enough room for OpenAPI hits + live JSON
            if call_name == "search_docs":
                summary_cap = 8000
            elif call_name in {
                "search_sse_apis",
                "list_sse_apis",
                "call_sse_api",
                "describe_application",
                "search_capabilities",
                "explain_capability",
                "find_providers",
                "impact_of_change",
                "search_code",
            }:
                summary_cap = 4000
            else:
                summary_cap = 500
            return ToolCallItem(
                name=call_name,
                args=call_args,
                result_summary=_tool_result_text(result.data)[:summary_cap]
                if result.success
                else result.error or "error",
            )

        if tel is None:
            recorded.append(await _one_call())
            continue
        try:
            async with tel.span(
                "mcp.tool.call",
                attributes={
                    "tool": call_name,
                    "agent.trace_id": trace_id or "",
                },
            ) as span:
                item = await _one_call()
                # Langfuse log tab reads span input/output, not metadata.
                span.input = call_args
                span.output = item.result_summary
                recorded.append(item)
        except Exception:  # noqa: BLE001
            recorded.append(await _one_call())
    return recorded


def _records_to_items(records: list[ToolCallRecord]) -> list[ToolCallItem]:
    return [
        ToolCallItem(
            name=r.name,
            args=dict(r.arguments),
            result_summary=r.result_summary,
        )
        for r in records
    ]


def _with_trace(output: AgentTurnOutput, trace_id: str) -> AgentTurnOutput:
    return output.model_copy(update={"trace_id": trace_id})


async def run_agent_turn(
    *,
    prompt: str,
    chat_provider: ChatProvider,
    tools_client: ToolsClientProvider,
    prompt_store: PromptStoreProvider,
    history: list[LLMMessage] | None = None,
    pii_token_map: dict[str, str] | None = None,
) -> AgentTurnOutput:
    """Run a single agent turn and return structured output."""
    trace_id = str(uuid.uuid4())
    t0 = time.perf_counter()
    tel = None
    with contextlib.suppress(Exception):
        tel = get_telemetry_provider()

    async def _run_body() -> AgentTurnOutput:
        intent, reason, detail = classify_intent(prompt)

        if intent == IntentType.REFUSE:
            return _with_trace(
                AgentTurnOutput(
                    answer="",
                    citations=[],
                    tool_calls=[],
                    requires_human_approval=True,
                    confidence=0.0,
                    refusal=reason,
                    escalation=None,
                ),
                trace_id,
            )

        if intent == IntentType.ESCALATE:
            return _with_trace(
                AgentTurnOutput(
                    answer="",
                    citations=[],
                    tool_calls=[],
                    requires_human_approval=True,
                    confidence=0.0,
                    refusal="Escalating per policy; do not draft a reply.",
                    escalation=EscalationItem(
                        category=reason,  # type: ignore[arg-type]
                        reason=detail or "Escalation triggered by router",
                    ),
                ),
                trace_id,
            )

        system_prompt = _normalize_legacy_tool_names(
            await load_system_prompt(prompt_store, _SYSTEM_PROMPT_NAME)
        )

        _TEXT_ONLY_PREAMBLE = (
            "IMPORTANT: This is a TEXT-ONLY conversation. There are no images, "
            "files, or attachments. Do not reference or request images. "
            "You MUST respond with ONLY valid JSON matching the OUTPUT CONTRACT.\n"
            "Available tools ONLY: search_sse_apis, list_sse_apis, call_sse_api, "
            "describe_application, search_capabilities, explain_capability, "
            "find_providers, impact_of_change, search_code, search_docs. "
            "Do not invent tool names (no lookup_loan, get_escrow_breakdown, "
            "get_escrow_data, search_policy).\n"
            "For outbound proxies, packages, or topics of an application: call "
            "describe_application with application_id (loanservices). Do not use "
            "search_docs for that.\n"
            "Which app owns X / explain X: find_providers or explain_capability. "
            "Who depends on X: impact_of_change. Facades / classes in an app: "
            "search_code with application_id. Capability discovery: "
            "search_capabilities. Not search_docs for graph questions.\n"
            "Final JSON fields: answer (string prose, not an object), citations "
            "(list), confidence (0.0-1.0 number), refusal (string or null), "
            "requires_human_approval (always true).\n"
            "For live loan facts: search_sse_apis then call_sse_api with the "
            "operation_id from search (query params for GetEscrowByLoanNumber "
            "go in query/query_params or path_params — both are accepted).\n\n"
        )
        full_system_prompt = _TEXT_ONLY_PREAMBLE + system_prompt

        messages = [
            LLMMessage(role="system", content=full_system_prompt),
            *(history or []),
            LLMMessage(role="user", content=prompt),
        ]

        tools_def = _tools_for_client(tools_client)

        async def _tool_executor(tcs: Sequence[Any]) -> list[ToolCallRecord]:
            typed = [
                tc
                if isinstance(tc, ToolCallRequest)
                else ToolCallRequest(name=tc.name, arguments=dict(tc.arguments))
                for tc in tcs
            ]
            items = await _execute_tools(
                typed,
                tools_client,
                pii_token_map=pii_token_map,
                trace_id=trace_id,
            )
            return [
                ToolCallRecord(
                    name=i.name,
                    arguments=dict(i.args),
                    result_summary=i.result_summary,
                    success=True,
                )
                for i in items
            ]

        async def _validator(raw: str, records: list[ToolCallRecord]) -> AgentValidatorResult:
            items = _records_to_items(records)
            try:
                parsed = parse_agent_output(raw, items)
                return AgentValidatorResult(is_valid=True, parsed_output=parsed, retry_feedback=None)
            except AgentParseError as exc:
                return AgentValidatorResult(
                    is_valid=False, parsed_output=None, retry_feedback=str(exc)
                )

        runtime = get_agent_runtime_provider()
        result = await runtime.run(
            AgentTurnRequest(
                messages=messages,
                tools=tools_def,
                max_tool_rounds=4,
                max_validation_retries=_MAX_RETRIES,
                temperature=0.0,
                max_tokens=2048,
                json_mode=True,
                parallel_tool_calls=True,
            ),
            llm=chat_provider,
            tools=tools_client,
            validator=_validator,
            tool_executor=_tool_executor,
        )

        recorded_tools = _records_to_items(list(result.tool_calls))

        if result.parsed_output is not None and hasattr(result.parsed_output, "answer"):
            parsed = result.parsed_output
            return _with_trace(
                AgentTurnOutput(
                    answer=parsed.answer,
                    citations=parsed.citations,
                    tool_calls=recorded_tools,
                    requires_human_approval=True,
                    confidence=parsed.confidence,
                    refusal=parsed.refusal,
                    escalation=parsed.escalation,
                ),
                trace_id,
            )

        return _with_trace(
            AgentTurnOutput(
                answer="",
                citations=[],
                tool_calls=recorded_tools,
                requires_human_approval=True,
                confidence=0.0,
                refusal=(
                    f"I could not produce a valid response after {_MAX_RETRIES + 1} attempts. "
                    f"{result.raw_text[:200]}"
                ),
                escalation=None,
            ),
            trace_id,
        )

    if tel is None:
        return await _run_body()
    try:
        cm = tel.span(
            "agent.turn",
            attributes={
                "agent.trace_id": trace_id,
                "user_query_len": len(prompt),
            },
        )
        ctx = await cm.__aenter__()
    except Exception:  # noqa: BLE001
        return await _run_body()
    try:
        tid = getattr(ctx, "trace_id", None) or trace_id
        out = await _run_body()
        if out.trace_id != tid:
            out = _with_trace(out, str(tid))
        ctx.input = prompt[:2000]
        ctx.output = (out.answer or out.refusal or "")[:2000]
        latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        with contextlib.suppress(Exception):
            await tel.record_metric(
                "agent.turn.latency_ms",
                latency_ms,
                unit="ms",
                attributes={"agent.trace_id": out.trace_id or str(tid)},
            )
        await cm.__aexit__(None, None, None)
        return out
    except BaseException as exc:
        await cm.__aexit__(type(exc), exc, exc.__traceback__)
        raise
