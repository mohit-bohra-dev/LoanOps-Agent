"""Auth and read-only checks for the MCP boundary. No HTTP client."""

from __future__ import annotations

import secrets
from typing import Any

_READ_ONLY_TOOLS = frozenset({"search_sse_apis", "list_sse_apis", "search_docs", "call_sse_api"})


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


def body_present(body: Any) -> bool:
    return body not in (None, "", {}, [])


def assert_sse_read_only(
    *,
    method_arg: str | None,
    body: Any,
    resolved_method: str | None,
) -> None:
    """call_sse_api on the MCP server is GET-only. Fail closed if unresolved."""
    if body_present(body):
        raise PolicyError("call_sse_api body is not allowed")
    if method_arg is not None and str(method_arg).strip().upper() != "GET":
        raise PolicyError("call_sse_api method must be GET")
    if resolved_method is None or resolved_method.lower() != "get":
        raise PolicyError("call_sse_api only allows a resolved GET operation")
