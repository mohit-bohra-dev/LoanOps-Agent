"""Repository Registry — data-driven onboarding entry (ADR-016)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml  # type: ignore[import-untyped]

# Any used for optional artifact_store to avoid circular import at type-check time.
from packages.eakg.models import AccessStatus, IndexStatus, utc_now_iso

VALID_INDEX = frozenset(
    {
        "registered",
        "cloning",
        "extracting",
        "enriching",
        "pending_review",
        "indexed",
        "failed",
    }
)
VALID_ACCESS = frozenset({"ok", "no_access", "auth_required"})
EnvironmentName = Literal["local", "dev", "stage", "prod"]
Lifecycle = Literal["registered", "active", "degraded", "retired"]
VALID_ENV = frozenset({"local", "dev", "stage", "prod"})
VALID_LIFECYCLE = frozenset({"registered", "active", "degraded", "retired"})


def _lifecycle(value: object) -> Lifecycle:
    text = str(value or "active")
    if text not in VALID_LIFECYCLE:
        return "active"
    return text  # type: ignore[return-value]


def _environments(value: object) -> dict[str, AppEnvironment]:
    if not isinstance(value, dict):
        return {}
    out: dict[str, AppEnvironment] = {}
    for key, raw in value.items():
        if isinstance(raw, dict):
            out[str(key)] = AppEnvironment.from_dict(raw)
    return out


@dataclass
class AppEnvironment:
    """Live address for one application in one environment (FR-022)."""

    base_url: str
    auth_audience: str = ""
    spec_path: str = ""
    spec_fixture: str = ""
    enabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if data["auth_audience"] == "":
            del data["auth_audience"]
        if data["spec_path"] == "":
            del data["spec_path"]
        if data["spec_fixture"] == "":
            del data["spec_fixture"]
        if data["enabled"] is True:
            del data["enabled"]
        return data

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> AppEnvironment:
        return cls(
            base_url=str(raw.get("base_url") or ""),
            auth_audience=str(raw.get("auth_audience") or ""),
            spec_path=str(raw.get("spec_path") or ""),
            spec_fixture=str(raw.get("spec_fixture") or ""),
            enabled=bool(raw.get("enabled", True)),
        )


@dataclass
class RepositoryRecord:
    repository_id: str
    application: str
    application_id: str
    git_url: str = ""
    default_branch: str = "main"
    gitlab_project_id: int | None = None
    team: str = ""
    owner: str = ""
    technology: str = ""
    last_indexed_commit: str = ""
    last_indexed_at: str = ""
    index_status: IndexStatus = "registered"
    access_status: AccessStatus = "ok"
    visibility: str = ""
    deployables: list[str] = field(default_factory=list)
    detector_versions: dict[str, str] = field(default_factory=dict)
    shard_path: str = ""
    api_project_path: str = ""  # e.g. src/Fees.WebApi
    lifecycle: Lifecycle = "active"
    service_url_key: str = ""
    environments: dict[str, AppEnvironment] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["environments"] = {
            key: env.to_dict() if isinstance(env, AppEnvironment) else AppEnvironment.from_dict(env).to_dict()
            for key, env in self.environments.items()
        }
        if not data["environments"]:
            del data["environments"]
        if data.get("lifecycle") == "active":
            del data["lifecycle"]
        if not data.get("service_url_key"):
            del data["service_url_key"]
        return data

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> RepositoryRecord:
        status = str(raw.get("index_status") or "registered")
        if status not in VALID_INDEX:
            status = "registered"
        access = str(raw.get("access_status") or "ok")
        if access not in VALID_ACCESS:
            access = "ok"
        return cls(
            repository_id=str(raw["repository_id"]),
            application=str(raw.get("application") or raw["repository_id"]),
            application_id=str(raw.get("application_id") or raw["repository_id"]),
            git_url=str(raw.get("git_url") or ""),
            default_branch=str(raw.get("default_branch") or "main"),
            gitlab_project_id=(
                int(raw["gitlab_project_id"]) if raw.get("gitlab_project_id") is not None else None
            ),
            team=str(raw.get("team") or ""),
            owner=str(raw.get("owner") or ""),
            technology=str(raw.get("technology") or ""),
            last_indexed_commit=str(raw.get("last_indexed_commit") or ""),
            last_indexed_at=str(raw.get("last_indexed_at") or ""),
            index_status=status,  # type: ignore[arg-type]
            access_status=access,  # type: ignore[arg-type]
            visibility=str(raw.get("visibility") or ""),
            deployables=list(raw.get("deployables") or []),
            detector_versions=dict(raw.get("detector_versions") or {}),
            shard_path=str(raw.get("shard_path") or ""),
            api_project_path=str(raw.get("api_project_path") or ""),
            lifecycle=_lifecycle(raw.get("lifecycle")),
            service_url_key=str(raw.get("service_url_key") or ""),
            environments=_environments(raw.get("environments")),
        )


class RepositoryRegistry:
    """Load / save repository registry (file YAML or Postgres — ADR-027)."""

    def __init__(
        self,
        path: str | Path,
        *,
        artifact_store: Any | None = None,
    ) -> None:
        from packages.eakg.artifact_store import AbstractEakgArtifactStore

        self.path = Path(path)
        self._store: AbstractEakgArtifactStore | None = artifact_store
        self._records: dict[str, RepositoryRecord] = {}
        if self._store is not None:
            self.reload()
        elif self.path.is_file():
            self.reload()

    def reload(self) -> None:
        if self._store is not None:
            repos = self._store.load_registry()
        else:
            raw = yaml.safe_load(self.path.read_text(encoding="utf-8")) or {}
            repos = raw.get("repositories") or []
        self._records = {
            str(r["repository_id"]): RepositoryRecord.from_dict(r)
            for r in repos
            if isinstance(r, dict) and r.get("repository_id")
        }

    def save(self) -> None:
        payload = [r.to_dict() for r in sorted(self._records.values(), key=lambda x: x.repository_id)]
        if self._store is not None:
            self._store.save_registry(payload)
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            yaml.safe_dump({"repositories": payload}, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )

    def list_active(self, environment: str) -> list[RepositoryRecord]:
        """Apps callable in this environment: not retired, env enabled, no blocking issues."""
        from packages.eakg.registry_validate import blocking_issues, validate_registry

        issues = validate_registry(self)
        active: list[RepositoryRecord] = []
        for record in self._records.values():
            if record.lifecycle == "retired":
                continue
            env = record.environments.get(environment)
            if env is None or not env.enabled:
                continue
            if blocking_issues(record, environment, issues):
                continue
            active.append(record)
        return active

    def list(self) -> list[RepositoryRecord]:
        return list(self._records.values())

    def get(self, repository_id: str) -> RepositoryRecord | None:
        return self._records.get(repository_id)

    def upsert(self, record: RepositoryRecord) -> None:
        if not record.shard_path:
            record.shard_path = f"repos/{record.repository_id}"
        self._records[record.repository_id] = record

    def set_status(
        self,
        repository_id: str,
        *,
        index_status: IndexStatus | None = None,
        access_status: AccessStatus | None = None,
        commit: str | None = None,
    ) -> RepositoryRecord:
        rec = self._records[repository_id]
        if index_status is not None:
            rec.index_status = index_status
        if access_status is not None:
            rec.access_status = access_status
        if commit is not None:
            rec.last_indexed_commit = commit
            rec.last_indexed_at = utc_now_iso()
        self.save()
        return rec

    def register(
        self,
        *,
        repository_id: str,
        application: str,
        git_url: str,
        application_id: str | None = None,
        default_branch: str = "main",
        gitlab_project_id: int | None = None,
        team: str = "",
        api_project_path: str = "",
    ) -> RepositoryRecord:
        rec = RepositoryRecord(
            repository_id=repository_id,
            application=application,
            application_id=application_id or repository_id,
            git_url=git_url,
            default_branch=default_branch,
            gitlab_project_id=gitlab_project_id,
            team=team,
            owner=team,
            shard_path=f"repos/{repository_id}",
            api_project_path=api_project_path,
            index_status="registered",
        )
        self.upsert(rec)
        self.save()
        return rec
