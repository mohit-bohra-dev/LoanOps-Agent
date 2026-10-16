"""Agent runner — orchestrates a single agent turn.

Flow:
1. Load the system prompt via PromptStoreProvider
2. Classify intent via the pure-function router
3. If ANSWER: run AgentRuntimeProvider (LangGraph/native) with tools + validator
4. Map ToolCallRecord → ToolCallItem; return AgentTurnOutput
"""

from __future__ import annotations

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
from packages.common.providers.factory import get_agent_runtime_provider
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
            "Invoke an SSE REST API by operation_id from search/list "
            "(e.g. getLoanSummary, getPaymentSchedules), or method+path + path_params. "
            "Required for live loan data."
        ),
        parameters={
            "type": "object",
            "properties": {
                "operation_id": {"type": "string"},
                "method": {"type": "string"},
                "path": {"type": "string"},
                "path_params": {"type": "object"},
                "query": {"type": "object"},
                "body": {},
            },
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


async def _execute_tools(
    tool_calls: list[ToolCallRequest],
    tools_client: ToolsClientProvider,
    pii_token_map: dict[str, str] | None = None,
) -> list[ToolCallItem]:
    """Execute tool calls and return recorded items (PII-aware)."""
    recorded: list[ToolCallItem] = []
    for tc in tool_calls:
        resolved_args: dict[str, Any] = (
            PiiTokenizer.detokenize_dict(tc.arguments, pii_token_map)
            if pii_token_map
            else tc.arguments
        )

        tool = ToolCall(tool_name=tc.name, parameters=resolved_args)
        result = await tools_client.call(tool)
        summary_cap = 8000 if tc.name == "search_docs" else 500
        recorded.append(
            ToolCallItem(
                name=tc.name,
                args=tc.arguments,
                result_summary=str(result.data)[:summary_cap]
                if result.success
                else result.error or "error",
            )
        )
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
    intent, reason, detail = classify_intent(prompt)

    if intent == IntentType.REFUSE:
        return AgentTurnOutput(
            answer="",
            citations=[],
            tool_calls=[],
            requires_human_approval=True,
            confidence=0.0,
            refusal=reason,
            escalation=None,
        )

    if intent == IntentType.ESCALATE:
        return AgentTurnOutput(
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
        )

    system_prompt = await load_system_prompt(prompt_store, _SYSTEM_PROMPT_NAME)

    _TEXT_ONLY_PREAMBLE = (
        "IMPORTANT: This is a TEXT-ONLY conversation. There are no images, "
        "files, or attachments. Do not reference or request images. "
        "You MUST respond with ONLY valid JSON matching the OUTPUT CONTRACT.\n\n"
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
        items = await _execute_tools(typed, tools_client, pii_token_map=pii_token_map)
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
            max_tool_rounds=3,
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
        return AgentTurnOutput(
            answer=parsed.answer,
            citations=parsed.citations,
            tool_calls=recorded_tools,
            requires_human_approval=True,
            confidence=parsed.confidence,
            refusal=parsed.refusal,
            escalation=parsed.escalation,
        )

    return AgentTurnOutput(
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
    )
