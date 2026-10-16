"""Doc GraphRAG — community summary routing wrapping DocsService (P4)."""

from packages.graph_rag.route import select_route
from packages.graph_rag.service import GraphRagService

__all__ = ["GraphRagService", "select_route"]
