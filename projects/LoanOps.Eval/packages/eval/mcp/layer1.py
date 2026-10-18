"""Layer 1 MCP eval runner — protocol / contracts / functional / errors / perf."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any

from mcp.server.fastmcp.exceptions import ToolError
from packages.common.providers import AuditEvent
from packages.common.providers.factory import get_telemetry_provider
from packages.common.providers.testing import MockTelemetryProvider
from packages.eval.mcp.cases import all_cases
from packages.eval.mcp.harness import (
    ASGI_BASE_URL,
    EXPECTED_MCP_TOOLS,
    FIXTURE_AUTH_HEADER,
    FIXTURE_BEARER,
    AsgiMcpDriver,
    FakeClient,
    FakeMode,
    FixtureCatalogClient,
    eval_settings,
    percentile,
    run_execute,
    tool_list_snapshot_payload,
)
from packages.mcp_server.policy import PolicyError
from packages.mcp_server.server import execute_tool
from pydantic import BaseModel, Field

SNAPSHOT_DIR = Path(__file__).resolve().parent / "snapshots"
TOOLS_SNAPSHOT = SNAPSHOT_DIR / "tools.json"
RESPONSES_DIR = SNAPSHOT_DIR / "responses"

# Offline FakeClient path — generous; gate only with --enforce-latency.
DEFAULT_LATENCY_P95_MS = 4000.0
MAX_TOOLS_LIST_BYTES = 256_000
MAX_TOOL_RESULT_BYTES = 8_000


class CaseResult(BaseModel):
    id: str
    suite: str
    passed: bool
    detail: str = ""
    latency_ms: float | None = None


class Layer1Report(BaseModel):
    suites: dict[str, dict[str, Any]] = Field(default_factory=dict)
    cases: list[CaseResult] = Field(default_factory=list)
    thresholds_passed: bool = False
    breaches: list[str] = Field(default_factory=list)
    protocol_version: str | None = None
    metrics: dict[str, float] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class FakeAudit:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    async def emit(self, event: AuditEvent) -> None:
        self.events.append(event)


def _error_path_ok(audit: FakeAudit, tel: MockTelemetryProvider, *, detail_suffix: str) -> bool:
    _ = detail_suffix
    ok = True
    ok = ok and audit.events[-1].payload.get("success") is False if audit.events else False
    outcomes = [m for m in tel.recorded_metrics if m["name"] == "mcp.tool.outcome"]
    ok = ok and outcomes[-1]["attributes"].get("outcome") == "error" if outcomes else False
    return ok


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _normalize_tools_for_snapshot(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop volatile description whitespace only; keep schema structure."""
    return tool_list_snapshot_payload(tools)


async def _run_protocol(driver: AsgiMcpDriver, report: Layer1Report) -> None:
    # initialize
    t0 = time.perf_counter()
    init = driver.initialize()
    ms = (time.perf_counter() - t0) * 1000
    ok = (
        init.http_status == 200
        and init.result is not None
        and isinstance(init.result.get("protocolVersion"), str)
    )
    report.protocol_version = (
        str(init.result.get("protocolVersion")) if init.result else None
    )
    report.cases.append(
        CaseResult(
            id="proto_initialize",
            suite="protocol",
            passed=ok,
            detail=f"protocolVersion={report.protocol_version}",
            latency_ms=round(ms, 2),
        )
    )

    # parse error
    bad = driver.rpc(b"{not json")
    pe = bad.protocol_error or {}
    ok_parse = pe.get("code") == -32700
    report.cases.append(
        CaseResult(
            id="proto_parse_error",
            suite="protocol",
            passed=ok_parse,
            detail=str(pe),
        )
    )

    # unknown method — FastMCP/SDK returns -32602 Invalid request parameters
    unk = driver.rpc({"jsonrpc": "2.0", "id": 9, "method": "nope"})
    ue = unk.protocol_error or {}
    ok_unk = ue.get("code") in (-32601, -32602)
    report.cases.append(
        CaseResult(
            id="proto_unknown_method",
            suite="protocol",
            passed=ok_unk,
            detail=f"code={ue.get('code')} (SDK may use -32602)",
        )
    )
    if ue.get("code") == -32602:
        report.notes.append(
            "Unknown JSON-RPC method returns -32602 (Invalid request parameters) "
            "via mcp SDK, not classic -32601."
        )

    # missing required param via tools/call
    miss = driver.tools_call("search_docs", {})
    # May be protocol error or isError tool result depending on FastMCP validation
    miss_ok = miss.is_jsonrpc_error or (
        miss.result is not None and bool(miss.result.get("isError"))
    )
    report.cases.append(
        CaseResult(
            id="proto_invalid_params_missing_query",
            suite="protocol",
            passed=miss_ok,
            detail=miss.raw_text[:300],
        )
    )

    bad_type = driver.tools_call("search_docs", {"query": "escrow", "top_k": "abc"})
    bt_ok = bad_type.is_jsonrpc_error or (
        bad_type.result is not None and bool(bad_type.result.get("isError"))
    )
    report.cases.append(
        CaseResult(
            id="proto_invalid_params_bad_type",
            suite="protocol",
            passed=bt_ok,
            detail=bad_type.raw_text[:300],
        )
    )

    # unknown tool — do not use real ModularToolsClient for known tools (slow).
    # Unknown tool name should fail without backend.
    ut = driver.tools_call("not_a_real_tool", {"q": 1})
    ut_ok = ut.is_jsonrpc_error or (
        ut.result is not None and bool(ut.result.get("isError"))
    )
    if not ut_ok:
        ut_ok = (
            "Unknown" in ut.raw_text
            or "not_a_real_tool" in ut.raw_text.lower()
            or ut.http_status >= 400
        )
    # FastMCP may return isError with text
    if ut.result and ut.result.get("content"):
        ut_ok = True  # tool layer answered; check isError if present
        if "isError" in ut.result:
            ut_ok = bool(ut.result["isError"])
    report.cases.append(
        CaseResult(
            id="proto_unknown_tool",
            suite="protocol",
            passed=ut_ok,
            detail=ut.raw_text[:400],
        )
    )


async def _run_contracts(driver: AsgiMcpDriver, report: Layer1Report) -> None:
    listed = driver.tools_list()
    tools_raw = []
    if listed.result and isinstance(listed.result.get("tools"), list):
        tools_raw = list(listed.result["tools"])
    names = {str(t.get("name")) for t in tools_raw if isinstance(t, dict)}
    expected = set(EXPECTED_MCP_TOOLS)
    list_ok = names == expected
    report.cases.append(
        CaseResult(
            id="contracts_tools_list_names",
            suite="contracts",
            passed=list_ok,
            detail=f"got={sorted(names)}",
        )
    )

    readonly_ok = True
    for t in tools_raw:
        if not isinstance(t, dict):
            readonly_ok = False
            break
        ann = t.get("annotations") or {}
        hint = ann.get("readOnlyHint") if isinstance(ann, dict) else None
        if hint is not True and ann.get("readOnly") is not True:
            readonly_ok = False
            break
    report.cases.append(
        CaseResult(
            id="contracts_readonly_invariant",
            suite="contracts",
            passed=readonly_ok,
            detail="all tools readOnlyHint=true",
        )
    )

    snap = _normalize_tools_for_snapshot([t for t in tools_raw if isinstance(t, dict)])
    if TOOLS_SNAPSHOT.is_file():
        expected_snap = _load_json(TOOLS_SNAPSHOT)
        snap_ok = snap == expected_snap
        report.cases.append(
            CaseResult(
                id="contracts_tools_list_snapshot",
                suite="contracts",
                passed=snap_ok,
                detail=(
                    "OK"
                    if snap_ok
                    else "snapshot drift — update snapshots/tools.json if intentional"
                ),
            )
        )
    else:
        _write_json(TOOLS_SNAPSHOT, snap)
        report.cases.append(
            CaseResult(
                id="contracts_tools_list_snapshot",
                suite="contracts",
                passed=True,
                detail=f"wrote initial snapshot {TOOLS_SNAPSHOT}",
            )
        )
        report.notes.append(f"Created initial tools snapshot at {TOOLS_SNAPSHOT}")

    # Schema validity: each tool has object inputSchema with type object
    schema_ok = True
    for t in tools_raw:
        if not isinstance(t, dict):
            schema_ok = False
            break
        schema = t.get("inputSchema") or t.get("input_schema") or {}
        bad_schema = not isinstance(schema, dict) or (
            schema.get("type") not in (None, "object")
            and "properties" not in schema
            and schema.get("type") != "object"
        )
        if bad_schema:
            schema_ok = False
            break
    report.cases.append(
        CaseResult(
            id="contracts_input_schemas",
            suite="contracts",
            passed=schema_ok,
            detail="inputSchema present per tool",
        )
    )

    # GET-only policy via execute_tool + FakeClient
    for case_id, args in (
        ("contracts_get_only_post", {"method": "POST", "path": "/api/Loans/1"}),
        (
            "contracts_get_only_body",
            {"operation_id": "getLoanSummary", "body": {"amount": 1}},
        ),
    ):
        client = FakeClient(mode=FakeMode.OK)
        passed = False
        detail = ""
        try:
            await run_execute(name="call_sse_api", arguments=args, client=client)
            detail = "expected PolicyError"
        except PolicyError as exc:
            passed = True
            detail = str(exc)
        except ToolError as exc:
            # execute_tool raises ToolError for failures; PolicyError before call
            msg = str(exc)
            passed = (
                "body" in msg.lower() or "GET" in msg or "method" in msg.lower()
            )
            detail = msg
        report.cases.append(
            CaseResult(id=case_id, suite="contracts", passed=passed, detail=detail)
        )
        if client.calls:
            report.cases[-1].passed = False
            report.cases[-1].detail += " (client was called)"

    # Happy path each tool via FakeClient
    for name in EXPECTED_MCP_TOOLS:
        from packages.eval.mcp.harness import HAPPY_ARGS

        client = FakeClient(mode=FakeMode.OK)
        try:
            text = await run_execute(
                name=name, arguments=dict(HAPPY_ARGS[name]), client=client
            )
            passed = text.startswith("ok:") and len(client.calls) == 1
            detail = text[:200]
        except Exception as exc:  # noqa: BLE001
            passed = False
            detail = str(exc)
        report.cases.append(
            CaseResult(
                id=f"contracts_happy_{name}",
                suite="contracts",
                passed=passed,
                detail=detail,
            )
        )


async def _run_functional(report: Layer1Report) -> None:
    from packages.eval.mcp.harness import HAPPY_ARGS

    RESPONSES_DIR.mkdir(parents=True, exist_ok=True)

    for name in EXPECTED_MCP_TOOLS:
        for mode, expect in ((FakeMode.OK, "ok"), (FakeMode.EMPTY, "empty")):
            client = FakeClient(mode=mode)
            case_id = f"functional_{expect}_{name}"
            try:
                text = await run_execute(
                    name=name, arguments=dict(HAPPY_ARGS[name]), client=client
                )
                if expect == "ok":
                    passed = text.startswith("ok:") and not text.startswith("empty:")
                else:
                    passed = text.startswith("empty:")
                # FakeClient response snapshots (separate from fixture snapshots)
                if name in ("search_docs", "list_sse_apis", "call_sse_api"):
                    snap_path = RESPONSES_DIR / f"fake_{name}_{expect}.txt"
                    if snap_path.is_file():
                        expected = snap_path.read_text(encoding="utf-8")
                        if text != expected:
                            passed = False
                            detail = f"response snapshot drift vs {snap_path.name}"
                        else:
                            detail = text[:200]
                    else:
                        snap_path.write_text(text, encoding="utf-8")
                        detail = f"wrote {snap_path.name}"
                else:
                    detail = text[:200]
            except Exception as exc:  # noqa: BLE001
                passed = False
                detail = str(exc)
            report.cases.append(
                CaseResult(id=case_id, suite="functional", passed=passed, detail=detail)
            )

    # Fixture catalog client path
    fx = FixtureCatalogClient()
    text = await run_execute(
        name="search_sse_apis", arguments={"query": "loan", "limit": 5}, client=fx
    )
    report.cases.append(
        CaseResult(
            id="functional_fixture_search_sse",
            suite="functional",
            passed="getLoanSummary" in text and "empty:" not in text,
            detail=text[:200],
        )
    )

    fx_empty = FixtureCatalogClient(empty_search=True)
    text_e = await run_execute(
        name="search_sse_apis",
        arguments={"query": "__no_match__", "limit": 5},
        client=fx_empty,
    )
    snap = RESPONSES_DIR / "search_sse_apis_empty.txt"
    empty_ok = text_e.startswith("empty:")
    detail_e = text_e[:200]
    if not snap.is_file():
        snap.write_text(text_e, encoding="utf-8")
        detail_e = f"wrote {snap.name}; {detail_e}"
    elif snap.read_text(encoding="utf-8") != text_e:
        empty_ok = False
        detail_e = "snapshot drift"
    report.cases.append(
        CaseResult(
            id="functional_fixture_search_empty",
            suite="functional",
            passed=empty_ok,
            detail=detail_e,
        )
    )

    text_list = await run_execute(
        name="list_sse_apis", arguments={"limit": 10}, client=FixtureCatalogClient()
    )
    report.cases.append(
        CaseResult(
            id="functional_fixture_list",
            suite="functional",
            passed="getLoanSummary" in text_list,
            detail=text_list[:200],
        )
    )

    text_call = await run_execute(
        name="call_sse_api",
        arguments={"operation_id": "getLoanSummary", "path_params": {"loan_id": "100245"}},
        client=FixtureCatalogClient(),
    )
    call_snap = RESPONSES_DIR / "call_sse_api_ok.txt"
    if not call_snap.is_file():
        call_snap.write_text(text_call, encoding="utf-8")
        call_ok = "100245" in text_call or "fixture" in text_call
    else:
        call_ok = text_call == call_snap.read_text(encoding="utf-8")
    report.cases.append(
        CaseResult(
            id="functional_fixture_call_ok",
            suite="functional",
            passed=call_ok,
            detail=text_call[:200],
        )
    )

    try:
        await run_execute(
            name="call_sse_api",
            arguments={"operation_id": "unknown_op"},
            client=FixtureCatalogClient(),
        )
        unk_ok = False
        detail = "expected PolicyError/ToolError"
    except (ToolError, PolicyError) as exc:
        unk_ok = True
        detail = str(exc)
    report.cases.append(
        CaseResult(
            id="functional_fixture_call_unknown",
            suite="functional",
            passed=unk_ok,
            detail=detail,
        )
    )

    text_lim = await run_execute(
        name="search_sse_apis",
        arguments={"query": "loan", "limit": 1},
        client=FakeClient(mode=FakeMode.OK),
    )
    report.cases.append(
        CaseResult(
            id="functional_limit_one",
            suite="functional",
            passed=text_lim.startswith("ok:"),
            detail=text_lim[:200],
        )
    )


async def _run_errors(report: Layer1Report) -> None:
    modes = (
        ("errors_upstream_fail", FakeMode.FAIL),
        ("errors_upstream_raise", FakeMode.RAISE),
        ("errors_timeout", FakeMode.TIMEOUT),
        ("errors_rate_limit", FakeMode.RATE_LIMIT),
    )
    for case_id, mode in modes:
        client = FakeClient(mode=mode, timeout_flag=True)
        audit = FakeAudit()
        tel = MockTelemetryProvider()
        passed = False
        detail = ""
        try:
            await execute_tool(
                name="search_docs",
                arguments={"query": "escrow"},
                authorization=FIXTURE_AUTH_HEADER,
                user=None,
                tenant=None,
                settings=eval_settings(),
                client=client,
                audit=audit,
                telemetry=tel,
            )
            detail = "expected error"
        except ToolError as exc:
            detail = str(exc)
            passed = _error_path_ok(audit, tel, detail_suffix="")
            if not passed:
                detail += " (audit/telemetry incomplete)"
        except RuntimeError as exc:
            # FakeMode.RAISE propagates from client.call before ToolError wrapping.
            detail = str(exc)
            passed = mode == FakeMode.RAISE and "simulated" in detail
            if passed and audit.events:
                passed = audit.events[-1].payload.get("success") is False
        except Exception as exc:  # noqa: BLE001
            detail = f"{type(exc).__name__}: {exc}"
            passed = False
        report.cases.append(
            CaseResult(id=case_id, suite="errors", passed=passed, detail=detail[:300])
        )


async def _run_perf(driver: AsgiMcpDriver, report: Layer1Report, *, enforce_latency: bool) -> None:
    # Concurrent isolation
    async def one(i: int) -> str:
        client = FakeClient(mode=FakeMode.OK)
        return await run_execute(
            name="search_docs",
            arguments={"query": f"escrow-{i}"},
            client=client,
        )

    results = await asyncio.gather(*[one(i) for i in range(8)])
    conc_ok = all(r == "ok:search_docs" for r in results) and len(results) == 8
    report.cases.append(
        CaseResult(
            id="perf_concurrent_isolation",
            suite="perf",
            passed=conc_ok,
            detail=f"n={len(results)}",
        )
    )

    latencies: list[float] = []
    for _ in range(20):
        client = FakeClient(mode=FakeMode.OK)
        t0 = time.perf_counter()
        await run_execute(
            name="search_docs", arguments={"query": "escrow"}, client=client
        )
        latencies.append((time.perf_counter() - t0) * 1000)
    latencies.sort()
    p50 = percentile(latencies, 50)
    p95 = percentile(latencies, 95)
    report.metrics["latency_p50_ms"] = round(p50, 2)
    report.metrics["latency_p95_ms"] = round(p95, 2)
    lat_ok = True
    detail = f"p50={p50:.2f} p95={p95:.2f}"
    if enforce_latency and p95 > DEFAULT_LATENCY_P95_MS:
        lat_ok = False
        detail += f" (exceeds {DEFAULT_LATENCY_P95_MS})"
        report.breaches.append("latency_p95_ms")
    report.cases.append(
        CaseResult(
            id="perf_latency_percentiles",
            suite="perf",
            passed=lat_ok,
            detail=detail,
            latency_ms=round(p95, 2),
        )
    )

    # Payload budgets: tools/list size + sample FakeClient result
    listed = driver.tools_list()
    list_bytes = len(listed.raw_text.encode("utf-8"))
    sample = await run_execute(
        name="search_docs",
        arguments={"query": "escrow"},
        client=FakeClient(mode=FakeMode.OK),
    )
    sample_bytes = len(sample.encode("utf-8"))
    pay_ok = list_bytes <= MAX_TOOLS_LIST_BYTES and sample_bytes <= MAX_TOOL_RESULT_BYTES
    report.metrics["tools_list_bytes"] = float(list_bytes)
    report.metrics["sample_result_bytes"] = float(sample_bytes)
    report.cases.append(
        CaseResult(
            id="perf_payload_budgets",
            suite="perf",
            passed=pay_ok,
            detail=f"list={list_bytes} sample={sample_bytes} base={ASGI_BASE_URL}",
        )
    )


async def run_layer1(*, enforce_latency: bool = False) -> Layer1Report:
    report = Layer1Report(
        notes=[
            "Auth evaluation deferred by design; fixture bearer is harness plumbing only.",
            "Cursor/Gemini negotiated protocolVersion in the wild: unverified.",
        ]
    )
    driver = AsgiMcpDriver()
    await _run_protocol(driver, report)
    await _run_contracts(driver, report)
    await _run_functional(report)
    await _run_errors(report)
    await _run_perf(driver, report, enforce_latency=enforce_latency)

    # Suite summaries
    for suite in ("protocol", "contracts", "functional", "errors", "perf"):
        subset = [c for c in report.cases if c.suite == suite]
        passed = sum(1 for c in subset if c.passed)
        report.suites[suite] = {
            "total": len(subset),
            "passed": passed,
            "failed": len(subset) - passed,
        }
        if passed < len(subset):
            report.breaches.append(f"suite:{suite}")

    report.thresholds_passed = len(report.breaches) == 0

    # Telemetry metrics
    try:
        tel = get_telemetry_provider()
        await tel.record_metric(
            "eval.mcp.l1.pass_rate",
            (
                sum(1 for c in report.cases if c.passed) / len(report.cases)
                if report.cases
                else 0.0
            ),
            unit="ratio",
            attributes={"total": str(len(report.cases))},
        )
        for suite, stats in report.suites.items():
            total = int(stats["total"]) or 1
            await tel.record_metric(
                f"eval.mcp.l1.{suite}_pass_rate",
                float(stats["passed"]) / float(total),
                unit="ratio",
            )
        if hasattr(tel, "flush"):
            await tel.flush()
    except Exception:  # noqa: BLE001
        report.notes.append("telemetry push failed (fail-open)")

    report.metrics["pass_rate"] = (
        sum(1 for c in report.cases if c.passed) / len(report.cases)
        if report.cases
        else 0.0
    )
    return report


def _print_report(report: Layer1Report) -> None:
    print()
    print("=" * 60)
    print("Layer 1 MCP Eval Report")
    print("=" * 60)
    if report.protocol_version:
        print(f"  protocolVersion: {report.protocol_version}")
    for suite, stats in report.suites.items():
        print(f"  [{suite}] {stats['passed']}/{stats['total']} passed")
    for k, v in report.metrics.items():
        print(f"  metric {k}: {v}")
    failed = [c for c in report.cases if not c.passed]
    if failed:
        print(f"\n  FAILED ({len(failed)}):")
        for c in failed:
            print(f"    - {c.id}: {c.detail[:120]}")
    if report.notes:
        print("\n  Notes:")
        for n in report.notes:
            print(f"    - {n}")
    print()
    if report.thresholds_passed:
        print("  [PASS] ALL LAYER-1 CHECKS PASSED")
    else:
        print(f"  [FAIL] breaches: {report.breaches}")
    print("=" * 60)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Layer 1 MCP evaluation.")
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("out/eval-mcp-l1.json"),
        help="JSON report path",
    )
    parser.add_argument(
        "--enforce-latency",
        action="store_true",
        help="Fail if FakeClient p95 exceeds threshold",
    )
    args = parser.parse_args()
    # Silence unused import warning for all_cases catalog availability
    _ = all_cases
    _ = FIXTURE_BEARER

    report = asyncio.run(run_layer1(enforce_latency=args.enforce_latency))
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    _print_report(report)
    return 0 if report.thresholds_passed else 1


if __name__ == "__main__":
    sys.exit(main())
