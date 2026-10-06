"""Select MVP analyzers: DotNet (API) + optional Graphify (engineering)."""

from __future__ import annotations

from pathlib import Path

from packages.eakg.analyzers.dotnet_adapter import DotNetRoslynAdapter
from packages.eakg.analyzers.graphify_adapter import GraphifyAstAdapter
from packages.eakg.analyzers.protocol import Analyzer, inventory
from packages.eakg.analyzers.types import Inventory

# Java is an explicit non-entry — never registered.
_DOTNET = DotNetRoslynAdapter()
_GRAPHIFY = GraphifyAstAdapter()


def select_analyzers(
    repo: Path,
    *,
    engineering_graph: bool,
) -> tuple[list[Analyzer], Inventory, list[str]]:
    """Return (adapters to run, inventory, unsupported languages).

    Unsupported = inventoried languages with no API-surface adapter.
    csharp is supported by DotNetRoslynAdapter. Graphify is not an API adapter.
    """
    inv = inventory(repo)
    chosen: list[Analyzer] = []
    if _DOTNET.detect(repo) > 0:
        chosen.append(_DOTNET)
    if engineering_graph:
        chosen.append(_GRAPHIFY)
    api_langs = set()
    for a in chosen:
        if a.produces_api_surface:
            api_langs |= set(a.languages)
    unsupported = [lang for lang in inv.languages if lang not in api_langs]
    return chosen, inv, unsupported
