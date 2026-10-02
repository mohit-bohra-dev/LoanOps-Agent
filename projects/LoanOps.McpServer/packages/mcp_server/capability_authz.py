"""Capability requiresPermission checks for the MCP boundary. Pure; no HTTP."""

from __future__ import annotations

from packages.mcp_server.policy import PolicyError

# Ontology rdfs:label for loanops:perm_loan_read (data/capability_kg + extract_openapi).
# Also IRI-style local name in case callers pass the resource, not the label.
# No implicit "*". Wildcard only when explicitly listed in configured allow-list.
_SYSTEM_DEV_READ_PERMS: frozenset[str] = frozenset(
    {
        "loan.read",
        "loanops:perm_loan_read",
    }
)

_ROLE_DEFAULTS: dict[str, frozenset[str]] = {
    "system": _SYSTEM_DEV_READ_PERMS,
    "dev": _SYSTEM_DEV_READ_PERMS,
}


def normalize_permission(label: str) -> str:
    """Strip whitespace and lower-case a permission label."""
    return label.strip().lower()


def assert_capability_permission(
    *,
    required: str | None,
    allowed: frozenset[str],
    enforce: bool,
) -> None:
    """Raise PolicyError when enforce is on and required perm not in allowed.

    Empty/None required → no ACL on capability → allow.
    """
    if not enforce:
        return
    if required is None or not str(required).strip():
        return
    needed = normalize_permission(str(required))
    if needed not in allowed:
        raise PolicyError(f"Permission '{needed}' not allowed for current role")


def allowed_permissions_for_role(
    role: str,
    configured: list[str] | frozenset[str],
) -> frozenset[str]:
    """Resolve allowed perms: configured set wins; else role defaults (system/dev)."""
    if configured:
        return frozenset(normalize_permission(p) for p in configured if str(p).strip())
    key = normalize_permission(role) if role else ""
    return _ROLE_DEFAULTS.get(key, frozenset())
