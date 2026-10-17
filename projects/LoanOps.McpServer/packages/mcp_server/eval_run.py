"""MCP fixture eval — scores to TelemetryProvider only (no report file).

Usage::

    python -m packages.mcp_server.eval_run
"""

from __future__ import annotations

import asyncio
import sys
from typing import Any

from packages.common.providers import ToolCall, ToolResult
from packages.common.providers.factory import get_telemetry_provider
from packages.common.settings import McpConfig, Settings
from packages.mcp_server.eval_fixtures import MCP_EVAL_CASES, McpEvalCase
from packages.mcp_server.policy import AuthError, PolicyError
from packages.mcp_server.server import execute_tool


class _Op:
    def __init__(self, method: str = "get") -> None:
        self.method = method


class _FakeClient:
    """In-process stub — same shape as unit-test FakeClient."""

    def __init__(self) -> None:
        self.calls: list[ToolCall] = []

    async def find_sse_operation(
        self,
        *,
        operation_id: str | None = None,
        method: str | None = None,
        path: str | None = None,
    ) -> _Op | None:
        _ = method, path
        if operation_id == "missing":
            return None
        return _Op("get")

    async def call(self, tool: ToolCall) -> ToolResult:
        self.calls.append(tool)
        return ToolResult(tool_name=tool.tool_name, success=True, data={"text": "ok"})

    def capability_catalog(self) -> Any | None:
        return None

    def operation_resolver(self) -> Any | None:
        return None


def _settings() -> Settings:
    return Settings(mcp=McpConfig(auth_token="secret-token", role="system"))


async def _run_case(case: McpEvalCase, client: _FakeClient) -> str:
    """Return observed outcome: ok | denied | policy | error."""
    try:
        await execute_tool(
            name=case["tool"],
            arguments=dict(case["arguments"]),
            authorization=case["authorization"],
            user=None,
            tenant=None,
            settings=_settings(),
            client=client,
            audit=None,
        )
        return "ok"
    except AuthError:
        return "denied"
    except PolicyError:
        return "policy"
    except Exception:  # noqa: BLE001
        return "error"


async def run_mcp_eval() -> dict[str, float]:
    """Run fixtures; push eval.mcp.* metrics; return metric map."""
    client = _FakeClient()
    auth_ok = 0
    auth_n = 0
    policy_ok = 0
    policy_n = 0
    success_ok = 0
    success_n = 0

    for case in MCP_EVAL_CASES:
        observed = await _run_case(case, client)
        expect = case["expect"]
        passed = observed == expect
        if expect == "denied":
            auth_n += 1
            if passed:
                auth_ok += 1
        elif expect == "policy":
            policy_n += 1
            if passed:
                policy_ok += 1
        else:
            success_n += 1
            if passed:
                success_ok += 1

    metrics = {
        "mcp_auth_correctness": (auth_ok / auth_n) if auth_n else 1.0,
        "mcp_policy_correctness": (policy_ok / policy_n) if policy_n else 1.0,
        "mcp_success_rate": (success_ok / success_n) if success_n else 1.0,
    }

    telemetry = get_telemetry_provider()
    for name, value in metrics.items():
        await telemetry.record_metric(
            f"eval.mcp.{name}",
            value,
            unit="ratio",
            attributes={"cases": str(len(MCP_EVAL_CASES))},
        )
    if hasattr(telemetry, "flush"):
        await telemetry.flush()

    return metrics


def main() -> None:
    metrics = asyncio.run(run_mcp_eval())
    failed = [k for k, v in metrics.items() if v < 1.0]
    summary = " ".join(f"{k}={v:.2f}" for k, v in metrics.items())
    print(f"mcp_eval {summary}")
    if failed:
        print(f"mcp_eval FAILED: {', '.join(failed)}", file=sys.stderr)
        raise SystemExit(1)
    raise SystemExit(0)


if __name__ == "__main__":
    main()
