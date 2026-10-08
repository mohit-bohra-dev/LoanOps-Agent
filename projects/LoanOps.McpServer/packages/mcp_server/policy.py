"""Auth and read-only checks for the MCP boundary. No HTTP client."""

from __future__ import annotations

import secrets
from typing import Any

from packages.tools.policy import ToolPolicyError
from packages.tools.policy import assert_sse_read_only as _assert_sse_read_only
from packages.tools.policy import body_present

# Must include every read tool the MCP server exposes (SSE + docs + EAKG).
_READ_ONLY_TOOLS = frozenset(
    {
        "search_sse_apis",
        "list_sse_apis",
        "search_docs",
        "call_sse_api",
        "search_capabilities",
        "explain_capability",
        "find_providers",
        "impact_of_change",
    }
)


class AuthError(Exception):
    """Bearer missing, empty server token, or token mismatch."""


class PolicyError(Exception):
    """Scope or read/write rejection."""


def bearer_matches(authorization: str | None, expected: str) -> bool:
    """True only when both sides are non-empty and the bearer matches."""
    if not expected or not authorization:
        return False
    if not authorization.lower().startswith("bearer "):
        return False
    presented = authorization[7:]
    try:
        return secrets.compare_digest(presented, expected)
    except (TypeError, ValueError):
        return False


def assert_tool_allowed(name: str, allowed: frozenset[str]) -> None:
    if name not in allowed or name not in _READ_ONLY_TOOLS:
        raise PolicyError(f"Tool '{name}' not allowed for current scope")


def assert_sse_read_only(
    *,
    method_arg: str | None,
    body: Any,
    resolved_method: str | None,
) -> None:
    """call_sse_api on the MCP server is GET-only. Fail closed if unresolved."""
    try:
        _assert_sse_read_only(
            method_arg=method_arg,
            body=body,
            resolved_method=resolved_method,
        )
    except ToolPolicyError as exc:
        raise PolicyError(str(exc)) from exc


__all__ = [
    "AuthError",
    "PolicyError",
    "assert_sse_read_only",
    "assert_tool_allowed",
    "bearer_matches",
    "body_present",
]
