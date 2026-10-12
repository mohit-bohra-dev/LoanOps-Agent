"""CapabilityCatalogService fingerprint cache."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from packages.tools.capability_catalog import CapabilityCatalogService, shard_fingerprint

_MIN_TTL = """\
@prefix loanops: <https://loanops.local/ontology/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

loanops:cap_get_loan a loanops:Capability ;
    rdfs:label "get_loan" ;
    loanops:operationId "getLoan" ;
    loanops:readOnly true ;
    loanops:reviewStatus "discovered" .
"""


def _write_shard(root: Path) -> None:
    repo = root / "repos" / "demo"
    repo.mkdir(parents=True)
    (repo / "graph.ttl").write_text(_MIN_TTL, encoding="utf-8")
    (root / "enterprise").mkdir(parents=True, exist_ok=True)


def test_fingerprint_changes_when_shard_touched(tmp_path: Path) -> None:
    _write_shard(tmp_path)
    fp1 = shard_fingerprint(tmp_path)
    graph = tmp_path / "repos" / "demo" / "graph.ttl"
    graph.write_text(_MIN_TTL + "\n# touch\n", encoding="utf-8")
    fp2 = shard_fingerprint(tmp_path)
    assert fp1 != fp2


def test_catalog_reuses_merge_until_fingerprint_changes(tmp_path: Path) -> None:
    _write_shard(tmp_path)
    svc = CapabilityCatalogService(tmp_path, enabled=True)
    with patch(
        "packages.tools.capability_catalog.merge_shards",
        wraps=__import__(
            "packages.eakg.merge", fromlist=["merge_shards"]
        ).merge_shards,
    ) as mocked:
        c1 = svc.catalog()
        c2 = svc.catalog()
        assert c1 is not None
        assert c2 is not None
        assert mocked.call_count == 1
        graph = tmp_path / "repos" / "demo" / "graph.ttl"
        graph.write_text(_MIN_TTL + "\n# rebuild\n", encoding="utf-8")
        c3 = svc.catalog()
        assert c3 is not None
        assert mocked.call_count == 2


@pytest.mark.asyncio
async def test_eakg_tool_via_modular_client(tmp_path: Path) -> None:
    from unittest.mock import patch

    from packages.common.providers.graph_store import FakeGraphStore
    from packages.common.settings import CapabilityKgConfig, EakgConfig, Settings
    from packages.db.client import DbConfig, SqlServerClient
    from packages.eakg.graph_upload import upload_graph
    from packages.sse.loader import OpenApiCatalogService
    from packages.tools.modular_tools import ModularToolsClient
    from provider_contracts.tools_client import ToolCall
    from rdflib import Graph

    gs = FakeGraphStore()
    g = Graph()
    g.parse(data=_MIN_TTL, format="turtle")
    await upload_graph(gs, "demo", g)

    settings = Settings(
        eakg=EakgConfig(shard_dir=str(tmp_path)),
        capability_kg=CapabilityKgConfig(enabled=True),
    )
    svc = CapabilityCatalogService(tmp_path, enabled=True)
    sse = OpenApiCatalogService(api_base_url="https://fixture.local", swagger_links=[])
    from packages.sse.types import OpenApiCatalog

    sse._catalog = OpenApiCatalog(operations=[], loaded_at="now", sources=[])
    db = SqlServerClient(DbConfig(), fixture_mode=True)
    client = ModularToolsClient(
        sse=sse,
        db=db,
        role="system",
        catalog_service=svc,
        settings=settings,
        capability_block=None,
    )
    with patch(
        "packages.common.providers.factory.get_graph_store",
        return_value=gs,
    ):
        result = await client.call(
            ToolCall(tool_name="search_capabilities", parameters={"query": "loan"})
        )
    assert result.success
    assert "get_loan" in (result.data or {}).get("text", "") or "getLoan" in (
        result.data or {}
    ).get("text", "")
