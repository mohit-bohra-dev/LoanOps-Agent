"""Embedding provider protocol — re-exports from provider_contracts."""

from provider_contracts.embedding import AbstractEmbeddingProvider as EmbeddingProvider
from provider_contracts.embedding import EmbeddingResult

__all__ = ["EmbeddingProvider", "EmbeddingResult"]
