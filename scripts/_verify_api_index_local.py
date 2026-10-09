"""Smoke: row counts + ApiSearchService for local Part 1."""

from __future__ import annotations

import asyncio
from pathlib import Path

from sqlalchemy import text

from packages.api_index.catalog import load_operations
from packages.api_index.keyword_index import KeywordIndex
from packages.api_index.paths import manifest_path, sidecar_path
from packages.api_index.search import ApiSearchService
from packages.common.providers.factory import get_embedding_provider, get_vector_store_provider
from packages.common.settings import get_settings


async def main() -> None:
    s = get_settings()
    vs = get_vector_store_provider()
    async with vs._engine.connect() as conn:
        n = await conn.execute(text("SELECT count(*) FROM vs_api_ops_local_47084b1c"))
        print("rows", n.scalar())
        apps = await conn.execute(
            text(
                """
                SELECT metadata->>'application_id' AS app, count(*) AS n
                FROM vs_api_ops_local_47084b1c
                GROUP BY 1 ORDER BY 1
                """
            )
        )
        for r in apps:
            print("app", r.app, r.n)

    op_set = load_operations(s.eakg.shard_dir, s.eakg.environment)
    assert op_set is not None
    callable_ops = [o for o in op_set.operations if o.callable]
    print("ops", len(op_set.operations), "callable", len(callable_ops))
    kw = KeywordIndex(callable_ops)
    shard = Path(s.eakg.shard_dir)
    env = s.eakg.environment
    svc = ApiSearchService(
        operations=callable_ops,
        keyword_index=kw,
        vector_store=vs,
        embedder=get_embedding_provider(),
        environment=env,
        namespace_prefix=s.api_index.namespace_prefix,
        app_shortlist_size=s.api_index.app_shortlist_size,
        manifest_path=manifest_path(shard, env),
        sidecar_path=sidecar_path(shard, env),
    )
    for q in ["escrow analysis loan", "fee schedule", "loan summary borrowers"]:
        outcome = await svc.search(q, limit=5)
        print("Q:", q, "backend=", outcome.backend, "confident=", outcome.confident)
        for h in outcome.hits[:5]:
            print(
                f"  {h.record.public_id} {h.record.application_id} "
                f"score={h.score:.3f}"
            )


if __name__ == "__main__":
    asyncio.run(main())
