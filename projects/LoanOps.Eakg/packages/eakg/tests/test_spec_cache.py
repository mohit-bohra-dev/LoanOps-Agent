"""Cached OpenAPI specs: last-good retention and registry catalog with no HTTP."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from packages.eakg.registry import AppEnvironment, RepositoryRecord, RepositoryRegistry
from packages.eakg.spec_cache import read_current_spec, refresh_spec
from packages.eakg.store import ShardStore
from packages.sse.loader import OpenApiCatalogService, resolve_catalog_source


async def _token(_app: str, _aud: str) -> str:
    return ""


def _fees(fixture: str) -> RepositoryRecord:
    return RepositoryRecord(
        repository_id="fees",
        application="Fees",
        application_id="fees",
        git_url="",
        environments={"local": AppEnvironment(base_url="http://127.0.0.1:9102", spec_fixture=fixture)},
    )


@pytest.mark.asyncio
async def test_refresh_keeps_last_good_spec(tmp_path: Path) -> None:
    fixture = tmp_path / "fees.openapi.json"
    fixture.write_text(
        '{"openapi":"3.0.3","info":{"title":"Fees","version":"1"},"paths":{"/api/fees":{"get":{"operationId":"getFees"}}}}',
        encoding="utf-8",
    )
    store = ShardStore(tmp_path / "shards")
    record = _fees(str(fixture))
    first = await refresh_spec(record, "local", store, _token)
    assert first["status"] == "ok"
    record.environments["local"].spec_fixture = str(tmp_path / "missing.json")
    second = await refresh_spec(record, "local", store, _token)
    assert second["status"] == "failed"
    assert second["spec_hash"] == first["spec_hash"]
    doc, _pointer = read_current_spec(store, "fees", "local")
    assert doc is not None
    assert "paths" in doc


@pytest.mark.asyncio
async def test_registry_catalog_does_not_open_http(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fixture = tmp_path / "fees.openapi.json"
    fixture.write_text(
        '{"openapi":"3.0.3","info":{"title":"Fees","version":"1"},"paths":{"/api/fees":{"get":{"operationId":"getFees","summary":"Get fees"}}}}',
        encoding="utf-8",
    )
    store = ShardStore(tmp_path / "shards")
    await refresh_spec(_fees(str(fixture)), "local", store, _token)
    doc, _pointer = read_current_spec(store, "fees", "local")

    def _boom(*_args: object, **_kwargs: object) -> httpx.AsyncClient:
        raise AssertionError("registry catalog must not construct an HTTP client")

    monkeypatch.setattr(httpx, "AsyncClient", _boom)
    service = OpenApiCatalogService(
        swagger_links=[],
        fixture_path=None,
        registry_specs=[
            {
                "source_id": "fees",
                "label": "Fees",
                "base_url": "http://127.0.0.1:9102",
                "document": doc,
            }
        ],
    )
    catalog = await service.load()
    assert catalog.sources[0].operation_count == 1
    assert catalog.operations[0].id == "fees:getFees"


def test_env_example_selects_registry_and_pgvector() -> None:
    text = Path(".env.example").read_text(encoding="utf-8")
    assert "SSE__CATALOG_SOURCE=registry" in text
    assert "VECTOR_STORE__PROVIDER=pgvector" in text
    assert "\nVECTOR_STORE__PROVIDER=qdrant" not in text


def test_auto_prefers_registry_when_a_spec_exists() -> None:
    assert (
        resolve_catalog_source(
            "auto",
            has_swagger_links=False,
            registry_has_spec=True,
            use_fixture=True,
        )
        == "registry"
    )


@pytest.mark.asyncio
async def test_reload_registry_swaps_cached_spec() -> None:
    first: dict[str, object] = {
        "source_id": "fees",
        "label": "Fees",
        "base_url": "http://127.0.0.1:9102",
        "document": {
            "openapi": "3.0.3",
            "paths": {"/api/fees": {"get": {"operationId": "getFees"}}},
        },
    }
    second: dict[str, object] = {
        **first,
        "document": {
            "openapi": "3.0.3",
            "paths": {"/api/fees/{id}": {"get": {"operationId": "getFeeById"}}},
        },
    }
    current: dict[str, list[dict[str, object]]] = {"specs": [first]}

    def _reload() -> list[dict[str, object]]:
        return list(current["specs"])

    service = OpenApiCatalogService(swagger_links=[], registry_specs=[first], reload_specs=_reload)
    loaded = await service.load()
    assert loaded.operations[0].operation_id == "getFees"
    current["specs"] = [second]
    service.reload_registry()
    reloaded = await service.load()
    assert reloaded.operations[0].operation_id == "getFeeById"


def test_legacy_registry_still_lists_three_apps() -> None:
    registry = RepositoryRegistry("data/eakg/registry/repositories.yaml")
    assert {rec.repository_id for rec in registry.list()} >= {"escrow", "fees", "loanservices"}
    local = {rec.application_id for rec in registry.list_active("local")}
    assert local == {"escrow", "fees", "loanservices"}
