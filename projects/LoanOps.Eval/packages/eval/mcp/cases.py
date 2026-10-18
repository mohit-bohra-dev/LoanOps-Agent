"""Typed Layer 1 cases with suite tags and eval_methods (no Auth cases)."""

from __future__ import annotations

from typing import Any, Literal

from packages.eval.mcp.harness import EXPECTED_MCP_TOOLS, HAPPY_ARGS, FakeMode
from pydantic import BaseModel, Field

Suite = Literal["protocol", "contracts", "functional", "errors", "perf"]


class McpL1Case(BaseModel):
    id: str
    suite: Suite
    eval_methods: list[str] = Field(default_factory=list)
    tool: str | None = None
    arguments: dict[str, Any] = Field(default_factory=dict)
    fake_mode: FakeMode | None = None
    expect: str = "ok"  # ok | empty | is_error | protocol_error | policy
    notes: str = ""


def protocol_cases() -> list[McpL1Case]:
    return [
        McpL1Case(
            id="proto_initialize",
            suite="protocol",
            eval_methods=["deterministic_assert"],
            expect="ok",
            notes="initialize + protocolVersion",
        ),
        McpL1Case(
            id="proto_parse_error",
            suite="protocol",
            eval_methods=["deterministic_assert"],
            expect="protocol_error",
            notes="malformed JSON → -32700",
        ),
        McpL1Case(
            id="proto_unknown_method",
            suite="protocol",
            eval_methods=["deterministic_assert"],
            expect="protocol_error",
            notes="unknown method (SDK returns -32602 Invalid request parameters)",
        ),
        McpL1Case(
            id="proto_invalid_params_missing_query",
            suite="protocol",
            eval_methods=["deterministic_assert"],
            tool="search_docs",
            arguments={},
            expect="protocol_error",
            notes="missing required query",
        ),
        McpL1Case(
            id="proto_invalid_params_bad_type",
            suite="protocol",
            eval_methods=["deterministic_assert"],
            tool="search_docs",
            arguments={"query": "escrow", "top_k": "abc"},
            expect="protocol_error",
            notes="wrong type for top_k",
        ),
        McpL1Case(
            id="proto_unknown_tool",
            suite="protocol",
            eval_methods=["deterministic_assert"],
            tool="not_a_real_tool",
            arguments={"q": 1},
            expect="is_error",
            notes="unknown tool on tools/call",
        ),
    ]


def contract_cases() -> list[McpL1Case]:
    cases = [
        McpL1Case(
            id="contracts_tools_list_snapshot",
            suite="contracts",
            eval_methods=["snapshot"],
            expect="ok",
        ),
        McpL1Case(
            id="contracts_readonly_invariant",
            suite="contracts",
            eval_methods=["deterministic_assert"],
            expect="ok",
        ),
        McpL1Case(
            id="contracts_get_only_post",
            suite="contracts",
            eval_methods=["deterministic_assert"],
            tool="call_sse_api",
            arguments={"method": "POST", "path": "/api/Loans/1"},
            fake_mode=FakeMode.OK,
            expect="policy",
        ),
        McpL1Case(
            id="contracts_get_only_body",
            suite="contracts",
            eval_methods=["deterministic_assert"],
            tool="call_sse_api",
            arguments={"operation_id": "getLoanSummary", "body": {"amount": 1}},
            fake_mode=FakeMode.OK,
            expect="policy",
        ),
    ]
    for name in EXPECTED_MCP_TOOLS:
        cases.append(
            McpL1Case(
                id=f"contracts_happy_{name}",
                suite="contracts",
                eval_methods=["deterministic_assert"],
                tool=name,
                arguments=dict(HAPPY_ARGS[name]),
                fake_mode=FakeMode.OK,
                expect="ok",
            )
        )
    return cases


def functional_cases() -> list[McpL1Case]:
    cases: list[McpL1Case] = []
    for name in EXPECTED_MCP_TOOLS:
        cases.append(
            McpL1Case(
                id=f"functional_ok_{name}",
                suite="functional",
                eval_methods=["deterministic_assert", "snapshot"],
                tool=name,
                arguments=dict(HAPPY_ARGS[name]),
                fake_mode=FakeMode.OK,
                expect="ok",
            )
        )
        cases.append(
            McpL1Case(
                id=f"functional_empty_{name}",
                suite="functional",
                eval_methods=["deterministic_assert", "snapshot"],
                tool=name,
                arguments=dict(HAPPY_ARGS[name]),
                fake_mode=FakeMode.EMPTY,
                expect="empty",
            )
        )
    cases.extend(
        [
            McpL1Case(
                id="functional_fixture_search_sse",
                suite="functional",
                eval_methods=["deterministic_assert"],
                tool="search_sse_apis",
                arguments={"query": "loan", "limit": 5},
                expect="ok",
                notes="FixtureCatalogClient",
            ),
            McpL1Case(
                id="functional_fixture_search_empty",
                suite="functional",
                eval_methods=["deterministic_assert", "snapshot"],
                tool="search_sse_apis",
                arguments={"query": "__no_match__", "limit": 5},
                expect="empty",
                notes="FixtureCatalogClient empty",
            ),
            McpL1Case(
                id="functional_fixture_list",
                suite="functional",
                eval_methods=["deterministic_assert", "snapshot"],
                tool="list_sse_apis",
                arguments={"limit": 10},
                expect="ok",
            ),
            McpL1Case(
                id="functional_fixture_call_ok",
                suite="functional",
                eval_methods=["deterministic_assert", "snapshot"],
                tool="call_sse_api",
                arguments={"operation_id": "getLoanSummary", "path_params": {"loan_id": "100245"}},
                expect="ok",
            ),
            McpL1Case(
                id="functional_fixture_call_unknown",
                suite="functional",
                eval_methods=["deterministic_assert"],
                tool="call_sse_api",
                arguments={"operation_id": "unknown_op"},
                expect="is_error",
            ),
            McpL1Case(
                id="functional_limit_one",
                suite="functional",
                eval_methods=["deterministic_assert"],
                tool="search_sse_apis",
                arguments={"query": "loan", "limit": 1},
                fake_mode=FakeMode.OK,
                expect="ok",
            ),
        ]
    )
    return cases


def error_cases() -> list[McpL1Case]:
    return [
        McpL1Case(
            id="errors_upstream_fail",
            suite="errors",
            eval_methods=["deterministic_assert"],
            tool="search_docs",
            arguments={"query": "escrow"},
            fake_mode=FakeMode.FAIL,
            expect="is_error",
        ),
        McpL1Case(
            id="errors_upstream_raise",
            suite="errors",
            eval_methods=["deterministic_assert"],
            tool="search_docs",
            arguments={"query": "escrow"},
            fake_mode=FakeMode.RAISE,
            expect="is_error",
        ),
        McpL1Case(
            id="errors_timeout",
            suite="errors",
            eval_methods=["deterministic_assert"],
            tool="search_docs",
            arguments={"query": "escrow"},
            fake_mode=FakeMode.TIMEOUT,
            expect="is_error",
        ),
        McpL1Case(
            id="errors_rate_limit",
            suite="errors",
            eval_methods=["deterministic_assert"],
            tool="search_docs",
            arguments={"query": "escrow"},
            fake_mode=FakeMode.RATE_LIMIT,
            expect="is_error",
        ),
    ]


def perf_cases() -> list[McpL1Case]:
    return [
        McpL1Case(
            id="perf_concurrent_isolation",
            suite="perf",
            eval_methods=["deterministic_assert"],
            tool="search_docs",
            arguments={"query": "escrow"},
            fake_mode=FakeMode.OK,
            expect="ok",
        ),
        McpL1Case(
            id="perf_latency_percentiles",
            suite="perf",
            eval_methods=["deterministic_assert"],
            tool="search_docs",
            arguments={"query": "escrow"},
            fake_mode=FakeMode.OK,
            expect="ok",
        ),
        McpL1Case(
            id="perf_payload_budgets",
            suite="perf",
            eval_methods=["deterministic_assert"],
            expect="ok",
        ),
    ]


def all_cases() -> list[McpL1Case]:
    return [
        *protocol_cases(),
        *contract_cases(),
        *functional_cases(),
        *error_cases(),
        *perf_cases(),
    ]
