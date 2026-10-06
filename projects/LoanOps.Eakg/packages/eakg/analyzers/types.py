"""Normalized engineering-graph fragment types (analyzer protocol)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

NodeKind = Literal["Method", "Type", "HttpCall", "ApiHandler"]
EdgeKind = Literal["calls", "handlesOperation", "sendsHttpRequest"]


@dataclass(frozen=True)
class Provenance:
    analyzer: str
    version: str
    commit: str


@dataclass
class FragmentNode:
    id: str
    kind: NodeKind
    language: str
    file: str
    line: int
    label: str = ""


@dataclass
class FragmentEdge:
    source: str
    target: str
    kind: EdgeKind
    confidence: float
    provenance: Provenance


@dataclass
class GraphFragment:
    nodes: list[FragmentNode] = field(default_factory=list)
    edges: list[FragmentEdge] = field(default_factory=list)


@dataclass
class Inventory:
    languages: list[str]
    projects: list[str]


@dataclass
class AnalyzerResult:
    fragment: GraphFragment
    error: str | None = None
    extra: dict[str, object] = field(default_factory=dict)
