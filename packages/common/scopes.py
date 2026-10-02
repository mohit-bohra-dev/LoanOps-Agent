"""Tool allow-lists by role / API key scope."""

from __future__ import annotations

# Keep constants inline — avoid importing docs/sse packages (heavy providers).
SSE_TOOL_NAMES = ("search_sse_apis", "list_sse_apis", "call_sse_api")
EAKG_TOOL_NAMES = (
    "search_capabilities",
    "explain_capability",
    "find_providers",
    "impact_of_change",
)
DB_TOOL_NAMES = ("get_customer_servicing_summary", "run_read_only_sql")
DOCS_TOOL_NAMES = ("search_docs", "index_docs")
WIKI_TOOL_NAMES = (
    "wiki_document_feature",
    "wiki_search_gitlab",
    "wiki_get_jira_ticket",
    "wiki_resolve_package",
    "wiki_read_page",
)

SCOPE_TOOLS: dict[str, frozenset[str]] = {
    "sse.read": frozenset(SSE_TOOL_NAMES),
    "eakg.read": frozenset(EAKG_TOOL_NAMES),
    "docs.search": frozenset({"search_docs"}),
    "docs.index": frozenset({"index_docs"}),
    "db.read": frozenset(DB_TOOL_NAMES),
    "wiki.write_docs": frozenset({"wiki_document_feature"}),
    "wiki.gitlab": frozenset({"wiki_search_gitlab"}),
    "wiki.jira": frozenset({"wiki_get_jira_ticket"}),
    "wiki.packages": frozenset({"wiki_resolve_package"}),
    "wiki.screen": frozenset({"wiki_read_page"}),
}

ROLE_SCOPES: dict[str, frozenset[str]] = {
    # Default agent path: live SSE OpenAPI + docs + enterprise capability graph queries.
    "system": frozenset({"sse.read", "docs.search", "eakg.read"}),
    "dev": frozenset(
        {
            "sse.read",
            "eakg.read",
            "docs.search",
            "docs.index",
            "db.read",
            "wiki.write_docs",
            "wiki.gitlab",
            "wiki.jira",
            "wiki.packages",
            "wiki.screen",
        }
    ),
    "pm": frozenset({"sse.read", "docs.search", "wiki.jira", "eakg.read"}),
    "care_rep": frozenset({"sse.read", "docs.search", "eakg.read"}),
    "customer": frozenset({"sse.read"}),
}


def tools_for_scopes(scopes: list[str] | frozenset[str]) -> frozenset[str]:
    allowed: set[str] = set()
    for scope in scopes:
        allowed |= SCOPE_TOOLS.get(scope, frozenset())
    return frozenset(allowed)


def tools_for_role(role: str) -> frozenset[str]:
    return tools_for_scopes(ROLE_SCOPES.get(role, frozenset()))


def filter_tool_names(names: list[str], allowed: frozenset[str]) -> list[str]:
    return [n for n in names if n in allowed]
