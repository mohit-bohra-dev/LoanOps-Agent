"""EAKG non-graph artifact store (ADR-027) — file or Postgres."""

from __future__ import annotations

import asyncio
import concurrent.futures
import hashlib
import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Literal

import yaml  # type: ignore[import-untyped]

Backend = Literal["file", "postgres"]


def _run_sync(coro: Any) -> Any:
    """Run an async coroutine from sync code (sync Registry / ShardStore)."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


def normalize_asyncpg_dsn(dsn: str) -> str:
    """Strip SQLAlchemy ``+asyncpg`` dialect marker for asyncpg.connect."""
    text = dsn.strip()
    if text.startswith("postgresql+asyncpg://"):
        return "postgresql://" + text.removeprefix("postgresql+asyncpg://")
    if text.startswith("postgres+asyncpg://"):
        return "postgres://" + text.removeprefix("postgres+asyncpg://")
    return text


def content_hash_payload(payload: Any) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


class AbstractEakgArtifactStore(ABC):
    """Registry + interface + OpenAPI + manifest + operations catalog."""

    @property
    @abstractmethod
    def backend(self) -> Backend: ...

    @abstractmethod
    def ensure_schema(self) -> None: ...

    @abstractmethod
    def load_registry(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    def save_registry(self, repositories: list[dict[str, Any]]) -> None: ...

    @abstractmethod
    def put_interface(self, repository_id: str, payload: dict[str, Any]) -> None: ...

    @abstractmethod
    def get_interface(self, repository_id: str) -> dict[str, Any] | None: ...

    @abstractmethod
    def put_manifest(self, repository_id: str, payload: dict[str, Any]) -> None: ...

    @abstractmethod
    def get_manifest(self, repository_id: str) -> dict[str, Any] | None: ...

    @abstractmethod
    def put_openapi(
        self,
        repository_id: str,
        environment: str,
        *,
        pointer: dict[str, Any],
        spec: dict[str, Any] | None,
    ) -> None: ...

    @abstractmethod
    def get_openapi_pointer(
        self, repository_id: str, environment: str
    ) -> dict[str, Any] | None: ...

    @abstractmethod
    def get_openapi_spec(
        self, repository_id: str, environment: str
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]: ...

    @abstractmethod
    def put_operations(self, environment: str, payload: dict[str, Any]) -> None: ...

    @abstractmethod
    def get_operations(self, environment: str) -> dict[str, Any] | None: ...


class FileEakgArtifactStore(AbstractEakgArtifactStore):
    """Disk layout under shard_dir (tests / offline)."""

    def __init__(self, shard_dir: str | Path, *, registry_path: str | Path) -> None:
        self.root = Path(shard_dir)
        self.registry_path = Path(registry_path)

    @property
    def backend(self) -> Backend:
        return "file"

    def ensure_schema(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)

    def load_registry(self) -> list[dict[str, Any]]:
        if not self.registry_path.is_file():
            return []
        raw = yaml.safe_load(self.registry_path.read_text(encoding="utf-8")) or {}
        repos = raw.get("repositories") or []
        return [r for r in repos if isinstance(r, dict) and r.get("repository_id")]

    def save_registry(self, repositories: list[dict[str, Any]]) -> None:
        self.ensure_schema()
        payload = {
            "repositories": sorted(repositories, key=lambda x: str(x.get("repository_id") or ""))
        }
        self.registry_path.write_text(
            yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )

    def _repo_dir(self, repository_id: str) -> Path:
        return self.root / "repos" / repository_id

    def put_interface(self, repository_id: str, payload: dict[str, Any]) -> None:
        dest = self._repo_dir(repository_id) / "interface.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def get_interface(self, repository_id: str) -> dict[str, Any] | None:
        path = self._repo_dir(repository_id) / "interface.json"
        if not path.is_file():
            return None
        raw: object = json.loads(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else None

    def put_manifest(self, repository_id: str, payload: dict[str, Any]) -> None:
        dest = self._repo_dir(repository_id) / "manifest.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def get_manifest(self, repository_id: str) -> dict[str, Any] | None:
        path = self._repo_dir(repository_id) / "manifest.json"
        if not path.is_file():
            return None
        raw: object = json.loads(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else None

    def put_openapi(
        self,
        repository_id: str,
        environment: str,
        *,
        pointer: dict[str, Any],
        spec: dict[str, Any] | None,
    ) -> None:
        env_dir = self._repo_dir(repository_id) / "openapi" / environment
        env_dir.mkdir(parents=True, exist_ok=True)
        (env_dir / "current.json").write_text(
            json.dumps(pointer, indent=2), encoding="utf-8"
        )
        if spec is not None:
            spec_hash = str(pointer.get("spec_hash") or content_hash_payload(spec))
            (env_dir / f"{spec_hash}.json").write_text(
                json.dumps(spec, indent=2), encoding="utf-8"
            )

    def get_openapi_pointer(
        self, repository_id: str, environment: str
    ) -> dict[str, Any] | None:
        path = self._repo_dir(repository_id) / "openapi" / environment / "current.json"
        if not path.is_file():
            return None
        raw: object = json.loads(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else None

    def get_openapi_spec(
        self, repository_id: str, environment: str
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        pointer = self.get_openapi_pointer(repository_id, environment)
        if pointer is None:
            return None, None
        spec_hash = str(pointer.get("spec_hash") or "")
        if not spec_hash:
            return None, pointer
        path = self._repo_dir(repository_id) / "openapi" / environment / f"{spec_hash}.json"
        if not path.is_file():
            return None, pointer
        raw: object = json.loads(path.read_text(encoding="utf-8"))
        return (raw if isinstance(raw, dict) else None), pointer

    def put_operations(self, environment: str, payload: dict[str, Any]) -> None:
        dest = self.root / "enterprise" / "api_index" / environment / "operations.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def get_operations(self, environment: str) -> dict[str, Any] | None:
        path = self.root / "enterprise" / "api_index" / environment / "operations.json"
        if not path.is_file():
            return None
        raw: object = json.loads(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else None


_SCHEMA_SQL = (Path(__file__).parent / "sql" / "eakg_artifacts.sql").read_text(encoding="utf-8")


class PostgresEakgArtifactStore(AbstractEakgArtifactStore):
    """Postgres JSONB store (product)."""

    def __init__(self, dsn: str) -> None:
        self._dsn = normalize_asyncpg_dsn(dsn)

    @property
    def backend(self) -> Backend:
        return "postgres"

    def ensure_schema(self) -> None:
        _run_sync(self._ensure_schema())

    async def _ensure_schema(self) -> None:
        import asyncpg

        conn = await asyncpg.connect(self._dsn)
        try:
            await conn.execute(_SCHEMA_SQL)
        finally:
            await conn.close()

    def load_registry(self) -> list[dict[str, Any]]:
        return _run_sync(self._load_registry())

    async def _load_registry(self) -> list[dict[str, Any]]:
        import asyncpg

        conn = await asyncpg.connect(self._dsn)
        try:
            row = await conn.fetchrow("SELECT payload FROM eakg_registry WHERE id = 1")
            if row is None:
                return []
            payload = row["payload"]
            if isinstance(payload, str):
                payload = json.loads(payload)
            repos = payload.get("repositories") if isinstance(payload, dict) else None
            if not isinstance(repos, list):
                return []
            return [r for r in repos if isinstance(r, dict) and r.get("repository_id")]
        finally:
            await conn.close()

    def save_registry(self, repositories: list[dict[str, Any]]) -> None:
        _run_sync(self._save_registry(repositories))

    async def _save_registry(self, repositories: list[dict[str, Any]]) -> None:
        import asyncpg

        payload = {
            "repositories": sorted(
                repositories, key=lambda x: str(x.get("repository_id") or "")
            )
        }
        conn = await asyncpg.connect(self._dsn)
        try:
            await conn.execute(
                """
                INSERT INTO eakg_registry (id, payload, updated_at)
                VALUES (1, $1::jsonb, now())
                ON CONFLICT (id) DO UPDATE
                SET payload = EXCLUDED.payload, updated_at = now()
                """,
                json.dumps(payload),
            )
        finally:
            await conn.close()

    def put_interface(self, repository_id: str, payload: dict[str, Any]) -> None:
        _run_sync(self._put_interface(repository_id, payload))

    async def _put_interface(self, repository_id: str, payload: dict[str, Any]) -> None:
        import asyncpg

        commit = str(payload.get("commit_sha") or "")
        chash = content_hash_payload(payload)
        conn = await asyncpg.connect(self._dsn)
        try:
            await conn.execute(
                """
                INSERT INTO eakg_interface
                    (repository_id, commit_sha, content_hash, payload, updated_at)
                VALUES ($1, $2, $3, $4::jsonb, now())
                ON CONFLICT (repository_id) DO UPDATE
                SET commit_sha = EXCLUDED.commit_sha,
                    content_hash = EXCLUDED.content_hash,
                    payload = EXCLUDED.payload,
                    updated_at = now()
                """,
                repository_id,
                commit,
                chash,
                json.dumps(payload),
            )
        finally:
            await conn.close()

    def get_interface(self, repository_id: str) -> dict[str, Any] | None:
        return _run_sync(self._get_json(
            "SELECT payload FROM eakg_interface WHERE repository_id = $1",
            repository_id,
        ))

    def put_manifest(self, repository_id: str, payload: dict[str, Any]) -> None:
        _run_sync(self._put_kv("eakg_manifest", repository_id, payload))

    def get_manifest(self, repository_id: str) -> dict[str, Any] | None:
        return _run_sync(self._get_json(
            "SELECT payload FROM eakg_manifest WHERE repository_id = $1",
            repository_id,
        ))

    def put_openapi(
        self,
        repository_id: str,
        environment: str,
        *,
        pointer: dict[str, Any],
        spec: dict[str, Any] | None,
    ) -> None:
        _run_sync(self._put_openapi(repository_id, environment, pointer, spec))

    async def _put_openapi(
        self,
        repository_id: str,
        environment: str,
        pointer: dict[str, Any],
        spec: dict[str, Any] | None,
    ) -> None:
        import asyncpg

        spec_hash = str(pointer.get("spec_hash") or "")
        source_url = str(pointer.get("source_url") or "")
        conn = await asyncpg.connect(self._dsn)
        try:
            await conn.execute(
                """
                INSERT INTO eakg_openapi
                    (repository_id, environment, spec_hash, source_url, pointer, payload, updated_at)
                VALUES ($1, $2, $3, $4, $5::jsonb, $6::jsonb, now())
                ON CONFLICT (repository_id, environment) DO UPDATE
                SET spec_hash = EXCLUDED.spec_hash,
                    source_url = EXCLUDED.source_url,
                    pointer = EXCLUDED.pointer,
                    payload = COALESCE(EXCLUDED.payload, eakg_openapi.payload),
                    updated_at = now()
                """,
                repository_id,
                environment,
                spec_hash,
                source_url,
                json.dumps(pointer),
                json.dumps(spec) if spec is not None else None,
            )
        finally:
            await conn.close()

    def get_openapi_pointer(
        self, repository_id: str, environment: str
    ) -> dict[str, Any] | None:
        return _run_sync(self._get_openapi_pointer(repository_id, environment))

    async def _get_openapi_pointer(
        self, repository_id: str, environment: str
    ) -> dict[str, Any] | None:
        import asyncpg

        conn = await asyncpg.connect(self._dsn)
        try:
            row = await conn.fetchrow(
                """
                SELECT pointer FROM eakg_openapi
                WHERE repository_id = $1 AND environment = $2
                """,
                repository_id,
                environment,
            )
            if row is None:
                return None
            pointer = row["pointer"]
            if isinstance(pointer, str):
                pointer = json.loads(pointer)
            return pointer if isinstance(pointer, dict) else None
        finally:
            await conn.close()

    def get_openapi_spec(
        self, repository_id: str, environment: str
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        return _run_sync(self._get_openapi_spec(repository_id, environment))

    async def _get_openapi_spec(
        self, repository_id: str, environment: str
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        import asyncpg

        conn = await asyncpg.connect(self._dsn)
        try:
            row = await conn.fetchrow(
                """
                SELECT pointer, payload FROM eakg_openapi
                WHERE repository_id = $1 AND environment = $2
                """,
                repository_id,
                environment,
            )
            if row is None:
                return None, None
            pointer = row["pointer"]
            if isinstance(pointer, str):
                pointer = json.loads(pointer)
            if not isinstance(pointer, dict):
                pointer = None
            payload = row["payload"]
            if isinstance(payload, str):
                payload = json.loads(payload)
            if payload is not None and not isinstance(payload, dict):
                payload = None
            return payload, pointer
        finally:
            await conn.close()

    def put_operations(self, environment: str, payload: dict[str, Any]) -> None:
        _run_sync(self._put_kv_env("eakg_operations", environment, payload))

    def get_operations(self, environment: str) -> dict[str, Any] | None:
        return _run_sync(self._get_json(
            "SELECT payload FROM eakg_operations WHERE environment = $1",
            environment,
        ))

    async def _put_kv(self, table: str, repository_id: str, payload: dict[str, Any]) -> None:
        import asyncpg

        conn = await asyncpg.connect(self._dsn)
        try:
            await conn.execute(
                f"""
                INSERT INTO {table} (repository_id, payload, updated_at)
                VALUES ($1, $2::jsonb, now())
                ON CONFLICT (repository_id) DO UPDATE
                SET payload = EXCLUDED.payload, updated_at = now()
                """,
                repository_id,
                json.dumps(payload),
            )
        finally:
            await conn.close()

    async def _put_kv_env(
        self, table: str, environment: str, payload: dict[str, Any]
    ) -> None:
        import asyncpg

        conn = await asyncpg.connect(self._dsn)
        try:
            await conn.execute(
                f"""
                INSERT INTO {table} (environment, payload, updated_at)
                VALUES ($1, $2::jsonb, now())
                ON CONFLICT (environment) DO UPDATE
                SET payload = EXCLUDED.payload, updated_at = now()
                """,
                environment,
                json.dumps(payload),
            )
        finally:
            await conn.close()

    async def _get_json(self, sql: str, key: str) -> dict[str, Any] | None:
        import asyncpg

        conn = await asyncpg.connect(self._dsn)
        try:
            row = await conn.fetchrow(sql, key)
            if row is None:
                return None
            payload = row["payload"]
            if isinstance(payload, str):
                payload = json.loads(payload)
            return payload if isinstance(payload, dict) else None
        finally:
            await conn.close()


def resolve_eakg_store_dsn(settings: Any) -> str:
    """Pick DSN: EAKG_STORE__DSN or VECTOR_STORE__PGVECTOR_DSN."""
    raw = str(getattr(settings.eakg_store, "dsn", "") or "").strip()
    if raw:
        return normalize_asyncpg_dsn(raw)
    return normalize_asyncpg_dsn(str(settings.vector_store.pgvector_dsn))


def get_eakg_artifact_store(settings: Any | None = None) -> AbstractEakgArtifactStore:
    """Factory (settings-driven). Not lru_cache — tests mutate env often."""
    from packages.common.settings import Settings, get_settings

    cfg = settings or get_settings()
    assert isinstance(cfg, Settings)
    backend = cfg.eakg_store.backend
    if backend == "postgres":
        store: AbstractEakgArtifactStore = PostgresEakgArtifactStore(resolve_eakg_store_dsn(cfg))
        store.ensure_schema()
        return store
    shard = cfg.eakg_store.file_shard_dir.strip() or cfg.eakg.shard_dir
    return FileEakgArtifactStore(shard, registry_path=cfg.eakg.registry_path)
