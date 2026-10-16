"""Citation grounding — policy cites must match search_docs retrieval this turn."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

# Bullet lines from DocsService.search: "- [sop] path/to.md (score=0.123)"
_SEARCH_DOCS_PATH_RE = re.compile(
    r"^-\s*\[[^\]]+\]\s+(\S+)\s+\(score=",
    re.MULTILINE,
)

_DOC_SEARCH_TOOLS = frozenset({"search_docs"})


@dataclass(frozen=True)
class GroundingReport:
    """Counts from a grounding pass."""

    kept: int
    dropped_ungrounded: int
    dropped_bad_snippet: int


def _tool_name(tool: Any) -> str:
    if hasattr(tool, "name"):
        return str(tool.name)
    if isinstance(tool, dict):
        return str(tool.get("name", "unknown"))
    return "unknown"


def _tool_summary(tool: Any) -> str:
    if hasattr(tool, "result_summary"):
        return str(tool.result_summary or "")
    if isinstance(tool, dict):
        return str(tool.get("result_summary", "") or "")
    return ""


def _normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def extract_paths_and_texts(recorded_tools: list[Any]) -> tuple[set[str], list[str]]:
    """Collect relative paths and raw texts from search_docs tool results."""
    paths: set[str] = set()
    texts: list[str] = []
    for tool in recorded_tools:
        if _tool_name(tool) not in _DOC_SEARCH_TOOLS:
            continue
        summary = _tool_summary(tool)
        if not summary or summary == "No matching documents.":
            continue
        texts.append(summary)
        for match in _SEARCH_DOCS_PATH_RE.finditer(summary):
            path = match.group(1).replace("\\", "/")
            paths.add(path)
            # Also accept basename matches for fragment-only cites
            if "/" in path:
                paths.add(path.rsplit("/", 1)[-1])
    return paths, texts


def policy_citation_grounded(policy_source: str, paths: set[str]) -> bool:
    """True if policy path (strip prefix + fragment) matches a retrieved path."""
    raw = policy_source
    if raw.startswith("policy:"):
        raw = raw[len("policy:") :]
    path = raw.split("#", 1)[0].replace("\\", "/").lstrip("/")
    if not path:
        return False
    if path in paths:
        return True
    # Prefix / suffix tolerance: must_cite style hardship/x.md vs full relative
    for p in paths:
        if p.endswith(path) or path.endswith(p):
            return True
    return False


def ground_citations(
    data: dict[str, Any],
    recorded_tools: list[Any] | None,
) -> GroundingReport:
    """Drop ungrounded ``policy:`` citations in-place.

    When *recorded_tools* is None or empty, grounding is skipped (parser-only
    callers / unit tests). When tools ran but none were ``search_docs``, all
    ``policy:`` citations are dropped.
    """
    citations = data.get("citations")
    if not isinstance(citations, list):
        return GroundingReport(0, 0, 0)

    if not recorded_tools:
        return GroundingReport(kept=len(citations), dropped_ungrounded=0, dropped_bad_snippet=0)

    paths, texts = extract_paths_and_texts(recorded_tools)
    combined = _normalize_ws("\n".join(texts)) if texts else ""

    kept_list: list[Any] = []
    dropped_ungrounded = 0
    dropped_bad_snippet = 0

    for cite in citations:
        if not isinstance(cite, dict):
            kept_list.append(cite)
            continue

        source = cite.get("source", "")
        if not isinstance(source, str) or not source.startswith("policy:"):
            kept_list.append(cite)
            continue

        if not paths or not policy_citation_grounded(source, paths):
            dropped_ungrounded += 1
            continue

        snippet = cite.get("snippet", "")
        if isinstance(snippet, str) and snippet.strip() and combined:
            if _normalize_ws(snippet) not in combined:
                dropped_bad_snippet += 1
                continue

        kept_list.append(cite)

    data["citations"] = kept_list
    return GroundingReport(
        kept=len(kept_list),
        dropped_ungrounded=dropped_ungrounded,
        dropped_bad_snippet=dropped_bad_snippet,
    )
