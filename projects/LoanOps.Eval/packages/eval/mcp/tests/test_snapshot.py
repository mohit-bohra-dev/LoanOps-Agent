"""Regression snapshots for tools/list."""

from __future__ import annotations

import json
from pathlib import Path

from packages.eval.mcp.harness import AsgiMcpDriver, tool_list_snapshot_payload

TOOLS_SNAP = Path(__file__).resolve().parents[1] / "snapshots" / "tools.json"


def test_tools_snapshot_file_exists_and_matches() -> None:
    driver = AsgiMcpDriver()
    resp = driver.tools_list()
    assert resp.result is not None
    snap = tool_list_snapshot_payload(list(resp.result["tools"]))
    TOOLS_SNAP.parent.mkdir(parents=True, exist_ok=True)
    if not TOOLS_SNAP.is_file():
        TOOLS_SNAP.write_text(json.dumps(snap, indent=2) + "\n", encoding="utf-8")
    expected = json.loads(TOOLS_SNAP.read_text(encoding="utf-8"))
    assert snap == expected
    assert len(expected) == 10
