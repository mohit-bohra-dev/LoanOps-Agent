"""PNMAC ``requested_destination`` resolution (Auth0JwtRetriever port).

Faithful to Plaisse wiki ``registry/destination.ts`` /
``PNMAC.Core.WebApi.Auth0JwtRetriever.ResolveDestinationFromEndpoint``.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

_BASE_ENVIRONMENTS = ("dev", "qa", "stg", "prd")
DEFAULT_HOSTS_THAT_REQUIRE_TOKENS = ("pnmac.com", "pennymac.com", "plaisse.com", "localhost")


def _remove_scheme(value: str) -> str:
    return re.sub(r"^https?://", "", value, flags=re.IGNORECASE)


def _extract_subdomain(host: str) -> str:
    if "." not in host:
        return host
    i = host.index(".")
    return host[:i] if i > 0 else host


def _extract_app_name_from_subdomain_pattern(host: str) -> str | None:
    for env in _BASE_ENVIRONMENTS:
        m = re.search(rf"\.{env}\d*\.", host, flags=re.IGNORECASE)
        if m:
            return host[: m.start()]
    return None


def _extract_app_name_from_suffix_pattern(subdomain: str) -> str | None:
    for env in _BASE_ENVIRONMENTS:
        m = re.search(rf"-{env}\d*$", subdomain, flags=re.IGNORECASE)
        if m:
            before = subdomain[: m.start()]
            if re.search(r"-plaisse$", before, flags=re.IGNORECASE):
                return before[: -len("-plaisse")]
            return before
    return None


def extract_app_name_from_host(host: str) -> str:
    if not host:
        return host
    from_sub = _extract_app_name_from_subdomain_pattern(host)
    if from_sub is not None:
        return from_sub
    subdomain = _extract_subdomain(host)
    from_suffix = _extract_app_name_from_suffix_pattern(subdomain)
    if from_suffix is not None:
        return from_suffix
    if re.search(r"-plaisse$", subdomain, flags=re.IGNORECASE):
        return subdomain[: -len("-plaisse")]
    return subdomain


def requires_token(
    url_str: str,
    *,
    hosts_that_require_tokens: tuple[str, ...] | list[str] = DEFAULT_HOSTS_THAT_REQUIRE_TOKENS,
) -> bool:
    host = urlparse(url_str).hostname or ""
    host_l = host.lower()
    for h in hosts_that_require_tokens:
        hl = h.lower()
        if host_l == hl or host_l.endswith(f".{hl}"):
            return True
    return False


def resolve_destination(
    url_str: str,
    *,
    destination_mappings: dict[str, str] | None = None,
    hosts_that_require_tokens: tuple[str, ...] | list[str] = DEFAULT_HOSTS_THAT_REQUIRE_TOKENS,
) -> str:
    """Return Auth0 ``requested_destination`` for a target service URL."""
    u = urlparse(url_str)
    host = u.hostname or ""
    port = f":{u.port}" if u.port and u.port not in (80, 443) else ""
    base_url = f"{u.scheme}://{host}{port}"
    mapping = destination_mappings or {}

    if requires_token(url_str, hosts_that_require_tokens=hosts_that_require_tokens):
        if "." not in host:
            return mapping.get(base_url) or _remove_scheme(base_url)
        app_name = extract_app_name_from_host(host)
        app_name_url = f"{u.scheme}://{app_name}"
        if app_name_url in mapping:
            return mapping[app_name_url]
        subdomain_url = f"{u.scheme}://{_extract_subdomain(host)}"
        if subdomain_url in mapping:
            return mapping[subdomain_url]
        if base_url in mapping:
            return mapping[base_url]
        return _remove_scheme(app_name_url)

    return mapping.get(base_url) or mapping.get(url_str) or _remove_scheme(base_url)
