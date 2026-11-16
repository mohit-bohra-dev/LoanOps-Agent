"""EAKG non-graph artifact store (ADR-027) — Postgres product; file mirror under Postgres/."""

from __future__ import annotations

import asyncio
import concurrent.futures
import hashlib
import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Literal

import yaml  # type: ignore[import-untyped]

from packages.eakg.pipeline_layout import postgres_dir, resolve_file_shard_dir

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


def _loads_obj(raw: object) -> Any:
    if isinstance(raw, str):
        return json.loads(raw)
    return raw


class AbstractEakgArtifactStore(ABC):
    """Registry + interface + OpenAPI + ops + embeddings / proposals / engineering / GraphRAG."""

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

    @abstractmethod
    def put_embeddings(self, payload: dict[str, Any]) -> None: ...

    @abstractmethod
    def get_embeddings(self) -> dict[str, Any] | None: ...

    @abstractmethod
    def append_proposal(self, repository_id: str, row: dict[str, Any]) -> None: ...

    @abstractmethod
    def read_proposals(self, repository_id: str) -> list[dict[str, Any]]: ...

    @abstractmethod
    def append_decision(self, row: dict[str, Any]) -> None: ...

    @abstractmethod
    def read_decisions(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    def put_engineering(
        self, repository_id: str, artifact_name: str, payload: dict[str, Any]
    ) -> None: ...

    @abstractmethod
    def get_engineering(
        self, repository_id: str, artifact_name: str
    ) -> dict[str, Any] | None: ...

    @abstractmethod
    def put_graphrag(self, artifact_key: str, payload: Any) -> None: ...

    @abstractmethod
    def get_graphrag(self, artifact_key: str) -> Any | None: ...

    @abstractmethod
    def put_kv(self, key: str, payload: dict[str, Any]) -> None: ...

    @abstractmethod
    def get_kv(self, key: str) -> dict[str, Any] | None: ...

    @abstractmethod
    def put_sop_page(self, path: str, body: str) -> None: ...

    @abstractmethod
    def get_sop_page(self, path: str) -> str | None: ...

    @abstractmethod
    def put_pipeline_run(self, run_id: str, pipeline_id: str, payload: dict[str, Any]) -> None: ...

    @abstractmethod
    def get_pipeline_run(self, run_id: str) -> dict[str, Any] | None: ...

    @abstractmethod
    def list_pipeline_runs(
        self, pipeline_id: str | None = None, *, limit: int = 50
    ) -> list[dict[str, Any]]: ...

    @abstractmethod
    def put_asset_state(self, asset_key: str, payload: dict[str, Any]) -> None: ...

    @abstractmethod
    def get_asset_state(self, asset_key: str) -> dict[str, Any] | None: ...


class FileEakgArtifactStore(AbstractEakgArtifactStore):
    """Disk mirror under ``<root>/Postgres/…`` (tests / offline)."""

    def __init__(self, shard_dir: str | Path, *, registry_path: str | Path) -> None:
        self.root = Path(shard_dir)
        self.pg = postgres_dir(self.root)
        self.registry_path = Path(registry_path)

    @property
    def backend(self) -> Backend:
        return "file"

    def ensure_schema(self) -> None:
        self.pg.mkdir(parents=True, exist_ok=True)
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)

    def load_registry(self) -> list[dict[str, Any]]:
        path = self.pg / "registry.yaml"
        if not path.is_file():
            path = self.registry_path
        if not path.is_file():
            return []
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        repos = raw.get("repositories") or []
        return [r for r in repos if isinstance(r, dict) and r.get("repository_id")]

    def save_registry(self, repositories: list[dict[str, Any]]) -> None:
        self.ensure_schema()
        payload = {
            "repositories": sorted(repositories, key=lambda x: str(x.get("repository_id") or ""))
        }
        text = yaml.safe_dump(payload, sort_keys=False, allow_unicode=True)
        dest = self.pg / "registry.yaml"
        dest.write_text(text, encoding="utf-8")
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        self.registry_path.write_text(text, encoding="utf-8")

    def put_interface(self, repository_id: str, payload: dict[str, Any]) -> None:
        dest = self.pg / "interface" / f"{repository_id}.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def get_interface(self, repository_id: str) -> dict[str, Any] | None:
        path = self.pg / "interface" / f"{repository_id}.json"
        if not path.is_file():
            return None
        raw: object = json.loads(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else None

    def put_manifest(self, repository_id: str, payload: dict[str, Any]) -> None:
        dest = self.pg / "manifest" / f"{repository_id}.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def get_manifest(self, repository_id: str) -> dict[str, Any] | None:
        path = self.pg / "manifest" / f"{repository_id}.json"
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
        dest = self.pg / "openapi" / repository_id / f"{environment}.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        blob = {"pointer": pointer, "spec": spec}
        dest.write_text(json.dumps(blob, indent=2), encoding="utf-8")

    def get_openapi_pointer(
        self, repository_id: str, environment: str
    ) -> dict[str, Any] | None:
        path = self.pg / "openapi" / repository_id / f"{environment}.json"
        if not path.is_file():
            return None
        raw: object = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return None
        pointer = raw.get("pointer")
        return pointer if isinstance(pointer, dict) else None

    def get_openapi_spec(
        self, repository_id: str, environment: str
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        path = self.pg / "openapi" / repository_id / f"{environment}.json"
        if not path.is_file():
            return None, None
        raw: object = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return None, None
        pointer = raw.get("pointer")
        spec = raw.get("spec")
        return (
            spec if isinstance(spec, dict) else None,
            pointer if isinstance(pointer, dict) else None,
        )

    def put_operations(self, environment: str, payload: dict[str, Any]) -> None:
        dest = self.pg / "operations" / f"{environment}.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def get_operations(self, environment: str) -> dict[str, Any] | None:
        path = self.pg / "operations" / f"{environment}.json"
        if not path.is_file():
            return None
        raw: object = json.loads(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else None

    def put_embeddings(self, payload: dict[str, Any]) -> None:
        dest = self.pg / "embeddings.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def get_embeddings(self) -> dict[str, Any] | None:
        path = self.pg / "embeddings.json"
        if not path.is_file():
            return None
        raw: object = json.loads(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else None

    def append_proposal(self, repository_id: str, row: dict[str, Any]) -> None:
        path = self.pg / "proposals" / f"{repository_id}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")

    def read_proposals(self, repository_id: str) -> list[dict[str, Any]]:
        path = self.pg / "proposals" / f"{repository_id}.jsonl"
        if not path.is_file():
            return []
        out: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                out.append(json.loads(line))
        return out

    def append_decision(self, row: dict[str, Any]) -> None:
        path = self.pg / "decisions" / "decisions.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")

    def read_decisions(self) -> list[dict[str, Any]]:
        path = self.pg / "decisions" / "decisions.jsonl"
        if not path.is_file():
            return []
        out: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                out.append(json.loads(line))
        return out

    def put_engineering(
        self, repository_id: str, artifact_name: str, payload: dict[str, Any]
    ) -> None:
        dest = self.pg / "engineering" / repository_id / artifact_name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def get_engineering(
        self, repository_id: str, artifact_name: str
    ) -> dict[str, Any] | None:
        path = self.pg / "engineering" / repository_id / artifact_name
        if not path.is_file():
            return None
        raw: object = json.loads(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else None

    def put_graphrag(self, artifact_key: str, payload: Any) -> None:
        dest = self.pg / "graphrag" / f"{artifact_key}.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def get_graphrag(self, artifact_key: str) -> Any | None:
        path = self.pg / "graphrag" / f"{artifact_key}.json"
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def put_kv(self, key: str, payload: dict[str, Any]) -> None:
        safe = key.replace("/", "__")
        dest = self.pg / "kv" / f"{safe}.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def get_kv(self, key: str) -> dict[str, Any] | None:
        safe = key.replace("/", "__")
        path = self.pg / "kv" / f"{safe}.json"
        if not path.is_file():
            return None
        raw: object = json.loads(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else None

    def put_sop_page(self, path: str, body: str) -> None:
        dest = self.pg / "sop_page_cache" / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(body, encoding="utf-8")

    def get_sop_page(self, path: str) -> str | None:
        dest = self.pg / "sop_page_cache" / path
        if not dest.is_file():
            return None
        return dest.read_text(encoding="utf-8")

    def put_pipeline_run(self, run_id: str, pipeline_id: str, payload: dict[str, Any]) -> None:
        dest = self.pg / "pipeline_runs" / f"{run_id}.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        row = {"run_id": run_id, "pipeline_id": pipeline_id, **payload}
        dest.write_text(json.dumps(row, indent=2), encoding="utf-8")

    def get_pipeline_run(self, run_id: str) -> dict[str, Any] | None:
        path = self.pg / "pipeline_runs" / f"{run_id}.json"
        if not path.is_file():
            return None
        raw: object = json.loads(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else None

    def list_pipeline_runs(
        self, pipeline_id: str | None = None, *, limit: int = 50
    ) -> list[dict[str, Any]]:
        root = self.pg / "pipeline_runs"
        if not root.is_dir():
            return []
        rows: list[dict[str, Any]] = []
        for path in root.glob("*.json"):
            raw: object = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                continue
            if pipeline_id is not None and raw.get("pipeline_id") != pipeline_id:
                continue
            rows.append(raw)
        rows.sort(key=lambda r: str(r.get("started_at") or ""), reverse=True)
        return rows[: max(0, limit)]

    def put_asset_state(self, asset_key: str, payload: dict[str, Any]) -> None:
        safe = asset_key.replace("/", "__").replace(":", "__")
        dest = self.pg / "asset_state" / f"{safe}.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        row = {"asset_key": asset_key, **payload}
        dest.write_text(json.dumps(row, indent=2), encoding="utf-8")

    def get_asset_state(self, asset_key: str) -> dict[str, Any] | None:
        safe = asset_key.replace("/", "__").replace(":", "__")
        path = self.pg / "asset_state" / f"{safe}.json"
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
            # asyncpg execute() runs one statement; split the DDL file.
            for stmt in (s.strip() for s in _SCHEMA_SQL.split(";")):
                if stmt:
                    await conn.execute(stmt)
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
            payload = _loads_obj(row["payload"])
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
        _run_sync(self._put_repo_row("eakg_manifest", repository_id, payload))

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
            pointer = _loads_obj(row["pointer"])
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
            pointer = _loads_obj(row["pointer"])
            if not isinstance(pointer, dict):
                pointer = None
            payload = _loads_obj(row["payload"])
            if payload is not None and not isinstance(payload, dict):
                payload = None
            return payload, pointer
        finally:
            await conn.close()

    def put_operations(self, environment: str, payload: dict[str, Any]) -> None:
        _run_sync(self._put_env_row("eakg_operations", environment, payload))

    def get_operations(self, environment: str) -> dict[str, Any] | None:
        return _run_sync(self._get_json(
            "SELECT payload FROM eakg_operations WHERE environment = $1",
            environment,
        ))

    def put_embeddings(self, payload: dict[str, Any]) -> None:
        _run_sync(self._put_singleton("eakg_capability_embeddings", payload))

    def get_embeddings(self) -> dict[str, Any] | None:
        return _run_sync(self._get_json(
            "SELECT payload FROM eakg_capability_embeddings WHERE id = 1",
            "",
            singleton=True,
        ))

    def append_proposal(self, repository_id: str, row: dict[str, Any]) -> None:
        _run_sync(self._append_proposal(repository_id, row))

    async def _append_proposal(self, repository_id: str, row: dict[str, Any]) -> None:
        import asyncpg

        conn = await asyncpg.connect(self._dsn)
        try:
            await conn.execute(
                """
                INSERT INTO eakg_proposals (repository_id, payload, created_at)
                VALUES ($1, $2::jsonb, now())
                """,
                repository_id,
                json.dumps(row),
            )
        finally:
            await conn.close()

    def read_proposals(self, repository_id: str) -> list[dict[str, Any]]:
        return _run_sync(self._read_proposals(repository_id))

    async def _read_proposals(self, repository_id: str) -> list[dict[str, Any]]:
        import asyncpg

        conn = await asyncpg.connect(self._dsn)
        try:
            rows = await conn.fetch(
                """
                SELECT payload FROM eakg_proposals
                WHERE repository_id = $1
                ORDER BY seq
                """,
                repository_id,
            )
            out: list[dict[str, Any]] = []
            for row in rows:
                payload = _loads_obj(row["payload"])
                if isinstance(payload, dict):
                    out.append(payload)
            return out
        finally:
            await conn.close()

    def append_decision(self, row: dict[str, Any]) -> None:
        _run_sync(self._append_decision(row))

    async def _append_decision(self, row: dict[str, Any]) -> None:
        import asyncpg

        conn = await asyncpg.connect(self._dsn)
        try:
            await conn.execute(
                """
                INSERT INTO eakg_decisions (payload, created_at)
                VALUES ($1::jsonb, now())
                """,
                json.dumps(row),
            )
        finally:
            await conn.close()

    def read_decisions(self) -> list[dict[str, Any]]:
        return _run_sync(self._read_decisions())

    async def _read_decisions(self) -> list[dict[str, Any]]:
        import asyncpg

        conn = await asyncpg.connect(self._dsn)
        try:
            rows = await conn.fetch(
                "SELECT payload FROM eakg_decisions ORDER BY seq"
            )
            out: list[dict[str, Any]] = []
            for row in rows:
                payload = _loads_obj(row["payload"])
                if isinstance(payload, dict):
                    out.append(payload)
            return out
        finally:
            await conn.close()

    def put_engineering(
        self, repository_id: str, artifact_name: str, payload: dict[str, Any]
    ) -> None:
        _run_sync(self._put_engineering(repository_id, artifact_name, payload))

    async def _put_engineering(
        self, repository_id: str, artifact_name: str, payload: dict[str, Any]
    ) -> None:
        import asyncpg

        conn = await asyncpg.connect(self._dsn)
        try:
            await conn.execute(
                """
                INSERT INTO eakg_engineering
                    (repository_id, artifact_name, payload, updated_at)
                VALUES ($1, $2, $3::jsonb, now())
                ON CONFLICT (repository_id, artifact_name) DO UPDATE
                SET payload = EXCLUDED.payload, updated_at = now()
                """,
                repository_id,
                artifact_name,
                json.dumps(payload),
            )
        finally:
            await conn.close()

    def get_engineering(
        self, repository_id: str, artifact_name: str
    ) -> dict[str, Any] | None:
        return _run_sync(self._get_engineering(repository_id, artifact_name))

    async def _get_engineering(
        self, repository_id: str, artifact_name: str
    ) -> dict[str, Any] | None:
        import asyncpg

        conn = await asyncpg.connect(self._dsn)
        try:
            row = await conn.fetchrow(
                """
                SELECT payload FROM eakg_engineering
                WHERE repository_id = $1 AND artifact_name = $2
                """,
                repository_id,
                artifact_name,
            )
            if row is None:
                return None
            payload = _loads_obj(row["payload"])
            return payload if isinstance(payload, dict) else None
        finally:
            await conn.close()

    def put_graphrag(self, artifact_key: str, payload: Any) -> None:
        _run_sync(self._put_graphrag(artifact_key, payload))

    async def _put_graphrag(self, artifact_key: str, payload: Any) -> None:
        import asyncpg

        conn = await asyncpg.connect(self._dsn)
        try:
            await conn.execute(
                """
                INSERT INTO eakg_graphrag (artifact_key, payload, updated_at)
                VALUES ($1, $2::jsonb, now())
                ON CONFLICT (artifact_key) DO UPDATE
                SET payload = EXCLUDED.payload, updated_at = now()
                """,
                artifact_key,
                json.dumps(payload),
            )
        finally:
            await conn.close()

    def get_graphrag(self, artifact_key: str) -> Any | None:
        return _run_sync(self._get_graphrag(artifact_key))

    async def _get_graphrag(self, artifact_key: str) -> Any | None:
        import asyncpg

        conn = await asyncpg.connect(self._dsn)
        try:
            row = await conn.fetchrow(
                "SELECT payload FROM eakg_graphrag WHERE artifact_key = $1",
                artifact_key,
            )
            if row is None:
                return None
            return _loads_obj(row["payload"])
        finally:
            await conn.close()

    def put_kv(self, key: str, payload: dict[str, Any]) -> None:
        _run_sync(self._put_kv_row(key, payload))

    def get_kv(self, key: str) -> dict[str, Any] | None:
        return _run_sync(self._get_json(
            "SELECT payload FROM eakg_kv WHERE key = $1",
            key,
        ))

    def put_sop_page(self, path: str, body: str) -> None:
        _run_sync(self._put_sop_page(path, body))

    async def _put_sop_page(self, path: str, body: str) -> None:
        import asyncpg

        conn = await asyncpg.connect(self._dsn)
        try:
            await conn.execute(
                """
                INSERT INTO sop_page_cache (path, body, updated_at)
                VALUES ($1, $2, now())
                ON CONFLICT (path) DO UPDATE
                SET body = EXCLUDED.body, updated_at = now()
                """,
                path,
                body,
            )
        finally:
            await conn.close()

    def get_sop_page(self, path: str) -> str | None:
        return _run_sync(self._get_sop_page(path))

    async def _get_sop_page(self, path: str) -> str | None:
        import asyncpg

        conn = await asyncpg.connect(self._dsn)
        try:
            row = await conn.fetchrow(
                "SELECT body FROM sop_page_cache WHERE path = $1",
                path,
            )
            if row is None:
                return None
            return str(row["body"])
        finally:
            await conn.close()

    def put_pipeline_run(self, run_id: str, pipeline_id: str, payload: dict[str, Any]) -> None:
        _run_sync(self._put_pipeline_run(run_id, pipeline_id, payload))

    async def _put_pipeline_run(
        self, run_id: str, pipeline_id: str, payload: dict[str, Any]
    ) -> None:
        import asyncpg

        conn = await asyncpg.connect(self._dsn)
        try:
            await conn.execute(
                """
                INSERT INTO eakg_pipeline_runs (run_id, pipeline_id, payload, started_at, updated_at)
                VALUES ($1, $2, $3::jsonb, COALESCE(($3::jsonb->>'started_at')::timestamptz, now()), now())
                ON CONFLICT (run_id) DO UPDATE
                SET pipeline_id = EXCLUDED.pipeline_id,
                    payload = EXCLUDED.payload,
                    updated_at = now()
                """,
                run_id,
                pipeline_id,
                json.dumps({"run_id": run_id, "pipeline_id": pipeline_id, **payload}),
            )
        finally:
            await conn.close()

    def get_pipeline_run(self, run_id: str) -> dict[str, Any] | None:
        return _run_sync(self._get_pipeline_run(run_id))

    async def _get_pipeline_run(self, run_id: str) -> dict[str, Any] | None:
        import asyncpg

        conn = await asyncpg.connect(self._dsn)
        try:
            row = await conn.fetchrow(
                "SELECT payload FROM eakg_pipeline_runs WHERE run_id = $1",
                run_id,
            )
            if row is None:
                return None
            payload = _loads_obj(row["payload"])
            return payload if isinstance(payload, dict) else None
        finally:
            await conn.close()

    def list_pipeline_runs(
        self, pipeline_id: str | None = None, *, limit: int = 50
    ) -> list[dict[str, Any]]:
        return _run_sync(self._list_pipeline_runs(pipeline_id, limit=limit))

    async def _list_pipeline_runs(
        self, pipeline_id: str | None, *, limit: int
    ) -> list[dict[str, Any]]:
        import asyncpg

        conn = await asyncpg.connect(self._dsn)
        try:
            if pipeline_id is None:
                rows = await conn.fetch(
                    """
                    SELECT payload FROM eakg_pipeline_runs
                    ORDER BY started_at DESC
                    LIMIT $1
                    """,
                    max(0, limit),
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT payload FROM eakg_pipeline_runs
                    WHERE pipeline_id = $1
                    ORDER BY started_at DESC
                    LIMIT $2
                    """,
                    pipeline_id,
                    max(0, limit),
                )
            out: list[dict[str, Any]] = []
            for row in rows:
                payload = _loads_obj(row["payload"])
                if isinstance(payload, dict):
                    out.append(payload)
            return out
        finally:
            await conn.close()

    def put_asset_state(self, asset_key: str, payload: dict[str, Any]) -> None:
        _run_sync(self._put_asset_state(asset_key, payload))

    async def _put_asset_state(self, asset_key: str, payload: dict[str, Any]) -> None:
        import asyncpg

        conn = await asyncpg.connect(self._dsn)
        try:
            await conn.execute(
                """
                INSERT INTO eakg_asset_state (asset_key, payload, updated_at)
                VALUES ($1, $2::jsonb, now())
                ON CONFLICT (asset_key) DO UPDATE
                SET payload = EXCLUDED.payload, updated_at = now()
                """,
                asset_key,
                json.dumps({"asset_key": asset_key, **payload}),
            )
        finally:
            await conn.close()

    def get_asset_state(self, asset_key: str) -> dict[str, Any] | None:
        return _run_sync(self._get_asset_state(asset_key))

    async def _get_asset_state(self, asset_key: str) -> dict[str, Any] | None:
        import asyncpg

        conn = await asyncpg.connect(self._dsn)
        try:
            row = await conn.fetchrow(
                "SELECT payload FROM eakg_asset_state WHERE asset_key = $1",
                asset_key,
            )
            if row is None:
                return None
            payload = _loads_obj(row["payload"])
            return payload if isinstance(payload, dict) else None
        finally:
            await conn.close()

    async def _put_singleton(self, table: str, payload: dict[str, Any]) -> None:
        import asyncpg

        conn = await asyncpg.connect(self._dsn)
        try:
            await conn.execute(
                f"""
                INSERT INTO {table} (id, payload, updated_at)
                VALUES (1, $1::jsonb, now())
                ON CONFLICT (id) DO UPDATE
                SET payload = EXCLUDED.payload, updated_at = now()
                """,
                json.dumps(payload),
            )
        finally:
            await conn.close()

    async def _put_repo_row(
        self, table: str, repository_id: str, payload: dict[str, Any]
    ) -> None:
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

    async def _put_env_row(
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

    async def _put_kv_row(self, key: str, payload: dict[str, Any]) -> None:
        import asyncpg

        conn = await asyncpg.connect(self._dsn)
        try:
            await conn.execute(
                """
                INSERT INTO eakg_kv (key, payload, updated_at)
                VALUES ($1, $2::jsonb, now())
                ON CONFLICT (key) DO UPDATE
                SET payload = EXCLUDED.payload, updated_at = now()
                """,
                key,
                json.dumps(payload),
            )
        finally:
            await conn.close()

    async def _get_json(
        self, sql: str, key: str, *, singleton: bool = False
    ) -> dict[str, Any] | None:
        import asyncpg

        conn = await asyncpg.connect(self._dsn)
        try:
            row = await conn.fetchrow(sql) if singleton else await conn.fetchrow(sql, key)
            if row is None:
                return None
            payload = _loads_obj(row["payload"])
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
    shard = resolve_file_shard_dir(cfg.eakg_store.file_shard_dir)
    return FileEakgArtifactStore(shard, registry_path=cfg.eakg.registry_path)
