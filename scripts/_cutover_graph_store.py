"""One-time cutover helper: load three pilot graphs into SPARQL store and smoke-query.

Uses GRAPH_STORE__* (GraphDB). Falls back to FakeGraphStore only when --fake is set
(CI / offline verify). Does not write Turtle back into the repo.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from packages.common.providers.factory import get_graph_store
from packages.common.providers.graph_store import FakeGraphStore
from packages.common.settings import get_settings
from packages.eakg.graph_upload import upload_graph
from rdflib import Graph

DEFAULT_IDS = ("escrow", "fees", "loanservices")

_COUNT_OPS = """
PREFIX lo: <https://loanops.local/ontology/>
SELECT (COUNT(?op) AS ?n) WHERE {
  GRAPH ?g { ?op a lo:APIOperation . }
}
"""


async def _run(*, fake: bool, shard_dir: Path, ids: list[str]) -> dict[str, object]:
    settings = get_settings()
    store = FakeGraphStore() if fake else get_graph_store()
    ns = settings.capability_kg.namespace
    report: dict[str, object] = {"backend": "fake" if fake else "http", "apps": {}}
    apps: dict[str, object] = {}
    for rid in ids:
        gpath = shard_dir / "repos" / rid / "graph.ttl"
        epath = shard_dir / "repos" / rid / "evidence.ttl"
        if not gpath.is_file():
            apps[rid] = {"status": "missing", "path": str(gpath)}
            continue
        g = Graph()
        g.parse(gpath, format="turtle")
        eg = Graph()
        if epath.is_file():
            eg.parse(epath, format="turtle")
        iri = await upload_graph(store, rid, g, namespace=ns, evidence=eg or None)
        apps[rid] = {"status": "ok", "named_graph": iri, "triples": len(g) + len(eg)}
    report["apps"] = apps
    count = await store.query(_COUNT_OPS)
    bindings = count.get("results", {}).get("bindings", [])
    n = 0
    if bindings:
        n = int(bindings[0].get("n", {}).get("value") or 0)
    report["operation_count"] = n
    if not fake:
        await store.aclose()
    return report


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--fake", action="store_true", help="Use FakeGraphStore (no GraphDB)")
    p.add_argument("--shard-dir", default="")
    p.add_argument("--ids", default=",".join(DEFAULT_IDS))
    args = p.parse_args()
    settings = get_settings()
    shard = Path(args.shard_dir or settings.eakg.shard_dir)
    ids = [x.strip() for x in args.ids.split(",") if x.strip()]
    try:
        report = asyncio.run(_run(fake=args.fake, shard_dir=shard, ids=ids))
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"status": "error", "error": str(exc)}, indent=2))
        return 2
    print(json.dumps(report, indent=2, default=str))
    apps = report.get("apps")
    if not isinstance(apps, dict):
        return 2
    if any(isinstance(v, dict) and v.get("status") != "ok" for v in apps.values()):
        return 2
    if int(report.get("operation_count") or 0) < 1:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
