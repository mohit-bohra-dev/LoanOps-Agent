"""Per-app OpenAPI cache. Runtime reads these files; it does not fetch swagger."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from packages.eakg.openapi_enrich import fetch_spec_with_source, load_fixture_spec
from packages.eakg.registry import RepositoryRecord, RepositoryRegistry
from packages.eakg.store import ShardStore

SPEC_HTTP_TIMEOUT_S = 20.0
SPEC_APP_BUDGET_S = 30.0
TokenSource = Callable[[str, str], Awaitable[str]]


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _env_dir(store: ShardStore, repository_id: str, environment: str) -> Path:
    return store.repo_dir(repository_id) / "openapi" / environment


def pointer_path(store: ShardStore, repository_id: str, environment: str) -> Path:
    return _env_dir(store, repository_id, environment) / "current.json"


def _canonical(doc: dict[str, Any]) -> str:
    return json.dumps(doc, sort_keys=True, separators=(",", ":"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(path)


def read_pointer(store: ShardStore, repository_id: str, environment: str) -> dict[str, Any] | None:
    path = pointer_path(store, repository_id, environment)
    if not path.is_file():
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    return raw if isinstance(raw, dict) else None


def read_current_spec(
    store: ShardStore,
    repository_id: str,
    environment: str,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    pointer = read_pointer(store, repository_id, environment)
    if pointer is None:
        return None, None
    spec_hash = str(pointer.get("spec_hash") or "")
    if not spec_hash:
        return None, pointer
    path = _env_dir(store, repository_id, environment) / f"{spec_hash}.json"
    if not path.is_file():
        return None, pointer
    raw = json.loads(path.read_text(encoding="utf-8"))
    return (raw if isinstance(raw, dict) else None), pointer


def _prune(directory: Path, keep: str) -> None:
    files = sorted(directory.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    hashed = [p for p in files if p.name != "current.json"]
    for old in hashed[3:]:
        if old.stem != keep:
            old.unlink(missing_ok=True)


async def refresh_spec(
    record: RepositoryRecord,
    environment: str,
    store: ShardStore,
    token_source: TokenSource,
    *,
    transport: Any | None = None,
) -> dict[str, Any]:
    target = record.environments.get(environment)
    previous = read_pointer(store, record.repository_id, environment) or {}
    if target is None or not target.enabled:
        pointer = {
            **previous,
            "environment": environment,
            "status": "failed",
            "last_error": "not_registered_in_env",
            "last_attempt_at": _now(),
        }
        _write_json(pointer_path(store, record.repository_id, environment), pointer)
        return pointer

    doc: dict[str, Any] | None = None
    url: str | None = None
    err: str | None = None
    credential: str | None = None
    if target.spec_fixture:
        doc = load_fixture_spec(target.spec_fixture)
        url = target.spec_fixture
        if doc is None:
            err = f"fixture missing: {target.spec_fixture}"
        credential = "configured"
    else:
        token = await token_source(record.application_id, target.auth_audience)
        credential = "configured" if token else "missing"
        paths = (target.spec_path,) if target.spec_path else ()
        doc, url, err = await fetch_spec_with_source(
            target.base_url,
            token,
            paths=paths,
            timeout=SPEC_HTTP_TIMEOUT_S,
            transport=transport,
        )

    directory = _env_dir(store, record.repository_id, environment)
    if isinstance(doc, dict) and ("paths" in doc or "openapi" in doc or "swagger" in doc):
        digest = hashlib.sha256(_canonical(doc).encode("utf-8")).hexdigest()[:12]
        _write_json(directory / f"{digest}.json", doc)
        _prune(directory, digest)
        paths_obj = doc.get("paths")
        count = len(paths_obj) if isinstance(paths_obj, dict) else 0
        pointer = {
            "environment": environment,
            "spec_hash": digest,
            "source_url": url,
            "fetched_at": _now(),
            "last_attempt_at": _now(),
            "status": "ok",
            "last_error": None,
            "operation_count": count,
            "changed": digest != previous.get("spec_hash"),
            "credential": credential,
        }
    else:
        pointer = {
            **{k: v for k, v in previous.items() if k != "changed"},
            "environment": environment,
            "status": "failed",
            "last_error": (err or "invalid spec")[:300],
            "last_attempt_at": _now(),
            "credential": credential,
        }
    _write_json(pointer_path(store, record.repository_id, environment), pointer)
    return pointer


async def refresh_all(
    registry: RepositoryRegistry,
    environment: str,
    store: ShardStore,
    token_source: TokenSource,
) -> dict[str, dict[str, Any]]:
    import asyncio

    sem = asyncio.Semaphore(8)
    results: dict[str, dict[str, Any]] = {}

    async def _one(record: RepositoryRecord) -> None:
        async with sem:
            try:
                results[record.repository_id] = await asyncio.wait_for(
                    refresh_spec(record, environment, store, token_source),
                    timeout=SPEC_APP_BUDGET_S,
                )
            except Exception as exc:  # noqa: BLE001 — one app must not fail the rest
                results[record.repository_id] = {
                    "environment": environment,
                    "status": "failed",
                    "last_error": str(exc)[:300],
                }

    await asyncio.gather(*(_one(rec) for rec in registry.list_active(environment)))
    return results
