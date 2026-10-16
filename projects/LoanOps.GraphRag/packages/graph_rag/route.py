"""Pure query → local|global route (not exposed on LLM tool schema)."""

from __future__ import annotations

from typing import Literal

Route = Literal["local", "global"]

# Deterministic multi-doc / survey cues (doc-graphrag FR-009).
_GLOBAL_HINTS: tuple[str, ...] = (
    "compare",
    "across",
    "overview",
    "differ",
    " versus ",
    " vs ",
    "survey",
    "relate",
    "together with",
    "alongside",
    "interact",
    "connect",
)


def select_route(query: str) -> Route:
    """Return ``global`` when the query looks multi-policy; else ``local``."""
    q = f" {query.lower()} "
    for hint in _GLOBAL_HINTS:
        if hint in q or hint.strip() in q:
            return "global"
    return "local"
