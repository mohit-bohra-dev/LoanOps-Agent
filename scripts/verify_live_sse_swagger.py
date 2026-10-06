"""Fetch live SSE swagger (no fixture file) and sanity-check parse + GET invoke.

Does not print tokens or response bodies (PII). Requires SSE__API_KEY in .env.

  uv run python scripts/verify_live_sse_swagger.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import httpx

from packages.common.settings import Settings
from packages.sse.invoke import invoke_sse_api
from packages.sse.loader import DEFAULT_SWAGGER_LINKS, OpenApiCatalogService

_HAND_CATALOG = _ROOT / "data" / "sse-loanservices-catalog.json"
_DUMP_DIR = _ROOT / "data" / "sse-live"
_DEMO_LOAN_ID = "1000002245"
_SUMMARY_HINTS = ("getloansummary", "loans_getsummary", "summary")


def _links(cfg: Settings) -> list[dict[str, str]]:
    if cfg.sse.swagger_links:
        return [
            {"id": link.id, "label": link.label, "url": link.url} for link in cfg.sse.swagger_links
        ]
    if cfg.sse.swagger_urls:
        from urllib.parse import urlparse

        out: list[dict[str, str]] = []
        for i, u in enumerate(cfg.sse.swagger_urls):
            host = urlparse(u).hostname or f"app-{i}"
            slug = host.split(".")[0].replace("-", "_")
            out.append({"id": slug, "label": host, "url": u})
        return out
    return list(DEFAULT_SWAGGER_LINKS)


def _path_norm(path: str) -> str:
    import re

    return re.sub(r"\{[^}]+\}", "{}", path).lower()


async def main() -> int:
    cfg = Settings()
    if not cfg.sse.api_key:
        print("FAIL: SSE__API_KEY empty")
        return 1

    links = _links(cfg)
    print(f"base={cfg.sse.api_base_url}")
    print(f"use_fixture={cfg.sse.use_fixture} fixture_path={cfg.sse.fixture_path or '(empty)'}")
    print("NOTE: this script ignores fixture_path (force HTTP swagger).")
    for link in links:
        print(f"link {link['id']}: {link['url']}")

    svc = OpenApiCatalogService(
        swagger_links=links,
        api_base_url=cfg.sse.api_base_url,
        bearer_token=cfg.sse.api_key,
        fixture_path=None,
        timeout_seconds=30.0,
    )
    catalog = await svc.load(refresh=True)

    fetch_fail = 0
    for src in catalog.sources:
        if src.error:
            fetch_fail += 1
            print(f"SOURCE {src.id} FAIL url={src.url} error={src.error}")
        else:
            print(f"SOURCE {src.id} OK ops={src.operation_count} url={src.url}")

    print(f"parsed_ops={len(catalog.operations)}")

    _DUMP_DIR.mkdir(parents=True, exist_ok=True)
    headers = {"Authorization": f"Bearer {cfg.sse.api_key}", "Accept": "application/json"}
    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        for link in links:
            resp = await client.get(link["url"])
            dest = _DUMP_DIR / f"{link['id']}.swagger.json"
            dest.write_bytes(resp.content)
            print(f"dump {dest.relative_to(_ROOT)} http={resp.status_code} bytes={len(resp.content)}")
    slim = [
        {
            "id": op.id,
            "source_id": op.source_id,
            "method": op.method,
            "path": op.path,
            "operation_id": op.operation_id,
        }
        for op in catalog.operations
    ]
    ops_dest = _DUMP_DIR / "operations.json"
    ops_dest.write_text(json.dumps(slim, indent=2) + "\n", encoding="utf-8")
    print(f"dump {ops_dest.relative_to(_ROOT)} ops={len(slim)}")

    expected_paths: list[str] = []
    if _HAND_CATALOG.is_file():
        raw = json.loads(_HAND_CATALOG.read_text(encoding="utf-8"))
        expected_paths = list(raw.get("paths", {}).keys())
        live_norms = {_path_norm(op.path) for op in catalog.operations}
        for p in expected_paths:
            mark = "HIT" if _path_norm(p) in live_norms else "MISS"
            print(f"hand_catalog_path {mark} {p}")

    summary = None
    for op in catalog.operations:
        oid = (op.operation_id or "").lower()
        if "summary" in oid and "loan" in oid:
            summary = op
            break
        if op.method == "get" and _path_norm(op.path).endswith("/api/loans/{}/summary"):
            summary = op
            break
    if summary is None:
        for op in catalog.operations:
            blob = f"{op.operation_id or ''} {op.path}".lower()
            if any(h in blob for h in _SUMMARY_HINTS) and op.method == "get":
                summary = op
                break

    if summary is None:
        print("FAIL: no loan summary GET in live catalog")
        return 1 if fetch_fail else 2

    path_names = [p.name for p in summary.parameters if p.in_ == "path"]
    print(
        f"summary_op id={summary.id} operation_id={summary.operation_id} "
        f"method={summary.method} path={summary.path} path_params={path_names}"
    )

    params: dict[str, str] = {}
    if path_names:
        params[path_names[0]] = _DEMO_LOAN_ID
    else:
        params["id"] = _DEMO_LOAN_ID
        params["loan_id"] = _DEMO_LOAN_ID

    result = await invoke_sse_api(
        svc,
        method=summary.method,
        path=summary.path,
        path_params=params,
        operation=summary,
    )
    print(f"invoke status={result.status} ok={result.ok} url_host_only (no body)")
    # URL may include loan id (synthetic demo id, not PII) — print path only
    print(f"invoke_path={summary.path} duration_ms={result.duration_ms}")
    if not result.ok:
        print(f"invoke_error_class={type(result.error_message).__name__} len={len(result.error_message or '')}")
        return 3

    if fetch_fail:
        print("PARTIAL: invoke OK but at least one swagger source failed")
        return 4
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
