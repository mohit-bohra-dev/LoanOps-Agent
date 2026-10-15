"""Tree-sitter structural API extractors (Python, Node/TypeScript)."""

from __future__ import annotations

from pathlib import Path

from packages.eakg.extractors.treesitter.node import extract_node_routes
from packages.eakg.extractors.treesitter.python import extract_python_routes
from packages.eakg.models import ApiOperationFact


def extract_treesitter_routes(
    repo: Path,
    *,
    repository_id: str,
    commit_sha: str,
    api_project_path: str = "",
    languages: list[str] | None = None,
) -> tuple[list[ApiOperationFact], list[str]]:
    """Run enabled language strategies and concatenate facts."""
    langs = set(languages or [])
    facts: list[ApiOperationFact] = []
    warnings: list[str] = []
    want_py = not langs or "python" in langs
    want_node = not langs or bool(langs & {"javascript", "typescript"})
    if want_py:
        f, w = extract_python_routes(
            repo,
            repository_id=repository_id,
            commit_sha=commit_sha,
            api_project_path=api_project_path,
        )
        facts.extend(f)
        warnings.extend(w)
    if want_node:
        f, w = extract_node_routes(
            repo,
            repository_id=repository_id,
            commit_sha=commit_sha,
            api_project_path=api_project_path,
        )
        facts.extend(f)
        warnings.extend(w)
    return facts, warnings
