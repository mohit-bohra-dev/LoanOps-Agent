"""Static .NET ASP.NET Core extractor — Roslyn primary (D5), regex interim."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from packages.eakg.models import (
    ApiOperationFact,
    AuthzSource,
    ConnectionFact,
    Evidence,
    PackageRefFact,
    ProxyFact,
    RepoInterface,
    RouteCompositionFact,
    ServiceUrlFact,
    TopicFact,
)

logger = logging.getLogger(__name__)

DETECTOR_ID = "dotnet_static"
DETECTOR_VERSION = "1.0.0"

_HTTP_ATTR = re.compile(
    r"\[Http(Get|Post|Put|Delete|Patch)(?:\(\"([^\"]*)\"\))?\]",
    re.IGNORECASE,
)
_ROUTE_ATTR = re.compile(r"\[Route\(\"([^\"]+)\"\)\]")
_AUTHORIZE = re.compile(
    r"\[Authorize(?:\([^\]]*Policy\s*=\s*([^\])\s,]+)[^\)]*\))?\]",
    re.IGNORECASE,
)
_ALLOW_ANON = re.compile(r"\[AllowAnonymous\]", re.IGNORECASE)
_CLASS = re.compile(
    r"(?:public\s+)?(?:partial\s+)?(?:abstract\s+)?class\s+(\w+Controller)\b"
)
_METHOD = re.compile(
    r"(?:public|protected)\s+(?:async\s+)?(?:virtual\s+)?(?:[\w.<>,\[\]\?]+\s+)+(\w+)\s*\("
)
_PKG_REF = re.compile(
    r'<PackageReference\s+Include="([^"]+)"(?:\s+Version="([^"]*)")?',
    re.IGNORECASE,
)
_SDK_WEB = re.compile(r'Sdk="Microsoft\.NET\.Sdk\.Web"', re.IGNORECASE)
_EXCLUDE = re.compile(r"<Compile\s+Remove=\"([^\"]+)\"", re.IGNORECASE)
_SERVICE_URL_OPT = re.compile(r"options\.Value\.(\w+Url)\b")
_SERVICE_URL_LAMBDA = re.compile(r"c\s*=>\s*c\.(\w+Url)\b")
_SERVICE_URL_STR = re.compile(r'"ServiceUrls:(\w+Url)"')
_APPSETTINGS_URL = re.compile(r'"(\w+Url)"\s*:\s*"([^"]*)"')
_TOPIC = re.compile(r'"(\w*TopicName)"\s*:\s*"([^"]+)"')
_CONN = re.compile(r'"(\w*(?:Context|ConnectionString|Connnection))"|connectionStrings\.(\w+)', re.I)
_PROXY_CLASS = re.compile(
    r"class\s+(\w+)\s*:\s*([^{]+Auth0ServiceProxy|[^{]+RestClient)\b"
)
_URL_KEY_IN_CTOR = re.compile(r"c\s*=>\s*c\.(\w+Url)|options\.Value\.(\w+Url)|AppSettings\.(\w+Url)")
_FORMAT_ROUTE = re.compile(
    r'(?:apiUrl|url|path)\s*=\s*String\.Format\(\s*"([^"]+)"\s*,\s*([^)]+)\)',
    re.IGNORECASE,
)
_CONST_ASSIGN = re.compile(r'(?:string|var)\s+(\w+)\s*=\s*"([^"]*)"')
_AUTH_PKG = re.compile(r"PNMAC\.AppServices\.AppAuth", re.IGNORECASE)


def _line_of(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def _rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _evidence(
    repo_id: str,
    commit: str,
    path: str,
    start: int,
    end: int,
    confidence: float,
) -> Evidence:
    return Evidence(
        repository_id=repo_id,
        commit_sha=commit,
        file_path=path,
        line_start=start,
        line_end=end,
        detector_id=DETECTOR_ID,
        detector_version=DETECTOR_VERSION,
        confidence=confidence,
    )


def _strip_block_comments(text: str) -> str:
    """Remove /* */ and line comments for coarse parsing; keep newlines for line nums."""
    # Keep structure for line numbers by replacing comment interiors with spaces
    out = []
    i = 0
    n = len(text)
    while i < n:
        if text.startswith("//", i):
            while i < n and text[i] != "\n":
                out.append(" ")
                i += 1
            continue
        if text.startswith("/*", i):
            i += 2
            while i < n and not text.startswith("*/", i):
                out.append("\n" if text[i] == "\n" else " ")
                i += 1
            i = min(i + 2, n)
            continue
        out.append(text[i])
        i += 1
    return "".join(out)


def _join_routes(class_route: str | None, action_route: str | None, http_template: str | None) -> str:
    parts: list[str] = []
    for p in (class_route, action_route, http_template):
        if not p:
            continue
        if p.startswith("/"):
            return p if p.startswith("/") else "/" + p
        parts.append(p.strip("/"))
    if not parts:
        return "/"
    path = "/" + "/".join(parts)
    # controller token
    return path


def extract_packages(
    repo_root: Path,
    *,
    repository_id: str,
    commit_sha: str,
) -> list[PackageRefFact]:
    facts: list[PackageRefFact] = []
    for csproj in repo_root.rglob("*.csproj"):
        if "test" in csproj.as_posix().lower() and "Tests" in csproj.name:
            # still include; consumers appear in WebApi too
            pass
        text = csproj.read_text(encoding="utf-8", errors="ignore")
        rel = _rel(csproj, repo_root)
        for m in _PKG_REF.finditer(text):
            line = _line_of(text, m.start())
            facts.append(
                PackageRefFact(
                    package_id=m.group(1),
                    version=m.group(2),
                    project_path=rel,
                    evidence=[_evidence(repository_id, commit_sha, rel, line, line, 1.0)],
                )
            )
    return facts


def extract_controllers(
    repo_root: Path,
    *,
    repository_id: str,
    commit_sha: str,
    api_project_path: str = "",
) -> list[ApiOperationFact]:
    facts: list[ApiOperationFact] = []
    search_roots: list[Path] = []
    if api_project_path:
        p = repo_root / api_project_path
        if p.is_dir():
            search_roots.append(p)
    if not search_roots:
        search_roots = [repo_root]

    excluded: set[str] = set()
    for csproj in repo_root.rglob("*.csproj"):
        text = csproj.read_text(encoding="utf-8", errors="ignore")
        for m in _EXCLUDE.finditer(text):
            excluded.add(m.group(1).replace("\\", "/"))

    for root in search_roots:
        for cs in root.rglob("*Controller.cs"):
            rel = _rel(cs, repo_root)
            if any(rel.endswith(ex) or ex in rel for ex in excluded):
                continue
            if "Startup_Old" in cs.name:
                continue
            raw = cs.read_text(encoding="utf-8", errors="ignore")
            # Skip fully commented controller files (Fees MSPWriteBack pattern)
            active = _strip_block_comments(raw)
            if "class " not in active and "partial class" not in active:
                continue
            class_m = _CLASS.search(active)
            if not class_m:
                continue
            controller = class_m.group(1)
            # class-level authorize / route — scan from class start to first method-ish
            class_start = class_m.start()
            # look backwards for attributes (up to 800 chars before class)
            preamble = active[max(0, class_start - 800) : class_start]
            class_routes = _ROUTE_ATTR.findall(preamble)
            class_route = class_routes[-1] if class_routes else None
            class_auth = None
            class_auth_source: AuthzSource | None = None
            if _AUTHORIZE.search(preamble):
                am = _AUTHORIZE.search(preamble)
                class_auth = (am.group(1) if am and am.group(1) else "Authorize").strip()
                class_auth_source = "class-level"
            if _ALLOW_ANON.search(preamble):
                class_auth = "AllowAnonymous"
                class_auth_source = "attribute"

            # Split roughly by Http* attributes
            for hm in _HTTP_ATTR.finditer(active):
                method = hm.group(1).upper()
                http_tmpl = hm.group(2)
                window_start = max(0, hm.start() - 400)
                window = active[window_start : hm.start() + 400]
                routes = _ROUTE_ATTR.findall(window)
                action_route = routes[-1] if routes else None
                # Method name may sit after many attributes (ProducesResponseType, etc.)
                after = active[hm.end() : hm.end() + 1200]
                mm = _METHOD.search(after)
                if not mm:
                    continue
                action = mm.group(1)
                if action in {"if", "while", "for", "return", "switch", "using"}:
                    continue
                # Skip if another [Http*] appears before the method (attribute binds elsewhere)
                next_http = _HTTP_ATTR.search(after)
                if next_http is not None and next_http.start() < mm.start():
                    continue
                path = _join_routes(class_route, action_route, http_tmpl)
                if "[controller]" in path:
                    ctrl_token = controller.replace("Controller", "")
                    path = path.replace("[controller]", ctrl_token)

                authz_policy = class_auth
                authz_source: AuthzSource = class_auth_source or "unknown"
                local_auth = _AUTHORIZE.search(window)
                if local_auth:
                    authz_policy = (local_auth.group(1) or "Authorize").strip()
                    authz_source = "attribute"
                if _ALLOW_ANON.search(window):
                    authz_policy = "AllowAnonymous"
                    authz_source = "attribute"

                line = _line_of(active, hm.start())
                key = f"{method}:{path}:{controller}.{action}"
                facts.append(
                    ApiOperationFact(
                        operation_key=key,
                        http_method=method,
                        http_path=path,
                        controller=controller,
                        action=action,
                        authz_policy=authz_policy,
                        authz_source=authz_source,
                        read_only=method == "GET",
                        evidence=[_evidence(repository_id, commit_sha, rel, line, line, 0.95)],
                    )
                )
    return facts


def extract_service_urls(
    repo_root: Path,
    *,
    repository_id: str,
    commit_sha: str,
) -> list[ServiceUrlFact]:
    facts: list[ServiceUrlFact] = []
    patterns = (
        (_SERVICE_URL_OPT, "options_value"),
        (_SERVICE_URL_LAMBDA, "lambda_member"),
        (_SERVICE_URL_STR, "string_literal"),
    )
    for path in list(repo_root.rglob("*.cs")) + list(repo_root.rglob("appsettings*.json")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        rel = _rel(path, repo_root)
        if path.suffix.lower() == ".json":
            for m in _APPSETTINGS_URL.finditer(text):
                line = _line_of(text, m.start())
                facts.append(
                    ServiceUrlFact(
                        key=m.group(1),
                        usage_kind="config",
                        evidence=[_evidence(repository_id, commit_sha, rel, line, line, 1.0)],
                    )
                )
            continue
        for pat, kind in patterns:
            for m in pat.finditer(text):
                line = _line_of(text, m.start())
                facts.append(
                    ServiceUrlFact(
                        key=m.group(1),
                        usage_kind=kind,
                        evidence=[_evidence(repository_id, commit_sha, rel, line, line, 0.9)],
                    )
                )
    return facts


def extract_proxies(
    repo_root: Path,
    *,
    repository_id: str,
    commit_sha: str,
) -> list[ProxyFact]:
    facts: list[ProxyFact] = []
    for path in repo_root.rglob("*.cs"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        rel = _rel(path, repo_root)
        for m in _PROXY_CLASS.finditer(text):
            cls = m.group(1)
            base = m.group(2).strip().split()[-1]
            # look ahead in class body for url key
            body = text[m.end() : m.end() + 1500]
            uk = _URL_KEY_IN_CTOR.search(body)
            url_key = None
            if uk:
                url_key = uk.group(1) or uk.group(2) or uk.group(3)
            line = _line_of(text, m.start())
            facts.append(
                ProxyFact(
                    class_name=cls,
                    base_class=base,
                    url_key=url_key,
                    evidence=[_evidence(repository_id, commit_sha, rel, line, line, 0.95)],
                )
            )
    return facts


def extract_topics(
    repo_root: Path,
    *,
    repository_id: str,
    commit_sha: str,
) -> list[TopicFact]:
    facts: list[TopicFact] = []
    for path in repo_root.rglob("appsettings*.json"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        rel = _rel(path, repo_root)
        for m in _TOPIC.finditer(text):
            line = _line_of(text, m.start())
            facts.append(
                TopicFact(
                    topic_key=m.group(1),
                    topic_value=m.group(2),
                    role="declare",
                    evidence=[_evidence(repository_id, commit_sha, rel, line, line, 1.0)],
                )
            )
    return facts


def extract_connections(
    repo_root: Path,
    *,
    repository_id: str,
    commit_sha: str,
) -> list[ConnectionFact]:
    facts: list[ConnectionFact] = []
    seen: set[str] = set()
    for path in list(repo_root.rglob("appsettings*.json")) + list(repo_root.rglob("*.cs")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        rel = _rel(path, repo_root)
        for m in _CONN.finditer(text):
            key = m.group(1) or m.group(2)
            if not key or key in seen:
                continue
            if "Url" in key and key.endswith("Url"):
                continue
            seen.add(key)
            line = _line_of(text, m.start())
            facts.append(
                ConnectionFact(
                    connection_key=key,
                    evidence=[_evidence(repository_id, commit_sha, rel, line, line, 0.9)],
                )
            )
    return facts


def _resolve_format(template: str, args_blob: str, locals_map: dict[str, str]) -> str:
    """Best-effort String.Format resolve for route composition."""
    args = [a.strip() for a in args_blob.split(",")]
    values: list[str] = []
    for a in args:
        if a in locals_map:
            values.append(locals_map[a])
        elif a.startswith('"') and a.endswith('"'):
            values.append(a[1:-1])
        else:
            values.append("{" + a + "}")
    try:
        return template.format(*values)
    except (IndexError, ValueError):
        # fallback: replace {0} style manually
        out = template
        for i, v in enumerate(values):
            out = out.replace("{" + str(i) + "}", v)
        return out


def extract_route_compositions(
    repo_root: Path,
    *,
    repository_id: str,
    commit_sha: str,
) -> list[RouteCompositionFact]:
    facts: list[RouteCompositionFact] = []
    for path in repo_root.rglob("*.cs"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        rel = _rel(path, repo_root)
        locals_map = {m.group(1): m.group(2) for m in _CONST_ASSIGN.finditer(text)}
        # also catch inline string api = "api", controllerName = "Loans"
        for m in re.finditer(r'(\w+)\s*=\s*"([^"]*)"', text):
            locals_map.setdefault(m.group(1), m.group(2))
        url_key = None
        uk = _URL_KEY_IN_CTOR.search(text) or _SERVICE_URL_OPT.search(text)
        if uk:
            url_key = next((g for g in uk.groups() if g), None)
        for m in _FORMAT_ROUTE.finditer(text):
            composed = _resolve_format(m.group(1), m.group(2), locals_map)
            line = _line_of(text, m.start())
            # find enclosing method name
            before = text[: m.start()]
            methods = list(_METHOD.finditer(before))
            symbol = methods[-1].group(1) if methods else path.stem
            facts.append(
                RouteCompositionFact(
                    caller_symbol=symbol,
                    composed_path=composed if composed.startswith("/") else "/" + composed,
                    http_method="GET",
                    url_key=url_key,
                    evidence=[_evidence(repository_id, commit_sha, rel, line, line, 0.7)],
                )
            )
    return facts


def build_interface(
    *,
    repository_id: str,
    application_id: str,
    commit_sha: str,
    packages: list[PackageRefFact],
    operations: list[ApiOperationFact],
    urls: list[ServiceUrlFact],
    topics: list[TopicFact],
    conns: list[ConnectionFact],
    proxies: list[ProxyFact],
    routes: list[RouteCompositionFact],
) -> RepoInterface:
    auth_pkgs = sorted(
        {p.package_id for p in packages if _AUTH_PKG.search(p.package_id)}
    )
    return RepoInterface(
        repository_id=repository_id,
        application_id=application_id,
        commit_sha=commit_sha,
        packages=[
            {"package_id": p.package_id, "version": p.version, "project": p.project_path}
            for p in packages
        ],
        operations=[
            {
                "key": o.operation_key,
                "method": o.http_method,
                "path": o.http_path,
                "controller": o.controller,
                "action": o.action,
                "authz_policy": o.authz_policy,
                "authz_source": o.authz_source,
                "read_only": o.read_only,
            }
            for o in operations
        ],
        service_url_keys=sorted({u.key for u in urls}),
        topics=[
            {"key": t.topic_key, "value": t.topic_value, "role": t.role} for t in topics
        ],
        connection_keys=sorted({c.connection_key for c in conns}),
        proxies=[
            {"class": p.class_name, "base": p.base_class, "url_key": p.url_key} for p in proxies
        ],
        route_compositions=[
            {
                "caller": r.caller_symbol,
                "path": r.composed_path,
                "method": r.http_method,
                "url_key": r.url_key,
            }
            for r in routes
        ],
        auth_packages=auth_pkgs,
    )


def extract_repo(
    repo_root: str | Path,
    *,
    repository_id: str,
    application_id: str,
    commit_sha: str,
    api_project_path: str = "",
    extractor: str | None = None,
) -> tuple[RepoInterface, dict[str, object]]:
    root = Path(repo_root)
    mode = (extractor or "").strip().lower()
    if not mode:
        try:
            from packages.common.settings import Settings

            mode = Settings().eakg.extractor
        except Exception:  # noqa: BLE001
            mode = "auto"
    if mode not in {"auto", "roslyn", "regex"}:
        mode = "auto"

    packages = extract_packages(root, repository_id=repository_id, commit_sha=commit_sha)
    operations: list[ApiOperationFact] = []
    op_detector = DETECTOR_ID
    if mode in {"auto", "roslyn"}:
        try:
            from packages.eakg.extractors.roslyn import (
                DETECTOR_ID as ROSLYN_ID,
            )
            from packages.eakg.extractors.roslyn import extract_controllers_roslyn

            operations = extract_controllers_roslyn(
                root,
                repository_id=repository_id,
                commit_sha=commit_sha,
                api_project_path=api_project_path,
            )
            op_detector = ROSLYN_ID
            logger.info(
                "eakg extractor=roslyn ops=%s repo=%s", len(operations), repository_id
            )
        except Exception as exc:  # noqa: BLE001
            if mode == "roslyn":
                raise
            logger.warning("roslyn extract failed (%s); falling back to regex", exc)
            operations = []
    if not operations:
        operations = extract_controllers(
            root,
            repository_id=repository_id,
            commit_sha=commit_sha,
            api_project_path=api_project_path,
        )
        op_detector = DETECTOR_ID
        logger.info(
            "eakg extractor=regex ops=%s repo=%s", len(operations), repository_id
        )

    urls = extract_service_urls(root, repository_id=repository_id, commit_sha=commit_sha)
    topics = extract_topics(root, repository_id=repository_id, commit_sha=commit_sha)
    conns = extract_connections(root, repository_id=repository_id, commit_sha=commit_sha)
    proxies = extract_proxies(root, repository_id=repository_id, commit_sha=commit_sha)
    routes = extract_route_compositions(
        root, repository_id=repository_id, commit_sha=commit_sha
    )
    iface = build_interface(
        repository_id=repository_id,
        application_id=application_id,
        commit_sha=commit_sha,
        packages=packages,
        operations=operations,
        urls=urls,
        topics=topics,
        conns=conns,
        proxies=proxies,
        routes=routes,
    )
    details: dict[str, object] = {
        "packages": packages,
        "operations": operations,
        "urls": urls,
        "topics": topics,
        "conns": conns,
        "proxies": proxies,
        "routes": routes,
        "extractor": op_detector,
    }
    return iface, details
