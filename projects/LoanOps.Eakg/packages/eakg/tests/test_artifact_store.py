"""File artifact store round-trip (Postgres covered by migrate operator path)."""

from __future__ import annotations

from pathlib import Path

from packages.eakg.artifact_store import FileEakgArtifactStore
from packages.eakg.registry import RepositoryRegistry


def test_file_store_registry_and_interface(tmp_path: Path) -> None:
    reg_path = tmp_path / "repositories.yaml"
    store = FileEakgArtifactStore(tmp_path / "eakg", registry_path=reg_path)
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
