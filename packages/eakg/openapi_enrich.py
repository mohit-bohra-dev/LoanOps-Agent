"""Hybrid OpenAPI enrichment — static graph authoritative; live optional."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx

from packages.eakg.models import RepoInterface
from packages.eakg.store import ShardStore

# Candidate swagger paths (Fees returned 404 on /swagger/v1/swagger.json)
SPEC_CANDIDATES = (
    "/swagger/v1/swagger.json",
    "/swagger/v1.0/swagger.json",
    "/swagger/docs/v1",
    "/openapi/v1.json",
    "/swagger/FF/swagger.json",
)


async def fetch_spec(
    base_url: str,
    *,
    token: str = "",
    timeout: float = 20.0,
) -> dict[str, Any] | None:
    headers: dict[str, str] = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        for path in SPEC_CANDIDATES:
            url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
            try:
                resp = await client.get(url, headers=headers)
            except httpx.HTTPError:
                continue
            if resp.status_code != 200:
                continue
            try:
                data = resp.json()
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict) and ("paths" in data or "openapi" in data or "swagger" in data):
                return data
    return None


def load_fixture_spec(path: str | Path) -> dict[str, Any] | None:
    p = Path(path)
    if not p.is_file():
        return None
    data = json.loads(p.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else None


async def enrich_interface(
    iface: RepoInterface,
    store: ShardStore,
    *,
    mode: str,
    base_url: str = "",
    token: str = "",
    fixture_path: str = "",
) -> RepoInterface:
    from packages.eakg.graph_build import enrich_operations_from_openapi

    if mode == "static":
        return iface

    cached = store.read_openapi_cache(iface.repository_id, iface.commit_sha)
    if cached:
        return enrich_operations_from_openapi(iface, cached)

    spec: dict[str, Any] | None = None
    if fixture_path:
        spec = load_fixture_spec(fixture_path)
    if spec is None and mode in {"hybrid", "live"} and base_url:
        spec = await fetch_spec(base_url, token=token)
    if spec is None:
        return iface

    store.write_openapi_cache(iface.repository_id, iface.commit_sha, spec)
    return enrich_operations_from_openapi(iface, spec)
