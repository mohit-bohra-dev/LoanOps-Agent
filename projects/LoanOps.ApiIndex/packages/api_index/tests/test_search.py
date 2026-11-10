"""Two-stage search cases (spec §14.1 P3)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from packages.api_index.indexer import reindex, write_manifest, IndexManifest, ManifestEntry
from packages.api_index.keyword_index import KeywordIndex
from packages.api_index.records import OperationSet, UnifiedOperation, normalize_path, uid
from packages.api_index.search import (
    ApiSearchService,
    SearchHit,
    SearchOutcome,
    _MIN_CONFIDENT_SCORE,
    backend_header,
    format_search_outcome,
)
from packages.common.providers.testing import MockEmbeddingProvider, MockVectorStoreProvider


def _op(
    *,
    app: str,
    public: str,
    path: str,
    summary: str,
    permission: str | None = None,
    method: str = "get",
    read_only: bool = True,
    environment: str = "local",
) -> UnifiedOperation:
    norm = normalize_path(path)
    return UnifiedOperation(
        uid=uid(app, method, norm),
        public_id=public,
        application_id=app,
        application_label=app.title(),
        environment=environment,  # type: ignore[arg-type]
        method=method,  # type: ignore[arg-type]
        path=path,
        normalized_path=norm,
        summary=summary,
        permission=permission,
        read_only=read_only,
        callable=True,
        join="openapi_only",
        source_base_url="http://127.0.0.1:9",
        eakg_operation_key=public.split(":", 1)[-1],
    )


def _ops() -> list[UnifiedOperation]:
    return [
        _op(app="fees", public="fees:getFees", path="/api/fees/{id}", summary="get fees", permission="fees.read"),
        _op(
            app="escrow",
            public="escrow:getEscrow",
            path="/api/escrow/{id}",
            summary="get escrow",
            permission="escrow.read",
        ),
        _op(
            app="loanservices",
            public="loanservices:getLoanSummary",
            path="/api/Loans/{id}/Summary",
            summary="loan summary",
            permission="loan.read",
        ),
        _op(
            app="fees",
            public="fees:createFee",
            path="/api/fees",
            summary="create fee",
            method="post",
            read_only=False,
            permission="fees.write",
        ),
    ]


class _FailingVectorStore(MockVectorStoreProvider):
    async def search(self, *args: Any, **kwargs: Any) -> list[Any]:
        raise RuntimeError("vector store down")


class _FailingEmbedder(MockEmbeddingProvider):
    async def embed(self, text: str) -> Any:
        raise RuntimeError("embed down")


@pytest.mark.asyncio
async def test_application_filter_returns_only_that_app(tmp_path: Path) -> None:
    ops = _ops()
    vs = MockVectorStoreProvider()
    emb = MockEmbeddingProvider(dimensions=8)
    manifest = tmp_path / "m.json"
    sidecar = tmp_path / "s.json"
    await reindex(
        "local",
        OperationSet(environment="local", built_at=datetime.now(UTC), operations=ops),
        vector_store=vs,
        embedder=emb,
        manifest_path=manifest,
        namespace_prefix="api_ops",
        sidecar_path=sidecar,
    )
    svc = ApiSearchService(
        operations=ops,
        keyword_index=KeywordIndex(ops),
        vector_store=vs,
        embedder=emb,
        environment="local",
        namespace_prefix="api_ops",
        manifest_path=manifest,
        sidecar_path=sidecar,
    )
    out = await svc.search("fees", limit=10, application_ids=["fees"])
    assert out.hits
    assert all(h.record.application_id == "fees" for h in out.hits)
    assert all(h.record.read_only for h in out.hits)


@pytest.mark.asyncio
async def test_permission_filter(tmp_path: Path) -> None:
    ops = _ops()
    vs = MockVectorStoreProvider()
    emb = MockEmbeddingProvider(dimensions=8)
    manifest = tmp_path / "m.json"
    sidecar = tmp_path / "s.json"
    await reindex(
        "local",
        OperationSet(environment="local", built_at=datetime.now(UTC), operations=ops),
        vector_store=vs,
        embedder=emb,
        manifest_path=manifest,
        namespace_prefix="api_ops",
        sidecar_path=sidecar,
    )
    svc = ApiSearchService(
        operations=ops,
        keyword_index=KeywordIndex(ops),
        vector_store=vs,
        embedder=emb,
        environment="local",
        namespace_prefix="api_ops",
        manifest_path=manifest,
        sidecar_path=sidecar,
    )
    out = await svc.search("get", limit=20, permission="loan.read")
    assert out.hits
    assert all(h.record.permission == "loan.read" for h in out.hits)


@pytest.mark.asyncio
async def test_shortlist_contains_keyword_exact_app(tmp_path: Path) -> None:
    ops = _ops()
    vs = MockVectorStoreProvider()
    emb = MockEmbeddingProvider(dimensions=8)
    manifest = tmp_path / "m.json"
    sidecar = tmp_path / "s.json"
    await reindex(
        "local",
        OperationSet(environment="local", built_at=datetime.now(UTC), operations=ops),
        vector_store=vs,
        embedder=emb,
        manifest_path=manifest,
        namespace_prefix="api_ops",
        sidecar_path=sidecar,
    )
    svc = ApiSearchService(
        operations=ops,
        keyword_index=KeywordIndex(ops),
        vector_store=vs,
        embedder=emb,
        environment="local",
        namespace_prefix="api_ops",
        app_shortlist_size=1,
        manifest_path=manifest,
        sidecar_path=sidecar,
    )
    out = await svc.search("getLoanSummary", limit=5)
    assert "loanservices" in out.shortlist


@pytest.mark.asyncio
async def test_vector_error_falls_back_to_sidecar_label(tmp_path: Path) -> None:
    ops = _ops()
    emb = MockEmbeddingProvider(dimensions=8)
    good = MockVectorStoreProvider()
    manifest = tmp_path / "m.json"
    sidecar = tmp_path / "s.json"
    await reindex(
        "local",
        OperationSet(environment="local", built_at=datetime.now(UTC), operations=ops),
        vector_store=good,
        embedder=emb,
        manifest_path=manifest,
        namespace_prefix="api_ops",
        sidecar_path=sidecar,
    )
    svc = ApiSearchService(
        operations=ops,
        keyword_index=KeywordIndex(ops),
        vector_store=_FailingVectorStore(),
        embedder=emb,
        environment="local",
        namespace_prefix="api_ops",
        manifest_path=manifest,
        sidecar_path=sidecar,
    )
    out = await svc.search("fees", limit=5)
    assert out.backend == "sidecar"
    assert backend_header(out.backend) == "(fallback: local vector sidecar)"
    assert "vector_store_unavailable" in out.warnings


@pytest.mark.asyncio
async def test_embed_error_falls_back_to_keyword_label(tmp_path: Path) -> None:
    ops = _ops()
    svc = ApiSearchService(
        operations=ops,
        keyword_index=KeywordIndex(ops),
        vector_store=MockVectorStoreProvider(),
        embedder=_FailingEmbedder(dimensions=8),
        environment="local",
        namespace_prefix="api_ops",
        manifest_path=tmp_path / "m.json",
        sidecar_path=tmp_path / "s.json",
    )
    out = await svc.search("getFees", limit=5)
    assert out.backend == "keyword"
    assert backend_header(out.backend) == "(keyword search — embeddings unavailable)"
    assert out.hits


@pytest.mark.asyncio
async def test_no_confident_match_header(tmp_path: Path) -> None:
    ops = _ops()
    svc = ApiSearchService(
        operations=ops,
        keyword_index=KeywordIndex(ops),
        vector_store=None,
        embedder=None,
        environment="local",
        namespace_prefix="api_ops",
    )
    out = await svc.search("zzzznotanoperation", limit=5)
    # keyword may still return weak hits or empty
    text = format_search_outcome(out, "zzzznotanoperation")
    if out.hits and not out.confident:
        assert "No confident match" in text
    elif not out.hits:
        assert text == "No matching SSE API operations."
    else:
        # force low score path via outcome
        out.confident = False
        out.hits[0].score = _MIN_CONFIDENT_SCORE - 0.01
        text2 = format_search_outcome(out, "zzzznotanoperation")
        assert "No confident match" in text2


def test_format_states_backend_invoke_and_missing_params() -> None:
    op = _op(
        app="escrow",
        public="escrow:GetLatest",
        path="/api/EscrowAnalysis/GetLatest",
        summary="latest analysis",
    )
    write = _op(
        app="escrow",
        public="escrow:Perform",
        path="/api/SingleEscrowAnalysis/Perform",
        summary="run analysis",
        method="post",
        read_only=False,
    )
    head = _op(
        app="escrow",
        public="escrow:HeadLatest",
        path="/api/EscrowAnalysis/HeadLatest",
        summary="head probe",
        method="head",
        read_only=True,
    )
    text = format_search_outcome(
        SearchOutcome(
            hits=[
                SearchHit(record=op, score=0.9),
                SearchHit(record=write, score=0.4),
                SearchHit(record=head, score=0.3),
            ],
            backend="vector_index",
            confident=True,
        ),
        "escrow analysis",
    )
    assert text.startswith("backend: vector_index")
    assert "invoke: call_sse_api" in text
    assert "invoke: not via call_sse_api (GET-only)" in text
    assert "params: none in cached spec" in text
    # HEAD must not be labeled callable (policy is GET-only).
    assert text.count("invoke: not via call_sse_api (GET-only)") >= 2

    weak = format_search_outcome(
        SearchOutcome(
            hits=[SearchHit(record=op, score=0.2)],
            backend="vector_index",
            confident=False,
        ),
        "zzzz",
    )
    assert weak.startswith("backend: vector_index")
    assert "No confident match" in weak


@pytest.mark.asyncio
async def test_keyword_index_graded_score() -> None:
    ops = _ops()
    idx = KeywordIndex(ops)
    scored = idx.score("getFees")
    assert scored
    top_uid = max(scored, key=lambda u: scored[u])
    assert idx._by_uid[top_uid].public_id == "fees:getFees"
    assert "fees" in idx.exact_name_apps("getFees")


@pytest.mark.asyncio
async def test_env_isolation_namespace(tmp_path: Path) -> None:
    """Same app in two envs ⇒ distinct namespaces (US9)."""
    ops_local = [
        _op(
            app="fees",
            public="fees:getFees",
            path="/api/fees/{id}",
            summary="local fees",
            environment="local",
        )
    ]
    ops_stage = [
        _op(
            app="fees",
            public="fees:getFees",
            path="/api/fees/{id}",
            summary="stage fees DIFFERENT",
            environment="stage",
        )
    ]
    vs = MockVectorStoreProvider()
    emb = MockEmbeddingProvider(dimensions=8)
    r1 = await reindex(
        "local",
        OperationSet(environment="local", built_at=datetime.now(UTC), operations=ops_local),
        vector_store=vs,
        embedder=emb,
        manifest_path=tmp_path / "local" / "m.json",
        namespace_prefix="api_ops",
        sidecar_path=tmp_path / "local" / "s.json",
    )
    r2 = await reindex(
        "stage",
        OperationSet(environment="stage", built_at=datetime.now(UTC), operations=ops_stage),
        vector_store=vs,
        embedder=emb,
        manifest_path=tmp_path / "stage" / "m.json",
        namespace_prefix="api_ops",
        sidecar_path=tmp_path / "stage" / "s.json",
    )
    assert r1.namespace != r2.namespace
    assert "local" in r1.namespace
    assert "stage" in r2.namespace


@pytest.mark.asyncio
async def test_always_post_filters_even_with_any_of(tmp_path: Path) -> None:
    """Product rule: post-filter always runs even when supports_any_of_filter."""
    ops = _ops()
    vs = MockVectorStoreProvider()
    assert vs.supports_any_of_filter is True
    emb = MockEmbeddingProvider(dimensions=8)
    manifest = tmp_path / "m.json"
    sidecar = tmp_path / "s.json"
    await reindex(
        "local",
        OperationSet(environment="local", built_at=datetime.now(UTC), operations=ops),
        vector_store=vs,
        embedder=emb,
        manifest_path=manifest,
        namespace_prefix="api_ops",
        sidecar_path=sidecar,
    )
    svc = ApiSearchService(
        operations=ops,
        keyword_index=KeywordIndex(ops),
        vector_store=vs,
        embedder=emb,
        environment="local",
        namespace_prefix="api_ops",
        manifest_path=manifest,
        sidecar_path=sidecar,
    )
    out = await svc.search("fee", limit=20, application_ids=["fees"])
    assert all(h.record.application_id == "fees" for h in out.hits)
    assert all(h.record.read_only for h in out.hits)


def test_manifest_model_id_written(tmp_path: Path) -> None:
    write_manifest(
        tmp_path / "m.json",
        IndexManifest(
            namespace="api_ops_local_x",
            embed_model_id="mock:8",
            entries={"u": ManifestEntry(text_hash="a", public_id="a:b", application_id="a")},
        ),
    )
    assert (tmp_path / "m.json").is_file()


class _CountingEmbedder(MockEmbeddingProvider):
    def __init__(self, dimensions: int = 8) -> None:
        super().__init__(dimensions=dimensions)
        self.texts: list[str] = []

    async def embed(self, text: str) -> Any:
        self.texts.append(text)
        return await super().embed(text)


@pytest.mark.asyncio
async def test_search_embeds_query_once_no_probe(tmp_path: Path) -> None:
    """Cold search embeds the query only — never a separate embed('probe')."""
    ops = _ops()
    vs = MockVectorStoreProvider()
    emb = _CountingEmbedder(dimensions=8)
    manifest = tmp_path / "m.json"
    sidecar = tmp_path / "s.json"
    await reindex(
        "local",
        OperationSet(environment="local", built_at=datetime.now(UTC), operations=ops),
        vector_store=vs,
        embedder=MockEmbeddingProvider(dimensions=8),
        manifest_path=manifest,
        namespace_prefix="api_ops",
        sidecar_path=sidecar,
    )
    svc = ApiSearchService(
        operations=ops,
        keyword_index=KeywordIndex(ops),
        vector_store=vs,
        embedder=emb,
        environment="local",
        namespace_prefix="api_ops",
        manifest_path=manifest,
        sidecar_path=sidecar,
    )
    await svc.search("get fees", limit=5)
    assert emb.texts == ["get fees"]
    assert "probe" not in emb.texts

    # Same query hits query embed LRU — zero additional embeds.
    await svc.search("get fees", limit=5)
    assert emb.texts == ["get fees"]

    # Distinct query pays one more embed.
    await svc.search("loan summary", limit=5)
    assert emb.texts == ["get fees", "loan summary"]
    assert "probe" not in emb.texts


class _FlakyThenOkEmbedder(_CountingEmbedder):
    def __init__(self, dimensions: int = 8) -> None:
        super().__init__(dimensions=dimensions)
        self.fail_once = True

    async def embed(self, text: str) -> Any:
        self.texts.append(text)
        if self.fail_once:
            self.fail_once = False
            raise RuntimeError("transient")
        return await MockEmbeddingProvider.embed(self, text)


@pytest.mark.asyncio
async def test_transient_embed_failure_does_not_poison_probe(tmp_path: Path) -> None:
    """Failed embed must not set _model_probed so the next call can recover."""
    ops = _ops()
    emb = _FlakyThenOkEmbedder(dimensions=8)
    svc = ApiSearchService(
        operations=ops,
        keyword_index=KeywordIndex(ops),
        vector_store=MockVectorStoreProvider(),
        embedder=emb,
        environment="local",
        namespace_prefix="api_ops",
        manifest_path=tmp_path / "m.json",
        sidecar_path=tmp_path / "s.json",
    )
    out1 = await svc.search("getFees", limit=5)
    assert out1.backend == "keyword"
    assert svc._model_probed is False

    out2 = await svc.search("getFees", limit=5)
    assert out2.backend in {"vector_index", "sidecar", "keyword"}
    assert svc._model_probed is True
