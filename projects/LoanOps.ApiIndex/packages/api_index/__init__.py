"""Unified OpenAPI + EAKG operation index (ADR-024)."""

from __future__ import annotations

__all__ = ["normalize_path", "build_operations", "OperationResolver", "OperationCatalog"]

from packages.api_index.catalog import OperationCatalog, build_operations
from packages.api_index.records import normalize_path
from packages.api_index.resolver import OperationResolver
