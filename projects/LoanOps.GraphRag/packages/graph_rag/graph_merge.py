"""Merge DocLinkGraph edges with shared-entity path edges; resolve entities."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def resolve_entities(
    per_chunk: list[tuple[str, str, list[dict[str, Any]], list[dict[str, Any]]]],
) -> dict[str, Any]:
    """Deterministic entity/relation graph from grounded chunk extractions.

    per_chunk items: (chunk_id, path, entities, relations)
    """
    entities: dict[str, dict[str, Any]] = {}
    relations: list[dict[str, Any]] = []
    entity_chunks: dict[str, list[str]] = defaultdict(list)
    entity_paths: dict[str, set[str]] = defaultdict(set)
    seen_rel: set[tuple[str, str, str]] = set()

    for chunk_id, path, ents, rels in per_chunk:
        for ent in ents:
            name = str(ent["name"]).strip()
            key = name.lower()
            if key not in entities:
                entities[key] = {"id": key, "name": name, "type": ent.get("type", "concept")}
            entity_chunks[key].append(chunk_id)
            entity_paths[key].add(path)
        for rel in rels:
            src = str(rel["source"]).strip().lower()
            tgt = str(rel["target"]).strip().lower()
            typ = str(rel.get("type") or "related")
            rel_key = (src, tgt, typ)
            if rel_key in seen_rel:
                continue
            seen_rel.add(rel_key)
            relations.append({"source": src, "target": tgt, "type": typ})

    # Shared-entity path edges (kind=shared_entity)
    path_edges: list[dict[str, str]] = []
    seen_pe: set[tuple[str, str]] = set()
    for _key, paths in entity_paths.items():
        plist = sorted(paths)
        for i, a in enumerate(plist):
            for b in plist[i + 1 :]:
                lo, hi = (a, b) if a < b else (b, a)
                if (lo, hi) in seen_pe:
                    continue
                seen_pe.add((lo, hi))
                path_edges.append({"from": a, "to": b, "kind": "shared_entity"})

    entity_list = [entities[k] for k in sorted(entities)]
    for e in entity_list:
        e["chunk_ids"] = sorted(set(entity_chunks[e["id"]]))
        e["paths"] = sorted(entity_paths[e["id"]])
    relations.sort(key=lambda r: (r["source"], r["target"], r["type"]))
    path_edges.sort(key=lambda e: (e["kind"], e["from"], e["to"]))

    return {
        "entities": entity_list,
        "relations": relations,
        "path_edges": path_edges,
    }


def merge_doc_and_entity_edges(
    doc_edges: list[dict[str, str]],
    path_edges: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Union of doc_links + shared_entity edges; sorted unique."""
    seen: set[tuple[str, str, str]] = set()
    out: list[dict[str, str]] = []
    for edge in list(doc_edges) + list(path_edges):
        a = edge["from"].replace("\\", "/")
        b = edge["to"].replace("\\", "/")
        kind = edge.get("kind", "related")
        lo, hi = (a, b) if a < b else (b, a)
        key = (lo, hi, kind)
        if key in seen:
            continue
        seen.add(key)
        out.append({"from": a, "to": b, "kind": kind})
    out.sort(key=lambda e: (e["kind"], e["from"], e["to"]))
    return out
