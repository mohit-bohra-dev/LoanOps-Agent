"""Canonical HTTP route identity for multi-adapter API merge."""

from __future__ import annotations

import hashlib
import re

_PARAM_COLON = re.compile(r":([A-Za-z_][A-Za-z0-9_]*)")
_PARAM_ANGLE = re.compile(r"<(?:[^:>]+:)?([^>]+)>")
_PARAM_BRACE = re.compile(r"\{([^{}:]+)(?::[^{}]+)?\}")
_MULTI_SLASH = re.compile(r"/+")


def normalize_path(path: str) -> str:
    """Normalize framework path templates to OpenAPI-style ``{id}`` form."""
    raw = (path or "").strip()
    if not raw:
        return "/"
    # Flask <int:id> / <id> before colon rewrite (colon appears inside angles)
    out = _PARAM_ANGLE.sub(r"{\1}", raw)
    # ASP.NET / Spring {id:int} → {id}
    out = _PARAM_BRACE.sub(r"{\1}", out)
    # Express style :id (not already braced)
    out = _PARAM_COLON.sub(r"{\1}", out)
    if not out.startswith("/"):
        out = "/" + out
    out = _MULTI_SLASH.sub("/", out)
    if len(out) > 1 and out.endswith("/"):
        out = out.rstrip("/")
    return out


def route_key(method: str, path: str) -> str:
    """Canonical merge key: ``METHOD:/normalized/path``."""
    m = (method or "GET").strip().upper() or "GET"
    return f"{m}:{normalize_path(path)}"


def route_key_hash(key: str) -> str:
    """Stable short hash for RDF local names."""
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


def fact_rank(detector_id: str, controller: str) -> int:
    """Lower rank wins merge metadata. Controllers beat Minimal APIs beat tree-sitter."""
    did = (detector_id or "").lower()
    ctrl = controller or ""
    if did.startswith("dotnet_roslyn") or did.startswith("dotnet_static"):
        if ctrl == "MinimalApi" or ctrl.startswith("MinimalApi:"):
            return 10
        return 0
    if did.startswith("treesitter"):
        return 20
    return 50
