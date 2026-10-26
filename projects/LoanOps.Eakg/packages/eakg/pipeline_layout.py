"""File-mode layout mirroring product stores (GraphDB / Postgres / pgvector).

Root default: ``data/pipeline_store`` via ``EAKG_STORE__FILE_SHARD_DIR``.
"""

from __future__ import annotations

from pathlib import Path

GRAPH_DB = "GraphDb"
POSTGRES = "Postgres"
PGVECTOR = "Pgvector"
NAMED_GRAPHS = "named_graphs"


def pipeline_root(shard_dir: str | Path) -> Path:
    return Path(shard_dir)


def graph_db_dir(shard_dir: str | Path) -> Path:
    return pipeline_root(shard_dir) / GRAPH_DB / NAMED_GRAPHS


def postgres_dir(shard_dir: str | Path) -> Path:
    return pipeline_root(shard_dir) / POSTGRES


def pgvector_dir(shard_dir: str | Path) -> Path:
    return pipeline_root(shard_dir) / PGVECTOR


def resolve_file_shard_dir(file_shard_dir: str, *, fallback: str = "data/pipeline_store") -> str:
    text = (file_shard_dir or "").strip()
    return text or fallback
