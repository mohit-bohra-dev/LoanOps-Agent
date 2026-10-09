"""Registry application mapping and validation (FR-022)."""

from __future__ import annotations

import json
from pathlib import Path

from packages.eakg.registry import AppEnvironment, RepositoryRecord, RepositoryRegistry
from packages.eakg.registry_import import import_taac
from packages.eakg.registry_validate import validate_registry


def _record(
    app_id: str,
    *,
    git_url: str = "https://gitlab.example.invalid/apps/fees.git",
    service_url_key: str = "",
    environments: dict[str, AppEnvironment] | None = None,
) -> RepositoryRecord:
    return RepositoryRecord(
        repository_id=app_id,
        application=app_id,
        application_id=app_id,
        git_url=git_url,
        service_url_key=service_url_key,
        environments=environments or {},
        shard_path=f"repos/{app_id}",
    )


def test_mapping_round_trip_keeps_source_and_address(tmp_path: Path) -> None:
    path = tmp_path / "repositories.yaml"
    registry = RepositoryRegistry(path)
    registry.upsert(
        _record(
            "fees",
            service_url_key="FeesApiUrl",
            environments={
                "dev": AppEnvironment(
                    base_url="https://feesapi.dev.example.invalid",
                    auth_audience="https://api.example.invalid",
                )
            },
        )
    )
    registry.save()
    loaded = RepositoryRegistry(path).get("fees")
    assert loaded is not None
    assert loaded.git_url.endswith("/fees.git")
    assert loaded.service_url_key == "FeesApiUrl"
    assert loaded.environments["dev"].base_url == "https://feesapi.dev.example.invalid"
    assert "lifecycle" not in loaded.to_dict()


def test_legacy_yaml_loads_without_new_fields(tmp_path: Path) -> None:
    path = tmp_path / "repositories.yaml"
    path.write_text(
        "repositories:\n"
        "- repository_id: fees\n"
        "  application: Fees\n"
        "  application_id: fees\n"
        "  git_url: https://gitlab.example.invalid/fees.git\n",
        encoding="utf-8",
    )
    loaded = RepositoryRegistry(path).get("fees")
    assert loaded is not None
    assert loaded.git_url.endswith("/fees.git")
    assert loaded.environments == {}
    assert loaded.lifecycle == "active"


def test_api_only_is_active_and_source_only_is_not(tmp_path: Path) -> None:
    path = tmp_path / "repositories.yaml"
    registry = RepositoryRegistry(path)
    registry.upsert(
        _record(
            "fees",
            git_url="",
            environments={"local": AppEnvironment(base_url="http://127.0.0.1:9101")},
        )
    )
    registry.upsert(
        _record(
            "escrow",
            git_url="https://gitlab.example.invalid/escrow.git",
            environments={},
        )
    )
    active = {rec.application_id for rec in registry.list_active("local")}
    assert active == {"fees"}


def test_env_mismatch_and_bad_url(tmp_path: Path) -> None:
    path = tmp_path / "repositories.yaml"
    registry = RepositoryRegistry(path)
    registry.upsert(
        _record(
            "fees",
            environments={"dev": AppEnvironment(base_url="https://feesapi.stage.example.invalid", auth_audience="https://api.example.invalid")},
        )
    )
    codes = {issue.code for issue in validate_registry(registry)["fees"]}
    assert "env_mismatch" in codes
    assert registry.list_active("dev") == []


def test_taac_fills_blank_url_and_does_not_write_git(tmp_path: Path) -> None:
    path = tmp_path / "repositories.yaml"
    registry = RepositoryRegistry(path)
    registry.upsert(_record("fees", git_url="https://gitlab.example.invalid/fees.git", service_url_key="FeesApiUrl"))
    registry.upsert(_record("ghost", git_url=""))
    taac = tmp_path / "taac.json"
    taac.write_text(
        json.dumps(
            {
                "Auth0": {"Api": {"Identifier": "https://api.example.invalid"}},
                "ServiceUrls": {
                    "FeesApiUrl": "https://feesapi.dev.example.invalid",
                    "UnknownApiUrl": "https://unknown.dev.example.invalid",
                },
            }
        ),
        encoding="utf-8",
    )
    report = import_taac(registry, taac, "dev", dry_run=False)
    loaded = RepositoryRegistry(path).get("fees")
    assert loaded is not None
    assert loaded.git_url == "https://gitlab.example.invalid/fees.git"
    assert loaded.environments["dev"].base_url == "https://feesapi.dev.example.invalid"
    assert "fees" in report.filled
    assert "UnknownApiUrl" in report.unregistered
    assert RepositoryRegistry(path).get("ghost") is not None
    assert RepositoryRegistry(path).get("ghost").git_url == ""  # type: ignore[union-attr]


def test_taac_does_not_overwrite_existing_url(tmp_path: Path) -> None:
    path = tmp_path / "repositories.yaml"
    registry = RepositoryRegistry(path)
    registry.upsert(
        _record(
            "fees",
            environments={"dev": AppEnvironment(base_url="https://feesapi.dev.example.invalid", auth_audience="https://api.example.invalid")},
        )
    )
    taac = tmp_path / "taac.json"
    taac.write_text(
        json.dumps({"ServiceUrls": {"FeesApiUrl": "https://other.dev.example.invalid"}}),
        encoding="utf-8",
    )
    report = import_taac(registry, taac, "dev")
    loaded = registry.get("fees")
    assert loaded is not None
    assert loaded.environments["dev"].base_url == "https://feesapi.dev.example.invalid"
    assert report.conflicts
