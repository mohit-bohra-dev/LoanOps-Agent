"""Tree-sitter grammar smoke + Python/Node route extract fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest
from packages.eakg.analyzers.registry import select_analyzers
from packages.eakg.analyzers.types import AnalyzerResult, GraphFragment
from packages.eakg.extractors.treesitter.node import extract_node_routes
from packages.eakg.extractors.treesitter.python import extract_python_routes
from packages.eakg.merge_api import merge_api_results
from packages.eakg.route_identity import route_key

FIX = Path(__file__).parent / "fixtures"


def test_tree_sitter_grammar_smoke() -> None:
    import tree_sitter_javascript as tsjs
    import tree_sitter_python as tspy
    import tree_sitter_typescript as tsts
    from tree_sitter import Language, Parser

    Parser(Language(tspy.language())).parse(b"def f():\n  return 1\n")
    Parser(Language(tsjs.language())).parse(b"const x = 1;\n")
    Parser(Language(tsts.language_typescript())).parse(b"const x: number = 1;\n")
    Parser(Language(tsts.language_tsx())).parse(b"const x = <div />;\n")


def test_select_analyzers_python_uses_treesitter(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (tmp_path / "main.py").write_text("from fastapi import FastAPI\n", encoding="utf-8")
    chosen, inv, unsupported = select_analyzers(tmp_path, engineering_graph=False)
    assert "python" in inv.languages
    assert any(a.id == "treesitter_api" for a in chosen)
    assert "python" not in unsupported


def test_select_analyzers_java_still_unsupported(tmp_path: Path) -> None:
    (tmp_path / "pom.xml").write_text("<project/>", encoding="utf-8")
    chosen, inv, unsupported = select_analyzers(tmp_path, engineering_graph=False)
    assert "java" in inv.languages
    assert not any(a.produces_api_surface for a in chosen)
    assert "java" in unsupported


def test_python_fixture_routes() -> None:
    facts, _warnings = extract_python_routes(
        FIX / "pythonapi",
        repository_id="pythonapi",
        commit_sha="py1",
    )
    keys = {route_key(f.http_method, f.http_path) for f in facts}
    assert "GET:/api/loans/{loan_id}" in keys
    assert "POST:/webhooks" in keys
    assert "GET:/fees/items/{item_id}" in keys


def test_node_fixture_routes() -> None:
    facts, _warnings = extract_node_routes(
        FIX / "nodeapi",
        repository_id="nodeapi",
        commit_sha="n1",
    )
    keys = {route_key(f.http_method, f.http_path) for f in facts}
    assert "GET:/api/loans/{id}" in keys
    assert "POST:/webhooks" in keys
    assert "GET:/api/legacy" in keys
    assert "GET:/health" in keys
    assert "GET:/ready" in keys
    assert "GET:/env" not in keys


def test_mixed_csharp_node_merge_stable() -> None:
    from packages.eakg.models import ApiOperationFact, Evidence

    def ev(det: str, line: int) -> Evidence:
        return Evidence(
            repository_id="mixed",
            commit_sha="m1",
            file_path="a",
            line_start=line,
            line_end=line,
            detector_id=det,
            detector_version="1.0.0",
            confidence=0.9,
        )

    cs = ApiOperationFact(
        operation_key="GET:/a:C.A",
        http_method="GET",
        http_path="/a",
        controller="C",
        action="A",
        authz_policy=None,
        authz_source="unknown",
        read_only=True,
        evidence=[ev("dotnet_roslyn", 1)],
    )
    node = ApiOperationFact(
        operation_key="GET:/b:main",
        http_method="GET",
        http_path="/b",
        controller="server",
        action="main",
        authz_policy=None,
        authz_source="unknown",
        read_only=True,
        evidence=[ev("treesitter_node", 2)],
    )
    r1 = AnalyzerResult(
        fragment=GraphFragment(),
        extra={"operation_facts": [cs], "extractor": "dotnet_roslyn"},
    )
    r2 = AnalyzerResult(
        fragment=GraphFragment(),
        extra={"operation_facts": [node], "extractor": "treesitter_api"},
    )
    m1 = merge_api_results(
        [r1, r2], repository_id="mixed", application_id="mixed", commit_sha="m1"
    )
    m2 = merge_api_results(
        [r2, r1], repository_id="mixed", application_id="mixed", commit_sha="m1"
    )
    assert [f.http_path for f in m1.facts] == [f.http_path for f in m2.facts]
    assert len(m1.facts) == 2


@pytest.mark.asyncio
async def test_onboard_python_fixture(tmp_path: Path) -> None:
    from packages.common.providers.graph_store import FakeGraphStore
    from packages.eakg.onboard import onboard_repository
    from packages.eakg.registry import RepositoryRegistry
    from packages.eakg.store import ShardStore

    store = ShardStore(tmp_path / "eakg")
    store.ensure_layout()
    registry = RepositoryRegistry(tmp_path / "repositories.yaml")
    registry.register(
        repository_id="pythonapi",
        application="pythonapi",
        application_id="pythonapi",
        git_url="",
    )
    # empty git_url short-circuits to spec-only — set a dummy and use local_path
    rec = registry.get("pythonapi")
    assert rec is not None
    rec.git_url = "https://example.invalid/pythonapi.git"
    registry.upsert(rec)
    registry.save()
    report = await onboard_repository(
        registry,
        store,
        rec,
        skip_clone=True,
        local_path=FIX / "pythonapi",
        engineering_graph=False,
        graph_store=FakeGraphStore(),
    )
    assert "error" not in report or report.get("error") is None
    assert registry.get("pythonapi") is not None
    assert registry.get("pythonapi").index_status == "indexed"  # type: ignore[union-attr]
