"""Technology detection — extensible extractor registry key."""

from __future__ import annotations

from pathlib import Path


def detect_technology(repo_root: str | Path) -> str:
    root = Path(repo_root)
    csprojs = list(root.rglob("*.csproj"))
    if csprojs:
        for p in csprojs:
            text = p.read_text(encoding="utf-8", errors="ignore")
            if "Microsoft.NET.Sdk.Web" in text or "Sdk=\"Microsoft.NET.Sdk.Web\"" in text:
                return "dotnet-aspnetcore"
        return "dotnet"
    if (root / "package.json").is_file():
        return "nodejs"
    if list(root.glob("pom.xml")) or list(root.rglob("pom.xml"))[:1]:
        return "java-maven"
    if (root / "pyproject.toml").is_file():
        return "python"
    return "unknown"
