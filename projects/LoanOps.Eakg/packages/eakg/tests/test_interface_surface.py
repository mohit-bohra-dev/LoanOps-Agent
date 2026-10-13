"""Interface surface → RDF + describe_application + search_code."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from packages.capability_kg.ontology import (
    CLASS_SERVICE_PROXY,
    DEFAULT_NAMESPACE,
    PRED_PROXY_CLASS,
    loanops_ns,
)
from packages.common.providers.graph_store import FakeGraphStore
from packages.common.settings import EakgConfig, Settings
from packages.eakg.engineering import search_code
from packages.eakg.graph_build import interface_to_graph
from packages.eakg.graph_upload import upload_graph
from packages.eakg.models import RepoInterface
from packages.eakg.query import describe_application
from packages.eakg.rebuild_graphs import rebuild_graphs_from_interfaces
from packages.eakg.store import ShardStore
from packages.tools.eakg_tools import dispatch_eakg_tool
from rdflib.namespace import RDF


def _iface() -> RepoInterface:
    return RepoInterface(
        repository_id="loanservices",
        application_id="loanservices",
        commit_sha="abc",
        operations=[
            {
                "key": "GET:/api/Loans/{id}/Summary",
                "method": "GET",
                "path": "/api/Loans/{id}/Summary",
                "controller": "LoansController",
                "action": "GetLoanSummary",
                "authz_source": "unknown",
                "read_only": True,
            }
        ],
        packages=[{"package_id": "PNMAC.Escrow.Client", "version": "1.0.0"}],
        topics=[{"key": "k1", "value": "FinancialTransactionPosted", "role": "publish"}],
        connection_keys=["LoanServicesContext"],
        service_url_keys=["EscrowUrl"],
        proxies=[
            {
                "class": "EscrowApiProxy",
                "base": "HttpProxyBase",
                "url_key": "EscrowUrl",
            },
            {"class": "CashApiProxy", "base": "HttpProxyBase", "url_key": "CashUrl"},
        ],
        route_compositions=[
            {
                "caller": "SomeFacade.Get",
                "path": "/api/Loans/{id}/Summary",
                "method": "GET",
                "url_key": "LoanServicesUrl",
            }
        ],
    )


def test_interface_to_graph_emits_proxy_triples() -> None:
    g, _eg = interface_to_graph(_iface())
    ns = loanops_ns(DEFAULT_NAMESPACE)
    proxy_types = list(g.subjects(RDF.type, ns[CLASS_SERVICE_PROXY]))
    assert proxy_types
    classes = {str(o) for _s, _p, o in g.triples((None, ns[PRED_PROXY_CLASS], None))}
    assert "EscrowApiProxy" in classes
    assert "CashApiProxy" in classes


@pytest.mark.asyncio
async def test_describe_application_from_graph() -> None:
    iface = _iface()
    g, eg = interface_to_graph(iface)
    gs = FakeGraphStore()
    await upload_graph(gs, "loanservices", g, evidence=eg)
    row = await describe_application(gs, "loanservices")
    assert row.get("source") == "graph"
    classes = {p.get("class") for p in row.get("proxies") or []}
    assert "EscrowApiProxy" in classes
    assert "CashApiProxy" in classes
    assert "LoanServicesContext" in (row.get("connection_keys") or [])
    pkgs = {p.get("package_id") for p in row.get("packages") or []}
    assert "PNMAC.Escrow.Client" in pkgs


@pytest.mark.asyncio
async def test_describe_application_interface_fallback() -> None:
    gs = FakeGraphStore()
    row = await describe_application(
        gs, "loanservices", interface_fallback=_iface()
    )
    assert row.get("source") == "interface"
    assert any(p.get("class") == "EscrowApiProxy" for p in row.get("proxies") or [])


@pytest.mark.asyncio
async def test_describe_application_tool_dispatch(tmp_path: Path) -> None:
    shard = tmp_path / "eakg"
    store = ShardStore(shard)
    store.ensure_layout()
    store.write_interface(_iface())
    settings = Settings(eakg=EakgConfig(shard_dir=str(shard)))
    gs = FakeGraphStore()
    text = await dispatch_eakg_tool(
        "describe_application",
        {"application_id": "loanservices"},
        settings=settings,
        graph_store=gs,
    )
    payload = json.loads(text)
    assert any(p.get("class") == "EscrowApiProxy" for p in payload.get("proxies") or [])


def test_search_code_in_process_fixture(tmp_path: Path) -> None:
    graph = {
        "nodes": [
            {
                "id": "n1",
                "label": "LoanSummaryFacade",
                "source_file": "src/Facades/LoanSummaryFacade.cs",
                "type": "class",
            },
            {
                "id": "n2",
                "label": "EscrowApiProxy",
                "source_file": "src/Proxies/EscrowApiProxy.cs",
                "type": "class",
            },
        ],
        "edges": [],
    }
    path = tmp_path / "graph.json"
    path.write_text(json.dumps(graph), encoding="utf-8")
    row = search_code(
        "loanservices",
        "*Facade*",
        engineering_graph_path=path,
        prefer_subprocess=False,
    )
    assert row.get("source") == "in_process"
    labels = {h.get("label") for h in row.get("hits") or []}
    assert "LoanSummaryFacade" in labels
    assert "EscrowApiProxy" not in labels


def test_search_code_missing_graph(tmp_path: Path) -> None:
    row = search_code(
        "loanservices",
        "Facade",
        engineering_graph_path=tmp_path / "missing.json",
    )
    assert "missing" in str(row.get("error") or "").lower()


@pytest.mark.asyncio
async def test_rebuild_graphs_from_interfaces(tmp_path: Path) -> None:
    store = ShardStore(tmp_path / "eakg")
    store.ensure_layout()
    store.write_interface(_iface())
    gs = FakeGraphStore()
    report = await rebuild_graphs_from_interfaces(
        store, gs, ["loanservices"]
    )
    assert report["loanservices"]["status"] == "ok"
    assert report["loanservices"]["proxies"] == 2
    row = await describe_application(gs, "loanservices")
    assert any(p.get("class") == "EscrowApiProxy" for p in row.get("proxies") or [])


def test_eakg_engineering_graph_setting_default() -> None:
    assert Settings().eakg.engineering_graph is True


@pytest.mark.asyncio
async def test_sync_repo_passes_engineering_graph(monkeypatch: pytest.MonkeyPatch) -> None:
    from packages.eakg import sync as sync_mod

    captured: dict[str, object] = {}

    async def _fake_onboard(*_a: object, **kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        return {"ok": True}

    rec = type(
        "R",
        (),
        {
            "repository_id": "loanservices",
            "application_id": "loanservices",
            "git_url": "https://example.invalid/ls.git",
            "default_branch": "main",
        },
    )()

    class _Reg:
        def get(self, _id: str) -> object:
            return rec

    monkeypatch.setattr(
        sync_mod,
        "eakg_runtime",
        lambda _cfg: (_Reg(), object(), object()),
    )
    monkeypatch.setattr(sync_mod, "onboard_repository", _fake_onboard)
    settings = Settings(
        eakg=EakgConfig(engineering_graph=True, workspace_dir=str(Path(".")))
    )
    await sync_mod.sync_repo("loanservices", settings=settings)
    assert captured.get("engineering_graph") is True
