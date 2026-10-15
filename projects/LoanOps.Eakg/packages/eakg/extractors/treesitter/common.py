"""Shared helpers for tree-sitter API route extractors."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from packages.eakg.models import ApiOperationFact, AuthzSource, Evidence, utc_now_iso
from packages.eakg.route_identity import normalize_path

SKIP_DIR_NAMES = frozenset(
    {
        ".git",
        "node_modules",
        ".venv",
        "venv",
        "dist",
        "build",
        "target",
        "bin",
        "obj",
        "coverage",
        "__pycache__",
        ".tox",
        ".mypy_cache",
        ".pytest_cache",
        "vendor",
    }
)

MAX_FILE_BYTES = 1_000_000


def iter_source_files(
    root: Path,
    *,
    suffixes: frozenset[str],
    api_project_path: str = "",
) -> Iterator[Path]:
    search = root
    if api_project_path.strip():
        candidate = root / api_project_path.replace("\\", "/").lstrip("/")
        if candidate.is_dir():
            search = candidate
    stack = [search]
    while stack:
        current = stack.pop()
        try:
            entries = list(current.iterdir())
        except OSError:
            continue
        for entry in entries:
            if entry.is_dir():
                if entry.name in SKIP_DIR_NAMES:
                    continue
                # skip common test directories
                lowered = entry.name.lower()
                if lowered in {"test", "tests", "__tests__", "spec", "specs"}:
                    continue
                stack.append(entry)
                continue
            if not entry.is_file():
                continue
            suf = entry.suffix.lower()
            if suf not in suffixes:
                continue
            name = entry.name.lower()
            if name.endswith((".d.ts", ".min.js", ".min.css")):
                continue
            if any(
                name.endswith(x)
                for x in (".test.js", ".test.ts", ".test.tsx", ".spec.js", ".spec.ts", ".spec.tsx")
            ):
                continue
            try:
                if entry.stat().st_size > MAX_FILE_BYTES:
                    continue
            except OSError:
                continue
            yield entry


def node_text(source: bytes, node: object) -> str:
    start = getattr(node, "start_byte", None)
    end = getattr(node, "end_byte", None)
    if isinstance(start, int) and isinstance(end, int):
        return source[start:end].decode("utf-8", errors="replace")
    text = getattr(node, "text", None)
    if isinstance(text, bytes):
        return text.decode("utf-8", errors="replace")
    if isinstance(text, str):
        return text
    return ""


def make_fact(
    *,
    method: str,
    path: str,
    controller: str,
    action: str,
    repository_id: str,
    commit_sha: str,
    file_path: str,
    line: int,
    detector_id: str,
    detector_version: str,
    confidence: float,
    authz_policy: str | None = None,
    authz_source: AuthzSource = "unknown",
    framework: str = "",
    language: str = "",
    prefix_unresolved: bool = False,
) -> ApiOperationFact:
    http_method = method.strip().upper() or "GET"
    http_path = normalize_path(path)
    key = f"{http_method}:{http_path}:{controller}.{action}"
    fact = ApiOperationFact(
        operation_key=key,
        http_method=http_method,
        http_path=http_path,
        controller=controller,
        action=action,
        authz_policy=authz_policy,
        authz_source=authz_source,
        read_only=http_method in {"GET", "HEAD", "OPTIONS"},
        evidence=[
            Evidence(
                repository_id=repository_id,
                commit_sha=commit_sha,
                file_path=file_path,
                line_start=line,
                line_end=line,
                detector_id=detector_id,
                detector_version=detector_version,
                confidence=confidence,
                extracted_at=utc_now_iso(),
            )
        ],
    )
    # stash metadata on a private attr via summary? Keep in operation_key only.
    # Callers attach framework/language onto interface dict after merge if needed.
    del framework, language, prefix_unresolved
    return fact


def cheap_contains(source: bytes, tokens: tuple[bytes, ...]) -> bool:
    return any(t in source for t in tokens)
