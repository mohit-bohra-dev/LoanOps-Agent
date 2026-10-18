"""L1b schema / tools/list / readOnly / GET-only policy."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from packages.eval.mcp.harness import (
    EXPECTED_MCP_TOOLS,
    HAPPY_ARGS,
    AsgiMcpDriver,
    FakeClient,
    FakeMode,
    run_execute,
    tool_list_snapshot_payload,
)
from packages.mcp_server.policy import PolicyError

SNAPSHOT = Path(__file__).resolve().parents[1] / "snapshots" / "tools.json"


def test_tools_list_names_and_readonly() -> None:
    driver = AsgiMcpDriver()
    resp = driver.tools_list()
    assert resp.result is not None
    tools = resp.result["tools"]
    names = {t["name"] for t in tools}
    assert names == set(EXPECTED_MCP_TOOLS)
    for t in tools:
        ann = t.get("annotations") or {}
        assert ann.get("readOnlyHint") is True


def test_tools_list_snapshot() -> None:
    driver = AsgiMcpDriver()
    resp = driver.tools_list()
    assert resp.result is not None
    snap = tool_list_snapshot_payload(list(resp.result["tools"]))
    if not SNAPSHOT.is_file():
        SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
        SNAPSHOT.write_text(json.dumps(snap, indent=2) + "\n", encoding="utf-8")
    expected = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    assert snap == expected


@pytest.mark.asyncio
async def test_get_only_post_and_body_policy() -> None:
    client = FakeClient(mode=FakeMode.OK)
    with pytest.raises(PolicyError):
        await run_execute(
            name="call_sse_api",
            arguments={"method": "POST", "path": "/api/Loans/1"},
            client=client,
        )
    assert client.calls == []
    with pytest.raises(PolicyError):
        await run_execute(
            name="call_sse_api",
            arguments={"operation_id": "getLoanSummary", "body": {"amount": 1}},
            client=client,
        )
    assert client.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize("name", list(EXPECTED_MCP_TOOLS))
async def test_happy_path_each_tool(name: str) -> None:
    client = FakeClient(mode=FakeMode.OK)
    text = await run_execute(name=name, arguments=dict(HAPPY_ARGS[name]), client=client)
    assert text.startswith("ok:")
    assert len(client.calls) == 1
