"""Wiki specialists — scaffold for port from plaisse-wiki.

Live API → packages.sse. Live SQL → packages.db.
This package owns: doc write, GitLab, Jira, commit reconcile, NuGet, screen read.
"""

from __future__ import annotations

from typing import Any

WIKI_TOOL_NAMES = (
    "wiki_document_feature",
    "wiki_search_gitlab",
    "wiki_get_jira_ticket",
    "wiki_resolve_package",
    "wiki_read_page",
)


async def dispatch_wiki_tool(name: str, args: dict[str, Any]) -> str:
    """Placeholder until full TS→Python port of wiki specialists."""
    _ = args
    return (
        f"wiki tool '{name}' registered but not yet ported from plaisse-wiki. "
        "Use search_docs / search_sse_apis for query path."
    )
