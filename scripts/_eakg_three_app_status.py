"""Print EAKG/OpenAPI status for registry-active apps (no secrets)."""

from __future__ import annotations

import json
from pathlib import Path

from packages.common.settings import get_settings
from packages.eakg.registry import RepositoryRegistry


def main() -> None:
    s = get_settings()
    reg = RepositoryRegistry(s.eakg.registry_path)
    print("env", s.eakg.environment, "shard", s.eakg.shard_dir)
    for r in reg.list_active(s.eakg.environment):
        app = r.application_id
        root = Path(s.eakg.shard_dir) / "repos" / app
        iface = root / "interface.json"
        g = root / "graph.ttl"
        ev = root / "evidence.ttl"
        env_local = r.environments.get("local")
        fixture = env_local.spec_fixture if env_local else None
        ptr = root / "openapi" / "local" / "current.json"
        ops = 0
        if iface.is_file():
            ops = len(json.loads(iface.read_text(encoding="utf-8")).get("operations") or [])
        ptr_info: dict = {}
        if ptr.is_file():
            ptr_info = json.loads(ptr.read_text(encoding="utf-8"))
        print("---", app)
        print("  indexed_commit", r.last_indexed_commit, "status", r.index_status)
        print("  interface_ops", ops)
        print("  graph_ttl_kb", round(g.stat().st_size / 1024, 1) if g.is_file() else None)
        print("  evidence_ttl_kb", round(ev.stat().st_size / 1024, 1) if ev.is_file() else None)
        print("  local_spec_fixture", bool(fixture), fixture)
        print(
            "  openapi_cache",
            {
                k: ptr_info.get(k)
                for k in ("spec_hash", "operation_count", "source_url", "status")
            },
        )


if __name__ == "__main__":
    main()
