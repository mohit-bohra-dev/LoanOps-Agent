"""ADR-029: coverage, ledger, gate, investigator, patterns, backtest."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from packages.eakg.analyzers.types import AnalyzerResult, GraphFragment, Inventory
from packages.eakg.candidate_gate import CandidateProposal, validate_candidate
from packages.eakg.coverage import build_coverage_manifest
from packages.eakg.gap_ledger import (
    build_ledger,
    count_by_shape,
    from_openapi_join_report,
    shapes_eligible_for_pattern,
)
from packages.eakg.investigate_agent import (
    InvestigateContext,
    investigate_item,
    persist_accepted_proposals,
)
from packages.eakg.merge_api import ConflictRecord, merge_operation_facts
from packages.eakg.models import ApiOperationFact, Evidence, RepoInterface
from packages.eakg.pattern_backtest import backtest_pattern_proposal
from packages.eakg.patterns import PatternSet, load_patterns
from packages.eakg.store import ShardStore


@dataclass
class _FakeAnalyzer:
    id: str
    version: str = "1.0.0"
    languages: frozenset[str] = frozenset({"csharp"})
    produces_api_surface: bool = True
    fatal: bool = True

    def detect(self, repo: Path) -> float:
        return 1.0

    def extract(self, *args: Any, **kwargs: Any) -> AnalyzerResult:
        return AnalyzerResult(fragment=GraphFragment())


def _ev(det: str = "dotnet_roslyn") -> Evidence:
    return Evidence(
        repository_id="r1",
        commit_sha="abc",
        file_path="C.cs",
        line_start=1,
        line_end=2,
        detector_id=det,
        detector_version="1.0.0",
        confidence=1.0,
    )


def test_coverage_incomplete_on_zero_ops() -> None:
    a = _FakeAnalyzer(id="dotnet_roslyn")
    res = AnalyzerResult(
        fragment=GraphFragment(),
        extra={"operation_facts": []},
    )
    m = build_coverage_manifest(
        repository_id="r1",
        adapters=[a],  # type: ignore[list-item]
        results=[res],
        inventory=Inventory(languages=["csharp"], projects=["x.csproj"]),
        unsupported=[],
        patterns_hash="deadbeef",
    )
    assert m.status == "incomplete"
    assert any("zero_operations" in r for r in m.incomplete_reasons)


def test_conflict_record_on_field_mismatch() -> None:
    a = ApiOperationFact(
        operation_key="k",
        http_method="GET",
        http_path="/x",
        controller="A",
        action="GetX",
        authz_policy="polA",
        authz_source="attribute",
        read_only=True,
        evidence=[_ev("dotnet_roslyn")],
    )
    b = ApiOperationFact(
        operation_key="k2",
        http_method="GET",
        http_path="/x",
        controller="A",
        action="GetX",
        authz_policy="polB",
        authz_source="attribute",
        read_only=True,
        evidence=[_ev("treesitter_python")],
    )
    merged = merge_operation_facts([a, b], repository_id="r1", application_id="app", commit_sha="c")
    assert len(merged.facts) == 1
    assert any(c.field == "authz_policy" for c in merged.conflicts)


def test_ledger_from_openapi_and_shape_pattern_eligibility() -> None:
    report = {
        "openapi_only": ["fees:getFees", "fees:getOther", "fees:getThird"],
        "eakg_only": [],
        "ambiguous": [],
    }
    items = from_openapi_join_report(report, repository_id="fees")
    assert len(items) == 3
    assert shapes_eligible_for_pattern(items)  # same shape key openapi:openapi_only:*
    # shape keys differ by public_id feature — check count_by_shape
    counts = count_by_shape(items)
    assert sum(counts.values()) == 3


def test_gate_rejects_boundary_and_bad_method() -> None:
    bad = CandidateProposal(
        kind="operation",
        repository_id="r1",
        ledger_item_id="g1",
        payload={"method": "TRACE", "path": "/x"},
        evidence=[{"file_path": "a.cs", "line_start": 1}],
    )
    v = validate_candidate(bad)
    assert not v.accepted
    assert any("bad_method" in r for r in v.reasons)

    boundary = CandidateProposal(
        kind="capability_link",
        repository_id="r1",
        ledger_item_id="g2",
        payload={"kind": "capability_link"},
        evidence=[{"detector_id": "dotnet_roslyn", "file_path": "a.cs"}],
        source_tool="read_file_window",
    )
    v2 = validate_candidate(boundary)
    assert not v2.accepted
    assert "boundary_implementation_to_capability" in v2.reasons


def test_gate_accepts_no_finding() -> None:
    prop = CandidateProposal(
        kind="no_finding",
        repository_id="r1",
        ledger_item_id="g1",
        payload={"rationale": "nothing there"},
    )
    assert validate_candidate(prop).accepted


@pytest.mark.asyncio
async def test_investigate_item_mock_chat_no_finding(tmp_path: Path) -> None:
    from packages.common.providers.chat import LLMMessage, LLMResponse, ToolCallRequest

    class FakeChat:
        async def chat(self, messages: list[LLMMessage], **kwargs: Any) -> LLMResponse:
            return LLMResponse(
                content="",
                model="fake",
                tool_calls=[
                    ToolCallRequest(
                        name="propose_no_finding",
                        arguments={"rationale": "cannot resolve"},
                    )
                ],
            )

    from packages.eakg.gap_ledger import LedgerItem

    item = LedgerItem(
        item_id="gap_1",
        shape_key="openapi:openapi_only:fees:getFees",
        source="openapi",
        kind="openapi_only",
        repository_id="fees",
        context={"public_id": "fees:getFees"},
    )
    res = await investigate_item(
        item,
        chat=FakeChat(),
        ctx=InvestigateContext(repository_id="fees"),
        allow_pattern=False,
    )
    assert res.closed_as == "no_finding"
    assert res.verdicts and res.verdicts[0].accepted


@pytest.mark.asyncio
async def test_persist_proposals(tmp_path: Path) -> None:
    store = ShardStore(tmp_path)
    store.ensure_layout()
    from packages.eakg.investigate_agent import InvestigateResult
    from packages.eakg.candidate_gate import GateVerdict

    prop = CandidateProposal(
        kind="operation",
        repository_id="fees",
        ledger_item_id="gap_1",
        payload={"method": "GET", "path": "/api/fees", "controller": "F", "action": "Get"},
        evidence=[
            {
                "repository_id": "fees",
                "commit_sha": "c",
                "file_path": "spec.json",
                "line_start": 1,
                "line_end": 1,
                "detector_id": "llm_investigate_openapi",
                "detector_version": "1.0.0",
                "confidence": 0.5,
            }
        ],
    )
    result = InvestigateResult(
        ledger_item_id="gap_1",
        proposals=[prop],
        verdicts=[GateVerdict(accepted=True)],
        closed_as="proposed",
    )
    written = persist_accepted_proposals(store, result)
    assert len(written) == 1
    assert written[0].status == "pending_review"
    assert written[0].payload.get("callable") is False


def test_load_patterns_and_backtest_fail_on_regression(tmp_path: Path) -> None:
    d = tmp_path / "patterns"
    d.mkdir()
    (d / "sdk_suffixes.yaml").write_text(
        "client_suffixes: ['.Client']\ndomain_suffixes: ['.Domain']\n",
        encoding="utf-8",
    )
    ps = load_patterns(d)
    assert ps.patterns_hash
    assert ".Client" in ps.sdk_client_suffixes

    iface = RepoInterface(
        repository_id="r1",
        application_id="loanservices",
        commit_sha="c",
        packages=[{"package_id": "PNMAC.Fees.Client", "project": "a.csproj"}],
    )
    # Candidate that drops .Client → regression
    report = backtest_pattern_proposal(
        proposal_payload={
            "pattern_file": "sdk_suffixes.yaml",
            "yaml_fragment": "client_suffixes: []\ndomain_suffixes: ['.Domain']\n",
        },
        motivating_items=[],
        established_interfaces=[iface],
        baseline_patterns=ps,
    )
    assert not report.passed
    assert report.established_changed


def test_build_ledger_combines_sources() -> None:
    cov = build_coverage_manifest(
        repository_id="r1",
        adapters=[_FakeAnalyzer(id="dotnet_roslyn")],  # type: ignore[list-item]
        results=[AnalyzerResult(fragment=GraphFragment(), error="boom")],
        inventory=Inventory(languages=["csharp", "java"], projects=[]),
        unsupported=["java"],
    )
    items = build_ledger(
        coverage=cov,
        conflicts=[
            ConflictRecord(
                route_key="GET:/x",
                field="action",
                preferred_value="A",
                other_value="B",
                preferred_detector="dotnet_roslyn",
                other_detector="treesitter_python",
            )
        ],
        openapi_report={"openapi_only": ["a:b"], "eakg_only": [], "ambiguous": []},
        unmapped_taac=["FeesUrl"],
        repository_id="r1",
    )
    sources = {i.source for i in items}
    assert "coverage" in sources or "code" in sources
    assert "conflict" in sources
    assert "openapi" in sources
    assert "taac" in sources
