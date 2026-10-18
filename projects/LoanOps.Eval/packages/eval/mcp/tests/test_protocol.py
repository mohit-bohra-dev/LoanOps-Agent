"""L1a protocol suite."""

from __future__ import annotations

from packages.eval.mcp.harness import AsgiMcpDriver


def test_initialize_negotiates_protocol_version() -> None:
    driver = AsgiMcpDriver()
    resp = driver.initialize()
    assert resp.http_status == 200
    assert resp.result is not None
    assert resp.result.get("protocolVersion") == "2025-03-26"


def test_malformed_json_parse_error() -> None:
    driver = AsgiMcpDriver()
    resp = driver.rpc(b"{not json")
    assert resp.protocol_error is not None
    assert resp.protocol_error.get("code") == -32700


def test_unknown_method_jsonrpc_error() -> None:
    driver = AsgiMcpDriver()
    resp = driver.rpc({"jsonrpc": "2.0", "id": 1, "method": "nope"})
    assert resp.protocol_error is not None
    # mcp SDK maps unknown methods to -32602 (Invalid request parameters)
    assert resp.protocol_error.get("code") in (-32601, -32602)


def test_missing_required_param_fails() -> None:
    driver = AsgiMcpDriver()
    resp = driver.tools_call("search_docs", {})
    assert resp.is_jsonrpc_error or (
        resp.result is not None and bool(resp.result.get("isError"))
    )


def test_wrong_param_type_fails() -> None:
    driver = AsgiMcpDriver()
    resp = driver.tools_call("search_docs", {"query": "x", "top_k": "abc"})
    assert resp.is_jsonrpc_error or (
        resp.result is not None and bool(resp.result.get("isError"))
    )


def test_unknown_tool_fails() -> None:
    driver = AsgiMcpDriver()
    resp = driver.tools_call("not_a_real_tool", {"q": 1})
    assert resp.is_jsonrpc_error or (
        resp.result is not None and bool(resp.result.get("isError"))
    ) or resp.http_status >= 400
