"""One-off: inspect swagger schemas for loan endpoints. Safe to delete."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import httpx

from packages.common.settings import Settings

SWAGGER = "https://loanservicesapi-plaisse-dev.pnmac.com/swagger/1.0/swagger.json"

TARGETS = [
    "/api/Loans/{id}",
    "/api/Loans/{id}/Summary",
    "/api/Loans/{id}/Balances",
    "/api/Loans/{LoanId}/BorrowerSummary",
    "/api/Loans/{id}/Delinquencies",
    "/api/SearchBar",
]


def resolve_ref(spec: dict, ref: str) -> dict:
    # e.g. "#/definitions/LoanSummaryDto"
    node: dict = spec
    for part in ref.lstrip("#/").split("/"):
        node = node.get(part, {})
    return node


def schema_ref(schema: dict) -> str | None:
    if not schema:
        return None
    if "$ref" in schema:
        return schema["$ref"]
    items = schema.get("items")
    if isinstance(items, dict) and "$ref" in items:
        return items["$ref"]
    return None


def print_props(spec: dict, ref: str, indent: str = "      ") -> None:
    definition = resolve_ref(spec, ref)
    props = definition.get("properties", {})
    if not props:
        print(f"{indent}(no properties on {ref})")
        return
    for name, meta in props.items():
        typ = meta.get("type") or schema_ref(meta) or ""
        fmt = meta.get("format", "")
        label = f"{typ}({fmt})" if fmt else typ
        print(f"{indent}{name}: {label}")


async def main() -> None:
    s = Settings()
    headers = {
        "Authorization": f"Bearer {s.data.loan_api.api_key}",
        "Accept": "application/json",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        spec = (await client.get(SWAGGER, headers=headers)).json()

    paths = spec.get("paths", {})
    for target in TARGETS:
        print("=" * 72)
        print(target)
        node = paths.get(target)
        if not node:
            print("  (not found)")
            continue
        for method, detail in node.items():
            if method.startswith("x-"):
                continue
            print(f"  {method.upper()} — {detail.get('summary', '')}")
            for p in detail.get("parameters", []):
                p_type = p.get("type") or schema_ref(p.get("schema", {})) or ""
                print(
                    f"    param: {p.get('name')} "
                    f"(in={p.get('in')}, required={p.get('required')}, type={p_type})"
                )
            resp = detail.get("responses", {}).get("200", {})
            ref = schema_ref(resp.get("schema", {}))
            if ref:
                print(f"    200 -> {ref}")
                print_props(spec, ref)
            else:
                print(f"    200 -> {resp.get('schema', {})}")


if __name__ == "__main__":
    asyncio.run(main())
