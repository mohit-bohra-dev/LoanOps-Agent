"""EAKG discovery tools (search / explain / find / impact / describe / code)."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from packages.common.providers.graph_store import AbstractGraphStore, GraphStoreError
from packages.common.scopes import EAKG_TOOL_NAMES
from packages.common.settings import Settings
from packages.eakg.engineering import search_code
from packages.eakg.query import (
    describe_application,
    explain_capability,
    find_providers,
    impact_of_change,
    safe_application_id,
    search_capabilities,
)
from packages.tools.policy import ToolPolicyError

EAKG_TOOLS = EAKG_TOOL_NAMES


async def dispatch_eakg_tool(
    name: str,
    arguments: dict[str, Any],
    *,
    catalog_service: Any | None = None,
    settings: Settings,
    graph_store: AbstractGraphStore | None = None,
) -> str:
    """Run EAKG query tools against the configured SPARQL graph store."""
    _ = catalog_service  # retained for call-site compatibility; unused (ADR-026)
    if name not in EAKG_TOOLS:
        raise ToolPolicyError(f"Unknown EAKG tool: {name}")

    store = graph_store
    if store is None:
        from packages.common.providers.factory import get_graph_store

        store = get_graph_store()

    ns = settings.capability_kg.namespace
    try:
        if name == "search_capabilities":
            rows = await search_capabilities(
                store,
                str(arguments.get("query") or ""),
                namespace=ns,
                limit=int(arguments.get("limit") or 15),
            )
            return json.dumps(rows, indent=2)
        if name == "explain_capability":
            row = await explain_capability(
                store,
                str(arguments.get("capability_id") or ""),
                namespace=ns,
            )
            return json.dumps(row or {"error": "not found"}, indent=2)
        if name == "find_providers":
            rows = await find_providers(
                store, str(arguments.get("query") or ""), namespace=ns
            )
            return json.dumps(rows, indent=2)
        if name == "impact_of_change":
            rows = await impact_of_change(
                store, str(arguments.get("target") or ""), namespace=ns
            )
            if settings.capability_kg.approved_only:
                rows = [r for r in rows if r.get("review_status") == "approved"]
            return json.dumps(rows, indent=2)
        if name == "describe_application":
            app_raw = safe_application_id(str(arguments.get("application_id") or ""))
            if app_raw is None:
                return json.dumps(
                    {"error": "application_id required (alphanumeric / ._- only)"}
                )
            app_id: str = app_raw
            from packages.eakg.runtime import eakg_runtime

            _reg, shard, _arts = eakg_runtime(settings)

            def _load_iface() -> Any:
                return shard.read_interface(app_id)

            row = await describe_application(
                store,
                app_id,
                namespace=ns,
                interface_fallback=_load_iface,
            )
            return json.dumps(row, indent=2)
        if name == "search_code":
            code_raw = safe_application_id(str(arguments.get("application_id") or ""))
            if code_raw is None:
                return json.dumps(
                    {"error": "application_id required (alphanumeric / ._- only)"}
                )
            code_app: str = code_raw
            from packages.eakg.runtime import eakg_runtime

            _reg, shard, _arts = eakg_runtime(settings)
            eng_path = shard.engineering_dir(code_app) / "graph.json"
            row = await asyncio.to_thread(
                search_code,
                code_app,
                str(arguments.get("query") or ""),
                engineering_graph_path=eng_path,
                limit=int(arguments.get("limit") or 20),
            )
            return json.dumps(row, indent=2)
    except GraphStoreError as exc:
        raise ToolPolicyError(f"graph store unavailable: {exc}") from exc
    raise ToolPolicyError(f"Unknown EAKG tool: {name}")
