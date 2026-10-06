"""ASP.NET Core / Roslyn adapter — only writer of EAKG API operations in MVP."""

from __future__ import annotations

from pathlib import Path

from packages.eakg.analyzers.protocol import Analyzer
from packages.eakg.analyzers.types import (
    AnalyzerResult,
    FragmentNode,
    GraphFragment,
    Provenance,
)
from packages.eakg.extractors.dotnet import extract_repo
from packages.eakg.models import ApiOperationFact


class DotNetRoslynAdapter:
    id = "dotnet_roslyn"
    version = "2.0.0"
    languages = frozenset({"csharp"})
    produces_api_surface = True
    fatal = True

    def detect(self, repo: Path) -> float:
        root = Path(repo)
        if list(root.rglob("*.csproj")):
            return 1.0
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
        iface, details = extract_repo(
            repo,
            repository_id=repository_id,
            application_id=application_id,
            commit_sha=commit_sha,
            api_project_path=api_project_path,
        )
        nodes: list[FragmentNode] = []
        ops = details.get("operations")
        if isinstance(ops, list):
            for item in ops:
                if not isinstance(item, ApiOperationFact):
                    continue
                file_path = item.evidence[0].file_path if item.evidence else ""
                line = item.evidence[0].line_start if item.evidence else 1
                symbol = f"{item.controller}.{item.action}" if item.controller else item.action
                nodes.append(
                    FragmentNode(
                        id=f"{repository_id}:{file_path}:{symbol}",
                        kind="ApiHandler",
                        language="csharp",
                        file=file_path,
                        line=line,
                        label=symbol,
                    )
                )
        extractor_id = str(details.get("extractor") or self.id)
        extra: dict[str, object] = {
            "repo_interface": iface,
            "details": details,
            "extractor": extractor_id,
        }
        return AnalyzerResult(
            fragment=GraphFragment(nodes=nodes),
            extra=extra,
        )


def as_analyzer() -> Analyzer:
    return DotNetRoslynAdapter()
