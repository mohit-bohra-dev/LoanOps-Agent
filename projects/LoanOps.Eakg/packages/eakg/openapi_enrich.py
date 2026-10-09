"""Hybrid OpenAPI enrichment — static graph authoritative; live optional."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

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


def _same_origin(left: str, right: str) -> bool:
    a, b = urlparse(left), urlparse(right)
    return (a.scheme, a.netloc) == (b.scheme, b.netloc) and bool(a.netloc)


async def fetch_spec_with_source(
    base_url: str,
    token: str = "",
    *,
    paths: tuple[str, ...] | list[str] = SPEC_CANDIDATES,
    timeout: float = 20.0,
    transport: httpx.AsyncBaseTransport | None = None,
) -> tuple[dict[str, Any] | None, str | None, str | None]:
    """GET a spec. Follow at most 3 redirects, and only on the same origin."""
    headers: dict[str, str] = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    candidates = tuple(p for p in paths if p) or SPEC_CANDIDATES
    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=False,
        headers=headers,
        transport=transport,
    ) as client:
        for path in candidates:
            url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
            for _hop in range(4):
                try:
                    resp = await client.get(url)
                except httpx.HTTPError as exc:
                    return None, url, str(exc)
                if resp.status_code in {301, 302, 303, 307, 308}:
                    loc = resp.headers.get("location") or ""
                    nxt = urljoin(url, loc)
                    if not loc or not _same_origin(base_url, nxt):
                        return None, url, f"redirect left origin: {nxt}"
                    url = nxt
                    continue
                if resp.status_code != 200:
                    break
                try:
                    data = resp.json()
                except json.JSONDecodeError:
                    break
                if isinstance(data, dict) and ("paths" in data or "openapi" in data or "swagger" in data):
                    return data, url, None
                break
    return None, None, "no OpenAPI document at candidate paths"


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
    spec: dict[str, Any] | None = None,
) -> RepoInterface:
    from packages.eakg.graph_build import enrich_operations_from_openapi

    if mode == "static":
        return iface

    if spec is not None:
        store.write_openapi_cache(iface.repository_id, iface.commit_sha, spec)
        return enrich_operations_from_openapi(iface, spec)

    cached = store.read_openapi_cache(iface.repository_id, iface.commit_sha)
    if cached:
        return enrich_operations_from_openapi(iface, cached)

    if fixture_path:
        spec = load_fixture_spec(fixture_path)
    if spec is None and mode in {"hybrid", "live"} and base_url:
        spec = await fetch_spec(base_url, token=token)
    if spec is None:
        return iface

    store.write_openapi_cache(iface.repository_id, iface.commit_sha, spec)
    return enrich_operations_from_openapi(iface, spec)
