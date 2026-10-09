"""Two-stage API operation search (spec §3.5)."""

from __future__ import annotations

import math
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from packages.api_index.indexer import IndexManifest, load_manifest, namespace_for
from packages.api_index.keyword_index import KeywordIndex, unified_to_api_operation
from packages.api_index.metrics import record_metric
from packages.api_index.records import UnifiedOperation
from packages.common.providers.embedding import EmbeddingProvider
from packages.common.providers.vector_store import SearchResult, VectorStoreProvider
from packages.sse.semantic import OpenApiEmbeddingEntry, load_openapi_index

_MIN_CONFIDENT_SCORE = 0.35
_MIN_KEYWORD_CONFIDENT = 0.5
_QUERY_EMBED_LRU = 1024
_PROBE_TOP_K = 60
_SHORTLIST_CAP = 8

BackendLabel = Literal["vector_index", "sidecar", "keyword"]


class SearchHit(BaseModel):
    record: UnifiedOperation
    score: float
    vector_score: float | None = None
    keyword_score: float | None = None


class SearchOutcome(BaseModel):
    hits: list[SearchHit] = Field(default_factory=list)
    backend: BackendLabel = "keyword"
    confident: bool = False
    shortlist: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


def backend_header(backend: BackendLabel) -> str:
    if backend == "vector_index":
        return "(vector index)"
    if backend == "sidecar":
        return "(fallback: local vector sidecar)"
    return "(keyword search — embeddings unavailable)"


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b, strict=True):
        dot += x * y
        na += x * x
        nb += y * y
    if na <= 0.0 or nb <= 0.0:
        return 0.0
    return dot / math.sqrt(na * nb)


def _mean_top3(scores: list[float]) -> float:
    if not scores:
        return 0.0
    top = sorted(scores, reverse=True)[:3]
    return sum(top) / float(len(top))


class ApiSearchService:
    """Two-stage vector shortlist + keyword blend with defensive post-filter."""

    def __init__(
        self,
        *,
        operations: list[UnifiedOperation],
        keyword_index: KeywordIndex,
        vector_store: VectorStoreProvider | None,
        embedder: EmbeddingProvider | None,
        environment: str,
        namespace_prefix: str,
        app_shortlist_size: int = 5,
        manifest_path: Path | None = None,
        sidecar_path: Path | None = None,
        allowed_permissions: frozenset[str] | None = None,
        enforce_permissions: bool = False,
    ) -> None:
        self._ops = list(operations)
        self._by_uid = {op.uid: op for op in self._ops}
        self._by_public = {op.public_id: op for op in self._ops}
        self._keyword = keyword_index
        self._vs = vector_store
        self._embedder = embedder
        self._environment = environment
        self._namespace_prefix = namespace_prefix
        self._app_shortlist_size = max(1, min(20, app_shortlist_size))
        self._manifest_path = manifest_path
        self._sidecar_path = sidecar_path
        self._allowed_permissions = allowed_permissions or frozenset()
        self._enforce_permissions = enforce_permissions
        self._query_cache: OrderedDict[str, list[float]] = OrderedDict()
        self._model_mismatch = False
        self._live_model_id = ""
        self._manifest_model_id = ""
        self._namespace = ""
        self._sidecar: dict[str, OpenApiEmbeddingEntry] = {}
        self._refresh_manifest_state()

    def _refresh_manifest_state(self) -> None:
        manifest = (
            load_manifest(self._manifest_path)
            if self._manifest_path is not None
            else IndexManifest()
        )
        self._manifest_model_id = manifest.embed_model_id
        self._namespace = manifest.namespace
        if self._sidecar_path is not None:
            self._sidecar = load_openapi_index(self._sidecar_path)
        else:
            self._sidecar = {}

    def invalidate_catalog(
        self,
        operations: list[UnifiedOperation],
        keyword_index: KeywordIndex,
    ) -> None:
        self._ops = list(operations)
        self._by_uid = {op.uid: op for op in self._ops}
        self._by_public = {op.public_id: op for op in self._ops}
        self._keyword = keyword_index
        self._refresh_manifest_state()
        self._query_cache.clear()

    async def _ensure_model(self) -> None:
        if self._embedder is None:
            self._model_mismatch = True
            return
        probe = await self._embedder.embed("probe")
        self._live_model_id = f"{probe.model}:{probe.dimensions}"
        if self._manifest_model_id and self._live_model_id != self._manifest_model_id:
            self._model_mismatch = True
        else:
            self._model_mismatch = False
        if not self._namespace and self._live_model_id:
            self._namespace = namespace_for(
                self._namespace_prefix, self._environment, self._live_model_id
            )

    async def _embed_cached(self, query: str) -> list[float]:
        if self._embedder is None:
            raise RuntimeError("embedder unavailable")
        key = query.lower()
        cached = self._query_cache.get(key)
        if cached is not None:
            self._query_cache.move_to_end(key)
            return cached
        result = await self._embedder.embed(query)
        vec = list(result.vector)
        self._query_cache[key] = vec
        while len(self._query_cache) > _QUERY_EMBED_LRU:
            self._query_cache.popitem(last=False)
        return vec

    def _permission_ok(self, meta: dict[str, Any], permission: str | None) -> bool:
        if permission:
            needed = permission.strip().lower()
            got = str(meta.get("permission") or "").strip().lower()
            if got != needed:
                return False
        if self._enforce_permissions and self._allowed_permissions:
            got = str(meta.get("permission") or "").strip().lower()
            if got and got not in {p.lower() for p in self._allowed_permissions}:
                return False
        return True

    def _post_filter(
        self,
        meta: dict[str, Any],
        *,
        shortlist: set[str],
        permission: str | None,
    ) -> bool:
        if meta.get("read_only") is not True:
            return False
        app = str(meta.get("application_id") or "")
        if shortlist and app not in shortlist:
            return False
        return self._permission_ok(meta, permission)

    def _keyword_only(
        self,
        query: str,
        *,
        limit: int,
        shortlist: list[str],
        permission: str | None,
        warnings: list[str],
    ) -> SearchOutcome:
        scored = self._keyword.score(query, apps=shortlist or None, limit=max(3 * limit, limit))
        short_set = set(shortlist)
        hits: list[SearchHit] = []
        for uid, kw in sorted(
            scored.items(),
            key=lambda kv: (-kv[1], self._by_uid[kv[0]].public_id if kv[0] in self._by_uid else kv[0]),
        ):
            op = self._by_uid.get(uid)
            if op is None:
                continue
            meta = {
                "read_only": op.read_only,
                "application_id": op.application_id,
                "permission": op.permission,
            }
            if not self._post_filter(meta, shortlist=short_set, permission=permission):
                continue
            hits.append(SearchHit(record=op, score=kw, keyword_score=kw, vector_score=None))
            if len(hits) >= limit:
                break
        confident = bool(hits) and hits[0].score >= _MIN_KEYWORD_CONFIDENT
        return SearchOutcome(
            hits=hits[:limit],
            backend="keyword",
            confident=confident,
            shortlist=shortlist,
            warnings=warnings,
        )

    async def _sidecar_search(
        self,
        query: str,
        qvec: list[float],
        *,
        limit: int,
        shortlist: list[str],
        permission: str | None,
        warnings: list[str],
    ) -> SearchOutcome:
        short = set(shortlist) if shortlist else set()
        kw = self._keyword.score(query, apps=shortlist or None, limit=max(3 * limit, limit))
        cand: dict[str, float] = {}
        vec_scores: dict[str, float] = {}
        for public_id, entry in self._sidecar.items():
            op = self._by_public.get(public_id)
            if op is None:
                continue
            meta = {
                "read_only": op.read_only,
                "application_id": op.application_id,
                "permission": op.permission,
            }
            if not self._post_filter(meta, shortlist=short if short else {op.application_id}, permission=permission):
                if short and op.application_id not in short:
                    continue
                if not op.read_only:
                    continue
                if not self._permission_ok(meta, permission):
                    continue
            cos = _cosine(qvec, entry.vector)
            vec_scores[op.uid] = cos
            cand[op.uid] = 0.7 * cos
        for uid, k in kw.items():
            cand[uid] = cand.get(uid, 0.0) + 0.3 * k
        ordered = sorted(
            cand.items(),
            key=lambda kv: (
                -kv[1],
                self._by_uid[kv[0]].public_id if kv[0] in self._by_uid else kv[0],
            ),
        )
        hits: list[SearchHit] = []
        for uid, score in ordered:
            op = self._by_uid.get(uid)
            if op is None:
                continue
            meta = {
                "read_only": op.read_only,
                "application_id": op.application_id,
                "permission": op.permission,
            }
            if not self._post_filter(meta, shortlist=short, permission=permission):
                continue
            hits.append(
                SearchHit(
                    record=op,
                    score=score,
                    vector_score=vec_scores.get(uid),
                    keyword_score=kw.get(uid),
                )
            )
            if len(hits) >= limit:
                break
        confident = bool(hits) and hits[0].score >= _MIN_CONFIDENT_SCORE
        return SearchOutcome(
            hits=hits,
            backend="sidecar",
            confident=confident,
            shortlist=shortlist,
            warnings=warnings,
        )

    async def search(
        self,
        query: str,
        *,
        limit: int = 15,
        application_ids: list[str] | None = None,
        permission: str | None = None,
    ) -> SearchOutcome:
        started = time.perf_counter()
        outcome = await self._search_body(
            query,
            limit=limit,
            application_ids=application_ids,
            permission=permission,
        )
        await record_metric(
            "api_index.search.latency_ms",
            (time.perf_counter() - started) * 1000.0,
            unit="ms",
            attributes={"backend": outcome.backend},
        )
        await record_metric(
            "api_index.search.shortlist_size",
            float(len(outcome.shortlist)),
            unit="1",
            attributes={"backend": outcome.backend},
        )
        return outcome

    async def _search_body(
        self,
        query: str,
        *,
        limit: int = 15,
        application_ids: list[str] | None = None,
        permission: str | None = None,
    ) -> SearchOutcome:
        q = query.strip()
        warnings: list[str] = []
        if not q:
            return SearchOutcome(hits=[], backend="keyword", confident=False)

        try:
            await self._ensure_model()
        except Exception:  # noqa: BLE001
            warnings.append("embed_unavailable")
            return self._keyword_only(
                q, limit=limit, shortlist=list(application_ids or []), permission=permission, warnings=warnings
            )

        if self._model_mismatch:
            warnings.append("embed_model_mismatch")
            if self._sidecar and self._manifest_model_id:
                # sidecar may still match if written with same model as live
                try:
                    qvec = await self._embed_cached(q)
                    shortlist = list(application_ids or [])
                    if not shortlist:
                        shortlist = self._keyword.exact_name_apps(q)[:_SHORTLIST_CAP]
                    return await self._sidecar_search(
                        q, qvec, limit=limit, shortlist=shortlist, permission=permission, warnings=warnings
                    )
                except Exception:  # noqa: BLE001
                    pass
            return self._keyword_only(
                q, limit=limit, shortlist=list(application_ids or []), permission=permission, warnings=warnings
            )

        try:
            qvec = await self._embed_cached(q)
        except Exception:  # noqa: BLE001
            warnings.append("embed_unavailable")
            return self._keyword_only(
                q, limit=limit, shortlist=list(application_ids or []), permission=permission, warnings=warnings
            )

        if application_ids:
            shortlist = list(dict.fromkeys(application_ids))
        else:
            shortlist = await self._probe_shortlist(qvec, q)

        if self._vs is None:
            warnings.append("vector_store_unavailable")
            return await self._sidecar_search(
                q, qvec, limit=limit, shortlist=shortlist, permission=permission, warnings=warnings
            )

        vs_any_of = bool(getattr(self._vs, "supports_any_of_filter", False))
        base_filter: dict[str, Any] = {"read_only": True}
        try:
            if vs_any_of and shortlist:
                vec_hits = await self._vs.search(
                    qvec,
                    namespace=self._namespace or "default",
                    top_k=max(4 * limit, 40),
                    filter={**base_filter, "application_id": list(shortlist)},
                )
            else:
                vec_hits = await self._vs.search(
                    qvec,
                    namespace=self._namespace or "default",
                    top_k=max(8 * limit, 120),
                    filter=base_filter,
                )
        except Exception:  # noqa: BLE001
            warnings.append("vector_store_unavailable")
            return await self._sidecar_search(
                q, qvec, limit=limit, shortlist=shortlist, permission=permission, warnings=warnings
            )

        short_set = set(shortlist)
        filtered: list[SearchResult] = []
        for hit in vec_hits:
            meta = dict(hit.metadata or {})
            # Always post-filter (product rule), even when provider supports any-of.
            if self._post_filter(meta, shortlist=short_set, permission=permission):
                filtered.append(hit)

        kw = self._keyword.score(query=q, apps=shortlist, limit=max(3 * limit, limit))
        cand: dict[str, float] = {}
        vec_scores: dict[str, float] = {}
        for hit in filtered:
            uid = str((hit.metadata or {}).get("uid") or "")
            if not uid:
                # fall back to public_id lookup
                public_id = str((hit.metadata or {}).get("public_id") or hit.id)
                op = self._by_public.get(public_id)
                uid = op.uid if op else ""
            if not uid:
                continue
            vec_scores[uid] = float(hit.score)
            cand[uid] = 0.7 * float(hit.score)
        for uid, k in kw.items():
            cand[uid] = cand.get(uid, 0.0) + 0.3 * k

        ordered = sorted(
            cand.items(),
            key=lambda kv: (
                -kv[1],
                self._by_uid[kv[0]].public_id if kv[0] in self._by_uid else kv[0],
            ),
        )
        hits: list[SearchHit] = []
        for uid, score in ordered:
            op = self._by_uid.get(uid)
            if op is None:
                continue
            meta = {
                "read_only": op.read_only,
                "application_id": op.application_id,
                "permission": op.permission,
            }
            if not self._post_filter(meta, shortlist=short_set, permission=permission):
                continue
            hits.append(
                SearchHit(
                    record=op,
                    score=score,
                    vector_score=vec_scores.get(uid),
                    keyword_score=kw.get(uid),
                )
            )
            if len(hits) >= limit:
                break

        confident = bool(hits) and hits[0].score >= _MIN_CONFIDENT_SCORE
        return SearchOutcome(
            hits=hits,
            backend="vector_index",
            confident=confident,
            shortlist=shortlist,
            warnings=warnings,
        )

    @staticmethod
    def format_outcome(outcome: SearchOutcome, query: str) -> str:
        """Duck-typed formatter for sse.tools (no api_index import there)."""
        return format_search_outcome(outcome, query)

    async def _probe_shortlist(self, qvec: list[float], query: str) -> list[str]:
        kw_apps = self._keyword.exact_name_apps(query)
        if self._vs is None:
            return (kw_apps + [])[:_SHORTLIST_CAP]
        try:
            probe = await self._vs.search(
                qvec,
                namespace=self._namespace or "default",
                top_k=_PROBE_TOP_K,
                filter={"read_only": True},
            )
        except Exception:  # noqa: BLE001
            return kw_apps[:_SHORTLIST_CAP]
        by_app: dict[str, list[float]] = {}
        for hit in probe:
            app = str((hit.metadata or {}).get("application_id") or "")
            if not app:
                continue
            by_app.setdefault(app, []).append(float(hit.score))
        ranked = sorted(
            ((app, _mean_top3(scores)) for app, scores in by_app.items()),
            key=lambda t: (-t[1], t[0]),
        )
        top = [app for app, _ in ranked[: self._app_shortlist_size]]
        merged = list(dict.fromkeys([*top, *kw_apps]))
        return merged[:_SHORTLIST_CAP]


def format_search_outcome(outcome: SearchOutcome, query: str) -> str:
    """Render SearchOutcome for search_sse_apis tool text."""
    if not outcome.hits:
        return "No matching SSE API operations."
    lines: list[str] = []
    if not outcome.confident:
        lines.append(
            f'No confident match for "{query}" — the operations below are the closest, '
            "and may not answer the question."
        )
    header = backend_header(outcome.backend)
    lines.append(f"{header}\nOpenAPI operations:")
    for hit in outcome.hits:
        api = unified_to_api_operation(hit.record)
        from packages.sse.catalog import summarize_operation

        lines.append(summarize_operation(api))
    return "\n".join(lines)

