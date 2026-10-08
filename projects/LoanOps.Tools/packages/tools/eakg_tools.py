"""EAKG discovery tools (search / explain / find / impact)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from packages.capability_kg.store import load_graph
from packages.common.scopes import EAKG_TOOL_NAMES
from packages.common.settings import Settings
from packages.eakg.query import (
    explain_capability,
    find_providers,
    impact_of_change,
    search_capabilities,
)
from packages.tools.capability_catalog import CapabilityCatalogService
from packages.tools.policy import ToolPolicyError

EAKG_TOOLS = EAKG_TOOL_NAMES


async def dispatch_eakg_tool(
    name: str,
    arguments: dict[str, Any],
    *,
    catalog_service: CapabilityCatalogService | None,
    settings: Settings,
) -> str:
    """Run EAKG query tools. When approved_only, read catalog/approved.ttl only."""
    # LAYER2-BP E1: EAKG tools (was mcp_server._execute_eakg_tool)
    if name not in EAKG_TOOLS:
        raise ToolPolicyError(f"Unknown EAKG tool: {name}")

    from rdflib import Graph

    ns = settings.capability_kg.namespace
    graph: Graph
    if settings.capability_kg.approved_only:
        approved = Path(settings.eakg.shard_dir) / "catalog" / "approved.ttl"
        if not approved.is_file():
            return json.dumps([])
        graph = load_graph(approved, namespace=ns)
    else:
        if catalog_service is None:
            raise ToolPolicyError("capability catalog unavailable")
        merged = catalog_service.graph()
        if merged is None:
            return json.dumps([])
        graph = merged

    if name == "search_capabilities":
        rows = search_capabilities(
            graph,
            str(arguments.get("query") or ""),
            namespace=ns,
            limit=int(arguments.get("limit") or 15),
        )
        return json.dumps(rows, indent=2)
    if name == "explain_capability":
        row = explain_capability(
            graph,
            str(arguments.get("capability_id") or ""),
            namespace=ns,
        )
        return json.dumps(row or {"error": "not found"}, indent=2)
    if name == "find_providers":
        rows = find_providers(graph, str(arguments.get("query") or ""), namespace=ns)
        return json.dumps(rows, indent=2)
    if name == "impact_of_change":
        rows = impact_of_change(graph, str(arguments.get("target") or ""), namespace=ns)
        if settings.capability_kg.approved_only:
            rows = [r for r in rows if r.get("review_status") == "approved"]
        return json.dumps(rows, indent=2)
    raise ToolPolicyError(f"Unknown EAKG tool: {name}")
