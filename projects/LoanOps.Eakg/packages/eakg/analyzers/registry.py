"""Select API + optional Graphify analyzers from inventory."""

from __future__ import annotations

from pathlib import Path

from packages.eakg.analyzers.dotnet_adapter import DotNetRoslynAdapter
from packages.eakg.analyzers.graphify_adapter import GraphifyAstAdapter
from packages.eakg.analyzers.protocol import Analyzer, inventory
from packages.eakg.analyzers.treesitter_adapter import TreeSitterApiAdapter
from packages.eakg.analyzers.types import Inventory

_DOTNET = DotNetRoslynAdapter()
_TREESITTER = TreeSitterApiAdapter()
_GRAPHIFY = GraphifyAstAdapter()


def select_analyzers(
    repo: Path,
    *,
    engineering_graph: bool,
) -> tuple[list[Analyzer], Inventory, list[str]]:
    """Return (adapters to run, inventory, unsupported languages).

    Unsupported = inventoried languages with no API-surface adapter.
    csharp → DotNetRoslynAdapter; python/javascript/typescript → TreeSitterApiAdapter.
    java remains unsupported. Graphify is not an API adapter.
    """
    inv = inventory(repo)
    chosen: list[Analyzer] = []
    if _DOTNET.detect(repo) > 0:
        chosen.append(_DOTNET)
    if _TREESITTER.detect(repo) > 0:
        chosen.append(_TREESITTER)
    if engineering_graph:
        chosen.append(_GRAPHIFY)
    api_langs: set[str] = set()
    for a in chosen:
        if a.produces_api_surface:
            api_langs |= set(a.languages)
    unsupported = [lang for lang in inv.languages if lang not in api_langs]
    return chosen, inv, unsupported
