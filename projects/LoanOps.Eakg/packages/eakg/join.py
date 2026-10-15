"""Shared join key: application + METHOD + normalized HTTP path."""

from __future__ import annotations

from packages.eakg.detectors import _norm_path
from packages.eakg.graph_build import _safe
from packages.eakg.route_identity import route_key, route_key_hash


def join_key(application_id: str, http_method: str, http_path: str) -> str:
    method = http_method.strip().upper() or "GET"
    return f"{application_id}|{method}|{_norm_path(http_path)}"


def eakg_operation_local_name(
    application_id: str,
    action: str,
    http_method: str,
    http_path: str = "/",
) -> str:
    """RDF local name matching ``interface_to_graph`` (route-key hash)."""
    del action  # label only; identity is method+path
    rhash = route_key_hash(route_key(http_method, http_path))
    return f"op_{_safe(application_id)}_{rhash}"
