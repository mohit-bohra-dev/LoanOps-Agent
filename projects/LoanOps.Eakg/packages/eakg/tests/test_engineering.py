"""Engineering graph projector + analyzer registry (fixtures, no live Graphify)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from packages.eakg.analyzers.protocol import inventory
from packages.eakg.analyzers.registry import select_analyzers
from packages.eakg.engineering import explain_operation, project_links
from packages.eakg.join import eakg_operation_local_name, join_key
from packages.eakg.models import ApiOperationFact, Evidence, RepoInterface
from packages.eakg.onboard import onboard_repository
from packages.eakg.registry import RepositoryRegistry
from packages.eakg.store import ShardStore

FIX = Path(__file__).parent / "fixtures"


def _fact() -> ApiOperationFact:
    return ApiOperationFact(
        operation_key="GET:/api/Loans/{id}/Summary",
        http_method="GET",
        http_path="/api/Loans/{id}/Summary",
        controller="LoansController",
        action="GetLoanSummary",
        authz_policy=None,
        authz_source="unknown",
        read_only=True,
        evidence=[
            Evidence(
                repository_id="loanservices",
                commit_sha="abc",
                file_path="src/LoanServices.WebApi/Controllers/LoansController.cs",
                line_start=8,
                line_end=8,
                detector_id="dotnet_roslyn",
                detector_version="2.0.0",
                confidence=0.97,
            )
        ],
    )


def test_join_key_normalizes_path() -> None:
    assert join_key("loanservices", "get", "/api/Loans/123/Summary") == (
        "loanservices|GET|/api/loans/{id}/summary"
    )


def test_project_links_matches_file_and_action(tmp_path: Path) -> None:
    graph = {
        "nodes": [
            {
                "id": "n_getloansummary",
                "label": "GetLoanSummary",
                "source_file": "src/LoanServices.WebApi/Controllers/LoansController.cs",
                "source_location": "L8",
            },
            {
                "id": "n_task",
                "label": "Task",
                "source_file": "src/LoanServices.WebApi/Controllers/LoansController.cs",
                "source_location": "L8",
            },
        ],
        "edges": [
            {
                "source": "n_caller",
                "target": "n_getloansummary",
                "relation": "calls",
            },
            {
                "id": "ignored",
            },
        ],
    }
    # caller node
    graph["nodes"].append(
        {
            "id": "n_caller",
            "label": "SomeService.Run",
            "source_file": "src/LoanServices.WebApi/Services/SomeService.cs",
            "source_location": "L20",
        }
    )
    gpath = tmp_path / "graph.json"
    gpath.write_text(json.dumps(graph), encoding="utf-8")
    iface = RepoInterface(
        repository_id="loanservices",
        application_id="loanservices",
        commit_sha="abc",
    )
    payload = project_links(iface, [_fact()], gpath, commit_sha="abc")
    assert len(payload["links"]) == 1
    row = payload["links"][0]
    assert row["graphify_node_id"] == "n_getloansummary"
    assert row["eakg_operation"] == eakg_operation_local_name(
        "loanservices", "GetLoanSummary", "GET"
    )
    assert "Task" not in row["symbol"]
    lpath = tmp_path / "links.json"
    lpath.write_text(json.dumps(payload), encoding="utf-8")
    explained = explain_operation(lpath, gpath, str(row["eakg_operation"]))
    assert explained.get("file", "").endswith("LoansController.cs")
    callers = explained.get("callers")
    assert isinstance(callers, list)
    assert any(c.get("id") == "n_caller" for c in callers)


def test_project_links_skips_without_file_match(tmp_path: Path) -> None:
    graph = {
        "nodes": [
            {
                "id": "n_other",
                "label": "GetLoanSummary",
                "source_file": "src/Other/OtherController.cs",
            }
        ],
        "edges": [],
    }
    gpath = tmp_path / "graph.json"
    gpath.write_text(json.dumps(graph), encoding="utf-8")
    iface = RepoInterface(
        repository_id="loanservices",
        application_id="loanservices",
        commit_sha="abc",
    )
    payload = project_links(iface, [_fact()], gpath, commit_sha="abc")
    assert payload["links"] == []


def test_select_analyzers_java_has_no_api_adapter(tmp_path: Path) -> None:
    (tmp_path / "pom.xml").write_text("<project/>", encoding="utf-8")
    chosen, inv, unsupported = select_analyzers(tmp_path, engineering_graph=False)
    assert "java" in inv.languages
    assert not any(a.produces_api_surface for a in chosen)
    assert "java" in unsupported


def test_select_analyzers_python_does_not_wipe_dotnet(tmp_path: Path) -> None:
    """Unknown/extra language recorded; DotNet still selected."""
    csproj = tmp_path / "App.csproj"
    csproj.write_text(
        '<Project Sdk="Microsoft.NET.Sdk.Web"><ItemGroup></ItemGroup></Project>',
        encoding="utf-8",
    )
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    chosen, inv, unsupported = select_analyzers(tmp_path, engineering_graph=False)
    assert "csharp" in inv.languages
    assert "python" in inv.languages
    assert any(a.id == "dotnet_roslyn" for a in chosen)
    assert "python" in unsupported
    assert "csharp" not in unsupported


@pytest.mark.asyncio
async def test_onboard_java_fails_without_wiping_dotnet_path(tmp_path: Path) -> None:
    java = tmp_path / "javaapp"
    java.mkdir()
    (java / "pom.xml").write_text("<project/>", encoding="utf-8")
    store = ShardStore(tmp_path / "eakg")
    store.ensure_layout()
    registry = RepositoryRegistry(tmp_path / "repositories.yaml")
    registry.register(
        repository_id="javaapp",
        application="javaapp",
        application_id="javaapp",
        git_url="https://example.invalid/java.git",
    )
    rec = registry.get("javaapp")
    assert rec is not None
    report = await onboard_repository(registry, store, rec, local_path=java)
    assert report.get("error", "").startswith("no extractor")
    assert store.read_interface("javaapp") is None


@pytest.mark.asyncio
async def test_onboard_engineering_graph_failed_still_indexed(tmp_path: Path) -> None:
    store = ShardStore(tmp_path / "eakg")
    store.ensure_layout()
    registry = RepositoryRegistry(tmp_path / "repositories.yaml")
    registry.register(
        repository_id="loanservices",
        application="loanservices",
        application_id="loanservices",
        git_url="https://example.invalid/ls.git",
        api_project_path="src/LoanServices.WebApi",
    )
    rec = registry.get("loanservices")
    assert rec is not None
    report = await onboard_repository(
        registry,
        store,
        rec,
        local_path=FIX / "loanservices",
        engineering_graph=True,
    )
    assert store.read_interface("loanservices") is not None
    eng = [s for s in report["stages"] if "engineering_graph" in s]
    assert eng
    # graphify missing or extract failed → failed; clone still indexed
    assert eng[-1]["engineering_graph"] in {"ok", "failed"}
    man = store.read_manifest("loanservices")
    assert man is not None
    assert man.get("engineering_graph") in {"ok", "failed"}


def test_inventory_fees_is_csharp() -> None:
    inv = inventory(FIX / "fees")
    assert "csharp" in inv.languages
