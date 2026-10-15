"""Express / Fastify route extraction via tree-sitter (JS/TS)."""

from __future__ import annotations

from pathlib import Path

from packages.eakg.extractors.treesitter.common import (
    cheap_contains,
    iter_source_files,
    make_fact,
    node_text,
)
from packages.eakg.models import ApiOperationFact
from tree_sitter import Language, Node, Parser

DETECTOR_ID = "treesitter_node"
DETECTOR_VERSION = "1.0.0"

_HTTP = frozenset({"get", "post", "put", "delete", "patch", "head", "options"})
_TOKENS = (b"express", b"fastify", b".get(", b".post(", b".route(")


def _js_parser() -> Parser:
    import tree_sitter_javascript as tsjs

    return Parser(Language(tsjs.language()))


def _ts_parser(*, tsx: bool) -> Parser:
    import tree_sitter_typescript as tsts

    lang = tsts.language_tsx() if tsx else tsts.language_typescript()
    return Parser(Language(lang))


def _string_literal(source: bytes, node: Node | None) -> str | None:
    if node is None:
        return None
    if node.type in {"string", "string_fragment", "template_string"}:
        raw = node_text(source, node)
        if node.type == "template_string":
            # only accept no interpolation
            if "${" in raw:
                return None
            return raw.strip("`")
        if len(raw) >= 2 and raw[0] in "\"'" and raw[-1] == raw[0]:
            return raw[1:-1]
    return None


def _callee_parts(source: bytes, node: Node) -> list[str]:
    if node.type == "member_expression":
        obj = node.child_by_field_name("object")
        prop = node.child_by_field_name("property")
        left = _callee_parts(source, obj) if obj is not None else []
        right = node_text(source, prop) if prop is not None else ""
        return [*left, right] if right else left
    if node.type == "call_expression":
        # Unwrap app.route(...).get — object of member is a call
        inner = node.child_by_field_name("function")
        return _callee_parts(source, inner) if inner is not None else []
    if node.type in {"identifier", "property_identifier"}:
        return [node_text(source, node)]
    return []


def _has_framework_import(source: bytes) -> tuple[bool, bool]:
    text = source.lower()
    return b"express" in text, b"fastify" in text


def _is_callable_arg(node: Node) -> bool:
    return node.type in {
        "identifier",
        "arrow_function",
        "function_expression",
        "function",
        "member_expression",
        "parenthesized_expression",
        "call_expression",
    }


def _handler_name(source: bytes, node: Node) -> str:
    if node.type == "identifier":
        return node_text(source, node)
    if node.type == "member_expression":
        prop = node.child_by_field_name("property")
        if prop is not None:
            return node_text(source, prop)
    return "handler"


def _collect_use_prefixes(source: bytes, root: Node) -> dict[str, str]:
    """app.use('/api', router) → router var prefix."""
    prefixes: dict[str, str] = {}
    stack: list[Node] = [root]
    while stack:
        node = stack.pop()
        stack.extend(reversed(node.named_children))
        if node.type != "call_expression":
            continue
        func = node.child_by_field_name("function")
        args = node.child_by_field_name("arguments")
        if func is None or args is None:
            continue
        parts = _callee_parts(source, func)
        if len(parts) < 2 or parts[-1] != "use":
            continue
        named = [c for c in args.named_children]
        if len(named) < 2:
            continue
        prefix = _string_literal(source, named[0])
        router = named[1]
        if prefix is None or router.type != "identifier":
            continue
        prefixes[node_text(source, router)] = prefix
    return prefixes


def _extract_from_tree(
    source: bytes,
    root: Node,
    *,
    rel: str,
    repository_id: str,
    commit_sha: str,
) -> tuple[list[ApiOperationFact], list[str]]:
    warnings: list[str] = []
    facts: list[ApiOperationFact] = []
    has_express, has_fastify = _has_framework_import(source)
    if not has_express and not has_fastify:
        return [], []
    prefixes = _collect_use_prefixes(source, root)
    controller = Path(rel).stem
    stack: list[Node] = [root]
    while stack:
        node = stack.pop()
        stack.extend(reversed(node.named_children))
        if node.type != "call_expression":
            continue
        func = node.child_by_field_name("function")
        args = node.child_by_field_name("arguments")
        if func is None or args is None:
            continue
        # Express app.route(path).get(handler) before callee-parts length check
        if (
            has_express
            and func.type == "member_expression"
            and func.child_by_field_name("object") is not None
            and func.child_by_field_name("object").type == "call_expression"  # type: ignore[union-attr]
        ):
            prop = func.child_by_field_name("property")
            obj_call = func.child_by_field_name("object")
            if (
                prop is not None
                and obj_call is not None
                and node_text(source, prop).lower() in _HTTP
            ):
                inner_func = obj_call.child_by_field_name("function")
                inner_args = obj_call.child_by_field_name("arguments")
                if inner_func is not None and inner_args is not None:
                    inner_parts = _callee_parts(source, inner_func)
                    if len(inner_parts) >= 1 and inner_parts[-1].lower() == "route":
                        route_path = None
                        for child in inner_args.named_children:
                            route_path = _string_literal(source, child)
                            if route_path is not None:
                                break
                        named_args = list(args.named_children)
                        if route_path is not None and named_args:
                            owner = inner_parts[-2] if len(inner_parts) >= 2 else ""
                            prefix = prefixes.get(owner, "")
                            full = (
                                f"{prefix.rstrip('/')}/{route_path.lstrip('/')}"
                                if prefix
                                else route_path
                            )
                            facts.append(
                                make_fact(
                                    method=node_text(source, prop).upper(),
                                    path=full,
                                    controller=controller,
                                    action=_handler_name(source, named_args[-1]),
                                    repository_id=repository_id,
                                    commit_sha=commit_sha,
                                    file_path=rel,
                                    line=node.start_point[0] + 1,
                                    detector_id=DETECTOR_ID,
                                    detector_version=DETECTOR_VERSION,
                                    confidence=0.85,
                                    framework="Express",
                                    language="javascript",
                                )
                            )
                            continue

        parts = _callee_parts(source, func)
        if len(parts) < 2:
            continue
        owner, meth = parts[-2], parts[-1].lower()

        # Fastify route({ method, url, handler }) — object form only
        if meth == "route" and has_fastify:
            obj = None
            for child in args.named_children:
                if child.type == "object":
                    obj = child
                    break
            if obj is None:
                # Express router.route(path) string form — handled via .get chain above
                continue
            method_val: str | None = None
            url_val: str | None = None
            handler_name = "handler"
            for prop in obj.named_children:
                if prop.type != "pair":
                    continue
                key_node = prop.child_by_field_name("key")
                val_node = prop.child_by_field_name("value")
                if key_node is None or val_node is None:
                    continue
                key = node_text(source, key_node).strip("\"'")
                if key in {"method", "methods"}:
                    method_val = _string_literal(source, val_node)
                    if method_val is None and val_node.type == "array":
                        # take first
                        for el in val_node.named_children:
                            method_val = _string_literal(source, el)
                            if method_val:
                                break
                elif key == "url":
                    url_val = _string_literal(source, val_node)
                elif key == "handler":
                    handler_name = _handler_name(source, val_node)
            if not method_val or not url_val:
                continue
            line = node.start_point[0] + 1
            facts.append(
                make_fact(
                    method=method_val,
                    path=url_val,
                    controller=controller,
                    action=handler_name,
                    repository_id=repository_id,
                    commit_sha=commit_sha,
                    file_path=rel,
                    line=line,
                    detector_id=DETECTOR_ID,
                    detector_version=DETECTOR_VERSION,
                    confidence=0.85,
                    framework="Fastify",
                    language="javascript",
                )
            )
            continue

        if meth not in _HTTP and meth != "route":
            continue

        named_args = list(args.named_children)
        # Express app.get(path, handler) — reject app.get('env') (1 string arg)
        if meth in _HTTP:
            if len(named_args) < 2:
                continue
            path_arg = named_args[0]
            handler_arg = named_args[-1]
            route_path = _string_literal(source, path_arg)
            if route_path is None:
                continue
            if not _is_callable_arg(handler_arg):
                continue
            # Fastify also uses .get(path, handler)
            framework = "Express" if has_express else "Fastify"
            prefix = prefixes.get(owner, "")
            full = f"{prefix.rstrip('/')}/{route_path.lstrip('/')}" if prefix else route_path
            conf = 0.85
            if owner not in prefixes and owner not in {
                "app",
                "router",
                "server",
                "fastify",
                "api",
            }:
                conf = 0.6
                warnings.append(f"{rel}: unresolved router prefix for '{owner}'")
            line = node.start_point[0] + 1
            facts.append(
                make_fact(
                    method=meth.upper(),
                    path=full,
                    controller=controller,
                    action=_handler_name(source, handler_arg),
                    repository_id=repository_id,
                    commit_sha=commit_sha,
                    file_path=rel,
                    line=line,
                    detector_id=DETECTOR_ID,
                    detector_version=DETECTOR_VERSION,
                    confidence=conf,
                    framework=framework,
                    language="javascript",
                    prefix_unresolved=conf < 0.7,
                )
            )
            continue
    return facts, warnings


def extract_node_routes(
    repo: Path,
    *,
    repository_id: str,
    commit_sha: str,
    api_project_path: str = "",
) -> tuple[list[ApiOperationFact], list[str]]:
    warnings: list[str] = []
    facts: list[ApiOperationFact] = []
    try:
        js_parser = _js_parser()
        ts_parser = _ts_parser(tsx=False)
        tsx_parser = _ts_parser(tsx=True)
    except Exception as exc:  # noqa: BLE001
        return [], [f"tree-sitter JS/TS unavailable: {exc}"]

    suffixes = frozenset({".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"})
    for path in iter_source_files(
        repo, suffixes=suffixes, api_project_path=api_project_path
    ):
        try:
            source = path.read_bytes()
        except OSError:
            continue
        if not cheap_contains(source, _TOKENS):
            continue
        suf = path.suffix.lower()
        if suf == ".tsx":
            parser = tsx_parser
        elif suf == ".ts":
            parser = ts_parser
        else:
            parser = js_parser
        tree = parser.parse(source)
        rel = str(path.relative_to(repo)).replace("\\", "/")
        file_facts, file_warns = _extract_from_tree(
            source,
            tree.root_node,
            rel=rel,
            repository_id=repository_id,
            commit_sha=commit_sha,
        )
        facts.extend(file_facts)
        warnings.extend(file_warns)
    return facts, warnings
