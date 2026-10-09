"""One-shot: expand local OpenAPI fixtures from shard interface.json (no PII)."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path("data/eakg")
APPS = {
    "escrow": "Escrow Manager",
    "fees": "Fees",
    "loanservices": "Loan Services",
}


def path_params(path: str) -> list[dict[str, object]]:
    params: list[dict[str, object]] = []
    for name in re.findall(r"\{([^}/]+)\}", path):
        params.append(
            {
                "name": name,
                "in": "path",
                "required": True,
                "schema": {"type": "string"},
            }
        )
    for name in re.findall(r"\[([^\]/]+)\]", path):
        params.append(
            {
                "name": name,
                "in": "path",
                "required": True,
                "schema": {"type": "string"},
            }
        )
    return params


def main() -> None:
    for app_id, title in APPS.items():
        iface = json.loads(
            (ROOT / "repos" / app_id / "interface.json").read_text(encoding="utf-8")
        )
        paths: dict[str, dict[str, object]] = {}
        op_ids_used: set[str] = set()
        for op in iface.get("operations") or []:
            method = str(op.get("method") or "GET").lower()
            path = str(op.get("path") or "")
            if not path or method not in {
                "get",
                "post",
                "put",
                "patch",
                "delete",
                "head",
                "options",
            }:
                continue
            action = str(op.get("action") or "op")
            oid = action
            n = 2
            while oid in op_ids_used:
                oid = f"{action}_{n}"
                n += 1
            op_ids_used.add(oid)
            entry = paths.setdefault(path, {})
            if method in entry:
                continue
            item: dict[str, object] = {
                "operationId": oid,
                "summary": f"{action} ({op.get('controller') or ''})".strip(),
                "tags": [str(op.get("controller") or app_id)],
                "responses": {"200": {"description": "OK"}},
            }
            params = path_params(path)
            if params:
                item["parameters"] = params
            if method in {"post", "put", "patch"}:
                item["requestBody"] = {
                    "required": False,
                    "content": {
                        "application/json": {"schema": {"type": "object"}}
                    },
                }
            entry[method] = item
        doc = {
            "openapi": "3.0.3",
            "info": {"title": f"{title} (from EAKG interface)", "version": "1.0.0"},
            "paths": dict(sorted(paths.items())),
        }
        out = ROOT / "fixtures" / "specs" / f"{app_id}.openapi.json"
        out.write_text(json.dumps(doc, indent=2), encoding="utf-8")
        op_count = sum(len(v) for v in paths.values())
        print(f"{app_id}: paths={len(paths)} ops={op_count} -> {out}")


if __name__ == "__main__":
    main()
