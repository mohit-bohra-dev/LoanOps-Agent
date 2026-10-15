"""EAKG analyzer plugins (MVP: Roslyn + Graphify + tree-sitter)."""

from packages.eakg.analyzers.protocol import Analyzer, inventory
from packages.eakg.analyzers.types import AnalyzerResult, GraphFragment, Inventory

__all__ = [
    "Analyzer",
    "AnalyzerResult",
    "GraphFragment",
    "Inventory",
    "inventory",
    "select_analyzers",
]


def __getattr__(name: str) -> object:
    if name == "select_analyzers":
        from packages.eakg.analyzers.registry import select_analyzers

        return select_analyzers
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
