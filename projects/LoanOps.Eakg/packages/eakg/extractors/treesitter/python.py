"""FastAPI / Flask route extraction via tree-sitter."""

from __future__ import annotations

from pathlib import Path

from packages.eakg.extractors.treesitter.common import (
    cheap_contains,
    iter_source_files,
    make_fact,
    node_text,
)
from packages.eakg.models import ApiOperationFact, AuthzSource
from tree_sitter import Language, Node, Parser

DETECTOR_ID = "treesitter_python"
DETECTOR_VERSION = "1.0.0"

_HTTP = frozenset({"get", "post", "put", "delete", "patch", "head", "options"})
_TOKENS = (b"fastapi", b"flask", b"APIRouter", b"Blueprint", b"@app.", b"@router.")


def _parser() -> Parser:
    import tree_sitter_python as tspython

    return Parser(Language(tspython.language()))


def _string_literal(source: bytes, node: Node | None) -> str | None:
    if node is None:
        return None
    if node.type == "string":
        raw = node_text(source, node)
        if len(raw) >= 2 and raw[0] in "\"'" and raw[-1] == raw[0]:
            return raw[1:-1]
        if raw.startswith(('"""', "'''")) and len(raw) >= 6:
            return raw[3:-3]
        return raw.strip("\"'")
    if node.type == "concatenated_string":
        parts: list[str] = []
        for child in node.children:
            part = _string_literal(source, child)
            if part is None:
                return None
            parts.append(part)
        return "".join(parts)
    return None


def _attr_parts(source: bytes, node: Node) -> list[str]:
    if node.type == "attribute":
        obj = node.child_by_field_name("object")
        attr = node.child_by_field_name("attribute")
        left = _attr_parts(source, obj) if obj is not None else []
        right = node_text(source, attr) if attr is not None else ""
        return [*left, right] if right else left
    if node.type == "identifier":
        return [node_text(source, node)]
    return []


def _decorator_call(source: bytes, dec: Node) -> Node | None:
    # decorator: '@' call  OR  '@' identifier / attribute
    for child in dec.children:
        if child.type == "call":
            return child
    return None


def _methods_from_kwargs(source: bytes, call: Node) -> list[str]:
    args = call.child_by_field_name("arguments")
    if args is None:
        return []
    for child in args.children:
        if child.type != "keyword_argument":
            continue
        name_node = child.child_by_field_name("name")
        if name_node is None or node_text(source, name_node) != "methods":
            continue
        val = child.child_by_field_name("value")
        if val is None:
            continue
        methods: list[str] = []
        if val.type == "list":
            for el in val.children:
                s = _string_literal(source, el)
                if s:
                    methods.append(s.upper())
        return methods
    return []


def _first_string_arg(source: bytes, call: Node) -> str | None:
    args = call.child_by_field_name("arguments")
    if args is None:
        return None
    for child in args.named_children:
        if child.type == "keyword_argument":
            continue
        s = _string_literal(source, child)
        if s is not None:
            return s
    return None


def _imports_gate(source: bytes) -> tuple[bool, bool]:
    text = source.lower()
    has_fastapi = b"fastapi" in text
    has_flask = b"flask" in text
    return has_fastapi, has_flask


def _collect_prefixes(source: bytes, root: Node) -> dict[str, str]:
    """Same-file APIRouter(prefix=) / Blueprint(..., url_prefix=)."""
    prefixes: dict[str, str] = {}
    stack: list[Node] = [root]
    while stack:
        node = stack.pop()
        stack.extend(reversed(node.named_children))
        if node.type != "assignment":
            continue
        left = node.child_by_field_name("left")
        right = node.child_by_field_name("right")
        if left is None or right is None or right.type != "call":
            continue
        name = node_text(source, left) if left.type == "identifier" else ""
        if not name:
            continue
        func = right.child_by_field_name("function")
        if func is None:
            continue
        fname = node_text(source, func)
        if (
            fname not in {"APIRouter", "Blueprint"}
            and not fname.endswith(".APIRouter")
            and "Blueprint" not in fname
            and "APIRouter" not in fname
        ):
            continue
        args = right.child_by_field_name("arguments")
        if args is None:
            continue
        for child in args.children:
            if child.type != "keyword_argument":
                continue
            kn = child.child_by_field_name("name")
            if kn is None:
                continue
            kn_text = node_text(source, kn)
            if kn_text not in {"prefix", "url_prefix"}:
                continue
            val = child.child_by_field_name("value")
            s = _string_literal(source, val)
            if s is not None:
                prefixes[name] = s
    return prefixes


def _function_name(source: bytes, decorated: Node) -> str:
    for child in decorated.named_children:
        if child.type == "function_definition":
            name = child.child_by_field_name("name")
            if name is not None:
                return node_text(source, name)
    return "handler"


def _has_login_required(source: bytes, decorated: Node) -> bool:
    for child in decorated.named_children:
        if child.type != "decorator":
            continue
        text = node_text(source, child)
        if "login_required" in text:
            return True
    return False


def extract_python_routes(
    repo: Path,
    *,
    repository_id: str,
    commit_sha: str,
    api_project_path: str = "",
) -> tuple[list[ApiOperationFact], list[str]]:
    warnings: list[str] = []
    facts: list[ApiOperationFact] = []
    try:
        parser = _parser()
    except Exception as exc:  # noqa: BLE001
        return [], [f"tree-sitter-python unavailable: {exc}"]

    for path in iter_source_files(
        repo, suffixes=frozenset({".py"}), api_project_path=api_project_path
    ):
        try:
            source = path.read_bytes()
        except OSError:
            continue
        if not cheap_contains(source, _TOKENS):
            continue
        has_fastapi, has_flask = _imports_gate(source)
        if not has_fastapi and not has_flask:
            continue
        tree = parser.parse(source)
        root = tree.root_node
        prefixes = _collect_prefixes(source, root)
        rel = str(path.relative_to(repo)).replace("\\", "/")
        controller = path.stem
        stack: list[Node] = [root]
        while stack:
            node = stack.pop()
            stack.extend(reversed(node.named_children))
            if node.type != "decorated_definition":
                continue
            action = _function_name(source, node)
            authz_policy: str | None = None
            authz_source: AuthzSource = "unknown"
            if _has_login_required(source, node):
                authz_policy = "login_required"
                authz_source = "attribute"
            for child in node.named_children:
                if child.type != "decorator":
                    continue
                call = _decorator_call(source, child)
                if call is None:
                    continue
                func = call.child_by_field_name("function")
                if func is None:
                    continue
                parts = _attr_parts(source, func)
                if len(parts) < 2:
                    continue
                owner, meth = parts[-2], parts[-1].lower()
                route_path = _first_string_arg(source, call)
                if route_path is None:
                    continue
                methods: list[str] = []
                framework = ""
                if meth in _HTTP:
                    methods = [meth.upper()]
                    framework = "FastAPI" if has_fastapi else "Flask"
                elif meth == "route":
                    methods = _methods_from_kwargs(source, call) or ["GET"]
                    framework = "Flask" if has_flask else "FastAPI"
                else:
                    continue
                prefix = prefixes.get(owner, "")
                if owner in prefixes or owner in {"app", "router", "api", "blueprint", "bp"}:
                    if prefix:
                        full = f"{prefix.rstrip('/')}/{route_path.lstrip('/')}"
                    else:
                        full = route_path
                    conf = 0.9
                else:
                    # unknown router variable — emit path as written
                    full = route_path
                    conf = 0.6
                    warnings.append(f"{rel}: unresolved router prefix for '{owner}'")
                line = child.start_point[0] + 1
                for http_method in methods:
                    facts.append(
                        make_fact(
                            method=http_method,
                            path=full,
                            controller=controller,
                            action=action,
                            repository_id=repository_id,
                            commit_sha=commit_sha,
                            file_path=rel,
                            line=line,
                            detector_id=DETECTOR_ID,
                            detector_version=DETECTOR_VERSION,
                            confidence=conf,
                            authz_policy=authz_policy,
                            authz_source=authz_source,
                            framework=framework,
                            language="python",
                            prefix_unresolved=conf < 0.7,
                        )
                    )
    return facts, warnings
