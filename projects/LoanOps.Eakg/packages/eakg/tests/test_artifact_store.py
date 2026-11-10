"""File artifact store round-trip (Postgres covered by migrate operator path)."""

from __future__ import annotations

from pathlib import Path

from packages.eakg.artifact_store import FileEakgArtifactStore
from packages.eakg.registry import RepositoryRegistry


def test_file_store_registry_and_interface(tmp_path: Path) -> None:
    reg_path = tmp_path / "repositories.yaml"
    root = tmp_path / "pipeline_store"
    store = FileEakgArtifactStore(root, registry_path=reg_path)
    store.ensure_schema()
    store.save_registry(
        [
            {
                "repository_id": "fees",
                "application": "fees",
                "application_id": "fees",
                "git_url": "https://example.invalid/fees.git",
            }
        ]
    )
    assert (root / "Postgres" / "registry.yaml").is_file()
    registry = RepositoryRegistry(reg_path, artifact_store=store)
    assert registry.get("fees") is not None
    store.put_interface(
        "fees",
        {
            "repository_id": "fees",
            "application_id": "fees",
            "commit_sha": "abc",
            "operations": [],
            "packages": [],
        },
    )
    assert (root / "Postgres" / "interface" / "fees.json").is_file()
    iface = store.get_interface("fees")
    assert iface is not None
    assert iface["commit_sha"] == "abc"
    store.put_openapi(
        "fees",
        "local",
        pointer={"spec_hash": "deadbeef", "status": "ok"},
        spec={"openapi": "3.0.0", "paths": {}},
    )
    spec, pointer = store.get_openapi_spec("fees", "local")
    assert pointer is not None
    assert pointer["spec_hash"] == "deadbeef"
    assert spec is not None
    assert spec["openapi"] == "3.0.0"
    store.put_embeddings({"version": 1, "capabilities": []})
    assert store.get_embeddings() is not None
    store.append_proposal("fees", {"id": "p1"})
    assert store.read_proposals("fees")[0]["id"] == "p1"
    store.put_engineering("fees", "links.json", {"edges": []})
    assert store.get_engineering("fees", "links.json") == {"edges": []}
    store.put_sop_page("escrow/x.md", "# hi\n")
    assert store.get_sop_page("escrow/x.md") == "# hi\n"
    store.put_pipeline_run(
        "run_1",
        "openapi_to_api_index",
        {
            "status": "succeeded",
            "started_at": "2026-11-10T12:00:00Z",
            "params": {"environment": "dev"},
        },
    )
    got = store.get_pipeline_run("run_1")
    assert got is not None
    assert got["status"] == "succeeded"
    assert got["pipeline_id"] == "openapi_to_api_index"
    listed = store.list_pipeline_runs("openapi_to_api_index", limit=10)
    assert len(listed) == 1
    assert listed[0]["run_id"] == "run_1"
