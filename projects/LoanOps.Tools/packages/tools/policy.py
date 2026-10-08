"""Read-only tool policy for the execution core (ModularToolsClient).

MCP server keeps its own AuthError/PolicyError and re-exports these checks.
"""

from __future__ import annotations

from typing import Any


class ToolPolicyError(Exception):
    """Scope or read/write rejection at the tools execution boundary."""


def body_present(body: Any) -> bool:
    return body not in (None, "", {}, [])


def assert_sse_read_only(
    *,
    method_arg: str | None,
    body: Any,
    resolved_method: str | None,
) -> None:
    """call_sse_api is GET-only. Fail closed if unresolved."""
    if body_present(body):
        raise ToolPolicyError("call_sse_api body is not allowed")
    if method_arg is not None and str(method_arg).strip().upper() != "GET":
        raise ToolPolicyError("call_sse_api method must be GET")
    if resolved_method is None or resolved_method.lower() != "get":
        raise ToolPolicyError("call_sse_api only allows a resolved GET operation")
