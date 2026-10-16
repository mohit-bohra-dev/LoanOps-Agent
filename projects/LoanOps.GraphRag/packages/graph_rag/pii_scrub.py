"""Light PII scrub on extraction outputs; allowlist known state/policy tokens."""

from __future__ import annotations

import re
from typing import Any

# Scrub patterns (entity *names* matching these are dropped unless allowlisted).
_PHONE = re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
# Heuristic person: First Last (two capitalized words) — conservative; allowlist overrides.
_PERSONISH = re.compile(r"^[A-Z][a-z]+\s+[A-Z][a-z]+$")

_STATE_ALLOWLIST = frozenset(
    {
        "alabama",
        "alaska",
        "arizona",
        "arkansas",
        "california",
        "colorado",
        "connecticut",
        "delaware",
        "florida",
        "georgia",
        "hawaii",
        "idaho",
        "illinois",
        "indiana",
        "iowa",
        "kansas",
        "kentucky",
        "louisiana",
        "maine",
        "maryland",
        "massachusetts",
        "michigan",
        "minnesota",
        "mississippi",
        "missouri",
        "montana",
        "nebraska",
        "nevada",
        "new hampshire",
        "new jersey",
        "new mexico",
        "new york",
        "north carolina",
        "north dakota",
        "ohio",
        "oklahoma",
        "oregon",
        "pennsylvania",
        "rhode island",
        "south carolina",
        "south dakota",
        "tennessee",
        "texas",
        "utah",
        "vermont",
        "virginia",
        "washington",
        "west virginia",
        "wisconsin",
        "wyoming",
        "al",
        "ak",
        "az",
        "ar",
        "ca",
        "co",
        "ct",
        "de",
        "fl",
        "ga",
        "hi",
        "id",
        "il",
        "in",
        "ia",
        "ks",
        "ky",
        "la",
        "me",
        "md",
        "ma",
        "mi",
        "mn",
        "ms",
        "mo",
        "mt",
        "ne",
        "nv",
        "nh",
        "nj",
        "nm",
        "ny",
        "nc",
        "nd",
        "oh",
        "ok",
        "or",
        "pa",
        "ri",
        "sc",
        "sd",
        "tn",
        "tx",
        "ut",
        "vt",
        "va",
        "wa",
        "wv",
        "wi",
        "wy",
    }
)

_POLICY_ALLOWLIST = frozenset(
    {
        "scra",
        "usda",
        "fha",
        "gse",
        "fema",
        "ndfb",
        "lafa",
        "efta",
        "ioe",
        "pmi",
        "dil",
    }
)


def _allowed_token(name: str) -> bool:
    n = name.strip().lower()
    return n in _STATE_ALLOWLIST or n in _POLICY_ALLOWLIST


def _looks_like_pii(name: str) -> bool:
    if _PHONE.search(name) or _EMAIL.search(name) or _SSN.search(name):
        return True
    if _PERSONISH.match(name.strip()) and not _allowed_token(name):
        return True
    return False


def scrub_extraction(
    entities: list[dict[str, Any]],
    relations: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Drop PII-like entity names; drop relations touching dropped entities."""
    kept: list[dict[str, Any]] = []
    dropped: list[dict[str, Any]] = []
    kept_names: set[str] = set()
    for ent in entities:
        name = str(ent.get("name") or "")
        if _looks_like_pii(name) and not _allowed_token(name):
            dropped.append({"kind": "pii_entity", "entity": ent})
            continue
        kept.append(ent)
        kept_names.add(name.strip().lower())

    kept_rels: list[dict[str, Any]] = []
    for rel in relations:
        src = str(rel.get("source") or "").strip().lower()
        tgt = str(rel.get("target") or "").strip().lower()
        if src not in kept_names or tgt not in kept_names:
            dropped.append({"kind": "pii_relation", "relation": rel})
            continue
        kept_rels.append(rel)
    return kept, kept_rels, dropped
