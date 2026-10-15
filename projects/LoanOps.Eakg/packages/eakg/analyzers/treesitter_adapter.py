"""Non-fatal tree-sitter API surface adapter (Python / Node)."""

from __future__ import annotations

from pathlib import Path

from packages.eakg.analyzers.protocol import Analyzer, inventory
from packages.eakg.analyzers.types import AnalyzerResult, GraphFragment
from packages.eakg.extractors.treesitter import extract_treesitter_routes
from packages.eakg.models import RepoInterface


class TreeSitterApiAdapter:
    id = "treesitter_api"
    version = "1.0.0"
    languages = frozenset({"python", "javascript", "typescript"})
    produces_api_surface = True
    fatal = False

    def detect(self, repo: Path) -> float:
        inv = inventory(repo)
        if set(inv.languages) & self.languages:
            return 0.8
        # Nested markers without inventory hit
        root = Path(repo)
        for pkg in root.rglob("package.json"):
            if "node_modules" not in pkg.parts:
                return 0.7
        if next(root.rglob("pyproject.toml"), None) is not None:
            return 0.7
        if next(root.rglob("requirements.txt"), None) is not None:
            return 0.7
        if next(root.rglob("*.py"), None) is not None:
            return 0.6
        return 0.0

    def extract(
        self,
        repo: Path,
        *,
        repository_id: str,
        application_id: str,
        commit_sha: str,
        api_project_path: str = "",
        dest: Path | None = None,
    ) -> AnalyzerResult:
        del dest
        inv = inventory(repo)
        langs = [lang for lang in inv.languages if lang in self.languages]
        facts, warnings = extract_treesitter_routes(
            Path(repo),
            repository_id=repository_id,
            commit_sha=commit_sha,
            api_project_path=api_project_path,
            languages=langs or None,
        )
        iface = RepoInterface(
            repository_id=repository_id,
            application_id=application_id,
            commit_sha=commit_sha,
        )
        iface.operations = [
            {
                "key": f.operation_key,
                "method": f.http_method,
                "path": f.http_path,
                "controller": f.controller,
                "action": f.action,
                "authz_policy": f.authz_policy,
                "authz_source": f.authz_source,
                "read_only": f.read_only,
            }
            for f in facts
        ]
        extra: dict[str, object] = {
            "repo_interface": iface,
            "details": {"operations": facts, "extractor": self.id},
            "extractor": self.id,
            "operation_facts": facts,
            "warnings": warnings,
        }
        return AnalyzerResult(fragment=GraphFragment(), extra=extra)


def as_analyzer() -> Analyzer:
    return TreeSitterApiAdapter()
