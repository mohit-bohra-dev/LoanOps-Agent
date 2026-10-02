"""Repository Registry — data-driven onboarding entry (ADR-016)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml
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


@dataclass
class RepositoryRecord:
    repository_id: str
    application: str
    application_id: str
    git_url: str
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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

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
            git_url=str(raw["git_url"]),
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
        )


class RepositoryRegistry:
    """Load / save repositories.yaml. Never hard-code pilot IDs in detectors."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._records: dict[str, RepositoryRecord] = {}
        if self.path.is_file():
            self.reload()

    def reload(self) -> None:
        raw = yaml.safe_load(self.path.read_text(encoding="utf-8")) or {}
        repos = raw.get("repositories") or []
        self._records = {
            r["repository_id"]: RepositoryRecord.from_dict(r)
            for r in repos
            if isinstance(r, dict) and r.get("repository_id")
        }

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "repositories": [r.to_dict() for r in sorted(self._records.values(), key=lambda x: x.repository_id)]
        }
        self.path.write_text(
            yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )

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
