"""Vector store provider protocol — re-exports from provider_contracts."""

from provider_contracts.vector_store import (
    AbstractVectorStoreProvider as VectorStoreProvider,
)
from provider_contracts.vector_store import SearchResult, VectorDocument

__all__ = ["VectorStoreProvider", "SearchResult", "VectorDocument"]
